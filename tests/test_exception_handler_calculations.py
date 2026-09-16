"""Regression tests for excluding exception/error-handling bookkeeping
(e.g. a retry-counter increment on a run-status row) from the Calculations
section, based on which source block it came from - not any field name.

Root cause (traced against samples/07_DPD_Bucket_Classification.sql, a
real generated report): a `COUNT = ISNULL(COUNT, 0) + 1` retry-counter
inside a `BEGIN CATCH ... END CATCH` block was rendered as a business
Calculation, duplicating content already shown verbatim under Exception
Handling. Chunk-level tagging turned out not to work for this real file
(its whole procedure body, CATCH block included, was fused into one
`nested_block` chunk) - the fix is a deterministic source-span classifier
instead. Fixture data below is a generic reconstruction, not tied to any
real procedure/table/column name in implementation code.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import _exclude_exception_handler_calculations
from src.validation.semantic_validation import find_exception_handler_spans


# --------------------------------------------------------------------------
# find_exception_handler_spans
# --------------------------------------------------------------------------

_TSQL_SOURCE = """
CREATE PROCEDURE dbo.DemoProc
AS
BEGIN
    BEGIN TRY
        UPDATE t SET Balance = Balance - 100 WHERE AccountId = 1
    END TRY
    BEGIN CATCH
        UPDATE dbo.RunStatus
        SET COMPLETED = 'N', ErrorDate = GETDATE(), RetryCount = ISNULL(RetryCount, 0) + 1
        WHERE ProcessName = 'DemoProc'
    END CATCH
END
"""

_ORACLE_SOURCE = """
CREATE OR REPLACE PROCEDURE demo_proc AS
BEGIN
    UPDATE t SET balance = balance - 100 WHERE account_id = 1;
EXCEPTION
    WHEN OTHERS THEN
        UPDATE run_status
        SET completed = 'N', retry_count = NVL(retry_count, 0) + 1
        WHERE process_name = 'demo_proc';
END;
"""


def test_finds_tsql_catch_block_body():
    spans = find_exception_handler_spans(_TSQL_SOURCE, dialect="tsql")
    assert len(spans) == 1
    start, end = spans[0]
    body = _TSQL_SOURCE[start:end]
    assert "RetryCount" in body
    assert "BEGIN CATCH" not in body
    assert "END CATCH" not in body


def test_finds_oracle_exception_block_body():
    spans = find_exception_handler_spans(_ORACLE_SOURCE, dialect="oracle")
    assert len(spans) == 1
    start, end = spans[0]
    body = _ORACLE_SOURCE[start:end]
    assert "retry_count" in body
    assert "WHEN OTHERS" in body  # inside the handler body, correctly included


def test_no_handler_present_returns_empty():
    source = "UPDATE t SET x = 1 WHERE y = 2"
    assert find_exception_handler_spans(source, dialect="tsql") == []


def test_string_literal_containing_catch_keyword_is_not_mistaken_for_a_block():
    source = "UPDATE t SET Note = 'Please BEGIN CATCH your breath' WHERE id = 1"
    assert find_exception_handler_spans(source, dialect="tsql") == []


# --------------------------------------------------------------------------
# pipeline._exclude_exception_handler_calculations
# --------------------------------------------------------------------------


def test_calculation_inside_catch_block_is_excluded():
    spans = find_exception_handler_spans(_TSQL_SOURCE, dialect="tsql")
    calculations = [
        {
            "name": "RetryCount",
            "expression": "ISNULL(RetryCount, 0) + 1",
            "output": "RetryCount",
            "source_evidence": ["RetryCount = ISNULL(RetryCount, 0) + 1"],
        }
    ]
    result = _exclude_exception_handler_calculations(calculations, _TSQL_SOURCE, spans)
    assert result == []


def test_calculation_outside_catch_block_is_kept():
    spans = find_exception_handler_spans(_TSQL_SOURCE, dialect="tsql")
    calculations = [
        {
            "name": "Balance",
            "expression": "Balance - 100",
            "output": "Balance",
            "source_evidence": ["UPDATE t SET Balance = Balance - 100 WHERE AccountId = 1"],
        }
    ]
    result = _exclude_exception_handler_calculations(calculations, _TSQL_SOURCE, spans)
    assert result == calculations


def test_mixed_calculations_only_the_handler_one_is_dropped():
    spans = find_exception_handler_spans(_TSQL_SOURCE, dialect="tsql")
    real_calc = {
        "name": "Balance", "expression": "Balance - 100", "output": "Balance",
        "source_evidence": ["UPDATE t SET Balance = Balance - 100 WHERE AccountId = 1"],
    }
    bookkeeping_calc = {
        "name": "RetryCount", "expression": "ISNULL(RetryCount, 0) + 1", "output": "RetryCount",
        "source_evidence": ["RetryCount = ISNULL(RetryCount, 0) + 1"],
    }
    result = _exclude_exception_handler_calculations([real_calc, bookkeeping_calc], _TSQL_SOURCE, spans)
    assert result == [real_calc]


def test_no_handler_spans_leaves_calculations_untouched():
    calculations = [{"name": "X", "expression": "X + 1", "source_evidence": ["X = X + 1"]}]
    assert _exclude_exception_handler_calculations(calculations, _TSQL_SOURCE, []) == calculations


def test_falls_back_to_expression_when_no_source_evidence_present():
    spans = find_exception_handler_spans(_TSQL_SOURCE, dialect="tsql")
    calculations = [{"name": "RetryCount", "expression": "ISNULL(RetryCount, 0) + 1"}]
    result = _exclude_exception_handler_calculations(calculations, _TSQL_SOURCE, spans)
    assert result == []
