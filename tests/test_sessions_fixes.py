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

from src.ingestion.ingestion import CodeChunk, CodeIngestionAgent, decode_sql_source_bytes
from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import SynthesisResult
from src.dialect.detector import DialectDetectionResult
from src.parsing.statement_boundaries import split_top_level_statements
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks, split_table_operations


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


def test_ingestion_preserves_original_code_and_chunk_location_metadata():
    agent = CodeIngestionAgent(max_chunk_chars=200, dialect="oracle")
    original = "CREATE OR REPLACE PROCEDURE demo AS\nBEGIN\nSELECT 1 FROM dual;\nEND;"
    cleaned = original.replace("\r\n", "\n")
    detection = DialectDetectionResult(dialect="ORACLE", confidence="high", concrete_dialect="oracle")

    result = agent.ingest_text(
        cleaned,
        dialect="oracle",
        source_filename="demo.sql",
        original_code=original,
        prevalidated_code=cleaned,
        prevalidated_warnings=[],
        prevalidated_injection_flags=[],
        detection_result=detection,
    )

    assert result.original_code == original
    assert result.raw_code == cleaned
    assert result.chunks
    first_chunk = result.chunks[0]
    assert first_chunk.source_filename == "demo.sql"
    assert first_chunk.source_line_start >= 1
    assert first_chunk.source_line_end >= first_chunk.source_line_start


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
    from src.retrieval.retriever import _LocalHashEmbeddingFunction

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


def test_data_touched_row_with_embedded_pipe_and_newline_does_not_break_table():
    # "Data Touched" (src/output/report_formatter.py) replaced the old,
    # duplicated "Important Business Updates" + "Tables Read" / "Tables
    # Written" sections with a single deduplicated table - see report
    # design notes. It's driven by `_consolidate_rows` output rather than
    # raw tables_read/tables_written dicts directly.
    #
    # The Purpose column no longer surfaces raw WHERE-predicate text at
    # all (that was a separate bug - see the business_meaning-based
    # `_table_purpose_text` rewrite), so this regression test exercises
    # table-escaping robustness through the business_meaning path instead:
    # a business rule's own text is the only remaining source of
    # arbitrary characters that could reach this table.
    fmt = ReportFormatterAgent()
    consolidated_reads = fmt._consolidate_rows(
        [
            {
                "table": "SYSDAYMATRIX",
                "target_columns": ["DATE"],
                "where_predicate": "TIMEKEY = @TIMEKEY | LEGACY\nAND FLAG = 1",
                "operation": "READ",
            }
        ]
    )
    rules = [
        {
            "fields_affected": ["DATE"],
            "business_meaning": "Resolves the run date | also used for legacy jobs\nsecond line",
        }
    ]
    report = fmt._data_touched_section(consolidated_reads, [], rules)
    assert _no_broken_table_rows(report)
    assert "\\|" in report  # pipe survived, escaped
    # The raw WHERE-predicate text itself must never appear verbatim.
    assert "TIMEKEY = @TIMEKEY" not in report


def test_large_table_is_split_with_repeated_headers_and_no_rows_lost():
    fmt = ReportFormatterAgent()
    consolidated_reads = fmt._consolidate_rows(
        [
            {"table": f"PRO.TABLE_{i}", "target_columns": ["COL_A"], "where_predicate": "X = 1", "operation": "READ"}
            for i in range(75)
        ]
    )
    report = fmt._data_touched_section(consolidated_reads, [])
    assert _no_broken_table_rows(report)
    assert "continued" in report
    # every table name must still be present somewhere in the split output
    for i in range(75):
        assert f"PRO.TABLE_{i}" in report
    # header line repeated more than once (split happened)
    assert report.count("| Table | Read/Write | Purpose |") > 1


def test_small_table_is_not_split():
    fmt = ReportFormatterAgent()
    consolidated_reads = fmt._consolidate_rows(
        [{"table": "PRO.ONE_TABLE", "target_columns": ["COL_A"], "where_predicate": "", "operation": "READ"}]
    )
    report = fmt._data_touched_section(consolidated_reads, [])
    assert "continued" not in report


def test_data_touched_omits_temp_working_tables_but_notes_the_omission():
    fmt = ReportFormatterAgent()
    consolidated_reads = fmt._consolidate_rows(
        [
            {"table": "#DPD", "target_columns": ["X"], "operation": "READ"},
            {"table": "PRO.ACCOUNTCAL", "target_columns": ["Y"], "operation": "READ"},
        ]
    )
    report = fmt._data_touched_section(consolidated_reads, [])
    assert "#DPD" not in report
    assert "PRO.ACCOUNTCAL" in report
    assert "working/temporary table" in report


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


def test_at_a_glance_lists_all_written_tables_not_just_first_six():
    # Regression test: "Tables Updated" in At a Glance used to hard-slice
    # to the first 6 consolidated writes (`consolidated_writes[:6]`),
    # silently dropping every table past that - local (#) and history
    # tables included - with no indication anything was hidden. It must
    # now show every table when there are few, or an honest "+N more"
    # pointer to the full "Tables Written" section rather than dropping
    # rows invisibly.
    table_names = [
        "PRO.CUSTOMERCAL", "#DPD", "PRO.AccountCal", "PRO.ACCOUNT_MOVEMENT_HISTORY",
        "PRO.CUSTOMER_MOVEMENT_HISTORY", "PRO.ACCOUNTCAL", "PRO.SMA_MOVEMENT_HISTORY",
        "PRO.PREVSMASTATUS", "#SMACLASS", "#ACCOUNT_MOVEMENT_HISTORY",
        "#Customer_MOVEMENT_HISTORY", "PRO.ACLRUNNINGPROCESSSTATUS",
    ]
    writes = [{"table": name} for name in table_names]
    summary = ReportFormatterAgent._summarize_table_list(writes)
    for name in table_names[:10]:
        assert f"`{name}`" in summary
    assert "+2 more" in summary

    small_writes = [{"table": name} for name in table_names[:3]]
    small_summary = ReportFormatterAgent._summarize_table_list(small_writes)
    for name in table_names[:3]:
        assert f"`{name}`" in small_summary
    assert "more" not in small_summary


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
            "evidence_spans": [
                {
                    "source_file": "demo.sql",
                    "line_start": 12,
                    "line_end": 14,
                    "chunk_id": "01_main",
                    "statement_id": "STMT-01",
                    "evidence_type": "CONDITION",
                }
            ],
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
        ],
        "chunk_provenance": [
            {
                "chunk_id": "01_main",
                "chunk_kind": "main_body",
                "chunk_context": ["main_body"],
                "embedded_sql": [],
                "parse_error": "",
                "guardrail_warnings": [],
                "support_confidence": "high",
                "source_file": "demo.sql",
                "source_char_start": 100,
                "source_char_end": 200,
                "source_line_start": 12,
                "source_line_end": 14,
                "source_location_status": "available",
            }
        ],
    }
    report = ReportFormatterAgent()._source_traceability_details(rules, merged_extraction)
    assert _no_broken_table_rows(report)
    assert "Lines 12-14" in report


def test_business_rule_block_shows_compact_source_location():
    rules = [
        {
            "condition": "overdue_days <= 90",
            "action": "Keeps the account in the standard bucket",
            "rule_type": "explicit",
            "validation_status": "verified",
            "source_evidence": ["overdue_days <= 90"],
            "source_chunks": ["01_main:main_body"],
            "evidence_spans": [
                {
                    "source_file": "demo.sql",
                    "line_start": 12,
                    "line_end": 14,
                    "chunk_id": "01_main",
                    "statement_id": "STMT-01",
                    "evidence_type": "CONDITION",
                }
            ],
            "technical_references": ["conditions[0]"],
            "unresolved_ambiguities": [],
            "dependencies": [],
        }
    ]
    report = ReportFormatterAgent().format(
        ingestion=_ingestion_stub(),
        merged_extraction={"tables_read": [], "tables_written": [], "conditions": []},
        synthesis=_synthesis_stub(rules),
        extraction_guardrail_warnings=[],
    )
    assert "**Source:**" not in report
    # Source Traceability (chunk ids, statement ids, source line spans) is
    # pipeline provenance and must not appear in the business report.
    assert "## Source Traceability" not in report
    assert "Chunk 01_main" not in report
    assert "Statement STMT-01" not in report

    verification = ReportFormatterAgent().format_verification(
        ingestion=_ingestion_stub(),
        merged_extraction={"tables_read": [], "tables_written": [], "conditions": []},
        synthesis=_synthesis_stub(rules),
    )
    assert "## Source Traceability" in verification
    assert "demo.sql \\| Lines 12-14 \\| Chunk 01_main \\| Statement STMT-01" in verification

def test_find_write_only_temp_tables_flags_genuinely_dead_table():
    from src.parsing.dedup import find_write_only_temp_tables

    table_operations = [
        {"table": "#DEAD", "operation": "INSERT", "source_statement_text": "SELECT 1 INTO #DEAD"},
    ]
    raw_source = (
        "IF OBJECT_ID('TEMPDB..#DEAD') IS NOT NULL\n"
        "   DROP TABLE #DEAD\n"
        "SELECT 1 INTO #DEAD\n"
    )
    assert find_write_only_temp_tables(table_operations, raw_source=raw_source) == ["#DEAD"]


def test_find_write_only_temp_tables_does_not_flag_table_read_via_missed_join():
    """Regression test for a real false positive found while validating
    against a production sample: a temp table read only inside an
    `UPDATE ... FROM ... JOIN` clause that a statement-boundary edge case
    merged with a following `IF EXISTS (...)` block, so the structural
    parser never emitted a READ record for it. The table is still
    written-only per `table_operations`, but its name appears again in
    the raw source outside of its own creation boilerplate - that must
    be enough to keep it off the confident "dead code" list.
    """
    from src.parsing.dedup import find_write_only_temp_tables

    table_operations = [
        {
            "table": "#ALIVE",
            "operation": "INSERT",
            "source_statement_text": "SELECT A.ID INTO #ALIVE FROM SOURCE_TABLE A",
        },
    ]
    raw_source = (
        "IF OBJECT_ID('TEMPDB..#ALIVE') IS NOT NULL\n"
        "   DROP TABLE #ALIVE\n"
        "SELECT A.ID INTO #ALIVE FROM SOURCE_TABLE A\n"
        "UPDATE A SET A.X = B.Y FROM TARGET_TABLE A INNER JOIN #ALIVE B ON A.ID = B.ID\n"
    )
    # Structurally, only the write is known (the JOIN-read was missed) -
    # but the raw-source cross-check must still exclude it.
    structural_only = find_write_only_temp_tables(table_operations)
    assert structural_only == ["#ALIVE"]
    assert find_write_only_temp_tables(table_operations, raw_source=raw_source) == []