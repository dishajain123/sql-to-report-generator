"""Regression coverage for large-procedure chunk/decision-chain coherence
at a scale representative of the audit's real dataset (the largest real
file there produced 41 chunks and 89 decision chains). Uses a
programmatically generated, generic synthetic procedure - not any real
procedure's name or content - combining the same shapes the audit flagged
(temp-table lifecycle blocks + CASE-expression business classification),
so this is reproducible without the real dataset and never encodes any
client-specific logic.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.ingestion import CodeIngestionAgent, MAX_CHUNK_CHARS
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent
from src.validation.semantic_validation import (
    extract_case_assignment_decision_chains,
    merge_decision_chains,
)


def _generate_large_procedure(n_blocks: int = 150) -> str:
    """Build a synthetic T-SQL procedure with `n_blocks` independent
    temp-table-lifecycle + CASE-classification blocks - large enough
    (~150-200KB) and varied enough that it must produce a realistic
    multi-chunk split and a genuinely large decision-chain count, without
    being derived from any real stored procedure.
    """
    header = "CREATE PROCEDURE dbo.SyntheticLargeBatchJob\n    @ProcessingDate DATE\nAS\nBEGIN\n    SET NOCOUNT ON;\n\n"
    blocks = []
    for i in range(n_blocks):
        table = f"#stage_{i}"
        field = f"Classification_{i}"
        block = (
            f"    IF OBJECT_ID('TEMPDB..{table}') IS NOT NULL\n"
            f"        DROP TABLE {table}\n\n"
            f"    SELECT AccountId, OverdueDays_{i} AS OverdueDays INTO {table}\n"
            f"    FROM dbo.SourceAccounts_{i} WHERE ProcessingDate = @ProcessingDate\n\n"
            f"    UPDATE A SET A.{field} = (\n"
            f"        CASE\n"
            f"            WHEN A.OverdueDays BETWEEN 1 AND 30 THEN 'BAND_1'\n"
            f"            WHEN A.OverdueDays BETWEEN 31 AND 60 THEN 'BAND_2'\n"
            f"            WHEN A.OverdueDays BETWEEN 61 AND 90 THEN 'BAND_3'\n"
            f"            ELSE 'BAND_0'\n"
            f"        END\n"
            f"    )\n"
            f"    FROM {table} A\n"
            f"    WHERE A.OverdueDays > 0\n\n"
            f"    EXEC dbo.LogStageCompletion @StageName = 'stage_{i}'\n\n"
        )
        blocks.append(block)
    footer = "END\n"
    return header + "".join(blocks) + footer


def test_large_synthetic_procedure_chunks_at_a_realistic_scale():
    """Sanity-checks the chunker's behavior at the same order of magnitude
    the audit measured on real data (up to 41 chunks) rather than only
    ever being exercised against small fixtures."""
    source = _generate_large_procedure(n_blocks=150)
    assert len(source) > 80_000, "fixture must be large enough to be representative"

    agent = CodeIngestionAgent(max_chunk_chars=MAX_CHUNK_CHARS)
    result = agent.ingest_text(source, dialect="tsql", source_filename="synthetic_large.sql")

    assert len(result.chunks) >= 15, "a 100KB+ object with 150 blocks should split into many chunks"
    assert len(result.chunks) <= 200, "chunk count should stay proportional, not explode"
    # No chunk may silently exceed the configured ceiling by more than the
    # documented soft-limit headroom used by _enforce_size_limit.
    for chunk in result.chunks:
        assert len(chunk.text) <= MAX_CHUNK_CHARS * 1.5


def test_deterministic_decision_chains_scale_with_no_duplication_or_loss():
    """Deterministic decision-chain extraction runs over the *whole* raw
    source in one pass (not per-LLM-chunk), so it is inherently immune to
    the cross-chunk-boundary loss the audit worried about - this test
    proves that holds at the ~40+ decision-chain scale the audit's real
    largest file actually reached (89 chains), not just on a handful."""
    n_blocks = 150
    source = _generate_large_procedure(n_blocks=n_blocks)

    chains = extract_case_assignment_decision_chains(source)

    assert len(chains) == n_blocks, "exactly one CASE decision chain per synthetic block, no loss or duplication"

    def _target_field(chain: dict) -> str:
        branches = chain.get("branches") or []
        assignments = branches[0].get("assignments") if branches else []
        return str((assignments or [{}])[0].get("field") or "")

    targets = {_target_field(chain) for chain in chains}
    assert len(targets) == n_blocks, "every block's distinct target field must be captured, none merged together"
    for i in range(n_blocks):
        assert f"Classification_{i}" in targets, f"block {i}'s target field went missing"


def test_merge_decision_chains_stays_idempotent_at_scale():
    """Merging the same large chain set with itself (simulating agreement
    between the deterministic pass and an LLM-derived pass covering the
    same source) must not duplicate entries - the exact dedup/reconciliation
    behavior `decision_groups.py`/`reconciliation.py` exist to guarantee,
    now checked at real-world scale instead of only a small sample."""
    source = _generate_large_procedure(n_blocks=150)
    chains = extract_case_assignment_decision_chains(source)
    assert len(chains) == 150

    merged = merge_decision_chains(chains, chains)

    assert len(merged) == 150, "merging a chain set with an exact duplicate of itself must not double-count"


def test_large_synthetic_procedure_triggers_sectioned_synthesis():
    """Confirms the pipeline's existing hierarchical/sectioned synthesis
    path (plan_synthesis_sections) actually engages for an object at this
    scale - the audit's proposed fix already exists in the codebase; this
    is the missing test proving it activates rather than being dead code
    for real-sized objects."""
    source = _generate_large_procedure(n_blocks=150)
    agent = CodeIngestionAgent(max_chunk_chars=MAX_CHUNK_CHARS)
    ingestion = agent.ingest_text(source, dialect="tsql", source_filename="synthetic_large.sql")

    synthesizer = RuleSynthesizerAgent(
        client=None, model="test-model", temperature=0.1, seed=0, provider="openai",
        max_tokens=2000, hard_max_output_tokens=6000,
    )

    assert synthesizer.requires_sectioned_synthesis(source) is True
    sections = synthesizer.plan_synthesis_sections(ingestion.chunks, source)
    assert len(sections) > 1, "an object this large must actually split into multiple synthesis sections"
