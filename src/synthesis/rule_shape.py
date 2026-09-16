"""Permanent structural shaping of synthesized business rules.

Rule counts come from SQL structure (one rule per real decision), not from
sample ``-- Rule N`` comments. Those comments are a soft reference only.

This module collapses MERGE upsert halves and suppresses IF-ladder branch
fragments so the business-rule list (and Canonical IR) already carries the
intended shape. Report formatting may re-apply the same shaping as a
safety net for older IRs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _is_decision_rows_grounded(rule: Dict[str, Any]) -> bool:
    if bool(rule.get("decision_rows_grounded")):
        return True
    rule_type = str(rule.get("rule_type") or "").strip().lower()
    rows = rule.get("decision_logic_rows")
    return rule_type == "deterministic_decision_table" and isinstance(rows, list) and bool(rows)


def shape_structural_business_rules(
    rules: Optional[List[Dict[str, Any]]],
    merged_extraction: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Collapse MERGE halves and drop IF-ladder fragment shells permanently.

    Uses the same heuristics as report formatting so pipeline output, IR, and
    reports agree on one rule per structural decision.
    """
    from src.output.report_formatter import ReportFormatterAgent

    agent = ReportFormatterAgent()
    shaped = list(rules or [])
    shaped = agent._suppress_decision_ladder_branch_fragments(shaped, merged_extraction)
    shaped = agent._collapse_merge_upsert_halves(shaped, merged_extraction)
    return shaped


def clear_grounded_reconciliation_conflicts(
    rules: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Keep SQL-grounded decision tables out of CONFLICT exclusion.

    Reconciliation can mark a grounded ladder CONFLICT when the model also
    emitted overlapping fragments. Those fragments are shaped away; the
    grounded table itself must remain MATCHED for IR and reports.
    """
    cleaned: List[Dict[str, Any]] = []
    for rule in list(rules or []):
        if not isinstance(rule, dict):
            continue
        item = dict(rule)
        status = str(item.get("reconciliation_status") or "").strip().upper()
        if status == "CONFLICT" and _is_decision_rows_grounded(item):
            item["reconciliation_status"] = "MATCHED"
            item["validation_status"] = "MATCHED"
        cleaned.append(item)
    return cleaned


def drop_ungrounded_conflict_rules(
    rules: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Remove non-grounded CONFLICT shells from the permanent rule list.

    Grounded decision tables are retained (and should already be cleared via
    :func:`clear_grounded_reconciliation_conflicts`).
    """
    kept: List[Dict[str, Any]] = []
    for rule in list(rules or []):
        if not isinstance(rule, dict):
            continue
        status = str(rule.get("reconciliation_status") or "").strip().upper()
        if status == "CONFLICT" and not _is_decision_rows_grounded(rule):
            continue
        kept.append(rule)
    return kept


def finalize_business_rule_shape(
    rules: Optional[List[Dict[str, Any]]],
    merged_extraction: Optional[Dict[str, Any]] = None,
    *,
    after_reconciliation: bool = False,
) -> List[Dict[str, Any]]:
    """Apply permanent structural shaping for pipeline / IR.

    Call once after floors + alias rewrite (``after_reconciliation=False``),
    then again after reconciliation so CONFLICT cleanup sticks on the IR.
    """
    shaped = shape_structural_business_rules(rules, merged_extraction)
    if after_reconciliation:
        shaped = clear_grounded_reconciliation_conflicts(shaped)
        shaped = drop_ungrounded_conflict_rules(shaped)
    return shaped
