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
| Run Timestamp | `2026-09-16T10:00:51.061229+00:00` |
| Object ID | `obj_6df4a37e0d2e` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_983d1d8fc327` |
| Total LLM Calls | `8` |
| Successful Calls | `8` |
| Failed Calls | `0` |
| Prompt Tokens | `60079` |
| Completion Tokens | `11531` |
| Total Tokens | `71610` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 4982 | available |
| synthesis | 5 | 5 | 0 | 30249 | available |
| synthesis_revision | 2 | 2 | 0 | 36379 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| ⚠️ 1 | Classify asset based on days past due [MATCHED] (`rule__1`) | `AssetClass` | Classify the account's asset class based on the number of days past due. |
| ⚠️ 2 | Set NPA flag based on asset class [MATCHED] (`rule__2`) | `NpaFlag` | Set the NPA flag for active accounts based on the asset class. |
| ⚠️ 3 | Calculate additional provision [MATCHED] (`rule__3`) | `AddlProvision` | Calculate the additional provision for accounts flagged as NPA with a non-zero additional provisioning percentage. |
| ⚠️ 4 | Set classification date [MATCHED] (`rule__4`) | `ClassificationDate` | Set the classification date for accounts newly marked as NPA. |
| ⚠️ 5 | Set RestructureReviewFlag [MATCHED] (`rule__5`) | `RestructureReviewFlag` | Set the RestructureReviewFlag for accounts with overdue days between 61 and 90. |
| ⚠️ 6 | Update run status [MATCHED] (`rule__6`) | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Update the run status for the 'NPA_Classification_Simple' process. |
| 🔴 7 | Update run status on error [CONFLICT] (`rule__7`) | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an exception occurs during the 'NPA_Classification_Simple' process, update the run status to reflect the error. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify asset based on days past due (rule__1) | UPDATE A SET A.AssetClass = (CASE WHEN A.DaysPastDue <= 90 THEN 'STANDARD'... | Not cited | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | Verified |
| 2 | Set NPA flag based on asset class (rule__2) | UPDATE A SET A.NpaFlag = (CASE WHEN A.AssetClass = 'STANDARD' THEN 'N' ELSE 'Y' END) FROM PRO.AccountCal A WHERE A.AccountStatus = 'ACTIVE' | Not cited | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | Verified |
| 3 | Calculate additional provision (rule__3) | UPDATE A SET A.AddlProvision = (A.OutstandingBalance * A.AddlProvisionPer) / 100 FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND ISNULL(A.AddlProvisionPer, 0) <> 0 | Not cited | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | Verified |
| 4 | Set classification date (rule__4) | UPDATE A SET A.ClassificationDate = GETDATE() FROM PRO.AccountCal A WHERE A.NpaFlag = 'Y' AND A.ClassificationDate IS NULL | Not cited | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | Verified |
| 5 | Set RestructureReviewFlag (rule__5) | UPDATE A SET A.RestructureReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.DaysPastDue BETWEEN 61 AND 90 | Not cited | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_09 | Verified |
| 6 | Update run status (rule__6) | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' | Not cited | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_09 | Verified |
| 7 | Update run status on error (rule__7) | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Classification_Simple' | Not cited | Not cited | source_sql | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0028_0033_866:branch_001 | A.DaysPastDue <= 90 | source \| Lines 29-30 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0028_0033_866:branch_002 | A.DaysPastDue BETWEEN 91 AND 180 | source \| Lines 30-31 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0028_0033_866:branch_003 | A.DaysPastDue BETWEEN 181 AND 365 | source \| Lines 31-32 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0028_0033_866:branch_004 | ELSE | source \| Lines 32-33 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0041_0044_1351:branch_001 | A.AssetClass = 'STANDARD' | source \| Lines 42-43 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_06 |
| case_0041_0044_1351:branch_002 | ELSE | source \| Lines 43-44 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_06 |
| decision_chain_003:branch_001 | A.DaysPastDue <= 90 | source |
| decision_chain_003:branch_002 | A.DaysPastDue BETWEEN 91 AND 180 | source |
| decision_chain_003:branch_003 | A.DaysPastDue BETWEEN 181 AND 365 | source |
| decision_chain_003:branch_004 | A.AssetClass = 'STANDARD' | source |
| decision_chain_003:branch_005 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 63
- **Disposition:** covered_by_rule=51, uncovered=12

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
| IF_BRANCH | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | A.DaysPastDue <= 90 |
| IF_BRANCH | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | A.DaysPastDue BETWEEN 91 AND 180 |
| IF_BRANCH | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | A.DaysPastDue BETWEEN 181 AND 365 |
| IF_BRANCH | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | A.AssetClass = 'STANDARD' |
| ELSE | covered_by_rule | samples/01_NPA_Classification_Simple.sql | full_source | ELSE |
| CASE | covered_by_rule | Lines 28-28 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 29-29 | unavailable | WHEN A.DaysPastDue <= 90 THEN |
| CASE_BRANCH | uncovered | Lines 30-30 | unavailable | WHEN A.DaysPastDue BETWEEN 91 AND 180 THEN |
| CASE_BRANCH | uncovered | Lines 31-31 | unavailable | WHEN A.DaysPastDue BETWEEN 181 AND 365 THEN |
| ELSE | covered_by_rule | Lines 32-32 | unavailable | ELSE |
| CASE | covered_by_rule | Lines 41-41 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 42-42 | unavailable | WHEN A.AssetClass = THEN |
| ELSE | covered_by_rule | Lines 43-43 | unavailable | ELSE |
| CALCULATION | covered_by_rule | Lines 54-54 | unavailable | SET A.AddlProvision = (A.OutstandingBalance * A.AddlProvisionPer) / 100 |
| CATCH | uncovered | Lines 77-77 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 82-82 | unavailable | END CATCH |

## Confirmed Statement Dependencies


Unresolved dependency candidates: 41. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** explicit = 7
- **By validation status:** unverified = 1, verified = 6

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 10
- **Deterministic-only facts:** 12
- **LLM-only claims:** 0
- **Conflicts:** 2
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_eb4a6b6b61a8`): full_source
- `CONFLICT` rule (`recon_2dc17454b320`): rule__7, 03_batch3_main_body+batch3_nested_block:chunk_text_09;03_batch3_main_body+batch3_nested_block:embedded_06_16;04_batch3_exception:chunk_text_02;04_batch3_exception:embedded_01_05 - Deterministic evidence conflicts with the synthesized claim.
- `DETERMINISTIC_ONLY` coverage (`recon_60f34e34dad0`): 03_batch3_main_body+batch3_nested_block, 03_batch3_main_body+batch3_nested_block:chunk_text_04 - Deterministic evidence is present in the source but no synthesized rule referenced it.
- `DETERMINISTIC_ONLY` coverage (`recon_60f34e34dad0`): 03_batch3_main_body+batch3_nested_block, 03_batch3_main_body+batch3_nested_block:chunk_text_05 - Deterministic evidence is present in the source but no synthesized rule referenced it.
- `DETERMINISTIC_ONLY` coverage (`recon_60f34e34dad0`): 03_batch3_main_body+batch3_nested_block, 03_batch3_main_body+batch3_nested_block:chunk_text_07 - Deterministic evidence is present in the source but no synthesized rule referenced it.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 88.4/100
- **Statement coverage:** 18 / 26 (69.2%)
- **Rule grounding coverage:** 7 / 7 (100.0%)
- **Decision-chain coverage:** 6 / 6 branches (100.0%)
- **Conflicts:** 2
- **Contradictions:** 3
- **Review required items:** 5
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule__7`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- One or more ambiguities showed signs of repetition-degeneration or mid-sentence truncation and were dropped rather than included in the report.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.AssetClass = (CASE WHEN A.AssetClass = 'STANDARD' THEN 'N' ELSE A.AssetClass END) FROM PRO.AccountCal A WHERE A.AccountStatus = 'ACTIVE'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.NpaFlag = (CASE WHEN A.NpaFlag = 'Y' AND COALESCE(A.AddlProvisionPer, 0) <> 0 THEN 'Y' ELSE A.NpaFlag END) FROM PRO.AccountCal A WHERE A.AccountStatus = 'ACTIVE'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.RestructureReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.AccountStatus = 'ACTIVE' AND A.DaysPastDue BETWEEN 61 AND 90
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A
        SET A.ClassificationDate = GETDATE()
        FROM PRO.AccountCal A
        WHERE A.NpaFlag = 'Y'
          AND A.ClassificationDate IS NULL
- Synthesized in 5 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
