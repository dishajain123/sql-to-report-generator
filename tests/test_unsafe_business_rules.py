"""Deterministic safety fixtures for unsafe synthesized business rules.

These tests model the output of a mocked synthesis response.  They deliberately
exercise downstream grounding, reconciliation, quality, and verification
reporting rather than testing whether JSON parsing accepts the response.
"""

from __future__ import annotations

import pytest

from src.ir.canonical_ir import CanonicalBusinessIR
from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from src.validation.reconciliation import reconcile_deterministic_evidence
from tests.test_reconciliation import _make_ingestion, _rule


def _chain(*branches, chain_type="IF_ELSIF_ELSE", subject="STATUS"):
    return {
        "chain_id": "fixture_chain",
        "chain_type": chain_type,
        "subject": subject,
        "branches": list(branches),
    }


def _branch(condition, value, *, field="STATUS", catch_all=False):
    return {
        "branch_condition": condition,
        "is_catch_all": catch_all,
        "assignments": [{"field": field, "value": value}],
    }


def _base_merged(chains=None):
    return {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "decision_chains": list(chains or []),
        "statement_provenance": [
            {
                "statement_id": "stmt_fixture",
                "source_chunk_id": "chunk_1",
                "parse_status": "parsed",
                "source_line_start": 1,
                "source_line_end": 8,
            }
        ],
    }


def _run_fixture(name, merged, rules):
    ingestion = _make_ingestion(dialect="TSQL")
    synthesis = SynthesisResult(data={"business_rules": rules})
    reconciliation = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )
    report_data = dict(merged)
    report_data["reconciliation"] = reconciliation.to_dict()
    report_data["coverage"] = reconciliation.coverage
    report_data["quality"] = reconciliation.quality
    canonical = CanonicalBusinessIR.from_pipeline(
        ingestion=ingestion,
        merged_extraction=report_data,
        synthesis=synthesis,
        reconciliation=reconciliation,
    )
    verification = ReportFormatterAgent().format_verification(
        ingestion=ingestion,
        merged_extraction=report_data,
        synthesis=synthesis,
        canonical_ir=canonical,
    )
    assert "## Quality Summary" in verification, name
    assert "**Review required:" in verification, name
    return reconciliation, verification


def _correct_chain_rules():
    return [
        _rule(
            rule_id="rule_high",
            fields_affected=["STATUS"],
            condition="SCORE >= 90",
            action="STATUS = 'A'",
            source_evidence=["SCORE >= 90"],
        ),
        _rule(
            rule_id="rule_default",
            fields_affected=["STATUS"],
            condition="ELSE",
            action="STATUS = 'B'",
            source_evidence=["ELSE"],
        ),
    ]


@pytest.fixture
def two_branch_chain():
    return _chain(
        _branch("SCORE >= 90", "'A'"),
        _branch("ELSE", "'B'", catch_all=True),
    )


@pytest.mark.parametrize(
    "name, rules_factory, expected_status, expected_coverage",
    [
        (
            "omitted_else",
            lambda: [_correct_chain_rules()[0]],
            "MATCHED",
            50.0,
        ),
        (
            "omitted_if",
            lambda: [_correct_chain_rules()[1]],
            "MATCHED",
            50.0,
        ),
        (
            "wrong_branch_outcome",
            lambda: [
                _rule(
                    fields_affected=["STATUS"],
                    condition="SCORE >= 90",
                    action="STATUS = 'Z'",
                    source_evidence=["SCORE >= 90"],
                )
            ],
            "CONFLICT",
            50.0,
        ),
        (
            "wrong_comparison_operator",
            lambda: [
                _rule(
                    fields_affected=["STATUS"],
                    condition="SCORE > 90",
                    action="STATUS = 'A'",
                    source_evidence=["SCORE >= 90"],
                )
            ],
            "CONFLICT",
            50.0,
        ),
        (
            "wrong_literal",
            lambda: [
                _rule(
                    fields_affected=["STATUS"],
                    condition="SCORE >= 90",
                    action="STATUS = 'Z'",
                    source_evidence=["SCORE >= 90"],
                )
            ],
            "CONFLICT",
            50.0,
        ),
        (
            "hallucinated_field",
            lambda: [
                _rule(
                    fields_affected=["UNRELATED_FIELD"],
                    condition="SCORE >= 90",
                    action="UNRELATED_FIELD = 'A'",
                    source_evidence=["SCORE >= 90"],
                )
            ],
            "CONFLICT",
            50.0,
        ),
        (
            "rule_without_evidence",
            lambda: [
                _rule(
                    fields_affected=["STATUS"],
                    condition="SCORE >= 90",
                    action="STATUS = 'A'",
                )
            ],
            "LLM_ONLY",
            50.0,
        ),
    ],
)
def test_unsafe_branch_fixtures_reach_downstream_review(
    two_branch_chain, name, rules_factory, expected_status, expected_coverage
):
    result, report = _run_fixture(
        name,
        _base_merged([two_branch_chain]),
        rules_factory(),
    )
    rule_record = next(record for record in result.records if record.kind == "rule")

    assert rule_record.status == expected_status
    expected_confidence = "low" if expected_status in {"CONFLICT", "LLM_ONLY"} else "high"
    assert rule_record.confidence == expected_confidence
    assert result.coverage["decision_chain_coverage_pct"] == expected_coverage
    assert result.quality["status"] == "REVIEW_REQUIRED"
    assert result.quality["review_required"] is True
    assert "**Review required:** Yes" in report
    if expected_status == "CONFLICT":
        assert result.contradictions
        assert any(item.classification == "GENUINE_BUSINESS_CONTRADICTION" for item in result.contradictions)


def test_wrong_null_behavior_is_a_conflict_and_is_reported():
    chain = _chain(
        _branch("ACCOUNT_ID IS NULL", "'UNASSIGNED'"),
        _branch("ELSE", "'ASSIGNED'", catch_all=True),
        subject="ACCOUNT_STATUS",
    )
    rule = _rule(
        fields_affected=["ACCOUNT_STATUS"],
        condition="ACCOUNT_ID IS NOT NULL",
        action="ACCOUNT_STATUS = 'UNASSIGNED'",
        source_evidence=["ACCOUNT_ID IS NULL"],
    )
    result, report = _run_fixture("wrong_null_behavior", _base_merged([chain]), [rule])

    assert result.records[0].status == "CONFLICT"
    assert result.records[0].comparison["condition_status"] == "CONFLICT"
    assert result.coverage["decision_chain_coverage_pct"] == 50.0
    assert result.quality["status"] == "REVIEW_REQUIRED"
    assert "condition_conflict" in report.lower() or "contradiction" in report.lower()


def test_wrong_date_boundary_is_a_conflict_and_is_reported():
    chain = _chain(
        _branch("DUE_DATE < '2024-01-01'", "'OVERDUE'"),
        _branch("ELSE", "'CURRENT'", catch_all=True),
        subject="ACCOUNT_STATUS",
    )
    rule = _rule(
        fields_affected=["ACCOUNT_STATUS"],
        condition="DUE_DATE <= '2024-01-01'",
        action="ACCOUNT_STATUS = 'OVERDUE'",
        source_evidence=["DUE_DATE < '2024-01-01'"],
    )
    result, report = _run_fixture("wrong_date_boundary", _base_merged([chain]), [rule])

    assert result.records[0].status == "CONFLICT"
    assert result.records[0].comparison["condition_status"] == "CONFLICT"
    assert result.quality["review_required"] is True
    assert "**Review required:** Yes" in report


def test_unsupported_dynamic_sql_claim_remains_low_confidence_and_reviewable():
    merged = _base_merged()
    merged["ambiguities"] = ["The target is assembled dynamically at runtime."]
    rule = _rule(
        fields_affected=[],
        condition="dynamic sql is assembled at runtime",
        action="Flag for manual review",
        confidence="low",
        rule_type="assumption",
        source_evidence=[],
    )
    result, report = _run_fixture("unsupported_dynamic_sql", merged, [rule])

    assert result.records[0].status == "LLM_ONLY"
    assert result.records[0].confidence == "low"
    assert result.coverage["decision_chain_coverage_pct"] == 100.0
    assert result.quality["status"] == "REVIEW_REQUIRED"
    assert result.quality["review_required"] is True
    assert "**Review required:** Yes" in report


def test_duplicate_business_rules_are_grouped_without_false_contradiction():
    chain = _chain(_branch("SCORE >= 90", "'A'"), _branch("ELSE", "'B'", catch_all=True))
    first = _correct_chain_rules()[0]
    second = {**first, "rule_id": "rule_high_duplicate", "source_chunks": ["chunk_2"]}
    first["source_chunks"] = ["chunk_1"]
    result, report = _run_fixture("duplicate_business_rule", _base_merged([chain]), [first, second])

    assert result.coverage["duplicate_rule_groups"] >= 1
    assert not any(item.classification == "GENUINE_BUSINESS_CONTRADICTION" for item in result.contradictions)
    assert result.quality["status"] == "REVIEW_REQUIRED"  # the ELSE branch is still uncovered
    assert "**Review required:** Yes" in report


def test_contradictory_business_rule_is_conflict_and_review_required():
    chain = _chain(_branch("SCORE >= 90", "'A'"), _branch("ELSE", "'B'", catch_all=True))
    rules = [
        _correct_chain_rules()[0],
        _rule(
            rule_id="rule_conflict",
            fields_affected=["STATUS"],
            condition="SCORE >= 90",
            action="STATUS = 'Z'",
            source_evidence=["SCORE >= 90"],
        ),
    ]
    result, report = _run_fixture("contradictory_business_rule", _base_merged([chain]), rules)

    assert any(item.classification == "GENUINE_BUSINESS_CONTRADICTION" for item in result.contradictions)
    assert any(record.status == "CONFLICT" for record in result.records if record.kind == "rule")
    assert result.quality["status"] == "REVIEW_REQUIRED"
    assert "Contradictions" in report
    assert "**Review required:** Yes" in report


@pytest.mark.parametrize("name, fallback_condition", [
    ("correct_paraphrased_rule", "the score meets the high-score threshold"),
    ("correct_fallback_wording", "all other scores"),
])
def test_correct_paraphrase_and_fallback_are_not_false_contradictions(
    name, fallback_condition, two_branch_chain
):
    rules = [
        _rule(
            rule_id="rule_high",
            fields_affected=["STATUS"],
            condition="the score meets the high-score threshold" if "paraphrased" in name else "SCORE >= 90",
            action="STATUS = 'A'",
            source_evidence=["SCORE >= 90"],
        ),
        _rule(
            rule_id="rule_default",
            fields_affected=["STATUS"],
            condition=fallback_condition,
            action="STATUS = 'B'",
            source_evidence=["ELSE"],
        ),
    ]
    result, report = _run_fixture(name, _base_merged([two_branch_chain]), rules)

    assert all(record.status == "MATCHED" for record in result.records if record.kind == "rule")
    assert not any(item.classification == "GENUINE_BUSINESS_CONTRADICTION" for item in result.contradictions)
    assert result.coverage["decision_chain_coverage_pct"] == 100.0
    assert result.quality["status"] == "PASS"
    assert result.quality["review_required"] is False
    assert "**Review required:** No" in report


def test_technical_status_statement_is_removed_before_business_reporting():
    technical_rule = _rule(
        fields_affected=["COMPLETED"],
        condition="process finishes",
        action="Sets process status to COMPLETED",
        source_evidence=["RUNNINGPROCESSSTATUS"],
    )
    merged = _base_merged()
    merged["table_operations"] = [
        {"table": "RUNNINGPROCESSSTATUS", "operation": "UPDATE", "target_columns": ["COMPLETED"]}
    ]
    filtered = RuleSynthesizerAgent._remove_operational_status_rules(
        [technical_rule], merged
    )
    result, report = _run_fixture("technical_statement_not_business_rule", merged, filtered)

    assert filtered == []
    assert not any(record.kind == "rule" for record in result.records)
    assert result.quality["status"] == "LOW_CONFIDENCE"
    assert result.quality["review_required"] is False
    assert "No synthesized rules were available" in report
