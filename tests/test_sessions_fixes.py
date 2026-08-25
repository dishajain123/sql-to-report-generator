"""
Regression tests for the fixes made while triaging the 4 attached
banking stored-procedure samples:

1. UTF-16 source decoding shared between the CLI and Streamlit UI
   (agents.ingestion.decode_sql_source_bytes).
2. Deterministic TRUNCATE TABLE extraction as its own destructive
   operation kind (technical_sql_ops).
3. Chroma embedding-function protocol compliance for offline RAG
   retrieval (agents.retriever._LocalHashEmbeddingFunction).
4. Markdown table cell escaping / large-table splitting and redundant
   rule-text removal in the report formatter (agents.report_formatter).

Run with:  pytest tests/test_session_fixes.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from agents.ingestion import CodeChunk, CodeIngestionAgent, decode_sql_source_bytes
from agents.report_formatter import ReportFormatterAgent
from agents.rule_synthesizer import SynthesisResult
from sql_statement_boundaries import split_top_level_statements
from technical_sql_ops import extract_table_operations_from_chunks, split_table_operations


# --------------------------------------------------------------------------
# 1. UTF-16 decoding
# --------------------------------------------------------------------------


def test_decode_sql_source_bytes_handles_utf16_le_with_bom():
    text = "CREATE PROCEDURE dbo.Foo AS BEGIN SELECT 1 END"
    raw = text.encode("utf-16-le")
    raw_with_bom = b"\xff\xfe" + raw
    decoded = decode_sql_source_bytes(raw_with_bom)
    assert decoded == text
    assert "BEGIN" in decoded
    assert "SELECT" in decoded


def test_decode_sql_source_bytes_handles_utf16_without_bom_heuristically():
    text = "DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY = @TIMEKEY"
    raw = text.encode("utf-16-le")  # no BOM, matches raw SSMS-exported files
    decoded = decode_sql_source_bytes(raw)
    assert "DELETE" in decoded
    assert "TIMEKEY" in decoded


def test_decode_sql_source_bytes_plain_utf8_roundtrips():
    text = "SELECT * FROM dbo.Foo WHERE x = 1"
    assert decode_sql_source_bytes(text.encode("utf-8")) == text


def test_decode_sql_source_bytes_empty_input():
    assert decode_sql_source_bytes(b"") == ""


def test_naive_utf8_decode_of_utf16_source_loses_keywords_regression_guard():
    """Documents *why* the fix matters: a naive UTF-8 decode of UTF-16
    source doesn't raise, it silently produces text where every keyword
    match fails. This pins that failure mode so nobody reintroduces a
    bare `.decode("utf-8", errors="replace")` on upload paths.
    """
    text = "DELETE FROM PRO.SMA_MOVEMENT_HISTORY"
    raw = text.encode("utf-16-le")
    naive = raw.decode("utf-8", errors="replace")
    assert "DELETE" not in naive  # the bug

    fixed = decode_sql_source_bytes(raw)
    assert "DELETE" in fixed  # the fix


def test_code_ingestion_agent_decode_source_bytes_delegates_to_shared_function():
    text = "SELECT 1"
    raw = b"\xff\xfe" + text.encode("utf-16-le")
    assert CodeIngestionAgent._decode_source_bytes(raw) == decode_sql_source_bytes(raw)


# --------------------------------------------------------------------------
# 2. TRUNCATE TABLE extraction
# --------------------------------------------------------------------------


def _chunk(text: str) -> CodeChunk:
    return CodeChunk(chunk_id="c1", kind="main_body", context_path=["main_body"], text=text, embedded_sql=[])


def test_truncate_table_extracted_as_destructive_operation_not_dropped():
    ops, _ = extract_table_operations_from_chunks(
        [_chunk("TRUNCATE TABLE PRO.SMA_MOVEMENT_HISTORY;")], dialect="tsql"
    )
    assert len(ops) == 1
    assert ops[0]["operation"] == "TRUNCATE"
    assert ops[0]["table"] == "PRO.SMA_MOVEMENT_HISTORY"


def test_truncate_table_never_gets_a_fabricated_where_predicate():
    ops, _ = extract_table_operations_from_chunks(
        [_chunk("TRUNCATE TABLE PRO.PREVSMASTATUS;")], dialect="tsql"
    )
    assert ops[0]["where_predicate"] in (None, "")
    assert ops[0]["join_predicates"] == []
    assert ops[0]["exists_predicates"] == []


def test_truncate_table_classified_as_a_write_not_a_read():
    ops, _ = extract_table_operations_from_chunks(
        [_chunk("TRUNCATE TABLE PRO.SMA_MOVEMENT_HISTORY;")], dialect="tsql"
    )
    reads, writes = split_table_operations(ops)
    assert reads == []
    assert len(writes) == 1
    assert writes[0]["operation"] == "TRUNCATE"


def test_delete_with_where_still_extracted_normally_alongside_truncate_support():
    ops, _ = extract_table_operations_from_chunks(
        [_chunk("DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY = @TIMEKEY;")],
        dialect="tsql",
    )
    delete_ops = [o for o in ops if o["operation"] == "DELETE"]
    assert len(delete_ops) == 1
    assert delete_ops[0]["where_predicate"]


def test_statement_boundary_splitter_starts_new_statement_at_truncate():
    """Direct unit test on the shared boundary detector: TRUNCATE must be
    recognized as a statement-starting keyword, just like SELECT/INSERT/
    UPDATE/DELETE/MERGE/DECLARE, or a preceding statement silently
    swallows it as trailing text.
    """
    text = (
        "SELECT 1 FROM PRO.PREVSMASTATUS\r\n"
        "\r\n"
        "TRUNCATE TABLE PRO.PREVSMASTATUS\r\n"
        "\r\n"
        "INSERT INTO PRO.PREVSMASTATUS\r\n"
        "SELECT 1"
    )
    statements = split_top_level_statements(text, text)
    # TRUNCATE must get its own boundary rather than being merged into the
    # tail of the preceding SELECT. (The trailing INSERT/SELECT split into
    # two pieces here is pre-existing, unrelated splitter behavior for
    # `INSERT INTO x` followed by `SELECT ...` on separate lines - not
    # something this fix changes - so we only assert on the TRUNCATE
    # boundary itself rather than the total statement count.)
    assert any(s.upper().startswith("TRUNCATE") for s in statements)
    truncate_stmt = next(s for s in statements if s.upper().startswith("TRUNCATE"))
    assert "SELECT" not in truncate_stmt.upper()


def test_truncate_immediately_followed_by_insert_no_separators_both_extracted():
    """Regression guard for the exact pattern found in
    PRO_SMA_MARKING_StoredProcedure.sql: a SELECT, then an unterminated
    (no ';', no blank-line-only separation beyond a stray newline)
    `TRUNCATE TABLE X` immediately followed by `INSERT INTO X`. Before the
    statement-boundary keyword list included TRUNCATE, this whole
    TRUNCATE statement silently merged into the *end* of the preceding
    SELECT's text, sqlglot then failed to parse the merged text, and the
    regex fallback (which also didn't know about TRUNCATE) had no path
    to recover it - so the TRUNCATE simply vanished with no warning.
    """
    embedded = (
        "SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS\r\n"
        "FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B\r\n"
        "ON A.CustomerAcID=B.CustomerAcID\r\n"
        "WHERE B.SMA_CLASS IS NOT NULL\r\n"
        "\r\n"
        "TRUNCATE TABLE PRO.PREVSMASTATUS\r\n"
        "\r\n"
        "INSERT INTO PRO.PREVSMASTATUS\r\n"
        "SELECT @TIMEKEY,CustomerAcID,SMA_CLASS\r\n"
        "FROM #SMACLASS"
    )
    chunk = CodeChunk(
        chunk_id="c1", kind="nested_block", context_path=["main_body"], text="", embedded_sql=[embedded]
    )
    ops, _ = extract_table_operations_from_chunks([chunk], dialect="tsql")
    kinds_by_table = {(o["operation"], o["table"]) for o in ops}
    assert ("TRUNCATE", "PRO.PREVSMASTATUS") in kinds_by_table
    assert ("INSERT", "PRO.PREVSMASTATUS") in kinds_by_table
    truncate_op = next(o for o in ops if o["operation"] == "TRUNCATE" and o["table"] == "PRO.PREVSMASTATUS")
    assert not truncate_op["where_predicate"]


# --------------------------------------------------------------------------
# 3. Retriever embedding-function protocol
# --------------------------------------------------------------------------


def test_local_hash_embedding_function_reports_default_name():
    from agents.retriever import _LocalHashEmbeddingFunction

    fn = _LocalHashEmbeddingFunction()
    assert fn.name() == "default"
    assert fn.get_config() == {"dimension": fn.dimension}
    rebuilt = fn.build_from_config(fn.get_config())
    assert rebuilt.dimension == fn.dimension


# --------------------------------------------------------------------------
# 4. Report formatter: table escaping / splitting / redundant text
# --------------------------------------------------------------------------


def _ingestion_stub():
    return type(
        "Ingestion",
        (),
        {
            "object_name": "obj",
            "object_type": "PROCEDURE",
            "dialect": "tsql",
            "dialect_confidence": "high",
            "parameters": [],
            "parameter_parse_status": "parameterless",
            "parse_warnings": [],
            "raw_code": "",
        },
    )()


def _synthesis_stub(rules):
    return SynthesisResult(
        data={
            "purpose_summary": "Purpose",
            "step_by_step_flow": [],
            "business_rules": rules,
            "calculations": [],
            "exception_handling_summary": "",
            "ambiguities": [],
        },
        guardrail_warnings=[],
        jargon_flags=[],
        parse_error=None,
    )


def _no_broken_table_rows(report: str) -> bool:
    for line in report.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and not stripped.endswith("|"):
            return False
    return True


def test_escape_table_cell_neutralizes_pipes_newlines_and_backticks():
    escaped = ReportFormatterAgent._escape_table_cell("A = 1 | B\nC = `weird`")
    assert "\n" not in escaped
    assert "<br>" in escaped
    assert "|" not in escaped.replace(r"\|", "")  # only escaped pipes remain
    assert "`" not in escaped


def test_table_read_row_with_embedded_pipe_and_newline_does_not_break_table():
    merged_extraction = {
        "tables_read": [
            {
                "table": "SYSDAYMATRIX",
                "target_columns": ["DATE"],
                "where_predicate": "TIMEKEY = @TIMEKEY | LEGACY\nAND FLAG = 1",
            }
        ],
        "tables_written": [],
    }
    report = ReportFormatterAgent()._tables_read(merged_extraction)
    assert _no_broken_table_rows(report)
    assert "\\|" in report  # pipe survived, escaped


def test_large_table_is_split_with_repeated_headers_and_no_rows_lost():
    tables_read = [
        {"table": f"PRO.TABLE_{i}", "target_columns": ["COL_A"], "where_predicate": "X = 1"}
        for i in range(75)
    ]
    report = ReportFormatterAgent()._tables_read({"tables_read": tables_read, "tables_written": []})
    assert _no_broken_table_rows(report)
    assert "continued" in report
    # every table name must still be present somewhere in the split output
    for i in range(75):
        assert f"PRO.TABLE_{i}" in report
    # header line repeated more than once (split happened)
    assert report.count("| Table Name | Key Columns | Filter Conditions |") > 1


def test_small_table_is_not_split():
    tables_read = [{"table": "PRO.ONE_TABLE", "target_columns": ["COL_A"], "where_predicate": ""}]
    report = ReportFormatterAgent()._tables_read({"tables_read": tables_read, "tables_written": []})
    assert "continued" not in report


def test_when_not_eligible_omitted_when_source_has_no_negative_path():
    rules = [
        {
            "condition": "overdue_days <= 90",
            "action": "Keeps the account in the standard bucket",
            "rule_type": "explicit",
            "validation_status": "verified",
            # no when_not_eligible supplied by synthesis
        }
    ]
    report = ReportFormatterAgent().format(
        ingestion=_ingestion_stub(),
        merged_extraction={"tables_read": [], "tables_written": [], "conditions": []},
        synthesis=_synthesis_stub(rules),
        extraction_guardrail_warnings=[],
    )
    assert "### When Not Eligible" not in report
    assert "the stated outcome does not apply" not in report
    assert "see the collapsible mapping below" not in report


def test_when_not_eligible_rendered_when_source_has_meaningful_negative_path():
    rules = [
        {
            "condition": "overdue_days > 90",
            "action": "Escalate to sub-standard",
            "rule_type": "explicit",
            "validation_status": "verified",
            "when_not_eligible": ["Account remains in its current asset class"],
        }
    ]
    report = ReportFormatterAgent().format(
        ingestion=_ingestion_stub(),
        merged_extraction={"tables_read": [], "tables_written": [], "conditions": []},
        synthesis=_synthesis_stub(rules),
        extraction_guardrail_warnings=[],
    )
    assert "### When Not Eligible" in report
    assert "Account remains in its current asset class" in report


@pytest.mark.parametrize(
    "status,rule_type,expected_icon",
    [
        ("verified", "explicit", "🟢"),
        ("verified", "assumption", "🟠"),
        ("unverified", "inferred", "🟠"),
        ("parser_failed", "inferred", "🔴"),
        ("ambiguous", "inferred", "🔴"),
        ("insufficient_evidence", "inferred", "🟠"),
    ],
)
def test_review_priority_icon_matches_validation_status(status, rule_type, expected_icon):
    rule = {"validation_status": status, "rule_type": rule_type}
    assert ReportFormatterAgent._review_priority_icon(rule) == expected_icon


def test_business_rule_summary_table_includes_priority_column():
    rules = [
        {"condition": "c1", "action": "a1", "rule_type": "explicit", "validation_status": "verified"},
        {"condition": "c2", "action": "a2", "rule_type": "inferred", "validation_status": "parser_failed"},
    ]
    report = ReportFormatterAgent()._business_rule_summary_table(rules)
    assert "| Priority | Rule | Output | Business Purpose |" in report
    assert "🟢" in report
    assert "🔴" in report


def test_source_traceability_table_survives_pipes_in_technical_references():
    rules = [
        {
            "condition": "c1",
            "action": "a1",
            "rule_type": "explicit",
            "validation_status": "verified",
            "technical_references": ["conditions[0]"],
        }
    ]
    merged_extraction = {
        "conditions": [
            {
                "condition": "overdue_days <= 90",
                "true_branch": "Stay Standard | keep",
                "false_branch": None,
                "source_chunk_id": "01_main",
                "source_chunk_kind": "main_body",
            }
        ]
    }
    report = ReportFormatterAgent()._source_traceability_details(rules, merged_extraction)
    assert _no_broken_table_rows(report)