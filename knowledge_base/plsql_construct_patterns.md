# Common PL/SQL Construct Patterns (Reference)

This document explains what common SQL/PL-SQL constructs typically
represent from a business-process standpoint, so the extraction pipeline
can correctly interpret code before a human-readable rule is written.

## Cursors and Cursor FOR Loops

A cursor declared over a query against an accounts/loans/transactions
table, iterated row-by-row, almost always represents **batch processing**:
the system is working through a set of accounts or records one at a time
to apply the same evaluation or update to each of them. For example, a
cursor over `LOAN_ACCOUNT WHERE status = 'ACTIVE'` iterated in a loop that
computes overdue days per row represents a batch run that re-evaluates
every active loan's classification, not a one-off lookup.

## MERGE Statements

A `MERGE` statement typically implements **upsert / synchronization**
logic: if a matching record already exists, it is updated in place;
otherwise a new record is inserted. In banking contexts this commonly
represents reconciling a target table (e.g. a provisioning summary table)
against the latest computed values without creating duplicate rows.

## IF / CASE / WHEN Branching

Conditional branches based on thresholds (day counts, amount thresholds,
status codes) represent **decision points that select between distinct
business outcomes**. The business-relevant fact is the condition and the
distinct outcome selected, not the branching mechanism itself.

## Exception Handling Sections

- A specific named exception handler (e.g. `NO_DATA_FOUND`,
  `TOO_MANY_ROWS`, a user-defined exception) represents a planned response
  to a specific, anticipated failure scenario relevant to the business
  process (e.g. "no matching account found").
- A generic `WHEN OTHERS` handler represents a catch-all safety net for
  unanticipated failures. If it logs the error and re-raises, this
  represents "the failure is recorded for investigation and the operation
  is stopped/rolled back rather than silently continuing." If it swallows
  the error silently, this represents an operational risk: a failure could
  occur without any visible trace, which is worth flagging for review.

## Dynamic SQL (EXECUTE IMMEDIATE)

Dynamic SQL built and executed as a runtime string cannot generally be
statically resolved to a fixed table/column/condition, since its exact
content may depend on runtime parameters. This should always be flagged
as an area needing human review rather than guessed.

## Bulk Operations (BULK COLLECT / FORALL)

These constructs represent the same row-by-row business logic as a
cursor loop, but implemented for performance at scale (processing a large
batch of accounts or transactions efficiently). The business meaning is
the same as a cursor-driven batch process: a bulk evaluation/update
applied across many records at once.

## Sequences / Audit Columns

Population of columns such as `created_by`, `updated_by`, `created_date`,
or use of a sequence to generate a surrogate key, typically represents
standard record-keeping/audit trail behavior rather than business logic in
itself, unless the value is used later to drive a business decision.

## Locking Hints (FOR UPDATE)

A `SELECT ... FOR UPDATE` typically represents a business need to prevent
two concurrent processes from acting on the same account/record at the
same time (e.g. to avoid double-processing the same loan in a batch
classification run).
