"""Tests for conservative source-order dependency edges."""

from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent
from src.validation.dependencies import build_statement_dependencies
from tests.test_reconciliation import _make_ingestion


def _op(statement_id, operation, table, line, *, fields=None, predicate=None, statement_kind=""):
    return {
        "statement_id": statement_id,
        "source_statement_id": statement_id,
        "operation": operation,
        "statement_kind": statement_kind or operation,
        "table": table,
        "target_columns": list(fields or []),
        "assigned_values": [
            {"column": field, "value": "literal"}
            for field in fields or []
        ],
        "where_predicate": predicate,
        "source_line_start": line,
        "source_line_end": line,
        "source_chunk_id": "chunk_1",
    }


def test_temp_table_write_then_read_creates_one_confirmed_edge():
    graph = build_statement_dependencies([
        _op("s1", "INSERT", "#stage", 10, fields=["ACCOUNT_ID"]),
        _op("s2", "READ", "#stage", 20, statement_kind="SELECT"),
    ])

    assert graph["edge_count"] == 1
    edge = graph["edges"][0]
    assert edge["type"] == "temp_write_to_read"
    assert edge["confidence"] == "high"
    assert edge["from"]["statement_id"] == "s1"
    assert edge["to"]["statement_id"] == "s2"


def test_sequential_unconditional_updates_identify_later_override():
    graph = build_statement_dependencies([
        _op("s1", "UPDATE", "ACCOUNT", 10, fields=["STATUS"]),
        _op("s2", "UPDATE", "ACCOUNT", 20, fields=["STATUS"]),
    ])

    assert [edge["type"] for edge in graph["edges"]] == ["later_update_overrides_field"]
    assert graph["edges"][0]["from"]["order"] < graph["edges"][0]["to"]["order"]


def test_independent_updates_do_not_create_dependencies():
    graph = build_statement_dependencies([
        _op("s1", "UPDATE", "ACCOUNT", 10, fields=["STATUS"]),
        _op("s2", "UPDATE", "ACCOUNT", 20, fields=["BALANCE"]),
    ])

    assert graph["edges"] == []
    assert graph["unresolved"] == []


def test_multiple_temporary_tables_do_not_cross_link():
    graph = build_statement_dependencies([
        _op("s1", "INSERT", "#first", 10),
        _op("s2", "INSERT", "#second", 20),
        _op("s3", "READ", "#first", 30, statement_kind="SELECT"),
        _op("s4", "READ", "#second", 40, statement_kind="SELECT"),
    ])

    pairs = {(edge["from"]["table"], edge["to"]["table"]) for edge in graph["edges"]}
    assert pairs == {("#first", "#first"), ("#second", "#second")}


def test_staging_write_then_merge_is_explicitly_identified():
    graph = build_statement_dependencies([
        _op("s1", "INSERT", "staging_accounts", 10),
        _op("s2", "READ", "staging_accounts", 20, statement_kind="MERGE"),
        _op("s2", "MERGE", "ACCOUNT", 20, fields=["STATUS"], statement_kind="MERGE"),
    ])

    assert any(edge["type"] == "staging_write_to_merge" for edge in graph["edges"])
    edge = next(edge for edge in graph["edges"] if edge["type"] == "staging_write_to_merge")
    assert edge["from"]["table"] == "staging_accounts"
    assert edge["to"]["statement_id"] == "s2"


def test_conditional_same_field_overlap_remains_unresolved():
    graph = build_statement_dependencies([
        _op("s1", "UPDATE", "ACCOUNT", 10, fields=["STATUS"], predicate="ACCOUNT_ID = 1"),
        _op("s2", "UPDATE", "ACCOUNT", 20, fields=["STATUS"], predicate="ACCOUNT_ID = 2"),
    ])

    assert graph["edges"] == []
    assert graph["unresolved_count"] == 1
    assert graph["unresolved"][0]["type"] == "conditional_field_overlap"


def test_confirmed_edges_are_passed_to_synthesis_but_unresolved_candidates_are_not():
    graph = build_statement_dependencies([
        _op("s1", "INSERT", "#stage", 10),
        _op("s2", "READ", "#stage", 20, statement_kind="SELECT"),
    ])
    payload = RuleSynthesizerAgent._build_compact_synthesis_payload({"statement_dependencies": graph})

    assert len(payload["statement_dependencies"]["edges"]) == 1
    assert "unresolved" not in payload["statement_dependencies"]

    verification = ReportFormatterAgent()._statement_dependencies_section({"statement_dependencies": graph})
    assert "## Confirmed Statement Dependencies" in verification
    assert "temp_write_to_read" in verification
    assert "Confidence" in verification

