"""Regression tests for rule/decision-chain identity normalization and
duplicate-rule consolidation.

Root cause (real bug, traced against a real generated report -
samples/output/1_PRO.DPD_Bucket_Classification.StoredProcedure_report.md,
produced from samples/07_DPD_Bucket_Classification.sql): two independently
extracted rules for the exact same underlying SQL decision were rendered
as separate numbered rules because rule-identity comparison never stripped
table/alias/bracket qualifiers from condition text before comparing. The
fixture data below is a literal reconstruction of that real report's rule
rows (labeled as fixtures only - nothing in src/ references this
procedure, table, or column names).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parsing.decision_identity import (
    bare_field_key,
    normalized_condition_key,
    rule_decision_identity,
    strip_qualifiers,
)
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent


# --------------------------------------------------------------------------
# strip_qualifiers / bare_field_key / normalized_condition_key
# --------------------------------------------------------------------------


def test_strip_qualifiers_collapses_plain_alias_qualified_chain():
    assert strip_qualifiers("A.DpdDays") == "DpdDays"


def test_strip_qualifiers_collapses_fully_schema_qualified_chain():
    assert strip_qualifiers("PRO.LoanAccountCal.DpdDays") == "DpdDays"


def test_strip_qualifiers_collapses_bracketed_chain():
    assert strip_qualifiers("[PRO].[LoanAccountCal].[DpdDays]") == "DpdDays"


def test_strip_qualifiers_collapses_mixed_bracket_and_plain_chain():
    assert strip_qualifiers("[PRO].LoanAccountCal.DpdDays") == "DpdDays"


def test_strip_qualifiers_handles_merge_target_source_aliases():
    assert strip_qualifiers("Target.DpdBucket") == "DpdBucket"
    assert strip_qualifiers("Source.DpdBucket") == "DpdBucket"


def test_strip_qualifiers_handles_temp_table_qualifier():
    assert strip_qualifiers("#DpdStaging.FacilityType") == "FacilityType"


def test_strip_qualifiers_leaves_bare_identifier_unchanged():
    assert strip_qualifiers("DpdDays") == "DpdDays"


def test_strip_qualifiers_never_mangles_a_decimal_literal():
    assert strip_qualifiers("AdjustedPenalty * 1.10") == "AdjustedPenalty * 1.10"


def test_bare_field_key_matches_across_qualification_styles():
    keys = {
        bare_field_key("PRO.LoanAccountCal.DpdBucket"),
        bare_field_key("A.DpdBucket"),
        bare_field_key("[PRO].[LoanAccountCal].[DpdBucket]"),
        bare_field_key("DpdBucket"),
    }
    assert len(keys) == 1


def test_normalized_condition_key_matches_qualified_and_bare_condition():
    qualified = "PRO.LoanAccountCal.DpdDays BETWEEN 1 AND 30"
    bare = "DpdDays BETWEEN 1 AND 30"
    assert normalized_condition_key(qualified) == normalized_condition_key(bare)


def test_normalized_condition_key_protects_string_literal_contents():
    # A literal containing something bracket/dot-shaped must never be
    # mistaken for a qualifier chain and rewritten.
    left = normalized_condition_key("Status = 'A.B'")
    right = normalized_condition_key("Status = 'A.B'")
    assert left == right
    assert "'A.B'" in left  # literal survives untouched, not collapsed to 'B'


def test_normalized_condition_key_is_case_and_whitespace_insensitive():
    assert normalized_condition_key("DpdDays   =   0") == normalized_condition_key("dpddays = 0")


# --------------------------------------------------------------------------
# rule_decision_identity - the (field, conditions) merge key
# --------------------------------------------------------------------------

# Literal fixtures reconstructed from the real report's R3/R4 (DpdBucket
# classification, qualified vs bare), R9/R10 (facility-type penalty
# adjustment, qualified vs bare), and R6/R7 (penalty-interest calculation,
# same 4 conditions but R7 bundles unrelated extra content into 2 of the 4
# outcomes - simulating a coverage-retry pass that fused in nearby,
# unrelated logic). R8 has a genuinely different, shorter condition ladder
# and must NOT be treated as the same rule as R6/R7.

_R3_ROWS = [
    {"condition": "PRO.LoanAccountCal.DpdDays IS NULL", "outcome": "'NOT_APPLICABLE'"},
    {"condition": "PRO.LoanAccountCal.DpdDays = 0", "outcome": "'CURRENT'"},
    {"condition": "PRO.LoanAccountCal.DpdDays BETWEEN 1 AND 30", "outcome": "'BUCKET_1_30'"},
    {"condition": "PRO.LoanAccountCal.DpdDays BETWEEN 31 AND 60", "outcome": "'BUCKET_31_60'"},
    {"condition": "PRO.LoanAccountCal.DpdDays BETWEEN 61 AND 90", "outcome": "'BUCKET_61_90'"},
    {"condition": "ELSE", "outcome": "'BUCKET_90_PLUS'"},
]
_R4_ROWS = [
    {"condition": "DpdDays IS NULL", "outcome": "'NOT_APPLICABLE'"},
    {"condition": "DpdDays = 0", "outcome": "'CURRENT'"},
    {"condition": "DpdDays BETWEEN 1 AND 30", "outcome": "'BUCKET_1_30'"},
    {"condition": "DpdDays BETWEEN 31 AND 60", "outcome": "'BUCKET_31_60'"},
    {"condition": "DpdDays BETWEEN 61 AND 90", "outcome": "'BUCKET_61_90'"},
    {"condition": "ELSE", "outcome": "'BUCKET_90_PLUS'"},
]

_R9_ROWS = [
    {"condition": "#DpdStaging.FacilityType IN ('CC', 'OD')", "outcome": "#DpdStaging.AdjustedPenalty * 1.10"},
    {"condition": "#DpdStaging.FacilityType IN ('TL', 'DL')", "outcome": "#DpdStaging.AdjustedPenalty * 1.05"},
    {"condition": "ELSE", "outcome": "#DpdStaging.AdjustedPenalty"},
]
_R10_ROWS = [
    {"condition": "FacilityType IN ('CC', 'OD')", "outcome": "AdjustedPenalty * 1.10"},
    {"condition": "FacilityType IN ('TL', 'DL')", "outcome": "AdjustedPenalty * 1.05"},
    {"condition": "ELSE", "outcome": "AdjustedPenalty"},
]

_R6_ROWS = [
    {"condition": "PRO.LoanAccountCal.DpdBucket = 'BUCKET_1_30'", "outcome": "(PRO.LoanAccountCal.OutstandingBalance * 0.02) / 365 * PRO.LoanAccountCal.DpdDays"},
    {"condition": "PRO.LoanAccountCal.DpdBucket = 'BUCKET_31_60'", "outcome": "(PRO.LoanAccountCal.OutstandingBalance * 0.03) / 365 * PRO.LoanAccountCal.DpdDays"},
    {"condition": "PRO.LoanAccountCal.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS')", "outcome": "(PRO.LoanAccountCal.OutstandingBalance * 0.04) / 365 * PRO.LoanAccountCal.DpdDays"},
    {"condition": "ELSE", "outcome": "0"},
]
_R7_ROWS = [
    {"condition": "DpdBucket = 'BUCKET_1_30'", "outcome": "(OutstandingBalance * 0.02) / 365 * DpdDays"},
    {"condition": "DpdBucket = 'BUCKET_31_60'", "outcome": "(OutstandingBalance * 0.03) / 365 * DpdDays"},
    {"condition": "DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS')", "outcome": "(OutstandingBalance * 0.04) / 365 * DpdDays; 'SEVERE_DPD_OTHER_FACILITY'"},
    {"condition": "ELSE", "outcome": "0; 'EARLY_DPD_WORSENED'"},
]
_R8_ROWS = [
    {"condition": "DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD')", "outcome": "'SEVERE_DPD_CASH_CREDIT'; Update BucketWorsened and GracePeriodApplied"},
    {"condition": "DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS')", "outcome": "(OutstandingBalance * 0.04) / 365 * DpdDays; 'SEVERE_DPD_OTHER_FACILITY'"},
    {"condition": "ELSE", "outcome": "0; 'EARLY_DPD_WORSENED'"},
]


def test_r3_r4_share_identity_after_normalization():
    assert rule_decision_identity("DpdBucket", _R3_ROWS) == rule_decision_identity("DpdBucket", _R4_ROWS)
    assert rule_decision_identity("PRO.LoanAccountCal.DpdBucket", _R3_ROWS) == rule_decision_identity("A.DpdBucket", _R4_ROWS)


def test_r9_r10_share_identity_after_normalization():
    assert rule_decision_identity("AdjustedPenalty", _R9_ROWS) == rule_decision_identity("AdjustedPenalty", _R10_ROWS)
    assert rule_decision_identity("#DpdStaging.AdjustedPenalty", _R9_ROWS) == rule_decision_identity("S.AdjustedPenalty", _R10_ROWS)


def test_r6_r7_share_identity_despite_differing_bundled_outcomes():
    # Conditions match once normalized even though R7's outcomes bundle in
    # unrelated extra content on 2 of the 4 branches - identity is
    # condition-based only, by design (see rule_decision_identity docstring).
    assert rule_decision_identity("PenalInterestAmount", _R6_ROWS) == rule_decision_identity(
        "PenalInterestAmount", _R7_ROWS
    )


def test_r8_does_not_share_identity_with_r6_or_r7():
    # R8's condition ladder is genuinely different (fewer branches, an
    # extra AND clause on the first condition) - must NOT be merged in.
    assert rule_decision_identity("PenalInterestAmount", _R8_ROWS) != rule_decision_identity(
        "PenalInterestAmount", _R6_ROWS
    )
    assert rule_decision_identity("PenalInterestAmount", _R8_ROWS) != rule_decision_identity(
        "PenalInterestAmount", _R7_ROWS
    )


def test_genuinely_different_rules_sharing_a_target_column_do_not_collide():
    # Two rules that both affect the same field but branch on completely
    # different conditions (e.g. a status-classification rule vs a
    # separate default/fallback rule for the same field in another
    # statement) must never be treated as the same rule just because the
    # target column matches.
    rows_a = [{"condition": "OverdueDays > 90", "outcome": "'HIGH_RISK'"}]
    rows_b = [{"condition": "AccountType = 'PREMIUM'", "outcome": "'LOW_RISK'"}]
    assert rule_decision_identity("RiskCategory", rows_a) != rule_decision_identity("RiskCategory", rows_b)


# --------------------------------------------------------------------------
# RuleSynthesizerAgent.consolidate_duplicate_rules
# --------------------------------------------------------------------------

_R3_RULE = {"rule_id": "r3", "output_field": "DpdBucket", "rule_name": "Classify (qualified)", "decision_logic_rows": _R3_ROWS}
_R4_RULE = {"rule_id": "r4", "output_field": "DpdBucket", "rule_name": "Classify (bare)", "decision_logic_rows": _R4_ROWS}
_R9_RULE = {"rule_id": "r9", "output_field": "AdjustedPenalty", "rule_name": "Adjust (qualified)", "decision_logic_rows": _R9_ROWS}
_R10_RULE = {"rule_id": "r10", "output_field": "AdjustedPenalty", "rule_name": "Adjust (bare)", "decision_logic_rows": _R10_ROWS}
_R6_RULE = {"rule_id": "r6", "output_field": "PenalInterestAmount", "rule_name": "Calc (clean)", "decision_logic_rows": _R6_ROWS}
_R7_RULE = {
    "rule_id": "r7", "output_field": "PenalInterestAmount",
    "fields_affected": ["AccountId", "EscalationDate", "Reason"],
    "rule_name": "Calc (bundled)", "decision_logic_rows": _R7_ROWS,
}
_R8_RULE = {
    "rule_id": "r8", "output_field": "PenalInterestAmount",
    "fields_affected": ["BucketWorsened", "GracePeriodApplied", "AccountId", "EscalationDate", "Reason"],
    "rule_name": "Calc (most bundled)", "decision_logic_rows": _R8_ROWS,
}


def test_consolidate_merges_r3_r4_into_one_rule():
    result = RuleSynthesizerAgent.consolidate_duplicate_rules([_R3_RULE, _R4_RULE])
    assert len(result) == 1


def test_consolidate_merges_r9_r10_into_one_rule():
    result = RuleSynthesizerAgent.consolidate_duplicate_rules([_R9_RULE, _R10_RULE])
    assert len(result) == 1


def test_consolidate_merges_r6_r7_keeping_narrowest_and_footnoting_the_rest():
    result = RuleSynthesizerAgent.consolidate_duplicate_rules([_R6_RULE, _R7_RULE])
    assert len(result) == 1
    merged = result[0]
    assert merged["rule_id"] == "r6"  # narrowest (fewest fields) kept
    assert merged["decision_logic_rows"] == _R6_ROWS  # clean outcomes preserved, not fused
    note = merged.get("consolidation_note") or ""
    assert "AccountId" in note and "EscalationDate" in note and "Reason" in note


def test_consolidate_does_not_merge_r8_with_r6_r7():
    result = RuleSynthesizerAgent.consolidate_duplicate_rules([_R6_RULE, _R7_RULE, _R8_RULE])
    ids = {r["rule_id"] for r in result}
    assert ids == {"r6", "r8"}  # r7 merged away into r6; r8 stands alone


def test_consolidate_merge_keeps_only_the_kept_candidates_degraded_flag():
    clean = dict(_R6_RULE, degraded=False)
    noisy = dict(_R7_RULE, degraded=True)
    result = RuleSynthesizerAgent.consolidate_duplicate_rules([clean, noisy])
    assert len(result) == 1
    assert result[0]["degraded"] is False  # not OR'd - the kept (clean) candidate wins


def test_consolidate_never_merges_rules_with_no_decision_logic_rows():
    a = {"rule_id": "a", "output_field": "Status", "decision_logic_rows": []}
    b = {"rule_id": "b", "output_field": "Status", "decision_logic_rows": []}
    result = RuleSynthesizerAgent.consolidate_duplicate_rules([a, b])
    assert len(result) == 2


def test_consolidate_leaves_genuinely_different_rules_alone():
    rule_a = {"rule_id": "a", "output_field": "RiskCategory",
              "decision_logic_rows": [{"condition": "OverdueDays > 90", "outcome": "'HIGH_RISK'"}]}
    rule_b = {"rule_id": "b", "output_field": "RiskCategory",
              "decision_logic_rows": [{"condition": "AccountType = 'PREMIUM'", "outcome": "'LOW_RISK'"}]}
    result = RuleSynthesizerAgent.consolidate_duplicate_rules([rule_a, rule_b])
    assert len(result) == 2


# --------------------------------------------------------------------------
# RuleSynthesizerAgent._remove_tautological_rules
# --------------------------------------------------------------------------


def test_tautology_filter_drops_single_field_not_null_guard():
    rule = {"rule_id": "r17", "output_field": "PenalInterestAmount",
            "decision_logic_rows": [{"condition": "PenalInterestAmount is not null", "outcome": "Update PenalInterestAmount"}]}
    assert RuleSynthesizerAgent._remove_tautological_rules([rule]) == []


def test_tautology_filter_drops_multi_field_are_not_null_guard():
    rule = {"rule_id": "r18", "output_field": "AccountId",
            "decision_logic_rows": [{
                "condition": "AccountId, DpdBucket, FacilityType, AdjustedPenalty are not null",
                "outcome": "Insert and update records in #DpdStaging",
            }]}
    assert RuleSynthesizerAgent._remove_tautological_rules([rule]) == []


def test_tautology_filter_keeps_real_multi_branch_business_rule():
    rule = {"rule_id": "r16", "output_field": "DpdBucket",
            "decision_logic_rows": [
                {"condition": "DpdDays > 90 AND FacilityType IN ('CC', 'OD')", "outcome": "'SEVERE_DPD_CASH_CREDIT'"},
            ]}
    assert RuleSynthesizerAgent._remove_tautological_rules([rule]) == [rule]


def test_tautology_filter_keeps_multi_row_rule_even_if_first_row_is_a_null_guard():
    rule = {"rule_id": "mixed", "output_field": "Status",
            "decision_logic_rows": [
                {"condition": "Status is not null", "outcome": "Update Status"},
                {"condition": "Score > 90", "outcome": "'APPROVED'"},
            ]}
    assert RuleSynthesizerAgent._remove_tautological_rules([rule]) == [rule]


def test_tautology_filter_keeps_a_null_check_that_is_not_paired_with_a_bare_operation_outcome():
    # A calculated/literal outcome after a not-null guard is real content,
    # not a restatement of the write - must never be dropped.
    rule = {"rule_id": "real", "output_field": "PenalInterestAmount",
            "decision_logic_rows": [{"condition": "OutstandingBalance is not null", "outcome": "OutstandingBalance * 0.02"}]}
    assert RuleSynthesizerAgent._remove_tautological_rules([rule]) == [rule]
