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
| Prompt Version | `4f519f469b95300a` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `b859a07238dacc50303d610ab22eae1ab45c1b21751706ed5e8962cce31f7ddd` |
| Configuration Version | `db93bfb59420a471` |
| Run Timestamp | `2026-09-16T23:15:11.424194+00:00` |
| Object ID | `obj_e4fc72fc188b` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_5f62b20d7c4a` |
| Total LLM Calls | `8` |
| Successful Calls | `8` |
| Failed Calls | `0` |
| Prompt Tokens | `46341` |
| Completion Tokens | `7428` |
| Total Tokens | `53769` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 7181 | available |
| synthesis | 7 | 7 | 0 | 46588 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Insert into #RestructureDecisions [MATCHED] (`deterministic_statement_03_batch3_main_body:chunk_text_05_accountid`) | `AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths` | Not specified |
| 🟠 2 | Update AccountStatus, LastPaymentDueDate, PriorRestructureCount [MATCHED] (`deterministic_statement_05_batch3_main_body:chunk_text_01_accountstatus`) | `AccountStatus, LastPaymentDueDate, PriorRestructureCount` | Not specified |
| 🟠 3 | Insert into RestructureAuditLog [MATCHED] (`deterministic_statement_05_batch3_main_body:chunk_text_02_accountid`) | `AccountId, DecisionDate, EligibleFlag` | Not specified |
| 🟠 4 | Upsert restructureregister [MATCHED] (`deterministic_statement_04_batch3_main_body:chunk_text_01:MATCHED_eligibleflag+upsert`) | `EligibleFlag, RevisedTenureMonths, LastEvaluatedDate, AccountId, FirstEvaluatedDate` | Refresh existing rows and insert rows not already present. |
| 🟠 5 | Determine RestructureEligible [MATCHED] (`deterministic_tsql_if_0029_0061_restructureeligible`) | `RestructureEligible` | Not specified |
| 🟠 6 | Determine RestructureEligible [MATCHED] (`deterministic_decision_1241_2314_0_restructureeligible`) | `RestructureEligible` | Not specified |
| 🟢 7 | Update revised tenure months [MATCHED] (`rule__3`) | `RevisedTenureMonths` | Update the 'RevisedTenureMonths' field in '#RestructureDecisions' based on the outstanding balance of the loan account. |
| 🟠 8 | Upsert restructuredecisions [LLM_ONLY] (`rule__1__8+upsert`) | `#RestructureDecisions.EligibleFlag, #RestructureDecisions.RevisedTenureMonths, #RestructureDecisions.LastEvaluatedDate, AccountId, EligibleFlag, RevisedTenureMonths, FirstEvaluatedDate, LastEvaluatedDate` | Update the eligibility flag, revised tenure months, and last evaluated date for matched restructuring records. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Insert into #RestructureDecisions (deterministic_statement_03_batch3_main_body:chunk_text_05_accountid) | Not cited | source | 03_batch3_main_body | Not cited | Verified |
| 2 | Update AccountStatus, LastPaymentDueDate, PriorRestructureCount (deterministic_statement_05_batch3_main_body:chunk_text_01_accountstatus) | Not cited | source | 05_batch3_main_body | Not cited | Verified |
| 3 | Insert into RestructureAuditLog (deterministic_statement_05_batch3_main_body:chunk_text_02_accountid) | Not cited | source | 05_batch3_main_body | Not cited | Verified |
| 4 | Upsert restructureregister (deterministic_statement_04_batch3_main_body:chunk_text_01:MATCHED_eligibleflag+upsert) | Not cited | source \| Lines 106-120 | 04_batch3_main_body | Not cited | Verified |
| 5 | Determine RestructureEligible (deterministic_tsql_if_0029_0061_restructureeligible) | Not cited | source \| Lines 29-61 | Not cited | Not cited | Verified |
| 6 | Determine RestructureEligible (deterministic_decision_1241_2314_0_restructureeligible) | Not cited | source \| Lines 33-55 | Not cited | Not cited | Verified |
| 7 | Update revised tenure months (rule__3) | #RestructureDecisions.EligibleFlag = 'Y'; CASE WHEN PRO.LoanAccountCal.OutstandingBalance > 1000000 THEN 60 WHEN PRO.LoanAccountCal.OutstandingBalance > 500000 THEN 48 ELSE 36 END | Not cited | table_operations[2] | Not cited | Verified |
| 8 | Upsert restructuredecisions (rule__1__8+upsert) | WHEN MATCHED THEN UPDATE SET #RestructureDecisions.EligibleFlag = #RestructureDecisions.EligibleFlag, #RestructureDecisions.RevisedTenureMonths = #RestructureDecisions.RevisedTenureMonths, #RestructureDecisions.LastEvaluatedDate = @ProcessDate | Not cited | MERGE statement | Not cited | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| tsql_if_0029_0061:branch_001 | @ProcessDate < @SchemeCutoffDate | samples/08_Loan_Restructuring_Eligibility.sql \| Lines 30-55 \| Chunk 01_batch3_nested_block \| Statement 03_batch3_main_body:chunk_text_05 |
| tsql_if_0029_0061:branch_002 | ELSE | source \| Lines 57-61 |
| decision_1241_2314_0:branch_001 | (PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA')) AND ((PRO.LoanAccountCal.PriorRestructureCount IS NULL OR PRO.LoanAccountCal.PriorRestructureCount = 0) AND (PRO.LoanAccountCal.OverdueDays <= 60)) | samples/08_Loan_Restructuring_Eligibility.sql \| Lines 33-55 \| Chunk 01_batch3_nested_block \| Statement 03_batch3_main_body:chunk_text_05 |
| decision_1241_2314_0:branch_002 | (PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA')) AND (PRO.LoanAccountCal.PriorRestructureCount IS NULL OR PRO.LoanAccountCal.PriorRestructureCount = 0) | samples/08_Loan_Restructuring_Eligibility.sql \| Lines 33-55 \| Chunk 01_batch3_nested_block \| Statement 03_batch3_main_body:chunk_text_05 |
| decision_1241_2314_0:branch_003 | (PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA')) AND ((PRO.LoanAccountCal.PriorRestructureCount = 1) AND (PRO.LoanAccountCal.OverdueDays <= 30 AND NOT PRO.LoanAccountCal.OutstandingBalance IS NULL)) | samples/08_Loan_Restructuring_Eligibility.sql \| Lines 33-55 \| Chunk 01_batch3_nested_block \| Statement 03_batch3_main_body:chunk_text_05 |
| decision_1241_2314_0:branch_004 | (PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA')) AND (PRO.LoanAccountCal.PriorRestructureCount = 1) | samples/08_Loan_Restructuring_Eligibility.sql \| Lines 33-55 \| Chunk 01_batch3_nested_block \| Statement 03_batch3_main_body:chunk_text_05 |
| decision_1241_2314_0:branch_005 | PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA') | samples/08_Loan_Restructuring_Eligibility.sql \| Lines 33-55 \| Chunk 01_batch3_nested_block \| Statement 03_batch3_main_body:chunk_text_05 |
| decision_1241_2314_0:branch_006 | ELSE | samples/08_Loan_Restructuring_Eligibility.sql \| Lines 33-55 \| Chunk 01_batch3_nested_block \| Statement 03_batch3_main_body:chunk_text_05 |
| case_0094_0098_3821:branch_001 | PRO.LoanAccountCal.OutstandingBalance > 1000000 | source \| Lines 95-96 |
| case_0094_0098_3821:branch_002 | PRO.LoanAccountCal.OutstandingBalance > 500000 | source \| Lines 96-97 |
| case_0094_0098_3821:branch_003 | ELSE | source \| Lines 97-98 |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 96
- **Disposition:** covered_by_rule=63, technical_only=5, uncovered=28

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-5 | 00_batch3_main_body+batch3_nested_block:chunk_text_01, 00_batch3_main_body+batch3_nested_block | USE [DEMO_MISDB] SET ANSI_NULLS ON SET QUOTED_IDENTIFIER ON |
| STATEMENT | uncovered | Lines 7-8 | 00_batch3_main_body+batch3_nested_block:chunk_text_02, 00_batch3_main_body+batch3_nested_block | BEGIN SET NOCOUNT ON |
| STATEMENT | uncovered | Lines 9-9 | 00_batch3_main_body+batch3_nested_block:chunk_text_03, 00_batch3_main_body+batch3_nested_block | BEGIN TRY |
| SELECT | uncovered | Lines 11-11 | 00_batch3_main_body+batch3_nested_block:chunk_text_04, 00_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| STATEMENT | uncovered | Lines 12-15 | 00_batch3_main_body+batch3_nested_block:chunk_text_05, 00_batch3_main_body+batch3_nested_block | DECLARE @SchemeCutoffDate DATE = DATEADD(YEAR, -2, @ProcessDate) -- Rule 1: sequential IF/ELSE - the restructuring scheme is only -- open at all if today falls before the scheme cutoff |
| STATEMENT | covered_by_rule | Lines 16-16 | 00_batch3_main_body+batch3_nested_block:chunk_text_06, 00_batch3_main_body+batch3_nested_block | IF @ProcessDate < @SchemeCutoffDate |
| STATEMENT | uncovered | Lines 18-20 | 00_batch3_main_body+batch3_nested_block:chunk_text_07, 00_batch3_main_body+batch3_nested_block | BEGIN -- Rule 2: nested IF/ELSE - only Standard or SMA accounts are -- considered; everything else is ineligible outright |
| UPDATE | uncovered | Lines 1-22 | 01_batch3_nested_block:chunk_text_01, 01_batch3_nested_block | UPDATE A SET A.RestructureEligible = CASE WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE -- Rule 3: within eligible asset classes, restructuring -- count and overdue history further narrow eligibility WHEN A.PriorRestructureCount IS... |
| UPDATE | uncovered | Lines 1-22 | 01_batch3_nested_block:embedded_01_02, 01_batch3_nested_block | UPDATE A SET A.RestructureEligible = CASE WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE -- Rule 3: within eligible asset classes, restructuring -- count and overdue history further narrow eligibility WHEN A.PriorRestructureCount IS... |
| STATEMENT | covered_by_rule | Lines 1-1 | 02_batch3_nested_block+batch3_main_body:chunk_text_01, 02_batch3_nested_block+batch3_main_body | END |
| STATEMENT | covered_by_rule | Lines 3-3 | 02_batch3_nested_block+batch3_main_body:chunk_text_02, 02_batch3_nested_block+batch3_main_body | ELSE |
| STATEMENT | uncovered | Lines 5-5 | 02_batch3_nested_block+batch3_main_body:chunk_text_03, 02_batch3_nested_block+batch3_main_body | BEGIN |
| UPDATE | uncovered | Lines 6-8 | 02_batch3_nested_block+batch3_main_body:chunk_text_04, 02_batch3_nested_block+batch3_main_body | UPDATE A SET A.RestructureEligible = 'SCHEME_CLOSED' FROM PRO.LoanAccountCal A |
| STATEMENT | covered_by_rule | Lines 1-1 | 02_batch3_nested_block+batch3_main_body:chunk_text_05, 02_batch3_nested_block+batch3_main_body | END |
| UPDATE | uncovered | Lines 6-8 | 02_batch3_nested_block+batch3_main_body:embedded_01_06, 02_batch3_nested_block+batch3_main_body | UPDATE A SET A.RestructureEligible = 'SCHEME_CLOSED' FROM PRO.LoanAccountCal A |
| UPDATE | covered_by_rule | Lines 1-6 | 03_batch3_main_body:chunk_text_01, 03_batch3_main_body | -- Rule 4: accounts with no recorded outstanding balance cannot be -- assessed for restructuring at all and must be marked separately UPDATE A SET A.RestructureEligible = 'NOT_ASSESSED' FROM PRO.LoanAccountCal A WHERE A.OutstandingBalanc... |
| STATEMENT | covered_by_rule | Lines 10-10 | 03_batch3_main_body:chunk_text_02, 03_batch3_main_body | IF OBJECT_ID('tempdb..#RestructureDecisions') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 13-13 | 03_batch3_main_body:chunk_text_03, 03_batch3_main_body | DROP TABLE #RestructureDecisions |
| INSERT | covered_by_rule | Lines 17-27 | 03_batch3_main_body:chunk_text_04, 03_batch3_main_body | CREATE TABLE #RestructureDecisions ( AccountId VARCHAR(20), DecisionDate DATE, EligibleFlag VARCHAR(15), AssetClassAtEval VARCHAR(20), RevisedTenureMonths INT ) -- Rule 5: conditional INSERT - capture the decision only for -- accounts th... |
| INSERT | covered_by_rule | Lines 30-37 | 03_batch3_main_body:chunk_text_05, 03_batch3_main_body | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| UPDATE | covered_by_rule | Lines 40-53 | 03_batch3_main_body:chunk_text_06, 03_batch3_main_body | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| INSERT | covered_by_rule | Lines 30-37 | 03_batch3_main_body:embedded_01_07, 03_batch3_main_body | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| UPDATE | covered_by_rule | Lines 40-53 | 03_batch3_main_body:embedded_02_08, 03_batch3_main_body | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| MERGE | covered_by_rule | Lines 1-15 | 04_batch3_main_body:chunk_text_01, 04_batch3_main_body | MERGE PRO.RestructureRegister AS Target USING #RestructureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.EligibleFlag = Source.EligibleFlag, Target.RevisedTenureMonths = Source.RevisedTenur... |
| MERGE | covered_by_rule | Lines 1-15 | 04_batch3_main_body:embedded_01_02, 04_batch3_main_body | MERGE PRO.RestructureRegister AS Target USING #RestructureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.EligibleFlag = Source.EligibleFlag, Target.RevisedTenureMonths = Source.RevisedTenur... |
| UPDATE | covered_by_rule | Lines 1-10 | 05_batch3_main_body:chunk_text_01, 05_batch3_main_body | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| INSERT | covered_by_rule | Lines 13-17 | 05_batch3_main_body:chunk_text_02, 05_batch3_main_body | INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT R.AccountId, R.LastEvaluatedDate, R.EligibleFlag FROM PRO.RestructureRegister R WHERE R.LastEvaluatedDate = @ProcessDate AND R.EligibleFlag = 'Y' |
| UPDATE | covered_by_rule | Lines 21-23 | 05_batch3_main_body:chunk_text_03, 05_batch3_main_body | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| STATEMENT | covered_by_rule | Lines 27-27 | 05_batch3_main_body:chunk_text_04, 05_batch3_main_body | END TRY |
| UPDATE | covered_by_rule | Lines 1-10 | 05_batch3_main_body:embedded_01_05, 05_batch3_main_body | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| INSERT | covered_by_rule | Lines 13-17 | 05_batch3_main_body:embedded_02_06, 05_batch3_main_body | INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT R.AccountId, R.LastEvaluatedDate, R.EligibleFlag FROM PRO.RestructureRegister R WHERE R.LastEvaluatedDate = @ProcessDate AND R.EligibleFlag = 'Y' |
| UPDATE | covered_by_rule | Lines 21-23 | 05_batch3_main_body:embedded_03_07, 05_batch3_main_body | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| STATEMENT | uncovered | Lines 1-2 | 06_batch3_exception:chunk_text_01, 06_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 3-5 | 06_batch3_exception:chunk_text_02, 06_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| STATEMENT | uncovered | Lines 6-6 | 06_batch3_exception:chunk_text_03, 06_batch3_exception | END CATCH |
| SET | uncovered | Lines 7-7 | 06_batch3_exception:chunk_text_04, 06_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 06_batch3_exception:chunk_text_05, 06_batch3_exception | END |
| UPDATE | uncovered | Lines 3-5 | 06_batch3_exception:embedded_01_06, 06_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| SET | uncovered | Lines 7-7 | 06_batch3_exception:embedded_02_07, 06_batch3_exception | SET NOCOUNT OFF |
| READ | uncovered | unavailable | 00_batch3_main_body+batch3_nested_block:chunk_text_04, 00_batch3_main_body+batch3_nested_block:chunk_text_04, 00_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql / Lines 33-54 | 01_batch3_nested_block:chunk_text_01, 01_batch3_nested_block:chunk_text_01, 01_batch3_nested_block | UPDATE A SET A.RestructureEligible = CASE WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE -- Rule 3: within eligible asset classes, restructuring -- count and overdue history further narrow eligibility WHEN A.PriorRestructureCount IS... |
| UPDATE | uncovered | unavailable | 01_batch3_nested_block:embedded_01_02, 01_batch3_nested_block:embedded_01_02, 01_batch3_nested_block | UPDATE A SET A.RestructureEligible = CASE WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE -- Rule 3: within eligible asset classes, restructuring -- count and overdue history further narrow eligibility WHEN A.PriorRestructureCount IS... |
| UPDATE | uncovered | samples/08_Loan_Restructuring_Eligibility.sql | 02_batch3_nested_block+batch3_main_body:chunk_text_04, 02_batch3_nested_block+batch3_main_body:chunk_text_04, 02_batch3_nested_block+batch3_main_body | UPDATE A SET A.RestructureEligible = 'SCHEME_CLOSED' FROM PRO.LoanAccountCal A |
| UPDATE | uncovered | unavailable | 02_batch3_nested_block+batch3_main_body:embedded_01_06, 02_batch3_nested_block+batch3_main_body:embedded_01_06, 02_batch3_nested_block+batch3_main_body | UPDATE A SET A.RestructureEligible = 'SCHEME_CLOSED' FROM PRO.LoanAccountCal A |
| UPDATE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body:chunk_text_01, 03_batch3_main_body:chunk_text_01, 03_batch3_main_body | -- Rule 4: accounts with no recorded outstanding balance cannot be -- assessed for restructuring at all and must be marked separately UPDATE A SET A.RestructureEligible = 'NOT_ASSESSED' FROM PRO.LoanAccountCal A WHERE A.OutstandingBalanc... |
| INSERT_TEMP | technical_only | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body:chunk_text_05, 03_batch3_main_body:chunk_text_05, 03_batch3_main_body | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| UPDATE_TEMP | technical_only | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body:chunk_text_06, 03_batch3_main_body:chunk_text_06, 03_batch3_main_body | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| READ | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 03_batch3_main_body:chunk_text_06, 03_batch3_main_body:chunk_text_06, 03_batch3_main_body | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| READ | covered_by_rule | unavailable | 03_batch3_main_body:embedded_01_07, 03_batch3_main_body:embedded_01_07, 03_batch3_main_body | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_main_body:embedded_01_07, 03_batch3_main_body:embedded_01_07, 03_batch3_main_body | INSERT INTO #RestructureDecisions (AccountId, DecisionDate, EligibleFlag, AssetClassAtEval, RevisedTenureMonths) SELECT A.AccountId, @ProcessDate, A.RestructureEligible, A.AssetClass, NULL FROM PRO.LoanAccountCal A WHERE A.RestructureEli... |
| UPDATE_TEMP | technical_only | unavailable | 03_batch3_main_body:embedded_02_08, 03_batch3_main_body:embedded_02_08, 03_batch3_main_body | UPDATE D SET D.RevisedTenureMonths = ( CASE WHEN A.OutstandingBalance > 1000000 THEN 60 WHEN A.OutstandingBalance > 500000 THEN 48 ELSE 36 END ) FROM #RestructureDecisions D INNER JOIN PRO.LoanAccountCal A ON A.AccountId = D.AccountId WH... |
| MERGE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql / Lines 106-120 | 04_batch3_main_body:chunk_text_01, 04_batch3_main_body:chunk_text_01, 04_batch3_main_body | MERGE PRO.RestructureRegister AS Target USING #RestructureDecisions AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.EligibleFlag = Source.EligibleFlag, Target.RevisedTenureMonths = Source.RevisedTenur... |
| UPDATE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 05_batch3_main_body:chunk_text_01, 05_batch3_main_body:chunk_text_01, 05_batch3_main_body | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| READ_TEMP | technical_only | samples/08_Loan_Restructuring_Eligibility.sql | 05_batch3_main_body:chunk_text_01, 05_batch3_main_body:chunk_text_01, 05_batch3_main_body | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| INSERT | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 05_batch3_main_body:chunk_text_02, 05_batch3_main_body:chunk_text_02, 05_batch3_main_body | INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT R.AccountId, R.LastEvaluatedDate, R.EligibleFlag FROM PRO.RestructureRegister R WHERE R.LastEvaluatedDate = @ProcessDate AND R.EligibleFlag = 'Y' |
| UPDATE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql | 05_batch3_main_body:chunk_text_03, 05_batch3_main_body:chunk_text_03, 05_batch3_main_body | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| UPDATE | covered_by_rule | unavailable | 05_batch3_main_body:embedded_01_05, 05_batch3_main_body:embedded_01_05, 05_batch3_main_body | UPDATE A SET A.AccountStatus = 'RESTRUCTURED', A.LastPaymentDueDate = DATEADD(MONTH, D.RevisedTenureMonths, @ProcessDate), A.PriorRestructureCount = ISNULL(A.PriorRestructureCount, 0) + 1 FROM PRO.LoanAccountCal A INNER JOIN #Restructure... |
| READ | covered_by_rule | unavailable | 05_batch3_main_body:embedded_02_06, 05_batch3_main_body:embedded_02_06, 05_batch3_main_body | INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag) SELECT R.AccountId, R.LastEvaluatedDate, R.EligibleFlag FROM PRO.RestructureRegister R WHERE R.LastEvaluatedDate = @ProcessDate AND R.EligibleFlag = 'Y' |
| UPDATE | covered_by_rule | unavailable | 05_batch3_main_body:embedded_03_07, 05_batch3_main_body:embedded_03_07, 05_batch3_main_body | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| UPDATE | uncovered | samples/08_Loan_Restructuring_Eligibility.sql / Lines 142-149 | 06_batch3_exception:chunk_text_02, 06_batch3_exception:chunk_text_02, 06_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| UPDATE | uncovered | unavailable | 06_batch3_exception:embedded_01_06, 06_batch3_exception:embedded_01_06, 06_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Loan_Restructuring_Eligibility' |
| IF_BRANCH | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql / Lines 30-55 | 03_batch3_main_body:chunk_text_05, 01_batch3_nested_block | @ProcessDate < @SchemeCutoffDate |
| ELSE | covered_by_rule | Lines 57-61 | unavailable | ELSE |
| IF_BRANCH | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql / Lines 33-55 | 03_batch3_main_body:chunk_text_05, 01_batch3_nested_block | (PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA')) AND ((PRO.LoanAccountCal.PriorRestructureCount IS NULL OR PRO.LoanAccountCal.PriorRestructureCount = 0) AND (PRO.LoanAccountCal.OverdueDays <= 60)) |
| IF_BRANCH | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql / Lines 33-55 | 03_batch3_main_body:chunk_text_05, 01_batch3_nested_block | (PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA')) AND (PRO.LoanAccountCal.PriorRestructureCount IS NULL OR PRO.LoanAccountCal.PriorRestructureCount = 0) |
| IF_BRANCH | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql / Lines 33-55 | 03_batch3_main_body:chunk_text_05, 01_batch3_nested_block | (PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA')) AND ((PRO.LoanAccountCal.PriorRestructureCount = 1) AND (PRO.LoanAccountCal.OverdueDays <= 30 AND NOT PRO.LoanAccountCal.OutstandingBalance IS NULL)) |
| IF_BRANCH | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql / Lines 33-55 | 03_batch3_main_body:chunk_text_05, 01_batch3_nested_block | (PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA')) AND (PRO.LoanAccountCal.PriorRestructureCount = 1) |
| IF_BRANCH | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql / Lines 33-55 | 03_batch3_main_body:chunk_text_05, 01_batch3_nested_block | PRO.LoanAccountCal.AssetClass IN ('STANDARD', 'SMA') |
| ELSE | covered_by_rule | samples/08_Loan_Restructuring_Eligibility.sql / Lines 33-55 | 03_batch3_main_body:chunk_text_05, 01_batch3_nested_block | ELSE |
| CASE | covered_by_rule | Lines 95-96 | unavailable | PRO.LoanAccountCal.OutstandingBalance > 1000000 |
| CASE | covered_by_rule | Lines 96-97 | unavailable | PRO.LoanAccountCal.OutstandingBalance > 500000 |
| ELSE | covered_by_rule | Lines 97-98 | unavailable | ELSE |
| IF | covered_by_rule | Lines 29-29 | unavailable | IF @ProcessDate < @SchemeCutoffDate |
| CASE | covered_by_rule | Lines 35-35 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 36-36 | unavailable | WHEN A.AssetClass IN ( , ) THEN |
| CASE | covered_by_rule | Lines 37-37 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 40-40 | unavailable | WHEN A.PriorRestructureCount IS NULL OR A.PriorRestructureCount = 0 THEN |
| CASE | covered_by_rule | Lines 41-41 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 42-42 | unavailable | WHEN A.OverdueDays <= 60 THEN |
| ELSE | covered_by_rule | Lines 43-43 | unavailable | ELSE |
| CASE_BRANCH | covered_by_rule | Lines 45-45 | unavailable | WHEN A.PriorRestructureCount = 1 THEN |
| CASE | covered_by_rule | Lines 46-46 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 47-47 | unavailable | WHEN A.OverdueDays <= 30 AND A.OutstandingBalance IS NOT NULL THEN |
| ELSE | covered_by_rule | Lines 48-48 | unavailable | ELSE |
| ELSE | covered_by_rule | Lines 50-50 | unavailable | ELSE |
| ELSE | covered_by_rule | Lines 52-52 | unavailable | ELSE |
| ELSE | covered_by_rule | Lines 56-56 | unavailable | ELSE |
| IF | uncovered | Lines 70-70 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 94-94 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 95-95 | unavailable | WHEN A.OutstandingBalance > 1000000 THEN 60 |
| CASE_BRANCH | uncovered | Lines 96-96 | unavailable | WHEN A.OutstandingBalance > 500000 THEN 48 |
| ELSE | covered_by_rule | Lines 97-97 | unavailable | ELSE 36 |
| CASE_BRANCH | covered_by_rule | Lines 109-109 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | covered_by_rule | Lines 114-114 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CATCH | uncovered | Lines 142-142 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 147-147 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| later_update_overrides_field | 01_batch3_nested_block:embedded_01_02 / PRO.LoanAccountCal | 02_batch3_nested_block+batch3_main_body:embedded_01_06 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 01_batch3_nested_block:embedded_01_02 / PRO.LoanAccountCal | 03_batch3_main_body:embedded_01_07 / PRO.LoanAccountCal | high |
| later_update_overrides_field | 01_batch3_nested_block:embedded_01_02 / PRO.LoanAccountCal | 01_batch3_nested_block:chunk_text_01 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 05_batch3_main_body:embedded_01_05 / PRO.LoanAccountCal | 03_batch3_main_body:embedded_01_07 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 02_batch3_nested_block+batch3_main_body:embedded_01_06 / PRO.LoanAccountCal | 03_batch3_main_body:embedded_01_07 / PRO.LoanAccountCal | high |
| later_update_overrides_field | 02_batch3_nested_block+batch3_main_body:embedded_01_06 / PRO.LoanAccountCal | 01_batch3_nested_block:chunk_text_01 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_main_body:embedded_01_07 / #RestructureDecisions | 03_batch3_main_body:embedded_02_08 / #RestructureDecisions | high |

Unresolved dependency candidates: 36. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 8
- **By rule type:** deterministic_decision_table = 6, explicit = 2
- **By validation status:** unverified = 1, verified = 7

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 18
- **Deterministic-only facts:** 6
- **LLM-only claims:** 3
- **Conflicts:** 4
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_e412afd2fc54`): full_source
- `LLM_ONLY` tables_written (`recon_92caf8dde7b5`): full_source
- `CONFLICT` tables_written (`recon_e412afd2fc54`): full_source
- `CONFLICT` tables_written (`recon_e412afd2fc54`): full_source
- `LLM_ONLY` tables_written (`recon_92caf8dde7b5`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 77.00945626477542/100
- **Statement coverage:** 21 / 39 (53.8%)
- **Rule grounding coverage:** 2 / 9 (22.2%)
- **Decision-chain coverage:** 11 / 11 branches (100.0%)
- **Conflicts:** 4
- **Contradictions:** 6
- **Review required items:** 13
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Operation Conflict on `source`: Synthesized table operation conflicts with deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: IF @ProcessDate < @SchemeCutoffDate
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: WHEN A.AssetClass IN ('STANDARD', 'SMA') THEN CASE WHEN A.PriorRestructureCount IS NULL OR A.PriorRestructureCount = 0 THEN CASE WHEN A.OverdueDays <= 60 THEN 'Y'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: WHEN A.PriorRestructureCount = 0 THEN 'Y' WHEN A.OverdueDays <= 30 AND A.OutstandingBalance IS NOT NULL THEN 'Y' ELSE 'N'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO PRO.RestructureAuditLog (AccountId, DecisionDate, EligibleFlag)
        SELECT AccountId, @ProcessDate, EligibleFlag
        FROM PRO.RestructureRegister
        WHERE LastEvaluatedDate = @ProcessDate AND EligibleFlag = 'Y'
- Synthesized in 7 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
- Automated style check flagged possible leftover technical jargon in the synthesized output: merge statement.
