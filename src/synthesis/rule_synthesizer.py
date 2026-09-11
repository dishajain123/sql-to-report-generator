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

from src.parsing.sql_comments import executable_sql

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
_SYNTHESIS_EVIDENCE_MAP_MAX_CHARS = int(
    os.environ.get("SYNTHESIS_EVIDENCE_MAP_MAX_CHARS", "12000")
)
_SYNTHESIS_EVIDENCE_TEXT_MAX_CHARS = int(
    os.environ.get("SYNTHESIS_EVIDENCE_TEXT_MAX_CHARS", "240")
)
# Secondary cap (alongside the decision-point budget below) on how much raw
# source text a single synthesis *section* is allowed to accumulate when
# `plan_synthesis_sections` groups extraction chunks together. Bounds the
# prompt size for chunks that carry little/no decision logic (so they don't
# consume any of the decision-point budget) but are still large in plain
# character count.
_SYNTHESIS_SECTION_MAX_CHARS = int(os.environ.get("SYNTHESIS_SECTION_MAX_CHARS", "24000"))


class RuleSynthesizerAgent:
    """Runs the business-rule synthesis call over the merged technical
    extraction for the whole object, using the configured chat client
    directly.
    """

    # Matches a short run (2-24 chars) repeated back-to-back 6+ times, e.g.
    # "SMA_SMA_SMA_SMA_SMA_SMA_" - the shape a small/rate-limited model
    # produces when it degenerates into a token loop near its own output
    # ceiling instead of stopping cleanly. This is a *literal* immediate
    # repetition check (the same substring recurring with nothing else in
    # between), so it does not fire on ordinary business/SQL text that
    # happens to reuse the same word or column name several times with
    # other content between occurrences (see `_is_degenerate_text`).
    _DEGENERATE_REPEAT_PATTERN = re.compile(r"(.{2,24}?)\1{5,}")

    @staticmethod
    def _is_degenerate_text(text: Any) -> bool:
        """True when `text` contains a long run of literal token repetition
        characteristic of generation degeneration, not ordinary prose/SQL.

        Guarded by two thresholds so a short, coincidental repeat inside
        otherwise normal text is never flagged: the repeated run itself must
        be at least 20 characters, and must make up at least a quarter of
        the whole string.
        """
        if not isinstance(text, str) or not text:
            return False
        match = RuleSynthesizerAgent._DEGENERATE_REPEAT_PATTERN.search(text)
        if not match:
            return False
        span = match.end() - match.start()
        return span >= 20 and span / max(1, len(text)) >= 0.25

    def __init__(
        self,
        client,
        model: str,
        temperature: float = 0.1,
        seed: Optional[int] = 0,
        provider: str = "openai",
        response_cache: Optional[PersistentLLMResponseCache] = None,
        max_tokens: int = 16000,
        hard_max_output_tokens: Optional[int] = None,
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
            hard_max_output_tokens: the REAL, server-enforced maximum
                completion tokens for the configured provider/model (see
                `llm_client.resolve_model_output_ceiling`), when known.
                Every single-pass/sectioning budget decision below must be
                bounded by this, not by the generic
                `LLM_HARD_MAX_OUTPUT_TOKENS` module default (32768) - some
                real Bedrock models (Amazon Nova Lite/Micro/Pro) cap
                completions at 5000 tokens server-side regardless of what
                `max_tokens` a caller requests. Sizing the single-pass/
                sectioning budget against the generic default when the real
                ceiling is smaller under-triggers sectioning and produces
                sections still too large for the model to complete, so
                truncation happens no matter how it's retried. Defaults to
                the module-level `_HARD_MAX_OUTPUT_TOKENS` when not given
                (unknown provider/model, or a caller that predates this
                parameter).
        """
        self.client = client
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.provider = provider
        self.response_cache = response_cache
        self.max_tokens = max_tokens
        self.hard_max_output_tokens = (
            int(hard_max_output_tokens) if hard_max_output_tokens else _HARD_MAX_OUTPUT_TOKENS
        )

    def _estimate_output_tokens(self, raw_source: str, requested: Optional[int] = None) -> int:
        """Projected completion tokens a single synthesis call over
        `raw_source` would need, *before* clamping to the hard per-call
        ceiling. Exposed (via `requires_sectioned_synthesis`) so a caller can
        detect ahead of time that a single pass is effectively guaranteed to
        truncate mid-JSON, instead of only discovering it from a
        `finish_reason == "length"` response after the call.
        """
        points = len(find_decision_points(raw_source or ""))
        base = max(int(requested or self.max_tokens), _BASE_SYNTHESIS_TOKENS)
        return base + points * _PER_DECISION_POINT_TOKENS

    def _output_token_budget(self, raw_source: str, requested: Optional[int] = None) -> int:
        return min(self.hard_max_output_tokens, self._estimate_output_tokens(raw_source, requested))

    def requires_sectioned_synthesis(self, raw_source: str, requested: Optional[int] = None) -> bool:
        """True when a single synthesis call over the whole `raw_source`
        would need more completion tokens than the hard output ceiling
        allows. In that case the call is not merely at risk of truncating -
        it is virtually guaranteed to, because `_output_token_budget` will
        clamp the request down to the ceiling regardless of how many rules
        actually need to be produced. Callers should use
        `plan_synthesis_sections` and one `synthesize()` call per section
        instead of a single whole-object call.
        """
        return self._estimate_output_tokens(raw_source, requested) > self.hard_max_output_tokens

    def plan_synthesis_sections(
        self,
        chunks: Sequence[Any],
        full_raw_source: str,
        requested: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Group extraction chunks into contiguous synthesis sections.

        `chunks` is the same ordered list of `src.ingestion.ingestion.CodeChunk`
        objects (or chunk-shaped dicts) already produced for the extraction
        stage - this reuses those boundaries rather than introducing a second,
        independent split of the source. Each returned section is sized so its
        own decision-point count stays comfortably under the hard output-token
        ceiling (leaving headroom under `_HARD_MAX_OUTPUT_TOKENS` so the
        section's own eventual `_output_token_budget` call never itself needs
        to clamp), with a secondary character-count cap for chunks that carry
        little decision logic but a lot of plain text. A chunk is never split
        across two sections.

        Returns a list of `{"chunk_ids": [...], "char_start": int|None,
        "char_end": int|None}` dicts in source order. A source with no chunks
        comes back as a single all-covering entry with an empty chunk-id list,
        so callers can treat "no sectioning possible" and "one section is
        enough" the same way.
        """
        chunk_list = list(chunks or [])
        if not chunk_list:
            return [{
                "chunk_ids": [],
                "char_start": 0,
                "char_end": len(full_raw_source or ""),
            }]

        base = max(int(requested or self.max_tokens), _BASE_SYNTHESIS_TOKENS)
        # `base` is the single-pass whole-object budget floor (16000 by
        # default) - appropriate headroom to reserve when the real hard
        # ceiling comfortably exceeds it, but nonsensical to subtract
        # wholesale from a *per-model* ceiling that's smaller than `base`
        # itself (e.g. Amazon Nova Lite's real 5000-token cap): that would
        # make every section's budget collapse to the 1-decision-point
        # floor, producing one synthesis call per chunk instead of sensibly
        # grouped sections. Capping the reserved overhead at half the real
        # ceiling keeps a meaningful chunk of the ceiling available for
        # decision-point-driven content on every model, while leaving the
        # existing large-ceiling behavior (`min(base, ceiling // 2) == base`
        # whenever `ceiling >= 2 * base`) unchanged.
        section_overhead = min(base, self.hard_max_output_tokens // 2)
        section_token_budget = max(_PER_DECISION_POINT_TOKENS, self.hard_max_output_tokens - section_overhead)
        section_point_budget = max(1, section_token_budget // max(1, _PER_DECISION_POINT_TOKENS))

        sections: List[Dict[str, Any]] = []
        current_ids: List[str] = []
        current_start: Optional[int] = None
        current_end: Optional[int] = None
        current_points = 0
        current_chars = 0

        def _flush() -> None:
            if current_ids:
                sections.append({
                    "chunk_ids": list(current_ids),
                    "char_start": current_start,
                    "char_end": current_end,
                })

        for chunk in chunk_list:
            if isinstance(chunk, dict):
                chunk_id = chunk.get("chunk_id")
                chunk_text = chunk.get("text", "") or ""
                char_start = chunk.get("source_char_start", -1)
                char_end = chunk.get("source_char_end", -1)
            else:
                chunk_id = getattr(chunk, "chunk_id", None)
                chunk_text = getattr(chunk, "text", "") or ""
                char_start = getattr(chunk, "source_char_start", -1)
                char_end = getattr(chunk, "source_char_end", -1)
            chunk_points = max(1, len(find_decision_points(chunk_text)))
            chunk_chars = len(chunk_text)

            would_exceed_points = current_points + chunk_points > section_point_budget
            would_exceed_chars = current_chars + chunk_chars > _SYNTHESIS_SECTION_MAX_CHARS
            if current_ids and (would_exceed_points or would_exceed_chars):
                _flush()
                current_ids, current_start, current_end = [], None, None
                current_points, current_chars = 0, 0

            current_ids.append(chunk_id)
            current_points += chunk_points
            current_chars += chunk_chars
            if isinstance(char_start, int) and char_start >= 0:
                current_start = char_start if current_start is None else min(current_start, char_start)
            if isinstance(char_end, int) and char_end >= 0:
                current_end = char_end if current_end is None else max(current_end, char_end)

        _flush()
        return sections

    @staticmethod
    def merge_section_results(results: Sequence["SynthesisResult"]) -> "SynthesisResult":
        """Combine the per-section `SynthesisResult`s produced by sectioned
        synthesis (one call per `plan_synthesis_sections` entry) back into a
        single whole-object result shaped exactly like a normal `synthesize()`
        return value, so every downstream consumer (coverage-gap revision,
        reconciliation, report formatting) keeps working against one
        `SynthesisResult` without change.
        """
        usable = [item for item in results if isinstance(item, SynthesisResult)]
        if not usable:
            return SynthesisResult(data=dict(_EMPTY_SYNTHESIS))
        if len(usable) == 1:
            return usable[0]

        def _dedup_preserve_order(values: Sequence[Any]) -> List[Any]:
            seen: set = set()
            ordered: List[Any] = []
            for value in values:
                key = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(value)
            return ordered

        purpose_summaries = [str(item.data.get("purpose_summary") or "").strip() for item in usable]
        merged_purpose = "\n\n".join(_dedup_preserve_order([text for text in purpose_summaries if text]))

        exception_summaries = [
            str(item.data.get("exception_handling_summary") or "").strip() for item in usable
        ]
        merged_exception_summary = " ".join(
            _dedup_preserve_order([text for text in exception_summaries if text])
        )

        def _rule_identity_key(rule: Dict[str, Any]) -> Tuple[str, str, str, str]:
            # Sectioning runs the same synthesis prompt once per section, and
            # overlapping/duplicated evidence (e.g. a rule whose condition
            # spans a boundary and gets re-derived by two adjacent sections)
            # can produce the exact same rule twice. Identity on the
            # business-meaning fields - not `rule_id` (regenerated per call)
            # or any other volatile field - so only genuine duplicates
            # collapse.
            return (
                str(rule.get("rule_name") or "").strip(),
                str(rule.get("condition") or "").strip(),
                str(rule.get("action") or "").strip(),
                str(rule.get("output_field") or "").strip(),
            )

        def _rule_has_degenerate_text(rule: Dict[str, Any]) -> bool:
            return any(
                RuleSynthesizerAgent._is_degenerate_text(rule.get(key))
                for key in ("rule_name", "condition", "action", "business_meaning")
            )

        dropped_degenerate = False

        merged_steps_raw: List[str] = []
        for item in usable:
            for step in item.data.get("step_by_step_flow") or []:
                step_text = str(step)
                if not step_text.strip():
                    continue
                if RuleSynthesizerAgent._is_degenerate_text(step_text):
                    dropped_degenerate = True
                    continue
                merged_steps_raw.append(step_text)
        merged_steps = _dedup_preserve_order(merged_steps_raw)

        merged_rules: List[Dict[str, Any]] = []
        seen_rule_keys: set = set()
        for item in usable:
            for rule in item.data.get("business_rules") or []:
                if not isinstance(rule, dict):
                    continue
                if _rule_has_degenerate_text(rule):
                    dropped_degenerate = True
                    continue
                key = _rule_identity_key(rule)
                if key in seen_rule_keys:
                    continue
                seen_rule_keys.add(key)
                merged_rules.append(rule)

        merged_calculations: List[Dict[str, Any]] = []
        for item in usable:
            merged_calculations.extend(
                calc for calc in (item.data.get("calculations") or []) if isinstance(calc, dict)
            )

        merged_ambiguities: List[str] = []
        for item in usable:
            merged_ambiguities.extend(
                str(value) for value in (item.data.get("ambiguities") or []) if str(value).strip()
            )
        merged_ambiguities = _dedup_preserve_order(merged_ambiguities)

        merged_data: Dict[str, Any] = dict(_EMPTY_SYNTHESIS)
        merged_data["purpose_summary"] = merged_purpose
        merged_data["exception_handling_summary"] = merged_exception_summary
        merged_data["step_by_step_flow"] = merged_steps
        merged_data["business_rules"] = merged_rules
        merged_data["calculations"] = merged_calculations
        merged_data["ambiguities"] = merged_ambiguities

        merged_jargon: List[str] = []
        for item in usable:
            merged_jargon.extend(item.jargon_flags or [])
        merged_jargon = _dedup_preserve_order(merged_jargon)

        merged_warnings: List[str] = []
        for item in usable:
            merged_warnings.extend(item.guardrail_warnings or [])
        merged_warnings = _dedup_preserve_order(merged_warnings)
        merged_warnings.append(
            f"Synthesized in {len(usable)} section(s) aligned to extraction chunk "
            "boundaries because the object exceeded the single-call output-token "
            "ceiling; sections were merged into this report."
        )
        if dropped_degenerate:
            merged_warnings.append(
                "One or more sections produced text with signs of "
                "repetition-degeneration (a long run of the same short token "
                "repeated verbatim, typical of a model running out of output "
                "budget) and were dropped rather than included in the report."
            )

        merged_parse_error = "; ".join(
            _dedup_preserve_order([item.parse_error for item in usable if item.parse_error])
        )

        return SynthesisResult(
            data=merged_data,
            raw_response=json.dumps(merged_data, separators=(",", ":"), default=str),
            parse_error=merged_parse_error,
            jargon_flags=merged_jargon,
            guardrail_warnings=merged_warnings,
            truncated=any(item.truncated for item in usable),
        )

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
            source_name=object_name,
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
        elif error:
            # Malformed JSON with `finish_reason != "length"` means the model
            # reported it finished normally - it just produced an invalid
            # formatting slip, not a token-budget problem, so retrying with a
            # larger ceiling (as the truncated branch above does) would ask
            # for the same room the model already had. Before this, ANY
            # non-truncated parse failure returned immediately with zero
            # rules for the whole call - on a small/weak model (e.g. Amazon
            # Nova Lite) this silently dropped entire sections' worth of
            # business rules, including this codebase's own SMA_CLASS/
            # SMA_REASON classification section on PRO.SMA_MARKING. One
            # bounded retry of the identical request gives the model a
            # second, independent attempt at valid JSON before giving up.
            retry = self._retry_same_request(completion_kwargs, telemetry_tracker)
            if retry is not None:
                response, raw_response = retry
                finish_reason = str(getattr(response.choices[0], "finish_reason", "") or "").lower()
                truncated = finish_reason == "length"
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
        # Retrying at `self.hard_max_output_tokens` (the real, per-model
        # ceiling) rather than the generic module default: if the failed
        # call already requested the model's true maximum (e.g. 5000 for
        # Amazon Nova Lite), retrying at a larger generic ceiling would just
        # get silently clamped back down to the same 5000 server-side and
        # reproduce the identical truncation - a wasted call that looks like
        # a retry but cannot possibly succeed differently.
        current = int(completion_kwargs.get("max_tokens", 0) or 0)
        ceiling = max(current, self.hard_max_output_tokens)
        if ceiling <= current:
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

    def _retry_same_request(self, completion_kwargs: Dict[str, Any], tracker) -> Optional[Tuple[Any, str]]:
        """One bounded retry of the identical request, for a non-truncated
        malformed-JSON response (see the `synthesize()` call site). Unlike
        `_retry_with_ceiling`, `max_tokens` is unchanged - the first call
        wasn't cut off, so a larger ceiling has no bearing on whether the
        second attempt comes back valid.
        """
        response = None
        start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(**completion_kwargs)
            return response, response.choices[0].message.content or ""
        finally:
            if tracker is not None:
                try:
                    tracker.record_call(
                        stage="synthesis_retry",
                        provider=self.provider,
                        model_name=completion_kwargs.get("model", self.model),
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
            source_name=object_name,
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
        source_name: str = "",
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
        dependency_graph = merged_extraction.get("statement_dependencies") or {}
        if isinstance(dependency_graph, dict):
            payload["statement_dependencies"] = {
                "version": dependency_graph.get("version", "1"),
                "edges": dependency_graph.get("edges", []) or [],
            }
        payload["decision_chain_evidence_map"] = RuleSynthesizerAgent._build_decision_chain_evidence_map(
            merged_extraction.get("decision_chains", []) or [],
            source_name=source_name,
        )
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
            payload["source_sql"] = executable_sql(raw_source)
        return payload

    @staticmethod
    def _compact_evidence_text(value: Any, limit: int = _SYNTHESIS_EVIDENCE_TEXT_MAX_CHARS) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= limit:
            return text
        return text[: max(1, limit - 3)].rstrip() + "..."

    @staticmethod
    def _compact_evidence_location(item: Dict[str, Any]) -> Dict[str, Any]:
        spans = [span for span in item.get("evidence_spans", []) or [] if isinstance(span, dict)]
        line_start = item.get("source_line_start", -1)
        line_end = item.get("source_line_end", -1)
        char_start = item.get("source_char_start", -1)
        char_end = item.get("source_char_end", -1)
        if spans:
            line_values = [span.get("line_start", -1) for span in spans if span.get("line_start", -1) >= 0]
            line_ends = [span.get("line_end", -1) for span in spans if span.get("line_end", -1) >= 0]
            char_values = [span.get("char_start", -1) for span in spans if span.get("char_start", -1) >= 0]
            char_ends = [span.get("char_end", -1) for span in spans if span.get("char_end", -1) >= 0]
            if line_start in (None, -1) and line_values:
                line_start = min(line_values)
            if line_end in (None, -1) and line_ends:
                line_end = max(line_ends)
            if char_start in (None, -1) and char_values:
                char_start = min(char_values)
            if char_end in (None, -1) and char_ends:
                char_end = max(char_ends)
        location: Dict[str, Any] = {}
        if isinstance(line_start, int) and isinstance(line_end, int) and line_start >= 0 and line_end >= 0:
            location["lines"] = f"{line_start}-{line_end}"
        if isinstance(char_start, int) and isinstance(char_end, int) and char_start >= 0 and char_end >= 0:
            location["chars"] = f"{char_start}-{char_end}"
        return location

    @staticmethod
    def _build_decision_chain_evidence_map(
        chains: Any,
        source_name: str = "",
    ) -> Dict[str, Any]:
        """Build a bounded, deterministic branch evidence view for synthesis.

        This is deliberately a data summary, not a second extraction model:
        it preserves branch order, source anchors, affected fields, and parse
        risk while excluding arbitrary provenance payloads and raw SQL text.
        """
        if not isinstance(chains, list):
            chains = []
        compact_chains: List[Dict[str, Any]] = []
        for chain_index, chain in enumerate(chains):
            if not isinstance(chain, dict):
                continue
            branches = chain.get("branches") or []
            if not isinstance(branches, list):
                branches = []
            chain_fields: List[str] = []
            chain_statement_ids: List[str] = []
            compact_branches: List[Dict[str, Any]] = []
            for branch_index, branch in enumerate(branches):
                if not isinstance(branch, dict):
                    continue
                assignments = branch.get("assignments") or []
                if not isinstance(assignments, list):
                    assignments = []
                outcomes: List[Dict[str, str]] = []
                branch_fields: List[str] = []
                statement_ids: List[str] = []
                for assignment in assignments:
                    if not isinstance(assignment, dict):
                        continue
                    field_name = str(assignment.get("field") or "").strip()
                    value = str(assignment.get("value") or "").strip()
                    if field_name:
                        branch_fields.append(field_name)
                        outcomes.append({
                            "field": RuleSynthesizerAgent._compact_evidence_text(field_name),
                            "value": RuleSynthesizerAgent._compact_evidence_text(value),
                        })
                spans = [span for span in branch.get("evidence_spans", []) or [] if isinstance(span, dict)]
                for candidate in [branch, *spans]:
                    statement_id = str(
                        candidate.get("source_statement_id")
                        or candidate.get("statement_id")
                        or ""
                    ).strip()
                    if statement_id and statement_id not in statement_ids:
                        statement_ids.append(statement_id)
                for field_name in branch_fields:
                    if field_name not in chain_fields:
                        chain_fields.append(field_name)
                for statement_id in statement_ids:
                    if statement_id not in chain_statement_ids:
                        chain_statement_ids.append(statement_id)
                branch_item: Dict[str, Any] = {
                    "branch": branch.get("branch_id") or f"branch_{branch_index + 1:03d}",
                    "condition": RuleSynthesizerAgent._compact_evidence_text(
                        branch.get("branch_condition") or branch.get("condition") or ""
                    ),
                    "fallback": bool(branch.get("is_catch_all"))
                    or str(branch.get("branch_condition") or "").strip().upper() in {"ELSE", "OTHERWISE"},
                    "outcomes": outcomes,
                    "fields": branch_fields,
                    "statement_ids": statement_ids,
                }
                location = RuleSynthesizerAgent._compact_evidence_location(branch)
                if location:
                    branch_item["location"] = location
                compact_branches.append(branch_item)

            status = str(
                chain.get("parse_status")
                or chain.get("status")
                or ("unsupported" if chain.get("unsupported") else "parsed")
            ).strip().lower()
            unresolved = []
            for key in ("unresolved", "unresolved_fragments", "ambiguities", "parse_warnings", "unsupported_constructs"):
                values = chain.get(key) or []
                if isinstance(values, str):
                    values = [values]
                if isinstance(values, list):
                    unresolved.extend(
                        RuleSynthesizerAgent._compact_evidence_text(value)
                        for value in values
                        if str(value or "").strip()
                    )
            chain_item: Dict[str, Any] = {
                "chain": chain.get("chain_id") or f"decision_chain_{chain_index + 1:03d}",
                "source": RuleSynthesizerAgent._compact_evidence_text(
                    chain.get("source_identifier") or chain.get("source_file") or source_name
                ),
                "type": RuleSynthesizerAgent._compact_evidence_text(chain.get("chain_type") or ""),
                "branches": compact_branches,
                "affected_fields": chain_fields,
                "statement_ids": chain_statement_ids,
                "parse_status": status or "unresolved",
            }
            chain_location = RuleSynthesizerAgent._compact_evidence_location(chain)
            if chain_location:
                chain_item["location"] = chain_location
            if unresolved:
                chain_item["unresolved"] = list(dict.fromkeys(unresolved))
            compact_chains.append(chain_item)

        evidence_map: Dict[str, Any] = {
            "format": "decision_chain_evidence_v1",
            "chains": compact_chains,
        }
        serialized = json.dumps(evidence_map, separators=(",", ":"), ensure_ascii=True, default=str)
        if len(serialized) <= _SYNTHESIS_EVIDENCE_MAP_MAX_CHARS:
            return evidence_map

        # Keep every branch anchor but drop optional detail first. This makes
        # the bound predictable for unusually large procedures without
        # silently pretending omitted provenance was unavailable.
        for chain_item in compact_chains:
            chain_item.pop("unresolved", None)
            chain_item.pop("statement_ids", None)
            for branch_item in chain_item.get("branches", []):
                branch_item.pop("outcomes", None)
                branch_item.pop("statement_ids", None)
                branch_item["bounded_detail"] = True
        evidence_map["bounded"] = True
        evidence_map["bound_chars"] = _SYNTHESIS_EVIDENCE_MAP_MAX_CHARS
        total_chain_count = len(compact_chains)
        total_branch_count = sum(len(item.get("branches", [])) for item in compact_chains)
        omitted_branch_count = 0
        while (
            len(json.dumps(evidence_map, separators=(",", ":"), ensure_ascii=True, default=str))
            > _SYNTHESIS_EVIDENCE_MAP_MAX_CHARS
            and evidence_map["chains"]
        ):
            last_chain = evidence_map["chains"][-1]
            if last_chain.get("branches"):
                last_chain["branches"].pop()
                omitted_branch_count += 1
            else:
                omitted_branch_count += len(last_chain.get("branches", []))
                evidence_map["chains"].pop()
        if len(evidence_map["chains"]) < total_chain_count:
            evidence_map["omitted_chain_count"] = total_chain_count - len(evidence_map["chains"])
        if omitted_branch_count:
            evidence_map["omitted_branch_count"] = omitted_branch_count
        if total_branch_count == 0 and len(evidence_map["chains"]) < total_chain_count:
            evidence_map["omitted_branch_count"] = 0
        return evidence_map

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

        The one exception is `decision_logic_rows`: when the model returns a
        rule with an empty decision table, `_backfill_decision_logic_rows`
        fills it in from `technical_context["decision_chains"]` -
        deterministic, source-derived branch evidence extracted by
        `pipeline._extract_deterministic_decision_chains` before synthesis
        ever runs (see that function's docstring). This is a backfill of a
        *representation* the model already reasoned about (it authored the
        rule's `condition`/`action` text describing the same ladder), not an
        invented fact: a small/rate-limited completion budget (e.g. Amazon
        Nova Lite's real 5000-token cap - see `resolve_model_output_ceiling`
        in `llm_client.py`) can leave no room for the model to also spell out
        every branch as structured rows, especially once large objects are
        synthesized section-by-section and each section's budget shrinks
        further. Without this, every multi-branch classification rule (SMA
        class thresholds, SMA reason precedence, etc.) silently loses its
        "Decision Logic" table in the final report even though the source
        evidence for it was extracted and available the whole time.
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

        decision_chains: List[Dict[str, Any]] = []
        if isinstance(technical_context, dict):
            raw_chains = technical_context.get("decision_chains")
            if isinstance(raw_chains, list):
                decision_chains = [chain for chain in raw_chains if isinstance(chain, dict)]

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
            if not rule["decision_logic_rows"] and decision_chains:
                rule["decision_logic_rows"] = RuleSynthesizerAgent._backfill_decision_logic_rows(
                    rule, decision_chains
                )
            for key in ("rule_type", "confidence", "validation_status", "rule_id", "ambiguity_id"):
                value = rule.get(key, "")
                rule[key] = value if isinstance(value, str) else ("" if value is None else str(value))
            normalized.append(rule)
        return normalized

    @staticmethod
    def _backfill_decision_logic_rows(
        rule: Dict[str, Any], decision_chains: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Reconstruct `decision_logic_rows` for one rule from deterministic
        decision-chain evidence, matched by the rule's own `output_field`.

        A decision chain's branches carry `assignments` of `{field, value}`
        pairs (one multi-branch ladder can assign several output fields at
        once - e.g. SMA_CLASS and SMA_REASON from the same CASE ladder). Only
        the branches that actually assign *this* rule's output field are
        used, so a rule for one field never picks up rows that describe a
        different field's outcomes from the same chain. A single matching
        branch is not a decision table (nothing to choose between), so a
        chain contributes rows only when it yields at least two.
        """
        output_field = str(rule.get("output_field") or "").strip()
        if not output_field:
            return []
        output_field_key = output_field.lower()
        matching_chains = [
            chain for chain in decision_chains
            if any(str(a.get("field") or "").strip().lower() == output_field_key
                   for branch in (chain.get("branches") or [])
                   for a in (branch.get("assignments") or []) if isinstance(a, dict))
        ]
        if len(matching_chains) != 1:
            return []
        # An unconditional reset is not the later classification ladder.
        if re.search(r"\b(reset|initialize|initialise|clear)\b", str(rule.get("rule_name") or ""), re.I):
            return []

        for chain in decision_chains:
            branches = chain.get("branches")
            if not isinstance(branches, list):
                continue
            rows: List[Dict[str, Any]] = []
            for branch in branches:
                if not isinstance(branch, dict):
                    continue
                assignments = branch.get("assignments")
                if not isinstance(assignments, list):
                    continue
                match = next(
                    (
                        assignment
                        for assignment in assignments
                        if isinstance(assignment, dict)
                        # Case-insensitive: the model's own `output_field`
                        # text ("SMA_Class") does not always match the
                        # deterministic extractor's literal source casing
                        # ("SMA_CLASS") verbatim, and a strict `==` here
                        # silently drops the backfill for an otherwise
                        # perfectly matched field.
                        and str(assignment.get("field") or "").strip().lower() == output_field_key
                    ),
                    None,
                )
                if match is None:
                    continue
                condition = (
                    "ELSE"
                    if branch.get("is_catch_all")
                    else str(branch.get("branch_condition") or "").strip()
                )
                rows.append({"condition": condition, "outcome": str(match.get("value") or "").strip()})
            if len(rows) >= 2:
                return rows
        return []

    @staticmethod
    def ensure_decision_chain_coverage(
        rules: List[Dict[str, Any]], decision_chains: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Guarantee a Decision Logic table for every deterministic
        multi-branch decision chain found in the source, independent of
        whether the model produced a matching rule for it.

        `_backfill_decision_logic_rows` (used inside `_normalize_business_rules`)
        fills in `decision_logic_rows` on a rule the model already authored,
        matched by that rule's own `output_field` - but it has nothing to
        attach to when the model never produced a rule for a field at all.
        That happens more than it should on a small/weak model under a tight
        completion budget: a whole section's response fails to parse, a
        field gets folded into a different rule's prose instead of standing
        on its own, or the model simply omits it on a given run. Call this as
        the final step, once, after synthesis and every coverage-gap review
        pass are done: any chain still missing its own table at that point
        gets one synthesized directly from the same deterministic source
        evidence the backfill uses - no LLM call, so it cannot fail to
        parse, omit a branch, or vary from run to run. This is the
        guarantee, not the best-effort: every real multi-branch CASE/IF
        ladder in the source ends up with a rendered Decision Logic table.

        Coverage is judged per CHAIN, by whether an existing rule's table
        already represents its actual branch conditions - never by output
        field name alone. A source can legitimately contain two independent
        decision chains that assign the *same* field for entirely different
        reasons (e.g. PRO.SMA_MARKING has both a DPD-threshold ladder
        assigning SMA_CLASS and a separate, unrelated CASE mapping
        SMA_CLASS text to an integer rank for aggregation) - "the field
        already has a table" would incorrectly skip the second one, silently
        dropping a real business rule the source actually contains.
        """
        if not decision_chains:
            return rules

        def _field_key(value: Any) -> str:
            return str(value or "").strip().lower()

        def _normalized_condition(value: Any) -> str:
            from src.parsing.decision_identity import decision_text_key
            return decision_text_key(value)

        def _rows_key(rows: List[Dict[str, Any]]) -> list:
            return [
                (_normalized_condition(row.get("condition")),
                 _normalized_condition(row.get("outcome")))
                for row in rows if isinstance(row, dict)
            ]

        def _field_is_covered(chain: Dict[str, Any], field_key: str, rows: List[Dict[str, Any]]) -> bool:
            expected = _rows_key(rows)
            for rule in rules:
                if _field_key(rule.get("output_field")) != field_key:
                    continue
                source_chain = rule.get("source_chain_id")
                if source_chain and source_chain != chain.get("chain_id"):
                    continue
                if expected and expected == _rows_key(rule.get("decision_logic_rows") or []):
                    return True
            return False

        synthetic_rules: List[Dict[str, Any]] = []
        for chain in decision_chains:
            if not isinstance(chain, dict):
                continue
            branches = chain.get("branches")
            if not isinstance(branches, list):
                continue

            fields_in_chain: "OrderedDict[str, str]" = OrderedDict()
            for branch in branches:
                if not isinstance(branch, dict):
                    continue
                for assignment in branch.get("assignments") or []:
                    if not isinstance(assignment, dict):
                        continue
                    field = str(assignment.get("field") or "").strip()
                    if field:
                        fields_in_chain.setdefault(_field_key(field), field)

            for field_key, display_field in fields_in_chain.items():
                rows: List[Dict[str, Any]] = []
                for branch in branches:
                    if not isinstance(branch, dict):
                        continue
                    match = next(
                        (
                            assignment
                            for assignment in (branch.get("assignments") or [])
                            if isinstance(assignment, dict)
                            and _field_key(assignment.get("field")) == field_key
                        ),
                        None,
                    )
                    if match is None:
                        continue
                    condition = (
                        "ELSE"
                        if branch.get("is_catch_all")
                        else str(branch.get("branch_condition") or "").strip()
                    )
                    rows.append({"condition": condition, "outcome": str(match.get("value") or "").strip()})
                if len(rows) < 2 or _field_is_covered(chain, field_key, rows):
                    continue
                synthetic_rules.append({
                    "rule_id": f"deterministic_{chain.get('chain_id') or 'chain'}_{field_key}",
                    "source_chain_id": str(chain.get("chain_id") or ""),
                    "decision_role": str(chain.get("decision_role") or "assignment"),
                    "rule_name": (f"Determine inputs to {chain['aggregation']} for {display_field}"
                                  if chain.get("aggregation") else f"Determine {display_field}"),
                    "business_meaning": (
                        f"The decision rows show per-row inputs to {chain['aggregation']}; "
                        f"{display_field} is the aggregate of those inputs over the SQL grouping."
                        if chain.get("aggregation") else str(chain.get("execution_semantics") or "")
                    ),
                    "condition": "",
                    "action": (
                        f"Sets {display_field} based on the decision logic below, "
                        "reconstructed directly from the source's branching logic."
                    ),
                    "output_field": display_field,
                    "eligibility": list(chain.get("eligibility") or []),
                    "decision_context": list(chain.get("decision_context") or []),
                    "execution_semantics": str(chain.get("execution_semantics") or ""),
                    "decision_logic": [],
                    "tie_priority_handling": [],
                    "default": [],
                    "when_not_eligible": [],
                    "fields_affected": [display_field],
                    "source_evidence": [],
                    "source_chunks": [],
                    "technical_references": [],
                    "unresolved_ambiguities": [],
                    "dependencies": [],
                    "decision_logic_rows": rows,
                    "rule_type": "deterministic_decision_table",
                    "confidence": "deterministic",
                    "validation_status": "",
                    "ambiguity_id": "",
                })
        return rules + synthetic_rules

    @staticmethod
    def _scan_for_jargon(data: Dict[str, Any]) -> List[str]:
        flat_text = json.dumps(data).lower()
        return [term for term in _BANNED_TERMS if term in flat_text]