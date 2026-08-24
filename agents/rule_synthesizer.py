"""
Rule Synthesizer Agent - THE MOST CRITICAL AGENT in the pipeline.

Takes the merged, technical, per-chunk extractions produced by the
Logic Extraction Agent and rewrites them as clear, numbered,
business-intent rules. This is where the system earns (or loses) the
core requirement of the whole project: the output must explain WHAT a
rule accomplishes and WHY it exists from a business/regulatory
standpoint - never restate SQL/PLSQL syntax in English.

The prompt below is deliberately explicit and includes a banned-word
list, because prompt design for this exact agent is called out as the
hardest and most important part of the whole build.

Calls the Groq API directly via the official `groq` SDK - no
orchestration framework is involved.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

# --------------------------------------------------------------------------
# Prompt content
# --------------------------------------------------------------------------

RULE_SYNTHESIS_SYSTEM_PROMPT = """You are a senior business analyst who specializes in \
core-banking and regulatory (RBI IRAC) domain knowledge. You are reviewing a \
TECHNICAL extraction (already produced by a separate tool) of what a banking \
database procedure/function/view/trigger does, and your job is to rewrite it as \
a set of clear BUSINESS RULES that a non-technical banking operations, audit, \
or compliance reader could understand.

You must explain what the logic ACCOMPLISHES and WHY it exists (the business \
or regulatory intent), never HOW it is implemented in code.

DETERMINISM — THIS OUTPUT WILL BE DIFFED ACROSS RUNS ON THE SAME INPUT:
- Given the same technical extraction, you must always produce the same \
business rules, steps, calculations, and ambiguities — the same items, the \
same wording, the same order. Do not introduce run-to-run variation.
- Order "step_by_step_flow" and "business_rules" strictly by the order the \
underlying logic appears in the merged technical extraction — never by \
importance or severity.
- Use plain, literal, consistent phrasing. Describe the same kind of \
operation (e.g. two similar field updates) the same way each time. Do not \
hedge ("likely", "probably", "seems to") on anything the extraction states \
directly — state it plainly. Save uncertainty language for genuine gaps, \
and put those only in "ambiguities".
- Never invent field names, thresholds, counts, or examples that are not \
present in the technical extraction.

FIELD-LEVEL PRECISION — NAME WHAT IS ACTUALLY CHANGED:
- Whenever a business rule's "action" results in data being written or \
updated, name the specific business field/attribute affected (e.g. "sets \
the account's asset classification to Sub-Standard", "updates the \
provisioning amount", "marks the overdue days counter") — never a vague \
"updates the record" or "modifies the data" with no named field.
- If the technical extraction identifies the exact column, use its business \
meaning (not the raw column name) if a business meaning is available; \
otherwise use the raw column/field name rather than omitting it.
- If a rule updates multiple fields, state each one explicitly in the \
action text rather than summarizing them away.
- In addition to naming the field(s) in the "action" text, every business \
rule whose action writes to the database must also list those same field(s) \
in a separate "fields_affected" array on that rule, using the identical \
business-meaning names used in the action text (not raw column names, \
unless no business meaning is available). If the rule does not write any \
data (e.g. it only reads, validates, or branches), "fields_affected" must \
be an empty list - never omit the key and never guess a name to fill it.
- If the specific field being written truly cannot be determined from the \
extraction (e.g. it came from unresolved dynamic SQL), do NOT guess a field \
name — write the action in terms of what business outcome is intended, set \
"fields_affected" to an empty list, and add a corresponding entry to \
"ambiguities" explaining which field could not be pinned down.

STRICT STYLE RULES:
- NEVER use these words/phrases, or close synonyms of them, in your output: \
"IF-ELSIF chain", "IF statement", "ELSE branch", "loop", "cursor", "FOR loop", \
"WHILE loop", "UPDATE statement", "INSERT statement", "SELECT statement", \
"MERGE statement", "SQL", "PL/SQL", "variable", "exception block", "WHEN OTHERS", \
"NULL check", "syntax", "function call", "procedure call", "table join".
- Do not restate code structure ("first it does X, then it does Y in the code") - \
describe operational/business sequence instead ("the system first verifies X \
before it proceeds to Y").
- Where the extraction includes banking/regulatory context (e.g. RBI IRAC \
thresholds), explicitly connect the rule to that regulatory intent.
- If the extraction lists an ambiguity, carry it forward honestly - never invent \
a plausible-sounding business meaning for something that was not confidently \
extracted.
- Be concise and precise. Prefer plain English banking terminology (e.g. \
"overdue days", "asset classification", "provisioning amount", "outstanding \
balance") over generic terms.

AMBIGUITIES — NEVER QUOTE THE SOURCE:
- Every string in "ambiguities" must be written entirely in your own \
analytical words. Do NOT copy, paste, or closely paraphrase code comments, \
string literals, or raw code text from the technical extraction — this \
includes developer comments (e.g. "-- TODO", "/* legacy hack */"), \
commented-out code, or embedded error message strings, even if the \
technical extraction contains them verbatim.
- Instead, describe: (a) what part of the logic is affected, (b) what is \
unresolved or unclear about its business effect, and (c) why it could not \
be determined from the extraction. You may refer to a developer note \
existing without quoting its literal text (e.g. "a nearby developer note \
suggests this path may be deprecated, which could not be confirmed from \
the extraction").
- Never include file paths, line numbers, or raw code fragments in \
"ambiguities" - describe the logic in business terms instead.

Return STRICT JSON ONLY (no markdown fences, no commentary) matching exactly
this schema:

{
  "purpose_summary": "<2-4 sentence plain-language business impact of the whole object>",
  "step_by_step_flow": ["<numbered-ready business-language operational step>", "..."],
  "business_rules": [
    {"condition": "<business-language condition>", "action": "<business-language resulting action, naming the specific field(s) affected when data is written>", "fields_affected": ["<business field name written by this rule>", "..."]}
  ],
  "calculations": [
    {"metric": "<what is being calculated, business term>", "explanation": "<plain-language formula breakdown>"}
  ],
  "exception_handling_summary": "<plain-language operational risk summary of what happens on failure paths>",
  "ambiguities": ["<carried-forward or newly identified items needing human review, written in your own words with no quoted source text, or empty list>"]
}

"fields_affected" must always be present on every item in "business_rules", \
as an array of strings (use an empty array [] when the rule writes no data). \
Never set "fields_affected" to null or omit it.
"""


def _build_user_prompt(
    object_name: str,
    object_type: str,
    parameter_summary: str,
    merged_extraction: Dict[str, Any],
) -> str:
    return f"""OBJECT NAME: {object_name}
OBJECT TYPE: {object_type}
BUSINESS ROLE OF PARAMETERS: {parameter_summary or "No parameters."}

--- MERGED TECHNICAL EXTRACTION (all code chunks combined) ---
{json.dumps(merged_extraction, indent=2)}

Synthesize the business rules now, following the schema and style rules exactly."""


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
    "merge statement", "cursor", "pl/sql", "exception block", "when others",
]


@dataclass
class SynthesisResult:
    data: Dict[str, Any] = field(default_factory=lambda: dict(_EMPTY_SYNTHESIS))
    raw_response: str = ""
    parse_error: str = ""
    jargon_flags: List[str] = field(default_factory=list)


class RuleSynthesizerAgent:
    """Runs the business-rule synthesis call over the merged technical
    extraction for the whole object, using the Groq API directly.
    """

    def __init__(self, client, model: str, temperature: float = 0.1):
        """
        Args:
            client: an initialized `groq.Groq` client instance.
            model: the Groq model name to call (configurable per pipeline run).
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
        model: str | None = None,
    ) -> SynthesisResult:
        """`model`, if given, overrides the agent's configured model for
        just this call - lets callers (e.g. a UI model-switcher) pick a
        different Groq model per run without re-constructing the agent.
        """
        user_prompt = _build_user_prompt(
            object_name=object_name,
            object_type=object_type,
            parameter_summary=parameter_summary,
            merged_extraction=merged_extraction,
        )

        response = self.client.chat.completions.create(
            model=model or self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": RULE_SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_response = response.choices[0].message.content or ""

        data, error = self._parse_json(raw_response)
        jargon_flags = self._scan_for_jargon(data)
        return SynthesisResult(
            data=data,
            raw_response=raw_response,
            parse_error=error,
            jargon_flags=jargon_flags,
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
        "condition", "action", and "fields_affected" - regardless of what
        the model actually returned.

        This exists so downstream consumers (UI rendering, exports, diffing
        across runs) can rely on a stable schema and never hit a KeyError
        or a None where a list was expected, even if:
          - the model is an older/cheaper Groq model that ignores the new
            "fields_affected" instruction and omits the key entirely,
          - the model returns "fields_affected" as a single string instead
            of a list,
          - the model returns null instead of an empty list,
          - a business rule entry itself isn't a dict (malformed item).

        Normalizing here (rather than trusting the prompt alone) is what
        keeps the schema change backward-compatible and avoids breaking
        any existing integration that consumes this output.
        """
        if not isinstance(raw_rules, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for rule in raw_rules:
            if not isinstance(rule, dict):
                continue

            condition = rule.get("condition", "")
            action = rule.get("action", "")

            fields_affected = rule.get("fields_affected", [])
            if fields_affected is None:
                fields_affected = []
            elif isinstance(fields_affected, str):
                # Model returned a single field as a bare string rather than
                # a one-item list - coerce rather than drop the data.
                fields_affected = [fields_affected] if fields_affected.strip() else []
            elif isinstance(fields_affected, list):
                fields_affected = [
                    str(item).strip() for item in fields_affected if str(item).strip()
                ]
            else:
                fields_affected = []

            normalized.append(
                {
                    "condition": condition,
                    "action": action,
                    "fields_affected": fields_affected,
                }
            )
        return normalized

    @staticmethod
    def _scan_for_jargon(data: Dict[str, Any]) -> List[str]:
        flat_text = json.dumps(data).lower()
        return [term for term in _BANNED_TERMS if term in flat_text]