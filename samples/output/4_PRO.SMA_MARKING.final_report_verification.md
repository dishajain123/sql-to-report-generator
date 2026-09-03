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
| Prompt Version | `2203cd718d4b2038` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `f460ffa9a400079ae1cc7050278c39538a2ec22f1ba51bf01f10cd35065bb02d` |
| Configuration Version | `56aad373bf8755e7` |
| Run Timestamp | `2026-09-02T11:18:34.375705+00:00` |
| Object ID | `obj_7bd00a4d3ff9` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_adf4df286501` |
| Total LLM Calls | `12` |
| Successful Calls | `12` |
| Failed Calls | `0` |
| Prompt Tokens | `85961` |
| Completion Tokens | `19214` |
| Total Tokens | `105175` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 11 | 11 | 0 | 56607 | available |
| synthesis | 1 | 1 | 0 | 48568 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Reset negative DPD to zero [CONFLICT] (`rule_3d914a7c3c49`) | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_StockStmt` | Ensures that negative overdue days are reset to zero. |
| 🔴 2 | Calculate DPD_IntService [CONFLICT] (`rule_5a14c3d412e6`) | `DPD_IntService` | The DPD_IntService is calculated. |
| 🔴 3 | Calculate DPD_NoCredit [CONFLICT] (`rule_dbafe13078fe`) | `DPD_NoCredit` | The DPD_NoCredit is calculated. |
| 🔴 4 | Calculate DPD_Overdrawn [CONFLICT] (`rule_aac512f78ca3`) | `DPD_Overdrawn` | The DPD_Overdrawn is calculated. |
| 🔴 5 | Calculate DPD_Overdue [CONFLICT] (`rule_43726b0af424`) | `DPD_Overdue` | The DPD_Overdue is calculated. |
| 🔴 6 | Calculate DPD_Renewal [CONFLICT] (`rule_682510a107f9`) | `DPD_Renewal` | The DPD_Renewal is calculated. |
| 🔴 7 | Calculate DPD_StockStmt [CONFLICT] (`rule_5a6e91aebbd7`) | `DPD_StockStmt` | The DPD_StockStmt is calculated. |
| 🔴 8 | Assign account-level SMA fields in order [CONFLICT] (`rule_d2d38cfca5e4`) | `SMA_CLASS` | The account-level SMA fields in order is assigned. |
| 🟠 9 | Update SMA movement history [LLM_ONLY] (`rule_19f62c052dae`) | `TIMEKEY` | Updates the SMA movement history record for the specified time key. |
| 🔴 10 | Insert SMA movement history [CONFLICT] (`rule_9e961415d3d5`) | `Not specified` | Inserts a new SMA movement history record if the current status differs from the previous status. |
| 🔴 11 | Update account movement history [CONFLICT] (`rule_a92faaf92f30`) | `EffectiveToTimeKey` | Updates the effective to time key and movement to date for account movement history records. |
| 🔴 12 | Reset negative DPD values to zero [CONFLICT] (`rule_6097f150db38`) | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | Negative overdue-day values are reset to zero before the maximum overdue days is calculated. |
| 🔴 13 | Propagate customer-level SMA status [CONFLICT] (`rule_17b76dad5b17`) | `FLGSMA, SMA_DT` | Propagate customer-level SMA status. |
| 🔴 14 | Assign customer movement description by key [CONFLICT] (`rule_7e6059d465d1`) | `CustMoveDescription` | Customer-level SMA status is aggregated from linked SMA-marked accounts. Customer movement descriptions are assigned from the applicable as… |
| 🔴 15 | Clear SMA fields before reprocessing [CONFLICT] (`rule_800f501f8018`) | `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA` | Existing SMA classification fields are cleared before the account is reprocessed. |
| 🟠 16 | Update DPD_Max [MATCHED] (`rule_3794267c5c42`) | `DPD_Max` | The procedure sets DPD_Max to the source-defined value. |
| 🟠 17 | Update DPD_Max [MATCHED] (`rule_515e102afe3f`) | `DPD_Max` | The procedure sets DPD_Max to the source-defined value when COALESCE(A.DPD_Overdrawn, 0) > 0 OR COALESCE(A.DPD_Overdue, 0) > 0. |
| 🟠 18 | Update SMA_CLASS [MATCHED] (`rule_046dce107da9`) | `SMA_CLASS` | The procedure sets SMA_CLASS to the source-defined value. |
| 🔴 19 | Update EffectiveToTimeKey, MovementToDate [CONFLICT] (`rule_95a6376b7d82`) | `EffectiveToTimeKey, MovementToDate` | The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS… |
| 🔴 20 | Update EffectiveToTimeKey, MovementToDate [CONFLICT] (`rule_a6f6db894bd4`) | `EffectiveToTimeKey, MovementToDate` | The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCust… |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Reset negative DPD to zero (rule_3d914a7c3c49) | isnull(DPD_IntService,0)<0; isnull(DPD_NoCredit,0)<0; isnull(DPD_Overdrawn,0)<0; isnull(DPD_Overdue,0)<0; isnull(DPD_StockStmt,0)<0 | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Line 55 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_05 (+9 more span(s)) | 01_nested_block:nested_block | conditions[1]: isnull(DPD_IntService,0)<0 -> UPDATE #DPD SET DPD_IntService=0; table_operations[4]; table_operations[15]; tables_read[3]: #DPD \| READ \| target: A.CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COA…; tables_read[13]: PRO.ACCOUNTCAL \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_C…; tables_written[1]: #DPD \| UPDATE \| target: DPD_IntService \| WHERE: COALESCE(DPD_IntService, 0) < 0; _(+28 more instance(s) not shown)_ | Verified |
| 2 | Calculate DPD_IntService (rule_5a14c3d412e6) | isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 75-95 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_11 (+1 more span(s)) | 01_nested_block:nested_block | conditions[7]: isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) OR isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) OR isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn,0) OR i…; table_operations[10]; table_operations[11]; table_operations[20]; tables_read[9]: A \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.A…; tables_read[18]: PRO.CUSTOMERCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MI…; _(+1 more instance(s) not shown)_ | Verified |
| 3 | Calculate DPD_NoCredit (rule_dbafe13078fe) | isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 END DPD_NoCredit | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 75-95 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_11 (+1 more span(s)) | 01_nested_block:nested_block | conditions[7]: isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) OR isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) OR isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn,0) OR i…; table_operations[10]; table_operations[11]; table_operations[20]; tables_read[9]: A \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.A…; tables_read[18]: PRO.CUSTOMERCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MI…; _(+1 more instance(s) not shown)_ | Verified |
| 4 | Calculate DPD_Overdrawn (rule_aac512f78ca3) | isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn,0) THEN A.DPD_Overdrawn ELSE 0 END DPD_Overdrawn | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 75-95 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_11 (+1 more span(s)) | 01_nested_block:nested_block | conditions[7]: isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) OR isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) OR isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn,0) OR i…; table_operations[10]; table_operations[11]; table_operations[20]; tables_read[9]: A \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.A…; tables_read[18]: PRO.CUSTOMERCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MI…; _(+1 more instance(s) not shown)_ | Verified |
| 5 | Calculate DPD_Overdue (rule_43726b0af424) | isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue,0) THEN A.DPD_Overdue ELSE 0 END DPD_Overdue | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 75-95 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_11 (+1 more span(s)) | 01_nested_block:nested_block | conditions[7]: isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) OR isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) OR isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn,0) OR i…; table_operations[10]; table_operations[11]; table_operations[20]; tables_read[9]: A \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.A…; tables_read[18]: PRO.CUSTOMERCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MI…; _(+1 more instance(s) not shown)_ | Verified |
| 6 | Calculate DPD_Renewal (rule_682510a107f9) | isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview,0) THEN A.DPD_Renewal ELSE 0 END DPD_Renewal | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 75-95 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_11 (+1 more span(s)) | 01_nested_block:nested_block | conditions[7]: isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) OR isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) OR isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn,0) OR i…; table_operations[10]; table_operations[11]; table_operations[20]; tables_read[9]: A \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.A…; tables_read[18]: PRO.CUSTOMERCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MI…; _(+1 more instance(s) not shown)_ | Verified |
| 7 | Calculate DPD_StockStmt (rule_5a6e91aebbd7) | isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) THEN A.DPD_StockStmt ELSE 0 END DPD_StockStmt | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 75-95 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_11 (+1 more span(s)) | 01_nested_block:nested_block | conditions[7]: isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) OR isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) OR isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn,0) OR i…; table_operations[10]; table_operations[11]; table_operations[20]; tables_read[9]: A \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.A…; tables_read[18]: PRO.CUSTOMERCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MI…; _(+1 more instance(s) not shown)_ | Verified |
| 8 | Assign account-level SMA fields in order (rule_d2d38cfca5e4) | dpd.DPD_Max BETWEEN 1 AND 30; dpd.DPD_Max BETWEEN 31 AND 60; dpd.DPD_Max BETWEEN 61 AND 90; dpd.DPD_Max > 90; dpd.DPD_MAX BETWEEN 276 AND 305; dpd.DPD_MAX BETWEEN 306 AND 335; dpd.DPD_MAX BETWEEN 336 AND 365; dpd.DPD_MAX >= 366; A.FACILITYTYPE IN ('CC','OD')… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 128-226 \| Chunk 01_nested_block_2; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 128-226 \| Chunk 01_nested_block_2 \| Statement 01_nested_block_2:chunk_text_01 (+17 more span(s)) | 01_nested_block_2:nested_block; 01_nested_block_3:nested_block; 01_nested_block:nested_block; 01_nested_block_1:nested_block; 01_nested_block_4:nested_block | conditions[13]: dpd.DPD_Max BETWEEN 1 AND 30 -> 'SMA_0'; table_operations[28]; table_operations[29]; table_operations[30]; table_operations[31]; table_operations[32]; _(+81 more instance(s) not shown)_ | Needs Review |
| 9 | Update SMA movement history (rule_19f62c052dae) | EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block_4; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 54-61 \| Chunk 01_nested_block_4 \| Statement 01_nested_block_4:chunk_text_07 | 01_nested_block_4:nested_block | conditions[38]: EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) -> DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY; table_operations[46]; table_operations[47]; tables_read[42]: #DPD \| READ \| target: DPD_Overdue \| WHERE: COALESCE(DPD_Overdue, 0) < 0; tables_read[43]: #DPD \| READ \| target: DPD_Renewal \| WHERE: COALESCE(DPD_Renewal, 0) < 0; tables_written[27]: PRO.CUSTOMERCAL \| UPDATE \| target: A.SMA_CLASS_KEY, A.SMA_DT \| WHERE: A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN | Needs Review |
| 10 | Insert SMA movement history (rule_9e961415d3d5) | B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block_4; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 83-87 \| Chunk 01_nested_block_4 \| Statement 01_nested_block_4:chunk_text_12 (+1 more span(s)) | 01_nested_block_4:nested_block | conditions[39]: B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') -> INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) SELECT @TIMEKEY,B.Cu…; table_operations[53]; table_operations[76]; table_operations[77]; tables_read[67]: PRO.CUSTOMERCAL \| READ \| target: CustMoveDescription \| WHERE: SYSASSETCLASSALT_KEY = 4; tables_written[31]: PRO.SMA_MOVEMENT_HISTORY \| INSERT \| target: TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS \| WHERE: None | Needs Review |
| 11 | Update account movement history (rule_a92faaf92f30) | AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Chunk 01_nested_block_5; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 142-149 \| Chunk 01_nested_block_5 \| Statement 01_nested_block_5:chunk_text_05 (+1 more span(s)) | 01_nested_block_5:nested_block | conditions[43]: AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null -> UPDATE AA SET EffectiveToTimeKey = @vEffectiveto, MovementToDate=DATEADD(DD,-1,@ProcessDate); table_operations[98]; table_operations[99]; table_operations[100]; table_operations[105]; tables_read[85]: PRO.CUSTOMERCAL \| READ \| target: CustMoveDescription \| WHERE: SYSASSETCLASSALT_KEY=5; _(+5 more instance(s) not shown)_ | Verified |
| 12 | Reset negative DPD values to zero (rule_6097f150db38) | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0; COALESCE(DPD_IntService, 0) < 0; [{"column": "DPD_IntService", "expression": "0"}]; UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0; COALESCE(DPD_NoCredit, 0) < 0; [{"column": "D… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Line 55 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_05; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Line 55 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_14 (+11 more span(s)) | 01_nested_block:nested_block | table_operations[4]; table_operations[15]; tables_read[3]: #DPD \| READ \| target: A.CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COA…; tables_read[13]: PRO.ACCOUNTCAL \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_C…; tables_written[1]: #DPD \| UPDATE \| target: DPD_IntService \| WHERE: COALESCE(DPD_IntService, 0) < 0; tables_written[9]: #DPD \| UPDATE \| target: DPD_IntService \| WHERE: isnull(DPD_IntService,0)<0; _(+34 more instance(s) not shown)_ | Needs Review |
| 13 | Propagate customer-level SMA status (rule_17b76dad5b17) | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON= (CASE WHEN A.FACILIT… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 227-268 \| Chunk 01_nested_block_3; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 128-226 \| Chunk 01_nested_block_2 \| Statement 01_nested_block_2:chunk_text_01 (+13 more span(s)) | 01_nested_block_3:nested_block; 01_nested_block_2:nested_block; 01_nested_block_4:nested_block; 01_nested_block_5:nested_block | conditions[34]: ELSE -> 'OTHER'; table_operations[28]; table_operations[29]; table_operations[30]; table_operations[31]; table_operations[32]; _(+46 more instance(s) not shown)_ | Needs Review |
| 14 | Assign customer movement description by key (rule_7e6059d465d1) | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON= (CASE WHEN A.FACILIT… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 227-268 \| Chunk 01_nested_block_3; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 128-226 \| Chunk 01_nested_block_2 \| Statement 01_nested_block_2:chunk_text_01 (+34 more span(s)) | 01_nested_block_3:nested_block; 01_nested_block_2:nested_block; 01_nested_block_4:nested_block | conditions[34]: ELSE -> 'OTHER'; table_operations[28]; table_operations[29]; table_operations[30]; table_operations[31]; table_operations[32]; _(+118 more instance(s) not shown)_ | Needs Review |
| 15 | Clear SMA fields before reprocessing (rule_800f501f8018) | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM PRO.ACCOUNTCAL A; [{"column": "A.SMA_CLASS", "expression": "NULL"}, {"column": "A.SMA_REASON", "expression": "NULL"}, {"column": "A.SMA_DT", "expression": "NULL"}, {"column":… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 13-17 \| Chunk 01_nested_block_1 \| Statement 01_nested_block_1:chunk_text_02; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 13-17 \| Chunk 01_nested_block_1 \| Statement 01_nested_block_1:embedded_01_04 | 01_nested_block_1:nested_block | table_operations[24]; table_operations[25]; table_operations[27]; tables_read[22]: PRO.ACCOUNTCAL \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS, MI…; tables_read[23]: PRO.ACCOUNTCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS, MIN(A.SMA_D…; tables_read[25]: PRO.PREVSMASTATUS \| READ \| target: @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS \| WHERE: B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,''); _(+2 more instance(s) not shown)_ | Needs Review |
| 16 | Update DPD_Max (rule_3794267c5c42) | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/; [{"column": "A.DPD_Max", "expression": "0"}] | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 98-103 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_12; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 98-103 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_21 | 01_nested_block:nested_block | table_operations[12]; table_operations[13]; table_operations[21]; tables_read[10]: PRO.CUSTOMERCAL \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Accou…; tables_read[11]: AdvAcBasicDetail \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Acco…; tables_read[19]: PRO.SMA_MOVEMENT_HISTORY \| READ \| target: 1 \| WHERE: TIMEKEY=@TIMEKEY) BEGIN; _(+2 more instance(s) not shown)_ | Needs Review |
| 17 | Update DPD_Max (rule_515e102afe3f) | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0)… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 1-9 \| Chunk 01_nested_block_1 \| Statement 01_nested_block_1:chunk_text_01; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 1-9 \| Chunk 01_nested_block_1 \| Statement 01_nested_block_1:embedded_01_03 (+1 more span(s)) | 01_nested_block_1:nested_block | table_operations[22]; table_operations[23]; table_operations[26]; tables_read[20]: PRO.ACCOUNTCAL \| READ \| target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS \| WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALANC…; tables_read[21]: PRO.CUSTOMERCAL \| READ \| target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS \| WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALAN…; tables_read[24]: PRO.ACCOUNTCAL \| READ \| target: A.CustomerAcID, ISNULL(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) SMA_CLASS INTO #SMACLASS \| WHERE: B.FLGSMA='Y' AND ISNULL(A.…; _(+3 more instance(s) not shown)_ | Needs Review |
| 18 | Update SMA_CLASS (rule_046dce107da9) | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END); [{"column": "SMA_CLASS", "expression": "(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 W… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 78-80 \| Chunk 01_nested_block_4 \| Statement 01_nested_block_4:chunk_text_11; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 78-80 \| Chunk 01_nested_block_4 \| Statement 01_nested_block_4:embedded_01_39 (+1 more span(s)) | 01_nested_block_4:nested_block | table_operations[52]; table_operations[75]; tables_read[46]: #DPD \| READ \| target: DPD_IntService \| WHERE: isnull(DPD_IntService,0)<0; tables_read[66]: PRO.CUSTOMERCAL \| READ \| target: CustMoveDescription \| WHERE: SYSASSETCLASSALT_KEY = 3; tables_written[30]: #SMACLASS \| UPDATE \| target: SMA_CLASS \| WHERE: None; calculations[12]: metric not specified \| explanation not specified | Needs Review |
| 19 | Update EffectiveToTimeKey, MovementToDate (rule_95a6376b7d82) | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON AA.CustomerAcID=B.Cust… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 142-149 \| Chunk 01_nested_block_5 \| Statement 01_nested_block_5:chunk_text_05; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 142-149 \| Chunk 01_nested_block_5 \| Statement 01_nested_block_5:embedded_01_10 (+3 more span(s)) | 01_nested_block_5:nested_block; 01_nested_block_6:nested_block; 01_nested_block_7:nested_block | table_operations[98]; table_operations[99]; table_operations[100]; table_operations[105]; tables_read[85]: PRO.CUSTOMERCAL \| READ \| target: CustMoveDescription \| WHERE: SYSASSETCLASSALT_KEY=5; tables_read[86]: PRO.CUSTOMERCAL \| READ \| target: CustMoveDescription \| WHERE: SYSASSETCLASSALT_KEY=6; _(+7 more instance(s) not shown)_ | Needs Review |
| 20 | Update EffectiveToTimeKey, MovementToDate (rule_a6f6db894bd4) | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B ON AA.SourceSystemCusto… | /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 137-144 \| Chunk 01_nested_block_6 \| Statement 01_nested_block_6:chunk_text_06; /Users/dishajain/Downloads/proc project/TEST PROC/PRO.SMA_MARKING_12122023.StoredProcedure.sql \| Lines 137-144 \| Chunk 01_nested_block_6 \| Statement 01_nested_block_6:embedded_01_12 (+2 more span(s)) | 01_nested_block_6:nested_block; 01_nested_block_7:nested_block | table_operations[111]; table_operations[112]; table_operations[113]; table_operations[118]; tables_read[94]: PRO.AccountCal \| READ \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL; tables_read[95]: PRO.AccountCal \| READ \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey…; _(+8 more instance(s) not shown)_ | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 20
- **By rule type:** explicit = 20
- **By validation status:** insufficient_evidence = 12, verified = 8

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 32
- **Deterministic-only facts:** 1
- **LLM-only claims:** 3
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
- **Quality score:** 6/100
- **Statement coverage:** 83 / 120 (69.2%)
- **Rule grounding coverage:** 19 / 20 (95.0%)
- **Conflicts:** 41
- **Contradictions:** 63
- **Review required items:** 107
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
- The supporting technical evidence was low-confidence and should not be presented as fully verified: A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0), A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0), A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0), A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0), ELSE
- The supporting technical evidence was low-confidence and should not be presented as fully verified: EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY)
- The supporting technical evidence was low-confidence and should not be presented as fully verified: B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'')
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "DPD_IntService", "expression": "0"}], [{"column": "DPD_NoCredit", "expression": "0"}], [{"column": "DPD_Overdrawn", "expression": "0"}], [{"column": "DPD_Overdue", "expression": "0"}], [{"column": "DPD_Renewal", "expression": "0"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "SMA_CLASS", "expression": "'STD'"}], [{"column": "SMA_CLASS", "expression": "'SUB'"}], [{"column": "SMA_CLASS", "expression": "'DB1'"}], [{"column": "SMA_CLASS", "expression": "'DB2'"}], [{"column": "SMA_CLASS", "expression": "'DB3'"}]
- The supporting technical evidence was low-confidence and should not be presented as fully verified: UPDATE A SET A.SMA_CLASS=  
   (CASE  WHEN dpd.DPD_Max  BETWEEN 1 AND 30  THEN 'SMA_0'  
       WHEN dpd.DPD_Max  BETWEEN 31 AND 60  THEN 'SMA_1'  
    WHEN dpd.DPD_Max  BETWEEN 61 AND 90  THEN 'SMA_2'  
    WHEN dpd.DPD_Max >90 THEN 'SMA_2'  
    ELSE NULL  
    END)  
,A.SMA_REASON= (CASE   
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED'  
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY NO CREDIT'  
      WHEN A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) THEN  'DEGRADE BY OVERDUE'  
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 THEN 'DEGRADE BY CONTI EXCESS'  
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY STOCK STATEMENT'  
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY REVIEW DUE DATE'  
        
      ELSE 'OTHER'  
     END)  
,A.SMA_DT=   DATEADD(DAY, -dpd.DPD_MAX+1 ,@ProcessDate)  
,A.FLGSMA='Y'  
FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B ON A.CustomerEntityID=B.CustomerEntityID  
INNER JOIN AdvAcBasicDetail ABD  
   ON A.AccountEntityID=ABD.AccountEntityId  
   AND (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY)  
      --AND ABD.ReferencePeriod=91   
 INNER JOIN #DPD dpd on dpd.AccountEntityId=a.AccountEntityId  
   --LEFT JOIN DIMPRODUCT C ON C.PRODUCTALT_KEY=A.PRODUCTALT_KEY     
   --AND ISNULL(C.PRODUCTGROUP,'N')<>'KCC'    
   --AND isnull(C.ProductSubGroup,'N') NOT in('KCC')  
   --and c.NPANorms='DPD91'  
   --AND (C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY)  
WHERE ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1  
 AND ISNULL(A.BALANCE,0)>0   
 and A.ASSET_NORM<>'ALWYS_STD'  
AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 )   
AND ISNULL(DPD.DPD_MAX,0)>0   
  
  
  
------UPDATE A SET A.SMA_CLASS=  
------   (CASE  WHEN dpd.DPD_Max  BETWEEN 31 AND 60  THEN 'SMA_0'  
------       WHEN dpd.DPD_Max  BETWEEN 61 AND 90  THEN 'SMA_1'  
------    WHEN dpd.DPD_Max  BETWEEN 91 AND 180  THEN 'SMA_2'  
------    WHEN dpd.DPD_Max >180 THEN 'SMA_2'  
------    ELSE NULL  
------    END)  
------,A.SMA_REASON= (CASE   
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED'  
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY NO CREDIT'  
------      WHEN A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) THEN  'DEGRADE BY OVERDUE'  
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30  THEN 'DEGRADE BY CONTI EXCESS'  
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY STOCK STATEMENT'  
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY REVIEW DUE DATE'  
        
------      ELSE 'OTHER'  
------     END)  
------,A.SMA_DT=   DATEADD(DAY, -dpd.DPD_MAX+1 ,@ProcessDate)  
------,A.FLGSMA='Y'  
------FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B ON A.CustomerEntityID=B.CustomerEntityID  
------INNER JOIN AdvAcBasicDetail ABD  
------   ON A.AccountEntityID=ABD.AccountEntityId  
------   AND (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY)  
------      AND ABD.ReferencePeriod=181   
------ INNER JOIN #DPD dpd on dpd.AccountEntityId=a.AccountEntityId  
------   --LEFT JOIN DIMPRODUCT C ON C.PRODUCTALT_KEY=A.PRODUCTALT_KEY     
------   --AND ISNULL(C.PRODUCTGROUP,'N')<>'KCC'    
------   --AND isnull(C.ProductSubGroup,'N') NOT in('KCC')  
------   --and c.NPANorms='DPD91'  
------   --AND (C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY)  
------WHERE ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1  
------ AND ISNULL(A.BALANCE,0)>0   
------ and A.ASSET_NORM<>'ALWYS_STD'  
------AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 )   
----------AND ISNULL(DPD.DPD_MAX,0)>0  
------AND ISNULL(DPD.DPD_MAX,0)>30  
  
  
  
  
--------UPDATE A SET A.SMA_CLASS= (  
--------                              CASE WHEN A.FACILITYTYPE IN('CC','OD') THEN ( CASE WHEN  REFPERIODOVERDRAWN-60>=DPD_MAX  
--------                                                              THEN 'SMA_0'  
--------                                                         WHEN REFPERIODOVERDRAWN-30>=DPD_MAX  THEN 'SMA_1'  
--------                       ELSE 'SMA_2' END)   
--------                              ELSE ( CASE WHEN  REFPERIODOVERDUE-60>=DPD_MAX  
--------                                                              THEN 'SMA_0'  
--------                                                         WHEN REFPERIODOVERDUE-30>=DPD_MAX  THEN 'SMA_1'  
--------                       ELSE 'SMA_2' END)  
--------         END)  
  
------UPDATE A SET A.SMA_CLASS=  
------   (CASE  WHEN dpd.DPD_MAX  BETWEEN 276 AND 305  THEN 'SMA_0'  
------       WHEN dpd.DPD_MAX  BETWEEN 306 AND 335  THEN 'SMA_1'  
------    WHEN dpd.DPD_MAX  BETWEEN 336 AND 365  THEN 'SMA_2'  
------    WHEN dpd.DPD_MAX >=366 THEN 'SMA_2'  
------    ELSE NULL  
------    END)  
  
------   ,A.SMA_REASON= (CASE   
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(DPD.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED', [{"column": "A.SMA_CLASS", "expression": "(CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max > 90 THEN 'SMA_2' ELSE NULL END)"}, {"column": "A.SMA_REASON", "expression": "(CASE WHEN A.FACILITYTYPE IN ('CC', 'OD') AND COALESCE(DPD.DPD_INTSERVICE, 0) = COALESCE(dpd.DPD_MAX, 0) THEN 'DEGRADE BY INT NOT SERVICED' WHEN A.FACILITYTYPE IN ('CC', 'OD') AND COALESCE(DPD.DPD_NOCREDIT, 0) = COALESCE(dpd.DPD_MAX, 0) THEN 'DEGRADE BY NO CREDIT' WHEN A.FACILITYTYPE IN ('TL', 'DL', 'BP', 'BD', 'PC') AND COALESCE(dpd.DPD_OVERDUE, 0) = COALESCE(dpd.DPD_MAX, 0) THEN 'DEGRADE BY OVERDUE' WHEN A.FACILITYTYPE IN ('CC', 'OD') AND COALESCE(dpd.DPD_OVERDRAWN, 0) = COALESCE(dpd.DPD_MAX, 0) AND COALESCE(dpd.DPD_OVERDRAWN, 0) > 30 THEN 'DEGRADE BY CONTI EXCESS' WHEN A.FACILITYTYPE IN ('CC', 'OD') AND COALESCE(DPD.DPD_STOCKSTMT, 0) = COALESCE(dpd.DPD_MAX, 0) THEN 'DEGRADE BY STOCK STATEMENT' WHEN A.FACILITYTYPE IN ('CC', 'OD') AND COALESCE(DPD.DPD_RENEWAL, 0) = COALESCE(dpd.DPD_MAX, 0) THEN 'DEGRADE BY REVIEW DUE DATE' ELSE 'OTHER' END)"}, {"column": "A.SMA_DT", "expression": "DATEADD(DAY, -dpd.DPD_MAX + 1, @ProcessDate)"}, {"column": "A.FLGSMA", "expression": "'Y'"}], UPDATE PRO.AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL, FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL, UPDATE PRO.AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL, FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL, UPDATE PRO.AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL, FinalAssetClassAlt_Key = 3 AND SMA_CLASS IS NULL, UPDATE PRO.AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL, FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL, UPDATE PRO.AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL, FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL, FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL, FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL, FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL, FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL, FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "A.FLGSMA", "expression": "NULL"}, {"column": "A.SMA_CLASS_KEY", "expression": "NULL"}, {"column": "A.SMA_DT", "expression": "NULL"}], [{"column": "A.SMA_CLASS_KEY", "expression": "B.MAXSMA_CLASS"}, {"column": "A.SMA_DT", "expression": "B.SMA_Dt"}], [{"column": "CustMoveDescription", "expression": "'SMA_0'"}], [{"column": "CustMoveDescription", "expression": "'SMA_1'"}], [{"column": "CustMoveDescription", "expression": "'SMA_2'"}], [{"column": "CustMoveDescription", "expression": "'STD'"}], [{"column": "CustMoveDescription", "expression": "'SUB'"}], [{"column": "CustMoveDescription", "expression": "'DB1'"}], [{"column": "CustMoveDescription", "expression": "'DB2'"}], [{"column": "CustMoveDescription", "expression": "'DB3'"}], [{"column": "CustMoveDescription", "expression": "'LOS'"}]
- The supporting technical evidence was low-confidence and should not be presented as fully verified: UPDATE A SET A.SMA_CLASS=  
   (CASE  WHEN dpd.DPD_Max  BETWEEN 1 AND 30  THEN 'SMA_0'  
       WHEN dpd.DPD_Max  BETWEEN 31 AND 60  THEN 'SMA_1'  
    WHEN dpd.DPD_Max  BETWEEN 61 AND 90  THEN 'SMA_2'  
    WHEN dpd.DPD_Max >90 THEN 'SMA_2'  
    ELSE NULL  
    END)  
,A.SMA_REASON= (CASE   
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED'  
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY NO CREDIT'  
      WHEN A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) THEN  'DEGRADE BY OVERDUE'  
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 THEN 'DEGRADE BY CONTI EXCESS'  
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY STOCK STATEMENT'  
      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY REVIEW DUE DATE'  
        
      ELSE 'OTHER'  
     END)  
,A.SMA_DT=   DATEADD(DAY, -dpd.DPD_MAX+1 ,@ProcessDate)  
,A.FLGSMA='Y'  
FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B ON A.CustomerEntityID=B.CustomerEntityID  
INNER JOIN AdvAcBasicDetail ABD  
   ON A.AccountEntityID=ABD.AccountEntityId  
   AND (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY)  
      --AND ABD.ReferencePeriod=91   
 INNER JOIN #DPD dpd on dpd.AccountEntityId=a.AccountEntityId  
   --LEFT JOIN DIMPRODUCT C ON C.PRODUCTALT_KEY=A.PRODUCTALT_KEY     
   --AND ISNULL(C.PRODUCTGROUP,'N')<>'KCC'    
   --AND isnull(C.ProductSubGroup,'N') NOT in('KCC')  
   --and c.NPANorms='DPD91'  
   --AND (C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY)  
WHERE ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1  
 AND ISNULL(A.BALANCE,0)>0   
 and A.ASSET_NORM<>'ALWYS_STD'  
AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 )   
AND ISNULL(DPD.DPD_MAX,0)>0   
  
  
  
------UPDATE A SET A.SMA_CLASS=  
------   (CASE  WHEN dpd.DPD_Max  BETWEEN 31 AND 60  THEN 'SMA_0'  
------       WHEN dpd.DPD_Max  BETWEEN 61 AND 90  THEN 'SMA_1'  
------    WHEN dpd.DPD_Max  BETWEEN 91 AND 180  THEN 'SMA_2'  
------    WHEN dpd.DPD_Max >180 THEN 'SMA_2'  
------    ELSE NULL  
------    END)  
------,A.SMA_REASON= (CASE   
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED'  
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY NO CREDIT'  
------      WHEN A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) THEN  'DEGRADE BY OVERDUE'  
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30  THEN 'DEGRADE BY CONTI EXCESS'  
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY STOCK STATEMENT'  
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY REVIEW DUE DATE'  
        
------      ELSE 'OTHER'  
------     END)  
------,A.SMA_DT=   DATEADD(DAY, -dpd.DPD_MAX+1 ,@ProcessDate)  
------,A.FLGSMA='Y'  
------FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B ON A.CustomerEntityID=B.CustomerEntityID  
------INNER JOIN AdvAcBasicDetail ABD  
------   ON A.AccountEntityID=ABD.AccountEntityId  
------   AND (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY)  
------      AND ABD.ReferencePeriod=181   
------ INNER JOIN #DPD dpd on dpd.AccountEntityId=a.AccountEntityId  
------   --LEFT JOIN DIMPRODUCT C ON C.PRODUCTALT_KEY=A.PRODUCTALT_KEY     
------   --AND ISNULL(C.PRODUCTGROUP,'N')<>'KCC'    
------   --AND isnull(C.ProductSubGroup,'N') NOT in('KCC')  
------   --and c.NPANorms='DPD91'  
------   --AND (C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY)  
------WHERE ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1  
------ AND ISNULL(A.BALANCE,0)>0   
------ and A.ASSET_NORM<>'ALWYS_STD'  
------AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 )   
----------AND ISNULL(DPD.DPD_MAX,0)>0  
------AND ISNULL(DPD.DPD_MAX,0)>30  
  
  
  
  
--------UPDATE A SET A.SMA_CLASS= (  
--------                              CASE WHEN A.FACILITYTYPE IN('CC','OD') THEN ( CASE WHEN  REFPERIODOVERDRAWN-60>=DPD_MAX  
--------                                                              THEN 'SMA_0'  
--------                                                         WHEN REFPERIODOVERDRAWN-30>=DPD_MAX  THEN 'SMA_1'  
--------                       ELSE 'SMA_2' END)   
--------                              ELSE ( CASE WHEN  REFPERIODOVERDUE-60>=DPD_MAX  
--------                                                              THEN 'SMA_0'  
--------                                                         WHEN REFPERIODOVERDUE-30>=DPD_MAX  THEN 'SMA_1'  
--------                       ELSE 'SMA_2' END)  
--------         END)  
  
------UPDATE A SET A.SMA_CLASS=  
------   (CASE  WHEN dpd.DPD_MAX  BETWEEN 276 AND 305  THEN 'SMA_0'  
------       WHEN dpd.DPD_MAX  BETWEEN 306 AND 335  THEN 'SMA_1'  
------    WHEN dpd.DPD_MAX  BETWEEN 336 AND 365  THEN 'SMA_2'  
------    WHEN dpd.DPD_MAX >=366 THEN 'SMA_2'  
------    ELSE NULL  
------    END)  
  
------   ,A.SMA_REASON= (CASE   
------      WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(DPD.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED', UPDATE A SET A.FLGSMA=NULL  
             ,A.SMA_CLASS_KEY=NULL  
       ,A.SMA_DT=NULL  
     FROM PRO.CUSTOMERCAL A, UPDATE A SET A.FLGSMA='Y'  
FROM PRO.CUSTOMERCAL A INNER JOIN PRO.ACCOUNTCAL B ON A.CustomerEntityID =B.CustomerEntityID  
WHERE B.FLGSMA='Y'  
  
  
IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL  
   DROP TABLE #TEMPTABLE_SMACLASS, B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS, SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1   
                             WHEN SMA_CLASS='SMA_1' THEN  2  
        WHEN SMA_CLASS='SMA_2' THEN  3 ELSE 0 END ) MAXSMA_CLASS  
        ,MIN(A.SMA_Dt) AS SMA_Dt  
                                 
INTO #TEMPTABLE_SMACLASS  
 FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B  
ON A.CustomerEntityID=B.CustomerEntityID AND  B.FLGSMA='Y'  
GROUP BY A.CustomerEntityID, UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt  
FROM PRO.CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID  
WHERE A.FLGSMA='Y', A.FLGSMA = 'Y', UPDATE A SET A.FLGSMA='Y'  
FROM PRO.CUSTOMERCAL A INNER JOIN PRO.ACCOUNTCAL B ON A.UCIF_ID =B.UCIF_ID  
WHERE B.FLGSMA='Y'  
  
  
IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL  
   DROP TABLE #TEMPTABLE_SMACLASSUcif, B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif, SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1   
                          WHEN SMA_CLASS='SMA_1' THEN  2  
                          WHEN SMA_CLASS='SMA_2' THEN  3 ELSE 0 END ) MAXSMA_CLASS  
                  ,MIN(A.SMA_Dt) AS SMA_Dt  
                                 
INTO #TEMPTABLE_SMACLASSUcif  
 FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B  
ON A.UCIF_ID=B.UCIF_ID AND  B.FLGSMA='Y'  
GROUP BY A.UCIF_ID, UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt  
FROM PRO.CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID  
WHERE A.FLGSMA='Y'  
  
  
  
 IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY)  
 BEGIN, A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN, SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2'))  SMA_CLASS INTO #SMACLASS  
FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID  
 AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYID AND A.FLGSMA='Y'   
WHERE B.FLGSMA='Y' AND  ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1, B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1, UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1, SMA_CLASS_KEY = 1, UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2, SMA_CLASS_KEY = 2, UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3, SMA_CLASS_KEY = 3, A.FLGSMA='Y', SMA_CLASS_KEY=1, SMA_CLASS_KEY=2, SMA_CLASS_KEY=3, UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1, SYSASSETCLASSALT_KEY = 1, UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2, SYSASSETCLASSALT_KEY = 2, UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3, SYSASSETCLASSALT_KEY = 3, UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4, SYSASSETCLASSALT_KEY = 4, UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5, SYSASSETCLASSALT_KEY = 5, UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6, SYSASSETCLASSALT_KEY = 6, SYSASSETCLASSALT_KEY=1, SYSASSETCLASSALT_KEY=2, SYSASSETCLASSALT_KEY=3, SYSASSETCLASSALT_KEY=4, SYSASSETCLASSALT_KEY=5, SYSASSETCLASSALT_KEY=6
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "A.SMA_CLASS", "expression": "NULL"}, {"column": "A.SMA_REASON", "expression": "NULL"}, {"column": "A.SMA_DT", "expression": "NULL"}, {"column": "A.FLGSMA", "expression": "NULL"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "A.DPD_Max", "expression": "0"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "A.DPD_Max", "expression": "(CASE WHEN (COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_NoCredit, 0) AND COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_Overdrawn, 0) AND COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_Overdue, 0) AND COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_Renewal, 0) AND COALESCE(A.DPD_IntService, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_IntService, 0) WHEN (COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_IntService, 0) AND COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_Overdrawn, 0) AND COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_Overdue, 0) AND COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_Renewal, 0) AND COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_NoCredit, 0) WHEN (COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_NoCredit, 0) AND COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_IntService, 0) AND COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_Overdue, 0) AND COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_Renewal, 0) AND COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_Overdrawn, 0) WHEN (COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_NoCredit, 0) AND COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_IntService, 0) AND COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_Overdrawn, 0) AND COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_Overdue, 0) AND COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_Renewal, 0) WHEN (COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_NoCredit, 0) AND COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_IntService, 0) AND COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_Overdrawn, 0) AND COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_Renewal, 0) AND COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.DPD_StockStmt, 0)) THEN COALESCE(A.DPD_Overdue, 0) ELSE COALESCE(A.DPD_StockStmt, 0) END)"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "SMA_CLASS", "expression": "(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE SMA_CLASS END)"}]
- The supporting technical evidence was low-confidence and should not be presented as fully verified: UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1  
     WHEN SMA_CLASS='SMA_1' THEN 2  
     WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "EffectiveToTimeKey", "expression": "@vEffectiveto"}, {"column": "MovementToDate", "expression": "DATEADD(DAY, -1, @ProcessDate)"}]
