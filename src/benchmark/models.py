from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split()).lower()


def _normalize_identifier(value: Any) -> str:
    text = str(value or "").strip().upper()
    for ch in ("[", "]", '"', "`"):
        text = text.replace(ch, "")
    return " ".join(text.split())


def _normalize_optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sorted_normalized_strings(values: Sequence[Any]) -> List[str]:
    return sorted({val for val in (_normalize_text(item) for item in values) if val})


def _hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def _stringify(value: Any) -> str:
    return "" if value in (None, "") else str(value)


def _percentage_change(baseline: Optional[float], optimized: Optional[float]) -> Optional[float]:
    if baseline in (None, 0):
        return None
    if optimized is None:
        return None
    return round(((baseline - optimized) / baseline) * 100.0, 4)


@dataclass(frozen=True)
class BenchmarkRunConfig:
    label: str
    sql_file_path: str
    dialect: str = "auto"
    pipeline_kwargs: Dict[str, Any] = field(default_factory=dict)
    cache_enabled: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": _stringify(self.label),
            "sql_file_path": _stringify(self.sql_file_path),
            "dialect": _stringify(self.dialect),
            "pipeline_kwargs": dict(self.pipeline_kwargs),
            "cache_enabled": self.cache_enabled,
        }


@dataclass(frozen=True)
class BenchmarkTelemetry:
    input_file: str = ""
    provider: str = ""
    model_name: str = ""
    dialect: str = ""
    extraction_call_count: Optional[int] = None
    extraction_prompt_tokens: Optional[int] = None
    extraction_completion_tokens: Optional[int] = None
    synthesis_call_count: Optional[int] = None
    synthesis_prompt_tokens: Optional[int] = None
    synthesis_completion_tokens: Optional[int] = None
    total_prompt_tokens: Optional[int] = None
    total_completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_seconds: Optional[float] = None
    extraction_latency_seconds: Optional[float] = None
    synthesis_latency_seconds: Optional[float] = None
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None
    success_count: Optional[int] = None
    failure_count: Optional[int] = None
    rag_context_chars: Optional[int] = None
    rag_context_blocks: Optional[int] = None
    rag_context_words: Optional[int] = None

    @property
    def cache_hit_rate(self) -> Optional[float]:
        if self.cache_hits is None and self.cache_misses is None:
            return None
        hits = int(self.cache_hits or 0)
        misses = int(self.cache_misses or 0)
        total = hits + misses
        if total <= 0:
            return None
        return round(hits / total, 6)

    @property
    def total_call_count(self) -> Optional[int]:
        if self.extraction_call_count is None and self.synthesis_call_count is None:
            return None
        return int(self.extraction_call_count or 0) + int(self.synthesis_call_count or 0)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "input_file": _stringify(self.input_file),
            "provider": _stringify(self.provider),
            "model_name": _stringify(self.model_name),
            "dialect": _stringify(self.dialect),
            "extraction_call_count": self.extraction_call_count,
            "extraction_prompt_tokens": self.extraction_prompt_tokens,
            "extraction_completion_tokens": self.extraction_completion_tokens,
            "synthesis_call_count": self.synthesis_call_count,
            "synthesis_prompt_tokens": self.synthesis_prompt_tokens,
            "synthesis_completion_tokens": self.synthesis_completion_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_seconds": self.latency_seconds,
            "extraction_latency_seconds": self.extraction_latency_seconds,
            "synthesis_latency_seconds": self.synthesis_latency_seconds,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "rag_context_chars": self.rag_context_chars,
            "rag_context_blocks": self.rag_context_blocks,
            "rag_context_words": self.rag_context_words,
        }
        return {key: value for key, value in payload.items() if value not in (None, "", [], {}, ())}

    @classmethod
    def from_telemetry_dict(
        cls,
        *,
        input_file: str = "",
        provider: str = "",
        model_name: str = "",
        dialect: str = "",
        telemetry: Optional[Mapping[str, Any]] = None,
        extraction_latency_seconds: Optional[float] = None,
        synthesis_latency_seconds: Optional[float] = None,
        rag_context_chars: Optional[int] = None,
        rag_context_blocks: Optional[int] = None,
        rag_context_words: Optional[int] = None,
    ) -> "BenchmarkTelemetry":
        telemetry = dict(telemetry or {})
        totals = dict(telemetry.get("totals") or {})
        stage_breakdown = dict(telemetry.get("stage_breakdown") or {})
        extraction = dict(stage_breakdown.get("extraction") or {})
        synthesis = dict(stage_breakdown.get("synthesis") or {})
        extraction_latency = _normalize_optional_float(extraction.get("latency_seconds"))
        synthesis_latency = _normalize_optional_float(synthesis.get("latency_seconds"))
        latency_seconds: Optional[float]
        if extraction_latency is None and synthesis_latency is None:
            latency_seconds = None
        else:
            latency_seconds = float((extraction_latency or 0.0) + (synthesis_latency or 0.0))
        return cls(
            input_file=input_file,
            provider=provider,
            model_name=model_name,
            dialect=dialect,
            extraction_call_count=_normalize_optional_int(extraction.get("call_count")),
            extraction_prompt_tokens=_normalize_optional_int(
                (extraction.get("token_usage") or {}).get("prompt_tokens")
            ),
            extraction_completion_tokens=_normalize_optional_int(
                (extraction.get("token_usage") or {}).get("completion_tokens")
            ),
            synthesis_call_count=_normalize_optional_int(synthesis.get("call_count")),
            synthesis_prompt_tokens=_normalize_optional_int(
                (synthesis.get("token_usage") or {}).get("prompt_tokens")
            ),
            synthesis_completion_tokens=_normalize_optional_int(
                (synthesis.get("token_usage") or {}).get("completion_tokens")
            ),
            total_prompt_tokens=_normalize_optional_int(totals.get("prompt_tokens")),
            total_completion_tokens=_normalize_optional_int(totals.get("completion_tokens")),
            total_tokens=_normalize_optional_int(totals.get("total_tokens")),
            latency_seconds=latency_seconds,
            extraction_latency_seconds=extraction_latency,
            synthesis_latency_seconds=synthesis_latency,
            cache_hits=_normalize_optional_int(telemetry.get("cache_hit_count")),
            cache_misses=_normalize_optional_int(telemetry.get("cache_miss_count")),
            success_count=_normalize_optional_int(telemetry.get("success_count")),
            failure_count=_normalize_optional_int(telemetry.get("failure_count")),
            rag_context_chars=rag_context_chars,
            rag_context_blocks=rag_context_blocks,
            rag_context_words=rag_context_words,
        )


@dataclass(frozen=True)
class BusinessOutputSnapshot:
    rule_count: int = 0
    rule_signatures: List[Dict[str, Any]] = field(default_factory=list)
    rule_names: List[str] = field(default_factory=list)
    conditions_count: int = 0
    decision_chain_count: int = 0
    decision_branch_count: int = 0
    calculations_count: int = 0
    loops_count: int = 0
    exceptions_count: int = 0
    ambiguities_count: int = 0
    business_meanings: List[str] = field(default_factory=list)
    purpose_summary: str = ""
    step_by_step_flow: List[str] = field(default_factory=list)
    tables_read: List[str] = field(default_factory=list)
    tables_written: List[str] = field(default_factory=list)
    operations: List[Tuple[str, str]] = field(default_factory=list)
    narrative_signature: str = ""
    semantic_signature: str = ""

    @staticmethod
    def _normalize_row(row: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "condition": _normalize_text(row.get("condition")),
            "outcome": _normalize_text(row.get("outcome")),
            "output_field": _normalize_text(row.get("output_field")),
        }

    @staticmethod
    def _rule_signature(rule: Mapping[str, Any]) -> Dict[str, Any]:
        decision_rows: List[Dict[str, Any]] = []
        for row in rule.get("decision_logic_rows") or []:
            if isinstance(row, Mapping):
                decision_rows.append(BusinessOutputSnapshot._normalize_row(row))
        fields_affected = _sorted_normalized_strings(rule.get("fields_affected") or [])
        return {
            "rule_name": _normalize_text(rule.get("rule_name")),
            "rule_type": _normalize_text(rule.get("rule_type")),
            "condition": _normalize_text(rule.get("condition")),
            "action": _normalize_text(rule.get("action")),
            "output_field": _normalize_text(rule.get("output_field")),
            "fields_affected": fields_affected,
            "decision_logic_rows": decision_rows,
            "reconciliation_status": _normalize_text(rule.get("reconciliation_status")),
        }

    @classmethod
    def from_pipeline_state(
        cls,
        *,
        merged_extraction: Mapping[str, Any] | None = None,
        synthesis_data: Mapping[str, Any] | None = None,
    ) -> "BusinessOutputSnapshot":
        merged_extraction = dict(merged_extraction or {})
        synthesis_data = dict(synthesis_data or {})
        rules = [rule for rule in (synthesis_data.get("business_rules") or []) if isinstance(rule, Mapping)]
        rule_signatures = [cls._rule_signature(rule) for rule in rules]
        normalized_rule_signatures = sorted(rule_signatures, key=lambda item: json.dumps(item, sort_keys=True))
        rule_names = sorted(
            {name for name in (_normalize_text(rule.get("rule_name")) for rule in rules) if name}
        )
        purpose_summary = _normalize_text(synthesis_data.get("purpose_summary"))
        step_by_step_flow = _sorted_normalized_strings(synthesis_data.get("step_by_step_flow") or [])
        business_meanings = _sorted_normalized_strings(
            [rule.get("business_meaning") for rule in rules if rule.get("business_meaning")]
        )
        conditions = merged_extraction.get("conditions") or []
        decision_chains = merged_extraction.get("decision_chains") or []
        calculations = merged_extraction.get("calculations") or []
        loops = merged_extraction.get("loops") or []
        exception_handling = merged_extraction.get("exception_handling") or []
        ambiguities = merged_extraction.get("ambiguities") or []
        tables_read = sorted(
            {table for table in (_normalize_identifier(row.get("table")) for row in merged_extraction.get("tables_read") or []) if table}
        )
        tables_written = sorted(
            {table for table in (_normalize_identifier(row.get("table")) for row in merged_extraction.get("tables_written") or []) if table}
        )
        operations = sorted(
            {
                (_normalize_text(op.get("operation")), _normalize_identifier(op.get("table")))
                for op in merged_extraction.get("table_operations") or []
                if isinstance(op, Mapping)
            }
        )
        decision_branch_count = 0
        for chain in decision_chains:
            if isinstance(chain, Mapping):
                branches = chain.get("branches") or []
                decision_branch_count += sum(1 for branch in branches if isinstance(branch, Mapping))
        semantic_payload = {
            "rule_count": len(rule_signatures),
            "rule_signatures": normalized_rule_signatures,
            "conditions_count": len([item for item in conditions if isinstance(item, Mapping)]),
            "decision_chain_count": len([item for item in decision_chains if isinstance(item, Mapping)]),
            "decision_branch_count": decision_branch_count,
            "calculations_count": len([item for item in calculations if isinstance(item, Mapping)]),
            "loops_count": len([item for item in loops if isinstance(item, Mapping)]),
            "exceptions_count": len([item for item in exception_handling if isinstance(item, Mapping)]),
            "ambiguities_count": len([item for item in ambiguities if isinstance(item, Mapping) or isinstance(item, str)]),
            "tables_read": tables_read,
            "tables_written": tables_written,
            "operations": operations,
        }
        narrative_payload = {
            "purpose_summary": purpose_summary,
            "step_by_step_flow": step_by_step_flow,
            "business_meanings": business_meanings,
            "rule_names": rule_names,
        }
        return cls(
            rule_count=len(rule_signatures),
            rule_signatures=normalized_rule_signatures,
            rule_names=rule_names,
            conditions_count=len([item for item in conditions if isinstance(item, Mapping)]),
            decision_chain_count=len([item for item in decision_chains if isinstance(item, Mapping)]),
            decision_branch_count=decision_branch_count,
            calculations_count=len([item for item in calculations if isinstance(item, Mapping)]),
            loops_count=len([item for item in loops if isinstance(item, Mapping)]),
            exceptions_count=len([item for item in exception_handling if isinstance(item, Mapping)]),
            ambiguities_count=len([item for item in ambiguities if isinstance(item, Mapping) or isinstance(item, str)]),
            business_meanings=business_meanings,
            purpose_summary=purpose_summary,
            step_by_step_flow=step_by_step_flow,
            tables_read=tables_read,
            tables_written=tables_written,
            operations=operations,
            narrative_signature=json.dumps(narrative_payload, sort_keys=True, separators=(",", ":")),
            semantic_signature=json.dumps(semantic_payload, sort_keys=True, separators=(",", ":")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkRunRecord:
    label: str
    input_file: str
    model_name: str
    provider: str
    dialect: str
    telemetry: BenchmarkTelemetry
    business: BusinessOutputSnapshot
    success: bool = True
    error: str = ""
    report_hash: str = ""
    verification_hash: str = ""
    rag_context_chars: Optional[int] = None
    rag_context_blocks: Optional[int] = None
    rag_context_words: Optional[int] = None
    report_text: str = field(default="", repr=False, compare=False)
    verification_text: str = field(default="", repr=False, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "label": _stringify(self.label),
            "input_file": _stringify(self.input_file),
            "model_name": _stringify(self.model_name),
            "provider": _stringify(self.provider),
            "dialect": _stringify(self.dialect),
            "telemetry": self.telemetry.to_dict(),
            "business": self.business.to_dict(),
            "success": bool(self.success),
            "error": _stringify(self.error),
            "report_hash": _stringify(self.report_hash),
            "verification_hash": _stringify(self.verification_hash),
            "rag_context_chars": self.rag_context_chars,
            "rag_context_blocks": self.rag_context_blocks,
            "rag_context_words": self.rag_context_words,
        }
        return {key: value for key, value in payload.items() if value not in (None, "", [], {}, ())}


@dataclass(frozen=True)
class BenchmarkComparisonResult:
    baseline: BenchmarkRunRecord
    optimized: BenchmarkRunRecord
    business_equivalent: bool
    markdown_text_changed: bool
    wording_only_difference: bool
    semantic_regression: bool
    semantic_differences: List[str] = field(default_factory=list)
    token_reduction_percent: Optional[float] = None
    prompt_token_reduction_percent: Optional[float] = None
    completion_token_reduction_percent: Optional[float] = None
    call_reduction_percent: Optional[float] = None
    latency_change_percent: Optional[float] = None
    cache_hit_rate_baseline: Optional[float] = None
    cache_hit_rate_optimized: Optional[float] = None
    total_token_reduction: Optional[int] = None
    prompt_token_reduction: Optional[int] = None
    completion_token_reduction: Optional[int] = None
    call_reduction: Optional[int] = None
    latency_change_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "baseline": self.baseline.to_dict(),
            "optimized": self.optimized.to_dict(),
            "business_equivalent": self.business_equivalent,
            "markdown_text_changed": self.markdown_text_changed,
            "wording_only_difference": self.wording_only_difference,
            "semantic_regression": self.semantic_regression,
            "semantic_differences": list(self.semantic_differences),
            "token_reduction_percent": self.token_reduction_percent,
            "prompt_token_reduction_percent": self.prompt_token_reduction_percent,
            "completion_token_reduction_percent": self.completion_token_reduction_percent,
            "call_reduction_percent": self.call_reduction_percent,
            "latency_change_percent": self.latency_change_percent,
            "cache_hit_rate_baseline": self.cache_hit_rate_baseline,
            "cache_hit_rate_optimized": self.cache_hit_rate_optimized,
            "total_token_reduction": self.total_token_reduction,
            "prompt_token_reduction": self.prompt_token_reduction,
            "completion_token_reduction": self.completion_token_reduction,
            "call_reduction": self.call_reduction,
            "latency_change_seconds": self.latency_change_seconds,
        }
        return {key: value for key, value in payload.items() if value not in (None, "", [], {}, ())}

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def to_markdown(self) -> str:
        baseline = self.baseline.telemetry
        optimized = self.optimized.telemetry
        rows = [
            ("Prompt tokens", baseline.total_prompt_tokens, optimized.total_prompt_tokens, self.prompt_token_reduction_percent),
            (
                "Completion tokens",
                baseline.total_completion_tokens,
                optimized.total_completion_tokens,
                self.completion_token_reduction_percent,
            ),
            ("Total tokens", baseline.total_tokens, optimized.total_tokens, self.token_reduction_percent),
            (
                "LLM calls",
                baseline.total_call_count,
                optimized.total_call_count,
                self.call_reduction_percent,
            ),
            ("Latency (s)", baseline.latency_seconds, optimized.latency_seconds, self.latency_change_percent),
            ("Cache hit rate", baseline.cache_hit_rate, optimized.cache_hit_rate, None),
        ]

        def _fmt(value: Any) -> str:
            if value is None:
                return "n/a"
            if isinstance(value, float):
                return f"{value:.4f}".rstrip("0").rstrip(".")
            return str(value)

        lines = [
            "LLM Efficiency Benchmark",
            "========================",
            "",
            f"Input: {self.baseline.input_file}",
            f"Model: {self.baseline.model_name} | Provider: {self.baseline.provider} | Dialect: {self.baseline.dialect}",
            "",
            f"{'Metric':<18} {'Baseline':>12} {'Optimized':>12} {'Change':>12}",
            f"{'-' * 18} {'-' * 12} {'-' * 12} {'-' * 12}",
        ]
        for label, baseline_value, optimized_value, pct in rows:
            change = "n/a" if pct is None else f"{pct:+.2f}%"
            lines.append(
                f"{label:<18} {_fmt(baseline_value):>12} {_fmt(optimized_value):>12} {change:>12}"
            )
        lines.extend(
            [
                "",
                f"Business output: {'EQUIVALENT' if self.business_equivalent else 'DIFFERENT'}",
                f"Quality regression: {'NO' if self.business_equivalent else 'YES'}",
                f"Markdown text changed: {'YES' if self.markdown_text_changed else 'NO'}",
            ]
        )
        return "\n".join(lines)


def safe_percentage_change(baseline: Optional[float], optimized: Optional[float]) -> Optional[float]:
    return _percentage_change(baseline, optimized)
