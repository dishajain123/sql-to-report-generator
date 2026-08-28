from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


_AVAILABILITY_VALUES = {"available", "partial", "unavailable"}


def _coerce_optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mapping_from_usage(usage: Any) -> Dict[str, Any]:
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return dict(usage)
    for attr in ("model_dump", "dict", "to_dict"):
        method = getattr(usage, attr, None)
        if callable(method):
            try:
                mapped = method()
            except Exception:
                mapped = None
            if isinstance(mapped, dict):
                return dict(mapped)
    payload: Dict[str, Any] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if hasattr(usage, key):
            payload[key] = getattr(usage, key)
    if payload:
        return payload
    try:
        return dict(usage)
    except Exception:
        return {}


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    availability: str = "unavailable"

    def __post_init__(self) -> None:
        availability = str(self.availability or "unavailable").strip().lower()
        if availability not in _AVAILABILITY_VALUES:
            availability = "unavailable"
        object.__setattr__(self, "availability", availability)

    @classmethod
    def from_any(cls, usage: Any) -> "TokenUsage":
        mapping = _mapping_from_usage(usage)
        prompt_tokens = _coerce_optional_int(mapping.get("prompt_tokens"))
        completion_tokens = _coerce_optional_int(mapping.get("completion_tokens"))
        total_tokens = _coerce_optional_int(mapping.get("total_tokens"))

        available_fields = [
            field_name
            for field_name, value in (
                ("prompt_tokens", prompt_tokens),
                ("completion_tokens", completion_tokens),
                ("total_tokens", total_tokens),
            )
            if value is not None
        ]
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens
            available_fields.append("total_tokens")
        if not available_fields:
            availability = "unavailable"
        elif len(available_fields) == 3:
            availability = "available"
        else:
            availability = "partial"
        return cls(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            availability=availability,
        )

    @property
    def is_available(self) -> bool:
        return self.availability == "available"

    @property
    def is_partial(self) -> bool:
        return self.availability == "partial"

    @property
    def is_unavailable(self) -> bool:
        return self.availability == "unavailable"

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "availability": self.availability,
        }
        return {key: value for key, value in payload.items() if value not in (None, "", [], {}, ())}


@dataclass(frozen=True)
class LLMCallMetric:
    stage: str
    provider: str
    model_name: str
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    latency_seconds: Optional[float] = None
    success: bool = True
    error_type: str = ""
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "stage": str(self.stage or "").strip(),
            "provider": str(self.provider or "").strip(),
            "model_name": str(self.model_name or "").strip(),
            "token_usage": self.token_usage.to_dict(),
            "latency_seconds": self.latency_seconds,
            "success": bool(self.success),
            "error_type": str(self.error_type or "").strip(),
            "error_message": str(self.error_message or "").strip(),
        }
        return {key: value for key, value in payload.items() if value not in (None, "", [], {}, ())}


@dataclass
class RunTelemetry:
    run_id: str
    call_metrics: List[LLMCallMetric] = field(default_factory=list)
    totals: TokenUsage = field(default_factory=TokenUsage)
    stage_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": str(self.run_id or "").strip(),
            "call_count": len(self.call_metrics),
            "success_count": sum(1 for metric in self.call_metrics if metric.success),
            "failure_count": sum(1 for metric in self.call_metrics if not metric.success),
            "totals": self.totals.to_dict(),
            "stage_breakdown": {key: dict(value) for key, value in self.stage_breakdown.items()},
            "call_metrics": [metric.to_dict() for metric in self.call_metrics],
        }

