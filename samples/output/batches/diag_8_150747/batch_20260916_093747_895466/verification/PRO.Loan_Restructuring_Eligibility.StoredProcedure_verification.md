# Loan Restructuring Eligibility — Verification & Traceability

> Companion artifact to `PRO.Loan_Restructuring_Eligibility.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_e4fc72fc188b` |
| Raw technical object name (from source) | `Loan_Restructuring_Eligibility` |

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
| Source Hash | `b859a07238dacc50303d610ab22eae1ab45c1b21751706ed5e8962cce31f7ddd` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:39:49.342283+00:00` |
| Object ID | `obj_e4fc72fc188b` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_885975301283` |
| Total LLM Calls | `9` |
| Successful Calls | `9` |
| Failed Calls | `0` |
| Prompt Tokens | `86172` |
| Completion Tokens | `16389` |
| Total Tokens | `102561` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 6890 | available |
| synthesis | 7 | 7 | 0 | 67074 | available |
| synthesis_revision | 1 | 1 | 0 | 28597 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| ⚠️ 1 | Check process date against cutoff date [CONFLICT] (`rule__1`) | `RestructureEligible` | Determine if the process date is before the scheme cutoff date. |
| ⚠️ 2 | Insert into temporary table [MATCHED] (`rule__5`) | `AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths` | Insert records into the #RestructureDecisions table for eligible accounts. |
| ⚠️ 3 | Update RevisedTenureMonths [CONFLICT] (`rule__6`) | `RevisedTenureMonths` | Update the RevisedTenureMonths field in the #RestructureDecisions table based on the outstanding balance. |
| ⚠️ 4 | Merge RestructureRegister with temporary table [UNRESOLVED] (`rule__7`) | `Not specified` | Merge the PRO.RestructureRegister table with the #RestructureDecisions table. |
| ⚠️ 5 | Update AccountStatus and LastPaymentDueDate [MATCHED] (`rule__8`) | `LastPaymentDueDate, AccountStatus` | Update the AccountStatus and LastPaymentDueDate fields for eligible accounts. |
| ⚠️ 6 | Insert into RestructureAuditLog [MATCHED] (`rule__9`) | `AccountId, DecisionDate, EligibleFlag` | Insert records into the PRO.RestructureAuditLog table for accounts approved in the current run. |
| ⚠️ 7 | Set RestructureEligible to NOT_ASSESSED [MATCHED] (`rule__2`) | `RestructureEligible` | Set the RestructureEligible field to 'NOT_ASSESSED' if the outstanding balance is NULL. |
| ⚠️ 8 | Create temporary table [LLM_ONLY] (`rule__4`) | `Not specified` | Create the temporary #RestructureDecisions table. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Check process date against cutoff date (rule__1) | IF @ProcessDate < @SchemeCutoffDate | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | Needs Review |
| 2 | Insert into temporary table (rule__5) | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEligible IS NOT NULL AND… | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_20 | 03_batch3_main_body+batch3_nested_block:chunk_text_20 | Verified |
| 3 | Update RevisedTenureMonths (rule__6) | UPDATE D SET D.RevisedTenureMonths = CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WHERE D.EligibleFlag = 'Y' | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_19 | 03_batch3_main_body+batch3_nested_block:chunk_text_19 | Needs Review |
| 4 | Merge RestructureRegister with temporary table (rule__7) | MERGE PRO.RestructureRegister AS Target USING #RestructureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.EligibleFlag = Source.EligibleFlag, Target.RevisedTenureMonths = Source.RevisedTenureMonths, Target.LastEv… | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_27 | 03_batch3_main_body+batch3_nested_block:embedded_04_27 | Needs Review |
| 5 | Update AccountStatus and LastPaymentDueDate (rule__8) | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate) FROM PRO.LoanAccountCal A INNER JOIN #RestructureDecisions D ON D.AccountId = A.AccountId WHERE D.EligibleFlag = 'Y' | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_20 | 03_batch3_main_body+batch3_nested_block:chunk_text_20 | Verified |
| 6 | Insert into RestructureAuditLog (rule__9) | INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT R.AccountId, R.LastEvaluatedDate, R.EligibleFlag FROM PRO.RestructureRegister R WHERE R.LastEvaluatedDate = @ProcessDate AND R.EligibleFlag = 'Y' | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_27 | 03_batch3_main_body+batch3_nested_block:embedded_04_27 | Verified |
| 7 | Set RestructureEligible to NOT_ASSESSED (rule__2) | UPDATE A SET A.RestructureEligible = 'NOT_ASSESSED' FROM PRO.LoanAccountCal A WHERE A.OutstandingBalance IS NULL | Not cited | Not cited | Not cited | Verified |
| 8 | Create temporary table (rule__4) | CREATE TABLE #RestructureDecisions (AccountId VARCHAR(20), DecisionDate DATE, EligibleFlag VARCHAR(15), AssetClassAtEval VARCHAR(20), RevisedTenureMonths INT) | Not cited | Not cited | Not cited | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| decision_1241_2314_0:branch_001 | (A.AssetClass IN ('STANDARD', 'SMA')) AND ((A.PriorRestructureCount IS NULL OR A.PriorRestructureCount = 0) AND (A.OverdueDays <= 60)) | source \| Lines 33-55 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| decision_1241_2314_0:branch_002 | (A.AssetClass IN ('STANDARD', 'SMA')) AND (A.PriorRestructureCount IS NULL OR A.PriorRestructureCount = 0) | source \| Lines 33-55 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| decision_1241_2314_0:branch_003 | (A.AssetClass IN ('STANDARD', 'SMA')) AND ((A.PriorRestructureCount = 1) AND (A.OverdueDays <= 30 AND NOT A.OutstandingBalance IS NULL)) | source \| Lines 33-55 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| decision_1241_2314_0:branch_004 | (A.AssetClass IN ('STANDARD', 'SMA')) AND (A.PriorRestructureCount = 1) | source \| Lines 33-55 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| decision_1241_2314_0:branch_005 | A.AssetClass IN ('STANDARD', 'SMA') | source \| Lines 33-55 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| decision_1241_2314_0:branch_006 | ELSE | source \| Lines 33-55 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_07 |
| case_0094_0098_3821:branch_001 | A.OutstandingBalance > 1000000 | source \| Lines 95-96 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_19 |
| case_0094_0098_3821:branch_002 | A.OutstandingBalance > 500000 | source \| Lines 96-97 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_19 |
| case_0094_0098_3821:branch_003 | ELSE | source \| Lines 97-98 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_19 |
| decision_chain_003:branch_001 | A.AssetClass IN ('STANDARD', 'SMA') | source |
| decision_chain_003:branch_002 | ELSE | source |
| decision_chain_004:branch_001 | A.OutstandingBalance > 1000000 | source |
| decision_chain_004:branch_002 | A.OutstandingBalance > 500000 | source |
| decision_chain_004:branch_003 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 105
- **Disposition:** covered_by_rule=79, technical_only=5, uncovered=21

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
| STATEMENT | covered_by_rule | Lines 7-10 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @SchemeCutoffDate DATE = DATEADD(YEAR, -2, @ProcessDate) -- Rule 1: sequential IF/ELSE - the restructuring scheme is only -- open at all if today falls before the scheme cutoff |
| STATEMENT | covered_by_rule | Lines 11-11 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | IF @ProcessDate < @SchemeCutoffDate |
| STATEMENT | covered_by_rule | Lines 12-14 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | BEGIN -- Rule 2: nested IF/ELSE - only Standard or SMA accounts are -- considered; everything else is ineligible outright |
| UPDATE | covered_by_rule | Lines 15-36 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = CASE WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE -- Rule 3: within eligible asset classes, restructuring -- count and overdue history further narrow eligibility WHEN A.PriorRestructureCount IS... |
| STATEMENT | covered_by_rule | Lines 26-26 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 9-9 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | ELSE |
| STATEMENT | covered_by_rule | Lines 1-1 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 40-42 | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = 'SCHEME_CLOSED' FROM PRO.LoanAccountCal A |
| STATEMENT | covered_by_rule | Lines 43-46 | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | END -- Rule 4: accounts with no recorded outstanding balance cannot be -- assessed for restructuring at all and must be marked separately |
| UPDATE | covered_by_rule | Lines 47-50 | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = 'NOT_ASSESSED' FROM PRO.LoanAccountCal A WHERE A.OutstandingBalance IS NULL |
| STATEMENT | covered_by_rule | Lines 52-52 | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | IF OBJECT_ID('tempdb..#RestructureDecisions') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 53-53 | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | DROP TABLE #RestructureDecisions |
| INSERT | covered_by_rule | Lines 55-65 | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | CREATE TABLE #RestructureDecisions ( AccountId VARCHAR(20), DecisionDate DATE, EligibleFlag VARCHAR(15), AssetClassAtEval VARCHAR(20), RevisedTenureMonths INT ) -- Rule 5: conditional INSERT - capture the decision only for -- accounts th... |
| INSERT | covered_by_rule | Lines 66-73 | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| UPDATE | covered_by_rule | Lines 74-87 | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| MERGE | covered_by_rule | Lines 88-102 | 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block | MERGE PRO.RestructureRegister AS Target USING #RestructureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.EligibleFlag = Source.EligibleFlag, Target.RevisedTenureMonths = Source.RevisedTenur... |
| UPDATE | covered_by_rule | Lines 103-112 | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| INSERT | covered_by_rule | Lines 113-117 | 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT R.AccountId, R.LastEvaluatedDate, R.EligibleFlag FROM PRO.RestructureRegister R WHERE R.LastEvaluatedDate = @ProcessDate AND R.EligibleFlag = 'Y' |
| UPDATE | covered_by_rule | Lines 119-121 | 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| STATEMENT | covered_by_rule | Lines 123-123 | 03_batch3_main_body+batch3_nested_block:chunk_text_23, 03_batch3_main_body+batch3_nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 15-36 | 03_batch3_main_body+batch3_nested_block:embedded_01_24, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = CASE WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE -- Rule 3: within eligible asset classes, restructuring -- count and overdue history further narrow eligibility WHEN A.PriorRestructureCount IS... |
| UPDATE | covered_by_rule | Lines 40-42 | 03_batch3_main_body+batch3_nested_block:embedded_02_25, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = 'SCHEME_CLOSED' FROM PRO.LoanAccountCal A |
| UPDATE | covered_by_rule | Lines 47-50 | 03_batch3_main_body+batch3_nested_block:embedded_03_26, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = 'NOT_ASSESSED' FROM PRO.LoanAccountCal A WHERE A.OutstandingBalance IS NULL |
| INSERT | covered_by_rule | Lines 66-73 | 03_batch3_main_body+batch3_nested_block:embedded_04_27, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| UPDATE | covered_by_rule | Lines 74-87 | 03_batch3_main_body+batch3_nested_block:embedded_05_28, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| MERGE | covered_by_rule | Lines 88-102 | 03_batch3_main_body+batch3_nested_block:embedded_06_29, 03_batch3_main_body+batch3_nested_block | MERGE PRO.RestructureRegister AS Target USING #RestructureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.EligibleFlag = Source.EligibleFlag, Target.RevisedTenureMonths = Source.RevisedTenur... |
| UPDATE | covered_by_rule | Lines 103-112 | 03_batch3_main_body+batch3_nested_block:embedded_07_30, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| INSERT | covered_by_rule | Lines 113-117 | 03_batch3_main_body+batch3_nested_block:embedded_08_31, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT R.AccountId, R.LastEvaluatedDate, R.EligibleFlag FROM PRO.RestructureRegister R WHERE R.LastEvaluatedDate = @ProcessDate AND R.EligibleFlag = 'Y' |
| UPDATE | covered_by_rule | Lines 119-121 | 03_batch3_main_body+batch3_nested_block:embedded_09_32, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_05, 04_batch3_exception | END |
| UPDATE | uncovered | Lines 3-5 | 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| SET | uncovered | Lines 7-7 | 04_batch3_exception:embedded_02_07, 04_batch3_exception | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = CASE WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE -- Rule 3: within eligible asset classes, restructuring -- count and overdue history further narrow eligibility WHEN A.PriorRestructureCount IS... |
| UPDATE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = 'SCHEME_CLOSED' FROM PRO.LoanAccountCal A |
| UPDATE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = 'NOT_ASSESSED' FROM PRO.LoanAccountCal A WHERE A.OutstandingBalance IS NULL |
| INSERT_TEMP | technical_only | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| UPDATE_TEMP | technical_only | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| READ | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| MERGE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block | MERGE PRO.RestructureRegister AS Target USING #RestructureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.EligibleFlag = Source.EligibleFlag, Target.RevisedTenureMonths = Source.RevisedTenur... |
| UPDATE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| READ_TEMP | technical_only | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| INSERT | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT R.AccountId, R.LastEvaluatedDate, R.EligibleFlag FROM PRO.RestructureRegister R WHERE R.LastEvaluatedDate = @ProcessDate AND R.EligibleFlag = 'Y' |
| UPDATE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_24, 03_batch3_main_body+batch3_nested_block:embedded_01_24, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = CASE WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE -- Rule 3: within eligible asset classes, restructuring -- count and overdue history further narrow eligibility WHEN A.PriorRestructureCount IS... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_25, 03_batch3_main_body+batch3_nested_block:embedded_02_25, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = 'SCHEME_CLOSED' FROM PRO.LoanAccountCal A |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_26, 03_batch3_main_body+batch3_nested_block:embedded_03_26, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.RestructureEligible = 'NOT_ASSESSED' FROM PRO.LoanAccountCal A WHERE A.OutstandingBalance IS NULL |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_27, 03_batch3_main_body+batch3_nested_block:embedded_04_27, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_27, 03_batch3_main_body+batch3_nested_block:embedded_04_27, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_28, 03_batch3_main_body+batch3_nested_block:embedded_05_28, 03_batch3_main_body+batch3_nested_block | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_07_30, 03_batch3_main_body+batch3_nested_block:embedded_07_30, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_31, 03_batch3_main_body+batch3_nested_block:embedded_08_31, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT R.AccountId, R.LastEvaluatedDate, R.EligibleFlag FROM PRO.RestructureRegister R WHERE R.LastEvaluatedDate = @ProcessDate AND R.EligibleFlag = 'Y' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_09_32, 03_batch3_main_body+batch3_nested_block:embedded_09_32, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| UPDATE | uncovered | samples/08_Loan_Restructuring_Eligibility.sql / Lines 142-149 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| UPDATE | uncovered | unavailable | 04_batch3_exception:embedded_01_06, 04_batch3_exception:embedded_01_06, 04_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| IF_BRANCH | covered_by_rule | Lines 33-55 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | (A.AssetClass IN ('STANDARD', 'SMA')) AND ((A.PriorRestructureCount IS NULL OR A.PriorRestructureCount = 0) AND (A.OverdueDays <= 60)) |
| IF_BRANCH | covered_by_rule | Lines 33-55 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | (A.AssetClass IN ('STANDARD', 'SMA')) AND (A.PriorRestructureCount IS NULL OR A.PriorRestructureCount = 0) |
| IF_BRANCH | covered_by_rule | Lines 33-55 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | (A.AssetClass IN ('STANDARD', 'SMA')) AND ((A.PriorRestructureCount = 1) AND (A.OverdueDays <= 30 AND NOT A.OutstandingBalance IS NULL)) |
| IF_BRANCH | covered_by_rule | Lines 33-55 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | (A.AssetClass IN ('STANDARD', 'SMA')) AND (A.PriorRestructureCount = 1) |
| IF_BRANCH | covered_by_rule | Lines 33-55 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | A.AssetClass IN ('STANDARD', 'SMA') |
| ELSE | covered_by_rule | Lines 33-55 | 03_batch3_main_body+batch3_nested_block:chunk_text_07 | ELSE |
| CASE | covered_by_rule | Lines 95-96 | 03_batch3_main_body+batch3_nested_block:chunk_text_19 | A.OutstandingBalance > 1000000 |
| CASE | covered_by_rule | Lines 96-97 | 03_batch3_main_body+batch3_nested_block:chunk_text_19 | A.OutstandingBalance > 500000 |
| ELSE | covered_by_rule | Lines 97-98 | 03_batch3_main_body+batch3_nested_block:chunk_text_19 | ELSE |
| IF_BRANCH | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | full_source | A.AssetClass IN ('STANDARD', 'SMA') |
| ELSE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | full_source | A.OutstandingBalance > 1000000 |
| IF_BRANCH | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | full_source | A.OutstandingBalance > 500000 |
| ELSE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | full_source | ELSE |
| IF | covered_by_rule | Lines 29-29 | unavailable | IF @ProcessDate < @SchemeCutoffDate |
| CASE | covered_by_rule | Lines 35-35 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 36-36 | unavailable | WHEN A.AssetClass IN ( , ) THEN |
| CASE | covered_by_rule | Lines 37-37 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 40-40 | unavailable | WHEN A.PriorRestructureCount IS NULL OR A.PriorRestructureCount = 0 THEN |
| CASE | covered_by_rule | Lines 41-41 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 42-42 | unavailable | WHEN A.OverdueDays <= 60 THEN |
| ELSE | covered_by_rule | Lines 43-43 | unavailable | ELSE |
| CASE_BRANCH | uncovered | Lines 45-45 | unavailable | WHEN A.PriorRestructureCount = 1 THEN |
| CASE | covered_by_rule | Lines 46-46 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 47-47 | unavailable | WHEN A.OverdueDays <= 30 AND A.OutstandingBalance IS NOT NULL THEN |
| ELSE | covered_by_rule | Lines 48-48 | unavailable | ELSE |
| ELSE | covered_by_rule | Lines 50-50 | unavailable | ELSE |
| ELSE | covered_by_rule | Lines 52-52 | unavailable | ELSE |
| ELSE | covered_by_rule | Lines 56-56 | unavailable | ELSE |
| IF | uncovered | Lines 70-70 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 94-94 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 95-95 | unavailable | WHEN A.OutstandingBalance > 1000000 THEN 60 |
| CASE_BRANCH | covered_by_rule | Lines 96-96 | unavailable | WHEN A.OutstandingBalance > 500000 THEN 48 |
| ELSE | covered_by_rule | Lines 97-97 | unavailable | ELSE 36 |
| CASE_BRANCH | covered_by_rule | Lines 109-109 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | covered_by_rule | Lines 114-114 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CATCH | uncovered | Lines 142-142 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 147-147 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| later_update_overrides_field | 03_batch3_main_body+batch3_nested_block:embedded_01_24 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_02_25 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_24 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_04_27 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_25 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_04_27 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_03_26 / PRO.LoanAccountCal | 03_batch3_main_body+batch3_nested_block:embedded_04_27 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_04_27 / #RestructureDecisions | 03_batch3_main_body+batch3_nested_block:embedded_05_28 / #RestructureDecisions | high |

Unresolved dependency candidates: 46. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 8
- **By rule type:** explicit = 8
- **By validation status:** unverified = 4, verified = 4

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 13
- **Deterministic-only facts:** 2
- **LLM-only claims:** 1
- **Conflicts:** 6
- **Unresolved items:** 1
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_e412afd2fc54`): full_source
- `CONFLICT` tables_written (`recon_e412afd2fc54`): full_source
- `CONFLICT` tables_written (`recon_e412afd2fc54`): full_source
- `CONFLICT` tables_written (`recon_e412afd2fc54`): full_source
- `CONFLICT` rule (`recon_b53da4d75597`): rule__1, 03_batch3_main_body+batch3_nested_block, 03_batch3_main_body+batch3_nested_block:chunk_text_07;03_batch3_main_body+batch3_nested_block:chunk_text_11;03_batch3_main_body+batch3_nested_block:chunk_text_13;03_batch3_main_body+batch3_nested_block:embedded_01_24;03_batch3_main_body+batch3_nested_block:embedded_02_25;03_batch3_main_body+batch3_nested_block:embedded_03_26;03_batch3_main_body+batch3_nested_block:embedded_04_27 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 86.39423076923076/100
- **Statement coverage:** 26 / 44 (59.1%)
- **Rule grounding coverage:** 7 / 8 (87.5%)
- **Decision-chain coverage:** 9 / 9 branches (100.0%)
- **Conflicts:** 6
- **Contradictions:** 8
- **Review required items:** 16
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Operation Conflict on `source`: Synthesized table operation conflicts with deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: First condition met
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Second condition met
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Third condition met
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Condition for updating RevisedTenureMonths
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE WHEN A.PriorRestructureCount IS NULL OR A.PriorRestructureCount = 0 THEN CASE WHEN A.OverdueDays <= 60 THEN 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) VALUES (A.AccountId, @ProcessDate, D.EligibleFlag, A.AssetClass, D.RevisedTenureMonths)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE #RestructureDecisions SET RevisedTenureMonths = D.RevisedTenureMonths WHERE EligibleFlag = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT AccountId, @ProcessDate, EligibleFlag FROM #RestructureDecisions WHERE EligibleFlag = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.RestructureEligible = 'Y' FROM PRO.LoanAccountCal A INNER JOIN #RestructureDecisions D ON D.AccountId = A.AccountId WHERE A.OutstandingBalance IS NULL AND D.EligibleFlag = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate) FROM PRO.LoanAccountCal A INNER JOIN #RestructureDecisions D ON D.AccountId = A.AccountId WHERE D.EligibleFlag = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #RestructureDecisions D ON D.AccountId = A.AccountId WHERE A.RestructureEligible IS NOT NULL AND A.RestructureEligible <> 'NOT_ASSESSED' AND D.EligibleFlag = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.OutstandingBalance IS NULL AND D.EligibleFlag = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.AccountStatus = 'RESTRUCTURED' FROM PRO.LoanAccountCal A INNER JOIN #RestructureDecisions D ON D.AccountId = A.AccountId WHERE D.EligibleFlag = 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #RestructureDecisions D ON D.AccountId = A.AccountId WHERE D.EligibleFlag = 'Y'
- Synthesized in 7 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
