# SMA Stage Marking Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_Stage_Marking_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 7 needs review |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 7 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure SMA_Stage_Marking_Simple is designed to perform marking operations on financial data for a specific time period, likely for regulatory or internal reporting purposes.

## Process Flow

1. Read the process date from the SysDayMatrix table.
2. Update the SmaStage for accounts with overdue days between 1 and 90.
3. Update the FlagSma for accounts with a non-null SmaStage.
4. Update the SmaReason for accounts with a FlagSma of 'Y'.
5. Update the SmaStageDate for accounts with a FlagSma of 'Y'.
6. Reset the SmaStage, FlagSma, and SmaReason for accounts with no overdue days.
7. Update the process completion status in the RunStatus table.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Determine SMA stage (SmaStage) | `SmaStage` | Assign an SMA stage to accounts based on the number of overdue days. |
| ⚠️ Determine SMA stage (A.SmaStage) | `SmaStage` | Assign an SMA stage to accounts based on the number of overdue days. |
| ⚠️ Set SMA flag (FlagSma) | `FlagSma` | Set the SMA flag for accounts based on the presence of an SMA stage. |
| ⚠️ Set SMA flag (A.FlagSma) | `FlagSma` | Set the SMA flag for accounts based on the presence of an SMA stage. |
| ⚠️ Calculate SMA stage date | `SmaStageDate` | Calculate the SMA stage date for accounts based on the number of overdue days. |
| ⚠️ Update process completion status | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Update the process completion status in the RunStatus table. |
| ⚠️ Update run status on error | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an exception occurs, the run status is updated to indicate the process is not completed, the error date is set, the error description is… |

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

- Set the SMA flag for accounts based on the presence of an SMA stage.

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

- Set the SMA flag for accounts based on the presence of an SMA stage.

### Decision Logic

| Condition | Result |
|---|---|
| SmaStage IS NOT NULL | 'Y' |
| ELSE | 'N' |

### R5 — Calculate SMA stage date

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `SmaStageDate`

**Applies to:**

- Account has a FlagSma of 'Y'

**Summary:**

- Calculate the SMA stage date for accounts based on the number of overdue days.


### R6 — Update process completion status

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- ProcessName is 'SMA_Stage_Marking_Simple'

**Summary:**

- Update the process completion status in the RunStatus table.


### R7 — Update run status on error

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `COMPLETED, ErrorDate, ErrorDescription, RunCount`

**Applies to:**

- ProcessName = 'SMA_Stage_Marking_Simple'

**Summary:**

- If an exception occurs, the run status is updated to indicate the process is not completed, the error date is set, the error description is recorded, and the run count is incremented.

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

The procedure uses a TRY-CATCH block to handle exceptions, but no specific exception handling steps are defined in the provided extraction. If an exception occurs during the execution of the SMA_Stage_Marking_Simple process, the procedure updates the run status to indicate the process is not completed, sets the error date, captures the error message, and increments the run count.

## Findings / Needs Review

- Lines 25-35 (ASSIGNMENT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 68-73 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The extraction does not provide specific details on the marking operations performed by the procedure, such as the fields affected or the logic behind the marking process.
- 3 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
