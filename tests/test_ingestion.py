"""
Unit tests for agents.ingestion.CodeIngestionAgent.

Run with:  pytest tests/test_ingestion.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.ingestion.ingestion import CodeIngestionAgent
from src.ingestion.ingestion import CodeChunk
from src.ingestion.ingestion import IngestionResult
from src.ingestion.ingestion import build_object_identity_stem
from src.output.report_formatter import ReportFormatterAgent
from src.ingestion.guardrails import run_input_guardrails
from src.ingestion.guardrails import ground_extraction_against_source
from src.ingestion.guardrails import find_inactive_code_blocks, strip_inactive_code_for_llm
from src.dialect.detector import DialectDetectionResult, detect_dialect
import src.parsing.technical_sql_ops as sql_ops
from src.parsing.technical_sql_ops import extract_table_operations_from_chunks, split_table_operations


SAMPLE_PROCEDURE = """
CREATE OR REPLACE PROCEDURE classify_npa_and_provision (
    p_account_id IN NUMBER
) IS
    v_overdue_days NUMBER;
BEGIN
    SELECT overdue_days INTO v_overdue_days FROM LOAN_ACCOUNT WHERE account_id = p_account_id;

    IF v_overdue_days <= 90 THEN
        UPDATE LOAN_ACCOUNT SET asset_classification = 'STANDARD' WHERE account_id = p_account_id;
    ELSE
        UPDATE LOAN_ACCOUNT SET asset_classification = 'SUBSTANDARD' WHERE account_id = p_account_id;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE;
END;
/
"""

SAMPLE_VIEW = """
CREATE OR REPLACE VIEW VW_TEST AS
SELECT account_id, overdue_days FROM LOAN_ACCOUNT WHERE overdue_days > 0;
"""

SAMPLE_QUOTED_OBJECT = """
CREATE OR REPLACE PROCEDURE "Loan Maintenance"."Recalc Status" (
    p_account_id IN NUMBER
) IS
BEGIN
    NULL;
END;
/
"""

SAMPLE_CTE_SQL = """
CREATE OR REPLACE PROCEDURE cte_demo IS
BEGIN
    WITH cte AS (
        SELECT account_id
        FROM LOAN_ACCOUNT
    )
    SELECT account_id
    INTO v_account_id
    FROM cte;
END;
/
"""

SAMPLE_TSQL_TRY_CATCH = """
CREATE PROCEDURE dbo.demo_proc
AS
BEGIN
    BEGIN TRY
        SELECT 1;
    END TRY
    BEGIN CATCH
        SELECT ERROR_MESSAGE();
    END CATCH
END
GO
"""

SAMPLE_TSQL_CREATE_OR_ALTER = """
CREATE OR ALTER PROCEDURE [dbo].[usp_mark_sma]
(
    @account_id INT,
    @status VARCHAR(20) = 'A' OUTPUT,
    @threshold DECIMAL(18, 2) = 90
)
AS
BEGIN
    DECLARE @local_counter INT = 0;
    SELECT @local_counter = COUNT(*)
    FROM dbo.Accounts
    WHERE account_id = @account_id;
END
GO
"""

SAMPLE_TSQL_CREATE_OR_ALTER_WITH_RECOMPILE = """
CREATE OR ALTER PROCEDURE [PRO].[SMA_MARKING_12122023]
@TIMEKEY INT
WITH RECOMPILE
AS
BEGIN
    SELECT 1;
END
GO
"""

SAMPLE_TSQL_PARAMLESS_WITH_DECLARE = """
CREATE PROCEDURE dbo.no_params_here
AS
BEGIN
    DECLARE @x INT = 1;
    SELECT @x;
END
GO
"""

SAMPLE_TSQL_BAD_PARAMS = """
CREATE PROCEDURE dbo.bad_params
(
    @account_id INT,
    @status VARCHAR(20) = 
)
AS
BEGIN
    SELECT 1;
END
GO
"""

SAMPLE_TSQL_DPD_CASE = """
CREATE OR ALTER PROCEDURE dbo.dpd_case_demo
AS
BEGIN
    IF @timekey > 26267
        UPDATE #DPD
        SET DPD_MAX = CASE
            WHEN DPD_IntService > DPD_NoCredit THEN DPD_IntService
            ELSE DPD_NoCredit
        END;
    ELSE
        UPDATE #DPD
        SET DPD_MAX = CASE
            WHEN DPD_Overdrawn > DPD_Overdue THEN DPD_Overdrawn
            ELSE DPD_Overdue
        END;
END
GO
"""

SAMPLE_SMA_TABLE_OPS = """
CREATE PROCEDURE dbo.SMA_MARKING_12122023
@TIMEKEY INT
AS
BEGIN
    SELECT DATE
    FROM SYSDAYMATRIX
    WHERE TIMEKEY = @TIMEKEY;

    SELECT A.AccountEntityID
    FROM [dbo].Automate_Advances A
    WHERE EXT_FLG = 'Y';

    INSERT INTO #TEMPTABLE (CustomerAcID, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt)
    SELECT CustomerAcID, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt
    FROM #DPD
    WHERE ISNULL(DPD_IntService,0) >= ISNULL(RefPeriodIntService,0)
       OR ISNULL(DPD_NoCredit,0) >= ISNULL(RefPeriodNoCredit,0)
       OR ISNULL(DPD_Overdrawn,0) >= ISNULL(RefPeriodOverDrawn,0)
       OR ISNULL(DPD_Overdue,0) >= ISNULL(RefPeriodOverdue,0)
       OR ISNULL(DPD_Renewal,0) >= ISNULL(RefPeriodReview,0)
       OR ISNULL(DPD_StockStmt,0) >= ISNULL(RefPeriodStkStatement,0);

    UPDATE A
    SET DPD_IntService = 0,
        DPD_NoCredit = 0,
        DPD_Renewal = 0,
        DPD_StockStmt = 0
    FROM #DPD A
    WHERE ISNULL(DPD_IntService,0) < 0
       OR ISNULL(DPD_NoCredit,0) < 0
       OR ISNULL(DPD_Renewal,0) < 0
       OR ISNULL(DPD_StockStmt,0) < 0;

    UPDATE A
    SET FLGSMA = 'Y'
    FROM PRO.ACCOUNTCAL A
    INNER JOIN PRO.CUSTOMERCAL B ON A.CustomerEntityID = B.CustomerEntityID
    WHERE ISNULL(B.FLGPROCESSING,'N') = 'N'
      AND EXISTS (
          SELECT 1
          FROM PRO.SMA_MOVEMENT_HISTORY M
          WHERE M.CustomerAcID = A.CustomerAcID
      );

    UPDATE PRO.ACLRUNNINGPROCESSSTATUS
    SET COMPLETED = 'Y',
        ERRORDATE = NULL,
        ERRORDESCRIPTION = NULL,
        COUNT = ISNULL(COUNT,0) + 1
    WHERE RUNNINGPROCESSNAME = 'SMA_MARKING';
END
GO
"""

SAMPLE_ANON_BLOCK = """
DECLARE
    v_x NUMBER := 1;
BEGIN
    NULL;
END;
/
"""


@pytest.fixture
def agent():
    return CodeIngestionAgent(max_chunk_chars=2000)


def test_detect_object_type_procedure(agent):
    assert agent.detect_object_type(SAMPLE_PROCEDURE) == "PROCEDURE"


def test_detect_object_type_view(agent):
    assert agent.detect_object_type(SAMPLE_VIEW) == "VIEW"


def test_detect_object_type_anonymous_block(agent):
    assert agent.detect_object_type(SAMPLE_ANON_BLOCK) == "PLSQL_BLOCK"


def test_extract_object_name_procedure(agent):
    name = agent.extract_object_name(SAMPLE_PROCEDURE, "PROCEDURE")
    assert name == "classify_npa_and_provision"


def test_extract_object_name_with_quotes(agent):
    name = agent.extract_object_name(SAMPLE_QUOTED_OBJECT, "PROCEDURE")
    assert name == "Recalc Status"


def test_extract_parameters(agent):
    params = agent.extract_parameters(SAMPLE_PROCEDURE)
    assert len(params) == 1
    assert params[0].name == "p_account_id"
    assert params[0].direction == "IN"
    assert params[0].datatype == "NUMBER"


def test_extract_tsql_create_or_alter_metadata(agent):
    object_type, object_name, parameters, warnings, object_name_status, parameter_status = agent.extract_object_metadata(
        SAMPLE_TSQL_CREATE_OR_ALTER, dialect="tsql"
    )
    assert object_type == "PROCEDURE"
    assert object_name == "usp_mark_sma"
    assert object_name_status == "verified"
    assert parameter_status == "parameterized"
    assert warnings == []
    assert [p.name for p in parameters] == ["@account_id", "@status", "@threshold"]
    assert parameters[0].direction == "IN"
    assert parameters[1].direction == "OUT"
    assert parameters[1].datatype == "VARCHAR(20)"
    assert parameters[2].datatype == "DECIMAL(18, 2)"


def test_extract_tsql_parameters_with_header_options(agent):
    object_type, object_name, parameters, warnings, object_name_status, parameter_status = agent.extract_object_metadata(
        SAMPLE_TSQL_CREATE_OR_ALTER_WITH_RECOMPILE, dialect="tsql"
    )
    assert object_type == "PROCEDURE"
    assert object_name == "SMA_MARKING_12122023"
    assert object_name_status == "verified"
    assert parameter_status == "parameterized"
    assert warnings == []
    assert [p.name for p in parameters] == ["@TIMEKEY"]
    assert parameters[0].direction == "IN"
    assert parameters[0].datatype == "INT"


def test_declare_variables_do_not_become_parameters(agent):
    object_type, object_name, parameters, warnings, object_name_status, parameter_status = agent.extract_object_metadata(
        SAMPLE_TSQL_PARAMLESS_WITH_DECLARE, dialect="tsql"
    )
    assert object_type == "PROCEDURE"
    assert object_name == "no_params_here"
    assert object_name_status == "verified"
    assert parameters == []
    assert parameter_status == "parameterless"
    assert not any("declare" in warning.lower() for warning in warnings)


def test_malformed_tsql_parameter_list_is_not_hidden_as_parameterless(agent):
    object_type, object_name, parameters, warnings, object_name_status, parameter_status = agent.extract_object_metadata(
        SAMPLE_TSQL_BAD_PARAMS, dialect="tsql"
    )
    assert object_type == "PROCEDURE"
    assert object_name == "bad_params"
    assert object_name_status == "verified"
    assert parameters == []
    assert parameter_status == "failed"
    assert any("parameter extraction failed" in warning.lower() for warning in warnings)


def test_chunk_code_produces_chunks(agent):
    warnings = []
    chunks = agent.chunk_code(SAMPLE_PROCEDURE, warnings)
    assert len(chunks) > 0
    kinds = {c.kind for c in chunks}
    # We expect at least a main body/nested block and an exception section
    assert "exception" in kinds
    assert any("declaration" in c.context_path for c in chunks)


def test_chunk_code_respects_max_size(agent):
    big_code = SAMPLE_PROCEDURE + ("\n-- padding comment line" * 500)
    warnings = []
    chunks = agent.chunk_code(big_code, warnings)
    for c in chunks:
        assert len(c.text) <= agent.max_chunk_chars + 200  # small tolerance for statement boundaries


def test_structural_parse_keeps_case_expression_out_of_raw_text_fallback(agent):
    warnings = []
    stmts = agent._extract_and_validate_sql(
        "CASE WHEN DPD_MAX > 90 THEN 'HIGH' ELSE 'LOW' END;",
        warnings,
        dialect="tsql",
    )
    assert stmts == ["CASE WHEN DPD_MAX > 90 THEN 'HIGH' ELSE 'LOW' END;"]
    assert warnings == []


def test_inline_comments_do_not_force_raw_text_fallback(agent):
    warnings = []
    stmt = (
        "UPDATE #DPD SET DPD_MAX = CASE WHEN DPD_IntService > DPD_NoCredit "
        "THEN DPD_IntService ELSE DPD_NoCredit END -- developer note\n;"
    )
    stmts = agent._extract_and_validate_sql(stmt, warnings, dialect="tsql")
    assert stmts == [stmt]
    assert warnings == []


def test_ingest_full_file(tmp_path, agent):
    sql_file = tmp_path / "sample.sql"
    sql_file.write_text(SAMPLE_PROCEDURE, encoding="utf-8")

    result = agent.ingest(str(sql_file))
    assert result.object_type == "PROCEDURE"
    assert result.object_name == "classify_npa_and_provision"
    assert len(result.parameters) == 1
    assert len(result.chunks) > 0


def test_ingest_tsql_metadata_preserved(tmp_path):
    agent = CodeIngestionAgent(max_chunk_chars=2000, dialect="tsql")
    sql_file = tmp_path / "sample_tsql.sql"
    sql_file.write_text(SAMPLE_TSQL_CREATE_OR_ALTER, encoding="utf-8")

    result = agent.ingest(str(sql_file), dialect="tsql")
    assert result.object_type == "PROCEDURE"
    assert result.object_name == "usp_mark_sma"
    assert result.parameter_parse_status == "parameterized"
    assert [p.name for p in result.parameters] == ["@account_id", "@status", "@threshold"]
    assert result.parameters[1].direction == "OUT"
    assert result.parameters[1].datatype == "VARCHAR(20)"
    assert result.parameters[2].datatype == "DECIMAL(18, 2)"


def test_ingest_parameter_failure_is_not_hidden_as_none(tmp_path):
    agent = CodeIngestionAgent(max_chunk_chars=2000, dialect="tsql")
    sql_file = tmp_path / "paramless_tsql.sql"
    sql_file.write_text(SAMPLE_TSQL_PARAMLESS_WITH_DECLARE, encoding="utf-8")

    result = agent.ingest(str(sql_file), dialect="tsql")
    assert result.object_type == "PROCEDURE"
    assert result.object_name == "no_params_here"
    assert result.parameter_parse_status == "parameterless"
    assert result.parameters == []


def test_temp_tables_are_not_marked_low_confidence_when_present_in_source():
    data = {
        "tables_read": [
            {
                "table": "#DPD",
                "columns": ["DPD_MAX"],
                "filter_condition": "DPD_MAX > 90",
                "confidence": "high",
            }
        ],
        "tables_written": [],
        "conditions": [],
        "loops": [],
        "calculations": [],
        "exception_handling": [],
        "ambiguities": [],
    }
    warnings = ground_extraction_against_source(data, SAMPLE_TSQL_DPD_CASE)
    assert warnings == []
    assert data["tables_read"][0]["confidence"] == "high"


def test_ingest_uses_filename_fallback_when_header_is_missing(tmp_path):
    agent = CodeIngestionAgent(max_chunk_chars=2000, dialect="tsql")
    sql_file = tmp_path / "loan_status_recalc_procedure.sql"
    sql_file.write_text("BEGIN SELECT 1; END", encoding="utf-8")

    result = agent.ingest(str(sql_file), dialect="tsql")
    assert result.object_type == "PROCEDURE"
    assert result.object_name == "recalc"
    assert result.object_name_status == "verified"


def test_load_file_decodes_utf16_sql_and_preserves_parameters(tmp_path):
    sql_file = tmp_path / "PRO.SMA_MARKING_12122023.StoredProcedure.sql"
    sql_file.write_bytes(SAMPLE_TSQL_CREATE_OR_ALTER_WITH_RECOMPILE.encode("utf-16"))

    loaded = CodeIngestionAgent._load_file(str(sql_file))
    assert "CREATE OR ALTER PROCEDURE [PRO].[SMA_MARKING_12122023]" in loaded
    assert "@TIMEKEY INT" in loaded

    agent = CodeIngestionAgent(max_chunk_chars=2000, dialect="tsql")
    result = agent.ingest_text(loaded, dialect="tsql", source_filename=str(sql_file))
    assert result.object_name == "SMA_MARKING_12122023"
    assert result.parameters and result.parameters[0].name == "@TIMEKEY"
    assert result.parameter_parse_status == "parameterized"


def test_statement_level_table_operations_preserve_predicates_and_statement_ids():
    chunk = CodeChunk(
        chunk_id="00_main_body",
        kind="main_body",
        text=SAMPLE_SMA_TABLE_OPS,
        embedded_sql=[
            "SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY = @TIMEKEY",
            "SELECT A.AccountEntityID FROM [dbo].Automate_Advances A WHERE EXT_FLG = 'Y'",
            "INSERT INTO #TEMPTABLE (CustomerAcID, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt) SELECT CustomerAcID, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt FROM #DPD WHERE ISNULL(DPD_IntService,0) >= ISNULL(RefPeriodIntService,0) OR ISNULL(DPD_NoCredit,0) >= ISNULL(RefPeriodNoCredit,0) OR ISNULL(DPD_Overdrawn,0) >= ISNULL(RefPeriodOverDrawn,0) OR ISNULL(DPD_Overdue,0) >= ISNULL(RefPeriodOverdue,0) OR ISNULL(DPD_Renewal,0) >= ISNULL(RefPeriodReview,0) OR ISNULL(DPD_StockStmt,0) >= ISNULL(RefPeriodStkStatement,0)",
            "UPDATE A SET DPD_IntService = 0, DPD_NoCredit = 0, DPD_Renewal = 0, DPD_StockStmt = 0 FROM #DPD A WHERE ISNULL(DPD_IntService,0) < 0 OR ISNULL(DPD_NoCredit,0) < 0 OR ISNULL(DPD_Renewal,0) < 0 OR ISNULL(DPD_StockStmt,0) < 0",
            "UPDATE A SET FLGSMA = 'Y' FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B ON A.CustomerEntityID = B.CustomerEntityID WHERE ISNULL(B.FLGPROCESSING,'N') = 'N' AND EXISTS (SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY M WHERE M.CustomerAcID = A.CustomerAcID)",
            "UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT,0) + 1 WHERE RUNNINGPROCESSNAME = 'SMA_MARKING'",
        ],
        context_path=["main_body"],
    )

    operations, provenance = extract_table_operations_from_chunks([chunk], "tsql")
    reads, writes = split_table_operations(operations)

    assert len(provenance) >= 6
    assert any(op["source_statement_id"].startswith("00_main_body:") for op in reads)
    assert any(op["table"] == "SYSDAYMATRIX" and op["where_predicate"] == "TIMEKEY = @TIMEKEY" for op in reads)
    assert any(op["table"] == "dbo.Automate_Advances" and op["where_predicate"] == "EXT_FLG = 'Y'" for op in reads)
    assert any(op["table"] == "#DPD" and "RefPeriodIntService" in op["where_predicate"] for op in reads)
    assert any(
        op["table"] == "#DPD"
        and op["operation"] == "UPDATE"
        and "DPD_IntService" in op["where_predicate"]
        and "< 0" in op["where_predicate"]
        for op in writes
    )
    assert any(
        op["table"] == "PRO.ACCOUNTCAL"
        and op["operation"] == "UPDATE"
        and op["join_predicates"]
        and op["exists_predicates"]
        for op in writes
    )
    assert any(
        op["table"] == "PRO.ACLRUNNINGPROCESSSTATUS"
        and op["where_predicate"] == "RUNNINGPROCESSNAME = 'SMA_MARKING'"
        for op in writes
    )
    assert all(op["active_status"] == "ACTIVE" for op in operations)
    assert all("Always, on each execution" not in (op.get("where_predicate") or "") for op in operations)


def test_real_sma_sql_pattern_extracts_schema_qualified_read_and_process_status_update():
    raw_sql = """
DECLARE @vEffectiveto INT
SET @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y')

UPDATE PRO.ACLRUNNINGPROCESSSTATUS
SET COMPLETED='Y',
    ERRORDATE=NULL,
    ERRORDESCRIPTION=NULL,
    COUNT=ISNULL(COUNT,0)+1
WHERE RUNNINGPROCESSNAME='SMA_MARKING'
"""
    chunk = CodeChunk(
        chunk_id="real_sma_chunk",
        kind="main_body",
        text=raw_sql,
        embedded_sql=[],
        context_path=["main_body"],
    )

    operations, provenance = extract_table_operations_from_chunks([chunk], "tsql")
    reads, writes = split_table_operations(operations)

    assert provenance, "expected statement provenance for real SQL pattern"
    assert any(op["table"] == "dbo.Automate_Advances" for op in reads)
    assert any(
        op["table"] == "PRO.ACLRUNNINGPROCESSSTATUS"
        and op["operation"] == "UPDATE"
        and op["where_predicate"] == "RUNNINGPROCESSNAME = 'SMA_MARKING'"
        for op in writes
    )
    assert all("Always, on each execution" not in (op.get("where_predicate") or "") for op in operations)


def test_tsql_update_fallback_preserves_case_assignments_and_filters_comments():
    raw_sql = """
UPDATE B
SET B.AssetKey = CASE WHEN B.Days > @Limit THEN 7 ELSE 3 END,
    B.DbtDt = NULL,
    B.DegDate = @ProcessDate
FROM ##Customer B
WHERE B.Active = 1
-- UPDATE B SET B.AssetKey = 999
"""
    chunk = CodeChunk(chunk_id="case_update_chunk", kind="main_body", text=raw_sql, context_path=["main_body"])
    operations, _ = extract_table_operations_from_chunks([chunk], "tsql")
    updates = [op for op in operations if op["operation"] == "UPDATE"]
    assert updates
    assignments = updates[0]["assigned_values"]
    assert {item["column"] for item in assignments} == {"B.AssetKey", "B.DbtDt", "B.DegDate"}
    assert any("CASE WHEN" in item["expression"] for item in assignments)
    assert any(item["expression"].upper() == "NULL" for item in assignments)
    assert any(item["expression"] == "@ProcessDate" for item in assignments)
    case_assignment = next(item for item in assignments if item["column"] == "B.AssetKey")
    assert case_assignment["case_branches"]
    assert case_assignment["case_branches"][0]["condition"] == "B.Days > @Limit"
    assert case_assignment["case_branches"][-1]["condition"] == "ELSE"


def test_update_insert_select_does_not_emit_spurious_read_rows():
    chunk = CodeChunk(
        chunk_id="dml_chunk",
        kind="main_body",
        text=(
            "UPDATE dbo.Account SET Status = 'OVERDUE' WHERE DpdDays > 90;\n"
            "INSERT INTO dbo.AccountAudit (AccountId, NewStatus)\n"
            "SELECT AccountId, 'OVERDUE' FROM dbo.Account WHERE DpdDays > 90;"
        ),
        embedded_sql=[],
        context_path=["main_body"],
    )

    operations, _ = extract_table_operations_from_chunks([chunk], "tsql")
    reads, writes = split_table_operations(operations)

    assert [op["operation"] for op in writes] == ["UPDATE", "INSERT"]
    assert [op["table"] for op in reads] == ["dbo.Account"]
    assert all(op["operation"] != "READ" or op["table"] != "dbo.Account" for op in operations if op["operation"] == "READ")


def test_unsupported_postgresql_short_circuits_without_oracle_fallback():
    raw = """
CREATE OR REPLACE FUNCTION demo_fn()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE NOTICE 'hi';
END;
$$;
"""
    clean = run_input_guardrails(raw).clean_code
    detection = detect_dialect(clean, hint="auto")
    agent = CodeIngestionAgent(dialect="auto")
    result = agent.ingest_text(
        clean,
        dialect="auto",
        source_filename="demo_fn.sql",
        original_code=raw,
        prevalidated_code=clean,
        prevalidated_warnings=[],
        prevalidated_injection_flags=[],
        detection_result=detection,
    )

    assert result.dialect == "UNSUPPORTED"
    assert result.object_type == "UNKNOWN"
    assert result.object_name == "UNKNOWN_OBJECT"
    assert result.concrete_dialect == ""
    assert result.fallback_dialect == ""
    assert result.parse_warnings == ["PostgreSQL features detected; unsupported by the current parser layer."]


def test_regex_fallback_preserves_where_without_alias(monkeypatch):
    def fail_parse_one(*args, **kwargs):
        raise sql_ops.ParseError("forced fallback")

    monkeypatch.setattr(sql_ops.sqlglot, "parse_one", fail_parse_one)

    chunk = CodeChunk(
        chunk_id="fallback_where",
        kind="main_body",
        text="SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY = @TIMEKEY",
        embedded_sql=[],
        context_path=["main_body"],
    )

    operations, _ = extract_table_operations_from_chunks([chunk], "tsql")
    reads, writes = split_table_operations(operations)

    assert not writes
    assert any(
        op["table"] == "SYSDAYMATRIX"
        and op["operation"] == "READ"
        and op["where_predicate"] == "TIMEKEY = @TIMEKEY"
        and op["table_alias"] == ""
        for op in reads
    )


def test_oracle_select_into_variable_is_read_only():
    chunk = CodeChunk(
        chunk_id="oracle_select_into",
        kind="main_body",
        text=(
            'SELECT "Date" INTO v_ProcessDate FROM SysDayMatrix '
            'WHERE TimeKey = p_TIMEKEY AND ROWNUM = 1'
        ),
        embedded_sql=[],
        context_path=["main_body"],
    )

    operations, _ = extract_table_operations_from_chunks([chunk], "oracle")
    reads, writes = split_table_operations(operations)

    assert not any(op["table"] == "v_ProcessDate" for op in writes)
    assert any(op["table"] == "SysDayMatrix" and op["operation"] == "READ" for op in reads)


def test_tsql_select_into_table_remains_a_write():
    chunk = CodeChunk(
        chunk_id="tsql_select_into",
        kind="main_body",
        text="SELECT account_id INTO #Overdue FROM LOAN_ACCOUNT WHERE overdue_days > 0",
        embedded_sql=[],
        context_path=["main_body"],
    )

    operations, _ = extract_table_operations_from_chunks([chunk], "tsql")
    reads, writes = split_table_operations(operations)

    assert any(op["table"] == "LOAN_ACCOUNT" and op["operation"] == "READ" for op in reads)
    assert any(op["table"] == "#Overdue" and op["operation"] == "INSERT" for op in writes)


def test_regex_fallback_captures_insert_and_delete(monkeypatch):
    def fail_parse_one(*args, **kwargs):
        raise sql_ops.ParseError("forced fallback")

    monkeypatch.setattr(sql_ops.sqlglot, "parse_one", fail_parse_one)

    chunk = CodeChunk(
        chunk_id="fallback_write",
        kind="main_body",
        text=(
            "INSERT INTO #TEMPTABLE (CustomerAcID, DPD_IntService) "
            "SELECT CustomerAcID, DPD_IntService FROM #DPD WHERE DPD_IntService > 0; "
            "DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY = @TIMEKEY"
        ),
        embedded_sql=[],
        context_path=["main_body"],
    )

    operations, _ = extract_table_operations_from_chunks([chunk], "tsql")
    reads, writes = split_table_operations(operations)

    assert any(
        op["table"] == "#TEMPTABLE"
        and op["operation"] == "INSERT"
        and op["target_columns"] == ["CustomerAcID", "DPD_IntService"]
        and op["source_columns"] == ["CustomerAcID", "DPD_IntService"]
        for op in writes
    )
    assert any(
        op["table"] == "PRO.ACLRUNNINGPROCESSSTATUS" or op["table"] == "PRO.SMA_MOVEMENT_HISTORY"
        for op in writes
    )
    assert any(
        op["table"] == "PRO.SMA_MOVEMENT_HISTORY"
        and op["operation"] == "DELETE"
        and op["where_predicate"] == "TIMEKEY = @TIMEKEY"
        and op["table_alias"] == ""
        for op in writes
    )
    assert not reads or all(op["operation"] == "READ" for op in reads)


def test_table_sections_do_not_turn_missing_predicates_into_filters():
    fmt = ReportFormatterAgent()
    consolidated_reads = fmt._consolidate_rows(
        [
            {
                "statement_id": "00_main_body:stmt_01",
                "table": "SYSDAYMATRIX",
                "table_alias": "",
                "operation": "READ",
                "target_columns": ["DATE"],
                "source_columns": ["TIMEKEY"],
                "where_predicate": "TIMEKEY = @TIMEKEY",
                "join_predicates": [],
                "exists_predicates": [],
                "constants": ["@TIMEKEY"],
                "active_status": "ACTIVE",
                "provenance": {"chunk_id": "00_main_body", "chunk_kind": "main_body"},
            },
            {
                "statement_id": "00_main_body:stmt_02",
                # Not a temp table (no leading '#') so it isn't excluded
                # from the business-facing "Data Touched" section - this
                # specifically exercises the no-predicate fallback path.
                "table": "PRO.DPD_WORK",
                "table_alias": "A",
                "operation": "READ",
                "target_columns": ["DPD_IntService"],
                "source_columns": ["DPD_IntService"],
                "where_predicate": "",
                "join_predicates": [],
                "exists_predicates": [],
                "constants": [],
                "active_status": "ACTIVE",
                "provenance": {"chunk_id": "00_main_body", "chunk_kind": "main_body"},
            },
        ]
    )
    report = fmt._data_touched_section(consolidated_reads, [])
    # No predicate was extracted for PRO.DPD_WORK - the formatter must
    # never fabricate a trigger/filter phrase for it, only fall back to
    # the columns touched (or "Not specified" if there are none either).
    assert "Always, on each execution" not in report
    assert "Provides: DPD_IntService" in report


def test_ingest_missing_file_raises(agent):
    with pytest.raises(FileNotFoundError):
        agent.ingest("/nonexistent/path/does_not_exist.sql")


def test_dynamic_sql_flagged_as_warning(agent):
    code_with_dynamic_sql = """
    CREATE OR REPLACE PROCEDURE dyn_proc IS
    BEGIN
        EXECUTE IMMEDIATE 'UPDATE LOAN_ACCOUNT SET status = ''X'' WHERE account_id = ' || 1;
    END;
    /
    """
    warnings = []
    agent.chunk_code(code_with_dynamic_sql, warnings)
    assert any("Dynamic SQL" in w for w in warnings)


def test_cte_embedded_sql_is_preserved(agent):
    warnings = []
    chunks = agent.chunk_code(SAMPLE_CTE_SQL, warnings)
    assert any(chunk.embedded_sql for chunk in chunks)


def test_tsql_try_catch_is_not_duplicated():
    agent = CodeIngestionAgent(max_chunk_chars=2000, dialect="tsql")
    warnings = []
    chunks = agent.chunk_code(SAMPLE_TSQL_TRY_CATCH, warnings, dialect="tsql")
    kinds = [chunk.kind for chunk in chunks]
    assert "main_body" in kinds
    assert "exception" in kinds
    assert sum(1 for chunk in chunks if "SELECT 1;" in chunk.text) == 1


def test_if_else_block_is_kept_together_when_chunking_over_limit():
    agent = CodeIngestionAgent(max_chunk_chars=300, dialect="tsql")
    warnings = []
    text = """
CREATE PROCEDURE dbo.flow_demo
AS
BEGIN
    IF @timekey > 26267 THEN
        UPDATE #DPD
        SET DPD_MAX = CASE
            WHEN DPD_IntService > DPD_NoCredit THEN DPD_IntService
            ELSE DPD_NoCredit
        END;
    ELSE
        UPDATE #DPD
        SET DPD_MAX = CASE
            WHEN DPD_Overdrawn > DPD_Overdue THEN DPD_Overdrawn
            ELSE DPD_Overdue
        END;
    END IF;

    UPDATE #DPD SET DPD_MAX = 0;
    UPDATE #DPD SET DPD_MAX = 1;
    UPDATE #DPD SET DPD_MAX = 2;
    UPDATE #DPD SET DPD_MAX = 3;
    UPDATE #DPD SET DPD_MAX = 4;
END
GO
"""
    chunks = agent.chunk_code(text, warnings, dialect="tsql")
    assert any("IF @timekey > 26267 THEN" in chunk.text and "ELSE" in chunk.text for chunk in chunks)
    assert not any(chunk.text.lstrip().startswith("ELSE") for chunk in chunks)


def test_detect_dialect_marks_postgresql_as_unsupported():
    pg_code = """
    CREATE OR REPLACE FUNCTION demo_fn()
    RETURNS void
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RAISE NOTICE 'hi';
    END;
    $$;
    """
    result = detect_dialect(pg_code, hint="auto")
    assert result.dialect == "UNSUPPORTED"
    assert result.concrete_dialect is None
    assert result.confidence == "low"


def test_detect_dialect_returns_unknown_when_evidence_is_insufficient():
    code = "SELECT 1 FROM dual;"
    result = detect_dialect(code, hint="auto")
    assert result.dialect == "UNKNOWN"
    assert result.concrete_dialect is None
    assert result.confidence == "low"


def test_ingest_text_uses_prevalidated_input_without_rerunning_guardrails(monkeypatch, agent):
    def fail_guardrails(_raw_code):
        raise AssertionError("run_input_guardrails should not be called for prevalidated input")

    monkeypatch.setattr("src.ingestion.ingestion.run_input_guardrails", fail_guardrails)

    detection = DialectDetectionResult(dialect="ORACLE", confidence="high", concrete_dialect="oracle")
    result = agent.ingest_text(
        SAMPLE_PROCEDURE,
        dialect="oracle",
        prevalidated_code=SAMPLE_PROCEDURE,
        prevalidated_warnings=["prevalidated warning"],
        prevalidated_injection_flags=["prevalidated flag"],
        detection_result=detection,
    )

    assert result.dialect == "ORACLE"
    assert "prevalidated warning" in result.parse_warnings
    assert "prevalidated flag" in result.parse_warnings


# --------------------------------------------------------------------------
# Canonical business-name normalization / output identity (generic,
# pattern-based - never a hardcoded date or object name).
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_name,expected",
    [
        ("SMA_MARKING_12122023", "SMA_MARKING"),  # DDMMYYYY date suffix
        ("SMA_MARKING_20231212", "SMA_MARKING"),  # YYYYMMDD date suffix
        ("usp_calc_v2", "usp_calc"),  # version suffix
        ("usp_calc_VERSION12", "usp_calc"),
        ("rpt_summary_final2", "rpt_summary"),  # "final" revision marker
        ("proc_name_bak", "proc_name"),  # backup marker
        ("proc_name_backup", "proc_name"),
        ("proc_v2_20231212", "proc"),  # stacked suffixes
        ("SMA_MARKING", "SMA_MARKING"),  # no suffix - unchanged
        ("GET_STATUS", "GET_STATUS"),  # no suffix - unchanged
        ("12122023", "12122023"),  # entirely numeric - left alone
        ("UNKNOWN_OBJECT", "UNKNOWN_OBJECT"),  # sentinel - left alone
    ],
)
def test_derive_canonical_business_name_is_generic(raw_name, expected):
    assert CodeIngestionAgent.derive_canonical_business_name(raw_name) == expected


def test_ingest_text_populates_schema_and_canonical_object_name(agent):
    code = """
    CREATE OR ALTER PROCEDURE [PRO].[SMA_MARKING_12122023]
    @TIMEKEY INT
    WITH RECOMPILE
    AS
    BEGIN
        SELECT 1;
    END
    GO
    """
    result = agent.ingest_text(code, dialect="tsql")
    # The raw technical name is exactly what the SQL header declares -
    # this must never be altered, since reconciliation/traceability
    # match against it.
    assert result.object_name == "SMA_MARKING_12122023"
    assert result.schema == "PRO"
    # The canonical/business name has the generic date suffix stripped.
    assert result.canonical_object_name == "SMA_MARKING"


def test_build_object_identity_stem_uses_parsed_identity_not_filename():
    ingestion = IngestionResult(
        object_name="SMA_MARKING_12122023",
        object_type="PROCEDURE",
        parameters=[],
        raw_code="",
        chunks=[],
        schema="PRO",
        canonical_object_name="SMA_MARKING",
    )
    # Regardless of what the uploaded file happened to be named, the
    # output identity comes from the parsed object.
    stem = build_object_identity_stem(ingestion, fallback_stem="whatever_the_upload_was_called")
    assert stem == "PRO.SMA_MARKING.StoredProcedure"


def test_build_object_identity_stem_falls_back_when_object_unknown():
    ingestion = IngestionResult(
        object_name="UNKNOWN_OBJECT",
        object_type="UNKNOWN",
        parameters=[],
        raw_code="",
        chunks=[],
        schema="",
        canonical_object_name="UNKNOWN_OBJECT",
    )
    stem = build_object_identity_stem(ingestion, fallback_stem="my_upload")
    assert stem == "my_upload"


def test_build_object_identity_stem_generic_for_other_object_types():
    ingestion = IngestionResult(
        object_name="rpt_summary_final2",
        object_type="VIEW",
        parameters=[],
        raw_code="",
        chunks=[],
        schema="dbo",
        canonical_object_name="rpt_summary",
    )
    assert build_object_identity_stem(ingestion) == "dbo.rpt_summary.View"


# --------------------------------------------------------------------------
# Regression tests for _find_sql_statement_spans' semicolon-free boundary
# detection (see coverage/grounding fix for SMA_Stage_Marking_Simple-style
# T-SQL bodies that never use ";" between statements).
# --------------------------------------------------------------------------

def test_semicolon_free_updates_are_split_into_separate_parseable_statements(agent):
    """Regression test for the real bug: a semicolon-free T-SQL body with
    several UPDATE...SET...(CASE...END)...FROM...WHERE statements back to
    back used to be merged into one unparseable span by
    _find_sql_statement_spans (it only closed a span on ";"). Each
    statement here must come back separately and parse cleanly.
    """
    body = (
        "UPDATE A\n"
        "SET A.SmaStage = (\n"
        "        CASE\n"
        "            WHEN A.OverdueDays BETWEEN 1 AND 30 THEN 'SMA_0'\n"
        "            WHEN A.OverdueDays BETWEEN 31 AND 60 THEN 'SMA_1'\n"
        "            ELSE NULL\n"
        "        END\n"
        "    )\n"
        "FROM PRO.AccountCal A\n"
        "WHERE A.OverdueDays > 0\n"
        "\n"
        "UPDATE A\n"
        "SET A.FlagSma = (\n"
        "        CASE\n"
        "            WHEN A.SmaStage IS NOT NULL THEN 'Y'\n"
        "            ELSE 'N'\n"
        "        END\n"
        "    )\n"
        "FROM PRO.AccountCal A\n"
    )
    spans = CodeIngestionAgent._find_sql_statement_spans(body)
    assert len(spans) == 2
    first = body[spans[0][0]:spans[0][1]].strip()
    second = body[spans[1][0]:spans[1][1]].strip()
    assert first.startswith("UPDATE A")
    assert "SmaStage" in first
    assert "FlagSma" not in first
    assert second.startswith("UPDATE A")
    assert "FlagSma" in second


def test_semicolon_free_update_before_block_end_is_bounded_by_end(agent):
    """A statement followed directly by a block-terminating END (e.g. the
    end of a TRY block) with no semicolon and no following statement
    keyword must still be closed at the END, not left open until EOF
    (which would swallow trailing BEGIN CATCH / END CATCH text into the
    statement and break parsing)."""
    body = (
        "BEGIN TRY\n"
        "UPDATE PRO.RunStatus\n"
        "SET COMPLETED = 'Y', ErrorDate = NULL\n"
        "WHERE ProcessName = 'demo'\n"
        "END TRY\n"
        "BEGIN CATCH\n"
        "UPDATE PRO.RunStatus\n"
        "SET COMPLETED = 'N', ErrorDate = GETDATE()\n"
        "WHERE ProcessName = 'demo'\n"
        "END CATCH\n"
    )
    spans = CodeIngestionAgent._find_sql_statement_spans(body)
    assert len(spans) == 2
    first = body[spans[0][0]:spans[0][1]].strip()
    second = body[spans[1][0]:spans[1][1]].strip()
    assert "END TRY" not in first
    assert "BEGIN CATCH" not in first
    assert "COMPLETED = 'Y'" in first
    assert "END CATCH" not in second
    assert "COMPLETED = 'N'" in second


def test_bare_case_end_is_not_mistaken_for_a_block_boundary(agent):
    """A CASE...END with no wrapping parentheses must stay intact as one
    statement - the END that closes the CASE must never be treated as a
    block-terminating END that would incorrectly split the statement."""
    body = (
        "UPDATE t SET x = CASE WHEN a = 1 THEN 'Y' ELSE 'N' END\n"
        "UPDATE t2 SET y = 1 WHERE z = 2\n"
    )
    spans = CodeIngestionAgent._find_sql_statement_spans(body)
    assert len(spans) == 2
    first = body[spans[0][0]:spans[0][1]].strip()
    assert first == "UPDATE t SET x = CASE WHEN a = 1 THEN 'Y' ELSE 'N' END"


def test_update_inside_if_begin_end_block_is_isolated_by_the_block_end(agent):
    """A single UPDATE wrapped in IF EXISTS(...) BEGIN ... END must be
    recognized as its own statement bounded by that END, and a following
    statement after the block must not be merged into it."""
    body = (
        "IF EXISTS (SELECT 1 FROM t)\n"
        "BEGIN\n"
        "    UPDATE t SET x = 1 WHERE y = 2\n"
        "END\n"
        "UPDATE t2 SET z = 3\n"
    )
    spans = CodeIngestionAgent._find_sql_statement_spans(body)
    assert len(spans) == 2
    assert body[spans[0][0]:spans[0][1]].strip() == "UPDATE t SET x = 1 WHERE y = 2"
    assert body[spans[1][0]:spans[1][1]].strip() == "UPDATE t2 SET z = 3"


def test_semicolon_terminated_statements_are_unaffected(agent):
    """Existing semicolon-terminated behavior must be unchanged."""
    body = "UPDATE t SET x = 1;\nUPDATE t2 SET y = 2;\n"
    spans = CodeIngestionAgent._find_sql_statement_spans(body)
    assert len(spans) == 2
    assert body[spans[0][0]:spans[0][1]].strip() == "UPDATE t SET x = 1;"
    assert body[spans[1][0]:spans[1][1]].strip() == "UPDATE t2 SET y = 2;"


def test_sma_stage_marking_style_statements_structurally_parse_end_to_end(agent):
    """Full end-to-end regression using the exact statement shapes from the
    real SMA_Stage_Marking_Simple bug report: every statement must come
    back validated (no 'Could not fully structurally parse' warning)."""
    body = (
        "UPDATE A\n"
        "SET A.SmaStage = (\n"
        "        CASE\n"
        "            WHEN A.OverdueDays BETWEEN 1 AND 30 THEN 'SMA_0'\n"
        "            WHEN A.OverdueDays BETWEEN 31 AND 60 THEN 'SMA_1'\n"
        "            ELSE NULL\n"
        "        END\n"
        "    )\n"
        "FROM PRO.AccountCal A\n"
        "WHERE A.OverdueDays > 0\n"
        "\n"
        "UPDATE PRO.RunStatus\n"
        "SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE()\n"
        "WHERE ProcessName = 'demo'\n"
        "END CATCH\n"
    )
    warnings = []
    stmts = agent._extract_and_validate_sql(body, warnings, dialect="tsql")
    assert len(stmts) == 2
    assert not any("Could not fully structurally parse" in w for w in warnings)

def test_header_param_with_as_keyword_and_output_direction_is_extracted():
    # Regression test for the client-corpus finding: "@Date as Varchar(20)"
    # (an "AS" between parameter name and datatype - unusual but valid
    # T-SQL, seen throughout the corpus, e.g. ACLMainRunProcessForDummy)
    # previously made the "AS"-detection logic treat the very first "AS"
    # found after the object name as the body-opening keyword, truncating
    # the parameter list to a single word. It also lost the OUTPUT
    # direction entirely once the default-value literal was masked.
    agent = CodeIngestionAgent()
    sql = (
        "CREATE PROC [PRO].[ACLMainRunProcessForDummy]\n"
        "@Date as Varchar(20)\n"
        ",@Result as Int = 0 OutPut\n"
        "As\n"
        "BEGIN\n"
        "SELECT 1\n"
        "END"
    )
    masked = agent._mask_strings_and_comments(sql, mask_brackets=False)
    params, complete, saw_candidate = agent._extract_parameters_tsql_detailed(sql, masked)
    assert complete
    assert saw_candidate
    assert [p.name for p in params] == ["@Date", "@Result"]
    assert [p.datatype for p in params] == ["VARCHAR(20)", "INT"]
    assert [p.direction for p in params] == ["IN", "OUT"]


def test_header_trailing_inline_comment_does_not_swallow_first_parameter():
    # Regression test: "CREATE PROCEDURE ... --26857" (a trailing inline
    # comment on the header line, seen in the client corpus, e.g.
    # Final_AssetClass_Npadate) has no comma before it, so splitting the
    # RAW parameter block glued the comment text onto the front of the
    # first parameter ("--26857\n@TIMEKEY INT"), which then failed the
    # "starts with @" check and silently dropped a real parameter. A
    # masked default-value literal ('N') immediately followed by "with
    # recompile" must also not be lost.
    agent = CodeIngestionAgent()
    sql = (
        "CREATE PROCEDURE [PRO].[Final_AssetClass_Npadate] --26857\n"
        "@TIMEKEY INT ,\n"
        "@FlgPreErosion char(1)='N'\n"
        "with recompile\n"
        "AS\n"
        "BEGIN\n"
        "SELECT 1\n"
        "END"
    )
    masked = agent._mask_strings_and_comments(sql, mask_brackets=False)
    params, complete, saw_candidate = agent._extract_parameters_tsql_detailed(sql, masked)
    assert complete
    assert [p.name for p in params] == ["@TIMEKEY", "@FlgPreErosion"]
    assert [p.datatype for p in params] == ["INT", "CHAR(1)"]


def test_genuinely_empty_default_value_still_reports_failure():
    # Companion safety check for the two regression tests above: a
    # genuinely malformed default (nothing at all follows "=", not even a
    # masked literal) must still be reported as unparseable, not silently
    # accepted just because the fix above learned to recover masked
    # defaults elsewhere.
    agent = CodeIngestionAgent()
    sql = "CREATE PROCEDURE dbo.bad_params\n(\n    @status VARCHAR(20) = \n)\nAS\nBEGIN\n    SELECT 1;\nEND"
    masked = agent._mask_strings_and_comments(sql, mask_brackets=False)
    params, complete, saw_candidate = agent._extract_parameters_tsql_detailed(sql, masked)
    assert not complete
    assert params == []


def test_commented_out_dml_is_stripped_before_reaching_the_llm():
    # Regression test for the client-corpus finding: 2,417 commented-out
    # DML lines across 80/91 files were passed to the extraction prompt as
    # if they were ordinary code content (extraction's injection-defense
    # instruction to "extract [comment content] the same way you would any
    # other code" made no distinction between prose and dead SQL). A
    # commented-out UPDATE/INSERT/DELETE/MERGE must never reach the model
    # as candidate active logic; ordinary business commentary must be left
    # completely untouched.
    source = (
        "-- Rule 1: classify the SMA stage by overdue days\n"
        "UPDATE A SET A.SmaStage = 'X' FROM PRO.AccountCal A\n"
        "\n"
        "-- Old logic, replaced 2020-12-31:\n"
        "-- UPDATE A SET A.SmaStage = DATEADD(DAY, -A.OverdueDays, @ProcessDate)\n"
        "-- FROM PRO.AccountCal A WHERE A.OverdueDays > 30\n"
        "\n"
        "-- TODO: consider adding an UPDATE trigger here for auditing\n"
    )
    sanitized, snippets = strip_inactive_code_for_llm(source)

    # Length/line structure must be preserved exactly - downstream char/line
    # offset tracking depends on it.
    assert len(sanitized) == len(source)
    assert sanitized.count("\n") == source.count("\n")

    # The real business comment and the prose TODO (which only *mentions*
    # UPDATE, isn't one) must survive completely untouched.
    assert "-- Rule 1: classify the SMA stage by overdue days" in sanitized
    assert "UPDATE A SET A.SmaStage = 'X' FROM PRO.AccountCal A" in sanitized
    assert "-- TODO: consider adding an UPDATE trigger here for auditing" in sanitized

    # The commented-out UPDATE must be gone from what the LLM sees...
    assert "DATEADD(DAY, -A.OverdueDays" not in sanitized
    assert "INACTIVE CODE REMOVED" in sanitized
    # ...but preserved separately for verification-report-only surfacing.
    assert len(snippets) == 1
    assert "DATEADD(DAY, -A.OverdueDays" in snippets[0]


def test_inactive_code_detection_requires_both_dml_keyword_and_code_shape():
    # A comment that merely mentions a DML keyword in prose (no
    # assignment, no qualified identifier, no bind variable, no
    # terminator) must not be flagged - only text that actually looks like
    # commented-out code should be.
    prose_only = "-- We should probably UPDATE the documentation for this someday\n"
    assert find_inactive_code_blocks(prose_only) == []


def test_find_called_procedures_orders_and_excludes_dynamic_sql():
    # Regression test built from the real client-corpus finding: one
    # orchestrator procedure makes 23 EXEC calls and contains almost no
    # business logic of its own - its entire business meaning IS the call
    # sequence, which the report had no way to show before this. Also
    # verifies commented-out EXEC calls and dynamic-SQL EXEC forms
    # (EXEC(...), EXEC @var, sp_executesql) are correctly excluded.
    agent = CodeIngestionAgent()
    sql = (
        "CREATE PROCEDURE PRO.Orchestrator\n"
        "AS\n"
        "BEGIN\n"
        "EXEC PRO.StepOne @TimeKey=@TimeKey\n"
        "EXEC [PRO].[StepTwo] @TimeKey=@TimeKey\n"
        "EXEC  PRO.[StepThree] @TimeKey=@TimeKey\n"
        "--EXEC PRO.DisabledStep @TimeKey=@TimeKey\n"
        "EXEC @rc = dbo.StepFour @account_id\n"
        "EXEC (@dynamic_sql)\n"
        "EXEC sp_executesql @sql\n"
        "END\n"
    )
    calls = agent.find_called_procedures(sql, dialect="tsql")
    assert [c["name"] for c in calls] == [
        "PRO.StepOne",
        "[PRO].[StepTwo]",
        "PRO.[StepThree]",
        "dbo.StepFour",
    ]
    assert calls[0]["arguments"] == "@TimeKey=@TimeKey"
    assert calls[3]["return_variable"] == "@rc"
    # Order must be preserved (source order, not alphabetical or grouped).
    assert [int(c["line"]) for c in calls] == sorted(int(c["line"]) for c in calls)


def test_find_hardcoded_dates_excludes_commented_out_literals():
    # Regression test built from the real client-corpus finding: 293
    # hardcoded date literals in live code across 28/91 files - usually a
    # deliberate cutover boundary or a forgotten test value, and typically
    # the first thing an audit reviewer asks about. A date-shaped literal
    # that only appears inside a commented-out statement must not be
    # reported as if it were live.
    agent = CodeIngestionAgent()
    sql = (
        "UPDATE A SET A.ContiExcessDt = '1900-01-01' WHERE A.Flag = 'Y'\n"
        "\n"
        "-- Old cutover logic, no longer used:\n"
        "-- UPDATE A SET A.ContiExcessDt = '2020-12-31' WHERE A.Flag = 'N'\n"
        "\n"
        "UPDATE A SET A.NextReviewDt = '01/01/1900'\n"
    )
    dates = agent.find_hardcoded_dates(sql)
    values = [d["value"] for d in dates]
    assert "1900-01-01" in values
    assert "01/01/1900" in values
    assert "2020-12-31" not in values
    assert len(dates) == 2