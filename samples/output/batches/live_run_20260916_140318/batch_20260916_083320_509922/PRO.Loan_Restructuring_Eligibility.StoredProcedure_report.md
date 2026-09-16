# Loan Restructuring Eligibility — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Loan_Restructuring_Eligibility` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 1 confident, 1 needs review |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 1 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

This procedure determines the eligibility of loan accounts for restructuring based on various business rules and updates the relevant fields accordingly.

## Process Flow

1. Set the process date based on the time key.
2. Determine the restructuring eligibility for each loan account based on the process date, asset class, overdue days, and prior restructure count.
3. Update the restructuring eligibility for accounts with a null outstanding balance.
4. Create a temporary table to store restructuring decisions.
5. Insert restructuring decisions into the temporary table.
6. Update the revised tenure months for eligible accounts based on the outstanding balance.
7. Merge restructuring decisions into the restructuring register.
8. Update the account status, last payment due date, and prior restructure count for eligible accounts.
9. Insert restructuring decisions into the restructuring audit log.
10. Update the running process status for the loan restructuring eligibility process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine RestructureEligible | `RestructureEligible` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| ⚠️ Merge restructuring decisions | `Not specified` | Merge restructuring decisions into the 'PRO.RestructureRegister' table. |

## Business Rules

### R1 — Determine RestructureEligible

**Affected Field:** `RestructureEligible`


**Source context:**

- IF @ProcessDate < @SchemeCutoffDate is true
- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal AS A
- Expression: CASE WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE WHEN A.PriorRestructureCount IS NULL OR A.PriorRestructureCount = 0 THEN CASE WHEN A.OverdueDays <= 60 THEN 'Y' ELSE 'N' END WHEN A.PriorRestructureCount = 1 THEN CASE WHEN A.OverdueDays <= 30 AND NOT A.OutstandingBalance IS NULL THEN 'Y' ELSE 'N' END ELSE 'N' END ELSE 'N' END

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

### R2 — Merge restructuring decisions

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** Not specified

**Applies to:** eligibility not documented.

**Summary:**

- Merge restructuring decisions into the 'RestructureRegister' table.

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

### Calculation — @SchemeCutoffDate

**Expression:**

```sql
DATEADD(YEAR, -2, @ProcessDate)
```

**Output:**
`Not specified`

**Used By:**
Not specified

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

If the process fails, the running process status is updated to indicate the failure.

## Findings / Needs Review

- Lines 137-139 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 144-146 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
