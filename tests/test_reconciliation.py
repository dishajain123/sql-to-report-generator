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
from src.validation.reconciliation import (
    ContradictionFinding,
    ReconciliationRecord,
    _build_quality_assessment,
    _gather_contradictions,
    reconcile_deterministic_evidence,
)


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


def _evidence_span(*, chunk_id="chunk_1", statement_id="stmt_1", parse_status="parsed", evidence_type="CONDITION"):
    return {
        "source_file": "demo.sql",
        "char_start": 1,
        "char_end": 10,
        "line_start": 1,
        "line_end": 2,
        "chunk_id": chunk_id,
        "statement_id": statement_id,
        "evidence_type": evidence_type,
        "source_location_status": "available",
        "statement_parse_status": parse_status,
    }


def _rule(
    *,
    rule_id="rule_1",
    rule_name="Rule 1",
    source_chunks=None,
    source_statement_ids=None,
    technical_references=None,
    fields_affected=None,
    condition=None,
    action=None,
    decision_logic_rows=None,
    **extra,
):
    rule = {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "source_chunks": list(source_chunks or []),
        "source_statement_ids": list(source_statement_ids or []),
        "technical_references": list(technical_references or []),
        "fields_affected": list(fields_affected or []),
        "condition": condition,
        "action": action,
        "decision_logic_rows": list(decision_logic_rows or []),
        "validation_status": "verified",
        "rule_type": "explicit",
        "confidence": "medium",
    }
    rule.update(extra)
    return rule


def _find_record(result, *, kind=None, status=None):
    for record in result.records:
        if kind is not None and record.kind != kind:
            continue
        if status is not None and record.status != status:
            continue
        return record
    raise AssertionError(f"No record found for kind={kind!r} status={status!r}")


def _find_contradiction(result, *, classification=None, ctype=None, severity=None):
    for item in result.contradictions:
        if classification is not None and item.classification != classification:
            continue
        if ctype is not None and item.type != ctype:
            continue
        if severity is not None and item.severity != severity:
            continue
        return item
    raise AssertionError(
        f"No contradiction found for classification={classification!r} type={ctype!r} severity={severity!r}"
    )


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


def test_provenance_matches_raw_chunk_ids_even_when_display_labels_include_kind():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", chunk_id="chunk_1", statement_id="stmt_1", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", chunk_id="chunk_1", statement_id="stmt_1", columns=["STATUS"])],
    }
    synthesis = _make_synthesis([
        _rule(
            source_chunks=["chunk_1:main_body"],
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

    record = _find_record(result, kind="rule", status="MATCHED")
    assert record.chunk_id == "chunk_1"
    assert record.statement_id == "stmt_1"
    assert record.deterministic_evidence["source_chunks"] == ["chunk_1"]


def test_evidence_spans_can_ground_when_text_is_only_paraphrased():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", chunk_id="chunk_1", statement_id="stmt_1", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", chunk_id="chunk_1", statement_id="stmt_1", columns=["STATUS"])],
    }
    synthesis = _make_synthesis([
        {
            "rule_id": "rule_1",
            "rule_name": "Rule 1",
            "source_chunks": ["chunk_1:main_body"],
            "source_chunk_ids": ["chunk_1"],
            "source_statement_ids": ["stmt_1"],
            "technical_references": ["stmt_1"],
            "fields_affected": ["STATUS"],
            "condition": "STATUS is adjusted for the branch",
            "action": "STATUS is adjusted for the branch",
            "decision_logic_rows": [],
            "validation_status": "verified",
            "rule_type": "explicit",
            "confidence": "medium",
            "evidence_spans": [_evidence_span()],
            "source_evidence": ["branch summary, not the exact SQL text"],
        }
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="MATCHED")
    assert record.deterministic_evidence["statement_ids"] == ["stmt_1"]
    assert record.comparison["field_status"] == "MATCHED"


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
    contradiction = _find_contradiction(result, classification="TECHNICAL_PROVENANCE_NOISE")
    assert record.comparison["table_status"] == "CONFLICT"
    assert record.deterministic_evidence["operation"] == "UPDATE"
    assert record.llm_claim["operation"] == "MERGE"
    assert contradiction.business_relevant is False
    assert contradiction.counted_for_review is False


def test_technical_vs_business_overlap_is_classified_from_explicit_cleanup_semantics():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [
            _table_row(
                "PRO.ACCOUNTCAL",
                "UPDATE",
                columns=["SMA_CLASS", "SMA_REASON", "SMA_DT", "FLGSMA"],
                filter_condition="FinalAssetClassAlt_Key = 1",
                assigned_values=[{"column": "SMA_CLASS", "expression": "'STD'"}],
            )
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            _table_row(
                "PRO.ACCOUNTCAL",
                "UPDATE",
                columns=["SMA_CLASS", "SMA_REASON", "SMA_DT", "FLGSMA"],
                filter_condition="FinalAssetClassAlt_Key = 1",
                assigned_values=[{"column": "SMA_CLASS", "expression": "'STD'"}],
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
            fields_affected=["SMA_CLASS", "SMA_REASON", "SMA_DT", "FLGSMA"],
            condition="FinalAssetClassAlt_Key = 1",
            action="Clear prior SMA fields and set SMA_CLASS = 'STD'",
            decision_logic_rows=[
                {"condition": "FinalAssetClassAlt_Key = 1", "outcome": "Clear prior SMA fields and set SMA_CLASS = 'STD'"},
            ],
            business_meaning="Technical cleanup before recalculation.",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    contradiction = _find_contradiction(result, classification="TECHNICAL_VS_BUSINESS_OVERLAP", ctype="outcome_conflict")
    assert contradiction.business_relevant is False
    assert contradiction.counted_for_review is False


def test_insufficient_evidence_remains_review_relevant():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [
            _table_row("ACCOUNT", "UPDATE", columns=["STATUS"], filter_condition="STATUS = 'A'", assigned_values=[{"column": "STATUS", "expression": "'A'"}])
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            _table_row("ACCOUNT", "UPDATE", columns=["STATUS"], filter_condition="STATUS = 'A'", assigned_values=[{"column": "STATUS", "expression": "'A'"}])
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
            fields_affected=["STATUS"],
            condition="DPD > 30",
            action="STATUS = 'SMA-2'",
            validation_status="insufficient_evidence",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    contradiction = _find_contradiction(result, classification="INSUFFICIENT_EVIDENCE")
    assert contradiction.business_relevant is True
    assert contradiction.counted_for_review is True


def test_business_review_required_items_are_deduped_by_underlying_issue():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                columns=["SMA_STATUS"],
                filter_condition="DPD >= 30",
                assigned_values=[{"column": "SMA_STATUS", "expression": "'SMA-1'"}],
            )
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                columns=["SMA_STATUS"],
                filter_condition="DPD >= 30",
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
            condition="DPD > 30",
            action="SMA_STATUS = 'SMA-2'",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    # Raw review-required accounting still reflects the legacy aggregate,
    # while the new internal summary dedupes the underlying issue.
    assert result.review_summary["review_item_count"] == 1
    assert result.review_summary["business_review_required_items"] == 1
    assert result.coverage["business_review_required_items"] == 1
    assert result.coverage["review_required_items"] >= 2


def test_raw_contradiction_evidence_is_preserved():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "MERGE", columns=["STATUS"])],
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

    contradiction = _find_contradiction(result, classification="TECHNICAL_PROVENANCE_NOISE", ctype="operation_conflict")
    assert contradiction.evidence["record"]["reconciliation_id"]
    assert contradiction.evidence["record"]["kind"] == "tables_written"


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
    verification = ReportFormatterAgent().format_verification(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert "## Reconciliation Summary" in verification
    assert "Conflicts" in verification


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

    contradiction = _find_contradiction(result, classification="GENUINE_BUSINESS_CONTRADICTION", ctype="condition_conflict")
    assert any(item.type == "condition_conflict" for item in result.contradictions)
    assert contradiction.business_relevant is True
    assert contradiction.counted_for_review is True
    assert result.quality["status"] == "REVIEW_REQUIRED"
    assert result.review_required is True


def test_disjoint_threshold_branches_are_not_auto_contradictions():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "statement_provenance": [
            {"statement_id": "stmt_low", "parse_status": "parsed"},
            {"statement_id": "stmt_high", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_low",
            source_chunks=["chunk_low"],
            technical_references=["stmt_low"],
            fields_affected=["SMA_STATUS"],
            condition="DPD < 30",
            action="SMA_STATUS = 'SMA-0'",
        ),
        _rule(
            rule_id="rule_high",
            source_chunks=["chunk_high"],
            technical_references=["stmt_high"],
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


def test_overlapping_threshold_branches_still_conflict():
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
            decision_logic_rows=[
                {"condition": "DPD >= 30", "outcome": "SMA_STATUS = 'SMA-1'"},
                {"condition": "DPD > 30", "outcome": "SMA_STATUS = 'SMA-2'"},
            ],
            tie_priority_handling=["Explicit ordered thresholds"],
        ),
        _rule(
            rule_id="rule_b",
            source_chunks=["chunk_b"],
            technical_references=["stmt_b"],
            fields_affected=["SMA_STATUS"],
            condition="DPD > 30",
            action="SMA_STATUS = 'SMA-2'",
        ),
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    contradiction = _find_contradiction(result, classification="VALID_ORDERED_BRANCH", ctype="rule_vs_rule_conflict")
    assert contradiction.business_relevant is False
    assert contradiction.counted_for_review is False
    assert any(item.type == "rule_vs_rule_conflict" for item in result.contradictions)


def test_comment_only_evidence_does_not_ground_executable_rule():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", chunk_id="chunk_1", statement_id="stmt_1", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", chunk_id="chunk_1", statement_id="stmt_1", columns=["STATUS"])],
    }
    synthesis = _make_synthesis([
        {
            "rule_id": "rule_1",
            "rule_name": "Rule 1",
            "source_chunks": ["chunk_1:comment_block"],
            "source_chunk_ids": ["chunk_1"],
            "source_statement_ids": ["stmt_1"],
            "technical_references": ["stmt_1"],
            "fields_affected": ["STATUS"],
            "condition": "STATUS is mentioned in comments only",
            "action": "STATUS is mentioned in comments only",
            "decision_logic_rows": [],
            "validation_status": "verified",
            "rule_type": "explicit",
            "confidence": "medium",
            "evidence_spans": [_evidence_span(parse_status="parse_failed", evidence_type="COMMENT")],
            "source_evidence": ["comment-only guidance"],
        }
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="LLM_ONLY")
    assert record.deterministic_evidence == {}


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


def test_technical_predicate_formatting_difference_is_not_a_contradiction():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [
            _table_row(
                "SYSDAYMATRIX",
                "READ",
                chunk_id="chunk_1",
                statement_id="stmt_1",
                columns=["DATE"],
                filter_condition="TIMEKEY=@TIMEKEY)",
            )
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            _table_row(
                "SYSDAYMATRIX",
                "READ",
                chunk_id="chunk_1",
                statement_id="stmt_1",
                columns=["DATE"],
                filter_condition="TIMEKEY=@TIMEKEY",
            )
        ],
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

    assert not any(item.type == "condition_conflict" for item in result.contradictions)
    assert any(record.status == "MATCHED" for record in result.records if record.kind == "tables_written")


def test_tables_read_column_projection_differences_do_not_create_business_contradictions():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [
            _table_row(
                "ACCOUNT",
                "READ",
                chunk_id="chunk_1",
                statement_id="stmt_1",
                columns=["ACCOUNT_ID", "BALANCE", "STATUS"],
                filter_condition="STATUS = 'A'",
            )
        ],
        "tables_written": [],
        "llm_tables_read": [
            _table_row(
                "ACCOUNT",
                "READ",
                chunk_id="chunk_1",
                statement_id="stmt_1",
                columns=["STATUS"],
                filter_condition="STATUS = 'A'",
            )
        ],
        "llm_tables_written": [],
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

    assert not any(item.type == "field_conflict" for item in result.contradictions)
    assert any(record.status == "MATCHED" for record in result.records if record.kind == "tables_read")


def test_rule_candidate_rows_ignore_unrelated_rows_from_same_chunk():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [
            _table_row(
                "DPD",
                "UPDATE",
                chunk_id="chunk_1",
                statement_id="stmt_dpd",
                columns=["DPD_IntService"],
                filter_condition="DPD_IntService < 0",
                assigned_values=[{"column": "DPD_IntService", "expression": "0"}],
            ),
            _table_row(
                "PRO.ACCOUNTCAL",
                "UPDATE",
                chunk_id="chunk_1",
                statement_id="stmt_other",
                columns=["SMA_CLASS", "SMA_REASON", "SMA_DT", "FLGSMA"],
                filter_condition="FinalAssetClassAlt_Key = 1",
                assigned_values=[{"column": "SMA_CLASS", "expression": "NULL"}],
            ),
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            _table_row(
                "DPD",
                "UPDATE",
                chunk_id="chunk_1",
                statement_id="stmt_dpd",
                columns=["DPD_IntService"],
                filter_condition="DPD_IntService < 0",
                assigned_values=[{"column": "DPD_IntService", "expression": "0"}],
            ),
            _table_row(
                "PRO.ACCOUNTCAL",
                "UPDATE",
                chunk_id="chunk_1",
                statement_id="stmt_other",
                columns=["SMA_CLASS", "SMA_REASON", "SMA_DT", "FLGSMA"],
                filter_condition="FinalAssetClassAlt_Key = 1",
                assigned_values=[{"column": "SMA_CLASS", "expression": "NULL"}],
            ),
        ],
        "statement_provenance": [
            {"statement_id": "stmt_dpd", "parse_status": "parsed"},
            {"statement_id": "stmt_other", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_dpd",
            source_chunks=["chunk_1"],
            technical_references=["stmt_dpd"],
            fields_affected=["DPD_IntService"],
            condition="DPD_IntService < 0",
            action="DPD_IntService = 0",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="MATCHED")
    assert record.rule_id == "rule_dpd"
    assert not any(item.type == "rule_vs_rule_conflict" for item in result.contradictions)


def test_rule_candidate_rows_prefer_statement_identity_over_shared_chunk():
    ingestion = _make_ingestion()
    merged = {
        "tables_read": [],
        "tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                chunk_id="chunk_1",
                statement_id="stmt_chunk",
                columns=["STATUS"],
                filter_condition="STATUS = 'N'",
                assigned_values=[{"column": "STATUS", "expression": "'N'"}],
            ),
            _table_row(
                "ACCOUNT",
                "UPDATE",
                chunk_id="chunk_2",
                statement_id="stmt_match",
                columns=["STATUS"],
                filter_condition="STATUS = 'B'",
                assigned_values=[{"column": "STATUS", "expression": "'B'"}],
            ),
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            _table_row(
                "ACCOUNT",
                "UPDATE",
                chunk_id="chunk_1",
                statement_id="stmt_match",
                columns=["STATUS"],
                filter_condition="STATUS = 'Y'",
                assigned_values=[{"column": "STATUS", "expression": "'Y'"}],
            )
        ],
        "statement_provenance": [
            {"statement_id": "stmt_chunk", "parse_status": "parsed"},
            {"statement_id": "stmt_match", "parse_status": "parsed"},
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            rule_id="rule_stmt_match",
            source_chunks=["chunk_1:main_body"],
            source_statement_ids=["stmt_match"],
            technical_references=["stmt_match"],
            fields_affected=["STATUS"],
            condition="STATUS = 'Y'",
            action="STATUS = 'Y'",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="CONFLICT")
    assert record.statement_id == "stmt_match"
    assert record.deterministic_evidence["statement_ids"] == ["stmt_match"]
    assert record.deterministic_evidence["filters"] == ["STATUS = 'B'"]


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


def test_duplicate_contradiction_ids_are_deduplicated():
    records = [
        ReconciliationRecord(
            reconciliation_id="recon_1",
            kind="tables_written",
            status="CONFLICT",
            object_id="obj_1",
            chunk_id="chunk_1",
            statement_id="stmt_1",
            llm_claim={
                "table": "ACCOUNT",
                "operation": "MERGE",
            },
            deterministic_evidence={
                "table": "ACCOUNT",
                "operation": "UPDATE",
                "filter_condition": "STATUS = 'A'",
            },
            comparison={"table_status": "CONFLICT"},
        ),
        ReconciliationRecord(
            reconciliation_id="recon_2",
            kind="tables_written",
            status="CONFLICT",
            object_id="obj_1",
            chunk_id="chunk_1",
            statement_id="stmt_1",
            llm_claim={
                "table": "ACCOUNT",
                "operation": "MERGE",
            },
            deterministic_evidence={
                "table": "ACCOUNT",
                "operation": "UPDATE",
                "filter_condition": "STATUS = 'B'",
            },
            comparison={"table_status": "CONFLICT"},
        ),
    ]

    contradictions, _ = _gather_contradictions(object_id="obj_1", rules=[], records=records)

    contradiction_ids = [item.contradiction_id for item in contradictions]
    assert len(contradiction_ids) == len(set(contradiction_ids))
    assert len(contradictions) == 1


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


def test_quality_score_does_not_double_count_llm_only_and_contradiction_review_items():
    """Regression test for a scoring bug: review_required_items previously folded in
    both LLM_ONLY records and review-required contradictions, which were *also* each
    penalized separately (llm_only_rules bucket, and the HIGH/MEDIUM/LOW contradiction
    severity buckets). That double-penalty could drive the score to 0 even when the
    grounding coverage was high, purely from the same handful of findings being
    subtracted twice. This test locks in that each finding is only charged once."""

    records = [ReconciliationRecord(reconciliation_id="r1", kind="rule", status="MATCHED", object_id="obj_1") for _ in range(11)]
    records += [ReconciliationRecord(reconciliation_id="r2", kind="rule", status="LLM_ONLY", object_id="obj_1") for _ in range(2)]

    contradictions = [
        ContradictionFinding(contradiction_id=f"c{i}", type="source", severity="MEDIUM", object_id="obj_1", review_required=True)
        for i in range(3)
    ]

    coverage_without_dedup = {
        "llm_only_rules": 2,
        "deterministic_only_facts": 0,
        # Old (buggy) behavior: review_required_items double-counts the 2 LLM_ONLY
        # records and the 3 review-required contradictions that already have their
        # own dedicated penalty buckets below.
        "review_required_items": 2 + 3,
        "business_review_required_items": 2 + 3,
        "statement_parse_success_pct": 100.0,
        "rule_grounding_pct": 84.6,
        "total_statements": 13,
        "synthesized_rules": 13,
    }
    coverage_with_dedup = dict(coverage_without_dedup)
    # New behavior: unresolved_for_scoring excludes items already penalized via
    # llm_only_rules / contradiction-severity buckets.
    coverage_with_dedup["unresolved_for_scoring"] = 0

    double_counted = _build_quality_assessment(
        coverage=coverage_without_dedup, contradictions=contradictions, unsupported_dialect=False, records=records
    )
    deduplicated = _build_quality_assessment(
        coverage=coverage_with_dedup, contradictions=contradictions, unsupported_dialect=False, records=records
    )

    assert deduplicated["score"] > double_counted["score"], (
        "Deduplicated scoring should never score lower than the double-counted formula "
        "for the same underlying findings."
    )
    # The review flag must still correctly reflect that real issues exist — dedup must
    # not hide genuine problems, only stop charging the score for them twice.
    assert deduplicated["status"] == "REVIEW_REQUIRED"

# --------------------------------------------------------------------------
# Regression tests for decision-chain grounding (see
# _decision_chain_rows / _collect_deterministic_rows). Root cause: a rule
# whose deterministic evidence is a CASE/IF branch condition (not a
# table-level WHERE predicate) previously had no comparable deterministic
# row to match against at all, because _collect_deterministic_rows only
# ever looked at tables_read/tables_written. This is what made every
# condition-based rule in objects like SMA_Stage_Marking_Simple come back
# LLM_ONLY regardless of whether the source actually supported it.
# --------------------------------------------------------------------------

def _decision_chain(subject, branches):
    return {"chain_type": "CASE_EXPRESSION", "subject": subject, "branches": branches}


def test_decision_chain_branch_grounds_rule_with_no_table_evidence():
    """Test A (from the investigation brief): deterministic evidence for a
    CASE-branch condition must ground the matching LLM rule, even though
    there is zero tables_read/tables_written evidence for it."""
    ingestion = _make_ingestion(dialect="TSQL")
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "decision_chains": [
            _decision_chain(
                "A.OverdueDays",
                [
                    {"branch_condition": "A.OverdueDays BETWEEN 1 AND 30", "assignments": [{"field": "SmaStage", "value": "'SMA_0'"}]},
                ],
            )
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            fields_affected=["SmaStage"],
            condition="A.OverdueDays BETWEEN 1 AND 30",
            action="SmaStage = 'SMA_0'",
            source_evidence=["A.OverdueDays BETWEEN 1 AND 30"],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="MATCHED")
    assert record.status not in {"LLM_ONLY", "UNRESOLVED"}
    assert any("smastage" in c.lower() for c in record.deterministic_evidence["target_columns"])


def test_decision_chain_grounding_does_not_require_provenance_metadata():
    """Test B: decision_chains rows carry no chunk/statement identity
    (guardrail normalization strips it), so grounding here necessarily
    happens without that metadata. Confirms this does not, on its own,
    push the rule into a worse status than MATCHED."""
    ingestion = _make_ingestion(dialect="TSQL")
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "decision_chains": [
            _decision_chain(
                "A.FacilityType",
                [
                    {"branch_condition": "A.FacilityType IN ('CC', 'OD')", "assignments": [{"field": "SmaReason", "value": "'CASH CREDIT / OVERDRAFT OVERDUE'"}]},
                    {"branch_condition": "ELSE", "assignments": [{"field": "SmaReason", "value": "'OTHER FACILITY OVERDUE'"}]},
                ],
            )
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            fields_affected=["SmaReason"],
            condition="A.FacilityType IN ('CC', 'OD')",
            action="SmaReason = 'CASH CREDIT / OVERDRAFT OVERDUE'",
            source_evidence=["A.FacilityType IN ('CC', 'OD')"],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="MATCHED")
    assert record.status == "MATCHED"


def test_decision_chain_contradicting_llm_claim_remains_a_conflict():
    """Test C: a genuine contradiction between the LLM's claimed outcome
    and the deterministic branch outcome must still be reported as a
    CONFLICT - grounding decision_chains must never weaken real conflict
    detection."""
    ingestion = _make_ingestion(dialect="TSQL")
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "decision_chains": [
            _decision_chain(
                "A.OverdueDays",
                [
                    {"branch_condition": "A.OverdueDays BETWEEN 1 AND 30", "assignments": [{"field": "SmaStage", "value": "'SMA_0'"}]},
                    {"branch_condition": "ELSE", "assignments": [{"field": "SmaStage", "value": "NULL"}]},
                ],
            )
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            fields_affected=["SmaStage"],
            condition="A.OverdueDays BETWEEN 1 AND 30",
            # Deliberately wrong outcome vs. the deterministic branch (which says 'SMA_0').
            action="SmaStage = 'SMA-1'",
            source_evidence=["A.OverdueDays BETWEEN 1 AND 30"],
            decision_logic_rows=[
                {"condition": "A.OverdueDays BETWEEN 1 AND 30", "outcome": "'SMA-1'"},
            ],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="CONFLICT")
    assert record.comparison["outcome_status"] == "CONFLICT"


def test_rule_with_genuinely_no_deterministic_evidence_stays_llm_only():
    """Test D: a rule with no matching decision_chains, no table evidence,
    and no citable source_evidence must remain LLM_ONLY - the fix must not
    cause everything to be marked grounded regardless of actual evidence."""
    ingestion = _make_ingestion(dialect="TSQL")
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "decision_chains": [],
    }
    synthesis = _make_synthesis([
        _rule(
            fields_affected=["SomeUnrelatedField"],
            condition="X = 1",
            action="SomeUnrelatedField = 'Y'",
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="LLM_ONLY")
    assert record.status == "LLM_ONLY"


def test_decision_chain_rows_never_pollute_table_level_reconciliation():
    """Decision-chain-derived rows are tagged _section='decision_chains'
    and must never be picked up by the tables_read/tables_written
    comparison loop (which filters deterministic_rows by _section) -
    only by rule reconciliation."""
    ingestion = _make_ingestion(dialect="TSQL")
    merged = {
        "tables_read": [],
        "tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "llm_tables_read": [],
        "llm_tables_written": [_table_row("ACCOUNT", "UPDATE", columns=["STATUS"])],
        "decision_chains": [
            _decision_chain(
                "X",
                [
                    {"branch_condition": "X > 1", "assignments": [{"field": "Y", "value": "1"}]},
                    {"branch_condition": "ELSE", "assignments": [{"field": "Y", "value": "0"}]},
                ],
            )
        ],
    }
    synthesis = _make_synthesis([
        _rule(
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

    table_records = [r for r in result.records if r.kind == "tables_written"]
    assert len(table_records) == 1
    assert table_records[0].deterministic_evidence.get("table") == "ACCOUNT"


def test_decision_chain_sibling_branches_ground_via_partial_citation():
    """The real bug report's exact shape: the rule's source_evidence cites
    only ONE branch condition, but its decision_logic_rows correctly
    describes the full ladder (including ELSE). The uncited sibling
    branches must still be pulled in via _expand_decision_chain_siblings,
    since they are the same structural decision table, not separate
    uncited claims."""
    ingestion = _make_ingestion(dialect="TSQL")
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "decision_chains": [
            _decision_chain(
                "A.OverdueDays",
                [
                    {"branch_condition": "A.OverdueDays BETWEEN 1 AND 30", "assignments": [{"field": "SmaStage", "value": "'SMA_0'"}]},
                    {"branch_condition": "A.OverdueDays BETWEEN 31 AND 60", "assignments": [{"field": "SmaStage", "value": "'SMA_1'"}]},
                    {"branch_condition": "ELSE", "assignments": [{"field": "SmaStage", "value": "NULL"}]},
                ],
            )
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            fields_affected=["SmaStage"],
            condition=None,
            action=None,
            # Only ONE branch cited - matches the real bug report exactly.
            source_evidence=["A.OverdueDays BETWEEN 1 AND 30"],
            decision_logic_rows=[
                {"condition": "A.OverdueDays BETWEEN 1 AND 30", "outcome": "'SMA_0'"},
                {"condition": "A.OverdueDays BETWEEN 31 AND 60", "outcome": "'SMA_1'"},
                {"condition": "ELSE", "outcome": "NULL"},
            ],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="MATCHED")
    assert record.comparison["condition_status"] != "CONFLICT"
    assert record.comparison["outcome_status"] != "CONFLICT"
    assert "else" in record.deterministic_evidence["filters"][0].lower() or \
        any("else" in f.lower() for f in record.deterministic_evidence["filters"])


def test_decision_chain_sibling_expansion_does_not_leak_across_chains():
    """Sibling expansion must stay within the same chain - a candidate
    from chain 0 must never pull in branches belonging to a completely
    different chain 1, even if both assign to fields with the same name
    coincidentally."""
    ingestion = _make_ingestion(dialect="TSQL")
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "decision_chains": [
            _decision_chain(
                "A.OverdueDays",
                [
                    {"branch_condition": "A.OverdueDays BETWEEN 1 AND 30", "assignments": [{"field": "SmaStage", "value": "'SMA_0'"}]},
                    {"branch_condition": "ELSE", "assignments": [{"field": "SmaStage", "value": "NULL"}]},
                ],
            ),
            _decision_chain(
                "B.SomethingElse",
                [
                    {"branch_condition": "B.SomethingElse = 1", "assignments": [{"field": "SmaStage", "value": "'UNRELATED'"}]},
                    {"branch_condition": "ELSE", "assignments": [{"field": "SmaStage", "value": "'DEFAULT'"}]},
                ],
            ),
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            fields_affected=["SmaStage"],
            condition=None,
            action=None,
            source_evidence=["A.OverdueDays BETWEEN 1 AND 30"],
            decision_logic_rows=[
                {"condition": "A.OverdueDays BETWEEN 1 AND 30", "outcome": "'SMA_0'"},
                {"condition": "ELSE", "outcome": "NULL"},
            ],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="MATCHED")
    assert "UNRELATED" not in record.deterministic_evidence["assigned_values"]
    assert "DEFAULT" not in record.deterministic_evidence["assigned_values"]
    """Realistic production shape (matches the actual SMA_Stage_Marking_Simple
    report): one rule whose decision_logic_rows cite an entire multi-branch
    decision table, all branches for the same field. Every branch's
    condition/outcome must be found in the deterministic evidence with no
    spurious conflict, since the rule and the source agree completely."""
    ingestion = _make_ingestion(dialect="TSQL")
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "decision_chains": [
            _decision_chain(
                "A.OverdueDays",
                [
                    {"branch_condition": "A.OverdueDays BETWEEN 1 AND 30", "assignments": [{"field": "SmaStage", "value": "'SMA_0'"}]},
                    {"branch_condition": "A.OverdueDays BETWEEN 31 AND 60", "assignments": [{"field": "SmaStage", "value": "'SMA_1'"}]},
                    {"branch_condition": "ELSE", "assignments": [{"field": "SmaStage", "value": "NULL"}]},
                ],
            )
        ],
    }
    synthesis = _make_synthesis([
        _rule(
            fields_affected=["SmaStage"],
            condition=None,
            action=None,
            source_evidence=[
                "A.OverdueDays BETWEEN 1 AND 30",
                "A.OverdueDays BETWEEN 31 AND 60",
            ],
            decision_logic_rows=[
                {"condition": "A.OverdueDays BETWEEN 1 AND 30", "outcome": "'SMA_0'"},
                {"condition": "A.OverdueDays BETWEEN 31 AND 60", "outcome": "'SMA_1'"},
                {"condition": "ELSE", "outcome": "NULL"},
            ],
        )
    ])

    result = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    record = _find_record(result, kind="rule", status="MATCHED")
    assert record.comparison["outcome_status"] != "CONFLICT"
    assert record.comparison["condition_status"] != "CONFLICT"