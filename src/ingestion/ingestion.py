"""
agents/ingestion.py
--------------------
Code Ingestion Agent.

Responsibilities
-----------------
1. Read a raw .sql/.prc/.pks/.pkb/.txt file containing one banking DB
   object (procedure, function, view, trigger, or a standalone
   procedural block), in either Oracle SQL/PL-SQL or SQL Server T-SQL.
2. Run input guardrails (sanitize encoding artifacts, flag possible
   prompt-injection content in comments/strings) before anything else
   touches the text.
3. Detect the SQL dialect (Oracle vs T-SQL) unless the caller already
   supplied one, and apply dialect-appropriate object/parameter/batch
   detection.
4. Identify the object type and its name.
5. Extract the formal parameter list (name / direction / datatype) for
   procedures & functions, using dialect-appropriate syntax.
6. Use `sqlglot`, with the correct read dialect, to structurally
   validate/parse the embedded SQL statements (SELECT / INSERT / UPDATE
   / DELETE / MERGE) that live inside the procedural body. sqlglot does
   not understand procedural control-flow (IF/LOOP/CURSOR/EXCEPTION,
   TRY/CATCH) natively, so those regions are chunked using
   structural/regex heuristics instead.
7. Split large objects into logical, context-preserving chunks
   (declaration section, per-cursor blocks, main executable body,
   nested blocks, exception section, and - for T-SQL - per-batch
   sections split on "GO" separators) so that no chunk sent downstream
   ever risks overflowing the LLM's context window.

All structural detection (step 6/7) is done against a *masked* copy of
the code - string literals and comments have their interior replaced
with spaces so structural keywords that only appear inside a comment or
a quoted string can never misfire the section splitter. The real,
unmasked code text is always what is stored in chunks and sent
downstream; masking never removes information needed for business-rule
extraction, it only prevents it from confusing structural detection.

Nothing in this module talks to an LLM - it is a pure, deterministic
pre-processing stage.
"""

from __future__ import annotations

import codecs
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import sqlglot
from sqlglot.errors import ParseError

from src.validation.confidence import derive_chunk_support_confidence
from src.dialect.detector import (
    AMBIGUOUS,
    ORACLE,
    POSTGRES,
    TSQL,
    UNKNOWN,
    UNSUPPORTED,
    DialectDetectionResult,
    detect_dialect,
    normalize_dialect_name,
    prompt_dialect_for_state,
)
from src.ingestion.guardrails import InputGuardrailError, run_input_guardrails
from src.parsing.statement_boundaries import split_top_level_statement_spans
from src.core.pipeline_utils import RunMetadata, stable_id, source_hash

# --------------------------------------------------------------------------
# Source-byte decoding
# --------------------------------------------------------------------------
#
# Kept at module level (not just as a CodeIngestionAgent staticmethod) so
# every entry point that reads raw SQL bytes - the CLI (main.py), the
# Streamlit uploader / bundled-sample picker (app.py), and tests - can
# import and reuse the exact same encoding detection instead of each
# caller doing its own (often naive) `.decode("utf-8", errors="replace")`,
# which silently corrupts the very common case of a UTF-16 SSMS/Toad SQL
# export (every character interleaved with NUL bytes survives the decode
# as garbage rather than raising, so the corruption is invisible until
# parsing/extraction downstream mysteriously fails or truncates).


def decode_sql_source_bytes(raw: bytes) -> str:
    """Decode SQL source text using a small set of safe, common encodings.

    Many vendor SQL exports (SSMS "Save As", Toad, etc.) are UTF-16 with a
    BOM, or UTF-16 without a BOM. Reading them as UTF-8 with
    errors="replace" does not raise - it "succeeds" while turning every
    character into `<char>\\x00`, which then fails every keyword/regex
    match downstream (BEGIN/END, DELETE/TRUNCATE, table names, etc.) with
    no visible error. We try BOM/heuristic-based decoders first, then fall
    back to UTF-8.
    """
    if not raw:
        return ""

    candidates: List[str] = []

    if raw.startswith(codecs.BOM_UTF8):
        candidates.append("utf-8-sig")
    if raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE):
        candidates.append("utf-16")
    else:
        # No BOM: heuristically detect UTF-16 by NUL-byte parity. Plain
        # ASCII/UTF-8 SQL source essentially never contains NUL bytes, so a
        # high NUL ratio is a strong UTF-16 signal; which half of the byte
        # pairs is zero tells us little-endian vs big-endian.
        nul_ratio = raw.count(b"\x00") / max(len(raw), 1)
        if nul_ratio > 0.1:
            even_nuls = raw[0::2].count(0) / max(len(raw[0::2]), 1)
            odd_nuls = raw[1::2].count(0) / max(len(raw[1::2]), 1)
            if odd_nuls > even_nuls:
                candidates.extend(["utf-16-le", "utf-16"])
            elif even_nuls > odd_nuls:
                candidates.extend(["utf-16-be", "utf-16"])

    candidates.extend(["utf-8-sig", "utf-8"])

    seen = set()
    for encoding in candidates:
        if encoding in seen:
            continue
        seen.add(encoding)
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------
# Data models
# --------------------------------------------------------------------------


@dataclass
class Parameter:
    name: str
    direction: str  # IN / OUT / IN OUT
    datatype: str


@dataclass
class CodeChunk:
    chunk_id: str
    kind: str  # declaration | main_body | cursor | exception | nested_block | statement
    text: str
    embedded_sql: List[str] = field(default_factory=list)
    context_path: List[str] = field(default_factory=list)
    source_filename: str = ""
    source_char_start: int = -1
    source_char_end: int = -1
    source_line_start: int = -1
    source_line_end: int = -1
    source_location_status: str = "unavailable"


@dataclass
class IngestionResult:
    object_name: str
    object_type: str  # PROCEDURE | FUNCTION | VIEW | TRIGGER | PLSQL_BLOCK | UNKNOWN
    parameters: List[Parameter]
    raw_code: str
    chunks: List[CodeChunk]
    original_code: str = ""
    object_id: str = ""
    source_filename: str = ""
    dialect: str = ORACLE
    dialect_confidence: str = "high"
    concrete_dialect: str = ""
    fallback_dialect: str = ""
    source_hash: str = ""
    object_name_status: str = "verified"  # verified | failed
    parameter_parse_status: str = "parameterless"  # parameterized | parameterless | failed
    parse_warnings: List[str] = field(default_factory=list)
    run_metadata: Optional[RunMetadata] = None
    # Schema/owner the object was declared under (e.g. "PRO" from
    # "[PRO].[SMA_MARKING_12122023]"), when the source header was
    # schema-qualified. Empty when the header had no qualifier. This is
    # purely a delimiter split of the same header that produced
    # `object_name` - never guessed or defaulted.
    schema: str = ""
    # The stable *business* identity for this object, derived from
    # `object_name` by stripping generic, non-domain-specific trailing
    # version/date/backup-style suffixes (see
    # `CodeIngestionAgent.derive_canonical_business_name`). Used for
    # report titles and filenames so that dated/versioned copies of the
    # same procedure ("SMA_MARKING_12122023", "SMA_MARKING_v2", ...)
    # are documented under one stable identity. `object_name` itself is
    # left untouched and remains the exact technical identifier used
    # for source-code matching/reconciliation.
    canonical_object_name: str = ""


# --------------------------------------------------------------------------
# Object identity -> output filename
# --------------------------------------------------------------------------

# Display token used in report/output filenames for each object type,
# matching the project's existing `<Schema>.<Name>.<Type>_report.md`
# convention (e.g. "PRO.SMA_MARKING.StoredProcedure_report.md").
_OBJECT_TYPE_FILENAME_TOKEN = {
    "PROCEDURE": "StoredProcedure",
    "FUNCTION": "Function",
    "VIEW": "View",
    "TRIGGER": "Trigger",
    "PLSQL_BLOCK": "Block",
    "TSQL_BLOCK": "Block",
}


def build_object_identity_stem(ingestion: "IngestionResult", fallback_stem: str = "") -> str:
    """Builds the `<Schema>.<Name>.<Type>` filename stem for a report from
    the object's *parsed* identity, not from whatever the input .sql file
    happened to be named.

    This is the single, generic place output naming is decided: it is
    driven entirely by `IngestionResult` (schema qualifier + canonical
    business name + object type, all derived from the SQL definition
    itself), so it produces a stable name for any procedure, function,
    view, or trigger - regardless of what the uploaded/source filename
    was, and without any hardcoded object name or date. `fallback_stem`
    (typically the source file's stem) is only used when the object
    identity could not be determined at all (e.g. an unparseable or
    anonymous block), preserving the previous behavior for that edge
    case.
    """
    name = str(getattr(ingestion, "canonical_object_name", "") or "").strip()
    if not name or name.upper() in {"UNKNOWN_OBJECT", "UNKNOWN"}:
        name = str(getattr(ingestion, "object_name", "") or "").strip()
    if not name or name.upper() in {"UNKNOWN_OBJECT", "UNKNOWN", "ANONYMOUS_BLOCK"}:
        return fallback_stem or "UNKNOWN_OBJECT"

    object_type = str(getattr(ingestion, "object_type", "") or "").strip().upper()
    type_token = _OBJECT_TYPE_FILENAME_TOKEN.get(object_type)
    if not type_token:
        type_token = re.sub(r"[^A-Za-z0-9]+", "", object_type).title() or "Object"

    schema = str(getattr(ingestion, "schema", "") or "").strip()
    if schema:
        return f"{schema}.{name}.{type_token}"
    return f"{name}.{type_token}"


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

MAX_CHUNK_CHARS = 3000  # ceiling per chunk sent to the LLM - generous headroom
# chosen to minimize the number of LLM calls per object while still
# keeping any single call well within budget.

_OBJECT_TYPE_PATTERNS = {
    ORACLE: [
        ("PROCEDURE", re.compile(r"\bCREATE\s+(OR\s+REPLACE\s+)?PROCEDURE\b", re.IGNORECASE)),
        ("FUNCTION", re.compile(r"\bCREATE\s+(OR\s+REPLACE\s+)?FUNCTION\b", re.IGNORECASE)),
        ("TRIGGER", re.compile(r"\bCREATE\s+(OR\s+REPLACE\s+)?TRIGGER\b", re.IGNORECASE)),
        ("VIEW", re.compile(r"\bCREATE\s+(OR\s+REPLACE\s+)?(FORCE\s+)?VIEW\b", re.IGNORECASE)),
    ],
    TSQL: [
        ("PROCEDURE", re.compile(r"\bCREATE\s+(OR\s+ALTER\s+)?PROC(EDURE)?\b", re.IGNORECASE)),
        ("PROCEDURE", re.compile(r"\bALTER\s+PROC(EDURE)?\b", re.IGNORECASE)),
        ("FUNCTION", re.compile(r"\bCREATE\s+(OR\s+ALTER\s+)?FUNCTION\b", re.IGNORECASE)),
        ("TRIGGER", re.compile(r"\bCREATE\s+(OR\s+ALTER\s+)?TRIGGER\b", re.IGNORECASE)),
        ("VIEW", re.compile(r"\bCREATE\s+(OR\s+ALTER\s+)?VIEW\b", re.IGNORECASE)),
    ],
}

_ANON_BLOCK_PATTERN = re.compile(r"^\s*DECLARE\b|^\s*BEGIN\b", re.IGNORECASE)

_ORACLE_NAME = re.compile(
    r'(?:"(?:[^"]|"")+"|[A-Za-z0-9_$#]+)(?:\s*\.\s*(?:"(?:[^"]|"")+"|[A-Za-z0-9_$#]+))*'
)
_TSQL_NAME = re.compile(
    r'(?:\[(?:[^\]]|\]\])+\]|[A-Za-z0-9_]+)(?:\s*\.\s*(?:\[(?:[^\]]|\]\])+\]|[A-Za-z0-9_]+))*'
)

_NAME_PATTERNS = {
    ORACLE: {
        "PROCEDURE": re.compile(rf"PROCEDURE\s+({_ORACLE_NAME.pattern})", re.IGNORECASE),
        "FUNCTION": re.compile(rf"FUNCTION\s+({_ORACLE_NAME.pattern})", re.IGNORECASE),
        "TRIGGER": re.compile(rf"TRIGGER\s+({_ORACLE_NAME.pattern})", re.IGNORECASE),
        "VIEW": re.compile(rf"VIEW\s+({_ORACLE_NAME.pattern})", re.IGNORECASE),
    },
    TSQL: {
        "PROCEDURE": re.compile(rf"PROC(?:EDURE)?\s+({_TSQL_NAME.pattern})", re.IGNORECASE),
        "FUNCTION": re.compile(rf"FUNCTION\s+({_TSQL_NAME.pattern})", re.IGNORECASE),
        "TRIGGER": re.compile(rf"TRIGGER\s+({_TSQL_NAME.pattern})", re.IGNORECASE),
        "VIEW": re.compile(rf"VIEW\s+({_TSQL_NAME.pattern})", re.IGNORECASE),
    },
}

# Matches a single formal Oracle parameter inside a (....) parameter list, e.g.
#   p_account_id IN NUMBER
#   p_result OUT VARCHAR2
_PARAM_LINE_ORACLE = re.compile(
    r"^\s*([A-Za-z0-9_\"$]+)\s+"
    r"(IN\s+OUT|IN|OUT)?\s*"
    r"([A-Za-z0-9_.]+(?:\([^)]*\))?)",
    re.IGNORECASE,
)

# Matches a single formal T-SQL parameter, e.g.
#   @p_account_id INT
#   @p_result VARCHAR(50) OUTPUT
#   @p_status INT = 0 OUT
_PARAM_LINE_TSQL = re.compile(
    r"^\s*(@[A-Za-z0-9_]+)\s+"
    r"([A-Za-z0-9_.]+(?:\([^)]*\))?)"
    r"(?:\s*=\s*[^,]+?)?"
    r"\s*(OUTPUT|OUT)?\s*$",
    re.IGNORECASE,
)

_GO_BATCH_SPLIT = re.compile(r"^[ \t]*GO[ \t]*$", re.IGNORECASE | re.MULTILINE)
_DYNAMIC_SQL_ORACLE = re.compile(r"\b(?:EXECUTE\s+IMMEDIATE|DBMS_SQL(?:\b|\.)?)", re.IGNORECASE)
_DYNAMIC_SQL_TSQL = re.compile(
    r"\b(?:SP_EXECUTESQL\b|EXEC(?:UTE)?\s*\(\s*|EXEC(?:UTE)?\s+@)",
    re.IGNORECASE,
)


class CodeIngestionAgent:
    """Deterministic parsing / chunking front-door of the pipeline."""

    def __init__(self, max_chunk_chars: int = MAX_CHUNK_CHARS, dialect: str = "auto"):
        self.max_chunk_chars = max_chunk_chars
        self.dialect_hint = dialect

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, file_path: str, dialect: Optional[str] = None) -> IngestionResult:
        raw_code = self._load_file(file_path)
        return self.ingest_text(raw_code, dialect=dialect, source_filename=file_path, original_code=raw_code)

    def ingest_text(
        self,
        raw_code: str,
        dialect: Optional[str] = None,
        source_filename: Optional[str] = None,
        original_code: Optional[str] = None,
        prevalidated_code: Optional[str] = None,
        prevalidated_warnings: Optional[List[str]] = None,
        prevalidated_injection_flags: Optional[List[str]] = None,
        detection_result: Optional[DialectDetectionResult] = None,
    ) -> IngestionResult:
        """Same as `ingest`, but takes source text directly (used by the
        pipeline once input guardrails have already run once at the top
        of the flow, to avoid double-sanitizing the same text).
        """
        warnings: List[str] = []

        if prevalidated_code is None:
            try:
                guard_result = run_input_guardrails(raw_code)
            except InputGuardrailError as exc:
                raise ValueError(str(exc)) from exc
            clean_code = guard_result.clean_code
            warnings.extend(guard_result.warnings)
            warnings.extend(guard_result.injection_flags)
        else:
            clean_code = prevalidated_code
            warnings.extend(prevalidated_warnings or [])
            warnings.extend(prevalidated_injection_flags or [])

        detection = detection_result or detect_dialect(clean_code, hint=dialect or self.dialect_hint)
        resolved_dialect = normalize_dialect_name(detection.dialect)
        if resolved_dialect in {UNKNOWN, AMBIGUOUS, UNSUPPORTED}:
            if resolved_dialect == UNSUPPORTED:
                warnings.append("PostgreSQL features detected; unsupported by the current parser layer.")
            elif resolved_dialect == UNKNOWN:
                warnings.append("Insufficient evidence to determine a supported SQL dialect.")
            else:
                warnings.append("Dialect evidence is conflicting between Oracle and T-SQL; manual review is required.")

            chunks = self.chunk_code(
                clean_code,
                warnings,
                dialect=resolved_dialect,
                source_filename=source_filename or "",
                source_text=original_code or raw_code,
            )
            warnings = [
                warning
                for warning in warnings
                if "Dialect-specific SQL parsing was unavailable for this object; embedded SQL is preserved" not in warning
            ]
            object_id = stable_id("obj", source_hash(clean_code), "UNKNOWN", "UNKNOWN_OBJECT", resolved_dialect)
            return IngestionResult(
                object_id=object_id,
                object_name="UNKNOWN_OBJECT",
                object_type="UNKNOWN",
                parameters=[],
                raw_code=clean_code,
                chunks=chunks,
                original_code=original_code or raw_code,
                source_filename=source_filename or "",
                dialect=resolved_dialect,
                dialect_confidence=detection.confidence,
                concrete_dialect="",
                fallback_dialect="",
                source_hash=source_hash(clean_code),
                object_name_status="failed",
                parameter_parse_status="failed",
                parse_warnings=warnings,
                run_metadata=None,
                schema="",
                canonical_object_name="UNKNOWN_OBJECT",
            )
        prompt_dialect = detection.concrete_dialect or prompt_dialect_for_state(resolved_dialect) or "oracle"
        if detection.confidence == "low":
            warnings.append(
                f"SQL dialect could not be confidently determined; verify the object was analyzed under the "
                "correct dialect."
            )

        object_type, object_name, parameters, metadata_warnings, object_name_status, parameter_status = (
            self.extract_object_metadata(
                clean_code,
                dialect=prompt_dialect,
                source_filename=source_filename or "",
            )
        )
        warnings.extend(metadata_warnings)

        # Schema qualifier (if any) from the same header match, and the
        # display/business identity derived from the raw object name -
        # see `extract_object_schema` / `derive_canonical_business_name`.
        # Only attempted when the name actually came from the SQL header
        # itself (not a filename fallback), so a schema is never guessed
        # from anything other than the object's own declaration.
        object_schema = ""
        if object_name_status == "verified" and object_name != "UNKNOWN_OBJECT":
            object_schema = self.extract_object_schema(clean_code, object_type, dialect=prompt_dialect)
        canonical_object_name = self.derive_canonical_business_name(object_name)

        chunks = self.chunk_code(
            clean_code,
            warnings,
            dialect=resolved_dialect,
            source_filename=source_filename or "",
            source_text=original_code or raw_code,
        )
        object_id = stable_id("obj", source_hash(clean_code), object_type, object_name, resolved_dialect)
        run_metadata = None

        return IngestionResult(
            object_id=object_id,
            object_name=object_name,
            object_type=object_type,
            parameters=parameters,
            raw_code=clean_code,
            chunks=chunks,
            original_code=original_code or raw_code,
            source_filename=source_filename or "",
            dialect=resolved_dialect,
            dialect_confidence=detection.confidence,
            concrete_dialect=detection.concrete_dialect or "",
            fallback_dialect=prompt_dialect if resolved_dialect != prompt_dialect.upper() else "",
            source_hash=source_hash(clean_code),
            object_name_status=object_name_status,
            parameter_parse_status=parameter_status,
            parse_warnings=warnings,
            run_metadata=run_metadata,
            schema=object_schema,
            canonical_object_name=canonical_object_name,
        )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_file(file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Input SQL file not found: {file_path}")
        if path.suffix.lower() not in (".sql", ".prc", ".pks", ".pkb", ".txt"):
            raise ValueError(
                f"Unsupported file extension '{path.suffix}'. Expected a .sql file."
            )
        raw = path.read_bytes()
        return CodeIngestionAgent._decode_source_bytes(raw)

    @staticmethod
    def _decode_source_bytes(raw: bytes) -> str:
        """Decode SQL source text using a small set of safe, common encodings.

        Thin wrapper kept for backward compatibility; delegates to the
        module-level ``decode_sql_source_bytes`` so every entry point
        (CLI, Streamlit upload, bundled-sample loading, tests) shares the
        exact same encoding detection instead of each caller reimplementing
        (or, worse, skipping) it.
        """
        return decode_sql_source_bytes(raw)

    # ------------------------------------------------------------------
    # Comment / string masking (used only to find structural split points)
    # ------------------------------------------------------------------

    @staticmethod
    def _mask_strings_and_comments(
        code: str, mask_brackets: bool = True, mask_double_quotes: bool = True
    ) -> str:
        """Return a same-length copy of `code` with the interior of line
        comments (--...), block comments (/*...*/), and single-quoted
        string literals (with '' escaping handled) replaced by spaces.

        This is used exclusively to locate structural split points
        (BEGIN/END/EXCEPTION/CURSOR/GO-batch boundaries, dynamic-SQL
        detection) so a keyword that only appears inside a comment or a
        quoted string can never misfire structural detection. The
        original, unmasked `code` is always what gets stored in chunks
        and sent to downstream stages - masking never discards any
        business-rule-relevant content, it only guides where to split.
        """
        result = list(code)
        n = len(code)
        i = 0
        while i < n:
            two = code[i : i + 2]
            if two == "--":
                j = code.find("\n", i)
                j = n if j == -1 else j
                for k in range(i, j):
                    result[k] = " "
                i = j
            elif two == "/*":
                j = code.find("*/", i + 2)
                j = n if j == -1 else j + 2
                for k in range(i, min(j, n)):
                    if code[k] != "\n":
                        result[k] = " "
                i = j
            elif code[i] == "'":
                j = i + 1
                while j < n:
                    if code[j : j + 2] == "''":
                        j += 2
                        continue
                    if code[j] == "'":
                        j += 1
                        break
                    j += 1
                for k in range(i, min(j, n)):
                    if code[k] != "\n":
                        result[k] = " "
                i = j
            elif mask_double_quotes and code[i] == '"':
                j = i + 1
                while j < n:
                    if code[j : j + 2] == '""':
                        j += 2
                        continue
                    if code[j] == '"':
                        j += 1
                        break
                    j += 1
                for k in range(i, min(j, n)):
                    if code[k] != "\n":
                        result[k] = " "
                i = j
            elif mask_brackets and code[i] == "[":
                j = i + 1
                while j < n:
                    if code[j] == "]":
                        j += 1
                        break
                    j += 1
                for k in range(i, min(j, n)):
                    if code[k] != "\n":
                        result[k] = " "
                i = j
            else:
                i += 1
        return "".join(result)

    # ------------------------------------------------------------------
    # Object type / name detection
    # ------------------------------------------------------------------

    def detect_object_type(self, code: str, dialect: str = ORACLE) -> str:
        dialect = normalize_dialect_name(dialect)
        masked = self._mask_strings_and_comments(code)
        patterns = _OBJECT_TYPE_PATTERNS.get(dialect)
        if patterns is None:
            patterns = _OBJECT_TYPE_PATTERNS[ORACLE] + _OBJECT_TYPE_PATTERNS[TSQL]
        for obj_type, pattern in patterns:
            if pattern.search(masked):
                return obj_type
        if _ANON_BLOCK_PATTERN.search(masked):
            if dialect == ORACLE:
                return "PLSQL_BLOCK"
            if dialect == TSQL:
                return "TSQL_BLOCK"
            return "UNKNOWN"
        return "UNKNOWN"

    def _detect_object_type_with_fallback(self, code: str, dialect: str) -> tuple[str, str]:
        dialect = normalize_dialect_name(dialect)
        primary = self.detect_object_type(code, dialect=dialect)
        if primary != "UNKNOWN":
            return primary, dialect
        fallback_dialect = TSQL if dialect == ORACLE else ORACLE
        fallback = self.detect_object_type(code, dialect=fallback_dialect)
        if fallback != "UNKNOWN":
            return fallback, fallback_dialect
        return primary, dialect

    @staticmethod
    def _derive_object_type_from_filename(source_filename: str) -> str:
        stem = Path(source_filename).stem.strip()
        if not stem:
            return "UNKNOWN"

        parts = [part for part in re.split(r"[.\s_-]+", stem) if part]
        if not parts:
            return "UNKNOWN"

        type_tokens = {
            "procedure": "PROCEDURE",
            "proc": "PROCEDURE",
            "storedprocedure": "PROCEDURE",
            "function": "FUNCTION",
            "view": "VIEW",
            "trigger": "TRIGGER",
        }
        for part in reversed(parts):
            token = re.sub(r"[^A-Za-z]+", "", part).lower()
            if token in type_tokens:
                return type_tokens[token]
        return "UNKNOWN"

    @staticmethod
    def _derive_object_name_from_filename(source_filename: str) -> str:
        stem = Path(source_filename).stem.strip()
        if not stem:
            return "UNKNOWN_OBJECT"

        parts = [part for part in re.split(r"[.\s_-]+", stem) if part]
        if not parts:
            return "UNKNOWN_OBJECT"

        type_tokens = {
            "procedure",
            "proc",
            "storedprocedure",
            "function",
            "view",
            "trigger",
        }
        common_prefix_tokens = {
            "dbo",
            "pro",
            "prod",
            "dev",
            "test",
            "tmp",
            "stage",
            "stg",
            "schema",
        }
        for index in range(len(parts) - 1, -1, -1):
            token = re.sub(r"[^A-Za-z]+", "", parts[index]).lower()
            if token in type_tokens and index > 0:
                candidate_parts = parts[:index]
                if candidate_parts:
                    first_token = re.sub(r"[^A-Za-z]+", "", candidate_parts[0]).lower()
                    if first_token in common_prefix_tokens and len(candidate_parts) > 1:
                        candidate_parts = candidate_parts[1:]
                if not candidate_parts:
                    return "UNKNOWN_OBJECT"
                if len(candidate_parts) == 1:
                    return candidate_parts[0] or "UNKNOWN_OBJECT"
                if re.sub(r"[^A-Za-z]+", "", parts[0]).lower() in common_prefix_tokens:
                    candidate = "_".join(candidate_parts)
                else:
                    candidate = candidate_parts[-1]
                return candidate or "UNKNOWN_OBJECT"

        if len(parts) == 1:
            candidate = parts[0]
            if re.search(r"[A-Za-z]", candidate) and candidate.lower() not in {
                "input",
                "sample",
                "output",
                "report",
                "temp",
                "test",
            }:
                return candidate
        return "UNKNOWN_OBJECT"

    def extract_object_name(self, code: str, object_type: str, dialect: str = ORACLE) -> str:
        dialect = normalize_dialect_name(dialect)
        masked = self._mask_strings_and_comments(
            code, mask_brackets=False, mask_double_quotes=False
        )
        pattern = _NAME_PATTERNS.get(dialect, _NAME_PATTERNS[ORACLE]).get(object_type)
        if pattern:
            match = pattern.search(masked)
            if match:
                return self._normalize_object_name(match.group(1), dialect)
        if object_type in ("PLSQL_BLOCK", "TSQL_BLOCK"):
            return "ANONYMOUS_BLOCK"
        return "UNKNOWN_OBJECT"

    def extract_object_schema(self, code: str, object_type: str, dialect: str = ORACLE) -> str:
        """Returns the schema/owner qualifier from the same header match
        `extract_object_name` uses (e.g. "PRO" from `[PRO].[SMA_MARKING]`),
        or "" when the header wasn't schema-qualified or couldn't be
        matched. Deliberately mirrors `extract_object_name`'s matching so
        the two never disagree about which header they read."""
        dialect = normalize_dialect_name(dialect)
        masked = self._mask_strings_and_comments(
            code, mask_brackets=False, mask_double_quotes=False
        )
        pattern = _NAME_PATTERNS.get(dialect, _NAME_PATTERNS[ORACLE]).get(object_type)
        if pattern:
            match = pattern.search(masked)
            if match:
                schema, _ = self._split_qualified_name(match.group(1), dialect)
                return schema
        return ""

    @staticmethod
    def _clean_identifier_part(part: str, dialect: str) -> str:
        """Strips T-SQL bracket / Oracle-and-T-SQL double-quote delimiters
        from a single (already dot-split) identifier segment. Purely a
        delimiter-normalization step - never changes the letters/digits of
        the identifier itself."""
        dialect = normalize_dialect_name(dialect)
        if dialect == TSQL:
            part = part.strip("[]")
            if part.startswith('"') and part.endswith('"'):
                part = part[1:-1]
        else:
            if part.startswith('"') and part.endswith('"'):
                part = part[1:-1].replace('""', '"')
        return part

    @classmethod
    def _split_qualified_name(cls, raw_name: str, dialect: str) -> Tuple[str, str]:
        """Splits a possibly schema-qualified raw identifier (as captured
        by `_NAME_PATTERNS`) into `(schema, tail)`, with delimiters
        normalized for the given dialect. `schema` is `""` when the
        identifier was not schema-qualified. This only re-shapes the
        already-matched text from the SQL header; it never inspects the
        object name's characters to decide what the "real" name is."""
        parts = [part.strip() for part in re.split(r"\s*\.\s*", raw_name) if part.strip()]
        if not parts:
            return "", "UNKNOWN_OBJECT"
        tail = cls._clean_identifier_part(parts[-1], dialect)
        schema = cls._clean_identifier_part(parts[-2], dialect) if len(parts) > 1 else ""
        return schema, (tail or "UNKNOWN_OBJECT")

    @classmethod
    def _normalize_object_name(cls, raw_name: str, dialect: str) -> str:
        _, tail = cls._split_qualified_name(raw_name, dialect)
        return tail

    # Generic, non-domain-specific trailing suffix patterns that teams
    # commonly append to a live object's name when saving a dated,
    # versioned, or backup copy of it (e.g. `SMA_MARKING_12122023`,
    # `usp_calc_v2`, `rpt_summary_final2`, `proc_name_bak`). None of these
    # reference a specific date, object, or procedure - the same pattern
    # applies to any future object name. At most one such suffix is
    # stripped (see `derive_canonical_business_name`) to recover the
    # stable *business* identity used for report titles/filenames; the
    # raw, unmodified name is always preserved separately for exact
    # source traceability.
    _CANONICAL_SUFFIX_RE = re.compile(
        r"_(?:V|VER|VERSION)\d{1,3}$"          # _v2, _VER10, _VERSION3
        r"|_\d{8}$"                             # 8-digit date, any order (12122023)
        r"|_\d{6}$"                             # 6-digit date (121223)
        r"|_\d{4}$"                             # bare 4-digit year (2023)
        r"|_(?:BAK|BACKUP|OLD|COPY\d*|TEMP|TMP|"
        r"FINAL\d*|NEW|ARCHIVE|ARCHIVED|DEPRECATED|DRAFT|WIP|REV\d*)$",
        re.IGNORECASE,
    )

    @classmethod
    def derive_canonical_business_name(cls, raw_name: str) -> str:
        """Best-effort, fully generic normalization of a technical object
        name into the stable *business* identity used for report titles
        and output filenames.

        Teams frequently keep a "live" procedure/function/view under one
        name and periodically save dated or versioned copies of it
        (`_12122023`, `_v2`, `_backup`, `_final2`, ...). Those suffixes are
        real characters in the SQL object name, but they identify a
        *revision* of the object, not a different business object - so
        two runs against `SMA_MARKING` and `SMA_MARKING_12122023` should
        produce consistently-named business documentation.

        This strips at most a few stacked trailing suffixes matching
        `_CANONICAL_SUFFIX_RE` (e.g. `_v2_20231212`), purely by pattern -
        never a hardcoded date, object, or procedure name - and only ever
        when a non-empty, letter-containing base remains after stripping.
        If nothing matches, or stripping would leave an empty/purely
        numeric base, the original name is returned unchanged. This is a
        display-only identity: `object_name` (the raw technical name) is
        never modified and remains what reconciliation/traceability match
        against the source SQL.
        """
        name = str(raw_name or "").strip()
        if not name or name.upper() in {"UNKNOWN_OBJECT", "UNKNOWN", "ANONYMOUS_BLOCK"}:
            return name
        for _ in range(3):  # cap iterations against stacked suffixes
            match = cls._CANONICAL_SUFFIX_RE.search(name)
            if not match:
                break
            candidate = name[: match.start()]
            if not candidate or not re.search(r"[A-Za-z]", candidate):
                break
            name = candidate
        return name or str(raw_name or "").strip()

    def _extract_object_name_with_fallback(
        self, code: str, object_type: str, dialect: str
    ) -> tuple[str, str]:
        dialect = normalize_dialect_name(dialect)
        name = self.extract_object_name(code, object_type, dialect=dialect)
        if name != "UNKNOWN_OBJECT":
            return name, dialect
        fallback_dialect = TSQL if dialect == ORACLE else ORACLE
        fallback_name = self.extract_object_name(code, object_type, dialect=fallback_dialect)
        if fallback_name != "UNKNOWN_OBJECT":
            return fallback_name, fallback_dialect
        return name, dialect

    # ------------------------------------------------------------------
    # Parameter extraction
    # ------------------------------------------------------------------

    def extract_parameters(self, code: str, dialect: str = ORACLE) -> List[Parameter]:
        """Extract the formal parameter list for a procedure/function.

        Oracle: parameters live between the first matching top-level
        parentheses that follow the object name, e.g.
            PROCEDURE classify_npa (
                p_account_id IN NUMBER,
                p_status     OUT VARCHAR2
            ) IS ...

        T-SQL: parameters are introduced by "@name TYPE" pairs after the
        object name, optionally parenthesized, terminated by "AS", e.g.
            CREATE PROCEDURE dbo.classify_npa
                @p_account_id INT,
                @p_status VARCHAR(20) OUTPUT
            AS BEGIN ... END
        """
        dialect = normalize_dialect_name(dialect)
        masked = self._mask_strings_and_comments(code, mask_brackets=(dialect != TSQL))
        if dialect == TSQL:
            return self._extract_parameters_tsql(code, masked)
        return self._extract_parameters_oracle(code, masked)

    def _parameter_signature_present(self, code: str, dialect: str) -> bool:
        dialect = normalize_dialect_name(dialect)
        masked = self._mask_strings_and_comments(code, mask_brackets=(dialect != TSQL))
        if dialect == TSQL:
            header_match = re.search(
                r"(PROC(?:EDURE)?|FUNCTION)\s+" rf"({_TSQL_NAME.pattern})",
                masked,
                re.IGNORECASE,
            )
            if not header_match:
                return False
            search_start = header_match.end()
            as_match = re.search(r"\bAS\b", masked[search_start:], re.IGNORECASE)
            if not as_match:
                return False
            header_region = masked[search_start : search_start + as_match.start()]
            return "@" in header_region
        header = re.search(r"\b(?:PROCEDURE|FUNCTION)\b", masked, re.IGNORECASE)
        return bool(header and "(" in masked[header.end() :])

    def _extract_parameters_with_fallback(
        self, code: str, object_type: str, dialect: str
    ) -> tuple[List[Parameter], str, str]:
        dialect = normalize_dialect_name(dialect)
        if object_type not in ("PROCEDURE", "FUNCTION"):
            return [], "parameterless", dialect

        if dialect == TSQL:
            params, complete, saw_signature = self._extract_parameters_tsql_detailed(
                code, self._mask_strings_and_comments(code, mask_brackets=False)
            )
            if params and complete:
                return params, "parameterized", dialect
            if saw_signature and not complete:
                return [], "failed", dialect
        else:
            params = self.extract_parameters(code, dialect=dialect)
            if params:
                return params, "parameterized", dialect

        fallback_dialect = TSQL if dialect == ORACLE else ORACLE
        if fallback_dialect == TSQL:
            fallback_params, fallback_complete, fallback_saw_signature = (
                self._extract_parameters_tsql_detailed(
                    code, self._mask_strings_and_comments(code, mask_brackets=False)
                )
            )
            if fallback_params and fallback_complete:
                return fallback_params, "parameterized", fallback_dialect
            if fallback_saw_signature and not fallback_complete:
                return [], "failed", fallback_dialect
        else:
            fallback_params = self.extract_parameters(code, dialect=fallback_dialect)
            if fallback_params:
                return fallback_params, "parameterized", fallback_dialect

        if self._parameter_signature_present(code, dialect) or self._parameter_signature_present(
            code, fallback_dialect
        ):
            return [], "failed", dialect
        return [], "parameterless", dialect

    def extract_object_metadata(
        self, code: str, dialect: str = ORACLE, source_filename: str = ""
    ) -> tuple[str, str, List[Parameter], List[str], str, str]:
        dialect = normalize_dialect_name(dialect)
        warnings: List[str] = []
        object_type, object_type_dialect = self._detect_object_type_with_fallback(code, dialect)
        if object_type in {"UNKNOWN", "PLSQL_BLOCK", "TSQL_BLOCK"}:
            filename_object_type = self._derive_object_type_from_filename(source_filename)
            if filename_object_type != "UNKNOWN":
                prior_type = object_type
                object_type = filename_object_type
                object_type_dialect = "filename"
                if prior_type in {"PLSQL_BLOCK", "TSQL_BLOCK"}:
                    warnings.append(
                        "Database object type was recovered from the source filename because the "
                        "source body looked like a generic procedural block and the filename carried "
                        "a clearer object type."
                    )
                else:
                    warnings.append(
                        "Database object type was recovered from the source filename because the "
                        "header could not be parsed deterministically."
                    )
            else:
                warnings.append(
                    "Could not deterministically identify the database object type from the raw source."
                )
        elif object_type_dialect != dialect:
            warnings.append(
                f"Object type was identified using a {object_type_dialect.upper()} fallback because "
                f"the primary {dialect.upper()} pass did not match the header cleanly."
            )

        object_name, object_name_dialect = self._extract_object_name_with_fallback(
            code, object_type, object_type_dialect
        )
        object_name_status = "verified"
        if object_name == "UNKNOWN_OBJECT":
            filename_object_name = self._derive_object_name_from_filename(source_filename)
            if filename_object_name != "UNKNOWN_OBJECT":
                object_name = filename_object_name
                object_name_dialect = "filename"
                warnings.append(
                    "Database object name was recovered from the source filename because the "
                    "header could not be parsed deterministically."
                )
            else:
                object_name_status = "failed"
                warnings.append(
                    "Could not deterministically identify the database object name from the raw source."
                )
        elif object_name_dialect != object_type_dialect:
            warnings.append(
                f"Object name was identified using a {object_name_dialect.upper()} fallback because "
                "the primary dialect header pattern did not match cleanly."
            )

        parameter_dialect_hint = (
            object_name_dialect
            if object_name_dialect in (ORACLE, TSQL)
            else (object_type_dialect if object_type_dialect in (ORACLE, TSQL) else dialect)
        )
        parameters, parameter_status, parameter_dialect = self._extract_parameters_with_fallback(
            code, object_type, parameter_dialect_hint
        )
        if parameter_status == "failed":
            warnings.append(
                "Parameter extraction failed for a parameterized object header; the object is not "
                "known to be parameterless."
            )
        elif parameter_status == "parameterized" and parameter_dialect != object_name_dialect:
            warnings.append(
                f"Parameters were extracted using a {parameter_dialect.upper()} fallback because "
                "the primary dialect pass did not capture the formal parameter list cleanly."
            )

        return object_type, object_name, parameters, warnings, object_name_status, parameter_status

    def _extract_parameters_oracle(self, code: str, masked: str) -> List[Parameter]:
        header_match = re.search(
            r"(PROCEDURE|FUNCTION)\s+"
            rf"({_ORACLE_NAME.pattern})\s*\(",
            masked,
            re.IGNORECASE,
        )
        if not header_match:
            return []

        start = header_match.end()
        depth = 1
        end = start
        for i, ch in enumerate(masked[start:], start=start):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        param_block = code[start:end]

        params_raw = self._split_top_level_commas(param_block)

        parameters: List[Parameter] = []
        for raw in params_raw:
            raw = raw.strip()
            if not raw:
                continue
            m = _PARAM_LINE_ORACLE.match(raw)
            if m:
                name, direction, datatype = m.groups()
                parameters.append(
                    Parameter(
                        name=name,
                        direction=(direction or "IN").upper(),
                        datatype=datatype.upper(),
                    )
                )
        return parameters

    def _extract_parameters_tsql(self, code: str, masked: str) -> List[Parameter]:
        params, _, _ = self._extract_parameters_tsql_detailed(code, masked)
        return params

    def _extract_parameters_tsql_detailed(
        self, code: str, masked: str
    ) -> tuple[List[Parameter], bool, bool]:
        header_match = re.search(
            r"(PROC(?:EDURE)?|FUNCTION)\s+" rf"({_TSQL_NAME.pattern})",
            masked,
            re.IGNORECASE,
        )
        if not header_match:
            return [], True, False

        # Parameter list runs from right after the object name up to the
        # first top-level "AS" keyword (parentheses are optional in T-SQL).
        search_start = header_match.end()
        as_match = re.search(r"\bAS\b", masked[search_start:], re.IGNORECASE)
        if not as_match:
            return [], False, True
        param_block_masked = masked[search_start : search_start + as_match.start()]
        param_block = code[search_start : search_start + as_match.start()]

        header_option_match = re.search(
            r"(?im)^\s*(?:WITH\s+RECOMPILE|WITH\s+ENCRYPTION|WITH\s+SCHEMABINDING|"
            r"WITH\s+NATIVE_COMPILATION|WITH\s+EXECUTE\s+AS|EXECUTE\s+AS|FOR\s+REPLICATION|"
            r"RETURNS\s+NULL\s+ON\s+NULL\s+INPUT|CALLED\s+ON\s+NULL\s+INPUT)\b",
            param_block_masked,
        )
        if header_option_match:
            param_block_masked = param_block_masked[: header_option_match.start()]
            param_block = param_block[: header_option_match.start()]

        # Strip an optional wrapping "(" ... ")" if present.
        stripped = param_block_masked.strip()
        if stripped.startswith("(") and stripped.endswith(")"):
            offset = param_block_masked.index("(") + 1
            end_offset = param_block_masked.rindex(")")
            param_block = param_block[offset:end_offset]

        params_raw = self._split_top_level_commas(param_block)

        parameters: List[Parameter] = []
        saw_candidate = False
        complete = True
        for raw in params_raw:
            raw = raw.strip()
            if not raw:
                continue
            if self._is_tsql_header_option_fragment(raw):
                continue
            if not raw.startswith("@"):
                complete = False
                continue
            saw_candidate = True
            m = _PARAM_LINE_TSQL.match(raw)
            if m:
                name, datatype, out_kw = m.groups()
                direction = "OUT" if out_kw else "IN"
                parameters.append(
                    Parameter(name=name, direction=direction, datatype=datatype.upper())
                )
            else:
                complete = False
        if saw_candidate and not complete:
            return parameters, False, True
        return parameters, complete, saw_candidate

    @staticmethod
    def _is_tsql_header_option_fragment(fragment: str) -> bool:
        normalized = re.sub(r"\s+", " ", fragment.strip()).upper()
        if not normalized:
            return False
        header_option_prefixes = (
            "WITH RECOMPILE",
            "WITH ENCRYPTION",
            "WITH SCHEMABINDING",
            "WITH NATIVE_COMPILATION",
            "WITH EXECUTE AS",
            "EXECUTE AS",
            "FOR REPLICATION",
            "RETURNS NULL ON NULL INPUT",
            "CALLED ON NULL INPUT",
        )
        return any(normalized.startswith(prefix) for prefix in header_option_prefixes)

    @staticmethod
    def _split_top_level_commas(text: str) -> List[str]:
        """Split on commas that are not nested inside parentheses (e.g.
        NUMBER(10,2) or DECIMAL(18,2) must not be split internally).
        """
        parts: List[str] = []
        depth = 0
        buf = ""
        for ch in text:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append(buf)
                buf = ""
            else:
                buf += ch
        if buf.strip():
            parts.append(buf)
        return parts

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def chunk_code(
        self,
        code: str,
        warnings: List[str],
        dialect: str = ORACLE,
        source_filename: str = "",
        source_text: Optional[str] = None,
    ) -> List[CodeChunk]:
        """Split procedural code into logically coherent, context-preserving
        sections, then greedily merge adjacent small sections back together
        (up to `max_chunk_chars`) so a typical object produces only a
        handful of chunks - and therefore a handful of LLM calls - instead
        of one call per tiny declaration/cursor/nested-block fragment.
        Any section that is still too large on its own is split further on
        statement boundaries as a fallback.
        """
        dialect = normalize_dialect_name(dialect)
        batches = self._split_batches(code, dialect)
        source_text = source_text or code
        source_cursor = 0
        source_line_starts = self._line_start_offsets(source_text)

        sections: List[Tuple[str, str]] = []
        for batch_idx, batch_text in enumerate(batches):
            if not batch_text.strip():
                continue
            batch_sections = self._split_logical_sections(batch_text, dialect)
            if len(batches) > 1:
                sections.extend(
                    (f"batch{batch_idx}_{kind}", text) for kind, text in batch_sections
                )
            else:
                sections.extend(batch_sections)

        merged_sections = self._merge_small_sections(sections)

        chunks: List[CodeChunk] = []
        for idx, (kind, text) in enumerate(merged_sections):
            section_start, section_end = self._locate_text_span(source_text, text, source_cursor)
            if section_start >= 0:
                source_cursor = section_end
            for sub_idx, sub_text in enumerate(self._enforce_size_limit(text)):
                chunk_id = f"{idx:02d}_{kind}" + (f"_{sub_idx}" if sub_idx else "")
                embedded_sql = self._extract_and_validate_sql(sub_text, warnings, dialect)
                sub_start, sub_end = self._locate_text_span(text, sub_text)
                if section_start >= 0 and sub_start >= 0:
                    global_start = section_start + sub_start
                    global_end = section_start + sub_end
                    line_start = self._line_number_for_offset(source_line_starts, global_start)
                    line_end = self._line_number_for_offset(source_line_starts, max(global_end - 1, global_start))
                    location_status = "available"
                else:
                    global_start = -1
                    global_end = -1
                    line_start = -1
                    line_end = -1
                    location_status = "unavailable"
                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        kind=kind,
                        text=sub_text,
                        embedded_sql=embedded_sql,
                        context_path=self._build_context_path(kind),
                        source_filename=source_filename,
                        source_char_start=global_start,
                        source_char_end=global_end,
                        source_line_start=line_start,
                        source_line_end=line_end,
                        source_location_status=location_status,
                    )
                )
        return chunks

    @staticmethod
    def _line_start_offsets(text: str) -> List[int]:
        offsets = [0]
        for idx, char in enumerate(text):
            if char == "\n" and idx + 1 < len(text):
                offsets.append(idx + 1)
        return offsets

    @staticmethod
    def _line_number_for_offset(line_starts: List[int], offset: int) -> int:
        if offset < 0:
            return -1
        # `line_starts` is kept for backward compatibility with callers
        # that already precomputed it, but the line number itself is
        # derived directly from the source offset so it stays correct
        # even when the source text contains repeated line starts or
        # partial sections.
        source_text_line_index = 0
        for start in line_starts:
            if start > offset:
                break
            source_text_line_index += 1
        return max(1, source_text_line_index)

    @staticmethod
    def _locate_text_span(source_text: str, snippet: str, start_at: int = 0) -> Tuple[int, int]:
        if not source_text or not snippet:
            return -1, -1
        snippet_text = str(snippet).strip()
        if not snippet_text:
            return -1, -1
        start = source_text.find(snippet_text, max(0, start_at))
        if start < 0 and snippet_text != snippet:
            start = source_text.find(str(snippet), max(0, start_at))
            if start >= 0:
                snippet_text = str(snippet)
        if start < 0:
            return -1, -1
        return start, start + len(snippet_text)

    def _split_batches(self, code: str, dialect: str) -> List[str]:
        """Split on "GO" batch separators (T-SQL only). Every batch is
        preserved and later chunked - no batch is discarded, even
        preamble batches like "USE db;" - so no source information is
        lost, per the preprocessing requirement to retain everything
        relevant to business-rule extraction.
        """
        dialect = normalize_dialect_name(dialect)
        if dialect != TSQL:
            return [code]
        masked = self._mask_strings_and_comments(code)
        split_points = [m.start() for m in _GO_BATCH_SPLIT.finditer(masked)]
        if not split_points:
            return [code]

        batches: List[str] = []
        last_end = 0
        for m in _GO_BATCH_SPLIT.finditer(masked):
            batches.append(code[last_end : m.start()])
            last_end = m.end()
        batches.append(code[last_end:])
        return [b for b in batches if b.strip()]

    def _merge_small_sections(self, sections: List[tuple]) -> List[tuple]:
        """Greedily coalesce consecutive (kind, text) sections into fewer,
        larger sections, never exceeding `max_chunk_chars` per merged
        section. This is what keeps the number of downstream LLM calls
        proportional to the object's actual size rather than to how many
        structural regions it happens to have.
        """
        if not sections:
            return []

        merged: List[tuple] = []
        current_kind: Optional[str] = None
        current_text = ""

        for kind, text in sections:
            candidate_text = f"{current_text}\n\n{text}" if current_text else text
            if current_kind == kind and len(candidate_text) <= self.max_chunk_chars:
                current_text = candidate_text
                continue
            if current_text:
                merged.append((current_kind or kind, current_text))
            current_kind = kind
            current_text = text

        if current_text:
            merged.append((current_kind or "main_body", current_text))

        return merged

    def _build_context_path(self, kind: str) -> List[str]:
        if kind.startswith("batch") and "_" in kind:
            batch_label, remainder = kind.split("_", 1)
            return [batch_label] + [part for part in remainder.split("+") if part]
        return [part for part in kind.split("+") if part]

    def _split_logical_sections(self, code: str, dialect: str = ORACLE) -> List[tuple]:
        """Heuristic structural split into (kind, text) tuples:
        declaration / cursor / main_body / exception / nested_block.
        Structural boundaries are located on a masked (comment/string
        blanked) copy of `code`, but the returned text slices are always
        taken from the original, unmasked `code`.
        """
        dialect = normalize_dialect_name(dialect)
        masked = self._mask_strings_and_comments(code)

        decl_match = re.search(r"\bIS\b|\bAS\b", masked, re.IGNORECASE)
        exc_start = self._find_top_level_exception_start(masked, dialect)
        begin_match = re.search(r"\bBEGIN\b", masked, re.IGNORECASE)

        decl_start = decl_match.end() if decl_match else 0
        begin_start = begin_match.start() if begin_match else len(code)
        exc_start = exc_start if exc_start is not None else len(code)

        sections: List[tuple] = []

        # Declaration section (includes cursor declarations)
        declaration_text = code[decl_start:begin_start].strip()
        declaration_text_masked = masked[decl_start:begin_start]
        if declaration_text:
            cursor_pattern = re.compile(r"CURSOR\s+\w+.*?;", re.IGNORECASE | re.DOTALL)
            cursor_blocks = list(cursor_pattern.finditer(declaration_text_masked))
            if cursor_blocks:
                last_end = 0
                for cb in cursor_blocks:
                    pre = code[decl_start + last_end : decl_start + cb.start()].strip()
                    if pre:
                        sections.append(("declaration", pre))
                    sections.append(
                        ("cursor", code[decl_start + cb.start() : decl_start + cb.end()])
                    )
                    last_end = cb.end()
                tail = code[decl_start + last_end : begin_start].strip()
                if tail:
                    sections.append(("declaration", tail))
            else:
                sections.append(("declaration", declaration_text))

        # Main executable body (BEGIN ... up to EXCEPTION/CATCH or END)
        body_end = exc_start if exc_start > begin_start else len(code)
        main_body = code[begin_start:body_end].strip()
        if main_body:
            for nested_kind, nested_text in self._split_nested_blocks(main_body):
                sections.append((nested_kind, nested_text))

        # Exception handling section (Oracle EXCEPTION block or T-SQL
        # BEGIN CATCH region, whichever this dialect uses)
        if exc_start < len(code):
            exception_text = code[exc_start:].strip()
            if exception_text:
                sections.append(("exception", exception_text))

        if not sections:
            sections.append(("main_body", code.strip()))

        return sections

    def _split_nested_blocks(self, body: str) -> List[tuple]:
        """Within the main body, separate out nested BEGIN...END sub-blocks
        (e.g. inner blocks used for localized error handling) from the
        top-level statements, so each can be chunked/interpreted with
        appropriate context. Boundaries are located on a masked copy;
        slices are always taken from the real, unmasked `body` text.
        """
        masked_body = self._mask_strings_and_comments(body)
        results: List[tuple] = []
        begin_depth = 0
        case_depth = 0
        child_start: Optional[int] = None
        last_end = 0
        i = 0
        n = len(masked_body)

        def next_word(idx: int) -> str:
            match = re.match(r"\b([A-Z_]+)\b", masked_body[idx:], re.IGNORECASE)
            return match.group(1).upper() if match else ""

        while i < n:
            begin_match = re.match(r"\bBEGIN\b", masked_body[i:], re.IGNORECASE)
            if begin_match:
                begin_depth += 1
                if begin_depth == 2 and child_start is None:
                    child_start = i
                i += begin_match.end()
                continue

            case_match = re.match(r"\bCASE\b", masked_body[i:], re.IGNORECASE)
            if case_match:
                case_depth += 1
                i += case_match.end()
                continue

            end_match = re.match(r"\bEND\b", masked_body[i:], re.IGNORECASE)
            if end_match:
                suffix = next_word(i + end_match.end())
                if case_depth > 0 and suffix not in {"IF", "LOOP", "WHILE", "TRY", "CATCH", "CASE"}:
                    case_depth = max(case_depth - 1, 0)
                    i += end_match.end()
                    continue

                if suffix in {"IF", "LOOP", "WHILE", "TRY", "CATCH", "CASE"}:
                    i += end_match.end() + len(suffix)
                    continue

                if begin_depth == 2 and child_start is not None:
                    pre = body[last_end:child_start].strip()
                    if pre:
                        results.append(("main_body", pre))
                    results.append(("nested_block", body[child_start : i + end_match.end()]))
                    last_end = i + end_match.end()
                    child_start = None
                begin_depth = max(begin_depth - 1, 0)
                i += end_match.end()
                continue

            i += 1

        if not results:
            return [("main_body", body)]

        tail = body[last_end:].strip()
        if tail:
            results.append(("main_body", tail))
        return results or [("main_body", body)]

    @staticmethod
    def _find_top_level_exception_start(masked: str, dialect: str) -> Optional[int]:
        """Return the first top-level exception/catch section start.

        PL/SQL uses `EXCEPTION`; T-SQL uses `BEGIN CATCH`. We look for the
        first match that appears at the same BEGIN-depth as the outer
        object body, so nested exception handlers do not prematurely end
        the main body split.
        """
        dialect = normalize_dialect_name(dialect)
        begin_depth = 0
        case_depth = 0
        i = 0
        n = len(masked)

        def next_word(idx: int) -> str:
            match = re.match(r"\b([A-Z_]+)\b", masked[idx:], re.IGNORECASE)
            return match.group(1).upper() if match else ""

        while i < n:
            if dialect == TSQL:
                begin_catch = re.match(r"\bBEGIN\s+CATCH\b", masked[i:], re.IGNORECASE)
                if begin_catch and begin_depth <= 1:
                    return i
            else:
                exception = re.match(r"\bEXCEPTION\b", masked[i:], re.IGNORECASE)
                if exception and begin_depth <= 1:
                    return i

            begin_match = re.match(r"\bBEGIN\b", masked[i:], re.IGNORECASE)
            if begin_match:
                begin_depth += 1
                i += begin_match.end()
                continue

            case_match = re.match(r"\bCASE\b", masked[i:], re.IGNORECASE)
            if case_match:
                case_depth += 1
                i += case_match.end()
                continue

            end_match = re.match(r"\bEND\b", masked[i:], re.IGNORECASE)
            if end_match:
                suffix = next_word(i + end_match.end())
                if case_depth > 0 and suffix not in {"IF", "LOOP", "WHILE", "TRY", "CATCH", "CASE"}:
                    case_depth = max(case_depth - 1, 0)
                    i += end_match.end()
                    continue

                if suffix in {"IF", "LOOP", "WHILE", "TRY", "CATCH", "CASE"}:
                    i += end_match.end() + len(suffix)
                    continue

                begin_depth = max(begin_depth - 1, 0)
                i += end_match.end()
                continue

            i += 1

        return None

    def _enforce_size_limit(self, text: str) -> List[str]:
        if len(text) <= self.max_chunk_chars:
            return [text]

        # Keep a modestly oversized control-flow block intact when it
        # clearly contains IF/ELSE or CASE logic. Splitting these
        # branches apart is worse for downstream rule extraction than a
        # small, controlled overflow, so we only fall back to splitting
        # when the section is genuinely too large to keep whole.
        soft_limit = int(self.max_chunk_chars * 1.25)
        masked = self._mask_strings_and_comments(text)
        if len(text) <= soft_limit and (
            (re.search(r"\bIF\b", masked, re.IGNORECASE) and re.search(r"\bELSE\b", masked, re.IGNORECASE))
            or re.search(r"\bCASE\b", masked, re.IGNORECASE)
        ):
            return [text]

        # Split at real top-level statement boundaries (keyword- and
        # parenthesis-depth-aware, not ';'-based - a lot of legacy T-SQL
        # has few or no semicolon terminators at all, which made the
        # previous ';'-only split a silent no-op and forced everything
        # through the raw line/character hard-wrap below, which does not
        # know where a statement or a multi-line CASE expression ends and
        # can truncate mid-expression or even mid-word). This split is
        # gap-free by construction - every character of `text` still ends
        # up in exactly one statement piece.
        spans = split_top_level_statement_spans(text, masked)
        statements = [text[start:end] for start, end in spans] or [text]

        pieces: List[str] = []
        buf = ""
        for stmt in statements:
            if len(buf) + len(stmt) > self.max_chunk_chars and buf:
                pieces.append(buf)
                buf = stmt
            else:
                buf += ("\n" if buf else "") + stmt
        if buf:
            pieces.append(buf)
        if not pieces:
            pieces = [text]

        # A single top-level statement can still be larger than the
        # ceiling on its own (e.g. one enormous CASE expression) - hard-
        # wrap on line boundaries as the last resort so no chunk sent
        # downstream ever exceeds the ceiling, regardless of how few
        # statement boundaries it contains.
        final_pieces: List[str] = []
        for piece in pieces:
            final_pieces.extend(self._hard_wrap_on_lines(piece))
        return final_pieces

    def _hard_wrap_on_lines(self, text: str) -> List[str]:
        if len(text) <= self.max_chunk_chars:
            return [text]
        lines = text.split("\n")
        pieces: List[str] = []
        buf = ""
        for line in lines:
            candidate = f"{buf}\n{line}" if buf else line
            if len(candidate) > self.max_chunk_chars and buf:
                pieces.append(buf)
                buf = line
            else:
                buf = candidate
            # A single line longer than the ceiling on its own (no
            # newlines to split on) - hard-cut it as a last resort.
            while len(buf) > self.max_chunk_chars:
                pieces.append(buf[: self.max_chunk_chars])
                buf = buf[self.max_chunk_chars :]
        if buf:
            pieces.append(buf)
        return pieces or [text]

    # ------------------------------------------------------------------
    # Embedded SQL validation via sqlglot
    # ------------------------------------------------------------------

    def _extract_and_validate_sql(
        self, text: str, warnings: List[str], dialect: str = ORACLE
    ) -> List[str]:
        """Pull out SELECT/INSERT/UPDATE/DELETE/MERGE statements embedded in
        a procedural chunk and validate them structurally with sqlglot,
        using the dialect detected for this object. Dynamic SQL (Oracle
        EXECUTE IMMEDIATE, T-SQL EXEC()/sp_executesql) content is
        flagged, not parsed, since its true text is often only known at
        runtime.
        """
        dialect = normalize_dialect_name(dialect)
        masked = self._mask_strings_and_comments(text)

        dynamic_pattern = _DYNAMIC_SQL_TSQL if dialect == TSQL else _DYNAMIC_SQL_ORACLE
        for hit in dynamic_pattern.finditer(masked):
            snippet = text[hit.start() : min(len(text), hit.start() + 120)].strip()
            warnings.append(
                "Dynamic SQL detected and cannot be fully statically resolved: "
                f"{snippet or 'dynamic construct'}..."
            )

        validated: List[str] = []
        if dialect not in (ORACLE, TSQL):
            warnings.append(
                "Dialect-specific SQL parsing was unavailable for this object; embedded SQL is preserved "
                "as source text without structural validation."
            )
            return []

        sqlglot_dialect = "tsql" if dialect == TSQL else "oracle"
        for start, end in self._find_sql_statement_spans(masked):
            stmt = text[start:end].strip()
            if not stmt:
                continue
            try:
                sqlglot.parse_one(stmt, read=sqlglot_dialect)
                validated.append(stmt)
                continue
            except ParseError:
                pass

            commentless_stmt = re.sub(r"/\*.*?\*/", " ", stmt, flags=re.DOTALL)
            commentless_stmt = re.sub(r"--[^\n]*", " ", commentless_stmt)
            try:
                sqlglot.parse_one(commentless_stmt, read=sqlglot_dialect)
                validated.append(stmt)
                continue
            except ParseError:
                pass

            parsed = False
            if re.match(r"^\s*CASE\b", stmt, re.IGNORECASE):
                try:
                    sqlglot.parse_one(f"SELECT {stmt}", read=sqlglot_dialect)
                    parsed = True
                except ParseError:
                    parsed = False

            if parsed:
                validated.append(stmt)
                continue

            warnings.append(
                "Could not fully structurally parse embedded SQL statement "
                f"(non-fatal, passed through as raw text): {stmt[:120].strip()}..."
            )
            validated.append(stmt)
        return validated

    @staticmethod
    def _find_sql_statement_spans(masked: str) -> List[Tuple[int, int]]:
        """Return top-level SQL statement spans from masked source text.

        CTEs starting with WITH are captured, and nested subqueries are
        skipped because spans only begin at depth 0.
        """
        spans: List[Tuple[int, int]] = []
        n = len(masked)
        keyword_re = re.compile(
            r"\b(WITH|SELECT|INSERT|UPDATE|DELETE|MERGE|SET|CASE)\b",
            re.IGNORECASE,
        )
        depth = 0
        i = 0
        start = None

        def prev_nonspace(idx: int) -> int:
            j = idx - 1
            while j >= 0 and masked[j] in " \t\r":
                j -= 1
            return j

        while i < n:
            ch = masked[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif depth == 0:
                if start is None:
                    m = keyword_re.match(masked, i)
                    if m:
                        prev = prev_nonspace(i)
                        if prev < 0 or masked[prev] in ";\n":
                            start = i
                            i = m.end() - 1
                elif ch == ";" and depth == 0:
                    spans.append((start, i + 1))
                    start = None
            i += 1

        if start is not None:
            spans.append((start, n))

        return spans