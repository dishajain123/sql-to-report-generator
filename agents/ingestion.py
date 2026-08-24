"""
agents/ingestion.py
--------------------
Code Ingestion Agent.

Responsibilities
-----------------
1. Read a raw .sql / .prc file containing exactly one banking DB object
   (procedure, function, view, trigger, or a standalone PL/SQL block).
2. Identify the object type and its name.
3. Extract the formal parameter list (name / direction / datatype) for
   procedures & functions.
4. Use `sqlglot` to structurally validate/parse the embedded SQL
   statements (SELECT / INSERT / UPDATE / DELETE / MERGE) that live
   inside the procedural body. sqlglot does not understand PL/SQL
   control-flow (IF/LOOP/CURSOR/EXCEPTION) natively, so those regions
   are chunked using structural/regex heuristics instead.
5. Split large objects into logical, context-preserving chunks
   (declaration section, per-cursor blocks, main executable body,
   nested blocks, exception section) so that no chunk sent downstream
   ever risks overflowing the LLM's context window.

Nothing in this module talks to an LLM - it is a pure, deterministic
pre-processing stage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import sqlglot
from sqlglot.errors import ParseError

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


@dataclass
class IngestionResult:
    object_name: str
    object_type: str  # PROCEDURE | FUNCTION | VIEW | TRIGGER | PLSQL_BLOCK | UNKNOWN
    parameters: List[Parameter]
    raw_code: str
    chunks: List[CodeChunk]
    parse_warnings: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

MAX_CHUNK_CHARS = 3000  # ceiling per chunk sent to the LLM - generous headroom
# given modern Groq context windows, chosen to minimize the number of LLM
# calls per object while still keeping any single call well within budget.

_OBJECT_TYPE_PATTERNS = [
    ("PROCEDURE", re.compile(r"\bCREATE\s+(OR\s+REPLACE\s+)?PROCEDURE\b", re.IGNORECASE)),
    ("FUNCTION", re.compile(r"\bCREATE\s+(OR\s+REPLACE\s+)?FUNCTION\b", re.IGNORECASE)),
    ("TRIGGER", re.compile(r"\bCREATE\s+(OR\s+REPLACE\s+)?TRIGGER\b", re.IGNORECASE)),
    ("VIEW", re.compile(r"\bCREATE\s+(OR\s+REPLACE\s+)?(FORCE\s+)?VIEW\b", re.IGNORECASE)),
]

_ANON_BLOCK_PATTERN = re.compile(r"^\s*DECLARE\b|^\s*BEGIN\b", re.IGNORECASE)

_NAME_PATTERNS = {
    "PROCEDURE": re.compile(r"PROCEDURE\s+([A-Za-z0-9_\".$]+)", re.IGNORECASE),
    "FUNCTION": re.compile(r"FUNCTION\s+([A-Za-z0-9_\".$]+)", re.IGNORECASE),
    "TRIGGER": re.compile(r"TRIGGER\s+([A-Za-z0-9_\".$]+)", re.IGNORECASE),
    "VIEW": re.compile(r"VIEW\s+([A-Za-z0-9_\".$]+)", re.IGNORECASE),
}

# Matches a single formal parameter inside a (....) parameter list, e.g.
#   p_account_id IN NUMBER
#   p_result OUT VARCHAR2
_PARAM_LINE = re.compile(
    r"^\s*([A-Za-z0-9_\"$]+)\s+"
    r"(IN\s+OUT|IN|OUT)?\s*"
    r"([A-Za-z0-9_.]+(?:\([^)]*\))?)",
    re.IGNORECASE,
)


class CodeIngestionAgent:
    """Deterministic parsing / chunking front-door of the pipeline."""

    def __init__(self, max_chunk_chars: int = MAX_CHUNK_CHARS):
        self.max_chunk_chars = max_chunk_chars

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, file_path: str) -> IngestionResult:
        raw_code = self._load_file(file_path)
        object_type = self.detect_object_type(raw_code)
        object_name = self.extract_object_name(raw_code, object_type)
        parameters = self.extract_parameters(raw_code) if object_type in (
            "PROCEDURE",
            "FUNCTION",
        ) else []

        warnings: List[str] = []
        chunks = self.chunk_code(raw_code, warnings)

        return IngestionResult(
            object_name=object_name,
            object_type=object_type,
            parameters=parameters,
            raw_code=raw_code,
            chunks=chunks,
            parse_warnings=warnings,
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
        return path.read_text(encoding="utf-8", errors="replace")

    # ------------------------------------------------------------------
    # Object type / name detection
    # ------------------------------------------------------------------

    def detect_object_type(self, code: str) -> str:
        for obj_type, pattern in _OBJECT_TYPE_PATTERNS:
            if pattern.search(code):
                return obj_type
        if _ANON_BLOCK_PATTERN.search(code):
            return "PLSQL_BLOCK"
        return "UNKNOWN"

    def extract_object_name(self, code: str, object_type: str) -> str:
        pattern = _NAME_PATTERNS.get(object_type)
        if pattern:
            match = pattern.search(code)
            if match:
                return match.group(1).strip('"')
        return "ANONYMOUS_BLOCK" if object_type == "PLSQL_BLOCK" else "UNKNOWN_OBJECT"

    # ------------------------------------------------------------------
    # Parameter extraction
    # ------------------------------------------------------------------

    def extract_parameters(self, code: str) -> List[Parameter]:
        """Extract the formal parameter list between the first matching
        top-level parentheses that follow the object name, e.g.

            PROCEDURE classify_npa (
                p_account_id IN NUMBER,
                p_status     OUT VARCHAR2
            ) IS ...
        """
        header_match = re.search(
            r"(PROCEDURE|FUNCTION)\s+[A-Za-z0-9_\".$]+\s*\(", code, re.IGNORECASE
        )
        if not header_match:
            return []

        start = header_match.end()
        depth = 1
        end = start
        for i, ch in enumerate(code[start:], start=start):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        param_block = code[start:end]

        # Split on commas that are not inside nested parens (e.g. NUMBER(10,2))
        params_raw: List[str] = []
        depth = 0
        buf = ""
        for ch in param_block:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                params_raw.append(buf)
                buf = ""
            else:
                buf += ch
        if buf.strip():
            params_raw.append(buf)

        parameters: List[Parameter] = []
        for raw in params_raw:
            raw = raw.strip()
            if not raw:
                continue
            m = _PARAM_LINE.match(raw)
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

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def chunk_code(self, code: str, warnings: List[str]) -> List[CodeChunk]:
        """Split procedural code into logically coherent, context-preserving
        sections, then greedily merge adjacent small sections back together
        (up to `max_chunk_chars`) so a typical object produces only a
        handful of chunks - and therefore a handful of LLM calls - instead
        of one call per tiny declaration/cursor/nested-block fragment.
        Any section that is still too large on its own is split further on
        statement boundaries as a fallback.
        """
        sections = self._split_logical_sections(code)
        merged_sections = self._merge_small_sections(sections)

        chunks: List[CodeChunk] = []
        for idx, (kind, text) in enumerate(merged_sections):
            for sub_idx, sub_text in enumerate(self._enforce_size_limit(text)):
                chunk_id = f"{idx:02d}_{kind}" + (f"_{sub_idx}" if sub_idx else "")
                embedded_sql = self._extract_and_validate_sql(sub_text, warnings)
                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        kind=kind,
                        text=sub_text,
                        embedded_sql=embedded_sql,
                    )
                )
        return chunks

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
        current_kinds: List[str] = []
        current_text = ""

        for kind, text in sections:
            candidate_text = f"{current_text}\n\n{text}" if current_text else text
            if current_text and len(candidate_text) > self.max_chunk_chars:
                merged.append(("+".join(current_kinds), current_text))
                current_kinds = [kind]
                current_text = text
            else:
                current_kinds.append(kind)
                current_text = candidate_text

        if current_text:
            merged.append(("+".join(current_kinds), current_text))

        return merged

    def _split_logical_sections(self, code: str) -> List[tuple]:
        """Heuristic structural split into (kind, text) tuples:
        declaration / cursor / main_body / exception / nested_block.
        """
        sections: List[tuple] = []

        decl_match = re.search(r"\bIS\b|\bAS\b", code, re.IGNORECASE)
        exc_match = re.search(r"\bEXCEPTION\b", code, re.IGNORECASE)
        begin_match = re.search(r"\bBEGIN\b", code, re.IGNORECASE)

        decl_start = decl_match.end() if decl_match else 0
        begin_start = begin_match.start() if begin_match else len(code)
        exc_start = exc_match.start() if exc_match else len(code)

        # Declaration section (includes cursor declarations)
        declaration_text = code[decl_start:begin_start].strip()
        if declaration_text:
            cursor_blocks = list(
                re.finditer(r"CURSOR\s+\w+.*?;", declaration_text, re.IGNORECASE | re.DOTALL)
            )
            if cursor_blocks:
                last_end = 0
                for cb in cursor_blocks:
                    pre = declaration_text[last_end:cb.start()].strip()
                    if pre:
                        sections.append(("declaration", pre))
                    sections.append(("cursor", cb.group(0)))
                    last_end = cb.end()
                tail = declaration_text[last_end:].strip()
                if tail:
                    sections.append(("declaration", tail))
            else:
                sections.append(("declaration", declaration_text))

        # Main executable body (BEGIN ... up to EXCEPTION or END)
        body_end = exc_start if exc_start > begin_start else len(code)
        main_body = code[begin_start:body_end].strip()
        if main_body:
            for nested_kind, nested_text in self._split_nested_blocks(main_body):
                sections.append((nested_kind, nested_text))

        # Exception handling section
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
        appropriate context.
        """
        nested_pattern = re.compile(
            r"\bBEGIN\b.*?\bEND\s*;", re.IGNORECASE | re.DOTALL
        )
        matches = list(nested_pattern.finditer(body))
        # The outermost BEGIN...END often spans the whole body; only treat
        # matches that are *not* the entire body as "nested".
        results: List[tuple] = []
        if len(matches) <= 1:
            return [("main_body", body)]

        last_end = 0
        for m in matches[:-1]:  # last match usually closes the outer block
            pre = body[last_end:m.start()].strip()
            if pre:
                results.append(("main_body", pre))
            results.append(("nested_block", m.group(0)))
            last_end = m.end()
        tail = body[last_end:].strip()
        if tail:
            results.append(("main_body", tail))
        return results or [("main_body", body)]

    def _enforce_size_limit(self, text: str) -> List[str]:
        if len(text) <= self.max_chunk_chars:
            return [text]
        # split on statement terminators (';') keeping chunks under the limit
        statements = [s.strip() + ";" for s in text.split(";") if s.strip()]
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
        return pieces or [text]

    # ------------------------------------------------------------------
    # Embedded SQL validation via sqlglot
    # ------------------------------------------------------------------

    def _extract_and_validate_sql(self, text: str, warnings: List[str]) -> List[str]:
        """Pull out SELECT/INSERT/UPDATE/DELETE/MERGE statements embedded in
        a procedural chunk and validate them structurally with sqlglot.
        Dynamic SQL (EXECUTE IMMEDIATE) content is flagged, not parsed,
        since its true text is often only known at runtime.
        """
        dynamic_sql_hits = re.findall(
            r"EXECUTE\s+IMMEDIATE\s+.*?;", text, re.IGNORECASE | re.DOTALL
        )
        for hit in dynamic_sql_hits:
            warnings.append(
                "Dynamic SQL (EXECUTE IMMEDIATE) detected and cannot be fully "
                f"statically resolved: {hit[:120].strip()}..."
            )

        candidates = re.findall(
            r"(SELECT|INSERT|UPDATE|DELETE|MERGE)\b.*?;",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        validated: List[str] = []
        # re.findall with a capturing group only returns the group; redo without one
        candidates = re.findall(
            r"(?:SELECT|INSERT|UPDATE|DELETE|MERGE)\b.*?;",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        for stmt in candidates:
            try:
                sqlglot.parse_one(stmt, read="oracle")
                validated.append(stmt.strip())
            except ParseError:
                # Still surface it downstream, just flag that structural
                # parsing failed (e.g. it references PL/SQL-only syntax).
                warnings.append(
                    f"Could not fully structurally parse embedded SQL statement "
                    f"(non-fatal, passed through as raw text): {stmt[:120].strip()}..."
                )
                validated.append(stmt.strip())
        return validated
