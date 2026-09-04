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

`format_verification()` produces the verification text emitted to the run log. It carries
exactly that internal detail, so nothing is silently dropped - a
reviewer can still trace any business rule back to the precise SQL
lines, chunk, and statement that produced it, see its reconciliation
status against the deterministic extraction, and see the run metadata
the report was generated under. The two are meant to be written side by
alongside the business report in the run log; `format()` ends with a short
pointer to that log so a reader knows where to look for provenance without
that provenance cluttering the business document itself.
"""

from __future__ import annotations

from collections import OrderedDict
import copy
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.ingestion.ingestion import IngestionResult
from src.ir.canonical_ir import CanonicalBusinessIR
from src.synthesis.rule_synthesizer import SynthesisResult
from src.dialect.detector import AMBIGUOUS, ORACLE, TSQL, UNKNOWN, UNSUPPORTED, normalize_dialect_name
from src.core.pipeline_utils import RunMetadata, run_metadata_to_dict
from src.parsing.dedup import find_write_only_temp_tables

_NOT_DETERMINED = "Not explicitly determined from source SQL."
# Common, semantically-empty words excluded from the business-meaning
# similarity check in `_rules_look_like_the_same_concept` - keeping this
# short and generic (not domain-specific) so it doesn't accidentally
# suppress a real signal word from any particular business domain.
_STOPWORDS_FOR_RULE_SIMILARITY = frozenset(
    {
        "the", "and", "for", "are", "that", "this", "with", "from", "based",
        "sets", "set", "when", "before", "after", "value", "values", "field",
        "fields", "procedure", "record", "records", "source", "defined",
        "applies", "updates", "update", "into", "each", "any", "not", "all",
    }
)

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
        raw_merged_extraction = copy.deepcopy(merged_extraction)
        raw_synthesis_data = copy.deepcopy(synthesis.data)
        run_metadata = run_metadata or getattr(ingestion, "run_metadata", None) or self._metadata_from_merged(
            merged_extraction
        )
        canonical_ir = canonical_ir or self._canonical_ir(ingestion, merged_extraction, synthesis, run_metadata)
        merged_extraction = canonical_ir.to_legacy_merged_extraction(merged_extraction)
        synthesis = self._synthesis_view(synthesis, canonical_ir)
        rules: List[Dict[str, Any]] = [rule.to_dict() for rule in canonical_ir.business_rules]
        display_rules = self._business_rules_for_display(raw_business_rules, rules)
        # Presentation must preserve the LLM-authored rule text. Only the
        # deletion-only operational filter is applied at this boundary.
        business_rules_for_display = self._display_business_rules(display_rules)
        consolidated_reads = self._consolidate_rows(merged_extraction.get("tables_read", []) or [])
        consolidated_writes = self._consolidate_rows(merged_extraction.get("tables_written", []) or [])
        return {
            "run_metadata": run_metadata,
            "canonical_ir": canonical_ir,
            "merged_extraction": merged_extraction,
            "raw_merged_extraction": raw_merged_extraction,
            "raw_synthesis_data": raw_synthesis_data,
            "synthesis": synthesis,
            "rules": rules,
            "decision_blocks": list(getattr(canonical_ir, "decision_blocks", []) or []),
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
        resolved_merged_extraction = ctx["merged_extraction"]
        raw_merged_extraction = ctx["raw_merged_extraction"]
        raw_synthesis_data = ctx["raw_synthesis_data"]

        sections = [
            self._title_block(ingestion, synthesis),
            self._source_truncation_banner(extraction_guardrail_warnings or []),
            self._at_a_glance(
                ingestion,
                synthesis,
                consolidated_reads,
                consolidated_writes,
                business_rules_for_display,
                resolved_merged_extraction,
            ),
            self._reconciliation_notice(resolved_merged_extraction, synthesis),
            self._what_this_does(synthesis, business_rules_for_display, resolved_merged_extraction),
            self._end_to_end_flow(synthesis, business_rules_for_display, resolved_merged_extraction),
            self._called_procedures_section(ingestion),
            self._business_rule_overview_table(business_rules_for_display),
            self._business_rules_section(
                business_rules_for_display,
                decision_blocks=ctx["decision_blocks"],
            ),
            self._calculations(synthesis, resolved_merged_extraction),
            self._data_touched_section(consolidated_reads, consolidated_writes, business_rules_for_display),
            self._hardcoded_values_section(ingestion),
            self._exception_handling(synthesis, getattr(ingestion, "raw_code", ""), resolved_merged_extraction),
            self._findings_section(
                synthesis,
                resolved_merged_extraction,
                getattr(ingestion, "raw_code", ""),
                raw_merged_extraction=raw_merged_extraction,
                raw_synthesis_data=raw_synthesis_data,
            ),
            self._verification_pointer(),
        ]
        sections = [s for s in sections if s and s.strip()]
        return "\n\n".join(sections).strip() + "\n"

    @staticmethod
    def _source_truncation_banner(extraction_guardrail_warnings: List[str]) -> str:
        """A source-level truncation (the input guardrail's char-limit cut,
        `guardrails.py: MAX_INPUT_CHARS`) must be a loud, top-of-document
        statement, not a warning buried in a log the reader never opens.
        Before this, `format()` accepted `extraction_guardrail_warnings` as
        a parameter but never actually read it, so a procedure clipped by
        the size limit produced a report with no indication that its last
        portion of logic was silently dropped.
        """
        for warning in extraction_guardrail_warnings or []:
            text = str(warning or "")
            if "processing limit" in text.lower() and "truncated" in text.lower():
                return (
                    "> **⚠ SOURCE TRUNCATED — INCOMPLETE ANALYSIS**\n"
                    f"> {text}\n"
                    "> Everything below reflects only the analyzed portion of the source. "
                    "Do not treat this report as complete."
                )
        return ""

    @staticmethod
    def _reconciliation_notice(merged_extraction: Dict[str, Any], synthesis: SynthesisResult) -> str:
        """Business-language banner surfacing what the validator actually
        found, instead of the reader seeing "None identified" while the
        pipeline's own quality score is near zero. This used to be dead
        code (built, never called from `format()`) - see the docstring
        history; without it a low-confidence report and a clean report
        rendered identically to the reader.
        """
        quality = merged_extraction.get("quality") or synthesis.data.get("quality") or {}
        if not isinstance(quality, dict) or not quality:
            return ""
        status = str(quality.get("status") or "").upper()
        review_required = bool(quality.get("review_required")) or status in {
            "REVIEW_REQUIRED",
            "FAIL",
            "FAILED",
            "LOW_CONFIDENCE",
        }
        if not review_required:
            return ""

        coverage = quality.get("coverage") or merged_extraction.get("reconciliation", {}).get("coverage") or {}
        score = quality.get("score")

        detail_bits: List[str] = []
        synthesized_rules = coverage.get("synthesized_rules")
        grounded_rules = coverage.get("rules_with_deterministic_support")
        if synthesized_rules:
            ungrounded = synthesized_rules - (grounded_rules or 0)
            if ungrounded > 0:
                detail_bits.append(
                    f"{ungrounded} of {synthesized_rules} rules could not be traced back to source statements"
                )
        total_statements = coverage.get("total_statements")
        parsed_statements = coverage.get("parsed_statements")
        if total_statements:
            unmatched_pct = round(100 - float(coverage.get("statement_parse_success_pct") or 0), 1)
            if unmatched_pct > 0:
                detail_bits.append(f"{unmatched_pct}% of SQL statements were not matched to a rule")
        contradiction_count = coverage.get("contradictions")
        if contradiction_count:
            detail_bits.append(f"{contradiction_count} contradiction(s) were flagged between source and report")

        detail = " — " + "; ".join(detail_bits) + "." if detail_bits else "."
        score_bit = f" (quality score {score}/100)" if score is not None else ""
        return (
            "**Automated verification:** REVIEW REQUIRED" + score_bit + detail
            + " See the companion verification report before relying on this document."
        )

    def format_verification(
        self,
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis: SynthesisResult,
        canonical_ir: Optional[CanonicalBusinessIR] = None,
        run_metadata: Optional[RunMetadata] = None,
        report_filename: Optional[str] = None,
        extraction_guardrail_warnings: Optional[List[str]] = None,
    ) -> str:
        """Assembles verification / traceability diagnostics for the run log:
        run metadata, rule-to-source mapping (rule IDs, chunk IDs,
        statement IDs, source file/line spans), reconciliation summary,
        quality/confidence scoring, and low-level pipeline/guardrail
        diagnostics. None of this belongs in the business report
        `format()` produces - it exists so that detail isn't lost, just
        kept out of the document business users read.
        """
        ctx = self._prepare(ingestion, merged_extraction, synthesis, canonical_ir, run_metadata)
        run_metadata_resolved = ctx["run_metadata"]
        merged_extraction = ctx["merged_extraction"]
        synthesis = ctx["synthesis"]
        rules = ctx["rules"]

        sections = [
            self._verification_title_block(ingestion, report_filename),
            self._run_metadata_section(ingestion, run_metadata_resolved),
            self._telemetry_section(run_metadata_resolved),
            self._business_rule_summary_table(rules, include_technical_ids=True),
            self._source_traceability_details(rules, merged_extraction),
            self._validation_summary(rules, merged_extraction, synthesis),
            self._reconciliation_summary(merged_extraction, synthesis),
            self._quality_summary(merged_extraction, synthesis),
            self._pipeline_diagnostics_section(
                ingestion,
                synthesis,
                extraction_guardrail_warnings or [],
                ctx["raw_merged_extraction"].get("informational_uncertainties", []) or [],
            ),
        ]
        sections = [s for s in sections if s and s.strip()]
        return "\n\n".join(sections).strip() + "\n"

    def _pipeline_diagnostics_section(
        self,
        ingestion: IngestionResult,
        synthesis: SynthesisResult,
        extraction_guardrail_warnings: List[str],
        informational_uncertainties: Optional[List[str]] = None,
    ) -> str:
        """Low-level parser/guardrail/jargon-scanner noise that is pipeline
        plumbing, not a business finding - kept here (verification-only)
        instead of the business report. See `_findings_section` in the
        business report for the genuinely business-relevant subset
        (deterministic dead-code findings + LLM-flagged ambiguities).
        """
        items: List[str] = []
        items.extend(getattr(ingestion, "parse_warnings", []) or [])
        items.extend(extraction_guardrail_warnings)
        items.extend(
            f"Informational uncertainty: {item}"
            for item in (informational_uncertainties or [])
            if str(item).strip()
        )
        items.extend(synthesis.guardrail_warnings)
        if synthesis.jargon_flags:
            items.append(
                "Automated style check flagged possible leftover technical "
                f"jargon in the synthesized output: {', '.join(synthesis.jargon_flags)}."
            )
        if synthesis.parse_error:
            items.append(
                "The business rule synthesis response could not be parsed as "
                "valid JSON; the object's rules should be regenerated."
            )
        if not items:
            return "## Pipeline Diagnostics\n\nNone."
        deduped = list(dict.fromkeys(items))
        lines = [f"- {item}" for item in deduped]
        return "## Pipeline Diagnostics\n\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # 0. Title
    # ------------------------------------------------------------------

    def _title_block(self, ingestion: IngestionResult, synthesis: SynthesisResult) -> str:
        object_name = self._display_object_name(ingestion)
        schema = str(getattr(ingestion, "schema", "") or "").strip()
        technical_name = f"{schema}.{getattr(ingestion, 'object_name', object_name)}" if schema else object_name
        dialect = self._display_dialect(getattr(ingestion, "dialect", ""))
        parameters = getattr(ingestion, "parameters", None) or []
        if parameters:
            input_display = ", ".join(
                f"`{parameter.name}` ({parameter.datatype}"
                + (", the processing day" if "timekey" in str(parameter.name).lower() else "")
                + ")"
                for parameter in parameters
            )
        else:
            input_display = "None"
        return (
            f"# {object_name} — Business Logic Report\n\n"
            f"**Procedure:** `{technical_name}`  ·  **Dialect:** {dialect}  ·  "
            f"**Input:** {input_display}"
        )

    @staticmethod
    def _verification_pointer() -> str:
        """Point reviewers to the run log for technical diagnostics."""
        return (
            "---\n\n_Source traceability, rule IDs, reconciliation, and run "
            "metadata are emitted in the pipeline run log rather than in "
            "this report._"
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
        """Choose which rule list the business report renders.

        `canonical_rules` (from `canonical_ir.business_rules`) is always
        preferred: it is the only one of the two that has been through
        grounding against the deterministic extraction AND sorted into
        actual source execution order (see
        `_order_business_rules_by_execution_order` in
        src/ir/canonical_ir.py). Falling back to the raw, unordered,
        ungrounded LLM output just because it happens to contain more
        items silently threw both of those away - the report would show
        whatever arbitrary order the model returned rules in, with none
        of the grounding checks applied.

        The only legitimate reason to fall back to `raw_rules` is if
        canonical_ir ended up with NO rules at all (e.g. every rule
        failed grounding) - in that degraded case, showing the raw,
        ungrounded rules is still strictly better than showing an empty
        report. That is the one fallback kept here.
        """
        raw_rules = [rule for rule in raw_rules if isinstance(rule, dict)]
        canonical_rules = [rule for rule in canonical_rules if isinstance(rule, dict)]
        return canonical_rules

    def _display_business_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return a presentation copy without changing rule count or text."""
        return [dict(rule) for rule in rules if isinstance(rule, dict)]

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

    def _telemetry_section(self, run_metadata: Optional[RunMetadata]) -> str:
        data = run_metadata_to_dict(run_metadata)
        telemetry = data.get("telemetry") if isinstance(data, dict) else {}
        if not isinstance(telemetry, dict) or not telemetry:
            return ""
        totals = telemetry.get("totals") if isinstance(telemetry.get("totals"), dict) else {}
        stage_breakdown = telemetry.get("stage_breakdown") if isinstance(telemetry.get("stage_breakdown"), dict) else {}
        rows = [
            ("Run ID", telemetry.get("run_id", "")),
            ("Total LLM Calls", telemetry.get("call_count", "")),
            ("Successful Calls", telemetry.get("success_count", "")),
            ("Failed Calls", telemetry.get("failure_count", "")),
            ("Prompt Tokens", totals.get("prompt_tokens", "")),
            ("Completion Tokens", totals.get("completion_tokens", "")),
            ("Total Tokens", totals.get("total_tokens", "")),
            ("Telemetry Availability", totals.get("availability", "")),
        ]
        lines = ["## LLM Telemetry", "", "| Item | Value |", "|---|---|"]
        lines.extend(
            f"| {label} | `{value}` |" if value not in ("", None) else f"| {label} |  |"
            for label, value in rows
        )
        if stage_breakdown:
            lines.extend(["", "| Stage | Calls | Success | Failure | Tokens | Availability |", "|---|---:|---:|---:|---:|---|"])
            for stage in sorted(stage_breakdown):
                summary = stage_breakdown.get(stage, {})
                tokens = summary.get("token_usage") if isinstance(summary.get("token_usage"), dict) else {}
                lines.append(
                    "| {stage} | {calls} | {success} | {failure} | {tokens_total} | {availability} |".format(
                        stage=stage,
                        calls=summary.get("call_count", 0),
                        success=summary.get("success_count", 0),
                        failure=summary.get("failure_count", 0),
                        tokens_total=tokens.get("total_tokens", ""),
                        availability=tokens.get("availability", ""),
                    )
                )
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
        merged_extraction: Optional[Dict[str, Any]] = None,
    ) -> str:
        object_name = self._display_object_name(ingestion)
        schema = str(getattr(ingestion, "schema", "") or "").strip()
        technical_name = f"{schema}.{getattr(ingestion, 'object_name', object_name)}" if schema else object_name
        dialect = self._display_dialect(getattr(ingestion, "dialect", ""))
        parameters = getattr(ingestion, "parameters", None) or []
        input_display = (
            ", ".join(f"`{parameter.name}` ({parameter.datatype})" for parameter in parameters)
            if parameters
            else "None"
        )
        history_tables = [
            str(row.get("table") or "")
            for row in (consolidated_reads or []) + (consolidated_writes or [])
            if isinstance(row, dict) and _HISTORY_TABLE_PATTERN.search(str(row.get("table") or ""))
        ]
        visible_reads = self._visible_table_count(consolidated_reads)
        visible_writes = self._visible_table_count(consolidated_writes)
        rows = [
            ("Procedure", f"`{technical_name}`"),
            ("Dialect", dialect),
            ("Input", input_display),
            ("Business rules", str(len(rules))),
            ("Tables read", str(visible_reads)),
            ("Tables written", str(visible_writes)),
            (
                "Produces audit trail",
                "Yes — records audit events" if history_tables else "Not detected",
            ),
        ]
        lines = ["## At a Glance", "", "| | |", "|---|---|"]
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

    @staticmethod
    def _visible_table_count(buckets: List[Dict[str, Any]]) -> int:
        """Count only physical tables shown in the business report.

        Temporary working tables and unresolved short alias tokens remain in
        verification/provenance, but are intentionally excluded from the
        reader-facing table count just as they are from Data Touched.
        """
        count = 0
        for bucket in buckets or []:
            table = str(bucket.get("table") or "").strip()
            if not table or table.startswith("#"):
                continue
            if len(table) <= 3 and table.isalpha() and "." not in table and "_" not in table:
                continue
            count += 1
        return count

    # ------------------------------------------------------------------
    # 2. What This Procedure Does
    # ------------------------------------------------------------------

    def _what_this_does(
        self,
        synthesis: SynthesisResult,
        rules: List[Dict[str, Any]],
        merged_extraction: Optional[Dict[str, Any]] = None,
    ) -> str:
        summary = str(synthesis.data.get("purpose_summary") or "").strip()
        if not summary:
            summary = self._derive_purpose_summary(rules)
        return "\n".join(["## What This Does", "", summary])

    def _derive_purpose_summary(self, rules: List[Dict[str, Any]]) -> str:
        """Compose a purpose line from the rules when the model didn't send one.

        Marked explicitly as derived so no reader mistakes it for the model's
        own summary of intent.
        """
        fields = self._distinct_text(
            [self._business_rule_output(rule) for rule in rules or []]
        )
        fields = [field for field in fields if field and field != "Not specified"]
        if not fields:
            return _NOT_DETERMINED
        shown = ", ".join(f"`{field}`" for field in fields[:8])
        more = f", and {len(fields) - 8} other field(s)" if len(fields) > 8 else ""
        return (
            f"_Derived from the extracted rules (no purpose summary was returned "
            f"by the analysis):_ this object applies {len(rules)} business rule(s) "
            f"that set {shown}{more}."
        )

    # ------------------------------------------------------------------
    # 3. End-to-End Business Flow
    # ------------------------------------------------------------------

    def _end_to_end_flow(
        self,
        synthesis: SynthesisResult,
        rules: Optional[List[Dict[str, Any]]] = None,
        merged_extraction: Optional[Dict[str, Any]] = None,
    ) -> str:
        steps: List[str] = synthesis.data.get("step_by_step_flow", []) or []
        if steps:
            lines = [
                f"{i + 1}. {self._strip_leading_numbering(step)}"
                for i, step in enumerate(steps)
            ]
            return "## Process Flow\n\n" + "\n".join(lines)
        # Rules are already emitted in source order, so their names are a
        # faithful (if terse) flow. Better than a placeholder that reads as
        # "the source has no discernible process".
        names = [
            self._business_rule_name(rule, i + 1) for i, rule in enumerate(rules or [])
        ]
        if not names:
            return f"## Process Flow\n\n_{_NOT_DETERMINED}_"
        lines = [f"{i + 1}. {name}" for i, name in enumerate(names)]
        return (
            "## Process Flow\n\n"
            "_Derived from the extracted rules in source order (no step-by-step "
            "flow was returned by the analysis):_\n\n" + "\n".join(lines)
        )

    @staticmethod
    def _called_procedures_section(ingestion: IngestionResult) -> str:
        """List statically-callable EXEC targets in source order.

        222 EXEC calls were measured across 76/91 client procedures, with
        one orchestrator (MAINPROECESSFORASSETCLASSFICATION_BACKDTD_TWO)
        making 23 and containing almost no business logic of its own - its
        entire business meaning IS the call sequence. Without this
        section, an orchestrator's report showed near-zero business rules
        with no indication of what it actually does (call other
        procedures, in order), and a called child's report gave no hint
        of when or in what order it runs relative to its siblings.
        """
        calls = getattr(ingestion, "called_procedures", None) or []
        if not calls:
            return ""
        rows = ["| Order | Procedure | Arguments |", "|---|---|---|"]
        for i, call in enumerate(calls, start=1):
            name = str(call.get("name") or "").strip() or "Not specified"
            arguments = str(call.get("arguments") or "").strip() or "_none_"
            rows.append(f"| {i} | `{name}` | `{arguments}` |")
        return (
            "## Called Procedures\n\n"
            f"This procedure calls {len(calls)} other stored procedure(s), in this order:\n\n"
            + "\n".join(rows)
        )

    @staticmethod
    def _hardcoded_values_section(ingestion: IngestionResult) -> str:
        """List live hardcoded date literals found in the source.

        293 hardcoded date literals were measured in live (non-commented)
        code across 28/91 client files - in a regulatory batch these are
        usually either a deliberate cutover boundary or a forgotten test
        value, and this is typically the first thing an audit reviewer
        asks about. Deterministic and cheap: no LLM involvement, so
        nothing here can be missed by a model or hallucinated.
        """
        dates = getattr(ingestion, "hardcoded_dates", None) or []
        if not dates:
            return ""
        counts: "OrderedDict[str, List[str]]" = OrderedDict()
        for entry in dates:
            value = str(entry.get("value") or "").strip()
            line = str(entry.get("line") or "").strip()
            if not value:
                continue
            counts.setdefault(value, []).append(line)
        if not counts:
            return ""
        rows = ["| Value | Occurrences | Line(s) |", "|---|---|---|"]
        for value, lines in counts.items():
            shown_lines = ", ".join(lines[:8])
            if len(lines) > 8:
                shown_lines += f", + {len(lines) - 8} more"
            rows.append(f"| `{value}` | {len(lines)} | {shown_lines} |")
        return (
            "## Hardcoded Values\n\n"
            "Literal date values found directly in the source (not parameters or config lookups):\n\n"
            + "\n".join(rows)
        )

    # ------------------------------------------------------------------
    # (Dead "Eligibility" section removed - this used to pool every
    # rule's eligibility conditions into one flat cross-rule list, which
    # is exactly the anti-pattern this report design moved away from:
    # eligibility is now rendered per-rule inside each rule's own block
    # in _render_business_rule_block, next to the fields it gates. This
    # section was defined but never wired into `format()`'s section
    # list, so its removal changes nothing about current report output.)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 5. Business Rules
    # ------------------------------------------------------------------

    def _business_rules_section(
        self,
        rules: List[Dict[str, Any]],
        decision_blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = ["## Business Rules", ""]
        if not rules:
            lines.append("_No business rules were identified from the extracted source._")
            return "\n".join(lines)
        if decision_blocks:
            rule_by_id = {
                str(rule.get("rule_id") or ""): rule
                for rule in rules
                if str(rule.get("rule_id") or "")
            }
            consumed_ids: set[str] = set()
            rendered_index = 1
            for block in decision_blocks:
                if not isinstance(block, dict):
                    continue
                block_rules = [
                    rule_by_id[rule_id]
                    for rule_id in block.get("rule_ids", []) or []
                    if rule_id in rule_by_id
                ]
                branches = block.get("branches") or []
                if not block_rules or not isinstance(branches, list):
                    continue
                if all(str(rule.get("rule_id") or "") in consumed_ids for rule in block_rules):
                    continue
                # Canonical branches are the structural source of truth. The
                # renderer does not regroup rules by whichever chain happened
                # to be processed last, which can split multi-output CASEs.
                block_rule = dict(block_rules[0])
                block_rule["decision_block_title"] = block.get("name") or block_rule.get("decision_block_title")
                block_rule["decision_logic_rows"] = [
                    {
                        "condition": branch.get("condition", ""),
                        "outcome": "; ".join(
                            self._distinct_text(
                                [self._assignment_text(item) for item in (branch.get("results") or [])]
                            )
                        ),
                    }
                    for branch in branches
                    if isinstance(branch, dict)
                ]
                lines.extend(self._render_decision_block(rendered_index, [*block_rules, block_rule]))
                lines.append("")
                consumed_ids.update(str(rule.get("rule_id") or "") for rule in block_rules)
                rendered_index += 1

            # Anything not attached to a canonical structural block remains
            # an independent LLM-authored rule and is rendered unchanged.
            for rule in rules:
                if str(rule.get("rule_id") or "") in consumed_ids:
                    continue
                lines.extend(self._render_business_rule_block(rendered_index, rule))
                lines.append("")
                rendered_index += 1
            return "\n".join(lines).strip()
        groups: List[List[Dict[str, Any]]] = []
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for rule in rules:
            block_id = str(rule.get("decision_block_id") or "").strip()
            if block_id:
                if block_id not in grouped:
                    grouped[block_id] = []
                    groups.append(grouped[block_id])
                grouped[block_id].append(rule)
            else:
                groups.append([rule])
        for idx, group in enumerate(groups, start=1):
            # A canonical decision block remains a block even when the LLM
            # represented the complete chain in one rule.  Group size is not
            # a safe proxy for structural control flow.
            has_structural_block = bool(str(group[0].get("decision_block_id") or "").strip())
            if len(group) > 1 or has_structural_block:
                lines.extend(self._render_decision_block(idx, group))
            else:
                lines.extend(self._render_business_rule_block(idx, group[0]))
            lines.append("")
        return "\n".join(lines).strip()

    def _render_decision_block(self, idx: int, rules: List[Dict[str, Any]]) -> List[str]:
        names = self._distinct_text([self._business_rule_name(rule, idx) for rule in rules])
        authored_block_title = next(
            (
                str(rule.get("decision_block_title") or "").strip()
                for rule in rules
                if str(rule.get("decision_block_title") or "").strip()
            ),
            "",
        )
        title = authored_block_title or self._decision_block_title(names)
        affected = self._distinct_text([self._business_rule_output(rule) for rule in rules])
        table_rows: List[Tuple[str, str]] = []
        for rule in rules:
            rows = self._decision_logic_rows(rule)
            if rows:
                action = str(rule.get("action") or "").strip()
                for row in rows:
                    condition = str(row.get("condition") or "").strip()
                    outcome = self._assignment_text(row.get("outcome") or "")
                    assignments = [
                        self._assignment_text(item)
                        for item in (row.get("assignments") or [])
                    ]
                    # A model may put a secondary branch result in the
                    # rule-level action while using the row for the primary
                    # result. Preserve that authored content only when it
                    # carries a literal/result not already represented by
                    # the row; paraphrases remain suppressed.
                    if outcome:
                        result_values = [*assignments, outcome]
                    else:
                        result_values = [*assignments, self._field_references_for_display(action)] if action else assignments
                    table_rows.append((condition, "; ".join(self._distinct_text(result_values))))

                # A rule-level action can contain an additional assignment
                # shared by the block. Render it once, rather than attaching
                # it to every branch and repeating the first branch outcome.
                if action and self._action_has_unrepresented_result(
                    action, [value for row in table_rows for value in row[1:]]
                ):
                    table_rows.append(("", self._field_references_for_display(action)))
            else:
                condition = str(rule.get("condition") or "").strip()
                result = str(rule.get("action") or rule.get("business_meaning") or "").strip()
                table_rows.append((condition, result))

        table_content = [value for row in table_rows for value in row]
        explanations = self._decision_block_explanations(rules, table_content)
        lines = [f"### R{idx} — {title}", ""]
        lines.extend([
            f"**Affected Field:** `{', '.join(affected)}`" if affected and affected[0] != "Not specified" else "**Affected Field:** Not specified",
            "",
            "**Summary:**",
            "",
        ])
        lines.extend(f"- {value}" for value in explanations)
        lines.extend(["", "### Decision Logic", ""])
        lines.extend(self._decision_logic_block([
            {"condition": condition, "outcome": outcome}
            for condition, outcome in table_rows
        ]))
        return lines

    def _decision_block_explanations(
        self, rules: List[Dict[str, Any]], table_content: List[str]
    ) -> List[str]:
        """Use only concise LLM-authored summaries above the branch table."""
        table_keys = {
            re.sub(r"\s+", " ", str(value or "")).strip().casefold()
            for value in table_content
        }
        explanations: List[str] = []
        for rule in rules:
            meaning = str(rule.get("business_meaning") or "").strip()
            if not meaning:
                continue
            key = re.sub(r"\s+", " ", meaning).strip().casefold()
            if key not in table_keys:
                explanations.append(meaning)
        explanations = self._distinct_text(explanations)
        return explanations[:3] or [_NOT_DETERMINED]

    @staticmethod
    def _decision_block_title(names: List[str]) -> str:
        """Use shared LLM wording, never the first branch as the title."""
        usable = [name for name in names if name and name.casefold() != "not specified"]
        if not usable:
            return "Decision block"
        words = [name.split() for name in usable]
        prefix: List[str] = []
        for group in zip(*words):
            if len({word.casefold() for word in group}) != 1:
                break
            prefix.append(group[0])
        if prefix:
            return " ".join(prefix)
        return "Decision block"

    def _render_business_rule_block(self, idx: int, rule: Dict[str, Any]) -> List[str]:
        rule_name = self._business_rule_name(rule, idx)
        output_field = self._business_rule_output(rule)
        decision_logic_rows = self._decision_logic_rows(rule)
        meaning = str(rule.get("business_meaning") or "").strip()
        # `default` carries the CASE's literal ELSE value (e.g. "'OTHER'",
        # "NULL", "isnull(A.DPD_StockStmt,0)"). Merging it flat into the
        # summary bullets printed raw SQL under a business heading, and
        # duplicated a row the Decision Logic table already shows. It is kept,
        # but under its own label and only when it adds something.
        summary_values = self._distinct_text([
            self._field_references_for_display(meaning),
            *self._rule_text_lines(rule.get("tie_priority_handling")),
            *self._rule_text_lines(rule.get("when_not_eligible")),
        ])
        default_values = [
            value
            for value in self._rule_text_lines(rule.get("default"))
            if self._is_presentable_default(value, decision_logic_rows)
        ]

        eligibility_items = self._rule_text_lines(rule.get("eligibility"))

        lines = [f"### R{idx} — {rule_name}", ""]
        lines.append(f"**Affected Field:** `{output_field}`" if output_field != "Not specified" else "**Affected Field:** Not specified")
        lines.append("")
        if eligibility_items:
            lines.append("**Applies to:**")
            lines.append("")
            lines.extend(f"- {item}" for item in eligibility_items)
        else:
            # An empty "eligibility" list means the source showed no gating
            # condition at all - that is itself a material fact (the rule
            # runs unconditionally) and must be stated, not left silent.
            lines.append("**Applies to:** all rows (no additional conditions found in the source)")
        lines.append("")
        lines.append("**Summary:**")
        lines.append("")
        lines.extend(f"- {value}" for value in (summary_values or [_NOT_DETERMINED]))
        lines.append("")

        if default_values:
            lines.append("**Default / fallback:**")
            lines.append("")
            lines.extend(f"- {value}" for value in default_values)
            lines.append("")

        if decision_logic_rows:
            lines.append("### Decision Logic")
            lines.append("")
            lines.extend(self._decision_logic_block(decision_logic_rows))
            lines.append("")

        return lines

    @staticmethod
    def _is_presentable_default(value: Any, decision_logic_rows: List[Dict[str, str]]) -> bool:
        """True only when a `default` adds information a reader can use.

        Suppressed when: the Decision Logic table already carries an ELSE row
        with the same outcome (duplication), the value is a bare NULL (the
        absence of an outcome is already implied), or the value is a raw SQL
        expression rather than a business statement. In the last case the
        expression stays in the verification report's technical lineage - it
        just must not appear under a business heading.
        """
        text = str(value or "").strip()
        if not text:
            return False
        if text.casefold() in {"null", "none", "not specified", "n/a"}:
            return False
        for row in decision_logic_rows or []:
            condition = str(row.get("condition") or "").strip().casefold()
            outcome = str(row.get("outcome") or "").strip()
            if condition in {"else", "otherwise", "default"} and outcome.casefold() == text.casefold():
                return False
        # A bare identifier, a function call, or an operator expression is
        # developer detail, not a business default.
        if re.fullmatch(r"[A-Za-z_][\w\.]*", text):
            return False
        if re.search(r"[()<>=+\-*/]|\bisnull\b|\bcoalesce\b|\bcase\b", text, re.IGNORECASE):
            return False
        return True

    @staticmethod
    def _action_has_unrepresented_result(action: str, represented: List[str]) -> bool:
        """Keep authored secondary result data, not repeated prose.

        This is intentionally presentation-only. It does not interpret SQL
        or construct a result; it compares literal/assignment markers already
        present in the model text with the canonical row data.
        """
        normalized_action = str(action or "").strip()
        if not normalized_action:
            return False
        normalized_rows = " ".join(str(value or "") for value in represented)
        literal = re.compile(r"'(?:''|[^'])*'|\b\d+(?:\.\d+)?\b")
        action_literals = {item.casefold() for item in literal.findall(normalized_action)}
        row_literals = {item.casefold() for item in literal.findall(normalized_rows)}
        if action_literals - row_literals:
            return True
        if re.search(r"(?:\:=|(?<![<>!])=(?!=))", normalized_action) and not re.search(
            r"(?:\:=|(?<![<>!])=(?!=))", normalized_rows
        ):
            return True
        return False

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
            + self._tables_read(_precomputed=consolidated_reads)
            + "\n\n"
            + self._tables_written(_precomputed=consolidated_writes)
        )

    def _tables_read(
        self,
        merged_extraction: Optional[Dict[str, Any]] = None,
        _precomputed: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        consolidated = _precomputed if _precomputed is not None else self._consolidate_rows(
            (merged_extraction or {}).get("tables_read", []) or []
        )
        if not consolidated:
            return "## Tables Read\n\n_None identified._"
        header = ["| Table Name | Key Columns | Filter Conditions |", "|---|---|---|"]
        rows = [self._render_consolidated_read_row(bucket) for bucket in consolidated]
        return "## Tables Read\n\n" + self._render_split_table(header, rows)

    def _tables_written(
        self,
        merged_extraction: Optional[Dict[str, Any]] = None,
        _precomputed: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        consolidated = _precomputed if _precomputed is not None else self._consolidate_rows(
            (merged_extraction or {}).get("tables_written", []) or []
        )
        if not consolidated:
            return "## Tables Written\n\n_None identified._"
        header = ["| Table Name | Operation Type | Columns Affected | Business Trigger |", "|---|---|---|---|"]
        rows = [self._render_consolidated_written_row(bucket) for bucket in consolidated]
        return "## Tables Written\n\n" + self._render_split_table(header, rows)

    def _render_consolidated_read_row(self, bucket: Dict[str, Any]) -> str:
        columns = bucket["target_columns"] or bucket["source_columns"]
        business_context = (
            ", ".join(self._field_for_display(column) for column in columns)
            if columns else "Not specified"
        )
        filters = "; ".join(bucket["filters"]) if bucket["filters"] else "None"
        filters = self._shorten_text(filters, 200)
        extra = f" _(consolidated from {bucket['count']} raw references)_" if bucket["count"] > 1 else ""
        return (
            f"| `{bucket['table']}` | {self._escape_table_cell(business_context)} | "
            f"{self._escape_table_cell(filters)}{extra} |"
        )

    def _render_consolidated_written_row(self, bucket: Dict[str, Any]) -> str:
        operation = ", ".join(bucket["operations"]) if bucket["operations"] else "operation not specified"
        columns = (
            ", ".join(self._field_for_display(column) for column in bucket["target_columns"])
            if bucket["target_columns"] else "Not identified"
        )
        filters = "; ".join(bucket["filters"]) if bucket["filters"] else "None"
        filters = self._shorten_text(filters, 200)
        extra = f" _(consolidated from {bucket['count']} raw references)_" if bucket["count"] > 1 else ""
        return (
            f"| `{bucket['table']}` | `{self._escape_table_cell(operation)}` | "
            f"{self._escape_table_cell(columns)} | {self._escape_table_cell(filters)}{extra} |"
        )

    # ------------------------------------------------------------------
    # (Dead duplicate of "Data Touched" removed here - see the live
    # definition further below, which is the one Python actually uses
    # since a class body keeps only the LAST definition of a given
    # method name. Keeping two copies in sync by hand was itself a
    # source of bugs - see report design notes.)
    # ------------------------------------------------------------------

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
            field_display = ", ".join(
                f"`{self._escape_table_cell(self._field_for_display(f))}`"
                for f in group["fields"]
            )
            lines.append(f"| {field_display} | {self._escape_table_cell(group['meaning'])} |")
            field_budget -= len(group["fields"])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 13. Business Rule Summary
    # ------------------------------------------------------------------

    def _business_rule_overview_table(self, rules: List[Dict[str, Any]]) -> str:
        """Render a business-facing rule index without internal metadata.

        The verification summary intentionally includes reconciliation and
        validation details. The main report gets the same rule inventory in
        a presentation-only form so it remains useful without exposing
        pipeline status or provenance identifiers.
        """
        header = ["| Rule | Affected Field | Business Purpose |", "|---|---|---|"]
        if not rules:
            return "## Business Rule Summary\n\n" + "\n".join(header) + "\n_No business rules were identified._"
        rows = []
        for idx, rule in enumerate(rules, start=1):
            name = self._escape_table_cell(self._business_rule_name(rule, idx))
            output = self._escape_table_cell(self._business_rule_output(rule))
            purpose = self._escape_table_cell(
                self._shorten_text(self._business_rule_business_meaning(rule), 140)
            )
            rows.append(f"| {name} | `{output}` | {purpose} |")
        return "## Business Rule Summary\n\n" + self._render_split_table(header, rows)

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

    def _calculations(
        self,
        synthesis: SynthesisResult,
        merged_extraction: Optional[Dict[str, Any]] = None,
    ) -> str:
        calcs = list(synthesis.data.get("calculations", []) or [])
        if not calcs:
            return "## Calculations\n\n_None identified._"
        lines = []
        for calculation in calcs:
            if not isinstance(calculation, dict):
                continue
            name = (
                calculation.get("name") or calculation.get("result")
                or calculation.get("field") or calculation.get("metric")
                or "Not specified"
            )
            expression = calculation.get("expression") or calculation.get("formula") or "Not specified"
            feeds = self._calculation_output(calculation, merged_extraction)
            used_by = self._calculation_used_by(calculation, merged_extraction, feeds)
            lines.extend([
                f"### Calculation — {self._field_for_display(name)}",
                "",
                "**Expression:**",
                self._field_references_for_display(expression),
                "",
                "**Output:**",
                self._field_for_display(feeds),
                "",
                "**Used By:**",
                str(used_by),
                "",
            ])
        if not lines:
            return "## Calculations\n\n_None identified._"
        return "## Calculations\n\n" + "\n".join(lines)

    @classmethod
    def _calculation_output(
        cls, calculation: Dict[str, Any], merged_extraction: Optional[Dict[str, Any]]
    ) -> str:
        """Resolve only destinations already present in model/provenance data."""
        for key in ("output", "output_field", "destination", "target", "target_column", "feeds"):
            value = calculation.get(key)
            if isinstance(value, str) and value.strip():
                return value
        formula = str(calculation.get("expression") or calculation.get("formula") or "")
        evidence = " ".join(cls._rule_text_lines(calculation.get("source_evidence") or calculation.get("evidence")))
        needle = re.sub(r"\s+", " ", f"{formula} {evidence}").strip().casefold()
        rows = (merged_extraction or {}).get("tables_written", []) if isinstance(merged_extraction, dict) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            assigned = row.get("assigned_values") or row.get("assignments") or []
            assigned_items = assigned if isinstance(assigned, list) else [assigned]
            for item in assigned_items:
                if not isinstance(item, dict):
                    continue
                expression = str(item.get("expression") or item.get("value") or "")
                if not expression:
                    continue
                normalized_expression = re.sub(r"\s+", " ", expression).strip().casefold()
                if normalized_expression in needle or needle in normalized_expression:
                    table = str(row.get("table") or "").strip()
                    column = str(item.get("column") or item.get("target_column") or "").strip()
                    if table and column:
                        return f"{table}.{column}"
        return "Not specified"

    @classmethod
    def _calculation_used_by(
        cls,
        calculation: Dict[str, Any],
        merged_extraction: Optional[Dict[str, Any]],
        output: str,
    ) -> str:
        for key in ("used_by", "used_by_operation", "relationship"):
            value = calculation.get(key)
            if isinstance(value, str) and value.strip():
                return value
        rows = (merged_extraction or {}).get("tables_written", []) if isinstance(merged_extraction, dict) else []
        output_text = str(output or "").casefold()
        for row in rows:
            if not isinstance(row, dict):
                continue
            table = str(row.get("table") or "").strip()
            operation = str(row.get("operation") or "").strip().upper()
            if not table or not operation:
                continue
            if output_text.startswith(f"{table.casefold()}."):
                return f"{operation} INTO {table}" if operation == "INSERT" else f"{operation} {table}"
        return "Not specified"

    def _exception_handling(
        self,
        synthesis: SynthesisResult,
        raw_source: str = "",
        merged_extraction: Optional[Dict[str, Any]] = None,
    ) -> str:
        summary = str(synthesis.data.get("exception_handling_summary") or "").strip()
        if not summary:
            # The LLM key can be missing because the response was truncated
            # before it. A TRY/CATCH block is structurally detectable, so
            # derive the fact rather than asserting "none identified" over a
            # failure path the source plainly contains.
            summary = self._derive_exception_handling(raw_source)
        summary = re.sub(
            r"(?i)\b(?:continues?|proceeds?)\s+(?:execution|processing)\b",
            "the source does not explicitly state whether processing continues",
            str(summary),
        )
        return f"## Exception Handling\n\n{summary}"

    @staticmethod
    def _derive_exception_handling(raw_source: str) -> str:
        """Describe the failure path from the source's CATCH block.

        Deterministic and conservative: it reports only what the CATCH block
        structurally does (which tables it writes, whether it cleans up
        temporary tables, whether it re-raises), never why.
        """
        text = str(raw_source or "")
        if not text:
            return "No explicit failure-path behavior identified."
        block = re.search(
            r"(?is)\bBEGIN\s+CATCH\b(.*?)\bEND\s+CATCH\b", text
        )
        if not block:
            if re.search(r"(?i)\bEXCEPTION\s+WHEN\b", text):
                return (
                    "The source contains an exception handler, but its behavior could "
                    "not be summarized automatically. Review the failure path manually."
                )
            return "No explicit failure-path behavior identified."

        body = block.group(1)
        written = []
        for match in re.finditer(
            r"(?is)\b(?:UPDATE|INSERT\s+INTO|DELETE\s+FROM)\s+([\[\]\w]+(?:\.[\[\]\w]+)*)", body
        ):
            name = match.group(1).replace("[", "").replace("]", "")
            if not name.startswith("#") and name not in written:
                written.append(name)
        dropped = len(re.findall(r"(?i)\bDROP\s+TABLE\s+#", body))
        rethrows = bool(re.search(r"(?i)\b(?:THROW|RAISERROR)\b", body))

        parts = ["The procedure runs inside a TRY/CATCH block."]
        if written:
            parts.append(
                "On failure it records the error against "
                + ", ".join(f"`{name}`" for name in written[:4])
                + " (status, error timestamp, and error message)."
            )
        if dropped:
            parts.append(
                f"It also drops {dropped} temporary working table(s) before exiting."
            )
        if rethrows:
            parts.append("The error is then re-raised to the caller.")
        else:
            parts.append(
                "The error is not re-raised, so the procedure returns without "
                "signalling failure to its caller - downstream steps will only "
                "detect the failure by reading the status table."
            )
        return " ".join(parts)

    @staticmethod
    def _is_control_or_audit_table(table_name: str, write_bucket: Optional[Dict[str, Any]]) -> bool:
        """Behavior-first control/audit detection, not just a name regex.

        `PRO.RunStatus` and `PRO.PROCESSMONITOR` are written by nearly
        every procedure in the client corpus with start/end time, status,
        and process-identity columns - unambiguously control/audit tables
        - but neither matches a HISTORY/AUDIT/MOVEMENT name pattern, so a
        name-only check would leave them sitting in the same undifferentiated
        list as `PRO.AccountCal`. Name patterns remain the primary signal
        (cheap, precise); a column-shape signal is added as a fallback for
        exactly this case.
        """
        if _HISTORY_TABLE_PATTERN.search(table_name) or re.search(
            r"RUNSTATUS|PROCESSMONITOR|PROCESS_MONITOR|JOBLOG|JOB_LOG|ERRORLOG|ERROR_LOG",
            table_name,
            re.IGNORECASE,
        ):
            return True
        if not write_bucket:
            return False
        columns = " ".join(str(c) for c in (write_bucket.get("target_columns") or [])).casefold()
        control_signals = (
            "errordate", "errordescription", "error_date", "error_description",
            "runcount", "run_count", "processname", "process_name",
            "starttime", "start_time", "endtime", "end_time", "completed",
        )
        hits = sum(1 for signal in control_signals if signal in columns)
        return hits >= 2

    def _data_touched_section(
        self,
        consolidated_reads: List[Dict[str, Any]],
        consolidated_writes: List[Dict[str, Any]],
        rules: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        reads_by_table = {b["table"].upper(): b for b in consolidated_reads}
        writes_by_table = {b["table"].upper(): b for b in consolidated_writes}
        all_keys = list(OrderedDict.fromkeys(list(writes_by_table.keys()) + list(reads_by_table.keys())))
        temp_table_keys = [k for k in all_keys if k.startswith("#")]
        display_keys = [k for k in all_keys if not k.startswith("#")]
        # Defensive filter against unresolved SQL aliases leaking through
        # as if they were table names (e.g. a self-join alias like "AA"
        # that the deterministic table-resolution step couldn't map back
        # to its real table within this chunk's boundaries). A real
        # schema-qualified or standalone table name is never a single
        # bare word of 1-3 letters with no schema prefix and no
        # underscore - that shape is a strong, cheap signal of a raw
        # alias rather than a resolved table, and printing one as a
        # "table" in the business report is exactly what must never
        # happen (see the synthesis prompt's alias-naming rule). Anything
        # this filter removes is still fully visible in the verification
        # report's technical lineage, so no evidence is silently lost -
        # only this specific display is protected from a bad name.
        pre_alias_filter_count = len(display_keys)
        display_keys = [
            k for k in display_keys
            if not (len(k) <= 3 and k.isalpha() and "." not in k and "_" not in k)
        ]
        unresolved_alias_count = pre_alias_filter_count - len(display_keys)
        if not display_keys and not temp_table_keys:
            return "## Data Touched\n\n_None identified._"

        def _render_rows(keys: List[str]) -> List[str]:
            out: List[str] = []
            for key in keys:
                write_bucket = writes_by_table.get(key)
                read_bucket = reads_by_table.get(key)
                bucket = write_bucket or read_bucket
                table_name = bucket["table"]
                if write_bucket and read_bucket:
                    rw = "Read + Write"
                elif write_bucket:
                    rw = "Write"
                else:
                    rw = "Read"
                purpose = self._table_purpose_text(write_bucket, read_bucket, rules)
                out.append(
                    f"| `{self._escape_table_cell(table_name)}` | {rw} | "
                    f"{self._escape_table_cell(purpose)} |"
                )
            return out

        header = ["| Table | Read/Write | Purpose |", "|---|---|---|"]
        # Row-count budget per role subsection before collapsing the tail
        # behind a count. A flat 146-row table (the corpus's largest,
        # InsertDataforAssetClassficationRBL) is not a business artifact;
        # grouping by role plus this cap makes even that procedure's
        # Data Touched section readable.
        role_row_cap = 20

        def _render_group(title: str, keys: List[str]) -> str:
            if not keys:
                return ""
            visible, hidden = keys[:role_row_cap], keys[role_row_cap:]
            body = self._render_split_table(header, _render_rows(visible))
            if hidden:
                body += f"\n\n_+ {len(hidden)} more {title.lower()} table(s) - see the verification report._"
            return f"### {title}\n\n{body}"

        control_keys = [
            k for k in display_keys
            if self._is_control_or_audit_table(writes_by_table.get(k, reads_by_table.get(k, {})).get("table", k), writes_by_table.get(k))
        ]
        remaining_keys = [k for k in display_keys if k not in control_keys]
        target_keys = [k for k in remaining_keys if k in writes_by_table]
        source_keys = [k for k in remaining_keys if k not in writes_by_table]

        sections: List[str] = []
        if display_keys:
            # Below a small table count, the role split adds structure
            # without adding value - render one flat table as before.
            if len(display_keys) <= 8:
                sections.append(self._render_split_table(header, _render_rows(display_keys)))
            else:
                for title, keys in (
                    ("Target (written)", target_keys),
                    ("Source (read-only)", source_keys),
                    ("Control / Audit", control_keys),
                ):
                    rendered = _render_group(title, keys)
                    if rendered:
                        sections.append(rendered)
        else:
            sections.append("_No permanent tables identified._")

        # Temp tables (# / ##) are frequently where the actual business
        # logic lives in this codebase (a procedure stages its work in a
        # temp table, then writes back to the permanent table at the
        # end) - they are surfaced as their own subsection rather than
        # silently folded into a vague "omitted" footnote.
        if temp_table_keys:
            sections.append(_render_group("Working Tables (temporary)", temp_table_keys) or "")

        note = ""
        if unresolved_alias_count:
            # This is NOT the same thing as a temp table - it is a SQL
            # alias (e.g. a self-join "A") that the deterministic
            # table-resolution step could not map back to its base table
            # within this chunk. Do not describe it as a "working" or
            # "temporary" table; that asserts something about the source
            # that this filter has no evidence for.
            note = (
                f"\n\n_{unresolved_alias_count} table reference(s) could not be resolved to a table "
                "name and are omitted from this list - see the verification report for the full "
                "technical lineage._"
            )
        return "## Data Touched\n\n" + "\n\n".join(s for s in sections if s) + note

    _COLUMN_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    _COLUMN_ALIAS_RE = re.compile(r"(?is)\bAS\s+\[?([A-Za-z_][A-Za-z0-9_]*)\]?\s*$")
    _COLUMN_TRAILING_ALIAS_RE = re.compile(
        r"(?i)(?:END|\))\s+\[?([A-Za-z_][A-Za-z0-9_]*)\]?\s*$"
    )

    @staticmethod
    def _clean_column_token(value: Any) -> Optional[str]:
        """Reduce a select-list item to the column name a reader recognises.

        `#TEMPTABLE` is populated by a SELECT whose items are full CASE
        expressions. Printing those verbatim put 300 characters of SQL into
        a business table cell. The alias is the name that matters; an item
        with no recoverable alias is dropped rather than shown raw.
        """
        text = str(value or "").strip().strip(",").strip()
        if not text:
            return None
        alias = ReportFormatterAgent._COLUMN_ALIAS_RE.search(text)
        if alias:
            return alias.group(1)
        text = text.strip("[]").strip()
        if "." in text and ReportFormatterAgent._COLUMN_IDENT_RE.match(text.rsplit(".", 1)[-1]):
            text = text.rsplit(".", 1)[-1]
        if ReportFormatterAgent._COLUMN_IDENT_RE.match(text):
            return text
        trailing = ReportFormatterAgent._COLUMN_TRAILING_ALIAS_RE.search(text)
        if trailing:
            return trailing.group(1)
        return None

    @staticmethod
    def _table_purpose_text(
        write_bucket: Optional[Dict[str, Any]],
        read_bucket: Optional[Dict[str, Any]],
        rules: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """One-line business purpose for a table row. MUST NEVER be raw SQL."""
        for bucket in (write_bucket, read_bucket):
            if bucket and bucket.get("target_columns"):
                cleaned: List[str] = []
                dropped = 0
                for column in bucket["target_columns"]:
                    name = ReportFormatterAgent._clean_column_token(column)
                    if name and name not in cleaned:
                        cleaned.append(name)
                    elif not name:
                        dropped += 1
                operations = {str(operation).upper() for operation in bucket.get("operations") or []}
                if not cleaned:
                    if operations:
                        return (
                            "Participates in "
                            + ", ".join(sorted(operations)).lower()
                            + " processing (columns are computed expressions)."
                        )
                    return "Not specified"
                shown = ", ".join(
                    ReportFormatterAgent._field_for_display(name) for name in cleaned[:6]
                )
                overflow = len(cleaned) - 6 + dropped
                if overflow > 0:
                    shown += f" (+{overflow} more)"
                if "INSERT" in operations:
                    return f"Inserts data into: {shown}"
                if "UPDATE" in operations:
                    return f"Updates: {shown}"
                if "DELETE" in operations:
                    return f"Deletes rows identified by: {shown}"
                return f"Provides: {shown}"
            if bucket and bucket.get("operations"):
                operations = ", ".join(bucket["operations"])
                return f"Participates in {operations.lower()} processing."
        return "Not specified"

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
                "Pipeline Diagnostics section._"
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
            "",
            "_This count reflects every individually traceable rule (one per source "
            "statement/field, for full auditability). The business report may show a "
            "smaller number, because closely related rules that apply the same pattern "
            "to several fields (e.g. \"reset each of these six DPD fields to zero if "
            "negative\") are presented there as one combined rule for readability. "
            "Every rule counted here is still individually traceable in the Source "
            "Traceability table below - none are dropped, only grouped for display._",
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

    def _findings_section(
        self,
        synthesis: SynthesisResult,
        merged_extraction: Dict[str, Any],
        raw_source: str = "",
        raw_merged_extraction: Optional[Dict[str, Any]] = None,
        raw_synthesis_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Business-relevant findings only: deterministic dead-code /
        disabled-logic detection first (highest signal - these are
        concrete, verifiable facts about the object's actual behavior),
        followed by genuine LLM-flagged ambiguities from the source. Pure
        pipeline/parser/guardrail plumbing noise has moved to
        `_pipeline_diagnostics_section` in the pipeline run log - it
        was drowning out the findings that actually matter to a business
        reader (see report design notes).
        """
        items: List[str] = []

        table_operations = merged_extraction.get("table_operations", []) or []
        dead_tables = find_write_only_temp_tables(table_operations, raw_source=raw_source)
        for table in dead_tables:
            items.append(
                f"**Working table `{table}` appears to be unused.** It is built during "
                "processing but never subsequently read anywhere else in this object - it "
                "has no effect on the final outcome and may be safe to remove, or may "
                "indicate logic that was intended to use it but doesn't."
            )

        source_merged_extraction = raw_merged_extraction or merged_extraction
        source_synthesis_data = raw_synthesis_data or synthesis.data

        # Informational uncertainty is retained in verification metadata, not
        # promoted to a human-review finding unless another validator proves
        # a contradiction or an uncovered executable region.
        merged_ambiguities = source_merged_extraction.get("ambiguities", []) or []
        items.extend(
            str(item).strip()
            for item in merged_ambiguities
            if str(item).strip() and not self._is_reconciliation_diagnostic(item)
        )
        for chunk in source_merged_extraction.get("chunk_provenance", []) or []:
            if not isinstance(chunk, dict):
                continue
            parse_error = str(chunk.get("parse_error") or "").strip()
            if not parse_error:
                continue
            chunk_id = str(chunk.get("chunk_id") or "").strip() or "this chunk"
            chunk_kind = str(chunk.get("chunk_kind") or "").strip()
            if chunk_id == "this chunk":
                items.append(
                    "Automatic extraction for this chunk returned malformed JSON and could not be parsed; "
                    "this chunk needs manual review."
                )
            else:
                suffix = f" ({chunk_kind})" if chunk_kind else ""
                items.append(
                    f"Chunk '{chunk_id}'{suffix} technical extraction returned malformed JSON and needs manual review."
                )
        items.extend(
            str(item).strip()
            for item in (source_synthesis_data.get("ambiguities", []) or [])
            if str(item).strip() and not self._is_reconciliation_diagnostic(item)
        )

        if not items:
            return "## Findings / Needs Review\n\nNone identified."

        deduped = list(dict.fromkeys(items))
        def _finding_sort_key(text: str) -> tuple[int, int]:
            normalized = text.strip().lower()
            if normalized.startswith("automatic extraction for this chunk returned malformed json"):
                return (0, 0)
            if normalized.startswith("chunk '"):
                return (1, 0)
            return (2, 0)

        deduped = sorted(enumerate(deduped), key=lambda pair: (_finding_sort_key(pair[1]), pair[0]))
        ordered_items = [item for _, item in deduped]
        lines = [f"- {item}" for item in ordered_items]
        return "## Findings / Needs Review\n\n" + "\n".join(lines)

    @staticmethod
    def _is_reconciliation_diagnostic(value: Any) -> bool:
        """Keep raw reconciliation classifier output out of business findings.

        The detailed status, record kind, and contradiction explanation remain
        available in the verification diagnostics. The business report should
        contain only source/business findings and plain-language ambiguities.
        """
        text = str(value or "").strip().lower()
        return text.startswith(
            (
                "reconciliation review required:",
                "reconciliation detected a source/report discrepancy:",
            )
        )

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
            return ReportFormatterAgent._humanize_object_name(canonical)
        object_name = str(getattr(ingestion, "object_name", "") or "").strip()
        if object_name and object_name.upper() not in {"UNKNOWN_OBJECT", "UNKNOWN", "NONE"}:
            return ReportFormatterAgent._humanize_object_name(object_name)
        return "Not specified"

    @staticmethod
    def _humanize_object_name(name: str) -> str:
        if "_" not in str(name):
            return str(name)
        parts = re.split(r"[_\s]+", str(name).strip())
        return " ".join(
            part if part.isupper() and len(part) <= 4 else part.capitalize()
            for part in parts
            if part
        )

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
        value = rule.get("rule_name")
        return value if isinstance(value, str) and value.strip() else "Not specified"

    @staticmethod
    def _business_rule_output(rule: Dict[str, Any]) -> str:
        output_field = rule.get("output_field")
        fields = rule.get("fields_affected") or []
        if isinstance(fields, str):
            fields = [fields]
        values = []
        if isinstance(output_field, str) and output_field.strip():
            values.append(output_field.strip())
        if isinstance(fields, list):
            values.extend(str(field).strip() for field in fields if str(field).strip())
        values = list(dict.fromkeys(values))
        if values:
            display_values: List[str] = []
            for value in values:
                display_values.extend(
                    ReportFormatterAgent._field_for_display(part)
                    for part in re.split(r"\s*,\s*", value)
                    if part.strip()
                )
            return ", ".join(dict.fromkeys(display_values))
        return "Not specified"

    @staticmethod
    def _field_for_display(value: Any) -> str:
        """Remove presentation-only alias segments without mutating source data.

        Two-part values such as ``A.Field`` are alias-qualified fields. For
        longer qualified names, preserve the first schema/table path and
        remove only interior one-to-three-letter alias segments, e.g.
        ``schema.Table.A.Field`` -> ``schema.Table.Field``.
        """
        text = str(value or "").strip()
        if not text or "." not in text:
            return text
        parts = text.split(".")
        if len(parts) == 2 and re.fullmatch(r"[A-Za-z]{1,3}", parts[0]):
            return parts[1]
        if len(parts) > 2:
            parts = [parts[0], *(
                part for part in parts[1:-1]
                if not re.fullmatch(r"[A-Za-z]{1,3}", part)
            ), parts[-1]]
        return ".".join(parts)

    @staticmethod
    def _field_references_for_display(value: Any) -> str:
        """Clean dotted field references only while rendering text.

        The underlying LLM/canonical values remain unchanged. Dotted paths
        are handled as units so expressions such as ``A.Field`` and
        ``schema.Table.A.Field`` lose only their alias segment.
        """
        text = str(value or "")
        dotted_path = re.compile(
            r"(?<![A-Za-z0-9_])(?:[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*"
        )
        return dotted_path.sub(
            lambda match: ReportFormatterAgent._field_for_display(match.group(0)), text
        )

    @staticmethod
    def _business_rule_business_meaning(rule: Dict[str, Any]) -> str:
        meaning = rule.get("business_meaning")
        return meaning if isinstance(meaning, str) and meaning.strip() else "Not specified"

    @staticmethod
    def _missing_llm_rule_fields(rule: Dict[str, Any]) -> List[str]:
        missing: List[str] = []
        for key in (
            "rule_name", "business_meaning", "condition", "action",
            "rule_type", "confidence", "validation_status", "source_evidence",
        ):
            value = rule.get(key)
            if value is None or value == "" or value == []:
                missing.append(key)
        if not rule.get("output_field") and not rule.get("fields_affected"):
            missing.append("output_field/fields_affected")
        return missing

    @staticmethod
    def _rule_text_lines(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item)]
        else:
            text = str(value)
            if not text:
                return []
            return [text]

    @staticmethod
    def _decision_logic_rows(rule: Dict[str, Any]) -> List[Dict[str, str]]:
        """Return only the decision rows supplied by the LLM."""
        rows = rule.get("decision_logic_rows")
        if not isinstance(rows, list) or not rows:
            return []
        rendered = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            rendered_row = {
                "condition": row.get("condition", ""),
                "outcome": row.get("outcome", ""),
            }
            if row.get("assignments"):
                rendered_row["assignments"] = row["assignments"]
            rendered.append(rendered_row)
        return rendered

    def _decision_logic_block(self, rows: List[Dict[str, str]]) -> List[str]:
        lines = ["| Condition | Result |", "|---|---|"]
        for row in rows:
            condition = self._escape_table_cell(self._pretty_condition_for_display(row["condition"]))
            results = [self._field_references_for_display(row.get("outcome") or "")]
            assignments = row.get("assignments") or []
            if not isinstance(assignments, list):
                assignments = [assignments]
            results.extend(self._assignment_text(item) for item in assignments if str(item).strip())
            outcome = self._escape_table_cell("; ".join(self._distinct_text(results)))
            lines.append(f"| {condition} | {outcome} |")
        return lines

    @staticmethod
    def _distinct_text(values: List[Any]) -> List[str]:
        """Remove only exact repeated display values; never merge meanings."""
        result: List[str] = []
        seen = set()
        for value in values:
            text = str(value or "").strip()
            if not text:
                continue
            key = re.sub(r"\s+", " ", text).casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(text)
        return result

    @staticmethod
    def _assignment_text(value: Any) -> str:
        if isinstance(value, dict):
            field = value.get("field") or value.get("column") or value.get("target")
            result = value.get("value") or value.get("expression") or value.get("result")
            if field and result:
                return f"{ReportFormatterAgent._field_for_display(field)} := {result}"
        return ReportFormatterAgent._field_references_for_display(value).strip()

    @staticmethod
    def _pretty_condition_for_display(condition: str) -> str:
        """Return the LLM-authored condition without semantic rewriting."""
        return ReportFormatterAgent._field_references_for_display(condition)

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