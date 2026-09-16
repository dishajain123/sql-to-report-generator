# DPD Bucket Classification — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.DPD_Bucket_Classification` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 8 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

The procedure calculates overdue days and updates the overdue penalty for loan accounts based on the overdue days and the account's overdue bucket. It also updates the account's overdue bucket based on the overdue days and flags accounts that have worsened in their overdue status. Additionally, it stages and updates adjusted penalties for certain facility types and inserts records into audit and collections queue tables.

## Process Flow

1. Calculate overdue days for accounts with a last payment due date.
2. Set overdue days to zero and overdue bucket to 'NOT_APPLICABLE' for accounts without a last payment due date.
3. Update the overdue bucket based on the overdue days.
4. Flag accounts that have worsened in their overdue status.
5. Calculate the overdue penalty based on the overdue bucket.
6. Adjust the penalty for certain facility types.
7. Stage adjusted penalties into a temporary table.
8. Merge staged penalties into the overdue bucket history table.
9. Insert records into the collections queue for accounts that have worsened.
10. Insert records into the overdue bucket audit log for accounts with a recent update.
11. Update the process status to indicate completion or failure.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine BucketWorsened | `BucketWorsened` | Not specified |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Calculate overdue days | `DpdDays` | Determine the number of days past due for accounts with a last payment due date. |
| Set overdue days to zero | `DpdDays, DpdBucket` | For accounts without a last payment due date, set the overdue days to zero. |
| Update overdue bucket (DpdBucket) | `DpdBucket` | Classify accounts into overdue buckets based on the number of overdue days. |
| Update overdue bucket (A.DpdBucket) | `DpdBucket` | Classify accounts into overdue buckets based on the number of overdue days. |
| Flag worsened accounts | `BucketWorsened` | Flag accounts that have worsened in their overdue status. |
| Merge staged penalties | `Target.DpdBucket, Target.AdjustedPenalty, Target.LastUpdatedDate` | Merge staged penalties into the overdue bucket history table. |

## Business Rules

### R1 — Determine BucketWorsened

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


### R2 — Determine Reason

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

### R3 — Calculate overdue days

**Affected Field:** `DpdDays`

**Applies to:**

- Account has a last payment due date
- Last payment due date is on or before the process date

**Summary:**

- Determine the number of days past due for accounts with a last payment due date.

### Decision Logic

| Condition | Result |
|---|---|
| LastPaymentDueDate IS NOT NULL AND LastPaymentDueDate <= @ProcessDate | DATEDIFF(DAY, LastPaymentDueDate, @ProcessDate) |


### R4 — Set overdue days to zero

**Affected Field:** `DpdDays, DpdBucket`

**Applies to:**

- Account does not have a last payment due date

**Summary:**

- For accounts without a last payment due date, set the overdue days to zero.

### Decision Logic

| Condition | Result |
|---|---|
| LastPaymentDueDate IS NULL | 0 |


### R5 — Update overdue bucket (DpdBucket)

**Affected Field:** `DpdBucket`

**Summary:**

- Classify accounts into overdue buckets based on the number of overdue days.

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

### R6 — Update overdue bucket (A.DpdBucket)

**Affected Field:** `DpdBucket`

**Summary:**

- Classify accounts into overdue buckets based on the number of overdue days.

### Decision Logic

| Condition | Result |
|---|---|
| DpdDays IS NULL | 'NOT_APPLICABLE' |
| DpdDays = 0 | 'CURRENT' |
| DpdDays BETWEEN 1 AND 30 | 'BUCKET_1_30' |
| DpdDays BETWEEN 31 AND 60 | 'BUCKET_31_60' |
| DpdDays BETWEEN 61 AND 90 | 'BUCKET_61_90' |
| ELSE | 'BUCKET_90_PLUS' |

### R7 — Flag worsened accounts

**Affected Field:** `BucketWorsened`

**Applies to:**

- Account has a previous overdue bucket
- Current overdue bucket differs from previous
- Current overdue days are greater than previous overdue days

**Summary:**

- Flag accounts that have worsened in their overdue status.

### Decision Logic

| Condition | Result |
|---|---|
| PrevDpdBucket IS NOT NULL AND DpdBucket <> PrevDpdBucket AND DpdDays > ISNULL(PrevDpdDays, 0) | 'Y' |


### R8 — Merge staged penalties

**Affected Field:** `Target.DpdBucket, Target.AdjustedPenalty, Target.LastUpdatedDate`

**Applies to:**

- Staged account matches an existing account in the overdue bucket history table

**Summary:**

- Merge staged penalties into the overdue bucket history table.

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
    (CASE
    WHEN DpdBucket = 'BUCKET_1_30' THEN (OutstandingBalance * 0.02) / 365 * DpdDays
    WHEN DpdBucket = 'BUCKET_31_60' THEN (OutstandingBalance * 0.03) / 365 * DpdDays
    WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') THEN (OutstandingBalance * 0.04) / 365 * DpdDays
    ELSE 0
END)
```

**Output:**
`PRO.LoanAccountCal.PenalInterestAmount`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — AdjustedPenalty

**Expression:**

```sql
    (CASE
    WHEN FacilityType IN ('CC', 'OD') THEN AdjustedPenalty * 1.10
    WHEN FacilityType IN ('TL', 'DL') THEN AdjustedPenalty * 1.05
    ELSE AdjustedPenalty
END)
```

**Output:**
`#DpdStaging.AdjustedPenalty`

**Used By:**
UPDATE #DpdStaging; READ #DpdStaging

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

If an error occurs during the process, the process status is updated to indicate failure with the current date and error message.

## Findings / Needs Review

- Lines 73-77 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 95-95 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 162-164 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 169-171 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Business rule synthesis returned malformed JSON and could not be parsed; the full object needs manual review.
- 7 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
