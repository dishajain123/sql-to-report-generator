"""Tests for deterministic orchestration gate extraction."""

from src.parsing.process_gates import extract_process_gates, summarize_process_gates
from src.output.report_formatter import ReportFormatterAgent


ORCHESTRATOR = """
CREATE PROCEDURE PRO.MainRun AS
BEGIN

IF (SELECT Completed FROM PRO.AclRunningProcessStatus WHERE RunningProcessName='StepA')='Y'
AND (SELECT Completed FROM PRO.AclRunningProcessStatus WHERE RunningProcessName='StepB')='N'
BEGIN
    INSERT INTO PRO.ProcessMonitor(UserID,Description,MODE)
    SELECT ORIGINAL_LOGIN(),'StepB','RUNNING'
    EXEC PRO.StepB @TIMEKEY=@TIMEKEY
    UPDATE PRO.PROCESSMONITOR SET MODE='COMPLETE' WHERE DESCRIPTION='StepB'
END

IF (SELECT Completed FROM PRO.AclRunningProcessStatus WHERE RunningProcessName='StepB')='N'
BEGIN
  RETURN;
END
ELSE
BEGIN
    UPDATE BANDAUDITSTATUS SET CompletedCount=CompletedCount+1
END

IF (SELECT Completed FROM PRO.AclRunningProcessStatus WHERE RunningProcessName='StepB')='Y'
AND (SELECT Completed FROM PRO.AclRunningProcessStatus WHERE RunningProcessName='StepC')='N'
BEGIN
    EXEC PRO.StepC @TIMEKEY=@TIMEKEY
END

END
"""


PLAIN_BUSINESS = """
CREATE PROCEDURE PRO.Classify AS
BEGIN
    UPDATE PRO.ACCOUNTCAL
    SET AssetClass = CASE WHEN DpdDays > 90 THEN 'NPA' ELSE 'STD' END

    IF @Flag = 'Y'
        UPDATE PRO.ACCOUNTCAL SET Reviewed = 1
    ELSE
        UPDATE PRO.ACCOUNTCAL SET Reviewed = 0
END
"""


def test_extracts_run_steps_in_source_order():
    gates = extract_process_gates(ORCHESTRATOR)
    runs = [g for g in gates if g["gate_type"] == "run_step"]
    assert [g["step_name"] for g in runs] == ["StepB", "StepC"]
    assert runs[0]["executed_procedures"] == ["PRO.StepB"]


def test_detects_abort_gate():
    gates = extract_process_gates(ORCHESTRATOR)
    aborts = [g for g in gates if g["gate_type"] == "abort_if_incomplete"]
    assert len(aborts) == 1
    assert aborts[0]["aborts_run"] is True
    assert aborts[0]["executed_procedures"] == []


def test_nested_ifs_are_not_double_counted():
    """A guard inside an already-emitted block is part of that step, not a
    new one - the regression that produced duplicate gates."""
    gates = extract_process_gates(ORCHESTRATOR)
    for previous, current in zip(gates, gates[1:]):
        assert current["source_char_start"] >= previous["source_char_end"]


def test_precondition_text_is_business_language():
    gates = extract_process_gates(ORCHESTRATOR)
    text = gates[0]["precondition_text"]
    assert "has completed" in text
    assert "has not yet completed" in text
    for jargon in ("SELECT", "WHERE", "='Y'", "='N'"):
        assert jargon not in text


def test_summary_reports_order_and_resumability():
    summary = summarize_process_gates(extract_process_gates(ORCHESTRATOR))
    assert summary["execution_order"] == ["StepB", "StepC"]
    assert summary["step_count"] == 2
    assert summary["resumable"] is True
    assert summary["aborting_gates"] == 1
    assert summary["status_tables"] == ["PRO.AclRunningProcessStatus"]


def test_no_gates_for_ordinary_business_procedure():
    """The safety property: normal CASE/IF logic must never be
    reinterpreted as orchestration."""
    assert extract_process_gates(PLAIN_BUSINESS) == []
    assert summarize_process_gates([]) == {}


def test_non_tsql_dialect_is_a_no_op():
    assert extract_process_gates(ORCHESTRATOR, dialect="oracle") == []


def test_empty_and_malformed_input_is_safe():
    for value in ("", None, "not sql at all", "IF ("):
        assert extract_process_gates(value) == []


def test_formatter_section_omitted_without_gates():
    assert ReportFormatterAgent._process_gates_section(None) == ""
    assert ReportFormatterAgent._process_gates_section({}) == ""
    assert ReportFormatterAgent._process_gates_section({"process_gates": []}) == ""


def test_formatter_section_renders_steps():
    gates = extract_process_gates(ORCHESTRATOR)
    section = ReportFormatterAgent._process_gates_section(
        {"process_gates": gates, "process_gate_summary": summarize_process_gates(gates)}
    )
    assert "## Process Sequence and Run Conditions" in section
    assert "StepB" in section and "StepC" in section
    assert "re-run safely" in section