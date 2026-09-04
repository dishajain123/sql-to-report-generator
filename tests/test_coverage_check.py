from pathlib import Path

from src.validation.coverage_check import (
    CoverageGap,
    find_coverage_gaps,
    find_decision_points,
    format_gap_for_ambiguity,
)
from src.synthesis.rule_synthesizer import SynthesisResult
from src.ingestion.ingestion import IngestionResult
import pipeline as pipeline_module
from pipeline import LogicRulesExtractorPipeline


_SMA_CASE_SOURCE = """
UPDATE A SET A.SMA_CLASS=
   (CASE  WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0'
          WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1'
          WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2'
          WHEN dpd.DPD_Max > 90 THEN 'SMA_2'
          ELSE NULL
   END)
FROM ##AccountCal A
"""


def test_find_decision_points_locates_case_and_if_keywords_by_line():
    points = find_decision_points(_SMA_CASE_SOURCE)
    keywords = {p["keyword"] for p in points}
    assert "CASE" in keywords
    assert "WHEN" in keywords
    lines = {p["line"] for p in points}
    assert 3 in lines and 6 in lines


def test_find_decision_points_ignores_commented_and_quoted_keywords():
    source = "-- WHEN this is commented out, CASE should not count\nA = 'literal with WHEN inside'"
    assert find_decision_points(source) == []


def test_uncited_decision_ladder_is_reported_as_a_gap():
    gaps = find_coverage_gaps(_SMA_CASE_SOURCE, rules=[])
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.line_start == 3
    assert gap.line_end == 6
    assert "SMA_0" in gap.snippet


def test_rule_citing_the_branch_text_clears_the_gap():
    rules = [
        {
            "rule_name": "Classify SMA stage from DPD",
            "fields_affected": ["SMA_CLASS"],
            "source_evidence": [
                "dpd.DPD_Max BETWEEN 1 AND 30 -> SMA_0",
                "dpd.DPD_Max BETWEEN 31 AND 60 -> SMA_1",
                "dpd.DPD_Max BETWEEN 61 AND 90 -> SMA_2",
                "dpd.DPD_Max > 90 -> SMA_2",
            ],
        }
    ]
    assert find_coverage_gaps(_SMA_CASE_SOURCE, rules=rules) == []


def test_a_construct_no_extractor_recognizes_is_still_caught_generically():
    """The whole point of a keyword-position scan instead of a branch
    parser: it doesn't need to understand MERGE/WHILE/whatever to notice
    an IF sitting in unreviewed territory."""
    source = """
    WHILE @i < 10
    BEGIN
        IF @flag = 'Y'
            SET @Result = 1
        SET @i = @i + 1
    END
    """
    gaps = find_coverage_gaps(source, rules=[])
    assert len(gaps) == 1
    assert "IF" in gaps[0].keywords


def test_no_decision_points_means_no_gaps():
    assert find_coverage_gaps("SELECT 1", rules=[]) == []


def test_no_decision_keyword_assignment_is_still_a_coverage_gap():
    source = "UPDATE accounts SET provision_amount = balance * rate"
    gaps = find_coverage_gaps(source, rules=[])
    assert len(gaps) == 1
    assert gaps[0].keywords == ["ASSIGNMENT", "CALCULATION"]

    rule = {
        "source_evidence": ["provision_amount = balance * rate"],
        "fields_affected": ["provision_amount"],
    }
    assert find_coverage_gaps(source, rules=[rule]) == []


def test_plain_unconditional_update_is_flagged_as_gap():
    source = "UPDATE t SET FLGSMA = 'Y' WHERE x = 1"
    gaps = find_coverage_gaps(source, rules=[])
    assert gaps
    assert gaps[0].line_start == 1
    assert gaps[0].line_end == 1
    assert "ASSIGNMENT" in gaps[0].keywords


def test_plain_update_cited_by_rule_evidence_clears_gap():
    source = "UPDATE t SET FLGSMA = 'Y' WHERE x = 1"
    rules = [{"source_evidence": ["FLGSMA = 'Y' WHERE x = 1"]}]
    assert find_coverage_gaps(source, rules=rules) == []


def test_where_clause_equality_alone_does_not_over_flag():
    source = "SELECT * FROM t WHERE x = 1"
    assert find_coverage_gaps(source, rules=[]) == []


def test_multiline_update_assignment_stays_one_gap():
    source = """UPDATE accounts
SET FLGSMA = 'Y'
WHERE x = 1"""
    gaps = find_coverage_gaps(source, rules=[])
    assert len(gaps) == 1
    assert gaps[0].line_start == 1
    assert gaps[0].line_end == 3


def test_partial_branch_evidence_does_not_cover_the_other_branch():
    source = """UPDATE accounts SET risk_band = CASE
WHEN score < 50 THEN 'LOW'
WHEN score >= 50 THEN 'HIGH'
END"""
    rules = [{"source_evidence": ["score < 50 -> LOW"], "fields_affected": ["risk_band"]}]
    gaps = find_coverage_gaps(source, rules=rules)
    assert gaps
    assert any(gap.line_end >= 3 and "score >= 50" in gap.snippet for gap in gaps)


def test_separate_updates_require_their_own_where_predicate_evidence():
    source = """UPDATE CustomerCal
SET SysAssetClassAlt_Key = 4
WHERE SysNPA_Dt <= @ProcessDate;
UPDATE CustomerCal
SET SysAssetClassAlt_Key = 5
WHERE SplCatg1Alt_Key = 870 OR SplCatg2Alt_Key = 870
   OR SplCatg3Alt_Key = 870 OR SplCatg4Alt_Key = 870;"""
    rules = [{
        "rule_name": "First asset-class update",
        "source_evidence": ["SysNPA_Dt <= @ProcessDate"],
        "condition": "SysNPA_Dt <= @ProcessDate",
        "action": "Assign the first asset class",
        "fields_affected": ["SysAssetClassAlt_Key"],
    }]
    gaps = find_coverage_gaps(source, rules)
    assert gaps
    assert any("SplCatg1Alt_Key" in gap.snippet for gap in gaps)


def test_linked_calculation_evidence_covers_insert_values_anchor():
    source = """INSERT INTO NPA_PROVISION (account_id, provision_amount, created_at)
VALUES (p_account_id, v_outstanding * v_provision_pct / 100, SYSDATE);"""
    rules = [{
        "rule_name": "Persist calculated provision",
        "source_evidence": ["INSERT INTO NPA_PROVISION (account_id, provision_amount, created_at)"],
        "action": "Persist the calculated provision amount",
        "fields_affected": ["provision_amount"],
        "calculations": [{
            "field": "provision_amount",
            "formula": "v_outstanding * v_provision_pct / 100",
            "output_field": "NPA_PROVISION.provision_amount",
        }],
    }]
    assert find_coverage_gaps(source, rules) == []


def test_common_tokens_across_rules_do_not_cover_distinct_statement():
    source = """UPDATE shared_table SET shared_value = first_value WHERE selector = 1;
UPDATE shared_table SET shared_value = second_value WHERE selector = 2 AND scope_code = 9;"""
    rules = [
        {
            "source_evidence": ["shared_value = first_value WHERE selector = 1"],
            "fields_affected": ["shared_value"],
        },
        {
            "source_evidence": ["shared_table shared_value selector"],
            "fields_affected": ["shared_value"],
        },
    ]
    gaps = find_coverage_gaps(source, rules)
    assert gaps
    assert any("second_value" in gap.snippet or "scope_code" in gap.snippet for gap in gaps)


class _CoverageSynthesizer:
    def __init__(self, revised_rules, fail_revision=False):
        self.revised_rules = revised_rules
        self.fail_revision = fail_revision
        self.synthesize_calls = 0
        self.revise_calls = []

    def synthesize(self, **kwargs):
        self.synthesize_calls += 1
        return SynthesisResult(
            data={
                "purpose_summary": "initial",
                "step_by_step_flow": [],
                "business_rules": [],
                "calculations": [],
                "exception_handling_summary": "",
                "ambiguities": [],
            }
        )

    def revise(self, **kwargs):
        self.revise_calls.append(kwargs)
        if self.fail_revision:
            return SynthesisResult(
                data={"business_rules": [], "ambiguities": []},
            )
        return SynthesisResult(
            data={
                "business_rules": self.revised_rules,
                "ambiguities": [],
            }
        )


def _run_coverage_pipeline(monkeypatch, source, revised_rules, *, fail_revision=False, retries=2):
    pipeline = LogicRulesExtractorPipeline.__new__(LogicRulesExtractorPipeline)
    pipeline.dialect = "tsql"
    pipeline.model_name = "test-model"
    pipeline.provider = "test"
    pipeline.project_root = Path(__file__).resolve().parent.parent
    pipeline.chunk_workers = 1
    pipeline.max_coverage_retries = retries
    pipeline.retrieval_agent = type("Retrieval", (), {"build_or_load": lambda self: None})()
    pipeline.ingestion_agent = type(
        "Ingestion",
        (),
        {"ingest_text": lambda self, *args, **kwargs: IngestionResult(
            object_name="TEST_PROC",
            object_type="PROCEDURE",
            parameters=[],
            raw_code=source,
            original_code=source,
            chunks=[],
            dialect="TSQL",
        )},
    )()
    pipeline._read_source_file = lambda _: source
    pipeline._extract_all_chunks = lambda *args, **kwargs: []
    pipeline._merge_extractions = lambda *args, **kwargs: {
        "conditions": [], "decision_chains": [], "loops": [],
        "tables_read": [], "tables_written": [], "table_operations": [],
        "calculations": [], "exception_handling": [], "ambiguities": [],
    }
    pipeline.synthesizer_agent = _CoverageSynthesizer(revised_rules, fail_revision)
    class _Formatter:
        def __init__(self):
            self.synthesis_data = []

        def format(self, **kwargs):
            self.synthesis_data.append(kwargs["synthesis"].data)
            return "report"

        def format_verification(self, **kwargs):
            return "verification"

    pipeline.formatter_agent = _Formatter()
    pipeline._reconciliation_review_findings = lambda _: []

    class _Reconciliation:
        coverage = {}
        quality = {}
        records = []
        contradictions = []

        def to_dict(self):
            return {}

    class _CanonicalIR:
        @classmethod
        def from_pipeline(cls, **kwargs):
            return cls()

        def to_dict(self):
            return {}

    monkeypatch.setattr(pipeline_module, "reconcile_deterministic_evidence", lambda **kwargs: _Reconciliation())
    monkeypatch.setattr(pipeline_module, "CanonicalBusinessIR", _CanonicalIR)
    result = pipeline.run("sample.sql", dialect="tsql")
    return pipeline, result


def test_empty_synthesis_triggers_revision_and_uses_revised_llm_rules(monkeypatch):
    source = "UPDATE accounts SET provision_amount = balance * rate"
    revised = [{
        "rule_name": "Calculate provision amount",
        "condition": "account is eligible",
        "action": "Multiply balance by rate",
        "output_field": "provision_amount",
        "source_evidence": [source],
        "fields_affected": ["provision_amount"],
    }]
    pipeline, result = _run_coverage_pipeline(monkeypatch, source, revised)
    synthesizer = pipeline.synthesizer_agent
    assert synthesizer.synthesize_calls == 1
    assert len(synthesizer.revise_calls) == 1
    assert "provision_amount" in synthesizer.revise_calls[0]["gaps"][0].snippet
    assert result.report == "report"
    assert pipeline.formatter_agent.synthesis_data[-1]["business_rules"] == revised
    assert find_coverage_gaps(source, pipeline.formatter_agent.synthesis_data[-1]["business_rules"]) == []


def test_thin_synthesis_revises_uncovered_branch_and_finishes_covered(monkeypatch):
    source = """UPDATE accounts SET risk_band = CASE
WHEN score < 50 THEN 'LOW'
WHEN score >= 50 THEN 'HIGH'
END"""
    revised = [{
        "rule_name": "Assign risk band",
        "condition": "score determines the band",
        "action": "Assign LOW below 50 and HIGH at or above 50",
        "output_field": "risk_band",
        "source_evidence": [
            "risk_band = CASE", "score < 50 THEN 'LOW'", "score >= 50 THEN 'HIGH'", "END",
        ],
        "fields_affected": ["risk_band"],
    }]
    pipeline, _ = _run_coverage_pipeline(monkeypatch, source, revised)
    synthesizer = pipeline.synthesizer_agent
    assert len(synthesizer.revise_calls) == 1
    assert synthesizer.revise_calls[0]["gaps"]
    assert pipeline.formatter_agent.synthesis_data[-1]["business_rules"] == revised
    assert find_coverage_gaps(source, revised) == []


def test_unanticipated_while_assignment_is_sent_to_llm_review(monkeypatch):
    source = """WHILE pending_count > 0
SET pending_count = pending_count - 1
SET processed_count = processed_count + 1"""
    revised = [{
        "rule_name": "Process pending records",
        "condition": "pending records remain",
        "action": "Process each pending record and increment the processed count",
        "output_field": "processed_count",
        "source_evidence": ["pending_count = pending_count - 1", "processed_count = processed_count + 1"],
        "fields_affected": ["processed_count"],
    }]
    pipeline, _ = _run_coverage_pipeline(monkeypatch, source, revised)
    assert pipeline.synthesizer_agent.revise_calls
    assert find_coverage_gaps(source, revised) == []


def test_failed_bounded_revision_reports_gap_without_fabricating_rule(monkeypatch):
    source = "UPDATE accounts SET provision_amount = balance * rate"
    pipeline, result = _run_coverage_pipeline(monkeypatch, source, [], fail_revision=True, retries=2)
    assert len(pipeline.synthesizer_agent.revise_calls) == 2
    assert pipeline.synthesizer_agent.revised_rules == []
    assert any(
        "Possible unreviewed decision logic" in item
        for item in pipeline.formatter_agent.synthesis_data[-1]["ambiguities"]
    )


def test_format_gap_for_ambiguity_never_fabricates_business_meaning():
    gap = CoverageGap(line_start=10, line_end=12, snippet="CASE WHEN x THEN y END", keywords=["CASE", "WHEN"])
    text = format_gap_for_ambiguity(gap)
    assert "10-12" in text
    assert "review" in text.lower()
    # Must not assert what the logic *means* - only that it needs review.
    assert "business rule" not in text.lower() or "confirm" in text.lower()
