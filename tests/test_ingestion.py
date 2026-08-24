"""
Unit tests for agents.ingestion.CodeIngestionAgent.

Run with:  pytest tests/test_ingestion.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from agents.ingestion import CodeIngestionAgent
from agents.ingestion import CodeChunk
from agents.report_formatter import ReportFormatterAgent
from guardrails import ground_extraction_against_source
from dialect_detector import DialectDetectionResult, UnsupportedDialectError, detect_dialect
from technical_sql_ops import extract_table_operations_from_chunks, split_table_operations


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


def test_table_sections_do_not_turn_missing_predicates_into_filters():
    report = ReportFormatterAgent()._tables_read(
        {
            "tables_read": [
                {
                    "statement_id": "00_main_body:stmt_01",
                    "table": "SYSDAYMATRIX",
                    "table_alias": "",
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
                    "table": "#DPD",
                    "table_alias": "A",
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
        }
    )
    assert "Always, on each execution" not in report
    assert "None" in report


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


def test_detect_dialect_rejects_postgresql():
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
    with pytest.raises(UnsupportedDialectError):
        detect_dialect(pg_code, hint="auto")


def test_ingest_text_uses_prevalidated_input_without_rerunning_guardrails(monkeypatch, agent):
    def fail_guardrails(_raw_code):
        raise AssertionError("run_input_guardrails should not be called for prevalidated input")

    monkeypatch.setattr("agents.ingestion.run_input_guardrails", fail_guardrails)

    detection = DialectDetectionResult(dialect="oracle", confidence="high")
    result = agent.ingest_text(
        SAMPLE_PROCEDURE,
        dialect="oracle",
        prevalidated_code=SAMPLE_PROCEDURE,
        prevalidated_warnings=["prevalidated warning"],
        prevalidated_injection_flags=["prevalidated flag"],
        detection_result=detection,
    )

    assert result.dialect == "oracle"
    assert "prevalidated warning" in result.parse_warnings
    assert "prevalidated flag" in result.parse_warnings
