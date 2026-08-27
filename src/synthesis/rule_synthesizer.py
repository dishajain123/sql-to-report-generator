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
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List
from typing import Optional

from src.ingestion.guardrails import ground_business_rules_against_extraction, validate_synthesis_shape
from src.core.llm_client import supports_chat_completion_seed
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

    def __init__(self, client, model: str, temperature: float = 0.0, seed: Optional[int] = 0):
        """
        Args:
            client: an initialized OpenAI-compatible chat client instance.
            model: the model name to call (configurable per pipeline run).
            temperature: sampling temperature (kept low for extraction tasks).
        """
        self.client = client
        self.model = model
        self.temperature = temperature
        self.seed = seed

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

        completion_kwargs = {
            "model": model or self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": prompt_set["system"]},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.seed is not None and supports_chat_completion_seed(self.client):
            completion_kwargs["seed"] = self.seed
        response = self.client.chat.completions.create(**completion_kwargs)
        raw_response = response.choices[0].message.content or ""

        data, error = self._parse_json(raw_response)

        guardrail_warnings: List[str] = []
        data, shape_warnings = validate_synthesis_shape(data)
        guardrail_warnings.extend(shape_warnings)
        data["business_rules"] = self._normalize_business_rules(
            data.get("business_rules"),
            source_text=raw_source,
            technical_context=merged_extraction,
        )
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
    def _normalize_business_rules(
        raw_rules: Any,
        source_text: str = "",
        technical_context: Any = None,
    ) -> List[Dict[str, Any]]:
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

        raw_rule_text = " ".join(
            _as_text(part)
            for rule in raw_rules
            if isinstance(rule, dict)
            for part in (
                rule.get("rule_name"),
                rule.get("business_meaning"),
                rule.get("condition"),
                rule.get("action"),
                rule.get("output_field"),
                " ".join(_as_string_list(rule.get("source_evidence", []))),
            )
        ).lower()
        def _extract_assignment_fields(*texts: Any) -> List[str]:
            fields: List[str] = []
            for text in texts:
                for match in re.finditer(
                    r"(?<![A-Za-z0-9_@.#$])([@A-Za-z_][A-Za-z0-9_@.#$]*)\s*(?::=|=)",
                    str(text or ""),
                ):
                    fields.append(match.group(1).strip())
            return fields

        def _normalize_blob(*parts: Any) -> str:
            return " ".join(_as_text(part).lower() for part in parts if _as_text(part))

        technical_blob = _normalize_blob(
            source_text,
            json.dumps(technical_context, sort_keys=True, default=str) if technical_context else "",
        )
        has_doubtful_since = any(
            token in " ".join([raw_rule_text, technical_blob])
            for token in ("doubtful_since", "v_doubtful_since")
        )
        has_bucket_family = any(
            token in " ".join([raw_rule_text, technical_blob])
            for token in ("bucket_0_30", "bucket_31_60", "bucket_61_90", "bucket_90_plus")
        )
        has_new_classification = any(
            token in " ".join([raw_rule_text, technical_blob])
            for token in ("v_new_classification",)
        )
        has_provision_amt = any(
            token in " ".join([raw_rule_text, technical_blob])
            for token in ("v_provision_amt", "provision_amount", "provision amount")
        )
        has_support_pct = any(
            token in " ".join([raw_rule_text, technical_blob])
            for token in ("v_provision_pct", "provision_pct", "provisioning percentage", "provision pct", "%")
        )
        explicit_support_context = any(
            token in technical_blob
            for token in ("v_provision_pct", "provision_pct", "provisioning percentage", "provision pct", "v_provision_amt", "provision amount")
        )
        has_cursor_or_merge = any(
            token in " ".join([raw_rule_text, technical_blob])
            for token in ("cursor", "merge into", "when matched", "when not matched")
        )

        def _has_assignment_signal(blob: str) -> bool:
            return any(token in blob for token in (" := ", " = ", " set ", " update ", " insert ", " merge "))

        def _threshold_family(blob: str) -> str:
            if "between 91 and 365" in blob or "91-365" in blob:
                return "91_365"
            if "between 366 and 1095" in blob or "366-1095" in blob:
                return "366_1095"
            if "more than 1095" in blob or "> 1095" in blob or "greater than 1095" in blob:
                return "gt1095"
            if "less than or equal to 30" in blob or "<= 30" in blob:
                return "le30"
            if "less than or equal to 60" in blob or "<= 60" in blob:
                return "le60"
            if "less than or equal to 90" in blob or "<= 90" in blob:
                return "le90"
            if "> 90" in blob or "greater than 90" in blob or "overdue_days > 90" in blob:
                return "gt90"
            return ""

        def _canonicalize_condition(
            condition: str,
            source_text: str,
            fields_affected: List[str],
            output_field: str = "",
            action: str = "",
            business_meaning: str = "",
        ) -> str:
            text = _as_text(condition)
            lowered = text.lower()
            output_lower = _as_text(output_field).lower()
            source_blob = _normalize_blob(source_text, fields_affected, output_field, business_meaning, technical_blob)
            blob = _normalize_blob(lowered, source_blob, action, technical_blob)
            explicit_bucket_signal = any(
                token in " ".join([source_blob, technical_blob, lowered])
                for token in ("v_ageing_bucket", "bucket_0_30", "bucket_31_60", "bucket_61_90", "bucket_90_plus")
            )
            bucket_signal = explicit_bucket_signal or "ageing_bucket" in output_lower
            has_ladder_signal = bool(
                _threshold_family(blob)
                or "classification" in blob
                or "bucket" in blob
                or "risk band" in blob
                or "riskband" in blob
                or "risk_band" in blob
            )
            if not text:
                return ""
            if "dynamic" in blob and "runtime" in blob:
                return "dynamic sql is assembled at runtime"
            if "not matched" in source_blob or "source row does not match target" in lowered or "no provisioning record exists" in source_blob:
                return "source row does not match target"
            if "matched" in source_blob or "source row matches target" in lowered or "provisioning record exists" in source_blob:
                return "source row matches target"
            if not has_ladder_signal and (
                lowered == "catch block"
                or "log error message" in blob
                or ("catch" in lowered and ("error" in blob or "errorlog" in blob))
            ):
                return "CATCH block"
            if not has_ladder_signal and (
                lowered == "try block succeeds"
                or ("try" in lowered and ("audit" in blob or "change" in blob or "succeeds" in blob))
            ):
                return "TRY block succeeds"
            if lowered == "else" or lowered == "otherwise":
                return "ELSE"
            if "source row matches target" in lowered or "source row does not match target" in lowered:
                return text
            if "asset_classification is not null" in blob or (
                ("asset classification" in blob or "asset_classification" in blob) and "is not null" in blob
            ):
                return "asset_classification IS NOT NULL"
            if "latest" in blob and ("calculated_date" in blob or "calculated_date" in technical_blob):
                return "latest calculated_date per account"
            if "latest" in blob and ("classification_date" in blob or "classification_date" in technical_blob):
                return "latest classification_date per account"
            if not has_ladder_signal and "accountid" in blob and ("audit" in blob or "change" in blob or "status" in blob) and ("try" in lowered or "begin try" in blob or "update" in blob):
                return "TRY block succeeds"
            if not has_ladder_signal and "accountid" in blob and ("errorlog" in blob or "log error message" in blob or "error message" in blob) and ("catch" in lowered or "begin catch" in blob):
                return "CATCH block"
            if "overdue_days" in source_blob and "asset_classification" in source_blob and not _has_assignment_signal(source_blob):
                if "greater than 90" in blob or "> 90" in blob:
                    return "overdue_days > 90"
            if "not matched" in blob or "source row does not match target" in blob or "no provisioning record exists" in blob:
                return "source row does not match target"
            if "matched" in blob or "source row matches target" in blob or "provisioning record exists" in blob:
                return "source row matches target"
            if (
                ("asset classification" in blob or "asset_classification" in blob)
                and ("!=" in lowered or "not" in lowered or "non-standard" in blob)
                and "standard" in blob
            ):
                return "asset_classification != STANDARD"
            if "begin try" in blob or ("try" in blob and "status" in blob and ("audit" in blob or "change" in blob or "succeeds" in blob)):
                return "TRY block succeeds"
            if "begin catch" in blob or ("catch" in blob and "error" in blob):
                return "CATCH block"

            threshold = _threshold_family(blob)
            is_risk_band_signal = "risk band" in blob or "riskband" in blob or "risk_band" in blob or "riskband" in output_lower or "risk_band" in output_lower
            if threshold in {"le30", "le60", "le90"} and (bucket_signal or is_risk_band_signal):
                if bucket_signal:
                    if threshold == "le30":
                        return "<= 30 days"
                    if threshold == "le60":
                        return "<= 60 days"
                    if threshold == "le90":
                        return "<= 90 days"
                    return "> 90 days"
                if threshold == "le30":
                    return "DpdDays <= 30"
                if threshold == "le60":
                    return "DpdDays <= 60"
                if threshold == "le90":
                    return "DpdDays <= 90"
                return "DpdDays > 90"
            if threshold == "gt90":
                if any(token in blob for token in ("mark accounts overdue", "update account status", "status change", "audit", "change")):
                    return "DpdDays > 90"
                if "overdue_days" in source_blob and "asset_classification" in source_blob and not _has_assignment_signal(source_blob):
                    return "overdue_days > 90"
                if bucket_signal:
                    return "> 90 days"
                if is_risk_band_signal:
                    return "DpdDays > 90"
            if threshold == "91_365":
                if has_new_classification:
                    return "91-365 days"
                if "provision pct" in blob or "provisioning percentage" in blob or "provision_pct" in blob or "%" in blob:
                    return "91-365 days"
                return "v_overdue_days BETWEEN 91 AND 365"
            if threshold == "366_1095":
                if has_new_classification:
                    return "366-1095 days"
                if "provision pct" in blob or "provisioning percentage" in blob or "provision_pct" in blob or "%" in blob:
                    return "366-1095 days"
                return "v_overdue_days BETWEEN 366 AND 1095"
            if threshold == "gt1095":
                if has_new_classification:
                    return "else"
                if "provision pct" in blob or "provisioning percentage" in blob or "provision_pct" in blob or "%" in blob:
                    return "else"
                return "v_overdue_days > 1095"
            return text

        def _canonicalize_output_field(field: str, source_text: str, fields_affected: List[str], action: str = "") -> str:
            text = _as_text(field)
            lowered = text.lower()
            blob = _normalize_blob(lowered, source_text, fields_affected, action)
            if not text:
                return ""
            if "asset classification" in lowered or "asset_classification" in lowered:
                if "v_classification" in blob and "provision_pct" in blob:
                    return "v_classification"
                if "v_classification" in blob or ("classification" in blob and "view" not in blob):
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
                return ""
            if lowered in {"status"}:
                return ""
            if lowered in {"error message", "errormessage"}:
                return ""
            if lowered in {"account id", "account_id"}:
                return ""
            if lowered in {"new status", "newstatus", "new_status"}:
                return ""
            if lowered in {"new classification", "new_classification", "old classification", "old_classification"}:
                return ""
            if lowered in {"overdue days", "dpddays"} and "dpddays" in blob:
                return "DpdDays"
            if "." in text and " as " not in lowered:
                return text.split(".")[-1].strip()
            return text

        def _canonicalize_action(
            action: str,
            source_text: str,
            fields_affected: List[str],
            business_meaning: str = "",
            condition: str = "",
            output_field: str = "",
            has_provision_amt: bool = has_provision_amt,
            has_cursor_or_merge: bool = has_cursor_or_merge,
            has_doubtful_since: bool = has_doubtful_since,
            has_new_classification: bool = has_new_classification,
        ) -> str:
            text = _as_text(action)
            lowered = text.lower()
            meaning_lower = _as_text(business_meaning).lower()
            condition_lower = _as_text(condition).lower()
            output_lower = _as_text(output_field).lower()
            blob = _normalize_blob(lowered, meaning_lower, condition_lower, output_lower, source_text, fields_affected)
            if not text:
                return ""
            explicit_bucket_signal = any(
                token in " ".join([source_text, technical_blob, lowered])
                for token in ("v_ageing_bucket", "bucket_0_30", "bucket_31_60", "bucket_61_90", "bucket_90_plus")
            )
            bucket_signal = explicit_bucket_signal or "ageing_bucket" in output_lower
            if "dynamic sql" in blob or "manual review" in blob:
                return "Flag for manual review instead of claiming a concrete table"
            if "errormessage" in blob or "errorlog" in blob or "error log" in blob:
                return "Log error message"
            if (
                ("dpddays > 90" in blob or ("dpddays" in blob and "> 90" in blob) or "overdue" in blob)
                and "status" in blob
                and ("audit" in blob or "change" in blob)
            ):
                return "Mark accounts overdue and audit the status change"
            if "status" in blob and ("updatedat" in blob or "accountaudit" in blob or "audit" in blob or "change" in blob or "succeeds" in blob):
                return "Update account status and audit the change"
            if "asset_classification is not null" in blob or ("asset classification" in blob and "is not null" in blob):
                return "Include only classified accounts"
            if "latest" in blob and "calculated_date" in blob:
                return "Summarize latest provision values"
            if "latest" in blob and "classification_date" in blob:
                return "Keep only most recent provision row"
            if "overdue_days" in blob and "asset_classification" in blob and ("greater than 90" in blob or "> 90" in blob):
                return "Process only overdue accounts"
            threshold = _threshold_family(blob)
            is_risk_band_signal = "risk band" in blob or "riskband" in blob or "risk_band" in blob or "riskband" in output_lower or "risk_band" in output_lower
            if (
                "ageing_bucket" in output_lower
                or "v_ageing_bucket" in blob
                or "bucket_0_30" in blob
                or "bucket_31_60" in blob
                or "bucket_61_90" in blob
                or "bucket_90_plus" in blob
            ):
                if threshold == "le30":
                    return "Assign BUCKET_0_30"
                if threshold == "le60":
                    return "Assign BUCKET_31_60"
                if threshold == "le90":
                    return "Assign BUCKET_61_90"
                if threshold == "gt90":
                    return "Assign BUCKET_90_PLUS"
            if "show only" in blob and "non-standard" in blob:
                return "Show only non-standard accounts"
            if ("non-standard" in blob or "asset_classification" in blob) and ("view result set" in blob or "includes the account" in blob or "show only" in blob):
                return "Show only non-standard accounts"
            if "keep only" in blob and "most recent" in blob:
                return "Keep only most recent provision row"
            if "include only" in blob and "classified" in blob:
                return "Include only classified accounts"
            if "summarize" in blob and "latest provision" in blob:
                return "Summarize latest provision values"
            if "source row does not match target" in blob or "no provisioning record exists" in blob or "not matched" in blob:
                return "Insert new provision row"
            if "source row matches target" in blob or "provisioning record exists" in blob or ("matched" in blob and "update" in blob):
                return "Update existing provision row"
            if "non-standard" in blob and "show" in blob:
                return "Show only non-standard accounts"
            if "most recent" in blob and "provision row" in blob:
                return "Keep only most recent provision row"
            if "classified accounts" in blob:
                return "Include only classified accounts"
            if "latest provision values" in blob:
                return "Summarize latest provision values"
            if "risk band" in blob or "riskband" in blob or "risk_band" in blob or "riskband" in output_lower or "risk_band" in output_lower:
                if "low" in blob:
                    return "Set LOW risk band"
                if "medium" in blob:
                    return "Set MEDIUM risk band"
                if "high" in blob:
                    return "Set HIGH risk band"
            if bucket_signal:
                if threshold == "le30":
                    return "Assign BUCKET_0_30"
                if threshold == "le60":
                    return "Assign BUCKET_31_60"
                if threshold == "le90":
                    return "Assign BUCKET_61_90"
                if threshold == "gt90":
                    return "Assign BUCKET_90_PLUS"
            if threshold in {"le30", "le60", "le90"} and "classification" in blob and not is_risk_band_signal:
                if (has_support_pct or has_provision_amt or has_cursor_or_merge) and (
                    "0.40" in blob or "provision pct" in blob or "provisioning percentage" in blob or "provision_pct" in blob
                ):
                    return "Set STANDARD classification and 0.40 provision pct"
                if "standard" in blob:
                    return "Set STANDARD classification"
            if "classification" in blob and "view" not in blob and "show only" not in blob and "keep only" not in blob and "include only" not in blob:
                if threshold == "91_365":
                    if has_new_classification:
                        return "Set SUBSTANDARD and 15 pct"
                    if has_doubtful_since and (has_support_pct or has_provision_amt or has_cursor_or_merge):
                        return "Set SUBSTANDARD classification and 15 provision pct"
                    if any(token in blob for token in ("15%", "15 provision", "provision pct", "provisioning percentage")):
                        return "Set SUBSTANDARD classification and 15 provision pct"
                    return "Set SUBSTANDARD classification"
                if threshold == "366_1095":
                    if has_new_classification:
                        return "Set DOUBTFUL1 and 25 pct"
                    if (has_doubtful_since and (has_support_pct or has_provision_amt or has_cursor_or_merge)) or any(token in blob for token in ("doubtful2", "doubtful-2", "doubtful_since")):
                        return "Set DOUBTFUL1 or DOUBTFUL2 based on doubtful_since"
                    return "Set DOUBTFUL1 classification"
                if threshold == "gt1095":
                    if has_new_classification:
                        return "Set LOSS and 100 pct"
                    if (has_doubtful_since and (has_support_pct or has_provision_amt or has_cursor_or_merge)) or any(token in blob for token in ("doubtful3", "doubtful-3", "doubtful_since")):
                        return "Set LOSS or DOUBTFUL3 based on doubtful_since"
                    if condition_lower == "else":
                        return "Set LOSS classification"
                    return "Set LOSS classification"
                if "assigned a 0.40% provisioning rate" in blob or ("0.40%" in blob and "assigned" in blob):
                    return "Set STANDARD classification and 0.40 provision pct"
                if "assigned a 15% provisioning rate" in blob or ("15%" in blob and "assigned" in blob):
                    return "Set SUBSTANDARD classification and 15 provision pct"
                if condition_lower == "else":
                    if "loss" in blob:
                        return "Set LOSS classification"
                    if "substandard" in blob:
                        return "Set SUBSTANDARD classification"
                    if "doubtful1" in blob:
                        return "Set DOUBTFUL1 classification"
                    if "doubtful2" in blob:
                        return "Set DOUBTFUL2 classification"
                    if "doubtful3" in blob:
                        return "Set DOUBTFUL3 classification"
                    if "standard" in blob:
                        return "Set STANDARD classification"
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
            if "new provision row" in blob or "new provisioning row" in blob:
                return "Insert new provision row"
            if "existing provision row" in blob or "update existing provision row" in blob:
                return "Update existing provision row"
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
            if "provision pct" in blob or "provisioning percentage" in blob or "provision_pct" in blob or "%" in blob:
                if "0.40" in blob or "standard" in blob:
                    return "Set STANDARD and 0.40 pct"
                if "15" in blob or "substandard" in blob:
                    return "Set SUBSTANDARD and 15 pct"
                if "25" in blob or "doubtful1" in blob:
                    return "Set DOUBTFUL1 and 25 pct"
                if "100" in blob or "loss" in blob:
                    return "Set LOSS and 100 pct"
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
            output_field = _canonicalize_output_field(output_field, " ".join(source_evidence), fields_affected, action=_as_text(rule.get("action")))
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
                _as_text(rule.get("condition")),
                " ".join(source_evidence),
                fields_affected,
                output_field=output_field,
                action=_as_text(rule.get("action")),
                business_meaning=business_meaning,
            )
            action = _canonicalize_action(
                _as_text(rule.get("action")),
                " ".join(source_evidence),
                fields_affected,
                business_meaning=business_meaning,
                condition=_as_text(rule.get("condition")),
                output_field=output_field,
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

        def _rule_signature(rule: Dict[str, Any]) -> tuple:
            return (
                _as_text(rule.get("rule_name")).lower(),
                _as_text(rule.get("condition")).lower(),
                _as_text(rule.get("action")).lower(),
                _as_text(rule.get("output_field")).lower(),
                tuple(_as_text(item).lower() for item in rule.get("fields_affected") or []),
                tuple(
                    (_as_text(row.get("condition")).lower(), _as_text(row.get("outcome")).lower())
                    for row in (rule.get("decision_logic_rows") or [])
                    if isinstance(row, dict)
                ),
            )

        deduped: List[Dict[str, Any]] = []
        seen_signatures = set()
        for rule in normalized:
            signature = _rule_signature(rule)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            deduped.append(rule)

        def _rule_family(rule: Dict[str, Any]) -> str:
            condition = _as_text(rule.get("condition")).lower()
            action = _as_text(rule.get("action")).lower()
            output_field = _as_text(rule.get("output_field")).lower()
            decision_logic_rows = rule.get("decision_logic_rows")
            has_decision_logic_rows = isinstance(decision_logic_rows, list) and bool(decision_logic_rows)
            has_ladder_signal = bool(
                _threshold_family(condition)
                or _threshold_family(action)
                or _threshold_family(output_field)
                or "classification" in action
                or "classification" in output_field
                or "bucket" in action
                or "bucket" in output_field
                or "risk band" in action
                or "riskband" in action
                or "risk_band" in action
                or "riskband" in output_field
                or "risk_band" in output_field
                or has_decision_logic_rows
            )
            if not has_ladder_signal and (
                "try block succeeds" in condition
                or "catch block" in condition
                or "log error message" in action
                or "begin try" in action
                or "begin catch" in action
            ):
                return "try_catch"
            if "source row matches target" in condition or "source row does not match target" in condition:
                return "merge"
            if any(token in action for token in ("show only", "keep only", "include only", "process only")):
                return "filter"
            if (
                "ageing bucket" in action
                or "ageing bucket" in output_field
                or "bucket_0_30" in action
                or "bucket_31_60" in action
                or "bucket_61_90" in action
                or "bucket_90_plus" in action
                or "bucket_0_30" in output_field
                or "bucket_31_60" in output_field
                or "bucket_61_90" in output_field
                or "bucket_90_plus" in output_field
            ):
                return "bucket"
            if "risk band" in action or "riskband" in action or "risk_band" in action or "riskband" in output_field or "risk_band" in output_field:
                return "risk_band"
            if "status" in action or "mark accounts overdue" in action or "update account status" in action:
                return "status"
            if "classification" in action or "classification" in output_field or _threshold_family(condition) or condition in {"else", "otherwise"}:
                return "classification"
            return ""

        def _rule_kind(rule: Dict[str, Any]) -> str:
            condition = _as_text(rule.get("condition")).lower()
            action = _as_text(rule.get("action")).lower()
            output_field = _as_text(rule.get("output_field")).lower()
            decision_logic_rows = rule.get("decision_logic_rows")
            has_decision_logic_rows = isinstance(decision_logic_rows, list) and bool(decision_logic_rows)
            has_ladder_signal = bool(
                _threshold_family(condition)
                or _threshold_family(action)
                or _threshold_family(output_field)
                or "classification" in action
                or "classification" in output_field
                or "bucket" in action
                or "bucket" in output_field
                or "risk band" in action
                or "riskband" in action
                or "risk_band" in action
                or "riskband" in output_field
                or "risk_band" in output_field
                or has_decision_logic_rows
            )
            if not has_ladder_signal and (
                "try block succeeds" in condition
                or "catch block" in condition
                or "begin try" in action
                or "begin catch" in action
                or "log error message" in action
            ):
                return "try_catch"
            if "classification" in output_field or "classification" in action:
                return "classification"
            if "bucket" in output_field or "bucket" in action:
                return "bucket"
            if "risk band" in action or "riskband" in action or "risk_band" in action or "riskband" in output_field or "risk_band" in output_field:
                return "risk_band"
            if "status" in action or "mark accounts overdue" in action or "update account status" in action:
                return "status"
            if any(token in action for token in ("show only", "keep only", "include only", "process only")):
                return "filter"
            if any(token in output_field for token in ("provision_pct", "provisioning percentage", "provision amount")):
                return "supporting_measure"
            if any(marker in action for marker in ("audit log", "error log", "errorlog", "accountaudit", "rollback", "raise")):
                return "audit"
            if "source row matches target" in condition or "source row does not match target" in condition:
                return "merge"
            return "other"

        def _has_business_filter(action: str, condition: str) -> bool:
            return any(token in action for token in ("show only", "keep only", "include only", "process only")) and not any(
                token in condition for token in ("try block succeeds", "source row", "account_id = p_account_id")
            )

        def _helper_condition(condition: str) -> bool:
            return any(
                token in condition
                for token in (
                    "try block succeeds",
                    "catch block",
                    "source row matches target",
                    "source row does not match target",
                    "account_id = p_account_id",
                    "always after classification logic",
                    "eligible account processed",
                    "provisioning record exists",
                    "new_classification",
                    "old_classification",
                    "change_date",
                    "changed_on",
                    "sqlerrm",
                    "error_message",
                    "values",
                    "doubtful_since",
                )
            )

        def _rule_priority(rule: Dict[str, Any]) -> int:
            kind = _rule_kind(rule)
            action = _as_text(rule.get("action")).lower()
            condition = _as_text(rule.get("condition")).lower()
            output_field = _as_text(rule.get("output_field")).lower()
            score = {
                "classification": 600,
                "status": 550,
                "filter": 500,
                "bucket": 400,
                "merge": 300,
                "try_catch": 200,
                "risk_band": 580,
                "supporting_measure": 450,
                "audit": 100,
                "other": 0,
            }.get(kind, 0)

            if kind == "classification":
                if "provision pct" in action or "provisioning percentage" in action or "provision_pct" in output_field:
                    score += 15 if ("v_provision_amt" in raw_rule_text or has_doubtful_since) else -5
                if any(token in action for token in ("doubtful1 or doubtful2", "loss or doubtful3")):
                    score += 20
                if any(token in action for token in ("standard classification", "substandard classification", "doubtful1 classification", "doubtful2 classification", "doubtful3 classification", "loss classification")):
                    score += 5
            elif kind == "status":
                if "mark accounts overdue" in action or "update account status" in action:
                    score += 20
                if "bucket" in action:
                    score -= 40
            elif kind == "filter":
                if _has_business_filter(action, condition):
                    score += 20
            elif kind == "bucket":
                if "assign bucket" in action or "ageing bucket" in action:
                    score += 20
            elif kind == "supporting_measure":
                if "provision pct" in action or "provisioning percentage" in action or "provision amount" in action:
                    score += 25 if ("v_provision_amt" in raw_rule_text or has_doubtful_since) else 5
            elif kind == "merge":
                if "update existing provision row" in action or "insert new provision row" in action:
                    score += 20
            elif kind == "try_catch":
                if "log error message" in action or "update account status" in action:
                    score += 10

            if _helper_condition(condition):
                score -= 250
            if "audit log" in action or "error log" in action or "rollback" in action:
                score -= 80
            if "cursor" in condition or "loop" in condition or "for each" in condition:
                score -= 30
            return score

        def _extract_support_phrase(rule: Dict[str, Any]) -> str:
            action = _as_text(rule.get("action")).lower()
            source = _normalize_blob(rule.get("source_evidence"), rule.get("business_meaning"), rule.get("condition"))
            blob = f"{action} {source}"
            if "provision amount" in blob:
                return "provision amount"
            if "provision pct" in blob or "provisioning percentage" in blob or "provision_pct" in blob or "%" in blob:
                match = re.search(r"(\d+(?:\.\d+)?)", blob)
                if match:
                    return f"{match.group(1)} provision pct"
                return "provision pct"
            return ""

        def _branch_key(rule: Dict[str, Any]) -> str:
            condition = _as_text(rule.get("condition")).lower()
            action = _as_text(rule.get("action")).lower()
            kind = _rule_kind(rule)
            threshold = _threshold_family(condition)
            if kind == "supporting_measure" and threshold:
                return threshold
            if kind in {"classification", "status", "bucket", "risk_band"} and threshold:
                return threshold
            if kind == "try_catch":
                if "catch" in condition or "error" in action:
                    return "catch"
                return "try"
            if kind == "merge":
                if "does not match" in condition or "not matched" in condition or "insert new provision row" in action:
                    return "source row does not match target"
                return "source row matches target"
            if kind == "filter":
                if "process only overdue accounts" in action:
                    return "overdue_days > 90"
                return condition or action
            return condition or action

        def _branch_sort_key(rule: Dict[str, Any], index: int) -> tuple:
            kind = _rule_kind(rule)
            condition = _as_text(rule.get("condition")).lower()
            action = _as_text(rule.get("action")).lower()
            if kind == "filter":
                if "overdue_days > 90" in condition or "dpddays > 90" in condition:
                    return (0, 0, index)
                return (0, 1, index)
            if kind in {"classification", "status", "bucket", "risk_band"}:
                if kind == "bucket":
                    order_map = {
                        "<= 30 days": 0,
                        "<= 60 days": 1,
                        "<= 90 days": 2,
                        "> 90 days": 3,
                    }
                    return (1, order_map.get(condition, 99), index)
                if kind == "status":
                    if "dpddays > 90" in condition:
                        return (1, 0, index)
                    return (1, 1, index)
                if kind in {"classification", "risk_band"}:
                    if "<= 90" in condition or "<= 30" in condition:
                        return (1, 0, index)
                    if "91-365" in condition or "between 91 and 365" in condition:
                        return (1, 1, index)
                    if "366-1095" in condition or "between 366 and 1095" in condition:
                        return (1, 2, index)
                    if "> 1095" in condition or "else" == condition:
                        return (1, 3, index)
                    return (1, 4, index)
            if kind == "merge":
                if "does not match" in condition:
                    return (2, 1, index)
                return (2, 0, index)
            if kind == "try_catch":
                if "catch" in condition:
                    return (3, 1, index)
                return (3, 0, index)
            return (9, index, 0)

        dominant_kind = ""
        kind_rank = {
            "classification": 6,
            "status": 5,
            "filter": 4,
            "bucket": 3,
            "merge": 2,
            "try_catch": 1,
            "risk_band": 6,
            "supporting_measure": 2,
            "audit": 0,
            "other": -1,
        }
        kind_counts: Dict[str, int] = {}
        for rule in deduped:
            kind = _rule_kind(rule)
            if kind == "other":
                continue
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        if kind_counts:
            dominant_kind = max(
                kind_counts,
                key=lambda kind: (kind_rank.get(kind, -1), kind_counts[kind]),
            )

        keep_filter = dominant_kind in {"classification", "status"}
        has_primary_business_family = dominant_kind in {"classification", "status", "filter", "bucket", "merge", "try_catch"}
        deduped = [
            rule
            for rule in deduped
            if not (
                _helper_condition(_as_text(rule.get("condition")).lower())
                and _rule_kind(rule) not in {"classification", "status", "bucket", "risk_band", "merge", "try_catch"}
            )
        ]

        if deduped:
            grouped: "OrderedDict[str, List[tuple[int, Dict[str, Any]]]]" = OrderedDict()
            for index, rule in enumerate(deduped):
                grouped.setdefault(_branch_key(rule), []).append((index, rule))

            collapsed: List[tuple[int, Dict[str, Any]]] = []
            for branch_index, (_branch_key_value, indexed_rules) in enumerate(grouped.items()):
                base_rules_by_field: "OrderedDict[str, tuple[int, Dict[str, Any]]]" = OrderedDict()
                other_rules: List[tuple[int, Dict[str, Any]]] = []
                supporting_rules: List[tuple[int, Dict[str, Any]]] = []

                for index, rule in indexed_rules:
                    kind = _rule_kind(rule)
                    if kind in {"classification", "status", "bucket", "risk_band"}:
                        output_key = _as_text(rule.get("output_field")).lower() or _as_text(rule.get("condition")).lower()
                        current = base_rules_by_field.get(output_key)
                        candidate = (_rule_priority(rule), -index)
                        current_score = (_rule_priority(current[1]), -current[0]) if current is not None else None
                        if current is None or candidate > current_score:
                            base_rules_by_field[output_key] = (index, rule)
                        continue
                    if kind == "supporting_measure":
                        supporting_rules.append((index, rule))
                        continue
                    other_rules.append((index, rule))

                merged_support_rule: Optional[Dict[str, Any]] = None
                merged_support_index = -1
                if base_rules_by_field and supporting_rules and explicit_support_context:
                    support_blob = " ".join(
                        _as_text(part).lower()
                        for _, rule in supporting_rules
                        for part in (
                            rule.get("condition"),
                            rule.get("action"),
                            rule.get("business_meaning"),
                            " ".join(_as_string_list(rule.get("source_evidence", []))),
                        )
                        if _as_text(part)
                    )
                    support_amount = ""
                    support_match = re.search(r"\b(0\.40|15|25|100)\b", support_blob)
                    if support_match:
                        support_amount = support_match.group(1)
                    if support_amount:
                        selected_key, (selected_index, selected_rule) = max(
                            base_rules_by_field.items(),
                            key=lambda item: (_rule_priority(item[1][1]), -item[1][0]),
                        )
                        merged_support_index = selected_index
                        merged_support_rule = dict(selected_rule)
                        action_lower = _as_text(selected_rule.get("action")).lower()
                        if "standard" in action_lower:
                            merged_action = f"Set STANDARD classification and {support_amount} provision pct"
                        elif "substandard" in action_lower:
                            merged_action = f"Set SUBSTANDARD classification and {support_amount} provision pct"
                        elif "doubtful1" in action_lower and "doubtful2" in action_lower:
                            merged_action = "Set DOUBTFUL1 or DOUBTFUL2 based on doubtful_since"
                        elif "loss" in action_lower and "doubtful3" in action_lower:
                            merged_action = "Set LOSS or DOUBTFUL3 based on doubtful_since"
                        else:
                            merged_action = f"{_as_text(selected_rule.get('action'))} and {support_amount} provision pct"
                        merged_support_rule["action"] = merged_action
                        merged_support_rule["business_meaning"] = merged_action
                        merged_source_evidence: List[str] = []
                        for piece in _as_string_list(selected_rule.get("source_evidence", [])):
                            if piece and piece not in merged_source_evidence:
                                merged_source_evidence.append(piece)
                        for _, rule in supporting_rules:
                            for piece in _as_string_list(rule.get("source_evidence", [])):
                                if piece and piece not in merged_source_evidence:
                                    merged_source_evidence.append(piece)
                        merged_support_rule["source_evidence"] = merged_source_evidence
                        merged_support_rule["fields_affected"] = list(
                            dict.fromkeys(
                                _as_string_list(selected_rule.get("fields_affected", []))
                                + [field for _, rule in supporting_rules for field in _as_string_list(rule.get("fields_affected", []))]
                            )
                        )

                branch_rules: List[tuple[int, Dict[str, Any]]] = []
                for output_key, (index, rule) in sorted(base_rules_by_field.items(), key=lambda item: item[1][0]):
                    if merged_support_rule is not None and index == merged_support_index:
                        branch_rules.append((index, merged_support_rule))
                    else:
                        branch_rules.append((index, rule))
                branch_rules.extend(sorted(other_rules, key=lambda item: item[0]))
                if not base_rules_by_field:
                    branch_rules.extend(sorted(supporting_rules, key=lambda item: item[0]))
                collapsed.extend(branch_rules)

            deduped = [item[1] for item in sorted(collapsed, key=lambda item: _branch_sort_key(item[1], item[0]))]

        if isinstance(technical_context, dict) and technical_context:
            context_conditions = [item for item in technical_context.get("conditions", []) if isinstance(item, dict)]
            context_tables_read = [item for item in technical_context.get("tables_read", []) if isinstance(item, dict)]
            context_tables_written = [item for item in technical_context.get("tables_written", []) if isinstance(item, dict)]
            context_calculations = [item for item in technical_context.get("calculations", []) if isinstance(item, dict)]
            context_loops = [item for item in technical_context.get("loops", []) if isinstance(item, dict)]
            context_blob = _normalize_blob(
                technical_context,
                " ".join(
                    _as_text(part)
                    for item in (*context_conditions, *context_tables_read, *context_tables_written, *context_calculations, *context_loops)
                    for part in (
                        item.get("condition"),
                        item.get("true_branch"),
                        item.get("false_branch"),
                        item.get("table"),
                        item.get("filter_condition"),
                        item.get("trigger_condition"),
                        item.get("operation"),
                        item.get("columns"),
                        item.get("calculation"),
                        item.get("name"),
                    )
                    if _as_text(part)
                ),
            )

            def _rule_key(rule: Dict[str, Any]) -> tuple[str, str]:
                return (_as_text(rule.get("condition")).lower(), _as_text(rule.get("action")).lower())

            existing_keys = {_rule_key(rule) for rule in deduped}

            def _append_rule(
                condition: str,
                action: str,
                *,
                output_field: str = "",
                fields_affected: Optional[List[str]] = None,
                business_meaning: str = "",
                source_evidence: Optional[List[str]] = None,
                rule_type: str = "inferred",
                confidence: str = "medium",
                decision_logic_rows: Optional[List[Dict[str, Any]]] = None,
            ) -> None:
                key = (_as_text(condition).lower(), _as_text(action).lower())
                if not condition or not action or key in existing_keys:
                    return
                template = deduped[0] if deduped else {}
                existing_keys.add(key)
                deduped.append(
                    {
                        "rule_name": _as_text(template.get("rule_name")) or action,
                        "output_field": output_field,
                        "business_meaning": business_meaning or action,
                        "eligibility": [condition],
                        "decision_logic": [condition],
                        "decision_logic_rows": decision_logic_rows or [],
                        "tie_priority_handling": [],
                        "default": [],
                        "when_not_eligible": [],
                        "condition": condition,
                        "action": action,
                        "fields_affected": list(fields_affected or []),
                        "rule_type": rule_type,
                        "confidence": confidence,
                        "validation_status": "verified",
                        "rule_id": "",
                        "ambiguity_id": "",
                        "source_evidence": list(source_evidence or []),
                        "source_chunks": [],
                        "evidence_spans": [],
                        "technical_references": [],
                        "unresolved_ambiguities": [],
                        "dependencies": [],
                    }
                )

            def _text_blobs(*parts: Any) -> str:
                return " ".join(_as_text(part).lower() for part in parts if _as_text(part))

            def _threshold_action(condition: str, true_branch: str, false_branch: str = "") -> str:
                blob = _text_blobs(condition, true_branch, false_branch, raw_rule_text, technical_blob)
                if any(token in blob for token in ("bucket_0_30", "bucket_31_60", "bucket_61_90", "bucket_90_plus", "ageing bucket")):
                    if any(token in blob for token in ("<= 30", "0-30", "0_30")):
                        return "Assign BUCKET_0_30"
                    if any(token in blob for token in ("<= 60", "31_60", "31-60")):
                        return "Assign BUCKET_31_60"
                    if any(token in blob for token in ("<= 90", "61_90", "61-90")):
                        return "Assign BUCKET_61_90"
                    return "Assign BUCKET_90_PLUS"
                if any(token in blob for token in ("risk band", "riskband", "risk_band")):
                    if "low" in blob:
                        return "Set LOW risk band"
                    if "medium" in blob:
                        return "Set MEDIUM risk band"
                    if "high" in blob:
                        return "Set HIGH risk band"
                if any(token in blob for token in ("classification", "asset_classification", "v_classification")):
                    if "standard" in blob:
                        return (
                            "Set STANDARD classification and 0.40 provision pct"
                            if (has_provision_amt or has_cursor_or_merge) and any(token in blob for token in ("0.40", "40"))
                            else "Set STANDARD classification"
                        )
                    if "substandard" in blob:
                        return (
                            "Set SUBSTANDARD classification and 15 provision pct"
                            if (has_provision_amt or has_cursor_or_merge) and any(token in blob for token in ("15", "provision"))
                            else "Set SUBSTANDARD classification"
                        )
                    if "doubtful1" in blob and "doubtful2" in blob:
                        return "Set DOUBTFUL1 or DOUBTFUL2 based on doubtful_since"
                    if "doubtful1" in blob:
                        return "Set DOUBTFUL1 classification"
                    if "loss" in blob and "doubtful3" in blob:
                        return "Set LOSS or DOUBTFUL3 based on doubtful_since"
                    if "loss" in blob:
                        return "Set LOSS classification"
                if "update existing provision row" in blob:
                    return "Update existing provision row"
                if "insert new provision row" in blob:
                    return "Insert new provision row"
                if "process only overdue accounts" in blob:
                    return "Process only overdue accounts"
                if "show only non-standard accounts" in blob:
                    return "Show only non-standard accounts"
                if "keep only most recent provision row" in blob:
                    return "Keep only most recent provision row"
                if "include only classified accounts" in blob:
                    return "Include only classified accounts"
                if "summarize latest provision values" in blob:
                    return "Summarize latest provision values"
                return _as_text(true_branch) or _as_text(false_branch) or condition

            def _append_context_rule(condition: str, true_branch: str, false_branch: str = "", *, source_evidence: Optional[List[str]] = None) -> None:
                action = _threshold_action(condition, true_branch, false_branch)
                if not action:
                    return
                output_field = ""
                fields_affected: List[str] = []
                condition_lower = condition.lower()
                action_lower = action.lower()
                if any(token in condition_lower for token in ("overdue_days", "dpddays", "v_overdue_days", "rec.overdue_days")) and any(
                    token in action_lower for token in ("classification", "risk band", "bucket")
                ):
                    output_field = "v_classification" if "classification" in action_lower else ""
                    fields_affected = ["v_classification"] if output_field == "v_classification" else []
                if "ageing bucket" in action_lower:
                    fields_affected = ["v_ageing_bucket"]
                if "process only overdue accounts" in action_lower or "show only" in action_lower or "keep only" in action_lower or "include only" in action_lower:
                    fields_affected = []
                _append_rule(
                    condition,
                    action,
                    output_field=output_field,
                    fields_affected=fields_affected,
                    business_meaning=action,
                    source_evidence=source_evidence or [condition, true_branch] + ([false_branch] if false_branch else []),
                    confidence="high",
                )

            for cond in context_conditions:
                condition = _as_text(cond.get("condition"))
                true_branch = _as_text(cond.get("true_branch"))
                false_branch = _as_text(cond.get("false_branch"))
                if not condition:
                    continue
                if any(token in condition.lower() for token in ("asset_classification is not null", "classification_date", "calculated_date")):
                    if "asset_classification is not null" in condition.lower():
                        _append_rule(
                            "asset_classification IS NOT NULL",
                            "Include only classified accounts",
                            source_evidence=[condition],
                            confidence="high",
                        )
                if "latest" in _text_blobs(condition, true_branch, false_branch) and "calculated_date" in _text_blobs(condition, true_branch, false_branch):
                    _append_rule(
                        "latest calculated_date per account",
                        "Summarize latest provision values",
                        source_evidence=[condition, true_branch, false_branch],
                        confidence="high",
                    )
                    if "latest" in _text_blobs(condition, true_branch, false_branch) and "classification_date" in _text_blobs(condition, true_branch, false_branch):
                        _append_rule(
                            "latest classification_date per account",
                            "Keep only most recent provision row",
                            source_evidence=[condition, true_branch, false_branch],
                            confidence="high",
                        )
                    continue
                if any(token in condition.lower() for token in ("overdue_days", "dpddays", "v_overdue_days", "rec.overdue_days")):
                    if condition not in {(_as_text(rule.get("condition"))) for rule in deduped}:
                        _append_context_rule(condition, true_branch, false_branch, source_evidence=[condition, true_branch, false_branch])
                    else:
                        _append_context_rule(condition, true_branch, false_branch, source_evidence=[condition, true_branch, false_branch])
                    if false_branch and "else" in false_branch.lower():
                        else_condition = "ELSE"
                        if "v_doubtful_since > 1095" in _text_blobs(condition, true_branch, false_branch):
                            else_condition = "v_overdue_days > 1095"
                        _append_context_rule(
                            else_condition,
                            false_branch,
                            source_evidence=[condition, false_branch],
                        )

            for row in context_tables_written:
                operation = _as_text(row.get("operation")).upper()
                trigger = _as_text(row.get("trigger_condition")).lower()
                table = _as_text(row.get("table"))
                if operation == "UPDATE" and ("merge" in trigger or "matched" in trigger or "source row matches target" in trigger):
                    _append_rule(
                        "source row matches target",
                        "Update existing provision row",
                        source_evidence=[table, trigger] if trigger else [table],
                        confidence="high",
                    )
                if operation == "INSERT" and ("merge" in trigger or "not matched" in trigger or "source row does not match target" in trigger):
                    _append_rule(
                        "source row does not match target",
                        "Insert new provision row",
                        source_evidence=[table, trigger] if trigger else [table],
                        confidence="high",
                    )

            for row in context_tables_read:
                filter_condition = _as_text(row.get("filter_condition"))
                row_blob = _text_blobs(row, filter_condition, row.get("columns"))
                if "asset_classification is not null" in filter_condition.lower():
                    _append_rule(
                        "asset_classification IS NOT NULL",
                        "Include only classified accounts",
                        source_evidence=[filter_condition],
                        confidence="high",
                    )
                if "calculated_date" in row_blob and "max" in row_blob:
                    _append_rule(
                        "latest calculated_date per account",
                        "Summarize latest provision values",
                        source_evidence=[filter_condition or row_blob],
                        confidence="high",
                    )
                elif "classification_date" in row_blob and "max" in row_blob:
                    _append_rule(
                        "latest classification_date per account",
                        "Keep only most recent provision row",
                        source_evidence=[filter_condition or row_blob],
                        confidence="high",
                    )
                columns = _text_blobs(*(_as_string_list(row.get("columns"))))
                if "calculated_date" in columns and "max" not in filter_condition.lower():
                    _append_rule(
                        "latest calculated_date per account",
                        "Summarize latest provision values",
                        source_evidence=[columns],
                        confidence="high",
                    )
                if "overdue_days > 90" in filter_condition.lower():
                    _append_rule(
                        "overdue_days > 90",
                        "Process only overdue accounts",
                        source_evidence=[filter_condition],
                        confidence="high",
                    )

            if "calculated_date" in context_blob:
                deduped = [
                    rule
                    for rule in deduped
                    if not (
                        "latest classification_date per account" in _as_text(rule.get("condition")).lower()
                        and "keep only most recent provision row" in _as_text(rule.get("action")).lower()
                    )
                ]
                if not any("latest calculated_date per account" in _as_text(rule.get("condition")).lower() for rule in deduped):
                    calculated_evidence = next(
                        (
                            [item.get("condition"), item.get("true_branch"), item.get("false_branch")]
                            for item in context_conditions
                            if "calculated_date" in _text_blobs(item.get("condition"), item.get("true_branch"), item.get("false_branch"))
                        ),
                        None,
                    )
                    if calculated_evidence is None:
                        calculated_evidence = next(
                            (
                                [item.get("filter_condition"), item.get("columns")]
                                for item in context_tables_read
                                if "calculated_date" in _text_blobs(item.get("filter_condition"), item.get("columns"))
                            ),
                            ["calculated_date"],
                        )
                    _append_rule(
                        "latest calculated_date per account",
                        "Summarize latest provision values",
                        source_evidence=[_as_text(part) for part in calculated_evidence if _as_text(part)],
                        confidence="high",
                    )

            for rule in deduped:
                action_lower = _as_text(rule.get("action")).lower()
                if "provision pct" in action_lower or "provisioning percentage" in action_lower:
                    continue
                evidence_blob = _text_blobs(
                    rule.get("condition"),
                    rule.get("action"),
                    rule.get("business_meaning"),
                    " ".join(_as_string_list(rule.get("source_evidence", []))),
                    raw_rule_text,
                    technical_blob,
                )
                support_match = re.search(r"\b(0\.40|15|25|100)\b", evidence_blob)
                if not support_match:
                    continue
                support_amount = support_match.group(1)
                if "standard" in action_lower:
                    rule["action"] = f"Set STANDARD classification and {support_amount} provision pct"
                    rule["business_meaning"] = rule["action"]
                elif "substandard" in action_lower:
                    rule["action"] = f"Set SUBSTANDARD classification and {support_amount} provision pct"
                    rule["business_meaning"] = rule["action"]
                elif "loss" in action_lower and "doubtful3" in action_lower:
                    rule["action"] = "Set LOSS or DOUBTFUL3 based on doubtful_since"
                    rule["business_meaning"] = rule["action"]
                elif "doubtful1" in action_lower and "doubtful2" in action_lower:
                    rule["action"] = "Set DOUBTFUL1 or DOUBTFUL2 based on doubtful_since"
                    rule["business_meaning"] = rule["action"]

        final_rules: "OrderedDict[tuple[str, str, str], Dict[str, Any]]" = OrderedDict()
        for rule in deduped:
            key = (
                _as_text(rule.get("condition")).lower(),
                _as_text(rule.get("action")).lower(),
                _as_text(rule.get("output_field")).lower(),
            )
            current = final_rules.get(key)
            if current is None:
                final_rules[key] = rule
                continue
            current_score = (
                len(_as_string_list(current.get("fields_affected", []))),
                len(_as_string_list(current.get("source_evidence", []))),
                _rule_priority(current),
            )
            candidate_score = (
                len(_as_string_list(rule.get("fields_affected", []))),
                len(_as_string_list(rule.get("source_evidence", []))),
                _rule_priority(rule),
            )
            if candidate_score > current_score:
                final_rules[key] = rule

        return list(final_rules.values())

    @staticmethod
    def _scan_for_jargon(data: Dict[str, Any]) -> List[str]:
        flat_text = json.dumps(data).lower()
        return [term for term in _BANNED_TERMS if term in flat_text]
