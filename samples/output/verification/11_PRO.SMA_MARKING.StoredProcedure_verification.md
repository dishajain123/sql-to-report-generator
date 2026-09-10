# SMA Marking — Verification & Traceability

> Companion artifact to `PRO.SMA_MARKING.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_6ed9993261c9` |
| Raw technical object name (from source) | `SMA_MARKING` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `58d2266ab7c89acf` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `fff7585a03cb147d56cb99cc3fa108a5a08556179ba637f7356954000e362a12` |
| Configuration Version | `19623ceb340f7d06` |
| Run Timestamp | `2026-09-10T11:32:53.123913+00:00` |
| Object ID | `obj_6ed9993261c9` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_90db366e57db` |
| Total LLM Calls | `5` |
| Successful Calls | `5` |
| Failed Calls | `0` |
| Prompt Tokens | `191290` |
| Completion Tokens | `17655` |
| Total Tokens | `208945` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 28307 | available |
| synthesis | 3 | 3 | 0 | 104815 | available |
| synthesis_revision | 1 | 1 | 0 | 75823 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Update account movement history [UNRESOLVED] (`rule_01`) | `Not specified` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.ACCOUNT_MOVEMENT_HISTORY table based on certain conditions. |
| 🟠 2 | Update customer movement history [UNRESOLVED] (`rule_02`) | `Not specified` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.CUSTOMER_MOVEMENT_HISTORY table based on certain conditions. |
| 🔴 3 | Assign SMA class based on DPD Max [CONFLICT] (`rule_03`) | `SMA_CLASS` | Assigns the SMA class to an account based on the maximum overdue days (DPD) and facility type. The SMA class is determined by the range of… |
| 🔴 4 | Set SMA reason based on DPD Max [CONFLICT] (`rule_04`) | `SMA_REASON` | Sets the reason for the SMA class based on the maximum overdue days (DPD) and facility type. The reason is determined by which DPD componen… |
| 🔴 5 | Set SMA date based on DPD Max [CONFLICT] (`rule_05`) | `SMA_DT` | Sets the date when the SMA classification was applied based on the maximum overdue days (DPD). |
| 🔴 6 | Set SMA flag to 'Y' [CONFLICT] (`rule_06`) | `FLGSMA` | Sets the SMA flag to 'Y' for accounts that meet the SMA classification criteria. |
| 🟠 7 | Initialize customer flags [LLM_ONLY] (`rule_07`) | `FLGSMA, SMA_CLASS_KEY, SMA_DT` | Sets the FLGSMA, SMA_CLASS_KEY, and SMA_DT fields to NULL in the ##CUSTOMERCAL table. |
| 🔴 8 | Set FLGSMA to 'Y' [CONFLICT] (`rule_08`) | `FLGSMA` | Sets the FLGSMA field to 'Y' in the ##CUSTOMERCAL table for accounts that meet certain conditions. |
| 🔴 9 | Update SMA_CLASS_KEY and SMA_DT from temporary tables [CONFLICT] (`rule_09`) | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the information in the temporary tables. |
| 🟠 10 | Delete existing SMA_MOVEMENT_HISTORY record [UNRESOLVED] (`rule_10`) | `Not specified` | Deletes the existing SMA_MOVEMENT_HISTORY record for the given TIMEKEY if it exists. |
| 🟠 11 | Insert new SMA_MOVEMENT_HISTORY record [LLM_ONLY] (`rule_11`) | `TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS` | Inserts a new record into the PRO.SMA_MOVEMENT_HISTORY table with the current SMA_CLASS and previous SMA_CLASS for accounts that have chang… |
| 🟠 12 | Truncate PREVSMASTATUS table [LLM_ONLY] (`rule_12`) | `Not specified` | Truncates the PRO.PREVSMASTATUS table. |
| 🟢 13 | Update CustMoveDescription based on SYSASSETCLASSALT_KEY [MATCHED] (`rule_13`) | `CustMoveDescription` | Updates the CustMoveDescription in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY. |
| 🟢 14 | Update SMA_CLASS based on FinalAssetClassAlt_Key [MATCHED] (`rule_14`) | `SMA_CLASS` | Updates the SMA_CLASS in the ##AccountCal table based on the FinalAssetClassAlt_Key for accounts where SMA_CLASS is NULL. |
| 🟠 15 | Update process status [UNRESOLVED] (`rule_15`) | `Not specified` | Updates the COMPLETED, ERRORDATE, ERRORDESCRIPTION, and COUNT fields in the PRO.ACLRUNNINGPROCESSSTATUS table to reflect the process status. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Update account movement history (rule_01) | AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL | Not cited | 00_main_body_4 | 00_main_body_4:embedded_02_09 | Needs Review |
| 2 | Update customer movement history (rule_02) | AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL | Not cited | 00_main_body_4 | 00_main_body_4:embedded_09_37 | Needs Review |
| 3 | Assign SMA class based on DPD Max (rule_03) | dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0'; dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1'; dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2'; dpd.DPD_Max > 90 THEN 'SMA_2' | Not cited | source_chunk_id: 00_main_body_2 | statement_id: 00_main_body_2:embedded_01_02 | Needs Review |
| 4 | Set SMA reason based on DPD Max (rule_04) | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED'; A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY NO CREDIT'; A.FACILITYTYPE IN ('TL','D… | Not cited | source_chunk_id: 00_main_body_2 | statement_id: 00_main_body_2:embedded_01_02 | Needs Review |
| 5 | Set SMA date based on DPD Max (rule_05) | dpd.DPD_Max BETWEEN 1 AND 30 THEN DATEADD(DAY, -dpd.DPD_MAX+1, @ProcessDate); dpd.DPD_Max BETWEEN 31 AND 60 THEN DATEADD(DAY, -dpd.DPD_MAX+1, @ProcessDate); dpd.DPD_Max BETWEEN 61 AND 90 THEN DATEADD(DAY, -dpd.DPD_MAX+1, @ProcessDate); dpd.DPD_Max > 90 THEN D… | Not cited | source_chunk_id: 00_main_body_2 | statement_id: 00_main_body_2:embedded_01_02 | Needs Review |
| 6 | Set SMA flag to 'Y' (rule_06) | A.FLGSMA='Y' | Not cited | source_chunk_id: 00_main_body_2 | statement_id: 00_main_body_2:embedded_01_02 | Needs Review |
| 7 | Initialize customer flags (rule_07) | UPDATE A SET A.FLGSMA=NULL,A.SMA_CLASS_KEY=NULL,A.SMA_DT=NULL FROM ##CUSTOMERCAL A | Not cited | Not cited | Not cited | Verified |
| 8 | Set FLGSMA to 'Y' (rule_08) | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID WHERE B.FLGSMA='Y' | Not cited | Not cited | Not cited | Verified |
| 9 | Update SMA_CLASS_KEY and SMA_DT from temporary tables (rule_09) | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y'; UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A… | Not cited | Not cited | Not cited | Verified |
| 10 | Delete existing SMA_MOVEMENT_HISTORY record (rule_10) | IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY END | Not cited | Not cited | Not cited | Verified |
| 11 | Insert new SMA_MOVEMENT_HISTORY record (rule_11) | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SMA_CLASS IS NOT NULL AN… | Not cited | Not cited | Not cited | Verified |
| 12 | Truncate PREVSMASTATUS table (rule_12) | TRUNCATE TABLE PRO.PREVSMASTATUS | Not cited | Not cited | Not cited | Verified |
| 13 | Update CustMoveDescription based on SYSASSETCLASSALT_KEY (rule_13) | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1 | Not cited | Not cited | Not cited | Verified |
| 14 | Update SMA_CLASS based on FinalAssetClassAlt_Key (rule_14) | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL | Not cited | Not cited | Not cited | Verified |
| 15 | Update process status (rule_15) | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' | Not cited | Not cited | 00_main_body_7:chunk_text_01 | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0149_0154:branch_001 | (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND    isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND  isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_StockStmt,0)) | source \| Lines 149-150 \| Statement 00_main_body_5:chunk_text_05 |
| case_0149_0154:branch_002 | (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>=  isnull(A.DPD_Overdrawn,0) AND    isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND    isnull(A.DPD_NoCredit,0)>=  isnull(A.DPD_Renewal,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_StockStmt,0)) | source \| Lines 150-151 |
| case_0149_0154:branch_003 | (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0)  AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND   isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_StockStmt,0)) | source \| Lines 151-152 |
| case_0149_0154:branch_004 | (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0)    AND isnull(A.DPD_Renewal,0)>=   isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0)  AND  isnull(A.DPD_Renewal,0)>=   isnull(A.DPD_Overdue,0)  AND isnull(A.DPD_Renewal,0) >=isnull(A.DPD_StockStmt ,0)) | source \| Lines 152-153 |
| case_0149_0154:branch_005 | (isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0)    AND isnull(A.DPD_Overdue,0)>=   isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0)  AND  isnull(A.DPD_Overdue,0)>=   isnull(A.DPD_Renewal,0)  AND isnull(A.DPD_Overdue ,0)>=isnull(A.DPD_StockStmt ,0)) | source \| Lines 153-154 |
| case_0149_0154:branch_006 | ELSE | source \| Line 154 |
| case_0169_0174:branch_001 | dpd.DPD_Max  BETWEEN 1 AND 30 | /tmp/tmps580yne1.sql \| Lines 169-170 \| Chunk 00_main_body_2 |
| case_0169_0174:branch_002 | dpd.DPD_Max  BETWEEN 31 AND 60 | /tmp/tmps580yne1.sql \| Lines 170-171 \| Chunk 00_main_body_2 |
| case_0169_0174:branch_003 | dpd.DPD_Max  BETWEEN 61 AND 90 | /tmp/tmps580yne1.sql \| Lines 171-172 \| Chunk 00_main_body_2 |
| case_0169_0174:branch_004 | dpd.DPD_Max >90 | /tmp/tmps580yne1.sql \| Lines 172-173 \| Chunk 00_main_body_2 |
| case_0169_0174:branch_005 | ELSE | /tmp/tmps580yne1.sql \| Lines 173-174 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_001 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmps580yne1.sql \| Lines 176-177 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_002 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmps580yne1.sql \| Lines 177-178 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_003 | A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmps580yne1.sql \| Lines 178-179 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_004 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 | /tmp/tmps580yne1.sql \| Lines 179-180 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_005 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmps580yne1.sql \| Lines 180-181 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_006 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmps580yne1.sql \| Lines 181-183 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_007 | ELSE | /tmp/tmps580yne1.sql \| Lines 183-184 \| Chunk 00_main_body_2 |
| case_0378_0380:branch_001 | SMA_CLASS='SMA_0' | source \| Lines 378-379 |
| case_0378_0380:branch_002 | SMA_CLASS='SMA_1' | source \| Lines 379-380 |
| case_0378_0380:branch_003 | SMA_CLASS='SMA_2' | source \| Line 380 |
| case_0378_0380:branch_004 | ELSE | source \| Line 380 |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 378
- **Disposition:** covered_by_rule=100, technical_only=104, parser_failed=17, uncovered=157

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-3 | 00_main_body:chunk_text_01, 00_main_body | BEGIN SET NOCOUNT ON BEGIN TRY |
| SELECT | uncovered | Lines 6-6 | 00_main_body:chunk_text_02, 00_main_body | DECLARE @ProcessDate DATE=(SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY=@TIMEKEY) |
| SELECT | uncovered | Lines 8-14 | 00_main_body:chunk_text_03, 00_main_body | Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y') --------------START------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-------------... |
| SELECT | uncovered | Lines 17-24 | 00_main_body:chunk_text_04, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| UPDATE | uncovered | Lines 27-37 | 00_main_body:chunk_text_05, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| UPDATE | parser_failed | Lines 40-65 | 00_main_body:chunk_text_06, 00_main_body | Update A SET A.ReviewDueDt=NULL,A.DPD_Renewal=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_Key --WHERE C.EffectiveFromTimeKey<=@TIME... |
| SELECT | uncovered | Lines 68-97 | 00_main_body:chunk_text_07, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| UPDATE | uncovered | Lines 100-100 | 00_main_body:chunk_text_08, 00_main_body | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0 |
| UPDATE | uncovered | Lines 102-102 | 00_main_body:chunk_text_09, 00_main_body | UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0 |
| UPDATE | uncovered | Lines 104-104 | 00_main_body:chunk_text_10, 00_main_body | UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0 |
| UPDATE | uncovered | Lines 106-106 | 00_main_body:chunk_text_11, 00_main_body | UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0 |
| UPDATE | uncovered | Lines 108-108 | 00_main_body:chunk_text_12, 00_main_body | UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0 |
| UPDATE | parser_failed | Lines 110-117 | 00_main_body:chunk_text_13, 00_main_body | UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0 ----/* CALCULATE MAX DPD */ IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE |
| COMMAND | uncovered | Lines 2-3 | 00_main_body:embedded_01_14, 00_main_body | SET NOCOUNT ON BEGIN TRY |
| SELECT | uncovered | Lines 6-6 | 00_main_body:embedded_01_15, 00_main_body | DECLARE @ProcessDate DATE=(SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY=@TIMEKEY) |
| SELECT | uncovered | Lines 8-14 | 00_main_body:embedded_01_16, 00_main_body | Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y') --------------START------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-------------... |
| SELECT | uncovered | Lines 17-24 | 00_main_body:embedded_02_17, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| UPDATE | uncovered | Lines 27-37 | 00_main_body:embedded_03_18, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| UPDATE | parser_failed | Lines 40-65 | 00_main_body:embedded_04_19, 00_main_body | Update A SET A.ReviewDueDt=NULL,A.DPD_Renewal=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_Key --WHERE C.EffectiveFromTimeKey<=@TIME... |
| SELECT | uncovered | Lines 68-97 | 00_main_body:embedded_05_20, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| UPDATE | uncovered | Lines 100-100 | 00_main_body:embedded_06_21, 00_main_body | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0 |
| UPDATE | uncovered | Lines 102-102 | 00_main_body:embedded_07_22, 00_main_body | UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0 |
| UPDATE | uncovered | Lines 104-104 | 00_main_body:embedded_08_23, 00_main_body | UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0 |
| UPDATE | uncovered | Lines 106-106 | 00_main_body:embedded_09_24, 00_main_body | UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0 |
| UPDATE | uncovered | Lines 108-108 | 00_main_body:embedded_10_25, 00_main_body | UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0 |
| UPDATE | parser_failed | Lines 110-117 | 00_main_body:embedded_11_26, 00_main_body | UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0 ----/* CALCULATE MAX DPD */ IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE |
| SELECT | uncovered | Lines 1-21 | 00_main_body_1:chunk_text_01, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| UPDATE | uncovered | Lines 24-29 | 00_main_body_1:chunk_text_02, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| UPDATE | uncovered | Lines 32-40 | 00_main_body_1:chunk_text_03, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| UPDATE | uncovered | Lines 44-48 | 00_main_body_1:chunk_text_04, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
| SELECT | uncovered | Lines 1-21 | 00_main_body_1:embedded_01_05, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| UPDATE | uncovered | Lines 24-29 | 00_main_body_1:embedded_02_06, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| UPDATE | uncovered | Lines 32-40 | 00_main_body_1:embedded_03_07, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| UPDATE | uncovered | Lines 44-48 | 00_main_body_1:embedded_04_08, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
| UPDATE | covered_by_rule | Lines 1-99 | 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| UPDATE | covered_by_rule | Lines 1-99 | 00_main_body_2:embedded_01_02, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| UPDATE | covered_by_rule | Lines 1-42 | 00_main_body_3:chunk_text_01, 00_main_body_3 | ------ WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(DPD.DPD_MAX,0) THEN 'DEGRADE BY NO CREDIT' ------ WHEN A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(DPD.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) THEN... |
| UPDATE | covered_by_rule | Lines 1-4 | 00_main_body_4:chunk_text_01, 00_main_body_4 | UPDATE A SET A.FLGSMA=NULL ,A.SMA_CLASS_KEY=NULL ,A.SMA_DT=NULL FROM ##CUSTOMERCAL A |
| UPDATE | parser_failed | Lines 7-13 | 00_main_body_4:chunk_text_02, 00_main_body_4 | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID WHERE B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS |
| SELECT | covered_by_rule | Lines 16-24 | 00_main_body_4:chunk_text_03, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| UPDATE | covered_by_rule | Lines 27-29 | 00_main_body_4:chunk_text_04, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| UPDATE | parser_failed | Lines 34-40 | 00_main_body_4:chunk_text_05, 00_main_body_4 | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.UCIF_ID =B.UCIF_ID WHERE B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif |
| SELECT | covered_by_rule | Lines 43-51 | 00_main_body_4:chunk_text_06, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| UPDATE | parser_failed | Lines 54-61 | 00_main_body_4:chunk_text_07, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID WHERE A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN |
| DELETE | parser_failed | Lines 63-64 | 00_main_body_4:chunk_text_08, 00_main_body_4 | DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY END |
| STATEMENT | covered_by_rule | Lines 68-69 | 00_main_body_4:chunk_text_09, 00_main_body_4 | IF OBJECT_ID('TEMPDB..#SMACLASS') IS NOT NULL DROP TABLE #SMACLASS |
| SELECT | covered_by_rule | Lines 72-75 | 00_main_body_4:chunk_text_10, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| UPDATE | covered_by_rule | Lines 78-80 | 00_main_body_4:chunk_text_11, 00_main_body_4 | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END) |
| INSERT | covered_by_rule | Lines 83-87 | 00_main_body_4:chunk_text_12, 00_main_body_4 | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SM... |
| TRUNCATETABLE | covered_by_rule | Lines 90-90 | 00_main_body_4:chunk_text_13, 00_main_body_4 | TRUNCATE TABLE PRO.PREVSMASTATUS |
| INSERT | covered_by_rule | Lines 93-101 | 00_main_body_4:chunk_text_14, 00_main_body_4 | INSERT INTO PRO.PREVSMASTATUS SELECT @TIMEKEY,CustomerAcID,SMA_CLASS FROM #SMACLASS --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY) --SELECT A.CustomerAc... |
| UPDATE | covered_by_rule | Lines 104-104 | 00_main_body_4:chunk_text_15, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1 |
| UPDATE | covered_by_rule | Lines 106-106 | 00_main_body_4:chunk_text_16, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2 |
| UPDATE | covered_by_rule | Lines 108-108 | 00_main_body_4:chunk_text_17, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3 |
| UPDATE | covered_by_rule | Lines 110-110 | 00_main_body_4:chunk_text_18, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4 |
| UPDATE | covered_by_rule | Lines 112-112 | 00_main_body_4:chunk_text_19, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5 |
| UPDATE | covered_by_rule | Lines 114-114 | 00_main_body_4:chunk_text_20, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6 |
| UPDATE | covered_by_rule | Lines 116-116 | 00_main_body_4:chunk_text_21, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1 |
| UPDATE | covered_by_rule | Lines 118-118 | 00_main_body_4:chunk_text_22, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2 |
| UPDATE | covered_by_rule | Lines 120-120 | 00_main_body_4:chunk_text_23, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3 |
| UPDATE | covered_by_rule | Lines 123-123 | 00_main_body_4:chunk_text_24, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL |
| UPDATE | covered_by_rule | Lines 125-125 | 00_main_body_4:chunk_text_25, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL |
| UPDATE | covered_by_rule | Lines 127-127 | 00_main_body_4:chunk_text_26, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL |
| UPDATE | covered_by_rule | Lines 129-129 | 00_main_body_4:chunk_text_27, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL |
| UPDATE | covered_by_rule | Lines 131-131 | 00_main_body_4:chunk_text_28, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL |
| UPDATE | covered_by_rule | Lines 1-4 | 00_main_body_4:embedded_01_29, 00_main_body_4 | UPDATE A SET A.FLGSMA=NULL ,A.SMA_CLASS_KEY=NULL ,A.SMA_DT=NULL FROM ##CUSTOMERCAL A |
| UPDATE | parser_failed | Lines 7-13 | 00_main_body_4:embedded_02_30, 00_main_body_4 | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID WHERE B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS |
| SELECT | covered_by_rule | Lines 16-24 | 00_main_body_4:embedded_03_31, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| UPDATE | covered_by_rule | Lines 27-29 | 00_main_body_4:embedded_04_32, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| UPDATE | parser_failed | Lines 34-40 | 00_main_body_4:embedded_05_33, 00_main_body_4 | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.UCIF_ID =B.UCIF_ID WHERE B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif |
| SELECT | covered_by_rule | Lines 43-51 | 00_main_body_4:embedded_06_34, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| UPDATE | parser_failed | Lines 54-61 | 00_main_body_4:embedded_07_35, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID WHERE A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN |
| DELETE | covered_by_rule | Lines 63-63 | 00_main_body_4:embedded_08_36, 00_main_body_4 | DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY |
| SELECT | covered_by_rule | Lines 72-75 | 00_main_body_4:embedded_09_37, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| UPDATE | covered_by_rule | Lines 78-80 | 00_main_body_4:embedded_10_38, 00_main_body_4 | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END) |
| INSERT | covered_by_rule | Lines 83-83 | 00_main_body_4:embedded_11_39, 00_main_body_4 | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) |
| SELECT | covered_by_rule | Lines 84-87 | 00_main_body_4:embedded_12_40, 00_main_body_4 | SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') |
| TRUNCATETABLE | covered_by_rule | Lines 90-90 | 00_main_body_4:embedded_12_41, 00_main_body_4 | TRUNCATE TABLE PRO.PREVSMASTATUS |
| INSERT | covered_by_rule | Lines 93-93 | 00_main_body_4:embedded_13_42, 00_main_body_4 | INSERT INTO PRO.PREVSMASTATUS |
| SELECT | covered_by_rule | Lines 94-101 | 00_main_body_4:embedded_14_43, 00_main_body_4 | SELECT @TIMEKEY,CustomerAcID,SMA_CLASS FROM #SMACLASS --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY) --SELECT A.CustomerAcID,A.FinalAssetClassAlt_Key,A.... |
| UPDATE | covered_by_rule | Lines 104-104 | 00_main_body_4:embedded_15_44, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1 |
| UPDATE | covered_by_rule | Lines 106-106 | 00_main_body_4:embedded_16_45, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2 |
| UPDATE | covered_by_rule | Lines 108-108 | 00_main_body_4:embedded_17_46, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3 |
| UPDATE | covered_by_rule | Lines 110-110 | 00_main_body_4:embedded_18_47, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4 |
| UPDATE | covered_by_rule | Lines 112-112 | 00_main_body_4:embedded_19_48, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5 |
| UPDATE | covered_by_rule | Lines 114-114 | 00_main_body_4:embedded_20_49, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6 |
| UPDATE | covered_by_rule | Lines 116-116 | 00_main_body_4:embedded_21_50, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1 |
| UPDATE | covered_by_rule | Lines 118-118 | 00_main_body_4:embedded_22_51, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2 |
| UPDATE | covered_by_rule | Lines 120-120 | 00_main_body_4:embedded_23_52, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3 |
| UPDATE | covered_by_rule | Lines 123-123 | 00_main_body_4:embedded_24_53, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL |
| UPDATE | covered_by_rule | Lines 125-125 | 00_main_body_4:embedded_25_54, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL |
| UPDATE | covered_by_rule | Lines 127-127 | 00_main_body_4:embedded_26_55, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL |
| UPDATE | covered_by_rule | Lines 129-129 | 00_main_body_4:embedded_27_56, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL |
| UPDATE | covered_by_rule | Lines 131-131 | 00_main_body_4:embedded_28_57, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL |
| UPDATE | parser_failed | Lines 1-39 | 00_main_body_5:chunk_text_01, 00_main_body_5 | UPDATE ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HISTORY') IS NOT NULL -- DROP TABLE #ACCOUNT_MOVEMENT_HISTORY -- SELECT CustomerAcID,FinalAssetClassAl... |
| UPDATE | uncovered | Lines 41-62 | 00_main_body_5:chunk_text_02, 00_main_body_5 | else begin IF OBJECT_ID ('TEMPDB..#ACCOUNT_MOVEMENT_HISTORY') IS NOT NULL DROP TABLE #ACCOUNT_MOVEMENT_HISTORY CREATE TABLE #ACCOUNT_MOVEMENT_HISTORY ( [UCIF_ID] [varchar](50) NULL, [RefCustomerID] [varchar](50) NULL, [SourceSystemCustom... |
| INSERT | uncovered | Lines 65-96 | 00_main_body_5:chunk_text_03, 00_main_body_5 | INSERT INTO #ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementF... |
| INSERT | uncovered | Lines 100-139 | 00_main_body_5:chunk_text_04, 00_main_body_5 | INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus ,TotOsAcc ,Moveme... |
| UPDATE | uncovered | Lines 142-149 | 00_main_body_5:chunk_text_05, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| UPDATE | parser_failed | Lines 1-38 | 00_main_body_5:embedded_01_06, 00_main_body_5 | UPDATE ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HISTORY') IS NOT NULL -- DROP TABLE #ACCOUNT_MOVEMENT_HISTORY -- SELECT CustomerAcID,FinalAssetClassAl... |
| INSERT | uncovered | Lines 65-80 | 00_main_body_5:embedded_02_07, 00_main_body_5 | INSERT INTO #ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementF... |
| SELECT | uncovered | Lines 81-96 | 00_main_body_5:embedded_03_08, 00_main_body_5 | SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey ,SMA_CLASS AS MovementFromStatus ,SMA_CLASS AS MovementToStatus ,ISNULL(Balance,0)... |
| INSERT | uncovered | Lines 100-117 | 00_main_body_5:embedded_04_09, 00_main_body_5 | INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus ,TotOsAcc ,Moveme... |
| SELECT | uncovered | Lines 118-139 | 00_main_body_5:embedded_05_10, 00_main_body_5 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNUL... |
| UPDATE | uncovered | Lines 142-149 | 00_main_body_5:embedded_06_11, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| UPDATE | parser_failed | Lines 1-24 | 00_main_body_6:chunk_text_01, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| SELECT | uncovered | Lines 27-30 | 00_main_body_6:chunk_text_02, 00_main_body_6 | if EXISTS ( select 1 from PRO.CUSTOMER_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA' end |
| UPDATE | uncovered | Lines 32-53 | 00_main_body_6:chunk_text_03, 00_main_body_6 | else begin IF OBJECT_ID ('TEMPDB..#Customer_MOVEMENT_HISTORY') IS NOT NULL DROP TABLE #Customer_MOVEMENT_HISTORY CREATE TABLE #Customer_MOVEMENT_HISTORY ( [UCIF_ID] [varchar](50) NULL, [RefCustomerID] [varchar](50) NULL, [SourceSystemCus... |
| INSERT | uncovered | Lines 57-89 | 00_main_body_6:chunk_text_04, 00_main_body_6 | INSERT INTO #Customer_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, totOsCust ,MovementFr... |
| INSERT | uncovered | Lines 93-134 | 00_main_body_6:chunk_text_05, 00_main_body_6 | INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust ,Movemen... |
| UPDATE | uncovered | Lines 137-144 | 00_main_body_6:chunk_text_06, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| UPDATE | uncovered | Lines 1-22 | 00_main_body_6:embedded_01_07, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| INSERT | uncovered | Lines 57-72 | 00_main_body_6:embedded_02_08, 00_main_body_6 | INSERT INTO #Customer_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, totOsCust ,MovementFr... |
| SELECT | uncovered | Lines 73-89 | 00_main_body_6:embedded_03_09, 00_main_body_6 | SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey ,CustMoveDescription AS MovementFromStatus ,CustMoveDescription AS MovementToStatus ,... |
| INSERT | uncovered | Lines 93-110 | 00_main_body_6:embedded_04_10, 00_main_body_6 | INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust ,Movemen... |
| SELECT | uncovered | Lines 111-134 | 00_main_body_6:embedded_05_11, 00_main_body_6 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNULL(A... |
| UPDATE | uncovered | Lines 137-144 | 00_main_body_6:embedded_06_12, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| UPDATE | parser_failed | Lines 1-27 | 00_main_body_7:chunk_text_01, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| UPDATE | covered_by_rule | Lines 30-44 | 00_main_body_7:chunk_text_02, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| UPDATE | parser_failed | Lines 51-59 | 00_main_body_7:chunk_text_03, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' -----------------Added for DashBoard 04-03-2021 --Update BANDAUDITSTATUS set Complet... |
| STATEMENT | covered_by_rule | Lines 61-67 | 00_main_body_7:chunk_text_04, 00_main_body_7 | BEGIN CATCH DROP TABLE #TEMPTABLE_SMACLASS DROP TABLE #SMACLASS DROP TABLE #ACCOUNT_MOVEMENT_HISTORY DROP TABLE #Customer_MOVEMENT_HISTORY |
| UPDATE | parser_failed | Lines 70-74 | 00_main_body_7:chunk_text_05, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' END CATCH |
| SET | covered_by_rule | Lines 76-77 | 00_main_body_7:chunk_text_06, 00_main_body_7 | SET NOCOUNT OFF END |
| STATEMENT | covered_by_rule | Lines 80-80 | 00_main_body_7:chunk_text_07, 00_main_body_7 | GO |
| UPDATE | covered_by_rule | Lines 1-24 | 00_main_body_7:embedded_01_08, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| UPDATE | covered_by_rule | Lines 30-44 | 00_main_body_7:embedded_02_09, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| UPDATE | covered_by_rule | Lines 51-57 | 00_main_body_7:embedded_03_10, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' -----------------Added for DashBoard 04-03-2021 --Update BANDAUDITSTATUS set Complet... |
| UPDATE | covered_by_rule | Lines 70-72 | 00_main_body_7:embedded_04_11, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' |
| SET | covered_by_rule | Lines 76-76 | 00_main_body_7:embedded_05_12, 00_main_body_7 | SET NOCOUNT OFF |
| READ | uncovered | unavailable | 00_main_body:chunk_text_02, 00_main_body:chunk_text_02, 00_main_body | DECLARE @ProcessDate DATE=(SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY=@TIMEKEY) |
| READ | uncovered | unavailable | 00_main_body:chunk_text_03, 00_main_body:chunk_text_03, 00_main_body | Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y') --------------START------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-------------... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_04, 00_main_body:chunk_text_04, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_04, 00_main_body:chunk_text_04, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_04, 00_main_body:chunk_text_04, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_05, 00_main_body:chunk_text_05, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_05, 00_main_body:chunk_text_05, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_05, 00_main_body:chunk_text_05, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:chunk_text_06, 00_main_body:chunk_text_06, 00_main_body | Update A SET A.ReviewDueDt=NULL,A.DPD_Renewal=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_Key --WHERE C.EffectiveFromTimeKey<=@TIME... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_07, 00_main_body:chunk_text_07, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_07, 00_main_body:chunk_text_07, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_08, 00_main_body:chunk_text_08, 00_main_body | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_09, 00_main_body:chunk_text_09, 00_main_body | UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_10, 00_main_body:chunk_text_10, 00_main_body | UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_11, 00_main_body:chunk_text_11, 00_main_body | UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body:chunk_text_12, 00_main_body:chunk_text_12, 00_main_body | UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:chunk_text_13, 00_main_body:chunk_text_13, 00_main_body | UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0 ----/* CALCULATE MAX DPD */ IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE |
| READ_TEMP | technical_only | unavailable | 00_main_body:embedded_02_17, 00_main_body:embedded_02_17, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_03_18, 00_main_body:embedded_03_18, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| READ_TEMP | technical_only | unavailable | 00_main_body:embedded_05_20, 00_main_body:embedded_05_20, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_06_21, 00_main_body:embedded_06_21, 00_main_body | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_07_22, 00_main_body:embedded_07_22, 00_main_body | UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_08_23, 00_main_body:embedded_08_23, 00_main_body | UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_09_24, 00_main_body:embedded_09_24, 00_main_body | UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_10_25, 00_main_body:embedded_10_25, 00_main_body | UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0 |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_1:chunk_text_01, 00_main_body_1:chunk_text_01, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_1:chunk_text_01, 00_main_body_1:chunk_text_01, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_1:chunk_text_02, 00_main_body_1:chunk_text_02, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body_1:chunk_text_02, 00_main_body_1:chunk_text_02, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_1:chunk_text_03, 00_main_body_1:chunk_text_03, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body_1:chunk_text_03, 00_main_body_1:chunk_text_03, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_1:chunk_text_04, 00_main_body_1:chunk_text_04, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body_1:chunk_text_04, 00_main_body_1:chunk_text_04, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
| READ_TEMP | technical_only | unavailable | 00_main_body_1:embedded_01_05, 00_main_body_1:embedded_01_05, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_1:embedded_02_06, 00_main_body_1:embedded_02_06, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_1:embedded_03_07, 00_main_body_1:embedded_03_07, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_1:embedded_04_08, 00_main_body_1:embedded_04_08, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| READ | covered_by_rule | /tmp/tmps580yne1.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| READ | covered_by_rule | /tmp/tmps580yne1.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_2:embedded_01_02, 00_main_body_2:embedded_01_02, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_01, 00_main_body_4:chunk_text_01, 00_main_body_4 | UPDATE A SET A.FLGSMA=NULL ,A.SMA_CLASS_KEY=NULL ,A.SMA_DT=NULL FROM ##CUSTOMERCAL A |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:chunk_text_02, 00_main_body_4:chunk_text_02, 00_main_body_4 | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID WHERE B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_03, 00_main_body_4:chunk_text_03, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_03, 00_main_body_4:chunk_text_03, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_03, 00_main_body_4:chunk_text_03, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_04, 00_main_body_4:chunk_text_04, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| READ | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_04, 00_main_body_4:chunk_text_04, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_04, 00_main_body_4:chunk_text_04, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:chunk_text_05, 00_main_body_4:chunk_text_05, 00_main_body_4 | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.UCIF_ID =B.UCIF_ID WHERE B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_06, 00_main_body_4:chunk_text_06, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_06, 00_main_body_4:chunk_text_06, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_06, 00_main_body_4:chunk_text_06, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| READ | covered_by_rule | unavailable | 00_main_body_4:chunk_text_07, 00_main_body_4:chunk_text_07, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID WHERE A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:chunk_text_07, 00_main_body_4:chunk_text_07, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID WHERE A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN |
| DELETE | covered_by_rule | unavailable | 00_main_body_4:chunk_text_08, 00_main_body_4:chunk_text_08, 00_main_body_4 | DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY END |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_10, 00_main_body_4:chunk_text_10, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_10, 00_main_body_4:chunk_text_10, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_10, 00_main_body_4:chunk_text_10, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_11, 00_main_body_4:chunk_text_11, 00_main_body_4 | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END) |
| INSERT | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_12, 00_main_body_4:chunk_text_12, 00_main_body_4 | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SM... |
| TRUNCATE | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_13, 00_main_body_4:chunk_text_13, 00_main_body_4 | TRUNCATE TABLE PRO.PREVSMASTATUS |
| INSERT | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_14, 00_main_body_4:chunk_text_14, 00_main_body_4 | INSERT INTO PRO.PREVSMASTATUS SELECT @TIMEKEY,CustomerAcID,SMA_CLASS FROM #SMACLASS --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY) --SELECT A.CustomerAc... |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_15, 00_main_body_4:chunk_text_15, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_16, 00_main_body_4:chunk_text_16, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_17, 00_main_body_4:chunk_text_17, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_18, 00_main_body_4:chunk_text_18, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_19, 00_main_body_4:chunk_text_19, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_20, 00_main_body_4:chunk_text_20, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_21, 00_main_body_4:chunk_text_21, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_22, 00_main_body_4:chunk_text_22, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_23, 00_main_body_4:chunk_text_23, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3 |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_24, 00_main_body_4:chunk_text_24, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_25, 00_main_body_4:chunk_text_25, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_26, 00_main_body_4:chunk_text_26, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_27, 00_main_body_4:chunk_text_27, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:chunk_text_28, 00_main_body_4:chunk_text_28, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_01_29, 00_main_body_4:embedded_01_29, 00_main_body_4 | UPDATE A SET A.FLGSMA=NULL ,A.SMA_CLASS_KEY=NULL ,A.SMA_DT=NULL FROM ##CUSTOMERCAL A |
| READ_TEMP | technical_only | unavailable | 00_main_body_4:embedded_03_31, 00_main_body_4:embedded_03_31, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_04_32, 00_main_body_4:embedded_04_32, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| READ_TEMP | technical_only | unavailable | 00_main_body_4:embedded_06_34, 00_main_body_4:embedded_06_34, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| DELETE | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_4:embedded_08_36, 00_main_body_4:embedded_08_36, 00_main_body_4 | DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY |
| READ_TEMP | technical_only | unavailable | 00_main_body_4:embedded_09_37, 00_main_body_4:embedded_09_37, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_10_38, 00_main_body_4:embedded_10_38, 00_main_body_4 | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END) |
| INSERT | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_4:embedded_11_39, 00_main_body_4:embedded_11_39, 00_main_body_4 | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) |
| READ | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_4:embedded_12_40, 00_main_body_4:embedded_12_40, 00_main_body_4 | SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:embedded_12_40, 00_main_body_4:embedded_12_40, 00_main_body_4 | SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') |
| INSERT | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_4:embedded_13_42, 00_main_body_4:embedded_13_42, 00_main_body_4 | INSERT INTO PRO.PREVSMASTATUS |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_4:embedded_14_43, 00_main_body_4:embedded_14_43, 00_main_body_4 | SELECT @TIMEKEY,CustomerAcID,SMA_CLASS FROM #SMACLASS --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY) --SELECT A.CustomerAcID,A.FinalAssetClassAlt_Key,A.... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_15_44, 00_main_body_4:embedded_15_44, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_16_45, 00_main_body_4:embedded_16_45, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_17_46, 00_main_body_4:embedded_17_46, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_18_47, 00_main_body_4:embedded_18_47, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_19_48, 00_main_body_4:embedded_19_48, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_20_49, 00_main_body_4:embedded_20_49, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_21_50, 00_main_body_4:embedded_21_50, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_22_51, 00_main_body_4:embedded_22_51, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_23_52, 00_main_body_4:embedded_23_52, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_24_53, 00_main_body_4:embedded_24_53, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_25_54, 00_main_body_4:embedded_25_54, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_26_55, 00_main_body_4:embedded_26_55, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_27_56, 00_main_body_4:embedded_27_56, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_28_57, 00_main_body_4:embedded_28_57, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL |
| READ | uncovered | unavailable | 00_main_body_5:chunk_text_01, 00_main_body_5:chunk_text_01, 00_main_body_5 | UPDATE ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HISTORY') IS NOT NULL -- DROP TABLE #ACCOUNT_MOVEMENT_HISTORY -- SELECT CustomerAcID,FinalAssetClassAl... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_5:chunk_text_01, 00_main_body_5:chunk_text_01, 00_main_body_5 | UPDATE ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HISTORY') IS NOT NULL -- DROP TABLE #ACCOUNT_MOVEMENT_HISTORY -- SELECT CustomerAcID,FinalAssetClassAl... |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_5:chunk_text_03, 00_main_body_5:chunk_text_03, 00_main_body_5 | INSERT INTO #ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementF... |
| INSERT | uncovered | /tmp/tmps580yne1.sql | 00_main_body_5:chunk_text_04, 00_main_body_5:chunk_text_04, 00_main_body_5 | INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus ,TotOsAcc ,Moveme... |
| UPDATE | uncovered | /tmp/tmps580yne1.sql | 00_main_body_5:chunk_text_05, 00_main_body_5:chunk_text_05, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body_5:chunk_text_05, 00_main_body_5:chunk_text_05, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_5:chunk_text_05, 00_main_body_5:chunk_text_05, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_5:embedded_02_07, 00_main_body_5:embedded_02_07, 00_main_body_5 | INSERT INTO #ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementF... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_5:embedded_03_08, 00_main_body_5:embedded_03_08, 00_main_body_5 | SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey ,SMA_CLASS AS MovementFromStatus ,SMA_CLASS AS MovementToStatus ,ISNULL(Balance,0)... |
| INSERT | uncovered | /tmp/tmps580yne1.sql | 00_main_body_5:embedded_04_09, 00_main_body_5:embedded_04_09, 00_main_body_5 | INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus ,TotOsAcc ,Moveme... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_5:embedded_05_10, 00_main_body_5:embedded_05_10, 00_main_body_5 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNUL... |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body_5:embedded_05_10, 00_main_body_5:embedded_05_10, 00_main_body_5 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNUL... |
| UPDATE | uncovered | unavailable | 00_main_body_5:embedded_06_11, 00_main_body_5:embedded_06_11, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| READ_TEMP | technical_only | unavailable | 00_main_body_6:chunk_text_01, 00_main_body_6:chunk_text_01, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| UPDATE | uncovered | unavailable | 00_main_body_6:chunk_text_01, 00_main_body_6:chunk_text_01, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| READ | uncovered | unavailable | 00_main_body_6:chunk_text_02, 00_main_body_6:chunk_text_02, 00_main_body_6 | if EXISTS ( select 1 from PRO.CUSTOMER_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA' end |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_6:chunk_text_04, 00_main_body_6:chunk_text_04, 00_main_body_6 | INSERT INTO #Customer_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, totOsCust ,MovementFr... |
| INSERT | uncovered | /tmp/tmps580yne1.sql | 00_main_body_6:chunk_text_05, 00_main_body_6:chunk_text_05, 00_main_body_6 | INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust ,Movemen... |
| UPDATE | uncovered | /tmp/tmps580yne1.sql | 00_main_body_6:chunk_text_06, 00_main_body_6:chunk_text_06, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body_6:chunk_text_06, 00_main_body_6:chunk_text_06, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_6:chunk_text_06, 00_main_body_6:chunk_text_06, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| UPDATE | uncovered | /tmp/tmps580yne1.sql | 00_main_body_6:embedded_01_07, 00_main_body_6:embedded_01_07, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body_6:embedded_01_07, 00_main_body_6:embedded_01_07, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_6:embedded_01_07, 00_main_body_6:embedded_01_07, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| INSERT_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_6:embedded_02_08, 00_main_body_6:embedded_02_08, 00_main_body_6 | INSERT INTO #Customer_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, totOsCust ,MovementFr... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_6:embedded_03_09, 00_main_body_6:embedded_03_09, 00_main_body_6 | SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey ,CustMoveDescription AS MovementFromStatus ,CustMoveDescription AS MovementToStatus ,... |
| INSERT | uncovered | /tmp/tmps580yne1.sql | 00_main_body_6:embedded_04_10, 00_main_body_6:embedded_04_10, 00_main_body_6 | INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust ,Movemen... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_6:embedded_05_11, 00_main_body_6:embedded_05_11, 00_main_body_6 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNULL(A... |
| READ | uncovered | /tmp/tmps580yne1.sql | 00_main_body_6:embedded_05_11, 00_main_body_6:embedded_05_11, 00_main_body_6 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNULL(A... |
| UPDATE | uncovered | unavailable | 00_main_body_6:embedded_06_12, 00_main_body_6:embedded_06_12, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| READ_TEMP | technical_only | unavailable | 00_main_body_7:chunk_text_01, 00_main_body_7:chunk_text_01, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| UPDATE | covered_by_rule | unavailable | 00_main_body_7:chunk_text_01, 00_main_body_7:chunk_text_01, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| UPDATE_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_7:chunk_text_02, 00_main_body_7:chunk_text_02, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| READ | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_7:chunk_text_02, 00_main_body_7:chunk_text_02, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_7:chunk_text_02, 00_main_body_7:chunk_text_02, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| UPDATE | covered_by_rule | unavailable | 00_main_body_7:chunk_text_03, 00_main_body_7:chunk_text_03, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' -----------------Added for DashBoard 04-03-2021 --Update BANDAUDITSTATUS set Complet... |
| UPDATE | covered_by_rule | unavailable | 00_main_body_7:chunk_text_05, 00_main_body_7:chunk_text_05, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' END CATCH |
| UPDATE | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_7:embedded_01_08, 00_main_body_7:embedded_01_08, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| READ | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_7:embedded_01_08, 00_main_body_7:embedded_01_08, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| READ_TEMP | technical_only | /tmp/tmps580yne1.sql | 00_main_body_7:embedded_01_08, 00_main_body_7:embedded_01_08, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_7:embedded_02_09, 00_main_body_7:embedded_02_09, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| UPDATE | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_7:embedded_03_10, 00_main_body_7:embedded_03_10, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' -----------------Added for DashBoard 04-03-2021 --Update BANDAUDITSTATUS set Complet... |
| UPDATE | covered_by_rule | /tmp/tmps580yne1.sql | 00_main_body_7:embedded_04_11, 00_main_body_7:embedded_04_11, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' |
| CASE | uncovered | Lines 149-150 | 00_main_body_5:chunk_text_05 | (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.... |
| CASE | uncovered | Lines 150-151 | unavailable | (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>= isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_NoCredit,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.DPD_... |
| CASE | uncovered | Lines 151-152 | unavailable | (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.D... |
| CASE | uncovered | Lines 152-153 | unavailable | (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Renewal,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Renewal,0)>= isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Ren... |
| CASE | uncovered | Lines 153-154 | unavailable | (isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdue,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Overdue,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Ove... |
| ELSE | covered_by_rule | Lines 154-154 | unavailable | ELSE |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 169-170 | 00_main_body_2 | dpd.DPD_Max BETWEEN 1 AND 30 |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 170-171 | 00_main_body_2 | dpd.DPD_Max BETWEEN 31 AND 60 |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 171-172 | 00_main_body_2 | dpd.DPD_Max BETWEEN 61 AND 90 |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 172-173 | 00_main_body_2 | dpd.DPD_Max >90 |
| ELSE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 173-174 | 00_main_body_2 | ELSE |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 176-177 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 177-178 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 178-179 | 00_main_body_2 | A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 179-180 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 180-181 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) |
| CASE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 181-183 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) |
| ELSE | covered_by_rule | /tmp/tmps580yne1.sql / Lines 183-184 | 00_main_body_2 | ELSE |
| CASE | uncovered | Lines 378-379 | unavailable | SMA_CLASS='SMA_0' |
| CASE | uncovered | Lines 379-380 | unavailable | SMA_CLASS='SMA_1' |
| CASE | uncovered | Lines 380-380 | unavailable | SMA_CLASS='SMA_2' |
| ELSE | covered_by_rule | Lines 380-380 | unavailable | ELSE |
| IF | uncovered | Lines 24-24 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| IF | uncovered | Lines 72-72 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| IF | uncovered | Lines 117-117 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | uncovered | Lines 121-121 | unavailable | ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, |
| CASE_BRANCH | uncovered | Lines 121-121 | unavailable | ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, |
| ELSE | uncovered | Lines 121-121 | unavailable | ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, |
| CASE | uncovered | Lines 122-122 | unavailable | CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 END DPD_NoCredit, |
| CASE_BRANCH | uncovered | Lines 122-122 | unavailable | CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 END DPD_NoCredit, |
| ELSE | uncovered | Lines 122-122 | unavailable | CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 END DPD_NoCredit, |
| CASE | uncovered | Lines 123-123 | unavailable | CASE WHEN isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn ,0) THEN A.DPD_Overdrawn ELSE 0 END DPD_Overdrawn, |
| CASE_BRANCH | uncovered | Lines 123-123 | unavailable | CASE WHEN isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn ,0) THEN A.DPD_Overdrawn ELSE 0 END DPD_Overdrawn, |
| ELSE | uncovered | Lines 123-123 | unavailable | CASE WHEN isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn ,0) THEN A.DPD_Overdrawn ELSE 0 END DPD_Overdrawn, |
| CASE | uncovered | Lines 124-124 | unavailable | CASE WHEN isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue ,0) THEN A.DPD_Overdue ELSE 0 END DPD_Overdue , |
| CASE_BRANCH | uncovered | Lines 124-124 | unavailable | CASE WHEN isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue ,0) THEN A.DPD_Overdue ELSE 0 END DPD_Overdue , |
| ELSE | uncovered | Lines 124-124 | unavailable | CASE WHEN isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue ,0) THEN A.DPD_Overdue ELSE 0 END DPD_Overdue , |
| CASE | uncovered | Lines 125-125 | unavailable | CASE WHEN isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview ,0) THEN A.DPD_Renewal ELSE 0 END DPD_Renewal , |
| CASE_BRANCH | uncovered | Lines 125-125 | unavailable | CASE WHEN isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview ,0) THEN A.DPD_Renewal ELSE 0 END DPD_Renewal , |
| ELSE | uncovered | Lines 125-125 | unavailable | CASE WHEN isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview ,0) THEN A.DPD_Renewal ELSE 0 END DPD_Renewal , |
| CASE | uncovered | Lines 126-126 | unavailable | CASE WHEN isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) THEN A.DPD_StockStmt ELSE 0 END DPD_StockStmt |
| CASE_BRANCH | uncovered | Lines 126-126 | unavailable | CASE WHEN isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) THEN A.DPD_StockStmt ELSE 0 END DPD_StockStmt |
| ELSE | uncovered | Lines 126-126 | unavailable | CASE WHEN isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) THEN A.DPD_StockStmt ELSE 0 END DPD_StockStmt |
| CASE | uncovered | Lines 149-149 | unavailable | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| CASE_BRANCH | uncovered | Lines 149-149 | unavailable | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| CASE_BRANCH | uncovered | Lines 150-150 | unavailable | WHEN (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>= isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_NoCredit,0)>= isnull(A.DPD_Renewal,0) AND isnull(A... |
| CASE_BRANCH | uncovered | Lines 151-151 | unavailable | WHEN (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_Renewal,0) AND isnul... |
| CASE_BRANCH | uncovered | Lines 152-152 | unavailable | WHEN (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Renewal,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Renewal,0)>= isnull(A.DPD_Overdue,0) AND isnull(A.DP... |
| CASE_BRANCH | uncovered | Lines 153-153 | unavailable | WHEN (isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdue,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Overdue,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.DP... |
| ELSE | uncovered | Lines 154-154 | unavailable | ELSE isnull(A.DPD_StockStmt,0) END) |
| CASE | uncovered | Lines 169-169 | unavailable | (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN |
| CASE_BRANCH | uncovered | Lines 169-169 | unavailable | (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN |
| CASE_BRANCH | uncovered | Lines 170-170 | unavailable | WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN |
| CASE_BRANCH | uncovered | Lines 171-171 | unavailable | WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN |
| CASE_BRANCH | uncovered | Lines 172-172 | unavailable | WHEN dpd.DPD_Max >90 THEN |
| ELSE | uncovered | Lines 173-173 | unavailable | ELSE NULL |
| CASE | uncovered | Lines 175-175 | unavailable | ,A.SMA_REASON= (CASE |
| CASE_BRANCH | uncovered | Lines 176-176 | unavailable | WHEN A.FACILITYTYPE IN ( , ) AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN |
| CASE_BRANCH | uncovered | Lines 177-177 | unavailable | WHEN A.FACILITYTYPE IN ( , ) AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) THEN |
| CASE_BRANCH | uncovered | Lines 178-178 | unavailable | WHEN A.FACILITYTYPE IN ( , , , , ) AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) THEN |
| CASE_BRANCH | uncovered | Lines 179-179 | unavailable | WHEN A.FACILITYTYPE IN ( , ) AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 THEN |
| CASE_BRANCH | uncovered | Lines 180-180 | unavailable | WHEN A.FACILITYTYPE IN ( , ) AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) THEN |
| CASE_BRANCH | uncovered | Lines 181-181 | unavailable | WHEN A.FACILITYTYPE IN ( , ) AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) THEN |
| ELSE | covered_by_rule | Lines 183-183 | unavailable | ELSE |
| IF | uncovered | Lines 321-321 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | uncovered | Lines 324-324 | unavailable | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 324-324 | unavailable | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS= THEN 1 |
| CALCULATION | uncovered | Lines 324-324 | unavailable | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 325-325 | unavailable | WHEN SMA_CLASS= THEN 2 |
| CASE_BRANCH | uncovered | Lines 326-326 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE 0 END ) MAXSMA_CLASS |
| ELSE | uncovered | Lines 326-326 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE 0 END ) MAXSMA_CLASS |
| CALCULATION | uncovered | Lines 327-327 | unavailable | ,MIN(A.SMA_Dt) AS SMA_Dt |
| IF | uncovered | Lines 345-345 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | uncovered | Lines 348-348 | unavailable | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 348-348 | unavailable | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS= THEN 1 |
| CALCULATION | uncovered | Lines 348-348 | unavailable | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 349-349 | unavailable | WHEN SMA_CLASS= THEN 2 |
| CASE_BRANCH | uncovered | Lines 350-350 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE 0 END ) MAXSMA_CLASS |
| ELSE | uncovered | Lines 350-350 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE 0 END ) MAXSMA_CLASS |
| CALCULATION | uncovered | Lines 351-351 | unavailable | ,MIN(A.SMA_Dt) AS SMA_Dt |
| IF | covered_by_rule | Lines 364-364 | unavailable | IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) |
| IF | uncovered | Lines 370-370 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | uncovered | Lines 378-378 | unavailable | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 378-378 | unavailable | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 379-379 | unavailable | WHEN SMA_CLASS= THEN 2 |
| CASE_BRANCH | uncovered | Lines 380-380 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE SMA_CLASS END) |
| ELSE | uncovered | Lines 380-380 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE SMA_CLASS END) |
| IF | uncovered | Lines 450-450 | unavailable | if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) |
| ELSE | covered_by_rule | Lines 454-454 | unavailable | else |
| IF | uncovered | Lines 456-456 | unavailable | IF OBJECT_ID ( ) IS NOT NULL |
| CASE | uncovered | Lines 549-549 | unavailable | (CASE WHEN B.CustomerAcID IS NULL THEN 1 |
| CASE_BRANCH | uncovered | Lines 549-549 | unavailable | (CASE WHEN B.CustomerAcID IS NULL THEN 1 |
| CASE_BRANCH | uncovered | Lines 550-550 | unavailable | WHEN B.CustomerAcID IS NOT NULL AND A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 |
| IF | uncovered | Lines 587-587 | unavailable | if EXISTS ( select 1 from PRO.CUSTOMER_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) |
| ELSE | covered_by_rule | Lines 591-591 | unavailable | else |
| IF | uncovered | Lines 593-593 | unavailable | IF OBJECT_ID ( ) IS NOT NULL |
| CASE | uncovered | Lines 690-690 | unavailable | (CASE WHEN B.SourceSystemCustomerID IS NULL THEN 1 |
| CASE_BRANCH | uncovered | Lines 690-690 | unavailable | (CASE WHEN B.SourceSystemCustomerID IS NULL THEN 1 |
| CASE_BRANCH | uncovered | Lines 691-691 | unavailable | WHEN B.SourceSystemCustomerID IS NOT NULL AND A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 |
| CATCH | uncovered | Lines 760-760 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 772-772 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| temp_write_to_read | 00_main_body_2:embedded_01_02 / ##AccountCal | 00_main_body_4:embedded_03_31 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_2:embedded_01_02 / ##AccountCal | 00_main_body:embedded_02_17 / ##ACCOUNTCAL | high |
| temp_write_to_read | 00_main_body_2:embedded_01_02 / ##AccountCal | 00_main_body_4:embedded_06_34 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_2:embedded_01_02 / ##AccountCal | 00_main_body_4:embedded_09_37 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_2:embedded_01_02 / ##AccountCal | 00_main_body:embedded_05_20 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_4:embedded_01_29 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_5:chunk_text_01 / ##AccountCal | 00_main_body_4:embedded_03_31 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_5:chunk_text_01 / ##AccountCal | 00_main_body:embedded_02_17 / ##ACCOUNTCAL | high |
| temp_write_to_read | 00_main_body_5:chunk_text_01 / ##AccountCal | 00_main_body_4:embedded_06_34 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_5:chunk_text_01 / ##AccountCal | 00_main_body_4:embedded_09_37 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_5:chunk_text_01 / ##AccountCal | 00_main_body:embedded_05_20 / ##AccountCal | high |
| table_write_to_later_use | 00_main_body_7:chunk_text_01 / PRO.CUSTOMER_MOVEMENT_HISTORY | 00_main_body_6:chunk_text_02 / PRO.CUSTOMER_MOVEMENT_HISTORY | high |
| temp_write_to_read | 00_main_body_4:chunk_text_02 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_04_32 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:chunk_text_05 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body:embedded_03_18 / ##ACCOUNTCAL | 00_main_body_4:embedded_06_34 / ##AccountCal | high |
| temp_write_to_read | 00_main_body:embedded_03_18 / ##ACCOUNTCAL | 00_main_body_4:embedded_09_37 / ##AccountCal | high |
| temp_write_to_read | 00_main_body:embedded_03_18 / ##ACCOUNTCAL | 00_main_body:embedded_05_20 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_7:embedded_02_09 / ##ACCOUNTCAL | 00_main_body_4:embedded_06_34 / ##AccountCal | high |
| later_update_overrides_field | 00_main_body_7:embedded_02_09 / ##ACCOUNTCAL | 00_main_body:chunk_text_06 / ##ACCOUNTCAL | high |
| temp_write_to_read | 00_main_body_7:embedded_02_09 / ##ACCOUNTCAL | 00_main_body_4:embedded_09_37 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_7:embedded_02_09 / ##ACCOUNTCAL | 00_main_body:embedded_05_20 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_1:embedded_02_06 / #DPD | 00_main_body_2:chunk_text_01 / #DPD | high |
| temp_write_to_read | 00_main_body_1:embedded_03_07 / #DPD | 00_main_body_2:chunk_text_01 / #DPD | high |
| temp_write_to_read | 00_main_body:chunk_text_06 / ##ACCOUNTCAL | 00_main_body_4:embedded_09_37 / ##AccountCal | high |
| temp_write_to_read | 00_main_body:chunk_text_06 / ##ACCOUNTCAL | 00_main_body:embedded_05_20 / ##AccountCal | high |
| temp_write_to_read | 00_main_body_4:chunk_text_07 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_15_44 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_16_45 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_17_46 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_18_47 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_19_48 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_20_49 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_21_50 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_22_51 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body_4:embedded_23_52 / ##CUSTOMERCAL | 00_main_body_2:chunk_text_01 / ##CUSTOMERCAL | high |
| temp_write_to_read | 00_main_body:embedded_06_21 / #DPD | 00_main_body_2:chunk_text_01 / #DPD | high |
| temp_write_to_read | 00_main_body:embedded_07_22 / #DPD | 00_main_body_2:chunk_text_01 / #DPD | high |
| temp_write_to_read | 00_main_body:embedded_08_23 / #DPD | 00_main_body_2:chunk_text_01 / #DPD | high |
| temp_write_to_read | 00_main_body:embedded_09_24 / #DPD | 00_main_body_2:chunk_text_01 / #DPD | high |
| temp_write_to_read | 00_main_body:embedded_10_25 / #DPD | 00_main_body_2:chunk_text_01 / #DPD | high |
| temp_write_to_read | 00_main_body:chunk_text_13 / #DPD | 00_main_body_2:chunk_text_01 / #DPD | high |

Unresolved dependency candidates: 733. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 15
- **By rule type:** explicit = 15
- **By validation status:** unverified = 7, verified = 8

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Reconciliation Summary

- **Matched facts:** 2
- **Deterministic-only facts:** 47
- **LLM-only claims:** 3
- **Conflicts:** 6
- **Unresolved items:** 4
- **Review required:** Yes

### Review Items

- `CONFLICT` rule (`recon_17d08250bee3`): source_chunk_id - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_bc1080e18265`): source_chunk_id - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_2ed96d35e0aa`): source_chunk_id - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_1181a82b4014`): source_chunk_id, 00_main_body_4:chunk_text_07;00_main_body_4:embedded_04_32 - Deterministic evidence conflicts with the synthesized claim.
- `LLM_ONLY` rule (`recon_ee89d9f01650`): no direct provenance - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 91.62073770491801/100
- **Statement coverage:** 100 / 129 (77.5%)
- **Rule grounding coverage:** 12 / 15 (80.0%)
- **Decision-chain coverage:** 13 / 22 branches (59.1%)
- **Decision-chain coverage gaps:** 9 branch(es) require review (`(isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND    isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND  isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_StockStmt,0))`, `(isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>=  isnull(A.DPD_Overdrawn,0) AND    isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND    isnull(A.DPD_NoCredit,0)>=  isnull(A.DPD_Renewal,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_StockStmt,0))`, `(isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0)  AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND   isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_StockStmt,0))`, `(isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0)    AND isnull(A.DPD_Renewal,0)>=   isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0)  AND  isnull(A.DPD_Renewal,0)>=   isnull(A.DPD_Overdue,0)  AND isnull(A.DPD_Renewal,0) >=isnull(A.DPD_StockStmt ,0))`, `(isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0)    AND isnull(A.DPD_Overdue,0)>=   isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0)  AND  isnull(A.DPD_Overdue,0)>=   isnull(A.DPD_Renewal,0)  AND isnull(A.DPD_Overdue ,0)>=isnull(A.DPD_StockStmt ,0))`, and 4 more)
- **Conflicts:** 6
- **Contradictions:** 7
- **Review required items:** 20
- **Review required:** Yes

Deterministic decision-chain coverage is incomplete (59.1%).

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized rule affects different fields than the deterministic evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): Update         A
SET            A.ReviewDueDt=NULL,A.DPD_Renewal=0
FROM           ##ACCOUNTCAL A 
INNER JOIN     #DPD...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0  
  
  
  
----/* CALCULATE MAX DPD */  
  
  IF O...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.FLGSMA='Y'  
FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.FLGSMA='Y'  
FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.UCIF_ID =B.UCIF_ID  
WHERE B.FLGSMA='Y...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt  
FROM ##CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASSUc...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS   
FROM PRO.PREVSMASTATUS A  RIGHT OUTER JOIN  #SMACLASS B  
ON...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE  ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL  
    
  
  
 --IF OB...
- Technical extraction response reached the output limit; recovered facts may be incomplete.
- Commented-out logic found in source (19 block(s)) and excluded from extraction - not included in the business rules.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: dpd.DPD_Max BETWEEN 1 AND 30 THEN DATEADD(DAY, -dpd.DPD_MAX+1, @ProcessDate), dpd.DPD_Max BETWEEN 31 AND 60 THEN DATEADD(DAY, -dpd.DPD_MAX+1, @ProcessDate), dpd.DPD_Max BETWEEN 61 AND 90 THEN DATEADD(DAY, -dpd.DPD_MAX+1, @ProcessDate), dpd.DPD_Max > 90 THEN DATEADD(DAY, -dpd.DPD_MAX+1, @ProcessDate)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY END
- Synthesized in 3 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
