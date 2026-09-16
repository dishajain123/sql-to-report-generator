# DPD Bucket Classification — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.DPD_Bucket_Classification` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 16 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

The procedure DPD_Bucket_Classification updates various fields in the PRO.LoanAccountCal table and related tables to classify and manage overdue days past due (DPD) for loan accounts, ensuring compliance with regulatory requirements.

## Process Flow

1. Update the DpdDays field in the LoanAccountCal table.
2. Update the DpdBucket field in the LoanAccountCal table.
3. Update the BucketWorsened and GracePeriodApplied fields in the LoanAccountCal table.
4. Update the PenalInterestAmount field in the LoanAccountCal table.
5. Insert records into the DpdStaging table.
6. Update the AdjustedPenalty field in the DpdStaging table.
7. Merge records into the DpdBucketHistory table.
8. Insert records into the CollectionsQueue table.
9. Insert records into the DpdBucketAuditLog table.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Update DpdBucket (DpdBucket) | `DpdBucket` | Update the DpdBucket field in the LoanAccountCal table based on the number of days past due. |
| Insert into DpdStaging | `AccountId, DpdBucket, FacilityType, AdjustedPenalty` | Insert records into the DpdStaging table. |
| Update AdjustedPenalty in DpdStaging | `AdjustedPenalty` | Update the AdjustedPenalty field in the DpdStaging table. |
| Merge into DpdBucketHistory | `AccountId, DpdBucket, AdjustedPenalty, LastUpdatedDate, FirstFlaggedDate` | Merge records into the DpdBucketHistory table. |
| Insert into CollectionsQueue | `AccountId, EscalationDate, Reason` | Insert records into the CollectionsQueue table. |
| Determine DpdBucket | `DpdBucket` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine BucketWorsened | `BucketWorsened` | Not specified |
| Determine AdjustedPenalty | `AdjustedPenalty` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Calculate DPD days [1] | `DpdDays` | Determine the number of days past due for each loan account where the last payment due date is not null and is less than or equal to the pr… |
| Classify DPD buckets [1] | `DpdBucket` | Assign each loan account to a DPD bucket based on the number of days past due. |
| Calculate DPD days [2] | `DpdDays` | Determine the number of days past due for each loan account. |
| Classify DPD buckets [2] | `DpdBucket` | Classify each loan account into a DPD bucket based on the number of days past due. |
| Update DPD history | `Target.DpdBucket, Target.AdjustedPenalty, Target.LastUpdatedDate` | Merge records from the DpdStaging table into the DpdBucketHistory table. |
| Calculate DpdDays | `DpdDays` | Determine the number of days past due for accounts with a last payment due date. |
| Update DpdBucket (A.DpdBucket) | `DpdBucket` | Classify accounts into DPD buckets based on the number of days past due. |

## Business Rules

### R1 — Update DpdBucket (DpdBucket)

**Affected Field:** `DpdBucket`

**Applies to:**

- DpdDays is greater than 90

**Summary:**

- Update the DpdBucket field in the LoanAccountCal table based on the number of days past due.

### Decision Logic

| Condition | Result |
|---|---|
| DpdDays > 90 | 'BUCKET_90_PLUS' |


### R2 — Insert into DpdStaging

**Affected Field:** `AccountId, DpdBucket, FacilityType, AdjustedPenalty`

**Applies to:**

- AccountId, DpdBucket, FacilityType, AdjustedPenalty are provided

**Summary:**

- Insert records into the DpdStaging table.


### R3 — Update AdjustedPenalty in DpdStaging

**Affected Field:** `AdjustedPenalty`

**Applies to:**

- AdjustedPenalty is provided

**Summary:**

- Update the AdjustedPenalty field in the DpdStaging table.


### R4 — Merge into DpdBucketHistory

**Affected Field:** `AccountId, DpdBucket, AdjustedPenalty, LastUpdatedDate, FirstFlaggedDate`

**Applies to:**

- Target.AccountId, Source.AccountId, Target.DpdBucket, Source.DpdBucket, Target.AdjustedPenalty, Source.AdjustedPenalty, Target.LastUpdatedDate, AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate are provided

**Summary:**

- Merge records into the DpdBucketHistory table.


### R5 — Insert into CollectionsQueue

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- AccountId, EscalationDate, Reason are provided

**Summary:**

- Insert records into the CollectionsQueue table.


### R6 — Determine DpdBucket

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

### R7 — Determine BucketWorsened

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


### R8 — Determine AdjustedPenalty

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

### R9 — Determine Reason

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

### R10 — Calculate DPD days [1]

**Affected Field:** `DpdDays`

**Applies to:**

- LastPaymentDueDate is not null
- LastPaymentDueDate is less than or equal to @ProcessDate

**Summary:**

- Determine the number of days past due for each loan account where the last payment due date is not null and is less than or equal to the process date.

### Decision Logic

| Condition | Result |
|---|---|
| LastPaymentDueDate IS NOT NULL AND LastPaymentDueDate <= @ProcessDate | DATEDIFF(DAY, LastPaymentDueDate, @ProcessDate) |


### R11 — Classify DPD buckets [1]

**Affected Field:** `DpdBucket`

**Applies to:**

- DpdDays is greater than the previous days past due
- DpdBucket is different from the previous bucket

**Summary:**

- Assign each loan account to a DPD bucket based on the number of days past due.

### Decision Logic

| Condition | Result |
|---|---|
| DpdDays <= 30 | 'BUCKET_1_30' |
| DpdDays > 30 AND DpdDays <= 60 | 'BUCKET_31_60' |
| DpdDays > 60 AND DpdDays <= 90 | 'BUCKET_61_90' |
| DpdDays > 90 | 'BUCKET_90_PLUS' |


### R12 — Calculate DPD days [2]

**Affected Field:** `DpdDays`

**Applies to:**

- Account has a last payment due date
- Last payment due date is on or before the process date

**Summary:**

- Determine the number of days past due for each loan account.


### R13 — Classify DPD buckets [2]

**Affected Field:** `DpdBucket`

**Applies to:**

- DPD days have increased since the last update
- Current DPD bucket differs from the previous one

**Summary:**

- Classify each loan account into a DPD bucket based on the number of days past due.


### R14 — Update DPD history

**Affected Field:** `Target.DpdBucket, Target.AdjustedPenalty, Target.LastUpdatedDate`

**Applies to:**

- Records match on account ID

**Summary:**

- Merge records from the DpdStaging table into the DpdBucketHistory table.


### R15 — Calculate DpdDays

**Affected Field:** `DpdDays`

**Applies to:**

- Account has a last payment due date
- Last payment due date is on or before the process date

**Summary:**

- Determine the number of days past due for accounts with a last payment due date.


### R16 — Update DpdBucket (A.DpdBucket)

**Affected Field:** `DpdBucket`

**Applies to:**

- Account has a change in days past due
- Current DPD bucket differs from previous

**Summary:**

- Classify accounts into DPD buckets based on the number of days past due.

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

- Lines 73-77 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic.
- 7 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
