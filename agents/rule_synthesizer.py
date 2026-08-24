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

from guardrails import ground_business_rules_against_extraction, validate_synthesis_shape
from prompts.prompt_loader import get_prompt_set, render_user_prompt

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

        normalized: List[Dict[str, Any]] = []
        for rule in raw_rules:
            if not isinstance(rule, dict):
                continue

            fields_affected = _as_string_list(rule.get("fields_affected", []))
            output_field = _as_text(rule.get("output_field")) or (", ".join(fields_affected) if fields_affected else "")
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

            normalized.append(
                {
                    "rule_name": _as_text(rule.get("rule_name"))
                    or _as_text(rule.get("condition"))
                    or _as_text(rule.get("action")),
                    "output_field": output_field,
                    "business_meaning": business_meaning,
                    "eligibility": eligibility,
                    "decision_logic": decision_logic,
                    "decision_logic_rows": decision_logic_rows,
                    "tie_priority_handling": tie_priority_handling,
                    "default": default_value,
                    "when_not_eligible": when_not_eligible,
                    "condition": rule.get("condition", ""),
                    "action": rule.get("action", ""),
                    "fields_affected": fields_affected,
                    "rule_type": rule.get("rule_type", ""),
                    "confidence": rule.get("confidence", ""),
                    "validation_status": rule.get("validation_status", "unverified"),
                    "source_evidence": _as_string_list(rule.get("source_evidence", [])),
                    "source_chunks": _as_string_list(rule.get("source_chunks", [])),
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
