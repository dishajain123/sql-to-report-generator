# DPD Bucket Classification — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.DPD_Bucket_Classification` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 12 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

The DPD_Bucket_Classification procedure updates the DpdBucketHistory table with the latest DPD bucket classification and adjusted penalty for each account, ensuring the history records reflect the most current status.

## Process Flow

1. Retrieve the process date from the SysDayMatrix table using the provided time key.
2. Update the DpdDays field for loan accounts with a non-null last payment due date that is less than or equal to the process date.
3. Update the DpdDays and DpdBucket fields for loan accounts with a null last payment due date.
4. Update the DpdBucket field in the LoanAccountCal table based on the number of DpdDays for each account.
5. Merge the latest DPD bucket classification and adjusted penalty data from the source into the DpdBucketHistory table, updating existing records or inserting new ones as necessary.
6. Merge the DpdBucketHistory table with the DpdStaging table based on the AccountId.
7. For matched records, update the DpdBucket, AdjustedPenalty, and LastUpdatedDate fields in the DpdBucketHistory table with the corresponding values from the DpdStaging table and set the LastUpdatedDate to the current process date.
8. For unmatched records in the DpdBucketHistory table, insert a new record with the AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, and LastUpdatedDate from the DpdStaging table, all set to the current process date.
9. Insert records into the CollectionsQueue table for accounts with worsened DPD status, categorizing the reason for escalation based on the DPD bucket and facility type.
10. Insert records into the DpdBucketAuditLog table to log the transition of accounts to new DPD buckets.
11. Update the ACLRUNNINGPROCESSSTATUS table to mark the DPD Bucket Classification process as completed and increment the count of processed records.
12. Read the last updated DPD bucket for each account from the DpdBucketHistory table.
13. Update the ACLRUNNINGPROCESSSTATUS table to mark the DPD Bucket Classification process as completed and increment the count if the process runs successfully.
14. If an error occurs during the process, update the ACLRUNNINGPROCESSSTATUS table to mark the process as not completed, record the error date and description, and increment the count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Calculate DpdDays for non-null due dates | `DpdDays` | Calculate the number of days past due for loan accounts with a non-null last payment due date that is less than or equal to the process dat… |
| Determine DpdBucket | `DpdBucket` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine PenalInterestAmount | `PenalInterestAmount` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine BucketWorsened | `BucketWorsened` | Not specified |
| Determine AdjustedPenalty | `AdjustedPenalty` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Classify DPD bucket | `DpdBucket` | Classify loan accounts into DPD buckets based on the number of days past due, affecting the account's risk assessment and management. |
| Update DpdBucketHistory with new values | `DpdBucketHistory, DpdBucket, AdjustedPenalty, LastUpdatedDate` | Update the DpdBucket, AdjustedPenalty, and LastUpdatedDate fields in the DpdBucketHistory table with the latest values from the DpdStaging… |
| Insert new records into DpdBucketHistory | `DpdBucketHistory, AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate` | Insert new records into the DpdBucketHistory table with values from the DpdStaging table for unmatched records. |
| Classify DPD buckets [1] | `CollectionsQueue` | Classify loan accounts into DPD buckets based on the number of days past due and facility type, and escalate severe cases. |
| Classify DPD buckets [2] | `CollectionsQueue` | Classify loan accounts into DPD buckets based on the number of days past due and facility type, and escalate severe cases. |
| Read DPD bucket history | `DpdBucket, AccountId` | Retrieve the last updated DPD bucket for each account from the DpdBucketHistory table. |

## Business Rules

### R1 — Calculate DpdDays for non-null due dates

**Affected Field:** `DpdDays`

**Applies to:**

- Loan account has a non-null last payment due date
- Last payment due date is less than or equal to the process date

**Summary:**

- Calculate the number of days past due for loan accounts with a non-null last payment due date that is less than or equal to the process date.

### Decision Logic

| Condition | Result |
|---|---|
| LastPaymentDueDate IS NOT NULL AND LastPaymentDueDate <= @ProcessDate | DATEDIFF(DAY, LastPaymentDueDate, @ProcessDate) |


### R2 — Determine DpdBucket

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

### R3 — Determine PenalInterestAmount

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

### R4 — Determine BucketWorsened

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


### R5 — Determine AdjustedPenalty

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

### R6 — Determine Reason

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

### R7 — Classify DPD bucket

**Affected Field:** `DpdBucket`

**Summary:**

- Classify loan accounts into DPD buckets based on the number of days past due, affecting the account's risk assessment and management.

### Decision Logic

| Condition | Result |
|---|---|
| DpdDays IS NULL | NOT_APPLICABLE |
| DpdDays = 0 | CURRENT |
| DpdDays BETWEEN 1 AND 30 | BUCKET_1_30 |
| DpdDays BETWEEN 31 AND 60 | BUCKET_31_60 |
| DpdDays BETWEEN 61 AND 90 | BUCKET_61_90 |
| ELSE | BUCKET_90_PLUS |

### R8 — Update DpdBucketHistory with new values

**Affected Field:** `DpdBucketHistory, DpdBucket, AdjustedPenalty, LastUpdatedDate`

**Applies to:**

- Record exists in DpdStaging table

**Summary:**

- Update the DpdBucket, AdjustedPenalty, and LastUpdatedDate fields in the DpdBucketHistory table with the latest values from the DpdStaging table for matched records.

### Decision Logic

| Condition | Result |
|---|---|
| Record exists in both DpdBucketHistory and DpdStaging tables with matching AccountId | Update DpdBucket, AdjustedPenalty, and LastUpdatedDate with values from DpdStaging and current process date |


### R9 — Insert new records into DpdBucketHistory

**Affected Field:** `DpdBucketHistory, AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate`

**Applies to:**

- Record exists in DpdStaging table but not in DpdBucketHistory table

**Summary:**

- Insert new records into the DpdBucketHistory table with values from the DpdStaging table for unmatched records.

### Decision Logic

| Condition | Result |
|---|---|
| Record exists in DpdStaging table but not in DpdBucketHistory table with matching AccountId | Insert new record with values from DpdStaging and current process date |


### R10 — Classify DPD buckets [1]

**Affected Field:** `CollectionsQueue`

**Summary:**

- Classify loan accounts into DPD buckets based on the number of days past due and facility type, and escalate severe cases.

### Decision Logic

| Condition | Result |
|---|---|
| DpdBucket = 'BUCKET_1_30' |  |
| DpdBucket = 'BUCKET_31_60' |  |
| DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | 'SEVERE_DPD_OTHER_FACILITY' |
| ELSE | 'EARLY_DPD_WORSENED' |

### R11 — Classify DPD buckets [2]

**Affected Field:** `CollectionsQueue`

**Summary:**

- Classify loan accounts into DPD buckets based on the number of days past due and facility type, and escalate severe cases.

### Decision Logic

| Condition | Result |
|---|---|
| DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') | 'SEVERE_DPD_CASH_CREDIT' |
| DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | 'SEVERE_DPD_OTHER_FACILITY' |
| ELSE | 'EARLY_DPD_WORSENED' |

### R12 — Read DPD bucket history

**Affected Field:** `DpdBucket, AccountId`

**Applies to:**

- The account's last updated date matches the process date.

**Summary:**

- Retrieve the last updated DPD bucket for each account from the DpdBucketHistory table.

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

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
