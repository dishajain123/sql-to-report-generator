"""
dialect_detector.py
--------------------
Deterministic SQL dialect detector.

Detects Oracle SQL/PL-SQL, SQL Server T-SQL, PostgreSQL, and ambiguous
or unsupported inputs using structural signals. Only Oracle and T-SQL
are currently supported for parsing/extraction. PostgreSQL is detected
explicitly so it never gets misclassified as Oracle/T-SQL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

ORACLE = "ORACLE"
TSQL = "TSQL"
POSTGRES = "POSTGRES"
UNKNOWN = "UNKNOWN"
AMBIGUOUS = "AMBIGUOUS"
UNSUPPORTED = "UNSUPPORTED"

SUPPORTED_DIALECTS = (ORACLE, TSQL)
DETECTABLE_DIALECTS = (ORACLE, TSQL, POSTGRES)

_PROMPT_DIALECT_MAP = {ORACLE: "oracle", TSQL: "tsql"}


class UnsupportedDialectError(ValueError):
    """Raised when the source appears to use an unsupported dialect."""


def normalize_dialect_name(dialect: str) -> str:
    value = str(dialect or "").strip().upper()
    if value in {"ORACLE", "TSQL", POSTGRES, UNKNOWN, AMBIGUOUS, UNSUPPORTED}:
        return value
    return value


def prompt_dialect_for_state(dialect: str) -> Optional[str]:
    return _PROMPT_DIALECT_MAP.get(normalize_dialect_name(dialect))


# Each signal is (dialect, weight, compiled_pattern). Weight reflects how
# strongly the signal implies that dialect on its own (a "GO" batch
# separator on its own line is near-conclusive for T-SQL; a trailing "/"
# terminator is near-conclusive for Oracle SQL*Plus style scripts).
_SIGNALS: List[tuple] = [
    # --- Oracle / PL-SQL signals -------------------------------------------------
    (ORACLE, 3, re.compile(r"^\s*/\s*$", re.MULTILINE)),
    (ORACLE, 3, re.compile(r"\bCREATE\s+OR\s+REPLACE\b", re.IGNORECASE)),
    (ORACLE, 2, re.compile(r"\bEXCEPTION\s*\n?\s*WHEN\b", re.IGNORECASE)),
    (ORACLE, 2, re.compile(r"\bDBMS_[A-Z_]+\b", re.IGNORECASE)),
    (ORACLE, 2, re.compile(r"\bEXECUTE\s+IMMEDIATE\b", re.IGNORECASE)),
    (ORACLE, 2, re.compile(r"%TYPE\b|%ROWTYPE\b", re.IGNORECASE)),
    (ORACLE, 1, re.compile(r"\bVARCHAR2\b|\bNUMBER\s*\(", re.IGNORECASE)),
    (ORACLE, 1, re.compile(r"\bROWNUM\b", re.IGNORECASE)),
    (ORACLE, 1, re.compile(r"\bNVL\s*\(", re.IGNORECASE)),
    (ORACLE, 1, re.compile(r":=", re.MULTILINE)),
    # --- T-SQL / SQL Server signals ----------------------------------------------
    (TSQL, 3, re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)),
    (TSQL, 3, re.compile(r"\bBEGIN\s+TRY\b", re.IGNORECASE)),
    (TSQL, 2, re.compile(r"\bCREATE\s+(OR\s+ALTER\s+)?PROC(EDURE)?\b", re.IGNORECASE)),
    (TSQL, 2, re.compile(r"@\w+", re.MULTILINE)),
    (TSQL, 2, re.compile(r"\bSP_EXECUTESQL\b", re.IGNORECASE)),
    (TSQL, 2, re.compile(r"\[(?:[A-Za-z0-9_ ]+)\]")),
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
    dialect: str
    confidence: str
    oracle_score: int = 0
    tsql_score: int = 0
    signals_matched: List[str] = field(default_factory=list)
    concrete_dialect: Optional[str] = None
    user_specified: bool = False
    source: str = "auto"


def _strongly_ambiguous(oracle_score: int, tsql_score: int) -> bool:
    return oracle_score > 0 and tsql_score > 0 and abs(oracle_score - tsql_score) <= 1


def detect_dialect(code: str, hint: str = "auto") -> DialectDetectionResult:
    """Detect whether `code` is Oracle SQL/PL-SQL or SQL Server T-SQL.

    Explicit user hints are trusted when they are Oracle/T-SQL. Automatic
    detection never silently defaults to Oracle when evidence is weak.
    """
    normalized_hint = normalize_dialect_name(hint)
    if normalized_hint in SUPPORTED_DIALECTS:
        return DialectDetectionResult(
            dialect=normalized_hint,
            concrete_dialect=normalized_hint.lower(),
            confidence="high",
            signals_matched=["explicit override"],
            user_specified=True,
            source="user",
        )
    if normalized_hint not in {"AUTO", ""}:
        raise UnsupportedDialectError(
            f"Unsupported SQL dialect hint '{hint}'. Only 'oracle' and 'tsql' are supported."
        )

    code = _mask_strings_and_comments(code)
    oracle_score = 0
    tsql_score = 0
    postgres_score = 0
    matched: List[str] = []

    for dialect, weight, pattern in _SIGNALS:
        if not pattern.search(code):
            continue
        if dialect == ORACLE:
            oracle_score += weight
        else:
            tsql_score += weight
        matched.append(f"{dialect}:{pattern.pattern[:40]}")

    for weight, pattern in _POSTGRESQL_SIGNALS:
        if pattern.search(code):
            postgres_score += weight
            matched.append(f"{POSTGRES}:{pattern.pattern[:40]}")

    if postgres_score >= 3 and postgres_score >= max(oracle_score, tsql_score):
        return DialectDetectionResult(
            dialect=UNSUPPORTED,
            confidence="low",
            oracle_score=oracle_score,
            tsql_score=tsql_score,
            signals_matched=matched,
            concrete_dialect=None,
        )

    if oracle_score == 0 and tsql_score == 0:
        return DialectDetectionResult(
            dialect=UNKNOWN,
            confidence="low",
            oracle_score=0,
            tsql_score=0,
            signals_matched=[],
            concrete_dialect=None,
        )

    if _strongly_ambiguous(oracle_score, tsql_score):
        return DialectDetectionResult(
            dialect=AMBIGUOUS,
            confidence="low",
            oracle_score=oracle_score,
            tsql_score=tsql_score,
            signals_matched=matched,
            concrete_dialect=None,
        )

    if oracle_score >= 3 and oracle_score >= tsql_score + 2:
        return DialectDetectionResult(
            dialect=ORACLE,
            confidence="high" if oracle_score >= 4 else "medium",
            oracle_score=oracle_score,
            tsql_score=tsql_score,
            signals_matched=matched,
            concrete_dialect="oracle",
        )

    if tsql_score >= 3 and tsql_score >= oracle_score + 2:
        return DialectDetectionResult(
            dialect=TSQL,
            confidence="high" if tsql_score >= 4 else "medium",
            oracle_score=oracle_score,
            tsql_score=tsql_score,
            signals_matched=matched,
            concrete_dialect="tsql",
        )

    return DialectDetectionResult(
        dialect=UNKNOWN,
        confidence="low",
        oracle_score=oracle_score,
        tsql_score=tsql_score,
        signals_matched=matched,
        concrete_dialect=None,
    )

