"""
Rule Synthesizer Agent - THE MOST CRITICAL AGENT in the pipeline.

Takes the merged, technical, per-chunk extractions produced by the
Logic Extraction Agent and rewrites them as clear, numbered,
business-intent rules. This is where the system earns (or loses) the
core requirement of the whole project: the output must explain WHAT a
rule accomplishes and WHY it exists from a business/regulatory
standpoint - never restate SQL/PLSQL/T-SQL syntax in English.

All prompt content is loaded from prompts/rule_synthesis.yaml via the
centralized `prompts.prompt_loader` - nothing here is a hardcoded prompt
string. The prompt is selected per SQL dialect (Oracle vs T-SQL), and is
deliberately explicit with a banned-word list, because prompt design for
this exact agent is called out as the hardest and most important part of
the whole build.

Every business rule the model returns is passed through the output
guardrails in `guardrails.py`: the JSON shape is validated/repaired, and
every claimed "fields_affected" entry is cross-checked against the
merged technical extraction and/or the raw source (anti-hallucination
grounding), with the rule's "rule_type" (explicit/inferred/assumption),
"confidence", and "validation_status" preserved so downstream reporting
never presents an inferred or unverifiable claim as a confirmed fact.

Calls an OpenAI-compatible chat completion API directly - no
orchestration framework is involved.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple
from typing import Optional

from src.ingestion.guardrails import ground_business_rules_against_extraction, validate_synthesis_shape
from src.core.llm_client import supports_chat_completion_seed
from src.core.pipeline_utils import PIPELINE_VERSION, stable_id
from src.core.llm_response_cache import PersistentLLMResponseCache
from src.parsing.dedup import dedup_table_operations
from src.prompts.prompt_loader import get_prompt_set, render_user_prompt
from src.telemetry.tracker import LLMTelemetryTracker
from src.validation.coverage_check import find_decision_points

_EMPTY_SYNTHESIS: Dict[str, Any] = {
    "purpose_summary": "",
    "step_by_step_flow": [],
    "business_rules": [],
    "calculations": [],
    "exception_handling_summary": "",
    "ambiguities": [],
}

# A best-effort post-hoc guard: if any banned technical term slips through
# despite the prompt, we flag it rather than silently shipping jargon.
_BANNED_TERMS = [
    "if-elsif", "if statement", "else branch", "for loop", "while loop",
    "update statement", "insert statement", "select statement",
    "merge statement", "cursor", "pl/sql", "t-sql", "exception block",
    "when others", "try/catch",
]


@dataclass
class SynthesisResult:
    data: Dict[str, Any] = field(default_factory=lambda: dict(_EMPTY_SYNTHESIS))
    raw_response: str = ""
    parse_error: str = ""
    jargon_flags: List[str] = field(default_factory=list)
    guardrail_warnings: List[str] = field(default_factory=list)
    truncated: bool = False


_BASE_SYNTHESIS_TOKENS = int(os.environ.get("BASE_SYNTHESIS_TOKENS", "16000"))
_PER_DECISION_POINT_TOKENS = int(os.environ.get("PER_DECISION_POINT_TOKENS", "256"))
_HARD_MAX_OUTPUT_TOKENS = int(os.environ.get("LLM_HARD_MAX_OUTPUT_TOKENS", "32768"))


class RuleSynthesizerAgent:
    """Runs the business-rule synthesis call over the merged technical
    extraction for the whole object, using the configured chat client
    directly.
    """

    def __init__(
        self,
        client,
        model: str,
        temperature: float = 0.1,
        seed: Optional[int] = 0,
        provider: str = "openai",
        response_cache: Optional[PersistentLLMResponseCache] = None,
        max_tokens: int = 16000,
    ):
        """
        Args:
            client: an initialized OpenAI-compatible chat client instance.
            model: the model name to call (configurable per pipeline run).
            temperature: sampling temperature (kept low for extraction tasks).
            max_tokens: explicit output-token cap passed on every completion
                call. This must always be set, even though OpenAI's API
                itself defaults to a generous ceiling when omitted: the
                Bedrock-backed client (`_BedrockChatCompletions.create` in
                `llm_client.py`) defaults its OWN `max_tokens` parameter to
                1024 when the caller doesn't pass one explicitly, which
                silently truncates synthesis JSON for any object whose
                business-rule output exceeds ~1024 tokens (this procedure's
                sample run alone produced ~17K completion tokens) -
                truncated JSON then fails to parse and the pipeline falls
                back to a degraded/empty result with no clear error. Passing
                max_tokens on every call removes the ambiguity for both
                providers instead of relying on a per-provider default.
        """
        self.client = client
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.provider = provider
        self.response_cache = response_cache
        self.max_tokens = max_tokens

    def _output_token_budget(self, raw_source: str, requested: Optional[int] = None) -> int:
        points = len(find_decision_points(raw_source or ""))
        base = max(int(requested or self.max_tokens), _BASE_SYNTHESIS_TOKENS)
        return min(_HARD_MAX_OUTPUT_TOKENS, base + points * _PER_DECISION_POINT_TOKENS)

    def synthesize(
        self,
        object_name: str,
        object_type: str,
        parameter_summary: str,
        merged_extraction: Dict[str, Any],
        dialect: str = "oracle",
        raw_source: str = "",
        model: str | None = None,
        telemetry_tracker: Optional[LLMTelemetryTracker] = None,
    ) -> SynthesisResult:
        """`model`, if given, overrides the agent's configured model for
        just this call - lets callers pick a different model per run
        without re-constructing the agent.
        """
        if str(dialect or "").strip().lower() not in {"oracle", "tsql"}:
            return SynthesisResult(data=dict(_EMPTY_SYNTHESIS))
        prompt_set = get_prompt_set("rule_synthesis.yaml", dialect=dialect)
        compact_merged_extraction = self._build_compact_synthesis_payload(
            merged_extraction,
            raw_source=raw_source,
        )
        user_prompt = render_user_prompt(
            prompt_set["user_template"],
            object_name=object_name,
            object_type=object_type,
            dialect=dialect,
            parameter_summary=parameter_summary or "No parameters.",
            merged_extraction_json=json.dumps(
                compact_merged_extraction,
                separators=(",", ":"),
                default=str,
            ),
        )
        effective_seed = self.seed if self.seed is not None and supports_chat_completion_seed(self.client) else None
        effective_max_tokens = self._output_token_budget(raw_source)
        cache_request = self._build_cache_request(
            stage="synthesis",
            dialect=dialect,
            provider=self.provider,
            model_name=model or self.model,
            system_prompt=prompt_set["system"],
            user_prompt=user_prompt,
            temperature=self.temperature,
            seed=effective_seed,
            max_tokens=effective_max_tokens,
        )
        tracker = telemetry_tracker
        if self.response_cache is not None:
            cache_lookup = self.response_cache.lookup(cache_request)
            if cache_lookup.hit:
                raw_response = cache_lookup.response_text or ""
                data, error = self._parse_json(raw_response)
                if not error:
                    if tracker is not None:
                        tracker.record_cache_lookup(stage="synthesis", hit=True)
                    guardrail_warnings: List[str] = []
                    data, shape_warnings = validate_synthesis_shape(data)
                    guardrail_warnings.extend(shape_warnings)
                    data["business_rules"] = self._normalize_business_rules(
                        data.get("business_rules"),
                        source_text=raw_source,
                        technical_context=merged_extraction,
                    )
                    data["business_rules"] = self._remove_operational_status_rules(
                        data["business_rules"], merged_extraction
                    )
                    data["business_rules"] = self._remove_non_business_cleanup_rules(
                        data["business_rules"], merged_extraction
                    )
                    data["business_rules"] = self._remove_operation_only_rules(data["business_rules"])
                    data["business_rules"] = self._remove_auxiliary_rules(
                        data["business_rules"],
                        merged_extraction,
                        data.get("calculations"),
                        data.get("exception_handling_summary"),
                    )
                    guardrail_warnings.extend(
                        ground_business_rules_against_extraction(
                            data["business_rules"], merged_extraction, raw_source=raw_source
                        )
                    )
                    jargon_flags = self._scan_for_jargon(data)
                    return SynthesisResult(
                        data=data,
                        raw_response=raw_response,
                        parse_error=error,
                        jargon_flags=jargon_flags,
                        guardrail_warnings=guardrail_warnings,
                    )
                self.response_cache.delete(cache_request)
                if tracker is not None and cache_lookup.status != "disabled":
                    tracker.record_cache_lookup(stage="synthesis", hit=False)
            elif cache_lookup.status != "disabled" and tracker is not None:
                tracker.record_cache_lookup(stage="synthesis", hit=False)

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
                        stage="synthesis",
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
            else:
                retry = self._retry_with_ceiling(completion_kwargs, telemetry_tracker)
                if retry is not None:
                    response, raw_response = retry
                    finish_reason = str(getattr(response.choices[0], "finish_reason", "") or "").lower()
                    truncated = truncated or finish_reason == "length"
                    data, error = self._parse_json(raw_response)
                    if truncated and error:
                        recovered = self._recover_partial_json(raw_response)
                        if recovered is not None:
                            data, error = recovered, ""
        if error:
            jargon_flags = self._scan_for_jargon(data)
            return SynthesisResult(
                data=data,
                raw_response=raw_response,
                parse_error=error,
                jargon_flags=jargon_flags,
                guardrail_warnings=[],
                truncated=truncated,
            )

        guardrail_warnings: List[str] = []
        if truncated:
            guardrail_warnings.append(
                "Synthesis response reached the output limit; recovered rules may be incomplete."
            )
            # Also surface this to the reader. A truncated synthesis is the
            # single most likely cause of a missing purpose summary, missing
            # process flow, missing calculations, or a short rule list - the
            # report must say so rather than printing a placeholder that reads
            # like "the source contained nothing here".
            existing = data.get("ambiguities")
            data["ambiguities"] = list(existing or []) + [
                "The automated analysis of this procedure exceeded the model's maximum "
                "response length and was cut short. Sections of this report may be "
                "incomplete or missing entirely. Re-run with a larger model before "
                "treating this document as a complete record of the procedure's logic."
            ]
        data, shape_warnings = validate_synthesis_shape(data)
        guardrail_warnings.extend(shape_warnings)
        data["business_rules"] = self._normalize_business_rules(
            data.get("business_rules"),
            source_text=raw_source,
            technical_context=merged_extraction,
        )
        data["business_rules"] = self._remove_operational_status_rules(
            data["business_rules"], merged_extraction
        )
        data["business_rules"] = self._remove_non_business_cleanup_rules(
            data["business_rules"], merged_extraction
        )
        data["business_rules"] = self._remove_operation_only_rules(data["business_rules"])
        data["business_rules"] = self._remove_auxiliary_rules(
            data["business_rules"],
            merged_extraction,
            data.get("calculations"),
            data.get("exception_handling_summary"),
        )
        guardrail_warnings.extend(
            ground_business_rules_against_extraction(
                data["business_rules"], merged_extraction, raw_source=raw_source
            )
        )

        jargon_flags = self._scan_for_jargon(data)
        if self.response_cache is not None and not error:
            self.response_cache.store(cache_request, raw_response)
        return SynthesisResult(
            data=data,
            raw_response=raw_response,
            parse_error=error,
            jargon_flags=jargon_flags,
            guardrail_warnings=guardrail_warnings,
            truncated=truncated,
        )

    # Keys whose value is a JSON array of independently-useful items. If the
    # truncation lands *inside* one of these arrays, the complete items before
    # the cut are still recoverable.
    _RECOVERABLE_LIST_KEYS = (
        "business_rules",
        "calculations",
        "ambiguities",
        "step_by_step_flow",
    )

    @staticmethod
    def _recover_partial_json(raw_response: str) -> Optional[Dict[str, Any]]:
        """Recover every complete top-level key from a length-truncated object.

        A truncated synthesis response is not empty - it is a valid JSON
        prefix. Everything emitted before the cut is intact, and because the
        schema orders `purpose_summary` and `step_by_step_flow` *before*
        `business_rules`, those keys are almost always complete even when the
        rule array is not.

        The previous implementation searched only for `"business_rules"` and
        returned `{"business_rules": items}`, silently discarding
        `purpose_summary`, `step_by_step_flow`, `calculations`, and
        `exception_handling_summary`. That is why a truncated run produced a
        report with four dead placeholder sections while the model had
        actually returned all four.

        This walks the object key-by-key with `raw_decode`, keeping every key
        that decodes cleanly, and falls back to per-item salvage for the one
        array the cut landed inside.
        """
        text = str(raw_response or "").strip()
        if not text:
            return None
        fence = re.match(r"^```(?:json)?\s*(.*)$", text, re.DOTALL)
        if fence:
            text = fence.group(1)
        start = text.find("{")
        if start == -1:
            return None

        decoder = json.JSONDecoder()
        recovered: Dict[str, Any] = {}
        cursor = start + 1

        def _skip_ws(index: int) -> int:
            while index < len(text) and text[index].isspace():
                index += 1
            return index

        while True:
            cursor = _skip_ws(cursor)
            if cursor >= len(text) or text[cursor] == "}":
                break
            if text[cursor] != '"':
                break
            try:
                key, cursor = decoder.raw_decode(text, cursor)
            except json.JSONDecodeError:
                break
            cursor = _skip_ws(cursor)
            if cursor >= len(text) or text[cursor] != ":":
                break
            cursor = _skip_ws(cursor + 1)
            if cursor >= len(text):
                break
            try:
                value, end = decoder.raw_decode(text, cursor)
            except json.JSONDecodeError:
                # The cut landed inside this value. If it is one of the
                # recoverable arrays, keep the complete items before the cut.
                if text[cursor] == "[" and str(key) in RuleSynthesizerAgent._RECOVERABLE_LIST_KEYS:
                    items = RuleSynthesizerAgent._recover_list_items(text, cursor + 1, decoder)
                    if items:
                        recovered[str(key)] = items
                break
            recovered[str(key)] = value
            cursor = _skip_ws(end)
            if cursor < len(text) and text[cursor] == ",":
                cursor += 1
                continue
            break

        return recovered or None

    @staticmethod
    def _recover_list_items(text: str, cursor: int, decoder: json.JSONDecoder) -> List[Any]:
        """Return the complete items of a truncated JSON array."""
        items: List[Any] = []
        while cursor < len(text):
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            if cursor >= len(text) or text[cursor] == "]":
                break
            try:
                item, end = decoder.raw_decode(text, cursor)
            except json.JSONDecodeError:
                break
            items.append(item)
            cursor = end
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            if cursor < len(text) and text[cursor] == ",":
                cursor += 1
                continue
            break
        return items

    def _retry_with_ceiling(self, completion_kwargs: Dict[str, Any], tracker) -> Optional[Tuple[Any, str]]:
        ceiling = max(int(completion_kwargs.get("max_tokens", 0) or 0), _HARD_MAX_OUTPUT_TOKENS)
        if ceiling <= int(completion_kwargs.get("max_tokens", 0) or 0):
            return None
        retry_kwargs = dict(completion_kwargs)
        retry_kwargs["max_tokens"] = ceiling
        response = None
        start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(**retry_kwargs)
            return response, response.choices[0].message.content or ""
        finally:
            if tracker is not None:
                try:
                    tracker.record_call(
                        stage="synthesis_retry",
                        provider=self.provider,
                        model_name=retry_kwargs.get("model", self.model),
                        response=response,
                        latency_seconds=time.perf_counter() - start,
                        success=response is not None,
                        error=None,
                    )
                except Exception:
                    pass

    def revise(
        self,
        object_name: str,
        object_type: str,
        parameter_summary: str,
        merged_extraction: Dict[str, Any],
        existing_rules: List[Dict[str, Any]],
        gaps: Sequence[Any],
        dialect: str = "oracle",
        raw_source: str = "",
        model: str | None = None,
        telemetry_tracker: Optional[LLMTelemetryTracker] = None,
    ) -> Optional[SynthesisResult]:
        """Ask the model to review specific, deterministically-identified
        gaps and return its own updated, complete rule set.

        This is the coverage-driven counterpart to `synthesize()`. It is
        deliberately NOT a deterministic content generator: every rule it
        returns is model-authored business language, same as the first
        pass. What's deterministic is only *where to look again* - the
        caller (`pipeline.py`) supplies `gaps`, each a source line range
        and snippet that a purely syntactic scan
        (`src/validation/coverage_check.py`) found no rule's evidence
        pointing at. That scan has no idea what the branch means; it only
        knows a CASE/WHEN/IF/ELSIF keyword sits there un-cited. The model
        is always free to conclude a gap is not business-relevant (e.g. a
        technical-only branch) and say so - this never forces a rule into
        existence, it only forces the model to look and explain itself.

        Returns None (never raises past the caller) if there are no gaps
        to review, so callers can safely call this in a loop without
        special-casing the empty case.
        """
        if not gaps:
            return None
        if str(dialect or "").strip().lower() not in {"oracle", "tsql"}:
            return None
        prompt_set = get_prompt_set("rule_synthesis.yaml", dialect=dialect)
        compact_merged_extraction = self._build_compact_synthesis_payload(
            merged_extraction,
            raw_source=raw_source,
        )
        gap_lines = []
        for gap in gaps:
            line_start = getattr(gap, "line_start", None)
            line_end = getattr(gap, "line_end", None)
            snippet = getattr(gap, "snippet", "")
            gap_lines.append(
                f"- Lines {line_start}-{line_end}:\n  {snippet}"
            )
        gaps_block = "\n".join(gap_lines) if gap_lines else "(none)"
        existing_rules_json = json.dumps(
            existing_rules or [], separators=(",", ":"), default=str
        )
        revision_instructions = (
            "REVIEW PASS - a separate, purely syntactic scan of the source "
            "(it does not understand SQL semantics, only keyword positions) "
            "found the source line ranges below containing a CASE/WHEN/IF/"
            "ELSIF keyword that is not cited as evidence by any rule in your "
            "previous extraction. This does not mean logic was necessarily "
            "missed - it may be a technical-only branch, or already covered "
            "by a rule whose evidence text just didn't happen to quote that "
            "line. For EACH line range below:\n"
            "  1. Re-read that exact source snippet.\n"
            "  2. If it expresses a business decision, calculation, or "
            "condition not already represented, ADD a new rule for it "
            "(same schema and business-language rules as before), with "
            "`source_evidence` quoting the exact condition/branch text so "
            "it is traceable back to these lines.\n"
            "  3. If it is genuinely technical-only (e.g. cursor bookkeeping, "
            "temp-table cleanup) or already covered by an existing rule, "
            "leave it out - do not fabricate a rule to satisfy the count.\n\n"
            f"UNREVIEWED SOURCE LOCATIONS:\n{gaps_block}\n\n"
            f"YOUR PREVIOUS RULES (JSON array - keep every rule that is "
            f"still correct, unchanged):\n{existing_rules_json}\n\n"
            "Return the COMPLETE business_rules array in your response: "
            "every previously-correct rule plus any new rules from this "
            "review. Do not drop a previously-correct rule just because it "
            "isn't mentioned above. Same JSON schema as before."
        )
        user_prompt = render_user_prompt(
            prompt_set["user_template"],
            object_name=object_name,
            object_type=object_type,
            dialect=dialect,
            parameter_summary=parameter_summary or "No parameters.",
            merged_extraction_json=json.dumps(
                compact_merged_extraction,
                separators=(",", ":"),
                default=str,
            ),
        )
        user_prompt = f"{user_prompt}\n\n{revision_instructions}"
        effective_seed = self.seed if self.seed is not None and supports_chat_completion_seed(self.client) else None
        completion_kwargs = {
            "model": model or self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
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
            if telemetry_tracker is not None:
                try:
                    telemetry_tracker.record_call(
                        stage="synthesis_revision",
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

        data, error = self._parse_json(raw_response)
        if error:
            # A revision pass that fails to parse must never wipe out an
            # already-good rule set - keep what synthesize() produced and
            # let the gap simply remain flagged for human review.
            return None

        guardrail_warnings: List[str] = []
        data, shape_warnings = validate_synthesis_shape(data)
        guardrail_warnings.extend(shape_warnings)
        data["business_rules"] = self._normalize_business_rules(
            data.get("business_rules"),
            source_text=raw_source,
            technical_context=merged_extraction,
        )
        data["business_rules"] = self._remove_operational_status_rules(
            data["business_rules"], merged_extraction
        )
        data["business_rules"] = self._remove_non_business_cleanup_rules(
            data["business_rules"], merged_extraction
        )
        data["business_rules"] = self._remove_operation_only_rules(data["business_rules"])
        data["business_rules"] = self._remove_auxiliary_rules(
            data["business_rules"],
            merged_extraction,
            data.get("calculations"),
            data.get("exception_handling_summary"),
        )
        jargon_flags = self._scan_for_jargon(data)
        return SynthesisResult(
            data=data,
            raw_response=raw_response,
            parse_error=error,
            jargon_flags=jargon_flags,
            guardrail_warnings=guardrail_warnings,
        )

    @staticmethod
    def _build_compact_synthesis_payload(
        merged_extraction: Dict[str, Any],
        raw_source: str = "",
    ) -> Dict[str, Any]:
        """Return only the technical facts the synthesis prompt can use.

        This is a prompt-size reduction only: `merged_extraction` itself
        is never mutated, so grounding, reconciliation, the verification
        report, and downstream reporting still see the full,
        non-deduplicated evidence (every raw statement occurrence, every
        chunk's embedded SQL, full statement provenance). Only what gets
        serialized into the *synthesis LLM prompt* is compacted here.

        The payload intentionally keeps the prompt compact: the
        deduplicated `table_operations` view is the table-evidence input
        used by synthesis, while the heavier provenance transport fields
        stay out of the synthesis prompt so they do not bloat the model
        context. The compact view is a prompt-size aid; it does not
        replace the original evidence in `merged_extraction`.
        """

        if not isinstance(merged_extraction, dict):
            return {}

        payload = OrderedDict()
        payload["conditions"] = merged_extraction.get("conditions", []) or []
        payload["decision_chains"] = merged_extraction.get("decision_chains", []) or []
        payload["loops"] = merged_extraction.get("loops", []) or []

        raw_table_operations = merged_extraction.get("table_operations", []) or []
        if isinstance(raw_table_operations, list) and raw_table_operations:
            payload["table_operations"] = dedup_table_operations(raw_table_operations)
        else:
            # Fallback for objects where deterministic statement parsing
            # produced nothing (unsupported dialect / parse failure) -
            # the LLM-extracted tables_read/tables_written are the only
            # evidence available, so they still need to reach the prompt
            # in that case. Also deduplicated by the same grouping logic
            # so repeated LLM-extracted references don't reintroduce the
            # same duplication from the other direction.
            fallback_ops = list(merged_extraction.get("tables_read", []) or []) + list(
                merged_extraction.get("tables_written", []) or []
            )
            payload["table_operations"] = dedup_table_operations(fallback_ops) if fallback_ops else []

        payload["calculations"] = merged_extraction.get("calculations", []) or []
        payload["exception_handling"] = merged_extraction.get("exception_handling", []) or []
        payload["ambiguities"] = merged_extraction.get("ambiguities", []) or []
        # Nested procedural chunks can be structurally incomplete while the
        # original source remains available. Keep it separate from the
        # deterministic fact view so the model can recover missing context
        # without changing the facts used by reconciliation.
        if str(raw_source or "").strip():
            payload["source_sql"] = str(raw_source)
        return payload

    @staticmethod
    def _remove_operational_status_rules(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Keep process bookkeeping out of the business-rule collection.

        This applies only when deterministic operations identify the rule as a
        process-status write. The operation and its evidence remain available
        through the merged technical extraction and verification output.
        """
        status_fields = {
            "COMPLETED", "ERRORDATE", "ERRORDESCRIPTION", "COUNT",
            "RUNNINGPROCESSNAME",
        }
        status_tables = {
            str(row.get("table") or "").strip().upper()
            for row in (merged_extraction or {}).get("table_operations", []) or []
            if isinstance(row, dict)
            and "runningprocessstatus" in str(row.get("table") or "").lower()
        }
        if not status_tables:
            return list(rules or [])

        filtered: List[Dict[str, Any]] = []
        for rule in rules or []:
            if not isinstance(rule, dict):
                continue
            text = json.dumps(rule, sort_keys=True, default=str).upper()
            raw_fields = rule.get("fields_affected", [])
            if isinstance(raw_fields, str):
                raw_fields = [raw_fields]
            fields = {
                token.strip().upper().split(".")[-1]
                for token in raw_fields or []
            }
            is_status_rule = bool(fields & status_fields) and any(
                marker in text
                for marker in (
                    "PROCESS STATUS", "RUNNING PROCESS", "ERROR DESCRIPTION",
                    "COMPLETION", "COMPLETED",
                )
            )
            if not is_status_rule:
                filtered.append(rule)
        return filtered

    @staticmethod
    def _remove_non_business_cleanup_rules(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Keep pure temporary-object cleanup in technical lineage only.

        A DROP of a temporary table is an execution concern, not a business
        decision. This narrow filter requires deterministic operation
        evidence and an empty business-field set, so it cannot hide a rule
        describing a meaningful state change. The operation remains in
        ``merged_extraction`` for verification and provenance consumers.
        """
        operations = [
            row for row in (merged_extraction or {}).get("table_operations", []) or []
            if isinstance(row, dict)
            and str(row.get("active_status") or "ACTIVE").upper() == "ACTIVE"
            and str(row.get("operation") or "").upper() == "DROP"
        ]
        cleanup_tables = {
            str(row.get("table") or "").strip().upper()
            for row in operations
            if re.search(r"(^#|TEMP|TMP|TEMPORARY)", str(row.get("table") or ""), re.IGNORECASE)
        }
        filtered: List[Dict[str, Any]] = []
        for rule in rules or []:
            if not isinstance(rule, dict):
                continue
            fields = rule.get("fields_affected") or []
            if isinstance(fields, str):
                fields = [fields]
            has_business_fields = any(str(field).strip() for field in fields)
            rule_text = json.dumps(rule, sort_keys=True, default=str).lower()
            evidence_text = " ".join(
                str(item) for item in (rule.get("source_evidence") or [])
            )
            # Parser metadata is preferred, but a valid source citation is
            # sufficient to classify a technical DROP when the statement
            # parser could not build an operation record for that dialect or
            # syntax variant. This remains deletion-only and does not infer
            # business meaning.
            cleanup_evidence = bool(re.search(
                r"\bDROP\s+TABLE\b.*(?:#|TEMP|TMP|TEMPORARY)",
                evidence_text,
                re.IGNORECASE | re.DOTALL,
            ))
            is_cleanup_description = any(
                marker in rule_text for marker in ("drop", "temporary", "temp table", "cleanup")
            )
            decision_rows = [
                row for row in (rule.get("decision_logic_rows") or [])
                if isinstance(row, dict)
            ]
            distinct_outcomes = {
                json.dumps(row, sort_keys=True, default=str)
                for row in decision_rows
            }
            condition = str(rule.get("condition") or "").strip()
            existence_guard = bool(re.search(
                r"\b(?:if\s+)?(?:object_id\s*\([^)]*\)|table\s+\S+|\S+\s+exists)"
                r"(?:\s+is\s+not\s+null|\s+exists)?\b",
                condition,
                re.IGNORECASE,
            ))
            has_genuine_decision = len(distinct_outcomes) >= 2 or (
                bool(condition) and not existence_guard
            )
            is_cleanup = bool(cleanup_tables) or cleanup_evidence or existence_guard
            if is_cleanup and is_cleanup_description and not has_business_fields and not has_genuine_decision:
                continue
            filtered.append(rule)
        return filtered

    @staticmethod
    def _remove_operation_only_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Exclude CRUD mechanics that do not express a business decision."""
        filtered: List[Dict[str, Any]] = []
        for rule in rules or []:
            if not isinstance(rule, dict):
                continue
            if rule.get("decision_logic_rows"):
                filtered.append(rule)
                continue
            evidence = " ".join(str(item) for item in rule.get("source_evidence") or []).upper()
            name = str(rule.get("rule_name") or "").lower()
            action = str(rule.get("action") or "").lower()
            is_crud = bool(re.search(r"\b(SELECT|UPDATE|INSERT|DELETE|MERGE)\b", evidence))
            is_mechanical = (
                "source-defined value" in action
                or "source-defined value" in name
                or (name.startswith(("update ", "insert ", "write ")) and not rule.get("eligibility"))
            )
            if is_crud and is_mechanical:
                continue
            filtered.append(rule)
        return filtered

    @staticmethod
    def _remove_auxiliary_rules(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
        calculations: Any = None,
        exception_summary: Any = None,
    ) -> List[Dict[str, Any]]:
        """Keep calculation/exception-only items in their own sections.

        This is a deletion-only classification filter. It never changes a
        rule or creates a replacement. A rule with actual conditions or
        decision rows is retained because a calculation or failure path can
        also be a genuine business decision.
        """
        calculation_fields = set()
        for calculation in calculations or []:
            if not isinstance(calculation, dict):
                continue
            for key in ("name", "result", "field", "metric", "output_field", "destination"):
                value = str(calculation.get(key) or "").strip()
                if value:
                    calculation_fields.add(value.casefold().split(".")[-1])

        exception_items = list((merged_extraction or {}).get("exception_handling", []) or [])
        exception_items.append(exception_summary or "")
        exception_context = " ".join(str(item) for item in exception_items).casefold()
        filtered: List[Dict[str, Any]] = []
        for rule in rules or []:
            if not isinstance(rule, dict):
                continue
            has_condition = bool(str(rule.get("condition") or "").strip() or rule.get("eligibility"))
            has_decision_rows = bool(rule.get("decision_logic_rows"))
            if has_condition or has_decision_rows:
                filtered.append(rule)
                continue

            fields = [str(rule.get("output_field") or ""), *(rule.get("fields_affected") or [])]
            field_names = {value.casefold().split(".")[-1] for value in fields if str(value).strip()}
            rule_text = json.dumps(rule, sort_keys=True, default=str).casefold()
            is_calculation_only = bool(calculation_fields & field_names) and bool(
                re.search(r"\bcalculat(?:e|es|ed|ion|ing)\b|\bformula\b|\bexpression\b", rule_text)
            )
            is_exception_only = bool(exception_context) and bool(
                re.search(r"\bexception\b|\braise\b|\bfailure path\b|\berror handling\b", rule_text)
            )
            if is_calculation_only or is_exception_only:
                continue
            filtered.append(rule)
        return filtered

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
        cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", cleaned, flags=re.MULTILINE).strip()
        try:
            parsed = RuleSynthesizerAgent._decode_json_payload(cleaned)
            merged = dict(_EMPTY_SYNTHESIS)
            merged.update({k: v for k, v in parsed.items() if k in _EMPTY_SYNTHESIS})
            merged["business_rules"] = RuleSynthesizerAgent._normalize_business_rules(
                merged.get("business_rules")
            )
            return merged, ""
        except json.JSONDecodeError as exc:
            fallback = dict(_EMPTY_SYNTHESIS)
            fallback["ambiguities"] = [
                "Business rule synthesis returned malformed JSON and could not be "
                "parsed; the full object needs manual review."
            ]
            return fallback, str(exc)

    @staticmethod
    def _decode_json_payload(cleaned: str) -> Dict[str, Any]:
        """Parse a JSON object from the model output.

        The model is expected to return strict JSON, but in practice it
        may wrap the object in a brief preamble or trailing prose. We try
        the strict parse first, then fall back to locating the first
        decodable JSON object in the text so recoverable responses do not
        collapse into an empty synthesis result.
        """
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            for start in (match.start() for match in re.finditer(r"[\{\[]", cleaned)):
                try:
                    parsed, _ = decoder.raw_decode(cleaned[start:])
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict) and set(parsed).intersection(_EMPTY_SYNTHESIS):
                    return parsed
            raise
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("Expected a JSON object", cleaned, 0)
        return parsed

    @staticmethod
    def _normalize_business_rules(
        raw_rules: Any,
        source_text: str = "",
        technical_context: Any = None,
    ) -> List[Dict[str, Any]]:
        """Coerce model output to the stable rule schema without rewriting it.

        This method intentionally does not infer missing business meaning,
        normalize terminology, merge rules, or alter any model-authored text.
        """
        if not isinstance(raw_rules, list):
            return []

        def as_list(value: Any) -> List[Any]:
            if value is None:
                return []
            if isinstance(value, list):
                return list(value)
            if isinstance(value, str):
                return [value]
            return []

        def as_dict_list(value: Any) -> List[Dict[str, Any]]:
            return [item for item in as_list(value) if isinstance(item, dict)]

        normalized: List[Dict[str, Any]] = []
        for raw_rule in raw_rules:
            if not isinstance(raw_rule, dict):
                continue
            rule = dict(raw_rule)
            for key in ("rule_name", "business_meaning", "condition", "action", "output_field"):
                value = rule.get(key, "")
                rule[key] = value if isinstance(value, str) else ("" if value is None else str(value))
            for key in (
                "eligibility", "decision_logic", "tie_priority_handling", "default",
                "when_not_eligible", "fields_affected", "source_evidence", "source_chunks",
                "technical_references", "unresolved_ambiguities", "dependencies",
            ):
                rule[key] = as_list(rule.get(key))
            rule["decision_logic_rows"] = as_dict_list(rule.get("decision_logic_rows"))
            for key in ("rule_type", "confidence", "validation_status", "rule_id", "ambiguity_id"):
                value = rule.get(key, "")
                rule[key] = value if isinstance(value, str) else ("" if value is None else str(value))
            normalized.append(rule)
        return normalized

    @staticmethod
    def _scan_for_jargon(data: Dict[str, Any]) -> List[str]:
        flat_text = json.dumps(data).lower()
        return [term for term in _BANNED_TERMS if term in flat_text]
