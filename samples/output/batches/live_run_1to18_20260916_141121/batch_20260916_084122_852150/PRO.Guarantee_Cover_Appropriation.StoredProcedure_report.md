# Guarantee Cover Appropriation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Guarantee_Cover_Appropriation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 10 |
| Tables read | 5 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

This procedure calculates and updates the appropriation of guarantee cover for loan accounts, ensuring that the available balance of the guarantee fund is adjusted accordingly and records are maintained for tracking and reporting purposes.

## Process Flow

1. Initialize variables with process date and available cover balance.
2. Update loan accounts to set cover request amount to null and cover shortfall flag to 'N' for accounts with a guarantee flag 'Y' and no provision amount.
3. Update loan accounts to set cover request amount to provision amount for accounts with a guarantee flag 'Y', a non-null provision amount, and a positive provision amount.
4. Check if the fund renewal date is within 7 days of the process date and update cover appropriation and shortfall flag for accounts with a guarantee flag 'Y' and a positive cover request amount.
5. If the available cover balance is greater than zero, update cover appropriation for accounts with a guarantee flag 'Y' and a positive cover request amount based on asset class.
6. If the available cover balance is not greater than zero, set cover appropriation to zero and cover shortfall flag to 'Y' for accounts with a guarantee flag 'Y' and a positive cover request amount.
7. Update net provision after cover for accounts with a guarantee flag 'Y'.
8. Create a temporary table to stage cover ledger data.
9. Insert data into the temporary cover ledger staging table from loan accounts with a guarantee flag 'Y' and a positive cover request amount.
10. Merge data from the temporary cover ledger staging table into the guarantee cover ledger table.
11. Insert records into the collections queue for accounts with a guarantee flag 'Y' and a cover shortfall flag 'Y'.
12. Update the guarantee fund's available balance and last appropriation date.
13. Update the running process status for the guarantee cover appropriation process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine CoverAppropriatedAmount | `CoverAppropriatedAmount` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Update CoverRequestedAmount | `CoverRequestedAmount` | Set the CoverRequestedAmount field based on specific conditions. |
| Update CoverShortfallFlag | `CoverShortfallFlag` | Set the CoverShortfallFlag field based on specific conditions. |
| Update CoverAppropriatedAmount | `CoverAppropriatedAmount` | Set the CoverAppropriatedAmount field based on specific conditions. |
| Update NetProvisionAfterCover | `NetProvisionAfterCover` | Set the NetProvisionAfterCover field based on specific conditions. |
| Set cover request to provision amount | `CoverRequestedAmount` | For accounts with a guarantee flag 'Y', a non-null provision amount, and a positive provision amount, the cover request amount is set to th… |
| Calculate cover appropriation based on asset class | `CoverAppropriatedAmount` | For accounts with a guarantee flag 'Y' and a positive cover request amount, calculate cover appropriation based on the asset class. |
| Calculate net provision after cover | `NetProvisionAfterCover` | For accounts with a guarantee flag 'Y', calculate the net provision after cover by subtracting the cover appropriated amount from the provi… |
| Stage cover ledger data | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Insert data into the temporary cover ledger staging table from loan accounts with a guarantee flag 'Y' and a positive cover request amount. |
| Merge cover ledger data | `Target.CoverAppropriatedAmount, Target.NetProvisionAfterCover, Target.LastAppropriationDate, Source.AccountId, Source.CoverAppropriatedAmount, Source.NetProvisionAfterCover, Source.FirstAppropriationDate, Source.LastAppropriationDate` | Merge data from the temporary cover ledger staging table into the guarantee cover ledger table, updating matched records and inserting new… |

## Business Rules

### R1 — Determine CoverAppropriatedAmount

**Affected Field:** `CoverAppropriatedAmount`


**Applies to:**

- GuaranteeCoveredFlag = 'Y' AND CoverRequestedAmount > 0

**Source context:**

- IF @AvailableCoverBalance IS NOT NULL AND @AvailableCoverBalance > 0 is true
- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal AS A
- Expression: CASE WHEN A.AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE WHEN A.CoverRequestedAmount <= @AvailableCoverBalance THEN A.CoverRequestedAmount ELSE @AvailableCoverBalance END WHEN A.AssetClass = 'SUBSTANDARD' THEN CASE WHEN A.CoverRequestedAmount <= @AvailableCoverBalance * 0.5 THEN A.CoverRequestedAmount ELSE @AvailableCoverBalance * 0.5 END ELSE 0 END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| (AssetClass IN ('DOUBTFUL', 'LOSS')) AND (CoverRequestedAmount <= @AvailableCoverBalance) | CoverRequestedAmount |
| AssetClass IN ('DOUBTFUL', 'LOSS') | @AvailableCoverBalance |
| (AssetClass = 'SUBSTANDARD') AND (CoverRequestedAmount <= @AvailableCoverBalance * 0.5) | CoverRequestedAmount |
| AssetClass = 'SUBSTANDARD' | @AvailableCoverBalance * 0.5 |
| ELSE | 0 |

### R2 — Update CoverRequestedAmount

**Affected Field:** `CoverRequestedAmount`

**Applies to:**

- CoverRequestedAmount is being updated

**Summary:**

- Set the CoverRequestedAmount field based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| CoverRequestedAmount condition | specific value |


### R3 — Update CoverShortfallFlag

**Affected Field:** `CoverShortfallFlag`

**Applies to:**

- CoverShortfallFlag is being updated

**Summary:**

- Set the CoverShortfallFlag field based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| CoverShortfallFlag condition | specific value |


### R4 — Update CoverAppropriatedAmount

**Affected Field:** `CoverAppropriatedAmount`

**Applies to:**

- CoverAppropriatedAmount is being updated

**Summary:**

- Set the CoverAppropriatedAmount field based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| CoverAppropriatedAmount condition | specific value |


### R5 — Update NetProvisionAfterCover

**Affected Field:** `NetProvisionAfterCover`

**Applies to:**

- NetProvisionAfterCover is being updated

**Summary:**

- Set the NetProvisionAfterCover field based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| NetProvisionAfterCover condition | specific value |


### R6 — Set cover request to provision amount

**Affected Field:** `CoverRequestedAmount`

**Applies to:**

- Account has a guarantee flag 'Y'
- Account has a non-null provision amount
- Account has a positive provision amount

**Summary:**

- For accounts with a guarantee flag 'Y', a non-null provision amount, and a positive provision amount, the cover request amount is set to the provision amount.


### R7 — Calculate cover appropriation based on asset class

**Affected Field:** `CoverAppropriatedAmount`

**Summary:**

- For accounts with a guarantee flag 'Y' and a positive cover request amount, calculate cover appropriation based on the asset class.

### Decision Logic

| Condition | Result |
|---|---|
| AssetClass IN ('DOUBTFUL', 'LOSS') | CASE WHEN CoverRequestedAmount <= @AvailableCoverBalance THEN CoverRequestedAmount ELSE @AvailableCoverBalance END |
| AssetClass = 'SUBSTANDARD' | CASE WHEN CoverRequestedAmount <= @AvailableCoverBalance * 0.5 THEN CoverRequestedAmount ELSE @AvailableCoverBalance * 0.5 END |
| ELSE | 0 |

### R8 — Calculate net provision after cover

**Affected Field:** `NetProvisionAfterCover`

**Applies to:**

- Account has a guarantee flag 'Y'

**Summary:**

- For accounts with a guarantee flag 'Y', calculate the net provision after cover by subtracting the cover appropriated amount from the provision amount.


### R9 — Stage cover ledger data

**Affected Field:** `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover`

**Applies to:**

- Account has a guarantee flag 'Y'
- Account has a positive cover request amount

**Summary:**

- Insert data into the temporary cover ledger staging table from loan accounts with a guarantee flag 'Y' and a positive cover request amount.


### R10 — Merge cover ledger data

**Affected Field:** `Target.CoverAppropriatedAmount, Target.NetProvisionAfterCover, Target.LastAppropriationDate, Source.AccountId, Source.CoverAppropriatedAmount, Source.NetProvisionAfterCover, Source.FirstAppropriationDate, Source.LastAppropriationDate`

**Applies to:**

- Temporary table record matches guarantee cover ledger record by AccountId

**Summary:**

- Merge data from the temporary cover ledger staging table into the guarantee cover ledger table, updating matched records and inserting new records.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | UPDATE SET Target.CoverAppropriatedAmount = Source.CoverAppropriatedAmount, Target.NetProvisionAfterCover = Source.NetProvisionAfterCover, Target.LastAppropriationDate = @ProcessDate |
| WHEN NOT MATCHED BY TARGET | INSERT (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover, FirstAppropriationDate, LastAppropriationDate) VALUES (Source.AccountId, Source.CoverAppropriatedAmount, Source.NetProvisionAfterCover, @ProcessDate, @ProcessDate) |

## Calculations

### Calculation — CoverAppropriatedAmount

**Expression:**

```sql
CASE
    WHEN AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE
    WHEN CoverRequestedAmount <= @AvailableCoverBalance THEN CoverRequestedAmount
    ELSE @AvailableCoverBalance
END
    WHEN AssetClass = 'SUBSTANDARD' THEN CASE
    WHEN CoverRequestedAmount <= @AvailableCoverBalance * 0.5 THEN CoverRequestedAmount
    ELSE @AvailableCoverBalance * 0.5
END
    ELSE 0
END
```

**Output:**
`PRO.LoanAccountCal.CoverAppropriatedAmount`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — NetProvisionAfterCover

**Expression:**

```sql
ProvisionAmount - COALESCE(CoverAppropriatedAmount, 0)
```

**Output:**
`PRO.LoanAccountCal.NetProvisionAfterCover`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — AvailableBalance

**Expression:**

```sql
@AvailableCoverBalance - (SELECT COALESCE(SUM(CoverAppropriatedAmount), 0) FROM LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y')
```

**Output:**
`PRO.GuaranteeFund.AvailableBalance`

**Used By:**
UPDATE PRO.GuaranteeFund; READ PRO.GuaranteeFund

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: CoverRequestedAmount, CoverShortfallFlag, CoverAppropriatedAmount, NetProvisionAfterCover |
| `PRO.GuaranteeCoverLedger` | Read + Write | Provides: Target.AccountId, Target.CoverAppropriatedAmount, Target.NetProvisionAfterCover, Target.LastAppropriationDate, FirstAppropriationDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.GuaranteeFund` | Read + Write | Updates: AvailableBalance, LastAppropriationDate |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#CoverLedgerStaging` | Write | Inserts data into: AccountId, CoverAppropriatedAmount, NetProvisionAfterCover |

## Exception Handling

If an exception occurs during the execution of the 'Guarantee_Cover_Appropriation' process, the procedure catches the exception and updates the ACLRUNNINGPROCESSSTATUS table to reflect the error.

## Findings / Needs Review

- Lines 148-150 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 155-157 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- The specific conditions and outcomes for updating CoverRequestedAmount, CoverShortfallFlag, CoverAppropriatedAmount, and NetProvisionAfterCover are not detailed in the extraction.
- 5 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
