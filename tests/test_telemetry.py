from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.pipeline_utils import RunMetadata, attach_run_telemetry, run_metadata_to_dict
from src.ingestion.ingestion import CodeChunk, IngestionResult
from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import SynthesisResult
from src.telemetry.aggregator import aggregate_token_usage
from src.telemetry.models import TokenUsage
from src.telemetry.tracker import LLMTelemetryTracker


class _UsageObject:
    def __init__(self, prompt_tokens=None, completion_tokens=None, total_tokens=None):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class _Response:
    def __init__(self, usage):
        self.usage = usage


class _BrokenUsageResponse:
    @property
    def usage(self):  # pragma: no cover - exercised for failure safety
        raise RuntimeError("usage unavailable")


def _ingestion() -> IngestionResult:
    return IngestionResult(
        object_name="telemetry_demo",
        object_type="PROCEDURE",
        parameters=[],
        raw_code="SELECT 1 FROM dual",
        chunks=[CodeChunk(chunk_id="chunk_1", kind="main_body", text="SELECT 1 FROM dual")],
        object_id="obj_telemetry",
        dialect="ORACLE",
        concrete_dialect="oracle",
        fallback_dialect="oracle",
        source_hash="hash",
        source_filename="demo.sql",
    )


def _synthesis() -> SynthesisResult:
    return SynthesisResult(
        data={
            "purpose_summary": "Demo.",
            "step_by_step_flow": [],
            "business_rules": [],
            "calculations": [],
            "exception_handling_summary": "",
            "ambiguities": [],
        }
    )


def test_token_usage_supports_complete_partial_and_unavailable_values():
    complete = TokenUsage.from_any({"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
    assert complete.availability == "available"
    assert complete.total_tokens == 15

    partial = TokenUsage.from_any(_UsageObject(prompt_tokens=4))
    assert partial.availability == "partial"
    assert partial.prompt_tokens == 4
    assert partial.total_tokens is None

    unavailable = TokenUsage.from_any(None)
    assert unavailable.availability == "unavailable"
    assert unavailable.to_dict() == {"availability": "unavailable"}


def test_aggregate_token_usage_does_not_invent_zeroes():
    usage = aggregate_token_usage(
        [
            TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, availability="available"),
            TokenUsage(prompt_tokens=None, completion_tokens=2, total_tokens=None, availability="partial"),
        ]
    )
    assert usage.availability == "partial"
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 7
    assert usage.total_tokens == 15


def test_tracker_records_multiple_calls_and_stage_breakdown():
    tracker = LLMTelemetryTracker()
    tracker.record_call(
        stage="extraction",
        provider="openai",
        model_name="demo-model",
        response=_Response({"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}),
        latency_seconds=0.25,
        success=True,
    )
    tracker.record_call(
        stage="synthesis",
        provider="openai",
        model_name="demo-model",
        response=_Response(_UsageObject(prompt_tokens=18, completion_tokens=9, total_tokens=27)),
        latency_seconds=0.5,
        success=True,
    )

    telemetry = tracker.snapshot("run_123")
    assert telemetry.run_id == "run_123"
    assert telemetry.totals.total_tokens == 47
    assert telemetry.stage_breakdown["extraction"]["call_count"] == 1
    assert telemetry.stage_breakdown["synthesis"]["token_usage"]["total_tokens"] == 27


def test_tracker_is_thread_safe_for_concurrent_calls():
    tracker = LLMTelemetryTracker()

    def _record(index: int) -> None:
        tracker.record_call(
            stage="extraction" if index % 2 == 0 else "synthesis",
            provider="openai",
            model_name="demo-model",
            response=_Response({"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}),
            latency_seconds=0.01,
            success=True,
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(_record, range(24)))

    telemetry = tracker.snapshot("run_threaded")
    assert telemetry.to_dict()["call_count"] == 24
    assert telemetry.stage_breakdown["extraction"]["call_count"] == 12
    assert telemetry.stage_breakdown["synthesis"]["call_count"] == 12


def test_tracker_never_raises_when_usage_is_unavailable():
    tracker = LLMTelemetryTracker()
    tracker.record_call(
        stage="extraction",
        provider="openai",
        model_name="demo-model",
        response=_BrokenUsageResponse(),
        latency_seconds=0.02,
        success=True,
    )
    telemetry = tracker.snapshot("run_broken")
    payload = telemetry.to_dict()
    assert payload["call_count"] == 1
    assert payload["call_metrics"][0]["token_usage"]["availability"] == "unavailable"


def test_run_metadata_serializes_telemetry_and_verification_only():
    tracker = LLMTelemetryTracker()
    tracker.record_call(
        stage="extraction",
        provider="openai",
        model_name="demo-model",
        response=_Response({"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13}),
        latency_seconds=0.3,
        success=True,
    )
    telemetry = tracker.snapshot("run_meta")
    run_metadata = RunMetadata(
        pipeline_version="v1",
        prompt_version="p1",
        knowledge_base_version="kb1",
        model_name="demo-model",
        provider="openai",
        dialect="oracle",
        dialect_confidence="high",
        source_hash="hash",
        configuration_version="cfg1",
        run_timestamp="2026-08-28T00:00:00+00:00",
        object_id="obj_telemetry",
    )
    run_metadata = attach_run_telemetry(run_metadata, telemetry.to_dict())
    serialized = run_metadata_to_dict(run_metadata)
    assert serialized["telemetry"]["run_id"] == "run_meta"
    assert serialized["telemetry"]["totals"]["total_tokens"] == 13

    ingestion = _ingestion()
    ingestion.run_metadata = run_metadata
    report = ReportFormatterAgent().format(ingestion=ingestion, merged_extraction={}, synthesis=_synthesis())
    verification = ReportFormatterAgent().format_verification(
        ingestion=ingestion,
        merged_extraction={},
        synthesis=_synthesis(),
    )
    assert "LLM Telemetry" not in report
    assert "## LLM Telemetry" in verification
    assert "Total Tokens" in verification
