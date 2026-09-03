from src.validation.semantic_validation import (
    extract_procedural_decision_chains,
  extract_nested_decision_chains,
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
