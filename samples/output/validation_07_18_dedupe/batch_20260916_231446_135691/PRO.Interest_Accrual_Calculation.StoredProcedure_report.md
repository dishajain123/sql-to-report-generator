# Interest Accrual Calculation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Interest_Accrual_Calculation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 5 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

The procedure updates or inserts interest accrual data into the InterestAccrualLedger table based on the data in the #AccrualStaging table.

## Process Flow

1. Retrieve the process date from the SysDayMatrix table based on the provided TimeKey.
2. Calculate the number of days since the last accrual for active accounts.
3. Determine the effective interest rate for active accounts, applying a promotional rate reduction for eligible accounts.
4. Update the DaysSinceLastAccrual field in the PRO.LoanAccountCal.LoanAccountCal table for active accounts.
5. Update the effective interest rate for active accounts to match the base interest rate.
6. Drop the temporary accrual staging table if it already exists.
7. Create a new temporary accrual staging table.
8. Insert records into the accrual staging table with the account ID, calculated accrued interest amount, and accrual tier for active accounts with a non-null outstanding balance.
9. Merge data from the #AccrualStaging table into the PRO.LoanAccountCal.InterestAccrualLedger table.
10. For matching records, update the AccruedInterestAmount, AccrualTier, and LastAccrualDate fields in the PRO.LoanAccountCal.InterestAccrualLedger table.
11. Update the outstanding balance and last accrual date for loan accounts by adding the accrued interest amount from the staging table.
12. Insert records into the collateral review table for accounts with large accruals.
13. Update the process status to mark the interest accrual calculation as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Insert into CollateralReview | `AccountId, ReviewDate, ShortfallAmount` | Not specified |
| Determine DaysSinceLastAccrual | `DaysSinceLastAccrual` | Not specified |
| Determine EffectiveInterestRate | `EffectiveInterestRate` | Not specified |
| Determine AccrualTier | `AccrualTier` | Not specified |
| Upsert interestaccrualledger | `PRO.InterestAccrualLedger.AccruedInterestAmount, PRO.InterestAccrualLedger.AccrualTier, PRO.InterestAccrualLedger.LastAccrualDate, AccruedInterestAmount, AccrualTier, LastAccrualDate, AccountId, FirstAccrualDate` | Update the AccruedInterestAmount, AccrualTier, and LastAccrualDate fields for existing records in the InterestAccrualLedger table when a ma… |

## Business Rules

### R1 — Insert into CollateralReview

**Affected Field:** `AccountId, ReviewDate, ShortfallAmount`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| AccrualTier = 'LARGE' | AccountId := AccountId; ReviewDate := @ProcessDate; ShortfallAmount := AccruedInterestAmount |


### R2 — Determine DaysSinceLastAccrual

**Affected Field:** `DaysSinceLastAccrual`


**Applies to:**

- PRO.LoanAccountCal.LoanAccountCal.AccountStatus = 'ACTIVE'

**Source context:**

- Target: PRO.LoanAccountCal.LoanAccountCal
- FROM PRO.LoanAccountCal.LoanAccountCal

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| LastAccrualDate IS NULL | 1 |
| ELSE | DATEDIFF(DAY, LoanAccountCal.LastAccrualDate, @ProcessDate) |

### R3 — Determine EffectiveInterestRate

**Affected Field:** `EffectiveInterestRate`

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PromotionalFlag = 'Y' AND AccountOpenDate >= @PromoWindowStart) — row filter: PRO.LoanAccountCal.AccountStatus = 'ACTIVE' AND PRO.LoanAccountCal.PromotionalFlag = 'Y' AND PRO.LoanAccountCal.AccountOpenDate >= @PromoWindowStart | EffectiveInterestRate := PRO.LoanAccountCal.BaseInterestRate - 0.02; EffectiveInterestRate := PRO.LoanAccountCal.BaseInterestRate |
| ELSE — row filter: PRO.LoanAccountCal.AccountStatus = 'ACTIVE' | PRO.LoanAccountCal.BaseInterestRate |

### R4 — Determine AccrualTier

**Affected Field:** `AccrualTier`


**Applies to:**

- PRO.LoanAccountCal.AccountStatus = 'ACTIVE' AND NOT PRO.LoanAccountCal.OutstandingBalance IS NULL

**Source context:**

- Target: #AccrualStaging
- FROM PRO.LoanAccountCal
- Expression: CASE WHEN (PRO.LoanAccountCal.OutstandingBalance * PRO.LoanAccountCal.EffectiveInterestRate / 365) * PRO.LoanAccountCal.DaysSinceLastAccrual > 5000 THEN 'LARGE' WHEN (PRO.LoanAccountCal.OutstandingBalance * PRO.LoanAccountCal.EffectiveInterestRate / 365) * PRO.LoanAccountCal.DaysSinceLastAccrual > 1000 THEN 'MEDIUM' ELSE 'SMALL' END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| (OutstandingBalance * EffectiveInterestRate / 365) * DaysSinceLastAccrual > 5000 | 'LARGE' |
| (OutstandingBalance * EffectiveInterestRate / 365) * DaysSinceLastAccrual > 1000 | 'MEDIUM' |
| ELSE | 'SMALL' |

### R5 — Upsert interestaccrualledger

**Affected Field:** `PRO.InterestAccrualLedger.AccruedInterestAmount, PRO.InterestAccrualLedger.AccrualTier, PRO.InterestAccrualLedger.LastAccrualDate, AccruedInterestAmount, AccrualTier, LastAccrualDate, AccountId, FirstAccrualDate`

**Applies to:**

- Record exists in both PRO.InterestAccrualLedger and #AccrualStaging tables

**Summary:**

- Update the AccruedInterestAmount, AccrualTier, and LastAccrualDate fields for existing records in the InterestAccrualLedger table when a match is found in the #AccrualStaging table.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | #AccrualStaging.AccruedInterestAmount, #AccrualStaging.AccrualTier, @ProcessDate; #AccrualStaging.AccruedInterestAmount; #AccrualStaging.AccrualTier; @ProcessDate |
| WHEN NOT MATCHED BY TARGET | #AccrualStaging.AccountId, #AccrualStaging.AccruedInterestAmount, #AccrualStaging.AccrualTier, @ProcessDate, @ProcessDate |

## Calculations

### Calculation — DaysSinceLastAccrual

**Expression:**

```sql
    (CASE
    WHEN PRO.LoanAccountCal.LastAccrualDate IS NULL THEN 1
    ELSE DATEDIFF(DAY, PRO.LoanAccountCal.LastAccrualDate, @ProcessDate)
END)
```

**Output:**
`PRO.LoanAccountCal.DaysSinceLastAccrual`

**Used By:**
READ PRO.LoanAccountCal; UPDATE PRO.LoanAccountCal

### Calculation — EffectiveInterestRate

**Expression:**

```sql
    (CASE
    WHEN PRO.LoanAccountCal.PromotionalFlag = 'Y' AND PRO.LoanAccountCal.AccountOpenDate >= @PromoWindowStart THEN PRO.LoanAccountCal.BaseInterestRate - 0.02
    ELSE PRO.LoanAccountCal.BaseInterestRate
END)
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — AccruedInterestAmount

**Expression:**

```sql
(PRO.LoanAccountCal.OutstandingBalance * PRO.LoanAccountCal.EffectiveInterestRate / 365) * PRO.LoanAccountCal.DaysSinceLastAccrual
```

**Output:**
`#AccrualStaging.AccruedInterestAmount`

**Used By:**
INSERT INTO #AccrualStaging

### Calculation — AccrualTier

**Expression:**

```sql
CASE
    WHEN (PRO.LoanAccountCal.OutstandingBalance * PRO.LoanAccountCal.EffectiveInterestRate / 365) * PRO.LoanAccountCal.DaysSinceLastAccrual > 5000 THEN 'LARGE'
    WHEN (PRO.LoanAccountCal.OutstandingBalance * PRO.LoanAccountCal.EffectiveInterestRate / 365) * PRO.LoanAccountCal.DaysSinceLastAccrual > 1000 THEN 'MEDIUM'
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
PRO.LoanAccountCal.OutstandingBalance + ISNULL(#AccrualStaging.AccruedInterestAmount, 0)
```

**Output:**
`PRO.LoanAccountCal.OutstandingBalance`

**Used By:**
READ PRO.LoanAccountCal

### Calculation — DaysSinceLastAccrual

**Expression:**

```sql
    (CASE
    WHEN PRO.LoanAccountCal.LastAccrualDate IS NULL THEN 1
    ELSE DATEDIFF(DAY, CAST(PRO.LoanAccountCal.LastAccrualDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2))
END)
```

**Output:**
`DaysSinceLastAccrual`

**Used By:**
Not specified

### Calculation — EffectiveInterestRate

**Expression:**

```sql
PRO.LoanAccountCal.BaseInterestRate - 0.02
```

**Output:**
`EffectiveInterestRate`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: PRO.LoanAccountCal.DaysSinceLastAccrual, PRO.LoanAccountCal.EffectiveInterestRate, PRO.LoanAccountCal.OutstandingBalance, PRO.LoanAccountCal.LastAccrualDate |
| `PRO.InterestAccrualLedger` | Read + Write | Provides: PRO.CollateralReview.AccruedInterestAmount, PRO.CollateralReview.AccrualTier, PRO.CollateralReview.LastAccrualDate, AccountId, FirstAccrualDate |
| `PRO.CollateralReview` | Write | Inserts data into: AccountId, ReviewDate, ShortfallAmount |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#AccrualStaging` | Read + Write | Inserts data into: AccountId, AccruedInterestAmount, AccrualTier |

## Exception Handling

If an error occurs during the interest accrual calculation, the process status is updated to indicate failure and the error details are logged.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
