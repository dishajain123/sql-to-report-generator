"""Permanent alias → table resolution (pipeline data, not report-only)."""
from __future__ import annotations

from src.parsing.alias_resolution import (
    alias_map_from_statement_text,
    field_for_display,
    resolve_aliases_in_business_rules,
    resolve_aliases_in_decision_chains,
    resolve_aliases_in_merged_extraction,
    rewrite_text,
)


def test_merge_target_source_bound_from_statement_text():
    text = (
        "MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source "
        "ON Target.AccountId = Source.AccountId"
    )
    alias_map = alias_map_from_statement_text(text)
    assert alias_map["TARGET"] == "PRO.DpdBucketHistory"
    assert alias_map["SOURCE"] == "#DpdStaging"
    assert rewrite_text("Source.DpdBucket", alias_map) == "#DpdStaging.DpdBucket"
    assert rewrite_text("Target.AccountId", alias_map) == "PRO.DpdBucketHistory.AccountId"


def test_update_alias_from_real_table():
    text = "UPDATE A SET A.DpdDays = 1 FROM PRO.LoanAccountCal A WHERE A.DpdDays IS NOT NULL"
    alias_map = alias_map_from_statement_text(text)
    assert alias_map["A"] == "PRO.LoanAccountCal"
    assert rewrite_text("A.DpdDays", alias_map) == "PRO.LoanAccountCal.DpdDays"


def test_english_from_the_prose_does_not_bind_alias_to_the():
    blob = "Insert into the #DpdStaging table from the A.LoanAccountCal table"
    alias_map = alias_map_from_statement_text(blob)
    assert alias_map.get("A") != "the"


def test_resolve_aliases_in_decision_chains_rewrites_branch_text():
    chains = [{
        "chain_id": "c1",
        "decision_context": [
            "Target: PRO.LoanAccountCal",
            "FROM PRO.LoanAccountCal AS A",
        ],
        "eligibility": ["A.DpdDays IS NOT NULL"],
        "branches": [{
            "branch_condition": "A.DpdDays = 0",
            "assignments": [{"field": "A.DpdBucket", "value": "'CURRENT'"}],
        }],
    }]
    resolved = resolve_aliases_in_decision_chains(chains, {})
    assert resolved[0]["eligibility"] == ["PRO.LoanAccountCal.DpdDays IS NOT NULL"]
    assert resolved[0]["branches"][0]["branch_condition"] == "PRO.LoanAccountCal.DpdDays = 0"
    assert resolved[0]["branches"][0]["assignments"][0]["field"] == "PRO.LoanAccountCal.DpdBucket"


def test_resolve_aliases_in_business_rules_and_merged_extraction():
    merged = {
        "table_operations": [{
            "operation": "MERGE",
            "table": "PRO.DpdBucketHistory",
            "table_alias": "Target",
            "source_statement_text": (
                "MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source "
                "ON Target.AccountId = Source.AccountId"
            ),
        }],
        "decision_chains": [],
    }
    merged = resolve_aliases_in_merged_extraction(merged)
    rules = resolve_aliases_in_business_rules(
        [{
            "rule_id": "r1",
            "rule_name": "Upsert",
            "decision_logic_rows": [
                {"condition": "WHEN MATCHED", "outcome": "Source.DpdBucket"},
            ],
            "source_evidence": [merged["table_operations"][0]["source_statement_text"]],
        }],
        merged,
    )
    assert rules[0]["decision_logic_rows"][0]["outcome"] == "#DpdStaging.DpdBucket"


def test_field_for_display_keeps_schema_and_strips_unresolved_roles():
    assert field_for_display("PRO.LoanAccountCal.DpdDays") == "PRO.LoanAccountCal.DpdDays"
    assert field_for_display("Target.AccountId") == "AccountId"
    assert field_for_display("A.DpdDays") == "DpdDays"
