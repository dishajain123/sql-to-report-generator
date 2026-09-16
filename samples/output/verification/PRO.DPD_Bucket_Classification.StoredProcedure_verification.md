# DPD Bucket Classification — Verification & Traceability

> Companion artifact to `PRO.DPD_Bucket_Classification.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_ff7556b8a40e` |
| Raw technical object name (from source) | `DPD_Bucket_Classification` |

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
| Source Hash | `e455daa4382c749cb51b9aeddb6a078eb577f8ab2a6a75754bce810661b49a2b` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:12:52.968844+00:00` |
| Object ID | `obj_ff7556b8a40e` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_00d1835a920c` |
| Total LLM Calls | `17` |
| Successful Calls | `17` |
| Failed Calls | `0` |
| Prompt Tokens | `526615` |
| Completion Tokens | `38614` |
| Total Tokens | `565229` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 9707 | available |
| synthesis | 8 | 8 | 0 | 265640 | available |
| synthesis_retry | 7 | 7 | 0 | 229238 | available |
| synthesis_revision | 1 | 1 | 0 | 60644 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Determine DpdBucket [MATCHED] (`deterministic_case_0043_0050_1482_dpdbucket`) | `DpdBucket` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 2 | Determine PenalInterestAmount [MATCHED] (`deterministic_case_0059_0064_2167_penalinterestamount`) | `PenalInterestAmount` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 3 | Determine BucketWorsened [MATCHED] (`deterministic_tsql_if_0071_0094_bucketworsened`) | `BucketWorsened` | Not specified |
| 🟠 4 | Determine AdjustedPenalty [MATCHED] (`deterministic_case_0117_0121_4529_adjustedpenalty`) | `AdjustedPenalty` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 5 | Determine Reason [MATCHED] (`deterministic_decision_5813_6511_2_reason`) | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| ⚠️ 6 | Calculate DPD days [MATCHED] (`rule__1`) | `DpdDays` | Determine the number of days past due for each loan account. |
| ⚠️ 7 | Classify DPD bucket [MATCHED] (`rule__2`) | `DpdBucket` | Classify each loan account into a DPD bucket based on the number of days past due. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Determine DpdBucket (deterministic_case_0043_0050_1482_dpdbucket) | Not cited | source \| Lines 43-50 | Not cited | Not cited | Verified |
| 2 | Determine PenalInterestAmount (deterministic_case_0059_0064_2167_penalinterestamount) | Not cited | source \| Lines 59-64 | Not cited | Not cited | Verified |
| 3 | Determine BucketWorsened (deterministic_tsql_if_0071_0094_bucketworsened) | Not cited | source \| Lines 71-94 | Not cited | Not cited | Verified |
| 4 | Determine AdjustedPenalty (deterministic_case_0117_0121_4529_adjustedpenalty) | Not cited | source \| Lines 117-121 | Not cited | Not cited | Verified |
| 5 | Determine Reason (deterministic_decision_5813_6511_2_reason) | Not cited | source \| Lines 143-157 | Not cited | Not cited | Verified |
| 6 | Calculate DPD days (rule__1) | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate | Not cited | Not cited | Not cited | Verified |
| 7 | Classify DPD bucket (rule__2) | UPDATE A SET A.DpdBucket = CASE WHEN A.DpdDays <= 30 THEN 'BUCKET_1_30' WHEN A.DpdDays > 30 AND A.DpdDays <= 60 THEN 'BUCKET_31_60' WHEN A.DpdDays > 60 AND A.DpdDays <= 90 THEN 'BUCKET_61_90' ELSE 'BUCKET_90_PLUS' END FROM PRO.LoanAccountCal A WHERE A.DpdDays… | Not cited | Not cited | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0043_0050_1482:branch_001 | A.DpdDays IS NULL | samples/07_DPD_Bucket_Classification.sql \| Lines 44-45 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_07 |
| case_0043_0050_1482:branch_002 | A.DpdDays = 0 | samples/07_DPD_Bucket_Classification.sql \| Lines 45-46 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_07 |
| case_0043_0050_1482:branch_003 | A.DpdDays BETWEEN 1 AND 30 | samples/07_DPD_Bucket_Classification.sql \| Lines 46-47 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_07 |
| case_0043_0050_1482:branch_004 | A.DpdDays BETWEEN 31 AND 60 | samples/07_DPD_Bucket_Classification.sql \| Lines 47-48 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_07 |
| case_0043_0050_1482:branch_005 | A.DpdDays BETWEEN 61 AND 90 | samples/07_DPD_Bucket_Classification.sql \| Lines 48-49 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_07 |
| case_0043_0050_1482:branch_006 | ELSE | samples/07_DPD_Bucket_Classification.sql \| Lines 49-50 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_07 |
| case_0059_0064_2167:branch_001 | A.DpdBucket = 'BUCKET_1_30' | samples/07_DPD_Bucket_Classification.sql \| Lines 60-61 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_08 |
| case_0059_0064_2167:branch_002 | A.DpdBucket = 'BUCKET_31_60' | samples/07_DPD_Bucket_Classification.sql \| Lines 61-62 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_10 |
| case_0059_0064_2167:branch_003 | A.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | samples/07_DPD_Bucket_Classification.sql \| Lines 62-63 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_10 |
| case_0059_0064_2167:branch_004 | ELSE | samples/07_DPD_Bucket_Classification.sql \| Lines 63-64 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_12 |
| tsql_if_0071_0094:branch_001 | EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) | samples/07_DPD_Bucket_Classification.sql \| Lines 72-78 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_18 |
| tsql_if_0071_0094:branch_002 | EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) | samples/07_DPD_Bucket_Classification.sql \| Lines 80-87 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_22 |
| tsql_if_0071_0094:branch_003 | ELSE | samples/07_DPD_Bucket_Classification.sql \| Lines 89-93 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_23 |
| case_0117_0121_4529:branch_001 | S.FacilityType IN ('CC', 'OD') | samples/07_DPD_Bucket_Classification.sql \| Lines 118-119 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_25 |
| case_0117_0121_4529:branch_002 | S.FacilityType IN ('TL', 'DL') | samples/07_DPD_Bucket_Classification.sql \| Lines 119-120 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_25 |
| case_0117_0121_4529:branch_003 | ELSE | samples/07_DPD_Bucket_Classification.sql \| Lines 120-121 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_25 |
| decision_5813_6511_2:branch_001 | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') | samples/07_DPD_Bucket_Classification.sql \| Lines 143-157 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_26 |
| decision_5813_6511_2:branch_002 | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | samples/07_DPD_Bucket_Classification.sql \| Lines 143-157 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_26 |
| decision_5813_6511_2:branch_003 | ELSE | samples/07_DPD_Bucket_Classification.sql \| Lines 143-157 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_26 |
| decision_chain_006:branch_001 | A.DpdDays IS NULL | source |
| decision_chain_006:branch_002 | A.DpdDays = 0 | source |
| decision_chain_006:branch_003 | A.DpdDays BETWEEN 1 AND 30 | source |
| decision_chain_006:branch_004 | A.DpdDays BETWEEN 31 AND 60 | source |
| decision_chain_006:branch_005 | A.DpdDays BETWEEN 61 AND 90 | source |
| decision_chain_006:branch_006 | ELSE | source |
| decision_chain_007:branch_001 | A.DpdBucket = 'BUCKET_1_30' | source |
| decision_chain_007:branch_002 | A.DpdBucket = 'BUCKET_31_60' | source |
| decision_chain_007:branch_003 | A.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | source |
| decision_chain_007:branch_004 | ELSE | source |
| decision_chain_008:branch_001 | A.LastPaymentDueDate >= @GraceWindowStart | source |
| decision_chain_008:branch_002 | A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) | source |
| decision_chain_008:branch_003 | ELSE | source |
| decision_chain_009:branch_001 | S.FacilityType IN ('CC', 'OD') | source |
| decision_chain_009:branch_002 | S.FacilityType IN ('TL', 'DL') | source |
| decision_chain_009:branch_003 | ELSE | source |
| decision_chain_010:branch_001 | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') | source |
| decision_chain_010:branch_002 | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | source |
| decision_chain_010:branch_003 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 155
- **Disposition:** covered_by_rule=105, technical_only=4, uncovered=46

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | uncovered | Lines 1-2 | 03_batch3_main_body:chunk_text_01, 03_batch3_main_body | BEGIN SET NOCOUNT ON |
| STATEMENT | uncovered | Lines 1-1 | 04_batch3_nested_block:chunk_text_01, 04_batch3_nested_block | BEGIN TRY |
| SELECT | uncovered | Lines 3-3 | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| STATEMENT | uncovered | Lines 4-6 | 04_batch3_nested_block:chunk_text_03, 04_batch3_nested_block | DECLARE @GraceWindowStart DATE = DATEADD(DAY, -3, @ProcessDate) -- Rule 1: derive days past due from the last payment date |
| UPDATE | covered_by_rule | Lines 7-13 | 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | uncovered | Lines 14-20 | 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | uncovered | Lines 21-36 | 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | covered_by_rule | Lines 37-50 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| SELECT | uncovered | Lines 51-51 | 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block | IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| STATEMENT | uncovered | Lines 1-1 | 04_batch3_nested_block:chunk_text_09, 04_batch3_nested_block | BEGIN |
| UPDATE | uncovered | Lines 53-57 | 04_batch3_nested_block:chunk_text_10, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| STATEMENT | covered_by_rule | Lines 30-30 | 04_batch3_nested_block:chunk_text_11, 04_batch3_nested_block | END |
| SELECT | covered_by_rule | Lines 59-59 | 04_batch3_nested_block:chunk_text_12, 04_batch3_nested_block | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| STATEMENT | uncovered | Lines 1-1 | 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 61-66 | 04_batch3_nested_block:chunk_text_14, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| STATEMENT | covered_by_rule | Lines 30-30 | 04_batch3_nested_block:chunk_text_15, 04_batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 29-29 | 04_batch3_nested_block:chunk_text_16, 04_batch3_nested_block | ELSE |
| STATEMENT | uncovered | Lines 1-1 | 04_batch3_nested_block:chunk_text_17, 04_batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 70-72 | 04_batch3_nested_block:chunk_text_18, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| STATEMENT | covered_by_rule | Lines 30-30 | 04_batch3_nested_block:chunk_text_19, 04_batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 75-75 | 04_batch3_nested_block:chunk_text_20, 04_batch3_nested_block | IF OBJECT_ID('tempdb..#DpdStaging') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 76-76 | 04_batch3_nested_block:chunk_text_21, 04_batch3_nested_block | DROP TABLE #DpdStaging |
| INSERT | covered_by_rule | Lines 78-87 | 04_batch3_nested_block:chunk_text_22, 04_batch3_nested_block | CREATE TABLE #DpdStaging ( AccountId VARCHAR(20), DpdBucket VARCHAR(20), FacilityType VARCHAR(10), AdjustedPenalty DECIMAL(18,2) ) -- Rule 6: conditional INSERT - only stage accounts that actually -- worsened this cycle, not the full pop... |
| INSERT | covered_by_rule | Lines 88-94 | 04_batch3_nested_block:chunk_text_23, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE | uncovered | Lines 95-107 | 04_batch3_nested_block:chunk_text_24, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| MERGE | covered_by_rule | Lines 108-122 | 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block | MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdated... |
| INSERT | uncovered | Lines 123-136 | 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | uncovered | Lines 137-140 | 04_batch3_nested_block:chunk_text_27, 04_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | covered_by_rule | Lines 142-144 | 04_batch3_nested_block:chunk_text_28, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| STATEMENT | covered_by_rule | Lines 146-146 | 04_batch3_nested_block:chunk_text_29, 04_batch3_nested_block | END TRY |
| STATEMENT | covered_by_rule | Lines 147-148 | 04_batch3_nested_block:chunk_text_30, 04_batch3_nested_block | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | covered_by_rule | Lines 149-151 | 04_batch3_nested_block:chunk_text_31, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| STATEMENT | covered_by_rule | Lines 152-152 | 04_batch3_nested_block:chunk_text_32, 04_batch3_nested_block | END CATCH |
| SET | covered_by_rule | Lines 153-153 | 04_batch3_nested_block:chunk_text_33, 04_batch3_nested_block | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 30-30 | 04_batch3_nested_block:chunk_text_34, 04_batch3_nested_block | END |
| UPDATE | covered_by_rule | Lines 7-13 | 04_batch3_nested_block:embedded_01_35, 04_batch3_nested_block | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | uncovered | Lines 14-20 | 04_batch3_nested_block:embedded_02_36, 04_batch3_nested_block | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | uncovered | Lines 21-36 | 04_batch3_nested_block:embedded_03_37, 04_batch3_nested_block | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | covered_by_rule | Lines 37-50 | 04_batch3_nested_block:embedded_04_38, 04_batch3_nested_block | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| UPDATE | uncovered | Lines 53-57 | 04_batch3_nested_block:embedded_05_39, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| UPDATE | covered_by_rule | Lines 61-66 | 04_batch3_nested_block:embedded_06_40, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| UPDATE | covered_by_rule | Lines 70-72 | 04_batch3_nested_block:embedded_07_41, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| INSERT | covered_by_rule | Lines 88-94 | 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE | uncovered | Lines 95-107 | 04_batch3_nested_block:embedded_09_43, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| MERGE | covered_by_rule | Lines 108-122 | 04_batch3_nested_block:embedded_10_44, 04_batch3_nested_block | MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdated... |
| INSERT | uncovered | Lines 123-136 | 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | uncovered | Lines 137-140 | 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | covered_by_rule | Lines 142-144 | 04_batch3_nested_block:embedded_13_47, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| UPDATE | covered_by_rule | Lines 149-151 | 04_batch3_nested_block:embedded_14_48, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| SET | covered_by_rule | Lines 153-153 | 04_batch3_nested_block:embedded_15_49, 04_batch3_nested_block | SET NOCOUNT OFF |
| READ | uncovered | unavailable | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| READ | uncovered | unavailable | 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block | IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_10, 04_batch3_nested_block:chunk_text_10, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| READ | uncovered | unavailable | 04_batch3_nested_block:chunk_text_12, 04_batch3_nested_block:chunk_text_12, 04_batch3_nested_block | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_14, 04_batch3_nested_block:chunk_text_14, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_18, 04_batch3_nested_block:chunk_text_18, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| INSERT_TEMP | technical_only | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_23, 04_batch3_nested_block:chunk_text_23, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE_TEMP | technical_only | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_24, 04_batch3_nested_block:chunk_text_24, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| MERGE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block | MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdated... |
| INSERT | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_27, 04_batch3_nested_block:chunk_text_27, 04_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_28, 04_batch3_nested_block:chunk_text_28, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_31, 04_batch3_nested_block:chunk_text_31, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_01_35, 04_batch3_nested_block:embedded_01_35, 04_batch3_nested_block | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | uncovered | unavailable | 04_batch3_nested_block:embedded_02_36, 04_batch3_nested_block:embedded_02_36, 04_batch3_nested_block | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | uncovered | unavailable | 04_batch3_nested_block:embedded_03_37, 04_batch3_nested_block:embedded_03_37, 04_batch3_nested_block | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | uncovered | unavailable | 04_batch3_nested_block:embedded_04_38, 04_batch3_nested_block:embedded_04_38, 04_batch3_nested_block | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| UPDATE | uncovered | unavailable | 04_batch3_nested_block:embedded_05_39, 04_batch3_nested_block:embedded_05_39, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| UPDATE | uncovered | unavailable | 04_batch3_nested_block:embedded_06_40, 04_batch3_nested_block:embedded_06_40, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| UPDATE | uncovered | unavailable | 04_batch3_nested_block:embedded_07_41, 04_batch3_nested_block:embedded_07_41, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| READ | uncovered | unavailable | 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| INSERT_TEMP | technical_only | unavailable | 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE_TEMP | technical_only | unavailable | 04_batch3_nested_block:embedded_09_43, 04_batch3_nested_block:embedded_09_43, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| READ | uncovered | unavailable | 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | uncovered | unavailable | 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| READ | uncovered | unavailable | 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| INSERT | uncovered | unavailable | 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | uncovered | unavailable | 04_batch3_nested_block:embedded_13_47, 04_batch3_nested_block:embedded_13_47, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| UPDATE | uncovered | unavailable | 04_batch3_nested_block:embedded_14_48, 04_batch3_nested_block:embedded_14_48, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 44-45 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | A.DpdDays IS NULL |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 45-46 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | A.DpdDays = 0 |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 46-47 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | A.DpdDays BETWEEN 1 AND 30 |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 47-48 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | A.DpdDays BETWEEN 31 AND 60 |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 48-49 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | A.DpdDays BETWEEN 61 AND 90 |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 49-50 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | ELSE |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 60-61 | 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block | A.DpdBucket = 'BUCKET_1_30' |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 61-62 | 04_batch3_nested_block:chunk_text_10, 04_batch3_nested_block | A.DpdBucket = 'BUCKET_31_60' |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 62-63 | 04_batch3_nested_block:chunk_text_10, 04_batch3_nested_block | A.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 63-64 | 04_batch3_nested_block:chunk_text_12, 04_batch3_nested_block | ELSE |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 72-78 | 04_batch3_nested_block:chunk_text_18, 04_batch3_nested_block | EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 80-87 | 04_batch3_nested_block:chunk_text_22, 04_batch3_nested_block | EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 89-93 | 04_batch3_nested_block:chunk_text_23, 04_batch3_nested_block | ELSE |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 118-119 | 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block | S.FacilityType IN ('CC', 'OD') |
| CASE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 119-120 | 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block | S.FacilityType IN ('TL', 'DL') |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 120-121 | 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block | ELSE |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 143-157 | 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 143-157 | 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 143-157 | 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block | ELSE |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.DpdDays IS NULL |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.DpdDays = 0 |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.DpdDays BETWEEN 1 AND 30 |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.DpdDays BETWEEN 31 AND 60 |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.DpdDays BETWEEN 61 AND 90 |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.DpdBucket = 'BUCKET_1_30' |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.DpdBucket = 'BUCKET_31_60' |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.LastPaymentDueDate >= @GraceWindowStart |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | S.FacilityType IN ('CC', 'OD') |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | S.FacilityType IN ('TL', 'DL') |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') |
| IF_BRANCH | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') |
| ELSE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql | full_source | ELSE |
| CASE | covered_by_rule | Lines 43-43 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 44-44 | unavailable | WHEN A.DpdDays IS NULL THEN |
| CASE_BRANCH | covered_by_rule | Lines 45-45 | unavailable | WHEN A.DpdDays = 0 THEN |
| CASE_BRANCH | covered_by_rule | Lines 46-46 | unavailable | WHEN A.DpdDays BETWEEN 1 AND 30 THEN |
| CASE_BRANCH | covered_by_rule | Lines 47-47 | unavailable | WHEN A.DpdDays BETWEEN 31 AND 60 THEN |
| CASE_BRANCH | covered_by_rule | Lines 48-48 | unavailable | WHEN A.DpdDays BETWEEN 61 AND 90 THEN |
| ELSE | covered_by_rule | Lines 49-49 | unavailable | ELSE |
| CASE | covered_by_rule | Lines 59-59 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 60-60 | unavailable | WHEN A.DpdBucket = THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays |
| CASE_BRANCH | covered_by_rule | Lines 61-61 | unavailable | WHEN A.DpdBucket = THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays |
| CASE_BRANCH | covered_by_rule | Lines 62-62 | unavailable | WHEN A.DpdBucket IN ( , ) THEN (A.OutstandingBalance * 0.04) / 365 * A.DpdDays |
| ELSE | covered_by_rule | Lines 63-63 | unavailable | ELSE 0 |
| IF | covered_by_rule | Lines 71-71 | unavailable | IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| ELSE | covered_by_rule | Lines 79-79 | unavailable | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| IF | covered_by_rule | Lines 79-79 | unavailable | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| ELSE | covered_by_rule | Lines 88-88 | unavailable | ELSE |
| IF | uncovered | Lines 95-95 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 117-117 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 118-118 | unavailable | WHEN S.FacilityType IN ( , ) THEN S.AdjustedPenalty * 1.10 |
| CASE_BRANCH | covered_by_rule | Lines 119-119 | unavailable | WHEN S.FacilityType IN ( , ) THEN S.AdjustedPenalty * 1.05 |
| ELSE | covered_by_rule | Lines 120-120 | unavailable | ELSE S.AdjustedPenalty |
| CASE_BRANCH | uncovered | Lines 131-131 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | uncovered | Lines 136-136 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CASE | covered_by_rule | Lines 145-145 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 146-146 | unavailable | WHEN DpdBucket IN ( , ) AND FacilityType IN ( , ) |
| CASE_BRANCH | covered_by_rule | Lines 148-148 | unavailable | WHEN DpdBucket IN ( , ) |
| ELSE | covered_by_rule | Lines 150-150 | unavailable | ELSE |
| CATCH | uncovered | Lines 167-167 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 172-172 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_35 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_35 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_35 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_35 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_02_36 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_02_36 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_02_36 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_02_36 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_04 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_04 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_04 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_04 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_05 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_05 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_05 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_05 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_06 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_06 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_06 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_06 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| later_update_overrides_field | 04_batch3_nested_block:chunk_text_07 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_04_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_07 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_07 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_07 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_07 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_10 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_10 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_10 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_10 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_14 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_14 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_14 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_14 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_18 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_18 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| later_update_overrides_field | 04_batch3_nested_block:chunk_text_18 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_41 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_18 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_18 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_23 / #DpdStaging | 04_batch3_nested_block:chunk_text_24 / #DpdStaging | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_23 / #DpdStaging | 04_batch3_nested_block:embedded_08_42 / #DpdStaging | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_23 / #DpdStaging | 04_batch3_nested_block:embedded_09_43 / #DpdStaging | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_24 / #DpdStaging | 04_batch3_nested_block:embedded_08_42 / #DpdStaging | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_25 / PRO.DpdBucketHistory | 04_batch3_nested_block:embedded_12_46 / PRO.DpdBucketHistory | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_26 / PRO.CollectionsQueue | 04_batch3_nested_block:embedded_11_45 / PRO.CollectionsQueue | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_27 / PRO.DpdBucketAuditLog | 04_batch3_nested_block:embedded_12_46 / PRO.DpdBucketAuditLog | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_03_37 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_03_37 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_03_37 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_03_37 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_04_38 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_08 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_04_38 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_04_38 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_04_38 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_05_39 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_12 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_05_39 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_05_39 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_06_40 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_06_40 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_07_41 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_08_42 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_07_41 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_11_45 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_08_42 / #DpdStaging | 04_batch3_nested_block:embedded_09_43 / #DpdStaging | high |

Unresolved dependency candidates: 32. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** deterministic_decision_table = 5, explicit = 2
- **By validation status:** verified = 7

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 20
- **Deterministic-only facts:** 27
- **LLM-only claims:** 1
- **Conflicts:** 8
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_303872d07307`): full_source
- `CONFLICT` tables_written (`recon_303872d07307`): full_source
- `CONFLICT` tables_written (`recon_303872d07307`): full_source
- `CONFLICT` tables_written (`recon_303872d07307`): full_source
- `CONFLICT` tables_written (`recon_303872d07307`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 77.54347826086958/100
- **Statement coverage:** 34 / 55 (61.8%)
- **Rule grounding coverage:** 2 / 7 (28.6%)
- **Decision-chain coverage:** 19 / 19 branches (100.0%)
- **Conflicts:** 8
- **Contradictions:** 12
- **Review required items:** 21
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Synthesis response reached the output limit; recovered rules may be incomplete.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.DpdBucket = CASE WHEN A.DpdDays <= 30 THEN 'BUCKET_1_30' WHEN A.DpdDays > 30 AND A.DpdDays <= 60 THEN 'BUCKET_31_60' WHEN A.DpdDays > 60 AND A.DpdDays <= 90 THEN 'BUCKET_61_90' ELSE 'BUCKET_90_PLUS' END FROM PRO.LoanAccountCal A WHERE A.DpdDays IS NOT NULL
- Synthesized in 8 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
- The business rule synthesis response could not be parsed as valid JSON; the object's rules should be regenerated.
