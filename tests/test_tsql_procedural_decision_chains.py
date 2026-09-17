"""Regression tests for `extract_tsql_if_elseif_chains` (T-SQL procedural
IF / ELSE IF / ELSE decision-chain extraction) and its downstream effect
on reconciliation.

Root cause this addresses (see `docs/SMA_report_root_causes.md` and the
module comment above `extract_tsql_if_elseif_chains` in
`src/validation/semantic_validation.py`): `extract_procedural_decision_
chains` and `extract_nested_decision_chains` only recognize Oracle
PL/SQL's `IF ... THEN` / `ELSIF ... THEN` / `END IF` keywords and never
match T-SQL's `IF` / `ELSE IF` / `ELSE` / bare `END` syntax at all - so a
T-SQL procedure's sequential IF/ELSE IF/ELSE ladders had ZERO
deterministic decision-chain coverage, meaning reconciliation had no
counter-evidence to check a synthesized rule's condition/outcome
against for that shape of logic, and `ensure_decision_chain_coverage`
had nothing to backfill a table from.

These tests use a generic "employee bonus tier" domain, deliberately
NOT the DPD/loan-servicing domain any bundled sample uses, so the fix
cannot be accidentally specific to one procedure's shape.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.ingestion import CodeChunk, IngestionResult
from src.output.report_formatter import ReportFormatterAgent
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks, split_table_operations
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from src.validation.reconciliation import reconcile_deterministic_evidence
from src.validation.semantic_validation import extract_tsql_if_elseif_chains
from pipeline import _extract_deterministic_decision_chains


# --------------------------------------------------------------------------
# 1. Simple IF / ELSE
# --------------------------------------------------------------------------


def test_simple_if_else_is_captured_as_a_two_branch_chain():
    sql = """
    IF @Score >= 90
    BEGIN
        UPDATE dbo.Employee SET Tier = 'GOLD' WHERE EmployeeId = @EmployeeId
    END
    ELSE
    BEGIN
        UPDATE dbo.Employee SET Tier = 'SILVER' WHERE EmployeeId = @EmployeeId
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    chain = chains[0]
    assert [b["branch_condition"] for b in chain["branches"]] == ["@Score >= 90", "ELSE"]
    assert chain["branches"][0]["assignments"] == [{"field": "Tier", "value": "'GOLD'"}]
    assert chain["branches"][1]["assignments"] == [{"field": "Tier", "value": "'SILVER'"}]


def test_a_bare_if_with_no_else_produces_no_chain():
    """A single unconditional branch has nothing to reconcile against -
    must not be emitted as a spurious "decision" with only one outcome."""
    sql = """
    IF @Score >= 90
    BEGIN
        UPDATE dbo.Employee SET Tier = 'GOLD' WHERE EmployeeId = @EmployeeId
    END
    """
    assert extract_tsql_if_elseif_chains(sql) == []


# --------------------------------------------------------------------------
# 2. Sequential IF / ELSE IF / ELSE - exclusivity/order preserved
# --------------------------------------------------------------------------


def test_sequential_if_elseif_else_preserves_branch_order_and_exclusivity():
    sql = """
    IF @Score >= 90
    BEGIN
        UPDATE dbo.Employee SET Tier = 'GOLD' WHERE EmployeeId = @EmployeeId
    END
    ELSE IF @Score >= 70
    BEGIN
        UPDATE dbo.Employee SET Tier = 'SILVER' WHERE EmployeeId = @EmployeeId
    END
    ELSE
    BEGIN
        UPDATE dbo.Employee SET Tier = 'BRONZE' WHERE EmployeeId = @EmployeeId
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    branches = chains[0]["branches"]
    conditions = [b["branch_condition"] for b in branches]
    assert conditions == ["@Score >= 90", "@Score >= 70", "ELSE"]
    outcomes = [b["assignments"][0]["value"] for b in branches]
    assert outcomes == ["'GOLD'", "'SILVER'", "'BRONZE'"]
    # The ELSE branch's effective condition records that it only applies
    # when EVERY earlier condition in the ladder was false - the sequential
    # exclusivity - not as an independent, unconditional third rule.
    assert "@Score >= 90" in branches[-1]["effective_condition"]
    assert "@Score >= 70" in branches[-1]["effective_condition"]


# --------------------------------------------------------------------------
# 3. Nested IF inside a branch: must not misattribute the nested
#    assignment to the outer branch
# --------------------------------------------------------------------------


def test_nested_if_inside_a_branch_is_not_misattributed_to_the_outer_branch():
    """A SET inside a nested IF only applies when BOTH the outer and the
    inner condition hold. Flattening it onto the outer branch alone would
    assert a condition that is not actually sufficient on its own - the
    exact class of hallucination this extractor must not introduce."""
    sql = """
    IF @Department = 'SALES'
    BEGIN
        IF @Region = 'EAST'
        BEGIN
            SET @BonusRate = 0.10
        END
        ELSE
        BEGIN
            SET @BonusRate = 0.08
        END
    END
    ELSE
    BEGIN
        SET @BonusRate = 0.05
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    for chain in chains:
        sales_branch = next(
            (b for b in chain["branches"] if b["branch_condition"] == "@Department = 'SALES'"), None
        )
        if sales_branch is not None:
            assert sales_branch["assignments"] == []


def test_nested_if_is_recovered_as_its_own_independently_scoped_chain():
    """The nested `@Region = 'EAST'` ladder inside the SALES branch above
    is not lost - it is recovered as its own chain, with its own genuine
    conditions (which say nothing about `@Department`, correctly, since
    asserting that would require re-attaching the outer condition this
    recursive extraction has no way to know), and with source positions
    corrected back to real, absolute line numbers in the original text
    (not relative to the branch snippet the recursive call actually saw -
    a provenance bug that would otherwise point a reader at the wrong
    part of the file).
    """
    sql = (
        "IF @Department = 'SALES'\n"
        "BEGIN\n"
        "    IF @Region = 'EAST'\n"
        "    BEGIN\n"
        "        SET @BonusRate = 0.10\n"
        "    END\n"
        "    ELSE\n"
        "    BEGIN\n"
        "        SET @BonusRate = 0.08\n"
        "    END\n"
        "END\n"
        "ELSE\n"
        "BEGIN\n"
        "    SET @BonusRate = 0.05\n"
        "END\n"
    )
    chains = extract_tsql_if_elseif_chains(sql)
    nested = next(
        (c for c in chains if any(b["branch_condition"] == "@Region = 'EAST'" for b in c["branches"])),
        None,
    )
    assert nested is not None, f"expected a recovered nested chain, got: {chains}"
    conditions = [b["branch_condition"] for b in nested["branches"]]
    assert conditions == ["@Region = 'EAST'", "ELSE"]
    outcomes = [b["assignments"][0]["value"] for b in nested["branches"]]
    assert outcomes == ["0.10", "0.08"]
    # Line 3 (1-indexed) is the real `IF @Region = 'EAST'` line in the
    # snippet above - the recursive call's own local numbering would have
    # reported this as line 1 (relative to just the SALES branch's body)
    # without the offset correction.
    assert nested["source_line_start"] == 3


# --------------------------------------------------------------------------
# 4. UPDATE with multiple assigned columns in one branch
# --------------------------------------------------------------------------


def test_update_with_multiple_columns_captures_every_assignment():
    sql = """
    IF @YearsOfService >= 5
    BEGIN
        UPDATE dbo.Employee SET Tier = 'SENIOR', VacationDays = 25 WHERE EmployeeId = @EmployeeId
    END
    ELSE
    BEGIN
        UPDATE dbo.Employee SET Tier = 'JUNIOR', VacationDays = 15 WHERE EmployeeId = @EmployeeId
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    first_branch = chains[0]["branches"][0]
    assert {"field": "Tier", "value": "'SENIOR'"} in first_branch["assignments"]
    assert {"field": "VacationDays", "value": "25"} in first_branch["assignments"]


# --------------------------------------------------------------------------
# 5. Variable assignment (`SET @var = ...`) as the branch action
# --------------------------------------------------------------------------


def test_variable_assignment_branches_are_captured():
    sql = """
    IF @PerformanceRating = 'EXCEEDS'
    BEGIN
        SET @BonusMultiplier = 1.5
    END
    ELSE
    BEGIN
        SET @BonusMultiplier = 1.0
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    assert chains[0]["branches"][0]["assignments"] == [{"field": "@BonusMultiplier", "value": "1.5"}]


# --------------------------------------------------------------------------
# 6. A CASE-derived value inside a branch attributes the field (so the
#    IF/ELSE ladder still qualifies) but leaves the CASE body to the CASE
#    extractor
# --------------------------------------------------------------------------


def test_case_expression_value_inside_a_branch_is_not_claimed_by_this_extractor():
    sql = """
    IF @Active = 1
    BEGIN
        UPDATE dbo.Employee
        SET Tier = CASE WHEN Score >= 90 THEN 'GOLD' ELSE 'SILVER' END
        WHERE EmployeeId = @EmployeeId
    END
    ELSE
    BEGIN
        UPDATE dbo.Employee SET Tier = 'INACTIVE' WHERE EmployeeId = @EmployeeId
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    then_assigns = chains[0]["branches"][0]["assignments"]
    else_assigns = chains[0]["branches"][1]["assignments"]
    assert then_assigns == [{
        "field": "Tier",
        "value": "(nested CASE — see separate decision table)",
    }]
    # Pointer must not embed the CASE body (GOLD/SILVER stay with the CASE extractor).
    assert "GOLD" not in then_assigns[0]["value"].upper()
    assert "SILVER" not in then_assigns[0]["value"].upper()
    assert else_assigns == [{"field": "Tier", "value": "'INACTIVE'"}]

# --------------------------------------------------------------------------
# 7. A chain where two branches each assign a DIFFERENT field once is
#    correctly rejected (regression: an earlier version of this extractor
#    accepted this on a chain-wide aggregate check, producing a chain that
#    `ensure_decision_chain_coverage` could never render a table for -
#    silently invisible "coverage" that didn't actually cover anything)
# --------------------------------------------------------------------------


def test_two_branches_each_assigning_a_different_field_once_is_rejected():
    sql = """
    IF @HasBonus = 1
    BEGIN
        SET @BonusRate = 0.05
    END
    ELSE
    BEGIN
        SET @PenaltyRate = 0.02
    END
    """
    assert extract_tsql_if_elseif_chains(sql) == []


# --------------------------------------------------------------------------
# 8. IF EXISTS(...) condition text is preserved verbatim
# --------------------------------------------------------------------------


def test_if_exists_condition_is_preserved_verbatim():
    sql = """
    IF EXISTS (SELECT 1 FROM dbo.EmployeeBonusOverride WHERE EmployeeId = @EmployeeId)
    BEGIN
        SET @BonusRate = 0.20
    END
    ELSE
    BEGIN
        SET @BonusRate = 0.05
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    assert chains[0]["branches"][0]["branch_condition"] == (
        "EXISTS (SELECT 1 FROM dbo.EmployeeBonusOverride WHERE EmployeeId = @EmployeeId)"
    )


# --------------------------------------------------------------------------
# 9. INSERT-based branch action (a queue/audit row, not an UPDATE) is
#    captured, positionally matching the INSERT's column list against its
#    VALUES list
# --------------------------------------------------------------------------


def test_insert_branch_action_columns_are_matched_to_their_values():
    sql = """
    IF @YearsOfService >= 10
    BEGIN
        INSERT INTO dbo.RecognitionQueue (EmployeeId, AwardDate, AwardType)
        VALUES (@EmployeeId, @ProcessDate, 'TEN_YEAR_MILESTONE')
    END
    ELSE
    BEGIN
        INSERT INTO dbo.RecognitionQueue (EmployeeId, AwardDate, AwardType)
        VALUES (@EmployeeId, @ProcessDate, 'STANDARD_REVIEW')
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    first_branch = chains[0]["branches"][0]
    assert {"field": "AwardType", "value": "'TEN_YEAR_MILESTONE'"} in first_branch["assignments"]
    assert {"field": "EmployeeId", "value": "@EmployeeId"} in first_branch["assignments"]
    second_branch = chains[0]["branches"][1]
    assert {"field": "AwardType", "value": "'STANDARD_REVIEW'"} in second_branch["assignments"]


def test_insert_values_with_nested_function_call_parentheses_split_correctly():
    """A value expression containing its own parenthesized function call
    (`DATEADD(...)`) must not be split at the comma inside it when the
    INSERT's VALUES list is parsed positionally against its columns."""
    sql = """
    IF @Escalate = 1
    BEGIN
        INSERT INTO dbo.RecognitionQueue (EmployeeId, AwardDate, AwardType)
        VALUES (@EmployeeId, DATEADD(DAY, 1, @ProcessDate), 'ESCALATED')
    END
    ELSE
    BEGIN
        INSERT INTO dbo.RecognitionQueue (EmployeeId, AwardDate, AwardType)
        VALUES (@EmployeeId, @ProcessDate, 'ROUTINE')
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    first_branch = chains[0]["branches"][0]
    assert {"field": "AwardDate", "value": "DATEADD(DAY, 1, @ProcessDate)"} in first_branch["assignments"]
    assert {"field": "AwardType", "value": "'ESCALATED'"} in first_branch["assignments"]


# --------------------------------------------------------------------------
# 10. Full pipeline integration: a synthesized rule that contradicts this
#    now-captured T-SQL IF/ELSE evidence is flagged CONFLICT and excluded
#    from the main report - proving the whole chain (extraction ->
#    reconciliation -> report exclusion) benefits, not just the extractor
#    in isolation. Different domain from DPD on purpose.
# --------------------------------------------------------------------------


_BONUS_TIER_SQL = """
CREATE PROCEDURE dbo.AssignBonusTier
    @EmployeeId INT
AS
BEGIN
    IF @Score >= 90
    BEGIN
        UPDATE dbo.Employee SET Tier = 'GOLD' WHERE EmployeeId = @EmployeeId
    END
    ELSE IF @Score >= 70
    BEGIN
        UPDATE dbo.Employee SET Tier = 'SILVER' WHERE EmployeeId = @EmployeeId
    END
    ELSE
    BEGIN
        UPDATE dbo.Employee SET Tier = 'BRONZE' WHERE EmployeeId = @EmployeeId
    END
END
"""


def _make_ingestion() -> IngestionResult:
    return IngestionResult(
        object_name="AssignBonusTier",
        object_type="PROCEDURE",
        parameters=[],
        raw_code=_BONUS_TIER_SQL,
        chunks=[CodeChunk(chunk_id="chunk_1", kind="main_body", text=_BONUS_TIER_SQL)],
        object_id="obj_bonus",
        dialect="TSQL",
        concrete_dialect="tsql",
        fallback_dialect="tsql",
        source_hash="hash",
        source_filename="demo.sql",
    )


def test_hallucinated_rule_contradicting_tsql_if_chain_is_flagged_conflict_and_excluded():
    """A model-authored rule invents a bucket scheme ('PLATINUM' at a
    threshold and with a name that appears nowhere in the source) for the
    exact same sequential IF/ELSE IF/ELSE ladder the new extractor now
    captures. Reconciliation must flag it CONFLICT using this new
    evidence, and the main report must exclude it (see
    `_exclude_conflicting_rules` in report_formatter.py) - end-to-end
    proof this extractor's evidence is actually load-bearing, not just
    self-consistent in isolation.
    """
    ingestion = _make_ingestion()
    chains = _extract_deterministic_decision_chains(ingestion.raw_code, "tsql")
    assert any(c["chain_type"] == "TSQL_IF_ELSE" for c in chains)

    deterministic_rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)

    hallucinated_rule = {
        "rule_id": "rule_hallucinated",
        "rule_name": "Assign bonus tier",
        "output_field": "Tier",
        "fields_affected": ["Tier"],
        "condition": "Score >= 90",
        "action": "Set Tier to PLATINUM.",
        "business_meaning": "Assigns a platinum tier for top performers.",
        "decision_logic_rows": [
            {"condition": "Score >= 90", "outcome": "'PLATINUM'"},  # invented value
            {"condition": "Score >= 70", "outcome": "'SILVER'"},
            {"condition": "ELSE", "outcome": "'BRONZE'"},
        ],
        "rule_type": "explicit",
        "confidence": "medium",
        "validation_status": "verified",
        "source_chunks": ["chunk_1"],
    }

    table_operations, statement_provenance = extract_table_operations_from_chunks(ingestion.chunks, "tsql")
    tables_read, tables_written = split_table_operations(table_operations)

    all_rules = deterministic_rules + [hallucinated_rule]
    synthesis = SynthesisResult(data={"business_rules": all_rules})
    merged_extraction = {
        "decision_chains": chains,
        "statement_provenance": statement_provenance,
        "table_operations": table_operations,
        "tables_read": tables_read, "tables_written": tables_written,
        "llm_tables_read": [], "llm_tables_written": [],
    }

    reconcile_deterministic_evidence(ingestion=ingestion, merged_extraction=merged_extraction, synthesis=synthesis)

    conflicting = [r for r in synthesis.data["business_rules"] if r.get("rule_id") == "rule_hallucinated"]
    assert conflicting, "the hallucinated rule must still be present in the rule list for this assertion"
    assert conflicting[0].get("reconciliation_status") == "CONFLICT"

    report = ReportFormatterAgent().format(ingestion=ingestion, merged_extraction=merged_extraction, synthesis=synthesis)
    assert "PLATINUM" not in report
    assert "GOLD" in report  # the real, deterministically-backed value is still shown


# --------------------------------------------------------------------------
# 11. Row-level WHERE filter is captured PER BRANCH, separate from the
#    branch-selection (IF/ELSE IF) condition
# --------------------------------------------------------------------------


def test_row_filter_is_captured_separately_from_branch_selection_condition():
    """Regression for a real gap: `IF EXISTS(...) BEGIN UPDATE ... WHERE
    <row filter> END` lost the UPDATE's own WHERE clause entirely - only
    the EXISTS branch-selection condition survived. The two answer
    different questions ("does this branch run at all" vs "which rows
    does it act on once it does") and must not be conflated or dropped.
    """
    sql = """
    IF EXISTS (SELECT 1 FROM dbo.Employee WHERE Overtime > 0)
    BEGIN
        UPDATE dbo.Employee SET Tier = 'OVERTIME' WHERE Overtime > 40
    END
    ELSE
    BEGIN
        UPDATE dbo.Employee SET Tier = 'STANDARD'
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    branches = chains[0]["branches"]
    assert branches[0]["branch_condition"] == "EXISTS (SELECT 1 FROM dbo.Employee WHERE Overtime > 0)"
    assert branches[0]["row_filter"] == "Overtime > 40"
    # The ELSE branch's UPDATE has no WHERE at all - unconditional, not
    # "unknown" - must be represented as an explicit empty string.
    assert branches[1]["row_filter"] == ""


def test_if_else_with_case_then_and_literal_else_still_emits_ladder():
    """Sample 08 shape: IF scheme-open THEN SET col = CASE... ELSE SET col
    = 'SCHEME_CLOSED'. Skipping CASE-valued SET left the field on only the
    ELSE branch, so the ladder failed the 2-branch-per-field bar and the
    SCHEME_CLOSED outcome disappeared from the report.
    """
    sql = """
    IF @ProcessDate < @SchemeCutoffDate
    BEGIN
        UPDATE A
        SET A.RestructureEligible =
            CASE
                WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN 'Y'
                ELSE 'N'
            END
        FROM PRO.LoanAccountCal A
    END
    ELSE
    BEGIN
        UPDATE A
        SET A.RestructureEligible = 'SCHEME_CLOSED'
        FROM PRO.LoanAccountCal A
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    assert len(chains) == 1
    branches = chains[0]["branches"]
    assert len(branches) == 2
    assert branches[0]["branch_condition"] == "@ProcessDate < @SchemeCutoffDate"
    assert branches[0]["assignments"] == [{
        "field": "RestructureEligible",
        "value": "(nested CASE — see separate decision table)",
    }]
    assert branches[1]["branch_condition"] == "ELSE"
    assert branches[1]["assignments"] == [{
        "field": "RestructureEligible",
        "value": "'SCHEME_CLOSED'",
    }]
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    assert any(
        "SCHEME_CLOSED" in str(row.get("outcome") or "")
        for rule in rules
        for row in (rule.get("decision_logic_rows") or [])
    )


def test_merge_after_if_ladder_is_not_owned_by_overextended_if_span():
    """Sample 09: IF quarter-end ReviewReason append ends, then comments,
    then MERGE. The IF span must not swallow the MERGE comment lines, and
    MERGE floors must still emit when only an insert-half LLM rule exists.
    """
    from src.synthesis.rule_synthesizer import RuleSynthesizerAgent

    sql_path = Path(__file__).resolve().parents[1] / "samples" / "09_Provision_Coverage_Merge.sql"
    raw = sql_path.read_text(encoding="utf-8")
    chains = extract_tsql_if_elseif_chains(raw)
    assert chains
    review_if = next(c for c in chains if "ReviewReason" in str(c))
    # Real ELSE END is on line 79; must not reach the MERGE comment/preamble.
    assert review_if["source_line_end"] <= 79

    merge_op = {
        "operation": "MERGE",
        "table": "PRO.ProvisionCoverageSummary",
        "source_line_start": 81,
        "source_statement_id": "merge_09",
        "merge_on_predicate": "Target.AccountId = Source.AccountId",
        "assigned_values": [
            {"merge_branch": "MATCHED", "column": "OutstandingBalance", "expression": "Source.OutstandingBalance"},
            {"merge_branch": "MATCHED", "column": "ProvisionAmount", "expression": "Source.ProvisionAmount"},
            {"merge_branch": "MATCHED", "column": "CoverageRatio", "expression": "Source.CoverageRatio"},
            {"merge_branch": "MATCHED", "column": "LastUpdatedDate", "expression": "@ProcessDate"},
            {"merge_branch": "NOT_MATCHED_BY_TARGET", "column": "AccountId", "expression": "Source.AccountId"},
            {"merge_branch": "NOT_MATCHED_BY_TARGET", "column": "OutstandingBalance", "expression": "Source.OutstandingBalance"},
            {"merge_branch": "NOT_MATCHED_BY_TARGET", "column": "FirstSeenDate", "expression": "@ProcessDate"},
            {"merge_branch": "NOT_MATCHED_BY_TARGET", "column": "LastUpdatedDate", "expression": "@ProcessDate"},
        ],
    }
    insert_only = {
        "rule_id": "llm_insert",
        "rule_name": "Insert new records",
        "output_field": "AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, FirstSeenDate, LastUpdatedDate",
        "fields_affected": [
            "AccountId", "OutstandingBalance", "ProvisionAmount",
            "CoverageRatio", "FirstSeenDate", "LastUpdatedDate",
        ],
        "decision_context": ["Target: PRO.ProvisionCoverageSummary"],
        "eligibility": ["No matching records exist in the Provision Coverage Summary table"],
        "decision_logic_rows": [{
            "condition": "No matching records exist in the Provision Coverage Summary table",
            "outcome": "insert",
        }],
        "source_evidence": ["WHEN NOT MATCHED BY TARGET THEN INSERT"],
    }
    merged = {"table_operations": [merge_op], "decision_chains": chains}
    floored = RuleSynthesizerAgent.ensure_statement_coverage([insert_only], merged)
    matched_floors = [
        rule for rule in floored
        if any(
            "WHEN MATCHED" in str(row.get("condition") or "").upper()
            for row in (rule.get("decision_logic_rows") or [])
        )
    ]
    assert matched_floors, "MATCHED MERGE floors must emit despite preceding IF span"
    from src.output.report_formatter import ReportFormatterAgent
    collapsed = ReportFormatterAgent()._collapse_merge_upsert_halves(floored)
    assert any(str(r.get("rule_name") or "").startswith("Upsert") for r in collapsed)
def test_row_filter_annotation_is_shown_distinctly_in_rendered_rows():
    sql = """
    IF EXISTS (SELECT 1 FROM dbo.Employee WHERE Overtime > 0)
    BEGIN
        UPDATE dbo.Employee SET Tier = 'OVERTIME', Bonus = 100 WHERE Overtime > 40
    END
    ELSE
    BEGIN
        UPDATE dbo.Employee SET Tier = 'STANDARD', Bonus = 0
    END
    """
    chains = extract_tsql_if_elseif_chains(sql)
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    tier_rule = next(
        r for r in rules
        if "Tier" in str(r.get("output_field") or "")
    )
    assert "Bonus" in str(tier_rule.get("output_field") or "")
    rows = {row["condition"]: row["outcome"] for row in tier_rule["decision_logic_rows"]}
    overtime_row = next(cond for cond in rows if cond.startswith("EXISTS"))
    assert "row filter: Overtime > 40" in overtime_row
    assert "Tier := 'OVERTIME'" in rows[overtime_row]
    assert "Bonus := 100" in rows[overtime_row]
    else_row = next(cond for cond in rows if cond == "ELSE — applies to all rows (no additional filter)")
    assert "Tier := 'STANDARD'" in rows[else_row]
    assert "Bonus := 0" in rows[else_row]


# --------------------------------------------------------------------------
# 12. Unreachable CASE branch (contradicts the enclosing statement's own
#    WHERE clause) is flagged, not presented as an executed outcome
# --------------------------------------------------------------------------


def test_unreachable_case_branch_is_flagged_not_silently_presented_as_executed():
    """Regression for a real report finding: `WHERE Score IS NOT NULL`
    gating an UPDATE whose own CASE still carries a `WHEN Score IS NULL
    THEN ...` branch - dead code the source keeps, which must never be
    shown with the same confidence as a branch that can actually execute.
    """
    from src.synthesis.rule_synthesizer import RuleSynthesizerAgent as RSA

    chain = {
        "chain_type": "CASE_EXPRESSION",
        "chain_id": "case_test",
        "eligibility": ["NOT Score IS NULL"],
        "branches": [
            {"branch_condition": "Score IS NULL", "assignments": [{"field": "Tier", "value": "'UNSCORED'"}]},
            {"branch_condition": "Score >= 90", "assignments": [{"field": "Tier", "value": "'GOLD'"}]},
            {"is_catch_all": True, "branch_condition": "ELSE", "assignments": [{"field": "Tier", "value": "'STANDARD'"}]},
        ],
    }
    rules = RSA.ensure_decision_chain_coverage([], [chain])
    tier_rule = next(r for r in rules if r["output_field"] == "Tier")
    unreachable_row = next(row for row in tier_rule["decision_logic_rows"] if row["outcome"] == "'UNSCORED'")
    assert "UNREACHABLE" in unreachable_row["condition"]
    reachable_row = next(row for row in tier_rule["decision_logic_rows"] if row["outcome"] == "'GOLD'")
    assert "UNREACHABLE" not in reachable_row["condition"]


def test_unreachable_annotation_does_not_defeat_duplicate_row_detection():
    """The unreachable-branch and row-filter annotations are purely
    presentational - a model-authored duplicate of the same decision
    table (which would never reproduce this exact annotation text) must
    still be recognized as a duplicate and suppressed."""
    from src.output.report_formatter import ReportFormatterAgent

    canonical_rule = {
        "rule_id": "r1", "rule_name": "Determine tier",
        "output_field": "Tier", "fields_affected": ["Tier"],
        "decision_block_id": "block1", "rule_type": "deterministic_decision_table",
        "decision_logic_rows": [
            {"condition": "Score IS NULL [UNREACHABLE — contradicts this statement's own WHERE clause; never executes for any row it touches]", "outcome": "'UNSCORED'"},
            {"condition": "Score >= 90", "outcome": "'GOLD'"},
            {"condition": "ELSE", "outcome": "'STANDARD'"},
        ],
    }
    narrative_dup = {
        "rule_id": "r2", "rule_name": "Classify tier",
        "output_field": "Tier", "fields_affected": ["Tier"],
        "decision_logic_rows": [
            {"condition": "Score IS NULL", "outcome": "'UNSCORED'"},
            {"condition": "Score >= 90", "outcome": "'GOLD'"},
            {"condition": "ELSE", "outcome": "'STANDARD'"},
        ],
    }
    result = ReportFormatterAgent()._suppress_content_duplicate_decision_tables([canonical_rule, narrative_dup])
    assert {r["rule_id"] for r in result} == {"r1"}


# --------------------------------------------------------------------------
# 13. Exception Handling never falsely claims "no explicit failure-path
#    behavior" when the source has an explicit BEGIN CATCH block
# --------------------------------------------------------------------------


def test_exception_handling_falls_back_to_catch_block_text_when_no_llm_summary():
    """Regression: `_exception_handling` accepted `raw_source` but never
    used it - when the LLM-authored `exception_handling_summary` was
    empty (a truncated response, a chunk the model never saw, ...), the
    report claimed "No explicit failure-path behavior identified", which
    is FALSE whenever the source actually has a `BEGIN CATCH` block."""
    raw_source = (
        "CREATE PROCEDURE dbo.DoWork AS BEGIN\n"
        "BEGIN TRY\n"
        "    UPDATE dbo.Employee SET Tier = 'GOLD'\n"
        "END TRY\n"
        "BEGIN CATCH\n"
        "    UPDATE dbo.JobStatus SET COMPLETED = 'N', ERRORDESCRIPTION = ERROR_MESSAGE()\n"
        "    WHERE JobName = 'DoWork'\n"
        "END CATCH\n"
        "END\n"
    )
    synthesis = SynthesisResult(data={"exception_handling_summary": ""})
    report_section = ReportFormatterAgent()._exception_handling(synthesis, raw_source=raw_source)
    assert "No explicit failure-path behavior identified" not in report_section
    assert "BEGIN CATCH" in report_section
    assert "dbo.JobStatus" in report_section
    assert "COMPLETED = 'N'" in report_section


def test_exception_handling_prefers_llm_summary_when_present():
    synthesis = SynthesisResult(data={"exception_handling_summary": "Logs the error and marks the job failed."})
    report_section = ReportFormatterAgent()._exception_handling(synthesis, raw_source="BEGIN CATCH END CATCH")
    assert "Logs the error and marks the job failed." in report_section
    assert "```sql" not in report_section


def test_exception_handling_reports_none_identified_when_truly_absent():
    synthesis = SynthesisResult(data={"exception_handling_summary": ""})
    report_section = ReportFormatterAgent()._exception_handling(synthesis, raw_source="SELECT 1")
    assert "No explicit failure-path behavior identified" in report_section
