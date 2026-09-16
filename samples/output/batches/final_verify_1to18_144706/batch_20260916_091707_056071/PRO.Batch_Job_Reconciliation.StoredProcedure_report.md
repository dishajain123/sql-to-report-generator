# Batch Job Reconciliation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Batch_Job_Reconciliation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 2 confident, 2 needs review |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 2 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The Batch_Job_Reconciliation procedure performs reconciliation of batch feeds, determining the outcome and severity of each feed based on row count discrepancies and retry status, and updates various system tables with the results.

## Process Flow

1. Initialize the process by setting the process date and month end date.
2. Create a temporary table to store reconciliation results.
3. Insert initial reconciliation results into the temporary table based on feed data.
4. Update the severity tier of feeds that require a retry.
5. Read from the temporary table to determine the final outcome and severity tier for each feed.
6. Merge reconciliation summary data into the batch reconciliation summary table.
7. Update the severity tier in the batch reconciliation summary table for feeds that have not been reconciled within the last 14 days.
8. Insert records into the batch reconciliation log for feeds that have been reconciled.
9. Insert records into the collections queue for accounts that require escalation.
10. Update the running process status for the batch job reconciliation process.
11. Read from the batch feed registry to determine the outcome and shortfall percentage for each feed.
12. Calculate the outcome and shortfall percentage for each feed based on row count discrepancies and retry status.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine Outcome, ShortfallPct | `Outcome, ShortfallPct` | Compute these fields for the same eligible rows. Each field has its own ordered decision table. |
| ⚠️ Update retry count | `RetryCount` | Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that need to be retried. |
| ⚠️ Merge reconciliation summary | `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate` | Merge reconciliation summary data into the PRO.BatchReconciliationSummary table. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |

## Business Rules

### R1 — Determine Outcome, ShortfallPct

**Affected Field:** `Outcome, ShortfallPct`

Compute these fields for the same eligible rows. Each field has its own ordered decision table.

**Applies to:**

- FeedDate = @ProcessDate

**Source context:**

- Target: #ReconciliationResults
- FROM PRO.BatchFeedRegistry

**Evaluation order (within each field):**

First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

#### Decision Logic — Outcome

- Expression: CASE WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE' WHEN ActualRowCount >= ExpectedRowCount THEN 'RECONCILED' WHEN @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100 > 10 THEN 'FAILED' WHEN COALESCE(RetryCount, 0) = 0 THEN 'RETRY_QUEUED' ELSE 'FAILED' END

| Condition | Result |
|---|---|
| ExpectedRowCount IS NULL OR ExpectedRowCount = 0 | 'NOT_APPLICABLE' |
| ActualRowCount >= ExpectedRowCount | 'RECONCILED' |
| @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100 > 10 | 'FAILED' |
| COALESCE(RetryCount, 0) = 0 | 'RETRY_QUEUED' |
| ELSE | 'FAILED' |

#### Decision Logic — ShortfallPct

- Expression: CASE WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN NULL WHEN ActualRowCount >= ExpectedRowCount THEN 0 ELSE (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100 END

| Condition | Result |
|---|---|
| ExpectedRowCount IS NULL OR ExpectedRowCount = 0 | NULL |
| ActualRowCount >= ExpectedRowCount | 0 |
| ELSE | (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100 |

### R2 — Update retry count

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `RetryCount`

**Applies to:**

- FeedDate matches the process date
- FeedName is in the #ReconciliationResults with Outcome 'RETRY_QUEUED'

**Summary:**

- Update the RetryCount in the BatchFeedRegistry table for feeds that need to be retried.


### R3 — Merge reconciliation summary

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge reconciliation summary data into the BatchReconciliationSummary table.


### R4 — Determine Reason

**Affected Field:** `Reason`


**Applies to:**

- Outcome = 'FAILED'

**Source context:**

- Target: PRO.CollectionsQueue
- FROM #ReconciliationResults
- Expression: CASE WHEN SeverityTier = 'CRITICAL' THEN 'FEED_RECONCILIATION_CRITICAL' ELSE 'FEED_RECONCILIATION_FAILED' END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| SeverityTier = 'CRITICAL' | 'FEED_RECONCILIATION_CRITICAL' |
| ELSE | 'FEED_RECONCILIATION_FAILED' |

## Calculations

### Calculation — Outcome

**Expression:**

```sql
CASE
    WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE'
    WHEN ActualRowCount >= ExpectedRowCount THEN 'RECONCILED'
    WHEN @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS DECIMAL(18,4)) / ExpectedRowCount) * 100 > 10 THEN 'FAILED'
    WHEN ISNULL(RetryCount, 0) = 0 THEN 'RETRY_QUEUED'
    ELSE 'FAILED'
END
```

**Output:**
`#ReconciliationResults.Outcome`

**Used By:**
INSERT INTO #ReconciliationResults

### Calculation — ShortfallPct

**Expression:**

```sql
CASE
    WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN NULL
    WHEN ActualRowCount >= ExpectedRowCount THEN 0
    ELSE (CAST(ExpectedRowCount - ActualRowCount AS DECIMAL(18,4)) / ExpectedRowCount) * 100
END
```

**Output:**
`#ReconciliationResults.ShortfallPct`

**Used By:**
INSERT INTO #ReconciliationResults

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS

### Calculation — Outcome

**Expression:**

```sql
CASE
    WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE'
    WHEN ActualRowCount >= ExpectedRowCount THEN 'RECONCILED'
    WHEN @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100 > 10 THEN 'FAILED'
    WHEN ISNULL(RetryCount, 0) = 0 THEN 'RETRY_QUEUED'
    ELSE 'FAILED'
END
```

**Output:**
`#ReconciliationResults.Outcome`

**Used By:**
INSERT INTO #ReconciliationResults

### Calculation — ShortfallPct

**Expression:**

```sql
CASE
    WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN NULL
    WHEN ActualRowCount >= ExpectedRowCount THEN 0
    ELSE (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100
END
```

**Output:**
`#ReconciliationResults.ShortfallPct`

**Used By:**
INSERT INTO #ReconciliationResults

### Calculation — ShortfallPct

**Expression:**

```sql
(CAST(ExpectedRowCount - ActualRowCount AS DECIMAL(18,4)) / ExpectedRowCount) * 100
```

**Output:**
`Not specified`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.BatchFeedRegistry` | Read + Write | Updates: RetryCount |
| `PRO.BatchReconciliationSummary` | Read + Write | Updates: Target.FeedName, Target.Outcome, Target.ShortfallPct, Target.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn |
| `PRO.BatchReconciliationLog` | Write | Inserts data into: FeedName, Outcome, ReconciledOn |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#ReconciliationResults` | Read + Write | Inserts data into: FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn |

## Exception Handling

If an exception occurs during the batch job reconciliation process, the procedure catches the exception and updates the status of the process to mark it as incomplete, records the error details, and increments the error count.

## Findings / Needs Review

- Lines 27-27 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 96-102 (ASSIGNMENT/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- 3 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
