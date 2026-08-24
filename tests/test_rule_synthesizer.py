"""
Unit tests for agents.rule_synthesizer.RuleSynthesizerAgent.

The Groq client itself is mocked (no real `groq.Groq` instance, no
network access, no GROQ_API_KEY needed) so these tests focus purely on:
JSON parsing/fallback behavior, and the post-hoc jargon-leakage guard.

Run with:  pytest tests/test_rule_synthesizer.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from agents.rule_synthesizer import RuleSynthesizerAgent


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeCompletionResponse:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    """Stand-in for `client.chat.completions` that returns a pre-canned
    response regardless of input, so we can test parsing logic in
    isolation from any real Groq API call.
    """

    def __init__(self, canned_response: str):
        self.canned_response = canned_response
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        return _FakeCompletionResponse(self.canned_response)


class _FakeChat:
    def __init__(self, canned_response: str):
        self.completions = _FakeCompletions(canned_response)


class _FakeGroqClient:
    """Minimal stand-in for a `groq.Groq` client instance."""

    def __init__(self, canned_response: str = ""):
        self.chat = _FakeChat(canned_response)

    def set_response(self, canned_response: str):
        self.chat.completions.canned_response = canned_response


VALID_SYNTHESIS_JSON = json.dumps(
    {
        "purpose_summary": "Determines whether a loan should be classified as an NPA.",
        "step_by_step_flow": [
            "The system checks how overdue the account is.",
            "It assigns a risk classification based on that overdue period.",
        ],
        "business_rules": [
            {
                "condition": "Account is not more than 90 days overdue",
                "action": "Classified as Standard with minimal provisioning",
            }
        ],
        "calculations": [
            {
                "metric": "Provisioning amount",
                "explanation": "Outstanding balance multiplied by the applicable risk percentage.",
            }
        ],
        "exception_handling_summary": "Failures are logged and the change is not applied.",
        "ambiguities": [],
    }
)


def _make_agent(canned_response: str) -> RuleSynthesizerAgent:
    client = _FakeGroqClient(canned_response)
    return RuleSynthesizerAgent(client=client, model="llama-3.3-70b-versatile", temperature=0.1)


def test_synthesize_parses_valid_json():
    agent = _make_agent(VALID_SYNTHESIS_JSON)
    result = agent.synthesize(
        object_name="classify_npa_and_provision",
        object_type="PROCEDURE",
        parameter_summary="p_account_id (IN NUMBER)",
        merged_extraction={"conditions": [], "tables_read": []},
    )
    assert result.parse_error == ""
    assert result.data["business_rules"][0]["condition"].startswith("Account is not more")
    assert result.jargon_flags == []


def test_synthesize_calls_configured_model():
    client = _FakeGroqClient(VALID_SYNTHESIS_JSON)
    agent = RuleSynthesizerAgent(client=client, model="llama-3.1-8b-instant", temperature=0.2)
    agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )
    assert client.chat.completions.last_call_kwargs["model"] == "llama-3.1-8b-instant"
    assert client.chat.completions.last_call_kwargs["temperature"] == 0.2


def test_synthesize_handles_malformed_json():
    agent = _make_agent("this is not valid json at all {{{")
    result = agent.synthesize(
        object_name="classify_npa_and_provision",
        object_type="PROCEDURE",
        parameter_summary="p_account_id (IN NUMBER)",
        merged_extraction={},
    )
    assert result.parse_error != ""
    assert result.data["ambiguities"]  # fallback ambiguity note populated
    assert "manual review" in result.data["ambiguities"][0]


def test_synthesize_strips_markdown_fences():
    fenced = "```json\n" + VALID_SYNTHESIS_JSON + "\n```"
    agent = _make_agent(fenced)
    result = agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )
    assert result.parse_error == ""
    assert result.data["purpose_summary"]


def test_jargon_flagging_detects_banned_terms():
    jargon_json = json.dumps(
        {
            "purpose_summary": "This uses a cursor to loop over rows.",
            "step_by_step_flow": [],
            "business_rules": [],
            "calculations": [],
            "exception_handling_summary": "",
            "ambiguities": [],
        }
    )
    agent = _make_agent(jargon_json)
    result = agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )
    assert "cursor" in result.jargon_flags


def test_synthesize_missing_keys_default_safely():
    partial_json = json.dumps({"purpose_summary": "Only a summary provided."})
    agent = _make_agent(partial_json)
    result = agent.synthesize(
        object_name="obj",
        object_type="VIEW",
        parameter_summary="none",
        merged_extraction={},
    )
    assert result.data["purpose_summary"] == "Only a summary provided."
    assert result.data["business_rules"] == []
    assert result.data["ambiguities"] == []
