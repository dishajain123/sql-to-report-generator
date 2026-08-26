"""
Focused tests for deterministic reconciliation.

Run with:  pytest tests/test_reconciliation.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.ingestion.ingestion import CodeChunk, IngestionResult
from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import SynthesisResult
from src.validation.reconciliation import reconcile_deterministic_evidence


def _make_ingestion(dialect: str = "ORACLE") -> IngestionResult:
    return IngestionResult(
        object_name="demo_proc",
        object_type="PROCEDURE",
        parameters=[],
        raw_code="select 1",
        chunks=[CodeChunk(chunk_id="chunk_1", kind="main_body", text="select 1")],
        object_id="obj_1",
        dialect=dialect,
        concrete_dialect=dialect.lower() if dialect else "",
        fallback_dialect="oracle",
        source_hash="source-hash",
    )


def _make_synthesis(rules):
    return SynthesisResult(data={"business_rules": rules})


def _table_row(table, operation, *, chunk_id="chunk_1", statement_id="stmt_1", columns=None, filter_condition=None, assigned_values=None):
    row = {
        "table": table,
        "operation": operation,
        "source_chunk_id": chunk_id,
        "statement_id": statement_id,
        "source_statement_id": statement_id,
        "target_columns": list(columns or []),
        "columns": list(columns or []),
        "filter_condition": filter_condition,
        "where_predicate": filter_condition,
        "assigned_values": list(assigned_values or []),
    }
    return row


def _rule(
    *,
    rule_id="rule_1",
    rule_name="Rule 1",
    source_chunks=None,
    technical_references=None,
    fields_affected=None,
    condition=None,
    action=None,
    decision_logic_rows=None,
):
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "source_chunks": list(source_chunks or []),
        "technical_references": list(technical_references or []),
        "fields_affected": list(fields_affected or []),
        "condition": condition,
        "action": action,
        "decision_logic_rows": list(decision_logic_rows or []),
        "validation_status": "verified",
        "rule_type": "explicit",
        "confidence": "medium",
    }


def _find_record(result, *, kind=None, status=None):
    for record in result.records:
        if kind is not None and record.kind != kind:
            continue
        if status is not None and record.status != status:
            continue
        return record
    raise AssertionError(f"No record found for kind={kind!r} status={status!r}")


def test_matching_table_operation_is_marked_matched():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
    }
    synthesis = _make_synthesis([
        _rule(
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["STATUS"],
            condition="STATUS = 'A'",
            action="STATUS = 'A'",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="tables_written", status="MATCHED")
    assert record.llm_claim["table"] == "ACCOUNT"
    assert record.deterministic_evidence["table"] == "ACCOUNT"
    assert record.confidence in {"medium", "high"}


def test_table_conflict_is_preserved():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "MERGE", columns=["STATUS"])],
    }
    synthesis = _make_synthesis([
        _rule(
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["STATUS"],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="tables_written", status="CONFLICT")
    assert record.comparison["table_status"] == "CONFLICT"
    assert record.deterministic_evidence["operation"] == "UPDATE"
    assert record.llm_claim["operation"] == "MERGE"


def test_field_conflict_is_detected_from_deterministic_columns():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["SMA_STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["SMA_STATUS"])],
    }
    synthesis = _make_synthesis([
        _rule(
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["STATUS"],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="CONFLICT")
    assert record.comparison["field_status"] == "CONFLICT"
    assert record.deterministic_evidence["target_columns"] == ["SMA_STATUS"]


def test_condition_conflict_is_detected():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                columns=["SMA_STATUS"],
                filter_condition="DPD > 30",
            )
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                columns=["SMA_STATUS"],
                filter_condition="DPD > 30",
            )
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["SMA_STATUS"],
            condition="DPD >= 30",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="CONFLICT")
    assert record.comparison["condition_status"] == "CONFLICT"


def test_outcome_conflict_is_detected():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                columns=["SMA_STATUS"],
                assigned_values=[{"column": "SMA_STATUS", "expression": "'SMA-1'"}],
            )
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                columns=["SMA_STATUS"],
                assigned_values=[{"column": "SMA_STATUS", "expression": "'SMA-1'"}],
            )
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["SMA_STATUS"],
            action="SMA_STATUS = 'SMA-2'",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="CONFLICT")
    assert record.comparison["outcome_status"] == "CONFLICT"
    assert "SMA-1" in str(record.deterministic_evidence["assigned_values"])


def test_llm_only_claim_is_flagged():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
    }
    synthesis = _make_synthesis([
        _rule(
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["STATUS"],
            condition="DPD >= 30",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="LLM_ONLY")
    assert record.confidence == "low"


def test_deterministic_only_fact_is_reported_when_missing_from_synthesis():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
    }
    synthesis = _make_synthesis([])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="coverage", status="DETERMINISTIC_ONLY")
    assert record.deterministic_evidence["table"] == "ACCOUNT"
    assert result.summary["deterministic_only"] == 1
    assert result.review_required is False


@pytest.mark.parametrize("dialect", ["UNKNOWN", "AMBIGUOUS", "UNSUPPORTED"])
def test_unsupported_or_ambiguous_dialect_is_constrained_and_reviewable(dialect):
    ingestion = _make_ingestion(dialect=dialect)
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
    }
    synthesis = _make_synthesis([
        _rule(
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["STATUS"],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="tables_written", status="MATCHED")
    assert record.confidence == "low"
    assert result.unsupported_dialect is True
    assert result.review_required is True


def test_report_formatter_surfaces_reconciliation_summary():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "MERGE", columns=["STATUS"])],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_1",
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["STATUS"],
        )
    ])
    reconciliation = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    ).to_dict()
    merged["reconciliation"] = reconciliation
    synthesis.data["reconciliation"] = reconciliation

    report = ReportFormatterAgent().format(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert "## Reconciliation Summary" in report
    assert "Conflicts" in report


def test_condition_contradiction_forces_review_required():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["SMA_STATUS"], filter_condition="DPD >= 30")],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["SMA_STATUS"], filter_condition="DPD >= 30")],
        "statement_provenance": [
            {"statement_id": "stmt_1", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_1",
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["SMA_STATUS"],
            condition="DPD > 30",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert any(item.type == "condition_conflict" for item in result.contradictions)
    assert result.quality["status"] == "REVIEW_REQUIRED"
    assert result.review_required is True


def test_outcome_contradiction_is_detected():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                columns=["SMA_STATUS"],
                assigned_values=[{"column": "SMA_STATUS", "expression": "'SMA-1'"}],
            )
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                columns=["SMA_STATUS"],
                assigned_values=[{"column": "SMA_STATUS", "expression": "'SMA-1'"}],
            )
        ],
        "statement_provenance": [
            {"statement_id": "stmt_1", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_1",
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["SMA_STATUS"],
            action="SMA_STATUS = 'SMA-2'",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert any(item.type == "outcome_conflict" for item in result.contradictions)
    assert result.quality["status"] == "REVIEW_REQUIRED"


def test_table_operation_contradiction_is_detected():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"], chunk_id="chunk_1", statement_id="stmt_1")],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "MERGE", columns=["STATUS"], chunk_id="chunk_1", statement_id="stmt_1")],
        "statement_provenance": [
            {"statement_id": "stmt_1", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert any(item.type == "operation_conflict" for item in result.contradictions)
    assert any(record.status == "CONFLICT" for record in result.records if record.kind == "tables_written")


def test_rule_vs_rule_conflict_across_chunks_is_detected():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "statement_provenance": [
            {"statement_id": "stmt_a", "parse_status": "parsed"},
            {"statement_id": "stmt_b", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_a",
            source_chunks=["chunk_a"],
            technical_references=["stmt_a"],
            fields_affected=["SMA_STATUS"],
            condition="DPD >= 30",
            action="SMA_STATUS = 'SMA-1'",
        ),
        _rule(
            rule_id="rule_b",
            source_chunks=["chunk_b"],
            technical_references=["stmt_b"],
            fields_affected=["SMA_STATUS"],
            condition="DPD >= 30",
            action="SMA_STATUS = 'SMA-2'",
        ),
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert any(item.type == "rule_vs_rule_conflict" for item in result.contradictions)
    assert result.review_required is True


def test_duplicate_rule_without_contradiction_is_grouped():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "statement_provenance": [
            {"statement_id": "stmt_a", "parse_status": "parsed"},
            {"statement_id": "stmt_b", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_a",
            source_chunks=["chunk_a"],
            technical_references=["stmt_a"],
            fields_affected=["SMA_STATUS"],
            condition="DPD >= 30",
            action="SMA_STATUS = 'SMA-1'",
        ),
        _rule(
            rule_id="rule_b",
            source_chunks=["chunk_b"],
            technical_references=["stmt_b"],
            fields_affected=["SMA_STATUS"],
            condition="DPD >= 30",
            action="SMA_STATUS = 'SMA-1'",
        ),
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert not any(item.type == "rule_vs_rule_conflict" for item in result.contradictions)
    assert result.duplicate_rule_groups


def test_coverage_metrics_are_calculated():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"], chunk_id="chunk_1", statement_id="stmt_1")],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"], chunk_id="chunk_1", statement_id="stmt_1")],
        "statement_provenance": [
            {"statement_id": "stmt_1", "parse_status": "parsed"},
            {"statement_id": "stmt_2", "parse_status": "parse_failed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_1",
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["STATUS"],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert result.coverage["total_statements"] == 2
    assert result.coverage["parsed_statements"] == 1
    assert result.coverage["unsupported_unparsed_statements"] == 1
    assert result.coverage["synthesized_rules"] == 1
    assert result.coverage["rules_with_deterministic_support"] == 1
    assert result.coverage["statement_parse_success_pct"] == 50.0
    assert result.coverage["rule_grounding_pct"] == 100.0


def test_zero_denominator_handling_does_not_fabricate_percentages():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "statement_provenance": [],
    }
    synthesis = _make_synthesis([])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert "statement_parse_success_pct" not in result.coverage
    assert "rule_grounding_pct" not in result.coverage
    assert result.quality["status"] == "LOW_CONFIDENCE"


@pytest.mark.parametrize("dialect", ["UNKNOWN", "AMBIGUOUS"])
def test_unsupported_or_ambiguous_dialect_quality_is_low_confidence(dialect):
    ingestion = _make_ingestion(dialect=dialect)
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "statement_provenance": [
            {"statement_id": "stmt_1", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_1",
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["STATUS"],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert result.unsupported_dialect is True
    assert result.quality["status"] in {"LOW_CONFIDENCE", "REVIEW_REQUIRED"}
    assert result.quality["review_required"] is True


def test_llm_only_rule_reduces_quality_score():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "statement_provenance": [
            {"statement_id": "stmt_1", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_1",
            source_chunks=["chunk_1"],
            technical_references=["stmt_1"],
            fields_affected=["STATUS"],
            condition="DPD >= 30",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert result.quality["factors"]["llm_only_rules"] == 1
    assert result.quality["score"] < 100
    assert result.quality["status"] in {"REVIEW_REQUIRED", "LOW_CONFIDENCE"}
