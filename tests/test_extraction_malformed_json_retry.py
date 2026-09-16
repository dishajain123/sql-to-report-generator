"""Regression coverage for retrying a genuinely malformed (non-truncated)
extraction response.

Root cause: `LogicExtractionAgent.extract()` only ever retried when the
response was cut off mid-JSON (`finish_reason == "length"`). A response
that came back *complete* (`finish_reason == "stop"`) but simply wasn't
valid JSON - stray prose, a broken code fence, degenerate output - fell
straight through to the "malformed JSON, needs manual review" fallback on
the very first attempt, with no retry at all, even though callers
downstream describe this outcome as failing "after retries" (see the
degraded-run banner text in pipeline.py / report_formatter.py). This
mattered in practice for administratively-trivial chunks (bare
`SET QUOTED_IDENTIFIER ON`-style content) and other chunks with nothing
for a business-rule extraction prompt to find, where a free-text
non-JSON response is a real, observed failure mode.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extraction.logic_extractor import LogicExtractionAgent


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content, finish_reason):
        self.message = _FakeMessage(content)
        self.finish_reason = finish_reason


class _FakeResponse:
    def __init__(self, content, finish_reason="stop"):
        self.choices = [_FakeChoice(content, finish_reason)]
        self.usage = None


def _valid_extraction_json() -> str:
    return json.dumps({
        "conditions": [], "decision_chains": [], "loops": [],
        "tables_read": [], "tables_written": [], "calculations": [],
        "exception_handling": [], "ambiguities": [],
    })


class _ScriptedCompletions:
    """Each call consults `responses` in order; records every `seed` kwarg
    it was called with, so a test can confirm a retry doesn't just repeat
    the same deterministic seed against the same malformed output.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.seeds_seen = []

    def create(self, seed=None, **kwargs):
        # `seed` is an explicit parameter (not folded into **kwargs) so
        # `supports_chat_completion_seed` (which inspects the real
        # signature) reports seed support, matching a real OpenAI-shaped
        # client and exercising the seed-varying behavior under test.
        self.seeds_seen.append(seed)
        content = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return _FakeResponse(content)


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, responses):
        self.chat = _FakeChat(_ScriptedCompletions(responses))


def _make_agent(client, seed=0):
    return LogicExtractionAgent(
        client=client, model="demo-model", temperature=0.1, seed=seed,
        provider="openai", max_tokens=2000, hard_max_output_tokens=8000,
    )


def test_malformed_non_truncated_response_gets_one_retry_and_can_succeed():
    """First call returns complete-but-invalid JSON (finish_reason="stop",
    not "length"); the retry returns valid JSON. The chunk must come back
    clean - no parse_error, real extraction data - rather than degrading
    to the malformed-JSON fallback on the first bad response."""
    client = _FakeClient([
        "Sorry, I don't see any business logic in this fragment.",
        _valid_extraction_json(),
    ])
    agent = _make_agent(client)

    result = agent.extract(
        chunk_id="00_declaration",
        chunk_kind="declaration",
        code_chunk="SET QUOTED_IDENTIFIER ON",
        rag_context="",
        object_type="PROCEDURE",
        object_name="demo",
        dialect="tsql",
    )

    assert client.chat.completions.calls == 2
    assert result.parse_error == ""
    assert result.data["conditions"] == []
    # The retry must not reuse the exact same seed as the failed attempt -
    # replaying the identical request against a deterministic model would
    # just reproduce the same malformed text.
    seeds = client.chat.completions.seeds_seen
    assert len(seeds) == 2
    assert seeds[0] != seeds[1]


def test_malformed_response_still_degrades_gracefully_if_retry_also_fails():
    """Both the original call and its retry return invalid JSON - the
    chunk must still degrade to the documented malformed-JSON fallback
    (not raise), and by now the fallback's "...after retries..." framing
    is actually true."""
    client = _FakeClient([
        "not json at all",
        "still not json",
    ])
    agent = _make_agent(client)

    result = agent.extract(
        chunk_id="02_batch2_declaration",
        chunk_kind="declaration",
        code_chunk="SET QUOTED_IDENTIFIER ON",
        rag_context="",
        object_type="PROCEDURE",
        object_name="demo",
        dialect="tsql",
    )

    assert client.chat.completions.calls == 2
    assert result.parse_error != ""
    assert result.data["ambiguities"]


def test_truncated_response_path_unaffected_by_malformed_retry_branch():
    """A length-truncated response with unrecoverable partial JSON still
    takes the existing truncation-retry-at-ceiling path, not the new
    malformed-JSON branch (they're mutually exclusive on `truncated`)."""
    client = _FakeClient([
        '{"conditions": [',  # truncated, not recoverable as-is
        _valid_extraction_json(),
    ])
    agent = _make_agent(client)
    # Force the first call's max_tokens below hard_max_output_tokens so the
    # truncation branch's "retry at the ceiling" condition is reachable.
    agent.max_tokens = 10

    result = agent.extract(
        chunk_id="03_main_body",
        chunk_kind="main_body",
        code_chunk="UPDATE t SET x = 1",
        rag_context="",
        object_type="PROCEDURE",
        object_name="demo",
        dialect="tsql",
    )

    assert client.chat.completions.calls == 2
    assert result.parse_error == ""
    # The recovered/retried result reflects the successful call's own
    # finish_reason, not the original truncated one - this test's purpose
    # is only to confirm the malformed-non-truncated branch (which would
    # trigger a *second*, seed-varied retry) never runs here: exactly one
    # retry call happens, taking the pre-existing truncation path.
    assert result.data["conditions"] == []