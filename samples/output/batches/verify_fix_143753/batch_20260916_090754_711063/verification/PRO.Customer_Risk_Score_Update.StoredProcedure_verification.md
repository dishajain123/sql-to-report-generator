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
| Prompt Version | `3fde9e2078dcda12` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `bf43796fc130f298a4c8afbd753f6ba5118f3523d01e50888df119b8b254ea7d` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:07:54.745996+00:00` |
| Object ID | `obj_9cfe9a17e845` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_dc0d43797baa` |
| Total LLM Calls | `10` |
| Successful Calls | `10` |
| Failed Calls | `0` |
| Prompt Tokens | `140094` |
| Completion Tokens | `27032` |
| Total Tokens | `167126` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 7231 | available |
| synthesis | 7 | 7 | 0 | 93744 | available |
| synthesis_revision | 2 | 2 | 0 | 66151 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| ⚠️ 1 | Calculate UtilizationRatio [MATCHED] (`rule__1`) | `UtilizationRatio` | Determine the utilization ratio for customers with a non-null and positive credit limit. |
| ⚠️ 2 | Calculate RiskScore [MATCHED] (`rule__2`) | `RiskScore` | Determine the risk score for customers based on their overdue days, utilization ratio, and prior defaults. |
| ⚠️ 3 | Determine RiskTier [CONFLICT] (`rule__3`) | `RiskTier` | Assign a risk tier to a customer based on their risk score. |
| ⚠️ 4 | Calculate RecommendedLimitAdjustmentPct [CONFLICT] (`rule__4`) | `RecommendedLimitAdjustmentPct` | Determine the recommended limit adjustment percentage for customers based on their risk tier and prior default count. |
| ⚠️ 5 | Merge Updated Risk Scores and Tiers into History [MATCHED] (`rule__6`) | `CustomerId, RiskScore, RiskTier, LastScoredDate, FirstScoredDate` | Merge the staged risk scores and tiers into the risk score history. |
| ⚠️ 6 | Log Updated Risk Scores and Tiers for Audit [MATCHED] (`rule__7`) | `CustomerId, ScoreDate, RiskScore, RiskTier` | Log the updated risk scores and tiers for audit purposes. |
| ⚠️ 7 | Stage Updated Risk Scores and Tiers [MATCHED] (`rule__5`) | `CustomerId, RiskScore, RiskTier` | Stage the updated risk scores and tiers for customers. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Calculate UtilizationRatio (rule__1) | UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_01_29 | dependency_0001; dependency_0002 | Verified |
| 2 | Calculate RiskScore (rule__2) | UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_02_30 | dependency_0003; dependency_0004 | Verified |
| 3 | Determine RiskTier (rule__3) | UPDATE C SET C.RiskTier = CASE WHEN C.RiskScore < 20 THEN 'LOW' WHEN C.RiskScore < 50 THEN 'MODERATE' WHEN C.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END FROM PRO.CustomerRiskProfile C WHERE C.RiskScore IS NOT NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_03_31 | dependency_0005; dependency_0006 | Needs Review |
| 4 | Calculate RecommendedLimitAdjustmentPct (rule__4) | UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEVERE' THEN -40 ELSE 0 E… | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_04_32 | dependency_0007; dependency_0008 | Needs Review |
| 5 | Merge Updated Risk Scores and Tiers into History (rule__6) | MERGE PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate = @ProcessDate WHEN NOT… | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_08_36 | dependency_0010; dependency_0011 | Verified |
| 6 | Log Updated Risk Scores and Tiers for Audit (rule__7) | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL | Not cited | 03_batch3_main_body+batch3_nested_block:embedded_06_34 | dependency_0009 | Verified |
| 7 | Stage Updated Risk Scores and Tiers (rule__5) | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL | Not cited | Not cited | dependency_0009 | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0046_0051_1660:branch_001 | C.RiskScore < 20 | source \| Lines 47-48 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_10 |
| case_0046_0051_1660:branch_002 | C.RiskScore < 50 | source \| Lines 48-49 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_10 |
| case_0046_0051_1660:branch_003 | C.RiskScore < 80 | source \| Lines 49-50 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_10 |
| case_0046_0051_1660:branch_004 | ELSE | source \| Lines 50-51 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_10 |
| decision_2205_2686_0:branch_001 | (C.RiskTier = 'LOW') AND (COALESCE(C.PriorDefaultCount, 0) = 0) | source \| Lines 60-71 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_16 |
| decision_2205_2686_0:branch_002 | C.RiskTier = 'LOW' | source \| Lines 60-71 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_16 |
| decision_2205_2686_0:branch_003 | C.RiskTier = 'MODERATE' | source \| Lines 60-71 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_16 |
| decision_2205_2686_0:branch_004 | C.RiskTier = 'HIGH' | source \| Lines 60-71 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_16 |
| decision_2205_2686_0:branch_005 | C.RiskTier = 'SEVERE' | source \| Lines 60-71 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_16 |
| decision_2205_2686_0:branch_006 | ELSE | source \| Lines 60-71 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_16 |
| decision_chain_003:branch_001 | C.RiskScore < 20 | source |
| decision_chain_003:branch_002 | C.RiskScore < 50 | source |
| decision_chain_003:branch_003 | C.RiskScore < 80 | source |
| decision_chain_003:branch_004 | ELSE | source |
| decision_chain_003:branch_005 | C.RiskTier = 'LOW' | source |
| decision_chain_003:branch_006 | C.RiskTier = 'MODERATE' | source |
| decision_chain_003:branch_007 | C.RiskTier = 'HIGH' | source |
| decision_chain_003:branch_008 | C.RiskTier = 'SEVERE' | source |
| decision_chain_003:branch_009 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 107
- **Disposition:** covered_by_rule=92, technical_only=2, uncovered=13

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
| STATEMENT | covered_by_rule | Lines 7-10 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @ReviewCycleStart DATE = DATEADD(MONTH, -1, @ProcessDate) -- Rule 1: utilization ratio is only computed where a credit limit -- is on record and positive |
| UPDATE | covered_by_rule | Lines 11-18 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 -- Rule 2: composite score combines overdue days, utilization, and -- prior defaults... |
| UPDATE | covered_by_rule | Lines 19-26 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C -- Rule 3: multi-branch risk tier derived from the com... |
| UPDATE | covered_by_rule | Lines 27-40 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RiskTier = ( CASE WHEN C.RiskScore < 20 THEN 'LOW' WHEN C.RiskScore < 50 THEN 'MODERATE' WHEN C.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END ) FROM PRO.CustomerRiskProfile C -- Rule 4: sequential IF/ELSE, nested inside - w... |
| STATEMENT | covered_by_rule | Lines 41-41 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | IF @ProcessDate >= @ReviewCycleStart |
| STATEMENT | covered_by_rule | Lines 1-1 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 43-53 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEV... |
| STATEMENT | covered_by_rule | Lines 34-34 | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 33-33 | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | ELSE |
| STATEMENT | covered_by_rule | Lines 1-1 | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 57-59 | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = 0 FROM PRO.CustomerRiskProfile C |
| STATEMENT | covered_by_rule | Lines 34-34 | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 62-62 | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | IF OBJECT_ID('tempdb..#RiskScoreStaging') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 63-63 | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | DROP TABLE #RiskScoreStaging |
| INSERT | covered_by_rule | Lines 65-73 | 03_batch3_main_body+batch3_nested_block:chunk_text_18, 03_batch3_main_body+batch3_nested_block | CREATE TABLE #RiskScoreStaging ( CustomerId VARCHAR(20), RiskScore DECIMAL(9,2), RiskTier VARCHAR(10) ) -- Rule 5: conditional INSERT - only customers with a computed -- score this cycle are staged |
| INSERT | covered_by_rule | Lines 74-81 | 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| MERGE | covered_by_rule | Lines 82-95 | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | MERGE PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate =... |
| INSERT | covered_by_rule | Lines 96-100 | 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| UPDATE | covered_by_rule | Lines 102-104 | 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| STATEMENT | covered_by_rule | Lines 106-106 | 03_batch3_main_body+batch3_nested_block:chunk_text_23, 03_batch3_main_body+batch3_nested_block | END TRY |
| STATEMENT | covered_by_rule | Lines 107-108 | 03_batch3_main_body+batch3_nested_block:chunk_text_24, 03_batch3_main_body+batch3_nested_block | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | covered_by_rule | Lines 109-111 | 03_batch3_main_body+batch3_nested_block:chunk_text_25, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| STATEMENT | covered_by_rule | Lines 112-112 | 03_batch3_main_body+batch3_nested_block:chunk_text_26, 03_batch3_main_body+batch3_nested_block | END CATCH |
| SET | covered_by_rule | Lines 113-113 | 03_batch3_main_body+batch3_nested_block:chunk_text_27, 03_batch3_main_body+batch3_nested_block | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 34-34 | 03_batch3_main_body+batch3_nested_block:chunk_text_28, 03_batch3_main_body+batch3_nested_block | END |
| UPDATE | covered_by_rule | Lines 11-18 | 03_batch3_main_body+batch3_nested_block:embedded_01_29, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 -- Rule 2: composite score combines overdue days, utilization, and -- prior defaults... |
| UPDATE | covered_by_rule | Lines 19-26 | 03_batch3_main_body+batch3_nested_block:embedded_02_30, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C -- Rule 3: multi-branch risk tier derived from the com... |
| UPDATE | covered_by_rule | Lines 27-40 | 03_batch3_main_body+batch3_nested_block:embedded_03_31, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RiskTier = ( CASE WHEN C.RiskScore < 20 THEN 'LOW' WHEN C.RiskScore < 50 THEN 'MODERATE' WHEN C.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END ) FROM PRO.CustomerRiskProfile C -- Rule 4: sequential IF/ELSE, nested inside - w... |
| UPDATE | covered_by_rule | Lines 43-53 | 03_batch3_main_body+batch3_nested_block:embedded_04_32, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEV... |
| UPDATE | covered_by_rule | Lines 57-59 | 03_batch3_main_body+batch3_nested_block:embedded_05_33, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = 0 FROM PRO.CustomerRiskProfile C |
| INSERT | covered_by_rule | Lines 74-81 | 03_batch3_main_body+batch3_nested_block:embedded_06_34, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| MERGE | covered_by_rule | Lines 82-95 | 03_batch3_main_body+batch3_nested_block:embedded_07_35, 03_batch3_main_body+batch3_nested_block | MERGE PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate =... |
| INSERT | covered_by_rule | Lines 96-100 | 03_batch3_main_body+batch3_nested_block:embedded_08_36, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| UPDATE | covered_by_rule | Lines 102-104 | 03_batch3_main_body+batch3_nested_block:embedded_09_37, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| UPDATE | covered_by_rule | Lines 109-111 | 03_batch3_main_body+batch3_nested_block:embedded_10_38, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| SET | covered_by_rule | Lines 113-113 | 03_batch3_main_body+batch3_nested_block:embedded_11_39, 03_batch3_main_body+batch3_nested_block | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 -- Rule 2: composite score combines overdue days, utilization, and -- prior defaults... |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C -- Rule 3: multi-branch risk tier derived from the com... |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RiskTier = ( CASE WHEN C.RiskScore < 20 THEN 'LOW' WHEN C.RiskScore < 50 THEN 'MODERATE' WHEN C.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END ) FROM PRO.CustomerRiskProfile C -- Rule 4: sequential IF/ELSE, nested inside - w... |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEV... |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = 0 FROM PRO.CustomerRiskProfile C |
| INSERT_TEMP | technical_only | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block:chunk_text_19, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| MERGE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block:chunk_text_20, 03_batch3_main_body+batch3_nested_block | MERGE PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate =... |
| INSERT | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block:chunk_text_21, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block:chunk_text_22, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| UPDATE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_25, 03_batch3_main_body+batch3_nested_block:chunk_text_25, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_29, 03_batch3_main_body+batch3_nested_block:embedded_01_29, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0 -- Rule 2: composite score combines overdue days, utilization, and -- prior defaults... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_30, 03_batch3_main_body+batch3_nested_block:embedded_02_30, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C -- Rule 3: multi-branch risk tier derived from the com... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_31, 03_batch3_main_body+batch3_nested_block:embedded_03_31, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RiskTier = ( CASE WHEN C.RiskScore < 20 THEN 'LOW' WHEN C.RiskScore < 50 THEN 'MODERATE' WHEN C.RiskScore < 80 THEN 'HIGH' ELSE 'SEVERE' END ) FROM PRO.CustomerRiskProfile C -- Rule 4: sequential IF/ELSE, nested inside - w... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_32, 03_batch3_main_body+batch3_nested_block:embedded_04_32, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEV... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_33, 03_batch3_main_body+batch3_nested_block:embedded_05_33, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.RecommendedLimitAdjustmentPct = 0 FROM PRO.CustomerRiskProfile C |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_34, 03_batch3_main_body+batch3_nested_block:embedded_06_34, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| INSERT_TEMP | technical_only | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_34, 03_batch3_main_body+batch3_nested_block:embedded_06_34, 03_batch3_main_body+batch3_nested_block | INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE RiskScore IS NOT NULL -- Rule 6: upsert the staged score into the history table - -- refresh custom... |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_36, 03_batch3_main_body+batch3_nested_block:embedded_08_36, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_08_36, 03_batch3_main_body+batch3_nested_block:embedded_08_36, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE PrevRiskScore IS NULL AND RiskScore IS NOT NULL |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_09_37, 03_batch3_main_body+batch3_nested_block:embedded_09_37, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_10_38, 03_batch3_main_body+batch3_nested_block:embedded_10_38, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Customer_Risk_Score_Update' |
| CASE | covered_by_rule | Lines 47-48 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | C.RiskScore < 20 |
| CASE | covered_by_rule | Lines 48-49 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | C.RiskScore < 50 |
| CASE | covered_by_rule | Lines 49-50 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | C.RiskScore < 80 |
| ELSE | covered_by_rule | Lines 50-51 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | ELSE |
| IF_BRANCH | covered_by_rule | Lines 60-71 | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | (C.RiskTier = 'LOW') AND (COALESCE(C.PriorDefaultCount, 0) = 0) |
| IF_BRANCH | covered_by_rule | Lines 60-71 | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | C.RiskTier = 'LOW' |
| IF_BRANCH | covered_by_rule | Lines 60-71 | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | C.RiskTier = 'MODERATE' |
| IF_BRANCH | covered_by_rule | Lines 60-71 | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | C.RiskTier = 'HIGH' |
| IF_BRANCH | covered_by_rule | Lines 60-71 | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | C.RiskTier = 'SEVERE' |
| ELSE | covered_by_rule | Lines 60-71 | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | ELSE |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | full_source | C.RiskScore < 20 |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | full_source | C.RiskScore < 50 |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | full_source | C.RiskScore < 80 |
| ELSE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | full_source | C.RiskTier = 'LOW' |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | full_source | C.RiskTier = 'MODERATE' |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | full_source | C.RiskTier = 'HIGH' |
| IF_BRANCH | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | full_source | C.RiskTier = 'SEVERE' |
| ELSE | covered_by_rule | samples/12_Customer_Risk_Score_Update.sql | full_source | ELSE |
| CALCULATION | covered_by_rule | Lines 29-29 | unavailable | SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit |
| CASE | covered_by_rule | Lines 46-46 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 47-47 | unavailable | WHEN C.RiskScore < 20 THEN |
| CASE_BRANCH | covered_by_rule | Lines 48-48 | unavailable | WHEN C.RiskScore < 50 THEN |
| CASE_BRANCH | covered_by_rule | Lines 49-49 | unavailable | WHEN C.RiskScore < 80 THEN |
| ELSE | covered_by_rule | Lines 50-50 | unavailable | ELSE |
| IF | uncovered | Lines 58-58 | unavailable | IF @ProcessDate >= @ReviewCycleStart |
| CASE | covered_by_rule | Lines 62-62 | unavailable | CASE |
| CASE_BRANCH | uncovered | Lines 63-63 | unavailable | WHEN C.RiskTier = THEN |
| CASE | covered_by_rule | Lines 64-64 | unavailable | CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END |
| CASE_BRANCH | covered_by_rule | Lines 64-64 | unavailable | CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END |
| ELSE | covered_by_rule | Lines 64-64 | unavailable | CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END |
| CASE_BRANCH | uncovered | Lines 65-65 | unavailable | WHEN C.RiskTier = THEN 0 |
| CASE_BRANCH | uncovered | Lines 66-66 | unavailable | WHEN C.RiskTier = THEN -15 |
| CASE_BRANCH | uncovered | Lines 67-67 | unavailable | WHEN C.RiskTier = THEN -40 |
| ELSE | covered_by_rule | Lines 68-68 | unavailable | ELSE 0 |
| ELSE | covered_by_rule | Lines 72-72 | unavailable | ELSE |
| IF | uncovered | Lines 79-79 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE_BRANCH | covered_by_rule | Lines 102-102 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | covered_by_rule | Lines 107-107 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CATCH | uncovered | Lines 124-124 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 129-129 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_29 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_06_34 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_29 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_08_36 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_30 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_06_34 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_30 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_08_36 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_03_31 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_06_34 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_03_31 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_08_36 / PRO.CustomerRiskProfile | high |
| later_update_overrides_field | 03_batch3_main_body+batch3_nested_block:embedded_04_32 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_05_33 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_04_32 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_06_34 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_04_32 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_08_36 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_05_33 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_06_34 / PRO.CustomerRiskProfile | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_05_33 / PRO.CustomerRiskProfile | 03_batch3_main_body+batch3_nested_block:embedded_08_36 / PRO.CustomerRiskProfile | high |

Unresolved dependency candidates: 43. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** explicit = 7
- **By validation status:** unverified = 2, verified = 5

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 19
- **Deterministic-only facts:** 0
- **LLM-only claims:** 2
- **Conflicts:** 6
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_000ad3f48c41`): full_source
- `CONFLICT` tables_written (`recon_000ad3f48c41`): full_source
- `CONFLICT` tables_written (`recon_000ad3f48c41`): full_source
- `CONFLICT` tables_written (`recon_000ad3f48c41`): full_source
- `LLM_ONLY` tables_written (`recon_bb51153dedb8`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 88.28571428571429/100
- **Statement coverage:** 26 / 44 (59.1%)
- **Rule grounding coverage:** 7 / 7 (100.0%)
- **Decision-chain coverage:** 10 / 10 branches (100.0%)
- **Conflicts:** 6
- **Contradictions:** 6
- **Review required items:** 14
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `rule__3`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `rule__3`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: C.UtilizationRatio
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: C.RiskScore
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: C.RiskTier
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: C.RecommendedLimitAdjustmentPct
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2) FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RiskTier = CASE WHEN C.RiskScore < 50 THEN 'LOW' WHEN C.RiskScore >= 50 AND C.RiskScore < 100 THEN 'MODERATE' WHEN C.RiskScore >= 100 AND C.RiskScore < 150 THEN 'HIGH' ELSE 'SEVERE' END FROM PRO.CustomerRiskProfile C WHERE C.RiskScore IS NOT NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEVERE' THEN -40 ELSE 0 END FROM PRO.CustomerRiskProfile C WHERE C.RiskTier IN ('LOW', 'MODERATE', 'HIGH', 'SEVERE')
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C
        SET C.RiskTier = (
                CASE
                    WHEN C.RiskScore < 20 THEN 'LOW'
                    WHEN C.RiskScore < 50 THEN 'MODERATE'
                    WHEN C.RiskScore < 80 THEN 'HIGH'
               END
        )
        FROM PRO.CustomerRiskProfile C
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RiskTier = CASE WHEN C.RiskScore <= 30 THEN 'LOW' WHEN C.RiskScore > 30 AND C.RiskScore <= 60 THEN 'MODERATE' WHEN C.RiskScore > 60 AND C.RiskScore <= 90 THEN 'HIGH' ELSE 'SEVERE' END FROM PRO.CustomerRiskProfile C WHERE C.RiskScore IS NOT NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.UtilizationRatio = C.CurrentBalance / C.CreditLimit, C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2), C.RiskTier = CASE WHEN C.RiskScore <= 30 THEN 'LOW' WHEN C.RiskScore > 30 AND C.RiskScore <= 60 THEN 'MODERATE' WHEN C.RiskScore > 60 AND C.RiskScore <= 90 THEN 'HIGH' ELSE 'SEVERE' END, C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEVERE' THEN -40 ELSE 0 END FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO #RiskScoreStaging (CustomerId, RiskScore, RiskTier) SELECT CustomerId, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE C.RiskScore IS NOT NULL AND C.RiskTier IS NOT NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.RiskScoreHistory AS Target USING (SELECT CustomerId, RiskScore, RiskTier, @ProcessDate AS LastScoredDate, @ProcessDate AS FirstScoredDate FROM PRO.CustomerRiskProfile WHERE C.RiskScore IS NOT NULL AND C.RiskTier IS NOT NULL) AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate = Source.LastScoredDate WHEN NOT MATCHED BY TARGET THEN INSERT (CustomerId, RiskScore, RiskTier, FirstScoredDate, LastScoredDate) VALUES (Source.CustomerId, Source.RiskScore, Source.RiskTier, Source.FirstScoredDate, Source.LastScoredDate)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, @ProcessDate, RiskScore, RiskTier FROM PRO.CustomerRiskProfile WHERE C.RiskScore IS NOT NULL AND C.RiskTier IS NOT NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RiskTier = CASE WHEN C.RiskScore < 50 THEN 'LOW' WHEN C.RiskScore >= 50 AND C.RiskScore < 75 THEN 'MODERATE' WHEN C.RiskScore >= 75 AND C.RiskScore < 100 THEN 'HIGH' ELSE 'SEVERE' END FROM PRO.CustomerRiskProfile C WHERE C.RiskScore IS NOT NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN COALESCE(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEVERE' THEN -40 ELSE 0 END FROM PRO.CustomerRiskProfile C WHERE C.RiskTier IS NOT NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate = GETDATE() WHEN NOT MATCHED BY TARGET THEN INSERT (CustomerId, RiskScore, RiskTier, FirstScoredDate, LastScoredDate) VALUES (Source.CustomerId, Source.RiskScore, Source.RiskTier, GETDATE(), GETDATE())
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO PRO.RiskScoreAuditLog (CustomerId, ScoreDate, RiskScore, RiskTier) SELECT CustomerId, GETDATE(), RiskScore, RiskTier FROM #RiskScoreStaging
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RiskTier = CASE WHEN C.RiskScore <= 50 THEN 'LOW' WHEN C.RiskScore > 50 AND C.RiskScore <= 100 THEN 'MODERATE' WHEN C.RiskScore > 100 AND C.RiskScore <= 150 THEN 'HIGH' ELSE 'SEVERE' END FROM PRO.CustomerRiskProfile C WHERE C.RiskScore IS NOT NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RiskScore = (ISNULL(C.OverdueDays, 0) * 0.5) + (ISNULL(C.UtilizationRatio, 0) * 100 * 0.3) + (ISNULL(C.PriorDefaultCount, 0) * 20 * 0.2), C.RiskTier = CASE WHEN C.RiskScore <= 50 THEN 'LOW' WHEN C.RiskScore > 50 AND C.RiskScore <= 100 THEN 'MODERATE' WHEN C.RiskScore > 100 AND C.RiskScore <= 150 THEN 'HIGH' ELSE 'SEVERE' END, C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEVERE' THEN -40 ELSE 0 END FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.RiskScoreHistory AS Target USING #RiskScoreStaging AS Source ON Target.CustomerId = Source.CustomerId WHEN MATCHED THEN UPDATE SET Target.RiskScore = Source.RiskScore, Target.RiskTier = Source.RiskTier, Target.LastScoredDate = @ProcessDate WHEN NOT MATCHED BY TARGET THEN INSERT (CustomerId, RiskScore, RiskTier, FirstScoredDate, LastScoredDate) VALUES (Source.CustomerId, Source.RiskScore, Source.RiskTier, @ProcessDate, @ProcessDate)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RiskTier = CASE WHEN C.RiskScore < 50 THEN 'LOW' WHEN C.RiskScore >= 50 AND C.RiskScore < 75 THEN 'MODERATE' WHEN C.RiskScore >= 75 AND C.RiskScore < 100 THEN 'HIGH' ELSE 'SEVERE' END FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE C SET C.RecommendedLimitAdjustmentPct = CASE WHEN C.RiskTier = 'LOW' THEN CASE WHEN ISNULL(C.PriorDefaultCount, 0) = 0 THEN 10 ELSE 0 END WHEN C.RiskTier = 'MODERATE' THEN 0 WHEN C.RiskTier = 'HIGH' THEN -15 WHEN C.RiskTier = 'SEVERE' THEN -40 ELSE 0 END FROM PRO.CustomerRiskProfile C WHERE C.CreditLimit IS NOT NULL AND C.CreditLimit > 0
- Synthesized in 7 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
