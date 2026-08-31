from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.benchmark.models import (
    BenchmarkComparisonResult,
    BenchmarkRunRecord,
    BenchmarkTelemetry,
    BusinessOutputSnapshot,
    safe_percentage_change,
)
from src.benchmark.runner import compare_benchmark_runs


def _telemetry(
    *,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    extraction_calls: int | None,
    synthesis_calls: int | None,
    cache_hits: int | None = None,
    cache_misses: int | None = None,
    extraction_latency: float | None = None,
    synthesis_latency: float | None = None,
) -> BenchmarkTelemetry:
    stage_breakdown = {
        "extraction": {
            "call_count": extraction_calls,
            "latency_seconds": extraction_latency,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        },
        "synthesis": {
            "call_count": synthesis_calls,
            "latency_seconds": synthesis_latency,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        },
    }
    telemetry = {
        "totals": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "stage_breakdown": stage_breakdown,
        "cache_hit_count": cache_hits,
        "cache_miss_count": cache_misses,
        "success_count": 3,
        "failure_count": 0,
    }
    return BenchmarkTelemetry.from_telemetry_dict(
        input_file="sample.sql",
        provider="openai",
        model_name="gpt-4.1",
        dialect="oracle",
        telemetry=telemetry,
        rag_context_chars=123,
        rag_context_blocks=2,
        rag_context_words=24,
    )


def _business_snapshot(
    *, meaning_suffix: str = "", condition_suffix: str = "", rule_condition_suffix: str = ""
) -> BusinessOutputSnapshot:
    merged_extraction = {
        "conditions": [{"condition": f"overdue_days > 90{condition_suffix}"}],
        "decision_chains": [
            {
                "branches": [
                    {"condition": "overdue_days > 90", "outcome": "HIGH"},
                    {"condition": "else", "outcome": "LOW"},
                ]
            }
        ],
        "calculations": [{"metric": "provision"}],
        "loops": [{"kind": "cursor"}],
        "exception_handling": [{"kind": "catch"}],
        "ambiguities": ["needs review"],
        "tables_read": [{"table": "dbo.Account"}],
        "tables_written": [{"table": "dbo.AccountAudit"}],
        "table_operations": [
            {"operation": "READ", "table": "dbo.Account"},
            {"operation": "UPDATE", "table": "dbo.Account"},
        ],
    }
    synthesis = {
        "purpose_summary": "Determine overdue status" + meaning_suffix,
        "step_by_step_flow": ["Read account", "Update status"],
        "business_rules": [
            {
                "rule_name": "Update account status",
                "rule_type": "explicit",
                "condition": f"overdue_days > 90{rule_condition_suffix}",
                "action": "set status to overdue",
                "output_field": "Status",
                "fields_affected": ["Status"],
                "decision_logic_rows": [
                    {"condition": "overdue_days > 90", "outcome": "OVERDUE", "output_field": "Status"}
                ],
                "reconciliation_status": "MATCHED",
                "business_meaning": "Accounts are marked overdue when days overdue exceed 90" + meaning_suffix,
            }
        ],
    }
    return BusinessOutputSnapshot.from_pipeline_state(
        merged_extraction=merged_extraction,
        synthesis_data=synthesis,
    )


def _run_record(
    *,
    label: str,
    telemetry: BenchmarkTelemetry,
    business: BusinessOutputSnapshot,
    report_text: str,
) -> BenchmarkRunRecord:
    return BenchmarkRunRecord(
        label=label,
        input_file="sample.sql",
        model_name="gpt-4.1",
        provider="openai",
        dialect="oracle",
        telemetry=telemetry,
        business=business,
        success=True,
        report_hash="hash-" + label,
        verification_hash="ver-" + label,
        rag_context_chars=telemetry.rag_context_chars,
        rag_context_blocks=telemetry.rag_context_blocks,
        rag_context_words=telemetry.rag_context_words,
        report_text=report_text,
        verification_text="verification " + label,
    )


def test_benchmark_telemetry_aggregation_and_cache_hit_rate():
    telemetry = _telemetry(
        prompt_tokens=100,
        completion_tokens=40,
        total_tokens=140,
        extraction_calls=2,
        synthesis_calls=1,
        cache_hits=3,
        cache_misses=1,
        extraction_latency=1.25,
        synthesis_latency=0.75,
    )

    assert telemetry.total_prompt_tokens == 100
    assert telemetry.total_completion_tokens == 40
    assert telemetry.total_tokens == 140
    assert telemetry.extraction_call_count == 2
    assert telemetry.synthesis_call_count == 1
    assert telemetry.total_call_count == 3
    assert telemetry.cache_hit_rate == 0.75
    assert telemetry.latency_seconds == 2.0


def test_benchmark_missing_telemetry_remains_unavailable():
    telemetry = BenchmarkTelemetry.from_telemetry_dict(
        input_file="sample.sql",
        telemetry={},
    )

    assert telemetry.extraction_call_count is None
    assert telemetry.total_prompt_tokens is None
    assert telemetry.total_tokens is None
    assert telemetry.cache_hit_rate is None


def test_benchmark_percentage_calculations():
    assert safe_percentage_change(100, 80) == 20.0
    assert safe_percentage_change(100, 100) == 0.0
    assert safe_percentage_change(None, 80) is None
    assert safe_percentage_change(0, 80) is None


def test_benchmark_baseline_vs_optimized_comparison_reports_semantic_equivalence():
    baseline = _run_record(
        label="baseline",
        telemetry=_telemetry(
            prompt_tokens=100,
            completion_tokens=40,
            total_tokens=140,
            extraction_calls=2,
            synthesis_calls=1,
            cache_hits=2,
            cache_misses=1,
            extraction_latency=1.0,
            synthesis_latency=1.0,
        ),
        business=_business_snapshot(),
        report_text="rule one\nrule two",
    )
    optimized = _run_record(
        label="optimized",
        telemetry=_telemetry(
            prompt_tokens=80,
            completion_tokens=30,
            total_tokens=110,
            extraction_calls=1,
            synthesis_calls=1,
            cache_hits=3,
            cache_misses=0,
            extraction_latency=0.8,
            synthesis_latency=0.7,
        ),
        business=_business_snapshot(meaning_suffix=""),
        report_text="rule one changed wording\nrule two changed wording",
    )

    comparison = compare_benchmark_runs(baseline, optimized)

    assert comparison.business_equivalent is True
    assert comparison.wording_only_difference is True
    assert comparison.semantic_regression is False
    assert comparison.token_reduction_percent == 21.4286
    assert comparison.prompt_token_reduction_percent == 20.0
    assert comparison.completion_token_reduction_percent == 25.0
    assert comparison.call_reduction_percent == 33.3333
    assert comparison.cache_hit_rate_baseline == 0.666667
    assert comparison.cache_hit_rate_optimized == 1.0


def test_benchmark_detects_semantic_output_difference():
    baseline = _run_record(
        label="baseline",
        telemetry=_telemetry(
            prompt_tokens=100,
            completion_tokens=40,
            total_tokens=140,
            extraction_calls=2,
            synthesis_calls=1,
        ),
        business=_business_snapshot(),
        report_text="same",
    )
    optimized = _run_record(
        label="optimized",
        telemetry=_telemetry(
            prompt_tokens=90,
            completion_tokens=35,
            total_tokens=125,
            extraction_calls=2,
            synthesis_calls=1,
        ),
        business=_business_snapshot(rule_condition_suffix=" and status = 'OPEN'"),
        report_text="same",
    )

    comparison = compare_benchmark_runs(baseline, optimized)

    assert comparison.business_equivalent is False
    assert comparison.semantic_regression is True
    assert "rule_signatures" in comparison.semantic_differences or "conditions_count" in comparison.semantic_differences


def test_benchmark_serialization_and_markdown_summary():
    baseline = _run_record(
        label="baseline",
        telemetry=_telemetry(
            prompt_tokens=100,
            completion_tokens=40,
            total_tokens=140,
            extraction_calls=2,
            synthesis_calls=1,
            cache_hits=1,
            cache_misses=1,
        ),
        business=_business_snapshot(),
        report_text="baseline report",
    )
    optimized = _run_record(
        label="optimized",
        telemetry=_telemetry(
            prompt_tokens=80,
            completion_tokens=30,
            total_tokens=110,
            extraction_calls=1,
            synthesis_calls=1,
            cache_hits=2,
            cache_misses=0,
        ),
        business=_business_snapshot(),
        report_text="optimized report",
    )
    comparison = compare_benchmark_runs(baseline, optimized)
    payload = json.loads(comparison.to_json())

    assert payload["business_equivalent"] is True
    assert payload["baseline"]["telemetry"]["cache_hit_rate"] == 0.5
    assert "LLM Efficiency Benchmark" in comparison.to_markdown()
    assert "Business output: EQUIVALENT" in comparison.to_markdown()
