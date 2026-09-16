# Provision Percentage Calculation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Percentage_Calculation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 1 confident, 5 needs review |
| Tables read | 2 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 5 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure updates the run status of the 'Provision_Percentage_Calculation' process, marking it as incomplete and incrementing the run count if an error occurs during execution.

## Process Flow

1. Set the provision percentage based on the asset class.
2. Increase the provision percentage by 10% for unsecured accounts with non-standard asset classes.
3. Calculate the provision amount based on the outstanding balance and provision percentage.
4. Ensure the provision amount does not exceed the outstanding balance.
5. Flag accounts for senior review if the provision amount exceeds 1,000,000.
6. Update the process status to mark the process as completed and increment the run count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine ProvisionPct | `ProvisionPct` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Set provision percentage by asset class | `ProvisionPct` | Determine the provision percentage based on the asset class of the account. |
| ⚠️ Calculate provision amount | `ProvisionAmount` | Calculate the provision amount based on the outstanding balance and provision percentage. |
| ⚠️ Ensure provision amount does not exceed balance | `ProvisionAmount` | Ensure the provision amount does not exceed the outstanding balance. |
| ⚠️ Flag accounts for senior review | `SeniorReviewFlag` | Flag accounts for senior review if the provision amount exceeds 1,000,000. |
| ⚠️ Update process status | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | Update the process status to mark the process as completed and increment the run count. |

## Business Rules

### R1 — Determine ProvisionPct

**Affected Field:** `ProvisionPct`


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

### R2 — Set provision percentage by asset class

**Affected Field:** `ProvisionPct`

**Summary:**

- Determine the provision percentage based on the asset class of the account.

### Decision Logic

| Condition | Result |
|---|---|
| AssetClass = 'STANDARD' | 0.40 |
| AssetClass = 'SUBSTANDARD' | 15.00 |
| AssetClass = 'DOUBTFUL' | 25.00 |
| AssetClass = 'LOSS' | 100.00 |
| ELSE |  |

### R3 — Calculate provision amount

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `ProvisionAmount`

**Applies to:**

- Account has a positive outstanding balance

**Summary:**

- Calculate the provision amount based on the outstanding balance and provision percentage.


### R4 — Ensure provision amount does not exceed balance

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `ProvisionAmount`

**Applies to:**

- Provision amount exceeds the outstanding balance

**Summary:**

- Ensure the provision amount does not exceed the outstanding balance.


### R5 — Flag accounts for senior review

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `SeniorReviewFlag`

**Applies to:**

- Provision amount exceeds 1,000,000

**Summary:**

- Flag accounts for senior review if the provision amount exceeds 1,000,000.


### R6 — Update process status

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `COMPLETED, ErrorDate, ErrorDescription, RunCount`

**Applies to:**

- Process name matches 'Provision_Percentage_Calculation'

**Summary:**

- Update the process status to mark the process as completed and increment the run count.

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

If an error occurs during the execution of the 'Provision_Percentage_Calculation' process, the run status is updated to reflect the error and the run count is incremented.

## Findings / Needs Review

- Lines 45-48 (ASSIGNMENT/CALCULATION) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 57-60 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
