from __future__ import annotations

from evaluation.evaluator import _compare_business_rules


def _rule(condition, action, output_field="", **extra):
    value = {"condition": condition, "action": action, "output_field": output_field}
    value.update(extra)
    return value


def _status(expected, actual, aliases=None):
    return _compare_business_rules(expected, actual, aliases or {})


def test_wording_and_natural_language_condition_are_equivalent():
    result = _status(
        [_rule("overdue_days > 1095", "asset_classification = 'NPA'")],
        [_rule("overdue days exceeds 1095 days", "Classify the asset as NPA")],
    )
    assert result["semantic_status"] == "PASS"


def test_equivalent_outcome_wording_passes_but_wrong_literal_fails():
    expected = [_rule("status = 'READY'", "status = 'READY'")]
    assert _status(expected, [_rule("status = 'READY'", "Set the status to READY")])["semantic_status"] == "PASS"
    wrong = _status(expected, [_rule("status = 'READY'", "Set the status to HOLD")])
    assert wrong["semantic_status"] == "FAIL"
    assert any(item["type"] == "WRONG_OUTCOME" for item in wrong["classifications"])


def test_operator_and_literal_changes_are_not_equivalent():
    operator = _status([_rule("overdue_days > 90", "set NPA")], [_rule("overdue_days >= 90", "set NPA")])
    assert any(item["type"] == "WRONG_OPERATOR" for item in operator["classifications"])
    literal = _status([_rule("overdue_days > 90", "set NPA")], [_rule("overdue_days > 91", "set NPA")])
    assert any(item["type"] == "WRONG_LITERAL" for item in literal["classifications"])


def test_null_and_not_null_are_not_equivalent():
    result = _status([_rule("customer_id IS NULL", "flag review")], [_rule("customer_id IS NOT NULL", "flag review")])
    assert any(item["type"] == "WRONG_NULL_SEMANTICS" for item in result["classifications"])


def test_date_boundary_change_is_not_equivalent():
    result = _status(
        [_rule("due_date < '2024-01-01'", "mark overdue")],
        [_rule("due_date < '2024-02-01'", "mark overdue")],
    )
    assert any(item["type"] == "WRONG_DATE_SEMANTICS" for item in result["classifications"])


def test_proven_intermediate_variable_alias_passes():
    result = _status(
        [_rule("score >= 90", "set STANDARD", "v_classification")],
        [_rule("score >= 90", "classify the account as STANDARD", "asset_classification")],
        {"V_CLASSIFICATION": "ASSET_CLASSIFICATION"},
    )
    assert result["semantic_status"] == "PASS"


def test_unknown_field_mapping_fails_instead_of_being_guessed():
    result = _status(
        [_rule("score >= 90", "set STANDARD", "v_classification")],
        [_rule("score >= 90", "classify the account as STANDARD", "unrelated_status")],
    )
    assert result["semantic_status"] == "FAIL"
    assert any(item["type"] == "WRONG_FIELD" for item in result["classifications"])


def test_else_fallback_and_reordered_disjoint_branches_pass():
    expected = [
        _rule("score >= 90", "set A"),
        _rule("ELSE", "set B"),
    ]
    actual = [
        _rule("else", "B"),
        _rule("score >= 90", "A"),
    ]
    assert _status(expected, actual)["semantic_status"] == "PASS"


def test_missing_branch_and_extra_unsupported_rule_fail():
    missing = _status(
        [_rule("score >= 90", "set A"), _rule("ELSE", "set B")],
        [_rule("score >= 90", "set A")],
    )
    assert any(item["type"] == "MISSING_BRANCH" for item in missing["classifications"])
    extra = _status(
        [_rule("score >= 90", "set A")],
        [_rule("score >= 90", "set A"), _rule("score >= 90", "write an audit log")],
    )
    assert any(item["type"] == "EXTRA_UNSUPPORTED_RULE" for item in extra["classifications"])


def test_complex_and_dynamic_claims_remain_review_required():
    complex_result = _status(
        [_rule("A = 1 AND (B = 2 OR C = 3)", "set READY")],
        [_rule("complex predicate", "set READY")],
    )
    assert complex_result["semantic_status"] == "REVIEW_REQUIRED"
    dynamic_result = _status(
        [_rule("dynamic SQL is assembled at runtime", "flag for manual review")],
        [_rule("account_id = @id", "update the dynamically selected table")],
    )
    assert dynamic_result["semantic_status"] == "REVIEW_REQUIRED"
