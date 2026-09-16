from __future__ import annotations

import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

import src.core.llm_client as llm_client
from src.core.llm_client import (
    LLMTransientError,
    call_with_retry,
    create_llm_client,
    load_llm_config,
    supports_chat_completion_seed,
)


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


def test_signed_request_date_header_is_valid_amz_date_format(monkeypatch):
    """Regression test for the datetime.utcnow() deprecation fix (Python
    3.12+ warns on the naive-UTC utcnow()/utcfromtimestamp() APIs): the
    SigV4 signing helper must keep producing the exact same amz-date
    format (YYYYMMDDTHHMMSSZ) using the timezone-aware
    datetime.now(timezone.utc) replacement."""
    monkeypatch.setattr(llm_client, "boto3", None)
    monkeypatch.setattr(llm_client, "BotoConfig", None)

    transport = llm_client._BedrockRuntimeTransport(
        access_key_id="AKIAEXAMPLE",
        secret_access_key="secret-example",
        region="us-east-1",
        session_token=None,
    )
    request = transport._signed_request(url="https://example.amazonaws.com/model/x/converse", body=b"{}")

    amz_date = request.headers.get("X-amz-date") or request.get_header("X-amz-date")
    assert amz_date is not None
    import re as _re

    assert _re.fullmatch(r"\d{8}T\d{6}Z", amz_date)


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


# --------------------------------------------------------------------------
# Retry/backoff regression tests (audit fix: the Bedrock raw-HTTP fallback
# path previously had zero retry logic at all - a single rate-limit or
# timeout blip aborted the whole call). `call_with_retry` is the generic,
# reusable retry primitive; the tests below cover it directly plus its two
# wiring points in `_BedrockRuntimeTransport`.
# --------------------------------------------------------------------------


def test_call_with_retry_succeeds_after_transient_failure(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise LLMTransientError("temporary rate limit")
        return "ok"

    result = call_with_retry(flaky, max_attempts=3, base_delay=0.01, max_delay=0.02)

    assert result == "ok"
    assert attempts["count"] == 2


def test_call_with_retry_exhausts_and_reraises(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)
    attempts = {"count": 0}

    def always_flaky():
        attempts["count"] += 1
        raise LLMTransientError("still rate limited")

    with pytest.raises(LLMTransientError):
        call_with_retry(always_flaky, max_attempts=3, base_delay=0.01, max_delay=0.02)

    assert attempts["count"] == 3


def test_call_with_retry_does_not_retry_permanent_errors(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)
    attempts = {"count": 0}

    def permanently_broken():
        attempts["count"] += 1
        raise RuntimeError("bad request")

    with pytest.raises(RuntimeError, match="bad request"):
        call_with_retry(permanently_broken, max_attempts=3, base_delay=0.01, max_delay=0.02)

    assert attempts["count"] == 1


def _make_raw_http_transport(monkeypatch) -> "llm_client._BedrockRuntimeTransport":
    monkeypatch.setattr(llm_client, "boto3", None)
    monkeypatch.setattr(llm_client, "BotoConfig", None)
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)
    return llm_client._BedrockRuntimeTransport(
        access_key_id="AKIAEXAMPLE",
        secret_access_key="secret-example",
        region="us-east-1",
        session_token=None,
    )


def test_bedrock_raw_http_retries_on_429_then_succeeds(monkeypatch):
    transport = _make_raw_http_transport(monkeypatch)
    calls = {"count": 0}
    success_body = json.dumps(
        {
            "output": {"message": {"content": [{"text": "hello"}]}},
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }
    ).encode("utf-8")

    def fake_sender(request):
        calls["count"] += 1
        if calls["count"] == 1:
            raise HTTPError(request.full_url, 429, "Too Many Requests", {}, io.BytesIO(b"rate limited"))
        return SimpleNamespace(read=lambda: success_body, close=lambda: None)

    transport._request_sender = fake_sender

    response = transport.invoke(model="amazon.nova-lite-v1:0", messages=[{"role": "user", "content": "hi"}])

    assert calls["count"] == 2
    assert response.choices[0].message.content == "hello"


def test_bedrock_raw_http_400_is_not_retried(monkeypatch):
    transport = _make_raw_http_transport(monkeypatch)
    calls = {"count": 0}

    def fake_sender(request):
        calls["count"] += 1
        raise HTTPError(request.full_url, 400, "Bad Request", {}, io.BytesIO(b"malformed payload"))

    transport._request_sender = fake_sender

    with pytest.raises(RuntimeError, match="Bedrock invocation failed: 400"):
        transport.invoke(model="amazon.nova-lite-v1:0", messages=[{"role": "user", "content": "hi"}])

    assert calls["count"] == 1


def test_bedrock_raw_http_network_error_is_retried_then_exhausts(monkeypatch):
    transport = _make_raw_http_transport(monkeypatch)
    calls = {"count": 0}

    def fake_sender(request):
        calls["count"] += 1
        raise URLError("connection refused")

    transport._request_sender = fake_sender

    with pytest.raises(RuntimeError, match="Bedrock invocation failed: connection refused"):
        transport.invoke(model="amazon.nova-lite-v1:0", messages=[{"role": "user", "content": "hi"}])

    # Default max_attempts=3 inside call_with_retry.
    assert calls["count"] == 3


# --------------------------------------------------------------------------
# TPM (tokens-per-minute) pre-flight budgeting helpers.
#
# These exist because a model's MAX COMPLETION TOKENS (what
# `resolve_model_output_ceiling` reports - the model's raw capability) and
# an account's actual per-minute rate limit are two unrelated numbers.
# Groq's free tier caps `openai/gpt-oss-120b` at 8,000 TOTAL tokens/minute
# even though the model itself can emit up to 65,536 completion tokens per
# call on a higher tier. Sizing a request against the former without regard
# for the latter is a guaranteed 413 on a rate-limited account.
# --------------------------------------------------------------------------


def test_resolve_tpm_limit_is_none_by_default():
    """Unset `LLM_TPM_LIMIT` -> no clamping, zero behavior change for
    every account that hasn't configured this."""
    import os
    os.environ.pop("LLM_TPM_LIMIT", None)
    assert llm_client.resolve_tpm_limit("groq") is None


def test_resolve_tpm_limit_reads_env_var(monkeypatch):
    monkeypatch.setenv("LLM_TPM_LIMIT", "8000")
    assert llm_client.resolve_tpm_limit("groq") == 8000


def test_resolve_tpm_limit_ignores_garbage_value(monkeypatch):
    monkeypatch.setenv("LLM_TPM_LIMIT", "not-a-number")
    assert llm_client.resolve_tpm_limit("groq") is None


def test_resolve_tpm_limit_ignores_non_positive_value(monkeypatch):
    monkeypatch.setenv("LLM_TPM_LIMIT", "0")
    assert llm_client.resolve_tpm_limit("groq") is None
    monkeypatch.setenv("LLM_TPM_LIMIT", "-500")
    assert llm_client.resolve_tpm_limit("groq") is None


def test_estimate_prompt_tokens_scales_with_length():
    short = llm_client.estimate_prompt_tokens("hello")
    long = llm_client.estimate_prompt_tokens("hello " * 1000)
    assert short > 0
    assert long > short * 100


def test_estimate_prompt_tokens_sums_multiple_strings():
    combined = llm_client.estimate_prompt_tokens("a" * 350, "b" * 350)
    single = llm_client.estimate_prompt_tokens("a" * 350)
    assert combined > single


def test_clamp_tokens_for_tpm_is_noop_when_limit_unset():
    assert llm_client.clamp_tokens_for_tpm(5000, 10000, None) == 10000


def test_clamp_tokens_for_tpm_shrinks_to_fit():
    # 8000 limit, ~4000 already spent on prompt, 200 margin reserved ->
    # available = 8000 - 4000 - 200 = 3800, below the desired 10000.
    result = llm_client.clamp_tokens_for_tpm(4000, 10000, 8000)
    assert result == 3800


def test_clamp_tokens_for_tpm_never_exceeds_desired():
    # Plenty of room, but must never ask for MORE than the caller wanted.
    result = llm_client.clamp_tokens_for_tpm(100, 500, 8000)
    assert result == 500


def test_clamp_tokens_for_tpm_returns_none_when_prompt_alone_does_not_fit():
    # Matches the user-reported case almost exactly: prompt tokens alone
    # already exceed the TPM ceiling.
    result = llm_client.clamp_tokens_for_tpm(46012, 5000, 8000)
    assert result is None


def test_clamp_tokens_for_tpm_returns_none_below_minimum_floor():
    # Technically some room remains (8000 - 7900 - 200 = -100), but even a
    # generous prompt estimate leaves less than the minimum useful output.
    result = llm_client.clamp_tokens_for_tpm(7900, 5000, 8000)
    assert result is None