"""
pipeline.py
------------
Central orchestrator (`LogicRulesExtractorPipeline`) that wires together
the guardrail layer, dialect detection, and the five agents into the
end-to-end flow:

    Input -> Input Guardrails -> Dialect Detection -> Preprocessing
    (Code Ingestion Agent: comment/string masking, batch splitting,
    embedded-SQL extraction) -> Pattern Retrieval (RAG) -> Logic
    Extraction (+ per-chunk output guardrails) -> Rule Synthesis
    (+ output guardrails) -> Report Formatting -> Final Output

This orchestration is plain Python - there is no agent framework
involved. "Running the pipeline" just means calling each stage's
methods in order and passing data between them via ordinary Python
objects/dicts.

The LLM configuration is loaded from environment variables so the
provider, API key, model, and base URL can all be changed without code
changes. A single OpenAI-compatible client is created once and shared by
both LLM-calling agents.
"""

from __future__ import annotations

import os
import logging
import time
import copy
import hashlib
import json
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.ingestion.ingestion import (
    MAX_CHUNK_CHARS,
    CodeIngestionAgent,
    IngestionResult,
    build_object_identity_stem,
)
from src.retrieval.retriever import PatternRetrievalAgent
from src.extraction.logic_extractor import LogicExtractionAgent, ChunkExtraction
from src.synthesis.rule_synthesizer import (
    RuleSynthesizerAgent,
    SynthesisResult,
    rule_identity_key,
    PromptTooLargeForRateLimitError,
)
from src.synthesis.rule_shape import finalize_business_rule_shape
from src.output.report_formatter import ReportFormatterAgent
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks, split_table_operations
from src.parsing.calculations import calculations_from_operations
from src.parsing.process_gates import extract_process_gates, summarize_process_gates
from src.parsing.alias_resolution import (
    resolve_aliases_in_business_rules,
    resolve_aliases_in_merged_extraction,
)
from src.ingestion.guardrails import InputGuardrailError, run_input_guardrails, strip_inactive_code_for_llm
from src.dialect.detector import UnsupportedDialectError, detect_dialect
from src.core.llm_client import LLMConfig, create_llm_client, load_llm_config, resolve_model_output_ceiling
from src.core.llm_response_cache import PersistentLLMResponseCache
from src.validation.confidence import derive_chunk_support_confidence
from src.validation.reconciliation import reconcile_deterministic_evidence
from src.validation.semantic_validation import (
    extract_procedural_decision_chains,
    extract_nested_decision_chains,
    extract_case_assignment_decision_chains,
    extract_tsql_if_elseif_chains,
    merge_decision_chains,
    find_semantic_anomalies,
    find_exception_handler_spans,
)
from src.validation.coverage_check import (
    build_completeness_ledger,
    find_coverage_gaps,
    format_gap_for_ambiguity,
    format_consolidated_gap_ambiguity,
)
from src.validation.dependencies import build_statement_dependencies
from src.ir.canonical_ir import CanonicalBusinessIR
from src.core.pipeline_utils import (
    PIPELINE_VERSION,
    RunMetadata,
    attach_run_telemetry,
    build_run_metadata,
    run_metadata_to_dict,
    stable_id,
)
from src.telemetry.tracker import LLMTelemetryTracker

logger = logging.getLogger("logic_rules_extractor.pipeline")

DEFAULT_TEMPERATURE = 0.1  # low-temperature extraction / synthesis task
DEFAULT_SEED = 0
# Explicit output-token ceilings for every LLM call. These MUST be passed
# explicitly rather than relying on provider defaults: the OpenAI client
# defaults to a large ceiling when omitted, but the Bedrock-backed client
# (`_BedrockChatCompletions.create` in src/core/llm_client.py) defaults its
# own `max_tokens` to 1024 when the caller doesn't pass one - silently
# truncating extraction/synthesis JSON well before it's complete for any
# object of realistic size (a single stored procedure's synthesis call can
# need ~15-20K completion tokens). Truncated JSON then fails validation and
# the pipeline falls back to a degraded result with no obvious root cause.
# Override via LLM_EXTRACTION_MAX_TOKENS / LLM_SYNTHESIS_MAX_TOKENS if a
# particular model/provider needs a different ceiling.
DEFAULT_EXTRACTION_MAX_TOKENS = int(os.environ.get("LLM_EXTRACTION_MAX_TOKENS", "6000"))
DEFAULT_SYNTHESIS_MAX_TOKENS = int(os.environ.get("LLM_SYNTHESIS_MAX_TOKENS", "16000"))

# The single-pass selector is intentionally based on the configured context
# window, not equal to it. The selector reserves prompt/schema space, but does
# not reserve the entire worst-case completion ceiling: the extraction call
# already sizes its output adaptively and detects/retries truncation. This
# keeps input-sized objects from being routed to chunking solely because a
# theoretical maximum completion was reserved up front.
_DEFAULT_PROMPT_SCHEMA_RESERVE = 3000
_DEFAULT_MODEL_CONTEXT_WINDOW = int(os.environ.get("LLM_CONTEXT_WINDOW", "32768"))
SINGLE_PASS_TOKEN_BUDGET = int(
    os.environ.get(
        "SINGLE_PASS_TOKEN_BUDGET",
        str(
            max(
                4096,
                _DEFAULT_MODEL_CONTEXT_WINDOW - _DEFAULT_PROMPT_SCHEMA_RESERVE,
            )
        ),
    )
)

# Stage 4 (embedded SQL / per-chunk technical extraction) is the slowest
# stage because it makes one LLM call per chunk. Chunks are independent, so
# they're extracted concurrently; 4 workers was overly conservative for
# typical stored-procedure sizes (10-60 chunks) and left most of the run
# serialized. Bump the out-of-the-box default and let PIPELINE_CHUNK_WORKERS
# override it per environment (e.g. lower it back down if the LLM provider's
# rate limit needs it).
DEFAULT_CHUNK_WORKERS = 8

# Bounded number of model-driven review passes the coverage-gap loop may
# trigger after the first synthesis call (see `find_coverage_gaps` /
# `RuleSynthesizerAgent.revise`). Kept small and bounded on purpose: a
# gap that's still unresolved after this many targeted look-backs is far
# more likely genuinely ambiguous/technical than something more retries
# would fix, and should surface as a reviewable ambiguity instead of
# looping. Override via PIPELINE_COVERAGE_RETRIES per environment.
DEFAULT_COVERAGE_RETRIES = int(os.environ.get("PIPELINE_COVERAGE_RETRIES", "2"))


def supported_analysis_dialect(ingestion: IngestionResult) -> Optional[str]:
    dialect = (ingestion.concrete_dialect or ingestion.fallback_dialect or ingestion.dialect or "").strip().lower()
    if dialect in {"oracle", "tsql"}:
        return dialect
    return None


def _extract_deterministic_decision_chains(source: str, dialect: str = "tsql") -> List[Dict[str, Any]]:
    """Run every deterministic chain extractor before canonical merging.

    The extractors cover complementary procedural shapes.  In particular,
    nested extraction must not suppress the flat PL/SQL ladder extractor;
    ``merge_decision_chains`` remains the single deduplication boundary.
    """
    from src.parsing.decision_tables import enrich_decision_tables
    # `extract_nested_decision_chains`/`extract_procedural_decision_chains`
    # only recognize Oracle PL/SQL's IF...THEN/ELSIF...THEN/END IF syntax
    # (see their docstrings) and never match T-SQL's IF/ELSE IF/ELSE/bare
    # END - so a T-SQL source needs its own syntax-aware extractor or its
    # procedural IF ladders have zero deterministic decision-chain coverage
    # at all, regardless of how much real business logic they contain.
    tsql_chains = extract_tsql_if_elseif_chains(source) if str(dialect or "").strip().lower() == "tsql" else []
    chains = merge_decision_chains(
        extract_case_assignment_decision_chains(source),
        extract_nested_decision_chains(source),
        extract_procedural_decision_chains(source),
        tsql_chains,
    )
    return enrich_decision_tables(source, chains, dialect=dialect)


def _ranges_overlap(left_start: Any, left_end: Any, right_start: Any, right_end: Any) -> bool:
    try:
        left_start, left_end = int(left_start), int(left_end)
        right_start, right_end = int(right_start), int(right_end)
    except (TypeError, ValueError):
        return False
    if min(left_start, left_end, right_start, right_end) < 0:
        return False
    return not (left_end <= right_start or right_end <= left_start)


_TRUNCATION_AMBIGUITY_MARKER = "exceeded the model's maximum"


def _merge_into_truncation_ambiguity(container: Dict[str, Any], gap_summary: str) -> bool:
    """Fold a consolidated coverage-gap summary into the existing
    truncation ambiguity string (identified by its stable marker phrase)
    instead of appending it as a second, separate bullet. Keeps the
    truncation cause and its affected line ranges as one report item.

    Returns True when an existing truncation ambiguity was found and
    merged in place, False when this container had no such ambiguity to
    merge into. Callers that invoke this on more than one container (e.g.
    both `merged_extraction` and `synthesis.data`) must check this return
    value before falling back to a standalone append in the other
    container - `_findings_section` unions ambiguities from every
    container without deduplicating near-identical text, so unconditionally
    appending `gap_summary` on its own to a container that has no marker,
    right after successfully merging the same summary into another
    container's marker, produces two findings bullets (one standalone, one
    combined) describing the exact same truncation instead of one.
    """
    ambiguities = list(container.get("ambiguities", []) or [])
    for index, item in enumerate(ambiguities):
        if _TRUNCATION_AMBIGUITY_MARKER in str(item):
            ambiguities[index] = f"{str(item).rstrip()} {gap_summary}"
            container["ambiguities"] = ambiguities
            return True
    return False


def _exclude_exception_handler_calculations(
    calculations: List[Dict[str, Any]], raw_source: str, handler_spans: List[Tuple[int, int]]
) -> List[Dict[str, Any]]:
    """Drop any calculation whose own source text falls inside one of
    `handler_spans` (an exception/error-handler block body - see
    `find_exception_handler_spans`). Matched by substring against the
    handler block's own source text, using the calculation's captured
    `source_evidence` (the exact originating statement text, when
    present) or else its `expression`/`formula` text - never by field
    name, so this generalizes to any status/bookkeeping table without
    hardcoding one.
    """
    if not handler_spans or not calculations:
        return calculations
    handler_texts = [raw_source[start:end] for start, end in handler_spans]
    filtered: List[Dict[str, Any]] = []
    for calc in calculations:
        if not isinstance(calc, dict):
            filtered.append(calc)
            continue
        evidence = [str(item).strip() for item in (calc.get("source_evidence") or []) if str(item).strip()]
        expression = str(calc.get("expression") or calc.get("formula") or "").strip()
        needles = evidence or ([expression] if expression else [])
        if needles and any(
            needle in handler_text for needle in needles for handler_text in handler_texts
        ):
            continue
        filtered.append(calc)
    return filtered


def _mark_rules_degraded_if_unreliable(result: "SynthesisResult") -> "SynthesisResult":
    """Stamp `degraded: True` onto every business rule a synthesis call
    (single-call or one section) returned, when that specific call's own
    response was truncated (`finish_reason == "length"`) or the call
    itself is flagged as having failed (`synthesis_failed`). This is the
    per-call granularity available today - no `business_rule` dict carries
    a source line range or chunk id, so a reader sees "this rule came from
    an unreliable pass" rather than nothing beyond the existing run-level
    footer, but not exactly which lines within that pass are suspect.

    `RuleSynthesizerAgent.consolidate_duplicate_rules` (called once, after
    every synthesis/revision call has finished) relies on this: when two
    candidates for the same decision merge, only the *kept* (narrowest)
    candidate's own `degraded` value survives - so a clean rule that
    happens to have a noisier duplicate is never shown as degraded just
    because that duplicate existed.
    """
    truncated = getattr(result, "truncated", False)
    synthesis_failed = getattr(result, "synthesis_failed", False)
    if not (truncated or synthesis_failed):
        return result
    reason = "synthesis_failed" if synthesis_failed else "truncated"
    rules = result.data.get("business_rules") if isinstance(result.data, dict) else None
    for rule in rules or []:
        if isinstance(rule, dict):
            rule["degraded"] = True
            rule["degraded_reason"] = reason
    return result


def _annotate_decision_chain_provenance(
    merged_extraction: Dict[str, Any], ingestion: IngestionResult
) -> None:
    """Join extracted branch spans to existing chunks and statements.

    Only exact character/line overlap is used. Missing offsets remain missing;
    a chunk or statement is never assigned merely because it is nearby.
    """
    chains = merged_extraction.get("decision_chains") or []
    if not isinstance(chains, list):
        return
    chunks = list(getattr(ingestion, "chunks", []) or [])
    statements = list(merged_extraction.get("statement_provenance") or [])

    def overlaps(item: Any, span: Dict[str, Any]) -> bool:
        if not isinstance(item, dict):
            start = getattr(item, "source_char_start", -1)
            end = getattr(item, "source_char_end", -1)
            line_start = getattr(item, "source_line_start", -1)
            line_end = getattr(item, "source_line_end", -1)
        else:
            start = item.get("source_char_start", item.get("char_start", -1))
            end = item.get("source_char_end", item.get("char_end", -1))
            line_start = item.get("source_line_start", item.get("line_start", -1))
            line_end = item.get("source_line_end", item.get("line_end", -1))
        if _ranges_overlap(span.get("char_start", -1), span.get("char_end", -1), start, end):
            return True
        try:
            return (
                int(span.get("line_start", -1)) > 0
                and int(line_start) > 0
                and int(span.get("line_end", -1)) >= int(line_start)
                and int(line_end) >= int(span.get("line_start", -1))
            )
        except (TypeError, ValueError):
            return False

    for chain_index, chain in enumerate(chains, start=1):
        if not isinstance(chain, dict):
            continue
        chain_id = str(chain.get("chain_id") or f"decision_chain_{chain_index:03d}").strip()
        chain["chain_id"] = chain_id
        source_identifier = str(
            getattr(ingestion, "source_filename", "") or getattr(ingestion, "object_id", "") or ""
        ).strip()
        if source_identifier:
            chain["source_identifier"] = source_identifier
        for branch_index, branch in enumerate(chain.get("branches") or [], start=1):
            if not isinstance(branch, dict):
                continue
            branch_id = str(branch.get("branch_id") or f"{chain_id}:branch_{branch_index:03d}").strip()
            branch["chain_id"] = chain_id
            branch["branch_id"] = branch_id
            spans = [dict(span) for span in branch.get("evidence_spans", []) if isinstance(span, dict)]
            if not spans:
                spans = [
                    {
                        "char_start": branch.get("source_char_start", -1),
                        "char_end": branch.get("source_char_end", -1),
                        "line_start": branch.get("source_line_start", -1),
                        "line_end": branch.get("source_line_end", -1),
                        "source_location_status": branch.get("source_location_status", "unavailable"),
                    }
                ]
            enriched_spans = []
            for span in spans:
                span["chain_id"] = chain_id
                span["branch_id"] = branch_id
                if source_identifier:
                    span.setdefault("source_identifier", source_identifier)
                matching_chunks = [chunk for chunk in chunks if overlaps(chunk, span)]
                matching_statements = [statement for statement in statements if overlaps(statement, span)]
                if matching_chunks:
                    span.setdefault("source_file", getattr(matching_chunks[0], "source_filename", ""))
                    span["chunk_id"] = getattr(matching_chunks[0], "chunk_id", "")
                if matching_statements:
                    statement = matching_statements[0]
                    span["statement_id"] = str(
                        statement.get("statement_id") or statement.get("source_statement_id") or ""
                    )
                    span.setdefault("source_file", statement.get("source_file", ""))
                enriched_spans.append(span)
            primary = enriched_spans[0]
            branch["evidence_spans"] = enriched_spans
            branch["source_char_start"] = primary.get("char_start", -1)
            branch["source_char_end"] = primary.get("char_end", -1)
            branch["source_line_start"] = primary.get("line_start", -1)
            branch["source_line_end"] = primary.get("line_end", -1)
            branch["source_location_status"] = primary.get("source_location_status", "unavailable")
            if source_identifier:
                branch["source_identifier"] = source_identifier
            if primary.get("source_file"):
                branch["source_file"] = primary["source_file"]
            if primary.get("chunk_id"):
                branch["source_chunk_id"] = primary["chunk_id"]
            if primary.get("statement_id"):
                branch["source_statement_id"] = primary["statement_id"]


class PipelineInputError(ValueError):
    """Raised when the input source cannot be safely processed at all
    (fails input guardrails before any parsing or LLM call is made).
    """


@dataclass
class PipelineRunResult:
    """Everything a caller (CLI, Streamlit app, tests) needs from one
    pipeline run.

    `report` is the clean, business-facing Markdown document.
    `verification_report` is the traceability diagnostic (source provenance,
    rule IDs, reconciliation, run metadata) that does not appear in
    `report`. CLI and batch entry points persist it as a matching artifact
    under an output/verification directory and also emit it to the run log.
    `ingestion` carries the parsed object
    identity (`object_name`, `canonical_object_name`, `schema`,
    `object_type`) so callers can derive output filenames from what the
    SQL actually declares rather than from the input filename - see
    `src.ingestion.ingestion.build_object_identity_stem`.

    Kept as a small dataclass (rather than a bare string) so the business
    report and diagnostic output cannot be accidentally conflated.
    """

    report: str
    verification_report: str
    ingestion: IngestionResult


class LogicRulesExtractorPipeline:
    """End-to-end coordinator for the AI-Powered DB Logic & Business
    Rules Extractor.
    """

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        seed: Optional[int] = DEFAULT_SEED,
        persist_directory: str = "chroma_store",
        knowledge_base_dir: str = "knowledge_base",
        max_chunk_chars: int = MAX_CHUNK_CHARS,
        retrieval_k: int = 4,
        chunk_workers: Optional[int] = None,
        dialect: str = "auto",
        extraction_max_tokens: int = DEFAULT_EXTRACTION_MAX_TOKENS,
        synthesis_max_tokens: int = DEFAULT_SYNTHESIS_MAX_TOKENS,
        max_coverage_retries: int = DEFAULT_COVERAGE_RETRIES,
        single_pass_token_budget: Optional[int] = None,
        response_cache_enabled: Optional[bool] = None,
    ):
        self.llm_config = llm_config or load_llm_config()
        self.max_coverage_retries = max_coverage_retries
        configured_budget = os.environ.get("SINGLE_PASS_TOKEN_BUDGET")
        model_context_window = int(getattr(self.llm_config, "context_window", _DEFAULT_MODEL_CONTEXT_WINDOW))
        self.single_pass_token_budget = int(
            configured_budget
            if configured_budget is not None
            else (
                single_pass_token_budget
                if single_pass_token_budget is not None
                else max(4096, model_context_window - _DEFAULT_PROMPT_SCHEMA_RESERVE)
            )
        )
        self.model_name = self.llm_config.model_name
        self.retrieval_k = retrieval_k
        self.chunk_workers = self._resolve_chunk_workers(chunk_workers)
        self.dialect = dialect
        self.seed = seed
        self.project_root = Path(__file__).resolve().parent
        self.pipeline_version = PIPELINE_VERSION
        self.provider = self.llm_config.provider
        # Persistent response caching stays opt-in for the interactive
        # application (app.py never passes `response_cache_enabled`, so it
        # keeps making fresh calls run to run). Batch/dev iteration is where
        # the cache earns its keep - re-running the same set of procedures
        # after a prompt or logic tweak shouldn't re-cost the full LLM spend
        # every time - so callers doing that (the CLI's `--cache` flag,
        # `evaluate.py`, or any other batch/dev entry point) can pass
        # `response_cache_enabled=True` explicitly, or set the
        # `LLM_RESPONSE_CACHE_ENABLED` environment variable, which
        # `PersistentLLMResponseCache` itself falls back to when this
        # constructor argument is left as `None`.
        self.response_cache = PersistentLLMResponseCache(enabled=response_cache_enabled)
        self.client = create_llm_client(self.llm_config)
        # The real, server-enforced maximum completion tokens for this
        # provider/model (e.g. 5000 for Amazon Nova Lite on Bedrock), when
        # known - see `resolve_model_output_ceiling`. Both LLM-calling agents
        # MUST size their single-pass/sectioning/retry budgets against this,
        # not the generic 32768 default: a budget computed against a ceiling
        # larger than what the model will actually return under-triggers
        # sectioning and produces sections still too big to complete,
        # guaranteeing truncated JSON no matter how a caller retries.
        self.model_output_ceiling = resolve_model_output_ceiling(self.provider, self.model_name)

        self.ingestion_agent = CodeIngestionAgent(max_chunk_chars=max_chunk_chars, dialect=dialect)
        self.retrieval_agent = PatternRetrievalAgent(
            persist_directory=persist_directory,
            knowledge_base_dir=knowledge_base_dir,
        )
        self.extraction_agent = LogicExtractionAgent(
            client=self.client,
            model=self.model_name,
            temperature=temperature,
            seed=seed,
            provider=self.provider,
            response_cache=self.response_cache,
            max_tokens=extraction_max_tokens,
            hard_max_output_tokens=self.model_output_ceiling,
        )

        self.synthesizer_agent = RuleSynthesizerAgent(
            client=self.client,
            model=self.model_name,
            temperature=temperature,
            seed=seed,
            provider=self.provider,
            response_cache=self.response_cache,
            max_tokens=synthesis_max_tokens,
            hard_max_output_tokens=self.model_output_ceiling,
        )
        self.formatter_agent = ReportFormatterAgent()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        sql_file_path: str,
        dialect: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> PipelineRunResult:
        """Run the full pipeline against a single .sql input file and
        return a `PipelineRunResult` containing the business report, its
    verification/traceability diagnostics, and the parsed
        ingestion result (object identity) the caller can use to derive
        output filenames.

        Args:
            sql_file_path: path to the input .sql file.
            dialect: optional dialect override for this run only
                ("oracle" / "tsql" / "auto"). Defaults to the dialect the
                pipeline was constructed with.
            progress_callback: optional callable invoked with a short
                human-readable status string at the start of each stage
                (e.g. to drive a UI progress indicator).
        """

        def _report_progress(message: str) -> None:
            logger.info(message)
            if progress_callback:
                progress_callback(message)

        effective_dialect = dialect or self.dialect

        _report_progress("Stage 1/6: Running input guardrails")
        raw_code = self._read_source_file(sql_file_path)
        stage_start = time.perf_counter()
        try:
            guard_result = run_input_guardrails(raw_code)
        except InputGuardrailError as exc:
            raise PipelineInputError(str(exc)) from exc
        if guard_result.injection_flags:
            _report_progress(
                "Input guardrails flagged possible prompt-injection content in "
                "the source (treated as inert data, flagged for review)"
            )

        stage_1_seconds = time.perf_counter() - stage_start
        logger.info("Stage 1/6 completed in %.2fs (input guardrails)", stage_1_seconds)

        _report_progress("Stage 2/6: Detecting dialect")
        stage_start = time.perf_counter()
        try:
            detection = detect_dialect(guard_result.clean_code, hint=effective_dialect)
        except UnsupportedDialectError as exc:
            raise PipelineInputError(str(exc)) from exc
        _report_progress(f"Detected {detection.dialect} dialect (confidence: {detection.confidence})")

        stage_2_seconds = time.perf_counter() - stage_start
        logger.info("Stage 2/6 completed in %.2fs (dialect detection)", stage_2_seconds)

        _report_progress(f"Stage 3/6: Preprocessing, parsing, and chunking {sql_file_path}")
        stage_start = time.perf_counter()
        try:
            ingestion = self.ingestion_agent.ingest_text(
                guard_result.clean_code,
                dialect=effective_dialect,
                source_filename=sql_file_path,
                original_code=raw_code,
                prevalidated_code=guard_result.clean_code,
                prevalidated_warnings=guard_result.warnings,
                prevalidated_injection_flags=guard_result.injection_flags,
                detection_result=detection,
            )
        except UnsupportedDialectError as exc:
            raise PipelineInputError(str(exc)) from exc
        run_metadata = build_run_metadata(
            project_root=self.project_root,
            model_name=self.model_name,
            provider=self.provider,
            dialect=ingestion.dialect,
            dialect_confidence=ingestion.dialect_confidence,
            raw_source=ingestion.original_code or ingestion.raw_code,
            object_id=ingestion.object_id,
        )
        ingestion.run_metadata = run_metadata
        _report_progress(
            f"Detected {ingestion.dialect} {ingestion.object_type} '{ingestion.object_name}' "
            f"with {len(ingestion.chunks)} chunk(s)"
        )
        stage_3_seconds = time.perf_counter() - stage_start
        logger.info(
            "Stage 3/6 completed in %.2fs (preprocessing/parsing/chunking)", stage_3_seconds
        )

        _report_progress(
            f"Stage 4/6: Retrieving dependencies / pattern context and extracting logic "
            f"per chunk (model: {self.model_name})"
        )
        stage_start = time.perf_counter()
        telemetry_tracker = LLMTelemetryTracker()
        kb_start = time.perf_counter()
        self.retrieval_agent.build_or_load()
        kb_seconds = time.perf_counter() - kb_start
        if kb_seconds > 0:
            logger.info("Persistent knowledge base ready in %.2fs", kb_seconds)
        analysis_dialect = supported_analysis_dialect(ingestion)
        full_rag_context = self._retrieve_full_source_context(ingestion)
        estimated_tokens = self._estimate_single_pass_tokens(ingestion.raw_code, full_rag_context)
        single_pass = self._use_single_pass(ingestion, estimated_tokens)
        selected_budget = getattr(self, "single_pass_token_budget", SINGLE_PASS_TOKEN_BUDGET)
        extraction_execution = {
            "estimated_input_tokens": estimated_tokens,
            "single_pass_token_budget": selected_budget,
            "selected_path": "single-pass" if single_pass else "chunked",
            "extraction_calls": 1 if single_pass else len(ingestion.chunks),
            "merge_ran": not single_pass,
        }
        logger.info(
            "Stage 4 extraction selection: estimated_tokens=%s budget=%s path=%s extraction_calls=%s merge_ran=%s",
            estimated_tokens,
            selected_budget,
            extraction_execution["selected_path"],
            extraction_execution["extraction_calls"],
            extraction_execution["merge_ran"],
        )
        if single_pass:
            chunk_extractions = [
                self._extract_full_source(
                    ingestion,
                    rag_context=full_rag_context,
                    analysis_dialect=analysis_dialect,
                    telemetry_tracker=telemetry_tracker,
                )
            ]
            # A malformed full-source response is not partial evidence. Use
            # the established chunk/merge path instead of allowing an empty
            # technical payload to bias synthesis or its coverage audit.
            if chunk_extractions[0].parse_error:
                logger.warning(
                    "Full-source extraction was unusable; falling back to the existing chunked extraction path"
                )
                single_pass = False
                chunk_extractions = self._extract_all_chunks(
                    ingestion,
                    run_metadata=run_metadata,
                    analysis_dialect=analysis_dialect,
                    telemetry_tracker=telemetry_tracker,
                )
                extraction_execution.update(
                    {
                        "selected_path": "chunked",
                        "extraction_calls": len(chunk_extractions),
                        "merge_ran": True,
                        "fallback_reason": "full_source_extraction_parse_error",
                    }
                )
        else:
            chunk_extractions = self._extract_all_chunks(
                ingestion,
                run_metadata=run_metadata,
                analysis_dialect=analysis_dialect,
                telemetry_tracker=telemetry_tracker,
            )
        extraction_guardrail_warnings = self._collect_extraction_guardrail_warnings(chunk_extractions)
        retrieval_seconds, extraction_seconds = self._chunk_timing_totals(chunk_extractions)
        stage_4_seconds = time.perf_counter() - stage_start
        logger.info(
            "Stage 4/6 completed in %.2fs total "
            "(kb_ready=%.2fs, retrieval/KB sum=%.2fs, LLM extraction sum=%.2fs, workers=%s, chunks=%s)",
            stage_4_seconds,
            kb_seconds,
            retrieval_seconds,
            extraction_seconds,
            self.chunk_workers,
            len(chunk_extractions),
        )

        _report_progress("Stage 5/6: Reasoning over the technical extraction into business rules")
        stage_start = time.perf_counter()
        merged_extraction = (
            self._single_pass_extraction_payload(chunk_extractions[0], ingestion)
            if single_pass
            else self._merge_extractions(chunk_extractions, ingestion=ingestion)
        )
        merged_extraction["extraction_execution"] = extraction_execution
        # Deterministic, source-derived decision-ladder evidence. Two
        # independent constructs are checked because either can carry a
        # source-supported multi-branch business decision that the LLM
        # extraction stage must not be allowed to silently drop, merge, or
        # reword away: procedural IF/ELSIF/ELSE ladders (Oracle PL/SQL
        # only - T-SQL has no THEN/END IF), and CASE WHEN/THEN/ELSE/END
        # expressions (identical ANSI SQL in both Oracle and T-SQL, so a
        # single check covers both dialects). Neither firing does not mean
        # the object has no decision logic - it means this deterministic
        # pass found no *unambiguous, single-target* ladder to anchor on.
        deterministic_chains = _extract_deterministic_decision_chains(ingestion.raw_code, analysis_dialect or "tsql")
        if deterministic_chains:
            # Keep deterministic chains as structured technical context for
            # the model; they never replace or rewrite synthesized rules.
            merged_extraction["decision_chains"] = merge_decision_chains(
                deterministic_chains, merged_extraction.get("decision_chains", [])
            )
        semantic_findings = find_semantic_anomalies(
            ingestion.raw_code,
            merged_extraction.get("calculations", []),
        )
        merged_extraction["semantic_findings"] = []
        merged_extraction["informational_uncertainties"] = semantic_findings
        merged_extraction["run_metadata"] = run_metadata_to_dict(run_metadata)
        merged_extraction["llm_tables_read"] = list(merged_extraction.get("tables_read", []))
        merged_extraction["llm_tables_written"] = list(merged_extraction.get("tables_written", []))
        if analysis_dialect is None:
            table_operations, statement_provenance = [], []
        else:
            table_operations, statement_provenance = extract_table_operations_from_chunks(
                ingestion.chunks, analysis_dialect
            )
        merged_extraction["statement_provenance"] = statement_provenance
        _annotate_decision_chain_provenance(merged_extraction, ingestion)
        # Orchestration checkpoint gates. Strictly additive: emits its own
        # `process_gates` record type and never a `decision_chain`, so it
        # cannot affect decision-table identity, merging, coverage floors,
        # dedup or IR matching. Empty for non-orchestration objects.
        process_gates = extract_process_gates(
            ingestion.raw_code, dialect=analysis_dialect or ingestion.dialect
        )
        if process_gates:
            merged_extraction["process_gates"] = process_gates
            merged_extraction["process_gate_summary"] = summarize_process_gates(process_gates)
        if table_operations:
            merged_extraction["table_operations"] = table_operations
            merged_extraction["tables_read"], merged_extraction["tables_written"] = (
                split_table_operations(table_operations)
            )
        merged_extraction["calculations"] = (
            list(merged_extraction.get("calculations", []))
            + calculations_from_operations(table_operations)
        )
        # Exception/error-handling bookkeeping (a retry-counter increment,
        # a status-flag write inside a BEGIN CATCH/EXCEPTION block) is not
        # a business calculation - it already appears verbatim under
        # Exception Handling. Identified by where in the source it comes
        # from, not any field name, so it generalizes regardless of what
        # the status table/columns are called.
        exception_handler_spans = find_exception_handler_spans(
            ingestion.raw_code, dialect=analysis_dialect or ingestion.dialect
        )
        merged_extraction["calculations"] = _exclude_exception_handler_calculations(
            merged_extraction["calculations"], ingestion.raw_code, exception_handler_spans
        )
        merged_extraction["statement_dependencies"] = build_statement_dependencies(
            merged_extraction.get("table_operations", []),
            merged_extraction.get("statement_provenance", []),
        )
        # Permanent alias → real-table rewrite on deterministic evidence
        # (decision chains + table_operations) before synthesis / IR / report
        # so every downstream stage sees PRO.Table.col rather than A.col /
        # Target.col / Source.col. Report formatter remains a display safety
        # net for residual LLM prose only.
        merged_extraction = resolve_aliases_in_merged_extraction(merged_extraction)
        synthesis_input = self._build_synthesis_input(merged_extraction)
        parameter_summary = self._summarize_parameters(ingestion)
        synthesis = self._run_rule_synthesis(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis_input=synthesis_input,
            parameter_summary=parameter_summary,
            dialect=analysis_dialect or ingestion.dialect,
            telemetry_tracker=telemetry_tracker,
        )
        synthesis.data["run_metadata"] = run_metadata_to_dict(run_metadata)

        # Coverage-driven revision loop. This is the general-purpose
        # completeness backstop: `find_coverage_gaps` is a purely lexical,
        # dialect-agnostic scan for CASE/WHEN/IF/ELSIF keyword positions
        # that no synthesized rule's evidence appears to reference - it
        # has no idea what a gap *means*, so it never authors a rule
        # itself. When it finds one, the model gets a second, narrowly
        # scoped look at exactly that source region and decides for
        # itself whether a rule belongs there (see
        # `RuleSynthesizerAgent.revise`). Bounded to a small number of
        # retries so a genuinely ambiguous or non-business region doesn't
        # loop forever; whatever remains uncovered after that is reported
        # as an ambiguity, never silently dropped and never fabricated.
        coverage_gaps = find_coverage_gaps(
            ingestion.raw_code, synthesis.data.get("business_rules", [])
        )
        coverage_retries_used = 0
        while coverage_gaps and coverage_retries_used < self.max_coverage_retries:
            coverage_retries_used += 1
            _report_progress(
                f"Coverage check found {len(coverage_gaps)} unreviewed decision "
                f"point(s); asking the model to review (attempt {coverage_retries_used})"
            )
            revision = self.synthesizer_agent.revise(
                object_name=ingestion.object_name,
                object_type=ingestion.object_type,
                parameter_summary=parameter_summary,
                merged_extraction=synthesis_input,
                existing_rules=synthesis.data.get("business_rules", []),
                gaps=coverage_gaps,
                dialect=analysis_dialect or ingestion.dialect,
                raw_source=ingestion.raw_code,
                telemetry_tracker=telemetry_tracker,
            )
            if revision is None:
                # No gaps to review, dialect unsupported, or the revision
                # call itself failed to parse - either way, stop retrying
                # rather than loop on a call that isn't making progress.
                break
            revised_rules = revision.data.get("business_rules")
            if revised_rules is None:
                revised_rules = synthesis.data.get("business_rules", [])
            else:
                # A revise() call runs because a purely lexical scan found
                # an uncited CASE/WHEN/IF/ELSIF line - it says nothing about
                # whether the call's own response was reliable. Live runs
                # show the call succeeding cleanly (`finish_reason=stop`,
                # valid JSON) is the common case, not the exception: the
                # previous "the call happening at all is the degradation
                # signal for whatever it returns" logic stamped `degraded:
                # True` on the WHOLE returned array regardless, including
                # every already-accepted rule the model was only asked to
                # echo back unchanged - a report showing "0 confident, 7
                # needs review: truncated or failed" for a run where every
                # single LLM call actually succeeded (see the 01-18 sample
                # batch analysis). Only a rule that is genuinely NEW here -
                # not present, in substance, in what synthesize() already
                # had - is the actual product of "the model had to look
                # again"; an existing rule's own identity (everything but
                # `rule_id`/`degraded*`, see `rule_identity_key`) is
                # unaffected by simply being echoed back in the same JSON
                # array. `degraded_reason` names *why* separately from the
                # boolean, so report_formatter can stop claiming every
                # flagged rule was "truncated or failed" when this path was
                # actually a successful, targeted second look.
                previously_known = {
                    rule_identity_key(rule)
                    for rule in (synthesis.data.get("business_rules") or [])
                    if isinstance(rule, dict)
                }
                for rule in revised_rules:
                    if isinstance(rule, dict) and rule_identity_key(rule) not in previously_known:
                        rule["degraded"] = True
                        rule["degraded_reason"] = "gap_review"

                # The revise() prompt *asks* the model to return every
                # previously-correct rule plus the new ones, but nothing
                # enforced it: a weaker/smaller model routinely returns only
                # the rules it considered "relevant to the gaps", and that
                # array then replaced the full set wholesale - so a pass
                # whose entire purpose is to INCREASE coverage could silently
                # reduce it. Re-attach any prior rule the revision dropped;
                # the coverage loop may only ever add.
                returned_keys = {
                    rule_identity_key(rule)
                    for rule in revised_rules
                    if isinstance(rule, dict)
                }
                dropped = [
                    rule
                    for rule in (synthesis.data.get("business_rules") or [])
                    if isinstance(rule, dict)
                    and rule_identity_key(rule) not in returned_keys
                ]
                if dropped:
                    logger.warning(
                        "Synthesis revision omitted %d previously-synthesized "
                        "rule(s); re-attaching them so the coverage pass "
                        "cannot reduce coverage.",
                        len(dropped),
                    )
                    revised_rules = list(revised_rules) + dropped
            synthesis.data["business_rules"] = revised_rules
            synthesis.guardrail_warnings = list(synthesis.guardrail_warnings or []) + list(
                revision.guardrail_warnings or []
            )
            coverage_gaps = find_coverage_gaps(
                ingestion.raw_code, synthesis.data.get("business_rules", [])
            )
        merged_extraction["coverage_check"] = {
            "retries_used": coverage_retries_used,
            "unresolved_gaps": [
                {
                    "line_start": gap.line_start,
                    "line_end": gap.line_end,
                    "snippet": gap.snippet,
                    "keywords": gap.keywords,
                }
                for gap in coverage_gaps
            ],
        }
        if coverage_gaps:
            # A truncated synthesis pass (finish_reason == "length") produces
            # a *cause*, not N independent ambiguities: every gap after the
            # cutoff point exists only because the model never got to that
            # region, not because each one was individually reviewed and
            # found ambiguous. In that case, fold one short "affected
            # regions" fragment into the existing truncation ambiguity
            # instead of adding 15-20+ near-duplicate "needs review" bullets
            # - one bullet explains both the cause and the affected lines.
            # Genuine (non-truncation) gaps keep their own bullet each, just
            # shorter, since those were reviewed individually and each one
            # is a distinct thing to check.
            if getattr(synthesis, "truncated", False) and len(coverage_gaps) > 1:
                gap_summary = format_consolidated_gap_ambiguity(coverage_gaps)
                # `_findings_section` unions ambiguities from both
                # containers without deduplicating near-identical text, so
                # merging the same summary into both containers' truncation
                # markers (or merging into one and appending standalone to
                # the other) would show the affected-regions text twice.
                # Merge into whichever container already carries the
                # truncation ambiguity; only append it standalone (to
                # `merged_extraction`, the container `_findings_section`
                # always reads) when NEITHER container has that marker, so
                # the information is never silently dropped.
                merged_into_synthesis = _merge_into_truncation_ambiguity(synthesis.data, gap_summary)
                merged_into_extraction = _merge_into_truncation_ambiguity(merged_extraction, gap_summary)
                if not merged_into_synthesis and not merged_into_extraction:
                    merged_extraction["ambiguities"] = list(merged_extraction.get("ambiguities", []) or []) + [gap_summary]
            else:
                gap_findings = [format_gap_for_ambiguity(gap) for gap in coverage_gaps]
                merged_extraction["ambiguities"].extend(gap_findings)
                synthesis.data["ambiguities"] = list(synthesis.data.get("ambiguities", []) or [])
                synthesis.data["ambiguities"].extend(gap_findings)

        # Guarantee, not best-effort: every deterministic multi-branch
        # decision chain the source actually contains (SMA_CLASS thresholds,
        # SMA_REASON precedence, etc.) gets a rendered Decision Logic table
        # in the final report, regardless of whether the model produced a
        # matching rule for it this run. Runs once, after synthesis and every
        # coverage-gap review pass are done, and only adds a rule for a field
        # no existing rule already covers - see
        # `RuleSynthesizerAgent.ensure_decision_chain_coverage`.
        synthesis.data["business_rules"] = RuleSynthesizerAgent.ensure_decision_chain_coverage(
            synthesis.data.get("business_rules", []),
            merged_extraction.get("decision_chains", []),
        )
        # `ensure_decision_chain_coverage` guarantees a rule for every
        # qualifying deterministic chain regardless of what table it
        # targets - including a boilerplate `IF EXISTS(...) ... ELSE ...`
        # around the standard ACLRUNNINGPROCESSSTATUS bookkeeping in a
        # CATCH block, which produces a fully "correct" but purely
        # operational per-column decision table ("Determine COMPLETED",
        # "Determine ERRORDATE", ...). `_remove_operational_status_rules`
        # already exists to keep exactly this kind of plumbing out of the
        # business-rule collection, but it only ran on the model's own
        # rules *before* this synthetic step added more - re-run it now so
        # the same exclusion applies uniformly no matter which stage
        # produced the rule.
        synthesis.data["business_rules"] = RuleSynthesizerAgent._remove_operational_status_rules(
            synthesis.data.get("business_rules", []), merged_extraction
        )

        # Second, independent guarantee: a single-statement conditional
        # write (a WHERE-gated UPDATE/INSERT with no second branch at all,
        # so `extract_*_decision_chains` never recognizes it as a "chain")
        # has no coverage guarantee above - `ensure_decision_chain_coverage`
        # only fires for multi-branch ladders. Run right after it, from the
        # same deterministic `table_operations` extraction, so a write like
        # "set DpdBucket to NOT_APPLICABLE where LastPaymentDueDate is
        # null" cannot silently vanish from the report just because the
        # model's own synthesis pass missed it. See
        # `RuleSynthesizerAgent.ensure_statement_coverage`.
        synthesis.data["business_rules"] = RuleSynthesizerAgent.ensure_statement_coverage(
            synthesis.data.get("business_rules", []), merged_extraction
        )
        synthesis.data["business_rules"] = RuleSynthesizerAgent._remove_operational_status_rules(
            synthesis.data.get("business_rules", []), merged_extraction
        )

        # Drop rules whose entire "decision" is a null-check guarding its
        # own field's write (`X IS NOT NULL -> update X`) - zero business
        # content, just a restatement of the write itself. Run after the
        # coverage backfill above for the same reason `_remove_operational_
        # status_rules` is re-run here: a synthetic chain-derived rule can
        # be just as tautological as a model-authored one.
        synthesis.data["business_rules"] = RuleSynthesizerAgent._remove_tautological_rules(
            synthesis.data.get("business_rules", [])
        )
        # Re-apply the technical-cleanup / read-only SELECT filters after
        # coverage floors and revision: those stages can reintroduce a
        # CREATE #temp or "Read history" rule that synthesize() already
        # excluded once from the model's own output.
        synthesis.data["business_rules"] = RuleSynthesizerAgent._remove_non_business_cleanup_rules(
            synthesis.data.get("business_rules", []), merged_extraction
        )
        synthesis.data["business_rules"] = RuleSynthesizerAgent._remove_operation_only_rules(
            synthesis.data.get("business_rules", [])
        )

        # Consolidate rules that are really the same underlying decision
        # extracted more than once - most commonly a deterministic chain's
        # own (qualified) rule next to a model-authored (bare) rule for the
        # exact same statement that the qualifier mismatch above already
        # prevents in the common case, but also two model-authored rules
        # from different synthesis/revision passes describing the same
        # condition ladder. Run last, once every other filter has settled
        # the final rule set, so consolidation sees the true final
        # candidates rather than something a later filter would have
        # dropped anyway.
        synthesis.data["business_rules"] = RuleSynthesizerAgent.consolidate_duplicate_rules(
            synthesis.data.get("business_rules", [])
        )

        # Final safety net, run once here after every other rule-shaping
        # stage above: a blank decision_logic_rows outcome that survived
        # everything else (consolidation only helps when a second, better
        # candidate exists to compare against - it can't fix a rule that
        # was the only candidate for its identity) gets one last chance
        # to be filled in from the deterministic decision_chains data,
        # the one source proven correct throughout this pipeline. Never
        # overwrites a non-blank value, so this can only make a report
        # more complete, never less accurate.
        synthesis.data["business_rules"] = RuleSynthesizerAgent.backfill_blank_outcomes_from_decision_chains(
            synthesis.data.get("business_rules", []), merged_extraction.get("decision_chains", [])
        )
        # Permanent alias rewrite on the final business-rule set (model +
        # deterministic floors) so IR / reconciliation / report all share
        # table-qualified text rather than SQL aliases.
        synthesis.data["business_rules"] = resolve_aliases_in_business_rules(
            synthesis.data.get("business_rules", []), merged_extraction
        )
        # Permanent structural shaping (MERGE upsert collapse, IF-ladder
        # fragment suppress). Rule counts follow SQL decisions, not sample
        # "-- Rule N" comments; those comments are a soft reference only.
        # Formatter re-applies the same shaping as a safety net for older IRs.
        synthesis.data["business_rules"] = finalize_business_rule_shape(
            synthesis.data.get("business_rules", []),
            merged_extraction,
            after_reconciliation=False,
        )

        # Same exception-handler exclusion as merged_extraction["calculations"]
        # above, applied to the model-authored calculations list too - a
        # calculation can come from either source.
        synthesis.data["calculations"] = _exclude_exception_handler_calculations(
            synthesis.data.get("calculations", []), ingestion.raw_code, exception_handler_spans
        )

        # Diagnostic-only inventory: this is deliberately built after
        # synthesis/revision so it can say what happened to each executable
        # construct without becoming another source of business rules.
        merged_extraction["completeness_ledger"] = build_completeness_ledger(
            ingestion.raw_code,
            merged_extraction=merged_extraction,
            rules=synthesis.data.get("business_rules", []),
        )

        logger.info("Stage 5/6 completed in %.2fs (business reasoning)", time.perf_counter() - stage_start)

        _report_progress("Stage 6/6: Reconciling deterministic evidence against synthesized output")
        stage_start = time.perf_counter()
        reconciliation = reconcile_deterministic_evidence(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
        )
        if reconciliation is None or not hasattr(reconciliation, "to_dict"):
            raise RuntimeError("Report generation requires completed reconciliation evidence.")
        # Keep SQL-grounded decision tables; drop ungrounded CONFLICT shells
        # from the permanent rule list before IR so reports and IR agree.
        synthesis.data["business_rules"] = finalize_business_rule_shape(
            synthesis.data.get("business_rules", []),
            merged_extraction,
            after_reconciliation=True,
        )
        merged_extraction["reconciliation"] = reconciliation.to_dict()
        merged_extraction["coverage"] = reconciliation.coverage
        merged_extraction["quality"] = reconciliation.quality
        synthesis.data["reconciliation"] = reconciliation.to_dict()
        synthesis.data["coverage"] = reconciliation.coverage
        synthesis.data["quality"] = reconciliation.quality
        reconciliation_findings = self._reconciliation_review_findings(reconciliation)
        merged_extraction["ambiguities"].extend(reconciliation_findings)
        synthesis.data["ambiguities"] = list(synthesis.data.get("ambiguities", []) or [])
        synthesis.data["ambiguities"].extend(reconciliation_findings)
        telemetry_run_id = stable_id(
            "telemetry",
            run_metadata.source_hash if run_metadata else "",
            run_metadata.configuration_version if run_metadata else "",
            run_metadata.run_timestamp if run_metadata else "",
        )
        telemetry_payload = telemetry_tracker.snapshot(telemetry_run_id).to_dict()
        # Aggregate the per-chunk/per-section LLM-failure markers
        # (ChunkExtraction.llm_call_failed, SynthesisResult.synthesis_failed)
        # into one explicit "degraded run" signal, stashed in run telemetry
        # (an existing, schema-free extension point - see RunMetadata) so
        # report_formatter can render a prominent banner. Without this, a
        # report with silently-empty evidence for a failed chunk/section
        # looks identical to a fully clean run - the exact "when, not if"
        # risk the audit flagged for a ~1,000-LLM-call batch.
        failed_chunk_count = sum(
            1 for item in chunk_extractions if getattr(item, "llm_call_failed", False)
        )
        failed_section = bool(getattr(synthesis, "synthesis_failed", False))
        telemetry_payload["degraded"] = failed_chunk_count > 0 or failed_section
        telemetry_payload["failed_chunk_count"] = failed_chunk_count
        telemetry_payload["failed_section_count"] = 1 if failed_section else 0
        run_metadata = attach_run_telemetry(run_metadata, telemetry_payload)
        ingestion.run_metadata = run_metadata
        merged_extraction["run_metadata"] = run_metadata_to_dict(run_metadata)
        synthesis.data["run_metadata"] = run_metadata_to_dict(run_metadata)
        canonical_ir = CanonicalBusinessIR.from_pipeline(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
            reconciliation=reconciliation,
            run_metadata=run_metadata,
        )
        merged_extraction["canonical_ir"] = canonical_ir.to_dict()
        synthesis.data["canonical_ir"] = canonical_ir.to_dict()
        stage_6_seconds = time.perf_counter() - stage_start
        logger.info(
            "Stage 6/6 completed in %.2fs (deterministic reconciliation)", stage_6_seconds
        )

        _report_progress("Stage 7/7: Applying output guardrails and formatting final report")
        stage_start = time.perf_counter()
        report_filename = f"{build_object_identity_stem(ingestion, fallback_stem=Path(sql_file_path).stem)}_report.md"
        report = self.formatter_agent.format(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
            canonical_ir=canonical_ir,
            extraction_guardrail_warnings=extraction_guardrail_warnings,
            run_metadata=run_metadata,
        )
        verification_report = self.formatter_agent.format_verification(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
            canonical_ir=canonical_ir,
            run_metadata=run_metadata,
            report_filename=report_filename,
            extraction_guardrail_warnings=extraction_guardrail_warnings,
        )
        # Keep verification separate from the business report. Entry points
        # persist this text under output/verification and include it in logs.
        logger.info(
            "Verification/traceability diagnostics for %s:\n%s",
            report_filename,
            verification_report.rstrip(),
        )
        logger.info("Stage 7/7 completed in %.2fs (final report generation)", time.perf_counter() - stage_start)
        return PipelineRunResult(report=report, verification_report=verification_report, ingestion=ingestion)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_source_file(sql_file_path: str) -> str:
        # Delegates the extension/existence check to the ingestion
        # agent's own loader so there is exactly one place that owns
        # "what file types are accepted".
        return CodeIngestionAgent._load_file(sql_file_path)

    @staticmethod
    def _estimate_text_tokens(value: str) -> int:
        """Conservatively estimate tokens without coupling the app to a tokenizer."""
        # Calibrated to ~3.5 chars/token for SQL. The previous 1.5 chars/token
        # divisor was roughly 2.3x more pessimistic than real Bedrock usage
        # (measured: sample runs used ~2,521 completion tokens against a
        # source far smaller than that ratio implied), which pushed objects
        # into the chunked extraction path - where rules fragment, duplicate,
        # and get lost in the merge - even when they would fit comfortably in
        # a single pass. Still deliberately conservative (not pushed to the
        # ~4 chars/token typical of general code) since under-counting here
        # is safe (falls back to chunking) and over-counting is not
        # (truncated single-pass prompt). Validate against the actual
        # `inputTokens` Bedrock returns (already captured in telemetry) if
        # this needs recalibrating further for a specific model/corpus.
        return max(1, math.ceil(len(value or "") / 3.5))

    def _estimate_single_pass_tokens(self, raw_code: str, rag_context: str) -> int:
        """Estimate the extraction prompt input plus a safety reserve."""
        return (
            self._estimate_text_tokens(raw_code)
            + self._estimate_text_tokens(rag_context)
            + _DEFAULT_PROMPT_SCHEMA_RESERVE
        )

    def _use_single_pass(self, ingestion: IngestionResult, estimated_tokens: int) -> bool:
        """Select full-source extraction only when the supported dialect fits."""
        budget = getattr(self, "single_pass_token_budget", SINGLE_PASS_TOKEN_BUDGET)
        return bool(supported_analysis_dialect(ingestion)) and estimated_tokens <= budget

    def _retrieve_full_source_context(self, ingestion: IngestionResult) -> str:
        """Retrieve the same kind of KB context used by chunk extraction."""
        query = (
            f"{ingestion.dialect} {ingestion.object_type} full source banking logic: "
            f"{ingestion.raw_code[:400]}"
        )
        retrieve = getattr(self.retrieval_agent, "retrieve_context_text", None)
        return retrieve(query, k=self.retrieval_k) if retrieve is not None else ""

    def _extract_full_source(
        self,
        ingestion: IngestionResult,
        *,
        rag_context: str,
        analysis_dialect: str,
        telemetry_tracker: Optional[LLMTelemetryTracker] = None,
    ) -> ChunkExtraction:
        """Run the existing technical extractor once over the complete source."""
        extraction_start = time.perf_counter()
        # Strip commented-out DML before it ever reaches the extraction
        # prompt (see strip_inactive_code_for_llm docstring) - this must be
        # deterministic, not left to a prompted instruction the model can
        # lose track of against thousands of lines of realistic-looking
        # dead SQL. The sanitized text is what gets sent AND what
        # ground_extraction_against_source checks the response against, so
        # nothing here can be "grounded" in dead code.
        sanitized_source, inactive_snippets = strip_inactive_code_for_llm(ingestion.raw_code)
        try:
            extraction = self.extraction_agent.extract(
                chunk_id="full_source",
                chunk_kind="full_source",
                code_chunk=sanitized_source,
                rag_context=rag_context,
                object_type=ingestion.object_type,
                object_name=ingestion.object_name,
                chunk_context=["full_source"],
                embedded_sql=[sql for chunk in ingestion.chunks for sql in (chunk.embedded_sql or [])],
                dialect=analysis_dialect,
                telemetry_tracker=telemetry_tracker,
            )
        except Exception as exc:  # noqa: BLE001
            extraction = ChunkExtraction(
                chunk_id="full_source",
                chunk_kind="full_source",
                chunk_context=["full_source"],
                data={
                    "conditions": [], "decision_chains": [], "loops": [],
                    "tables_read": [], "tables_written": [], "calculations": [],
                    "exception_handling": [], "ambiguities": [],
                },
                parse_error=str(exc),
                guardrail_warnings=[f"Full-source extraction failed: {exc}"],
                llm_call_failed=True,
            )
        if inactive_snippets:
            # Verification-report-only note (see format_verification's
            # guardrail_warnings surfacing) - never promoted to the
            # business report. Genuinely useful to a reviewer, and removes
            # the risk of a repealed rule being documented as active.
            extraction.guardrail_warnings = list(extraction.guardrail_warnings or []) + [
                f"Commented-out logic found in source ({len(inactive_snippets)} block(s)) and excluded "
                "from extraction - not included in the business rules."
            ]
        setattr(extraction, "_timings", {"retrieval": 0.0, "extraction": time.perf_counter() - extraction_start})
        return extraction

    @staticmethod
    def _single_pass_extraction_payload(
        extraction: ChunkExtraction, ingestion: IngestionResult
    ) -> Dict[str, Any]:
        """Adapt one extraction result to the established merged-evidence shape."""
        sections = (
            "conditions", "decision_chains", "loops", "tables_read", "tables_written",
            "calculations", "exception_handling", "ambiguities",
        )
        payload: Dict[str, Any] = {section: [] for section in sections}
        support_confidence = derive_chunk_support_confidence(
            parse_error=extraction.parse_error,
            guardrail_warnings=extraction.guardrail_warnings,
            has_direct_evidence=bool(extraction.data.get("tables_read") or extraction.data.get("tables_written")),
            has_embedded_sql=bool(extraction.embedded_sql),
            ambiguity_count=len(extraction.data.get("ambiguities", []) or []),
            dynamic_sql_detected=any("Dynamic SQL detected" in w for w in extraction.guardrail_warnings),
            parser_unavailable=any("structural validation was unavailable" in w.lower() for w in extraction.guardrail_warnings),
        )
        for section in sections:
            for item in extraction.data.get(section, []) or []:
                if isinstance(item, dict):
                    annotated_item = dict(item)
                    annotated_item.setdefault("source_chunk_id", extraction.chunk_id)
                    annotated_item.setdefault("source_chunk_kind", extraction.chunk_kind)
                    annotated_item.setdefault("source_chunk_context", extraction.chunk_context)
                    annotated_item.setdefault("source_parse_error", extraction.parse_error)
                    annotated_item.setdefault("source_guardrail_warnings", extraction.guardrail_warnings)
                    annotated_item.setdefault("source_confidence", support_confidence)
                    annotated_item.setdefault("source_file", ingestion.source_filename)
                    annotated_item.setdefault("source_char_start", 0)
                    annotated_item.setdefault("source_char_end", len(ingestion.raw_code))
                    annotated_item.setdefault("source_line_start", 1)
                    annotated_item.setdefault("source_line_end", ingestion.raw_code.count("\n") + 1)
                    annotated_item.setdefault("source_location_status", "full_source")
                    payload[section].append(annotated_item)
                else:
                    payload[section].append(item)
        payload["chunk_provenance"] = [{
            "chunk_id": extraction.chunk_id,
            "chunk_kind": extraction.chunk_kind,
            "chunk_context": extraction.chunk_context,
            "embedded_sql": extraction.embedded_sql,
            "parse_error": extraction.parse_error,
            "guardrail_warnings": extraction.guardrail_warnings,
            "support_confidence": support_confidence,
            "source_file": ingestion.source_filename,
            "source_char_start": 0,
            "source_char_end": len(ingestion.raw_code),
            "source_line_start": 1,
            "source_line_end": ingestion.raw_code.count("\n") + 1,
            "source_location_status": "full_source",
        }]
        if extraction.parse_error:
            payload["ambiguities"].append(
                "Full-source technical extraction returned malformed JSON and needs manual review."
            )
        return payload

    def _extract_all_chunks(
        self,
        ingestion: IngestionResult,
        run_metadata: Optional[RunMetadata] = None,
        analysis_dialect: Optional[str] = None,
        telemetry_tracker: Optional[LLMTelemetryTracker] = None,
    ) -> list[ChunkExtraction]:
        if not ingestion.chunks:
            return []
        if analysis_dialect is None:
            analysis_dialect = supported_analysis_dialect(ingestion)
        if analysis_dialect is None:
            return []

        exact_extraction_cache: Dict[str, ChunkExtraction] = {}
        cache_lock = threading.Lock()
        in_flight: Dict[str, threading.Event] = {}
        worker_count = min(self.chunk_workers, len(ingestion.chunks))
        if worker_count <= 1:
            results: list[ChunkExtraction] = []
            for idx, chunk in enumerate(ingestion.chunks):
                _, extraction = self._extract_single_chunk(
                    idx,
                    chunk,
                    ingestion,
                    exact_extraction_cache=exact_extraction_cache,
                    cache_lock=cache_lock,
                    in_flight=in_flight,
                    cache_namespace=self._chunk_cache_namespace(ingestion, run_metadata),
                    telemetry_tracker=telemetry_tracker,
                )
                results.append(extraction)
            return results

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(
                    self._extract_single_chunk,
                    idx,
                    chunk,
                    ingestion,
                    exact_extraction_cache,
                    cache_lock,
                    in_flight,
                    self._chunk_cache_namespace(ingestion, run_metadata),
                    telemetry_tracker,
                )
                for idx, chunk in enumerate(ingestion.chunks)
            ]
            ordered = [future.result() for future in futures]
        ordered.sort(key=lambda item: item[0])
        return [item[1] for item in ordered]

    def _extract_single_chunk(
        self,
        index: int,
        chunk,
        ingestion: IngestionResult,
        exact_extraction_cache: Optional[Dict[str, ChunkExtraction]] = None,
        cache_lock: Optional[threading.Lock] = None,
        in_flight: Optional[Dict[str, threading.Event]] = None,
        cache_namespace: str = "",
        telemetry_tracker: Optional[LLMTelemetryTracker] = None,
    ) -> tuple[int, ChunkExtraction]:
        timings: Dict[str, float] = {"retrieval": 0.0, "extraction": 0.0}
        query = self._build_retrieval_query(ingestion, chunk)
        retrieval_start = time.perf_counter()
        rag_context = self.retrieval_agent.retrieve_context_text(query, k=self.retrieval_k)
        timings["retrieval"] = time.perf_counter() - retrieval_start

        cache_key = None
        if exact_extraction_cache is not None:
            cache_key = self._chunk_cache_key(
                ingestion=ingestion,
                chunk=chunk,
                rag_context=rag_context,
                cache_namespace=cache_namespace,
            )
            cached = None
            owner = True
            wait_event = None
            if cache_lock is not None:
                with cache_lock:
                    cached = exact_extraction_cache.get(cache_key)
                    if cached is None and in_flight is not None:
                        wait_event = in_flight.get(cache_key)
                        if wait_event is None:
                            wait_event = threading.Event()
                            in_flight[cache_key] = wait_event
                        else:
                            owner = False
            else:
                cached = exact_extraction_cache.get(cache_key)
            if cached is not None:
                extraction = copy.deepcopy(cached)
                extraction.chunk_id = chunk.chunk_id
                extraction.chunk_kind = chunk.kind
                extraction.chunk_context = chunk.context_path
                extraction.embedded_sql = chunk.embedded_sql
                setattr(extraction, "_timings", timings)
                return index, extraction
            if not owner and wait_event is not None:
                wait_event.wait()
                if cache_lock is not None:
                    with cache_lock:
                        cached = exact_extraction_cache.get(cache_key)
                else:
                    cached = exact_extraction_cache.get(cache_key)
                if cached is not None:
                    extraction = copy.deepcopy(cached)
                    extraction.chunk_id = chunk.chunk_id
                    extraction.chunk_kind = chunk.kind
                    extraction.chunk_context = chunk.context_path
                    extraction.embedded_sql = chunk.embedded_sql
                    setattr(extraction, "_timings", timings)
                    return index, extraction

        extraction_start = time.perf_counter()
        sanitized_chunk_text, inactive_snippets = strip_inactive_code_for_llm(chunk.text)
        try:
            extraction = self.extraction_agent.extract(
                chunk_id=chunk.chunk_id,
                chunk_kind=chunk.kind,
                code_chunk=sanitized_chunk_text,
                rag_context=rag_context,
                object_type=ingestion.object_type,
                object_name=ingestion.object_name,
                chunk_context=chunk.context_path,
                embedded_sql=chunk.embedded_sql,
                dialect=ingestion.concrete_dialect or ingestion.fallback_dialect or "oracle",
                telemetry_tracker=telemetry_tracker,
            )
        except Exception as exc:  # noqa: BLE001
            extraction = ChunkExtraction(
                chunk_id=chunk.chunk_id,
                chunk_kind=chunk.kind,
                chunk_context=chunk.context_path,
                embedded_sql=chunk.embedded_sql,
                data={
                    "conditions": [],
                    "loops": [],
                    "tables_read": [],
                    "tables_written": [],
                    "calculations": [],
                    "exception_handling": [],
                    "ambiguities": [],
                },
                raw_response="",
                parse_error=str(exc),
                guardrail_warnings=[f"Chunk extraction failed: {exc}"],
                llm_call_failed=True,
            )
        if inactive_snippets:
            # Verification-report-only note - see the matching comment in
            # _extract_full_source. Deterministic, not prompted: this
            # chunk's commented-out DML never reached the extraction
            # prompt as candidate logic.
            extraction.guardrail_warnings = list(extraction.guardrail_warnings or []) + [
                f"Commented-out logic found in source ({len(inactive_snippets)} block(s)) and excluded "
                "from extraction - not included in the business rules."
            ]
        timings["extraction"] = time.perf_counter() - extraction_start
        setattr(extraction, "_timings", timings)
        if exact_extraction_cache is not None and cache_key is not None:
            if cache_lock is not None:
                with cache_lock:
                    exact_extraction_cache[cache_key] = copy.deepcopy(extraction)
                    if in_flight is not None and cache_key in in_flight:
                        in_flight.pop(cache_key).set()
            else:
                exact_extraction_cache[cache_key] = copy.deepcopy(extraction)
        elif in_flight is not None and cache_key is not None:
            in_flight.pop(cache_key, None)
        return index, extraction

    @staticmethod
    def _chunk_cache_key(
        ingestion: IngestionResult, chunk, rag_context: str, cache_namespace: str = ""
    ) -> str:
        payload = "|".join(
            [
                cache_namespace,
                ingestion.object_type,
                ingestion.object_name,
                ingestion.dialect,
                ingestion.concrete_dialect,
                chunk.kind,
                " > ".join(chunk.context_path or []),
                chunk.text,
                "\n".join(chunk.embedded_sql or []),
                rag_context,
            ]
        )
        return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()

    @staticmethod
    def _chunk_cache_namespace(
        ingestion: IngestionResult, run_metadata: Optional[RunMetadata] = None
    ) -> str:
        return stable_id(
            "cache",
            PIPELINE_VERSION,
            ingestion.source_hash,
            ingestion.dialect,
            ingestion.concrete_dialect,
            ingestion.fallback_dialect,
            run_metadata.configuration_version if run_metadata else "",
            run_metadata.prompt_version if run_metadata else "",
            run_metadata.knowledge_base_version if run_metadata else "",
        )

    @staticmethod
    def _chunk_timing_totals(chunk_extractions: list[ChunkExtraction]) -> tuple[float, float]:
        retrieval_total = 0.0
        extraction_total = 0.0
        for extraction in chunk_extractions:
            timings = getattr(extraction, "_timings", {}) or {}
            retrieval_total += float(timings.get("retrieval", 0.0) or 0.0)
            extraction_total += float(timings.get("extraction", 0.0) or 0.0)
        return retrieval_total, extraction_total

    @staticmethod
    def _collect_extraction_guardrail_warnings(
        chunk_extractions: list[ChunkExtraction],
    ) -> List[str]:
        warnings: List[str] = []
        for extraction in chunk_extractions:
            warnings.extend(extraction.guardrail_warnings)
        return warnings

    @staticmethod
    def _build_retrieval_query(ingestion: IngestionResult, chunk) -> str:
        # Keep the retrieval query short and construct-focused so the
        # vector search surfaces the most relevant pattern docs.
        snippet = chunk.text[:400]
        context = " / ".join(chunk.context_path) if getattr(chunk, "context_path", None) else chunk.kind
        embedded = "; ".join(chunk.embedded_sql[:2]) if getattr(chunk, "embedded_sql", None) else ""
        suffix = f" | embedded SQL: {embedded}" if embedded else ""
        return f"{ingestion.dialect} {ingestion.object_type} {context} banking logic: {snippet}{suffix}"

    @staticmethod
    def _merge_extractions(
        chunk_extractions: list[ChunkExtraction], ingestion: Optional[IngestionResult] = None
    ) -> Dict[str, Any]:
        merged: Dict[str, Any] = {
            "conditions": [],
            "decision_chains": [],
            "loops": [],
            "tables_read": [],
            "tables_written": [],
            "calculations": [],
            "exception_handling": [],
            "ambiguities": [],
            "chunk_provenance": [],
        }
        chunk_lookup = {chunk.chunk_id: chunk for chunk in getattr(ingestion, "chunks", []) or []}
        decision_chain_keys: set[str] = set()
        for extraction in chunk_extractions:
            chunk_meta = chunk_lookup.get(extraction.chunk_id)
            support_confidence = derive_chunk_support_confidence(
                parse_error=extraction.parse_error,
                guardrail_warnings=extraction.guardrail_warnings,
                has_direct_evidence=bool(extraction.data.get("tables_read") or extraction.data.get("tables_written")),
                has_embedded_sql=bool(extraction.embedded_sql),
                ambiguity_count=len(extraction.data.get("ambiguities", []) or []),
                dynamic_sql_detected=any("Dynamic SQL detected" in w for w in extraction.guardrail_warnings),
                parser_unavailable=bool(
                    any("structural validation was unavailable" in w.lower() for w in extraction.guardrail_warnings)
                ),
            )
            merged["chunk_provenance"].append(
                {
                    "chunk_id": extraction.chunk_id,
                    "chunk_kind": extraction.chunk_kind,
                    "chunk_context": extraction.chunk_context,
                    "embedded_sql": extraction.embedded_sql,
                    "parse_error": extraction.parse_error,
                    "guardrail_warnings": extraction.guardrail_warnings,
                    "support_confidence": support_confidence,
                    "source_file": getattr(chunk_meta, "source_filename", "") if chunk_meta else "",
                    "source_char_start": getattr(chunk_meta, "source_char_start", -1) if chunk_meta else -1,
                    "source_char_end": getattr(chunk_meta, "source_char_end", -1) if chunk_meta else -1,
                    "source_line_start": getattr(chunk_meta, "source_line_start", -1) if chunk_meta else -1,
                    "source_line_end": getattr(chunk_meta, "source_line_end", -1) if chunk_meta else -1,
                    "source_location_status": getattr(chunk_meta, "source_location_status", "unavailable") if chunk_meta else "unavailable",
                }
            )
            for key in merged:
                if key == "chunk_provenance":
                    continue
                for item in extraction.data.get(key, []) or []:
                    if key == "decision_chains" and isinstance(item, dict):
                        structural_item = {
                            "chain_type": item.get("chain_type", ""),
                            "subject": item.get("subject", ""),
                            "branches": item.get("branches", []),
                        }
                        chain_key = json.dumps(
                            structural_item, sort_keys=True, separators=(",", ":"), default=str
                        )
                        if chain_key in decision_chain_keys:
                            continue
                        decision_chain_keys.add(chain_key)
                    if isinstance(item, dict):
                        annotated_item = dict(item)
                        annotated_item.setdefault("source_chunk_id", extraction.chunk_id)
                        annotated_item.setdefault("source_chunk_kind", extraction.chunk_kind)
                        annotated_item.setdefault("source_chunk_context", extraction.chunk_context)
                        annotated_item.setdefault("source_parse_error", extraction.parse_error)
                        annotated_item.setdefault(
                            "source_guardrail_warnings", extraction.guardrail_warnings
                        )
                        annotated_item.setdefault(
                            "source_confidence",
                            support_confidence,
                        )
                        if chunk_meta is not None:
                            annotated_item.setdefault("source_file", getattr(chunk_meta, "source_filename", ""))
                            annotated_item.setdefault("source_char_start", getattr(chunk_meta, "source_char_start", -1))
                            annotated_item.setdefault("source_char_end", getattr(chunk_meta, "source_char_end", -1))
                            annotated_item.setdefault("source_line_start", getattr(chunk_meta, "source_line_start", -1))
                            annotated_item.setdefault("source_line_end", getattr(chunk_meta, "source_line_end", -1))
                            annotated_item.setdefault(
                                "source_location_status", getattr(chunk_meta, "source_location_status", "unavailable")
                            )
                        merged[key].append(annotated_item)
                    else:
                        merged[key].append(item)
            if extraction.parse_error:
                merged["ambiguities"].append(
                    f"Chunk '{extraction.chunk_id}' ({extraction.chunk_kind}) technical "
                    "extraction returned malformed JSON and needs manual review."
                )
        return merged

    # Technical-extraction sections whose items carry a reliable per-item
    # `source_chunk_id` (set in `_merge_extractions` / `extract_table_
    # operations_from_chunks`), and so can be safely restricted to just the
    # chunks belonging to one synthesis section.
    #
    # `statement_provenance` and the `llm_tables_read`/`llm_tables_written`
    # duplicates (see `llm_tables_read = list(tables_read)` a few lines
    # above the sectioned-synthesis call site) used to be deliberately left
    # OUT of this list on the assumption that they were "small and already
    # deduplicated, so duplicating them across sections is harmless." That
    # assumption was wrong: measured on a real, unremarkable 176-line
    # procedure split into 12 sections, `statement_provenance` alone was
    # 41KB (~11,800 estimated tokens) of JSON attached, UNFILTERED, to
    # EVERY section - on its own already bigger than an 8,000 TPM rate
    # limit, before a single character of that section's own content was
    # added. Every section's synthesis call was rejected pre-flight
    # (`PromptTooLargeForRateLimitError`), and the object's report ended up
    # with zero business rules, zero purpose_summary, zero
    # step_by_step_flow - "Not explicitly determined from source SQL"
    # everywhere, even though every underlying extraction fact was present
    # and correct. Root cause was this one list not being scoped down like
    # its siblings; the fix is exactly that, not a bigger TPM budget or a
    # smaller SYNTHESIS_EVIDENCE_MAP_MAX_CHARS.
    _CHUNK_SCOPED_SYNTHESIS_SECTIONS = (
        "conditions",
        "decision_chains",
        "loops",
        "calculations",
        "exception_handling",
        "tables_read",
        "tables_written",
        "table_operations",
        "statement_provenance",
        "llm_tables_read",
        "llm_tables_written",
    )

    @staticmethod
    def _scope_extraction_to_chunks(merged_extraction: Dict[str, Any], chunk_ids: set) -> Dict[str, Any]:
        """Return a shallow copy of `merged_extraction` restricted to the
        technical evidence that belongs to `chunk_ids`, for one sectioned
        synthesis call. `merged_extraction` itself is never mutated - the
        full, unscoped evidence is still what reconciliation, the
        verification report, and downstream formatting see.
        """
        scoped: Dict[str, Any] = dict(merged_extraction)
        for key in LogicRulesExtractorPipeline._CHUNK_SCOPED_SYNTHESIS_SECTIONS:
            items = merged_extraction.get(key)
            if not isinstance(items, list):
                continue
            scoped[key] = [
                item for item in items
                if isinstance(item, dict) and item.get("source_chunk_id") in chunk_ids
            ]
        chunk_provenance = merged_extraction.get("chunk_provenance")
        if isinstance(chunk_provenance, list):
            scoped["chunk_provenance"] = [
                item for item in chunk_provenance
                if isinstance(item, dict) and item.get("chunk_id") in chunk_ids
            ]
        # `statement_dependencies` (see `build_statement_dependencies`) is
        # not a flat list - it's a {version, edge_count, edges,
        # unresolved_count, unresolved} graph over the WHOLE object's
        # statements, and measured just as large as statement_provenance
        # (~39KB on the same 176-line sample) for the same reason: nothing
        # scoped it down per section. An edge/unresolved-pair is kept only
        # when at least one endpoint belongs to this section - a
        # cross-section edge whose OTHER endpoint the section can't see is
        # still meaningful context ("this section's write feeds a read
        # elsewhere"), but an edge entirely outside the section is not.
        statement_dependencies = merged_extraction.get("statement_dependencies")
        if isinstance(statement_dependencies, dict):
            scoped["statement_dependencies"] = LogicRulesExtractorPipeline._scope_statement_dependencies(
                statement_dependencies, chunk_ids
            )
        return scoped

    @staticmethod
    def _scope_statement_dependencies(statement_dependencies: Dict[str, Any], chunk_ids: set) -> Dict[str, Any]:
        def _endpoint_chunk_id(endpoint: Any) -> str:
            if isinstance(endpoint, dict):
                location = endpoint.get("location")
                if isinstance(location, dict) and location.get("source_chunk_id"):
                    return str(location.get("source_chunk_id"))
            return ""

        def _statement_id_chunk_id(statement_id: Any) -> str:
            # Statement ids are formatted "<chunk_id>:<suffix>" throughout
            # this pipeline (see extract_table_operations_from_chunks) -
            # chunk ids themselves never contain ":", so splitting on the
            # first one recovers the chunk id even when no richer
            # `location` object is present (the `unresolved` entries below
            # only carry the bare id, not a full endpoint object).
            text = str(statement_id or "")
            return text.split(":", 1)[0] if text else ""

        edges = statement_dependencies.get("edges")
        scoped_edges = []
        if isinstance(edges, list):
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                from_chunk = _endpoint_chunk_id(edge.get("from"))
                to_chunk = _endpoint_chunk_id(edge.get("to"))
                if from_chunk in chunk_ids or to_chunk in chunk_ids:
                    scoped_edges.append(edge)

        unresolved = statement_dependencies.get("unresolved")
        scoped_unresolved = []
        if isinstance(unresolved, list):
            for item in unresolved:
                if not isinstance(item, dict):
                    continue
                from_chunk = _statement_id_chunk_id(item.get("from_statement_id"))
                to_chunk = _statement_id_chunk_id(item.get("to_statement_id"))
                if from_chunk in chunk_ids or to_chunk in chunk_ids:
                    scoped_unresolved.append(item)

        scoped = dict(statement_dependencies)
        scoped["edges"] = scoped_edges
        scoped["edge_count"] = len(scoped_edges)
        scoped["unresolved"] = scoped_unresolved
        scoped["unresolved_count"] = len(scoped_unresolved)
        return scoped

    def _run_rule_synthesis(
        self,
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis_input: Dict[str, Any],
        parameter_summary: str,
        dialect: str,
        telemetry_tracker: Optional[LLMTelemetryTracker],
    ) -> SynthesisResult:
        """Run business-rule synthesis for the object.

        Small/medium objects take exactly the previous single-call path: one
        `RuleSynthesizerAgent.synthesize()` call over the whole merged
        extraction. Objects large enough that a single call is virtually
        guaranteed to exceed the hard output-token ceiling (see
        `RuleSynthesizerAgent.requires_sectioned_synthesis`) - `PRO.
        SMA_MARKING` and several of the larger real procedures reliably hit
        this - are instead synthesized per logical section, reusing the same
        chunk boundaries the extraction stage already produced, and the
        resulting per-section rule sets are merged into one result. This
        avoids the truncation that otherwise silently drops business rules
        and inflates Needs Review with gaps that only exist because
        synthesis never reached that code.
        """
        raw_source = ingestion.raw_code

        def _run_single_call() -> SynthesisResult:
            # Mirrors the per-chunk extraction degrade pattern
            # (_extract_one_chunk's except block): a transient LLM failure
            # here must not abort the whole run - it previously did,
            # unlike extraction, because there was no exception boundary
            # around this call at all. Degrading to an empty-but-valid
            # SynthesisResult (SynthesisResult's own `data` default factory
            # already supplies the correct empty schema) keeps the run
            # alive and marks it for the run-level "degraded run" signal.
            try:
                result = self.synthesizer_agent.synthesize(
                    object_name=ingestion.object_name,
                    object_type=ingestion.object_type,
                    parameter_summary=parameter_summary,
                    merged_extraction=synthesis_input,
                    dialect=dialect,
                    raw_source=raw_source,
                    telemetry_tracker=telemetry_tracker,
                )
                return _mark_rules_degraded_if_unreliable(result)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Rule synthesis failed for '%s': %s", ingestion.object_name, exc)
                return SynthesisResult(
                    parse_error=str(exc),
                    guardrail_warnings=[f"Rule synthesis failed: {exc}"],
                    synthesis_failed=True,
                )

        # Duck-typed defensively: some callers (tests, lightweight synthesizer
        # stand-ins) swap in a `synthesizer_agent` that only implements the
        # original `synthesize()`/`revise()` surface. Sectioning is an
        # optimization, not a contract every synthesizer must honor, so its
        # absence just means "run the single-call path exactly as before"
        # rather than an error.
        requires_sectioned_synthesis = getattr(self.synthesizer_agent, "requires_sectioned_synthesis", None)
        plan_synthesis_sections = getattr(self.synthesizer_agent, "plan_synthesis_sections", None)
        if (
            requires_sectioned_synthesis is None
            or plan_synthesis_sections is None
            or not requires_sectioned_synthesis(raw_source)
        ):
            return _run_single_call()

        sections = plan_synthesis_sections(ingestion.chunks, raw_source)
        if len(sections) <= 1:
            return _run_single_call()

        logger.info(
            "Synthesis: '%s' exceeds the single-call output-token budget; "
            "running %d section(s) aligned to extraction chunk boundaries instead of one call.",
            ingestion.object_name,
            len(sections),
        )
        chunk_lookup = {
            getattr(chunk, "chunk_id", None): chunk
            for chunk in (ingestion.chunks or [])
        }

        def _run_section(section: Dict[str, Any]) -> SynthesisResult:
            chunk_id_list = list(section.get("chunk_ids") or [])
            chunk_ids = set(chunk_id_list)
            section_extraction = self._scope_extraction_to_chunks(merged_extraction, chunk_ids)
            section_synthesis_input = self._build_synthesis_input(section_extraction)
            text_override = section.get("text_override")
            start = section.get("char_start")
            end = section.get("char_end")
            if isinstance(text_override, str) and text_override:
                # Set by `plan_synthesis_sections` when a single chunk's own
                # decision-point count exceeded the section budget and had
                # to be sub-split (see `_split_oversized_chunk_into_sections`)
                # - an explicit, exact slice of that chunk's own text, valid
                # whether or not absolute source offsets are available.
                section_raw_source = text_override
            elif (
                isinstance(start, int)
                and isinstance(end, int)
                and 0 <= start < end <= len(raw_source)
            ):
                section_raw_source = raw_source[start:end]
            else:
                # Character offsets aren't always available (e.g. batch-split
                # T-SQL objects, where `CodeChunk.source_char_start/end` come
                # back -1 - a pre-existing ingestion limitation, not
                # something sectioning can assume away). Falling back to the
                # *whole* raw source here would silently defeat sectioning:
                # every section's own truncation-budget estimate is derived
                # from the raw source it's given, so handing each one the
                # full object would just reproduce the original truncation
                # risk once per section instead of avoiding it. Reconstruct
                # the section's text directly from its own chunks' text
                # instead - this works whether or not offsets are available,
                # and is the same "reuse the extraction boundaries" contract
                # either way.
                section_texts = [
                    str(getattr(chunk_lookup[chunk_id], "text", "") or "")
                    for chunk_id in chunk_id_list
                    if chunk_id in chunk_lookup
                ]
                section_raw_source = "\n".join(text for text in section_texts if text) or raw_source
            # Unlike _run_single_call, this previously had NO exception
            # boundary at all - one section's LLM call failing aborted the
            # entire run, even though the other sections' calls had
            # already succeeded (or were about to). Degrading just this
            # section to an empty-but-valid result lets its siblings'
            # rules survive `merge_section_results` untouched.
            #
            # A single failure here used to be final on the first attempt,
            # with no retry at all - despite the degraded-run banner
            # telling the report reader this section "failed after
            # retries". For a transient failure (rate limit, timeout,
            # provider hiccup) a second attempt with the *exact same*
            # request often just succeeds, exactly like the retry already
            # added to `LogicExtractionAgent.extract()` for a malformed
            # extraction response. `PromptTooLargeForRateLimitError` is the
            # one exception explicitly NOT retried here: it is a
            # deterministic pre-flight size check (see
            # `RuleSynthesizerAgent.synthesize`'s `LLM_TPM_LIMIT` guard),
            # not a transient condition - the prompt is exactly as large on
            # a second attempt, so retrying it would just burn a call to
            # reproduce the identical failure. If your `.env` sets
            # `LLM_TPM_LIMIT` / `SYNTHESIS_EVIDENCE_MAP_MAX_CHARS` /
            # `SYNTHESIS_SECTION_MAX_CHARS` to values tuned for a
            # heavily-rate-limited free-tier account (see
            # config/.env.example), and your real account isn't actually
            # that constrained, raising or unsetting those is the fix for
            # THIS failure mode - no retry count can work around a request
            # that is genuinely too large for a limit that doesn't really
            # apply to you.
            attempts = 0
            last_exc: Exception | None = None
            while attempts < 2:
                attempts += 1
                try:
                    result = self.synthesizer_agent.synthesize(
                        object_name=ingestion.object_name,
                        object_type=ingestion.object_type,
                        parameter_summary=parameter_summary,
                        merged_extraction=section_synthesis_input,
                        dialect=dialect,
                        raw_source=section_raw_source,
                        telemetry_tracker=telemetry_tracker,
                        is_section=True,
                    )
                    return _mark_rules_degraded_if_unreliable(result)
                except PromptTooLargeForRateLimitError as exc:
                    last_exc = exc
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempts < 2:
                        logger.warning(
                            "Rule synthesis section failed for '%s' (chunks %s), "
                            "retrying once: %s",
                            ingestion.object_name,
                            chunk_id_list,
                            exc,
                        )
            logger.warning(
                "Rule synthesis section failed for '%s' (chunks %s) after %d attempt(s): %s",
                ingestion.object_name,
                chunk_id_list,
                attempts,
                last_exc,
            )
            return SynthesisResult(
                parse_error=str(last_exc),
                guardrail_warnings=[
                    f"Synthesis section failed after {attempts} attempt(s) "
                    f"(chunks {chunk_id_list}): {last_exc}"
                ],
                synthesis_failed=True,
            )

        # Sections are independent synthesis calls over disjoint parts of
        # the same object - nothing in one section's prompt or result
        # depends on another's, they are only combined afterward by
        # `merge_section_results`. Run them concurrently (same
        # ThreadPoolExecutor pattern, and the same `self.chunk_workers`
        # budget, already used for per-chunk extraction in
        # `_extract_all_chunks`) instead of one full network round-trip
        # after another: this is the dominant cost of Stage 5 for any
        # object large enough to need sectioning in the first place
        # (PRO.SMA_MARKING reliably needs 2-4 sections), and running them
        # sequentially wastes wall-clock time waiting on I/O with nothing
        # else happening, not on work that has to be serialized. Output is
        # unaffected - each section call and its content are identical to
        # the sequential version; only the scheduling changes, and
        # `LLMTelemetryTracker`/`PersistentLLMResponseCache` are already
        # relied on to be thread-safe by that same extraction-stage usage.
        worker_count = min(self.chunk_workers, len(sections))
        if worker_count <= 1:
            section_results = [_run_section(section) for section in sections]
        else:
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                section_results = list(executor.map(_run_section, sections))
        return RuleSynthesizerAgent.merge_section_results(section_results, merged_extraction)

    @staticmethod
    def _build_synthesis_input(merged_extraction: Dict[str, Any]) -> Dict[str, Any]:
        """Create the isolated, complete handoff sent to synthesis.

        Extraction and deterministic SQL parsing produce different views of
        the same object. They must be merged before synthesis, but the
        synthesis agent must not receive a live reference to the pipeline's
        reconciliation/formatting state. A deep copy also prevents provider
        clients or post-processing from mutating the evidence later used for
        verification. Only recognized extraction sections are forwarded;
        run artifacts are attached after synthesis and therefore cannot leak
        into the model input.
        """
        if not isinstance(merged_extraction, dict):
            return {}
        allowed_sections = {
            "conditions",
            "decision_chains",
            "loops",
            "tables_read",
            "tables_written",
            "table_operations",
            "calculations",
            "exception_handling",
            "ambiguities",
            "chunk_provenance",
            "statement_provenance",
            "llm_tables_read",
            "llm_tables_written",
            "semantic_findings",
            "statement_dependencies",
        }
        return copy.deepcopy(
            {
                key: value
                for key, value in merged_extraction.items()
                if key in allowed_sections
            }
        )

    @staticmethod
    def _reconciliation_review_findings(reconciliation: Any) -> list[str]:
        """Turn every unresolved reconciliation result into a report finding."""
        findings: list[str] = []
        for record in getattr(reconciliation, "records", []) or []:
            status = str(
                record.get("status", "") if isinstance(record, dict)
                else getattr(record, "status", "")
                or ""
            ).upper()
            if status not in {"CONFLICT", "UNRESOLVED", "LLM_ONLY", "DETERMINISTIC_ONLY"}:
                continue
            kind = str(
                record.get("kind", "evidence") if isinstance(record, dict)
                else getattr(record, "kind", "evidence")
                or "evidence"
            )
            findings.append(
                f"Reconciliation review required: {kind} evidence is {status.lower()} "
                "and must not be treated as a confirmed business rule."
            )
        for contradiction in getattr(reconciliation, "contradictions", []) or []:
            explanation = str(
                contradiction.get("explanation", "") if isinstance(contradiction, dict)
                else getattr(contradiction, "explanation", "")
                or ""
            ).strip()
            if explanation:
                findings.append(f"Reconciliation detected a source/report discrepancy: {explanation}")
        return list(dict.fromkeys(findings))

    @staticmethod
    def _summarize_parameters(ingestion: IngestionResult) -> str:
        if ingestion.parameter_parse_status == "failed":
            return "Parameter extraction failed / Needs Review."
        if not ingestion.parameters:
            return "No parameters."
        return "; ".join(
            f"{p.name} ({p.direction} {p.datatype})" for p in ingestion.parameters
        )

    @staticmethod
    def _resolve_chunk_workers(chunk_workers: Optional[int]) -> int:
        if chunk_workers is not None:
            return max(1, int(chunk_workers))
        raw = os.environ.get("PIPELINE_CHUNK_WORKERS", "").strip()
        if raw:
            try:
                return max(1, int(raw))
            except ValueError:
                logger.warning("Invalid PIPELINE_CHUNK_WORKERS=%r; defaulting to %d", raw, DEFAULT_CHUNK_WORKERS)
        return DEFAULT_CHUNK_WORKERS