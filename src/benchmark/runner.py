from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from types import MethodType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.core.llm_response_cache import PersistentLLMResponseCache
from src.core.llm_client import load_llm_config
from src.core.pipeline_utils import (
    attach_run_telemetry,
    build_run_metadata,
    run_metadata_to_dict,
    stable_id,
)
from src.dialect.detector import detect_dialect
from src.ingestion.guardrails import run_input_guardrails
from src.ingestion.ingestion import CodeIngestionAgent
from src.ir.canonical_ir import CanonicalBusinessIR
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks, split_table_operations
from src.retrieval.retriever import PatternRetrievalAgent
from src.telemetry.tracker import LLMTelemetryTracker
from src.validation.reconciliation import reconcile_deterministic_evidence

from pipeline import LogicRulesExtractorPipeline, supported_analysis_dialect

from .models import (
    BenchmarkComparisonResult,
    BenchmarkRunConfig,
    BenchmarkRunRecord,
    BenchmarkTelemetry,
    BusinessOutputSnapshot,
    safe_percentage_change,
)


def _hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def _count_words(text: str) -> int:
    return len([token for token in str(text or "").split() if token])


def _merge_pipeline_kwargs(config: BenchmarkRunConfig) -> Dict[str, Any]:
    kwargs = dict(config.pipeline_kwargs or {})
    kwargs.setdefault("dialect", config.dialect)
    return kwargs


def _empty_business_snapshot() -> BusinessOutputSnapshot:
    return BusinessOutputSnapshot.from_pipeline_state({}, {})


def _execute_benchmark_run(config: BenchmarkRunConfig) -> BenchmarkRunRecord:
    pipeline = LogicRulesExtractorPipeline(**_merge_pipeline_kwargs(config))
    if config.cache_enabled is not None:
        pipeline.response_cache.enabled = bool(config.cache_enabled)

    raw_code = pipeline._read_source_file(config.sql_file_path)
    start_time = time.perf_counter()
    tracker = LLMTelemetryTracker()
    rag_chars = 0
    rag_blocks = 0
    rag_words = 0

    try:
        guard_result = run_input_guardrails(raw_code)
        detection = detect_dialect(guard_result.clean_code, hint=config.dialect)
        ingestion = pipeline.ingestion_agent.ingest_text(
            guard_result.clean_code,
            dialect=config.dialect,
            source_filename=config.sql_file_path,
            original_code=raw_code,
            prevalidated_code=guard_result.clean_code,
            prevalidated_warnings=guard_result.warnings,
            prevalidated_injection_flags=guard_result.injection_flags,
            detection_result=detection,
        )
        run_metadata = build_run_metadata(
            project_root=pipeline.project_root,
            model_name=pipeline.model_name,
            provider=pipeline.provider,
            dialect=ingestion.dialect,
            dialect_confidence=ingestion.dialect_confidence,
            raw_source=ingestion.raw_code,
            object_id=ingestion.object_id,
        )
        ingestion.run_metadata = run_metadata

        analysis_dialect = supported_analysis_dialect(ingestion)
        retrieval_original = pipeline.retrieval_agent.retrieve_context_text

        def _counting_retrieve_context_text(self, query: str, k: int = 4) -> str:
            nonlocal rag_chars, rag_blocks, rag_words
            context_text = retrieval_original(query, k=k)
            rag_chars += len(context_text)
            rag_blocks += context_text.count("[Source:")
            rag_words += _count_words(context_text)
            return context_text

        pipeline.retrieval_agent.retrieve_context_text = MethodType(
            _counting_retrieve_context_text, pipeline.retrieval_agent
        )
        pipeline.retrieval_agent.build_or_load()
        chunk_extractions = pipeline._extract_all_chunks(
            ingestion,
            run_metadata=run_metadata,
            analysis_dialect=analysis_dialect,
            telemetry_tracker=tracker,
        )
        merged_extraction = pipeline._merge_extractions(chunk_extractions, ingestion=ingestion)
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
            merged_extraction["tables_read"], merged_extraction["tables_written"] = split_table_operations(
                table_operations
            )
        parameter_summary = pipeline._summarize_parameters(ingestion)
        synthesis = pipeline.synthesizer_agent.synthesize(
            object_name=ingestion.object_name,
            object_type=ingestion.object_type,
            parameter_summary=parameter_summary,
            merged_extraction=merged_extraction,
            dialect=analysis_dialect or ingestion.dialect,
            raw_source=ingestion.raw_code,
            telemetry_tracker=tracker,
        )
        synthesis.data["run_metadata"] = run_metadata_to_dict(run_metadata)
        reconciliation = reconcile_deterministic_evidence(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
        )
        merged_extraction["reconciliation"] = reconciliation.to_dict()
        merged_extraction["coverage"] = reconciliation.coverage
        merged_extraction["quality"] = reconciliation.quality
        synthesis.data["reconciliation"] = reconciliation.to_dict()
        synthesis.data["coverage"] = reconciliation.coverage
        synthesis.data["quality"] = reconciliation.quality
        telemetry_run_id = stable_id(
            "telemetry",
            run_metadata.source_hash if run_metadata else "",
            run_metadata.configuration_version if run_metadata else "",
            run_metadata.run_timestamp if run_metadata else "",
        )
        telemetry_payload = tracker.snapshot(telemetry_run_id).to_dict()
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
        report = pipeline.formatter_agent.format(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
            canonical_ir=canonical_ir,
            extraction_guardrail_warnings=pipeline._collect_extraction_guardrail_warnings(chunk_extractions),
            run_metadata=run_metadata,
            verification_filename="benchmark_verification.md",
        )
        verification = pipeline.formatter_agent.format_verification(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
            canonical_ir=canonical_ir,
            run_metadata=run_metadata,
            report_filename="benchmark_report.md",
        )
        telemetry = BenchmarkTelemetry.from_telemetry_dict(
            input_file=config.sql_file_path,
            provider=pipeline.provider,
            model_name=pipeline.model_name,
            dialect=ingestion.dialect,
            telemetry=run_metadata.telemetry if run_metadata else {},
            rag_context_chars=rag_chars,
            rag_context_blocks=rag_blocks,
            rag_context_words=rag_words,
        )
        business = BusinessOutputSnapshot.from_pipeline_state(
            merged_extraction=merged_extraction,
            synthesis_data=synthesis.data,
        )
        return BenchmarkRunRecord(
            label=config.label,
            input_file=config.sql_file_path,
            model_name=pipeline.model_name,
            provider=pipeline.provider,
            dialect=ingestion.dialect,
            telemetry=telemetry,
            business=business,
            success=True,
            error="",
            report_hash=_hash_text(report),
            verification_hash=_hash_text(verification),
            rag_context_chars=rag_chars,
            rag_context_blocks=rag_blocks,
            rag_context_words=rag_words,
            report_text=report,
            verification_text=verification,
        )
    except Exception as exc:  # noqa: BLE001
        telemetry = BenchmarkTelemetry.from_telemetry_dict(
            input_file=config.sql_file_path,
            telemetry=tracker.snapshot("benchmark_error").to_dict() if tracker else {},
            rag_context_chars=rag_chars,
            rag_context_blocks=rag_blocks,
            rag_context_words=rag_words,
        )
        return BenchmarkRunRecord(
            label=config.label,
            input_file=config.sql_file_path,
            model_name=pipeline.model_name,
            provider=pipeline.provider,
            dialect=config.dialect,
            telemetry=telemetry,
            business=_empty_business_snapshot(),
            success=False,
            error=str(exc),
            report_hash="",
            verification_hash="",
            rag_context_chars=rag_chars,
            rag_context_blocks=rag_blocks,
            rag_context_words=rag_words,
        )


def run_benchmark_run(config: BenchmarkRunConfig) -> BenchmarkRunRecord:
    return _execute_benchmark_run(config)


def _compare_business_snapshots(
    baseline: BusinessOutputSnapshot, optimized: BusinessOutputSnapshot
) -> Tuple[bool, bool, List[str]]:
    semantic_equal = baseline.semantic_signature == optimized.semantic_signature
    wording_only = semantic_equal and (
        baseline.narrative_signature != optimized.narrative_signature
    )
    differences: List[str] = []
    baseline_payload = baseline.to_dict()
    optimized_payload = optimized.to_dict()
    for key in (
        "rule_count",
        "rule_signatures",
        "conditions_count",
        "decision_chain_count",
        "decision_branch_count",
        "calculations_count",
        "loops_count",
        "exceptions_count",
        "ambiguities_count",
        "tables_read",
        "tables_written",
        "operations",
    ):
        if baseline_payload.get(key) != optimized_payload.get(key):
            differences.append(key)
    if baseline.business_meanings != optimized.business_meanings:
        differences.append("business_meanings")
    if baseline.purpose_summary != optimized.purpose_summary:
        differences.append("purpose_summary")
    if baseline.step_by_step_flow != optimized.step_by_step_flow:
        differences.append("step_by_step_flow")
    return semantic_equal, wording_only, sorted(set(differences))


def compare_benchmark_runs(
    baseline: BenchmarkRunRecord,
    optimized: BenchmarkRunRecord,
) -> BenchmarkComparisonResult:
    business_equivalent, wording_only_difference, semantic_differences = _compare_business_snapshots(
        baseline.business, optimized.business
    )
    baseline_telemetry = baseline.telemetry
    optimized_telemetry = optimized.telemetry
    baseline_total_calls = None
    optimized_total_calls = None
    if baseline_telemetry.extraction_call_count is not None or baseline_telemetry.synthesis_call_count is not None:
        baseline_total_calls = int(baseline_telemetry.extraction_call_count or 0) + int(
            baseline_telemetry.synthesis_call_count or 0
        )
    if optimized_telemetry.extraction_call_count is not None or optimized_telemetry.synthesis_call_count is not None:
        optimized_total_calls = int(optimized_telemetry.extraction_call_count or 0) + int(
            optimized_telemetry.synthesis_call_count or 0
        )
    total_prompt_reduction = None
    total_completion_reduction = None
    total_token_reduction = None
    if baseline_telemetry.total_prompt_tokens is not None and optimized_telemetry.total_prompt_tokens is not None:
        total_prompt_reduction = int(baseline_telemetry.total_prompt_tokens) - int(optimized_telemetry.total_prompt_tokens)
    if baseline_telemetry.total_completion_tokens is not None and optimized_telemetry.total_completion_tokens is not None:
        total_completion_reduction = int(baseline_telemetry.total_completion_tokens) - int(
            optimized_telemetry.total_completion_tokens
        )
    if baseline_telemetry.total_tokens is not None and optimized_telemetry.total_tokens is not None:
        total_token_reduction = int(baseline_telemetry.total_tokens) - int(optimized_telemetry.total_tokens)
    call_reduction = None
    if baseline_total_calls is not None and optimized_total_calls is not None:
        call_reduction = baseline_total_calls - optimized_total_calls
    latency_change = None
    if baseline_telemetry.latency_seconds is not None and optimized_telemetry.latency_seconds is not None:
        latency_change = baseline_telemetry.latency_seconds - optimized_telemetry.latency_seconds

    return BenchmarkComparisonResult(
        baseline=baseline,
        optimized=optimized,
        business_equivalent=business_equivalent,
        markdown_text_changed=baseline.report_text != optimized.report_text,
        wording_only_difference=wording_only_difference or (
            business_equivalent and baseline.report_text != optimized.report_text
        ),
        semantic_regression=not business_equivalent,
        semantic_differences=semantic_differences,
        token_reduction_percent=safe_percentage_change(
            baseline_telemetry.total_tokens, optimized_telemetry.total_tokens
        ),
        prompt_token_reduction_percent=safe_percentage_change(
            baseline_telemetry.total_prompt_tokens, optimized_telemetry.total_prompt_tokens
        ),
        completion_token_reduction_percent=safe_percentage_change(
            baseline_telemetry.total_completion_tokens, optimized_telemetry.total_completion_tokens
        ),
        call_reduction_percent=safe_percentage_change(baseline_total_calls, optimized_total_calls),
        latency_change_percent=safe_percentage_change(
            baseline_telemetry.latency_seconds, optimized_telemetry.latency_seconds
        ),
        cache_hit_rate_baseline=baseline_telemetry.cache_hit_rate,
        cache_hit_rate_optimized=optimized_telemetry.cache_hit_rate,
        total_token_reduction=total_token_reduction,
        prompt_token_reduction=total_prompt_reduction,
        completion_token_reduction=total_completion_reduction,
        call_reduction=call_reduction,
        latency_change_seconds=latency_change,
    )


def run_benchmark_pair(
    baseline_config: BenchmarkRunConfig,
    optimized_config: BenchmarkRunConfig,
) -> BenchmarkComparisonResult:
    baseline = run_benchmark_run(baseline_config)
    optimized = run_benchmark_run(optimized_config)
    return compare_benchmark_runs(baseline, optimized)
