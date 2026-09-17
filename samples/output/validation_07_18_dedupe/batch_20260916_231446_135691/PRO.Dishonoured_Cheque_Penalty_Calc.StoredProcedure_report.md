# Dishonoured Cheque Penalty Calc — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Dishonoured_Cheque_Penalty_Calc` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 7 |
| Tables read | 5 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

This procedure calculates and updates dishonoured cheque penalties for accounts that have crossed a specified threshold, ensuring that penalties are applied and accounts are flagged for suspension if necessary. This procedure also writes to: AccountStatusAuditLog, ChequePenaltyLedger, DishonouredCheque, LoanAccountCal, NewSuspensions, PenaltyStaging.

## Process Flow

1. Retrieve the processing date from the SysDayMatrix table based on the provided TimeKey.
2. Calculate the lookback window start date by subtracting 6 months from the processing date.
3. Update the penalty amount for dishonoured cheques on the processing date where the penalty has not been applied and the dishonour reason is not specified or is null.
4. Set the HoldForReview flag to 'Y' for dishonoured cheques on the processing date where the dishonour reason is null.
5. Update the outstanding balance of loan accounts by adding the penalty amount for dishonoured cheques on the processing date where the penalty amount is not null.
6. Create a temporary table to stage penalty information for dishonoured cheques on the processing date where the penalty amount is not null, including the account ID, penalty amount, and count of dishonoured cheques for the account within a lookback window.
7. Insert records into the temporary staging table with account ID, penalty amount, and dishonour count for dishonoured cheques on the processing date where the penalty amount is not null.
8. Merge the cheque penalty ledger with a staging table to update existing records or insert new records for accounts with dishonoured cheques.
9. Drop the temporary table #NewSuspensions if it already exists.
10. Insert account IDs into the temporary table #NewSuspensions for accounts with a dishonour count of 3 or more that are not already suspended.
11. Check if the process 'Dishonoured_Cheque_Penalty_Calc' is already running.
12. If the process is running, update its status to indicate an error, record the error message, and increment the count.
13. If the process is not running, insert a new record to start the process, setting its status to 'Not Completed', the error date to the current date, the error description to the error message, and the count to 1.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Calculate penalty amount | `PenaltyAmount` | Determine the penalty amount for dishonoured cheques based on the repeat count and dishonour reason. |
| Stage penalty information | `AccountId, PenaltyAmount, DishonourCount` | Insert records into a temporary staging table with account ID, penalty amount, and dishonour count for dishonoured cheques on the processin… |
| Insert into #NewSuspensions | `AccountId` | Not specified |
| Determine HoldForReview | `HoldForReview` | Not specified |
| Insert into #PenaltyStaging | `AccountId, PenaltyAmount, DishonourCount` | Not specified |
| Determine ChequeBookSuspended | `ChequeBookSuspended` | Not specified |
| Upsert chequepenaltyledger | `PRO.ChequePenaltyLedger.PenaltyAmount, PenaltyAmount, DishonourCount, LastPenaltyDate, AccountId, FirstPenaltyDate` | Increase the penalty amount for accounts with dishonoured cheques by the amount specified in the staging table. |

## Business Rules

### R1 — Calculate penalty amount

**Affected Field:** `PenaltyAmount`

**Summary:**

- Determine the penalty amount for dishonoured cheques based on the repeat count and dishonour reason.

**Applies to:**

- #NewSuspensions.DishonouredCheque.DishonouredCheque.DishonourDate = @ProcessDate AND #NewSuspensions.DishonouredCheque.DishonouredCheque.PenaltyApplied = 'N'

**Source context:**

- Target: #NewSuspensions.DishonouredCheque
- FROM #NewSuspensions.DishonouredCheque

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourReason IS NULL | NULL |
| RepeatCount IS NULL OR RepeatCount = 0 | 350.00 |
| RepeatCount = 1 | 750.00 |
| ELSE | 1500.00 |

### R2 — Stage penalty information

**Affected Field:** `AccountId, PenaltyAmount, DishonourCount`

**Applies to:**

- Dishonoured cheques on the processing date with a non-null penalty amount

**Summary:**

- Insert records into a temporary staging table with account ID, penalty amount, and dishonour count for dishonoured cheques on the processing date where the penalty amount is not null.

### Decision Logic

| Condition | Result |
|---|---|
| #NewSuspensions.DishonouredCheque.DishonourDate = @ProcessDate AND #NewSuspensions.DishonouredCheque.PenaltyAmount IS NOT NULL | INSERT INTO #PenaltyStaging (AccountId, PenaltyAmount, DishonourCount)<br>        SELECT #NewSuspensions.DishonouredCheque.AccountId, #NewSuspensions.DishonouredCheque.PenaltyAmount,<br>               (SELECT COUNT(*) FROM #NewSuspensions.DishonouredCheque D2<br>                WHERE #NewSuspensions.DishonouredCheque.AccountId = #NewSuspensions.DishonouredCheque.AccountId AND #NewSuspensions.DishonouredCheque.DishonourDate >= @LookbackWindowStart)<br>        FROM #NewSuspensions.DishonouredCheque D<br>        WHERE #NewSuspensions.DishonouredCheque.DishonourDate = @ProcessDate<br>          AND #NewSuspensions.DishonouredCheque.PenaltyAmount IS NOT NULL |


### R3 — Insert into #NewSuspensions

**Affected Field:** `AccountId`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| #PenaltyStaging.DishonourCount >= 3 AND (LoanAccountCal.ChequeBookSuspended <> 'Y' OR LoanAccountCal.ChequeBookSuspended IS NULL) | AccountId := #PenaltyStaging.AccountId |


### R4 — Determine HoldForReview

**Affected Field:** `HoldForReview`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND DishonourReason IS NULL | 'Y' |


### R5 — Insert into #PenaltyStaging

**Affected Field:** `AccountId, PenaltyAmount, DishonourCount`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| #NewSuspensions.DishonouredCheque.DishonourDate = @ProcessDate AND NOT #NewSuspensions.DishonouredCheque.PenaltyAmount IS NULL | AccountId := #NewSuspensions.DishonouredCheque.AccountId; PenaltyAmount := #NewSuspensions.DishonouredCheque.PenaltyAmount; DishonourCount := (SELECT COUNT(*) FROM #NewSuspensions.DishonouredCheque AS D2 WHERE #NewSuspensions.DishonouredCheque.AccountId = #NewSuspensions.DishonouredCheque.AccountId AND #NewSuspensions.DishonouredCheque.DishonourDate >= @LookbackWindowStart) |


### R6 — Determine ChequeBookSuspended

**Affected Field:** `ChequeBookSuspended`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| AccountId IN (SELECT AccountId FROM #NewSuspensions) | 'Y' |


### R7 — Upsert chequepenaltyledger

**Affected Field:** `PRO.ChequePenaltyLedger.PenaltyAmount, PenaltyAmount, DishonourCount, LastPenaltyDate, AccountId, FirstPenaltyDate`

**Applies to:**

- Account record exists in the cheque penalty ledger

**Summary:**

- Increase the penalty amount for accounts with dishonoured cheques by the amount specified in the staging table.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | #NewSuspensions.ChequePenaltyLedger.PenaltyAmount + #PenaltyStaging.PenaltyAmount; #NewSuspensions.ChequePenaltyLedger.PenaltyAmount + #PenaltyStaging.PenaltyAmount; #PenaltyStaging.DishonourCount; @ProcessDate |
| WHEN NOT MATCHED BY TARGET | #PenaltyStaging.AccountId; #PenaltyStaging.PenaltyAmount; #PenaltyStaging.DishonourCount; @ProcessDate |

## Calculations

### Calculation — OutstandingBalance

**Expression:**

```sql
ISNULL(PRO.LoanAccountCal.OutstandingBalance, 0) + PRO.DishonouredCheque.PenaltyAmount
```

**Output:**
`PRO.LoanAccountCal.OutstandingBalance`

**Used By:**
READ PRO.LoanAccountCal; UPDATE PRO.LoanAccountCal

### Calculation — DishonourCount

**Expression:**

```sql
(SELECT COUNT(*) FROM #NewSuspensions.DishonouredCheque.DishonouredCheque AS D2 WHERE PRO.DishonouredCheque.AccountId = PRO.DishonouredCheque.AccountId AND PRO.DishonouredCheque.DishonourDate >= @LookbackWindowStart)
```

**Output:**
`#PenaltyStaging.DishonourCount`

**Used By:**
INSERT INTO #PenaltyStaging

### Calculation — PenaltyAmount

**Expression:**

```sql
#NewSuspensions.DishonouredCheque.PenaltyAmount + #PenaltyStaging.PenaltyAmount
```

**Output:**
`PRO.ChequePenaltyLedger.PenaltyAmount`

**Used By:**
READ PRO.ChequePenaltyLedger


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.DishonouredCheque` | Read + Write | Updates: PRO.DishonouredCheque.PenaltyAmount, PRO.DishonouredCheque.HoldForReview, PRO.DishonouredCheque.PenaltyApplied |
| `PRO.LoanAccountCal` | Read + Write | Updates: PRO.LoanAccountCal.OutstandingBalance, ChequeBookSuspended |
| `PRO.ChequePenaltyLedger` | Read + Write | Provides: #NewSuspensions.DishonouredCheque.PenaltyAmount, #NewSuspensions.DishonouredCheque.DishonourCount, #NewSuspensions.DishonouredCheque.LastPenaltyDate, AccountId, FirstPenaltyDate |
| `PRO.AccountStatusAuditLog` | Write | Inserts data into: AccountId, TransitionDate, NewStatus, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Inserts data into: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT, RUNNINGPROCESSNAME |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#PenaltyStaging` | Read + Write | Inserts data into: AccountId, PenaltyAmount, DishonourCount |
| `#NewSuspensions` | Read + Write | Inserts data into: #PenaltyStaging.AccountId |

## Exception Handling

If an error occurs during the process, the status is updated to indicate an error, the error date is set to the current date, the error description is recorded, and the count is incremented.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
