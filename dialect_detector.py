"""
dialect_detector.py
--------------------
Deterministic SQL dialect detector.

Distinguishes Oracle SQL/PL-SQL from SQL Server T-SQL using structural
signals (never a single keyword in isolation), so downstream stages
(ingestion parsing, sqlglot validation, prompt selection) can apply the
correct dialect-specific rules. Runs before preprocessing/parsing in the
pipeline, as required by the overall flow:

    Input -> Guardrails -> Dialect Detection -> Preprocessing -> ...

Only two dialects are supported by design: "oracle" and "tsql".
PostgreSQL and other dialects are intentionally out of scope; inputs
that look like PostgreSQL are rejected rather than silently misrouted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

ORACLE = "oracle"
TSQL = "tsql"
SUPPORTED_DIALECTS = (ORACLE, TSQL)


class UnsupportedDialectError(ValueError):
    """Raised when the source appears to use an unsupported dialect."""

# Each signal is (dialect, weight, compiled_pattern). Weight reflects how
# strongly the signal implies that dialect on its own (a "GO" batch
# separator on its own line is near-conclusive for T-SQL; a trailing "/"
# terminator is near-conclusive for Oracle SQL*Plus style scripts).
_SIGNALS: List[tuple] = [
    # --- Oracle / PL-SQL signals -------------------------------------------------
    (ORACLE, 3, re.compile(r"^\s*/\s*$", re.MULTILINE)),  # SQL*Plus "/" terminator
    (ORACLE, 3, re.compile(r"\bCREATE\s+OR\s+REPLACE\b", re.IGNORECASE)),
    (ORACLE, 2, re.compile(r"\bEXCEPTION\s*\n?\s*WHEN\b", re.IGNORECASE)),
    (ORACLE, 2, re.compile(r"\bDBMS_[A-Z_]+\b", re.IGNORECASE)),
    (ORACLE, 2, re.compile(r"\bEXECUTE\s+IMMEDIATE\b", re.IGNORECASE)),
    (ORACLE, 2, re.compile(r"%TYPE\b|%ROWTYPE\b", re.IGNORECASE)),
    (ORACLE, 1, re.compile(r"\bVARCHAR2\b|\bNUMBER\s*\(", re.IGNORECASE)),
    (ORACLE, 1, re.compile(r"\bROWNUM\b", re.IGNORECASE)),
    (ORACLE, 1, re.compile(r"\bNVL\s*\(", re.IGNORECASE)),
    (ORACLE, 1, re.compile(r":=", re.MULTILINE)),  # PL/SQL assignment operator
    # --- T-SQL / SQL Server signals ----------------------------------------------
    (TSQL, 3, re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)),  # batch separator
    (TSQL, 3, re.compile(r"\bBEGIN\s+TRY\b", re.IGNORECASE)),
    (TSQL, 2, re.compile(r"\bCREATE\s+(OR\s+ALTER\s+)?PROC(EDURE)?\b", re.IGNORECASE)),
    (TSQL, 2, re.compile(r"@\w+", re.MULTILINE)),  # @variable / @parameter syntax
    (TSQL, 2, re.compile(r"\bSP_EXECUTESQL\b", re.IGNORECASE)),
    (TSQL, 2, re.compile(r"\[[A-Za-z0-9_ ]+\]"), ),  # bracketed identifiers
    (TSQL, 1, re.compile(r"\bNVARCHAR\b|\bDATETIME2?\b|\bBIT\b", re.IGNORECASE)),
    (TSQL, 1, re.compile(r"\bTOP\s*\(?\s*\d+\)?", re.IGNORECASE)),
    (TSQL, 1, re.compile(r"\bISNULL\s*\(", re.IGNORECASE)),
    (TSQL, 1, re.compile(r"\bIDENTITY\s*\(", re.IGNORECASE)),
    (TSQL, 1, re.compile(r"\bOUTPUT\b", re.IGNORECASE)),
    (TSQL, 1, re.compile(r"@@ROWCOUNT|@@IDENTITY|@@ERROR", re.IGNORECASE)),
]

# PostgreSQL-specific signals. These are strong enough to reject the
# source early rather than misclassify it as Oracle/T-SQL.
_POSTGRESQL_SIGNALS: List[tuple] = [
    (3, re.compile(r"\bLANGUAGE\s+PLPGSQL\b", re.IGNORECASE)),
    (3, re.compile(r"\bDO\s+\$\$", re.IGNORECASE)),
    (2, re.compile(r"\bON\s+CONFLICT\b", re.IGNORECASE)),
    (2, re.compile(r"\bRETURNING\b", re.IGNORECASE)),
    (2, re.compile(r"::[A-Za-z_][A-Za-z0-9_]*", re.MULTILINE)),
    (2, re.compile(r"\bRAISE\s+NOTICE\b", re.IGNORECASE)),
    (2, re.compile(r"\bPERFORM\b", re.IGNORECASE)),
    (2, re.compile(r"\bSERIAL\b", re.IGNORECASE)),
    (1, re.compile(r"\bILIKE\b", re.IGNORECASE)),
]


def _mask_strings_and_comments(code: str) -> str:
    """Mask comments and quoted literals so dialect signals only see
    structural source text.
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
        elif code[i] == '"':
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
        elif code[i] == "[":
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


@dataclass
class DialectDetectionResult:
    dialect: str  # "oracle" | "tsql"
    confidence: str  # "high" | "medium" | "low"
    oracle_score: int = 0
    tsql_score: int = 0
    signals_matched: List[str] = field(default_factory=list)


def detect_dialect(code: str, hint: str = "auto") -> DialectDetectionResult:
    """Detect whether `code` is Oracle SQL/PL-SQL or SQL Server T-SQL.

    Args:
        code: the raw source text.
        hint: "auto" (default) to detect from content, or an explicit
            "oracle" / "tsql" override supplied by the caller (e.g. a
            CLI flag or UI selector) which is trusted as-is and returned
            with "high" confidence without running the heuristics.
    """
    normalized_hint = (hint or "auto").strip().lower()
    if normalized_hint in SUPPORTED_DIALECTS:
        return DialectDetectionResult(
            dialect=normalized_hint, confidence="high", signals_matched=["explicit override"]
        )
    if normalized_hint not in ("auto", ""):
        raise UnsupportedDialectError(
            f"Unsupported SQL dialect hint '{hint}'. Only 'oracle' and 'tsql' are supported."
        )

    code = _mask_strings_and_comments(code)
    oracle_score = 0
    tsql_score = 0
    postgres_score = 0
    matched: List[str] = []

    for dialect, weight, pattern in _SIGNALS:
        hits = pattern.findall(code)
        if not hits:
            continue
        if dialect == ORACLE:
            oracle_score += weight
        else:
            tsql_score += weight
        matched.append(f"{dialect}:{pattern.pattern[:40]}")

    for weight, pattern in _POSTGRESQL_SIGNALS:
        if pattern.search(code):
            postgres_score += weight
            matched.append(f"postgresql:{pattern.pattern[:40]}")

    if postgres_score >= 4 and postgres_score >= oracle_score and postgres_score >= tsql_score:
        raise UnsupportedDialectError(
            "The source appears to use PostgreSQL / PLpgSQL, which is not supported. "
            "Please provide an Oracle PL/SQL or SQL Server T-SQL object."
        )

    if oracle_score == 0 and tsql_score == 0:
        # No structural signal either way - default to Oracle (the
        # project's original/primary supported dialect) but say so
        # plainly at low confidence rather than pretending certainty.
        return DialectDetectionResult(
            dialect=ORACLE, confidence="low", oracle_score=0, tsql_score=0, signals_matched=[]
        )

    if oracle_score > tsql_score:
        dialect = ORACLE
    elif tsql_score > oracle_score:
        dialect = TSQL
    else:
        # Genuine tie - default to Oracle but flag low confidence.
        dialect = ORACLE

    margin = abs(oracle_score - tsql_score)
    total = oracle_score + tsql_score
    if total == 0:
        confidence = "low"
    elif margin / total >= 0.5:
        confidence = "high"
    elif margin / total >= 0.2:
        confidence = "medium"
    else:
        confidence = "low"

    return DialectDetectionResult(
        dialect=dialect,
        confidence=confidence,
        oracle_score=oracle_score,
        tsql_score=tsql_score,
        signals_matched=matched,
    )
