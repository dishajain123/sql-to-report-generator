from src.validation.semantic_validation import (
    extract_procedural_decision_chains,
  extract_nested_decision_chains,
    extract_case_assignment_decision_chains,
    merge_decision_chains,
    find_semantic_anomalies,
)


def test_extracts_ordered_oracle_ladder_and_effective_else_condition():
    source = """
    IF v_overdue_days <= 90 THEN
      v_classification := 'STANDARD';
      v_provision_pct := 0.40;
    ELSIF v_overdue_days BETWEEN 91 AND 365 THEN
      v_classification := 'SUBSTANDARD';
      v_provision_pct := 15;
    ELSE
      v_classification := 'LOSS';
      v_provision_pct := 100;
    END IF;
    """
    chains = extract_procedural_decision_chains(source)
    assert len(chains) == 1
    assert [branch["branch_condition"] for branch in chains[0]["branches"]] == [
        "v_overdue_days <= 90",
        "v_overdue_days BETWEEN 91 AND 365",
        "ELSE",
    ]
    assert [assignment["value"] for assignment in chains[0]["branches"][0]["assignments"]] == [
        "'STANDARD'", "0.40"
    ]
    assert "all preceding conditions are false" in chains[0]["branches"][-1]["effective_condition"]


def test_flags_sub_one_provision_percentage_divided_by_100():
    source = "v_rate := 0.40; result := v_balance * v_rate / 100;"
    findings = find_semantic_anomalies(source)
    assert findings
    assert "v_rate" in findings[0]


def test_nested_decision_chain_keeps_parent_and_child_conditions_bound():
    source = """
    IF v_days <= 90 THEN
      v_status := 'STANDARD';
    ELSIF v_days BETWEEN 91 AND 365 THEN
      v_status := 'SUBSTANDARD';
    ELSIF v_days BETWEEN 366 AND 1095 THEN
      IF v_since <= 365 THEN
        v_status := 'DOUBTFUL1';
      ELSE
        v_status := 'DOUBTFUL2';
      END IF;
    ELSE
      IF v_since > 1095 THEN
        v_status := 'LOSS';
      ELSE
        v_status := 'DOUBTFUL3';
      END IF;
    END IF;
    """
    chain = extract_nested_decision_chains(source)[0]
    values = [item["value"] for branch in chain["branches"] for item in branch["assignments"]]
    conditions = [branch["branch_condition"] for branch in chain["branches"]]
    assert values == ["'STANDARD'", "'SUBSTANDARD'", "'DOUBTFUL1'", "'DOUBTFUL2'", "'LOSS'", "'DOUBTFUL3'"]
    assert "v_days BETWEEN 366 AND 1095" in conditions[2]
    assert "v_since <= 365" in conditions[2]
    assert "v_since > 1095" in conditions[4]


def test_tsql_case_expression_assignment_ladder_is_captured():
    """Regression test for the failure mode found while investigating lost
    business logic in T-SQL stored procedures (e.g. PRO.SMA_MARKING): a
    multi-branch SMA classification CASE expression assigned to a table
    column. T-SQL has no IF/THEN/END IF syntax, so the PL/SQL-only ladder
    extractors never fire here - this must be picked up on its own.
    """
    source = """
    UPDATE A SET A.SMA_CLASS=
       (CASE  WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0'
              WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1'
              WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2'
              WHEN dpd.DPD_Max > 90 THEN 'SMA_2'
              ELSE NULL
       END)
    FROM ##AccountCal A
    """
    chains = extract_case_assignment_decision_chains(source)
    assert len(chains) == 1
    chain = chains[0]
    assert chain["chain_type"] == "CASE_EXPRESSION"
    conditions = [branch["branch_condition"] for branch in chain["branches"]]
    assert conditions == [
        "dpd.DPD_Max BETWEEN 1 AND 30",
        "dpd.DPD_Max BETWEEN 31 AND 60",
        "dpd.DPD_Max BETWEEN 61 AND 90",
        "dpd.DPD_Max > 90",
        "ELSE",
    ]
    values = [branch["assignments"][0]["value"] for branch in chain["branches"]]
    assert values == ["'SMA_0'", "'SMA_1'", "'SMA_2'", "'SMA_2'", "NULL"]
    # The alias-qualified target column collapses to the bare business
    # field name so it lines up with how a rule would name it.
    assert all(branch["assignments"][0]["field"] == "SMA_CLASS" for branch in chain["branches"])
    assert "all preceding conditions are false" in chain["branches"][-1]["effective_condition"]


def test_case_expression_ignores_commented_out_when_branch():
    """A WHEN clause that is commented out in the source must never be
    reported as a live branch (would fabricate business logic that isn't
    actually executed)."""
    source = """
    DegReason = CASE --------WHEN  PeakDPD>=A.REFPERIODOVERDUE THEN 'NPA due to Peak DPD'
        WHEN  ISNULL(B.DPD_Seller,0)>=A.REFPERIODOVERDUE THEN 'NPA Due to Virtual DPD'
        WHEN  B.NPA_ClassSeller='Y' THEN 'NPA Due to Seller Classification'
    END
    """
    chains = extract_case_assignment_decision_chains(source)
    assert len(chains) == 1
    conditions = [branch["branch_condition"] for branch in chains[0]["branches"]]
    assert "PeakDPD>=A.REFPERIODOVERDUE" not in " ".join(conditions)
    assert len(conditions) == 2


def test_case_expression_as_alias_target_is_captured():
    """The `CASE ... END AS alias` projection form (common in SELECT/INSERT
    ... SELECT) is also a genuine assignment target, not just `field = CASE`."""
    source = """
    SELECT CustomerID,
        CASE WHEN DPD BETWEEN 1 AND 90 THEN 'STANDARD'
             WHEN DPD BETWEEN 91 AND 365 THEN 'SUBSTANDARD'
             ELSE 'DOUBTFUL'
        END AS AssetClass
    FROM Accounts
    """
    chains = extract_case_assignment_decision_chains(source)
    assert len(chains) == 1
    assert chains[0]["branches"][0]["assignments"][0]["field"] == "AssetClass"
    assert len(chains[0]["branches"]) == 3


def test_case_expression_nested_case_keeps_full_outer_and_inner_value_text():
    """A nested CASE inside a THEN/ELSE clause must not crash the matcher
    and its full text must survive intact in the outer branch's value
    (verifies no branch text is discarded, even if not further split)."""
    source = """
    A.SMA_CLASS = CASE WHEN A.FACILITYTYPE IN ('CC','OD')
                        THEN (CASE WHEN REFPERIODOVERDRAWN-60>=DPD_MAX THEN 'SMA_0'
                                   WHEN REFPERIODOVERDRAWN-30>=DPD_MAX THEN 'SMA_1'
                                   ELSE 'SMA_2' END)
                        ELSE 'SMA_UNKNOWN'
                   END
    """
    chains = extract_case_assignment_decision_chains(source)
    assert len(chains) == 1
    branches = chains[0]["branches"]
    assert len(branches) == 2
    facility_branch_value = branches[0]["assignments"][0]["value"]
    assert "REFPERIODOVERDRAWN-60>=DPD_MAX" in facility_branch_value
    assert "'SMA_0'" in facility_branch_value and "'SMA_1'" in facility_branch_value


def test_case_expression_single_when_without_else_is_not_a_ladder():
    """A lone WHEN/THEN with no ELSE and no other branch is a conditional
    default, not a multi-way decision ladder - must not be fabricated into
    one."""
    source = "A.FLAG = CASE WHEN A.STATUS = 'X' THEN 1 END"
    assert extract_case_assignment_decision_chains(source) == []


def test_merge_decision_chains_keeps_deterministic_first_and_drops_exact_duplicates():
    deterministic = [
        {
            "chain_type": "CASE_EXPRESSION",
            "subject": "dpd",
            "branches": [
                {"branch_condition": "DPD > 90", "assignments": [{"field": "SMA_CLASS", "value": "'SMA_2'"}]},
                {"branch_condition": "ELSE", "assignments": [{"field": "SMA_CLASS", "value": "NULL"}]},
            ],
        }
    ]
    llm_duplicate = [
        {
            "chain_type": "CASE_EXPRESSION",
            "subject": "dpd",
            "branches": [
                {"branch_condition": "dpd > 90", "assignments": [{"field": "sma_class", "value": "SMA_2"}]},
                {"branch_condition": "else", "assignments": [{"field": "sma_class", "value": "null"}]},
            ],
        },
        {
            # Distinct chain, different field entirely - must be kept.
            "chain_type": "IF_ELSIF_ELSE",
            "subject": "flg",
            "branches": [
                {"branch_condition": "X = 1", "assignments": [{"field": "OTHER_FLAG", "value": "'Y'"}]},
                {"branch_condition": "ELSE", "assignments": [{"field": "OTHER_FLAG", "value": "'N'"}]},
            ],
        },
    ]
    merged = merge_decision_chains(deterministic, llm_duplicate)
    assert len(merged) == 2
    assert merged[0] is deterministic[0]
    assert merged[1]["subject"] == "flg"


def test_procedural_ladder_still_wins_when_present_alongside_case_expressions():
    """Sanity check: adding the CASE-expression path must not regress the
    existing PL/SQL IF/ELSIF/ELSE ladder extraction it sits alongside."""
    source = """
    IF v_overdue_days <= 90 THEN
      v_classification := 'STANDARD';
    ELSIF v_overdue_days BETWEEN 91 AND 365 THEN
      v_classification := 'SUBSTANDARD';
    ELSE
      v_classification := 'LOSS';
    END IF;
    """
    case_chains = extract_case_assignment_decision_chains(source)
    ladder_chains = extract_procedural_decision_chains(source)
    assert case_chains == []
    assert len(ladder_chains) == 1