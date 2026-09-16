# Dishonoured Cheque Penalty Calc — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Dishonoured_Cheque_Penalty_Calc` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 14 |
| Tables read | 5 |
| Tables written | 5 |
| Produces audit trail | Not detected |

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
| Set hold for review (D.HoldForReview) | `HoldForReview` | Mark a dishonoured cheque for review if it has not been penalized yet. |
| Mark penalty as applied | `PenaltyApplied` | Mark the penalty as applied for a dishonoured cheque if it has a penalty amount. |
| Update outstanding balance [1] | `OutstandingBalance` | Update the outstanding balance for loan accounts affected by dishonoured cheques. |
| Insert suspension records | `AccountId` | Insert records into the temporary table for accounts to suspend cheque books. |
| Mark cheque for review | `HoldForReview` | Mark cheques for review if the dishonour reason is not specified. |
| Apply penalty to cheque | `PenaltyApplied` | Apply penalties to cheques where the penalty amount is not null. |
| Calculate dishonour count | `DishonourCount` | Calculate the count of dishonoured cheques for each account within a specified lookback window. |
| Suspend cheque book (P.AccountId) | `AccountId` | Determine accounts to suspend cheque books based on repeated dishonours. |
| Update outstanding balance [2] | `OutstandingBalance` | Update outstanding balances in loan accounts. |
| Log account status transition | `AccountId` | Log account status transitions and process completion status. |
| Suspend cheque book (ChequeBookSuspended) | `ChequeBookSuspended` | Suspend the cheque book for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null penalty… |
| Suspend cheque book (A.ChequeBookSuspended) | `ChequeBookSuspended` | Suspend the cheque book for accounts with a sufficient number of dishonoured cheques within the lookback window and where the cheque book i… |
| Set hold for review (HoldForReview) | `HoldForReview` | Mark cheques that need review for penalty application. |
| Insert into staging | `AccountId, PenaltyAmount, DishonourCount` | Insert records into a staging table for further processing. |

## Business Rules

### R1 — Set hold for review (D.HoldForReview)

**Affected Field:** `HoldForReview`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty not yet applied

**Summary:**

- Mark a dishonoured cheque for review if it has not been penalized yet.


### R2 — Mark penalty as applied

**Affected Field:** `PenaltyApplied`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Mark the penalty as applied for a dishonoured cheque if it has a penalty amount.


### R3 — Update outstanding balance [1]

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Update the outstanding balance for loan accounts affected by dishonoured cheques.


### R4 — Insert suspension records

**Affected Field:** `AccountId`

**Applies to:**

- Dishonour count is 3 or more
- Cheque book is not already suspended or status is unknown

**Summary:**

- Insert records into the temporary table for accounts to suspend cheque books.


### R5 — Mark cheque for review

**Affected Field:** `HoldForReview`

**Applies to:**

- Dishonoured cheque date matches process date
- Dishonour reason is not specified

**Summary:**

- Mark cheques for review if the dishonour reason is not specified.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND DishonourReason IS NULL | Set HoldForReview to 'Y' |


### R6 — Apply penalty to cheque

**Affected Field:** `PenaltyApplied`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Apply penalties to cheques where the penalty amount is not null.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND NOT PenaltyAmount IS NULL | Set PenaltyApplied to 'Y' |


### R7 — Calculate dishonour count

**Affected Field:** `DishonourCount`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Calculate the count of dishonoured cheques for each account within a specified lookback window.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | Insert account ID, penalty amount, and dishonour count into a staging table |


### R8 — Suspend cheque book (P.AccountId)

**Affected Field:** `AccountId`

**Applies to:**

- Dishonour count is 3 or more
- Cheque book is not already suspended or status is unknown

**Summary:**

- Determine accounts to suspend cheque books based on repeated dishonours.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourCount >= 3 AND (ChequeBookSuspended <> 'Y' OR ChequeBookSuspended IS NULL) | Insert account ID into a temporary table for suspension |


### R9 — Update outstanding balance [2]

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Update outstanding balances in loan accounts.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND NOT PenaltyAmount IS NULL | Add penalty amount to the outstanding balance |


### R10 — Log account status transition

**Affected Field:** `AccountId`

**Applies to:**

- Account ID is in the list of accounts to suspend cheque books

**Summary:**

- Log account status transitions and process completion status.

### Decision Logic

| Condition | Result |
|---|---|
| AccountId IN (SELECT AccountId FROM #NewSuspensions) | Insert account ID, transition date, new status, and reason into the account status audit log |


### R11 — Suspend cheque book (ChequeBookSuspended)

**Affected Field:** `ChequeBookSuspended`

**Applies to:**

- Dishonoured cheque has a dishonour date matching the process date
- Dishonoured cheque has a non-null penalty amount
- Cheque book is not already suspended

**Summary:**

- Suspend the cheque book for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null penalty amount, and the account is not already suspended.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | 'Y' |


### R12 — Suspend cheque book (A.ChequeBookSuspended)

**Affected Field:** `ChequeBookSuspended`

**Applies to:**

- Account has a sufficient number of dishonoured cheques
- Cheque book is not already suspended

**Summary:**

- Suspend the cheque book for accounts with a sufficient number of dishonoured cheques within the lookback window and where the cheque book is not already suspended.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourCount >= 3 AND (ChequeBookSuspended <> 'Y' OR ChequeBookSuspended IS NULL) | 'Y' |


### R13 — Set hold for review (HoldForReview)

**Affected Field:** `HoldForReview`

**Applies to:**

- Dishonoured cheque record exists

**Summary:**

- Mark cheques that need review for penalty application.

### Decision Logic

| Condition | Result |
|---|---|
| HoldForReview is NULL | Set to 'Y' |


### R14 — Insert into staging

**Affected Field:** `AccountId, PenaltyAmount, DishonourCount`

**Applies to:**

- Dishonoured cheque record exists

**Summary:**

- Insert records into a staging table for further processing.

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

The procedure uses a CATCH block to handle exceptions, updating the process status with the current date, error message, and incrementing the count if the process is running. If the process is not running, it inserts a new process status record.

## Findings / Needs Review

- Lines 103-103 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 123-125 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 134-136 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The exact logic for calculating the penalty amount is not detailed in the extraction.
- The specific conditions under which the penalty is applied are not explicitly stated.
- The staging table #PenaltyStaging is used but its purpose and subsequent processing are not detailed.
- 3 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
