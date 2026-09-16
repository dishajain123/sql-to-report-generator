# Account Closure Audit Trail — Verification & Traceability

> Companion artifact to `PRO.Account_Closure_Audit_Trail.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_acc34f0279ea` |
| Raw technical object name (from source) | `Account_Closure_Audit_Trail` |

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
| Source Hash | `dbd70daccf7e4c93750a154552f19e03fc03b6af1aa265203447e991ea5f2dd8` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:27:20.626443+00:00` |
| Object ID | `obj_acc34f0279ea` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_934c425145cf` |
| Total LLM Calls | `8` |
| Successful Calls | `8` |
| Failed Calls | `0` |
| Prompt Tokens | `57469` |
| Completion Tokens | `14615` |
| Total Tokens | `72084` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 7463 | available |
| synthesis | 7 | 7 | 0 | 64621 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Update account status to closed [CONFLICT] (`rule__1`) | `AccountStatus, ClosureDate` | If the account status is not already closed, update it to closed and set the closure date to the current date. |
| 🔴 2 | Update account status [CONFLICT] (`rule__1__3`) | `AccountStatus, ClosureDate` | Update the account status in the PRO.LoanAccountCal table based on the outstanding balance and dispute status. |
| 🔴 3 | Insert closure decisions [CONFLICT] (`rule__2__4`) | `AccountId, NewStatus, Reason` | Insert closure decisions into the #ClosureDecisions table. |
| 🔴 4 | Merge closure decisions [CONFLICT] (`rule__3`) | `AccountId, Target.AccountId, Source.AccountId, Target.NewStatus, Source.NewStatus, Target.Reason, Source.Reason, Target.LastDecisionDate, NewStatus, Reason, FirstDecisionDate, LastDecisionDate` | Merge closure decisions into the PRO.ClosureRegister table. |
| 🟢 5 | Insert escalation records [MATCHED] (`rule__4`) | `AccountId, EscalationDate, Reason` | Insert records into the PRO.CollectionsQueue table for escalation. |
| 🟢 6 | Insert audit log entries [MATCHED] (`rule__5`) | `AccountId, TransitionDate, NewStatus, Reason` | Insert audit log entries into the PRO.AccountStatusAuditLog table. |
| 🔴 7 | Update account status to active [CONFLICT] (`rule__1__8`) | `AccountStatus, ClosureRejectReason` | If an account is pending closure and has an outstanding balance greater than zero, update its status to 'ACTIVE' and set the closure reject… |
| 🔴 8 | Update account status to active with unresolved dispute [CONFLICT] (`rule__2__9`) | `AccountStatus, ClosureRejectReason` | If an account is pending closure, has no outstanding balance, and has an unresolved dispute, update its status to 'ACTIVE' and set the clos… |
| 🟢 9 | Insert closure decisions [MATCHED] (`rule__3__10`) | `AccountId, NewStatus, Reason` | Insert closure decisions into the #ClosureDecisions temporary table for accounts that are pending closure and have a closure reject reason… |
| 🟢 10 | Merge closure decisions into register [MATCHED] (`rule__4__11`) | `AccountId, NewStatus, Reason` | Merge closure decisions from the #ClosureDecisions temporary table into the PRO.ClosureRegister. |
| 🟢 11 | Insert unresolved dispute escalations [MATCHED] (`rule__5__12`) | `AccountId, EscalationDate, Reason` | Insert records into PRO.CollectionsQueue for accounts with unresolved disputes that are pending closure and have a closure reject reason ot… |
| 🟢 12 | Insert audit log entries [MATCHED] (`rule__6`) | `AccountId, TransitionDate, NewStatus, Reason` | Insert audit log entries into PRO.AccountStatusAuditLog for accounts that have transitioned status. |
| 🔴 13 | Update account status to closed [CONFLICT] (`rule__1__14`) | `AccountStatus, ClosureDate` | If an account is pending closure and has an outstanding balance greater than zero, update its status to closed and record the closure date. |
| 🔴 14 | Update account status for dispute [CONFLICT] (`rule__2__15`) | `AccountStatus, ClosureDate` | If an account is pending closure, has no outstanding balance, and has a dispute flag set with a dispute raised date after a specified grace… |
| 🔴 15 | Insert closure decisions [CONFLICT] (`rule__3__16`) | `AccountId, NewStatus, Reason` | Insert decisions into the #ClosureDecisions temporary table for accounts that are pending closure and meet certain conditions. |
| 🟢 16 | Merge closure decisions [MATCHED] (`rule__4__17`) | `AccountId, NewStatus, Reason, LastDecisionDate` | Merge closure decisions into the PRO.ClosureRegister. |
| 🔴 17 | Insert collections queue records [CONFLICT] (`rule__5__18`) | `AccountId, EscalationDate, Reason` | Insert records into PRO.CollectionsQueue for accounts that have been rejected for closure. |
| 🔴 18 | Update account status to 'DISPUTE_PENDING' [CONFLICT] (`rule__2__20`) | `AccountStatus` | If an account is pending closure, has no outstanding balance, and has a dispute flag set with a dispute raised date after the grace cutoff,… |
| 🟢 19 | Insert closure decisions [MATCHED] (`rule__3__21`) | `AccountId, NewStatus, Reason` | Insert closure decisions into the #ClosureDecisions temporary table for accounts pending closure with a closure reject reason or without an… |
| 🟢 20 | Insert collections queue records [MATCHED] (`rule__4__22`) | `AccountId, EscalationDate, Reason` | Insert records into the PRO.CollectionsQueue table for accounts with closure reasons other than 'CLOSED_ZERO_BALANCE'. |
| 🟢 21 | Insert account status audit log entries [MATCHED] (`rule__5__23`) | `AccountId, TransitionDate, NewStatus, Reason` | Insert audit log entries into the PRO.AccountStatusAuditLog table for accounts that transitioned status. |
| 🔴 22 | Reset closure reject reason [CONFLICT] (`rule__1__24`) | `ClosureRejectReason` | If an account is not active or its closure reject reason is null, reset the closure reject reason to null. |
| 🔴 23 | Update account status and closure date [CONFLICT] (`rule__2__25`) | `AccountStatus, ClosureDate` | Update the account status and closure date based on various conditions such as outstanding balance and dispute flag. |
| 🟠 24 | Determine AccountStatus [MATCHED] (`deterministic_decision_1056_2119_0_accountstatus`) | `AccountStatus` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| 🟠 25 | Determine ClosureDate [MATCHED] (`deterministic_case_0040_0046_1564_closuredate`) | `ClosureDate` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 26 | Determine Reason [MATCHED] (`deterministic_decision_3292_3811_2_reason`) | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Update account status to closed (rule__1) | A.AccountStatus!= 'CLOSED' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_18 | Not cited | Needs Review |
| 2 | Update account status (rule__1__3) | A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) > 0; A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaisedDate IS NULL OR A.DisputeRaisedDate > @DisputeGraceCutoff)… | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_18 | 03_batch3_main_body+batch3_nested_block:embedded_01_18 | Needs Review |
| 3 | Insert closure decisions (rule__2__4) | A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) > 0 | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | Needs Review |
| 4 | Merge closure decisions (rule__3) | Target.AccountId = Source.AccountId | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | Needs Review |
| 5 | Insert escalation records (rule__4) | Reason <> 'CLOSED_ZERO_BALANCE' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_06_23 | 03_batch3_main_body+batch3_nested_block:embedded_06_23 | Verified |
| 6 | Insert audit log entries (rule__5) | A.ClosureDate = @ProcessDate OR A.ClosureRejectReason IN ('OUTSTANDING_BALANCE', 'UNRESOLVED_DISPUTE') | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | Verified |
| 7 | Update account status to active (rule__1__8) | A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) > 0 | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_18 | 03_batch3_main_body+batch3_nested_block:embedded_01_18 | Needs Review |
| 8 | Update account status to active with unresolved dispute (rule__2__9) | A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaisedDate IS NULL OR A.DisputeRaisedDate > @DisputeGraceCutoff) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_02_19 | 03_batch3_main_body+batch3_nested_block:embedded_02_19 | Needs Review |
| 9 | Insert closure decisions (rule__3__10) | A.AccountStatus = 'PENDING_CLOSURE' AND A.ClosureRejectReason <> 'CLOSED_ZERO_BALANCE' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | Verified |
| 10 | Merge closure decisions into register (rule__4__11) | Not cited | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | Verified |
| 11 | Insert unresolved dispute escalations (rule__5__12) | A.AccountStatus = 'PENDING_CLOSURE' AND A.ClosureRejectReason <> 'CLOSED_ZERO_BALANCE' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_06_23 | 03_batch3_main_body+batch3_nested_block:embedded_06_23 | Verified |
| 12 | Insert audit log entries (rule__6) | A.ClosureDate = @ProcessDate OR A.ClosureRejectReason IN ('OUTSTANDING_BALANCE', 'UNRESOLVED_DISPUTE') | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_07_24 | 03_batch3_main_body+batch3_nested_block:embedded_07_24 | Verified |
| 13 | Update account status to closed (rule__1__14) | A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) > 0 | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_18 | 03_batch3_main_body+batch3_nested_block:embedded_01_18 | Needs Review |
| 14 | Update account status for dispute (rule__2__15) | A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaisedDate IS NULL OR A.DisputeRaisedDate > @DisputeGraceCutoff) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_02_19 | 03_batch3_main_body+batch3_nested_block:embedded_02_19 | Needs Review |
| 15 | Insert closure decisions (rule__3__16) | A.ClosureDate = @ProcessDate OR A.ClosureRejectReason IN ('OUTSTANDING_BALANCE', 'UNRESOLVED_DISPUTE') | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | Needs Review |
| 16 | Merge closure decisions (rule__4__17) | MERGE PRO.ClosureRegister AS Target | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | 03_batch3_main_body+batch3_nested_block:embedded_04_21 | Verified |
| 17 | Insert collections queue records (rule__5__18) | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'CLOSURE_REJECTED_' + Reason FROM #ClosureDecisions WHERE Reason <> 'CLOSED_ZERO_BALANCE' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_06_23 | 03_batch3_main_body+batch3_nested_block:embedded_06_23 | Needs Review |
| 18 | Update account status to 'DISPUTE_PENDING' (rule__2__20) | A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaisedDate IS NULL OR A.DisputeRaisedDate > @DisputeGraceCutoff) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_02_19 | 03_batch3_main_body+batch3_nested_block:embedded_02_19 | Needs Review |
| 19 | Insert closure decisions (rule__3__21) | A.AccountStatus = 'PENDING_CLOSURE' AND (A.ClosureRejectReason IS NOT NULL OR A.AccountStatus NOT IN ('ACTIVE')) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_03_20; 03_batch3_main_body+batch3_nested_block:embedded_04_21 | 03_batch3_main_body+batch3_nested_block:embedded_03_20; 03_batch3_main_body+batch3_nested_block:embedded_04_21 | Verified |
| 20 | Insert collections queue records (rule__4__22) | Reason <> 'CLOSED_ZERO_BALANCE' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_06_23 | 03_batch3_main_body+batch3_nested_block:embedded_06_23 | Verified |
| 21 | Insert account status audit log entries (rule__5__23) | Not cited | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_07_25 | 03_batch3_main_body+batch3_nested_block:embedded_07_25 | Verified |
| 22 | Reset closure reject reason (rule__1__24) | A.AccountStatus NOT IN ('ACTIVE') OR A.ClosureRejectReason IS NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_18 | dependency_0001 | Needs Review |
| 23 | Update account status and closure date (rule__2__25) | A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) > 0 | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_02_19 | dependency_0002 | Needs Review |
| 24 | Determine AccountStatus (deterministic_decision_1056_2119_0_accountstatus) | Not cited | source \| Lines 29-52 | Not cited | Not cited | Verified |
| 25 | Determine ClosureDate (deterministic_case_0040_0046_1564_closuredate) | Not cited | source \| Lines 40-46 | Not cited | Not cited | Verified |
| 26 | Determine Reason (deterministic_decision_3292_3811_2_reason) | Not cited | source \| Lines 83-93 | Not cited | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| decision_1056_2119_0:branch_001 | (COALESCE(A.OutstandingBalance, 0) = 0) AND (A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL) | source \| Lines 29-52 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| decision_1056_2119_0:branch_002 | (COALESCE(A.OutstandingBalance, 0) = 0) AND (NOT A.DisputeRaisedDate IS NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff) | source \| Lines 29-52 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| decision_1056_2119_0:branch_003 | COALESCE(A.OutstandingBalance, 0) = 0 | source \| Lines 29-52 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| decision_1056_2119_0:branch_004 | ELSE | source \| Lines 29-52 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| case_0040_0046_1564:branch_001 | ISNULL(A.OutstandingBalance, 0) = 0<br>                     AND (A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL<br>                          OR (A.DisputeRaisedDate IS NOT NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff)) | source \| Lines 41-45 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_06 |
| case_0040_0046_1564:branch_002 | ELSE | source \| Lines 45-46 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| decision_3292_3811_2:branch_001 | A.ClosureRejectReason IS NOT NULL | source \| Lines 83-93 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_12 |
| decision_3292_3811_2:branch_002 | ELSE | source \| Lines 83-93 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_12 |
| decision_chain_004:branch_001 | ISNULL(A.OutstandingBalance, 0) = 0 | source |
| decision_chain_004:branch_002 | ELSE | source |
| decision_chain_005:branch_001 | ISNULL(A.OutstandingBalance, 0) > 0 | source |
| decision_chain_005:branch_002 | ISNULL(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaisedDate IS NULL OR A.DisputeRaisedDate > @DisputeGraceCutoff) | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 88
- **Disposition:** covered_by_rule=66, technical_only=4, uncovered=18

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
| STATEMENT | covered_by_rule | Lines 7-10 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @DisputeGraceCutoff DATE = DATEADD(DAY, -30, @ProcessDate) -- Rule 1: nested IF/ELSE - accounts pending closure with a zero -- or null balance are checked for disputes before closing |
| UPDATE | covered_by_rule | Lines 11-33 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = CASE WHEN ISNULL(A.OutstandingBalance, 0) = 0 THEN CASE WHEN A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL THEN 'CLOSED' WHEN A.DisputeRaisedDate IS NOT NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff TH... |
| UPDATE | covered_by_rule | Lines 34-43 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'ACTIVE', A.ClosureRejectReason = 'OUTSTANDING_BALANCE' FROM PRO.LoanAccountCal A WHERE A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) > 0 -- Rule 3: accounts pending closure with a... |
| UPDATE | covered_by_rule | Lines 44-51 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'ACTIVE', A.ClosureRejectReason = 'UNRESOLVED_DISPUTE' FROM PRO.LoanAccountCal A WHERE A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaise... |
| STATEMENT | covered_by_rule | Lines 53-53 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | IF OBJECT_ID('tempdb..#ClosureDecisions') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 54-54 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | DROP TABLE #ClosureDecisions |
| INSERT | covered_by_rule | Lines 56-64 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | CREATE TABLE #ClosureDecisions ( AccountId VARCHAR(20), NewStatus VARCHAR(20), Reason VARCHAR(30) ) -- Rule 4: conditional INSERT - stage only accounts that actually -- transitioned status this run |
| INSERT | covered_by_rule | Lines 65-74 | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ClosureDecisions (AccountId, NewStatus, Reason) SELECT A.AccountId, A.AccountStatus, ISNULL(A.ClosureRejectReason, 'CLOSED_ZERO_BALANCE') FROM PRO.LoanAccountCal A WHERE A.ClosureDate = @ProcessDate OR A.ClosureRejectReason... |
| MERGE | covered_by_rule | Lines 75-88 | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | MERGE PRO.ClosureRegister AS Target USING #ClosureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.NewStatus = Source.NewStatus, Target.Reason = Source.Reason, Target.LastDecisionDate = @Proc... |
| INSERT | covered_by_rule | Lines 89-95 | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'CLOSURE_REJECTED_' + Reason FROM #ClosureDecisions WHERE Reason <> 'CLOSED_ZERO_BALANCE' -- Rule 7: every account that transitioned sta... |
| INSERT | covered_by_rule | Lines 96-101 | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, NewStatus, Reason FROM #ClosureDecisions -- Rule 8: clear the reject reason for accounts that are not -- currently in a... |
| UPDATE | covered_by_rule | Lines 102-106 | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ClosureRejectReason = NULL FROM PRO.LoanAccountCal A WHERE A.AccountStatus NOT IN ('ACTIVE') OR A.ClosureRejectReason IS NULL |
| UPDATE | covered_by_rule | Lines 108-110 | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Account_Closure_Audit_Trail' |
| STATEMENT | covered_by_rule | Lines 112-112 | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 11-33 | 03_batch3_main_body+batch3_nested_block:embedded_01_18, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = CASE WHEN ISNULL(A.OutstandingBalance, 0) = 0 THEN CASE WHEN A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL THEN 'CLOSED' WHEN A.DisputeRaisedDate IS NOT NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff TH... |
| UPDATE | covered_by_rule | Lines 34-43 | 03_batch3_main_body+batch3_nested_block:embedded_02_19, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'ACTIVE', A.ClosureRejectReason = 'OUTSTANDING_BALANCE' FROM PRO.LoanAccountCal A WHERE A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) > 0 -- Rule 3: accounts pending closure with a... |
| UPDATE | covered_by_rule | Lines 44-51 | 03_batch3_main_body+batch3_nested_block:embedded_03_20, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'ACTIVE', A.ClosureRejectReason = 'UNRESOLVED_DISPUTE' FROM PRO.LoanAccountCal A WHERE A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaise... |
| INSERT | covered_by_rule | Lines 65-74 | 03_batch3_main_body+batch3_nested_block:embedded_04_21, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ClosureDecisions (AccountId, NewStatus, Reason) SELECT A.AccountId, A.AccountStatus, ISNULL(A.ClosureRejectReason, 'CLOSED_ZERO_BALANCE') FROM PRO.LoanAccountCal A WHERE A.ClosureDate = @ProcessDate OR A.ClosureRejectReason... |
| MERGE | covered_by_rule | Lines 75-88 | 03_batch3_main_body+batch3_nested_block:embedded_05_22, 03_batch3_main_body+batch3_nested_block | MERGE PRO.ClosureRegister AS Target USING #ClosureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.NewStatus = Source.NewStatus, Target.Reason = Source.Reason, Target.LastDecisionDate = @Proc... |
| INSERT | covered_by_rule | Lines 89-95 | 03_batch3_main_body+batch3_nested_block:embedded_06_23, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'CLOSURE_REJECTED_' + Reason FROM #ClosureDecisions WHERE Reason <> 'CLOSED_ZERO_BALANCE' -- Rule 7: every account that transitioned sta... |
| INSERT | covered_by_rule | Lines 96-101 | 03_batch3_main_body+batch3_nested_block:embedded_07_24, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, NewStatus, Reason FROM #ClosureDecisions -- Rule 8: clear the reject reason for accounts that are not -- currently in a... |
| UPDATE | covered_by_rule | Lines 102-106 | 03_batch3_main_body+batch3_nested_block:embedded_08_25, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ClosureRejectReason = NULL FROM PRO.LoanAccountCal A WHERE A.AccountStatus NOT IN ('ACTIVE') OR A.ClosureRejectReason IS NULL |
| UPDATE | covered_by_rule | Lines 108-110 | 03_batch3_main_body+batch3_nested_block:embedded_09_26, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Account_Closure_Audit_Trail' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Account_Closure_Audit_Trail' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_05, 04_batch3_exception | END |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Account_Closure_Audit_Trail' |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:embedded_02_07, 04_batch3_exception | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = CASE WHEN ISNULL(A.OutstandingBalance, 0) = 0 THEN CASE WHEN A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL THEN 'CLOSED' WHEN A.DisputeRaisedDate IS NOT NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff TH... |
| UPDATE | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'ACTIVE', A.ClosureRejectReason = 'OUTSTANDING_BALANCE' FROM PRO.LoanAccountCal A WHERE A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) > 0 -- Rule 3: accounts pending closure with a... |
| UPDATE | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'ACTIVE', A.ClosureRejectReason = 'UNRESOLVED_DISPUTE' FROM PRO.LoanAccountCal A WHERE A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaise... |
| INSERT_TEMP | technical_only | samples/13_Account_Closure_Audit_Trail.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ClosureDecisions (AccountId, NewStatus, Reason) SELECT A.AccountId, A.AccountStatus, ISNULL(A.ClosureRejectReason, 'CLOSED_ZERO_BALANCE') FROM PRO.LoanAccountCal A WHERE A.ClosureDate = @ProcessDate OR A.ClosureRejectReason... |
| MERGE | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | MERGE PRO.ClosureRegister AS Target USING #ClosureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.NewStatus = Source.NewStatus, Target.Reason = Source.Reason, Target.LastDecisionDate = @Proc... |
| INSERT | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'CLOSURE_REJECTED_' + Reason FROM #ClosureDecisions WHERE Reason <> 'CLOSED_ZERO_BALANCE' -- Rule 7: every account that transitioned sta... |
| INSERT | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, NewStatus, Reason FROM #ClosureDecisions -- Rule 8: clear the reject reason for accounts that are not -- currently in a... |
| UPDATE | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ClosureRejectReason = NULL FROM PRO.LoanAccountCal A WHERE A.AccountStatus NOT IN ('ACTIVE') OR A.ClosureRejectReason IS NULL |
| UPDATE | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Account_Closure_Audit_Trail' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_18, 03_batch3_main_body+batch3_nested_block:embedded_01_18, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = CASE WHEN ISNULL(A.OutstandingBalance, 0) = 0 THEN CASE WHEN A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL THEN 'CLOSED' WHEN A.DisputeRaisedDate IS NOT NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff TH... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_19, 03_batch3_main_body+batch3_nested_block:embedded_02_19, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'ACTIVE', A.ClosureRejectReason = 'OUTSTANDING_BALANCE' FROM PRO.LoanAccountCal A WHERE A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) > 0 -- Rule 3: accounts pending closure with a... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_20, 03_batch3_main_body+batch3_nested_block:embedded_03_20, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'ACTIVE', A.ClosureRejectReason = 'UNRESOLVED_DISPUTE' FROM PRO.LoanAccountCal A WHERE A.AccountStatus = 'PENDING_CLOSURE' AND ISNULL(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaise... |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_21, 03_batch3_main_body+batch3_nested_block:embedded_04_21, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ClosureDecisions (AccountId, NewStatus, Reason) SELECT A.AccountId, A.AccountStatus, ISNULL(A.ClosureRejectReason, 'CLOSED_ZERO_BALANCE') FROM PRO.LoanAccountCal A WHERE A.ClosureDate = @ProcessDate OR A.ClosureRejectReason... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_21, 03_batch3_main_body+batch3_nested_block:embedded_04_21, 03_batch3_main_body+batch3_nested_block | INSERT INTO #ClosureDecisions (AccountId, NewStatus, Reason) SELECT A.AccountId, A.AccountStatus, ISNULL(A.ClosureRejectReason, 'CLOSED_ZERO_BALANCE') FROM PRO.LoanAccountCal A WHERE A.ClosureDate = @ProcessDate OR A.ClosureRejectReason... |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_23, 03_batch3_main_body+batch3_nested_block:embedded_06_23, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'CLOSURE_REJECTED_' + Reason FROM #ClosureDecisions WHERE Reason <> 'CLOSED_ZERO_BALANCE' -- Rule 7: every account that transitioned sta... |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_23, 03_batch3_main_body+batch3_nested_block:embedded_06_23, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'CLOSURE_REJECTED_' + Reason FROM #ClosureDecisions WHERE Reason <> 'CLOSED_ZERO_BALANCE' -- Rule 7: every account that transitioned sta... |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_24, 03_batch3_main_body+batch3_nested_block:embedded_07_24, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, NewStatus, Reason FROM #ClosureDecisions -- Rule 8: clear the reject reason for accounts that are not -- currently in a... |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_24, 03_batch3_main_body+batch3_nested_block:embedded_07_24, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, NewStatus, Reason FROM #ClosureDecisions -- Rule 8: clear the reject reason for accounts that are not -- currently in a... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_25, 03_batch3_main_body+batch3_nested_block:embedded_08_25, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ClosureRejectReason = NULL FROM PRO.LoanAccountCal A WHERE A.AccountStatus NOT IN ('ACTIVE') OR A.ClosureRejectReason IS NULL |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_09_26, 03_batch3_main_body+batch3_nested_block:embedded_09_26, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Account_Closure_Audit_Trail' |
| UPDATE | uncovered | samples/13_Account_Closure_Audit_Trail.sql / Lines 131-138 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Account_Closure_Audit_Trail' |
| UPDATE | uncovered | unavailable | 04_batch3_exception:embedded_01_06, 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Account_Closure_Audit_Trail' |
| IF_BRANCH | covered_by_rule | Lines 29-52 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | (COALESCE(A.OutstandingBalance, 0) = 0) AND (A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL) |
| IF_BRANCH | covered_by_rule | Lines 29-52 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | (COALESCE(A.OutstandingBalance, 0) = 0) AND (NOT A.DisputeRaisedDate IS NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff) |
| IF_BRANCH | covered_by_rule | Lines 29-52 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | COALESCE(A.OutstandingBalance, 0) = 0 |
| ELSE | covered_by_rule | Lines 29-52 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | ELSE |
| CASE | covered_by_rule | Lines 41-45 | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | ISNULL(A.OutstandingBalance, 0) = 0 AND (A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL OR (A.DisputeRaisedDate IS NOT NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff)) |
| ELSE | covered_by_rule | Lines 45-46 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | ELSE |
| IF_BRANCH | covered_by_rule | Lines 83-93 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | A.ClosureRejectReason IS NOT NULL |
| ELSE | covered_by_rule | Lines 83-93 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | ELSE |
| IF_BRANCH | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | full_source | ISNULL(A.OutstandingBalance, 0) = 0 |
| ELSE | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | full_source | ISNULL(A.OutstandingBalance, 0) > 0 |
| IF_BRANCH | covered_by_rule | samples/13_Account_Closure_Audit_Trail.sql | full_source | ISNULL(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND (A.DisputeRaisedDate IS NULL OR A.DisputeRaisedDate > @DisputeGraceCutoff) |
| CASE | covered_by_rule | Lines 31-31 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 32-32 | unavailable | WHEN ISNULL(A.OutstandingBalance, 0) = 0 THEN |
| CASE | covered_by_rule | Lines 33-33 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 34-34 | unavailable | WHEN A.DisputeFlag = OR A.DisputeFlag IS NULL THEN |
| CASE_BRANCH | covered_by_rule | Lines 35-35 | unavailable | WHEN A.DisputeRaisedDate IS NOT NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff THEN |
| ELSE | covered_by_rule | Lines 36-36 | unavailable | ELSE |
| ELSE | covered_by_rule | Lines 38-38 | unavailable | ELSE |
| CASE | covered_by_rule | Lines 40-40 | unavailable | A.ClosureDate = CASE |
| CASE_BRANCH | covered_by_rule | Lines 41-41 | unavailable | WHEN ISNULL(A.OutstandingBalance, 0) = 0 |
| ELSE | covered_by_rule | Lines 45-45 | unavailable | ELSE A.ClosureDate |
| IF | uncovered | Lines 71-71 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE_BRANCH | uncovered | Lines 96-96 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | uncovered | Lines 101-101 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CATCH | uncovered | Lines 131-131 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 136-136 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_18 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_04_21 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_19 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_04_21 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_03_20 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_04_21 / PRO.LoanAccountCal | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_04_21 / #ClosureDecisions | 03_batch3_main_body+batch3_nested_block:embedded_06_23 / #ClosureDecisions | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_04_21 / #ClosureDecisions | 03_batch3_main_body+batch3_nested_block:embedded_07_24 / #ClosureDecisions | high |

Unresolved dependency candidates: 36. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 26
- **By rule type:** deterministic_decision_table = 3, explicit = 23
- **By validation status:** unverified = 13, verified = 13

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 25
- **Deterministic-only facts:** 2
- **LLM-only claims:** 1
- **Conflicts:** 17
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_aafcaa5f3169`): full_source
- `CONFLICT` tables_written (`recon_aafcaa5f3169`): full_source
- `CONFLICT` tables_written (`recon_aafcaa5f3169`): full_source
- `LLM_ONLY` tables_written (`recon_d0302c65b857`): full_source
- `CONFLICT` tables_written (`recon_aafcaa5f3169`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 80.79166666666669/100
- **Statement coverage:** 26 / 38 (68.4%)
- **Rule grounding coverage:** 23 / 26 (88.5%)
- **Decision-chain coverage:** 8 / 8 branches (100.0%)
- **Conflicts:** 17
- **Contradictions:** 25
- **Review required items:** 43
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `rule__1`: Synthesized condition conflicts with deterministic predicate evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.AccountStatus!= 'CLOSED'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL, A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND A.DisputeRaisedDate IS NOT NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff, A.AccountStatus = 'PENDING_CLOSURE' AND COALESCE(A.OutstandingBalance, 0) = 0 AND A.DisputeFlag = 'Y' AND A.DisputeRaisedDate IS NOT NULL AND A.DisputeRaisedDate > @DisputeGraceCutoff
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.AccountStatus = 'PENDING_CLOSURE' AND A.ClosureRejectReason <> 'CLOSED_ZERO_BALANCE'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: No source evidence was provided for the synthesized rule.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.AccountStatus = 'PENDING_CLOSURE' AND (A.ClosureRejectReason IS NOT NULL OR A.AccountStatus NOT IN ('ACTIVE'))
- Synthesized in 7 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
