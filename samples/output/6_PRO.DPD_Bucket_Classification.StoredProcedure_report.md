# DPD Bucket Classification — Business Logic Report

> **⚠ DEGRADED RUN — POSSIBLY INCOMPLETE**
> 1 rule synthesis section(s) failed after retries and were excluded rather than aborting the whole run. This report may be missing evidence or business rules from the affected portion of the source. Re-run to attempt full coverage.

## At a Glance

| | |
|---|---|
| Procedure | `PRO.DPD_Bucket_Classification` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 5 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

Not explicitly determined from source SQL.

## Process Flow

_Not explicitly determined from source SQL._

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine DpdBucket | `DpdBucket` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine PenalInterestAmount | `PenalInterestAmount` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine BucketWorsened | `BucketWorsened` | Not specified |
| Determine AdjustedPenalty | `AdjustedPenalty` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |

## Business Rules

### R1 — Determine DpdBucket

**Affected Field:** `DpdBucket`


**Applies to:**

- NOT PRO.LoanAccountCal.DpdDays IS NULL

**Source context:**

- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.DpdDays IS NULL |  |
| PRO.LoanAccountCal.DpdDays = 0 | 'CURRENT' |
| PRO.LoanAccountCal.DpdDays BETWEEN 1 AND 30 | 'BUCKET_1_30' |
| PRO.LoanAccountCal.DpdDays BETWEEN 31 AND 60 | 'BUCKET_31_60' |
| PRO.LoanAccountCal.DpdDays BETWEEN 61 AND 90 | 'BUCKET_61_90' |
| ELSE | 'BUCKET_90_PLUS' |

### R2 — Determine PenalInterestAmount

**Affected Field:** `PenalInterestAmount`


**Source context:**

- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.DpdBucket = 'BUCKET_1_30' | (PRO.LoanAccountCal.OutstandingBalance * 0.02) / 365 * PRO.LoanAccountCal.DpdDays |
| PRO.LoanAccountCal.DpdBucket = 'BUCKET_31_60' | (PRO.LoanAccountCal.OutstandingBalance * 0.03) / 365 * PRO.LoanAccountCal.DpdDays |
| PRO.LoanAccountCal.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | (PRO.LoanAccountCal.OutstandingBalance * 0.04) / 365 * PRO.LoanAccountCal.DpdDays |
| ELSE | 0 |

### R3 — Determine BucketWorsened

**Affected Field:** `BucketWorsened`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| EXISTS (SELECT 1 FROM LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) — row filter: LastPaymentDueDate >= @GraceWindowStart | 'N' |
| EXISTS (SELECT 1 FROM LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) — row filter: PrevDpdBucket IS NOT NULL AND DpdBucket <> PrevDpdBucket AND DpdDays > ISNULL(PrevDpdDays, 0) | 'Y' |
| ELSE — applies to all rows (no additional filter) | 'N' |


### R4 — Determine AdjustedPenalty

**Affected Field:** `AdjustedPenalty`


**Applies to:**

- NOT #DpdStaging.AdjustedPenalty IS NULL

**Source context:**

- Target: #DpdStaging
- FROM #DpdStaging AS S

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| #DpdStaging.FacilityType IN ('CC', 'OD') | #DpdStaging.AdjustedPenalty * 1.10 |
| #DpdStaging.FacilityType IN ('TL', 'DL') | #DpdStaging.AdjustedPenalty * 1.05 |
| ELSE | #DpdStaging.AdjustedPenalty |

### R5 — Determine Reason

**Affected Field:** `Reason`


**Applies to:**

- BucketWorsened = 'Y'

**Source context:**

- Target: PRO.CollectionsQueue
- FROM PRO.LoanAccountCal
- Expression: CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') THEN 'SEVERE_DPD_OTHER_FACILITY' ELSE 'EARLY_DPD_WORSENED' END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') | 'SEVERE_DPD_CASH_CREDIT' |
| DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | 'SEVERE_DPD_OTHER_FACILITY' |
| ELSE | 'EARLY_DPD_WORSENED' |

## Calculations

### Calculation — DpdDays

**Expression:**

```sql
DATEDIFF(DAY, LastPaymentDueDate, @ProcessDate)
```

**Output:**
`PRO.LoanAccountCal.DpdDays`

**Used By:**
UPDATE PRO.LoanAccountCal

### Calculation — PenalInterestAmount

**Expression:**

```sql
CASE
    WHEN DpdBucket = 'BUCKET_1_30' THEN (OutstandingBalance * 0.02) / 365 * DpdDays
    WHEN DpdBucket = 'BUCKET_31_60' THEN (OutstandingBalance * 0.03) / 365 * DpdDays
    WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') THEN (OutstandingBalance * 0.04) / 365 * DpdDays
    ELSE 0
END
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — AdjustedPenalty

**Expression:**

```sql
CASE
    WHEN FacilityType IN ('CC', 'OD') THEN AdjustedPenalty * 1.10
    WHEN FacilityType IN ('TL', 'DL') THEN AdjustedPenalty * 1.05
    ELSE AdjustedPenalty
END
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — Target.DpdBucket / Target.AdjustedPenalty / Target.LastUpdatedDate (MERGE update)

**Expression:**

```sql
Source.DpdBucket, Source.AdjustedPenalty, @ProcessDate
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — DpdDays

**Expression:**

```sql
DATEDIFF(DAY, CAST(LastPaymentDueDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2))
```

**Output:**
`DpdDays`

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
| `PRO.LoanAccountCal` | Read + Write | Updates: DpdDays, DpdBucket, PenalInterestAmount, BucketWorsened, GracePeriodApplied |
| `PRO.DpdBucketHistory` | Read + Write | Provides: Target.AccountId, Target.DpdBucket, Target.AdjustedPenalty, Target.LastUpdatedDate, FirstFlaggedDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.DpdBucketAuditLog` | Write | Inserts data into: AccountId, TransitionDate, NewBucket |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#DpdStaging` | Read + Write | Inserts data into: AccountId, DpdBucket, FacilityType, AdjustedPenalty |

## Exception Handling

The procedure defines an explicit error handler (`BEGIN CATCH ... END CATCH`). On failure, it runs:

```sql
-- Exception handling: record the failure for operations to investigate
        UPDATE PRO.ACLRUNNINGPROCESSSTATUS
        SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1
        WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification'
```

## Findings / Needs Review

- Lines 27-31 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 34-38 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 41-53 (ASSIGNMENT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 58-62 (ASSIGNMENT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 71-77 (ASSIGNMENT/IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 79-86 (ASSIGNMENT/IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 91-91 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 95-95 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 108-111 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 115-124 (ASSIGNMENT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 128-128 (MERGE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 131-137 (ASSIGNMENT/INSERT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 143-153 (INSERT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 157-160 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
