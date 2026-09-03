from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.evaluator import _derive_important_fields, _filter_supporting_reads, _reportable_operations, _rule_signature_candidates
from evaluation.metrics import normalize_text
from src.extraction.logic_extractor import ChunkExtraction
from src.extraction.logic_extractor import LogicExtractionAgent
from src.ingestion.ingestion import CodeChunk, IngestionResult, Parameter
from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent


def _ingestion(object_type: str = "PROCEDURE") -> IngestionResult:
    return IngestionResult(
        object_name="demo_object",
        object_type=object_type,
        parameters=[
            Parameter(name="@AccountId", direction="IN", datatype="NUMBER"),
            Parameter(name="@TableName", direction="IN", datatype="VARCHAR2"),
        ],
        raw_code="select 1",
        chunks=[CodeChunk(chunk_id="chunk_1", kind="main_body", text="select 1")],
        dialect="ORACLE",
        concrete_dialect="oracle",
        fallback_dialect="oracle",
        source_hash="hash",
    )


def test_agents_default_to_low_temperature():
    assert LogicExtractionAgent(client=object(), model="demo").temperature == 0.1
    assert RuleSynthesizerAgent(client=object(), model="demo").temperature == 0.1


def test_view_filter_rule_stays_a_filter():
    raw_rules = [
        {
            "condition": "la.asset_classification != 'STANDARD'",
            "action": "Includes only non-standard accounts",
            "fields_affected": [],
            "source_evidence": ["la.asset_classification != 'STANDARD'"],
            "business_meaning": "The view only shows non-standard accounts.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "asset_classification != STANDARD"
    assert normalized[0]["action"] == "Show only non-standard accounts"


def test_latest_classification_date_rule_canonicalizes_to_most_recent_row():
    raw_rules = [
        {
            "condition": "np.classification_date = (select max(classification_date) from npa_provision where account_id = la.account_id)",
            "action": "Includes only the provision record with the latest classification date for each account.",
            "fields_affected": [],
            "source_evidence": ["np.classification_date = (select max(classification_date) from npa_provision where account_id = la.account_id)"],
            "business_meaning": "Keeps the most recent provision row per account.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "latest classification_date per account"
    assert normalized[0]["action"] == "Keep only most recent provision row"


def test_latest_calculated_date_rule_uses_source_context():
    raw_rules = [
        {
            "condition": "latest classification_date per account",
            "action": "Summarize latest provision values",
            "output_field": "",
            "fields_affected": [],
            "source_evidence": ["np.calculated_date = (select max(calculated_date) from npa_provision where account_id = la.account_id)"],
            "business_meaning": "Summarize the latest provision values for each account.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules,
        source_text="calculated_date",
        technical_context={"tables_read": [{"table": "NPA_PROVISION", "columns": ["calculated_date"]}]},
    )
    assert normalized[0]["condition"] == "latest calculated_date per account"
    assert normalized[0]["action"] == "Summarize latest provision values"


def test_oracle_overdue_ladder_canonicalizes_branch_values():
    raw_rules = [
        {
            "condition": "v_overdue_days BETWEEN 91 AND 365",
            "action": "Set STANDARD classification",
            "output_field": "asset_classification",
            "fields_affected": ["asset_classification"],
            "source_evidence": ["v_overdue_days BETWEEN 91 AND 365", "v_classification := 'SUBSTANDARD'"],
            "business_meaning": "Assign the account's classification based on overdue days.",
        },
        {
            "condition": "v_overdue_days BETWEEN 91 AND 365",
            "action": "15",
            "output_field": "provision_pct",
            "fields_affected": ["provision_pct"],
            "source_evidence": ["v_overdue_days BETWEEN 91 AND 365", "v_provision_pct := 15"],
            "business_meaning": "Assign the provisioning percentage based on overdue days.",
        },
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "v_overdue_days BETWEEN 91 AND 365"
    assert normalized[0]["action"] == "Set SUBSTANDARD classification"
    assert normalized[0]["output_field"] == "v_classification"
    assert len(normalized) == 1


def test_decision_chain_assignments_are_normalized_and_drive_exact_rules():
    chain = {
        "subject": "v_overdue_days",
        "branches": [
            {
                "branch_condition": "v_overdue_days <= 90",
                "assignments": [
                    {"field": "v_classification", "value": "STANDARD"},
                    {"field": "v_provision_pct", "value": "0.40"},
                ],
            },
            {
                "branch_condition": "v_overdue_days BETWEEN 91 AND 365",
                "assignments": [
                    {"field": "v_classification", "value": "SUBSTANDARD"},
                    {"field": "v_provision_pct", "value": "15"},
                ],
            },
            {
                "branch_condition": "v_overdue_days BETWEEN 366 AND 1095",
                "assignments": [
                    {"field": "v_classification", "value": "DOUBTFUL1"},
                    {"field": "v_provision_pct", "value": "25"},
                ],
            },
            {
                "branch_condition": "ELSE",
                "assignments": [
                    {"field": "v_classification", "value": "LOSS"},
                    {"field": "v_provision_pct", "value": "100"},
                ],
            },
        ],
    }
    normalized = RuleSynthesizerAgent._normalize_business_rules(
        [
            {
                "rule_name": "Wrong duplicate",
                "fields_affected": ["v_classification"],
                "eligibility": ["v_overdue_days <= 90", "v_overdue_days > 1095"],
            },
            {
                "rule_name": "Another wrong duplicate",
                "fields_affected": ["v_classification"],
            },
        ]
    )
    rules = RuleSynthesizerAgent._apply_authoritative_decision_chains(
        normalized,
        {"decision_chains": [chain]},
    )

    classification_rules = [rule for rule in rules if rule["output_field"] == "v_classification"]
    assert len(classification_rules) == 4
    assert [rule["action"] for rule in classification_rules] == [
        "Assigns v_classification the value STANDARD.",
        "Assigns v_classification the value SUBSTANDARD.",
        "Assigns v_classification the value DOUBTFUL1.",
        "Assigns v_classification the value LOSS.",
    ]
    assert not any(rule["output_field"] == "v_provision_pct" for rule in rules)


def test_authoritative_chain_removes_rules_identified_only_by_output_field():
    chain = {
        "subject": "input_days",
        "branches": [
            {"branch_condition": "input_days <= 10", "assignments": [{"field": "status", "value": "A"}]},
            {"branch_condition": "ELSE", "assignments": [{"field": "status", "value": "B"}]},
        ],
    }
    rules = RuleSynthesizerAgent._apply_authoritative_decision_chains(
        [{"output_field": "status", "action": "Wrong stale rule", "fields_affected": []}],
        {"decision_chains": [chain]},
    )
    assert len(rules) == 2
    assert [rule["output_field"] for rule in rules] == ["status", "status"]
    assert [rule["action"] for rule in rules] == [
        "Assigns status the value A.",
        "Assigns status the value B.",
    ]

    generic_rules = RuleSynthesizerAgent._apply_authoritative_decision_chains(
        [],
        {
            "decision_chains": [
                {
                    "subject": "input_code",
                    "branches": [
                        {"branch_condition": "input_code = 1", "assignments": [{"field": "status_code", "value": "OPEN"}]},
                        {"branch_condition": "ELSE", "assignments": [{"field": "status_code", "value": "CLOSED"}]},
                    ],
                }
            ]
        },
    )
    assert [rule["action"] for rule in generic_rules] == [
        "Assigns status_code the value OPEN.",
        "Assigns status_code the value CLOSED.",
    ]


def test_decision_table_does_not_render_alternative_branches_as_all_eligibility():
    report = ReportFormatterAgent()._business_rules_section(
        [
            {
                "rule_name": "Determine classification",
                "output_field": "v_classification",
                "business_meaning": "Determines the classification from decision bands.",
                "eligibility": [
                    "Overdue days are between 366 and 1095",
                    "Overdue days are more than 1095",
                ],
                "decision_logic_rows": [
                    {"condition": "v_overdue_days BETWEEN 366 AND 1095", "outcome": "DOUBTFUL1"},
                    {"condition": "ELSE", "outcome": "LOSS"},
                ],
            }
        ]
    )
    assert "**Eligibility" not in report
    assert "DOUBTFUL1" in report
    assert "LOSS" in report


def test_single_condition_rule_renders_condition_outcome_table():
    report = ReportFormatterAgent()._business_rules_section(
        [
            {
                "rule_name": "Assign status",
                "output_field": "status",
                "condition": "input_code = 1",
                "action": "Assigns status the value OPEN.",
                "business_meaning": "Assigns the status for the matching input code.",
                "eligibility": [],
            }
        ]
    )
    assert "### Decision Logic" in report
    assert "| input_code equals 1 | Assigns status the value OPEN. |" in report


def test_oracle_nested_doubtful_branch_collapses_with_context():
    raw_rules = [
        {
            "condition": "v_overdue_days BETWEEN 366 AND 1095",
            "action": "Set DOUBTFUL1 classification",
            "output_field": "v_classification",
            "fields_affected": ["v_classification"],
            "source_evidence": ["v_overdue_days BETWEEN 366 AND 1095"],
            "business_meaning": "Assign the account's classification based on overdue days.",
        },
        {
            "condition": "v_overdue_days BETWEEN 366 AND 1095",
            "action": "Set DOUBTFUL2 classification",
            "output_field": "v_classification",
            "fields_affected": ["v_classification"],
            "source_evidence": ["v_overdue_days BETWEEN 366 AND 1095"],
            "business_meaning": "Assign the account's classification based on overdue days.",
        },
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules,
        source_text="v_doubtful_since",
        technical_context={"conditions": [{"condition": "v_doubtful_since"}]},
    )
    assert len(normalized) == 1
    assert normalized[0]["action"] == "Set DOUBTFUL1 or DOUBTFUL2 based on doubtful_since"


def test_oracle_provision_ladder_merges_supporting_percentage():
    raw_rules = [
        {
            "condition": "v_overdue_days <= 90",
            "action": "Set STANDARD classification",
            "output_field": "v_classification",
            "fields_affected": ["v_classification"],
            "source_evidence": ["v_overdue_days <= 90", "v_provision_pct := 0.40"],
            "business_meaning": "Assign the account's classification based on overdue days.",
        },
        {
            "condition": "v_overdue_days <= 90",
            "action": "0.40",
            "output_field": "v_provision_pct",
            "fields_affected": ["v_provision_pct"],
            "source_evidence": ["v_overdue_days <= 90", "v_provision_pct := 0.40"],
            "business_meaning": "Assign the provisioning percentage based on overdue days.",
        },
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules,
        source_text="v_provision_pct",
        technical_context={"conditions": [{"condition": "v_overdue_days <= 90"}]},
    )
    assert len(normalized) == 1
    assert normalized[0]["action"] == "Set STANDARD classification and 0.40 provision pct"


def test_oracle_bucket_ladder_canonicalization_is_stable():
    raw_rules = [
        {
            "condition": "rec.overdue_days <= 30",
            "action": "Set standard classification",
            "output_field": "ageing_bucket",
            "fields_affected": ["ageing_bucket"],
            "source_evidence": ["rec.overdue_days <= 30", "v_ageing_bucket := 'BUCKET_0_30'"],
            "business_meaning": "Assign the ageing bucket based on overdue days.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "<= 30 days"
    assert normalized[0]["action"] == "Assign BUCKET_0_30"


def test_bucket_normalization_requires_explicit_bucket_evidence():
    raw_rules = [
        {
            "condition": "la.asset_classification != 'STANDARD'",
            "action": "Show only non-standard accounts",
            "output_field": "asset_classification",
            "fields_affected": ["asset_classification"],
            "source_evidence": ["la.asset_classification != 'STANDARD'"],
            "business_meaning": "The view only shows non-standard accounts.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "asset_classification != STANDARD"
    assert normalized[0]["action"] == "Show only non-standard accounts"


def test_dynamic_sql_rule_is_manual_review_only():
    raw_rules = [
        {
            "condition": "Target table and columns are determined dynamically at runtime.",
            "action": "Flag for manual review instead of claiming a concrete table.",
            "fields_affected": [],
            "source_evidence": ["dynamic SQL assembled at runtime"],
            "business_meaning": "Dynamic SQL is used.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "dynamic sql is assembled at runtime"
    assert normalized[0]["action"] == "Flag for manual review instead of claiming a concrete table"


def test_merge_rule_canonicalization_is_stable():
    raw_rules = [
        {
            "condition": "tgt.account_id = src.account_id",
            "action": "Updates the account's provisioning amount and the last updated timestamp.",
            "fields_affected": ["provision_amount", "updated_at"],
            "source_evidence": ["WHEN MATCHED THEN UPDATE"],
            "business_meaning": "Updates the existing provision row.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "source row matches target"
    assert normalized[0]["action"] == "Update existing provision row"


def test_try_catch_rule_canonicalization_is_stable():
    raw_rules = [
        {
            "condition": "The account matches the provided account identifier.",
            "action": "Update account status and audit the change.",
            "fields_affected": ["Status", "UpdatedAt"],
            "source_evidence": ["BEGIN TRY", "BEGIN CATCH", "status update"],
            "business_meaning": "Updates status when the request succeeds.",
        },
        {
            "condition": "An error occurs during the status update.",
            "action": "Log error message.",
            "fields_affected": ["ErrorMessage"],
            "source_evidence": ["BEGIN CATCH", "ERROR_MESSAGE()"],
            "business_meaning": "Logs the failure.",
        },
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "TRY block succeeds"
    assert normalized[0]["action"] == "Update account status and audit the change"
    assert normalized[1]["condition"] == "CATCH block"
    assert normalized[1]["action"] == "Log error message"


def test_overdue_status_rule_canonicalizes_to_mark_overdue():
    raw_rules = [
        {
            "condition": "DpdDays > 90",
            "action": "Update account status and audit the change.",
            "fields_affected": ["Status"],
            "source_evidence": ["DpdDays > 90", "Status", "Audit"],
            "business_meaning": "Marks the account overdue and records the status change.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["action"] == "Mark accounts overdue and audit the status change"


def test_try_catch_wrapper_with_risk_band_ladder_stays_on_the_ladder():
    raw_rules = [
        {
            "condition": "TRY block succeeds",
            "action": "Set low risk band",
            "output_field": "RiskBand",
            "fields_affected": ["RiskBand"],
            "decision_logic_rows": [
                {"condition": "DpdDays <= 30", "outcome": "LOW"},
                {"condition": "DpdDays <= 90", "outcome": "MEDIUM"},
                {"condition": "ELSE", "outcome": "HIGH"},
            ],
            "source_evidence": ["DpdDays <= 30", "DpdDays <= 90", "ELSE"],
            "business_meaning": "Assigns a risk band based on days overdue.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules,
        source_text="DpdDays <= 30 DpdDays <= 90",
        technical_context={"decision_chains": [{"subject": "DpdDays", "branches": []}]},
    )
    assert normalized[0]["condition"] == "DpdDays <= 30"
    assert normalized[0]["action"] == "Set LOW risk band"


def test_update_status_try_catch_stays_wrapper_based():
    raw_rules = [
        {
            "condition": "TRY block succeeds",
            "action": "Update account status and audit the change",
            "fields_affected": ["Status", "UpdatedAt"],
            "source_evidence": ["BEGIN TRY", "UPDATE dbo.Account", "INSERT dbo.AccountAudit"],
            "business_meaning": "Update the account and record the audit trail.",
        },
        {
            "condition": "CATCH block",
            "action": "Log error message",
            "fields_affected": ["ErrorMessage"],
            "source_evidence": ["BEGIN CATCH", "ERROR_MESSAGE()"],
            "business_meaning": "Log the failure.",
        },
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules,
        source_text="BEGIN TRY BEGIN CATCH @NewStatus AccountAudit ErrorLog",
        technical_context={"exception_handling": ["BEGIN TRY", "BEGIN CATCH"]},
    )
    assert normalized[0]["condition"] == "TRY block succeeds"
    assert normalized[0]["action"] == "Update account status and audit the change"
    assert normalized[1]["condition"] == "CATCH block"


def test_merge_branch_canonicalization_distinguishes_insert_and_update():
    raw_rules = [
        {
            "condition": "source row matches target",
            "action": "Update existing provision row",
            "fields_affected": ["provision_amount"],
            "source_evidence": ["WHEN MATCHED THEN UPDATE"],
            "business_meaning": "Updates an existing provision row.",
        },
        {
            "condition": "source row matches target",
            "action": "Update existing provision row",
            "fields_affected": ["provision_amount"],
            "source_evidence": ["WHEN NOT MATCHED THEN INSERT"],
            "business_meaning": "Inserts a new provision row.",
        },
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "source row matches target"
    assert normalized[0]["action"] == "Update existing provision row"
    assert normalized[1]["condition"] == "source row does not match target"
    assert normalized[1]["action"] == "Insert new provision row"


def test_rule_signature_candidates_recognize_ladder_else_equivalence():
    rule = {
        "condition": "DpdDays > 90",
        "action": "Set high risk band",
        "output_field": "RiskBand",
        "decision_logic_rows": [
            {"condition": "DpdDays <= 30", "outcome": "LOW"},
            {"condition": "DpdDays <= 90", "outcome": "MEDIUM"},
            {"condition": "DpdDays > 90", "outcome": "HIGH"},
        ],
        "rule_name": "Risk band ladder",
        "business_meaning": "Assigns a risk band from days overdue.",
        "source_evidence": ["DpdDays ladder"],
    }

    candidates = {
        tuple(normalize_text(item) for item in candidate)
        for candidate in _rule_signature_candidates(rule)
    }
    assert ("else", "set high risk band", "riskband") in candidates


def test_merge_target_read_is_preserved_but_not_reported_twice():
    ops = [
        {"operation": "MERGE", "table": "dbo.NPA_Provision", "statement_id": "s1"},
        {"operation": "READ", "table": "dbo.Staging_Provisioning", "statement_id": "s1"},
        {"operation": "READ", "table": "dbo.NPA_Provision", "statement_id": "s1"},
        {"operation": "READ", "table": "dual", "statement_id": "s2"},
    ]

    reads = _filter_supporting_reads(ops, [op for op in ops if op["operation"] == "READ"], keep_merge_target=True)
    assert {row["table"] for row in reads} == {"dbo.Staging_Provisioning", "dbo.NPA_Provision"}

    reportable = _reportable_operations(ops)
    assert {row["table"] for row in reportable if row["operation"] == "READ"} == {"dbo.Staging_Provisioning"}


def test_try_catch_error_logging_canonicalizes_to_catch():
    raw_rules = [
        {
            "condition": "TRY block succeeds",
            "action": "Log error message",
            "fields_affected": ["ErrorMessage"],
            "source_evidence": ["BEGIN CATCH", "ERROR_MESSAGE()"],
            "business_meaning": "Logs the failure.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(raw_rules)
    assert normalized[0]["condition"] == "CATCH block"
    assert normalized[0]["action"] == "Log error message"


def test_important_fields_are_grounded_and_stable():
    ingestion = _ingestion()
    table_rows = [
        {
            "operation": "READ",
            "target_columns": [
                "account_id",
                "customer_id",
                "asset_classification",
                "provision_amount",
                "branch_code",
                "account_count",
                "total_outstanding",
                "total_provision",
            ],
            "columns": [
                "account_id",
                "customer_id",
                "asset_classification",
                "provision_amount",
                "branch_code",
                "account_count",
                "total_outstanding",
                "total_provision",
            ],
            "source_columns": ["account_id", "customer_id", "branch_code"],
            "assigned_values": [],
        },
        {
            "operation": "UPDATE",
            "target_columns": ["updated_at", "created_at"],
            "columns": ["updated_at", "created_at"],
            "assigned_values": [
                {"column": "updated_at", "expression": "GETDATE()"},
                {"column": "created_at", "expression": "GETDATE()"},
            ],
        },
    ]
    rules = [
        {
            "rule_name": "Process counts",
            "business_meaning": "Keeps track of the processed count.",
            "condition": "processed_count > 0",
            "action": "Update the processed count.",
            "output_field": "v_processed_count",
            "fields_affected": ["v_processed_count"],
            "source_evidence": ["v_processed_count"],
            "decision_logic_rows": [],
        }
    ]

    fields = _derive_important_fields(ingestion, table_rows, rules)
    for expected in [
        "@AccountId",
        "@TableName",
        "account_id",
        "customer_id",
        "asset_classification",
        "provision_amount",
        "branch_code",
        "account_count",
        "total_outstanding",
        "total_provision",
        "updated_at",
        "created_at",
        "v_processed_count",
    ]:
        assert expected in fields
    for unexpected in ["and", "between", "from", "select", "update", "merge"]:
        assert unexpected not in fields


def test_reportable_operations_hide_supporting_reads_and_locks():
    ops = [
        {"operation": "READ", "table": "dbo.Account", "statement_id": "s1"},
        {"operation": "UPDATE", "table": "dbo.Account", "statement_id": "s1"},
        {"operation": "LOCK", "table": "dbo.Account", "statement_id": "s1"},
        {"operation": "READ", "table": "dbo.Other", "statement_id": "s2"},
    ]

    reportable = _reportable_operations(ops)
    assert reportable == [
        {"operation": "UPDATE", "table": "dbo.Account", "statement_id": "s1"},
        {"operation": "READ", "table": "dbo.Other", "statement_id": "s2"},
    ]


def test_classification_ladder_backfills_missing_branches_from_context():
    raw_rules = [
        {
            "condition": "v_overdue_days BETWEEN 91 AND 365",
            "action": "Set SUBSTANDARD classification",
            "output_field": "v_classification",
            "fields_affected": ["v_classification"],
            "source_evidence": ["v_overdue_days BETWEEN 91 AND 365"],
            "business_meaning": "Classify the account by overdue days.",
        }
    ]

    normalized = RuleSynthesizerAgent._normalize_business_rules(
        raw_rules,
        source_text="v_provision_pct := 15; v_classification := 'LOSS';",
        technical_context={
            "conditions": [
                {"condition": "v_overdue_days <= 90", "true_branch": "v_classification := 'STANDARD'; v_provision_pct := 0.40;"},
                {"condition": "v_overdue_days BETWEEN 91 AND 365", "true_branch": "v_classification := 'SUBSTANDARD'; v_provision_pct := 15;"},
                {
                    "condition": "v_overdue_days BETWEEN 366 AND 1095",
                    "true_branch": "IF v_doubtful_since <= 365 THEN v_classification := 'DOUBTFUL1'; ELSE v_classification := 'DOUBTFUL2'; END IF;",
                    "false_branch": "ELSE",
                },
                {
                    "condition": "v_doubtful_since > 1095",
                    "true_branch": "v_classification := 'LOSS';",
                    "false_branch": "v_classification := 'DOUBTFUL3';",
                },
            ],
        },
    )
    conditions = {rule["condition"] for rule in normalized}
    assert "v_overdue_days <= 90" in conditions
    assert "91-365 days" in conditions
    assert "v_overdue_days > 1095" in conditions or "ELSE" in conditions


def test_view_and_merge_rules_backfill_from_context():
    normalized = RuleSynthesizerAgent._normalize_business_rules(
        [
            {
                "condition": "latest calculated_date per account",
                "action": "Summarize latest provision values",
                "output_field": "",
                "fields_affected": [],
                "source_evidence": ["latest calculated_date per account"],
                "business_meaning": "Summarize the latest provision values for each account.",
            },
            {
                "condition": "source row does not match target",
                "action": "Insert new provision row",
                "output_field": "",
                "fields_affected": [],
                "source_evidence": ["WHEN NOT MATCHED THEN INSERT"],
                "business_meaning": "Insert a new provision row.",
            },
        ],
        technical_context={
            "conditions": [
                {"condition": "la.asset_classification IS NOT NULL", "true_branch": "row included in view result"},
                {"condition": "np.calculated_date = (SELECT MAX(np2.calculated_date) FROM NPA_PROVISION np2 WHERE np2.account_id = la.account_id)", "true_branch": "row included in view result"},
            ],
            "tables_read": [
                {"table": "NPA_PROVISION", "filter_condition": "classification_date = (SELECT MAX(classification_date) FROM NPA_PROVISION WHERE account_id = la.account_id)"},
            ],
            "tables_written": [
                {"table": "dbo.NPA_Provision", "operation": "UPDATE", "trigger_condition": "WHEN MATCHED"},
                {"table": "dbo.NPA_Provision", "operation": "INSERT", "trigger_condition": "WHEN NOT MATCHED"},
            ],
        },
    )
    pairs = {(rule["condition"], rule["action"]) for rule in normalized}
    assert ("asset_classification IS NOT NULL", "Include only classified accounts") in pairs
    assert ("latest calculated_date per account", "Summarize latest provision values") in pairs
    assert ("source row matches target", "Update existing provision row") in pairs
    assert ("source row does not match target", "Insert new provision row") in pairs
