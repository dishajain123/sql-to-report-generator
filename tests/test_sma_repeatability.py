"""Repeatability regression test for the SMA_MARKING procedure.

Runs the deterministic layers of the pipeline (ingestion, decision-chain
extraction, table-operation extraction, deterministic rule synthesis via
`ensure_decision_chain_coverage`, reconciliation, canonical IR, business
report, and verification report) three times over the same input and
asserts every stage produces byte-identical output.

Scope note: this exercises the deterministic pipeline stages - the ones
responsible for canonicalization, ID stability, ordering, and reconciliation
- without making a live LLM call. Those stages are exactly where
non-determinism from Python set/dict iteration, unstable sorting, retrieval
tie-breaking, or timestamp/uuid-based identity would show up, and they are
what canonicalizes whatever the model returns into the final report. The
model call itself is already configured for minimum sampling variance
(temperature=0.1, seed=0 passed when the provider supports it - see
`pipeline.py` DEFAULT_TEMPERATURE/DEFAULT_SEED) and is not re-exercised here
to avoid spending live Bedrock cost/data-transfer on every test run; a
model response is DATA to this test's mocked path exactly the same as it is
to `merge_section_results` and `RuleSynthesizerAgent.synthesize` elsewhere
in the suite.
"""
from __future__ import annotations

from pathlib import Path

from src.ingestion.ingestion import CodeIngestionAgent
from src.ir.canonical_ir import CanonicalBusinessIR
from src.output.report_formatter import ReportFormatterAgent
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks, split_table_operations
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from src.validation.reconciliation import reconcile_deterministic_evidence
from pipeline import _extract_deterministic_decision_chains, supported_analysis_dialect

SAMPLE = Path(__file__).resolve().parent.parent / "samples/PRO.SMA_MARKING_12122023.StoredProcedure.sql"


def _run_deterministic_pipeline_once():
    """One full pass through every deterministic stage, from raw SQL to
    the final business report and verification report. Mirrors the real
    `pipeline.py` orchestration for these stages exactly (same helper
    functions, same call order) so this test exercises the genuine
    production code path, not a simplified stand-in.
    """
    ingestion = CodeIngestionAgent().ingest(str(SAMPLE))
    dialect = supported_analysis_dialect(ingestion)
    chains = _extract_deterministic_decision_chains(ingestion.raw_code, dialect or "tsql")
    table_operations, statement_provenance = extract_table_operations_from_chunks(ingestion.chunks, dialect)
    tables_read, tables_written = split_table_operations(table_operations)

    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    synthesis = SynthesisResult(data={"business_rules": rules})

    merged_extraction = {
        "decision_chains": chains,
        "statement_provenance": statement_provenance,
        "table_operations": table_operations,
        "tables_read": tables_read,
        "tables_written": tables_written,
        "llm_tables_read": [],
        "llm_tables_written": [],
    }

    reconciliation = reconcile_deterministic_evidence(
        ingestion=ingestion, merged_extraction=merged_extraction, synthesis=synthesis,
    )
    merged_extraction["reconciliation"] = reconciliation.to_dict()
    merged_extraction["coverage"] = reconciliation.coverage
    merged_extraction["quality"] = reconciliation.quality
    synthesis.data["reconciliation"] = reconciliation.to_dict()
    synthesis.data["coverage"] = reconciliation.coverage
    synthesis.data["quality"] = reconciliation.quality

    canonical_ir = CanonicalBusinessIR.from_pipeline(
        ingestion=ingestion, merged_extraction=merged_extraction, synthesis=synthesis, reconciliation=reconciliation,
    )
    formatter = ReportFormatterAgent()
    report = formatter.format(ingestion, merged_extraction, synthesis, canonical_ir=canonical_ir)
    verification = formatter.format_verification(ingestion, merged_extraction, synthesis, canonical_ir=canonical_ir)

    return {
        "chains": chains,
        "rules": rules,
        "canonical_ir": canonical_ir.to_dict(),
        "report": report,
        "verification": verification,
    }


def test_sma_pipeline_is_repeatable_across_three_runs():
    """The same input/configuration must produce the same canonical IR,
    the same business rules (content and order), and the same final
    report/verification report on every run - this is the acceptance
    criterion, not merely "no exception raised".
    """
    runs = [_run_deterministic_pipeline_once() for _ in range(3)]

    # 1. Decision chains: same chains, same order, same content.
    assert runs[0]["chains"] == runs[1]["chains"] == runs[2]["chains"]

    # 2. Business rules (the canonical business-rule identity, not just a
    # rendering artifact): same rule_ids in the same order, same content.
    rule_ids = [[rule.get("rule_id") for rule in run["rules"]] for run in runs]
    assert rule_ids[0] == rule_ids[1] == rule_ids[2]
    assert runs[0]["rules"] == runs[1]["rules"] == runs[2]["rules"]

    # 3. Canonical IR: the structured representation the report is built
    # from must be byte-for-byte identical.
    assert runs[0]["canonical_ir"] == runs[1]["canonical_ir"] == runs[2]["canonical_ir"]

    # 4. Final business report: identical Markdown on every run.
    assert runs[0]["report"] == runs[1]["report"] == runs[2]["report"]

    # 5. Verification report: identical Markdown on every run (rule IDs,
    # reconciliation IDs, ordering, and the quality/coverage summary all
    # included).
    assert runs[0]["verification"] == runs[1]["verification"] == runs[2]["verification"]


def test_sma_repeatability_would_catch_a_real_regression():
    """Sanity-check the test itself: two runs that genuinely differ (rule
    order shuffled) must fail the same comparison the repeatability test
    above relies on, so a silent no-op assertion isn't hiding behind an
    equality check on data that's trivially always equal.
    """
    run_a = _run_deterministic_pipeline_once()
    run_b = dict(run_a)
    run_b["rules"] = list(reversed(run_a["rules"]))
    assert run_a["rules"] != run_b["rules"]
