"""Deterministic semantic checks for source-to-report consistency."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple


_ASSIGNMENT_RE = re.compile(
    r"^\s*(?P<field>[A-Za-z_][A-Za-z0-9_$#]*)\s*(?::=|=)\s*(?P<value>[^;]+?)\s*;?\s*$",
    re.IGNORECASE,
)
_IF_RE = re.compile(r"^\s*IF\s+(.+?)\s+THEN\s*$", re.IGNORECASE)
_ELSIF_RE = re.compile(r"^\s*ELSIF\s+(.+?)\s+THEN\s*$", re.IGNORECASE)
_ELSE_RE = re.compile(r"^\s*ELSE\s*$", re.IGNORECASE)
_END_IF_RE = re.compile(r"^\s*END\s+IF\b", re.IGNORECASE)


def extract_procedural_decision_chains(source: str) -> List[Dict[str, Any]]:
    """Extract simple PL/SQL IF/ELSIF/ELSE assignment ladders deterministically.

    This deliberately handles only a complete, unambiguous ladder. It does
    not guess through nested control flow, SQL statements, or dynamic code.
    """
    lines = str(source or "").splitlines()
    chains: List[Dict[str, Any]] = []
    index = 0
    while index < len(lines):
        match = _IF_RE.match(lines[index])
        if not match:
            index += 1
            continue
        branches: List[Dict[str, Any]] = []
        subject = ""
        current_condition = match.group(1).strip()
        depth = 1
        assignments: List[Dict[str, str]] = []
        branch_start = index
        index += 1
        while index < len(lines):
            line = lines[index]
            if _IF_RE.match(line):
                depth += 1
                index += 1
                continue
            if _END_IF_RE.match(line):
                depth -= 1
                if depth == 0:
                    branches.append({"branch_condition": current_condition, "assignments": assignments})
                    break
                index += 1
                continue
            if depth == 1:
                next_condition = None
                elsif = _ELSIF_RE.match(line)
                if elsif:
                    next_condition = elsif.group(1).strip()
                elif _ELSE_RE.match(line):
                    next_condition = "ELSE"
                if next_condition is not None:
                    branches.append({"branch_condition": current_condition, "assignments": assignments})
                    current_condition = next_condition
                    assignments = []
                    index += 1
                    continue
                assignment = _ASSIGNMENT_RE.match(line)
                if assignment:
                    field = assignment.group("field").strip()
                    value = assignment.group("value").strip().rstrip(";").strip()
                    assignments.append({"field": field, "value": value})
                    if not subject:
                        subject_match = re.match(r"([A-Za-z_][A-Za-z0-9_$#]*)", current_condition)
                        subject = subject_match.group(1) if subject_match else ""
            index += 1
        if depth == 0 and len(branches) >= 2:
            previous = [branch["branch_condition"] for branch in branches]
            for branch in branches:
                if branch["branch_condition"].upper() == "ELSE":
                    branch["effective_condition"] = (
                        "all preceding conditions are false: " + "; ".join(previous[:-1])
                    )
            chains.append({
                "chain_type": "IF_ELSIF_ELSE",
                "subject": subject,
                "branches": branches,
                "source_line_start": branch_start + 1,
                "source_line_end": index + 1,
            })
        index += 1
    return chains


def extract_nested_decision_chains(source: str) -> List[Dict[str, Any]]:
    """Extract complete leaf paths from nested procedural IF ladders.

    Unlike a flat regex pass, this keeps each child outcome attached to its
    parent path. It deliberately emits only ladders with at least two
    categorical outcomes and never interprets SQL statements as branches.
    """
    lines = [line for line in str(source or "").splitlines() if line.strip()]

    def assignment(line: str) -> Dict[str, str] | None:
        match = _ASSIGNMENT_RE.match(line)
        if not match:
            return None
        return {"field": match.group("field").strip(), "value": match.group("value").strip().rstrip(";").strip()}

    def parse_if(position: int, parents: List[str]) -> tuple[List[Dict[str, Any]], int]:
        first = _IF_RE.match(lines[position])
        if not first:
            return [], position + 1
        branches: List[Dict[str, Any]] = []
        condition = first.group(1).strip()
        preceding_conditions: List[str] = []
        position += 1
        while position < len(lines):
            direct: List[Dict[str, str]] = []
            nested_paths: List[Dict[str, Any]] = []
            while position < len(lines):
                if _IF_RE.match(lines[position]):
                    nested_paths, position = parse_if(position, parents + [condition])
                    continue
                if _ELSIF_RE.match(lines[position]) or _ELSE_RE.match(lines[position]) or _END_IF_RE.match(lines[position]):
                    break
                item = assignment(lines[position])
                if item:
                    direct.append(item)
                position += 1

            if condition.upper() == "ELSE":
                effective_condition = " AND ".join(
                    f"NOT ({item})" for item in preceding_conditions
                ) or "ELSE"
            else:
                effective_condition = condition
            path_condition = " AND ".join(parents + [effective_condition])
            if nested_paths:
                for nested in nested_paths:
                    assignments = list(direct) + list(nested.get("assignments", []))
                    branches.append({"branch_condition": nested["branch_condition"], "assignments": assignments})
            else:
                branches.append({"branch_condition": path_condition, "assignments": direct})

            if condition.upper() != "ELSE":
                preceding_conditions.append(condition)
            if position >= len(lines) or _END_IF_RE.match(lines[position]):
                return branches, position + 1
            elsif = _ELSIF_RE.match(lines[position])
            condition = elsif.group(1).strip() if elsif else "ELSE"
            position += 1
        return branches, position

    chains: List[Dict[str, Any]] = []
    position = 0
    while position < len(lines):
        if not _IF_RE.match(lines[position]):
            position += 1
            continue
        branches, position = parse_if(position, [])
        fields = {item["field"] for branch in branches for item in branch["assignments"] if item.get("field")}
        outcomes = {
            item["value"] for branch in branches for item in branch["assignments"] if item.get("value")
        }
        if len(branches) >= 2 and fields and len(outcomes) >= 2:
            chains.append({"chain_type": "NESTED_IF", "subject": "", "branches": branches})
    return chains


_CASE_KEYWORD_RE = re.compile(r"\bCASE\b|\bEND\b", re.IGNORECASE)
_CASE_BODY_TOKEN_RE = re.compile(r"\bCASE\b|\bEND\b|\bWHEN\b|\bTHEN\b|\bELSE\b", re.IGNORECASE)
_CASE_ASSIGN_TARGET_RE = re.compile(
    r"(?P<target>@?[A-Za-z_][A-Za-z0-9_$#]*(?:\.[A-Za-z_][A-Za-z0-9_$#]*)?)\s*(?::=|=)\s*\(?\s*$"
)
_CASE_ALIAS_RE = re.compile(r"^\s*\)?\s*AS\s+(?P<alias>[A-Za-z_][A-Za-z0-9_$#]*)\b", re.IGNORECASE)


def _strip_sql_comments(source: str) -> str:
    """Return a same-length copy of `source` with `--` line comments and
    `/* */` block comments blanked to spaces (newlines preserved) and
    string literals left completely untouched.

    Keyword scanning (CASE/WHEN/THEN/ELSE/END) is done on this text so a
    commented-out branch can never be mistaken for live logic. Unlike a
    full mask, string contents are preserved because branch *values*
    (e.g. `'SMA_0'`) must remain intact for extraction.
    """
    text = str(source or "")
    result = list(text)
    n = len(text)
    i = 0
    while i < n:
        two = text[i : i + 2]
        if text[i] == "'":
            j = i + 1
            while j < n:
                if text[j : j + 2] == "''":
                    j += 2
                    continue
                if text[j] == "'":
                    j += 1
                    break
                j += 1
            i = j
            continue
        if two == "--":
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                result[k] = " "
            i = j
            continue
        if two == "/*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, min(j, n)):
                if text[k] != "\n":
                    result[k] = " "
            i = j
            continue
        i += 1
    return "".join(result)


def _find_outer_case_spans(text: str) -> List[Tuple[int, int]]:
    """Return (start, end) character spans of every outermost `CASE ...
    END` expression in `text` (which must already have comments blanked
    via `_strip_sql_comments`). A nested `CASE ... END` is consumed as
    part of its parent's span, never returned as its own top-level span.
    """
    spans: List[Tuple[int, int]] = []
    stack: List[int] = []
    for match in _CASE_KEYWORD_RE.finditer(text):
        token = match.group(0).upper()
        if token == "CASE":
            stack.append(match.start())
            continue
        # token == "END"
        if not stack:
            continue
        start = stack.pop()
        if stack:
            continue
        end = match.end()
        trailing = re.match(r"\s*CASE\b", text[match.end() : match.end() + 8], re.IGNORECASE)
        if trailing:
            end = match.end() + trailing.end()
        spans.append((start, end))
    return spans


def _split_top_level_case_branches(
    text: str, case_start: int, case_end: int
) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """Split one `CASE ... END` span (from `_find_outer_case_spans`) into
    its top-level `WHEN <cond> THEN <value>` branches plus an optional
    `ELSE <value>`.

    Only tokens at depth 0 *relative to this CASE* are treated as branch
    boundaries - a nested `CASE ... END` occurring inside a THEN/ELSE
    value is left as literal, unsplit text in that branch's value, so no
    nested branch text is ever discarded, only left less granular.
    """
    inner = text[case_start:case_end]
    body_start_match = re.match(r"CASE\b", inner, re.IGNORECASE)
    body_start = body_start_match.end() if body_start_match else 0
    body_end = len(inner)
    end_match = re.search(r"\bEND\b(\s*CASE\b)?\s*$", inner, re.IGNORECASE)
    if end_match:
        body_end = end_match.start()
    body = inner[body_start:body_end]

    boundaries: List[Tuple[str, int, int]] = []
    depth = 0
    for match in _CASE_BODY_TOKEN_RE.finditer(body):
        token = match.group(0).upper()
        if token == "CASE":
            depth += 1
            continue
        if token == "END":
            depth -= 1
            continue
        if depth == 0:
            boundaries.append((token, match.start(), match.end()))

    branches: List[Dict[str, str]] = []
    else_value: Optional[str] = None
    index = 0
    total = len(boundaries)
    while index < total:
        token, start, end = boundaries[index]
        if token == "WHEN":
            then_index = index + 1
            if then_index >= total or boundaries[then_index][0] != "THEN":
                index += 1
                continue
            condition = body[end : boundaries[then_index][1]].strip()
            value_stop = boundaries[then_index + 1][1] if then_index + 1 < total else len(body)
            value = body[boundaries[then_index][2] : value_stop].strip()
            if condition and value:
                branches.append({"condition": condition, "value": value})
            index = then_index + 1
            continue
        if token == "ELSE":
            value_stop = boundaries[index + 1][1] if index + 1 < total else len(body)
            value = body[end:value_stop].strip()
            if value:
                else_value = value
            index += 1
            continue
        index += 1
    return branches, else_value


def extract_case_assignment_decision_chains(source: str) -> List[Dict[str, Any]]:
    """Deterministically extract `WHEN/THEN/ELSE` branch ladders from SQL
    `CASE` expressions that assign a single target field or column - the
    ANSI SQL construct used for multi-way business classification (e.g.
    `A.SMA_CLASS = (CASE WHEN ... THEN 'SMA_0' WHEN ... THEN 'SMA_1' ...
    ELSE NULL END)`, or `... CASE WHEN ... END AS AssetClass` in a SELECT
    projection).

    This is the CASE-expression counterpart of
    `extract_procedural_decision_chains` / `extract_nested_decision_chains`
    (which only understand PL/SQL `IF/ELSIF/ELSE ... END IF` ladders).
    `CASE ... END` is identical ANSI SQL in both Oracle PL/SQL and T-SQL,
    so this single implementation covers both dialects generically -
    unlike the procedural ladder, it is not dialect-specific.

    Deliberately conservative, matching the posture of the sibling
    functions: only a CASE expression with an unambiguous assignment
    target (either `target = (CASE ...)` / `target := CASE ...` on its
    left, or `CASE ... END AS alias` on its right) and at least two
    branches (WHEN clauses plus an optional ELSE) is emitted. Anything
    else - CASE expressions used inside a WHERE/JOIN condition, or a
    single WHEN with no ELSE - is left alone rather than guessed at.
    """
    text = _strip_sql_comments(str(source or ""))
    chains: List[Dict[str, Any]] = []
    for case_start, case_end in _find_outer_case_spans(text):
        target: Optional[str] = None
        preceding_match = _CASE_ASSIGN_TARGET_RE.search(text[:case_start])
        if preceding_match:
            target = preceding_match.group("target").strip()
        else:
            alias_match = _CASE_ALIAS_RE.match(text[case_end : case_end + 200])
            if alias_match:
                target = alias_match.group("alias").strip()
        if not target:
            continue
        field_name = target.split(".")[-1].strip()
        if not field_name or field_name.upper() in {"WHEN", "THEN", "ELSE", "CASE", "END"}:
            continue

        branches_raw, else_value = _split_top_level_case_branches(text, case_start, case_end)
        total_branches = len(branches_raw) + (1 if else_value is not None else 0)
        if total_branches < 2:
            continue

        branches: List[Dict[str, Any]] = []
        conditions_so_far: List[str] = []
        for branch in branches_raw:
            branches.append(
                {
                    "branch_condition": branch["condition"],
                    "assignments": [{"field": field_name, "value": branch["value"]}],
                }
            )
            conditions_so_far.append(branch["condition"])
        if else_value is not None:
            else_branch: Dict[str, Any] = {
                "branch_condition": "ELSE",
                "assignments": [{"field": field_name, "value": else_value}],
            }
            if conditions_so_far:
                else_branch["effective_condition"] = (
                    "all preceding conditions are false: " + "; ".join(conditions_so_far)
                )
            branches.append(else_branch)

        subject_match = re.match(r"[A-Za-z_][A-Za-z0-9_$#]*", branches_raw[0]["condition"]) if branches_raw else None
        subject = subject_match.group(0) if subject_match else field_name
        chains.append(
            {
                "chain_type": "CASE_EXPRESSION",
                "subject": subject,
                "branches": branches,
                "source_line_start": text.count("\n", 0, case_start) + 1,
                "source_line_end": text.count("\n", 0, case_end) + 1,
            }
        )
    return chains


def _decision_chain_signature(chain: Any) -> Optional[str]:
    """Normalized structural signature used to tell whether two decision
    chains are duplicates of the same source evidence (same field(s),
    same branch conditions/outcomes) versus genuinely different chains
    that both happen to touch a shared field. Whitespace/case differences
    that don't change meaning are normalized away; nothing else is.
    """
    if not isinstance(chain, dict):
        return None
    branches = chain.get("branches")
    if not isinstance(branches, list) or not branches:
        return None
    normalized_branches = []
    for branch in branches:
        if not isinstance(branch, dict):
            continue
        condition = re.sub(r"\s+", " ", str(branch.get("branch_condition") or "")).strip().lower()
        assignments = branch.get("assignments")
        pairs: List[List[str]] = []
        if isinstance(assignments, list):
            for item in assignments:
                if not isinstance(item, dict):
                    continue
                field = re.sub(r"\s+", " ", str(item.get("field") or "")).strip().lower()
                value = re.sub(r"\s+", " ", str(item.get("value") or "")).strip().lower().strip("'\"")
                if field:
                    pairs.append([field, value])
        normalized_branches.append([condition, sorted(pairs)])
    if not normalized_branches:
        return None
    return json.dumps(sorted(normalized_branches, key=str), sort_keys=True, default=str)


def merge_decision_chains(*chain_lists: List[Any]) -> List[Dict[str, Any]]:
    """Merge decision-chain lists from multiple sources (deterministic
    source-derived chains, then LLM-extracted chains, ...) into one list,
    earlier lists taking priority.

    Chains are combined, never intersected: every chain from every list is
    kept unless it is a structural duplicate (same normalized branch
    conditions and field/value assignments) of a chain already kept from
    an earlier, higher-priority list - duplicates are only ever merged
    when they are structurally equivalent, per the completeness
    requirement this function exists to satisfy. Passing deterministic,
    source-derived chains first means that when a later (e.g. LLM) chain
    for the same field is *not* a structural duplicate, both are kept:
    the deterministic chain remains authoritative for its fields (see
    `RuleSynthesizerAgent._apply_authoritative_decision_chains`, which
    processes chains in list order and lets the first chain to claim a
    field win), while the other chain can still contribute any additional
    fields the deterministic pass did not cover.
    """
    merged: List[Dict[str, Any]] = []
    seen_signatures: set[str] = set()
    for chains in chain_lists:
        if not isinstance(chains, list):
            continue
        for chain in chains:
            if not isinstance(chain, dict):
                continue
            signature = _decision_chain_signature(chain)
            if signature is not None:
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
            merged.append(chain)
    return merged


def find_semantic_anomalies(
    source: str,
    calculations: List[Dict[str, Any]] | None = None,
) -> List[str]:
    """Return review findings for suspicious, source-visible calculations."""
    text = " ".join(str(item) for item in (calculations or []))
    text = f"{source or ''} {text}"
    findings: List[str] = []
    assignments = re.findall(
        r"(?P<field>[A-Za-z_][A-Za-z0-9_$#]*)\s*:?=\s*(?P<value>[0-9]+(?:\.[0-9]+)?)",
        str(source or ""),
        re.IGNORECASE,
    )
    for field, value in assignments:
        if float(value) >= 1:
            continue
        if not re.search(rf"\b{re.escape(field)}\b\s*/\s*100\b", text, re.IGNORECASE):
            continue
        findings.append(
            f"Calculation needs review: {field} is assigned a value below 1 and then divided by 100, "
            "which may reduce the intended rate by an additional factor of 100."
        )
    return findings