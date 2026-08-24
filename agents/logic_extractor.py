"""
agents/logic_extractor.py
--------------------------
Logic Extraction Agent.

For each code chunk (plus the pattern/domain context retrieved by the
Pattern Retrieval Agent), this agent performs a *technical* pass that
produces a structured, intermediate JSON extraction of:

    - conditions / branches (IF / CASE / WHEN)
    - loops / cursors and what they iterate over
    - tables read (with columns + filter conditions)
    - tables written (with operation type + trigger condition)
    - calculations / formulas
    - exception handling behavior
    - anything the model could not confidently determine (ambiguities)

This is still a *technical* extraction (it may still use SQL
terminology) - translating it into pure business language is the job
of the downstream Rule Synthesizer Agent. Keeping these two concerns
separate keeps each prompt focused and each agent independently
testable.

Calls the Groq API directly via the official `groq` SDK - there is no
orchestration framework in this module; a "chain" here is just one
Python method calling `client.chat.completions.create(...)`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

# --------------------------------------------------------------------------
# Prompt content
# --------------------------------------------------------------------------

LOGIC_EXTRACTION_SYSTEM_PROMPT = """You are a senior database engineer performing a precise, \
technical reverse-engineering pass over a fragment of a banking PL/SQL object. \
You are NOT writing business documentation yet - that happens in a later stage. \
Your only job here is accurate, structured technical extraction.

You will be given:
1. A chunk of PL/SQL / SQL code (this may be a declaration section, a cursor, \
the main executable body, a nested block, or the exception section).
2. Retrieved reference context describing common SQL/PLSQL construct semantics \
and relevant banking/regulatory domain rules (e.g. RBI IRAC norms). Use this \
context to correctly interpret constructs, but only extract what is actually \
present in the code chunk.

Return STRICT JSON ONLY (no markdown fences, no commentary) matching exactly
this schema:

{
  "conditions": [
    {"condition": "<the literal condition/expression>", "true_branch": "<what happens>", "false_branch": "<what happens, or null>"}
  ],
  "loops": [
    {"loop_type": "cursor|for|while|basic", "iterates_over": "<table/cursor/collection>", "purpose": "<what it processes>"}
  ],
  "tables_read": [
    {"table": "<TABLE_NAME>", "columns": ["COL1","COL2"], "filter_condition": "<WHERE clause / condition, or null>"}
  ],
  "tables_written": [
    {"table": "<TABLE_NAME>", "operation": "INSERT|UPDATE|DELETE|MERGE", "columns": ["COL1","COL2"], "trigger_condition": "<condition under which the write happens, or null>"}
  ],
  "calculations": [
    {"result": "<what is being computed>", "formula": "<the literal expression>"}
  ],
  "exception_handling": [
    {"handler": "<exception name or WHEN OTHERS>", "behavior": "<rollback/log/re-raise/silent/etc>"}
  ],
  "ambiguities": [
    "<anything unclear, unresolved dynamic SQL, or logic you could not confidently determine>"
  ]
}

Rules:
- If a category has nothing present in this chunk, return an empty list for it - never fabricate entries.
- For every entry in "tables_written", list the specific column(s) actually \
assigned/inserted/affected by that write in "columns" (e.g. for an UPDATE, the \
columns on the left-hand side of SET; for an INSERT, the columns in the column \
list or positionally matched to the VALUES/SELECT list; for a MERGE, the columns \
touched by the matched WHEN clause(s) that apply). List every distinct column \
touched across all branches that lead to this write, even if only some branches \
touch a given column.
- Never guess the meaning of unresolved dynamic SQL (EXECUTE IMMEDIATE with a runtime-built string); \
add it to "ambiguities" instead. If a write's target columns cannot be determined \
because the write itself is unresolved dynamic SQL, return an empty list for \
"columns" on that entry rather than guessing, and add the unresolved part to \
"ambiguities".
- Keep field values literal/precise and short (technical detail is fine here).
"""


def _build_user_prompt(
    object_type: str,
    object_name: str,
    chunk_kind: str,
    rag_context: str,
    code_chunk: str,
) -> str:
    return f"""OBJECT TYPE: {object_type}
OBJECT NAME: {object_name}
CHUNK KIND: {chunk_kind}

--- RETRIEVED REFERENCE CONTEXT ---
{rag_context}

--- CODE CHUNK ---
{code_chunk}

Return the JSON extraction now."""


_EMPTY_EXTRACTION: Dict[str, Any] = {
    "conditions": [],
    "loops": [],
    "tables_read": [],
    "tables_written": [],
    "calculations": [],
    "exception_handling": [],
    "ambiguities": [],
}


@dataclass
class ChunkExtraction:
    chunk_id: str
    chunk_kind: str
    data: Dict[str, Any] = field(default_factory=lambda: dict(_EMPTY_EXTRACTION))
    raw_response: str = ""
    parse_error: str = ""


class LogicExtractionAgent:
    """Runs the technical extraction call over a single code chunk using
    the Groq API directly.
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

    def extract(
        self,
        chunk_id: str,
        chunk_kind: str,
        code_chunk: str,
        rag_context: str,
        object_type: str,
        object_name: str,
        model: str | None = None,
    ) -> ChunkExtraction:
        """`model`, if given, overrides the agent's configured model for
        just this call - lets callers (e.g. a UI model-switcher) pick a
        different Groq model per run without re-constructing the agent.
        """
        user_prompt = _build_user_prompt(
            object_type=object_type,
            object_name=object_name,
            chunk_kind=chunk_kind,
            rag_context=rag_context,
            code_chunk=code_chunk,
        )

        response = self.client.chat.completions.create(
            model=model or self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": LOGIC_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_response = response.choices[0].message.content or ""

        data, error = self._parse_json(raw_response)
        return ChunkExtraction(
            chunk_id=chunk_id,
            chunk_kind=chunk_kind,
            data=data,
            raw_response=raw_response,
            parse_error=error,
        )

    @staticmethod
    def _parse_json(raw_response: str) -> tuple[Dict[str, Any], str]:
        cleaned = raw_response.strip()
        # strip markdown code fences if the model added them anyway
        cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", cleaned, flags=re.MULTILINE).strip()
        try:
            parsed = json.loads(cleaned)
            merged = dict(_EMPTY_EXTRACTION)
            merged.update({k: v for k, v in parsed.items() if k in _EMPTY_EXTRACTION})
            return merged, ""
        except json.JSONDecodeError as exc:
            fallback = dict(_EMPTY_EXTRACTION)
            fallback["ambiguities"] = [
                "Automatic extraction for this chunk returned malformed JSON and "
                "could not be parsed; this chunk needs manual review."
            ]
            return fallback, str(exc)