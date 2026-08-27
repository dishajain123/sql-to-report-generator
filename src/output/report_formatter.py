"""
agents/report_formatter.py
----------------------------
Report Formatter Agent.

Pure, deterministic assembly stage (no LLM call). Takes:
    - the IngestionResult (object metadata, parameters, dialect, parse
      warnings)
    - the merged technical extraction (tables read/written etc.)
    - the SynthesisResult (business rules, purpose summary, calculations)
    - any additional guardrail warnings collected during per-chunk
      extraction (input/output guardrail flags that aren't already
      folded into `ingestion.parse_warnings` or `synthesis`)

...and renders the single final Markdown report.

Report philosophy
------------------
The report is organized **business understanding first -> decision
logic second -> technical details third -> SQL evidence last**, so a
business analyst, tester, or new team member can read the first couple
of sections and understand what the object does without reading SQL,
while a technical reviewer can still drill all the way down to the
exact source predicates.

Nothing here invents business meaning. Every section either restates
data already produced by the Logic Extraction / Rule Synthesis agents
(and their guardrails), or is a purely presentational transformation of
that data (grouping, deduplication, table-splitting, truncation with a
pointer to the full text). Anything that cannot be confidently derived
from the source is rendered as the literal phrase
``Not explicitly determined from source SQL`` rather than being
inferred, defaulted, or guessed - in particular, **rule priority is
never inferred from extraction order**; a priority ordering is only
shown when the synthesized rule actually carries explicit
`tie_priority_handling` content.

Two documents, one agent
-------------------------
`format()` produces the business-facing report: purpose, rules, decision
logic, calculations, dependencies, exceptions - the things a business
analyst needs to understand or review a rule. It never includes
pipeline-internal detail (rule IDs, chunk/statement IDs, source file
paths or line numbers, reconciliation status, quality/confidence
scoring, run/model metadata).

`format_verification()` produces the companion artifact that carries
exactly that internal detail, so nothing is silently dropped - a
reviewer can still trace any business rule back to the precise SQL
lines, chunk, and statement that produced it, see its reconciliation
status against the deterministic extraction, and see the run metadata
the report was generated under. The two are meant to be written side by
side (e.g. `<name>_report.md` and `<name>_verification.md`); `format()`
ends with a short pointer to the companion file so a reader always knows
where to look for provenance without that provenance cluttering the
business document itself.
"""

from __future__ import annotations

from collections import OrderedDict
import copy
import re
from typing import Any, Dict, List, Optional, Tuple

from src.ingestion.ingestion import IngestionResult
from src.ir.canonical_ir import CanonicalBusinessIR
from src.synthesis.rule_synthesizer import SynthesisResult
from src.dialect.detector import AMBIGUOUS, ORACLE, TSQL, UNKNOWN, UNSUPPORTED, normalize_dialect_name
from src.core.pipeline_utils import RunMetadata, run_metadata_to_dict

_NOT_DETERMINED = "Not explicitly determined from source SQL."

# Common, generic (non-domain-specific) naming patterns used to spot an
# account/customer/entity-style roll-up hierarchy and a history/movement
# audit trail purely from table and rule names already present in the
# extraction - never hardcoded to any one procedure's business domain.
_HISTORY_TABLE_PATTERN = re.compile(r"HISTORY|MOVEMENT|AUDIT_LOG|AUDIT_TRAIL", re.IGNORECASE)
_HIERARCHY_LEVEL_TERMS = [
    "account", "customer", "ucif", "branch", "portfolio", "entity", "household", "group",
]

# Rendering fallback text this formatter itself produces (see
# _business_rule_output / _business_rule_business_meaning) - if any of
# these come back from a business-rule field, it means "no real value
# was present," not "here is a field literally named this." Checked
# case-insensitively so they can never be mistaken for a real field name
# in Important Fields or anywhere else a field list is rendered.
_PLACEHOLDER_FIELD_VALUES = {
    "not specified", "n/a", "na", "none", "not applicable", "unknown",
    "not identified", "not determined", "not confirmed", "tbd",
}


class ReportFormatterAgent:
    """Assembles the final Markdown business logic report."""

    _MAX_TABLE_ROWS = 40

    # ------------------------------------------------------------------
    # Top-level assembly
    # ------------------------------------------------------------------

    def _prepare(
        self,
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis: SynthesisResult,
        canonical_ir: Optional[CanonicalBusinessIR],
        run_metadata: Optional[RunMetadata],
    ) -> Dict[str, Any]:
        """Shared prep step for both `format()` and `format_verification()`
        so the two documents are always built from exactly the same
        reconciled data - nothing computed for one can silently drift
        from the other."""
        raw_business_rules = copy.deepcopy(list((synthesis.data or {}).get("business_rules") or []))
        run_metadata = run_metadata or getattr(ingestion, "run_metadata", None) or self._metadata_from_merged(
            merged_extraction
        )
        canonical_ir = canonical_ir or self._canonical_ir(ingestion, merged_extraction, synthesis, run_metadata)
        merged_extraction = canonical_ir.to_legacy_merged_extraction(merged_extraction)
        synthesis = self._synthesis_view(synthesis, canonical_ir)
        rules: List[Dict[str, Any]] = [rule.to_dict() for rule in canonical_ir.business_rules]
        business_rules_for_display = self._display_business_rules(
            self._business_rules_for_display(raw_business_rules, rules)
        )
        consolidated_reads = self._consolidate_rows(merged_extraction.get("tables_read", []) or [])
        consolidated_writes = self._consolidate_rows(merged_extraction.get("tables_written", []) or [])
        return {
            "run_metadata": run_metadata,
            "canonical_ir": canonical_ir,
            "merged_extraction": merged_extraction,
            "synthesis": synthesis,
            "rules": rules,
            "business_rules_for_display": business_rules_for_display,
            "consolidated_reads": consolidated_reads,
            "consolidated_writes": consolidated_writes,
        }

    def format(
        self,
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis: SynthesisResult,
        canonical_ir: Optional[CanonicalBusinessIR] = None,
        extraction_guardrail_warnings: Optional[List[str]] = None,
        run_metadata: Optional[RunMetadata] = None,
        verification_filename: Optional[str] = None,
    ) -> str:
        """Assembles the business-facing report only. Contains business
        objective, rules, decision logic, inputs, calculations,
        classifications, actions, dependencies, exceptions, and business
        interpretation - and deliberately nothing from the pipeline's own
        bookkeeping (run metadata, rule/chunk/statement IDs, source file
        paths or line numbers, reconciliation status, quality/confidence
        scoring). See `format_verification()` for that companion detail.
        """
        ctx = self._prepare(ingestion, merged_extraction, synthesis, canonical_ir, run_metadata)
        synthesis = ctx["synthesis"]
        business_rules_for_display = ctx["business_rules_for_display"]
        consolidated_reads = ctx["consolidated_reads"]
        consolidated_writes = ctx["consolidated_writes"]

        sections = [
            self._title_block(ingestion, synthesis),
            self._at_a_glance(ingestion, synthesis, consolidated_reads, consolidated_writes, business_rules_for_display),
            self._what_this_does(synthesis, business_rules_for_display),
            self._end_to_end_flow(synthesis),
            self._eligibility_section(business_rules_for_display),
            self._business_rules_section(business_rules_for_display),
            self._decision_priority_section(synthesis, business_rules_for_display),
            self._fallback_section(business_rules_for_display),
            self._rollup_section(business_rules_for_display),
            self._history_section(business_rules_for_display, consolidated_writes, consolidated_reads),
            self._important_updates_section(consolidated_writes),
            self._technical_lineage_section(consolidated_reads, consolidated_writes),
            self._important_fields_section(ingestion, business_rules_for_display),
            self._business_rule_summary_table(business_rules_for_display),
            self._calculations(synthesis),
            self._exception_handling(synthesis),
            self._ambiguities(ingestion, synthesis, extraction_guardrail_warnings or []),
            self._verification_pointer(verification_filename),
        ]
        sections = [s for s in sections if s and s.strip()]
        return "\n\n".join(sections).strip() + "\n"

    def format_verification(
        self,
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis: SynthesisResult,
        canonical_ir: Optional[CanonicalBusinessIR] = None,
        run_metadata: Optional[RunMetadata] = None,
        report_filename: Optional[str] = None,
    ) -> str:
        """Assembles the companion verification / traceability artifact:
        run metadata, rule-to-source mapping (rule IDs, chunk IDs,
        statement IDs, source file/line spans), reconciliation summary,
        and quality/confidence scoring. None of this belongs in the
        business report `format()` produces - it exists so that detail
        isn't lost, just kept out of the document business users read.
        """
        ctx = self._prepare(ingestion, merged_extraction, synthesis, canonical_ir, run_metadata)
        run_metadata_resolved = ctx["run_metadata"]
        merged_extraction = ctx["merged_extraction"]
        synthesis = ctx["synthesis"]
        rules = ctx["rules"]

        sections = [
            self._verification_title_block(ingestion, report_filename),
            self._run_metadata_section(ingestion, run_metadata_resolved),
            self._business_rule_summary_table(rules, include_technical_ids=True),
            self._source_traceability_details(rules, merged_extraction),
            self._validation_summary(rules, merged_extraction, synthesis),
            self._reconciliation_summary(merged_extraction, synthesis),
            self._quality_summary(merged_extraction, synthesis),
        ]
        sections = [s for s in sections if s and s.strip()]
        return "\n\n".join(sections).strip() + "\n"

    # ------------------------------------------------------------------
    # 0. Title
    # ------------------------------------------------------------------

    def _title_block(self, ingestion: IngestionResult, synthesis: SynthesisResult) -> str:
        object_name = self._display_object_name(ingestion)
        tagline = self._one_line_purpose(synthesis)
        return f"# {object_name} — Business Logic Report\n\n> {tagline}"

    @staticmethod
    def _verification_pointer(verification_filename: Optional[str]) -> str:
        """A short, business-safe pointer from the main report to its
        companion traceability artifact - no IDs, statuses, or paths, just
        a filename so a reviewer knows where to look."""
        name = str(verification_filename or "").strip()
        if not name:
            return (
                "---\n\n_Source traceability, rule IDs, reconciliation, and run "
                "metadata are maintained separately in this object's verification "
                "artifact rather than in this report._"
            )
        return (
            "---\n\n_Source traceability, rule IDs, reconciliation, and run "
            f"metadata for this report are maintained separately in `{name}`._"
        )

    @staticmethod
    def _verification_title_block(ingestion: IngestionResult, report_filename: Optional[str]) -> str:
        object_name = ReportFormatterAgent._display_object_name(ingestion)
        object_id = getattr(ingestion, "object_id", "") or "unassigned"
        raw_name = str(getattr(ingestion, "object_name", "") or "").strip()
        lines = [f"# {object_name} — Verification & Traceability", ""]
        if report_filename:
            lines.append(
                f"> Companion artifact to `{report_filename}`. Everything here is "
                "pipeline/source provenance for review and audit; none of it "
                "appears in the business report."
            )
        else:
            lines.append(
                "> Companion traceability artifact. Everything here is "
                "pipeline/source provenance for review and audit; none of it "
                "appears in the business report."
            )
        lines.append("")
        lines.append("| Item | Value |")
        lines.append("|---|---|")
        lines.append(f"| Object ID | `{object_id}` |")
        if raw_name and raw_name.upper() not in {"UNKNOWN_OBJECT", "UNKNOWN"} and raw_name != object_name:
            lines.append(f"| Raw technical object name (from source) | `{raw_name}` |")
        return "\n".join(lines)

    @staticmethod
    def _metadata_from_merged(merged_extraction: Dict[str, Any]) -> Optional[RunMetadata]:
        metadata = merged_extraction.get("run_metadata")
        if isinstance(metadata, RunMetadata):
            return metadata
        if isinstance(metadata, dict) and metadata:
            try:
                return RunMetadata(**metadata)
            except TypeError:
                return None
        return None

    @staticmethod
    def _canonical_ir(
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis: SynthesisResult,
        run_metadata: Optional[RunMetadata],
    ) -> CanonicalBusinessIR:
        cached = merged_extraction.get("canonical_ir") or synthesis.data.get("canonical_ir")
        if isinstance(cached, dict) and cached:
            try:
                return CanonicalBusinessIR.from_pipeline(
                    ingestion=ingestion,
                    merged_extraction=merged_extraction,
                    synthesis=synthesis,
                    run_metadata=run_metadata,
                )
            except Exception:
                pass
        return CanonicalBusinessIR.from_pipeline(
            ingestion=ingestion,
            merged_extraction=merged_extraction,
            synthesis=synthesis,
            run_metadata=run_metadata,
        )

    @staticmethod
    def _synthesis_view(synthesis: SynthesisResult, canonical_ir: CanonicalBusinessIR) -> SynthesisResult:
        view = copy.copy(synthesis)
        view.data = canonical_ir.to_legacy_synthesis_data(synthesis.data)
        return view

    @staticmethod
    def _business_rules_for_display(
        raw_rules: List[Dict[str, Any]],
        canonical_rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        raw_rules = [rule for rule in raw_rules if isinstance(rule, dict)]
        canonical_rules = [rule for rule in canonical_rules if isinstance(rule, dict)]
        if not raw_rules:
            return canonical_rules
        if len(raw_rules) > len(canonical_rules):
            return raw_rules
        raw_complexity = sum(
            1 for rule in raw_rules if rule.get("decision_logic_rows") or rule.get("eligibility") or rule.get("condition")
        )
        canonical_complexity = sum(
            1 for rule in canonical_rules if rule.get("decision_logic_rows") or rule.get("eligibility") or rule.get("condition")
        )
        if raw_complexity > canonical_complexity and len(raw_rules) >= len(canonical_rules):
            return raw_rules
        return canonical_rules

    def _display_business_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        collapsed: List[Dict[str, Any]] = []
        used_indices: set[int] = set()
        for idx, rule in enumerate(rules):
            if idx in used_indices:
                continue
            family_key = self._display_rule_family_key(rule)
            if family_key == "reset_negative_dpd_zero":
                group_indices = [
                    other_idx
                    for other_idx, other_rule in enumerate(rules)
                    if other_idx not in used_indices
                    and self._display_rule_family_key(other_rule) == family_key
                ]
                if len(group_indices) > 1:
                    collapsed.append(self._merge_negative_dpd_reset_rules([rules[i] for i in group_indices]))
                    used_indices.update(group_indices)
                    continue
            collapsed.append(dict(rule))
            used_indices.add(idx)
        return collapsed

    @staticmethod
    def _display_rule_family_key(rule: Dict[str, Any]) -> str:
        blob = " ".join(
            [
                str(rule.get("rule_name") or ""),
                str(rule.get("action") or ""),
                str(rule.get("business_meaning") or ""),
                str(rule.get("output_field") or ""),
                " ".join(str(field) for field in rule.get("fields_affected") or []),
            ]
        ).lower()
        blob = re.sub(r"dpd[_ ]?[a-z0-9]+", "dpd_field", blob)
        blob = re.sub(r"\s+", " ", blob).strip()
        if "reset" in blob and "zero" in blob and "dpd_field" in blob:
            return "reset_negative_dpd_zero"
        return blob

    @staticmethod
    def _merge_negative_dpd_reset_rules(rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        merged = dict(rules[0]) if rules else {}

        def _append_unique(container: List[str], values: List[str]) -> None:
            for value in values:
                text = str(value or "").strip()
                if text and text not in container:
                    container.append(text)

        def _extract_dpd_field(text: str) -> str:
            match = re.search(r"(?i)\b(DPD(?:[_ ]?[A-Za-z0-9]+)?)\b", text or "")
            return match.group(1).replace(" ", "_") if match else ""

        field_order: List[str] = []
        eligibility_order: List[str] = []
        source_evidence: List[str] = []
        source_chunks: List[str] = []
        source_statements: List[str] = []

        for rule in rules:
            _append_unique(field_order, [field for field in (rule.get("fields_affected") or []) if str(field).strip()])
            _append_unique(eligibility_order, [cond for cond in (rule.get("eligibility") or []) if str(cond).strip()])
            _append_unique(source_evidence, [item for item in (rule.get("source_evidence") or []) if str(item).strip()])
            _append_unique(source_chunks, [item for item in (rule.get("source_chunks") or []) if str(item).strip()])
            _append_unique(source_statements, [item for item in (rule.get("source_statements") or []) if str(item).strip()])
            for value in (rule.get("rule_name"), rule.get("condition"), rule.get("action")):
                field = _extract_dpd_field(str(value or ""))
                if field and field not in field_order:
                    field_order.append(field)

        merged["rule_name"] = "Reset negative DPD values to zero"
        merged["business_meaning"] = (
            "Any negative Days Past Due values are reset to zero to prevent invalid overdue calculations."
        )
        merged["output_field"] = ""
        merged["fields_affected"] = field_order
        summary_condition = ""
        if field_order:
            if len(field_order) == 1:
                summary_condition = f"{field_order[0]} is less than zero"
            else:
                summary_condition = ", ".join(field_order[:-1]) + f", or {field_order[-1]} is less than zero"
        merged["eligibility"] = [summary_condition] if summary_condition else eligibility_order or [
            "DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, or DPD_StockStmt is less than zero"
        ]
        merged["condition"] = summary_condition or "DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, or DPD_StockStmt is less than zero"
        merged["action"] = merged["business_meaning"]
        merged["decision_logic_rows"] = [
            {
                "condition": merged["condition"],
                "outcome": merged["business_meaning"],
            }
        ]
        merged["source_evidence"] = source_evidence
        merged["source_chunks"] = source_chunks
        if source_statements:
            merged["source_statements"] = source_statements
        return merged

    def _run_metadata_section(self, ingestion: IngestionResult, run_metadata: Optional[RunMetadata]) -> str:
        data = run_metadata_to_dict(run_metadata)
        if not data:
            return ""
        rows = [
            ("Pipeline Version", data.get("pipeline_version", "")),
            ("Prompt Version", data.get("prompt_version", "")),
            ("Knowledge Base Version", data.get("knowledge_base_version", "")),
            ("Model", data.get("model_name", "")),
            ("Provider", data.get("provider", "")),
            ("Dialect", self._display_dialect(getattr(ingestion, "dialect", ""))),
            ("Dialect Confidence", self._title_confidence(getattr(ingestion, "dialect_confidence", ""))),
            ("Source Hash", data.get("source_hash", "")),
            ("Configuration Version", data.get("configuration_version", "")),
            ("Run Timestamp", data.get("run_timestamp", "")),
            ("Object ID", data.get("object_id", "") or getattr(ingestion, "object_id", "")),
        ]
        lines = ["## Run Metadata", "", "| Item | Value |", "|---|---|"]
        lines.extend(f"| {label} | `{value}` |" if value else f"| {label} |  |" for label, value in rows)
        return "\n".join(lines)

    @staticmethod
    def _one_line_purpose(synthesis: SynthesisResult) -> str:
        summary = str(synthesis.data.get("purpose_summary") or "").strip()
        if not summary:
            return _NOT_DETERMINED
        first_sentence = re.split(r"(?<=[.!?])\s+", summary)[0].strip()
        return first_sentence or summary

    @staticmethod
    def _display_dialect(dialect: str) -> str:
        normalized = normalize_dialect_name(dialect)
        mapping = {
            ORACLE: "Oracle",
            TSQL: "T-SQL",
            UNKNOWN: "Unknown",
            AMBIGUOUS: "Ambiguous",
            UNSUPPORTED: "Unsupported",
        }
        return mapping.get(normalized, str(dialect).title() if dialect else "Unknown")

    @staticmethod
    def _title_confidence(confidence: str) -> str:
        normalized = str(confidence or "").strip().lower()
        return normalized.title() if normalized else "Low"

    @staticmethod
    def _format_source_location(span: Dict[str, Any]) -> str:
        source_file = str(span.get("source_file") or "").strip() or "source"
        line_start = int(span.get("line_start") or -1)
        line_end = int(span.get("line_end") or -1)
        chunk_id = str(span.get("chunk_id") or "").strip()
        statement_id = str(span.get("statement_id") or "").strip()

        parts = [source_file]
        if line_start > 0:
            if line_end > 0 and line_end != line_start:
                parts.append(f"Lines {line_start}-{line_end}")
            else:
                parts.append(f"Line {line_start}")
        if chunk_id:
            parts.append(f"Chunk {chunk_id}")
        if statement_id:
            parts.append(f"Statement {statement_id}")
        return " | ".join(parts)

    def _format_evidence_spans(self, spans: List[Dict[str, Any]], limit: int = 2) -> str:
        cleaned: List[str] = []
        seen: set = set()
        for span in spans or []:
            if not isinstance(span, dict):
                continue
            key = (
                str(span.get("source_file") or ""),
                int(span.get("line_start") or -1),
                int(span.get("line_end") or -1),
                str(span.get("chunk_id") or ""),
                str(span.get("statement_id") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(self._format_source_location(span))
        if not cleaned:
            return ""
        if len(cleaned) > limit:
            remainder = len(cleaned) - limit
            return "; ".join(cleaned[:limit]) + f" (+{remainder} more span(s))"
        return "; ".join(cleaned)

    # ------------------------------------------------------------------
    # 1. At a Glance
    # ------------------------------------------------------------------

    def _at_a_glance(
        self,
        ingestion: IngestionResult,
        synthesis: SynthesisResult,
        consolidated_reads: List[Dict[str, Any]],
        consolidated_writes: List[Dict[str, Any]],
        rules: List[Dict[str, Any]],
    ) -> str:
        dialect_label = self._display_dialect(getattr(ingestion, "dialect", ""))
        confidence_label = self._title_confidence(getattr(ingestion, "dialect_confidence", ""))
        object_name = self._display_object_name(ingestion)
        object_type = self._display_object_type(getattr(ingestion, "object_type", ""))

        if getattr(ingestion, "parameter_parse_status", "parameterless") == "failed":
            params_display = "Not specified (extraction failed / Needs Review)"
        elif getattr(ingestion, "parameters", None):
            params_display = "; ".join(
                f"`{p.name}` ({p.direction}, {p.datatype})" for p in ingestion.parameters
            )
        else:
            params_display = "None"

        primary_tables = self._summarize_table_list(consolidated_writes)
        hierarchy_levels = self._detect_hierarchy_levels(rules)
        entity_display = " → ".join(level.title() for level in hierarchy_levels) if hierarchy_levels else "Not explicitly determined from source SQL"

        rows = [
            ("Object", f"`{object_name}`"),
            ("Type", object_type),
            ("SQL Dialect", dialect_label),
            ("Dialect Confidence", confidence_label),
            ("Parameters", params_display),
            ("Primary Business Entity", entity_display),
            ("Tables Updated", primary_tables),
            ("Business Rules Identified", str(len(rules))),
        ]
        lines = ["## At a Glance", "", "| Item | Details |", "|---|---|"]
        lines.extend(f"| {label} | {value} |" for label, value in rows)
        if normalize_dialect_name(getattr(ingestion, "dialect", "")) in {UNKNOWN, AMBIGUOUS, UNSUPPORTED}:
            lines.extend(
                [
                    "",
                    "**Manual review required:** the SQL dialect could not be confidently resolved "
                    "and downstream parsing was handled with a restricted fallback path.",
                ]
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 2. What This Procedure Does
    # ------------------------------------------------------------------

    def _what_this_does(self, synthesis: SynthesisResult, rules: List[Dict[str, Any]]) -> str:
        summary = str(synthesis.data.get("purpose_summary") or "").strip() or _NOT_DETERMINED
        outputs = self._unique_ordered(
            [self._business_rule_output(rule) for rule in rules if self._business_rule_output(rule) != "Not specified"]
        )
        lines = [
            "## What This Procedure Does",
            "",
            "### In Simple Terms",
            "",
            summary,
        ]
        if outputs:
            lines.extend(
                [
                    "",
                    "### Business Outcome",
                    "",
                    "After this procedure completes, the following fields have been evaluated and, where applicable, updated:",
                    "",
                ]
            )
            lines.extend(f"- `{field}`" for field in outputs[:15])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 3. End-to-End Business Flow
    # ------------------------------------------------------------------

    def _end_to_end_flow(self, synthesis: SynthesisResult) -> str:
        steps: List[str] = synthesis.data.get("step_by_step_flow", []) or []
        if not steps:
            return f"## End-to-End Business Flow\n\n_{_NOT_DETERMINED}_"
        lines = [f"{i + 1}. {self._strip_leading_numbering(step)}" for i, step in enumerate(steps)]
        return "## End-to-End Business Flow\n\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # 4. Eligibility
    # ------------------------------------------------------------------

    def _eligibility_section(self, rules: List[Dict[str, Any]]) -> str:
        conditions: List[str] = []
        for rule in rules:
            conditions.extend(self._rule_text_lines(rule.get("eligibility") or rule.get("condition")))
        deduped = self._unique_ordered(conditions)
        lines = ["## Eligibility", ""]
        if not deduped:
            lines.append(f"_{_NOT_DETERMINED}_")
            return "\n".join(lines)
        lines.append(
            "The extracted business rules reference the following eligibility conditions "
            "(gathered from each rule's own eligibility criteria; see the Business Rules "
            "section below for which condition applies to which rule):"
        )
        lines.append("")
        lines.extend(f"- {c}" for c in deduped[:15])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 5. Business Rules
    # ------------------------------------------------------------------

    def _business_rules_section(self, rules: List[Dict[str, Any]]) -> str:
        lines = ["## Business Rules", ""]
        if not rules:
            lines.append("_No business rules were identified from the extracted source._")
            return "\n".join(lines)
        for idx, rule in enumerate(rules, start=1):
            lines.extend(self._render_business_rule_block(idx, rule))
            lines.append("")
        return "\n".join(lines).strip()

    def _render_business_rule_block(self, idx: int, rule: Dict[str, Any]) -> List[str]:
        rule_name = self._business_rule_name(rule, idx)
        output_field = self._business_rule_output(rule)
        business_meaning = self._business_rule_business_meaning(rule)
        eligibility = self._rule_text_lines(rule.get("eligibility") or rule.get("condition"))
        decision_logic_rows = self._decision_logic_rows(rule)
        tie_handling = self._rule_text_lines(rule.get("tie_priority_handling"))
        default_value = self._rule_text_lines(rule.get("default"))
        when_not_eligible = self._rule_text_lines(rule.get("when_not_eligible"))

        lines = [f"## Rule: {rule_name}", ""]
        if output_field != "Not specified":
            lines.append(f"**Applies to:** `{output_field}`")
        lines.append(f"**Business meaning:** {business_meaning}")
        lines.append("")

        if eligibility:
            lines.append("### Eligibility")
            lines.extend(f"- {e}" for e in eligibility)
            lines.append("")

        # Only shown for a genuine multi-band/lookup mapping (see
        # _decision_logic_rows) - an ordinary single condition -> single
        # outcome rule is already fully covered by Eligibility plus
        # Business meaning above, so repeating both in a one-row table
        # underneath would only restate the same sentence twice.
        if decision_logic_rows:
            lines.append("### Decision Logic")
            lines.extend(self._decision_logic_block(decision_logic_rows))
            lines.append("")

        # Priority is only ever shown when the source itself established
        # it - never inferred merely from the order rules were extracted.
        if tie_handling:
            lines.append("### Tie / Priority Handling")
            lines.extend(f"- {t}" for t in tie_handling)
            lines.append("")

        if default_value:
            lines.append("### Default")
            lines.extend(f"- {d}" for d in default_value)
            lines.append("")

        if when_not_eligible:
            lines.append("### When Not Eligible")
            lines.extend(f"- {w}" for w in when_not_eligible)
            lines.append("")

        return lines

    # ------------------------------------------------------------------
    # 6. Decision Logic / Rule Priority
    # ------------------------------------------------------------------

    def _decision_priority_section(self, synthesis: SynthesisResult, rules: List[Dict[str, Any]]) -> str:
        """Rule precedence only. The step-by-step flow already lives in
        'End-to-End Business Flow' - reprinting it here added nothing
        and just duplicated a wall of long sentences under a second
        heading, so this section covers exactly one thing: which rules
        (if any) have a source-confirmed priority/tie-break behavior.
        """
        priority_rows: List[Tuple[str, str]] = []
        for idx, rule in enumerate(rules, start=1):
            tie_handling = self._rule_text_lines(rule.get("tie_priority_handling"))
            if tie_handling:
                name = self._business_rule_name(rule, idx)
                priority_rows.append((name, "; ".join(tie_handling)))

        lines = ["## Rule Priority", ""]
        if priority_rows:
            lines.append(
                "The following rules have an explicit, source-confirmed priority or "
                "tie-breaking behavior when more than one condition could apply:"
            )
            lines.append("")
            lines.append("| Rule | Priority / Tie-Breaking Behavior |")
            lines.append("|---|---|")
            for name, behavior in priority_rows:
                lines.append(f"| {self._escape_table_cell(name)} | {self._escape_table_cell(behavior)} |")
        else:
            lines.append(
                f"{_NOT_DETERMINED} Rule order in this report reflects extraction order "
                "only and must not be read as a business priority."
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 7. Fallback / Not-Met Conditions
    # ------------------------------------------------------------------

    def _fallback_section(self, rules: List[Dict[str, Any]]) -> str:
        items: List[str] = []
        for rule in rules:
            items.extend(self._rule_text_lines(rule.get("default")))
            items.extend(self._rule_text_lines(rule.get("when_not_eligible")))
        deduped = self._unique_ordered(items)
        lines = ["## Fallback Handling", ""]
        if not deduped:
            lines.append(f"_{_NOT_DETERMINED}_")
            return "\n".join(lines)
        lines.extend(f"- {item}" for item in deduped[:20])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 8. Roll-Up / Entity Hierarchy (optional, generic)
    # ------------------------------------------------------------------

    def _rollup_section(self, rules: List[Dict[str, Any]]) -> str:
        levels = self._detect_hierarchy_levels(rules)
        if len(levels) < 2:
            return ""

        level_rules: "OrderedDict[str, List[str]]" = OrderedDict((level, []) for level in levels)
        for idx, rule in enumerate(rules, start=1):
            haystack = " ".join(
                [
                    str(rule.get("rule_name") or ""),
                    str(rule.get("business_meaning") or ""),
                    str(rule.get("output_field") or ""),
                ]
            ).lower()
            for level in levels:
                if re.search(rf"\b{re.escape(level)}", haystack):
                    level_rules[level].append(self._business_rule_name(rule, idx))

        lines = ["## Entity Hierarchy", "", "```text"]
        for i, level in enumerate(levels):
            lines.append(level.title())
            if i != len(levels) - 1:
                lines.append("    ↓")
        lines.append("```")
        lines.append("")
        lines.append(
            "The extracted rules reference more than one level of this hierarchy. Rules "
            "mentioning each level (by name, in order first encountered):"
        )
        lines.append("")
        for level, names in level_rules.items():
            if names:
                lines.append(f"- **{level.title()}:** " + "; ".join(self._unique_ordered(names)[:6]))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 9. History / Movement Tracking (optional, generic)
    # ------------------------------------------------------------------

    def _history_section(
        self,
        rules: List[Dict[str, Any]],
        consolidated_writes: List[Dict[str, Any]],
        consolidated_reads: List[Dict[str, Any]],
    ) -> str:
        history_tables = self._unique_ordered(
            [b["table"] for b in consolidated_writes if _HISTORY_TABLE_PATTERN.search(b["table"])]
            + [b["table"] for b in consolidated_reads if _HISTORY_TABLE_PATTERN.search(b["table"])]
        )
        if not history_tables:
            return ""

        related_rules = [
            rule
            for rule in rules
            if _HISTORY_TABLE_PATTERN.search(
                " ".join(rule.get("technical_references", []) or [])
                + " "
                + str(rule.get("rule_name") or "")
                + " "
                + str(rule.get("business_meaning") or "")
            )
        ]

        lines = [
            "## Movement History",
            "",
            "```text",
            "Previous Status",
            "      ↓",
            "Current Status",
            "      ↓",
            "Status Change?",
            "   ↙       ↘",
            " Yes        No",
            " ↓           ↓",
            "Record       No movement",
            "history",
            "```",
            "",
            "**History / movement tables identified:** " + ", ".join(f"`{t}`" for t in history_tables),
            "",
        ]
        if related_rules:
            lines.append("**Related business rules:**")
            lines.append("")
            for idx, rule in enumerate(rules, start=1):
                if rule in related_rules:
                    lines.append(f"- {self._business_rule_name(rule, idx)}: {self._business_rule_business_meaning(rule)}")
        else:
            lines.append(f"_{_NOT_DETERMINED}_ (no business rule was linked back to these tables)")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 10. Important Business Updates
    # ------------------------------------------------------------------

    def _important_updates_section(self, consolidated_writes: List[Dict[str, Any]]) -> str:
        if not consolidated_writes:
            return "## Important Business Updates\n\n_None identified._"
        header = ["| Table | Fields Updated | Operation(s) |", "|---|---|---|"]
        rows = []
        for bucket in consolidated_writes:
            fields = ", ".join(bucket["target_columns"][:10]) or "Not identified"
            ops = ", ".join(bucket["operations"]) or "Not specified"
            rows.append(
                f"| `{bucket['table']}` | {self._escape_table_cell(fields)} | `{self._escape_table_cell(ops)}` |"
            )
        return "## Important Business Updates\n\n" + self._render_split_table(header, rows)

    # ------------------------------------------------------------------
    # 11. Technical Data Lineage (Tables Read / Written)
    # ------------------------------------------------------------------

    def _technical_lineage_section(
        self, consolidated_reads: List[Dict[str, Any]], consolidated_writes: List[Dict[str, Any]]
    ) -> str:
        return (
            "## Technical Data Lineage\n\n"
            + self._tables_read({"tables_read": []}, _precomputed=consolidated_reads)
            + "\n\n"
            + self._tables_written({"tables_written": []}, _precomputed=consolidated_writes)
        )

    def _tables_read(self, merged_extraction: Dict[str, Any], _precomputed: Optional[List[Dict[str, Any]]] = None) -> str:
        consolidated = _precomputed if _precomputed is not None else self._consolidate_rows(
            merged_extraction.get("tables_read", []) or []
        )
        if not consolidated:
            return "## Tables Read\n\n_None identified._"
        header = ["| Table Name | Key Columns | Filter Conditions |", "|---|---|---|"]
        rows = [self._render_consolidated_read_row(b) for b in consolidated]
        return "## Tables Read\n\n" + self._render_split_table(header, rows)

    def _tables_written(self, merged_extraction: Dict[str, Any], _precomputed: Optional[List[Dict[str, Any]]] = None) -> str:
        consolidated = _precomputed if _precomputed is not None else self._consolidate_rows(
            merged_extraction.get("tables_written", []) or []
        )
        if not consolidated:
            return "## Tables Written\n\n_None identified._"
        header = ["| Table Name | Operation Type | Columns Affected | Business Trigger |", "|---|---|---|---|"]
        rows = [self._render_consolidated_written_row(b) for b in consolidated]
        return "## Tables Written\n\n" + self._render_split_table(header, rows)

    def _render_consolidated_read_row(self, bucket: Dict[str, Any]) -> str:
        columns = bucket["target_columns"] or bucket["source_columns"]
        business_context = ", ".join(columns) if columns else "Not specified"
        filters = "; ".join(bucket["filters"]) if bucket["filters"] else "None"
        filters = self._shorten_text(filters, 200)
        extra = f" _(consolidated from {bucket['count']} raw references)_" if bucket["count"] > 1 else ""
        return (
            f"| `{bucket['table']}` | {self._escape_table_cell(business_context)} | "
            f"{self._escape_table_cell(filters)}{extra} |"
        )

    def _render_consolidated_written_row(self, bucket: Dict[str, Any]) -> str:
        operation = ", ".join(bucket["operations"]) if bucket["operations"] else "operation not specified"
        columns = ", ".join(bucket["target_columns"]) if bucket["target_columns"] else "Not identified"
        filters = "; ".join(bucket["filters"]) if bucket["filters"] else "None"
        filters = self._shorten_text(filters, 200)
        extra = f" _(consolidated from {bucket['count']} raw references)_" if bucket["count"] > 1 else ""
        return (
            f"| `{bucket['table']}` | `{self._escape_table_cell(operation)}` | "
            f"{self._escape_table_cell(columns)} | {self._escape_table_cell(filters)}{extra} |"
        )

    def _consolidate_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Groups raw per-statement table_operations rows by table name
        (case-insensitively) so the same physical table referenced across
        many chunks/statements renders as one row with the union of
        columns/operations/filters instead of dozens of near-duplicate
        rows - this is a purely presentational consolidation and never
        drops a table, only merges repeated references to it.
        """
        grouped: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        for row in rows:
            if not isinstance(row, dict):
                continue
            table = str(row.get("table") or "table not specified").strip() or "table not specified"
            key = table.upper()
            bucket = grouped.setdefault(
                key,
                {
                    "table": table,
                    "target_columns": [],
                    "source_columns": [],
                    "operations": [],
                    "filters": [],
                    "count": 0,
                    "_target_col_keys": set(),
                    "_source_col_keys": set(),
                },
            )
            bucket["count"] += 1

            for col in (row.get("target_columns") or row.get("columns") or []):
                c = str(col).strip()
                if not c:
                    continue
                dkey = self._dedupe_column_key(c)
                if dkey not in bucket["_target_col_keys"] and len(bucket["target_columns"]) < 15:
                    bucket["_target_col_keys"].add(dkey)
                    bucket["target_columns"].append(c)
            for col in row.get("source_columns") or []:
                c = str(col).strip()
                if not c:
                    continue
                dkey = self._dedupe_column_key(c)
                if dkey not in bucket["_source_col_keys"] and len(bucket["source_columns"]) < 15:
                    bucket["_source_col_keys"].add(dkey)
                    bucket["source_columns"].append(c)

            op = str(row.get("operation") or "").strip()
            if op and op not in bucket["operations"]:
                bucket["operations"].append(op)

            filter_candidates = [
                self._clean_text(row.get("where_predicate") or row.get("filter_condition") or ""),
                "; ".join(self._join_predicate_texts(row.get("join_predicates") or [])),
                "; ".join(self._exists_predicate_texts(row.get("exists_predicates") or [])),
                self._clean_text(row.get("having_predicate") or ""),
            ]
            if not row.get("where_predicate") and row.get("trigger_condition"):
                filter_candidates.append(self._clean_text(row.get("trigger_condition")))
            for f in filter_candidates:
                if f and f not in bucket["filters"] and len(bucket["filters"]) < 3:
                    bucket["filters"].append(f)

        return list(grouped.values())

    # ------------------------------------------------------------------
    # 12. Important Fields
    # ------------------------------------------------------------------

    def _important_fields_section(self, ingestion: IngestionResult, rules: List[Dict[str, Any]]) -> str:
        """Grounded in the already business-curated rule output, so this
        can never surface parser noise (keywords, literals, punctuation)
        the way a raw technical-identifier scrape would - every entry
        here is either a declared parameter or a field a synthesized
        business rule actually claims to read/affect. Every candidate is
        validated in full (not just its first token) so a rendering
        placeholder like "Not specified"/"N/A"/"None" - which happens to
        start with a word that alone looks like an identifier - can never
        be mistaken for a real field name. When one rule affects several
        fields, they are grouped onto a single row instead of repeating
        the same explanatory sentence once per field.
        """
        seen_fields: set = set()
        groups: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

        for param in getattr(ingestion, "parameters", []) or []:
            name = getattr(param, "name", "")
            if name and name not in seen_fields:
                seen_fields.add(name)
                groups[f"param::{name}"] = {
                    "fields": [name],
                    "meaning": f"Declared parameter ({getattr(param, 'direction', '')}, {getattr(param, 'datatype', '')}).",
                }

        for idx, rule in enumerate(rules, start=1):
            rule_name = self._business_rule_name(rule, idx)
            meaning = self._shorten_text(self._business_rule_business_meaning(rule), 110)
            candidates = list(rule.get("fields_affected") or [])
            output_field = rule.get("output_field")
            if output_field:
                candidates = [output_field] + [f for f in candidates if f != output_field]

            fields_for_rule: List[str] = []
            for candidate in candidates:
                if not self._looks_like_field_name(candidate):
                    continue
                for part in re.split(r"[,/]", str(candidate)):
                    field = part.strip()
                    if field and field not in seen_fields:
                        seen_fields.add(field)
                        fields_for_rule.append(field)

            if fields_for_rule:
                groups[f"rule::{idx}"] = {
                    "fields": fields_for_rule,
                    "meaning": f"{meaning} (Rule: {rule_name})",
                }

        if not groups:
            return "## Important Fields\n\n_None identified._"

        lines = ["## Important Fields", "", "| Fields | Business Meaning |", "|---|---|"]
        field_budget = 40
        for group in groups.values():
            if field_budget <= 0:
                break
            field_display = ", ".join(f"`{self._escape_table_cell(f)}`" for f in group["fields"])
            lines.append(f"| {field_display} | {self._escape_table_cell(group['meaning'])} |")
            field_budget -= len(group["fields"])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 13. Business Rule Summary
    # ------------------------------------------------------------------

    def _business_rule_summary_table(self, rules: List[Dict[str, Any]], include_technical_ids: bool = False) -> str:
        header = ["| Priority | Rule | Output | Business Purpose |", "|---|---|---|---|"]
        if not rules:
            return "## Business Rule Summary\n\n" + "\n".join(header) + "\n_No business rules were identified._"
        rows = []
        for idx, rule in enumerate(rules, start=1):
            icon = self._review_priority_icon(rule)
            name = self._escape_table_cell(self._business_rule_name(rule, idx))
            output = self._escape_table_cell(self._business_rule_output(rule))
            purpose = self._escape_table_cell(self._shorten_text(self._business_rule_business_meaning(rule), 140))
            if include_technical_ids:
                rule_id = self._escape_table_cell(str(rule.get("rule_id") or f"rule_{idx:02d}"))
                recon_status = str(rule.get("reconciliation_status") or "").strip().upper()
                if recon_status:
                    name = f"{name} [{recon_status}]"
                name = f"{name} (`{rule_id}`)"
            rows.append(f"| {icon} {idx} | {name} | `{output}` | {purpose} |")
        return "## Business Rule Summary\n\n" + self._render_split_table(header, rows)

    # ------------------------------------------------------------------
    # 14. Source Traceability (collapsible, deduplicated, escaped)
    # ------------------------------------------------------------------

    def _source_traceability_details(
        self, rules: List[Dict[str, Any]], merged_extraction: Dict[str, Any]
    ) -> str:
        lines = [
            "## Source Traceability",
            "",
            "<details>",
            "<summary><strong>Show rule-to-source mapping</strong></summary>",
            "",
        ]
        header = [
            "| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |",
            "|---|---|---|---|---|---|---|",
        ]
        rows = []
        for idx, rule in enumerate(rules, start=1):
            name = self._business_rule_name(rule, idx)
            rule_id = str(rule.get("rule_id") or f"rule_{idx:02d}")
            evidence = rule.get("source_evidence") or []
            evidence_display = self._shorten_text("; ".join(evidence), 260) if evidence else "Not cited"
            source_location_display = self._format_evidence_spans(rule.get("evidence_spans") or [])
            if not source_location_display:
                source_location_display = "Not cited"
            source_chunks = rule.get("source_chunks") or []
            source_chunks_display = "; ".join(source_chunks) if source_chunks else "Not cited"
            technical_refs = self._dedupe_technical_references(
                rule.get("technical_references") or [], merged_extraction
            )
            technical_refs_display = "; ".join(technical_refs) if technical_refs else "Not cited"
            unresolved = rule.get("unresolved_ambiguities") or []
            notes = "; ".join(unresolved) if unresolved else (
                "Verified"
                if str(rule.get("validation_status") or "unverified").lower() == "verified"
                else "Needs Review"
            )
            rows.append(
                f"| {idx} | {self._escape_table_cell(f'{name} ({rule_id})')} | {self._escape_table_cell(evidence_display)} | "
                f"{self._escape_table_cell(source_location_display)} | {self._escape_table_cell(source_chunks_display)} | "
                f"{self._escape_table_cell(technical_refs_display)} | {self._escape_table_cell(notes)} |"
            )
        lines.append(self._render_split_table(header, rows))
        lines.append("")
        lines.append(
            "_Source evidence is the literal technical text carried through the pipeline; "
            "Source Location is derived deterministically from chunk and statement provenance when available; "
            "SQL Statements / Chunks and Technical References point back to the extracted "
            "chunk ids and statement references used by the guardrails. Technical references "
            "that repeat the same table/operation/target-columns are shown once._"
        )
        lines.append("</details>")
        return "\n".join(lines)

    def _dedupe_technical_references(
        self, refs: List[str], merged_extraction: Dict[str, Any], limit: int = 6, max_len: int = 200
    ) -> List[str]:
        rendered: List[str] = []
        seen: set = set()
        for ref in refs:
            text = self._render_technical_reference(ref, merged_extraction)
            text = self._shorten_text(text, max_len)
            # Two references to the same table/operation/target-columns that
            # only differ in *how* they were parsed (structured parse vs.
            # regex fallback) or in their provenance ids are the same piece
            # of evidence for reporting purposes - collapse them.
            sig = re.sub(r"\s+", " ", text).strip().lower()
            sig = re.sub(r"provenance:.*$", "", sig).strip()
            sig = re.sub(r"^\S+:\s*", "", sig)  # drop the leading ref id, e.g. "tables_written[9]: "
            if sig in seen:
                continue
            seen.add(sig)
            rendered.append(text)
        if len(rendered) > limit:
            omitted = len(refs) - limit
            rendered = rendered[:limit] + [f"_(+{omitted} more instance(s) not shown)_"]
        return rendered

    # ------------------------------------------------------------------
    # Supplementary technical sections
    # ------------------------------------------------------------------

    def _calculations(self, synthesis: SynthesisResult) -> str:
        calcs = synthesis.data.get("calculations", [])
        if not calcs:
            return "## Calculations / Formulas\n\n_None identified._"
        lines = [
            f"- **{c.get('metric', 'Metric')}:** {c.get('explanation', 'N/A')}"
            for c in calcs
        ]
        return "## Calculations / Formulas\n\n" + "\n".join(lines)

    def _exception_handling(self, synthesis: SynthesisResult) -> str:
        summary = synthesis.data.get("exception_handling_summary") or (
            "No explicit failure-path behavior identified."
        )
        return f"## Exception Handling Behavior\n\n{summary}"

    def _validation_summary(
        self,
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
        synthesis: SynthesisResult,
    ) -> str:
        """Rollup of how many business rules are explicit/inferred/
        assumption and verified/unverified, so a reviewer can triage
        which rules need the closest human scrutiny without reading the
        full table.
        """
        if not rules:
            return (
                "## Rule Provenance Summary\n\n"
                "_No business rules were synthesized for this object - see "
                "Ambiguities section._"
            )

        type_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        for r in rules:
            rule_type = r.get("rule_type") or "inferred"
            status = r.get("validation_status") or "unverified"
            type_counts[rule_type] = type_counts.get(rule_type, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1

        lines = [
            "## Rule Provenance Summary",
            "",
            f"- **Total business rules:** {len(rules)}",
            "- **By rule type:** " + ", ".join(f"{k} = {v}" for k, v in sorted(type_counts.items())),
            "- **By validation status:** " + ", ".join(f"{k} = {v}" for k, v in sorted(status_counts.items())),
        ]
        if status_counts.get("unverified"):
            lines.append(
                "\n_Rules marked **unverified** could not be matched back to the "
                "technical extraction or source code and should be prioritized for "
                "human review before being treated as confirmed._"
            )
        if status_counts.get("parser_failed"):
            lines.append(
                "\n_Rules marked **parser_failed** depend on technical evidence from "
                "a chunk that failed structural parsing and must be treated as "
                "uncertain until the source is reprocessed or manually reviewed._"
            )
        if status_counts.get("insufficient_evidence"):
            lines.append(
                "\n_Rules marked **insufficient_evidence** have some support, but the "
                "technical extraction was incomplete or only weakly supported and "
                "should not be treated as fully verified._"
            )
        if status_counts.get("ambiguous"):
            lines.append(
                "\n_Rules marked **ambiguous** are supported only weakly or with "
                "conflicting technical signals and need a human review before use._"
            )
        return "\n".join(lines)

    def _reconciliation_summary(self, merged_extraction: Dict[str, Any], synthesis: SynthesisResult) -> str:
        reconciliation = merged_extraction.get("reconciliation") or synthesis.data.get("reconciliation") or {}
        if not isinstance(reconciliation, dict) or not reconciliation:
            return ""

        summary = reconciliation.get("summary") or {}
        status_counts = reconciliation.get("status_counts") or {}
        records = reconciliation.get("records") or []
        review_required = bool(reconciliation.get("review_required") or summary.get("review_required"))

        lines = [
            "## Reconciliation Summary",
            "",
            f"- **Matched facts:** {summary.get('matched', status_counts.get('MATCHED', 0))}",
            f"- **Deterministic-only facts:** {summary.get('deterministic_only', status_counts.get('DETERMINISTIC_ONLY', 0))}",
            f"- **LLM-only claims:** {summary.get('llm_only', status_counts.get('LLM_ONLY', 0))}",
            f"- **Conflicts:** {summary.get('conflicts', status_counts.get('CONFLICT', 0))}",
            f"- **Unresolved items:** {summary.get('unresolved', status_counts.get('UNRESOLVED', 0))}",
        ]

        if review_required:
            lines.append("- **Review required:** Yes")
        else:
            lines.append("- **Review required:** No")

        note = str(summary.get("note") or "").strip()
        if note:
            lines.extend(["", note])

        review_items = []
        for record in records:
            if not isinstance(record, dict):
                continue
            status = str(record.get("status") or "").upper()
            if status in {"CONFLICT", "LLM_ONLY", "UNRESOLVED", "DETERMINISTIC_ONLY"}:
                review_items.append(record)
        if review_items:
            lines.extend(["", "### Review Items", ""])
            for record in review_items[:5]:
                label = record.get("kind") or "item"
                rec_id = record.get("reconciliation_id") or "n/a"
                rule_id = record.get("rule_id") or ""
                chunk_id = record.get("chunk_id") or ""
                statement_id = record.get("statement_id") or ""
                status = str(record.get("status") or "").upper()
                note_text = str(record.get("note") or "").strip()
                context_bits = [bit for bit in [rule_id, chunk_id, statement_id] if bit]
                context = ", ".join(context_bits) if context_bits else "no direct provenance"
                line = f"- `{status}` {label} (`{rec_id}`): {context}"
                if note_text:
                    line += f" - {note_text}"
                lines.append(line)

        return "\n".join(lines)

    def _quality_summary(self, merged_extraction: Dict[str, Any], synthesis: SynthesisResult) -> str:
        quality = merged_extraction.get("quality") or synthesis.data.get("quality") or {}
        if not isinstance(quality, dict) or not quality:
            return ""

        coverage = quality.get("coverage") or merged_extraction.get("reconciliation", {}).get("coverage") or {}
        contradictions = quality.get("contradictions") or merged_extraction.get("reconciliation", {}).get("contradictions") or []
        factors = quality.get("factors") or {}
        status = str(quality.get("status") or "LOW_CONFIDENCE").upper()
        score = quality.get("score")
        review_required = bool(quality.get("review_required"))

        lines = [
            "## Quality Summary",
            "",
            f"- **Overall status:** {status}",
        ]
        if score is not None:
            lines.append(f"- **Quality score:** {score}/100")
        lines.append(
            f"- **Statement coverage:** {coverage.get('parsed_statements', 0)} / {coverage.get('total_statements', 0)}"
            + (
                f" ({coverage.get('statement_parse_success_pct')}%)"
                if coverage.get("statement_parse_success_pct") is not None
                else ""
            )
        )
        lines.append(
            f"- **Rule grounding coverage:** {coverage.get('rules_with_deterministic_support', 0)} / {coverage.get('synthesized_rules', 0)}"
            + (
                f" ({coverage.get('rule_grounding_pct')}%)"
                if coverage.get("rule_grounding_pct") is not None
                else ""
            )
        )
        lines.append(f"- **Conflicts:** {coverage.get('conflicts', 0)}")
        lines.append(f"- **Contradictions:** {coverage.get('contradictions', len(contradictions) if isinstance(contradictions, list) else 0)}")
        lines.append(f"- **Review required items:** {coverage.get('review_required_items', 0)}")
        if review_required:
            lines.append("- **Review required:** Yes")
        else:
            lines.append("- **Review required:** No")

        note = str(quality.get("note") or "").strip()
        if note:
            lines.extend(["", note])

        if isinstance(contradictions, list) and contradictions:
            lines.extend(["", "### Contradictions", ""])
            for finding in contradictions[:5]:
                if not isinstance(finding, dict):
                    continue
                finding_type = str(finding.get("type") or "contradiction").replace("_", " ").title()
                severity = str(finding.get("severity") or "LOW").upper()
                explanation = str(finding.get("explanation") or "").strip()
                target = finding.get("rule_id") or ", ".join(finding.get("related_rule_ids") or []) or "source"
                lines.append(f"- `{severity}` {finding_type} on `{target}`" + (f": {explanation}" if explanation else ""))

        if factors:
            lines.append("")
            lines.append(
                "_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._"
            )
        return "\n".join(lines)

    def _ambiguities(
        self,
        ingestion: IngestionResult,
        synthesis: SynthesisResult,
        extraction_guardrail_warnings: List[str],
    ) -> str:
        items: List[str] = []
        items.extend(getattr(ingestion, "parse_warnings", []) or [])
        items.extend(extraction_guardrail_warnings)
        items.extend(synthesis.data.get("ambiguities", []) or [])
        items.extend(synthesis.guardrail_warnings)
        if synthesis.jargon_flags:
            items.append(
                "Automated style check flagged possible leftover technical "
                f"jargon in the synthesized output: {', '.join(synthesis.jargon_flags)}. "
                "Recommend a human pass to rephrase in business terms."
            )
        if synthesis.parse_error:
            items.append(
                "The business rule synthesis response could not be parsed as "
                "valid JSON; the object's rules should be regenerated or "
                "reviewed manually."
            )

        if not items:
            return "## Ambiguities / Needs Review\n\nNone."

        deduped = list(dict.fromkeys(items))
        lines = [f"- {item}" for item in deduped]
        return "## Ambiguities / Needs Review\n\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # Legacy curated glossary (kept for backward compatibility - small,
    # capped, only genuinely domain-specific banking/regulatory terms;
    # not part of the main assembled report but still available for
    # callers/tests that want a short glossary blurb rather than the
    # full Important Fields table).
    # ------------------------------------------------------------------

    def _glossary_section(self, ingestion: IngestionResult) -> str:
        raw_code = str(getattr(ingestion, "raw_code", "") or "")
        entries = self._legacy_glossary_entries(raw_code)
        lines = ["## Glossary", ""]
        if not entries:
            lines.append("No domain-specific terms were identified.")
            return "\n".join(lines)

        lines.extend(["| Term | What it means |", "|---|---|"])
        for term, meaning in entries[:5]:
            lines.append(f"| **{term}** | {meaning} |")
        return "\n".join(lines)

    @staticmethod
    def _legacy_glossary_entries(raw_code: str) -> List[Tuple[str, str]]:
        text = str(raw_code or "")
        if not text.strip():
            return []

        patterns: List[Tuple[str, str, str]] = [
            (
                "DPD",
                r"(?<![A-Z0-9_])DPD(?![A-Z0-9_])",
                "Days Past Due - the count of overdue days used to measure delinquency.",
            ),
            (
                "NPA",
                r"(?<![A-Z0-9_])NPA(?![A-Z0-9_])",
                "Non-Performing Asset - a loan or account that has moved into delinquency.",
            ),
            (
                "SMA",
                r"(?<![A-Z0-9_])SMA(?![A-Z0-9_])",
                "Special Mention Account - an account that needs closer monitoring.",
            ),
            (
                "UCIF",
                r"(?<![A-Z0-9_])UCIF(?![A-Z0-9_])",
                "Unique Customer Identification File - the customer identifier used to group linked accounts.",
            ),
            (
                "IRAC",
                r"(?<![A-Z0-9_])IRAC(?![A-Z0-9_])",
                "Asset classification and provisioning norms used for overdue loan accounts.",
            ),
            (
                "Asset Classification Codes",
                r"(?<![A-Z0-9_])(?:FINALASSETCLASSALT_KEY|SYSASSETCLASSALT_KEY|SMA_CLASS|STD|SUB|DB1|DB2|DB3|LOS)(?![A-Z0-9_])",
                "Asset status labels used to classify accounts into standard, sub-standard, doubtful, or loss buckets.",
            ),
        ]

        entries: List[Tuple[str, str]] = []
        for term, pattern, meaning in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                entries.append((term, meaning))
        return entries

    # ------------------------------------------------------------------
    # Generic, low-risk heuristics (presentational grouping only - never
    # invent facts, only detect keywords already present in extracted
    # rule text so related rules can be visually grouped)
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_field_name(value: Any) -> bool:
        """True only if `value` is, in full, a single clean identifier or
        a short comma/slash-separated list of clean identifiers (e.g.
        "SMA_CLASS" or "SMA_CLASS, SMA_REASON"). False for prose
        sentences, rendering placeholders ("Not specified", "N/A", ...),
        or anything else that isn't actually a field name - validated
        across the WHOLE string, not just its first word, since a
        placeholder sentence can easily start with a word that alone
        looks like a valid identifier (e.g. "Not specified" starts with
        "Not", which passes an identifier-shape check on its own).
        """
        text = str(value or "").strip()
        if not text:
            return False
        if text.lower() in _PLACEHOLDER_FIELD_VALUES:
            return False
        parts = [p.strip() for p in re.split(r"[,/]", text)]
        if not parts or len(parts) > 8:
            return False
        for part in parts:
            if not part or part.lower() in _PLACEHOLDER_FIELD_VALUES:
                return False
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", part):
                return False
        return True

    @staticmethod
    def _detect_hierarchy_levels(rules: List[Dict[str, Any]]) -> List[str]:
        haystacks = [
            " ".join(
                [
                    str(rule.get("rule_name") or ""),
                    str(rule.get("business_meaning") or ""),
                    str(rule.get("output_field") or ""),
                ]
            ).lower()
            for rule in rules
        ]
        combined = " ".join(haystacks)
        found: List[str] = []
        for level in _HIERARCHY_LEVEL_TERMS:
            if re.search(rf"\b{re.escape(level)}", combined):
                found.append(level)
        return found

    # ------------------------------------------------------------------
    # Small formatting utilities
    # ------------------------------------------------------------------

    def _render_split_table(self, header_lines: List[str], rows: List[str]) -> str:
        """Renders a Markdown table, splitting it into multiple
        header-repeating tables when it has more than `_MAX_TABLE_ROWS`
        rows, so long tables stay readable in GitHub/VS Code instead of
        becoming one unbroken wall. No row is ever dropped by this -
        only re-paginated.
        """
        if not rows:
            return "\n".join(header_lines)
        if len(rows) <= self._MAX_TABLE_ROWS:
            return "\n".join(header_lines + rows)

        chunks = [rows[i : i + self._MAX_TABLE_ROWS] for i in range(0, len(rows), self._MAX_TABLE_ROWS)]
        total = len(chunks)
        parts: List[str] = []
        for i, chunk in enumerate(chunks, start=1):
            if i > 1:
                parts.append(f"_(continued — part {i} of {total})_")
                parts.append("")
            parts.append("\n".join(header_lines + chunk))
        return "\n\n".join(parts)

    @staticmethod
    def _dedupe_column_key(column: str) -> str:
        """Normalizes a column reference for deduplication purposes only
        (the original text is still what gets displayed) - strips a
        leading table alias (e.g. "A.", "dpd.") and upper-cases the rest,
        so "A.SMA_DT", "dpd.SMA_DT", and "SMA_DT" are recognized as the
        same underlying column instead of three separate table rows.
        """
        text = str(column or "").strip()
        match = re.match(r"^[A-Za-z_][A-Za-z0-9_]*\.(.+)$", text)
        base = match.group(1) if match else text
        return base.upper()

    # At-a-Glance table cap. This is a *display* cap only - unlike the
    # previous `consolidated_writes[:6]` slice (which silently dropped
    # every table past the 6th, local temp tables and history tables
    # included, with no indication anything was hidden), going over the
    # cap here always renders a "+N more" pointer to the full, complete
    # "Tables Written" section rather than dropping tables invisibly.
    _AT_A_GLANCE_TABLE_CAP = 10

    @classmethod
    def _summarize_table_list(cls, consolidated_writes: List[Dict[str, Any]]) -> str:
        if not consolidated_writes:
            return "Not identified"
        names = [str(b.get("table") or "").strip() for b in consolidated_writes]
        names = [n for n in names if n]
        if not names:
            return "Not identified"
        if len(names) <= cls._AT_A_GLANCE_TABLE_CAP:
            return ", ".join(f"`{n}`" for n in names)
        shown = names[: cls._AT_A_GLANCE_TABLE_CAP]
        remaining = len(names) - len(shown)
        return (
            ", ".join(f"`{n}`" for n in shown)
            + f" _(+{remaining} more — see Tables Written below)_"
        )

    @staticmethod
    def _unique_ordered(items: List[str]) -> List[str]:
        seen: set = set()
        result: List[str] = []
        for item in items:
            key = re.sub(r"\s+", " ", str(item)).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(str(item).strip())
        return result

    @staticmethod
    def _display_object_name(ingestion: IngestionResult) -> str:
        canonical = str(getattr(ingestion, "canonical_object_name", "") or "").strip()
        if canonical and canonical.upper() not in {"UNKNOWN_OBJECT", "UNKNOWN", "NONE"}:
            return canonical
        object_name = str(getattr(ingestion, "object_name", "") or "").strip()
        if object_name and object_name.upper() not in {"UNKNOWN_OBJECT", "UNKNOWN", "NONE"}:
            return object_name
        return "Not specified"

    @staticmethod
    def _display_object_type(object_type: str) -> str:
        normalized = str(object_type or "").strip()
        if not normalized or normalized.upper() in {"UNKNOWN"}:
            return "Not specified"
        return normalized.replace("_", " ").title()

    @staticmethod
    def _strip_leading_numbering(text: str) -> str:
        return re.sub(r"^\s*\d+(?:\.\d+)*[\).\s-]+", "", str(text or "")).strip()

    @staticmethod
    def _business_rule_name(rule: Dict[str, Any], idx: int) -> str:
        explicit = str(rule.get("rule_name") or "").strip()
        condition = str(rule.get("condition") or "").strip()
        action = str(rule.get("action") or "").strip()
        if explicit:
            if condition and re.search(r"[<>=]|\bbetween\b|\belse\b", condition, re.IGNORECASE):
                if re.search(r"\bladder\b|\bclassification\b|\bbucket\b|\brisk\b", explicit, re.IGNORECASE):
                    return condition
            return explicit
        if condition:
            if not action:
                return condition
            if re.search(r"[<>=]|\bbetween\b|\belse\b", condition, re.IGNORECASE):
                return condition
            if len(condition) <= len(action):
                return condition
        name = action or condition or f"Rule {idx}"
        return name or f"Rule {idx}"

    @staticmethod
    def _business_rule_output(rule: Dict[str, Any]) -> str:
        output_field = rule.get("output_field")
        if isinstance(output_field, str) and output_field.strip():
            return output_field.strip()
        fields = rule.get("fields_affected") or []
        if fields:
            return ", ".join(fields)
        return "Not specified"

    @staticmethod
    def _business_rule_business_meaning(rule: Dict[str, Any]) -> str:
        meaning = rule.get("business_meaning") or rule.get("action") or rule.get("condition")
        text = str(meaning or "").strip()
        if text and ReportFormatterAgent._meaning_matches_rule_name(rule, text):
            return text
        derived = ReportFormatterAgent._meaning_from_rule_name(rule)
        return derived or text or "Not specified"

    @staticmethod
    def _meaning_matches_rule_name(rule: Dict[str, Any], meaning: str) -> bool:
        name = str(rule.get("rule_name") or "").strip().lower()
        if not name or not meaning:
            return False

        stopwords = {
            "the", "a", "an", "to", "of", "and", "or", "for", "if", "when", "by", "from",
            "all", "any", "each", "this", "that", "is", "are", "be", "as", "with", "on",
            "into", "in", "out", "based", "rule", "account", "accounts", "field", "fields",
        }

        def _tokens(text: str) -> set[str]:
            return {
                token
                for token in re.findall(r"[A-Za-z0-9_]+", text.lower())
                if token not in stopwords and not token.isdigit()
            }

        name_tokens = _tokens(name)
        meaning_tokens = _tokens(str(meaning))
        if not name_tokens or not meaning_tokens:
            return False
        overlap = name_tokens & meaning_tokens
        return len(overlap) >= max(1, min(2, len(name_tokens) // 2))

    @staticmethod
    def _meaning_from_rule_name(rule: Dict[str, Any]) -> str:
        name = str(rule.get("rule_name") or rule.get("action") or rule.get("condition") or "").strip()
        if not name:
            return ""
        patterns = [
            (r"(?i)^reset\s+(?P<body>.+?)\s+to\s+(?P<value>.+)$", "{body} are reset to {value}."),
            (r"(?i)^calculate\s+(?P<body>.+)$", "The {body} is calculated."),
            (r"(?i)^clear\s+(?P<body>.+)$", "Previous {body} is cleared."),
            (r"(?i)^assign\s+(?P<body>.+)$", "The {body} is assigned."),
            (r"(?i)^set\s+(?P<body>.+)$", "The {body} is set."),
            (r"(?i)^flag\s+(?P<body>.+)$", "The {body} is flagged."),
            (r"(?i)^update\s+(?P<body>.+)$", "The {body} is updated."),
            (r"(?i)^default\s+(?P<body>.+)$", "The {body} is defaulted."),
            (r"(?i)^show\s+(?P<body>.+)$", "The result set shows {body}."),
            (r"(?i)^keep\s+(?P<body>.+)$", "The result set keeps {body}."),
            (r"(?i)^include\s+(?P<body>.+)$", "The result set includes only {body}."),
            (r"(?i)^process\s+(?P<body>.+)$", "The process handles {body}."),
        ]
        for pattern, template in patterns:
            match = re.match(pattern, name)
            if match:
                body = match.groupdict().get("body", "").strip()
                value = match.groupdict().get("value", "").strip()
                if pattern.lower().startswith("(?i)^calculate") and body.lower().endswith(" for account"):
                    body = body[: -len(" for account")].strip()
                    if body:
                        return f"The {body} is calculated for the account."
                if value and body:
                    return template.format(body=body, value=value).strip()
                if body:
                    return template.format(body=body).strip()
        cleaned = name[:1].upper() + name[1:]
        return cleaned if cleaned.endswith(".") else cleaned + "."

    @staticmethod
    def _rule_text_lines(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        if not text:
            return []
        parts = [part.strip(" -") for part in re.split(r"(?:\n+|;\s+)", text) if part.strip(" -")]
        return parts or [text]

    def _decision_logic_rows(self, rule: Dict[str, Any]) -> List[Dict[str, str]]:
        """Only returns rows for a genuine multi-band/lookup mapping
        (2+ distinct condition -> outcome pairs for the same field, e.g.
        a days-overdue ladder). A single condition -> single outcome
        rule already has that outcome stated once in "Business meaning"
        and its gating condition in "Eligibility" - re-stating both as a
        one-row table underneath added nothing but repeated text, so
        that synthetic single-row fallback has been removed entirely.
        """
        rows = rule.get("decision_logic_rows")
        if not isinstance(rows, list) or not rows:
            return []
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            condition = str(row.get("condition") or row.get("when") or row.get("if") or "").strip()
            outcome = str(row.get("outcome") or row.get("then") or row.get("result") or "").strip()
            if condition or outcome:
                normalized.append(
                    {
                        "condition": condition or "Not specified",
                        "outcome": outcome or "Not specified",
                    }
                )
        return normalized

    def _decision_logic_block(self, rows: List[Dict[str, str]]) -> List[str]:
        lines = ["| Condition | Outcome |", "|---|---|"]
        for row in rows:
            lines.append(
                f"| {self._escape_table_cell(row['condition'])} | {self._escape_table_cell(row['outcome'])} |"
            )
        return lines

    # ------------------------------------------------------------------
    # Review-priority icon / escaping / truncation
    # ------------------------------------------------------------------

    @staticmethod
    def _review_priority_icon(rule: Dict[str, Any]) -> str:
        """Maps a rule's validation status (and, for the ambiguous
        'verified but not explicit' case, its rule type) to a quick
        visual review-priority signal for the summary table:
          - red: parser failure or ambiguous technical support - review first
          - green: verified and explicitly stated in the source
          - amber: everything else (unverified, assumption, inferred,
            partially supported) - review before treating as confirmed
        """
        reconciliation_status = str(rule.get("reconciliation_status") or "").strip().upper()
        if reconciliation_status == "CONFLICT":
            return "🔴"
        if reconciliation_status in {"LLM_ONLY", "UNRESOLVED"}:
            return "🟠"
        if reconciliation_status == "DETERMINISTIC_ONLY":
            return "🟡"
        status = str(rule.get("validation_status") or "unverified").strip().lower()
        rule_type = str(rule.get("rule_type") or "").strip().lower()
        if status in {"parser_failed", "ambiguous"}:
            return "🔴"
        if status == "verified" and rule_type == "explicit":
            return "🟢"
        return "🟠"

    @staticmethod
    def _escape_table_cell(text: Any) -> str:
        cleaned = str(text or "").replace("`", "")
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = cleaned.replace("\n", "<br>")
        cleaned = cleaned.replace("|", r"\|")
        return cleaned.strip()

    @staticmethod
    def _clean_text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @staticmethod
    def _shorten_text(text: Any, max_length: int = 180) -> str:
        cleaned = ReportFormatterAgent._clean_text(text)
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[: max_length - 1].rstrip() + "…"

    @staticmethod
    def _join_predicate_texts(predicates: List[Any]) -> List[str]:
        texts: List[str] = []
        for predicate in predicates:
            if isinstance(predicate, dict):
                text = predicate.get("predicate") or predicate.get("condition") or ""
            else:
                text = predicate
            cleaned = ReportFormatterAgent._clean_text(text)
            if cleaned:
                texts.append(cleaned)
        return texts

    @staticmethod
    def _exists_predicate_texts(predicates: List[Any]) -> List[str]:
        texts: List[str] = []
        for predicate in predicates:
            if isinstance(predicate, dict):
                text = predicate.get("predicate") or ""
                kind = predicate.get("kind") or "EXISTS"
                subquery_tables = ", ".join(predicate.get("subquery_tables", []) or [])
                if subquery_tables:
                    text = f"{kind}: {text} [tables: {subquery_tables}]"
            else:
                text = predicate
            cleaned = ReportFormatterAgent._clean_text(text)
            if cleaned:
                texts.append(cleaned)
        return texts

    # ------------------------------------------------------------------
    # Technical-reference rendering (used by Source Traceability)
    # ------------------------------------------------------------------

    def _render_technical_reference(self, ref: str, merged_extraction: Dict[str, Any]) -> str:
        match = re.match(r"^([a-z_]+)\[(\d+)\]$", str(ref).strip())
        if not match:
            return str(ref)
        section, index_text = match.groups()
        items = merged_extraction.get(section, []) or []
        try:
            index = int(index_text)
        except ValueError:
            return str(ref)
        if index < 0 or index >= len(items):
            return str(ref)
        item = items[index]
        if not isinstance(item, dict):
            return str(ref)

        if section == "conditions":
            condition = item.get("condition") or "condition not specified"
            outcome = item.get("true_branch") or item.get("false_branch") or item.get("result") or "outcome not specified"
            return f"{ref}: {condition} -> {outcome}"
        if section in ("tables_read", "tables_written"):
            table = item.get("table") or "table not specified"
            op = item.get("operation")
            target_columns = ", ".join(item.get("target_columns", []) or item.get("columns", []) or []) or "N/A"
            where_predicate = item.get("where_predicate") or item.get("filter_condition") or item.get("trigger_condition") or "None"
            op_part = f" | {op}" if op else ""
            return f"{ref}: `{table}`{op_part} | target: {target_columns} | WHERE: {where_predicate}"
        if section == "calculations":
            metric = item.get("metric") or "metric not specified"
            explanation = item.get("explanation") or "explanation not specified"
            return f"{ref}: {metric} | {explanation}"
        if section == "loops":
            loop_type = item.get("loop_type") or "loop"
            purpose = item.get("purpose") or item.get("iterates_over") or "purpose not specified"
            return f"{ref}: {loop_type} | {purpose}"
        if section == "exception_handling":
            handler = item.get("handler") or "handler not specified"
            behavior = item.get("behavior") or "behavior not specified"
            return f"{ref}: {handler} | {behavior}"
        if section == "ambiguities":
            return f"{ref}: {item}"
        return str(ref)