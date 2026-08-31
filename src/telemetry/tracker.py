from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Optional

from .aggregator import aggregate_run_telemetry
from .models import LLMCallMetric, RunTelemetry, TokenUsage


class LLMTelemetryTracker:
    """Thread-safe per-run accumulator for LLM call telemetry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._call_metrics: list[LLMCallMetric] = []
        self._cache_events: list[tuple[str, str]] = []

    def record_call(
        self,
        *,
        stage: str,
        provider: str,
        model_name: str,
        response: Any = None,
        latency_seconds: Optional[float] = None,
        success: bool = True,
        error: BaseException | None = None,
    ) -> None:
        try:
            usage = TokenUsage.from_any(getattr(response, "usage", None) if response is not None else None)
        except Exception:
            usage = TokenUsage()
        try:
            metric = LLMCallMetric(
                stage=stage,
                provider=provider,
                model_name=model_name,
                token_usage=usage,
                latency_seconds=latency_seconds,
                success=success,
                error_type=type(error).__name__ if error else "",
                error_message=str(error) if error else "",
            )
            with self._lock:
                self._call_metrics.append(metric)
        except Exception:
            return

    def record_cache_lookup(self, *, stage: str, hit: bool) -> None:
        try:
            event = (str(stage or "").strip() or "unknown", "hit" if hit else "miss")
            with self._lock:
                self._cache_events.append(event)
        except Exception:
            return

    def snapshot(self, run_id: str) -> RunTelemetry:
        with self._lock:
            metrics = list(self._call_metrics)
            cache_events = list(self._cache_events)
        telemetry = aggregate_run_telemetry(run_id, metrics)
        if cache_events:
            hit_counts = defaultdict(int)
            miss_counts = defaultdict(int)
            for stage, status in cache_events:
                if status == "hit":
                    telemetry.cache_hit_count += 1
                    hit_counts[stage] += 1
                else:
                    telemetry.cache_miss_count += 1
                    miss_counts[stage] += 1
            telemetry.cache_hit_stage_breakdown = dict(hit_counts)
            telemetry.cache_miss_stage_breakdown = dict(miss_counts)
        return telemetry

    def to_dict(self, run_id: str) -> dict[str, Any]:
        return self.snapshot(run_id).to_dict()
