# Batch Job Reconciliation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Batch_Job_Reconciliation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 1 confident, 5 needs review |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 5 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The Batch_Job_Reconciliation procedure processes and updates reconciliation results for a given time key, ensuring that the results are correctly categorized and recorded.

## Process Flow

1. Initialize temporary table #ReconciliationResults with feed data for the specified time key.
2. Update the BatchFeedRegistry table to set RetryCount to 1 for feeds marked as 'RETRY_QUEUED'.
3. Update the SeverityTier in #ReconciliationResults based on the outcome of the feed.
4. Merge reconciliation summary data into the BatchReconciliationSummary table.
5. Update the SeverityTier in BatchReconciliationSummary to 'CRITICAL' for feeds not reconciled within the last 14 days.
6. Insert reconciliation log entries into BatchReconciliationLog for feeds with a 'FAILED' outcome.
7. Insert escalation records into CollectionsQueue for feeds with a 'CRITICAL' severity tier.
8. Update the ACLRUNNINGPROCESSSTATUS table to mark the batch job as completed and increment the count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine Outcome, ShortfallPct | `Outcome, ShortfallPct` | Compute these fields for the same eligible rows. Each field has its own ordered decision table. |
| ⚠️ Update retry count | `RetryCount` | Updates the RetryCount in PRO.BatchFeedRegistry to 1 for feeds marked as 'RETRY_QUEUED'. |
| ⚠️ Update severity tier (#ReconciliationResults) | `SeverityTier` | Updates the SeverityTier in #ReconciliationResults based on the outcome of the feed. |
| ⚠️ Update severity tier | `SeverityTier` | Updates the SeverityTier in #ReconciliationResults based on the outcome of the feed. |
| ⚠️ Merge reconciliation summary | `Outcome, FeedName, ShortfallPct, SeverityTier, LastReconciledDate` | Merges reconciliation summary data into the BatchReconciliationSummary table. |
| ⚠️ Insert escalation records | `Reason` | Inserts escalation records into CollectionsQueue for feeds with a 'CRITICAL' severity tier. |

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

- The feed date matches the process date

**Summary:**

- Updates the RetryCount in BatchFeedRegistry to 1 for feeds marked as 'RETRY_QUEUED'.


### R3 — Update severity tier (#ReconciliationResults)

**Affected Field:** `SeverityTier`

**Summary:**

- Updates the SeverityTier in #ReconciliationResults based on the outcome of the feed.

**Source context:**

- Target: #ReconciliationResults
- FROM #ReconciliationResults AS R

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| #ReconciliationResults.Outcome = 'RECONCILED' | 'NONE' |
| #ReconciliationResults.Outcome = 'NOT_APPLICABLE' | 'NONE' |
| #ReconciliationResults.Outcome = 'RETRY_QUEUED' | 'WATCH' |
| #ReconciliationResults.Outcome = 'FAILED' AND #ReconciliationResults.ShortfallPct > 25 | 'CRITICAL' |
| #ReconciliationResults.Outcome = 'FAILED' | 'HIGH' |
| ELSE | 'UNKNOWN' |

### R4 — Update severity tier

**Affected Field:** `SeverityTier`

**Summary:**

- Updates the SeverityTier in #ReconciliationResults based on the outcome of the feed.

### Decision Logic

| Condition | Result |
|---|---|
| Outcome = 'RECONCILED' | 'NONE' |
| Outcome = 'NOT_APPLICABLE' | 'NONE' |
| Outcome = 'RETRY_QUEUED' | 'WATCH' |
| Outcome = 'FAILED' AND ShortfallPct > 25 | 'CRITICAL' |
| Outcome = 'FAILED' | 'HIGH' |
| ELSE | 'UNKNOWN' |

### R5 — Merge reconciliation summary

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `Outcome, FeedName, ShortfallPct, SeverityTier, LastReconciledDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merges reconciliation summary data into the BatchReconciliationSummary table.


### R6 — Insert escalation records

**Affected Field:** `Reason`

**Summary:**

- Inserts escalation records into CollectionsQueue for feeds with a 'CRITICAL' severity tier.

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

### Calculation — ShortfallPct

**Expression:**

```sql
(CAST(ExpectedRowCount - ActualRowCount AS DECIMAL(18,4)) / ExpectedRowCount) * 100
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
    WHEN @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100 > 10 THEN 'FAILED'
    WHEN COALESCE(RetryCount, 0) = 0 THEN 'RETRY_QUEUED'
    ELSE 'FAILED'
END
```

**Output:**
`Outcome`

**Used By:**
Not specified

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
`ShortfallPct`

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

If an exception occurs during the execution of the batch job reconciliation process, the procedure catches the exception and updates the process status to indicate it is not completed, records the current date as the error date, captures the error message, and increments the error count.

## Findings / Needs Review

- Lines 27-27 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 129-131 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 136-138 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
