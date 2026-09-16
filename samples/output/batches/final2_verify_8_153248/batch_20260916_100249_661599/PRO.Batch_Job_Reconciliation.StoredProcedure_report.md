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

The Batch_Job_Reconciliation procedure processes batch feed data, updates reconciliation results, and logs outcomes for batch feeds. It affects reconciliation results, batch feed registry, and batch reconciliation summary tables.

## Process Flow

1. Read the SysDayMatrix table to get the date for the given TimeKey.
2. Insert initial reconciliation results into the #ReconciliationResults temporary table.
3. Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that are queued for retry.
4. Read reconciliation results from the #ReconciliationResults table for further processing.
5. Update the SeverityTier in the #ReconciliationResults table based on the outcome and shortfall percentage.
6. Merge reconciliation summary data into the PRO.BatchReconciliationSummary table.
7. Update the SeverityTier in the PRO.BatchReconciliationSummary table for feeds that have not been reconciled and are older than 14 days.
8. Insert reconciliation outcomes into the PRO.BatchReconciliationLog table.
9. Insert records into the PRO.CollectionsQueue table for accounts that require escalation.
10. Update the status of the batch job reconciliation process in the PRO.ACLRUNNINGPROCESSSTATUS table.
11. Read the PRO.BatchFeedRegistry table to determine the outcome and shortfall percentage for each feed.
12. Calculate the outcome and shortfall percentage for each feed based on expected and actual row counts.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Merge reconciliation summary [1] | `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate` | Merge reconciliation summary data into the PRO.BatchReconciliationSummary table. |
| Update retry count [1] | `RetryCount` | Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that need to be retried. |
| Merge reconciliation summary [2] | `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate` | Merge reconciliation summary data into the PRO.BatchReconciliationSummary table. |
| Update retry count for feeds | `RetryCount` | Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that need to be retried. |
| Determine Outcome, ShortfallPct | `Outcome, ShortfallPct` | Compute these fields for the same eligible rows. Each field has its own ordered decision table. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Merge reconciliation summary (SeverityTier) | `SeverityTier, Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, FirstReconciledDate, LastReconciledDate` | Merge reconciliation summary data into the batch reconciliation summary table. |
| Update retry count [2] | `RetryCount` | Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that need to be retried. |
| Merge reconciliation summary (FeedName) | `FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn` | Merge reconciliation summary data from the #ReconciliationResults temporary table into the PRO.BatchReconciliationSummary table. |
| Insert collections queue | `AccountId, EscalationDate, Reason` | Insert data into the PRO.CollectionsQueue table for accounts that need escalation. |

## Business Rules

### R1 — Merge reconciliation summary [1]

**Affected Field:** `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge reconciliation summary data into the BatchReconciliationSummary table.


### R2 — Update retry count [1]

**Affected Field:** `RetryCount`

**Applies to:**

- FeedDate = @ProcessDate
- FeedName is in the set of feeds with outcome 'RETRY_QUEUED'

**Summary:**

- Update the RetryCount in the BatchFeedRegistry table for feeds that need to be retried.


### R3 — Merge reconciliation summary [2]

**Affected Field:** `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge reconciliation summary data into the BatchReconciliationSummary table.


### R4 — Update retry count for feeds

**Affected Field:** `RetryCount`

**Applies to:**

- FeedDate = @ProcessDate
- FeedName is in the set of feeds with outcome 'RETRY_QUEUED'

**Summary:**

- Update the RetryCount in the BatchFeedRegistry table for feeds that need to be retried.


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

### R7 — Merge reconciliation summary (SeverityTier)

**Affected Field:** `SeverityTier, Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, FirstReconciledDate, LastReconciledDate`

**Applies to:**

- Outcome is not 'RECONCILED' and FirstReconciledDate is more than 14 days ago

**Summary:**

- Merge reconciliation summary data into the batch reconciliation summary table.


### R8 — Update retry count [2]

**Affected Field:** `RetryCount`

**Applies to:**

- FeedDate matches the process date
- FeedName is in the #ReconciliationResults with Outcome 'RETRY_QUEUED'

**Summary:**

- Update the RetryCount in the BatchFeedRegistry table for feeds that need to be retried.


### R9 — Merge reconciliation summary (FeedName)

**Affected Field:** `FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn`

**Applies to:**

- FeedDate matches the process date
- FeedName is in the #ReconciliationResults with Outcome 'RETRY_QUEUED'

**Summary:**

- Merge reconciliation summary data from the #ReconciliationResults temporary table into the BatchReconciliationSummary table.


### R10 — Insert collections queue

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- AccountId is eligible for escalation

**Summary:**

- Insert data into the CollectionsQueue table for accounts that need escalation.

## Calculations

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

If an exception occurs during the execution of the Batch_Job_Reconciliation procedure, the status of the running process is updated to indicate failure, and the error details are recorded.

## Findings / Needs Review

- Lines 27-27 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- The extraction does not provide specific conditions or outcomes for the update of the SeverityTier field, leading to inferred rules based on the general structure of the SQL statements.
- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
