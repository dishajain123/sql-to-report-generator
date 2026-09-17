# Guarantee Cover Appropriation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Guarantee_Cover_Appropriation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 8 |
| Tables read | 5 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

This procedure updates the Guarantee Cover Ledger with appropriated amounts and dates, inserts records into the Collections Queue for accounts with guarantee cover shortfalls, and reads from the Loan Account Calendar to identify accounts needing coverage. This procedure also writes to: CollectionsQueue, CoverLedgerStaging, GuaranteeCoverLedger, GuaranteeFund, LoanAccountCal.

## Process Flow

1. Read the current date from the SysDayMatrix table using the provided TimeKey.
2. Read the available cover balance and renewal date from the GuaranteeFund table for the fund with ID 'GOVT_CGF'.
3. Update the CoverRequestedAmount and CoverShortfallFlag fields in the LoanAccountCal table for accounts with GuaranteeCoveredFlag set to 'Y' and a NULL ProvisionAmount.
4. Update the CoverRequestedAmount, CoverShortfallFlag, and CoverAppropriatedAmount fields in the PRO.LoanAccountCal.LoanAccountCal table for accounts with guarantee cover flagged as 'Y' and specific provisioning conditions.
5. Update the CoverAppropriatedAmount for loan accounts with a GuaranteeCoveredFlag of 'Y' and a CoverRequestedAmount greater than 0, based on the asset class and requested cover amount.
6. Reset the CoverAppropriatedAmount to zero and set the CoverShortfallFlag to 'Y' for loan accounts with a guarantee cover where the cover requested amount is greater than zero.
7. Update the NetProvisionAfterCover for loan accounts with a guarantee cover by subtracting the CoverAppropriatedAmount from the ProvisionAmount.
8. Drop the temporary table #CoverLedgerStaging if it exists.
9. Insert the AccountId, CoverAppropriatedAmount, and NetProvisionAfterCover into the temporary table #CoverLedgerStaging for loan accounts with a guarantee cover where the cover requested amount is greater than zero.
10. Merge data from the staging table into the Guarantee Cover Ledger, updating existing records or inserting new ones.
11. Insert records into the Collections Queue for accounts that have been guaranteed and have a shortfall, flagging them for escalation.
12. Read from the Loan Account Calendar to identify accounts that have been guaranteed and have a shortfall, preparing for further processing.
13. Update the AvailableBalance and LastAppropriationDate of the government guarantee fund based on the sum of CoverAppropriatedAmount from the LoanAccountCal table where GuaranteeCoveredFlag is 'Y'.
14. Update the status of the Guarantee_Cover_Appropriation process in the ACLRUNNINGPROCESSSTATUS table to mark it as completed, reset error details, and increment the process count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Insert into #CoverLedgerStaging | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Not specified |
| Determine AvailableBalance | `AvailableBalance` | Not specified |
| Insert unmatched records | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover, FirstAppropriationDate, LastAppropriationDate` | Not specified |
| Determine CoverAppropriatedAmount, CoverShortfallFlag | `CoverAppropriatedAmount, CoverShortfallFlag` | Not specified |
| Determine CoverAppropriatedAmount | `CoverAppropriatedAmount` | Not specified |
| Set CoverRequestedAmount to ProvisionAmount | `CoverRequestedAmount` | For accounts with GuaranteeCoveredFlag set to 'Y', a non-NULL ProvisionAmount greater than 0, set CoverRequestedAmount to ProvisionAmount. |
| Calculate net provision after cover | `NetProvisionAfterCover` | For loan accounts with a guarantee cover, the NetProvisionAfterCover is calculated by subtracting the CoverAppropriatedAmount from the Prov… |
| Update Guarantee Cover Ledger | `GuaranteeCoverLedger, CoverAppropriatedAmount, NetProvisionAfterCover, LastAppropriationDate` | Update the Guarantee Cover Ledger with the appropriated amount, net provision after cover, and the last appropriation date. |

## Business Rules

### R1 — Insert into #CoverLedgerStaging

**Affected Field:** `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| GuaranteeCoveredFlag = 'Y' AND CoverRequestedAmount > 0 | AccountId := AccountId; CoverAppropriatedAmount := CoverAppropriatedAmount; NetProvisionAfterCover := NetProvisionAfterCover |


### R2 — Determine AvailableBalance

**Affected Field:** `AvailableBalance`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| FundId = 'GOVT_CGF' | @AvailableCoverBalance - (SELECT COALESCE(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal.LoanAccountCal.LoanAccountCal.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y') |


### R3 — Insert unmatched records

**Affected Field:** `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover, FirstAppropriationDate, LastAppropriationDate`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN NOT MATCHED BY TARGET | #CoverLedgerStaging.AccountId; #CoverLedgerStaging.CoverAppropriatedAmount; #CoverLedgerStaging.NetProvisionAfterCover; @ProcessDate |


### R4 — Determine CoverAppropriatedAmount, CoverShortfallFlag

**Affected Field:** `CoverAppropriatedAmount, CoverShortfallFlag`

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| @FundRenewalDate IS NOT NULL AND @ProcessDate >= DATEADD(DAY, -7, @FundRenewalDate) — row filter: PRO.LoanAccountCal.GuaranteeCoveredFlag = 'Y' AND PRO.LoanAccountCal.CoverRequestedAmount > 0 | CoverAppropriatedAmount := 0; CoverShortfallFlag := 'Y' |
| @AvailableCoverBalance IS NOT NULL AND @AvailableCoverBalance > 0 — row filter: PRO.LoanAccountCal.GuaranteeCoveredFlag = 'Y' AND PRO.LoanAccountCal.CoverRequestedAmount > 0 | CoverAppropriatedAmount := (nested CASE — see separate decision table) |
| ELSE — row filter: PRO.LoanAccountCal.GuaranteeCoveredFlag = 'Y' AND PRO.LoanAccountCal.CoverRequestedAmount > 0 | CoverAppropriatedAmount := 0; CoverShortfallFlag := 'Y' |

### R5 — Determine CoverAppropriatedAmount

**Affected Field:** `CoverAppropriatedAmount`


**Applies to:**

- PRO.LoanAccountCal.LoanAccountCal.GuaranteeCoveredFlag = 'Y' AND PRO.LoanAccountCal.LoanAccountCal.CoverRequestedAmount > 0

**Source context:**

- IF @AvailableCoverBalance IS NOT NULL AND @AvailableCoverBalance > 0 is true
- Target: PRO.LoanAccountCal.LoanAccountCal.LoanAccountCal
- FROM PRO.LoanAccountCal.LoanAccountCal.LoanAccountCal
- Expression: CASE WHEN PRO.LoanAccountCal.LoanAccountCal.AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE WHEN PRO.LoanAccountCal.LoanAccountCal.CoverRequestedAmount <= @AvailableCoverBalance THEN PRO.LoanAccountCal.LoanAccountCal.CoverRequestedAmount ELSE @AvailableCoverBalance END WHEN PRO.LoanAccountCal.LoanAccountCal.AssetClass = 'SUBSTANDARD' THEN CASE WHEN PRO.LoanAccountCal.LoanAccountCal.CoverRequestedAmount <= @AvailableCoverBalance * 0.5 THEN PRO.LoanAccountCal.LoanAccountCal.CoverRequestedAmount ELSE @AvailableCoverBalance * 0.5 END ELSE 0 END

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

### R6 — Set CoverRequestedAmount to ProvisionAmount

**Affected Field:** `CoverRequestedAmount`

**Applies to:**

- Account has GuaranteeCoveredFlag set to 'Y'
- Account has a non-NULL ProvisionAmount greater than 0

**Summary:**

- For accounts with GuaranteeCoveredFlag set to 'Y', a non-NULL ProvisionAmount greater than 0, set CoverRequestedAmount to ProvisionAmount.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.LoanAccountCal.GuaranteeCoveredFlag = 'Y' AND PRO.LoanAccountCal.LoanAccountCal.ProvisionAmount IS NOT NULL AND PRO.LoanAccountCal.LoanAccountCal.ProvisionAmount > 0 | PRO.LoanAccountCal.LoanAccountCal.ProvisionAmount |


### R7 — Calculate net provision after cover

**Affected Field:** `NetProvisionAfterCover`

**Applies to:**

- Loan account has a guarantee cover

**Summary:**

- For loan accounts with a guarantee cover, the NetProvisionAfterCover is calculated by subtracting the CoverAppropriatedAmount from the ProvisionAmount.

### Decision Logic

| Condition | Result |
|---|---|
| GuaranteeCoveredFlag = 'Y' | NetProvisionAfterCover = ProvisionAmount - CoverAppropriatedAmount |


### R8 — Update Guarantee Cover Ledger

**Affected Field:** `GuaranteeCoverLedger, CoverAppropriatedAmount, NetProvisionAfterCover, LastAppropriationDate`

**Applies to:**

- Account exists in the Guarantee Cover Ledger

**Summary:**

- Update the Guarantee Cover Ledger with the appropriated amount, net provision after cover, and the last appropriation date.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.GuaranteeCoverLedger.AccountId = #CoverLedgerStaging.AccountId | #CoverLedgerStaging.CoverAppropriatedAmount, #CoverLedgerStaging.NetProvisionAfterCover, @ProcessDate |

## Calculations

### Calculation — CoverAppropriatedAmount

**Expression:**

```sql
CASE
    WHEN PRO.LoanAccountCal.AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE
    WHEN PRO.LoanAccountCal.CoverRequestedAmount <= @AvailableCoverBalance THEN PRO.LoanAccountCal.CoverRequestedAmount
    ELSE @AvailableCoverBalance
END
    WHEN PRO.LoanAccountCal.AssetClass = 'SUBSTANDARD' THEN CASE
    WHEN PRO.LoanAccountCal.CoverRequestedAmount <= @AvailableCoverBalance * 0.5 THEN PRO.LoanAccountCal.CoverRequestedAmount
    ELSE @AvailableCoverBalance * 0.5
END
    ELSE 0
END
```

**Output:**
`PRO.LoanAccountCal.CoverAppropriatedAmount`

**Used By:**
READ PRO.LoanAccountCal; UPDATE PRO.LoanAccountCal

### Calculation — NetProvisionAfterCover

**Expression:**

```sql
ProvisionAmount - ISNULL(CoverAppropriatedAmount, 0)
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — AvailableBalance

**Expression:**

```sql
@AvailableCoverBalance - (SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y')
```

**Output:**
`PRO.GuaranteeFund.AvailableBalance`

**Used By:**
READ PRO.GuaranteeFund


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: PRO.LoanAccountCal.CoverRequestedAmount, PRO.LoanAccountCal.CoverShortfallFlag, PRO.LoanAccountCal.CoverAppropriatedAmount, PRO.LoanAccountCal.NetProvisionAfterCover |
| `PRO.GuaranteeCoverLedger` | Read + Write | Provides: #CoverLedgerStaging.CoverAppropriatedAmount, #CoverLedgerStaging.NetProvisionAfterCover, #CoverLedgerStaging.LastAppropriationDate, AccountId, FirstAppropriationDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.GuaranteeFund` | Read + Write | Updates: AvailableBalance, LastAppropriationDate |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#CoverLedgerStaging` | Write | Inserts data into: AccountId, CoverAppropriatedAmount, NetProvisionAfterCover |

## Exception Handling

In case of an error during the process, the status of the Guarantee_Cover_Appropriation process is updated to mark it as not completed, the error date and message are recorded, and the process count is incremented.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
