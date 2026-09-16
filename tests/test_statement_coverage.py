"""Regression tests for `RuleSynthesizerAgent.ensure_statement_coverage`.

`ensure_decision_chain_coverage` guarantees a rule for every multi-branch
CASE/IF ladder the source contains, but a single UPDATE/INSERT statement
that assigns a literal/simple value under its own WHERE clause - with no
second branch at all - had no equivalent guarantee: it could silently
vanish from the report if the model's own synthesis pass missed it.
`ensure_statement_coverage` closes that gap directly from the deterministic
`table_operations` extraction, with no LLM call involved.
"""
from __future__ import annotations

from src.synthesis.rule_synthesizer import RuleSynthesizerAgent


def _operation(**overrides):
    base = {
        "table": "ACCOUNT",
        "operation": "UPDATE",
        "source_statement_id": "chunk_1:stmt_01",
        "source_chunk_id": "chunk_1",
        "source_line_start": 4,
        "source_line_end": 4,
        "source_char_start": 10,
        "source_char_end": 40,
        "where_predicate": "LastPaymentDueDate IS NULL",
        "assigned_values": [
            {"column": "DpdBucket", "expression": "'NOT_APPLICABLE'"},
        ],
    }
    base.update(overrides)
    return base


def test_synthesizes_a_rule_for_an_uncovered_single_branch_conditional_write():
    merged_extraction = {"table_operations": [_operation()]}
    rules = RuleSynthesizerAgent.ensure_statement_coverage([], merged_extraction)
    assert len(rules) == 1
    rule = rules[0]
    assert rule["output_field"] == "DpdBucket"
    assert rule["rule_type"] == "deterministic_decision_table"
    assert rule["confidence"] == "deterministic"
    assert rule["decision_logic_rows"] == [
        {"condition": "LastPaymentDueDate IS NULL", "outcome": "'NOT_APPLICABLE'"}
    ]


def test_skips_a_field_already_named_by_an_existing_rule():
    existing = [{
        "rule_id": "r1",
        "output_field": "DpdBucket",
        "decision_logic_rows": [
            {"condition": "LastPaymentDueDate IS NULL", "outcome": "'NOT_APPLICABLE'"},
        ],
    }]
    merged_extraction = {"table_operations": [_operation()]}
    rules = RuleSynthesizerAgent.ensure_statement_coverage(existing, merged_extraction)
    assert len(rules) == 1
    assert rules == existing


def test_contentless_shell_does_not_block_conditional_write_floor():
    """A model shell that only names columns must not suppress the floor.

    Observed on DPD audit INSERT: fields_affected listed TransitionDate /
    NewBucket with zero decision rows; reconciliation then CONFLICT-
    excluded the shell and the write vanished from the report.
    """
    shell = {
        "rule_id": "shell",
        "rule_name": "Log DPD bucket transitions",
        "output_field": "DpdBucketAuditLog",
        "fields_affected": ["AccountId", "TransitionDate", "NewBucket"],
    }
    audit_op = _operation(
        table="PRO.DpdBucketAuditLog",
        operation="INSERT",
        source_statement_id="chunk_1:stmt_audit",
        where_predicate="H.LastUpdatedDate = @ProcessDate",
        assigned_values=[
            {"column": "AccountId", "expression": "H.AccountId"},
            {"column": "TransitionDate", "expression": "@ProcessDate"},
            {"column": "NewBucket", "expression": "H.DpdBucket"},
        ],
    )
    rules = RuleSynthesizerAgent.ensure_statement_coverage([shell], {"table_operations": [audit_op]})
    shell_rule = next(rule for rule in rules if rule.get("rule_id") == "shell")
    assert shell_rule.get("decision_logic_rows")
    assert "TransitionDate" in str(shell_rule.get("output_field") or "")
    assert shell_rule.get("decision_rows_grounded") is True


def test_insert_with_case_column_is_not_floored_as_passthrough_rules():
    """CollectionsQueue-style INSERT: CASE Reason is chain-owned; do not
    invent separate EscalationDate / AccountId floors for the same INSERT.
    """
    op = _operation(
        table="PRO.CollectionsQueue",
        operation="INSERT",
        source_statement_id="chunk_1:stmt_queue",
        where_predicate="BucketWorsened = 'Y'",
        assigned_values=[
            {"column": "AccountId", "expression": "AccountId"},
            {"column": "EscalationDate", "expression": "@ProcessDate"},
            {
                "column": "Reason",
                "expression": "CASE WHEN x THEN 'A' ELSE 'B' END",
                # case_branches may be absent when ops come from a secondary
                # extractor path - expression text alone must still gate.
            },
        ],
    )
    shell = {
        "rule_id": "esc",
        "rule_name": "Insert escalation records",
        "output_field": "CollectionsQueue",
        "fields_affected": ["AccountId", "EscalationDate", "Reason"],
    }
    rules = RuleSynthesizerAgent.ensure_statement_coverage(
        [shell], {"table_operations": [op]}
    )
    assert rules == []


def test_skips_an_unconditional_write_with_no_where_predicate():
    merged_extraction = {"table_operations": [_operation(where_predicate="")]}
    rules = RuleSynthesizerAgent.ensure_statement_coverage([], merged_extraction)
    assert rules == []


def test_skips_an_assignment_whose_value_is_a_case_expression():
    # Already covered by ensure_decision_chain_coverage's own extraction -
    # synthesizing here too would create a redundant second table for the
    # same statement.
    op = _operation(assigned_values=[
        {"column": "DpdBucket", "expression": "CASE WHEN x THEN 1 ELSE 0 END",
         "case_branches": [{"condition": "x", "value": "1"}]},
    ])
    rules = RuleSynthesizerAgent.ensure_statement_coverage([], {"table_operations": [op]})
    assert rules == []


def test_skips_process_bookkeeping_tables():
    op = _operation(table="ACLRUNNINGPROCESSSTATUS", assigned_values=[
        {"column": "COMPLETED", "expression": "1"},
    ])
    rules = RuleSynthesizerAgent.ensure_statement_coverage([], {"table_operations": [op]})
    assert rules == []


def test_deduplicates_the_same_statement_and_field_across_repeated_calls():
    merged_extraction = {"table_operations": [_operation()]}
    once = RuleSynthesizerAgent.ensure_statement_coverage([], merged_extraction)
    twice = RuleSynthesizerAgent.ensure_statement_coverage(once, merged_extraction)
    assert len(twice) == 1


def test_no_table_operations_returns_rules_unchanged():
    existing = [{"rule_id": "r1", "output_field": "X"}]
    assert RuleSynthesizerAgent.ensure_statement_coverage(existing, {}) == existing
    assert RuleSynthesizerAgent.ensure_statement_coverage(existing, None) == existing


def test_two_distinct_conditional_writes_each_get_their_own_rule():
    grace_op = _operation(
        table="ACCOUNT",
        source_statement_id="chunk_1:stmt_02",
        where_predicate="LastPaymentDueDate >= @GraceWindowStart",
        assigned_values=[{"column": "GracePeriodApplied", "expression": "'Y'"}],
    )
    merged_extraction = {"table_operations": [_operation(), grace_op]}
    rules = RuleSynthesizerAgent.ensure_statement_coverage([], merged_extraction)
    assert {r["output_field"] for r in rules} == {"DpdBucket", "GracePeriodApplied"}
