# Provision Coverage Merge — Business Logic Report

> **⚠ DEGRADED RUN — POSSIBLY INCOMPLETE**
> 1 rule synthesis section(s) failed after retries and were excluded rather than aborting the whole run. This report may be missing evidence or business rules from the affected portion of the source. Re-run to attempt full coverage.

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Coverage_Merge` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 4 |
| Tables read | 4 |
| Tables written | 3 |
| Produces audit trail | Not detected |

## What This Does

Not explicitly determined from source SQL.

## Process Flow

_Not explicitly determined from source SQL._

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine CoverageRatio | `CoverageRatio` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Determine ReviewReason (#ProvisionCoverage) | `ReviewReason` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine ReviewReason | `ReviewReason` | Not specified |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |

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

### R2 — Determine ReviewReason (#ProvisionCoverage)

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

### R3 — Determine ReviewReason

**Affected Field:** `ReviewReason`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| @ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate) — row filter: CoverageRatio IS NOT NULL AND CoverageRatio < 0.6 | ReviewReason + '_QUARTER_END' |
| ELSE — row filter: CoverageRatio IS NOT NULL AND CoverageRatio < 0.5 | ReviewReason |


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
`ReviewReason`

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

The procedure defines an explicit error handler (`BEGIN CATCH ... END CATCH`). On failure, it runs:

```sql
-- Exception handling: record the failure for operations to investigate
        UPDATE PRO.ACLRUNNINGPROCESSSTATUS
        SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1
        WHERE RUNNINGPROCESSNAME = 'Provision_Coverage_Merge'
```

## Findings / Needs Review

- Lines 26-26 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 40-50 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 40-50 (CALCULATION/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 55-60 (ASSIGNMENT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 68-72 (ASSIGNMENT/IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 76-78 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 84-84 (MERGE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 87-94 (ASSIGNMENT/INSERT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 99-104 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 108-112 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 117-122 (CASE/INSERT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
