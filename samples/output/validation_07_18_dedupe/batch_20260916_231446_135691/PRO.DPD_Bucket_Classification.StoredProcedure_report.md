# DPD Bucket Classification — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.DPD_Bucket_Classification` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 9 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

The procedure updates the DpdBucketHistory table with the latest DPD bucket classification and adjusted penalty for each account, based on the data in the #DpdStaging temporary table. This procedure also writes to: CollectionsQueue, DpdBucketAuditLog, LoanAccountCal.

## Process Flow

1. Retrieve the process date from the SysDayMatrix table using the provided TimeKey.
2. Calculate the DPD for loan accounts with a non-null last payment due date that is on or before the process date.
3. Set the DPD to 0 and classify the account as 'NOT_APPLICABLE' for loan accounts with a null last payment due date.
4. Update the DpdBucket field in the PRO.LoanAccountCal.LoanAccountCal table based on the number of DpdDays for each loan account.
5. Calculate the PenalInterestAmount for each loan account based on its DPD bucket and outstanding balance.
6. Update the PenalInterestAmount in the LoanAccountCal table for accounts that have not yet reached the grace period start date.
7. Update the BucketWorsened and GracePeriodApplied fields in the LoanAccountCal table for accounts with a LastPaymentDueDate on or after the GraceWindowStart date.
8. If there are accounts with a non-null PrevDpdBucket, update the BucketWorsened field for accounts where the DpdBucket has changed and the DpdDays is greater than the PrevDpdDays.
9. Reset the BucketWorsened flag to 'N' for all loan accounts.
10. Drop the temporary table #DpdStaging if it exists.
11. Create the temporary table #DpdStaging with columns for account ID, DPD bucket, facility type, and adjusted penalty.
12. Insert records into #DpdStaging from PRO.LoanAccountCal.LoanAccountCal where the BucketWorsened flag is 'Y'.
13. Adjust the penalty amount in #DpdStaging based on the facility type.
14. Merge the data from the #DpdStaging temporary table into the PRO.LoanAccountCal.DpdBucketHistory table.
15. For matching records, update the DpdBucket, AdjustedPenalty, and LastUpdatedDate fields in the PRO.LoanAccountCal.DpdBucketHistory table.
16. Insert records into the CollectionsQueue table for accounts that have worsened to a severe DPD bucket, specifying the escalation date and reason.
17. Insert records into the DpdBucketAuditLog table for accounts that have a DPD bucket transition on the process date, specifying the account ID, transition date, and new bucket.
18. Update the ACLRUNNINGPROCESSSTATUS table to mark the DPD Bucket Classification process as completed and increment the count, resetting error details if successful.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Insert into #DpdStaging | `AccountId, DpdBucket, FacilityType, AdjustedPenalty` | Not specified |
| Determine BucketWorsened, GracePeriodApplied | `BucketWorsened, GracePeriodApplied` | Not specified |
| Determine AdjustedPenalty | `AdjustedPenalty` | Not specified |
| Determine Reason | `Reason` | Not specified |
| Calculate DPD for accounts with due date | `PRO.LoanAccountCal.DpdDays` | For loan accounts with a recorded last payment due date on or before the process date, calculate the number of days past due. |
| Classify DPD bucket | `DpdBucket` | Classify loan accounts into DPD buckets based on the number of days past due. |
| Calculate PenalInterestAmount | `PenalInterestAmount` | Determine the PenalInterestAmount for a loan account based on its DPD bucket and outstanding balance. |
| Upsert dpdbuckethistory | `DpdBucket, AdjustedPenalty, LastUpdatedDate, AccountId, FirstFlaggedDate` | Update the DpdBucket, AdjustedPenalty, and LastUpdatedDate fields for existing records in the PRO.DpdBucketHistory table. |
| Log DPD bucket transitions | `AccountId, TransitionDate, NewBucket` | Insert records into the DpdBucketAuditLog table for accounts that have a DPD bucket transition on the process date. |

## Business Rules

### R1 — Insert into #DpdStaging

**Affected Field:** `AccountId, DpdBucket, FacilityType, AdjustedPenalty`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.BucketWorsened = 'Y' | AccountId := PRO.LoanAccountCal.AccountId; DpdBucket := PRO.LoanAccountCal.DpdBucket; FacilityType := PRO.LoanAccountCal.FacilityType; AdjustedPenalty := PRO.LoanAccountCal.PenalInterestAmount |


### R2 — Determine BucketWorsened, GracePeriodApplied

**Affected Field:** `BucketWorsened, GracePeriodApplied`

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) — row filter: PRO.LoanAccountCal.LastPaymentDueDate >= @GraceWindowStart | BucketWorsened := 'N'; GracePeriodApplied := 'Y' |
| EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) — row filter: PRO.LoanAccountCal.PrevDpdBucket IS NOT NULL AND PRO.LoanAccountCal.DpdBucket <> PRO.LoanAccountCal.PrevDpdBucket AND PRO.LoanAccountCal.DpdDays > ISNULL(PRO.LoanAccountCal.PrevDpdDays, 0) | BucketWorsened := 'Y' |
| ELSE — applies to all rows (no additional filter) | BucketWorsened := 'N' |

### R3 — Determine AdjustedPenalty

**Affected Field:** `AdjustedPenalty`


**Applies to:**

- NOT #DpdStaging.AdjustedPenalty IS NULL

**Source context:**

- Target: #DpdStaging
- FROM #DpdStaging

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| FacilityType IN ('CC', 'OD') | AdjustedPenalty * 1.10 |
| FacilityType IN ('TL', 'DL') | AdjustedPenalty * 1.05 |
| ELSE | AdjustedPenalty |

### R4 — Determine Reason

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

### R5 — Calculate DPD for accounts with due date

**Affected Field:** `PRO.LoanAccountCal.DpdDays`

**Applies to:**

- Loan account has a recorded last payment due date
- Last payment due date is on or before the process date

**Summary:**

- For loan accounts with a recorded last payment due date on or before the process date, calculate the number of days past due.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.LastPaymentDueDate IS NOT NULL AND PRO.LoanAccountCal.LastPaymentDueDate <= @ProcessDate | DATEDIFF(DAY, PRO.LoanAccountCal.LastPaymentDueDate, @ProcessDate) |


### R6 — Classify DPD bucket

**Affected Field:** `DpdBucket`

**Summary:**

- Classify loan accounts into DPD buckets based on the number of days past due.

**Applies to:**

- NOT PRO.LoanAccountCal.LoanAccountCal.DpdDays IS NULL

**Source context:**

- Target: PRO.LoanAccountCal.LoanAccountCal
- FROM PRO.LoanAccountCal.LoanAccountCal

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| DpdDays IS NULL | 'NOT_APPLICABLE' |
| DpdDays = 0 | 'CURRENT' |
| DpdDays BETWEEN 1 AND 30 | 'BUCKET_1_30' |
| DpdDays BETWEEN 31 AND 60 | 'BUCKET_31_60' |
| DpdDays BETWEEN 61 AND 90 | 'BUCKET_61_90' |
| ELSE | 'BUCKET_90_PLUS' |

### R7 — Calculate PenalInterestAmount

**Affected Field:** `PenalInterestAmount`

**Summary:**

- Determine the PenalInterestAmount for a loan account based on its DPD bucket and outstanding balance.

**Source context:**

- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| DpdBucket = 'BUCKET_1_30' | (OutstandingBalance * 0.02) / 365 * DpdDays |
| DpdBucket = 'BUCKET_31_60' | (OutstandingBalance * 0.03) / 365 * DpdDays |
| DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | (OutstandingBalance * 0.04) / 365 * DpdDays |
| ELSE | 0 |

### R8 — Upsert dpdbuckethistory

**Affected Field:** `DpdBucket, AdjustedPenalty, LastUpdatedDate, AccountId, FirstFlaggedDate`

**Applies to:**

- Record exists in PRO.DpdBucketHistory table

**Summary:**

- Update the DpdBucket, AdjustedPenalty, and LastUpdatedDate fields for existing records in the PRO.DpdBucketHistory table.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | #DpdStaging.DpdBucket; #DpdStaging.AdjustedPenalty; @ProcessDate |
| WHEN NOT MATCHED BY TARGET | #DpdStaging.AccountId; #DpdStaging.DpdBucket; #DpdStaging.AdjustedPenalty; @ProcessDate |


### R9 — Log DPD bucket transitions

**Affected Field:** `AccountId, TransitionDate, NewBucket`

**Applies to:**

- Accounts with a DPD bucket transition on the process date

**Summary:**

- Insert records into the DpdBucketAuditLog table for accounts that have a DPD bucket transition on the process date.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.DpdBucketHistory.LastUpdatedDate = @ProcessDate | AccountId := PRO.DpdBucketHistory.AccountId; TransitionDate := @ProcessDate; NewBucket := PRO.DpdBucketHistory.DpdBucket |

## Calculations

### Calculation — DpdDays

**Expression:**

```sql
DATEDIFF(DAY, PRO.LoanAccountCal.LastPaymentDueDate, @ProcessDate)
```

**Output:**
`PRO.LoanAccountCal.DpdDays`

**Used By:**
READ PRO.LoanAccountCal; UPDATE PRO.LoanAccountCal

### Calculation — PenalInterestAmount

**Expression:**

```sql
    (CASE
    WHEN PRO.LoanAccountCal.DpdBucket = 'BUCKET_1_30' THEN (PRO.LoanAccountCal.OutstandingBalance * 0.02) / 365 * PRO.LoanAccountCal.DpdDays
    WHEN PRO.LoanAccountCal.DpdBucket = 'BUCKET_31_60' THEN (PRO.LoanAccountCal.OutstandingBalance * 0.03) / 365 * PRO.LoanAccountCal.DpdDays
    WHEN PRO.LoanAccountCal.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') THEN (PRO.LoanAccountCal.OutstandingBalance * 0.04) / 365 * PRO.LoanAccountCal.DpdDays
    ELSE 0
END)
```

**Output:**
`PRO.LoanAccountCal.PenalInterestAmount`

**Used By:**
READ PRO.LoanAccountCal

### Calculation — AdjustedPenalty

**Expression:**

```sql
    (CASE
    WHEN #DpdStaging.FacilityType IN ('CC', 'OD') THEN #DpdStaging.AdjustedPenalty * 1.10
    WHEN #DpdStaging.FacilityType IN ('TL', 'DL') THEN #DpdStaging.AdjustedPenalty * 1.05
    ELSE #DpdStaging.AdjustedPenalty
END)
```

**Output:**
`#DpdStaging.AdjustedPenalty`

**Used By:**
READ #DpdStaging; UPDATE #DpdStaging

### Calculation — DpdDays

**Expression:**

```sql
DATEDIFF(DAY, CAST(PRO.LoanAccountCal.LastPaymentDueDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2))
```

**Output:**
`DpdDays`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: PRO.LoanAccountCal.DpdDays, PRO.LoanAccountCal.DpdBucket, PRO.LoanAccountCal.PenalInterestAmount, PRO.LoanAccountCal.BucketWorsened, PRO.LoanAccountCal.GracePeriodApplied |
| `PRO.DpdBucketHistory` | Read + Write | Provides: #DpdStaging.DpdBucket, #DpdStaging.AdjustedPenalty, #DpdStaging.LastUpdatedDate, AccountId, FirstFlaggedDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.DpdBucketAuditLog` | Write | Inserts data into: AccountId, TransitionDate, NewBucket |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#DpdStaging` | Read + Write | Inserts data into: AccountId, DpdBucket, FacilityType, AdjustedPenalty |

## Exception Handling

If an error occurs during the DPD Bucket Classification process, the ACLRUNNINGPROCESSSTATUS table is updated to reflect the error, including setting COMPLETED to 'N', ERRORDATE to the current date and time, ERRORDESCRIPTION to the error message, and incrementing the COUNT.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
