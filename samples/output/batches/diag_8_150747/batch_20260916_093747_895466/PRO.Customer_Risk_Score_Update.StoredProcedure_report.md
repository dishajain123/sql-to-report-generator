# Customer Risk Score Update — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Customer_Risk_Score_Update` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 18 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure updates the risk profile of customers by calculating their utilization ratio, risk score, risk tier, and recommended limit adjustment percentage based on their credit limit, current balance, overdue days, and prior defaults. The updated risk profile is then staged, merged into the risk score history, and logged for audit purposes.

## Process Flow

1. Read the current date from the SysDayMatrix table.
2. Calculate and update the UtilizationRatio for customers with a non-null and positive CreditLimit.
3. Calculate and update the RiskScore for customers based on overdue days, utilization ratio, and prior defaults.
4. Determine the RiskTier for customers based on the composite RiskScore.
5. Calculate and update the RecommendedLimitAdjustmentPct for customers based on their RiskTier and prior default count.
6. Insert the CustomerId, RiskScore, and RiskTier into the #RiskScoreStaging table.
7. Merge the RiskScoreHistory table with the current RiskScore, RiskTier, and scoring dates.
8. Insert the CustomerId, ScoreDate, RiskScore, and RiskTier into the RiskScoreAuditLog table.
9. Update the ACLRUNNINGPROCESSSTATUS table to mark the process as completed and increment the count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Update UtilizationRatio | `UtilizationRatio` | Set the UtilizationRatio for customers based on their risk profile. |
| Update RiskScore | `RiskScore` | Set the RiskScore for customers based on their risk profile. |
| Calculate Utilization Ratio [1] | `UtilizationRatio` | Determine the utilization ratio for a customer based on their current balance and credit limit. |
| Calculate Risk Score [1] | `RiskScore` | Determine the risk score for a customer based on their overdue days, utilization ratio, and prior default count. |
| Determine RecommendedLimitAdjustmentPct | `RecommendedLimitAdjustmentPct` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Determine RiskTier (RiskTier) | `RiskTier` | First matching row wins; ELSE includes false or NULL predicates. |
| Calculate UtilizationRatio [1] | `UtilizationRatio` | Determine the UtilizationRatio for customers with a non-null and positive CreditLimit. |
| Determine RiskTier (C.RiskTier) | `RiskTier` | Determine the RiskTier for customers based on the composite RiskScore. |
| Calculate Utilization Ratio [2] | `UtilizationRatio` | Determine the utilization ratio for a customer based on their current balance and credit limit. |
| Calculate Utilization Ratio [3] | `UtilizationRatio` | Determine the utilization ratio for customers with a non-null and positive credit limit. |
| Stage Updated Risk Scores and Tiers | `CustomerId, RiskScore, RiskTier` | Stage the updated risk scores and tiers for customers. |
| Merge Updated Risk Scores and Tiers into History | `CustomerId, RiskScore, RiskTier` | Merge the staged risk scores and tiers into the risk score history. |
| Log Updated Risk Scores and Tiers for Audit | `CustomerId, ScoreDate, RiskScore, RiskTier` | Log the updated risk scores and tiers for audit purposes. |
| Calculate Utilization Ratio [4] | `UtilizationRatio` | Determine the utilization ratio for customers with a non-null and positive credit limit. |
| Stage Risk Score and Risk Tier | `Not specified` | Stage the customer's risk score and risk tier for later processing. |
| Merge Risk Score and Risk Tier into History | `Not specified` | Merge the customer's risk score and risk tier into the risk score history. |
| Log Risk Score and Risk Tier | `Not specified` | Log the customer's risk score and risk tier into the risk score audit log. |
| Calculate UtilizationRatio [2] | `UtilizationRatio` | Determine the utilization ratio for each customer by dividing the current balance by the credit limit. |

## Business Rules

### R1 — Update UtilizationRatio

**Affected Field:** `UtilizationRatio`

**Applies to:** eligibility not documented.

**Summary:**

- Set the UtilizationRatio for customers based on their risk profile.


### R2 — Update RiskScore

**Affected Field:** `RiskScore`

**Applies to:** eligibility not documented.

**Summary:**

- Set the RiskScore for customers based on their risk profile.


### R3 — Calculate Utilization Ratio [1]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the utilization ratio for a customer based on their current balance and credit limit.


### R4 — Calculate Risk Score [1]

**Affected Field:** `RiskScore`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the risk score for a customer based on their overdue days, utilization ratio, and prior default count.


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

### R6 — Determine RiskTier (RiskTier)

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

### R7 — Calculate UtilizationRatio [1]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Customer has a non-null and positive CreditLimit

**Summary:**

- Determine the UtilizationRatio for customers with a non-null and positive CreditLimit.


### R8 — Determine RiskTier (C.RiskTier)

**Affected Field:** `RiskTier`

**Summary:**

- Determine the RiskTier for customers based on the composite RiskScore.

### Decision Logic

| Condition | Result |
|---|---|
| RiskScore < 20 | 'LOW' |
| RiskScore < 50 | LOW |
| RiskScore < 80 |  |
| ELSE |  |

### R9 — Calculate Utilization Ratio [2]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Credit limit is not null and greater than zero

**Summary:**

- Determine the utilization ratio for a customer based on their current balance and credit limit.

### Decision Logic

| Condition | Result |
|---|---|
| CreditLimit IS NOT NULL AND CreditLimit > 0 | CurrentBalance / CreditLimit |


### R10 — Calculate Utilization Ratio [3]

**Affected Field:** `UtilizationRatio`

**Applies to:**

- Customer has a non-null and positive credit limit

**Summary:**

- Determine the utilization ratio for customers with a non-null and positive credit limit.


### R11 — Stage Updated Risk Scores and Tiers

**Affected Field:** `CustomerId, RiskScore, RiskTier`

**Applies to:**

- Customer has a non-null risk score

**Summary:**

- Stage the updated risk scores and tiers for customers.


### R12 — Merge Updated Risk Scores and Tiers into History

**Affected Field:** `CustomerId, RiskScore, RiskTier`

**Applies to:**

- Customer has a non-null risk score

**Summary:**

- Merge the staged risk scores and tiers into the risk score history.


### R13 — Log Updated Risk Scores and Tiers for Audit

**Affected Field:** `CustomerId, ScoreDate, RiskScore, RiskTier`

**Applies to:**

- Customer has a non-null risk score

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

The procedure uses a TRY-CATCH block to handle any exceptions that may occur during execution. If an error occurs during the process, the process status is updated to indicate failure, the error date and message are recorded, and the count of attempts is incremented.

## Findings / Needs Review

- Lines 28-32 (ASSIGNMENT/CALCULATION) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 113-117 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- 7 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
