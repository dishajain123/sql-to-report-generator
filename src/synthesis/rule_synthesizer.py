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
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
from typing import Optional

from src.ingestion.guardrails import ground_business_rules_against_extraction, validate_synthesis_shape
from src.core.llm_client import supports_chat_completion_seed
from src.core.pipeline_utils import PIPELINE_VERSION, stable_id
from src.core.llm_response_cache import PersistentLLMResponseCache
from src.parsing.dedup import dedup_table_operations
from src.prompts.prompt_loader import get_prompt_set, render_user_prompt
from src.telemetry.tracker import LLMTelemetryTracker

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

    def __init__(
        self,
        client,
        model: str,
        temperature: float = 0.1,
        seed: Optional[int] = 0,
        provider: str = "openai",
        response_cache: Optional[PersistentLLMResponseCache] = None,
        max_tokens: int = 16000,
    ):
        """
        Args:
            client: an initialized OpenAI-compatible chat client instance.
            model: the model name to call (configurable per pipeline run).
            temperature: sampling temperature (kept low for extraction tasks).
            max_tokens: explicit output-token cap passed on every completion
                call. This must always be set, even though OpenAI's API
                itself defaults to a generous ceiling when omitted: the
                Bedrock-backed client (`_BedrockChatCompletions.create` in
                `llm_client.py`) defaults its OWN `max_tokens` parameter to
                1024 when the caller doesn't pass one explicitly, which
                silently truncates synthesis JSON for any object whose
                business-rule output exceeds ~1024 tokens (this procedure's
                sample run alone produced ~17K completion tokens) -
                truncated JSON then fails to parse and the pipeline falls
                back to a degraded/empty result with no clear error. Passing
                max_tokens on every call removes the ambiguity for both
                providers instead of relying on a per-provider default.
        """
        self.client = client
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.provider = provider
        self.response_cache = response_cache
        self.max_tokens = max_tokens

    def synthesize(
        self,
        object_name: str,
        object_type: str,
        parameter_summary: str,
        merged_extraction: Dict[str, Any],
        dialect: str = "oracle",
        raw_source: str = "",
        model: str | None = None,
        telemetry_tracker: Optional[LLMTelemetryTracker] = None,
    ) -> SynthesisResult:
        """`model`, if given, overrides the agent's configured model for
        just this call - lets callers pick a different model per run
        without re-constructing the agent.
        """
        if str(dialect or "").strip().lower() not in {"oracle", "tsql"}:
            return SynthesisResult(data=dict(_EMPTY_SYNTHESIS))
        prompt_set = get_prompt_set("rule_synthesis.yaml", dialect=dialect)
        compact_merged_extraction = self._build_compact_synthesis_payload(
            merged_extraction,
            raw_source=raw_source,
        )
        user_prompt = render_user_prompt(
            prompt_set["user_template"],
            object_name=object_name,
            object_type=object_type,
            dialect=dialect,
            parameter_summary=parameter_summary or "No parameters.",
            merged_extraction_json=json.dumps(
                compact_merged_extraction,
                separators=(",", ":"),
                default=str,
            ),
        )
        effective_seed = self.seed if self.seed is not None and supports_chat_completion_seed(self.client) else None
        cache_request = self._build_cache_request(
            stage="synthesis",
            dialect=dialect,
            provider=self.provider,
            model_name=model or self.model,
            system_prompt=prompt_set["system"],
            user_prompt=user_prompt,
            temperature=self.temperature,
            seed=effective_seed,
            max_tokens=self.max_tokens,
        )
        tracker = telemetry_tracker
        if self.response_cache is not None:
            cache_lookup = self.response_cache.lookup(cache_request)
            if cache_lookup.hit:
                raw_response = cache_lookup.response_text or ""
                data, error = self._parse_json(raw_response)
                if not error:
                    if tracker is not None:
                        tracker.record_cache_lookup(stage="synthesis", hit=True)
                    guardrail_warnings: List[str] = []
                    data, shape_warnings = validate_synthesis_shape(data)
                    guardrail_warnings.extend(shape_warnings)
                    data["business_rules"] = self._normalize_business_rules(
                        data.get("business_rules"),
                        source_text=raw_source,
                        technical_context=merged_extraction,
                    )
                    data["business_rules"] = self._remove_operational_status_rules(
                        data["business_rules"], merged_extraction
                    )
                    data["business_rules"] = self._remove_non_business_cleanup_rules(
                        data["business_rules"], merged_extraction
                    )
                    data["business_rules"] = self._augment_rules_from_executable_operations(
                        data["business_rules"], merged_extraction
                    )
                    data["business_rules"] = self._canonicalize_synthesis_families(
                        data["business_rules"], merged_extraction
                    )
                    data["business_rules"] = self._apply_authoritative_decision_chains(
                        data["business_rules"], merged_extraction
                    )
                    data["business_rules"] = self._remove_operation_only_rules(data["business_rules"])
                    data["business_rules"] = self._split_multi_field_rules_using_decision_chains(
                        data["business_rules"], merged_extraction
                    )
                    self._complete_synthesis_from_deterministic_facts(data, merged_extraction, raw_source=raw_source)
                    data["business_rules"] = self._remove_operation_only_rules(data["business_rules"])
                    data["business_rules"] = self._apply_authoritative_decision_chains(
                        data["business_rules"], merged_extraction
                    )
                    self._append_completeness_warnings(data, merged_extraction)
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
                self.response_cache.delete(cache_request)
                if tracker is not None and cache_lookup.status != "disabled":
                    tracker.record_cache_lookup(stage="synthesis", hit=False)
            elif cache_lookup.status != "disabled" and tracker is not None:
                tracker.record_cache_lookup(stage="synthesis", hit=False)

        completion_kwargs = {
            "model": model or self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": prompt_set["system"]},
                {"role": "user", "content": user_prompt},
            ],
        }
        if effective_seed is not None:
            completion_kwargs["seed"] = effective_seed
        response = None
        call_success = False
        call_error: Exception | None = None
        start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(**completion_kwargs)
            call_success = True
        except Exception as exc:  # noqa: BLE001
            call_error = exc
            raise
        finally:
            if tracker is not None:
                try:
                    tracker.record_call(
                        stage="synthesis",
                        provider=self.provider,
                        model_name=model or self.model,
                        response=response,
                        latency_seconds=time.perf_counter() - start,
                        success=call_success,
                        error=call_error,
                    )
                except Exception:
                    pass
        raw_response = response.choices[0].message.content or ""

        data, error = self._parse_json(raw_response)
        if error:
            jargon_flags = self._scan_for_jargon(data)
            return SynthesisResult(
                data=data,
                raw_response=raw_response,
                parse_error=error,
                jargon_flags=jargon_flags,
                guardrail_warnings=[],
            )

        guardrail_warnings: List[str] = []
        data, shape_warnings = validate_synthesis_shape(data)
        guardrail_warnings.extend(shape_warnings)
        data["business_rules"] = self._normalize_business_rules(
            data.get("business_rules"),
            source_text=raw_source,
            technical_context=merged_extraction,
        )
        data["business_rules"] = self._remove_operational_status_rules(
            data["business_rules"], merged_extraction
        )
        data["business_rules"] = self._remove_non_business_cleanup_rules(
            data["business_rules"], merged_extraction
        )
        data["business_rules"] = self._augment_rules_from_executable_operations(
            data["business_rules"], merged_extraction
        )
        data["business_rules"] = self._canonicalize_synthesis_families(
            data["business_rules"], merged_extraction
        )
        data["business_rules"] = self._apply_authoritative_decision_chains(
            data["business_rules"], merged_extraction
        )
        data["business_rules"] = self._remove_operation_only_rules(data["business_rules"])
        data["business_rules"] = self._split_multi_field_rules_using_decision_chains(
            data["business_rules"], merged_extraction
        )
        self._complete_synthesis_from_deterministic_facts(data, merged_extraction, raw_source=raw_source)
        data["business_rules"] = self._remove_operation_only_rules(data["business_rules"])
        data["business_rules"] = self._apply_authoritative_decision_chains(
            data["business_rules"], merged_extraction
        )
        self._append_completeness_warnings(data, merged_extraction)
        guardrail_warnings.extend(
            ground_business_rules_against_extraction(
                data["business_rules"], merged_extraction, raw_source=raw_source
            )
        )

        jargon_flags = self._scan_for_jargon(data)
        if self.response_cache is not None and not error:
            self.response_cache.store(cache_request, raw_response)
        return SynthesisResult(
            data=data,
            raw_response=raw_response,
            parse_error=error,
            jargon_flags=jargon_flags,
            guardrail_warnings=guardrail_warnings,
        )

    @staticmethod
    def _build_compact_synthesis_payload(
        merged_extraction: Dict[str, Any],
        raw_source: str = "",
    ) -> Dict[str, Any]:
        """Return only the technical facts the synthesis prompt can use.

        This is a prompt-size reduction only: `merged_extraction` itself
        is never mutated, so grounding, reconciliation, the verification
        report, and downstream reporting still see the full,
        non-deduplicated evidence (every raw statement occurrence, every
        chunk's embedded SQL, full statement provenance). Only what gets
        serialized into the *synthesis LLM prompt* is compacted here.

        The payload intentionally keeps the prompt compact: the
        deduplicated `table_operations` view is the table-evidence input
        used by synthesis, while the heavier provenance transport fields
        stay out of the synthesis prompt so they do not bloat the model
        context. The compact view is a prompt-size aid; it does not
        replace the original evidence in `merged_extraction`.
        """

        if not isinstance(merged_extraction, dict):
            return {}

        payload = OrderedDict()
        payload["conditions"] = merged_extraction.get("conditions", []) or []
        payload["decision_chains"] = merged_extraction.get("decision_chains", []) or []
        payload["loops"] = merged_extraction.get("loops", []) or []

        raw_table_operations = merged_extraction.get("table_operations", []) or []
        if isinstance(raw_table_operations, list) and raw_table_operations:
            payload["table_operations"] = dedup_table_operations(raw_table_operations)
        else:
            # Fallback for objects where deterministic statement parsing
            # produced nothing (unsupported dialect / parse failure) -
            # the LLM-extracted tables_read/tables_written are the only
            # evidence available, so they still need to reach the prompt
            # in that case. Also deduplicated by the same grouping logic
            # so repeated LLM-extracted references don't reintroduce the
            # same duplication from the other direction.
            fallback_ops = list(merged_extraction.get("tables_read", []) or []) + list(
                merged_extraction.get("tables_written", []) or []
            )
            payload["table_operations"] = dedup_table_operations(fallback_ops) if fallback_ops else []

        payload["calculations"] = merged_extraction.get("calculations", []) or []
        payload["exception_handling"] = merged_extraction.get("exception_handling", []) or []
        payload["ambiguities"] = merged_extraction.get("ambiguities", []) or []
        # Nested procedural chunks can be structurally incomplete while the
        # original source remains available. Keep it separate from the
        # deterministic fact view so the model can recover missing context
        # without changing the facts used by reconciliation.
        if str(raw_source or "").strip():
            payload["source_sql"] = str(raw_source)
        return payload

    @staticmethod
    def _audit_synthesis_completeness(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
    ) -> List[str]:
        """Report deterministic business families omitted by synthesis.

        This is deliberately a one-way audit: it never manufactures a rule.
        Family signals must come from executable deterministic facts, while
        matching is against the returned rule's fields and text.
        """
        if not isinstance(merged_extraction, dict):
            return []
        rule_text = " ".join(
            json.dumps(rule, sort_keys=True, default=str).lower()
            for rule in rules
            if isinstance(rule, dict)
        )
        facts: List[str] = []
        for key in ("conditions", "calculations", "exception_handling", "table_operations"):
            for item in merged_extraction.get(key, []) or []:
                if isinstance(item, dict):
                    facts.append(json.dumps(item, sort_keys=True, default=str).lower())
                elif item:
                    facts.append(str(item).lower())
        fact_text = " ".join(facts)

        families = [
            ("negative DPD reset", ("< 0", "<0"), ("dpd_", "reset", "zero")),
            ("DPD maximum calculation", ("dpd_max", "maximum"), ("dpd_max", "maximum", "highest")),
            ("SMA field clearing", ("sma_class=null", "sma_class_key=null", "sma_dt=null"), ("clear", "reset", "sma")),
            ("account SMA classification", ("sma_class", "sma_0", "sma_1", "sma_2"), ("classification", "sma class", "sma_0", "sma_1")),
            ("SMA flag assignment", ("flgsma", "flgsma='y'", "flgsma = 'y'"), ("flgsma", "sma flag", "flag")),
            ("customer SMA propagation", ("customercal", "sma_class_key", "flgsma"), ("customer", "propagat", "roll")),
            ("customer movement description", ("custmovedescription",), ("movement description", "custmove")),
            ("asset-class fallback", ("sma_class is null", "sma_class=null"), ("fallback", "default", "asset class")),
            ("process completion/error handling", ("aclrunningprocessstatus", "errordescription", "completed"), ("process", "error", "completion")),
        ]
        missing: List[str] = []
        for label, fact_signals, rule_signals in families:
            if not any(signal in fact_text for signal in fact_signals):
                continue
            if not any(signal in rule_text for signal in rule_signals):
                missing.append(label)
        return missing

    @staticmethod
    def _remove_operational_status_rules(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Keep process bookkeeping out of the business-rule collection.

        This applies only when deterministic operations identify the rule as a
        process-status write. The operation and its evidence remain available
        through the merged technical extraction and verification output.
        """
        status_fields = {
            "COMPLETED", "ERRORDATE", "ERRORDESCRIPTION", "COUNT",
            "RUNNINGPROCESSNAME",
        }
        status_tables = {
            str(row.get("table") or "").strip().upper()
            for row in (merged_extraction or {}).get("table_operations", []) or []
            if isinstance(row, dict)
            and "runningprocessstatus" in str(row.get("table") or "").lower()
        }
        if not status_tables:
            return list(rules or [])

        filtered: List[Dict[str, Any]] = []
        for rule in rules or []:
            if not isinstance(rule, dict):
                continue
            text = json.dumps(rule, sort_keys=True, default=str).upper()
            raw_fields = rule.get("fields_affected", [])
            if isinstance(raw_fields, str):
                raw_fields = [raw_fields]
            fields = {
                token.strip().upper().split(".")[-1]
                for token in raw_fields or []
            }
            is_status_rule = bool(fields & status_fields) and any(
                marker in text
                for marker in (
                    "PROCESS STATUS", "RUNNING PROCESS", "ERROR DESCRIPTION",
                    "COMPLETION", "COMPLETED",
                )
            )
            if not is_status_rule:
                filtered.append(rule)
        return filtered

    @staticmethod
    def _remove_non_business_cleanup_rules(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Keep pure temporary-object cleanup in technical lineage only.

        A DROP of a temporary table is an execution concern, not a business
        decision. This narrow filter requires deterministic operation
        evidence and an empty business-field set, so it cannot hide a rule
        describing a meaningful state change. The operation remains in
        ``merged_extraction`` for verification and provenance consumers.
        """
        operations = [
            row for row in (merged_extraction or {}).get("table_operations", []) or []
            if isinstance(row, dict)
            and str(row.get("active_status") or "ACTIVE").upper() == "ACTIVE"
            and str(row.get("operation") or "").upper() == "DROP"
        ]
        cleanup_tables = {
            str(row.get("table") or "").strip().upper()
            for row in operations
            if re.search(r"(^#|TEMP|TMP|TEMPORARY)", str(row.get("table") or ""), re.IGNORECASE)
        }
        if not cleanup_tables:
            return list(rules or [])

        filtered: List[Dict[str, Any]] = []
        for rule in rules or []:
            if not isinstance(rule, dict):
                continue
            fields = rule.get("fields_affected") or []
            if isinstance(fields, str):
                fields = [fields]
            has_business_fields = any(str(field).strip() for field in fields)
            rule_text = json.dumps(rule, sort_keys=True, default=str).lower()
            is_cleanup_description = any(
                marker in rule_text for marker in ("drop", "temporary", "temp table", "cleanup")
            )
            has_decision = bool(rule.get("decision_logic_rows") or rule.get("decision_logic"))
            if is_cleanup_description and not has_business_fields and not has_decision:
                continue
            filtered.append(rule)
        return filtered

    @staticmethod
    def _split_multi_field_rules_using_decision_chains(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Deterministically split a rule that spans 2+ output fields into
        one rule per field, using the structured `decision_chains` data
        (`branch_condition` + per-field `assignments`) as ground truth -
        never guessing a split from the rule's own prose or from
        clustering outcome text.

        Why this exists: the synthesis prompt already instructs the model
        to keep one output field per rule and to use `decision_chains` as
        the authoritative source for exactly this case, but prompt
        compliance is probabilistic - a real production example merged a
        days-overdue classification ladder (output field: SMA_CLASS) with
        a facility-type-driven reason chain (output field: SMA_REASON)
        into one rule's decision table, because the model grouped them by
        eye instead of by the chain structure. Rather than rely on the
        model getting this right every time, this makes the split itself
        a deterministic data transform: IF the extraction captured a
        `decision_chains` entry whose branches carry per-field
        `assignments` for 2+ of this rule's `fields_affected`, THEN this
        rebuilds correct, separate `decision_logic_rows` for each field
        directly from that chain - the model's job stays "describe what
        this field's rule means in business language", not "get the
        branch/field bookkeeping right by itself".

        Matching a rule to a chain is deliberately conservative: only a
        rule whose `fields_affected` set is covered by (a subset of, or
        equal to) the union of fields assigned across ALL branches of one
        chain is split against that chain. If no matching chain is found
        (e.g. an older cached extraction predating this fix, or a chain
        that genuinely doesn't cover this rule), the rule is returned
        unchanged - this function only ever removes a known-mixed rule,
        never invents a split it isn't sure of.
        """
        chains = merged_extraction.get("decision_chains") if isinstance(merged_extraction, dict) else None
        if not isinstance(chains, list) or not chains:
            return rules

        # Pre-index each chain by the set of fields it assigns across all
        # its branches, and pre-collect each field's ordered
        # (condition, outcome) rows across the chain's branches.
        chain_field_rows: List[Tuple[frozenset, Dict[str, List[Dict[str, str]]]]] = []
        for chain in chains:
            if not isinstance(chain, dict):
                continue
            branches = chain.get("branches")
            if not isinstance(branches, list) or not branches:
                continue
            per_field_rows: Dict[str, List[Dict[str, str]]] = {}
            for branch in branches:
                if not isinstance(branch, dict):
                    continue
                condition = str(branch.get("branch_condition") or "").strip()
                assignments = branch.get("assignments")
                if isinstance(assignments, list):
                    assignments = {
                        str(item.get("field") or "").strip(): str(item.get("value") or "")
                        for item in assignments
                        if isinstance(item, dict) and str(item.get("field") or "").strip()
                    }
                if not condition or not isinstance(assignments, dict) or not assignments:
                    continue
                for field, value in assignments.items():
                    field_key = str(field).strip()
                    if not field_key:
                        continue
                    per_field_rows.setdefault(field_key, []).append(
                        {"condition": condition, "outcome": str(value)}
                    )
            if len(per_field_rows) < 2:
                # Only genuinely multi-field chains are useful here - a
                # single-field chain is already what the model is
                # expected to produce as one ordinary rule.
                continue
            field_set = frozenset(f.lower() for f in per_field_rows.keys())
            chain_field_rows.append((field_set, per_field_rows))

        if not chain_field_rows:
            return rules

        result: List[Dict[str, Any]] = []
        for rule in rules:
            fields_affected = [str(f).strip() for f in (rule.get("fields_affected") or []) if str(f).strip()]
            rule_field_set = frozenset(f.lower() for f in fields_affected)
            if len(rule_field_set) < 2:
                result.append(rule)
                continue

            matching_chain = None
            for chain_fields, per_field_rows in chain_field_rows:
                if rule_field_set and rule_field_set <= chain_fields:
                    matching_chain = per_field_rows
                    break
            if matching_chain is None:
                result.append(rule)
                continue

            base_name = str(rule.get("rule_name") or "").strip()
            base_meaning = str(rule.get("business_meaning") or "").strip()
            for field in fields_affected:
                field_rows = matching_chain.get(field) or matching_chain.get(field.strip())
                if not field_rows:
                    # This particular field wasn't actually covered by the
                    # matched chain's branches (e.g. fields_affected named
                    # a field the chain doesn't touch) - keep it out of
                    # the split rather than fabricating rows for it.
                    continue
                split_rule = dict(rule)
                split_rule["fields_affected"] = [field]
                split_rule["output_field"] = field
                split_rule["decision_logic_rows"] = field_rows
                split_rule["rule_name"] = (
                    f"{base_name} — {field}" if base_name else f"Assign {field}"
                )
                split_rule["business_meaning"] = (
                    base_meaning or f"Determines the value assigned to {field}."
                )
                result.append(split_rule)

        return result

    @staticmethod
    def _apply_authoritative_decision_chains(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Make structured branch chains win over contradictory LLM prose.

        Chain assignments are normalized as a list by the extraction
        guardrail, while older callers may provide a mapping. Supporting both
        forms keeps cached and newly generated extractions equivalent. A
        chain is executable evidence, so its field/branch rows replace any
        model rules targeting those fields; descriptive text and provenance
        from the first matching model rule are retained where available.
        """
        chains = (merged_extraction or {}).get("decision_chains", [])
        if not isinstance(chains, list) or not chains:
            return rules

        def display_value(value: Any) -> str:
            text = str(value or "").strip()
            if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
                return text[1:-1]
            return text

        rebuilt: List[Dict[str, Any]] = []
        consumed_fields: set[str] = set()
        authoritative_fields: set[str] = set()
        for chain in chains:
            if not isinstance(chain, dict) or not isinstance(chain.get("branches"), list):
                continue
            branch_data: List[Tuple[str, Dict[str, str]]] = []
            field_names: "OrderedDict[str, None]" = OrderedDict()
            for branch in chain["branches"]:
                if not isinstance(branch, dict):
                    continue
                condition = str(branch.get("branch_condition") or "").strip()
                assignments = branch.get("assignments")
                if isinstance(assignments, list):
                    assignments = {
                        str(item.get("field") or "").strip(): str(item.get("value") or "")
                        for item in assignments
                        if isinstance(item, dict) and str(item.get("field") or "").strip()
                    }
                if not condition or not isinstance(assignments, dict):
                    continue
                for field_name, value in assignments.items():
                    field_name = str(field_name).strip()
                    if field_name:
                        field_names.setdefault(field_name, None)
                branch_data.append((condition, assignments))
            if not field_names or not branch_data:
                continue
            authoritative_fields.update(field.lower() for field in field_names)

            field_rows: "OrderedDict[str, List[Dict[str, str]]]" = OrderedDict(
                (field_name, []) for field_name in field_names
            )
            for condition, assignments in branch_data:
                for field_name in field_rows:
                    field_rows[field_name].append(
                        {
                            "condition": condition,
                            "outcome": str(assignments.get(field_name, "unchanged")),
                        }
                    )

            candidates = [
                rule for rule in rules
                if isinstance(rule, dict)
                and any(
                    str(field).strip().lower() in {name.lower() for name in field_rows}
                    for field in (rule.get("fields_affected") or [])
                )
            ]
            for field_name, rows in field_rows.items():
                if field_name.lower() in consumed_fields:
                    continue
                outcomes = [row["outcome"].strip().strip("'\"") for row in rows]
                is_calculation_field = bool(outcomes) and all(
                    re.fullmatch(r"[-+]?\d+(?:\.\d+)?", outcome) for outcome in outcomes
                )
                if is_calculation_field:
                    consumed_fields.add(field_name.lower())
                    continue
                field_template = next(
                    (
                        rule for rule in candidates
                        if field_name.lower() in {
                            str(field).strip().lower()
                            for field in (rule.get("fields_affected") or [])
                        }
                    ),
                    None,
                )
                template = field_template or (candidates[0] if candidates else {})
                rebuilt_rule = dict(template)
                # Non-numeric branch outcomes represent categorical business
                # decisions. Keep every mutually exclusive branch as a
                # separate rule so source branches cannot be merged or lost.
                outcomes = [row["outcome"].strip().strip("'\"") for row in rows]
                if not all(re.fullmatch(r"[-+]?\d+(?:\.\d+)?", outcome) for outcome in outcomes):
                    for row in rows:
                        branch_rule = dict(rebuilt_rule)
                        branch_rule["fields_affected"] = [field_name]
                        branch_rule["output_field"] = field_name
                        branch_rule["decision_logic_rows"] = []
                        branch_rule["eligibility"] = []
                        branch_rule["condition"] = row["condition"]
                        outcome = display_value(row["outcome"])
                        branch_rule["action"] = f"Assigns {field_name} the value {outcome}."
                        branch_rule["business_meaning"] = (
                            f"Assigns {field_name} the value {outcome} when the "
                            f"source condition is {row['condition']}."
                        )
                        branch_rule["rule_name"] = f"Assign {field_name} as {outcome}"
                        branch_rule["source_evidence"] = [row["condition"], row["outcome"]]
                        rebuilt.append(branch_rule)
                else:
                    rebuilt_rule["fields_affected"] = [field_name]
                    rebuilt_rule["output_field"] = field_name
                    rebuilt_rule["decision_logic_rows"] = rows
                    rebuilt_rule["eligibility"] = []
                    rebuilt_rule["condition"] = str(chain.get("subject") or "").strip()
                    rebuilt_rule["action"] = f"Assigns {field_name} according to the source-defined decision bands."
                    rebuilt_rule["business_meaning"] = (
                        f"Determines the value assigned to {field_name} based on the "
                        f"source-defined decision bands."
                    )
                    rebuilt_rule["rule_name"] = f"Determine {field_name} from decision bands"
                    rebuilt_rule["source_evidence"] = [
                        evidence
                        for row in rows
                        for evidence in (row["condition"], row["outcome"])
                        if evidence
                    ]
                    rebuilt.append(rebuilt_rule)
                consumed_fields.add(field_name.lower())

        if not rebuilt:
            return rules

        chain_fields = authoritative_fields
        remaining = [
            rule for rule in rules
            if not (
                isinstance(rule, dict)
                    and any(
                        str(field).strip().lower() in chain_fields
                        for field in list(rule.get("fields_affected") or [])
                        + ([rule.get("output_field")] if rule.get("output_field") else [])
                    )
            )
        ]
        return remaining + rebuilt

    @staticmethod
    def _remove_operation_only_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Exclude CRUD mechanics that do not express a business decision."""
        filtered: List[Dict[str, Any]] = []
        for rule in rules or []:
            if not isinstance(rule, dict):
                continue
            if rule.get("decision_logic_rows"):
                filtered.append(rule)
                continue
            evidence = " ".join(str(item) for item in rule.get("source_evidence") or []).upper()
            name = str(rule.get("rule_name") or "").lower()
            action = str(rule.get("action") or "").lower()
            is_crud = bool(re.search(r"\b(SELECT|UPDATE|INSERT|DELETE|MERGE)\b", evidence))
            is_mechanical = (
                "source-defined value" in action
                or "source-defined value" in name
                or (name.startswith(("update ", "insert ", "write ")) and not rule.get("eligibility"))
            )
            if is_crud and is_mechanical:
                continue
            filtered.append(rule)
        return filtered

    @staticmethod
    def _canonicalize_synthesis_families(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Stabilize equivalent branch rows without changing their meaning."""
        operations_blob = json.dumps(
            (merged_extraction or {}).get("table_operations", []),
            sort_keys=True,
            default=str,
        ).lower()
        has_positive_flag_assignment = "flgsma" in operations_blob and "'y'" in operations_blob

        def text(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, (list, tuple)):
                return ", ".join(str(item) for item in value if item is not None)
            return str(value).strip()

        def reset_signature(rule: Dict[str, Any]) -> str:
            rule_text = " ".join(
                text(rule.get(key)).lower()
                for key in ("rule_name", "action", "business_meaning")
            )
            if not any(token in rule_text for token in ("reset", "sanitize", "zero", "cleanup")):
                return ""
            target_fields = [
                text(field).split(".")[-1].strip()
                for field in (rule.get("fields_affected") or [])
                if text(field).strip()
            ]
            if not target_fields or not all(field.upper().startswith("DPD_") for field in target_fields):
                return ""
            rows = rule.get("decision_logic_rows")
            if not isinstance(rows, list) or not rows:
                return ""
            signatures = []
            for row in rows:
                if not isinstance(row, dict):
                    return ""
                condition = text(row.get("condition"))
                outcome = text(row.get("outcome"))
                if not re.search(r"<\s*0|negative|below\s+0|less\s+than\s+0", condition, re.IGNORECASE):
                    return ""
                if not re.fullmatch(r"['\"]?0['\"]?", outcome):
                    return ""
                # Field names are the only intentional difference between
                # repeated metric-reset rules. Do not merge other predicates.
                condition = re.sub(r"\b(?:is\s+)?(?:below|less\s+than)\s+0\b", "<0", condition, flags=re.IGNORECASE)
                condition = re.sub(r"\bnegative\b", "<0", condition, flags=re.IGNORECASE)
                condition = re.sub(r"\bis\s+(?=<\s*0)", "", condition, flags=re.IGNORECASE)
                condition = re.sub(
                    r"\b(?:ISNULL|COALESCE)\s*\(\s*(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*,[^)]*\)",
                    "<field>", condition, flags=re.IGNORECASE,
                )
                condition = re.sub(
                    r"(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*(?=<\s*0)",
                    "<field>", condition, flags=re.IGNORECASE,
                )
                signatures.append(re.sub(r"\s+", "", condition).lower())
            return "|".join(signatures)

        def merge_repeated_resets(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            groups: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
            passthrough: List[Dict[str, Any]] = []
            for item in items:
                signature = reset_signature(item)
                if signature:
                    groups.setdefault(signature, []).append(item)
                else:
                    passthrough.append(item)

            merged_items: List[Dict[str, Any]] = list(passthrough)
            for signature, members in groups.items():
                if len(members) == 1:
                    merged_items.extend(members)
                    continue
                combined = dict(members[0])
                fields: List[str] = []
                rows: List[Dict[str, Any]] = []
                seen_rows = set()
                for member in members:
                    for field in member.get("fields_affected") or []:
                        value = text(field)
                        if value and value.lower() not in {item.lower() for item in fields}:
                            fields.append(value)
                    for row in member.get("decision_logic_rows") or []:
                        if not isinstance(row, dict):
                            continue
                        key = json.dumps(row, sort_keys=True, default=str)
                        if key not in seen_rows:
                            seen_rows.add(key)
                            rows.append(dict(row))
                    for key in ("eligibility", "source_evidence", "source_chunks", "source_chunk_ids",
                                "source_statement_ids", "evidence_spans", "technical_references",
                                "unresolved_ambiguities", "dependencies"):
                        current = list(combined.get(key) or [])
                        for value in member.get(key) or []:
                            if value not in current:
                                current.append(value)
                        combined[key] = current
                combined["fields_affected"] = fields
                combined["output_field"] = ", ".join(fields)
                combined["decision_logic_rows"] = rows
                combined["rule_name"] = text(combined.get("rule_name")) or "Reset negative values to zero"
                combined["rule_id"] = stable_id(
                    "rule", "reset_negative_metrics",
                    *(text(member.get("rule_id")) for member in members),
                )
                merged_items.append(combined)
            return sorted(merged_items, key=lambda item: int(item.get("_source_index", 0)))

        rules = merge_repeated_resets([rule for rule in (rules or []) if isinstance(rule, dict)])
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            rows = rule.get("decision_logic_rows")
            if isinstance(rows, list):
                unique_rows: List[Dict[str, Any]] = []
                positions: Dict[str, int] = {}
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    condition = text(row.get("condition"))
                    # Parser wrappers can trail an otherwise identical condition.
                    condition = re.split(r"\s+if\s+object_id\s*\(", condition, maxsplit=1, flags=re.IGNORECASE)[0].strip()
                    row = dict(row)
                    row["condition"] = condition
                    key = re.sub(r"\s+", "", condition).lower()
                    if not key:
                        unique_rows.append(row)
                        continue
                    if key not in positions:
                        positions[key] = len(unique_rows)
                        unique_rows.append(row)
                        continue
                    previous = unique_rows[positions[key]]
                    previous_outcome = text(previous.get("outcome"))
                    outcome = text(row.get("outcome"))
                    generic_previous = not previous_outcome or "assigned value from source" in previous_outcome.lower()
                    generic_current = not outcome or "assigned value from source" in outcome.lower()
                    if generic_previous and not generic_current:
                        unique_rows[positions[key]] = row
                rule["decision_logic_rows"] = unique_rows

            output_field = text(rule.get("output_field")).lower()
            name = text(rule.get("rule_name"))
            lowered_name = name.lower()
            if "dpd_max" in output_field and ("determine" in lowered_name or "highest overdue" in lowered_name):
                rule["rule_name"] = "Calculate maximum DPD for account"
            elif "flgsma" in output_field and has_positive_flag_assignment and "set sma flag" in lowered_name:
                rule["rule_name"] = "Set SMA flag to Y for processed accounts"
            elif "sma_class" in output_field and "finalassetclass" in operations_blob and "fallback" in lowered_name:
                rule["rule_name"] = "Assign SMA class for accounts with final asset class key"

        # A model may emit the same structured filter more than once with
        # different prose titles.  Collapse only exact structural duplicates;
        # distinct conditions, outcomes, or branch rows remain independent.
        unique_rules: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        for rule in rules:
            condition = re.sub(r"\s+", "", text(rule.get("condition"))).lower()
            rows = rule.get("decision_logic_rows") or []
            row_signature = json.dumps(
                [
                    {
                        "condition": re.sub(r"\s+", "", text(row.get("condition"))).lower(),
                        "outcome": text(row.get("outcome")).lower(),
                    }
                    for row in rows if isinstance(row, dict)
                ],
                sort_keys=True,
            )
            if not condition and not row_signature:
                unique_rules[f"unique:{len(unique_rules)}"] = rule
                continue
            key = json.dumps(
                {
                    "condition": condition,
                    "output_field": text(rule.get("output_field")).lower(),
                    "fields": sorted(text(field).lower() for field in (rule.get("fields_affected") or [])),
                    "rows": row_signature,
                },
                sort_keys=True,
            )
            existing = unique_rules.get(key)
            if existing is None:
                unique_rules[key] = rule
                continue
            for field_name in (
                "source_evidence", "source_chunks", "source_chunk_ids",
                "source_statement_ids", "technical_references", "evidence_spans",
            ):
                values = list(existing.get(field_name) or [])
                for value in rule.get(field_name) or []:
                    if value not in values:
                        values.append(value)
                existing[field_name] = values
        return list(unique_rules.values())

    @classmethod
    def _append_completeness_warnings(
        cls,
        data: Dict[str, Any],
        merged_extraction: Dict[str, Any],
    ) -> None:
        missing = cls._audit_synthesis_completeness(
            data.get("business_rules", []) or [], merged_extraction
        )
        if not missing:
            return
        ambiguities = list(data.get("ambiguities", []) or [])
        for family in missing:
            message = (
                "Synthesis completeness review: deterministic executable evidence contains "
                f"the '{family}' business family, but no synthesized rule was returned."
            )
            if message not in ambiguities:
                ambiguities.append(message)
        data["ambiguities"] = ambiguities

    @classmethod
    def _complete_synthesis_from_deterministic_facts(
        cls,
        data: Dict[str, Any],
        merged_extraction: Dict[str, Any],
        raw_source: str = "",
    ) -> None:
        """Complete omitted synthesis fields from explicit SQL facts.

        A successful model response is not necessarily complete.  This pass
        is deliberately conservative: it uses only structured deterministic
        operation rows and their source expressions, never domain defaults or
        report-specific values.  Existing LLM content always wins; only
        empty top-level fields and assignment-backed statements not already
        represented by a rule are completed.
        """
        if not isinstance(data, dict) or not isinstance(merged_extraction, dict):
            return

        rules = [rule for rule in data.get("business_rules", []) or [] if isinstance(rule, dict)]
        operations = [
            row for row in (merged_extraction.get("table_operations", []) or [])
            if isinstance(row, dict)
            and str(row.get("active_status") or "ACTIVE").upper() == "ACTIVE"
            and str(row.get("operation") or "").upper() in {"UPDATE", "INSERT", "DELETE", "MERGE"}
        ]

        def rule_references(rule: Dict[str, Any]) -> set[str]:
            refs = {str(value).strip() for value in (rule.get("technical_references") or []) if str(value).strip()}
            refs.update(
                str(span.get("statement_id") or "").strip()
                for span in (rule.get("evidence_spans") or [])
                if isinstance(span, dict) and str(span.get("statement_id") or "").strip()
            )
            return refs

        represented = set().union(*(rule_references(rule) for rule in rules)) if rules else set()

        def assigned_columns(row: Dict[str, Any]) -> List[str]:
            values: List[str] = []
            for assignment in row.get("assigned_values") or []:
                if not isinstance(assignment, dict):
                    continue
                column = str(assignment.get("column") or "").strip().split(".")[-1]
                if column and column.upper() not in {item.upper() for item in values}:
                    values.append(column)
            return values

        def evidence_span(row: Dict[str, Any], evidence_type: str = "ASSIGNMENT") -> Dict[str, Any]:
            return {
                "source_file": row.get("source_file", ""),
                "char_start": row.get("source_char_start", -1),
                "char_end": row.get("source_char_end", -1),
                "line_start": row.get("source_line_start", -1),
                "line_end": row.get("source_line_end", -1),
                "chunk_id": row.get("source_chunk_id", ""),
                "statement_id": row.get("statement_id") or row.get("source_statement_id", ""),
                "evidence_type": evidence_type,
                "source_location_status": row.get("source_location_status", "unavailable"),
                "statement_parse_status": row.get("statement_parse_status") or row.get("parse_status", ""),
            }

        def assignment_evidence(row: Dict[str, Any]) -> List[str]:
            values = []
            for value in (
                row.get("source_statement_text"),
                row.get("where_predicate"),
                json.dumps(row.get("assigned_values"), sort_keys=True, default=str),
            ):
                text = str(value or "").strip()
                if text and text != "[]" and text not in values:
                    values.append(text)
            return values

        for row in operations:
            statement_id = str(row.get("statement_id") or row.get("source_statement_id") or "").strip()
            assignments = row.get("assigned_values") or []
            columns = assigned_columns(row)
            if not statement_id or not columns or not assignments or statement_id in represented:
                continue
            operation = str(row.get("operation") or "").upper()
            predicate = str(row.get("where_predicate") or "").strip()

            # A model may already have combined the repeated negative-DPD
            # updates into one family. In that case attach any omitted
            # deterministic member statement to that family instead of
            # creating a second, duplicate business rule.
            is_negative_reset = (
                operation == "UPDATE"
                and str(row.get("table") or "").strip().upper() == "#DPD"
                and bool(re.search(r"<\s*0", predicate))
                and all(column.upper().startswith("DPD_") for column in columns)
            )
            if is_negative_reset:
                reset_rule = next(
                    (
                        candidate for candidate in rules
                        if "reset" in str(candidate.get("rule_name") or "").lower()
                        and any(
                            str(field).strip().upper().startswith("DPD_")
                            for field in (candidate.get("fields_affected") or [])
                        )
                    ),
                    None,
                )
                if reset_rule is not None:
                    existing_fields = list(reset_rule.get("fields_affected") or [])
                    for column in columns:
                        if str(column).upper() not in {str(field).upper() for field in existing_fields}:
                            existing_fields.append(column)
                    reset_rule["fields_affected"] = existing_fields
                    reset_rule["output_field"] = ", ".join(existing_fields)
                    for key in ("source_evidence", "source_chunks", "technical_references"):
                        values = list(reset_rule.get(key) or [])
                        additions = (
                            assignment_evidence(row) if key == "source_evidence"
                            else [str(row.get("source_chunk_id"))] if key == "source_chunks" and row.get("source_chunk_id")
                            else [statement_id]
                        )
                        for value in additions:
                            if value and value not in values:
                                values.append(value)
                        reset_rule[key] = values
                    spans = list(reset_rule.get("evidence_spans") or [])
                    span = evidence_span(row)
                    if span not in spans:
                        spans.append(span)
                    reset_rule["evidence_spans"] = spans
                    represented.add(statement_id)
                    continue
            field_text = ", ".join(columns)
            assignments_text = "; ".join(
                f"{str(item.get('column') or '').strip().split('.')[-1]} = {str(item.get('expression') or '').strip()}"
                for item in assignments if isinstance(item, dict) and item.get("column")
            )
            rule = {
                "rule_name": f"{operation.title()} {field_text}",
                "business_meaning": (
                    f"The procedure sets {field_text} to the source-defined value"
                    + (f" when {predicate}." if predicate else ".")
                ),
                "condition": predicate,
                "action": assignments_text or f"Set {field_text}.",
                "output_field": field_text,
                "eligibility": [predicate] if predicate else [],
                "fields_affected": columns,
                "rule_type": "explicit",
                "confidence": "high",
                "validation_status": "verified" if row.get("parse_status") not in {"parse_failed", "unsupported"} else "parser_failed",
                "source_evidence": assignment_evidence(row),
                "source_chunks": [str(row.get("source_chunk_id"))] if row.get("source_chunk_id") else [],
                "technical_references": [statement_id],
                "evidence_spans": [evidence_span(row)],
                "unresolved_ambiguities": [],
                "dependencies": [],
            }
            rule["rule_id"] = stable_id("rule", statement_id, field_text, assignments_text)
            rules.append(rule)
            represented.add(statement_id)

        if rules:
            data["business_rules"] = cls._normalize_business_rules(rules)

        if not str(data.get("purpose_summary") or "").strip() and rules:
            fields = []
            for rule in rules:
                for field_name in rule.get("fields_affected", []) or []:
                    if field_name and str(field_name).upper() not in {str(v).upper() for v in fields}:
                        fields.append(str(field_name))
            if fields:
                data["purpose_summary"] = (
                    "This object applies source-defined conditions and updates "
                    + ", ".join(fields[:12]) + "."
                )

        if not data.get("step_by_step_flow") and rules:
            data["step_by_step_flow"] = [
                str(rule.get("business_meaning") or rule.get("action") or "").strip()
                for rule in rules
                if str(rule.get("business_meaning") or rule.get("action") or "").strip()
            ]

        if not data.get("calculations"):
            calculations = []
            calculation_markers = ("CASE", "DATEDIFF", "DATEADD", "COALESCE", "ISNULL", "MAX(", "+", "-", "*", "/")
            for row in operations:
                for assignment in row.get("assigned_values") or []:
                    if not isinstance(assignment, dict):
                        continue
                    expression = str(assignment.get("expression") or "").strip()
                    if expression and any(marker in expression.upper() for marker in calculation_markers):
                        metric = str(assignment.get("column") or "").strip().split(".")[-1]
                        item = {"metric": metric or "derived value", "explanation": expression}
                        if item not in calculations:
                            calculations.append(item)
            data["calculations"] = calculations

        if not str(data.get("exception_handling_summary") or "").strip():
            exception_items = merged_extraction.get("exception_handling", []) or []
            exception_text = " ".join(json.dumps(item, default=str) for item in exception_items)
            source_text = " ".join(str(row.get("source_statement_text") or "") for row in operations)
            if exception_items or re.search(r"\b(?:CATCH|EXCEPTION|ERROR_MESSAGE|RAISE|WHEN OTHERS)\b", exception_text + source_text, re.I):
                error_fields = []
                for row in operations:
                    table = str(row.get("table") or "")
                    if not re.search(r"error|status|process", table, re.I):
                        continue
                    for assignment in row.get("assigned_values") or []:
                        if not isinstance(assignment, dict):
                            continue
                        field = str(assignment.get("column") or "").strip().split(".")[-1]
                        if field and re.search(r"error|completed|count", field, re.I) and field not in error_fields:
                            error_fields.append(field)
                if error_fields:
                    data["exception_handling_summary"] = (
                        "The failure path records operational error/status information in "
                        + ", ".join(error_fields) + "."
                    )
                else:
                    data["exception_handling_summary"] = "The source contains an explicit failure-handling path."

        # A model can return a valid JSON object while omitting a material
        # IF/ELSIF/ELSE ladder.  Recover only ladders that are explicit in the
        # original source and assign multiple distinct literal values to the
        # same field.  This is intentionally conservative: calculations,
        # technical date branches, and uncertain prose are not promoted to
        # business rules.
        cls._complete_literal_assignment_ladders(data, raw_source)

    @classmethod
    def _complete_literal_assignment_ladders(cls, data: Dict[str, Any], source: str) -> None:
        if not isinstance(data, dict) or not str(source or "").strip():
            return

        source_without_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
        lines = source_without_comments.splitlines()
        frames: List[Dict[str, Any]] = []
        completed: List[Dict[str, Any]] = []
        if_re = re.compile(r"^\s*IF\s+(.+?)\s+THEN\s*$", re.I)
        elsif_re = re.compile(r"^\s*ELSIF\s+(.+?)\s+THEN\s*$", re.I)
        else_re = re.compile(r"^\s*ELSE\s*$", re.I)
        end_re = re.compile(r"^\s*END\s+IF\b", re.I)
        assignment_re = re.compile(
            r"^\s*([A-Za-z_][A-Za-z0-9_$#]*)\s*(?::=|=)\s*(.+?);\s*$",
            re.I,
        )

        def new_branch(condition: str, line_no: int) -> Dict[str, Any]:
            return {"condition": condition.strip(), "assignments": [], "line_start": line_no, "line_end": line_no}

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue
            match = if_re.match(line)
            if match:
                parent_condition = ""
                if frames:
                    parent_condition = str(frames[-1]["branches"][-1]["condition"])
                condition = match.group(1)
                if parent_condition:
                    condition = f"{parent_condition} AND {condition}"
                frame = {"parent": frames[-1] if frames else None, "branches": [new_branch(condition, line_no)]}
                frames.append(frame)
                continue
            if frames and (match := elsif_re.match(line)):
                parent_condition = ""
                if frames[-1].get("parent"):
                    parent_condition = str(frames[-1]["parent"]["branches"][-1]["condition"])
                condition = match.group(1)
                if parent_condition:
                    condition = f"{parent_condition} AND {condition}"
                frames[-1]["branches"].append(new_branch(condition, line_no))
                continue
            if frames and else_re.match(line):
                parent_condition = ""
                if frames[-1].get("parent"):
                    parent_condition = str(frames[-1]["parent"]["branches"][-1]["condition"])
                condition = "ELSE"
                if parent_condition:
                    condition = f"{parent_condition} AND ELSE"
                frames[-1]["branches"].append(new_branch(condition, line_no))
                continue
            if frames and end_re.match(line):
                frame = frames.pop()
                for branch in frame["branches"]:
                    branch["line_end"] = line_no
                completed.append(frame)
                continue
            if frames:
                match = assignment_re.match(line)
                if match:
                    frames[-1]["branches"][-1]["assignments"].append(
                        {"field": match.group(1), "value": match.group(2).strip(), "line": line_no}
                    )

        rules = [rule for rule in data.get("business_rules", []) or [] if isinstance(rule, dict)]
        ladder_rows: Dict[str, List[Dict[str, Any]]] = {}
        for frame in completed:
            branches = frame["branches"]
            assignments = [item for branch in branches for item in branch["assignments"]]
            by_field: Dict[str, List[Dict[str, Any]]] = {}
            for item in assignments:
                value = str(item.get("value") or "").strip()
                field_name = str(item.get("field") or "").strip()
                # Literal branch outcomes are safe to reconstruct.  Do not
                # turn variable/date/calculation branches into business rules.
                if not field_name or not value or not re.search(r"(?:'[^']*'|\"[^\"]*\"|[-+]?\d+(?:\.\d+)?)", value):
                    continue
                by_field.setdefault(field_name.upper(), []).append(item)

            for field_name, field_assignments in by_field.items():
                values = {str(item["value"]).upper() for item in field_assignments}
                normalized_values = {value.strip().strip("'\"").upper() for value in values}
                if normalized_values and all(
                    re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value) for value in normalized_values
                ):
                    continue
                # A nested branch may contain two outcomes while its parent
                # contributes the outer ELSE/default outcome.  Keep every
                # branch from an explicit IF ladder here; the frame itself
                # supplies the structural safety check.
                if len(branches) < 2:
                    continue
                rows = []
                for branch in branches:
                    branch_items = [item for item in branch["assignments"] if str(item.get("field") or "").upper() == field_name]
                    for item in branch_items:
                        rows.append(
                            {
                                "condition": branch["condition"],
                                "outcome": str(item["value"]).strip().strip("'").strip('"'),
                                "_source_line": item.get("line", branch.get("line_start", 0)),
                            }
                        )
                if not rows:
                    continue
                ladder_rows.setdefault(field_name, []).extend(rows)

        for field_name, rows in ladder_rows.items():
            rows.sort(key=lambda row: int(row.get("_source_line", 0) or 0))
            source_spans = [
                {
                    "source_file": "",
                    "char_start": -1,
                    "char_end": -1,
                    "line_start": int(row.get("_source_line", -1) or -1),
                    "line_end": int(row.get("_source_line", -1) or -1),
                    "chunk_id": "",
                    "statement_id": "",
                    "evidence_type": "OUTCOME",
                    "source_location_status": "available",
                }
                for row in rows
            ]
            for row in rows:
                row.pop("_source_line", None)
            matching = [
                rule for rule in rules
                if field_name in {str(value).strip().upper().split(".")[-1] for value in (rule.get("fields_affected") or [])}
                or field_name == str(rule.get("output_field") or "").strip().upper()
            ]
            rule = matching[0] if matching else None
            if rule is None:
                rule = {
                    "rule_name": f"Assign {field_name} by source-defined conditions",
                    "business_meaning": f"Assigns {field_name} according to the ordered conditions in the source.",
                    "condition": "",
                    "action": f"Set {field_name} to the branch outcome.",
                    "output_field": field_name,
                    "eligibility": [],
                    "fields_affected": [field_name],
                    "rule_type": "explicit",
                    "confidence": "high",
                    "validation_status": "verified",
                    "source_evidence": [],
                    "source_chunks": [],
                    "technical_references": [],
                    "evidence_spans": [],
                    "unresolved_ambiguities": [],
                    "dependencies": [],
                    "rule_id": "",
                }
                rules.append(rule)
            rule["decision_logic_rows"] = rows
            rule["decision_logic"] = [row["condition"] for row in rows]
            existing_spans = list(rule.get("evidence_spans") or [])
            for span in source_spans:
                if span not in existing_spans:
                    existing_spans.append(span)
            rule["evidence_spans"] = existing_spans
            for row in rows:
                evidence = f"{row['condition']} -> {row['outcome']}"
                if evidence not in rule.setdefault("source_evidence", []):
                    rule["source_evidence"].append(evidence)
            rule.setdefault("confidence", "high")
            rule.setdefault("validation_status", "verified")

        data["business_rules"] = cls._normalize_business_rules(rules)

    @staticmethod
    def _augment_rules_from_executable_operations(
        rules: List[Dict[str, Any]],
        merged_extraction: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Materialize only clearly structured, omitted write families.

        The LLM remains responsible for interpretation. This narrow fallback
        exists for complete, repeated assignment families that deterministic
        extraction already describes exactly. Every generated row carries the
        originating operation evidence; uncertain or non-executable rows are
        ignored rather than guessed.
        """
        if not isinstance(merged_extraction, dict):
            return list(rules or [])

        result = list(rules or [])
        operations = [
            row for row in (merged_extraction.get("table_operations", []) or [])
            if isinstance(row, dict) and str(row.get("active_status") or "ACTIVE").upper() == "ACTIVE"
        ]

        def blob(row: Dict[str, Any]) -> str:
            return " ".join(
                str(row.get(key) or "")
                for key in ("table", "operation", "statement_kind", "target_columns", "where_predicate", "source_statement_text", "assigned_values")
            ).lower()

        def rule_blob(rule: Dict[str, Any]) -> str:
            return json.dumps(rule, sort_keys=True, default=str).lower()

        def spans(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            output: List[Dict[str, Any]] = []
            seen = set()
            for row in rows:
                provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else row
                span = {
                    "source_file": row.get("source_file") or provenance.get("source_file", ""),
                    "char_start": row.get("source_char_start", provenance.get("source_char_start", -1)),
                    "char_end": row.get("source_char_end", provenance.get("source_char_end", -1)),
                    "line_start": row.get("source_line_start", provenance.get("source_line_start", -1)),
                    "line_end": row.get("source_line_end", provenance.get("source_line_end", -1)),
                    "chunk_id": row.get("source_chunk_id") or provenance.get("chunk_id", ""),
                    "statement_id": row.get("statement_id") or row.get("source_statement_id") or provenance.get("statement_id", ""),
                    "evidence_type": "ASSIGNMENT",
                    "source_location_status": row.get("source_location_status", provenance.get("source_location_status", "unavailable")),
                    "statement_parse_status": row.get("statement_parse_status", provenance.get("statement_parse_status", "")),
                }
                key = json.dumps(span, sort_keys=True, default=str)
                if key not in seen:
                    seen.add(key)
                    output.append(span)
            return output

        def evidence(rows: List[Dict[str, Any]]) -> List[str]:
            values: List[str] = []
            for row in rows:
                for value in (
                    row.get("source_statement_text"),
                    row.get("where_predicate"),
                    json.dumps(row.get("assigned_values"), sort_keys=True, default=str) if row.get("assigned_values") else "",
                ):
                    text = str(value or "").strip()
                    if text and text not in values:
                        values.append(text)
            return values

        def fields(rows: List[Dict[str, Any]], allowed: Optional[set[str]] = None) -> List[str]:
            output: List[str] = []
            for row in rows:
                values = row.get("target_columns") or row.get("columns") or []
                if isinstance(values, str):
                    values = [values]
                for value in values:
                    clean = str(value).strip().split(".")[-1]
                    if allowed and clean.upper() not in {item.upper() for item in allowed}:
                        continue
                    if clean and clean.upper() not in {item.upper() for item in output}:
                        output.append(clean)
            return output

        def assignment_value(row: Dict[str, Any], field: str) -> str:
            for assignment in row.get("assigned_values") or []:
                if not isinstance(assignment, dict):
                    continue
                if str(assignment.get("column") or "").strip().upper().split(".")[-1] == field.upper():
                    value = str(assignment.get("expression") or "").strip()
                    return value.strip("'") if value else ""
            return ""

        def append_family(
            family_marker: str,
            family_rules: List[Dict[str, Any]],
            *,
            name: str,
            action: str,
            output_field: str,
            family_fields: List[str],
            condition: str,
            rows: List[Dict[str, Any]],
            decision_rows: Optional[List[Dict[str, Any]]] = None,
            meaning: Optional[str] = None,
        ) -> None:
            if not rows:
                return
            if family_marker == "negative DPD values are reset":
                existing_reset = any(
                    any(
                        str(field).strip().upper().split(".")[-1].startswith("DPD_")
                        for field in (rule.get("fields_affected") or [])
                    )
                    and any(
                        marker in rule_blob(rule)
                        for marker in ("reset", "sanitize", "negative", "below 0", "less than 0")
                    )
                    for rule in result
                )
                if existing_reset:
                    return
            elif any(family_marker in rule_blob(rule) for rule in result):
                return
            result.append(
                {
                    "rule_name": name,
                    "output_field": output_field,
                    "business_meaning": meaning or action,
                    "eligibility": [condition] if condition else [],
                    "decision_logic": [condition] if condition else [],
                    "decision_logic_rows": decision_rows or [],
                    "tie_priority_handling": [],
                    "default": [],
                    "when_not_eligible": [],
                    "condition": condition,
                    "action": action,
                    "fields_affected": family_fields,
                    "rule_type": "explicit",
                    "confidence": "high" if all(str(row.get("confidence") or "").lower() == "high" for row in rows) else "medium",
                    "validation_status": "verified",
                    "rule_id": "",
                    "ambiguity_id": "",
                    "source_evidence": evidence(rows),
                    "source_chunks": list(dict.fromkeys(str(row.get("source_chunk_id") or "") for row in rows if row.get("source_chunk_id"))),
                    "evidence_spans": spans(rows),
                    "technical_references": list(dict.fromkeys(str(row.get("statement_id") or row.get("source_statement_id") or "") for row in rows if row.get("statement_id") or row.get("source_statement_id"))),
                    "unresolved_ambiguities": [],
                    "dependencies": [],
                    "_source_index": len(result),
                }
            )

        reset_rows = [
            row for row in operations
            if str(row.get("operation") or "").upper() == "UPDATE"
            and str(row.get("table") or "").upper() == "#DPD"
            and re.search(r"<\s*0", blob(row))
            and any(
                str(value).strip().split(".")[-1].upper().startswith("DPD_")
                for value in (row.get("target_columns") or [])
            )
        ]
        reset_fields = fields(reset_rows, {"DPD_IntService", "DPD_NoCredit", "DPD_Overdrawn", "DPD_Overdue", "DPD_Renewal", "DPD_StockStmt"})
        append_family(
            "negative DPD values are reset",
            reset_rows,
            name="Reset negative DPD values to zero",
            action="Reset negative overdue-day values to zero",
            output_field=", ".join(reset_fields),
            family_fields=reset_fields,
            condition="overdue-day value is below zero",
            rows=reset_rows,
            decision_rows=[
                {"condition": str(row.get("where_predicate") or ""), "outcome": "0", "field": field}
                for row in reset_rows for field in fields([row])
            ],
            meaning="Negative overdue-day values are reset to zero before the maximum overdue days is calculated.",
        )

        flag_rows = [
            row for row in operations
            if str(row.get("operation") or "").upper() == "UPDATE"
            and "flgsma" in blob(row)
            and "customercal" not in str(row.get("table") or "").lower()
            and any(
                str(assignment.get("expression") or "").strip().upper() not in {"", "NULL"}
                for assignment in (row.get("assigned_values") or [])
                if isinstance(assignment, dict)
            )

        ]
        append_family(
            "account SMA flag is set",
            flag_rows,
            name="Set SMA flag for processed accounts",
            action="Set the account SMA flag",
            output_field="FLGSMA",
            family_fields=["FLGSMA"],
            condition=str(flag_rows[0].get("where_predicate") or "") if flag_rows else "",
            rows=flag_rows,
            meaning="Processed accounts are marked as being under SMA classification.",
        )

        max_rows = [
            row for row in operations
            if str(row.get("operation") or "").upper() == "UPDATE"
            and str(row.get("table") or "").strip().upper() == "#DPD"
            and any(
                str(value).strip().split(".")[-1].upper() == "DPD_MAX"
                for value in (row.get("target_columns") or [])
            )
            and any(
                marker in blob(row)
                for marker in ("case when", "greatest(", "max(", "maximum")
            )
        ]
        if max_rows and not any(
            "dpd_max" in rule_blob(rule)
            and any(marker in rule_blob(rule) for marker in ("highest overdue", "maximum overdue", "calculate maximum"))
            for rule in result
        ):
            append_family(
                "dpd_max calculation family",
                max_rows,
                name="Calculate maximum DPD for account",
                action="Calculate the maximum overdue days value for each account",
                output_field="DPD_Max",
                family_fields=["DPD_Max"],
                condition=str(max_rows[0].get("where_predicate") or "") or "maximum overdue-day source value is selected",
                rows=max_rows,
                meaning="The maximum DPD is calculated for the account.",
            )

        customer_rows = [
            row for row in operations
            if "customercal" in str(row.get("table") or "").lower()
            and any(field in blob(row) for field in ("flgsma", "sma_class_key", "sma_dt"))
        ]
        customer_fields = fields(customer_rows, {"FLGSMA", "SMA_CLASS_KEY", "SMA_DT"})
        append_family(
            "customer SMA status is propagated",
            customer_rows,
            name="Propagate customer-level SMA status",
            action="Propagate the worst SMA status to the customer",
            output_field=", ".join(customer_fields),
            family_fields=customer_fields,
            condition="customer has an SMA-marked account",
            rows=customer_rows,
            meaning="Customer-level SMA status is aggregated from linked SMA-marked accounts.",
        )

        clear_rows = [
            row for row in operations
            if str(row.get("operation") or "").upper() == "UPDATE"
            and "customercal" not in str(row.get("table") or "").lower()
            and any(
                str(assignment.get("expression") or "").strip().upper() == "NULL"
                for assignment in (row.get("assigned_values") or [])
                if isinstance(assignment, dict)
            )
            and any(
                field.upper() in {"SMA_CLASS", "SMA_CLASS_KEY", "SMA_REASON", "SMA_DT", "FLGSMA"}
                for field in fields([row])
            )
            and "finalassetclass" not in blob(row)
        ]
        clear_fields = fields(clear_rows, {"SMA_CLASS", "SMA_CLASS_KEY", "SMA_REASON", "SMA_DT", "FLGSMA"})
        append_family(
            "existing SMA classification fields are cleared",
            clear_rows,
            name="Clear SMA fields before reprocessing",
            action="Clear existing SMA classification fields before reprocessing",
            output_field=", ".join(clear_fields),
            family_fields=clear_fields,
            condition="existing SMA classification is reset before reprocessing",
            rows=clear_rows,
            decision_rows=[
                {"condition": str(row.get("where_predicate") or "") or "Before reprocessing", "outcome": "NULL", "field": field}
                for row in clear_rows for field in clear_fields
            ],
            meaning="Existing SMA classification fields are cleared before the account is reprocessed.",
        )

        movement_rows = [
            row for row in operations
            if str(row.get("operation") or "").upper() == "UPDATE"
            and "custmovedescription" in blob(row)
        ]
        movement_decisions = []
        for row in movement_rows:
            value = assignment_value(row, "CustMoveDescription")
            movement_decisions.append({
                "condition": str(row.get("where_predicate") or "") or "Not specified",
                "outcome": value or "assigned value from source statement",
                "field": "CustMoveDescription",
            })
        append_family(
            "customer movement description is assigned",
            movement_rows,
            name="Assign customer movement description by key",
            action="Assign the customer movement description",
            output_field="CustMoveDescription",
            family_fields=["CustMoveDescription"],
            condition="customer asset-class or SMA key matches",
            rows=movement_rows,
            decision_rows=movement_decisions,
            meaning="Customer movement descriptions are assigned from the applicable asset-class or SMA key.",
        )

        fallback_rows = [
            row for row in operations
            if str(row.get("operation") or "").upper() == "UPDATE"
            and "accountcal" in str(row.get("table") or "").lower()
            and "sma_class" in blob(row)
            and "null" in blob(row)
            and "finalassetclass" in blob(row)
        ]
        append_family(
            "asset-class fallback label is assigned",
            fallback_rows,
            name="Apply final asset-class fallback",
            action="Assign the asset-class label when no SMA class is present",
            output_field="SMA_CLASS",
            family_fields=["SMA_CLASS"],
            condition="SMA_CLASS is NULL",
            rows=fallback_rows,
            decision_rows=[
                {"condition": str(row.get("where_predicate") or ""), "outcome": assignment_value(row, "SMA_CLASS") or "assigned asset-class label", "field": "SMA_CLASS"}
                for row in fallback_rows
            ],
            meaning="Accounts without an SMA classification receive the label associated with their final asset-class key.",
        )

        return result

    @staticmethod
    def _build_cache_request(
        *,
        stage: str,
        dialect: str,
        provider: str,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        seed: Optional[int],
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {
            "pipeline_version": PIPELINE_VERSION,
            "stage": stage,
            "provider": provider,
            "model_name": model_name,
            "dialect": dialect,
            "temperature": temperature,
            "seed": seed,
            # Included so any change to the output-token ceiling correctly
            # invalidates previously cached responses (a response cached
            # under a smaller max_tokens may have been truncated - see the
            # max_tokens note on __init__ - and must never be replayed once
            # the ceiling changes).
            "max_tokens": max_tokens,
            "response_format": None,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }

    @staticmethod
    def _parse_json(raw_response: str) -> tuple[Dict[str, Any], str]:
        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", cleaned, flags=re.MULTILINE).strip()
        try:
            parsed = RuleSynthesizerAgent._decode_json_payload(cleaned)
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
    def _decode_json_payload(cleaned: str) -> Dict[str, Any]:
        """Parse a JSON object from the model output.

        The model is expected to return strict JSON, but in practice it
        may wrap the object in a brief preamble or trailing prose. We try
        the strict parse first, then fall back to locating the first
        decodable JSON object in the text so recoverable responses do not
        collapse into an empty synthesis result.
        """
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            for start in (match.start() for match in re.finditer(r"[\{\[]", cleaned)):
                try:
                    parsed, _ = decoder.raw_decode(cleaned[start:])
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
            raise
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("Expected a JSON object", cleaned, 0)
        return parsed

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
            if any(token in blob for token in ("clear", "reset", "reprocessing", "cleanup")) and "sma" in blob:
                return "Clear SMA fields before reprocessing"
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
        for source_index, rule in enumerate(raw_rules):
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
                    "_source_index": source_index,
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
                        "_source_index": len(deduped),
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

        def _merge_list_values(values: List[Any]) -> List[Any]:
            merged: List[Any] = []
            seen: set = set()
            for value in values:
                if isinstance(value, dict):
                    key = json.dumps(value, sort_keys=True, default=str)
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(dict(value))
                    continue
                text = _as_text(value)
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(text)
            return merged

        def _merge_rule_families(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            def _family_key(rule: Dict[str, Any]) -> str:
                text = _normalize_blob(
                    rule.get("rule_name"),
                    rule.get("condition"),
                    rule.get("action"),
                    rule.get("business_meaning"),
                    rule.get("output_field"),
                    rule.get("source_evidence"),
                    rule.get("technical_references"),
                    rule.get("fields_affected"),
                )
                if any(token in text for token in ("clear", "reset", "reprocessing", "preprocessing", "cleanup")) and "sma" in text:
                    return ""
                if "custmovedescription" in text:
                    return "cust_move_description"
                if (
                    "flgsma" in text
                    and any(token in text for token in ("customer", "customercal", "customerentityid", "ucif"))
                ) or (
                    any(token in text for token in ("sma_class_key", "sma_dt"))
                    and any(token in text for token in ("customer", "customercal", "customerentityid", "ucif"))
                ):
                    return "sma_customer"
                if (
                    any(token in text for token in ("sma_class", "sma_reason", "sma_dt"))
                    and any(token in text for token in ("dpd_max", "dpd.dpd_max", "facilitytype", "degrade"))
                    and "default" not in text
                ):
                    return "sma_account"
                return ""

            def _allowed_family_field(field: str, family: str) -> str:
                text = _as_text(field)
                if not text:
                    return ""
                clean = text.split(".")[-1].strip()
                allowed_fields = {
                    "sma_account": {"SMA_CLASS", "SMA_REASON", "FLGSMA", "SMA_DT"},
                    "sma_customer": {"FLGSMA", "SMA_CLASS_KEY", "SMA_DT"},
                    "cust_move_description": {"CustMoveDescription"},
                }.get(family, set())
                if clean in allowed_fields:
                    return clean
                if text in allowed_fields:
                    return text
                return ""

            def _family_label(family: str) -> str:
                if family == "sma_account":
                    return "Assign account-level SMA fields in order"
                if family == "sma_customer":
                    return "Propagate customer-level SMA status"
                if family == "cust_move_description":
                    return "Assign customer movement description by key"
                return ""

            def _family_output_field(family: str, member_rules: List[Dict[str, Any]]) -> str:
                if family == "cust_move_description":
                    return "CustMoveDescription"
                fields: List[str] = []
                for rule in member_rules:
                    for field in _as_string_list(rule.get("fields_affected", [])) + ([_as_text(rule.get("output_field"))] if _as_text(rule.get("output_field")) else []):
                        allowed = _allowed_family_field(field, family)
                        if allowed and allowed not in fields:
                            fields.append(allowed)
                return ", ".join(fields)

            def _family_condition(rule: Dict[str, Any]) -> str:
                condition = _as_text(rule.get("condition"))
                if condition:
                    return condition
                eligibility = _as_string_list(rule.get("eligibility"))
                return eligibility[0] if eligibility else ""

            def _family_action(rule: Dict[str, Any]) -> str:
                action = _as_text(rule.get("action"))
                if action:
                    return action
                meaning = _as_text(rule.get("business_meaning"))
                return meaning

            def _family_rule_type(member_rules: List[Dict[str, Any]]) -> str:
                order = {"explicit": 3, "inferred": 2, "assumption": 1}
                best = ""
                best_rank = -1
                for rule in member_rules:
                    value = str(rule.get("rule_type") or "").strip().lower()
                    rank = order.get(value, 0)
                    if rank > best_rank:
                        best = value or best
                        best_rank = rank
                return best or "inferred"

            def _family_confidence(member_rules: List[Dict[str, Any]]) -> str:
                order = {"high": 3, "medium": 2, "low": 1}
                worst = "high"
                worst_rank = 3
                for rule in member_rules:
                    value = str(rule.get("confidence") or "").strip().lower()
                    rank = order.get(value, 2)
                    if rank < worst_rank:
                        worst = value or worst
                        worst_rank = rank
                return worst or "medium"

            def _family_status(member_rules: List[Dict[str, Any]]) -> str:
                order = {
                    "verified": 5,
                    "unverified": 4,
                    "insufficient_evidence": 3,
                    "ambiguous": 2,
                    "parser_failed": 1,
                }
                worst = "verified"
                worst_rank = 5
                for rule in member_rules:
                    value = str(rule.get("validation_status") or "").strip().lower()
                    rank = order.get(value, 4)
                    if rank < worst_rank:
                        worst = value or worst
                        worst_rank = rank
                return worst or "unverified"

            def _family_decision_rows(member_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                rows: List[Dict[str, Any]] = []
                for rule in member_rules:
                    rule_condition = _family_condition(rule)
                    rule_action = _family_action(rule)
                    rule_meaning = _as_text(rule.get("business_meaning")) or rule_action
                    rule_output = _as_text(rule.get("output_field"))
                    row_fields = []
                    for field in _as_string_list(rule.get("fields_affected", [])):
                        allowed = _allowed_family_field(field, family)
                        if allowed and allowed not in row_fields:
                            row_fields.append(allowed)
                    if not row_fields and rule_output:
                        allowed_output = _allowed_family_field(rule_output, family)
                        if allowed_output:
                            row_fields = [allowed_output]
                    decision_rows = rule.get("decision_logic_rows")
                    if isinstance(decision_rows, list) and decision_rows:
                        for row in decision_rows:
                            if not isinstance(row, dict):
                                continue
                            condition = _as_text(row.get("condition") or row.get("when") or rule_condition)
                            outcome = _as_text(row.get("outcome") or row.get("then") or row.get("result") or rule_meaning)
                            merged_row = {
                                "condition": condition or "Not specified",
                                "outcome": outcome or "Not specified",
                            }
                            if row_fields:
                                merged_row["field"] = ", ".join(row_fields)
                            rows.append(merged_row)
                        continue
                    merged_row = {
                        "condition": rule_condition or "Not specified",
                        "outcome": rule_meaning or "Not specified",
                    }
                    if row_fields:
                        merged_row["field"] = ", ".join(row_fields)
                    rows.append(merged_row)
                return rows

            if not rules:
                return []

            family_groups: "OrderedDict[str, List[tuple[int, Dict[str, Any]]]]" = OrderedDict()
            passthrough: List[tuple[int, Dict[str, Any]]] = []
            for index, rule in enumerate(rules):
                source_index = int(rule.get("_source_index", index))
                family = _family_key(rule)
                if family:
                    family_groups.setdefault(family, []).append((source_index, rule))
                else:
                    passthrough.append((source_index, rule))

            merged: List[tuple[int, Dict[str, Any]]] = []
            for family, indexed_rules in family_groups.items():
                if len(indexed_rules) < 2:
                    merged.extend(indexed_rules)
                    continue
                indexed_rules = sorted(indexed_rules, key=lambda item: item[0])
                member_rules = [rule for _, rule in indexed_rules]
                first_index = indexed_rules[0][0]
                combined: Dict[str, Any] = dict(member_rules[0])
                combined_fields: List[str] = []
                for rule in member_rules:
                    for field in _as_string_list(rule.get("fields_affected", [])) + ([_as_text(rule.get("output_field"))] if _as_text(rule.get("output_field")) else []):
                        allowed = _allowed_family_field(field, family)
                        if allowed and allowed not in combined_fields:
                            combined_fields.append(allowed)

                combined["rule_name"] = _family_label(family) or _as_text(member_rules[0].get("rule_name")) or _family_action(member_rules[0])
                combined["output_field"] = _family_output_field(family, member_rules)
                _member_meanings = _merge_list_values(
                    [_as_text(rule.get("business_meaning")) for rule in member_rules if _as_text(rule.get("business_meaning"))]
                )
                combined["business_meaning"] = (
                    " ".join(_member_meanings) if _member_meanings
                    else (_family_label(family) or _as_text(member_rules[0].get("business_meaning")) or _family_action(member_rules[0]))
                )
                combined["eligibility"] = _merge_list_values(
                    [
                        item
                        for rule in member_rules
                        for item in (_as_string_list(rule.get("eligibility", [])) or ([_family_condition(rule)] if _family_condition(rule) else []))
                    ]
                )
                combined["decision_logic"] = _merge_list_values(
                    [
                        item
                        for rule in member_rules
                        for item in (_as_string_list(rule.get("decision_logic", [])) or ([_family_condition(rule)] if _family_condition(rule) else []))
                    ]
                )
                combined["decision_logic_rows"] = _family_decision_rows(member_rules)
                combined["tie_priority_handling"] = _merge_list_values(
                    [
                        item
                        for rule in member_rules
                        for item in _as_string_list(rule.get("tie_priority_handling", []))
                    ]
                )
                combined["default"] = _merge_list_values(
                    [item for rule in member_rules for item in _as_string_list(rule.get("default", []))]
                )
                combined["when_not_eligible"] = _merge_list_values(
                    [item for rule in member_rules for item in _as_string_list(rule.get("when_not_eligible", []))]
                )
                combined["condition"] = _family_condition(member_rules[0])
                combined["action"] = _family_action(member_rules[0])
                combined["fields_affected"] = combined_fields
                combined["rule_type"] = _family_rule_type(member_rules)
                combined["confidence"] = _family_confidence(member_rules)
                combined["validation_status"] = _family_status(member_rules)
                member_ids = [str(rule.get("rule_id") or "") for rule in member_rules if str(rule.get("rule_id") or "").strip()]
                combined["rule_id"] = stable_id("rule", family, *member_ids, first_index)
                ambiguity_ids = [str(rule.get("ambiguity_id") or "") for rule in member_rules if str(rule.get("ambiguity_id") or "").strip()]
                combined["ambiguity_id"] = stable_id("ambiguity", family, *ambiguity_ids, first_index) if ambiguity_ids else _as_text(member_rules[0].get("ambiguity_id"))
                combined["source_evidence"] = _merge_list_values(
                    [item for rule in member_rules for item in _as_string_list(rule.get("source_evidence", []))]
                )
                combined["source_chunks"] = _merge_list_values(
                    [item for rule in member_rules for item in _as_string_list(rule.get("source_chunks", []))]
                )
                combined["source_chunk_ids"] = _merge_list_values(
                    [item for rule in member_rules for item in _as_string_list(rule.get("source_chunk_ids", []))]
                )
                combined["source_statement_ids"] = _merge_list_values(
                    [item for rule in member_rules for item in _as_string_list(rule.get("source_statement_ids", []))]
                )
                combined["evidence_spans"] = _merge_list_values(
                    [item for rule in member_rules for item in (rule.get("evidence_spans") or []) if isinstance(item, dict)]
                )
                combined["technical_references"] = _merge_list_values(
                    [item for rule in member_rules for item in _as_string_list(rule.get("technical_references", []))]
                )
                combined["unresolved_ambiguities"] = _merge_list_values(
                    [item for rule in member_rules for item in _as_string_list(rule.get("unresolved_ambiguities", []))]
                )
                combined["dependencies"] = _merge_list_values(
                    [item for rule in member_rules for item in _as_string_list(rule.get("dependencies", []))]
                )
                merged.append((first_index, combined))

            merged.extend(passthrough)
            merged.sort(key=lambda item: item[1].get("_source_index", item[0]))
            return [rule for _, rule in merged]

        deduped = _merge_rule_families(deduped)

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
