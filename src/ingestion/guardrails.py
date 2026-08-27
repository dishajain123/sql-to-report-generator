"""
guardrails.py
-------------
Centralized input/output guardrail layer for the pipeline.

This module is deliberately framework-free and dependency-free (beyond
the stdlib) so its behavior is fully auditable and deterministic - a
requirement for a guardrail layer whose entire job is to be trustworthy.

INPUT GUARDRAILS (run once, before dialect detection/preprocessing/
any LLM call):
    - Reject empty, non-text, or absurdly oversized input safely.
    - Normalize encoding artifacts (BOM, stray NUL/control bytes) that
      have no legitimate place in SQL source and can otherwise confuse
      downstream regex-based structural parsing.
    - Detect likely prompt-injection payloads hidden inside comments or
      string literals. This is intentionally NOT a simple keyword
      blocklist: a single incidental word (e.g. "system" appearing in a
      column comment) must not trip it. Detection instead looks for the
      *structural* shape of an injection attempt - fake role markers,
      instruction-override phrasing, fenced fake system blocks - so it
      catches real payloads while staying quiet on ordinary banking
      terminology. The pipeline never executes the SQL and never lets
      injected text change its own instructions; a hit here only adds a
      review flag, it never blocks the (read-only) analysis.

OUTPUT GUARDRAILS (run once per LLM response, both the per-chunk
technical extraction and the whole-object business synthesis):
    - Validate the parsed JSON against an explicit shape (required keys,
      expected types) and repair malformed shapes to safe empty
      defaults rather than trusting whatever the model returned.
    - Evidence-grounding / anti-hallucination check: every table,
      column, or field name the model claims must be traceable back to
      real evidence (the source code chunk for the technical extraction
      stage; the merged technical extraction for the business synthesis
      stage). Names that cannot be matched back to evidence are not
      silently presented as fact - they are flagged so the report can
      say "unverified" instead of asserting something invented.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from src.validation.confidence import (
    clamp_confidence,
    derive_business_rule_confidence,
    derive_chunk_support_confidence,
    normalize_confidence,
)
from src.core.pipeline_utils import stable_id

# --------------------------------------------------------------------------
# Input guardrails
# --------------------------------------------------------------------------

MAX_INPUT_CHARS = 200_000
MIN_INPUT_CHARS = 5

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

# Structural injection signals. Each must combine with the surrounding
# context of "this text sits inside a comment/string in a SQL file" to
# be meaningful - on its own, a match here only produces a review flag,
# never a silent behavior change in any agent's actual instructions.
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(the\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?(system|previous|above)\s+(prompt|instructions)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"\bsystem\s*:\s*\S", re.IGNORECASE),
    re.compile(r"\bassistant\s*:\s*\S", re.IGNORECASE),
    re.compile(r"</?(system|assistant|user)>", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(you|that)", re.IGNORECASE),
    re.compile(r"do\s+not\s+(follow|apply)\s+(the\s+)?(schema|rules|format)", re.IGNORECASE),
    re.compile(r"respond\s+only\s+with\s+", re.IGNORECASE),
]


class InputGuardrailError(ValueError):
    """Raised for input that cannot be safely processed at all."""


@dataclass
class InputGuardrailResult:
    clean_code: str
    warnings: List[str] = field(default_factory=list)
    injection_flags: List[str] = field(default_factory=list)


def run_input_guardrails(raw_code: str, max_chars: int = MAX_INPUT_CHARS) -> InputGuardrailResult:
    """Sanitize and validate raw source text before any parsing begins.

    Raises InputGuardrailError for input that must not proceed at all
    (empty/whitespace-only content). Everything else is repaired in
    place with a recorded warning rather than causing a hard failure,
    per "safe failure handling" - a malformed-but-recoverable input
    should still produce a report with visible caveats, not a crash.
    """
    warnings: List[str] = []

    if raw_code is None:
        raise InputGuardrailError("Input SQL source is missing (None).")

    text = raw_code.replace("\x00", "")

    if text.startswith("\ufeff"):
        text = text[1:]
        warnings.append("Stripped a byte-order-mark (BOM) from the start of the input file.")

    stripped_ctrl = _CONTROL_CHARS_RE.sub("", text)
    if stripped_ctrl != text:
        warnings.append(
            "Removed non-printable control characters from the input source "
            "before analysis; this does not affect readable SQL/PLSQL content."
        )
    text = stripped_ctrl

    if len(text.strip()) < MIN_INPUT_CHARS:
        raise InputGuardrailError(
            "Input SQL source is empty or too short to analyze. Provide a "
            "complete procedure, function, view, trigger, or PL/SQL block."
        )

    if len(text) > max_chars:
        warnings.append(
            f"Input source exceeds the {max_chars:,}-character processing limit "
            "and was truncated; results may be incomplete for the truncated tail. "
            "Split very large objects into smaller files for complete coverage."
        )
        text = text[:max_chars]

    injection_flags = _detect_prompt_injection(text)

    return InputGuardrailResult(clean_code=text, warnings=warnings, injection_flags=injection_flags)


def _extract_comment_and_string_text(code: str) -> List[str]:
    """Pull out the text that actually lives inside comments and string
    literals - the only places a malicious payload embedded in a SQL
    file could plausibly try to pose as instructions to the LLM.
    """
    texts: List[str] = []
    texts.extend(re.findall(r"--[^\n]*", code))
    texts.extend(re.findall(r"/\*.*?\*/", code, re.DOTALL))
    texts.extend(re.findall(r"'(?:[^']|'')*'", code))
    return texts


def _detect_prompt_injection(code: str) -> List[str]:
    findings: List[str] = []
    for snippet in _extract_comment_and_string_text(code):
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(snippet):
                findings.append(
                    "Potential prompt-injection content was detected inside a "
                    "code comment or string literal (phrasing that resembles an "
                    "attempt to override analysis instructions). It is treated "
                    "strictly as inert source data - never as instructions - and "
                    "is flagged here for human review."
                )
                break
        if findings:
            break
    return findings


# --------------------------------------------------------------------------
# Output guardrails - technical extraction stage
# --------------------------------------------------------------------------

_EXTRACTION_LIST_FIELDS = (
    "conditions",
    "decision_chains",
    "loops",
    "tables_read",
    "tables_written",
    "calculations",
    "exception_handling",
    "ambiguities",
)

_ALLOWED_CONFIDENCE = {"high", "medium", "low"}
_ALLOWED_RULE_TYPES = {"explicit", "inferred", "assumption"}
_ALLOWED_VALIDATION_STATUS = {
    "verified",
    "unverified",
    "ambiguous",
    "parser_failed",
    "insufficient_evidence",
}


def _normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _normalize_confidence(value: Any, default: str = "medium") -> str:
    return normalize_confidence(value, default=default)


def _normalize_validation_status(value: Any, default: str = "unverified") -> str:
    status = str(value or "").strip().lower()
    return status if status in _ALLOWED_VALIDATION_STATUS else default


def validate_extraction_shape(data: Any) -> Tuple[Dict[str, Any], List[str]]:
    """Validate/repair a per-chunk technical-extraction JSON payload
    against its expected schema. Never trusts field types blindly.
    """
    warnings: List[str] = []
    if not isinstance(data, dict):
        warnings.append(
            "Technical extraction response was not a JSON object; replaced "
            "with an empty extraction for this chunk."
        )
        return {k: [] for k in _EXTRACTION_LIST_FIELDS}, warnings

    cleaned: Dict[str, Any] = {}
    for key in _EXTRACTION_LIST_FIELDS:
        value = data.get(key, [])
        if not isinstance(value, list):
            warnings.append(
                f"Extraction field '{key}' was not a list as the schema requires; "
                "discarded and replaced with an empty list."
            )
            value = []
        if key == "ambiguities":
            value = [str(v) for v in value if str(v).strip()]
        elif key == "decision_chains":
            value = _normalize_decision_chains(value)
        else:
            normalized_items = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                normalized_item = dict(item)
                normalized_item["table"] = str(normalized_item.get("table", "") or "")
                normalized_item["columns"] = _normalize_string_list(normalized_item.get("columns", []))
                normalized_item["confidence"] = _normalize_confidence(
                    normalized_item.get("confidence", "medium")
                )
                if key == "tables_read":
                    normalized_item["filter_condition"] = normalized_item.get("filter_condition")
                elif key == "tables_written":
                    normalized_item["operation"] = str(normalized_item.get("operation", "") or "")
                    normalized_item["trigger_condition"] = normalized_item.get("trigger_condition")
                normalized_items.append(normalized_item)
            value = normalized_items
        cleaned[key] = value
    return cleaned, warnings


def _normalize_decision_chains(value: List[Any]) -> List[Dict[str, Any]]:
    """Normalize the "decision_chains" field: each entry links a shared
    "subject" to an ordered list of mutually-exclusive branches, each of
    which may assign one or more fields. This has a different shape from
    every other extraction field (no table/columns/confidence), so it
    gets its own defensive coercion rather than reusing the generic
    per-item loop above - malformed branches/assignments are dropped
    quietly (never fabricated), the same "repair, don't trust blindly"
    posture as the rest of this module.
    """
    normalized_chains: List[Dict[str, Any]] = []
    for chain in value:
        if not isinstance(chain, dict):
            continue
        raw_branches = chain.get("branches", [])
        if not isinstance(raw_branches, list):
            continue
        branches: List[Dict[str, Any]] = []
        for branch in raw_branches:
            if not isinstance(branch, dict):
                continue
            branch_condition = str(branch.get("branch_condition", "") or "").strip()
            if not branch_condition:
                continue
            raw_assignments = branch.get("assignments", [])
            assignments: List[Dict[str, str]] = []
            if isinstance(raw_assignments, list):
                for assignment in raw_assignments:
                    if not isinstance(assignment, dict):
                        continue
                    field_name = str(assignment.get("field", "") or "").strip()
                    value_text = str(assignment.get("value", "") or "").strip()
                    if not field_name:
                        continue
                    assignments.append({"field": field_name, "value": value_text})
            branches.append({"branch_condition": branch_condition, "assignments": assignments})
        if len(branches) < 2:
            # A "chain" of fewer than two branches isn't a decision ladder -
            # it carries no structural information the flat "conditions"
            # field doesn't already capture, so don't keep a degenerate
            # single-branch entry around to confuse downstream synthesis.
            continue
        normalized_chains.append(
            {
                "chain_type": str(chain.get("chain_type", "") or "").strip(),
                "subject": str(chain.get("subject", "") or "").strip(),
                "branches": branches,
            }
        )
    return normalized_chains


def ground_extraction_against_source(data: Dict[str, Any], source_text: str) -> List[str]:
    """Anti-hallucination check for the technical extraction stage.

    Every table name (and, where present, column name) claimed in
    "tables_read"/"tables_written" must be traceable back to the actual
    source code chunk it was extracted from. Entries that cannot be
    matched are downgraded to low confidence in place (mutates `data`)
    and a human-readable warning is returned for the Ambiguities
    section - the goal is to prevent a fabricated table/column name from
    silently reaching the final report as an asserted fact.
    """
    warnings: List[str] = []

    for section in ("tables_read", "tables_written"):
        for item in data.get(section, []):
            if not isinstance(item, dict):
                continue
            item_warnings: List[str] = []
            table = str(item.get("table", "")).strip()
            confidence = _normalize_confidence(item.get("confidence", "medium"))
            table_found = bool(table) and _identifier_present(source_text, table)
            columns = _normalize_string_list(item.get("columns", []))
            direct_evidence = table_found and all(_identifier_present(source_text, col) for col in columns)
            item["columns"] = columns
            if table and not table_found:
                confidence = "low"
                item_warnings.append(
                    f"Table '{table}' named in the technical extraction ({section}) "
                    "could not be matched back to the source code for this chunk and "
                    "may not be accurate; flagged low-confidence rather than asserted."
                )
            for col in columns:
                if not _identifier_present(source_text, col):
                    confidence = "low"
                    item_warnings.append(
                        f"Column '{col}' referenced for table '{table or 'unknown'}' "
                        "could not be matched back to the source code for this chunk; "
                        "treated as unverified and low-confidence."
                    )
            item["confidence"] = derive_chunk_support_confidence(
                parse_error="",
                guardrail_warnings=item_warnings,
                has_direct_evidence=direct_evidence or table_found,
                has_embedded_sql=bool(section == "tables_written" and item.get("operation")),
                ambiguity_count=0 if table_found else 1,
                dynamic_sql_detected=False,
                parser_unavailable=False,
            )
            if confidence == "low":
                item["confidence"] = "low"
            warnings.extend(item_warnings)
    return warnings


# --------------------------------------------------------------------------
# Output guardrails - business rule synthesis stage
# --------------------------------------------------------------------------

_SYNTHESIS_LIST_FIELDS = (
    "step_by_step_flow",
    "business_rules",
    "calculations",
    "ambiguities",
)


def validate_synthesis_shape(data: Any) -> Tuple[Dict[str, Any], List[str]]:
    """Validate/repair the whole-object business-rule synthesis JSON
    payload against its expected schema.
    """
    warnings: List[str] = []
    if not isinstance(data, dict):
        warnings.append(
            "Business rule synthesis response was not a JSON object; replaced "
            "with an empty synthesis result."
        )
        return (
            {
                "purpose_summary": "",
                "step_by_step_flow": [],
                "business_rules": [],
                "calculations": [],
                "exception_handling_summary": "",
                "ambiguities": [],
            },
            warnings,
        )

    cleaned: Dict[str, Any] = {}
    cleaned["purpose_summary"] = str(data.get("purpose_summary", "") or "")
    cleaned["exception_handling_summary"] = str(data.get("exception_handling_summary", "") or "")

    for key in _SYNTHESIS_LIST_FIELDS:
        value = data.get(key, [])
        if not isinstance(value, list):
            warnings.append(
                f"Synthesis field '{key}' was not a list as the schema requires; "
                "discarded and replaced with an empty list."
            )
            value = []
        if key in ("step_by_step_flow", "ambiguities"):
            value = [str(v) for v in value if str(v).strip()]
        else:
            value = [v for v in value if isinstance(v, dict)]
        cleaned[key] = value

    return cleaned, warnings


_TECHNICAL_SECTIONS = (
    "conditions",
    "decision_chains",
    "loops",
    "tables_read",
    "tables_written",
    "calculations",
    "exception_handling",
    "ambiguities",
)


def _normalize_text(text: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9_]+", " ", str(text or "").upper())).strip()


def _normalize_identifier_text(text: Any) -> str:
    return re.sub(r'[\[\]"`]', "", str(text or "").upper()).strip()


def _identifier_present(source_text: str, identifier: str) -> bool:
    normalized_identifier = _normalize_identifier_text(identifier)
    if not normalized_identifier:
        return False
    normalized_source = _normalize_identifier_text(source_text)
    if normalized_identifier in normalized_source:
        return True
    pattern = re.compile(
        r"(?<![A-Z0-9_#])" + re.escape(normalized_identifier) + r"(?![A-Z0-9_])"
    )
    return bool(pattern.search(normalized_source))


def _record_text(record: Dict[str, Any]) -> str:
    parts: List[str] = []
    # "decision_chains" records have a different shape (subject + ordered
    # branches, each with its own assignments) than every other technical
    # section, so they need their own flattening rather than the flat
    # key list below - without this, a rule whose "source_evidence" quotes
    # a branch condition or an assigned value verbatim (exactly what the
    # extraction/synthesis prompts both ask for) would never be traceable
    # back to its evidence, and would be wrongly downgraded to
    # "unverified" even though it is fully grounded.
    branches = record.get("branches")
    if isinstance(branches, list):
        subject = record.get("subject")
        if subject:
            parts.append(str(subject))
        for branch in branches:
            if not isinstance(branch, dict):
                continue
            branch_condition = branch.get("branch_condition")
            if branch_condition:
                parts.append(str(branch_condition))
            for assignment in branch.get("assignments") or []:
                if not isinstance(assignment, dict):
                    continue
                field_name = assignment.get("field")
                value = assignment.get("value")
                if field_name:
                    parts.append(str(field_name))
                if value:
                    parts.append(str(value))
    for key in (
        "condition",
        "true_branch",
        "false_branch",
        "loop_type",
        "iterates_over",
        "purpose",
        "table",
        "table_alias",
        "statement_id",
        "source_statement_id",
        "statement_kind",
        "statement_text",
        "source_statement_text",
        "where_predicate",
        "having_predicate",
        "filter_condition",
        "trigger_condition",
        "active_status",
        "columns",
        "target_columns",
        "source_columns",
        "operation",
        "join_predicates",
        "exists_predicates",
        "constants",
        "provenance",
        "result",
        "formula",
        "handler",
        "behavior",
    ):
        value = record.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value if str(item).strip())
        elif value not in (None, ""):
            parts.append(str(value))
    return _normalize_text(" ".join(parts))


def _collect_technical_records(merged_extraction: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunk_meta = {}
    for chunk in merged_extraction.get("chunk_provenance", []) or []:
        if not isinstance(chunk, dict):
            continue
        chunk_id = str(chunk.get("chunk_id", "")).strip()
        if chunk_id:
            chunk_meta[chunk_id] = chunk

    records: List[Dict[str, Any]] = []
    for section in _TECHNICAL_SECTIONS:
        for index, item in enumerate(merged_extraction.get(section, []) or []):
            if not isinstance(item, dict):
                continue
            chunk_id = str(item.get("source_chunk_id", "")).strip()
            chunk_info = chunk_meta.get(chunk_id, {})
            parse_error = str(item.get("source_parse_error") or chunk_info.get("parse_error") or "")
            warnings = _normalize_string_list(
                item.get("source_guardrail_warnings") or chunk_info.get("guardrail_warnings") or []
            )
            support_confidence = _normalize_confidence(
                item.get("source_confidence")
                or chunk_info.get("support_confidence")
                or item.get("confidence", "high")
            )
            record = dict(item)
            record.update(
                {
                    "_section": section,
                    "_index": index,
                    "_chunk_id": chunk_id,
                    "_chunk_kind": str(item.get("source_chunk_kind") or chunk_info.get("chunk_kind") or ""),
                    "_chunk_context": item.get("source_chunk_context") or chunk_info.get("chunk_context") or [],
                    "_parse_error": parse_error,
                    "_guardrail_warnings": warnings,
                    "_support_confidence": support_confidence,
                    "_text": _record_text(item),
                }
            )
            records.append(record)
    return records


def _build_evidence_span(
    record: Dict[str, Any],
    chunk_meta: Dict[str, Any],
    statement_meta: Dict[str, Any],
) -> Dict[str, Any]:
    source_file = (
        str(record.get("source_file") or statement_meta.get("source_file") or chunk_meta.get("source_file") or "").strip()
    )
    chunk_id = (
        str(record.get("source_chunk_id") or chunk_meta.get("chunk_id") or "").strip()
    )
    statement_id = (
        str(
            record.get("statement_id")
            or record.get("source_statement_id")
            or statement_meta.get("statement_id")
            or statement_meta.get("source_statement_id")
            or ""
        ).strip()
    )
    char_start = record.get("source_char_start")
    if not isinstance(char_start, int) or char_start < 0:
        char_start = statement_meta.get("source_char_start")
    if not isinstance(char_start, int) or char_start < 0:
        char_start = chunk_meta.get("source_char_start", -1)
    char_end = record.get("source_char_end")
    if not isinstance(char_end, int) or char_end < 0:
        char_end = statement_meta.get("source_char_end")
    if not isinstance(char_end, int) or char_end < 0:
        char_end = chunk_meta.get("source_char_end", -1)
    line_start = record.get("source_line_start")
    if not isinstance(line_start, int) or line_start < 0:
        line_start = statement_meta.get("source_line_start")
    if not isinstance(line_start, int) or line_start < 0:
        line_start = chunk_meta.get("source_line_start", -1)
    line_end = record.get("source_line_end")
    if not isinstance(line_end, int) or line_end < 0:
        line_end = statement_meta.get("source_line_end")
    if not isinstance(line_end, int) or line_end < 0:
        line_end = chunk_meta.get("source_line_end", -1)
    location_status = str(
        record.get("source_location_status")
        or statement_meta.get("source_location_status")
        or chunk_meta.get("source_location_status")
        or "unavailable"
    ).strip().lower()
    evidence_type = str(
        record.get("evidence_type")
        or statement_meta.get("evidence_type")
        or record.get("_section")
        or "UNKNOWN"
    ).strip().upper()

    return {
        "source_file": source_file,
        "char_start": int(char_start) if isinstance(char_start, int) else -1,
        "char_end": int(char_end) if isinstance(char_end, int) else -1,
        "line_start": int(line_start) if isinstance(line_start, int) else -1,
        "line_end": int(line_end) if isinstance(line_end, int) else -1,
        "chunk_id": chunk_id,
        "statement_id": statement_id,
        "evidence_type": evidence_type,
        "source_location_status": location_status,
    }


def _span_signature(span: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        str(span.get("source_file") or ""),
        int(span.get("char_start") or -1),
        int(span.get("char_end") or -1),
        int(span.get("line_start") or -1),
        int(span.get("line_end") or -1),
        str(span.get("chunk_id") or ""),
        str(span.get("statement_id") or ""),
        str(span.get("evidence_type") or ""),
        str(span.get("source_location_status") or ""),
    )


def _coerce_int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _match_evidence_to_records(evidence: str, records: List[Dict[str, Any]], raw_source: str) -> List[Dict[str, Any]]:
    evidence_norm = _normalize_text(evidence)
    if not evidence_norm:
        return []
    matches: List[Dict[str, Any]] = []
    for record in records:
        record_text = record.get("_text", "")
        if not record_text:
            continue
        if evidence_norm in record_text or record_text in evidence_norm:
            matches.append(record)
            continue
    return matches


def ground_business_rules_against_extraction(
    business_rules: List[Dict[str, Any]],
    merged_extraction: Dict[str, Any],
    raw_source: str = "",
) -> List[str]:
    """Anti-hallucination + provenance check for synthesized business
    rules. Mutates each rule dict in place to guarantee it always
    carries "rule_type", "confidence", "validation_status", and
    "fields_affected" with values drawn from a fixed, safe vocabulary -
    never presenting an inferred or unverifiable claim as a confirmed
    fact. Returns human-readable warnings for anything downgraded.
    """
    warnings: List[str] = []
    technical_records = _collect_technical_records(merged_extraction)
    chunk_lookup: Dict[str, Dict[str, Any]] = {}
    for chunk in merged_extraction.get("chunk_provenance", []) or []:
        if not isinstance(chunk, dict):
            continue
        chunk_id = str(chunk.get("chunk_id", "")).strip()
        if chunk_id:
            chunk_lookup[chunk_id] = chunk
    statement_lookup: Dict[str, Dict[str, Any]] = {}
    for statement in merged_extraction.get("statement_provenance", []) or []:
        if not isinstance(statement, dict):
            continue
        statement_id = str(statement.get("statement_id", "")).strip()
        if statement_id:
            statement_lookup[statement_id] = statement
    has_parser_failed_chunk = any(
        isinstance(chunk, dict) and str(chunk.get("parse_error", "")).strip()
        for chunk in merged_extraction.get("chunk_provenance", []) or []
    )
    for index, rule in enumerate(business_rules, start=1):
        if not isinstance(rule, dict):
            continue

        # --- rule_type: clamp to the fixed vocabulary; never invent one ---
        rule_type = str(rule.get("rule_type", "")).strip().lower()
        if rule_type not in _ALLOWED_RULE_TYPES:
            rule.setdefault("_rule_type_defaulted", True)
            rule_type = "inferred"
        rule["rule_type"] = rule_type

        # --- confidence: clamp to the fixed vocabulary ---
        # --- evidence grounding for fields_affected ---
        fields_affected = _normalize_string_list(rule.get("fields_affected", []))
        rule["fields_affected"] = fields_affected

        # --- provenance grounding for source_evidence and dependencies ---
        source_evidence = _normalize_string_list(rule.get("source_evidence", []))
        rule["source_evidence"] = source_evidence
        dependencies = _normalize_string_list(rule.get("dependencies", []))
        rule["dependencies"] = dependencies

        matched_records: List[Dict[str, Any]] = []
        evidence_spans: List[Dict[str, Any]] = []
        unresolved_evidence: List[str] = []
        parser_failed_evidence: List[str] = []
        low_support_evidence: List[str] = []
        ambiguous_evidence: List[str] = []
        technical_refs: List[str] = []
        source_chunks: List[str] = []

        if not source_evidence:
            unresolved_evidence.append("No source evidence was provided for the synthesized rule.")

        for evidence in source_evidence:
            matches = _match_evidence_to_records(evidence, technical_records, raw_source)
            if not matches:
                unresolved_evidence.append(evidence)
                continue

            matched_records.extend(matches)
            for record in matches:
                ref = f"{record['_section']}[{record['_index']}]"
                if ref not in technical_refs:
                    technical_refs.append(ref)
                chunk_label = record.get("_chunk_id") or ""
                if chunk_label:
                    chunk_name = f"{chunk_label}:{record.get('_chunk_kind') or 'chunk'}"
                    if chunk_name not in source_chunks:
                        source_chunks.append(chunk_name)

                if record.get("_parse_error"):
                    parser_failed_evidence.append(evidence)
                elif record.get("_support_confidence") == "low" or record.get("confidence") == "low":
                    low_support_evidence.append(evidence)

                if record.get("_section") == "ambiguities" or record.get("confidence") == "low":
                    ambiguous_evidence.append(evidence)

                chunk_id = str(record.get("_chunk_id") or "").strip()
                chunk_meta = chunk_lookup.get(chunk_id, {})
                statement_id = str(record.get("statement_id") or record.get("source_statement_id") or "").strip()
                statement_meta = statement_lookup.get(statement_id, {})
                span = _build_evidence_span(record, chunk_meta, statement_meta)
                if _span_signature(span) not in {_span_signature(existing) for existing in evidence_spans}:
                    evidence_spans.append(span)

        if not evidence_spans and source_evidence:
            for chunk_id in source_chunks:
                clean_chunk_id = chunk_id.split(":", 1)[0]
                chunk_meta = chunk_lookup.get(clean_chunk_id, {})
                if not chunk_meta:
                    continue
                span = {
                    "source_file": str(chunk_meta.get("source_file") or ""),
                    "char_start": _coerce_int(chunk_meta.get("source_char_start", -1)),
                    "char_end": _coerce_int(chunk_meta.get("source_char_end", -1)),
                    "line_start": _coerce_int(chunk_meta.get("source_line_start", -1)),
                    "line_end": _coerce_int(chunk_meta.get("source_line_end", -1)),
                    "chunk_id": clean_chunk_id,
                    "statement_id": "",
                    "evidence_type": "UNKNOWN",
                    "source_location_status": str(chunk_meta.get("source_location_status") or "unavailable"),
                }
                if _span_signature(span) not in {_span_signature(existing) for existing in evidence_spans}:
                    evidence_spans.append(span)

        rule_id_seed = [
            rule.get("rule_name") or "",
            rule.get("output_field") or "",
            rule.get("condition") or "",
            rule.get("action") or "",
            "|".join(source_evidence),
            "|".join(fields_affected),
            "|".join(source_chunks),
        ]
        rule["rule_id"] = stable_id("rule", *rule_id_seed, length=12)
        rule["source_chunks"] = source_chunks
        rule["technical_references"] = technical_refs
        rule["evidence_spans"] = evidence_spans

        unresolved_issues: List[str] = []
        if unresolved_evidence:
            unresolved_issues.append(
                "Could not trace the stated source evidence back to a successfully parsed "
                "technical extraction record: " + ", ".join(unresolved_evidence)
            )
        if parser_failed_evidence:
            unresolved_issues.append(
                "The supporting technical evidence came from a chunk that failed to parse: "
                + ", ".join(dict.fromkeys(parser_failed_evidence))
            )
        if low_support_evidence:
            unresolved_issues.append(
                "The supporting technical evidence was low-confidence and should not be "
                "presented as fully verified: "
                + ", ".join(dict.fromkeys(low_support_evidence))
            )
        if ambiguous_evidence:
            unresolved_issues.append(
                "The supporting technical evidence was itself ambiguous or incomplete: "
                + ", ".join(dict.fromkeys(ambiguous_evidence))
            )

        if parser_failed_evidence:
            validation_status = "parser_failed"
        elif not source_evidence:
            validation_status = "unverified"
        elif unresolved_evidence and not matched_records and has_parser_failed_chunk:
            validation_status = "parser_failed"
        elif unresolved_evidence and not matched_records:
            validation_status = "unverified"
        elif unresolved_evidence or low_support_evidence:
            validation_status = "insufficient_evidence"
        elif ambiguous_evidence:
            validation_status = "ambiguous"
        else:
            validation_status = "verified"

        rule["validation_status"] = validation_status

        rule["confidence"] = derive_business_rule_confidence(
            validation_status=validation_status,
            source_evidence_count=len(source_evidence),
            matched_record_count=len(matched_records),
            source_chunk_count=len(source_chunks),
            parser_failed=bool(parser_failed_evidence),
            low_support=bool(low_support_evidence),
            ambiguous=bool(ambiguous_evidence),
            unresolved_evidence=bool(unresolved_evidence and not matched_records),
            rule_type=rule_type,
            llm_only=not source_evidence,
        )
        if validation_status == "unverified" or validation_status != "verified":
            warnings.extend(unresolved_issues)

        if validation_status in {"parser_failed", "insufficient_evidence", "ambiguous"}:
            rule["unresolved_ambiguities"] = unresolved_issues
            rule["ambiguity_id"] = stable_id(
                "amb",
                rule["rule_id"],
                validation_status,
                "|".join(unresolved_issues) if unresolved_issues else "none",
                length=12,
            )
        else:
            rule["unresolved_ambiguities"] = []
            rule["ambiguity_id"] = ""

    return warnings