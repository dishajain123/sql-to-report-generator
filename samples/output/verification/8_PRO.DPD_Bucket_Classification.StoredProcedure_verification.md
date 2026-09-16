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
| Prompt Version | `4f519f469b95300a` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `e455daa4382c749cb51b9aeddb6a078eb577f8ab2a6a75754bce810661b49a2b` |
| Configuration Version | `db93bfb59420a471` |
| Run Timestamp | `2026-09-16T17:38:20.806740+00:00` |
| Object ID | `obj_ff7556b8a40e` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_78a096ad83df` |
| Total LLM Calls | `7` |
| Successful Calls | `7` |
| Failed Calls | `0` |
| Prompt Tokens | `40767` |
| Completion Tokens | `7533` |
| Total Tokens | `48300` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 9863 | available |
| synthesis | 6 | 6 | 0 | 38437 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| ⚠️ 1 | Calculate DpdDays for non-null due dates [MATCHED] (`rule__1`) | `DpdDays` | Calculate the number of days past due for loan accounts with a non-null last payment due date that is less than or equal to the process dat… |
| 🟠 2 | Determine DpdBucket [MATCHED] (`deterministic_case_0043_0050_1482_dpdbucket`) | `DpdBucket` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 3 | Determine PenalInterestAmount [MATCHED] (`deterministic_case_0059_0064_2167_penalinterestamount`) | `PenalInterestAmount` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 4 | Determine BucketWorsened [MATCHED] (`deterministic_tsql_if_0071_0094_bucketworsened`) | `BucketWorsened` | Not specified |
| 🟠 5 | Determine AdjustedPenalty [MATCHED] (`deterministic_case_0117_0121_4529_adjustedpenalty`) | `AdjustedPenalty` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 6 | Determine Reason [MATCHED] (`deterministic_decision_5813_6511_2_reason`) | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| 🟢 7 | Classify DPD bucket [MATCHED] (`rule__1__2`) | `DpdBucket` | Classify loan accounts into DPD buckets based on the number of days past due, affecting the account's risk assessment and management. |
| 🟠 8 | Update DpdBucketHistory with new values [LLM_ONLY] (`rule__1__3`) | `DpdBucketHistory, DpdBucket, AdjustedPenalty, LastUpdatedDate` | Update the DpdBucket, AdjustedPenalty, and LastUpdatedDate fields in the DpdBucketHistory table with the latest values from the DpdStaging… |
| 🟠 9 | Insert new records into DpdBucketHistory [LLM_ONLY] (`rule__2`) | `DpdBucketHistory, AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate` | Insert new records into the DpdBucketHistory table with values from the DpdStaging table for unmatched records. |
| ⚠️ 10 | Classify DPD buckets [MATCHED] (`rule__1__5`) | `CollectionsQueue` | Classify loan accounts into DPD buckets based on the number of days past due and facility type, and escalate severe cases. |
| ⚠️ 11 | Read DPD bucket history [MATCHED] (`rule__1__6`) | `DpdBucket, AccountId` | Retrieve the last updated DPD bucket for each account from the DpdBucketHistory table. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Calculate DpdDays for non-null due dates (rule__1) | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate | Not cited | 00_batch3_main_body:chunk_text_06 | 00_batch3_main_body:chunk_text_06 | Verified |
| 2 | Determine DpdBucket (deterministic_case_0043_0050_1482_dpdbucket) | Not cited | source \| Lines 43-50 | Not cited | Not cited | Verified |
| 3 | Determine PenalInterestAmount (deterministic_case_0059_0064_2167_penalinterestamount) | Not cited | source \| Lines 59-64 | Not cited | Not cited | Verified |
| 4 | Determine BucketWorsened (deterministic_tsql_if_0071_0094_bucketworsened) | Not cited | source \| Lines 71-94 | Not cited | Not cited | Verified |
| 5 | Determine AdjustedPenalty (deterministic_case_0117_0121_4529_adjustedpenalty) | Not cited | source \| Lines 117-121 | Not cited | Not cited | Verified |
| 6 | Determine Reason (deterministic_decision_5813_6511_2_reason) | Not cited | source \| Lines 143-157 | Not cited | Not cited | Verified |
| 7 | Classify DPD bucket (rule__1__2) | A.DpdDays IS NOT NULL; CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE'... | Not cited | Not cited | Not cited | Verified |
| 8 | Update DpdBucketHistory with new values (rule__1__3) | WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdatedDate = @ProcessDate | Not cited | Not cited | Not cited | Needs Review |
| 9 | Insert new records into DpdBucketHistory (rule__2) | WHEN NOT MATCHED BY TARGET THEN INSERT (AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate) VALUES (Source.AccountId, Source.DpdBucket, Source.AdjustedPenalty, @ProcessDate, @ProcessDate) | Not cited | Not cited | Not cited | Needs Review |
| 10 | Classify DPD buckets (rule__1__5) | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket IN ('BUCKET_61_90', 'B… | Not cited | Not cited | Not cited | Verified |
| 11 | Read DPD bucket history (rule__1__6) | SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate | Not cited | Not cited | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0043_0050_1482:branch_001 | A.DpdDays IS NULL | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql \| Lines 44-45 \| Chunk 01_batch3_main_body \| Statement 04_batch3_nested_block:chunk_text_08 |
| case_0043_0050_1482:branch_002 | A.DpdDays = 0 | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql \| Lines 45-46 \| Chunk 01_batch3_main_body \| Statement 04_batch3_nested_block:chunk_text_08 |
| case_0043_0050_1482:branch_003 | A.DpdDays BETWEEN 1 AND 30 | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql \| Lines 46-47 \| Chunk 01_batch3_main_body \| Statement 04_batch3_nested_block:chunk_text_08 |
| case_0043_0050_1482:branch_004 | A.DpdDays BETWEEN 31 AND 60 | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql \| Lines 47-48 \| Chunk 01_batch3_main_body \| Statement 04_batch3_nested_block:chunk_text_08 |
| case_0043_0050_1482:branch_005 | A.DpdDays BETWEEN 61 AND 90 | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql \| Lines 48-49 \| Chunk 01_batch3_main_body \| Statement 04_batch3_nested_block:chunk_text_08 |
| case_0043_0050_1482:branch_006 | ELSE | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql \| Lines 49-50 \| Chunk 01_batch3_main_body \| Statement 04_batch3_nested_block:chunk_text_08 |
| case_0059_0064_2167:branch_001 | A.DpdBucket = 'BUCKET_1_30' | source \| Lines 60-61 |
| case_0059_0064_2167:branch_002 | A.DpdBucket = 'BUCKET_31_60' | source \| Lines 61-62 |
| case_0059_0064_2167:branch_003 | A.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | source \| Lines 62-63 |
| case_0059_0064_2167:branch_004 | ELSE | source \| Lines 63-64 |
| tsql_if_0071_0094:branch_001 | EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) | source \| Lines 72-78 |
| tsql_if_0071_0094:branch_002 | EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) | source \| Lines 80-87 |
| tsql_if_0071_0094:branch_003 | ELSE | source \| Lines 89-93 |
| case_0117_0121_4529:branch_001 | S.FacilityType IN ('CC', 'OD') | source \| Lines 118-119 |
| case_0117_0121_4529:branch_002 | S.FacilityType IN ('TL', 'DL') | source \| Lines 119-120 |
| case_0117_0121_4529:branch_003 | ELSE | source \| Lines 120-121 |
| decision_5813_6511_2:branch_001 | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') | source \| Lines 143-157 |
| decision_5813_6511_2:branch_002 | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') | source \| Lines 143-157 |
| decision_5813_6511_2:branch_003 | ELSE | source \| Lines 143-157 |
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
| decision_chain_008:branch_001 | IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) | source |
| decision_chain_008:branch_002 | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) | source |
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

- **Executable constructs:** 151
- **Disposition:** covered_by_rule=99, technical_only=4, uncovered=48

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | covered_by_rule | Lines 1-5 | 00_batch3_main_body:chunk_text_01, 00_batch3_main_body | USE [DEMO_MISDB] SET ANSI_NULLS ON SET QUOTED_IDENTIFIER ON |
| STATEMENT | covered_by_rule | Lines 7-8 | 00_batch3_main_body:chunk_text_02, 00_batch3_main_body | BEGIN SET NOCOUNT ON |
| STATEMENT | covered_by_rule | Lines 11-11 | 00_batch3_main_body:chunk_text_03, 00_batch3_main_body | BEGIN TRY |
| SELECT | covered_by_rule | Lines 15-15 | 00_batch3_main_body:chunk_text_04, 00_batch3_main_body | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| STATEMENT | covered_by_rule | Lines 18-20 | 00_batch3_main_body:chunk_text_05, 00_batch3_main_body | DECLARE @GraceWindowStart DATE = DATEADD(DAY, -3, @ProcessDate) -- Rule 1: derive days past due from the last payment date |
| UPDATE | covered_by_rule | Lines 23-29 | 00_batch3_main_body:chunk_text_06, 00_batch3_main_body | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | covered_by_rule | Lines 32-38 | 00_batch3_main_body:chunk_text_07, 00_batch3_main_body | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | covered_by_rule | Lines 23-29 | 00_batch3_main_body:embedded_01_08, 00_batch3_main_body | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | covered_by_rule | Lines 32-38 | 00_batch3_main_body:embedded_02_09, 00_batch3_main_body | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | covered_by_rule | Lines 1-16 | 01_batch3_main_body:chunk_text_01, 01_batch3_main_body | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | covered_by_rule | Lines 1-16 | 01_batch3_main_body:embedded_01_02, 01_batch3_main_body | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | uncovered | Lines 1-14 | 02_batch3_main_body:chunk_text_01, 02_batch3_main_body | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| SELECT | uncovered | Lines 17-17 | 02_batch3_main_body:chunk_text_02, 02_batch3_main_body | IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| UPDATE | uncovered | Lines 1-14 | 02_batch3_main_body:embedded_01_03, 02_batch3_main_body | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| STATEMENT | uncovered | Lines 1-1 | 03_batch3_nested_block+batch3_main_body:chunk_text_01, 03_batch3_nested_block+batch3_main_body | BEGIN |
| UPDATE | uncovered | Lines 2-6 | 03_batch3_nested_block+batch3_main_body:chunk_text_02, 03_batch3_nested_block+batch3_main_body | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| STATEMENT | covered_by_rule | Lines 7-7 | 03_batch3_nested_block+batch3_main_body:chunk_text_03, 03_batch3_nested_block+batch3_main_body | END |
| SELECT | uncovered | Lines 9-9 | 03_batch3_nested_block+batch3_main_body:chunk_text_04, 03_batch3_nested_block+batch3_main_body | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| STATEMENT | uncovered | Lines 1-1 | 03_batch3_nested_block+batch3_main_body:chunk_text_05, 03_batch3_nested_block+batch3_main_body | BEGIN |
| UPDATE | uncovered | Lines 12-17 | 03_batch3_nested_block+batch3_main_body:chunk_text_06, 03_batch3_nested_block+batch3_main_body | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| STATEMENT | covered_by_rule | Lines 7-7 | 03_batch3_nested_block+batch3_main_body:chunk_text_07, 03_batch3_nested_block+batch3_main_body | END |
| STATEMENT | covered_by_rule | Lines 9-9 | 03_batch3_nested_block+batch3_main_body:chunk_text_08, 03_batch3_nested_block+batch3_main_body | ELSE |
| UPDATE | uncovered | Lines 2-6 | 03_batch3_nested_block+batch3_main_body:embedded_01_09, 03_batch3_nested_block+batch3_main_body | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| UPDATE | uncovered | Lines 12-17 | 03_batch3_nested_block+batch3_main_body:embedded_02_10, 03_batch3_nested_block+batch3_main_body | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| STATEMENT | uncovered | Lines 1-1 | 04_batch3_nested_block:chunk_text_01, 04_batch3_nested_block | BEGIN |
| UPDATE | uncovered | Lines 4-6 | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| STATEMENT | covered_by_rule | Lines 9-9 | 04_batch3_nested_block:chunk_text_03, 04_batch3_nested_block | END |
| STATEMENT | uncovered | Lines 13-13 | 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block | IF OBJECT_ID('tempdb..#DpdStaging') IS NOT NULL |
| STATEMENT | uncovered | Lines 16-16 | 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block | DROP TABLE #DpdStaging |
| INSERT | uncovered | Lines 20-29 | 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block | CREATE TABLE #DpdStaging ( AccountId VARCHAR(20), DpdBucket VARCHAR(20), FacilityType VARCHAR(10), AdjustedPenalty DECIMAL(18,2) ) -- Rule 6: conditional INSERT - only stage accounts that actually -- worsened this cycle, not the full pop... |
| INSERT | uncovered | Lines 32-38 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE | covered_by_rule | Lines 41-53 | 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| UPDATE | uncovered | Lines 4-6 | 04_batch3_nested_block:embedded_01_09, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| INSERT | uncovered | Lines 32-38 | 04_batch3_nested_block:embedded_02_10, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE | covered_by_rule | Lines 41-53 | 04_batch3_nested_block:embedded_03_11, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| MERGE | uncovered | Lines 1-15 | 05_batch3_nested_block:chunk_text_01, 05_batch3_nested_block | MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdated... |
| MERGE | uncovered | Lines 1-15 | 05_batch3_nested_block:embedded_01_02, 05_batch3_nested_block | MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdated... |
| INSERT | covered_by_rule | Lines 1-14 | 06_batch3_nested_block:chunk_text_01, 06_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | covered_by_rule | Lines 17-20 | 06_batch3_nested_block:chunk_text_02, 06_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | uncovered | Lines 24-26 | 06_batch3_nested_block:chunk_text_03, 06_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| STATEMENT | uncovered | Lines 30-30 | 06_batch3_nested_block:chunk_text_04, 06_batch3_nested_block | END TRY |
| STATEMENT | uncovered | Lines 33-34 | 06_batch3_nested_block:chunk_text_05, 06_batch3_nested_block | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 37-39 | 06_batch3_nested_block:chunk_text_06, 06_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| STATEMENT | uncovered | Lines 42-42 | 06_batch3_nested_block:chunk_text_07, 06_batch3_nested_block | END CATCH |
| SET | covered_by_rule | Lines 45-45 | 06_batch3_nested_block:chunk_text_08, 06_batch3_nested_block | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 9-9 | 06_batch3_nested_block:chunk_text_09, 06_batch3_nested_block | END |
| INSERT | covered_by_rule | Lines 1-14 | 06_batch3_nested_block:embedded_01_10, 06_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | covered_by_rule | Lines 17-20 | 06_batch3_nested_block:embedded_02_11, 06_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | uncovered | Lines 24-26 | 06_batch3_nested_block:embedded_03_12, 06_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| UPDATE | uncovered | Lines 37-39 | 06_batch3_nested_block:embedded_04_13, 06_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| SET | covered_by_rule | Lines 45-45 | 06_batch3_nested_block:embedded_05_14, 06_batch3_nested_block | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 00_batch3_main_body:chunk_text_04, 00_batch3_main_body:chunk_text_04, 00_batch3_main_body | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 00_batch3_main_body:chunk_text_06, 00_batch3_main_body:chunk_text_06, 00_batch3_main_body | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 00_batch3_main_body:chunk_text_07, 00_batch3_main_body:chunk_text_07, 00_batch3_main_body | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | covered_by_rule | unavailable | 00_batch3_main_body:embedded_01_08, 00_batch3_main_body:embedded_01_08, 00_batch3_main_body | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | covered_by_rule | unavailable | 00_batch3_main_body:embedded_02_09, 00_batch3_main_body:embedded_02_09, 00_batch3_main_body | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql / Lines 41-56 | 01_batch3_main_body:chunk_text_01, 01_batch3_main_body:chunk_text_01, 01_batch3_main_body | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | covered_by_rule | unavailable | 01_batch3_main_body:embedded_01_02, 01_batch3_main_body:embedded_01_02, 01_batch3_main_body | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | uncovered | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 02_batch3_main_body:chunk_text_01, 02_batch3_main_body:chunk_text_01, 02_batch3_main_body | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| READ | uncovered | unavailable | 02_batch3_main_body:chunk_text_02, 02_batch3_main_body:chunk_text_02, 02_batch3_main_body | IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| UPDATE | uncovered | unavailable | 02_batch3_main_body:embedded_01_03, 02_batch3_main_body:embedded_01_03, 02_batch3_main_body | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| UPDATE | uncovered | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 03_batch3_nested_block+batch3_main_body:chunk_text_02, 03_batch3_nested_block+batch3_main_body:chunk_text_02, 03_batch3_nested_block+batch3_main_body | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| READ | uncovered | unavailable | 03_batch3_nested_block+batch3_main_body:chunk_text_04, 03_batch3_nested_block+batch3_main_body:chunk_text_04, 03_batch3_nested_block+batch3_main_body | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| UPDATE | uncovered | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 03_batch3_nested_block+batch3_main_body:chunk_text_06, 03_batch3_nested_block+batch3_main_body:chunk_text_06, 03_batch3_nested_block+batch3_main_body | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| UPDATE | uncovered | unavailable | 03_batch3_nested_block+batch3_main_body:embedded_01_09, 03_batch3_nested_block+batch3_main_body:embedded_01_09, 03_batch3_nested_block+batch3_main_body | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| UPDATE | uncovered | unavailable | 03_batch3_nested_block+batch3_main_body:embedded_02_10, 03_batch3_nested_block+batch3_main_body:embedded_02_10, 03_batch3_nested_block+batch3_main_body | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| UPDATE | uncovered | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| INSERT_TEMP | technical_only | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE_TEMP | technical_only | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| UPDATE | uncovered | unavailable | 04_batch3_nested_block:embedded_01_09, 04_batch3_nested_block:embedded_01_09, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| READ | uncovered | unavailable | 04_batch3_nested_block:embedded_02_10, 04_batch3_nested_block:embedded_02_10, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| INSERT_TEMP | technical_only | unavailable | 04_batch3_nested_block:embedded_02_10, 04_batch3_nested_block:embedded_02_10, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE_TEMP | technical_only | unavailable | 04_batch3_nested_block:embedded_03_11, 04_batch3_nested_block:embedded_03_11, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| MERGE | uncovered | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql / Lines 128-142 | 05_batch3_nested_block:chunk_text_01, 05_batch3_nested_block:chunk_text_01, 05_batch3_nested_block | MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdated... |
| INSERT | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 06_batch3_nested_block:chunk_text_01, 06_batch3_nested_block:chunk_text_01, 06_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 06_batch3_nested_block:chunk_text_02, 06_batch3_nested_block:chunk_text_02, 06_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | uncovered | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 06_batch3_nested_block:chunk_text_03, 06_batch3_nested_block:chunk_text_03, 06_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| UPDATE | uncovered | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | 06_batch3_nested_block:chunk_text_06, 06_batch3_nested_block:chunk_text_06, 06_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| READ | covered_by_rule | unavailable | 06_batch3_nested_block:embedded_01_10, 06_batch3_nested_block:embedded_01_10, 06_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | covered_by_rule | unavailable | 06_batch3_nested_block:embedded_01_10, 06_batch3_nested_block:embedded_01_10, 06_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| READ | covered_by_rule | unavailable | 06_batch3_nested_block:embedded_02_11, 06_batch3_nested_block:embedded_02_11, 06_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| INSERT | covered_by_rule | unavailable | 06_batch3_nested_block:embedded_02_11, 06_batch3_nested_block:embedded_02_11, 06_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | uncovered | unavailable | 06_batch3_nested_block:embedded_03_12, 06_batch3_nested_block:embedded_03_12, 06_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| UPDATE | uncovered | unavailable | 06_batch3_nested_block:embedded_04_13, 06_batch3_nested_block:embedded_04_13, 06_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| CASE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql / Lines 44-45 | 04_batch3_nested_block:chunk_text_08, 01_batch3_main_body | A.DpdDays IS NULL |
| CASE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql / Lines 45-46 | 04_batch3_nested_block:chunk_text_08, 01_batch3_main_body | A.DpdDays = 0 |
| CASE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql / Lines 46-47 | 04_batch3_nested_block:chunk_text_08, 01_batch3_main_body | A.DpdDays BETWEEN 1 AND 30 |
| CASE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql / Lines 47-48 | 04_batch3_nested_block:chunk_text_08, 01_batch3_main_body | A.DpdDays BETWEEN 31 AND 60 |
| CASE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql / Lines 48-49 | 04_batch3_nested_block:chunk_text_08, 01_batch3_main_body | A.DpdDays BETWEEN 61 AND 90 |
| ELSE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql / Lines 49-50 | 04_batch3_nested_block:chunk_text_08, 01_batch3_main_body | ELSE |
| CASE | covered_by_rule | Lines 60-61 | unavailable | A.DpdBucket = 'BUCKET_1_30' |
| CASE | covered_by_rule | Lines 61-62 | unavailable | A.DpdBucket = 'BUCKET_31_60' |
| CASE | covered_by_rule | Lines 62-63 | unavailable | A.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') |
| ELSE | covered_by_rule | Lines 63-64 | unavailable | ELSE |
| IF_BRANCH | covered_by_rule | Lines 72-78 | unavailable | EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| IF_BRANCH | covered_by_rule | Lines 80-87 | unavailable | EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| ELSE | covered_by_rule | Lines 89-93 | unavailable | ELSE |
| CASE | covered_by_rule | Lines 118-119 | unavailable | S.FacilityType IN ('CC', 'OD') |
| CASE | covered_by_rule | Lines 119-120 | unavailable | S.FacilityType IN ('TL', 'DL') |
| ELSE | covered_by_rule | Lines 120-121 | unavailable | ELSE |
| IF_BRANCH | covered_by_rule | Lines 143-157 | unavailable | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') |
| IF_BRANCH | covered_by_rule | Lines 143-157 | unavailable | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') |
| ELSE | covered_by_rule | Lines 143-157 | unavailable | ELSE |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | A.DpdDays IS NULL |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | A.DpdDays = 0 |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | A.DpdDays BETWEEN 1 AND 30 |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | A.DpdDays BETWEEN 31 AND 60 |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | A.DpdDays BETWEEN 61 AND 90 |
| ELSE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | A.DpdBucket = 'BUCKET_1_30' |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | A.DpdBucket = 'BUCKET_31_60' |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | A.DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') |
| ELSE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | ELSE |
| IF_BRANCH | uncovered | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| IF_BRANCH | uncovered | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| ELSE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | S.FacilityType IN ('CC', 'OD') |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | S.FacilityType IN ('TL', 'DL') |
| ELSE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | ELSE |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') |
| IF_BRANCH | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') |
| ELSE | covered_by_rule | /var/folders/d5/q6cyw5854xz1ksr1wj0fmf5r0000gn/T/tmp1rfakqnr.sql | full_source | ELSE |
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
| CASE_BRANCH | covered_by_rule | Lines 131-131 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | covered_by_rule | Lines 136-136 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
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
| table_write_to_later_use | 01_batch3_main_body:embedded_01_02 / PRO.LoanAccountCal | 06_batch3_nested_block:embedded_01_10 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 01_batch3_main_body:embedded_01_02 / PRO.LoanAccountCal | 03_batch3_nested_block+batch3_main_body:chunk_text_04 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 01_batch3_main_body:embedded_01_02 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_02_10 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 01_batch3_main_body:embedded_01_02 / PRO.LoanAccountCal | 02_batch3_main_body:chunk_text_02 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 02_batch3_main_body:embedded_01_03 / PRO.LoanAccountCal | 06_batch3_nested_block:embedded_01_10 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 02_batch3_main_body:embedded_01_03 / PRO.LoanAccountCal | 03_batch3_nested_block+batch3_main_body:chunk_text_04 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 02_batch3_main_body:embedded_01_03 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_02_10 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 02_batch3_main_body:embedded_01_03 / PRO.LoanAccountCal | 02_batch3_main_body:chunk_text_02 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_nested_block+batch3_main_body:embedded_01_09 / PRO.LoanAccountCal | 03_batch3_nested_block+batch3_main_body:chunk_text_04 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_nested_block+batch3_main_body:embedded_01_09 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_02_10 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_nested_block+batch3_main_body:embedded_01_09 / PRO.LoanAccountCal | 02_batch3_main_body:chunk_text_02 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_09 / PRO.LoanAccountCal | 03_batch3_nested_block+batch3_main_body:chunk_text_04 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_09 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_02_10 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_09 / PRO.LoanAccountCal | 02_batch3_main_body:chunk_text_02 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_nested_block+batch3_main_body:embedded_02_10 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_02_10 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 03_batch3_nested_block+batch3_main_body:embedded_02_10 / PRO.LoanAccountCal | 02_batch3_main_body:chunk_text_02 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 00_batch3_main_body:embedded_01_08 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_02_10 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 00_batch3_main_body:embedded_01_08 / PRO.LoanAccountCal | 02_batch3_main_body:chunk_text_02 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_02_10 / #DpdStaging | 04_batch3_nested_block:embedded_03_11 / #DpdStaging | high |
| table_write_to_later_use | 00_batch3_main_body:embedded_02_09 / PRO.LoanAccountCal | 02_batch3_main_body:chunk_text_02 / PRO.LoanAccountCal | high |

Unresolved dependency candidates: 83. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 11
- **By rule type:** deterministic_decision_table = 5, explicit = 6
- **By validation status:** unverified = 2, verified = 9

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 24
- **Deterministic-only facts:** 23
- **LLM-only claims:** 2
- **Conflicts:** 9
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
- **Quality score:** 76.5098814229249/100
- **Statement coverage:** 30 / 51 (58.8%)
- **Rule grounding coverage:** 4 / 11 (36.4%)
- **Decision-chain coverage:** 19 / 19 branches (100.0%)
- **Conflicts:** 9
- **Contradictions:** 10
- **Review required items:** 21
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Synthesis response reached the output limit; recovered rules may be incomplete.
- Synthesis section failed after 1 attempt(s) (chunks ['02_batch3_main_body']): Synthesis prompt for 'DPD_Bucket_Classification' is estimated at ~9535 tokens, which leaves no room under LLM_TPM_LIMIT=8000 even for the smallest useful completion. Either raise LLM_TPM_LIMIT to match what your account's rate-limit page actually shows, or reduce SYNTHESIS_EVIDENCE_MAP_MAX_CHARS / SYNTHESIS_SECTION_MAX_CHARS so each synthesis section carries less content.
- Synthesis section failed after 1 attempt(s) (chunks ['02_batch3_main_body']): Synthesis prompt for 'DPD_Bucket_Classification' is estimated at ~9532 tokens, which leaves no room under LLM_TPM_LIMIT=8000 even for the smallest useful completion. Either raise LLM_TPM_LIMIT to match what your account's rate-limit page actually shows, or reduce SYNTHESIS_EVIDENCE_MAP_MAX_CHARS / SYNTHESIS_SECTION_MAX_CHARS so each synthesis section carries less content.
- Synthesis section failed after 1 attempt(s) (chunks ['03_batch3_nested_block+batch3_main_body']): Synthesis prompt for 'DPD_Bucket_Classification' is estimated at ~8356 tokens, which leaves no room under LLM_TPM_LIMIT=8000 even for the smallest useful completion. Either raise LLM_TPM_LIMIT to match what your account's rate-limit page actually shows, or reduce SYNTHESIS_EVIDENCE_MAP_MAX_CHARS / SYNTHESIS_SECTION_MAX_CHARS so each synthesis section carries less content.
- Synthesis section failed after 1 attempt(s) (chunks ['03_batch3_nested_block+batch3_main_body']): Synthesis prompt for 'DPD_Bucket_Classification' is estimated at ~8347 tokens, which leaves no room under LLM_TPM_LIMIT=8000 even for the smallest useful completion. Either raise LLM_TPM_LIMIT to match what your account's rate-limit page actually shows, or reduce SYNTHESIS_EVIDENCE_MAP_MAX_CHARS / SYNTHESIS_SECTION_MAX_CHARS so each synthesis section carries less content.
- Synthesis section failed after 1 attempt(s) (chunks ['04_batch3_nested_block']): Synthesis prompt for 'DPD_Bucket_Classification' is estimated at ~9320 tokens, which leaves no room under LLM_TPM_LIMIT=8000 even for the smallest useful completion. Either raise LLM_TPM_LIMIT to match what your account's rate-limit page actually shows, or reduce SYNTHESIS_EVIDENCE_MAP_MAX_CHARS / SYNTHESIS_SECTION_MAX_CHARS so each synthesis section carries less content.
- Synthesis section failed after 1 attempt(s) (chunks ['04_batch3_nested_block']): Synthesis prompt for 'DPD_Bucket_Classification' is estimated at ~9369 tokens, which leaves no room under LLM_TPM_LIMIT=8000 even for the smallest useful completion. Either raise LLM_TPM_LIMIT to match what your account's rate-limit page actually shows, or reduce SYNTHESIS_EVIDENCE_MAP_MAX_CHARS / SYNTHESIS_SECTION_MAX_CHARS so each synthesis section carries less content.
- Synthesized in 12 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
- The business rule synthesis response could not be parsed as valid JSON; the object's rules should be regenerated.
