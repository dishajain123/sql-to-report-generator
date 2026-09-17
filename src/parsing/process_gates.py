"""Deterministic extraction of orchestration / checkpoint gate logic.

WHY THIS MODULE EXISTS
----------------------
`extract_tsql_if_elseif_chains` (src/validation/semantic_validation.py)
deliberately only emits a decision chain when a ladder *assigns a field*
two or more distinct values across its branches - that is the correct bar
for a "decision table", and it must not be lowered, because lowering it
floods the report with one-row tables for every incidental `IF`.

Orchestrator stored procedures, however, carry essentially all of their
business meaning in a shape that bar excludes by construction: an ordered
run of checkpoint-gated steps, where each `IF` guards an `EXEC` rather
than an assignment.  The canonical corpus shape is:

    IF (SELECT Completed FROM PRO.AclRunningProcessStatus
        WHERE RunningProcessName='Reference_Period_Calculation')='Y'
    AND (SELECT Completed FROM PRO.AclRunningProcessStatus
        WHERE RunningProcessName='DPD_Calculation')='N'
    BEGIN
        INSERT INTO PRO.ProcessMonitor(...) SELECT ...,'DPD_Calculation','RUNNING',...
        EXEC PRO.DPD_Calculation @TIMEKEY=@TIMEKEY
        UPDATE PRO.PROCESSMONITOR SET MODE='COMPLETE' ... DESCRIPTION='DPD_Calculation'
    END

    IF (SELECT Completed FROM PRO.AclRunningProcessStatus
        WHERE RunningProcessName='DPD_Calculation')='N'
    BEGIN RETURN; END
    ELSE BEGIN UPDATE BANDAUDITSTATUS SET CompletedCount=CompletedCount+1 ... END

Read as business logic that is: *"run step N only once its predecessor has
completed and it has not already completed itself (so a re-run resumes
rather than repeats); if a step did not complete, abort the whole batch
instead of continuing on stale data."*  That is a resumable, checkpointed,
abort-on-failure batch contract - genuinely reportable, and previously
invisible to every deterministic extractor in the codebase.

SCOPE / SAFETY
--------------
This module is strictly **additive**.  It emits its own record type
(`process_gates`) and never produces `decision_chain` records, so it
cannot alter decision-table identity, merging, coverage floors, dedup, or
IR matching.  It is deliberately conservative: a gate is only emitted when
the guard genuinely reads a status/checkpoint table, so ordinary business
`IF`s are never reinterpreted as orchestration.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.core.pipeline_utils import stable_id
from src.parsing.sql_comments import executable_sql

# --------------------------------------------------------------------------
# Recognition patterns
# --------------------------------------------------------------------------

# A status/checkpoint table is one whose name carries a run-state meaning.
# Matching on the *name* keeps this generic across installations (the corpus
# uses AclRunningProcessStatus; other deployments use ProcessStatus,
# BatchRunStatus, JobControl, ...) without hardcoding any single table.
_STATUS_TABLE_RE = re.compile(
    r"(?i)\b(?:\w+\.)?(\[?\w*(?:RunningProcess|ProcessStatus|RunStatus|BatchStatus|"
    r"JobStatus|JobControl|ProcessControl|RunControl|Checkpoint)\w*\]?)\b"
)

# `(SELECT <state_col> FROM <status_table> WHERE <key_col> = '<step>') = '<value>'
_GATE_TERM_RE = re.compile(
    r"(?is)\(\s*SELECT\s+(?P<state_col>[\w\[\]]+)\s+FROM\s+(?P<table>[\w\.\[\]]+)\s+"
    r"WHERE\s+(?P<key_col>[\w\[\]]+)\s*=\s*'(?P<step>[^']+)'\s*\)\s*"
    r"(?P<op>=|<>|!=)\s*'(?P<value>[^']*)'"
)

_IF_START_RE = re.compile(r"(?im)^[ \t]*IF\b")
_EXEC_RE = re.compile(r"(?i)\b(?:EXEC|EXECUTE)\s+(?P<proc>\[?\w+\]?(?:\.\[?\w+\]?)*)")
_RETURN_RE = re.compile(r"(?i)\bRETURN\b\s*;?")
_MONITOR_DESC_RE = re.compile(r"(?i)'(?P<desc>[A-Za-z_][\w]*)'\s*,\s*'RUNNING'")

_BEGIN_RE = re.compile(r"(?i)^\s*BEGIN\b")
_END_RE = re.compile(r"(?i)^\s*END\b")
_ELSE_RE = re.compile(r"(?i)^\s*ELSE\b")

# Statements that are pure run-bookkeeping rather than business writes.
_BOOKKEEPING_TABLE_RE = re.compile(
    r"(?i)\b(?:\w+\.)?(?:ProcessMonitor|BandAuditStatus|AuditStatus|RunLog|JobLog)\b"
)


def _is_status_table(name: str) -> bool:
    return bool(_STATUS_TABLE_RE.search(str(name or "")))


def _clean_ident(name: str) -> str:
    return str(name or "").replace("[", "").replace("]", "").strip()


def _block_bounds(text: str, search_from: int) -> Optional[tuple]:
    """Return (body_start, body_end) of the BEGIN...END block that follows
    ``search_from``, honouring nesting. Falls back to a single statement
    when the branch has no BEGIN/END wrapper.
    """
    probe = text[search_from:]
    match = re.search(r"(?is)^\s*BEGIN\b", probe)
    if not match:
        # Single-statement branch: up to the next blank line or next IF.
        stop = re.search(r"(?im)^\s*$|^[ \t]*IF\b", probe[1:])
        end = search_from + 1 + (stop.start() if stop else len(probe) - 1)
        return (search_from, end)

    pos = search_from + match.end()
    depth = 1
    token = re.compile(r"(?i)\b(BEGIN|END)\b")
    while depth > 0:
        nxt = token.search(text, pos)
        if not nxt:
            return (search_from + match.end(), len(text))
        # `BEGIN TRY` / `BEGIN CATCH` still open a block; `END TRY`/`END CATCH`
        # still close one, so plain keyword counting stays balanced.
        if nxt.group(1).upper() == "BEGIN":
            depth += 1
        else:
            depth -= 1
        pos = nxt.end()
    return (search_from + match.end(), pos)


def _executed_procedures(body: str) -> List[str]:
    seen, out = set(), []
    for match in _EXEC_RE.finditer(body):
        proc = _clean_ident(match.group("proc"))
        if not proc or proc.lower().startswith("sp_"):
            continue
        if proc.lower() not in seen:
            seen.add(proc.lower())
            out.append(proc)
    return out


def _describe_gate(terms: List[Dict[str, str]], step: str) -> str:
    """Plain-language precondition text, in source order."""
    parts = []
    for term in terms:
        negated = term["op"] in {"<>", "!="}
        done = (term["value"].upper() in {"Y", "YES", "1", "TRUE", "C", "COMPLETE", "COMPLETED"})
        if negated:
            done = not done
        if term["step"].lower() == str(step or "").lower():
            parts.append(
                f"'{term['step']}' has already completed" if done
                else f"'{term['step']}' has not yet completed"
            )
        else:
            parts.append(
                f"'{term['step']}' has completed" if done
                else f"'{term['step']}' has not completed"
            )
    return " and ".join(parts)


def extract_process_gates(source: str, dialect: str = "tsql") -> List[Dict[str, Any]]:
    """Extract ordered checkpoint-gated orchestration steps.

    Returns one record per guarded block, in source order. Returns ``[]``
    for any object that is not orchestration-shaped, which is the common
    case - the cost on a normal business procedure is a single regex scan.
    """
    if str(dialect or "").strip().lower() not in {"tsql", "", "auto"}:
        return []

    text = executable_sql(str(source or ""))
    if not text or not _STATUS_TABLE_RE.search(text):
        return []

    gates: List[Dict[str, Any]] = []
    sequence = 0
    # Highest body end offset emitted so far. An `IF` that begins before
    # this point sits *inside* a block we already reported, so it is a
    # nested guard, not a new orchestration step - emitting it would
    # double-count the enclosing step (the enclosing block's own
    # guard terms are still visible to the inner match).
    consumed_until = -1

    for if_match in _IF_START_RE.finditer(text):
        start = if_match.start()
        if start < consumed_until:
            continue
        # The guard runs from IF up to the branch body (BEGIN, or the first
        # statement when unwrapped). Bound the search so a missing BEGIN
        # cannot swallow the rest of the procedure.
        window = text[start:start + 4000]
        begin_rel = re.search(r"(?im)^\s*BEGIN\b", window)
        guard_text = window[: begin_rel.start()] if begin_rel else window[:600]

        terms = [
            {
                "state_column": _clean_ident(m.group("state_col")),
                "table": _clean_ident(m.group("table")),
                "key_column": _clean_ident(m.group("key_col")),
                "step": m.group("step").strip(),
                "op": m.group("op"),
                "value": m.group("value").strip(),
            }
            for m in _GATE_TERM_RE.finditer(guard_text)
            if _is_status_table(m.group("table"))
        ]
        if not terms:
            continue

        body_start = start + (begin_rel.start() if begin_rel else len(guard_text))
        bounds = _block_bounds(text, body_start)
        if not bounds:
            continue
        body = text[bounds[0]:bounds[1]]

        procedures = _executed_procedures(body)
        aborts = bool(_RETURN_RE.search(body)) and not procedures

        # The step this gate governs: the EXEC'd procedure when present,
        # else the ProcessMonitor description, else the self-referencing
        # guard term (the one tested for "not yet completed").
        step_name = ""
        if procedures:
            step_name = procedures[0].split(".")[-1]
        if not step_name:
            desc = _MONITOR_DESC_RE.search(body)
            if desc:
                step_name = desc.group("desc")
        if not step_name:
            pending = [t for t in terms if t["value"].upper() in {"N", "NO", "0", "FALSE"}]
            step_name = (pending or terms)[-1]["step"]

        if aborts:
            gate_type = "abort_if_incomplete"
        elif procedures:
            gate_type = "run_step"
        else:
            gate_type = "guarded_block"

        sequence += 1
        consumed_until = max(consumed_until, bounds[1])
        gates.append(
            {
                "gate_id": stable_id("gate", step_name, sequence, gate_type),
                "sequence": sequence,
                "gate_type": gate_type,
                "step_name": step_name,
                "preconditions": terms,
                "precondition_text": _describe_gate(terms, step_name),
                "executed_procedures": procedures,
                "aborts_run": aborts,
                "status_table": terms[0]["table"],
                "source_char_start": start,
                "source_char_end": bounds[1],
                "source_line_start": text.count("\n", 0, start) + 1,
                "bookkeeping_only": (
                    not procedures
                    and bool(_BOOKKEEPING_TABLE_RE.search(body))
                ),
            }
        )

    return gates


def summarize_process_gates(gates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Roll gates up into the facts a report needs about the run contract."""
    if not gates:
        return {}
    steps = [g["step_name"] for g in gates if g["gate_type"] == "run_step"]
    ordered, seen = [], set()
    for step in steps:
        if step.lower() not in seen:
            seen.add(step.lower())
            ordered.append(step)
    return {
        "total_gates": len(gates),
        "step_count": len(ordered),
        "execution_order": ordered,
        "aborting_gates": sum(1 for g in gates if g["aborts_run"]),
        "resumable": any(
            any(t["value"].upper() in {"N", "NO", "0", "FALSE"}
                and t["step"].lower() == g["step_name"].lower()
                for t in g["preconditions"])
            for g in gates if g["gate_type"] == "run_step"
        ),
        "status_tables": sorted({g["status_table"] for g in gates}),
    }