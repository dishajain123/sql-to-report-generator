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
    assert "## Business Rule Summary" in report
    assert "## Source Traceability" in verification
    assert "STATUS" in report
