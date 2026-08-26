from __future__ import annotations

from typing import Any, Iterable

_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def normalize_confidence(value: Any, default: str = "medium") -> str:
    confidence = str(value or "").strip().lower()
    return confidence if confidence in _CONFIDENCE_ORDER else default


def _rank(confidence: str) -> int:
    return _CONFIDENCE_ORDER.get(normalize_confidence(confidence), 1)


def clamp_confidence(*values: Any) -> str:
    if not values:
        return "medium"
    return max((normalize_confidence(v) for v in values), key=_rank)


def derive_chunk_support_confidence(
    *,
    parse_error: str = "",
    guardrail_warnings: Iterable[str] | None = None,
    has_direct_evidence: bool = True,
    has_embedded_sql: bool = False,
    ambiguity_count: int = 0,
    dynamic_sql_detected: bool = False,
    parser_unavailable: bool = False,
) -> str:
    warnings = list(guardrail_warnings or [])
    if parse_error or parser_unavailable or dynamic_sql_detected:
        return "low"
    if ambiguity_count:
        return "low"
    if warnings:
        return "medium" if has_direct_evidence or has_embedded_sql else "low"
    if has_direct_evidence:
        return "high"
    return "low"


def derive_business_rule_confidence(
    *,
    validation_status: str,
    source_evidence_count: int,
    matched_record_count: int,
    source_chunk_count: int,
    parser_failed: bool = False,
    low_support: bool = False,
    ambiguous: bool = False,
    unresolved_evidence: bool = False,
    rule_type: str = "inferred",
    llm_only: bool = False,
) -> str:
    status = str(validation_status or "").strip().lower()
    rule_type = str(rule_type or "").strip().lower()

    if parser_failed or low_support or ambiguous or unresolved_evidence:
        return "low"
    if status in {"parser_failed", "insufficient_evidence", "ambiguous"}:
        return "low"
    if source_evidence_count == 0:
        return "low"
    if llm_only or rule_type == "assumption":
        return "low"

    if status == "verified" and matched_record_count >= 1 and source_chunk_count >= 1:
        return "high"
    if status == "verified" and matched_record_count >= 1:
        return "high"
    if matched_record_count >= 1:
        return "medium"
    return "low"
