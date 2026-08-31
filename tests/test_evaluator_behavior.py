from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.evaluator import (
    ActualArtifacts,
    _filter_supporting_reads,
    _payloads_equal_ignoring_generated_at,
    compare_case,
)


def _actual_artifacts() -> ActualArtifacts:
    return ActualArtifacts(
        dialect="ORACLE",
        object_type="procedure",
        object_name="demo_proc",
        parameters=[],
        tables_read=[],
        tables_written=[],
        operations=[],
        business_rules=[],
        ambiguities=[],
        important_fields=[],
        source_issues=[],
        parser_mode="deterministic",
    )


def test_generated_at_only_difference_is_ignored_for_baseline_comparison():
    baseline = {
        "generated_at": "2026-08-28T11:00:56.616677+00:00",
        "mode": "deterministic",
        "results": [{"case_id": "case_1", "status": "PASS", "checks": {"dialect": {"match": True}}}],
        "summary": {"overall_status": "PASS", "case_count": 1},
    }
    current = {
        "generated_at": "2026-08-31T06:00:00.000000+00:00",
        "mode": "deterministic",
        "results": [{"case_id": "case_1", "status": "PASS", "checks": {"dialect": {"match": True}}}],
        "summary": {"overall_status": "PASS", "case_count": 1},
    }

    assert _payloads_equal_ignoring_generated_at(baseline, current)


def test_baseline_comparison_detects_real_content_changes():
    baseline = {
        "generated_at": "2026-08-28T11:00:56.616677+00:00",
        "mode": "deterministic",
        "results": [{"case_id": "case_1", "status": "PASS", "checks": {"dialect": {"match": True}}}],
        "summary": {"overall_status": "PASS", "case_count": 1},
    }
    current = {
        "generated_at": "2026-08-31T06:00:00.000000+00:00",
        "mode": "deterministic",
        "results": [{"case_id": "case_1", "status": "FAIL", "checks": {"dialect": {"match": False}}}],
        "summary": {"overall_status": "FAIL", "case_count": 1},
    }

    assert not _payloads_equal_ignoring_generated_at(baseline, current)


def test_compare_case_marks_matching_deterministic_case_as_pass():
    expected = {
        "case_id": "case_1",
        "dialect": "oracle",
        "object_type": "procedure",
        "parameters": [],
        "tables_read": [],
        "tables_written": [],
        "operations": [],
        "ambiguities": [],
        "important_fields": [],
    }

    result = compare_case(expected, _actual_artifacts(), live_mode=False)
    assert result.status == "PASS"


def test_filter_supporting_reads_can_preserve_merge_target_read():
    table_operations = [
        {"operation": "MERGE", "table": "dbo.npa_provision", "statement_id": "stmt_1"},
        {"operation": "READ", "table": "dbo.npa_provision", "statement_id": "stmt_1"},
        {"operation": "READ", "table": "dbo.staging_provisioning", "statement_id": "stmt_1"},
    ]
    reads = [table_operations[1], table_operations[2]]

    filtered = _filter_supporting_reads(table_operations, reads, keep_merge_target=True)
    assert [row["table"] for row in filtered] == ["dbo.npa_provision", "dbo.staging_provisioning"]
