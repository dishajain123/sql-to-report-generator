"""Group field decisions only when their executable statement and scope agree."""
from collections import OrderedDict


def group_statement_decisions(rules):
    groups = OrderedDict()
    for index, rule in enumerate(rules):
        span = tuple(rule.get('statement_span') or [])
        context = tuple(item for item in rule.get('decision_context', [])
                        if not item.startswith('Expression:'))
        eligible = bool(rule.get('source_chain_id') and len(span) == 2
                        and rule.get('decision_role', 'assignment') == 'assignment')
        key = (span, context, tuple(rule.get('eligibility') or []), rule.get('execution_semantics')) if eligible else ('individual', index)
        groups.setdefault(key, []).append(rule)
    displayed = []
    for members in groups.values():
        fields = [rule.get('output_field') for rule in members]
        # Two occurrences writing the same field are separate evaluations.
        if len(members) == 1 or len(set(fields)) != len(fields):
            displayed.extend(members)
            continue
        grouped = dict(members[0])
        grouped['decision_tables'] = members
        grouped['rule_id'] = grouped['decision_block_id'] = 'statement_' + '_'.join(map(str, grouped['statement_span']))
        grouped['rule_name'] = grouped['decision_block_title'] = 'Determine ' + ', '.join(fields)
        grouped['fields_affected'] = fields
        grouped['output_field'] = ', '.join(fields)
        grouped['business_meaning'] = 'Compute these fields for the same eligible rows. Each field has its own ordered decision table.'
        grouped['decision_context'] = [item for item in grouped.get('decision_context', []) if not item.startswith('Expression:')]
        # No combined ladder: concatenating branches would change their meaning.
        grouped['decision_logic_rows'] = []
        displayed.append(grouped)
    return displayed
