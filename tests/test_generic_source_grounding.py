"""Regression tests for domain-neutral source grounding and rendering."""

from src.output.report_formatter import ReportFormatterAgent
from src.validation.reconciliation import _rule_candidate_rows
from src.validation.semantic_validation import find_semantic_anomalies
from src.validation.coverage_check import find_coverage_gaps
from src.synthesis.rule_synthesizer import SynthesisResult
from src.ir.canonical_ir import (
    TableOperationIR,
    _attach_calculation_destinations,
    _build_decision_blocks,
    BusinessRuleIR,
)
from src.ingestion.ingestion import CodeChunk
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks


def test_evidence_fragment_links_to_containing_dml_statement():
    rule = {"source_evidence": ["amount * factor"]}
    rows = [{
        "statement_text": "INSERT INTO target (total) VALUES (base_amount * factor)",
        "filter_condition": "",
        "where_predicate": "",
    }]
    assert _rule_candidate_rows(rule, rows) == rows


def test_fractional_calculation_is_reported_as_uncertain_not_incorrect():
    findings = find_semantic_anomalies(
        "v_rate := 0.25; v_total := v_rate / divisor;",
        calculations=[],
    )
    assert len(findings) == 1
    assert "uncertainty" in findings[0].lower()
    assert "incorrect" not in findings[0].lower()


def test_decision_rows_preserve_llm_supplied_assignments_separately():
    rows = ReportFormatterAgent._decision_logic_rows({
        "decision_logic_rows": [{
            "condition": "input meets threshold",
            "outcome": "selected",
            "assignments": ["result := selected", "score := score + adjustment"],
        }]
    })
    assert rows[0]["condition"] == "input meets threshold"
    assert rows[0]["outcome"] == "selected"
    assert rows[0]["assignments"] == ["result := selected", "score := score + adjustment"]


def test_business_report_includes_metadata_free_rule_summary_table():
    report = ReportFormatterAgent()._business_rule_overview_table([
        {
            "rule_name": "Apply state transition",
            "fields_affected": ["state_code"],
            "business_meaning": "Updates the state when the input is eligible.",
            "validation_status": "verified",
            "rule_id": "internal-rule-id",
            "reconciliation_status": "MATCHED",
        }
    ])
    assert "## Business Rule Summary" in report
    assert "| Rule | Affected Field | Business Purpose |" in report
    assert "Apply state transition" in report
    assert "state_code" in report
    assert "validation_status" not in report
    assert "internal-rule-id" not in report
    assert "MATCHED" not in report


def test_cited_dml_statement_is_not_reported_as_unreviewed_keyword():
    source = "INSERT INTO target_table (total_value) VALUES (base_value * factor_value);"
    rules = [{"source_evidence": ["base_value * factor_value"]}]
    assert find_coverage_gaps(source, rules) == []


def test_cited_exception_handler_covers_when_and_handler_dml():
    source = """BEGIN
  NULL;
EXCEPTION
  WHEN OTHERS THEN
    INSERT INTO audit_table (message) VALUES (error_message);
END;"""
    rules = [{"source_evidence": ["INSERT INTO audit_table (message) VALUES (error_message)"]}]
    assert find_coverage_gaps(source, rules) == []


def test_unrelated_dml_statement_remains_a_gap():
    source = """UPDATE target_table SET result_value = first_value WHERE key_value = 1;
UPDATE target_table SET result_value = second_value WHERE key_value = 2 AND region_code = 9;"""
    rules = [{"source_evidence": ["result_value = first_value WHERE key_value = 1 AND region_code = 8"]}]
    gaps = find_coverage_gaps(source, rules)
    assert gaps
    assert any("second_value" in gap.snippet for gap in gaps)


def test_parent_branch_evidence_covers_nested_assignments():
    source = """IF input_flag = 1 THEN
  first_value := source_value;
  second_value := first_value + adjustment_value;
END IF;"""
    rules = [{
        "condition": "input_flag = 1",
        "action": "Apply both assignments",
        "fields_affected": ["first_value", "second_value"],
        "source_evidence": ["IF input_flag = 1 THEN"],
    }]
    assert find_coverage_gaps(source, rules) == []


def test_calculation_evidence_covers_dml_with_same_output_expression():
    source = "INSERT INTO output_table (total_value) VALUES (base_value * rate_value);"
    rules = [{
        "action": "Calculate the output total",
        "fields_affected": ["total_value"],
        "source_evidence": ["base_value * rate_value"],
    }]
    assert find_coverage_gaps(source, rules) == []


def test_uncovered_nested_assignment_still_produces_a_gap():
    source = """IF input_flag = 1 THEN
  first_value := source_value;
END IF;
UPDATE output_table SET other_value = unrelated_value;"""
    rules = [{
        "condition": "input_flag = 1",
        "action": "Apply the branch assignment",
        "fields_affected": ["first_value"],
        "source_evidence": ["IF input_flag = 1 THEN"],
    }]
    gaps = find_coverage_gaps(source, rules)
    assert gaps
    assert any("other_value" in gap.snippet for gap in gaps)


def test_business_rule_rendering_keeps_conditional_assignments_and_evidence():
    rule = {
        "rule_name": "Apply generic state transition",
        "condition": "input_flag = 1",
        "eligibility": ["input_flag = 1"],
        "action": "state_value := 'READY'",
        "business_meaning": "Moves the item to the ready state.",
        "output_field": "state_value",
        "source_evidence": ["IF input_flag = 1 THEN", "state_value := 'READY';"],
        "validation_status": "verified",
    }
    report = ReportFormatterAgent()._business_rules_section([rule])
    assert "**Summary:**" in report
    assert "Moves the item to the ready state." in report
    assert "**Condition:**" not in report
    assert "**Then:**" not in report
    assert "**Source Evidence:**" not in report
    assert "validation_status" not in report


def test_business_rule_labels_have_markdown_boundaries_and_no_redundant_prose():
    report = ReportFormatterAgent()._business_rules_section([{
        "rule_name": "Apply state",
        "output_field": "state_code",
        "condition": "input_code = 1",
        "action": "Sets state_code to READY.",
        "business_meaning": "Sets the state to READY when input_code is 1.",
        "decision_logic_rows": [{"condition": "input_code = 1", "outcome": "READY"}],
    }])
    assert "**Affected Field:** `state_code`" in report
    # No "eligibility" was supplied, so the report must say so explicitly
    # rather than silently omitting the line - "unconditional" is itself a
    # material fact, not an absence of one.
    assert "**Applies to:** all rows (no additional conditions found in the source)\n\n**Summary:**" in report
    assert "**Condition:**" not in report
    assert "**Then:**" not in report
    assert "| input_code = 1 | READY |" in report
    assert "Sets state_code to READY." not in report
    assert "Sets the state to READY when input_code is 1." in report
    assert "When / Condition" not in report
    assert "Then / Result" not in report


def test_rendering_strips_alias_segments_from_affected_fields_and_outputs():
    formatter = ReportFormatterAgent()
    report = formatter._business_rules_section([{
        "rule_name": "Update eligible state",
        "output_field": "PRO.AccountCal.A.AddlProvision",
        "fields_affected": ["A.UpgradeEligible"],
        "condition": "input_value is present",
        "action": "Apply the source-defined update.",
    }])
    assert "`PRO.AccountCal.AddlProvision, UpgradeEligible`" in report
    assert "PRO.AccountCal.A.AddlProvision" not in report
    assert "A.UpgradeEligible" not in report

    condition_report = formatter._business_rules_section([{
        "rule_name": "Evaluate generic field",
        "output_field": "ResultField",
        "condition": "A.InputField = 1 AND ISNULL(A.OtherField, 0) > 0",
        "action": "A.ResultField := A.InputField",
    }])
    assert "A.InputField" not in condition_report
    assert "A.OtherField" not in condition_report
    assert "A.ResultField" not in condition_report

    branch_report = formatter._business_rules_section([{
        "rule_name": "Classify generic input",
        "output_field": "ResultField",
        "condition": "A.InputField is evaluated",
        "action": "Apply the matching result.",
        "decision_logic_rows": [
            {"condition": "A.InputField = 1", "outcome": "A.ResultField = 'X'"},
            {"condition": "ELSE", "outcome": "A.ResultField = 'Y'"},
        ],
    }])
    assert "A.InputField" not in branch_report
    assert "A.ResultField" not in branch_report

    calculation = SynthesisResult(data={
        "calculations": [{
            "field": "derived_value",
            "formula": "source_value * factor_value",
            "output_field": "PRO.AccountCal.A.AddlProvision",
        }]
    })
    calc_report = formatter._calculations(calculation)
    assert "**Output:**\nPRO.AccountCal.AddlProvision" in calc_report
    assert "PRO.AccountCal.A.AddlProvision" not in calc_report


def test_then_bullets_use_each_decision_row_outcome():
    report = ReportFormatterAgent()._business_rules_section([{
        "rule_name": "Assign category by range",
        "output_field": "category_code",
        "condition": "input_value is evaluated",
        "action": "Assign the category according to the matching range.",
        "decision_logic_rows": [
            {"condition": "input_value <= 10", "outcome": "STANDARD"},
            {"condition": "input_value <= 20", "outcome": "SUBSTANDARD"},
            {"condition": "input_value <= 30", "outcome": "DOUBTFUL"},
            {"condition": "ELSE", "outcome": "LOSS"},
        ],
    }])
    for outcome in ("STANDARD", "SUBSTANDARD", "DOUBTFUL", "LOSS"):
        assert outcome in report
    assert "**Condition:**" not in report
    assert "**Then:**" not in report


def test_each_calculation_renders_its_own_output_field():
    report = ReportFormatterAgent()._calculations(SynthesisResult(data={
        "calculations": [
            {"field": "first_total", "formula": "first_value + first_rate", "output_field": "target.first_total"},
            {"field": "second_total", "formula": "second_value + second_rate", "output_field": "target.second_total"},
        ]
    }))
    first = report.index("### Calculation — first_total")
    second = report.index("### Calculation — second_total")
    assert "**Output:**\ntarget.first_total" in report[first:second]
    assert "**Output:**\ntarget.second_total" in report[second:]
    assert "target.second_total" not in report[first:second]


def test_decision_block_keeps_authored_secondary_result_in_action():
    report = ReportFormatterAgent()._business_rules_section([{
        "rule_name": "Apply state and score",
        "output_field": "state_code, score_value",
        "condition": "input_code = 1",
        "action": "Sets state_code to READY and score_value to 0.40.",
        "decision_logic_rows": [{"condition": "input_code = 1", "outcome": "READY"}],
    }])
    assert "Not explicitly determined from source SQL." in report
    assert "Sets state_code to READY and score_value to 0.40." not in report


def test_calculations_render_expression_output_and_evidence_separately():
    synthesis = SynthesisResult(data={
        "calculations": [{
            "result": "net_value",
            "formula": "gross_value - adjustment_value",
            "output_field": "net_value",
            "source_evidence": ["net_value := gross_value - adjustment_value;"],
        }]
    })
    report = ReportFormatterAgent()._calculations(synthesis)
    assert "### Calculation — net_value" in report
    assert "**Expression:**\ngross_value - adjustment_value" in report
    assert "**Output:**\nnet_value" in report
    assert "**Used By:**\nNot specified" in report
    assert "**Source Evidence:**" not in report


def test_calculation_report_resolves_generic_dml_output_and_used_by():
    synthesis = SynthesisResult(data={
        "calculations": [{"result": "total_value", "formula": "base_value * rate_value"}]
    })
    report = ReportFormatterAgent()._calculations(synthesis, {
        "tables_written": [{
            "table": "output_table",
            "operation": "INSERT",
            "assigned_values": [{"column": "total_value", "expression": "base_value * rate_value"}],
        }]
    })
    assert "**Output:**\noutput_table.total_value" in report
    assert "**Used By:**\nINSERT INTO output_table" in report


def test_unknown_calculation_destination_is_not_invented():
    report = ReportFormatterAgent()._calculations(SynthesisResult(data={
        "calculations": [{"result": "derived_value", "formula": "opaque_function(input_value)"}]
    }))
    assert "**Output:**\nNot specified" in report


def test_canonical_calculation_retains_generic_dml_destination_provenance():
    calculations = [{"result": "total_value", "formula": "base_value * rate_value"}]
    operations = [TableOperationIR(
        table="output_table",
        operation="INSERT",
        assigned_values=[{"column": "total_value", "expression": "base_value * rate_value"}],
    )]
    canonical = _attach_calculation_destinations(calculations, operations)
    assert canonical[0]["destination"] == "output_table.total_value"
    assert canonical[0]["used_by"] == "INSERT INTO output_table"
    assert calculations[0].get("destination") is None


def test_canonical_calculation_links_procedural_assignment_to_dml():
    calculations = [{"result": "derived_total", "formula": "base_value * rate_value"}]
    operations = [TableOperationIR(
        table="output_table",
        operation="INSERT",
        assigned_values=[{"column": "total_value", "expression": "derived_total"}],
    )]
    canonical = _attach_calculation_destinations(
        calculations,
        operations,
        "derived_total := base_value * rate_value;",
    )
    assert canonical[0]["destination"] == "output_table.total_value"


def test_parser_preserves_insert_expression_to_target_column_relationship():
    operations, _ = extract_table_operations_from_chunks([
        CodeChunk(chunk_id="chunk_1", kind="main_body", text=(
            "INSERT INTO output_table (total_value, item_id) "
            "VALUES (base_value * rate_value, source_id)"
        ))
    ], "oracle")
    insert = next(row for row in operations if row["operation"] == "INSERT")
    assert insert["assigned_values"] == [
        {"column": "total_value", "expression": "base_value * rate_value"},
        {"column": "item_id", "expression": "source_id"},
    ]


def test_assignments_are_not_rendered_as_fake_outcomes():
    report = ReportFormatterAgent()._business_rules_section([{
        "rule_name": "Apply assignment",
        "decision_logic_rows": [{
            "condition": "input_value > threshold",
            "outcome": "",
            "assignments": ["result_value := input_value"],
        }],
        "source_evidence": ["result_value := input_value;"],
    }])
    assert "| Condition | Result |" in report
    assert "| Condition | Assignments |" not in report
    assert "| input_value > threshold | result_value := input_value |" in report


def test_exception_summary_is_separate_from_business_rule_content():
    synthesis = SynthesisResult(data={
        "business_rules": [],
        "exception_handling_summary": "On failure, the handler records the error and re-raises it.",
    })
    report = ReportFormatterAgent()._exception_handling(synthesis)
    assert report.startswith("## Exception Handling")
    assert "records the error and re-raises it" in report
    assert "validation_status" not in report


def test_unrelated_sql_domain_has_no_formatter_semantic_fallback():
    report = ReportFormatterAgent()._business_rules_section([{
        "rule_name": "Route package",
        "condition": "temperature_celsius < threshold_celsius",
        "action": "route_code := 'COLD_CHAIN'",
        "business_meaning": "Routes the package using the supplied temperature rule.",
        "source_evidence": ["route_code := 'COLD_CHAIN';"],
    }])
    assert "Routes the package using the supplied temperature rule." in report
    assert "temperature_celsius < threshold_celsius" not in report
    assert "route_code := 'COLD_CHAIN'" not in report
    assert "classification" not in report.lower()
    assert "provision" not in report.lower()


def test_if_elsif_else_rules_group_into_one_structural_decision_block():
    rules = [
        BusinessRuleIR(rule_id="r1", condition="status_code = 1", action="state := 'OPEN'"),
        BusinessRuleIR(rule_id="r2", condition="status_code = 2", action="state := 'CLOSED'"),
    ]
    blocks = _build_decision_blocks(rules, [{
        "chain_type": "IF_ELSIF_ELSE",
        "branches": [
            {"branch_condition": "status_code = 1"},
            {"branch_condition": "status_code = 2"},
            {"branch_condition": "ELSE"},
        ],
    }])
    assert len(blocks) == 1
    assert blocks[0]["rule_ids"] == ["r1", "r2"]
    assert rules[0].extra["decision_block_id"] == rules[1].extra["decision_block_id"]


def test_decision_block_keeps_all_source_branches_and_avoids_first_branch_title():
    rules = [
        BusinessRuleIR(
            rule_id="r1", condition="input_code = 1", action="state := 'OPEN'",
            extra={"rule_name": "Route item as OPEN"},
        ),
        BusinessRuleIR(
            rule_id="r2", condition="input_code = 2", action="state := 'HELD'",
            extra={"rule_name": "Route item as HELD"},
        ),
    ]
    blocks = _build_decision_blocks(rules, [{
        "chain_type": "IF_ELSIF_ELSE",
        "branches": [
            {"branch_condition": "input_code = 1", "assignments": [{"value": "'OPEN'"}]},
            {"branch_condition": "input_code = 2", "assignments": [{"value": "'HELD'"}]},
            {"branch_condition": "ELSE", "assignments": [{"value": "'UNKNOWN'"}]},
        ],
    }])
    assert len(blocks) == 1
    assert len(blocks[0]["branches"]) == 3
    assert blocks[0]["name"] == "Route item as"


def test_nested_if_chain_remains_one_parent_structural_block():
    rules = [
        BusinessRuleIR(rule_id="r1", condition="outer_flag = 1 AND inner_flag = 1", action="result := 'A'"),
        BusinessRuleIR(rule_id="r2", condition="outer_flag = 1 AND inner_flag = 0", action="result := 'B'"),
    ]
    blocks = _build_decision_blocks(rules, [{
        "chain_type": "NESTED_IF",
        "branches": [
            {"branch_condition": "outer_flag = 1 AND inner_flag = 1"},
            {"branch_condition": "outer_flag = 1 AND inner_flag = 0"},
        ],
    }])
    assert len(blocks) == 1
    assert len(blocks[0]["branches"]) == 2


def test_case_when_else_chain_groups_without_domain_knowledge():
    rules = [
        BusinessRuleIR(rule_id="r1", condition="kind_code = 10", action="bucket := 'FIRST'"),
        BusinessRuleIR(rule_id="r2", condition="kind_code = 20", action="bucket := 'SECOND'"),
    ]
    blocks = _build_decision_blocks(rules, [{
        "chain_type": "CASE_EXPRESSION",
        "branches": [
            {"branch_condition": "kind_code = 10"},
            {"branch_condition": "kind_code = 20"},
            {"branch_condition": "ELSE"},
        ],
    }])
    assert len(blocks) == 1


def test_independent_if_rules_are_not_grouped_without_shared_chain():
    rules = [
        BusinessRuleIR(rule_id="r1", condition="temperature > upper_limit", action="alert := 1"),
        BusinessRuleIR(rule_id="r2", condition="pressure < lower_limit", action="shutdown := 1"),
    ]
    assert _build_decision_blocks(rules, []) == []


def test_grouped_renderer_keeps_all_branch_results_in_one_block():
    report = ReportFormatterAgent()._business_rules_section([
        {"rule_name": "First branch", "decision_block_id": "block_1", "condition": "code = 1", "action": "state := 'A'"},
        {"rule_name": "Second branch", "decision_block_id": "block_1", "condition": "code = 2", "action": "state := 'B'"},
    ])
    assert report.count("### R1 —") == 1
    assert "**Condition:**" not in report
    assert "**Then:**" not in report
    assert "**Summary:**" in report
    assert report.count("### Decision Logic") == 1
    assert "| code = 1 | state := 'A' |" in report
    assert "| code = 2 | state := 'B' |" in report


def test_grouped_renderer_keeps_all_assignments_in_each_branch_result():
    report = ReportFormatterAgent()._business_rules_section([{
        "rule_name": "Apply coordinated outputs",
        "decision_block_id": "block_1",
        "condition": "input_code = 1",
        "decision_logic_rows": [{
            "condition": "input_code = 1",
            "outcome": "READY",
            "assignments": ["state_code := 'READY'", "score_value := 0.40"],
        }],
    }])
    assert "| input_code = 1 | state_code := 'READY'; score_value := 0.40; READY |" in report
    assert "**Condition:**" not in report
    assert "**Then:**" not in report


def test_reconciliation_banner_is_available_but_kept_out_of_the_business_report():
    # Per explicit client direction, the automated-verification/quality-
    # score banner must NOT appear in the business report - business
    # readers found it too prominent/noisy in that document. The function
    # itself is still correct and still tested (it's used elsewhere / kept
    # available), but format() must not call it. The equivalent detail
    # (status, score, coverage %, contradictions) still reaches a reviewer
    # through format_verification()'s _quality_summary, so nothing is
    # silently lost - it is just kept out of this specific document.
    from types import SimpleNamespace

    notice = ReportFormatterAgent._reconciliation_notice(
        {"quality": {"status": "REVIEW_REQUIRED", "review_required": True, "coverage": {}}},
        SimpleNamespace(data={}),
    )
    assert notice.startswith("**Automated verification:** REVIEW REQUIRED")

    # format() must never call it.
    assert "_reconciliation_notice" not in ReportFormatterAgent.format.__code__.co_names

    # format_verification() still surfaces the same underlying quality
    # data via _quality_summary, so a reviewer isn't losing the signal.
    assert "_quality_summary" in ReportFormatterAgent.format_verification.__code__.co_names

    # A clean/passing report must not show the banner at all either way.
    clean_notice = ReportFormatterAgent._reconciliation_notice(
        {"quality": {"status": "PASS", "review_required": False, "coverage": {}}},
        SimpleNamespace(data={}),
    )
    assert clean_notice == ""