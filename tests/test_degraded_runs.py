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


def test_one_failed_extraction_chunk_sets_degraded_banner_with_correct_count():
    # The first chunk extraction call fails permanently; every other call
    # (remaining chunks, synthesis) succeeds normally.
    client = _FakeClient(extraction_script=[RuntimeError("simulated rate-limit exhaustion")])
    pipeline = _make_pipeline(client)

    result = pipeline.run(str(SAMPLE))

    assert client.chat.completions.extraction_calls >= 2
    assert "DEGRADED RUN" in result.report
    assert "1 chunk extraction call(s)" in result.report
    assert "Re-run to attempt full coverage." in result.report


def test_failed_synthesis_call_sets_degraded_banner_and_report_still_completes():
    # A small object takes the single-call synthesis path (no chunking
    # needed for extraction to succeed) - only the synthesis call fails.
    client = _FakeClient(synthesis_script=[RuntimeError("simulated timeout")])
    pipeline = _make_pipeline(client, single_pass_token_budget=500_000)

    result = pipeline.run(str(SAMPLE))

    assert client.chat.completions.synthesis_calls >= 1
    assert "DEGRADED RUN" in result.report
    assert "rule synthesis section(s)" in result.report or "1 rule synthesis section(s)" in result.report
