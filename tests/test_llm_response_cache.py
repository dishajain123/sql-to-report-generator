"""
Regression tests for persistent exact LLM response caching.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.llm_response_cache import PersistentLLMResponseCache
from src.extraction.logic_extractor import LogicExtractionAgent
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent
from src.telemetry.tracker import LLMTelemetryTracker


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int, total_tokens: int):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class _FakeCompletionResponse:
    def __init__(self, content: str, usage: _FakeUsage | dict | None = None):
        self.choices = [_FakeChoice(content)]
        self.usage = usage


class _FakeCompletions:
    def __init__(self, canned_response: str, usage: _FakeUsage | dict | None = None):
        self.canned_response = canned_response
        self.usage = usage
        self.calls = 0
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.calls += 1
        self.last_call_kwargs = kwargs
        return _FakeCompletionResponse(self.canned_response, usage=self.usage)


class _FakeChat:
    def __init__(self, canned_response: str, usage: _FakeUsage | dict | None = None):
        self.completions = _FakeCompletions(canned_response, usage=usage)


class _FakeClient:
    def __init__(self, canned_response: str, usage: _FakeUsage | dict | None = None):
        self.chat = _FakeChat(canned_response, usage=usage)


def _extraction_response() -> str:
    return json.dumps(
        {
            "conditions": [],
            "decision_chains": [],
            "loops": [],
            "tables_read": [],
            "tables_written": [],
            "calculations": [],
            "exception_handling": [],
            "ambiguities": [],
        }
    )


def _synthesis_response() -> str:
    return json.dumps(
        {
            "purpose_summary": "Demo.",
            "step_by_step_flow": [],
            "business_rules": [],
            "calculations": [],
            "exception_handling_summary": "",
            "ambiguities": [],
        }
    )


def _make_extraction_agent(cache: PersistentLLMResponseCache, client: _FakeClient, tracker=None, **kwargs):
    return LogicExtractionAgent(
        client=client,
        model=kwargs.get("model", "demo-model"),
        temperature=kwargs.get("temperature", 0.1),
        seed=kwargs.get("seed", 0),
        provider=kwargs.get("provider", "openai"),
        telemetry_tracker=tracker,
        response_cache=cache,
    )


def _make_synthesis_agent(cache: PersistentLLMResponseCache, client: _FakeClient, tracker=None, **kwargs):
    return RuleSynthesizerAgent(
        client=client,
        model=kwargs.get("model", "demo-model"),
        temperature=kwargs.get("temperature", 0.1),
        seed=kwargs.get("seed", 0),
        provider=kwargs.get("provider", "openai"),
        response_cache=cache,
    )


def _run_extraction(agent: LogicExtractionAgent):
    return agent.extract(
        chunk_id="chunk_1",
        chunk_kind="main_body",
        code_chunk="BEGIN NULL; END;",
        rag_context="context",
        object_type="PROCEDURE",
        object_name="demo_proc",
        chunk_context=["main_body"],
        embedded_sql=[],
        dialect="oracle",
    )


def _run_synthesis(agent: RuleSynthesizerAgent):
    return agent.synthesize(
        object_name="demo_proc",
        object_type="PROCEDURE",
        parameter_summary="No parameters.",
        merged_extraction={
            "conditions": [],
            "decision_chains": [],
            "loops": [],
            "tables_read": [],
            "tables_written": [],
            "calculations": [],
            "exception_handling": [],
            "ambiguities": [],
        },
        dialect="oracle",
        raw_source="BEGIN NULL; END;",
    )


def test_successful_extraction_response_is_persisted_and_reused(tmp_path):
    cache = PersistentLLMResponseCache(path=tmp_path / "llm_cache.sqlite3", enabled=True)
    first_client = _FakeClient(_extraction_response(), usage={"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15})
    first_agent = _make_extraction_agent(cache, first_client)

    first_result = _run_extraction(first_agent)

    assert first_client.chat.completions.calls == 1
    assert first_result.parse_error == ""

    second_client = _FakeClient(_extraction_response(), usage={"prompt_tokens": 99, "completion_tokens": 1, "total_tokens": 100})
    second_agent = _make_extraction_agent(cache, second_client)
    second_result = _run_extraction(second_agent)

    assert second_client.chat.completions.calls == 0
    assert second_result.data == first_result.data
    assert second_result.raw_response == first_result.raw_response


def test_identical_request_hits_cache_without_provider_call(tmp_path):
    cache = PersistentLLMResponseCache(path=tmp_path / "llm_cache.sqlite3", enabled=True)
    tracker = LLMTelemetryTracker()
    client = _FakeClient(_extraction_response(), usage={"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10})
    agent = _make_extraction_agent(cache, client, tracker=tracker)

    _run_extraction(agent)
    _run_extraction(agent)

    telemetry = tracker.snapshot("run_cache_hit")
    assert client.chat.completions.calls == 1
    assert telemetry.call_count == 1
    assert telemetry.cache_miss_count == 1
    assert telemetry.cache_hit_count == 1
    assert telemetry.totals.total_tokens == 10


def test_different_request_inputs_miss_the_cache(tmp_path):
    cache = PersistentLLMResponseCache(path=tmp_path / "llm_cache.sqlite3", enabled=True)
    first_client = _FakeClient(_extraction_response())
    first_agent = _make_extraction_agent(cache, first_client, model="model-a", temperature=0.1)
    _run_extraction(first_agent)

    second_client = _FakeClient(_extraction_response())
    second_agent = _make_extraction_agent(cache, second_client, model="model-b", temperature=0.1)
    _run_extraction(second_agent)

    assert first_client.chat.completions.calls == 1
    assert second_client.chat.completions.calls == 1


def test_synthesis_and_extraction_use_separate_cache_namespaces(tmp_path):
    cache = PersistentLLMResponseCache(path=tmp_path / "llm_cache.sqlite3", enabled=True)

    extraction_client = _FakeClient(_extraction_response())
    extraction_agent = _make_extraction_agent(cache, extraction_client)
    _run_extraction(extraction_agent)

    synthesis_client = _FakeClient(_synthesis_response())
    synthesis_agent = _make_synthesis_agent(cache, synthesis_client)
    _run_synthesis(synthesis_agent)

    assert extraction_client.chat.completions.calls == 1
    assert synthesis_client.chat.completions.calls == 1


def test_corrupt_cache_file_falls_back_safely(tmp_path):
    cache_path = tmp_path / "corrupt.sqlite3"
    cache_path.write_text("not a sqlite database", encoding="utf-8")
    cache = PersistentLLMResponseCache(path=cache_path, enabled=True)
    client = _FakeClient(_extraction_response())
    agent = _make_extraction_agent(cache, client)

    result = _run_extraction(agent)

    assert client.chat.completions.calls == 1
    assert result.parse_error == ""


def test_cache_io_failure_falls_back_safely(tmp_path, monkeypatch):
    cache = PersistentLLMResponseCache(path=tmp_path / "llm_cache.sqlite3", enabled=True)
    client = _FakeClient(_extraction_response())
    agent = _make_extraction_agent(cache, client)

    with patch("src.core.llm_response_cache.sqlite3.connect", side_effect=OSError("boom")):
        result = _run_extraction(agent)

    assert client.chat.completions.calls == 1
    assert result.parse_error == ""


def test_disabled_cache_preserves_existing_behavior(tmp_path):
    cache = PersistentLLMResponseCache(path=tmp_path / "llm_cache.sqlite3", enabled=False)
    client = _FakeClient(_extraction_response())
    agent = _make_extraction_agent(cache, client)

    _run_extraction(agent)
    _run_extraction(agent)

    assert client.chat.completions.calls == 2


def test_synthesis_cache_persists_across_agent_instances(tmp_path):
    cache = PersistentLLMResponseCache(path=tmp_path / "llm_cache.sqlite3", enabled=True)
    first_client = _FakeClient(_synthesis_response())
    first_agent = _make_synthesis_agent(cache, first_client)
    first_result = _run_synthesis(first_agent)

    assert first_client.chat.completions.calls == 1
    assert first_result.parse_error == ""

    second_client = _FakeClient(_synthesis_response())
    second_agent = _make_synthesis_agent(cache, second_client)
    second_result = _run_synthesis(second_agent)

    assert second_client.chat.completions.calls == 0
    assert second_result.data == first_result.data

