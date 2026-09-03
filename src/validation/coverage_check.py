"""Deterministic, content-blind completeness checking for synthesized
business rules.

This module never authors, edits, or overwrites business logic - it is
not a rule extractor. It answers a narrow, purely syntactic question:
does every source-visible decision, assignment, or calculation anchor
fall within a source region that at least one synthesized rule's evidence
appears to cover?

Why this exists (and why it looks the way it does): an earlier version of
this pipeline used a similar keyword scan to *reconstruct* rule branches
directly from CASE/IF source text and splice that reconstruction into
`business_rules` (see `src/validation/semantic_validation.py`'s
`extract_case_assignment_decision_chains` /
`extract_procedural_decision_chains`, still used as a narrower,
conservative normalization safety net for the specific single-target
ladder shapes they recognize). That approach caps correctness at whatever
constructs the regex anticipated, and - more importantly - it means a
regex, not the model, ends up authoring business content.

This module intentionally does the opposite: it never parses branch
*meaning* (conditions, values, field assignments), it never writes to
`business_rules`, and it makes no assumption about which SQL construct
carries business logic. It only marks *where* a decision point exists
(by keyword + line range) and, orthogonally, whether the model's own
output ended up mentioning that location. When it doesn't, the caller is
expected to hand the exact gap back to the model (see
`RuleSynthesizerAgent.revise` in `src/synthesis/rule_synthesizer.py`) so
a human-equivalent reviewer - the LLM - decides what belongs there, not a
regex. Because the check is purely lexical (keyword positions + token
overlap), it generalizes to constructs nobody anticipated - a WHILE loop
driving a business flag, a MERGE's matched/not-matched branches, a
windowed CTE - without needing a dedicated parser for each one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Set


# Keywords that mark a source-visible decision point. Deliberately broad
# and dialect-agnostic (ANSI SQL / T-SQL / PL-SQL all share this
# vocabulary) rather than tied to any one construct; there is no attempt
# to determine WHICH of these actually carries business logic - anything
# purely technical is expected to simply not be cited by any rule,
# which is fine (see `_TECHNICAL_ONLY_KEYWORDS_NOTE` below).
_DECISION_KEYWORD_RE = re.compile(
    r"\bCASE\b|\bWHEN\b|\bIF\b|\bELSIF\b|\bELSEIF\b", re.IGNORECASE
)
_STATEMENT_START_RE = re.compile(
    r"(?:^|;)\s*(?P<keyword>UPDATE|INSERT|DELETE|MERGE)\b", re.IGNORECASE
)
_SET_RE = re.compile(r"\bSET\b", re.IGNORECASE)
_SET_ASSIGNMENT_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*\b\s*=", re.IGNORECASE
)
_WALRUS_ASSIGNMENT_RE = re.compile(r":=")
_SELECT_RE = re.compile(r"\bSELECT\b", re.IGNORECASE)
_FROM_RE = re.compile(r"\bFROM\b", re.IGNORECASE)
_SET_CLAUSE_END_RE = re.compile(
    r"\b(?:WHERE|FROM|ON|GROUP|ORDER|HAVING|RETURNING)\b", re.IGNORECASE
)
_CALCULATION_RE = re.compile(
    r"\b(?:SUM|AVG|MIN|MAX|COUNT|ROUND|ABS|COALESCE|GREATEST)\s*\(|"
    r"\b[A-Za-z_][A-Za-z0-9_]*\s*[+*/%]\s*[A-Za-z_][A-Za-z0-9_]*\b",
    re.IGNORECASE,
)

# Generic SQL/procedural stopwords excluded from token-overlap matching so
# coverage isn't "detected" just because both the source line and some
# unrelated rule happen to use the words THEN/AND/NULL/etc. This list is
# syntax-level, not domain-level - it contains no business terms.
_STOPWORDS: Set[str] = {
    "the", "and", "or", "not", "is", "in", "on", "as", "then", "else",
    "end", "case", "when", "if", "elsif", "elseif", "null", "select",
    "from", "where", "set", "update", "insert", "into", "values",
    "begin", "declare", "between", "isnull", "coalesce", "cast",
    "exists", "with", "join", "inner", "outer", "left", "right", "over",
    "partition", "order", "by", "group", "having", "distinct", "top",
    "true", "false", "like", "for", "loop", "while", "return", "exec",
    "execute", "procedure", "function", "table", "int", "varchar", "date",
    "datetime", "float", "decimal",
}
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")

# How close two decision-point line numbers must be to be treated as part
# of the same ladder/block for reporting purposes, so one 10-branch CASE
# is reported as one gap, not ten.
_LINE_GROUPING_GAP = 2
# Minimum fraction of a block's meaningful tokens that must appear
# somewhere in the synthesized rules' combined evidence text for the
# block to be considered covered. Deliberately lenient (favors NOT
# flagging a gap) because this is a coarse pre-filter ahead of a real LLM
# review, not a correctness judgment in itself - a low threshold keeps
# the retry loop bounded to genuine gaps rather than firing on every
# paraphrase.
_COVERAGE_TOKEN_THRESHOLD = 0.3


@dataclass
class CoverageGap:
    """One source region containing a decision-point keyword that no
    synthesized rule's evidence appears to reference."""

    line_start: int
    line_end: int
    snippet: str
    keywords: List[str] = field(default_factory=list)


def _strip_comments_and_strings_for_scan(source: str) -> str:
    """Same-length copy of `source` with comments blanked (so a keyword
    appearing only in a comment is never counted as a decision point) and
    string-literal interiors blanked too (so a business description
    inside a quoted string can't spuriously match a keyword or inflate
    token overlap). Newlines are preserved so line numbers stay accurate.
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
            for k in range(i, min(j, n)):
                if text[k] != "\n":
                    result[k] = " "
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


def _scan_line_keywords(source: str) -> Dict[int, List[str]]:
    """Return lexical coverage anchors grouped by source line.

    This intentionally tracks only enough statement context to distinguish a
    SET assignment from an ordinary WHERE equality and a SELECT projection
    assignment. It does not parse SQL or interpret the expression on either
    side of an operator.
    """
    text = _strip_comments_and_strings_for_scan(source)
    anchors: Dict[int, List[str]] = {}
    in_set_clause = False
    in_select_projection = False

    for lineno, line in enumerate(text.splitlines(), start=1):
        keywords = [match.group(0).upper() for match in _DECISION_KEYWORD_RE.finditer(line)]

        statement_starts = list(_STATEMENT_START_RE.finditer(line))
        keywords.extend(match.group("keyword").upper() for match in statement_starts)

        # A new statement resets the lightweight clause context. Semicolons
        # are the only statement boundary needed for this position scan.
        if statement_starts or re.search(r"(?:^|;)\s*SELECT\b", line, re.IGNORECASE):
            in_set_clause = False
            in_select_projection = bool(
                re.search(r"(?:^|;)\s*SELECT\b", line, re.IGNORECASE)
            )

        select_match = _SELECT_RE.search(line)
        if select_match:
            in_select_projection = True
        from_match = _FROM_RE.search(line)
        if from_match and in_select_projection:
            in_select_projection = False

        set_match = _SET_RE.search(line)
        if set_match:
            in_set_clause = True

        clause_end = _SET_CLAUSE_END_RE.search(line)
        assignment_prefix = line if clause_end is None else line[: clause_end.start()]

        # := is an assignment anchor unless it is part of a SELECT
        # projection. A plain '=' is only an assignment anchor in SET
        # context, preventing every WHERE comparison from becoming a gap.
        if not in_select_projection and _WALRUS_ASSIGNMENT_RE.search(assignment_prefix):
            keywords.append("ASSIGNMENT")
        if in_set_clause and _SET_ASSIGNMENT_RE.search(assignment_prefix):
            keywords.append("ASSIGNMENT")

        if clause_end is not None:
            in_set_clause = False
        if keywords:
            anchors[lineno] = sorted(set(keywords))

    return anchors


def find_decision_points(source: str) -> List[Dict[str, Any]]:
    """Return every (line_number, keyword) decision-point occurrence in
    `source`. Purely a keyword position scan - no branch/condition/value
    parsing, no dialect-specific grammar, so it never goes stale as new
    constructs are added to the source and never needs updating for a
    dialect this pipeline doesn't yet special-case.
    """
    points: List[Dict[str, Any]] = []
    for lineno, keywords in _scan_line_keywords(source).items():
        points.extend({"line": lineno, "keyword": keyword} for keyword in keywords)
    return points


def _find_coverage_anchors(source: str) -> Dict[int, List[str]]:
    """Find syntax-only source lines worth checking for citation.

    Decision keywords are useful, but they are not the definition of
    business logic. Assignment and calculation anchors catch meaningful
    straight-line SQL as well as constructs whose branching vocabulary is
    unfamiliar to this module. The patterns identify locations only; they
    never interpret an expression or create a rule.
    """
    text = _strip_comments_and_strings_for_scan(source)
    anchors = _scan_line_keywords(source)
    for lineno, line in enumerate(text.splitlines(), start=1):
        keywords = anchors.get(lineno, [])
        had_update = "UPDATE" in keywords
        if "ASSIGNMENT" in keywords:
            # The assignment is the actionable anchor on an UPDATE/INSERT
            # header; retaining both would make one statement look like two
            # independent uncovered regions.
            anchors[lineno] = [
                keyword for keyword in keywords if keyword not in {"UPDATE", "INSERT"}
            ]
            keywords = anchors[lineno]
        if line.rstrip().endswith("=") and had_update:
            # A value continued on the next line is not useful evidence by
            # itself, and the statement header is already represented by the
            # following concrete branch/calculation anchor when present.
            anchors[lineno] = [
                keyword for keyword in keywords if keyword not in {"UPDATE", "ASSIGNMENT"}
            ]
            keywords = anchors[lineno]
        if _CALCULATION_RE.search(line):
            anchors.setdefault(lineno, []).append("CALCULATION")
            anchors[lineno] = sorted(set(anchors[lineno]))
        if not anchors.get(lineno):
            anchors.pop(lineno, None)
    return anchors


def _group_lines(line_numbers: Sequence[int], max_gap: int = _LINE_GROUPING_GAP) -> List[List[int]]:
    ordered = sorted(set(line_numbers))
    groups: List[List[int]] = []
    for line in ordered:
        if groups and line - groups[-1][-1] <= max_gap:
            groups[-1].append(line)
        else:
            groups.append([line])
    return groups


def _tokens(text: str) -> Set[str]:
    return {
        token.lower()
        for token in _TOKEN_RE.findall(str(text or ""))
        if token.lower() not in _STOPWORDS
    }


def _dml_predicate_tokens_by_line(source: str) -> Dict[int, Set[str]]:
    """Map each line in a DML statement to that statement's predicate tokens.

    This is intentionally a lexical statement/clause scan, not SQL parsing.
    Keeping predicate vocabulary separate from SET/table vocabulary prevents
    one UPDATE of a shared column from falsely covering another UPDATE whose
    WHERE condition was never cited.
    """
    text = _strip_comments_and_strings_for_scan(source)
    result: Dict[int, Set[str]] = {}
    statement_start = 0
    for match in re.finditer(r";|$", text):
        statement_end = match.start()
        statement = text[statement_start:statement_end]
        dml_match = re.search(r"\b(?:UPDATE|INSERT|DELETE|MERGE)\b", statement, re.IGNORECASE)
        if dml_match:
            where_match = re.search(r"\bWHERE\b", statement[dml_match.start():], re.IGNORECASE)
            if where_match:
                predicate_start = dml_match.start() + where_match.end()
                predicate_tokens = _tokens(statement[predicate_start:])
                if predicate_tokens:
                    line_start = text.count("\n", 0, statement_start) + 1
                    line_end = text.count("\n", 0, statement_end) + 1
                    for line_number in range(line_start, line_end + 1):
                        result[line_number] = predicate_tokens
        statement_start = match.end()
        if match.start() == len(text):
            break
    return result


def _compact_text(text: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(text or "").lower())


def _rule_evidence_text(rule: Any) -> str:
    if not isinstance(rule, dict):
        return ""
    parts: List[str] = []
    for key in (
        "source_evidence", "condition", "action", "business_meaning",
        "rule_name", "eligibility", "decision_logic_rows",
    ):
        value = rule.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            parts.append(" ".join(str(item) for item in value))
        else:
            parts.append(str(value))
    return " ".join(parts)


def _rule_evidence_fragments(rule: Any) -> List[str]:
    """Return model-supplied evidence fragments for line-local checks."""
    if not isinstance(rule, dict):
        return []
    evidence = rule.get("source_evidence")
    if isinstance(evidence, str):
        return [evidence]
    if isinstance(evidence, (list, tuple)):
        return [str(item) for item in evidence if str(item).strip()]
    return []


def find_coverage_gaps(
    source: str,
    rules: Sequence[Any],
) -> List[CoverageGap]:
    """Return source-anchor blocks that no rule appears to reference.

    This never inspects *what* a rule says beyond simple token overlap -
    it cannot tell whether a rule correctly describes a branch, only
    whether the model's output shows any sign of having looked at that
    part of the source at all. That is a deliberately weak, cheap,
    dialect-agnostic pre-filter: it exists to bound how often the (more
    expensive, more trustworthy) LLM revision pass in
    `RuleSynthesizerAgent.revise` needs to run, not to replace it.
    """
    anchors_by_line = _find_coverage_anchors(source)
    if not anchors_by_line:
        return []
    lines = str(source or "").splitlines()
    rule_tokens: Set[str] = set()
    evidence_fragments: List[str] = []
    for rule in rules or []:
        rule_tokens |= _tokens(_rule_evidence_text(rule))
        evidence_fragments.extend(_rule_evidence_fragments(rule))

    groups = _group_lines(list(anchors_by_line))
    predicate_tokens_by_line = _dml_predicate_tokens_by_line(source)

    gaps: List[CoverageGap] = []
    for group in groups:
        uncovered_lines: List[int] = []
        for line_number in group:
            line_tokens = _tokens(lines[line_number - 1] if line_number <= len(lines) else "")
            if not line_tokens:
                continue
            overlap = line_tokens & rule_tokens
            predicate_tokens = predicate_tokens_by_line.get(line_number, set())
            predicate_overlap = rule_tokens & predicate_tokens
            coverage_ratio = len(overlap) / len(line_tokens)
            fragment_match = any(
                (
                    _compact_text(fragment) in _compact_text(lines[line_number - 1])
                    or (
                        len(line_tokens & _tokens(fragment)) >= 2
                        and len(line_tokens & _tokens(fragment)) >= len(_tokens(fragment))
                    )
                )
                for fragment in evidence_fragments
                if _tokens(fragment)
            )
            # A single shared field name is not enough to prove that a
            # branch line was reviewed. Requiring two meaningful tokens on
            # multi-token lines catches a rule that cites only one branch of
            # an otherwise similar ladder, while retaining lenient matching
            # for paraphrased single-anchor lines.
            if predicate_tokens:
                # For DML, shared SET/table vocabulary is not evidence that
                # this statement's own business predicate was reviewed.
                predicate_covered = bool(predicate_overlap) and (
                    len(predicate_tokens) < 2 or len(predicate_overlap) >= 2
                )
                if not fragment_match and not predicate_covered:
                    uncovered_lines.append(line_number)
            elif not fragment_match and (coverage_ratio < _COVERAGE_TOKEN_THRESHOLD or (
                len(line_tokens) >= 2 and len(overlap) < 2
            )):
                uncovered_lines.append(line_number)
        if not uncovered_lines:
            continue
        start, end = uncovered_lines[0], uncovered_lines[-1]
        # When a DML assignment anchor is uncovered, report the complete
        # statement span so the revision prompt contains the predicate that
        # distinguishes this statement from other writes to the same field.
        predicate_lines = [
            line_number
            for line_number in predicate_tokens_by_line
            if any(
                predicate_tokens_by_line.get(line_number) == predicate_tokens_by_line.get(uncovered)
                for uncovered in uncovered_lines
            )
        ]
        if predicate_lines:
            start = min(start, min(predicate_lines))
            end = max(end, max(predicate_lines))
        block_lines = lines[max(0, start - 1) : end]
        snippet = "\n".join(block_lines).strip()
        keywords = sorted({kw for line in uncovered_lines for kw in anchors_by_line.get(line, [])})
        gaps.append(
            CoverageGap(
                line_start=start,
                line_end=end,
                snippet=snippet[:400],
                keywords=keywords,
            )
        )
    return gaps


def format_gap_for_ambiguity(gap: CoverageGap) -> str:
    """Render one unresolved gap as a report-facing ambiguity string,
    matching the pipeline's existing 'never silently guess' convention
    (see DESIGN_NOTES.md) for anything that can't be confidently
    resolved after the bounded revision loop.
    """
    snippet = gap.snippet.strip().replace("\n", " ")
    if len(snippet) > 160:
        snippet = snippet[:160].rstrip() + "..."
    return (
        f"Possible unreviewed decision logic near source line "
        f"{gap.line_start}-{gap.line_end} ({'/'.join(gap.keywords) or 'decision keyword'}): "
        f"no synthesized rule's evidence appears to reference \"{snippet}\". "
        "Needs human review to confirm whether this is business-relevant."
    )
