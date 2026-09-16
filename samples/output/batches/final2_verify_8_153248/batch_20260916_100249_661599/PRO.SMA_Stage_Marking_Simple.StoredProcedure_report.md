# SMA Stage Marking Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_Stage_Marking_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 6 confident, 1 needs review |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ℹ️ **Additional rules added from a targeted review pass.** 1 rule(s) were added after a second, narrowly-scoped look at a source line no rule initially cited - the model's call succeeded normally, but a new rule for a previously-unreviewed line still warrants a quick human check against the source; affected rules are marked inline. |

## What This Does

The procedure SMA_Stage_Marking_Simple is designed to perform operations on a database using a specified time key, though the specific operations are not detailed in the provided extraction.

## Process Flow

1. Read the current date from the SysDayMatrix table using the provided TimeKey.
2. Update the SMA stage, flag, reason, and stage date for accounts that are currently overdue and flagged for SMA.
3. Update the SMA stage date for accounts that are no longer overdue.
4. Increment the run count and mark the process as completed in the RunStatus table.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine SmaStage | `SmaStage` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Update SMA stage date | `SmaStageDate` | Update the SMA stage date for accounts that are currently overdue. |
| Increment run count | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Increment the run count for the SMA_Stage_Marking_Simple process. |
| Determine FlagSma | `FlagSma` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine SmaReason | `SmaReason` | First matching row wins; ELSE includes false or NULL predicates. |
| Set FlagSma to Y | `FlagSma` | Flag accounts as SMA overdue if they have a non-null SmaStage. |
| Assign SmaReason based on FacilityType | `SmaReason` | Assign a reason for the SMA stage based on the account's facility type. |

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

### R2 — Update SMA stage date

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `SmaStageDate`

**Applies to:**

- Account is flagged for SMA

**Summary:**

- Update the SMA stage date for accounts that are currently overdue.

### Decision Logic

| Condition | Result |
|---|---|
| FlagSma = 'Y' | DATEADD(DAY, -OverdueDays + 1, @ProcessDate) |


### R3 — Increment run count

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- ProcessName is SMA_Stage_Marking_Simple

**Summary:**

- Increment the run count for the SMA_Stage_Marking_Simple process.


### R4 — Determine FlagSma

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

### R5 — Determine SmaReason

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

### R6 — Set FlagSma to Y

**Affected Field:** `FlagSma`

**Summary:**

- Flag accounts as SMA overdue if they have a non-null SmaStage.

### Decision Logic

| Condition | Result |
|---|---|
| SmaStage IS NOT NULL | 'Y' |
| ELSE |  |

### R7 — Assign SmaReason based on FacilityType

**Affected Field:** `SmaReason`

**Summary:**

- Assign a reason for the SMA stage based on the account's facility type.

### Decision Logic

| Condition | Result |
|---|---|
| FacilityType IN ('CC', 'OD') | 'CASH CREDIT / OVERDRAFT OVERDUE' |
| FacilityType IN ('TL', 'DL') | 'TERM LOAN OVERDUE' |
| ELSE |  |

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
`PRO.RunStatus.RunCount`

**Used By:**
UPDATE PRO.RunStatus; READ PRO.RunStatus


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AccountCal` | Read + Write | Updates: SmaStage, FlagSma, SmaReason, SmaStageDate |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |
| `SysDayMatrix` | Read | Provides: [Date] |

## Exception Handling

No explicit exception handling is defined in the provided extraction. If an exception occurs during the execution of the SMA_Stage_Marking_Simple process, the run status is updated to indicate the process is not completed, and error details are recorded.

## Findings / Needs Review

- Lines 25-35 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 68-73 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The source SQL indicates the use of the DEMO_MISDB database and the setting of ANSI_NULLS and QUOTED_IDENTIFIER options, but no further operations or business logic is described.
- 2 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
