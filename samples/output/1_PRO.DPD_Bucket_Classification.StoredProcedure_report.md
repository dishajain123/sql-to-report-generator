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

The procedure updates the DpdBucketHistory table with the latest DPD bucket classification and adjusted penalty for accounts, based on the data from the #DpdStaging table. This procedure also writes to: CollectionsQueue, DpdBucketAuditLog, LoanAccountCal.

## Process Flow

1. Retrieve the process date from the SysDayMatrix table using the provided TimeKey.
2. Calculate the DPD for loan accounts with a non-null last payment due date that is on or before the process date.
3. Set the DPD to 0 and classify the bucket as 'NOT_APPLICABLE' for loan accounts with a null last payment due date.
4. Update the DpdBucket field in the LoanAccountCal table based on the number of DpdDays for each loan account.
5. Calculate the PenalInterestAmount for each loan account based on its DPD bucket and outstanding balance.
6. Update the BucketWorsened and GracePeriodApplied fields in the LoanAccountCal table for accounts with a LastPaymentDueDate on or after the GraceWindowStart date.
7. If there are accounts with a non-null PrevDpdBucket, update the BucketWorsened field for accounts where the DpdBucket has changed and the DpdDays is greater than the PrevDpdDays.
8. Reset the BucketWorsened flag to 'N' for all loan accounts.
9. Drop the temporary table #DpdStaging if it exists.
10. Create the temporary table #DpdStaging with columns for account ID, DPD bucket, facility type, and adjusted penalty.
11. Insert records into #DpdStaging from PRO.LoanAccountCal.LoanAccountCal where the BucketWorsened flag is 'Y'.
12. Adjust the AdjustedPenalty in #DpdStaging based on the facility type.
13. Update the AdjustedPenalty in #DpdStaging with the calculated values.
14. Merge the data from the #DpdStaging table into the PRO.LoanAccountCal.DpdBucketHistory table.
15. For matching records, update the DpdBucket, AdjustedPenalty, and LastUpdatedDate fields in the PRO.LoanAccountCal.DpdBucketHistory table.
16. Insert records into the CollectionsQueue table for accounts that have worsened to a severe DPD bucket, specifying the escalation date and reason.
17. Insert records into the DpdBucketAuditLog table for accounts that have a transition in their DPD bucket on the process date, logging the account ID, transition date, and new bucket.
18. Update the ACLRUNNINGPROCESSSTATUS table to mark the DPD Bucket Classification process as completed and increment the count, resetting error details if successful.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Classify DPD buckets | `DpdBucket` | Classify loan accounts into DPD buckets based on the number of days past due, affecting risk assessment and management. |
| Insert into #DpdStaging | `AccountId, DpdBucket, FacilityType, AdjustedPenalty` | Sets AccountId, DpdBucket, FacilityType, and AdjustedPenalty on DpdStaging to AccountId := PRO.LoanAccountCal.AccountId; DpdBucket := PRO.L… |
| Determine BucketWorsened, GracePeriodApplied | `BucketWorsened, GracePeriodApplied` | Sets BucketWorsened and GracePeriodApplied depending on which of the 3 conditions below applies (g., BucketWorsened := 'N'; GracePeriodAppl… |
| Determine Reason | `Reason` | Sets Reason depending on which of the 3 conditions below applies (g., 'SEVERE_DPD_CASH_CREDIT' when DpdBucket IN ('BUCKET_61_90', 'BUCKET_9… |
| Calculate DPD for accounts with due date | `PRO.LoanAccountCal.DpdDays` | Calculate the number of days past due for loan accounts with a recorded last payment due date that is on or before the process date. |
| Update PenalInterestAmount | `PenalInterestAmount` | Update the PenalInterestAmount in the LoanAccountCal table for each account. |
| Adjust penalty based on facility type | `AdjustedPenalty` | Adjust the AdjustedPenalty in #DpdStaging based on the facility type. |
| Upsert dpdbuckethistory | `DpdBucket, AdjustedPenalty, LastUpdatedDate, AccountId, FirstFlaggedDate` | Update the DpdBucket, AdjustedPenalty, and LastUpdatedDate fields for existing records in the PRO.DpdBucketHistory table. |
| Log DPD bucket transitions | `AccountId, TransitionDate, NewBucket` | Transitions in DPD buckets for accounts on the process date are logged in the DpdBucketAuditLog table. |

## Business Rules

### R1 — Classify DPD buckets

**Affected Field:** `DpdBucket`

**Summary:**

- Classify loan accounts into DPD buckets based on the number of days past due, affecting risk assessment and management.

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

### R2 — Insert into #DpdStaging

**Affected Field:** `AccountId, DpdBucket, FacilityType, AdjustedPenalty`

**Applies to:** eligibility not documented.

**Summary:**

- Sets AccountId, DpdBucket, FacilityType, and AdjustedPenalty on DpdStaging to AccountId := PRO.LoanAccountCal.AccountId; DpdBucket := PRO.LoanAccountCal.DpdBucket; FacilityType := PRO.LoanAccountCal.FacilityType; AdjustedPenalty := PRO.LoanAccountCal.PenalInterestAmount when PRO.LoanAccountCal.BucketWorsened = 'Y'.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.BucketWorsened = 'Y' | AccountId := PRO.LoanAccountCal.AccountId; DpdBucket := PRO.LoanAccountCal.DpdBucket; FacilityType := PRO.LoanAccountCal.FacilityType; AdjustedPenalty := PRO.LoanAccountCal.PenalInterestAmount |


### R3 — Determine BucketWorsened, GracePeriodApplied

**Affected Field:** `BucketWorsened, GracePeriodApplied`

**Summary:**

- Sets BucketWorsened and GracePeriodApplied depending on which of the 3 conditions below applies (g., BucketWorsened := 'N'; GracePeriodApplied := 'Y' when EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart)).

### Decision Logic

| Condition | Result |
|---|---|
| EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) — row filter: PRO.LoanAccountCal.LastPaymentDueDate >= @GraceWindowStart | BucketWorsened := 'N'; GracePeriodApplied := 'Y' |
| EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) — row filter: PRO.LoanAccountCal.PrevDpdBucket IS NOT NULL AND PRO.LoanAccountCal.DpdBucket <> PRO.LoanAccountCal.PrevDpdBucket AND PRO.LoanAccountCal.DpdDays > ISNULL(PRO.LoanAccountCal.PrevDpdDays, 0) | BucketWorsened := 'Y' |
| ELSE — applies to all rows (no additional filter) | BucketWorsened := 'N' |

### R4 — Determine Reason

**Affected Field:** `Reason`

**Summary:**

- Sets Reason depending on which of the 3 conditions below applies (g., 'SEVERE_DPD_CASH_CREDIT' when DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD')).

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

- Calculate the number of days past due for loan accounts with a recorded last payment due date that is on or before the process date.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.LastPaymentDueDate IS NOT NULL AND PRO.LoanAccountCal.LastPaymentDueDate <= @ProcessDate | DATEDIFF(DAY, PRO.LoanAccountCal.LastPaymentDueDate, @ProcessDate) |


### R6 — Update PenalInterestAmount

**Affected Field:** `PenalInterestAmount`

**Summary:**

- Update the PenalInterestAmount in the LoanAccountCal table for each account.

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

### R7 — Adjust penalty based on facility type

**Affected Field:** `AdjustedPenalty`

**Summary:**

- Adjust the AdjustedPenalty in #DpdStaging based on the facility type.

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

- Transitions in DPD buckets for accounts on the process date are logged in the DpdBucketAuditLog table.

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
| `PRO.DpdBucketHistory` | Read + Write | Provides: PRO.LoanAccountCal.DpdBucket, PRO.LoanAccountCal.AdjustedPenalty, PRO.LoanAccountCal.LastUpdatedDate, AccountId, FirstFlaggedDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.DpdBucketAuditLog` | Write | Inserts data into: AccountId, TransitionDate, NewBucket |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#DpdStaging` | Read + Write | Inserts data into: AccountId, DpdBucket, FacilityType, AdjustedPenalty |

## Exception Handling

If an error occurs during the DPD Bucket Classification process, the process is marked as not completed, the error date and description are recorded, and the count is incremented.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
