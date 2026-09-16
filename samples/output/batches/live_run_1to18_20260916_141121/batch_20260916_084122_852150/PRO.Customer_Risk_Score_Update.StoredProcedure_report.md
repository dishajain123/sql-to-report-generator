# Customer Risk Score Update — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Customer_Risk_Score_Update` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 5 needs review |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Yes — records audit events |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 5 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

This procedure calculates and updates the risk profile for customers based on their credit utilization, overdue days, and prior defaults. It also adjusts the recommended credit limit based on the risk tier and prior default count.

## Process Flow

1. Calculate the utilization ratio for each customer.
2. Calculate the risk score for each customer based on overdue days, utilization ratio, and prior defaults.
3. Determine the risk tier for each customer based on the risk score.
4. Calculate the recommended limit adjustment percentage based on the risk tier and prior default count.
5. Stage the risk score and risk tier for each customer.
6. Update the risk score history with the new risk scores and risk tiers.
7. Log the risk score audit for each customer.
8. Update the process status to mark the process as completed.
9. If an error occurs, update the process status to mark the process as failed and log the error.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Calculate Utilization Ratio | `UtilizationRatio` | Determine the utilization ratio for each customer by dividing their current balance by their credit limit. |
| ⚠️ Calculate Risk Score | `RiskScore` | Determine the risk score for each customer based on overdue days, utilization ratio, and prior defaults. |
| ⚠️ Stage Risk Score and Risk Tier | `CustomerId, RiskScore, RiskTier` | Stage the risk score and risk tier for each customer into a temporary table. |
| ⚠️ Update Risk Score History | `Target.RiskScore, Target.RiskTier, Target.LastScoredDate` | Update the risk score history with the new risk scores and risk tiers. |
| ⚠️ Log Risk Score Audit | `CustomerId, ScoreDate, RiskScore, RiskTier` | Log the risk score audit for each customer. |

## Business Rules

### R1 — Calculate Utilization Ratio

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the utilization ratio for each customer by dividing their current balance by their credit limit.

### Decision Logic

| Condition | Result |
|---|---|
| CreditLimit IS NOT NULL AND CreditLimit > 0 | CurrentBalance / CreditLimit |


### R2 — Calculate Risk Score

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RiskScore`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the risk score for each customer based on overdue days, utilization ratio, and prior defaults.

### Decision Logic

| Condition | Result |
|---|---|
| CreditLimit IS NOT NULL AND CreditLimit > 0 | (ISNULL(OverdueDays, 0) * 0.5) + (ISNULL(UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(PriorDefaultCount, 0) * 20 * 0.2) |


### R3 — Stage Risk Score and Risk Tier

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `CustomerId, RiskScore, RiskTier`

**Applies to:**

- Risk score is not null

**Summary:**

- Stage the risk score and risk tier for each customer into a temporary table.


### R4 — Update Risk Score History

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `Target.RiskScore, Target.RiskTier, Target.LastScoredDate`

**Applies to:**

- Customer ID matches in target and source tables

**Summary:**

- Update the risk score history with the new risk scores and risk tiers.


### R5 — Log Risk Score Audit

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `CustomerId, ScoreDate, RiskScore, RiskTier`

**Applies to:**

- Previous risk score is null and risk score is not null

**Summary:**

- Log the risk score audit for each customer.

## Calculations

### Calculation — UtilizationRatio

**Expression:**

```sql
CurrentBalance / CreditLimit
```

**Output:**
`PRO.CustomerRiskProfile.UtilizationRatio`

**Used By:**
UPDATE PRO.CustomerRiskProfile; READ PRO.CustomerRiskProfile

### Calculation — RiskScore

**Expression:**

```sql
(COALESCE(OverdueDays, 0) * 0.5) + (COALESCE(UtilizationRatio, 0) * 100 * 0.3) + (COALESCE(PriorDefaultCount, 0) * 20 * 0.2)
```

**Output:**
`PRO.CustomerRiskProfile.RiskScore`

**Used By:**
UPDATE PRO.CustomerRiskProfile; READ PRO.CustomerRiskProfile

### Calculation — RecommendedLimitAdjustmentPct

**Expression:**

```sql
CASE
    WHEN RiskTier = 'LOW' THEN CASE
    WHEN COALESCE(PriorDefaultCount, 0) = 0 THEN 10
    ELSE 0
END
    WHEN RiskTier = 'MODERATE' THEN 0
    WHEN RiskTier = 'HIGH' THEN -15
    WHEN RiskTier = 'SEVERE' THEN -40
    ELSE 0
END
```

**Output:**
`PRO.CustomerRiskProfile.RecommendedLimitAdjustmentPct`

**Used By:**
UPDATE PRO.CustomerRiskProfile; READ PRO.CustomerRiskProfile

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.CustomerRiskProfile` | Read + Write | Updates: UtilizationRatio, RiskScore, RiskTier, RecommendedLimitAdjustmentPct |
| `PRO.RiskScoreHistory` | Read + Write | Provides: Target.CustomerId, Target.RiskScore, Target.RiskTier, Target.LastScoredDate, FirstScoredDate |
| `PRO.RiskScoreAuditLog` | Write | Inserts data into: CustomerId, ScoreDate, RiskScore, RiskTier |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#RiskScoreStaging` | Write | Inserts data into: CustomerId, RiskScore, RiskTier |

## Exception Handling

If an error occurs during the process, the process status is updated to mark the process as failed and the error is logged.

## Findings / Needs Review

- Lines 28-32 (ASSIGNMENT/CALCULATION) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 119-121 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 126-128 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- The exact conditions for setting UtilizationRatio, RiskScore, RiskTier, and RecommendedLimitAdjustmentPct are not explicitly stated in the extraction.
- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
