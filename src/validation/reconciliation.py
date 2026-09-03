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

CONTRADICTION_CLASSIFICATIONS = {
    "GENUINE_BUSINESS_CONTRADICTION",
    "TECHNICAL_PROVENANCE_NOISE",
    "TECHNICAL_VS_BUSINESS_OVERLAP",
    "VALID_ORDERED_BRANCH",
    "INSUFFICIENT_EVIDENCE",
}

BUSINESS_REVIEW_CLASSIFICATIONS = {
    "GENUINE_BUSINESS_CONTRADICTION",
    "INSUFFICIENT_EVIDENCE",
}

EXPECTED_FINDING_CLASSIFICATIONS = {
    "TECHNICAL_PROVENANCE_NOISE",
    "TECHNICAL_VS_BUSINESS_OVERLAP",
    "VALID_ORDERED_BRANCH",
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


def _normalize_sql_fragment(value: Any) -> str:
    cleaned = _clean_text(value).rstrip(";,")
    if not cleaned:
        return ""
    cleaned = _strip_outer_parentheses(cleaned)
    while cleaned.endswith(")") and cleaned.count("(") < cleaned.count(")"):
        cleaned = cleaned[:-1].rstrip()
        cleaned = _strip_outer_parentheses(cleaned)
    return _clean_text(cleaned)


def _normalize_column_reference(value: Any) -> str:
    cleaned = _normalize_sql_fragment(value)
    if "." not in cleaned:
        return _normalize_value(cleaned)
    left, right = cleaned.rsplit(".", 1)
    alias = _clean_text(left).strip("[]")
    column = _clean_text(right).strip("[]")
    if not alias or not column:
        return _normalize_value(cleaned)
    if len(alias) <= 4 and (alias.islower() or len(alias) <= 2):
        return _normalize_value(column)
    return _normalize_value(cleaned)


def _expressions_semantically_equal(left: Any, right: Any) -> bool:
    return _normalize_sql_fragment(left).lower() == _normalize_sql_fragment(right).lower()


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
    return _normalize_sql_fragment(
        row.get("filter_condition")
        or row.get("where_predicate")
        or row.get("trigger_condition")
        or ""
    ).lower()


def _row_assigned_values(row: Dict[str, Any]) -> List[str]:
    values = []
    for item in row.get("assigned_values") or []:
        if not isinstance(item, dict):
            continue
        expression = _normalize_sql_fragment(_strip_quotes(item.get("expression")))
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
    cleaned = _normalize_sql_fragment(str(text or ""))
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
    cleaned = _normalize_sql_fragment(str(text or ""))
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
    if left_statement and right_statement:
        return left_statement == right_statement
    if left_statement or right_statement:
        return False
    return bool(left_chunk and right_chunk and left_chunk == right_chunk)


def _rule_source_identity(rule: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    raw_chunks = rule.get("source_chunk_ids") or []
    if not raw_chunks:
        raw_chunks = [
            str(chunk).split(":", 1)[0].strip()
            for chunk in rule.get("source_chunks") or []
            if str(chunk).strip()
        ]
    chunks = [str(chunk).strip() for chunk in raw_chunks if str(chunk).strip()]

    raw_statements = rule.get("source_statement_ids") or []
    if not raw_statements:
        raw_statements = [
            str(ref).strip()
            for ref in rule.get("source_statements") or []
            if str(ref).strip()
        ]
    statements = [str(ref).strip() for ref in raw_statements if str(ref).strip()]
    return chunks, statements


def _rule_evidence_spans(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [dict(span) for span in rule.get("evidence_spans") or [] if isinstance(span, dict)]


def _span_is_executable(span: Dict[str, Any]) -> bool:
    return str(span.get("statement_parse_status") or "").strip().lower() == "parsed"


def _row_matches_evidence_span(row: Dict[str, Any], span: Dict[str, Any]) -> bool:
    row_chunk = _chunk_id_from_row(row)
    row_statement = _statement_id_from_row(row)
    span_chunk = str(span.get("chunk_id") or "").strip()
    span_statement = str(span.get("statement_id") or "").strip()
    if span_statement and row_statement and span_statement == row_statement:
        return True
    if span_statement and row_statement and span_statement != row_statement:
        return False
    if span_chunk and row_chunk and span_chunk == row_chunk:
        return True

    span_file = str(span.get("source_file") or "").strip()
    row_file = str(row.get("source_file") or row.get("provenance", {}).get("source_file") or "").strip()
    if span_file and row_file and span_file == row_file:
        span_start = int(span.get("char_start") or -1)
        span_end = int(span.get("char_end") or -1)
        row_start = int(row.get("source_char_start") or row.get("provenance", {}).get("source_char_start") or -1)
        row_end = int(row.get("source_char_end") or row.get("provenance", {}).get("source_char_end") or -1)
        if span_start >= 0 and span_end >= 0 and row_start >= 0 and row_end >= 0:
            if not (span_end < row_start or row_end < span_start):
                return True

        span_line_start = int(span.get("line_start") or -1)
        span_line_end = int(span.get("line_end") or -1)
        row_line_start = int(row.get("source_line_start") or row.get("provenance", {}).get("source_line_start") or -1)
        row_line_end = int(row.get("source_line_end") or row.get("provenance", {}).get("source_line_end") or -1)
        if span_line_start >= 0 and span_line_end >= 0 and row_line_start >= 0 and row_line_end >= 0:
            if not (span_line_end < row_line_start or row_line_end < span_line_start):
                return True

    return False


def _condition_space(condition: Dict[str, str]) -> Optional[Dict[str, Any]]:
    lhs = _normalize_value(condition.get("lhs"))
    op = str(condition.get("op") or "").upper().replace(" ", "")
    rhs_raw = _clean_text(condition.get("rhs"))
    if not lhs or not op or not rhs_raw:
        return None
    if op == "IN":
        values = [_normalize_value(item) for item in re.split(r",\s*", _strip_outer_parentheses(rhs_raw).strip("()")) if _normalize_value(item)]
        if not values:
            return None
        return {"lhs": lhs, "kind": "set", "values": values, "raw": condition.get("raw", "")}
    if op == "NOTIN":
        values = [_normalize_value(item) for item in re.split(r",\s*", _strip_outer_parentheses(rhs_raw).strip("()")) if _normalize_value(item)]
        if not values:
            return None
        return {"lhs": lhs, "kind": "negated_set", "values": values, "raw": condition.get("raw", "")}
    if op == "=":
        return {"lhs": lhs, "kind": "point", "lower": rhs_raw, "upper": rhs_raw, "lower_inclusive": True, "upper_inclusive": True, "raw": condition.get("raw", "")}
    if op in {">", ">=", "<", "<="}:
        numeric_match = re.match(r"^[-+]?\d+(?:\.\d+)?$", rhs_raw)
        if numeric_match:
            value = float(rhs_raw) if "." in rhs_raw else int(rhs_raw)
            if op == ">":
                return {"lhs": lhs, "kind": "range", "lower": value, "lower_inclusive": False, "raw": condition.get("raw", "")}
            if op == ">=":
                return {"lhs": lhs, "kind": "range", "lower": value, "lower_inclusive": True, "raw": condition.get("raw", "")}
            if op == "<":
                return {"lhs": lhs, "kind": "range", "upper": value, "upper_inclusive": False, "raw": condition.get("raw", "")}
            if op == "<=":
                return {"lhs": lhs, "kind": "range", "upper": value, "upper_inclusive": True, "raw": condition.get("raw", "")}
    between_match = re.match(
        r"^(?P<lhs>[A-Z0-9_.\[\]#$]+)\s+BETWEEN\s+(?P<lower>[-+]?\d+(?:\.\d+)?)\s+AND\s+(?P<upper>[-+]?\d+(?:\.\d+)?)$",
        _clean_text(condition.get("raw") or ""),
        re.IGNORECASE,
    )
    if between_match:
        lhs_text = _normalize_value(between_match.group("lhs"))
        lower = float(between_match.group("lower")) if "." in between_match.group("lower") else int(between_match.group("lower"))
        upper = float(between_match.group("upper")) if "." in between_match.group("upper") else int(between_match.group("upper"))
        if lhs_text:
            return {
                "lhs": lhs_text,
                "kind": "range",
                "lower": lower,
                "upper": upper,
                "lower_inclusive": True,
                "upper_inclusive": True,
                "raw": condition.get("raw", ""),
            }
    if _normalize_value(condition.get("raw")) in {"else", "otherwise"}:
        return {"lhs": lhs, "kind": "catch_all", "raw": condition.get("raw", "")}
    return None


def _spaces_overlap(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    if not left or not right:
        return False
    if left.get("lhs") != right.get("lhs"):
        return False
    if left.get("kind") == "catch_all" or right.get("kind") == "catch_all":
        return left.get("kind") == "catch_all" and right.get("kind") == "catch_all"
    if left.get("kind") == "point" and right.get("kind") == "point":
        return _normalize_value(left.get("lower")) == _normalize_value(right.get("lower"))
    if left.get("kind") == "set" and right.get("kind") == "set":
        return bool(set(left.get("values") or []) & set(right.get("values") or []))
    if left.get("kind") == "set" and right.get("kind") == "point":
        return _normalize_value(right.get("lower")) in set(left.get("values") or [])
    if right.get("kind") == "set" and left.get("kind") == "point":
        return _normalize_value(left.get("lower")) in set(right.get("values") or [])

    left_lower = left.get("lower")
    left_upper = left.get("upper")
    right_lower = right.get("lower")
    right_upper = right.get("upper")

    def _lower_bound(space: Dict[str, Any]) -> Tuple[Optional[float], bool]:
        return space.get("lower"), bool(space.get("lower_inclusive", True))

    def _upper_bound(space: Dict[str, Any]) -> Tuple[Optional[float], bool]:
        return space.get("upper"), bool(space.get("upper_inclusive", True))

    left_lb, left_lb_inclusive = _lower_bound(left)
    left_ub, left_ub_inclusive = _upper_bound(left)
    right_lb, right_lb_inclusive = _lower_bound(right)
    right_ub, right_ub_inclusive = _upper_bound(right)

    if left_lb is not None and right_ub is not None:
        if left_lb > right_ub:
            return False
        if left_lb == right_ub and (not left_lb_inclusive or not right_ub_inclusive):
            return False
    if right_lb is not None and left_ub is not None:
        if right_lb > left_ub:
            return False
        if right_lb == left_ub and (not right_lb_inclusive or not left_ub_inclusive):
            return False
    if left_lb is not None and left_ub is not None and right_lb is not None and right_ub is not None:
        return True
    if left_lb is not None and right_lb is not None:
        return True
    if left_ub is not None and right_ub is not None:
        return True
    return False


def _rule_has_executable_span(rule: Dict[str, Any]) -> bool:
    for span in _rule_evidence_spans(rule):
        if _span_is_executable(span):
            return True
    return False


def _rule_candidate_rows(rule: Dict[str, Any], deterministic_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence_spans = _rule_evidence_spans(rule)
    executable_spans = [span for span in evidence_spans if _span_is_executable(span)]
    source_chunk_ids, source_statement_ids = _rule_source_identity(rule)
    source_chunk_ids = {str(chunk).strip() for chunk in source_chunk_ids if str(chunk).strip()}
    source_statement_ids = {str(statement).strip() for statement in source_statement_ids if str(statement).strip()}

    candidate_rows: List[Dict[str, Any]] = []

    if executable_spans:
        for row in deterministic_rows:
            if any(_row_matches_evidence_span(row, span) for span in executable_spans):
                candidate_rows.append(row)
        if candidate_rows:
            return candidate_rows
        if source_statement_ids:
            candidate_rows = [
                row
                for row in deterministic_rows
                if _statement_id_from_row(row) in source_statement_ids
            ]
            if candidate_rows:
                return candidate_rows
        return []

    if evidence_spans and not executable_spans:
        return []

    if source_statement_ids:
        for row in deterministic_rows:
            if _statement_id_from_row(row) in source_statement_ids:
                candidate_rows.append(row)
        if candidate_rows:
            return candidate_rows
        return []

    if source_chunk_ids:
        for row in deterministic_rows:
            if _chunk_id_from_row(row) in source_chunk_ids:
                candidate_rows.append(row)
        if candidate_rows:
            return candidate_rows

    source_evidence = [
        _normalize_value(e) for e in rule.get("source_evidence") or [] if _clean_text(e)
    ]
    if source_evidence:
        for row in deterministic_rows:
            row_text_candidates = {
                _normalize_value(row.get("filter_condition") or ""),
                _normalize_value(row.get("where_predicate") or ""),
                _normalize_value(row.get("statement_text") or ""),
            }
            # Evidence is often a verbatim branch/calculation fragment inside
            # a larger statement. Containment is still source-grounded and
            # avoids classifying a genuinely linked rule as LLM_ONLY merely
            # because the model cited a sub-span rather than the full row.
            if any(
                fragment in candidate or candidate in fragment
                for fragment in source_evidence
                for candidate in row_text_candidates
                if fragment and candidate
            ):
                candidate_rows.append(row)
        if candidate_rows:
            return candidate_rows

    return candidate_rows


def _condition_overlap_key(condition: Dict[str, str]) -> Optional[Dict[str, Any]]:
    space = _condition_space(condition)
    if not space:
        return None
    return space


def _rule_condition_spaces(rule: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    spaces: Dict[str, List[Dict[str, Any]]] = {}
    for condition in _structured_rule_conditions(rule):
        space = _condition_space(condition)
        if not space:
            continue
        lhs = str(space.get("lhs") or "").strip()
        if not lhs:
            continue
        spaces.setdefault(lhs, []).append(space)
    return spaces


def _rules_have_structural_overlap(left_rule: Dict[str, Any], right_rule: Dict[str, Any]) -> bool:
    left_spaces = _rule_condition_spaces(left_rule)
    right_spaces = _rule_condition_spaces(right_rule)
    shared_lhs = set(left_spaces) & set(right_spaces)
    if not shared_lhs:
        return False
    for lhs in shared_lhs:
        left_values = left_spaces.get(lhs, [])
        right_values = right_spaces.get(lhs, [])
        if not left_values or not right_values:
            return False
        if not any(_spaces_overlap(left_value, right_value) for left_value in left_values for right_value in right_values):
            return False
    return True


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


def _row_relevant_to_rule(
    row: Dict[str, Any],
    claim_fields: Sequence[str],
    claim_conditions: Sequence[str],
    claim_outcomes: Sequence[str],
) -> bool:
    row_fields = {_normalize_column_reference(value) for value in _row_columns(row) if _clean_text(value)}
    claim_field_set = {_normalize_column_reference(value) for value in claim_fields if _clean_text(value)}
    if row_fields and claim_field_set and row_fields & claim_field_set:
        return True

    row_filter = _row_filter(row)
    if row_filter and any(_expressions_semantically_equal(row_filter, condition) for condition in claim_conditions if _clean_text(condition)):
        return True

    row_values = {_normalize_sql_fragment(value).lower() for value in _row_assigned_values(row) if _clean_text(value)}
    claim_outcome_set = set()
    for value in claim_outcomes or []:
        parsed = _parse_structured_assignment(value)
        if parsed and _clean_text(parsed.get("rhs")):
            claim_outcome_set.add(_normalize_sql_fragment(parsed.get("rhs")).lower())
        elif _clean_text(value):
            claim_outcome_set.add(_normalize_sql_fragment(value).lower())
    if row_values and claim_outcome_set and row_values & claim_outcome_set:
        return True

    return False


def _normalize_claim_axis_values(values: Sequence[Any], *, column_references: bool = False) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        if not _clean_text(value):
            continue
        normalized.add(_normalize_column_reference(value) if column_references else _normalize_sql_fragment(value).lower())
    return normalized


def _rule_signature(rule: Dict[str, Any]) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]:
    return (
        tuple(sorted(_normalize_set(_rule_claim_fields(rule)))),
        tuple(sorted({_clean_text(item.get("raw") or "") for item in _structured_rule_conditions(rule)})),
        tuple(sorted({_clean_text(item.get("raw") or "") for item in _structured_rule_outcomes(rule)})),
    )


def _rule_text_blob(rule: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "rule_name",
        "condition",
        "action",
        "business_meaning",
        "output_field",
        "validation_status",
        "rule_type",
    ):
        value = _clean_text(rule.get(key))
        if value:
            parts.append(value)
    for key in ("fields_affected", "eligibility", "decision_logic", "tie_priority_handling", "default", "when_not_eligible"):
        parts.extend(_normalize_list(rule.get(key) or []))
    for key in ("source_evidence", "technical_references", "source_chunks", "source_chunk_ids", "source_statement_ids"):
        parts.extend(_normalize_list(rule.get(key) or []))
    for row in rule.get("decision_logic_rows") or []:
        if not isinstance(row, dict):
            continue
        parts.extend(
            _normalize_list(
                [
                    row.get("field"),
                    row.get("condition"),
                    row.get("when"),
                    row.get("if"),
                    row.get("outcome"),
                    row.get("then"),
                    row.get("result"),
                ]
            )
        )
    return _normalize_value(" ".join(parts))


def _rule_has_ordered_branch_metadata(rule: Dict[str, Any]) -> bool:
    decision_rows = rule.get("decision_logic_rows") or []
    if isinstance(decision_rows, list) and len([row for row in decision_rows if isinstance(row, dict)]) >= 2:
        return True
    for key in ("tie_priority_handling", "default", "when_not_eligible"):
        if _normalize_list(rule.get(key) or []):
            return True
    text = _rule_text_blob(rule)
    if not text:
        return False
    if any(token in text for token in ("ordered branch", "decision chain", "decision ladder", "priority handling")):
        return True
    return False


def _rule_has_technical_preprocessing_metadata(rule: Dict[str, Any], deterministic_evidence: Optional[Dict[str, Any]] = None) -> bool:
    text = _rule_text_blob(rule)
    deterministic_text = _normalize_value(" ".join(
        _normalize_list((deterministic_evidence or {}).get("assigned_values") or [])
        + _normalize_list((deterministic_evidence or {}).get("filters") or [])
    ))
    if not text and not deterministic_text:
        return False
    if any(token in text for token in ("clear prior", "reset", "reprocessing", "preprocessing", "cleanup", "before reprocess")):
        return True
    if any(token in deterministic_text for token in ("null", "0")) and any(
        token in text for token in ("clear", "reset", "cleanup", "reprocess", "preprocess")
    ):
        return True
    return False


def _rule_has_insufficient_evidence(rule: Dict[str, Any], record: Optional[Dict[str, Any]] = None) -> bool:
    validation_status = _clean_text(rule.get("validation_status") or (record or {}).get("comparison", {}).get("coverage_status"))
    if validation_status.lower() in {"insufficient_evidence", "parser_failed", "ambiguous"}:
        return True
    return False


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
    if _row_operation(det_row) == "read":
        llm_filter = _row_filter(llm_row)
        det_filter = _row_filter(det_row)
        if llm_filter and det_filter and not _expressions_semantically_equal(llm_filter, det_filter):
            return False
        return True
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
    classification: str = "INSUFFICIENT_EVIDENCE"
    classification_reason: str = ""
    business_relevant: bool = True
    counted_for_review: bool = True
    review_item_id: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconciliationResult:
    records: List[ReconciliationRecord] = field(default_factory=list)
    status_counts: Dict[str, int] = field(default_factory=dict)
    review_required: bool = False
    unsupported_dialect: bool = False
    summary: Dict[str, Any] = field(default_factory=dict)
    contradictions: List[ContradictionFinding] = field(default_factory=list)
    classification_summary: Dict[str, Any] = field(default_factory=dict)
    review_summary: Dict[str, Any] = field(default_factory=dict)
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
            "classification_summary": dict(self.classification_summary),
            "review_summary": dict(self.review_summary),
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


def _classify_contradiction_finding(
    *,
    contradiction_type: str,
    record: Optional[ReconciliationRecord] = None,
    original_rule: Optional[Dict[str, Any]] = None,
    paired_rule: Optional[Dict[str, Any]] = None,
    contradiction: Optional[ContradictionFinding] = None,
) -> tuple[str, str, bool, bool]:
    record_dict = asdict(record) if isinstance(record, ReconciliationRecord) else {}
    source_rule = original_rule or {}
    paired_rule = paired_rule or {}
    finding_type = str(contradiction_type or getattr(contradiction, "type", "") or "").strip().lower()

    if record and record.kind in {"tables_read", "tables_written"}:
        return (
            "TECHNICAL_PROVENANCE_NOISE",
            "Deterministic table-operation reconciliation is a technical provenance finding rather than a business-rule contradiction.",
            False,
            False,
        )

    if source_rule and _rule_has_ordered_branch_metadata(source_rule):
        return (
            "VALID_ORDERED_BRANCH",
            "The rule carries explicit ordered-branch / decision-chain metadata, so the difference reflects branch ordering rather than incompatible business logic.",
            False,
            False,
        )

    if source_rule and _rule_has_technical_preprocessing_metadata(source_rule, record_dict.get("deterministic_evidence") if record_dict else None):
        return (
            "TECHNICAL_VS_BUSINESS_OVERLAP",
            "The rule explicitly describes preprocessing/reset/cleanup behavior that overlaps with business logic.",
            False,
            False,
        )

    if source_rule and _rule_has_insufficient_evidence(source_rule, record_dict):
        return (
            "INSUFFICIENT_EVIDENCE",
            "The available provenance is not strong enough to distinguish this finding from a genuine review item.",
            True,
            True,
        )

    if paired_rule and _rule_has_ordered_branch_metadata(paired_rule):
        return (
            "VALID_ORDERED_BRANCH",
            "The paired rule carries explicit ordered-branch / decision-chain metadata, so the difference reflects branch ordering rather than incompatible business logic.",
            False,
            False,
        )

    if paired_rule and _rule_has_technical_preprocessing_metadata(paired_rule, record_dict.get("deterministic_evidence") if record_dict else None):
        return (
            "TECHNICAL_VS_BUSINESS_OVERLAP",
            "The paired rule explicitly describes preprocessing/reset/cleanup behavior that overlaps with business logic.",
            False,
            False,
        )

    if paired_rule and _rule_has_insufficient_evidence(paired_rule, record_dict):
        return (
            "INSUFFICIENT_EVIDENCE",
            "The available provenance is not strong enough to distinguish this finding from a genuine review item.",
            True,
            True,
        )

    if finding_type in {"rule_vs_rule_conflict", "condition_conflict", "outcome_conflict", "field_conflict", "table_conflict", "operation_conflict"}:
        return (
            "GENUINE_BUSINESS_CONTRADICTION",
            "The evidence shows incompatible executable SQL/business logic with no explicit ordered-branch or technical-preprocessing explanation.",
            True,
            True,
        )

    return (
        "INSUFFICIENT_EVIDENCE",
        "The contradiction cannot be confidently classified from the available evidence.",
        True,
        True,
    )


def _contradiction_review_item_id(contradiction: ContradictionFinding) -> str:
    evidence_record = contradiction.evidence.get("record") if isinstance(contradiction.evidence, dict) else {}
    if isinstance(evidence_record, dict):
        reconciliation_id = str(evidence_record.get("reconciliation_id") or "").strip()
        if reconciliation_id:
            return reconciliation_id
    if contradiction.rule_id:
        return stable_id(
            "review",
            contradiction.object_id,
            contradiction.rule_id,
            contradiction.type,
            contradiction.reconciliation_status,
        )
    if contradiction.related_rule_ids:
        return stable_id(
            "review",
            contradiction.object_id,
            contradiction.type,
            "|".join(sorted(contradiction.related_rule_ids)),
            contradiction.reconciliation_status,
        )
    return stable_id(
        "review",
        contradiction.object_id,
        contradiction.type,
        contradiction.reconciliation_status,
        "|".join(sorted(contradiction.chunk_ids)),
        "|".join(sorted(contradiction.statement_ids)),
        contradiction.source_value,
        contradiction.llm_value,
    )


def _record_review_item_id(record: ReconciliationRecord) -> str:
    return str(record.reconciliation_id or stable_id(
        "review",
        record.object_id,
        record.kind,
        record.rule_id or record.chunk_id or record.statement_id,
        record.status,
    ))


def _classification_summary_from_contradictions(contradictions: Sequence[ContradictionFinding]) -> Dict[str, Any]:
    counts = {classification: 0 for classification in CONTRADICTION_CLASSIFICATIONS}
    for contradiction in contradictions:
        classification = str(contradiction.classification or "").strip().upper()
        if classification not in counts:
            classification = "INSUFFICIENT_EVIDENCE"
        counts[classification] += 1
    return {
        "total_contradictions": len(list(contradictions)),
        "genuine_business_contradictions": counts["GENUINE_BUSINESS_CONTRADICTION"],
        "technical_provenance_noise": counts["TECHNICAL_PROVENANCE_NOISE"],
        "technical_vs_business_overlap": counts["TECHNICAL_VS_BUSINESS_OVERLAP"],
        "valid_ordered_branches": counts["VALID_ORDERED_BRANCH"],
        "insufficient_evidence": counts["INSUFFICIENT_EVIDENCE"],
        "expected_non_business_findings": counts["TECHNICAL_PROVENANCE_NOISE"] + counts["TECHNICAL_VS_BUSINESS_OVERLAP"] + counts["VALID_ORDERED_BRANCH"],
        "counts": counts,
    }


def _build_review_summary(
    *,
    records: Sequence[ReconciliationRecord],
    contradictions: Sequence[ContradictionFinding],
    unsupported_dialect: bool,
) -> Dict[str, Any]:
    review_items: Dict[str, Dict[str, Any]] = {}

    def _ensure_item(item_id: str, *, source: str, kind: str = "", status: str = "") -> Dict[str, Any]:
        item = review_items.setdefault(
            item_id,
            {
                "review_item_id": item_id,
                "sources": [],
                "kind": kind,
                "status": status,
                "record_ids": [],
                "contradiction_ids": [],
                "classifications": [],
                "business_relevant": False,
                "counted_for_review": False,
            },
        )
        if source not in item["sources"]:
            item["sources"].append(source)
        if kind and not item.get("kind"):
            item["kind"] = kind
        if status and not item.get("status"):
            item["status"] = status
        return item

    for record in records:
        if record.status not in {"CONFLICT", "LLM_ONLY", "UNRESOLVED"} and not (record.status == "MATCHED" and unsupported_dialect):
            continue
        item_id = _record_review_item_id(record)
        item = _ensure_item(item_id, source="record", kind=record.kind, status=record.status)
        item["record_ids"].append(record.reconciliation_id)
        item["counted_for_review"] = True
        item["business_relevant"] = record.status in {"LLM_ONLY", "UNRESOLVED"}
        if unsupported_dialect and record.status == "MATCHED":
            item["business_relevant"] = True

    for contradiction in contradictions:
        item_id = contradiction.review_item_id or _contradiction_review_item_id(contradiction)
        item = _ensure_item(
            item_id,
            source="contradiction",
            kind=contradiction.type,
            status=contradiction.reconciliation_status,
        )
        item["contradiction_ids"].append(contradiction.contradiction_id)
        item["classifications"].append(contradiction.classification)
        if contradiction.business_relevant:
            item["business_relevant"] = True
        if contradiction.counted_for_review:
            item["counted_for_review"] = True

    for item in review_items.values():
        item["record_ids"] = sorted({str(v).strip() for v in item["record_ids"] if str(v).strip()})
        item["contradiction_ids"] = sorted({str(v).strip() for v in item["contradiction_ids"] if str(v).strip()})
        item["classifications"] = sorted({str(v).strip().upper() for v in item["classifications"] if str(v).strip()})

    business_review_items = [item for item in review_items.values() if item.get("business_relevant")]
    expected_items = [item for item in review_items.values() if not item.get("business_relevant") and item.get("counted_for_review")]
    return {
        "review_item_count": len(review_items),
        "business_review_required_items": len(business_review_items),
        "expected_review_items": len(expected_items),
        "items": sorted(review_items.values(), key=lambda item: item["review_item_id"]),
    }

def _gather_contradictions(
    *,
    object_id: str,
    rules: Sequence[Dict[str, Any]],
    records: Sequence[ReconciliationRecord],
) -> tuple[List[ContradictionFinding], List[Dict[str, Any]]]:
    contradictions: List[ContradictionFinding] = []
    duplicate_groups: List[Dict[str, Any]] = []
    rule_lookup = {
        str(rule.get("rule_id") or "").strip(): rule
        for rule in rules
        if isinstance(rule, dict) and str(rule.get("rule_id") or "").strip()
    }

    def _finalize(
        finding: ContradictionFinding,
        *,
        record: Optional[ReconciliationRecord] = None,
        original_rule: Optional[Dict[str, Any]] = None,
        paired_rule: Optional[Dict[str, Any]] = None,
    ) -> ContradictionFinding:
        classification, reason, business_relevant, counted_for_review = _classify_contradiction_finding(
            contradiction_type=finding.type,
            record=record,
            original_rule=original_rule,
            paired_rule=paired_rule,
            contradiction=finding,
        )
        finding.classification = classification
        finding.classification_reason = reason
        finding.business_relevant = business_relevant
        finding.counted_for_review = counted_for_review
        finding.review_item_id = _record_review_item_id(record) if record else _contradiction_review_item_id(finding)
        return finding

    for record in records:
        if record.kind == "tables_read" or record.kind == "tables_written":
            if record.status != "CONFLICT":
                continue
            llm_claim = record.llm_claim or {}
            deterministic = record.deterministic_evidence or {}
            llm_table = _clean_text(llm_claim.get("table"))
            det_table = _clean_text(deterministic.get("table"))
            if llm_table and det_table and _normalize_value(llm_table) != _normalize_value(det_table):
                contradictions.append(
                    _finalize(
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
                        ),
                        record=record,
                    )
                )
            llm_operation = _clean_text(llm_claim.get("operation"))
            det_operation = _clean_text(deterministic.get("operation"))
            if llm_operation and det_operation and _normalize_value(llm_operation) != _normalize_value(det_operation):
                contradictions.append(
                    _finalize(
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
                        ),
                        record=record,
                    )
                )
            llm_columns = {_normalize_column_reference(v) for v in llm_claim.get("target_columns") or llm_claim.get("columns") or [] if _clean_text(v)}
            det_columns = {_normalize_column_reference(v) for v in deterministic.get("target_columns") or deterministic.get("columns") or [] if _clean_text(v)}
            if record.kind == "tables_written" and llm_columns and det_columns and llm_columns != det_columns:
                contradictions.append(
                    _finalize(
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
                        ),
                        record=record,
                    )
                )
            llm_filter = _clean_text(llm_claim.get("filter_condition") or llm_claim.get("where_predicate") or llm_claim.get("trigger_condition"))
            det_filter = _clean_text(deterministic.get("filter_condition") or deterministic.get("where_predicate") or deterministic.get("trigger_condition"))
            if llm_filter and det_filter and not _expressions_semantically_equal(llm_filter, det_filter):
                contradictions.append(
                    _finalize(
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
                        ),
                        record=record,
                    )
                )
            llm_assignment_values = {_normalize_sql_fragment(v).lower() for v in _row_assigned_values(llm_claim) if _clean_text(v)}
            det_assignment_values = {_normalize_sql_fragment(v).lower() for v in _row_assigned_values(deterministic) if _clean_text(v)}
            if llm_assignment_values and det_assignment_values and llm_assignment_values != det_assignment_values:
                contradictions.append(
                    _finalize(
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
                        ),
                        record=record,
                    )
                )
            continue

        if record.kind != "rule" or record.status != "CONFLICT":
            continue
        original_rule = rule_lookup.get(record.rule_id or "", {})
        comparison = record.comparison or {}
        if comparison.get("field_status") == "CONFLICT":
            contradictions.append(
                _finalize(
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
                    ),
                    record=record,
                    original_rule=original_rule,
                )
            )
        if comparison.get("condition_status") == "CONFLICT":
            llm_conditions = _find_record_condition_values(record)
            contradictions.append(
                _finalize(
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
                    ),
                    record=record,
                    original_rule=original_rule,
                )
            )
        if comparison.get("outcome_status") == "CONFLICT":
            llm_outcomes = _find_record_outcome_values(record)
            contradictions.append(
                _finalize(
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
                    ),
                    record=record,
                    original_rule=original_rule,
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
        chunk_union = sorted({
            str(chunk).strip()
            for rule in grouped_rules
            for chunk in (rule.get("source_chunk_ids") or rule.get("source_chunks") or [])
            if str(chunk).strip()
        })
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
            right_chunks, right_statements = _rule_source_identity(right_rule)
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

            contradictory = _rules_have_structural_overlap(left_rule, right_rule)
            explanation = ""
            if contradictory:
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
                        *right_chunks,
                    }
                )
                contradictions.append(
                    _finalize(
                        _create_contradiction(
                        object_id=object_id,
                        contradiction_type="rule_vs_rule_conflict",
                        severity="HIGH",
                        related_rule_ids=related_rule_ids,
                        chunk_ids=chunk_ids,
                        statement_ids=sorted(
                            {
                                *left_statements,
                                *right_statements,
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
                        ),
                        original_rule=left_rule,
                        paired_rule=right_rule,
                    )
            )

    deduped_contradictions: List[ContradictionFinding] = []
    seen_contradiction_ids: set[str] = set()
    for contradiction in contradictions:
        if contradiction.contradiction_id in seen_contradiction_ids:
            continue
        seen_contradiction_ids.add(contradiction.contradiction_id)
        deduped_contradictions.append(contradiction)

    return deduped_contradictions, duplicate_groups


def _build_coverage_metrics(
    *,
    merged_extraction: Dict[str, Any],
    rules: Sequence[Dict[str, Any]],
    records: Sequence[ReconciliationRecord],
    contradictions: Sequence[ContradictionFinding],
    duplicate_rule_groups: Sequence[Dict[str, Any]],
    classification_summary: Optional[Dict[str, Any]] = None,
    review_summary: Optional[Dict[str, Any]] = None,
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
    # Scoring-only count: excludes LLM_ONLY records and review-required contradictions,
    # since both are already penalized separately (llm_only_rules bucket, and the
    # HIGH/MEDIUM/LOW contradiction-severity buckets) in _build_quality_assessment.
    # review_required_items itself stays unchanged above — it is the accurate,
    # user-facing "N items need review" count and must not undercount.
    unresolved_for_scoring = sum(
        1
        for record in records
        if record.status in {"CONFLICT", "UNRESOLVED"}
        or (record.status == "MATCHED" and unsupported_dialect)
    )

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
        "unresolved_for_scoring": unresolved_for_scoring,
        "duplicate_rule_groups": len(list(duplicate_rule_groups)),
    }
    if classification_summary:
        metrics["genuine_business_contradictions"] = int(classification_summary.get("genuine_business_contradictions", 0) or 0)
        metrics["technical_provenance_noise"] = int(classification_summary.get("technical_provenance_noise", 0) or 0)
        metrics["technical_vs_business_overlap"] = int(classification_summary.get("technical_vs_business_overlap", 0) or 0)
        metrics["valid_ordered_branches"] = int(classification_summary.get("valid_ordered_branches", 0) or 0)
        metrics["insufficient_evidence_contradictions"] = int(classification_summary.get("insufficient_evidence", 0) or 0)
        metrics["expected_non_business_findings"] = int(classification_summary.get("expected_non_business_findings", 0) or 0)
    if review_summary:
        metrics["review_item_count"] = int(review_summary.get("review_item_count", 0) or 0)
        metrics["business_review_required_items"] = int(review_summary.get("business_review_required_items", 0) or 0)
        metrics["expected_review_items"] = int(review_summary.get("expected_review_items", 0) or 0)
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
    unresolved_items = int(
        coverage.get("unresolved_for_scoring", coverage.get("review_required_items", 0)) or 0
    )
    business_review_items = int(coverage.get("business_review_required_items", unresolved_items) or unresolved_items)
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
            "business_review_required_items": business_review_items,
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
        source_chunks, source_statements = _rule_source_identity(rule)
        candidate_rows = _rule_candidate_rows(rule, deterministic_rows)
        if candidate_rows:
            relevant_rows = [
                row
                for row in candidate_rows
                if _row_relevant_to_rule(row, claim_fields, claim_conditions, claim_outcomes)
            ]
            if relevant_rows:
                candidate_rows = relevant_rows

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
            claim_field_set = _normalize_claim_axis_values(claim_fields, column_references=True)
            claim_condition_set = _normalize_claim_axis_values(claim_conditions)
            claim_outcome_set: set[str] = set()
            for value in claim_outcomes:
                parsed = _parse_structured_assignment(value)
                if parsed and _clean_text(parsed.get("rhs")):
                    claim_outcome_set.add(_normalize_sql_fragment(parsed.get("rhs")).lower())
                elif _clean_text(value):
                    claim_outcome_set.add(_normalize_sql_fragment(value).lower())
            field_union: set[str] = set()
            condition_union: set[str] = set()
            outcome_union: set[str] = set()
            for row in candidate_rows:
                row_fields = {_normalize_column_reference(value) for value in _row_columns(row) if _clean_text(value)}
                row_filter = _row_filter(row)
                row_values = {_normalize_sql_fragment(value).lower() for value in _row_assigned_values(row) if _clean_text(value)}
                field_union |= row_fields
                if row_filter:
                    condition_union.add(row_filter)
                outcome_union |= row_values

            field_match = bool(claim_field_set and field_union and claim_field_set.issubset(field_union))
            condition_match = bool(claim_condition_set and condition_union and claim_condition_set.issubset(condition_union))
            outcome_match = bool(claim_outcome_set and outcome_union and claim_outcome_set.issubset(outcome_union))
            field_conflict = bool(claim_field_set and field_union and not field_match)
            condition_conflict = bool(claim_condition_set and condition_union and not condition_match)
            outcome_conflict = bool(claim_outcome_set and outcome_union and not outcome_match)

            if field_conflict or condition_conflict or outcome_conflict:
                status = "CONFLICT"
            elif field_match or condition_match or outcome_match:
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
                "field_status": "MATCHED" if field_match else ("CONFLICT" if field_conflict else "UNRESOLVED"),
                "condition_status": "MATCHED" if condition_match else ("CONFLICT" if condition_conflict else "UNRESOLVED"),
                "outcome_status": "MATCHED" if outcome_match else ("CONFLICT" if outcome_conflict else "UNRESOLVED"),
            }
            if status != "CONFLICT" and not (field_match or condition_match or outcome_match):
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
                statement_id=";".join(sorted(source_statements or deterministic_evidence.get("statement_ids", []))),
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
        str(chunk).split(":", 1)[0].strip()
        for rule in rules
        for chunk in (rule.get("source_chunk_ids") or rule.get("source_chunks") or [])
        if str(chunk).strip()
    }
    rule_statement_refs = {
        str(statement).strip()
        for rule in rules
        for statement in (rule.get("source_statement_ids") or rule.get("technical_references") or [])
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
    classification_summary = _classification_summary_from_contradictions(contradictions)
    review_summary = _build_review_summary(
        records=records,
        contradictions=contradictions,
        unsupported_dialect=unsupported_dialect,
    )
    coverage = _build_coverage_metrics(
        merged_extraction=merged_extraction,
        rules=rules,
        records=records,
        contradictions=contradictions,
        duplicate_rule_groups=duplicate_rule_groups,
        classification_summary=classification_summary,
        review_summary=review_summary,
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
        "business_review_required_items": review_summary["business_review_required_items"],
        "expected_review_items": review_summary["expected_review_items"],
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
        classification_summary=classification_summary,
        review_summary=review_summary,
        coverage=coverage,
        quality=quality,
        duplicate_rule_groups=duplicate_rule_groups,
    )
