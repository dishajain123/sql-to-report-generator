"""Permanent alias → real-table resolution for pipeline data.

This is not a report-only cosmetic layer. Callers rewrite structured
extraction / synthesis fields (decision-chain conditions, assignment
values, WHERE predicates, business-rule decision rows) so downstream
stages - IR, reconciliation, and the business report - all see real
table names instead of SQL aliases (`A`, `S`, `Target`, `Source`, …).

Only substitutes names proven by FROM / JOIN / MERGE / USING / UPDATE
context or `table_operations`. Never invents a table.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from src.parsing.technical_sql_ops import _extract_from_clause_alias_map

_SQL_KEYWORDS = {
    "AS", "ON", "SET", "WHERE", "WHEN", "THEN", "AND", "OR", "BY",
    "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "CROSS", "JOIN",
    "INTO", "FROM", "UPDATE", "MERGE", "USING", "INSERT", "SELECT",
    "VALUES", "NOT", "MATCHED", "TABLE",
}
_TABLE_STOPWORDS = {
    "THE", "A", "AN", "THIS", "THAT", "THESE", "THOSE", "INTO",
}
_SCHEMA_KEEP = {"PRO", "DBO", "SYS", "TMP", "OMS", "CFG"}
_ROLE_ALIASES = {"TARGET", "SOURCE", "SRC", "TGT"}
_DOTTED_PATH = re.compile(
    # Include '#' so temp-table paths (`#DPD.Col`) are one token; otherwise
    # the engine matches `DPD.Col` after the hash and corrupts the name to
    # `#DPD_Col` on a second rewrite pass.
    r"(?<![A-Za-z0-9_#])(?:#?[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*"
)


def alias_map_from_statement_text(text: str) -> Dict[str, str]:
    """Extract alias → table bindings from MERGE / USING / FROM prose."""
    alias_map: Dict[str, str] = {}
    blob = str(text or "")
    if not blob.strip():
        return alias_map
    for pattern in (
        r"(?is)\bMERGE\s+(?P<table>[\w.#\[\]]+)\s+(?:AS\s+)?(?P<alias>\w+)\b",
        r"(?is)\bUSING\s+(?P<table>[\w.#\[\]]+)\s+(?:AS\s+)?(?P<alias>\w+)\b",
    ):
        for match in re.finditer(pattern, blob):
            table = str(match.group("table") or "").strip()
            alias = str(match.group("alias") or "").strip()
            if table and alias and table.upper() not in _TABLE_STOPWORDS:
                alias_map.setdefault(alias.upper(), table)
    for pattern in (
        r"(?is)\bFROM\s+(?P<table>[\w.#\[\]]+)\s+(?:AS\s+)?(?P<alias>\w+)\b",
        r"(?is)\bJOIN\s+(?P<table>[\w.#\[\]]+)\s+(?:AS\s+)?(?P<alias>\w+)\b",
    ):
        for match in re.finditer(pattern, blob):
            table = str(match.group("table") or "").strip()
            alias = str(match.group("alias") or "").strip()
            if (
                table
                and alias
                and alias.upper() not in _SQL_KEYWORDS
                and table.upper() not in _TABLE_STOPWORDS
            ):
                alias_map.setdefault(alias.upper(), table)
    for match in re.finditer(
        r"(?is)\bUPDATE\s+(?P<alias>\w+)\b[\s\S]{0,240}?\bFROM\s+(?P<table>[\w.#\[\]]+)"
        r"(?:\s+(?:AS\s+)?(?P=alias)\b)?",
        blob,
    ):
        table = str(match.group("table") or "").strip()
        alias = str(match.group("alias") or "").strip()
        if (
            table
            and alias
            and alias.upper() not in _SQL_KEYWORDS
            and table.upper() not in _TABLE_STOPWORDS
        ):
            alias_map.setdefault(alias.upper(), table)
    insert_match = re.search(
        r"(?is)\bINSERT\s+INTO\s+(?P<table>[\w.#\[\]]+)", blob
    )
    if insert_match:
        table = insert_match.group("table").strip()
        if table.upper() not in _TABLE_STOPWORDS:
            alias_map.setdefault("TARGET", table)
    # Also accept a leading FROM-clause fragment (decision_context style).
    stripped = re.sub(r"(?i)^\s*FROM\b", "", blob)
    for alias, table in _extract_from_clause_alias_map(stripped).items():
        if table.upper() not in _TABLE_STOPWORDS:
            alias_map.setdefault(alias, table)
    return alias_map


def alias_map_from_extraction(merged_extraction: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Procedure-wide alias map from deterministic `table_operations`."""
    alias_map: Dict[str, str] = {}
    for op in (merged_extraction or {}).get("table_operations") or []:
        if not isinstance(op, dict):
            continue
        table = str(op.get("table") or "").strip()
        alias = str(op.get("table_alias") or "").strip()
        if table and alias:
            alias_map.setdefault(alias.upper(), table)
        statement_text = str(
            op.get("source_statement_text") or op.get("statement_text") or ""
        )
        for key, value in alias_map_from_statement_text(statement_text).items():
            alias_map.setdefault(key, value)
        if table and str(op.get("operation") or "").upper() == "MERGE":
            alias_map.setdefault("TARGET", table)
    return alias_map


def alias_map_from_decision_context(context_items: Any) -> Dict[str, str]:
    """Alias map from a chain/rule's own Target: + FROM/JOIN context lines."""
    alias_map: Dict[str, str] = {}
    lines = [
        str(item) for item in (context_items or [])
        if str(item or "").strip()
    ]
    for text in lines:
        if text.startswith("Target:"):
            table = text[len("Target:"):].strip()
            if table:
                alias_map.setdefault("TARGET", table)
    from_bits = [
        text for text in lines
        if not text.startswith("Target:") and not text.startswith("Expression:")
    ]
    if from_bits:
        joined = re.sub(r"(?i)^\s*FROM\b", "", " ".join(from_bits))
        for alias, table in _extract_from_clause_alias_map(joined).items():
            alias_map.setdefault(alias, table)
        for alias, table in alias_map_from_statement_text(" ".join(from_bits)).items():
            alias_map.setdefault(alias, table)
    return alias_map


def field_for_display(value: Any, alias_map: Optional[Dict[str, str]] = None) -> str:
    """Resolve one dotted path's alias segment to a real table name."""
    text = str(value or "").strip()
    if not text or "." not in text:
        return text
    parts = text.split(".")

    def _resolve_or_strip(part: str) -> Optional[str]:
        if alias_map:
            resolved = alias_map.get(part.upper())
            if resolved:
                resolved_bare = resolved.split(".")[-1].lstrip("#")
                if part.casefold() == resolved_bare.casefold():
                    return part
                return resolved
        if re.fullmatch(r"[A-Za-z]{1,3}", part) or part.upper() in _ROLE_ALIASES:
            if part.upper() in _SCHEMA_KEEP:
                return part
            return None
        return part

    if len(parts) == 2:
        resolved = _resolve_or_strip(parts[0])
        return f"{resolved}.{parts[1]}" if resolved else parts[1]
    if len(parts) > 2:
        middle = [
            resolved
            for resolved in (_resolve_or_strip(part) for part in parts[1:-1])
            if resolved is not None
        ]
        parts = [parts[0], *middle, parts[-1]]
        # Also resolve a leading short alias / role on long paths.
        head = _resolve_or_strip(parts[0])
        if head is None:
            parts = parts[1:]
        elif head != parts[0]:
            parts = [head, *parts[1:]]
    return ".".join(parts)


def rewrite_text(value: Any, alias_map: Optional[Dict[str, str]] = None) -> str:
    """Rewrite every dotted alias.field reference in free text."""
    text = str(value or "")
    if not text or not alias_map:
        # Still strip unresolved Target./Source./A. when no map is useful.
        if not text:
            return text
        return _DOTTED_PATH.sub(
            lambda match: field_for_display(match.group(0), alias_map), text
        )
    return _DOTTED_PATH.sub(
        lambda match: field_for_display(match.group(0), alias_map), text
    )


def merge_branch_text_looks_like_merge(blob: str) -> bool:
    """True when free text (a rule's own name/prose/condition/outcome,
    already casefolded by the caller) plausibly describes a MERGE
    statement's MATCHED or NOT MATCHED branch.

    Shared by `ensure_statement_coverage` (rule_synthesizer.py, deciding
    whether an existing rule already covers a MERGE branch's column
    before flooring it) and `_collapse_merge_upsert_halves`
    (report_formatter.py, folding per-column MERGE fragments into one
    upsert rule) so both sides of "is this rule about a MERGE branch"
    agree - a rule phrased one way must not look MATCHED to one caller
    and ambiguous to the other.
    """
    # `when matched` / `when not matched` must count even after alias
    # rewrite strips `Source.`/`Target.` markers from outcome text - the
    # deterministic MERGE floors keep those branch prefixes in the
    # condition cell, and collapse must still classify them as MERGE.
    return bool(
        re.search(
            r"\bmerge\b|target\.|source\.|"
            r"\bwhen matched\b|\bwhen not matched\b|"
            r"first(?:flagged|seen|evaluated|reconciled|watched)?date|"
            r"matched records?|unmatched records?|record exists in\b|"
            r"record does not exist",
            blob,
        )
    )


def merge_branch_text_is_matched(blob: str) -> bool:
    """True when text plausibly describes a MERGE WHEN MATCHED branch.

    A real "not matched" signal (`when not matched`, `not matched by
    target`, a bare `unmatched records` mention) rules this out unless an
    explicit `when matched` marker is also present - a rule phrased as
    "insert new/unmatched records" must never also read as MATCHED.
    """
    if re.search(
        r"when not matched|not matched by target|(?<![a-z])unmatched records?",
        blob,
    ) and not re.search(r"when matched(?!\s+by)", blob):
        return False
    return bool(
        re.search(
            r"when matched(?!\s+by)|update existing|existing records?|"
            r"record exists in\b|(?<![a-z])matched records?|"
            r"target\.\w+\s*=\s*(?:source\.\w+|@)",
            blob,
        )
    )


def merge_branch_text_is_unmatched(blob: str) -> bool:
    """True when text plausibly describes a MERGE WHEN NOT MATCHED branch."""
    return bool(
        re.search(
            r"when not matched|insert (?:a )?new|insert unmatched|"
            r"(?<![a-z])unmatched records?|"
            r"not (currently |previously )?present|does not exist|"
            r"not matched by target|record does not exist",
            blob,
        )
    )


def strip_redundant_table_qualifiers(
    value: Any,
    known_tables: Optional[Sequence[str]] = None,
) -> str:
    """Drop schema.table. prefixes when the table context is already known.

    Display-only helper for Decision Logic cells: when Source context already
    states ``Target: PRO.LoanAccountCal``, repeating
    ``PRO.LoanAccountCal.DpdBucket`` in every Condition/Result cell is noise.
    Bare column names and literals are preserved; qualifiers for tables *not*
    in ``known_tables`` are kept so cross-table references stay unambiguous.
    """
    text = str(value or "")
    if not text or not known_tables:
        return text
    bare_tables: List[str] = []
    full_tables: List[str] = []
    for raw in known_tables:
        token = str(raw or "").strip().strip("[]")
        if not token:
            continue
        full_tables.append(token)
        # Keep leading '#' on temp tables so stripping never matches the
        # bare name inside `#DPD.DPD_IntService` as `DPD.` (which would
        # leave a stray `#DPD_IntService`).
        bare_tables.append(token.split(".")[-1])
    # Longest first so schema.table beats bare table.
    candidates = sorted(
        {t for t in full_tables + bare_tables if t},
        key=len,
        reverse=True,
    )
    for table in candidates:
        # schema.table.column → column  OR  table.column → column
        pattern = re.compile(
            rf"(?i)(?<![A-Za-z0-9_#]){re.escape(table)}\.([A-Za-z_][\w$#]*)"
        )
        text = pattern.sub(r"\1", text)
    return text


def strip_as_alias_noise(value: Any, alias_map: Optional[Dict[str, str]] = None) -> str:
    """Rewrite dotted refs and drop trailing `AS alias` / bare alias tokens."""
    text = rewrite_text(value, alias_map)
    if not alias_map:
        return text
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        if not alias:
            continue
        text = re.sub(rf"(?i)\s+AS\s+{re.escape(alias)}\b", "", text)
        if alias.upper() in _ROLE_ALIASES:
            continue
        text = re.sub(
            rf"(?i)(?<=[\w.#\]])\s+{re.escape(alias)}\b(?=\s|$|,|\bON\b|\bWHERE\b|\bJOIN\b)",
            "",
            text,
        )
    return text


def _rewrite_list(values: Any, alias_map: Dict[str, str], *, context: bool = False) -> List[Any]:
    if not isinstance(values, list):
        return values
    rewriter = strip_as_alias_noise if context else rewrite_text
    return [rewriter(item, alias_map) if isinstance(item, str) else item for item in values]


def resolve_aliases_in_decision_chains(
    chains: Any,
    merged_extraction: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Rewrite alias-qualified text inside deterministic decision chains."""
    if not isinstance(chains, list):
        return chains
    procedure_map = alias_map_from_extraction(merged_extraction)
    resolved: List[Dict[str, Any]] = []
    for chain in chains:
        if not isinstance(chain, dict):
            resolved.append(chain)
            continue
        chain = dict(chain)
        local = dict(procedure_map)
        for alias, table in alias_map_from_decision_context(
            chain.get("decision_context")
        ).items():
            local.setdefault(alias, table)
        source_sql = str(chain.get("source_sql") or "")
        for alias, table in alias_map_from_statement_text(source_sql).items():
            local.setdefault(alias, table)
        if local:
            chain["eligibility"] = _rewrite_list(chain.get("eligibility"), local)
            chain["decision_context"] = _rewrite_list(
                chain.get("decision_context"), local, context=True
            )
            branches = []
            for branch in chain.get("branches") or []:
                if not isinstance(branch, dict):
                    branches.append(branch)
                    continue
                branch = dict(branch)
                if "branch_condition" in branch:
                    branch["branch_condition"] = rewrite_text(
                        branch.get("branch_condition"), local
                    )
                if "condition" in branch:
                    branch["condition"] = rewrite_text(branch.get("condition"), local)
                assignments = []
                for item in branch.get("assignments") or []:
                    if not isinstance(item, dict):
                        assignments.append(item)
                        continue
                    item = dict(item)
                    if "field" in item:
                        item["field"] = rewrite_text(item.get("field"), local)
                    if "value" in item:
                        item["value"] = rewrite_text(item.get("value"), local)
                    assignments.append(item)
                branch["assignments"] = assignments
                branches.append(branch)
            chain["branches"] = branches
        resolved.append(chain)
    return resolved


def resolve_aliases_in_table_operations(
    operations: Any,
) -> List[Dict[str, Any]]:
    """Rewrite WHERE / assignment expressions on deterministic table ops."""
    if not isinstance(operations, list):
        return operations
    resolved: List[Dict[str, Any]] = []
    for op in operations:
        if not isinstance(op, dict):
            resolved.append(op)
            continue
        op = dict(op)
        local = alias_map_from_statement_text(
            str(op.get("source_statement_text") or op.get("statement_text") or "")
        )
        table = str(op.get("table") or "").strip()
        alias = str(op.get("table_alias") or "").strip()
        if table and alias:
            local.setdefault(alias.upper(), table)
        if table and str(op.get("operation") or "").upper() == "MERGE":
            local.setdefault("TARGET", table)
        if local:
            if op.get("where_predicate"):
                op["where_predicate"] = rewrite_text(op.get("where_predicate"), local)
            if op.get("filter_condition"):
                op["filter_condition"] = rewrite_text(op.get("filter_condition"), local)
            assigned = []
            for item in op.get("assigned_values") or []:
                if not isinstance(item, dict):
                    assigned.append(item)
                    continue
                item = dict(item)
                if item.get("column"):
                    item["column"] = rewrite_text(item.get("column"), local)
                if item.get("expression"):
                    item["expression"] = rewrite_text(item.get("expression"), local)
                branches = []
                for branch in item.get("case_branches") or []:
                    if not isinstance(branch, dict):
                        branches.append(branch)
                        continue
                    branch = dict(branch)
                    if branch.get("condition"):
                        branch["condition"] = rewrite_text(branch.get("condition"), local)
                    if branch.get("outcome"):
                        branch["outcome"] = rewrite_text(branch.get("outcome"), local)
                    if branch.get("value"):
                        branch["value"] = rewrite_text(branch.get("value"), local)
                    branches.append(branch)
                if branches:
                    item["case_branches"] = branches
                assigned.append(item)
            if assigned:
                op["assigned_values"] = assigned
        resolved.append(op)
    return resolved


def resolve_aliases_in_business_rules(
    rules: Any,
    merged_extraction: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Rewrite alias-qualified text inside synthesized / floored rules."""
    if not isinstance(rules, list):
        return rules
    procedure_map = alias_map_from_extraction(merged_extraction)
    resolved: List[Dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            resolved.append(rule)
            continue
        rule = dict(rule)
        # A ROLE alias (TARGET/SOURCE/A/S/...) only ever means one thing
        # WITHIN a single statement - it is not a procedure-wide constant
        # ("Target" is DpdBucketHistory in one MERGE and #DpdStaging in a
        # completely unrelated INSERT elsewhere in the same procedure).
        # `procedure_map` mixes every statement's aliases into one dict, so
        # it must only ever fill a gap THIS rule's own context left open -
        # never override what this rule's own decision_context/text
        # already resolved. Building `local` from the rule's own sources
        # FIRST (with `procedure_map` folded in last, via `setdefault`)
        # is what makes that priority order real; the previous "global
        # map first, rule-specific setdefault second" order let an
        # unrelated statement's TARGET silently win over this rule's own,
        # correct "Target: ..." line every time both happened to use the
        # same role name.
        local: Dict[str, str] = {}
        for alias, table in alias_map_from_decision_context(
            rule.get("decision_context")
        ).items():
            local[alias] = table
        blob = " ".join(
            [
                str(rule.get("rule_name") or ""),
                " ".join(str(item) for item in (rule.get("source_evidence") or [])),
                " ".join(str(item) for item in (rule.get("decision_context") or [])),
            ]
        )
        for alias, table in alias_map_from_statement_text(blob).items():
            local.setdefault(alias, table)
        upsert_match = re.match(
            r"(?i)^\s*upsert\s+(.+?)\s*$", str(rule.get("rule_name") or "")
        )
        if upsert_match:
            token = upsert_match.group(1).strip()
            if token and token.casefold() not in {"matched and new records", "target"}:
                local.setdefault("TARGET", token)
        for alias, table in procedure_map.items():
            local.setdefault(alias, table)
        if local:
            for key in (
                "condition", "action", "business_meaning", "output_field",
                "execution_semantics",
            ):
                if rule.get(key):
                    rule[key] = rewrite_text(rule.get(key), local)
            for key in (
                "eligibility", "fields_affected", "source_evidence",
                "tie_priority_handling", "default", "when_not_eligible",
            ):
                if rule.get(key):
                    rule[key] = _rewrite_list(rule.get(key), local)
            if rule.get("decision_context"):
                rule["decision_context"] = _rewrite_list(
                    rule.get("decision_context"), local, context=True
                )
            rows = []
            for row in rule.get("decision_logic_rows") or []:
                if not isinstance(row, dict):
                    rows.append(row)
                    continue
                row = dict(row)
                if "condition" in row:
                    row["condition"] = rewrite_text(row.get("condition"), local)
                if "outcome" in row:
                    row["outcome"] = rewrite_text(row.get("outcome"), local)
                rows.append(row)
            if rows:
                rule["decision_logic_rows"] = rows
        resolved.append(rule)
    return resolved


def resolve_aliases_in_merged_extraction(
    merged_extraction: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """In-place-safe rewrite of chains + table_operations on the extraction."""
    data = dict(merged_extraction or {})
    if "decision_chains" in data:
        data["decision_chains"] = resolve_aliases_in_decision_chains(
            data.get("decision_chains"), data
        )
    if "table_operations" in data:
        data["table_operations"] = resolve_aliases_in_table_operations(
            data.get("table_operations")
        )
    return data
