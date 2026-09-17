# Loan Restructuring Eligibility — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Loan_Restructuring_Eligibility` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 7 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

This procedure determines the eligibility of loan accounts for restructuring based on predefined criteria and updates relevant account statuses, payment due dates, and restructuring counts. This procedure also writes to: LoanAccountCal, RestructureAuditLog, RestructureDecisions, RestructureRegister.

## Process Flow

1. Read the process date from the SysDayMatrix table using the provided TimeKey.
2. Calculate the scheme cutoff date by subtracting two years from the process date.
3. Check if the process date is before the scheme cutoff date.
4. Update the 'RestructureEligible' field in the 'PRO.LoanAccountCal' table based on the asset class and overdue days.
5. Set the 'RestructureEligible' field to 'NOT_ASSESSED' for loan accounts with a NULL outstanding balance.
6. Drop the temporary table '#RestructureDecisions' if it exists.
7. Create the temporary table '#RestructureDecisions' with columns for account ID, decision date, eligibility flag, asset class, and revised tenure months.
8. Insert records into '#RestructureDecisions' for loan accounts with a non-NULL and non-'NOT_ASSESSED' 'RestructureEligible' status.
9. Update the 'RevisedTenureMonths' field in '#RestructureDecisions' based on the outstanding balance of the loan account.
10. Merge the restructuring decisions into the restructuring register.
11. For matched records, update the eligibility flag, revised tenure months, and last evaluated date.
12. Update the account status, last payment due date, and prior restructure count for eligible accounts.
13. Insert eligible accounts into the restructure audit log.
14. Update the running process status to mark the process as completed.
15. Handle any exceptions by updating the running process status to indicate an error.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Insert into #RestructureDecisions | `AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths` | Not specified |
| Update AccountStatus, LastPaymentDueDate, PriorRestructureCount | `AccountStatus, LastPaymentDueDate, PriorRestructureCount` | Not specified |
| Insert into RestructureAuditLog | `AccountId, DecisionDate, EligibleFlag` | Not specified |
| Upsert restructureregister | `EligibleFlag, RevisedTenureMonths, LastEvaluatedDate, AccountId, FirstEvaluatedDate` | Refresh existing rows and insert rows not already present. |
| Determine RestructureEligible | `RestructureEligible` | Not specified |
| Determine RestructureEligible (PRO.LoanAccountCal) | `RestructureEligible` | Not specified |
| Update revised tenure months | `RevisedTenureMonths` | Update the 'RevisedTenureMonths' field in '#RestructureDecisions' based on the outstanding balance of the loan account. |

## Business Rules

### R1 — Insert into #RestructureDecisions

**Affected Field:** `AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| NOT PRO.LoanAccountCal.RestructureEligible IS NULL AND PRO.LoanAccountCal.RestructureEligible <> 'NOT_ASSESSED' | AccountId := PRO.LoanAccountCal.AccountId; DecisionDate := @ProcessDate; EligibleFlag := PRO.LoanAccountCal.RestructureEligible; AssetClassAtEval := PRO.LoanAccountCal.AssetClass; RevisedTenureMonths := NULL |


### R2 — Update AccountStatus, LastPaymentDueDate, PriorRestructureCount

**Affected Field:** `AccountStatus, LastPaymentDueDate, PriorRestructureCount`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| #RestructureDecisions.EligibleFlag = 'Y' | AccountStatus := 'RESTRUCTURED'; LastPaymentDueDate := DATEADD(MONTH, #RestructureDecisions.RevisedTenureMonths, @ProcessDate); PriorRestructureCount := COALESCE(PriorRestructureCount, 0) + 1 |


### R3 — Insert into RestructureAuditLog

**Affected Field:** `AccountId, DecisionDate, EligibleFlag`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.RestructureRegister.LastEvaluatedDate = @ProcessDate AND PRO.RestructureRegister.EligibleFlag = 'Y' | AccountId := PRO.RestructureRegister.AccountId; DecisionDate := PRO.RestructureRegister.LastEvaluatedDate; EligibleFlag := PRO.RestructureRegister.EligibleFlag |


### R4 — Upsert restructureregister

**Affected Field:** `EligibleFlag, RevisedTenureMonths, LastEvaluatedDate, AccountId, FirstEvaluatedDate`

**Applies to:** eligibility not documented.

**Summary:**

- Refresh existing rows and insert rows not already present.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | #RestructureDecisions.EligibleFlag; #RestructureDecisions.RevisedTenureMonths; @ProcessDate |
| WHEN NOT MATCHED BY TARGET | #RestructureDecisions.AccountId; #RestructureDecisions.EligibleFlag; #RestructureDecisions.RevisedTenureMonths; @ProcessDate |


### R5 — Determine RestructureEligible

**Affected Field:** `RestructureEligible`

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| @ProcessDate < @SchemeCutoffDate — applies to all rows (no additional filter) | (nested CASE — see separate decision table) |
| ELSE — applies to all rows (no additional filter) | 'SCHEME_CLOSED' |

### R6 — Determine RestructureEligible (PRO.LoanAccountCal)

**Affected Field:** `RestructureEligible`


**Source context:**

- IF @ProcessDate < @SchemeCutoffDate is true
- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal
- Expression: CASE WHEN PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA') THEN CASE WHEN PRO.LoanAccountCal.PriorRestructureCount IS NULL OR PRO.LoanAccountCal.PriorRestructureCount = 0 THEN CASE WHEN PRO.LoanAccountCal.OverdueDays <= 60 THEN 'Y' ELSE 'N' END WHEN PRO.LoanAccountCal.PriorRestructureCount = 1 THEN CASE WHEN PRO.LoanAccountCal.OverdueDays <= 30 AND NOT PRO.LoanAccountCal.OutstandingBalance IS NULL THEN 'Y' ELSE 'N' END ELSE 'N' END ELSE 'N' END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| (AssetClass IN ('STANDARD', 'SMA')) AND ((PriorRestructureCount IS NULL OR PriorRestructureCount = 0) AND (OverdueDays <= 60)) | 'Y' |
| (AssetClass IN ('STANDARD', 'SMA')) AND (PriorRestructureCount IS NULL OR PriorRestructureCount = 0) | 'N' |
| (AssetClass IN ('STANDARD', 'SMA')) AND ((PriorRestructureCount = 1) AND (OverdueDays <= 30 AND NOT OutstandingBalance IS NULL)) | 'Y' |
| (AssetClass IN ('STANDARD', 'SMA')) AND (PriorRestructureCount = 1) | 'N' |
| AssetClass IN ('STANDARD', 'SMA') | 'N' |
| ELSE | 'N' |

### R7 — Update revised tenure months

**Affected Field:** `RevisedTenureMonths`

**Summary:**

- Update the 'RevisedTenureMonths' field in '#RestructureDecisions' based on the outstanding balance of the loan account.

**Applies to:**

- #RestructureDecisions.EligibleFlag = 'Y'

**Source context:**

- Target: #RestructureDecisions
- FROM #RestructureDecisions INNER JOIN PRO.LoanAccountCal ON PRO.LoanAccountCal.AccountId = #RestructureDecisions.AccountId

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.OutstandingBalance > 1000000 | 60 |
| PRO.LoanAccountCal.OutstandingBalance > 500000 | 48 |
| ELSE | 36 |

## Calculations

### Calculation — LastPaymentDueDate

**Expression:**

```sql
DATEADD(MONTH, #RestructureDecisions.RevisedTenureMonths, @ProcessDate)
```

**Output:**
`PRO.LoanAccountCal.LastPaymentDueDate`

**Used By:**
READ PRO.LoanAccountCal; UPDATE PRO.LoanAccountCal

### Calculation — PriorRestructureCount

**Expression:**

```sql
ISNULL(PRO.LoanAccountCal.PriorRestructureCount, 0) + 1
```

**Output:**
`PRO.LoanAccountCal.PriorRestructureCount`

**Used By:**
READ PRO.LoanAccountCal; UPDATE PRO.LoanAccountCal

### Calculation — SchemeCutoffDate

**Expression:**

```sql
DATEADD(YEAR, -2, @ProcessDate)
```

**Output:**
`Not specified`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: PRO.LoanAccountCal.RestructureEligible, PRO.LoanAccountCal.AccountStatus, PRO.LoanAccountCal.LastPaymentDueDate, PRO.LoanAccountCal.PriorRestructureCount |
| `PRO.RestructureRegister` | Read + Write | Provides: #RestructureDecisions.EligibleFlag, #RestructureDecisions.RevisedTenureMonths, #RestructureDecisions.LastEvaluatedDate, AccountId, FirstEvaluatedDate |
| `PRO.RestructureAuditLog` | Write | Inserts data into: AccountId, DecisionDate, EligibleFlag |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#RestructureDecisions` | Read + Write | Inserts data into: AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths |

## Exception Handling

If an exception occurs during the process, the running process status is updated to indicate an error, and the error details are logged.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
