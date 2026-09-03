from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from src.ingestion.ingestion import IngestionResult, Parameter
from src.core.pipeline_utils import RunMetadata, run_metadata_to_dict

DETERMINISTIC_FACT = "DETERMINISTIC_FACT"
LLM_INTERPRETATION = "LLM_INTERPRETATION"


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _coerce_int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _string_list(values: Any) -> List[str]:
    if not values:
        return []
    if isinstance(values, str):
        return [values] if values.strip() else []
    if isinstance(values, list):
        return [str(v).strip() for v in values if str(v).strip()]
    return []


def _dict_list(values: Any) -> List[Dict[str, Any]]:
    if not isinstance(values, list):
        return []
    return [dict(v) for v in values if isinstance(v, dict)]


def _merge_extra(source: Dict[str, Any], consumed_keys: Sequence[str]) -> Dict[str, Any]:
    consumed = set(consumed_keys)
    return {key: value for key, value in source.items() if key not in consumed}


def _calculation_tokens(value: Any) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(value or ""))
        if token.casefold() not in {"select", "from", "where", "set", "values", "into"}
    }


def _attach_calculation_destinations(
    calculations: List[Dict[str, Any]], operations: List["TableOperationIR"], source_text: str = ""
) -> List[Dict[str, Any]]:
    """Link existing calculation expressions through local variables to writes."""
    result = [dict(item) for item in calculations]
    for calculation in result:
        if any(str(calculation.get(key) or "").strip() for key in ("destination", "output", "output_field")):
            continue
        expression_tokens = _calculation_tokens(calculation.get("expression") or calculation.get("formula"))
        if not expression_tokens:
            continue
        local_targets = set()
        for match in re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_$#]*)\s*:=\s*(.*?);", str(source_text or ""), re.IGNORECASE | re.DOTALL
        ):
            rhs_tokens = _calculation_tokens(match.group(2))
            if expression_tokens <= rhs_tokens or (
                len(expression_tokens) >= 2 and len(expression_tokens & rhs_tokens) >= max(2, len(expression_tokens) // 2)
            ):
                local_targets.add(match.group(1).casefold())
        for operation in operations:
            table = str(operation.table or "").strip()
            for assignment in operation.assigned_values:
                if not isinstance(assignment, dict):
                    continue
                assigned_expression = assignment.get("expression") or assignment.get("value")
                assigned_tokens = _calculation_tokens(assigned_expression)
                if not (expression_tokens <= assigned_tokens or len(expression_tokens & assigned_tokens) >= 2 or local_targets & assigned_tokens):
                    continue
                column = str(assignment.get("column") or assignment.get("target_column") or "").strip()
                if not table or not column:
                    continue
                operation_name = str(operation.operation or "").upper()
                calculation["destination"] = f"{table}.{column}"
                calculation["used_by"] = f"INSERT INTO {table}" if operation_name == "INSERT" else f"{operation_name} {table}"
                break
            if calculation.get("destination"):
                break
    return result


def _order_business_rules_by_execution_order(
    business_rules: List["BusinessRuleIR"], statements: List["StatementIR"]
) -> List["BusinessRuleIR"]:
    """Order rules by where their evidence first appears in the source
    file, instead of leaving them in whatever order the synthesis LLM
    happened to return them.

    Purely deterministic - no LLM judgment involved. For each rule, take
    the smallest known source line number across:
      1. the rule's own `evidence_spans[*].line_start` (set during output
         guardrail grounding), then
      2. the source line of any statement whose chunk_id matches one of
         the rule's `source_chunks`.
    Rules for which no line number can be resolved (e.g. no evidence
    spans and no matching statement - genuinely rare, but possible for a
    rule synthesized from cross-chunk reasoning) keep their original
    relative order and sort after every rule with a known position, so
    nothing is ever dropped or arbitrarily reordered on missing data.
    """
    chunk_first_line: Dict[str, int] = {}
    for statement in statements:
        line = statement.source_line_start
        if line is None or line < 0:
            continue
        chunk_id = statement.source_chunk_id
        if not chunk_id:
            continue
        if chunk_id not in chunk_first_line or line < chunk_first_line[chunk_id]:
            chunk_first_line[chunk_id] = line

    _UNKNOWN = float("inf")

    def _rule_line(rule: "BusinessRuleIR") -> float:
        candidates: List[int] = []
        for span in rule.evidence_spans:
            if span.line_start is not None and span.line_start >= 0:
                candidates.append(span.line_start)
        for chunk_ref in rule.source_chunks:
            # source_chunks entries look like "<chunk_id>:<chunk_kind>" -
            # only the chunk_id portion (before the first colon) matches
            # StatementIR.source_chunk_id.
            chunk_id = str(chunk_ref).split(":", 1)[0]
            if chunk_id in chunk_first_line:
                candidates.append(chunk_first_line[chunk_id])
        return min(candidates) if candidates else _UNKNOWN

    indexed = list(enumerate(business_rules))
    indexed.sort(key=lambda pair: (_rule_line(pair[1]), pair[0]))
    return [rule for _, rule in indexed]


def _filter_none(mapping: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in mapping.items() if value not in (None, "", [], {}, ())}


@dataclass
class ParameterIR:
    name: str
    direction: str
    datatype: str
    origin: str = DETERMINISTIC_FACT
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_parameter(cls, parameter: Parameter) -> "ParameterIR":
        return cls(
            name=_clean_text(getattr(parameter, "name", "")),
            direction=_clean_text(getattr(parameter, "direction", "")),
            datatype=_clean_text(getattr(parameter, "datatype", "")),
            origin=DETERMINISTIC_FACT,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParameterIR":
        return cls(
            name=_clean_text(data.get("name")),
            direction=_clean_text(data.get("direction")),
            datatype=_clean_text(data.get("datatype")),
            origin=_clean_text(data.get("origin")) or DETERMINISTIC_FACT,
            extra=_merge_extra(data, {"name", "direction", "datatype", "origin", "extra"}),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "name": self.name,
            "direction": self.direction,
            "datatype": self.datatype,
            "origin": self.origin,
        }
        payload.update(self.extra)
        return _filter_none(payload)


@dataclass
class ObjectMetadataIR:
    object_id: str
    object_name: str
    object_type: str
    source_filename: str = ""
    dialect: str = ""
    dialect_confidence: str = ""
    source_hash: str = ""
    origin: str = DETERMINISTIC_FACT
    run_metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_ingestion(cls, ingestion: IngestionResult, run_metadata: Optional[RunMetadata] = None) -> "ObjectMetadataIR":
        return cls(
            object_id=_clean_text(getattr(ingestion, "object_id", "")),
            object_name=_clean_text(getattr(ingestion, "object_name", "")),
            object_type=_clean_text(getattr(ingestion, "object_type", "")),
            source_filename=_clean_text(getattr(ingestion, "source_filename", "")),
            dialect=_clean_text(getattr(ingestion, "dialect", "")),
            dialect_confidence=_clean_text(getattr(ingestion, "dialect_confidence", "")),
            source_hash=_clean_text(getattr(ingestion, "source_hash", "")),
            origin=DETERMINISTIC_FACT,
            run_metadata=run_metadata_to_dict(run_metadata or getattr(ingestion, "run_metadata", None)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return _filter_none(
            {
                "object_id": self.object_id,
                "object_name": self.object_name,
                "object_type": self.object_type,
                "source_filename": self.source_filename,
                "dialect": self.dialect,
                "dialect_confidence": self.dialect_confidence,
                "source_hash": self.source_hash,
                "origin": self.origin,
                "run_metadata": self.run_metadata,
            }
        )


@dataclass
class EvidenceSpanIR:
    source_file: str = ""
    char_start: int = -1
    char_end: int = -1
    line_start: int = -1
    line_end: int = -1
    chunk_id: str = ""
    statement_id: str = ""
    evidence_type: str = ""
    source_location_status: str = "unavailable"
    origin: str = DETERMINISTIC_FACT

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceSpanIR":
        return cls(
            source_file=_clean_text(data.get("source_file")),
            char_start=_coerce_int(data.get("char_start"), -1),
            char_end=_coerce_int(data.get("char_end"), -1),
            line_start=_coerce_int(data.get("line_start"), -1),
            line_end=_coerce_int(data.get("line_end"), -1),
            chunk_id=_clean_text(data.get("chunk_id")),
            statement_id=_clean_text(data.get("statement_id")),
            evidence_type=_clean_text(data.get("evidence_type")),
            source_location_status=_clean_text(data.get("source_location_status")) or "unavailable",
            origin=_clean_text(data.get("origin")) or DETERMINISTIC_FACT,
        )

    def to_dict(self) -> Dict[str, Any]:
        return _filter_none(
            {
                "source_file": self.source_file,
                "char_start": self.char_start,
                "char_end": self.char_end,
                "line_start": self.line_start,
                "line_end": self.line_end,
                "chunk_id": self.chunk_id,
                "statement_id": self.statement_id,
                "evidence_type": self.evidence_type,
                "source_location_status": self.source_location_status,
                "origin": self.origin,
            }
        )


@dataclass
class StatementIR:
    statement_id: str
    source_chunk_id: str
    source_chunk_kind: str
    statement_index: int = 0
    statement_kind: str = ""
    source_statement_text: str = ""
    parse_status: str = ""
    parse_error: str = ""
    source_file: str = ""
    source_char_start: int = -1
    source_char_end: int = -1
    source_line_start: int = -1
    source_line_end: int = -1
    source_location_status: str = "unavailable"
    evidence_type: str = ""
    origin: str = DETERMINISTIC_FACT
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatementIR":
        return cls(
            statement_id=_clean_text(data.get("statement_id")),
            source_chunk_id=_clean_text(data.get("source_chunk_id")),
            source_chunk_kind=_clean_text(data.get("source_chunk_kind")),
            statement_index=_coerce_int(data.get("statement_index"), 0),
            statement_kind=_clean_text(data.get("statement_kind")),
            source_statement_text=_clean_text(data.get("source_statement_text")),
            parse_status=_clean_text(data.get("parse_status")),
            parse_error=_clean_text(data.get("parse_error")),
            source_file=_clean_text(data.get("source_file")),
            source_char_start=_coerce_int(data.get("source_char_start"), -1),
            source_char_end=_coerce_int(data.get("source_char_end"), -1),
            source_line_start=_coerce_int(data.get("source_line_start"), -1),
            source_line_end=_coerce_int(data.get("source_line_end"), -1),
            source_location_status=_clean_text(data.get("source_location_status")) or "unavailable",
            evidence_type=_clean_text(data.get("evidence_type")),
            origin=_clean_text(data.get("origin")) or DETERMINISTIC_FACT,
            extra=_merge_extra(
                data,
                {
                    "statement_id",
                    "source_chunk_id",
                    "source_chunk_kind",
                    "statement_index",
                    "statement_kind",
                    "source_statement_text",
                    "parse_status",
                    "parse_error",
                    "source_file",
                    "source_char_start",
                    "source_char_end",
                    "source_line_start",
                    "source_line_end",
                    "source_location_status",
                    "evidence_type",
                    "origin",
                    "extra",
                },
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "statement_id": self.statement_id,
            "source_chunk_id": self.source_chunk_id,
            "source_chunk_kind": self.source_chunk_kind,
            "statement_index": self.statement_index,
            "statement_kind": self.statement_kind,
            "source_statement_text": self.source_statement_text,
            "parse_status": self.parse_status,
            "parse_error": self.parse_error,
            "source_file": self.source_file,
            "source_char_start": self.source_char_start,
            "source_char_end": self.source_char_end,
            "source_line_start": self.source_line_start,
            "source_line_end": self.source_line_end,
            "source_location_status": self.source_location_status,
            "evidence_type": self.evidence_type,
            "origin": self.origin,
        }
        payload.update(self.extra)
        return _filter_none(payload)


@dataclass
class TableOperationIR:
    table: str
    operation: str
    statement_id: str = ""
    source_chunk_id: str = ""
    source_chunk_kind: str = ""
    source_statement_text: str = ""
    target_columns: List[str] = field(default_factory=list)
    source_columns: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    where_predicate: str = ""
    having_predicate: str = ""
    join_predicates: List[Dict[str, Any]] = field(default_factory=list)
    exists_predicates: List[Dict[str, Any]] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)
    assigned_values: List[Dict[str, Any]] = field(default_factory=list)
    confidence: str = ""
    source_file: str = ""
    source_char_start: int = -1
    source_char_end: int = -1
    source_line_start: int = -1
    source_line_end: int = -1
    source_location_status: str = "unavailable"
    origin: str = DETERMINISTIC_FACT
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableOperationIR":
        return cls(
            table=_clean_text(data.get("table")),
            operation=_clean_text(data.get("operation")),
            statement_id=_clean_text(data.get("statement_id") or data.get("source_statement_id")),
            source_chunk_id=_clean_text(data.get("source_chunk_id")),
            source_chunk_kind=_clean_text(data.get("source_chunk_kind")),
            source_statement_text=_clean_text(data.get("source_statement_text")),
            target_columns=_string_list(data.get("target_columns")),
            source_columns=_string_list(data.get("source_columns")),
            columns=_string_list(data.get("columns")),
            where_predicate=_clean_text(data.get("where_predicate") or data.get("filter_condition")),
            having_predicate=_clean_text(data.get("having_predicate")),
            join_predicates=_dict_list(data.get("join_predicates")),
            exists_predicates=_dict_list(data.get("exists_predicates")),
            constants=_string_list(data.get("constants")),
            assigned_values=_dict_list(data.get("assigned_values")),
            confidence=_clean_text(data.get("confidence")),
            source_file=_clean_text(data.get("source_file")),
            source_char_start=_coerce_int(data.get("source_char_start"), -1),
            source_char_end=_coerce_int(data.get("source_char_end"), -1),
            source_line_start=_coerce_int(data.get("source_line_start"), -1),
            source_line_end=_coerce_int(data.get("source_line_end"), -1),
            source_location_status=_clean_text(data.get("source_location_status")) or "unavailable",
            origin=_clean_text(data.get("origin")) or DETERMINISTIC_FACT,
            extra=_merge_extra(
                data,
                {
                    "table",
                    "operation",
                    "statement_id",
                    "source_statement_id",
                    "source_chunk_id",
                    "source_chunk_kind",
                    "source_statement_text",
                    "target_columns",
                    "source_columns",
                    "columns",
                    "where_predicate",
                    "filter_condition",
                    "having_predicate",
                    "join_predicates",
                    "exists_predicates",
                    "constants",
                    "assigned_values",
                    "confidence",
                    "source_file",
                    "source_char_start",
                    "source_char_end",
                    "source_line_start",
                    "source_line_end",
                    "source_location_status",
                    "origin",
                    "extra",
                },
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "table": self.table,
            "operation": self.operation,
            "statement_id": self.statement_id,
            "source_statement_id": self.statement_id,
            "source_chunk_id": self.source_chunk_id,
            "source_chunk_kind": self.source_chunk_kind,
            "source_statement_text": self.source_statement_text,
            "target_columns": list(self.target_columns),
            "source_columns": list(self.source_columns),
            "columns": list(self.columns),
            "where_predicate": self.where_predicate,
            "filter_condition": self.where_predicate or None,
            "having_predicate": self.having_predicate or None,
            "join_predicates": list(self.join_predicates),
            "exists_predicates": list(self.exists_predicates),
            "constants": list(self.constants),
            "assigned_values": list(self.assigned_values),
            "confidence": self.confidence,
            "source_file": self.source_file,
            "source_char_start": self.source_char_start,
            "source_char_end": self.source_char_end,
            "source_line_start": self.source_line_start,
            "source_line_end": self.source_line_end,
            "source_location_status": self.source_location_status,
            "origin": self.origin,
        }
        payload.update(self.extra)
        return _filter_none(payload)


@dataclass
class BusinessRuleIR:
    rule_id: str
    rule_type: str = ""
    condition: str = ""
    action: str = ""
    output_field: str = ""
    business_meaning: str = ""
    fields_affected: List[str] = field(default_factory=list)
    confidence: str = ""
    evidence: List[str] = field(default_factory=list)
    evidence_spans: List[EvidenceSpanIR] = field(default_factory=list)
    source_chunks: List[str] = field(default_factory=list)
    source_statements: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    reconciliation_status: str = ""
    origin: str = LLM_INTERPRETATION
    validation_status: str = ""
    llm_claim: Dict[str, Any] = field(default_factory=dict)
    deterministic_evidence: Dict[str, Any] = field(default_factory=dict)
    comparison: Dict[str, Any] = field(default_factory=dict)
    reconciliation_notes: List[str] = field(default_factory=list)
    decision_logic: List[str] = field(default_factory=list)
    decision_logic_rows: List[Dict[str, Any]] = field(default_factory=list)
    tie_priority_handling: List[str] = field(default_factory=list)
    default: List[str] = field(default_factory=list)
    when_not_eligible: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BusinessRuleIR":
        evidence_spans = [EvidenceSpanIR.from_dict(item) for item in _dict_list(data.get("evidence_spans"))]
        return cls(
            rule_id=_clean_text(data.get("rule_id")),
            rule_type=_clean_text(data.get("rule_type")),
            condition=_clean_text(data.get("condition")),
            action=_clean_text(data.get("action")),
            output_field=_clean_text(data.get("output_field")),
            business_meaning=_clean_text(data.get("business_meaning")),
            fields_affected=_string_list(data.get("fields_affected")),
            confidence=_clean_text(data.get("confidence")),
            evidence=_string_list(data.get("source_evidence") or data.get("evidence")),
            evidence_spans=evidence_spans,
            source_chunks=_string_list(data.get("source_chunks")),
            source_statements=_string_list(data.get("source_statements")),
            dependencies=_string_list(data.get("dependencies")),
            ambiguities=_string_list(data.get("ambiguities") or data.get("unresolved_ambiguities")),
            reconciliation_status=_clean_text(data.get("reconciliation_status")),
            origin=_clean_text(data.get("origin")) or LLM_INTERPRETATION,
            validation_status=_clean_text(data.get("validation_status")),
            llm_claim=dict(data.get("llm_claim") or {}),
            deterministic_evidence=dict(data.get("deterministic_evidence") or {}),
            comparison=dict(data.get("comparison") or {}),
            reconciliation_notes=_string_list(data.get("reconciliation_notes")),
            decision_logic=_string_list(data.get("decision_logic")),
            decision_logic_rows=_dict_list(data.get("decision_logic_rows")),
            tie_priority_handling=_string_list(data.get("tie_priority_handling")),
            default=_string_list(data.get("default")),
            when_not_eligible=_string_list(data.get("when_not_eligible")),
            extra=_merge_extra(
                data,
                {
                    "rule_id",
                    "rule_type",
                    "condition",
                    "action",
                    "output_field",
                    "business_meaning",
                    "fields_affected",
                    "confidence",
                    "source_evidence",
                    "evidence",
                    "evidence_spans",
                    "source_chunks",
                    "source_statements",
                    "dependencies",
                    "ambiguities",
                    "unresolved_ambiguities",
                    "reconciliation_status",
                    "origin",
                    "validation_status",
                    "llm_claim",
                    "deterministic_evidence",
                    "comparison",
                    "reconciliation_notes",
                    "decision_logic",
                    "decision_logic_rows",
                    "tie_priority_handling",
                    "default",
                    "when_not_eligible",
                    "extra",
                },
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "condition": self.condition,
            "action": self.action,
            "output_field": self.output_field,
            "business_meaning": self.business_meaning,
            "fields_affected": list(self.fields_affected),
            "confidence": self.confidence,
            "source_evidence": list(self.evidence),
            "evidence_spans": [span.to_dict() for span in self.evidence_spans],
            "source_chunks": list(self.source_chunks),
            "source_statements": list(self.source_statements),
            "dependencies": list(self.dependencies),
            "ambiguities": list(self.ambiguities),
            "reconciliation_status": self.reconciliation_status,
            "origin": self.origin,
            "validation_status": self.validation_status,
            "llm_claim": dict(self.llm_claim),
            "deterministic_evidence": dict(self.deterministic_evidence),
            "comparison": dict(self.comparison),
            "reconciliation_notes": list(self.reconciliation_notes),
            "decision_logic": list(self.decision_logic),
            "decision_logic_rows": list(self.decision_logic_rows),
            "tie_priority_handling": list(self.tie_priority_handling),
            "default": list(self.default),
            "when_not_eligible": list(self.when_not_eligible),
        }
        payload.update(self.extra)
        return _filter_none(payload)


def _decision_chain_tokens(value: Any) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_$#]*|\d+(?:\.\d+)?", str(value or ""))
        if token.casefold() not in {"and", "or", "not", "between", "is", "null", "else"}
    }


def _build_decision_blocks(rules: List["BusinessRuleIR"], chains: Any) -> List[Dict[str, Any]]:
    """Attach rules to source-derived chains for presentation grouping only."""
    blocks: List[Dict[str, Any]] = []
    if not isinstance(chains, list):
        return blocks
    for chain_index, chain in enumerate(chains, start=1):
        branches = chain.get("branches") if isinstance(chain, dict) else None
        if not isinstance(branches, list):
            continue
        conditions = [str(item.get("branch_condition") or "") for item in branches if isinstance(item, dict)]
        if len(conditions) < 2:
            continue
        matched = []
        for rule in rules:
            candidates = [rule.condition, *rule.evidence]
            if any(
                _decision_chain_tokens(condition)
                and (_decision_chain_tokens(condition) <= _decision_chain_tokens(candidate)
                     or _decision_chain_tokens(candidate) <= _decision_chain_tokens(condition))
                for condition in conditions for candidate in candidates if str(candidate or "").strip()
            ):
                matched.append(rule)
        if not matched:
            continue
        block_id = f"decision_block_{chain_index:03d}"
        block_branches = []
        for rule in matched:
            rule.extra["decision_block_id"] = block_id
            results: List[Any] = []
            if rule.decision_logic_rows:
                for row in rule.decision_logic_rows:
                    if not isinstance(row, dict):
                        continue
                    results.extend(row.get("assignments") or [])
                    if row.get("outcome") not in (None, ""):
                        results.append(row.get("outcome"))
            elif rule.action or rule.business_meaning:
                results.append(rule.action or rule.business_meaning)
            block_branches.append({
                "rule_id": rule.rule_id,
                "condition": rule.condition,
                "results": results,
            })
        blocks.append({"block_id": block_id, "rule_ids": [rule.rule_id for rule in matched], "branches": block_branches})
    return blocks


@dataclass
class CanonicalBusinessIR:
    object_metadata: ObjectMetadataIR
    parameters: List[ParameterIR] = field(default_factory=list)
    statements: List[StatementIR] = field(default_factory=list)
    table_operations: List[TableOperationIR] = field(default_factory=list)
    business_rules: List[BusinessRuleIR] = field(default_factory=list)
    decision_blocks: List[Dict[str, Any]] = field(default_factory=list)
    calculations: List[Dict[str, Any]] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    reconciliation: Dict[str, Any] = field(default_factory=dict)
    coverage: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    run_metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_provenance: List[Dict[str, Any]] = field(default_factory=list)
    origin: str = DETERMINISTIC_FACT

    @classmethod
    def from_pipeline(
        cls,
        *,
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis: Any,
        reconciliation: Optional[Any] = None,
        run_metadata: Optional[RunMetadata] = None,
    ) -> "CanonicalBusinessIR":
        run_meta = run_metadata or getattr(ingestion, "run_metadata", None)
        reconciliation_payload = _to_dict(reconciliation or merged_extraction.get("reconciliation") or synthesis.data.get("reconciliation"))
        coverage = dict(merged_extraction.get("coverage") or synthesis.data.get("coverage") or reconciliation_payload.get("coverage") or {})
        quality = dict(merged_extraction.get("quality") or synthesis.data.get("quality") or reconciliation_payload.get("quality") or {})

        object_metadata = ObjectMetadataIR.from_ingestion(ingestion, run_meta)
        parameters = [ParameterIR.from_parameter(param) for param in getattr(ingestion, "parameters", []) or []]
        statements = [StatementIR.from_dict(item) for item in _dict_list(merged_extraction.get("statement_provenance"))]

        table_rows = []
        for key in ("table_operations", "tables_read", "tables_written"):
            table_rows.extend(_dict_list(merged_extraction.get(key)))
        deduped_table_rows = _dedupe_table_rows(table_rows)
        table_operations = [TableOperationIR.from_dict(item) for item in deduped_table_rows]

        business_rules = [BusinessRuleIR.from_dict(item) for item in _dict_list(synthesis.data.get("business_rules"))]
        business_rules = _order_business_rules_by_execution_order(business_rules, statements)
        decision_blocks = _build_decision_blocks(business_rules, merged_extraction.get("decision_chains"))
        calculations = _attach_calculation_destinations(
            [dict(item) for item in _dict_list(synthesis.data.get("calculations"))],
            table_operations,
            source_text=getattr(ingestion, "raw_code", ""),
        )
        exceptions = _string_list(synthesis.data.get("exception_handling_summary"))
        ambiguities = _string_list(merged_extraction.get("ambiguities")) + _string_list(synthesis.data.get("ambiguities"))
        contradictions = _dict_list(reconciliation_payload.get("contradictions"))
        chunk_provenance = _dict_list(merged_extraction.get("chunk_provenance"))

        return cls(
            object_metadata=object_metadata,
            parameters=parameters,
            statements=statements,
            table_operations=table_operations,
            business_rules=business_rules,
            decision_blocks=decision_blocks,
            calculations=calculations,
            exceptions=exceptions,
            ambiguities=list(dict.fromkeys(ambiguities)),
            contradictions=contradictions,
            reconciliation=reconciliation_payload,
            coverage=coverage,
            quality=quality,
            run_metadata=run_metadata_to_dict(run_meta),
            chunk_provenance=chunk_provenance,
            origin=DETERMINISTIC_FACT,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_metadata": self.object_metadata.to_dict(),
            "parameters": [item.to_dict() for item in self.parameters],
            "statements": [item.to_dict() for item in self.statements],
            "table_operations": [item.to_dict() for item in self.table_operations],
            "business_rules": [item.to_dict() for item in self.business_rules],
            "calculations": [dict(item) for item in self.calculations],
            "exceptions": list(self.exceptions),
            "ambiguities": list(self.ambiguities),
            "contradictions": [dict(item) for item in self.contradictions],
            "reconciliation": _to_dict(self.reconciliation),
            "coverage": dict(self.coverage),
            "quality": dict(self.quality),
            "run_metadata": dict(self.run_metadata),
            "chunk_provenance": [dict(item) for item in self.chunk_provenance],
            "origin": self.origin,
        }

    def to_legacy_merged_extraction(self, merged_extraction: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = dict(merged_extraction or {})
        reads = [row.to_dict() for row in self.table_operations if _clean_text(row.operation).upper() == "READ"]
        writes = [row.to_dict() for row in self.table_operations if _clean_text(row.operation).upper() != "READ"]
        payload.update(
            {
                "tables_read": reads,
                "tables_written": writes,
                "table_operations": [row.to_dict() for row in self.table_operations],
                "statement_provenance": [item.to_dict() for item in self.statements],
                "chunk_provenance": [dict(item) for item in self.chunk_provenance],
                "ambiguities": list(self.ambiguities),
                "run_metadata": self.run_metadata,
                "reconciliation": _to_dict(self.reconciliation),
                "coverage": dict(self.coverage),
                "quality": dict(self.quality),
                "canonical_ir": self.to_dict(),
            }
        )
        return payload

    def to_legacy_synthesis_data(self, synthesis_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = dict(synthesis_data or {})
        payload.update(
            {
            "business_rules": [rule.to_dict() for rule in self.business_rules],
            "decision_blocks": [dict(item) for item in self.decision_blocks],
            "calculations": [dict(item) for item in self.calculations],
                "exception_handling_summary": "; ".join(self.exceptions),
                "ambiguities": list(self.ambiguities),
                "reconciliation": _to_dict(self.reconciliation),
                "coverage": dict(self.coverage),
                "quality": dict(self.quality),
                "run_metadata": self.run_metadata,
                "canonical_ir": self.to_dict(),
            }
        )
        return payload


def _to_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "to_dict"):
        try:
            data = value.to_dict()
            return dict(data) if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _dedupe_table_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for row in rows:
        signature = (
            _clean_text(row.get("table")),
            _clean_text(row.get("operation")),
            tuple(_string_list(row.get("target_columns") or row.get("columns"))),
            _clean_text(row.get("where_predicate") or row.get("filter_condition")),
            _clean_text(row.get("having_predicate")),
            _clean_text(row.get("statement_id") or row.get("source_statement_id")),
        )
        if signature in seen:
            continue
        seen.add(signature)
        result.append(dict(row))
    return result
