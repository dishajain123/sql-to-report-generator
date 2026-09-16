# NPA Classification Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Classification_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 7 |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |

## What This Does

The procedure updates the run status of the 'NPA_Classification_Simple' process, marking it as incomplete and recording an error if an exception occurs.

## Process Flow

1. Read the process date from the SysDayMatrix table.
2. Update the AssetClass field based on the DaysPastDue value.
3. Update the NpaFlag field based on the AssetClass value.
4. Calculate and update the AddlProvision field for accounts flagged as NPA.
5. Set the ClassificationDate for accounts newly marked as NPA.
6. Set the RestructureReviewFlag for accounts with DaysPastDue between 61 and 90.
7. Update the run status to mark the process as completed and increment the run count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine AssetClass | `AssetClass` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine NpaFlag | `NpaFlag` | First matching row wins; ELSE includes false or NULL predicates. |
| Classify NPA based on time key | `NPA_Classification` | Classifies non-performing assets based on the provided time key. |
| Calculate AddlProvision | `AddlProvision` | Calculate the additional provision for accounts flagged as NPA. |
| Set ClassificationDate | `ClassificationDate` | Set the ClassificationDate for accounts newly marked as NPA. |
| Set RestructureReviewFlag | `RestructureReviewFlag` | Set the RestructureReviewFlag for accounts with DaysPastDue between 61 and 90. |
| Update RunStatus | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | Update the run status to mark the process as completed and increment the run count. |

## Business Rules

### R1 — Determine AssetClass

**Affected Field:** `AssetClass`


**Applies to:**

- PRO.AccountCal.AccountStatus = 'ACTIVE'

**Source context:**

- Target: PRO.AccountCal
- FROM PRO.AccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.AccountCal.DaysPastDue <= 90 | 'STANDARD' |
| PRO.AccountCal.DaysPastDue BETWEEN 91 AND 180 | 'SUBSTANDARD' |
| PRO.AccountCal.DaysPastDue BETWEEN 181 AND 365 | 'DOUBTFUL' |
| ELSE | 'LOSS' |

### R2 — Determine NpaFlag

**Affected Field:** `NpaFlag`


**Applies to:**

- PRO.AccountCal.AccountStatus = 'ACTIVE'

**Source context:**

- Target: PRO.AccountCal
- FROM PRO.AccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.AccountCal.AssetClass = 'STANDARD' | 'N' |
| ELSE | 'Y' |

### R3 — Classify NPA based on time key

**Affected Field:** `NPA_Classification`

**Applies to:** eligibility not documented.

**Summary:**

- Classifies non-performing assets based on the provided time key.


### R4 — Calculate AddlProvision

**Affected Field:** `AddlProvision`

**Applies to:**

- NpaFlag = 'Y' AND ISNULL(AddlProvisionPer, 0) <> 0

**Summary:**

- Calculate the additional provision for accounts flagged as NPA.


### R5 — Set ClassificationDate

**Affected Field:** `ClassificationDate`

**Applies to:**

- NpaFlag = 'Y' AND ClassificationDate IS NULL

**Summary:**

- Set the ClassificationDate for accounts newly marked as NPA.


### R6 — Set RestructureReviewFlag

**Affected Field:** `RestructureReviewFlag`

**Applies to:**

- DaysPastDue BETWEEN 61 AND 90

**Summary:**

- Set the RestructureReviewFlag for accounts with DaysPastDue between 61 and 90.


### R7 — Update RunStatus

**Affected Field:** `COMPLETED, ErrorDate, ErrorDescription, RunCount`

**Applies to:**

- ProcessName = 'NPA_Classification_Simple'

**Summary:**

- Update the run status to mark the process as completed and increment the run count.

## Calculations

### Calculation — AddlProvision

**Expression:**

```sql
(OutstandingBalance * AddlProvisionPer) / 100
```

**Output:**
`PRO.AccountCal.AddlProvision`

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
| `PRO.AccountCal` | Read + Write | Updates: AssetClass, NpaFlag, AddlProvision, ClassificationDate, RestructureReviewFlag |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |
| `SysDayMatrix` | Read | Provides: [Date] |

## Exception Handling

The procedure uses a TRY/CATCH block to handle exceptions, but no specific exception handling is documented within the provided SQL. The procedure captures and logs any exceptions that occur during the 'NPA_Classification_Simple' process by updating the run status in the PRO.RunStatus table.

## Findings / Needs Review

- Lines 67-70 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
