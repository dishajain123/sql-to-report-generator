"""Focused regression coverage for extraction-stage LLM telemetry.

Root cause (see docs/SMA_report_root_causes.md, "production-hardening
follow-up" entry): `LogicExtractionAgent.extract()`'s own retry-on-
truncation call was a second, real `client.chat.completions.create(...)`
invocation made with no `tracker.record_call(...)` around it at all -
unlike `RuleSynthesizerAgent`'s equivalent retries, already recorded under
a dedicated `synthesis_retry` stage. Its tokens, and its very existence,
were invisible to telemetry.

These tests exercise the real production code path end-to-end
(`LogicRulesExtractorPipeline.run()`, `LogicExtractionAgent.extract()`,
`LLMTelemetryTracker`, `aggregate_run_telemetry`,
`ReportFormatterAgent._telemetry_section`) against fake, OpenAI-shaped
clients - no live model call - so every assertion is backed by a real,
reproducible invocation count rather than an assumption about the log
output of one past run.
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
from src.telemetry.tracker import LLMTelemetryTracker
from pipeline import LogicRulesExtractorPipeline

SAMPLE = Path(__file__).resolve().parent.parent / "samples/PRO.SMA_MARKING_12122023.StoredProcedure.sql"


# --------------------------------------------------------------------------
# Fake, OpenAI-shaped chat-completions client
# --------------------------------------------------------------------------


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content, finish_reason):
        self.message = _FakeMessage(content)
        self.finish_reason = finish_reason


class _FakeUsage:
    def __init__(self, prompt_tokens, completion_tokens, total_tokens):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class _FakeResponse:
    def __init__(self, content, usage, finish_reason):
        self.choices = [_FakeChoice(content, finish_reason)]
        self.usage = usage


def _extraction_json() -> str:
    return json.dumps({
        "conditions": [], "decision_chains": [], "loops": [],
        "tables_read": [], "tables_written": [], "calculations": [],
        "exception_handling": [], "ambiguities": [],
    })


def _synthesis_json() -> str:
    return json.dumps({
        "purpose_summary": "Demo.", "step_by_step_flow": [], "business_rules": [],
        "calculations": [], "exception_handling_summary": "", "ambiguities": [],
    })


def _is_extraction_prompt(system_text: str) -> bool:
    # The two prompt YAMLs are distinguishable by schema shape - extraction
    # asks for "decision_chains" without ever mentioning "business_rules".
    return "decision_chains" in system_text and "business_rules" not in system_text


class _ScriptedCompletions:
    """Fake `client.chat.completions`. `script` is a list of callables
    (call_index -> _FakeResponse | Exception) consulted in order for
    extraction calls only; synthesis calls always get a clean response so
    tests can isolate extraction-path behavior without also having to
    script synthesis.
    """

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0
        self.extraction_calls = 0
        self.synthesis_calls = 0
        self.call_log = []

    def create(self, **kwargs):
        self.calls += 1
        system_text = kwargs["messages"][0]["content"]
        usage = _FakeUsage(500 + self.calls, 50 + self.calls, 550 + 2 * self.calls)
        if _is_extraction_prompt(system_text):
            self.extraction_calls += 1
            self.call_log.append(("extraction", self.extraction_calls))
            if self.extraction_calls <= len(self.script):
                outcome = self.script[self.extraction_calls - 1]
                if isinstance(outcome, Exception):
                    raise outcome
                content, finish_reason = outcome
                return _FakeResponse(content, usage, finish_reason)
            return _FakeResponse(_extraction_json(), usage, "stop")
        self.synthesis_calls += 1
        self.call_log.append(("synthesis", self.synthesis_calls))
        return _FakeResponse(_synthesis_json(), usage, "stop")


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, script):
        self.chat = _FakeChat(_ScriptedCompletions(script))


class _FakeRetrievalAgent:
    def retrieve_context_text(self, query, k=4):
        return "no context"

    def build_or_load(self, force_rebuild=False):
        pass


def _make_pipeline(client, single_pass_token_budget=500_000):
    """Build a real `LogicRulesExtractorPipeline` wired to fake clients,
    mirroring exactly how `__init__` constructs each agent, without ever
    touching real network/AWS credentials.
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


def _telemetry_stage_breakdown(verification_report: str) -> dict:
    """Parse the "## LLM Telemetry" stage table out of a rendered
    verification report into {stage: calls} for easy assertions.
    """
    section = verification_report.split("## LLM Telemetry", 1)[1].split("## ", 1)[0]
    breakdown = {}
    for line in section.splitlines():
        if not line.startswith("| ") or line.startswith("| Item") or line.startswith("| Stage") or set(line.strip()) <= {"|", "-", " ", ":"}:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[1].isdigit():
            breakdown[cells[0]] = int(cells[1])
    return breakdown


# --------------------------------------------------------------------------
# 1. A normal extraction call creates exactly one `extraction` record
# --------------------------------------------------------------------------


def test_normal_extraction_call_creates_one_extraction_telemetry_record():
    tracker = LLMTelemetryTracker()
    client = _FakeClient(script=[(_extraction_json(), "stop")])
    agent = LogicExtractionAgent(
        client=client, model="demo-model", temperature=0.1, seed=0, provider="openai",
        telemetry_tracker=tracker, max_tokens=2000, hard_max_output_tokens=20000,
    )

    result = agent.extract(
        chunk_id="chunk_1", chunk_kind="main_body", code_chunk="UPDATE t SET x=1",
        rag_context="", object_type="PROCEDURE", object_name="demo", dialect="tsql",
    )

    assert result.parse_error == ""
    assert client.chat.completions.extraction_calls == 1
    snapshot = tracker.snapshot("run").to_dict()
    assert snapshot["call_count"] == 1
    assert snapshot["stage_breakdown"]["extraction"]["call_count"] == 1
    tokens = snapshot["stage_breakdown"]["extraction"]["token_usage"]
    assert tokens["prompt_tokens"] and tokens["completion_tokens"] and tokens["total_tokens"]


# --------------------------------------------------------------------------
# 2. Chunked extraction records each actual invocation, one per chunk
# --------------------------------------------------------------------------


def test_chunked_extraction_records_telemetry_for_each_chunk():
    client = _FakeClient(script=[])  # every extraction call gets a clean response
    pipeline = _make_pipeline(client, single_pass_token_budget=1)  # force chunked path

    result = pipeline.run(str(SAMPLE))
    breakdown = _telemetry_stage_breakdown(result.verification_report)

    assert client.chat.completions.extraction_calls >= 2, "the SMA sample must chunk into 2+ pieces"
    assert breakdown.get("extraction") == client.chat.completions.extraction_calls
    assert "extraction_retry" not in breakdown  # nothing truncated in this scenario


# --------------------------------------------------------------------------
# 3. Retries and the single-pass -> chunked fallback do not disappear
# --------------------------------------------------------------------------


def test_full_source_truncation_retry_and_chunked_fallback_all_appear_in_telemetry():
    """Reproduces the exact real-world shape from the live SMA verification
    report this fix was traced against: the single-pass, whole-source
    extraction attempt truncates (`finish_reason == "length"`), its own
    retry-on-truncation ALSO comes back unusable, `chunk_extractions[0].
    parse_error` stays set, and `pipeline.py` falls back to per-chunk
    extraction. Every one of those real calls - the failed single-pass
    attempt, its retry, and every chunked-path call - must appear in
    telemetry; none may be silently dropped.
    """
    truncated = ('{"conditions": [', "length")
    script = [truncated, truncated]  # single-pass call, then its own retry - both truncated
    client = _FakeClient(script=script)
    pipeline = _make_pipeline(client, single_pass_token_budget=500_000)  # single-pass attempted first

    result = pipeline.run(str(SAMPLE))
    breakdown = _telemetry_stage_breakdown(result.verification_report)

    # 1 single-pass attempt + 1 retry of it + N real chunked-path calls.
    total_extraction_related_calls = client.chat.completions.extraction_calls
    assert total_extraction_related_calls > 2, "must have fallen back to chunked extraction"
    assert breakdown.get("extraction", 0) >= 1
    assert breakdown.get("extraction_retry", 0) >= 1
    recorded_extraction_total = breakdown.get("extraction", 0) + breakdown.get("extraction_retry", 0)
    assert recorded_extraction_total == total_extraction_related_calls, (
        "every real extraction-family call must be represented in telemetry - "
        f"client made {total_extraction_related_calls} calls, telemetry recorded {recorded_extraction_total}"
    )


# --------------------------------------------------------------------------
# 4. Synthesis telemetry continues working unchanged alongside extraction
# --------------------------------------------------------------------------


def test_synthesis_telemetry_still_recorded_alongside_extraction():
    client = _FakeClient(script=[])
    pipeline = _make_pipeline(client, single_pass_token_budget=1)

    result = pipeline.run(str(SAMPLE))
    breakdown = _telemetry_stage_breakdown(result.verification_report)

    assert breakdown.get("synthesis", 0) == client.chat.completions.synthesis_calls
    assert breakdown.get("synthesis", 0) > 0


# --------------------------------------------------------------------------
# 5. No duplicate telemetry record for a single real invocation
# --------------------------------------------------------------------------


def test_no_duplicate_telemetry_record_per_invocation():
    client = _FakeClient(script=[])
    pipeline = _make_pipeline(client, single_pass_token_budget=1)

    result = pipeline.run(str(SAMPLE))
    breakdown = _telemetry_stage_breakdown(result.verification_report)

    total_real_calls = client.chat.completions.calls
    total_recorded_calls = sum(breakdown.values())
    assert total_recorded_calls == total_real_calls, (
        f"telemetry recorded {total_recorded_calls} calls for {total_real_calls} real invocations "
        "- every invocation must map to exactly one record, never more, never fewer"
    )
