# SMA Stage Marking Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_Stage_Marking_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 1 confident, 3 needs review |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ℹ️ **Additional rules added from a targeted review pass.** 3 rule(s) were added after a second, narrowly-scoped look at a source line no rule initially cited - the model's call succeeded normally, but a new rule for a previously-unreviewed line still warrants a quick human check against the source; affected rules are marked inline. |

## What This Does

The procedure SMA_Stage_Marking_Simple is designed to perform marking operations on data within the DEMO_MISDB database, likely related to financial or operational metrics.

## Process Flow

1. Read the current date from the SysDayMatrix table based on the provided TimeKey.
2. Update the SmaStageDate for accounts that are currently overdue.
3. Update the SmaStage, FlagSma, and SmaReason for accounts based on their overdue days and facility type.
4. Update the run status for the SMA_Stage_Marking_Simple process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine FlagSma | `FlagSma` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Update SmaStageDate for overdue accounts | `SmaStageDate` | Calculate and update the SMA stage date for accounts that are currently overdue. |
| ⚠️ Increment run count | `RunCount` | Increment the run count for the SMA_Stage_Marking_Simple process. |
| ⚠️ Update run status on error | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an exception occurs, the run status is updated to indicate the process is not completed, the error date is set, the error description is… |

## Business Rules

### R1 — Determine FlagSma

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

### R2 — Update SmaStageDate for overdue accounts

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `SmaStageDate`

**Applies to:**

- SMA flag is set to 'Y'

**Summary:**

- Calculate and update the SMA stage date for accounts that are currently overdue.


### R3 — Increment run count

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `RunCount`

**Applies to:**

- Process name is 'SMA_Stage_Marking_Simple'

**Summary:**

- Increment the run count for the SMA_Stage_Marking_Simple process.


### R4 — Update run status on error

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `COMPLETED, ErrorDate, ErrorDescription, RunCount`

**Applies to:**

- ProcessName is 'SMA_Stage_Marking_Simple'

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

If an exception occurs during the execution of the SMA_Stage_Marking_Simple process, the run status is updated to indicate the process is not completed, the error date is set, the error description is recorded, and the run count is incremented.

## Findings / Needs Review

- Lines 25-35 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 68-73 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The extraction does not provide specific details on the operations performed by the procedure SMA_Stage_Marking_Simple, leading to uncertainties about its exact business impact and the fields it affects.
- 6 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
