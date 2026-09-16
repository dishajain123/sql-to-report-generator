# SMA Stage Marking Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_Stage_Marking_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 6 needs review |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 6 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure SMA_Stage_Marking_Simple is designed to perform marking operations on data within the DEMO_MISDB database, likely related to financial or operational metrics.

## Process Flow

1. Read the current date from SysDayMatrix using the provided TimeKey.
2. Update the SMA stage for accounts with overdue days greater than zero based on the number of overdue days.
3. Update the SMA flag for accounts based on whether they have a non-null SMA stage.
4. Update the SMA reason for accounts with a 'Y' SMA flag based on the facility type.
5. Update the SMA stage date for accounts with a 'Y' SMA flag using the calculated date.
6. Reset the SMA stage, flag, and reason for accounts with zero overdue days.
7. Update the process status in PRO.RunStatus to mark the process as completed and increment the run count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Determine SMA stage (SmaStage) | `SmaStage` | Assign an SMA stage to accounts based on the number of overdue days. |
| ⚠️ Determine SMA stage (A.SmaStage) | `SmaStage` | Assign an SMA stage to accounts based on the number of overdue days. |
| ⚠️ Set SMA flag (FlagSma) | `FlagSma` | Set the SMA flag for accounts based on whether they have a non-null SMA stage. |
| ⚠️ Set SMA flag (A.FlagSma) | `FlagSma` | Set the SMA flag for accounts based on whether they have a non-null SMA stage. |
| ⚠️ Calculate SMA stage date | `SmaStageDate` | Calculate the SMA stage date for accounts with a 'Y' SMA flag. |
| ⚠️ Log process completion | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | Update the process status in PRO.RunStatus to mark the process as completed and increment the run count. |

## Business Rules

### R1 — Determine SMA stage (SmaStage)

**Affected Field:** `SmaStage`

**Summary:**

- Assign an SMA stage to accounts based on the number of overdue days.

**Applies to:**

- PRO.AccountCal.OverdueDays > 0

**Source context:**

- Target: PRO.AccountCal
- FROM PRO.AccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.AccountCal.OverdueDays BETWEEN 1 AND 30 | 'SMA_0' |
| PRO.AccountCal.OverdueDays BETWEEN 31 AND 60 | 'SMA_1' |
| PRO.AccountCal.OverdueDays BETWEEN 61 AND 90 | 'SMA_2' |
| ELSE | NULL |

### R2 — Determine SMA stage (A.SmaStage)

**Affected Field:** `SmaStage`

**Summary:**

- Assign an SMA stage to accounts based on the number of overdue days.

### Decision Logic

| Condition | Result |
|---|---|
| OverdueDays BETWEEN 1 AND 30 | 'SMA_0' |
| OverdueDays BETWEEN 31 AND 60 | 'SMA_1' |
| OverdueDays BETWEEN 61 AND 90 | 'SMA_2' |
| ELSE | NULL |

### R3 — Set SMA flag (FlagSma)

**Affected Field:** `FlagSma`

**Summary:**

- Set the SMA flag for accounts based on whether they have a non-null SMA stage.

**Source context:**

- Target: PRO.AccountCal
- FROM PRO.AccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.AccountCal.SmaStage IS NOT NULL | 'Y' |
| ELSE | 'N' |

### R4 — Set SMA flag (A.FlagSma)

**Affected Field:** `FlagSma`

**Summary:**

- Set the SMA flag for accounts based on whether they have a non-null SMA stage.

### Decision Logic

| Condition | Result |
|---|---|
| SmaStage IS NOT NULL | 'Y' |
| ELSE | 'N' |

### R5 — Calculate SMA stage date

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `SmaStageDate`

**Applies to:**

- Account has a 'Y' SMA flag

**Summary:**

- Calculate the SMA stage date for accounts with a 'Y' SMA flag.


### R6 — Log process completion

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `COMPLETED, ErrorDate, ErrorDescription, RunCount`

**Applies to:**

- Process name is 'SMA_Stage_Marking_Simple'

**Summary:**

- Update the process status in RunStatus to mark the process as completed and increment the run count.

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

No explicit exception handling is described in the provided extraction. The procedure uses a TRY-CATCH block to handle any exceptions that may occur during execution. If an exception occurs during the execution of the SMA_Stage_Marking_Simple process, the run status is updated to reflect the error and the process is marked as incomplete.

## Findings / Needs Review

- Lines 25-35 (ASSIGNMENT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 68-73 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The extraction does not provide specific details on the operations performed by the procedure SMA_Stage_Marking_Simple, leading to an inability to detail the business rules, calculations, and exception handling.
- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
