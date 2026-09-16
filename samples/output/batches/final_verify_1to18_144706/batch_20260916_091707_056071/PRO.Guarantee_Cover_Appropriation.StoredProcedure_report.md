# Guarantee Cover Appropriation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Guarantee_Cover_Appropriation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 20 |
| Tables read | 5 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

This procedure calculates and updates the appropriation of guarantee cover for loan accounts, ensuring that the available balance of the guarantee fund is correctly adjusted and that the accounts are properly flagged and updated with the appropriated amount and net provision after cover.

## Process Flow

1. Read the available balance from the guarantee fund.
2. Update the cover appropriation amount for loan accounts based on their asset class and the available cover balance.
3. Calculate the net provision after cover for each loan account.
4. Update the available balance in the guarantee fund by subtracting the total appropriated amount from the loan accounts.
5. Insert records into the cover ledger staging table.
6. Merge records into the guarantee cover ledger table.
7. Insert records into the collections queue table.
8. Update the running process status to mark the process as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine CoverAppropriatedAmount | `CoverAppropriatedAmount` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Update net provision after cover | `NetProvisionAfterCover` | Update the net provision after cover in the loan account calculation table based on the provision amount and cover appropriated amount. |
| Update CoverRequestedAmount | `CoverRequestedAmount` | Update the CoverRequestedAmount field in the PRO.LoanAccountCal table based on specific conditions. |
| Update CoverShortfallFlag | `CoverShortfallFlag` | Update the CoverShortfallFlag field in the PRO.LoanAccountCal table based on specific conditions. |
| Update CoverAppropriatedAmount | `CoverAppropriatedAmount` | Update the CoverAppropriatedAmount field in the PRO.LoanAccountCal table based on specific conditions. |
| Update NetProvisionAfterCover | `NetProvisionAfterCover` | Update the NetProvisionAfterCover field in the PRO.LoanAccountCal table based on specific conditions. |
| Insert into CoverLedgerStaging [1] | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Insert data into the #CoverLedgerStaging table. |
| Insert into CollectionsQueue [1] | `AccountId, EscalationDate, Reason` | Insert data into the PRO.CollectionsQueue table. |
| Reset cover requested amount to null | `CoverRequestedAmount` | For accounts with a guarantee covered flag of 'Y' and a null provision amount, the cover requested amount is reset to null. |
| Set cover requested amount to provision amount | `CoverRequestedAmount` | For accounts with a guarantee covered flag of 'Y', a non-null provision amount, and a positive provision amount, the cover requested amount… |
| Update cover appropriation amount | `CoverAppropriatedAmount` | Calculate the cover appropriation amount for loan accounts based on their asset class and the available cover balance. |
| Calculate net provision after cover [1] | `NetProvisionAfterCover` | Calculate the net provision after cover for each loan account. |
| Update available balance in guarantee fund [1] | `AvailableBalance` | Update the available balance in the guarantee fund by subtracting the total appropriated amount from the loan accounts. |
| Merge into guarantee cover ledger [1] | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Merge records into the guarantee cover ledger table. |
| Calculate net provision after cover [2] | `NetProvisionAfterCover` | Calculate the net provision after cover for loan accounts. |
| Update available balance in guarantee fund [2] | `AvailableBalance` | Update the available balance in the guarantee fund after appropriation. |
| Insert into cover ledger staging | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Insert records into the cover ledger staging table. |
| Merge into guarantee cover ledger [2] | `Target.AccountId, Source.AccountId, Target.CoverAppropriatedAmount, Source.CoverAppropriatedAmount, Target.NetProvisionAfterCover, Source.NetProvisionAfterCover, Target.LastAppropriationDate, AccountId, CoverAppropriatedAmount, NetProvisionAfterCover, FirstAppropriationDate, LastAppropriationDate` | Merge records into the guarantee cover ledger table. |
| Insert into CoverLedgerStaging [2] | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Insert records into the '#CoverLedgerStaging' table with fields 'AccountId', 'CoverAppropriatedAmount', and 'NetProvisionAfterCover'. |
| Insert into CollectionsQueue [2] | `AccountId, EscalationDate, Reason` | Insert records into the 'PRO.CollectionsQueue' table with fields 'AccountId', 'EscalationDate', and 'Reason'. |

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

### R2 — Update net provision after cover

**Affected Field:** `NetProvisionAfterCover`

**Applies to:**

- GuaranteeCoveredFlag = 'Y'

**Summary:**

- Update the net provision after cover in the loan account calculation table based on the provision amount and cover appropriated amount.

### Decision Logic

| Condition | Result |
|---|---|
| ProvisionAmount - ISNULL(CoverAppropriatedAmount, 0) | ProvisionAmount - ISNULL(CoverAppropriatedAmount, 0) |


### R3 — Update CoverRequestedAmount

**Affected Field:** `CoverRequestedAmount`

**Applies to:**

- CoverRequestedAmount is being updated

**Summary:**

- Update the CoverRequestedAmount field in the LoanAccountCal table based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| CoverRequestedAmount is updated | new value |


### R4 — Update CoverShortfallFlag

**Affected Field:** `CoverShortfallFlag`

**Applies to:**

- CoverShortfallFlag is being updated

**Summary:**

- Update the CoverShortfallFlag field in the LoanAccountCal table based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| CoverShortfallFlag is updated | new value |


### R5 — Update CoverAppropriatedAmount

**Affected Field:** `CoverAppropriatedAmount`

**Applies to:**

- CoverAppropriatedAmount is being updated

**Summary:**

- Update the CoverAppropriatedAmount field in the LoanAccountCal table based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| CoverAppropriatedAmount is updated | new value |


### R6 — Update NetProvisionAfterCover

**Affected Field:** `NetProvisionAfterCover`

**Applies to:**

- NetProvisionAfterCover is being updated

**Summary:**

- Update the NetProvisionAfterCover field in the LoanAccountCal table based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| NetProvisionAfterCover is updated | new value |


### R7 — Insert into CoverLedgerStaging [1]

**Affected Field:** `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover`

**Applies to:**

- Data is being inserted into #CoverLedgerStaging

**Summary:**

- Insert data into the #CoverLedgerStaging table.


### R8 — Insert into CollectionsQueue [1]

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- Data is being inserted into CollectionsQueue

**Summary:**

- Insert data into the CollectionsQueue table.


### R9 — Reset cover requested amount to null

**Affected Field:** `CoverRequestedAmount`

**Applies to:**

- Account has a guarantee covered flag of 'Y'
- Provision amount is null

**Summary:**

- For accounts with a guarantee covered flag of 'Y' and a null provision amount, the cover requested amount is reset to null.

### Decision Logic

| Condition | Result |
|---|---|
| GuaranteeCoveredFlag = 'Y' AND ProvisionAmount IS NULL | NULL |


### R10 — Set cover requested amount to provision amount

**Affected Field:** `CoverRequestedAmount`

**Applies to:**

- Account has a guarantee covered flag of 'Y'
- Provision amount is not null
- Provision amount is greater than 0

**Summary:**

- For accounts with a guarantee covered flag of 'Y', a non-null provision amount, and a positive provision amount, the cover requested amount is set to the provision amount.

### Decision Logic

| Condition | Result |
|---|---|
| GuaranteeCoveredFlag = 'Y' AND ProvisionAmount IS NOT NULL AND ProvisionAmount > 0 | ProvisionAmount |


### R11 — Update cover appropriation amount

**Affected Field:** `CoverAppropriatedAmount`

**Summary:**

- Calculate the cover appropriation amount for loan accounts based on their asset class and the available cover balance.

### Decision Logic

| Condition | Result |
|---|---|
| AssetClass IN ('DOUBTFUL', 'LOSS') | CASE WHEN CoverRequestedAmount <= @AvailableCoverBalance THEN CoverRequestedAmount ELSE @AvailableCoverBalance END |
| AssetClass = 'SUBSTANDARD' | CASE WHEN CoverRequestedAmount <= @AvailableCoverBalance * 0.5 THEN CoverRequestedAmount ELSE @AvailableCoverBalance * 0.5 END |
| ELSE | 0 |

### R12 — Calculate net provision after cover [1]

**Affected Field:** `NetProvisionAfterCover`

**Applies to:**

- Loan account is guaranteed

**Summary:**

- Calculate the net provision after cover for each loan account.

### Decision Logic

| Condition | Result |
|---|---|
| GuaranteeCoveredFlag = 'Y' | ProvisionAmount - ISNULL(CoverAppropriatedAmount, 0) |


### R13 — Update available balance in guarantee fund [1]

**Affected Field:** `AvailableBalance`

**Applies to:**

- Guarantee fund is the government cover guarantee fund

**Summary:**

- Update the available balance in the guarantee fund by subtracting the total appropriated amount from the loan accounts.

### Decision Logic

| Condition | Result |
|---|---|
| FundId = 'GOVT_CGF' | @AvailableCoverBalance - (SELECT COALESCE(SUM(CoverAppropriatedAmount), 0) FROM LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y') |


### R14 — Merge into guarantee cover ledger [1]

**Affected Field:** `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover`

**Applies to:** eligibility not documented.

**Summary:**

- Merge records into the guarantee cover ledger table.


### R15 — Calculate net provision after cover [2]

**Affected Field:** `NetProvisionAfterCover`

**Applies to:**

- Loan account has a guarantee covered flag set to 'Y'

**Summary:**

- Calculate the net provision after cover for loan accounts.


### R16 — Update available balance in guarantee fund [2]

**Affected Field:** `AvailableBalance`

**Applies to:**

- Guarantee fund has a fund ID of 'GOVT_CGF'

**Summary:**

- Update the available balance in the guarantee fund after appropriation.


### R17 — Insert into cover ledger staging

**Affected Field:** `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover`

**Applies to:**

- Loan account has a guarantee covered flag set to 'Y'

**Summary:**

- Insert records into the cover ledger staging table.


### R18 — Merge into guarantee cover ledger [2]

**Affected Field:** `Target.AccountId, Source.AccountId, Target.CoverAppropriatedAmount, Source.CoverAppropriatedAmount, Target.NetProvisionAfterCover, Source.NetProvisionAfterCover, Target.LastAppropriationDate, AccountId, CoverAppropriatedAmount, NetProvisionAfterCover, FirstAppropriationDate, LastAppropriationDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge records into the guarantee cover ledger table.


### R19 — Insert into CoverLedgerStaging [2]

**Affected Field:** `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover`

**Applies to:**

- The '#CoverLedgerStaging' table is being updated

**Summary:**

- Insert records into the '#CoverLedgerStaging' table with fields 'AccountId', 'CoverAppropriatedAmount', and 'NetProvisionAfterCover'.


### R20 — Insert into CollectionsQueue [2]

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- The 'CollectionsQueue' table is being updated

**Summary:**

- Insert records into the 'CollectionsQueue' table with fields 'AccountId', 'EscalationDate', and 'Reason'.

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

If an error occurs during the 'Guarantee_Cover_Appropriation' process, the status is logged in the 'PRO.ACLRUNNINGPROCESSSTATUS' table with 'COMPLETED' set to 'N', 'ERRORDATE' set to the current date and time, 'ERRORDESCRIPTION' set to the error message, and 'COUNT' incremented by 1.

## Findings / Needs Review

- The specific conditions and outcomes for updating fields in the PRO.LoanAccountCal table are not detailed in the extraction, leading to placeholders for the decision logic rows.
- 7 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
