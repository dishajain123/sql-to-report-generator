# Interest Accrual Calculation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Interest_Accrual_Calculation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 12 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

The procedure calculates and records interest accruals for loan accounts based on the time elapsed since the last accrual, the outstanding balance, and the effective interest rate.

## Process Flow

1. Calculate the number of days since the last accrual for active accounts.
2. Adjust the effective interest rate for promotional accounts opened within a specified window.
3. Calculate the accrued interest amount for active accounts with outstanding balances.
4. Classify the accrual amount into tiers based on its size.
5. Insert the calculated accruals into a staging table.
6. Update the outstanding balance of accounts with accrued interest from the staging table.
7. Insert a record into the interest accrual ledger by merging with existing records.
8. Insert a review case for accounts with large accruals into the collateral review table.
9. Update the process status to mark the interest accrual calculation as completed.
10. On failure, update the process status to indicate an error and log the error message.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Update Outstanding Balance with Accrued Interest [1] | `OutstandingBalance` | Update the outstanding balance of accounts with accrued interest from the staging table. |
| Calculate Accrued Interest Amount [2] | `AccruedInterestAmount` | Calculate the accrued interest amount for active accounts with a non-null outstanding balance. |
| Log Review Case for Large Accruals | `AccountId, ReviewDate, ShortfallAmount` | Log a review case for every large-accrual account, read back from the staging table populated above. |
| Determine DaysSinceLastAccrual | `DaysSinceLastAccrual` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine EffectiveInterestRate | `EffectiveInterestRate` | Not specified |
| Calculate Accrued Interest Amount [3] | `AccruedInterestAmount` | Calculate the accrued interest amount for active accounts with a non-null outstanding balance. |
| Update Outstanding Balance with Accrued Interest [2] | `OutstandingBalance, LastAccrualDate` | Update the outstanding balance of accounts with accrued interest and set the last accrual date. |
| Merge Accrual Data into Ledger | `InterestAccrualLedger` | Merge the accrual data from the staging table into the interest accrual ledger. |
| Merge Staging Table into Interest Accrual Ledger | `AccountId, AccruedInterestAmount, AccrualTier, LastAccrualDate` | Merge the staging table data into the interest accrual ledger, updating existing records and inserting new ones. |
| Update Outstanding Balance with Accrued Interest [3] | `OutstandingBalance` | Update the outstanding balance of accounts with accrued interest from the staging table. |
| Insert Interest Accrual Ledger Record | `Not specified` | Insert a record into the interest accrual ledger by merging with existing records. |
| Insert Collateral Review Case | `Not specified` | Insert a review case for accounts with large accruals into the collateral review table. |

## Business Rules

### R1 — Update Outstanding Balance with Accrued Interest [1]

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Account status is active
- Outstanding balance is not null

**Summary:**

- Update the outstanding balance of accounts with accrued interest from the staging table.


### R2 — Calculate Accrued Interest Amount [2]

**Affected Field:** `AccruedInterestAmount`

**Applies to:**

- Account status is active
- Outstanding balance is not null

**Summary:**

- Calculate the accrued interest amount for active accounts with a non-null outstanding balance.


### R3 — Log Review Case for Large Accruals

**Affected Field:** `AccountId, ReviewDate, ShortfallAmount`

**Applies to:**

- Accrual tier is large

**Summary:**

- Log a review case for every large-accrual account, read back from the staging table populated above.


### R4 — Determine DaysSinceLastAccrual

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

### R5 — Determine EffectiveInterestRate

**Affected Field:** `EffectiveInterestRate`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| EXISTS (SELECT 1 FROM LoanAccountCal WHERE PromotionalFlag = 'Y' AND AccountOpenDate >= @PromoWindowStart) — row filter: AccountStatus = 'ACTIVE' AND PromotionalFlag = 'Y' AND AccountOpenDate >= @PromoWindowStart | BaseInterestRate - 0.02 |
| ELSE — row filter: AccountStatus = 'ACTIVE' | BaseInterestRate |


### R6 — Calculate Accrued Interest Amount [3]

**Affected Field:** `AccruedInterestAmount`

**Applies to:**

- Account status is active
- Outstanding balance is not null

**Summary:**

- Calculate the accrued interest amount for active accounts with a non-null outstanding balance.


### R7 — Update Outstanding Balance with Accrued Interest [2]

**Affected Field:** `OutstandingBalance, LastAccrualDate`

**Applies to:**

- Account status is active
- Outstanding balance is not null

**Summary:**

- Update the outstanding balance of accounts with accrued interest and set the last accrual date.


### R8 — Merge Accrual Data into Ledger

**Affected Field:** `InterestAccrualLedger`

**Applies to:** eligibility not documented.

**Summary:**

- Merge the accrual data from the staging table into the interest accrual ledger.


### R9 — Merge Staging Table into Interest Accrual Ledger

**Affected Field:** `AccountId, AccruedInterestAmount, AccrualTier, LastAccrualDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge the staging table data into the interest accrual ledger, updating existing records and inserting new ones.


### R10 — Update Outstanding Balance with Accrued Interest [3]

**Affected Field:** `OutstandingBalance`

**Applies to:**

- Account ID matches between staging and loan account tables

**Summary:**

- Update the outstanding balance of accounts with accrued interest from the staging table.


### R11 — Insert Interest Accrual Ledger Record

**Affected Field:** Not specified

**Applies to:**

- Account ID matches between target and source tables

**Summary:**

- Insert a record into the interest accrual ledger by merging with existing records.


### R12 — Insert Collateral Review Case

**Affected Field:** Not specified

**Applies to:**

- Accrual tier is large

**Summary:**

- Insert a review case for accounts with large accruals into the collateral review table.

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

### Calculation — (A.OutstandingBalance * A.EffectiveInterestRate / 365) * A.DaysSinceLastAccrual

**Expression:**

```sql
(OutstandingBalance * EffectiveInterestRate / 365) * DaysSinceLastAccrual
```

**Output:**
`#AccrualStaging.AccruedInterestAmount`

**Used By:**
INSERT INTO #AccrualStaging

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

On failure, the process status is updated to indicate an error, the error date is set to the current date, the error description is set to the error message, and the count is incremented.

## Findings / Needs Review

- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
