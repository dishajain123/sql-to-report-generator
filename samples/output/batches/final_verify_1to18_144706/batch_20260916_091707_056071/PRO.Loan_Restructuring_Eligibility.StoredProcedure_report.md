# Loan Restructuring Eligibility — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Loan_Restructuring_Eligibility` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 5 needs review |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 5 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

This procedure determines the eligibility of loan accounts for restructuring based on various business rules and updates the necessary fields accordingly.

## Process Flow

1. Calculate the process date based on the provided time key.
2. Determine the scheme cutoff date by subtracting two years from the process date.
3. Update the 'RestructureEligible' field in the 'PRO.LoanAccountCal' table based on the asset class and overdue days.
4. Update the 'AccountStatus', 'LastPaymentDueDate', and 'PriorRestructureCount' fields in the 'PRO.LoanAccountCal' table for eligible accounts.
5. Insert records into the '#RestructureDecisions' table for eligible accounts.
6. Update the 'RevisedTenureMonths' field in the '#RestructureDecisions' table for eligible accounts.
7. Read from the '#RestructureDecisions' table to get the revised tenure months and eligible flag for eligible accounts.
8. Merge records into the 'PRO.RestructureRegister' table for eligible accounts.
9. Read from the 'PRO.RestructureRegister' table to get the last evaluated date and eligible flag for accounts evaluated on the process date.
10. Insert records into the 'PRO.RestructureAuditLog' table for accounts approved in the current run.
11. Update the 'COMPLETED', 'ERRORDATE', 'ERRORDESCRIPTION', and 'COUNT' fields in the 'PRO.ACLRUNNINGPROCESSSTATUS' table to mark the process as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Insert into temporary table | `AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths` | Insert records into the #RestructureDecisions table for eligible accounts. |
| ⚠️ Update account status and last payment due date | `LastPaymentDueDate, AccountStatus` | Update the AccountStatus and LastPaymentDueDate for eligible accounts. |
| ⚠️ Insert restructure audit log | `AccountId, DecisionDate, EligibleFlag` | Insert records into the PRO.RestructureAuditLog table for accounts approved in the current run. |
| ⚠️ Create temporary table | `Not specified` | Create the temporary #RestructureDecisions table. |
| ⚠️ Merge restructure register | `Target.AccountId, Source.AccountId, Target.EligibleFlag, Source.EligibleFlag, Target.RevisedTenureMonths, Source.RevisedTenureMonths, Target.LastEvaluatedDate, AccountId, EligibleFlag, RevisedTenureMonths, FirstEvaluatedDate, LastEvaluatedDate` | Merge records into the PRO.RestructureRegister table. |

## Business Rules

### R1 — Insert into temporary table

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths`

**Applies to:**

- Account is flagged as eligible

**Summary:**

- Insert records into the #RestructureDecisions table for eligible accounts.


### R2 — Update account status and last payment due date

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `LastPaymentDueDate, AccountStatus`

**Applies to:**

- Account is flagged as eligible

**Summary:**

- Update the AccountStatus and LastPaymentDueDate for eligible accounts.

### Decision Logic

| Condition | Result |
|---|---|
| EligibleFlag = 'Y' | DATEADD(MONTH, RevisedTenureMonths, @ProcessDate) |


### R3 — Insert restructure audit log

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, DecisionDate, EligibleFlag`

**Applies to:**

- Account is flagged as eligible

**Summary:**

- Insert records into the RestructureAuditLog table for accounts approved in the current run.


### R4 — Create temporary table

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** Not specified

**Applies to:** eligibility not documented.

**Summary:**

- Create the temporary #RestructureDecisions table.


### R5 — Merge restructure register

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `Target.AccountId, Source.AccountId, Target.EligibleFlag, Source.EligibleFlag, Target.RevisedTenureMonths, Source.RevisedTenureMonths, Target.LastEvaluatedDate, AccountId, EligibleFlag, RevisedTenureMonths, FirstEvaluatedDate, LastEvaluatedDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge records into the RestructureRegister table.

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

If an error occurs during the execution of the procedure, the running process status is updated to reflect the error.

## Findings / Needs Review

- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
