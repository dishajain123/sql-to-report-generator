from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Sequence

from .models import LLMCallMetric, RunTelemetry, TokenUsage


def _sum_ints(values: Sequence[int | None]) -> tuple[int | None, str]:
    present = [value for value in values if value is not None]
    if not present:
        return None, "unavailable"
    total = sum(present)
    availability = "available" if len(present) == len(values) else "partial"
    return total, availability


def aggregate_token_usage(usages: Iterable[TokenUsage]) -> TokenUsage:
    usage_list = [usage for usage in usages if isinstance(usage, TokenUsage)]
    if not usage_list:
        return TokenUsage()

    prompt_tokens, prompt_state = _sum_ints([usage.prompt_tokens for usage in usage_list])
    completion_tokens, completion_state = _sum_ints([usage.completion_tokens for usage in usage_list])

    totals_available = [usage.total_tokens for usage in usage_list]
    total_tokens, total_state = _sum_ints(totals_available)
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens
        total_state = "available" if prompt_state == "available" and completion_state == "available" else "partial"

    states = {prompt_state, completion_state, total_state}
    if states == {"unavailable"}:
        availability = "unavailable"
    elif states == {"available"}:
        availability = "available"
    else:
        availability = "partial"

    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        availability=availability,
    )


def _stage_summary(metrics: Sequence[LLMCallMetric]) -> Dict[str, Any]:
    token_usage = aggregate_token_usage(metric.token_usage for metric in metrics)
    return {
        "call_count": len(metrics),
        "success_count": sum(1 for metric in metrics if metric.success),
        "failure_count": sum(1 for metric in metrics if not metric.success),
        "latency_seconds": round(
            sum(float(metric.latency_seconds or 0.0) for metric in metrics if metric.latency_seconds is not None), 6
        ),
        "token_usage": token_usage.to_dict(),
        "usage_available_call_count": sum(1 for metric in metrics if metric.token_usage.is_available),
        "usage_partial_call_count": sum(1 for metric in metrics if metric.token_usage.is_partial),
        "usage_unavailable_call_count": sum(1 for metric in metrics if metric.token_usage.is_unavailable),
    }


def aggregate_run_telemetry(run_id: str, call_metrics: Sequence[LLMCallMetric]) -> RunTelemetry:
    ordered_metrics = [metric for metric in call_metrics if isinstance(metric, LLMCallMetric)]
    totals = aggregate_token_usage(metric.token_usage for metric in ordered_metrics)
    grouped: Dict[str, List[LLMCallMetric]] = defaultdict(list)
    for metric in ordered_metrics:
        grouped[str(metric.stage or "").strip() or "unknown"].append(metric)
    stage_breakdown = {stage: _stage_summary(metrics) for stage, metrics in grouped.items()}
    return RunTelemetry(
        run_id=str(run_id or "").strip(),
        call_metrics=list(ordered_metrics),
        totals=totals,
        stage_breakdown=stage_breakdown,
    )
