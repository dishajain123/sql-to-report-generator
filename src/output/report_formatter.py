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
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.ingestion.ingestion import IngestionResult
from src.ir.canonical_ir import CanonicalBusinessIR
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
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
        # Last presentation-boundary safety pass: canonical IR may have been
        # built from an older/cached synthesis result. Reapply deterministic
        # chain and CRUD filters before anything reaches the user-facing
        # report, while keeping verification backed by the full source data.
        display_rules = RuleSynthesizerAgent._apply_authoritative_decision_chains(
            display_rules, merged_extraction
        )
        display_rules = RuleSynthesizerAgent._remove_operation_only_rules(display_rules)
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
        resolved_merged_extraction = ctx["merged_extraction"]
        raw_merged_extraction = ctx["raw_merged_extraction"]
        raw_synthesis_data = ctx["raw_synthesis_data"]

        sections = [
            self._title_block(ingestion, synthesis),
            self._at_a_glance(
                ingestion,
                synthesis,
                consolidated_reads,
                consolidated_writes,
                business_rules_for_display,
                resolved_merged_extraction,
            ),
            self._reconciliation_notice(resolved_merged_extraction),
            self._what_this_does(synthesis, business_rules_for_display, resolved_merged_extraction),
            self._end_to_end_flow(synthesis, business_rules_for_display, resolved_merged_extraction),
            self._business_rules_section(business_rules_for_display),
            self._calculations(synthesis, resolved_merged_extraction),
            self._data_touched_section(consolidated_reads, consolidated_writes, business_rules_for_display),
            self._exception_handling(synthesis, getattr(ingestion, "raw_code", ""), resolved_merged_extraction),
            self._findings_section(
                synthesis,
                resolved_merged_extraction,
                getattr(ingestion, "raw_code", ""),
                raw_merged_extraction=raw_merged_extraction,
                raw_synthesis_data=raw_synthesis_data,
            ),
            self._verification_pointer(verification_filename),
        ]
        sections = [s for s in sections if s and s.strip()]
        return "\n\n".join(sections).strip() + "\n"

    @staticmethod
    def _reconciliation_notice(merged_extraction: Dict[str, Any]) -> str:
        quality = merged_extraction.get("quality") if isinstance(merged_extraction, dict) else {}
        status = str((quality or {}).get("status") or "").upper()
        if status not in {"REVIEW_REQUIRED", "FAIL", "FAILED"}:
            return ""
        return (
            "## Review Required\n\n"
            "The reconciliation stage detected source/report inconsistencies. "
            "Business Rules, Calculations, and Data Touched are provisional and "
            "must not be treated as confirmed until the discrepancies are resolved."
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
        """Assembles the companion verification / traceability artifact:
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
            self._pipeline_diagnostics_section(ingestion, synthesis, extraction_guardrail_warnings or []),
        ]
        sections = [s for s in sections if s and s.strip()]
        return "\n\n".join(sections).strip() + "\n"

    def _pipeline_diagnostics_section(
        self,
        ingestion: IngestionResult,
        synthesis: SynthesisResult,
        extraction_guardrail_warnings: List[str],
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
        if canonical_rules:
            return canonical_rules
        return raw_rules

    def _display_business_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rules = [dict(rule) for rule in rules if isinstance(rule, dict)]
        return self._deduplicate_business_rules(rules)

    @staticmethod
    def _rule_field_signature(rule: Dict[str, Any]) -> frozenset:
        fields = {str(f).strip().lower() for f in (rule.get("fields_affected") or []) if str(f).strip()}
        if fields:
            return frozenset(fields)
        output_field = str(rule.get("output_field") or "").strip().lower()
        return frozenset({output_field}) if output_field else frozenset()

    @staticmethod
    def _meaning_word_set(rule: Dict[str, Any]) -> frozenset:
        text = f"{rule.get('rule_name') or ''} {rule.get('business_meaning') or ''}".lower()
        words = {w for w in re.findall(r"[a-z]{3,}", text) if w not in _STOPWORDS_FOR_RULE_SIMILARITY}
        return frozenset(words)

    @staticmethod
    def _rules_look_like_the_same_concept(rule_a: Dict[str, Any], rule_b: Dict[str, Any]) -> bool:
        """Second gate for merging, alongside field-signature overlap.

        Field overlap alone is NOT a safe merge signal on its own: two
        genuinely different statements in the source can happen to touch
        the same handful of fields (a real production example: a dead
        threshold-cap fragment and the live "reset negative values to
        zero" logic both touch DPD_IntService/DPD_NoCredit/etc, but they
        are not the same rule and must never be merged just because their
        field lists overlap - see report design notes). Require the two
        rules' own business_meaning/rule_name text to also share enough
        vocabulary to plausibly be the same underlying concept, using a
        cheap Jaccard word-overlap check - no external NLP dependency,
        but enough to block the false-merge case above (whose wording
        shares almost no words with the reset-to-zero rule) while still
        allowing genuine near-duplicates (whose wording is close
        paraphrase of each other) to merge.
        """
        words_a = ReportFormatterAgent._meaning_word_set(rule_a)
        words_b = ReportFormatterAgent._meaning_word_set(rule_b)
        if not words_a or not words_b:
            # No usable text to compare on either side - do not merge on
            # field overlap alone; require an explicit signal.
            return False
        overlap = len(words_a & words_b) / len(words_a | words_b)
        return overlap >= 0.25

    @staticmethod
    def _deduplicate_business_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge rules that write to the same field(s) into one.

        This is a defensive, deterministic safety net enforcing the
        synthesis prompt's own "group related conditions that drive the
        same output field into one rule" instruction - upstream steps
        (LLM synthesis, or the deterministic completeness backfill in
        `_augment_rules_from_executable_operations` /
        `_complete_synthesis_from_deterministic_facts` in
        src/synthesis/rule_synthesizer.py) can each independently emit a
        rule for the same field, producing near-duplicate rules with
        slightly different literal SQL text (e.g. an `ISNULL(...)`
        variant and a `COALESCE(...)` variant of the same reset logic,
        or two separate branches of what should be one decision table -
        see report design notes for concrete examples). Rather than try
        to prevent every possible source of duplication upstream, this
        guarantees the *displayed* report never shows two rules for the
        same field(s) regardless of where the duplicate came from.

        Two rules are merged ONLY when BOTH hold:
          1. Their `fields_affected` (or, absent that, `output_field`)
             sets are identical or one is a subset of the other, AND
          2. Their business_meaning/rule_name text shares enough
             vocabulary to plausibly describe the same underlying
             concept (see `_rules_look_like_the_same_concept`).
        Field overlap alone is not sufficient - two structurally
        different statements that happen to touch the same fields (e.g.
        a dead code fragment and a live one covering an overlapping
        field set) must never be silently combined into one rule; that
        would misrepresent what the source actually does, which is worse
        than leaving two separate rules in the report. Merging unions
        eligibility, decision table rows (deduplicated by
        condition+outcome), source evidence, and source chunks; keeps
        the longer/more complete business meaning and rule name; and
        keeps the position of the FIRST occurrence so execution ordering
        from canonical_ir is preserved.
        """
        merged: List[Dict[str, Any]] = []
        signatures: List[frozenset] = []

        for rule in rules:
            sig = ReportFormatterAgent._rule_field_signature(rule)
            match_idx = None
            if sig:
                for i, existing_sig in enumerate(signatures):
                    if not existing_sig:
                        continue
                    fields_overlap = sig == existing_sig or sig <= existing_sig or existing_sig <= sig
                    if fields_overlap and ReportFormatterAgent._rules_look_like_the_same_concept(rule, merged[i]):
                        match_idx = i
                        break
            if match_idx is None:
                merged.append(dict(rule))
                signatures.append(sig)
                continue

            target = merged[match_idx]
            # Distinct branch predicates are separate business outcomes,
            # even when they target the same field and use similar prose.
            # Never merge mutually exclusive or nested paths merely because
            # their field signatures overlap.
            target_condition = ReportFormatterAgent._clean_text(target.get("condition"))
            incoming_condition = ReportFormatterAgent._clean_text(rule.get("condition"))
            if target_condition and incoming_condition and target_condition.lower() != incoming_condition.lower():
                merged.append(dict(rule))
                signatures.append(sig)
                continue
            if target.get("decision_logic_rows") or rule.get("decision_logic_rows"):
                target_rows = ReportFormatterAgent._decision_logic_rows(target)
                incoming_rows = ReportFormatterAgent._decision_logic_rows(rule)
                if target_rows and incoming_rows and target_rows != incoming_rows:
                    merged.append(dict(rule))
                    signatures.append(sig)
                    continue
            # Union the wider field set so a subsequent, even-more-complete
            # duplicate can still match against it.
            signatures[match_idx] = signatures[match_idx] | sig
            target["fields_affected"] = sorted(
                {str(f) for f in (target.get("fields_affected") or [])}
                | {str(f) for f in (rule.get("fields_affected") or [])}
            )
            if len(str(rule.get("business_meaning") or "")) > len(str(target.get("business_meaning") or "")):
                target["business_meaning"] = rule.get("business_meaning")
            if len(str(rule.get("rule_name") or "")) > len(str(target.get("rule_name") or "")):
                target["rule_name"] = rule.get("rule_name")
            target["eligibility"] = ReportFormatterAgent._unique_ordered(
                list(target.get("eligibility") or []) + list(rule.get("eligibility") or [])
            )
            existing_rows = target.get("decision_logic_rows") or []
            incoming_rows = rule.get("decision_logic_rows") or []
            seen_rows = {
                (str(r.get("condition") or ""), str(r.get("outcome") or ""))
                for r in existing_rows
                if isinstance(r, dict)
            }
            for row in incoming_rows:
                if not isinstance(row, dict):
                    continue
                key = (str(row.get("condition") or ""), str(row.get("outcome") or ""))
                if key not in seen_rows:
                    existing_rows.append(row)
                    seen_rows.add(key)
            target["decision_logic_rows"] = existing_rows
            target["source_evidence"] = ReportFormatterAgent._unique_ordered(
                list(target.get("source_evidence") or []) + list(rule.get("source_evidence") or [])
            )
            target["source_chunks"] = ReportFormatterAgent._unique_ordered(
                list(target.get("source_chunks") or []) + list(rule.get("source_chunks") or [])
            )

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
        purpose = str(synthesis.data.get("purpose_summary") or "").strip() or _NOT_DETERMINED
        history_tables = [
            str(row.get("table") or "")
            for row in (consolidated_reads or []) + (consolidated_writes or [])
            if isinstance(row, dict) and _HISTORY_TABLE_PATTERN.search(str(row.get("table") or ""))
        ]
        visible_reads = self._visible_table_count(consolidated_reads)
        visible_writes = self._visible_table_count(consolidated_writes)
        rows = [
            ("Purpose", purpose),
            ("Business rules", str(len(rules))),
            ("Tables read", str(visible_reads)),
            ("Tables written", str(visible_writes)),
            ("Produces audit trail", "Yes — records audit events" if history_tables else "No"),
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
        summary = str(synthesis.data.get("purpose_summary") or "").strip() or _NOT_DETERMINED
        lines = [
            "## What This Does",
            "",
            summary,
        ]
        return "\n".join(lines)

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
        if not steps:
            return f"## Process Flow\n\n_{_NOT_DETERMINED}_"
        lines = [f"{i + 1}. {self._strip_leading_numbering(step)}" for i, step in enumerate(steps)]
        return "## Process Flow\n\n" + "\n".join(lines)

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
        eligibility = self._rule_text_lines(rule.get("eligibility"))
        decision_logic_rows = self._decision_logic_rows(rule)
        tie_handling = self._rule_text_lines(rule.get("tie_priority_handling"))
        default_value = self._rule_text_lines(rule.get("default"))
        when_not_eligible = self._rule_text_lines(rule.get("when_not_eligible"))

        lines = [f"### R{idx} — {rule_name}", ""]
        if output_field != "Not specified":
            lines.append(f"**Applies to:** `{output_field}`")
        # Eligibility rendered per-rule, directly under the fields it
        # gates, rather than pooled into one flat cross-rule list at the
        # top of the report - a reader must never have to cross-reference
        # a separate section to know which conditions gate THIS rule.
        # Ordered decision rows are mutually exclusive alternatives. Their
        # branch predicates must never be rendered as simultaneous
        # eligibility requirements, even if the model copied them there.
        if decision_logic_rows:
            eligibility = []
        if eligibility:
            if len(eligibility) == 1:
                lines.append(f"**Eligibility:** {self._pretty_condition_for_display(eligibility[0])}")
            else:
                lines.append("**Eligibility (all must hold):**")
                lines.extend(f"- {self._pretty_condition_for_display(e)}" for e in eligibility)
        lines.append(f"**Meaning:** {business_meaning}")
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
            field = calculation.get("field") or calculation.get("metric") or "Metric"
            formula = calculation.get("formula") or calculation.get("explanation") or "N/A"
            lines.append(f"- **{field}:** {formula}")
        if not lines:
            return "## Calculations\n\n_None identified._"
        return "## Calculations\n\n" + "\n".join(lines)

    def _exception_handling(
        self,
        synthesis: SynthesisResult,
        raw_source: str = "",
        merged_extraction: Optional[Dict[str, Any]] = None,
    ) -> str:
        summary = synthesis.data.get("exception_handling_summary") or "No explicit failure-path behavior identified."
        summary = re.sub(
            r"(?i)\b(?:continues?|proceeds?)\s+(?:execution|processing)\b",
            "the source does not explicitly state whether processing continues",
            str(summary),
        )
        return f"## Exception Handling\n\n{summary}"

    def _data_touched_section(
        self,
        consolidated_reads: List[Dict[str, Any]],
        consolidated_writes: List[Dict[str, Any]],
        rules: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        reads_by_table = {b["table"].upper(): b for b in consolidated_reads}
        writes_by_table = {b["table"].upper(): b for b in consolidated_writes}
        all_keys = list(OrderedDict.fromkeys(list(writes_by_table.keys()) + list(reads_by_table.keys())))
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
        display_keys = [
            k for k in display_keys
            if not (len(k) <= 3 and k.isalpha() and "." not in k and "_" not in k)
        ]
        if not display_keys:
            return "## Data Touched\n\n_None identified._"

        header = ["| Table | Read/Write | Purpose |", "|---|---|---|"]
        rows: List[str] = []
        for key in display_keys:
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
            rows.append(
                f"| `{self._escape_table_cell(table_name)}` | {rw} | "
                f"{self._escape_table_cell(purpose)} |"
            )

        skipped = len(all_keys) - len(display_keys)
        note = ""
        if skipped:
            note = (
                f"\n\n_{skipped} working/temporary table(s) used only for intermediate calculation "
                "steps are omitted here - see the verification report for the full technical lineage._"
            )
        return "## Data Touched\n\n" + self._render_split_table(header, rows) + note

    @staticmethod
    def _table_purpose_text(
        write_bucket: Optional[Dict[str, Any]],
        read_bucket: Optional[Dict[str, Any]],
        rules: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """One-line business purpose for a table row.

        MUST NEVER be raw SQL. Business rules already carry a clean,
        plain-English `business_meaning` naming exactly what changes and
        why - reuse that instead of falling back to WHERE-clause/filter
        text, which is developer detail with no place in the business
        report (compare the verification report, which does carry the
        full literal predicates for technical review).

        Preference order:
          1. business_meaning of any rule that writes a column in this
             table (fields_affected overlaps this table's target_columns).
          2. business_meaning of any rule that reads from this table.
          3. the literal columns touched, framed as plain text ("Provides
             <cols>" / "Updates <cols>") - still not raw SQL, just a
             last-resort fact when no rule could be matched.
          4. "Not specified" - never a fabricated purpose.
        """
        for bucket in (write_bucket, read_bucket):
            if bucket and bucket.get("target_columns"):
                cols = ", ".join(bucket["target_columns"][:6])
                operations = {str(operation).upper() for operation in bucket.get("operations") or []}
                if "INSERT" in operations:
                    return f"Inserts data into: {cols}"
                if "UPDATE" in operations:
                    return f"Updates: {cols}"
                if "DELETE" in operations:
                    return f"Deletes rows identified by: {cols}"
                return f"Provides: {cols}"
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
        `_pipeline_diagnostics_section` in the verification report - it
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

        items.extend(
            str(item).strip()
            for item in source_merged_extraction.get("semantic_findings", []) or []
            if str(item).strip()
        )
        merged_ambiguities = source_merged_extraction.get("ambiguities", []) or []
        items.extend(str(item).strip() for item in merged_ambiguities if str(item).strip())
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
        items.extend(str(item).strip() for item in (source_synthesis_data.get("ambiguities", []) or []) if str(item).strip())

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
    def _clean_sql_fragment_for_display(text: str) -> str:
        """Deterministic readability cleanup applied to condition/outcome/
        eligibility text at render time only - never touches the
        underlying rule data used for grounding, verification, or the
        audit trail, only what gets printed in the business report.

        Handles the two most common sources of raw-SQL leakage seen in
        real output:

        1. Table-alias prefixes on column references (`A.DPD_IntService`,
           `dpd.DPD_Max`, `DPD.DPD_INTSERVICE`) - the synthesis prompt
           already explicitly forbids printing a raw alias as if it were
           a table name, but the model doesn't always comply for column
           references embedded inside a condition/outcome string. Every
           value that reaches this function is already known to be
           condition/outcome/eligibility text (never a table name - those
           come from `fields_affected`/Data Touched, a different code
           path), so any `<word>.<identifier>` pattern found here is
           structurally a column reference and the prefix is safe to
           drop, keeping just the column name.
        2. `ISNULL(x, y)` / `COALESCE(x, y)` NULL-defaulting wrappers -
           collapsed to just `x`, which preserves the practical meaning
           for a business reader (a NULL value being treated as the
           default) while removing function-call noise. Applied
           iteratively since these can nest.

        This is intentionally conservative: it never rewrites operators,
        never reorders boolean logic, and never invents wording - only
        removes syntax that carries no additional business meaning.
        """
        if not text:
            return text
        cleaned = text
        # Unwrap ISNULL(x, y) / COALESCE(x, y) -> x. Iterate a few passes
        # to handle nesting; bounded so a pathological input can't loop.
        wrapper_pattern = re.compile(r"\b(?:ISNULL|COALESCE)\s*\(\s*([^,()]+?)\s*,\s*[^()]+?\)", re.IGNORECASE)
        for _ in range(4):
            new_cleaned = wrapper_pattern.sub(r"\1", cleaned)
            if new_cleaned == cleaned:
                break
            cleaned = new_cleaned
        # Strip alias prefixes on column references: <word>.<identifier> -> <identifier>.
        # Deliberately does not fire on things that aren't alias.column
        # shaped (e.g. leaves quoted string literals and numbers alone).
        cleaned = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\.([A-Za-z_][A-Za-z0-9_]*)\b", r"\1", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        return cleaned or text

    @staticmethod
    def _rule_text_lines(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            text = str(value).strip()
            if not text:
                return []
            items = [part.strip(" -") for part in re.split(r"(?:\n+|;\s+)", text) if part.strip(" -")] or [text]
        return [ReportFormatterAgent._clean_sql_fragment_for_display(item) for item in items]

    def _decision_logic_rows(self, rule: Dict[str, Any]) -> List[Dict[str, str]]:
        """Return exact condition/outcome rows for this business rule.

        Explicit single-branch rules are rendered as one table row too. This
        keeps the report shape consistent and makes the condition/outcome
        binding visible instead of leaving it only in prose.
        """
        rows = rule.get("decision_logic_rows")
        if not isinstance(rows, list) or not rows:
            condition = str(rule.get("condition") or "").strip()
            action = str(rule.get("action") or "").strip()
            if condition and action:
                return [{"condition": condition, "outcome": action}]
            return []
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            condition = str(row.get("condition") or row.get("when") or row.get("if") or "").strip()
            outcome = str(row.get("outcome") or row.get("then") or row.get("result") or "").strip()
            if condition or outcome:
                # "ELSE" is a structural marker for the default branch,
                # not a SQL fragment - leave it exactly as-is rather than
                # running it through alias/wrapper cleanup.
                clean_condition = (
                    condition if condition.strip().upper() == "ELSE"
                    else self._clean_sql_fragment_for_display(condition)
                )
                normalized.append(
                    {
                        "condition": clean_condition or "Not specified",
                        "outcome": self._clean_sql_fragment_for_display(outcome) or "Not specified",
                    }
                )
        # Repeated field-level cleanup assignments are one business pattern,
        # not several different decisions. Collapse only the unambiguous
        # shape "<metric> < 0 -> 0" when the rule itself is explicitly about
        # reset/cleanup. The original rows remain intact in the verification
        # artifact and in the rule payload.
        rule_text = " ".join(
            str(rule.get(key) or "").lower()
            for key in ("rule_name", "action", "business_meaning")
        )
        reset_rows = [
            row for row in normalized
            if re.search(r"(?:<\s*0|negative)", row["condition"], re.IGNORECASE)
            and re.fullmatch(r"['\"]?0['\"]?", row["outcome"].strip())
        ]
        if len(reset_rows) >= 2 and any(
            token in rule_text for token in ("reset", "sanitize", "cleanup", "zero out", "set to zero")
        ):
            return [{"condition": "Metric value < 0", "outcome": "Metric set to 0"}]
        return normalized

    def _decision_logic_block(self, rows: List[Dict[str, str]]) -> List[str]:
        lines = ["| Condition | Outcome |", "|---|---|"]
        for row in rows:
            lines.append(
                f"| {self._escape_table_cell(self._pretty_condition_for_display(row['condition']))} | {self._escape_table_cell(row['outcome'])} |"
            )
        return lines

    @staticmethod
    def _pretty_condition_for_display(condition: str) -> str:
        """Make common SQL predicates readable without changing their meaning.

        This is deliberately a presentation-only transformation. Raw
        conditions remain in synthesis/reconciliation/verification data; the
        business report simply avoids exposing null wrappers, aliases, and
        operator-heavy syntax when a faithful plain-language equivalent is
        unambiguous.
        """
        text = ReportFormatterAgent._clean_sql_fragment_for_display(str(condition or "").strip())
        if not text or text.upper() == "ELSE":
            return text
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\bBETWEEN\s+([^\s]+)\s+AND\s+([^\s]+)", r"is between \1 and \2", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*>=\s*", " is at least ", text)
        text = re.sub(r"\s*<=\s*", " is at most ", text)
        text = re.sub(r"\s*<>\s*", " is not ", text)
        text = re.sub(r"\s*!=\s*", " is not ", text)
        text = re.sub(r"\s+>\s*", " is above ", text)
        text = re.sub(r"\s+<\s*", " is below ", text)
        text = re.sub(r"\s*=\s*", " equals ", text)
        text = re.sub(r"\s+AND\s+", " and ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+OR\s+", " or ", text, flags=re.IGNORECASE)
        return text.strip()

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
