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
from dataclasses import dataclass
import os
from types import SimpleNamespace
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from openai import OpenAI


# Amazon Nova Lite rejects Converse requests whose requested output limit is
# 10,000 or higher. Keep this constraint local to the Bedrock transport so
# other providers and the pipeline's existing configuration are unchanged.
BEDROCK_MAX_OUTPUT_TOKENS = 9999

try:  # pragma: no cover - optional dependency in developer environments
    import boto3  # type: ignore
    from botocore.config import Config as BotoConfig  # type: ignore
except Exception:  # pragma: no cover - boto3 is installed in production
    boto3 = None
    BotoConfig = None


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
    context_window = _configured_context_window()

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


def _configured_context_window() -> int:
    """Return the configured model context window, with a conservative default."""
    raw = os.environ.get("LLM_CONTEXT_WINDOW", "32768").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 32768
    return max(value, 4096)


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
        payload = self._build_payload(messages, temperature=temperature, max_tokens=max_tokens)
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
        request = self._signed_request(url=url, body=body)
        try:
            response = self._request_sender(request)
            raw = response.read()
            if hasattr(response, "close"):
                try:
                    response.close()
                except Exception:
                    pass
        except HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = str(exc)
            raise RuntimeError(f"Bedrock invocation failed: {exc.code} {detail or exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"Bedrock invocation failed: {exc.reason}") from exc

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

        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
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

    def _invoke_via_boto3(self, *, client, model_id: str, payload: dict):
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
                response = client.converse(**converse_kwargs)
                decoded = response if isinstance(response, dict) else {}
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
                    decoded = json.loads(raw.decode("utf-8"))
                else:
                    decoded = json.loads(str(raw or "{}"))
            else:  # pragma: no cover - defensive fallback for unusual stubs
                raise RuntimeError("Bedrock client does not expose converse() or invoke_model().")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Bedrock invocation failed: {exc}") from exc

        content = self._extract_content(decoded)
        usage = self._extract_usage(decoded)
        prompt_tokens = self._coerce_int(usage.get("inputTokens"))
        completion_tokens = self._coerce_int(usage.get("outputTokens"))
        total_tokens = self._coerce_int(usage.get("totalTokens"))
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        text = str(model or "").strip()
        if text.lower().startswith("bedrock/"):
            return text.split("/", 1)[1].strip()
        return text

    @staticmethod
    def _build_payload(messages, temperature: float = 0.0, max_tokens: int = 1024) -> dict:
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
        safe_max_tokens = min(max_tokens, BEDROCK_MAX_OUTPUT_TOKENS)
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
            },
        }
        if system_parts:
            payload["system"] = [{"text": "\n\n".join(system_parts)}]
        return payload

    def _signed_request(self, *, url: str, body: bytes) -> Request:
        parsed = url.split("://", 1)[-1]
        host, _, path = parsed.partition("/")
        amz_date = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
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
