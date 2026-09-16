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

This procedure updates the risk profile of customers by calculating their utilization ratio, risk score, risk tier, and recommended limit adjustment percentage based on their credit limit, current balance, overdue days, and prior defaults. The updated risk profile is then staged, merged into the risk score history, and logged for audit purposes.

## Process Flow

1. Calculate the utilization ratio for each customer.
2. Calculate the risk score for each customer based on their utilization ratio, overdue days, and prior default count.
3. Determine the risk tier for each customer based on their risk score.
4. Calculate the recommended limit adjustment percentage for each customer based on their risk tier and prior default count.
5. Update the customer risk profile with the calculated values.
6. Insert the customer ID, risk score, and risk tier into the risk score staging table.
7. Merge the risk score history with the latest risk score, risk tier, and scoring date.
8. Insert the customer ID, score date, risk score, and risk tier into the risk score audit log.
9. Update the process status with the completion status and increment the count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Calculate UtilizationRatio | `UtilizationRatio` | Determine the utilization ratio for customers with a non-null and positive credit limit. |
| ⚠️ Calculate RiskScore | `RiskScore` | Determine the risk score for customers based on their overdue days, utilization ratio, and prior defaults. |
| ⚠️ Merge Updated Risk Scores and Tiers into History | `CustomerId, RiskScore, RiskTier, LastScoredDate, FirstScoredDate` | Merge the staged risk scores and tiers into the risk score history. |
| ⚠️ Log Updated Risk Scores and Tiers for Audit | `CustomerId, ScoreDate, RiskScore, RiskTier` | Log the updated risk scores and tiers for audit purposes. |
| ⚠️ Stage Updated Risk Scores and Tiers | `CustomerId, RiskScore, RiskTier` | Stage the updated risk scores and tiers for customers. |

## Business Rules

### R1 — Calculate UtilizationRatio

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Customer has a non-null and positive credit limit

**Summary:**

- Determine the utilization ratio for customers with a non-null and positive credit limit.

### Decision Logic

| Condition | Result |
|---|---|
| CreditLimit IS NOT NULL AND CreditLimit > 0 | CurrentBalance / CreditLimit |


### R2 — Calculate RiskScore

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RiskScore`

**Applies to:**

- Customer has a non-null and positive credit limit

**Summary:**

- Determine the risk score for customers based on their overdue days, utilization ratio, and prior defaults.

### Decision Logic

| Condition | Result |
|---|---|
| CreditLimit IS NOT NULL AND CreditLimit > 0 | (ISNULL(OverdueDays, 0) * 0.5) + (ISNULL(UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(PriorDefaultCount, 0) * 20 * 0.2) |


### R3 — Merge Updated Risk Scores and Tiers into History

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `CustomerId, RiskScore, RiskTier, LastScoredDate, FirstScoredDate`

**Applies to:**

- CustomerId, RiskScore, and RiskTier are present in #RiskScoreStaging

**Summary:**

- Merge the staged risk scores and tiers into the risk score history.


### R4 — Log Updated Risk Scores and Tiers for Audit

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `CustomerId, ScoreDate, RiskScore, RiskTier`

**Applies to:**

- CustomerId, RiskScore, and RiskTier are present in #RiskScoreStaging

**Summary:**

- Log the updated risk scores and tiers for audit purposes.


### R5 — Stage Updated Risk Scores and Tiers

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `CustomerId, RiskScore, RiskTier`

**Applies to:**

- Customer has a non-null risk score

**Summary:**

- Stage the updated risk scores and tiers for customers.

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

### Calculation — RiskTier

**Expression:**

```sql
CASE
    WHEN RiskScore < 20 THEN 'LOW'
    WHEN RiskScore < 50 THEN 'MODERATE'
    WHEN RiskScore < 80 THEN 'HIGH'
    ELSE 'SEVERE'
END
```

**Output:**
`Not specified`

**Used By:**
Not specified


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

The procedure uses a TRY-CATCH block to handle any exceptions that may occur during execution. If an error occurs during the process, the ACLRUNNINGPROCESSSTATUS table is updated to mark the process as failed, record the error date, set the error description to the error message, and increment the count.

## Findings / Needs Review

- Lines 28-32 (ASSIGNMENT/CALCULATION) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 119-121 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 126-128 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 3 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
