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
from src.synthesis.rule_synthesizer import PromptTooLargeForRateLimitError
from src.ingestion.guardrails import ground_business_rules_against_extraction
from src.validation.coverage_check import find_coverage_gaps
from src.validation.coverage_check import find_coverage_gaps


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self.message = _FakeMessage(content)
        self.finish_reason = finish_reason


class _FakeCompletionResponse:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self.choices = [_FakeChoice(content, finish_reason)]


class _FakeCompletions:
    """Stand-in for `client.chat.completions` that returns a pre-canned
    response regardless of input, so we can test parsing logic in
    isolation from any real Groq API call.
    """

    def __init__(self, canned_response: str, finish_reason: str = "stop"):
        self.canned_response = canned_response
        self.finish_reason = finish_reason
        self.last_call_kwargs = None
        self.calls = []

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        self.calls.append(kwargs)
        return _FakeCompletionResponse(self.canned_response, self.finish_reason)


class _FakeChat:
    def __init__(self, canned_response: str, finish_reason: str = "stop"):
        self.completions = _FakeCompletions(canned_response, finish_reason)


class _FakeGroqClient:
    """Minimal stand-in for a `groq.Groq` client instance."""

    def __init__(self, canned_response: str = "", finish_reason: str = "stop"):
        self.chat = _FakeChat(canned_response, finish_reason)

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
        "statement_dependencies",
        "decision_chain_evidence_map",
        "loops",
        "table_operations",
        "calculations",
        "exception_handling",
        "ambiguities",
    ]
    assert compact["conditions"] == [{"condition": "x"}]
    assert compact["statement_dependencies"] == {"version": "1", "edges": []}
    assert compact["decision_chain_evidence_map"]["chains"] == [
        {
            "chain": "decision_chain_001",
            "source": "",
            "type": "",
            "branches": [],
            "affected_fields": [],
            "statement_ids": [],
            "parse_status": "parsed",
        }
    ]
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


def test_decision_chain_evidence_map_preserves_branches_locations_and_relationships():
    compact = RuleSynthesizerAgent._build_compact_synthesis_payload(
        {
            "decision_chains": [
                {
                    "chain_id": "chain_1",
                    "chain_type": "IF_ELSIF_ELSE",
                    "source_file": "classify.sql",
                    "source_line_start": 120,
                    "source_line_end": 145,
                    "branches": [
                        {
                            "branch_id": "chain_1:branch_001",
                            "branch_condition": "DPD > 90",
                            "source_line_start": 120,
                            "source_line_end": 128,
                            "source_statement_id": "stmt_7",
                            "assignments": [
                                {"field": "ASSET_CLASS", "value": "'NPA'"},
                            ],
                        },
                        {
                            "branch_id": "chain_1:branch_002",
                            "branch_condition": "ELSE",
                            "is_catch_all": True,
                            "evidence_spans": [
                                {"line_start": 129, "line_end": 145, "statement_id": "stmt_8"}
                            ],
                            "assignments": [
                                {"field": "ASSET_CLASS", "value": "'STANDARD'"},
                            ],
                        },
                    ],
                }
            ]
        },
        source_name="classify",
    )

    evidence = compact["decision_chain_evidence_map"]
    chain = evidence["chains"][0]
    assert chain["source"] == "classify.sql"
    assert chain["location"] == {"lines": "120-145"}
    assert chain["affected_fields"] == ["ASSET_CLASS"]
    assert [branch["condition"] for branch in chain["branches"]] == ["DPD > 90", "ELSE"]
    assert chain["branches"][0]["location"] == {"lines": "120-128"}
    assert chain["branches"][0]["statement_ids"] == ["stmt_7"]
    assert chain["branches"][1]["fallback"] is True
    assert chain["branches"][1]["statement_ids"] == ["stmt_8"]


def test_decision_chain_evidence_map_marks_unsupported_fragments_and_unknown_locations():
    compact = RuleSynthesizerAgent._build_compact_synthesis_payload(
        {
            "decision_chains": [
                {
                    "chain_id": "chain_dynamic",
                    "unsupported": True,
                    "unresolved_fragments": ["dynamic branch target"],
                    "branches": [
                        {
                            "branch_condition": "runtime predicate",
                            "assignments": [],
                        }
                    ],
                }
            ]
        }
    )

    chain = compact["decision_chain_evidence_map"]["chains"][0]
    assert chain["parse_status"] == "unsupported"
    assert chain["unresolved"] == ["dynamic branch target"]
    assert "location" not in chain["branches"][0]
    assert chain["branches"][0]["condition"] == "runtime predicate"


def test_decision_chain_evidence_map_is_bounded_for_wide_procedures(monkeypatch):
    chains = [
        {
            "chain_id": f"chain_{index}",
            "chain_type": "CASE",
            "branches": [
                {
                    "branch_id": f"branch_{index}_{branch}",
                    "branch_condition": "condition " + ("x" * 300),
                    "assignments": [
                        {"field": "FIELD", "value": "value " + ("y" * 300)},
                    ],
                }
                for branch in range(20)
            ],
        }
        for index in range(20)
    ]
    monkeypatch.setattr(
        "src.synthesis.rule_synthesizer._SYNTHESIS_EVIDENCE_MAP_MAX_CHARS",
        4000,
    )

    evidence = RuleSynthesizerAgent._build_decision_chain_evidence_map(chains)
    serialized = json.dumps(evidence, separators=(",", ":"), ensure_ascii=True)
    assert len(serialized) <= 4000
    assert evidence["bounded"] is True
    represented = sum(len(chain["branches"]) for chain in evidence["chains"])
    assert represented + evidence["omitted_branch_count"] == 400
    assert evidence.get("omitted_chain_count", 0) + len(evidence["chains"]) == len(chains)


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


def test_synthesize_is_section_appends_scope_note_only_when_set():
    """Real bug (live-generated report): every section of a sectioned
    synthesis run was asked for "the step-by-step flow" with no notion of
    seeing only a partial view, so each section independently guessed at
    the WHOLE object's flow from its own narrow slice - once an object
    needed many small sections (common under a tight per-call token
    budget), no single section ever saw enough to write a comprehensive
    flow, and the final report showed a shallow, partial flow. Confirms
    the prompt is unchanged by default (`is_section=False`, the existing
    single-call/whole-object path) and gets the section-scoping note
    appended only when a caller explicitly says this call is one section
    of a larger object.
    """
    agent = _make_agent(VALID_SYNTHESIS_JSON)
    agent.synthesize(
        object_name="demo", object_type="PROCEDURE",
        parameter_summary="No parameters.", merged_extraction={"conditions": []},
    )
    whole_object_prompt = agent.client.chat.completions.last_call_kwargs["messages"][1]["content"]
    assert "SECTION SCOPE" not in whole_object_prompt

    agent.synthesize(
        object_name="demo", object_type="PROCEDURE",
        parameter_summary="No parameters.", merged_extraction={"conditions": []},
        is_section=True,
    )
    section_prompt = agent.client.chat.completions.last_call_kwargs["messages"][1]["content"]
    assert "SECTION SCOPE" in section_prompt
    assert "ONLY the executable stages visible in THIS excerpt" in section_prompt
    # The rest of the prompt is otherwise identical - only the note is appended.
    assert section_prompt.startswith(whole_object_prompt)


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


class _QueuedFakeCompletions:
    """Returns a different canned response/finish_reason on each successive
    `create()` call, from a fixed queue - unlike `_FakeCompletions`, which
    always returns the same response. Needed to simulate "first call comes
    back malformed, retry comes back clean" without a real LLM.
    """

    def __init__(self, responses: list[tuple[str, str]]):
        self._responses = list(responses)
        self.calls: list[dict] = []
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        self.calls.append(kwargs)
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        content, finish_reason = self._responses[index]
        return _FakeCompletionResponse(content, finish_reason)


class _QueuedFakeClient:
    def __init__(self, responses: list[tuple[str, str]]):
        self.chat = type("Chat", (), {})()
        self.chat.completions = _QueuedFakeCompletions(responses)


def test_synthesize_retries_and_recovers_from_non_truncated_malformed_json():
    # `finish_reason="stop"` on both calls - the model reports it finished
    # normally, it just returned invalid JSON the first time (a formatting
    # slip, not a token-budget problem). Before the fix, only a truncated
    # (`finish_reason == "length"`) response got a retry; anything else
    # returned an empty result immediately, silently dropping every rule
    # that call would otherwise have produced.
    client = _QueuedFakeClient([
        ("this is not valid json at all {{{", "stop"),
        (VALID_SYNTHESIS_JSON, "stop"),
    ])
    agent = RuleSynthesizerAgent(client=client, model="m", temperature=0.1)

    result = agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )

    assert len(client.chat.completions.calls) == 2  # one bounded same-request retry
    assert result.parse_error == ""
    assert result.truncated is False
    assert len(result.data["business_rules"]) == 1
    assert result.data["business_rules"][0]["action"].startswith("Classified as Standard")


def test_synthesize_gives_up_after_one_retry_if_still_malformed():
    # Both calls malformed: exactly one retry is attempted (not an
    # unbounded loop), and the failure is still reported honestly rather
    # than fabricating a result.
    client = _QueuedFakeClient([
        ("still not valid json {{{", "stop"),
        ("also not valid json {{{", "stop"),
    ])
    agent = RuleSynthesizerAgent(client=client, model="m", temperature=0.1)

    result = agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )

    assert len(client.chat.completions.calls) == 2
    assert result.parse_error != ""
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


def test_truncated_synthesis_response_is_detected_via_finish_reason():
    client = _FakeGroqClient('{"business_rules":[{"condition":"x"', finish_reason="length")
    agent = RuleSynthesizerAgent(client=client, model="m", temperature=0.1)

    result = agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )

    assert result.truncated is True
    assert result.parse_error != ""
    assert len(client.chat.completions.calls) == 2  # one bounded ceiling retry


def test_truncated_response_recovers_partial_valid_rules_instead_of_discarding_all():
    response = (
        '{"business_rules":['
        '{"condition":"first condition","action":"first result",'
        '"fields_affected":["target_value"]},'
        '{"condition":"second condition"'
    )
    client = _FakeGroqClient(response, finish_reason="length")
    agent = RuleSynthesizerAgent(client=client, model="m", temperature=0.1)

    result = agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
    )

    assert result.truncated is True
    assert result.parse_error == ""
    assert [rule["condition"] for rule in result.data["business_rules"]] == [
        "first condition"
    ]
    assert any("output limit" in warning for warning in result.guardrail_warnings)


def test_max_tokens_scales_with_decision_point_count():
    client = _FakeGroqClient(VALID_SYNTHESIS_JSON)
    agent = RuleSynthesizerAgent(client=client, model="m", temperature=0.1)
    source = "BEGIN " + " ".join(
        f"IF flag_{idx} = 1 BEGIN SET value_{idx} = 1; END;" for idx in range(20)
    ) + " END;"

    agent.synthesize(
        object_name="obj",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
        dialect="tsql",
        raw_source=source,
    )

    assert client.chat.completions.last_call_kwargs["max_tokens"] > agent.max_tokens


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
    # Dialect is surfaced once, in the "At a Glance" table - the old
    # duplicate "**Dialect:** ..." bold line directly under the title was
    # removed since the table already carries it.
    assert "| Dialect | Oracle |" in report
    assert "**Dialect:**" not in report


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


def test_report_formatter_rejects_execution_semantics_as_business_purpose():
    """Evaluation-order commentary must never appear as Business Purpose."""
    assert ReportFormatterAgent._business_rule_business_meaning({
        "business_meaning": "First matching row wins; ELSE includes false or NULL predicates.",
    }) == "Not specified"
    assert ReportFormatterAgent._business_rule_business_meaning({
        "business_meaning": "Same as semantics",
        "execution_semantics": "Same as semantics",
    }) == "Not specified"


def test_remove_operation_only_rules_drops_read_only_select_framed_as_business_rule():
    read_rule = {
        "rule_id": "r_read",
        "rule_name": "Read DPD bucket history",
        "business_meaning": "Retrieve the last updated DPD bucket for each account.",
        "action": "Read the last updated DPD bucket",
        "output_field": "DpdBucket",
        "condition": "SELECT DpdBucket FROM DpdBucketHistory",
        "source_evidence": ["SELECT TOP 1 DpdBucket FROM DpdBucketHistory"],
        "decision_logic_rows": [],
    }
    keep_rule = {
        "rule_id": "r_keep",
        "rule_name": "Classify DPD bucket",
        "business_meaning": "Assign the overdue bucket.",
        "output_field": "DpdBucket",
        "decision_logic_rows": [
            {"condition": "DpdDays = 0", "outcome": "'CURRENT'"},
            {"condition": "ELSE", "outcome": "'BUCKET_90_PLUS'"},
        ],
    }
    kept = RuleSynthesizerAgent._remove_operation_only_rules([read_rule, keep_rule])
    assert [rule["rule_id"] for rule in kept] == ["r_keep"]


def test_remove_operation_only_rules_drops_read_titled_one_row_where_filter():
    """Model often pastes an INSERT's WHERE into a one-row table and titles
    the rule "Read ..." - still retrieval framing, not a business ladder.
    """
    read_rule = {
        "rule_id": "r_read",
        "rule_name": "Read loan and valuation details",
        "business_meaning": "Read the SecuredFlag from LoanAccountCal.",
        "fields_affected": ["SecuredFlag", "AccountId"],
        "decision_logic_rows": [
            {"condition": "SecuredFlag = 'Y' AND NOT EXISTS (...)", "outcome": "AccountId"},
        ],
    }
    keep_rule = {
        "rule_id": "r_keep",
        "rule_name": "Readiness gate",  # not a Read/Retrieve verb title
        "decision_logic_rows": [
            {"condition": "ReadyFlag = 'Y'", "outcome": "'GO'"},
            {"condition": "ELSE", "outcome": "'HOLD'"},
        ],
    }
    kept = RuleSynthesizerAgent._remove_operation_only_rules([read_rule, keep_rule])
    assert [rule["rule_id"] for rule in kept] == ["r_keep"]


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
        "LLM supplied label", "CUSTOM_CONDITION >= 7", "CUSTOM_FIELD", "LLM_VALUE",
    ):
        assert value in report
    assert "A.CUSTOM_CONDITION >= 7" not in report
    assert "LLM supplied meaning." in report
    # Eligibility (the WHERE/JOIN/IF gating condition) IS meant to reach the
    # report - it was a real accuracy defect that it didn't (see the
    # "Applies to:" rendering in _render_business_rule_block). Only the raw
    # `condition`/`action` fields are intentionally kept out, since their
    # business-language equivalent already lives in `business_meaning` /
    # the decision-logic table.
    assert "LLM supplied eligibility" in report
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


def test_synthesis_prompt_forbids_evaluation_order_titles_and_table_restatements():
    # Regression test for two real observed defects (see
    # docs/SMA_report_root_causes.md, "rule titles that read as duplicates"
    # and "a content-level duplicate survives even with unique titles"):
    # the model copied evaluation-order boilerplate ("First matching row
    # wins...") verbatim into "rule_name", and separately emitted a
    # narrative-only rule that restated, in prose, a decision table another
    # rule already carried for the same field(s). Both were previously
    # fixed only downstream in report_formatter.py; the prompt itself must
    # also tell the model not to do either in the first place.
    #
    # Checked against the three raw "system" keys directly (not through
    # `get_prompt_set`, which only ever accepts "oracle"/"tsql" - "default"
    # is an unreachable fallback for this file since both real dialects are
    # always explicitly defined, but it is still real prompt content worth
    # keeping in sync).
    from src.prompts.prompt_loader import _load_yaml

    data = _load_yaml("rule_synthesis.yaml")
    for dialect in ("default", "oracle", "tsql"):
        system_text = data["system"][dialect]
        assert "NEVER COPY EXECUTION-SEMANTICS" in system_text
        assert "SQL type conversion still applies" in system_text
        assert "DO NOT RESTATE A DECISION TABLE IN PROSE" in system_text


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
        "new_rules": [
            {
                "condition": "dpd.DPD_Max BETWEEN 1 AND 30",
                "action": "SMA_CLASS is set to SMA_0",
                "fields_affected": ["SMA_CLASS"],
                "source_evidence": ["dpd.DPD_Max BETWEEN 1 AND 30 -> 'SMA_0'"],
            },
        ],
        "obsolete_rule_ids": [],
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


def test_revise_sends_the_gap_snippet_and_references_existing_rules_by_id():
    client = _FakeGroqClient(REVISED_SYNTHESIS_JSON)
    agent = RuleSynthesizerAgent(client=client, model="llama-3.3-70b-versatile", temperature=0.1)
    # `rule_id` is always present by the time pipeline.py calls revise() -
    # every rule passes through `_normalize_business_rules`
    # (-> `unique_rule_ids`) before this point in the real flow.
    existing_rules = [{"rule_id": "r1", "condition": "x", "action": "y"}]
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
    # The untouched prior rule plus the one new rule the model added for
    # the previously-uncovered CASE ladder.
    assert len(result.data["business_rules"]) == 2
    sent_prompt = client.chat.completions.last_call_kwargs["messages"][1]["content"]
    assert "Lines 3-6" in sent_prompt
    assert "SMA_0" in sent_prompt
    # The existing rule is referenced by its id, not retyped in full - this
    # is the whole point of the redesign: no per-rule JSON echo cost.
    assert "r1" in sent_prompt
    assert '"action": "y"' not in sent_prompt
    assert '"action":"y"' not in sent_prompt


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
    agent.client.set_response(json.dumps({"new_rules": revised_rules, "obsolete_rule_ids": []}))
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


def test_auxiliary_calculation_rule_is_not_duplicated_in_business_rules():
    rules = [{
        "rule_name": "Calculate derived total",
        "business_meaning": "Calculates the derived total.",
        "action": "Calculates the derived total.",
        "output_field": "derived_total",
    }]
    assert RuleSynthesizerAgent._remove_auxiliary_rules(
        rules,
        {},
        calculations=[{"result": "derived_total", "formula": "base_value + adjustment"}],
    ) == []


def test_auxiliary_filter_keeps_calculation_with_real_decision_logic():
    rule = {
        "rule_name": "Calculate conditional total",
        "condition": "input_code = 1",
        "action": "Calculates the derived total.",
        "output_field": "derived_total",
        "decision_logic_rows": [{"condition": "input_code = 1", "outcome": "derived_total"}],
    }
    assert RuleSynthesizerAgent._remove_auxiliary_rules(
        [rule], {}, calculations=[{"result": "derived_total", "formula": "base + adjustment"}]
    ) == [rule]


def test_auxiliary_exception_rule_is_not_duplicated_in_business_rules():
    rule = {
        "rule_name": "Handle failure path",
        "business_meaning": "Handles the failure path.",
        "condition": "", "eligibility": [],
        "action": "Records the failure and raises it.",
    }
    assert RuleSynthesizerAgent._remove_auxiliary_rules(
        [rule], {"exception_handling": ["failure handler records the event"]}
    ) == []


def _dpd_bucket_chain():
    """Mirrors the real decision chain from
    `samples/07_DPD_Bucket_Classification.sql`'s `DpdBucket` CASE."""
    return {
        "chain_type": "CASE_EXPRESSION",
        "subject": "A.DpdDays",
        "branches": [
            {"branch_condition": "A.DpdDays IS NULL", "assignments": [{"field": "DpdBucket", "value": "'NOT_APPLICABLE'"}]},
            {"branch_condition": "A.DpdDays = 0", "assignments": [{"field": "DpdBucket", "value": "'CURRENT'"}]},
            {"branch_condition": "A.DpdDays BETWEEN 1 AND 30", "assignments": [{"field": "DpdBucket", "value": "'BUCKET_1_30'"}]},
            {"branch_condition": "A.DpdDays BETWEEN 31 AND 60", "assignments": [{"field": "DpdBucket", "value": "'BUCKET_31_60'"}]},
            {"branch_condition": "A.DpdDays BETWEEN 61 AND 90", "assignments": [{"field": "DpdBucket", "value": "'BUCKET_61_90'"}]},
            {"is_catch_all": True, "branch_condition": "ELSE", "assignments": [{"field": "DpdBucket", "value": "'BUCKET_90_PLUS'"}]},
        ],
    }


def test_blank_else_outcome_is_repaired_from_a_structurally_matching_decision_chain():
    """Regression for a real live-generated report
    (`samples/07_DPD_Bucket_Classification.sql`'s "DPD Bucket
    Classification" report): a model-authored rule reproduced every
    condition of the `DpdBucket` CASE exactly, but left its own final ELSE
    row's outcome blank - apparently running low on its own output budget
    right at the end. Because the rule already carried non-empty
    `decision_logic_rows`, the "no rows at all" backfill never ran, and the
    blank ELSE cell reached the rendered report. `_normalize_business_rules`
    must now repair just that blank cell from the deterministic chain,
    whose branch conditions line up with the rule's own rows one-for-one.
    """
    raw_rules = [{
        "rule_id": "r12",
        "rule_name": "Classify accounts into DPD buckets",
        "output_field": "DpdBucket",
        "fields_affected": ["DpdBucket"],
        "condition": "DpdDays is evaluated",
        "action": "Classify the account into a DPD bucket.",
        "decision_logic_rows": [
            {"condition": "DpdDays IS NULL", "outcome": "'NOT_APPLICABLE'"},
            {"condition": "DpdDays = 0", "outcome": "'CURRENT'"},
            {"condition": "DpdDays BETWEEN 1 AND 30", "outcome": "'BUCKET_1_30'"},
            {"condition": "DpdDays BETWEEN 31 AND 60", "outcome": "'BUCKET_31_60'"},
            {"condition": "DpdDays BETWEEN 61 AND 90", "outcome": "'BUCKET_61_90'"},
            {"condition": "ELSE", "outcome": ""},  # left blank by the model
        ],
        "business_meaning": "Classifies DPD accounts into buckets.",
        "rule_type": "explicit",
        "confidence": "medium",
        "validation_status": "verified",
    }]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules, technical_context={"decision_chains": [_dpd_bucket_chain()]}
    )

    rows = normalized[0]["decision_logic_rows"]
    assert len(rows) == 6
    assert rows[-1]["condition"] == "ELSE"
    assert rows[-1]["outcome"] == "'BUCKET_90_PLUS'"
    # Every other row's model-authored outcome is left exactly as-is.
    assert rows[1]["outcome"] == "'CURRENT'"


def test_repair_does_not_touch_a_rule_whose_conditions_do_not_line_up():
    """A rule sharing the same output_field but with a genuinely different
    (or shorter/reordered) set of conditions than any decision chain must
    not be "repaired" - the structural match requires every condition to
    line up one-for-one, in order, not just a shared field name."""
    raw_rules = [{
        "rule_id": "r1",
        "rule_name": "Different classification",
        "output_field": "DpdBucket",
        "fields_affected": ["DpdBucket"],
        "condition": "some other condition",
        "action": "Assign a bucket by a different rule entirely.",
        "decision_logic_rows": [
            {"condition": "DpdDays <= 30", "outcome": "1"},
            {"condition": "DpdDays > 30", "outcome": ""},
        ],
        "business_meaning": "Unrelated classification.",
        "rule_type": "explicit",
        "confidence": "medium",
        "validation_status": "verified",
    }]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules, technical_context={"decision_chains": [_dpd_bucket_chain()]}
    )

    rows = normalized[0]["decision_logic_rows"]
    assert rows[1]["outcome"] == ""  # left untouched - no structural match


def test_repair_never_overwrites_a_non_blank_outcome():
    """Even when a rule qualifies for repair (one blank row), any row that
    already has its own non-blank outcome must be left exactly as the
    model authored it, never replaced by the deterministic chain's value -
    the repair only ever fills in what's missing."""
    raw_rules = [{
        "rule_id": "r1",
        "rule_name": "Classify accounts into DPD buckets",
        "output_field": "DpdBucket",
        "fields_affected": ["DpdBucket"],
        "condition": "DpdDays is evaluated",
        "action": "Classify the account into a DPD bucket.",
        "decision_logic_rows": [
            {"condition": "DpdDays IS NULL", "outcome": "'NOT_APPLICABLE'"},
            {"condition": "DpdDays = 0", "outcome": "'CURRENT_CUSTOM_TEXT'"},  # authored differently, but non-blank
            {"condition": "DpdDays BETWEEN 1 AND 30", "outcome": "'BUCKET_1_30'"},
            {"condition": "DpdDays BETWEEN 31 AND 60", "outcome": "'BUCKET_31_60'"},
            {"condition": "DpdDays BETWEEN 61 AND 90", "outcome": "'BUCKET_61_90'"},
            {"condition": "ELSE", "outcome": ""},
        ],
        "business_meaning": "Classifies DPD accounts into buckets.",
        "rule_type": "explicit",
        "confidence": "medium",
        "validation_status": "verified",
    }]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules, technical_context={"decision_chains": [_dpd_bucket_chain()]}
    )

    rows = normalized[0]["decision_logic_rows"]
    assert rows[1]["outcome"] == "'CURRENT_CUSTOM_TEXT'"
    assert rows[-1]["outcome"] == "'BUCKET_90_PLUS'"


def test_blank_first_row_outcome_is_repaired_even_with_a_qualified_output_field():
    """Regression for a real live-generated report
    (`samples/07_DPD_Bucket_Classification.sql`'s R2 "Determine DpdBucket"
    table): the model left the FIRST branch's outcome blank (`DpdDays IS
    NULL` -> should be 'NOT_APPLICABLE'), not the last, and authored
    `output_field` as a fully schema-qualified reference
    (`PRO.LoanAccountCal.DpdBucket`) rather than the bare `DpdBucket` the
    deterministic chain's own assignments use. The old strict
    `field.lower() == output_field.lower()` comparison never matched a
    qualified `output_field` against the chain's bare field name, so
    repair silently no-opped and the blank cell reached the report -
    field comparisons must collapse to the bare trailing segment, the same
    way condition comparisons already do.
    """
    raw_rules = [{
        "rule_id": "r2",
        "rule_name": "Determine DpdBucket",
        "output_field": "PRO.LoanAccountCal.DpdBucket",
        "fields_affected": ["PRO.LoanAccountCal.DpdBucket"],
        "condition": "DpdDays is evaluated",
        "action": "Assign a DPD bucket to each account.",
        "decision_logic_rows": [
            {"condition": "PRO.LoanAccountCal.DpdDays IS NULL", "outcome": ""},  # left blank by the model
            {"condition": "PRO.LoanAccountCal.DpdDays = 0", "outcome": "'CURRENT'"},
            {"condition": "PRO.LoanAccountCal.DpdDays BETWEEN 1 AND 30", "outcome": "'BUCKET_1_30'"},
            {"condition": "PRO.LoanAccountCal.DpdDays BETWEEN 31 AND 60", "outcome": "'BUCKET_31_60'"},
            {"condition": "PRO.LoanAccountCal.DpdDays BETWEEN 61 AND 90", "outcome": "'BUCKET_61_90'"},
            {"condition": "ELSE", "outcome": "'BUCKET_90_PLUS'"},
        ],
        "business_meaning": "Classifies DPD accounts into buckets.",
        "rule_type": "explicit",
        "confidence": "medium",
        "validation_status": "verified",
    }]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules, technical_context={"decision_chains": [_dpd_bucket_chain()]}
    )

    rows = normalized[0]["decision_logic_rows"]
    assert rows[0]["condition"] == "PRO.LoanAccountCal.DpdDays IS NULL"
    assert rows[0]["outcome"] == "'NOT_APPLICABLE'"

def test_nested_list_inside_fields_affected_is_flattened():
    """A model can return `fields_affected` with a NESTED list as one of
    its own items (e.g. `["SeverityTier", ["FeedName", "Outcome"]]`)
    instead of a flat list of field names. Left as-is, that inner list
    string-reprs straight into the rendered report ("SeverityTier,
    ['FeedName', 'Outcome']") - normalization must flatten it so every
    downstream caller can keep assuming a flat list of scalar field names.
    """
    raw_rules = [
        {
            "rule_id": "r1",
            "rule_name": "Insert reconciliation results",
            "output_field": "SeverityTier",
            "fields_affected": ["SeverityTier", ["FeedName", "Outcome", "ReconciledOn"]],
            "business_meaning": "Insert reconciliation results.",
            "rule_type": "explicit",
        },
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)

    assert normalized[0]["fields_affected"] == ["SeverityTier", "FeedName", "Outcome", "ReconciledOn"]
    assert not any(isinstance(item, list) for item in normalized[0]["fields_affected"])


# --------------------------------------------------------------------------
# Regression: the coverage-review pass must never REDUCE coverage.
#
# `_decode_json_payload` falls back to `json.JSONDecoder().raw_decode`, which
# successfully decodes a *prefix* of a cut-off response. That meant a
# revise() call which hit the model's output ceiling could parse "cleanly"
# while carrying only the first few of the rules it was told to echo back,
# and pipeline.py then assigned that shortened array straight over the good
# one. On a small-ceiling model (Amazon Nova Lite: 5000 completion tokens)
# echoing a large existing rule set back is guaranteed to truncate, so the
# pass designed to close coverage gaps actively destroyed rules instead.
# --------------------------------------------------------------------------


def test_revise_discards_truncated_response_instead_of_shrinking_rule_set():
    """A revise() response cut off at the token ceiling must be rejected.

    The payload below is valid, parseable JSON carrying a `new_rules` array
    with one entry - i.e. what a truncated response looks like after
    `raw_decode` salvages a JSON-valid prefix of a longer intended array.
    With `finish_reason="length"` the agent must return None so the caller
    keeps its existing rules rather than trusting a response that might be
    missing everything after the cut.
    """
    salvageable_prefix = json.dumps(
        {"new_rules": [{"condition": "only the first new rule survived"}]}
    )
    client = _FakeGroqClient(salvageable_prefix, finish_reason="length")
    agent = RuleSynthesizerAgent(
        client=client, model="llama-3.3-70b-versatile", temperature=0.1
    )
    gap = CoverageGap(line_start=1, line_end=2, snippet="IF x THEN y", keywords=["IF"])

    result = agent.revise(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="",
        merged_extraction={},
        existing_rules=[
            {"rule_id": "r1", "condition": "rule one"},
            {"rule_id": "r2", "condition": "rule two"},
            {"rule_id": "r3", "condition": "rule three"},
        ],
        gaps=[gap],
    )

    # Parseable, but truncated -> must be discarded, not returned.
    assert result is None


def test_revise_still_accepts_an_untruncated_response():
    """Guard against the truncation check over-firing: a normal
    `finish_reason="stop"` revision must still come back."""
    client = _FakeGroqClient(REVISED_SYNTHESIS_JSON, finish_reason="stop")
    agent = RuleSynthesizerAgent(
        client=client, model="llama-3.3-70b-versatile", temperature=0.1
    )
    gap = CoverageGap(line_start=1, line_end=2, snippet="IF x THEN y", keywords=["IF"])

    result = agent.revise(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="",
        merged_extraction={},
        existing_rules=[{"rule_id": "r1", "condition": "x", "action": "y"}],
        gaps=[gap],
    )

    assert result is not None
    assert len(result.data["business_rules"]) == 2


def test_revise_budgets_output_tokens_against_gap_count_not_rule_count():
    """revise() no longer asks the model to echo the whole rule set back,
    so its output budget must scale with how many gaps are under review -
    NOT with the number of already-accepted rules (which used to drive
    `_output_token_budget(raw_source)` and made a revision request as
    expensive as a full resynthesis on a large, mostly-correct object).
    A request budgeted for 1 gap must be smaller than one budgeted for 20.
    """
    client = _FakeGroqClient(REVISED_SYNTHESIS_JSON)
    agent = RuleSynthesizerAgent(
        client=client,
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=1024,
        hard_max_output_tokens=32768,
    )
    # A large existing rule set that, under the OLD echo-based design,
    # would have inflated the requested budget on its own.
    existing_rules = [{"rule_id": f"r{i}", "condition": f"rule {i}"} for i in range(150)]

    small_gap = [CoverageGap(line_start=1, line_end=2, snippet="IF x THEN y", keywords=["IF"])]
    many_gaps = [
        CoverageGap(line_start=i, line_end=i + 1, snippet=f"IF x{i} THEN y{i}", keywords=["IF"])
        for i in range(20)
    ]

    agent.revise(
        object_name="demo", object_type="PROCEDURE", parameter_summary="",
        merged_extraction={}, existing_rules=existing_rules, gaps=small_gap,
    )
    small_budget = client.chat.completions.last_call_kwargs["max_tokens"]

    agent.revise(
        object_name="demo", object_type="PROCEDURE", parameter_summary="",
        merged_extraction={}, existing_rules=existing_rules, gaps=many_gaps,
    )
    large_budget = client.chat.completions.last_call_kwargs["max_tokens"]

    assert large_budget > small_budget, (
        "revise()'s output budget should scale with how many gaps are "
        "under review, not stay flat regardless of review scope"
    )


def test_revise_does_not_inflate_prompt_size_with_rule_count():
    """The single biggest lever against the TPM 413 this fixes: the sent
    prompt must stay small even when there are hundreds of already-accepted
    rules, because they are referenced by id in a compact index rather than
    retyped in full JSON."""
    client = _FakeGroqClient(REVISED_SYNTHESIS_JSON)
    agent = RuleSynthesizerAgent(client=client, model="llama-3.3-70b-versatile", temperature=0.1)
    existing_rules = [
        {
            "rule_id": f"r{i}",
            "condition": f"some fairly verbose business condition number {i} " * 3,
            "action": f"some fairly verbose business action number {i} " * 3,
            "source_evidence": [f"evidence line {i}"] * 4,
            "fields_affected": [f"FIELD_{i}"],
        }
        for i in range(150)
    ]
    gap = CoverageGap(line_start=1, line_end=2, snippet="IF x THEN y", keywords=["IF"])

    agent.revise(
        object_name="demo", object_type="PROCEDURE", parameter_summary="",
        merged_extraction={}, existing_rules=existing_rules, gaps=[gap],
    )

    sent_prompt = client.chat.completions.last_call_kwargs["messages"][1]["content"]
    # None of the verbose full-field content should appear - only compact
    # "id: short label" index lines.
    assert "fairly verbose business action" not in sent_prompt
    assert "evidence line" not in sent_prompt

    # Compare against what the OLD design (full JSON echo of every existing
    # rule) would have cost for the same 150 rules, to anchor the assertion
    # in the actual regression rather than an arbitrary constant that could
    # drift as the fixed template text grows.
    old_style_echo_cost = len(
        json.dumps(existing_rules, separators=(",", ":"), default=str)
    )
    assert len(sent_prompt) < old_style_echo_cost, (
        "compact id-based referencing should cost less prompt space than "
        "retyping every existing rule's full JSON would have"
    )


# --------------------------------------------------------------------------
# Pre-flight LLM_TPM_LIMIT guard - integration with synthesize()/revise().
#
# Unit coverage for the underlying helpers (`estimate_prompt_tokens`,
# `resolve_tpm_limit`, `clamp_tokens_for_tpm`) lives in test_llm_client.py.
# These tests confirm the two call sites actually use them: `synthesize()`
# fails fast with an actionable error when even the whole object can't
# reasonably be attempted, and `revise()` skips gracefully (returns None,
# same as "no gaps" or "malformed JSON") rather than sending a doomed
# request that would 413.
# --------------------------------------------------------------------------


def test_synthesize_raises_actionable_error_when_prompt_cannot_fit_tpm_budget(monkeypatch):
    monkeypatch.setenv("LLM_TPM_LIMIT", "500")  # far smaller than any real prompt
    agent = _make_agent(json.dumps({"business_rules": []}))

    with pytest.raises(PromptTooLargeForRateLimitError) as excinfo:
        agent.synthesize(
            object_name="demo",
            object_type="PROCEDURE",
            parameter_summary="",
            merged_extraction={},
            dialect="tsql",
            raw_source="IF x = 1 THEN y = 2;",
        )

    message = str(excinfo.value)
    assert "LLM_TPM_LIMIT" in message
    assert "500" in message


def test_synthesize_does_not_raise_when_tpm_limit_is_unset():
    """No `LLM_TPM_LIMIT` configured -> the guard is a no-op, exactly like
    before this feature existed."""
    agent = _make_agent(json.dumps({"business_rules": []}))
    result = agent.synthesize(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="",
        merged_extraction={},
        dialect="tsql",
        raw_source="IF x = 1 THEN y = 2;",
    )
    assert result is not None


def test_revise_returns_none_gracefully_when_prompt_cannot_fit_tpm_budget(monkeypatch):
    monkeypatch.setenv("LLM_TPM_LIMIT", "500")
    agent = _make_agent(REVISED_SYNTHESIS_JSON)
    gap = CoverageGap(line_start=1, line_end=2, snippet="IF x THEN y", keywords=["IF"])

    result = agent.revise(
        object_name="demo",
        object_type="PROCEDURE",
        parameter_summary="",
        merged_extraction={},
        existing_rules=[{"rule_id": "r1", "condition": "x", "action": "y"}],
        gaps=[gap],
    )

    # Skipped gracefully - same contract as no-gaps/unsupported-dialect/
    # malformed-JSON: caller keeps its existing rules, gap stays flagged.
    assert result is None


# --------------------------------------------------------------------------
# Regression: section PLANNING must account for the account's real TPM
# ceiling, not just the model's raw completion capability.
#
# Without this, a small-to-medium object that comfortably fits a model's
# raw output ceiling (e.g. openai/gpt-oss-120b: 65,536 completion tokens)
# was judged "no sectioning needed" and sent as one single-pass call - even
# though that call's prompt (system prompt + template + evidence payload)
# does NOT fit under a much smaller account-level TPM ceiling (Groq free
# tier: 8,000 tokens total). The pre-flight TPM guard then correctly
# refused that oversized call, `synthesize()` raised, and pipeline.py's
# per-section try/except (see pipeline.py::_run_section) turned that into
# a completely empty result for the WHOLE object - not a partial one.
# Live symptom: a 176-line, 55-decision-point procedure came back with 0
# of its ~10 real rules and a "Needs Review" line for nearly the entire
# source.
# --------------------------------------------------------------------------


def test_sectioning_ceiling_is_unaffected_when_tpm_limit_is_unset():
    """No `LLM_TPM_LIMIT` configured -> sectioning decisions are exactly
    what they were before this feature existed."""
    agent = RuleSynthesizerAgent(
        client=_FakeGroqClient("{}"),
        model="openai/gpt-oss-120b",
        provider="groq",
        temperature=0.1,
        hard_max_output_tokens=65536,
    )
    assert agent._sectioning_ceiling() == 65536


def test_requires_sectioned_synthesis_accounts_for_tpm_not_just_model_ceiling(monkeypatch):
    """The exact live-reported failure, reproduced deterministically: a
    55-decision-point object (DPD_Bucket_Classification-sized) that fits
    comfortably under a model's raw 65,536-token ceiling must still be
    recognized as needing sectioning once the account's real TPM ceiling
    (8,000) is configured - because a single-pass call over it does not
    fit once the ~5,000+ token fixed prompt overhead is counted.
    """
    monkeypatch.setenv("LLM_TPM_LIMIT", "8000")
    agent = RuleSynthesizerAgent(
        client=_FakeGroqClient("{}"),
        model="openai/gpt-oss-120b",
        provider="groq",
        temperature=0.1,
        hard_max_output_tokens=65536,
    )
    raw_source = "\n".join(f"IF x{i} = 1 THEN SET y{i} = 2;" for i in range(55))

    # Sanity: this object genuinely fits the model's raw capability alone -
    # the old, TPM-blind check would have said "no sectioning needed" here.
    assert agent._estimate_output_tokens(raw_source) < agent.hard_max_output_tokens

    assert agent.requires_sectioned_synthesis(raw_source) is True


def test_plan_synthesis_sections_shrinks_section_budget_under_tight_tpm(monkeypatch):
    """`plan_synthesis_sections` must plan smaller sections (lower
    decision-point budget per section) once `LLM_TPM_LIMIT` makes the
    real usable ceiling much smaller than the model's raw capability -
    this is what actually prevents an oversized section from ever being
    attempted (and therefore ever being silently dropped whole)."""
    agent_unlimited = RuleSynthesizerAgent(
        client=_FakeGroqClient("{}"), model="openai/gpt-oss-120b",
        provider="groq", temperature=0.1, hard_max_output_tokens=65536,
    )
    # Captured now, before LLM_TPM_LIMIT is set - `_sectioning_ceiling`
    # reads the environment live on every call (not cached at
    # construction), so this must be read BEFORE the env var changes below,
    # not re-read afterward.
    unlimited_ceiling = agent_unlimited._sectioning_ceiling()
    assert unlimited_ceiling == 65536

    monkeypatch.setenv("LLM_TPM_LIMIT", "8000")
    agent_limited = RuleSynthesizerAgent(
        client=_FakeGroqClient("{}"), model="openai/gpt-oss-120b",
        provider="groq", temperature=0.1, hard_max_output_tokens=65536,
    )
    assert agent_limited._sectioning_ceiling() < unlimited_ceiling
    assert agent_limited._sectioning_ceiling() < 5000  # well under the 8000 TPM itself