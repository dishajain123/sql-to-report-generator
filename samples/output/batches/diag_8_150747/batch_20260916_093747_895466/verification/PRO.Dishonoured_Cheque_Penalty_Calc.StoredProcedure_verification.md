# Dishonoured Cheque Penalty Calc — Verification & Traceability

> Companion artifact to `PRO.Dishonoured_Cheque_Penalty_Calc.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_4c8f8a44b029` |
| Raw technical object name (from source) | `Dishonoured_Cheque_Penalty_Calc` |

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
| Source Hash | `d449240b166222b5c18aaa2aaa825720e537d8fefd960737c15f5a7e2f4da7e2` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:38:19.926459+00:00` |
| Object ID | `obj_4c8f8a44b029` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_ec1d4529846d` |
| Total LLM Calls | `8` |
| Successful Calls | `8` |
| Failed Calls | `0` |
| Prompt Tokens | `82428` |
| Completion Tokens | `18609` |
| Total Tokens | `101037` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 7391 | available |
| synthesis | 6 | 6 | 0 | 63711 | available |
| synthesis_revision | 1 | 1 | 0 | 29935 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟢 1 | Update penalty amount [MATCHED] (`rule__1__12`) | `PenaltyAmount` | Set the penalty amount for dishonoured cheques with a dishonour date matching the process date and no existing penalty amount. |
| 🟢 2 | Mark penalty applied [MATCHED] (`rule__2__13`) | `PenaltyApplied` | Mark cheques for which penalties have not been applied as applied. |
| 🟢 3 | Calculate dishonour count [MATCHED] (`rule__3__14`) | `DishonourCount` | Calculate the count of dishonoured cheques for each account within the lookback window. |
| 🟢 4 | Update account balance [MATCHED] (`rule__4__15`) | `OutstandingBalance` | Update the outstanding balance of loan accounts with a dishonour date matching the process date and a non-null penalty amount. |
| 🟠 5 | Suspend cheque book [UNRESOLVED] (`rule__5__16`) | `Not specified` | Suspend cheque books for accounts with a dishonour count greater than or equal to 3 and no current suspension. |
| 🟢 6 | Hold cheque for review [MATCHED] (`rule__2__20`) | `HoldForReview` | Hold cheques for review if the dishonour date matches the process date and the dishonour reason is null. |
| 🟢 7 | Mark penalty as applied [MATCHED] (`rule__3__21`) | `PenaltyApplied` | Mark penalties as applied for dishonoured cheques with a dishonour date matching the process date and a non-null penalty amount. |
| 🟢 8 | Adjust outstanding balance [MATCHED] (`rule__4__22`) | `OutstandingBalance` | Adjust the outstanding balance for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null… |
| 🟢 9 | Suspend cheque book [MATCHED] (`rule__5__23`) | `ChequeBookSuspended` | Suspend the cheque book for loan accounts with dishonoured cheques having a dishonour date matching the process date and a non-null penalty… |
| 🟢 10 | Log account status transition [MATCHED] (`rule__6__24`) | `AccountId, TransitionDate, NewStatus, Reason` | Log the transition of account status to 'CHEQUE_BOOK_SUSPENDED' for accounts with sufficient dishonour counts and where the cheque book is… |
| 🟢 11 | Suspend cheque book [MATCHED] (`rule__5__29`) | `ChequeBookSuspended` | Suspend the cheque book for accounts with 3 or more dishonoured cheques and no current suspension, and log the suspension reason. |
| 🟢 12 | Update penalty amount [MATCHED] (`rule__1`) | `PenaltyAmount` | Calculate and update the penalty amount for each dishonoured cheque based on the provided time key. |
| 🟠 13 | Set hold for review [LLM_ONLY] (`rule__2`) | `HoldForReview` | Mark cheques that need review for penalty application. |
| 🔴 14 | Apply penalty [CONFLICT] (`rule__3`) | `PenaltyApplied` | Apply the calculated penalty to the cheques. |
| 🟠 15 | Insert into staging [LLM_ONLY] (`rule__4`) | `AccountId, PenaltyAmount, DishonourCount` | Insert records into a staging table for further processing. |
| 🟢 16 | Calculate penalty amount [MATCHED] (`rule__1__6`) | `PenaltyAmount` | Determine the penalty amount for a dishonoured cheque based on the dishonour date and repeat count. |
| 🟢 17 | Set cheques to hold for review [MATCHED] (`rule__2__7`) | `HoldForReview` | Mark cheques for review if certain conditions are met. |
| 🟢 18 | Update penalty applied flag [MATCHED] (`rule__3__8`) | `PenaltyApplied` | Update the penalty applied flag for cheques with a penalty amount. |
| 🔴 19 | Calculate dishonour count [CONFLICT] (`rule__4__9`) | `DishonourCount` | Calculate the dishonour count for each account within a lookback window. |
| 🟢 20 | Determine accounts for suspension [MATCHED] (`rule__5__10`) | `AccountId` | Determine accounts that need suspension based on the dishonour count and cheque book status. |
| 🟠 21 | Update account status audit log [LLM_ONLY] (`rule__6`) | `AccountId` | Update the account status audit log for suspended accounts. |
| 🟠 22 | Merge penalty data [LLM_ONLY] (`rule__6__17`) | `Not specified` | Merge penalty data into the cheque penalty ledger. |
| 🟠 23 | Log account status [LLM_ONLY] (`rule__7`) | `Not specified` | Log account status transitions. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Update penalty amount (rule__1__12) | D.DishonourDate = @ProcessDate AND D.PenaltyApplied = 'N' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_13 | 03_batch3_main_body+batch3_nested_block:embedded_01_13 | Verified |
| 2 | Mark penalty applied (rule__2__13) | D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS NOT NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_24 | 03_batch3_main_body+batch3_nested_block:embedded_04_24 | Verified |
| 3 | Calculate dishonour count (rule__3__14) | D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS NOT NULL | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | Verified |
| 4 | Update account balance (rule__4__15) | D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS NOT NULL | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | Verified |
| 5 | Suspend cheque book (rule__5__16) | P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_07_27 | 03_batch3_main_body+batch3_nested_block:embedded_07_27 | Needs Review |
| 6 | Hold cheque for review (rule__2__20) | D.DishonourDate = @ProcessDate AND D.DishonourReason IS NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_02_22 | 03_batch3_main_body+batch3_nested_block:embedded_02_22 | Verified |
| 7 | Mark penalty as applied (rule__3__21) | D.DishonourDate = @ProcessDate AND NOT D.PenaltyAmount IS NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_24 | 03_batch3_main_body+batch3_nested_block:embedded_04_24 | Verified |
| 8 | Adjust outstanding balance (rule__4__22) | D.DishonourDate = @ProcessDate AND NOT D.PenaltyAmount IS NULL | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | Verified |
| 9 | Suspend cheque book (rule__5__23) | D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS NOT NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_03_23 | 03_batch3_main_body+batch3_nested_block:embedded_03_23 | Verified |
| 10 | Log account status transition (rule__6__24) | AccountId IN (SELECT AccountId FROM #NewSuspensions) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_07_27 | 03_batch3_main_body+batch3_nested_block:embedded_07_27 | Verified |
| 11 | Suspend cheque book (rule__5__29) | P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL) | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_07_27 | Not cited | Verified |
| 12 | Update penalty amount (rule__1) | D.PenaltyAmount | Not cited | Not cited | Not cited | Verified |
| 13 | Set hold for review (rule__2) | D.HoldForReview | Not cited | Not cited | Not cited | Needs Review |
| 14 | Apply penalty (rule__3) | D.PenaltyApplied | Not cited | Not cited | Not cited | Needs Review |
| 15 | Insert into staging (rule__4) | INSERT INTO #PenaltyStaging | Not cited | Not cited | Not cited | Needs Review |
| 16 | Calculate penalty amount (rule__1__6) | UPDATE D SET D.PenaltyAmount = ( CASE WHEN D.DishonourReason IS NULL THEN NULL WHEN D.RepeatCount IS NULL OR D.RepeatCount = 0 THEN 350.00 WHEN D.RepeatCount = 1 THEN 750.00 ELSE 1500.00 END ) FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate… | Not cited | Not cited | Not cited | Verified |
| 17 | Set cheques to hold for review (rule__2__7) | UPDATE D SET D.HoldForReview = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND D.DishonourReason IS NULL | Not cited | Not cited | Not cited | Verified |
| 18 | Update penalty applied flag (rule__3__8) | UPDATE D SET D.PenaltyApplied = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND NOT D.PenaltyAmount IS NULL | Not cited | Not cited | Not cited | Verified |
| 19 | Calculate dishonour count (rule__4__9) | INSERT INTO #PenaltyStaging (AccountId, PenaltyAmount, DishonourCount) SELECT D.AccountId, D.PenaltyAmount, (SELECT COUNT(*) FROM PRO.DishonouredCheque D2 WHERE D2.AccountId = D.AccountId AND D2.DishonourDate >= @LookbackWindowStart) FROM PRO.DishonouredChequ… | Not cited | Not cited | Not cited | Needs Review |
| 20 | Determine accounts for suspension (rule__5__10) | INSERT INTO #NewSuspensions SELECT P.AccountId FROM #PenaltyStaging P INNER JOIN PRO.LoanAccountCal A ON P.AccountId = A.AccountId WHERE P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL) | Not cited | Not cited | Not cited | Verified |
| 21 | Update account status audit log (rule__6) | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, 'CHEQUE_BOOK_SUSPENDED', 'REPEAT_DISHONOUR_THRESHOLD' FROM #NewSuspensions | Not cited | Not cited | Not cited | Needs Review |
| 22 | Merge penalty data (rule__6__17) | MERGE PRO.ChequePenaltyLedger AS Target | Not cited | Not cited | Not cited | Needs Review |
| 23 | Log account status (rule__7) | INSERT INTO PRO.AccountStatusAuditLog | Not cited | Not cited | Not cited | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0031_0036_1087:branch_001 | D.DishonourReason IS NULL | source \| Lines 32-33 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_06 |
| case_0031_0036_1087:branch_002 | D.RepeatCount IS NULL OR D.RepeatCount = 0 | source \| Lines 33-34 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_06 |
| case_0031_0036_1087:branch_003 | D.RepeatCount = 1 | source \| Lines 34-35 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| case_0031_0036_1087:branch_004 | ELSE | source \| Lines 35-36 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| tsql_if_0132_0142:branch_001 | EXISTS (SELECT 1 FROM PRO.ACLRUNNINGPROCESSSTATUS WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc') | samples/17_Dishonoured_Cheque_Penalty_Calc.sql \| Lines 133-137 \| Chunk 04_batch3_exception |
| tsql_if_0132_0142:branch_002 | ELSE | samples/17_Dishonoured_Cheque_Penalty_Calc.sql \| Lines 139-142 \| Chunk 04_batch3_exception |
| decision_chain_003:branch_001 | D.DishonourReason IS NULL | source |
| decision_chain_003:branch_002 | D.RepeatCount IS NULL OR D.RepeatCount = 0 | source |
| decision_chain_003:branch_003 | D.RepeatCount = 1 | source |
| decision_chain_003:branch_004 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 106
- **Disposition:** covered_by_rule=69, technical_only=8, uncovered=29

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
| STATEMENT | covered_by_rule | Lines 7-10 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @LookbackWindowStart DATE = DATEADD(MONTH, -6, @ProcessDate) -- Rule 1: multi-branch CASE - penalty scales with how many times -- the account has already been dishonoured |
| UPDATE | covered_by_rule | Lines 11-25 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.PenaltyAmount = ( CASE WHEN D.DishonourReason IS NULL THEN NULL WHEN D.RepeatCount IS NULL OR D.RepeatCount = 0 THEN 350.00 WHEN D.RepeatCount = 1 THEN 750.00 ELSE 1500.00 END ) FROM PRO.DishonouredCheque D WHERE D.Dishono... |
| UPDATE | covered_by_rule | Lines 26-33 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.HoldForReview = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND D.DishonourReason IS NULL -- Rule 3: apply the computed penalty to the account balance and -- mark the cheque as processed |
| UPDATE | covered_by_rule | Lines 34-39 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.OutstandingBalance = ISNULL(A.OutstandingBalance, 0) + D.PenaltyAmount FROM PRO.LoanAccountCal A INNER JOIN PRO.DishonouredCheque D ON D.AccountId = A.AccountId WHERE D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS N... |
| UPDATE | covered_by_rule | Lines 41-45 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.PenaltyApplied = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 47-47 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | IF OBJECT_ID('tempdb..#PenaltyStaging') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 48-48 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | DROP TABLE #PenaltyStaging |
| INSERT | covered_by_rule | Lines 50-58 | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | CREATE TABLE #PenaltyStaging ( AccountId VARCHAR(20), PenaltyAmount DECIMAL(18,2), DishonourCount INT ) -- Rule 4: conditional INSERT - stage only accounts penalised -- today, together with their trailing dishonour count |
| INSERT | covered_by_rule | Lines 59-69 | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | INSERT INTO #PenaltyStaging (AccountId, PenaltyAmount, DishonourCount) SELECT D.AccountId, D.PenaltyAmount, (SELECT COUNT(*) FROM PRO.DishonouredCheque D2 WHERE D2.AccountId = D.AccountId AND D2.DishonourDate >= @LookbackWindowStart) FRO... |
| MERGE | covered_by_rule | Lines 70-84 | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | MERGE PRO.ChequePenaltyLedger AS Target USING #PenaltyStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.PenaltyAmount = Target.PenaltyAmount + Source.PenaltyAmount, Target.DishonourCount = Sourc... |
| STATEMENT | covered_by_rule | Lines 85-85 | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | IF OBJECT_ID('tempdb..#NewSuspensions') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 86-86 | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | DROP TABLE #NewSuspensions |
| SELECT | covered_by_rule | Lines 88-96 | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | SELECT P.AccountId INTO #NewSuspensions FROM #PenaltyStaging P INNER JOIN PRO.LoanAccountCal A ON A.AccountId = P.AccountId WHERE P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL) -- Rule 7: suspen... |
| UPDATE | covered_by_rule | Lines 97-99 | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.LoanAccountCal SET ChequeBookSuspended = 'Y' WHERE AccountId IN (SELECT AccountId FROM #NewSuspensions) |
| INSERT | covered_by_rule | Lines 101-103 | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, 'CHEQUE_BOOK_SUSPENDED', 'REPEAT_DISHONOUR_THRESHOLD' FROM #NewSuspensions |
| UPDATE | covered_by_rule | Lines 105-107 | 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc' |
| STATEMENT | covered_by_rule | Lines 109-109 | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 11-25 | 03_batch3_main_body+batch3_nested_block:embedded_01_21, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.PenaltyAmount = ( CASE WHEN D.DishonourReason IS NULL THEN NULL WHEN D.RepeatCount IS NULL OR D.RepeatCount = 0 THEN 350.00 WHEN D.RepeatCount = 1 THEN 750.00 ELSE 1500.00 END ) FROM PRO.DishonouredCheque D WHERE D.Dishono... |
| UPDATE | covered_by_rule | Lines 26-33 | 03_batch3_main_body+batch3_nested_block:embedded_02_22, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.HoldForReview = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND D.DishonourReason IS NULL -- Rule 3: apply the computed penalty to the account balance and -- mark the cheque as processed |
| UPDATE | covered_by_rule | Lines 34-39 | 03_batch3_main_body+batch3_nested_block:embedded_03_23, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.OutstandingBalance = ISNULL(A.OutstandingBalance, 0) + D.PenaltyAmount FROM PRO.LoanAccountCal A INNER JOIN PRO.DishonouredCheque D ON D.AccountId = A.AccountId WHERE D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS N... |
| UPDATE | covered_by_rule | Lines 41-45 | 03_batch3_main_body+batch3_nested_block:embedded_04_24, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.PenaltyApplied = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS NOT NULL |
| INSERT | covered_by_rule | Lines 59-69 | 03_batch3_main_body+batch3_nested_block:embedded_05_25, 03_batch3_main_body+batch3_nested_block | INSERT INTO #PenaltyStaging (AccountId, PenaltyAmount, DishonourCount) SELECT D.AccountId, D.PenaltyAmount, (SELECT COUNT(*) FROM PRO.DishonouredCheque D2 WHERE D2.AccountId = D.AccountId AND D2.DishonourDate >= @LookbackWindowStart) FRO... |
| MERGE | covered_by_rule | Lines 70-84 | 03_batch3_main_body+batch3_nested_block:embedded_06_26, 03_batch3_main_body+batch3_nested_block | MERGE PRO.ChequePenaltyLedger AS Target USING #PenaltyStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.PenaltyAmount = Target.PenaltyAmount + Source.PenaltyAmount, Target.DishonourCount = Sourc... |
| SELECT | covered_by_rule | Lines 88-96 | 03_batch3_main_body+batch3_nested_block:embedded_07_27, 03_batch3_main_body+batch3_nested_block | SELECT P.AccountId INTO #NewSuspensions FROM #PenaltyStaging P INNER JOIN PRO.LoanAccountCal A ON A.AccountId = P.AccountId WHERE P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL) -- Rule 7: suspen... |
| UPDATE | covered_by_rule | Lines 97-99 | 03_batch3_main_body+batch3_nested_block:embedded_08_28, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.LoanAccountCal SET ChequeBookSuspended = 'Y' WHERE AccountId IN (SELECT AccountId FROM #NewSuspensions) |
| INSERT | covered_by_rule | Lines 101-103 | 03_batch3_main_body+batch3_nested_block:embedded_09_29, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, 'CHEQUE_BOOK_SUSPENDED', 'REPEAT_DISHONOUR_THRESHOLD' FROM #NewSuspensions |
| UPDATE | covered_by_rule | Lines 105-107 | 03_batch3_main_body+batch3_nested_block:embedded_10_30, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc' |
| INSERT | uncovered | Lines 1-4 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to -- investigate, including a fallback insert if the status row -- itself is missing |
| SELECT | uncovered | Lines 5-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | IF EXISTS (SELECT 1 FROM PRO.ACLRUNNINGPROCESSSTATUS WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc') |
| STATEMENT | uncovered | Lines 1-1 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | BEGIN |
| UPDATE | uncovered | Lines 7-9 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc' |
| STATEMENT | covered_by_rule | Lines 10-10 | 04_batch3_exception:chunk_text_05, 04_batch3_exception | END |
| STATEMENT | covered_by_rule | Lines 11-11 | 04_batch3_exception:chunk_text_06, 04_batch3_exception | ELSE |
| STATEMENT | uncovered | Lines 1-1 | 04_batch3_exception:chunk_text_07, 04_batch3_exception | BEGIN |
| INSERT | uncovered | Lines 13-14 | 04_batch3_exception:chunk_text_08, 04_batch3_exception | INSERT INTO PRO.ACLRUNNINGPROCESSSTATUS (RUNNINGPROCESSNAME, COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT) VALUES ('Dishonoured_Cheque_Penalty_Calc', 'N', GETDATE(), ERROR_MESSAGE(), 1) |
| STATEMENT | covered_by_rule | Lines 10-10 | 04_batch3_exception:chunk_text_09, 04_batch3_exception | END |
| STATEMENT | uncovered | Lines 16-16 | 04_batch3_exception:chunk_text_10, 04_batch3_exception | END CATCH |
| SET | uncovered | Lines 17-17 | 04_batch3_exception:chunk_text_11, 04_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 10-10 | 04_batch3_exception:chunk_text_12, 04_batch3_exception | END |
| UPDATE | uncovered | Lines 7-9 | 04_batch3_exception:embedded_01_13, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc' |
| INSERT | uncovered | Lines 13-14 | 04_batch3_exception:embedded_02_14, 04_batch3_exception | INSERT INTO PRO.ACLRUNNINGPROCESSSTATUS (RUNNINGPROCESSNAME, COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT) VALUES ('Dishonoured_Cheque_Penalty_Calc', 'N', GETDATE(), ERROR_MESSAGE(), 1) |
| SET | uncovered | Lines 17-17 | 04_batch3_exception:embedded_03_15, 04_batch3_exception | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.PenaltyAmount = ( CASE WHEN D.DishonourReason IS NULL THEN NULL WHEN D.RepeatCount IS NULL OR D.RepeatCount = 0 THEN 350.00 WHEN D.RepeatCount = 1 THEN 750.00 ELSE 1500.00 END ) FROM PRO.DishonouredCheque D WHERE D.Dishono... |
| UPDATE | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.HoldForReview = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND D.DishonourReason IS NULL -- Rule 3: apply the computed penalty to the account balance and -- mark the cheque as processed |
| UPDATE | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.OutstandingBalance = ISNULL(A.OutstandingBalance, 0) + D.PenaltyAmount FROM PRO.LoanAccountCal A INNER JOIN PRO.DishonouredCheque D ON D.AccountId = A.AccountId WHERE D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS N... |
| READ | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.OutstandingBalance = ISNULL(A.OutstandingBalance, 0) + D.PenaltyAmount FROM PRO.LoanAccountCal A INNER JOIN PRO.DishonouredCheque D ON D.AccountId = A.AccountId WHERE D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS N... |
| UPDATE | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.PenaltyApplied = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS NOT NULL |
| INSERT_TEMP | technical_only | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | INSERT INTO #PenaltyStaging (AccountId, PenaltyAmount, DishonourCount) SELECT D.AccountId, D.PenaltyAmount, (SELECT COUNT(*) FROM PRO.DishonouredCheque D2 WHERE D2.AccountId = D.AccountId AND D2.DishonourDate >= @LookbackWindowStart) FRO... |
| MERGE | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | MERGE PRO.ChequePenaltyLedger AS Target USING #PenaltyStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.PenaltyAmount = Target.PenaltyAmount + Source.PenaltyAmount, Target.DishonourCount = Sourc... |
| READ_TEMP | technical_only | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | SELECT P.AccountId INTO #NewSuspensions FROM #PenaltyStaging P INNER JOIN PRO.LoanAccountCal A ON A.AccountId = P.AccountId WHERE P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL) -- Rule 7: suspen... |
| READ | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | SELECT P.AccountId INTO #NewSuspensions FROM #PenaltyStaging P INNER JOIN PRO.LoanAccountCal A ON A.AccountId = P.AccountId WHERE P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL) -- Rule 7: suspen... |
| INSERT_TEMP | technical_only | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | SELECT P.AccountId INTO #NewSuspensions FROM #PenaltyStaging P INNER JOIN PRO.LoanAccountCal A ON A.AccountId = P.AccountId WHERE P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL) -- Rule 7: suspen... |
| UPDATE | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.LoanAccountCal SET ChequeBookSuspended = 'Y' WHERE AccountId IN (SELECT AccountId FROM #NewSuspensions) |
| READ_TEMP | technical_only | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.LoanAccountCal SET ChequeBookSuspended = 'Y' WHERE AccountId IN (SELECT AccountId FROM #NewSuspensions) |
| INSERT | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, 'CHEQUE_BOOK_SUSPENDED', 'REPEAT_DISHONOUR_THRESHOLD' FROM #NewSuspensions |
| UPDATE | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_21, 03_batch3_main_body+batch3_nested_block:embedded_01_21, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.PenaltyAmount = ( CASE WHEN D.DishonourReason IS NULL THEN NULL WHEN D.RepeatCount IS NULL OR D.RepeatCount = 0 THEN 350.00 WHEN D.RepeatCount = 1 THEN 750.00 ELSE 1500.00 END ) FROM PRO.DishonouredCheque D WHERE D.Dishono... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_22, 03_batch3_main_body+batch3_nested_block:embedded_02_22, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.HoldForReview = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND D.DishonourReason IS NULL -- Rule 3: apply the computed penalty to the account balance and -- mark the cheque as processed |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_23, 03_batch3_main_body+batch3_nested_block:embedded_03_23, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.OutstandingBalance = ISNULL(A.OutstandingBalance, 0) + D.PenaltyAmount FROM PRO.LoanAccountCal A INNER JOIN PRO.DishonouredCheque D ON D.AccountId = A.AccountId WHERE D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS N... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_24, 03_batch3_main_body+batch3_nested_block:embedded_04_24, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.PenaltyApplied = 'Y' FROM PRO.DishonouredCheque D WHERE D.DishonourDate = @ProcessDate AND D.PenaltyAmount IS NOT NULL |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_25, 03_batch3_main_body+batch3_nested_block:embedded_05_25, 03_batch3_main_body+batch3_nested_block | INSERT INTO #PenaltyStaging (AccountId, PenaltyAmount, DishonourCount) SELECT D.AccountId, D.PenaltyAmount, (SELECT COUNT(*) FROM PRO.DishonouredCheque D2 WHERE D2.AccountId = D.AccountId AND D2.DishonourDate >= @LookbackWindowStart) FRO... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_25, 03_batch3_main_body+batch3_nested_block:embedded_05_25, 03_batch3_main_body+batch3_nested_block | INSERT INTO #PenaltyStaging (AccountId, PenaltyAmount, DishonourCount) SELECT D.AccountId, D.PenaltyAmount, (SELECT COUNT(*) FROM PRO.DishonouredCheque D2 WHERE D2.AccountId = D.AccountId AND D2.DishonourDate >= @LookbackWindowStart) FRO... |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_27, 03_batch3_main_body+batch3_nested_block:embedded_07_27, 03_batch3_main_body+batch3_nested_block | SELECT P.AccountId INTO #NewSuspensions FROM #PenaltyStaging P INNER JOIN PRO.LoanAccountCal A ON A.AccountId = P.AccountId WHERE P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL) -- Rule 7: suspen... |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_28, 03_batch3_main_body+batch3_nested_block:embedded_08_28, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.LoanAccountCal SET ChequeBookSuspended = 'Y' WHERE AccountId IN (SELECT AccountId FROM #NewSuspensions) |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_28, 03_batch3_main_body+batch3_nested_block:embedded_08_28, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.LoanAccountCal SET ChequeBookSuspended = 'Y' WHERE AccountId IN (SELECT AccountId FROM #NewSuspensions) |
| READ_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_09_29, 03_batch3_main_body+batch3_nested_block:embedded_09_29, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, 'CHEQUE_BOOK_SUSPENDED', 'REPEAT_DISHONOUR_THRESHOLD' FROM #NewSuspensions |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_09_29, 03_batch3_main_body+batch3_nested_block:embedded_09_29, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AccountStatusAuditLog (AccountId, TransitionDate, NewStatus, Reason) SELECT AccountId, @ProcessDate, 'CHEQUE_BOOK_SUSPENDED', 'REPEAT_DISHONOUR_THRESHOLD' FROM #NewSuspensions |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_10_30, 03_batch3_main_body+batch3_nested_block:embedded_10_30, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc' |
| READ | uncovered | unavailable | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | IF EXISTS (SELECT 1 FROM PRO.ACLRUNNINGPROCESSSTATUS WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc') |
| UPDATE | uncovered | samples/17_Dishonoured_Cheque_Penalty_Calc.sql / Lines 128-145 | 04_batch3_exception:chunk_text_04, 04_batch3_exception:chunk_text_04, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc' |
| INSERT | uncovered | samples/17_Dishonoured_Cheque_Penalty_Calc.sql / Lines 128-145 | 04_batch3_exception:chunk_text_08, 04_batch3_exception:chunk_text_08, 04_batch3_exception | INSERT INTO PRO.ACLRUNNINGPROCESSSTATUS (RUNNINGPROCESSNAME, COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT) VALUES ('Dishonoured_Cheque_Penalty_Calc', 'N', GETDATE(), ERROR_MESSAGE(), 1) |
| UPDATE | uncovered | unavailable | 04_batch3_exception:embedded_01_13, 04_batch3_exception:embedded_01_13, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc' |
| CASE | covered_by_rule | Lines 32-33 | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | D.DishonourReason IS NULL |
| CASE | covered_by_rule | Lines 33-34 | 03_batch3_main_body+batch3_nested_block:chunk_text_06 | D.RepeatCount IS NULL OR D.RepeatCount = 0 |
| CASE | covered_by_rule | Lines 34-35 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | D.RepeatCount = 1 |
| ELSE | covered_by_rule | Lines 35-36 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | ELSE |
| IF_BRANCH | uncovered | samples/17_Dishonoured_Cheque_Penalty_Calc.sql / Lines 133-137 | 04_batch3_exception | EXISTS (SELECT 1 FROM PRO.ACLRUNNINGPROCESSSTATUS WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc') |
| ELSE | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql / Lines 139-142 | 04_batch3_exception | ELSE |
| IF_BRANCH | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | full_source | D.DishonourReason IS NULL |
| IF_BRANCH | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | full_source | D.RepeatCount IS NULL OR D.RepeatCount = 0 |
| IF_BRANCH | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | full_source | D.RepeatCount = 1 |
| ELSE | covered_by_rule | samples/17_Dishonoured_Cheque_Penalty_Calc.sql | full_source | ELSE |
| CASE | covered_by_rule | Lines 31-31 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 32-32 | unavailable | WHEN D.DishonourReason IS NULL THEN NULL |
| CASE_BRANCH | covered_by_rule | Lines 33-33 | unavailable | WHEN D.RepeatCount IS NULL OR D.RepeatCount = 0 THEN 350.00 |
| CASE_BRANCH | covered_by_rule | Lines 34-34 | unavailable | WHEN D.RepeatCount = 1 THEN 750.00 |
| ELSE | covered_by_rule | Lines 35-35 | unavailable | ELSE 1500.00 |
| IF | uncovered | Lines 65-65 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CALCULATION | covered_by_rule | Lines 79-79 | unavailable | (SELECT COUNT(*) FROM PRO.DishonouredCheque D2 |
| CASE_BRANCH | uncovered | Lines 91-91 | unavailable | WHEN MATCHED THEN |
| CALCULATION | uncovered | Lines 93-93 | unavailable | Target.PenaltyAmount = Target.PenaltyAmount + Source.PenaltyAmount, |
| CASE_BRANCH | uncovered | Lines 96-96 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| IF | uncovered | Lines 103-103 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CATCH | uncovered | Lines 128-128 | unavailable | BEGIN CATCH |
| IF | uncovered | Lines 132-132 | unavailable | IF EXISTS (SELECT 1 FROM PRO.ACLRUNNINGPROCESSSTATUS WHERE RUNNINGPROCESSNAME = ) |
| ELSE | covered_by_rule | Lines 138-138 | unavailable | ELSE |
| CATCH | uncovered | Lines 143-143 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| table_write_to_later_use | 04_batch3_exception:embedded_01_13 / PRO.ACLRUNNINGPROCESSSTATUS | 04_batch3_exception:chunk_text_08 / PRO.ACLRUNNINGPROCESSSTATUS | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_21 / PRO.DishonouredCheque | 03_batch3_main_body+batch3_nested_block:embedded_05_25 / PRO.DishonouredCheque | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_22 / PRO.DishonouredCheque | 03_batch3_main_body+batch3_nested_block:embedded_05_25 / PRO.DishonouredCheque | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_04_24 / PRO.DishonouredCheque | 03_batch3_main_body+batch3_nested_block:embedded_05_25 / PRO.DishonouredCheque | high |
| temp_write_to_read | 03_batch3_main_body+batch3_nested_block:embedded_05_25 / #PenaltyStaging | 03_batch3_main_body+batch3_nested_block:embedded_07_27 / #PenaltyStaging | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_10_30 / PRO.ACLRUNNINGPROCESSSTATUS | 04_batch3_exception:chunk_text_08 / PRO.ACLRUNNINGPROCESSSTATUS | high |
| table_write_to_later_use | 04_batch3_exception:chunk_text_04 / PRO.ACLRUNNINGPROCESSSTATUS | 04_batch3_exception:chunk_text_08 / PRO.ACLRUNNINGPROCESSSTATUS | high |

Unresolved dependency candidates: 37. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 23
- **By rule type:** explicit = 23
- **By validation status:** unverified = 8, verified = 15

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 26
- **Deterministic-only facts:** 3
- **LLM-only claims:** 9
- **Conflicts:** 7
- **Unresolved items:** 1
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_read (`recon_a8e91f317680`): full_source
- `CONFLICT` tables_read (`recon_a8e91f317680`): full_source
- `CONFLICT` tables_read (`recon_a8e91f317680`): full_source
- `CONFLICT` tables_written (`recon_1c4a385129d7`): full_source
- `CONFLICT` tables_written (`recon_1c4a385129d7`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 83.58040372670807/100
- **Statement coverage:** 30 / 50 (60.0%)
- **Rule grounding coverage:** 18 / 23 (78.3%)
- **Decision-chain coverage:** 5 / 6 branches (83.3%)
- **Decision-chain coverage gaps:** 1 branch(es) require review (`EXISTS (SELECT 1 FROM PRO.ACLRUNNINGPROCESSSTATUS WHERE RUNNINGPROCESSNAME = 'Dishonoured_Cheque_Penalty_Calc')`)
- **Conflicts:** 7
- **Contradictions:** 8
- **Review required items:** 25
- **Review required:** Yes

Deterministic decision-chain coverage is incomplete (83.3%).; Statement parse success is below the preferred threshold.

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: D.PenaltyAmount
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: D.HoldForReview
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: D.PenaltyApplied
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO #PenaltyStaging
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE PRO.ACLRUNNINGPROCESSSTATUS
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE D
        SET D.PenaltyApplied = 'Y'
        FROM PRO.DishonouredCheque D
        WHERE D.DishonourDate = @ProcessDate
          AND NOT D.PenaltyAmount IS NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO #NewSuspensions
        SELECT P.AccountId
        FROM #PenaltyStaging P
        INNER JOIN PRO.LoanAccountCal A ON P.AccountId = A.AccountId
        WHERE P.DishonourCount >= 3 AND (A.ChequeBookSuspended <> 'Y' OR A.ChequeBookSuspended IS NULL)
- Synthesized in 6 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
