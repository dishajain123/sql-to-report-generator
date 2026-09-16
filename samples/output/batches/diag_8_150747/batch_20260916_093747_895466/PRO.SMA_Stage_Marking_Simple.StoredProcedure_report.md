# SMA Stage Marking Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_Stage_Marking_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 3 needs review |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 3 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure SMA_Stage_Marking_Simple updates the SMA stage, SMA flag, SMA reason, and SMA stage date for accounts with overdue days greater than zero, and increments the run count for the process.

## Process Flow

1. Read the current date from the SysDayMatrix table based on the provided TimeKey.
2. Update the SmaStage, FlagSma, SmaReason, and SmaStageDate fields in the PRO.AccountCal table for accounts with overdue days greater than zero and a SMA flag set to 'Y'.
3. Update the SmaStageDate field in the PRO.AccountCal table for accounts with overdue days equal to zero and a SMA flag set to 'Y'.
4. Update the COMPLETED, ErrorDate, ErrorDescription, and RunCount fields in the PRO.RunStatus table for the SMA_Stage_Marking_Simple process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Calculate SMA stage date | `SmaStageDate` | Calculate the SMA stage date for accounts that are overdue and flagged for SMA. |
| ⚠️ Mark process as completed | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Mark the SMA stage marking process as completed and increment the run count. |
| ⚠️ Update run status on error | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an exception occurs during the SMA_Stage_Marking_Simple process, the run status is updated to indicate the process is not completed, and… |

## Business Rules

### R1 — Calculate SMA stage date

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `SmaStageDate`

**Applies to:**

- Account is flagged for SMA

**Summary:**

- Calculate the SMA stage date for accounts that are overdue and flagged for SMA.

### Decision Logic

| Condition | Result |
|---|---|
| FlagSma = 'Y' | DATEADD(DAY, -OverdueDays + 1, @ProcessDate) |


### R2 — Mark process as completed

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- Process name matches 'SMA_Stage_Marking_Simple'

**Summary:**

- Mark the SMA stage marking process as completed and increment the run count.

### Decision Logic

| Condition | Result |
|---|---|
| ProcessName = 'SMA_Stage_Marking_Simple' | ISNULL(RunCount, 0) + 1 |


### R3 — Update run status on error

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `COMPLETED, ErrorDate, ErrorDescription, RunCount`

**Applies to:**

- ProcessName is 'SMA_Stage_Marking_Simple'

**Summary:**

- If an exception occurs during the SMA_Stage_Marking_Simple process, the run status is updated to indicate the process is not completed, and error details are recorded.

### Decision Logic

| Condition | Result |
|---|---|
| Exception occurs | COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 |

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

No explicit exception handling is defined in the provided SQL. If an exception occurs during the execution of the SMA_Stage_Marking_Simple process, the run status is updated to indicate the process is not completed, and error details are recorded.

## Findings / Needs Review

- Lines 25-35 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 68-73 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The extraction does not provide specific details on the marking operations performed by the procedure, such as the tables involved or the specific fields updated.
- 6 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
