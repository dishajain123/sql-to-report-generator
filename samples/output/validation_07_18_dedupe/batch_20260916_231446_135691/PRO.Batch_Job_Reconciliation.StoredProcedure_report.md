# Batch Job Reconciliation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Batch_Job_Reconciliation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 7 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

The Batch_Job_Reconciliation procedure reconciles batch feed data for a specific time key, determining the outcome and shortfall percentage for each feed and updating the reconciliation results accordingly. This procedure also writes to: BatchFeedRegistry, BatchReconciliationLog, BatchReconciliationSummary, CollectionsQueue, ReconciliationResults.

## Process Flow

1. Retrieve the date corresponding to the provided time key from the SysDayMatrix table.
2. Determine the end date of the month for the retrieved date.
3. Drop the temporary #ReconciliationResults table if it already exists.
4. Create the temporary #ReconciliationResults table to store reconciliation outcomes.
5. Insert reconciliation results into the #ReconciliationResults table based on the batch feed data for the specified date.
6. Read the date information from the SysDayMatrix table for the specified time key.
7. Read the reconciliation results from the #ReconciliationResults.BatchFeedRegistry table for the feeds processed on the specified process date, including the feed name, outcome, shortfall percentage, and process date.
8. Update the RetryCount for batch feeds that need a retry based on reconciliation results.
9. Update the SeverityTier field in the #ReconciliationResults table based on the outcome and shortfall percentage of each reconciliation result.
10. Merge the data from the #ReconciliationResults temporary table into the #ReconciliationResults.BatchReconciliationSummary table.
11. For matched records, update the Outcome, ShortfallPct, SeverityTier, and LastReconciledDate fields in the #ReconciliationResults.BatchReconciliationSummary table with the corresponding values from the #ReconciliationResults table.
12. For unmatched records, insert new records into the #ReconciliationResults.BatchReconciliationSummary table with the FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, and LastReconciledDate fields from the #ReconciliationResults table.
13. Update the severity tier of reconciliation summaries that have not been reconciled and were first reconciled more than 14 days ago.
14. Insert failed reconciliation details into the reconciliation log.
15. Insert details of failed reconciliations into the collections queue.
16. Update the status of the batch job process to completed and increment the count of processed records.
17. Update the status of the batch job reconciliation process to mark it as incomplete and record the current date and error message if an exception occurs.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Upsert batchreconciliationsummary | `Outcome, ShortfallPct, SeverityTier, LastReconciledDate, FeedName, FirstReconciledDate` | Refresh existing rows and insert rows not already present. |
| Determine Outcome, ShortfallPct | `Outcome, ShortfallPct` | Compute these fields for the same eligible rows. Each field has its own ordered decision table. |
| Determine Reason | `Reason` | Not specified |
| Update RetryCount for retry queued feeds | `RetryCount` | Increment the RetryCount for batch feeds that are marked as 'RETRY_QUEUED' in the reconciliation results. |
| Determine SeverityTier | `SeverityTier` | Set the severity tier of a reconciliation result based on its outcome and shortfall percentage. |
| Insert failed reconciliation log | `FeedName, Outcome, ReconciledOn` | Log the details of failed reconciliations into the reconciliation log. |
| Insert collections queue for failed reconciliations | `AccountId, EscalationDate, Reason` | Queue collections for failed reconciliations with the appropriate reason. |

## Business Rules

### R1 — Upsert batchreconciliationsummary

**Affected Field:** `Outcome, ShortfallPct, SeverityTier, LastReconciledDate, FeedName, FirstReconciledDate`

**Applies to:** eligibility not documented.

**Summary:**

- Refresh existing rows and insert rows not already present.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | #ReconciliationResults.Outcome; #ReconciliationResults.ShortfallPct; #ReconciliationResults.SeverityTier; #ReconciliationResults.ReconciledOn |
| WHEN NOT MATCHED BY TARGET | #ReconciliationResults.FeedName; #ReconciliationResults.Outcome; #ReconciliationResults.ShortfallPct; #ReconciliationResults.SeverityTier; #ReconciliationResults.ReconciledOn |


### R2 — Determine Outcome, ShortfallPct

**Affected Field:** `Outcome, ShortfallPct`

Compute these fields for the same eligible rows. Each field has its own ordered decision table.

**Applies to:**

- FeedDate = @ProcessDate

**Source context:**

- Target: #ReconciliationResults
- FROM #ReconciliationResults.BatchFeedRegistry

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

### R3 — Determine Reason

**Affected Field:** `Reason`


**Applies to:**

- Outcome = 'FAILED'

**Source context:**

- Target: #ReconciliationResults.CollectionsQueue
- FROM #ReconciliationResults
- Expression: CASE WHEN SeverityTier = 'CRITICAL' THEN 'FEED_RECONCILIATION_CRITICAL' ELSE 'FEED_RECONCILIATION_FAILED' END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| SeverityTier = 'CRITICAL' | 'FEED_RECONCILIATION_CRITICAL' |
| ELSE | 'FEED_RECONCILIATION_FAILED' |

### R4 — Update RetryCount for retry queued feeds

**Affected Field:** `RetryCount`

**Applies to:**

- The batch feed date matches the process date
- The batch feed name is in the reconciliation results with an outcome of 'RETRY_QUEUED'

**Summary:**

- Increment the RetryCount for batch feeds that are marked as 'RETRY_QUEUED' in the reconciliation results.

### Decision Logic

| Condition | Result |
|---|---|
| FeedDate = @ProcessDate AND FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED') | 1 |


### R5 — Determine SeverityTier

**Affected Field:** `SeverityTier`

**Summary:**

- Set the severity tier of a reconciliation result based on its outcome and shortfall percentage.

**Source context:**

- Target: #ReconciliationResults
- FROM #ReconciliationResults

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| Outcome = 'RECONCILED' | 'NONE' |
| Outcome = 'NOT_APPLICABLE' | 'NONE' |
| Outcome = 'RETRY_QUEUED' | 'WATCH' |
| Outcome = 'FAILED' AND ShortfallPct > 25 | 'CRITICAL' |
| Outcome = 'FAILED' | 'HIGH' |
| ELSE | 'UNKNOWN' |

### R6 — Insert failed reconciliation log

**Affected Field:** `FeedName, Outcome, ReconciledOn`

**Applies to:**

- Reconciliation outcome is 'FAILED'

**Summary:**

- Log the details of failed reconciliations into the reconciliation log.


### R7 — Insert collections queue for failed reconciliations

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- Reconciliation outcome is 'FAILED'

**Summary:**

- Queue collections for failed reconciliations with the appropriate reason.

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
| `PRO.BatchReconciliationSummary` | Read + Write | Updates: #ReconciliationResults.BatchReconciliationSummary.Outcome, #ReconciliationResults.BatchReconciliationSummary.ShortfallPct, #ReconciliationResults.BatchReconciliationSummary.SeverityTier, #ReconciliationResults.BatchReconciliationSummary.LastReconciledDate, FeedName, FirstReconciledDate |
| `PRO.BatchReconciliationLog` | Write | Inserts data into: FeedName, Outcome, ReconciledOn |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#ReconciliationResults` | Read + Write | Inserts data into: FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn |

## Exception Handling

If an error occurs during the batch job reconciliation process, the procedure updates the status to mark the process as incomplete and records the current date, error message, and increments the error count.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
