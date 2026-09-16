# DPD Bucket Classification — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.DPD_Bucket_Classification` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 10 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

The procedure calculates the Days Past Due (DPD) for each loan account as of the processing date and assigns a NOT_APPLICABLE bucket to accounts that have no recorded due date. This supports timely ageing of loan exposures for regulatory reporting and risk monitoring.

## Process Flow

1. Retrieve the processing date from SysDayMatrix using the supplied TimeKey.
2. For accounts with a non‑null last payment due date that is on or before the processing date, compute DPD as the difference in days between the due date and the processing date.
3. For accounts with a null last payment due date, set DPD to zero and mark the DPD bucket as NOT_APPLICABLE.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Calculate DPD days | `DpdDays` | When an account has a recorded due date on or before the processing date, the system calculates the number of days past due; if no due date… |
| Set DPD bucket for missing due date | `DpdBucket` | If an account lacks a recorded last payment due date, its DPD bucket is marked as NOT_APPLICABLE. |
| Determine DpdBucket | `DpdBucket` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine PenalInterestAmount | `PenalInterestAmount` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine BucketWorsened | `BucketWorsened` | Not specified |
| Determine AdjustedPenalty | `AdjustedPenalty` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Set DPD bucket | `DpdBucket` | When a staging record is processed, the account's DPD bucket classification is stored in the history table, updating an existing record or… |
| Set adjusted penalty | `AdjustedPenalty` | When a staging record is processed, the account's adjusted penalty amount is stored in the history table, updating an existing record or cr… |
| Set first flagged date | `FirstFlaggedDate` | When a new account record is inserted, its FirstFlaggedDate is initialized to the current process date, marking the start of DPD tracking f… |

## Business Rules

### R1 — Calculate DPD days

**Affected Field:** `DpdDays`

**Applies to:**

- Account has a recorded last payment due date on or before the processing date
- Account has no recorded last payment due date

**Summary:**

- When an account has a recorded due date on or before the processing date, the system calculates the number of days past due; if no due date is recorded, the days past due are set to zero.

### Decision Logic

| Condition | Result |
|---|---|
| LastPaymentDueDate IS NOT NULL AND LastPaymentDueDate <= @ProcessDate | DATEDIFF(DAY, LastPaymentDueDate, @ProcessDate) |
| LastPaymentDueDate IS NULL | 0 |


### R2 — Set DPD bucket for missing due date

**Affected Field:** `DpdBucket`

**Applies to:**

- Account has no recorded last payment due date

**Summary:**

- If an account lacks a recorded last payment due date, its DPD bucket is marked as NOT_APPLICABLE.


### R3 — Determine DpdBucket

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

### R4 — Determine PenalInterestAmount

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

### R5 — Determine BucketWorsened

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


### R6 — Determine AdjustedPenalty

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

### R7 — Determine Reason

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

### R8 — Set DPD bucket

**Affected Field:** `DpdBucket`

**Applies to:** eligibility not documented.

**Summary:**

- When a staging record is processed, the account's DPD bucket classification is stored in the history table, updating an existing record or creating a new one.


### R9 — Set adjusted penalty

**Affected Field:** `AdjustedPenalty`

**Applies to:** eligibility not documented.

**Summary:**

- When a staging record is processed, the account's adjusted penalty amount is stored in the history table, updating an existing record or creating a new one.


### R10 — Set first flagged date

**Affected Field:** `FirstFlaggedDate`

**Applies to:** eligibility not documented.

**Summary:**

- When a new account record is inserted, its FirstFlaggedDate is initialized to the current process date, marking the start of DPD tracking for that account.

## Calculations

### Calculation — DpdDays

**Expression:**

```sql
DATEDIFF(DAY, LastPaymentDueDate, @ProcessDate)
```

**Output:**
`PRO.LoanAccountCal.DpdDays`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

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

### Calculation — Reason (CollectionsQueue)

**Expression:**

```sql
CASE
    WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT'
    WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') THEN 'SEVERE_DPD_OTHER_FACILITY'
    ELSE 'EARLY_DPD_WORSENED'
END
```

**Output:**
`PRO.CollectionsQueue.Reason`

**Used By:**
INSERT INTO PRO.CollectionsQueue

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

The procedure encloses its logic in a TRY block but does not define a CATCH block; therefore any runtime error will cause the procedure to abort without custom error handling.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
