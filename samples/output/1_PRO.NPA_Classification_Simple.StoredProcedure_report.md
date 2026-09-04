# NPA Classification Simple — Business Logic Report

**Procedure:** `PRO.NPA_Classification_Simple`  ·  **Dialect:** T-SQL  ·  **Input:** `@TimeKey` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Classification_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 5 |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | No |

## What This Does

This procedure classifies the asset class of active accounts based on the number of days past due, flags accounts as Non-Performing Assets (NPA), calculates additional provisioning for NPA accounts, stamps the classification date, and flags accounts for restructuring review.

## Process Flow

1. Classify the account's asset class based on the number of days past due.
2. Flag the account as NPA if it is not classified as Standard.
3. Calculate the additional provisioning for accounts flagged as NPA.
4. Stamp the classification date for accounts newly marked as NPA.
5. Flag accounts with 61 to 90 days past due for restructuring review.
6. Update the run status to indicate successful completion or failure.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Classify asset class by overdue days | `AssetClass` | Classifies the account's asset class based on the number of days past due. If the account is overdue by 90 days or less, it is classified a… |
| Flag account as NPA | `NpaFlag` | Flags the account as a Non-Performing Asset (NPA) if its asset class is not Standard. If the asset class is Standard, the NPA flag is set t… |
| Calculate additional provisioning | `AddlProvision` | Calculates the additional provisioning for accounts flagged as NPA based on the outstanding balance and additional provision percentage. |
| Stamp classification date | `ClassificationDate` | Stamps the classification date for accounts newly marked as NPA if the classification date is currently NULL. |
| Flag for restructuring review | `RestructureReviewFlag` | Flags accounts with 61 to 90 days past due for restructuring review. |

## Business Rules

### R1 — Classify asset class by overdue days

**Affected Field:** `AssetClass`

**Summary:**

- Classifies the account's asset class based on the number of days past due. If the account is overdue by 90 days or less, it is classified as Standard. If overdue by 91 to 180 days, it is classified as Substandard. If overdue by 181 to 365 days, it is classified as Doubtful. Otherwise, it is classified as Loss.

### Decision Logic

| Condition | Result |
|---|---|
| DaysPastDue <= 90 | 'STANDARD' |
| DaysPastDue BETWEEN 91 AND 180 | 'SUBSTANDARD' |
| DaysPastDue BETWEEN 181 AND 365 | 'DOUBTFUL' |
| ELSE | 'LOSS' |


### R2 — Flag account as NPA

**Affected Field:** `NpaFlag`

**Summary:**

- Flags the account as a Non-Performing Asset (NPA) if its asset class is not Standard. If the asset class is Standard, the NPA flag is set to 'N'. Otherwise, it is set to 'Y'.

### Decision Logic

| Condition | Result |
|---|---|
| AssetClass = 'STANDARD' | 'N' |
| ELSE | 'Y' |


### R3 — Calculate additional provisioning

**Affected Field:** `AddlProvision`

**Summary:**

- Calculates the additional provisioning for accounts flagged as NPA based on the outstanding balance and additional provision percentage.


### R4 — Stamp classification date

**Affected Field:** `ClassificationDate`

**Summary:**

- Stamps the classification date for accounts newly marked as NPA if the classification date is currently NULL.


### R5 — Flag for restructuring review

**Affected Field:** `RestructureReviewFlag`

**Summary:**

- Flags accounts with 61 to 90 days past due for restructuring review.

## Calculations

### Calculation — AddlProvision

**Expression:**
(OutstandingBalance * AddlProvisionPer) / 100

**Output:**
PRO.AccountCal.AddlProvision

**Used By:**
UPDATE PRO.AccountCal


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AccountCal` | Read + Write | Updates: AssetClass, NpaFlag, AddlProvision, ClassificationDate, RestructureReviewFlag |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |
| `SysDayMatrix` | Read | Provides: [Date] |

_1 working/temporary table(s) used only for intermediate calculation steps are omitted here - see the pipeline run log for the full technical lineage._

## Exception Handling

If an error occurs during the execution of the procedure, the run status is updated to indicate failure, and the error details are recorded.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
