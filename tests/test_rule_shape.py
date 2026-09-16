"""Permanent structural rule shaping (pipeline / IR path)."""

from src.synthesis.rule_shape import (
    clear_grounded_reconciliation_conflicts,
    drop_ungrounded_conflict_rules,
    finalize_business_rule_shape,
    shape_structural_business_rules,
)


def test_shape_suppresses_ladder_fragment_and_keeps_ladder():
    ladder = {
        "rule_id": "ladder",
        "rule_name": "Bucket Worsened",
        "rule_type": "deterministic_decision_table",
        "decision_block_id": "tsql_if_1",
        "fields_affected": ["BucketWorsened"],
        "decision_logic_rows": [
            {"condition": "EXISTS overdue — row filter: PrevDpdBucket IS NOT NULL", "outcome": "1"},
            {"condition": "ELSE", "outcome": "0"},
        ],
    }
    fragment = {
        "rule_id": "frag",
        "rule_name": "Reset Bucket Worsened",
        "fields_affected": ["BucketWorsened"],
        "decision_logic_rows": [
            {"condition": "PrevDpdBucket IS NOT NULL AND DpdBucket <> PrevDpdBucket", "outcome": "1"},
        ],
    }
    shaped = shape_structural_business_rules([ladder, fragment])
    ids = {r["rule_id"] for r in shaped}
    assert "ladder" in ids
    assert "frag" not in ids


def test_shape_collapses_merge_matched_and_unmatched():
    matched = {
        "rule_id": "m1",
        "rule_name": "Update existing records",
        "output_field": "DpdBucket, AdjustedPenalty, LastUpdatedDate",
        "fields_affected": ["DpdBucket", "AdjustedPenalty", "LastUpdatedDate"],
        "decision_context": ["Target: PRO.DpdBucketHistory"],
        "decision_logic_rows": [
            {
                "condition": "Target.AccountId = Source.AccountId",
                "outcome": "Source.DpdBucket, Source.AdjustedPenalty, @ProcessDate",
            }
        ],
        "source_evidence": ["WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket"],
    }
    unmatched = {
        "rule_id": "m2",
        "rule_name": "Insert new records",
        "output_field": "AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate",
        "fields_affected": [
            "AccountId",
            "DpdBucket",
            "AdjustedPenalty",
            "FirstFlaggedDate",
            "LastUpdatedDate",
        ],
        "decision_context": ["Target: PRO.DpdBucketHistory"],
        "decision_logic_rows": [
            {
                "condition": "Record does not exist in DpdBucketHistory table",
                "outcome": "Source.AccountId",
            }
        ],
        "source_evidence": ["WHEN NOT MATCHED BY TARGET THEN INSERT"],
    }
    shaped = shape_structural_business_rules([matched, unmatched])
    assert len(shaped) == 1
    assert shaped[0]["rule_name"].startswith("Upsert")
    rows = shaped[0].get("decision_logic_rows") or []
    assert [row["condition"] for row in rows] == ["WHEN MATCHED", "WHEN NOT MATCHED BY TARGET"]


def test_clear_grounded_conflict_keeps_audit_style_rule():
    grounded = {
        "rule_id": "audit",
        "rule_name": "Audit insert",
        "decision_rows_grounded": True,
        "reconciliation_status": "CONFLICT",
        "decision_logic_rows": [
            {"condition": "WHERE Changed = 1", "outcome": "INSERT INTO Audit"},
        ],
    }
    shell = {
        "rule_id": "noise",
        "rule_name": "Bad claim",
        "reconciliation_status": "CONFLICT",
        "decision_logic_rows": [{"condition": "1=1", "outcome": "X"}],
    }
    cleared = clear_grounded_reconciliation_conflicts([grounded, shell])
    assert cleared[0]["reconciliation_status"] == "MATCHED"
    assert cleared[1]["reconciliation_status"] == "CONFLICT"
    kept = drop_ungrounded_conflict_rules(cleared)
    assert [r["rule_id"] for r in kept] == ["audit"]


def test_finalize_after_reconciliation_shapes_and_drops_conflicts():
    ladder = {
        "rule_id": "ladder",
        "rule_name": "Stages",
        "rule_type": "deterministic_decision_table",
        "decision_block_id": "tsql_if_1",
        "fields_affected": ["StageFlag"],
        "decision_logic_rows": [
            {"condition": "A", "outcome": "1"},
            {"condition": "ELSE", "outcome": "0"},
        ],
        "reconciliation_status": "MATCHED",
    }
    fragment = {
        "rule_id": "frag",
        "rule_name": "Reset Stage",
        "fields_affected": ["StageFlag"],
        "decision_logic_rows": [{"condition": "A", "outcome": "1"}],
        "reconciliation_status": "CONFLICT",
    }
    grounded = {
        "rule_id": "ins",
        "rule_name": "Queue insert",
        "decision_rows_grounded": True,
        "reconciliation_status": "CONFLICT",
        "decision_logic_rows": [
            {"condition": "WHERE Flag = 1", "outcome": "INSERT INTO Queue"},
        ],
    }
    final = finalize_business_rule_shape(
        [ladder, fragment, grounded],
        after_reconciliation=True,
    )
    ids = {r["rule_id"] for r in final}
    assert ids == {"ladder", "ins"}
    assert next(r for r in final if r["rule_id"] == "ins")["reconciliation_status"] == "MATCHED"
