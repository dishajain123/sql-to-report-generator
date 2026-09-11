"""Behavior regressions for SQL decisions beyond searched CASE expressions."""
import itertools
import sqlite3
from pathlib import Path

import sqlglot

from pipeline import _extract_deterministic_decision_chains
from src.ingestion.ingestion import CodeIngestionAgent, decode_sql_source_bytes
from src.ir.canonical_ir import BusinessRuleIR, _build_decision_blocks
from src.output.report_formatter import ReportFormatterAgent
from src.parsing.decision_tables import expression_rows
from src.parsing.decision_identity import decision_text_key
from src.parsing.sql_comments import executable_sql
from src.parsing.statement_boundaries import split_top_level_statement_spans
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from src.validation.semantic_validation import extract_case_assignment_decision_chains, merge_decision_chains

SAMPLE = Path(__file__).resolve().parents[1] / 'samples/PRO.SMA_MARKING_12122023.StoredProcedure.sql'


def test_simple_case_preserves_operand_and_sql_null_comparison():
    chain = extract_case_assignment_decision_chains("UPDATE t SET label=CASE code WHEN 1 THEN 'A' WHEN NULL THEN 'B' END")[0]
    assert [b['branch_condition'] for b in chain['branches']] == ['code = 1', 'code = NULL', 'ELSE']
    assert chain['branches'][-1]['assignments'][0]['value'] == 'NULL'
    assert chain['branches'][-1]['implicit_default']


def test_nested_case_leaf_table_matches_database_for_nullable_inputs():
    expression = "CASE WHEN x > 0 THEN CASE WHEN y > 0 THEN 'BOTH' ELSE 'X' END ELSE CASE WHEN y > 0 THEN 'Y' END END"
    rows = expression_rows(sqlglot.parse_one(expression, read='tsql'))
    db = sqlite3.connect(':memory:')
    try:
        for x, y in itertools.product([None, -1, 1], repeat=2):
            clause = ' FROM (SELECT ? AS x, ? AS y)'
            expected = db.execute('SELECT '+expression+clause, (x, y)).fetchone()[0]
            for condition, outcome in rows:
                if condition == 'ELSE' or db.execute('SELECT CASE WHEN '+condition+' THEN 1 ELSE 0 END'+clause, (x, y)).fetchone()[0]:
                    actual = db.execute('SELECT '+outcome+clause, (x, y)).fetchone()[0]
                    break
            assert actual == expected, (x, y, rows)
    finally:
        db.close()


def test_iif_false_and_null_both_use_fallback():
    rows = expression_rows(sqlglot.parse_one("IIF(score > 10, 'HIGH', 'LOW')", read='tsql'))
    assert rows == [('score > 10', "'HIGH'"), ('ELSE', "'LOW'")]


def test_coalesce_and_choose_preserve_priority_and_invalid_index_fallback():
    sql = "SELECT ISNULL(a.label, CHOOSE(b.rank, 'A', 'B', 'C')) result FROM a LEFT JOIN b ON a.id=b.id"
    chains = _extract_deterministic_decision_chains(sql)
    assert len(chains) == 1
    branches = chains[0]['branches']
    assert branches[0]['branch_condition'] == 'a.label IS NOT NULL'
    assert branches[0]['assignments'][0]['value'] == 'a.label'
    assert [b['branch_condition'] for b in branches[1:-1]] == [f'CONVERT(INT, b.rank) = {i}' for i in [1, 2, 3]]
    assert branches[-1]['assignments'][0]['value'] == 'NULL'
    assert 'SQL type conversion' in chains[0]['execution_semantics']


def test_same_line_case_ids_and_branch_order_do_not_collapse_distinct_decisions():
    sql = "UPDATE t SET band=CASE WHEN x>0 THEN 'A' ELSE 'B' END; UPDATE t SET band=CASE WHEN x>0 THEN 'A' ELSE 'B' END;"
    chains = _extract_deterministic_decision_chains(sql)
    assert len(chains) == len({c['chain_id'] for c in chains}) == 2
    chain = chains[0]
    reversed_chain = dict(chain, branches=list(reversed(chain['branches'])))
    assert len(merge_decision_chains([chain, reversed_chain])) == 2


def test_coverage_is_order_sensitive_and_preserves_literal_case():
    chain = extract_case_assignment_decision_chains("UPDATE t SET band=CASE WHEN x>0 THEN 'A' WHEN x>10 THEN 'B' ELSE 'C' END")[0]
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], [chain])
    reversed_rule = dict(rules[0], decision_logic_rows=list(reversed(rules[0]['decision_logic_rows'])))
    assert len(RuleSynthesizerAgent.ensure_decision_chain_coverage([reversed_rule], [chain])) == 2
    assert decision_text_key("label='A'") != decision_text_key("label='a'")


def test_sequential_updates_keep_duplicate_predicates_and_later_overrides():
    sql = "UPDATE t SET label='A' WHERE code=1;\nUPDATE t SET label='B' WHERE code=1;\nUPDATE t SET label='C' WHERE code=2;"
    chains = _extract_deterministic_decision_chains(sql)
    assert len(chains) == 1 and chains[0]['chain_type'] == 'SEQUENTIAL_UPDATES'
    assert 'later matching updates can overwrite' in chains[0]['execution_semantics']
    assert [b['source_line_start'] for b in chains[0]['branches']] == [1, 2, 3]
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    blocks = _build_decision_blocks([BusinessRuleIR.from_dict(r) for r in rules], chains)
    assert [b['results'] for b in blocks[0]['branches']] == [["'A'"], ["'B'"], ["'C'"]]
    db = sqlite3.connect(':memory:')
    try:
        db.executescript('CREATE TABLE t(code INT, label TEXT); INSERT INTO t VALUES (1,\'old\'),(2,\'old\'),(3,\'old\');'+sql)
        assert db.execute('SELECT label FROM t ORDER BY code').fetchall() == [('B',), ('C',), ('old',)]
    finally:
        db.close()


def test_updates_across_reads_or_control_boundaries_are_not_one_mapping():
    sql = "UPDATE t SET label='A' WHERE code=1;\nSELECT * FROM t;\nUPDATE t SET label='B' WHERE code=2;"
    assert not [c for c in _extract_deterministic_decision_chains(sql) if c['chain_type'] == 'SEQUENTIAL_UPDATES']


def test_statement_boundaries_keep_control_wrappers_out_of_sql():
    sql = "UPDATE t SET x=1 WHERE y=2\nIF EXISTS(SELECT 1 FROM t)\nBEGIN\nUPDATE t SET x=3 WHERE y=4\nEND\nELSE\nBEGIN\nUPDATE t SET x=5\nEND"
    spans = split_top_level_statement_spans(sql, CodeIngestionAgent._mask_strings_and_comments(sql))
    assert ''.join(sql[a:b] for a, b in spans) == sql
    updates = [sql[a:b].strip() for a, b in spans if sql[a:b].strip().startswith('UPDATE')]
    assert updates == ['UPDATE t SET x=1 WHERE y=2', 'UPDATE t SET x=3 WHERE y=4', 'UPDATE t SET x=5']


def test_comments_do_not_create_procedural_decision_tables():
    sql = "/* IF x = 1 THEN\n result := 'A';\nELSE\n result := 'B';\nEND IF; */"
    assert _extract_deterministic_decision_chains(sql, dialect='oracle') == []


def test_real_sample_scope_fallback_and_sequential_maps_reach_full_report():
    ingestion = CodeIngestionAgent().ingest(str(SAMPLE))
    chains = _extract_deterministic_decision_chains(ingestion.raw_code)
    assert len([c for c in chains if c['chain_type'] == 'CASE_EXPRESSION']) == 12
    mappings = [c for c in chains if c['chain_type'] == 'SEQUENTIAL_UPDATES']
    assert [(c['source_line_start'], len(c['branches'])) for c in mappings] == [(360, 9), (370, 6)]
    rank = next(c for c in chains if c['source_line_start'] == 284)
    assert any('GROUP BY A.CustomerEntityID' in item for item in rank['decision_context'])
    ucif = next(c for c in chains if c['source_line_start'] == 308)
    assert any('GROUP BY A.UCIF_ID' in item for item in ucif['decision_context'])
    classification = next(c for c in chains if c['source_line_start'] == 129)
    assert any('BALANCE' in item.upper() for item in classification['eligibility'])
    assert 'TARGET: PRO.ACCOUNTCAL' in [item.upper() for item in classification['decision_context']]
    for start, table in [(471, 'ACCOUNT_MOVEMENT_HISTORY'), (610, 'CUSTOMER_MOVEMENT_HISTORY')]:
        chain = next(c for c in chains if c['source_line_start'] == start)
        assert any('ELSE of IF EXISTS' in item and table in item for item in chain['decision_context'])
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    report = ReportFormatterAgent().format(ingestion, {'decision_chains': chains}, SynthesisResult(data={'business_rules': rules}))
    assert 'GROUP BY A.UCIF_ID' in report
    assert 'later matching updates can overwrite' in report
    assert 'CONVERT(INT, SMA_CLASS_KEY) = 3' in report
    assert 'EffectiveFromTimeKey' in report


def test_predicate_case_becomes_row_selection_not_a_column_assignment():
    sql = "UPDATE t SET x=1 WHERE x=CASE WHEN flag=1 THEN 2 END"
    chains = _extract_deterministic_decision_chains(sql)
    assert len(chains) == 1
    chain = chains[0]
    assert chain['decision_role'] == 'predicate'
    assert [b['assignments'][0]['value'] for b in chain['branches']] == ['x = 2', 'x = NULL']
    assert all(b['assignments'][0]['field'] == 'Row selection predicate' for b in chain['branches'])
    assert 'FALSE or NULL excludes' in chain['execution_semantics']


def test_sma_history_insert_predicates_have_their_own_tables():
    chains = _extract_deterministic_decision_chains(decode_sql_source_bytes(SAMPLE.read_bytes()))
    predicates = [c for c in chains if c.get('decision_role') == 'predicate']
    assert [c['source_line_start'] for c in predicates] == [471, 610]
    assert all(c['branches'][-1]['assignments'][0]['value'] == '(NULL) = 1' for c in predicates)
    ingestion = CodeIngestionAgent().ingest(str(SAMPLE))
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], predicates)
    report = ReportFormatterAgent().format(ingestion, {'decision_chains': predicates}, SynthesisResult(data={'business_rules': rules}))
    assert '**Decision output:** `Row selection predicate`' in report


def test_unknown_oracle_choose_function_is_not_given_sql_server_semantics():
    assert _extract_deterministic_decision_chains('SELECT CHOOSE(x,1,2) result FROM dual', dialect='oracle') == []


def test_multi_output_recovery_keeps_field_names_on_branch_results():
    chain = {'chain_id': 'multi', 'branches': [
        {'branch_condition': 'x > 0', 'assignments': [{'field': 'flag', 'value': "'Y'"}, {'field': 'amount', 'value': '10'}]},
        {'branch_condition': 'ELSE', 'assignments': [{'field': 'flag', 'value': "'N'"}, {'field': 'amount', 'value': '0'}]},
    ]}
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], [chain])
    block = _build_decision_blocks([BusinessRuleIR.from_dict(r) for r in rules], [chain])[0]
    assert block['branches'][0]['results'] == [{'field': 'flag', 'value': "'Y'"}, {'field': 'amount', 'value': '10'}]
