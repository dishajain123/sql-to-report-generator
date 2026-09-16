# Batch Job Reconciliation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Batch_Job_Reconciliation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 10 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

The Batch_Job_Reconciliation procedure performs reconciliation of batch feeds, determining the outcome and severity of each feed based on row count discrepancies and retry status, and updates various system tables with the results.

## Process Flow

1. Read the SysDayMatrix table to get the date for the given TimeKey.
2. Insert initial reconciliation results into the #ReconciliationResults table.
3. Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that need to be retried.
4. Read the #ReconciliationResults table to process feeds with specific outcomes.
5. Update the SeverityTier in the #ReconciliationResults table based on certain conditions.
6. Merge reconciliation summary data into the PRO.BatchReconciliationSummary table.
7. Update the SeverityTier in the PRO.BatchReconciliationSummary table for feeds that have not been reconciled within the last 14 days.
8. Insert records into the PRO.BatchReconciliationLog table to log the outcomes of the reconciliation process.
9. Insert records into the PRO.CollectionsQueue table to escalate certain accounts.
10. Update the status of the batch job in the PRO.ACLRUNNINGPROCESSSTATUS table.
11. Read the PRO.BatchFeedRegistry table to determine the outcome and shortfall percentage for each feed.
12. Calculate the outcome, shortfall percentage, and count for the reconciliation process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Update retry count [1] | `RetryCount` | Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that need to be retried. |
| Merge reconciliation summary [1] | `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate` | Merge reconciliation summary data into the PRO.BatchReconciliationSummary table. |
| Update retry count for feeds | `RetryCount` | Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that need to be retried. |
| Insert collections queue entries | `AccountId, EscalationDate, Reason, SeverityTier, RetryCount, FeedName, Outcome, ReconciledOn` | Insert records into the PRO.CollectionsQueue table for accounts needing escalation due to failed feeds. |
| Determine Outcome, ShortfallPct | `Outcome, ShortfallPct` | Compute these fields for the same eligible rows. Each field has its own ordered decision table. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Merge reconciliation summary [2] | `FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate` | Merge reconciliation summary data into the BatchReconciliationSummary table. |
| Update retry count [2] | `RetryCount` | Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that need to be retried. |
| Merge reconciliation summary (FeedName) | `FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn` | Merge reconciliation summary data from the #ReconciliationResults temporary table into the PRO.BatchReconciliationSummary table. |
| Merge reconciliation summary [3] | `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate` | Merge reconciliation summary data into the PRO.BatchReconciliationSummary table. |

## Business Rules

### R1 — Update retry count [1]

**Affected Field:** `RetryCount`

**Applies to:**

- FeedDate = @ProcessDate
- FeedName is in the set of feeds with outcome 'RETRY_QUEUED'

**Summary:**

- Update the RetryCount in the BatchFeedRegistry table for feeds that need to be retried.


### R2 — Merge reconciliation summary [1]

**Affected Field:** `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge reconciliation summary data into the BatchReconciliationSummary table.


### R3 — Update retry count for feeds

**Affected Field:** `RetryCount`

**Applies to:**

- FeedDate = @ProcessDate
- FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED')

**Summary:**

- Update the RetryCount in the BatchFeedRegistry table for feeds that need to be retried.


### R4 — Insert collections queue entries

**Affected Field:** `AccountId, EscalationDate, Reason, SeverityTier, RetryCount, FeedName, Outcome, ReconciledOn`

**Summary:**

- Insert records into the PRO.CollectionsQueue table for accounts needing escalation due to failed feeds.

### Decision Logic

| Condition | Result |
|---|---|
| Outcome = 'RECONCILED' | NONE |
| Outcome = 'NOT_APPLICABLE' | NONE |
| Outcome = 'RETRY_QUEUED' | CRITICAL; Increment the retry count by 1.; WATCH |
| Outcome = 'FAILED' AND ShortfallPct > 25 | CRITICAL |
| Outcome = 'FAILED' | Insert records into the CollectionsQueue table.; Insert records into the BatchReconciliationLog table.; HIGH |
| ELSE | UNKNOWN |

### R5 — Determine Outcome, ShortfallPct

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

### R6 — Determine Reason

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

### R7 — Merge reconciliation summary [2]

**Affected Field:** `FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate`

**Applies to:**

- The temporary table contains reconciliation results.

**Summary:**

- Merge reconciliation summary data into the BatchReconciliationSummary table.


### R8 — Update retry count [2]

**Affected Field:** `RetryCount`

**Applies to:**

- FeedDate matches the process date
- FeedName is in the #ReconciliationResults with Outcome 'RETRY_QUEUED'

**Summary:**

- Update the RetryCount in the BatchFeedRegistry table for feeds that need to be retried.


### R9 — Merge reconciliation summary (FeedName)

**Affected Field:** `FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn`

**Applies to:** eligibility not documented.

**Summary:**

- Merge reconciliation summary data from the #ReconciliationResults temporary table into the BatchReconciliationSummary table.


### R10 — Merge reconciliation summary [3]

**Affected Field:** `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge reconciliation summary data into the BatchReconciliationSummary table.

## Calculations

### Calculation — Outcome

**Expression:**

```sql
CASE
    WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE'
    WHEN ActualRowCount >= ExpectedRowCount THEN 'RECONCILED'
    WHEN @ProcessDate = @MonthEndDate AND ((ExpectedRowCount - ActualRowCount) / ExpectedRowCount) * 100 > 10 THEN 'FAILED'
    WHEN ISNULL(RetryCount, 0) = 0 THEN 'RETRY_QUEUED'
    ELSE 'FAILED'
END
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — ShortfallPct

**Expression:**

```sql
CASE
    WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN NULL
    WHEN ActualRowCount >= ExpectedRowCount THEN 0
    ELSE ((ExpectedRowCount - ActualRowCount) / ExpectedRowCount) * 100
END
```

**Output:**
`Not specified`

**Used By:**
Not specified

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

### Calculation — Outcome

**Expression:**

```sql
CASE
    WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE'
    WHEN ActualRowCount >= ExpectedRowCount THEN 'RECONCILED'
    WHEN @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100 > 10 THEN 'FAILED'
    WHEN COALESCE(RetryCount, 0) = 0 THEN 'RETRY_QUEUED'
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

If an exception occurs during the batch job reconciliation process, the procedure updates the status of the process to indicate it is not completed, records the error date, captures the error description, and increments the error count.

## Findings / Needs Review

- 6 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
