"""
Regression tests for glossary generation.

The glossary was rewritten from an auto-scraped dump of every technical
identifier (verbose, hard to read, often not actually "hard" terms) to a
small, curated set of genuinely domain-specific banking/regulatory terms.
These tests verify that contract: only terms that actually appear in the
object's source are surfaced, the list is capped at 5, and the output
stays a plain two-column table with no leaked technical jargon.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.ingestion import IngestionResult, Parameter
from agents.report_formatter import ReportFormatterAgent


def _make_ingestion(raw_code: str) -> IngestionResult:
    return IngestionResult(
        object_name="SMA_MARKING_12122023",
        object_type="PROCEDURE",
        parameters=[Parameter(name="@TIMEKEY", direction="IN", datatype="INT")],
        raw_code=raw_code,
        chunks=[],
        dialect="tsql",
        parameter_parse_status="parameterized",
    )


def test_glossary_only_surfaces_terms_actually_present_in_source():
    formatter = ReportFormatterAgent()
    raw_code = (
        "UPDATE #DPD SET DPD_IntService = 0 WHERE ISNULL(DPD_IntService, 0) < 0; "
        "UPDATE PRO.AccountCal SET SMA_CLASS = 'STD' WHERE FinalAssetClassAlt_Key = 1;"
    )
    report = formatter._glossary_section(_make_ingestion(raw_code))

    assert report.startswith("## Glossary")
    assert "| Term | What it means |" in report
    assert "**DPD**" in report
    assert "**Asset Classification Codes" in report
    # These never appear in the source above, so they must not be surfaced.
    assert "**NPA**" not in report
    assert "**UCIF**" not in report
    assert "**IRAC Norms**" not in report


def test_glossary_is_capped_at_five_terms():
    formatter = ReportFormatterAgent()
    # Every curated term's pattern present at once - should still cap at 5.
    raw_code = "DPD NPA SMA UCIF STD IRAC"
    report = formatter._glossary_section(_make_ingestion(raw_code))

    term_rows = [line for line in report.splitlines() if line.startswith("| **")]
    assert len(term_rows) == 5


def test_glossary_placeholder_when_no_domain_terms_present():
    formatter = ReportFormatterAgent()
    raw_code = "UPDATE PRO.SOME_TABLE SET FLAG = 1 WHERE ID = 1"
    report = formatter._glossary_section(_make_ingestion(raw_code))

    assert "## Glossary" in report
    assert "No domain-specific terms" in report
    assert "| Term |" not in report


def test_glossary_does_not_false_positive_on_substrings():
    formatter = ReportFormatterAgent()
    # "STDDEV" and "SUBSTRING" contain SUB/STD as substrings but must not
    # trigger the asset-classification-code entry (word-boundary check).
    raw_code = "SELECT STDDEV(amount), SUBSTRING(name, 1, 3) FROM PRO.SOME_TABLE"
    report = formatter._glossary_section(_make_ingestion(raw_code))

    assert "No domain-specific terms" in report
    assert "Asset Classification Codes" not in report


def test_glossary_table_has_no_leaked_technical_jargon():
    formatter = ReportFormatterAgent()
    raw_code = "SMA_CLASS DPD NPA"
    report = formatter._glossary_section(_make_ingestion(raw_code))

    assert "confidence" not in report.lower()
    assert "provenance" not in report.lower()
    assert "active predicate" not in report.lower()