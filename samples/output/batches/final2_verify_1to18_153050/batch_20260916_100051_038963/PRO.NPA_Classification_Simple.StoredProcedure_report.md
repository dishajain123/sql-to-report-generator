# NPA Classification Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Classification_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 7 needs review |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ℹ️ **Additional rules added from a targeted review pass.** 7 rule(s) were added after a second, narrowly-scoped look at a source line no rule initially cited - the model's call succeeded normally, but a new rule for a previously-unreviewed line still warrants a quick human check against the source; affected rules are marked inline. |

## What This Does

This procedure updates the classification status and additional provisioning for accounts marked as Non-Performing Assets (NPA) based on their overdue days and other conditions.

## Process Flow

1. Read the current date from the SysDayMatrix table.
2. Update the AddlProvision for accounts flagged as NPA with a non-zero additional provisioning percentage.
3. Update the ClassificationDate for accounts newly marked as NPA.
4. Set the RestructureReviewFlag for accounts with overdue days between 61 and 90.
5. Update the run status for the NPA_Classification_Simple process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Classify asset based on days past due (AssetClass) | `AssetClass` | Classify the account's asset class based on the number of days past due. |
| ⚠️ Classify asset based on days past due (A.AssetClass, A.NpaFlag) | `AssetClass, NpaFlag` | Classify the account's asset class based on the number of days past due. |
| ⚠️ Set NPA flag based on asset class | `NpaFlag` | Set the NPA flag for active accounts based on the asset class. |
| ⚠️ Calculate additional provision | `AddlProvision` | Calculate the additional provision for accounts flagged as NPA with a non-zero additional provisioning percentage. |
| ⚠️ Set classification date | `ClassificationDate` | Set the classification date for accounts newly marked as NPA. |
| ⚠️ Set RestructureReviewFlag | `RestructureReviewFlag` | Set the RestructureReviewFlag for accounts with overdue days between 61 and 90. |
| ⚠️ Update run status | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Update the run status for the 'NPA_Classification_Simple' process. |

## Business Rules

### R1 — Classify asset based on days past due (AssetClass)

**Affected Field:** `AssetClass`

**Summary:**

- Classify the account's asset class based on the number of days past due.

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

### R2 — Classify asset based on days past due (A.AssetClass, A.NpaFlag)

**Affected Field:** `AssetClass, NpaFlag`

**Summary:**

- Classify the account's asset class based on the number of days past due.

### Decision Logic

| Condition | Result |
|---|---|
| DaysPastDue <= 90 | 'STANDARD' |
| DaysPastDue BETWEEN 91 AND 180 | 'SUBSTANDARD' |
| DaysPastDue BETWEEN 181 AND 365 | 'DOUBTFUL' |
| AssetClass = 'STANDARD' | 'N' |
| ELSE | 'LOSS'; 'Y' |

### R3 — Set NPA flag based on asset class

**Affected Field:** `NpaFlag`

**Summary:**

- Set the NPA flag for active accounts based on the asset class.

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

### R4 — Calculate additional provision

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `AddlProvision`

**Applies to:**

- AccountStatus is 'ACTIVE'

**Summary:**

- Calculate the additional provision for accounts flagged as NPA with a non-zero additional provisioning percentage.

### Decision Logic

| Condition | Result |
|---|---|
| NpaFlag = 'Y' AND ISNULL(AddlProvisionPer, 0) <> 0 | (OutstandingBalance * AddlProvisionPer) / 100 |


### R5 — Set classification date

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `ClassificationDate`

**Applies to:**

- AccountStatus is 'ACTIVE'

**Summary:**

- Set the classification date for accounts newly marked as NPA.

### Decision Logic

| Condition | Result |
|---|---|
| NpaFlag = 'Y' AND ClassificationDate IS NULL | current date |


### R6 — Set RestructureReviewFlag

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `RestructureReviewFlag`

**Applies to:**

- AccountStatus is 'ACTIVE'

**Summary:**

- Set the RestructureReviewFlag for accounts with overdue days between 61 and 90.

### Decision Logic

| Condition | Result |
|---|---|
| DaysPastDue BETWEEN 61 AND 90 | 'Y' |


### R7 — Update run status

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- ProcessName is 'NPA_Classification_Simple'

**Summary:**

- Update the run status for the 'NPA_Classification_Simple' process.

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

No explicit exception handling is defined in the provided SQL. If an exception occurs during the execution of the 'NPA_Classification_Simple' process, the run status is updated to reflect the error.

## Findings / Needs Review

- Lines 67-70 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
