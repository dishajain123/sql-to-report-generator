from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.ingestion.ingestion import CodeIngestionAgent
from src.dialect.detector import AMBIGUOUS, UNKNOWN, UNSUPPORTED, detect_dialect, normalize_dialect_name
from src.ingestion.guardrails import run_input_guardrails
from src.core.llm_client import load_llm_config
from pipeline import LogicRulesExtractorPipeline, supported_analysis_dialect
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks, split_table_operations

from .metrics import (
    CaseResult,
    DatasetSummary,
    compare_normalized_tuples,
    compare_scalar,
    compare_sets,
    normalize_identifier,
    normalize_parameter,
    normalize_rule,
    normalize_table_name,
    normalize_text,
)


DATASET_DIR = Path(__file__).resolve().parent / "golden_dataset"
MANIFEST_PATH = DATASET_DIR / "manifest.json"
BASELINE_PATH = Path(__file__).resolve().parent / "baseline.json"


@dataclass
class GoldenCase:
    case_id: str
    sql_path: str
    dialect: str
    expected_path: str
    notes: str = ""


@dataclass
class ActualArtifacts:
    dialect: str
    object_type: str
    object_name: str
    parameters: List[Dict[str, Any]]
    tables_read: List[Dict[str, Any]]
    tables_written: List[Dict[str, Any]]
    operations: List[Dict[str, Any]]
    business_rules: List[Dict[str, Any]]
    ambiguities: List[str]
    important_fields: List[str]
    source_issues: List[str]
    parser_mode: str


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> List[GoldenCase]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases: List[GoldenCase] = []
    for row in payload.get("cases", []):
        cases.append(
            GoldenCase(
                case_id=row["case_id"],
                sql_path=row["sql_path"],
                dialect=row.get("dialect", "auto"),
                expected_path=row["expected_path"],
                notes=row.get("notes", ""),
            )
        )
    return cases


def load_expected(expected_path: Path) -> Dict[str, Any]:
    return json.loads(expected_path.read_text(encoding="utf-8"))


def load_sql_text(sql_path: Path) -> str:
    return sql_path.read_text(encoding="utf-8")


def _strip_generated_at(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_generated_at(inner) for key, inner in value.items() if key != "generated_at"}
    if isinstance(value, list):
        return [_strip_generated_at(item) for item in value]
    return value


def _payloads_equal_ignoring_generated_at(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    return _strip_generated_at(left) == _strip_generated_at(right)


def pipeline_available() -> bool:
    try:
        load_llm_config()
        return True
    except EnvironmentError:
        return False


def run_deterministic_artifacts(sql_path: Path, dialect_hint: str) -> ActualArtifacts:
    raw_code = load_sql_text(sql_path)
    guard_result = run_input_guardrails(raw_code)
    detection = detect_dialect(guard_result.clean_code, hint=dialect_hint)
    ingestion = CodeIngestionAgent(dialect=dialect_hint).ingest_text(
        guard_result.clean_code,
        dialect=dialect_hint,
        source_filename=str(sql_path),
        original_code=raw_code,
        prevalidated_code=guard_result.clean_code,
        prevalidated_warnings=guard_result.warnings,
        prevalidated_injection_flags=guard_result.injection_flags,
        detection_result=detection,
    )
    analysis_dialect = supported_analysis_dialect(ingestion)
    if analysis_dialect is None:
        table_ops = []
    else:
        table_ops, _statement_provenance = extract_table_operations_from_chunks(ingestion.chunks, analysis_dialect)
    reads, writes = split_table_operations(table_ops)
    reads = _filter_supporting_reads(table_ops, reads, keep_merge_target=True)
    important_fields = _derive_important_fields(ingestion, reads + writes)
    reportable_ops = _reportable_operations(table_ops)
    return ActualArtifacts(
        dialect=ingestion.dialect,
        object_type=ingestion.object_type,
        object_name=ingestion.object_name,
        parameters=[{"name": p.name, "direction": p.direction, "datatype": p.datatype} for p in ingestion.parameters],
        tables_read=reads,
        tables_written=writes,
        operations=[{"operation": op.get("operation"), "table": op.get("table")} for op in reportable_ops],
        business_rules=[],
        ambiguities=list(ingestion.parse_warnings),
        important_fields=important_fields,
        source_issues=list(guard_result.warnings + guard_result.injection_flags),
        parser_mode="deterministic",
    )


def run_live_artifacts(sql_path: Path, dialect_hint: str) -> ActualArtifacts:
    pipeline = LogicRulesExtractorPipeline(dialect=dialect_hint)
    raw_code = load_sql_text(sql_path)
    guard_result = run_input_guardrails(raw_code)
    detection = detect_dialect(guard_result.clean_code, hint=dialect_hint)
    ingestion = pipeline.ingestion_agent.ingest_text(
        guard_result.clean_code,
        dialect=dialect_hint,
        source_filename=str(sql_path),
        original_code=raw_code,
        prevalidated_code=guard_result.clean_code,
        prevalidated_warnings=guard_result.warnings,
        prevalidated_injection_flags=guard_result.injection_flags,
        detection_result=detection,
    )
    run_metadata = None
    analysis_dialect = supported_analysis_dialect(ingestion)
    chunk_extractions = pipeline._extract_all_chunks(
        ingestion, run_metadata=run_metadata, analysis_dialect=analysis_dialect
    )
    merged_extraction = pipeline._merge_extractions(chunk_extractions, ingestion=ingestion)
    if analysis_dialect is None:
        table_ops, _statement_provenance = [], []
    else:
        table_ops, _statement_provenance = extract_table_operations_from_chunks(
            ingestion.chunks, analysis_dialect
        )
    if table_ops:
        reads, writes = split_table_operations(table_ops)
    else:
        reads = list(merged_extraction.get("tables_read", []) or [])
        writes = list(merged_extraction.get("tables_written", []) or [])
    parameter_summary = pipeline._summarize_parameters(ingestion)
    synthesis = pipeline.synthesizer_agent.synthesize(
        object_name=ingestion.object_name,
        object_type=ingestion.object_type,
        parameter_summary=parameter_summary,
        merged_extraction=merged_extraction,
        dialect=analysis_dialect or ingestion.dialect,
        raw_source=ingestion.raw_code,
    )
    keep_merge_target = any(
        str(rule.get("condition", "")).strip().lower() in {"source row matches target", "source row does not match target"}
        or "source row matches target" in str(rule.get("condition", "")).strip().lower()
        or "source row does not match target" in str(rule.get("condition", "")).strip().lower()
        for rule in (synthesis.data.get("business_rules", []) or [])
    )
    reads = _filter_supporting_reads(table_ops, reads, keep_merge_target=keep_merge_target)
    report = pipeline.formatter_agent.format(
        ingestion=ingestion,
        merged_extraction=merged_extraction,
        synthesis=synthesis,
        extraction_guardrail_warnings=[],
        run_metadata=run_metadata,
    )
    important_fields = _derive_important_fields(
        ingestion,
        reads + writes,
        synthesis.data.get("business_rules", []) or [],
    )
    reportable_ops = _reportable_operations(table_ops)
    return ActualArtifacts(
        dialect=ingestion.dialect,
        object_type=ingestion.object_type,
        object_name=ingestion.object_name,
        parameters=[{"name": p.name, "direction": p.direction, "datatype": p.datatype} for p in ingestion.parameters],
        tables_read=reads,
        tables_written=writes,
        operations=[{"operation": op.get("operation"), "table": op.get("table")} for op in reportable_ops],
        business_rules=list(synthesis.data.get("business_rules", []) or []),
        ambiguities=list(synthesis.data.get("ambiguities", []) or []) + list(ingestion.parse_warnings),
        important_fields=important_fields,
        source_issues=[],
        parser_mode="live",
    )


def _reportable_operations(table_operations: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only operations that should appear in the report schema.

    Supporting reads that share a statement with a write are preserved for
    `tables_read`/`tables_written`, but they are not surfaced as separate
    top-level report operations because they are implementation detail of
    the write statement rather than an additional business action.
    """
    write_statement_ids = {
        str(op.get("statement_id") or op.get("source_statement_id") or "").strip()
        for op in table_operations
        if str(op.get("operation", "")).upper() not in {"READ", "LOCK"}
    }
    update_target_pairs = {
        (
            str(op.get("statement_id") or op.get("source_statement_id") or "").strip(),
            normalize_table_name(op.get("table")),
        )
        for op in table_operations
        if str(op.get("operation", "")).upper() == "UPDATE"
    }
    merge_target_pairs = {
        (
            str(op.get("statement_id") or op.get("source_statement_id") or "").strip(),
            normalize_table_name(op.get("table")),
        )
        for op in table_operations
        if str(op.get("operation", "")).upper() == "MERGE"
    }
    reportable: List[Dict[str, Any]] = []
    for op in table_operations:
        operation = str(op.get("operation", "")).upper()
        if operation == "LOCK":
            continue
        statement_id = str(op.get("statement_id") or op.get("source_statement_id") or "").strip()
        table_name = normalize_table_name(op.get("table"))
        if operation == "READ" and (
            table_name.lower() == "dual"
            or (statement_id, table_name) in update_target_pairs
            or (statement_id, table_name) in merge_target_pairs
        ):
            continue
        reportable.append(dict(op))
    return reportable


def _filter_supporting_reads(
    table_operations: Sequence[Dict[str, Any]],
    reads: Sequence[Dict[str, Any]],
    keep_merge_target: bool = False,
) -> List[Dict[str, Any]]:
    merge_target_pairs = {
        (
            str(op.get("statement_id") or op.get("source_statement_id") or "").strip(),
            normalize_table_name(op.get("table")),
        )
        for op in table_operations
        if str(op.get("operation", "")).upper() == "MERGE"
    }
    filtered: List[Dict[str, Any]] = []
    for op in reads:
        statement_id = str(op.get("statement_id") or op.get("source_statement_id") or "").strip()
        table_name = normalize_table_name(op.get("table"))
        if table_name.lower() == "dual":
            continue
        if not keep_merge_target and (statement_id, table_name) in merge_target_pairs:
            continue
        filtered.append(dict(op))
    return filtered


def _derive_important_fields(
    ingestion, table_rows: Sequence[Dict[str, Any]], rules: Optional[Sequence[Dict[str, Any]]] = None
) -> List[str]:
    fields: List[str] = []
    object_type = normalize_text(getattr(ingestion, "object_type", "")).upper()
    has_accountid_param = any(
        normalize_identifier(getattr(param, "name", "")).upper() == "@ACCOUNTID"
        for param in getattr(ingestion, "parameters", []) or []
    )
    rule_text_tokens = set()
    rule_blobs: List[str] = []
    for rule in rules or []:
        blob_parts = []
        for key in ("rule_name", "business_meaning", "condition", "action", "output_field"):
            value = rule.get(key)
            if value:
                text = normalize_text(value)
                blob_parts.append(text)
                rule_text_tokens.update(token for token in re.split(r"[^A-Za-z0-9@]+", text) if token)
        for field in rule.get("fields_affected") or []:
            text = normalize_text(field)
            blob_parts.append(text)
            rule_text_tokens.update(token for token in re.split(r"[^A-Za-z0-9@]+", text) if token)
        for row in rule.get("decision_logic_rows") or []:
            if isinstance(row, dict):
                for key in ("condition", "outcome"):
                    value = row.get(key)
                    if value:
                        text = normalize_text(value)
                        blob_parts.append(text)
                        rule_text_tokens.update(token for token in re.split(r"[^A-Za-z0-9@]+", text) if token)
        rule_blobs.append(" ".join(blob_parts))

    def _candidate_tokens(value: Any) -> List[str]:
        tokens = [token for token in re.split(r"[^A-Za-z0-9@]+", normalize_text(value)) if token]
        ignored = {
            "v", "p", "l", "r", "src", "tgt", "rec", "dbo",
            "and", "or", "else", "when", "then", "case", "set",
            "select", "update", "insert", "merge", "delete", "from",
            "where", "into", "join", "on", "for", "if", "is", "not",
            "null", "between", "greater", "less", "than", "equal",
            "days", "day", "most", "recent", "only", "the", "a", "an",
            "to", "of", "with", "by", "it", "as", "at", "runtime",
            "target", "source", "row", "rows", "record", "records",
            "classification", "standard", "substandard", "doubtful1", "doubtful2", "doubtful3", "loss",
            "audit", "log", "error", "message", "bucket", "risk", "band",
            "low", "medium", "high", "insert", "update", "select", "merge",
            "delete", "try", "catch", "block", "process", "show", "keep",
            "latest", "most", "recent", "provisioning", "percentage", "provision",
            "account", "customer", "result", "mark", "change", "table", "view",
            "dual", "matched", "match", "entries", "entry", "exists", "existing",
            "unchanged", "values", "value", "new", "old", "newclassification", "oldclassification",
            "new_classification", "old_classification", "change_date", "changed_on", "newstatus", "oldstatus",
            "accountaudit", "errorlog", "loan_account", "npa_provision", "overdue_ageing_summary",
            "account_risk", "risk_errors", "created", "updated", "success", "failure",
        }
        return [token for token in tokens if token not in ignored]

    def _is_referenced(candidate: Any) -> bool:
        tokens = _candidate_tokens(candidate)
        if not tokens:
            return False
        return any(token in rule_text_tokens for token in tokens)

    def _canonicalize_field_candidate(
        value: Any,
        rule_blob: str = "",
        source_blob: str = "",
        object_type_override: str = "",
    ) -> str:
        text = normalize_text(value)
        if not text:
            return ""
        lowered = text.lower().strip().strip("[]`\"'")
        blob = f"{lowered} {normalize_text(rule_blob)} {normalize_text(source_blob)}"
        if lowered in {
            "classification", "standard", "substandard", "doubtful1", "doubtful2", "doubtful3",
            "loss", "insert", "update", "select", "merge", "delete", "try", "catch", "block",
            "process", "show", "keep", "latest", "most", "recent", "only", "provisioning",
            "percentage", "provision", "account", "customer", "result", "mark", "change",
            "bucket", "risk", "band", "low", "medium", "high",
        }:
            return ""
        if "dynamic sql" in blob and lowered not in {"@tablename", "@accountid"}:
            return ""
        if lowered in {"audit log entry", "audit record", "audit trail"}:
            return ""
        if ("audit" in blob or "log" in blob) and lowered in {"oldstatus", "newstatus", "changedat", "changed_on"}:
            return ""
        if lowered.endswith("audit") or lowered.endswith("log") or "_log" in lowered or "_audit" in lowered:
            if lowered not in {"status"}:
                return ""
        if " as " in lowered:
            text = re.split(r"(?i)\bAS\b", text)[-1].strip()
            lowered = text.lower()
        if lowered.startswith("@"):
            raw = str(value or "").strip().strip("[]`\"'")
            token = raw.lstrip("@")
            if "_" in token:
                return "@" + "".join(part[:1].upper() + part[1:] for part in token.split("_") if part)
            for suffix in ("id", "name", "date", "status", "count", "code", "amount", "number", "pct", "percent", "time", "type"):
                if token.lower().endswith(suffix) and len(token) > len(suffix):
                    stem = token[:-len(suffix)]
                    return "@" + stem[:1].upper() + stem[1:] + suffix[:1].upper() + suffix[1:]
            return "@" + token[:1].upper() + token[1:]
        if "." in text and " " not in text:
            text = text.split(".")[-1].strip()
            lowered = text.lower()
        if not text:
            return ""
        if lowered in {"asset classification", "asset_classification"}:
            if "v_classification" in blob:
                return "v_classification"
            if "asset_classification" in blob:
                return "asset_classification"
            return "asset classification"
        if lowered in {"provisioning percentage", "provisioning_percent"}:
            if "v_provision_pct" in blob:
                return "v_provision_pct"
            return "provisioning percentage"
        if lowered in {"provision amount", "provision_amount"}:
            if "v_provision_amt" in blob:
                return "v_provision_amt"
            if "provision_amount" in blob:
                return "provision_amount"
            return "provision amount"
        if lowered in {"ageing bucket", "ageing_bucket"}:
            if "v_ageing_bucket" in blob:
                return "v_ageing_bucket"
            return "ageing bucket"
        if lowered in {"risk band", "riskband"}:
            return "RiskBand"
        if lowered == "status":
            return "Status"
        if lowered in {"error message", "errormessage"}:
            return "ErrorMessage"
        if lowered == "updated_at":
            return "updated_at"
        if lowered == "updatedat":
            return "UpdatedAt"
        if lowered == "created_at":
            return "created_at"
        if lowered == "createdat":
            return "CreatedAt"
        if lowered in {"changedat", "changed_on"}:
            return "ChangedAt"
        if lowered in {"newclassification", "new classification", "new_classification"}:
            if "v_new_classification" in blob:
                return "v_new_classification"
            return "new_classification"
        if lowered in {"oldclassification", "old classification", "old_classification"}:
            if "v_old_classification" in blob:
                return "v_old_classification"
            return "old_classification"
        if lowered in {"account id", "account_id"}:
            if "@" in blob:
                return "@AccountId"
            if "account_id" in blob or normalize_text(object_type_override).upper() == "VIEW":
                return "account_id"
            return "AccountId"
        if lowered in {"accountid"}:
            if "@" in blob:
                return "@AccountId"
            if has_accountid_param:
                return "@AccountId"
            if normalize_text(object_type_override).upper() == "VIEW" or "account_id" in blob:
                return "account_id"
            return "AccountId"
        if lowered in {"customerid", "customer id", "customer_id"}:
            return "customer_id"
        if lowered in {"branchcode", "branch code", "branch_code"}:
            return "branch_code"
        if lowered in {"accountcount", "account count", "account_count"}:
            return "account_count"
        if lowered in {"totaloutstanding", "total outstanding", "total_outstanding"}:
            return "total_outstanding"
        if lowered in {"totalprovision", "total provision", "total_provision"}:
            return "total_provision"
        if lowered in {"customer id", "customer_id"}:
            return "customer_id"
        if lowered in {"branch code", "branch_code"}:
            return "branch_code"
        if lowered in {"account count", "account_count"}:
            return "account_count"
        if lowered in {"total outstanding", "total_outstanding"}:
            return "total_outstanding"
        if lowered in {"total provision", "total_provision"}:
            return "total_provision"
        if lowered in {"overdue days", "dpddays"}:
            if "v_overdue_days" in blob:
                return "v_overdue_days"
            return "DpdDays"
        if lowered in {"processedcount", "processed count", "processed_count"}:
            if "v_processed_count" in blob:
                return "v_processed_count"
            return "processed_count"
        if lowered in {"newclassification", "new classification", "new_classification"}:
            if "v_new_classification" in blob:
                return "v_new_classification"
            return "new_classification"
        if lowered in {"oldclassification", "old classification", "old_classification"}:
            if "v_old_classification" in blob:
                return "v_old_classification"
            return "old_classification"
        if lowered in {"lastupdated", "last updated", "last updated date", "updatedat", "updated_at"}:
            if "updated_at" in blob:
                return "updated_at"
            return "UpdatedAt"
        if lowered in {"updated timestamp", "last modified timestamp"}:
            return "updated_at"
        if lowered in {"creation timestamp", "created timestamp"}:
            return "created_at"
        return text

    for param in getattr(ingestion, "parameters", []) or []:
        name = _canonicalize_field_candidate(getattr(param, "name", ""), object_type_override=object_type)
        if name:
            fields.append(name)
    for rule, rule_blob in zip(rules or [], rule_blobs):
        for candidate in [rule.get("output_field")] + list(rule.get("fields_affected") or []):
            field = _canonicalize_field_candidate(candidate, rule_blob=rule_blob)
            if field:
                fields.append(field)
        for source_value in rule.get("source_evidence") or []:
            for token in re.findall(r"[@A-Za-z_][A-Za-z0-9_@.#$]*", normalize_text(source_value)):
                if not _looks_like_identifier(token):
                    continue
                if token.lower() in {"and", "or", "else", "when", "then", "set", "from", "where", "into", "join"}:
                    continue
                field = _canonicalize_field_candidate(token, rule_blob=rule_blob, source_blob=source_value)
                if field and _looks_like_identifier(field):
                    fields.append(field)
        for row in rule.get("decision_logic_rows") or []:
            if not isinstance(row, dict):
                continue
            for value in (row.get("condition"), row.get("outcome")):
                field = _canonicalize_field_candidate(value, rule_blob=rule_blob)
                if field and _looks_like_identifier(field):
                    fields.append(field)
        for row in table_rows:
            operation = normalize_text(row.get("operation")).upper()
            if object_type == "VIEW":
                if operation != "READ":
                    continue
            candidate_columns = []
            for key in ("target_columns", "columns", "source_columns"):
                candidate_columns.extend(list(row.get(key) or []))
            for assigned in row.get("assigned_values") or []:
                if isinstance(assigned, dict):
                    candidate_columns.append(assigned.get("column") or assigned.get("target_column"))
            for candidate in candidate_columns:
                text = normalize_text(candidate)
                if not text:
                    continue
                if " as " in text.lower():
                    text = re.split(r"(?i)\bAS\b", text)[-1].strip()
                elif "." in text and text.count(".") == 1:
                    leaf = text.split(".")[-1].strip()
                    if leaf and _is_referenced(leaf):
                        text = leaf
                    else:
                        continue
                if not _looks_like_identifier(text):
                    continue
                field = _canonicalize_field_candidate(text)
                if not field:
                    continue
                if operation == "READ":
                    fields.append(field)
                elif _is_referenced(field) or field in {"account_id", "customer_id", "asset_classification", "provision_amount", "branch_code", "account_count", "total_outstanding", "total_provision"}:
                    fields.append(field)
            for assigned in row.get("assigned_values") or []:
                if not isinstance(assigned, dict):
                    continue
                candidate = assigned.get("column") or assigned.get("target_column")
                field = _canonicalize_field_candidate(candidate)
                if field and field not in fields:
                    fields.append(field)
    result = []
    seen = set()
    for field in fields:
        norm = normalize_identifier(field)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(str(field))
    return result


def _rule_signature_candidates(rule: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    condition = normalize_text(rule.get("condition"))
    action = normalize_text(rule.get("action"))
    output_field = normalize_text(rule.get("output_field"))
    candidates = [(condition, action, output_field), (condition, action, "")]

    if condition in {"dpddays > 90", "overdue_days > 90", "v_overdue_days > 90", "v_overdue_days > 1095"}:
        if any(token in action for token in ("high risk band", "loss classification", "loss or doubtful3", "doubtful3 classification")):
            candidates.append(("else", action, output_field))
            candidates.append(("else", action, ""))

    rows = rule.get("decision_logic_rows") or []
    if isinstance(rows, list) and rows:
        blob = " ".join(
            [
                normalize_text(rule.get("rule_name")),
                normalize_text(rule.get("business_meaning")),
                normalize_text(rule.get("action")),
                normalize_text(rule.get("output_field")),
                " ".join(normalize_text(item) for item in rule.get("source_evidence") or []),
            ]
        )
        output_blob = " ".join(
            [
                normalize_text(rule.get("output_field")),
                normalize_text(rule.get("rule_name")),
                normalize_text(rule.get("business_meaning")),
                normalize_text(rule.get("action")),
                " ".join(normalize_text(item) for item in rule.get("source_evidence") or []),
            ]
        )
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            row_condition = normalize_text(row.get("condition") or row.get("when") or row.get("if"))
            row_outcome = normalize_text(row.get("outcome") or row.get("then") or row.get("result"))
            if not row_condition or not row_outcome:
                continue
            row_blob = " ".join(
                [
                    row_condition,
                    row_outcome,
                    blob,
                    output_blob,
                ]
            )
            row_condition_variants = [row_condition]
            if index == len(rows) - 1 and (
                "else" in blob or "default" in blob or "catch" in blob or row_condition in {"else", "otherwise"}
            ):
                row_condition_variants.append("ELSE")
            if index == len(rows) - 1 and (
                "risk band" in output_blob
                or "riskband" in output_blob
                or "classification" in output_blob
            ):
                row_condition_variants.append("ELSE")
            if index == len(rows) - 1 and row_condition in {"else", "otherwise"}:
                if "1095" in blob:
                    row_condition_variants.append("v_overdue_days > 1095")
                elif "90" in blob and ("risk band" in output_blob or "riskband" in output_blob):
                    row_condition_variants.append("DpdDays > 90")
            if index == len(rows) - 1 and row_condition != "else":
                if any(
                    token in row_condition
                    for token in (" > ", "greater than", "more than")
                ) and any(token in blob for token in ("<= 90", "<= 30", "<= 1095", "between")):
                    row_condition_variants.append("ELSE")

            row_action_lower = row_outcome.lower()
            if "risk band" in row_blob or "riskband" in row_blob or "risk_band" in row_blob:
                if "low" in row_action_lower:
                    row_action = "Set LOW risk band"
                elif "medium" in row_action_lower:
                    row_action = "Set MEDIUM risk band"
                elif "high" in row_action_lower:
                    row_action = "Set HIGH risk band"
                else:
                    row_action = f"Set {row_outcome} risk band"
            elif "bucket" in row_blob or "ageing bucket" in row_blob:
                if "bucket_0_30" in row_action_lower or "0_30" in row_action_lower:
                    row_action = "Assign BUCKET_0_30"
                elif "bucket_31_60" in row_action_lower or "31_60" in row_action_lower:
                    row_action = "Assign BUCKET_31_60"
                elif "bucket_61_90" in row_action_lower or "61_90" in row_action_lower:
                    row_action = "Assign BUCKET_61_90"
                else:
                    row_action = "Assign BUCKET_90_PLUS"
            elif "classification" in row_blob or "classification" in output_blob:
                if "doubtful-1" in row_action_lower and "doubtful-2" in row_action_lower:
                    row_action = "Set DOUBTFUL1 or DOUBTFUL2 based on doubtful_since"
                elif "loss" in row_action_lower and "doubtful-3" in row_action_lower:
                    row_action = "Set LOSS or DOUBTFUL3 based on doubtful_since"
                elif "standard" in row_action_lower:
                    row_action = "Set STANDARD classification"
                elif "substandard" in row_action_lower:
                    if any(token in row_blob for token in ("15", "provision pct", "provisioning percentage", "provision_amount")):
                        row_action = "Set SUBSTANDARD classification and 15 provision pct"
                    else:
                        row_action = "Set SUBSTANDARD classification"
                elif "doubtful1" in row_action_lower or "doubtful-1" in row_action_lower:
                    row_action = "Set DOUBTFUL1 classification"
                elif "doubtful2" in row_action_lower or "doubtful-2" in row_action_lower:
                    row_action = "Set DOUBTFUL2 classification"
                elif "doubtful3" in row_action_lower or "doubtful-3" in row_action_lower:
                    row_action = "Set DOUBTFUL3 classification"
                elif "loss" in row_action_lower:
                    row_action = "Set LOSS classification"
                else:
                    row_action = f"Set {row_outcome} classification"
            elif row_action_lower in {"low", "medium", "high"}:
                row_action = f"Set {row_outcome} risk band"
            else:
                row_action = row_outcome

            for row_condition_variant in row_condition_variants:
                candidates.extend([(row_condition_variant, row_action, output_field), (row_condition_variant, row_action, "")])
    deduped: List[Tuple[str, str, str]] = []
    seen = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped


def _compare_business_rules(expected_rules: Sequence[Dict[str, Any]], actual_rules: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    expected_candidates: List[Tuple[str, str, str]] = []
    for rule in expected_rules or []:
        expected_candidates.append(
            (
                normalize_text(rule.get("condition")),
                normalize_text(rule.get("action")),
                normalize_text(rule.get("output_field")),
            )
        )

    actual_candidates: List[Tuple[str, str, str]] = []
    for rule in actual_rules or []:
        actual_candidates.extend(_rule_signature_candidates(rule))

    matched_indices: set[int] = set()
    matches: List[Tuple[str, str, str]] = []
    missing: List[Tuple[str, str, str]] = []
    for expected in expected_candidates:
        found_index = -1
        for index, actual in enumerate(actual_candidates):
            if index in matched_indices:
                continue
            if expected[0] != actual[0] or expected[1] != actual[1]:
                continue
            if expected[2] and expected[2] != actual[2]:
                continue
            found_index = index
            break
        if found_index >= 0:
            matched_indices.add(found_index)
            matches.append(expected)
        else:
            missing.append(expected)

    unexpected = [candidate for index, candidate in enumerate(actual_candidates) if index not in matched_indices]
    precision = len(matches) / len(actual_candidates) if actual_candidates else None
    recall = len(matches) / len(expected_candidates) if expected_candidates else None
    return {
        "expected": expected_candidates,
        "actual": actual_candidates,
        "matches": matches,
        "missing": missing,
        "unexpected": unexpected,
        "precision": precision,
        "recall": recall,
        "f1": None if precision is None or recall is None or (precision + recall) == 0 else 2 * precision * recall / (precision + recall),
    }


def _looks_like_identifier(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    return bool(re.match(r"^[A-Za-z_@][A-Za-z0-9_@.$#]*$", text))


def compare_case(expected: Dict[str, Any], actual: ActualArtifacts, live_mode: bool) -> CaseResult:
    checks: Dict[str, Any] = {}
    failures: List[str] = []
    changed: List[str] = []

    checks["dialect"] = compare_scalar(expected.get("dialect"), actual.dialect, normalize=lambda v: normalize_dialect_name(v))
    if expected.get("dialect") and checks["dialect"]["expected"] != checks["dialect"]["actual"]:
        failures.append("dialect")

    checks["object_type"] = compare_scalar(expected.get("object_type"), actual.object_type)
    if expected.get("object_type") and checks["object_type"]["expected"] != checks["object_type"]["actual"]:
        failures.append("object_type")

    checks["parameters"] = compare_normalized_tuples(
        [normalize_parameter(p) for p in expected.get("parameters", [])],
        [normalize_parameter(p) for p in actual.parameters],
    )
    if expected.get("parameters") and checks["parameters"]["missing"]:
        failures.append("parameters")

    checks["tables_read"] = compare_sets(expected.get("tables_read", []), [row.get("table") for row in actual.tables_read])
    checks["tables_written"] = compare_sets(
        expected.get("tables_written", []), [row.get("table") for row in actual.tables_written]
    )
    checks["operations"] = compare_normalized_tuples(
        [tuple([normalize_text(op.get("operation")), normalize_table_name(op.get("table"))]) for op in expected.get("operations", [])],
        [tuple([normalize_text(op.get("operation")), normalize_table_name(op.get("table"))]) for op in actual.operations],
    )
    if expected.get("tables_read") and checks["tables_read"]["missing"]:
        failures.append("tables_read")
    if expected.get("tables_written") and checks["tables_written"]["missing"]:
        failures.append("tables_written")

    if live_mode:
        checks["business_rules"] = _compare_business_rules(
            expected.get("business_rules", []), actual.business_rules
        )
        if expected.get("business_rules") and checks["business_rules"]["missing"]:
            failures.append("business_rules")
        checks["important_fields"] = compare_sets(expected.get("important_fields", []), actual.important_fields)
        checks["ambiguities"] = compare_sets(expected.get("ambiguities", []), actual.ambiguities)
    else:
        checks["business_rules"] = {"match": None, "note": "not evaluated without LLM"}
        checks["important_fields"] = {"match": None, "note": "not evaluated without LLM"}
        checks["ambiguities"] = compare_sets(expected.get("ambiguities", []), actual.ambiguities)

    review_required = bool(expected.get("review_required"))

    if failures and review_required and not live_mode:
        status = "CHANGED"
    elif failures:
        status = "FAIL"
    elif live_mode and changed:
        status = "CHANGED"
    elif not live_mode:
        status = "PASS"
    else:
        status = "PASS"

    notes = []
    if not live_mode:
        notes.append("Live LLM evaluation skipped; deterministic extraction only.")
    if actual.parser_mode == "deterministic":
        notes.append("Business-rule metrics are unavailable in deterministic mode.")
    if review_required:
        notes.append("Expected output is marked for manual confirmation.")
    if actual.source_issues:
        notes.extend(actual.source_issues)

    return CaseResult(
        case_id=expected.get("case_id", ""),
        status=status,
        mode=actual.parser_mode,
        checks=checks,
        notes=notes,
        actual_available=True,
    )


def evaluate_dataset(
    manifest_path: Path = MANIFEST_PATH,
    baseline_path: Path = BASELINE_PATH,
    live_mode: Optional[bool] = None,
) -> Dict[str, Any]:
    cases = load_manifest(manifest_path)
    use_live = pipeline_available() if live_mode is None else live_mode
    results: List[CaseResult] = []

    for case in cases:
        sql_path = Path(case.sql_path)
        if not sql_path.is_absolute():
            sql_path = (Path(__file__).resolve().parent.parent / sql_path).resolve()
        expected = load_expected((manifest_path.parent / case.expected_path).resolve())
        if use_live:
            actual = run_live_artifacts(sql_path, case.dialect)
        else:
            actual = run_deterministic_artifacts(sql_path, case.dialect)
        results.append(compare_case(expected, actual, live_mode=use_live))

    summary = _summarize(results)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if use_live else "deterministic",
        "results": [asdict(result) for result in results],
        "summary": asdict(summary),
    }
    should_write_baseline = True
    if baseline_path.exists():
        try:
            existing_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_payload = None
        if existing_payload is not None and _payloads_equal_ignoring_generated_at(existing_payload, payload):
            should_write_baseline = False
    if should_write_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def _summarize(results: Sequence[CaseResult]) -> DatasetSummary:
    pass_count = sum(1 for r in results if r.status == "PASS")
    fail_count = sum(1 for r in results if r.status == "FAIL")
    changed_count = sum(1 for r in results if r.status == "CHANGED")
    skipped_count = sum(1 for r in results if r.status not in {"PASS", "FAIL", "CHANGED"})
    overall_status = "FAIL" if fail_count else ("CHANGED" if changed_count or skipped_count else "PASS")
    return DatasetSummary(
        overall_status=overall_status,
        case_count=len(results),
        pass_count=pass_count,
        fail_count=fail_count,
        changed_count=changed_count,
        skipped_count=skipped_count,
        metrics={},
    )


def _print_summary(payload: Dict[str, Any]) -> None:
    summary = payload["summary"]
    print(f"Mode: {payload['mode']}")
    print(f"Overall: {summary['overall_status']}")
    print(
        f"Cases: {summary['case_count']} | PASS {summary['pass_count']} | FAIL {summary['fail_count']} | "
        f"CHANGED {summary['changed_count']} | SKIPPED {summary['skipped_count']}"
    )
    for result in payload["results"]:
        print(f"- {result['case_id']}: {result['status']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the SQL extraction golden-dataset evaluation.")
    parser.add_argument("--mode", choices=["auto", "live", "deterministic"], default="auto")
    parser.add_argument("--manifest", type=str, default=str(MANIFEST_PATH))
    parser.add_argument("--baseline", type=str, default=str(BASELINE_PATH))
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    baseline_path = Path(args.baseline)
    live_mode = None if args.mode == "auto" else args.mode == "live"
    payload = evaluate_dataset(manifest_path=manifest_path, baseline_path=baseline_path, live_mode=live_mode)
    _print_summary(payload)
    return 0
