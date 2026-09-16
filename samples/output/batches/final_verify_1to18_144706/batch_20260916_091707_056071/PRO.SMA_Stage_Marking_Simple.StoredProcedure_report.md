# SMA Stage Marking Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_Stage_Marking_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 2 needs review |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 2 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure SMA_Stage_Marking_Simple is designed to perform marking operations on data within the DEMO_MISDB database, likely related to financial or business metrics tracking.

## Process Flow

1. Read the current date from the SysDayMatrix table based on the provided TimeKey.
2. Update the SmaStageDate for accounts that are currently overdue and have a flag indicating SMA status.
3. Update the SmaStageDate for accounts that are no longer overdue and have a flag indicating SMA status.
4. Update the SmaStage, FlagSma, and SmaReason for accounts based on their overdue days and facility type.
5. Update the RunStatus table to mark the process as completed and increment the run count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Update SMA stage date | `SmaStageDate` | Calculate and update the SMA stage date for accounts that are currently overdue. |
| ⚠️ Update process completion status | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Update the process completion status in the RunStatus table to indicate successful completion and increment the run count. |

## Business Rules

### R1 — Update SMA stage date

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `SmaStageDate`

**Applies to:**

- SMA flag is set to 'Y'

**Summary:**

- Calculate and update the SMA stage date for accounts that are currently overdue.


### R2 — Update process completion status

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- Process name is SMA_Stage_Marking_Simple

**Summary:**

- Update the process completion status in the RunStatus table to indicate successful completion and increment the run count.

## Calculations

### Calculation — SmaStageDate

**Expression:**

```sql
DATEADD(DAY, -OverdueDays + 1, @ProcessDate)
```

**Output:**
`PRO.AccountCal.SmaStageDate`

**Used By:**
UPDATE PRO.AccountCal; READ PRO.AccountCal

### Calculation — RunCount

**Expression:**

```sql
COALESCE(RunCount, 0) + 1
```

**Output:**
`RunCount`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AccountCal` | Read + Write | Updates: SmaStage, FlagSma, SmaReason, SmaStageDate |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |
| `SysDayMatrix` | Read | Provides: [Date] |

## Exception Handling

No explicit exception handling is defined in the provided SQL. If an exception occurs during the execution of the 'SMA_Stage_Marking_Simple' process, the procedure updates the run status in the PRO.RunStatus table to reflect the error.

## Findings / Needs Review

- Lines 25-35 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 68-73 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The extraction does not provide specific details on the operations performed by the procedure, such as table operations, calculations, or decision chains. The source SQL indicates the procedure is set up within the DEMO_MISDB database and configures ANSI_NULLS and QUOTED_IDENTIFIER options, but the actual business logic or operations it performs are not detailed in the extraction.
- 8 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
