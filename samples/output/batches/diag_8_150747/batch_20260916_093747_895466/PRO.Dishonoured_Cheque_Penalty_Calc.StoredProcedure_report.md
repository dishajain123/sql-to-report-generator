# Dishonoured Cheque Penalty Calc — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Dishonoured_Cheque_Penalty_Calc` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 20 |
| Tables read | 5 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

The procedure calculates penalties for dishonoured cheques based on the time key provided, updating various fields in the DishonouredCheque table and logging process status.

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
| Mark penalty applied | `PenaltyApplied` | Mark cheques for which penalties have not been applied as applied. |
| Calculate dishonour count [1] | `DishonourCount` | Calculate the count of dishonoured cheques for each account within the lookback window. |
| Update account balance | `OutstandingBalance` | Update the outstanding balance of loan accounts with a dishonour date matching the process date and a non-null penalty amount. |
| Suspend cheque book | `Not specified` | Suspend cheque books for accounts with a dishonour count greater than or equal to 3 and no current suspension. |
| Hold cheque for review | `HoldForReview` | Hold cheques for review if the dishonour date matches the process date and the dishonour reason is null. |
| Mark penalty as applied | `PenaltyApplied` | Mark penalties as applied for dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount. |
| Adjust outstanding balance | `OutstandingBalance` | Adjust the outstanding balance for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null… |
| Suspend cheque book (ChequeBookSuspended) | `ChequeBookSuspended` | Suspend the cheque book for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null penalty… |
| Log account status transition | `AccountId, TransitionDate, NewStatus, Reason` | Log the transition of account status to 'CHEQUE_BOOK_SUSPENDED' for accounts with sufficient dishonour counts and where the cheque book is… |
| Suspend cheque book (A.ChequeBookSuspended) | `ChequeBookSuspended` | Suspend the cheque book for accounts with 3 or more dishonoured cheques and no current suspension, and log the suspension reason. |
| Set hold for review | `HoldForReview` | Mark cheques that need review for penalty application. |
| Insert into staging | `AccountId, PenaltyAmount, DishonourCount` | Insert records into a staging table for further processing. |
| Calculate penalty amount (PenaltyAmount) | `PenaltyAmount` | Determine the penalty amount for a dishonoured cheque based on the dishonour date and repeat count. |
| Calculate penalty amount (D.PenaltyAmount) | `PenaltyAmount` | Determine the penalty amount for a dishonoured cheque based on the dishonour date and repeat count. |
| Set cheques to hold for review | `HoldForReview` | Mark cheques for review if certain conditions are met. |
| Update penalty applied flag | `PenaltyApplied` | Update the penalty applied flag for cheques with a penalty amount. |
| Determine accounts for suspension | `AccountId` | Determine accounts that need suspension based on the dishonour count and cheque book status. |
| Update account status audit log | `AccountId` | Update the account status audit log for suspended accounts. |
| Merge penalty data | `Not specified` | Merge penalty data into the cheque penalty ledger. |
| Log account status | `Not specified` | Log account status transitions. |

## Business Rules

### R1 — Mark penalty applied

**Affected Field:** `PenaltyApplied`

**Applies to:**

- Dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount

**Summary:**

- Mark cheques for which penalties have not been applied as applied.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | Set PenaltyApplied to 'Y' |


### R2 — Calculate dishonour count [1]

**Affected Field:** `DishonourCount`

**Applies to:**

- Dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount

**Summary:**

- Calculate the count of dishonoured cheques for each account within the lookback window.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | Set DishonourCount to a calculated value |


### R3 — Update account balance

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Loan accounts with a dishonour date matching the process date and a non-null penalty amount

**Summary:**

- Update the outstanding balance of loan accounts with a dishonour date matching the process date and a non-null penalty amount.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | Set OutstandingBalance to a calculated value |


### R4 — Suspend cheque book

**Affected Field:** Not specified

**Applies to:**

- Accounts with a dishonour count greater than or equal to 3 and no current suspension

**Summary:**

- Suspend cheque books for accounts with a dishonour count greater than or equal to 3 and no current suspension.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourCount >= 3 AND (ChequeBookSuspended <> 'Y' OR ChequeBookSuspended IS NULL) | Insert account IDs into #NewSuspensions |


### R5 — Hold cheque for review

**Affected Field:** `HoldForReview`

**Applies to:**

- Dishonoured cheque has a dishonour date matching the process date
- Dishonour reason is null

**Summary:**

- Hold cheques for review if the dishonour date matches the process date and the dishonour reason is null.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND DishonourReason IS NULL | 'Y' |


### R6 — Mark penalty as applied

**Affected Field:** `PenaltyApplied`

**Applies to:**

- Dishonoured cheque has a dishonour date matching the process date
- Dishonoured cheque has a non-null penalty amount

**Summary:**

- Mark penalties as applied for dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND NOT PenaltyAmount IS NULL | 'Y' |


### R7 — Adjust outstanding balance

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Dishonoured cheque has a dishonour date matching the process date
- Dishonoured cheque has a non-null penalty amount

**Summary:**

- Adjust the outstanding balance for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null penalty amount.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND NOT PenaltyAmount IS NULL | COALESCE(OutstandingBalance, 0) + PenaltyAmount |


### R8 — Suspend cheque book (ChequeBookSuspended)

**Affected Field:** `ChequeBookSuspended`

**Applies to:**

- Dishonoured cheque has a dishonour date matching the process date
- Dishonoured cheque has a non-null penalty amount

**Summary:**

- Suspend the cheque book for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null penalty amount, and where the account is not already suspended.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | 'Y' |


### R9 — Log account status transition

**Affected Field:** `AccountId, TransitionDate, NewStatus, Reason`

**Applies to:**

- Account ID is in the list of accounts to be suspended

**Summary:**

- Log the transition of account status to 'CHEQUE_BOOK_SUSPENDED' for accounts with sufficient dishonour counts and where the cheque book is not already suspended.


### R10 — Suspend cheque book (A.ChequeBookSuspended)

**Affected Field:** `ChequeBookSuspended`

**Applies to:**

- Accounts with 3 or more dishonoured cheques
- Cheque book not currently suspended

**Summary:**

- Suspend the cheque book for accounts with 3 or more dishonoured cheques and no current suspension, and log the suspension reason.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourCount >= 3 AND (ChequeBookSuspended <> 'Y' OR ChequeBookSuspended IS NULL) | Set ChequeBookSuspended to 'Y' and log the suspension in the account status audit log |


### R11 — Set hold for review

**Affected Field:** `HoldForReview`

**Applies to:**

- Dishonoured cheque record exists

**Summary:**

- Mark cheques that need review for penalty application.

### Decision Logic

| Condition | Result |
|---|---|
| HoldForReview is NULL | Set to 'Y' |


### R12 — Insert into staging

**Affected Field:** `AccountId, PenaltyAmount, DishonourCount`

**Applies to:**

- Dishonoured cheque record exists

**Summary:**

- Insert records into a staging table for further processing.


### R13 — Calculate penalty amount (PenaltyAmount)

**Affected Field:** `PenaltyAmount`

**Summary:**

- Determine the penalty amount for a dishonoured cheque based on the dishonour date and repeat count.

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

### R14 — Calculate penalty amount (D.PenaltyAmount)

**Affected Field:** `PenaltyAmount`

**Summary:**

- Determine the penalty amount for a dishonoured cheque based on the dishonour date and repeat count.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourReason IS NULL | NULL |
| RepeatCount IS NULL OR RepeatCount = 0 | 350.00 |
| RepeatCount = 1 | 750.00 |
| ELSE | 1500.00 |

### R15 — Set cheques to hold for review

**Affected Field:** `HoldForReview`

**Applies to:**

- Dishonoured cheques with a dishonour date matching the process date and no dishonour reason

**Summary:**

- Mark cheques for review if certain conditions are met.


### R16 — Update penalty applied flag

**Affected Field:** `PenaltyApplied`

**Applies to:**

- Dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount

**Summary:**

- Update the penalty applied flag for cheques with a penalty amount.


### R17 — Determine accounts for suspension

**Affected Field:** `AccountId`

**Applies to:**

- Accounts with a dishonour count of 3 or more and a cheque book not suspended or status unknown

**Summary:**

- Determine accounts that need suspension based on the dishonour count and cheque book status.


### R18 — Update account status audit log

**Affected Field:** `AccountId`

**Applies to:**

- Accounts that are to be suspended

**Summary:**

- Update the account status audit log for suspended accounts.


### R19 — Merge penalty data

**Affected Field:** Not specified

**Applies to:** eligibility not documented.

**Summary:**

- Merge penalty data into the cheque penalty ledger.


### R20 — Log account status

**Affected Field:** Not specified

**Applies to:** eligibility not documented.

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

### Calculation — PenaltyAmount

**Expression:**

```sql
    (CASE
    WHEN DishonourReason IS NULL THEN NULL
    WHEN RepeatCount IS NULL OR RepeatCount = 0 THEN 350.00
    WHEN RepeatCount = 1 THEN 750.00
    ELSE 1500.00
END)
```

**Output:**
`PRO.DishonouredCheque.PenaltyAmount`

**Used By:**
UPDATE PRO.DishonouredCheque


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

The procedure does not explicitly handle exceptions; it relies on the calling context to manage errors. The procedure uses a TRY-CATCH block to handle exceptions, updating the process status with the current date, error message, and incrementing the count if an exception occurs.

## Findings / Needs Review

- Lines 103-103 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- The exact calculation method for the penalty amount is not specified in the extraction.
- The criteria for setting a cheque to 'HoldForReview' are not detailed in the extraction.
- 2 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
