"""
agents/logic_extractor.py
--------------------------
Logic Extraction Agent.

For each code chunk (plus the pattern/domain context retrieved by the
Pattern Retrieval Agent), this agent performs a *technical* pass that
produces a structured, intermediate JSON extraction of:

    - conditions / branches (IF / CASE / WHEN)
    - decision chains: multi-branch IF/ELSIF/ELSE (or equivalent CASE) ladders that test
      the same subject and assign one or more fields per branch, captured as one linked
      structure (subject + ordered branches + per-branch field assignments) rather than as
      several disconnected "conditions" entries - this is what lets the downstream Rule
      Synthesizer represent a classification/threshold ladder as one rule per output field
      with correctly-ordered decision_logic_rows, instead of having to reverse-engineer the
      ladder's structure from prose and risk misattributing an outcome to the wrong branch.
    - loops / cursors and what they iterate over
    - tables read (with columns + filter conditions + confidence)
    - tables written (with operation type + trigger condition + confidence)
    - calculations / formulas
    - exception handling behavior
    - anything the model could not confidently determine (ambiguities)

This is still a *technical* extraction (it may still use SQL
terminology) - translating it into pure business language is the job
of the downstream Rule Synthesizer Agent. Keeping these two concerns
separate keeps each prompt focused and each agent independently
testable.

All prompt content is loaded from prompts/logic_extraction.yaml via the
centralized `prompts.prompt_loader` - nothing here is a hardcoded prompt
string. The prompt is selected per SQL dialect (Oracle vs T-SQL).

Every LLM response is passed through the output guardrails in
`guardrails.py`: the JSON shape is validated/repaired, and every
table/column name the model claims is cross-checked against the actual
source code chunk (anti-hallucination grounding) before being trusted.

Calls an OpenAI-compatible chat completion API directly - there is no
orchestration framework in this module; a "chain" here is just one
Python method calling `client.chat.completions.create(...)`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List
from typing import Optional

from src.ingestion.guardrails import ground_extraction_against_source, validate_extraction_shape
from src.core.llm_client import supports_chat_completion_seed
from src.prompts.prompt_loader import get_prompt_set, render_user_prompt

_EMPTY_EXTRACTION: Dict[str, Any] = {
    "conditions": [],
    "decision_chains": [],
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
    chunk_context: List[str] = field(default_factory=list)
    embedded_sql: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=lambda: dict(_EMPTY_EXTRACTION))
    raw_response: str = ""
    parse_error: str = ""
    guardrail_warnings: List[str] = field(default_factory=list)


class LogicExtractionAgent:
    """Runs the technical extraction call over a single code chunk using
    the configured chat completion client directly.
    """

    def __init__(self, client, model: str, temperature: float = 0.1, seed: Optional[int] = 0):
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

    def extract(
        self,
        chunk_id: str,
        chunk_kind: str,
        code_chunk: str,
        rag_context: str,
        object_type: str,
        object_name: str,
        chunk_context: List[str] | None = None,
        embedded_sql: List[str] | None = None,
        dialect: str = "oracle",
        model: str | None = None,
    ) -> ChunkExtraction:
        """`model`, if given, overrides the agent's configured model for
        just this call - lets callers pick a different model per run
        without re-constructing the agent.
        """
        prompt_set = get_prompt_set("logic_extraction.yaml", dialect=dialect)
        context_path = chunk_context or []
        embedded_sql_context = embedded_sql or []
        user_prompt = render_user_prompt(
            prompt_set["user_template"],
            object_type=object_type,
            object_name=object_name,
            dialect=dialect,
            chunk_kind=chunk_kind,
            chunk_context=" > ".join(context_path) if context_path else "None",
            embedded_sql_context="\n".join(f"- {stmt}" for stmt in embedded_sql_context)
            if embedded_sql_context
            else "None",
            rag_context=rag_context,
            code_chunk=code_chunk,
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
        data, shape_warnings = validate_extraction_shape(data)
        guardrail_warnings.extend(shape_warnings)
        guardrail_warnings.extend(ground_extraction_against_source(data, code_chunk))

        return ChunkExtraction(
            chunk_id=chunk_id,
            chunk_kind=chunk_kind,
            chunk_context=context_path,
            embedded_sql=embedded_sql_context,
            data=data,
            raw_response=raw_response,
            parse_error=error,
            guardrail_warnings=guardrail_warnings,
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
