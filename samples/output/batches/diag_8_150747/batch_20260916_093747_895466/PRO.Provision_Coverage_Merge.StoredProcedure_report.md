# Provision Coverage Merge — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Coverage_Merge` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 3 confident, 3 needs review |
| Tables read | 4 |
| Tables written | 3 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 3 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure calculates and updates the coverage ratio and review reason for accounts, and merges the data into the ProvisionCoverageSummary table. It also updates the process status and inserts data into the CollectionsQueue table.

## Process Flow

1. Read the date from the SysDayMatrix table based on the TimeKey parameter.
2. Insert data into the #ProvisionCoverage table from the PRO.LoanAccountCal table.
3. Update the ReviewReason in the #ProvisionCoverage table based on the CoverageRatio.
4. Merge data from the #ProvisionCoverage table into the PRO.ProvisionCoverageSummary table.
5. Update the BelowThresholdFlag in the PRO.ProvisionCoverageSummary table based on the CoverageRatio and LastUpdatedDate.
6. Insert data into the PRO.CollectionsQueue table.
7. Update the status in the PRO.ACLRUNNINGPROCESSSTATUS table for the 'Provision_Coverage_Merge' process.
8. Read data from the PRO.LoanAccountCal table to calculate the CoverageRatio.
9. Read data from the #ProvisionCoverage table to update the ReviewReason based on the CoverageRatio and process date.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine CoverageRatio | `CoverageRatio` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| ⚠️ Update the ReviewReason in the #ProvisionCoverage table to append '_QUARTER_END' for accounts with a coverage ratio less than 0.6. | `ReviewReason` | Update the ReviewReason in the #ProvisionCoverage table to append '_QUARTER_END' for accounts with a coverage ratio less than 0.6. |
| Determine ReviewReason (#ProvisionCoverage) | `ReviewReason` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| ⚠️ Merge data into PRO.ProvisionCoverageSummary | `AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, FirstSeenDate, LastUpdatedDate` | Merge the #ProvisionCoverage table data into the PRO.ProvisionCoverageSummary table. |
| ⚠️ Update BelowThresholdFlag | `BelowThresholdFlag` | Update the BelowThresholdFlag in the PRO.ProvisionCoverageSummary table based on coverage ratio thresholds. |

## Business Rules

### R1 — Determine CoverageRatio

**Affected Field:** `CoverageRatio`


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

### R2 — Update the ReviewReason in the #ProvisionCoverage table to append '_QUARTER_END' for accounts with a coverage ratio less than 0.6.

**Affected Field:** `ReviewReason`

**Summary:**

- Update the ReviewReason in the #ProvisionCoverage table to append '_QUARTER_END' for accounts with a coverage ratio less than 0.6.

### Decision Logic

| Condition | Result |
|---|---|
| @ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate) | ReviewReason + '_QUARTER_END' |
| ELSE |  |

### R3 — Determine ReviewReason (#ProvisionCoverage)

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

### R4 — Determine Reason

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

### R5 — Merge data into PRO.ProvisionCoverageSummary

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, FirstSeenDate, LastUpdatedDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge the #ProvisionCoverage table data into the ProvisionCoverageSummary table.


### R6 — Update BelowThresholdFlag

**Affected Field:** `BelowThresholdFlag`

**Summary:**

- Update the BelowThresholdFlag in the PRO.ProvisionCoverageSummary table based on coverage ratio thresholds.

### Decision Logic

| Condition | Result |
|---|---|
| CoverageRatio IS NULL |  |
| CoverageRatio < 0.25 |  |
| CoverageRatio < 0.5 | 'Y' |
| CoverageRatio >= 0.5 AND CoverageRatio < 1 |  |
| ELSE |  |

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

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS

### Calculation — CoverageRatio

**Expression:**

```sql
ProvisionAmount / OutstandingBalance
```

**Output:**
`Not specified`

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

The procedure uses a TRY-CATCH block to handle any exceptions that may occur during execution. If an error occurs during the execution of the 'Provision_Coverage_Merge' process, the running process status is updated to reflect the error.

## Findings / Needs Review

- Lines 26-26 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 70-72 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 76-78 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 2 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
