# Overdue Account Late Fee Assessment — Verification & Traceability

> Companion artifact to `PRO.Overdue_Account_Late_Fee_Assessment.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_25da39e4d440` |
| Raw technical object name (from source) | `Overdue_Account_Late_Fee_Assessment` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `4f519f469b95300a` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `5c2b7fd3479eb707f46ebf8d377f0382b1a5853f8f7651c647112572c9170f0a` |
| Configuration Version | `db93bfb59420a471` |
| Run Timestamp | `2026-09-16T23:15:53.156203+00:00` |
| Object ID | `obj_25da39e4d440` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_3ccbed3ca533` |
| Total LLM Calls | `7` |
| Successful Calls | `7` |
| Failed Calls | `0` |
| Prompt Tokens | `56767` |
| Completion Tokens | `6144` |
| Total Tokens | `62911` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 6485 | available |
| synthesis | 4 | 4 | 0 | 27546 | available |
| synthesis_revision | 2 | 2 | 0 | 28880 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Set escalate flag [MATCHED] (`rule__1__3`) | `#FeeSchedule.EscalateFlag` | Determine the escalate flag based on the number of overdue notifications. |
| 🟢 2 | Escalate overdue accounts to collections [MATCHED] (`rule__3__9`) | `AccountId, EscalationDate, Reason` | Insert records into the PRO.CollectionsQueue table for accounts that need escalation due to repeated overdue notifications. |
| 🟠 3 | Insert into CollectionsQueue [MATCHED] (`deterministic_statement_02_batch3_main_body:chunk_text_02_accountid`) | `AccountId, EscalationDate, Reason` | Not specified |
| 🟠 4 | Determine LateFee [MATCHED] (`deterministic_decision_1928_2574_1_latefee`) | `LateFee` | Not specified |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Set escalate flag (rule__1__3) | CASE WHEN #FeeSchedule.NotifyCount >= 3 THEN 'Y' WHEN #FeeSchedule.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END | Not cited | 01_batch3_main_body:embedded_01_03 | Not cited | Needs Review |
| 2 | Escalate overdue accounts to collections (rule__3__9) | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' | Not cited | 02_batch3_main_body:embedded_02_04 | Not cited | Verified |
| 3 | Insert into CollectionsQueue (deterministic_statement_02_batch3_main_body:chunk_text_02_accountid) | Not cited | source | 02_batch3_main_body | Not cited | Verified |
| 4 | Determine LateFee (deterministic_decision_1928_2574_1_latefee) | Not cited | source \| Lines 53-68 | Not cited | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| decision_1928_2574_1:branch_001 | COALESCE(NotifyCount, 0) = 0 | source \| Lines 53-68 \| Statement 00_batch3_main_body:chunk_text_10 |
| decision_1928_2574_1:branch_002 | COALESCE(NotifyCount, 0) = 1 | source \| Lines 53-68 \| Statement 00_batch3_main_body:chunk_text_10 |
| decision_1928_2574_1:branch_003 | ELSE | source \| Lines 53-68 \| Statement 00_batch3_main_body:chunk_text_10 |
| case_0070_0074_2630:branch_001 | #FeeSchedule.NotifyCount >= 3 | source \| Lines 71-72 \| Statement 00_batch3_main_body:chunk_text_11 |
| case_0070_0074_2630:branch_002 | #FeeSchedule.NotifyCount = 2 | source \| Lines 72-73 \| Statement 00_batch3_main_body:chunk_text_11 |
| case_0070_0074_2630:branch_003 | ELSE | source \| Lines 73-74 \| Statement 00_batch3_main_body:chunk_text_11 |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 69
- **Disposition:** covered_by_rule=44, technical_only=6, uncovered=19

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | covered_by_rule | Lines 1-5 | 00_batch3_main_body:chunk_text_01, 00_batch3_main_body | USE [DEMO_MISDB] SET ANSI_NULLS ON SET QUOTED_IDENTIFIER ON |
| STATEMENT | covered_by_rule | Lines 7-8 | 00_batch3_main_body:chunk_text_02, 00_batch3_main_body | BEGIN SET NOCOUNT ON |
| STATEMENT | covered_by_rule | Lines 11-11 | 00_batch3_main_body:chunk_text_03, 00_batch3_main_body | BEGIN TRY |
| SELECT | covered_by_rule | Lines 15-15 | 00_batch3_main_body:chunk_text_04, 00_batch3_main_body | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| STATEMENT | covered_by_rule | Lines 18-18 | 00_batch3_main_body:chunk_text_05, 00_batch3_main_body | DECLARE @MonthStartDate DATE = DATEADD(DAY, -DAY(@ProcessDate) + 1, @ProcessDate) |
| STATEMENT | covered_by_rule | Lines 21-21 | 00_batch3_main_body:chunk_text_06, 00_batch3_main_body | DECLARE @GraceWindowEnd DATE = DATEADD(DAY, 6, @MonthStartDate) |
| STATEMENT | covered_by_rule | Lines 25-25 | 00_batch3_main_body:chunk_text_07, 00_batch3_main_body | IF OBJECT_ID('tempdb..#FeeSchedule') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 28-28 | 00_batch3_main_body:chunk_text_08, 00_batch3_main_body | DROP TABLE #FeeSchedule |
| STATEMENT | covered_by_rule | Lines 32-42 | 00_batch3_main_body:chunk_text_09, 00_batch3_main_body | CREATE TABLE #FeeSchedule ( AccountId VARCHAR(20), LateFee DECIMAL(18,2), NotifyCount INT, EscalateFlag VARCHAR(1) ) -- Rule 0: NULL check - accounts with no last-notify date on record -- are treated as never notified before, distinct fr... |
| UPDATE | covered_by_rule | Lines 45-57 | 00_batch3_main_body:chunk_text_10, 00_batch3_main_body | UPDATE A SET A.NotifyCount = 0 FROM PRO.LoanAccountCal A WHERE A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL -- Rule 1: conditional INSERT - only accounts actually charged a -- fee this cycle are staged; ne... |
| INSERT | covered_by_rule | Lines 60-74 | 00_batch3_main_body:chunk_text_11, 00_batch3_main_body | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| UPDATE | covered_by_rule | Lines 45-57 | 00_batch3_main_body:embedded_01_12, 00_batch3_main_body | UPDATE A SET A.NotifyCount = 0 FROM PRO.LoanAccountCal A WHERE A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL -- Rule 1: conditional INSERT - only accounts actually charged a -- fee this cycle are staged; ne... |
| INSERT | covered_by_rule | Lines 60-74 | 00_batch3_main_body:embedded_02_13, 00_batch3_main_body | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| UPDATE | covered_by_rule | Lines 1-12 | 01_batch3_main_body:chunk_text_01, 01_batch3_main_body | UPDATE S SET S.EscalateFlag = ( CASE WHEN S.NotifyCount >= 3 THEN 'Y' WHEN S.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END ) FROM #FeeSchedule S -- Rule 3: derived-assignment UPDATE, apply the staged fee and -- record that a notification i... |
| UPDATE | covered_by_rule | Lines 15-24 | 01_batch3_main_body:chunk_text_02, 01_batch3_main_body | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| UPDATE | covered_by_rule | Lines 1-12 | 01_batch3_main_body:embedded_01_03, 01_batch3_main_body | UPDATE S SET S.EscalateFlag = ( CASE WHEN S.NotifyCount >= 3 THEN 'Y' WHEN S.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END ) FROM #FeeSchedule S -- Rule 3: derived-assignment UPDATE, apply the staged fee and -- record that a notification i... |
| UPDATE | covered_by_rule | Lines 15-24 | 01_batch3_main_body:embedded_02_04, 01_batch3_main_body | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| MERGE | covered_by_rule | Lines 1-14 | 02_batch3_main_body:chunk_text_01, 02_batch3_main_body | MERGE PRO.NotificationRegister AS Target USING #FeeSchedule AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.LateFee = Source.LateFee, Target.NotifyCount = Source.NotifyCount, Target.LastNotifyDate = @... |
| INSERT | covered_by_rule | Lines 17-20 | 02_batch3_main_body:chunk_text_02, 02_batch3_main_body | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| MERGE | covered_by_rule | Lines 1-14 | 02_batch3_main_body:embedded_01_03, 02_batch3_main_body | MERGE PRO.NotificationRegister AS Target USING #FeeSchedule AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.LateFee = Source.LateFee, Target.NotifyCount = Source.NotifyCount, Target.LastNotifyDate = @... |
| INSERT | covered_by_rule | Lines 17-20 | 02_batch3_main_body:embedded_02_04, 02_batch3_main_body | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| UPDATE | uncovered | Lines 1-3 | 03_batch3_main_body:chunk_text_01, 03_batch3_main_body | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| STATEMENT | uncovered | Lines 7-7 | 03_batch3_main_body:chunk_text_02, 03_batch3_main_body | END TRY |
| UPDATE | uncovered | Lines 1-3 | 03_batch3_main_body:embedded_01_03, 03_batch3_main_body | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_05, 04_batch3_exception | END |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:embedded_02_07, 04_batch3_exception | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 00_batch3_main_body:chunk_text_04, 00_batch3_main_body:chunk_text_04, 00_batch3_main_body | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 00_batch3_main_body:chunk_text_10, 00_batch3_main_body:chunk_text_10, 00_batch3_main_body | UPDATE A SET A.NotifyCount = 0 FROM PRO.LoanAccountCal A WHERE A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL -- Rule 1: conditional INSERT - only accounts actually charged a -- fee this cycle are staged; ne... |
| INSERT_TEMP | technical_only | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 00_batch3_main_body:chunk_text_11, 00_batch3_main_body:chunk_text_11, 00_batch3_main_body | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| UPDATE | covered_by_rule | unavailable | 00_batch3_main_body:embedded_01_12, 00_batch3_main_body:embedded_01_12, 00_batch3_main_body | UPDATE A SET A.NotifyCount = 0 FROM PRO.LoanAccountCal A WHERE A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL -- Rule 1: conditional INSERT - only accounts actually charged a -- fee this cycle are staged; ne... |
| READ | covered_by_rule | unavailable | 00_batch3_main_body:embedded_02_13, 00_batch3_main_body:embedded_02_13, 00_batch3_main_body | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| INSERT_TEMP | technical_only | unavailable | 00_batch3_main_body:embedded_02_13, 00_batch3_main_body:embedded_02_13, 00_batch3_main_body | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| UPDATE_TEMP | technical_only | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 01_batch3_main_body:chunk_text_01, 01_batch3_main_body:chunk_text_01, 01_batch3_main_body | UPDATE S SET S.EscalateFlag = ( CASE WHEN S.NotifyCount >= 3 THEN 'Y' WHEN S.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END ) FROM #FeeSchedule S -- Rule 3: derived-assignment UPDATE, apply the staged fee and -- record that a notification i... |
| UPDATE | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 01_batch3_main_body:chunk_text_02, 01_batch3_main_body:chunk_text_02, 01_batch3_main_body | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| READ_TEMP | technical_only | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 01_batch3_main_body:chunk_text_02, 01_batch3_main_body:chunk_text_02, 01_batch3_main_body | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| UPDATE_TEMP | technical_only | unavailable | 01_batch3_main_body:embedded_01_03, 01_batch3_main_body:embedded_01_03, 01_batch3_main_body | UPDATE S SET S.EscalateFlag = ( CASE WHEN S.NotifyCount >= 3 THEN 'Y' WHEN S.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END ) FROM #FeeSchedule S -- Rule 3: derived-assignment UPDATE, apply the staged fee and -- record that a notification i... |
| UPDATE | covered_by_rule | unavailable | 01_batch3_main_body:embedded_02_04, 01_batch3_main_body:embedded_02_04, 01_batch3_main_body | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| MERGE | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 02_batch3_main_body:chunk_text_01, 02_batch3_main_body:chunk_text_01, 02_batch3_main_body | MERGE PRO.NotificationRegister AS Target USING #FeeSchedule AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.LateFee = Source.LateFee, Target.NotifyCount = Source.NotifyCount, Target.LastNotifyDate = @... |
| INSERT | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 02_batch3_main_body:chunk_text_02, 02_batch3_main_body:chunk_text_02, 02_batch3_main_body | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| READ_TEMP | technical_only | unavailable | 02_batch3_main_body:embedded_02_04, 02_batch3_main_body:embedded_02_04, 02_batch3_main_body | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| INSERT | covered_by_rule | unavailable | 02_batch3_main_body:embedded_02_04, 02_batch3_main_body:embedded_02_04, 02_batch3_main_body | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| UPDATE | uncovered | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 03_batch3_main_body:chunk_text_01, 03_batch3_main_body:chunk_text_01, 03_batch3_main_body | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| UPDATE | uncovered | unavailable | 03_batch3_main_body:embedded_01_03, 03_batch3_main_body:embedded_01_03, 03_batch3_main_body | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| UPDATE | uncovered | samples/10_Overdue_Account_Late_Fee_Assessment.sql / Lines 114-121 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| UPDATE | uncovered | unavailable | 04_batch3_exception:embedded_01_06, 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| IF_BRANCH | covered_by_rule | Lines 53-68 | 00_batch3_main_body:chunk_text_10 | COALESCE(NotifyCount, 0) = 0 |
| IF_BRANCH | covered_by_rule | Lines 53-68 | 00_batch3_main_body:chunk_text_10 | COALESCE(NotifyCount, 0) = 1 |
| ELSE | covered_by_rule | Lines 53-68 | 00_batch3_main_body:chunk_text_10 | ELSE |
| CASE | covered_by_rule | Lines 71-72 | 00_batch3_main_body:chunk_text_11 | #FeeSchedule.NotifyCount >= 3 |
| CASE | covered_by_rule | Lines 72-73 | 00_batch3_main_body:chunk_text_11 | #FeeSchedule.NotifyCount = 2 |
| ELSE | covered_by_rule | Lines 73-74 | 00_batch3_main_body:chunk_text_11 | ELSE |
| IF | uncovered | Lines 26-26 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 55-55 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 56-56 | unavailable | WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 |
| CASE_BRANCH | covered_by_rule | Lines 57-57 | unavailable | WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 |
| ELSE | covered_by_rule | Lines 58-58 | unavailable | ELSE 1000.00 |
| CASE | covered_by_rule | Lines 70-70 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 71-71 | unavailable | WHEN S.NotifyCount >= 3 THEN |
| CASE_BRANCH | uncovered | Lines 72-72 | unavailable | WHEN S.NotifyCount = 2 THEN |
| ELSE | covered_by_rule | Lines 73-73 | unavailable | ELSE |
| CASE_BRANCH | covered_by_rule | Lines 93-93 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | uncovered | Lines 98-98 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CATCH | uncovered | Lines 114-114 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 119-119 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| temp_write_to_read | 01_batch3_main_body:embedded_01_03 / #FeeSchedule | 02_batch3_main_body:embedded_02_04 / #FeeSchedule | high |
| table_write_to_later_use | 01_batch3_main_body:embedded_01_03 / #FeeSchedule | 00_batch3_main_body:embedded_02_13 / #FeeSchedule | high |
| table_write_to_later_use | 01_batch3_main_body:embedded_02_04 / PRO.LoanAccountCal | 00_batch3_main_body:embedded_02_13 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 00_batch3_main_body:embedded_01_12 / PRO.LoanAccountCal | 00_batch3_main_body:embedded_02_13 / PRO.LoanAccountCal | high |

Unresolved dependency candidates: 22. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 4
- **By rule type:** deterministic_decision_table = 2, explicit = 2
- **By validation status:** MATCHED = 1, verified = 3

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 14
- **Deterministic-only facts:** 4
- **LLM-only claims:** 2
- **Conflicts:** 10
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` tables_written (`recon_5d384a26c74f`): full_source
- `CONFLICT` tables_written (`recon_c48a5e0d5e51`): full_source
- `LLM_ONLY` tables_written (`recon_5d384a26c74f`): full_source
- `CONFLICT` tables_written (`recon_c48a5e0d5e51`): full_source
- `CONFLICT` tables_written (`recon_c48a5e0d5e51`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 86.22222222222221/100
- **Statement coverage:** 18 / 31 (58.1%)
- **Rule grounding coverage:** 8 / 10 (80.0%)
- **Decision-chain coverage:** 6 / 6 branches (100.0%)
- **Conflicts:** 10
- **Contradictions:** 9
- **Review required items:** 21
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Outcome Conflict on `rule__1`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Outcome Conflict on `rule__2`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `MEDIUM` Field Conflict on `rule__1__3`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.NotifyCount = S.NotifyCount
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.LastNotifyDate = @ProcessDate
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE PRO.NotificationRegister AS Target USING #FeeSchedule AS Source ON Target.AccountId = Source.AccountId WHEN NOT MATCHED BY TARGET THEN INSERT (AccountId, LateFee, NotifyCount, FirstNotifyDate, LastNotifyDate) VALUES (Source.AccountId, Source.LateFee, Source.NotifyCount, @ProcessDate, @ProcessDate)
- Synthesized in 4 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
