"""Regression tests for the diagnostic executable-construct ledger."""

from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import SynthesisResult
from src.validation.coverage_check import build_completeness_ledger
from tests.test_reconciliation import _make_ingestion, _rule


def _multi_statement_source():
    return """BEGIN TRY
  SELECT account_id FROM #staging_accounts;
  UPDATE ACCOUNT SET STATUS = 'A';
  DELETE FROM #staging_accounts;
  TRUNCATE TABLE #staging_work;
  EXEC(@dynamic_sql);
END TRY
BEGIN CATCH
  INSERT INTO ERROR_LOG VALUES (1);
END CATCH;
"""


def _multi_statement_extraction():
    return {
        "statement_provenance": [
            {
                "statement_id": "stmt_select",
                "statement_kind": "SELECT",
                "source_statement_text": "SELECT account_id FROM #staging_accounts",
                "source_line_start": 2,
                "source_line_end": 2,
                "source_chunk_id": "chunk_1",
                "parse_status": "parsed",
            },
            {
                "statement_id": "stmt_update",
                "statement_kind": "UPDATE",
                "source_statement_text": "UPDATE ACCOUNT SET STATUS = 'A'",
                "source_line_start": 3,
                "source_line_end": 3,
                "source_chunk_id": "chunk_1",
                "parse_status": "parsed",
            },
            {
                "statement_id": "stmt_delete",
                "statement_kind": "DELETE",
                "source_statement_text": "DELETE FROM #staging_accounts",
                "source_line_start": 4,
                "source_line_end": 4,
                "source_chunk_id": "chunk_1",
                "parse_status": "parsed",
            },
            {
                "statement_id": "stmt_truncate",
                "statement_kind": "TRUNCATE",
                "source_statement_text": "TRUNCATE TABLE #staging_work",
                "source_line_start": 5,
                "source_line_end": 5,
                "source_chunk_id": "chunk_1",
                "parse_status": "parsed",
            },
            {
                "statement_id": "stmt_dynamic",
                "statement_kind": "EXEC",
                "source_statement_text": "EXEC(@dynamic_sql)",
                "source_line_start": 6,
                "source_line_end": 6,
                "source_chunk_id": "chunk_1",
                "parse_status": "parse_failed",
            },
            {
                "statement_id": "stmt_error",
                "statement_kind": "INSERT",
                "source_statement_text": "INSERT INTO ERROR_LOG VALUES (1)",
                "source_line_start": 9,
                "source_line_end": 9,
                "source_chunk_id": "chunk_1",
                "parse_status": "unsupported",
            },
            {
                "statement_id": "stmt_failed",
                "statement_kind": "MERGE",
                "source_statement_text": "MERGE malformed_source",
                "source_line_start": 11,
                "source_line_end": 11,
                "source_chunk_id": "chunk_1",
                "parse_status": "parse_failed",
            },
        ],
        "table_operations": [
            {
                "operation": "READ",
                "table": "#staging_accounts",
                "statement_id": "stmt_select",
                "source_line_start": 2,
                "source_line_end": 2,
            },
            {
                "operation": "DELETE",
                "table": "#staging_accounts",
                "statement_id": "stmt_delete",
                "source_line_start": 4,
                "source_line_end": 4,
            },
            {
                "operation": "TRUNCATE",
                "table": "#staging_work",
                "statement_id": "stmt_truncate",
                "source_line_start": 5,
                "source_line_end": 5,
            },
        ],
    }


def _statuses(ledger):
    return {item["construct_type"]: item["status"] for item in ledger["items"]}


def test_ledger_covers_mixed_multi_statement_constructs_with_provenance():
    ledger = build_completeness_ledger(
        _multi_statement_source(),
        _multi_statement_extraction(),
        rules=[
            _rule(
                source_statement_ids=["stmt_update"],
                source_evidence=["UPDATE ACCOUNT SET STATUS = 'A'"],
                fields_affected=["STATUS"],
                action="STATUS = 'A'",
            )
        ],
    )

    statuses = _statuses(ledger)
    assert statuses["UPDATE"] == "covered_by_rule"
    assert statuses["SELECT"] == "uncovered"
    assert statuses["EXEC"] == "dynamic_unresolved"
    assert statuses["INSERT"] == "unsupported"
    assert statuses["READ_TEMP"] == "technical_only"
    assert statuses["DELETE_TEMP"] == "technical_only"
    assert statuses["TRUNCATE_TEMP"] == "technical_only"
    update = next(item for item in ledger["items"] if item["construct_type"] == "UPDATE")
    assert update["line_start"] == 3
    assert update["line_end"] == 3
    assert update["statement_id"] == "stmt_update"
    assert ledger["status_counts"]["uncovered"] >= 1


def test_ledger_includes_decisions_loops_cursors_exceptions_and_calculations():
    source = """IF score >= 90 THEN
  result := amount * rate;
ELSE
  result := 0;
END IF;
CASE status WHEN 'A' THEN result := result + 1; ELSE result := result + 2; END CASE;
WHILE pending = 1 LOOP
  OPEN account_cursor;
  FETCH account_cursor INTO account_id;
  CLOSE account_cursor;
END LOOP;
EXCEPTION WHEN OTHERS THEN RAISE;
"""
    ledger = build_completeness_ledger(source, {"decision_chains": []}, rules=[])
    types = {item["construct_type"] for item in ledger["items"]}

    assert "IF" in types
    assert "ELSE" in types
    assert "CASE" in types or "CASE_BRANCH" in types
    assert "WHILE" in types
    assert "LOOP" in types
    assert "CURSOR_OPERATION" in types
    assert "EXCEPTION" in types
    assert "RAISE" in types
    assert "CALCULATION" in types
    assert all(item["status"] == "uncovered" for item in ledger["items"])


def test_ledger_marks_parser_failure_and_unsupported_without_promoting_them_to_rules():
    merged = {
        "statement_provenance": [
            {
                "statement_id": "failed_1",
                "statement_kind": "MERGE",
                "source_statement_text": "MERGE unsupported shape",
                "source_line_start": 10,
                "source_line_end": 12,
                "parse_status": "parse_failed",
            },
            {
                "statement_id": "unsupported_1",
                "statement_kind": "SELECT",
                "source_statement_text": "SELECT unsupported_function(x)",
                "source_line_start": 14,
                "source_line_end": 14,
                "parse_status": "unsupported",
            },
        ]
    }
    ledger = build_completeness_ledger("MERGE unsupported shape\nSELECT unsupported_function(x)", merged)

    assert ledger["status_counts"]["parser_failed"] == 1
    assert ledger["status_counts"]["unsupported"] == 1
    assert not any(item["status"] == "covered_by_rule" for item in ledger["items"])


def test_verification_report_renders_ledger_without_changing_business_report_semantics():
    merged = _multi_statement_extraction()
    merged["completeness_ledger"] = build_completeness_ledger(
        _multi_statement_source(),
        merged,
        rules=[
            _rule(
                source_statement_ids=["stmt_update"],
                source_evidence=["UPDATE ACCOUNT SET STATUS = 'A'"],
                fields_affected=["STATUS"],
                action="STATUS = 'A'",
            )
        ],
    )
    synthesis = SynthesisResult(data={
        "purpose_summary": "Updates account status.",
        "business_rules": [_rule(
            source_statement_ids=["stmt_update"],
            source_evidence=["UPDATE ACCOUNT SET STATUS = 'A'"],
            fields_affected=["STATUS"],
            action="STATUS = 'A'",
        )],
    })
    verification = ReportFormatterAgent().format_verification(
        ingestion=_make_ingestion("TSQL"),
        merged_extraction=merged,
        synthesis=synthesis,
    )

    assert "## Completeness Ledger" in verification
    assert "covered_by_rule" in verification
    assert "technical_only" in verification
    assert "dynamic_unresolved" in verification
    assert "parser_failed" in verification
    assert "unsupported" in verification
    assert "UPDATE" in verification
