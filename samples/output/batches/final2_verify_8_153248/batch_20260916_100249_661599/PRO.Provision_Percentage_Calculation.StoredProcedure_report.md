# Provision Percentage Calculation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Percentage_Calculation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 5 |
| Tables read | 2 |
| Tables written | 2 |
| Produces audit trail | Not detected |

## What This Does

The procedure calculates and updates the provision percentage and amount for accounts based on their asset class and outstanding balance, ensuring compliance with regulatory thresholds.

## Process Flow

1. Update the provision percentage for unsecured accounts with a non-standard asset class.
2. Calculate the provision amount based on the outstanding balance and provision percentage.
3. Ensure the provision amount does not exceed the outstanding balance.
4. Set a senior review flag for accounts with a provision amount over 1 million.
5. Update the process run status to mark the process as completed and increment the run count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine Provision Percentage (ProvisionPct) | `ProvisionPct` | Set the provision percentage for accounts based on their asset class. |
| Determine Provision Percentage (A.ProvisionPct) | `ProvisionPct` | Set the provision percentage for accounts based on their asset class. |
| Limit provision amount | `ProvisionAmount` | The provision amount is capped at the outstanding balance if it exceeds it. |
| Set senior review flag | `SeniorReviewFlag` | A senior review flag is set for accounts with a provision amount over 1 million. |
| Update run status | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | The process run status is updated to mark the process as completed and increment the run count. |

## Business Rules

### R1 — Determine Provision Percentage (ProvisionPct)

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

### R2 — Determine Provision Percentage (A.ProvisionPct)

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

### R3 — Limit provision amount

**Affected Field:** `ProvisionAmount`

**Applies to:**

- Provision amount exceeds outstanding balance

**Summary:**

- The provision amount is capped at the outstanding balance if it exceeds it.

### Decision Logic

| Condition | Result |
|---|---|
| ProvisionAmount > OutstandingBalance | OutstandingBalance |


### R4 — Set senior review flag

**Affected Field:** `SeniorReviewFlag`

**Applies to:**

- Provision amount exceeds 1 million

**Summary:**

- A senior review flag is set for accounts with a provision amount over 1 million.

### Decision Logic

| Condition | Result |
|---|---|
| ProvisionAmount > 1000000 | 'Y' |


### R5 — Update run status

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- Process name matches 'Provision_Percentage_Calculation'

**Summary:**

- The process run status is updated to mark the process as completed and increment the run count.

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


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AccountCal` | Read + Write | Updates: ProvisionPct, ProvisionAmount, SeniorReviewFlag |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |

## Exception Handling

If an error occurs during the provision percentage calculation, the run status is updated to reflect the error.

## Findings / Needs Review

- Lines 45-48 (ASSIGNMENT/CALCULATION) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 57-60 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The provision percentage calculation logic is not provided in the extraction, leading to an assumption that it is handled elsewhere.
- 2 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
