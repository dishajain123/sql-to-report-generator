"""Structural expression identity: keep operators, literals and NULL functions."""
import sqlglot
from sqlglot import exp
from src.parsing.decision_identity import decision_text_key


def expression_key(value, dialect='tsql'):
    text = str(value or '').strip()
    if not text:
        return ''
    try:
        node = sqlglot.parse_one(text, read=dialect)
        if node is None:
            return ''
        # Identifier case is insignificant here; quoted string data is not.
        for identifier in node.find_all(exp.Identifier):
            identifier.set('this', identifier.this.casefold())
        text = node.sql(dialect=dialect)
    except sqlglot.errors.SqlglotError:
        pass
    return decision_text_key(text)
