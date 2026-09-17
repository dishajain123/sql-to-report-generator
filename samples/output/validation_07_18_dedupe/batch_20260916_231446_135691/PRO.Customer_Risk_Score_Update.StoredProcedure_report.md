# Customer Risk Score Update — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Customer_Risk_Score_Update` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 7 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure updates the risk score and risk tier for customers in the PRO.CustomerRiskProfile table and logs the changes in the PRO.RiskScoreAuditLog table.

## Process Flow

1. Retrieve the process date from the SysDayMatrix table using the provided TimeKey.
2. Calculate the review cycle start date by subtracting one month from the process date.
3. Update the UtilizationRatio field in the CustomerRiskProfile table by dividing the CurrentBalance by the CreditLimit for customers with a non-null and positive CreditLimit.
4. Update the RiskScore field in the CustomerRiskProfile table using a formula that combines the overdue days, utilization ratio, and prior default count.
5. Read the date from the SysDayMatrix table based on the provided TimeKey.
6. Assign a RiskTier in the CustomerRiskProfile table based on the calculated RiskScore.
7. Check if the process date is on or after the review cycle start date.
8. Update the RecommendedLimitAdjustmentPct field in the CustomerRiskProfile table based on the customer's risk tier and prior default count.
9. Drop the temporary table #RiskScoreStaging if it exists.
10. Create the temporary table #RiskScoreStaging with columns CustomerId, RiskScore, and RiskTier.
11. Insert records into #RiskScoreStaging from PRO.CustomerRiskProfile where RiskScore is not null.
12. Update the RecommendedLimitAdjustmentPct field in PRO.CustomerRiskProfile to 0.
13. Merge the risk score and risk tier data from the #RiskScoreStaging table into the PRO.RiskScoreHistory table.
14. Insert a record into the PRO.RiskScoreAuditLog table for customers whose previous risk score is null and current risk score is not null.
15. Update the running process status for 'Customer_Risk_Score_Update' to mark it as completed and increment the count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Assign RiskTier | `RiskTier` | Assign a risk tier based on the calculated risk score. |
| Insert into #RiskScoreStaging | `CustomerId, RiskScore, RiskTier` | Not specified |
| Insert into RiskScoreAuditLog | `CustomerId, ScoreDate, RiskScore, RiskTier` | Not specified |
| Upsert riskscorehistory | `RiskScore, RiskTier, LastScoredDate, CustomerId, FirstScoredDate` | Refresh existing rows and insert rows not already present. |
| Determine RecommendedLimitAdjustmentPct | `RecommendedLimitAdjustmentPct` | Not specified |
| Determine RecommendedLimitAdjustmentPct (PRO.CustomerRiskProfile) | `RecommendedLimitAdjustmentPct` | Not specified |
| Merge risk score history | `RiskScore, RiskTier, LastScoredDate` | Merge the risk score and risk tier data from the #RiskScoreStaging table into the PRO.RiskScoreHistory table. |

## Business Rules

### R1 — Assign RiskTier

**Affected Field:** `RiskTier`

**Summary:**

- Assign a risk tier based on the calculated risk score.

**Source context:**

- Target: PRO.CustomerRiskProfile
- FROM PRO.CustomerRiskProfile

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| RiskScore < 20 | 'LOW' |
| RiskScore < 50 | 'MODERATE' |
| RiskScore < 80 | 'HIGH' |
| ELSE | 'SEVERE' |

### R2 — Insert into #RiskScoreStaging

**Affected Field:** `CustomerId, RiskScore, RiskTier`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| NOT RiskScore IS NULL | CustomerId := CustomerId; RiskScore := RiskScore; RiskTier := RiskTier |


### R3 — Insert into RiskScoreAuditLog

**Affected Field:** `CustomerId, ScoreDate, RiskScore, RiskTier`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| PrevRiskScore IS NULL AND NOT RiskScore IS NULL | CustomerId := CustomerId; ScoreDate := @ProcessDate; RiskScore := RiskScore; RiskTier := RiskTier |


### R4 — Upsert riskscorehistory

**Affected Field:** `RiskScore, RiskTier, LastScoredDate, CustomerId, FirstScoredDate`

**Applies to:** eligibility not documented.

**Summary:**

- Refresh existing rows and insert rows not already present.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | #RiskScoreStaging.RiskScore; #RiskScoreStaging.RiskTier; @ProcessDate |
| WHEN NOT MATCHED BY TARGET | #RiskScoreStaging.CustomerId; #RiskScoreStaging.RiskScore; #RiskScoreStaging.RiskTier; @ProcessDate |


### R5 — Determine RecommendedLimitAdjustmentPct

**Affected Field:** `RecommendedLimitAdjustmentPct`

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| @ProcessDate >= @ReviewCycleStart — applies to all rows (no additional filter) | (nested CASE — see separate decision table) |
| ELSE — applies to all rows (no additional filter) | 0 |

### R6 — Determine RecommendedLimitAdjustmentPct (PRO.CustomerRiskProfile)

**Affected Field:** `RecommendedLimitAdjustmentPct`


**Source context:**

- IF @ProcessDate >= @ReviewCycleStart is true
- Target: PRO.CustomerRiskProfile
- FROM PRO.CustomerRiskProfile
- Expression: CASE WHEN PRO.CustomerRiskProfile.RiskTier = 'LOW' THEN CASE WHEN COALESCE(PRO.CustomerRiskProfile.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN PRO.CustomerRiskProfile.RiskTier = 'MODERATE' THEN 0 WHEN PRO.CustomerRiskProfile.RiskTier = 'HIGH' THEN -15 WHEN PRO.CustomerRiskProfile.RiskTier = 'SEVERE' THEN -40 ELSE 0 END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| (RiskTier = 'LOW') AND (COALESCE(PriorDefaultCount, 0) = 0) | 10 |
| RiskTier = 'LOW' | 0 |
| RiskTier = 'MODERATE' | 0 |
| RiskTier = 'HIGH' | -15 |
| RiskTier = 'SEVERE' | -40 |
| ELSE | 0 |

### R7 — Merge risk score history

**Affected Field:** `RiskScore, RiskTier, LastScoredDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge the risk score and risk tier data from the #RiskScoreStaging table into the PRO.RiskScoreHistory table.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.RiskScoreHistory.CustomerId = #RiskScoreStaging.CustomerId | PRO.RiskScoreHistory.RiskScore = #RiskScoreStaging.RiskScore, PRO.RiskScoreHistory.RiskTier = #RiskScoreStaging.RiskTier, PRO.RiskScoreHistory.LastScoredDate = @ProcessDate |

## Calculations

### Calculation — UtilizationRatio

**Expression:**

```sql
PRO.CustomerRiskProfile.CurrentBalance / PRO.CustomerRiskProfile.CreditLimit
```

**Output:**
`PRO.CustomerRiskProfile.UtilizationRatio`

**Used By:**
READ PRO.CustomerRiskProfile; UPDATE PRO.CustomerRiskProfile

### Calculation — RiskScore

**Expression:**

```sql
(ISNULL(PRO.CustomerRiskProfile.OverdueDays, 0) * 0.5) + (ISNULL(PRO.CustomerRiskProfile.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(PRO.CustomerRiskProfile.PriorDefaultCount, 0) * 20 * 0.2)
```

**Output:**
`PRO.CustomerRiskProfile.RiskScore`

**Used By:**
READ PRO.CustomerRiskProfile

### Calculation — RecommendedLimitAdjustmentPct

**Expression:**

```sql
CASE
    WHEN PRO.CustomerRiskProfile.RiskTier = 'LOW' THEN CASE
    WHEN COALESCE(PRO.CustomerRiskProfile.PriorDefaultCount, 0) = 0 THEN 10
    ELSE 0
END
    WHEN PRO.CustomerRiskProfile.RiskTier = 'MODERATE' THEN 0
    WHEN PRO.CustomerRiskProfile.RiskTier = 'HIGH' THEN -15
    WHEN PRO.CustomerRiskProfile.RiskTier = 'SEVERE' THEN -40
    ELSE 0
END
```

**Output:**
`PRO.CustomerRiskProfile.RecommendedLimitAdjustmentPct`

**Used By:**
READ PRO.CustomerRiskProfile


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.CustomerRiskProfile` | Read + Write | Updates: PRO.CustomerRiskProfile.UtilizationRatio, PRO.CustomerRiskProfile.RiskScore, PRO.CustomerRiskProfile.RiskTier, PRO.CustomerRiskProfile.RecommendedLimitAdjustmentPct |
| `PRO.RiskScoreHistory` | Read + Write | Provides: PRO.CustomerRiskProfile.RiskScore, PRO.CustomerRiskProfile.RiskTier, PRO.CustomerRiskProfile.LastScoredDate, CustomerId, FirstScoredDate |
| `PRO.RiskScoreAuditLog` | Write | Inserts data into: CustomerId, ScoreDate, RiskScore, RiskTier |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#RiskScoreStaging` | Write | Inserts data into: CustomerId, RiskScore, RiskTier |

## Exception Handling

If an error occurs during the execution of the 'Customer_Risk_Score_Update' process, the procedure updates the running process status to mark it as failed, records the error date, sets the error description, and increments the count.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
