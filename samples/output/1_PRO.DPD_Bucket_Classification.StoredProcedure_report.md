# DPD Bucket Classification — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.DPD_Bucket_Classification` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 21 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

The procedure DPD_Bucket_Classification classifies loan accounts into different DPD (Days Past Due) buckets based on the number of days past due and updates related fields accordingly.

## Process Flow

1. Calculate the number of days past due (DpdDays) for loan accounts with a due date.
2. Set DpdDays to zero and DpdBucket to 'NOT_APPLICABLE' for loan accounts without a due date.
3. Classify loan accounts into overdue buckets based on DpdDays.
4. Determine if the account's overdue status has worsened since the last process run.
5. Calculate the penalty interest amount based on the DpdBucket classification.
6. Adjust the penalty interest amount based on the facility type.
7. Stage the adjusted penalty interest amount for further processing.
8. Merge the staged data into the DpdBucket history table.
9. Insert records into the collections queue for accounts that have worsened.
10. Insert records into the DpdBucket audit log for accounts with updated bucket classifications.
11. Update the process status to indicate successful completion or failure.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Calculate DpdDays for due accounts | `DpdDays` | For loan accounts with a due date, calculate the number of days past due based on the process date. |
| Set DpdDays for non-due accounts | `DpdDays, DpdBucket` | For loan accounts without a due date, set the number of days past due to zero and the bucket to 'NOT_APPLICABLE'. |
| Classify accounts into overdue buckets (DpdBucket) | `DpdBucket` | Classify loan accounts into overdue buckets based on the number of days past due. |
| Classify accounts into overdue buckets (A.DpdBucket) | `DpdBucket` | Classify loan accounts into overdue buckets based on the number of days past due. |
| Determine worsened bucket status | `BucketWorsened` | Determine if the account's overdue status has worsened since the last process run. |
| Calculate penalty interest amount (PenalInterestAmount) | `PenalInterestAmount` | Calculate the penalty interest amount for loan accounts based on the overdue bucket classification. |
| Calculate penalty interest amount (A.PenalInterestAmount) | `PenalInterestAmount, AccountId, EscalationDate, Reason` | Calculate the penalty interest amount for loan accounts based on the overdue bucket classification. |
| Calculate penalty interest amount (A.PenalInterestAmount, BucketWorsened, GracePeriodApplied) | `PenalInterestAmount, BucketWorsened, GracePeriodApplied, AccountId, EscalationDate, Reason` | Calculate the penalty interest amount for loan accounts based on the overdue bucket classification. |
| Adjust penalty interest amount by facility type (AdjustedPenalty) | `AdjustedPenalty` | Adjust the penalty interest amount based on the facility type for accounts with worsened status. |
| Adjust penalty interest amount by facility type (S.AdjustedPenalty) | `AdjustedPenalty` | Adjust the penalty interest amount based on the facility type for accounts with worsened status. |
| Stage adjusted penalty interest amount | `AccountId, DpdBucket, FacilityType, AdjustedPenalty` | Stage the adjusted penalty interest amount for further processing. |
| Merge staged data into DpdBucket history | `Target.DpdBucket, Target.AdjustedPenalty, Target.LastUpdatedDate` | Merge the staged data into the DpdBucket history table, updating existing records or inserting new ones. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Determine BucketWorsened | `BucketWorsened` | Not specified |
| Update DpdDays for certain conditions | `DpdDays` | Update the DpdDays field in the PRO.LoanAccountCal table based on specific conditions. |
| Update DpdBucket based on DpdDays and FacilityType | `DpdBucket` | Update the DpdBucket field in the PRO.LoanAccountCal table based on the DpdDays and FacilityType. |
| Update PenalInterestAmount | `PenalInterestAmount` | Update the PenalInterestAmount field in the PRO.LoanAccountCal table. |
| Insert and update records in #DpdStaging | `AccountId, DpdBucket, FacilityType, AdjustedPenalty` | Insert records into the #DpdStaging table and update the AdjustedPenalty field based on certain conditions. |
| Merge records into PRO.DpdBucketHistory | `AccountId, DpdBucket, AdjustedPenalty, LastUpdatedDate` | Merge records into the PRO.DpdBucketHistory table. |
| Insert records into PRO.CollectionsQueue | `AccountId, EscalationDate, Reason` | Insert records into the PRO.CollectionsQueue table. |
| Insert records into PRO.DpdBucketAuditLog | `AccountId, TransitionDate, NewBucket` | Insert records into the PRO.DpdBucketAuditLog table. |

## Business Rules

### R1 — Calculate DpdDays for due accounts

**Affected Field:** `DpdDays`

**Applies to:**

- Loan account has a due date
- Due date is on or before the process date

**Summary:**

- For loan accounts with a due date, calculate the number of days past due based on the process date.

### Decision Logic

| Condition | Result |
|---|---|
| LastPaymentDueDate IS NOT NULL AND LastPaymentDueDate <= @ProcessDate | DATEDIFF(DAY, LastPaymentDueDate, @ProcessDate) |


### R2 — Set DpdDays for non-due accounts

**Affected Field:** `DpdDays, DpdBucket`

**Applies to:**

- Loan account does not have a due date

**Summary:**

- For loan accounts without a due date, set the number of days past due to zero and the bucket to 'NOT_APPLICABLE'.

### Decision Logic

| Condition | Result |
|---|---|
| LastPaymentDueDate IS NULL | 0 |


### R3 — Classify accounts into overdue buckets (DpdBucket)

**Affected Field:** `DpdBucket`

**Summary:**

- Classify loan accounts into overdue buckets based on the number of days past due.

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
| PRO.LoanAccountCal.DpdDays IS NULL | 'NOT_APPLICABLE' |
| PRO.LoanAccountCal.DpdDays = 0 | 'CURRENT' |
| PRO.LoanAccountCal.DpdDays BETWEEN 1 AND 30 | 'BUCKET_1_30' |
| PRO.LoanAccountCal.DpdDays BETWEEN 31 AND 60 | 'BUCKET_31_60' |
| PRO.LoanAccountCal.DpdDays BETWEEN 61 AND 90 | 'BUCKET_61_90' |
| ELSE | 'BUCKET_90_PLUS' |

### R4 — Classify accounts into overdue buckets (A.DpdBucket)

**Affected Field:** `DpdBucket`

**Summary:**

- Classify loan accounts into overdue buckets based on the number of days past due.

### Decision Logic

| Condition | Result |
|---|---|
| DpdDays IS NULL | 'NOT_APPLICABLE' |
| DpdDays = 0 | 'CURRENT' |
| DpdDays BETWEEN 1 AND 30 | 'BUCKET_1_30' |
| DpdDays BETWEEN 31 AND 60 | 'BUCKET_31_60' |
| DpdDays BETWEEN 61 AND 90 | 'BUCKET_61_90' |
| ELSE | 'BUCKET_90_PLUS' |

### R5 — Determine worsened bucket status

**Affected Field:** `BucketWorsened`

**Applies to:**

- Loan account has a previous DpdBucket
- Current DpdBucket differs from previous
- DpdDays have increased since the last run

**Summary:**

- Determine if the account's overdue status has worsened since the last process run.

### Decision Logic

| Condition | Result |
|---|---|
| PrevDpdBucket IS NOT NULL AND DpdBucket <> PrevDpdBucket AND DpdDays > ISNULL(PrevDpdDays, 0) | 'Y' |


### R6 — Calculate penalty interest amount (PenalInterestAmount)

**Affected Field:** `PenalInterestAmount`

**Summary:**

- Calculate the penalty interest amount for loan accounts based on the overdue bucket classification.

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

### R7 — Calculate penalty interest amount (A.PenalInterestAmount)

**Affected Field:** `PenalInterestAmount, AccountId, EscalationDate, Reason`

**Summary:**

- Calculate the penalty interest amount for loan accounts based on the overdue bucket classification.

### Decision Logic

| Condition | Result |
|---|---|
| DpdBucket = 'BUCKET_1_30' | (OutstandingBalance * 0.02) / 365 * DpdDays |
| DpdBucket = 'BUCKET_31_60' | (OutstandingBalance * 0.03) / 365 * DpdDays |
| DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | (OutstandingBalance * 0.04) / 365 * DpdDays; 'SEVERE_DPD_OTHER_FACILITY' |
| ELSE | 0; 'EARLY_DPD_WORSENED' |

### R8 — Calculate penalty interest amount (A.PenalInterestAmount, BucketWorsened, GracePeriodApplied)

**Affected Field:** `PenalInterestAmount, BucketWorsened, GracePeriodApplied, AccountId, EscalationDate, Reason`

**Summary:**

- Calculate the penalty interest amount for loan accounts based on the overdue bucket classification.

### Decision Logic

| Condition | Result |
|---|---|
| DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') | 'SEVERE_DPD_CASH_CREDIT'; Update BucketWorsened and GracePeriodApplied |
| DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | (OutstandingBalance * 0.04) / 365 * DpdDays; 'SEVERE_DPD_OTHER_FACILITY' |
| ELSE | 0; 'EARLY_DPD_WORSENED' |

### R9 — Adjust penalty interest amount by facility type (AdjustedPenalty)

**Affected Field:** `AdjustedPenalty`

**Summary:**

- Adjust the penalty interest amount based on the facility type for accounts with worsened status.

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

### R10 — Adjust penalty interest amount by facility type (S.AdjustedPenalty)

**Affected Field:** `AdjustedPenalty`

**Summary:**

- Adjust the penalty interest amount based on the facility type for accounts with worsened status.

### Decision Logic

| Condition | Result |
|---|---|
| FacilityType IN ('CC', 'OD') | AdjustedPenalty * 1.10 |
| FacilityType IN ('TL', 'DL') | AdjustedPenalty * 1.05 |
| ELSE | AdjustedPenalty |

### R11 — Stage adjusted penalty interest amount

**Affected Field:** `AccountId, DpdBucket, FacilityType, AdjustedPenalty`

**Applies to:**

- Loan account's overdue status has worsened

**Summary:**

- Stage the adjusted penalty interest amount for further processing.

### Decision Logic

| Condition | Result |
|---|---|
| BucketWorsened = 'Y' | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty)<br>        SELECT AccountId, DpdBucket, FacilityType, PenalInterestAmount<br>        FROM LoanAccountCal A |


### R12 — Merge staged data into DpdBucket history

**Affected Field:** `Target.DpdBucket, Target.AdjustedPenalty, Target.LastUpdatedDate`

**Applies to:**

- Staged data exists

**Summary:**

- Merge the staged data into the DpdBucket history table, updating existing records or inserting new ones.

### Decision Logic

| Condition | Result |
|---|---|
| Target.AccountId = Source.AccountId | UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdatedDate = @ProcessDate |
| ELSE | INSERT (AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate)<br>        VALUES (Source.AccountId, Source.DpdBucket, Source.AdjustedPenalty, @ProcessDate, @ProcessDate) |


### R13 — Determine Reason

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

### R14 — Determine BucketWorsened

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


### R15 — Update DpdDays for certain conditions

**Affected Field:** `DpdDays`

**Applies to:**

- DpdDays is greater than 90

**Summary:**

- Update the DpdDays field in the LoanAccountCal table based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| DpdDays > 90 | DpdDays |


### R16 — Update DpdBucket based on DpdDays and FacilityType

**Affected Field:** `DpdBucket`

**Applies to:**

- DpdDays is greater than 90
- FacilityType is 'CC' or 'OD'

**Summary:**

- Update the DpdBucket field in the LoanAccountCal table based on the DpdDays and FacilityType.

### Decision Logic

| Condition | Result |
|---|---|
| DpdDays > 90 AND FacilityType IN ('CC', 'OD') | 'SEVERE_DPD_CASH_CREDIT' |


### R17 — Update PenalInterestAmount

**Affected Field:** `PenalInterestAmount`

**Applies to:**

- PenalInterestAmount is not null

**Summary:**

- Update the PenalInterestAmount field in the LoanAccountCal table.

### Decision Logic

| Condition | Result |
|---|---|
| PenalInterestAmount is not null | Update PenalInterestAmount |


### R18 — Insert and update records in #DpdStaging

**Affected Field:** `AccountId, DpdBucket, FacilityType, AdjustedPenalty`

**Applies to:**

- AccountId, DpdBucket, FacilityType, AdjustedPenalty are not null

**Summary:**

- Insert records into the #DpdStaging table and update the AdjustedPenalty field based on certain conditions.

### Decision Logic

| Condition | Result |
|---|---|
| AccountId, DpdBucket, FacilityType, AdjustedPenalty are not null | Insert and update records in #DpdStaging |


### R19 — Merge records into PRO.DpdBucketHistory

**Affected Field:** `AccountId, DpdBucket, AdjustedPenalty, LastUpdatedDate`

**Applies to:**

- Target.AccountId, Source.AccountId, Target.DpdBucket, Source.DpdBucket, Target.AdjustedPenalty, Source.AdjustedPenalty, Target.LastUpdatedDate, AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate are not null

**Summary:**

- Merge records into the DpdBucketHistory table.

### Decision Logic

| Condition | Result |
|---|---|
| Target.AccountId, Source.AccountId, Target.DpdBucket, Source.DpdBucket, Target.AdjustedPenalty, Source.AdjustedPenalty, Target.LastUpdatedDate, AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate are not null | Merge records into DpdBucketHistory |


### R20 — Insert records into PRO.CollectionsQueue

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- AccountId, EscalationDate, Reason are not null

**Summary:**

- Insert records into the CollectionsQueue table.

### Decision Logic

| Condition | Result |
|---|---|
| AccountId, EscalationDate, Reason are not null | Insert records into CollectionsQueue |


### R21 — Insert records into PRO.DpdBucketAuditLog

**Affected Field:** `AccountId, TransitionDate, NewBucket`

**Applies to:**

- AccountId, TransitionDate, NewBucket are not null

**Summary:**

- Insert records into the DpdBucketAuditLog table.

### Decision Logic

| Condition | Result |
|---|---|
| AccountId, TransitionDate, NewBucket are not null | Insert records into DpdBucketAuditLog |

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

- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic. Affected regions: lines 73-77, 95-95, 162-164, 169-171 (4 total) - needs review after a larger output budget or chunked synthesis.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
