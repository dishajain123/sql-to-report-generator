# DPD Bucket Classification — Business Logic Report

> **⚠ DEGRADED RUN — POSSIBLY INCOMPLETE**
> 1 rule synthesis section(s) failed after retries and were excluded rather than aborting the whole run. This report may be missing evidence or business rules from the affected portion of the source. Re-run to attempt full coverage.

## At a Glance

| | |
|---|---|
| Procedure | `PRO.DPD_Bucket_Classification` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 9 confident, 2 needs review |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 2 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The DPD_Bucket_Classification procedure identifies loan accounts whose delinquency bucket has worsened on the processing date, records escalation actions, audits the bucket transition, and updates the batch‑run status to indicate success or failure.

## Process Flow

1. Retrieve accounts from PRO.DpdBucketHistory where the bucket was updated on the current processing date.
2. Insert a row for each retrieved account into PRO.CollectionsQueue to trigger collection escalation.
3. Insert a row for each retrieved account into PRO.DpdBucketAuditLog to capture the bucket transition.
4. Mark the batch run as completed in PRO.ACLRUNNINGPROCESSSTATUS; on error, record the failure details.
5. (Earlier in the procedure) Update the loan account record with the new DPD bucket and any penal interest amount (logic not captured in the extraction).

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine DpdBucket | `DpdBucket` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine PenalInterestAmount | `PenalInterestAmount` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine BucketWorsened | `BucketWorsened` | Not specified |
| Determine AdjustedPenalty | `AdjustedPenalty` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Set AccountId in DPD history | `AccountId` | When the procedure runs, the account identifier from the source data is written to the DpdBucketHistory record. |
| Set DPD Bucket in DPD history | `DpdBucket` | When the procedure runs, the delinquency bucket value from the source data is stored in the DpdBucketHistory record. |
| Set Adjusted Penalty in DPD history | `AdjustedPenalty` | When the procedure runs, the adjusted penalty amount from the source data is recorded in the DpdBucketHistory table. |
| Set First Flagged Date in DPD history | `FirstFlaggedDate` | When the procedure runs, the date the account was first flagged for the current DPD bucket is stored in the DpdBucketHistory record. |
| ⚠️ Update DPD bucket value | `DpdBucket` | When a matching account is found, the DPD bucket classification is refreshed to the value supplied in the staging record. |
| ⚠️ Update adjusted penalty amount | `AdjustedPenalty` | When a matching account is found, the adjusted penalty amount is refreshed to the value supplied in the staging record. |

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

### R6 — Set AccountId in DPD history

**Affected Field:** `AccountId`

**Applies to:** eligibility not documented.

**Summary:**

- When the procedure runs, the account identifier from the source data is written to the DpdBucketHistory record.


### R7 — Set DPD Bucket in DPD history

**Affected Field:** `DpdBucket`

**Applies to:** eligibility not documented.

**Summary:**

- When the procedure runs, the delinquency bucket value from the source data is stored in the DpdBucketHistory record.


### R8 — Set Adjusted Penalty in DPD history

**Affected Field:** `AdjustedPenalty`

**Applies to:** eligibility not documented.

**Summary:**

- When the procedure runs, the adjusted penalty amount from the source data is recorded in the DpdBucketHistory table.


### R9 — Set First Flagged Date in DPD history

**Affected Field:** `FirstFlaggedDate`

**Applies to:** eligibility not documented.

**Summary:**

- When the procedure runs, the date the account was first flagged for the current DPD bucket is stored in the DpdBucketHistory record.


### R10 — Update DPD bucket value

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `DpdBucket`

**Applies to:** eligibility not documented.

**Summary:**

- When a matching account is found, the DPD bucket classification is refreshed to the value supplied in the staging record.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | Source.DpdBucket |
| WHEN NOT MATCHED BY TARGET | Source.DpdBucket |


### R11 — Update adjusted penalty amount

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AdjustedPenalty`

**Applies to:** eligibility not documented.

**Summary:**

- When a matching account is found, the adjusted penalty amount is refreshed to the value supplied in the staging record.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | Source.AdjustedPenalty |
| WHEN NOT MATCHED BY TARGET | Source.AdjustedPenalty |

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

### Calculation — DpdDays

**Expression:**

```sql
DATEDIFF(DAY, CAST(LastPaymentDueDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2))
```

**Output:**
`DpdDays`

**Used By:**
Not specified

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
`PenalInterestAmount`

**Used By:**
Not specified

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
`AdjustedPenalty`

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

If any statement within the TRY block raises an error, the procedure records the failure by setting COMPLETED to 'N', storing the current date in ERRORDATE, capturing the system error message in ERRORDESCRIPTION, and still increments the run COUNT. The batch then exits the TRY block and proceeds to the CATCH handling.

## Findings / Needs Review

- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic. Affected regions: lines 27-31, 34-38, 41-53, 73-77, 81-86 (+2 more) (7 total) - needs review after a larger output budget or chunked synthesis.
- The extraction does not include the source table or the MERGE ON clause, so the matching logic for updates versus inserts cannot be determined.
- No explicit eligibility or conditional logic is present in the extraction, leaving the trigger conditions for the MERGE operation unspecified.
- The exact business rules that determine the new DPD bucket (A.DpdBucket) and the penal interest amount (A.PenalInterestAmount) are not present in the extracted data; they are inferred only from statement dependencies.
- The source extraction does not provide the WHERE predicates (if any) governing the INSERTs into PRO.CollectionsQueue and PRO.DpdBucketAuditLog, so eligibility conditions for those inserts are assumed to be unconditional.
- 5 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
