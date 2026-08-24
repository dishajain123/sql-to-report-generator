"""
Unit tests for agents.ingestion.CodeIngestionAgent.

Run with:  pytest tests/test_ingestion.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from agents.ingestion import CodeIngestionAgent


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


def test_extract_parameters(agent):
    params = agent.extract_parameters(SAMPLE_PROCEDURE)
    assert len(params) == 1
    assert params[0].name == "p_account_id"
    assert params[0].direction == "IN"
    assert params[0].datatype == "NUMBER"


def test_chunk_code_produces_chunks(agent):
    warnings = []
    chunks = agent.chunk_code(SAMPLE_PROCEDURE, warnings)
    assert len(chunks) > 0
    kinds = {c.kind for c in chunks}
    # We expect at least a main body/nested block and an exception section
    assert "exception" in kinds


def test_chunk_code_respects_max_size(agent):
    big_code = SAMPLE_PROCEDURE + ("\n-- padding comment line" * 500)
    warnings = []
    chunks = agent.chunk_code(big_code, warnings)
    for c in chunks:
        assert len(c.text) <= agent.max_chunk_chars + 200  # small tolerance for statement boundaries


def test_ingest_full_file(tmp_path, agent):
    sql_file = tmp_path / "sample.sql"
    sql_file.write_text(SAMPLE_PROCEDURE, encoding="utf-8")

    result = agent.ingest(str(sql_file))
    assert result.object_type == "PROCEDURE"
    assert result.object_name == "classify_npa_and_provision"
    assert len(result.parameters) == 1
    assert len(result.chunks) > 0


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
