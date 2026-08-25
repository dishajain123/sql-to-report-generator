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
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from agents.ingestion import CodeIngestionAgent, IngestionResult
from agents.retriever import PatternRetrievalAgent
from agents.logic_extractor import LogicExtractionAgent, ChunkExtraction
from agents.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from agents.report_formatter import ReportFormatterAgent
from technical_sql_ops import extract_table_operations_from_chunks, split_table_operations
from guardrails import InputGuardrailError, run_input_guardrails
from dialect_detector import UnsupportedDialectError, detect_dialect
from llm_client import LLMConfig, create_llm_client, load_llm_config

logger = logging.getLogger("logic_rules_extractor.pipeline")

DEFAULT_TEMPERATURE = 0.1  # low temperature: this is an extraction task, not creative writing

# Stage 4 (embedded SQL / per-chunk technical extraction) is the slowest
# stage because it makes one LLM call per chunk. Chunks are independent, so
# they're extracted concurrently; 4 workers was overly conservative for
# typical stored-procedure sizes (10-60 chunks) and left most of the run
# serialized. Bump the out-of-the-box default and let PIPELINE_CHUNK_WORKERS
# override it per environment (e.g. lower it back down if the LLM provider's
# rate limit needs it).
DEFAULT_CHUNK_WORKERS = 8


class PipelineInputError(ValueError):
    """Raised when the input source cannot be safely processed at all
    (fails input guardrails before any parsing or LLM call is made).
    """


class LogicRulesExtractorPipeline:
    """End-to-end coordinator for the AI-Powered DB Logic & Business
    Rules Extractor.
    """

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        persist_directory: str = "chroma_store",
        knowledge_base_dir: str = "knowledge_base",
        max_chunk_chars: int = 6000,
        retrieval_k: int = 4,
        chunk_workers: Optional[int] = None,
        dialect: str = "auto",
    ):
        self.llm_config = llm_config or load_llm_config()
        self.model_name = self.llm_config.model_name
        self.retrieval_k = retrieval_k
        self.chunk_workers = self._resolve_chunk_workers(chunk_workers)
        self.dialect = dialect

        self.client = create_llm_client(self.llm_config)

        self.ingestion_agent = CodeIngestionAgent(max_chunk_chars=max_chunk_chars, dialect=dialect)
        self.retrieval_agent = PatternRetrievalAgent(
            persist_directory=persist_directory,
            knowledge_base_dir=knowledge_base_dir,
        )
        self.extraction_agent = LogicExtractionAgent(
            client=self.client, model=self.model_name, temperature=temperature
        )

        self.synthesizer_agent = RuleSynthesizerAgent(
            client=self.client, model=self.model_name, temperature=temperature
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
    ) -> str:
        """Run the full pipeline against a single .sql input file and
        return the final Markdown report as a string.

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
        _report_progress(
            f"Detected {detection.dialect} dialect (confidence: {detection.confidence})"
        )

        stage_2_seconds = time.perf_counter() - stage_start
        logger.info("Stage 2/6 completed in %.2fs (dialect detection)", stage_2_seconds)

        _report_progress(f"Stage 3/6: Preprocessing, parsing, and chunking {sql_file_path}")
        stage_start = time.perf_counter()
        try:
            ingestion = self.ingestion_agent.ingest_text(
                guard_result.clean_code,
                dialect=detection.dialect,
                source_filename=sql_file_path,
                prevalidated_code=guard_result.clean_code,
                prevalidated_warnings=guard_result.warnings,
                prevalidated_injection_flags=guard_result.injection_flags,
                detection_result=detection,
            )
        except UnsupportedDialectError as exc:
            raise PipelineInputError(str(exc)) from exc
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
        kb_start = time.perf_counter()
        self.retrieval_agent.build_or_load()
        kb_seconds = time.perf_counter() - kb_start
        if kb_seconds > 0:
            logger.info("Persistent knowledge base ready in %.2fs", kb_seconds)
        chunk_extractions = self._extract_all_chunks(ingestion)
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
        merged_extraction = self._merge_extractions(chunk_extractions)
        table_operations, statement_provenance = extract_table_operations_from_chunks(
            ingestion.chunks, ingestion.dialect
        )
        merged_extraction["statement_provenance"] = statement_provenance
        if table_operations:
            merged_extraction["llm_tables_read"] = list(merged_extraction.get("tables_read", []))
            merged_extraction["llm_tables_written"] = list(
                merged_extraction.get("tables_written", [])
            )
            merged_extraction["table_operations"] = table_operations
            merged_extraction["tables_read"], merged_extraction["tables_written"] = (
                split_table_operations(table_operations)
            )
        parameter_summary = self._summarize_parameters(ingestion)
        synthesis = self.synthesizer_agent.synthesize(
            object_name=ingestion.object_name,
            object_type=ingestion.object_type,
            parameter_summary=parameter_summary,
            merged_extraction=merged_extraction,
            dialect=ingestion.dialect,
            raw_source=ingestion.raw_code,
        )
        logger.info("Stage 5/6 completed in %.2fs (business reasoning)", time.perf_counter() - stage_start)

        _report_progress("Stage 6/6: Applying output guardrails and formatting final report")
        stage_start = time.perf_counter()
        report = self.formatter_agent.format(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
            extraction_guardrail_warnings=extraction_guardrail_warnings,
        )
        logger.info("Stage 6/6 completed in %.2fs (final report generation)", time.perf_counter() - stage_start)
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_source_file(sql_file_path: str) -> str:
        # Delegates the extension/existence check to the ingestion
        # agent's own loader so there is exactly one place that owns
        # "what file types are accepted".
        return CodeIngestionAgent._load_file(sql_file_path)

    def _extract_all_chunks(
        self, ingestion: IngestionResult
    ) -> list[ChunkExtraction]:
        if not ingestion.chunks:
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
        try:
            extraction = self.extraction_agent.extract(
                chunk_id=chunk.chunk_id,
                chunk_kind=chunk.kind,
                code_chunk=chunk.text,
                rag_context=rag_context,
                object_type=ingestion.object_type,
                object_name=ingestion.object_name,
                chunk_context=chunk.context_path,
                embedded_sql=chunk.embedded_sql,
                dialect=ingestion.dialect,
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
    def _chunk_cache_key(ingestion: IngestionResult, chunk, rag_context: str) -> str:
        payload = "|".join(
            [
                ingestion.object_type,
                ingestion.object_name,
                ingestion.dialect,
                chunk.kind,
                " > ".join(chunk.context_path or []),
                chunk.text,
                "\n".join(chunk.embedded_sql or []),
                rag_context,
            ]
        )
        return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()

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
    def _merge_extractions(chunk_extractions: list[ChunkExtraction]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {
            "conditions": [],
            "loops": [],
            "tables_read": [],
            "tables_written": [],
            "calculations": [],
            "exception_handling": [],
            "ambiguities": [],
            "chunk_provenance": [],
        }
        for extraction in chunk_extractions:
            merged["chunk_provenance"].append(
                {
                    "chunk_id": extraction.chunk_id,
                    "chunk_kind": extraction.chunk_kind,
                    "chunk_context": extraction.chunk_context,
                    "embedded_sql": extraction.embedded_sql,
                    "parse_error": extraction.parse_error,
                    "guardrail_warnings": extraction.guardrail_warnings,
                    "support_confidence": (
                        "low"
                        if extraction.parse_error
                        else ("medium" if extraction.guardrail_warnings else "high")
                    ),
                }
            )
            for key in merged:
                if key == "chunk_provenance":
                    continue
                for item in extraction.data.get(key, []) or []:
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
                            (
                                "low"
                                if extraction.parse_error
                                else ("medium" if extraction.guardrail_warnings else "high")
                            ),
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