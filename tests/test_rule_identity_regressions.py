"""Missing/reused revision IDs must not multiply or cross-wire report rules."""
import re
from copy import deepcopy

from src.ir.rule_identity import unique_rule_ids
from src.ir.canonical_ir import CanonicalBusinessIR
from src.ingestion.ingestion import CodeIngestionAgent
from src.output.report_formatter import ReportFormatterAgent
from src.synthesis.rule_synthesizer import RuleSynthesizerAgent, SynthesisResult
from pipeline import _extract_deterministic_decision_chains, _merge_into_truncation_ambiguity
from tests.test_sma_report_regressions import SAMPLE


def test_identity_repair_reserves_existing_ids_and_is_idempotent():
    rules = [{'rule_id': key, 'condition': str(i)}
             for i, key in enumerate(['R1', 'R1', '', None, 'R1__2'])]
    original = deepcopy(rules)
    fixed = unique_rule_ids(rules)
    assert len({r['rule_id'] for r in fixed}) == len(rules)
    assert all(r['rule_id'] for r in fixed)
    assert fixed[-1]['rule_id'] == 'R1__2'
    assert fixed[1]['original_rule_id'] == 'R1'
    assert unique_rule_ids(fixed) == fixed
    assert rules == original


def test_revision_normalization_assigns_ids_to_missing_and_colliding_rules():
    rules = [{'rule_name': 'a'}, {'rule_name': 'b', 'rule_id': 'R1'},
             {'rule_name': 'c', 'rule_id': 'R1'}]
    normalized = RuleSynthesizerAgent._normalize_business_rules(rules)
    assert len({r['rule_id'] for r in normalized}) == 3
    assert all(r['rule_id'] for r in normalized)


def test_section_merge_preserves_distinct_scopes_and_rows_with_reused_ids():
    rule = {'rule_id': 'R1', 'rule_name': 'Rank', 'output_field': 'rank',
            'condition': 'x = 1', 'action': 'Set rank',
            'source_statement_ids': ['entity'],
            'decision_logic_rows': [{'condition': 'x = 1', 'outcome': '1'}]}
    other = dict(rule, source_statement_ids=['ucif'])
    third = dict(rule, decision_logic_rows=[{'condition': 'x = 1', 'outcome': '2'}])
    merged = RuleSynthesizerAgent.merge_section_results([
        SynthesisResult(data={'business_rules': [rule]}),
        SynthesisResult(data={'business_rules': [rule, other, third]})])
    rules = merged.data['business_rules']
    assert len(rules) == 3
    assert len({r['rule_id'] for r in rules}) == 3


def test_mixed_sma_revision_rules_keep_all_tables_without_multiplying_or_losing_history():
    ingestion = CodeIngestionAgent().ingest(str(SAMPLE))
    chains = _extract_deterministic_decision_chains(ingestion.raw_code)
    deterministic = RuleSynthesizerAgent.ensure_decision_chain_coverage([], chains)
    # Reproduce the failing topology: 26 ID-less revision rules, nine with
    # decision rows, plus the deterministic tables recovered after revision.
    model_rules = []
    for r in deterministic[:9]:
        model_rules.append({k: deepcopy(v) for k, v in r.items()
                            if k not in {'rule_id', 'source_chain_id', 'deterministic_decision_table'}})
    for i in range(17):
        model_rules.append({'rule_name': f'History operation {i}',
                            'output_field': f'HistoryField{i}',
                            'business_meaning': f'Independent history update {i}'})
    synthesis = SynthesisResult(data={'business_rules': model_rules + deterministic})
    extraction = {'decision_chains': chains}
    ir = CanonicalBusinessIR.from_pipeline(ingestion=ingestion, merged_extraction=extraction, synthesis=synthesis)
    formatter = ReportFormatterAgent()
    projected = formatter._project_decision_rules([r.to_dict() for r in ir.business_rules], ir.decision_blocks)
    blocks = [r for r in projected if r.get('decision_block_id')]
    # Same-statement/same-eligibility chains (e.g. the six #DPD CASE columns
    # sharing one SELECT INTO) are now grouped into one displayed rule with
    # a per-field sub-table each, so displayed block count can be lower than
    # the raw chain count - but every chain's table must still be rendered
    # somewhere, with none dropped or duplicated.
    assert len(blocks) <= len(chains) == 23
    assert len({r['decision_block_id'] for r in blocks}) == len(blocks)
    assert sum(len(r['decision_tables']) if r.get('decision_tables') else 1 for r in blocks) == 23
    assert not any('HistoryField' in r['output_field'] for r in blocks)
    assert len([r for r in projected if r.get('rule_name', '').startswith('History operation')]) == 17
    report = formatter.format(ingestion, extraction, synthesis, canonical_ir=ir)
    count = int(re.search(r'\| Business rules \| (\d+) \|', report).group(1))
    assert count == len(re.findall(r'^### R\d+ —', report, re.M)) == len(projected)
    assert (len(re.findall(r'^### Decision Logic$', report, re.M))
            + len(re.findall(r'^#### Decision Logic', report, re.M))) == 23


def test_legacy_ambiguous_ids_do_not_borrow_last_rule_metadata():
    rules = [{'rule_id': '', 'rule_name': 'Decision'},
             {'rule_id': '', 'rule_name': 'History'}]
    blocks = [{'block_id': 'b', 'rule_ids': [''], 'name': 'Decision'}]
    assert ReportFormatterAgent()._project_decision_rules(rules, blocks) == rules


def test_duplicate_block_reference_is_projected_once():
    rule = {'rule_id': 'r', 'rule_name': 'Decision'}
    block = {'block_id': 'b', 'rule_ids': ['r'], 'name': 'Decision'}
    assert len(ReportFormatterAgent()._project_decision_rules([rule], [block, block])) == 1


def test_model_rule_name_copied_from_evaluation_order_is_replaced():
    """A model sometimes copies the evaluation-order/execution-semantics
    sentence verbatim into rule_name instead of writing a short business
    label (observed for several rules in a real report: R39/R40/R44-R49 all
    titled the same boilerplate sentence). ensure_decision_chain_coverage
    must rename that specific case to the same deterministic naming
    convention used for synthesized rules, without touching decision_logic_rows
    or a rule_name that is a real, non-generic label.
    """
    chain = {
        'chain_id': 'c1',
        'execution_semantics': 'First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.',
        'branches': [
            {'branch_condition': 'X = 1', 'assignments': [{'field': 'STATUS', 'value': 'A'}]},
            {'branch_condition': '', 'is_catch_all': True, 'assignments': [{'field': 'STATUS', 'value': 'B'}]},
        ],
    }
    covering_rule = {
        'rule_id': 'r1', 'output_field': 'STATUS', 'source_chain_id': 'c1',
        'rule_name': 'First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.',
        'decision_logic_rows': [
            {'condition': 'X = 1', 'outcome': 'A'},
            {'condition': 'ELSE', 'outcome': 'B'},
        ],
    }
    result = RuleSynthesizerAgent.ensure_decision_chain_coverage([covering_rule], [chain])
    fixed = next(r for r in result if r['rule_id'] == 'r1')
    assert fixed['rule_name'] == 'Determine STATUS'
    assert fixed['decision_logic_rows'] == covering_rule['decision_logic_rows']
    # A genuine, non-generic model name must survive untouched.
    named_rule = dict(covering_rule, rule_id='r2', rule_name='Reset status on reprocessing')
    result2 = RuleSynthesizerAgent.ensure_decision_chain_coverage([named_rule], [chain])
    assert next(r for r in result2 if r['rule_id'] == 'r2')['rule_name'] == 'Reset status on reprocessing'


def test_blank_outcome_near_cover_is_repaired_instead_of_duplicating():
    """A model rule that lists the correct ordered conditions but leaves an
    outcome cell blank must be repaired from the chain in place - not treated
    as uncovered (which used to synthesize a second, duplicate ladder).
    """
    chain = {
        'chain_id': 'c1',
        'execution_semantics': 'First matching row wins; ELSE includes false or NULL predicates.',
        'branches': [
            {'branch_condition': 'A.DpdDays IS NULL', 'assignments': [{'field': 'DpdBucket', 'value': "'NOT_APPLICABLE'"}]},
            {'branch_condition': 'A.DpdDays = 0', 'assignments': [{'field': 'DpdBucket', 'value': "'CURRENT'"}]},
            {'branch_condition': '', 'is_catch_all': True, 'assignments': [{'field': 'DpdBucket', 'value': "'BUCKET_90_PLUS'"}]},
        ],
    }
    near_cover = {
        'rule_id': 'r1',
        'output_field': 'DpdBucket',
        'rule_name': 'First matching row wins; ELSE includes false or NULL predicates.',
        'business_meaning': 'First matching row wins; ELSE includes false or NULL predicates.',
        'decision_logic_rows': [
            {'condition': 'DpdDays IS NULL', 'outcome': ''},
            {'condition': 'DpdDays = 0', 'outcome': "'CURRENT'"},
            {'condition': 'ELSE', 'outcome': "'BUCKET_90_PLUS'"},
        ],
    }
    result = RuleSynthesizerAgent.ensure_decision_chain_coverage([near_cover], [chain])
    assert len(result) == 1
    assert result[0]['rule_id'] == 'r1'
    assert result[0]['rule_name'] == 'Determine DpdBucket'
    assert result[0]['business_meaning'] == ''
    assert result[0]['decision_logic_rows'][0]['outcome'] == "'NOT_APPLICABLE'"


def test_incomplete_sibling_dropped_when_complete_cover_exists():
    chain = {
        'chain_id': 'c1',
        'branches': [
            {'branch_condition': 'X = 1', 'assignments': [{'field': 'STATUS', 'value': 'A'}]},
            {'branch_condition': '', 'is_catch_all': True, 'assignments': [{'field': 'STATUS', 'value': 'B'}]},
        ],
    }
    incomplete = {
        'rule_id': 'bad', 'output_field': 'STATUS',
        'decision_logic_rows': [
            {'condition': 'X = 1', 'outcome': ''},
            {'condition': 'ELSE', 'outcome': 'B'},
        ],
    }
    complete = {
        'rule_id': 'good', 'output_field': 'STATUS', 'rule_name': 'Set status',
        'decision_logic_rows': [
            {'condition': 'X = 1', 'outcome': 'A'},
            {'condition': 'ELSE', 'outcome': 'B'},
        ],
    }
    result = RuleSynthesizerAgent.ensure_decision_chain_coverage([incomplete, complete], [chain])
    assert [r['rule_id'] for r in result] == ['good']


def test_two_complete_model_covers_collapse_to_one():
    """Two model rules restating the same complete CASE ladder must not both
    survive ensure_decision_chain_coverage (observed: Determine DpdBucket +
    Classify DPD buckets for one source CASE).
    """
    chain = {
        'chain_id': 'c1',
        'branches': [
            {'branch_condition': 'DpdDays IS NULL', 'assignments': [{'field': 'DpdBucket', 'value': "'NOT_APPLICABLE'"}]},
            {'branch_condition': 'DpdDays = 0', 'assignments': [{'field': 'DpdBucket', 'value': "'CURRENT'"}]},
            {'branch_condition': '', 'is_catch_all': True, 'assignments': [{'field': 'DpdBucket', 'value': "'BUCKET_90_PLUS'"}]},
        ],
    }
    rows = [
        {'condition': 'DpdDays IS NULL', 'outcome': "'NOT_APPLICABLE'"},
        {'condition': 'DpdDays = 0', 'outcome': "'CURRENT'"},
        {'condition': 'ELSE', 'outcome': "'BUCKET_90_PLUS'"},
    ]
    first = {'rule_id': 'a', 'output_field': 'DpdBucket', 'rule_name': 'Determine DpdBucket',
             'decision_logic_rows': [dict(r) for r in rows]}
    second = {'rule_id': 'b', 'output_field': 'DpdBucket', 'rule_name': 'Classify DPD buckets',
              'business_meaning': 'Classify loan accounts into DPD buckets.',
              'decision_logic_rows': [dict(r) for r in rows]}
    result = RuleSynthesizerAgent.ensure_decision_chain_coverage([first, second], [chain])
    assert len(result) == 1
    assert result[0]['rule_id'] == 'b'  # prefers non-empty business_meaning


def test_formatter_collapses_noncanonical_content_duplicate_tables():
    rules = [
        {
            'rule_id': 'a', 'output_field': 'DpdBucket', 'rule_name': 'Determine DpdBucket',
            'fields_affected': ['DpdBucket'],
            'decision_logic_rows': [
                {'condition': 'DpdDays IS NULL', 'outcome': "'NOT_APPLICABLE'"},
                {'condition': 'ELSE', 'outcome': "'CURRENT'"},
            ],
        },
        {
            'rule_id': 'b', 'output_field': 'DpdBucket', 'rule_name': 'Classify DPD buckets',
            'fields_affected': ['DpdBucket'],
            'decision_logic_rows': [
                {'condition': 'DpdDays IS NULL', 'outcome': 'NOT_APPLICABLE'},
                {'condition': 'ELSE', 'outcome': 'CURRENT'},
            ],
        },
    ]
    kept = ReportFormatterAgent()._suppress_content_duplicate_decision_tables(rules)
    assert len(kept) == 1


def test_unreachable_annotation_does_not_blank_decision_block_results():
    """Deterministic coverage annotates unreachable CASE arms with
    `[UNREACHABLE ...]`. IR block membership must still match those rows to
    the raw chain conditions so the projected Result cell is not left blank
    (observed for DpdDays IS NULL -> NOT_APPLICABLE in a live DPD report).
    """
    from src.ir.canonical_ir import BusinessRuleIR, _build_decision_blocks

    chain = {
        'chain_id': 'case_1',
        'eligibility': ['NOT A.DpdDays IS NULL'],
        'branches': [
            {'branch_condition': 'A.DpdDays IS NULL', 'assignments': [{'field': 'DpdBucket', 'value': "'NOT_APPLICABLE'"}]},
            {'branch_condition': 'A.DpdDays = 0', 'assignments': [{'field': 'DpdBucket', 'value': "'CURRENT'"}]},
        ],
    }
    recovered = {
        'rule_id': 'det1',
        'output_field': 'DpdBucket',
        'rule_type': 'deterministic_decision_table',
        'source_chain_id': 'case_1',
        'rule_name': 'Determine DpdBucket',
        'decision_logic_rows': [
            {
                'condition': (
                    "A.DpdDays IS NULL [UNREACHABLE — contradicts this statement's own WHERE "
                    "clause; never executes for any row it touches]"
                ),
                'outcome': "'NOT_APPLICABLE'",
            },
            {'condition': 'A.DpdDays = 0', 'outcome': "'CURRENT'"},
        ],
    }
    blocks = _build_decision_blocks([BusinessRuleIR.from_dict(recovered)], [chain])
    assert len(blocks) == 1
    outcomes = [branch['results'] for branch in blocks[0]['branches']]
    assert outcomes[0] == ["'NOT_APPLICABLE'"]
    assert outcomes[1] == ["'CURRENT'"]


def test_qualified_chain_condition_is_recognized_as_covered_by_bare_model_rule():
    """Root-cause regression: a deterministic chain's own condition text is
    routinely alias/schema-qualified (`A.DpdDays IS NULL`,
    `PRO.LoanAccountCal.DpdDays IS NULL`) while a model-authored rule for
    the exact same statement just names the bare column (`DpdDays IS
    NULL`) - before qualifier-stripping was added to the coverage-check's
    row comparison, this mismatch meant `_field_is_covered` always
    returned False for a qualified chain, so a synthetic duplicate got
    appended right next to the model's already-correct rule (this is
    exactly what produced two numbered rules for one decision in a real
    generated report). The synthetic rule must now be skipped - only the
    model's original (bare) rule survives.

    The surviving cover must also be promoted to grounded
    (`decision_rows_grounded` + `source_chain_id`) so a later claim-level
    CONFLICT exclusion cannot erase the only representation of the ladder
    (observed: DpdBucket CASE missing from sample 07 after the covering
    model rule was CONFLICT-dropped with no deterministic twin).
    """
    chain = {
        'chain_id': 'c1',
        'branches': [
            {'branch_condition': 'A.DpdDays IS NULL', 'assignments': [{'field': 'DpdBucket', 'value': "'NOT_APPLICABLE'"}]},
            {'branch_condition': 'A.DpdDays = 0', 'assignments': [{'field': 'DpdBucket', 'value': "'CURRENT'"}]},
        ],
    }
    bare_model_rule = {
        'rule_id': 'r1', 'output_field': 'DpdBucket', 'rule_name': 'Classify accounts into overdue buckets',
        'decision_logic_rows': [
            {'condition': 'DpdDays IS NULL', 'outcome': "'NOT_APPLICABLE'"},
            {'condition': 'DpdDays = 0', 'outcome': "'CURRENT'"},
        ],
    }
    result = RuleSynthesizerAgent.ensure_decision_chain_coverage([bare_model_rule], [chain])
    assert len(result) == 1
    assert result[0]['rule_id'] == 'r1'
    assert result[0].get('decision_rows_grounded') is True
    assert result[0].get('source_chain_id') == 'c1'


def test_grounded_exact_cover_survives_conflict_exclusion():
    """Exact-match LLM cover promoted during ensure must not be dropped by
    `_exclude_conflicting_rules` even when reconciliation left CONFLICT.
    """
    chain = {
        'chain_id': 'case_0043_0050_1482',
        'branches': [
            {'branch_condition': 'DpdDays IS NULL', 'assignments': [{'field': 'DpdBucket', 'value': "'NOT_APPLICABLE'"}]},
            {'branch_condition': 'DpdDays = 0', 'assignments': [{'field': 'DpdBucket', 'value': "'CURRENT'"}]},
            {'branch_condition': 'DpdDays BETWEEN 1 AND 30', 'assignments': [{'field': 'DpdBucket', 'value': "'BUCKET_1_30'"}]},
        ],
    }
    llm_cover = {
        'rule_id': 'llm_dpd',
        'output_field': 'DpdBucket',
        'rule_name': 'Classify DPD bucket',
        'reconciliation_status': 'CONFLICT',
        'decision_logic_rows': [
            {'condition': 'DpdDays IS NULL', 'outcome': "'NOT_APPLICABLE'"},
            {'condition': 'DpdDays = 0', 'outcome': "'CURRENT'"},
            {'condition': 'DpdDays BETWEEN 1 AND 30', 'outcome': "'BUCKET_1_30'"},
        ],
    }
    covered = RuleSynthesizerAgent.ensure_decision_chain_coverage([llm_cover], [chain])
    kept, dropped = ReportFormatterAgent._exclude_conflicting_rules(covered)
    assert dropped == 0
    assert len(kept) == 1
    assert kept[0]['rule_id'] == 'llm_dpd'
    assert [row['outcome'] for row in kept[0]['decision_logic_rows']] == [
        "'NOT_APPLICABLE'", "'CURRENT'", "'BUCKET_1_30'",
    ]


def test_duplicate_rule_names_on_different_fields_are_disambiguated():
    """Two structurally distinct rules (different chains, different output
    fields) can legitimately share one synthesized name, e.g. the same MAX
    ladder recomputed once per CustomerEntityID and once per UCIF_ID. Left
    unchanged they render as indistinguishable duplicate rows in the
    overview table; the shared display projection must disambiguate them.
    """
    rules = [
        {'rule_id': 'r1', 'rule_name': 'Determine inputs to MAX for MAXSMA_CLASS',
         'output_field': 'MAXSMA_CLASS_BY_CUSTOMER'},
        {'rule_id': 'r2', 'rule_name': 'Determine inputs to MAX for MAXSMA_CLASS',
         'output_field': 'MAXSMA_CLASS_BY_UCIF'},
    ]
    blocks = [
        {'block_id': 'b1', 'rule_ids': ['r1'], 'name': 'Determine inputs to MAX for MAXSMA_CLASS'},
        {'block_id': 'b2', 'rule_ids': ['r2'], 'name': 'Determine inputs to MAX for MAXSMA_CLASS'},
    ]
    projected = ReportFormatterAgent()._project_decision_rules(rules, blocks)
    names = {r['rule_name'] for r in projected}
    assert len(names) == 2
    assert all('MAXSMA_CLASS' in name for name in names)
    # decision_block_title must be updated too: _render_decision_block's
    # detail heading prefers it over rule_name, so leaving it stale would
    # make the "### R<n> -" detail headers disagree with the disambiguated
    # summary-table titles for the exact same rules.
    assert {r['decision_block_title'] for r in projected} == names


def test_duplicate_rule_names_sharing_field_and_target_get_ordinal_fallback():
    """Two rules can share both output field and target table (e.g. one
    SELECT INTO populates a temp table, a later UPDATE transforms it in
    place) - field- and target-based disambiguation both collapse to the
    same suffix there, so an ordinal must break the remaining tie.
    """
    rules = [
        {'rule_id': 'r1', 'rule_name': 'Determine SMA_CLASS', 'output_field': 'SMA_CLASS',
         'decision_context': ['Target: #SMACLASS']},
        {'rule_id': 'r2', 'rule_name': 'Determine SMA_CLASS', 'output_field': 'SMA_CLASS',
         'decision_context': ['Target: #SMACLASS']},
    ]
    blocks = [
        {'block_id': 'b1', 'rule_ids': ['r1'], 'name': 'Determine SMA_CLASS',
         'decision_context': ['Target: #SMACLASS']},
        {'block_id': 'b2', 'rule_ids': ['r2'], 'name': 'Determine SMA_CLASS',
         'decision_context': ['Target: #SMACLASS']},
    ]
    projected = ReportFormatterAgent()._project_decision_rules(rules, blocks)
    names = [r['rule_name'] for r in projected]
    assert len(set(names)) == 2
    assert all(name.startswith('Determine SMA_CLASS (#SMACLASS)') for name in names)
    assert {r['decision_block_title'] for r in projected} == set(names)


def test_narrative_rule_duplicating_a_full_decision_block_is_suppressed():
    """A model rule can describe multiple fields as one comma-joined
    output_field string (e.g. "A, B, C") instead of a list of individual
    names. That string never matches a single chain field, so the rule
    never merges into the deterministic block it actually describes and
    survives as a redundant, table-less duplicate of a block that already
    documents those exact fields with real per-field decision tables
    (observed for real: a synthesized "set DPD to zero if below reference
    period" rule duplicating the #TEMPTABLE DPD_* block). It must be
    dropped - but only when its whole field set exactly matches a
    displayed block's whole field set; a rule that merely shares one field
    with a block (e.g. a real, separate DPD_Max reset-to-zero step sharing
    the DPD_Max field with the DPD_Max MAX-selection block) is a distinct
    rule and must survive.
    """
    block_rule = {
        'rule_id': 'r1', 'rule_name': 'Determine A, B',
        'output_field': 'A, B', 'fields_affected': ['A', 'B'],
        'decision_block_id': 'block1', 'decision_logic_rows': [],
    }
    narrative_dup = {
        'rule_id': 'r2', 'rule_name': 'Set A and B if below threshold',
        'output_field': 'A, B', 'business_meaning': 'restates the same thing',
    }
    distinct_single_field = {
        'rule_id': 'r3', 'rule_name': 'Reset A to zero', 'output_field': 'A',
    }
    displayed = [block_rule, narrative_dup, distinct_single_field]
    result = ReportFormatterAgent()._suppress_narrative_duplicates_of_decision_blocks(displayed)
    result_ids = {r['rule_id'] for r in result}
    assert result_ids == {'r1', 'r3'}


def test_model_rule_restating_a_decision_blocks_own_table_is_suppressed():
    """A model-authored rule can re-derive, row for row, the same table a
    deterministic block already recovered (observed for real: the DPD_Max
    MAX-selection ladder appeared once as a recovered `#DPD` block and once
    more as a narrative "Calculate maximum DPD" rule with an identical
    decision table, differing only in incidental whitespace and one side
    wrapping each branch's boolean expression in parentheses). Unlike the
    narrative-only case above, this duplicate DOES carry its own
    `decision_logic_rows`, so `_suppress_narrative_duplicates_of_decision_blocks`
    alone never touches it; the content-level pass must.
    """
    block_rule = {
        'rule_id': 'r1', 'rule_name': 'Determine DPD_Max',
        'output_field': 'DPD_Max', 'fields_affected': ['DPD_Max'],
        'decision_block_id': 'block1', 'rule_type': 'deterministic_decision_table',
        'decision_logic_rows': [
            {'condition': '(isnull(A,0)>=isnull(B,0)  AND   isnull(A,0)>=isnull(C,0))', 'outcome': 'isnull(A,0)'},
            {'condition': 'ELSE', 'outcome': 'isnull(C,0)'},
        ],
    }
    narrative_dup = {
        'rule_id': 'r2', 'rule_name': 'Calculate maximum DPD',
        'output_field': 'DPD_Max', 'fields_affected': ['DPD_Max'],
        'decision_logic_rows': [
            {'condition': 'isnull(A,0)>=isnull(B,0) AND isnull(A,0)>=isnull(C,0)', 'outcome': 'isnull(A,0)'},
            {'condition': 'ELSE', 'outcome': 'isnull(C,0)'},
        ],
    }
    distinct_reset_rule = {
        'rule_id': 'r3', 'rule_name': 'Reset DPD_Max to zero', 'output_field': 'DPD_Max',
        'decision_logic_rows': [
            {'condition': 'always', 'outcome': '0'},
        ],
    }
    displayed = [block_rule, narrative_dup, distinct_reset_rule]
    result = ReportFormatterAgent()._suppress_content_duplicate_decision_tables(displayed)
    result_ids = {r['rule_id'] for r in result}
    assert result_ids == {'r1', 'r3'}


def test_content_duplicate_suppression_survives_a_stray_space_before_punctuation():
    """Regression for a real live-generated report
    (`samples/output/6_PRO.SMA_MARKING...`): the DPD_Max MAX-selection
    ladder's recovered block and a model-authored "Calculate maximum DPD"
    duplicate of it differed, in one non-first row, only by a single space
    the original hand-typed source literally has before a comma
    (`isnull(A.DPD_NoCredit ,0)` in the deterministic block's row vs the
    model's cleaned-up `isnull(DPD_NoCredit,0)`). `_normalize_condition_text`
    collapses whitespace *runs* to one space but previously left a single
    stray space next to punctuation untouched, so that one row's signature
    differed, the whole 2-row tuple compared unequal, and the duplicate
    survived even with the content-level suppression pass in place.
    """
    block_rule = {
        'rule_id': 'r1', 'rule_name': 'Determine DPD_Max',
        'output_field': 'DPD_Max', 'fields_affected': ['DPD_Max'],
        'decision_block_id': 'block1', 'rule_type': 'deterministic_decision_table',
        'decision_logic_rows': [
            {'condition': 'isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0)', 'outcome': 'isnull(A.DPD_IntService,0)'},
            {'condition': 'isnull(A.DPD_NoCredit ,0)>=isnull(A.DPD_IntService,0)', 'outcome': 'isnull(A.DPD_NoCredit ,0)'},
            {'condition': 'ELSE', 'outcome': 'isnull(A.DPD_StockStmt,0)'},
        ],
    }
    narrative_dup = {
        'rule_id': 'r2', 'rule_name': 'Calculate maximum DPD',
        'output_field': 'DPD_Max', 'fields_affected': ['DPD_Max'],
        'decision_logic_rows': [
            {'condition': 'isnull(DPD_IntService,0)>=isnull(DPD_NoCredit,0)', 'outcome': 'isnull(DPD_IntService,0)'},
            {'condition': 'isnull(DPD_NoCredit,0)>=isnull(DPD_IntService,0)', 'outcome': 'isnull(DPD_NoCredit,0)'},
            {'condition': 'ELSE', 'outcome': 'isnull(DPD_StockStmt,0)'},
        ],
    }
    result = ReportFormatterAgent()._suppress_content_duplicate_decision_tables([block_rule, narrative_dup])
    assert {r['rule_id'] for r in result} == {'r1'}


def test_content_duplicate_suppression_matches_on_conditions_when_outcome_text_differs():
    """Regression for a real live-generated report
    (`samples/07_DPD_Bucket_Classification.sql`'s "DPD Bucket
    Classification" report): a deterministic decision-chain block rendered
    its conditions fully schema-qualified (`PRO.LoanAccountCal.DpdDays = 0`)
    with every outcome filled in, while an independently model-authored
    restatement of the *exact same* chain (same conditions in the same
    order, same field) rendered them unqualified (`DpdDays = 0`) *and* left
    its own final `ELSE` outcome blank. Neither difference is a sign these
    are genuinely different rules - they are the same chain, once with a
    schema-qualified column and a complete ELSE, once without either - but
    the strict outcome-inclusive signature the exact-match pass uses
    treated them as unequal and both survived into the same report.
    """
    block_rule = {
        'rule_id': 'r1', 'rule_name': 'Determine DpdBucket',
        'output_field': 'DpdBucket', 'fields_affected': ['DpdBucket'],
        'decision_block_id': 'block1', 'rule_type': 'deterministic_decision_table',
        'decision_logic_rows': [
            {'condition': 'PRO.LoanAccountCal.DpdDays IS NULL', 'outcome': "'NOT_APPLICABLE'"},
            {'condition': 'PRO.LoanAccountCal.DpdDays = 0', 'outcome': "'CURRENT'"},
            {'condition': 'PRO.LoanAccountCal.DpdDays BETWEEN 1 AND 30', 'outcome': "'BUCKET_1_30'"},
            {'condition': 'ELSE', 'outcome': "'BUCKET_90_PLUS'"},
        ],
    }
    narrative_dup = {
        'rule_id': 'r2', 'rule_name': 'Classify DpdBucket',
        'output_field': 'DpdBucket', 'fields_affected': ['DpdBucket'],
        'decision_logic_rows': [
            {'condition': 'DpdDays IS NULL', 'outcome': "'NOT_APPLICABLE'"},
            {'condition': 'DpdDays = 0', 'outcome': "'CURRENT'"},
            {'condition': 'DpdDays BETWEEN 1 AND 30', 'outcome': "'BUCKET_1_30'"},
            {'condition': 'ELSE', 'outcome': ''},  # left blank by the model, unlike the canonical block
        ],
    }
    result = ReportFormatterAgent()._suppress_content_duplicate_decision_tables([block_rule, narrative_dup])
    assert {r['rule_id'] for r in result} == {'r1'}


def test_content_duplicate_suppression_never_collapses_two_canonical_blocks():
    """Two rules that BOTH carry `decision_block_id` (i.e. are both
    canonical, deterministically recovered blocks) must never be collapsed
    into each other by the condition-only fallback, even if their
    conditions happen to line up - `_suppress_content_duplicate_decision_
    tables` only ever drops a non-canonical rule that duplicates a
    canonical one, exactly as the exact-match pass already guaranteed.
    """
    block_a = {
        'rule_id': 'r1', 'rule_name': 'Block A',
        'output_field': 'DpdBucket', 'fields_affected': ['DpdBucket'],
        'decision_block_id': 'blockA',
        'decision_logic_rows': [
            {'condition': 'DpdDays = 0', 'outcome': "'CURRENT'"},
            {'condition': 'ELSE', 'outcome': ''},
        ],
    }
    block_b = {
        'rule_id': 'r2', 'rule_name': 'Block B',
        'output_field': 'DpdBucket', 'fields_affected': ['DpdBucket'],
        'decision_block_id': 'blockB',
        'decision_logic_rows': [
            {'condition': 'DpdDays = 0', 'outcome': "'CURRENT'"},
            {'condition': 'ELSE', 'outcome': "'OTHER'"},
        ],
    }
    result = ReportFormatterAgent()._suppress_content_duplicate_decision_tables([block_a, block_b])
    assert {r['rule_id'] for r in result} == {'r1', 'r2'}


def test_project_decision_rules_emits_one_projection_per_primary_rule():
    """When the same synthesized rule is listed on two IR blocks (real
    chain + leftover shell), projection must emit a single displayed rule
    - not two canonical tables that content-dedup refuses to collapse.
    """
    rules = [
        {
            'rule_id': 'rule__1__3',
            'rule_name': 'Classify DPD buckets',
            'output_field': 'DpdBucket',
            'fields_affected': ['DpdBucket'],
            'decision_logic_rows': [
                {'condition': 'DpdDays IS NULL', 'outcome': 'NOT_APPLICABLE'},
                {'condition': 'ELSE', 'outcome': 'BUCKET_90_PLUS'},
            ],
        }
    ]
    blocks = [
        {
            'block_id': 'decision_block_001',
            'source_chain_id': 'case_0043_0050_1482',
            'name': 'Classify DPD buckets',
            'output_fields': ['DpdBucket'],
            'rule_ids': ['rule__1__3'],
            'branches': [
                {'condition': 'A.DpdDays IS NULL', 'results': ['NOT_APPLICABLE']},
                {'condition': 'ELSE', 'results': ['BUCKET_90_PLUS']},
            ],
        },
        {
            'block_id': 'decision_block_006',
            'source_chain_id': 'decision_chain_006',
            'name': 'Classify DPD buckets',
            'output_fields': [],
            'rule_ids': ['rule__1__3'],
            'branches': [
                {'condition': 'A.DpdDays IS NULL', 'results': []},
                {'condition': 'ELSE', 'results': []},
            ],
        },
    ]
    projected = ReportFormatterAgent()._project_decision_rules(rules, blocks)
    classify = [r for r in projected if 'Classify' in str(r.get('rule_name') or '')]
    assert len(classify) == 1
    assert classify[0]['decision_block_id'] == 'decision_block_001'


def test_conflicted_chain_block_keeps_full_facility_type_ladder():
    """A model rule that correctly restates AdjustedPenalty's CC/OD + TL/DL
    CASE can still be marked CONFLICT on a claim-level mismatch. Projection
    must keep the deterministic chain table (both facility branches) and
    clear CONFLICT so `_exclude_conflicting_rules` cannot delete the only
    copy of the ladder from the business report.
    """
    rules = [
        {
            'rule_id': 'rule__5',
            'rule_name': 'Adjust penalty in #DpdStaging',
            'output_field': 'AdjustedPenalty',
            'fields_affected': ['AdjustedPenalty'],
            'reconciliation_status': 'CONFLICT',
            'reconciliation_notes': ['Deterministic evidence conflicts with the synthesized claim.'],
            'decision_logic_rows': [
                {'condition': "S.FacilityType IN ('CC', 'OD')", 'outcome': 'S.AdjustedPenalty * 1.10'},
                {'condition': "S.FacilityType IN ('TL', 'DL')", 'outcome': 'S.AdjustedPenalty * 1.05'},
                {'condition': 'ELSE', 'outcome': 'S.AdjustedPenalty'},
            ],
        }
    ]
    blocks = [
        {
            'block_id': 'decision_block_004',
            'source_chain_id': 'case_0117_0121_4529',
            'name': 'Adjust penalty in #DpdStaging',
            'output_fields': ['AdjustedPenalty'],
            'rule_ids': ['rule__5'],
            'branches': [
                {'condition': "S.FacilityType IN ('CC', 'OD')", 'results': ['S.AdjustedPenalty * 1.10']},
                {'condition': "S.FacilityType IN ('TL', 'DL')", 'results': ['polluted action text']},
                {'condition': 'ELSE', 'results': ['S.AdjustedPenalty']},
            ],
        }
    ]
    merged = {
        'decision_chains': [
            {
                'chain_id': 'case_0117_0121_4529',
                'branches': [
                    {
                        'branch_condition': "S.FacilityType IN ('CC', 'OD')",
                        'assignments': [{'field': 'AdjustedPenalty', 'value': 'S.AdjustedPenalty * 1.10'}],
                    },
                    {
                        'branch_condition': "S.FacilityType IN ('TL', 'DL')",
                        'assignments': [{'field': 'AdjustedPenalty', 'value': 'S.AdjustedPenalty * 1.05'}],
                    },
                    {
                        'branch_condition': 'ELSE',
                        'assignments': [{'field': 'AdjustedPenalty', 'value': 'S.AdjustedPenalty'}],
                    },
                ],
            }
        ]
    }
    projected = ReportFormatterAgent()._project_decision_rules(rules, blocks, merged)
    assert len(projected) == 1
    rule = projected[0]
    assert rule['reconciliation_status'] == 'MATCHED'
    rows = rule['decision_logic_rows']
    assert len(rows) == 3
    assert "('TL', 'DL')" in rows[1]['condition']
    assert '1.05' in rows[1]['outcome']
    assert 'polluted' not in rows[1]['outcome']
    kept, suppressed = ReportFormatterAgent._exclude_conflicting_rules(projected)
    assert suppressed == 0
    assert len(kept) == 1


def test_suppress_if_ladder_branch_fragment_when_full_block_exists():
    ladder = {
        'rule_id': 'block_if',
        'rule_name': 'Determine BucketWorsened',
        'output_field': 'BucketWorsened, GracePeriodApplied',
        'fields_affected': ['BucketWorsened', 'GracePeriodApplied'],
        'decision_block_id': 'decision_block_003',
        'decision_logic_rows': [
            {
                'condition': 'EXISTS (...) — row filter: LastPaymentDueDate >= @GraceWindowStart',
                'outcome': "BucketWorsened := 'N'",
            },
            {
                'condition': (
                    'EXISTS (...) — row filter: PrevDpdBucket IS NOT NULL AND '
                    'DpdBucket <> PrevDpdBucket AND DpdDays > ISNULL(PrevDpdDays, 0)'
                ),
                'outcome': "BucketWorsened := 'Y'",
            },
            {'condition': 'ELSE', 'outcome': "BucketWorsened := 'N'"},
        ],
    }
    fragment = {
        'rule_id': 'frag',
        'rule_name': 'Update bucket worsened',
        'output_field': 'BucketWorsened',
        'fields_affected': ['BucketWorsened'],
        'decision_logic_rows': [
            {
                'condition': (
                    'PrevDpdBucket IS NOT NULL AND DpdBucket <> PrevDpdBucket '
                    'AND DpdDays > ISNULL(PrevDpdDays, 0)'
                ),
                'outcome': 'Y',
            },
        ],
    }
    kept = ReportFormatterAgent()._suppress_decision_ladder_branch_fragments([ladder, fragment])
    assert [rule['rule_id'] for rule in kept] == ['block_if']


def test_suppress_contentless_reset_when_if_ladder_covers_field():
    ladder = {
        'rule_id': 'block_if',
        'rule_name': 'Determine BucketWorsened',
        'output_field': 'BucketWorsened, GracePeriodApplied',
        'fields_affected': ['BucketWorsened', 'GracePeriodApplied'],
        'decision_block_id': 'decision_block_003',
        'decision_logic_rows': [
            {'condition': 'EXISTS (...)', 'outcome': "BucketWorsened := 'N'"},
            {'condition': 'EXISTS (...)', 'outcome': "BucketWorsened := 'Y'"},
            {'condition': 'ELSE', 'outcome': "BucketWorsened := 'N'"},
        ],
    }
    reset = {
        'rule_id': 'reset',
        'rule_name': "Reset BucketWorsened to 'N'",
        'output_field': 'BucketWorsened',
        'fields_affected': ['BucketWorsened'],
        'decision_logic_rows': [],
    }
    kept = ReportFormatterAgent()._suppress_decision_ladder_branch_fragments([ladder, reset])
    assert [rule['rule_id'] for rule in kept] == ['block_if']


def test_collapse_merge_matched_and_unmatched_into_one_upsert():
    matched = {
        'rule_id': 'm1',
        'rule_name': 'Update existing records',
        'output_field': 'DpdBucket, AdjustedPenalty, LastUpdatedDate',
        'fields_affected': ['DpdBucket', 'AdjustedPenalty', 'LastUpdatedDate'],
        'decision_context': ['Target: PRO.DpdBucketHistory'],
        'decision_logic_rows': [
            {
                'condition': 'Target.AccountId = Source.AccountId',
                'outcome': 'Source.DpdBucket, Source.AdjustedPenalty, @ProcessDate',
            }
        ],
        'source_evidence': ['WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket'],
    }
    unmatched = {
        'rule_id': 'm2',
        'rule_name': 'Insert new records',
        'output_field': 'AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate',
        'fields_affected': [
            'AccountId', 'DpdBucket', 'AdjustedPenalty', 'FirstFlaggedDate', 'LastUpdatedDate',
        ],
        'decision_context': ['Target: PRO.DpdBucketHistory'],
        'decision_logic_rows': [
            {
                'condition': 'Record does not exist in DpdBucketHistory table',
                'outcome': 'Source.AccountId',
            }
        ],
        'source_evidence': ['WHEN NOT MATCHED BY TARGET THEN INSERT'],
    }
    kept = ReportFormatterAgent()._collapse_merge_upsert_halves([matched, unmatched])
    assert len(kept) == 1
    assert kept[0]['rule_name'].startswith('Upsert')
    rows = kept[0]['decision_logic_rows']
    assert [row['condition'] for row in rows] == ['WHEN MATCHED', 'WHEN NOT MATCHED BY TARGET']


def test_collapse_per_column_matched_merge_fragments_with_insert():
    """Sectioned synthesis sometimes emits one MATCHED rule per SET column."""
    fragments = []
    for field in ('OutstandingBalance', 'ProvisionAmount', 'CoverageRatio', 'LastUpdatedDate'):
        fragments.append({
            'rule_id': f'u_{field}',
            'rule_name': f'Update {field}',
            'output_field': field,
            'fields_affected': [field],
            # Live Nova output often omits decision_context Target: on
            # sectioned MERGE halves - only summary/eligibility name the table.
            'summary': [
                f'Update the {field} for matched records in the ProvisionCoverageSummary table.'
            ],
            'eligibility': [
                'Record exists in both ProvisionCoverageSummary and #ProvisionCoverage tables'
            ],
            'decision_logic_rows': [
                {
                    'condition': 'Record exists in both ProvisionCoverageSummary and #ProvisionCoverage tables',
                    'outcome': f'Source.{field}' if field != 'LastUpdatedDate' else '@ProcessDate',
                },
            ],
            'source_evidence': [
                f'Target.{field} = Source.{field}'
                if field != 'LastUpdatedDate'
                else 'Target.LastUpdatedDate = @ProcessDate'
            ],
        })
    insert = {
        'rule_id': 'ins',
        'rule_name': 'Insert new record',
        'output_field': 'AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, FirstSeenDate, LastUpdatedDate',
        'fields_affected': [
            'AccountId', 'OutstandingBalance', 'ProvisionAmount',
            'CoverageRatio', 'FirstSeenDate', 'LastUpdatedDate',
        ],
        'summary': [
            'Insert a new record into the ProvisionCoverageSummary table for unmatched records.'
        ],
        'eligibility': ['Record does not exist in ProvisionCoverageSummary table'],
        'decision_logic_rows': [
            {
                'condition': 'Record does not exist in ProvisionCoverageSummary table',
                'outcome': 'Source.AccountId',
            },
        ],
        'source_evidence': [
            'INSERT (AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, '
            'FirstSeenDate, LastUpdatedDate) VALUES (Source.AccountId, ...)'
        ],
    }
    kept = ReportFormatterAgent()._collapse_merge_upsert_halves(fragments + [insert])
    assert len(kept) == 1
    assert kept[0]['rule_name'].startswith('Upsert')
    assert 'OutstandingBalance' in kept[0]['output_field']
    assert 'ProvisionAmount' in kept[0]['output_field']
    assert [row['condition'] for row in kept[0]['decision_logic_rows']] == [
        'WHEN MATCHED', 'WHEN NOT MATCHED BY TARGET',
    ]


def test_suppress_wasteful_duplicate_rules_keeps_distinct_ladders_and_folds_rest():
    """Samples 08–16 produced wasteful extras: DECLARE junk, MERGE halves
    beside Upsert, duplicate INSERTs, near-identical CASE restatements, and
    one-row UPDATE floors for each column of the same statement. Distinct
    IF vs CASE ladders on the same field must survive.
    """
    from src.output.report_formatter import ReportFormatterAgent

    fmt = ReportFormatterAgent()
    rules = [
        {
            "rule_id": "case",
            "rule_name": "Determine ReviewReason",
            "output_field": "ReviewReason",
            "fields_affected": ["ReviewReason"],
            "decision_context": ["Target: #ProvisionCoverage"],
            "rule_type": "deterministic_decision_table",
            "decision_rows_grounded": True,
            "decision_logic_rows": [
                # Live floors qualify temp-table columns; bare-name LLM
                # paraphrases must still collapse after `#Temp.Col` strip.
                {"condition": "#ProvisionCoverage.CoverageRatio IS NULL", "outcome": "'NO_BALANCE'"},
                {"condition": "#ProvisionCoverage.CoverageRatio < 0.25", "outcome": "'SEVERE_UNDERCOVER'"},
                {"condition": "#ProvisionCoverage.CoverageRatio < 0.5", "outcome": "'MODERATE_UNDERCOVER'"},
                {"condition": "#ProvisionCoverage.CoverageRatio >= 0.5 AND #ProvisionCoverage.CoverageRatio < 1", "outcome": "'ADEQUATE'"},
                {"condition": "ELSE", "outcome": "'FULLY_COVERED'"},
            ],
        },
        {
            "rule_id": "llm",
            "rule_name": "Determine ReviewReason based on CoverageRatio",
            "output_field": "ReviewReason",
            "fields_affected": ["ReviewReason"],
            "decision_context": ["Target: #ProvisionCoverage"],
            "decision_logic_rows": [
                {"condition": "CoverageRatio IS NULL", "outcome": "'NO_BALANCE'"},
                {"condition": "CoverageRatio < 0.25", "outcome": "'SEVERE_UNDERCOVER'"},
                {"condition": "CoverageRatio < 0.5", "outcome": "'MODERATE_UNDERCOVER'"},
                {"condition": "CoverageRatio >= 0.5 AND CoverageRatio < 1", "outcome": "'ADEQUATE'"},
                {"condition": "CoverageRatio >= 1", "outcome": "'FULLY_COVERED'"},
            ],
        },
        {
            "rule_id": "iff",
            "rule_name": "Determine ReviewReason (quarter)",
            "output_field": "ReviewReason",
            "fields_affected": ["ReviewReason"],
            "decision_context": ["Target: #ProvisionCoverage"],
            "rule_type": "deterministic_decision_table",
            "decision_logic_rows": [
                {"condition": "@ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate)",
                 "outcome": "ReviewReason + '_QUARTER_END'"},
                {"condition": "ELSE", "outcome": "ReviewReason"},
            ],
        },
        {
            "rule_id": "decl",
            "rule_name": "Calculate quarter start date",
            "output_field": "QuarterStartDate",
            "fields_affected": ["QuarterStartDate"],
            "decision_logic_rows": [],
        },
        {
            "rule_id": "up",
            "rule_name": "Upsert provisioncoveragesummary",
            "output_field": "OutstandingBalance, CoverageRatio",
            "fields_affected": ["OutstandingBalance", "CoverageRatio"],
            "decision_context": ["Target: PRO.ProvisionCoverageSummary"],
            "decision_logic_rows": [
                {"condition": "WHEN MATCHED", "outcome": "Source.OutstandingBalance"},
                {"condition": "WHEN NOT MATCHED BY TARGET", "outcome": "Source.AccountId"},
            ],
        },
        {
            "rule_id": "half",
            "rule_name": "Insert new records",
            "output_field": "AccountId, OutstandingBalance",
            "fields_affected": ["AccountId", "OutstandingBalance"],
            "decision_context": ["Target: PRO.ProvisionCoverageSummary"],
            "decision_logic_rows": [
                {"condition": "WHEN NOT MATCHED BY TARGET", "outcome": "Source.AccountId"},
            ],
            "source_evidence": ["WHEN NOT MATCHED BY TARGET THEN INSERT"],
        },
        {
            "rule_id": "matched_restatement",
            "rule_name": "Update coverage ratio",
            "output_field": "CoverageRatio",
            "fields_affected": ["CoverageRatio"],
            "decision_context": ["Target: PRO.ProvisionCoverageSummary"],
            "decision_logic_rows": [
                {"condition": "record matched", "outcome": "Source.CoverageRatio"},
            ],
        },
        {
            "rule_id": "s1",
            "rule_name": "Update account status",
            # Live sample 08 omits Target: and only qualifies the column.
            "output_field": "PRO.LoanAccountCal.AccountStatus",
            "fields_affected": ["PRO.LoanAccountCal.AccountStatus"],
            "decision_logic_rows": [
                {"condition": "#RestructureDecisions.EligibleFlag = 'Y'", "outcome": "'RESTRUCTURED'"}
            ],
        },
        {
            "rule_id": "s2",
            "rule_name": "Update last payment due date",
            "output_field": "PRO.LoanAccountCal.LastPaymentDueDate",
            "fields_affected": ["PRO.LoanAccountCal.LastPaymentDueDate"],
            "decision_logic_rows": [
                {"condition": "#RestructureDecisions.EligibleFlag = 'Y'", "outcome": "DATEADD(MONTH, 1, @ProcessDate)"}
            ],
        },
        {
            "rule_id": "audit_full",
            "rule_name": "Insert into RestructureAuditLog",
            "output_field": "AccountId, DecisionDate, EligibleFlag",
            "fields_affected": ["AccountId", "DecisionDate", "EligibleFlag"],
            "decision_context": ["Target: PRO.RestructureAuditLog"],
            "decision_logic_rows": [
                {"condition": "EligibleFlag = 'Y'", "outcome": "insert"},
            ],
        },
        {
            "rule_id": "audit_dup",
            "rule_name": "Insert into audit log",
            "output_field": "Not specified",
            "fields_affected": [],
            "decision_context": ["Target: PRO.RestructureAuditLog"],
            "decision_logic_rows": [],
            "summary": ["Insert records into the RestructureAuditLog table"],
        },
    ]
    merged = {
        "tables_written": [
            {"table": "#ProvisionCoverage"},
            {"table": "PRO.ProvisionCoverageSummary"},
            {"table": "PRO.LoanAccountCal"},
            {"table": "PRO.RestructureAuditLog"},
            {"table": "#RestructureDecisions"},
        ]
    }
    out = fmt._suppress_wasteful_duplicate_rules(rules, merged)
    names = [r["rule_name"] for r in out]
    assert "Calculate quarter start date" not in names
    assert "Insert new records" not in names
    assert "Determine ReviewReason based on CoverageRatio" not in names
    assert "Update coverage ratio" not in names
    assert "Insert into audit log" not in names
    assert "Determine ReviewReason" in names
    assert "Determine ReviewReason (quarter)" in names
    assert "Upsert provisioncoveragesummary" in names
    assert "Insert into RestructureAuditLog" in names
    combined = next(r for r in out if str(r.get("rule_name") or "").startswith("Update "))
    assert "AccountStatus" in combined["output_field"]
    assert "LastPaymentDueDate" in combined["output_field"]
    assert "AccountStatus :=" in combined["decision_logic_rows"][0]["outcome"]


def test_suppress_nested_case_pointer_and_declare_with_placeholder_row():
    from src.output.report_formatter import ReportFormatterAgent

    fmt = ReportFormatterAgent()
    rules = [
        {
            "rule_id": "ptr",
            "rule_name": "Determine ReviewPriority",
            "output_field": "ReviewPriority",
            "fields_affected": ["ReviewPriority"],
            "decision_logic_rows": [
                {
                    "condition": "DATEPART(MONTH, @ProcessDate) IN (3, 6, 9, 12)",
                    "outcome": "(nested CASE — see separate decision table)",
                },
                {
                    "condition": "ELSE",
                    "outcome": "(nested CASE — see separate decision table)",
                },
            ],
        },
        {
            "rule_id": "case",
            "rule_name": "Determine ReviewPriority (#CollateralStaging)",
            "output_field": "ReviewPriority",
            "fields_affected": ["ReviewPriority"],
            "decision_context": ["Target: #CollateralStaging"],
            "rule_type": "deterministic_decision_table",
            "decision_logic_rows": [
                {"condition": "ShortfallAmount IS NULL", "outcome": "'NONE'"},
                {"condition": "ShortfallAmount > 500000", "outcome": "'URGENT'"},
                {"condition": "ELSE", "outcome": "'NONE'"},
            ],
        },
        {
            "rule_id": "decl",
            "rule_name": "Calculate dispute grace cutoff",
            "output_field": "DisputeGraceCutoff",
            "fields_affected": ["DisputeGraceCutoff"],
            "decision_logic_rows": [
                {"condition": "ProcessDate is set", "outcome": "DisputeGraceCutoff"},
            ],
            "summary": [
                "Determine the dispute grace cutoff date by subtracting 30 days from the process date."
            ],
        },
    ]
    out = fmt._suppress_wasteful_duplicate_rules(
        rules, {"tables_written": [{"table": "#CollateralStaging"}]}
    )
    names = [r["rule_name"] for r in out]
    assert names == ["Determine ReviewPriority (#CollateralStaging)"]


def test_dedup_field_bare_name_strips_temp_table_hash_prefix():
    from src.output.report_formatter import ReportFormatterAgent

    assert (
        ReportFormatterAgent._dedup_field_bare_name(
            "#ProvisionCoverage.CoverageRatio IS NULL"
        )
        == "CoverageRatio IS NULL"
    )
    assert (
        ReportFormatterAgent._normalize_condition_text(
            "#RestructureDecisions.EligibleFlag = 'Y'", bare_fields=True
        )
        == "eligibleflag = y"
    )


def test_dpd_sample_has_no_wasteful_duplicates_in_current_shape():
    """Sample 07's post-fix rule list is already one rule per real
    decision (~9–10). Wasteful suppression must not delete distinct
    ladders (DpdBucket CASE vs PenalInterest vs grace IF vs upsert).
    """
    from src.output.report_formatter import ReportFormatterAgent

    fmt = ReportFormatterAgent()
    rules = [
        {"rule_id": "1", "rule_name": "Insert into #DpdStaging", "output_field": "AccountId, DpdBucket",
         "fields_affected": ["AccountId", "DpdBucket"], "decision_context": ["Target: #DpdStaging"],
         "decision_logic_rows": [{"condition": "BucketWorsened = 'Y'", "outcome": "insert"}],
         "rule_type": "deterministic_decision_table"},
        {"rule_id": "2", "rule_name": "Determine BucketWorsened, GracePeriodApplied",
         "output_field": "BucketWorsened, GracePeriodApplied",
         "fields_affected": ["BucketWorsened", "GracePeriodApplied"],
         "decision_context": ["Target: PRO.LoanAccountCal"],
         "rule_type": "deterministic_decision_table",
         "decision_logic_rows": [
             {"condition": "EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart)",
              "outcome": "BucketWorsened := 'N'; GracePeriodApplied := 'Y'"},
             {"condition": "ELSE", "outcome": "BucketWorsened := 'N'"},
         ]},
        {"rule_id": "3", "rule_name": "Classify DPD buckets", "output_field": "DpdBucket",
         "fields_affected": ["DpdBucket"], "decision_context": ["Target: PRO.LoanAccountCal"],
         "rule_type": "deterministic_decision_table", "decision_rows_grounded": True,
         "decision_logic_rows": [
             {"condition": "DpdDays IS NULL", "outcome": "'NOT_APPLICABLE'"},
             {"condition": "DpdDays = 0", "outcome": "'CURRENT'"},
             {"condition": "ELSE", "outcome": "'BUCKET_90_PLUS'"},
         ]},
        {"rule_id": "4", "rule_name": "Calculate PenalInterestAmount", "output_field": "PenalInterestAmount",
         "fields_affected": ["PenalInterestAmount"], "decision_context": ["Target: PRO.LoanAccountCal"],
         "rule_type": "deterministic_decision_table",
         "decision_logic_rows": [
             {"condition": "DpdBucket = 'BUCKET_1_30'", "outcome": "x"},
             {"condition": "ELSE", "outcome": "0"},
         ]},
        {"rule_id": "5", "rule_name": "Upsert dpdbuckethistory",
         "output_field": "DpdBucket, AdjustedPenalty",
         "fields_affected": ["DpdBucket", "AdjustedPenalty"],
         "decision_context": ["Target: PRO.DpdBucketHistory"],
         "decision_logic_rows": [
             {"condition": "WHEN MATCHED", "outcome": "Source.DpdBucket"},
             {"condition": "WHEN NOT MATCHED BY TARGET", "outcome": "Source.AccountId"},
         ]},
    ]
    out = fmt._suppress_wasteful_duplicate_rules(rules, {
        "tables_written": [
            {"table": "#DpdStaging"},
            {"table": "PRO.LoanAccountCal"},
            {"table": "PRO.DpdBucketHistory"},
        ]
    })
    assert len(out) == 5
    assert {r["rule_name"] for r in out} == {r["rule_name"] for r in rules}


def test_collapse_merge_floors_after_alias_rewrite_strips_source_target():
    """Deterministic MERGE floors keep `WHEN MATCHED` / `WHEN NOT MATCHED`
    in the condition cell but lose `Source.`/`Target.` after alias rewrite.
    Collapse must still recognize them as MERGE halves (sample 07 otherwise
    left 8 per-column floors + a bad LLM upsert).
    """
    from src.parsing.alias_resolution import (
        merge_branch_text_looks_like_merge,
        resolve_aliases_in_business_rules,
    )

    floors = []
    for branch, fields in (
        ('WHEN MATCHED', ('DpdBucket', 'AdjustedPenalty', 'LastUpdatedDate')),
        ('WHEN NOT MATCHED BY TARGET', ('AccountId', 'DpdBucket', 'AdjustedPenalty', 'FirstFlaggedDate', 'LastUpdatedDate')),
    ):
        for field in fields:
            floors.append({
                'rule_id': f'{branch}_{field}',
                'rule_name': f'Determine {field}',
                'output_field': field,
                'fields_affected': [field],
                'decision_context': ['Target: PRO.DpdBucketHistory'],
                'decision_logic_rows': [{
                    'condition': f'{branch}: AccountId = Source.AccountId',
                    'outcome': (
                        f'Source.{field}' if field not in ('LastUpdatedDate', 'FirstFlaggedDate')
                        else '@ProcessDate'
                    ),
                }],
                'source_evidence': [
                    'MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source '
                    f'ON Target.AccountId = Source.AccountId {branch} THEN Source.{field}'
                ],
            })

    merged = {
        'table_operations': [{
            'operation': 'MERGE',
            'table': 'PRO.DpdBucketHistory',
            'table_alias': 'Target',
            'source_statement_text': (
                'MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source '
                'ON Target.AccountId = Source.AccountId'
            ),
        }],
        'decision_chains': [],
    }
    rewritten = resolve_aliases_in_business_rules(floors, merged)
    for rule in rewritten:
        blob = ' '.join([
            str(rule.get('rule_name') or ''),
            ' '.join(str(row.get('condition') or '') for row in (rule.get('decision_logic_rows') or [])),
            ' '.join(str(row.get('outcome') or '') for row in (rule.get('decision_logic_rows') or [])),
            ' '.join(str(x) for x in (rule.get('source_evidence') or [])),
        ]).casefold()
        assert merge_branch_text_looks_like_merge(blob), blob
        # Outcomes should no longer carry Source./Target. markers.
        outcomes = ' '.join(str(row.get('outcome') or '') for row in (rule.get('decision_logic_rows') or []))
        assert 'Source.' not in outcomes and 'Target.' not in outcomes

    kept = ReportFormatterAgent()._collapse_merge_upsert_halves(rewritten)
    assert len(kept) == 1
    assert kept[0]['rule_name'].startswith('Upsert')
    assert [row['condition'] for row in kept[0]['decision_logic_rows']] == [
        'WHEN MATCHED', 'WHEN NOT MATCHED BY TARGET',
    ]


def test_single_write_identity_collapses_competing_noncanonical_tables():
    """Two model paraphrases of the same single-write field (e.g. RiskScore)
    must collapse to one even when neither carries decision_block_id and
    their WHERE predicates differ enough to miss content-signature dedup.
    """
    displayed = [
        {
            'rule_id': 'a',
            'rule_name': 'Calculate RiskScore',
            'output_field': 'RiskScore',
            'fields_affected': ['RiskScore'],
            'decision_logic_rows': [
                {'condition': 'CreditLimit IS NOT NULL AND CreditLimit > 0',
                 'outcome': '(ISNULL(OverdueDays, 0) * 0.5) + (ISNULL(UtilizationRatio, 0) * 100 * 0.3)'},
            ],
        },
        {
            'rule_id': 'b',
            'rule_name': 'Calculate Risk Score',
            'output_field': 'RiskScore',
            'fields_affected': ['RiskScore'],
            'decision_logic_rows': [
                {'condition': 'OverdueDays, UtilizationRatio, PriorDefaultCount are available',
                 'outcome': '(ISNULL(OverdueDays, 0) * 0.5) + (ISNULL(UtilizationRatio, 0) * 100 * 0.3)'},
            ],
        },
    ]
    merged = {
        'tables_written': [
            {
                'table': 'PRO.CustomerRiskProfile',
                'target_columns': ['RiskScore'],
                'source_line_start': 42,
                'source_char_start': 1000,
            },
        ],
    }
    # Confirm the helper sees RiskScore as globally single-write; if the
    # table_operations shape drifts, fail loudly rather than silently skip.
    assert 'riskscore' in ReportFormatterAgent._globally_single_write_fields(merged)
    result = ReportFormatterAgent()._suppress_single_write_field_duplicates_by_identity(
        displayed, merged
    )
    assert len(result) == 1
    assert result[0]['rule_id'] == 'a'


def test_consolidated_gap_ambiguity_does_not_duplicate_across_containers():
    """A truncated synthesis merges its coverage-gap summary into
    `synthesis.data["ambiguities"]`'s existing truncation bullet (the one
    containing "exceeded the model's maximum"), producing one combined
    sentence. `merged_extraction["ambiguities"]` never had that bullet in
    the first place (only synthesis adds it), so blindly calling
    `_merge_into_truncation_ambiguity` on `merged_extraction` too always
    fell through to its "append standalone" fallback, and
    `_findings_section` (which unions ambiguities from both containers
    without deduplicating near-identical text) then showed both the
    standalone "Affected regions: ..." bullet and the combined
    "...exceeded the model's maximum... Affected regions: ..." bullet -
    the exact same information twice (observed for real in
    `samples/output/4_PRO.SMA_MARKING...`). The caller must skip the
    standalone append once the summary was already merged elsewhere.
    """
    gap_summary = "Affected regions: lines 19-19, 653-660 (2 total) - needs review after a larger output budget or chunked synthesis."
    synthesis_data = {
        "ambiguities": [
            "The automated analysis of this procedure exceeded the model's maximum "
            "response length and was cut short."
        ]
    }
    merged_extraction = {"ambiguities": []}

    merged_into_synthesis = _merge_into_truncation_ambiguity(synthesis_data, gap_summary)
    merged_into_extraction = _merge_into_truncation_ambiguity(merged_extraction, gap_summary)
    assert merged_into_synthesis is True
    assert merged_into_extraction is False
    if not merged_into_synthesis and not merged_into_extraction:
        merged_extraction["ambiguities"].append(gap_summary)

    formatter = ReportFormatterAgent()
    synthesis = SynthesisResult(data={"business_rules": [], "ambiguities": synthesis_data["ambiguities"]})
    findings = formatter._findings_section(synthesis, merged_extraction)
    assert findings.count("Affected regions: lines 19-19, 653-660") == 1


def test_rule_alias_map_resolves_aliases_from_source_context():
    rule = {
        "decision_context": [
            "Target: PRO.ACCOUNTCAL",
            "FROM PRO.ACCOUNTCAL AS A INNER JOIN PRO.CUSTOMERCAL AS B ON A.CustomerEntityID = B.CustomerEntityID "
            "INNER JOIN #DPD AS dpd ON dpd.AccountEntityId = a.AccountEntityId",
        ],
    }
    alias_map = ReportFormatterAgent()._rule_alias_map(rule)
    assert alias_map["A"] == "PRO.ACCOUNTCAL"
    assert alias_map["B"] == "PRO.CUSTOMERCAL"
    assert alias_map["DPD"] == "#DPD"
    assert alias_map["TARGET"] == "PRO.ACCOUNTCAL"


def test_rule_alias_map_resolves_merge_target_and_source():
    rule = {
        "rule_name": "Upsert matched and new records",
        "source_evidence": [
            "MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source "
            "ON Target.AccountId = Source.AccountId "
            "WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket"
        ],
        "decision_logic_rows": [
            {"condition": "WHEN MATCHED", "outcome": "Source.DpdBucket"},
        ],
    }
    alias_map = ReportFormatterAgent._rule_alias_map(rule)
    assert alias_map["TARGET"] == "PRO.DpdBucketHistory"
    assert alias_map["SOURCE"] == "#DpdStaging"
    assert (
        ReportFormatterAgent._field_for_display("Source.DpdBucket", alias_map)
        == "#DpdStaging.DpdBucket"
    )
    assert (
        ReportFormatterAgent._field_for_display("Target.AccountId", alias_map)
        == "PRO.DpdBucketHistory.AccountId"
    )


def test_field_for_display_strips_unresolved_merge_role_aliases():
    assert ReportFormatterAgent._field_for_display("Target.AccountId") == "AccountId"
    assert ReportFormatterAgent._field_for_display("Source.DpdBucket") == "DpdBucket"


def test_context_line_drops_as_alias_suffix():
    alias_map = {"S": "#DpdStaging"}
    assert (
        ReportFormatterAgent._context_line_for_display("FROM #DpdStaging AS S", alias_map)
        == "FROM #DpdStaging"
    )


def test_field_for_display_does_not_double_hash_temp_tables():
    alias_map = {"S": "#DpdStaging"}
    # Resolving S → #DpdStaging.
    assert (
        ReportFormatterAgent._field_references_for_display("S.AdjustedPenalty * 1.10", alias_map)
        == "#DpdStaging.AdjustedPenalty * 1.10"
    )
    # Already-qualified temp table must not become ##DpdStaging.
    assert (
        ReportFormatterAgent._field_references_for_display(
            "#DpdStaging.AdjustedPenalty * 1.10", alias_map
        )
        == "#DpdStaging.AdjustedPenalty * 1.10"
    )


def test_alias_map_ignores_english_from_the_prose():
    blob = "Insert records into the #DpdStaging table from the A.LoanAccountCal table where BucketWorsened is Y"
    alias_map = ReportFormatterAgent._alias_map_from_statement_text(blob)
    assert alias_map.get("A") != "the"
    assert "THE" not in {k for k in alias_map}


def test_field_for_display_keeps_pro_schema_qualifier():
    assert ReportFormatterAgent._field_for_display("PRO.LoanAccountCal.DpdDays") == (
        "PRO.LoanAccountCal.DpdDays"
    )
    assert ReportFormatterAgent._field_for_display("PRO.LoanAccountCal") == "PRO.LoanAccountCal"


def test_field_for_display_replaces_known_alias_with_real_table_name():
    alias_map = {"A": "PRO.ACCOUNTCAL", "B": "PRO.CUSTOMERCAL"}
    # Known alias: replaced with the real table, not silently dropped.
    assert ReportFormatterAgent._field_for_display("A.FACILITYTYPE", alias_map) == "PRO.ACCOUNTCAL.FACILITYTYPE"
    assert ReportFormatterAgent._field_for_display("B.FLGSMA", alias_map) == "PRO.CUSTOMERCAL.FLGSMA"
    # Unknown alias (not in the map): falls back to the previous strip
    # behavior rather than inventing a table name.
    assert ReportFormatterAgent._field_for_display("Z.SomeField", alias_map) == "SomeField"
    # No map at all: unchanged strip-only behavior for every other caller.
    assert ReportFormatterAgent._field_for_display("A.FACILITYTYPE") == "FACILITYTYPE"


def test_render_decision_block_resolves_aliases_in_conditions_outcomes_and_eligibility():
    rule = {
        "rule_id": "r1",
        "rule_name": "Determine DPD_Max",
        "output_field": "DPD_Max",
        "fields_affected": ["DPD_Max"],
        "eligibility": ["A.DPD_Overdrawn > 0 OR A.DPD_Overdue > 0"],
        "decision_context": [
            "Target: #DPD",
            "FROM #DPD AS A",
        ],
        "decision_logic_rows": [
            {"condition": "A.DPD_IntService >= A.DPD_NoCredit", "outcome": "A.DPD_IntService"},
            {"condition": "ELSE", "outcome": "A.DPD_StockStmt"},
        ],
    }
    lines = "\n".join(ReportFormatterAgent()._render_decision_block(1, [rule]))
    # Alias → real table for Applies to / Source context; Decision Logic
    # then drops the redundant `#DPD.` prefix because Target is already named.
    assert "DPD_IntService >= DPD_NoCredit" in lines
    assert "#DPD.DPD_Overdrawn > 0 OR #DPD.DPD_Overdue > 0" in lines
    assert "| DPD_IntService >= DPD_NoCredit | DPD_IntService |" in lines
    # No bare, unexplained "A." alias should survive in the rendered block.
    assert "A.DPD" not in lines


def test_render_business_rule_block_resolves_aliases_in_eligibility_and_decision_rows():
    rule = {
        "rule_id": "r1",
        "rule_name": "Flag SMA for accounts",
        "output_field": "FLGSMA",
        "eligibility": ["B.FLGPROCESSING = 'N' AND A.BALANCE > 0"],
        "decision_context": [
            "Target: PRO.ACCOUNTCAL",
            "FROM PRO.ACCOUNTCAL AS A INNER JOIN PRO.CUSTOMERCAL AS B ON A.CustomerEntityID = B.CustomerEntityID",
        ],
        "decision_logic_rows": [
            {"condition": "A.BALANCE > 0", "outcome": "'Y'"},
        ],
    }
    lines = "\n".join(ReportFormatterAgent()._render_business_rule_block(1, rule))
    assert "PRO.CUSTOMERCAL.FLGPROCESSING = 'N' AND PRO.ACCOUNTCAL.BALANCE > 0" in lines
    assert "PRO.ACCOUNTCAL.BALANCE > 0" in lines
    assert "A.BALANCE" not in lines
    assert "B.FLGPROCESSING" not in lines


def test_render_statement_decisions_resolves_aliases_but_preserves_everything_else():
    """The grouped/statement-decision sub-tables (`_render_statement_decisions`)
    preserve literal source SQL formatting in their `### Decision Logic`
    tables for evidentiary fidelity (spacing, casing, function names,
    parenthesization are never rewritten) - but a bare, unexplained table
    alias (`A`, `B`, `dpd`) is not "formatting": a reader has no way to
    know which of several joined tables it names. Per explicit user
    request, alias segments are resolved to real table names here too,
    exactly like every other rendered rule field - only the literal
    dotted alias.field token is rewritten, nothing else in the row.
    """
    rule = {
        "rule_name": "Determine SMA_CLASS, SMA_REASON",
        "output_field": "SMA_CLASS, SMA_REASON",
        "business_meaning": "x",
        "eligibility": ["A.BALANCE > 0"],
        "decision_context": [
            "Target: PRO.ACCOUNTCAL",
            "FROM PRO.ACCOUNTCAL AS A INNER JOIN PRO.CUSTOMERCAL AS B ON A.CustomerEntityID = B.CustomerEntityID",
        ],
        "decision_tables": [
            {
                "output_field": "SMA_CLASS",
                "decision_context": ["Expression: COALESCE(A.SMA_CLASS, B.SMA_CLASS_KEY)"],
                "decision_logic_rows": [
                    {"condition": "A.DPD_Max  BETWEEN 1 AND 30", "outcome": "'SMA_0'"},
                    {"condition": "Z.UnknownAlias > 0", "outcome": "'SMA_1'"},
                ],
            }
        ],
    }
    lines = "\n".join(ReportFormatterAgent()._render_statement_decisions(1, rule))
    # Eligibility resolved (business text, not literal SQL evidence).
    assert "PRO.ACCOUNTCAL.BALANCE > 0" in lines
    # Decision Logic: alias resolved, then redundant Target table qualifier
    # stripped because Source context already names PRO.ACCOUNTCAL. Spacing
    # inside the predicate is preserved.
    assert "DPD_Max  BETWEEN 1 AND 30" in lines
    assert "PRO.ACCOUNTCAL.DPD_Max  BETWEEN 1 AND 30" not in lines
    # The "Expression:" bullet above the table gets the same treatment.
    assert "COALESCE(PRO.ACCOUNTCAL.SMA_CLASS, PRO.CUSTOMERCAL.SMA_CLASS_KEY)" in lines
    # An alias with no resolvable FROM/JOIN context falls back to stripping
    # it - never left as a bare, unexplained letter.
    assert "Z.UnknownAlias" not in lines
    assert "UnknownAlias > 0" in lines
    # No raw alias survives anywhere in the rendered decision table/expression.
    assert "A.DPD_Max" not in lines
    assert "A.SMA_CLASS" not in lines
    assert "B.SMA_CLASS_KEY" not in lines


def test_exact_calculation_duplicates_collapse_without_losing_distinct_scope():
    calc = {'name': 'Movement end', 'expression': 'DATEADD(DAY,-1,@ProcessDate)',
            'output_field': 'AccountHistory.MovementToDate', 'source_statement_ids': ['account']}
    other = dict(calc, output_field='CustomerHistory.MovementToDate', source_statement_ids=['customer'])
    report = ReportFormatterAgent()._calculations(SynthesisResult(data={'calculations': [calc, dict(calc), other]}))
    assert report.count('DATEADD(DAY,-1,@ProcessDate)') == 2
    assert 'AccountHistory.MovementToDate' in report
    assert 'CustomerHistory.MovementToDate' in report


def test_calculation_wrapped_in_outer_parens_collapses_against_unwrapped_duplicate():
    """Regression for a real live-generated report
    (`samples/07_DPD_Bucket_Classification.sql`): the same
    `PenalInterestAmount` CASE formula was re-derived by two different
    synthesis sections, one wrapping the whole expression in an outer
    `(...)` the other didn't - genuinely the same calculation, but the
    previous whitespace-only comparison (which strips spaces but never an
    outer paren pair) treated `(CASE ... END)` and `CASE ... END` as two
    different expressions and rendered both.
    """
    wrapped = {
        'name': 'PenalInterestAmount',
        'expression': "(CASE WHEN DpdBucket = 'BUCKET_1_30' THEN (OutstandingBalance * 0.02) / 365 * DpdDays ELSE 0 END)",
        'output_field': 'PRO.LoanAccountCal.PenalInterestAmount',
    }
    unwrapped = {
        'name': 'PenalInterestAmount',
        'expression': "CASE WHEN DpdBucket = 'BUCKET_1_30' THEN (OutstandingBalance * 0.02) / 365 * DpdDays ELSE 0 END",
        'output_field': 'PRO.LoanAccountCal.PenalInterestAmount',
    }
    report = ReportFormatterAgent()._calculations(SynthesisResult(data={'calculations': [wrapped, unwrapped]}))
    assert report.count('### Calculation') == 1


def test_calculation_isnull_and_coalesce_paraphrase_collapse_as_the_same_formula():
    """Regression for a real live-generated report: the same `RunCount =
    ISNULL(RunCount, 0) + 1` statement was rendered once with `ISNULL` and
    once with the semantically identical `COALESCE`, by two different
    synthesis sections re-deriving the same statement. Both must collapse
    into a single calculation.
    """
    isnull_version = {'name': 'RunCount', 'expression': 'ISNULL(RunCount, 0) + 1', 'output_field': 'PRO.RunStatus.RunCount'}
    coalesce_version = {'name': 'RunCount', 'expression': 'COALESCE(RunCount, 0) + 1', 'output_field': 'RunCount'}
    report = ReportFormatterAgent()._calculations(SynthesisResult(data={'calculations': [isnull_version, coalesce_version]}))
    assert report.count('### Calculation') == 1


def test_calculation_expression_renders_in_a_code_fence():
    """Improvement requested against a live report: a calculation's
    expression should render in a fenced code block (copyable, monospace,
    immune to markdown misinterpreting `*`/`_` inside the formula) rather
    than as a bare line of text.
    """
    calc = {'name': 'AddlProvision', 'expression': 'balance * rate / 100', 'output_field': 'AddlProvision'}
    report = ReportFormatterAgent()._calculations(SynthesisResult(data={'calculations': [calc]}))
    assert "```sql\nbalance * rate / 100\n```" in report


def test_multi_branch_case_expression_is_pretty_printed_across_lines():
    """A multi-branch CASE expression should render one WHEN/ELSE per line
    instead of one unbroken line, so a reader can actually use the formula
    - a live report rendered a 3-WHEN-plus-ELSE penalty formula as a single
    ~240-character line.
    """
    expression = (
        "CASE WHEN DpdBucket = 'BUCKET_1_30' THEN (OutstandingBalance * 0.02) / 365 * DpdDays "
        "WHEN DpdBucket = 'BUCKET_31_60' THEN (OutstandingBalance * 0.03) / 365 * DpdDays "
        "ELSE 0 END"
    )
    pretty = ReportFormatterAgent._pretty_print_expression(expression)
    lines = pretty.splitlines()
    assert lines[0].startswith("CASE")
    assert any(line.strip().startswith("WHEN DpdBucket = 'BUCKET_1_30'") for line in lines)
    assert any(line.strip().startswith("WHEN DpdBucket = 'BUCKET_31_60'") for line in lines)
    assert any(line.strip().startswith("ELSE 0") for line in lines)
    assert lines[-1].strip() == "END"


def test_short_non_case_expression_is_left_on_one_line():
    """A short formula with no branches should not be reformatted - there
    is no branch structure to hang line breaks on, and forcing one would
    only add noise."""
    assert ReportFormatterAgent._pretty_print_expression("balance * rate / 100") == "balance * rate / 100"


def test_merge_section_results_keeps_the_single_most_complete_purpose_summary():
    """Regression for a real live-generated report
    (`samples/07_DPD_Bucket_Classification.sql`): sectioned synthesis ran 3
    sections, and each one independently wrote its own full "purpose of
    this procedure" summary from partial evidence - three genuinely
    different *paraphrases* of the same idea, not three distinct ideas.
    Exact-string dedup let all three through, rendering 3 near-duplicate
    paragraphs under "What This Does". The merge must keep exactly one
    (the most complete / longest) rather than concatenating every
    section's restatement.
    """
    sections = [
        SynthesisResult(data={
            "purpose_summary": "The procedure classifies loan accounts into DPD buckets based on days past due and updates related fields accordingly.",
            "step_by_step_flow": [], "business_rules": [], "calculations": [],
            "exception_handling_summary": "", "ambiguities": [],
        }),
        SynthesisResult(data={
            "purpose_summary": (
                "The procedure classifies loan accounts into DPD buckets based on the number of "
                "days past the last payment due date, calculates associated penalty interest, and "
                "updates the DPD history table accordingly."
            ),
            "step_by_step_flow": [], "business_rules": [], "calculations": [],
            "exception_handling_summary": "", "ambiguities": [],
        }),
        SynthesisResult(data={
            "purpose_summary": (
                "The procedure classifies loan accounts into DPD buckets based on the number of "
                "days past due and updates related fields accordingly. It also logs transitions "
                "and escalates accounts to collections if necessary."
            ),
            "step_by_step_flow": [], "business_rules": [], "calculations": [],
            "exception_handling_summary": "", "ambiguities": [],
        }),
    ]
    merged = RuleSynthesizerAgent.merge_section_results(sections)
    assert merged.data["purpose_summary"].count("The procedure classifies") == 1
    # Keeps the longest (most complete) of the three paraphrases.
    assert merged.data["purpose_summary"] == sections[2].data["purpose_summary"]


def test_multi_ELSE_decision_table_is_stripped_as_concatenated_chains():
    """A single well-formed decision ladder has AT MOST ONE catch-all/ELSE
    row. A model can flatten TWO separate, independently-branching CASE
    expressions from the same INSERT statement into one combined row list
    (observed for real: an `Outcome` ladder's rows immediately followed by
    an unrelated `SeverityTier` ladder's rows), producing a table with two
    ELSE rows and garbled joined outcome cells wherever the two chains'
    positions collided. That structured table must be stripped (the rule
    itself survives, with an empty decision table) since it is provably
    not one real ladder - never merged/repaired, since there's no way to
    know from the flattened list alone how to split it back into two.
    """
    garbled_rule = {
        'rule_id': 'r1', 'rule_name': 'Insert reconciliation results',
        'output_field': 'Outcome, SeverityTier', 'fields_affected': ['Outcome', 'SeverityTier'],
        'decision_logic_rows': [
            {'condition': "ExpectedRowCount IS NULL", 'outcome': "'NOT_APPLICABLE'"},
            {'condition': "ActualRowCount >= ExpectedRowCount", 'outcome': "'RECONCILED'"},
            {'condition': 'ELSE', 'outcome': "'FAILED'"},
            {'condition': "Outcome = 'RECONCILED'", 'outcome': "'NONE'"},
            {'condition': "Outcome = 'FAILED'", 'outcome': "'HIGH'"},
            {'condition': 'ELSE', 'outcome': "'UNKNOWN'"},
        ],
    }
    genuine_single_ladder = {
        'rule_id': 'r2', 'rule_name': 'Determine SeverityTier',
        'output_field': 'SeverityTier', 'fields_affected': ['SeverityTier'],
        'decision_logic_rows': [
            {'condition': "Outcome = 'RECONCILED'", 'outcome': "'NONE'"},
            {'condition': "Outcome = 'FAILED'", 'outcome': "'HIGH'"},
            {'condition': 'ELSE', 'outcome': "'UNKNOWN'"},
        ],
    }
    canonical_rule = {
        'rule_id': 'r3', 'rule_name': 'Determine Outcome',
        'output_field': 'Outcome', 'fields_affected': ['Outcome'],
        'decision_block_id': 'block1',
        'decision_logic_rows': [
            {'condition': "ExpectedRowCount IS NULL", 'outcome': "'NOT_APPLICABLE'"},
            {'condition': 'ELSE', 'outcome': "'FAILED'"},
            {'condition': 'ELSE', 'outcome': "'FAILED'"},
        ],
    }
    displayed = [garbled_rule, genuine_single_ladder, canonical_rule]
    result = ReportFormatterAgent()._strip_concatenated_chain_decision_rows(displayed)
    by_id = {r['rule_id']: r for r in result}
    assert by_id['r1']['decision_logic_rows'] == []
    assert by_id['r2']['decision_logic_rows'] == genuine_single_ladder['decision_logic_rows']
    # A canonical (decision_block_id) rule is never touched, even if it
    # happens to carry two ELSE rows - deterministic extraction should
    # never actually produce that, but this pass must not be the one
    # second-guessing canonical content either way.
    assert by_id['r3']['decision_logic_rows'] == canonical_rule['decision_logic_rows']
