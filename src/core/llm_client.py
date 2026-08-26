"""
llm_client.py
-------------
Environment-driven LLM configuration and client construction.

The pipeline reads all LLM settings from environment variables so the
provider, API key, model, and base URL can be changed without touching
application code.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional

from openai import OpenAI


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str
    model_name: str
    base_url: Optional[str] = None


def load_llm_config() -> LLMConfig:
    provider = os.environ.get("LLM_PROVIDER", "").strip()
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model_name = os.environ.get("LLM_MODEL_NAME", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip() or None

    missing = [
        name
        for name, value in (
            ("LLM_PROVIDER", provider),
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
        provider=provider.lower(),
        api_key=api_key,
        model_name=model_name,
        base_url=base_url,
    )


def create_llm_client(config: LLMConfig):
    if config.provider != "openai":
        raise EnvironmentError(
            f"Unsupported LLM_PROVIDER '{config.provider}'. "
            "This codebase currently supports LLM_PROVIDER=openai."
        )

    client_kwargs = {"api_key": config.api_key}
    if config.base_url:
        client_kwargs["base_url"] = config.base_url

    return OpenAI(**client_kwargs)
