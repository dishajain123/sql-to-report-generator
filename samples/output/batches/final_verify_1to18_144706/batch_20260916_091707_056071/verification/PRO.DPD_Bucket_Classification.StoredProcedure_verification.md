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
| Run Timestamp | `2026-09-16T09:20:09.400860+00:00` |
| Object ID | `obj_ff7556b8a40e` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_c2be55c0c3b0` |
| Total LLM Calls | `17` |
| Successful Calls | `17` |
| Failed Calls | `0` |
| Prompt Tokens | `535035` |
| Completion Tokens | `38784` |
| Total Tokens | `573819` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 9877 | available |
| synthesis | 8 | 8 | 0 | 265640 | available |
| synthesis_retry | 7 | 7 | 0 | 229238 | available |
| synthesis_revision | 1 | 1 | 0 | 69064 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Update DpdDays [CONFLICT] (`rule__1`) | `DpdDays` | Update the DpdDays field in the LoanAccountCal table based on the number of days past due. |
| 🟢 2 | Update DpdBucket [MATCHED] (`rule__2`) | `DpdBucket` | Update the DpdBucket field in the LoanAccountCal table based on the number of days past due. |
| 🔴 3 | Update BucketWorsened and GracePeriodApplied [CONFLICT] (`rule__3`) | `BucketWorsened, GracePeriodApplied` | Update the BucketWorsened and GracePeriodApplied fields in the LoanAccountCal table based on the number of days past due. |
| 🔴 4 | Update PenalInterestAmount [CONFLICT] (`rule__4`) | `PenalInterestAmount` | Update the PenalInterestAmount field in the LoanAccountCal table based on the number of days past due. |
| 🟢 5 | Insert into DpdStaging [MATCHED] (`rule__5`) | `AccountId, DpdBucket, FacilityType, AdjustedPenalty` | Insert records into the DpdStaging table. |
| 🟢 6 | Update AdjustedPenalty in DpdStaging [MATCHED] (`rule__6`) | `AdjustedPenalty` | Update the AdjustedPenalty field in the DpdStaging table. |
| 🟢 7 | Merge into DpdBucketHistory [MATCHED] (`rule__7`) | `AccountId, DpdBucket, AdjustedPenalty, LastUpdatedDate, FirstFlaggedDate` | Merge records into the DpdBucketHistory table. |
| 🟢 8 | Insert into CollectionsQueue [MATCHED] (`rule__8`) | `AccountId, EscalationDate, Reason` | Insert records into the CollectionsQueue table. |
| 🟠 9 | Determine DpdBucket [MATCHED] (`deterministic_case_0043_0050_1482_dpdbucket`) | `DpdBucket` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 10 | Determine BucketWorsened [MATCHED] (`deterministic_tsql_if_0071_0094_bucketworsened`) | `BucketWorsened` | Not specified |
| 🟠 11 | Determine AdjustedPenalty [MATCHED] (`deterministic_case_0117_0121_4529_adjustedpenalty`) | `AdjustedPenalty` | First matching row wins; ELSE includes false or NULL predicates. |
| 🟠 12 | Determine Reason [MATCHED] (`deterministic_decision_5813_6511_2_reason`) | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| 🟢 13 | Calculate DPD days [MATCHED] (`rule__1__9`) | `DpdDays` | Determine the number of days past due for each loan account where the last payment due date is not null and is less than or equal to the pr… |
| 🟢 14 | Classify DPD buckets [MATCHED] (`rule__2__10`) | `DpdBucket` | Assign each loan account to a DPD bucket based on the number of days past due. |
| 🔴 15 | Classify DPD bucket [CONFLICT] (`rule__2__12`) | `DpdBucket` | Classify each loan account into a DPD bucket based on the number of days past due. |
| 🔴 16 | Calculate penal interest amount [CONFLICT] (`rule__3__13`) | `PenalInterestAmount` | Calculate the penal interest amount for each loan account based on the DPD bucket. |
| 🟢 17 | Calculate DPD days [MATCHED] (`rule__1__19`) | `DpdDays` | Determine the number of days past due for each loan account. |
| 🟢 18 | Classify DPD buckets [MATCHED] (`rule__2__20`) | `DpdBucket` | Classify each loan account into a DPD bucket based on the number of days past due. |
| 🟢 19 | Adjust penalty interest [MATCHED] (`rule__3__21`) | `PenalInterestAmount` | Adjust the penalty interest amount for each loan account based on its DPD bucket. |
| 🟠 20 | Update DPD history [LLM_ONLY] (`rule__4__22`) | `Target.DpdBucket, Target.AdjustedPenalty, Target.LastUpdatedDate` | Merge records from the DpdStaging table into the DpdBucketHistory table. |
| 🟢 21 | Calculate DpdDays [MATCHED] (`rule__1__23`) | `DpdDays` | Determine the number of days past due for accounts with a last payment due date. |
| 🟢 22 | Update DpdBucket [MATCHED] (`rule__2__24`) | `DpdBucket` | Classify accounts into DPD buckets based on the number of days past due. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Update DpdDays (rule__1) | DpdDays > 90 | Not cited | 04_batch3_nested_block:embedded_01_35 | dependency_0001; dependency_0002; dependency_0003; dependency_0004; dependency_0005; dependency_0006; _(+55 more instance(s) not shown)_ | Needs Review |
| 2 | Update DpdBucket (rule__2) | DpdDays > 90 | Not cited | 04_batch3_nested_block:embedded_02_36 | dependency_0001; dependency_0002; dependency_0003; dependency_0004; dependency_0005; dependency_0006; _(+55 more instance(s) not shown)_ | Verified |
| 3 | Update BucketWorsened and GracePeriodApplied (rule__3) | DpdDays > 90 | Not cited | 04_batch3_nested_block:chunk_text_10 | dependency_0026; dependency_0027; dependency_0028; dependency_0029; dependency_0030; dependency_0031; _(+30 more instance(s) not shown)_ | Needs Review |
| 4 | Update PenalInterestAmount (rule__4) | DpdDays > 90 | Not cited | 04_batch3_nested_block:chunk_text_07 | dependency_0022; dependency_0023; dependency_0024; dependency_0025; dependency_0026; dependency_0027; _(+34 more instance(s) not shown)_ | Needs Review |
| 5 | Insert into DpdStaging (rule__5) | AccountId, DpdBucket, FacilityType, AdjustedPenalty are provided | Not cited | 04_batch3_nested_block:chunk_text_23 | dependency_0039; dependency_0040; dependency_0041; dependency_0042; dependency_0043; dependency_0044; _(+17 more instance(s) not shown)_ | Verified |
| 6 | Update AdjustedPenalty in DpdStaging (rule__6) | S.AdjustedPenalty is provided | Not cited | 04_batch3_nested_block:chunk_text_24 | dependency_0040; dependency_0041; dependency_0042; dependency_0043; dependency_0044; dependency_0045; _(+16 more instance(s) not shown)_ | Verified |
| 7 | Merge into DpdBucketHistory (rule__7) | Target.AccountId, Source.AccountId, Target.DpdBucket, Source.DpdBucket, Target.AdjustedPenalty, Source.AdjustedPenalty, Target.LastUpdatedDate, AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate are provided | Not cited | 04_batch3_nested_block:chunk_text_25 | dependency_0043; dependency_0044; dependency_0045; dependency_0046; dependency_0047; dependency_0048; _(+13 more instance(s) not shown)_ | Verified |
| 8 | Insert into CollectionsQueue (rule__8) | AccountId, EscalationDate, Reason are provided | Not cited | 04_batch3_nested_block:chunk_text_26 | dependency_0044; dependency_0045; dependency_0046; dependency_0047; dependency_0048; dependency_0049; _(+12 more instance(s) not shown)_ | Verified |
| 9 | Determine DpdBucket (deterministic_case_0043_0050_1482_dpdbucket) | Not cited | source \| Lines 43-50 | Not cited | Not cited | Verified |
| 10 | Determine BucketWorsened (deterministic_tsql_if_0071_0094_bucketworsened) | Not cited | source \| Lines 71-94 | Not cited | Not cited | Verified |
| 11 | Determine AdjustedPenalty (deterministic_case_0117_0121_4529_adjustedpenalty) | Not cited | source \| Lines 117-121 | Not cited | Not cited | Verified |
| 12 | Determine Reason (deterministic_decision_5813_6511_2_reason) | Not cited | source \| Lines 143-157 | Not cited | Not cited | Verified |
| 13 | Calculate DPD days (rule__1__9) | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate | Not cited | Not cited | Not cited | Verified |
| 14 | Classify DPD buckets (rule__2__10) | UPDATE A SET A.DpdBucket = CASE WHEN A.DpdDays <= 30 THEN 'BUCKET_1_30' WHEN A.DpdDays > 30 AND A.DpdDays <= 60 THEN 'BUCKET_31_60' WHEN A.DpdDays > 60 AND A.DpdDays <= 90 THEN 'BUCKET_61_90' ELSE 'BUCKET_90_PLUS' END FROM PRO.LoanAccountCal A WHERE A.DpdDays… | Not cited | Not cited | Not cited | Verified |
| 15 | Classify DPD bucket (rule__2__12) | UPDATE A SET A.DpdBucket = (CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWEEN 61 AND 90 THEN 'BUCK… | Not cited | Not cited | Not cited | Needs Review |
| 16 | Calculate penal interest amount (rule__3__13) | UPDATE A SET A.PenalInterestAmount = (CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN ('BUCKET_61_90', 'BUCKE… | Not cited | Not cited | Not cited | Needs Review |
| 17 | Calculate DPD days (rule__1__19) | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate | Not cited | Not cited | Not cited | Verified |
| 18 | Classify DPD buckets (rule__2__20) | UPDATE A SET A.DpdBucket = CASE WHEN A.DpdDays <= 30 THEN 'BUCKET_1_30' WHEN A.DpdDays <= 60 THEN 'BUCKET_31_60' WHEN A.DpdDays <= 90 THEN 'BUCKET_61_90' ELSE 'BUCKET_90_PLUS' END FROM PRO.LoanAccountCal A WHERE A.DpdDays > COALESCE(A.PrevDpdDays, 0) AND A.Dp… | Not cited | Not cited | Not cited | Verified |
| 19 | Adjust penalty interest (rule__3__21) | UPDATE A SET A.PenalInterestAmount = CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN ('BUCKET_61_90', 'BUCKET… | Not cited | Not cited | Not cited | Verified |
| 20 | Update DPD history (rule__4__22) | MERGE INTO PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdatedDate = @ProcessDa… | Not cited | Not cited | Not cited | Needs Review |
| 21 | Calculate DpdDays (rule__1__23) | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate | Not cited | Not cited | Not cited | Verified |
| 22 | Update DpdBucket (rule__2__24) | UPDATE A SET A.DpdBucket = CASE WHEN A.DpdDays <= 30 THEN 'BUCKET_1_30' WHEN A.DpdDays <= 60 THEN 'BUCKET_31_60' WHEN A.DpdDays <= 90 THEN 'BUCKET_61_90' ELSE 'BUCKET_90_PLUS' END FROM PRO.LoanAccountCal A WHERE A.DpdDays > COALESCE(A.PrevDpdDays, 0) AND A.Dp… | Not cited | Not cited | Not cited | Verified |

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
- **Disposition:** covered_by_rule=139, technical_only=4, uncovered=12

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | uncovered | Lines 1-2 | 03_batch3_main_body:chunk_text_01, 03_batch3_main_body | BEGIN SET NOCOUNT ON |
| STATEMENT | covered_by_rule | Lines 1-1 | 04_batch3_nested_block:chunk_text_01, 04_batch3_nested_block | BEGIN TRY |
| SELECT | covered_by_rule | Lines 3-3 | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| STATEMENT | covered_by_rule | Lines 4-6 | 04_batch3_nested_block:chunk_text_03, 04_batch3_nested_block | DECLARE @GraceWindowStart DATE = DATEADD(DAY, -3, @ProcessDate) -- Rule 1: derive days past due from the last payment date |
| UPDATE | covered_by_rule | Lines 7-13 | 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | covered_by_rule | Lines 14-20 | 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | covered_by_rule | Lines 21-36 | 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | covered_by_rule | Lines 37-50 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| SELECT | covered_by_rule | Lines 51-51 | 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block | IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| STATEMENT | covered_by_rule | Lines 1-1 | 04_batch3_nested_block:chunk_text_09, 04_batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 53-57 | 04_batch3_nested_block:chunk_text_10, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| STATEMENT | covered_by_rule | Lines 30-30 | 04_batch3_nested_block:chunk_text_11, 04_batch3_nested_block | END |
| SELECT | covered_by_rule | Lines 59-59 | 04_batch3_nested_block:chunk_text_12, 04_batch3_nested_block | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
| STATEMENT | covered_by_rule | Lines 1-1 | 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 61-66 | 04_batch3_nested_block:chunk_text_14, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| STATEMENT | covered_by_rule | Lines 30-30 | 04_batch3_nested_block:chunk_text_15, 04_batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 29-29 | 04_batch3_nested_block:chunk_text_16, 04_batch3_nested_block | ELSE |
| STATEMENT | covered_by_rule | Lines 1-1 | 04_batch3_nested_block:chunk_text_17, 04_batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 70-72 | 04_batch3_nested_block:chunk_text_18, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| STATEMENT | covered_by_rule | Lines 30-30 | 04_batch3_nested_block:chunk_text_19, 04_batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 75-75 | 04_batch3_nested_block:chunk_text_20, 04_batch3_nested_block | IF OBJECT_ID('tempdb..#DpdStaging') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 76-76 | 04_batch3_nested_block:chunk_text_21, 04_batch3_nested_block | DROP TABLE #DpdStaging |
| INSERT | covered_by_rule | Lines 78-87 | 04_batch3_nested_block:chunk_text_22, 04_batch3_nested_block | CREATE TABLE #DpdStaging ( AccountId VARCHAR(20), DpdBucket VARCHAR(20), FacilityType VARCHAR(10), AdjustedPenalty DECIMAL(18,2) ) -- Rule 6: conditional INSERT - only stage accounts that actually -- worsened this cycle, not the full pop... |
| INSERT | covered_by_rule | Lines 88-94 | 04_batch3_nested_block:chunk_text_23, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE | covered_by_rule | Lines 95-107 | 04_batch3_nested_block:chunk_text_24, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| MERGE | covered_by_rule | Lines 108-122 | 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block | MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdated... |
| INSERT | covered_by_rule | Lines 123-136 | 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | covered_by_rule | Lines 137-140 | 04_batch3_nested_block:chunk_text_27, 04_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | covered_by_rule | Lines 142-144 | 04_batch3_nested_block:chunk_text_28, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| STATEMENT | covered_by_rule | Lines 146-146 | 04_batch3_nested_block:chunk_text_29, 04_batch3_nested_block | END TRY |
| STATEMENT | covered_by_rule | Lines 147-148 | 04_batch3_nested_block:chunk_text_30, 04_batch3_nested_block | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | covered_by_rule | Lines 149-151 | 04_batch3_nested_block:chunk_text_31, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| STATEMENT | covered_by_rule | Lines 152-152 | 04_batch3_nested_block:chunk_text_32, 04_batch3_nested_block | END CATCH |
| SET | covered_by_rule | Lines 153-153 | 04_batch3_nested_block:chunk_text_33, 04_batch3_nested_block | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 30-30 | 04_batch3_nested_block:chunk_text_34, 04_batch3_nested_block | END |
| UPDATE | covered_by_rule | Lines 7-13 | 04_batch3_nested_block:embedded_01_35, 04_batch3_nested_block | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | covered_by_rule | Lines 14-20 | 04_batch3_nested_block:embedded_02_36, 04_batch3_nested_block | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | covered_by_rule | Lines 21-36 | 04_batch3_nested_block:embedded_03_37, 04_batch3_nested_block | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | covered_by_rule | Lines 37-50 | 04_batch3_nested_block:embedded_04_38, 04_batch3_nested_block | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| UPDATE | covered_by_rule | Lines 53-57 | 04_batch3_nested_block:embedded_05_39, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| UPDATE | covered_by_rule | Lines 61-66 | 04_batch3_nested_block:embedded_06_40, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| UPDATE | covered_by_rule | Lines 70-72 | 04_batch3_nested_block:embedded_07_41, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| INSERT | covered_by_rule | Lines 88-94 | 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE | covered_by_rule | Lines 95-107 | 04_batch3_nested_block:embedded_09_43, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| MERGE | covered_by_rule | Lines 108-122 | 04_batch3_nested_block:embedded_10_44, 04_batch3_nested_block | MERGE PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdated... |
| INSERT | covered_by_rule | Lines 123-136 | 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | covered_by_rule | Lines 137-140 | 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | covered_by_rule | Lines 142-144 | 04_batch3_nested_block:embedded_13_47, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| UPDATE | covered_by_rule | Lines 149-151 | 04_batch3_nested_block:embedded_14_48, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| SET | covered_by_rule | Lines 153-153 | 04_batch3_nested_block:embedded_15_49, 04_batch3_nested_block | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block | UPDATE A SET A.DpdDays = DATEDIFF(DAY, A.LastPaymentDueDate, @ProcessDate) FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NOT NULL AND A.LastPaymentDueDate <= @ProcessDate -- Rule 2: accounts with no due date on record cannot be... |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block | IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE LastPaymentDueDate >= @GraceWindowStart) |
| UPDATE | covered_by_rule | samples/07_DPD_Bucket_Classification.sql / Lines 21-174 | 04_batch3_nested_block:chunk_text_10, 04_batch3_nested_block:chunk_text_10, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:chunk_text_12, 04_batch3_nested_block:chunk_text_12, 04_batch3_nested_block | ELSE IF EXISTS (SELECT 1 FROM PRO.LoanAccountCal WHERE PrevDpdBucket IS NOT NULL) |
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
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_02_36, 04_batch3_nested_block:embedded_02_36, 04_batch3_nested_block | UPDATE A SET A.DpdDays = 0, A.DpdBucket = 'NOT_APPLICABLE' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate IS NULL -- Rule 3: multi-branch bucket classification by DPD range |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_03_37, 04_batch3_nested_block:embedded_03_37, 04_batch3_nested_block | UPDATE A SET A.DpdBucket = ( CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWE... |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_04_38, 04_batch3_nested_block:embedded_04_38, 04_batch3_nested_block | UPDATE A SET A.PenalInterestAmount = ( CASE WHEN A.DpdBucket = 'BUCKET_1_30' THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays WHEN A.DpdBucket = 'BUCKET_31_60' THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays WHEN A.DpdBucket IN... |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_05_39, 04_batch3_nested_block:embedded_05_39, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N', A.GracePeriodApplied = 'Y' FROM PRO.LoanAccountCal A WHERE A.LastPaymentDueDate >= @GraceWindowStart |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_06_40, 04_batch3_nested_block:embedded_06_40, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'Y' FROM PRO.LoanAccountCal A WHERE A.PrevDpdBucket IS NOT NULL AND A.DpdBucket <> A.PrevDpdBucket AND A.DpdDays > ISNULL(A.PrevDpdDays, 0) |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_07_41, 04_batch3_nested_block:embedded_07_41, 04_batch3_nested_block | UPDATE A SET A.BucketWorsened = 'N' FROM PRO.LoanAccountCal A |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| INSERT_TEMP | technical_only | unavailable | 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block:embedded_08_42, 04_batch3_nested_block | INSERT INTO #DpdStaging (AccountId, DpdBucket, FacilityType, AdjustedPenalty) SELECT A.AccountId, A.DpdBucket, A.FacilityType, A.PenalInterestAmount FROM PRO.LoanAccountCal A WHERE A.BucketWorsened = 'Y' -- Rule 7: derived-assignment UPD... |
| UPDATE_TEMP | technical_only | unavailable | 04_batch3_nested_block:embedded_09_43, 04_batch3_nested_block:embedded_09_43, 04_batch3_nested_block | UPDATE S SET S.AdjustedPenalty = ( CASE WHEN S.FacilityType IN ('CC', 'OD') THEN S.AdjustedPenalty * 1.10 WHEN S.FacilityType IN ('TL', 'DL') THEN S.AdjustedPenalty * 1.05 ELSE S.AdjustedPenalty END ) FROM #DpdStaging S WHERE S.AdjustedP... |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| INSERT | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block:embedded_11_45, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, CASE WHEN DpdBucket IN ('BUCKET_61_90', 'BUCKET_90_PLUS') AND FacilityType IN ('CC', 'OD') THEN 'SEVERE_DPD_CASH_CREDIT' WHEN DpdBucket... |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| INSERT | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block:embedded_12_46, 04_batch3_nested_block | INSERT INTO PRO.DpdBucketAuditLog (AccountId, TransitionDate, NewBucket) SELECT H.AccountId, @ProcessDate, H.DpdBucket FROM PRO.DpdBucketHistory H WHERE H.LastUpdatedDate = @ProcessDate |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_13_47, 04_batch3_nested_block:embedded_13_47, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_14_48, 04_batch3_nested_block:embedded_14_48, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'DPD_Bucket_Classification' |
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
| CASE_BRANCH | uncovered | Lines 60-60 | unavailable | WHEN A.DpdBucket = THEN (A.OutstandingBalance * 0.02) / 365 * A.DpdDays |
| CASE_BRANCH | uncovered | Lines 61-61 | unavailable | WHEN A.DpdBucket = THEN (A.OutstandingBalance * 0.03) / 365 * A.DpdDays |
| CASE_BRANCH | uncovered | Lines 62-62 | unavailable | WHEN A.DpdBucket IN ( , ) THEN (A.OutstandingBalance * 0.04) / 365 * A.DpdDays |
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

- **Total business rules:** 22
- **By rule type:** deterministic_decision_table = 4, explicit = 18
- **By validation status:** unverified = 6, verified = 16

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 32
- **Deterministic-only facts:** 0
- **LLM-only claims:** 2
- **Conflicts:** 13
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
- **Quality score:** 86.26877470355733/100
- **Statement coverage:** 34 / 55 (61.8%)
- **Rule grounding coverage:** 17 / 22 (77.3%)
- **Decision-chain coverage:** 19 / 19 branches (100.0%)
- **Conflicts:** 13
- **Contradictions:** 18
- **Review required items:** 33
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: DpdDays > 90
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: AccountId, DpdBucket, FacilityType, AdjustedPenalty are provided
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: S.AdjustedPenalty is provided
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Target.AccountId, Source.AccountId, Target.DpdBucket, Source.DpdBucket, Target.AdjustedPenalty, Source.AdjustedPenalty, Target.LastUpdatedDate, AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate are provided
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: AccountId, EscalationDate, Reason are provided
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.DpdBucket = CASE WHEN A.DpdDays <= 30 THEN 'BUCKET_1_30' WHEN A.DpdDays > 30 AND A.DpdDays <= 60 THEN 'BUCKET_31_60' WHEN A.DpdDays > 60 AND A.DpdDays <= 90 THEN 'BUCKET_61_90' ELSE 'BUCKET_90_PLUS' END FROM PRO.LoanAccountCal A WHERE A.DpdDays > COALESCE(A.PrevDpdDays, 0) AND A.DpdBucket <> A.PrevDpdBucket
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.DpdBucket = (CASE WHEN A.DpdDays IS NULL THEN 'NOT_APPLICABLE' WHEN A.DpdDays = 0 THEN 'CURRENT' WHEN A.DpdDays BETWEEN 1 AND 30 THEN 'BUCKET_1_30' WHEN A.DpdDays BETWEEN 31 AND 60 THEN 'BUCKET_31_60' WHEN A.DpdDays BETWEEN 61 AND 90 THEN 'BUCKET_61_90' END) FROM PRO.LoanAccountCal A
- Synthesis response reached the output limit; recovered rules may be incomplete.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.DpdBucket = CASE WHEN A.DpdDays <= 30 THEN 'BUCKET_1_30' WHEN A.DpdDays > 30 AND A.DpdDays <= 60 THEN 'BUCKET_31_60' WHEN A.DpdDays > 60 AND A.DpdDays <= 90 THEN 'BUCKET_61_90' ELSE 'BUCKET_90_PLUS' END FROM PRO.LoanAccountCal A WHERE A.DpdDays IS NOT NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.DpdBucket = CASE WHEN A.DpdDays <= 30 THEN 'BUCKET_1_30' WHEN A.DpdDays > 30 AND A.DpdDays <= 60 THEN 'BUCKET_31_60' WHEN A.DpdDays > 60 AND A.DpdDays <= 90 THEN 'BUCKET_61_90' ELSE 'BUCKET_90_PLUS' END FROM PRO.LoanAccountCal A WHERE A.DpdDays > 0
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.DpdBucket = CASE WHEN A.DpdDays <= 30 THEN 'BUCKET_1_30' WHEN A.DpdDays <= 60 THEN 'BUCKET_31_60' WHEN A.DpdDays <= 90 THEN 'BUCKET_61_90' ELSE 'BUCKET_90_PLUS' END FROM PRO.LoanAccountCal A WHERE A.DpdDays > COALESCE(A.PrevDpdDays, 0) AND A.DpdBucket <> A.PrevDpdBucket
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.DpdBucketHistory AS Target USING #DpdStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.DpdBucket = Source.DpdBucket, Target.AdjustedPenalty = Source.AdjustedPenalty, Target.LastUpdatedDate = @ProcessDate WHEN NOT MATCHED BY TARGET THEN INSERT (AccountId, DpdBucket, AdjustedPenalty, FirstFlaggedDate, LastUpdatedDate) VALUES (Source.AccountId, Source.DpdBucket, Source.AdjustedPenalty, @ProcessDate, @ProcessDate)
- Synthesized in 8 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
