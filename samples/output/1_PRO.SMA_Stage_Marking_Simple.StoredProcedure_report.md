# SMA Stage Marking Simple — Business Logic Report

**Procedure:** `PRO.SMA_Stage_Marking_Simple`  ·  **Dialect:** T-SQL  ·  **Input:** `@TimeKey` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_Stage_Marking_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 5 |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | No |

## What This Does

This procedure marks each account's SMA (Special Mention Account) stage, flags SMA status, attributes a reason by facility type, calculates the date the current stage began, and clears SMA status for accounts no longer overdue.

## Process Flow

1. Classify the SMA stage by overdue days.
2. Flag the account as currently in SMA status.
3. Attribute the overdue reason by facility type for SMA accounts.
4. Calculate the date the current SMA stage began.
5. Clear SMA status for accounts that are no longer overdue.
6. Update the run status to indicate successful completion or failure.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Classify SMA stage by overdue days | `SmaStage` | Assigns the SMA stage classification based on the number of days an account is overdue. |
| Flag SMA status | `FlagSma` | Flags the account as currently in SMA status if the SMA stage is not null. |
| Attribute overdue reason by facility type | `SmaReason` | Attributes the overdue reason by facility type for SMA accounts. |
| Calculate SMA stage start date | `SmaStageDate` | Calculates the date the current SMA stage began by subtracting the overdue days from the process date. |
| Clear SMA status for non-overdue accounts | `SmaStage, FlagSma, SmaReason` | Clears the SMA stage, SMA status flag, and SMA reason for accounts that are no longer overdue. |

## Business Rules

### R1 — Classify SMA stage by overdue days

**Affected Field:** `SmaStage`

**Summary:**

- Assigns the SMA stage classification based on the number of days an account is overdue.

### Decision Logic

| Condition | Result |
|---|---|
| OverdueDays BETWEEN 1 AND 30 | 'SMA_0' |
| OverdueDays BETWEEN 31 AND 60 | 'SMA_1' |
| OverdueDays BETWEEN 61 AND 90 | 'SMA_2' |
| ELSE | NULL |


### R2 — Flag SMA status

**Affected Field:** `FlagSma`

**Summary:**

- Flags the account as currently in SMA status if the SMA stage is not null.

### Decision Logic

| Condition | Result |
|---|---|
| SmaStage IS NOT NULL | 'Y' |
| ELSE | 'N' |


### R3 — Attribute overdue reason by facility type

**Affected Field:** `SmaReason`

**Summary:**

- Attributes the overdue reason by facility type for SMA accounts.

### Decision Logic

| Condition | Result |
|---|---|
| FacilityType IN ('CC', 'OD') | 'CASH CREDIT / OVERDRAFT OVERDUE' |
| FacilityType IN ('TL', 'DL') | 'TERM LOAN OVERDUE' |
| ELSE | 'OTHER FACILITY OVERDUE' |


### R4 — Calculate SMA stage start date

**Affected Field:** `SmaStageDate`

**Summary:**

- Calculates the date the current SMA stage began by subtracting the overdue days from the process date.


### R5 — Clear SMA status for non-overdue accounts

**Affected Field:** `SmaStage, FlagSma, SmaReason`

**Summary:**

- Clears the SMA stage, SMA status flag, and SMA reason for accounts that are no longer overdue.

## Calculations

_None identified._

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AccountCal` | Read + Write | Updates: SmaStage, FlagSma, SmaReason, SmaStageDate |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |
| `SysDayMatrix` | Read | Provides: [Date] |

_1 working/temporary table(s) used only for intermediate calculation steps are omitted here - see the pipeline run log for the full technical lineage._

## Exception Handling

If an error occurs during the procedure execution, the run status is updated to indicate failure, and the error details are recorded.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
