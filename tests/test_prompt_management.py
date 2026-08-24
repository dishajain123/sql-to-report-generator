"""
Prompt management tests.

These tests ensure the LLM-facing agents source their prompts from YAML
via the shared loader and that the required prompt files/keys are
present for both supported dialects.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agents.logic_extractor as logic_module
import agents.rule_synthesizer as synth_module
from prompts.prompt_loader import get_prompt_set


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
    def __init__(self, canned_response: str):
        self.canned_response = canned_response
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        return _FakeCompletionResponse(self.canned_response)


class _FakeChat:
    def __init__(self, canned_response: str):
        self.completions = _FakeCompletions(canned_response)


class _FakeClient:
    def __init__(self, canned_response: str):
        self.chat = _FakeChat(canned_response)


def test_required_prompt_files_exist_for_supported_dialects():
    for filename in ("logic_extraction.yaml", "rule_synthesis.yaml"):
        for dialect in ("oracle", "tsql"):
            prompt_set = get_prompt_set(filename, dialect=dialect)
            assert prompt_set["system"].strip()
            assert prompt_set["user_template"].strip()


def test_logic_extractor_uses_yaml_prompt_loader(monkeypatch):
    calls = []

    def fake_get_prompt_set(filename: str, dialect: str = "oracle"):
        calls.append((filename, dialect))
        return {"system": "SYS_LOGIC", "user_template": "USER_LOGIC {object_name} {dialect}"}

    def fake_render_user_prompt(template: str, **kwargs):
        return template.format(**kwargs)

    monkeypatch.setattr(logic_module, "get_prompt_set", fake_get_prompt_set)
    monkeypatch.setattr(logic_module, "render_user_prompt", fake_render_user_prompt)

    client = _FakeClient(
        json.dumps(
            {
                "conditions": [],
                "loops": [],
                "tables_read": [],
                "tables_written": [],
                "calculations": [],
                "exception_handling": [],
                "ambiguities": [],
            }
        )
    )
    agent = logic_module.LogicExtractionAgent(client=client, model="test-model")
    agent.extract(
        chunk_id="00_main_body",
        chunk_kind="main_body",
        code_chunk="BEGIN NULL; END;",
        rag_context="context",
        object_type="PROCEDURE",
        object_name="demo_proc",
        dialect="oracle",
    )

    assert calls == [("logic_extraction.yaml", "oracle")]
    assert client.chat.completions.last_call_kwargs["messages"][0]["content"] == "SYS_LOGIC"
    assert client.chat.completions.last_call_kwargs["messages"][1]["content"] == (
        "USER_LOGIC demo_proc oracle"
    )


def test_rule_synthesizer_uses_yaml_prompt_loader(monkeypatch):
    calls = []

    def fake_get_prompt_set(filename: str, dialect: str = "oracle"):
        calls.append((filename, dialect))
        return {"system": "SYS_RULE", "user_template": "USER_RULE {object_name} {dialect}"}

    def fake_render_user_prompt(template: str, **kwargs):
        return template.format(**kwargs)

    monkeypatch.setattr(synth_module, "get_prompt_set", fake_get_prompt_set)
    monkeypatch.setattr(synth_module, "render_user_prompt", fake_render_user_prompt)

    client = _FakeClient(
        json.dumps(
            {
                "purpose_summary": "Summary",
                "step_by_step_flow": [],
                "business_rules": [],
                "calculations": [],
                "exception_handling_summary": "",
                "ambiguities": [],
            }
        )
    )
    agent = synth_module.RuleSynthesizerAgent(client=client, model="test-model")
    agent.synthesize(
        object_name="demo_proc",
        object_type="PROCEDURE",
        parameter_summary="none",
        merged_extraction={},
        dialect="tsql",
    )

    assert calls == [("rule_synthesis.yaml", "tsql")]
    assert client.chat.completions.last_call_kwargs["messages"][0]["content"] == "SYS_RULE"
    assert client.chat.completions.last_call_kwargs["messages"][1]["content"] == (
        "USER_RULE demo_proc tsql"
    )
