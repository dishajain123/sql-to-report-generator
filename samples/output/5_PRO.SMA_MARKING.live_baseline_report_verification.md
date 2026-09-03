# SMA Marking — Verification & Traceability

> Companion artifact to `PRO.SMA_MARKING.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_7bd00a4d3ff9` |
| Raw technical object name (from source) | `SMA_MARKING_12122023` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `ead05609fa4a6f41` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `f460ffa9a400079ae1cc7050278c39538a2ec22f1ba51bf01f10cd35065bb02d` |
| Configuration Version | `4ea5bb9cae5982bb` |
| Run Timestamp | `2026-09-03T03:54:25.706888+00:00` |
| Object ID | `obj_7bd00a4d3ff9` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_3217fc689b55` |
| Total LLM Calls | `12` |
| Successful Calls | `12` |
| Failed Calls | `0` |
| Prompt Tokens | `91389` |
| Completion Tokens | `17561` |
| Total Tokens | `108950` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 11 | 11 | 0 | 64073 | available |
| synthesis | 1 | 1 | 0 | 44877 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Reset negative DPD to zero [CONFLICT] (`rule_0c298aa8f0c0`) | `DPD_IntService` | negative DPD are reset to zero. |
| 🔴 2 | Reset negative DPD to zero [CONFLICT] (`rule_65e4be6c2ad0`) | `DPD_NoCredit` | negative DPD are reset to zero. |
| 🔴 3 | Reset negative DPD to zero [CONFLICT] (`rule_7db62e6a2b7c`) | `DPD_Overdrawn` | negative DPD are reset to zero. |
| 🔴 4 | Reset negative DPD to zero [CONFLICT] (`rule_6a640ea16c58`) | `DPD_Overdue` | negative DPD are reset to zero. |
| 🔴 5 | Reset negative DPD to zero [CONFLICT] (`rule_830d23a31775`) | `DPD_Renewal` | negative DPD are reset to zero. |
| 🟠 6 | Reset negative DPD to zero [LLM_ONLY] (`rule_5f494bf605d8`) | `DPD_StockStmt` | negative DPD are reset to zero. |
| 🔴 7 | Assign account-level SMA fields in order [CONFLICT] (`rule_22f53f187b7d`) | `SMA_CLASS, SMA_REASON` | The account-level SMA fields in order is assigned. |
| 🟠 8 | Update customer movement history [LLM_ONLY] (`rule_ca0ccdb75ce3`) | `EffectiveToTimeKey` | Updates the effective to time key and movement to date in the customer movement history. |
| 🔴 9 | Reset negative DPD values to zero [CONFLICT] (`rule_6097f150db38`) | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | Negative overdue-day values are reset to zero before the maximum overdue days is calculated. |
| 🔴 10 | Propagate customer-level SMA status [CONFLICT] (`rule_17b76dad5b17`) | `FLGSMA, SMA_DT` | Propagate customer-level SMA status. |
| 🔴 11 | Calculate maximum DPD for account [CONFLICT] (`rule_1cb7966427ff`) | `DPD_Max` | The maximum DPD is calculated for the account. |
| 🔴 12 | Assign customer movement description by key [CONFLICT] (`rule_7e6059d465d1`) | `CustMoveDescription` | Customer-level SMA status is aggregated from linked SMA-marked accounts. Customer movement descriptions are assigned from the applicable as… |
| 🔴 13 | Clear SMA fields before reprocessing [CONFLICT] (`rule_800f501f8018`) | `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA` | Existing SMA classification fields are cleared before the account is reprocessed. |
| 🟠 14 | Update DPD_Max [MATCHED] (`rule_3794267c5c42`) | `DPD_Max` | The procedure sets DPD_Max to the source-defined value. |
| 🟠 15 | Update SMA_CLASS [MATCHED] (`rule_046dce107da9`) | `SMA_CLASS` | The procedure sets SMA_CLASS to the source-defined value. |
| 🔴 16 | Update EffectiveToTimeKey, MovementToDate [CONFLICT] (`rule_95a6376b7d82`) | `EffectiveToTimeKey, MovementToDate` | The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS… |
| 🔴 17 | Update EffectiveToTimeKey, MovementToDate [CONFLICT] (`rule_a6f6db894bd4`) | `EffectiveToTimeKey, MovementToDate` | The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCust… |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Reset negative DPD to zero (rule_0c298aa8f0c0) | isnull(DPD_IntService,0)<0 | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Line 55 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_05 (+1 more span(s)) | 01_nested_block:nested_block | conditions[0]: isnull(DPD_IntService,0)<0 -> UPDATE #DPD SET DPD_IntService=0; table_operations[4]; table_operations[15]; tables_read[3]: #DPD \| READ \| target: A.CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COA…; tables_read[13]: PRO.ACCOUNTCAL \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_C…; tables_written[1]: #DPD \| UPDATE \| target: DPD_IntService \| WHERE: COALESCE(DPD_IntService, 0) < 0; _(+1 more instance(s) not shown)_ | Verified |
| 2 | Reset negative DPD to zero (rule_65e4be6c2ad0) | isnull(DPD_NoCredit,0)<0 | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Line 57 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_06 (+1 more span(s)) | 01_nested_block:nested_block | conditions[1]: isnull(DPD_NoCredit,0)<0 -> UPDATE #DPD SET DPD_NoCredit=0; table_operations[5]; table_operations[16]; tables_read[4]: A \| READ \| target: N/A \| WHERE: None; tables_read[14]: PRO.CUSTOMERCAL \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_…; tables_written[2]: #DPD \| UPDATE \| target: DPD_NoCredit \| WHERE: COALESCE(DPD_NoCredit, 0) < 0; _(+1 more instance(s) not shown)_ | Verified |
| 3 | Reset negative DPD to zero (rule_7db62e6a2b7c) | isnull(DPD_Overdrawn,0)<0 | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 6-20 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_03 (+2 more span(s)) | 01_nested_block:nested_block | conditions[2]: isnull(DPD_Overdrawn,0)<0 -> UPDATE #DPD SET DPD_Overdrawn=0; table_operations[1]; table_operations[6]; table_operations[17]; tables_read[1]: dbo.Automate_Advances \| READ \| target: Timekey-1 \| WHERE: EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD') IS NOT NULL DROP TABLE #DPD; tables_read[5]: PRO.AccountCal \| READ \| target: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExc…; _(+3 more instance(s) not shown)_ | Verified |
| 4 | Reset negative DPD to zero (rule_6a640ea16c58) | isnull(DPD_Overdue,0)<0 | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 6-20 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_03 (+2 more span(s)) | 01_nested_block:nested_block | conditions[3]: isnull(DPD_Overdue,0)<0 -> UPDATE #DPD SET DPD_Overdue=0; table_operations[1]; table_operations[7]; table_operations[18]; tables_read[1]: dbo.Automate_Advances \| READ \| target: Timekey-1 \| WHERE: EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD') IS NOT NULL DROP TABLE #DPD; tables_read[6]: #DPD \| READ \| target: A.CustomerAcID, CASE WHEN isnull(A.DPD_IntService, 0)>=isnull(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD…; _(+3 more instance(s) not shown)_ | Verified |
| 5 | Reset negative DPD to zero (rule_830d23a31775) | isnull(DPD_Renewal,0)<0 | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Line 63 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_09 (+1 more span(s)) | 01_nested_block:nested_block | conditions[4]: isnull(DPD_Renewal,0)<0 -> UPDATE #DPD SET DPD_Renewal=0; table_operations[8]; table_operations[19]; tables_read[7]: A \| READ \| target: A.DPD_StockStmt, A.DPD_Overdrawn, A.DPD_Overdue, A.DPD_IntService, A.DPD_NoCredit, A.DPD_Renewal \| WHERE: COALESCE(A.DPD_Overdrawn, 0) > 0 OR COALESCE(A.DPD_Overd…; tables_read[17]: PRO.ACCOUNTCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN…; tables_written[5]: #DPD \| UPDATE \| target: DPD_Renewal \| WHERE: COALESCE(DPD_Renewal, 0) < 0; _(+1 more instance(s) not shown)_ | Verified |
| 6 | Reset negative DPD to zero (rule_5f494bf605d8) | isnull(DPD_StockStmt,0)<0 | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 65-72 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_10 | 01_nested_block:nested_block | conditions[5]: isnull(DPD_StockStmt,0)<0 -> UPDATE #DPD SET DPD_StockStmt=0; table_operations[9]; tables_read[8]: A \| READ \| target: N/A \| WHERE: None; tables_written[6]: #DPD \| UPDATE \| target: DPD_StockStmt \| WHERE: isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE | Verified |
| 7 | Assign account-level SMA fields in order (rule_22f53f187b7d) | dpd.DPD_Max BETWEEN 1 AND 30; dpd.DPD_Max BETWEEN 31 AND 60; dpd.DPD_Max BETWEEN 61 AND 90; dpd.DPD_Max > 90; ELSE; A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0); A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 128-226 \| Chunk 01_nested_block_2; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 128-226 \| Chunk 01_nested_block_2 \| Statement 01_nested_block_2:chunk_text_01 (+16 more span(s)) | 01_nested_block_2:nested_block; 01_nested_block_3:nested_block; 01_nested_block_1:nested_block; 01_nested_block:nested_block; 01_nested_block_4:nested_block | conditions[12]: dpd.DPD_Max BETWEEN 1 AND 30 -> 'SMA_0'; decision_chains[2]; table_operations[28]; table_operations[29]; table_operations[30]; table_operations[31]; _(+70 more instance(s) not shown)_ | Verified |
| 8 | Update customer movement history (rule_ca0ccdb75ce3) | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS ) | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block_7; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 1-27 \| Chunk 01_nested_block_7 \| Statement 01_nested_block_7:chunk_text_01 | 01_nested_block_7:nested_block | conditions[37]: AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AN…; table_operations[120]; tables_read[101]: PRO.CUSTOMER_MOVEMENT_HISTORY \| READ \| target: EffectiveToTimeKey, MovementToDate \| WHERE: AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1…; tables_written[81]: PRO.CUSTOMER_MOVEMENT_HISTORY \| UPDATE \| target: EffectiveToTimeKey, MovementToDate \| WHERE: AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELEC… | Verified |
| 9 | Reset negative DPD values to zero (rule_6097f150db38) | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0; COALESCE(DPD_IntService, 0) < 0; [{"column": "DPD_IntService", "expression": "0"}]; UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0; COALESCE(DPD_NoCredit, 0) < 0; [{"column": "D… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Line 55 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_05; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Line 55 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_14 (+11 more span(s)) | 01_nested_block:nested_block | table_operations[4]; table_operations[15]; tables_read[3]: #DPD \| READ \| target: A.CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COA…; tables_read[13]: PRO.ACCOUNTCAL \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_C…; tables_written[1]: #DPD \| UPDATE \| target: DPD_IntService \| WHERE: COALESCE(DPD_IntService, 0) < 0; tables_written[9]: #DPD \| UPDATE \| target: DPD_IntService \| WHERE: isnull(DPD_IntService,0)<0; _(+34 more instance(s) not shown)_ | Needs Review |
| 10 | Propagate customer-level SMA status (rule_17b76dad5b17) | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON= (CASE WHEN A.FACILIT… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 227-268 \| Chunk 01_nested_block_3; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 128-226 \| Chunk 01_nested_block_2 \| Statement 01_nested_block_2:chunk_text_01 (+15 more span(s)) | 01_nested_block_3:nested_block; 01_nested_block_2:nested_block; 01_nested_block_4:nested_block; 01_nested_block_5:nested_block | conditions[27]: ELSE -> 'OTHER'; table_operations[28]; table_operations[29]; table_operations[30]; table_operations[31]; table_operations[32]; _(+48 more instance(s) not shown)_ | Needs Review |
| 11 | Calculate maximum DPD for account (rule_1cb7966427ff) | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0)… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block_1; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 1-9 \| Chunk 01_nested_block_1 \| Statement 01_nested_block_1:chunk_text_01 (+1 more span(s)) | 01_nested_block_1:nested_block | conditions[11]: isnull(A.DPD_Overdrawn,0)>0 OR Isnull(A.DPD_Overdue,0)>0 -> outcome not specified; table_operations[22]; table_operations[23]; table_operations[26]; tables_read[20]: PRO.ACCOUNTCAL \| READ \| target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS \| WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALANC…; tables_read[21]: PRO.CUSTOMERCAL \| READ \| target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS \| WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALAN…; _(+4 more instance(s) not shown)_ | Needs Review |
| 12 | Assign customer movement description by key (rule_7e6059d465d1) | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON= (CASE WHEN A.FACILIT… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 227-268 \| Chunk 01_nested_block_3; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 128-226 \| Chunk 01_nested_block_2 \| Statement 01_nested_block_2:chunk_text_01 (+34 more span(s)) | 01_nested_block_3:nested_block; 01_nested_block_2:nested_block; 01_nested_block_4:nested_block | conditions[27]: ELSE -> 'OTHER'; table_operations[28]; table_operations[29]; table_operations[30]; table_operations[31]; table_operations[32]; _(+119 more instance(s) not shown)_ | Needs Review |
| 13 | Clear SMA fields before reprocessing (rule_800f501f8018) | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM PRO.ACCOUNTCAL A; [{"column": "A.SMA_CLASS", "expression": "NULL"}, {"column": "A.SMA_REASON", "expression": "NULL"}, {"column": "A.SMA_DT", "expression": "NULL"}, {"column":… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 13-17 \| Chunk 01_nested_block_1 \| Statement 01_nested_block_1:chunk_text_02; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 13-17 \| Chunk 01_nested_block_1 \| Statement 01_nested_block_1:embedded_01_04 | 01_nested_block_1:nested_block | table_operations[24]; table_operations[25]; table_operations[27]; tables_read[22]: PRO.ACCOUNTCAL \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS, MI…; tables_read[23]: PRO.ACCOUNTCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS, MIN(A.SMA_D…; tables_read[25]: PRO.PREVSMASTATUS \| READ \| target: @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS \| WHERE: B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,''); _(+2 more instance(s) not shown)_ | Needs Review |
| 14 | Update DPD_Max (rule_3794267c5c42) | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/; [{"column": "A.DPD_Max", "expression": "0"}] | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 98-103 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_12; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 98-103 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_21 | 01_nested_block:nested_block | table_operations[12]; table_operations[13]; table_operations[21]; tables_read[10]: PRO.CUSTOMERCAL \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Accou…; tables_read[11]: AdvAcBasicDetail \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Acco…; tables_read[19]: PRO.SMA_MOVEMENT_HISTORY \| READ \| target: 1 \| WHERE: TIMEKEY=@TIMEKEY) BEGIN; _(+2 more instance(s) not shown)_ | Needs Review |
| 15 | Update SMA_CLASS (rule_046dce107da9) | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END); [{"column": "SMA_CLASS", "expression": "(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 W… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 78-80 \| Chunk 01_nested_block_4 \| Statement 01_nested_block_4:chunk_text_11; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 78-80 \| Chunk 01_nested_block_4 \| Statement 01_nested_block_4:embedded_01_39 | 01_nested_block_4:nested_block | table_operations[52]; table_operations[75]; tables_read[46]: #DPD \| READ \| target: DPD_IntService \| WHERE: isnull(DPD_IntService,0)<0; tables_read[66]: PRO.CUSTOMERCAL \| READ \| target: CustMoveDescription \| WHERE: SYSASSETCLASSALT_KEY = 3; tables_written[30]: #SMACLASS \| UPDATE \| target: SMA_CLASS \| WHERE: None | Needs Review |
| 16 | Update EffectiveToTimeKey, MovementToDate (rule_95a6376b7d82) | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON AA.CustomerAcID=B.Cust… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block_5; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 142-149 \| Chunk 01_nested_block_5 \| Statement 01_nested_block_5:chunk_text_05 (+3 more span(s)) | 01_nested_block_5:nested_block; 01_nested_block_6:nested_block; 01_nested_block_7:nested_block | conditions[35]: AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null -> outcome not specified; table_operations[98]; table_operations[99]; table_operations[100]; table_operations[105]; tables_read[85]: PRO.CUSTOMERCAL \| READ \| target: CustMoveDescription \| WHERE: SYSASSETCLASSALT_KEY=5; _(+7 more instance(s) not shown)_ | Needs Review |
| 17 | Update EffectiveToTimeKey, MovementToDate (rule_a6f6db894bd4) | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B ON AA.SourceSystemCusto… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 137-144 \| Chunk 01_nested_block_6 \| Statement 01_nested_block_6:chunk_text_06; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 137-144 \| Chunk 01_nested_block_6 \| Statement 01_nested_block_6:embedded_01_12 (+2 more span(s)) | 01_nested_block_6:nested_block; 01_nested_block_7:nested_block | table_operations[111]; table_operations[112]; table_operations[113]; table_operations[118]; tables_read[94]: PRO.AccountCal \| READ \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL; tables_read[95]: PRO.AccountCal \| READ \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey…; _(+6 more instance(s) not shown)_ | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 17
- **By rule type:** explicit = 17
- **By validation status:** insufficient_evidence = 9, verified = 8

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 28
- **Deterministic-only facts:** 1
- **LLM-only claims:** 5
- **Conflicts:** 41
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_read (`recon_d89a1d84f1ef`): 01_nested_block_2
- `CONFLICT` tables_read (`recon_d89a1d84f1ef`): 01_nested_block_2
- `LLM_ONLY` tables_read (`recon_e320f048135d`): 01_nested_block_3
- `CONFLICT` tables_read (`recon_e7f00de18fe3`): 01_nested_block_3
- `CONFLICT` tables_read (`recon_8e18c45a70af`): 01_nested_block_4

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 0/100
- **Statement coverage:** 83 / 120 (69.2%)
- **Rule grounding coverage:** 15 / 17 (88.2%)
- **Conflicts:** 41
- **Contradictions:** 64
- **Review required items:** 110
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

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID,  
RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNo...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE   A SET A.DPD_Max= (CASE    WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntServic...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.FLGSMA=NULL  
             ,A.SMA_CLASS_KEY=NULL  
       ,A.SMA_DT=NULL  
     FROM PRO.CUSTOMERCAL A...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE PRO.AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL  
    
  
  
 --IF O...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE AA  
 SET   
   EffectiveToTimeKey = @vEffectiveto  
    ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE AA  
SET   
 EffectiveToTimeKey = @vEffectiveto  
,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE PRO.ACLRUNNINGPROCESSSTATUS   
SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNU...
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "DPD_IntService", "expression": "0"}], [{"column": "DPD_NoCredit", "expression": "0"}], [{"column": "DPD_Overdrawn", "expression": "0"}], [{"column": "DPD_Overdue", "expression": "0"}], [{"column": "DPD_Renewal", "expression": "0"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "SMA_CLASS", "expression": "'STD'"}], [{"column": "SMA_CLASS", "expression": "'SUB'"}], [{"column": "SMA_CLASS", "expression": "'DB1'"}], [{"column": "SMA_CLASS", "expression": "'DB2'"}], [{"column": "SMA_CLASS", "expression": "'DB3'"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "A.DPD_Max", "expression": "(CASE WHEN (COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_NoCredit, 0) AND COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_Overdrawn, 0) AND COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_Overdue, 0) AND COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_Renewal, 0) AND COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_IntService, 0) WHEN (COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_IntService, 0) AND COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_Overdrawn, 0) AND COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_Overdue, 0) AND COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_Renewal, 0) AND COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_NoCredit, 0) WHEN (COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_NoCredit, 0) AND COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_IntService, 0) AND COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_Overdue, 0) AND COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_Renewal, 0) AND COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_Overdrawn, 0) WHEN (COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_NoCredit, 0) AND COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_IntService, 0) AND COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_Overdrawn, 0) AND COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_Overdue, 0) AND COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_Renewal, 0) WHEN (COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_NoCredit, 0) AND COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_IntService, 0) AND COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_Overdrawn, 0) AND COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_Renewal, 0) AND COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_Overdue, 0) ELSE COALESCE(A.DPD_StockStmt, 0) END)"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "A.FLGSMA", "expression": "NULL"}, {"column": "A.SMA_CLASS_KEY", "expression": "NULL"}, {"column": "A.SMA_DT", "expression": "NULL"}], [{"column": "A.SMA_CLASS_KEY", "expression": "B.MAXSMA_CLASS"}, {"column": "A.SMA_DT", "expression": "B.SMA_Dt"}], [{"column": "CustMoveDescription", "expression": "'SMA_0'"}], [{"column": "CustMoveDescription", "expression": "'SMA_1'"}], [{"column": "CustMoveDescription", "expression": "'SMA_2'"}], [{"column": "CustMoveDescription", "expression": "'STD'"}], [{"column": "CustMoveDescription", "expression": "'SUB'"}], [{"column": "CustMoveDescription", "expression": "'DB1'"}], [{"column": "CustMoveDescription", "expression": "'DB2'"}], [{"column": "CustMoveDescription", "expression": "'DB3'"}], [{"column": "CustMoveDescription", "expression": "'LOS'"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "A.SMA_CLASS", "expression": "NULL"}, {"column": "A.SMA_REASON", "expression": "NULL"}, {"column": "A.SMA_DT", "expression": "NULL"}, {"column": "A.FLGSMA", "expression": "NULL"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "A.DPD_Max", "expression": "0"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "SMA_CLASS", "expression": "(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE SMA_CLASS END)"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "EffectiveToTimeKey", "expression": "@vEffectiveto"}, {"column": "MovementToDate", "expression": "DATEADD(DAY, -1, @ProcessDate)"}]
