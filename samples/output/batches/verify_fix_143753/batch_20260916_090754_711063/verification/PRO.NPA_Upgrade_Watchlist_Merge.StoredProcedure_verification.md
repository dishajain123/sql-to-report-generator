# NPA Upgrade Watchlist Merge — Verification & Traceability

> Companion artifact to `PRO.NPA_Upgrade_Watchlist_Merge.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_487edfd00cd3` |
| Raw technical object name (from source) | `NPA_Upgrade_Watchlist_Merge` |

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
| Source Hash | `e9da111153acb52b0740fcc4803ef165c0400a479e089385010a9437a8eba1a4` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:10:45.400185+00:00` |
| Object ID | `obj_487edfd00cd3` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_8fcdb861f425` |
| Total LLM Calls | `8` |
| Successful Calls | `8` |
| Failed Calls | `0` |
| Prompt Tokens | `83178` |
| Completion Tokens | `18326` |
| Total Tokens | `101504` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 6891 | available |
| synthesis | 6 | 6 | 0 | 65257 | available |
| synthesis_revision | 1 | 1 | 0 | 29356 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Determine EligibleForUpgrade [MATCHED] (`deterministic_tsql_if_0073_0087_eligibleforupgrade`) | `EligibleForUpgrade` | Not specified |
| 🟠 2 | Update DaysSinceLastOverdue [LLM_ONLY] (`rule__1`) | `DaysSinceLastOverdue` | Update the 'DaysSinceLastOverdue' field in the 'PRO.LoanAccountCal' table. |
| 🟠 3 | Insert into WatchlistStaging [LLM_ONLY] (`rule__2`) | `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade` | Insert records into the '#WatchlistStaging' table with initial values for 'AccountId', 'AssetClass', 'DaysSinceLastOverdue', and 'EligibleF… |
| 🟠 4 | Update EligibleForUpgrade 1 [LLM_ONLY] (`rule__3`) | `EligibleForUpgrade` | Update the 'EligibleForUpgrade' field in the '#WatchlistStaging' table based on certain conditions. |
| 🟠 5 | Update EligibleForUpgrade 2 [LLM_ONLY] (`rule__4`) | `EligibleForUpgrade` | Update the 'EligibleForUpgrade' field in the '#WatchlistStaging' table based on certain conditions. |
| 🟠 6 | Update EligibleForUpgrade 3 [LLM_ONLY] (`rule__5`) | `EligibleForUpgrade` | Update the 'EligibleForUpgrade' field in the '#WatchlistStaging' table based on certain conditions. |
| 🟠 7 | Update AssetClass and UpgradeDate [LLM_ONLY] (`rule__6`) | `AssetClass, UpgradeDate` | Update the 'AssetClass' and 'UpgradeDate' fields in the 'PRO.LoanAccountCal' table. |
| 🟢 8 | Calculate DaysSinceLastOverdue [MATCHED] (`rule__1__7`) | `DaysSinceLastOverdue` | Calculate the number of days since the last overdue date for accounts that are not classified as 'STANDARD', have no overdue days, and have… |
| 🔴 9 | Stage eligible accounts for upgrade [CONFLICT] (`rule__2__8`) | `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade` | Stage accounts that are not classified as 'STANDARD', have no overdue days, and have a LastOverdueClearedDate that is not null and is less… |
| 🔴 10 | Update EligibleForUpgrade in temporary table [CONFLICT] (`rule__3__9`) | `EligibleForUpgrade` | Update the EligibleForUpgrade field in the temporary table to 'Y' for accounts that meet specific criteria. |
| 🟠 11 | Merge temporary table into NPA Upgrade Watchlist [LLM_ONLY] (`rule__4__10`) | `Target.AccountId, Source.AccountId, Target.DaysSinceLastOverdue, Source.DaysSinceLastOverdue, Target.EligibleForUpgrade, Source.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate, Source.AssetClass` | Merge data from the temporary table into the NPA Upgrade Watchlist. |
| 🔴 12 | Delete records from NPA Upgrade Watchlist [CONFLICT] (`rule__5__11`) | `AccountId, OverdueDays, EligibleForUpgrade` | Delete records from the NPA Upgrade Watchlist that meet specific criteria. |
| 🟢 13 | Calculate DaysSinceLastOverdue [MATCHED] (`rule__1__12`) | `DaysSinceLastOverdue` | Calculate the number of days since the last overdue date for accounts that are not standard and have no overdue days. |
| 🟢 14 | Stage eligible accounts for upgrade [MATCHED] (`rule__2__13`) | `EligibleForUpgrade` | Stage accounts for upgrade eligibility based on asset class and days since last overdue. |
| 🟢 15 | Update EligibleForUpgrade status [MATCHED] (`rule__3__14`) | `EligibleForUpgrade` | Update the EligibleForUpgrade status for accounts in the staging table. |
| 🟠 16 | Merge NPA Upgrade Watchlist records [UNRESOLVED] (`rule__4__15`) | `Not specified` | Merge, insert, update, and delete records in the NPA Upgrade Watchlist based on account status and overdue days. |
| 🟢 17 | Update DaysSinceLastOverdue [MATCHED] (`rule__1__16`) | `DaysSinceLastOverdue` | Calculate the number of days since the last overdue date was cleared for accounts that are not standard, have no overdue days, and have a c… |
| 🟢 18 | Delete Eligible Accounts from NPA Upgrade Watchlist [MATCHED] (`rule__8`) | `Not specified` | Delete records from the NPA Upgrade Watchlist where the account is eligible for upgrade. |
| 🟠 19 | Merge into NpaUpgradeWatchlist [LLM_ONLY] (`rule__4__19`) | `Target.DaysSinceLastOverdue, Target.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate` | Merge data from the WatchlistStaging table into the NpaUpgradeWatchlist table. |
| 🟠 20 | Delete Overdue Accounts from NPA Upgrade Watchlist [UNRESOLVED] (`rule__5__24`) | `Not specified` | Delete records from the NPA Upgrade Watchlist where the account has overdue days. |
| 🔴 21 | Update Asset Class and Upgrade Date [CONFLICT] (`rule__6__25`) | `AssetClass, UpgradeDate` | Update the asset class and upgrade date for accounts in the Loan Account Calculation table that are eligible for upgrade. |
| 🔴 22 | Insert Account Status Audit Log [CONFLICT] (`rule__7`) | `AccountId, TransitionDate, NewStatus, Reason` | Insert a record into the Account Status Audit Log for accounts that have been marked as 'STANDARD' and have an upgrade date matching the pr… |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Determine EligibleForUpgrade (deterministic_tsql_if_0073_0087_eligibleforupgrade) | Not cited | source \| Lines 73-87 | Not cited | Not cited | Verified |
| 2 | Update DaysSinceLastOverdue (rule__1) | A.DaysSinceLastOverdue is updated | Not cited | Not cited | Not cited | Needs Review |
| 3 | Insert into WatchlistStaging (rule__2) | Insert into '#WatchlistStaging' table | Not cited | Not cited | Not cited | Needs Review |
| 4 | Update EligibleForUpgrade 1 (rule__3) | Update 'EligibleForUpgrade' field in '#WatchlistStaging' table | Not cited | Not cited | Not cited | Needs Review |
| 5 | Update EligibleForUpgrade 2 (rule__4) | Update 'EligibleForUpgrade' field in '#WatchlistStaging' table | Not cited | Not cited | Not cited | Needs Review |
| 6 | Update EligibleForUpgrade 3 (rule__5) | Update 'EligibleForUpgrade' field in '#WatchlistStaging' table | Not cited | Not cited | Not cited | Needs Review |
| 7 | Update AssetClass and UpgradeDate (rule__6) | Update 'AssetClass' and 'UpgradeDate' fields in 'PRO.LoanAccountCal' table | Not cited | Not cited | Not cited | Needs Review |
| 8 | Calculate DaysSinceLastOverdue (rule__1__7) | UPDATE A SET A.DaysSinceLastOverdue = DATEDIFF(DAY, A.LastOverdueClearedDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate IS NOT NULL AND A.LastOverdueClearedDate <= @ProcessDate | Not cited | Not cited | Not cited | Verified |
| 9 | Stage eligible accounts for upgrade (rule__2__8) | INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) SELECT AccountId, AssetClass, DaysSinceLastOverdue, 'N' FROM PRO.LoanAccountCal WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate… | Not cited | Not cited | Not cited | Needs Review |
| 10 | Update EligibleForUpgrade in temporary table (rule__3__9) | UPDATE #WatchlistStaging SET S.EligibleForUpgrade = 'Y' WHERE S.EligibleForUpgrade = 'Y' | Not cited | Not cited | Not cited | Needs Review |
| 11 | Merge temporary table into NPA Upgrade Watchlist (rule__4__10) | MERGE INTO PRO.NpaUpgradeWatchlist USING #WatchlistStaging ON Target.AccountId = Source.AccountId | Not cited | Not cited | Not cited | Needs Review |
| 12 | Delete records from NPA Upgrade Watchlist (rule__5__11) | DELETE FROM PRO.NpaUpgradeWatchlist WHERE AccountId IN (SELECT AccountId FROM PRO.LoanAccountCal WHERE OverdueDays > 0) | Not cited | Not cited | Not cited | Needs Review |
| 13 | Calculate DaysSinceLastOverdue (rule__1__12) | UPDATE A SET A.DaysSinceLastOverdue = DATEDIFF(DAY, A.LastOverdueClearedDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate IS NOT NULL AND A.LastOverdueClearedDate <= @ProcessDate | Not cited | Not cited | Not cited | Verified |
| 14 | Stage eligible accounts for upgrade (rule__2__13) | UPDATE S SET S.EligibleForUpgrade = (CASE WHEN S.DaysSinceLastOverdue IS NULL THEN 'N' WHEN S.AssetClass = 'SUBSTANDARD' AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays THEN 'Y' WHEN S.AssetClass IN ('DOUBTFUL', 'LOSS') AND S.DaysSinceLastOverdue >= @D… | Not cited | Not cited | Not cited | Verified |
| 15 | Update EligibleForUpgrade status (rule__3__14) | IF DAY(@ProcessDate) = 1 BEGIN UPDATE S SET S.EligibleForUpgrade = 'PENDING_APPROVAL' FROM #WatchlistStaging S END | Not cited | Not cited | Not cited | Verified |
| 16 | Merge NPA Upgrade Watchlist records (rule__4__15) | MERGE INTO PRO.NpaUpgradeWatchlist; DELETE FROM PRO.NpaUpgradeWatchlist WHERE AccountId IN (SELECT AccountId FROM PRO.LoanAccountCal WHERE OverdueDays > 0); INSERT INTO PRO.NpaUpgradeWatchlist | Not cited | Not cited | Not cited | Needs Review |
| 17 | Update DaysSinceLastOverdue (rule__1__16) | UPDATE A SET A.DaysSinceLastOverdue = DATEDIFF(DAY, A.LastOverdueClearedDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate IS NOT NULL AND A.LastOverdueClearedDate <= @ProcessDate | Not cited | Not cited | Not cited | Verified |
| 18 | Delete Eligible Accounts from NPA Upgrade Watchlist (rule__8) | DELETE FROM PRO.NpaUpgradeWatchlist WHERE EligibleForUpgrade = 'Y' | Not cited | Not cited | Not cited | Verified |
| 19 | Merge into NpaUpgradeWatchlist (rule__4__19) | MERGE PRO.NpaUpgradeWatchlist AS Target USING #WatchlistStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DaysSinceLastOverdue = Source.DaysSinceLastOverdue, Target.EligibleForUpgrade = Source.EligibleForUpgrade, Tar… | Not cited | Not cited | Not cited | Needs Review |
| 20 | Delete Overdue Accounts from NPA Upgrade Watchlist (rule__5__24) | DELETE FROM PRO.NpaUpgradeWatchlist WHERE AccountId IN (SELECT AccountId FROM PRO.LoanAccountCal WHERE OverdueDays > 0) | Not cited | Not cited | Not cited | Needs Review |
| 21 | Update Asset Class and Upgrade Date (rule__6__25) | UPDATE A SET A.AssetClass = 'STANDARD', A.UpgradeDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId = A.AccountId AND W.AssetClass = A.AssetClass WHERE W.EligibleForUpgrade = 'Y' | Not cited | Not cited | Not cited | Needs Review |
| 22 | Insert Account Status Audit Log (rule__7) | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT A.AccountId, @ProcessDate, 'STANDARD', 'NPA_WATCH_PERIOD_COMPLETE' FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId = A.AccountId WHERE W.… | Not cited | Not cited | Not cited | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0061_0066_2296:branch_001 | S.DaysSinceLastOverdue IS NULL | source \| Lines 62-63 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_14 |
| case_0061_0066_2296:branch_002 | S.AssetClass = 'SUBSTANDARD' AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays | source \| Lines 63-64 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_14 |
| case_0061_0066_2296:branch_003 | S.AssetClass IN ('DOUBTFUL', 'LOSS') AND S.DaysSinceLastOverdue >= @DoubtfulWatchPeriodDays | source \| Lines 64-65 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_18 |
| case_0061_0066_2296:branch_004 | ELSE | source \| Lines 65-66 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_18 |
| tsql_if_0073_0087:branch_001 | DAY(@ProcessDate) = 1 | source \| Lines 74-79 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_20 |
| tsql_if_0073_0087:branch_002 | ELSE | source \| Lines 81-84 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_20 |
| decision_chain_003:branch_001 | S.DaysSinceLastOverdue IS NULL | source |
| decision_chain_003:branch_002 | S.AssetClass = 'SUBSTANDARD' AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays | source |
| decision_chain_003:branch_003 | S.AssetClass IN ('DOUBTFUL', 'LOSS') AND S.DaysSinceLastOverdue >= @DoubtfulWatchPeriodDays | source |
| decision_chain_003:branch_004 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 99
- **Disposition:** covered_by_rule=51, technical_only=8, uncovered=40

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
| STATEMENT | uncovered | Lines 7-7 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @StandardWatchPeriodDays INT = 365 |
| STATEMENT | uncovered | Lines 8-8 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | DECLARE @DoubtfulWatchPeriodDays INT = 545 |
| STATEMENT | uncovered | Lines 10-10 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | IF OBJECT_ID('tempdb..#WatchlistStaging') IS NOT NULL |
| STATEMENT | uncovered | Lines 11-11 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | DROP TABLE #WatchlistStaging |
| STATEMENT | uncovered | Lines 13-23 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | CREATE TABLE #WatchlistStaging ( AccountId VARCHAR(20), AssetClass VARCHAR(20), DaysSinceLastOverdue INT, EligibleForUpgrade VARCHAR(1) ) -- Rule 1: date comparison/derivation - recompute how many days -- have elapsed since the account l... |
| UPDATE | covered_by_rule | Lines 24-33 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.DaysSinceLastOverdue = DATEDIFF(DAY, A.LastOverdueClearedDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate IS NOT NULL AND A.LastOverdueCleare... |
| INSERT | uncovered | Lines 34-41 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) SELECT A.AccountId, A.AssetClass, A.DaysSinceLastOverdue, 'N' FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays =... |
| UPDATE | covered_by_rule | Lines 42-55 | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = ( CASE WHEN S.DaysSinceLastOverdue IS NULL THEN 'N' WHEN S.AssetClass = 'SUBSTANDARD' AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays THEN 'Y' WHEN S.AssetClass IN ('DOUBTFUL', 'LOSS') AND S.Day... |
| STATEMENT | covered_by_rule | Lines 56-56 | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | IF DAY(@ProcessDate) = 1 |
| STATEMENT | covered_by_rule | Lines 1-1 | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | uncovered | Lines 58-61 | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = 'PENDING_APPROVAL' FROM #WatchlistStaging S WHERE S.EligibleForUpgrade = 'Y' |
| STATEMENT | covered_by_rule | Lines 49-49 | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 40-40 | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | ELSE |
| STATEMENT | covered_by_rule | Lines 1-1 | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | uncovered | Lines 65-66 | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = S.EligibleForUpgrade FROM #WatchlistStaging S |
| STATEMENT | uncovered | Lines 67-70 | 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block | END -- Rule 4: upsert every staged account into the watchlist table - -- refresh accounts already tracked, add accounts newly clear |
| MERGE | covered_by_rule | Lines 71-84 | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | MERGE PRO.NpaUpgradeWatchlist AS Target USING #WatchlistStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DaysSinceLastOverdue = Source.DaysSinceLastOverdue, Target.EligibleForUpgrade = Source.E... |
| DELETE | covered_by_rule | Lines 85-96 | 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block | DELETE FROM PRO.NpaUpgradeWatchlist WHERE AccountId IN ( SELECT AccountId FROM PRO.LoanAccountCal WHERE OverdueDays > 0 ) -- Rule 6: status transition - promote every eligible watchlist -- account back to Standard, unless the account has... |
| UPDATE | covered_by_rule | Lines 97-104 | 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = 'STANDARD', A.UpgradeDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId = A.AccountId AND W.AssetClass = A.AssetClass WHERE W.EligibleForUpgrade = 'Y' -- Rule 7:... |
| INSERT | covered_by_rule | Lines 105-111 | 03_batch3_main_body+batch3_nested_block:chunk_text_23, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT A.AccountId, @ProcessDate, 'STANDARD', 'NPA_WATCH_PERIOD_COMPLETE' FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId... |
| DELETE | covered_by_rule | Lines 113-114 | 03_batch3_main_body+batch3_nested_block:chunk_text_24, 03_batch3_main_body+batch3_nested_block | DELETE FROM PRO.NpaUpgradeWatchlist WHERE EligibleForUpgrade = 'Y' |
| UPDATE | uncovered | Lines 116-118 | 03_batch3_main_body+batch3_nested_block:chunk_text_25, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'NPA_Upgrade_Watchlist_Merge' |
| STATEMENT | uncovered | Lines 120-120 | 03_batch3_main_body+batch3_nested_block:chunk_text_26, 03_batch3_main_body+batch3_nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 24-33 | 03_batch3_main_body+batch3_nested_block:embedded_01_27, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.DaysSinceLastOverdue = DATEDIFF(DAY, A.LastOverdueClearedDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate IS NOT NULL AND A.LastOverdueCleare... |
| INSERT | uncovered | Lines 34-41 | 03_batch3_main_body+batch3_nested_block:embedded_02_28, 03_batch3_main_body+batch3_nested_block | INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) SELECT A.AccountId, A.AssetClass, A.DaysSinceLastOverdue, 'N' FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays =... |
| UPDATE | covered_by_rule | Lines 42-55 | 03_batch3_main_body+batch3_nested_block:embedded_03_29, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = ( CASE WHEN S.DaysSinceLastOverdue IS NULL THEN 'N' WHEN S.AssetClass = 'SUBSTANDARD' AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays THEN 'Y' WHEN S.AssetClass IN ('DOUBTFUL', 'LOSS') AND S.Day... |
| UPDATE | uncovered | Lines 58-61 | 03_batch3_main_body+batch3_nested_block:embedded_04_30, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = 'PENDING_APPROVAL' FROM #WatchlistStaging S WHERE S.EligibleForUpgrade = 'Y' |
| UPDATE | uncovered | Lines 65-66 | 03_batch3_main_body+batch3_nested_block:embedded_05_31, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = S.EligibleForUpgrade FROM #WatchlistStaging S |
| MERGE | covered_by_rule | Lines 71-84 | 03_batch3_main_body+batch3_nested_block:embedded_06_32, 03_batch3_main_body+batch3_nested_block | MERGE PRO.NpaUpgradeWatchlist AS Target USING #WatchlistStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DaysSinceLastOverdue = Source.DaysSinceLastOverdue, Target.EligibleForUpgrade = Source.E... |
| DELETE | covered_by_rule | Lines 85-96 | 03_batch3_main_body+batch3_nested_block:embedded_07_33, 03_batch3_main_body+batch3_nested_block | DELETE FROM PRO.NpaUpgradeWatchlist WHERE AccountId IN ( SELECT AccountId FROM PRO.LoanAccountCal WHERE OverdueDays > 0 ) -- Rule 6: status transition - promote every eligible watchlist -- account back to Standard, unless the account has... |
| UPDATE | covered_by_rule | Lines 97-104 | 03_batch3_main_body+batch3_nested_block:embedded_08_34, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = 'STANDARD', A.UpgradeDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId = A.AccountId AND W.AssetClass = A.AssetClass WHERE W.EligibleForUpgrade = 'Y' -- Rule 7:... |
| INSERT | covered_by_rule | Lines 105-111 | 03_batch3_main_body+batch3_nested_block:embedded_09_35, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT A.AccountId, @ProcessDate, 'STANDARD', 'NPA_WATCH_PERIOD_COMPLETE' FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId... |
| DELETE | covered_by_rule | Lines 113-114 | 03_batch3_main_body+batch3_nested_block:embedded_10_36, 03_batch3_main_body+batch3_nested_block | DELETE FROM PRO.NpaUpgradeWatchlist WHERE EligibleForUpgrade = 'Y' |
| UPDATE | uncovered | Lines 116-118 | 03_batch3_main_body+batch3_nested_block:embedded_11_37, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'NPA_Upgrade_Watchlist_Merge' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'NPA_Upgrade_Watchlist_Merge' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_05, 04_batch3_exception | END |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'NPA_Upgrade_Watchlist_Merge' |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:embedded_02_07, 04_batch3_exception | SET NOCOUNT OFF |
| READ | uncovered | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.DaysSinceLastOverdue = DATEDIFF(DAY, A.LastOverdueClearedDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate IS NOT NULL AND A.LastOverdueCleare... |
| INSERT_TEMP | technical_only | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) SELECT A.AccountId, A.AssetClass, A.DaysSinceLastOverdue, 'N' FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays =... |
| UPDATE_TEMP | technical_only | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = ( CASE WHEN S.DaysSinceLastOverdue IS NULL THEN 'N' WHEN S.AssetClass = 'SUBSTANDARD' AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays THEN 'Y' WHEN S.AssetClass IN ('DOUBTFUL', 'LOSS') AND S.Day... |
| UPDATE_TEMP | technical_only | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = 'PENDING_APPROVAL' FROM #WatchlistStaging S WHERE S.EligibleForUpgrade = 'Y' |
| UPDATE_TEMP | technical_only | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = S.EligibleForUpgrade FROM #WatchlistStaging S |
| MERGE | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | MERGE PRO.NpaUpgradeWatchlist AS Target USING #WatchlistStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DaysSinceLastOverdue = Source.DaysSinceLastOverdue, Target.EligibleForUpgrade = Source.E... |
| DELETE | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block | DELETE FROM PRO.NpaUpgradeWatchlist WHERE AccountId IN ( SELECT AccountId FROM PRO.LoanAccountCal WHERE OverdueDays > 0 ) -- Rule 6: status transition - promote every eligible watchlist -- account back to Standard, unless the account has... |
| UPDATE | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = 'STANDARD', A.UpgradeDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId = A.AccountId AND W.AssetClass = A.AssetClass WHERE W.EligibleForUpgrade = 'Y' -- Rule 7:... |
| READ | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = 'STANDARD', A.UpgradeDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId = A.AccountId AND W.AssetClass = A.AssetClass WHERE W.EligibleForUpgrade = 'Y' -- Rule 7:... |
| INSERT | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_23, 03_batch3_main_body+batch3_nested_block:chunk_text_23, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT A.AccountId, @ProcessDate, 'STANDARD', 'NPA_WATCH_PERIOD_COMPLETE' FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId... |
| DELETE | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_24, 03_batch3_main_body+batch3_nested_block:chunk_text_24, 03_batch3_main_body+batch3_nested_block | DELETE FROM PRO.NpaUpgradeWatchlist WHERE EligibleForUpgrade = 'Y' |
| UPDATE | uncovered | samples/15_NPA_Upgrade_Watchlist_Merge.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_25, 03_batch3_main_body+batch3_nested_block:chunk_text_25, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'NPA_Upgrade_Watchlist_Merge' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_27, 03_batch3_main_body+batch3_nested_block:embedded_01_27, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.DaysSinceLastOverdue = DATEDIFF(DAY, A.LastOverdueClearedDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate IS NOT NULL AND A.LastOverdueCleare... |
| READ | uncovered | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_28, 03_batch3_main_body+batch3_nested_block:embedded_02_28, 03_batch3_main_body+batch3_nested_block | INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) SELECT A.AccountId, A.AssetClass, A.DaysSinceLastOverdue, 'N' FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays =... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_28, 03_batch3_main_body+batch3_nested_block:embedded_02_28, 03_batch3_main_body+batch3_nested_block | INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) SELECT A.AccountId, A.AssetClass, A.DaysSinceLastOverdue, 'N' FROM PRO.LoanAccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays =... |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_29, 03_batch3_main_body+batch3_nested_block:embedded_03_29, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = ( CASE WHEN S.DaysSinceLastOverdue IS NULL THEN 'N' WHEN S.AssetClass = 'SUBSTANDARD' AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays THEN 'Y' WHEN S.AssetClass IN ('DOUBTFUL', 'LOSS') AND S.Day... |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_30, 03_batch3_main_body+batch3_nested_block:embedded_04_30, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = 'PENDING_APPROVAL' FROM #WatchlistStaging S WHERE S.EligibleForUpgrade = 'Y' |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_31, 03_batch3_main_body+batch3_nested_block:embedded_05_31, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EligibleForUpgrade = S.EligibleForUpgrade FROM #WatchlistStaging S |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_33, 03_batch3_main_body+batch3_nested_block:embedded_07_33, 03_batch3_main_body+batch3_nested_block | DELETE FROM PRO.NpaUpgradeWatchlist WHERE AccountId IN ( SELECT AccountId FROM PRO.LoanAccountCal WHERE OverdueDays > 0 ) -- Rule 6: status transition - promote every eligible watchlist -- account back to Standard, unless the account has... |
| DELETE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_33, 03_batch3_main_body+batch3_nested_block:embedded_07_33, 03_batch3_main_body+batch3_nested_block | DELETE FROM PRO.NpaUpgradeWatchlist WHERE AccountId IN ( SELECT AccountId FROM PRO.LoanAccountCal WHERE OverdueDays > 0 ) -- Rule 6: status transition - promote every eligible watchlist -- account back to Standard, unless the account has... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_34, 03_batch3_main_body+batch3_nested_block:embedded_08_34, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = 'STANDARD', A.UpgradeDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId = A.AccountId AND W.AssetClass = A.AssetClass WHERE W.EligibleForUpgrade = 'Y' -- Rule 7:... |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_09_35, 03_batch3_main_body+batch3_nested_block:embedded_09_35, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT A.AccountId, @ProcessDate, 'STANDARD', 'NPA_WATCH_PERIOD_COMPLETE' FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId... |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_09_35, 03_batch3_main_body+batch3_nested_block:embedded_09_35, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT A.AccountId, @ProcessDate, 'STANDARD', 'NPA_WATCH_PERIOD_COMPLETE' FROM PRO.LoanAccountCal A INNER JOIN PRO.NpaUpgradeWatchlist W ON W.AccountId... |
| DELETE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_10_36, 03_batch3_main_body+batch3_nested_block:embedded_10_36, 03_batch3_main_body+batch3_nested_block | DELETE FROM PRO.NpaUpgradeWatchlist WHERE EligibleForUpgrade = 'Y' |
| UPDATE | uncovered | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_11_37, 03_batch3_main_body+batch3_nested_block:embedded_11_37, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'NPA_Upgrade_Watchlist_Merge' |
| UPDATE | uncovered | samples/15_NPA_Upgrade_Watchlist_Merge.sql / Lines 138-145 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'NPA_Upgrade_Watchlist_Merge' |
| UPDATE | uncovered | unavailable | 04_batch3_exception:embedded_01_06, 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'NPA_Upgrade_Watchlist_Merge' |
| CASE | covered_by_rule | Lines 62-63 | 03_batch3_main_body+batch3_nested_block:chunk_text_14 | S.DaysSinceLastOverdue IS NULL |
| CASE | covered_by_rule | Lines 63-64 | 03_batch3_main_body+batch3_nested_block:chunk_text_14 | S.AssetClass = 'SUBSTANDARD' AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays |
| CASE | covered_by_rule | Lines 64-65 | 03_batch3_main_body+batch3_nested_block:chunk_text_18 | S.AssetClass IN ('DOUBTFUL', 'LOSS') AND S.DaysSinceLastOverdue >= @DoubtfulWatchPeriodDays |
| ELSE | covered_by_rule | Lines 65-66 | 03_batch3_main_body+batch3_nested_block:chunk_text_18 | ELSE |
| IF_BRANCH | covered_by_rule | Lines 74-79 | 03_batch3_main_body+batch3_nested_block:chunk_text_20 | DAY(@ProcessDate) = 1 |
| ELSE | covered_by_rule | Lines 81-84 | 03_batch3_main_body+batch3_nested_block:chunk_text_20 | ELSE |
| IF_BRANCH | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | full_source | S.DaysSinceLastOverdue IS NULL |
| IF_BRANCH | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | full_source | S.AssetClass = 'SUBSTANDARD' AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays |
| IF_BRANCH | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | full_source | S.AssetClass IN ('DOUBTFUL', 'LOSS') AND S.DaysSinceLastOverdue >= @DoubtfulWatchPeriodDays |
| ELSE | covered_by_rule | samples/15_NPA_Upgrade_Watchlist_Merge.sql | full_source | ELSE |
| IF | uncovered | Lines 27-27 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 61-61 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 62-62 | unavailable | WHEN S.DaysSinceLastOverdue IS NULL THEN |
| CASE_BRANCH | uncovered | Lines 63-63 | unavailable | WHEN S.AssetClass = AND S.DaysSinceLastOverdue >= @StandardWatchPeriodDays THEN |
| CASE_BRANCH | uncovered | Lines 64-64 | unavailable | WHEN S.AssetClass IN ( , ) AND S.DaysSinceLastOverdue >= @DoubtfulWatchPeriodDays THEN |
| ELSE | covered_by_rule | Lines 65-65 | unavailable | ELSE |
| IF | covered_by_rule | Lines 73-73 | unavailable | IF DAY(@ProcessDate) = 1 |
| ELSE | covered_by_rule | Lines 80-80 | unavailable | ELSE |
| CASE_BRANCH | covered_by_rule | Lines 91-91 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | covered_by_rule | Lines 96-96 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CATCH | uncovered | Lines 138-138 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 143-143 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_27 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_02_28 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_27 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_07_33 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_27 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_09_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_28 / #WatchlistStaging | 03_batch3_main_body+batch3_nested_block:embedded_03_29 / #WatchlistStaging | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_28 / #WatchlistStaging | 03_batch3_main_body+batch3_nested_block:embedded_04_30 / #WatchlistStaging | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_28 / #WatchlistStaging | 03_batch3_main_body+batch3_nested_block:embedded_05_31 / #WatchlistStaging | high |
| later_update_overrides_field | 03_batch3_main_body+batch3_nested_block:embedded_03_29 / #WatchlistStaging | 03_batch3_main_body+batch3_nested_block:embedded_05_31 / #WatchlistStaging | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_08_34 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_09_35 / PRO.LoanAccountCal | high |

Unresolved dependency candidates: 39. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 22
- **By rule type:** deterministic_decision_table = 1, explicit = 21
- **By validation status:** unverified = 15, verified = 7

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 15
- **Deterministic-only facts:** 23
- **LLM-only claims:** 9
- **Conflicts:** 15
- **Unresolved items:** 2
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_read (`recon_5ffb908a96fb`): full_source
- `CONFLICT` tables_read (`recon_5ffb908a96fb`): full_source
- `CONFLICT` tables_read (`recon_5ffb908a96fb`): full_source
- `CONFLICT` tables_read (`recon_5ffb908a96fb`): full_source
- `CONFLICT` tables_written (`recon_722a74990fc9`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 71.03945111492281/100
- **Statement coverage:** 30 / 49 (61.2%)
- **Rule grounding coverage:** 13 / 22 (59.1%)
- **Decision-chain coverage:** 6 / 6 branches (100.0%)
- **Conflicts:** 15
- **Contradictions:** 16
- **Review required items:** 42
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Operation Conflict on `source`: Synthesized table operation conflicts with deterministic SQL/AST evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.DaysSinceLastOverdue is updated
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Insert into '#WatchlistStaging' table
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Update 'EligibleForUpgrade' field in '#WatchlistStaging' table
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Update 'AssetClass' and 'UpgradeDate' fields in 'PRO.LoanAccountCal' table
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) SELECT AccountId, AssetClass, DaysSinceLastOverdue, 'N' FROM PRO.LoanAccountCal WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate IS NOT NULL AND A.LastOverdueClearedDate <= @ProcessDate
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE #WatchlistStaging SET S.EligibleForUpgrade = 'Y' WHERE S.EligibleForUpgrade = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.NpaUpgradeWatchlist USING #WatchlistStaging ON Target.AccountId = Source.AccountId
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: IF DAY(@ProcessDate) = 1 BEGIN UPDATE S SET S.EligibleForUpgrade = 'PENDING_APPROVAL' FROM #WatchlistStaging S END
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.NpaUpgradeWatchlist, INSERT INTO PRO.NpaUpgradeWatchlist
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) VALUES (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE S SET S.EligibleForUpgrade = 'Y' FROM #WatchlistStaging S WHERE S.EligibleForUpgrade = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) SELECT AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade FROM PRO.LoanAccountCal WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.LastOverdueClearedDate IS NOT NULL AND A.LastOverdueClearedDate <= @ProcessDate
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE #WatchlistStaging SET S.EligibleForUpgrade = 'N' WHERE S.EligibleForUpgrade = 'Y'
- Synthesized in 6 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
