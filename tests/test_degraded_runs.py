"""Regression tests for the "degraded run" signal (audit fix: a chunk
extraction failure already degraded gracefully to empty evidence for that
chunk, but nothing told a report reader that had happened - a report
missing content after a transient LLM failure looked identical to a fully
clean one). These exercise the real production path end-to-end
(`LogicRulesExtractorPipeline.run()`, `ReportFormatterAgent._degraded_run_banner`)
against fake, OpenAI-shaped clients that can be scripted to fail specific
calls - no live model call - mirroring the pattern in
tests/test_extraction_telemetry.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.llm_response_cache import PersistentLLMResponseCache
from src.extraction.logic_extractor import LogicExtractionAgent
from src.ingestion.ingestion import CodeIngestionAgent
from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent
from pipeline import LogicRulesExtractorPipeline

SAMPLE = Path(__file__).resolve().parent.parent / "samples/PRO.SMA_MARKING_12122023.StoredProcedure.sql"


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content, finish_reason):
        self.message = _FakeMessage(content)
        self.finish_reason = finish_reason


class _FakeUsage:
    def __init__(self, prompt_tokens=100, completion_tokens=50, total_tokens=150):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class _FakeResponse:
    def __init__(self, content, finish_reason="stop"):
        self.choices = [_FakeChoice(content, finish_reason)]
        self.usage = _FakeUsage()


def _extraction_json() -> str:
    return json.dumps({
        "conditions": [], "decision_chains": [], "loops": [],
        "tables_read": [], "tables_written": [], "calculations": [],
        "exception_handling": [], "ambiguities": [],
    })


def _synthesis_json() -> str:
    return json.dumps({
        "purpose_summary": "Demo procedure.", "step_by_step_flow": [], "business_rules": [],
        "calculations": [], "exception_handling_summary": "", "ambiguities": [],
    })


def _synthesis_json_with_one_rule() -> str:
    return json.dumps({
        "purpose_summary": "Demo procedure.", "step_by_step_flow": [],
        "business_rules": [{
            "rule_id": "r1",
            "rule_name": "Classify demo status",
            "output_field": "DemoStatus",
            "decision_logic_rows": [
                {"condition": "Score > 90", "outcome": "'HIGH'"},
                {"condition": "ELSE", "outcome": "'LOW'"},
            ],
        }],
        "calculations": [], "exception_handling_summary": "", "ambiguities": [],
    })


def _is_extraction_prompt(system_text: str) -> bool:
    return "decision_chains" in system_text and "business_rules" not in system_text


class _ScriptedCompletions:
    """Fake `client.chat.completions`. `extraction_script`/`synthesis_script`
    are lists of callables consulted in call order for that stage only
    (`Exception` instances are raised instead of returning a response);
    once exhausted, later calls of that stage get a clean response so a
    test only needs to script the one call it cares about.
    """

    def __init__(self, extraction_script=None, synthesis_script=None):
        self.extraction_script = list(extraction_script or [])
        self.synthesis_script = list(synthesis_script or [])
        self.extraction_calls = 0
        self.synthesis_calls = 0

    def create(self, **kwargs):
        system_text = kwargs["messages"][0]["content"]
        if _is_extraction_prompt(system_text):
            self.extraction_calls += 1
            if self.extraction_calls <= len(self.extraction_script):
                outcome = self.extraction_script[self.extraction_calls - 1]
                if isinstance(outcome, Exception):
                    raise outcome
                return _FakeResponse(*outcome) if isinstance(outcome, tuple) else _FakeResponse(outcome)
            return _FakeResponse(_extraction_json())
        self.synthesis_calls += 1
        if self.synthesis_calls <= len(self.synthesis_script):
            outcome = self.synthesis_script[self.synthesis_calls - 1]
            if isinstance(outcome, Exception):
                raise outcome
            return _FakeResponse(*outcome) if isinstance(outcome, tuple) else _FakeResponse(outcome)
        return _FakeResponse(_synthesis_json())


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, extraction_script=None, synthesis_script=None):
        self.chat = _FakeChat(_ScriptedCompletions(extraction_script, synthesis_script))


class _FakeRetrievalAgent:
    def retrieve_context_text(self, query, k=4):
        return "no context"

    def build_or_load(self, force_rebuild=False):
        pass


def _make_pipeline(client, single_pass_token_budget=1):
    """Build a real `LogicRulesExtractorPipeline` wired to a fake client -
    mirrors `__init__` exactly, without touching real network/credentials.
    `single_pass_token_budget=1` forces the chunked extraction path by
    default, since a "failed chunk N of M" scenario needs M > 1.
    """
    pipeline = LogicRulesExtractorPipeline.__new__(LogicRulesExtractorPipeline)
    pipeline.max_coverage_retries = 0
    pipeline.single_pass_token_budget = single_pass_token_budget
    pipeline.model_name = "demo-model"
    pipeline.retrieval_k = 4
    pipeline.chunk_workers = 1
    pipeline.dialect = "auto"
    pipeline.seed = 0
    pipeline.project_root = Path(__file__).resolve().parent.parent
    pipeline.pipeline_version = "test"
    pipeline.provider = "openai"
    pipeline.response_cache = PersistentLLMResponseCache(enabled=False)
    pipeline.client = client
    pipeline.model_output_ceiling = 20000
    pipeline.ingestion_agent = CodeIngestionAgent(max_chunk_chars=6000, dialect="auto")
    pipeline.retrieval_agent = _FakeRetrievalAgent()
    pipeline.extraction_agent = LogicExtractionAgent(
        client=client, model="demo-model", temperature=0.1, seed=0, provider="openai",
        response_cache=pipeline.response_cache, max_tokens=2000, hard_max_output_tokens=20000,
    )
    pipeline.synthesizer_agent = RuleSynthesizerAgent(
        client=client, model="demo-model", temperature=0.1, seed=0, provider="openai",
        response_cache=pipeline.response_cache, max_tokens=2000, hard_max_output_tokens=20000,
    )
    pipeline.formatter_agent = ReportFormatterAgent()
    return pipeline


def test_all_calls_succeeding_produces_no_degraded_banner():
    client = _FakeClient()
    pipeline = _make_pipeline(client)

    result = pipeline.run(str(SAMPLE))

    assert client.chat.completions.extraction_calls >= 2, "sample must chunk into 2+ pieces"
    assert "DEGRADED RUN" not in result.report


def test_one_failed_extraction_chunk_is_tracked_but_not_shown_in_business_report():
    # The first chunk extraction call fails permanently; every other call
    # (remaining chunks, synthesis) succeeds normally. Per explicit client
    # direction, the business report never shows a degraded-run signal -
    # but the underlying telemetry must still correctly track the failure,
    # since that data is what a verification/diagnostic consumer relies on.
    client = _FakeClient(extraction_script=[RuntimeError("simulated rate-limit exhaustion")])
    pipeline = _make_pipeline(client)

    result = pipeline.run(str(SAMPLE))

    assert client.chat.completions.extraction_calls >= 2
    assert "DEGRADED RUN" not in result.report
    assert "Needs Review" not in result.report
    telemetry = result.ingestion.run_metadata.telemetry
    assert telemetry["degraded"] is True
    assert telemetry["failed_chunk_count"] == 1


def test_failed_synthesis_call_is_tracked_but_not_shown_in_business_report():
    # SMA_MARKING is large enough to always require sectioned synthesis, so
    # this exercises _run_section's retry-once-on-transient-failure path
    # (added after this test was first written): a single scripted failure
    # is no longer enough to degrade the section, since the retry attempt
    # gets the default clean response and recovers - so exhaust both
    # attempts (2 consecutive failures) to still see the section degrade.
    # The business report itself must show none of this (client direction);
    # the run still completes and the underlying telemetry still tracks it.
    client = _FakeClient(synthesis_script=[
        RuntimeError("simulated timeout"),
        RuntimeError("simulated timeout (retry also failed)"),
    ])
    pipeline = _make_pipeline(client, single_pass_token_budget=500_000)

    result = pipeline.run(str(SAMPLE))

    assert client.chat.completions.synthesis_calls >= 2
    assert "DEGRADED RUN" not in result.report
    assert "Needs Review" not in result.report
    telemetry = result.ingestion.run_metadata.telemetry
    assert telemetry["degraded"] is True
    assert telemetry["failed_section_count"] == 1


def test_one_transient_synthesis_failure_recovers_via_retry_without_degrading():
    """The retry-once behavior itself: a single transient synthesis
    failure (rate limit, timeout) must NOT degrade the report when the
    very next attempt succeeds - only genuinely exhausted failures should
    show the degraded banner."""
    client = _FakeClient(synthesis_script=[RuntimeError("simulated transient rate limit")])
    pipeline = _make_pipeline(client, single_pass_token_budget=500_000)

    result = pipeline.run(str(SAMPLE))

    assert client.chat.completions.synthesis_calls >= 2, "must have retried once"
    assert "DEGRADED RUN" not in result.report


def test_truncated_synthesis_response_still_renders_the_rule_without_any_marker(tmp_path):
    """Root cause 2 (original ask) was to mark a truncated rule's own
    output inline rather than only a run-level footer. Per subsequent,
    more recent explicit client direction, no degraded/"needs review"
    signal - inline or run-level - may appear in the business report at
    all; the reader should see confident, complete business analysis.
    This confirms the rule itself still renders correctly (the content
    that DID arrive from a truncated call is not discarded) with no
    visible marker anywhere in the report, while the underlying
    `degraded`/`llm_call_failed`-style tracking (verified in
    `test_mark_rules_degraded_if_unreliable_tags_the_reason` below and in
    pipeline-level telemetry tests) is untouched. Uses a small, self-
    contained source (rather than the large SMA_MARKING sample used
    elsewhere in this file) so synthesis takes the single-call path and
    this is the only rule in the report. The UPDATE carries no WHERE
    clause so `ensure_statement_coverage`'s deterministic floor (a real,
    separate guarantee unrelated to what this test checks) has nothing
    conditional to synthesize a second rule from.
    """
    small_sql = tmp_path / "small.sql"
    small_sql.write_text(
        "CREATE PROCEDURE dbo.DemoProc\nAS\nBEGIN\n    UPDATE t SET x = 1\nEND\n",
        encoding="utf-8",
    )
    client = _FakeClient(synthesis_script=[(_synthesis_json_with_one_rule(), "length")])
    pipeline = _make_pipeline(client, single_pass_token_budget=500_000)

    result = pipeline.run(str(small_sql), dialect="tsql")

    assert "### R1 — Classify demo status" in result.report
    assert "Needs Review" not in result.report
    assert "needs review" not in result.report.lower()
    assert "DEGRADED RUN" not in result.report


def test_mark_rules_degraded_if_unreliable_tags_the_reason():
    """`degraded_reason` (added alongside the boolean `degraded` flag) must
    distinguish an actual model-capacity failure from other paths that also
    set `degraded` (see `test_coverage_check.
    test_revision_only_degrades_the_genuinely_new_rule_not_echoed_ones` for
    the coverage-gap-review path's own, different reason). Without this,
    report_formatter cannot tell "this rule's own LLM call was truncated"
    apart from "this rule is new output from an otherwise-successful
    targeted review pass" and previously showed the same "truncated or
    failed" wording for both.
    """
    from pipeline import _mark_rules_degraded_if_unreliable
    from src.synthesis.rule_synthesizer import SynthesisResult

    truncated_result = SynthesisResult(
        data={"business_rules": [{"rule_name": "R"}]},
        truncated=True,
    )
    marked = _mark_rules_degraded_if_unreliable(truncated_result)
    assert marked.data["business_rules"][0]["degraded"] is True
    assert marked.data["business_rules"][0]["degraded_reason"] == "truncated"

    failed_result = SynthesisResult(
        data={"business_rules": [{"rule_name": "R"}]},
        synthesis_failed=True,
    )
    marked = _mark_rules_degraded_if_unreliable(failed_result)
    assert marked.data["business_rules"][0]["degraded_reason"] == "synthesis_failed"

    clean_result = SynthesisResult(data={"business_rules": [{"rule_name": "R"}]})
    marked = _mark_rules_degraded_if_unreliable(clean_result)
    assert "degraded" not in marked.data["business_rules"][0]
    assert "degraded_reason" not in marked.data["business_rules"][0]
