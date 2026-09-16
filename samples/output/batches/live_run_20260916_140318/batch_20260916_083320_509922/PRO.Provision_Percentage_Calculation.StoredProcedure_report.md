# Provision Percentage Calculation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Percentage_Calculation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 1 confident, 2 needs review |
| Tables read | 2 |
| Tables written | 2 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 2 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

This procedure calculates and updates the provision percentage and amount for accounts, and tracks the process run status.

## Process Flow

1. Set the provision percentage based on the asset class.
2. Increase the provision percentage by 10% for unsecured accounts with non-standard asset classes.
3. Calculate the provision amount based on the outstanding balance and provision percentage.
4. Ensure the provision amount does not exceed the outstanding balance.
5. Flag accounts for senior review if the provision amount exceeds 1,000,000.
6. Update the process run status to mark the process as completed and increment the run count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine ProvisionPct | `ProvisionPct` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Calculate provisioning percentage | `ProvisionPct` | Determine the provisioning percentage for accounts based on the asset class. |
| ⚠️ Update run status | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | Update the process run status to mark the process as completed and increment the run count. |

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

### R2 — Calculate provisioning percentage

**Affected Field:** `ProvisionPct`

**Summary:**

- Determine the provisioning percentage for accounts based on the asset class.

### Decision Logic

| Condition | Result |
|---|---|
| AssetClass = 'STANDARD' | 0.40 |
| AssetClass = 'SUBSTANDARD' | 15.00 |
| AssetClass = 'DOUBTFUL' | 25.00 |
| AssetClass = 'LOSS' | 100.00 |
| ELSE |  |

### R3 — Update run status

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `COMPLETED, ErrorDate, ErrorDescription, RunCount`

**Applies to:**

- Run status records in the RunStatus table

**Summary:**

- Update the process run status to mark the process as completed and increment the run count.

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

No explicit exception handling is defined in the provided extraction. If an error occurs during the provision percentage calculation, the run status is updated to indicate the error.

## Findings / Needs Review

- Lines 45-48 (ASSIGNMENT/CALCULATION) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 57-60 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
