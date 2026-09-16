# Interest Accrual Calculation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Interest_Accrual_Calculation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 3 confident, 3 needs review |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 3 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure calculates and records interest accruals for loan accounts based on the time elapsed since the last accrual, the outstanding balance, and the effective interest rate.

## Process Flow

1. Calculate the number of days since the last accrual for active accounts.
2. Adjust the effective interest rate for promotional accounts opened within the last 90 days.
3. Insert calculated accrual amounts and tiers into a staging table.
4. Merge the staging table data into the interest accrual ledger, updating existing records or inserting new ones.
5. Update the outstanding balance of accounts with accrued interest from the staging table.
6. Insert review cases for large accrual accounts into the collateral review table.
7. Update the process status to mark the interest accrual calculation as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine DaysSinceLastAccrual | `DaysSinceLastAccrual` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine EffectiveInterestRate | `EffectiveInterestRate` | Not specified |
| Determine AccrualTier | `AccrualTier` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| ⚠️ Insert Accrued Interest Amounts into Staging Table | `AccountId, AccruedInterestAmount, AccrualTier` | Insert calculated accrual amounts and tiers into a staging table for active accounts with non-null outstanding balances. |
| ⚠️ Merge Staging Table Data into Interest Accrual Ledger | `AccountId, AccruedInterestAmount, AccrualTier, LastAccrualDate` | Merge the staging table data into the interest accrual ledger, updating existing records or inserting new ones. |
| ⚠️ Update Outstanding Balance with Accrued Interest | `OutstandingBalance, LastAccrualDate` | Update the outstanding balance of accounts with accrued interest from the staging table. |

## Business Rules

### R1 — Determine DaysSinceLastAccrual

**Affected Field:** `DaysSinceLastAccrual`


**Applies to:**

- PRO.LoanAccountCal.AccountStatus = 'ACTIVE'

**Source context:**

- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.LastAccrualDate IS NULL | 1 |
| ELSE | DATEDIFF(DAY, PRO.LoanAccountCal.LastAccrualDate, @ProcessDate) |

### R2 — Determine EffectiveInterestRate

**Affected Field:** `EffectiveInterestRate`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| EXISTS (SELECT 1 FROM LoanAccountCal WHERE PromotionalFlag = 'Y' AND AccountOpenDate >= @PromoWindowStart) — row filter: AccountStatus = 'ACTIVE' AND PromotionalFlag = 'Y' AND AccountOpenDate >= @PromoWindowStart | BaseInterestRate - 0.02 |
| ELSE — row filter: AccountStatus = 'ACTIVE' | BaseInterestRate |


### R3 — Determine AccrualTier

**Affected Field:** `AccrualTier`


**Applies to:**

- PRO.LoanAccountCal.AccountStatus = 'ACTIVE' AND NOT PRO.LoanAccountCal.OutstandingBalance IS NULL

**Source context:**

- Target: #AccrualStaging
- FROM PRO.LoanAccountCal AS A
- Expression: CASE WHEN (A.OutstandingBalance * A.EffectiveInterestRate / 365) * A.DaysSinceLastAccrual > 5000 THEN 'LARGE' WHEN (A.OutstandingBalance * A.EffectiveInterestRate / 365) * A.DaysSinceLastAccrual > 1000 THEN 'MEDIUM' ELSE 'SMALL' END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| (PRO.LoanAccountCal.OutstandingBalance * PRO.LoanAccountCal.EffectiveInterestRate / 365) * PRO.LoanAccountCal.DaysSinceLastAccrual > 5000 | 'LARGE' |
| (PRO.LoanAccountCal.OutstandingBalance * PRO.LoanAccountCal.EffectiveInterestRate / 365) * PRO.LoanAccountCal.DaysSinceLastAccrual > 1000 | 'MEDIUM' |
| ELSE | 'SMALL' |

### R4 — Insert Accrued Interest Amounts into Staging Table

**Affected Field:** `AccountId, AccruedInterestAmount, AccrualTier`

**Summary:**

- Insert calculated accrual amounts and tiers into a staging table for active accounts with non-null outstanding balances.

### Decision Logic

| Condition | Result |
|---|---|
| (OutstandingBalance * EffectiveInterestRate / 365) * DaysSinceLastAccrual > 5000 | 'LARGE' |
| (OutstandingBalance * EffectiveInterestRate / 365) * DaysSinceLastAccrual > 1000 | 'MEDIUM' |
| ELSE | 'SMALL' |

### R5 — Merge Staging Table Data into Interest Accrual Ledger

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, AccruedInterestAmount, AccrualTier, LastAccrualDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge the staging table data into the interest accrual ledger, updating existing records or inserting new ones.


### R6 — Update Outstanding Balance with Accrued Interest

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `OutstandingBalance, LastAccrualDate`

**Applies to:**

- Join condition on AccountId

**Summary:**

- Update the outstanding balance of accounts with accrued interest from the staging table.

## Calculations

### Calculation — DaysSinceLastAccrual

**Expression:**

```sql
    (CASE
    WHEN LastAccrualDate IS NULL THEN 1
    ELSE DATEDIFF(DAY, LastAccrualDate, @ProcessDate)
END)
```

**Output:**
`PRO.LoanAccountCal.DaysSinceLastAccrual`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — EffectiveInterestRate

**Expression:**

```sql
BaseInterestRate - 0.02
```

**Output:**
`PRO.LoanAccountCal.EffectiveInterestRate`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — AccruedInterestAmount

**Expression:**

```sql
(OutstandingBalance * EffectiveInterestRate / 365) * DaysSinceLastAccrual
```

**Output:**
`#AccrualStaging.AccruedInterestAmount`

**Used By:**
INSERT INTO #AccrualStaging

### Calculation — AccrualTier

**Expression:**

```sql
CASE
    WHEN (OutstandingBalance * EffectiveInterestRate / 365) * DaysSinceLastAccrual > 5000 THEN 'LARGE'
    WHEN (OutstandingBalance * EffectiveInterestRate / 365) * DaysSinceLastAccrual > 1000 THEN 'MEDIUM'
    ELSE 'SMALL'
END
```

**Output:**
`#AccrualStaging.AccrualTier`

**Used By:**
INSERT INTO #AccrualStaging

### Calculation — OutstandingBalance

**Expression:**

```sql
OutstandingBalance + COALESCE(AccruedInterestAmount, 0)
```

**Output:**
`PRO.LoanAccountCal.OutstandingBalance`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS

### Calculation — DaysSinceLastAccrual

**Expression:**

```sql
    (CASE
    WHEN LastAccrualDate IS NULL THEN 1
    ELSE DATEDIFF(DAY, CAST(LastAccrualDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2))
END)
```

**Output:**
`DaysSinceLastAccrual`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: DaysSinceLastAccrual, EffectiveInterestRate, OutstandingBalance, LastAccrualDate |
| `PRO.InterestAccrualLedger` | Read + Write | Provides: Target.AccountId, Target.AccruedInterestAmount, Target.AccrualTier, Target.LastAccrualDate, FirstAccrualDate |
| `PRO.CollateralReview` | Write | Inserts data into: AccountId, ReviewDate, ShortfallAmount |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#AccrualStaging` | Read + Write | Inserts data into: AccountId, AccruedInterestAmount, AccrualTier |

## Exception Handling

If an error occurs during the execution of the procedure, the process status is updated to indicate failure, and the error date, description, and count are recorded.

## Findings / Needs Review

- Lines 119-121 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 126-128 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
