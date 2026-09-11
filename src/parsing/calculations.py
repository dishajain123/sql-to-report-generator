"""Keep parsed calculation expressions even when narrative synthesis omits them."""
import re

from src.parsing.sql_comments import executable_sql


def calculations_from_operations(operations):
    calculations = []
    seen = set()
    for operation in operations or []:
        for assignment in operation.get('assigned_values', []) or []:
            expression = str(assignment.get('expression') or '')
            column = str(assignment.get('column') or '')
            if not expression or not column:
                continue
            # Only formula-shaped assignments; never manufacture an expression
            # from prose, a predicate, or a source-column list.
            code = re.sub(r"'(?:''|[^'])*'", "''", executable_sql(expression))
            if not re.search(r'\b(?:DATEADD|DATEDIFF|SUM|AVG|MIN|MAX|ROUND|ABS)\s*\(|[+*/]|\w\s*-\s*\w', code, re.I):
                continue
            key = (operation.get('statement_id'), operation.get('table'), column, expression)
            if key in seen:
                continue
            seen.add(key)
            calculations.append({
                'name': column,
                'expression': expression,
                'output': column,
                'table': operation.get('table', ''),
                'source_chunk_id': operation.get('source_chunk_id', ''),
                'source_statement_id': operation.get('statement_id', ''),
                'source_evidence': [operation.get('source_statement_text', '')],
                'origin': 'DETERMINISTIC_FACT',
            })
    return calculations
