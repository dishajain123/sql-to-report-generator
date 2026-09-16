# Dishonoured Cheque Penalty Calc — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Dishonoured_Cheque_Penalty_Calc` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 7 needs review |
| Tables read | 5 |
| Tables written | 5 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 7 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

This procedure calculates penalties for dishonoured cheques, updates account balances, and manages account suspensions based on repeated dishonours.

## Process Flow

1. Calculate penalty amounts for dishonoured cheques based on repeat counts.
2. Mark cheques without a dishonour reason for review.
3. Update account balances with penalty amounts for dishonoured cheques.
4. Mark penalties as applied for dishonoured cheques.
5. Stage penalty data for processing.
6. Merge staged penalty data into the cheque penalty ledger.
7. Identify accounts with repeated dishonours for potential suspension.
8. Suspend cheque books for accounts with repeated dishonours.
9. Log account status changes due to repeated dishonours.
10. Update process status for the dishonoured cheque penalty calculation.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Update penalty amount (PenaltyAmount) | `PenaltyAmount` | Assign a penalty amount to dishonoured cheques based on specific conditions. |
| ⚠️ Update penalty amount (D.PenaltyAmount) | `PenaltyAmount` | Assign a penalty amount to dishonoured cheques based on specific conditions. |
| ⚠️ Mark cheque for review | `HoldForReview` | Flag a dishonoured cheque for review if no dishonour reason is provided. |
| ⚠️ Update account balance | `OutstandingBalance` | Adjust the account balance by adding the penalty amount for dishonoured cheques. |
| ⚠️ Mark penalty as applied | `PenaltyApplied` | Indicate that the penalty has been applied to a dishonoured cheque. |
| ⚠️ Merge penalty data | `PRO.ChequePenaltyLedger.AccountId, PRO.ChequePenaltyLedger.PenaltyAmount, PRO.ChequePenaltyLedger.DishonourCount, PRO.ChequePenaltyLedger.LastPenaltyDate` | Integrate staged penalty data into the cheque penalty ledger. |
| ⚠️ Log account status change | `PRO.AccountStatusAuditLog.AccountId, PRO.AccountStatusAuditLog.TransitionDate, PRO.AccountStatusAuditLog.NewStatus, PRO.AccountStatusAuditLog.Reason` | Record the status change of accounts due to repeated dishonours in the account status audit log. |

## Business Rules

### R1 — Update penalty amount (PenaltyAmount)

**Affected Field:** `PenaltyAmount`

**Summary:**

- Assign a penalty amount to dishonoured cheques based on specific conditions.

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

### R2 — Update penalty amount (D.PenaltyAmount)

**Affected Field:** `PenaltyAmount`

**Summary:**

- Assign a penalty amount to dishonoured cheques based on specific conditions.

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

- Dishonoured cheque date matches process date
- No dishonour reason provided

**Summary:**

- Flag a dishonoured cheque for review if no dishonour reason is provided.


### R4 — Update account balance

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Adjust the account balance by adding the penalty amount for dishonoured cheques.


### R5 — Mark penalty as applied

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `PenaltyApplied`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Indicate that the penalty has been applied to a dishonoured cheque.


### R6 — Merge penalty data

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `PRO.ChequePenaltyLedger.AccountId, PRO.ChequePenaltyLedger.PenaltyAmount, PRO.ChequePenaltyLedger.DishonourCount, PRO.ChequePenaltyLedger.LastPenaltyDate`

**Applies to:**

- Matching account IDs between target and source tables

**Summary:**

- Integrate staged penalty data into the cheque penalty ledger.


### R7 — Log account status change

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `PRO.AccountStatusAuditLog.AccountId, PRO.AccountStatusAuditLog.TransitionDate, PRO.AccountStatusAuditLog.NewStatus, PRO.AccountStatusAuditLog.Reason`

**Applies to:**

- Account is in the list of new suspensions

**Summary:**

- Record the status change of accounts due to repeated dishonours in the account status audit log.

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

The procedure includes steps to update the running process status to indicate completion and record any errors, ensuring that the process outcome is properly logged. The procedure uses a TRY-CATCH block to handle exceptions, but specific exception handling steps are not detailed in the extraction. The procedure uses a TRY-CATCH block to handle exceptions, updating the process status with the current date, error message, and incrementing the count if an exception occurs.

## Findings / Needs Review

- Lines 103-103 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 123-125 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 132-136 (ASSIGNMENT/IF/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 140-140 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 3 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
