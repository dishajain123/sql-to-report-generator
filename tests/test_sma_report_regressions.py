"""Source-to-report regressions exposed by the bundled dated SMA procedure."""
from pathlib import Path

from pipeline import _extract_deterministic_decision_chains
from src.ingestion.ingestion import decode_sql_source_bytes
from src.ir.canonical_ir import BusinessRuleIR, _build_decision_blocks
from src.output.report_formatter import ReportFormatterAgent
from src.parsing.sql_comments import executable_sql
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult

SAMPLE = Path(__file__).resolve().parents[1] / 'samples/PRO.SMA_MARKING_12122023.StoredProcedure.sql'


def test_comment_mask_preserves_strings_identifiers_nested_comments_and_locations():
    sql = "SELECT '--live', 'it''s /*live*/', [--column], \"/*name*/\";\r\n/* outer /* nested */ disabled */ SELECT 1 --disabled\r\n"
    active = executable_sql(sql)
    assert len(active) == len(sql)
    assert [i for i, c in enumerate(active) if c in '\r\n'] == [i for i, c in enumerate(sql) if c in '\r\n']
    assert "'--live'" in active and "'it''s /*live*/'" in active
    assert '[--column]' in active and '"/*name*/"' in active
    assert 'disabled' not in active and 'SELECT 1' in active


def test_real_sample_synthesis_input_excludes_disabled_rules_and_preserves_date_offset():
    source = decode_sql_source_bytes(SAMPLE.read_bytes())
    payload = RuleSynthesizerAgent._build_compact_synthesis_payload({}, raw_source=source)
    active = payload['source_sql']
    assert len(active) == len(source)
    assert 'BETWEEN 276 AND 305' not in active
    assert 'DPD_Max<=30' not in active
    assert 'DATEADD(DAY, -dpd.DPD_MAX+1 ,@ProcessDate)' in active
    chains = _extract_deterministic_decision_chains(source)
    thresholds = next(c for c in chains if 'BETWEEN 1 AND 30' in c['branches'][0]['branch_condition'])
    assert [b['assignments'][0]['value'] for b in thresholds['branches']] == ["'SMA_0'", "'SMA_1'", "'SMA_2'", "'SMA_2'", 'NULL']


def test_real_sample_maximum_branches_do_not_cross_match_or_absorb_else_rules():
    chains = _extract_deterministic_decision_chains(decode_sql_source_bytes(SAMPLE.read_bytes()))
    maximum = next(c for c in chains if c['branches'][0]['assignments'][0]['field'].lower() == 'dpd_max')
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], [maximum])
    rules.append({'rule_id': 'unrelated', 'rule_name': 'Reason', 'output_field': 'SMA_REASON',
                  'decision_logic_rows': [{'condition': 'ELSE', 'outcome': "'OTHER'"}]})
    blocks = _build_decision_blocks([BusinessRuleIR.from_dict(r) for r in rules], chains)
    assert len(blocks) == 1
    assert 'unrelated' not in blocks[0]['rule_ids']
    for expected, actual in zip(maximum['branches'], blocks[0]['branches']):
        assert actual['results'] == [expected['assignments'][0]['value']]


def test_matching_preserves_comparison_direction_and_branch_operand_order():
    chain = {'chain_id': 'c', 'branches': [
        {'branch_condition': 'a >= b', 'assignments': [{'field': 'winner', 'value': 'a'}]},
        {'branch_condition': 'b >= a', 'assignments': [{'field': 'winner', 'value': 'b'}]},
        {'branch_condition': 'ELSE', 'assignments': [{'field': 'winner', 'value': '0'}]},
    ]}
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], [chain])
    rules.append({'rule_id': 'wrong', 'output_field': 'winner', 'condition': 'a <= b', 'action': 'wrong'})
    block = _build_decision_blocks([BusinessRuleIR.from_dict(r) for r in rules], [chain])[0]
    assert [b['results'] for b in block['branches']] == [['a'], ['b'], ['0']]


def test_partial_table_and_different_result_do_not_count_as_complete_coverage():
    chain = {'chain_id': 'c', 'branches': [
        {'branch_condition': 'x = 1', 'assignments': [{'field': 'result', 'value': '10'}]},
        {'branch_condition': 'x = 2', 'assignments': [{'field': 'result', 'value': '20'}]},
        {'branch_condition': 'ELSE', 'assignments': [{'field': 'result', 'value': '0'}]},
    ]}
    partial = {'output_field': 'result', 'decision_logic_rows': [{'condition': 'x = 1', 'outcome': '10'}]}
    result = RuleSynthesizerAgent.ensure_decision_chain_coverage([partial], [chain])
    assert len(result) == 2 and len(result[-1]['decision_logic_rows']) == 3
    assert result[-1]['source_chain_id'] == 'c'
    assert len(RuleSynthesizerAgent.ensure_decision_chain_coverage(result, [chain])) == 2


def test_reset_is_not_backfilled_with_later_decision_table():
    chain = {'branches': [
        {'branch_condition': 'x > 0', 'assignments': [{'field': 'value', 'value': '1'}]},
        {'branch_condition': 'ELSE', 'assignments': [{'field': 'value', 'value': '2'}]},
    ]}
    rule = {'rule_name': 'Reset value', 'output_field': 'value'}
    assert RuleSynthesizerAgent._backfill_decision_logic_rows(rule, [chain]) == []
    assert RuleSynthesizerAgent._backfill_decision_logic_rows({'output_field': 'value'}, [chain, chain]) == []


def test_display_preserves_eligibility_and_does_not_invent_unconditional_execution():
    formatter = ReportFormatterAgent()
    rule = {'rule_id': 'r1', 'rule_name': 'Classify', 'output_field': 'result',
            'eligibility': ['balance > 0'], 'condition': 'x > 0'}
    blocks = [{'block_id': 'b', 'name': 'Classify', 'rule_ids': ['r1'],
               'branches': [{'condition': 'x > 0', 'results': ['1']}, {'condition': 'ELSE', 'results': ['0']}]}]
    projected = formatter._project_decision_rules([rule], blocks)
    assert len(projected) == 1
    report = formatter._business_rules_section(projected)
    assert 'balance > 0' in report
    assert 'all rows' not in '\n'.join(formatter._render_business_rule_block(1, {'rule_name': 'Unknown scope'}))


def test_calculations_survive_empty_synthesis_calculation_list():
    result = ReportFormatterAgent()._calculations(SynthesisResult(data={'calculations': []}), {
        'calculations': [{'field': 'SMA_DT', 'expression': 'DATEADD(DAY, -DPD_MAX+1, @ProcessDate)'}]
    })
    assert '-DPD_MAX+1' in result and '_None identified._' not in result


def test_source_recovery_replaces_wrong_branch_values_instead_of_concatenating_them():
    chain = {'chain_id': 'c', 'branches': [
        {'branch_condition': 'x = 1', 'assignments': [{'field': 'result', 'value': '10'}]},
        {'branch_condition': 'ELSE', 'assignments': [{'field': 'result', 'value': '0'}]},
    ]}
    wrong = {'rule_id': 'wrong', 'output_field': 'result', 'decision_logic_rows': [
        {'condition': 'x = 1', 'outcome': '999'}, {'condition': 'ELSE', 'outcome': '777'}]}
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([wrong], [chain])
    block = _build_decision_blocks([BusinessRuleIR.from_dict(r) for r in rules], [chain])[0]
    assert [b['results'] for b in block['branches']] == [['10'], ['0']]


def test_real_sample_parsed_calculations_preserve_offset_and_customer_aggregates():
    from src.ingestion.ingestion import CodeIngestionAgent
    from src.parsing.technical_sql_ops import extract_table_operations_from_chunks
    from src.parsing.calculations import calculations_from_operations

    ingestion = CodeIngestionAgent().ingest(str(SAMPLE))
    operations, _ = extract_table_operations_from_chunks(ingestion.chunks, 'tsql')
    calculations = calculations_from_operations(operations)
    expressions = '\n'.join(c['expression'] for c in calculations)
    assert 'DATEADD' in expressions and 'DPD_MAX' in expressions.upper()
    assert 'MIN(A.SMA_Dt)' in expressions
    assert 'MAX(CASE' in expressions
    assert all(c['source_chunk_id'] for c in calculations)


def test_full_report_counts_and_all_source_decision_tables_agree_for_bundled_sample():
    import re
    from src.ingestion.ingestion import CodeIngestionAgent
    ingestion = CodeIngestionAgent().ingest(str(SAMPLE))
    chains = _extract_deterministic_decision_chains(ingestion.raw_code)
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    report = ReportFormatterAgent().format(
        ingestion, {'decision_chains': chains}, SynthesisResult(data={'business_rules': rules})
    )
    count = int(re.search(r'\| Business rules \| (\d+) \|', report).group(1))
    # Same-statement/same-eligibility chains are grouped into one displayed
    # rule with a per-field sub-table each, so the displayed rule count can
    # be lower than the raw chain count - but the total number of rendered
    # decision tables (top-level "### Decision Logic" plus grouped
    # "#### Decision Logic - <field>") must still equal it exactly: every
    # chain's table is rendered exactly once, never dropped or duplicated.
    assert count == len(re.findall(r'^### R\d+ —', report, re.M)) <= len(chains)
    assert (len(re.findall(r'^### Decision Logic$', report, re.M))
            + len(re.findall(r'^#### Decision Logic', report, re.M))) == len(chains)
    assert "'OTHER'; SMA_CLASS" not in report
    assert 'BETWEEN 1 AND 30' in report
    assert 'DEGRADE BY CONTI EXCESS' in report


def test_all_twelve_active_case_occurrences_are_deterministically_recovered():
    chains = [c for c in _extract_deterministic_decision_chains(decode_sql_source_bytes(SAMPLE.read_bytes())) if c['chain_type'] == 'CASE_EXPRESSION']
    assert len(chains) == 12
    checks = [c for c in chains if 81 <= c['source_line_start'] <= 86]
    assert len(checks) == 6
    assert all(len(c['branches']) == 2 for c in checks)
    aggregates = [c for c in chains if c.get('aggregation') == 'MAX']
    assert [c['source_line_start'] for c in aggregates] == [284, 308]
    assert all([b['assignments'][0]['value'] for b in c['branches']] == ['1', '2', '3', '0'] for c in aggregates)
    rules = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    assert len(rules) == 12
    assert sum('per-row inputs to MAX' in r['business_meaning'] for r in rules) == 2


def test_case_aliases_do_not_turn_keywords_or_function_wrappers_into_outputs():
    from src.validation.semantic_validation import extract_case_assignment_decision_chains
    assert extract_case_assignment_decision_chains('SELECT CASE WHEN x=1 THEN 1 ELSE 0 END FROM t') == []
    assert extract_case_assignment_decision_chains('SELECT ABS(CASE WHEN x=1 THEN 1 ELSE 0 END) result FROM t') == []
    sql = "SELECT CASE WHEN label='CASE WHEN THEN ELSE END' THEN 'END' ELSE 'CASE' END result FROM t"
    chains = extract_case_assignment_decision_chains(sql)
    assert len(chains) == 1
    assert chains[0]['branches'][0]['branch_condition'] == "label='CASE WHEN THEN ELSE END'"
    assert [b['assignments'][0]['value'] for b in chains[0]['branches']] == ["'END'", "'CASE'"]


def test_identical_case_at_distinct_source_locations_is_not_deduplicated():
    from src.validation.semantic_validation import extract_case_assignment_decision_chains, merge_decision_chains
    sql = 'SELECT CASE WHEN x=1 THEN 1 ELSE 0 END result FROM t;\nSELECT CASE WHEN x=1 THEN 1 ELSE 0 END result FROM u;'
    chains = extract_case_assignment_decision_chains(sql)
    assert len(merge_decision_chains(chains, chains)) == 2
