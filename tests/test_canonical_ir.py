"""
Focused tests for the canonical business IR adapter layer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.ingestion import CodeChunk, IngestionResult
from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import SynthesisResult
from src.ir.canonical_ir import CanonicalBusinessIR
from src.validation.reconciliation import reconcile_deterministic_evidence


def _ingestion() -> IngestionResult:
    return IngestionResult(
        object_name="demo_proc",
        object_type="PROCEDURE",
        parameters=[],
        raw_code="UPDATE ACCOUNT SET STATUS = 'A' WHERE ID = 1",
        chunks=[CodeChunk(chunk_id="chunk_1", kind="main_body", text="UPDATE ACCOUNT SET STATUS = 'A' WHERE ID = 1")],
        object_id="obj_1",
        dialect="TSQL",
        concrete_dialect="tsql",
        fallback_dialect="tsql",
        source_hash="hash",
        source_filename="demo.sql",
    )


def _merged():
    return {
        "tables_read": [],
        "tables_written": [
            {
                "table": "ACCOUNT",
                "operation": "UPDATE",
                "source_chunk_id": "chunk_1",
                "statement_id": "stmt_1",
                "source_statement_id": "stmt_1",
                "target_columns": ["STATUS"],
                "columns": ["STATUS"],
                "filter_condition": "ID = 1",
                "where_predicate": "ID = 1",
                "assigned_values": [{"column": "STATUS", "expression": "'A'"}],
            }
        ],
        "llm_tables_read": [],
        "llm_tables_written": [
            {
                "table": "ACCOUNT",
                "operation": "UPDATE",
                "source_chunk_id": "chunk_1",
                "statement_id": "stmt_1",
                "source_statement_id": "stmt_1",
                "target_columns": ["STATUS"],
                "columns": ["STATUS"],
                "filter_condition": "ID = 1",
                "where_predicate": "ID = 1",
                "assigned_values": [{"column": "STATUS", "expression": "'A'"}],
            }
        ],
        "chunk_provenance": [
            {
                "chunk_id": "chunk_1",
                "chunk_kind": "main_body",
                "chunk_context": ["main_body"],
                "embedded_sql": [],
                "parse_error": "",
                "guardrail_warnings": [],
                "support_confidence": "high",
                "source_file": "demo.sql",
                "source_char_start": 0,
                "source_char_end": 44,
                "source_line_start": 1,
                "source_line_end": 1,
                "source_location_status": "available",
            }
        ],
        "statement_provenance": [
            {
                "statement_id": "stmt_1",
                "source_chunk_id": "chunk_1",
                "source_chunk_kind": "main_body",
                "statement_index": 1,
                "statement_kind": "UPDATE",
                "source_statement_text": "UPDATE ACCOUNT SET STATUS = 'A' WHERE ID = 1",
                "parse_status": "parsed",
                "parse_error": "",
                "source_file": "demo.sql",
                "source_char_start": 0,
                "source_char_end": 44,
                "source_line_start": 1,
                "source_line_end": 1,
                "source_location_status": "available",
                "evidence_type": "ASSIGNMENT",
            }
        ],
        "ambiguities": [],
    }


def _synthesis():
    return SynthesisResult(
        data={
            "purpose_summary": "Demo",
            "step_by_step_flow": [],
            "business_rules": [
                {
                    "rule_id": "rule_1",
                    "rule_type": "explicit",
                    "condition": "ID = 1",
                    "action": "Set STATUS to A",
                    "output_field": "STATUS",
                    "fields_affected": ["STATUS"],
                    "confidence": "high",
                    "source_evidence": ["ID = 1"],
                    "source_chunks": ["chunk_1"],
                    "technical_references": ["tables_written[0]"],
                    "evidence_spans": [
                        {
                            "source_file": "demo.sql",
                            "line_start": 1,
                            "line_end": 1,
                            "chunk_id": "chunk_1",
                            "statement_id": "stmt_1",
                            "evidence_type": "CONDITION",
                        }
                    ],
                    "dependencies": [],
                    "ambiguities": [],
                }
            ],
            "calculations": [],
            "exception_handling_summary": "",
            "ambiguities": [],
        }
    )


def test_canonical_ir_serializes_and_distinguishes_fact_types():
    ingestion = _ingestion()
    merged = _merged()
    synthesis = _synthesis()
    reconciliation = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )
    ir = CanonicalBusinessIR.from_pipeline(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        reconciliation=reconciliation,
    )

    payload = ir.to_dict()
    json.dumps(payload)
    assert payload["table_operations"][0]["origin"] == "DETERMINISTIC_FACT"
    assert payload["business_rules"][0]["origin"] == "LLM_INTERPRETATION"
    assert payload["business_rules"][0]["evidence_spans"][0]["statement_id"] == "stmt_1"
    assert payload["reconciliation"]["status_counts"]


def test_report_formatter_accepts_canonical_ir():
    ingestion = _ingestion()
    merged = _merged()
    synthesis = _synthesis()
    reconciliation = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )
    ir = CanonicalBusinessIR.from_pipeline(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        reconciliation=reconciliation,
    )

    report = ReportFormatterAgent().format(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        canonical_ir=ir,
    )
    verification = ReportFormatterAgent().format_verification(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        canonical_ir=ir,
    )
    assert "## Business Rules" in report
    assert "## Source Traceability" in verification
    assert "STATUS" in report


def test_business_report_findings_preserves_merged_and_synthesis_ambiguities():
    ingestion = _ingestion()
    merged = _merged()
    merged["ambiguities"] = [
        "Automatic extraction for this chunk returned malformed JSON and could not be parsed; this chunk needs manual review.",
    ]
    merged["chunk_provenance"].append(
        {
            "chunk_id": "01_nested_block",
            "chunk_kind": "nested_block",
            "chunk_context": ["main_body", "nested_block"],
            "embedded_sql": [],
            "parse_error": "malformed json",
            "guardrail_warnings": [],
            "support_confidence": "low",
            "source_file": "demo.sql",
            "source_char_start": 0,
            "source_char_end": 44,
            "source_line_start": 1,
            "source_line_end": 1,
            "source_location_status": "available",
        }
    )
    synthesis = _synthesis()
    synthesis.data["ambiguities"] = [
        "Automatic extraction for some chunks returned malformed JSON and needs manual review."
    ]
    reconciliation = reconcile_deterministic_evidence(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )
    ir = CanonicalBusinessIR.from_pipeline(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        reconciliation=reconciliation,
    )

    report = ReportFormatterAgent().format(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        canonical_ir=ir,
    )

    findings_section = report.split("## Findings / Needs Review", 1)[1]
    assert "Automatic extraction for this chunk returned malformed JSON and could not be parsed; this chunk needs manual review." in findings_section
    assert "Chunk '01_nested_block' (nested_block) technical extraction returned malformed JSON and needs manual review." in findings_section
    assert "Automatic extraction for some chunks returned malformed JSON and needs manual review." in findings_section
    assert findings_section.index("Automatic extraction for this chunk returned malformed JSON and could not be parsed; this chunk needs manual review.") < findings_section.index("Chunk '01_nested_block' (nested_block) technical extraction returned malformed JSON and needs manual review.")
    assert findings_section.index("Chunk '01_nested_block' (nested_block) technical extraction returned malformed JSON and needs manual review.") < findings_section.index("Automatic extraction for some chunks returned malformed JSON and needs manual review.")


def test_business_rules_are_ordered_by_source_execution_order_not_llm_order():
    """The synthesis LLM can return rules in any order; the canonical IR
    must reorder them by where their evidence first appears in the
    source file, so the business report always reads top-to-bottom in
    execution order regardless of what order the model produced them in.
    """
    ingestion = _ingestion()
    merged = _merged()
    # Two statements: line 40 (later in the file) and line 5 (earlier).
    merged["statement_provenance"] = [
        {
            "statement_id": "stmt_late",
            "source_chunk_id": "chunk_late",
            "source_chunk_kind": "main_body",
            "source_line_start": 40,
            "source_line_end": 40,
            "source_location_status": "available",
        },
        {
            "statement_id": "stmt_early",
            "source_chunk_id": "chunk_early",
            "source_chunk_kind": "main_body",
            "source_line_start": 5,
            "source_line_end": 5,
            "source_location_status": "available",
        },
    ]
    synthesis = _synthesis()
    # Deliberately return the rule whose evidence is LATER in the source
    # first, and the EARLIER one second - the opposite of execution order.
    synthesis.data["business_rules"] = [
        {
            "rule_id": "rule_late",
            "rule_type": "explicit",
            "condition": "late condition",
            "action": "late action",
            "output_field": "LATE_FIELD",
            "fields_affected": ["LATE_FIELD"],
            "source_chunks": ["chunk_late:main_body"],
            "source_evidence": ["late condition"],
        },
        {
            "rule_id": "rule_early",
            "rule_type": "explicit",
            "condition": "early condition",
            "action": "early action",
            "output_field": "EARLY_FIELD",
            "fields_affected": ["EARLY_FIELD"],
            "source_chunks": ["chunk_early:main_body"],
            "source_evidence": ["early condition"],
        },
        {
            "rule_id": "rule_unknown",
            "rule_type": "explicit",
            "condition": "no location info",
            "action": "unknown action",
            "output_field": "UNKNOWN_FIELD",
            "fields_affected": ["UNKNOWN_FIELD"],
            "source_chunks": [],
            "source_evidence": ["no location info"],
        },
    ]

    ir = CanonicalBusinessIR.from_pipeline(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    ordered_ids = [rule.rule_id for rule in ir.business_rules]
    # rule_early (line 5) must come before rule_late (line 40), even
    # though the LLM returned them in the opposite order; rule_unknown
    # has no resolvable location and must sort after both known-location
    # rules, keeping its original relative position.
    assert ordered_ids == ["rule_early", "rule_late", "rule_unknown"]
