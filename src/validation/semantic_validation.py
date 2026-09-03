"""Deterministic semantic checks for source-to-report consistency."""

from __future__ import annotations

import re
from typing import Any, Dict, List


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
