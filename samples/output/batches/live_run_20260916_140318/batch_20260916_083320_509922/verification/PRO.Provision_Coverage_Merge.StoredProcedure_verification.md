# Provision Coverage Merge — Verification & Traceability

> Companion artifact to `PRO.Provision_Coverage_Merge.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_8ece2542e210` |
| Raw technical object name (from source) | `Provision_Coverage_Merge` |

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
| Source Hash | `de5d0b52c31ed4ff02eea4b93e5cc831e8912c3d9887dc8ee759d7563e784b3d` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T08:39:37.846062+00:00` |
| Object ID | `obj_8ece2542e210` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_01aa045dcf5c` |
| Total LLM Calls | `6` |
| Successful Calls | `6` |
| Failed Calls | `0` |
| Prompt Tokens | `71846` |
| Completion Tokens | `10885` |
| Total Tokens | `82731` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 6386 | available |
| synthesis | 3 | 3 | 0 | 27945 | available |
| synthesis_revision | 2 | 2 | 0 | 48400 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Determine ReviewReason [MATCHED] (`deterministic_case_0056_0062_2036_reviewreason`) | `ReviewReason` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 2 | Determine Reason [MATCHED] (`deterministic_decision_4861_5218_2_reason`) | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| ⚠️ 3 | Insert account data [CONFLICT] (`rule__1`) | `AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, ReviewReason` | Insert account data into the #ProvisionCoverage temporary table from the PRO.LoanAccountCal table. |
| ⚠️ 4 | Calculate coverage ratio [MATCHED] (`rule__2`) | `CoverageRatio` | Calculate the coverage ratio for accounts with non-null outstanding balances. |
| ⚠️ 5 | Update review reason [MATCHED] (`rule__3`) | `ReviewReason` | Update the review reason based on the coverage ratio. |
| ⚠️ 6 | Conditionally append to review reason [MATCHED] (`rule__4`) | `ReviewReason` | Conditionally append '_QUARTER_END' to the review reason if the process date is within a certain range. |
| ⚠️ 7 | Merge data into summary table [LLM_ONLY] (`rule__5`) | `AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, FirstSeenDate, LastUpdatedDate` | Merge data from the #ProvisionCoverage temporary table into the PRO.ProvisionCoverageSummary table. |
| ⚠️ 8 | Update below threshold flag [MATCHED] (`rule__6`) | `BelowThresholdFlag` | Update the BelowThresholdFlag in the PRO.ProvisionCoverageSummary table based on the coverage ratio. |
| ⚠️ 9 | Insert into collections queue [CONFLICT] (`rule__7`) | `AccountId, EscalationDate, Reason` | Insert data into the PRO.CollectionsQueue table based on the coverage ratio and review reason. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Determine ReviewReason (deterministic_case_0056_0062_2036_reviewreason) | Not cited | source \| Lines 56-62 | Not cited | Not cited | Verified |
| 2 | Determine Reason (deterministic_decision_4861_5218_2_reason) | Not cited | source \| Lines 117-124 | Not cited | Not cited | Verified |
| 3 | Insert account data (rule__1) | INSERT INTO #ProvisionCoverage (AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, ReviewReason) SELECT A.AccountId, A.OutstandingBalance, A.ProvisionAmount, CASE WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.OutstandingBalance ELSE NUL… | Not cited | Not cited | Not cited | Needs Review |
| 4 | Calculate coverage ratio (rule__2) | CASE WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.OutstandingBalance ELSE NULL END | Not cited | Not cited | Not cited | Verified |
| 5 | Update review reason (rule__3) | CASE WHEN S.CoverageRatio IS NULL THEN 'NO_BALANCE' WHEN S.CoverageRatio < 0.25 THEN 'SEVERE_UNDERCOVER' WHEN S.CoverageRatio < 0.5 THEN 'MODERATE_UNDERCOVER' WHEN S.CoverageRatio >= 0.5 AND S.CoverageRatio < 1 THEN 'ADEQUATE' ELSE 'FULLY_COVERED' END | Not cited | Not cited | Not cited | Verified |
| 6 | Conditionally append to review reason (rule__4) | UPDATE S SET S.ReviewReason = S.ReviewReason + '_QUARTER_END' FROM #ProvisionCoverage S WHERE S.CoverageRatio IS NOT NULL AND S.CoverageRatio < 0.6 | Not cited | Not cited | Not cited | Verified |
| 7 | Merge data into summary table (rule__5) | MERGE PRO.ProvisionCoverageSummary AS Target USING #ProvisionCoverage AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.OutstandingBalance = Source.OutstandingBalance, Target.ProvisionAmount = Source.ProvisionAmount, Target.… | Not cited | Not cited | Not cited | Needs Review |
| 8 | Update below threshold flag (rule__6) | UPDATE T SET T.BelowThresholdFlag = 'Y' FROM PRO.ProvisionCoverageSummary T WHERE T.CoverageRatio IS NOT NULL AND T.CoverageRatio < 0.5 AND T.LastUpdatedDate = @ProcessDate | Not cited | Not cited | Not cited | Verified |
| 9 | Insert into collections queue (rule__7) | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN CoverageRatio < 0.25 THEN 'SEVERE_PROVISION_SHORTFALL' ELSE 'MODERATE_PROVISION_SHORTFALL' END FROM #ProvisionCoverage WHERE ReviewReason LIKE '%UND… | Not cited | Not cited | Not cited | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| decision_1348_1980_3:branch_001 | A.OutstandingBalance > 0 | source \| Lines 40-54 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| decision_1348_1980_3:branch_002 | ELSE | source \| Lines 40-54 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_08 |
| case_0056_0062_2036:branch_001 | S.CoverageRatio IS NULL | source \| Lines 57-58 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_12 |
| case_0056_0062_2036:branch_002 | S.CoverageRatio < 0.25 | source \| Lines 58-59 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_12 |
| case_0056_0062_2036:branch_003 | S.CoverageRatio < 0.5 | source \| Lines 59-60 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_12 |
| case_0056_0062_2036:branch_004 | S.CoverageRatio >= 0.5 AND S.CoverageRatio < 1 | source \| Lines 60-61 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_16 |
| case_0056_0062_2036:branch_005 | ELSE | source \| Lines 61-62 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_16 |
| tsql_if_0068_0083:branch_001 | @ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate) | source \| Lines 69-73 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_18 |
| tsql_if_0068_0083:branch_002 | ELSE | source \| Lines 75-79 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_18 |
| decision_4861_5218_2:branch_001 | CoverageRatio < 0.25 | source \| Lines 117-124 |
| decision_4861_5218_2:branch_002 | ELSE | source \| Lines 117-124 |
| decision_chain_005:branch_001 | S.CoverageRatio IS NULL | source |
| decision_chain_005:branch_002 | S.CoverageRatio < 0.25 | source |
| decision_chain_005:branch_003 | S.CoverageRatio < 0.5 | source |
| decision_chain_005:branch_004 | S.CoverageRatio >= 0.5 AND S.CoverageRatio < 1 | source |
| decision_chain_005:branch_005 | ELSE | source |
| decision_chain_006:branch_001 | T.CoverageRatio IS NOT NULL AND T.CoverageRatio < 0.5 AND T.LastUpdatedDate = @ProcessDate | source |
| decision_chain_006:branch_002 | T.CoverageRatio >= 0.5 AND T.LastUpdatedDate = @ProcessDate | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 104
- **Disposition:** covered_by_rule=56, technical_only=9, uncovered=39

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | uncovered | Lines 1-2 | 03_batch3_main_body+batch3_nested_block:chunk_text_01, 03_batch3_main_body+batch3_nested_block | BEGIN SET NOCOUNT ON |
| STATEMENT | uncovered | Lines 4-4 | 03_batch3_main_body+batch3_nested_block:chunk_text_02, 03_batch3_main_body+batch3_nested_block | BEGIN TRY |
| SELECT | uncovered | Lines 6-6 | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| STATEMENT | uncovered | Lines 7-7 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @QuarterStartDate DATE = DATEADD(MONTH, -3, @ProcessDate) |
| STATEMENT | uncovered | Lines 9-9 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | IF OBJECT_ID('tempdb..#ProvisionCoverage') IS NOT NULL |
| STATEMENT | uncovered | Lines 10-10 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | DROP TABLE #ProvisionCoverage |
| INSERT | uncovered | Lines 12-22 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | CREATE TABLE #ProvisionCoverage ( AccountId VARCHAR(20), OutstandingBalance DECIMAL(18,2), ProvisionAmount DECIMAL(18,2), CoverageRatio DECIMAL(9,4), ReviewReason VARCHAR(40) ) -- Rule 1: conditional INSERT - coverage ratio is only stage... |
| INSERT | covered_by_rule | Lines 23-36 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ProvisionCoverage (AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, ReviewReason) SELECT A.AccountId, A.OutstandingBalance, A.ProvisionAmount, CASE WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.Outst... |
| UPDATE | uncovered | Lines 37-50 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = ( CASE WHEN S.CoverageRatio IS NULL THEN 'NO_BALANCE' WHEN S.CoverageRatio < 0.25 THEN 'SEVERE_UNDERCOVER' WHEN S.CoverageRatio < 0.5 THEN 'MODERATE_UNDERCOVER' WHEN S.CoverageRatio >= 0.5 AND S.CoverageRati... |
| STATEMENT | uncovered | Lines 51-51 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | IF @ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate) |
| STATEMENT | uncovered | Lines 1-1 | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 53-55 | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = S.ReviewReason + '_QUARTER_END' FROM #ProvisionCoverage S WHERE S.CoverageRatio IS NOT NULL AND S.CoverageRatio < 0.6 |
| STATEMENT | covered_by_rule | Lines 30-30 | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 29-29 | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | ELSE |
| STATEMENT | uncovered | Lines 1-1 | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 59-61 | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = S.ReviewReason FROM #ProvisionCoverage S WHERE S.CoverageRatio IS NOT NULL AND S.CoverageRatio < 0.5 |
| UPDATE | covered_by_rule | Lines 62-66 | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | END -- Rule 4: upsert the computed coverage into the summary table - -- update accounts already tracked, insert accounts seen for the -- first time this run |
| MERGE | covered_by_rule | Lines 67-81 | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | MERGE PRO.ProvisionCoverageSummary AS Target USING #ProvisionCoverage AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.OutstandingBalance = Source.OutstandingBalance, Target.ProvisionAmount = Source.Pr... |
| UPDATE | covered_by_rule | Lines 82-90 | 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.BelowThresholdFlag = 'Y' FROM PRO.ProvisionCoverageSummary T WHERE T.CoverageRatio IS NOT NULL AND T.CoverageRatio < 0.5 AND T.LastUpdatedDate = @ProcessDate -- Rule 6: accounts at or above the threshold are cleared of any... |
| UPDATE | uncovered | Lines 91-99 | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.BelowThresholdFlag = 'N' FROM PRO.ProvisionCoverageSummary T WHERE T.CoverageRatio >= 0.5 AND T.LastUpdatedDate = @ProcessDate -- Rule 7: record a review case for every account newly below -- threshold - the escalation que... |
| INSERT | covered_by_rule | Lines 100-105 | 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN CoverageRatio < 0.25 THEN 'SEVERE_PROVISION_SHORTFALL' ELSE 'MODERATE_PROVISION_SHORTFALL' END FROM #ProvisionCoverage WHERE R... |
| UPDATE | uncovered | Lines 107-109 | 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Provision_Coverage_Merge' |
| STATEMENT | uncovered | Lines 111-111 | 03_batch3_main_body+batch3_nested_block:chunk_text_23, 03_batch3_main_body+batch3_nested_block | END TRY |
| INSERT | covered_by_rule | Lines 23-36 | 03_batch3_main_body+batch3_nested_block:embedded_01_24, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ProvisionCoverage (AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, ReviewReason) SELECT A.AccountId, A.OutstandingBalance, A.ProvisionAmount, CASE WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.Outst... |
| UPDATE | uncovered | Lines 37-50 | 03_batch3_main_body+batch3_nested_block:embedded_02_25, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = ( CASE WHEN S.CoverageRatio IS NULL THEN 'NO_BALANCE' WHEN S.CoverageRatio < 0.25 THEN 'SEVERE_UNDERCOVER' WHEN S.CoverageRatio < 0.5 THEN 'MODERATE_UNDERCOVER' WHEN S.CoverageRatio >= 0.5 AND S.CoverageRati... |
| UPDATE | covered_by_rule | Lines 53-55 | 03_batch3_main_body+batch3_nested_block:embedded_03_26, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = S.ReviewReason + '_QUARTER_END' FROM #ProvisionCoverage S WHERE S.CoverageRatio IS NOT NULL AND S.CoverageRatio < 0.6 |
| UPDATE | covered_by_rule | Lines 59-61 | 03_batch3_main_body+batch3_nested_block:embedded_04_27, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = S.ReviewReason FROM #ProvisionCoverage S WHERE S.CoverageRatio IS NOT NULL AND S.CoverageRatio < 0.5 |
| MERGE | covered_by_rule | Lines 67-81 | 03_batch3_main_body+batch3_nested_block:embedded_05_28, 03_batch3_main_body+batch3_nested_block | MERGE PRO.ProvisionCoverageSummary AS Target USING #ProvisionCoverage AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.OutstandingBalance = Source.OutstandingBalance, Target.ProvisionAmount = Source.Pr... |
| UPDATE | covered_by_rule | Lines 82-90 | 03_batch3_main_body+batch3_nested_block:embedded_06_29, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.BelowThresholdFlag = 'Y' FROM PRO.ProvisionCoverageSummary T WHERE T.CoverageRatio IS NOT NULL AND T.CoverageRatio < 0.5 AND T.LastUpdatedDate = @ProcessDate -- Rule 6: accounts at or above the threshold are cleared of any... |
| UPDATE | uncovered | Lines 91-99 | 03_batch3_main_body+batch3_nested_block:embedded_07_30, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.BelowThresholdFlag = 'N' FROM PRO.ProvisionCoverageSummary T WHERE T.CoverageRatio >= 0.5 AND T.LastUpdatedDate = @ProcessDate -- Rule 7: record a review case for every account newly below -- threshold - the escalation que... |
| INSERT | covered_by_rule | Lines 100-105 | 03_batch3_main_body+batch3_nested_block:embedded_08_31, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN CoverageRatio < 0.25 THEN 'SEVERE_PROVISION_SHORTFALL' ELSE 'MODERATE_PROVISION_SHORTFALL' END FROM #ProvisionCoverage WHERE R... |
| UPDATE | uncovered | Lines 107-109 | 03_batch3_main_body+batch3_nested_block:embedded_09_32, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Provision_Coverage_Merge' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Provision_Coverage_Merge' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_05, 04_batch3_exception | END |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Provision_Coverage_Merge' |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:embedded_02_07, 04_batch3_exception | SET NOCOUNT OFF |
| READ | uncovered | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| INSERT_TEMP | technical_only | samples/09_Provision_Coverage_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ProvisionCoverage (AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, ReviewReason) SELECT A.AccountId, A.OutstandingBalance, A.ProvisionAmount, CASE WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.Outst... |
| UPDATE_TEMP | technical_only | samples/09_Provision_Coverage_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = ( CASE WHEN S.CoverageRatio IS NULL THEN 'NO_BALANCE' WHEN S.CoverageRatio < 0.25 THEN 'SEVERE_UNDERCOVER' WHEN S.CoverageRatio < 0.5 THEN 'MODERATE_UNDERCOVER' WHEN S.CoverageRatio >= 0.5 AND S.CoverageRati... |
| UPDATE_TEMP | technical_only | samples/09_Provision_Coverage_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = S.ReviewReason + '_QUARTER_END' FROM #ProvisionCoverage S WHERE S.CoverageRatio IS NOT NULL AND S.CoverageRatio < 0.6 |
| UPDATE_TEMP | technical_only | samples/09_Provision_Coverage_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = S.ReviewReason FROM #ProvisionCoverage S WHERE S.CoverageRatio IS NOT NULL AND S.CoverageRatio < 0.5 |
| MERGE | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | MERGE PRO.ProvisionCoverageSummary AS Target USING #ProvisionCoverage AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.OutstandingBalance = Source.OutstandingBalance, Target.ProvisionAmount = Source.Pr... |
| UPDATE | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.BelowThresholdFlag = 'Y' FROM PRO.ProvisionCoverageSummary T WHERE T.CoverageRatio IS NOT NULL AND T.CoverageRatio < 0.5 AND T.LastUpdatedDate = @ProcessDate -- Rule 6: accounts at or above the threshold are cleared of any... |
| UPDATE | uncovered | samples/09_Provision_Coverage_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.BelowThresholdFlag = 'N' FROM PRO.ProvisionCoverageSummary T WHERE T.CoverageRatio >= 0.5 AND T.LastUpdatedDate = @ProcessDate -- Rule 7: record a review case for every account newly below -- threshold - the escalation que... |
| INSERT | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN CoverageRatio < 0.25 THEN 'SEVERE_PROVISION_SHORTFALL' ELSE 'MODERATE_PROVISION_SHORTFALL' END FROM #ProvisionCoverage WHERE R... |
| UPDATE | uncovered | samples/09_Provision_Coverage_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Provision_Coverage_Merge' |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_24, 03_batch3_main_body+batch3_nested_block:embedded_01_24, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ProvisionCoverage (AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, ReviewReason) SELECT A.AccountId, A.OutstandingBalance, A.ProvisionAmount, CASE WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.Outst... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_24, 03_batch3_main_body+batch3_nested_block:embedded_01_24, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ProvisionCoverage (AccountId, OutstandingBalance, ProvisionAmount, CoverageRatio, ReviewReason) SELECT A.AccountId, A.OutstandingBalance, A.ProvisionAmount, CASE WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.Outst... |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_25, 03_batch3_main_body+batch3_nested_block:embedded_02_25, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = ( CASE WHEN S.CoverageRatio IS NULL THEN 'NO_BALANCE' WHEN S.CoverageRatio < 0.25 THEN 'SEVERE_UNDERCOVER' WHEN S.CoverageRatio < 0.5 THEN 'MODERATE_UNDERCOVER' WHEN S.CoverageRatio >= 0.5 AND S.CoverageRati... |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_26, 03_batch3_main_body+batch3_nested_block:embedded_03_26, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = S.ReviewReason + '_QUARTER_END' FROM #ProvisionCoverage S WHERE S.CoverageRatio IS NOT NULL AND S.CoverageRatio < 0.6 |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_27, 03_batch3_main_body+batch3_nested_block:embedded_04_27, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.ReviewReason = S.ReviewReason FROM #ProvisionCoverage S WHERE S.CoverageRatio IS NOT NULL AND S.CoverageRatio < 0.5 |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_29, 03_batch3_main_body+batch3_nested_block:embedded_06_29, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.BelowThresholdFlag = 'Y' FROM PRO.ProvisionCoverageSummary T WHERE T.CoverageRatio IS NOT NULL AND T.CoverageRatio < 0.5 AND T.LastUpdatedDate = @ProcessDate -- Rule 6: accounts at or above the threshold are cleared of any... |
| UPDATE | uncovered | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_30, 03_batch3_main_body+batch3_nested_block:embedded_07_30, 03_batch3_main_body+batch3_nested_block | UPDATE T SET T.BelowThresholdFlag = 'N' FROM PRO.ProvisionCoverageSummary T WHERE T.CoverageRatio >= 0.5 AND T.LastUpdatedDate = @ProcessDate -- Rule 7: record a review case for every account newly below -- threshold - the escalation que... |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_31, 03_batch3_main_body+batch3_nested_block:embedded_08_31, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN CoverageRatio < 0.25 THEN 'SEVERE_PROVISION_SHORTFALL' ELSE 'MODERATE_PROVISION_SHORTFALL' END FROM #ProvisionCoverage WHERE R... |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_31, 03_batch3_main_body+batch3_nested_block:embedded_08_31, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN CoverageRatio < 0.25 THEN 'SEVERE_PROVISION_SHORTFALL' ELSE 'MODERATE_PROVISION_SHORTFALL' END FROM #ProvisionCoverage WHERE R... |
| UPDATE | uncovered | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_09_32, 03_batch3_main_body+batch3_nested_block:embedded_09_32, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Provision_Coverage_Merge' |
| UPDATE | uncovered | samples/09_Provision_Coverage_Merge.sql / Lines 129-136 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Provision_Coverage_Merge' |
| UPDATE | uncovered | unavailable | 04_batch3_exception:embedded_01_06, 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Provision_Coverage_Merge' |
| IF_BRANCH | covered_by_rule | Lines 40-54 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | A.OutstandingBalance > 0 |
| ELSE | covered_by_rule | Lines 40-54 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | ELSE |
| CASE | covered_by_rule | Lines 57-58 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | S.CoverageRatio IS NULL |
| CASE | covered_by_rule | Lines 58-59 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | S.CoverageRatio < 0.25 |
| CASE | covered_by_rule | Lines 59-60 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | S.CoverageRatio < 0.5 |
| CASE | covered_by_rule | Lines 60-61 | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | S.CoverageRatio >= 0.5 AND S.CoverageRatio < 1 |
| ELSE | covered_by_rule | Lines 61-62 | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | ELSE |
| IF_BRANCH | covered_by_rule | Lines 69-73 | 03_batch3_main_body+batch3_nested_block:chunk_text_18 | @ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate) |
| ELSE | covered_by_rule | Lines 75-79 | 03_batch3_main_body+batch3_nested_block:chunk_text_18 | ELSE |
| IF_BRANCH | covered_by_rule | Lines 117-124 | unavailable | CoverageRatio < 0.25 |
| ELSE | covered_by_rule | Lines 117-124 | unavailable | ELSE |
| IF_BRANCH | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | full_source | S.CoverageRatio IS NULL |
| IF_BRANCH | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | full_source | S.CoverageRatio < 0.25 |
| IF_BRANCH | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | full_source | S.CoverageRatio < 0.5 |
| IF_BRANCH | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | full_source | S.CoverageRatio >= 0.5 AND S.CoverageRatio < 1 |
| ELSE | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | full_source | T.CoverageRatio IS NOT NULL AND T.CoverageRatio < 0.5 AND T.LastUpdatedDate = @ProcessDate |
| IF_BRANCH | covered_by_rule | samples/09_Provision_Coverage_Merge.sql | full_source | T.CoverageRatio >= 0.5 AND T.LastUpdatedDate = @ProcessDate |
| IF | uncovered | Lines 26-26 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 44-44 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 45-45 | unavailable | WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.OutstandingBalance |
| CALCULATION | covered_by_rule | Lines 45-45 | unavailable | WHEN A.OutstandingBalance > 0 THEN A.ProvisionAmount / A.OutstandingBalance |
| ELSE | covered_by_rule | Lines 46-46 | unavailable | ELSE NULL |
| CASE | covered_by_rule | Lines 56-56 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 57-57 | unavailable | WHEN S.CoverageRatio IS NULL THEN |
| CASE_BRANCH | covered_by_rule | Lines 58-58 | unavailable | WHEN S.CoverageRatio < 0.25 THEN |
| CASE_BRANCH | covered_by_rule | Lines 59-59 | unavailable | WHEN S.CoverageRatio < 0.5 THEN |
| CASE_BRANCH | covered_by_rule | Lines 60-60 | unavailable | WHEN S.CoverageRatio >= 0.5 AND S.CoverageRatio < 1 THEN |
| ELSE | covered_by_rule | Lines 61-61 | unavailable | ELSE |
| IF | uncovered | Lines 68-68 | unavailable | IF @ProcessDate >= DATEADD(MONTH, 1, @QuarterStartDate) |
| ELSE | covered_by_rule | Lines 74-74 | unavailable | ELSE |
| CASE_BRANCH | covered_by_rule | Lines 87-87 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | covered_by_rule | Lines 93-93 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CASE | covered_by_rule | Lines 119-119 | unavailable | CASE WHEN CoverageRatio < 0.25 THEN ELSE END |
| CASE_BRANCH | covered_by_rule | Lines 119-119 | unavailable | CASE WHEN CoverageRatio < 0.25 THEN ELSE END |
| ELSE | covered_by_rule | Lines 119-119 | unavailable | CASE WHEN CoverageRatio < 0.25 THEN ELSE END |
| CATCH | uncovered | Lines 129-129 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 134-134 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_24 / #ProvisionCoverage | 03_batch3_main_body+batch3_nested_block:embedded_02_25 / #ProvisionCoverage | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_24 / #ProvisionCoverage | 03_batch3_main_body+batch3_nested_block:embedded_03_26 / #ProvisionCoverage | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_24 / #ProvisionCoverage | 03_batch3_main_body+batch3_nested_block:embedded_04_27 / #ProvisionCoverage | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_01_24 / #ProvisionCoverage | 03_batch3_main_body+batch3_nested_block:embedded_08_31 / #ProvisionCoverage | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_02_25 / #ProvisionCoverage | 03_batch3_main_body+batch3_nested_block:embedded_08_31 / #ProvisionCoverage | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_03_26 / #ProvisionCoverage | 03_batch3_main_body+batch3_nested_block:embedded_08_31 / #ProvisionCoverage | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_04_27 / #ProvisionCoverage | 03_batch3_main_body+batch3_nested_block:embedded_08_31 / #ProvisionCoverage | high |

Unresolved dependency candidates: 42. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 9
- **By rule type:** deterministic_decision_table = 2, explicit = 7
- **By validation status:** unverified = 3, verified = 6

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 17
- **Deterministic-only facts:** 19
- **LLM-only claims:** 2
- **Conflicts:** 6
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_7008b0d0ee1b`): full_source
- `CONFLICT` tables_written (`recon_7008b0d0ee1b`): full_source
- `CONFLICT` tables_written (`recon_7008b0d0ee1b`): full_source
- `CONFLICT` tables_written (`recon_7008b0d0ee1b`): full_source
- `LLM_ONLY` tables_written (`recon_149fb2b05528`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 75.91313131313133/100
- **Statement coverage:** 26 / 44 (59.1%)
- **Rule grounding coverage:** 6 / 9 (66.7%)
- **Decision-chain coverage:** 11 / 11 branches (100.0%)
- **Conflicts:** 6
- **Contradictions:** 9
- **Review required items:** 17
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `HIGH` Operation Conflict on `source`: Synthesized table operation conflicts with deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Operation Conflict on `source`: Synthesized table operation conflicts with deterministic SQL/AST evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: CASE WHEN CoverageRatio < 0.25 THEN 'SEVERE_PROVISION_SHORTFALL' ELSE 'MODERATE_PROVISION_SHORTFALL' END
- Synthesized in 3 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
