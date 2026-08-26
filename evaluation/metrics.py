from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    return " ".join(text.split())


def normalize_identifier(value: Any) -> str:
    text = str(value or "").strip().upper()
    for ch in ("[", "]", '"', "`"):
        text = text.replace(ch, "")
    return re_sub_whitespace(text)


def re_sub_whitespace(text: str) -> str:
    return " ".join(str(text or "").split())


def normalize_table_name(value: Any) -> str:
    text = normalize_identifier(value)
    return text


def normalize_parameter(parameter: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        normalize_identifier(parameter.get("name")),
        normalize_text(parameter.get("direction")),
        normalize_text(parameter.get("datatype")),
    )


def normalize_rule(rule: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        normalize_text(rule.get("condition")),
        normalize_text(rule.get("action")),
        normalize_text(rule.get("output_field") or rule.get("fields_affected") or ""),
    )


def compare_sets(expected: Iterable[Any], actual: Iterable[Any]) -> Dict[str, Any]:
    exp = {normalize_text(item) for item in expected if normalize_text(item)}
    act = {normalize_text(item) for item in actual if normalize_text(item)}
    matches = exp & act
    missing = exp - act
    unexpected = act - exp
    precision = len(matches) / len(act) if act else None
    recall = len(matches) / len(exp) if exp else None
    return {
        "expected": sorted(exp),
        "actual": sorted(act),
        "matches": sorted(matches),
        "missing": sorted(missing),
        "unexpected": sorted(unexpected),
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
    }


def compare_normalized_tuples(
    expected: Iterable[Tuple[str, ...]],
    actual: Iterable[Tuple[str, ...]],
) -> Dict[str, Any]:
    exp = set(expected)
    act = set(actual)
    matches = exp & act
    missing = exp - act
    unexpected = act - exp
    precision = len(matches) / len(act) if act else None
    recall = len(matches) / len(exp) if exp else None
    return {
        "expected": sorted(exp),
        "actual": sorted(act),
        "matches": sorted(matches),
        "missing": sorted(missing),
        "unexpected": sorted(unexpected),
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
    }


def compare_scalar(expected: Any, actual: Any, normalize=normalize_text) -> Dict[str, Any]:
    exp = normalize(expected)
    act = normalize(actual)
    return {
        "expected": exp,
        "actual": act,
        "match": bool(exp) and exp == act,
    }


def _f1(precision: Optional[float], recall: Optional[float]) -> Optional[float]:
    if precision is None or recall is None or (precision + recall) == 0:
        return None
    return 2 * precision * recall / (precision + recall)


@dataclass
class CaseResult:
    case_id: str
    status: str
    mode: str
    checks: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    actual_available: bool = True


@dataclass
class DatasetSummary:
    overall_status: str
    case_count: int
    pass_count: int
    fail_count: int
    changed_count: int
    skipped_count: int
    metrics: Dict[str, Any] = field(default_factory=dict)

