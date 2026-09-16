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
| Prompt Version | `3fde9e2078dcda12` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `5c2b7fd3479eb707f46ebf8d377f0382b1a5853f8f7651c647112572c9170f0a` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:24:09.824658+00:00` |
| Object ID | `obj_25da39e4d440` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_9b4854574dc0` |
| Total LLM Calls | `8` |
| Successful Calls | `8` |
| Failed Calls | `0` |
| Prompt Tokens | `72198` |
| Completion Tokens | `17793` |
| Total Tokens | `89991` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 6533 | available |
| synthesis | 6 | 6 | 0 | 54745 | available |
| synthesis_revision | 1 | 1 | 0 | 28713 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟢 1 | Increment notification count [MATCHED] (`rule__1`) | `NotifyCount` | Increment the notification count for each overdue account. |
| 🔴 2 | Calculate late fee [CONFLICT] (`rule__2`) | `LateFee` | Calculate the late fee based on the notification count. |
| 🟢 3 | Insert fee schedule details [MATCHED] (`rule__3`) | `AccountId, LateFee, NotifyCount, EscalateFlag` | Insert the account ID, calculated late fee, notification count, and escalation flag into the #FeeSchedule temporary table. |
| 🔴 4 | Update escalation flag [CONFLICT] (`rule__4`) | `EscalateFlag` | Update the escalation flag in the #FeeSchedule temporary table based on the notification count. |
| 🟢 5 | Determine escalation status [MATCHED] (`rule__5`) | `EscalateFlag` | Read from the #FeeSchedule temporary table to determine the escalation status for repeated overdue notifications. |
| 🔴 6 | Reset notification count [CONFLICT] (`rule__1__6`) | `NotifyCount` | Reset the notification count to zero for accounts with overdue days and no last notification date. |
| 🔴 7 | Insert into fee schedule [CONFLICT] (`rule__2__7`) | `AccountId, LateFee, NotifyCount, EscalateFlag` | Insert overdue accounts into the fee schedule with calculated late fees and notification counts. |
| 🟢 8 | Update late fee amount [MATCHED] (`rule__3__8`) | `LateFeeAmount, NotifyCount, LastNotifyDate` | Update the late fee amount, notification count, and last notification date in the loan account calendar. |
| 🟢 9 | Update escalate flag [MATCHED] (`rule__4__9`) | `EscalateFlag` | Update the escalate flag in the fee schedule based on certain conditions. |
| 🟢 10 | Merge into notification register [MATCHED] (`rule__5__10`) | `AccountId, LateFee, NotifyCount, LastNotifyDate` | Merge the fee schedule into the notification register. |
| 🟢 11 | Read overdue accounts [MATCHED] (`rule__8`) | `AccountId, LateFee, NotifyCount, LastNotifyDate` | Read overdue accounts from the loan account calendar to determine late fees and notification counts. |
| 🔴 12 | Update overdue accounts [CONFLICT] (`rule__1__12`) | `NotifyCount, LateFeeAmount, LastNotifyDate` | Update the notification count and late fee amount for accounts with overdue days. |
| 🔴 13 | Insert late fees [CONFLICT] (`rule__2__13`) | `AccountId, LateFee, NotifyCount, EscalateFlag` | Insert late fees and notification counts into #FeeSchedule for accounts with overdue days. |
| 🔴 14 | Update escalation flag [CONFLICT] (`rule__3__14`) | `EscalateFlag` | Update the escalation flag in #FeeSchedule based on notification counts. |
| 🔴 15 | Update late fee amount [CONFLICT] (`rule__4__15`) | `LateFeeAmount, NotifyCount, LastNotifyDate` | Update the late fee amount and notification count in PRO.LoanAccountCal. |
| 🔴 16 | Update overdue accounts [CONFLICT] (`rule__1__16`) | `NotifyCount, LateFeeAmount, LastNotifyDate` | Update the NotifyCount, LateFeeAmount, and LastNotifyDate fields in the LoanAccountCal table for accounts with overdue days. |
| 🔴 17 | Insert late fee schedule [CONFLICT] (`rule__2__17`) | `NotifyCount, AccountId, LateFee, EscalateFlag` | Insert late fee and notification count data into the #FeeSchedule temporary table. |
| 🟢 18 | Update escalate flag [MATCHED] (`rule__3__18`) | `EscalateFlag` | Update the EscalateFlag field in the #FeeSchedule table. |
| 🔴 19 | Merge notification register [CONFLICT] (`rule__4__19`) | `AccountId, LateFee, NotifyCount, FirstNotifyDate, LastNotifyDate` | Merge data into the NotificationRegister table to update or insert late fee and notification count records. |
| 🔴 20 | Update NotifyCount [CONFLICT] (`rule__1__20`) | `NotifyCount` | Increment the notification count for each overdue account. |
| 🟢 21 | Calculate LateFeeAmount [MATCHED] (`rule__2__21`) | `LateFeeAmount` | Calculate the late fee amount for each overdue account. |
| 🔴 22 | Increment notification count [CONFLICT] (`rule__2__22`) | `NotifyCount` | Increment the notification count for accounts with overdue loans. |
| 🔴 23 | Insert late fee details [CONFLICT] (`rule__3__23`) | `AccountId, LateFee, NotifyCount, EscalateFlag` | Insert late fee details into the FeeSchedule table based on the notification count. |
| 🔴 24 | Update escalation flag [CONFLICT] (`rule__4__24`) | `EscalateFlag` | Update the escalation flag in the FeeSchedule table if certain conditions are met. |
| 🟠 25 | Determine LateFee [MATCHED] (`deterministic_decision_1928_2574_1_latefee`) | `LateFee` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Increment notification count (rule__1) | Account is overdue | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_17 | Not cited | Verified |
| 2 | Calculate late fee (rule__2) | CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_02_18 | Not cited | Needs Review |
| 3 | Insert fee schedule details (rule__3) | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_02_18 | Not cited | Verified |
| 4 | Update escalation flag (rule__4) | UPDATE #FeeSchedule SET EscalateFlag = 1 WHERE NotifyCount > 1 | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_03_19 | Not cited | Needs Review |
| 5 | Determine escalation status (rule__5) | SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 1 | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_06_22 | Not cited | Verified |
| 6 | Reset notification count (rule__1__6) | A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_17 | 03_batch3_main_body+batch3_nested_block:embedded_01_17 | Needs Review |
| 7 | Insert into fee schedule (rule__2__7) | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FROM PRO.LoanAccountCal… | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | Needs Review |
| 8 | Update late fee amount (rule__3__8) | A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_12; 03_batch3_main_body+batch3_nested_block:embedded_04_20 | 03_batch3_main_body+batch3_nested_block:chunk_text_12; 03_batch3_main_body+batch3_nested_block:embedded_04_20 | Verified |
| 9 | Update escalate flag (rule__4__9) | EscalateFlag = 'Y' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_03_19 | 03_batch3_main_body+batch3_nested_block:embedded_03_19 | Verified |
| 10 | Merge into notification register (rule__5__10) | MERGE INTO PRO.NotificationRegister (Target.AccountId, Source.AccountId, Target.LateFee, Source.LateFee, Target.NotifyCount, Source.NotifyCount, Target.LastNotifyDate, AccountId, LateFee, NotifyCount, FirstNotifyDate, LastNotifyDate) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_06_22 | 03_batch3_main_body+batch3_nested_block:embedded_06_22 | Verified |
| 11 | Read overdue accounts (rule__8) | SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FROM PRO.LoanAccountCal WHERE OverdueDays > 0 AND NOT (@ProcessDate <= @GraceWindowEnd AND Overdu… | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_15 | 03_batch3_main_body+batch3_nested_block:chunk_text_15 | Verified |
| 12 | Update overdue accounts (rule__1__12) | A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND NOT A.NotifyCount IS NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_17 | 03_batch3_main_body+batch3_nested_block:embedded_01_17 | Needs Review |
| 13 | Insert late fees (rule__2__13) | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FROM PRO.LoanAccountCal… | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | Needs Review |
| 14 | Update escalation flag (rule__3__14) | UPDATE S SET S.EscalateFlag = (CASE WHEN S.NotifyCount >= 3 THEN 'Y' WHEN S.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END) FROM #FeeSchedule S | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_03_19 | 03_batch3_main_body+batch3_nested_block:embedded_03_19 | Needs Review |
| 15 | Update late fee amount (rule__4__15) | A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_20 | 03_batch3_main_body+batch3_nested_block:embedded_04_20 | Needs Review |
| 16 | Update overdue accounts (rule__1__16) | A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND NOT A.NotifyCount IS NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_17 | 03_batch3_main_body+batch3_nested_block:embedded_01_17 | Needs Review |
| 17 | Insert late fee schedule (rule__2__17) | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FROM PRO.LoanAccountCal… | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | Needs Review |
| 18 | Update escalate flag (rule__3__18) | SELECT S.NotifyCount, S.LateFee, S.AccountId, A.AccountId, AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_06_22 | 03_batch3_main_body+batch3_nested_block:embedded_06_22 | Verified |
| 19 | Merge notification register (rule__4__19) | MERGE PRO.NotificationRegister AS Target USING #FeeSchedule AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.LateFee = Source.LateFee, Target.NotifyCount = Source.NotifyCount, Target.LastNotifyDate = @ProcessDate WHEN NOT M… | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_05_21 | 03_batch3_main_body+batch3_nested_block:embedded_05_21 | Needs Review |
| 20 | Update NotifyCount (rule__1__20) | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FROM PRO.LoanAccountCal… | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | Needs Review |
| 21 | Calculate LateFeeAmount (rule__2__21) | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | Verified |
| 22 | Increment notification count (rule__2__22) | CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 1 WHEN ISNULL(NotifyCount, 0) = 1 THEN 2 ELSE NotifyCount + 1 END | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_17 | dependency_0001 | Verified |
| 23 | Insert late fee details (rule__3__23) | CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_02_18 | dependency_0002 | Verified |
| 24 | Update escalation flag (rule__4__24) | CASE WHEN ISNULL(EscalateFlag, 0) = 0 THEN 1 ELSE EscalateFlag END | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_03_19 | dependency_0003 | Verified |
| 25 | Determine LateFee (deterministic_decision_1928_2574_1_latefee) | Not cited | source \| Lines 53-68 | Not cited | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| decision_1928_2574_1:branch_001 | COALESCE(NotifyCount, 0) = 0 | source \| Lines 53-68 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_10 |
| decision_1928_2574_1:branch_002 | COALESCE(NotifyCount, 0) = 1 | source \| Lines 53-68 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_10 |
| decision_1928_2574_1:branch_003 | ELSE | source \| Lines 53-68 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_10 |
| case_0070_0074_2630:branch_001 | S.NotifyCount >= 3 | source \| Lines 71-72 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_12 |
| case_0070_0074_2630:branch_002 | S.NotifyCount = 2 | source \| Lines 72-73 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_12 |
| case_0070_0074_2630:branch_003 | ELSE | source \| Lines 73-74 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_12 |
| decision_chain_003:branch_001 | ISNULL(NotifyCount, 0) = 0 | source |
| decision_chain_003:branch_002 | ISNULL(NotifyCount, 0) = 1 | source |
| decision_chain_003:branch_003 | ELSE | source |
| decision_chain_004:branch_001 | S.NotifyCount >= 3 | source |
| decision_chain_004:branch_002 | S.NotifyCount = 2 | source |
| decision_chain_004:branch_003 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 79
- **Disposition:** covered_by_rule=57, technical_only=6, uncovered=16

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
| STATEMENT | covered_by_rule | Lines 7-7 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @MonthStartDate DATE = DATEADD(DAY, -DAY(@ProcessDate) + 1, @ProcessDate) |
| STATEMENT | covered_by_rule | Lines 8-10 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | DECLARE @GraceWindowEnd DATE = DATEADD(DAY, 6, @MonthStartDate) |
| STATEMENT | covered_by_rule | Lines 12-12 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | IF OBJECT_ID('tempdb..#FeeSchedule') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 13-13 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | DROP TABLE #FeeSchedule |
| STATEMENT | covered_by_rule | Lines 15-25 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | CREATE TABLE #FeeSchedule ( AccountId VARCHAR(20), LateFee DECIMAL(18,2), NotifyCount INT, EscalateFlag VARCHAR(1) ) -- Rule 0: NULL check - accounts with no last-notify date on record -- are treated as never notified before, distinct fr... |
| UPDATE | covered_by_rule | Lines 26-38 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.NotifyCount = 0 FROM PRO.LoanAccountCal A WHERE A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL -- Rule 1: conditional INSERT - only accounts actually charged a -- fee this cycle are staged; ne... |
| INSERT | covered_by_rule | Lines 39-53 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| UPDATE | covered_by_rule | Lines 54-65 | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EscalateFlag = ( CASE WHEN S.NotifyCount >= 3 THEN 'Y' WHEN S.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END ) FROM #FeeSchedule S -- Rule 3: derived-assignment UPDATE, apply the staged fee and -- record that a notification i... |
| UPDATE | covered_by_rule | Lines 66-75 | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| MERGE | covered_by_rule | Lines 76-89 | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | MERGE PRO.NotificationRegister AS Target USING #FeeSchedule AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.LateFee = Source.LateFee, Target.NotifyCount = Source.NotifyCount, Target.LastNotifyDate = @... |
| INSERT | covered_by_rule | Lines 90-93 | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| UPDATE | covered_by_rule | Lines 95-97 | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| STATEMENT | covered_by_rule | Lines 99-99 | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 26-38 | 03_batch3_main_body+batch3_nested_block:embedded_01_17, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.NotifyCount = 0 FROM PRO.LoanAccountCal A WHERE A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL -- Rule 1: conditional INSERT - only accounts actually charged a -- fee this cycle are staged; ne... |
| INSERT | covered_by_rule | Lines 39-53 | 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| UPDATE | covered_by_rule | Lines 54-65 | 03_batch3_main_body+batch3_nested_block:embedded_03_19, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EscalateFlag = ( CASE WHEN S.NotifyCount >= 3 THEN 'Y' WHEN S.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END ) FROM #FeeSchedule S -- Rule 3: derived-assignment UPDATE, apply the staged fee and -- record that a notification i... |
| UPDATE | covered_by_rule | Lines 66-75 | 03_batch3_main_body+batch3_nested_block:embedded_04_20, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| MERGE | covered_by_rule | Lines 76-89 | 03_batch3_main_body+batch3_nested_block:embedded_05_21, 03_batch3_main_body+batch3_nested_block | MERGE PRO.NotificationRegister AS Target USING #FeeSchedule AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.LateFee = Source.LateFee, Target.NotifyCount = Source.NotifyCount, Target.LastNotifyDate = @... |
| INSERT | covered_by_rule | Lines 90-93 | 03_batch3_main_body+batch3_nested_block:embedded_06_22, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| UPDATE | covered_by_rule | Lines 95-97 | 03_batch3_main_body+batch3_nested_block:embedded_07_23, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_05, 04_batch3_exception | END |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:embedded_02_07, 04_batch3_exception | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.NotifyCount = 0 FROM PRO.LoanAccountCal A WHERE A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL -- Rule 1: conditional INSERT - only accounts actually charged a -- fee this cycle are staged; ne... |
| INSERT_TEMP | technical_only | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| UPDATE_TEMP | technical_only | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EscalateFlag = ( CASE WHEN S.NotifyCount >= 3 THEN 'Y' WHEN S.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END ) FROM #FeeSchedule S -- Rule 3: derived-assignment UPDATE, apply the staged fee and -- record that a notification i... |
| UPDATE | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| READ_TEMP | technical_only | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| MERGE | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | MERGE PRO.NotificationRegister AS Target USING #FeeSchedule AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.LateFee = Source.LateFee, Target.NotifyCount = Source.NotifyCount, Target.LastNotifyDate = @... |
| INSERT | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| UPDATE | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_17, 03_batch3_main_body+batch3_nested_block:embedded_01_17, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.NotifyCount = 0 FROM PRO.LoanAccountCal A WHERE A.OverdueDays > 0 AND A.LastNotifyDate IS NULL AND A.NotifyCount IS NOT NULL -- Rule 1: conditional INSERT - only accounts actually charged a -- fee this cycle are staged; ne... |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block:embedded_02_18, 03_batch3_main_body+batch3_nested_block | INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag) SELECT AccountId, CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END, ISNULL(NotifyCount, 0) + 1, NULL FR... |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_19, 03_batch3_main_body+batch3_nested_block:embedded_03_19, 03_batch3_main_body+batch3_nested_block | UPDATE S SET S.EscalateFlag = ( CASE WHEN S.NotifyCount >= 3 THEN 'Y' WHEN S.NotifyCount = 2 THEN 'PENDING' ELSE 'N' END ) FROM #FeeSchedule S -- Rule 3: derived-assignment UPDATE, apply the staged fee and -- record that a notification i... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_20, 03_batch3_main_body+batch3_nested_block:embedded_04_20, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.LateFeeAmount = ISNULL(A.LateFeeAmount, 0) + S.LateFee, A.NotifyCount = S.NotifyCount, A.LastNotifyDate = @ProcessDate FROM PRO.LoanAccountCal A INNER JOIN #FeeSchedule S ON S.AccountId = A.AccountId -- Rule 4: upsert the... |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_22, 03_batch3_main_body+batch3_nested_block:embedded_06_22, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_22, 03_batch3_main_body+batch3_nested_block:embedded_06_22, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_23, 03_batch3_main_body+batch3_nested_block:embedded_07_23, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| UPDATE | uncovered | samples/10_Overdue_Account_Late_Fee_Assessment.sql / Lines 114-121 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| UPDATE | uncovered | unavailable | 04_batch3_exception:embedded_01_06, 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Overdue_Account_Late_Fee_Assessment' |
| IF_BRANCH | covered_by_rule | Lines 53-68 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | COALESCE(NotifyCount, 0) = 0 |
| IF_BRANCH | covered_by_rule | Lines 53-68 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | COALESCE(NotifyCount, 0) = 1 |
| ELSE | covered_by_rule | Lines 53-68 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | ELSE |
| CASE | covered_by_rule | Lines 71-72 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | S.NotifyCount >= 3 |
| CASE | covered_by_rule | Lines 72-73 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | S.NotifyCount = 2 |
| ELSE | covered_by_rule | Lines 73-74 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | ELSE |
| IF_BRANCH | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | full_source | ISNULL(NotifyCount, 0) = 0 |
| IF_BRANCH | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | full_source | ISNULL(NotifyCount, 0) = 1 |
| ELSE | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | full_source | S.NotifyCount >= 3 |
| IF_BRANCH | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | full_source | S.NotifyCount = 2 |
| ELSE | covered_by_rule | samples/10_Overdue_Account_Late_Fee_Assessment.sql | full_source | ELSE |
| IF | uncovered | Lines 26-26 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 55-55 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 56-56 | unavailable | WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 |
| CASE_BRANCH | covered_by_rule | Lines 57-57 | unavailable | WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 |
| ELSE | covered_by_rule | Lines 58-58 | unavailable | ELSE 1000.00 |
| CASE | covered_by_rule | Lines 70-70 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 71-71 | unavailable | WHEN S.NotifyCount >= 3 THEN |
| CASE_BRANCH | covered_by_rule | Lines 72-72 | unavailable | WHEN S.NotifyCount = 2 THEN |
| ELSE | covered_by_rule | Lines 73-73 | unavailable | ELSE |
| CASE_BRANCH | covered_by_rule | Lines 93-93 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | covered_by_rule | Lines 98-98 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CATCH | uncovered | Lines 114-114 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 119-119 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_17 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_02_18 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_18 / #FeeSchedule | 03_batch3_main_body+batch3_nested_block:embedded_03_19 / #FeeSchedule | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_02_18 / #FeeSchedule | 03_batch3_main_body+batch3_nested_block:embedded_06_22 / #FeeSchedule | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_03_19 / #FeeSchedule | 03_batch3_main_body+batch3_nested_block:embedded_06_22 / #FeeSchedule | high |

Unresolved dependency candidates: 22. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 25
- **By rule type:** deterministic_decision_table = 1, explicit = 24
- **By validation status:** unverified = 12, verified = 13

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 21
- **Deterministic-only facts:** 2
- **LLM-only claims:** 3
- **Conflicts:** 18
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_c48a5e0d5e51`): full_source
- `LLM_ONLY` tables_written (`recon_5d384a26c74f`): full_source
- `CONFLICT` tables_written (`recon_c48a5e0d5e51`): full_source
- `LLM_ONLY` tables_written (`recon_5d384a26c74f`): full_source
- `CONFLICT` tables_written (`recon_c48a5e0d5e51`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 81.71428571428571/100
- **Statement coverage:** 22 / 35 (62.9%)
- **Rule grounding coverage:** 24 / 25 (96.0%)
- **Decision-chain coverage:** 6 / 6 branches (100.0%)
- **Conflicts:** 18
- **Contradictions:** 19
- **Review required items:** 40
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `HIGH` Operation Conflict on `source`: Synthesized table operation conflicts with deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Outcome Conflict on `rule__2`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Outcome Conflict on `rule__4`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Outcome Conflict on `rule__1__6`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Account is overdue
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00 WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO #FeeSchedule (AccountId, LateFee, NotifyCount, EscalateFlag)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE #FeeSchedule SET EscalateFlag = 1 WHERE NotifyCount > 1
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: SELECT AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 1
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.NotificationRegister (Target.AccountId, Source.AccountId, Target.LateFee, Source.LateFee, Target.NotifyCount, Source.NotifyCount, Target.LastNotifyDate, AccountId, LateFee, NotifyCount, FirstNotifyDate, LastNotifyDate)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: SELECT S.NotifyCount, S.LateFee, S.AccountId, A.AccountId, AccountId, @ProcessDate, 'REPEATED_OVERDUE_NOTIFICATION' FROM #FeeSchedule WHERE EscalateFlag = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: CASE WHEN ISNULL(NotifyCount, 0) = 0 THEN 1 WHEN ISNULL(NotifyCount, 0) = 1 THEN 2 ELSE NotifyCount + 1 END
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: CASE WHEN ISNULL(EscalateFlag, 0) = 0 THEN 1 ELSE EscalateFlag END
- Synthesized in 6 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
