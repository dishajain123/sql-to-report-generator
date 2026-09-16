# Provision Coverage Merge — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Coverage_Merge` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 3 confident, 2 needs review |
| Tables read | 4 |
| Tables written | 3 |
| Produces audit trail | Not detected |
| **Run status** | ℹ️ **Additional rules added from a targeted review pass.** 2 rule(s) were added after a second, narrowly-scoped look at a source line no rule initially cited - the model's call succeeded normally, but a new rule for a previously-unreviewed line still warrants a quick human check against the source; affected rules are marked inline. |

## What This Does

The procedure updates and inserts records into the ProvisionCoverage and ProvisionCoverageSummary tables, and updates the ACLRUNNINGPROCESSSTATUS table to reflect the completion status of the Provision_Coverage_Merge process.

## Process Flow

1. Read the date for the given time key from the SysDayMatrix table.
2. Calculate the quarter start date based on the read date.
3. Drop the temporary #ProvisionCoverage table if it exists.
4. Create the temporary #ProvisionCoverage table with specified columns.
5. Insert account details into the #ProvisionCoverage table from the PRO.LoanAccountCal table.
6. Update the ReviewReason in the #ProvisionCoverage table based on the CoverageRatio.
7. Merge the #ProvisionCoverage table into the PRO.ProvisionCoverageSummary table.
8. Update the BelowThresholdFlag in the PRO.ProvisionCoverageSummary table based on the CoverageRatio and LastUpdatedDate.
9. Insert records into the PRO.CollectionsQueue table.
10. Update the status of the Provision_Coverage_Merge process in the PRO.ACLRUNNINGPROCESSSTATUS table.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine ReviewReason (#ProvisionCoverage) | `ReviewReason` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Update BelowThresholdFlag for CoverageRatio < 0.5 | `BelowThresholdFlag` | Set BelowThresholdFlag to 'Y' for accounts with a CoverageRatio less than 0.5 and a LastUpdatedDate equal to the process date. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Determine ReviewReason | `ReviewReason` | Not specified |
| ⚠️ Merge provisioning coverage summary | `Target.AccountId, Source.AccountId, Target.OutstandingBalance, Source.OutstandingBalance, Target.ProvisionAmount, Source.ProvisionAmount, Target.CoverageRatio, Source.CoverageRatio, Target.LastUpdatedDate, AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, FirstSeenDate, LastUpdatedDate` | Merge provisioning coverage summary data into the PRO.ProvisionCoverageSummary table. |

## Business Rules

### R1 — Determine ReviewReason (#ProvisionCoverage)

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

### R2 — Update BelowThresholdFlag for CoverageRatio < 0.5

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `BelowThresholdFlag`

**Applies to:**

- Account has a non-null CoverageRatio less than 0.5 and a LastUpdatedDate equal to the process date

**Summary:**

- Set BelowThresholdFlag to 'Y' for accounts with a CoverageRatio less than 0.5 and a LastUpdatedDate equal to the process date.

### Decision Logic

| Condition | Result |
|---|---|
| CoverageRatio < 0.5 AND LastUpdatedDate = @ProcessDate | 'Y' |


### R3 — Determine Reason

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

### R4 — Determine ReviewReason

**Affected Field:** `ReviewReason`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| @ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate) — row filter: CoverageRatio IS NOT NULL AND CoverageRatio < 0.6 | ReviewReason + '_QUARTER_END' |
| ELSE — row filter: CoverageRatio IS NOT NULL AND CoverageRatio < 0.5 | ReviewReason |


### R5 — Merge provisioning coverage summary

> ℹ️ **Needs Review — added from a targeted review pass.** A second, narrowly-scoped look at a source line no rule initially cited produced this rule; the call itself succeeded normally, but verify it against the source since it covers a line the first pass did not.

**Affected Field:** `Target.AccountId, Source.AccountId, Target.OutstandingBalance, Source.OutstandingBalance, Target.ProvisionAmount, Source.ProvisionAmount, Target.CoverageRatio, Source.CoverageRatio, Target.LastUpdatedDate, AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, FirstSeenDate, LastUpdatedDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge provisioning coverage summary data into the ProvisionCoverageSummary table.

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

If an error occurs during the process execution, the running process status is updated to reflect the error, and the process is marked as not completed.

## Findings / Needs Review

- Lines 26-26 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 70-72 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 76-78 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 2 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
