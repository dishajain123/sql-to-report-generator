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


def _source_line_records(source: str) -> List[Dict[str, Any]]:
    """Return exact line/character offsets without guessing missing locations."""
    text = str(source or "")
    records: List[Dict[str, Any]] = []
    offset = 0
    for line_number, raw_line in enumerate(text.splitlines(keepends=True), start=1):
        line = raw_line.rstrip("\r\n")
        end = offset + len(line)
        records.append(
            {
                "line": line,
                "line_number": line_number,
                "char_start": offset,
                "char_end": end,
            }
        )
        offset += len(raw_line)
    if text and not records:
        records.append({"line": text, "line_number": 1, "char_start": 0, "char_end": len(text)})
    return records


def _source_provenance(
    source: str,
    start: int,
    end: int,
    *,
    chain_id: str = "",
    branch_id: str = "",
) -> Dict[str, Any]:
    """Build one existing evidence-span-shaped provenance record."""
    text = str(source or "")
    if start < 0 or end < start or end > len(text):
        return {
            "char_start": -1,
            "char_end": -1,
            "line_start": -1,
            "line_end": -1,
            "source_location_status": "unavailable",
            "chain_id": chain_id,
            "branch_id": branch_id,
        }
    line_starts = [0]
    line_starts.extend(index + 1 for index, value in enumerate(text) if value == "\n")
    def line_for(offset: int) -> int:
        return max((index for index, value in enumerate(line_starts) if value <= offset), default=0) + 1
    return {
        "char_start": start,
        "char_end": end,
        "line_start": line_for(start),
        "line_end": line_for(max(end - 1, start)),
        "source_location_status": "available",
        "chain_id": chain_id,
        "branch_id": branch_id,
    }


def _line_provenance(
    source: str,
    records: List[Dict[str, Any]],
    start_index: int,
    end_index: int,
    *,
    chain_id: str = "",
    branch_id: str = "",
) -> Dict[str, Any]:
    if not records or start_index < 0 or end_index < start_index or end_index >= len(records):
        return _source_provenance(source, -1, -1, chain_id=chain_id, branch_id=branch_id)
    return _source_provenance(
        source,
        records[start_index]["char_start"],
        records[end_index]["char_end"],
        chain_id=chain_id,
        branch_id=branch_id,
    )


def _apply_branch_provenance(
    branch: Dict[str, Any], provenance: Dict[str, Any], *, chain_id: str, branch_index: int
) -> Dict[str, Any]:
    branch_id = f"{chain_id}:branch_{branch_index + 1:03d}"
    span = dict(provenance)
    span["chain_id"] = chain_id
    span["branch_id"] = branch_id
    result = dict(branch)
    existing_spans = [dict(item) for item in result.get("evidence_spans", []) if isinstance(item, dict)]
    if not existing_spans:
        existing_spans = [span]
    for existing_span in existing_spans:
        existing_span.setdefault("chain_id", chain_id)
        existing_span.setdefault("branch_id", branch_id)
    result.update(
        {
            "chain_id": chain_id,
            "branch_id": branch_id,
            "source_char_start": span.get("char_start", -1),
            "source_char_end": span.get("char_end", -1),
            "source_line_start": span.get("line_start", -1),
            "source_line_end": span.get("line_end", -1),
            "source_location_status": span.get("source_location_status", "unavailable"),
            "evidence_spans": existing_spans,
        }
    )
    return result


def extract_procedural_decision_chains(source: str) -> List[Dict[str, Any]]:
    """Extract simple PL/SQL IF/ELSIF/ELSE assignment ladders deterministically.

    This deliberately handles only a complete, unambiguous ladder. It does
    not guess through nested control flow, SQL statements, or dynamic code.
    """
    source_text = _strip_sql_comments(str(source or ""))
    records = _source_line_records(source_text)
    lines = [record["line"] for record in records]
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
        chain_start = index

        def finish_branch(end_index: int) -> None:
            branches.append(
                {
                    "branch_condition": current_condition,
                    "assignments": assignments,
                    "_start_index": branch_start,
                    "_end_index": max(branch_start, end_index),
                }
            )

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
                    finish_branch(index - 1)
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
                    finish_branch(index - 1)
                    current_condition = next_condition
                    assignments = []
                    branch_start = index
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
            chain_id = f"procedural_if_{chain_start + 1:04d}_{index + 1:04d}"
            for branch_index, branch in enumerate(branches):
                if branch["branch_condition"].upper() == "ELSE":
                    branch["effective_condition"] = (
                        "all preceding conditions are false or NULL: " + "; ".join(previous[:-1])
                    )
                provenance = _line_provenance(
                    source_text,
                    records,
                    branch.pop("_start_index"),
                    branch.pop("_end_index"),
                )
                branches[branch_index] = _apply_branch_provenance(
                    branch, provenance, chain_id=chain_id, branch_index=branch_index
                )
            chains.append({
                "chain_type": "IF_ELSIF_ELSE",
                "subject": subject,
                "branches": branches,
                "chain_id": chain_id,
                "source_char_start": records[chain_start]["char_start"],
                "source_char_end": records[index]["char_end"],
                "source_line_start": chain_start + 1,
                "source_line_end": index + 1,
                "source_location_status": "available",
            })
        index += 1
    return chains


def extract_nested_decision_chains(source: str) -> List[Dict[str, Any]]:
    """Extract complete leaf paths from nested procedural IF ladders.

    Unlike a flat regex pass, this keeps each child outcome attached to its
    parent path. It deliberately emits only ladders with at least two
    categorical outcomes and never interprets SQL statements as branches.
    """
    source_text = _strip_sql_comments(str(source or ""))
    source_records = _source_line_records(source_text)
    line_records = [record for record in source_records if record["line"].strip()]
    lines = [record["line"] for record in line_records]

    def assignment(line: str) -> Dict[str, str] | None:
        match = _ASSIGNMENT_RE.match(line)
        if not match:
            return None
        return {"field": match.group("field").strip(), "value": match.group("value").strip().rstrip(";").strip()}

    def parse_if(position: int, parents: List[str]) -> tuple[List[Dict[str, Any]], int, int, int]:
        if_start = position
        first = _IF_RE.match(lines[position])
        if not first:
            return [], position + 1, if_start, position
        branches: List[Dict[str, Any]] = []
        condition = first.group(1).strip()
        preceding_conditions: List[str] = []
        condition_index = position
        position += 1
        while position < len(lines):
            direct: List[Dict[str, str]] = []
            nested_paths: List[Dict[str, Any]] = []
            while position < len(lines):
                if _IF_RE.match(lines[position]):
                    nested_paths, position, _, _ = parse_if(position, parents + [condition])
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
            # An ELSE parent contributes no predicate of its own. Keeping the
            # marker in a nested path produces invalid conditions such as
            # ``ELSE AND child_condition`` and prevents structural matching
            # against the synthesized branch. Preserve the ELSE branch at
            # the level where it is rendered, but omit it from child paths.
            path_parts = [item for item in parents if str(item).strip().upper() != "ELSE"]
            if effective_condition.upper() != "ELSE":
                path_parts.append(effective_condition)
            path_condition = " AND ".join(path_parts) or "ELSE"
            if nested_paths:
                for nested in nested_paths:
                    assignments = list(direct) + list(nested.get("assignments", []))
                    parent_span = _line_provenance(
                        source_text, line_records, condition_index, max(condition_index, position - 1)
                    )
                    nested_spans = list(nested.get("evidence_spans") or [])
                    if not nested_spans and isinstance(nested.get("_provenance"), dict):
                        nested_spans = [nested["_provenance"]]
                    branches.append(
                        {
                            "branch_condition": nested["branch_condition"],
                            "assignments": assignments,
                            "evidence_spans": [parent_span, *nested_spans],
                        }
                    )
            else:
                branches.append(
                    {
                        "branch_condition": path_condition,
                        "assignments": direct,
                        "_provenance": _line_provenance(
                            source_text,
                            line_records,
                            condition_index,
                            max(condition_index, position - 1),
                        ),
                    }
                )

            if condition.upper() != "ELSE":
                preceding_conditions.append(condition)
            if position >= len(lines) or _END_IF_RE.match(lines[position]):
                end_index = position
                if branches:
                    for branch in branches:
                        if "_provenance" not in branch:
                            spans = branch.get("evidence_spans") or []
                            branch["_provenance"] = spans[-1] if spans else _line_provenance(
                                source_text, line_records, condition_index, condition_index
                            )
                return branches, position + 1, if_start, end_index
            elsif = _ELSIF_RE.match(lines[position])
            condition = elsif.group(1).strip() if elsif else "ELSE"
            condition_index = position
            position += 1
        return branches, position, if_start, max(if_start, position - 1)

    chains: List[Dict[str, Any]] = []
    position = 0
    while position < len(lines):
        if not _IF_RE.match(lines[position]):
            position += 1
            continue
        branches, position, chain_start, chain_end = parse_if(position, [])
        fields = {item["field"] for branch in branches for item in branch["assignments"] if item.get("field")}
        outcomes = {
            item["value"] for branch in branches for item in branch["assignments"] if item.get("value")
        }
        if len(branches) >= 2 and fields and len(outcomes) >= 2:
            chain_id = f"nested_if_{line_records[chain_start]['line_number']:04d}_{line_records[chain_end]['line_number']:04d}"
            for branch_index, branch in enumerate(branches):
                provenance = branch.pop("_provenance", _source_provenance(source_text, -1, -1))
                branches[branch_index] = _apply_branch_provenance(
                    branch, provenance, chain_id=chain_id, branch_index=branch_index
                )
            chains.append(
                {
                    "chain_type": "NESTED_IF",
                    "subject": "",
                    "branches": branches,
                    "chain_id": chain_id,
                    "source_char_start": line_records[chain_start]["char_start"],
                    "source_char_end": line_records[chain_end]["char_end"],
                    "source_line_start": line_records[chain_start]["line_number"],
                    "source_line_end": line_records[chain_end]["line_number"],
                    "source_location_status": "available",
                }
            )
    return chains


_CASE_KEYWORD_RE = re.compile(r"\bCASE\b|\bEND\b", re.IGNORECASE)
_CASE_BODY_TOKEN_RE = re.compile(r"\bCASE\b|\bEND\b|\bWHEN\b|\bTHEN\b|\bELSE\b", re.IGNORECASE)
_CASE_ASSIGN_TARGET_RE = re.compile(
    r"(?P<target>@?[A-Za-z_][A-Za-z0-9_$#]*(?:\.[A-Za-z_][A-Za-z0-9_$#]*)?)\s*(?::=|=)\s*\(?\s*$"
)
_CASE_ALIAS_RE = re.compile(
    r"^\s*(?P<closing>\)?)\s*(?:AS\s+)?(?P<alias>[A-Za-z_][A-Za-z0-9_$#]*)\b"
    r"(?=\s*(?:,|;|FROM\b|INTO\b|$))", re.IGNORECASE,
)
_CASE_ALIAS_STOPWORDS = {"FROM", "INTO", "WHERE", "GROUP", "ORDER", "HAVING", "AND", "OR", "WHEN", "THEN", "ELSE", "END", "AS"}


def _case_scan_text(text: str) -> str:
    # Keywords inside SQL literals and quoted identifiers are data. Preserve
    # coordinates so branch expressions can still be sliced from real text.
    return re.sub(
        r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|\[(?:\]\]|[^\]])*\]",
        lambda m: "".join(c if c in "\r\n" else " " for c in m.group()), text,
    )


def _strip_sql_comments(source: str) -> str:
    from src.parsing.sql_comments import executable_sql
    return executable_sql(source)


def _find_outer_case_spans(text: str) -> List[Tuple[int, int]]:
    """Return (start, end) character spans of every outermost `CASE ...
    END` expression in `text` (which must already have comments blanked
    via `_strip_sql_comments`). A nested `CASE ... END` is consumed as
    part of its parent's span, never returned as its own top-level span.
    """
    spans: List[Tuple[int, int]] = []
    stack: List[int] = []
    for match in _CASE_KEYWORD_RE.finditer(_case_scan_text(text)):
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
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
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
    for match in _CASE_BODY_TOKEN_RE.finditer(_case_scan_text(body)):
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
    else_value: Optional[Dict[str, Any]] = None
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
            operand = body[:boundaries[0][1]].strip()
            if operand:
                condition = f"{operand} = {condition}"
            value_stop = boundaries[then_index + 1][1] if then_index + 1 < total else len(body)
            value = body[boundaries[then_index][2] : value_stop].strip()
            if condition and value:
                branches.append(
                    {
                        "condition": condition,
                        "value": value,
                        "source_start": case_start + body_start + start,
                        "source_end": case_start + body_start + value_stop,
                    }
                )
            index = then_index + 1
            continue
        if token == "ELSE":
            value_stop = boundaries[index + 1][1] if index + 1 < total else len(body)
            value = body[end:value_stop].strip()
            if value:
                else_value = {
                    "value": value,
                    "source_start": case_start + body_start + start,
                    "source_end": case_start + body_start + value_stop,
                }
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
        aggregation = ""
        preceding_match = _CASE_ASSIGN_TARGET_RE.search(text[:case_start])
        if preceding_match:
            target = preceding_match.group("target").strip()
        else:
            alias_match = _CASE_ALIAS_RE.match(text[case_end : case_end + 200])
            if alias_match and alias_match.group("alias").upper() not in _CASE_ALIAS_STOPWORDS:
                wrapper = re.search(r"\b([A-Za-z_][\w$#]*)\s*\(\s*$", text[:case_start])
                if wrapper:
                    # The branch produces an input to an aggregate, not the
                    # final grouped result. Preserve that distinction.
                    if wrapper.group(1).upper() not in {"MAX", "MIN", "SUM", "AVG"} or not alias_match.group("closing"):
                        continue
                    aggregation = wrapper.group(1).upper()
                target = alias_match.group("alias").strip()
        if not target:
            continue
        field_name = target.split(".")[-1].strip()
        if not field_name or field_name.upper() in {"WHEN", "THEN", "ELSE", "CASE", "END"}:
            continue

        branches_raw, else_value = _split_top_level_case_branches(text, case_start, case_end)
        implicit_default = bool(branches_raw) and else_value is None
        if implicit_default:
            else_value = {"value": "NULL", "source_start": case_end - 3, "source_end": case_end}
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
                    "_provenance": _source_provenance(
                        str(source or ""), branch["source_start"], branch["source_end"]
                    ),
                }
            )
            conditions_so_far.append(branch["condition"])
        if else_value is not None:
            else_branch: Dict[str, Any] = {
                "branch_condition": "ELSE",
                "implicit_default": implicit_default,
                "assignments": [{"field": field_name, "value": else_value["value"]}],
                "_provenance": _source_provenance(
                    str(source or ""), else_value["source_start"], else_value["source_end"]
                ),
            }
            if conditions_so_far:
                else_branch["effective_condition"] = (
                    "all preceding conditions are false or NULL: " + "; ".join(conditions_so_far)
                )
            branches.append(else_branch)

        subject_match = re.match(r"[A-Za-z_][A-Za-z0-9_$#]*", branches_raw[0]["condition"]) if branches_raw else None
        subject = subject_match.group(0) if subject_match else field_name
        chain_id = f"case_{text.count(chr(10), 0, case_start) + 1:04d}_{text.count(chr(10), 0, case_end) + 1:04d}_{case_start}"
        for branch_index, branch in enumerate(branches):
            provenance = branch.pop("_provenance", _source_provenance(str(source or ""), -1, -1))
            branches[branch_index] = _apply_branch_provenance(
                branch, provenance, chain_id=chain_id, branch_index=branch_index
            )
        chains.append(
            {
                "chain_type": "CASE_EXPRESSION",
                "aggregation": aggregation,
                "subject": subject,
                "branches": branches,
                "chain_id": chain_id,
                "source_char_start": case_start,
                "source_char_end": case_end,
                "source_line_start": text.count("\n", 0, case_start) + 1,
                "source_line_end": text.count("\n", 0, case_end) + 1,
                "source_location_status": "available",
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
    chain_type = str(chain.get("chain_type") or "").strip().upper()
    for branch_index, branch in enumerate(branches):
        if not isinstance(branch, dict):
            continue
        from src.parsing.decision_identity import decision_text_key
        condition = decision_text_key(branch.get("branch_condition"))
        # The nested extractor represents a flat ladder's final ELSE as the
        # effective predicate ``NOT(A) AND NOT(B)``. The procedural ladder
        # extractor represents the same branch as literal ELSE. Normalize
        # only that final nested fallback for deduplication; explicit final
        # conditions and genuinely nested leaf paths remain distinct.
        if (
            chain_type == "NESTED_IF"
            and branch_index == len(branches) - 1
            and re.match(r"^not\s*\(", condition)
        ):
            condition = "else"
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
    return json.dumps([str(chain.get("aggregation") or ""), normalized_branches], sort_keys=True, default=str)


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
    seen_signatures: Dict[str, List[Dict[str, Any]]] = {}
    for chains in chain_lists:
        if not isinstance(chains, list):
            continue
        for chain in chains:
            if not isinstance(chain, dict):
                continue
            signature = _decision_chain_signature(chain)
            if signature is not None:
                earlier = seen_signatures.setdefault(signature, [])
                def distinct_occurrence(previous):
                    start = chain.get("source_char_start", -1)
                    previous_start = previous.get("source_char_start", -1)
                    return (isinstance(start, int) and isinstance(previous_start, int)
                            and start >= 0 and previous_start >= 0 and start != previous_start)
                if any(not distinct_occurrence(previous) for previous in earlier):
                    continue
                earlier.append(chain)
            merged.append(chain)
    return merged


def find_semantic_anomalies(
    source: str,
    calculations: List[Dict[str, Any]] | None = None,
) -> List[str]:
    """Return uncertainty notices for calculations needing human context.

    Static SQL text does not establish units, scale conventions, or intended
    business outcomes. This check therefore must not label a calculation as
    incorrect from numeric literals alone.
    """
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
        if not re.search(
            rf"\b{re.escape(field)}\b\s*/\s*(?:[0-9]+(?:\.[0-9]+)?|[A-Za-z_][A-Za-z0-9_$#]*)\b",
            text,
            re.IGNORECASE,
        ):
            continue
        findings.append(
            f"Calculation uncertainty: `{field}` uses a fractional numeric value "
            "in an expression that divides by a constant; the intended unit or "
            "scale cannot be established from SQL text alone."
        )
    return findings
