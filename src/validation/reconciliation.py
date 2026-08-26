from __future__ import annotations

from dataclasses import dataclass, field, asdict
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.validation.confidence import derive_business_rule_confidence, normalize_confidence
from src.dialect.detector import AMBIGUOUS, ORACLE, TSQL, UNKNOWN, UNSUPPORTED, normalize_dialect_name
from src.core.pipeline_utils import stable_id


RECONCILIATION_STATUSES = {
    "MATCHED",
    "DETERMINISTIC_ONLY",
    "LLM_ONLY",
    "CONFLICT",
    "UNRESOLVED",
}

CONTRADICTION_SEVERITIES = {"HIGH", "MEDIUM", "LOW"}
CONTRADICTION_TYPES = {
    "condition_conflict",
    "outcome_conflict",
    "field_conflict",
    "table_conflict",
    "operation_conflict",
    "rule_vs_rule_conflict",
    "cross_chunk_conflict",
}

_SIMPLE_CONDITION_RE = re.compile(
    r"^(?P<lhs>[A-Z0-9_.\[\]#$]+)\s*(?P<op>>=|<=|<>|!=|=|>|<|IN|NOT IN)\s*(?P<rhs>.+)$",
    re.IGNORECASE,
)
_SIMPLE_ASSIGNMENT_RE = re.compile(
    r"^(?P<lhs>[A-Z0-9_.\[\]#$]+)\s*(?P<op>:=|=)\s*(?P<rhs>.+)$",
    re.IGNORECASE,
)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_value(value: Any) -> str:
    return _clean_text(value).lower()


def _normalize_list(values: Sequence[Any]) -> List[str]:
    cleaned = []
    for value in values or []:
        text = _clean_text(value)
        if text:
            cleaned.append(text)
    return cleaned


def _normalize_set(values: Sequence[Any]) -> set[str]:
    return { _normalize_value(v) for v in _normalize_list(values) if _normalize_value(v) }


def _row_columns(row: Dict[str, Any]) -> List[str]:
    cols = row.get("target_columns") or row.get("columns") or []
    return _normalize_list(cols)


def _row_operation(row: Dict[str, Any]) -> str:
    return _normalize_value(row.get("operation") or "")


def _row_filter(row: Dict[str, Any]) -> str:
    return _normalize_value(
        row.get("filter_condition")
        or row.get("where_predicate")
        or row.get("trigger_condition")
        or ""
    )


def _row_assigned_values(row: Dict[str, Any]) -> List[str]:
    values = []
    for item in row.get("assigned_values") or []:
        if not isinstance(item, dict):
            continue
        expression = _clean_text(item.get("expression"))
        if expression:
            values.append(expression)
    return values


def _row_assigned_pairs(row: Dict[str, Any]) -> List[Dict[str, str]]:
    pairs: List[Dict[str, str]] = []
    for item in row.get("assigned_values") or []:
        if not isinstance(item, dict):
            continue
        column = _clean_text(item.get("column") or item.get("target_column") or item.get("field"))
        expression = _clean_text(item.get("expression"))
        if column or expression:
            pairs.append({"column": column, "expression": expression})
    return pairs


def _rule_claim_fields(rule: Dict[str, Any]) -> List[str]:
    fields = []
    output_field = _clean_text(rule.get("output_field"))
    if output_field:
        fields.append(output_field)
    fields.extend(_normalize_list(rule.get("fields_affected") or []))
    return _normalize_list(fields)


def _rule_claim_conditions(rule: Dict[str, Any]) -> List[str]:
    claims = []
    claims.extend(_normalize_list(rule.get("eligibility") or []))
    condition = _clean_text(rule.get("condition"))
    if condition:
        claims.append(condition)
    for row in rule.get("decision_logic_rows") or []:
        if not isinstance(row, dict):
            continue
        cond = _clean_text(row.get("condition") or row.get("when") or row.get("if"))
        if cond:
            claims.append(cond)
    return _normalize_list(claims)


def _rule_claim_outcomes(rule: Dict[str, Any]) -> List[str]:
    claims = []
    action = _clean_text(rule.get("action"))
    if action:
        claims.append(action)
    for row in rule.get("decision_logic_rows") or []:
        if not isinstance(row, dict):
            continue
        outcome = _clean_text(row.get("outcome") or row.get("then") or row.get("result"))
        if outcome:
            claims.append(outcome)
    return _normalize_list(claims)


def _strip_outer_parentheses(text: str) -> str:
    cleaned = _clean_text(text)
    while cleaned.startswith("(") and cleaned.endswith(")"):
        candidate = cleaned[1:-1].strip()
        if not candidate:
            break
        depth = 0
        balanced = True
        for char in candidate:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth < 0:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        cleaned = candidate
    return cleaned


def _strip_quotes(text: str) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned


def _parse_structured_comparison(text: Any) -> Optional[Dict[str, str]]:
    cleaned = _strip_outer_parentheses(str(text or ""))
    match = _SIMPLE_CONDITION_RE.match(cleaned)
    if not match:
        return None
    lhs = _normalize_value(match.group("lhs"))
    op = match.group("op").upper().replace(" ", "")
    rhs = _normalize_value(_strip_quotes(match.group("rhs")))
    if not lhs or not op or not rhs:
        return None
    return {"lhs": lhs, "op": op, "rhs": rhs, "raw": _clean_text(text)}


def _parse_structured_assignment(text: Any) -> Optional[Dict[str, str]]:
    cleaned = _strip_outer_parentheses(str(text or ""))
    match = _SIMPLE_ASSIGNMENT_RE.match(cleaned)
    if not match:
        return None
    lhs = _normalize_value(match.group("lhs"))
    rhs = _normalize_value(_strip_quotes(match.group("rhs")))
    if not lhs or not rhs:
        return None
    return {"lhs": lhs, "op": match.group("op"), "rhs": rhs, "raw": _clean_text(text)}


def _source_identity(row: Dict[str, Any]) -> Tuple[str, str]:
    return (_chunk_id_from_row(row), _statement_id_from_row(row))


def _same_source_identity(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    left_chunk, left_statement = _source_identity(left)
    right_chunk, right_statement = _source_identity(right)
    return bool(
        (left_chunk and right_chunk and left_chunk == right_chunk)
        or (left_statement and right_statement and left_statement == right_statement)
    )


def _rule_source_identity(rule: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    chunks = [str(chunk).strip() for chunk in rule.get("source_chunks") or [] if str(chunk).strip()]
    statements = [str(ref).strip() for ref in rule.get("technical_references") or [] if str(ref).strip()]
    return chunks, statements


def _structured_rule_conditions(rule: Dict[str, Any]) -> List[Dict[str, str]]:
    conditions: List[Dict[str, str]] = []
    for value in _rule_claim_conditions(rule):
        parsed = _parse_structured_comparison(value)
        if parsed:
            conditions.append(parsed)
    return conditions


def _structured_rule_outcomes(rule: Dict[str, Any]) -> List[Dict[str, str]]:
    outcomes: List[Dict[str, str]] = []
    for value in _rule_claim_outcomes(rule):
        parsed = _parse_structured_assignment(value)
        if parsed:
            outcomes.append(parsed)
    return outcomes


def _rule_signature(rule: Dict[str, Any]) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]:
    return (
        tuple(sorted(_normalize_set(_rule_claim_fields(rule)))),
        tuple(sorted({_clean_text(item.get("raw") or "") for item in _structured_rule_conditions(rule)})),
        tuple(sorted({_clean_text(item.get("raw") or "") for item in _structured_rule_outcomes(rule)})),
    )


def _rule_claim_tables(rule: Dict[str, Any]) -> List[str]:
    tables = []
    for evidence in rule.get("source_evidence") or []:
        evidence_text = _clean_text(evidence)
        if evidence_text:
            tables.append(evidence_text)
    return _normalize_list(tables)


def _table_row_signature(row: Dict[str, Any]) -> Tuple[str, str, Tuple[str, ...], str, Tuple[str, ...]]:
    return (
        _normalize_value(row.get("table") or ""),
        _row_operation(row),
        tuple(sorted(_normalize_set(_row_columns(row)))),
        _row_filter(row),
        tuple(sorted(_normalize_set(_row_assigned_values(row)))),
    )


def _table_rows_match(llm_row: Dict[str, Any], det_row: Dict[str, Any]) -> bool:
    if _normalize_value(llm_row.get("table") or "") != _normalize_value(det_row.get("table") or ""):
        return False
    if _row_operation(llm_row) and _row_operation(llm_row) != _row_operation(det_row):
        return False
    llm_cols = _normalize_set(_row_columns(llm_row))
    det_cols = _normalize_set(_row_columns(det_row))
    if llm_cols and det_cols and llm_cols != det_cols:
        return False
    llm_filter = _row_filter(llm_row)
    det_filter = _row_filter(det_row)
    if llm_filter and det_filter and llm_filter != det_filter:
        return False
    llm_values = _normalize_set(_row_assigned_values(llm_row))
    det_values = _normalize_set(_row_assigned_values(det_row))
    if llm_values and det_values and llm_values != det_values:
        return False
    return True


def _compare_rule_to_det(rule: Dict[str, Any], det_rows: Sequence[Dict[str, Any]]) -> Tuple[str, Dict[str, Any], Dict[str, Any], List[str]]:
    claim_fields = _rule_claim_fields(rule)
    claim_conditions = _rule_claim_conditions(rule)
    claim_outcomes = _rule_claim_outcomes(rule)

    matched_rows: List[Dict[str, Any]] = []
    comparable_rows: List[Dict[str, Any]] = []
    field_status = "UNRESOLVED"
    condition_status = "UNRESOLVED"
    outcome_status = "UNRESOLVED"

    source_chunks = {str(chunk).strip() for chunk in rule.get("source_chunks") or [] if str(chunk).strip()}
    source_evidence = {_normalize_value(e) for e in rule.get("source_evidence") or [] if _clean_text(e)}

    for row in det_rows:
        row_chunk = str(row.get("source_chunk_id") or "").strip()
        row_text = _normalize_value(row.get("source_statement_text") or row.get("filter_condition") or "")
        row_filter = _row_filter(row)
        row_values = _normalize_set(_row_assigned_values(row))
        row_fields = _normalize_set(_row_columns(row))

        chunk_match = bool(source_chunks and row_chunk and row_chunk in source_chunks)
        evidence_match = bool(source_evidence and (row_text in source_evidence or row_filter in source_evidence))
        if not (chunk_match or evidence_match):
            continue

        comparable_rows.append(row)
        if claim_fields:
            if row_fields and _normalize_set(claim_fields) == row_fields:
                field_status = "MATCHED" if field_status != "CONFLICT" else field_status
            elif row_fields:
                field_status = "CONFLICT"
        if claim_conditions:
            if row_filter and any(_normalize_value(c) == row_filter for c in claim_conditions):
                condition_status = "MATCHED" if condition_status != "CONFLICT" else condition_status
            elif row_filter:
                condition_status = "CONFLICT"
        if claim_outcomes:
            if row_values and any(_normalize_value(o) in row_values for o in claim_outcomes):
                outcome_status = "MATCHED" if outcome_status != "CONFLICT" else outcome_status
            elif row_values:
                outcome_status = "CONFLICT"
        matched_rows.append(row)

    if any(status == "CONFLICT" for status in (field_status, condition_status, outcome_status)):
        status = "CONFLICT"
    elif matched_rows and any(status == "MATCHED" for status in (field_status, condition_status, outcome_status)):
        status = "MATCHED"
    elif matched_rows:
        status = "UNRESOLVED"
    else:
        status = "LLM_ONLY"

    if not matched_rows and (claim_fields or claim_conditions or claim_outcomes):
        status = "LLM_ONLY"

    llm_claim = {
        "rule_name": rule.get("rule_name"),
        "output_field": rule.get("output_field"),
        "fields_affected": list(rule.get("fields_affected") or []),
        "condition": rule.get("condition"),
        "eligibility": list(rule.get("eligibility") or []),
        "decision_logic_rows": list(rule.get("decision_logic_rows") or []),
        "action": rule.get("action"),
    }
    deterministic_evidence = {
        "source_chunks": sorted({str(row.get("source_chunk_id") or "").strip() for row in matched_rows if str(row.get("source_chunk_id") or "").strip()}),
        "statement_ids": sorted({str(row.get("statement_id") or "").strip() for row in matched_rows if str(row.get("statement_id") or "").strip()}),
        "tables": sorted({str(row.get("table") or "").strip() for row in matched_rows if str(row.get("table") or "").strip()}),
        "operations": sorted({str(row.get("operation") or "").strip() for row in matched_rows if str(row.get("operation") or "").strip()}),
        "target_columns": sorted({col for row in matched_rows for col in _row_columns(row)}),
        "filters": sorted({row.get("filter_condition") or row.get("where_predicate") or "" for row in matched_rows if row.get("filter_condition") or row.get("where_predicate")}),
        "assigned_values": sorted({value for row in matched_rows for value in _row_assigned_values(row)}),
    }
    comparison = {
        "field_status": field_status,
        "condition_status": condition_status,
        "outcome_status": outcome_status,
        "has_deterministic_evidence": bool(matched_rows),
        "has_llm_claim": bool(claim_fields or claim_conditions or claim_outcomes),
        "candidate_count": len(comparable_rows),
    }
    if status == "MATCHED":
        return status, llm_claim, deterministic_evidence, matched_rows
    return status, llm_claim, deterministic_evidence, matched_rows


@dataclass
class ReconciliationRecord:
    reconciliation_id: str
    kind: str
    status: str
    object_id: str
    rule_id: str = ""
    chunk_id: str = ""
    statement_id: str = ""
    llm_claim: Dict[str, Any] = field(default_factory=dict)
    deterministic_evidence: Dict[str, Any] = field(default_factory=dict)
    comparison: Dict[str, Any] = field(default_factory=dict)
    note: str = ""
    confidence: str = "low"


@dataclass
class ContradictionFinding:
    contradiction_id: str
    type: str
    severity: str
    object_id: str
    rule_id: str = ""
    related_rule_ids: List[str] = field(default_factory=list)
    chunk_ids: List[str] = field(default_factory=list)
    statement_ids: List[str] = field(default_factory=list)
    source_value: str = ""
    llm_value: str = ""
    reconciliation_status: str = ""
    explanation: str = ""
    review_required: bool = True
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconciliationResult:
    records: List[ReconciliationRecord] = field(default_factory=list)
    status_counts: Dict[str, int] = field(default_factory=dict)
    review_required: bool = False
    unsupported_dialect: bool = False
    summary: Dict[str, Any] = field(default_factory=dict)
    contradictions: List[ContradictionFinding] = field(default_factory=list)
    coverage: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    duplicate_rule_groups: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "records": [asdict(record) for record in self.records],
            "status_counts": dict(self.status_counts),
            "review_required": self.review_required,
            "unsupported_dialect": self.unsupported_dialect,
            "summary": dict(self.summary),
            "contradictions": [asdict(finding) for finding in self.contradictions],
            "coverage": dict(self.coverage),
            "quality": dict(self.quality),
            "duplicate_rule_groups": [dict(group) for group in self.duplicate_rule_groups],
        }


def _collect_deterministic_rows(merged_extraction: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for row in merged_extraction.get("tables_read", []) or []:
        if isinstance(row, dict):
            cloned = dict(row)
            cloned["_section"] = "tables_read"
            rows.append(cloned)
    for row in merged_extraction.get("tables_written", []) or []:
        if isinstance(row, dict):
            cloned = dict(row)
            cloned["_section"] = "tables_written"
            rows.append(cloned)
    return rows


def _chunk_id_from_row(row: Dict[str, Any]) -> str:
    return str(row.get("source_chunk_id") or row.get("provenance", {}).get("chunk_id") or "").strip()


def _statement_id_from_row(row: Dict[str, Any]) -> str:
    return str(row.get("statement_id") or row.get("source_statement_id") or row.get("provenance", {}).get("statement_id") or "").strip()


def _confidence_for_status(status: str, current_confidence: str, matched: bool, unsupported_dialect: bool) -> str:
    if unsupported_dialect:
        return "low"
    if status in {"CONFLICT", "LLM_ONLY", "UNRESOLVED"}:
        return "low"
    if status == "MATCHED" and matched:
        return normalize_confidence(current_confidence, default="medium")
    return normalize_confidence(current_confidence, default="low")


def _create_contradiction(
    *,
    object_id: str,
    contradiction_type: str,
    severity: str,
    rule_id: str = "",
    related_rule_ids: Optional[List[str]] = None,
    chunk_ids: Optional[List[str]] = None,
    statement_ids: Optional[List[str]] = None,
    source_value: str = "",
    llm_value: str = "",
    reconciliation_status: str = "",
    explanation: str = "",
    evidence: Optional[Dict[str, Any]] = None,
    review_required: bool = True,
) -> ContradictionFinding:
    severity = str(severity or "LOW").upper()
    contradiction_type = str(contradiction_type or "").strip().lower()
    if severity not in CONTRADICTION_SEVERITIES:
        severity = "LOW"
    if contradiction_type not in CONTRADICTION_TYPES:
        contradiction_type = "rule_vs_rule_conflict"
    payload = [
        object_id,
        contradiction_type,
        severity,
        rule_id,
        "|".join(sorted({str(v).strip() for v in related_rule_ids or [] if str(v).strip()})),
        "|".join(sorted({str(v).strip() for v in chunk_ids or [] if str(v).strip()})),
        "|".join(sorted({str(v).strip() for v in statement_ids or [] if str(v).strip()})),
        source_value,
        llm_value,
        reconciliation_status,
        explanation,
    ]
    contradiction_id = stable_id("contra", *payload)
    return ContradictionFinding(
        contradiction_id=contradiction_id,
        type=contradiction_type,
        severity=severity,
        object_id=object_id,
        rule_id=rule_id,
        related_rule_ids=sorted({str(v).strip() for v in related_rule_ids or [] if str(v).strip()}),
        chunk_ids=sorted({str(v).strip() for v in chunk_ids or [] if str(v).strip()}),
        statement_ids=sorted({str(v).strip() for v in statement_ids or [] if str(v).strip()}),
        source_value=source_value,
        llm_value=llm_value,
        reconciliation_status=reconciliation_status,
        explanation=explanation,
        review_required=review_required,
        evidence=evidence or {},
    )


def _gather_contradictions(
    *,
    object_id: str,
    rules: Sequence[Dict[str, Any]],
    records: Sequence[ReconciliationRecord],
) -> tuple[List[ContradictionFinding], List[Dict[str, Any]]]:
    contradictions: List[ContradictionFinding] = []
    duplicate_groups: List[Dict[str, Any]] = []

    for record in records:
        if record.kind == "tables_read" or record.kind == "tables_written":
            if record.status != "CONFLICT":
                continue
            llm_claim = record.llm_claim or {}
            deterministic = record.deterministic_evidence or {}
            if _clean_text(llm_claim.get("table")) and _clean_text(deterministic.get("table")) and _normalize_value(llm_claim.get("table")) != _normalize_value(deterministic.get("table")):
                contradictions.append(
                    _create_contradiction(
                        object_id=object_id,
                        contradiction_type="table_conflict",
                        severity="MEDIUM",
                        chunk_ids=[record.chunk_id],
                        statement_ids=[record.statement_id],
                        source_value=str(deterministic.get("table") or ""),
                        llm_value=str(llm_claim.get("table") or ""),
                        reconciliation_status=record.status,
                        explanation="Synthesized table reference does not match deterministic table evidence.",
                        evidence={"record": asdict(record), "axis": "table"},
                    )
                )
            if _clean_text(llm_claim.get("operation")) and _clean_text(deterministic.get("operation")) and _normalize_value(llm_claim.get("operation")) != _normalize_value(deterministic.get("operation")):
                contradictions.append(
                    _create_contradiction(
                        object_id=object_id,
                        contradiction_type="operation_conflict",
                        severity="HIGH",
                        chunk_ids=[record.chunk_id],
                        statement_ids=[record.statement_id],
                        source_value=str(deterministic.get("operation") or ""),
                        llm_value=str(llm_claim.get("operation") or ""),
                        reconciliation_status=record.status,
                        explanation="Synthesized table operation conflicts with deterministic SQL/AST evidence.",
                        evidence={"record": asdict(record), "axis": "operation"},
                    )
                )
            llm_columns = { _normalize_value(v) for v in llm_claim.get("target_columns") or llm_claim.get("columns") or [] if _clean_text(v) }
            det_columns = { _normalize_value(v) for v in deterministic.get("target_columns") or deterministic.get("columns") or [] if _clean_text(v) }
            if llm_columns and det_columns and llm_columns != det_columns:
                contradictions.append(
                    _create_contradiction(
                        object_id=object_id,
                        contradiction_type="field_conflict",
                        severity="MEDIUM",
                        chunk_ids=[record.chunk_id],
                        statement_ids=[record.statement_id],
                        source_value=", ".join(sorted(det_columns)),
                        llm_value=", ".join(sorted(llm_columns)),
                        reconciliation_status=record.status,
                        explanation="Synthesized affected fields do not match deterministic SQL/AST evidence.",
                        evidence={"record": asdict(record), "axis": "fields"},
                    )
                )
            llm_filter = _parse_structured_comparison(llm_claim.get("filter_condition") or llm_claim.get("where_predicate") or llm_claim.get("trigger_condition"))
            det_filter = _parse_structured_comparison(deterministic.get("filter_condition") or deterministic.get("where_predicate") or deterministic.get("trigger_condition"))
            if llm_filter and det_filter and llm_filter != det_filter:
                contradictions.append(
                    _create_contradiction(
                        object_id=object_id,
                        contradiction_type="condition_conflict",
                        severity="HIGH",
                        chunk_ids=[record.chunk_id],
                        statement_ids=[record.statement_id],
                        source_value=str(deterministic.get("filter_condition") or deterministic.get("where_predicate") or ""),
                        llm_value=str(llm_claim.get("filter_condition") or llm_claim.get("where_predicate") or llm_claim.get("trigger_condition") or ""),
                        reconciliation_status=record.status,
                        explanation="Synthesized condition conflicts with deterministic predicate evidence.",
                        evidence={"record": asdict(record), "axis": "condition"},
                    )
                )
            llm_assignment_values = _normalize_set(_row_assigned_values(llm_claim))
            det_assignment_values = _normalize_set(_row_assigned_values(deterministic))
            if llm_assignment_values and det_assignment_values and llm_assignment_values != det_assignment_values:
                contradictions.append(
                    _create_contradiction(
                        object_id=object_id,
                        contradiction_type="outcome_conflict",
                        severity="HIGH",
                        chunk_ids=[record.chunk_id],
                        statement_ids=[record.statement_id],
                        source_value=", ".join(sorted(det_assignment_values)),
                        llm_value=", ".join(sorted(llm_assignment_values)),
                        reconciliation_status=record.status,
                        explanation="Synthesized assignment/outcome does not match deterministic SQL/AST evidence.",
                        evidence={"record": asdict(record), "axis": "outcome"},
                    )
                )
            continue

        if record.kind != "rule" or record.status != "CONFLICT":
            continue
        comparison = record.comparison or {}
        if comparison.get("field_status") == "CONFLICT":
            contradictions.append(
                _create_contradiction(
                    object_id=object_id,
                    contradiction_type="field_conflict",
                    severity="MEDIUM",
                    rule_id=record.rule_id,
                    chunk_ids=[record.chunk_id],
                    statement_ids=[record.statement_id],
                    source_value=", ".join((record.deterministic_evidence or {}).get("target_columns", []) or []),
                    llm_value=", ".join((record.llm_claim or {}).get("fields_affected", []) or []),
                    reconciliation_status=record.status,
                    explanation="Synthesized rule affects different fields than the deterministic evidence.",
                    evidence={"record": asdict(record), "axis": "fields"},
                )
            )
        if comparison.get("condition_status") == "CONFLICT":
            llm_conditions = _find_record_condition_values(record)
            contradictions.append(
                _create_contradiction(
                    object_id=object_id,
                    contradiction_type="condition_conflict",
                    severity="HIGH",
                    rule_id=record.rule_id,
                    chunk_ids=[record.chunk_id],
                    statement_ids=[record.statement_id],
                    source_value=", ".join((record.deterministic_evidence or {}).get("filters", []) or []),
                    llm_value=", ".join(llm_conditions),
                    reconciliation_status=record.status,
                    explanation="Synthesized condition conflicts with deterministic predicate evidence.",
                    evidence={"record": asdict(record), "axis": "condition"},
                )
            )
        if comparison.get("outcome_status") == "CONFLICT":
            llm_outcomes = _find_record_outcome_values(record)
            contradictions.append(
                _create_contradiction(
                    object_id=object_id,
                    contradiction_type="outcome_conflict",
                    severity="HIGH",
                    rule_id=record.rule_id,
                    chunk_ids=[record.chunk_id],
                    statement_ids=[record.statement_id],
                    source_value=", ".join((record.deterministic_evidence or {}).get("assigned_values", []) or []),
                    llm_value=", ".join(llm_outcomes),
                    reconciliation_status=record.status,
                    explanation="Synthesized outcome/assignment conflicts with deterministic evidence.",
                    evidence={"record": asdict(record), "axis": "outcome"},
                )
            )

    # Rule-vs-rule comparisons: same conditions with different outcomes, or
    # clearly incompatible overlapping conditions that we can parse
    # structurally. Identical duplicate rules are grouped instead of being
    # treated as contradictions.
    duplicate_index: Dict[Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]], List[Dict[str, Any]]] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        duplicate_index.setdefault(_rule_signature(rule), []).append(rule)

    for signature, grouped_rules in duplicate_index.items():
        if len(grouped_rules) < 2:
            continue
        chunk_union = sorted({chunk for rule in grouped_rules for chunk in (rule.get("source_chunks") or []) if str(chunk).strip()})
        if len(chunk_union) < 2:
            continue
        duplicate_groups.append(
            {
                "signature": {
                    "fields": list(signature[0]),
                    "conditions": list(signature[1]),
                    "outcomes": list(signature[2]),
                },
                "rule_ids": [str(rule.get("rule_id") or "") for rule in grouped_rules if str(rule.get("rule_id") or "").strip()],
                "chunk_ids": chunk_union,
                "support_count": len(grouped_rules),
            }
        )

    for left_index, left_rule in enumerate(rules):
        if not isinstance(left_rule, dict):
            continue
        left_fields = set(_rule_claim_fields(left_rule))
        left_conditions = _structured_rule_conditions(left_rule)
        left_outcomes = _structured_rule_outcomes(left_rule)
        if not left_conditions or not left_fields or not left_outcomes:
            continue
        left_chunks, left_statements = _rule_source_identity(left_rule)
        for right_rule in rules[left_index + 1 :]:
            if not isinstance(right_rule, dict):
                continue
            right_fields = set(_rule_claim_fields(right_rule))
            right_conditions = _structured_rule_conditions(right_rule)
            right_outcomes = _structured_rule_outcomes(right_rule)
            if not right_conditions or not right_fields or not right_outcomes:
                continue
            if not (left_fields & right_fields):
                continue

            # Duplicates: same structured condition and same outcome, just
            # supported by more than one chunk.
            if {
                (cond["lhs"], cond["op"], cond["rhs"])
                for cond in left_conditions
            } == {
                (cond["lhs"], cond["op"], cond["rhs"])
                for cond in right_conditions
            } and {
                (out["lhs"], out["rhs"])
                for out in left_outcomes
            } == {
                (out["lhs"], out["rhs"])
                for out in right_outcomes
            }:
                left_chunks_set = {str(v).strip() for v in left_rule.get("source_chunks") or [] if str(v).strip()}
                right_chunks_set = {str(v).strip() for v in right_rule.get("source_chunks") or [] if str(v).strip()}
                if left_chunks_set or right_chunks_set:
                    duplicate_groups.append(
                        {
                            "signature": {
                                "fields": sorted(left_fields & right_fields),
                                "conditions": [cond["raw"] for cond in left_conditions],
                                "outcomes": [out["raw"] for out in left_outcomes],
                            },
                            "rule_ids": sorted(
                                {
                                    str(left_rule.get("rule_id") or "").strip(),
                                    str(right_rule.get("rule_id") or "").strip(),
                                }
                                - {""}
                            ),
                            "chunk_ids": sorted(left_chunks_set | right_chunks_set),
                            "support_count": 2,
                        }
                    )
                continue

            left_condition_sig = {(cond["lhs"], cond["op"], cond["rhs"]) for cond in left_conditions}
            right_condition_sig = {(cond["lhs"], cond["op"], cond["rhs"]) for cond in right_conditions}
            same_lhs = {cond["lhs"] for cond in left_conditions} & {cond["lhs"] for cond in right_conditions}
            if not same_lhs:
                continue

            left_outcome_values = {(out["lhs"], out["rhs"]) for out in left_outcomes}
            right_outcome_values = {(out["lhs"], out["rhs"]) for out in right_outcomes}
            if left_outcome_values == right_outcome_values:
                continue

            contradictory = False
            explanation = ""
            for left_condition in left_conditions:
                for right_condition in right_conditions:
                    if left_condition["lhs"] != right_condition["lhs"]:
                        continue
                    if left_condition["op"] != right_condition["op"] or left_condition["rhs"] != right_condition["rhs"]:
                        contradictory = True
                        explanation = "Rules share the same field condition but apply different outcomes."
                        break
                if contradictory:
                    break
            if not contradictory and left_condition_sig and right_condition_sig:
                contradictory = bool(same_lhs) and bool(left_outcome_values ^ right_outcome_values)
                explanation = "Rules overlap on the same structured condition but assign different outcomes."

            if contradictory:
                related_rule_ids = sorted(
                    {
                        str(left_rule.get("rule_id") or "").strip(),
                        str(right_rule.get("rule_id") or "").strip(),
                    }
                    - {""}
                )
                chunk_ids = sorted(
                    {
                        *left_chunks,
                        *[str(v).strip() for v in right_rule.get("source_chunks") or [] if str(v).strip()],
                    }
                )
                contradictions.append(
                    _create_contradiction(
                        object_id=object_id,
                        contradiction_type="rule_vs_rule_conflict",
                        severity="HIGH",
                        related_rule_ids=related_rule_ids,
                        chunk_ids=chunk_ids,
                        statement_ids=sorted(
                            {
                                *left_statements,
                                *[
                                    str(v).strip()
                                    for v in right_rule.get("technical_references") or []
                                    if str(v).strip()
                                ],
                            }
                        ),
                        source_value=", ".join(sorted({out["raw"] for out in left_outcomes})),
                        llm_value=", ".join(sorted({out["raw"] for out in right_outcomes})),
                        reconciliation_status="CONFLICT",
                        explanation=explanation,
                        evidence={
                            "left_rule": {
                                "rule_id": left_rule.get("rule_id"),
                                "condition": [cond["raw"] for cond in left_conditions],
                                "outcome": [out["raw"] for out in left_outcomes],
                            },
                            "right_rule": {
                                "rule_id": right_rule.get("rule_id"),
                                "condition": [cond["raw"] for cond in right_conditions],
                                "outcome": [out["raw"] for out in right_outcomes],
                            },
                        },
                    )
                )

    return contradictions, duplicate_groups


def _build_coverage_metrics(
    *,
    merged_extraction: Dict[str, Any],
    rules: Sequence[Dict[str, Any]],
    records: Sequence[ReconciliationRecord],
    contradictions: Sequence[ContradictionFinding],
    duplicate_rule_groups: Sequence[Dict[str, Any]],
    unsupported_dialect: bool,
) -> Dict[str, Any]:
    statement_provenance = merged_extraction.get("statement_provenance", []) or []
    total_statements = len(statement_provenance)
    parsed_statements = sum(1 for row in statement_provenance if str((row or {}).get("parse_status") or "").lower() == "parsed")
    unsupported_statements = max(total_statements - parsed_statements, 0)
    deterministic_rows = _collect_deterministic_rows(merged_extraction)
    rule_list = list(rules)
    synthesized_rules = [record for record in records if record.kind == "rule"]
    rules_with_deterministic_support = sum(1 for record in synthesized_rules if bool(record.deterministic_evidence))
    llm_only_rules = sum(1 for record in synthesized_rules if record.status == "LLM_ONLY")
    deterministic_only_facts = sum(1 for record in records if record.status == "DETERMINISTIC_ONLY")
    conflicts = sum(1 for record in records if record.status == "CONFLICT")
    unresolved = sum(1 for record in records if record.status == "UNRESOLVED")
    review_required_items = sum(
        1
        for record in records
        if record.status in {"CONFLICT", "LLM_ONLY", "UNRESOLVED"}
        or (record.status == "MATCHED" and unsupported_dialect)
    ) + sum(1 for contradiction in contradictions if contradiction.review_required)

    metrics: Dict[str, Any] = {
        "total_statements": total_statements,
        "parsed_statements": parsed_statements,
        "unsupported_unparsed_statements": unsupported_statements,
        "deterministic_facts": len(deterministic_rows),
        "synthesized_rules": len(list(rules)),
        "rules_with_deterministic_support": rules_with_deterministic_support,
        "llm_only_rules": llm_only_rules,
        "deterministic_only_facts": deterministic_only_facts,
        "conflicts": conflicts,
        "contradictions": len(contradictions),
        "review_required_items": review_required_items,
        "duplicate_rule_groups": len(list(duplicate_rule_groups)),
    }
    if total_statements > 0:
        metrics["statement_parse_success_pct"] = round((parsed_statements / total_statements) * 100, 1)
    if rule_list:
        metrics["rule_grounding_pct"] = round((rules_with_deterministic_support / len(rule_list)) * 100, 1)
    return metrics


def _build_quality_assessment(
    *,
    coverage: Dict[str, Any],
    contradictions: Sequence[ContradictionFinding],
    unsupported_dialect: bool,
    records: Sequence[ReconciliationRecord],
) -> Dict[str, Any]:
    score = 100
    notes: List[str] = []
    high_contradictions = sum(1 for item in contradictions if item.severity == "HIGH")
    medium_contradictions = sum(1 for item in contradictions if item.severity == "MEDIUM")
    low_contradictions = sum(1 for item in contradictions if item.severity == "LOW")
    llm_only_rules = int(coverage.get("llm_only_rules", 0) or 0)
    deterministic_only_facts = int(coverage.get("deterministic_only_facts", 0) or 0)
    unresolved_items = int(coverage.get("review_required_items", 0) or 0)
    parse_success_pct = float(coverage.get("statement_parse_success_pct") or 0.0)
    grounding_pct = float(coverage.get("rule_grounding_pct") or 0.0)
    total_statements = int(coverage.get("total_statements", 0) or 0)
    synthesized_rules = int(coverage.get("synthesized_rules", 0) or 0)

    if unsupported_dialect:
        score -= 20
        notes.append("Dialect support is restricted.")
    if total_statements == 0:
        score -= 15
        notes.append("No statement provenance was available.")
    if synthesized_rules == 0:
        score -= 15
        notes.append("No synthesized rules were available.")
    score -= min(40, high_contradictions * 20)
    score -= min(20, medium_contradictions * 8)
    score -= min(10, low_contradictions * 3)
    score -= min(15, llm_only_rules * 7)
    score -= min(10, deterministic_only_facts * 2)
    score -= min(15, unresolved_items * 2)
    if parse_success_pct and parse_success_pct < 75:
        score -= 10
        notes.append("Statement parse success is below the preferred threshold.")
    if grounding_pct and grounding_pct < 75:
        score -= 10
        notes.append("Rule grounding coverage is below the preferred threshold.")
    if not any(record.status == "MATCHED" for record in records):
        score -= 10

    score = max(0, min(100, score))
    if high_contradictions or medium_contradictions or unresolved_items or llm_only_rules:
        overall_status = "REVIEW_REQUIRED"
    elif unsupported_dialect or parse_success_pct < 50 or grounding_pct < 50 or score < 60 or total_statements == 0 or synthesized_rules == 0:
        overall_status = "LOW_CONFIDENCE"
    else:
        overall_status = "PASS"
    if unsupported_dialect and overall_status == "PASS":
        overall_status = "LOW_CONFIDENCE"
    return {
        "status": overall_status,
        "score": score,
        "review_required": bool(high_contradictions or medium_contradictions or unresolved_items or llm_only_rules or unsupported_dialect),
        "factors": {
            "high_contradictions": high_contradictions,
            "medium_contradictions": medium_contradictions,
            "low_contradictions": low_contradictions,
            "llm_only_rules": llm_only_rules,
            "deterministic_only_facts": deterministic_only_facts,
            "parse_success_pct": coverage.get("statement_parse_success_pct"),
            "rule_grounding_pct": coverage.get("rule_grounding_pct"),
        },
        "note": "; ".join(notes),
    }


def _find_record_outcome_values(record: ReconciliationRecord) -> List[str]:
    llm_claim = record.llm_claim or {}
    return _rule_claim_outcomes(llm_claim)


def _find_record_condition_values(record: ReconciliationRecord) -> List[str]:
    llm_claim = record.llm_claim or {}
    return _rule_claim_conditions(llm_claim)


def reconcile_deterministic_evidence(
    *,
    ingestion,
    merged_extraction: Dict[str, Any],
    synthesis,
) -> ReconciliationResult:
    object_id = str(getattr(ingestion, "object_id", "") or "")
    dialect = normalize_dialect_name(getattr(ingestion, "dialect", ""))
    unsupported_dialect = dialect in {UNKNOWN, AMBIGUOUS, UNSUPPORTED}
    deterministic_rows = _collect_deterministic_rows(merged_extraction)
    llm_tables_read = [dict(row) for row in merged_extraction.get("llm_tables_read", []) or [] if isinstance(row, dict)]
    llm_tables_written = [dict(row) for row in merged_extraction.get("llm_tables_written", []) or [] if isinstance(row, dict)]

    records: List[ReconciliationRecord] = []
    status_counts: Dict[str, int] = {status: 0 for status in RECONCILIATION_STATUSES}
    matched_det_indexes: set[int] = set()
    matched_rule_det_indexes: set[int] = set()

    # Table-level reconciliation: preserve both the LLM claim and the deterministic row.
    for section, llm_rows in (("tables_read", llm_tables_read), ("tables_written", llm_tables_written)):
        det_rows = [row for row in deterministic_rows if row.get("_section") == section]
        for idx, llm_row in enumerate(llm_rows):
            matching_idx = None
            status = "LLM_ONLY"
            det_row = None
            for det_idx, candidate in enumerate(det_rows):
                if det_idx in matched_det_indexes:
                    continue
                if _table_rows_match(llm_row, candidate):
                    matching_idx = det_idx
                    det_row = candidate
                    status = "MATCHED"
                    break
            if det_row is None:
                for det_idx, candidate in enumerate(det_rows):
                    if det_idx in matched_det_indexes:
                        continue
                    if _same_source_identity(llm_row, candidate):
                        matching_idx = det_idx
                        det_row = candidate
                        status = "CONFLICT"
                        break
            if det_row is None:
                for det_idx, candidate in enumerate(det_rows):
                    if det_idx in matched_det_indexes:
                        continue
                    if _normalize_value(llm_row.get("table") or "") == _normalize_value(candidate.get("table") or ""):
                        matching_idx = det_idx
                        det_row = candidate
                        status = "CONFLICT"
                        break
            if det_row is not None and matching_idx is not None:
                matched_det_indexes.add(matching_idx)
            recon_id = stable_id(
                "recon",
                object_id,
                section,
                llm_row.get("source_chunk_id") or llm_row.get("table") or idx,
                llm_row.get("statement_id") or llm_row.get("source_statement_id") or "",
                status,
            )
            record = ReconciliationRecord(
                reconciliation_id=recon_id,
                kind=section,
                status=status,
                object_id=object_id,
                chunk_id=_chunk_id_from_row(llm_row),
                statement_id=_statement_id_from_row(llm_row),
                llm_claim=llm_row,
                deterministic_evidence=det_row or {},
                comparison={
                    "table_status": status,
                    "table": llm_row.get("table"),
                    "llm_columns": llm_row.get("columns") or llm_row.get("target_columns") or [],
                    "deterministic_columns": (det_row or {}).get("columns") or (det_row or {}).get("target_columns") or [],
                    "llm_filter": llm_row.get("filter_condition") or llm_row.get("where_predicate") or llm_row.get("trigger_condition"),
                    "deterministic_filter": (det_row or {}).get("filter_condition") or (det_row or {}).get("where_predicate") or (det_row or {}).get("trigger_condition"),
                },
                note="Structural fallback only; review required." if unsupported_dialect else "",
                confidence=_confidence_for_status(status, llm_row.get("confidence", "medium"), status == "MATCHED", unsupported_dialect),
            )
            records.append(record)
            status_counts[status] = status_counts.get(status, 0) + 1

    # Rule reconciliation against deterministic writes/conditions.
    rules = synthesis.data.get("business_rules", []) or []
    for idx, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            continue
        claim_fields = _rule_claim_fields(rule)
        claim_conditions = _rule_claim_conditions(rule)
        claim_outcomes = _rule_claim_outcomes(rule)
        source_chunks = {str(chunk).strip() for chunk in rule.get("source_chunks") or [] if str(chunk).strip()}
        candidate_rows = [
            row
            for row in deterministic_rows
            if (_chunk_id_from_row(row) and _chunk_id_from_row(row) in source_chunks)
            or any(_normalize_value(e) in {_normalize_value(row.get("filter_condition") or ""), _normalize_value(row.get("where_predicate") or ""), _normalize_value(row.get("statement_text") or "")} for e in rule.get("source_evidence") or [])
        ]
        if not candidate_rows and source_chunks:
            candidate_rows = [
                row for row in deterministic_rows if _chunk_id_from_row(row) in source_chunks
            ]

        status = "LLM_ONLY"
        comparison = {
            "field_status": "UNRESOLVED",
            "condition_status": "UNRESOLVED",
            "outcome_status": "UNRESOLVED",
        }
        deterministic_evidence: Dict[str, Any] = {}
        matched_rows = []
        if candidate_rows:
            matched_rows = candidate_rows
            field_matches = []
            condition_matches = []
            outcome_matches = []
            field_conflicts = []
            condition_conflicts = []
            outcome_conflicts = []
            for row in candidate_rows:
                row_fields = _normalize_set(_row_columns(row))
                row_filter = _row_filter(row)
                row_values = _normalize_set(_row_assigned_values(row))
                if claim_fields:
                    if row_fields and _normalize_set(claim_fields) == row_fields:
                        field_matches.append(row)
                    elif row_fields:
                        field_conflicts.append(row)
                if claim_conditions:
                    if row_filter and any(_normalize_value(c) == row_filter for c in claim_conditions):
                        condition_matches.append(row)
                    elif row_filter:
                        condition_conflicts.append(row)
                if claim_outcomes:
                    if row_values and any(_normalize_value(o) in row_values for o in claim_outcomes):
                        outcome_matches.append(row)
                    elif row_values:
                        outcome_conflicts.append(row)

            if field_conflicts or condition_conflicts or outcome_conflicts:
                status = "CONFLICT"
            elif field_matches or condition_matches or outcome_matches:
                status = "MATCHED"
            else:
                status = "UNRESOLVED"

            deterministic_evidence = {
                "source_chunks": sorted({_chunk_id_from_row(row) for row in matched_rows if _chunk_id_from_row(row)}),
                "statement_ids": sorted({_statement_id_from_row(row) for row in matched_rows if _statement_id_from_row(row)}),
                "tables": sorted({str(row.get("table") or "").strip() for row in matched_rows if str(row.get("table") or "").strip()}),
                "operations": sorted({str(row.get("operation") or "").strip() for row in matched_rows if str(row.get("operation") or "").strip()}),
                "target_columns": sorted({col for row in matched_rows for col in _row_columns(row)}),
                "filters": sorted({row.get("filter_condition") or row.get("where_predicate") or "" for row in matched_rows if row.get("filter_condition") or row.get("where_predicate")}),
                "assigned_values": sorted({value for row in matched_rows for value in _row_assigned_values(row)}),
            }
            comparison = {
                "field_status": "MATCHED" if field_matches and not field_conflicts else ("CONFLICT" if field_conflicts else "UNRESOLVED"),
                "condition_status": "MATCHED" if condition_matches and not condition_conflicts else ("CONFLICT" if condition_conflicts else "UNRESOLVED"),
                "outcome_status": "MATCHED" if outcome_matches and not outcome_conflicts else ("CONFLICT" if outcome_conflicts else "UNRESOLVED"),
            }
            if status == "UNRESOLVED" and claim_fields and claim_conditions:
                status = "UNRESOLVED"
            if status != "CONFLICT" and not (field_matches or condition_matches or outcome_matches):
                status = "UNRESOLVED"

        rule_recon_id = stable_id(
            "recon",
            object_id,
            "rule",
            rule.get("rule_id") or idx,
            status,
            "|".join(claim_fields),
            "|".join(claim_conditions),
            "|".join(claim_outcomes),
        )
        rule["reconciliation_id"] = rule_recon_id
        rule["reconciliation_status"] = status
        rule["reconciliation_notes"] = []
        rule["deterministic_evidence"] = deterministic_evidence
        rule["llm_claim"] = {
            "rule_name": rule.get("rule_name"),
            "output_field": rule.get("output_field"),
            "fields_affected": list(rule.get("fields_affected") or []),
            "condition": rule.get("condition"),
            "eligibility": list(rule.get("eligibility") or []),
            "decision_logic_rows": list(rule.get("decision_logic_rows") or []),
            "action": rule.get("action"),
        }
        if unsupported_dialect:
            rule["reconciliation_notes"].append(
                "Dialect-specific parsing fell back to a restricted structural path; review required."
            )

        if status == "CONFLICT":
            rule["confidence"] = "low"
            rule["reconciliation_notes"].append("Deterministic evidence conflicts with the synthesized claim.")
        elif status == "LLM_ONLY":
            rule["confidence"] = "low"
            rule["reconciliation_notes"].append("No deterministic evidence was found for this claim.")
        elif status == "UNRESOLVED":
            rule["confidence"] = "low"
            rule["reconciliation_notes"].append("Deterministic evidence exists, but comparison was not reliable enough for a match.")
        else:
            rule["confidence"] = derive_business_rule_confidence(
                validation_status=str(rule.get("validation_status") or "unverified"),
                source_evidence_count=len(rule.get("source_evidence") or []),
                matched_record_count=len(matched_rows),
                source_chunk_count=len(rule.get("source_chunks") or []),
                parser_failed=str(rule.get("validation_status") or "").lower() == "parser_failed",
                low_support=str(rule.get("confidence") or "").lower() == "low",
                ambiguous=False,
                unresolved_evidence=False,
                rule_type=str(rule.get("rule_type") or "inferred"),
                llm_only=False,
            )

        records.append(
            ReconciliationRecord(
                reconciliation_id=rule_recon_id,
                kind="rule",
                status=status,
                object_id=object_id,
                rule_id=str(rule.get("rule_id") or ""),
                chunk_id=";".join(sorted(source_chunks)),
                statement_id=";".join(deterministic_evidence.get("statement_ids", [])),
                llm_claim=rule["llm_claim"],
                deterministic_evidence=deterministic_evidence,
                comparison=comparison,
                note="; ".join(rule["reconciliation_notes"]),
                confidence=str(rule.get("confidence") or "low"),
            )
        )
        status_counts[status] = status_counts.get(status, 0) + 1

    # Coverage: deterministic facts that never made it into synthesized rules.
    rule_chunk_refs = {
        str(chunk).strip()
        for rule in rules
        for chunk in (rule.get("source_chunks") or [])
        if str(chunk).strip()
    }
    rule_statement_refs = {
        str(statement).strip()
        for rule in rules
        for statement in (rule.get("technical_references") or [])
        if str(statement).strip()
    }
    for row in deterministic_rows:
        if not row.get("operation") or str(row.get("operation")).upper() not in {"UPDATE", "INSERT", "DELETE", "MERGE", "TRUNCATE"}:
            continue
        chunk_id = _chunk_id_from_row(row)
        statement_id = _statement_id_from_row(row)
        meaningful = bool(_row_columns(row) or _row_assigned_values(row) or _row_filter(row))
        if not meaningful:
            continue
        covered = chunk_id in rule_chunk_refs or statement_id in rule_statement_refs
        if covered:
            continue
        recon_id = stable_id("recon", object_id, "coverage", chunk_id or statement_id or row.get("table") or row.get("operation"))
        records.append(
            ReconciliationRecord(
                reconciliation_id=recon_id,
                kind="coverage",
                status="DETERMINISTIC_ONLY",
                object_id=object_id,
                chunk_id=chunk_id,
                statement_id=statement_id,
                llm_claim={},
                deterministic_evidence={
                    "table": row.get("table"),
                    "operation": row.get("operation"),
                    "target_columns": row.get("target_columns") or row.get("columns") or [],
                    "filter_condition": row.get("filter_condition") or row.get("where_predicate"),
                    "assigned_values": row.get("assigned_values") or [],
                },
                comparison={"coverage_status": "MISSING_FROM_SYNTHESIS"},
                note="Deterministic evidence is present in the source but no synthesized rule referenced it.",
                confidence="low" if unsupported_dialect else "medium",
            )
        )
        status_counts["DETERMINISTIC_ONLY"] = status_counts.get("DETERMINISTIC_ONLY", 0) + 1

    contradictions, duplicate_rule_groups = _gather_contradictions(
        object_id=object_id,
        rules=rules,
        records=records,
    )
    coverage = _build_coverage_metrics(
        merged_extraction=merged_extraction,
        rules=rules,
        records=records,
        contradictions=contradictions,
        duplicate_rule_groups=duplicate_rule_groups,
        unsupported_dialect=unsupported_dialect,
    )
    quality = _build_quality_assessment(
        coverage=coverage,
        contradictions=contradictions,
        unsupported_dialect=unsupported_dialect,
        records=records,
    )

    summary = {
        "matched": status_counts.get("MATCHED", 0),
        "deterministic_only": status_counts.get("DETERMINISTIC_ONLY", 0),
        "llm_only": status_counts.get("LLM_ONLY", 0),
        "conflicts": status_counts.get("CONFLICT", 0),
        "unresolved": status_counts.get("UNRESOLVED", 0),
        "contradictions": len(contradictions),
        "review_required": bool(
            status_counts.get("CONFLICT")
            or status_counts.get("LLM_ONLY")
            or status_counts.get("UNRESOLVED")
            or unsupported_dialect
            or any(item.review_required for item in contradictions)
        ),
        "unsupported_dialect": unsupported_dialect,
        "note": (
            "Dialect-specific reconciliation used a restricted structural fallback path and should be manually reviewed."
            if unsupported_dialect
            else ""
        ),
    }

    return ReconciliationResult(
        records=records,
        status_counts=status_counts,
        review_required=summary["review_required"] or bool(quality.get("review_required")),
        unsupported_dialect=unsupported_dialect,
        summary=summary,
        contradictions=contradictions,
        coverage=coverage,
        quality=quality,
        duplicate_rule_groups=duplicate_rule_groups,
    )
