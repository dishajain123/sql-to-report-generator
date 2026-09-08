"""Conservative statement-order dependencies over deterministic SQL facts."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple


_WRITE_OPERATIONS = {"INSERT", "UPDATE", "MERGE"}
_CONSUMER_OPERATIONS = {"READ", "INSERT", "UPDATE", "MERGE", "DELETE"}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: Any) -> str:
    return _text(value).upper()


def _list(value: Any) -> List[str]:
    if isinstance(value, str):
        value = [value]
    return [_text(item) for item in (value or []) if _text(item)]


def _statement_id(row: Dict[str, Any]) -> str:
    return _text(row.get("statement_id") or row.get("source_statement_id"))


def _fields(row: Dict[str, Any]) -> List[str]:
    values = _list(row.get("target_columns") or row.get("columns"))
    for assignment in row.get("assigned_values") or []:
        if isinstance(assignment, dict):
            values.append(_text(assignment.get("column") or assignment.get("field")))
    result: List[str] = []
    for value in values:
        if value and _norm(value) not in {_norm(item) for item in result}:
            result.append(value)
    return result


def _order_key(row: Dict[str, Any], fallback: int) -> Tuple[int, int, int]:
    """Return a stable source order; unknown locations never imply order."""
    for key in ("source_char_start", "char_start", "source_line_start", "line_start"):
        try:
            value = int(row.get(key, -1))
        except (TypeError, ValueError):
            value = -1
        if value >= 0:
            return (0, value, fallback)
    return (1, fallback, fallback)


def _location(row: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key in (
        "source_file",
        "source_line_start",
        "source_line_end",
        "source_char_start",
        "source_char_end",
        "source_chunk_id",
        "source_statement_id",
        "statement_id",
    ):
        if row.get(key) not in (None, "", -1):
            result[key] = row[key]
    return result


def _endpoint(row: Dict[str, Any], *, order: int) -> Dict[str, Any]:
    return {
        "statement_id": _statement_id(row),
        "operation": _norm(row.get("operation")),
        "table": _text(row.get("table")),
        "fields": _fields(row),
        "order": order,
        "location": _location(row),
    }


def build_statement_dependencies(
    table_operations: Sequence[Dict[str, Any]],
    statement_provenance: Sequence[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    """Build only high-confidence dependencies from existing operation facts.

    Confirmed relationships require an exact normalized table match and two
    distinct statements with known source order. Same-field update edges are
    confirmed only for unconditional assignments; conditional overlaps remain
    unresolved rather than being treated as overrides.
    """
    provenance_order: Dict[str, Dict[str, Any]] = {}
    for index, statement in enumerate(statement_provenance or []):
        if not isinstance(statement, dict):
            continue
        statement_id = _statement_id(statement)
        if statement_id:
            provenance_order[statement_id] = {**statement, "_fallback_order": index}

    rows: List[Dict[str, Any]] = []
    for index, operation in enumerate(table_operations or []):
        if not isinstance(operation, dict):
            continue
        row = dict(operation)
        statement_id = _statement_id(row)
        if statement_id in provenance_order:
            row = {**provenance_order[statement_id], **row}
        row["_order_key"] = _order_key(row, index)
        row["_row_index"] = index
        rows.append(row)
    rows.sort(key=lambda row: row["_order_key"])

    edges: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []
    seen_edges: set[tuple] = set()

    def add_edge(kind: str, before: Dict[str, Any], after: Dict[str, Any], reason: str) -> None:
        edge_key = (kind, _statement_id(before), _statement_id(after), _norm(before.get("table")), tuple(sorted(_norm(field) for field in _fields(before) if field)))
        if edge_key in seen_edges:
            return
        seen_edges.add(edge_key)
        edges.append({
            "dependency_id": f"dependency_{len(edges) + 1:04d}",
            "type": kind,
            "confidence": "high",
            "reason": reason,
            "from": _endpoint(before, order=before["_row_index"]),
            "to": _endpoint(after, order=after["_row_index"]),
        })

    for before_index, before in enumerate(rows):
        before_table = _norm(before.get("table"))
        before_operation = _norm(before.get("operation"))
        if not before_table or before_operation not in _WRITE_OPERATIONS:
            continue
        for after in rows[before_index + 1 :]:
            after_table = _norm(after.get("table"))
            after_operation = _norm(after.get("operation"))
            if not after_table or before_table != after_table:
                continue
            before_id = _statement_id(before)
            after_id = _statement_id(after)
            if not before_id or not after_id or before_id == after_id:
                continue
            if before["_order_key"][0] != 0 or after["_order_key"][0] != 0:
                unresolved.append({
                    "type": "unknown_statement_order",
                    "table": before.get("table"),
                    "from_statement_id": before_id,
                    "to_statement_id": after_id,
                })
                continue
            if before_operation == "UPDATE" and after_operation == "UPDATE":
                shared_fields = {
                    _norm(field)
                    for field in _fields(before)
                    if _norm(field) in {_norm(item) for item in _fields(after)}
                }
                if shared_fields:
                    before_predicate = _text(before.get("where_predicate") or before.get("filter_condition"))
                    after_predicate = _text(after.get("where_predicate") or after.get("filter_condition"))
                    if not before_predicate and not after_predicate:
                        add_edge(
                            "later_update_overrides_field",
                            before,
                            after,
                            "Later unconditional UPDATE targets the same field as an earlier UPDATE.",
                        )
                    else:
                        unresolved.append({
                            "type": "conditional_field_overlap",
                            "table": before.get("table"),
                            "fields": sorted(shared_fields),
                            "from_statement_id": before_id,
                            "to_statement_id": after_id,
                            "reason": "Both statements target the same field but predicates prevent proving override order for all rows.",
                        })
                    continue
                # Same-table updates with disjoint target fields are
                # intentionally independent; table identity alone is not a
                # dependency signal for this pair.
                continue
            if after_operation in _CONSUMER_OPERATIONS:
                is_temp = before_table.startswith("#") or "TEMP" in before_table or "TMP" in before_table
                consumer_kind = _norm(after.get("statement_kind"))
                if consumer_kind == "MERGE" or after_operation == "MERGE":
                    kind = "staging_write_to_merge"
                    reason = "An earlier exact-table write is consumed by a later MERGE statement."
                else:
                    kind = "temp_write_to_read" if is_temp and after_operation == "READ" else "table_write_to_later_use"
                    reason = "An earlier exact-table write precedes a later use of the same table."
                add_edge(kind, before, after, reason)


    return {
        "version": "1",
        "edge_count": len(edges),
        "edges": edges,
        "unresolved_count": len(unresolved),
        "unresolved": unresolved,
    }
