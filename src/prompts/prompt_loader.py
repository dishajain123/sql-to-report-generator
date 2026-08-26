"""
prompts/prompt_loader.py
-------------------------
Centralized YAML prompt loader.

All LLM prompts (system prompts and user-prompt templates) live in
prompts/*.yaml, never as hardcoded Python string literals inside the
agent modules. Every agent that talks to the LLM goes through
`get_prompt_set()` in this module to load its prompt content, which
keeps prompt engineering fully separate from orchestration code and
lets prompts be edited/reviewed/versioned without touching Python.

Prompts are dialect-aware: each YAML file's "system" key is a mapping of
dialect -> prompt text (plus an optional "default" fallback), so the
same agent can select the correct Oracle PL/SQL or T-SQL system prompt
at call time without any hardcoded branching in the agent itself.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict

import yaml

_PROMPTS_DIR = Path(__file__).resolve().parent
_SUPPORTED_DIALECTS = {"oracle", "tsql"}


class PromptLoadError(RuntimeError):
    """Raised when a prompt YAML file is missing or malformed."""


@functools.lru_cache(maxsize=None)
def _load_yaml(filename: str) -> Dict[str, Any]:
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise PromptLoadError(f"Prompt file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise PromptLoadError(f"Prompt file {filename} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise PromptLoadError(f"Prompt file {filename} did not parse to a mapping.")
    return data


def get_prompt_set(filename: str, dialect: str = "oracle") -> Dict[str, str]:
    """Return {"system": <prompt text>, "user_template": <template text>}
    for the given prompt YAML file and SQL dialect.

    Args:
        filename: e.g. "logic_extraction.yaml" or "rule_synthesis.yaml".
        dialect: "oracle" or "tsql". Falls back to the file's "default"
            system prompt if no dialect-specific entry exists, so a new
            dialect can be added to the pipeline without breaking older
            prompt files that only define "default".
    """
    data = _load_yaml(filename)

    systems = data.get("system", {})
    if not isinstance(systems, dict):
        raise PromptLoadError(
            f"'system' key in {filename} must be a mapping of dialect -> prompt text."
        )

    dialect_key = (dialect or "oracle").strip().lower()
    if dialect_key not in _SUPPORTED_DIALECTS:
        raise PromptLoadError(
            f"Unsupported dialect '{dialect_key}' for {filename}. "
            "Only 'oracle' and 'tsql' are supported."
        )
    system_prompt = systems.get(dialect_key) or systems.get("default")
    if not system_prompt:
        raise PromptLoadError(
            f"No system prompt found for dialect '{dialect_key}' (and no 'default') "
            f"in {filename}."
        )

    user_template = data.get("user_template")
    if not user_template:
        raise PromptLoadError(f"'user_template' missing in {filename}.")

    return {"system": system_prompt, "user_template": user_template}


def render_user_prompt(template: str, **kwargs: Any) -> str:
    """Render a user-prompt template loaded from YAML using simple
    str.format() substitution - deliberately no external templating
    engine, to keep prompt rendering auditable and dependency-light.
    """
    return template.format(**kwargs)


def clear_cache() -> None:
    """Test/dev helper to force prompt YAML files to be re-read from
    disk on the next call (e.g. after editing a prompt file in place).
    """
    _load_yaml.cache_clear()
