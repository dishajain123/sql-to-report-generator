# Customer Risk Score Update — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Customer_Risk_Score_Update` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 19 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Yes — records audit events |

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
| Update UtilizationRatio | `UtilizationRatio` | Set the UtilizationRatio for customers based on their utilization levels. |
| Calculate UtilizationRatio [1] | `UtilizationRatio` | Determine the UtilizationRatio for customers with a non-null and positive CreditLimit. |
| Calculate RiskScore [1] | `RiskScore` | Determine the RiskScore for customers based on overdue days, utilization ratio, and prior defaults. |
| Determine RiskTier | `RiskTier` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine RecommendedLimitAdjustmentPct | `RecommendedLimitAdjustmentPct` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Calculate Utilization Ratio [1] | `UtilizationRatio` | Determine the utilization ratio for a customer by dividing their current balance by their credit limit. |
| Calculate Risk Score [1] | `RiskScore` | Determine the risk score for a customer based on their overdue days, utilization ratio, and prior default count. |
| Calculate Utilization Ratio [2] | `UtilizationRatio` | Determine the utilization ratio for a customer by dividing their current balance by their credit limit. |
| Calculate Risk Score [2] | `RiskScore` | Determine the risk score for a customer by combining their overdue days, utilization ratio, and prior default count. |
| Calculate Utilization Ratio [3] | `UtilizationRatio` | Determine the utilization ratio for customers with a non-null and positive credit limit. |
| Stage Updated Risk Scores and Tiers | `Not specified` | Stage the updated risk scores and tiers for customers. |
| Merge Updated Risk Scores and Tiers into History | `Not specified` | Merge the staged risk scores and tiers into the risk score history. |
| Log Updated Risk Scores and Tiers for Audit | `Not specified` | Log the updated risk scores and tiers for audit purposes. |
| Calculate Utilization Ratio [4] | `UtilizationRatio` | Determine the utilization ratio for customers with a non-null and positive credit limit. |
| Stage Risk Score and Risk Tier | `Not specified` | Stage the customer's risk score and risk tier for later processing. |
| Merge Risk Score and Risk Tier into History | `Not specified` | Merge the customer's risk score and risk tier into the risk score history. |
| Log Risk Score and Risk Tier | `Not specified` | Log the customer's risk score and risk tier into the risk score audit log. |
| Calculate UtilizationRatio [2] | `UtilizationRatio` | Determine the utilization ratio for each customer by dividing the current balance by the credit limit. |
| Calculate RiskScore [2] | `RiskScore` | Calculate the risk score for each customer based on overdue days, utilization ratio, and prior defaults. |

## Business Rules

### R1 — Update UtilizationRatio

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Customer has a UtilizationRatio

**Summary:**

- Set the UtilizationRatio for customers based on their utilization levels.

### Decision Logic

| Condition | Result |
|---|---|
| UtilizationRatio < 0.5 | 0.5 |
| UtilizationRatio >= 0.5 AND UtilizationRatio < 0.75 | 0.75 |
| UtilizationRatio >= 0.75 | 1.0 |


### R2 — Calculate UtilizationRatio [1]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Customer has a non-null and positive CreditLimit

**Summary:**

- Determine the UtilizationRatio for customers with a non-null and positive CreditLimit.


### R3 — Calculate RiskScore [1]

**Affected Field:** `RiskScore`

**Applies to:**

- Customer has a non-null and positive CreditLimit

**Summary:**

- Determine the RiskScore for customers based on overdue days, utilization ratio, and prior defaults.


### R4 — Determine RiskTier

**Affected Field:** `RiskTier`


**Source context:**

- Target: PRO.CustomerRiskProfile
- FROM PRO.CustomerRiskProfile AS C

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.CustomerRiskProfile.RiskScore < 20 | 'LOW' |
| PRO.CustomerRiskProfile.RiskScore < 50 | 'MODERATE' |
| PRO.CustomerRiskProfile.RiskScore < 80 | 'HIGH' |
| ELSE | 'SEVERE' |

### R5 — Determine RecommendedLimitAdjustmentPct

**Affected Field:** `RecommendedLimitAdjustmentPct`


**Source context:**

- IF @ProcessDate >= @ReviewCycleStart is true
- Target: PRO.CustomerRiskProfile
- FROM PRO.CustomerRiskProfile AS C
- Expression: CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN COALESCE(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEVERE' THEN -40 ELSE 0 END

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

### R6 — Calculate Utilization Ratio [1]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the utilization ratio for a customer by dividing their current balance by their credit limit.

### Decision Logic

| Condition | Result |
|---|---|
| CreditLimit IS NOT NULL AND CreditLimit > 0 | CurrentBalance / CreditLimit |


### R7 — Calculate Risk Score [1]

**Affected Field:** `RiskScore`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the risk score for a customer based on their overdue days, utilization ratio, and prior default count.

### Decision Logic

| Condition | Result |
|---|---|
| CreditLimit IS NOT NULL AND CreditLimit > 0 | (COALESCE(OverdueDays, 0) * 0.5) + (COALESCE(UtilizationRatio, 0) * 100 * 0.3) + (COALESCE(PriorDefaultCount, 0) * 20 * 0.2) |


### R8 — Calculate Utilization Ratio [2]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the utilization ratio for a customer by dividing their current balance by their credit limit.


### R9 — Calculate Risk Score [2]

**Affected Field:** `RiskScore`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the risk score for a customer by combining their overdue days, utilization ratio, and prior default count.


### R10 — Calculate Utilization Ratio [3]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Customer has a non-null and positive credit limit

**Summary:**

- Determine the utilization ratio for customers with a non-null and positive credit limit.


### R11 — Stage Updated Risk Scores and Tiers

**Affected Field:** Not specified

**Applies to:**

- Customer has a non-null risk score

**Summary:**

- Stage the updated risk scores and tiers for customers.


### R12 — Merge Updated Risk Scores and Tiers into History

**Affected Field:** Not specified

**Applies to:**

- Customer has a non-null risk score

**Summary:**

- Merge the staged risk scores and tiers into the risk score history.


### R13 — Log Updated Risk Scores and Tiers for Audit

**Affected Field:** Not specified

**Applies to:**

- Customer has a non-null risk score and risk tier

**Summary:**

- Log the updated risk scores and tiers for audit purposes.


### R14 — Calculate Utilization Ratio [4]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Customer has a non-null and positive credit limit

**Summary:**

- Determine the utilization ratio for customers with a non-null and positive credit limit.


### R15 — Stage Risk Score and Risk Tier

**Affected Field:** Not specified

**Applies to:**

- Customer has a non-null risk score and risk tier

**Summary:**

- Stage the customer's risk score and risk tier for later processing.


### R16 — Merge Risk Score and Risk Tier into History

**Affected Field:** Not specified

**Applies to:**

- Customer has a non-null risk score and risk tier

**Summary:**

- Merge the customer's risk score and risk tier into the risk score history.


### R17 — Log Risk Score and Risk Tier

**Affected Field:** Not specified

**Applies to:**

- Customer has a non-null risk score and risk tier

**Summary:**

- Log the customer's risk score and risk tier into the risk score audit log.


### R18 — Calculate UtilizationRatio [2]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the utilization ratio for each customer by dividing the current balance by the credit limit.


### R19 — Calculate RiskScore [2]

**Affected Field:** `RiskScore`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Calculate the risk score for each customer based on overdue days, utilization ratio, and prior defaults.

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

The procedure uses a TRY-CATCH block to handle exceptions, but the specific handling steps are not detailed in the extraction. If the process fails, the process status is marked as failed, the error date and message are recorded, and the count is incremented.

## Findings / Needs Review

- Lines 28-32 (ASSIGNMENT/CALCULATION) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 113-117 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The exact conditions for setting UtilizationRatio, RiskScore, RiskTier, and RecommendedLimitAdjustmentPct are not explicitly stated in the extraction.
- 5 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
