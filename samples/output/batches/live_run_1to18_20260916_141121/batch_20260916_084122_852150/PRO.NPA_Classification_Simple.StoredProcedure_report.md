# NPA Classification Simple — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Classification_Simple` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 2 confident, 4 needs review |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 4 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure updates the run status of the 'NPA_Classification_Simple' process, marking it as incomplete and incrementing the run count if an error occurs during execution.

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
| Determine AssetClass (AssetClass) | `AssetClass` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine NpaFlag | `NpaFlag` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Determine AssetClass (A.AssetClass, A.NpaFlag) | `AssetClass, NpaFlag` | Classify the account based on the DaysPastDue value. |
| ⚠️ Calculate AddlProvision | `AddlProvision` | Calculate the additional provision for accounts flagged as NPA. |
| ⚠️ Set ClassificationDate | `ClassificationDate` | Set the ClassificationDate for accounts newly marked as NPA. |
| ⚠️ Set RestructureReviewFlag | `RestructureReviewFlag` | Set the RestructureReviewFlag for accounts with DaysPastDue between 61 and 90. |

## Business Rules

### R1 — Determine AssetClass (AssetClass)

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

### R3 — Determine AssetClass (A.AssetClass, A.NpaFlag)

**Affected Field:** `AssetClass, NpaFlag`

**Summary:**

- Classify the account based on the DaysPastDue value.

### Decision Logic

| Condition | Result |
|---|---|
| DaysPastDue <= 90 | 'STANDARD' |
| DaysPastDue BETWEEN 91 AND 180 | 'SUBSTANDARD' |
| DaysPastDue BETWEEN 181 AND 365 | 'DOUBTFUL' |
| AssetClass = 'STANDARD' | 'N' |
| ELSE |  |

### R4 — Calculate AddlProvision

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AddlProvision`

**Applies to:**

- NpaFlag = 'Y'

**Summary:**

- Calculate the additional provision for accounts flagged as NPA.


### R5 — Set ClassificationDate

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `ClassificationDate`

**Applies to:**

- NpaFlag = 'Y'

**Summary:**

- Set the ClassificationDate for accounts newly marked as NPA.


### R6 — Set RestructureReviewFlag

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RestructureReviewFlag`

**Applies to:** eligibility not documented.

**Summary:**

- Set the RestructureReviewFlag for accounts with DaysPastDue between 61 and 90.

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

The procedure uses a TRY-CATCH block to handle exceptions, but the specific handling steps are not detailed in the extraction. If an error occurs during the execution of the 'NPA_Classification_Simple' process, the run status is updated to indicate an error and the error details are recorded.

## Findings / Needs Review

- Lines 67-70 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
