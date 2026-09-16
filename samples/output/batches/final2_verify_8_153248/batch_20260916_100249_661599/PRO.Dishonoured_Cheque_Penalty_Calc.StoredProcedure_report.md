# Dishonoured Cheque Penalty Calc — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Dishonoured_Cheque_Penalty_Calc` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 18 |
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
| Set hold for review | `HoldForReview` | Mark a dishonoured cheque for review if it has not been penalized yet. |
| Mark penalty as applied [1] | `PenaltyApplied` | Mark the penalty as applied for a dishonoured cheque if it has a penalty amount. |
| Update outstanding balance | `OutstandingBalance` | Update the outstanding balance for loan accounts affected by dishonoured cheques. |
| Insert penalty staging data | `AccountId, PenaltyAmount, DishonourCount` | Insert staging data for penalty calculation into the penalty ledger. |
| Determine accounts for suspension | `AccountId` | Determine which accounts need their cheque books suspended based on dishonour count. |
| Mark penalty applied | `PenaltyApplied` | Mark cheques for which penalties have not been applied as applied. |
| Calculate dishonour count | `DishonourCount` | Calculate the count of dishonoured cheques for each account within the lookback window. |
| Update account balance | `OutstandingBalance` | Update the outstanding balance of loan accounts with a dishonour date matching the process date and a non-null penalty amount. |
| Suspend cheque book (P.AccountId) | `AccountId` | Suspend cheque books for accounts with repeated dishonours. |
| Merge penalty data | `Not specified` | Merge penalty data into the cheque penalty ledger. |
| Log account status | `Not specified` | Log account status transitions. |
| Hold cheque for review | `HoldForReview` | Hold cheques for review if the dishonour date matches the process date and the dishonour reason is null. |
| Mark penalty as applied [2] | `PenaltyApplied` | Mark penalties as applied for dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount. |
| Adjust outstanding balance | `OutstandingBalance` | Adjust the outstanding balance for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null… |
| Suspend cheque book (ChequeBookSuspended) | `ChequeBookSuspended` | Suspend the cheque book for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null penalty… |
| Suspend cheque book (A.ChequeBookSuspended) | `ChequeBookSuspended` | Suspend the cheque book for accounts that have been dishonoured three or more times and have not already had their cheque book suspended. |
| Set cheques to hold for review | `HoldForReview` | Mark dishonoured cheques to hold for review based on the time key. |
| Insert records into staging table | `AccountId, PenaltyAmount, DishonourCount` | Insert records into the staging table for further processing based on the time key. |

## Business Rules

### R1 — Set hold for review

**Affected Field:** `HoldForReview`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty not yet applied

**Summary:**

- Mark a dishonoured cheque for review if it has not been penalized yet.


### R2 — Mark penalty as applied [1]

**Affected Field:** `PenaltyApplied`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Mark the penalty as applied for a dishonoured cheque if it has a penalty amount.


### R3 — Update outstanding balance

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Update the outstanding balance for loan accounts affected by dishonoured cheques.


### R4 — Insert penalty staging data

**Affected Field:** `AccountId, PenaltyAmount, DishonourCount`

**Applies to:**

- Dishonoured cheque date matches process date
- Penalty amount is not null

**Summary:**

- Insert staging data for penalty calculation into the penalty ledger.


### R5 — Determine accounts for suspension

**Affected Field:** `AccountId`

**Applies to:**

- Dishonour count is 3 or more
- Cheque book is not already suspended

**Summary:**

- Determine which accounts need their cheque books suspended based on dishonour count.


### R6 — Mark penalty applied

**Affected Field:** `PenaltyApplied`

**Applies to:**

- Dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount

**Summary:**

- Mark cheques for which penalties have not been applied as applied.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | Set PenaltyApplied to 'Y' |


### R7 — Calculate dishonour count

**Affected Field:** `DishonourCount`

**Applies to:**

- Dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount

**Summary:**

- Calculate the count of dishonoured cheques for each account within the lookback window.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | Set DishonourCount to a calculated value |


### R8 — Update account balance

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Loan accounts with a dishonour date matching the process date and a non-null penalty amount

**Summary:**

- Update the outstanding balance of loan accounts with a dishonour date matching the process date and a non-null penalty amount.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | Set OutstandingBalance to a calculated value |


### R9 — Suspend cheque book (P.AccountId)

**Affected Field:** `AccountId`

**Applies to:**

- Accounts with a dishonour count of 3 or more and a cheque book that is not suspended or null

**Summary:**

- Suspend cheque books for accounts with repeated dishonours.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourCount >= 3 AND (ChequeBookSuspended <> 'Y' OR ChequeBookSuspended IS NULL) | Insert AccountId into #NewSuspensions |


### R10 — Merge penalty data

**Affected Field:** Not specified

**Applies to:**

- Dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount

**Summary:**

- Merge penalty data into the cheque penalty ledger.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | Merge penalty data into the cheque penalty ledger |


### R11 — Log account status

**Affected Field:** Not specified

**Applies to:**

- Accounts with an AccountId in the #NewSuspensions table

**Summary:**

- Log account status transitions.

### Decision Logic

| Condition | Result |
|---|---|
| AccountId IN (SELECT AccountId FROM #NewSuspensions) | Insert account status transition into AccountStatusAuditLog |


### R12 — Hold cheque for review

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


### R13 — Mark penalty as applied [2]

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


### R14 — Adjust outstanding balance

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


### R15 — Suspend cheque book (ChequeBookSuspended)

**Affected Field:** `ChequeBookSuspended`

**Applies to:**

- Dishonoured cheque has a dishonour date matching the process date
- Dishonoured cheque has a non-null penalty amount
- Cheque book is not already suspended

**Summary:**

- Suspend the cheque book for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null penalty amount, and where the account has not already been suspended.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourDate = @ProcessDate AND PenaltyAmount IS NOT NULL | 'Y' |


### R16 — Suspend cheque book (A.ChequeBookSuspended)

**Affected Field:** `ChequeBookSuspended`

**Applies to:**

- Account has been dishonoured three or more times
- Cheque book is not already suspended

**Summary:**

- Suspend the cheque book for accounts that have been dishonoured three or more times and have not already had their cheque book suspended.

### Decision Logic

| Condition | Result |
|---|---|
| DishonourCount >= 3 AND (ChequeBookSuspended <> 'Y' OR ChequeBookSuspended IS NULL) | Set ChequeBookSuspended to 'Y' |


### R17 — Set cheques to hold for review

**Affected Field:** `HoldForReview`

**Applies to:**

- Dishonoured cheque record exists

**Summary:**

- Mark dishonoured cheques to hold for review based on the time key.


### R18 — Insert records into staging table

**Affected Field:** `AccountId, PenaltyAmount, DishonourCount`

**Applies to:**

- Dishonoured cheque records exist

**Summary:**

- Insert records into the staging table for further processing based on the time key.

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
CASE
    WHEN DishonourReason IS NULL THEN NULL
    WHEN RepeatCount IS NULL OR RepeatCount = 0 THEN 350.00
    WHEN RepeatCount = 1 THEN 750.00
    ELSE 1500.00
END
```

**Output:**
`Not specified`

**Used By:**
Not specified


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

The procedure does not explicitly handle exceptions, but it updates the process status table to reflect any errors encountered during execution. The procedure handles exceptions by updating the process status with the current date and error message, and incrementing the count if the process is already running. If not running, it inserts a new status record.

## Findings / Needs Review

- Lines 103-103 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- The specific formulas or logic for calculating the penalty amount, setting cheques to hold for review, and applying the penalty are not provided.
- The criteria for selecting records to insert into the staging table are not detailed.
- The specific conditions under which the process status is updated are not described.
- 3 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
