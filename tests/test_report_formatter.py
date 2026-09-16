"""Golden-style tests for business and verification report boundaries."""

from __future__ import annotations

from src.ingestion.ingestion import CodeChunk, IngestionResult
from src.ir.canonical_ir import CanonicalBusinessIR
from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import SynthesisResult
from src.validation.reconciliation import reconcile_deterministic_evidence


_SOURCE = """CREATE PROCEDURE dbo.classify_account
AS
BEGIN
    UPDATE ACCOUNT
    SET STATUS = CASE
        WHEN SCORE >= 90 THEN 'A'
        ELSE 'B'
    END;
END
"""


def _ingestion() -> IngestionResult:
    return IngestionResult(
        object_name="classify_account",
        object_type="PROCEDURE",
        parameters=[],
        raw_code=_SOURCE,
        original_code=_SOURCE,
        chunks=[
            CodeChunk(
                chunk_id="chunk_1",
                kind="main_body",
                text=_SOURCE,
                context_path=["main_body"],
                source_filename="demo.sql",
                source_char_start=0,
                source_char_end=len(_SOURCE),
                source_line_start=1,
                source_line_end=9,
                source_location_status="available",
            )
        ],
        object_id="obj_1",
        dialect="TSQL",
        concrete_dialect="tsql",
        fallback_dialect="tsql",
        source_hash="source-hash",
        source_filename="demo.sql",
    )


def _chain():
    return {
        "chain_type": "CASE_EXPRESSION",
        "subject": "STATUS",
        "chain_id": "case_0005_0008",
        "source_line_start": 5,
        "source_line_end": 8,
        "branches": [
            {
                "branch_condition": "SCORE >= 90",
                "assignments": [{"field": "STATUS", "value": "'A'"}],
                "branch_id": "case_0005_0008:branch_001",
                "source_line_start": 6,
                "source_line_end": 6,
                "source_chunk_id": "chunk_1",
                "source_statement_id": "stmt_1",
                "evidence_spans": [
                    {
                        "source_file": "demo.sql",
                        "line_start": 6,
                        "line_end": 6,
                        "chunk_id": "chunk_1",
                        "statement_id": "stmt_1",
                        "source_location_status": "available",
                    }
                ],
            },
            {
                "branch_condition": "ELSE",
                "assignments": [{"field": "STATUS", "value": "'B'"}],
                "branch_id": "case_0005_0008:branch_002",
                "source_line_start": 7,
                "source_line_end": 7,
                "source_chunk_id": "chunk_1",
                "source_statement_id": "stmt_1",
                "evidence_spans": [
                    {
                        "source_file": "demo.sql",
                        "line_start": 7,
                        "line_end": 7,
                        "chunk_id": "chunk_1",
                        "statement_id": "stmt_1",
                        "source_location_status": "available",
                    }
                ],
            },
        ],
    }


def _rule(*, source_evidence=True, rule_id="rule_1"):
    return {
        "rule_id": rule_id,
        "rule_name": "Classify account status",
        "business_meaning": "Assigns a risk status based on the account score.",
        "output_field": "STATUS",
        "fields_affected": ["STATUS"],
        "eligibility": ["The account is processed."],
        "condition": "SCORE >= 90",
        "action": "STATUS = 'A'",
        "decision_logic_rows": [
            {"condition": "SCORE >= 90", "outcome": "'A'"},
            {"condition": "ELSE", "outcome": "'B'"},
        ],
        "source_evidence": ["SCORE >= 90", "ELSE"] if source_evidence else [],
        "source_chunks": ["chunk_1:main_body"] if source_evidence else [],
        "technical_references": ["tables_written[0]"] if source_evidence else [],
        "evidence_spans": [
            {
                "source_file": "demo.sql",
                "line_start": 5,
                "line_end": 8,
                "chunk_id": "chunk_1",
                "statement_id": "stmt_1",
                "evidence_type": "CONDITION",
                "statement_parse_status": "parsed",
                "source_location_status": "available",
            }
        ] if source_evidence else [],
        "validation_status": "verified" if source_evidence else "unverified",
        "rule_type": "explicit",
        "confidence": "high" if source_evidence else "low",
    }


def _build(*, include_unresolved=False):
    rules = [_rule()]
    if include_unresolved:
        rules.append(_rule(source_evidence=False, rule_id="rule_2"))
    merged = {
        "tables_read": [],
        "tables_written": [],
        "llm_tables_read": [],
        "llm_tables_written": [],
        "decision_chains": [_chain()],
        "statement_provenance": [
            {
                "statement_id": "stmt_1",
                "source_chunk_id": "chunk_1",
                "source_chunk_kind": "main_body",
                "statement_kind": "UPDATE",
                "source_statement_text": "UPDATE ACCOUNT SET STATUS = CASE ... END",
                "parse_status": "parsed",
                "source_file": "demo.sql",
                "source_line_start": 4,
                "source_line_end": 8,
                "source_location_status": "available",
            }
        ],
        "chunk_provenance": [
            {
                "chunk_id": "chunk_1",
                "chunk_kind": "main_body",
                "chunk_context": ["main_body"],
                "source_file": "demo.sql",
                "source_line_start": 1,
                "source_line_end": 9,
                "source_location_status": "available",
            }
        ],
        "ambiguities": [],
    }
    synthesis = SynthesisResult(
        data={
            "purpose_summary": "Classifies account status.",
            "step_by_step_flow": ["Evaluate the account score."],
            "business_rules": rules,
            "calculations": [],
            "exception_handling_summary": "",
            "ambiguities": [],
        }
    )
    reconciliation = reconcile_deterministic_evidence(
        ingestion=_ingestion(),
        merged_extraction=merged,
        synthesis=synthesis,
    )
    merged["reconciliation"] = reconciliation.to_dict()
    merged["coverage"] = reconciliation.coverage
    merged["quality"] = reconciliation.quality
    canonical_ir = CanonicalBusinessIR.from_pipeline(
        ingestion=_ingestion(),
        merged_extraction=merged,
        synthesis=synthesis,
        reconciliation=reconciliation,
    )
    return _ingestion(), merged, synthesis, canonical_ir


def test_business_report_renders_one_clear_decision_logic_table_before_technical_details():
    ingestion, merged, synthesis, canonical_ir = _build()
    report = ReportFormatterAgent().format(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        canonical_ir=canonical_ir,
    )

    assert report.count("### Decision Logic") == 1
    assert report.count("| Condition | Result |") == 1
    assert "| SCORE >= 90 | 'A' |" in report
    assert "| ELSE | 'B' |" in report
    assert report.count("| SCORE >= 90 |") == 1
    assert report.count("| ELSE |") == 1
    assert "|  | STATUS = 'A' |" not in report
    assert "Decision-chain coverage gaps" not in report
    assert report.index("**Summary:**") < report.index("### Decision Logic")
    assert "## Source Traceability" not in report
    assert "rule_1" not in report
    assert "demo.sql" not in report


def test_verification_report_keeps_source_traceability_separate_and_shows_phase2_quality():
    ingestion, merged, synthesis, canonical_ir = _build()
    verification = ReportFormatterAgent().format_verification(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        canonical_ir=canonical_ir,
    )

    assert verification.count("## Source Traceability") == 1
    assert verification.count("## Quality Summary") == 1
    assert "| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |" in verification
    assert "SCORE >= 90" in verification
    assert "demo.sql" in verification
    assert "chunk_1" in verification
    assert "stmt_1" in verification
    assert "### Decision-Chain Branch Provenance" in verification
    assert "case_0005_0008:branch_001" in verification
    assert "demo.sql \\| Line 6 \\| Chunk chunk_1 \\| Statement stmt_1" in verification
    assert "**Decision-chain coverage:** 2 / 2 branches (100.0%)" in verification
    assert verification.index("## Source Traceability") < verification.index("## Quality Summary")


def test_quality_summary_renders_review_required_information():
    ingestion, merged, synthesis, canonical_ir = _build(include_unresolved=True)
    verification = ReportFormatterAgent().format_verification(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        canonical_ir=canonical_ir,
    )

    assert "## Quality Summary" in verification
    assert "- **Review required:** Yes" in verification
    assert "- **Review required items:**" in verification
    assert "Decision-chain coverage:" in verification


def test_quality_summary_explains_uncovered_decision_chain_branches():
    ingestion, merged, synthesis, canonical_ir = _build()
    merged["coverage"] = dict(merged["coverage"])
    merged["coverage"].update(
        {
            "decision_chain_covered_branches": 1,
            "decision_chain_coverage_pct": 50.0,
            "decision_chain_coverage_gaps": [
                {
                    "branch_condition": "ELSE",
                    "chain_type": "CASE_EXPRESSION",
                }
            ],
        }
    )
    merged["quality"] = dict(merged["quality"])
    merged["quality"]["review_required"] = True

    verification = ReportFormatterAgent().format_verification(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        canonical_ir=None,
    )

    assert (
        "- **Decision-chain coverage gaps:** 1 branch(es) require review (`ELSE`)"
        in verification
    )


def test_quality_summary_does_not_claim_chain_coverage_when_no_chains_exist():
    ingestion, merged, synthesis, canonical_ir = _build()
    merged["decision_chains"] = []
    merged["coverage"] = dict(merged["coverage"])
    merged["coverage"].update(
        {
            "decision_chain_count": 0,
            "decision_chain_total_branches": 0,
            "decision_chain_covered_branches": 0,
            "decision_chain_coverage_pct": 100.0,
        }
    )
    merged["quality"] = dict(merged["quality"])
    merged["quality"]["factors"] = dict(merged["quality"].get("factors") or {})
    merged["quality"]["factors"]["decision_chain_coverage_pct"] = 100.0
    canonical_ir = CanonicalBusinessIR.from_pipeline(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
    )

    verification = ReportFormatterAgent().format_verification(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        canonical_ir=canonical_ir,
    )

    assert "**Decision-chain coverage:** Not applicable" in verification
    assert "Decision-chain coverage: 0 / 0 branches (100.0%)" not in verification


# --------------------------------------------------------------------------
# render_called_procedures_section: batch-mode cross-reference resolution
# --------------------------------------------------------------------------


def test_render_called_procedures_section_without_resolver_matches_original_rendering():
    """Single-file mode (resolved=None) must render exactly the original
    3-column table with no "Report" column - unchanged behavior."""
    ingestion = _ingestion()
    ingestion.called_procedures = [
        {"name": "PRO.ChildProc", "arguments": "@TimeKey"},
    ]

    section = ReportFormatterAgent.render_called_procedures_section(ingestion)

    assert "## Called Procedures" in section
    assert "| Order | Procedure | Arguments |" in section
    assert "Report" not in section
    assert "PRO.ChildProc" in section


def test_render_called_procedures_section_with_resolver_links_to_sibling_report():
    ingestion = _ingestion()
    ingestion.called_procedures = [
        {"name": "[PRO].[ChildProc]", "arguments": "@TimeKey"},
        {"name": "PRO.UnknownSiblingProc", "arguments": ""},
    ]
    resolved = {"pro.childproc": "PRO.ChildProc_report.md"}

    section = ReportFormatterAgent.render_called_procedures_section(ingestion, resolved)

    assert "| Order | Procedure | Arguments | Report |" in section
    assert "[PRO.ChildProc_report.md](PRO.ChildProc_report.md)" in section
    assert "_not in this batch_" in section


def test_render_called_procedures_section_empty_when_no_calls():
    ingestion = _ingestion()
    ingestion.called_procedures = []

    assert ReportFormatterAgent.render_called_procedures_section(ingestion) == ""
    assert ReportFormatterAgent.render_called_procedures_section(ingestion, {}) == ""


def test_degraded_rule_markers_are_not_rendered_in_the_business_report():
    # Per explicit client direction, the business report must never show
    # any "needs review"/degraded signal, regardless of why a rule is
    # flagged (`degraded_reason` "truncated" or "gap_review") - the reader
    # should see confident, complete business analysis. The underlying
    # `degraded`/`degraded_reason` data on the rule dict is untouched;
    # only this rendering path omits it. Covers both wording variants that
    # used to differ (capacity-failure vs successful-gap-review), since
    # neither must ever surface here.
    ingestion, merged, synthesis, _canonical_ir_unused = _build()
    for reason in ("truncated", "gap_review"):
        synthesis.data["business_rules"][0]["degraded"] = True
        synthesis.data["business_rules"][0]["degraded_reason"] = reason
        report = ReportFormatterAgent().format(
            ingestion=ingestion,
            merged_extraction=merged,
            synthesis=synthesis,
            canonical_ir=None,
        )
        assert "truncated or failed" not in report
        assert "added from a targeted review pass" not in report
        assert "Needs Review" not in report
        assert "Run status" not in report


def test_render_business_rule_block_never_shows_a_degraded_marker():
    # Direct unit test of the per-rule renderer: no inline marker for any
    # `degraded_reason` value, and no `consolidation_note` line either.
    formatter = ReportFormatterAgent()
    for reason in ("truncated", "gap_review"):
        rule = _rule()
        rule["degraded"] = True
        rule["degraded_reason"] = reason
        rule["consolidation_note"] = "Also extracted with additional fields in another pass."
        block = "\n".join(formatter._render_business_rule_block(1, rule))
        assert "Needs Review" not in block
        assert "truncated or failed" not in block
        assert "targeted review pass" not in block
        assert "consolidation_note" not in block
        assert "Also extracted with additional fields" not in block


def test_business_report_never_shows_a_findings_or_needs_review_section():
    """Per explicit client direction, the business report must never
    contain a "## Findings / Needs Review" section (or any ambiguity/
    conflict-suppression content that used to feed it), regardless of how
    much genuine ambiguity/uncertainty exists in the underlying data - the
    reader should see confident, complete business analysis. The same
    data is untouched and still available to `_findings_section` directly
    (see its own dedicated tests) and to `format_verification()`'s
    diagnostics - only this document omits it.
    """
    ingestion, merged, synthesis, _canonical_ir_unused = _build()
    merged["ambiguities"] = [
        "Dynamic SQL detected and cannot be fully statically resolved: EXEC (@sql)...",
        "Working table `#temp_unused` appears to be unused.",
    ]
    synthesis.data["ambiguities"] = [
        "A second, separate condition may affect this same field but could not be resolved with confidence.",
    ]
    report = ReportFormatterAgent().format(
        ingestion=ingestion,
        merged_extraction=merged,
        synthesis=synthesis,
        canonical_ir=None,
    )
    assert "## Findings" not in report
    assert "Needs Review" not in report
    assert "Dynamic SQL detected" not in report
    assert "appears to be unused" not in report
    assert "could not be resolved with confidence" not in report


def test_field_token_set_drops_a_table_name_mistakenly_listed_as_a_field():
    """A model-authored rule occasionally lists its own TARGET TABLE (not a
    column) in fields_affected/output_field - e.g. "fields_affected:
    ACCOUNT_STATUS_HISTORY" for a rule that really writes several columns
    into that table. Left in, that token defeats every exact-set
    field-identity comparison the 5 duplicate-suppression passes rely on
    (this rule's set can never equal another representation of the same
    write's real per-column set). It must be dropped - but only when it
    names a KNOWN table and is not ALSO a known column name somewhere in
    the procedure, so a genuine column that happens to share a table's
    name is never dropped by mistake.
    """
    merged_extraction = {
        "tables_read": [],
        "tables_written": [
            {"table": "ACCOUNT_STATUS_HISTORY", "target_columns": ["STATUS", "UPDATED_AT"]},
        ],
    }
    rule = {"fields_affected": "STATUS, ACCOUNT_STATUS_HISTORY"}
    fields = ReportFormatterAgent._field_token_set(rule, merged_extraction)
    assert fields == {"status"}


def test_field_token_set_keeps_a_field_that_also_happens_to_be_a_table_name():
    merged_extraction = {
        "tables_read": [],
        "tables_written": [
            {"table": "STATUS", "target_columns": ["STATUS", "REASON"]},
        ],
    }
    rule = {"fields_affected": "STATUS"}
    fields = ReportFormatterAgent._field_token_set(rule, merged_extraction)
    assert fields == {"status"}


def test_field_token_set_without_merged_extraction_keeps_every_token():
    rule = {"fields_affected": "STATUS, ACCOUNT_STATUS_HISTORY"}
    fields = ReportFormatterAgent._field_token_set(rule, None)
    assert fields == {"status", "account_status_history"}


def test_calculations_section_excludes_process_bookkeeping_table():
    """A MAX/COUNT-style calculation whose target table is the same
    RUNNINGPROCESSSTATUS-style bookkeeping table
    `_remove_operational_status_rules` already keeps out of the
    business-rule collection must also be kept out of the Calculations
    section, rather than showing up as if it were a real business
    calculation.
    """
    merged_extraction = {
        "table_operations": [
            {"table": "ACLRUNNINGPROCESSSTATUS", "operation": "UPDATE"},
        ],
        "calculations": [],
    }
    synthesis = SynthesisResult(data={
        "calculations": [
            {"field": "ACLRUNNINGPROCESSSTATUS.COMPLETED", "expression": "COUNT(*)"},
            {"field": "TOTAL_SCORE", "expression": "BASE + BONUS"},
        ],
    })
    section = ReportFormatterAgent()._calculations(synthesis, merged_extraction)
    assert "TOTAL_SCORE" in section
    assert "COMPLETED" not in section
    assert "ACLRUNNINGPROCESSSTATUS" not in section


def test_calculations_section_keeps_all_calculations_when_no_status_table_exists():
    merged_extraction = {"table_operations": [], "calculations": []}
    synthesis = SynthesisResult(data={
        "calculations": [{"field": "TOTAL_SCORE", "expression": "BASE + BONUS"}],
    })
    section = ReportFormatterAgent()._calculations(synthesis, merged_extraction)
    assert "TOTAL_SCORE" in section
