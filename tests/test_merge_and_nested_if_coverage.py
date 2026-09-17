"""MERGE assigned_values extraction and nested IF coverage regressions."""

from __future__ import annotations

from pathlib import Path

from src.ingestion.ingestion import CodeIngestionAgent
from src.parsing.alias_resolution import strip_redundant_table_qualifiers
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent
from pipeline import _extract_deterministic_decision_chains


SAMPLE_07 = Path(__file__).resolve().parent.parent / "samples" / "07_DPD_Bucket_Classification.sql"


def test_merge_captures_matched_update_and_insert_assignments():
    sql = SAMPLE_07.read_text()
    ingestion = CodeIngestionAgent().ingest_text(
        sql, dialect="tsql", source_filename="07_DPD_Bucket_Classification.sql"
    )
    writes, _reads = extract_table_operations_from_chunks(ingestion.chunks, dialect="tsql")
    merges = [op for op in writes if op.get("operation") == "MERGE"]
    assert len(merges) >= 1
    merge = next(op for op in merges if "DpdBucketHistory" in str(op.get("table") or ""))
    assigned = merge.get("assigned_values") or []
    assert assigned, "MERGE must expose WHEN MATCHED / NOT MATCHED assignments"
    matched_cols = {
        str(item.get("column") or "").split(".")[-1]
        for item in assigned
        if item.get("merge_branch") == "MATCHED"
    }
    assert matched_cols >= {"DpdBucket", "AdjustedPenalty", "LastUpdatedDate"}
    insert_cols = {
        str(item.get("column") or "").split(".")[-1]
        for item in assigned
        if str(item.get("merge_branch") or "").startswith("NOT_MATCHED")
    }
    assert "AccountId" in insert_cols
    assert "FirstFlaggedDate" in insert_cols


def test_tsql_if_ladder_emits_multi_field_rule_with_gates_and_row_filters():
    sql = SAMPLE_07.read_text()
    chains = _extract_deterministic_decision_chains(sql, dialect="tsql")
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    ladder = next(
        rule
        for rule in rules
        if "BucketWorsened" in str(rule.get("output_field") or "")
    )
    assert "GracePeriodApplied" in str(ladder.get("output_field") or "")
    rows = ladder.get("decision_logic_rows") or []
    assert len(rows) == 3
    assert "EXISTS" in rows[0]["condition"]
    assert "row filter:" in rows[0]["condition"]
    assert "GracePeriodApplied := 'Y'" in rows[0]["outcome"]
    assert "BucketWorsened := 'Y'" in rows[1]["outcome"]
    assert rows[2]["condition"].startswith("ELSE")
    assert "BucketWorsened := 'N'" in rows[2]["outcome"]


def test_statement_coverage_does_not_orphan_fields_inside_tsql_if_ladder():
    sql = SAMPLE_07.read_text()
    chains = _extract_deterministic_decision_chains(sql, dialect="tsql")
    ingestion = CodeIngestionAgent().ingest_text(
        sql, dialect="tsql", source_filename="07_DPD_Bucket_Classification.sql"
    )
    writes, _reads = extract_table_operations_from_chunks(ingestion.chunks, dialect="tsql")
    merged = {"table_operations": writes, "decision_chains": chains}
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    rules = RuleSynthesizerAgent.ensure_statement_coverage(rules, merged)
    assert not any(
        str(rule.get("output_field") or "").strip() == "GracePeriodApplied"
        for rule in rules
    )
    # No single-branch floor that only restates the grace WHERE without IF EXISTS.
    for rule in rules:
        rows = rule.get("decision_logic_rows") or []
        if len(rows) != 1:
            continue
        condition = str(rows[0].get("condition") or "")
        assert not (
            "LastPaymentDueDate >= @GraceWindowStart" in condition
            and "EXISTS" not in condition
            and "GracePeriodApplied" in str(rule.get("output_field") or "")
        )


def test_strip_redundant_table_qualifiers_when_target_known():
    text = (
        "PRO.LoanAccountCal.DpdBucket = 'BUCKET_1_30' AND "
        "OtherTable.Status = 'X'"
    )
    cleaned = strip_redundant_table_qualifiers(text, ["PRO.LoanAccountCal"])
    assert "DpdBucket = 'BUCKET_1_30'" in cleaned
    assert "PRO.LoanAccountCal.DpdBucket" not in cleaned
    # Unrelated table qualifier must stay for disambiguation.
    assert "OtherTable.Status = 'X'" in cleaned


def test_strip_redundant_qualifiers_preserves_temp_table_hash():
    cleaned = strip_redundant_table_qualifiers(
        "#DPD.DPD_IntService >= #DPD.DPD_NoCredit",
        ["#DPD"],
    )
    assert cleaned == "DPD_IntService >= DPD_NoCredit"
    # Must not leave a stray leading hash glued to the column.
    assert "#DPD_IntService" not in cleaned


def test_if_ladder_survives_multiline_case_in_a_branch():
    """A multi-line `CASE ... END` closes with a line that is literally
    `END`, indistinguishable from a block terminator by line shape. It used
    to decrement BEGIN/END depth, closing the branch early and
    desynchronizing the walk, so the WHOLE ladder was dropped - including
    the sibling branches that parse fine. Modelled on
    samples/16_Guarantee_Cover_Appropriation.sql.
    """
    from src.validation.semantic_validation import extract_tsql_if_elseif_chains

    source = """
IF @FundRenewalDate IS NOT NULL AND @ProcessDate >= DATEADD(DAY, -7, @FundRenewalDate)
BEGIN
    UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.T A
END
ELSE IF @AvailableCoverBalance > 0
BEGIN
    UPDATE A
    SET A.CoverAppropriatedAmount =
        CASE
            WHEN A.AssetClass IN ('DOUBTFUL', 'LOSS') THEN
                CASE WHEN A.Req <= @Bal THEN A.Req ELSE @Bal END
            ELSE 0
        END
    FROM PRO.T A
END
ELSE
BEGIN
    UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.T A
END
"""
    chains = extract_tsql_if_elseif_chains(source)
    assert len(chains) == 1
    branches = chains[0]["branches"]
    assert len(branches) == 3
    # The blackout branch and the no-balance ELSE must both survive.
    conditions = " | ".join(str(b.get("branch_condition")) for b in branches)
    assert "FundRenewalDate" in conditions
    assert "ELSE" in conditions
