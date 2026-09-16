# Collateral Valuation Staging — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Collateral_Valuation_Staging` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 2 confident, 6 needs review |
| Tables read | 5 |
| Tables written | 4 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 6 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure Collateral_Valuation_Staging processes collateral valuation data for a specific time key, updating various fields in the #CollateralStaging table based on certain conditions.

## Process Flow

1. Initialize temporary staging table with account collateral data.
2. Calculate shortfall amounts for accounts with outstanding balances greater than collateral values.
3. Set shortfall amounts to zero for accounts with adequate collateral.
4. Assign review priorities based on shortfall amounts and month of process date.
5. Merge updated collateral data into the collateral position summary table.
6. Insert records into the collateral review table for accounts with positive shortfalls.
7. Mark loan accounts as stale if they lack recent collateral valuations.
8. Update the process status table to mark the collateral valuation staging process as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Insert collateral review data | `AccountId, ReviewDate, ShortfallAmount` | Insert collateral review data into the collateral review table. |
| Determine ReviewPriority (#CollateralStaging) [1] | `ReviewPriority` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine ReviewPriority (#CollateralStaging) [2] | `ReviewPriority` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Calculate shortfall amount | `ShortfallAmount` | Calculate shortfall amounts for accounts with outstanding balances greater than collateral values. |
| ⚠️ Set shortfall to zero | `ShortfallAmount` | Set shortfall amounts to zero for accounts with adequate collateral. |
| ⚠️ Assign review priority | `ReviewPriority` | Assign review priorities based on shortfall amounts and month of process date. |
| ⚠️ Merge collateral position summary | `CollateralValue, ShortfallAmount, ReviewPriority, LastUpdatedDate` | Merge updated collateral data into the collateral position summary table. |
| ⚠️ Mark accounts as stale | `CollateralStale` | Mark loan accounts as stale if they lack recent collateral valuations. |

## Business Rules

### R1 — Insert collateral review data

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, ReviewDate, ShortfallAmount`

**Applies to:**

- ShortfallAmount > 0

**Summary:**

- Insert collateral review data into the collateral review table.


### R2 — Determine ReviewPriority (#CollateralStaging) [1]

**Affected Field:** `ReviewPriority`


**Source context:**

- IF DATEPART(MONTH, @ProcessDate) IN (3, 6, 9, 12) is true
- Target: #CollateralStaging
- FROM #CollateralStaging AS S

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| ShortfallAmount IS NULL | 'NONE' |
| ShortfallAmount > 500000 | 'URGENT' |
| ShortfallAmount > 100000 | 'HIGH' |
| ShortfallAmount > 0 | 'STANDARD' |
| ELSE | 'NONE' |

### R3 — Determine ReviewPriority (#CollateralStaging) [2]

**Affected Field:** `ReviewPriority`


**Source context:**

- ELSE of IF DATEPART(MONTH, @ProcessDate) IN (3, 6, 9, 12) (false or NULL)
- Target: #CollateralStaging
- FROM #CollateralStaging AS S

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| ShortfallAmount > 500000 | 'HIGH' |
| ShortfallAmount > 0 | 'STANDARD' |
| ELSE | 'NONE' |

### R4 — Calculate shortfall amount

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `ShortfallAmount`

**Applies to:** eligibility not documented.

**Summary:**

- Calculate shortfall amounts for accounts with outstanding balances greater than collateral values.

### Decision Logic

| Condition | Result |
|---|---|
| OutstandingBalance > CollateralValue | OutstandingBalance - CollateralValue |


### R5 — Set shortfall to zero

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `ShortfallAmount`

**Applies to:** eligibility not documented.

**Summary:**

- Set shortfall amounts to zero for accounts with adequate collateral.

### Decision Logic

| Condition | Result |
|---|---|
| OutstandingBalance <= CollateralValue | 0 |


### R6 — Assign review priority

**Affected Field:** `ReviewPriority`

**Summary:**

- Assign review priorities based on shortfall amounts and month of process date.

### Decision Logic

| Condition | Result |
|---|---|
| DATEPART(MONTH, @ProcessDate) IN (3, 6, 9, 12) AND ShortfallAmount IS NULL | 'NONE' |
| DATEPART(MONTH, @ProcessDate) IN (3, 6, 9, 12) AND ShortfallAmount > 500000 | 'URGENT' |
| DATEPART(MONTH, @ProcessDate) IN (3, 6, 9, 12) AND ShortfallAmount > 100000 | 'HIGH' |
| DATEPART(MONTH, @ProcessDate) IN (3, 6, 9, 12) AND ShortfallAmount > 0 | 'STANDARD' |
| DATEPART(MONTH, @ProcessDate) NOT IN (3, 6, 9, 12) AND ShortfallAmount > 500000 | 'HIGH' |
| DATEPART(MONTH, @ProcessDate) NOT IN (3, 6, 9, 12) AND ShortfallAmount > 0 | 'STANDARD' |

### R7 — Merge collateral position summary

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `CollateralValue, ShortfallAmount, ReviewPriority, LastUpdatedDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge updated collateral data into the collateral position summary table.


### R8 — Mark accounts as stale

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `CollateralStale`

**Applies to:** eligibility not documented.

**Summary:**

- Mark loan accounts as stale if they lack recent collateral valuations.

## Calculations

### Calculation — ShortfallAmount

**Expression:**

```sql
OutstandingBalance - CollateralValue
```

**Output:**
`#CollateralStaging.ShortfallAmount`

**Used By:**
UPDATE #CollateralStaging; READ #CollateralStaging

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`COUNT`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.CollateralPositionSummary` | Read + Write | Provides: Target.AccountId, Target.CollateralValue, Target.ShortfallAmount, Target.ReviewPriority, Target.LastUpdatedDate, FirstSeenDate |
| `PRO.CollateralReview` | Write | Inserts data into: AccountId, ReviewDate, ShortfallAmount |
| `PRO.LoanAccountCal` | Read + Write | Updates: CollateralStale |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |
| `PRO.CollateralValuation` | Read | Provides: SecuredFlag, AccountId, ValuationDate, 1 |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#CollateralStaging` | Read + Write | Inserts data into: AccountId, CollateralValue, OutstandingBalance, ShortfallAmount, ReviewPriority |

## Exception Handling

The procedure uses a TRY-CATCH block to handle exceptions, but no specific exception handling steps are defined in the source. If an exception occurs during the execution of the 'Collateral_Valuation_Staging' process, the procedure updates the process status to indicate it is incomplete, records the error date, captures the error description, and increments the error count.

## Findings / Needs Review

- Lines 26-26 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 111-114 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 129-131 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 136-138 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
