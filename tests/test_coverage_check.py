from pathlib import Path

from src.validation.coverage_check import (
    CoverageGap,
    find_coverage_gaps,
    find_decision_points,
    format_consolidated_gap_ambiguity,
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
    final_rules = pipeline.formatter_agent.synthesis_data[-1]["business_rules"]
    assert all(rule["rule_id"] for rule in final_rules)
    assert [{k: v for k, v in rule.items() if k != "rule_id"} for rule in final_rules] == revised
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
    final_rules = pipeline.formatter_agent.synthesis_data[-1]["business_rules"]
    # Preserve authored content and allocate an identity for the revised rule.
    assert final_rules[0]["rule_id"]
    assert {k: v for k, v in final_rules[0].items() if k != "rule_id"} == revised[0]
    # ...and the pipeline's own deterministic guarantee
    # (`RuleSynthesizerAgent.ensure_decision_chain_coverage`) appends a
    # Decision Logic table for `risk_band` regardless of whether the model
    # supplied one, because the source's CASE ladder is unambiguous
    # (two explicit branches and the implicit NULL fallback) and the stubbed `revise()` here - unlike the real
    # `RuleSynthesizerAgent` - never populates `decision_logic_rows` itself.
    assert len(final_rules) == 2
    assert final_rules[1]["output_field"] == "risk_band"
    assert final_rules[1]["decision_logic_rows"] == [
        {"condition": "score < 50", "outcome": "'LOW'"},
        {"condition": "score >= 50", "outcome": "'HIGH'"},
        {"condition": "ELSE", "outcome": "NULL"},
    ]
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
    # Wording shortened (no more "Possible unreviewed decision logic" +
    # quoted snippet) - see `format_gap_for_ambiguity` in coverage_check.py.
    assert any(
        "not referenced by any synthesized rule" in item
        for item in pipeline.formatter_agent.synthesis_data[-1]["ambiguities"]
    )


class _NonEmptyInitialSynthesizer:
    """Like `_CoverageSynthesizer`, but `synthesize()` returns a real,
    already-complete rule (not empty) - so `revise()` can be exercised
    echoing that rule back unchanged alongside one genuinely new rule for
    the gap, the scenario `_CoverageSynthesizer` (always-empty initial
    synthesis) cannot cover.
    """

    def __init__(self, existing_rule, new_rule):
        self.existing_rule = existing_rule
        self.new_rule = new_rule
        self.revise_calls = []

    def synthesize(self, **kwargs):
        return SynthesisResult(
            data={
                "purpose_summary": "initial",
                "step_by_step_flow": [],
                "business_rules": [dict(self.existing_rule)],
                "calculations": [],
                "exception_handling_summary": "",
                "ambiguities": [],
            }
        )

    def revise(self, **kwargs):
        self.revise_calls.append(kwargs)
        # Echoes the existing rule back byte-for-byte (as the real model is
        # instructed to for still-correct rules) and adds one new rule for
        # the newly-reviewed gap.
        return SynthesisResult(
            data={
                "business_rules": [dict(self.existing_rule), dict(self.new_rule)],
                "ambiguities": [],
            }
        )


def test_revision_only_degrades_the_genuinely_new_rule_not_echoed_ones(monkeypatch):
    # Regression for a real bug found via live-run analysis: whenever the
    # coverage-gap revision loop ran at all, EVERY rule it returned -
    # including already-accepted rules the model was only asked to echo
    # back unchanged - was stamped `degraded: True` and rendered as
    # "possibly incomplete ... truncated or failed", even on a run where
    # every single LLM call (synthesis and revision alike) succeeded
    # cleanly. Only a rule that is actually NEW relative to what
    # synthesize() already had should ever be flagged from this path.
    source = (
        "UPDATE accounts SET tier = 'GOLD' WHERE balance > 1000\n"
        "IF fraud_flag = 1\n"
        "    UPDATE accounts SET blocked = 1\n"
    )
    existing_rule = {
        "rule_name": "Assign gold tier",
        "condition": "balance > 1000",
        "action": "Set tier to GOLD",
        "output_field": "tier",
        "source_evidence": ["balance > 1000"],
        "fields_affected": ["tier"],
    }
    new_rule = {
        "rule_name": "Block on fraud flag",
        "condition": "fraud_flag = 1",
        "action": "Block the account",
        "output_field": "blocked",
        "source_evidence": ["fraud_flag = 1"],
        "fields_affected": ["blocked"],
    }
    pipeline = LogicRulesExtractorPipeline.__new__(LogicRulesExtractorPipeline)
    pipeline.dialect = "tsql"
    pipeline.model_name = "test-model"
    pipeline.provider = "test"
    pipeline.project_root = Path(__file__).resolve().parent.parent
    pipeline.chunk_workers = 1
    pipeline.max_coverage_retries = 2
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
    synthesizer = _NonEmptyInitialSynthesizer(existing_rule, new_rule)
    pipeline.synthesizer_agent = synthesizer

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
    # `find_coverage_gaps` is coverage_check.py's own real lexical scanner -
    # it has its own dedicated test suite (the rest of this file) and isn't
    # what this test is about. Stubbing it isolates exactly the code this
    # test targets (pipeline.py's post-revision degraded-marking) from that
    # scanner's own heuristics (e.g. its coarse "parent branch" region
    # matching, which would otherwise make constructing a source whose
    # first statement is cited but second is not needlessly fragile).
    gap_calls = {"count": 0}

    def _fake_find_coverage_gaps(raw_code, rules):
        gap_calls["count"] += 1
        if gap_calls["count"] == 1:
            return [CoverageGap(line_start=2, line_end=3, snippet="IF fraud_flag = 1", keywords=["IF"])]
        return []

    monkeypatch.setattr(pipeline_module, "find_coverage_gaps", _fake_find_coverage_gaps)
    pipeline.run("sample.sql", dialect="tsql")

    assert synthesizer.revise_calls
    final_rules = pipeline.formatter_agent.synthesis_data[-1]["business_rules"]
    by_name = {rule["rule_name"]: rule for rule in final_rules}
    assert by_name["Assign gold tier"].get("degraded") is not True
    assert by_name["Block on fraud flag"].get("degraded") is True
    assert by_name["Block on fraud flag"].get("degraded_reason") == "gap_review"


def test_format_gap_for_ambiguity_never_fabricates_business_meaning():
    gap = CoverageGap(line_start=10, line_end=12, snippet="CASE WHEN x THEN y END", keywords=["CASE", "WHEN"])
    text = format_gap_for_ambiguity(gap)
    assert "10-12" in text
    assert "review" in text.lower()
    # Must not assert what the logic *means* - only that it needs review.
    assert "business rule" not in text.lower() or "confirm" in text.lower()


def test_consolidated_gap_ambiguity_does_not_repeat_a_shared_line_range():
    # Regression for a real live-generated report
    # (samples/output/6_PRO.SMA_MARKING...): two distinct gaps (an INSERT
    # keyword and a nested CASE/WHEN keyword) landed on the exact same
    # line range, and the un-deduped preview read "lines 610-651, 610-651,
    # ..." - the same range listed twice in one sentence, which reads as a
    # mistake even though both gaps are genuinely separate unresolved
    # constructs. The total count must still reflect every gap.
    gaps = [
        CoverageGap(line_start=610, line_end=651, snippet="INSERT INTO t ...", keywords=["INSERT"]),
        CoverageGap(line_start=610, line_end=651, snippet="CASE WHEN x THEN y END", keywords=["CASE", "WHEN"]),
        CoverageGap(line_start=693, line_end=695, snippet="UPDATE t SET x=1", keywords=["UPDATE"]),
    ]
    text = format_consolidated_gap_ambiguity(gaps)
    assert text.count("610-651") == 1
    assert "693-695" in text
    assert "(3 total)" in text


def test_where_gated_blocks_get_real_per_line_scoring_not_blanket_coverage(caplog):
    # Regression test built from the real client-corpus finding: the
    # pipeline's own logs on samples/02_SMA_Stage_Marking_Simple.sql showed
    # EVERY coverage block logging `overlap_ratio=0.000 matched_rule=none
    # uncovered=False` - a fabricated "no match" that actually meant "the
    # whole block was blanket-covered before any real per-line scoring ran".
    # Confirmed by A/B testing with the fix's exclusion line removed: with
    # the exact rule set below, EVERY block - including two
    # `UPDATE PRO.RunStatus` statements that no rule mentions at all -
    # logged as blanket-"covered", which is a structural no-op: the gate
    # cannot distinguish a genuinely-cited block from a genuinely-uncited
    # one. With the fix, WHERE-gated blocks get real per-line scoring
    # (a specific matched_rule index and a real overlap_ratio) instead.
    source = Path("samples/02_SMA_Stage_Marking_Simple.sql").read_text(encoding="utf-8")
    rules = [
        {
            "rule_name": "Classify SMA stage by overdue days",
            "source_evidence": ["A.OverdueDays BETWEEN 1 AND 30"],
            "output_field": "SmaStage",
            "fields_affected": ["SmaStage"],
            "condition": "OverdueDays BETWEEN 1 AND 30",
            "action": "Sets SmaStage",
        },
        {
            "rule_name": "Flag SMA status",
            "source_evidence": ["A.SmaStage IS NOT NULL"],
            "output_field": "FlagSma",
            "fields_affected": ["FlagSma"],
            "condition": "SmaStage IS NOT NULL",
            "action": "Sets FlagSma",
        },
        {
            "rule_name": "Attribute overdue reason by facility type",
            "source_evidence": ["A.FacilityType IN ('CC', 'OD')"],
            "output_field": "SmaReason",
            "fields_affected": ["SmaReason"],
            "condition": "FacilityType IN ('CC','OD')",
            "action": "Sets SmaReason",
        },
        {
            "rule_name": "Calculate SMA stage start date",
            "source_evidence": ["A.FlagSma = 'Y'"],
            "output_field": "SmaStageDate",
            "fields_affected": ["SmaStageDate"],
            "condition": "FlagSma='Y'",
            "action": "Sets SmaStageDate",
        },
        {
            "rule_name": "Clear SMA status for non-overdue accounts",
            "source_evidence": ["A.OverdueDays = 0"],
            "output_field": "SmaStage",
            "fields_affected": ["SmaStage", "FlagSma", "SmaReason"],
            "condition": "OverdueDays=0",
            "action": "Clears SMA fields",
        },
    ]
    with caplog.at_level("INFO", logger="src.validation.coverage_check"):
        find_coverage_gaps(source, rules)

    block_logs = [r.message for r in caplog.records if r.message.startswith("Coverage block")]
    assert block_logs, "Expected coverage-check to log per-block results."

    # The two blocks tied to a real, cited rule condition (lines 25-30 for
    # rule 1, 38-41 for rule 2) must show a specific matched rule and a
    # nonzero ratio now - not the fabricated "matched_rule=none" the
    # original logs showed for every single block in this file.
    rule1_block = next(msg for msg in block_logs if "lines=25-30" in msg)
    rule2_block = next(msg for msg in block_logs if "lines=38-41" in msg)
    assert "matched_rule=none" not in rule1_block, rule1_block
    assert "matched_rule=none" not in rule2_block, rule2_block

    # The two RunStatus updates (lines 75-76, 82-83) are not described by
    # ANY of the five rules above - a working gate must be able to say so
    # via real per-line scoring, rather than blanket-covering them as a
    # side effect of an unrelated rule's evidence matching elsewhere in the
    # region text.
    runstatus_blocks = [msg for msg in block_logs if "lines=75-76" in msg or "lines=82-83" in msg]
    assert runstatus_blocks
    for msg in runstatus_blocks:
        assert "region_covered=True" not in msg, (
            f"RunStatus block should not be blanket-covered by an unrelated rule's evidence: {msg}"
        )


def test_semicolon_free_statements_do_not_balloon_into_one_giant_gap():
    # Regression test for a real production bug: a report showed a single
    # "possible unreviewed decision logic" finding spanning lines 36-776 of
    # a 776-line procedure. Root cause was two-fold, both in
    # _dml_predicate_tokens_by_line: (1) statement boundaries were found by
    # splitting on ';', and this codebase's T-SQL mostly has NO semicolons
    # at all, so a whole semicolon-free procedure body was treated as ONE
    # statement, and the first WHERE clause found "swallowed" everything
    # after it as its own predicate; (2) even after using real
    # (keyword-based) statement boundaries, an off-by-one attributed a
    # statement's own trailing blank/comment lines - and the NEXT
    # statement's first line - to the wrong statement. Ten independent,
    # unrelated UPDATEs sharing one repeated WHERE guard (a common pattern
    # in this codebase, e.g. "WHERE FlgSma = 'Y'") must each be reported
    # as their own small gap, never merged into one file-spanning one.
    blocks = [
        f"\nUPDATE A\nSET A.Field{i} = CASE WHEN A.X{i} > 0 THEN 1 ELSE 0 END\n"
        f"FROM PRO.AccountCal A\nWHERE A.FlgSma = 'Y' "
        for i in range(10)
    ]
    source = "\n".join(blocks)
    gaps = find_coverage_gaps(source, [])
    assert len(gaps) == 10
    for gap in gaps:
        assert gap.line_end - gap.line_start < 10, (
            f"Gap {gap.line_start}-{gap.line_end} spans too many lines - "
            "statement boundaries have likely collapsed into one again."
        )


def test_dml_predicate_tokens_attribute_the_next_statements_own_line_correctly():
    # Narrower regression test isolating just the off-by-one: the sample
    # corpus file's Rule 2 (no WHERE clause of its own) must never have its
    # own "UPDATE A" anchor line attributed to Rule 1's (WHERE-gated)
    # predicate tokens just because Rule 1's statement span's trailing
    # blank/comment padding extends up to that boundary.
    from src.validation.coverage_check import _dml_predicate_tokens_by_line
    from pathlib import Path

    source = Path("samples/02_SMA_Stage_Marking_Simple.sql").read_text(encoding="utf-8")
    predicate_lines = _dml_predicate_tokens_by_line(source)
    rule2_update_line = next(
        i for i, line in enumerate(source.splitlines(), start=1)
        if line.strip() == "UPDATE A" and i > 30 and i < 45
    )
    assert rule2_update_line not in predicate_lines, (
        f"Line {rule2_update_line} (Rule 2's own UPDATE, which has no WHERE clause) "
        "must not be attributed to a different statement's predicate."
    )