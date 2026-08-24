"""
agents/report_formatter.py
----------------------------
Report Formatter Agent.

Pure, deterministic assembly stage (no LLM call). Takes:
    - the IngestionResult (object metadata, parameters, parse warnings)
    - the merged technical extraction (tables read/written etc.)
    - the SynthesisResult (business rules, purpose summary, calculations)

...and renders the single final Markdown report, strictly following
the required output structure. Any ambiguity signal from any upstream
stage (parse warnings, malformed-JSON fallbacks, jargon flags, or
LLM-identified ambiguities) is merged into one explicit, never-silent
"Ambiguities / Needs Review" section.
"""

from __future__ import annotations

from typing import Any, Dict, List

from agents.ingestion import IngestionResult
from agents.rule_synthesizer import SynthesisResult


class ReportFormatterAgent:
    """Assembles the final Markdown business logic report."""

    def format(
        self,
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis: SynthesisResult,
    ) -> str:
        sections = [
            self._object_overview(ingestion),
            self._purpose_summary(synthesis),
            self._tables_read(merged_extraction),
            self._tables_written(merged_extraction),
            self._step_by_step_flow(synthesis),
            self._business_rules(synthesis),
            self._calculations(synthesis),
            self._exception_handling(synthesis),
            self._ambiguities(ingestion, synthesis),
        ]
        return "\n\n".join(sections).strip() + "\n"

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _object_overview(self, ingestion: IngestionResult) -> str:
        lines = [
            "## Object Overview",
            "",
            f"- **Object Name:** `{ingestion.object_name}`",
            f"- **Object Type:** {ingestion.object_type.replace('_', ' ').title()}",
        ]
        if ingestion.parameters:
            lines.append("- **Parameters:**")
            lines.append("")
            lines.append("| Parameter | Direction | Datatype |")
            lines.append("|---|---|---|")
            for p in ingestion.parameters:
                lines.append(f"| `{p.name}` | {p.direction} | {p.datatype} |")
        else:
            lines.append("- **Parameters:** None")
        return "\n".join(lines)

    def _purpose_summary(self, synthesis: SynthesisResult) -> str:
        summary = synthesis.data.get("purpose_summary") or (
            "Purpose could not be confidently synthesized - see Ambiguities section."
        )
        return f"## Purpose Summary\n\n{summary}"

    def _tables_read(self, merged_extraction: Dict[str, Any]) -> str:
        rows = merged_extraction.get("tables_read", [])
        header = "| Table Name | Business Context | Filter Conditions |\n|---|---|---|"
        if not rows:
            return "## Tables Read\n\n_None identified._"
        body = []
        seen = set()
        for r in rows:
            table = r.get("table", "Unknown")
            columns = ", ".join(r.get("columns", []) or []) or "N/A"
            filt = r.get("filter_condition") or "No filter / full read"
            key = (table, filt)
            if key in seen:
                continue
            seen.add(key)
            body.append(f"| `{table}` | Columns referenced: {columns} | {filt} |")
        return "## Tables Read\n\n" + header + "\n" + "\n".join(body)

    def _tables_written(self, merged_extraction: Dict[str, Any]) -> str:
        rows = merged_extraction.get("tables_written", [])
        header = (
            "| Table Name | Operation Type | Columns Affected | Business Trigger |\n"
            "|---|---|---|---|"
        )
        if not rows:
            return "## Tables Written\n\n_None identified._"
        body = []
        seen = set()
        for r in rows:
            table = r.get("table", "Unknown")
            op = r.get("operation", "Unknown")
            # "columns" may be absent on extractions produced before this
            # field existed - fall back gracefully instead of erroring.
            columns = ", ".join(r.get("columns", []) or []) or "Not identified"
            trigger = r.get("trigger_condition") or "Always, on each execution"
            key = (table, op, trigger)
            if key in seen:
                continue
            seen.add(key)
            body.append(f"| `{table}` | {op} | {columns} | {trigger} |")
        return "## Tables Written\n\n" + header + "\n" + "\n".join(body)

    def _step_by_step_flow(self, synthesis: SynthesisResult) -> str:
        steps: List[str] = synthesis.data.get("step_by_step_flow", [])
        if not steps:
            return "## Step-by-Step Logic Flow\n\n_Could not be confidently reconstructed - see Ambiguities section._"
        lines = [f"{i + 1}. {step}" for i, step in enumerate(steps)]
        return "## Step-by-Step Logic Flow\n\n" + "\n".join(lines)

    def _business_rules(self, synthesis: SynthesisResult) -> str:
        rules = synthesis.data.get("business_rules", [])
        if not rules:
            return "## Business Rules / Validations\n\n_None identified._"
        header = "| Condition | Resulting Action | Fields Affected |\n|---|---|---|"
        body = []
        for r in rules:
            # "fields_affected" may be absent on synthesis results produced
            # before this field existed - fall back gracefully instead of
            # erroring, rather than assuming the key is always present.
            fields = r.get("fields_affected") or []
            fields_display = ", ".join(fields) if fields else "None (no data written)"
            body.append(
                f"| {r.get('condition', 'N/A')} | {r.get('action', 'N/A')} | {fields_display} |"
            )
        return "## Business Rules / Validations\n\n" + header + "\n" + "\n".join(body)

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

    def _ambiguities(self, ingestion: IngestionResult, synthesis: SynthesisResult) -> str:
        items: List[str] = []
        items.extend(ingestion.parse_warnings)
        items.extend(synthesis.data.get("ambiguities", []) or [])
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

        # de-duplicate while preserving order
        deduped = list(dict.fromkeys(items))
        lines = [f"- {item}" for item in deduped]
        return "## Ambiguities / Needs Review\n\n" + "\n".join(lines)