"""Statement context and additional source-derived decision tables.

Expressions are parsed as SQL, not inferred from field names. Sequential UPDATE
rules retain sequential semantics; they are never relabelled as a CASE ladder.
"""
from __future__ import annotations

import copy
import re
import sqlglot
from sqlglot import exp

from src.parsing.sql_comments import executable_sql
from src.parsing.statement_boundaries import split_top_level_statement_spans


def _mask(text):
    return re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|\[(?:\]\]|[^\]])*\]",
                  lambda m: ''.join(c if c in '\r\n' else ' ' for c in m.group()), text)


def _sql(node, dialect):
    return node.sql(dialect=dialect) if isinstance(node, exp.Expression) else str(node or '')


def _unwrap(node):
    while isinstance(node, exp.Paren):
        node = node.this
    return node


def _is_decision(node):
    node = _unwrap(node)
    return isinstance(node, (exp.Case, exp.If, exp.Coalesce)) or (
        isinstance(node, exp.Anonymous) and node.name.upper() == 'CHOOSE')


def expression_rows(node, dialect='tsql', depth=0):
    """Ordered first-match rows; ELSE includes SQL UNKNOWN, not just FALSE.

    Nested ELSE branches inherit the parent condition. Earlier rows have
    already tested the more specific paths, preserving first-match semantics
    without an incorrect NOT(predicate) test on nullable predicates.
    """
    node = _unwrap(node)
    if depth > 20:
        raise ValueError('Decision expression nesting exceeds 20 levels')
    alternatives = []
    if isinstance(node, exp.Case):
        subject = node.args.get('this')
        for branch in node.args.get('ifs') or []:
            condition = _sql(branch.this, dialect)
            if subject is not None:
                condition = f'{_sql(subject, dialect)} = {condition}'
            alternatives.append((condition, branch.args.get('true')))
        alternatives.append(('ELSE', node.args.get('default') if node.args.get('default') is not None else exp.Null()))
    elif isinstance(node, exp.If):
        alternatives = [(_sql(node.this, dialect), node.args.get('true')),
                        ('ELSE', node.args.get('false') if node.args.get('false') is not None else exp.Null())]
    elif isinstance(node, exp.Coalesce):
        values = [node.this, *node.expressions]
        alternatives = [(f'{_sql(value, dialect)} IS NOT NULL', value) for value in values[:-1]]
        alternatives.append(('ELSE', values[-1]))
    elif isinstance(node, exp.Anonymous) and node.name.upper() == 'CHOOSE' and dialect == 'tsql':
        if len(node.expressions) < 2:
            return []
        index, *values = node.expressions
        # SQL Server converts CHOOSE's index to int before selecting.
        alternatives = [(f'CONVERT(INT, {_sql(index, dialect)}) = {i}', value)
                        for i, value in enumerate(values, 1)] + [('ELSE', exp.Null())]
    else:
        return []
    rows = []
    for condition, value in alternatives:
        nested = expression_rows(value, dialect, depth + 1) if _is_decision(value) else []
        if not nested:
            rows.append((condition, _sql(value, dialect)))
        else:
            for child_condition, outcome in nested:
                combined = (child_condition if condition == 'ELSE' else condition
                            if child_condition == 'ELSE' else f'({condition}) AND ({child_condition})')
                rows.append((combined, outcome))
        if len(rows) > 128:
            raise ValueError('Decision expression exceeds 128 leaf rows')
    return rows


def _control_regions(source):
    """Recognize complete IF ... BEGIN/END [ELSE BEGIN/END] scopes.

    Only complete blocks are annotated. Unbracketed statements and Oracle
    THEN/END IF are left to their existing procedural parser.
    """
    masked = _mask(source)
    tokens = list(re.finditer(r'\b(?:IF|THEN|BEGIN|END|CASE|ELSE|UPDATE|SET|PRINT|DROP|RETURN)\b|[()]', masked, re.I))
    regions = []

    def block_end(index):
        stack = ['BEGIN']
        for j in range(index + 1, len(tokens)):
            word = tokens[j].group().upper()
            if word in {'BEGIN', 'CASE'}:
                stack.append(word)
            elif word == 'END':
                if not stack:
                    return None
                stack.pop()
                if not stack:
                    return j
        return None

    for i, token in enumerate(tokens):
        if token.group().upper() != 'IF' or (i and tokens[i - 1].group().upper() == 'END' and '\n' not in source[tokens[i - 1].end():token.start()]):
            continue
        depth = 0
        for j in range(i + 1, len(tokens)):
            word = tokens[j].group().upper()
            if word == '(':
                depth += 1
            elif word == ')':
                depth -= 1
            elif depth == 0:
                if word == 'BEGIN':
                    end = block_end(j)
                    if end is None:
                        break
                    condition = ' '.join(source[token.end():tokens[j].start()].split())
                    regions.append((tokens[j].end(), tokens[end].start(), f'IF {condition} is true'))
                    k = end + 1
                    if k + 1 < len(tokens) and tokens[k].group().upper() == 'ELSE' and tokens[k + 1].group().upper() == 'BEGIN':
                        else_end = block_end(k + 1)
                        if else_end is not None:
                            regions.append((tokens[k + 1].end(), tokens[else_end].start(),
                                            f'ELSE of IF {condition} (false or NULL)'))
                    break
                if word in {'THEN', 'UPDATE', 'SET', 'PRINT', 'DROP', 'RETURN', 'IF', 'END'}:
                    break
    return regions


def _records(source, dialect):
    masked = _mask(source)
    boundaries = {v for span in split_top_level_statement_spans(source, masked) for v in span}
    # Multiple semicolon-terminated statements on one line must retain distinct IDs.
    depth = 0
    for i, char in enumerate(masked):
        if char == '(':
            depth += 1
        elif char == ')':
            depth = max(0, depth - 1)
        elif char == ';' and depth == 0:
            boundaries.add(i + 1)
    cuts = sorted(boundaries)
    records = []
    for start, end in zip(cuts, cuts[1:]):
        raw = source[start:end]
        start += len(raw) - len(raw.lstrip())
        text = source[start:end].strip()
        if not text:
            continue
        if not re.match(r'(?i)^(SELECT|UPDATE|INSERT|WITH)\b', text):
            records.append({'start': start, 'end': end, 'tree': None})
            continue
        try:
            tree = sqlglot.parse_one(text, read=dialect)
        except sqlglot.errors.SqlglotError:
            tree = None
        records.append({'start': start, 'end': end, 'tree': tree})
    return records


def _assignments(tree):
    if isinstance(tree, exp.Update):
        return [(assignment.this.name, assignment.expression) for assignment in tree.expressions
                if isinstance(assignment, exp.EQ) and isinstance(assignment.this, exp.Column)]
    select = tree.expression if isinstance(tree, exp.Insert) else tree
    if isinstance(select, exp.Select):
        if isinstance(tree, exp.Insert) and isinstance(tree.this, exp.Schema):
            return [(column.name, projection.this if isinstance(projection, exp.Alias) else projection)
                    for column, projection in zip(tree.this.expressions, select.expressions)]
        return [(projection.alias, projection.this) for projection in select.expressions
                if isinstance(projection, exp.Alias)]
    return []


def _context(tree, dialect):
    select = tree.expression if isinstance(tree, exp.Insert) else tree
    where = select.args.get('where')
    eligibility = [_sql(where.this, dialect)] if where is not None else []
    context = []
    if isinstance(tree, (exp.Update, exp.Insert)):
        target = tree.this.this if isinstance(tree.this, exp.Schema) else tree.this
        from_clause = tree.args.get('from_') or tree.args.get('from')
        if isinstance(target, exp.Table) and not target.db and from_clause is not None:
            match = next((t for t in from_clause.find_all(exp.Table)
                          if t.alias and t.alias.casefold() == target.name.casefold()), None)
            if match is not None:
                target = match.copy()
                target.set('alias', None)
                target.set('joins', None)
        context.append(f'Target: {_sql(target, dialect)}')
    into = select.args.get('into')
    if into is not None:
        context.append(f'Target: {_sql(into.this, dialect)}')
    from_node = select.args.get('from_') or select.args.get('from')
    if from_node is not None:
        context.append(_sql(from_node, dialect))
    # Outer joins describe association; they are not independent eligibility filters.
    for join in select.args.get('joins') or []:
        context.append(_sql(join, dialect))
    group = select.args.get('group')
    if group is not None:
        context.append(_sql(group, dialect))
    having = select.args.get('having')
    if having is not None:
        context.append(_sql(having, dialect))
    return eligibility, context


def _chain(source, record, field, rows, suffix, **extra):
    from src.validation.semantic_validation import _apply_branch_provenance, _source_provenance
    start, end = record['start'], record['end']
    chain_id = f'decision_{start}_{end}_{suffix}'
    provenance = _source_provenance(source, start, end)
    branches = [_apply_branch_provenance(
        {'branch_condition': condition, 'assignments': [{'field': field, 'value': value}]},
        provenance, chain_id=chain_id, branch_index=index,
    ) for index, (condition, value) in enumerate(rows)]
    return dict(chain_type='SCALAR_EXPRESSION', chain_id=chain_id, subject=field,
                branches=branches, source_char_start=start, source_char_end=end,
                source_line_start=provenance['line_start'], source_line_end=provenance['line_end'],
                source_location_status='available', **extra)


def enrich_decision_tables(raw_source, chains, dialect='tsql'):
    """Add source context, scalar choices and contiguous conditional UPDATE maps."""
    source = executable_sql(raw_source)
    result = copy.deepcopy(chains)
    records = _records(source, dialect)
    regions = _control_regions(source) if dialect == 'tsql' else []
    for record in records:
        tree = record['tree']
        if not isinstance(tree, (exp.Update, exp.Select, exp.Insert)):
            continue
        eligibility, context = _context(tree, dialect)
        guards = [label for start, end, label in regions if start <= record['start'] < end]
        context = [*guards, *context]
        record.update(eligibility=eligibility, decision_context=context)
        members = [c for c in result if record['start'] <= c.get('source_char_start', -1)
                   and c.get('source_char_end', -1) <= record['end']]
        for chain in members:
            chain['eligibility'] = eligibility
            chain['decision_context'] = context
            chain['execution_semantics'] = 'First matching row wins; ELSE includes false or NULL predicates.'
        # A CASE in a WHERE predicate chooses a predicate value; it does
        # not assign the column on the other side of an equality.
        selection = tree.expression if isinstance(tree, exp.Insert) else tree
        where = selection.args.get('where')
        if where is not None:
            predicate = where.this
            cases = list(predicate.find_all(exp.Case))
            for case_index, case in enumerate(cases):
                parent = case.parent
                nested_query = False
                while parent is not None and parent is not where:
                    if isinstance(parent, (exp.Select, exp.Case)):
                        nested_query = True
                    parent = parent.parent
                if nested_query:
                    continue
                try:
                    rows = expression_rows(case, dialect)
                except ValueError:
                    continue
                predicate_rows = []
                for condition, value in rows:
                    replaced = predicate.copy()
                    if isinstance(replaced, exp.Case):
                        replaced = sqlglot.parse_one(value, read=dialect)
                    else:
                        list(replaced.find_all(exp.Case))[case_index].replace(sqlglot.parse_one(value, read=dialect))
                    predicate_rows.append((condition, _sql(replaced, dialect)))
                if len(predicate_rows) >= 2:
                    result.append(_chain(source, record, 'Row selection predicate', predicate_rows,
                        f'predicate_{case_index}', eligibility=[], decision_context=context,
                        decision_role='predicate',
                        execution_semantics='First matching row selects this CASE value in the WHERE predicate. The resulting predicate includes the row only when TRUE; FALSE or NULL excludes it. Other predicate terms still apply.'))
        assigned_fields = {name.casefold() for name, value in _assignments(tree) if value.find(exp.Case) is not None}
        for member in list(members):
            fields = {a.get('field', '').casefold() for b in member.get('branches', []) for a in b.get('assignments', [])}
            if member.get('chain_type') == 'CASE_EXPRESSION' and where is not None and fields and not fields.intersection(assigned_fields):
                # Do not retain a regex "assignment" found in a predicate.
                result.remove(member)
                members.remove(member)
        for index, (field, expression) in enumerate(_assignments(tree)):
            expression = _unwrap(expression)
            same_field = [c for c in members if any(a.get('field', '').casefold() == field.casefold()
                          for b in c.get('branches', []) for a in b.get('assignments', []))]
            nested_case = isinstance(expression, exp.Case) and any(isinstance(_unwrap(b.args.get('true')), (exp.Case, exp.If))
                          for b in expression.args.get('ifs') or [])
            nested_case = nested_case or (isinstance(expression, exp.Case) and isinstance(_unwrap(expression.args.get('default')), (exp.Case, exp.If)))
            if same_field and not nested_case:
                continue
            if not _is_decision(expression):
                continue
            try:
                rows = expression_rows(expression, dialect)
            except ValueError as exc:
                for chain in same_field:
                    chain.setdefault('decision_context', []).append(f'Expansion not completed: {exc}')
                continue
            if len(rows) < 2:
                continue
            for previous in same_field:
                result.remove(previous)
            result.append(_chain(source, record, field, rows, str(index),
                eligibility=eligibility, decision_context=context + [f'Expression: {_sql(expression, dialect)}'],
                execution_semantics='First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.'))

    # Map successive literal assignments only when target/fields/context match.
    # A read, unrelated write, or procedural boundary ends the sequence.
    run = []
    def flush():
        if len(run) < 2:
            return
        first, last = run[0], run[-1]
        for field_index, (field, _) in enumerate(_assignments(first['tree'])):
            rows = [(_sql(item['tree'].args['where'].this, dialect),
                     _sql(_assignments(item['tree'])[field_index][1], dialect)) for item in run]
            chain = _chain(source, {'start': first['start'], 'end': last['end']}, field, rows,
                           f'updates_{field_index}', eligibility=[], decision_context=first['decision_context'],
                           execution_semantics='Each row is a separate UPDATE executed in source order. Conditions use current values; later matching updates can overwrite earlier values. No matching update leaves the existing value unchanged.')
            chain['chain_type'] = 'SEQUENTIAL_UPDATES'
            # Each row cites its own statement, not the whole run.
            from src.validation.semantic_validation import _apply_branch_provenance, _source_provenance
            chain['branches'] = [_apply_branch_provenance(branch,
                _source_provenance(source, item['start'], item['end']),
                chain_id=chain['chain_id'], branch_index=i)
                for i, (branch, item) in enumerate(zip(chain['branches'], run))]
            result.append(chain)

    key = None
    for record in records:
        tree = record['tree']
        assignments = _assignments(tree)
        candidate = (isinstance(tree, exp.Update) and tree.args.get('where') is not None and assignments
                     and all(isinstance(_unwrap(value), (exp.Literal, exp.Null)) for _, value in assignments)
                     and not (tree.args.get('from_') or tree.args.get('from')) and not tree.args.get('joins'))
        current = (_sql(tree.this, dialect), tuple(field for field, _ in assignments),
                   tuple(record.get('decision_context', []))) if candidate else None
        if current != key or not candidate:
            flush()
            run = []
        if candidate:
            run.append(record)
        key = current
    flush()
    return sorted(result, key=lambda c: (c.get('source_char_start', -1), c.get('source_char_end', -1)))
