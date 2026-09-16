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
from src.parsing import alias_resolution as _alias_resolution
from src.ir.rule_identity import unique_rule_ids

import json
import logging
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple
from typing import Optional

from src.ingestion.guardrails import ground_business_rules_against_extraction, validate_synthesis_shape
from src.core.llm_client import (
    supports_chat_completion_seed,
    estimate_prompt_tokens,
    resolve_tpm_limit,
    clamp_tokens_for_tpm,
)
from src.core.pipeline_utils import PIPELINE_VERSION, stable_id
from src.core.llm_response_cache import PersistentLLMResponseCache
from src.parsing.dedup import dedup_table_operations
from src.prompts.prompt_loader import get_prompt_set, render_user_prompt
from src.telemetry.tracker import LLMTelemetryTracker
from src.validation.coverage_check import find_decision_points
from src.validation.coverage_check import _group_lines as _group_decision_point_lines

logger = logging.getLogger(__name__)


def rule_identity_key(rule: Dict[str, Any]) -> Tuple[str, ...]:
    """Stable identity for a business rule, ignoring volatile fields.

    Two rule dicts with the same identity are the same rule as far as this
    pipeline is concerned - same business meaning, same evidence, same
    everything except `rule_id`/`original_rule_id` (regenerated per call).
    Used both to dedupe genuine duplicates across sectioned synthesis calls
    (`merge_section_results`) and, in `pipeline.py`'s coverage-gap revision
    loop, to tell an already-accepted rule the model merely echoed back
    unchanged apart from a truly NEW rule the same call also introduced -
    only the latter is the actual product of "the model had to look again."
    """
    return (
        str(rule.get("rule_name") or "").strip(),
        str(rule.get("condition") or "").strip(),
        str(rule.get("action") or "").strip(),
        str(rule.get("output_field") or "").strip(),
        json.dumps(
            {
                key: value for key, value in rule.items()
                if key not in {
                    "rule_id", "original_rule_id", "rule_name", "condition",
                    "action", "output_field", "degraded", "degraded_reason",
                }
            },
            sort_keys=True, default=str,
        ),
    )

_EMPTY_SYNTHESIS: Dict[str, Any] = {
    "purpose_summary": "",
    "step_by_step_flow": [],
    "business_rules": [],
    "calculations": [],
    "exception_handling_summary": "",
    "ambiguities": [],
}


class PromptTooLargeForRateLimitError(RuntimeError):
    """Raised when a synthesis call's estimated prompt tokens alone (system
    prompt + rendered payload) leave no room for even the minimum useful
    completion under the account's configured `LLM_TPM_LIMIT`.

    This fires BEFORE the request is sent - it replaces a guaranteed
    provider-side 413 with an actionable message naming what to change.
    Unlike `revise()` (which can skip a gap-review pass and leave the gap
    flagged for human review), `synthesize()` has no equivalent fallback -
    skipping it silently would produce zero rules for the whole section -
    so this raises instead of returning an empty result.
    """

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
    # True exactly when this synthesis call (single-call or one section of
    # a sectioned run) raised and the pipeline degraded it to an empty
    # result to keep the run alive, mirroring `ChunkExtraction.llm_call_failed`.
    synthesis_failed: bool = False


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

# Deliberately conservative, deliberately NOT dialect-specific estimate of
# the FIXED prompt overhead (system prompt + the surrounding user-template
# skeleton) every synthesis/revision call pays before a single decision
# point's worth of content is added. Used only by `_sectioning_ceiling` to
# decide, before any real prompt is built, whether a section's planned size
# leaves any TPM headroom at all. The real oracle/tsql system prompts
# measure ~3,900-4,500 tokens; this is biased above that on purpose so
# section planning never UNDER-estimates and lets a section through that
# then fails the real per-call TPM guard anyway - see `_sectioning_ceiling`
# for why that failure mode (an entire section's rules silently dropped)
# matters more than a slightly-too-conservative section size.
_FIXED_PROMPT_OVERHEAD_TOKENS_ESTIMATE = 5200

# Local mirror of `src.core.llm_client._TPM_SAFETY_MARGIN` - kept as its own
# constant (not imported) because this one is a section-PLANNING margin,
# conceptually separate from the per-call margin the imported
# `clamp_tokens_for_tpm` applies right before a request is actually sent.
# Both bias toward attempting less, not more, for the same reason.
_TPM_SAFETY_MARGIN = 200


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

    # Matches the deterministic chunk/full-source parse-error housekeeping
    # templates this pipeline itself generates (see `pipeline.py`'s
    # `_merge_extractions`/`_single_pass_extraction_payload`) - not a
    # general "mentions malformed JSON" filter, so a genuine model-authored
    # ambiguity about validation/parsing elsewhere in the source is never
    # caught by this.
    _PARSE_ERROR_HOUSEKEEPING_RE = re.compile(
        r"malformed json.{0,40}(needs? (manual )?review|need(s)? manual review)", re.IGNORECASE
    )

    @staticmethod
    def _is_parse_error_housekeeping_ambiguity(text: Any) -> bool:
        return bool(isinstance(text, str) and RuleSynthesizerAgent._PARSE_ERROR_HOUSEKEEPING_RE.search(text))

    _STEP_WORD_RE = re.compile(r"[A-Za-z0-9_]+")

    @classmethod
    def _drop_near_duplicate_steps(cls, steps: List[str]) -> List[str]:
        """Drop a step_by_step_flow entry that near-restates an
        already-kept one, catching a paraphrase exact-text dedup misses
        (e.g. two sections each independently describing the same MERGE
        statement in slightly different words). A step is dropped only
        when its own content-word set overlaps an already-kept step's by
        80% or more of its smaller side (i.e. it is essentially the same
        step, not merely on a related topic), and only once it has at
        least 4 content words - short steps are common and legitimately
        similar-looking ("Commit the transaction.") without being
        duplicates of each other.
        """
        kept: List[str] = []
        kept_word_sets: List["set[str]"] = []
        for step in steps:
            words = {w.lower() for w in cls._STEP_WORD_RE.findall(step)}
            is_near_duplicate = False
            if len(words) >= 4:
                for kept_words in kept_word_sets:
                    smaller = min(len(words), len(kept_words))
                    if smaller and len(words & kept_words) / smaller >= 0.8:
                        is_near_duplicate = True
                        break
            if is_near_duplicate:
                continue
            kept.append(step)
            kept_word_sets.append(words)
        return kept

    @staticmethod
    def _clean_ambiguities(data: Dict[str, Any]) -> bool:
        """Drop degenerate-repetition and truncated-fragment garbage from
        `data["ambiguities"]` in place (same screen `merge_section_results`
        applies across sections, applied here to a single call's own
        response so a single-pass/cache-hit/revision result gets the same
        protection). Returns True if anything was dropped.
        """
        raw = data.get("ambiguities")
        if not isinstance(raw, list) or not raw:
            return False
        cleaned: List[str] = []
        dropped = False
        for value in raw:
            text = str(value)
            if not text.strip():
                continue
            if RuleSynthesizerAgent._is_degenerate_text(text) or RuleSynthesizerAgent._looks_truncated(text):
                dropped = True
                continue
            cleaned.append(text)
        data["ambiguities"] = cleaned
        return dropped

    # A truncated array item (the JSON cut off mid-string, e.g. finish_reason
    # == "length" landing inside an "ambiguities" entry) does not always fail
    # `_recover_partial_json`'s per-item `raw_decode` cleanly in every
    # position - an odd number of unescaped quote characters is a cheap,
    # reliable sign the string itself is an incomplete fragment rather than
    # a real, closed sentence (observed for real: "Chunk '00_main_body"
    # reaching the final report with no closing quote and no rest of the
    # sentence).
    @staticmethod
    def _looks_truncated(text: Any) -> bool:
        if not isinstance(text, str) or not text:
            return False
        stripped = text.strip()
        if not stripped:
            return False
        if stripped.count("'") % 2 == 1 or stripped.count('"') % 2 == 1:
            return True
        # A short fragment with no sentence-ending punctuation and no
        # trailing closing bracket/quote reads as cut off mid-thought.
        if len(stripped) <= 40 and stripped[-1] not in ".!?)]}'\"" and " " in stripped:
            return True
        return False

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

    def _sectioning_ceiling(self) -> int:
        """The effective output-token ceiling to plan SECTION SIZES
        against - deliberately NOT the same thing as `self.hard_max_output_tokens`
        (the model's raw completion capability).

        A rate-limited account's real per-call budget can be far smaller
        than the model's raw capability. Groq's free `openai/gpt-oss-120b`
        tier caps a whole call (prompt + completion) at 8,000 tokens even
        though the model itself can emit up to 65,536 completion tokens on
        a higher tier. If sectioning decisions
        (`requires_sectioned_synthesis`, `plan_synthesis_sections`) are
        planned against the model's raw capability instead of the
        account's real ceiling, a section gets built that will never fit
        once its prompt is assembled - and the caller's per-section
        try/except (`pipeline.py::_run_section`) then silently drops that
        ENTIRE section's rules rather than the object ever being split any
        finer.

        This is not hypothetical: a small (176-line, 55-decision-point)
        object comfortably fits under a model's raw 65,536-token ceiling
        in a single pass, so `requires_sectioned_synthesis` reported "no
        sectioning needed" and one single-pass call was attempted - but
        that object does NOT fit under an 8,000 TPM account ceiling once
        the ~4,000-4,500 token system prompt is accounted for. The
        pre-flight TPM guard correctly refused that oversized call, and
        the whole object came back with zero synthesized rules instead of
        the several smaller, successful calls it should have become.

        Only ever used for SECTION SIZING (deciding how much content one
        section may carry) - never for the real per-call `max_tokens` sent
        to the API (`_output_token_budget`, itself further clamped by the
        same TPM guard immediately before each call) and never for
        truncation-retry escalation (which legitimately wants the model's
        true capability, since a retry there responds to an
        already-truncated REAL response, not a preflight estimate).
        """
        tpm_limit = resolve_tpm_limit(self.provider)
        if tpm_limit is None:
            return self.hard_max_output_tokens
        available = tpm_limit - _FIXED_PROMPT_OVERHEAD_TOKENS_ESTIMATE - _TPM_SAFETY_MARGIN
        return max(_PER_DECISION_POINT_TOKENS, min(self.hard_max_output_tokens, available))

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
        return self._estimate_output_tokens(raw_source, requested) > self._sectioning_ceiling()

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
        sectioning_ceiling = self._sectioning_ceiling()
        section_overhead = min(base, sectioning_ceiling // 2)
        section_token_budget = max(_PER_DECISION_POINT_TOKENS, sectioning_ceiling - section_overhead)
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

            if chunk_points > section_point_budget:
                # This single chunk alone already needs more decision-point
                # budget than any section may have - grouping can't help
                # (grouping only ever adds MORE points to a section), and
                # every other chunk in this object is irrelevant to fixing
                # it. This is the real-world failure mode behind most
                # "Needs Review" rules on live runs against small-ceiling
                # models: a stored procedure whose entire body is one long,
                # un-nested run of sibling UPDATE/IF/CASE statements (no
                # BEGIN...END for the extraction stage to split on) becomes
                # one chunk with dozens of decision points, which used to
                # become one section guaranteed to blow the output-token
                # ceiling no matter what. Flush whatever was accumulating,
                # sub-split this one chunk on its own, then resume grouping
                # fresh from the next chunk.
                _flush()
                current_ids, current_start, current_end = [], None, None
                current_points, current_chars = 0, 0
                sections.extend(
                    self._split_oversized_chunk_into_sections(
                        chunk_id, chunk_text, char_start, char_end, section_point_budget
                    )
                )
                continue

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
    def _split_oversized_chunk_into_sections(
        chunk_id: Any,
        chunk_text: str,
        char_start: Any,
        char_end: Any,
        section_point_budget: int,
    ) -> List[Dict[str, Any]]:
        """Break one chunk whose own decision-point count exceeds
        `section_point_budget` into multiple synthesis sections.

        Splits only ever fall between decision-point clusters - lines
        grouped the same way `coverage_check._group_lines` groups citation
        evidence for coverage checking - never inside one, so a single
        CASE/IF statement's branches always stay together in one call.
        Every returned section repeats `chunk_id` in `chunk_ids`: the same
        chunk-level extraction evidence (already only chunk-granular, not
        statement-granular, everywhere else in this pipeline) is handed to
        each sub-slice, and `merge_section_results`'s existing rule-identity
        dedup collapses any resulting overlap between adjacent sub-slices.
        Each section carries an explicit `text_override` with its own exact
        slice of `chunk_text`, so `_run_rule_synthesis` never has to rely on
        (possibly unavailable, see `CodeChunk.source_char_start/end`)
        absolute source offsets to use it.
        """
        has_offset = isinstance(char_start, int) and char_start >= 0
        points = find_decision_points(chunk_text)
        point_lines = sorted({int(p["line"]) for p in points if isinstance(p, dict) and "line" in p})
        if not point_lines:
            return [{
                "chunk_ids": [chunk_id],
                "char_start": char_start if has_offset else None,
                "char_end": char_end if isinstance(char_end, int) and char_end >= 0 else None,
                "text_override": chunk_text,
            }]

        groups = _group_decision_point_lines(point_lines)
        lines = chunk_text.splitlines(keepends=True)
        line_char_offsets = [0]
        for line in lines:
            line_char_offsets.append(line_char_offsets[-1] + len(line))

        def _chars_for_line_range(start_line: int, end_line: int) -> Tuple[int, int]:
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), end_line)
            return line_char_offsets[start_idx], line_char_offsets[end_idx]

        sub_sections: List[Dict[str, Any]] = []
        group_start_line = 1
        accumulated_points = 0
        pending = False
        last_group_end_line = 0

        def _flush_pending(end_line: int) -> None:
            rel_start, rel_end = _chars_for_line_range(group_start_line, end_line)
            text_slice = chunk_text[rel_start:rel_end]
            if not text_slice.strip():
                return
            sub_sections.append({
                "chunk_ids": [chunk_id],
                "char_start": char_start + rel_start if has_offset else None,
                "char_end": char_start + rel_end if has_offset else None,
                "text_override": text_slice,
            })

        for group in groups:
            group_points = len(group)
            if pending and accumulated_points + group_points > section_point_budget:
                _flush_pending(last_group_end_line)
                group_start_line = last_group_end_line + 1
                accumulated_points = 0
                pending = False
            pending = True
            accumulated_points += group_points
            last_group_end_line = group[-1]
        _flush_pending(len(lines))

        return sub_sections or [{
            "chunk_ids": [chunk_id],
            "char_start": char_start if has_offset else None,
            "char_end": char_end if isinstance(char_end, int) and char_end >= 0 else None,
            "text_override": chunk_text,
        }]

    @staticmethod
    def _merge_scoped_written_tables(
        merged_extraction: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Bare (lowercased) written-table name -> original-casing display
        name, for every table `tables_written` reports - excluding process
        bookkeeping tables (same `runningprocessstatus`-name signal
        `_remove_operational_status_rules` uses), since a purpose summary
        is never expected to mention audit/status plumbing.
        """
        if not isinstance(merged_extraction, dict):
            return {}
        status_tables = {
            str(row.get("table") or "").strip().split(".")[-1].strip("#").casefold()
            for row in merged_extraction.get("table_operations", []) or []
            if isinstance(row, dict)
            and "runningprocessstatus" in str(row.get("table") or "").lower()
        }
        display_by_bare: Dict[str, str] = {}
        for row in merged_extraction.get("tables_written", []) or []:
            if not isinstance(row, dict):
                continue
            table = str(row.get("table") or "").strip()
            if not table:
                continue
            bare_key = table.split(".")[-1].strip("#").casefold()
            if not bare_key or bare_key in status_tables:
                continue
            display_by_bare.setdefault(bare_key, table.split(".")[-1].strip("#"))
        return display_by_bare

    @staticmethod
    def merge_section_results(
        results: Sequence["SynthesisResult"],
        merged_extraction: Optional[Dict[str, Any]] = None,
    ) -> "SynthesisResult":
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

        # Each section is synthesized with the *same* whole-object prompt
        # (`purpose_summary` asks for "the purpose of this procedure", not
        # "the purpose of this slice"), so every section independently
        # writes its own full-procedure summary from whatever partial
        # evidence it was scoped to - producing several genuinely different
        # *paraphrases* of the same one-sentence idea, not several distinct
        # ideas. Exact-string dedup does not catch paraphrases, so joining
        # every section's attempt produced 2-3 near-duplicate paragraphs
        # under "What This Does" in a live report. `purpose_summary` is a
        # single holistic field, not a per-section-contributed list like
        # `business_rules`, so the correct merge is to keep the single most
        # complete attempt - not simply the longest text (a section can pad
        # its own single-table guess with verbose phrasing and still say
        # less than a shorter, more complete attempt), but the one that
        # actually names the most of the object's real written tables,
        # tie-broken by length as before.
        purpose_summaries = [str(item.data.get("purpose_summary") or "").strip() for item in usable]
        known_written_tables = RuleSynthesizerAgent._merge_scoped_written_tables(merged_extraction)

        def _table_coverage_score(text: str) -> int:
            if not known_written_tables:
                return 0
            lowered = text.casefold()
            return sum(1 for bare in known_written_tables if bare and bare in lowered)

        purpose_candidates = [text for text in purpose_summaries if text]
        merged_purpose = max(
            purpose_candidates, key=lambda text: (_table_coverage_score(text), len(text)), default=""
        )
        if merged_purpose and known_written_tables:
            lowered_purpose = merged_purpose.casefold()
            missing_display = [
                display for bare, display in known_written_tables.items()
                if bare not in lowered_purpose
            ]
            # Only append when the winning summary still misses MORE than
            # half of what the object actually writes to - a summary that
            # already covers most tables doesn't need a bolted-on sentence,
            # and this never invents anything beyond table names the
            # deterministic extraction itself already reported.
            if len(missing_display) > len(known_written_tables) / 2:
                merged_purpose = (
                    f"{merged_purpose} This procedure also writes to: "
                    f"{', '.join(sorted(missing_display))}."
                )

        exception_summaries = [
            str(item.data.get("exception_handling_summary") or "").strip() for item in usable
        ]
        merged_exception_summary = " ".join(
            _dedup_preserve_order([text for text in exception_summaries if text])
        )

        _rule_identity_key = rule_identity_key

        def _rule_has_degenerate_text(rule: Dict[str, Any]) -> bool:
            return any(
                RuleSynthesizerAgent._is_degenerate_text(rule.get(key))
                for key in ("rule_name", "condition", "action", "business_meaning")
            )

        dropped_degenerate = False

        # Each section is now explicitly told (see `synthesize(...,
        # is_section=True)`) to describe ONLY the steps visible in its own
        # excerpt, in order - not to reconstruct the whole procedure's
        # flow from partial evidence. That single prompt change is what
        # makes concatenation correct here: sections are processed in
        # source order (`plan_synthesis_sections` walks the object's
        # chunks front-to-back), so each section's own steps, appended in
        # that same order, build one genuinely complete flow instead of
        # the old behavior of keeping only the single longest section's
        # own full-procedure guess (which, once an object needed enough
        # sections that no single one ever saw the whole thing - common
        # under a tight per-call token budget - produced a shallow,
        # partial flow no matter how long the "winning" section's guess
        # was). Exact-text dedup still guards against a section
        # accidentally repeating the same step twice within itself.
        merged_steps: List[str] = []
        for item in usable:
            for step in item.data.get("step_by_step_flow") or []:
                step_text = str(step)
                if not step_text.strip():
                    continue
                if RuleSynthesizerAgent._is_degenerate_text(step_text):
                    dropped_degenerate = True
                    continue
                merged_steps.append(step_text)
        merged_steps = _dedup_preserve_order(merged_steps)
        merged_steps = RuleSynthesizerAgent._drop_near_duplicate_steps(merged_steps)

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

        def _calculation_identity_key(calc: Dict[str, Any]) -> Tuple[str, str, str]:
            # Sections independently re-derive a calculation whose source
            # statement they can each see (e.g. a formula near a section
            # boundary), producing near-duplicate expressions that differ
            # only in incidental formatting: one section wraps the formula
            # in an outer `(...)` the other doesn't, or paraphrases
            # `ISNULL(...)` as `COALESCE(...)` (the same null-coalescing
            # function) - a plain string/dict-identity check misses both,
            # which is why "PenalInterestAmount" and "RunCount" were each
            # observed twice in the same live report. Field references
            # inside the expression are also reduced to their bare
            # trailing segment so an alias/schema-qualified restatement of
            # the same formula from a different section still collapses.
            #
            # The *target* is split into (table_part, field_part): two
            # calculations that share an identical formula but write to two
            # different, both-*qualified* tables (e.g. the same
            # `DATEADD(...)` formula for both `AccountHistory.
            # MovementToDate` and `CustomerHistory.MovementToDate`) are
            # genuinely distinct and must not collapse - but one section
            # rendering a bare, unqualified target ("RunCount") for the
            # exact same field another section fully qualified
            # ("PRO.RunStatus.RunCount") is the same field with a missing
            # qualifier, not a different one, so an empty table_part
            # matches any table (see the comparison loop below).
            target = str(
                calc.get("output_field") or calc.get("name") or calc.get("result")
                or calc.get("field") or calc.get("metric") or ""
            )
            target = re.sub(r"\s+", "", target).strip()
            if "." in target:
                table_part, _, field_part = target.rpartition(".")
                table_part, field_part = table_part.casefold(), field_part.casefold()
            else:
                table_part, field_part = "", target.casefold()
            expression = str(calc.get("expression") or calc.get("formula") or "")
            dotted_path = re.compile(r"(?<![A-Za-z0-9_])(?:[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*")
            bare = dotted_path.sub(lambda match: match.group(0).split(".")[-1], expression)
            bare = re.sub(r"(?i)\bISNULL\s*\(", "COALESCE(", bare)
            collapsed = re.sub(r"\s+", " ", bare).strip()
            while len(collapsed) >= 2 and collapsed[0] == "(" and collapsed[-1] == ")":
                depth = 0
                fully_wrapped = True
                for index, char in enumerate(collapsed):
                    if char == "(":
                        depth += 1
                    elif char == ")":
                        depth -= 1
                        if depth == 0 and index != len(collapsed) - 1:
                            fully_wrapped = False
                            break
                if not fully_wrapped:
                    break
                collapsed = collapsed[1:-1].strip()
            return (table_part, field_part, collapsed.casefold())

        def _calculation_matches(known: List[Tuple[str, str, str]], candidate: Tuple[str, str, str]) -> bool:
            table_part, field_part, expression_key = candidate
            for known_table, known_field, known_expression in known:
                if known_expression != expression_key or known_field != field_part:
                    continue
                if known_table and table_part and known_table != table_part:
                    continue
                return True
            return False

        merged_calculations: List[Dict[str, Any]] = []
        seen_calculation_keys: List[Tuple[str, str, str]] = []
        for item in usable:
            for calc in item.data.get("calculations") or []:
                if not isinstance(calc, dict):
                    continue
                key = _calculation_identity_key(calc)
                has_expression = bool(key[2])
                if has_expression and _calculation_matches(seen_calculation_keys, key):
                    continue
                if has_expression:
                    seen_calculation_keys.append(key)
                merged_calculations.append(calc)

        merged_ambiguities: List[str] = []
        for item in usable:
            for value in item.data.get("ambiguities") or []:
                text = str(value)
                if not text.strip():
                    continue
                # Same degenerate-repetition screen already applied to rules
                # and step_by_step_flow, plus a truncation check specific to
                # ambiguities: an unclosed quote or a short fragment with no
                # closing punctuation is a cut-off string, not a genuine
                # finding (observed for real: "Chunk '00_main_body" reaching
                # the report with no closing quote or rest of sentence).
                if RuleSynthesizerAgent._is_degenerate_text(text) or RuleSynthesizerAgent._looks_truncated(text):
                    dropped_degenerate = True
                    continue
                merged_ambiguities.append(text)
        merged_ambiguities = _dedup_preserve_order(merged_ambiguities)

        merged_data: Dict[str, Any] = dict(_EMPTY_SYNTHESIS)
        merged_data["purpose_summary"] = merged_purpose
        merged_data["exception_handling_summary"] = merged_exception_summary
        merged_data["step_by_step_flow"] = merged_steps
        merged_data["business_rules"] = unique_rule_ids(merged_rules)
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
            synthesis_failed=any(item.synthesis_failed for item in usable),
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
        is_section: bool = False,
    ) -> SynthesisResult:
        """`model`, if given, overrides the agent's configured model for
        just this call - lets callers pick a different model per run
        without re-constructing the agent.

        `is_section=True` tells the model this call sees only one excerpt
        of a larger object (see `_run_rule_synthesis`'s sectioned path in
        pipeline.py), not the whole thing. Without this, the prompt (which
        always asks for "the step-by-step flow" with no notion of a
        partial view) led every section to independently attempt a full-
        object flow from whatever fragment it could see - real bug,
        observed on a live report: with an object split into many small
        sections (common once a tight per-call token budget forces fine-
        grained sectioning - see `RuleSynthesizerAgent._sectioning_
        ceiling`), NO single section ever saw enough of the object to
        write a comprehensive flow, and `merge_section_results` keeping
        only the single longest section's attempt meant the final report
        showed a shallow 3-step flow for an 11-step procedure. Telling the
        model explicitly to describe only ITS OWN excerpt's steps, in
        order, is both more accurate (no guessing about invisible
        sections) and enables `merge_section_results` to concatenate every
        section's own steps into one genuinely complete flow instead of
        picking one section's partial guess.
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
        if is_section:
            user_prompt += (
                "\n\nSECTION SCOPE: this call sees only ONE EXCERPT of a "
                "larger object - other sections, not shown to you, cover "
                "the rest of its logic. step_by_step_flow must describe "
                "ONLY the executable stages visible in THIS excerpt, in "
                "the order they appear here - never guess at, invent, or "
                "summarize steps that happen before or after what you can "
                "see; leaving out a step you cannot see is correct, not "
                "incomplete. purpose_summary should still describe the "
                "overall object's business purpose as best it can be "
                "inferred from the object name/type/parameters and this "
                "excerpt together, since other sections will not repeat it."
            )
        effective_seed = self.seed if self.seed is not None and supports_chat_completion_seed(self.client) else None
        effective_max_tokens = self._output_token_budget(raw_source)

        # Pre-flight TPM guard: only active when `LLM_TPM_LIMIT` is set
        # (see `resolve_tpm_limit`'s docstring). A request built against
        # `hard_max_output_tokens` (the model's raw capability) can still
        # be far larger than what a rate-limited account is actually
        # allowed to send in one call - this shrinks `max_tokens` to fit
        # alongside the estimated prompt size, or raises a clear,
        # actionable error instead of letting the provider reject it with
        # a bare 413.
        tpm_limit = resolve_tpm_limit(self.provider)
        if tpm_limit is not None:
            prompt_tokens_estimate = estimate_prompt_tokens(prompt_set["system"], user_prompt)
            clamped = clamp_tokens_for_tpm(prompt_tokens_estimate, effective_max_tokens, tpm_limit)
            if clamped is None:
                raise PromptTooLargeForRateLimitError(
                    f"Synthesis prompt for '{object_name}' is estimated at "
                    f"~{prompt_tokens_estimate} tokens, which leaves no room "
                    f"under LLM_TPM_LIMIT={tpm_limit} even for the smallest "
                    "useful completion. Either raise LLM_TPM_LIMIT to match "
                    "what your account's rate-limit page actually shows, or "
                    "reduce SYNTHESIS_EVIDENCE_MAP_MAX_CHARS / "
                    "SYNTHESIS_SECTION_MAX_CHARS so each synthesis section "
                    "carries less content."
                )
            effective_max_tokens = clamped

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
                    if self._clean_ambiguities(data):
                        guardrail_warnings.append(
                            "One or more ambiguities showed signs of repetition-degeneration "
                            "or mid-sentence truncation and were dropped rather than included "
                            "in the report."
                        )
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
        used_recovery = False
        retried = False
        if truncated and error:
            recovered = self._recover_partial_json(raw_response)
            if recovered is not None:
                data, error = recovered, ""
                used_recovery = True
            else:
                retried = True
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
                            used_recovery = True
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
            retried = True
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
                        used_recovery = True
        if error:
            # Every retry above only re-attempted recovery when `truncated`
            # was set - but `_recover_partial_json` walks the object
            # key-by-key from the start and simply stops at whichever key's
            # value first fails to decode, so it salvages everything before
            # that point regardless of *why* decoding failed. A malformed-
            # but-*complete* response (`finish_reason != "length"` - a
            # stray/missing comma, an unescaped quote, one bad field deep in
            # the object) previously fell straight through to an empty
            # result and the "needs manual review" placeholder even when
            # `purpose_summary`, `step_by_step_flow`, and most of
            # `business_rules` were intact ahead of the one bad key. One
            # last unconditional recovery attempt here costs nothing when
            # the response truly has nothing usable (`_recover_partial_json`
            # returns `None`), and salvages real content otherwise.
            recovered = self._recover_partial_json(raw_response)
            if recovered is not None:
                data, error = recovered, ""
                used_recovery = True
        # Permanent, model-agnostic observability for exactly the trace this
        # module previously had none of: which outcome each synthesis call
        # (single-call or one section) actually reached, and why. Without
        # this, diagnosing "why is this rule Needs Review" required
        # re-running with ad hoc instrumentation every time - see the 01-18
        # sample batch analysis, where this was reconstructed by hand.
        result_points = len(find_decision_points(raw_source or ""))
        if error:
            outcome = "unresolved_parse_failure"
        elif used_recovery:
            outcome = "recovered_partial_json"
        elif truncated:
            outcome = "recovered_truncated_but_parsed"
        elif retried:
            outcome = "ok_after_retry"
        else:
            outcome = "ok"
        logger.info(
            "Synthesis call outcome=%s decision_points=%d requested_max_tokens=%d "
            "finish_reason=%s response_chars=%d rules=%d",
            outcome,
            result_points,
            effective_max_tokens,
            finish_reason or "unknown",
            len(raw_response or ""),
            len((data or {}).get("business_rules") or []) if isinstance(data, dict) else 0,
        )
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
        if self._clean_ambiguities(data):
            guardrail_warnings.append(
                "One or more ambiguities showed signs of repetition-degeneration "
                "or mid-sentence truncation and were dropped rather than included "
                "in the report."
            )
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
        deliberately NOT a deterministic content generator: every NEW rule
        it returns is model-authored business language, same as the first
        pass. What's deterministic is only *where to look again* - the
        caller (`pipeline.py`) supplies `gaps`, each a source line range
        and snippet that a purely syntactic scan
        (`src/validation/coverage_check.py`) found no rule's evidence
        pointing at. That scan has no idea what the branch means; it only
        knows a CASE/WHEN/IF/ELSIF keyword sits there un-cited. The model
        is always free to conclude a gap is not business-relevant (e.g. a
        technical-only branch) and say so - this never forces a rule into
        existence, it only forces the model to look and explain itself.

        Unlike an earlier version of this method, the model is NEVER asked
        to retype `existing_rules` back to us. That "echo the whole array"
        design made the request's token cost grow without bound as a
        synthesized object accumulated rules - for an object with 150+
        rules the prompt alone could exceed an entire minute's token
        budget on a rate-limited account before the model produced a
        single new word (see `_TPM_LIMIT` handling below). Instead, each
        existing rule is referenced by its already-assigned `rule_id`
        (see `src/ir/rule_identity.py::unique_rule_ids`, applied to every
        rule before it ever reaches here) and the model is asked only for
        (a) genuinely NEW rules, and (b) the rule_ids of any rules it now
        believes are wrong and should be dropped - a list that is normally
        empty. Every existing rule is kept unless explicitly named, so the
        "never silently drop a rule" guarantee holds structurally rather
        than depending on the model successfully retyping everything.

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

        # A compact per-rule INDEX, not the full rule objects. Just enough
        # for the model to recognize "this gap is already covered by rule
        # r4" or "rule r9 duplicates what I'm about to add" without paying
        # for every field (source_evidence arrays, fields_affected, etc.)
        # on every one of potentially hundreds of already-accepted rules.
        existing_rules = existing_rules or []
        index_lines = []
        for rule in existing_rules:
            if not isinstance(rule, dict):
                continue
            rule_id = str(rule.get("rule_id") or "").strip()
            if not rule_id:
                continue
            label = str(rule.get("rule_name") or rule.get("condition") or "").strip()
            label = label[:100]
            index_lines.append(f"- {rule_id}: {label}")
        existing_rules_index = "\n".join(index_lines) if index_lines else "(none yet)"

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
            "YOUR PREVIOUSLY-ACCEPTED RULES (id: short label - already "
            "recorded, do NOT retype these):\n"
            f"{existing_rules_index}\n\n"
            "Respond with ONLY this JSON object (not the full synthesis "
            "schema from before):\n"
            '{"new_rules": [ ... zero or more NEW rule objects, same '
            'schema as the original business_rules entries ... ], '
            '"obsolete_rule_ids": [ ... ids from the list above that are '
            "actually wrong/duplicate and should be removed - leave this "
            'empty unless you are certain ... ]}\n\n'
            "Any id from the list above that you do NOT include in "
            "`obsolete_rule_ids` is kept automatically - you do not need "
            "to (and must not) repeat its content."
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

        # A revision's OUTPUT is now bounded by how much genuinely new
        # content the gaps could produce, not by how many rules already
        # exist - so budget against the gap count, not `_output_token_budget`
        # (which sizes a full-object synthesis pass and would request far
        # more room than this call could ever use).
        revise_max_tokens = min(
            self.hard_max_output_tokens,
            max(_PER_DECISION_POINT_TOKENS * 4, len(gaps) * _PER_DECISION_POINT_TOKENS * 3),
        )

        prompt_tokens_estimate = estimate_prompt_tokens(prompt_set["system"], user_prompt)
        tpm_limit = resolve_tpm_limit(self.provider)
        clamped_max_tokens = clamp_tokens_for_tpm(
            prompt_tokens_estimate, revise_max_tokens, tpm_limit
        )
        if clamped_max_tokens is None:
            # The prompt alone (system + gap context + the rule INDEX,
            # which is small but not free) does not fit under the
            # configured LLM_TPM_LIMIT even with the smallest useful
            # completion budget. Sending anyway is a guaranteed 413.
            # Skip this revision pass gracefully - exactly like a parse
            # failure or an unsupported dialect - and let the gap surface
            # as a reviewable ambiguity instead.
            logger.warning(
                "Skipping coverage-revision call: estimated prompt tokens "
                "(%d) leave no room under LLM_TPM_LIMIT=%s even at the "
                "minimum completion budget. Consider raising LLM_TPM_LIMIT "
                "if your account actually allows more, or reducing "
                "SYNTHESIS_EVIDENCE_MAP_MAX_CHARS.",
                prompt_tokens_estimate, tpm_limit,
            )
            return None
        revise_max_tokens = clamped_max_tokens

        completion_kwargs = {
            "model": model or self.model,
            "temperature": self.temperature,
            "max_tokens": revise_max_tokens,
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
        finish_reason = str(getattr(response.choices[0], "finish_reason", "") or "").lower()
        revision_truncated = finish_reason == "length"

        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", cleaned, flags=re.MULTILINE).strip()
        try:
            revision_payload = self._decode_json_payload(cleaned)
        except json.JSONDecodeError:
            # A revision pass that fails to parse must never wipe out an
            # already-good rule set - keep what synthesize() produced and
            # let the gap simply remain flagged for human review.
            return None

        if revision_truncated:
            # `_decode_json_payload` falls back to `raw_decode`, which
            # successfully decodes a *prefix* of a cut-off response - so a
            # truncated `new_rules` array can still "parse". Even with the
            # new, much smaller schema this remains the dangerous case, not
            # the malformed one: a half-decoded `new_rules` array looks
            # like a legitimate (short) result. Discard it rather than risk
            # silently accepting a mid-sentence-cut rule.
            logger.warning(
                "Synthesis revision truncated (finish_reason=length, "
                "max_tokens=%d); discarding the partial response and "
                "keeping the existing rules so no rule is silently dropped "
                "or half-formed.",
                revise_max_tokens,
            )
            return None

        if not isinstance(revision_payload, dict):
            return None

        new_rules_raw = revision_payload.get("new_rules")
        if not isinstance(new_rules_raw, list):
            new_rules_raw = []
        obsolete_ids_raw = revision_payload.get("obsolete_rule_ids")
        if not isinstance(obsolete_ids_raw, list):
            obsolete_ids_raw = []
        obsolete_ids = {str(item).strip() for item in obsolete_ids_raw if str(item).strip()}

        guardrail_warnings: List[str] = []
        new_rules = self._normalize_business_rules(
            new_rules_raw,
            source_text=raw_source,
            technical_context=merged_extraction,
        )
        for rule in new_rules:
            if isinstance(rule, dict):
                rule["degraded"] = True
                rule["degraded_reason"] = "gap_review"

        kept_rules = [
            rule for rule in existing_rules
            if not (isinstance(rule, dict) and str(rule.get("rule_id") or "").strip() in obsolete_ids)
        ]
        merged_rules = unique_rule_ids(list(kept_rules) + list(new_rules))
        merged_rules = self._remove_operational_status_rules(merged_rules, merged_extraction)
        merged_rules = self._remove_non_business_cleanup_rules(merged_rules, merged_extraction)
        merged_rules = self._remove_operation_only_rules(merged_rules)

        data: Dict[str, Any] = dict(_EMPTY_SYNTHESIS)
        data["business_rules"] = merged_rules
        jargon_flags = self._scan_for_jargon(data)
        return SynthesisResult(
            data=data,
            raw_response=raw_response,
            parse_error="",
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
        # Deterministic chunk/full-source parse-error housekeeping ("Chunk
        # 'X' (kind) technical extraction returned malformed JSON and needs
        # manual review.", "Full-source technical extraction returned
        # malformed JSON...") is already tracked and will reach the final
        # report's Findings section regardless of what the model says - it
        # never needs the model to re-derive or repeat it. Sending it as
        # input "ambiguities" anyway invited the model to paraphrase it back
        # out in its own "ambiguities" output (observed for real: the same
        # fact reported 3-4 times with different wording - "Chunk
        # '00_main_body_1' ... malformed JSON", "Several chunks ... need
        # manual review", "The technical extraction for chunks '...',
        # '...' returned malformed JSON" - none of which added new
        # information over the one deterministic message per chunk).
        # Genuine extraction-derived ambiguities (anything not matching this
        # specific housekeeping shape) still reach the model unchanged.
        payload["ambiguities"] = [
            item for item in (merged_extraction.get("ambiguities", []) or [])
            if not RuleSynthesizerAgent._is_parse_error_housekeeping_ambiguity(item)
        ]
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
        status_table_bare_names = {
            table.split(".")[-1].strip("#") for table in status_tables if table
        }

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
            # Three independent signals, any one of which is enough on its
            # own: (1) the rule names one of the status columns directly -
            # the strongest, structural signal; (2) the rule's own
            # condition/evidence text names the status table itself (its
            # bare name, e.g. `ACLRUNNINGPROCESSSTATUS`) or the
            # `RUNNINGPROCESSNAME` scoping column - equally structural, and
            # catches a rule `ensure_decision_chain_coverage` synthesized
            # straight from a deterministic chain whose OTHER fields
            # (`ERRORDATE`, `ERRORDESCRIPTION`, ...) don't happen to be
            # this rule's own `fields_affected` value but still appear
            # verbatim in its condition text (e.g. `IF EXISTS (SELECT 1
            # FROM ACLRUNNINGPROCESSSTATUS WHERE RUNNINGPROCESSNAME = ...)`
            # guarding a CATCH-block bookkeeping write); (3) a plain
            # phrase-marker match, used only as a last resort when the rule
            # carries no resolved fields at all (a model-authored "Update
            # Process Status on Success/Failure" with an empty field list)
            # - never on its own when real fields ARE present, so it can
            # never misfire on an unrelated business rule that merely
            # mentions "completion" in prose.
            table_reference_match = bool(status_table_bare_names) and (
                any(name and name in text for name in status_table_bare_names)
                or "RUNNINGPROCESSNAME" in text
            )
            marker_match = any(
                marker in text
                for marker in (
                    "PROCESS STATUS", "RUNNING PROCESS", "ERROR DESCRIPTION",
                    "COMPLETION", "COMPLETED",
                )
            )
            is_status_rule = table_reference_match or (
                marker_match and (bool(fields & status_fields) or not fields)
            )
            if not is_status_rule:
                filtered.append(rule)
        return filtered

    # A single-row condition that is purely an existence/non-null check on
    # one or more fields, with nothing else - no comparison, no threshold,
    # no OR/AND branch content. Deliberately loose about field-list shape
    # ("X is not null", "X, Y, Z are not null", "NOT X IS NULL") since the
    # goal is to catch every phrasing the synthesis prompt is observed to
    # produce for this shape, not just one.
    _TAUTOLOGY_NULL_CHECK_RE = re.compile(
        r"(?i)^\s*(?:not\s+)?[\w #@\[\]$.,]+?\s+(?:is|are)(?:\s+not)?\s+null\s*$"
    )
    # A real business outcome states a literal value, a calculation, or a
    # branch-dependent choice. An outcome that names none of those - just an
    # operation verb (update/insert/merge) plus a target, or the bare field
    # name being written - carries no decision content on its own.
    _TAUTOLOGY_OUTCOME_HAS_CONTENT_RE = re.compile(r"(?i)['\"]|\bcase\b|\bwhen\b|[+\-*/]")
    _TAUTOLOGY_OPERATION_VERB_RE = re.compile(r"(?i)^\s*(?:update|insert|merge)\b")

    @staticmethod
    def _remove_tautological_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Drop rules whose only "decision" is a null-check guarding the
        very field(s) it writes - e.g. `PenalInterestAmount is not null ->
        Update PenalInterestAmount`, or `AccountId, DpdBucket... are not
        null -> Insert and update records in #Staging`. This describes that
        a write happens, not any business condition under which it
        happens differently - it is a restatement of the write's own
        existence, not a rule. A single-row requirement (no ELSE/second
        branch) keeps this from ever touching a genuine multi-branch
        decision that merely starts with a null guard.
        """
        from src.parsing.decision_identity import bare_field_key

        def _is_tautological(rule: Dict[str, Any]) -> bool:
            rows = rule.get("decision_logic_rows") or []
            if len(rows) != 1 or not isinstance(rows[0], dict):
                return False
            condition = str(rows[0].get("condition") or "").strip()
            outcome = str(rows[0].get("outcome") or "").strip()
            if not condition or not outcome:
                return False
            if not RuleSynthesizerAgent._TAUTOLOGY_NULL_CHECK_RE.match(condition):
                return False
            if RuleSynthesizerAgent._TAUTOLOGY_OUTCOME_HAS_CONTENT_RE.search(outcome):
                return False
            if RuleSynthesizerAgent._TAUTOLOGY_OPERATION_VERB_RE.match(outcome):
                return True
            condition_fields = {
                bare_field_key(part)
                for part in re.split(r"[,\s]+", condition)
                if part and part.upper() not in {"IS", "ARE", "NOT", "NULL"}
            }
            return bare_field_key(outcome) in condition_fields

        return [
            rule for rule in (rules or [])
            if not (isinstance(rule, dict) and _is_tautological(rule))
        ]

    @staticmethod
    def consolidate_duplicate_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge rules that independently describe the same underlying
        decision - same target field, same normalized condition ladder -
        into one, instead of rendering each extraction attempt as its own
        numbered rule.

        Outcomes are deliberately NOT part of the merge key (see
        `rule_decision_identity`'s docstring): two candidates for the same
        statement can disagree on outcome text while still being the same
        decision, most often because one bundles in content that actually
        belongs to a different, nearby statement (observed for real, from a
        coverage-retry pass that fused an unrelated CASE's results into an
        already-correct rule's branches). When a group merges, the kept
        candidate is chosen by, in order: (1) completeness - a candidate
        with any blank/missing outcome value loses to one whose every row
        has a real value, regardless of field count (real bug: a
        model-authored duplicate that omitted one branch's value, e.g.
        `DpdDays IS NULL -> ` with nothing after the arrow, used to win a
        tie against the deterministic chain-derived rule that correctly
        had `-> 'NOT_APPLICABLE'`, purely because both happened to touch
        only one field - completeness of the actual decision content must
        outrank a field-count tiebreak that was never meant to trade away
        correctness); (2) deterministic/grounded origin - a rule built
        directly from parsed source (`source_chain_id` set, or
        `rule_type == "deterministic_decision_table"`, or
        `confidence == "deterministic"` - see `ensure_decision_chain_
        coverage`) beats an equally-complete model-authored one, since it
        cannot hallucinate a value; (3) narrowest - fewest total fields in
        `output_field`/`fields_affected`, the original heuristic, still
        deciding between two otherwise-equal complete/model candidates
        (e.g. R6 vs R7 in the audit this function was built for). The
        other candidates' extra fields are recorded as a footnote
        (`consolidation_note`) rather than unioned into the kept rule's own
        content - unioning would risk presenting fused, possibly-incorrect
        content as one confident rule, which is worse than a visible
        footnote naming what else was seen. A `degraded` flag (if present)
        is taken from the kept candidate only, not OR'd across the group -
        merging into a clean, non-degraded rule must not mark it degraded
        just because a noisier duplicate also existed.

        Rules with no `decision_logic_rows` at all (nothing to key
        structural identity on) are never merged with anything, including
        each other - safe by construction, not by coincidence.
        """
        from src.parsing.decision_identity import rule_decision_identity

        def _all_fields(rule: Dict[str, Any]) -> List[str]:
            output_field = rule.get("output_field")
            fields = rule.get("fields_affected") or []
            if isinstance(fields, str):
                fields = [fields]
            values: List[str] = []
            if isinstance(output_field, str) and output_field.strip():
                values.append(output_field.strip())
            values.extend(str(field).strip() for field in fields if str(field).strip())
            return list(dict.fromkeys(values))

        def _has_incomplete_outcome(rule: Dict[str, Any]) -> bool:
            rows = rule.get("decision_logic_rows") or []
            return any(
                isinstance(row, dict) and not str(row.get("outcome") or "").strip()
                for row in rows
            )

        def _is_deterministic(rule: Dict[str, Any]) -> bool:
            return bool(
                rule.get("source_chain_id")
                or rule.get("rule_type") == "deterministic_decision_table"
                or rule.get("confidence") == "deterministic"
            )

        def _candidate_rank(rule: Dict[str, Any]) -> Tuple[int, int, int]:
            return (
                1 if _has_incomplete_outcome(rule) else 0,
                0 if _is_deterministic(rule) else 1,
                len(_all_fields(rule)),
            )

        groups: Dict[Any, List[Dict[str, Any]]] = {}
        order: List[Any] = []
        for rule in rules or []:
            if not isinstance(rule, dict):
                continue
            rows = rule.get("decision_logic_rows") or []
            key = ("__unkeyed__", id(rule)) if not rows else rule_decision_identity(
                rule.get("output_field"), rows
            )
            if key not in groups:
                order.append(key)
            groups.setdefault(key, []).append(rule)

        consolidated: List[Dict[str, Any]] = []
        for key in order:
            group = groups[key]
            if len(group) == 1:
                consolidated.append(group[0])
                continue
            kept = min(group, key=_candidate_rank)
            kept_fields = set(_all_fields(kept))
            other_fields = sorted(
                {field for rule in group if rule is not kept for field in _all_fields(rule)}
                - kept_fields
            )
            merged = dict(kept)
            if other_fields:
                note = (
                    "Also extracted with additional fields attached in another pass ("
                    + ", ".join(other_fields)
                    + ") - kept the narrower, consistent version of this rule."
                )
                existing_note = str(merged.get("consolidation_note") or "").strip()
                merged["consolidation_note"] = f"{existing_note} {note}".strip() if existing_note else note
            consolidated.append(merged)
        return consolidated

    @staticmethod
    def backfill_blank_outcomes_from_decision_chains(
        rules: List[Dict[str, Any]], decision_chains: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Final safety net: replace a blank/missing `decision_logic_rows`
        outcome with the real value from the matching deterministic chain
        branch, when one exists for the same field and (qualifier-
        normalized) condition.

        Real bug this closes (traced against a live-generated report):
        `consolidate_duplicate_rules` only helps when two CANDIDATES for
        the exact same condition ladder both survive to be compared - it
        cannot help a rule that is the *only* candidate for its identity
        but still has a blank cell for one row, e.g. when
        `merge_decision_chains` keeps a second, independently-extracted
        chain for the same CASE statement (not a byte-identical
        structural duplicate, so never deduped away) whose own branch
        text for one arm came back empty, and that chain - not the clean
        one - is what a downstream stage ends up attached to. Rather than
        chase every possible path that can produce a blank cell, this
        runs once, last, and cross-checks every blank outcome against the
        one source proven correct throughout this pipeline: the parsed
        source `decision_chains` themselves. It only ever fills an empty
        cell - it never overwrites a non-blank outcome, however it was
        derived, so this cannot make a report *less* accurate, only more
        complete.
        """
        from src.parsing.decision_identity import bare_field_key, normalized_condition_key

        def _normalize_for_chain_match(condition: str) -> str:
            # A rendered row's condition can carry a display-only
            # annotation appended after coverage (`_annotate_row_
            # condition_with_filter` - " — row filter: ...", or an
            # "[UNREACHABLE ...]" suffix) that a raw chain branch's own
            # condition text never has. Strip those before matching so an
            # annotated row can still find its chain branch.
            text = str(condition or "")
            for marker in (" — row filter:", " [UNREACHABLE"):
                idx = text.find(marker)
                if idx != -1:
                    text = text[:idx]
            return normalized_condition_key(text)

        chain_lookup: Dict[Tuple[str, str], str] = {}
        for chain in decision_chains or []:
            if not isinstance(chain, dict):
                continue
            for branch in chain.get("branches") or []:
                if not isinstance(branch, dict):
                    continue
                condition_text = (
                    "ELSE" if branch.get("is_catch_all")
                    else str(branch.get("branch_condition") or "").strip()
                )
                normalized_condition = normalized_condition_key(condition_text)
                for assignment in branch.get("assignments") or []:
                    if not isinstance(assignment, dict):
                        continue
                    field_key = bare_field_key(assignment.get("field"))
                    value = str(assignment.get("value") or "").strip()
                    if not field_key or not value:
                        continue
                    # First writer wins: merge_decision_chains already
                    # orders deterministic chains ahead of LLM-derived
                    # ones, so the first (highest-priority) value seen for
                    # a given (field, condition) pair is kept.
                    chain_lookup.setdefault((field_key, normalized_condition), value)

        if not chain_lookup:
            return rules

        for rule in rules or []:
            if not isinstance(rule, dict):
                continue
            rows = rule.get("decision_logic_rows")
            if not isinstance(rows, list):
                continue
            field_key = bare_field_key(rule.get("output_field"))
            if not field_key:
                continue
            for row in rows:
                if not isinstance(row, dict) or str(row.get("outcome") or "").strip():
                    continue
                replacement = chain_lookup.get(
                    (field_key, _normalize_for_chain_match(row.get("condition")))
                )
                if replacement:
                    row["outcome"] = replacement
        return rules

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
            and str(row.get("operation") or "").upper() in {"DROP", "CREATE"}
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
            # sufficient to classify a technical DROP/CREATE when the statement
            # parser could not build an operation record for that dialect or
            # syntax variant. This remains deletion-only and does not infer
            # business meaning.
            cleanup_evidence = bool(re.search(
                r"\b(?:DROP|CREATE)\s+TABLE\b.*(?:#|TEMP|TMP|TEMPORARY)",
                evidence_text,
                re.IGNORECASE | re.DOTALL,
            )) or bool(re.search(
                r"\b(?:DROP|CREATE)\s+TABLE\b.*(?:#|TEMP|TMP|TEMPORARY)",
                str(rule.get("condition") or "") + " " + str(rule.get("action") or "") + " " + str(rule.get("rule_name") or ""),
                re.IGNORECASE | re.DOTALL,
            ))
            is_cleanup_description = any(
                marker in rule_text for marker in (
                    "drop", "create", "temporary", "temp table", "cleanup", "#dpdstaging",
                )
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
                and not re.search(r"\b(?:DROP|CREATE)\s+TABLE\b", condition, re.IGNORECASE)
            )
            is_cleanup = bool(cleanup_tables) or cleanup_evidence or existence_guard
            # A CREATE/DROP of a temp staging table with no multi-branch
            # decision content is execution plumbing, not a business rule
            # (observed: "Create #DpdStaging table" rendered as R1).
            name_action = f"{rule.get('rule_name') or ''} {rule.get('action') or ''}".lower()
            is_temp_ddl = bool(re.search(
                r"\b(?:create|drop)\b.*(?:#\w+|temp(?:orary)?\s+table)",
                name_action,
                re.IGNORECASE,
            )) and not has_genuine_decision
            if ((is_cleanup and is_cleanup_description and not has_business_fields and not has_genuine_decision)
                    or is_temp_ddl):
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
            evidence = " ".join(str(item) for item in rule.get("source_evidence") or []).upper()
            condition = str(rule.get("condition") or "").upper()
            name = str(rule.get("rule_name") or "").lower()
            action = str(rule.get("action") or "").lower()
            meaning = str(rule.get("business_meaning") or "").lower()
            prose = f"{name} {action} {meaning}"
            evidence_blob = f"{evidence} {condition}"
            # A rule titled "Read/Retrieve/..." is retrieval framing, not a
            # business decision - even when the model pasted the INSERT's
            # WHERE filter into a one-row "decision table" (observed live
            # on Collateral Valuation Staging). Keep real multi-branch
            # ladders even if poorly titled.
            rows = rule.get("decision_logic_rows") or []
            is_read_titled = bool(re.match(r"^(read|retrieve|fetch|look\s*up|select)\b", name.strip()))
            if is_read_titled and len(rows) <= 1:
                continue
            if rows:
                filtered.append(rule)
                continue
            is_crud = bool(re.search(r"\b(SELECT|UPDATE|INSERT|DELETE|MERGE)\b", evidence_blob))
            is_mechanical = (
                "source-defined value" in action
                or "source-defined value" in name
                or (name.startswith(("update ", "insert ", "write ")) and not rule.get("eligibility"))
            )
            # A bare SELECT framed as a "business rule" (e.g. "Read DPD
            # bucket history") is technical retrieval, not a decision.
            # Require: SELECT evidence, no write verb in the citation, no
            # decision rows (already gated above), and read-oriented prose.
            is_read_only_select = (
                bool(re.search(r"\bSELECT\b", evidence_blob))
                and not bool(re.search(r"\b(UPDATE|INSERT|DELETE|MERGE)\b", evidence_blob))
                and bool(re.search(r"\b(read|retrieve|select|fetch|look\s*up|return)\b", prose))
            )
            if (is_crud and is_mechanical) or is_read_only_select:
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
                # A model occasionally returns a list with a NESTED list as
                # one of its own items (e.g. `fields_affected: ["SeverityTier",
                # ["FeedName", "Outcome", "ReconciledOn"]]`) instead of a flat
                # list of field names. Left as-is, that inner list survives
                # all the way to display and renders as a literal Python
                # repr (`['FeedName', 'Outcome', 'ReconciledOn']`) in the
                # report text. Flatten one level so every item downstream
                # can keep assuming a flat list of scalars, which every
                # existing caller already does.
                flattened: List[Any] = []
                for item in value:
                    if isinstance(item, list):
                        flattened.extend(item)
                    else:
                        flattened.append(item)
                return flattened
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
                if rule["decision_logic_rows"]:
                    # Every row came straight from deterministic chain
                    # evidence (the model supplied none of its own) - report
                    # formatting's duplicate-suppression passes treat this
                    # the same as a canonical `decision_block_id` rule when
                    # deciding which of two overlapping tables is authoritative.
                    rule["decision_rows_grounded"] = True
            elif decision_chains and RuleSynthesizerAgent._decision_logic_rows_look_incomplete(
                rule["decision_logic_rows"]
            ):
                # The rule already has its OWN rows (so the "no rows at
                # all" backfill above never runs), but at least one row's
                # outcome (or condition) is blank - observed for real: the
                # model reproduced every condition in a multi-branch chain
                # correctly but left the final ELSE row's outcome text
                # empty, apparently running low on budget right at the end
                # of its own response. Repair just the blank cell(s) from a
                # deterministic decision chain whose branch conditions line
                # up with this rule's own rows one-for-one - a direct
                # structural match, not the output_field-name-plus-evidence
                # heuristic `_backfill_decision_logic_rows` needs to trust a
                # *whole* replacement table, so it still works even when
                # the rule's own `source_evidence` doesn't literally quote
                # the chain's SQL.
                rule["decision_logic_rows"] = RuleSynthesizerAgent._repair_blank_decision_outcomes(
                    rule["decision_logic_rows"], rule.get("output_field", ""), decision_chains
                )
            for key in ("rule_type", "confidence", "validation_status", "rule_id", "ambiguity_id"):
                value = rule.get(key, "")
                rule[key] = value if isinstance(value, str) else ("" if value is None else str(value))
            normalized.append(rule)
        return unique_rule_ids(normalized)

    @staticmethod
    def _decision_logic_rows_look_incomplete(rows: List[Dict[str, Any]]) -> bool:
        """True when any row's `outcome` (or `condition`) is blank after
        stripping. A model response that ran low on its own output budget
        right at the last branch has been observed to reproduce every
        condition correctly but leave that branch's outcome text empty -
        the row is present, so this isn't caught by "no rows at all", but
        it is exactly the shape `_backfill_decision_logic_rows` exists to
        repair from the deterministic decision chain when one matches.
        """
        for row in rows:
            if not isinstance(row, dict):
                return True
            if not str(row.get("outcome") or "").strip():
                return True
            if not str(row.get("condition") or "").strip():
                return True
        return False

    @staticmethod
    def _decision_condition_key(text: Any) -> str:
        """Reduce a branch/row condition to a comparison key: dotted field
        references collapsed to their bare trailing segment (`A.DpdDays`,
        `PRO.LoanAccountCal.DpdDays`, and a bare `DpdDays` all become
        `DpdDays`), whitespace collapsed, casefolded. Used only to line up
        a rule's own condition text against a decision chain's branch
        condition text one-for-one - never for display.
        """
        text = str(text or "")
        dotted_path = re.compile(r"(?<![A-Za-z0-9_])(?:[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*")
        bare = dotted_path.sub(lambda match: match.group(0).split(".")[-1], text)
        return re.sub(r"\s+", "", bare).strip().casefold()

    @staticmethod
    def _repair_blank_decision_outcomes(
        rows: List[Dict[str, Any]], output_field: Any, decision_chains: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fill blank outcome cells in `rows` from whichever decision chain's
        branch conditions match `rows`' own conditions one-for-one, in
        order. Matching structurally on the condition sequence itself - not
        `output_field` name plus an evidence-text heuristic, which
        `_backfill_decision_logic_rows` needs in order to trust replacing a
        rule's entire table - is a strictly stronger correspondence signal
        here: rows whose conditions already line up perfectly with a
        chain's branches are, for practical purposes, never a coincidence,
        so their few blank cells can be safely filled without needing the
        rule to have recorded matching source_evidence text at all.
        Returns `rows` unchanged if no chain lines up or nothing was blank.
        """
        if not rows:
            return rows
        row_keys = [
            RuleSynthesizerAgent._decision_condition_key(row.get("condition", ""))
            for row in rows if isinstance(row, dict)
        ]
        if len(row_keys) != len(rows) or not any(row_keys):
            return rows
        output_field_key = RuleSynthesizerAgent._bare_field_key(output_field)
        if not output_field_key:
            return rows
        for chain in decision_chains:
            branches = chain.get("branches")
            if not isinstance(branches, list) or len(branches) != len(rows):
                continue
            branch_keys: List[str] = []
            branch_values: List[str] = []
            matched_every_branch = True
            for branch in branches:
                if not isinstance(branch, dict):
                    matched_every_branch = False
                    break
                condition = (
                    "ELSE" if branch.get("is_catch_all")
                    else str(branch.get("branch_condition") or "").strip()
                )
                assignments = branch.get("assignments")
                match = next(
                    (
                        a for a in (assignments or [])
                        if isinstance(a, dict)
                        and RuleSynthesizerAgent._bare_field_key(a.get("field")) == output_field_key
                    ),
                    None,
                )
                if match is None:
                    matched_every_branch = False
                    break
                branch_keys.append(RuleSynthesizerAgent._decision_condition_key(condition))
                branch_values.append(str(match.get("value") or "").strip())
            if not matched_every_branch or branch_keys != row_keys:
                continue
            repaired: List[Dict[str, Any]] = []
            changed = False
            for row, value in zip(rows, branch_values):
                if not isinstance(row, dict):
                    repaired.append(row)
                    continue
                if not str(row.get("outcome") or "").strip() and value:
                    new_row = dict(row)
                    new_row["outcome"] = value
                    repaired.append(new_row)
                    changed = True
                else:
                    repaired.append(row)
            if changed:
                return repaired
        return rows

    _IS_NULL_RE = re.compile(r"(?i)^\s*(?P<col>[\w.#$@]+)\s+IS\s+NULL\s*$")
    _IS_NOT_NULL_RE = re.compile(r"(?i)^\s*(?P<col>[\w.#$@]+)\s+IS\s+NOT\s+NULL\s*$")
    _NOT_IS_NULL_RE = re.compile(r"(?i)^\s*NOT\s+(?P<col>[\w.#$@]+)\s+IS\s+NULL\s*$")

    @staticmethod
    def _bare_column_name(text: str) -> str:
        return str(text or "").strip().split(".")[-1].strip().upper()

    @staticmethod
    def _bare_field_key(text: Any) -> str:
        """Reduce a field reference to a comparison key: a qualified
        reference (`PRO.LoanAccountCal.DpdBucket`, `A.DpdBucket`) and its
        bare form (`DpdBucket`) both collapse to the same key. A model-
        authored `output_field` is schema-qualified far more often than a
        deterministic decision chain's own `assignment["field"]` (always
        the bare source column) - comparing the two with a strict
        lowercase `==` silently fails the match and skips repair/backfill
        entirely for every qualified `output_field`.
        """
        return str(text or "").strip().split(".")[-1].strip().casefold()

    @classmethod
    def _branch_is_unreachable(cls, eligibility: Any, branch_condition: str) -> bool:
        """True when `branch_condition` can be *proven* to never hold for
        any row the enclosing statement's own WHERE clause (`eligibility`)
        already restricts to - currently: a plain `IS NULL` branch on a
        column the statement's WHERE already requires `IS NOT NULL` (or
        `NOT ... IS NULL`) on. Observed for real: `WHERE A.DpdDays IS NOT
        NULL` gating an UPDATE whose own CASE still carries a `WHEN A.
        DpdDays IS NULL THEN ...` branch - dead code the source keeps
        (defensively, or left over from an earlier version) that a report
        must not present with the same confidence as a branch that can
        actually execute.

        Deliberately narrow: this is not general boolean satisfiability -
        only a contradiction this certain (and this cheap) to prove is
        flagged; anything less certain is left alone rather than guessed
        at.
        """
        branch_null = cls._IS_NULL_RE.match(str(branch_condition or ""))
        if not branch_null:
            return False
        branch_col = cls._bare_column_name(branch_null.group("col"))
        for clause in eligibility or []:
            clause_text = str(clause or "")
            not_null = cls._NOT_IS_NULL_RE.match(clause_text) or cls._IS_NOT_NULL_RE.match(clause_text)
            if not_null and cls._bare_column_name(not_null.group("col")) == branch_col:
                return True
        return False

    @staticmethod
    def _annotate_row_condition_with_filter(condition: str, branch: Dict[str, Any], chain_type: Any) -> str:
        """Append a branch's own row-level WHERE filter to its rendered
        condition text, clearly labeled and visually separate from the
        branch-selection condition itself - the two answer different
        questions ("does this branch run at all" vs "which rows does it
        act on once it does") and merging them into one condition string
        with no label would silently lose that distinction (a real gap:
        a T-SQL `IF EXISTS(...) BEGIN UPDATE ... WHERE <row filter> END`
        ladder's per-branch row filter was previously dropped entirely).

        Only meaningful for `TSQL_IF_ELSE` chains, where each branch is
        its own separate UPDATE/INSERT statement and the row filter
        genuinely varies branch to branch (including a branch with NO
        filter at all, which must say so explicitly - "not shown" reads
        as "unknown", not as "applies to every row"). A `CASE`-expression
        chain's single enclosing statement WHERE is already surfaced
        once, for the whole rule, via `eligibility`/"Applies to" -
        repeating it on every row here would be pure noise.
        """
        if chain_type != "TSQL_IF_ELSE" or not isinstance(branch, dict):
            return condition
        row_filter = str(branch.get("row_filter") or "").strip()
        if row_filter:
            return f"{condition} — row filter: {row_filter}"
        return f"{condition} — applies to all rows (no additional filter)"

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
        output_field_key = RuleSynthesizerAgent._bare_field_key(output_field)
        matching_chains = [
            chain for chain in decision_chains
            if any(RuleSynthesizerAgent._bare_field_key(a.get("field")) == output_field_key
                   for branch in (chain.get("branches") or [])
                   for a in (branch.get("assignments") or []) if isinstance(a, dict))
        ]
        if len(matching_chains) != 1:
            return []
        from src.parsing.decision_identity import decision_text_key
        source_key = decision_text_key(matching_chains[0].get("source_sql", ""))
        evidence = rule.get("source_evidence") or []
        if isinstance(evidence, str):
            evidence = [evidence]
        if (not rule.get("source_chain_id") and source_key
                and not any(source_key in decision_text_key(item) for item in evidence)):
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
                        # Case- and qualification-insensitive: the model's
                        # own `output_field` text ("SMA_Class", or a fully
                        # qualified "PRO.Table.SMA_Class") does not always
                        # match the deterministic extractor's literal bare
                        # source casing ("SMA_CLASS") verbatim, and a strict
                        # `==` here silently drops the backfill for an
                        # otherwise perfectly matched field.
                        and RuleSynthesizerAgent._bare_field_key(assignment.get("field")) == output_field_key
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
                if RuleSynthesizerAgent._branch_is_unreachable(chain.get("eligibility"), condition):
                    condition = (
                        f"{condition} [UNREACHABLE — contradicts this statement's own WHERE "
                        "clause; never executes for any row it touches]"
                    )
                condition = RuleSynthesizerAgent._annotate_row_condition_with_filter(
                    condition, branch, chain.get("chain_type")
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
        rules = unique_rule_ids(rules)
        if not decision_chains:
            return rules

        def _field_key(value: Any) -> str:
            return RuleSynthesizerAgent._bare_field_key(value)

        def _normalized_condition(value: Any) -> str:
            # Qualifier-stripping, not just decision_text_key's whitespace/
            # case normalization: a deterministic chain's own condition/
            # outcome text is routinely fully-qualified or alias-qualified
            # (`PRO.LoanAccountCal.DpdDays = 0`, `#DpdStaging.AdjustedPenalty
            # * 1.10`) while a model-authored rule for the exact same
            # statement just names the bare column (`DpdDays = 0`,
            # `AdjustedPenalty * 1.10`). Without stripping qualifiers here,
            # `_field_is_covered` below never recognizes the two as the same
            # decision, and a synthetic backfill rule gets added right next
            # to the model's already-correct one - the real duplicate-rule
            # bug this normalization exists to close.
            #
            # Also strip display-only TSQL_IF annotations ("— row filter:",
            # "— applies to all rows", [UNREACHABLE ...]) so coverage
            # compares the structural IF/CASE predicates, not presentation.
            from src.parsing.decision_identity import normalized_condition_key
            text = str(value or "")
            text = re.sub(r"\s*—\s*row filter:.*$", "", text, flags=re.S | re.I)
            text = re.sub(r"\s*—\s*applies to all rows.*$", "", text, flags=re.S | re.I)
            text = re.sub(r"\s*\[UNREACHABLE[^\]]*\]", "", text, flags=re.I)
            return normalized_condition_key(text)

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

        def _repair_blank_outcome_cover(
            chain: Dict[str, Any], field_key: str, rows: List[Dict[str, Any]]
        ) -> bool:
            """A model rule that already lists the correct ordered conditions
            but left one-or-more outcome cells blank is a near-cover, not a
            miss. Filling those blanks from the chain (never inventing a new
            ladder) and treating the rule as covered avoids synthesizing a
            second, duplicate table for the same field.
            """
            expected_conditions = [_normalized_condition(row.get("condition")) for row in rows]
            if not expected_conditions:
                return False
            repaired = False
            for rule in rules:
                if _field_key(rule.get("output_field")) != field_key:
                    continue
                source_chain = rule.get("source_chain_id")
                if source_chain and source_chain != chain.get("chain_id"):
                    continue
                rule_rows = rule.get("decision_logic_rows") or []
                if not isinstance(rule_rows, list) or len(rule_rows) != len(rows):
                    continue
                rule_conditions = [
                    _normalized_condition(row.get("condition"))
                    for row in rule_rows if isinstance(row, dict)
                ]
                if rule_conditions != expected_conditions:
                    continue
                for rule_row, chain_row in zip(rule_rows, rows):
                    if not isinstance(rule_row, dict):
                        continue
                    if str(rule_row.get("outcome") or "").strip():
                        continue
                    replacement = str(chain_row.get("outcome") or "").strip()
                    if replacement:
                        rule_row["outcome"] = replacement
                        repaired = True
                if repaired or _rows_key(rule_rows) == _rows_key(rows):
                    return True
            return repaired

        def _sanitize_covering_rule_name(chain: Dict[str, Any], field_key: str, display_field: str) -> None:
            """When a model-authored rule already covers a chain's rows, its
            `rule_name` is kept (it may carry genuine business framing this
            deterministic path cannot invent). But the model sometimes copies
            the evaluation-order/execution-semantics sentence verbatim into
            `rule_name` (or `business_meaning`) instead of writing a short
            business label - that sentence is meant as procedural commentary,
            not a title/purpose, and reusing it produces near-duplicate rule
            titles and overview "Business Purpose" cells across unrelated
            fields/tables in the report. Replace only that specific failure
            mode with the same deterministic naming convention used for
            synthesized rules; never touch a rule_name that isn't a copy of
            the execution semantics text.
            """
            semantics = str(chain.get("execution_semantics") or "").strip().casefold()
            if not semantics:
                return
            for rule in rules:
                if _field_key(rule.get("output_field")) != field_key:
                    continue
                source_chain = rule.get("source_chain_id")
                if source_chain and source_chain != chain.get("chain_id"):
                    continue
                existing_name = str(rule.get("rule_name") or "").strip()
                if existing_name.casefold() == semantics:
                    rule["rule_name"] = (
                        f"Determine inputs to {chain['aggregation']} for {display_field}"
                        if chain.get("aggregation") else f"Determine {display_field}"
                    )
                existing_meaning = str(rule.get("business_meaning") or "").strip()
                if existing_meaning.casefold() == semantics:
                    # Empty meaning lets the formatter show "Not specified"
                    # rather than echoing evaluation-order commentary into
                    # the Business Purpose column.
                    rule["business_meaning"] = ""

        def _drop_incomplete_siblings(field_key: str, rows: List[Dict[str, Any]]) -> None:
            """Once a complete cover exists for this field's ladder, drop any
            sibling that restates the same ordered conditions - whether with
            blank outcomes (incomplete paraphrase) or with a second complete
            copy (two model rules for one CASE). Keep a single preferred
            cover: deterministic tables win, then a non-boilerplate name.
            """
            expected = _rows_key(rows)
            expected_conditions = [condition for condition, _outcome in expected]
            if not expected_conditions:
                return
            complete = [
                rule for rule in rules
                if _field_key(rule.get("output_field")) == field_key
                and _rows_key(rule.get("decision_logic_rows") or []) == expected
            ]
            if not complete:
                return

            def _cover_rank(rule: Dict[str, Any]) -> tuple:
                is_det = 1 if rule.get("rule_type") == "deterministic_decision_table" else 0
                name = str(rule.get("rule_name") or "").strip()
                semantics = str(rule.get("execution_semantics") or "").strip().casefold()
                boilerplate = 0 if (name and name.casefold() != semantics) else -1
                meaning = 1 if str(rule.get("business_meaning") or "").strip() else 0
                return (is_det, boilerplate, meaning, -len(name))

            preferred = max(complete, key=_cover_rank)
            preferred_id = id(preferred)
            kept: List[Dict[str, Any]] = []
            for rule in rules:
                if _field_key(rule.get("output_field")) != field_key:
                    kept.append(rule)
                    continue
                rule_rows = [row for row in (rule.get("decision_logic_rows") or []) if isinstance(row, dict)]
                rule_key = _rows_key(rule_rows)
                if rule_key == expected:
                    if id(rule) == preferred_id:
                        kept.append(rule)
                    continue
                rule_conditions = [condition for condition, _outcome in rule_key]
                has_blank = any(not str(row.get("outcome") or "").strip() for row in rule_rows)
                if rule_conditions == expected_conditions and has_blank:
                    continue
                kept.append(rule)
            rules[:] = kept

        synthetic_rules: List[Dict[str, Any]] = []
        for chain in decision_chains:
            if not isinstance(chain, dict):
                continue
            branches = chain.get("branches")
            if not isinstance(branches, list):
                continue

            chain_type = str(chain.get("chain_type") or "").strip().upper()
            # T-SQL IF/ELSEIF/ELSE is one mutual-exclusive control-flow
            # decision that may assign several fields per branch (e.g.
            # BucketWorsened + GracePeriodApplied under the grace gate).
            # Emitting one rule per field drops companion fields that only
            # appear in a single branch (len(rows)<2), then
            # ensure_statement_coverage re-floors them from the UPDATE's
            # WHERE alone - losing the enclosing IF EXISTS gate. Keep the
            # whole ladder as one multi-field rule instead.
            if chain_type == "TSQL_IF_ELSE":
                fields_in_chain: "OrderedDict[str, str]" = OrderedDict()
                branch_payloads: List[Tuple[Dict[str, Any], str, List[Dict[str, str]]]] = []
                for branch in branches:
                    if not isinstance(branch, dict):
                        continue
                    assignments = [
                        item for item in (branch.get("assignments") or [])
                        if isinstance(item, dict) and str(item.get("field") or "").strip()
                    ]
                    if not assignments:
                        continue
                    for assignment in assignments:
                        field = str(assignment.get("field") or "").strip()
                        fields_in_chain.setdefault(_field_key(field), field)
                    condition = (
                        "ELSE"
                        if branch.get("is_catch_all")
                        or str(branch.get("branch_condition") or "").strip().upper() == "ELSE"
                        else str(branch.get("branch_condition") or "").strip()
                    )
                    branch_payloads.append((branch, condition, assignments))
                if len(branch_payloads) < 2 or not fields_in_chain:
                    continue
                multi_field = len(fields_in_chain) > 1
                coverage_rows: List[Dict[str, Any]] = []
                display_rows: List[Dict[str, Any]] = []
                for branch, condition, assignments in branch_payloads:
                    if multi_field:
                        outcome = "; ".join(
                            f"{str(item.get('field') or '').strip()} := "
                            f"{str(item.get('value') or '').strip()}"
                            for item in assignments
                        )
                    else:
                        outcome = str(assignments[0].get("value") or "").strip()
                    coverage_rows.append({"condition": condition, "outcome": outcome})
                    display_condition = condition
                    if RuleSynthesizerAgent._branch_is_unreachable(
                        chain.get("eligibility"), display_condition
                    ):
                        display_condition = (
                            f"{display_condition} [UNREACHABLE — contradicts this statement's own WHERE "
                            "clause; never executes for any row it touches]"
                        )
                    display_condition = RuleSynthesizerAgent._annotate_row_condition_with_filter(
                        display_condition, branch, chain_type
                    )
                    display_rows.append({"condition": display_condition, "outcome": outcome})
                display_fields = list(fields_in_chain.values())
                primary_field = display_fields[0]
                primary_key = _field_key(primary_field)
                if _field_is_covered(chain, primary_key, coverage_rows) or any(
                    str(rule.get("source_chain_id") or "") == str(chain.get("chain_id") or "")
                    and _rows_key(rule.get("decision_logic_rows") or []) == _rows_key(coverage_rows)
                    for rule in rules
                ):
                    for field_key, display_field in fields_in_chain.items():
                        _sanitize_covering_rule_name(chain, field_key, display_field)
                        _drop_incomplete_siblings(field_key, coverage_rows)
                    continue
                # Also treat a model rule whose conditions match (ignoring
                # row-filter annotations) as covering the ladder.
                if _repair_blank_outcome_cover(chain, primary_key, coverage_rows):
                    for field_key, display_field in fields_in_chain.items():
                        _sanitize_covering_rule_name(chain, field_key, display_field)
                        _drop_incomplete_siblings(field_key, coverage_rows)
                    continue
                synthetic_rules.append({
                    "rule_id": f"deterministic_{chain.get('chain_id') or 'chain'}_{primary_key}",
                    "source_chain_id": str(chain.get("chain_id") or ""),
                    "evidence_spans": [{"line_start": chain.get("source_line_start", -1),
                                        "line_end": chain.get("source_line_end", -1),
                                        "char_start": chain.get("source_char_start", -1),
                                        "char_end": chain.get("source_char_end", -1)}],
                    "decision_role": str(chain.get("decision_role") or "assignment"),
                    "rule_name": (
                        f"Determine {', '.join(display_fields)}"
                        if multi_field
                        else f"Determine {primary_field}"
                    ),
                    "business_meaning": "",
                    "condition": "",
                    "action": (
                        f"Sets {', '.join(display_fields)} based on the decision logic below, "
                        "reconstructed directly from the source's IF/ELSEIF/ELSE branching."
                    ),
                    "output_field": ", ".join(display_fields),
                    "eligibility": list(chain.get("eligibility") or []),
                    "decision_context": list(chain.get("decision_context") or []),
                    "execution_semantics": (
                        "Exactly one IF/ELSEIF/ELSE branch runs; branch conditions are "
                        "mutually exclusive. Row filters apply only after a branch is selected."
                    ),
                    "decision_logic": [],
                    "tie_priority_handling": [],
                    "default": [],
                    "when_not_eligible": [],
                    "fields_affected": list(display_fields),
                    "source_evidence": [],
                    "source_chunks": [],
                    "technical_references": [],
                    "unresolved_ambiguities": [],
                    "dependencies": [],
                    "decision_logic_rows": display_rows,
                    "rule_type": "deterministic_decision_table",
                    "confidence": "deterministic",
                    "validation_status": "verified",
                    "ambiguity_id": "",
                })
                continue

            fields_in_chain = OrderedDict()
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
                row_branches: List[Dict[str, Any]] = []
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
                    row_branches.append(branch)
                if len(rows) < 2:
                    continue
                # Coverage/dedup matching (`_field_is_covered`) must compare
                # against the SAME condition text a model-authored rule
                # would plausibly produce - it never invents a "row filter:
                # ..." annotation, so comparing annotated rows here would
                # make every TSQL_IF_ELSE-sourced field register as
                # "never covered" even when a model rule already matches
                # it, silently duplicating the rule. Only annotate for
                # DISPLAY, after the coverage check, using the branch each
                # row was built from (tracked alongside it, not re-derived).
                if _field_is_covered(chain, field_key, rows):
                    _sanitize_covering_rule_name(chain, field_key, display_field)
                    _drop_incomplete_siblings(field_key, rows)
                    continue
                if _repair_blank_outcome_cover(chain, field_key, rows):
                    _sanitize_covering_rule_name(chain, field_key, display_field)
                    _drop_incomplete_siblings(field_key, rows)
                    continue
                def _display_condition(row: Dict[str, Any], branch: Dict[str, Any]) -> str:
                    text = str(row["condition"])
                    if RuleSynthesizerAgent._branch_is_unreachable(chain.get("eligibility"), text):
                        text = (
                            f"{text} [UNREACHABLE — contradicts this statement's own WHERE "
                            "clause; never executes for any row it touches]"
                        )
                    return RuleSynthesizerAgent._annotate_row_condition_with_filter(
                        text, branch, chain.get("chain_type")
                    )

                rows = [
                    {**row, "condition": _display_condition(row, branch)}
                    for row, branch in zip(rows, row_branches)
                ]
                synthetic_rules.append({
                    "rule_id": f"deterministic_{chain.get('chain_id') or 'chain'}_{field_key}",
                    "source_chain_id": str(chain.get("chain_id") or ""),
                    "evidence_spans": [{"line_start": chain.get("source_line_start", -1),
                                        "line_end": chain.get("source_line_end", -1),
                                        "char_start": chain.get("source_char_start", -1),
                                        "char_end": chain.get("source_char_end", -1)}],
                    "decision_role": str(chain.get("decision_role") or "assignment"),
                    "rule_name": (f"Determine inputs to {chain['aggregation']} for {display_field}"
                                  if chain.get("aggregation") else f"Determine {display_field}"),
                    "business_meaning": (
                        f"The decision rows show per-row inputs to {chain['aggregation']}; "
                        f"{display_field} is the aggregate of those inputs over the SQL grouping."
                        if chain.get("aggregation") else ""
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
                    "validation_status": "verified",
                    "ambiguity_id": "",
                })
        return unique_rule_ids(rules + synthetic_rules)

    @staticmethod
    def _rule_has_substantive_decision(rule: Dict[str, Any]) -> bool:
        """True when a rule carries a real decision table, not just prose.

        Contentless shells (and shells that only paste a WHERE into
        `eligibility`/`condition` with empty `decision_logic_rows`) must
        not count as coverage: they block deterministic floors, then get
        CONFLICT-excluded, and the write disappears from the report
        (observed: DpdBucketAuditLog insert on DPD).
        """
        if not isinstance(rule, dict):
            return False
        if rule.get("decision_logic_rows") or rule.get("decision_block_id"):
            return True
        if rule.get("decision_rows_grounded"):
            return True
        return False

    @staticmethod
    def _rule_field_keys(rule: Dict[str, Any]) -> "set[str]":
        values = rule.get("fields_affected") or []
        if isinstance(values, str):
            values = [values]
        if not values and rule.get("output_field"):
            values = [rule["output_field"]]
        keys: "set[str]" = set()
        for value in values:
            for token in str(value or "").split(","):
                key = RuleSynthesizerAgent._bare_field_key(token)
                if key:
                    keys.add(key)
        return keys

    @staticmethod
    def _rule_targets_write_table(rule: Dict[str, Any], bare_table: str) -> bool:
        """True when the rule's *write target* is `bare_table`.

        Deliberately ignores USING/FROM mentions: a MERGE into
        DpdBucketHistory that reads `#DpdStaging` must not count as
        covering the staging INSERT itself.
        """
        if not bare_table:
            return False
        needle = bare_table.casefold().strip("#")
        for item in rule.get("decision_context") or []:
            text = str(item or "").strip()
            if text.lower().startswith("target:") and needle in text.casefold():
                return True
        name = str(rule.get("rule_name") or "").casefold()
        if needle in name and any(
            token in name
            for token in ("insert", "into", "merge", "upsert", "update", "log", "write", "record")
        ):
            return True
        output = str(rule.get("output_field") or "").casefold()
        # Model sometimes puts the target table name in output_field
        # (e.g. output_field="DpdBucketAuditLog") instead of columns.
        if output and needle == output.split(".")[-1].strip("#"):
            return True
        return False

    @staticmethod
    def _enrich_contentless_rule_from_operation(
        rule: Dict[str, Any],
        *,
        where_predicate: str,
        display_fields: List[str],
        outcome: str,
        table: str,
    ) -> None:
        """Backfill a contentless model shell from deterministic ops."""
        rule["decision_logic_rows"] = [
            {"condition": where_predicate, "outcome": outcome}
        ]
        rule["fields_affected"] = list(display_fields)
        rule["output_field"] = ", ".join(display_fields)
        if table and not any(
            str(item).lower().startswith("target:")
            for item in (rule.get("decision_context") or [])
        ):
            context = list(rule.get("decision_context") or [])
            context.insert(0, f"Target: {table}")
            rule["decision_context"] = context
        rule["rule_type"] = "deterministic_decision_table"
        rule["decision_rows_grounded"] = True
        rule["confidence"] = "deterministic"
        rule["validation_status"] = "verified"
        # Clear a stale CONFLICT/LLM_ONLY so reconciliation re-evaluates
        # against the grounded rows rather than empty model prose.
        if str(rule.get("reconciliation_status") or "").upper() in {
            "CONFLICT", "LLM_ONLY", "UNRESOLVED", ""
        }:
            rule["reconciliation_status"] = "MATCHED"

    @staticmethod
    def ensure_statement_coverage(
        rules: List[Dict[str, Any]],
        merged_extraction: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Deterministic floor for a conditional write that never branches.

        `ensure_decision_chain_coverage` above guarantees a table for every
        multi-branch CASE/IF ladder, but a single UPDATE/INSERT statement
        that assigns a literal/simple value under its own WHERE clause -
        with no ELSE, no second branch, nothing `extract_*_decision_chains`
        would ever recognize as a "chain" - has no equivalent guarantee.
        That write is a real, single-row business rule (e.g. "set
        DpdBucket to NOT_APPLICABLE where LastPaymentDueDate is null") that
        can otherwise vanish from the report entirely if the model's own
        synthesis pass happens to miss it.

        Call this last, once, after `ensure_decision_chain_coverage`
        (same call-site pattern): for every write in
        `merged_extraction["table_operations"]` with a non-empty WHERE
        predicate whose assigned column is not already documented by a
        *substantive* rule (decision rows / eligibility / condition - not
        a contentless field-name shell), synthesize a minimal one-row
        canonical rule directly from that statement's own parsed
        predicate/assignment - no LLM call, so it cannot omit or
        misdescribe the write. An assignment whose value is itself a CASE
        expression (`assigned_values[i]["case_branches"]` non-empty) is
        skipped here - that is exactly the shape `ensure_decision_chain_coverage`
        already covers, and re-synthesizing it here would create a second,
        redundant table for the same statement.

        INSERT ... SELECT ... WHERE statements are floored as one
        multi-field rule for the whole statement (not one rule per
        column): an audit/queue insert is a single business write. INSERT
        statements that already carry a CASE-valued column are left to
        the CASE coverage path (the CASE field is the decision; companion
        passthrough columns like EscalationDate = @ProcessDate are not
        separate business rules).
        """
        rules = unique_rule_ids(rules)
        table_operations = (merged_extraction or {}).get("table_operations") or []
        if not isinstance(table_operations, list) or not table_operations:
            return rules

        def _field_key(value: Any) -> str:
            return RuleSynthesizerAgent._bare_field_key(value)

        def _rebuild_covered() -> "set[str]":
            covered: "set[str]" = set()
            for rule in rules:
                if not RuleSynthesizerAgent._rule_has_substantive_decision(rule):
                    continue
                covered.update(RuleSynthesizerAgent._rule_field_keys(rule))
            for rule in synthetic_rules:
                covered.update(RuleSynthesizerAgent._rule_field_keys(rule))
            return covered

        # Spans of complete TSQL_IF_ELSE ladders: writes inside these are
        # owned by ensure_decision_chain_coverage (including companion
        # fields assigned in only one branch). Flooring them again from
        # the UPDATE's own WHERE drops the enclosing IF/ELSEIF gate and
        # invents contradictory single-branch rules.
        tsql_if_spans: List[Tuple[int, int, "set[str]"]] = []
        for chain in (merged_extraction or {}).get("decision_chains") or []:
            if not isinstance(chain, dict):
                continue
            if str(chain.get("chain_type") or "").strip().upper() != "TSQL_IF_ELSE":
                continue
            start = chain.get("source_line_start")
            end = chain.get("source_line_end")
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            if start < 0 or end < 0:
                continue
            fields: "set[str]" = set()
            for branch in chain.get("branches") or []:
                if not isinstance(branch, dict):
                    continue
                for assignment in branch.get("assignments") or []:
                    if isinstance(assignment, dict):
                        key = _field_key(assignment.get("field"))
                        if key:
                            fields.add(key)
            tsql_if_spans.append((start, end, fields))

        def _owned_by_tsql_if_ladder(row: Dict[str, Any]) -> bool:
            line = row.get("source_line_start")
            if not isinstance(line, int) or line < 0:
                return False
            for start, end, _fields in tsql_if_spans:
                if start <= line <= end:
                    return True
            return False

        def _condition_with_control_flow(row: Dict[str, Any], where_predicate: str) -> str:
            """Prefixed enclosing IF gate when statement coverage still floors.

            Used for single-IF wrappers that never became a multi-branch
            TSQL_IF_ELSE chain, or ops annotated with control_flow by the
            parser. Never invents gates - only uses explicit annotations.
            """
            control = row.get("control_flow") or row.get("control_flow_predicates") or []
            gates: List[str] = []
            if isinstance(control, list):
                for item in control:
                    if isinstance(item, dict):
                        text = str(item.get("condition") or item.get("predicate") or "").strip()
                    else:
                        text = str(item or "").strip()
                    if text:
                        gates.append(text)
            elif isinstance(control, str) and control.strip():
                gates.append(control.strip())
            gate = str(row.get("control_flow_gate") or "").strip()
            if gate:
                gates.append(gate)
            # Deduplicate while preserving order
            seen: "set[str]" = set()
            unique_gates: List[str] = []
            for text in gates:
                key = text.casefold()
                if key in seen:
                    continue
                seen.add(key)
                unique_gates.append(text)
            if not unique_gates:
                return where_predicate
            gate_text = " AND ".join(unique_gates)
            if where_predicate:
                return f"{gate_text} — row filter: {where_predicate}"
            return gate_text

        # Same process-bookkeeping signal `_remove_operational_status_rules`
        # uses - this floor exists to surface real business decisions, not
        # to manufacture a rule for every RUNNINGPROCESSSTATUS audit write.
        status_tables = {
            str(row.get("table") or "").strip().split(".")[-1].strip("#").casefold()
            for row in table_operations
            if isinstance(row, dict)
            and "runningprocessstatus" in str(row.get("table") or "").lower()
        }

        synthetic_rules: List[Dict[str, Any]] = []
        seen_statement_fields: "set[Tuple[str, str]]" = set()
        seen_insert_statements: "set[str]" = set()
        case_insert_tables: "set[str]" = set()
        covered_fields = _rebuild_covered()

        def _make_synthetic(
            *,
            row: Dict[str, Any],
            statement_id: str,
            field_key: str,
            display_fields: List[str],
            where_predicate: str,
            outcome: str,
            rule_name: str,
        ) -> Dict[str, Any]:
            return {
                "rule_id": f"deterministic_statement_{statement_id or 'stmt'}_{field_key}",
                "source_statement_id": statement_id,
                "evidence_spans": [{
                    "line_start": row.get("source_line_start", -1),
                    "line_end": row.get("source_line_end", -1),
                    "char_start": row.get("source_char_start", -1),
                    "char_end": row.get("source_char_end", -1),
                }],
                "decision_role": "assignment",
                "rule_name": rule_name,
                "business_meaning": "",
                "condition": "",
                "action": (
                    f"Sets {', '.join(display_fields)} based on the condition below, "
                    "reconstructed directly from this statement's own WHERE clause."
                ),
                "output_field": ", ".join(display_fields),
                "eligibility": [],
                "decision_context": (
                    [f"Target: {row.get('table')}"] if row.get("table") else []
                ),
                "execution_semantics": "",
                "decision_logic": [],
                "tie_priority_handling": [],
                "default": [],
                "when_not_eligible": [],
                "fields_affected": list(display_fields),
                "source_evidence": [],
                "source_chunks": [row.get("source_chunk_id")] if row.get("source_chunk_id") else [],
                "technical_references": [],
                "unresolved_ambiguities": [],
                "dependencies": [],
                "decision_logic_rows": [{"condition": where_predicate, "outcome": outcome}],
                "rule_type": "deterministic_decision_table",
                "decision_rows_grounded": True,
                "confidence": "deterministic",
                "validation_status": "verified",
                "ambiguity_id": "",
            }

        for row in table_operations:
            if not isinstance(row, dict) or row.get("operation") not in ("UPDATE", "INSERT"):
                continue
            # Nested under a complete IF/ELSEIF/ELSE ladder → chain coverage.
            if _owned_by_tsql_if_ladder(row):
                continue
            table = str(row.get("table") or "").strip()
            bare_table = table.split(".")[-1].strip("#").casefold()
            if bare_table and bare_table in status_tables:
                continue
            where_predicate = str(row.get("where_predicate") or "").strip()
            where_predicate = _condition_with_control_flow(row, where_predicate)
            if not where_predicate:
                continue
            statement_id = str(row.get("source_statement_id") or row.get("statement_id") or "")
            assignments = [
                item for item in (row.get("assigned_values") or [])
                if isinstance(item, dict)
            ]
            if not assignments:
                continue

            if row.get("operation") == "INSERT":
                has_case = any(
                    item.get("case_branches")
                    or re.search(
                        r"(?i)\bCASE\b", str(item.get("expression") or "")
                    )
                    for item in assignments
                )
                # CASE-valued INSERT columns are owned by decision-chain
                # coverage (e.g. CollectionsQueue.Reason). Companion
                # passthrough columns on the same INSERT are not separate
                # business rules.
                if has_case:
                    if bare_table:
                        case_insert_tables.add(bare_table)
                    continue
                simple = [
                    item for item in assignments
                    if not item.get("case_branches")
                    and not re.search(
                        r"(?i)\bCASE\b", str(item.get("expression") or "")
                    )
                    and str(item.get("column") or "").strip()
                    and str(item.get("expression") or "").strip()
                ]
                if not simple:
                    continue
                # Dedupe by table+WHERE: deterministic + LLM table_operations
                # often both describe the same INSERT with different ids.
                insert_key = f"{bare_table}|{where_predicate.casefold()}"
                if insert_key in seen_insert_statements:
                    continue
                display_fields = [
                    str(item.get("column") or "").split(".")[-1].strip()
                    for item in simple
                ]
                field_keys = [_field_key(name) for name in display_fields if name]
                # Skip only when every column is already documented by a
                # substantive rule that *targets* this same insert table
                # (global field coverage alone is wrong: AccountId on a
                # MERGE must not suppress an audit INSERT of AccountId;
                # USING #temp mentions must not suppress the temp INSERT).
                if field_keys and all(
                    any(
                        RuleSynthesizerAgent._rule_has_substantive_decision(rule)
                        and _field_key(name) in RuleSynthesizerAgent._rule_field_keys(rule)
                        and RuleSynthesizerAgent._rule_targets_write_table(rule, bare_table)
                        for rule in list(rules) + synthetic_rules
                    )
                    for name in display_fields
                    if _field_key(name)
                ):
                    seen_insert_statements.add(insert_key)
                    continue
                seen_insert_statements.add(insert_key)
                outcome_parts = [
                    f"{str(item.get('column') or '').split('.')[-1].strip()} := "
                    f"{str(item.get('expression') or '').strip()}"
                    for item in simple
                ]
                outcome = (
                    outcome_parts[0]
                    if len(outcome_parts) == 1
                    else "; ".join(outcome_parts)
                )
                # Prefer enriching the model's own shell (keeps its title)
                # over adding a parallel synthetic that then fights the
                # shell through CONFLICT exclusion.
                shell = next(
                    (
                        rule for rule in rules
                        if not RuleSynthesizerAgent._rule_has_substantive_decision(rule)
                        and RuleSynthesizerAgent._rule_targets_write_table(rule, bare_table)
                    ),
                    None,
                )
                if shell is not None:
                    RuleSynthesizerAgent._enrich_contentless_rule_from_operation(
                        shell,
                        where_predicate=where_predicate,
                        display_fields=display_fields,
                        outcome=outcome,
                        table=table,
                    )
                    for key in field_keys:
                        covered_fields.add(key)
                        seen_statement_fields.add((statement_id, key))
                    continue
                short_table = table.split(".")[-1] if table else "rows"
                synthetic_rules.append(
                    _make_synthetic(
                        row=row,
                        statement_id=statement_id,
                        field_key=field_keys[0] if field_keys else "insert",
                        display_fields=display_fields,
                        where_predicate=where_predicate,
                        outcome=outcome,
                        rule_name=f"Insert into {short_table}",
                    )
                )
                for key in field_keys:
                    covered_fields.add(key)
                    seen_statement_fields.add((statement_id, key))
                continue

            for assignment in assignments:
                if assignment.get("case_branches"):
                    continue
                column = str(assignment.get("column") or "").strip()
                expression = str(assignment.get("expression") or "").strip()
                field_key = _field_key(column)
                if not field_key or not expression or field_key in covered_fields:
                    continue
                dedupe_key = (statement_id, field_key)
                if dedupe_key in seen_statement_fields:
                    continue
                seen_statement_fields.add(dedupe_key)
                covered_fields.add(field_key)
                display_field = column.split(".")[-1].strip() or column
                synthetic_rules.append(
                    _make_synthetic(
                        row=row,
                        statement_id=statement_id,
                        field_key=field_key,
                        display_fields=[display_field],
                        where_predicate=where_predicate,
                        outcome=expression,
                        rule_name=f"Determine {display_field}",
                    )
                )

        # MERGE floor: per-branch (WHEN MATCHED / WHEN NOT MATCHED BY
        # TARGET / WHEN NOT MATCHED BY SOURCE) coverage from
        # `assigned_values`' `merge_branch`-tagged entries (see
        # `_render_merge_assigned_values` in technical_sql_ops.py).
        # Historically a MERGE operation record always carried
        # `assigned_values=[]`, so no column of a MERGE statement had any
        # deterministic backstop - the model had to independently author a
        # rule for every SET column, and routinely missed one (observed:
        # AdjustedPenalty silently absent from a MERGE's WHEN MATCHED
        # UPDATE while DpdBucket/LastUpdatedDate were both covered).
        #
        # One synthetic rule PER MISSING COLUMN (not one per branch) -
        # deliberately mirrors the plain-UPDATE floor above rather than
        # combining a branch's columns into one rule here, so that
        # `_collapse_merge_upsert_halves` (report_formatter.py /
        # rule_shape.py), which already knows how to fold same-table
        # per-column MATCHED fragments into one upsert rule, does that
        # combining exactly once in one place - a model-authored fragment
        # for the same branch and a deterministic one for the column it
        # missed end up in the very same collapse group instead of two
        # competing partial upserts.
        #
        # The condition text literally includes the branch's own SQL
        # keyword (`WHEN MATCHED` / `WHEN NOT MATCHED BY TARGET` / `WHEN
        # NOT MATCHED BY SOURCE`) followed by the MERGE's own ON predicate
        # (and that WHEN's own extra condition, if any) - grounded
        # directly in the parsed SQL, not invented, and exactly the marker
        # `_collapse_merge_upsert_halves`'s matched/unmatched classifier
        # already recognizes.
        # A field name (e.g. `AdjustedPenalty`) can legitimately be
        # assigned by MORE THAN ONE branch of the SAME MERGE targeting the
        # SAME table - once on the MATCHED/UPDATE side, once again on the
        # NOT MATCHED/INSERT side - so the plain (table, field) scoping
        # `_rule_targets_write_table` gives the INSERT floor above is not
        # enough here: an existing rule documenting the INSERT half's
        # AdjustedPenalty must never be mistaken for covering the UPDATE
        # half's AdjustedPenalty too. Classify each candidate EXISTING
        # rule's own text (same MATCHED/NOT-MATCHED regex
        # `_collapse_merge_upsert_halves` uses, shared via
        # `alias_resolution` so both sides agree) and only treat a field
        # as covered when an existing, substantive, same-table rule
        # classifies to the SAME branch side. A rule that can't be
        # classified either way is treated conservatively as covering the
        # field (never risk inventing a duplicate when the branch can't be
        # determined).
        def _merge_field_covered(bare_table: str, branch_is_matched: bool, field_key: str) -> bool:
            for candidate in list(rules) + synthetic_rules:
                if not isinstance(candidate, dict):
                    continue
                if not RuleSynthesizerAgent._rule_has_substantive_decision(candidate):
                    continue
                if not RuleSynthesizerAgent._rule_targets_write_table(candidate, bare_table):
                    continue
                if field_key not in RuleSynthesizerAgent._rule_field_keys(candidate):
                    continue
                blob_parts = [
                    str(candidate.get("rule_name") or ""),
                    str(candidate.get("business_meaning") or ""),
                    str(candidate.get("condition") or ""),
                    str(candidate.get("action") or ""),
                    " ".join(str(x) for x in (candidate.get("eligibility") or [])),
                    " ".join(str(x) for x in (candidate.get("decision_context") or [])),
                ]
                for logic_row in candidate.get("decision_logic_rows") or []:
                    if isinstance(logic_row, dict):
                        blob_parts.append(str(logic_row.get("condition") or ""))
                        blob_parts.append(str(logic_row.get("outcome") or ""))
                blob = " ".join(blob_parts).casefold()
                candidate_matched = _alias_resolution.merge_branch_text_is_matched(blob)
                candidate_unmatched = _alias_resolution.merge_branch_text_is_unmatched(blob)
                if candidate_matched == candidate_unmatched:
                    return True
                if candidate_matched == branch_is_matched:
                    return True
            return False

        for row in table_operations:
            if not isinstance(row, dict) or row.get("operation") != "MERGE":
                continue
            if _owned_by_tsql_if_ladder(row):
                continue
            table = str(row.get("table") or "").strip()
            bare_table = table.split(".")[-1].strip("#").casefold()
            if bare_table and bare_table in status_tables:
                continue
            on_predicate = str(row.get("merge_on_predicate") or "").strip()
            statement_id = str(row.get("source_statement_id") or row.get("statement_id") or "")
            by_branch: Dict[str, List[Dict[str, Any]]] = {}
            for item in row.get("assigned_values") or []:
                if not isinstance(item, dict):
                    continue
                branch = str(item.get("merge_branch") or "").strip()
                if branch:
                    by_branch.setdefault(branch, []).append(item)
            branch_labels = {
                "MATCHED": "WHEN MATCHED",
                "NOT_MATCHED_BY_TARGET": "WHEN NOT MATCHED BY TARGET",
                "NOT_MATCHED_BY_SOURCE": "WHEN NOT MATCHED BY SOURCE",
            }
            for branch, items in by_branch.items():
                label = branch_labels.get(branch, branch)
                branch_condition = f"{label}: {on_predicate}" if on_predicate else label
                branch_is_matched = branch == "MATCHED"
                for item in items:
                    if item.get("case_branches") or re.search(
                        r"(?i)\bCASE\b", str(item.get("expression") or "")
                    ):
                        # CASE-valued MERGE assignments are owned by
                        # decision-chain coverage, same as CASE-valued
                        # INSERT columns above.
                        continue
                    when_condition = str(item.get("merge_condition") or "").strip()
                    full_condition = (
                        f"{branch_condition} AND {when_condition}"
                        if when_condition else branch_condition
                    )
                    column = str(item.get("column") or "").strip()
                    expression = str(item.get("expression") or "").strip()
                    field_key = _field_key(column)
                    if not field_key or not expression:
                        continue
                    dedupe_key = (f"{statement_id}:{branch}", field_key)
                    if dedupe_key in seen_statement_fields:
                        continue
                    if _merge_field_covered(bare_table, branch_is_matched, field_key):
                        seen_statement_fields.add(dedupe_key)
                        continue
                    seen_statement_fields.add(dedupe_key)
                    display_field = column.split(".")[-1].strip() or column
                    synthetic_rules.append(
                        _make_synthetic(
                            row=row,
                            statement_id=f"{statement_id}:{branch}",
                            field_key=field_key,
                            display_fields=[display_field],
                            where_predicate=full_condition,
                            outcome=expression,
                            rule_name=f"Determine {display_field}",
                        )
                    )

        combined = unique_rule_ids(rules + synthetic_rules)
        # Drop contentless shells whose fields are now fully documented by
        # substantive rules (deterministic floors or real model tables).
        # This removes "Reset BucketWorsened" / empty audit shells that
        # would otherwise survive as noise next to the real ladder/floor.
        substantive_fields: "set[str]" = set()
        for rule in combined:
            if RuleSynthesizerAgent._rule_has_substantive_decision(rule):
                substantive_fields.update(RuleSynthesizerAgent._rule_field_keys(rule))
        pruned: List[Dict[str, Any]] = []
        for rule in combined:
            if RuleSynthesizerAgent._rule_has_substantive_decision(rule):
                pruned.append(rule)
                continue
            # Contentless shell for an INSERT whose business decision is a
            # CASE column already floored by decision-chain coverage.
            if any(
                RuleSynthesizerAgent._rule_targets_write_table(rule, table)
                for table in case_insert_tables
            ):
                continue
            fields = RuleSynthesizerAgent._rule_field_keys(rule)
            if fields and fields <= substantive_fields:
                continue
            pruned.append(rule)
        return unique_rule_ids(pruned)

    @staticmethod
    def _scan_for_jargon(data: Dict[str, Any]) -> List[str]:
        flat_text = json.dumps(data).lower()
        return [term for term in _BANNED_TERMS if term in flat_text]