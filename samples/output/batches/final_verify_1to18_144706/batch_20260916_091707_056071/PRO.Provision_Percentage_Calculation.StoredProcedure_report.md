# Provision Percentage Calculation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Percentage_Calculation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 6 needs review |
| Tables read | 2 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 6 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure calculates and updates the provision percentage and amount for accounts based on their asset class and outstanding balance, and tracks the process run status.

## Process Flow

1. Determine the provision percentage for each account based on its asset class.
2. Update the provision percentage for accounts that are not secured and have a non-standard asset class.
3. Calculate the provision amount for accounts with a positive outstanding balance.
4. Ensure the provision amount does not exceed the outstanding balance.
5. Increment the run count for the process and mark it as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Increment run count and mark as completed | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Increment the run count for the process and mark it as completed. |
| ⚠️ Determine provision percentage (ProvisionPct) | `ProvisionPct` | Set the provision percentage for accounts based on their asset class. |
| ⚠️ Determine provision percentage (A.ProvisionPct) | `ProvisionPct` | Set the provision percentage for accounts based on their asset class. |
| ⚠️ Calculate provision amount | `ProvisionAmount` | Calculate the provision amount for accounts with a positive outstanding balance. |
| ⚠️ Ensure provision amount does not exceed balance | `ProvisionAmount` | Ensure the provision amount does not exceed the outstanding balance for accounts. |
| ⚠️ Set senior review flag | `SeniorReviewFlag` | Set the senior review flag to 'Y' for accounts with a provision amount over 1 million. |

## Business Rules

### R1 — Increment run count and mark as completed

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- Process name matches 'Provision_Percentage_Calculation'

**Summary:**

- Increment the run count for the process and mark it as completed.

### Decision Logic

| Condition | Result |
|---|---|
| ProcessName = 'Provision_Percentage_Calculation' | COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 |


### R2 — Determine provision percentage (ProvisionPct)

**Affected Field:** `ProvisionPct`

**Summary:**

- Set the provision percentage for accounts based on their asset class.

**Source context:**

- Target: PRO.AccountCal
- FROM PRO.AccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.AccountCal.AssetClass = 'STANDARD' | 0.40 |
| PRO.AccountCal.AssetClass = 'SUBSTANDARD' | 15.00 |
| PRO.AccountCal.AssetClass = 'DOUBTFUL' | 25.00 |
| PRO.AccountCal.AssetClass = 'LOSS' | 100.00 |
| ELSE | 0.00 |

### R3 — Determine provision percentage (A.ProvisionPct)

**Affected Field:** `ProvisionPct`

**Summary:**

- Set the provision percentage for accounts based on their asset class.

### Decision Logic

| Condition | Result |
|---|---|
| AssetClass = 'STANDARD' | 0.40 |
| AssetClass = 'SUBSTANDARD' | 15.00 |
| AssetClass = 'DOUBTFUL' | 25.00 |
| AssetClass = 'LOSS' | 100.00 |
| ELSE | 0.00 |

### R4 — Calculate provision amount

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `ProvisionAmount`

**Applies to:**

- Account has a positive outstanding balance

**Summary:**

- Calculate the provision amount for accounts with a positive outstanding balance.

### Decision Logic

| Condition | Result |
|---|---|
| OutstandingBalance > 0 | (OutstandingBalance * ProvisionPct) / 100 |


### R5 — Ensure provision amount does not exceed balance

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `ProvisionAmount`

**Applies to:**

- Account provision amount exceeds outstanding balance

**Summary:**

- Ensure the provision amount does not exceed the outstanding balance for accounts.

### Decision Logic

| Condition | Result |
|---|---|
| ProvisionAmount > OutstandingBalance | OutstandingBalance |


### R6 — Set senior review flag

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `SeniorReviewFlag`

**Applies to:**

- Provision amount is greater than 1 million

**Summary:**

- Set the senior review flag to 'Y' for accounts with a provision amount over 1 million.

### Decision Logic

| Condition | Result |
|---|---|
| ProvisionAmount > 1000000 | 'Y' |

## Calculations

### Calculation — ProvisionPct

**Expression:**

```sql
ProvisionPct + 10.00
```

**Output:**
`PRO.AccountCal.ProvisionPct`

**Used By:**
UPDATE PRO.AccountCal; READ PRO.AccountCal

### Calculation — ProvisionAmount

**Expression:**

```sql
(OutstandingBalance * ProvisionPct) / 100
```

**Output:**
`PRO.AccountCal.ProvisionAmount`

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
| `PRO.AccountCal` | Read + Write | Updates: ProvisionPct, ProvisionAmount, SeniorReviewFlag |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |

## Exception Handling

No explicit exception handling is defined in the provided extraction. If an exception occurs during the execution of the 'Provision_Percentage_Calculation' process, the run status is updated to reflect the error.

## Findings / Needs Review

- Lines 45-48 (ASSIGNMENT/CALCULATION) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 57-60 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
