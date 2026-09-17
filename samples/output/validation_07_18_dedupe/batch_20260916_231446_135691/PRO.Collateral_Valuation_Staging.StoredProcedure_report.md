# Collateral Valuation Staging — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Collateral_Valuation_Staging` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 7 |
| Tables read | 5 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

This procedure prepares collateral valuation data for review by inserting records into the PRO.CollateralReview table and updating the #CollateralStaging table.

## Process Flow

1. Create a temporary table #CollateralStaging to store account details and shortfall amounts.
2. Insert account details into #CollateralStaging for accounts with a secured flag and a valuation date within the last 12 months.
3. Calculate the shortfall amount for accounts where the outstanding balance exceeds the collateral value.
4. Update the ReviewPriority field in the #CollateralStaging table based on the ShortfallAmount.
5. Merge the data from the staging table #CollateralStaging into the PRO.CollateralPositionSummary table, updating existing records and inserting new records as necessary.
6. Insert records into the PRO.CollateralReview table for accounts with a positive shortfall amount from the staging table #CollateralStaging.
7. Read records from the #CollateralStaging table for accounts with a shortfall amount greater than zero.
8. Update the CollateralStale field in the PRO.LoanAccountCal table for secured loans that do not have a recent valuation.
9. Read the SecuredFlag, AccountId, and ValuationDate fields from the PRO.CollateralValuation table for secured loans that have a recent valuation.
10. Update the COMPLETED, ERRORDATE, ERRORDESCRIPTION, and COUNT fields in the PRO.ACLRUNNINGPROCESSSTATUS table to mark the Collateral Valuation Staging process as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Insert into CollateralReview | `AccountId, ReviewDate, ShortfallAmount` | Insert records into the PRO.CollateralReview table for accounts with a shortfall amount greater than zero. |
| Insert into #CollateralStaging | `AccountId, CollateralValue, OutstandingBalance, ShortfallAmount, ReviewPriority` | Not specified |
| Upsert collateralpositionsummary | `CollateralValue, ShortfallAmount, ReviewPriority, LastUpdatedDate, AccountId, FirstSeenDate` | Refresh existing rows and insert rows not already present. |
| Determine ReviewPriority | `ReviewPriority` | Not specified |
| Determine ReviewPriority (#CollateralStaging) | `ReviewPriority` | Not specified |
| Calculate shortfall amount | `ShortfallAmount` | Calculate the shortfall amount for accounts where the outstanding balance exceeds the collateral value. |
| Update collateral values | `CollateralValue, ShortfallAmount, ReviewPriority, LastUpdatedDate` | Update the collateral values and shortfall amounts in the PRO.CollateralPositionSummary table with the latest data from the staging table #… |

## Business Rules

### R1 — Insert into CollateralReview

**Affected Field:** `AccountId, ReviewDate, ShortfallAmount`

**Applies to:**

- ShortfallAmount > 0

**Summary:**

- Insert records into the PRO.CollateralReview table for accounts with a shortfall amount greater than zero.

### Decision Logic

| Condition | Result |
|---|---|
| ShortfallAmount > 0 | AccountId := AccountId; ReviewDate := @ProcessDate; ShortfallAmount := ShortfallAmount |


### R2 — Insert into #CollateralStaging

**Affected Field:** `AccountId, CollateralValue, OutstandingBalance, ShortfallAmount, ReviewPriority`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.SecuredFlag = 'Y' AND PRO.CollateralValuation.ValuationDate >= @StaleValuationCutoff | AccountId := PRO.LoanAccountCal.AccountId; CollateralValue := PRO.CollateralValuation.LatestValuationAmount; OutstandingBalance := PRO.LoanAccountCal.OutstandingBalance; ShortfallAmount := NULL; ReviewPriority := NULL |


### R3 — Upsert collateralpositionsummary

**Affected Field:** `CollateralValue, ShortfallAmount, ReviewPriority, LastUpdatedDate, AccountId, FirstSeenDate`

**Applies to:** eligibility not documented.

**Summary:**

- Refresh existing rows and insert rows not already present.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | #CollateralStaging.CollateralValue; #CollateralStaging.ShortfallAmount; #CollateralStaging.ReviewPriority; @ProcessDate |
| WHEN NOT MATCHED BY TARGET | #CollateralStaging.AccountId; #CollateralStaging.CollateralValue; #CollateralStaging.ShortfallAmount; #CollateralStaging.ReviewPriority; @ProcessDate |


### R4 — Determine ReviewPriority

**Affected Field:** `ReviewPriority`

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| DATEPART(MONTH, @ProcessDate) IN (3, 6, 9, 12) — applies to all rows (no additional filter) | (nested CASE — see separate decision table) |
| ELSE — applies to all rows (no additional filter) | (nested CASE — see separate decision table) |

### R5 — Determine ReviewPriority (#CollateralStaging)

**Affected Field:** `ReviewPriority`


**Source context:**

- IF DATEPART(MONTH, @ProcessDate) IN (3, 6, 9, 12) is true
- Target: #CollateralStaging
- FROM #CollateralStaging

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

### R6 — Calculate shortfall amount

**Affected Field:** `ShortfallAmount`

**Applies to:**

- Outstanding balance exceeds collateral value

**Summary:**

- Calculate the shortfall amount for accounts where the outstanding balance exceeds the collateral value.

### Decision Logic

| Condition | Result |
|---|---|
| #CollateralStaging.OutstandingBalance > #CollateralStaging.CollateralValue | #CollateralStaging.OutstandingBalance - #CollateralStaging.CollateralValue |


### R7 — Update collateral values

**Affected Field:** `CollateralValue, ShortfallAmount, ReviewPriority, LastUpdatedDate`

**Applies to:**

- The account ID in the staging table matches the account ID in the PRO.CollateralPositionSummary table.

**Summary:**

- Update the collateral values and shortfall amounts in the PRO.CollateralPositionSummary table with the latest data from the staging table #CollateralStaging.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.CollateralPositionSummary.AccountId = #CollateralStaging.AccountId | PRO.CollateralPositionSummary.CollateralValue = #CollateralStaging.CollateralValue, PRO.CollateralPositionSummary.ShortfallAmount = #CollateralStaging.ShortfallAmount, PRO.CollateralPositionSummary.ReviewPriority = #CollateralStaging.ReviewPriority, PRO.CollateralPositionSummary.LastUpdatedDate = @ProcessDate |

## Calculations

### Calculation — ShortfallAmount

**Expression:**

```sql
#CollateralStaging.OutstandingBalance - #CollateralStaging.CollateralValue
```

**Output:**
`#CollateralStaging.ShortfallAmount`

**Used By:**
READ #CollateralStaging; UPDATE #CollateralStaging

### Calculation — @StaleValuationCutoff

**Expression:**

```sql
DATEADD(MONTH, -12, @ProcessDate)
```

**Output:**
`Not specified`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.CollateralPositionSummary` | Read + Write | Provides: PRO.CollateralReview.CollateralValue, PRO.CollateralReview.ShortfallAmount, PRO.CollateralReview.ReviewPriority, PRO.CollateralReview.LastUpdatedDate, AccountId, FirstSeenDate |
| `PRO.CollateralReview` | Write | Inserts data into: AccountId, ReviewDate, ShortfallAmount |
| `PRO.LoanAccountCal` | Read + Write | Updates: PRO.LoanAccountCal.CollateralStale |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |
| `PRO.CollateralValuation` | Read | Provides: PRO.LoanAccountCal.SecuredFlag, PRO.CollateralValuation.AccountId, PRO.CollateralValuation.ValuationDate, 1 |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#CollateralStaging` | Read + Write | Inserts data into: AccountId, CollateralValue, OutstandingBalance, ShortfallAmount, ReviewPriority |

## Exception Handling

In case of an error, the Collateral Valuation Staging process is marked as failed.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
