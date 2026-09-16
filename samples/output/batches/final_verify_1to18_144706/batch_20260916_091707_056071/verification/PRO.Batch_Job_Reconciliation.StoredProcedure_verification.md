# Batch Job Reconciliation — Verification & Traceability

> Companion artifact to `PRO.Batch_Job_Reconciliation.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_4117700b7512` |
| Raw technical object name (from source) | `Batch_Job_Reconciliation` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `3fde9e2078dcda12` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `6b947b845d4b533c7af2a1c8f7c3fbcf08d427b1dd28c8ffbc62d6a4666f4d2e` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:30:58.312204+00:00` |
| Object ID | `obj_4117700b7512` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_0a6139e78034` |
| Total LLM Calls | `10` |
| Successful Calls | `10` |
| Failed Calls | `0` |
| Prompt Tokens | `125430` |
| Completion Tokens | `24265` |
| Total Tokens | `149695` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 7302 | available |
| synthesis | 7 | 7 | 0 | 76178 | available |
| synthesis_revision | 2 | 2 | 0 | 66215 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| ⚠️ 1 | Insert initial results [CONFLICT] (`rule__2`) | `Outcome, FeedName, ShortfallPct, SeverityTier, ReconciledOn` | Insert initial reconciliation results into the #ReconciliationResults temporary table based on batch feed registry data. |
| ⚠️ 2 | Update retry count [MATCHED] (`rule__3`) | `RetryCount` | Update the RetryCount in the PRO.BatchFeedRegistry table for feeds that need to be retried. |
| ⚠️ 3 | Update severity tier [CONFLICT] (`rule__4`) | `SeverityTier` | Update the SeverityTier in the #ReconciliationResults table based on the outcome and shortfall percentage. |
| ⚠️ 4 | Merge reconciliation summary [MATCHED] (`rule__5`) | `Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn, FeedName, Outcome, ShortfallPct, SeverityTier, FirstReconciledDate, LastReconciledDate` | Merge reconciliation summary data into the PRO.BatchReconciliationSummary table. |
| ⚠️ 5 | Update severity tier in summary [MATCHED] (`rule__6`) | `SeverityTier` | Update the SeverityTier in the PRO.BatchReconciliationSummary table for feeds that have not been reconciled within the last 14 days. |
| ⚠️ 6 | Queue collections for failed feeds [CONFLICT] (`rule__7`) | `AccountId, EscalationDate, Reason` | Insert records into the PRO.CollectionsQueue table for accounts needing escalation due to failed feeds. |
| 🟠 7 | Determine Outcome [MATCHED] (`deterministic_decision_1739_2891_1_outcome`) | `Outcome` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| 🟠 8 | Determine ShortfallPct [MATCHED] (`deterministic_decision_1739_2891_2_shortfallpct`) | `ShortfallPct` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| 🟠 9 | Determine Reason [MATCHED] (`deterministic_decision_5530_5841_2_reason`) | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Insert initial results (rule__2) | INSERT INTO #ReconciliationResults (FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn) SELECT FeedName, CASE... END, CASE... END, NULL, @ProcessDate FROM PRO.BatchFeedRegistry WHERE FeedDate = @ProcessDate | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | Not cited | Verified |
| 2 | Update retry count (rule__3) | UPDATE PRO.BatchFeedRegistry SET RetryCount = 1 WHERE FeedDate = @ProcessDate AND FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED') | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_08_24 | Not cited | Verified |
| 3 | Update severity tier (rule__4) | UPDATE R SET R.SeverityTier = CASE... END FROM #ReconciliationResults R | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_03_19 | Not cited | Verified |
| 4 | Merge reconciliation summary (rule__5) | MERGE INTO PRO.BatchReconciliationSummary... | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_20 | Not cited | Verified |
| 5 | Update severity tier in summary (rule__6) | UPDATE PRO.BatchReconciliationSummary SET T.SeverityTier = CASE... END FROM PRO.BatchReconciliationSummary T WHERE T.Outcome <> 'RECONCILED' AND T.FirstReconciledDate <= DATEADD(DAY, -14, @ProcessDate) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_09_25 | Not cited | Verified |
| 6 | Queue collections for failed feeds (rule__7) | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT FeedName, ReconciledOn, CASE... END FROM #ReconciliationResults WHERE Outcome = 'FAILED' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_07_23 | Not cited | Verified |
| 7 | Determine Outcome (deterministic_decision_1739_2891_1_outcome) | Not cited | source \| Lines 46-70 | Not cited | Not cited | Verified |
| 8 | Determine ShortfallPct (deterministic_decision_1739_2891_2_shortfallpct) | Not cited | source \| Lines 46-70 | Not cited | Not cited | Verified |
| 9 | Determine Reason (deterministic_decision_5530_5841_2_reason) | Not cited | source \| Lines 123-129 | Not cited | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| decision_1739_2891_1:branch_001 | ExpectedRowCount IS NULL OR ExpectedRowCount = 0 | source \| Lines 46-70 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| decision_1739_2891_1:branch_002 | ActualRowCount >= ExpectedRowCount | source \| Lines 46-70 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| decision_1739_2891_1:branch_003 | @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100 > 10 | source \| Lines 46-70 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| decision_1739_2891_1:branch_004 | COALESCE(RetryCount, 0) = 0 | source \| Lines 46-70 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| decision_1739_2891_1:branch_005 | ELSE | source \| Lines 46-70 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| decision_1739_2891_2:branch_001 | ExpectedRowCount IS NULL OR ExpectedRowCount = 0 | source \| Lines 46-70 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| decision_1739_2891_2:branch_002 | ActualRowCount >= ExpectedRowCount | source \| Lines 46-70 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| decision_1739_2891_2:branch_003 | ELSE | source \| Lines 46-70 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| case_0079_0086_3291:branch_001 | R.Outcome = 'RECONCILED' | source \| Lines 80-81 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_11 |
| case_0079_0086_3291:branch_002 | R.Outcome = 'NOT_APPLICABLE' | source \| Lines 81-82 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_11 |
| case_0079_0086_3291:branch_003 | R.Outcome = 'RETRY_QUEUED' | source \| Lines 82-83 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_11 |
| case_0079_0086_3291:branch_004 | R.Outcome = 'FAILED' AND R.ShortfallPct > 25 | source \| Lines 83-84 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_11 |
| case_0079_0086_3291:branch_005 | R.Outcome = 'FAILED' | source \| Lines 84-85 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_11 |
| case_0079_0086_3291:branch_006 | ELSE | source \| Lines 85-86 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_11 |
| decision_5530_5841_2:branch_001 | SeverityTier = 'CRITICAL' | source \| Lines 123-129 |
| decision_5530_5841_2:branch_002 | ELSE | source \| Lines 123-129 |
| decision_chain_005:branch_001 | ExpectedRowCount IS NULL OR ExpectedRowCount = 0 | source |
| decision_chain_005:branch_002 | ActualRowCount >= ExpectedRowCount | source |
| decision_chain_005:branch_003 | @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS DECIMAL(18,4)) / ExpectedRowCount) * 100 > 10 | source |
| decision_chain_005:branch_004 | ISNULL(RetryCount, 0) = 0 | source |
| decision_chain_005:branch_005 | ELSE | source |
| decision_chain_006:branch_001 | R.Outcome = 'RECONCILED' | source |
| decision_chain_006:branch_002 | R.Outcome = 'NOT_APPLICABLE' | source |
| decision_chain_006:branch_003 | R.Outcome = 'RETRY_QUEUED' | source |
| decision_chain_006:branch_004 | R.Outcome = 'FAILED' AND R.ShortfallPct > 25 | source |
| decision_chain_006:branch_005 | R.Outcome = 'FAILED' | source |
| decision_chain_006:branch_006 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 110
- **Disposition:** covered_by_rule=79, technical_only=8, uncovered=23

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | covered_by_rule | Lines 1-2 | 03_batch3_main_body+batch3_nested_block:chunk_text_01, 03_batch3_main_body+batch3_nested_block | BEGIN SET NOCOUNT ON |
| STATEMENT | covered_by_rule | Lines 4-4 | 03_batch3_main_body+batch3_nested_block:chunk_text_02, 03_batch3_main_body+batch3_nested_block | BEGIN TRY |
| SELECT | covered_by_rule | Lines 6-6 | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| STATEMENT | covered_by_rule | Lines 7-7 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @MonthEndDate DATE = EOMONTH(@ProcessDate) |
| STATEMENT | covered_by_rule | Lines 9-9 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | IF OBJECT_ID('tempdb..#ReconciliationResults') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 10-10 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | DROP TABLE #ReconciliationResults |
| STATEMENT | covered_by_rule | Lines 12-27 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | CREATE TABLE #ReconciliationResults ( FeedName VARCHAR(50), Outcome VARCHAR(20), ShortfallPct DECIMAL(9,4), SeverityTier VARCHAR(10), ReconciledOn DATE ) -- Rule 1: NULL check - a feed with no expected count on record -- cannot be reconc... |
| INSERT | covered_by_rule | Lines 28-51 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ReconciliationResults (FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn) SELECT FeedName, CASE WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE' WHEN ActualRowCount >= ExpectedRowCount TH... |
| UPDATE | covered_by_rule | Lines 52-58 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.BatchFeedRegistry SET RetryCount = 1 WHERE FeedDate = @ProcessDate AND FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED') -- Rule 3: multi-branch CASE - derive a severity tier for every --... |
| UPDATE | covered_by_rule | Lines 59-74 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | UPDATE R SET R.SeverityTier = ( CASE WHEN R.Outcome = 'RECONCILED' THEN 'NONE' WHEN R.Outcome = 'NOT_APPLICABLE' THEN 'NONE' WHEN R.Outcome = 'RETRY_QUEUED' THEN 'WATCH' WHEN R.Outcome = 'FAILED' AND R.ShortfallPct > 25 THEN 'CRITICAL' W... |
| MERGE | covered_by_rule | Lines 75-90 | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | MERGE PRO.BatchReconciliationSummary AS Target USING #ReconciliationResults AS Source ON Target.FeedName = Source.FeedName WHEN MATCHED THEN UPDATE SET Target.Outcome = Source.Outcome, Target.ShortfallPct = Source.ShortfallPct, Target.Se... |
| UPDATE | covered_by_rule | Lines 91-98 | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.SeverityTier = 'CRITICAL' FROM PRO.BatchReconciliationSummary T WHERE T.Outcome <> 'RECONCILED' AND T.FirstReconciledDate <= DATEADD(DAY, -14, @ProcessDate) -- Rule 6: persist every outcome computed above into the log, --... |
| INSERT | covered_by_rule | Lines 99-104 | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.BatchReconciliationLog (FeedName, Outcome, ReconciledOn) SELECT R.FeedName, R.Outcome, R.ReconciledOn FROM #ReconciliationResults R -- Rule 7: status transition and audit - failed feeds are -- escalated to the collections... |
| INSERT | covered_by_rule | Lines 105-109 | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT FeedName, ReconciledOn, CASE WHEN SeverityTier = 'CRITICAL' THEN 'FEED_RECONCILIATION_CRITICAL' ELSE 'FEED_RECONCILIATION_FAILED' END FROM #ReconciliationResults... |
| UPDATE | covered_by_rule | Lines 111-113 | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Batch_Job_Reconciliation' |
| STATEMENT | covered_by_rule | Lines 115-115 | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | END TRY |
| INSERT | covered_by_rule | Lines 28-51 | 03_batch3_main_body+batch3_nested_block:embedded_01_17, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ReconciliationResults (FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn) SELECT FeedName, CASE WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE' WHEN ActualRowCount >= ExpectedRowCount TH... |
| UPDATE | covered_by_rule | Lines 52-58 | 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.BatchFeedRegistry SET RetryCount = 1 WHERE FeedDate = @ProcessDate AND FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED') -- Rule 3: multi-branch CASE - derive a severity tier for every --... |
| UPDATE | covered_by_rule | Lines 59-74 | 03_batch3_main_body+batch3_nested_block:embedded_03_19, 03_batch3_main_body+batch3_nested_block | UPDATE R SET R.SeverityTier = ( CASE WHEN R.Outcome = 'RECONCILED' THEN 'NONE' WHEN R.Outcome = 'NOT_APPLICABLE' THEN 'NONE' WHEN R.Outcome = 'RETRY_QUEUED' THEN 'WATCH' WHEN R.Outcome = 'FAILED' AND R.ShortfallPct > 25 THEN 'CRITICAL' W... |
| MERGE | covered_by_rule | Lines 75-90 | 03_batch3_main_body+batch3_nested_block:embedded_04_20, 03_batch3_main_body+batch3_nested_block | MERGE PRO.BatchReconciliationSummary AS Target USING #ReconciliationResults AS Source ON Target.FeedName = Source.FeedName WHEN MATCHED THEN UPDATE SET Target.Outcome = Source.Outcome, Target.ShortfallPct = Source.ShortfallPct, Target.Se... |
| UPDATE | covered_by_rule | Lines 91-98 | 03_batch3_main_body+batch3_nested_block:embedded_05_21, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.SeverityTier = 'CRITICAL' FROM PRO.BatchReconciliationSummary T WHERE T.Outcome <> 'RECONCILED' AND T.FirstReconciledDate <= DATEADD(DAY, -14, @ProcessDate) -- Rule 6: persist every outcome computed above into the log, --... |
| INSERT | covered_by_rule | Lines 99-104 | 03_batch3_main_body+batch3_nested_block:embedded_06_22, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.BatchReconciliationLog (FeedName, Outcome, ReconciledOn) SELECT R.FeedName, R.Outcome, R.ReconciledOn FROM #ReconciliationResults R -- Rule 7: status transition and audit - failed feeds are -- escalated to the collections... |
| INSERT | covered_by_rule | Lines 105-109 | 03_batch3_main_body+batch3_nested_block:embedded_07_23, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT FeedName, ReconciledOn, CASE WHEN SeverityTier = 'CRITICAL' THEN 'FEED_RECONCILIATION_CRITICAL' ELSE 'FEED_RECONCILIATION_FAILED' END FROM #ReconciliationResults... |
| UPDATE | covered_by_rule | Lines 111-113 | 03_batch3_main_body+batch3_nested_block:embedded_08_24, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Batch_Job_Reconciliation' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Batch_Job_Reconciliation' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_05, 04_batch3_exception | END |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Batch_Job_Reconciliation' |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:embedded_02_07, 04_batch3_exception | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| INSERT_TEMP | technical_only | samples/18_Batch_Job_Reconciliation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ReconciliationResults (FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn) SELECT FeedName, CASE WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE' WHEN ActualRowCount >= ExpectedRowCount TH... |
| UPDATE | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.BatchFeedRegistry SET RetryCount = 1 WHERE FeedDate = @ProcessDate AND FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED') -- Rule 3: multi-branch CASE - derive a severity tier for every --... |
| READ_TEMP | technical_only | samples/18_Batch_Job_Reconciliation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.BatchFeedRegistry SET RetryCount = 1 WHERE FeedDate = @ProcessDate AND FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED') -- Rule 3: multi-branch CASE - derive a severity tier for every --... |
| UPDATE_TEMP | technical_only | samples/18_Batch_Job_Reconciliation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | UPDATE R SET R.SeverityTier = ( CASE WHEN R.Outcome = 'RECONCILED' THEN 'NONE' WHEN R.Outcome = 'NOT_APPLICABLE' THEN 'NONE' WHEN R.Outcome = 'RETRY_QUEUED' THEN 'WATCH' WHEN R.Outcome = 'FAILED' AND R.ShortfallPct > 25 THEN 'CRITICAL' W... |
| MERGE | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | MERGE PRO.BatchReconciliationSummary AS Target USING #ReconciliationResults AS Source ON Target.FeedName = Source.FeedName WHEN MATCHED THEN UPDATE SET Target.Outcome = Source.Outcome, Target.ShortfallPct = Source.ShortfallPct, Target.Se... |
| UPDATE | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.SeverityTier = 'CRITICAL' FROM PRO.BatchReconciliationSummary T WHERE T.Outcome <> 'RECONCILED' AND T.FirstReconciledDate <= DATEADD(DAY, -14, @ProcessDate) -- Rule 6: persist every outcome computed above into the log, --... |
| INSERT | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.BatchReconciliationLog (FeedName, Outcome, ReconciledOn) SELECT R.FeedName, R.Outcome, R.ReconciledOn FROM #ReconciliationResults R -- Rule 7: status transition and audit - failed feeds are -- escalated to the collections... |
| INSERT | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT FeedName, ReconciledOn, CASE WHEN SeverityTier = 'CRITICAL' THEN 'FEED_RECONCILIATION_CRITICAL' ELSE 'FEED_RECONCILIATION_FAILED' END FROM #ReconciliationResults... |
| UPDATE | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Batch_Job_Reconciliation' |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_17, 03_batch3_main_body+batch3_nested_block:embedded_01_17, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ReconciliationResults (FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn) SELECT FeedName, CASE WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE' WHEN ActualRowCount >= ExpectedRowCount TH... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_17, 03_batch3_main_body+batch3_nested_block:embedded_01_17, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ReconciliationResults (FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn) SELECT FeedName, CASE WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE' WHEN ActualRowCount >= ExpectedRowCount TH... |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.BatchFeedRegistry SET RetryCount = 1 WHERE FeedDate = @ProcessDate AND FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED') -- Rule 3: multi-branch CASE - derive a severity tier for every --... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.BatchFeedRegistry SET RetryCount = 1 WHERE FeedDate = @ProcessDate AND FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED') -- Rule 3: multi-branch CASE - derive a severity tier for every --... |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_19, 03_batch3_main_body+batch3_nested_block:embedded_03_19, 03_batch3_main_body+batch3_nested_block | UPDATE R SET R.SeverityTier = ( CASE WHEN R.Outcome = 'RECONCILED' THEN 'NONE' WHEN R.Outcome = 'NOT_APPLICABLE' THEN 'NONE' WHEN R.Outcome = 'RETRY_QUEUED' THEN 'WATCH' WHEN R.Outcome = 'FAILED' AND R.ShortfallPct > 25 THEN 'CRITICAL' W... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_21, 03_batch3_main_body+batch3_nested_block:embedded_05_21, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.SeverityTier = 'CRITICAL' FROM PRO.BatchReconciliationSummary T WHERE T.Outcome <> 'RECONCILED' AND T.FirstReconciledDate <= DATEADD(DAY, -14, @ProcessDate) -- Rule 6: persist every outcome computed above into the log, --... |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_22, 03_batch3_main_body+batch3_nested_block:embedded_06_22, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.BatchReconciliationLog (FeedName, Outcome, ReconciledOn) SELECT R.FeedName, R.Outcome, R.ReconciledOn FROM #ReconciliationResults R -- Rule 7: status transition and audit - failed feeds are -- escalated to the collections... |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_23, 03_batch3_main_body+batch3_nested_block:embedded_07_23, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT FeedName, ReconciledOn, CASE WHEN SeverityTier = 'CRITICAL' THEN 'FEED_RECONCILIATION_CRITICAL' ELSE 'FEED_RECONCILIATION_FAILED' END FROM #ReconciliationResults... |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_23, 03_batch3_main_body+batch3_nested_block:embedded_07_23, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT FeedName, ReconciledOn, CASE WHEN SeverityTier = 'CRITICAL' THEN 'FEED_RECONCILIATION_CRITICAL' ELSE 'FEED_RECONCILIATION_FAILED' END FROM #ReconciliationResults... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_24, 03_batch3_main_body+batch3_nested_block:embedded_08_24, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Batch_Job_Reconciliation' |
| UPDATE | uncovered | samples/18_Batch_Job_Reconciliation.sql / Lines 134-141 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Batch_Job_Reconciliation' |
| UPDATE | uncovered | unavailable | 04_batch3_exception:embedded_01_06, 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Batch_Job_Reconciliation' |
| IF_BRANCH | covered_by_rule | Lines 46-70 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | ExpectedRowCount IS NULL OR ExpectedRowCount = 0 |
| IF_BRANCH | covered_by_rule | Lines 46-70 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | ActualRowCount >= ExpectedRowCount |
| IF_BRANCH | covered_by_rule | Lines 46-70 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS NUMERIC(18, 4)) / ExpectedRowCount) * 100 > 10 |
| IF_BRANCH | covered_by_rule | Lines 46-70 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | COALESCE(RetryCount, 0) = 0 |
| ELSE | covered_by_rule | Lines 46-70 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | ELSE |
| IF_BRANCH | covered_by_rule | Lines 46-70 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | ExpectedRowCount IS NULL OR ExpectedRowCount = 0 |
| IF_BRANCH | covered_by_rule | Lines 46-70 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | ActualRowCount >= ExpectedRowCount |
| ELSE | covered_by_rule | Lines 46-70 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | ELSE |
| CASE | covered_by_rule | Lines 80-81 | 03_batch3_main_body+batch3_nested_block:chunk_text_11 | R.Outcome = 'RECONCILED' |
| CASE | covered_by_rule | Lines 81-82 | 03_batch3_main_body+batch3_nested_block:chunk_text_11 | R.Outcome = 'NOT_APPLICABLE' |
| CASE | covered_by_rule | Lines 82-83 | 03_batch3_main_body+batch3_nested_block:chunk_text_11 | R.Outcome = 'RETRY_QUEUED' |
| CASE | covered_by_rule | Lines 83-84 | 03_batch3_main_body+batch3_nested_block:chunk_text_11 | R.Outcome = 'FAILED' AND R.ShortfallPct > 25 |
| CASE | covered_by_rule | Lines 84-85 | 03_batch3_main_body+batch3_nested_block:chunk_text_11 | R.Outcome = 'FAILED' |
| ELSE | covered_by_rule | Lines 85-86 | 03_batch3_main_body+batch3_nested_block:chunk_text_11 | ELSE |
| IF_BRANCH | covered_by_rule | Lines 123-129 | unavailable | SeverityTier = 'CRITICAL' |
| ELSE | covered_by_rule | Lines 123-129 | unavailable | ELSE |
| IF_BRANCH | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | ExpectedRowCount IS NULL OR ExpectedRowCount = 0 |
| IF_BRANCH | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | ActualRowCount >= ExpectedRowCount |
| IF_BRANCH | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS DECIMAL(18,4)) / ExpectedRowCount) * 100 > 10 |
| IF_BRANCH | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | ISNULL(RetryCount, 0) = 0 |
| ELSE | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | R.Outcome = 'RECONCILED' |
| IF_BRANCH | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | R.Outcome = 'NOT_APPLICABLE' |
| IF_BRANCH | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | R.Outcome = 'RETRY_QUEUED' |
| IF_BRANCH | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | R.Outcome = 'FAILED' AND R.ShortfallPct > 25 |
| IF_BRANCH | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | R.Outcome = 'FAILED' |
| ELSE | covered_by_rule | samples/18_Batch_Job_Reconciliation.sql | full_source | ELSE |
| IF | uncovered | Lines 27-27 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 49-49 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 50-50 | unavailable | WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN |
| CASE_BRANCH | covered_by_rule | Lines 51-51 | unavailable | WHEN ActualRowCount >= ExpectedRowCount THEN |
| CASE_BRANCH | covered_by_rule | Lines 52-52 | unavailable | WHEN @ProcessDate = @MonthEndDate |
| CASE_BRANCH | covered_by_rule | Lines 55-55 | unavailable | WHEN ISNULL(RetryCount, 0) = 0 THEN |
| ELSE | covered_by_rule | Lines 56-56 | unavailable | ELSE |
| CASE | covered_by_rule | Lines 58-58 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 59-59 | unavailable | WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN NULL |
| CASE_BRANCH | covered_by_rule | Lines 60-60 | unavailable | WHEN ActualRowCount >= ExpectedRowCount THEN 0 |
| ELSE | covered_by_rule | Lines 61-61 | unavailable | ELSE (CAST(ExpectedRowCount - ActualRowCount AS DECIMAL(18,4)) / ExpectedRowCount) * 100 |
| CASE | covered_by_rule | Lines 79-79 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 80-80 | unavailable | WHEN R.Outcome = THEN |
| CASE_BRANCH | uncovered | Lines 81-81 | unavailable | WHEN R.Outcome = THEN |
| CASE_BRANCH | uncovered | Lines 82-82 | unavailable | WHEN R.Outcome = THEN |
| CASE_BRANCH | uncovered | Lines 83-83 | unavailable | WHEN R.Outcome = AND R.ShortfallPct > 25 THEN |
| CASE_BRANCH | uncovered | Lines 84-84 | unavailable | WHEN R.Outcome = THEN |
| ELSE | covered_by_rule | Lines 85-85 | unavailable | ELSE |
| CASE_BRANCH | uncovered | Lines 96-96 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | uncovered | Lines 102-102 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CASE | covered_by_rule | Lines 125-125 | unavailable | CASE WHEN SeverityTier = THEN ELSE END |
| CASE_BRANCH | covered_by_rule | Lines 125-125 | unavailable | CASE WHEN SeverityTier = THEN ELSE END |
| ELSE | covered_by_rule | Lines 125-125 | unavailable | CASE WHEN SeverityTier = THEN ELSE END |
| CATCH | uncovered | Lines 134-134 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 139-139 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_01_17 / #ReconciliationResults | 03_batch3_main_body+batch3_nested_block:embedded_02_18 / #ReconciliationResults | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_17 / #ReconciliationResults | 03_batch3_main_body+batch3_nested_block:embedded_03_19 / #ReconciliationResults | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_01_17 / #ReconciliationResults | 03_batch3_main_body+batch3_nested_block:embedded_06_22 / #ReconciliationResults | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_01_17 / #ReconciliationResults | 03_batch3_main_body+batch3_nested_block:embedded_07_23 / #ReconciliationResults | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_03_19 / #ReconciliationResults | 03_batch3_main_body+batch3_nested_block:embedded_06_22 / #ReconciliationResults | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_03_19 / #ReconciliationResults | 03_batch3_main_body+batch3_nested_block:embedded_07_23 / #ReconciliationResults | high |

Unresolved dependency candidates: 19. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 9
- **By rule type:** deterministic_decision_table = 3, explicit = 6
- **By validation status:** verified = 9

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 16
- **Deterministic-only facts:** 2
- **LLM-only claims:** 3
- **Conflicts:** 4
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` tables_read (`recon_f75276f4e2d1`): full_source
- `LLM_ONLY` tables_read (`recon_f75276f4e2d1`): full_source
- `CONFLICT` tables_written (`recon_824c82d25092`): full_source
- `LLM_ONLY` tables_written (`recon_dc5de928af01`): full_source
- `CONFLICT` rule (`recon_5de80f7625f5`): rule__2, 03_batch3_main_body+batch3_nested_block, 03_batch3_main_body+batch3_nested_block:chunk_text_08;03_batch3_main_body+batch3_nested_block:chunk_text_09;03_batch3_main_body+batch3_nested_block:chunk_text_10;03_batch3_main_body+batch3_nested_block:chunk_text_11;03_batch3_main_body+batch3_nested_block:chunk_text_12;03_batch3_main_body+batch3_nested_block:chunk_text_13;03_batch3_main_body+batch3_nested_block:embedded_01_17;03_batch3_main_body+batch3_nested_block:embedded_02_18;03_batch3_main_body+batch3_nested_block:embedded_03_19;03_batch3_main_body+batch3_nested_block:embedded_05_21;03_batch3_main_body+batch3_nested_block:embedded_06_22;03_batch3_main_body+batch3_nested_block:embedded_07_23 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 78.53333333333333/100
- **Statement coverage:** 24 / 36 (66.7%)
- **Rule grounding coverage:** 6 / 9 (66.7%)
- **Decision-chain coverage:** 16 / 16 branches (100.0%)
- **Conflicts:** 4
- **Contradictions:** 5
- **Review required items:** 12
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `HIGH` Operation Conflict on `source`: Synthesized table operation conflicts with deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Outcome Conflict on `rule__2`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Outcome Conflict on `rule__4`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `MEDIUM` Field Conflict on `rule__7`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE #ReconciliationResults SET R.SeverityTier = 'CRITICAL' WHERE ShortfallPct > 50
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: SELECT R.FeedName, R.Outcome, R.ReconciledOn FROM #ReconciliationResults R
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE #ReconciliationResults SET SeverityTier = CASE WHEN SeverityTier = 'CRITICAL' THEN 'FEED_RECONCILIATION_CRITICAL' ELSE 'FEED_RECONCILIATION_FAILED' END WHERE FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED')
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.BatchReconciliationSummary WITH (HOLDLOCK) AS Target USING (SELECT * FROM #ReconciliationResults) AS Source ON Target.FeedName = Source.FeedName WHEN MATCHED THEN UPDATE SET Target.Outcome = Source.Outcome, Target.ShortfallPct = Source.ShortfallPct, Target.SeverityTier = Source.SeverityTier, Target.LastReconciledDate = Source.ReconciledOn WHEN NOT MATCHED BY TARGET THEN INSERT (Target.FeedName, Source.FeedName, Target.Outcome, Source.Outcome, Target.ShortfallPct, Source.ShortfallPct, Target.SeverityTier, Source.SeverityTier, Target.LastReconciledDate, Source.ReconciledOn) VALUES (Source.FeedName, Source.FeedName, Source.Outcome, Source.Outcome, Source.ShortfallPct, Source.ShortfallPct, Source.SeverityTier, Source.SeverityTier, Source.ReconciledOn, Source.ReconciledOn)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: SELECT FeedName, CASE WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN 'NOT_APPLICABLE' WHEN ActualRowCount >= ExpectedRowCount THEN 'RECONCILED' WHEN @ProcessDate = @MonthEndDate AND (CAST(ExpectedRowCount - ActualRowCount AS DECIMAL(18,4)) / ExpectedRowCount) * 100 > 10 THEN 'FAILED' WHEN COALESCE(RetryCount, 0) = 0 THEN 'RETRY_QUEUED' ELSE 'FAILED' END, CASE WHEN ExpectedRowCount IS NULL OR ExpectedRowCount = 0 THEN NULL WHEN ActualRowCount >= ExpectedRowCount THEN 0 ELSE (CAST(ExpectedRowCount - ActualRowCount AS DECIMAL(18,4)) / ExpectedRowCount) * 100 END, NULL, @ProcessDate FROM PRO.BatchFeedRegistry WHERE FeedDate = @ProcessDate
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO #ReconciliationResults (FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn) SELECT FeedName, CASE... END, CASE... END, NULL, @ProcessDate FROM PRO.BatchFeedRegistry WHERE FeedDate = @ProcessDate
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE #ReconciliationResults SET R.SeverityTier = CASE... END WHERE...
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.BatchReconciliationSummary...
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE PRO.BatchReconciliationSummary SET T.SeverityTier =... WHERE T.Outcome <> 'RECONCILED' AND T.FirstReconciledDate <= DATEADD(DAY, -14, @ProcessDate)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: SELECT FeedName, CASE... END, CASE... END, NULL, @ProcessDate FROM PRO.BatchFeedRegistry WHERE FeedDate = @ProcessDate
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE PRO.BatchFeedRegistry SET RetryCount = RetryCount + 1 WHERE FeedDate = @ProcessDate AND FeedName IN (SELECT FeedName FROM #ReconciliationResults WHERE Outcome = 'RETRY_QUEUED')
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE R SET R.SeverityTier = CASE... END FROM #ReconciliationResults R
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE PRO.BatchReconciliationSummary AS Target USING (SELECT * FROM #ReconciliationResults) AS Source ON Target.FeedName = Source.FeedName
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE PRO.BatchReconciliationSummary SET T.SeverityTier = CASE... END FROM PRO.BatchReconciliationSummary T WHERE T.Outcome <> 'RECONCILED' AND T.FirstReconciledDate <= DATEADD(DAY, -14, @ProcessDate)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: SELECT FeedName, Outcome, ShortfallPct, SeverityTier, ReconciledOn FROM PRO.BatchFeedRegistry WHERE FeedDate = @ProcessDate
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE #ReconciliationResults SET SeverityTier = CASE... END WHERE...
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE PRO.BatchReconciliationSummary SET SeverityTier = CASE... END WHERE T.Outcome <> 'RECONCILED' AND T.FirstReconciledDate <= DATEADD(DAY, -14, @ProcessDate)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: SELECT FeedName, CASE... END AS Outcome, CASE... END AS ShortfallPct FROM PRO.BatchFeedRegistry WHERE FeedDate = @ProcessDate
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT FeedName, ReconciledOn, CASE... END FROM #ReconciliationResults WHERE Outcome = 'FAILED'
- Synthesized in 7 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
