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
    assert "**Condition:**" in report
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
    assert "### Decision Logic" not in report
    assert "**Then:**" in report
    assert report.count("Assigns status the value OPEN.") == 1


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
