from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import src.core.llm_client as llm_client
from src.core.llm_client import create_llm_client, load_llm_config, supports_chat_completion_seed


def test_load_llm_config_infers_bedrock_from_legacy_model_and_aws_env(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL_NAME", raising=False)
    monkeypatch.setenv("GPT_MODEL", "bedrock/amazon.nova-lite-v1:0")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAEXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret-example")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    config = load_llm_config()

    assert config.provider == "bedrock"
    assert config.api_key == ""
    assert config.model_name == "amazon.nova-lite-v1:0"
    assert config.aws_access_key_id == "AKIAEXAMPLE"
    assert config.aws_secret_access_key == "secret-example"
    assert config.aws_region == "us-east-1"


def test_load_llm_config_supports_groq_without_changing_bedrock_settings(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("GROQ_MODEL_NAME", "groq-test-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL_NAME", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    config = load_llm_config()

    assert config.provider == "groq"
    assert config.api_key == "groq-test-key"
    assert config.model_name == "groq-test-model"
    assert config.base_url == "https://api.groq.com/openai/v1"


def test_groq_client_uses_openai_compatible_endpoint(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(llm_client, "OpenAI", FakeOpenAI)
    config = SimpleNamespace(
        provider="groq",
        api_key="groq-test-key",
        model_name="groq-test-model",
        base_url="https://api.groq.com/openai/v1",
    )

    create_llm_client(config)

    assert captured == {
        "api_key": "groq-test-key",
        "base_url": "https://api.groq.com/openai/v1",
    }


def test_load_llm_config_supports_local_ollama_without_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL_NAME", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL_NAME", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    config = load_llm_config()

    assert config.provider == "ollama"
    assert config.api_key == "ollama"
    assert config.model_name == "llama3.1:8b"
    assert config.base_url == "http://localhost:11434/v1"


def test_bedrock_client_exposes_openai_like_chat_api(monkeypatch):
    monkeypatch.setattr(llm_client, "boto3", None)
    monkeypatch.setattr(llm_client, "BotoConfig", None)

    config = SimpleNamespace(
        provider="bedrock",
        api_key="",
        model_name="amazon.nova-lite-v1:0",
        base_url=None,
        aws_access_key_id="AKIAEXAMPLE",
        aws_secret_access_key="secret-example",
        aws_session_token="",
        aws_region="us-east-1",
    )
    client = create_llm_client(config)
    assert not supports_chat_completion_seed(client)

    captured = {}

    def fake_sender(request):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode("utf-8")
        response = {
            "output": {"message": {"content": [{"text": "hello"}]}},
            "usage": {"inputTokens": 12, "outputTokens": 5, "totalTokens": 17},
        }
        return SimpleNamespace(
            read=lambda: json.dumps(response).encode("utf-8"),
            close=lambda: None,
        )

    client.chat.completions._transport._request_sender = fake_sender
    response = client.chat.completions.create(
        model="bedrock/amazon.nova-lite-v1:0",
        messages=[
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"},
        ],
        temperature=0.1,
    )

    assert response.choices[0].message.content == "hello"
    assert response.usage.prompt_tokens == 12
    assert response.usage.completion_tokens == 5
    assert response.usage.total_tokens == 17
    assert "/model/amazon.nova-lite-v1%3A0/converse" in captured["url"]
    assert "%3A" in captured["url"]
    assert "system prompt" in captured["body"]
    assert "user prompt" in captured["body"]


def test_bedrock_client_caps_output_limit_for_nova_lite(monkeypatch):
    monkeypatch.setattr(llm_client, "boto3", None)
    monkeypatch.setattr(llm_client, "BotoConfig", None)

    payload = llm_client._BedrockRuntimeTransport._build_payload(
        [{"role": "user", "content": "prompt"}],
        max_tokens=16000,
    )

    assert payload["inferenceConfig"]["maxTokens"] == 9999


def test_bedrock_client_uses_boto3_default_chain_when_explicit_credentials_are_absent(monkeypatch):
    calls = {}

    class _FakeBedrockClient:
        def converse(self, **kwargs):
            calls["converse_kwargs"] = kwargs
            return {
                "output": {"message": {"content": [{"text": "hello"}]}},
                "usage": {"inputTokens": 12, "outputTokens": 5, "totalTokens": 17},
            }

    class _FakeBoto3Module:
        def client(self, service_name, **kwargs):
            calls["service_name"] = service_name
            calls["client_kwargs"] = kwargs
            return _FakeBedrockClient()

    monkeypatch.setattr(llm_client, "boto3", _FakeBoto3Module())
    monkeypatch.setattr(llm_client, "BotoConfig", lambda **kwargs: {"retries": kwargs.get("retries")})

    config = SimpleNamespace(
        provider="bedrock",
        api_key="",
        model_name="amazon.nova-lite-v1:0",
        base_url=None,
        aws_access_key_id="",
        aws_secret_access_key="",
        aws_session_token="",
        aws_region="us-east-1",
    )
    client = create_llm_client(config)
    response = client.chat.completions.create(
        model="bedrock/amazon.nova-lite-v1:0",
        messages=[
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"},
        ],
        temperature=0.1,
    )

    assert calls["service_name"] == "bedrock-runtime"
    assert calls["client_kwargs"]["region_name"] == "us-east-1"
    assert "aws_access_key_id" not in calls["client_kwargs"]
    assert "aws_secret_access_key" not in calls["client_kwargs"]
    assert response.choices[0].message.content == "hello"
    assert response.usage.prompt_tokens == 12
    assert response.usage.completion_tokens == 5
    assert response.usage.total_tokens == 17
    assert calls["converse_kwargs"]["modelId"] == "amazon.nova-lite-v1:0"
    assert calls["converse_kwargs"]["messages"]
    assert calls["converse_kwargs"]["system"]
