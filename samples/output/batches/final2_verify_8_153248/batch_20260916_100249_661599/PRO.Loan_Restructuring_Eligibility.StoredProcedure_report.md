# Loan Restructuring Eligibility — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Loan_Restructuring_Eligibility` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

This procedure determines the eligibility of loan accounts for restructuring based on various business rules and updates the necessary fields accordingly.

## Process Flow

1. Read the SysDayMatrix table to get the date for the given TimeKey.
2. Update the PRO.LoanAccountCal table to set the RestructureEligible status, AccountStatus, LastPaymentDueDate, and PriorRestructureCount for loans with a NULL OutstandingBalance and an EligibleFlag of 'Y'.
3. Insert records into the #RestructureDecisions table with AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, and RevisedTenureMonths.
4. Update the RevisedTenureMonths in the #RestructureDecisions table for records with an EligibleFlag of 'Y'.
5. Read from the PRO.LoanAccountCal and #RestructureDecisions tables to update the RestructureEligible status for loans with a non-null and non-'NOT_ASSESSED' RestructureEligible status and an EligibleFlag of 'Y'.
6. Merge records into the PRO.RestructureRegister table.
7. Read from the #RestructureDecisions table for records with an EligibleFlag of 'Y'.
8. Insert records into the PRO.RestructureAuditLog table with AccountId, DecisionDate, and EligibleFlag.
9. Update the PRO.ACLRUNNINGPROCESSSTATUS table to mark the Loan_Restructuring_Eligibility process as completed and increment the count.
10. Read from the PRO.RestructureRegister table for records with a LastEvaluatedDate equal to the ProcessDate and an EligibleFlag of 'Y'.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
_No business rules were identified._

## Business Rules

_No business rules were identified from the extracted source._

## Calculations

### Calculation — LastPaymentDueDate

**Expression:**

```sql
DATEADD(MONTH, RevisedTenureMonths, @ProcessDate)
```

**Output:**
`PRO.LoanAccountCal.LastPaymentDueDate`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — PriorRestructureCount

**Expression:**

```sql
ISNULL(PriorRestructureCount, 0) + 1
```

**Output:**
`PRO.LoanAccountCal.PriorRestructureCount`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

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
| `PRO.LoanAccountCal` | Read + Write | Updates: RestructureEligible, AccountStatus, LastPaymentDueDate, PriorRestructureCount |
| `PRO.RestructureRegister` | Read + Write | Provides: Target.AccountId, Target.EligibleFlag, Target.RevisedTenureMonths, Target.LastEvaluatedDate, FirstEvaluatedDate |
| `PRO.RestructureAuditLog` | Write | Inserts data into: AccountId, DecisionDate, EligibleFlag |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#RestructureDecisions` | Read + Write | Inserts data into: AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths |

## Exception Handling

If the process fails, the running process status is updated to indicate an error.

## Findings / Needs Review

- Lines 70-70 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 109-114 (ASSIGNMENT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- The specific asset classes and values for 'SpecificAssetClass' and 'DifferentAssetClass' are not explicitly mentioned in the extraction.
- The exact value for 'RevisedTenureMonths' in the 'Update Revised Tenure Months' rule is not specified.
- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
