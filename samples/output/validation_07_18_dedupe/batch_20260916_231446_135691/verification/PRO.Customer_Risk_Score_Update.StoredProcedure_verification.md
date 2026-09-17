# Customer Risk Score Update — Verification & Traceability

> Companion artifact to `PRO.Customer_Risk_Score_Update.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_9cfe9a17e845` |
| Raw technical object name (from source) | `Customer_Risk_Score_Update` |

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
| Source Hash | `bf43796fc130f298a4c8afbd753f6ba5118f3523d01e50888df119b8b254ea7d` |
| Configuration Version | `db93bfb59420a471` |
| Run Timestamp | `2026-09-16T23:16:25.403113+00:00` |
| Object ID | `obj_9cfe9a17e845` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_8e6ad139c526` |
| Total LLM Calls | `10` |
| Successful Calls | `10` |
| Failed Calls | `0` |
| Prompt Tokens | `85611` |
| Completion Tokens | `8010` |
| Total Tokens | `93621` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 6425 | available |
| synthesis | 7 | 7 | 0 | 49162 | available |
| synthesis_revision | 2 | 2 | 0 | 38034 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Assign RiskTier [MATCHED] (`rule__3`) | `PRO.CustomerRiskProfile.RiskTier` | Assign a risk tier based on the calculated risk score. |
| 🟠 2 | Insert into #RiskScoreStaging [MATCHED] (`deterministic_statement_03_batch3_nested_block+batch3_main_body:chunk_text_09_customerid`) | `CustomerId, RiskScore, RiskTier` | Not specified |
| 🟠 3 | Insert into RiskScoreAuditLog [MATCHED] (`deterministic_statement_04_batch3_nested_block:chunk_text_02_customerid`) | `CustomerId, ScoreDate, RiskScore, RiskTier` | Not specified |
| 🟠 4 | Upsert riskscorehistory [MATCHED] (`deterministic_statement_04_batch3_nested_block:chunk_text_01:MATCHED_riskscore+upsert`) | `RiskScore, RiskTier, LastScoredDate, CustomerId, FirstScoredDate` | Refresh existing rows and insert rows not already present. |
| 🟠 5 | Determine RecommendedLimitAdjustmentPct [MATCHED] (`deterministic_tsql_if_0058_0077_recommendedlimitadjustmentpct`) | `RecommendedLimitAdjustmentPct` | Not specified |
| 🟠 6 | Determine RecommendedLimitAdjustmentPct [MATCHED] (`deterministic_decision_2205_2686_0_recommendedlimitadjustmentpct`) | `RecommendedLimitAdjustmentPct` | Not specified |
| 🟠 7 | Check process date against review cycle start [UNRESOLVED] (`rule__1__6`) | `Not specified` | If the process date is on or after the review cycle start date, proceed with the risk score update. |
| 🟠 8 | Merge risk score history [LLM_ONLY] (`rule__1__9`) | `RiskScore, RiskTier, LastScoredDate` | Merge the risk score and risk tier data from the #RiskScoreStaging table into the PRO.RiskScoreHistory table. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Assign RiskTier (rule__3) | UPDATE C SET PRO.CustomerRiskProfile.RiskTier = ( CASE WHEN PRO.CustomerRiskProfile.RiskScore < 20 THEN 'LOW' WHEN PRO.CustomerRiskProfile.RiskScore < 50 THEN 'MODERATE' WHEN PRO.CustomerRiskProfile.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END ) FROM PRO.Cust… | Not cited | 00_batch3_main_body | dependency_0008; dependency_0009 | Needs Review |
| 2 | Insert into #RiskScoreStaging (deterministic_statement_03_batch3_nested_block+batch3_main_body:chunk_text_09_customerid) | Not cited | source | 03_batch3_nested_block+batch3_main_body | Not cited | Verified |
| 3 | Insert into RiskScoreAuditLog (deterministic_statement_04_batch3_nested_block:chunk_text_02_customerid) | Not cited | source | 04_batch3_nested_block | Not cited | Verified |
| 4 | Upsert riskscorehistory (deterministic_statement_04_batch3_nested_block:chunk_text_01:MATCHED_riskscore+upsert) | Not cited | source | 04_batch3_nested_block | Not cited | Verified |
| 5 | Determine RecommendedLimitAdjustmentPct (deterministic_tsql_if_0058_0077_recommendedlimitadjustmentpct) | Not cited | source \| Lines 58-77 | Not cited | Not cited | Verified |
| 6 | Determine RecommendedLimitAdjustmentPct (deterministic_decision_2205_2686_0_recommendedlimitadjustmentpct) | Not cited | source \| Lines 60-71 | Not cited | Not cited | Verified |
| 7 | Check process date against review cycle start (rule__1__6) | IF @ProcessDate >= @ReviewCycleStart | Not cited | Not cited | Not cited | Needs Review |
| 8 | Merge risk score history (rule__1__9) | MERGE PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON PRO.RiskScoreHistory.CustomerId = #RiskScoreStaging.CustomerId | Not cited | Not cited | Not cited | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0046_0051_1660:branch_001 | PRO.CustomerRiskProfile.RiskScore < 20 | source \| Lines 47-48 \| Statement 00_batch3_main_body:chunk_text_08 |
| case_0046_0051_1660:branch_002 | PRO.CustomerRiskProfile.RiskScore < 50 | source \| Lines 48-49 \| Statement 00_batch3_main_body:chunk_text_08 |
| case_0046_0051_1660:branch_003 | PRO.CustomerRiskProfile.RiskScore < 80 | source \| Lines 49-50 \| Statement 00_batch3_main_body:chunk_text_08 |
| case_0046_0051_1660:branch_004 | ELSE | source \| Lines 50-51 \| Statement 00_batch3_main_body:chunk_text_08 |
| tsql_if_0058_0077:branch_001 | @ProcessDate >= @ReviewCycleStart | samples/12_Customer_Risk_Score_Update.sql \| Lines 59-71 \| Chunk 02_batch3_nested_block |
| tsql_if_0058_0077:branch_002 | ELSE | source \| Lines 73-77 |
| decision_2205_2686_0:branch_001 | (PRO.CustomerRiskProfile.RiskTier = 'LOW') AND (COALESCE(PRO.CustomerRiskProfile.PriorDefaultCount, 0) = 0) | samples/12_Customer_Risk_Score_Update.sql \| Lines 60-71 \| Chunk 02_batch3_nested_block |
| decision_2205_2686_0:branch_002 | PRO.CustomerRiskProfile.RiskTier = 'LOW' | samples/12_Customer_Risk_Score_Update.sql \| Lines 60-71 \| Chunk 02_batch3_nested_block |
| decision_2205_2686_0:branch_003 | PRO.CustomerRiskProfile.RiskTier = 'MODERATE' | samples/12_Customer_Risk_Score_Update.sql \| Lines 60-71 \| Chunk 02_batch3_nested_block |
| decision_2205_2686_0:branch_004 | PRO.CustomerRiskProfile.RiskTier = 'HIGH' | samples/12_Customer_Risk_Score_Update.sql \| Lines 60-71 \| Chunk 02_batch3_nested_block |
| decision_2205_2686_0:branch_005 | PRO.CustomerRiskProfile.RiskTier = 'SEVERE' | samples/12_Customer_Risk_Score_Update.sql \| Lines 60-71 \| Chunk 02_batch3_nested_block |
| decision_2205_2686_0:branch_006 | ELSE | samples/12_Customer_Risk_Score_Update.sql \| Lines 60-71 \| Chunk 02_batch3_nested_block |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 96
- **Disposition:** covered_by_rule=68, technical_only=2, uncovered=26

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | covered_by_rule | Lines 1-5 | 00_batch3_main_body:chunk_text_01, 00_batch3_main_body | USE [DEMO_MISDB] SET ANSI_NULLS ON SET QUOTED_IDENTIFIER ON |
| STATEMENT | covered_by_rule | Lines 7-8 | 00_batch3_main_body:chunk_text_02, 00_batch3_main_body | BEGIN SET NOCOUNT ON |
| STATEMENT | covered_by_rule | Lines 11-11 | 00_batch3_main_body:chunk_text_03, 00_batch3_main_body | BEGIN TRY |
| SELECT | covered_by_rule | Lines 15-15 | 00_batch3_main_body:chunk_text_04, 00_batch3_main_body | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| STATEMENT | covered_by_rule | Lines 18-21 | 00_batch3_main_body:chunk_text_05, 00_batch3_main_body | DECLARE @ReviewCycleStart DATE = DATEADD(MONTH, -1, @ProcessDate) -- Rule 1: utilization ratio is only computed where a credit limit -- is on record and positive |
| UPDATE | covered_by_rule | Lines 24-31 | 00_batch3_main_body:chunk_text_06, 00_batch3_main_body | UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 -- Rule 2: composite score combines overdue days, utilization, and -- prior defaults... |
| UPDATE | covered_by_rule | Lines 34-41 | 00_batch3_main_body:chunk_text_07, 00_batch3_main_body | UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C -- Rule 3: multi-branch risk tier derived from the com... |
| UPDATE | covered_by_rule | Lines 44-57 | 00_batch3_main_body:chunk_text_08, 00_batch3_main_body | UPDATE C SET C.RiskTier = ( CASE WHEN C.RiskScore < 20 THEN 'LOW' WHEN C.RiskScore < 50 THEN 'MODERATE' WHEN C.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END ) FROM PRO.CustomerRiskProfile C -- Rule 4: sequential IF/ELSE, nested inside - w... |
| UPDATE | covered_by_rule | Lines 24-31 | 00_batch3_main_body:embedded_01_09, 00_batch3_main_body | UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 -- Rule 2: composite score combines overdue days, utilization, and -- prior defaults... |
| UPDATE | covered_by_rule | Lines 34-41 | 00_batch3_main_body:embedded_02_10, 00_batch3_main_body | UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C -- Rule 3: multi-branch risk tier derived from the com... |
| UPDATE | covered_by_rule | Lines 44-57 | 00_batch3_main_body:embedded_03_11, 00_batch3_main_body | UPDATE C SET C.RiskTier = ( CASE WHEN C.RiskScore < 20 THEN 'LOW' WHEN C.RiskScore < 50 THEN 'MODERATE' WHEN C.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END ) FROM PRO.CustomerRiskProfile C -- Rule 4: sequential IF/ELSE, nested inside - w... |
| STATEMENT | covered_by_rule | Lines 1-1 | 01_batch3_main_body+batch3_nested_block:chunk_text_01, 01_batch3_main_body+batch3_nested_block | IF @ProcessDate >= @ReviewCycleStart |
| STATEMENT | uncovered | Lines 3-3 | 01_batch3_main_body+batch3_nested_block:chunk_text_02, 01_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | uncovered | Lines 1-11 | 02_batch3_nested_block:chunk_text_01, 02_batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEV... |
| UPDATE | uncovered | Lines 1-11 | 02_batch3_nested_block:embedded_01_02, 02_batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEV... |
| STATEMENT | covered_by_rule | Lines 1-1 | 03_batch3_nested_block+batch3_main_body:chunk_text_01, 03_batch3_nested_block+batch3_main_body | END |
| STATEMENT | covered_by_rule | Lines 3-3 | 03_batch3_nested_block+batch3_main_body:chunk_text_02, 03_batch3_nested_block+batch3_main_body | ELSE |
| STATEMENT | covered_by_rule | Lines 5-5 | 03_batch3_nested_block+batch3_main_body:chunk_text_03, 03_batch3_nested_block+batch3_main_body | BEGIN |
| UPDATE | covered_by_rule | Lines 8-10 | 03_batch3_nested_block+batch3_main_body:chunk_text_04, 03_batch3_nested_block+batch3_main_body | UPDATE C SET C.RecommendedLimitAdjustmentPct = 0 FROM PRO.CustomerRiskProfile C |
| STATEMENT | covered_by_rule | Lines 1-1 | 03_batch3_nested_block+batch3_main_body:chunk_text_05, 03_batch3_nested_block+batch3_main_body | END |
| STATEMENT | covered_by_rule | Lines 17-17 | 03_batch3_nested_block+batch3_main_body:chunk_text_06, 03_batch3_nested_block+batch3_main_body | IF OBJECT_ID('tempdb..#RiskScoreStaging') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 20-20 | 03_batch3_nested_block+batch3_main_body:chunk_text_07, 03_batch3_nested_block+batch3_main_body | DROP TABLE #RiskScoreStaging |
| INSERT | covered_by_rule | Lines 24-32 | 03_batch3_nested_block+batch3_main_body:chunk_text_08, 03_batch3_nested_block+batch3_main_body | CREATE TABLE #RiskScoreStaging ( CustomerId VARCHAR(20), RiskScore DECIMAL(9,2), RiskTier VARCHAR(10) ) -- Rule 5: conditional INSERT - only customers with a computed -- score this cycle are staged |
| INSERT | covered_by_rule | Lines 35-42 | 03_batch3_nested_block+batch3_main_body:chunk_text_09, 03_batch3_nested_block+batch3_main_body | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| UPDATE | covered_by_rule | Lines 8-10 | 03_batch3_nested_block+batch3_main_body:embedded_01_10, 03_batch3_nested_block+batch3_main_body | UPDATE C SET C.RecommendedLimitAdjustmentPct = 0 FROM PRO.CustomerRiskProfile C |
| INSERT | covered_by_rule | Lines 35-42 | 03_batch3_nested_block+batch3_main_body:embedded_02_11, 03_batch3_nested_block+batch3_main_body | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| MERGE | covered_by_rule | Lines 1-14 | 04_batch3_nested_block:chunk_text_01, 04_batch3_nested_block | MERGE PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate =... |
| INSERT | covered_by_rule | Lines 17-21 | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| MERGE | covered_by_rule | Lines 1-14 | 04_batch3_nested_block:embedded_01_03, 04_batch3_nested_block | MERGE PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate =... |
| INSERT | covered_by_rule | Lines 17-21 | 04_batch3_nested_block:embedded_02_04, 04_batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| UPDATE | uncovered | Lines 1-3 | 05_batch3_nested_block:chunk_text_01, 05_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| STATEMENT | uncovered | Lines 7-7 | 05_batch3_nested_block:chunk_text_02, 05_batch3_nested_block | END TRY |
| STATEMENT | uncovered | Lines 10-11 | 05_batch3_nested_block:chunk_text_03, 05_batch3_nested_block | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 14-16 | 05_batch3_nested_block:chunk_text_04, 05_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| STATEMENT | uncovered | Lines 19-19 | 05_batch3_nested_block:chunk_text_05, 05_batch3_nested_block | END CATCH |
| SET | uncovered | Lines 22-22 | 05_batch3_nested_block:chunk_text_06, 05_batch3_nested_block | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 7-7 | 05_batch3_nested_block:chunk_text_07, 05_batch3_nested_block | END |
| UPDATE | uncovered | Lines 1-3 | 05_batch3_nested_block:embedded_01_08, 05_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| UPDATE | uncovered | Lines 14-16 | 05_batch3_nested_block:embedded_02_09, 05_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| SET | uncovered | Lines 22-22 | 05_batch3_nested_block:embedded_03_10, 05_batch3_nested_block | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 00_batch3_main_body:chunk_text_04, 00_batch3_main_body:chunk_text_04, 00_batch3_main_body | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 00_batch3_main_body:chunk_text_06, 00_batch3_main_body:chunk_text_06, 00_batch3_main_body | UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 -- Rule 2: composite score combines overdue days, utilization, and -- prior defaults... |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 00_batch3_main_body:chunk_text_07, 00_batch3_main_body:chunk_text_07, 00_batch3_main_body | UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C -- Rule 3: multi-branch risk tier derived from the com... |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 00_batch3_main_body:chunk_text_08, 00_batch3_main_body:chunk_text_08, 00_batch3_main_body | UPDATE C SET C.RiskTier = ( CASE WHEN C.RiskScore < 20 THEN 'LOW' WHEN C.RiskScore < 50 THEN 'MODERATE' WHEN C.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END ) FROM PRO.CustomerRiskProfile C -- Rule 4: sequential IF/ELSE, nested inside - w... |
| UPDATE | covered_by_rule | unavailable | 00_batch3_main_body:embedded_01_09, 00_batch3_main_body:embedded_01_09, 00_batch3_main_body | UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 -- Rule 2: composite score combines overdue days, utilization, and -- prior defaults... |
| UPDATE | covered_by_rule | unavailable | 00_batch3_main_body:embedded_02_10, 00_batch3_main_body:embedded_02_10, 00_batch3_main_body | UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C -- Rule 3: multi-branch risk tier derived from the com... |
| UPDATE | covered_by_rule | unavailable | 00_batch3_main_body:embedded_03_11, 00_batch3_main_body:embedded_03_11, 00_batch3_main_body | UPDATE C SET C.RiskTier = ( CASE WHEN C.RiskScore < 20 THEN 'LOW' WHEN C.RiskScore < 50 THEN 'MODERATE' WHEN C.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END ) FROM PRO.CustomerRiskProfile C -- Rule 4: sequential IF/ELSE, nested inside - w... |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql / Lines 60-70 | 02_batch3_nested_block:chunk_text_01, 02_batch3_nested_block:chunk_text_01, 02_batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEV... |
| UPDATE | uncovered | unavailable | 02_batch3_nested_block:embedded_01_02, 02_batch3_nested_block:embedded_01_02, 02_batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEV... |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_nested_block+batch3_main_body:chunk_text_04, 03_batch3_nested_block+batch3_main_body:chunk_text_04, 03_batch3_nested_block+batch3_main_body | UPDATE C SET C.RecommendedLimitAdjustmentPct = 0 FROM PRO.CustomerRiskProfile C |
| INSERT_TEMP | technical_only | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_nested_block+batch3_main_body:chunk_text_09, 03_batch3_nested_block+batch3_main_body:chunk_text_09, 03_batch3_nested_block+batch3_main_body | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_nested_block+batch3_main_body:embedded_01_10, 03_batch3_nested_block+batch3_main_body:embedded_01_10, 03_batch3_nested_block+batch3_main_body | UPDATE C SET C.RecommendedLimitAdjustmentPct = 0 FROM PRO.CustomerRiskProfile C |
| READ | covered_by_rule | unavailable | 03_batch3_nested_block+batch3_main_body:embedded_02_11, 03_batch3_nested_block+batch3_main_body:embedded_02_11, 03_batch3_nested_block+batch3_main_body | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_nested_block+batch3_main_body:embedded_02_11, 03_batch3_nested_block+batch3_main_body:embedded_02_11, 03_batch3_nested_block+batch3_main_body | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| MERGE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 04_batch3_nested_block:chunk_text_01, 04_batch3_nested_block:chunk_text_01, 04_batch3_nested_block | MERGE PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate =... |
| INSERT | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_02_04, 04_batch3_nested_block:embedded_02_04, 04_batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| INSERT | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_02_04, 04_batch3_nested_block:embedded_02_04, 04_batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| UPDATE | uncovered | samples/12_Customer_Risk_Score_Update.sql | 05_batch3_nested_block:chunk_text_01, 05_batch3_nested_block:chunk_text_01, 05_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| UPDATE | uncovered | samples/12_Customer_Risk_Score_Update.sql | 05_batch3_nested_block:chunk_text_04, 05_batch3_nested_block:chunk_text_04, 05_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| UPDATE | uncovered | unavailable | 05_batch3_nested_block:embedded_01_08, 05_batch3_nested_block:embedded_01_08, 05_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| UPDATE | uncovered | unavailable | 05_batch3_nested_block:embedded_02_09, 05_batch3_nested_block:embedded_02_09, 05_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| CASE | covered_by_rule | Lines 47-48 | 00_batch3_main_body:chunk_text_08 | PRO.CustomerRiskProfile.RiskScore < 20 |
| CASE | covered_by_rule | Lines 48-49 | 00_batch3_main_body:chunk_text_08 | PRO.CustomerRiskProfile.RiskScore < 50 |
| CASE | covered_by_rule | Lines 49-50 | 00_batch3_main_body:chunk_text_08 | PRO.CustomerRiskProfile.RiskScore < 80 |
| ELSE | covered_by_rule | Lines 50-51 | 00_batch3_main_body:chunk_text_08 | ELSE |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql / Lines 59-71 | 02_batch3_nested_block | @ProcessDate >= @ReviewCycleStart |
| ELSE | covered_by_rule | Lines 73-77 | unavailable | ELSE |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql / Lines 60-71 | 02_batch3_nested_block | (PRO.CustomerRiskProfile.RiskTier = 'LOW') AND (COALESCE(PRO.CustomerRiskProfile.PriorDefaultCount, 0) = 0) |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql / Lines 60-71 | 02_batch3_nested_block | PRO.CustomerRiskProfile.RiskTier = 'LOW' |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql / Lines 60-71 | 02_batch3_nested_block | PRO.CustomerRiskProfile.RiskTier = 'MODERATE' |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql / Lines 60-71 | 02_batch3_nested_block | PRO.CustomerRiskProfile.RiskTier = 'HIGH' |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql / Lines 60-71 | 02_batch3_nested_block | PRO.CustomerRiskProfile.RiskTier = 'SEVERE' |
| ELSE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql / Lines 60-71 | 02_batch3_nested_block | ELSE |
| CALCULATION | uncovered | Lines 29-29 | unavailable | SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit |
| CASE | covered_by_rule | Lines 46-46 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 47-47 | unavailable | WHEN C.RiskScore < 20 THEN |
| CASE_BRANCH | uncovered | Lines 48-48 | unavailable | WHEN C.RiskScore < 50 THEN |
| CASE_BRANCH | uncovered | Lines 49-49 | unavailable | WHEN C.RiskScore < 80 THEN |
| ELSE | covered_by_rule | Lines 50-50 | unavailable | ELSE |
| IF | covered_by_rule | Lines 58-58 | unavailable | IF @ProcessDate >= @ReviewCycleStart |
| CASE | covered_by_rule | Lines 62-62 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 63-63 | unavailable | WHEN C.RiskTier = THEN |
| CASE | covered_by_rule | Lines 64-64 | unavailable | CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END |
| CASE_BRANCH | covered_by_rule | Lines 64-64 | unavailable | CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END |
| ELSE | covered_by_rule | Lines 64-64 | unavailable | CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END |
| CASE_BRANCH | covered_by_rule | Lines 65-65 | unavailable | WHEN C.RiskTier = THEN 0 |
| CASE_BRANCH | covered_by_rule | Lines 66-66 | unavailable | WHEN C.RiskTier = THEN -15 |
| CASE_BRANCH | covered_by_rule | Lines 67-67 | unavailable | WHEN C.RiskTier = THEN -40 |
| ELSE | covered_by_rule | Lines 68-68 | unavailable | ELSE 0 |
| ELSE | covered_by_rule | Lines 72-72 | unavailable | ELSE |
| IF | uncovered | Lines 79-79 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE_BRANCH | uncovered | Lines 102-102 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | uncovered | Lines 107-107 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CATCH | uncovered | Lines 124-124 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 129-129 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| later_update_overrides_field | 02_batch3_nested_block:embedded_01_02 / PRO.CustomerRiskProfile | 03_batch3_nested_block+batch3_main_body:embedded_01_10 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 02_batch3_nested_block:embedded_01_02 / PRO.CustomerRiskProfile | 03_batch3_nested_block+batch3_main_body:embedded_02_11 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 02_batch3_nested_block:embedded_01_02 / PRO.CustomerRiskProfile | 04_batch3_nested_block:embedded_02_04 / PRO.CustomerRiskProfile | high |
| later_update_overrides_field | 02_batch3_nested_block:embedded_01_02 / PRO.CustomerRiskProfile | 02_batch3_nested_block:chunk_text_01 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_nested_block+batch3_main_body:embedded_01_10 / PRO.CustomerRiskProfile | 03_batch3_nested_block+batch3_main_body:embedded_02_11 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_nested_block+batch3_main_body:embedded_01_10 / PRO.CustomerRiskProfile | 04_batch3_nested_block:embedded_02_04 / PRO.CustomerRiskProfile | high |
| later_update_overrides_field | 03_batch3_nested_block+batch3_main_body:embedded_01_10 / PRO.CustomerRiskProfile | 02_batch3_nested_block:chunk_text_01 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 00_batch3_main_body:embedded_01_09 / PRO.CustomerRiskProfile | 03_batch3_nested_block+batch3_main_body:embedded_02_11 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 00_batch3_main_body:embedded_01_09 / PRO.CustomerRiskProfile | 04_batch3_nested_block:embedded_02_04 / PRO.CustomerRiskProfile | high |

Unresolved dependency candidates: 38. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 8
- **By rule type:** deterministic_decision_table = 5, explicit = 3
- **By validation status:** MATCHED = 1, unverified = 2, verified = 5

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 13
- **Deterministic-only facts:** 6
- **LLM-only claims:** 2
- **Conflicts:** 6
- **Unresolved items:** 1
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_000ad3f48c41`): full_source
- `CONFLICT` tables_written (`recon_000ad3f48c41`): full_source
- `LLM_ONLY` tables_written (`recon_bb51153dedb8`): full_source
- `CONFLICT` tables_written (`recon_000ad3f48c41`): full_source
- `CONFLICT` rule (`recon_2fe567305582`): rule__1, 00_batch3_main_body, 00_batch3_main_body:chunk_text_04;00_batch3_main_body:chunk_text_06;00_batch3_main_body:chunk_text_07;00_batch3_main_body:chunk_text_08;00_batch3_main_body:embedded_01_09;00_batch3_main_body:embedded_02_10;00_batch3_main_body:embedded_03_11 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 77.3/100
- **Statement coverage:** 22 / 40 (55.0%)
- **Rule grounding coverage:** 4 / 10 (40.0%)
- **Decision-chain coverage:** 12 / 12 branches (100.0%)
- **Conflicts:** 6
- **Contradictions:** 6
- **Review required items:** 15
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule__1`: Synthesized rule affects different fields than the deterministic evidence.
- `MEDIUM` Field Conflict on `rule__3`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Condition Conflict on `rule__3`: Synthesized condition conflicts with deterministic predicate evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: IF @ProcessDate >= @ReviewCycleStart
- Synthesized in 7 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
