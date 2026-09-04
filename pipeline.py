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
from typing import Any, Callable, Dict, List, Optional

from src.ingestion.ingestion import CodeIngestionAgent, IngestionResult, build_object_identity_stem
from src.retrieval.retriever import PatternRetrievalAgent
from src.extraction.logic_extractor import LogicExtractionAgent, ChunkExtraction
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from src.output.report_formatter import ReportFormatterAgent
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks, split_table_operations
from src.ingestion.guardrails import InputGuardrailError, run_input_guardrails, strip_inactive_code_for_llm
from src.dialect.detector import UnsupportedDialectError, detect_dialect
from src.core.llm_client import LLMConfig, create_llm_client, load_llm_config
from src.core.llm_response_cache import PersistentLLMResponseCache
from src.validation.confidence import derive_chunk_support_confidence
from src.validation.reconciliation import reconcile_deterministic_evidence
from src.validation.semantic_validation import (
    extract_procedural_decision_chains,
    extract_nested_decision_chains,
    extract_case_assignment_decision_chains,
    merge_decision_chains,
    find_semantic_anomalies,
)
from src.validation.coverage_check import find_coverage_gaps, format_gap_for_ambiguity
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
        max_chunk_chars: int = 6000,
        retrieval_k: int = 4,
        chunk_workers: Optional[int] = None,
        dialect: str = "auto",
        extraction_max_tokens: int = DEFAULT_EXTRACTION_MAX_TOKENS,
        synthesis_max_tokens: int = DEFAULT_SYNTHESIS_MAX_TOKENS,
        max_coverage_retries: int = DEFAULT_COVERAGE_RETRIES,
        single_pass_token_budget: Optional[int] = None,
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
        # Keep the benchmark-facing handle for explicit opt-in runs, but do
        # not enable persistent caching in the normal application pipeline.
        self.response_cache = PersistentLLMResponseCache(enabled=False)
        self.client = create_llm_client(self.llm_config)

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
        )

        self.synthesizer_agent = RuleSynthesizerAgent(
            client=self.client,
            model=self.model_name,
            temperature=temperature,
            seed=seed,
            provider=self.provider,
            response_cache=self.response_cache,
            max_tokens=synthesis_max_tokens,
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
        procedural_ladder_chains = (
            extract_nested_decision_chains(ingestion.raw_code)
            or extract_procedural_decision_chains(ingestion.raw_code)
        )
        case_expression_chains = extract_case_assignment_decision_chains(ingestion.raw_code)
        deterministic_chains = case_expression_chains + procedural_ladder_chains
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
        if table_operations:
            merged_extraction["table_operations"] = table_operations
            merged_extraction["tables_read"], merged_extraction["tables_written"] = (
                split_table_operations(table_operations)
            )
        synthesis_input = self._build_synthesis_input(merged_extraction)
        parameter_summary = self._summarize_parameters(ingestion)
        synthesis = self.synthesizer_agent.synthesize(
            object_name=ingestion.object_name,
            object_type=ingestion.object_type,
            parameter_summary=parameter_summary,
            merged_extraction=synthesis_input,
            dialect=analysis_dialect or ingestion.dialect,
            raw_source=ingestion.raw_code,
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
            synthesis.data["business_rules"] = revision.data.get(
                "business_rules", synthesis.data.get("business_rules", [])
            )
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
            gap_findings = [format_gap_for_ambiguity(gap) for gap in coverage_gaps]
            merged_extraction["ambiguities"].extend(gap_findings)
            synthesis.data["ambiguities"] = list(synthesis.data.get("ambiguities", []) or [])
            synthesis.data["ambiguities"].extend(gap_findings)

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