"""
Regression tests for glossary generation.

These tests exercise the glossary table directly so we can verify the
output contract stays limited to active technical evidence and the
two-column markdown table.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.ingestion import IngestionResult, Parameter
from agents.report_formatter import ReportFormatterAgent


def _make_ingestion() -> IngestionResult:
    return IngestionResult(
        object_name="SMA_MARKING_12122023",
        object_type="PROCEDURE",
        parameters=[Parameter(name="@TIMEKEY", direction="IN", datatype="INT")],
        raw_code="",
        chunks=[],
        dialect="tsql",
        parameter_parse_status="parameterized",
    )


def _make_merged_extraction():
    return {
        "table_operations": [
            {
                "table": "SYSDAYMATRIX",
                "operation": "READ",
                "target_columns": ["DATE"],
                "source_columns": ["DATE"],
                "where_predicate": "TIMEKEY = @TIMEKEY",
                "join_predicates": [],
                "exists_predicates": [],
                "having_predicate": None,
                "constants": ["@TIMEKEY"],
                "source_statement_text": "SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY = @TIMEKEY",
                "active_status": "ACTIVE",
                "source_parse_error": "",
            },
            {
                "table": "#DPD",
                "operation": "READ",
                "target_columns": ["DPD_Overdrawn", "DPD_Overdue"],
                "source_columns": ["DPD_Overdrawn", "DPD_Overdue"],
                "where_predicate": "DPD_Overdrawn > 30 OR DPD_Overdue > 0",
                "join_predicates": [],
                "exists_predicates": [],
                "having_predicate": None,
                "constants": ["30", "0"],
                "source_statement_text": "SELECT DPD_Overdrawn, DPD_Overdue FROM #DPD WHERE DPD_Overdrawn > 30 OR DPD_Overdue > 0",
                "active_status": "ACTIVE",
                "source_parse_error": "",
            },
            {
                "table": "#DPD",
                "operation": "UPDATE",
                "target_columns": [
                    "DPD_IntService",
                    "DPD_NoCredit",
                    "DPD_Renewal",
                    "DPD_StockStmt",
                ],
                "source_columns": [],
                "where_predicate": (
                    "ISNULL(DPD_IntService,0) < 0 OR ISNULL(DPD_NoCredit,0) < 0 OR "
                    "ISNULL(DPD_Renewal,0) < 0 OR ISNULL(DPD_StockStmt,0) < 0"
                ),
                "join_predicates": [],
                "exists_predicates": [],
                "having_predicate": None,
                "constants": ["0"],
                "source_statement_text": (
                    "UPDATE A SET DPD_IntService = 0, DPD_NoCredit = 0, "
                    "DPD_Renewal = 0, DPD_StockStmt = 0 FROM #DPD A "
                    "WHERE ISNULL(DPD_IntService,0) < 0 OR ISNULL(DPD_NoCredit,0) < 0 OR "
                    "ISNULL(DPD_Renewal,0) < 0 OR ISNULL(DPD_StockStmt,0) < 0"
                ),
                "active_status": "ACTIVE",
                "source_parse_error": "",
            },
            {
                "table": "PRO.ACCOUNTCAL",
                "operation": "UPDATE",
                "target_columns": ["FLGSMA"],
                "source_columns": [],
                "where_predicate": "ISNULL(B.FLGPROCESSING,'N') = 'N' AND EXISTS (SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY M WHERE M.CustomerAcID = A.CustomerAcID)",
                "join_predicates": [
                    {
                        "table": "PRO.CUSTOMERCAL",
                        "table_alias": "B",
                        "join_type": "INNER JOIN",
                        "predicate": "A.CustomerEntityID = B.CustomerEntityID",
                    }
                ],
                "exists_predicates": [
                    {
                        "kind": "EXISTS",
                        "predicate": "SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY M WHERE M.CustomerAcID = A.CustomerAcID",
                        "subquery_tables": ["PRO.SMA_MOVEMENT_HISTORY"],
                    }
                ],
                "having_predicate": None,
                "constants": ["'Y'", "'N'"],
                "source_statement_text": (
                    "UPDATE A SET FLGSMA = 'Y' FROM PRO.ACCOUNTCAL A "
                    "INNER JOIN PRO.CUSTOMERCAL B ON A.CustomerEntityID = B.CustomerEntityID "
                    "WHERE ISNULL(B.FLGPROCESSING,'N') = 'N' AND EXISTS (SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY M WHERE M.CustomerAcID = A.CustomerAcID)"
                ),
                "active_status": "ACTIVE",
                "source_parse_error": "",
            },
            {
                "table": "#DPD",
                "operation": "UPDATE",
                "target_columns": ["DPD_MAX"],
                "source_columns": [],
                "where_predicate": "",
                "join_predicates": [],
                "exists_predicates": [],
                "having_predicate": None,
                "constants": [],
                "source_statement_text": (
                    "UPDATE #DPD SET DPD_MAX = CASE WHEN DPD_Overdrawn > DPD_Overdue "
                    "THEN DPD_Overdrawn ELSE DPD_Overdue END"
                ),
                "active_status": "ACTIVE",
                "source_parse_error": "",
            },
            {
                "table": "PRO.ACLRUNNINGPROCESSSTATUS",
                "operation": "UPDATE",
                "target_columns": ["COMPLETED", "ERRORDATE", "ERRORDESCRIPTION", "COUNT"],
                "source_columns": [],
                "where_predicate": "RUNNINGPROCESSNAME = 'SMA_MARKING'",
                "join_predicates": [],
                "exists_predicates": [],
                "having_predicate": None,
                "constants": ["'Y'", "NULL", "'SMA_MARKING'", "0"],
                "source_statement_text": (
                    "UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', "
                    "ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT,0) + 1 "
                    "WHERE RUNNINGPROCESSNAME = 'SMA_MARKING'"
                ),
                "active_status": "ACTIVE",
                "source_parse_error": "",
            },
        ],
        "conditions": [],
        "calculations": [
            {
                "metric": "Legacy DPD_IntService calc",
                "formula": "commented out calculation",
                "active_status": "INACTIVE",
                "source_parse_error": "commented out",
            }
        ],
        "tables_read": [],
        "tables_written": [],
    }


def test_glossary_is_table_only_and_uses_active_technical_ir():
    formatter = ReportFormatterAgent()
    report = formatter._glossary_table(_make_ingestion(), _make_merged_extraction())

    assert report.startswith("| Term | Business Meaning |")
    assert "##" not in report
    assert "confidence" not in report.lower()
    assert "provenance" not in report.lower()
    assert "Legacy DPD_IntService calc" not in report
    assert "@TIMEKEY" in report
    assert "TIMEKEY = @TIMEKEY" in report
    assert "DPD_MAX" in report
    assert "CASE WHEN DPD_Overdrawn > DPD_Overdue THEN DPD_Overdrawn ELSE DPD_Overdue END" in report
    assert "DPD_IntService" in report
    assert "DPD_Overdrawn > 30 OR DPD_Overdue > 0" in report
    assert "'SMA_MARKING'" in report
    assert "RUNNINGPROCESSNAME" in report


def test_glossary_consolidates_multiple_active_usages():
    formatter = ReportFormatterAgent()
    report = formatter._glossary_table(_make_ingestion(), _make_merged_extraction())

    assert "DPD_Overdrawn" in report
    assert "Source field read in active SQL" in report
    assert "Referenced in active predicate(s)" in report or "Used in active predicate(s)" in report


def test_glossary_marks_constants_and_status_fields_from_active_usage():
    formatter = ReportFormatterAgent()
    report = formatter._glossary_table(_make_ingestion(), _make_merged_extraction())

    assert "| 0 |" in report
    assert "Literal reset value used in active update on #DPD for DPD_IntService, DPD_NoCredit, DPD_Renewal, DPD_StockStmt." in report
    assert "| 30 |" in report
    assert "Threshold or filter literal used in active predicate `DPD_Overdrawn > 30 OR DPD_Overdue > 0`." in report
    assert "| 'Y' |" in report
    assert "Flag literal used in active update on PRO.ACCOUNTCAL for FLGSMA." in report
    assert "| 'SMA_MARKING' |" in report
    assert "Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS." in report
