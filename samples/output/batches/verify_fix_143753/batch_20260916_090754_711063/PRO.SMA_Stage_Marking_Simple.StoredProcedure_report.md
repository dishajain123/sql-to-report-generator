# SMA Stage Marking Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_Stage_Marking_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 3 confident, 5 needs review |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 5 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure updates the SMA stage and related fields for accounts based on their overdue days and facility type, ensuring accurate stage marking and reason assignment.

## Process Flow

1. If an exception occurs during the execution of the 'SMA_Stage_Marking_Simple' process, the procedure updates the run status in the PRO.RunStatus table.
2. The COMPLETED status is set to 'N', indicating the process is not completed.
3. The ErrorDate is set to the current date and time.
4. The ErrorDescription is set to the error message encountered.
5. The RunCount is incremented by 1, or set to 1 if it is NULL.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine SmaStage | `SmaStage` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine FlagSma | `FlagSma` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine SmaReason | `SmaReason` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Determine SMA stage | `SmaStage` | Assign an SMA stage to accounts based on their overdue days. |
| ⚠️ Set SMA flag | `FlagSma` | Set the SMA flag based on the SMA stage. |
| ⚠️ Update SMA stage date | `SmaStageDate` | Calculate and update the SMA stage date for accounts flagged for SMA. |
| ⚠️ Increment run count | `RunCount` | Increment the run count for the SMA_Stage_Marking_Simple process. |
| ⚠️ Update run status on error | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an exception occurs during the 'SMA_Stage_Marking_Simple' process, update the run status to indicate the process is not completed, recor… |

## Business Rules

### R1 — Determine SmaStage

**Affected Field:** `SmaStage`


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

### R2 — Determine FlagSma

**Affected Field:** `FlagSma`


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

### R3 — Determine SmaReason

**Affected Field:** `SmaReason`


**Applies to:**

- PRO.AccountCal.FlagSma = 'Y'

**Source context:**

- Target: PRO.AccountCal
- FROM PRO.AccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.AccountCal.FacilityType IN ('CC', 'OD') | 'CASH CREDIT / OVERDRAFT OVERDUE' |
| PRO.AccountCal.FacilityType IN ('TL', 'DL') | 'TERM LOAN OVERDUE' |
| ELSE | 'OTHER FACILITY OVERDUE' |

### R4 — Determine SMA stage

**Affected Field:** `SmaStage`

**Summary:**

- Assign an SMA stage to accounts based on their overdue days.

### Decision Logic

| Condition | Result |
|---|---|
| OverdueDays BETWEEN 1 AND 30 | 'SMA_0' |
| OverdueDays BETWEEN 31 AND 60 | 'SMA_1' |
| OverdueDays BETWEEN 61 AND 90 | 'SMA_2' |
| ELSE |  |

### R5 — Set SMA flag

**Affected Field:** `FlagSma`

**Summary:**

- Set the SMA flag based on the SMA stage.

### Decision Logic

| Condition | Result |
|---|---|
| SmaStage IS NOT NULL | 'Y' |
| ELSE |  |

### R6 — Update SMA stage date

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `SmaStageDate`

**Applies to:**

- Account's SMA flag is set to 'Y'

**Summary:**

- Calculate and update the SMA stage date for accounts flagged for SMA.


### R7 — Increment run count

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RunCount`

**Applies to:**

- Process name is 'SMA_Stage_Marking_Simple'

**Summary:**

- Increment the run count for the SMA_Stage_Marking_Simple process.


### R8 — Update run status on error

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `COMPLETED, ErrorDate, ErrorDescription, RunCount`

**Applies to:**

- ProcessName = 'SMA_Stage_Marking_Simple'

**Summary:**

- If an exception occurs during the 'SMA_Stage_Marking_Simple' process, update the run status to indicate the process is not completed, record the error date, error description, and increment the run count.

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

If an exception occurs during the execution of the 'SMA_Stage_Marking_Simple' process, the procedure updates the run status to indicate the process is not completed, records the error date, error description, and increments the run count.

## Findings / Needs Review

- Lines 25-35 (ASSIGNMENT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 68-73 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The extraction does not provide any executable logic or decision chains, leading to an absence of business rules and calculations.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
