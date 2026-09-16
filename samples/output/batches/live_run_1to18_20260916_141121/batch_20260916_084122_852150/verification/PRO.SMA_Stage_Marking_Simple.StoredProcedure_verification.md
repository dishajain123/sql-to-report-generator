# SMA Stage Marking Simple — Verification & Traceability

> Companion artifact to `PRO.SMA_Stage_Marking_Simple.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_f88fd9f08d12` |
| Raw technical object name (from source) | `SMA_Stage_Marking_Simple` |

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
| Source Hash | `3673da81736b9d16643f497b5db0f9bedb14d4d26e65256490c25d2d77d0c0c2` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T08:42:05.834813+00:00` |
| Object ID | `obj_f88fd9f08d12` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_ce95ff804cf9` |
| Total LLM Calls | `6` |
| Successful Calls | `6` |
| Failed Calls | `0` |
| Prompt Tokens | `53813` |
| Completion Tokens | `10059` |
| Total Tokens | `63872` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 5803 | available |
| synthesis | 3 | 3 | 0 | 17158 | available |
| synthesis_revision | 2 | 2 | 0 | 40911 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| ⚠️ 1 | Determine SMA stage [MATCHED] (`rule__1`) | `SmaStage` | Assign an SMA stage to accounts based on the number of overdue days. |
| ⚠️ 2 | Set SMA flag [MATCHED] (`rule__2`) | `FlagSma` | Set the SMA flag for accounts based on the presence of an SMA stage. |
| ⚠️ 3 | Determine SMA reason [CONFLICT] (`rule__3`) | `SmaReason` | Assign an SMA reason to accounts based on their facility type. |
| ⚠️ 4 | Calculate SMA stage date [MATCHED] (`rule__4`) | `SmaStageDate` | Calculate the SMA stage date for accounts based on the number of overdue days. |
| ⚠️ 5 | Reset SMA status for non-overdue accounts [CONFLICT] (`rule__5`) | `SmaStage, FlagSma, SmaReason` | Reset the SMA stage, flag, and reason for accounts with no overdue days. |
| ⚠️ 6 | Update process completion status [MATCHED] (`rule__6`) | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Update the process completion status in the RunStatus table. |
| ⚠️ 7 | Update run status on error [MATCHED] (`rule__1__7`) | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an exception occurs, the run status is updated to indicate the process is not completed, the error date is set, the error description is… |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Determine SMA stage (rule__1) | UPDATE A SET A.SmaStage = (CASE WHEN A.OverdueDays BETWEEN 1 AND 30 THEN 'SMA_0' WHEN A.OverdueDays BETWEEN 31 AND 60 THEN 'SMA_1' WHEN A.OverdueDays BETWEEN 61 AND 90 THEN 'SMA_2' ELSE NULL END) FROM PRO.AccountCal A WHERE A.OverdueDays > 0 | Not cited | Not cited | Not cited | Verified |
| 2 | Set SMA flag (rule__2) | UPDATE A SET A.FlagSma = (CASE WHEN A.SmaStage IS NOT NULL THEN 'Y' ELSE 'N' END) FROM PRO.AccountCal A | Not cited | Not cited | Not cited | Verified |
| 3 | Determine SMA reason (rule__3) | UPDATE A SET A.SmaReason = (CASE WHEN A.FacilityType IN ('CC', 'OD') THEN 'CASH CREDIT / OVERDRAFT OVERDUE' WHEN A.FacilityType IN ('TL', 'DL') THEN 'TERM LOAN OVERDUE' ELSE 'OTHER FACILITY OVERDUE' END) FROM PRO.AccountCal A WHERE A.FlagSma = 'Y' | Not cited | Not cited | Not cited | Needs Review |
| 4 | Calculate SMA stage date (rule__4) | UPDATE A SET A.SmaStageDate = DATEADD(DAY, -A.OverdueDays + 1, @ProcessDate) FROM PRO.AccountCal A WHERE A.FlagSma = 'Y' | Not cited | Not cited | Not cited | Verified |
| 5 | Reset SMA status for non-overdue accounts (rule__5) | UPDATE A SET A.SmaStage = NULL, A.FlagSma = 'N', A.SmaReason = NULL FROM PRO.AccountCal A WHERE A.OverdueDays = 0 | Not cited | Not cited | Not cited | Needs Review |
| 6 | Update process completion status (rule__6) | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' | Not cited | Not cited | Not cited | Verified |
| 7 | Update run status on error (rule__1__7) | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' | Not cited | BEGIN CATCH... END CATCH | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0027_0032_807:branch_001 | A.OverdueDays BETWEEN 1 AND 30 | source \| Lines 28-29 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0027_0032_807:branch_002 | A.OverdueDays BETWEEN 31 AND 60 | source \| Lines 29-30 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0027_0032_807:branch_003 | A.OverdueDays BETWEEN 61 AND 90 | source \| Lines 30-31 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0027_0032_807:branch_004 | ELSE | source \| Lines 31-32 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0040_0043_1270:branch_001 | A.SmaStage IS NOT NULL | source \| Lines 41-42 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_06 |
| case_0040_0043_1270:branch_002 | ELSE | source \| Lines 42-43 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_06 |
| case_0050_0054_1570:branch_001 | A.FacilityType IN ('CC', 'OD') | source \| Lines 51-52 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| case_0050_0054_1570:branch_002 | A.FacilityType IN ('TL', 'DL') | source \| Lines 52-53 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| case_0050_0054_1570:branch_003 | ELSE | source \| Lines 53-54 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| decision_chain_004:branch_001 | A.OverdueDays BETWEEN 1 AND 30 | source |
| decision_chain_004:branch_002 | A.OverdueDays BETWEEN 31 AND 60 | source |
| decision_chain_004:branch_003 | A.OverdueDays BETWEEN 61 AND 90 | source |
| decision_chain_004:branch_004 | ELSE | source |
| decision_chain_005:branch_001 | A.SmaStage IS NOT NULL | source |
| decision_chain_005:branch_002 | ELSE | source |
| decision_chain_006:branch_001 | A.FacilityType IN ('CC', 'OD') | source |
| decision_chain_006:branch_002 | A.FacilityType IN ('TL', 'DL') | source |
| decision_chain_006:branch_003 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 73
- **Disposition:** covered_by_rule=57, uncovered=16

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | uncovered | Lines 1-2 | 03_batch3_main_body+batch3_nested_block:chunk_text_01, 03_batch3_main_body+batch3_nested_block | BEGIN SET NOCOUNT ON |
| STATEMENT | uncovered | Lines 4-4 | 03_batch3_main_body+batch3_nested_block:chunk_text_02, 03_batch3_main_body+batch3_nested_block | BEGIN TRY |
| SELECT | uncovered | Lines 6-8 | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) -- Rule 1: classify the SMA stage by overdue days |
| UPDATE | covered_by_rule | Lines 9-21 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStage = ( CASE WHEN A.OverdueDays BETWEEN 1 AND 30 THEN 'SMA_0' WHEN A.OverdueDays BETWEEN 31 AND 60 THEN 'SMA_1' WHEN A.OverdueDays BETWEEN 61 AND 90 THEN 'SMA_2' ELSE NULL END ) FROM PRO.AccountCal A WHERE A.OverdueDa... |
| UPDATE | covered_by_rule | Lines 22-31 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.FlagSma = ( CASE WHEN A.SmaStage IS NOT NULL THEN 'Y' ELSE 'N' END ) FROM PRO.AccountCal A -- Rule 3: attribute the overdue reason by facility type, for SMA accounts |
| UPDATE | covered_by_rule | Lines 32-45 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaReason = ( CASE WHEN A.FacilityType IN ('CC', 'OD') THEN 'CASH CREDIT / OVERDRAFT OVERDUE' WHEN A.FacilityType IN ('TL', 'DL') THEN 'TERM LOAN OVERDUE' ELSE 'OTHER FACILITY OVERDUE' END ) FROM PRO.AccountCal A WHERE A.F... |
| UPDATE | covered_by_rule | Lines 46-51 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStageDate = DATEADD(DAY, -A.OverdueDays + 1, @ProcessDate) FROM PRO.AccountCal A WHERE A.FlagSma = 'Y' -- Rule 5: clear SMA status for accounts that are no longer overdue |
| UPDATE | covered_by_rule | Lines 52-57 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStage = NULL, A.FlagSma = 'N', A.SmaReason = NULL FROM PRO.AccountCal A WHERE A.OverdueDays = 0 |
| UPDATE | covered_by_rule | Lines 59-61 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' |
| STATEMENT | uncovered | Lines 63-63 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 9-21 | 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStage = ( CASE WHEN A.OverdueDays BETWEEN 1 AND 30 THEN 'SMA_0' WHEN A.OverdueDays BETWEEN 31 AND 60 THEN 'SMA_1' WHEN A.OverdueDays BETWEEN 61 AND 90 THEN 'SMA_2' ELSE NULL END ) FROM PRO.AccountCal A WHERE A.OverdueDa... |
| UPDATE | covered_by_rule | Lines 22-31 | 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.FlagSma = ( CASE WHEN A.SmaStage IS NOT NULL THEN 'Y' ELSE 'N' END ) FROM PRO.AccountCal A -- Rule 3: attribute the overdue reason by facility type, for SMA accounts |
| UPDATE | covered_by_rule | Lines 32-45 | 03_batch3_main_body+batch3_nested_block:embedded_03_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaReason = ( CASE WHEN A.FacilityType IN ('CC', 'OD') THEN 'CASH CREDIT / OVERDRAFT OVERDUE' WHEN A.FacilityType IN ('TL', 'DL') THEN 'TERM LOAN OVERDUE' ELSE 'OTHER FACILITY OVERDUE' END ) FROM PRO.AccountCal A WHERE A.F... |
| UPDATE | covered_by_rule | Lines 46-51 | 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStageDate = DATEADD(DAY, -A.OverdueDays + 1, @ProcessDate) FROM PRO.AccountCal A WHERE A.FlagSma = 'Y' -- Rule 5: clear SMA status for accounts that are no longer overdue |
| UPDATE | covered_by_rule | Lines 52-57 | 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStage = NULL, A.FlagSma = 'N', A.SmaReason = NULL FROM PRO.AccountCal A WHERE A.OverdueDays = 0 |
| UPDATE | covered_by_rule | Lines 59-61 | 03_batch3_main_body+batch3_nested_block:embedded_06_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | END |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' |
| READ | uncovered | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) -- Rule 1: classify the SMA stage by overdue days |
| UPDATE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStage = ( CASE WHEN A.OverdueDays BETWEEN 1 AND 30 THEN 'SMA_0' WHEN A.OverdueDays BETWEEN 31 AND 60 THEN 'SMA_1' WHEN A.OverdueDays BETWEEN 61 AND 90 THEN 'SMA_2' ELSE NULL END ) FROM PRO.AccountCal A WHERE A.OverdueDa... |
| UPDATE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.FlagSma = ( CASE WHEN A.SmaStage IS NOT NULL THEN 'Y' ELSE 'N' END ) FROM PRO.AccountCal A -- Rule 3: attribute the overdue reason by facility type, for SMA accounts |
| UPDATE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaReason = ( CASE WHEN A.FacilityType IN ('CC', 'OD') THEN 'CASH CREDIT / OVERDRAFT OVERDUE' WHEN A.FacilityType IN ('TL', 'DL') THEN 'TERM LOAN OVERDUE' ELSE 'OTHER FACILITY OVERDUE' END ) FROM PRO.AccountCal A WHERE A.F... |
| UPDATE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStageDate = DATEADD(DAY, -A.OverdueDays + 1, @ProcessDate) FROM PRO.AccountCal A WHERE A.FlagSma = 'Y' -- Rule 5: clear SMA status for accounts that are no longer overdue |
| UPDATE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStage = NULL, A.FlagSma = 'N', A.SmaReason = NULL FROM PRO.AccountCal A WHERE A.OverdueDays = 0 |
| UPDATE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStage = ( CASE WHEN A.OverdueDays BETWEEN 1 AND 30 THEN 'SMA_0' WHEN A.OverdueDays BETWEEN 31 AND 60 THEN 'SMA_1' WHEN A.OverdueDays BETWEEN 61 AND 90 THEN 'SMA_2' ELSE NULL END ) FROM PRO.AccountCal A WHERE A.OverdueDa... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.FlagSma = ( CASE WHEN A.SmaStage IS NOT NULL THEN 'Y' ELSE 'N' END ) FROM PRO.AccountCal A -- Rule 3: attribute the overdue reason by facility type, for SMA accounts |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_13, 03_batch3_main_body+batch3_nested_block:embedded_03_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaReason = ( CASE WHEN A.FacilityType IN ('CC', 'OD') THEN 'CASH CREDIT / OVERDRAFT OVERDUE' WHEN A.FacilityType IN ('TL', 'DL') THEN 'TERM LOAN OVERDUE' ELSE 'OTHER FACILITY OVERDUE' END ) FROM PRO.AccountCal A WHERE A.F... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStageDate = DATEADD(DAY, -A.OverdueDays + 1, @ProcessDate) FROM PRO.AccountCal A WHERE A.FlagSma = 'Y' -- Rule 5: clear SMA status for accounts that are no longer overdue |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SmaStage = NULL, A.FlagSma = 'N', A.SmaReason = NULL FROM PRO.AccountCal A WHERE A.OverdueDays = 0 |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_16, 03_batch3_main_body+batch3_nested_block:embedded_06_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' |
| UPDATE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql / Lines 80-86 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' |
| UPDATE | covered_by_rule | unavailable | 04_batch3_exception:embedded_01_05, 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'SMA_Stage_Marking_Simple' |
| CASE | covered_by_rule | Lines 28-29 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | A.OverdueDays BETWEEN 1 AND 30 |
| CASE | covered_by_rule | Lines 29-30 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | A.OverdueDays BETWEEN 31 AND 60 |
| CASE | covered_by_rule | Lines 30-31 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | A.OverdueDays BETWEEN 61 AND 90 |
| ELSE | covered_by_rule | Lines 31-32 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | ELSE |
| CASE | covered_by_rule | Lines 41-42 | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | A.SmaStage IS NOT NULL |
| ELSE | covered_by_rule | Lines 42-43 | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | ELSE |
| CASE | covered_by_rule | Lines 51-52 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | A.FacilityType IN ('CC', 'OD') |
| CASE | covered_by_rule | Lines 52-53 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | A.FacilityType IN ('TL', 'DL') |
| ELSE | covered_by_rule | Lines 53-54 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | ELSE |
| IF_BRANCH | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | full_source | A.OverdueDays BETWEEN 1 AND 30 |
| IF_BRANCH | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | full_source | A.OverdueDays BETWEEN 31 AND 60 |
| IF_BRANCH | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | full_source | A.OverdueDays BETWEEN 61 AND 90 |
| ELSE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | full_source | A.SmaStage IS NOT NULL |
| ELSE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | full_source | A.FacilityType IN ('CC', 'OD') |
| IF_BRANCH | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | full_source | A.FacilityType IN ('TL', 'DL') |
| ELSE | covered_by_rule | samples/02_SMA_Stage_Marking_Simple.sql | full_source | ELSE |
| CASE | covered_by_rule | Lines 27-27 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 28-28 | unavailable | WHEN A.OverdueDays BETWEEN 1 AND 30 THEN |
| CASE_BRANCH | covered_by_rule | Lines 29-29 | unavailable | WHEN A.OverdueDays BETWEEN 31 AND 60 THEN |
| CASE_BRANCH | covered_by_rule | Lines 30-30 | unavailable | WHEN A.OverdueDays BETWEEN 61 AND 90 THEN |
| ELSE | covered_by_rule | Lines 31-31 | unavailable | ELSE NULL |
| CASE | covered_by_rule | Lines 40-40 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 41-41 | unavailable | WHEN A.SmaStage IS NOT NULL THEN |
| ELSE | covered_by_rule | Lines 42-42 | unavailable | ELSE |
| CASE | covered_by_rule | Lines 50-50 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 51-51 | unavailable | WHEN A.FacilityType IN ( , ) THEN |
| CASE_BRANCH | uncovered | Lines 52-52 | unavailable | WHEN A.FacilityType IN ( , ) THEN |
| ELSE | covered_by_rule | Lines 53-53 | unavailable | ELSE |
| CATCH | uncovered | Lines 80-80 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 85-85 | unavailable | END CATCH |

## Confirmed Statement Dependencies


Unresolved dependency candidates: 44. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** explicit = 7
- **By validation status:** unverified = 2, verified = 5

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 13
- **Deterministic-only facts:** 14
- **LLM-only claims:** 0
- **Conflicts:** 7
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_9c011e847efb`): full_source
- `CONFLICT` tables_written (`recon_9c011e847efb`): full_source
- `CONFLICT` tables_written (`recon_9c011e847efb`): full_source
- `CONFLICT` tables_written (`recon_9c011e847efb`): full_source
- `CONFLICT` tables_written (`recon_9c011e847efb`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 87.65957446808511/100
- **Statement coverage:** 18 / 26 (69.2%)
- **Rule grounding coverage:** 7 / 7 (100.0%)
- **Decision-chain coverage:** 9 / 9 branches (100.0%)
- **Conflicts:** 7
- **Contradictions:** 4
- **Review required items:** 11
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `rule__3`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Outcome Conflict on `rule__5`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- One or more ambiguities showed signs of repetition-degeneration or mid-sentence truncation and were dropped rather than included in the report.
- Synthesized in 3 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
