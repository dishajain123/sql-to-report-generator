"""
sql_statement_boundaries.py
----------------------------
Shared, dependency-free statement-boundary detector.

Both `agents/ingestion.py` (chunking oversized sections down to
`max_chunk_chars` for the LLM) and `technical_sql_ops.py` (splitting a
chunk's raw/embedded SQL into individual statements for structural
parsing) need to answer the same question: "where does one top-level SQL
statement end and the next begin?" - without ever cutting through the
middle of a multi-line CASE expression or subquery, and without ever
silently dropping any part of the original text.

This lives in its own module (importing from neither of the two callers)
specifically to avoid a circular import: `technical_sql_ops.py` already
imports `CodeChunk`/`CodeIngestionAgent` from `agents/ingestion.py`, so
`agents/ingestion.py` cannot import back from `technical_sql_ops.py`.

Why this needs to exist at all: a purely per-line check ("does this line
start with a keyword, and does *this line alone* look balanced?") is not
enough. A statement like

    UPDATE A SET A.DPD_Max = (CASE WHEN ... THEN ...
                               WHEN ... THEN ...
                               ELSE ... END)
    FROM #DPD A WHERE ...

opens a paren on the first line and only closes it several lines later.
A per-line-only check has no memory of that open paren, so it can
misread the CASE's own `ELSE`/`END` line as a top-level statement
boundary - silently truncating the statement before its FROM/WHERE
clause is ever reached. This module tracks parenthesis depth as a
running count *carried across lines* to avoid exactly that.

It also has to work on legacy T-SQL that uses few or no semicolon
terminators at all (extremely common in older stored procedures), so
statement boundaries here are keyword-based (a line starting with
WITH/SELECT/INSERT/UPDATE/DELETE/MERGE/DECLARE/TRUNCATE at paren-depth 0
starts a new statement) rather than relying on ';' at all.

Design note - "boundary list", not independent spans: the splitter
records only the *start* positions of new statements ("cut points") and
then partitions the full text between consecutive cut points. This is
deliberate: an earlier version of this logic tried to track an
open/close span per statement directly, which meant a terminator line
(END/ELSE/...) was consumed as a boundary but never actually included in
any span's output - silently dropping that line, and any trailing
comment-only content after the last statement, from the result. The
boundary-list approach makes that class of bug structurally impossible:
consecutive cut points always partition `text` from position 0 to
`len(text)` with no gaps, so every character ends up in exactly one
returned piece.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

_KEYWORD_RE = re.compile(r"(?i)^(WITH|SELECT|INSERT|UPDATE|DELETE|MERGE|DECLARE|TRUNCATE)\b")
_SET_RE = re.compile(r"(?i)^SET\b")
_TERMINATOR_RE = re.compile(
    r"(?i)^(END(?:\s+(?:CATCH|TRY|IF|LOOP|WHILE|CASE))?|ELSE|EXCEPTION|GO)\b"
)
_CONTINUATION_KINDS = {"UPDATE", "INSERT", "DELETE", "MERGE"}

# A `CASE ... END` expression is legal (and common) with no wrapping
# parentheses at all, e.g. `SET RiskBand = CASE WHEN ... END`. Such a
# construct never touches `paren_depth`, so without separately tracking
# how many CASE expressions are currently open, a bare `END` line that is
# only closing the CASE (not the enclosing statement) is indistinguishable
# from a genuine block terminator - and gets misread as one, truncating
# the statement before any trailing clause (WHERE/FROM/...) is reached.
# `_CASE_TOKEN_RE` finds every CASE/END keyword occurrence, in order,
# anywhere in a line (not just at the start, since `SET x = CASE ...`
# opens a CASE mid-line); `_BARE_END_RE` is used to recognize an END that
# is *not* part of one of the two-word terminators above (those close an
# IF/LOOP/WHILE/TRY/CATCH block or a CASE *statement*, not a CASE
# *expression*, and are left to the existing terminator handling).
_CASE_TOKEN_RE = re.compile(r"(?i)\b(CASE|END)\b")
_BLOCK_END_SUFFIX_RE = re.compile(r"(?i)^END\s*(CATCH|TRY|IF|LOOP|WHILE|CASE)\b")


def split_top_level_statement_spans(text: str, masked_text: str) -> List[Tuple[int, int]]:
    """Return (start, end) character spans that partition `text` into
    top-level statements, with zero gaps: every character of `text` from
    index 0 to len(text) is covered by exactly one returned span (or the
    function returns an empty list if `text` is empty/whitespace-only).

    `masked_text` must be the same text with string literals and comments
    blanked out to the same length (so offsets stay aligned) - callers
    pass their own `_mask_strings_and_comments(...)` output for this, so
    keyword/paren-depth detection is never fooled by SQL-looking text
    that only appears inside a string literal or a comment.
    """
    if not text:
        return []
    if len(masked_text) != len(text):
        # Defensive: mismatched masked text means offsets can't be
        # trusted - treat the whole input as a single span rather than
        # risk slicing at the wrong character.
        return [(0, len(text))]

    lines = text.splitlines(keepends=True)
    boundaries: List[int] = []
    have_open_statement = False
    current_is_cte = False
    cte_main_consumed = False
    current_statement_kind: Optional[str] = None
    paren_depth = 0
    case_depth = 0
    offset = 0

    for line in lines:
        line_masked = masked_text[offset : offset + len(line)]
        stripped = line_masked.lstrip()
        indent = len(line_masked) - len(stripped)
        line_start = offset + indent
        is_top_level = paren_depth <= 0

        keyword_match = _KEYWORD_RE.match(stripped) if is_top_level else None
        set_match = _SET_RE.match(stripped) if is_top_level else None
        terminator_match = _TERMINATOR_RE.match(stripped) if is_top_level else None
        # A bare "END" or "ELSE" line only closes the currently open
        # statement when it isn't actually part of an unparenthesized
        # CASE expression that's still open within that statement - CASE
        # uses both keywords internally (`CASE WHEN ... ELSE ... END`) and
        # is otherwise indistinguishable, line-by-line, from an IF block's
        # own ELSE/END. When a CASE is open, such a line stays attached to
        # the open span instead, and the CASE's own depth is decremented
        # below once the line is scanned.
        if (
            terminator_match
            and case_depth > 0
            and not _BLOCK_END_SUFFIX_RE.match(stripped)
            and terminator_match.group(1).upper() in {"END", "ELSE"}
        ):
            terminator_match = None

        if terminator_match and have_open_statement:
            # The terminator line (END/ELSE/EXCEPTION/GO) closes the
            # currently open statement. It is NOT recorded as a new
            # boundary - it stays attached to (is the tail end of) the
            # span that's already open, which is exactly where it
            # belongs. The next statement, if any, gets its own boundary
            # when a new keyword/content line is seen.
            have_open_statement = False
            current_is_cte = False
            cte_main_consumed = False
            current_statement_kind = None
            case_depth = 0
        elif keyword_match:
            keyword = keyword_match.group(1).upper()
            if not have_open_statement:
                boundaries.append(line_start)
                have_open_statement = True
                current_is_cte = keyword == "WITH"
                cte_main_consumed = False
                current_statement_kind = keyword
                case_depth = 0
            elif current_statement_kind == "MERGE" and keyword in {"UPDATE", "INSERT", "DELETE"}:
                # A MERGE statement commonly contains WHEN MATCHED/WHEN
                # NOT MATCHED branches whose body lines start with UPDATE
                # or INSERT. Those are continuations of the same MERGE
                # statement, not new top-level statements.
                pass
            elif current_statement_kind == "INSERT" and keyword == "SELECT":
                # INSERT ... SELECT is one logical statement, not two.
                pass
            elif current_is_cte and not cte_main_consumed and keyword in {
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "MERGE",
            }:
                # The main body of a WITH ... <verb> CTE - still the same
                # logical statement, not a new boundary.
                cte_main_consumed = True
                current_statement_kind = keyword
            else:
                boundaries.append(line_start)
                current_is_cte = keyword == "WITH"
                cte_main_consumed = False
                current_statement_kind = keyword
                case_depth = 0
        elif set_match and have_open_statement and current_statement_kind in _CONTINUATION_KINDS:
            # `SET` here is the enclosing UPDATE's own SET clause (or a
            # continuation of it across lines), not a new statement.
            pass
        elif set_match and not have_open_statement:
            boundaries.append(line_start)
            have_open_statement = True
            current_statement_kind = "SET"
            case_depth = 0
        elif not have_open_statement and stripped:
            # Real content with no recognized DML/SET keyword (BEGIN, IF,
            # WHILE, EXEC, PRINT, ...). Start a boundary anyway so no
            # non-blank content is ever left uncovered.
            boundaries.append(line_start)
            have_open_statement = True
            current_statement_kind = None
            case_depth = 0

        # Carry the running paren depth forward to the next line so a
        # multi-line CASE/subquery is never mistaken for "top level"
        # partway through. A top-level ';' (depth 0) closes whatever
        # statement is currently open, exactly like an explicit terminator
        # line would: without this, a DML statement that ends mid-line
        # (the overwhelmingly common case) has nothing to stop trailing,
        # unrelated procedural content - a following bare `IF ...`/`ELSIF
        # ...`/assignment line with no recognized keyword of its own -
        # from silently being swallowed into the same span. That glued-on
        # tail is exactly what previously reached sqlglot bolted onto the
        # end of a real SQL statement, corrupting the parse.
        statement_closed_by_semicolon = False
        for ch in line_masked:
            if ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth = max(paren_depth - 1, 0)
            elif ch == ";" and paren_depth == 0:
                statement_closed_by_semicolon = True

        # Carry the running CASE-expression depth forward too, in keyword
        # order of appearance, so a same-line `CASE ... END` nets to zero
        # and a still-open multi-line CASE correctly suppresses the next
        # bare END from being read as a statement terminator.
        for token in _CASE_TOKEN_RE.finditer(line_masked):
            if token.group(1).upper() == "CASE":
                case_depth += 1
            elif case_depth > 0:
                case_depth -= 1

        if statement_closed_by_semicolon and have_open_statement:
            have_open_statement = False
            current_is_cte = False
            cte_main_consumed = False
            current_statement_kind = None
            case_depth = 0

        offset += len(line)

    if not boundaries:
        # No recognizable statement start anywhere (e.g. the text is one
        # long comment block) - the whole thing is one piece.
        return [(0, len(text))]

    # Always cover from character 0, even if some leading content (e.g.
    # a leading comment block) preceded the first detected boundary -
    # every character of `text` must end up in some span.
    boundaries[0] = 0

    spans: List[Tuple[int, int]] = []
    for index, start in enumerate(boundaries):
        end = boundaries[index + 1] if index + 1 < len(boundaries) else len(text)
        spans.append((start, end))
    return spans


def split_top_level_statements(text: str, masked_text: str) -> List[str]:
    """Convenience wrapper: same as `split_top_level_statement_spans` but
    returns the statement substrings directly, stripped of surrounding
    whitespace. Never returns an empty list for non-empty input.
    """
    spans = split_top_level_statement_spans(text, masked_text)
    statements = [text[start:end].strip() for start, end in spans if text[start:end].strip()]
    if statements:
        return statements
    return [text.strip()] if text.strip() else []