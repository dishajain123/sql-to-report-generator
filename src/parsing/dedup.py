"""
src/parsing/dedup.py
---------------------
Deterministic (no-LLM) compaction of the per-statement table-operation
evidence produced by `technical_sql_ops.extract_table_operations_from_chunks`.

Why this exists
----------------
`extract_table_operations_from_chunks` deliberately keeps one record per
*statement occurrence* of a table reference (never collapsing distinct
predicates), because that is exactly right for the verification /
traceability artifact - every literal SQL statement must remain
individually inspectable.

But that same non-deduplicated list was previously being serialized
wholesale into the Rule Synthesis LLM prompt. For a stored procedure that
references the same handful of tables in dozens of statements (a common
pattern - `#DPD`, `PRO.ACCOUNTCAL`, `PRO.CUSTOMERCAL` etc. are each
touched 15-30+ times in typical procedures), that means the same table
name, largely-overlapping column lists, and near-duplicate WHERE-clause
text get repeated dozens of times in one JSON payload - the single
largest driver of prompt-token cost in the pipeline.

This module produces a *second*, compacted view used only for the
synthesis prompt:
    - one record per (table, operation) pair
    - `target_columns` is the union of every column ever written/read
      for that pair (deduplicated, order-preserving)
    - `where_predicates` is the deduplicated list of *distinct* predicate
      strings actually used (not one entry per statement occurrence)
    - `statement_count` records how many raw statements were collapsed,
      so the LLM (and downstream reporting) can still see "this was
      touched N times" without paying for N near-identical blobs

The original, non-deduplicated `table_operations` / `tables_read` /
`tables_written` / `statement_provenance` / `chunk_provenance` produced
by ingestion + extraction are NOT modified by this module and remain
available in `merged_extraction` for reconciliation, quality scoring,
and the verification report - only the synthesis *prompt* payload is
built from the compacted view.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _dedupe_ordered(values: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        cleaned = _clean(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def dedup_table_operations(
    table_operations: Sequence[Dict[str, Any]],
    max_predicates_per_group: int = 8,
) -> List[Dict[str, Any]]:
    """Collapse per-statement table-operation records into one record per
    (table, operation) pair.

    This is a pure grouping/deduplication transform - every fact that
    survives is a fact that was already present in the input; nothing is
    inferred. It only removes repetition, so it is safe to run
    unconditionally before the synthesis call.
    """
    groups: "dict[Tuple[str, str], Dict[str, Any]]" = {}
    order: List[Tuple[str, str]] = []

    for op in table_operations:
        if not isinstance(op, dict):
            continue
        table = _clean(op.get("table"))
        if not table:
            continue
        operation = _clean(op.get("operation")).upper() or "UNKNOWN"
        key = (table.upper(), operation)
        if key not in groups:
            groups[key] = {
                "table": table,
                "operation": operation,
                "target_columns": [],
                "where_predicates": [],
                "statement_count": 0,
            }
            order.append(key)
        bucket = groups[key]
        bucket["statement_count"] += 1

        columns = op.get("target_columns") or op.get("columns") or []
        if isinstance(columns, str):
            columns = [columns]
        bucket["target_columns"].extend(_clean(c) for c in columns if _clean(c))

        predicate = (
            op.get("where_predicate")
            or op.get("filter_condition")
            or op.get("trigger_condition")
            or ""
        )
        if _clean(predicate):
            bucket["where_predicates"].append(_clean(predicate))

    result: List[Dict[str, Any]] = []
    for key in order:
        bucket = groups[key]
        distinct_predicates = _dedupe_ordered(bucket["where_predicates"])
        result.append(
            {
                "table": bucket["table"],
                "operation": bucket["operation"],
                "target_columns": _dedupe_ordered(bucket["target_columns"]),
                "where_predicates": distinct_predicates[:max_predicates_per_group],
                "statement_count": bucket["statement_count"],
            }
        )
    return result


def find_write_only_temp_tables(
    table_operations: Sequence[Dict[str, Any]],
    raw_source: str = "",
) -> List[str]:
    """Deterministically flag temp tables (`#name`) that are written
    (INSERT/UPDATE/SELECT..INTO) but never subsequently read anywhere
    else in the same object.

    This is a pure reachability check over already-parsed table
    operations - no LLM judgment involved - and surfaces genuinely dead
    logic (e.g. a working table built and never queried again) that is
    exactly the kind of finding a business analyst needs flagged, but
    that free-text "ambiguity" narration from an LLM tends to either
    miss or bury among generic parse-quality complaints.

    Structural false positives are possible: some source constructs
    (e.g. a table only read inside an `UPDATE ... FROM ... JOIN` clause
    that a statement-boundary edge case merged with an adjacent
    statement) can leave a genuine read invisible to the structural
    parse even after `technical_sql_ops` handles the common cases. A
    "this is dead code" claim in a business report is exactly the kind
    of confident, verifiable-sounding statement that must not be wrong,
    so when `raw_source` is supplied this runs one more, deliberately
    conservative check: strip out the table's own creation boilerplate
    (its `IF OBJECT_ID(...) DROP TABLE ...` guard and the literal text
    of every write statement that touches it) from the raw source, and
    only keep the table on the "dead" list if its name does not appear
    anywhere in what's left. This can only ever *remove* a candidate
    from the list (a name that still turns up elsewhere in the source is
    downgraded to "uncertain, not reported"), never add one - false
    negatives here are far cheaper than a false claim in the report.
    """
    written: set[str] = set()
    read: set[str] = set()
    write_statement_texts: "dict[str, list[str]]" = {}
    for op in table_operations:
        if not isinstance(op, dict):
            continue
        table = _clean(op.get("table")).upper()
        if not table.startswith("#"):
            continue
        operation = _clean(op.get("operation")).upper()
        if operation == "READ":
            read.add(table)
        else:
            written.add(table)
            statement_text = op.get("source_statement_text") or ""
            if statement_text:
                write_statement_texts.setdefault(table, []).append(str(statement_text))

    structurally_dead = sorted(t for t in written if t not in read)
    if not raw_source:
        return structurally_dead

    confirmed: List[str] = []
    for table in structurally_dead:
        bare_name = table.lstrip("#")
        residual = raw_source
        # Strip the standard existence-check-and-drop guard for this
        # table (`IF OBJECT_ID('TEMPDB..#name') ... DROP TABLE #name`),
        # dialect-agnostic and tolerant of the surrounding whitespace
        # these guards are typically formatted with.
        residual = re.sub(
            rf"(?is)IF\s+OBJECT_ID\s*\(\s*['\"][^'\"]*{re.escape(bare_name)}['\"]\s*\)[^\n]*\n\s*DROP\s+TABLE\s+#{re.escape(bare_name)}\b",
            "",
            residual,
        )
        # Strip the literal text of every write statement already
        # attributed to this table, so only genuinely *other* mentions
        # remain to be checked.
        for statement_text in write_statement_texts.get(table, []):
            residual = residual.replace(statement_text, "")
        if not re.search(rf"(?i)#{re.escape(bare_name)}\b", residual):
            confirmed.append(table)
    return confirmed


def find_disabled_column_sources(
    table_operations: Sequence[Dict[str, Any]],
    always_literal_columns: Sequence[str],
) -> List[str]:
    """Flag columns that are always assigned the same hardcoded literal
    (e.g. `0`) across every write of a table - a strong deterministic
    signal that the "real" calculation for that column has been
    commented out upstream and a placeholder default was left in place.

    `always_literal_columns` should be pre-computed by the caller from
    the raw source (columns whose only observed assigned value across
    all writes is a literal); this helper just centralizes the
    reporting shape so it can be surfaced consistently.
    """
    return sorted(_dedupe_ordered(always_literal_columns))