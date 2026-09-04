"""
agents/logic_extractor.py
--------------------------
Logic Extraction Agent.

For each code chunk (plus the pattern/domain context retrieved by the
Pattern Retrieval Agent), this agent performs a *technical* pass that
produces a structured, intermediate JSON extraction of:

    - conditions / branches (IF / CASE / WHEN)
    - decision chains: multi-branch IF/ELSIF/ELSE (or equivalent CASE) ladders that test
      the same subject and assign one or more fields per branch, captured as one linked
      structure (subject + ordered branches + per-branch field assignments) rather than as
      several disconnected "conditions" entries - this is what lets the downstream Rule
      Synthesizer represent a classification/threshold ladder as one rule per output field
      with correctly-ordered decision_logic_rows, instead of having to reverse-engineer the
      ladder's structure from prose and risk misattributing an outcome to the wrong branch.
    - loops / cursors and what they iterate over
    - tables read (with columns + filter conditions + confidence)
    - tables written (with operation type + trigger condition + confidence)
    - calculations / formulas
    - exception handling behavior
    - anything the model could not confidently determine (ambiguities)

This is still a *technical* extraction (it may still use SQL
terminology) - translating it into pure business language is the job
of the downstream Rule Synthesizer Agent. Keeping these two concerns
separate keeps each prompt focused and each agent independently
testable.

All prompt content is loaded from prompts/logic_extraction.yaml via the
centralized `prompts.prompt_loader` - nothing here is a hardcoded prompt
string. The prompt is selected per SQL dialect (Oracle vs T-SQL).

Every LLM response is passed through the output guardrails in
`guardrails.py`: the JSON shape is validated/repaired, and every
table/column name the model claims is cross-checked against the actual
source code chunk (anti-hallucination grounding) before being trusted.

Calls an OpenAI-compatible chat completion API directly - there is no
orchestration framework in this module; a "chain" here is just one
Python method calling `client.chat.completions.create(...)`.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List
from typing import Optional

from src.ingestion.guardrails import ground_extraction_against_source, validate_extraction_shape
from src.core.llm_client import supports_chat_completion_seed
from src.core.pipeline_utils import PIPELINE_VERSION
from src.core.llm_response_cache import PersistentLLMResponseCache
from src.prompts.prompt_loader import get_prompt_set, render_user_prompt
from src.telemetry.tracker import LLMTelemetryTracker
from src.validation.coverage_check import find_decision_points

_EMPTY_EXTRACTION: Dict[str, Any] = {
    "conditions": [],
    "decision_chains": [],
    "loops": [],
    "tables_read": [],
    "tables_written": [],
    "calculations": [],
    "exception_handling": [],
    "ambiguities": [],
}


@dataclass
class ChunkExtraction:
    chunk_id: str
    chunk_kind: str
    chunk_context: List[str] = field(default_factory=list)
    embedded_sql: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=lambda: dict(_EMPTY_EXTRACTION))
    raw_response: str = ""
    parse_error: str = ""
    guardrail_warnings: List[str] = field(default_factory=list)
    truncated: bool = False


_BASE_EXTRACTION_TOKENS = int(os.environ.get("BASE_EXTRACTION_TOKENS", "6000"))
_PER_DECISION_POINT_EXTRACTION_TOKENS = int(
    os.environ.get("PER_DECISION_POINT_EXTRACTION_TOKENS", "128")
)
_HARD_MAX_OUTPUT_TOKENS = int(os.environ.get("LLM_HARD_MAX_OUTPUT_TOKENS", "32768"))


class LogicExtractionAgent:
    """Runs the technical extraction call over a single code chunk using
    the configured chat completion client directly.
    """

    def __init__(
        self,
        client,
        model: str,
        temperature: float = 0.1,
        seed: Optional[int] = 0,
        provider: str = "openai",
        telemetry_tracker: Optional[LLMTelemetryTracker] = None,
        response_cache: Optional[PersistentLLMResponseCache] = None,
        max_tokens: int = 6000,
    ):
        """
        Args:
            client: an initialized OpenAI-compatible chat client instance.
            model: the model name to call (configurable per pipeline run).
            temperature: sampling temperature (kept low for extraction tasks).
            max_tokens: explicit output-token cap passed on every completion
                call - see the matching note in
                `RuleSynthesizerAgent.__init__` (src/synthesis/rule_synthesizer.py):
                the Bedrock-backed client defaults to 1024 output tokens when
                this isn't passed explicitly, silently truncating extraction
                JSON for any code chunk whose extracted facts exceed that.
        """
        self.client = client
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.provider = provider
        self.telemetry_tracker = telemetry_tracker
        self.response_cache = response_cache
        self.max_tokens = max_tokens

    def _output_token_budget(self, code_chunk: str, requested: Optional[int] = None) -> int:
        points = len(find_decision_points(code_chunk or ""))
        base = max(int(requested or self.max_tokens), _BASE_EXTRACTION_TOKENS)
        return min(_HARD_MAX_OUTPUT_TOKENS, base + points * _PER_DECISION_POINT_EXTRACTION_TOKENS)

    def extract(
        self,
        chunk_id: str,
        chunk_kind: str,
        code_chunk: str,
        rag_context: str,
        object_type: str,
        object_name: str,
        chunk_context: List[str] | None = None,
        embedded_sql: List[str] | None = None,
        dialect: str = "oracle",
        model: str | None = None,
        telemetry_tracker: Optional[LLMTelemetryTracker] = None,
    ) -> ChunkExtraction:
        """`model`, if given, overrides the agent's configured model for
        just this call - lets callers pick a different model per run
        without re-constructing the agent.
        """
        prompt_set = get_prompt_set("logic_extraction.yaml", dialect=dialect)
        context_path = chunk_context or []
        embedded_sql_context = embedded_sql or []
        user_prompt = render_user_prompt(
            prompt_set["user_template"],
            object_type=object_type,
            object_name=object_name,
            dialect=dialect,
            chunk_kind=chunk_kind,
            chunk_context=" > ".join(context_path) if context_path else "None",
            embedded_sql_context="\n".join(f"- {stmt}" for stmt in embedded_sql_context)
            if embedded_sql_context
            else "None",
            rag_context=rag_context,
            code_chunk=code_chunk,
        )
        effective_seed = self.seed if self.seed is not None and supports_chat_completion_seed(self.client) else None
        effective_max_tokens = self._output_token_budget(code_chunk)
        cache_request = self._build_cache_request(
            stage="extraction",
            dialect=dialect,
            provider=self.provider,
            model_name=model or self.model,
            system_prompt=prompt_set["system"],
            user_prompt=user_prompt,
            temperature=self.temperature,
            seed=effective_seed,
            max_tokens=effective_max_tokens,
        )
        tracker = telemetry_tracker or self.telemetry_tracker
        if self.response_cache is not None:
            cache_lookup = self.response_cache.lookup(cache_request)
            if cache_lookup.hit:
                raw_response = cache_lookup.response_text or ""
                data, error = self._parse_json(raw_response)
                if not error:
                    if tracker is not None:
                        tracker.record_cache_lookup(stage="extraction", hit=True)
                    guardrail_warnings: List[str] = []
                    data, shape_warnings = validate_extraction_shape(data)
                    guardrail_warnings.extend(shape_warnings)
                    guardrail_warnings.extend(ground_extraction_against_source(data, code_chunk))
                    return ChunkExtraction(
                        chunk_id=chunk_id,
                        chunk_kind=chunk_kind,
                        chunk_context=context_path,
                        embedded_sql=embedded_sql_context,
                        data=data,
                        raw_response=raw_response,
                        parse_error=error,
                        guardrail_warnings=guardrail_warnings,
                    )
                self.response_cache.delete(cache_request)
                if tracker is not None and cache_lookup.status != "disabled":
                    tracker.record_cache_lookup(stage="extraction", hit=False)
            elif cache_lookup.status != "disabled" and tracker is not None:
                tracker.record_cache_lookup(stage="extraction", hit=False)

        completion_kwargs = {
            "model": model or self.model,
            "temperature": self.temperature,
            "max_tokens": effective_max_tokens,
            "messages": [
                {"role": "system", "content": prompt_set["system"]},
                {"role": "user", "content": user_prompt},
            ],
        }
        if effective_seed is not None:
            completion_kwargs["seed"] = effective_seed
        response = None
        call_success = False
        call_error: Exception | None = None
        start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(**completion_kwargs)
            call_success = True
        except Exception as exc:  # noqa: BLE001
            call_error = exc
            raise
        finally:
            if tracker is not None:
                try:
                    tracker.record_call(
                        stage="extraction",
                        provider=self.provider,
                        model_name=model or self.model,
                        response=response,
                        latency_seconds=time.perf_counter() - start,
                        success=call_success,
                        error=call_error,
                    )
                except Exception:
                    pass
        raw_response = response.choices[0].message.content or ""
        finish_reason = str(getattr(response.choices[0], "finish_reason", "") or "").lower()
        truncated = finish_reason == "length"

        data, error = self._parse_json(raw_response)
        if truncated and error:
            recovered = self._recover_partial_json(raw_response)
            if recovered is not None:
                data, error = recovered, ""
            elif effective_max_tokens < _HARD_MAX_OUTPUT_TOKENS:
                retry_kwargs = dict(completion_kwargs)
                retry_kwargs["max_tokens"] = _HARD_MAX_OUTPUT_TOKENS
                retry_response = self.client.chat.completions.create(**retry_kwargs)
                retry_reason = str(
                    getattr(retry_response.choices[0], "finish_reason", "") or ""
                ).lower()
                truncated = retry_reason == "length"
                raw_response = retry_response.choices[0].message.content or ""
                data, error = self._parse_json(raw_response)
                if truncated and error:
                    recovered = self._recover_partial_json(raw_response)
                    if recovered is not None:
                        data, error = recovered, ""

        guardrail_warnings: List[str] = []
        data, shape_warnings = validate_extraction_shape(data)
        guardrail_warnings.extend(shape_warnings)
        guardrail_warnings.extend(ground_extraction_against_source(data, code_chunk))
        if truncated:
            guardrail_warnings.append(
                "Technical extraction response reached the output limit; recovered facts may be incomplete."
            )
        if self.response_cache is not None and not error:
            self.response_cache.store(cache_request, raw_response)

        return ChunkExtraction(
            chunk_id=chunk_id,
            chunk_kind=chunk_kind,
            chunk_context=context_path,
            embedded_sql=embedded_sql_context,
            data=data,
            raw_response=raw_response,
            parse_error=error,
            guardrail_warnings=guardrail_warnings,
            truncated=truncated,
        )

    @staticmethod
    def _recover_partial_json(raw_response: str) -> Optional[Dict[str, Any]]:
        """Recover complete top-level array items from a length-truncated object."""
        for key in _EMPTY_EXTRACTION:
            marker = re.search(r'"' + re.escape(key) + r'"\s*:\s*\[', raw_response)
            if not marker:
                continue
            cursor = marker.end()
            items: List[Any] = []
            decoder = json.JSONDecoder()
            while cursor < len(raw_response):
                while cursor < len(raw_response) and raw_response[cursor].isspace():
                    cursor += 1
                if cursor >= len(raw_response) or raw_response[cursor] == "]":
                    break
                try:
                    item, end = decoder.raw_decode(raw_response, cursor)
                except json.JSONDecodeError:
                    break
                items.append(item)
                cursor = end
                while cursor < len(raw_response) and raw_response[cursor].isspace():
                    cursor += 1
                if cursor < len(raw_response) and raw_response[cursor] == ",":
                    cursor += 1
                    continue
                break
            if items:
                recovered = dict(_EMPTY_EXTRACTION)
                recovered[key] = items
                return recovered
        return None

    @staticmethod
    def _build_cache_request(
        *,
        stage: str,
        dialect: str,
        provider: str,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        seed: Optional[int],
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {
            "pipeline_version": PIPELINE_VERSION,
            "stage": stage,
            "provider": provider,
            "model_name": model_name,
            "dialect": dialect,
            "temperature": temperature,
            "seed": seed,
            # Included so any change to the output-token ceiling correctly
            # invalidates previously cached responses (a response cached
            # under a smaller max_tokens may have been truncated - see the
            # max_tokens note on __init__ - and must never be replayed once
            # the ceiling changes).
            "max_tokens": max_tokens,
            "response_format": None,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }

    @staticmethod
    def _parse_json(raw_response: str) -> tuple[Dict[str, Any], str]:
        cleaned = raw_response.strip()
        # strip markdown code fences if the model added them anyway
        cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", cleaned, flags=re.MULTILINE).strip()
        try:
            parsed = json.loads(cleaned)
            merged = dict(_EMPTY_EXTRACTION)
            merged.update({k: v for k, v in parsed.items() if k in _EMPTY_EXTRACTION})
            return merged, ""
        except json.JSONDecodeError as exc:
            fallback = dict(_EMPTY_EXTRACTION)
            fallback["ambiguities"] = [
                "Automatic extraction for this chunk returned malformed JSON and "
                "could not be parsed; this chunk needs manual review."
            ]
            return fallback, str(exc)
