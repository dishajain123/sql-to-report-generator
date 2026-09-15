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
    assert "#DPD.DPD_IntService >= #DPD.DPD_NoCredit" in lines
    assert "#DPD.DPD_Overdrawn > 0 OR #DPD.DPD_Overdue > 0" in lines
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
    # Decision table condition: alias resolved to the real table, every other
    # character (double space, "BETWEEN 1 AND 30") preserved exactly.
    assert "PRO.ACCOUNTCAL.DPD_Max  BETWEEN 1 AND 30" in lines
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
