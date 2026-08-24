"""
pipeline.py
------------
Central orchestrator (`LogicRulesExtractorPipeline`) that wires together
the five agents into the end-to-end Agentic RAG flow:

    1. CodeIngestionAgent      -> parse, detect type, chunk
    2. PatternRetrievalAgent   -> per-chunk RAG context
    3. LogicExtractionAgent    -> per-chunk technical extraction
    4. RuleSynthesizerAgent    -> whole-object business rule synthesis
    5. ReportFormatterAgent    -> final Markdown report

This orchestration is plain Python - there is no agent framework
involved. "Running the pipeline" just means calling each agent's
methods in order and passing data between them via ordinary Python
objects/dicts.

The Groq-backed LLM is configurable at the call level (model name is
passed in at construction time, defaulting to an env var / CLI flag),
so callers can freely switch between e.g. `llama-3.3-70b-versatile` and
`llama-3.1-8b-instant` without any code changes. A single `groq.Groq`
client is created once and shared by both LLM-calling agents.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, Optional

import time

from groq import Groq

from agents.ingestion import CodeIngestionAgent, IngestionResult
from agents.retriever import PatternRetrievalAgent
from agents.logic_extractor import LogicExtractionAgent, ChunkExtraction
from agents.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from agents.report_formatter import ReportFormatterAgent

logger = logging.getLogger("logic_rules_extractor.pipeline")

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TEMPERATURE = 0.1  # low temperature: this is an extraction task, not creative writing


class LogicRulesExtractorPipeline:
    """End-to-end coordinator for the AI-Powered DB Logic & Business
    Rules Extractor.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        groq_api_key: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        persist_directory: str = "chroma_store",
        knowledge_base_dir: str = "knowledge_base",
        max_chunk_chars: int = 6000,
        retrieval_k: int = 4,
    ):
        api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. Add it to your .env file or pass it "
                "explicitly to LogicRulesExtractorPipeline(groq_api_key=...)."
            )

        self.model_name = model_name
        self.retrieval_k = retrieval_k

        self.client = Groq(api_key=api_key)

        self.ingestion_agent = CodeIngestionAgent(max_chunk_chars=max_chunk_chars)
        self.retrieval_agent = PatternRetrievalAgent(
            persist_directory=persist_directory,
            knowledge_base_dir=knowledge_base_dir,
        )
        self.extraction_agent = LogicExtractionAgent(
            client=self.client, model=model_name, temperature=temperature
        )

        self.synthesizer_agent = RuleSynthesizerAgent(
            client=self.client, model=model_name, temperature=temperature
        )
        self.formatter_agent = ReportFormatterAgent()

        self.retrieval_agent.build_or_load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        sql_file_path: str,
        model_name: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Run the full pipeline against a single .sql input file and
        return the final Markdown report as a string.

        Args:
            sql_file_path: path to the input .sql file.
            model_name: optional Groq model override for this run only
                (defaults to the model the pipeline was constructed with).
                Lets a caller - e.g. a UI model-switcher - pick a
                different model per run without rebuilding the RAG store
                or re-creating the Groq client.
            progress_callback: optional callable invoked with a short
                human-readable status string at the start of each stage
                (e.g. to drive a UI progress indicator).
        """

        def _report_progress(message: str) -> None:
            logger.info(message)
            if progress_callback:
                progress_callback(message)

        effective_model = model_name or self.model_name

        _report_progress(f"Stage 1/5: Ingesting {sql_file_path}")
        ingestion = self.ingestion_agent.ingest(sql_file_path)
        _report_progress(
            f"Detected {ingestion.object_type} '{ingestion.object_name}' "
            f"with {len(ingestion.chunks)} chunk(s)"
        )

        _report_progress(
            f"Stage 2/5 + 3/5: Retrieving pattern context and extracting logic "
            f"per chunk (model: {effective_model})"
        )
        chunk_extractions = self._extract_all_chunks(ingestion, model=effective_model)

        # WARN: Remove
        sleep_time = 20
        logger.info(f"Sleeping for {sleep_time} Seconds")
        time.sleep(sleep_time)


        _report_progress("Stage 4/5: Synthesizing business rules")
        merged_extraction = self._merge_extractions(chunk_extractions)
        parameter_summary = self._summarize_parameters(ingestion)
        synthesis = self.synthesizer_agent.synthesize(
            object_name=ingestion.object_name,
            object_type=ingestion.object_type,
            parameter_summary=parameter_summary,
            merged_extraction=merged_extraction,
            model=effective_model,
        )

        _report_progress("Stage 5/5: Formatting final report")
        report = self.formatter_agent.format(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
        )
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_all_chunks(
        self, ingestion: IngestionResult, model: Optional[str] = None
    ) -> list[ChunkExtraction]:
        results: list[ChunkExtraction] = []
        for chunk in ingestion.chunks:
            query = self._build_retrieval_query(ingestion, chunk)
            rag_context = self.retrieval_agent.retrieve_context_text(
                query, k=self.retrieval_k
            )
            extraction = self.extraction_agent.extract(
                chunk_id=chunk.chunk_id,
                chunk_kind=chunk.kind,
                code_chunk=chunk.text,
                rag_context=rag_context,
                object_type=ingestion.object_type,
                object_name=ingestion.object_name,
                model=model,
            )
            results.append(extraction)
        return results

    @staticmethod
    def _build_retrieval_query(ingestion: IngestionResult, chunk) -> str:
        # Keep the retrieval query short and construct-focused so the
        # vector search surfaces the most relevant pattern docs.
        snippet = chunk.text[:400]
        return f"{ingestion.object_type} {chunk.kind} banking logic: {snippet}"

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
        }
        for extraction in chunk_extractions:
            for key in merged:
                merged[key].extend(extraction.data.get(key, []) or [])
            if extraction.parse_error:
                merged["ambiguities"].append(
                    f"Chunk '{extraction.chunk_id}' ({extraction.chunk_kind}) technical "
                    "extraction returned malformed JSON and needs manual review."
                )
        return merged

    @staticmethod
    def _summarize_parameters(ingestion: IngestionResult) -> str:
        if not ingestion.parameters:
            return "No parameters."
        return "; ".join(
            f"{p.name} ({p.direction} {p.datatype})" for p in ingestion.parameters
        )
