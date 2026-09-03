"""
Deterministic table-operation extraction from parsed SQL statements.

This module keeps statement-level provenance intact and splits each SQL
statement into explicit table-operation records so reads/writes can be
reported without collapsing distinct predicates or multiple references to
the same table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from src.ingestion.ingestion import CodeChunk, CodeIngestionAgent
from src.parsing.statement_boundaries import split_top_level_statement_spans, split_top_level_statements


# `split_top_level_statement_spans` is a general-purpose boundary detector
# shared with the LLM-chunking path: it deliberately gives *every* line of
# source text somewhere to live, including pure procedural wrapper text
# that carries no SQL of its own (`IF ...`, `BEGIN`, `BEGIN TRY`/`END TRY`,
# `BEGIN CATCH`/`END CATCH`, `EXCEPTION`, `EXEC ...`, PL/SQL `:=`
# assignments, bare `DECLARE`/cursor headers, ...). Those wrapper spans
# were never valid standalone SQL, so handing them to
# `sqlglot.parse_one()` here can only ever do one of two things: silently
# succeed as a meaningless `Command`/misc node (contributing zero real
# table operations, since there's no table reference in them to extract)
# or trigger sqlglot's "unsupported syntax ... falling back to parsing as
# a 'Command'" warning. Either way nothing downstream is gained, and the
# warning is pure noise. `_PARSEABLE_SPAN_RE` restricts the sqlglot call
# to spans that actually start with a real top-level SQL keyword, so
# control-flow-only fragments are skipped up front - no parse attempt, no
# warning - while every genuine embedded SQL statement (regardless of
# which Oracle/T-SQL procedural construct surrounds it) still gets
# structurally parsed exactly as before.
_PARSEABLE_SPAN_RE = re.compile(
    r"(?i)^(WITH|SELECT|INSERT|UPDATE|DELETE|MERGE|TRUNCATE|SET)\b"
)


_TABLE_REF_PATTERN = r"(?:\[(?:[^\]]|\]\])+\]|[#A-Za-z_][\w$#]*)(?:\s*\.\s*(?:\[(?:[^\]]|\]\])+\]|[#A-Za-z_][\w$#]*))*"
_TABLE_ALIAS_STOPWORDS = {
    "WHERE",
    "GROUP",
    "ORDER",
    "HAVING",
    "JOIN",
    "ON",
    "INNER",
    "LEFT",
    "RIGHT",
    "FULL",
    "CROSS",
    "OUTER",
    "UNION",
    "UPDATE",
    "INSERT",
    "DELETE",
    "MERGE",
    "DECLARE",
    "SET",
    "END",
}
# Same stopwords, usable as a negative lookahead *inside* a regex alias
# capture group, so "<table> WHERE ..." (no real alias) never has "WHERE"
# swallowed as if it were an alias - which would otherwise strip the
# keyword out of the remaining text and silently blank the WHERE clause.
_TABLE_ALIAS_STOPWORD_PATTERN = "|".join(sorted(_TABLE_ALIAS_STOPWORDS))
_OPTIONAL_ALIAS_GROUP = (
    rf"(?:\s+(?:AS\s+)?(?!(?:{_TABLE_ALIAS_STOPWORD_PATTERN})\b)(?P<{{name}}>\w+))?"
)


@dataclass
class StatementProvenance:
    statement_id: str
    source_chunk_id: str
    source_chunk_kind: str
    source_chunk_context: List[str] = field(default_factory=list)
    statement_index: int = 0
    statement_kind: str = ""
    source_statement_text: str = ""
    parse_status: str = "parsed"
    parse_error: str = ""
    active_status: str = "ACTIVE"
    operation_count: int = 0
    source_file: str = ""
    source_char_start: int = -1
    source_char_end: int = -1
    source_line_start: int = -1
    source_line_end: int = -1
    source_location_status: str = "unavailable"
    evidence_type: str = ""


def extract_table_operations_from_chunks(
    chunks: Sequence[CodeChunk], dialect: str
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return deterministic per-statement table operation records.

    The output is intentionally statement-centric:
    - distinct SQL statements keep distinct source_statement_id values
    - each table reference becomes its own record
    - reads and writes are not merged across statements
    """
    operations: List[Dict[str, Any]] = []
    provenance: List[Dict[str, Any]] = []
    seen_operation_keys: set[tuple] = set()
    normalized_dialect = str(dialect or "").strip().lower()
    if normalized_dialect not in {"oracle", "tsql"}:
        return operations, provenance
    sqlglot_dialect = "tsql" if normalized_dialect == "tsql" else "oracle"

    for chunk in chunks:
        source_texts = [("chunk_text", getattr(chunk, "text", "") or "")]
        source_texts.extend(
            (f"embedded_{index:02d}", embedded_text)
            for index, embedded_text in enumerate(list(getattr(chunk, "embedded_sql", []) or []), start=1)
        )

        statement_counter = 0
        for source_label, source_text in source_texts:
            for statement_start, statement_end in _split_embedded_sql_statement_spans(source_text, dialect):
                statement_text = source_text[statement_start:statement_end].strip()
                if not statement_text:
                    continue
                statement_counter += 1
                statement_id = f"{chunk.chunk_id}:{source_label}_{statement_counter:02d}"
                loc_start, loc_end = _locate_statement_span(chunk.text or source_text, statement_text)
                if loc_start >= 0:
                    source_line_start = _line_number_for_offset(chunk.text or source_text, loc_start)
                    source_line_end = _line_number_for_offset(chunk.text or source_text, max(loc_end - 1, loc_start))
                    source_location_status = "available"
                else:
                    source_line_start = -1
                    source_line_end = -1
                    source_location_status = "unavailable"
                evidence_type = _infer_evidence_type(source_label, statement_text)
                statement_prov = StatementProvenance(
                    statement_id=statement_id,
                    source_chunk_id=chunk.chunk_id,
                    source_chunk_kind=chunk.kind,
                    source_chunk_context=list(getattr(chunk, "context_path", []) or []),
                    statement_index=statement_counter,
                    source_statement_text=statement_text,
                    source_file=getattr(chunk, "source_file", "") or "",
                    source_char_start=loc_start,
                    source_char_end=loc_end,
                    source_line_start=source_line_start if source_location_status == "available" else getattr(chunk, "source_line_start", -1),
                    source_line_end=source_line_end if source_location_status == "available" else getattr(chunk, "source_line_end", -1),
                    source_location_status=source_location_status,
                    evidence_type=evidence_type,
                )

                parse_source = _strip_sql_comments(statement_text)
                if not _PARSEABLE_SPAN_RE.match(parse_source.lstrip()):
                    # Procedural wrapper text (IF/BEGIN/BEGIN TRY/END TRY/
                    # BEGIN CATCH/END CATCH/EXCEPTION/EXEC/PL-SQL `:=`
                    # assignments/bare DECLARE-cursor headers/...) never
                    # contains a standalone SQL statement of its own - any
                    # embedded SELECT/INSERT/UPDATE/DELETE/MERGE inside it
                    # already got its own span above. Skip sqlglot for it
                    # entirely (no meaningful table operation to extract,
                    # and no benefit to the spurious "unsupported syntax"
                    # warning it would otherwise produce); still run the
                    # cheap regex fallback as a safety net in case a table
                    # reference is present in a shape the span detector
                    # didn't carve out on its own.
                    statement_prov.parse_status = "skipped_non_sql"
                    fallback_ops = _regex_fallback_table_operations(
                        statement_text=statement_text,
                        statement_id=statement_id,
                        chunk=chunk,
                        dialect=sqlglot_dialect,
                    )
                    statement_prov.operation_count = len(fallback_ops)
                    for candidate in fallback_ops:
                        key = _operation_dedupe_key(candidate)
                        if key in seen_operation_keys:
                            continue
                        seen_operation_keys.add(key)
                        operations.append(candidate)
                    provenance.append(statement_prov.__dict__)
                    continue

                try:
                    tree = sqlglot.parse_one(parse_source, read=sqlglot_dialect)
                except Exception as exc:
                    statement_prov.parse_status = "parse_failed"
                    statement_prov.parse_error = str(exc)
                    fallback_ops = _regex_fallback_table_operations(
                        statement_text=statement_text,
                        statement_id=statement_id,
                        chunk=chunk,
                        dialect=sqlglot_dialect,
                    )
                    statement_prov.operation_count = len(fallback_ops)
                    for candidate in fallback_ops:
                        key = _operation_dedupe_key(candidate)
                        if key in seen_operation_keys:
                            continue
                        seen_operation_keys.add(key)
                        operations.append(candidate)
                    provenance.append(statement_prov.__dict__)
                    continue

                statement_prov.statement_kind = tree.__class__.__name__.upper()
                extracted = []
                for operation_node in _iter_top_level_operation_nodes(tree):
                    candidate_ops = _extract_table_ops_from_tree(
                        tree=operation_node,
                        statement_text=statement_text,
                        statement_id=statement_id,
                        chunk=chunk,
                        dialect=sqlglot_dialect,
                    )
                    for candidate in candidate_ops:
                        key = _operation_dedupe_key(candidate)
                        if key in seen_operation_keys:
                            continue
                        seen_operation_keys.add(key)
                        extracted.append(candidate)
                if not extracted:
                    for candidate in _regex_fallback_table_operations(
                        statement_text=statement_text,
                        statement_id=statement_id,
                        chunk=chunk,
                        dialect=sqlglot_dialect,
                    ):
                        key = _operation_dedupe_key(candidate)
                        if key in seen_operation_keys:
                            continue
                        seen_operation_keys.add(key)
                        extracted.append(candidate)
                statement_prov.operation_count = len(extracted)
                operations.extend(extracted)
                provenance.append(statement_prov.__dict__)

    return operations, provenance


def split_table_operations(
    table_operations: Sequence[Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    reads: List[Dict[str, Any]] = []
    writes: List[Dict[str, Any]] = []
    for op in table_operations:
        operation = str(op.get("operation", "")).upper()
        if operation == "READ":
            reads.append(dict(op))
        else:
            writes.append(dict(op))
            if operation in {"UPDATE", "MERGE"} and op.get("table"):
                reads.append({**dict(op), "operation": "READ"})
    return reads, writes


def _split_embedded_sql_statements(embedded_sql: str, dialect: str) -> List[str]:
    text = str(embedded_sql or "").strip()
    if not text:
        return []
    masked = CodeIngestionAgent._mask_strings_and_comments(text, mask_brackets=(str(dialect).lower() != "tsql"))
    return split_top_level_statements(text, masked)


def _split_embedded_sql_statement_spans(embedded_sql: str, dialect: str) -> List[Tuple[int, int]]:
    text = str(embedded_sql or "")
    if not text.strip():
        return []
    masked = CodeIngestionAgent._mask_strings_and_comments(text, mask_brackets=(str(dialect).lower() != "tsql"))
    return split_top_level_statement_spans(text, masked)


def _locate_statement_span(source_text: str, statement_text: str) -> Tuple[int, int]:
    source = str(source_text or "")
    target = str(statement_text or "").strip()
    if not source or not target:
        return -1, -1
    start = source.find(target)
    if start < 0:
        return -1, -1
    return start, start + len(target)


def _line_number_for_offset(text: str, offset: int) -> int:
    if offset < 0:
        return -1
    return text.count("\n", 0, offset) + 1


def _infer_evidence_type(source_label: str, statement_text: str) -> str:
    label = str(source_label or "").lower()
    stmt = str(statement_text or "").strip().upper()
    if label.startswith("embedded_"):
        return "ASSIGNMENT" if stmt.startswith("UPDATE") else "OUTCOME"
    if stmt.startswith("SELECT"):
        return "TABLE_REFERENCE"
    if stmt.startswith("UPDATE"):
        return "ASSIGNMENT"
    if stmt.startswith("INSERT"):
        return "OUTCOME"
    if stmt.startswith("DELETE"):
        return "CONDITION"
    if stmt.startswith("MERGE"):
        return "OUTCOME"
    if stmt.startswith("TRUNCATE"):
        return "OUTCOME"
    if stmt.startswith("EXCEPTION") or stmt.startswith("BEGIN CATCH"):
        return "EXCEPTION"
    if "CASE" in stmt or "WHEN " in stmt:
        return "CONDITION"
    return "TABLE_REFERENCE"


def _strip_sql_comments(text: str) -> str:
    stripped = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    stripped = re.sub(r"--[^\n]*", " ", stripped)
    return stripped


def _select_has_update_lock(tree: exp.Expression) -> bool:
    """True when a SELECT carries a row-locking clause (Oracle `FOR
    UPDATE`; sqlglot's generic `Lock(update=True)` node also covers
    dialect equivalents), independent of which table/columns are locked.
    """
    for lock in tree.args.get("locks") or []:
        if isinstance(lock, exp.Lock) and lock.args.get("update"):
            return True
    return False


def _extract_table_ops_from_tree(
    tree: exp.Expression,
    statement_text: str,
    statement_id: str,
    chunk: CodeChunk,
    dialect: str,
) -> List[Dict[str, Any]]:
    statement_kind = tree.__class__.__name__.upper()
    all_columns = _unique_preserve(_render_all_columns(tree, dialect))
    constants = _unique_preserve(_render_all_literals(tree, dialect))
    where_predicate = _render_expression(tree.args.get("where"), dialect)
    having_predicate = _render_expression(tree.args.get("having"), dialect)
    join_predicates = _render_join_predicates(tree, dialect)
    exists_predicates = _render_exists_predicates(tree, dialect)
    table_nodes = _collect_table_nodes(tree)

    operations: List[Dict[str, Any]] = []
    if isinstance(tree, exp.Select):
        # `SELECT ... INTO <table> FROM ...` (T-SQL) creates a brand-new
        # table from the result set - sqlglot models the INTO target as
        # just another `exp.Table` node inside the tree, so without this
        # check it gets swept up by `_collect_table_nodes` and reported
        # as a READ alongside the real FROM-clause tables. That silently
        # mis-tags every SELECT..INTO target as "read", which in turn
        # made temp tables built this way (a common pattern) invisible
        # to write-only/dead-table detection. Split it out and report it
        # as its own write operation instead.
        into_table_node = None
        into_clause = tree.args.get("into")
        if into_clause is not None:
            into_table_node = into_clause.this if isinstance(into_clause.this, exp.Table) else None
        into_signature = _table_signature(into_table_node) if into_table_node is not None else None
        read_table_nodes = [
            t for t in table_nodes
            if into_signature is None or _table_signature(t) != into_signature
        ]
        for occurrence_index, table in enumerate(read_table_nodes, start=1):
            operations.append(
                _build_operation_record(
                    operation="READ",
                    table=table,
                    target_columns=_render_select_projection_columns(tree, dialect),
                    source_columns=all_columns,
                    where_predicate=where_predicate,
                    having_predicate=having_predicate,
                    join_predicates=join_predicates,
                    exists_predicates=exists_predicates,
                    constants=constants,
                    statement_kind=statement_kind,
                    statement_text=statement_text,
                    statement_id=statement_id,
                    chunk=chunk,
                    dialect=dialect,
                    table_occurrence=occurrence_index,
                )
            )
        # In Oracle PL/SQL, `SELECT ... INTO variable FROM ...` assigns
        # query results to a local variable; it does not write a table.
        # T-SQL `SELECT ... INTO #table` is the opposite and must remain an
        # INSERT operation. Keep this distinction here, at the existing AST
        # extraction boundary, so downstream read/write consumers stay
        # dialect-neutral.
        is_oracle_variable_into = (
            into_table_node is not None and str(dialect or "").lower() == "oracle"
        )
        if into_table_node is not None and not is_oracle_variable_into:
            operations.append(
                _build_operation_record(
                    operation="INSERT",
                    table=into_table_node,
                    target_columns=_render_select_projection_columns(tree, dialect),
                    source_columns=all_columns,
                    where_predicate=where_predicate,
                    having_predicate=having_predicate,
                    join_predicates=join_predicates,
                    exists_predicates=exists_predicates,
                    constants=constants,
                    statement_kind="SELECT_INTO",
                    statement_text=statement_text,
                    statement_id=statement_id,
                    chunk=chunk,
                    dialect=dialect,
                    table_occurrence=1,
                )
            )
        # `SELECT ... FOR UPDATE` (Oracle) / `SELECT ... WITH (UPDLOCK)`
        # style row-locking reads are read-and-lock, not read-only: the
        # locked rows are held for a subsequent write, so any table
        # referenced by a locking SELECT is write-intent evidence too,
        # independent of what specific columns/tables are involved.
        # sqlglot represents this generically as a `Lock` node with
        # `update=True` on the SELECT, regardless of dialect.
        if _select_has_update_lock(tree):
            for occurrence_index, table in enumerate(read_table_nodes, start=1):
                operations.append(
                    _build_operation_record(
                        operation="LOCK",
                        table=table,
                        target_columns=[],
                        source_columns=all_columns,
                        where_predicate=where_predicate,
                        having_predicate=having_predicate,
                        join_predicates=join_predicates,
                        exists_predicates=exists_predicates,
                        constants=constants,
                        statement_kind=statement_kind,
                        statement_text=statement_text,
                        statement_id=statement_id,
                        chunk=chunk,
                        dialect=dialect,
                        table_occurrence=occurrence_index,
                    )
                )
        return operations

    if isinstance(tree, exp.Insert):
        target_table, target_columns = _resolve_insert_target(tree, dialect)
        source_expr = tree.args.get("expression")
        source_columns = _unique_preserve(
            _render_all_columns(source_expr, dialect) if source_expr is not None else []
        )
        if target_table is not None:
            operations.append(
                _build_operation_record(
                    operation="INSERT",
                    table=target_table,
                    target_columns=target_columns,
                    source_columns=source_columns,
                    where_predicate=where_predicate,
                    having_predicate=having_predicate,
                    join_predicates=join_predicates,
                    exists_predicates=exists_predicates,
                    constants=constants,
                    statement_kind=statement_kind,
                    statement_text=statement_text,
                    statement_id=statement_id,
                    chunk=chunk,
                    dialect=dialect,
                    table_occurrence=1,
                )
            )
        return operations

    if isinstance(tree, exp.Update):
        target_table = _resolve_update_target(tree, dialect)
        target_columns = _render_update_target_columns(tree, dialect)
        assigned_values = _render_update_assigned_values(tree, dialect)
        source_columns = _unique_preserve(
            [
                col
                for col in _render_all_columns(tree, dialect)
                if col not in target_columns
            ]
        )
        if target_table is not None:
            operations.append(
                _build_operation_record(
                    operation="UPDATE",
                    table=target_table,
                    target_columns=target_columns,
                    source_columns=source_columns,
                    where_predicate=where_predicate,
                    having_predicate=having_predicate,
                    join_predicates=join_predicates,
                    exists_predicates=exists_predicates,
                    constants=constants,
                    assigned_values=assigned_values,
                    statement_kind=statement_kind,
                    statement_text=statement_text,
                    statement_id=statement_id,
                    chunk=chunk,
                    dialect=dialect,
                    table_occurrence=1,
                )
            )
        # T-SQL's `UPDATE A SET ... FROM real_table A INNER JOIN other B
        # ON ...` idiom (used throughout T-SQL stored procedures) puts
        # every table the UPDATE actually depends on - the real target
        # table via its FROM-clause alias, plus every JOINed table -
        # into the FROM/JOIN clauses, not the `UPDATE <name>` head.
        # `table_nodes` (collected once above from the whole statement
        # tree) already contains all of them; only the resolved update
        # target has been recorded as a write so far, so every other
        # distinct table referenced is a genuine read dependency of this
        # statement and needs its own READ record - without this, any
        # table joined-but-not-updated in an UPDATE...FROM...JOIN
        # statement was invisible to "tables read", reconciliation, and
        # dead-table detection.
        target_key = (
            (_table_signature(target_table), _table_alias(target_table))
            if target_table is not None
            else None
        )
        read_table_nodes = [
            t for t in table_nodes
            if target_key is None or (_table_signature(t), _table_alias(t)) != target_key
        ]
        for occurrence_index, table in enumerate(read_table_nodes, start=1):
            operations.append(
                _build_operation_record(
                    operation="READ",
                    table=table,
                    target_columns=[],
                    source_columns=source_columns,
                    where_predicate=where_predicate,
                    having_predicate=having_predicate,
                    join_predicates=join_predicates,
                    exists_predicates=exists_predicates,
                    constants=constants,
                    statement_kind=statement_kind,
                    statement_text=statement_text,
                    statement_id=statement_id,
                    chunk=chunk,
                    dialect=dialect,
                    table_occurrence=occurrence_index,
                )
            )
        return operations

    if isinstance(tree, exp.Delete):
        target_table = _resolve_delete_target(tree, dialect)
        if target_table is not None:
            operations.append(
                _build_operation_record(
                    operation="DELETE",
                    table=target_table,
                    target_columns=[],
                    source_columns=all_columns,
                    where_predicate=where_predicate,
                    having_predicate=having_predicate,
                    join_predicates=join_predicates,
                    exists_predicates=exists_predicates,
                    constants=constants,
                    assigned_values=[],
                    statement_kind=statement_kind,
                    statement_text=statement_text,
                    statement_id=statement_id,
                    chunk=chunk,
                    dialect=dialect,
                    table_occurrence=1,
                )
            )
        return operations

    if isinstance(tree, exp.TruncateTable):
        # TRUNCATE has no WHERE/predicate - it is an unconditional,
        # whole-table wipe, which is a materially different (and higher-
        # risk) operation than a predicated DELETE. Keep that distinction
        # visible rather than collapsing it into a generic write, and
        # never invent a where_predicate/join/exists for it.
        operations = []
        for occurrence_index, table in enumerate(
            getattr(tree, "expressions", None) or [], start=1
        ):
            if not isinstance(table, exp.Table):
                continue
            operations.append(
                _build_operation_record(
                    operation="TRUNCATE",
                    table=table,
                    target_columns=[],
                    source_columns=[],
                    where_predicate=None,
                    having_predicate=None,
                    join_predicates=[],
                    exists_predicates=[],
                    constants=[],
                    assigned_values=[],
                    statement_kind=statement_kind,
                    statement_text=statement_text,
                    statement_id=statement_id,
                    chunk=chunk,
                    dialect=dialect,
                    table_occurrence=occurrence_index,
                )
            )
        return operations

    if isinstance(tree, exp.Merge):
        target_table = _resolve_merge_target(tree, dialect)
        if target_table is not None:
            operations.append(
                _build_operation_record(
                    operation="MERGE",
                    table=target_table,
                    target_columns=_render_all_columns(tree, dialect),
                    source_columns=all_columns,
                    where_predicate=where_predicate,
                    having_predicate=having_predicate,
                    join_predicates=join_predicates,
                    exists_predicates=exists_predicates,
                    constants=constants,
                    assigned_values=[],
                    statement_kind=statement_kind,
                    statement_text=statement_text,
                    statement_id=statement_id,
                    chunk=chunk,
                    dialect=dialect,
                    table_occurrence=1,
                )
            )
        return operations

    return operations


def _iter_top_level_operation_nodes(expression: exp.Expression) -> Iterable[exp.Expression]:
    relevant_types = (exp.Select, exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.TruncateTable)

    def _children(node: exp.Expression) -> Iterable[exp.Expression]:
        for value in node.args.values():
            if isinstance(value, exp.Expression):
                yield value
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, exp.Expression):
                        yield item

    def _recurse(node: exp.Expression, inside_operation: bool) -> Iterable[exp.Expression]:
        node_is_operation = isinstance(node, relevant_types)
        if node_is_operation and not inside_operation:
            yield node
            inside_operation = True
        for child in _children(node):
            yield from _recurse(child, inside_operation)

    yield from _recurse(expression, False)


def _operation_dedupe_key(operation: Dict[str, Any]) -> tuple:
    join_predicates = tuple(
        (
            item.get("table") if isinstance(item, dict) else str(item),
            item.get("join_type") if isinstance(item, dict) else "",
            item.get("predicate") if isinstance(item, dict) else "",
        )
        for item in operation.get("join_predicates", []) or []
    )
    exists_predicates = tuple(
        (
            item.get("kind") if isinstance(item, dict) else str(item),
            item.get("predicate") if isinstance(item, dict) else "",
            tuple(item.get("subquery_tables", []) or []) if isinstance(item, dict) else (),
        )
        for item in operation.get("exists_predicates", []) or []
    )
    return (
        operation.get("operation"),
        operation.get("table"),
        tuple(operation.get("target_columns", []) or []),
        tuple(operation.get("source_columns", []) or []),
        operation.get("where_predicate") or "",
        operation.get("having_predicate") or "",
        join_predicates,
        exists_predicates,
        tuple(operation.get("constants", []) or []),
    )


_JOIN_KEYWORDS_RE = re.compile(
    r"(?is)\b(?:INNER\s+JOIN|LEFT\s+(?:OUTER\s+)?JOIN|RIGHT\s+(?:OUTER\s+)?JOIN|"
    r"FULL\s+(?:OUTER\s+)?JOIN|OUTER\s+JOIN|CROSS\s+JOIN|JOIN)\b"
)


def _extract_from_clause_alias_map(from_text: str) -> Dict[str, str]:
    """Parse a raw `FROM ... JOIN ...` clause fragment (regex-fallback path
    only - the sqlglot AST path resolves aliases structurally already) and
    return {ALIAS_UPPER: real_table_name}. Best-effort: any segment that
    doesn't cleanly match "<table> [AS] <alias>" is skipped rather than
    guessed at.
    """
    if not from_text:
        return {}
    alias_map: Dict[str, str] = {}
    for segment in _JOIN_KEYWORDS_RE.split(from_text):
        # A base FROM clause can list multiple comma-separated tables; a
        # JOIN segment carries its own ON predicate that must be stripped
        # first so it doesn't get swallowed into the alias match.
        before_on = re.split(r"(?is)\bON\b", segment, maxsplit=1)[0]
        for candidate in before_on.split(","):
            match = re.match(
                rf"(?is)\s*(?P<table>{_TABLE_REF_PATTERN})\s*(?:(?:AS\s+)?(?P<alias>\w+))?\s*$",
                candidate.strip(),
            )
            if not match:
                continue
            alias = (match.group("alias") or "").strip()
            table_ref = match.group("table").strip()
            if alias and alias.upper() not in _TABLE_ALIAS_STOPWORDS:
                alias_map[alias.upper()] = table_ref
    return alias_map


def _find_top_level_keyword(masked_text: str, keyword: str, start: int = 0) -> int:
    """Return the index of the first standalone occurrence of `keyword`
    (matched as a whole word, case-insensitively, against `masked_text`)
    that sits at parenthesis depth 0, scanning forward from `start`.
    Returns -1 if not found.

    Depth is computed from the very beginning of `masked_text` (not from
    `start`) so parens opened earlier in the string are still accounted
    for correctly.
    """
    depth = 0
    for i in range(0, min(start, len(masked_text))):
        ch = masked_text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)

    n = len(masked_text)
    kw = keyword.upper()
    kw_len = len(kw)
    i = start
    while i < n:
        ch = masked_text[i]
        if ch == "(":
            depth += 1
            i += 1
            continue
        if ch == ")":
            depth = max(depth - 1, 0)
            i += 1
            continue
        if depth == 0 and masked_text[i : i + kw_len].upper() == kw:
            before_ok = i == 0 or not (masked_text[i - 1].isalnum() or masked_text[i - 1] == "_")
            after_idx = i + kw_len
            after_ok = after_idx >= n or not (masked_text[after_idx].isalnum() or masked_text[after_idx] == "_")
            if before_ok and after_ok:
                return i
        i += 1
    return -1


def _regex_fallback_table_operations(
    *,
    statement_text: str,
    statement_id: str,
    chunk: CodeChunk,
    dialect: str,
) -> List[Dict[str, Any]]:
    text = _strip_sql_comments(statement_text)
    operations: List[Dict[str, Any]] = []

    select_match = re.search(
        rf"(?is)\bSELECT\b(?P<select>.*?)\bFROM\b\s+(?P<table>{_TABLE_REF_PATTERN})"
        + _OPTIONAL_ALIAS_GROUP.format(name="alias")
        + r"(?P<rest>.*?)(?=$|\bUPDATE\b|\bINSERT\b|\bDELETE\b|\bMERGE\b|\bDECLARE\b|\bSET\b|\bEND\b)",
        text,
    )
    if select_match:
        table = select_match.group("table")
        alias = select_match.group("alias") or ""
        if alias.upper() in _TABLE_ALIAS_STOPWORDS:
            alias = ""
        rest = select_match.group("rest") or ""
        where_match = re.search(
            r"(?is)\bWHERE\b(?P<where>.*?)(?=$|\bGROUP\b|\bORDER\b|\bHAVING\b|\bUPDATE\b|\bINSERT\b|\bDELETE\b|\bMERGE\b|\bDECLARE\b|\bSET\b|\bEND\b)",
            rest,
        )
        where_predicate = _normalize_clause_text(where_match.group("where")) if where_match else ""
        target_columns = _split_simple_select_columns(select_match.group("select"))
        operations.append(
            {
                "table": _normalize_table_reference_text(table.strip(), text),
                "table_alias": alias,
                "operation": "READ",
                "statement_kind": "SELECT",
                "source_statement_id": statement_id,
                "statement_id": statement_id,
                "source_statement_text": statement_text,
                "source_chunk_id": chunk.chunk_id,
                "source_chunk_kind": chunk.kind,
                "source_chunk_context": list(chunk.context_path or []),
                "target_columns": target_columns,
                "source_columns": target_columns,
                "columns": _unique_preserve(target_columns),
                "where_predicate": where_predicate,
                "filter_condition": where_predicate or None,
                "having_predicate": None,
                "join_predicates": [],
                "exists_predicates": [],
                "constants": _extract_simple_constants(text),
                "active_status": "ACTIVE",
                "confidence": "medium",
                "provenance": {
                    "chunk_id": chunk.chunk_id,
                    "chunk_kind": chunk.kind,
                    "chunk_context": list(chunk.context_path or []),
                    "statement_id": statement_id,
                    "statement_kind": "SELECT",
                    "statement_text": statement_text,
                    "statement_parse_status": "regex_fallback",
                    "dialect": dialect,
                    "table_occurrence": 1,
                },
            }
        )

    update_head_match = re.search(
        rf"(?is)\bUPDATE\s+(?P<table>{_TABLE_REF_PATTERN})"
        + _OPTIONAL_ALIAS_GROUP.format(name="alias")
        + r"\s+SET\s+",
        text,
    )
    if update_head_match:
        table = update_head_match.group("table")
        alias = update_head_match.group("alias") or ""
        set_start = update_head_match.end()
        masked_full = CodeIngestionAgent._mask_strings_and_comments(
            text, mask_brackets=(str(dialect).lower() != "tsql")
        )

        from_idx = _find_top_level_keyword(masked_full, "FROM", set_start)
        where_idx = _find_top_level_keyword(masked_full, "WHERE", set_start)

        if from_idx != -1 and (where_idx == -1 or from_idx < where_idx):
            set_part = text[set_start:from_idx]
            from_end = where_idx if where_idx != -1 else len(text)
            from_part = text[from_idx + 4 : from_end]
            where_part = _normalize_clause_text(text[where_idx + 5 :]) if where_idx != -1 else ""
        elif where_idx != -1:
            set_part = text[set_start:where_idx]
            from_part = ""
            where_part = _normalize_clause_text(text[where_idx + 5 :])
        else:
            set_part = text[set_start:]
            from_part = ""
            where_part = ""

        target_columns = _split_update_target_columns(set_part)

        # T-SQL allows `UPDATE <alias> SET ... FROM <real_table> <alias> JOIN ...`.
        # In that shape the token right after UPDATE is an alias, not a table
        # name - resolve it against the FROM/JOIN clause before falling back
        # to using it verbatim, so the report never shows a bare alias (A, B,
        # AA...) in place of the real table.
        alias_map = _extract_from_clause_alias_map(from_part)
        resolved_table = alias_map.get(table.strip().upper())
        if resolved_table:
            final_table = resolved_table
            final_alias = table.strip()
        else:
            final_table = table.strip()
            final_alias = alias

        operations.append(
            {
                "table": _normalize_table_reference_text(final_table, text),
                "table_alias": final_alias,
                "operation": "UPDATE",
                "statement_kind": "UPDATE",
                "source_statement_id": statement_id,
                "statement_id": statement_id,
                "source_statement_text": statement_text,
                "source_chunk_id": chunk.chunk_id,
                "source_chunk_kind": chunk.kind,
                "source_chunk_context": list(chunk.context_path or []),
                "target_columns": target_columns,
                "source_columns": _extract_simple_columns(text, exclude=target_columns),
                "columns": _unique_preserve(target_columns),
                "where_predicate": where_part,
                "filter_condition": where_part or None,
                "having_predicate": None,
                "join_predicates": [],
                "exists_predicates": [],
                "constants": _extract_simple_constants(text),
                "active_status": "ACTIVE",
                "confidence": "medium",
                "provenance": {
                    "chunk_id": chunk.chunk_id,
                    "chunk_kind": chunk.kind,
                    "chunk_context": list(chunk.context_path or []),
                    "statement_id": statement_id,
                    "statement_kind": "UPDATE",
                    "statement_text": statement_text,
                    "statement_parse_status": "regex_fallback",
                    "dialect": dialect,
                    "table_occurrence": 1,
                },
            }
        )

    insert_match = re.search(
        rf"(?is)\bINSERT\s+INTO\s+(?P<table>{_TABLE_REF_PATTERN})\s*"
        r"(?:\((?P<cols>[^()]*)\))?\s*(?P<rest>.*?)"
        r"(?=$|\bUPDATE\b|\bINSERT\b|\bDELETE\b|\bMERGE\b|\bDECLARE\b|\bEND\b)",
        text,
    )
    if insert_match:
        table = insert_match.group("table")
        cols_text = insert_match.group("cols") or ""
        rest = insert_match.group("rest") or ""
        target_columns = _unique_preserve([c.strip() for c in cols_text.split(",") if c.strip()])
        select_in_rest = re.search(r"(?is)\bSELECT\b(?P<select>.*?)\bFROM\b", rest)
        source_columns = (
            _split_simple_select_columns(select_in_rest.group("select")) if select_in_rest else []
        )
        if not target_columns and source_columns:
            # `INSERT INTO table SELECT col1, col2 ...` with no explicit
            # column list - the selected columns are the effective targets.
            target_columns = list(source_columns)
        operations.append(
            {
                "table": _normalize_table_reference_text(table.strip(), text),
                "table_alias": "",
                "operation": "INSERT",
                "statement_kind": "INSERT",
                "source_statement_id": statement_id,
                "statement_id": statement_id,
                "source_statement_text": statement_text,
                "source_chunk_id": chunk.chunk_id,
                "source_chunk_kind": chunk.kind,
                "source_chunk_context": list(chunk.context_path or []),
                "target_columns": target_columns,
                "source_columns": source_columns,
                "columns": _unique_preserve(target_columns),
                "where_predicate": None,
                "filter_condition": None,
                "having_predicate": None,
                "join_predicates": [],
                "exists_predicates": [],
                "constants": _extract_simple_constants(text),
                "active_status": "ACTIVE",
                "confidence": "medium",
                "provenance": {
                    "chunk_id": chunk.chunk_id,
                    "chunk_kind": chunk.kind,
                    "chunk_context": list(chunk.context_path or []),
                    "statement_id": statement_id,
                    "statement_kind": "INSERT",
                    "statement_text": statement_text,
                    "statement_parse_status": "regex_fallback",
                    "dialect": dialect,
                    "table_occurrence": 1,
                },
            }
        )

    delete_match = re.search(
        rf"(?is)\bDELETE\s+(?:(?P<pre_alias>\w+)\s+)?FROM\s+(?P<table>{_TABLE_REF_PATTERN})"
        + _OPTIONAL_ALIAS_GROUP.format(name="post_alias")
        + r"(?P<rest>.*?)"
        r"(?=$|\bUPDATE\b|\bINSERT\b|\bDELETE\b|\bMERGE\b|\bDECLARE\b|\bEND\b)",
        text,
    )
    if delete_match:
        table = delete_match.group("table")
        pre_alias = delete_match.group("pre_alias") or ""
        post_alias = delete_match.group("post_alias") or ""
        rest = delete_match.group("rest") or ""
        where_match = re.search(r"(?is)\bWHERE\b(?P<where>.*)$", rest)
        where_predicate = _normalize_clause_text(where_match.group("where")) if where_match else ""
        alias = post_alias or pre_alias
        if alias.upper() in _TABLE_ALIAS_STOPWORDS:
            alias = ""
        operations.append(
            {
                "table": _normalize_table_reference_text(table.strip(), text),
                "table_alias": alias,
                "operation": "DELETE",
                "statement_kind": "DELETE",
                "source_statement_id": statement_id,
                "statement_id": statement_id,
                "source_statement_text": statement_text,
                "source_chunk_id": chunk.chunk_id,
                "source_chunk_kind": chunk.kind,
                "source_chunk_context": list(chunk.context_path or []),
                "target_columns": [],
                "source_columns": _extract_simple_columns(text),
                "columns": [],
                "where_predicate": where_predicate,
                "filter_condition": where_predicate or None,
                "having_predicate": None,
                "join_predicates": [],
                "exists_predicates": [],
                "constants": _extract_simple_constants(text),
                "active_status": "ACTIVE",
                "confidence": "medium",
                "provenance": {
                    "chunk_id": chunk.chunk_id,
                    "chunk_kind": chunk.kind,
                    "chunk_context": list(chunk.context_path or []),
                    "statement_id": statement_id,
                    "statement_kind": "DELETE",
                    "statement_text": statement_text,
                    "statement_parse_status": "regex_fallback",
                    "dialect": dialect,
                    "table_occurrence": 1,
                },
            }
        )

    return operations


def _split_simple_select_columns(select_text: str) -> List[str]:
    return _unique_preserve([part.strip() for part in str(select_text or "").split(",") if part.strip()])


def _split_update_target_columns(set_text: str) -> List[str]:
    cols = []
    for match in re.finditer(r"(?is)(?:^|,)\s*([#\w.\[\]]+)\s*=", set_text):
        cols.append(match.group(1).strip())
    return _unique_preserve(cols)


def _extract_simple_columns(text: str, exclude: Sequence[str] | None = None) -> List[str]:
    exclude_set = {str(item).strip() for item in (exclude or [])}
    cols = []
    for match in re.finditer(r"(?<![@#])\b([A-Za-z_][A-Za-z0-9_\.]*)\b", text):
        candidate = match.group(1)
        if candidate.upper() in {
            "SELECT",
            "FROM",
            "WHERE",
            "UPDATE",
            "INSERT",
            "DELETE",
            "MERGE",
            "SET",
            "AND",
            "OR",
            "NOT",
            "NULL",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
            "BEGIN",
            "DECLARE",
            "AS",
            "ON",
            "INTO",
            "EXISTS",
        }:
            continue
        if candidate in exclude_set:
            continue
        cols.append(candidate)
    return _unique_preserve(cols)


def _extract_simple_constants(text: str) -> List[str]:
    constants = re.findall(r"'(?:''|[^'])*'|\b\d+\b", text)
    return _unique_preserve(constants)


def _normalize_clause_text(text: str) -> str:
    cleaned = _strip_sql_comments(text)
    cleaned = re.split(r"(?i)\b(?:END\b|GO\b|DECLARE\b|SET NOCOUNT OFF\b)", cleaned, maxsplit=1)[0]
    return re.sub(r"\s+", " ", cleaned).strip()


def _build_operation_record(
    *,
    operation: str,
    table: exp.Table,
    target_columns: Sequence[str],
    source_columns: Sequence[str],
    where_predicate: str,
    having_predicate: str,
    join_predicates: Sequence[Dict[str, Any]],
    exists_predicates: Sequence[Dict[str, Any]],
    constants: Sequence[str],
    statement_kind: str,
    statement_text: str,
    statement_id: str,
    chunk: CodeChunk,
    dialect: str,
    table_occurrence: int,
    assigned_values: Sequence[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    table_name = _normalize_table_name_with_text(table, statement_text)
    table_alias = _table_alias(table)
    target_columns = _unique_preserve([str(v).strip() for v in target_columns if str(v).strip()])
    source_columns = _unique_preserve([str(v).strip() for v in source_columns if str(v).strip()])
    combined_columns = _unique_preserve(list(target_columns) + list(source_columns))
    return {
        "table": table_name,
        "table_alias": table_alias,
        "operation": operation,
        "statement_kind": statement_kind,
        "source_statement_id": statement_id,
        "statement_id": statement_id,
        "source_statement_text": statement_text,
        "source_chunk_id": chunk.chunk_id,
        "source_chunk_kind": chunk.kind,
        "source_chunk_context": list(chunk.context_path or []),
        "source_file": getattr(chunk, "source_filename", "") or "",
        "source_char_start": getattr(chunk, "source_char_start", -1),
        "source_char_end": getattr(chunk, "source_char_end", -1),
        "source_line_start": getattr(chunk, "source_line_start", -1),
        "source_line_end": getattr(chunk, "source_line_end", -1),
        "source_location_status": getattr(chunk, "source_location_status", "unavailable"),
        "target_columns": list(target_columns),
        "source_columns": list(source_columns),
        "columns": combined_columns,
        "where_predicate": where_predicate,
        "filter_condition": where_predicate or None,
        "having_predicate": having_predicate or None,
        "join_predicates": list(join_predicates),
        "exists_predicates": list(exists_predicates),
        "constants": list(constants),
        "assigned_values": list(assigned_values or []),
        "active_status": "ACTIVE",
        "confidence": "high",
        "provenance": {
            "chunk_id": chunk.chunk_id,
            "chunk_kind": chunk.kind,
            "chunk_context": list(chunk.context_path or []),
            "statement_id": statement_id,
            "statement_kind": statement_kind,
            "statement_text": statement_text,
            "statement_parse_status": "parsed",
            "dialect": dialect,
            "table_occurrence": table_occurrence,
            "source_file": getattr(chunk, "source_filename", "") or "",
            "source_char_start": getattr(chunk, "source_char_start", -1),
            "source_char_end": getattr(chunk, "source_char_end", -1),
            "source_line_start": getattr(chunk, "source_line_start", -1),
            "source_line_end": getattr(chunk, "source_line_end", -1),
            "source_location_status": getattr(chunk, "source_location_status", "unavailable"),
        },
    }


def _resolve_insert_target(tree: exp.Insert, dialect: str) -> tuple[Optional[exp.Table], List[str]]:
    schema = tree.args.get("this")
    if isinstance(schema, exp.Schema):
        target = schema.this if isinstance(schema.this, exp.Table) else None
        columns = [col.sql(dialect=dialect) for col in schema.expressions or []]
        return target, columns
    if isinstance(schema, exp.Table):
        return schema, []
    return None, []


def _resolve_update_target(tree: exp.Update, dialect: str) -> Optional[exp.Table]:
    target_alias = _table_alias(tree.this) if isinstance(tree.this, exp.Table) else _normalize_table_name(tree.this)
    target_alias_key = target_alias.upper()
    from_tables = _collect_table_nodes(tree)
    alias_matches: List[exp.Table] = []
    for table in from_tables:
        table_alias_key = _table_alias(table).upper()
        table_name_key = _normalize_table_name(table).upper()
        if table_alias_key != target_alias_key and table_name_key != target_alias_key:
            continue
        if table_name_key != target_alias_key or table.db:
            alias_matches.append(table)
    if alias_matches:
        return alias_matches[0]
    return tree.this if isinstance(tree.this, exp.Table) else None


def _resolve_delete_target(tree: exp.Delete, dialect: str) -> Optional[exp.Table]:
    if isinstance(tree.this, exp.Table):
        return tree.this
    if isinstance(tree.this, exp.Schema) and isinstance(tree.this.this, exp.Table):
        return tree.this.this
    return None


def _resolve_merge_target(tree: exp.Merge, dialect: str) -> Optional[exp.Table]:
    if isinstance(tree.this, exp.Table):
        return tree.this
    return None


def _source_tables(tree: exp.Expression, target_table: Optional[exp.Table]) -> List[exp.Table]:
    target_signature = _table_signature(target_table) if target_table is not None else ""
    target_alias_key = (_table_alias(target_table) if target_table is not None else "").upper()
    tables = []
    seen: set[tuple[str, str]] = set()
    for table in _collect_table_nodes(tree):
        signature = _table_signature(table)
        alias = _table_alias(table)
        if signature == target_signature or alias.upper() == target_alias_key:
            continue
        key = (signature, alias)
        if key in seen:
            continue
        seen.add(key)
        tables.append(table)
    return tables


def _collect_table_nodes(tree: exp.Expression) -> List[exp.Table]:
    tables: List[exp.Table] = []
    seen: set[tuple[str, str]] = set()
    for table in tree.find_all(exp.Table):
        key = (_table_signature(table), _table_alias(table))
        if key in seen:
            continue
        seen.add(key)
        tables.append(table)
    return tables


def _render_select_projection_columns(tree: Optional[exp.Expression], dialect: str) -> List[str]:
    if tree is None:
        return []
    if isinstance(tree, exp.Select):
        return _unique_preserve(
            [proj.sql(dialect=dialect) for proj in (tree.expressions or []) if proj is not None]
        )
    return _render_all_columns(tree, dialect)


def _render_update_target_columns(tree: exp.Update, dialect: str) -> List[str]:
    cols: List[str] = []
    for assignment in tree.args.get("expressions") or []:
        if isinstance(assignment, exp.Expression):
            left = assignment.args.get("this")
            if left is not None:
                cols.append(left.sql(dialect=dialect))
    return _unique_preserve(cols)


def _render_update_assigned_values(tree: exp.Update, dialect: str) -> List[Dict[str, str]]:
    pairs: List[Dict[str, str]] = []
    for assignment in tree.args.get("expressions") or []:
        if not isinstance(assignment, exp.Expression):
            continue
        left = assignment.args.get("this")
        right = assignment.args.get("expression")
        if left is None or right is None:
            continue
        pairs.append(
            {
                "column": left.sql(dialect=dialect),
                "expression": right.sql(dialect=dialect),
            }
        )
    return pairs


def _render_join_predicates(tree: exp.Expression, dialect: str) -> List[Dict[str, Any]]:
    joins = []
    for join in tree.find_all(exp.Join):
        if not isinstance(join, exp.Join):
            continue
        joins.append(
            {
                "table": _normalize_table_name(join.this) if isinstance(join.this, exp.Table) else join.this.sql(dialect=dialect),
                "table_alias": _table_alias(join.this) if isinstance(join.this, exp.Table) else "",
                "join_type": _join_type(join),
                "predicate": _render_expression(join.args.get("on"), dialect),
            }
        )
    return joins


def _render_exists_predicates(tree: exp.Expression, dialect: str) -> List[Dict[str, Any]]:
    predicates: List[Dict[str, Any]] = []
    handled_exists_ids: set[int] = set()
    for node in tree.walk():
        if isinstance(node, exp.Exists):
            if id(node) in handled_exists_ids:
                continue
            handled_exists_ids.add(id(node))
            predicates.append(
                {
                    "kind": "EXISTS",
                    "predicate": node.sql(dialect=dialect),
                    "subquery_tables": _tables_in_expression(node.this, dialect),
                }
            )
        elif isinstance(node, exp.Not) and isinstance(node.this, exp.Exists):
            exists = node.this
            handled_exists_ids.add(id(exists))
            predicates.append(
                {
                    "kind": "NOT EXISTS",
                    "predicate": node.sql(dialect=dialect),
                    "subquery_tables": _tables_in_expression(exists.this, dialect),
                }
            )
    return predicates


def _tables_in_expression(expression: Optional[exp.Expression], dialect: str) -> List[str]:
    if expression is None:
        return []
    return _unique_preserve([_normalize_table_name(table) for table in expression.find_all(exp.Table)])


def _render_all_columns(expression: Optional[exp.Expression], dialect: str) -> List[str]:
    if expression is None:
        return []
    return [column.sql(dialect=dialect) for column in expression.find_all(exp.Column)]


def _render_all_literals(expression: Optional[exp.Expression], dialect: str) -> List[str]:
    if expression is None:
        return []
    literals: List[str] = []
    for node in expression.walk():
        if isinstance(node, exp.Literal):
            literals.append(node.sql(dialect=dialect))
        elif isinstance(node, exp.Boolean):
            literals.append(node.sql(dialect=dialect))
        elif isinstance(node, exp.Null):
            literals.append("NULL")
    return literals


def _render_expression(expression: Optional[exp.Expression], dialect: str) -> str:
    if expression is None:
        return ""
    if isinstance(expression, exp.Where):
        expression = expression.this
    elif isinstance(expression, exp.Having):
        expression = expression.this
    return expression.sql(dialect=dialect) if expression is not None else ""


def _table_alias(table: Optional[exp.Table]) -> str:
    if not isinstance(table, exp.Table):
        return ""
    alias = table.alias_or_name or table.name or ""
    return str(alias).strip()


def _table_signature(table: Optional[exp.Table]) -> str:
    if not isinstance(table, exp.Table):
        return ""
    parts = []
    if table.db:
        parts.append(str(table.db))
    if table.name:
        parts.append(str(table.name))
    return ".".join(parts) if parts else table.sql()


def _normalize_table_name(table: Any) -> str:
    return _normalize_table_name_with_text(table, "")


def _normalize_table_name_with_text(table: Any, statement_text: str) -> str:
    if isinstance(table, exp.Table):
        parts: List[str] = []
        if table.db:
            parts.append(str(table.db).strip())
        if table.name:
            parts.append(str(table.name).strip())
        if not parts and table.this is not None:
            parts.append(str(table.this).strip())
        name = ".".join(part for part in parts if part)
        if not name:
            name = table.sql(dialect="tsql")
        return _restore_temp_table_prefix(name, statement_text)
    if table is None:
        return ""
    return _restore_temp_table_prefix(str(table), statement_text)


def _restore_temp_table_prefix(table_name: str, statement_text: str) -> str:
    text = str(table_name or "").strip()
    if not text:
        return text
    if text.startswith("#"):
        return text
    if not statement_text:
        return text
    for prefix in ("##", "#"):
        pattern = rf"(?<![\w#]){re.escape(prefix)}{re.escape(text)}(?![\w])"
        if re.search(pattern, statement_text):
            return f"{prefix}{text}"
    return text


def _normalize_table_reference_text(table_name: str, statement_text: str) -> str:
    text = str(table_name or "").strip()
    if not text:
        return text

    text = _restore_temp_table_prefix(text, statement_text)
    parts = [part.strip() for part in re.split(r"\s*\.\s*", text) if part.strip()]
    if not parts:
        return text

    normalized_parts = []
    for part in parts:
        cleaned = part.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1].replace("]]", "]")
        elif cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1].replace('""', '"')
        normalized_parts.append(cleaned)

    normalized = ".".join(normalized_parts)
    return _restore_temp_table_prefix(normalized, statement_text)


def _join_type(join: exp.Join) -> str:
    if join.args.get("kind"):
        return str(join.args.get("kind")).upper()
    side = join.args.get("side")
    if side:
        return f"{str(side).upper()} JOIN"
    return "JOIN"


def _unique_preserve(values: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
