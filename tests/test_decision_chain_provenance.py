"""Regression coverage for deterministic decision-chain provenance."""

from src.ingestion.guardrails import validate_extraction_shape
from src.ingestion.ingestion import CodeChunk, IngestionResult
from src.ir.canonical_ir import CanonicalBusinessIR
from src.synthesis.rule_synthesizer import SynthesisResult
from src.validation.reconciliation import _decision_chain_rows, _rule_decision_chain_links
from src.validation.semantic_validation import (
    extract_procedural_decision_chains,
    merge_decision_chains,
)
from pipeline import _annotate_decision_chain_provenance


def _source_chain():
    source = """IF status = 'A' THEN
  result := 'OPEN';
ELSE
  result := 'OTHER';
END IF;
"""
    return source, extract_procedural_decision_chains(source)[0]


def test_pipeline_attaches_existing_chunk_and_statement_provenance_to_branches():
    source, chain = _source_chain()
    ingestion = IngestionResult(
        object_name="classify",
        object_type="PROCEDURE",
        parameters=[],
        raw_code=source,
        chunks=[
            CodeChunk(
                chunk_id="chunk_1",
                kind="main_body",
                text=source,
                source_filename="demo.sql",
                source_char_start=0,
                source_char_end=len(source),
                source_line_start=1,
                source_line_end=5,
                source_location_status="available",
            )
        ],
        object_id="obj_1",
        source_filename="demo.sql",
    )
    merged = {
        "decision_chains": [chain],
        "statement_provenance": [
            {
                "statement_id": "stmt_1",
                "source_chunk_id": "chunk_1",
                "source_char_start": 0,
                "source_char_end": len(source),
                "source_line_start": 1,
                "source_line_end": 5,
                "source_file": "demo.sql",
            }
        ],
    }

    _annotate_decision_chain_provenance(merged, ingestion)

    branch = merged["decision_chains"][0]["branches"][0]
    assert branch["source_chunk_id"] == "chunk_1"
    assert branch["source_statement_id"] == "stmt_1"
    assert branch["source_identifier"] == "demo.sql"
    assert branch["evidence_spans"][0]["chunk_id"] == "chunk_1"
    assert branch["evidence_spans"][0]["statement_id"] == "stmt_1"


def test_guardrail_normalization_preserves_branch_provenance():
    _, chain = _source_chain()
    normalized, warnings = validate_extraction_shape({"decision_chains": [chain]})

    assert warnings == []
    branch = normalized["decision_chains"][0]["branches"][0]
    assert branch["branch_id"] == chain["branches"][0]["branch_id"]
    assert branch["evidence_spans"][0]["line_start"] == chain["branches"][0]["source_line_start"]


def test_duplicate_chain_merge_keeps_canonical_chain_provenance():
    _, chain = _source_chain()
    duplicate = {
        **chain,
        "source_file": "other.sql",
        "branches": [
            {**branch, "source_file": "other.sql"}
            for branch in chain["branches"]
        ],
    }

    merged = merge_decision_chains([chain], [duplicate])

    assert len(merged) == 1
    assert merged[0]["chain_id"] == chain["chain_id"]
    assert merged[0]["branches"][0]["branch_id"] == chain["branches"][0]["branch_id"]


def test_canonical_ir_retains_decision_branch_provenance():
    _, chain = _source_chain()
    ingestion = IngestionResult(
        object_name="classify",
        object_type="PROCEDURE",
        parameters=[],
        raw_code="",
        chunks=[],
        object_id="obj_1",
    )
    synthesis = SynthesisResult(
        data={
            "business_rules": [
                {
                    "rule_id": "rule_1",
                    "rule_name": "Classify status",
                    "fields_affected": ["result"],
                    "condition": "status = 'A'",
                    "action": "result = 'OPEN'",
                    "decision_logic_rows": [
                        {"condition": "status = 'A'", "outcome": "'OPEN'"},
                        {"condition": "ELSE", "outcome": "'OTHER'"},
                    ],
                }
            ]
        }
    )

    canonical = CanonicalBusinessIR.from_pipeline(
        ingestion=ingestion,
        merged_extraction={"decision_chains": [chain]},
        synthesis=synthesis,
    )

    branch = canonical.decision_blocks[0]["branches"][0]
    assert branch["chain_id"] == chain["chain_id"]
    assert branch["branch_id"] == chain["branches"][0]["branch_id"]
    assert branch["provenance"][0]["line_start"] == chain["branches"][0]["source_line_start"]
    assert canonical.to_dict()["decision_chains"][0]["branches"][0]["branch_id"] == branch["branch_id"]


def test_coverage_linkage_can_use_branch_evidence_spans_and_ids():
    _, chain = _source_chain()
    rows = _decision_chain_rows({"decision_chains": [chain]})
    rule = {
        "condition": "status = 'A'",
        "action": "result = 'OPEN'",
        "fields_affected": ["result"],
        "source_evidence": [],
        "evidence_spans": [
            {
                "line_start": chain["branches"][0]["source_line_start"],
                "line_end": chain["branches"][0]["source_line_end"],
            }
        ],
    }

    links = _rule_decision_chain_links(rule, rows)

    assert links
    assert links[0]["_branch_id"] == chain["branches"][0]["branch_id"]
    assert links[0]["_chain_evidence_spans"]


def test_unknown_branch_location_remains_unavailable_without_fabrication():
    chain = {
        "chain_type": "IF_ELSIF",
        "branches": [
            {"branch_condition": "x = 1", "assignments": [{"field": "result", "value": "'A'"}]},
            {"branch_condition": "ELSE", "assignments": [{"field": "result", "value": "'B'"}]},
        ],
    }

    rows = _decision_chain_rows({"decision_chains": [chain]})

    assert rows[0]["source_char_start"] == -1
    assert rows[0]["source_line_start"] == -1
    assert rows[0]["_chain_evidence_spans"] == []
