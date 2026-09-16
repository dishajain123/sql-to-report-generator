# Dishonoured Cheque Penalty Calc — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Dishonoured_Cheque_Penalty_Calc` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 6 needs review |
| Tables read | 5 |
| Tables written | 5 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 6 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure calculates penalties for dishonoured cheques, updates account balances, and manages account statuses based on the number of dishonoured cheques within a specified lookback window.

## Process Flow

1. Read the SysDayMatrix table to get the date for the given TimeKey.
2. Update the PRO.DishonouredCheque table to set penalty amounts, hold cheques for review, and mark penalties as applied.
3. Update the PRO.LoanAccountCal table to adjust outstanding balances and suspend cheque books.
4. Read the PRO.DishonouredCheque table to get penalty amounts and account IDs for dishonoured cheques.
5. Insert records into the #PenaltyStaging table to stage penalty amounts and dishonour counts.
6. Merge records in the PRO.ChequePenaltyLedger table to update penalty amounts and dishonour counts.
7. Read from the #PenaltyStaging table to get account IDs with sufficient dishonour counts for suspension.
8. Read from the PRO.LoanAccountCal table to get account IDs with sufficient dishonour counts for suspension.
9. Insert records into the #NewSuspensions table to log accounts with sufficient dishonour counts for suspension.
10. Read from the #NewSuspensions table to get account IDs for process logging.
11. Insert records into the PRO.AccountStatusAuditLog table to log account status transitions.
12. Update the PRO.ACLRUNNINGPROCESSSTATUS table to mark the process as completed and increment the count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Calculate penalty amount (PenaltyAmount) | `PenaltyAmount` | Determine the penalty amount for a dishonoured cheque based on the dishonour reason and repeat count. |
| ⚠️ Calculate penalty amount (D.PenaltyAmount) | `PenaltyAmount` | Determine the penalty amount for a dishonoured cheque based on the dishonour reason and repeat count. |
| ⚠️ Mark cheque for review | `HoldForReview` | Mark a cheque for review if certain conditions are met. |
| ⚠️ Update account balance | `OutstandingBalance` | Update the account balance with the calculated penalty amount. |
| ⚠️ Merge penalty data | `Not specified` | Merge penalty data into the cheque penalty ledger. |
| ⚠️ Log account status | `Not specified` | Log account status transitions. |

## Business Rules

### R1 — Calculate penalty amount (PenaltyAmount)

**Affected Field:** `PenaltyAmount`

**Summary:**

- Determine the penalty amount for a dishonoured cheque based on the dishonour reason and repeat count.

**Applies to:**

- PRO.DishonouredCheque.DishonourDate = @ProcessDate AND PRO.DishonouredCheque.PenaltyApplied = 'N'

**Source context:**

- Target: PRO.DishonouredCheque
- FROM PRO.DishonouredCheque AS D

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.DishonouredCheque.DishonourReason IS NULL | NULL |
| PRO.DishonouredCheque.RepeatCount IS NULL OR PRO.DishonouredCheque.RepeatCount = 0 | 350.00 |
| PRO.DishonouredCheque.RepeatCount = 1 | 750.00 |
| ELSE | 1500.00 |

### R2 — Calculate penalty amount (D.PenaltyAmount)

**Affected Field:** `PenaltyAmount`

**Summary:**

- Determine the penalty amount for a dishonoured cheque based on the dishonour reason and repeat count.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourReason IS NULL | NULL |
| RepeatCount IS NULL OR RepeatCount = 0 | 350.00 |
| RepeatCount = 1 | 750.00 |
| ELSE | 1500.00 |

### R3 — Mark cheque for review

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `HoldForReview`

**Applies to:**

- Dishonoured cheques with a specific date and no dishonour reason

**Summary:**

- Mark a cheque for review if certain conditions are met.


### R4 — Update account balance

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Accounts with dishonoured cheques and non-null penalty amounts

**Summary:**

- Update the account balance with the calculated penalty amount.


### R5 — Merge penalty data

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** Not specified

**Applies to:**

- Dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount

**Summary:**

- Merge penalty data into the cheque penalty ledger.


### R6 — Log account status

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** Not specified

**Applies to:**

- Accounts with a status transition to be logged

**Summary:**

- Log account status transitions.

## Calculations

### Calculation — OutstandingBalance

**Expression:**

```sql
COALESCE(OutstandingBalance, 0) + PenaltyAmount
```

**Output:**
`PRO.LoanAccountCal.OutstandingBalance`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — DishonourCount

**Expression:**

```sql
(SELECT COUNT(*) FROM DishonouredCheque AS D2 WHERE D2.AccountId = AccountId AND D2.DishonourDate >= @LookbackWindowStart)
```

**Output:**
`#PenaltyStaging.DishonourCount`

**Used By:**
INSERT INTO #PenaltyStaging

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.DishonouredCheque` | Read + Write | Updates: PenaltyAmount, HoldForReview, PenaltyApplied |
| `PRO.LoanAccountCal` | Read + Write | Updates: OutstandingBalance, ChequeBookSuspended |
| `PRO.ChequePenaltyLedger` | Read + Write | Provides: Target.AccountId, Target.PenaltyAmount, Target.DishonourCount, Target.LastPenaltyDate, FirstPenaltyDate |
| `PRO.AccountStatusAuditLog` | Write | Inserts data into: AccountId, TransitionDate, NewStatus, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Inserts data into: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT, RUNNINGPROCESSNAME |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#PenaltyStaging` | Read + Write | Inserts data into: AccountId, PenaltyAmount, DishonourCount |
| `#NewSuspensions` | Read + Write | Inserts data into: AccountId |

## Exception Handling

The procedure does not explicitly handle exceptions; any failures would be managed by the calling system or higher-level error handling mechanisms. The procedure handles exceptions by updating the process status with the current date, error message, and incrementing the count if the process is running. If the process is not running, it inserts a new process status record.

## Findings / Needs Review

- Lines 65-65 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 103-103 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 140-140 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The calculation method for penalty amount is not specified.
- The criteria for setting a cheque on hold for review are not detailed.
- The specific conditions under which the penalty is applied are not provided.
- 2 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
