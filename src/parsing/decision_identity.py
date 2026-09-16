"""SQL identity normalization that preserves literals and decision order."""
import re


def decision_text_key(value):
    parts = re.split(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|\[(?:\]\]|[^\]])*\])", str(value or ''))
    return ''.join(part if index % 2 else re.sub(r'\s+', ' ', part).casefold()
                   for index, part in enumerate(parts)).strip()


# --------------------------------------------------------------------------
# Qualifier-stripping identity: two extracted rules/decision chains for the
# *same* SQL statement routinely disagree on whether a column is written
# fully-qualified (`PRO.LoanAccountCal.DpdDays`), alias-qualified
# (`A.DpdDays`, `Target.DpdDays`/`Source.DpdDays` in a MERGE), bracketed
# (`[PRO].[LoanAccountCal].[DpdDays]`), or bare (`DpdDays`) - one is
# typically the deterministic decision-chain extractor's own FROM/alias
# text, the other a model-authored rule that just names the column.
# `decision_text_key` above deliberately does NOT strip these, since it is
# also used for exact source-substring matching where qualification is
# meaningful. Everything below is a separate, additive normalization used
# specifically for rule/chain *identity* comparison (dedup/coverage), where
# two conditions naming the same column under different qualification are
# the same condition.
# --------------------------------------------------------------------------

# A bracketed identifier, e.g. `[DpdBucket]` or `[Loan Account Cal]`.
_BRACKET = r"\[[^\]]*\]"
# A chain of 2+ bracketed identifiers joined by dots - captures only the
# last one, since that's the actual column once schema/table qualifiers
# are stripped.
_BRACKET_CHAIN_RE = re.compile(rf"(?:{_BRACKET}\.)+({_BRACKET})")
_LONE_BRACKET_RE = re.compile(r"\[([^\]]*)\]")

# A plain (unbracketed) SQL identifier: a normal name, a `#`/`##` temp-table
# name, or an `@` variable - anything that can legally appear as one
# segment of a qualified column reference.
_PLAIN_IDENT = r"(?:#{1,2}[A-Za-z_][\w$#]*|@[A-Za-z_][\w$#]*|[A-Za-z_][\w$#]*)"
# 2+ plain identifiers joined by dots (`A.DpdDays`, `PRO.LoanAccountCal.
# DpdDays`, `#DpdStaging.FacilityType`, `Target.DpdBucket`). Never matches a
# numeric literal like `1.10`, since a digit can't start `_PLAIN_IDENT`.
_PLAIN_CHAIN_RE = re.compile(rf"(?:{_PLAIN_IDENT}\.)+{_PLAIN_IDENT}")


def _collapse_bracket_chain(match: "re.Match") -> str:
    return match.group(1)[1:-1]


def _collapse_plain_chain(match: "re.Match") -> str:
    return match.group(0).rsplit(".", 1)[-1]


def strip_qualifiers(text: str) -> str:
    """Collapse every `schema.table.column`/`alias.column`/bracketed
    qualifier chain in `text` down to its bare final segment. Only applied
    to non-string-literal text by `normalized_condition_key` below - callers
    that need this on raw column/field names alone (no surrounding SQL
    text, so no literal to protect) can call it directly.
    """
    text = str(text or "")
    text = _BRACKET_CHAIN_RE.sub(_collapse_bracket_chain, text)
    text = _LONE_BRACKET_RE.sub(r"\1", text)
    text = _PLAIN_CHAIN_RE.sub(_collapse_plain_chain, text)
    return text


def bare_field_key(text) -> str:
    """Comparison key for a single field/column reference: a qualified
    reference and its bare form collapse to the same key. Safe to call on
    a raw field name (`output_field`, `fields_affected` entries) with no
    surrounding SQL - there's no string literal to protect.
    """
    return strip_qualifiers(str(text or "")).strip().casefold()


def normalized_condition_key(value) -> str:
    """Comparison key for a condition/outcome *expression* (not a bare
    field name) - same qualifier-stripping as `bare_field_key`, but string
    literals are located and protected first (via the same quote-splitting
    approach as `decision_text_key`) so a literal that happens to contain a
    dot or brackets is never mistaken for a qualifier chain and mangled.
    """
    parts = re.split(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\")", str(value or ''))
    out = []
    for index, part in enumerate(parts):
        if index % 2:
            out.append(part)
            continue
        part = strip_qualifiers(part)
        out.append(re.sub(r'\s+', ' ', part).casefold())
    return ''.join(out).strip()


def rule_decision_identity(field, rows):
    """Identity key for a rule/decision chain, used to recognize two
    independently-extracted candidates as the *same* decision: the bare
    target field plus the ordered tuple of its normalized *conditions*
    only - outcomes are deliberately excluded from the key. Two candidates
    can genuinely disagree on what a branch's result contains (one may
    bundle in content that actually belongs to a different, unrelated
    statement) while still being the same underlying decision point; the
    condition ladder is the more reliable identity signal, and comparing
    on it alone (rather than requiring outcomes to match too) is what lets
    real near-duplicates collapse without risking a false merge between
    two rules that only share a target column but branch on genuinely
    different conditions.

    `rows` is a list of `{"condition": ..., ...}` dicts (a rule's
    `decision_logic_rows`, or a decision chain's `branches` re-shaped the
    same way by the caller).
    """
    conditions = tuple(
        normalized_condition_key(row.get("condition"))
        for row in (rows or [])
        if isinstance(row, dict)
    )
    return (bare_field_key(field), conditions)
