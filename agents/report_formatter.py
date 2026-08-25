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
"""

from __future__ import annotations

from collections import OrderedDict
import re
from typing import Any, Dict, List, Optional

from agents.ingestion import IngestionResult
from agents.rule_synthesizer import SynthesisResult


class ReportFormatterAgent:
    """Assembles the final Markdown business logic report."""

    def format(
        self,
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis: SynthesisResult,
        extraction_guardrail_warnings: Optional[List[str]] = None,
    ) -> str:
        sections = [
            self._object_overview(ingestion),
            self._purpose_summary(synthesis),
            self._tables_read(merged_extraction),
            self._tables_written(merged_extraction),
            self._step_by_step_flow(synthesis),
            self._business_rules(ingestion, merged_extraction, synthesis),
            self._calculations(synthesis),
            self._exception_handling(synthesis),
            self._validation_summary(synthesis),
            self._ambiguities(ingestion, synthesis, extraction_guardrail_warnings or []),
        ]
        return "\n\n".join(sections).strip() + "\n"

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _object_overview(self, ingestion: IngestionResult) -> str:
        dialect_label = "Oracle SQL / PL-SQL" if ingestion.dialect == "oracle" else "SQL Server T-SQL"
        object_name = self._display_object_name(ingestion)
        object_type = self._display_object_type(ingestion.object_type)
        lines = [
            "## Object Overview",
            "",
            f"- **Object Name:** `{object_name}`",
            f"- **Object Type:** {object_type}",
            f"- **SQL Dialect:** {dialect_label}",
        ]
        if getattr(ingestion, "parameter_parse_status", "parameterless") == "failed":
            lines.append("- **Parameters:** Not specified (extraction failed / Needs Review)")
        elif ingestion.parameters:
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
        if not rows:
            return "## Tables Read\n\n_None identified._"
        header = (
            "| Table Name | Business Context | Filter Conditions |\n"
            "|---|---|---|"
        )
        body = [self._render_table_read_row(r) for r in rows]
        return "## Tables Read\n\n" + header + "\n" + "\n".join(body)

    def _tables_written(self, merged_extraction: Dict[str, Any]) -> str:
        rows = merged_extraction.get("tables_written", [])
        if not rows:
            return "## Tables Written\n\n_None identified._"
        header = (
            "| Table Name | Operation Type | Columns Affected | Business Trigger |\n"
            "|---|---|---|---|"
        )
        body = [self._render_table_written_row(r) for r in rows]
        return "## Tables Written\n\n" + header + "\n" + "\n".join(body)

    def _step_by_step_flow(self, synthesis: SynthesisResult) -> str:
        steps: List[str] = synthesis.data.get("step_by_step_flow", [])
        if not steps:
            return "## Step-by-Step Logic Flow\n\n_Could not be confidently reconstructed - see Ambiguities section._"
        lines = [f"{i + 1}. {self._strip_leading_numbering(step)}" for i, step in enumerate(steps)]
        return "## Step-by-Step Logic Flow\n\n" + "\n".join(lines)

    def _business_rules(
        self,
        ingestion: IngestionResult,
        merged_extraction: Dict[str, Any],
        synthesis: SynthesisResult,
    ) -> str:
        rules = synthesis.data.get("business_rules", [])
        object_name = self._display_object_name(ingestion)
        purpose = self._business_process_summary(synthesis)

        lines = [
            f"# Business Conditions Report — {object_name}",
            "",
            f"> **What this process does:** {purpose}",
            "",
            "## Glossary",
            "",
            self._glossary_table(ingestion, merged_extraction),
            "",
            "# Business Rules",
            "",
        ]

        if not rules:
            lines.append("_No business rules were identified from the extracted source._")
        else:
            for idx, rule in enumerate(rules, start=1):
                lines.extend(self._render_business_rule_block(idx, rule))
                lines.append("")

        lines.append(self._business_rule_summary_table(rules))
        lines.append("")
        lines.append(self._source_traceability_details(rules, merged_extraction))
        return "\n".join(lines).strip()

    def _render_business_rule_block(self, idx: int, rule: Dict[str, Any]) -> List[str]:
        rule_name = self._business_rule_name(rule, idx)
        status = str(rule.get("validation_status") or "unverified").strip().lower()
        title_suffix = " [Needs Review]" if status != "verified" else ""
        output_field = self._business_rule_output(rule)
        business_meaning = self._business_rule_business_meaning(rule)
        eligibility = self._rule_text_lines(rule.get("eligibility") or rule.get("condition"))
        decision_logic_rows = self._decision_logic_rows(rule)
        tie_handling = self._rule_text_lines(rule.get("tie_priority_handling"))
        default_value = self._rule_text_lines(rule.get("default"))
        when_not_eligible = self._rule_text_lines(rule.get("when_not_eligible"))
        if not when_not_eligible and rule.get("condition") and rule.get("action"):
            when_not_eligible = [
                "When the eligibility condition is not met, the stated outcome does not apply."
            ]
        dependencies = rule.get("dependencies") or []
        dependencies_display = "; ".join(dependencies) if dependencies else "None identified"

        return [
            f"## Rule: {rule_name}{title_suffix}",
            "",
            f"**Applies to:** `{output_field}`",
            f"**Business meaning:** {business_meaning}",
            "",
            "### Eligibility",
        ] + self._bullet_block(eligibility, "No eligibility condition was confidently extracted.") + [
            "",
            "### Decision Logic",
        ] + self._decision_logic_block(decision_logic_rows, rule) + [
            "",
            "### Tie / Priority Handling",
        ] + self._bullet_block(
            tie_handling or self._default_priority_text(rule, idx),
            "No priority ordering was explicitly identified.",
        ) + [
            "",
            "### Default",
        ] + self._bullet_block(default_value, "No source-confirmed default was extracted.") + [
            "",
            "### When Not Eligible",
        ] + self._bullet_block(
            when_not_eligible or "No source-confirmed not-eligible behavior was extracted.",
            "No source-confirmed not-eligible behavior was extracted.",
        ) + [
            "",
            f"**Source Traceability:** see the collapsible mapping below.",
        ]

    def _business_rule_summary_table(self, rules: List[Dict[str, Any]]) -> str:
        lines = [
            "# Business Rule Summary",
            "",
            "| Rule | Output | Business Purpose |",
            "|---|---|---|",
        ]
        for idx, rule in enumerate(rules, start=1):
            name = self._business_rule_name(rule, idx)
            output = self._business_rule_output(rule)
            purpose = self._business_rule_business_meaning(rule)
            lines.append(f"| {name} | `{output}` | {purpose} |")
        return "\n".join(lines)

    def _source_traceability_details(
        self, rules: List[Dict[str, Any]], merged_extraction: Dict[str, Any]
    ) -> str:
        lines = [
            "# Source Traceability",
            "",
            "<details>",
            "<summary><strong>Show rule-to-source mapping</strong></summary>",
            "",
            "| # | Rule | Source Evidence | SQL Statements / Chunks | Technical References | Notes |",
            "|---|---|---|---|---|---|",
        ]
        for idx, rule in enumerate(rules, start=1):
            name = self._business_rule_name(rule, idx)
            evidence = rule.get("source_evidence") or []
            evidence_display = "; ".join(evidence) if evidence else "Not cited"
            source_chunks = rule.get("source_chunks") or []
            source_chunks_display = "; ".join(source_chunks) if source_chunks else "Not cited"
            technical_refs = rule.get("technical_references") or []
            technical_refs_display = "; ".join(
                self._render_technical_reference(ref, merged_extraction) for ref in technical_refs
            ) if technical_refs else "Not cited"
            unresolved = rule.get("unresolved_ambiguities") or []
            notes = "; ".join(unresolved) if unresolved else (
                "Verified"
                if str(rule.get("validation_status") or "unverified").lower() == "verified"
                else "Needs Review"
            )
            lines.append(
                f"| {idx} | {name} | {evidence_display} | {source_chunks_display} | "
                f"{technical_refs_display} | {notes} |"
            )
        lines.append("")
        lines.append(
            "_Source evidence is the literal technical text carried through the pipeline; "
            "SQL Statements / Chunks and Technical References point back to the extracted "
            "chunk ids and statement references used by the guardrails._"
        )
        lines.append("</details>")
        return "\n".join(lines)

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

    def _validation_summary(self, synthesis: SynthesisResult) -> str:
        """Technical Implementation vs Business Interpretation split, plus
        a rollup of how many business rules are explicit/inferred/
        assumption and verified/unverified, so a reviewer can triage
        which rules need the closest human scrutiny without reading the
        full table.
        """
        rules = synthesis.data.get("business_rules", [])
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
            "**Technical Implementation:** derived directly from the parsed source "
            "code and the per-chunk technical extraction (conditions, table reads/"
            "writes, calculations) - see Tables Read/Written above.",
            "",
            "**Business Interpretation:** the Purpose Summary, Step-by-Step Logic "
            "Flow, and Business Rules sections translate that technical "
            "implementation into plain business language; the breakdown below shows "
            "how much of that interpretation is a direct restatement versus an "
            "inference or an assumption.",
            "",
            f"- **Total business rules:** {len(rules)}",
            "- **By rule type:** "
            + ", ".join(f"{k} = {v}" for k, v in sorted(type_counts.items())),
            "- **By validation status:** "
            + ", ".join(f"{k} = {v}" for k, v in sorted(status_counts.items())),
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

    def _ambiguities(
        self,
        ingestion: IngestionResult,
        synthesis: SynthesisResult,
        extraction_guardrail_warnings: List[str],
    ) -> str:
        items: List[str] = []
        items.extend(ingestion.parse_warnings)
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
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _display_object_name(ingestion: IngestionResult) -> str:
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
    def _business_process_summary(synthesis: SynthesisResult) -> str:
        summary = str(synthesis.data.get("purpose_summary") or "").strip()
        if summary:
            return summary
        return "This process reviews the extracted database logic and turns it into business-readable conditions and outcomes."

    @staticmethod
    def _business_rule_name(rule: Dict[str, Any], idx: int) -> str:
        name = str(rule.get("rule_name") or rule.get("action") or rule.get("condition") or f"Rule {idx}").strip()
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
        return text if text else "Not specified"

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

    def _bullet_block(self, value: Any, fallback: str) -> List[str]:
        items = self._rule_text_lines(value)
        if not items:
            return [f"- {fallback}"]
        return [f"- {item}" for item in items]

    def _decision_logic_rows(self, rule: Dict[str, Any]) -> List[Dict[str, str]]:
        rows = rule.get("decision_logic_rows")
        if isinstance(rows, list) and rows:
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
            if normalized:
                return normalized

        condition = str(rule.get("condition") or "").strip()
        outcome = self._business_rule_business_meaning(rule)
        if not condition and outcome == "Not specified":
            return []
        return [{"condition": condition or "Not specified", "outcome": outcome}]

    def _decision_logic_block(self, rows: List[Dict[str, str]], rule: Dict[str, Any]) -> List[str]:
        if rows:
            lines = ["| Condition | Outcome |", "|---|---|"]
            for row in rows:
                lines.append(f"| {row['condition']} | {row['outcome']} |")
            return lines
        fallback_condition = str(rule.get("condition") or "").strip() or "Not specified"
        fallback_outcome = self._business_rule_business_meaning(rule)
        if fallback_condition == "Not specified" and fallback_outcome == "Not specified":
            return ["- No source-confirmed decision logic was extracted."]
        return [f"- {fallback_condition} -> {fallback_outcome}"]

    @staticmethod
    def _default_priority_text(rule: Dict[str, Any], idx: int) -> str:
        if str(rule.get("validation_status") or "unverified").lower() != "verified":
            return "Needs Review"
        return f"Preserve the extracted order of this rule relative to the surrounding rules (rule #{idx})."

    def _glossary_table(self, ingestion: IngestionResult, merged_extraction: Dict[str, Any]) -> str:
        entries = self._build_glossary_entries(ingestion, merged_extraction)
        lines = ["| Term | Business Meaning |", "|---|---|"]
        for term, meaning in entries:
            lines.append(
                f"| {self._escape_table_cell(term)} | {self._escape_table_cell(meaning)} |"
            )
        return "\n".join(lines)

    def _glossary_section(self, ingestion: IngestionResult) -> str:
        """
        Backward-compatible glossary helper for the legacy test contract.

        The production report uses the active-technical-IR glossary table
        rendered through ``_glossary_table``. This helper keeps the older
        direct-raw-source glossary tests working without changing the report
        format used by ``format()``.
        """
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
    def _legacy_glossary_entries(raw_code: str) -> List[tuple[str, str]]:
        text = str(raw_code or "")
        if not text.strip():
            return []

        patterns: List[tuple[str, str, str]] = [
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

        entries: List[tuple[str, str]] = []
        for term, pattern, meaning in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                entries.append((term, meaning))
        return entries

    def _build_glossary_entries(
        self, ingestion: IngestionResult, merged_extraction: Dict[str, Any]
    ) -> List[tuple[str, str]]:
        evidence_map: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

        def register(term: str, *, kind: str, record: Dict[str, Any], detail: str = "") -> None:
            normalized = self._normalize_glossary_term(term)
            if not normalized:
                return
            entry = evidence_map.setdefault(
                normalized,
                {
                    "display_term": self._clean_text(term),
                    "kinds": [],
                    "tables": [],
                    "operations": [],
                    "occurrences": [],
                    "statements": [],
                    "clauses": [],
                    "expressions": [],
                    "constants": [],
                    "datatypes": [],
                    "directions": [],
                },
            )
            if kind not in entry["kinds"]:
                entry["kinds"].append(kind)
            table = self._clean_identifier(record.get("table"))
            if table and table not in entry["tables"]:
                entry["tables"].append(table)
            operation = self._clean_identifier(record.get("operation"))
            if operation and operation not in entry["operations"]:
                entry["operations"].append(operation)
            statement_text = self._clean_text(
                record.get("source_statement_text") or record.get("statement_text")
            )
            if statement_text and statement_text not in entry["statements"]:
                entry["statements"].append(statement_text)
            target_columns = [
                self._clean_identifier(col) for col in record.get("target_columns", []) or []
            ]
            if target_columns:
                occurrence = {
                    "table": table,
                    "operation": operation,
                    "target_columns": target_columns,
                    "statement_text": statement_text,
                    "clauses": [],
                }
                entry["occurrences"].append(occurrence)
            datatype = self._clean_text(record.get("datatype"))
            if datatype and datatype not in entry["datatypes"]:
                entry["datatypes"].append(datatype)
            direction = self._clean_text(record.get("direction"))
            if direction and direction not in entry["directions"]:
                entry["directions"].append(direction)
            if detail:
                if kind == "constant":
                    if normalized not in entry["constants"]:
                        entry["constants"].append(normalized)
                    if detail not in entry["clauses"]:
                        entry["clauses"].append(detail)
                elif kind in {"parameter", "target_column", "selected_column", "inserted_column", "source_column"}:
                    if detail not in entry["clauses"]:
                        entry["clauses"].append(detail)
                elif self._looks_like_expression(detail):
                    if detail not in entry["expressions"]:
                        entry["expressions"].append(detail)
                else:
                    if detail not in entry["clauses"]:
                        entry["clauses"].append(detail)

            if detail and entry["occurrences"]:
                entry["occurrences"][-1]["clauses"].append(detail)

        active_records = self._active_technical_records(ingestion, merged_extraction)
        parameter_names = [getattr(p, "name", "") for p in getattr(ingestion, "parameters", []) or []]

        for param in getattr(ingestion, "parameters", []) or []:
            register(
                getattr(param, "name", ""),
                kind="parameter",
                record={
                    "datatype": getattr(param, "datatype", ""),
                    "direction": getattr(param, "direction", ""),
                },
            )

        for section, record in active_records:
            table = self._clean_identifier(record.get("table"))
            operation = self._clean_identifier(record.get("operation"))
            statement_text = self._clean_text(
                record.get("source_statement_text") or record.get("statement_text")
            )
            where_predicate = self._clean_text(
                record.get("where_predicate") or record.get("filter_condition")
            )
            having_predicate = self._clean_text(record.get("having_predicate"))
            trigger_condition = self._clean_text(record.get("trigger_condition"))
            join_predicates = self._join_predicate_texts(record.get("join_predicates") or [])
            exists_predicates = self._exists_predicate_texts(record.get("exists_predicates") or [])
            clauses = [text for text in [where_predicate, having_predicate, trigger_condition] if text]
            clauses.extend(join_predicates)
            clauses.extend(exists_predicates)

            for clause in clauses:
                for clause_term in self._extract_clause_terms(clause):
                    register(clause_term, kind="predicate_term", record=record, detail=clause)

            if section == "table_operations":
                operation_kind = operation.upper() if operation else ""
                if operation_kind == "READ":
                    target_kind = "selected_column"
                elif operation_kind == "INSERT":
                    target_kind = "inserted_column"
                else:
                    target_kind = "target_column"

                for column in record.get("target_columns", []) or []:
                    detail = self._summarize_column_usage(
                        column=column,
                        operation=operation,
                        table=table,
                        statement_text=statement_text,
                        record=record,
                        role=target_kind,
                    )
                    register(column, kind=target_kind, record=record, detail=detail)
                if operation_kind != "READ":
                    for column in record.get("source_columns", []) or []:
                        detail = self._summarize_column_usage(
                            column=column,
                            operation=operation,
                            table=table,
                            statement_text=statement_text,
                            record=record,
                            role="source_column",
                        )
                        register(column, kind="source_column", record=record, detail=detail)
                for constant in record.get("constants", []) or []:
                    detail = self._summarize_constant_usage(
                        constant=constant,
                        operation=operation,
                        table=table,
                        record=record,
                        statement_text=statement_text,
                    )
                    register(constant, kind="constant", record=record, detail=detail)

                for param_name in parameter_names:
                    if not self._term_mentioned_in_text(param_name, statement_text):
                        continue
                    detail = self._summarize_parameter_usage(
                        param_name=param_name,
                        operation=operation,
                        table=table,
                        record=record,
                        clauses=clauses,
                        statement_text=statement_text,
                    )
                    register(param_name, kind="parameter", record=record, detail=detail)

            elif section in {"conditions", "calculations"}:
                detail = self._summarize_statement_item(
                    section=section,
                    record=record,
                    statement_text=statement_text,
                )
                candidate_terms = [
                    record.get("metric"),
                    record.get("result"),
                ]
                if section == "calculations" and not any(candidate_terms):
                    candidate_terms.append(record.get("formula"))
                for term in candidate_terms:
                    if term and self._normalize_glossary_term(term):
                        register(str(term), kind=section[:-1], record=record, detail=detail)

                for param_name in parameter_names:
                    if self._term_mentioned_in_text(param_name, statement_text):
                        detail = self._summarize_parameter_usage(
                            param_name=param_name,
                            operation=operation,
                            table=table,
                            record=record,
                            clauses=clauses,
                            statement_text=statement_text,
                        )
                        register(param_name, kind="parameter", record=record, detail=detail)

        ordered_entries: List[tuple[str, str]] = []
        for term, evidence in evidence_map.items():
            meaning = self._summarize_glossary_term(term, evidence)
            if meaning:
                ordered_entries.append((evidence.get("display_term") or term, meaning))
        return ordered_entries

    @staticmethod
    def _active_technical_records(
        ingestion: IngestionResult, merged_extraction: Dict[str, Any]
    ) -> List[tuple[str, Dict[str, Any]]]:
        records: List[tuple[str, Dict[str, Any]]] = []
        table_operations = merged_extraction.get("table_operations") or []
        if table_operations:
            for item in table_operations:
                if isinstance(item, dict) and ReportFormatterAgent._is_active_record(item):
                    records.append(("table_operations", item))
        else:
            for section in ("tables_read", "tables_written"):
                for item in merged_extraction.get(section, []) or []:
                    if isinstance(item, dict) and ReportFormatterAgent._is_active_record(item):
                        records.append((section, item))

        for section in ("conditions", "calculations"):
            for item in merged_extraction.get(section, []) or []:
                if isinstance(item, dict) and ReportFormatterAgent._is_active_record(item):
                    records.append((section, item))
        return records

    @staticmethod
    def _is_active_record(record: Dict[str, Any]) -> bool:
        active_status = str(record.get("active_status") or record.get("source_active_status") or "").strip().upper()
        if active_status and active_status not in {"ACTIVE", "YES", "Y", "TRUE"}:
            return False
        if str(record.get("source_parse_error") or "").strip():
            return False
        if str(record.get("parse_error") or "").strip():
            return False
        return True

    @staticmethod
    def _clean_text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @staticmethod
    def _clean_identifier(value: Any) -> str:
        text = re.sub(r'[\[\]"`]', "", str(value or "")).strip()
        return text

    @staticmethod
    def _looks_like_expression(text: Any) -> bool:
        cleaned = ReportFormatterAgent._clean_text(text).upper()
        if not cleaned:
            return False
        return any(
            token in cleaned
            for token in (" CASE ", " WHEN ", " THEN ", " ELSE ", " END ", " = ", " > ", " < ", " + ", " - ", " * ", " / ")
        ) or cleaned.startswith("(") or cleaned.endswith(")")

    @staticmethod
    def _normalize_glossary_term(term: Any) -> str:
        text = ReportFormatterAgent._clean_text(term)
        if not text:
            return ""
        if text.upper() == "NULL":
            return ""
        if text.startswith("@"):
            return text.upper()
        if re.fullmatch(r"'(?:''|[^'])*'|\d+(?:\.\d+)?", text):
            return text
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_@#.$]*", text):
            return text.split(".")[-1].upper()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_ ]*[A-Za-z0-9_]", text):
            return text.strip()
        return ""

    @staticmethod
    def _escape_table_cell(text: Any) -> str:
        return str(text or "").replace("|", r"\|").strip()

    @staticmethod
    def _shorten_text(text: Any, max_length: int = 180) -> str:
        cleaned = ReportFormatterAgent._clean_text(text)
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[: max_length - 1].rstrip() + "…"

    @staticmethod
    def _term_mentioned_in_text(term: str, text: str) -> bool:
        normalized_term = ReportFormatterAgent._clean_identifier(term).upper()
        normalized_text = ReportFormatterAgent._clean_identifier(text).upper()
        if not normalized_term or not normalized_text:
            return False
        return re.search(
            r"(?<![A-Z0-9_#@])" + re.escape(normalized_term) + r"(?![A-Z0-9_])",
            normalized_text,
        ) is not None

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

    def _summarize_parameter_usage(
        self,
        *,
        param_name: str,
        operation: str,
        table: str,
        record: Dict[str, Any],
        clauses: List[str],
        statement_text: str,
    ) -> str:
        clause_hits = [clause for clause in clauses if self._term_mentioned_in_text(param_name, clause)]
        if not clause_hits and self._term_mentioned_in_text(param_name, statement_text):
            clause_hits = [statement_text]
        if clause_hits:
            return "; ".join(clause_hits[:2])
        return ""

    def _summarize_constant_usage(
        self,
        *,
        constant: Any,
        operation: str,
        table: str,
        record: Dict[str, Any],
        statement_text: str,
    ) -> str:
        constant_text = self._clean_text(constant)
        target_columns = [self._clean_identifier(col) for col in record.get("target_columns", []) or []]
        where_predicate = self._clean_text(record.get("where_predicate") or record.get("filter_condition"))
        trigger_condition = self._clean_text(record.get("trigger_condition"))
        occurrences = record.get("occurrences") or []
        specific_occurrence = next(
            (
                occ
                for occ in occurrences
                if isinstance(occ, dict)
                and occ.get("operation") in {"UPDATE", "MERGE"}
                and occ.get("target_columns")
            ),
            None,
        )
        if specific_occurrence is None:
            specific_occurrence = next(
                (occ for occ in occurrences if isinstance(occ, dict) and occ.get("target_columns")),
                None,
            )
        if specific_occurrence and constant_text == "0":
            specific_table = specific_occurrence.get("table") or table
            specific_columns = ", ".join(specific_occurrence.get("target_columns") or [])
            if specific_columns:
                return f"Literal reset value used in active update on {specific_table or 'the target table'} for {specific_columns}."
        if specific_occurrence and constant_text in {"'Y'", "'N'", "'A'", "'I'"}:
            specific_table = specific_occurrence.get("table") or table
            specific_columns = ", ".join(specific_occurrence.get("target_columns") or [])
            if specific_columns:
                return f"Flag literal used in active update on {specific_table or 'the target table'} for {specific_columns}."
        if constant_text == "0" and target_columns and operation in {"UPDATE", "MERGE"}:
            columns_text = ", ".join(target_columns)
            return f"Literal reset value used in active {operation.lower()} on {table or 'the target table'} for {columns_text}."
        if constant_text in {"'Y'", "'N'", "'A'", "'I'"} and target_columns:
            columns_text = ", ".join(target_columns)
            return f"Flag literal used in active {operation.lower()} on {table or 'the target table'} for {columns_text}."
        if where_predicate and self._term_mentioned_in_text(constant_text, where_predicate):
            predicate_text = f"Threshold or filter literal used in active predicate `{self._shorten_text(where_predicate)}`."
            if operation in {"UPDATE", "MERGE"} and table:
                predicate_text += f" Target field updated in active SQL on {table}."
            return predicate_text
        if trigger_condition and self._term_mentioned_in_text(constant_text, trigger_condition):
            return f"Trigger literal used in active condition `{self._shorten_text(trigger_condition)}`."
        if self._term_mentioned_in_text(constant_text, statement_text):
            return f"Literal value used in active statement `{self._shorten_text(statement_text)}`."
        return "Literal value used in active SQL."

    def _summarize_column_usage(
        self,
        *,
        column: Any,
        operation: str,
        table: str,
        statement_text: str,
        record: Dict[str, Any],
        role: str,
    ) -> str:
        column_name = self._clean_identifier(column)
        operation_kind = operation.upper()
        clauses = [
            self._clean_text(record.get("where_predicate") or record.get("filter_condition")),
            self._clean_text(record.get("having_predicate")),
            self._clean_text(record.get("trigger_condition")),
        ]
        clauses.extend(self._join_predicate_texts(record.get("join_predicates") or []))
        clauses.extend(self._exists_predicate_texts(record.get("exists_predicates") or []))
        clause_hits = [clause for clause in clauses if self._term_mentioned_in_text(column_name, clause)]
        assignment_expression = self._extract_assignment_expression(statement_text, column_name)
        if role == "selected_column":
            if clause_hits:
                return "; ".join(clause_hits[:2])
            return ""
        if role == "inserted_column":
            return f"Inserted field populated in active INSERT into {table or 'the target table'}."
        if role == "source_column":
            if clause_hits:
                return "; ".join(clause_hits[:2])
            return ""
        if role == "target_column":
            if assignment_expression:
                if "CASE" in assignment_expression.upper():
                    return assignment_expression
                elif re.fullmatch(
                    r"'(?:''|[^'])*'|\d+(?:\.\d+)?|NULL", assignment_expression, flags=re.IGNORECASE
                ):
                    return assignment_expression
                else:
                    return assignment_expression
            if clause_hits:
                return "; ".join(clause_hits[:2])
            return ""
        if clause_hits:
            return "; ".join(clause_hits[:2])
        if self._term_mentioned_in_text(column_name, statement_text):
            return ""
        return ""

    @staticmethod
    def _extract_clause_terms(clause: str) -> List[str]:
        cleaned = ReportFormatterAgent._clean_identifier(clause).upper()
        if not cleaned:
            return []
        candidates = re.findall(r"(?<![A-Z0-9_#@])([A-Z_][A-Z0-9_@$#\.]*)(?![A-Z0-9_])", cleaned)
        stopwords = {
            "AND",
            "OR",
            "NOT",
            "IN",
            "IS",
            "NULL",
            "EXISTS",
            "SELECT",
            "FROM",
            "WHERE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
            "CASE",
            "ON",
            "AS",
            "BETWEEN",
            "LIKE",
            "INNER",
            "LEFT",
            "RIGHT",
            "FULL",
            "OUTER",
            "JOIN",
            "UPDATE",
            "INSERT",
            "DELETE",
            "MERGE",
            "SET",
            "VALUES",
            "GROUP",
            "ORDER",
            "HAVING",
            "BY",
            "INTO",
            "COALESCE",
            "ISNULL",
            "NVL",
            "GETDATE",
            "COUNT",
        }
        terms: List[str] = []
        for candidate in candidates:
            if candidate in stopwords:
                continue
            if re.fullmatch(r"\d+(?:\.\d+)?", candidate):
                continue
            if candidate not in terms:
                terms.append(candidate)
        return terms

    def _summarize_statement_item(
        self, *, section: str, record: Dict[str, Any], statement_text: str
    ) -> str:
        if section == "calculations":
            metric = self._clean_text(record.get("metric") or record.get("result") or "")
            formula = self._clean_text(record.get("formula") or record.get("expression") or "")
            if metric and formula:
                return f"Calculated field `{metric}` is defined by `{self._shorten_text(formula)}`."
            if metric:
                return f"Calculated field `{metric}` appears in the active technical extraction."
            if formula:
                return f"Calculated expression `{self._shorten_text(formula)}` appears in the active technical extraction."
        if section == "conditions":
            condition = self._clean_text(record.get("condition") or "")
            true_branch = self._clean_text(record.get("true_branch") or record.get("result") or "")
            if condition and true_branch:
                return f"Condition `{self._shorten_text(condition)}` leads to `{self._shorten_text(true_branch)}`."
            if condition:
                return f"Condition `{self._shorten_text(condition)}` appears in the active technical extraction."
        return f"Technical item appears in `{self._shorten_text(statement_text)}`."

    @staticmethod
    def _extract_assignment_expression(statement_text: str, column_name: str) -> str:
        if not statement_text or not column_name:
            return ""
        normalized_text = re.sub(r"\s+", " ", statement_text)
        upper_text = normalized_text.upper()
        set_index = upper_text.find(" SET ")
        if set_index == -1:
            set_index = upper_text.find("SET ")
        search_text = normalized_text[set_index + 4 :] if set_index >= 0 else normalized_text
        match = re.search(
            rf"(?is)\b(?:[A-Za-z_][\w\[\]\.]*\.)?{re.escape(column_name)}\b\s*=\s*(.*)",
            search_text,
        )
        if match:
            expr = match.group(1)
            expr = re.split(
                r"(?is)\s*,\s*(?:[A-Za-z_][\w\[\]\.]*\.)?[A-Za-z_][\w\[\]\.]*\b\s*="
                r"|\bFROM\b|\bWHERE\b|\bOUTPUT\b",
                expr,
                maxsplit=1,
            )[0]
            return ReportFormatterAgent._clean_text(expr)
        return ""

    def _summarize_glossary_term(self, term: str, evidence: Dict[str, Any]) -> str:
        kinds = evidence.get("kinds", [])
        tables = evidence.get("tables", [])
        operations = evidence.get("operations", [])
        statements = evidence.get("statements", [])
        clauses = evidence.get("clauses", [])
        expressions = evidence.get("expressions", [])
        constants = evidence.get("constants", [])
        datatypes = evidence.get("datatypes", [])
        occurrences = evidence.get("occurrences", [])

        if "parameter" in kinds or term.startswith("@"):
            fragments: List[str] = []
            if datatypes or evidence.get("directions"):
                descriptor_parts = []
                if evidence.get("directions"):
                    descriptor_parts.append(" / ".join(dict.fromkeys(evidence.get("directions", []))))
                if datatypes:
                    descriptor_parts.append(" / ".join(dict.fromkeys(datatypes)))
                fragments.append(f"Declared as {self._shorten_text(' '.join(descriptor_parts))}.")
            else:
                fragments.append("Declared parameter.")
            usage_texts = clauses or expressions
            if usage_texts:
                fragments.append(
                    "; ".join(f"`{self._shorten_text(text)}`" for text in usage_texts[:2])
                )
            elif operations:
                fragments.append(
                    "Used in active operations: "
                    + ", ".join(dict.fromkeys(op.lower() for op in operations))
                )
            else:
                fragments.append("No explicit active usage was captured in the validated technical IR.")
            return " ".join(fragments).strip()

        if term in constants or "constant" in kinds or re.fullmatch(r"'(?:''|[^'])*'|\d+(?:\.\d+)?", term):
            fragments = []
            if constants:
                fragments.append(
                    "Literal used in active SQL: "
                    + "; ".join(f"`{self._shorten_text(constant)}`" for constant in constants[:2])
                    + "."
                )
            specific_occurrence = None
            if occurrences:
                specific_occurrence = next(
                    (
                        occ
                        for occ in occurrences
                        if occ.get("operation") in {"UPDATE", "MERGE"}
                        and occ.get("target_columns")
                    ),
                    None,
                )
                if specific_occurrence is None:
                    specific_occurrence = next((occ for occ in occurrences if occ.get("target_columns")), None)
            if clauses:
                fragments.append(
                    "Observed in active predicate(s): "
                    + "; ".join(f"`{self._shorten_text(clause)}`" for clause in clauses[:2])
                )
            elif specific_occurrence:
                specific_table = specific_occurrence.get("table") or (tables[0] if tables else "")
                specific_columns = ", ".join(specific_occurrence.get("target_columns") or [])
                if term == "0" and specific_columns:
                    fragments.append(
                        f"Literal reset value used in active update on {specific_table or 'the target table'} for {specific_columns}."
                    )
                elif specific_occurrence.get("operation") in {"UPDATE", "MERGE"} and specific_columns:
                    fragments.append(
                        f"Used as an active value in {specific_occurrence.get('operation')} on {specific_table or 'the target table'}."
                    )
                elif specific_occurrence.get("operation") in {"UPDATE", "MERGE"} and tables:
                    fragments.append(
                        f"Used as an active value in {specific_occurrence.get('operation')} on {', '.join(dict.fromkeys(tables))}."
                    )
                else:
                    fragments.append(
                        "Used as an active literal in "
                        + ", ".join(dict.fromkeys(op.lower() for op in operations))
                        + "."
                    )
            return " ".join(fragments).strip() or "Literal value used in active SQL."

        fragments = []
        if "target_column" in kinds:
            assignment_expression = ""
            for statement in statements:
                assignment_expression = self._extract_assignment_expression(statement, term)
                if assignment_expression:
                    break
            if any("CASE" in expr.upper() for expr in expressions) or "CASE" in assignment_expression.upper():
                fragments.append(
                    "Calculated field updated in active SQL using `CASE`"
                    + (f" on {', '.join(dict.fromkeys(tables))}" if tables else "")
                    + (f": `{self._shorten_text(assignment_expression)}`" if assignment_expression else "")
                    + "."
                )
            elif assignment_expression:
                fragments.append(
                    "Target field updated in active SQL"
                    + (f" on {', '.join(dict.fromkeys(tables))}" if tables else "")
                    + f" from `{self._shorten_text(assignment_expression)}`."
                )
            elif expressions:
                fragments.append(
                    "Target field updated in active SQL from "
                    + "; ".join(f"`{self._shorten_text(expr)}`" for expr in expressions[:2])
                    + "."
                )
            else:
                fragments.append(
                    "Target field updated in active SQL"
                    + (f" on {', '.join(dict.fromkeys(tables))}" if tables else "")
                    + "."
                )
        if "source_column" in kinds:
            fragments.append(
                "Source field read in active SQL"
                + (f" on {', '.join(dict.fromkeys(tables))}" if tables else "")
                + "."
            )
        if "selected_column" in kinds:
            fragments.append(
                "Source field read in active SQL"
                + (f" from {', '.join(dict.fromkeys(tables))}" if tables else "")
                + "."
            )
            if clauses:
                fragments.append(
                    "Also referenced in active predicate(s): "
                    + "; ".join(f"`{self._shorten_text(clause)}`" for clause in clauses[:2])
                )
        if "predicate_term" in kinds:
            fragments.append(
                "Referenced in active predicate(s): "
                + "; ".join(f"`{self._shorten_text(clause)}`" for clause in clauses[:2])
            )
        if not fragments and clauses:
            fragments.append(
                "Referenced in active predicate(s): "
                + "; ".join(f"`{self._shorten_text(clause)}`" for clause in clauses[:2])
            )
        if not fragments and expressions:
            fragments.append(
                "Appears in active calculation(s): "
                + "; ".join(f"`{self._shorten_text(expr)}`" for expr in expressions[:2])
            )
        if not fragments:
            fragments.append("Referenced in active SQL.")
        return " ".join(fragments).strip()

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
        if section == "tables_read":
            table = item.get("table") or "table not specified"
            statement_id = item.get("source_statement_id") or item.get("statement_id") or "statement not specified"
            target_columns = ", ".join(item.get("target_columns", []) or item.get("columns", []) or []) or "N/A"
            source_columns = ", ".join(item.get("source_columns", []) or []) or "N/A"
            where_predicate = item.get("where_predicate") or item.get("filter_condition") or "None"
            join_predicates = "; ".join(
                self._join_predicate_text(jp) for jp in item.get("join_predicates", []) or []
            ) or "None"
            exists_predicates = "; ".join(
                self._exists_predicate_text(ep) for ep in item.get("exists_predicates", []) or []
            ) or "None"
            having_predicate = item.get("having_predicate") or "None"
            constants = ", ".join(item.get("constants", []) or []) or "None"
            provenance = self._table_provenance_text(item)
            return (
                f"{ref}: {statement_id} | `{table}` | target: {target_columns} | source: {source_columns} | "
                f"WHERE: {where_predicate} | JOIN: {join_predicates} | EXISTS: {exists_predicates} | "
                f"HAVING: {having_predicate} | constants: {constants} | {provenance}"
            )
        if section == "tables_written":
            table = item.get("table") or "table not specified"
            statement_id = item.get("source_statement_id") or item.get("statement_id") or "statement not specified"
            op = item.get("operation") or "operation not specified"
            target_columns = ", ".join(item.get("target_columns", []) or item.get("columns", []) or []) or "N/A"
            source_columns = ", ".join(item.get("source_columns", []) or []) or "N/A"
            where_predicate = item.get("where_predicate") or item.get("trigger_condition") or "None"
            join_predicates = "; ".join(
                self._join_predicate_text(jp) for jp in item.get("join_predicates", []) or []
            ) or "None"
            exists_predicates = "; ".join(
                self._exists_predicate_text(ep) for ep in item.get("exists_predicates", []) or []
            ) or "None"
            having_predicate = item.get("having_predicate") or "None"
            constants = ", ".join(item.get("constants", []) or []) or "None"
            provenance = self._table_provenance_text(item)
            return (
                f"{ref}: {statement_id} | `{table}` | {op} | target: {target_columns} | source: {source_columns} | "
                f"WHERE: {where_predicate} | JOIN: {join_predicates} | EXISTS: {exists_predicates} | "
                f"HAVING: {having_predicate} | constants: {constants} | {provenance}"
            )
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

    @staticmethod
    def _table_provenance_text(item: Dict[str, Any]) -> str:
        provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
        statement_id = item.get("source_statement_id") or item.get("statement_id") or provenance.get("statement_id") or "statement not specified"
        chunk_id = item.get("source_chunk_id") or provenance.get("chunk_id") or "chunk not specified"
        chunk_kind = item.get("source_chunk_kind") or provenance.get("chunk_kind") or "chunk"
        status = provenance.get("statement_parse_status") or item.get("statement_parse_status") or "parsed"
        return f"provenance: {chunk_id}:{chunk_kind} | {statement_id} | parse={status}"

    @staticmethod
    def _join_predicate_text(join_predicate: Any) -> str:
        if not isinstance(join_predicate, dict):
            return str(join_predicate)
        table = join_predicate.get("table") or "table not specified"
        join_type = join_predicate.get("join_type") or "JOIN"
        predicate = join_predicate.get("predicate") or "predicate not specified"
        return f"{join_type} {table} ON {predicate}"

    @staticmethod
    def _exists_predicate_text(exists_predicate: Any) -> str:
        if not isinstance(exists_predicate, dict):
            return str(exists_predicate)
        kind = exists_predicate.get("kind") or "EXISTS"
        predicate = exists_predicate.get("predicate") or "predicate not specified"
        subquery_tables = ", ".join(exists_predicate.get("subquery_tables", []) or []) or "N/A"
        return f"{kind}: {predicate} [tables: {subquery_tables}]"

    def _render_table_operation_row(self, row: Dict[str, Any], include_operation: bool) -> str:
        statement_id = row.get("source_statement_id") or row.get("statement_id") or "statement not specified"
        table = row.get("table") or "table not specified"
        alias = row.get("table_alias") or "N/A"
        operation = row.get("operation") or "operation not specified"
        target_columns = ", ".join(row.get("target_columns", []) or row.get("columns", []) or []) or "N/A"
        source_columns = ", ".join(row.get("source_columns", []) or []) or "N/A"
        where_predicate = row.get("where_predicate") or row.get("filter_condition") or "None"
        join_predicates = "; ".join(
            self._join_predicate_text(jp) for jp in row.get("join_predicates", []) or []
        ) or "None"
        exists_predicates = "; ".join(
            self._exists_predicate_text(ep) for ep in row.get("exists_predicates", []) or []
        ) or "None"
        having_predicate = row.get("having_predicate") or "None"
        constants = ", ".join(row.get("constants", []) or []) or "None"
        active_status = row.get("active_status") or "ACTIVE"
        provenance = self._table_provenance_text(row)
        if include_operation:
            return (
                f"| `{statement_id}` | `{table}` | `{operation}` | {target_columns} | {source_columns} | "
                f"{where_predicate} | {join_predicates} | {exists_predicates} | {having_predicate} | "
                f"{constants} | {active_status} | {provenance} |"
            )
        return (
            f"| `{statement_id}` | `{table}` | {alias} | {target_columns} | {source_columns} | {where_predicate} | "
            f"{join_predicates} | {exists_predicates} | {having_predicate} | {constants} | {active_status} | {provenance} |"
        )

    def _render_table_read_row(self, row: Dict[str, Any]) -> str:
        table = row.get("table") or "table not specified"
        target_columns = ", ".join(row.get("target_columns", []) or row.get("columns", []) or []) or ""
        source_columns = ", ".join(row.get("source_columns", []) or []) or ""
        business_context = target_columns or source_columns or "Not specified"

        where_predicate = row.get("where_predicate") or row.get("filter_condition") or ""
        join_predicates = "; ".join(
            self._join_predicate_text(jp) for jp in row.get("join_predicates", []) or []
        )
        exists_predicates = "; ".join(
            self._exists_predicate_text(ep) for ep in row.get("exists_predicates", []) or []
        )
        having_predicate = row.get("having_predicate") or ""
        filter_parts = [part for part in [where_predicate, join_predicates, exists_predicates, having_predicate] if part]
        filter_conditions = "; ".join(filter_parts) if filter_parts else "None"
        return (
            f"| `{table}` | {self._escape_table_cell(business_context)} | "
            f"{self._escape_table_cell(filter_conditions)} |"
        )

    def _render_table_written_row(self, row: Dict[str, Any]) -> str:
        table = row.get("table") or "table not specified"
        operation = row.get("operation") or "operation not specified"
        target_columns = ", ".join(row.get("target_columns", []) or row.get("columns", []) or []) or "Not identified"
        where_predicate = row.get("where_predicate") or row.get("filter_condition") or row.get("trigger_condition") or ""
        join_predicates = "; ".join(
            self._join_predicate_text(jp) for jp in row.get("join_predicates", []) or []
        )
        exists_predicates = "; ".join(
            self._exists_predicate_text(ep) for ep in row.get("exists_predicates", []) or []
        )
        having_predicate = row.get("having_predicate") or ""
        trigger_parts = [part for part in [where_predicate, join_predicates, exists_predicates, having_predicate] if part]
        business_trigger = "; ".join(trigger_parts) if trigger_parts else "None"
        return (
            f"| `{table}` | `{operation}` | {self._escape_table_cell(target_columns)} | "
            f"{self._escape_table_cell(business_trigger)} |"
        )
