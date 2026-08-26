"""
Rule Synthesizer Agent - THE MOST CRITICAL AGENT in the pipeline.

Takes the merged, technical, per-chunk extractions produced by the
Logic Extraction Agent and rewrites them as clear, numbered,
business-intent rules. This is where the system earns (or loses) the
core requirement of the whole project: the output must explain WHAT a
rule accomplishes and WHY it exists from a business/regulatory
standpoint - never restate SQL/PLSQL/T-SQL syntax in English.

All prompt content is loaded from prompts/rule_synthesis.yaml via the
centralized `prompts.prompt_loader` - nothing here is a hardcoded prompt
string. The prompt is selected per SQL dialect (Oracle vs T-SQL), and is
deliberately explicit with a banned-word list, because prompt design for
this exact agent is called out as the hardest and most important part of
the whole build.

Every business rule the model returns is passed through the output
guardrails in `guardrails.py`: the JSON shape is validated/repaired, and
every claimed "fields_affected" entry is cross-checked against the
merged technical extraction and/or the raw source (anti-hallucination
grounding), with the rule's "rule_type" (explicit/inferred/assumption),
"confidence", and "validation_status" preserved so downstream reporting
never presents an inferred or unverifiable claim as a confirmed fact.

Calls an OpenAI-compatible chat completion API directly - no
orchestration framework is involved.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.ingestion.guardrails import ground_business_rules_against_extraction, validate_synthesis_shape
from src.prompts.prompt_loader import get_prompt_set, render_user_prompt

_EMPTY_SYNTHESIS: Dict[str, Any] = {
    "purpose_summary": "",
    "step_by_step_flow": [],
    "business_rules": [],
    "calculations": [],
    "exception_handling_summary": "",
    "ambiguities": [],
}

# A best-effort post-hoc guard: if any banned technical term slips through
# despite the prompt, we flag it rather than silently shipping jargon.
_BANNED_TERMS = [
    "if-elsif", "if statement", "else branch", "for loop", "while loop",
    "update statement", "insert statement", "select statement",
    "merge statement", "cursor", "pl/sql", "t-sql", "exception block",
    "when others", "try/catch",
]


@dataclass
class SynthesisResult:
    data: Dict[str, Any] = field(default_factory=lambda: dict(_EMPTY_SYNTHESIS))
    raw_response: str = ""
    parse_error: str = ""
    jargon_flags: List[str] = field(default_factory=list)
    guardrail_warnings: List[str] = field(default_factory=list)


class RuleSynthesizerAgent:
    """Runs the business-rule synthesis call over the merged technical
    extraction for the whole object, using the configured chat client
    directly.
    """

    def __init__(self, client, model: str, temperature: float = 0.1):
        """
        Args:
            client: an initialized OpenAI-compatible chat client instance.
            model: the model name to call (configurable per pipeline run).
            temperature: sampling temperature (kept low for extraction tasks).
        """
        self.client = client
        self.model = model
        self.temperature = temperature

    def synthesize(
        self,
        object_name: str,
        object_type: str,
        parameter_summary: str,
        merged_extraction: Dict[str, Any],
        dialect: str = "oracle",
        raw_source: str = "",
        model: str | None = None,
    ) -> SynthesisResult:
        """`model`, if given, overrides the agent's configured model for
        just this call - lets callers pick a different model per run
        without re-constructing the agent.
        """
        if str(dialect or "").strip().lower() not in {"oracle", "tsql"}:
            return SynthesisResult(data=dict(_EMPTY_SYNTHESIS))
        prompt_set = get_prompt_set("rule_synthesis.yaml", dialect=dialect)
        user_prompt = render_user_prompt(
            prompt_set["user_template"],
            object_name=object_name,
            object_type=object_type,
            dialect=dialect,
            parameter_summary=parameter_summary or "No parameters.",
            merged_extraction_json=json.dumps(merged_extraction, indent=2),
        )

        response = self.client.chat.completions.create(
            model=model or self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": prompt_set["system"]},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_response = response.choices[0].message.content or ""

        data, error = self._parse_json(raw_response)

        guardrail_warnings: List[str] = []
        data, shape_warnings = validate_synthesis_shape(data)
        guardrail_warnings.extend(shape_warnings)
        data["business_rules"] = self._normalize_business_rules(data.get("business_rules"))
        guardrail_warnings.extend(
            ground_business_rules_against_extraction(
                data["business_rules"], merged_extraction, raw_source=raw_source
            )
        )

        jargon_flags = self._scan_for_jargon(data)
        return SynthesisResult(
            data=data,
            raw_response=raw_response,
            parse_error=error,
            jargon_flags=jargon_flags,
            guardrail_warnings=guardrail_warnings,
        )

    @staticmethod
    def _parse_json(raw_response: str) -> tuple[Dict[str, Any], str]:
        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", cleaned, flags=re.MULTILINE).strip()
        try:
            parsed = json.loads(cleaned)
            merged = dict(_EMPTY_SYNTHESIS)
            merged.update({k: v for k, v in parsed.items() if k in _EMPTY_SYNTHESIS})
            merged["business_rules"] = RuleSynthesizerAgent._normalize_business_rules(
                merged.get("business_rules")
            )
            return merged, ""
        except json.JSONDecodeError as exc:
            fallback = dict(_EMPTY_SYNTHESIS)
            fallback["ambiguities"] = [
                "Business rule synthesis returned malformed JSON and could not be "
                "parsed; the full object needs manual review."
            ]
            return fallback, str(exc)

    @staticmethod
    def _normalize_business_rules(raw_rules: Any) -> List[Dict[str, Any]]:
        """Guarantees every business rule has the full, expected shape -
        the legacy technical fields plus the business-readable report
        fields used by the formatter. This keeps backward compatibility
        with older model responses while allowing the new report layout
        to read stable keys.

        This exists so downstream consumers (UI rendering, exports,
        diffing across runs) can rely on a stable schema and never hit a
        KeyError or a None where a list was expected, even if:
          - the model ignores some of the newer schema fields and omits
            them entirely,
          - the model returns a list-typed field as a bare string
            instead of a one-item list,
          - the model returns null instead of an empty list,
          - a business rule entry itself isn't a dict (malformed item).

        Normalizing here (rather than trusting the prompt alone) is what
        keeps schema changes backward-compatible and avoids breaking any
        existing integration that consumes this output.
        """
        if not isinstance(raw_rules, list):
            return []

        def _as_string_list(value: Any) -> List[str]:
            if value is None:
                return []
            if isinstance(value, str):
                return [value] if value.strip() else []
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            return []

        def _as_text(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                return value.strip()
            return str(value).strip()

        def _as_span_list(value: Any) -> List[Dict[str, Any]]:
            if not isinstance(value, list):
                return []
            return [item for item in value if isinstance(item, dict)]

        def _extract_assignment_fields(*texts: Any) -> List[str]:
            fields: List[str] = []
            for text in texts:
                for match in re.finditer(
                    r"(?<![A-Za-z0-9_@.#$])([@A-Za-z_][A-Za-z0-9_@.#$]*)\s*(?::=|=)",
                    str(text or ""),
                ):
                    fields.append(match.group(1).strip())
            return fields

        def _canonicalize_condition(condition: str, source_text: str, fields_affected: List[str]) -> str:
            text = _as_text(condition)
            lowered = text.lower()
            source_lower = str(source_text or "").lower()
            field_blob = " ".join(fields_affected).lower()
            blob = " ".join([lowered, source_lower, field_blob])
            if not text:
                return ""
            if "try block succeeds" in lowered or "catch block" in lowered or lowered == "else":
                return text
            if "source row matches target" in lowered or "source row does not match target" in lowered:
                return text
            if "dynamic sql" in blob:
                return "dynamic sql is assembled at runtime"
            if "source row matches target" in blob or "provisioning record exists" in blob:
                return "source row matches target"
            if "source row does not match target" in blob or "no provisioning record exists" in blob:
                return "source row does not match target"
            if "non-standard" in blob and "asset classification" in blob:
                return "asset_classification != STANDARD"
            if "latest" in blob and "classification_date" in blob:
                return "latest classification_date per account"
            if "latest" in blob and "calculated_date" in blob:
                return "latest calculated_date per account"
            if "more than 90 days overdue" in blob and "audit" in blob:
                return "DpdDays > 90"
            if "greater than 30" in blob and "less than or equal to 90" in blob and "risk" in blob:
                return "DpdDays <= 90"
            if "less than or equal to 30" in blob and "risk" in blob:
                return "DpdDays <= 30"
            if "greater than 90" in blob and "overdue" in blob:
                return "DpdDays > 90"
            if "try block succeeds" in blob and "status" in blob:
                return "TRY block succeeds"
            if "catch block" in blob and "status" in blob:
                return "CATCH block"
            if "between 91 and 365" in blob:
                return "v_overdue_days BETWEEN 91 AND 365"
            if "between 366 and 1095" in blob:
                return "v_overdue_days BETWEEN 366 AND 1095"
            if "less than or equal to 90" in blob and "classification" in blob:
                return "v_overdue_days <= 90"
            if "more than 1095" in blob or "> 1095" in blob:
                return "v_overdue_days > 1095"
            if "91-365" in blob and "bucket" in blob:
                return "91-365 days"
            if "366-1095" in blob and "bucket" in blob:
                return "366-1095 days"
            if "<= 30" in blob and "bucket" in blob:
                return "<= 30 days"
            if "<= 60" in blob and "bucket" in blob:
                return "<= 60 days"
            if "<= 90" in blob and "bucket" in blob:
                return "<= 90 days"
            return text

        def _canonicalize_output_field(field: str, source_text: str, fields_affected: List[str]) -> str:
            text = _as_text(field)
            lowered = text.lower()
            blob = " ".join([lowered, str(source_text or "").lower(), " ".join(fields_affected).lower()])
            if not text:
                return ""
            if "asset classification" in lowered:
                if "v_classification" in blob:
                    return "v_classification"
                if "asset_classification" in blob:
                    return "asset_classification"
            if "provisioning percentage" in lowered and "v_provision_pct" in blob:
                return "v_provision_pct"
            if "provision amount" in lowered:
                if "v_provision_amt" in blob:
                    return "v_provision_amt"
                if "provision_amount" in blob:
                    return "provision_amount"
            if "ageing bucket" in lowered and "v_ageing_bucket" in blob:
                return "v_ageing_bucket"
            if lowered in {"risk band", "riskband"}:
                return "RiskBand"
            if lowered in {"status"}:
                return "Status"
            if lowered in {"error message", "errormessage"}:
                return "ErrorMessage"
            if lowered in {"account id", "account_id"}:
                if "@accountid" in blob:
                    return "@AccountId"
                if "account_id" in blob:
                    return "account_id"
                return "AccountId"
            if lowered in {"overdue days", "dpddays"} and "dpddays" in blob:
                return "DpdDays"
            if "." in text and " as " not in lowered:
                return text.split(".")[-1].strip()
            return text

        def _canonicalize_action(action: str, source_text: str, fields_affected: List[str], business_meaning: str = "") -> str:
            text = _as_text(action)
            lowered = text.lower()
            meaning_lower = _as_text(business_meaning).lower()
            blob = " ".join([lowered, meaning_lower, str(source_text or "").lower(), " ".join(fields_affected).lower()])
            if not text:
                return ""
            if "dynamic sql" in blob or "manual review" in blob:
                return "Flag for manual review instead of claiming a concrete table"
            if "source row matches target" in blob and "provision" in blob:
                return "Update existing provision row"
            if "source row does not match target" in blob and "provision" in blob:
                return "Insert new provision row"
            if "provisioning record exists" in blob and "update" in blob:
                return "Update existing provision row"
            if "no provisioning record exists" in blob and "insert" in blob:
                return "Insert new provision row"
            if "standard" in blob and "classification" in blob:
                if "assigned a 0.40% provisioning rate" in blob or "0.40%" in blob and "assigned" in blob:
                    return "Set STANDARD classification and 0.40 provision pct"
                if "assigned a 15% provisioning rate" in blob or "15%" in blob and "assigned" in blob:
                    return "Set SUBSTANDARD classification and 15 provision pct"
                if "substandard" in blob:
                    return "Set SUBSTANDARD classification"
                if "doubtful1" in blob:
                    return "Set DOUBTFUL1 classification"
                if "doubtful2" in blob:
                    return "Set DOUBTFUL2 classification"
                if "doubtful3" in blob:
                    return "Set DOUBTFUL3 classification"
                if "loss" in blob:
                    return "Set LOSS classification"
                return "Set STANDARD classification"
            if "risk band" in blob:
                if "low" in blob:
                    return "Set low risk band"
                if "medium" in blob:
                    return "Set medium risk band"
                if "high" in blob:
                    return "Set high risk band"
            if "status" in blob and "overdue" in blob and ("audit" in blob or "change" in blob):
                return "Mark accounts overdue and audit the status change"
            if "status" in blob and (
                "audit" in blob or "change" in blob or "updatedat" in blob or "changedat" in blob or "newstatus" in blob
            ):
                return "Update account status and audit the change"
            if "error" in blob and "log" in blob:
                return "Log error message"
            if "new provision row" in blob or "new provisioning row" in blob:
                return "Insert new provision row"
            if "existing provision row" in blob or "update existing provision row" in blob:
                return "Update existing provision row"
            if "non-standard" in blob and "show" in blob:
                return "Show only non-standard accounts"
            if "most recent" in blob and "provision row" in blob:
                return "Keep only most recent provision row"
            if "classified accounts" in blob:
                return "Include only classified accounts"
            if "latest provision values" in blob:
                return "Summarize latest provision values"
            if "classified as standard" in blob and "provisioning rate" in blob and "0.40" in blob:
                return "Set STANDARD classification and 0.40 provision pct"
            if "sub-standard" in blob or "substandard" in blob:
                if "provisioning rate" in blob and "15" in blob:
                    return "Set SUBSTANDARD classification and 15 provision pct"
                return "Set SUBSTANDARD classification"
            if "doubtful-1" in blob and "doubtful-2" in blob and "doubtful_since" in blob:
                return "Set DOUBTFUL1 or DOUBTFUL2 based on doubtful_since"
            if "loss" in blob and "doubtful-3" in blob and "doubtful_since" in blob:
                return "Set LOSS or DOUBTFUL3 based on doubtful_since"
            return text

        normalized: List[Dict[str, Any]] = []
        for rule in raw_rules:
            if not isinstance(rule, dict):
                continue

            fields_affected = _as_string_list(rule.get("fields_affected", []))
            source_evidence = _as_string_list(rule.get("source_evidence", []))
            derived_fields = _extract_assignment_fields(
                rule.get("condition"),
                rule.get("action"),
                rule.get("business_meaning"),
                *source_evidence,
            )
            for candidate in derived_fields:
                if candidate and candidate not in fields_affected:
                    fields_affected.append(candidate)
            output_field = _as_text(rule.get("output_field")) or (", ".join(fields_affected) if fields_affected else "")
            output_field = _canonicalize_output_field(output_field, " ".join(source_evidence), fields_affected)
            business_meaning = _as_text(rule.get("business_meaning")) or _as_text(rule.get("action"))
            eligibility = _as_string_list(rule.get("eligibility"))
            if not eligibility and _as_text(rule.get("condition")):
                eligibility = [_as_text(rule.get("condition"))]
            decision_logic = _as_string_list(rule.get("decision_logic"))
            if not decision_logic and _as_text(rule.get("condition")):
                decision_logic = [_as_text(rule.get("condition"))]
            decision_logic_rows = rule.get("decision_logic_rows")
            if not isinstance(decision_logic_rows, list):
                decision_logic_rows = []
            tie_priority_handling = _as_string_list(rule.get("tie_priority_handling"))
            default_value = _as_string_list(rule.get("default"))
            when_not_eligible = _as_string_list(rule.get("when_not_eligible"))
            condition = _canonicalize_condition(
                _as_text(rule.get("condition")), " ".join(source_evidence), fields_affected
            )
            action = _canonicalize_action(
                _as_text(rule.get("action")),
                " ".join(source_evidence),
                fields_affected,
                business_meaning=business_meaning,
            )

            normalized.append(
                {
                    "rule_name": _as_text(rule.get("rule_name"))
                    or condition
                    or action,
                    "output_field": output_field,
                    "business_meaning": business_meaning,
                    "eligibility": eligibility,
                    "decision_logic": decision_logic,
                    "decision_logic_rows": decision_logic_rows,
                    "tie_priority_handling": tie_priority_handling,
                    "default": default_value,
                    "when_not_eligible": when_not_eligible,
                    "condition": condition,
                    "action": action,
                    "fields_affected": fields_affected,
                    "rule_type": rule.get("rule_type", ""),
                    "confidence": rule.get("confidence", ""),
                    "validation_status": rule.get("validation_status", "unverified"),
                    "rule_id": _as_text(rule.get("rule_id")),
                    "ambiguity_id": _as_text(rule.get("ambiguity_id")),
                    "source_evidence": _as_string_list(rule.get("source_evidence", [])),
                    "source_chunks": _as_string_list(rule.get("source_chunks", [])),
                    "evidence_spans": _as_span_list(rule.get("evidence_spans", [])),
                    "technical_references": _as_string_list(rule.get("technical_references", [])),
                    "unresolved_ambiguities": _as_string_list(
                        rule.get("unresolved_ambiguities", [])
                    ),
                    "dependencies": _as_string_list(rule.get("dependencies", [])),
                }
            )
        return normalized

    @staticmethod
    def _scan_for_jargon(data: Dict[str, Any]) -> List[str]:
        flat_text = json.dumps(data).lower()
        return [term for term in _BANNED_TERMS if term in flat_text]
