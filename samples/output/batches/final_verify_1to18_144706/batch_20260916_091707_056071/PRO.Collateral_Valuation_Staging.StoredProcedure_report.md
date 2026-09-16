# Collateral Valuation Staging — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Collateral_Valuation_Staging` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 10 |
| Tables read | 5 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

This procedure calculates and updates collateral shortfall amounts and review priorities for accounts based on their outstanding balance and collateral value, and merges these updates into the collateral position summary.

## Process Flow

1. Initialize the process date and stale valuation cutoff date.
2. Create a temporary table to stage collateral data.
3. Insert account data into the temporary table.
4. Calculate the shortfall amount for accounts with an outstanding balance greater than the collateral value.
5. Calculate the shortfall amount as zero for accounts with an outstanding balance less than or equal to the collateral value.
6. Update the review priority for accounts with a shortfall amount greater than zero.
7. Update the review priority for accounts with a shortfall amount of zero.
8. Merge the temporary table data into the collateral position summary table.
9. Insert data into the collateral review table.
10. Update the loan account calendar table to mark collateral as stale if no recent valuation exists.
11. Update the process status table to mark the collateral valuation staging process as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Update shortfall amount | `ShortfallAmount` | Update the ShortfallAmount in the #CollateralStaging table based on certain conditions. |
| Read data for processing | `AccountId, @ProcessDate, ShortfallAmount` | Read data from the #CollateralStaging table for further processing. |
| Calculate shortfall amount | `ShortfallAmount` | Determine the shortfall amount for accounts with an outstanding balance greater than the collateral value. |
| Set shortfall amount to zero | `ShortfallAmount` | Set the shortfall amount to zero for accounts with an outstanding balance less than or equal to the collateral value. |
| Determine ReviewPriority (#CollateralStaging) [1] | `ReviewPriority` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine ReviewPriority (#CollateralStaging) [2] | `ReviewPriority` | First matching row wins; ELSE includes false or NULL predicates. |
| Mark collateral as stale | `CollateralStale` | Mark collateral as stale if no recent valuation exists for the account. |
| Update collateral stale status | `CollateralStale` | Mark collateral as stale if there is no recent valuation. |
| Read shortfall and account details | `AccountId, @ProcessDate, ShortfallAmount` | Read shortfall amounts and account IDs from the #CollateralStaging table for further processing. |
| Merge collateral position summaries | `Target.AccountId, Source.AccountId, Target.CollateralValue, Source.CollateralValue, Target.ShortfallAmount, Source.ShortfallAmount, Target.ReviewPriority, Source.ReviewPriority, Target.LastUpdatedDate, AccountId, CollateralValue, ShortfallAmount, ReviewPriority, FirstSeenDate, LastUpdatedDate` | Merge collateral position summaries. |

## Business Rules

### R1 — Update shortfall amount

**Affected Field:** `ShortfallAmount`

**Applies to:** eligibility not documented.

**Summary:**

- Update the ShortfallAmount in the #CollateralStaging table based on certain conditions.

### Decision Logic

| Condition | Result |
|---|---|
| Condition 1 | Value 1 |
| Condition 2 | Value 2 |


### R2 — Read data for processing

**Affected Field:** `AccountId, @ProcessDate, ShortfallAmount`

**Applies to:** eligibility not documented.

**Summary:**

- Read data from the #CollateralStaging table for further processing.


### R3 — Calculate shortfall amount

_Note: Also extracted with additional fields attached in another pass (S.ShortfallAmount) - kept the narrower, consistent version of this rule._

**Affected Field:** `ShortfallAmount`

**Applies to:**

- Account has an outstanding balance greater than the collateral value

**Summary:**

- Determine the shortfall amount for accounts with an outstanding balance greater than the collateral value.

### Decision Logic

| Condition | Result |
|---|---|
| OutstandingBalance > CollateralValue | OutstandingBalance - CollateralValue |


### R4 — Set shortfall amount to zero

_Note: Also extracted with additional fields attached in another pass (S.ShortfallAmount) - kept the narrower, consistent version of this rule._

**Affected Field:** `ShortfallAmount`

**Applies to:**

- Account has an outstanding balance less than or equal to the collateral value

**Summary:**

- Set the shortfall amount to zero for accounts with an outstanding balance less than or equal to the collateral value.

### Decision Logic

| Condition | Result |
|---|---|
| OutstandingBalance <= CollateralValue | 0 |


### R5 — Determine ReviewPriority (#CollateralStaging) [1]

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

### R6 — Determine ReviewPriority (#CollateralStaging) [2]

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

### R7 — Mark collateral as stale

**Affected Field:** `CollateralStale`

**Applies to:**

- Account is secured and has no recent valuation

**Summary:**

- Mark collateral as stale if no recent valuation exists for the account.


### R8 — Update collateral stale status

**Affected Field:** `CollateralStale`

**Applies to:**

- Account is secured and has no recent valuation

**Summary:**

- Mark collateral as stale if there is no recent valuation.


### R9 — Read shortfall and account details

**Affected Field:** `AccountId, @ProcessDate, ShortfallAmount`

**Applies to:** eligibility not documented.

**Summary:**

- Read shortfall amounts and account IDs from the #CollateralStaging table for further processing.


### R10 — Merge collateral position summaries

**Affected Field:** `Target.AccountId, Source.AccountId, Target.CollateralValue, Source.CollateralValue, Target.ShortfallAmount, Source.ShortfallAmount, Target.ReviewPriority, Source.ReviewPriority, Target.LastUpdatedDate, AccountId, CollateralValue, ShortfallAmount, ReviewPriority, FirstSeenDate, LastUpdatedDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge collateral position summaries.

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

The procedure uses a TRY-CATCH block to handle any exceptions that may occur during execution. If an exception occurs during the execution of the 'Collateral_Valuation_Staging' process, the procedure updates the process status to indicate it is incomplete, records the error date, captures the error description, and increments the error count.

## Findings / Needs Review

- Lines 26-26 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 111-114 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
