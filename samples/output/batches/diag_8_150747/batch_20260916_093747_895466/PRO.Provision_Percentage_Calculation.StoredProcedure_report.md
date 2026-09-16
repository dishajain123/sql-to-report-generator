# Provision Percentage Calculation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Percentage_Calculation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 5 needs review |
| Tables read | 2 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 5 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

This procedure calculates and updates the provision percentage and amount for accounts, flags accounts for senior review if the provision amount exceeds a million, and updates the run status for the process.

## Process Flow

1. Update the provision percentage for accounts based on their asset class.
2. Increase the provision percentage by 10% for certain accounts.
3. Calculate the provision amount based on the outstanding balance and updated provision percentage.
4. Ensure the provision amount does not exceed the outstanding balance.
5. Increment the run count for the 'Provision_Percentage_Calculation' process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Determine Provision Percentage (ProvisionPct) | `ProvisionPct` | Set the provision percentage based on the asset class of the account. |
| ⚠️ Determine Provision Percentage (A.ProvisionPct) | `ProvisionPct` | Set the provision percentage based on the asset class of the account. |
| ⚠️ Increment Run Count | `RunCount` | Increment the run count for the 'Provision_Percentage_Calculation' process. |
| ⚠️ Ensure Provision Amount Does Not Exceed Balance | `ProvisionAmount` | Ensure the provision amount does not exceed the outstanding balance. |
| ⚠️ Flag for Senior Review | `SeniorReviewFlag` | Flag accounts for senior review if the provision amount exceeds one million. |

## Business Rules

### R1 — Determine Provision Percentage (ProvisionPct)

**Affected Field:** `ProvisionPct`

**Summary:**

- Set the provision percentage based on the asset class of the account.

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

### R2 — Determine Provision Percentage (A.ProvisionPct)

**Affected Field:** `ProvisionPct`

**Summary:**

- Set the provision percentage based on the asset class of the account.

### Decision Logic

| Condition | Result |
|---|---|
| AssetClass = 'STANDARD' | 0.40 |
| AssetClass = 'SUBSTANDARD' | 15.00 |
| AssetClass = 'DOUBTFUL' | 25.00 |
| AssetClass = 'LOSS' | 100.00 |
| ELSE | 0.00 |

### R3 — Increment Run Count

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RunCount`

**Applies to:**

- Process name is 'Provision_Percentage_Calculation'

**Summary:**

- Increment the run count for the 'Provision_Percentage_Calculation' process.

### Decision Logic

| Condition | Result |
|---|---|
| ProcessName = 'Provision_Percentage_Calculation' | RunCount + 1 |


### R4 — Ensure Provision Amount Does Not Exceed Balance

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `ProvisionAmount`

**Applies to:**

- Provision amount exceeds outstanding balance

**Summary:**

- Ensure the provision amount does not exceed the outstanding balance.

### Decision Logic

| Condition | Result |
|---|---|
| ProvisionAmount > OutstandingBalance | OutstandingBalance |


### R5 — Flag for Senior Review

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `SeniorReviewFlag`

**Applies to:**

- Provision amount exceeds one million

**Summary:**

- Flag accounts for senior review if the provision amount exceeds one million.

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
`PRO.RunStatus.RunCount`

**Used By:**
UPDATE PRO.RunStatus; READ PRO.RunStatus

### Calculation — ProvisionPct

**Expression:**

```sql
CASE AssetClass
    WHEN 'STANDARD' THEN 0.40
    WHEN 'SUBSTANDARD' THEN 15.00
    WHEN 'DOUBTFUL' THEN 25.00
    WHEN 'LOSS' THEN 100.00
    ELSE 0.00
END
```

**Output:**
`Not specified`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AccountCal` | Read + Write | Updates: ProvisionPct, ProvisionAmount, SeniorReviewFlag |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |

## Exception Handling

If an error occurs during the execution of the 'Provision_Percentage_Calculation' process, the run status is updated to reflect the error and the run count is incremented.

## Findings / Needs Review

- Lines 45-48 (ASSIGNMENT/CALCULATION) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 57-60 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 2 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
