# GovtGuarAppropriation — Verification & Traceability

> Companion artifact to `PRO.GovtGuarAppropriation.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_b4a046e0936e` |

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
| Source Hash | `8ebfdd094bedd2d51dba69ce6a0a0da1599fb6d3eb0b7b9653c4c0037d52ab15` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T08:44:04.869151+00:00` |
| Object ID | `obj_b4a046e0936e` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_beb070f638c1` |
| Total LLM Calls | `5` |
| Successful Calls | `5` |
| Failed Calls | `0` |
| Prompt Tokens | `36367` |
| Completion Tokens | `8240` |
| Total Tokens | `44607` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 4772 | available |
| synthesis | 2 | 2 | 0 | 13960 | available |
| synthesis_revision | 2 | 2 | 0 | 25875 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| ⚠️ 1 | Reset AppGovGur to zero [MATCHED] (`rule__1`) | `AppGovGur` | For accounts where the customer is not currently being processed, the AppGovGur field is reset to zero. |
| ⚠️ 2 | Calculate government guarantee [MATCHED] (`rule__2`) | `GovGur` | Calculate the government guarantee amount for accounts with specific facility types and non-zero government guarantee amounts, and store it… |
| ⚠️ 3 | Update AppGovGur with calculated amount [MATCHED] (`rule__3`) | `AppGovGur` | Update the AppGovGur field in the account records with the calculated government guarantee amount from the temporary table for accounts wit… |
| ⚠️ 4 | Update AppGovGur with government guarantee amount [MATCHED] (`rule__4`) | `AppGovGur` | Update the AppGovGur field in the account records with the government guarantee amount for accounts with facility types other than specifie… |
| 🟠 5 | Determine GovGur [MATCHED] (`deterministic_case_0034_0036_879_govgur`) | `GovGur` | First matching row wins; ELSE includes false or NULL predicates. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Reset AppGovGur to zero (rule__1) | UPDATE A SET A.AppGovGur =0 FROM ##ACCOUNTCAL A INNER JOIN ##CustomerCal B ON A.CustomerEntityID=B.CustomerEntityID WHERE B.FlgProcessing='N' | Not cited | 00_main_body+nested_block:embedded_01_12 | dependency_0001 | Verified |
| 2 | Calculate government guarantee (rule__2) | SELECT A.AccountEntityID,(CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 THEN (A.GovtGtyAmt * (A.NetBalance / SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId))) END) GovGur INTO #TEMPTABLEAppGovGur FROM ##ACCOUNTCAL A WHERE A.F… | Not cited | 00_main_body+nested_block:chunk_text_06 | Not cited | Verified |
| 3 | Update AppGovGur with calculated amount (rule__3) | UPDATE A SET A.AppGovGur=B.GovGur FROM ##ACCOUNTCAL A INNER JOIN #TEMPTABLEAppGovGur B ON A.AccountEntityID=B.AccountEntityID WHERE A.FacilityType IN('BP','BD') | Not cited | 00_main_body+nested_block:embedded_02_13 | dependency_0001 | Verified |
| 4 | Update AppGovGur with government guarantee amount (rule__4) | UPDATE A SET A.AppGovGur=GovtGtyAmt FROM ##ACCOUNTCAL A WHERE NOT (A.FacilityType IN('BP','BD')) | Not cited | 00_main_body+nested_block:embedded_03_14 | Not cited | Verified |
| 5 | Determine GovGur (deterministic_case_0034_0036_879_govgur) | Not cited | source \| Lines 34-36 | Not cited | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0034_0036_879:branch_001 | SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 | source \| Lines 34-36 \| Statement 00_main_body+nested_block:chunk_text_08 |
| case_0034_0036_879:branch_002 | ELSE | source \| Line 36 \| Statement 00_main_body+nested_block:chunk_text_09 |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 48
- **Disposition:** covered_by_rule=26, technical_only=11, uncovered=11

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | covered_by_rule | Lines 1-2 | 00_main_body+nested_block:chunk_text_01, 00_main_body+nested_block | BEGIN SET NOCOUNT ON |
| UPDATE | covered_by_rule | Lines 4-6 | 00_main_body+nested_block:chunk_text_02, 00_main_body+nested_block | BEGIN TRY /*-----UPDATE AppGovGur =0 --------------------------*/ |
| UPDATE | covered_by_rule | Lines 7-9 | 00_main_body+nested_block:chunk_text_03, 00_main_body+nested_block | UPDATE A SET A.AppGovGur =0 FROM ##ACCOUNTCAL A INNER JOIN ##CustomerCal B ON A.CustomerEntityID=B.CustomerEntityID WHERE B.FlgProcessing='N' |
| STATEMENT | covered_by_rule | Lines 12-12 | 00_main_body+nested_block:chunk_text_04, 00_main_body+nested_block | IF OBJECT_ID('TEMPDB..#TEMPTABLEAppGovGur') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 13-13 | 00_main_body+nested_block:chunk_text_05, 00_main_body+nested_block | DROP TABLE #TEMPTABLEAppGovGur |
| SELECT | covered_by_rule | Lines 16-20 | 00_main_body+nested_block:chunk_text_06, 00_main_body+nested_block | SELECT A.AccountEntityID,(CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 THEN (A.GovtGtyAmt * (A.NetBalance / SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId))) END) GovGur INTO #TEMPTABLEAppGovGur FROM ##... |
| UPDATE | covered_by_rule | Lines 24-26 | 00_main_body+nested_block:chunk_text_07, 00_main_body+nested_block | UPDATE A SET A.AppGovGur=B.GovGur FROM ##ACCOUNTCAL A INNER JOIN #TEMPTABLEAppGovGur B ON A.AccountEntityID=B.AccountEntityID WHERE A.FacilityType IN('BP','BD') |
| UPDATE | covered_by_rule | Lines 29-31 | 00_main_body+nested_block:chunk_text_08, 00_main_body+nested_block | UPDATE A SET A.AppGovGur=GovtGtyAmt FROM ##ACCOUNTCAL A WHERE NOT (A.FacilityType IN('BP','BD')) |
| UPDATE | covered_by_rule | Lines 33-35 | 00_main_body+nested_block:chunk_text_09, 00_main_body+nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='GovtGuarAppropriation' |
| UPDATE | covered_by_rule | Lines 37-40 | 00_main_body+nested_block:chunk_text_10, 00_main_body+nested_block | DROP TABLE #TEMPTABLEAppGovGur -----------------Added for DashBoard 04-03-2021 --Update BANDAUDITSTATUS set CompletedCount=CompletedCount+1 where BandName='ASSET CLASSIFICATION' |
| STATEMENT | covered_by_rule | Lines 42-42 | 00_main_body+nested_block:chunk_text_11, 00_main_body+nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 7-9 | 00_main_body+nested_block:embedded_01_12, 00_main_body+nested_block | UPDATE A SET A.AppGovGur =0 FROM ##ACCOUNTCAL A INNER JOIN ##CustomerCal B ON A.CustomerEntityID=B.CustomerEntityID WHERE B.FlgProcessing='N' |
| SELECT | covered_by_rule | Lines 16-20 | 00_main_body+nested_block:embedded_02_13, 00_main_body+nested_block | SELECT A.AccountEntityID,(CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 THEN (A.GovtGtyAmt * (A.NetBalance / SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId))) END) GovGur INTO #TEMPTABLEAppGovGur FROM ##... |
| UPDATE | covered_by_rule | Lines 24-26 | 00_main_body+nested_block:embedded_03_14, 00_main_body+nested_block | UPDATE A SET A.AppGovGur=B.GovGur FROM ##ACCOUNTCAL A INNER JOIN #TEMPTABLEAppGovGur B ON A.AccountEntityID=B.AccountEntityID WHERE A.FacilityType IN('BP','BD') |
| UPDATE | covered_by_rule | Lines 29-31 | 00_main_body+nested_block:embedded_04_15, 00_main_body+nested_block | UPDATE A SET A.AppGovGur=GovtGtyAmt FROM ##ACCOUNTCAL A WHERE NOT (A.FacilityType IN('BP','BD')) |
| UPDATE | covered_by_rule | Lines 33-35 | 00_main_body+nested_block:embedded_05_16, 00_main_body+nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='GovtGuarAppropriation' |
| STATEMENT | uncovered | Lines 1-1 | 01_exception:chunk_text_01, 01_exception | BEGIN CATCH |
| UPDATE | uncovered | Lines 3-5 | 01_exception:chunk_text_02, 01_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='GovtGuarAppropriation' |
| STATEMENT | uncovered | Lines 6-6 | 01_exception:chunk_text_03, 01_exception | END CATCH |
| SET | uncovered | Lines 8-8 | 01_exception:chunk_text_04, 01_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 01_exception:chunk_text_05, 01_exception | END |
| STATEMENT | covered_by_rule | Lines 20-20 | 01_exception:chunk_text_06, 01_exception | GO |
| UPDATE | uncovered | Lines 3-5 | 01_exception:embedded_01_07, 01_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='GovtGuarAppropriation' |
| SET | uncovered | Lines 8-8 | 01_exception:embedded_02_08, 01_exception | SET NOCOUNT OFF |
| UPDATE_TEMP | technical_only | samples/06_GovtGuarAppropriation_REAL_UNEDITED.sql | 00_main_body+nested_block:chunk_text_03, 00_main_body+nested_block:chunk_text_03, 00_main_body+nested_block | UPDATE A SET A.AppGovGur =0 FROM ##ACCOUNTCAL A INNER JOIN ##CustomerCal B ON A.CustomerEntityID=B.CustomerEntityID WHERE B.FlgProcessing='N' |
| READ_TEMP | technical_only | samples/06_GovtGuarAppropriation_REAL_UNEDITED.sql | 00_main_body+nested_block:chunk_text_03, 00_main_body+nested_block:chunk_text_03, 00_main_body+nested_block | UPDATE A SET A.AppGovGur =0 FROM ##ACCOUNTCAL A INNER JOIN ##CustomerCal B ON A.CustomerEntityID=B.CustomerEntityID WHERE B.FlgProcessing='N' |
| READ_TEMP | technical_only | samples/06_GovtGuarAppropriation_REAL_UNEDITED.sql | 00_main_body+nested_block:chunk_text_06, 00_main_body+nested_block:chunk_text_06, 00_main_body+nested_block | SELECT A.AccountEntityID,(CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 THEN (A.GovtGtyAmt * (A.NetBalance / SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId))) END) GovGur INTO #TEMPTABLEAppGovGur FROM ##... |
| INSERT_TEMP | technical_only | samples/06_GovtGuarAppropriation_REAL_UNEDITED.sql | 00_main_body+nested_block:chunk_text_06, 00_main_body+nested_block:chunk_text_06, 00_main_body+nested_block | SELECT A.AccountEntityID,(CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 THEN (A.GovtGtyAmt * (A.NetBalance / SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId))) END) GovGur INTO #TEMPTABLEAppGovGur FROM ##... |
| UPDATE_TEMP | technical_only | samples/06_GovtGuarAppropriation_REAL_UNEDITED.sql | 00_main_body+nested_block:chunk_text_07, 00_main_body+nested_block:chunk_text_07, 00_main_body+nested_block | UPDATE A SET A.AppGovGur=B.GovGur FROM ##ACCOUNTCAL A INNER JOIN #TEMPTABLEAppGovGur B ON A.AccountEntityID=B.AccountEntityID WHERE A.FacilityType IN('BP','BD') |
| READ_TEMP | technical_only | samples/06_GovtGuarAppropriation_REAL_UNEDITED.sql | 00_main_body+nested_block:chunk_text_07, 00_main_body+nested_block:chunk_text_07, 00_main_body+nested_block | UPDATE A SET A.AppGovGur=B.GovGur FROM ##ACCOUNTCAL A INNER JOIN #TEMPTABLEAppGovGur B ON A.AccountEntityID=B.AccountEntityID WHERE A.FacilityType IN('BP','BD') |
| UPDATE_TEMP | technical_only | samples/06_GovtGuarAppropriation_REAL_UNEDITED.sql | 00_main_body+nested_block:chunk_text_08, 00_main_body+nested_block:chunk_text_08, 00_main_body+nested_block | UPDATE A SET A.AppGovGur=GovtGtyAmt FROM ##ACCOUNTCAL A WHERE NOT (A.FacilityType IN('BP','BD')) |
| UPDATE | covered_by_rule | samples/06_GovtGuarAppropriation_REAL_UNEDITED.sql | 00_main_body+nested_block:chunk_text_09, 00_main_body+nested_block:chunk_text_09, 00_main_body+nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='GovtGuarAppropriation' |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body+nested_block:embedded_01_12, 00_main_body+nested_block:embedded_01_12, 00_main_body+nested_block | UPDATE A SET A.AppGovGur =0 FROM ##ACCOUNTCAL A INNER JOIN ##CustomerCal B ON A.CustomerEntityID=B.CustomerEntityID WHERE B.FlgProcessing='N' |
| READ_TEMP | technical_only | unavailable | 00_main_body+nested_block:embedded_02_13, 00_main_body+nested_block:embedded_02_13, 00_main_body+nested_block | SELECT A.AccountEntityID,(CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 THEN (A.GovtGtyAmt * (A.NetBalance / SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId))) END) GovGur INTO #TEMPTABLEAppGovGur FROM ##... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body+nested_block:embedded_03_14, 00_main_body+nested_block:embedded_03_14, 00_main_body+nested_block | UPDATE A SET A.AppGovGur=B.GovGur FROM ##ACCOUNTCAL A INNER JOIN #TEMPTABLEAppGovGur B ON A.AccountEntityID=B.AccountEntityID WHERE A.FacilityType IN('BP','BD') |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body+nested_block:embedded_04_15, 00_main_body+nested_block:embedded_04_15, 00_main_body+nested_block | UPDATE A SET A.AppGovGur=GovtGtyAmt FROM ##ACCOUNTCAL A WHERE NOT (A.FacilityType IN('BP','BD')) |
| UPDATE | covered_by_rule | unavailable | 00_main_body+nested_block:embedded_05_16, 00_main_body+nested_block:embedded_05_16, 00_main_body+nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='GovtGuarAppropriation' |
| UPDATE | uncovered | samples/06_GovtGuarAppropriation_REAL_UNEDITED.sql / Lines 61-80 | 01_exception:chunk_text_02, 01_exception:chunk_text_02, 01_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='GovtGuarAppropriation' |
| UPDATE | uncovered | unavailable | 01_exception:embedded_01_07, 01_exception:embedded_01_07, 01_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='GovtGuarAppropriation' |
| CASE | covered_by_rule | Lines 34-36 | 00_main_body+nested_block:chunk_text_08 | SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 |
| ELSE | covered_by_rule | Lines 36-36 | 00_main_body+nested_block:chunk_text_09 | ELSE |
| IF | uncovered | Lines 30-30 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 34-34 | unavailable | SELECT A.AccountEntityID,(CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 |
| CASE_BRANCH | covered_by_rule | Lines 34-34 | unavailable | SELECT A.AccountEntityID,(CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 |
| CALCULATION | covered_by_rule | Lines 34-34 | unavailable | SELECT A.AccountEntityID,(CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 |
| CALCULATION | covered_by_rule | Lines 35-35 | unavailable | THEN (A.GovtGtyAmt * (A.NetBalance / SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId))) |
| CATCH | uncovered | Lines 61-61 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 66-66 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| temp_write_to_read | 00_main_body+nested_block:embedded_01_12 / ##ACCOUNTCAL | 00_main_body+nested_block:embedded_02_13 / ##ACCOUNTCAL | high |

Unresolved dependency candidates: 26. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 5
- **By rule type:** deterministic_decision_table = 1, explicit = 4
- **By validation status:** verified = 5

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 10
- **Deterministic-only facts:** 2
- **LLM-only claims:** 1
- **Conflicts:** 5
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_read (`recon_83b39e5e453c`): full_source
- `CONFLICT` tables_written (`recon_e0e7216f95ad`): full_source
- `LLM_ONLY` tables_written (`recon_49cf18a47dfc`): full_source
- `CONFLICT` tables_written (`recon_e0e7216f95ad`): full_source
- `CONFLICT` tables_written (`recon_e0e7216f95ad`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 85.77777777777777/100
- **Statement coverage:** 14 / 24 (58.3%)
- **Rule grounding coverage:** 4 / 5 (80.0%)
- **Decision-chain coverage:** 2 / 2 branches (100.0%)
- **Conflicts:** 5
- **Contradictions:** 5
- **Review required items:** 11
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Commented-out logic found in source (1 block(s)) and excluded from extraction - not included in the business rules.
- Synthesized in 2 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
