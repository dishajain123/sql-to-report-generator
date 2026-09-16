# Provision Coverage Merge — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Coverage_Merge` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 2 confident, 4 needs review |
| Tables read | 4 |
| Tables written | 3 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 4 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure 'Provision_Coverage_Merge' manages the merging and updating of provisioning coverage data for accounts, ensuring that the data is up-to-date and reflects the correct provisioning status based on the coverage ratio.

## Process Flow

1. Insert account data into the #ProvisionCoverage temporary table.
2. Calculate the coverage ratio for each account.
3. Update the review reason based on the coverage ratio.
4. Merge the #ProvisionCoverage temporary table data into the PRO.ProvisionCoverageSummary table.
5. Update the BelowThresholdFlag in the PRO.ProvisionCoverageSummary table based on the coverage ratio.
6. Insert data into the PRO.CollectionsQueue table based on the coverage ratio and review reason.
7. Update the PRO.ACLRUNNINGPROCESSSTATUS table to mark the process as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine ReviewReason | `ReviewReason` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| ⚠️ Calculate coverage ratio | `CoverageRatio` | Calculate the coverage ratio for accounts with non-null outstanding balances. |
| ⚠️ Update review reason | `ReviewReason, BelowThresholdFlag` | Update the review reason based on the coverage ratio. |
| ⚠️ Conditionally append to review reason | `ReviewReason` | Conditionally append '_QUARTER_END' to the review reason if the process date is within a certain range. |
| ⚠️ Merge data into summary table | `AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, FirstSeenDate, LastUpdatedDate` | Merge data from the #ProvisionCoverage temporary table into the PRO.ProvisionCoverageSummary table. |

## Business Rules

### R1 — Determine ReviewReason

**Affected Field:** `ReviewReason`


**Source context:**

- Target: #ProvisionCoverage
- FROM #ProvisionCoverage AS S

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| #ProvisionCoverage.CoverageRatio IS NULL | 'NO_BALANCE' |
| #ProvisionCoverage.CoverageRatio < 0.25 | 'SEVERE_UNDERCOVER' |
| #ProvisionCoverage.CoverageRatio < 0.5 | 'MODERATE_UNDERCOVER' |
| #ProvisionCoverage.CoverageRatio >= 0.5 AND #ProvisionCoverage.CoverageRatio < 1 | 'ADEQUATE' |
| ELSE | 'FULLY_COVERED' |

### R2 — Determine Reason

**Affected Field:** `Reason`


**Applies to:**

- ReviewReason LIKE '%UNDERCOVER%' AND NOT CoverageRatio IS NULL

**Source context:**

- Target: PRO.CollectionsQueue
- FROM #ProvisionCoverage
- Expression: CASE WHEN CoverageRatio < 0.25 THEN 'SEVERE_PROVISION_SHORTFALL' ELSE 'MODERATE_PROVISION_SHORTFALL' END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| CoverageRatio < 0.25 | 'SEVERE_PROVISION_SHORTFALL' |
| ELSE | 'MODERATE_PROVISION_SHORTFALL' |

### R3 — Calculate coverage ratio

**Affected Field:** `CoverageRatio`

**Summary:**

- Calculate the coverage ratio for accounts with non-null outstanding balances.

**Applies to:**

- NOT PRO.LoanAccountCal.OutstandingBalance IS NULL

**Source context:**

- Target: #ProvisionCoverage
- FROM PRO.LoanAccountCal AS A
- Expression: CASE WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.OutstandingBalance ELSE NULL END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.OutstandingBalance > 0 | PRO.LoanAccountCal.ProvisionAmount / PRO.LoanAccountCal.OutstandingBalance |
| ELSE | NULL |

### R4 — Update review reason

**Affected Field:** `ReviewReason, BelowThresholdFlag`

**Summary:**

- Update the review reason based on the coverage ratio.

### Decision Logic

| Condition | Result |
|---|---|
| CoverageRatio IS NULL | 'NO_BALANCE' |
| CoverageRatio < 0.25 | 'SEVERE_UNDERCOVER' |
| CoverageRatio < 0.5 | 'MODERATE_UNDERCOVER'; Set BelowThresholdFlag to 'Y'. |
| CoverageRatio >= 0.5 AND CoverageRatio < 1 | 'ADEQUATE' |
| ELSE |  |

### R5 — Conditionally append to review reason

**Affected Field:** `ReviewReason`

**Summary:**

- Conditionally append '_QUARTER_END' to the review reason if the process date is within a certain range.

### Decision Logic

| Condition | Result |
|---|---|
| @ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate) | ReviewReason + '_QUARTER_END' |
| ELSE | ReviewReason |

### R6 — Merge data into summary table

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, FirstSeenDate, LastUpdatedDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge data from the #ProvisionCoverage temporary table into the ProvisionCoverageSummary table.

## Calculations

### Calculation — CoverageRatio

**Expression:**

```sql
CASE
    WHEN OutstandingBalance > 0 THEN ProvisionAmount / OutstandingBalance
    ELSE NULL
END
```

**Output:**
`#ProvisionCoverage.CoverageRatio`

**Used By:**
INSERT INTO #ProvisionCoverage

### Calculation — ReviewReason

**Expression:**

```sql
ReviewReason + '_QUARTER_END'
```

**Output:**
`#ProvisionCoverage.ReviewReason`

**Used By:**
UPDATE #ProvisionCoverage; READ #ProvisionCoverage

### Calculation — CoverageRatio

**Expression:**

```sql
ProvisionAmount / OutstandingBalance
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
| `PRO.ProvisionCoverageSummary` | Read + Write | Updates: Target.AccountId, Target.OutstandingBalance, Target.ProvisionAmount, Target.CoverageRatio, Target.LastUpdatedDate, FirstSeenDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |
| `PRO.LoanAccountCal` | Read | Provides: AccountId, OutstandingBalance, ProvisionAmount, CASE<br>                   WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.OutstandingBalance<br>                   ELSE NULL<br>               END, NULL |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#ProvisionCoverage` | Read + Write | Inserts data into: AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, ReviewReason |

## Exception Handling

The procedure uses a TRY-CATCH block to handle exceptions, but no specific exception handling steps are defined in the source. If an error occurs during the execution of the 'Provision_Coverage_Merge' process, the running process status is updated to reflect the error.

## Findings / Needs Review

- Lines 26-26 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 70-72 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 76-78 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 124-126 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 131-133 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 2 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
