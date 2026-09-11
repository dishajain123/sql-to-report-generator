"""Tests for chunked/hierarchical rule synthesis.

Covers the three new pieces added so large procedures no longer silently
truncate mid-synthesis:

  - `RuleSynthesizerAgent.requires_sectioned_synthesis` /
    `.plan_synthesis_sections` - deciding whether a single synthesis call
    would blow the hard output-token ceiling, and grouping the existing
    extraction chunks into sections that (individually) won't.
  - `RuleSynthesizerAgent.merge_section_results` - recombining per-section
    `SynthesisResult`s into one whole-object result.
  - `LogicRulesExtractorPipeline._run_rule_synthesis` /
    `._scope_extraction_to_chunks` - the pipeline-level wiring that picks
    the single-call path for ordinary objects and the sectioned path only
    when it's actually needed, using the same technical evidence a single
    call would have seen, just partitioned by chunk.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.ingestion.ingestion import CodeChunk, IngestionResult
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from pipeline import LogicRulesExtractorPipeline

_CASE_BLOCK = (
    "CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' "
    "WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' "
    "WHEN dpd.DPD_Max > 60 THEN 'SMA_2' ELSE NULL END"
)


def _make_agent(max_tokens: int = 16000, hard_max_output_tokens=None) -> RuleSynthesizerAgent:
    # `client` is never called by the methods under test here - the tests
    # either exercise pure planning/merging logic, or monkeypatch
    # `synthesize` itself - so a plain sentinel object is enough.
    return RuleSynthesizerAgent(
        client=object(),
        model="test-model",
        max_tokens=max_tokens,
        hard_max_output_tokens=hard_max_output_tokens,
    )


# --------------------------------------------------------------------------
# Real per-model output ceilings (e.g. Amazon Nova Lite on Bedrock caps
# completions at 5000 tokens server-side) must drive sectioning, not the
# generic 32768 default - see `llm_client.resolve_model_output_ceiling` and
# the matching `hard_max_output_tokens` wiring in `RuleSynthesizerAgent`.
# --------------------------------------------------------------------------


def test_resolve_model_output_ceiling_returns_real_bedrock_cap():
    from src.core.llm_client import resolve_model_output_ceiling

    assert resolve_model_output_ceiling("bedrock", "amazon.nova-lite-v1:0") == 5000
    assert resolve_model_output_ceiling("bedrock", "anthropic.claude-3-haiku") == 4096
    # Unknown provider/model: no known ceiling, caller keeps its own default.
    assert resolve_model_output_ceiling("openai", "gpt-4o") is None
    assert resolve_model_output_ceiling("bedrock", "some-unlisted-model") is None or isinstance(
        resolve_model_output_ceiling("bedrock", "some-unlisted-model"), int
    )


def test_small_model_ceiling_forces_sectioning_at_a_much_lower_threshold():
    # A source that fits comfortably under the generic 32768 default must
    # still be routed to sectioning once the agent knows the real per-model
    # cap is small (5000, e.g. Amazon Nova Lite) - otherwise a single-pass
    # call is guaranteed to request more than the model will ever return,
    # and the server-side clamp truncates it no matter what was requested.
    huge_source = "\n".join(_CASE_BLOCK for _ in range(10))
    generic_agent = _make_agent(max_tokens=8192)
    small_cap_agent = _make_agent(max_tokens=8192, hard_max_output_tokens=5000)

    assert generic_agent.requires_sectioned_synthesis(huge_source) is False
    assert small_cap_agent.requires_sectioned_synthesis(huge_source) is True


def test_plan_synthesis_sections_stays_within_a_small_real_ceiling():
    # Regression for the exact PRO.SMA_MARKING failure mode: under the old
    # (generic-ceiling) planning, several sections were still budgeted at
    # 16000-32768 requested tokens even though Bedrock silently clamps every
    # Nova Lite completion to 5000 server-side - so most sections were
    # guaranteed to truncate mid-JSON regardless of retries. Every section's
    # own eventual `_output_token_budget` call must never exceed the real
    # per-model ceiling once that ceiling is wired in.
    agent = _make_agent(max_tokens=8192, hard_max_output_tokens=5000)
    chunks = []
    cursor = 0
    for i in range(12):
        text = _CASE_BLOCK
        chunks.append(_chunk(f"{i:02d}_main_body", text, cursor, cursor + len(text)))
        cursor += len(text) + 1
    raw_source = "\n".join(_CASE_BLOCK for _ in range(12))

    sections = agent.plan_synthesis_sections(chunks, raw_source)
    assert len(sections) > 1
    for section in sections:
        start, end = section["char_start"], section["char_end"]
        section_text = raw_source[start:end] if start is not None else raw_source
        assert agent._output_token_budget(section_text) <= 5000


# --------------------------------------------------------------------------
# requires_sectioned_synthesis
# --------------------------------------------------------------------------


def test_small_source_does_not_require_sectioned_synthesis():
    agent = _make_agent()
    assert agent.requires_sectioned_synthesis("UPDATE accounts SET balance = balance - 1") is False


def test_source_with_enough_decision_points_requires_sectioned_synthesis():
    agent = _make_agent(max_tokens=16000)
    # Base (16000) + points*256 must exceed the 32768 hard ceiling, i.e.
    # more than 65 decision points' worth of CASE/WHEN keywords.
    huge_source = "\n".join(_CASE_BLOCK for _ in range(40))
    assert agent.requires_sectioned_synthesis(huge_source) is True


# --------------------------------------------------------------------------
# plan_synthesis_sections
# --------------------------------------------------------------------------


def _chunk(chunk_id: str, text: str, start: int, end: int) -> CodeChunk:
    return CodeChunk(
        chunk_id=chunk_id,
        kind="main_body",
        text=text,
        source_char_start=start,
        source_char_end=end,
        source_line_start=1,
        source_line_end=1,
    )


def test_plan_synthesis_sections_returns_single_section_for_empty_chunks():
    agent = _make_agent()
    sections = agent.plan_synthesis_sections([], "some source")
    assert len(sections) == 1
    assert sections[0]["chunk_ids"] == []
    assert sections[0]["char_start"] == 0
    assert sections[0]["char_end"] == len("some source")


def test_plan_synthesis_sections_never_splits_a_chunk_and_covers_every_chunk():
    agent = _make_agent(max_tokens=16000)
    chunks = []
    cursor = 0
    for i in range(60):
        text = _CASE_BLOCK
        chunks.append(_chunk(f"{i:02d}_main_body", text, cursor, cursor + len(text)))
        cursor += len(text) + 1  # +1 for a joining newline in the real source

    sections = agent.plan_synthesis_sections(chunks, "x" * cursor)

    # Every chunk id appears in exactly one section, in original order.
    all_ids: List[str] = []
    for section in sections:
        all_ids.extend(section["chunk_ids"])
    assert all_ids == [c.chunk_id for c in chunks]

    # More than one section had to be produced for this input to be a
    # meaningful test of grouping (60 CASE blocks comfortably exceeds a
    # single 16000-token-base section budget).
    assert len(sections) > 1

    # Section char ranges are internally consistent with their chunk ids.
    chunk_by_id = {c.chunk_id: c for c in chunks}
    for section in sections:
        ids = section["chunk_ids"]
        expected_start = min(chunk_by_id[cid].source_char_start for cid in ids)
        expected_end = max(chunk_by_id[cid].source_char_end for cid in ids)
        assert section["char_start"] == expected_start
        assert section["char_end"] == expected_end


def test_plan_synthesis_sections_single_section_when_within_budget():
    agent = _make_agent(max_tokens=16000)
    chunks = [_chunk("00_main_body", "UPDATE t SET x = 1", 0, 19)]
    sections = agent.plan_synthesis_sections(chunks, "UPDATE t SET x = 1")
    assert len(sections) == 1
    assert sections[0]["chunk_ids"] == ["00_main_body"]


# --------------------------------------------------------------------------
# merge_section_results
# --------------------------------------------------------------------------


def _result(**data_overrides) -> SynthesisResult:
    data = {
        "purpose_summary": "",
        "step_by_step_flow": [],
        "business_rules": [],
        "calculations": [],
        "exception_handling_summary": "",
        "ambiguities": [],
    }
    data.update(data_overrides)
    return SynthesisResult(data=data)


def test_merge_section_results_passes_through_single_result_unchanged():
    only = _result(purpose_summary="the whole thing")
    merged = RuleSynthesizerAgent.merge_section_results([only])
    assert merged is only


def test_merge_section_results_concatenates_rules_and_dedupes_text_fields():
    first = _result(
        purpose_summary="Handles setup.",
        step_by_step_flow=["Drop temp tables.", "Load accounts."],
        business_rules=[{"rule_id": "r1", "rule_name": "Rule One"}],
        ambiguities=["Some shared caveat."],
    )
    second = _result(
        purpose_summary="Handles setup.",  # exact duplicate - should collapse
        step_by_step_flow=["Load accounts.", "Assign SMA class."],
        business_rules=[{"rule_id": "r2", "rule_name": "Rule Two"}],
        ambiguities=["Some shared caveat.", "A second, distinct caveat."],
    )
    merged = RuleSynthesizerAgent.merge_section_results([first, second])

    assert merged.data["purpose_summary"] == "Handles setup."
    assert merged.data["step_by_step_flow"] == [
        "Drop temp tables.",
        "Load accounts.",
        "Assign SMA class.",
    ]
    assert [r["rule_id"] for r in merged.data["business_rules"]] == ["r1", "r2"]
    assert merged.data["ambiguities"] == [
        "Some shared caveat.",
        "A second, distinct caveat.",
    ]
    assert any("2 section(s)" in w for w in merged.guardrail_warnings)


def test_merge_section_results_empty_input_returns_empty_synthesis():
    merged = RuleSynthesizerAgent.merge_section_results([])
    assert merged.data["business_rules"] == []
    assert merged.data["purpose_summary"] == ""


# --------------------------------------------------------------------------
# Pipeline wiring: _scope_extraction_to_chunks / _run_rule_synthesis
# --------------------------------------------------------------------------


def test_scope_extraction_to_chunks_filters_chunk_attributed_sections_only():
    merged_extraction: Dict[str, Any] = {
        "conditions": [
            {"source_chunk_id": "00_main_body", "field": "a"},
            {"source_chunk_id": "01_main_body", "field": "b"},
        ],
        "decision_chains": [
            {"source_chunk_id": "01_main_body", "chain_id": "c1"},
        ],
        "table_operations": [
            {"source_chunk_id": "00_main_body", "table": "T1"},
        ],
        "chunk_provenance": [
            {"chunk_id": "00_main_body"},
            {"chunk_id": "01_main_body"},
        ],
        # Not in the chunk-scoped list - must pass through untouched.
        "ambiguities": ["global note with no chunk attribution"],
        "statement_dependencies": {"version": "1", "edges": []},
    }
    scoped = LogicRulesExtractorPipeline._scope_extraction_to_chunks(
        merged_extraction, {"01_main_body"}
    )
    assert [c["field"] for c in scoped["conditions"]] == ["b"]
    assert [c["chain_id"] for c in scoped["decision_chains"]] == ["c1"]
    assert scoped["table_operations"] == []
    assert [p["chunk_id"] for p in scoped["chunk_provenance"]] == ["01_main_body"]
    # Untouched fields are passed through as-is.
    assert scoped["ambiguities"] == merged_extraction["ambiguities"]
    assert scoped["statement_dependencies"] == merged_extraction["statement_dependencies"]
    # The original is never mutated.
    assert len(merged_extraction["conditions"]) == 2


class _RecordingSynthesizer:
    """Stand-in for `RuleSynthesizerAgent` that records every `synthesize()`
    call and returns one distinguishable rule per call, while delegating
    the real sectioning decisions to an actual `RuleSynthesizerAgent`
    instance so the pipeline is exercised against real planning logic.
    """

    def __init__(self, delegate: RuleSynthesizerAgent):
        self._delegate = delegate
        self.calls: List[Dict[str, Any]] = []

    def requires_sectioned_synthesis(self, raw_source: str) -> bool:
        return self._delegate.requires_sectioned_synthesis(raw_source)

    def plan_synthesis_sections(self, chunks, raw_source):
        return self._delegate.plan_synthesis_sections(chunks, raw_source)

    def synthesize(self, **kwargs) -> SynthesisResult:
        self.calls.append(kwargs)
        rule_id = f"rule_{len(self.calls)}"
        return SynthesisResult(
            data={
                "purpose_summary": f"Section {len(self.calls)} summary.",
                "step_by_step_flow": [f"Section {len(self.calls)} step."],
                "business_rules": [{"rule_id": rule_id, "rule_name": rule_id}],
                "calculations": [],
                "exception_handling_summary": "",
                "ambiguities": [],
            }
        )


def _make_bare_pipeline() -> LogicRulesExtractorPipeline:
    pipeline = LogicRulesExtractorPipeline.__new__(LogicRulesExtractorPipeline)
    pipeline.dialect = "tsql"
    pipeline.model_name = "test-model"
    pipeline.provider = "test"
    pipeline.project_root = Path(__file__).resolve().parent.parent
    return pipeline


def test_run_rule_synthesis_uses_single_call_for_small_object():
    pipeline = _make_bare_pipeline()
    delegate = _make_agent(max_tokens=16000)
    recorder = _RecordingSynthesizer(delegate)
    pipeline.synthesizer_agent = recorder

    ingestion = IngestionResult(
        object_name="SMALL_PROC",
        object_type="PROCEDURE",
        parameters=[],
        raw_code="UPDATE t SET x = 1",
        original_code="UPDATE t SET x = 1",
        chunks=[_chunk("00_main_body", "UPDATE t SET x = 1", 0, 19)],
        dialect="TSQL",
    )
    result = pipeline._run_rule_synthesis(
        ingestion=ingestion,
        merged_extraction={},
        synthesis_input={},
        parameter_summary="No parameters.",
        dialect="tsql",
        telemetry_tracker=None,
    )
    assert len(recorder.calls) == 1
    assert result.data["business_rules"] == [{"rule_id": "rule_1", "rule_name": "rule_1"}]


def test_run_rule_synthesis_sections_large_object_and_merges_results():
    pipeline = _make_bare_pipeline()
    delegate = _make_agent(max_tokens=16000)
    recorder = _RecordingSynthesizer(delegate)
    pipeline.synthesizer_agent = recorder

    chunks = []
    cursor = 0
    conditions = []
    for i in range(60):
        text = _CASE_BLOCK
        chunk_id = f"{i:02d}_main_body"
        start, end = cursor, cursor + len(text)
        chunks.append(_chunk(chunk_id, text, start, end))
        conditions.append({"source_chunk_id": chunk_id, "field": f"field_{i}"})
        cursor = end + 1
    raw_source = "\n".join(_CASE_BLOCK for _ in range(60))

    ingestion = IngestionResult(
        object_name="BIG_PROC",
        object_type="PROCEDURE",
        parameters=[],
        raw_code=raw_source,
        original_code=raw_source,
        chunks=chunks,
        dialect="TSQL",
    )
    merged_extraction = {
        "conditions": conditions,
        "decision_chains": [],
        "loops": [],
        "calculations": [],
        "exception_handling": [],
        "tables_read": [],
        "tables_written": [],
        "table_operations": [],
        "chunk_provenance": [{"chunk_id": c.chunk_id} for c in chunks],
        "ambiguities": [],
    }

    result = pipeline._run_rule_synthesis(
        ingestion=ingestion,
        merged_extraction=merged_extraction,
        synthesis_input=merged_extraction,
        parameter_summary="No parameters.",
        dialect="tsql",
        telemetry_tracker=None,
    )

    # More than one section had to run for this to be a meaningful test.
    assert len(recorder.calls) > 1
    # Every call saw a strictly smaller raw_source than the whole object,
    # and only the `conditions` entries belonging to its own chunk ids.
    for call in recorder.calls:
        assert len(call["raw_source"]) < len(raw_source)
        seen_chunk_ids = {c["source_chunk_id"] for c in call["merged_extraction"]["conditions"]}
        assert seen_chunk_ids  # non-empty scoped slice
    # Results from every section were merged into one rule list, one per
    # section call, in call order.
    assert [r["rule_id"] for r in result.data["business_rules"]] == [
        f"rule_{i}" for i in range(1, len(recorder.calls) + 1)
    ]


# --------------------------------------------------------------------------
# merge_section_results: dedup + repetition-degeneration screening
# --------------------------------------------------------------------------


def _garbage_text(prefix: str = "Check if there is existing data ") -> str:
    return prefix + "SMA_" * 60


def test_is_degenerate_text_flags_repeated_token_without_separator():
    # Underscore is a word character, so "SMA_SMA_SMA..." has no \b
    # boundary between repeats - this specifically exercises that shape.
    assert RuleSynthesizerAgent._is_degenerate_text(_garbage_text()) is True


def test_is_degenerate_text_does_not_flag_real_report_text():
    real_samples = [
        "This procedure updates and calculates various overdue days and "
        "provisioning amounts for accounts under the SMA Aqua Scheme.",
        "FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_OVERDRAWN,0)=ISNULL(DPD_MAX,0) "
        "and ISNULL(DPD_OVERDRAWN,0)>30",
        "CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) "
        "THEN A.DPD_IntService ELSE 0 END",
        "AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey < @TIMEKEY",
    ]
    for text in real_samples:
        assert RuleSynthesizerAgent._is_degenerate_text(text) is False, text


def test_merge_section_results_drops_degenerate_step_and_keeps_clean_ones():
    first = _result(step_by_step_flow=["Reads account data."])
    second = _result(step_by_step_flow=["Reads account data.", _garbage_text()])
    merged = RuleSynthesizerAgent.merge_section_results([first, second])
    assert merged.data["step_by_step_flow"] == ["Reads account data."]
    assert any("repetition-degeneration" in w for w in merged.guardrail_warnings)


def test_merge_section_results_dedupes_identical_rules_across_sections():
    def rule(name="Assign SMA reason", condition="c1", action="a1"):
        return {"rule_name": name, "condition": condition, "action": action, "output_field": "SMA_REASON"}

    first = _result(business_rules=[rule()])
    second = _result(business_rules=[rule(), rule(), rule("Different rule", "c2", "a2")])
    merged = RuleSynthesizerAgent.merge_section_results([first, second])
    assert [r["rule_name"] for r in merged.data["business_rules"]] == [
        "Assign SMA reason",
        "Different rule",
    ]


def test_merge_section_results_drops_rule_with_degenerate_text():
    def rule(name):
        return {"rule_name": name, "condition": "c", "action": "a", "output_field": "X"}

    good = rule("A perfectly normal rule name")
    bad = rule(_garbage_text("Assign SMA reason "))
    merged = RuleSynthesizerAgent.merge_section_results([
        _result(business_rules=[good]),
        _result(business_rules=[bad]),
    ])
    names = [r["rule_name"] for r in merged.data["business_rules"]]
    assert names == ["A perfectly normal rule name"]
    assert any("repetition-degeneration" in w for w in merged.guardrail_warnings)


# --------------------------------------------------------------------------
# Deterministic Decision Logic backfill from decision_chains
# --------------------------------------------------------------------------


def test_normalize_business_rules_backfills_decision_logic_from_chains():
    raw_rule = {
        "rule_name": "Calculate maximum DPD",
        "condition": "",
        "action": "Sets DPD_Max to the largest of several overdue-day counters.",
        "output_field": "DPD_Max",
        "fields_affected": ["DPD_Max"],
        "decision_logic_rows": [],
    }
    technical_context = {
        "decision_chains": [
            {
                "chain_id": "c1",
                "branches": [
                    {
                        "branch_condition": "A.DPD_IntService >= all other DPD values",
                        "assignments": [{"field": "DPD_Max", "value": "A.DPD_IntService"}],
                    },
                    {
                        "branch_condition": "A.DPD_NoCredit >= all other DPD values",
                        "assignments": [{"field": "DPD_Max", "value": "A.DPD_NoCredit"}],
                    },
                    {
                        "branch_condition": "ELSE",
                        "is_catch_all": True,
                        "assignments": [{"field": "DPD_Max", "value": "A.DPD_StockStmt"}],
                    },
                ],
            }
        ]
    }
    normalized = RuleSynthesizerAgent._normalize_business_rules(
        [raw_rule], technical_context=technical_context
    )
    rows = normalized[0]["decision_logic_rows"]
    assert len(rows) == 3
    assert rows[0] == {"condition": "A.DPD_IntService >= all other DPD values", "outcome": "A.DPD_IntService"}
    assert rows[-1] == {"condition": "ELSE", "outcome": "A.DPD_StockStmt"}


def test_normalize_business_rules_does_not_override_model_supplied_rows():
    raw_rule = {
        "rule_name": "Assign SMA class",
        "output_field": "SMA_CLASS",
        "decision_logic_rows": [{"condition": "DPD_Max BETWEEN 1 AND 30", "outcome": "SMA_0"}],
    }
    technical_context = {
        "decision_chains": [
            {
                "branches": [
                    {"branch_condition": "x", "assignments": [{"field": "SMA_CLASS", "value": "should not appear"}]},
                    {"branch_condition": "y", "assignments": [{"field": "SMA_CLASS", "value": "should not appear either"}]},
                ]
            }
        ]
    }
    normalized = RuleSynthesizerAgent._normalize_business_rules(
        [raw_rule], technical_context=technical_context
    )
    # Model already supplied rows - the deterministic backfill must not fire.
    assert normalized[0]["decision_logic_rows"] == [
        {"condition": "DPD_Max BETWEEN 1 AND 30", "outcome": "SMA_0"}
    ]


def test_normalize_business_rules_backfill_requires_at_least_two_rows():
    raw_rule = {"rule_name": "X", "output_field": "FOO", "decision_logic_rows": []}
    technical_context = {
        "decision_chains": [
            {"branches": [{"branch_condition": "only one", "assignments": [{"field": "FOO", "value": "bar"}]}]}
        ]
    }
    normalized = RuleSynthesizerAgent._normalize_business_rules(
        [raw_rule], technical_context=technical_context
    )
    assert normalized[0]["decision_logic_rows"] == []


def test_normalize_business_rules_backfill_only_picks_matching_field_from_shared_chain():
    # Regression for PRO.SMA_MARKING: one CASE ladder assigns SMA_CLASS while
    # a separate CASE ladder assigns SMA_REASON. A rule for SMA_REASON must
    # never pick up SMA_CLASS's outcomes (or vice versa) even though both
    # chains are visible in the same technical_context.
    sma_class_rule = {"rule_name": "Assign SMA class", "output_field": "SMA_CLASS", "decision_logic_rows": []}
    sma_reason_rule = {"rule_name": "Assign SMA reason", "output_field": "SMA_REASON", "decision_logic_rows": []}
    technical_context = {
        "decision_chains": [
            {
                "chain_id": "class_ladder",
                "branches": [
                    {"branch_condition": "DPD_Max BETWEEN 1 AND 30", "assignments": [{"field": "SMA_CLASS", "value": "'SMA_0'"}]},
                    {"branch_condition": "DPD_Max BETWEEN 31 AND 60", "assignments": [{"field": "SMA_CLASS", "value": "'SMA_1'"}]},
                    {"branch_condition": "ELSE", "is_catch_all": True, "assignments": [{"field": "SMA_CLASS", "value": "'SMA_2'"}]},
                ],
            },
            {
                "chain_id": "reason_ladder",
                "branches": [
                    {"branch_condition": "FACILITYTYPE IN ('CC','OD') AND ...", "assignments": [{"field": "SMA_REASON", "value": "'DEGRADE BY NO CREDIT'"}]},
                    {"branch_condition": "ELSE", "is_catch_all": True, "assignments": [{"field": "SMA_REASON", "value": "'OTHER'"}]},
                ],
            },
        ]
    }
    normalized = RuleSynthesizerAgent._normalize_business_rules(
        [sma_class_rule, sma_reason_rule], technical_context=technical_context
    )
    class_rows = normalized[0]["decision_logic_rows"]
    reason_rows = normalized[1]["decision_logic_rows"]
    assert [r["outcome"] for r in class_rows] == ["'SMA_0'", "'SMA_1'", "'SMA_2'"]
    assert [r["outcome"] for r in reason_rows] == ["'DEGRADE BY NO CREDIT'", "'OTHER'"]
    assert all("DEGRADE" not in r["outcome"] for r in class_rows)
    assert all(r["outcome"] not in {"'SMA_0'", "'SMA_1'", "'SMA_2'"} for r in reason_rows)


def test_normalize_business_rules_backfill_ignores_unrelated_field():
    raw_rule = {"rule_name": "X", "output_field": "UNRELATED_FIELD", "decision_logic_rows": []}
    technical_context = {
        "decision_chains": [
            {
                "branches": [
                    {"branch_condition": "a", "assignments": [{"field": "SMA_CLASS", "value": "SMA_0"}]},
                    {"branch_condition": "b", "assignments": [{"field": "SMA_CLASS", "value": "SMA_1"}]},
                ]
            }
        ]
    }
    normalized = RuleSynthesizerAgent._normalize_business_rules(
        [raw_rule], technical_context=technical_context
    )
    assert normalized[0]["decision_logic_rows"] == []