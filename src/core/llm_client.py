"""
llm_client.py
-------------
Environment-driven LLM configuration and client construction.

The pipeline reads all LLM settings from environment variables so the
provider, API key, model, and base URL can be changed without touching
application code.
"""

from __future__ import annotations

import inspect
import datetime as _dt
import hashlib
import hmac
import json
import math
from dataclasses import dataclass
import os
from types import SimpleNamespace
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from openai import OpenAI


# Fallback ceiling used only when a model isn't in _BEDROCK_MODEL_OUTPUT_CAPS
# below. Kept for backward compatibility with any code still importing this
# name directly.
BEDROCK_MAX_OUTPUT_TOKENS = 9999

# Real per-model maximum COMPLETION tokens on Bedrock. These are hard ceilings
# imposed by the model itself, not configuration - requesting more than a
# model's true max silently gets clamped or rejected server-side, and (before
# the stopReason fix above) a clamp-induced truncation was invisible to the
# pipeline. Match on a substring of the normalized (post "bedrock/") model id
# so version-qualified ids (e.g. "amazon.nova-lite-v1:0") still resolve.
# Extend this map as new models are onboarded rather than trusting a single
# global constant to be correct for every model.
_BEDROCK_MODEL_OUTPUT_CAPS = {
    "amazon.nova-micro": 5000,
    "amazon.nova-lite": 5000,
    "amazon.nova-pro": 5000,
    "amazon.nova-2-lite": 65536,
    "amazon.nova-2-pro": 65536,
    "anthropic.claude-3-haiku": 4096,
    "anthropic.claude-3-5-sonnet": 8192,
    "anthropic.claude-3-7-sonnet": 8192,
}


# Real per-model maximum COMPLETION tokens on Groq. Same rationale as the
# Bedrock map above: sectioning/retry budget planning must be built against
# the ceiling the server will actually honour, or a large object silently
# under-triggers sectioning and truncates mid-JSON. Without an entry here a
# Groq model falls back to the generic 32768 default, which over-requests on
# the smaller Llama models.
_GROQ_MODEL_OUTPUT_CAPS = {
    "openai/gpt-oss-120b": 65536,
    "openai/gpt-oss-20b": 65536,
    "llama-3.3-70b-versatile": 32768,
    "llama-3.1-8b-instant": 8192,
    "qwen": 32768,
}


def _max_output_tokens_for_model(model_id: str) -> int:
    normalized = str(model_id or "").strip().lower()
    for prefix, cap in _BEDROCK_MODEL_OUTPUT_CAPS.items():
        if prefix in normalized:
            return cap
    return BEDROCK_MAX_OUTPUT_TOKENS


def _max_output_tokens_for_groq_model(model_id: str) -> Optional[int]:
    normalized = str(model_id or "").strip().lower()
    for prefix, cap in _GROQ_MODEL_OUTPUT_CAPS.items():
        if prefix in normalized:
            return cap
    return None


def resolve_model_output_ceiling(provider: str, model_name: str) -> Optional[int]:
    """Return the real, server-enforced maximum completion tokens for the
    configured provider/model, or `None` when no such ceiling is known.

    This is the single source of truth `_BedrockChatCompletions.create`
    already clamps every request against (`safe_max_tokens = min(max_tokens,
    _max_output_tokens_for_model(model_id))`). Extraction/synthesis budget
    planning (`RuleSynthesizerAgent`, `LogicExtractionAgent`) must be built
    against this same ceiling - not the generic `LLM_HARD_MAX_OUTPUT_TOKENS`
    default (32768) - or their single-pass/sectioning decisions silently
    request more completion tokens than the model will ever return (e.g.
    Amazon Nova Lite's real cap is 5000), guaranteeing truncated JSON no
    matter how large a budget the caller asks for.
    """
    normalized_provider = str(provider or "").strip().lower()
    if normalized_provider == "bedrock":
        return _max_output_tokens_for_model(model_name)
    if normalized_provider == "groq":
        return _max_output_tokens_for_groq_model(model_name)
    return None


def estimate_prompt_tokens(*texts: str) -> int:
    """Rough, provider-agnostic token estimate for a set of prompt strings.

    No tokenizer dependency: assumes ~3.5 characters per token, which is a
    deliberate slight OVERestimate for English/code text (real BPE
    tokenizers average closer to 4 chars/token) so this errs toward
    reserving too much room rather than too little. Used only for
    pre-flight token-per-minute (TPM) budgeting, i.e. deciding whether a
    request is even worth sending before the provider tells us with a 413 -
    the response's own `usage` field is always the real source of truth for
    what a call actually cost.
    """
    total_chars = sum(len(t or "") for t in texts)
    return math.ceil(total_chars / 3.5)


def resolve_tpm_limit(provider: Optional[str] = None) -> Optional[int]:
    """The account's real, plan-specific combined tokens-per-minute ceiling,
    if the caller has told us what it is.

    This cannot be known in advance from the model name alone - it depends
    on the account's plan (free vs Developer/Enterprise) and is unrelated to
    a model's MAX COMPLETION TOKENS figure. For example Groq's free plan
    caps `openai/gpt-oss-120b` at 8,000 TOTAL tokens (prompt + requested
    completion) per minute, even though the model itself can emit up to
    65,536 completion tokens per call on a higher tier - two unrelated
    numbers that are easy to conflate (see `_GROQ_MODEL_OUTPUT_CAPS` above,
    which is the LATTER, not this).

    Set `LLM_TPM_LIMIT` in the environment to the value shown on your
    provider's rate-limit/quota page (for Groq: the TPM column on
    https://console.groq.com/settings/limits) to have `RuleSynthesizerAgent`
    pre-emptively size every request under it instead of discovering the
    limit via a 413. Left unset (the default), this check is disabled
    entirely and behavior is unchanged from before this existed.
    """
    raw = os.environ.get("LLM_TPM_LIMIT", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


# Tokens always held back from a TPM budget so a request is never sized to
# the exact edge of the limit - both this module's char-based estimate and
# the provider's own tokenizer differ slightly from the actual count, and
# some providers reject a request whose RESERVED total (prompt +
# `max_tokens`) exceeds the limit even when the eventual real usage
# would not have.
_TPM_SAFETY_MARGIN = 200

# Below this many completion tokens, a call isn't worth attempting - there
# is no schema this pipeline emits that fits usefully in less room.
_TPM_MIN_OUTPUT_FLOOR = 200


def clamp_tokens_for_tpm(
    prompt_tokens: int, desired_max_tokens: int, tpm_limit: Optional[int]
) -> Optional[int]:
    """Return the largest `max_tokens` that keeps `prompt_tokens +
    max_tokens` under `tpm_limit`, or `None` if even the minimum useful
    completion budget does not fit and the call should not be sent at all.

    Never returns more than `desired_max_tokens` - this only ever shrinks a
    request relative to what the caller already planned to ask for, never
    grows one. When `tpm_limit` is `None` (the default, unset), returns
    `desired_max_tokens` unchanged - this function is a no-op until the
    person configures `LLM_TPM_LIMIT`.
    """
    if tpm_limit is None:
        return desired_max_tokens
    available = tpm_limit - prompt_tokens - _TPM_SAFETY_MARGIN
    if available < _TPM_MIN_OUTPUT_FLOOR:
        return None
    return max(_TPM_MIN_OUTPUT_FLOOR, min(desired_max_tokens, available))


# Nova models: sending temperature=0 alone does NOT guarantee deterministic,
# run-to-run-stable output on Bedrock - topP and topK keep their (non-greedy)
# model defaults unless explicitly pinned. The synthesis prompt spends ~20
# lines demanding run-to-run stability, so this must be set on every Nova
# request, not left to the model default.
_NOVA_DETERMINISTIC_TOP_P = 1.0
_NOVA_DETERMINISTIC_TOP_K = 1

try:  # pragma: no cover - optional dependency in developer environments
    import boto3  # type: ignore
    from botocore.config import Config as BotoConfig  # type: ignore
    from botocore.exceptions import ClientError as BotoClientError  # type: ignore
except Exception:  # pragma: no cover - boto3 is installed in production
    boto3 = None
    BotoConfig = None
    BotoClientError = None


class LLMTransientError(RuntimeError):
    """A genuinely transient LLM call failure - rate limit, timeout,
    connection error, or a 5xx server error. Callers (specifically
    `call_with_retry` below) may retry these. Every other failure (auth,
    malformed request, invalid/unparsable response body) is a permanent
    `RuntimeError` and must never be retried - retrying a bad request just
    burns the same bounded attempt budget for a result that will never
    change.
    """


# Bounded, generic retry helper for the one LLM call site with no built-in
# retry of its own: `_BedrockRuntimeTransport`'s raw HTTP fallback (used
# when boto3 isn't installed). The boto3 path already gets botocore's own
# "standard" retry mode, and the openai-SDK-backed providers (openai/groq/
# ollama) already retry transient errors by default via the `openai`
# package itself - wrapping those again here would risk compounding
# backoff on top of backoff already applied by the underlying client.
def call_with_retry(fn, *, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 8.0):
    """Call `fn()`, retrying with bounded exponential backoff (+ jitter)
    only when it raises `LLMTransientError`. Any other exception - a
    permanent failure, or a transient one already exhausted - propagates
    immediately on the attempt that raised it.
    """
    import random
    import time as _time

    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except LLMTransientError:
            if attempt >= max_attempts:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            _time.sleep(delay * (0.5 + random.random()))


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str
    model_name: str
    base_url: Optional[str] = None
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    aws_region: str = ""
    # Input context limit used by orchestration decisions. Providers/models
    # can override this through LLM_CONTEXT_WINDOW without changing code.
    context_window: int = 32768


def load_llm_config() -> LLMConfig:
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model_name = os.environ.get("LLM_MODEL_NAME", "").strip()
    groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
    groq_model_name = os.environ.get("GROQ_MODEL_NAME", "").strip()
    groq_base_url = os.environ.get("GROQ_BASE_URL", "").strip() or None
    ollama_model_name = os.environ.get("OLLAMA_MODEL_NAME", "").strip()
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "").strip() or None
    legacy_model_name = os.environ.get("GPT_MODEL", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip() or None
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
    aws_session_token = os.environ.get("AWS_SESSION_TOKEN", "").strip()
    aws_region = os.environ.get("AWS_DEFAULT_REGION", "").strip() or os.environ.get("AWS_REGION", "").strip()

    if not model_name and legacy_model_name and provider in {"", "bedrock"}:
        model_name = legacy_model_name

    if model_name.lower().startswith("bedrock/"):
        if not provider:
            provider = "bedrock"
        if provider == "bedrock":
            model_name = model_name.split("/", 1)[1].strip()
    elif not provider and aws_access_key_id and aws_secret_access_key and aws_region:
        provider = "bedrock"
    elif not provider:
        provider = "openai"

    provider = provider.lower()
    # Computed after model_name is fully resolved (bedrock/ prefix stripped)
    # so the per-model default in _configured_context_window can actually
    # match on the real model id.
    context_window = _configured_context_window(model_name)

    if provider == "groq":
        # Groq exposes an OpenAI-compatible chat-completions API. Keep its
        # credentials/model namespace separate so switching providers cannot
        # accidentally reuse an AWS model or key from the Bedrock setup.
        groq_key = groq_api_key or api_key
        groq_model = groq_model_name or model_name
        missing = [
            name
            for name, value in (
                ("GROQ_API_KEY / LLM_API_KEY", groq_key),
                ("GROQ_MODEL_NAME / LLM_MODEL_NAME", groq_model),
            )
            if not value
        ]
        if missing:
            raise EnvironmentError(
                "Missing required Groq environment variable(s): "
                + ", ".join(missing)
                + ". Set them in your .env file before running the app."
            )
        return LLMConfig(
            provider=provider,
            api_key=groq_key,
            model_name=groq_model,
            base_url=groq_base_url or base_url or "https://api.groq.com/openai/v1",
            context_window=context_window,
        )

    if provider == "ollama":
        # Ollama is a local server and deliberately needs no API key. The
        # OpenAI-compatible client still receives a harmless placeholder.
        return LLMConfig(
            provider=provider,
            api_key="ollama",
            model_name=ollama_model_name or model_name or "llama3.1:8b",
            base_url=ollama_base_url or "http://localhost:11434/v1",
            context_window=context_window,
        )

    if provider == "openai":
        missing = [
            name
            for name, value in (
                ("LLM_API_KEY", api_key),
                ("LLM_MODEL_NAME", model_name),
            )
            if not value
        ]
        if missing:
            raise EnvironmentError(
                "Missing required LLM environment variable(s): "
                + ", ".join(missing)
                + ". Set them in your .env file before running the app."
            )
        return LLMConfig(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            context_window=context_window,
        )

    if provider == "bedrock":
        missing = [
            name
            for name, value in (
                ("GPT_MODEL / LLM_MODEL_NAME", model_name),
                ("AWS_DEFAULT_REGION / AWS_REGION", aws_region),
            )
            if not value
        ]
        if missing:
            raise EnvironmentError(
                "Missing required Bedrock environment variable(s): "
                + ", ".join(missing)
                + ". Set them in your .env file before running the app."
            )
        return LLMConfig(
            provider=provider,
            api_key="",
            model_name=model_name,
            base_url=base_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            aws_region=aws_region,
            context_window=context_window,
        )

    raise EnvironmentError(
        f"Unsupported LLM_PROVIDER '{provider}'. "
        "This codebase currently supports LLM_PROVIDER=openai, groq, ollama, or bedrock."
    )


# Real context-window ceilings for Bedrock models, used as the DEFAULT when
# LLM_CONTEXT_WINDOW is not explicitly set. The previous flat 32768 default
# starved nova-lite (300K context) down to a ~30K effective budget after the
# prompt-schema reserve, which - combined with the pessimistic token
# estimator above - routed most objects in a 91-procedure corpus through the
# chunked extraction path even though they would fit in a single pass.
_BEDROCK_MODEL_CONTEXT_WINDOWS = {
    "amazon.nova-micro": 128000,
    "amazon.nova-lite": 300000,
    "amazon.nova-pro": 300000,
    "amazon.nova-2-lite": 1000000,
    "amazon.nova-2-pro": 1000000,
    "anthropic.claude-3-haiku": 200000,
    "anthropic.claude-3-5-sonnet": 200000,
    "anthropic.claude-3-7-sonnet": 200000,
}


def _configured_context_window(model_name: str = "") -> int:
    """Return the configured model context window.

    `LLM_CONTEXT_WINDOW` always wins when explicitly set (an operator
    override should never be silently ignored). Otherwise the default is
    looked up per-model from `_BEDROCK_MODEL_CONTEXT_WINDOWS` rather than a
    single flat constant, since a Bedrock model's real context window varies
    by an order of magnitude or more across the catalog.
    """
    raw = os.environ.get("LLM_CONTEXT_WINDOW", "").strip()
    if raw:
        try:
            return max(int(raw), 4096)
        except ValueError:
            pass
    normalized = str(model_name or "").strip().lower()
    for prefix, window in _BEDROCK_MODEL_CONTEXT_WINDOWS.items():
        if prefix in normalized:
            return window
    return 32768


def create_llm_client(config: LLMConfig):
    if config.provider in {"openai", "groq", "ollama"}:
        client_kwargs = {"api_key": config.api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url
        return OpenAI(**client_kwargs)

    if config.provider == "bedrock":
        return _BedrockOpenAICompatibleClient(
            access_key_id=config.aws_access_key_id,
            secret_access_key=config.aws_secret_access_key,
            region=config.aws_region,
            session_token=config.aws_session_token or None,
        )

    raise EnvironmentError(
        f"Unsupported LLM_PROVIDER '{config.provider}'. "
        "This codebase currently supports LLM_PROVIDER=openai, groq, ollama, or bedrock."
    )


def supports_chat_completion_seed(client) -> bool:
    try:
        return "seed" in inspect.signature(client.chat.completions.create).parameters
    except (AttributeError, TypeError, ValueError):
        return False


class _BedrockOpenAICompatibleClient:
    def __init__(
        self,
        *,
        access_key_id: str,
        secret_access_key: str,
        region: str,
        session_token: Optional[str] = None,
    ) -> None:
        self.chat = _BedrockChatNamespace(
            _BedrockChatCompletions(
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
                region=region,
                session_token=session_token,
            )
        )


class _BedrockChatNamespace:
    def __init__(self, completions: "_BedrockChatCompletions") -> None:
        self.completions = completions


class _BedrockChatCompletions:
    def __init__(
        self,
        *,
        access_key_id: str,
        secret_access_key: str,
        region: str,
        session_token: Optional[str] = None,
    ) -> None:
        self._transport = _BedrockRuntimeTransport(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            region=region,
            session_token=session_token,
        )

    def create(self, *, model: str, messages, temperature: float = 0.0, max_tokens: int = 1024):
        return self._transport.invoke(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )


class _BedrockRuntimeTransport:
    def __init__(
        self,
        *,
        access_key_id: str,
        secret_access_key: str,
        region: str,
        session_token: Optional[str] = None,
    ) -> None:
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token
        self.region = region
        self.service = "bedrock"
        self._request_sender = urlopen
        self._boto3_client = None

    def invoke(self, *, model: str, messages, temperature: float = 0.0, max_tokens: int = 1024):
        model_id = self._normalize_model_name(model)
        payload = self._build_payload(
            messages, temperature=temperature, max_tokens=max_tokens, model_id=model_id
        )
        boto3_client = self._build_boto3_client()
        if boto3_client is not None:
            return self._invoke_via_boto3(client=boto3_client, model_id=model_id, payload=payload)

        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        # Bedrock model IDs can contain reserved URL characters such as `:`.
        # The runtime endpoint expects the path segment to be percent-encoded,
        # and SigV4 must sign the exact same encoded path or the request will
        # fail with a signature mismatch.
        encoded_model_id = quote(model_id, safe="-_.~")
        url = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{encoded_model_id}/converse"

        def _send_once() -> bytes:
            # A fresh signed request is built on every attempt (not just
            # the first) - SigV4 signs its own embedded timestamp, and
            # rebuilding it keeps every retry attempt's signature valid
            # even if backoff delay pushes it into a new second.
            request = self._signed_request(url=url, body=body)
            try:
                response = self._request_sender(request)
                raw = response.read()
                if hasattr(response, "close"):
                    try:
                        response.close()
                    except Exception:
                        pass
                return raw
            except HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", errors="ignore")
                except Exception:
                    detail = str(exc)
                message = f"Bedrock invocation failed: {exc.code} {detail or exc.reason}"
                # Rate-limited (429) and server-side (5xx) responses are
                # genuinely transient - worth a bounded retry. Everything
                # else (4xx like bad request/auth/not-found) is a
                # permanent failure that retrying can never fix.
                if exc.code == 429 or exc.code >= 500:
                    raise LLMTransientError(message) from exc
                raise RuntimeError(message) from exc
            except URLError as exc:
                # Network-level failure (DNS, connection refused, timeout)
                # below the HTTP layer - always treated as transient.
                raise LLMTransientError(f"Bedrock invocation failed: {exc.reason}") from exc

        raw = call_with_retry(_send_once)

        try:
            decoded = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("Bedrock returned invalid JSON.") from exc

        content = self._extract_content(decoded)
        usage = decoded.get("usage") if isinstance(decoded, dict) else {}
        prompt_tokens = self._coerce_int(
            (usage or {}).get("inputTokens") if isinstance(usage, dict) else None
        )
        completion_tokens = self._coerce_int(
            (usage or {}).get("outputTokens") if isinstance(usage, dict) else None
        )
        total_tokens = self._coerce_int(
            (usage or {}).get("totalTokens") if isinstance(usage, dict) else None
        )
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens

        finish_reason = self._map_stop_reason(decoded.get("stopReason") if isinstance(decoded, dict) else None)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                    finish_reason=finish_reason,
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    def _build_boto3_client(self):
        if boto3 is None:
            return None
        if self._boto3_client is not None:
            return self._boto3_client

        client_kwargs: Dict[str, Any] = {"region_name": self.region}
        if BotoConfig is not None:
            client_kwargs["config"] = BotoConfig(retries={"max_attempts": 3, "mode": "standard"})
        if self.access_key_id and self.secret_access_key:
            client_kwargs["aws_access_key_id"] = self.access_key_id
            client_kwargs["aws_secret_access_key"] = self.secret_access_key
            if self.session_token:
                client_kwargs["aws_session_token"] = self.session_token
        self._boto3_client = boto3.client("bedrock-runtime", **client_kwargs)
        return self._boto3_client

    # AWS error codes that mean "the service is temporarily unable to keep
    # up / unavailable", not "this request is wrong" - worth a bounded
    # retry. botocore's own "standard" retry mode (configured in
    # `_build_boto3_client`) already retries a subset of these internally
    # before this method ever sees an exception; this is a second,
    # explicit layer specifically so codes botocore doesn't already know
    # about (Bedrock-specific throttling/timeout codes) still get bounded
    # retry rather than propagating as a permanent failure on the first hit.
    _RETRYABLE_BOTO_ERROR_CODES = frozenset(
        {
            "ThrottlingException",
            "TooManyRequestsException",
            "ServiceUnavailableException",
            "ServiceUnavailable",
            "ModelTimeoutException",
            "InternalServerException",
            "RequestTimeout",
            "RequestTimeoutException",
        }
    )

    def _invoke_via_boto3(self, *, client, model_id: str, payload: dict):
        def _call_once() -> dict:
            try:
                if hasattr(client, "converse"):
                    converse_kwargs = {
                        "modelId": model_id,
                        "messages": payload.get("messages") or [],
                        "inferenceConfig": payload.get("inferenceConfig") or {},
                    }
                    system = payload.get("system") or []
                    if system:
                        converse_kwargs["system"] = system
                    additional_fields = payload.get("additionalModelRequestFields")
                    if additional_fields:
                        converse_kwargs["additionalModelRequestFields"] = additional_fields
                    response = client.converse(**converse_kwargs)
                    return response if isinstance(response, dict) else {}
                elif hasattr(client, "invoke_model"):
                    response = client.invoke_model(
                        modelId=model_id,
                        contentType="application/json",
                        accept="application/json",
                        body=json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                    )
                    body = response.get("body") if isinstance(response, dict) else getattr(response, "body", None)
                    raw = body.read() if hasattr(body, "read") else body
                    if isinstance(raw, bytes):
                        return json.loads(raw.decode("utf-8"))
                    return json.loads(str(raw or "{}"))
                else:  # pragma: no cover - defensive fallback for unusual stubs
                    raise RuntimeError("Bedrock client does not expose converse() or invoke_model().")
            except RuntimeError:
                raise
            except Exception as exc:  # noqa: BLE001
                error_code = None
                if BotoClientError is not None and isinstance(exc, BotoClientError):
                    error_code = (exc.response or {}).get("Error", {}).get("Code")
                if error_code in self._RETRYABLE_BOTO_ERROR_CODES:
                    raise LLMTransientError(f"Bedrock invocation failed: {exc}") from exc
                raise RuntimeError(f"Bedrock invocation failed: {exc}") from exc

        decoded = call_with_retry(_call_once)

        content = self._extract_content(decoded)
        usage = self._extract_usage(decoded)
        prompt_tokens = self._coerce_int(usage.get("inputTokens"))
        completion_tokens = self._coerce_int(usage.get("outputTokens"))
        total_tokens = self._coerce_int(usage.get("totalTokens"))
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens
        finish_reason = self._map_stop_reason(decoded.get("stopReason") if isinstance(decoded, dict) else None)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                    finish_reason=finish_reason,
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    @staticmethod
    def _map_stop_reason(stop_reason: Optional[str]) -> str:
        """Map Bedrock Converse's `stopReason` to the OpenAI-style
        `finish_reason` the pipeline's truncation-detection code already
        reads (`logic_extractor.py`, `rule_synthesizer.py`). Without this,
        `finish_reason` was never set on the Bedrock response object, so
        `truncated = finish_reason == "length"` was always False - an
        existing safety net that silently never fired.
        """
        normalized = str(stop_reason or "").strip().lower()
        return {
            "max_tokens": "length",
            "end_turn": "stop",
            "stop_sequence": "stop",
            "tool_use": "tool_calls",
            "content_filtered": "content_filter",
        }.get(normalized, normalized or "stop")

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        text = str(model or "").strip()
        if text.lower().startswith("bedrock/"):
            return text.split("/", 1)[1].strip()
        return text

    @staticmethod
    def _build_payload(
        messages, temperature: float = 0.0, max_tokens: int = 1024, model_id: str = ""
    ) -> dict:
        system_parts = []
        user_parts = []
        for message in messages or []:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "").strip().lower()
            content = message.get("content")
            text = content if isinstance(content, str) else str(content or "")
            if role == "system":
                if text:
                    system_parts.append(text)
            else:
                if text:
                    user_parts.append(text)
        safe_max_tokens = min(max_tokens, _max_output_tokens_for_model(model_id))
        payload: dict[str, Any] = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": "\n\n".join(part for part in user_parts if part)}],
                }
            ],
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": safe_max_tokens,
                # Pin nucleus sampling so temperature=0 actually delivers
                # deterministic, diffable output (see _NOVA_DETERMINISTIC_TOP_P
                # above) instead of relying on undocumented model defaults.
                "topP": _NOVA_DETERMINISTIC_TOP_P,
            },
        }
        if "nova" in str(model_id or "").lower():
            # topK isn't part of Converse's common inferenceConfig - Nova
            # exposes it only via additionalModelRequestFields.
            payload["additionalModelRequestFields"] = {
                "inferenceConfig": {"topK": _NOVA_DETERMINISTIC_TOP_K}
            }
        if system_parts:
            payload["system"] = [{"text": "\n\n".join(system_parts)}]
        return payload

    def _signed_request(self, *, url: str, body: bytes) -> Request:
        parsed = url.split("://", 1)[-1]
        host, _, path = parsed.partition("/")
        amz_date = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        date_stamp = amz_date[:8]
        payload_hash = hashlib.sha256(body).hexdigest()
        canonical_uri = "/" + path
        headers = {
            "content-type": "application/json",
            "host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if self.session_token:
            headers["x-amz-security-token"] = self.session_token
        canonical_headers = "".join(f"{key}:{headers[key]}\n" for key in sorted(headers))
        signed_headers = ";".join(sorted(headers))
        canonical_request = "\n".join(
            [
                "POST",
                canonical_uri,
                "",
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signing_key = self._get_signature_key(
            self.secret_access_key,
            date_stamp,
            self.region,
            self.service,
        )
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        headers["Authorization"] = (
            "AWS4-HMAC-SHA256 "
            f"Credential={self.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return Request(url, data=body, headers=headers, method="POST")

    @staticmethod
    def _get_signature_key(secret_key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        def _sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        k_date = _sign(("AWS4" + secret_key).encode("utf-8"), date_stamp)
        k_region = _sign(k_date, region_name)
        k_service = _sign(k_region, service_name)
        return _sign(k_service, "aws4_request")

    @staticmethod
    def _extract_content(decoded: dict) -> str:
        try:
            output = decoded.get("output", {})
            message = output.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                texts = []
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text")
                        if text:
                            texts.append(str(text))
                if texts:
                    return "".join(texts)
        except Exception:
            pass
        return ""

    @staticmethod
    def _extract_usage(decoded: dict) -> dict:
        if not isinstance(decoded, dict):
            return {}
        usage = decoded.get("usage")
        if isinstance(usage, dict):
            return usage
        metrics = decoded.get("metrics")
        if isinstance(metrics, dict):
            return metrics
        return {}

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        try:
            if value in (None, ""):
                return None
            return int(value)
        except (TypeError, ValueError):
            return None