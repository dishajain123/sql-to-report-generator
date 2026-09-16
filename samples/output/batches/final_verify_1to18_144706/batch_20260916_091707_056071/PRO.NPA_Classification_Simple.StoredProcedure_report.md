# NPA Classification Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Classification_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 9 |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |

## What This Does

This procedure updates the classification status and additional provisioning for accounts marked as Non-Performing Assets (NPA) based on their overdue days and other conditions.

## Process Flow

1. Read the date for the given time key from the SysDayMatrix table.
2. Update the asset class, NPA flag, additional provision, classification date, and restructure review flag for active accounts with specific conditions.
3. Update the run status for the NPA classification process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Update RestructureReviewFlag | `RestructureReviewFlag` | Set the RestructureReviewFlag to 'Y' for accounts with overdue days between 61 and 90. |
| Update RunStatus [1] | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Mark the 'NPA_Classification_Simple' process as completed and increment the run count. |
| Determine AssetClass | `AssetClass` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine NpaFlag | `NpaFlag` | First matching row wins; ELSE includes false or NULL predicates. |
| Classify NPAs based on time key | `Not specified` | Classifies non-performing assets based on the provided time key. |
| Calculate additional provision | `AddlProvision` | Compute the additional provision for accounts with a specific NPA flag and non-zero additional provision percentage. |
| Calculate AddlProvision | `AddlProvision` | Calculate the additional provision for accounts flagged as NPA with a non-zero additional provision percentage. |
| Set ClassificationDate | `ClassificationDate` | Set the ClassificationDate for accounts newly marked as NPA this run. |
| Update RunStatus [2] | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Update the process status in the PRO.RunStatus table. |

## Business Rules

### R1 — Update RestructureReviewFlag

**Affected Field:** `RestructureReviewFlag`

**Applies to:**

- Account has overdue days between 61 and 90

**Summary:**

- Set the RestructureReviewFlag to 'Y' for accounts with overdue days between 61 and 90.

### Decision Logic

| Condition | Result |
|---|---|
| DaysPastDue BETWEEN 61 AND 90 | 'Y' |


### R2 — Update RunStatus [1]

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- Process name is 'NPA_Classification_Simple'

**Summary:**

- Mark the 'NPA_Classification_Simple' process as completed and increment the run count.

### Decision Logic

| Condition | Result |
|---|---|
| ProcessName = 'NPA_Classification_Simple' | COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 |


### R3 — Determine AssetClass

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

### R4 — Determine NpaFlag

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

### R5 — Classify NPAs based on time key

**Affected Field:** Not specified

**Applies to:** eligibility not documented.

**Summary:**

- Classifies non-performing assets based on the provided time key.


### R6 — Calculate additional provision

**Affected Field:** `AddlProvision`

**Applies to:**

- Account status is 'ACTIVE'
- NPA flag is 'Y'
- Additional provision percentage is not zero

**Summary:**

- Compute the additional provision for accounts with a specific NPA flag and non-zero additional provision percentage.


### R7 — Calculate AddlProvision

_Note: Also extracted with additional fields attached in another pass (A.AddlProvision) - kept the narrower, consistent version of this rule._

**Affected Field:** `AddlProvision`

**Applies to:**

- Account status is 'ACTIVE'
- NpaFlag is 'Y'

**Summary:**

- Calculate the additional provision for accounts flagged as NPA with a non-zero additional provision percentage.

### Decision Logic

| Condition | Result |
|---|---|
| NpaFlag = 'Y' AND ISNULL(AddlProvisionPer, 0) <> 0 | (OutstandingBalance * AddlProvisionPer) / 100 |


### R8 — Set ClassificationDate

**Affected Field:** `ClassificationDate`

**Applies to:**

- Account status is 'ACTIVE'
- NpaFlag is 'Y'

**Summary:**

- Set the ClassificationDate for accounts newly marked as NPA this run.

### Decision Logic

| Condition | Result |
|---|---|
| NpaFlag = 'Y' AND ClassificationDate IS NULL | @ProcessDate |


### R9 — Update RunStatus [2]

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- ProcessName is 'NPA_Classification_Simple'

**Summary:**

- Update the process status in the RunStatus table.

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

No explicit exception handling is defined in the provided SQL. If an error occurs during the execution of the 'NPA_Classification_Simple' process, the run status is updated to indicate the error and the run count is incremented.

## Findings / Needs Review

- Lines 67-70 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 2 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
