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

from agents.report_formatter import ReportFormatterAgent
from agents.rule_synthesizer import RuleSynthesizerAgent
from guardrails import ground_business_rules_against_extraction


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


def test_business_rule_provenance_fields_are_normalized():
    payload = json.dumps(
        {
            "purpose_summary": "Summary",
            "step_by_step_flow": [],
            "business_rules": [
                {
                    "condition": "x",
                    "action": "y",
                    "fields_affected": "FIELD_A",
                    "rule_type": "not-valid",
                    "confidence": "definitely",
                    "source_evidence": "evidence text",
                    "dependencies": "dep text",
                }
            ],
            "calculations": [],
            "exception_handling_summary": "",
            "ambiguities": [],
        }
    )
    agent = _make_agent(payload)
    result = agent.synthesize(
        object_name="obj",
        object_type="VIEW",
        parameter_summary="none",
        merged_extraction={"tables_read": [], "tables_written": []},
    )
    rule = result.data["business_rules"][0]
    assert rule["fields_affected"] == ["FIELD_A"]
    assert rule["rule_type"] == "inferred"
    assert rule["confidence"] == "medium"
    assert rule["validation_status"] in {"verified", "unverified", "ambiguous", "parser_failed", "insufficient_evidence"}
    assert rule["source_evidence"] == ["evidence text"]
    assert rule["source_chunks"] == []
    assert rule["technical_references"] == []
    assert rule["unresolved_ambiguities"] == []
    assert rule["dependencies"] == ["dep text"]


def test_parser_failed_evidence_stays_uncertain():
    merged_extraction = {
        "conditions": [
            {
                "condition": "DPD_Max > 90",
                "true_branch": "Set asset classification to Sub-Standard",
                "false_branch": None,
                "source_chunk_id": "00_main_body",
                "source_chunk_kind": "main_body",
                "source_parse_error": "Could not fully parse embedded SQL",
            }
        ],
        "loops": [],
        "tables_read": [],
        "tables_written": [],
        "calculations": [],
        "exception_handling": [],
        "ambiguities": [],
        "chunk_provenance": [
            {
                "chunk_id": "00_main_body",
                "chunk_kind": "main_body",
                "chunk_context": ["main_body"],
                "embedded_sql": [],
                "parse_error": "Could not fully parse embedded SQL",
                "guardrail_warnings": [],
                "support_confidence": "low",
            }
        ],
    }
    rules = [
        {
            "condition": "DPD Max threshold reached",
            "action": "Classify the account as higher risk",
            "fields_affected": ["asset_classification"],
            "rule_type": "inferred",
            "confidence": "high",
            "validation_status": "verified",
            "source_evidence": ["DPD_Max > 90"],
            "dependencies": [],
        }
    ]

    warnings = ground_business_rules_against_extraction(rules, merged_extraction)

    rule = rules[0]
    assert rule["validation_status"] == "parser_failed"
    assert rule["confidence"] == "low"
    assert rule["source_chunks"] == ["00_main_body:main_body"]
    assert rule["technical_references"] == ["conditions[0]"]
    assert rule["unresolved_ambiguities"]
    assert warnings


def test_low_confidence_technical_evidence_is_not_verified():
    merged_extraction = {
        "conditions": [],
        "loops": [],
        "tables_read": [
            {
                "table": "LOAN_ACCOUNT",
                "columns": ["DPD_MAX"],
                "filter_condition": "DPD_MAX > 90",
                "confidence": "low",
                "source_chunk_id": "01_main_body",
                "source_chunk_kind": "main_body",
            }
        ],
        "tables_written": [],
        "calculations": [],
        "exception_handling": [],
        "ambiguities": [],
        "chunk_provenance": [
            {
                "chunk_id": "01_main_body",
                "chunk_kind": "main_body",
                "chunk_context": ["main_body"],
                "embedded_sql": [],
                "parse_error": "",
                "guardrail_warnings": ["table name could not be matched confidently"],
                "support_confidence": "medium",
            }
        ],
    }
    rules = [
        {
            "condition": "Account reads the loan master table",
            "action": "Uses the overdue-days data to decide classification",
            "fields_affected": [],
            "rule_type": "inferred",
            "confidence": "high",
            "source_evidence": ["LOAN_ACCOUNT"],
            "dependencies": [],
        }
    ]

    ground_business_rules_against_extraction(rules, merged_extraction)

    rule = rules[0]
    assert rule["validation_status"] == "insufficient_evidence"
    assert rule["confidence"] == "low"
    assert rule["source_chunks"] == ["01_main_body:main_body"]
    assert rule["technical_references"] == ["tables_read[0]"]


def test_directly_supported_condition_can_remain_verified():
    merged_extraction = {
        "conditions": [
            {
                "condition": "overdue_days <= 90",
                "true_branch": "Stay Standard",
                "false_branch": "Escalate provisioning",
                "source_chunk_id": "02_main_body",
                "source_chunk_kind": "main_body",
            }
        ],
        "loops": [],
        "tables_read": [],
        "tables_written": [],
        "calculations": [],
        "exception_handling": [],
        "ambiguities": [],
        "chunk_provenance": [
            {
                "chunk_id": "02_main_body",
                "chunk_kind": "main_body",
                "chunk_context": ["main_body"],
                "embedded_sql": [],
                "parse_error": "",
                "guardrail_warnings": [],
                "support_confidence": "high",
            }
        ],
    }
    rules = [
        {
            "condition": "overdue_days <= 90",
            "action": "Keeps the account in the standard bucket",
            "fields_affected": [],
            "rule_type": "explicit",
            "confidence": "high",
            "source_evidence": ["overdue_days <= 90"],
            "dependencies": [],
        }
    ]

    ground_business_rules_against_extraction(rules, merged_extraction)

    rule = rules[0]
    assert rule["validation_status"] == "verified"
    assert rule["confidence"] == "high"
    assert rule["source_chunks"] == ["02_main_body:main_body"]
    assert rule["technical_references"] == ["conditions[0]"]


def test_report_formatter_surfaces_provenance_fields():
    agent = _make_agent(
        json.dumps(
            {
                "purpose_summary": "Summary",
                "step_by_step_flow": ["1. Check overdue days"],
                "business_rules": [
                    {
                        "condition": "overdue_days <= 90",
                        "action": "Keeps the account in the standard bucket",
                        "fields_affected": [],
                        "rule_type": "explicit",
                        "confidence": "high",
                        "validation_status": "verified",
                        "source_evidence": ["overdue_days <= 90"],
                        "source_chunks": ["02_main_body:main_body"],
                        "technical_references": ["conditions[0]"],
                        "unresolved_ambiguities": [],
                        "dependencies": [],
                    },
                    {
                        "condition": "DPD_Max > 90",
                        "action": "Marks the account for closer monitoring",
                        "fields_affected": ["FLGSMA"],
                        "rule_type": "inferred",
                        "confidence": "low",
                        "validation_status": "parser_failed",
                        "source_evidence": ["DPD_Max > 90"],
                        "source_chunks": ["03_main_body:main_body"],
                        "technical_references": ["conditions[1]"],
                        "unresolved_ambiguities": ["Underlying technical chunk could not be parsed cleanly."],
                        "dependencies": [],
                    }
                ],
                "calculations": [],
                "exception_handling_summary": "",
                "ambiguities": [],
            }
        )
    )
    result = agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={
            "conditions": [
                {
                    "condition": "overdue_days <= 90",
                    "true_branch": "Stay Standard",
                    "false_branch": "Escalate provisioning",
                    "source_chunk_id": "02_main_body",
                    "source_chunk_kind": "main_body",
                },
                {
                    "condition": "DPD_Max > 90",
                    "true_branch": "Mark for closer monitoring",
                    "false_branch": None,
                    "source_chunk_id": "03_main_body",
                    "source_chunk_kind": "main_body",
                }
            ],
            "tables_read": [],
            "tables_written": [],
            "loops": [],
            "calculations": [],
            "exception_handling": [],
            "ambiguities": [],
            "chunk_provenance": [
                {
                    "chunk_id": "02_main_body",
                    "chunk_kind": "main_body",
                    "chunk_context": ["main_body"],
                    "embedded_sql": [],
                    "parse_error": "",
                    "guardrail_warnings": [],
                    "support_confidence": "high",
                },
                {
                    "chunk_id": "03_main_body",
                    "chunk_kind": "main_body",
                    "chunk_context": ["main_body"],
                    "embedded_sql": [],
                    "parse_error": "parse failed",
                    "guardrail_warnings": ["technical extraction incomplete"],
                    "support_confidence": "low",
                }
            ],
        },
    )
    report = ReportFormatterAgent().format(
        ingestion=type(
            "Ingestion",
            (),
            {
                "object_name": "obj",
                "object_type": "PROCEDURE",
                "dialect": "oracle",
                "dialect_confidence": "high",
                "parameters": [],
                "parameter_parse_status": "parameterless",
                "parse_warnings": [],
            },
        )(),
        merged_extraction={
            "tables_read": [],
            "tables_written": [],
            "conditions": [],
            "loops": [],
            "calculations": [],
            "exception_handling": [],
            "ambiguities": [],
        },
        synthesis=result,
        extraction_guardrail_warnings=[],
    )
    assert "# Business Conditions Report — obj" in report
    assert "## Rule: overdue_days <= 90" in report
    assert "## Rule: DPD_Max > 90 [Needs Review]" in report
    assert "**Applies to:**" in report
    assert "### Decision Logic" in report
    assert "Business Rule Summary" in report
    assert "<details>" in report
    assert "Show rule-to-source mapping" in report
    assert "02_main_body:main_body" in report
    assert "03_main_body:main_body" in report
    assert "conditions[0]" in report
    assert "conditions[1]" in report
    assert "## Tables Read" in report
    assert "1. 1." not in report
    assert "business rules / validations" not in report.lower()
    assert "confidence" not in report.lower()
