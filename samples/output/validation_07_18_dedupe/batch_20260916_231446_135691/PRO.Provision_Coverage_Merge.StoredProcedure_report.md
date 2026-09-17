# Provision Coverage Merge — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Provision_Coverage_Merge` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 5 |
| Tables read | 4 |
| Tables written | 3 |
| Produces audit trail | Not detected |

## What This Does

The purpose of the Provision_Coverage_Merge procedure is to update or insert records in the ProvisionCoverageSummary table based on the data from the #ProvisionCoverage temporary table, ensuring that the latest provision coverage information is maintained for each account.

## Process Flow

1. Set the process date based on the provided time key.
2. Calculate the start date of the quarter three months prior to the process date.
3. Drop the temporary table if it already exists.
4. Create a temporary table to store account details, outstanding balances, provision amounts, coverage ratios, and review reasons.
5. Insert data into the temporary table from the LoanAccountCal table, calculating the coverage ratio where the outstanding balance is not null.
6. Update the ReviewReason field in the ProvisionCoverage table based on the CoverageRatio.
7. If the process date is after the quarter start date, append '_QUARTER_END' to the ReviewReason for accounts with a CoverageRatio less than 0.6.
8. Merge data from the #ProvisionCoverage temporary table into the ProvisionCoverageSummary table.
9. For matching records, update the OutstandingBalance, ProvisionAmount, CoverageRatio, and LastUpdatedDate fields with the latest values from the #ProvisionCoverage table.
10. Update the BelowThresholdFlag in the ProvisionCoverageSummary table based on the CoverageRatio.
11. Insert records into the CollectionsQueue table for accounts with severe provisioning shortfalls.
12. Update the ACLRUNNINGPROCESSSTATUS table to mark the Provision_Coverage_Merge process as completed and increment the count.
13. Update the status of the running process named 'Provision_Coverage_Merge' to mark it as incomplete and record the current date, error message, and increment the error count if an error occurs.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine ReviewReason | `ReviewReason` | Not specified |
| Insert account details | `CoverageRatio` | Insert account details, outstanding balances, provision amounts, coverage ratios, and review reasons into the temporary table from the Loan… |
| Flag below threshold | `BelowThresholdFlag` | If the CoverageRatio is below 0.5, set the BelowThresholdFlag to 'Y'. Otherwise, set it to 'N'. |
| Update ReviewReason based on CoverageRatio | `ReviewReason` | Update the ReviewReason based on the CoverageRatio. |
| Escalate severe provisioning shortfalls | `Reason` | Insert records into the CollectionsQueue for accounts with a severe provisioning shortfall. |

## Business Rules

### R1 — Determine ReviewReason

**Affected Field:** `ReviewReason`

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| @ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate) — row filter: #ProvisionCoverage.CoverageRatio IS NOT NULL AND #ProvisionCoverage.CoverageRatio < 0.6 | #ProvisionCoverage.ReviewReason + '_QUARTER_END' |
| ELSE — row filter: #ProvisionCoverage.CoverageRatio IS NOT NULL AND #ProvisionCoverage.CoverageRatio < 0.5 | #ProvisionCoverage.ReviewReason |

### R2 — Insert account details

**Affected Field:** `CoverageRatio`

**Summary:**

- Insert account details, outstanding balances, provision amounts, coverage ratios, and review reasons into the temporary table from the LoanAccountCal table where the outstanding balance is not null.

**Applies to:**

- NOT PRO.LoanAccountCal.OutstandingBalance IS NULL

**Source context:**

- Target: #ProvisionCoverage
- FROM PRO.LoanAccountCal
- Expression: CASE WHEN PRO.LoanAccountCal.OutstandingBalance > 0 THEN PRO.LoanAccountCal.ProvisionAmount / PRO.LoanAccountCal.OutstandingBalance ELSE NULL END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| OutstandingBalance > 0 | ProvisionAmount / OutstandingBalance |
| ELSE | NULL |

### R3 — Flag below threshold

**Affected Field:** `BelowThresholdFlag`

**Applies to:**

- CoverageRatio is not null
- LastUpdatedDate matches @ProcessDate

**Summary:**

- If the CoverageRatio is below 0.5, set the BelowThresholdFlag to 'Y'. Otherwise, set it to 'N'.

### Decision Logic

| Condition | Result |
|---|---|
| CoverageRatio < 0.5 | 'Y' |
| CoverageRatio >= 0.5 | 'N' |


### R4 — Update ReviewReason based on CoverageRatio

**Affected Field:** `ReviewReason`

**Summary:**

- Update the ReviewReason based on the CoverageRatio.

**Source context:**

- Target: #ProvisionCoverage
- FROM #ProvisionCoverage

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| CoverageRatio IS NULL | 'NO_BALANCE' |
| CoverageRatio < 0.25 | 'SEVERE_UNDERCOVER' |
| CoverageRatio < 0.5 | 'MODERATE_UNDERCOVER' |
| CoverageRatio >= 0.5 AND CoverageRatio < 1 | 'ADEQUATE' |
| ELSE | 'FULLY_COVERED' |

### R5 — Escalate severe provisioning shortfalls

**Affected Field:** `Reason`

**Summary:**

- Insert records into the CollectionsQueue for accounts with a severe provisioning shortfall.

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
    WHEN PRO.LoanAccountCal.OutstandingBalance > 0 THEN PRO.LoanAccountCal.ProvisionAmount / PRO.LoanAccountCal.OutstandingBalance
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
CASE
    WHEN CoverageRatio IS NULL THEN 'NO_BALANCE'
    WHEN CoverageRatio < 0.25 THEN 'SEVERE_UNDERCOVER'
    WHEN CoverageRatio < 0.5 THEN 'MODERATE_UNDERCOVER'
    WHEN CoverageRatio >= 0.5 AND CoverageRatio < 1 THEN 'ADEQUATE'
    ELSE 'FULLY_COVERED'
END
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — CoverageRatio

**Expression:**

```sql
PRO.LoanAccountCal.ProvisionAmount / PRO.LoanAccountCal.OutstandingBalance
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — ReviewReason

**Expression:**

```sql
#ProvisionCoverage.ReviewReason + '_QUARTER_END'
```

**Output:**
`ReviewReason`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.ProvisionCoverageSummary` | Read + Write | Updates: #ProvisionCoverage.OutstandingBalance, #ProvisionCoverage.ProvisionAmount, #ProvisionCoverage.CoverageRatio, #ProvisionCoverage.LastUpdatedDate, AccountId, FirstSeenDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |
| `PRO.LoanAccountCal` | Read | Provides: PRO.LoanAccountCal.AccountId, PRO.LoanAccountCal.OutstandingBalance, PRO.LoanAccountCal.ProvisionAmount, CASE<br>                   WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.OutstandingBalance<br>                   ELSE NULL<br>               END, NULL |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#ProvisionCoverage` | Read + Write | Inserts data into: AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, ReviewReason |

## Exception Handling

If an error occurs during the execution of the 'Provision_Coverage_Merge' process, the procedure updates the status to mark it as incomplete, records the current date, error message, and increments the error count.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
