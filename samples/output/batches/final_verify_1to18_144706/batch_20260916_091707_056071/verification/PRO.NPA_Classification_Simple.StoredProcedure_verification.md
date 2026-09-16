# NPA Classification Simple — Verification & Traceability

> Companion artifact to `PRO.NPA_Classification_Simple.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_6df4a37e0d2e` |
| Raw technical object name (from source) | `NPA_Classification_Simple` |

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
| Source Hash | `457174dc853a88d1f08fbd42ccd79e17f4bd6cf6b5389078bdab330ea3f3f7dd` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:17:07.078334+00:00` |
| Object ID | `obj_6df4a37e0d2e` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_b0e19998790d` |
| Total LLM Calls | `7` |
| Successful Calls | `7` |
| Failed Calls | `0` |
| Prompt Tokens | `45126` |
| Completion Tokens | `8200` |
| Total Tokens | `53326` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 5005 | available |
| synthesis | 5 | 5 | 0 | 29418 | available |
| synthesis_revision | 1 | 1 | 0 | 18903 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟢 1 | Update RestructureReviewFlag [MATCHED] (`rule__2__10`) | `RestructureReviewFlag` | Set the RestructureReviewFlag to 'Y' for accounts with overdue days between 61 and 90. |
| 🟢 2 | Update RunStatus [MATCHED] (`rule__3__11`) | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Mark the 'NPA_Classification_Simple' process as completed and increment the run count. |
| 🟠 3 | Determine AssetClass [MATCHED] (`deterministic_case_0028_0033_866_assetclass`) | `AssetClass` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 4 | Determine NpaFlag [MATCHED] (`deterministic_case_0041_0044_1351_npaflag`) | `NpaFlag` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 5 | Classify NPAs based on time key [LLM_ONLY] (`rule__1`) | `Not specified` | Classifies non-performing assets based on the provided time key. |
| 🟢 6 | Determine asset class [MATCHED] (`rule__1__2`) | `AssetClass` | Classify the account's asset class based on the number of days past due. |
| 🟠 7 | Calculate additional provision [LLM_ONLY] (`rule__2`) | `AddlProvision` | Compute the additional provision for accounts with a specific NPA flag and non-zero additional provision percentage. |
| 🔴 8 | Update run status [CONFLICT] (`rule__3`) | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Mark the NPA classification process as completed and increment the run count. |
| 🔴 9 | Set NpaFlag to 'Y' [CONFLICT] (`rule__1__5`) | `NpaFlag` | If an account is flagged as NPA and its asset class is not 'STANDARD', set the NpaFlag to 'Y'. |
| 🟢 10 | Calculate AddlProvision [MATCHED] (`rule__2__6`) | `AddlProvision` | Calculate the additional provision for accounts flagged as NPA with a non-zero additional provision percentage. |
| 🟢 11 | Set ClassificationDate [MATCHED] (`rule__3__7`) | `ClassificationDate` | Set the ClassificationDate for accounts newly marked as NPA this run. |
| 🟢 12 | Update RunStatus [MATCHED] (`rule__4`) | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Update the process status in the PRO.RunStatus table. |
| 🔴 13 | Update run status on error [CONFLICT] (`rule__1__12`) | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an error occurs during the 'NPA_Classification_Simple' process, the run status is marked as incomplete, the error date is set to the cur… |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Update RestructureReviewFlag (rule__2__10) | A.DaysPastDue BETWEEN 61 AND 90 | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | 03_batch3_main_body+batch3_nested_block:chunk_text_08 | Verified |
| 2 | Update RunStatus (rule__3__11) | ProcessName = 'NPA_Classification_Simple' | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_09; 03_batch3_main_body+batch3_nested_block:embedded_06_16 | 03_batch3_main_body+batch3_nested_block:chunk_text_09; 03_batch3_main_body+batch3_nested_block:embedded_06_16 | Verified |
| 3 | Determine AssetClass (deterministic_case_0028_0033_866_assetclass) | Not cited | source \| Lines 28-33 | Not cited | Not cited | Verified |
| 4 | Determine NpaFlag (deterministic_case_0041_0044_1351_npaflag) | Not cited | source \| Lines 41-44 | Not cited | Not cited | Verified |
| 5 | Classify NPAs based on time key (rule__1) | Not cited | Not cited | Not cited | Not cited | Verified |
| 6 | Determine asset class (rule__1__2) | UPDATE A SET A.AssetClass = (CASE WHEN A.DaysPastDue <= 90 THEN 'STANDARD' WHEN A.DaysPastDue BETWEEN 91 AND 180 THEN 'SUBSTANDARD' WHEN A.DaysPastDue BETWEEN 181 AND 365 THEN 'DOUBTFUL' END) | Not cited | Not cited | Not cited | Verified |
| 7 | Calculate additional provision (rule__2) | UPDATE A SET A.AddlProvision = (A.OutstandingBalance * A.AddlProvisionPer) / 100 | Not cited | Not cited | Not cited | Needs Review |
| 8 | Update run status (rule__3) | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' | Not cited | Not cited | Not cited | Needs Review |
| 9 | Set NpaFlag to 'Y' (rule__1__5) | UPDATE A SET A.NpaFlag = (CASE WHEN A.AssetClass = 'STANDARD' THEN 'N' ELSE 'Y' END) FROM PRO.AccountCal A WHERE A.AccountStatus = 'ACTIVE' | Not cited | Not cited | Not cited | Needs Review |
| 10 | Calculate AddlProvision (rule__2__6) | UPDATE A SET A.AddlProvision = (A.OutstandingBalance * A.AddlProvisionPer) / 100 FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND ISNULL(A.AddlProvisionPer, 0) <> 0 | Not cited | Not cited | Not cited | Verified |
| 11 | Set ClassificationDate (rule__3__7) | UPDATE A SET A.ClassificationDate = @ProcessDate FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND A.ClassificationDate IS NULL | Not cited | Not cited | Not cited | Verified |
| 12 | Update RunStatus (rule__4) | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' | Not cited | Not cited | Not cited | Verified |
| 13 | Update run status on error (rule__1__12) | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' | Not cited | Not cited | source_sql | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0028_0033_866:branch_001 | A.DaysPastDue <= 90 | source \| Lines 29-30 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0028_0033_866:branch_002 | A.DaysPastDue BETWEEN 91 AND 180 | source \| Lines 30-31 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0028_0033_866:branch_003 | A.DaysPastDue BETWEEN 181 AND 365 | source \| Lines 31-32 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0028_0033_866:branch_004 | ELSE | source \| Lines 32-33 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0041_0044_1351:branch_001 | A.AssetClass = 'STANDARD' | source \| Lines 42-43 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_06 |
| case_0041_0044_1351:branch_002 | ELSE | source \| Lines 43-44 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_06 |
| decision_chain_003:branch_001 | WHEN A.DaysPastDue <= 90 | source |
| decision_chain_003:branch_002 | WHEN A.DaysPastDue BETWEEN 91 AND 180 | source |
| decision_chain_003:branch_003 | WHEN A.DaysPastDue BETWEEN 181 AND 365 | source |
| decision_chain_003:branch_004 | ELSE | source |
| decision_chain_003:branch_005 | WHEN A.AssetClass = 'STANDARD' | source |
| decision_chain_003:branch_006 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 64
- **Disposition:** covered_by_rule=55, uncovered=9

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | covered_by_rule | Lines 1-2 | 03_batch3_main_body+batch3_nested_block:chunk_text_01, 03_batch3_main_body+batch3_nested_block | BEGIN SET NOCOUNT ON |
| STATEMENT | covered_by_rule | Lines 4-4 | 03_batch3_main_body+batch3_nested_block:chunk_text_02, 03_batch3_main_body+batch3_nested_block | BEGIN TRY |
| SELECT | covered_by_rule | Lines 6-8 | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) -- Rule 1: classify the account's asset class by days-past-due |
| UPDATE | covered_by_rule | Lines 9-21 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = ( CASE WHEN A.DaysPastDue <= 90 THEN 'STANDARD' WHEN A.DaysPastDue BETWEEN 91 AND 180 THEN 'SUBSTANDARD' WHEN A.DaysPastDue BETWEEN 181 AND 365 THEN 'DOUBTFUL' ELSE 'LOSS' END ) FROM PRO.AccountCal A WHERE A.A... |
| UPDATE | covered_by_rule | Lines 22-35 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.NpaFlag = ( CASE WHEN A.AssetClass = 'STANDARD' THEN 'N' ELSE 'Y' END ) FROM PRO.AccountCal A WHERE A.AccountStatus = 'ACTIVE' -- Rule 3 (formula, sourced from PRO.UpdateNetBalance_AccountWise / -- InsertDataforAssetClassf... |
| UPDATE | covered_by_rule | Lines 36-42 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AddlProvision = (A.OutstandingBalance * A.AddlProvisionPer) / 100 FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND ISNULL(A.AddlProvisionPer, 0) <> 0 -- Rule 4: stamp the classification date on accounts newly marked NPA thi... |
| UPDATE | covered_by_rule | Lines 43-49 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ClassificationDate = @ProcessDate FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND A.ClassificationDate IS NULL -- Rule 5: flag accounts approaching NPA (61-90 days overdue) for restructuring review |
| UPDATE | covered_by_rule | Lines 50-53 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.DaysPastDue BETWEEN 61 AND 90 |
| UPDATE | covered_by_rule | Lines 55-57 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' |
| STATEMENT | covered_by_rule | Lines 59-59 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 9-21 | 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = ( CASE WHEN A.DaysPastDue <= 90 THEN 'STANDARD' WHEN A.DaysPastDue BETWEEN 91 AND 180 THEN 'SUBSTANDARD' WHEN A.DaysPastDue BETWEEN 181 AND 365 THEN 'DOUBTFUL' ELSE 'LOSS' END ) FROM PRO.AccountCal A WHERE A.A... |
| UPDATE | covered_by_rule | Lines 22-35 | 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.NpaFlag = ( CASE WHEN A.AssetClass = 'STANDARD' THEN 'N' ELSE 'Y' END ) FROM PRO.AccountCal A WHERE A.AccountStatus = 'ACTIVE' -- Rule 3 (formula, sourced from PRO.UpdateNetBalance_AccountWise / -- InsertDataforAssetClassf... |
| UPDATE | covered_by_rule | Lines 36-42 | 03_batch3_main_body+batch3_nested_block:embedded_03_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AddlProvision = (A.OutstandingBalance * A.AddlProvisionPer) / 100 FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND ISNULL(A.AddlProvisionPer, 0) <> 0 -- Rule 4: stamp the classification date on accounts newly marked NPA thi... |
| UPDATE | covered_by_rule | Lines 43-49 | 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ClassificationDate = @ProcessDate FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND A.ClassificationDate IS NULL -- Rule 5: flag accounts approaching NPA (61-90 days overdue) for restructuring review |
| UPDATE | covered_by_rule | Lines 50-53 | 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.DaysPastDue BETWEEN 61 AND 90 |
| UPDATE | covered_by_rule | Lines 55-57 | 03_batch3_main_body+batch3_nested_block:embedded_06_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | END |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) -- Rule 1: classify the account's asset class by days-past-due |
| UPDATE | covered_by_rule | samples/01_NPA_Classification_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = ( CASE WHEN A.DaysPastDue <= 90 THEN 'STANDARD' WHEN A.DaysPastDue BETWEEN 91 AND 180 THEN 'SUBSTANDARD' WHEN A.DaysPastDue BETWEEN 181 AND 365 THEN 'DOUBTFUL' ELSE 'LOSS' END ) FROM PRO.AccountCal A WHERE A.A... |
| UPDATE | covered_by_rule | samples/01_NPA_Classification_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.NpaFlag = ( CASE WHEN A.AssetClass = 'STANDARD' THEN 'N' ELSE 'Y' END ) FROM PRO.AccountCal A WHERE A.AccountStatus = 'ACTIVE' -- Rule 3 (formula, sourced from PRO.UpdateNetBalance_AccountWise / -- InsertDataforAssetClassf... |
| UPDATE | covered_by_rule | samples/01_NPA_Classification_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AddlProvision = (A.OutstandingBalance * A.AddlProvisionPer) / 100 FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND ISNULL(A.AddlProvisionPer, 0) <> 0 -- Rule 4: stamp the classification date on accounts newly marked NPA thi... |
| UPDATE | covered_by_rule | samples/01_NPA_Classification_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ClassificationDate = @ProcessDate FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND A.ClassificationDate IS NULL -- Rule 5: flag accounts approaching NPA (61-90 days overdue) for restructuring review |
| UPDATE | covered_by_rule | samples/01_NPA_Classification_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.DaysPastDue BETWEEN 61 AND 90 |
| UPDATE | covered_by_rule | samples/01_NPA_Classification_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = ( CASE WHEN A.DaysPastDue <= 90 THEN 'STANDARD' WHEN A.DaysPastDue BETWEEN 91 AND 180 THEN 'SUBSTANDARD' WHEN A.DaysPastDue BETWEEN 181 AND 365 THEN 'DOUBTFUL' ELSE 'LOSS' END ) FROM PRO.AccountCal A WHERE A.A... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.NpaFlag = ( CASE WHEN A.AssetClass = 'STANDARD' THEN 'N' ELSE 'Y' END ) FROM PRO.AccountCal A WHERE A.AccountStatus = 'ACTIVE' -- Rule 3 (formula, sourced from PRO.UpdateNetBalance_AccountWise / -- InsertDataforAssetClassf... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_13, 03_batch3_main_body+batch3_nested_block:embedded_03_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AddlProvision = (A.OutstandingBalance * A.AddlProvisionPer) / 100 FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND ISNULL(A.AddlProvisionPer, 0) <> 0 -- Rule 4: stamp the classification date on accounts newly marked NPA thi... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ClassificationDate = @ProcessDate FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND A.ClassificationDate IS NULL -- Rule 5: flag accounts approaching NPA (61-90 days overdue) for restructuring review |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.DaysPastDue BETWEEN 61 AND 90 |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_16, 03_batch3_main_body+batch3_nested_block:embedded_06_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' |
| UPDATE | covered_by_rule | samples/01_NPA_Classification_Simple.sql / Lines 77-83 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' |
| UPDATE | covered_by_rule | unavailable | 04_batch3_exception:embedded_01_05, 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' |
| CASE | covered_by_rule | Lines 29-30 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | A.DaysPastDue <= 90 |
| CASE | covered_by_rule | Lines 30-31 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | A.DaysPastDue BETWEEN 91 AND 180 |
| CASE | covered_by_rule | Lines 31-32 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | A.DaysPastDue BETWEEN 181 AND 365 |
| ELSE | covered_by_rule | Lines 32-33 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | ELSE |
| CASE | covered_by_rule | Lines 42-43 | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | A.AssetClass = 'STANDARD' |
| ELSE | covered_by_rule | Lines 43-44 | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | ELSE |
| IF_BRANCH | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | WHEN A.DaysPastDue <= 90 |
| IF_BRANCH | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | WHEN A.DaysPastDue BETWEEN 91 AND 180 |
| IF_BRANCH | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | WHEN A.DaysPastDue BETWEEN 181 AND 365 |
| ELSE | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | WHEN A.AssetClass = 'STANDARD' |
| ELSE | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | ELSE |
| CASE | covered_by_rule | Lines 28-28 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 29-29 | unavailable | WHEN A.DaysPastDue <= 90 THEN |
| CASE_BRANCH | covered_by_rule | Lines 30-30 | unavailable | WHEN A.DaysPastDue BETWEEN 91 AND 180 THEN |
| CASE_BRANCH | covered_by_rule | Lines 31-31 | unavailable | WHEN A.DaysPastDue BETWEEN 181 AND 365 THEN |
| ELSE | covered_by_rule | Lines 32-32 | unavailable | ELSE |
| CASE | covered_by_rule | Lines 41-41 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 42-42 | unavailable | WHEN A.AssetClass = THEN |
| ELSE | covered_by_rule | Lines 43-43 | unavailable | ELSE |
| CALCULATION | covered_by_rule | Lines 54-54 | unavailable | SET A.AddlProvision = (A.OutstandingBalance * A.AddlProvisionPer) / 100 |
| CATCH | uncovered | Lines 77-77 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 82-82 | unavailable | END CATCH |

## Confirmed Statement Dependencies


Unresolved dependency candidates: 41. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 13
- **By rule type:** deterministic_decision_table = 2, explicit = 11
- **By validation status:** unverified = 4, verified = 9

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 12
- **Deterministic-only facts:** 2
- **LLM-only claims:** 2
- **Conflicts:** 4
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_eb4a6b6b61a8`): full_source
- `LLM_ONLY` rule (`recon_9c2717fb4b7a`): rule__1 - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_b454d4bb6cf1`): rule__2 - No deterministic evidence was found for this claim.
- `CONFLICT` rule (`recon_51ddf729d185`): rule__3, 03_batch3_main_body+batch3_nested_block:chunk_text_09;03_batch3_main_body+batch3_nested_block:embedded_06_16;04_batch3_exception:chunk_text_02;04_batch3_exception:embedded_01_05 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_a8bf393bad07`): rule__1__5, 03_batch3_main_body+batch3_nested_block:chunk_text_05;03_batch3_main_body+batch3_nested_block:chunk_text_06;03_batch3_main_body+batch3_nested_block:embedded_02_12 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 76.28893058161351/100
- **Statement coverage:** 18 / 26 (69.2%)
- **Rule grounding coverage:** 9 / 13 (69.2%)
- **Decision-chain coverage:** 6 / 6 branches (100.0%)
- **Conflicts:** 4
- **Contradictions:** 6
- **Review required items:** 12
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `rule__3`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Condition Conflict on `rule__1__5`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule__1__12`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: No source evidence was provided for the synthesized rule.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.AssetClass = (CASE WHEN A.DaysPastDue <= 90 THEN 'STANDARD' WHEN A.DaysPastDue BETWEEN 91 AND 180 THEN 'SUBSTANDARD' WHEN A.DaysPastDue BETWEEN 181 AND 365 THEN 'DOUBTFUL' END)
- Synthesized in 5 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
