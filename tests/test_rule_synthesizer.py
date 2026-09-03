"""
Unit tests for agents.rule_synthesizer.RuleSynthesizerAgent.

The Groq client itself is mocked (no real `groq.Groq` instance, no
network access, no GROQ_API_KEY needed) so these tests focus purely on:
JSON parsing/fallback behavior, and the post-hoc jargon-leakage guard.

Run with:  pytest tests/test_rule_synthesizer.py -v
"""

import json
import sys
from copy import deepcopy
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from src.ingestion.guardrails import ground_business_rules_against_extraction
from src.validation.coverage_check import find_coverage_gaps
from src.validation.coverage_check import find_coverage_gaps


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


def test_compact_synthesis_payload_keeps_only_synthesis_facts():
    # The synthesis prompt intentionally keeps a compact technical
    # evidence view: only the branch-reasoning fields the LLM actually
    # needs are serialized into the prompt. Heavier transport/provenance
    # fields stay in `merged_extraction` for verification/reporting.
    merged_extraction = {
        "conditions": [{"condition": "x"}],
        "decision_chains": [{"subject": "x"}],
        "loops": [{"loop": "x"}],
        "tables_read": [{"table": "A", "operation": "READ"}],
        "tables_written": [{"table": "B", "operation": "UPDATE"}],
        "table_operations": [
            {"operation": "READ", "table": "A", "target_columns": ["COL1"]},
            {"operation": "READ", "table": "A", "target_columns": ["COL1"], "where_predicate": "COL1 > 0"},
        ],
        "statement_provenance": [{"statement_id": "stmt_1"}],
        "chunk_provenance": [{"chunk_id": "chunk_1"}],
        "calculations": [{"metric": "m"}],
        "exception_handling": [{"kind": "catch"}],
        "ambiguities": ["needs review"],
        "run_metadata": {"model_name": "model"},
        "telemetry": {"totals": {"prompt_tokens": 1}},
        "llm_tables_read": [{"table": "A"}],
        "llm_tables_written": [{"table": "B"}],
        "reconciliation": {"status": "MATCHED"},
        "coverage": {"total_statements": 1},
        "quality": {"status": "PASS"},
        "canonical_ir": {"business_rules": []},
    }

    compact = RuleSynthesizerAgent._build_compact_synthesis_payload(merged_extraction)

    assert list(compact.keys()) == [
        "conditions",
        "decision_chains",
        "loops",
        "table_operations",
        "calculations",
        "exception_handling",
        "ambiguities",
    ]
    assert compact["conditions"] == [{"condition": "x"}]
    # The two near-duplicate READ records for table A collapse into one
    # deduplicated entry, with the distinct predicate preserved.
    assert len(compact["table_operations"]) == 1
    assert compact["table_operations"][0]["table"] == "A"
    assert compact["table_operations"][0]["operation"] == "READ"
    assert compact["table_operations"][0]["where_predicates"] == ["COL1 > 0"]
    assert compact["table_operations"][0]["statement_count"] == 2
    assert json.dumps(compact, separators=(",", ":"), default=str) == json.dumps(
        RuleSynthesizerAgent._build_compact_synthesis_payload(merged_extraction),
        separators=(",", ":"),
        default=str,
    )
    assert "tables_read" not in compact
    assert "tables_written" not in compact
    assert "run_metadata" not in compact
    assert "telemetry" not in compact
    assert "llm_tables_read" not in compact
    assert "llm_tables_written" not in compact
    assert "reconciliation" not in compact
    assert "coverage" not in compact
    assert "quality" not in compact
    assert "canonical_ir" not in compact
    assert merged_extraction["run_metadata"]["model_name"] == "model"


def test_compact_synthesis_payload_falls_back_to_tables_read_written_when_no_table_operations():
    # Objects where deterministic statement parsing produced nothing
    # (unsupported dialect / parse failure) still need *some* table
    # evidence in the synthesis prompt - fall back to the LLM-extracted
    # tables_read/tables_written, deduplicated the same way.
    merged_extraction = {
        "tables_read": [{"table": "A", "operation": "READ", "target_columns": ["X"]}],
        "tables_written": [{"table": "B", "operation": "UPDATE", "target_columns": ["Y"]}],
        "table_operations": [],
    }
    compact = RuleSynthesizerAgent._build_compact_synthesis_payload(merged_extraction)
    tables = {op["table"] for op in compact["table_operations"]}
    assert tables == {"A", "B"}


def test_synthesis_payload_includes_original_source_only_when_available():
    merged_extraction = {"conditions": [{"condition": "DPD_MAX >= 30"}]}
    compact = RuleSynthesizerAgent._build_compact_synthesis_payload(
        merged_extraction,
        raw_source="UPDATE ACCOUNT SET SMA_CLASS = 'SMA_1' WHERE DPD_MAX >= 30;",
    )

    assert compact["source_sql"] == (
        "UPDATE ACCOUNT SET SMA_CLASS = 'SMA_1' WHERE DPD_MAX >= 30;"
    )
    assert "source_sql" not in RuleSynthesizerAgent._build_compact_synthesis_payload(
        merged_extraction
    )


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


def test_synthesize_serializes_compact_payload_without_transport_fields():
    client = _FakeGroqClient(VALID_SYNTHESIS_JSON)
    agent = RuleSynthesizerAgent(client=client, model="llama-3.1-8b-instant", temperature=0.2)
    merged_extraction = {
        "conditions": [{"condition": "overdue_days > 90"}],
        "decision_chains": [{"subject": "overdue_days"}],
        "loops": [],
        "tables_read": [{"table": "LOAN_ACCOUNT"}],
        "tables_written": [{"table": "ACCOUNT_STATUS"}],
        "calculations": [],
        "exception_handling": [],
        "ambiguities": [],
        "run_metadata": {"model_name": "model"},
        "telemetry": {"totals": {"prompt_tokens": 1}},
        "llm_tables_read": [{"table": "LOAN_ACCOUNT"}],
        "llm_tables_written": [{"table": "ACCOUNT_STATUS"}],
        "statement_provenance": [{"statement_id": "stmt_1"}],
        "table_operations": [{"operation": "READ", "table": "LOAN_ACCOUNT", "target_columns": ["STATUS"]}],
        "reconciliation": {"status": "MATCHED"},
        "coverage": {"total_statements": 1},
        "quality": {"status": "PASS"},
        "canonical_ir": {"business_rules": []},
        "chunk_provenance": [{"chunk_id": "chunk_1"}],
    }

    agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction=merged_extraction,
    )
    user_prompt = client.chat.completions.last_call_kwargs["messages"][1]["content"]
    assert '"run_metadata"' not in user_prompt
    assert '"telemetry"' not in user_prompt
    assert '"llm_tables_read"' not in user_prompt
    assert '"llm_tables_written"' not in user_prompt
    assert '"reconciliation"' not in user_prompt
    assert '"coverage"' not in user_prompt
    assert '"quality"' not in user_prompt
    assert '"canonical_ir"' not in user_prompt
    assert '"tables_read"' not in user_prompt
    assert '"tables_written"' not in user_prompt
    assert '"statement_provenance"' not in user_prompt
    assert '"chunk_provenance"' not in user_prompt
    assert '"table_operations"' in user_prompt
    assert '"conditions":[{"condition":"overdue_days > 90"}]' in user_prompt
    # Deduplicated shape: table/operation plus the union of columns and
    # the distinct predicates actually used, not the raw per-statement dict.
    assert '"table":"LOAN_ACCOUNT"' in user_prompt
    assert '"operation":"READ"' in user_prompt
    assert '"target_columns":["STATUS"]' in user_prompt
    assert '\n    "conditions"' not in user_prompt
    assert '\n      "conditions"' not in user_prompt


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


def test_synthesize_always_passes_explicit_max_tokens():
    # Regression test: `max_tokens` must always be passed explicitly on
    # every completion call. The OpenAI client defaults to a generous
    # ceiling when it's omitted, but the Bedrock-backed client
    # (`_BedrockChatCompletions.create` in src/core/llm_client.py) defaults
    # its OWN max_tokens to 1024 when the caller doesn't pass one - which
    # silently truncates synthesis JSON well before it's complete for any
    # object of realistic size. Never rely on provider defaults here.
    client = _FakeGroqClient(VALID_SYNTHESIS_JSON)
    agent = RuleSynthesizerAgent(client=client, model="m", temperature=0.1)
    agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )
    assert client.chat.completions.last_call_kwargs["max_tokens"] == agent.max_tokens
    assert client.chat.completions.last_call_kwargs["max_tokens"] > 1024


def test_synthesize_max_tokens_is_configurable():
    client = _FakeGroqClient(VALID_SYNTHESIS_JSON)
    agent = RuleSynthesizerAgent(client=client, model="m", temperature=0.1, max_tokens=32000)
    agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )
    assert client.chat.completions.last_call_kwargs["max_tokens"] == 32000


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


def test_synthesize_recovers_json_wrapped_in_prose():
    wrapped = (
        "Here is the requested synthesis:\n"
        "```json\n"
        + VALID_SYNTHESIS_JSON
        + "\n```\n"
        "Please review the result."
    )
    agent = _make_agent(wrapped)
    result = agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )
    assert result.parse_error == ""
    assert len(result.data["business_rules"]) == 1
    assert result.data["business_rules"][0]["action"].startswith("Classified as Standard")


def test_synthesize_parse_failure_short_circuits_without_normalization(monkeypatch):
    validate_calls = {"count": 0}
    ground_calls = {"count": 0}

    def _unexpected_validate(data):
        validate_calls["count"] += 1
        return data, []

    def _unexpected_ground(*args, **kwargs):
        ground_calls["count"] += 1
        return []

    monkeypatch.setattr("src.synthesis.rule_synthesizer.validate_synthesis_shape", _unexpected_validate)
    monkeypatch.setattr("src.synthesis.rule_synthesizer.ground_business_rules_against_extraction", _unexpected_ground)

    agent = _make_agent("this is not valid json at all {{{")
    result = agent.synthesize(
        object_name="classify_npa_and_provision",
        object_type="PROCEDURE",
        parameter_summary="p_account_id (IN NUMBER)",
        merged_extraction={},
    )

    assert result.parse_error != ""
    assert validate_calls["count"] == 0
    assert ground_calls["count"] == 0
    assert result.data["business_rules"] == []


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
    assert rule["rule_type"] == "not-valid"
    assert rule["confidence"] == "definitely"
    assert rule["validation_status"] == ""
    assert rule["source_evidence"] == ["evidence text"]
    assert rule["source_chunks"] == []
    assert rule["technical_references"] == []
    assert rule["unresolved_ambiguities"] == []
    assert rule["dependencies"] == ["dep text"]


def test_technical_reset_rules_remain_separate_from_sma_family():
    raw_rules = [
        {
            "rule_name": "Clear prior SMA fields",
            "condition": "FinalAssetClassAlt_Key = 1 AND SMA_CLASS is NULL",
            "action": "Clear the SMA classification fields before reprocessing",
            "output_field": "SMA_CLASS",
            "fields_affected": ["SMA_CLASS", "SMA_REASON", "SMA_DT", "FLGSMA"],
            "source_evidence": ["A.SMA_CLASS=NULL", "A.SMA_REASON=NULL", "A.SMA_DT=NULL", "A.FLGSMA=NULL"],
            "business_meaning": "Technical cleanup before recalculation.",
            "rule_type": "explicit",
            "confidence": "high",
            "validation_status": "verified",
        },
        {
            "rule_name": "Assign SMA classification based on DPD_Max",
            "condition": "FinalAssetClassAlt_Key = 1 AND SMA_CLASS is NULL",
            "action": "Set SMA classification from the overdue-days band",
            "output_field": "SMA_CLASS",
            "fields_affected": ["SMA_CLASS"],
            "source_evidence": ["SMA_CLASS := 'STD'"],
            "business_meaning": "Assigns the account's SMA classification.",
            "rule_type": "explicit",
            "confidence": "high",
            "validation_status": "verified",
        },
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)

    assert len(normalized) == 2
    assert any("clear" in rule["action"].lower() for rule in normalized)
    assert any("classification" in rule["action"].lower() for rule in normalized)


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

    before = deepcopy(rules)
    warnings = ground_business_rules_against_extraction(rules, merged_extraction)

    assert rules == before
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

    before = deepcopy(rules)
    warnings = ground_business_rules_against_extraction(rules, merged_extraction)

    assert rules == before
    assert warnings


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

    before = deepcopy(rules)
    warnings = ground_business_rules_against_extraction(rules, merged_extraction)

    assert rules == before
    assert warnings == []


def test_business_rule_grounding_attaches_evidence_spans():
    merged_extraction = {
        "conditions": [
            {
                "condition": "DPD_MAX > 90",
                "true_branch": "Mark for review",
                "false_branch": None,
                "source_chunk_id": "CHUNK-01",
                "source_chunk_kind": "main_body",
                "statement_id": "STMT-01",
                "source_statement_text": "IF DPD_MAX > 90 THEN ...",
            }
        ],
        "tables_read": [
            {
                "table": "LOAN_ACCOUNT",
                "columns": ["DPD_MAX"],
                "filter_condition": "DPD_MAX > 90",
                "source_chunk_id": "CHUNK-01",
                "source_chunk_kind": "main_body",
            }
        ],
        "tables_written": [],
        "loops": [],
        "calculations": [],
        "exception_handling": [],
        "ambiguities": [],
        "chunk_provenance": [
            {
                "chunk_id": "CHUNK-01",
                "chunk_kind": "main_body",
                "chunk_context": ["main_body"],
                "embedded_sql": [],
                "parse_error": "",
                "guardrail_warnings": [],
                "support_confidence": "high",
                "source_file": "demo.sql",
                "source_char_start": 10,
                "source_char_end": 80,
                "source_line_start": 5,
                "source_line_end": 9,
                "source_location_status": "available",
            }
        ],
        "statement_provenance": [
            {
                "statement_id": "STMT-01",
                "source_chunk_id": "CHUNK-01",
                "source_file": "demo.sql",
                "source_char_start": 24,
                "source_char_end": 40,
                "source_line_start": 6,
                "source_line_end": 6,
                "source_location_status": "available",
                "evidence_type": "CONDITION",
            }
        ],
    }
    rules = [
        {
            "condition": "DPD exceeds 90 days",
            "action": "Treat the account as higher risk",
            "fields_affected": [],
            "rule_type": "inferred",
            "confidence": "high",
            "source_evidence": ["LOAN_ACCOUNT", "DPD_MAX > 90"],
            "dependencies": [],
        }
    ]

    before = deepcopy(rules)
    warnings = ground_business_rules_against_extraction(rules, merged_extraction)

    assert rules == before
    assert warnings == []


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
                    },
                    {
                        "condition": "SMA classification ladder",
                        "action": "Assigns SMA classification based on DPD band",
                        "output_field": "SMA_CLASS",
                        "decision_logic_rows": [
                            {"condition": "1-30 days overdue", "outcome": "SMA-0"},
                            {"condition": "31-60 days overdue", "outcome": "SMA-1"},
                            {"condition": "61+ days overdue", "outcome": "SMA-2"},
                        ],
                        "fields_affected": ["SMA_CLASS"],
                        "rule_type": "explicit",
                        "confidence": "high",
                        "validation_status": "verified",
                        "source_evidence": ["CASE WHEN DPD_Max BETWEEN 1 AND 30 THEN 'SMA-0' ..."],
                        "source_chunks": ["04_main_body:main_body"],
                        "technical_references": [],
                        "unresolved_ambiguities": [],
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
    assert "# obj — Business Logic Report" in report
    assert "### R1 — Not specified" in report
    assert "### R2 — Not specified" in report
    assert "**Validation:** Incomplete LLM-authored rule" not in report
    assert "**Affected Field:**" in report
    assert "### Decision Logic" in report
    assert "**Eligibility:**" not in report
    assert "**Meaning:**" not in report
    assert "**Action:**" not in report
    assert "## Rule Priority" not in report
    assert "SMA-0" in report and "SMA-1" in report and "SMA-2" in report
    assert "## Data Touched" in report
    assert "### In Simple Terms" not in report
    assert "### Business Outcome" not in report
    assert "emitted in the pipeline run log rather than in this report" in report
    assert "## Data Touched" in report
    assert "## Important Business Updates" not in report
    assert "1. 1." not in report
    assert "business rules / validations" not in report.lower()
    assert "**Dialect:** Oracle" in report


def test_report_formatter_prefers_canonical_business_rules_for_display():
    # `canonical_ir.business_rules` is always preferred over the raw LLM
    # output for display, even when raw_rules has more/"richer" items -
    # canonical is the only one of the two that's been grounded against
    # the deterministic extraction and sorted into actual source
    # execution order. Silently preferring "whichever list looks bigger"
    # was a real regression: it let raw, unordered, ungrounded rules
    # bypass all of that (see report design notes).
    raw_rules = [
        {"condition": "A", "action": "First", "decision_logic_rows": [{"condition": "A", "outcome": "X"}]},
        {"condition": "B", "action": "Second", "decision_logic_rows": [{"condition": "B", "outcome": "Y"}]},
        {"condition": "C", "action": "Third", "decision_logic_rows": [{"condition": "C", "outcome": "Z"}]},
    ]
    canonical_rules = [
        {"condition": "A", "action": "First"},
    ]

    chosen = ReportFormatterAgent._business_rules_for_display(raw_rules, canonical_rules)
    assert chosen == canonical_rules


def test_report_formatter_does_not_fall_back_to_raw_rules_when_canonical_is_empty():
    # An empty canonical rule set must remain empty in the report.
    raw_rules = [{"condition": "A", "action": "First"}]
    chosen = ReportFormatterAgent._business_rules_for_display(raw_rules, [])
    assert chosen == []


def test_report_formatter_preserves_synthesized_rule_boundaries_for_display():
    rules = [
        {
            "rule_name": "Reset negative DPD_IntService to zero",
            "business_meaning": "Any negative value in the DPD_IntService field is reset to zero to maintain data integrity.",
            "output_field": "DPD_IntService",
            "fields_affected": ["DPD_IntService"],
            "eligibility": ["isnull(DPD_IntService,0)<0"],
            "decision_logic_rows": [{"condition": "isnull(DPD_IntService,0)<0", "outcome": "0"}],
        },
        {
            "rule_name": "Reset negative DPD_NoCredit to zero",
            "business_meaning": "Any negative value in the DPD_NoCredit field is reset to zero to maintain data integrity.",
            "output_field": "DPD_NoCredit",
            "fields_affected": ["DPD_NoCredit"],
            "eligibility": ["isnull(DPD_NoCredit,0)<0"],
            "decision_logic_rows": [{"condition": "isnull(DPD_NoCredit,0)<0", "outcome": "0"}],
        },
    ]

    display_rules = ReportFormatterAgent()._display_business_rules(rules)
    assert len(display_rules) == 2
    assert display_rules[0]["rule_name"] == "Reset negative DPD_IntService to zero"
    assert display_rules[1]["rule_name"] == "Reset negative DPD_NoCredit to zero"


def test_report_formatter_renders_single_decision_logic_row():
    rows = ReportFormatterAgent()._decision_logic_rows(
        {"decision_logic_rows": [{"condition": "DPD_Max > 90", "outcome": "SMA-2"}]}
    )
    assert rows == [{"condition": "DPD_Max > 90", "outcome": "SMA-2"}]


def test_report_formatter_preserves_distinct_decision_rows():
    rows = ReportFormatterAgent()._decision_logic_rows(
        {
            "rule_name": "Classify account",
            "decision_logic_rows": [
                {"condition": "DPD_Max BETWEEN 1 AND 30", "outcome": "SMA_0"},
                {"condition": "DPD_Max BETWEEN 31 AND 60", "outcome": "SMA_1"},
            ],
        }
    )
    assert len(rows) == 2


def test_report_formatter_does_not_derive_business_meaning_from_other_fields():
    meaning = ReportFormatterAgent._business_rule_business_meaning(
        {
            "rule_name": "Calculate maximum DPD for account",
            "business_meaning": "Set STANDARD classification and 15 provision pct",
        }
    )
    assert meaning == "Set STANDARD classification and 15 provision pct"


def test_formatter_preserves_llm_rule_fields_in_report():
    rule = {
        "rule_name": "LLM supplied label",
        "business_meaning": "LLM supplied meaning.",
        "condition": "A.CUSTOM_CONDITION >= 7",
        "eligibility": ["LLM supplied eligibility"],
        "action": "LLM supplied action for CUSTOM_FIELD",
        "output_field": "CUSTOM_FIELD",
        "fields_affected": ["CUSTOM_FIELD"],
        "decision_logic_rows": [{"condition": "A.CUSTOM_CONDITION >= 7", "outcome": "LLM_VALUE"}],
        "source_evidence": ["A.CUSTOM_CONDITION >= 7"],
        "rule_type": "explicit",
        "confidence": "high",
        "validation_status": "verified",
    }
    report = ReportFormatterAgent()._business_rules_section([rule])
    for value in (
        "LLM supplied label", "A.CUSTOM_CONDITION >= 7", "CUSTOM_FIELD", "LLM_VALUE",
    ):
        assert value in report
    assert "LLM supplied meaning." not in report
    assert "LLM supplied eligibility" not in report
    assert "LLM supplied action for CUSTOM_FIELD" not in report


def test_formatter_flags_empty_required_fields_without_inventing_meaning():
    report = ReportFormatterAgent()._business_rules_section([
        {"condition": "SELECT derived_value FROM source_table", "action": "", "business_meaning": ""}
    ])
    assert "Incomplete LLM-authored rule" not in report
    assert "Not specified" in report
    assert "derived_value is" not in report


def test_formatter_does_not_merge_distinct_llm_rules():
    rules = [
        {"rule_name": "First LLM rule", "business_meaning": "First meaning."},
        {"rule_name": "Second LLM rule", "business_meaning": "Second meaning."},
    ]
    display_rules = ReportFormatterAgent()._display_business_rules(rules)
    report = ReportFormatterAgent()._business_rules_section(display_rules)
    assert len(display_rules) == 2
    assert report.count("### R") == 2
    assert "First meaning." in report and "Second meaning." in report


def test_formatter_never_creates_meaning_from_sql_or_ast_fields():
    rule = {
        "condition": "CASE WHEN amount > 0 THEN amount * rate END",
        "action": "",
        "business_meaning": "",
        "rule_name": "",
    }
    assert ReportFormatterAgent._business_rule_business_meaning(rule) == "Not specified"


def test_formatter_rule_count_and_content_match_canonical_ir_rules():
    canonical_rules = [
        {"rule_name": "Canonical one", "business_meaning": "Meaning one."},
        {"rule_name": "Canonical two", "business_meaning": "Meaning two."},
    ]
    chosen = ReportFormatterAgent._business_rules_for_display(
        [{"rule_name": "Raw extra"}], canonical_rules
    )
    report = ReportFormatterAgent()._business_rules_section(chosen)
    assert len(chosen) == len(canonical_rules) == 2
    assert report.count("### R") == len(canonical_rules)
    assert "Raw extra" not in report
    assert "Canonical one" in report and "Canonical two" in report


def test_operational_process_status_is_not_promoted_to_business_rule():
    rules = [
        {
            "rule_name": "Update process status on completion",
            "action": "Update the running process status on completion or failure",
            "fields_affected": ["COMPLETED", "ERRORDESCRIPTION", "COUNT"],
        },
        {
            "rule_name": "Assign SMA class",
            "action": "Assign the SMA classification",
            "fields_affected": ["SMA_CLASS"],
        },
    ]
    context = {
        "table_operations": [
            {"table": "PRO.ACLRUNNINGPROCESSSTATUS", "operation": "UPDATE"}
        ]
    }

    filtered = RuleSynthesizerAgent._remove_operational_status_rules(rules, context)

    assert [rule["rule_name"] for rule in filtered] == ["Assign SMA class"]


def test_pure_temporary_table_drop_is_not_a_business_rule():
    rules = [
        {
            "rule_name": "Drop existing temporary tables",
            "business_meaning": "Drops temporary tables before processing.",
            "fields_affected": [],
            "decision_logic": [],
        },
        {
            "rule_name": "Reset DPD",
            "business_meaning": "Resets negative DPD values.",
            "fields_affected": ["DPD_Overdue"],
        },
    ]
    context = {
        "table_operations": [
            {"table": "#DPD", "operation": "DROP", "active_status": "ACTIVE"}
        ]
    }

    filtered = RuleSynthesizerAgent._remove_non_business_cleanup_rules(rules, context)

    assert [rule["rule_name"] for rule in filtered] == ["Reset DPD"]


def test_existence_guarded_temporary_drop_with_condition_is_not_a_business_rule():
    rule = {
        "rule_name": "Drop temporary table when present",
        "business_meaning": "Drops temporary data before processing.",
        "condition": "IF OBJECT_ID('tempdb..#x') IS NOT NULL",
        "eligibility": ["IF OBJECT_ID('tempdb..#x') IS NOT NULL"],
        "action": "DROP TABLE #x",
        "fields_affected": [],
        "decision_logic": ["IF OBJECT_ID('tempdb..#x') IS NOT NULL"],
        "decision_logic_rows": [],
    }
    context = {
        "table_operations": [
            {"table": "#x", "operation": "DROP", "active_status": "ACTIVE"}
        ]
    }
    assert RuleSynthesizerAgent._remove_non_business_cleanup_rules([rule], context) == []


def test_cleanup_filter_keeps_rule_with_business_fields():
    rule = {
        "rule_name": "Drop temporary account data after export",
        "business_meaning": "Removes temporary account data after export.",
        "fields_affected": ["ExportStatus"],
    }
    context = {
        "table_operations": [
            {"table": "#EXPORT", "operation": "DROP", "active_status": "ACTIVE"}
        ]
    }

    filtered = RuleSynthesizerAgent._remove_non_business_cleanup_rules([rule], context)

    assert filtered == [rule]


def test_formatter_preserves_dynamic_synthesis_values_without_reference_fallbacks():
    formatter = ReportFormatterAgent()
    synthesis = SynthesisResult(
        data={
            "purpose_summary": "Reconciles inventory quantities for the supplied warehouse.",
            "step_by_step_flow": ["Read warehouse stock", "Update inventory balance"],
            "business_rules": [],
        }
    )
    ingestion = type(
        "Ingestion",
        (),
        {
            "object_name": "INVENTORY_PROC",
            "canonical_object_name": "INVENTORY_PROC",
            "object_type": "PROCEDURE",
            "dialect": "tsql",
            "parameters": [],
            "parse_warnings": [],
            "raw_code": "",
        },
    )()
    report = formatter.format(ingestion, {}, synthesis)
    assert "Reconciles inventory quantities" in report
    assert "Read warehouse stock" in report
    assert "SMA-0" not in report

def test_decision_chains_present_in_extraction_schema_for_all_dialects():
    # Regression test for the actual root cause of a real production bug:
    # the synthesis prompt treats "decision_chains" as the authoritative
    # source for multi-field decision ladders (see rule_synthesis.yaml),
    # but the extraction stage never asked the model to populate it -
    # so it was always empty, and the synthesis LLM had no structured
    # signal to correctly split a rule spanning two output fields (e.g.
    # SMA_CLASS + SMA_REASON getting merged into one rule's decision
    # table). This guards against that gap reopening silently.
    for dialect in ("default", "oracle", "tsql"):
        from src.prompts.prompt_loader import get_prompt_set

        prompt_set = get_prompt_set("logic_extraction.yaml", dialect=dialect if dialect != "default" else "oracle")
        system_text = prompt_set["system"]
        assert '"decision_chains"' in system_text
        assert "branch_condition" in system_text
        assert "assignments" in system_text


# --------------------------------------------------------------------------
# RuleSynthesizerAgent.revise() - the coverage-driven review pass.
#
# Unlike `_apply_authoritative_decision_chains`, this never authors rule
# content itself: it sends the model the exact unreviewed source region and
# lets the model decide what (if anything) belongs there. These tests mock
# the LLM response the same way the rest of this file does.
# --------------------------------------------------------------------------

from src.validation.coverage_check import CoverageGap  # noqa: E402


REVISED_SYNTHESIS_JSON = json.dumps(
    {
        "purpose_summary": "Determines whether a loan should be classified as an NPA.",
        "step_by_step_flow": [],
        "business_rules": [
            {
                "condition": "Account is not more than 90 days overdue",
                "action": "Classified as Standard with minimal provisioning",
            },
            {
                "condition": "dpd.DPD_Max BETWEEN 1 AND 30",
                "action": "SMA_CLASS is set to SMA_0",
                "fields_affected": ["SMA_CLASS"],
                "source_evidence": ["dpd.DPD_Max BETWEEN 1 AND 30 -> 'SMA_0'"],
            },
        ],
        "calculations": [],
        "exception_handling_summary": "",
        "ambiguities": [],
    }
)


def test_revise_returns_none_when_there_are_no_gaps():
    agent = _make_agent(REVISED_SYNTHESIS_JSON)
    assert agent.revise(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="",
        merged_extraction={},
        existing_rules=[],
        gaps=[],
    ) is None


def test_revise_sends_the_gap_snippet_and_existing_rules_to_the_model():
    client = _FakeGroqClient(REVISED_SYNTHESIS_JSON)
    agent = RuleSynthesizerAgent(client=client, model="llama-3.3-70b-versatile", temperature=0.1)
    existing_rules = [{"condition": "x", "action": "y"}]
    gap = CoverageGap(
        line_start=3, line_end=6,
        snippet="CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' ... END",
        keywords=["CASE", "WHEN"],
    )
    result = agent.revise(
        object_name="classify_npa_and_provision",
        object_type="PROCEDURE",
        parameter_summary="p_account_id (IN NUMBER)",
        merged_extraction={"conditions": [], "tables_read": []},
        existing_rules=existing_rules,
        gaps=[gap],
    )
    assert result is not None
    assert result.parse_error == ""
    # Two rules come back: the untouched prior rule plus the new one the
    # model added for the previously-uncovered CASE ladder.
    assert len(result.data["business_rules"]) == 2
    sent_prompt = client.chat.completions.last_call_kwargs["messages"][1]["content"]
    assert "Lines 3-6" in sent_prompt
    assert "SMA_0" in sent_prompt
    assert '"condition": "x"' in sent_prompt or "\"x\"" in sent_prompt


def test_revise_returns_none_on_malformed_json_without_wiping_prior_rules():
    agent = _make_agent("not valid json { at all")
    gap = CoverageGap(line_start=1, line_end=2, snippet="IF x THEN y", keywords=["IF"])
    result = agent.revise(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="",
        merged_extraction={},
        existing_rules=[{"condition": "kept"}],
        gaps=[gap],
    )
    assert result is None


def test_revise_unsupported_dialect_returns_none():
    agent = _make_agent(REVISED_SYNTHESIS_JSON)
    gap = CoverageGap(line_start=1, line_end=2, snippet="IF x THEN y", keywords=["IF"])
    assert agent.revise(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="",
        merged_extraction={},
        existing_rules=[],
        gaps=[gap],
        dialect="postgres",
    ) is None


def test_deterministic_pipeline_never_mutates_rule_text():
    rules = [
        {
            "rule_name": "Keep exact threshold label",
            "business_meaning": "Distinctive meaning: preserve the source label exactly.",
            "condition": "Distinctive condition: balance <= 100.00",
            "action": "Distinctive action: assign the exact low-balance label.",
            "output_field": "risk_label",
            "source_evidence": ["balance <= 100.00"],
            "fields_affected": ["risk_label"],
        },
        {
            "rule_name": "Keep exact priority calculation",
            "business_meaning": "Distinctive meaning: calculate the priority score.",
            "condition": "Distinctive condition: priority inputs are present",
            "action": "Distinctive action: calculate priority using the supplied formula.",
            "output_field": "priority_score",
            "source_evidence": ["priority_score = amount * factor"],
            "fields_affected": ["priority_score"],
        },
        {
            "rule_name": "Keep exact fallback wording",
            "business_meaning": "Distinctive meaning: use the explicit fallback wording.",
            "condition": "Distinctive condition: no eligible branch matched",
            "action": "Distinctive action: leave the destination unchanged.",
            "output_field": "status_code",
            "source_evidence": ["status_code"],
            "fields_affected": ["status_code"],
        },
    ]
    original_text = {
        rule["rule_name"]: {
            key: rule[key]
            for key in ("condition", "action", "business_meaning", "rule_name")
        }
        for rule in rules
    }

    post_processed = RuleSynthesizerAgent._normalize_business_rules(rules)
    post_processed = RuleSynthesizerAgent._remove_operational_status_rules(post_processed, {})
    post_processed = RuleSynthesizerAgent._remove_non_business_cleanup_rules(post_processed, {})
    post_processed = RuleSynthesizerAgent._remove_operation_only_rules(post_processed)
    for rule in post_processed:
        assert {
            key: rule[key]
            for key in ("condition", "action", "business_meaning", "rule_name")
        } == original_text[rule["rule_name"]]

    agent = _make_agent(json.dumps({"business_rules": rules}))
    revision = agent.revise(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="No parameters.",
        merged_extraction={},
        existing_rules=[],
        gaps=["review these source lines"],
        dialect="tsql",
        raw_source="UPDATE accounts SET risk_label = 'LOW'",
    )
    assert revision is not None
    for rule in revision.data["business_rules"]:
        assert {
            key: rule[key]
            for key in ("condition", "action", "business_meaning", "rule_name")
        } == original_text[rule["rule_name"]]


def test_empty_business_rules_triggers_coverage_gap_and_revision():
    source = """UPDATE accounts SET risk_label = CASE
WHEN balance < 0 THEN 'OVERDRAWN'
WHEN balance = 0 THEN 'ZERO'
ELSE 'POSITIVE'
END"""
    agent = _make_agent(json.dumps({"business_rules": []}))
    initial = agent.synthesize(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="No parameters.",
        merged_extraction={},
        dialect="tsql",
        raw_source=source,
    )
    assert initial.data["business_rules"] == []

    gaps = find_coverage_gaps(source, initial.data["business_rules"])
    assert gaps
    assert any("WHEN" in gap.keywords for gap in gaps)
    assert any("balance < 0" in gap.snippet for gap in gaps)

    revised_rules = [
        {
            "rule_name": "Assign risk label from balance band",
            "business_meaning": "The account receives a balance-based risk label.",
            "condition": "The balance falls into one of the source-defined bands.",
            "action": "Assign OVERDRAWN, ZERO, or POSITIVE according to the matching branch.",
            "output_field": "risk_label",
            "source_evidence": [source],
            "fields_affected": ["risk_label"],
        }
    ]
    agent.client.set_response(json.dumps({"business_rules": revised_rules}))
    revision = agent.revise(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="No parameters.",
        merged_extraction={},
        existing_rules=initial.data["business_rules"],
        gaps=gaps,
        dialect="tsql",
        raw_source=source,
    )
    assert revision is not None
    assert len(revision.data["business_rules"]) == len(revised_rules)
    for actual, expected in zip(revision.data["business_rules"], revised_rules):
        for key in ("rule_name", "business_meaning", "condition", "action", "output_field"):
            assert actual[key] == expected[key]
        assert actual["source_evidence"] == expected["source_evidence"]
        assert actual["fields_affected"] == expected["fields_affected"]
    assert find_coverage_gaps(source, revision.data["business_rules"]) == []


def test_report_findings_exclude_raw_reconciliation_classifier_text():
    formatter = ReportFormatterAgent()
    synthesis = SynthesisResult(
        data={
            "business_rules": [],
            "ambiguities": [
                "The source uses a dynamic value and needs business review.",
                "Reconciliation review required: tables_written evidence is llm_only and must not be treated as a confirmed business rule.",
                "Reconciliation detected a source/report discrepancy: raw contradiction_classifier output.",
            ]
        }
    )
    findings = formatter._findings_section(
        synthesis,
        {"ambiguities": list(synthesis.data["ambiguities"])},
    )
    assert "The source uses a dynamic value and needs business review." in findings
    assert "llm_only" not in findings
    assert "contradiction_classifier" not in findings
