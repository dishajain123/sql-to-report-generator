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
| Run Timestamp | `2026-09-10T10:43:12.707741+00:00` |
| Object ID | `obj_6ed9993261c9` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_2560e4cefbbf` |
| Total LLM Calls | `8` |
| Successful Calls | `8` |
| Failed Calls | `0` |
| Prompt Tokens | `275731` |
| Completion Tokens | `27927` |
| Total Tokens | `303658` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 28307 | available |
| synthesis | 6 | 6 | 0 | 195893 | available |
| synthesis_revision | 1 | 1 | 0 | 79458 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Initialize temporary table [UNRESOLVED] (`rule_01`) | `Not specified` | Creates a temporary table to store DPD values for further processing. |
| 🔴 2 | Reset DPD_Max to zero [CONFLICT] (`rule_02`) | `DPD_Max` | Resets the DPD_Max field in the #DPD table to zero for all accounts. |
| 🔴 3 | Calculate maximum DPD [CONFLICT] (`rule_03`) | `DPD_Max` | Calculates the maximum DPD value for each account and updates the DPD_Max field in the #DPD table. |
| 🔴 4 | Reset SMA class [CONFLICT] (`rule_04`) | `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA` | Resets the SMA class, reason, date, and flag in the ##AccountCal table to null for all accounts. |
| 🟠 5 | Set ContiExcessDt and DPD_Overdrawn to zero [LLM_ONLY] (`rule_05`) | `ContiExcessDt, DPD_Overdrawn` | For accounts with DPD_Overdrawn less than or equal to 30, the ContiExcessDt and DPD_Overdrawn fields are set to zero. |
| 🟠 6 | Set ReviewDueDt and DPD_Renewal to zero [LLM_ONLY] (`rule_06`) | `ReviewDueDt, DPD_Renewal` | For accounts with DPD_Overdrawn less than or equal to 30, the ReviewDueDt and DPD_Renewal fields are set to zero. |
| 🔴 7 | Insert account details if DPD_Overdrawn or DPD_Overdue is greater than 0 [CONFLICT] (`rule_07`) | `AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_MAX` | Inserts account details into a temporary table if DPD_Overdrawn is greater than 30 or DPD_Overdue is greater than 0. |
| 🔴 8 | Reset negative DPD values to zero [CONFLICT] (`rule_08`) | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | Resets negative values of DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt to zero. |
| 🟠 9 | Assign SMA class based on overdue days [MATCHED] (`rule_09`) | `SMA_CLASS` | Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2. |
| 🟠 10 | Assign SMA class based on overdue days [MATCHED] (`rule_10`) | `SMA_CLASS` | Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2. |
| 🟠 11 | Assign SMA class based on overdue days [MATCHED] (`rule_11`) | `SMA_CLASS` | Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2. |
| 🟠 12 | Assign SMA class based on overdue days [LLM_ONLY] (`rule_12`) | `SMA_CLASS` | Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2. |
| 🟠 13 | Assign SMA reason based on facility type and overdue days [MATCHED] (`rule_13`) | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| 🟠 14 | Assign SMA reason based on facility type and overdue days [MATCHED] (`rule_14`) | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| 🟠 15 | Assign SMA reason based on facility type and overdue days [MATCHED] (`rule_15`) | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| 🟠 16 | Assign SMA reason based on facility type and overdue days [MATCHED] (`rule_16`) | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| 🟠 17 | Assign SMA reason based on facility type and overdue days [MATCHED] (`rule_17`) | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| 🟠 18 | Assign SMA reason based on facility type and overdue days [MATCHED] (`rule_18`) | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| 🟠 19 | Assign SMA reason based on facility type and overdue days [MATCHED] (`rule_19`) | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| 🟠 20 | Initialize customer fields [LLM_ONLY] (`rule_20`) | `FLGSMA, SMA_CLASS_KEY, SMA_DT` | Sets the FLGSMA, SMA_CLASS_KEY, and SMA_DT fields in the ##CUSTOMERCAL table to NULL. |
| 🔴 21 | Set FLGSMA to 'Y' [CONFLICT] (`rule_21`) | `FLGSMA` | Sets the FLGSMA field in the ##CUSTOMERCAL table to 'Y' for accounts that meet certain conditions. |
| 🔴 22 | Create temporary table #TEMPTABLE_SMACLASS [CONFLICT] (`rule_22`) | `Not specified` | Creates a temporary table #TEMPTABLE_SMACLASS to store aggregated data on SMA_CLASS and SMA_Dt for accounts that meet certain conditions. |
| 🔴 23 | Update SMA_CLASS_KEY and SMA_DT [CONFLICT] (`rule_23`) | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the data in the temporary table #TEMPTABLE_SMACLASS. |
| 🟠 24 | Delete existing SMA_MOVEMENT_HISTORY record [UNRESOLVED] (`rule_24`) | `Not specified` | Deletes the existing record in the PRO.SMA_MOVEMENT_HISTORY table for the given TIMEKEY if it exists. |
| 🟢 25 | Create temporary table #SMACLASS [MATCHED] (`rule_25`) | `Not specified` | Creates a temporary table #SMACLASS to store SMA_CLASS values for accounts that meet certain conditions. |
| 🟢 26 | Map SMA_CLASS to numeric codes [MATCHED] (`rule_26`) | `SMA_CLASS` | Updates the #SMACLASS table to map SMA_CLASS values to numeric codes. |
| 🟠 27 | Insert into SMA_MOVEMENT_HISTORY [LLM_ONLY] (`rule_27`) | `Not specified` | Inserts records into the PRO.SMA_MOVEMENT_HISTORY table to track changes in SMA_CLASS. |
| 🟠 28 | Truncate PREVSMASTATUS table [LLM_ONLY] (`rule_28`) | `Not specified` | Truncates the PRO.PREVSMASTATUS table to remove old records. |
| 🟢 29 | Update CustMoveDescription based on SYSASSETCLASSALT_KEY [MATCHED] (`rule_29`) | `CustMoveDescription` | Updates the CustMoveDescription field in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY. |
| 🟢 30 | Update SMA_CLASS based on FinalAssetClassAlt_Key [MATCHED] (`rule_30`) | `SMA_CLASS` | Updates the SMA_CLASS field in the ##AccountCal table based on the FinalAssetClassAlt_Key. |
| 🔴 31 | Update customer movement history [CONFLICT] (`rule_31`) | `EffectiveToTimeKey, MovementToDate` | Updates the effective to time key and movement to date in the customer movement history table for specific conditions. |
| 🟠 32 | Update account details for SMA Aqua Scheme [LLM_ONLY] (`rule_32`) | `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal` | Updates account details such as continuous excess date, DPD overdrawn, review due date, and DPD renewal for SMA Aqua Scheme. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Initialize temporary table (rule_01) | SELECT A.CustomerAcID,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 END DPD_NoCredit, CASE WH… | Not cited | 00_main_body | 00_main_body:chunk_text_01 | Needs Review |
| 2 | Reset DPD_Max to zero (rule_02) | UPDATE A SET A.DPD_Max=0 FROM #DPD A | Not cited | 00_main_body | 00_main_body:embedded_02_06 | Needs Review |
| 3 | Calculate maximum DPD (rule_03) | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0)… | Not cited | 00_main_body | 00_main_body:embedded_03_07 | Needs Review |
| 4 | Reset SMA class (rule_04) | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A | Not cited | 00_main_body | 00_main_body:embedded_01_02 | Needs Review |
| 5 | Set ContiExcessDt and DPD_Overdrawn to zero (rule_05) | ISNULL(A.DPD_Overdrawn,0) <= 30 | Not cited | Not cited | Not cited | Needs Review |
| 6 | Set ReviewDueDt and DPD_Renewal to zero (rule_06) | ISNULL(A.DPD_Overdrawn,0) <= 30 | Not cited | Not cited | Not cited | Needs Review |
| 7 | Insert account details if DPD_Overdrawn or DPD_Overdue is greater than 0 (rule_07) | isnull(A.DPD_Overdrawn,0)>30 OR Isnull(A.DPD_Overdue,0)>0 | Not cited | Not cited | Not cited | Needs Review |
| 8 | Reset negative DPD values to zero (rule_08) | isnull(DPD_IntService,0)<0 OR isnull(DPD_NoCredit,0)<0 OR isnull(DPD_Overdrawn,0)<0 OR isnull(DPD_Overdue,0)<0 OR isnull(DPD_Renewal,0)<0 OR isnull(DPD_StockStmt,0)<0 | Not cited | Not cited | Not cited | Needs Review |
| 9 | Assign SMA class based on overdue days (rule_09) | dpd.DPD_Max BETWEEN 1 AND 30 | Not cited | Not cited | Not cited | Needs Review |
| 10 | Assign SMA class based on overdue days (rule_10) | dpd.DPD_Max BETWEEN 31 AND 60 | Not cited | Not cited | Not cited | Needs Review |
| 11 | Assign SMA class based on overdue days (rule_11) | dpd.DPD_Max BETWEEN 61 AND 90 | Not cited | Not cited | Not cited | Needs Review |
| 12 | Assign SMA class based on overdue days (rule_12) | dpd.DPD_Max > 90 | Not cited | Not cited | Not cited | Needs Review |
| 13 | Assign SMA reason based on facility type and overdue days (rule_13) | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) | Not cited | Not cited | Not cited | Needs Review |
| 14 | Assign SMA reason based on facility type and overdue days (rule_14) | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) | Not cited | Not cited | Not cited | Needs Review |
| 15 | Assign SMA reason based on facility type and overdue days (rule_15) | A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) | Not cited | Not cited | Not cited | Needs Review |
| 16 | Assign SMA reason based on facility type and overdue days (rule_16) | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 | Not cited | Not cited | Not cited | Needs Review |
| 17 | Assign SMA reason based on facility type and overdue days (rule_17) | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) | Not cited | Not cited | Not cited | Needs Review |
| 18 | Assign SMA reason based on facility type and overdue days (rule_18) | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) | Not cited | Not cited | Not cited | Needs Review |
| 19 | Assign SMA reason based on facility type and overdue days (rule_19) | ELSE | Not cited | Not cited | Not cited | Needs Review |
| 20 | Initialize customer fields (rule_20) | UPDATE A SET A.FLGSMA=NULL,A.SMA_CLASS_KEY=NULL,A.SMA_DT=NULL FROM ##CUSTOMERCAL A | Not cited | Not cited | Not cited | Verified |
| 21 | Set FLGSMA to 'Y' (rule_21) | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID WHERE B.FLGSMA='Y' | Not cited | Not cited | Not cited | Verified |
| 22 | Create temporary table #TEMPTABLE_SMACLASS (rule_22) | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.Custome… | Not cited | Not cited | Not cited | Verified |
| 23 | Update SMA_CLASS_KEY and SMA_DT (rule_23) | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' | Not cited | Not cited | Not cited | Verified |
| 24 | Delete existing SMA_MOVEMENT_HISTORY record (rule_24) | IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY END | Not cited | Not cited | Not cited | Verified |
| 25 | Create temporary table #SMACLASS (rule_25) | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYID AND A.FLGSMA='Y' WHE… | Not cited | Not cited | Not cited | Verified |
| 26 | Map SMA_CLASS to numeric codes (rule_26) | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END) | Not cited | Not cited | Not cited | Verified |
| 27 | Insert into SMA_MOVEMENT_HISTORY (rule_27) | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SMA_CLASS IS NOT NULL AN… | Not cited | Not cited | Not cited | Verified |
| 28 | Truncate PREVSMASTATUS table (rule_28) | TRUNCATE TABLE PRO.PREVSMASTATUS | Not cited | Not cited | Not cited | Verified |
| 29 | Update CustMoveDescription based on SYSASSETCLASSALT_KEY (rule_29) | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1 | Not cited | Not cited | Not cited | Verified |
| 30 | Update SMA_CLASS based on FinalAssetClassAlt_Key (rule_30) | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL | Not cited | Not cited | Not cited | Verified |
| 31 | Update customer movement history (rule_31) | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey < @TIMEKEY AND EXISTS(SELECT 1 FROM #Customer_MOVEMENT_HISTORY AS BB WHERE AA.SourceSystemCustomerID = BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENT… | Not cited | Not cited | Not cited | Needs Review |
| 32 | Update account details for SMA Aqua Scheme (rule_32) | A.AccountEntityID = B.AccountEntityID | Not cited | Not cited | Not cited | Needs Review |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0149_0154:branch_001 | (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND    isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND  isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_StockStmt,0)) | source \| Lines 149-150 \| Statement 00_main_body_5:chunk_text_05 |
| case_0149_0154:branch_002 | (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>=  isnull(A.DPD_Overdrawn,0) AND    isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND    isnull(A.DPD_NoCredit,0)>=  isnull(A.DPD_Renewal,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_StockStmt,0)) | source \| Lines 150-151 |
| case_0149_0154:branch_003 | (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0)  AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND   isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_StockStmt,0)) | source \| Lines 151-152 |
| case_0149_0154:branch_004 | (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0)    AND isnull(A.DPD_Renewal,0)>=   isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0)  AND  isnull(A.DPD_Renewal,0)>=   isnull(A.DPD_Overdue,0)  AND isnull(A.DPD_Renewal,0) >=isnull(A.DPD_StockStmt ,0)) | source \| Lines 152-153 |
| case_0149_0154:branch_005 | (isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0)    AND isnull(A.DPD_Overdue,0)>=   isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0)  AND  isnull(A.DPD_Overdue,0)>=   isnull(A.DPD_Renewal,0)  AND isnull(A.DPD_Overdue ,0)>=isnull(A.DPD_StockStmt ,0)) | source \| Lines 153-154 |
| case_0149_0154:branch_006 | ELSE | source \| Line 154 |
| case_0169_0174:branch_001 | dpd.DPD_Max  BETWEEN 1 AND 30 | /tmp/tmp_4nbr_1w.sql \| Lines 169-170 \| Chunk 00_main_body_2 |
| case_0169_0174:branch_002 | dpd.DPD_Max  BETWEEN 31 AND 60 | /tmp/tmp_4nbr_1w.sql \| Lines 170-171 \| Chunk 00_main_body_2 |
| case_0169_0174:branch_003 | dpd.DPD_Max  BETWEEN 61 AND 90 | /tmp/tmp_4nbr_1w.sql \| Lines 171-172 \| Chunk 00_main_body_2 |
| case_0169_0174:branch_004 | dpd.DPD_Max >90 | /tmp/tmp_4nbr_1w.sql \| Lines 172-173 \| Chunk 00_main_body_2 |
| case_0169_0174:branch_005 | ELSE | /tmp/tmp_4nbr_1w.sql \| Lines 173-174 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_001 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmp_4nbr_1w.sql \| Lines 176-177 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_002 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmp_4nbr_1w.sql \| Lines 177-178 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_003 | A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmp_4nbr_1w.sql \| Lines 178-179 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_004 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 | /tmp/tmp_4nbr_1w.sql \| Lines 179-180 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_005 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmp_4nbr_1w.sql \| Lines 180-181 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_006 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) | /tmp/tmp_4nbr_1w.sql \| Lines 181-183 \| Chunk 00_main_body_2 |
| case_0175_0184:branch_007 | ELSE | /tmp/tmp_4nbr_1w.sql \| Lines 183-184 \| Chunk 00_main_body_2 |
| case_0378_0380:branch_001 | SMA_CLASS='SMA_0' | source \| Lines 378-379 |
| case_0378_0380:branch_002 | SMA_CLASS='SMA_1' | source \| Lines 379-380 |
| case_0378_0380:branch_003 | SMA_CLASS='SMA_2' | source \| Line 380 |
| case_0378_0380:branch_004 | ELSE | source \| Line 380 |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 378
- **Disposition:** covered_by_rule=142, technical_only=104, parser_failed=17, uncovered=115

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | covered_by_rule | Lines 1-3 | 00_main_body:chunk_text_01, 00_main_body | BEGIN SET NOCOUNT ON BEGIN TRY |
| SELECT | covered_by_rule | Lines 6-6 | 00_main_body:chunk_text_02, 00_main_body | DECLARE @ProcessDate DATE=(SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY=@TIMEKEY) |
| SELECT | covered_by_rule | Lines 8-14 | 00_main_body:chunk_text_03, 00_main_body | Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y') --------------START------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-------------... |
| SELECT | covered_by_rule | Lines 17-24 | 00_main_body:chunk_text_04, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| UPDATE | covered_by_rule | Lines 27-37 | 00_main_body:chunk_text_05, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| UPDATE | parser_failed | Lines 40-65 | 00_main_body:chunk_text_06, 00_main_body | Update A SET A.ReviewDueDt=NULL,A.DPD_Renewal=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_Key --WHERE C.EffectiveFromTimeKey<=@TIME... |
| SELECT | covered_by_rule | Lines 68-97 | 00_main_body:chunk_text_07, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| UPDATE | covered_by_rule | Lines 100-100 | 00_main_body:chunk_text_08, 00_main_body | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0 |
| UPDATE | covered_by_rule | Lines 102-102 | 00_main_body:chunk_text_09, 00_main_body | UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0 |
| UPDATE | covered_by_rule | Lines 104-104 | 00_main_body:chunk_text_10, 00_main_body | UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0 |
| UPDATE | covered_by_rule | Lines 106-106 | 00_main_body:chunk_text_11, 00_main_body | UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0 |
| UPDATE | covered_by_rule | Lines 108-108 | 00_main_body:chunk_text_12, 00_main_body | UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0 |
| UPDATE | parser_failed | Lines 110-117 | 00_main_body:chunk_text_13, 00_main_body | UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0 ----/* CALCULATE MAX DPD */ IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE |
| COMMAND | covered_by_rule | Lines 2-3 | 00_main_body:embedded_01_14, 00_main_body | SET NOCOUNT ON BEGIN TRY |
| SELECT | covered_by_rule | Lines 6-6 | 00_main_body:embedded_01_15, 00_main_body | DECLARE @ProcessDate DATE=(SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY=@TIMEKEY) |
| SELECT | covered_by_rule | Lines 8-14 | 00_main_body:embedded_01_16, 00_main_body | Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y') --------------START------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-------------... |
| SELECT | covered_by_rule | Lines 17-24 | 00_main_body:embedded_02_17, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| UPDATE | covered_by_rule | Lines 27-37 | 00_main_body:embedded_03_18, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| UPDATE | parser_failed | Lines 40-65 | 00_main_body:embedded_04_19, 00_main_body | Update A SET A.ReviewDueDt=NULL,A.DPD_Renewal=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_Key --WHERE C.EffectiveFromTimeKey<=@TIME... |
| SELECT | covered_by_rule | Lines 68-97 | 00_main_body:embedded_05_20, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| UPDATE | covered_by_rule | Lines 100-100 | 00_main_body:embedded_06_21, 00_main_body | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0 |
| UPDATE | covered_by_rule | Lines 102-102 | 00_main_body:embedded_07_22, 00_main_body | UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0 |
| UPDATE | covered_by_rule | Lines 104-104 | 00_main_body:embedded_08_23, 00_main_body | UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0 |
| UPDATE | covered_by_rule | Lines 106-106 | 00_main_body:embedded_09_24, 00_main_body | UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0 |
| UPDATE | covered_by_rule | Lines 108-108 | 00_main_body:embedded_10_25, 00_main_body | UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0 |
| UPDATE | parser_failed | Lines 110-117 | 00_main_body:embedded_11_26, 00_main_body | UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0 ----/* CALCULATE MAX DPD */ IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE |
| SELECT | covered_by_rule | Lines 1-21 | 00_main_body_1:chunk_text_01, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| UPDATE | covered_by_rule | Lines 24-29 | 00_main_body_1:chunk_text_02, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| UPDATE | covered_by_rule | Lines 32-40 | 00_main_body_1:chunk_text_03, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| UPDATE | covered_by_rule | Lines 44-48 | 00_main_body_1:chunk_text_04, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
| SELECT | covered_by_rule | Lines 1-21 | 00_main_body_1:embedded_01_05, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| UPDATE | covered_by_rule | Lines 24-29 | 00_main_body_1:embedded_02_06, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| UPDATE | covered_by_rule | Lines 32-40 | 00_main_body_1:embedded_03_07, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| UPDATE | covered_by_rule | Lines 44-48 | 00_main_body_1:embedded_04_08, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
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
| STATEMENT | uncovered | Lines 68-69 | 00_main_body_4:chunk_text_09, 00_main_body_4 | IF OBJECT_ID('TEMPDB..#SMACLASS') IS NOT NULL DROP TABLE #SMACLASS |
| SELECT | covered_by_rule | Lines 72-75 | 00_main_body_4:chunk_text_10, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| UPDATE | covered_by_rule | Lines 78-80 | 00_main_body_4:chunk_text_11, 00_main_body_4 | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END) |
| INSERT | covered_by_rule | Lines 83-87 | 00_main_body_4:chunk_text_12, 00_main_body_4 | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SM... |
| TRUNCATETABLE | covered_by_rule | Lines 90-90 | 00_main_body_4:chunk_text_13, 00_main_body_4 | TRUNCATE TABLE PRO.PREVSMASTATUS |
| INSERT | uncovered | Lines 93-101 | 00_main_body_4:chunk_text_14, 00_main_body_4 | INSERT INTO PRO.PREVSMASTATUS SELECT @TIMEKEY,CustomerAcID,SMA_CLASS FROM #SMACLASS --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY) --SELECT A.CustomerAc... |
| UPDATE | covered_by_rule | Lines 104-104 | 00_main_body_4:chunk_text_15, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1 |
| UPDATE | uncovered | Lines 106-106 | 00_main_body_4:chunk_text_16, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2 |
| UPDATE | uncovered | Lines 108-108 | 00_main_body_4:chunk_text_17, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3 |
| UPDATE | uncovered | Lines 110-110 | 00_main_body_4:chunk_text_18, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4 |
| UPDATE | uncovered | Lines 112-112 | 00_main_body_4:chunk_text_19, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5 |
| UPDATE | uncovered | Lines 114-114 | 00_main_body_4:chunk_text_20, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6 |
| UPDATE | uncovered | Lines 116-116 | 00_main_body_4:chunk_text_21, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1 |
| UPDATE | uncovered | Lines 118-118 | 00_main_body_4:chunk_text_22, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2 |
| UPDATE | uncovered | Lines 120-120 | 00_main_body_4:chunk_text_23, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3 |
| UPDATE | covered_by_rule | Lines 123-123 | 00_main_body_4:chunk_text_24, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL |
| UPDATE | uncovered | Lines 125-125 | 00_main_body_4:chunk_text_25, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL |
| UPDATE | uncovered | Lines 127-127 | 00_main_body_4:chunk_text_26, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL |
| UPDATE | uncovered | Lines 129-129 | 00_main_body_4:chunk_text_27, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL |
| UPDATE | uncovered | Lines 131-131 | 00_main_body_4:chunk_text_28, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL |
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
| INSERT | uncovered | Lines 93-93 | 00_main_body_4:embedded_13_42, 00_main_body_4 | INSERT INTO PRO.PREVSMASTATUS |
| SELECT | uncovered | Lines 94-101 | 00_main_body_4:embedded_14_43, 00_main_body_4 | SELECT @TIMEKEY,CustomerAcID,SMA_CLASS FROM #SMACLASS --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY) --SELECT A.CustomerAcID,A.FinalAssetClassAlt_Key,A.... |
| UPDATE | covered_by_rule | Lines 104-104 | 00_main_body_4:embedded_15_44, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1 |
| UPDATE | uncovered | Lines 106-106 | 00_main_body_4:embedded_16_45, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2 |
| UPDATE | uncovered | Lines 108-108 | 00_main_body_4:embedded_17_46, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3 |
| UPDATE | uncovered | Lines 110-110 | 00_main_body_4:embedded_18_47, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4 |
| UPDATE | uncovered | Lines 112-112 | 00_main_body_4:embedded_19_48, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5 |
| UPDATE | uncovered | Lines 114-114 | 00_main_body_4:embedded_20_49, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6 |
| UPDATE | uncovered | Lines 116-116 | 00_main_body_4:embedded_21_50, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1 |
| UPDATE | uncovered | Lines 118-118 | 00_main_body_4:embedded_22_51, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2 |
| UPDATE | uncovered | Lines 120-120 | 00_main_body_4:embedded_23_52, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3 |
| UPDATE | covered_by_rule | Lines 123-123 | 00_main_body_4:embedded_24_53, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL |
| UPDATE | uncovered | Lines 125-125 | 00_main_body_4:embedded_25_54, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL |
| UPDATE | uncovered | Lines 127-127 | 00_main_body_4:embedded_26_55, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL |
| UPDATE | uncovered | Lines 129-129 | 00_main_body_4:embedded_27_56, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL |
| UPDATE | uncovered | Lines 131-131 | 00_main_body_4:embedded_28_57, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL |
| UPDATE | parser_failed | Lines 1-39 | 00_main_body_5:chunk_text_01, 00_main_body_5 | UPDATE ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HISTORY') IS NOT NULL -- DROP TABLE #ACCOUNT_MOVEMENT_HISTORY -- SELECT CustomerAcID,FinalAssetClassAl... |
| UPDATE | covered_by_rule | Lines 41-62 | 00_main_body_5:chunk_text_02, 00_main_body_5 | else begin IF OBJECT_ID ('TEMPDB..#ACCOUNT_MOVEMENT_HISTORY') IS NOT NULL DROP TABLE #ACCOUNT_MOVEMENT_HISTORY CREATE TABLE #ACCOUNT_MOVEMENT_HISTORY ( [UCIF_ID] [varchar](50) NULL, [RefCustomerID] [varchar](50) NULL, [SourceSystemCustom... |
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
| UPDATE | covered_by_rule | Lines 32-53 | 00_main_body_6:chunk_text_03, 00_main_body_6 | else begin IF OBJECT_ID ('TEMPDB..#Customer_MOVEMENT_HISTORY') IS NOT NULL DROP TABLE #Customer_MOVEMENT_HISTORY CREATE TABLE #Customer_MOVEMENT_HISTORY ( [UCIF_ID] [varchar](50) NULL, [RefCustomerID] [varchar](50) NULL, [SourceSystemCus... |
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
| STATEMENT | uncovered | Lines 61-67 | 00_main_body_7:chunk_text_04, 00_main_body_7 | BEGIN CATCH DROP TABLE #TEMPTABLE_SMACLASS DROP TABLE #SMACLASS DROP TABLE #ACCOUNT_MOVEMENT_HISTORY DROP TABLE #Customer_MOVEMENT_HISTORY |
| UPDATE | parser_failed | Lines 70-74 | 00_main_body_7:chunk_text_05, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' END CATCH |
| SET | uncovered | Lines 76-77 | 00_main_body_7:chunk_text_06, 00_main_body_7 | SET NOCOUNT OFF END |
| STATEMENT | covered_by_rule | Lines 80-80 | 00_main_body_7:chunk_text_07, 00_main_body_7 | GO |
| UPDATE | uncovered | Lines 1-24 | 00_main_body_7:embedded_01_08, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| UPDATE | covered_by_rule | Lines 30-44 | 00_main_body_7:embedded_02_09, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| UPDATE | uncovered | Lines 51-57 | 00_main_body_7:embedded_03_10, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' -----------------Added for DashBoard 04-03-2021 --Update BANDAUDITSTATUS set Complet... |
| UPDATE | uncovered | Lines 70-72 | 00_main_body_7:embedded_04_11, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' |
| SET | uncovered | Lines 76-76 | 00_main_body_7:embedded_05_12, 00_main_body_7 | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 00_main_body:chunk_text_02, 00_main_body:chunk_text_02, 00_main_body | DECLARE @ProcessDate DATE=(SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY=@TIMEKEY) |
| READ | covered_by_rule | unavailable | 00_main_body:chunk_text_03, 00_main_body:chunk_text_03, 00_main_body | Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y') --------------START------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-------------... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_04, 00_main_body:chunk_text_04, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_04, 00_main_body:chunk_text_04, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_04, 00_main_body:chunk_text_04, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_05, 00_main_body:chunk_text_05, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_05, 00_main_body:chunk_text_05, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_05, 00_main_body:chunk_text_05, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:chunk_text_06, 00_main_body:chunk_text_06, 00_main_body | Update A SET A.ReviewDueDt=NULL,A.DPD_Renewal=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_Key --WHERE C.EffectiveFromTimeKey<=@TIME... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_07, 00_main_body:chunk_text_07, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_07, 00_main_body:chunk_text_07, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_08, 00_main_body:chunk_text_08, 00_main_body | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_09, 00_main_body:chunk_text_09, 00_main_body | UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_10, 00_main_body:chunk_text_10, 00_main_body | UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_11, 00_main_body:chunk_text_11, 00_main_body | UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body:chunk_text_12, 00_main_body:chunk_text_12, 00_main_body | UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:chunk_text_13, 00_main_body:chunk_text_13, 00_main_body | UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0 ----/* CALCULATE MAX DPD */ IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE |
| READ_TEMP | technical_only | unavailable | 00_main_body:embedded_02_17, 00_main_body:embedded_02_17, 00_main_body | SELECT A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt into #DPD_Aqua_SMA FROM ##ACCOUNTCAL A INNER JOIN DIMPRODUCT C ON A.ProductAlt_Key =C.ProductAlt_Key WHERE C.EffectiveFromTimeKey<=@TIMEKEY AND... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_03_18, 00_main_body:embedded_03_18, 00_main_body | Update A SET A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID WHERE ISNULL(A.DPD_Overdrawn,0)<= 30 --INNER JOIN DIMPRODUCT C --ON A.ProductAlt_Key =C.ProductAlt_... |
| READ_TEMP | technical_only | unavailable | 00_main_body:embedded_05_20, 00_main_body:embedded_05_20, 00_main_body | select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID, RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt, RefPeriodIntService,RefPeriodNoCredit,RefPeri... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_06_21, 00_main_body:embedded_06_21, 00_main_body | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_07_22, 00_main_body:embedded_07_22, 00_main_body | UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_08_23, 00_main_body:embedded_08_23, 00_main_body | UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_09_24, 00_main_body:embedded_09_24, 00_main_body | UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0 |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body:embedded_10_25, 00_main_body:embedded_10_25, 00_main_body | UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0 |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_1:chunk_text_01, 00_main_body_1:chunk_text_01, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_1:chunk_text_01, 00_main_body_1:chunk_text_01, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_1:chunk_text_02, 00_main_body_1:chunk_text_02, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_1:chunk_text_02, 00_main_body_1:chunk_text_02, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_1:chunk_text_03, 00_main_body_1:chunk_text_03, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_1:chunk_text_03, 00_main_body_1:chunk_text_03, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_1:chunk_text_04, 00_main_body_1:chunk_text_04, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_1:chunk_text_04, 00_main_body_1:chunk_text_04, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
| READ_TEMP | technical_only | unavailable | 00_main_body_1:embedded_01_05, 00_main_body_1:embedded_01_05, 00_main_body_1 | SELECT A.CustomerAcID ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 EN... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_1:embedded_02_06, 00_main_body_1:embedded_02_06, 00_main_body_1 | UPDATE A SET A.DPD_Max=0 FROM #DPD A ---- /*----------------FIND MAX DPD---------------------------------------*/ |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_1:embedded_03_07, 00_main_body_1:embedded_03_07, 00_main_body_1 | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_1:embedded_04_08, 00_main_body_1:embedded_04_08, 00_main_body_1 | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL FROM ##AccountCal A |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql / Lines 168-266 | 00_main_body_2:chunk_text_01, 00_main_body_2:chunk_text_01, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_2:embedded_01_02, 00_main_body_2:embedded_01_02, 00_main_body_2 | UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END) ,A.SMA_REASON... |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_01, 00_main_body_4:chunk_text_01, 00_main_body_4 | UPDATE A SET A.FLGSMA=NULL ,A.SMA_CLASS_KEY=NULL ,A.SMA_DT=NULL FROM ##CUSTOMERCAL A |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:chunk_text_02, 00_main_body_4:chunk_text_02, 00_main_body_4 | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID WHERE B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_03, 00_main_body_4:chunk_text_03, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_03, 00_main_body_4:chunk_text_03, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_03, 00_main_body_4:chunk_text_03, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_04, 00_main_body_4:chunk_text_04, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_04, 00_main_body_4:chunk_text_04, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_04, 00_main_body_4:chunk_text_04, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:chunk_text_05, 00_main_body_4:chunk_text_05, 00_main_body_4 | UPDATE A SET A.FLGSMA='Y' FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.UCIF_ID =B.UCIF_ID WHERE B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_06, 00_main_body_4:chunk_text_06, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_06, 00_main_body_4:chunk_text_06, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_06, 00_main_body_4:chunk_text_06, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| READ | uncovered | unavailable | 00_main_body_4:chunk_text_07, 00_main_body_4:chunk_text_07, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID WHERE A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:chunk_text_07, 00_main_body_4:chunk_text_07, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID WHERE A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN |
| DELETE | covered_by_rule | unavailable | 00_main_body_4:chunk_text_08, 00_main_body_4:chunk_text_08, 00_main_body_4 | DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY END |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_10, 00_main_body_4:chunk_text_10, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_10, 00_main_body_4:chunk_text_10, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_10, 00_main_body_4:chunk_text_10, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_11, 00_main_body_4:chunk_text_11, 00_main_body_4 | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END) |
| INSERT | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_12, 00_main_body_4:chunk_text_12, 00_main_body_4 | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SM... |
| TRUNCATE | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_13, 00_main_body_4:chunk_text_13, 00_main_body_4 | TRUNCATE TABLE PRO.PREVSMASTATUS |
| INSERT | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_14, 00_main_body_4:chunk_text_14, 00_main_body_4 | INSERT INTO PRO.PREVSMASTATUS SELECT @TIMEKEY,CustomerAcID,SMA_CLASS FROM #SMACLASS --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY) --SELECT A.CustomerAc... |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_15, 00_main_body_4:chunk_text_15, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_16, 00_main_body_4:chunk_text_16, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_17, 00_main_body_4:chunk_text_17, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_18, 00_main_body_4:chunk_text_18, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_19, 00_main_body_4:chunk_text_19, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_20, 00_main_body_4:chunk_text_20, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_21, 00_main_body_4:chunk_text_21, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_22, 00_main_body_4:chunk_text_22, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_23, 00_main_body_4:chunk_text_23, 00_main_body_4 | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3 |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_24, 00_main_body_4:chunk_text_24, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_25, 00_main_body_4:chunk_text_25, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_26, 00_main_body_4:chunk_text_26, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_27, 00_main_body_4:chunk_text_27, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:chunk_text_28, 00_main_body_4:chunk_text_28, 00_main_body_4 | UPDATE ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_01_29, 00_main_body_4:embedded_01_29, 00_main_body_4 | UPDATE A SET A.FLGSMA=NULL ,A.SMA_CLASS_KEY=NULL ,A.SMA_DT=NULL FROM ##CUSTOMERCAL A |
| READ_TEMP | technical_only | unavailable | 00_main_body_4:embedded_03_31, 00_main_body_4:embedded_03_31, 00_main_body_4 | SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASS FROM ##AccountCal A INNER JOIN ##CUS... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_04_32, 00_main_body_4:embedded_04_32, 00_main_body_4 | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' |
| READ_TEMP | technical_only | unavailable | 00_main_body_4:embedded_06_34, 00_main_body_4:embedded_06_34, 00_main_body_4 | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLASS ,MIN(A.SMA_Dt) AS SMA_Dt INTO #TEMPTABLE_SMACLASSUcif FROM ##AccountCal A INNER JOIN ##CUSTOMER... |
| DELETE | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:embedded_08_36, 00_main_body_4:embedded_08_36, 00_main_body_4 | DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY |
| READ_TEMP | technical_only | unavailable | 00_main_body_4:embedded_09_37, 00_main_body_4:embedded_09_37, 00_main_body_4 | SELECT A.CustomerAcID,ISNULL(A.SMA_CLASS,CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')) SMA_CLASS INTO #SMACLASS FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYI... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_4:embedded_10_38, 00_main_body_4:embedded_10_38, 00_main_body_4 | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END) |
| INSERT | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:embedded_11_39, 00_main_body_4:embedded_11_39, 00_main_body_4 | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:embedded_12_40, 00_main_body_4:embedded_12_40, 00_main_body_4 | SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:embedded_12_40, 00_main_body_4:embedded_12_40, 00_main_body_4 | SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS FROM PRO.PREVSMASTATUS A RIGHT OUTER JOIN #SMACLASS B ON A.CustomerAcID=B.CustomerAcID WHERE B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') |
| INSERT | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:embedded_13_42, 00_main_body_4:embedded_13_42, 00_main_body_4 | INSERT INTO PRO.PREVSMASTATUS |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_4:embedded_14_43, 00_main_body_4:embedded_14_43, 00_main_body_4 | SELECT @TIMEKEY,CustomerAcID,SMA_CLASS FROM #SMACLASS --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY) --SELECT A.CustomerAcID,A.FinalAssetClassAlt_Key,A.... |
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
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:chunk_text_03, 00_main_body_5:chunk_text_03, 00_main_body_5 | INSERT INTO #ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementF... |
| INSERT | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:chunk_text_04, 00_main_body_5:chunk_text_04, 00_main_body_5 | INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus ,TotOsAcc ,Moveme... |
| UPDATE | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:chunk_text_05, 00_main_body_5:chunk_text_05, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| READ | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:chunk_text_05, 00_main_body_5:chunk_text_05, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:chunk_text_05, 00_main_body_5:chunk_text_05, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:embedded_02_07, 00_main_body_5:embedded_02_07, 00_main_body_5 | INSERT INTO #ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementF... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:embedded_03_08, 00_main_body_5:embedded_03_08, 00_main_body_5 | SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey ,SMA_CLASS AS MovementFromStatus ,SMA_CLASS AS MovementToStatus ,ISNULL(Balance,0)... |
| INSERT | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:embedded_04_09, 00_main_body_5:embedded_04_09, 00_main_body_5 | INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus ,TotOsAcc ,Moveme... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:embedded_05_10, 00_main_body_5:embedded_05_10, 00_main_body_5 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNUL... |
| READ | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_5:embedded_05_10, 00_main_body_5:embedded_05_10, 00_main_body_5 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNUL... |
| UPDATE | uncovered | unavailable | 00_main_body_5:embedded_06_11, 00_main_body_5:embedded_06_11, 00_main_body_5 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON... |
| READ_TEMP | technical_only | unavailable | 00_main_body_6:chunk_text_01, 00_main_body_6:chunk_text_01, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| UPDATE | uncovered | unavailable | 00_main_body_6:chunk_text_01, 00_main_body_6:chunk_text_01, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| READ | uncovered | unavailable | 00_main_body_6:chunk_text_02, 00_main_body_6:chunk_text_02, 00_main_body_6 | if EXISTS ( select 1 from PRO.CUSTOMER_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA' end |
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:chunk_text_04, 00_main_body_6:chunk_text_04, 00_main_body_6 | INSERT INTO #Customer_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, totOsCust ,MovementFr... |
| INSERT | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:chunk_text_05, 00_main_body_6:chunk_text_05, 00_main_body_6 | INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust ,Movemen... |
| UPDATE | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:chunk_text_06, 00_main_body_6:chunk_text_06, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| READ | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:chunk_text_06, 00_main_body_6:chunk_text_06, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:chunk_text_06, 00_main_body_6:chunk_text_06, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| UPDATE | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:embedded_01_07, 00_main_body_6:embedded_01_07, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| READ | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:embedded_01_07, 00_main_body_6:embedded_01_07, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:embedded_01_07, 00_main_body_6:embedded_01_07, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND A... |
| INSERT_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:embedded_02_08, 00_main_body_6:embedded_02_08, 00_main_body_6 | INSERT INTO #Customer_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, totOsCust ,MovementFr... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:embedded_03_09, 00_main_body_6:embedded_03_09, 00_main_body_6 | SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey ,CustMoveDescription AS MovementFromStatus ,CustMoveDescription AS MovementToStatus ,... |
| INSERT | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:embedded_04_10, 00_main_body_6:embedded_04_10, 00_main_body_6 | INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY ( UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust ,Movemen... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:embedded_05_11, 00_main_body_6:embedded_05_11, 00_main_body_6 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNULL(A... |
| READ | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_6:embedded_05_11, 00_main_body_6:embedded_05_11, 00_main_body_6 | SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus,A.MovementFromStatus), A.MovementToStatus, ISNULL(A... |
| UPDATE | uncovered | unavailable | 00_main_body_6:embedded_06_12, 00_main_body_6:embedded_06_12, 00_main_body_6 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B O... |
| READ_TEMP | technical_only | unavailable | 00_main_body_7:chunk_text_01, 00_main_body_7:chunk_text_01, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| UPDATE | uncovered | unavailable | 00_main_body_7:chunk_text_01, 00_main_body_7:chunk_text_01, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| UPDATE_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_7:chunk_text_02, 00_main_body_7:chunk_text_02, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| READ | covered_by_rule | /tmp/tmp_4nbr_1w.sql | 00_main_body_7:chunk_text_02, 00_main_body_7:chunk_text_02, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_7:chunk_text_02, 00_main_body_7:chunk_text_02, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| UPDATE | uncovered | unavailable | 00_main_body_7:chunk_text_03, 00_main_body_7:chunk_text_03, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' -----------------Added for DashBoard 04-03-2021 --Update BANDAUDITSTATUS set Complet... |
| UPDATE | uncovered | unavailable | 00_main_body_7:chunk_text_05, 00_main_body_7:chunk_text_05, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' END CATCH |
| UPDATE | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_7:embedded_01_08, 00_main_body_7:embedded_01_08, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| READ | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_7:embedded_01_08, 00_main_body_7:embedded_01_08, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| READ_TEMP | technical_only | /tmp/tmp_4nbr_1w.sql | 00_main_body_7:embedded_01_08, 00_main_body_7:embedded_01_08, 00_main_body_7 | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA WHERE AA.EffectiveToTimeKey = 49999 AND... |
| UPDATE_TEMP | technical_only | unavailable | 00_main_body_7:embedded_02_09, 00_main_body_7:embedded_02_09, 00_main_body_7 | Update A SET A.ContiExcessDt=B.ContiExcessDt,A.DPD_Overdrawn=B.DPD_Overdrawn,A.ReviewDueDt=B.ReviewDueDt,A.DPD_Renewal=B.DPD_Renewal FROM ##ACCOUNTCAL A inner join #DPD_Aqua_SMA B on A.AccountEntityID=B.AccountEntityID --WHERE ISNULL(B.D... |
| UPDATE | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_7:embedded_03_10, 00_main_body_7:embedded_03_10, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' -----------------Added for DashBoard 04-03-2021 --Update BANDAUDITSTATUS set Complet... |
| UPDATE | uncovered | /tmp/tmp_4nbr_1w.sql | 00_main_body_7:embedded_04_11, 00_main_body_7:embedded_04_11, 00_main_body_7 | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' |
| CASE | covered_by_rule | Lines 149-150 | 00_main_body_5:chunk_text_05 | (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.... |
| CASE | covered_by_rule | Lines 150-151 | unavailable | (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>= isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_NoCredit,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.DPD_... |
| CASE | covered_by_rule | Lines 151-152 | unavailable | (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.D... |
| CASE | covered_by_rule | Lines 152-153 | unavailable | (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Renewal,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Renewal,0)>= isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Ren... |
| CASE | covered_by_rule | Lines 153-154 | unavailable | (isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdue,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Overdue,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Ove... |
| ELSE | covered_by_rule | Lines 154-154 | unavailable | ELSE |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 169-170 | 00_main_body_2 | dpd.DPD_Max BETWEEN 1 AND 30 |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 170-171 | 00_main_body_2 | dpd.DPD_Max BETWEEN 31 AND 60 |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 171-172 | 00_main_body_2 | dpd.DPD_Max BETWEEN 61 AND 90 |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 172-173 | 00_main_body_2 | dpd.DPD_Max >90 |
| ELSE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 173-174 | 00_main_body_2 | ELSE |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 176-177 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 177-178 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 178-179 | 00_main_body_2 | A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 179-180 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 180-181 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) |
| CASE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 181-183 | 00_main_body_2 | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) |
| ELSE | covered_by_rule | /tmp/tmp_4nbr_1w.sql / Lines 183-184 | 00_main_body_2 | ELSE |
| CASE | covered_by_rule | Lines 378-379 | unavailable | SMA_CLASS='SMA_0' |
| CASE | covered_by_rule | Lines 379-380 | unavailable | SMA_CLASS='SMA_1' |
| CASE | covered_by_rule | Lines 380-380 | unavailable | SMA_CLASS='SMA_2' |
| ELSE | covered_by_rule | Lines 380-380 | unavailable | ELSE |
| IF | uncovered | Lines 24-24 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| IF | uncovered | Lines 72-72 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| IF | uncovered | Lines 117-117 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | covered_by_rule | Lines 121-121 | unavailable | ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, |
| CASE_BRANCH | covered_by_rule | Lines 121-121 | unavailable | ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, |
| ELSE | covered_by_rule | Lines 121-121 | unavailable | ,CASE WHEN isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) THEN A.DPD_IntService ELSE 0 END DPD_IntService, |
| CASE | covered_by_rule | Lines 122-122 | unavailable | CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 END DPD_NoCredit, |
| CASE_BRANCH | covered_by_rule | Lines 122-122 | unavailable | CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 END DPD_NoCredit, |
| ELSE | covered_by_rule | Lines 122-122 | unavailable | CASE WHEN isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) THEN A.DPD_NoCredit ELSE 0 END DPD_NoCredit, |
| CASE | covered_by_rule | Lines 123-123 | unavailable | CASE WHEN isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn ,0) THEN A.DPD_Overdrawn ELSE 0 END DPD_Overdrawn, |
| CASE_BRANCH | covered_by_rule | Lines 123-123 | unavailable | CASE WHEN isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn ,0) THEN A.DPD_Overdrawn ELSE 0 END DPD_Overdrawn, |
| ELSE | covered_by_rule | Lines 123-123 | unavailable | CASE WHEN isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn ,0) THEN A.DPD_Overdrawn ELSE 0 END DPD_Overdrawn, |
| CASE | covered_by_rule | Lines 124-124 | unavailable | CASE WHEN isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue ,0) THEN A.DPD_Overdue ELSE 0 END DPD_Overdue , |
| CASE_BRANCH | covered_by_rule | Lines 124-124 | unavailable | CASE WHEN isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue ,0) THEN A.DPD_Overdue ELSE 0 END DPD_Overdue , |
| ELSE | covered_by_rule | Lines 124-124 | unavailable | CASE WHEN isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue ,0) THEN A.DPD_Overdue ELSE 0 END DPD_Overdue , |
| CASE | covered_by_rule | Lines 125-125 | unavailable | CASE WHEN isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview ,0) THEN A.DPD_Renewal ELSE 0 END DPD_Renewal , |
| CASE_BRANCH | covered_by_rule | Lines 125-125 | unavailable | CASE WHEN isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview ,0) THEN A.DPD_Renewal ELSE 0 END DPD_Renewal , |
| ELSE | covered_by_rule | Lines 125-125 | unavailable | CASE WHEN isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview ,0) THEN A.DPD_Renewal ELSE 0 END DPD_Renewal , |
| CASE | covered_by_rule | Lines 126-126 | unavailable | CASE WHEN isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) THEN A.DPD_StockStmt ELSE 0 END DPD_StockStmt |
| CASE_BRANCH | covered_by_rule | Lines 126-126 | unavailable | CASE WHEN isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) THEN A.DPD_StockStmt ELSE 0 END DPD_StockStmt |
| ELSE | covered_by_rule | Lines 126-126 | unavailable | CASE WHEN isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) THEN A.DPD_StockStmt ELSE 0 END DPD_StockStmt |
| CASE | covered_by_rule | Lines 149-149 | unavailable | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| CASE_BRANCH | covered_by_rule | Lines 149-149 | unavailable | UPDATE A SET A.DPD_Max= (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=is... |
| CASE_BRANCH | covered_by_rule | Lines 150-150 | unavailable | WHEN (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>= isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_NoCredit,0)>= isnull(A.DPD_Renewal,0) AND isnull(A... |
| CASE_BRANCH | covered_by_rule | Lines 151-151 | unavailable | WHEN (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Overdrawn,0)>= isnull(A.DPD_Renewal,0) AND isnul... |
| CASE_BRANCH | covered_by_rule | Lines 152-152 | unavailable | WHEN (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Renewal,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Renewal,0)>= isnull(A.DPD_Overdue,0) AND isnull(A.DP... |
| CASE_BRANCH | covered_by_rule | Lines 153-153 | unavailable | WHEN (isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdue,0)>= isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Overdue,0)>= isnull(A.DPD_Renewal,0) AND isnull(A.DP... |
| ELSE | covered_by_rule | Lines 154-154 | unavailable | ELSE isnull(A.DPD_StockStmt,0) END) |
| CASE | covered_by_rule | Lines 169-169 | unavailable | (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN |
| CASE_BRANCH | covered_by_rule | Lines 169-169 | unavailable | (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN |
| CASE_BRANCH | covered_by_rule | Lines 170-170 | unavailable | WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN |
| CASE_BRANCH | covered_by_rule | Lines 171-171 | unavailable | WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN |
| CASE_BRANCH | covered_by_rule | Lines 172-172 | unavailable | WHEN dpd.DPD_Max >90 THEN |
| ELSE | covered_by_rule | Lines 173-173 | unavailable | ELSE NULL |
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
| CASE_BRANCH | covered_by_rule | Lines 326-326 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE 0 END ) MAXSMA_CLASS |
| ELSE | covered_by_rule | Lines 326-326 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE 0 END ) MAXSMA_CLASS |
| CALCULATION | covered_by_rule | Lines 327-327 | unavailable | ,MIN(A.SMA_Dt) AS SMA_Dt |
| IF | uncovered | Lines 345-345 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | uncovered | Lines 348-348 | unavailable | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 348-348 | unavailable | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS= THEN 1 |
| CALCULATION | uncovered | Lines 348-348 | unavailable | SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 349-349 | unavailable | WHEN SMA_CLASS= THEN 2 |
| CASE_BRANCH | covered_by_rule | Lines 350-350 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE 0 END ) MAXSMA_CLASS |
| ELSE | covered_by_rule | Lines 350-350 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE 0 END ) MAXSMA_CLASS |
| CALCULATION | covered_by_rule | Lines 351-351 | unavailable | ,MIN(A.SMA_Dt) AS SMA_Dt |
| IF | covered_by_rule | Lines 364-364 | unavailable | IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) |
| IF | uncovered | Lines 370-370 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE | uncovered | Lines 378-378 | unavailable | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 378-378 | unavailable | UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS= THEN 1 |
| CASE_BRANCH | uncovered | Lines 379-379 | unavailable | WHEN SMA_CLASS= THEN 2 |
| CASE_BRANCH | covered_by_rule | Lines 380-380 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE SMA_CLASS END) |
| ELSE | covered_by_rule | Lines 380-380 | unavailable | WHEN SMA_CLASS= THEN 3 ELSE SMA_CLASS END) |
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

- **Total business rules:** 32
- **By rule type:** explicit = 32
- **By validation status:** unverified = 21, verified = 11

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Reconciliation Summary

- **Matched facts:** 14
- **Deterministic-only facts:** 77
- **LLM-only claims:** 7
- **Conflicts:** 9
- **Unresolved items:** 2
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_871d8896862b`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_ffcecdb68377`): no direct provenance - No deterministic evidence was found for this claim.
- `CONFLICT` rule (`recon_f8f713f1c8a0`): 00_main_body:embedded_05_20 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_918218eb6aca`): 00_main_body:embedded_06_21;00_main_body:embedded_07_22;00_main_body:embedded_08_23;00_main_body:embedded_09_24;00_main_body:embedded_10_25 - Deterministic evidence conflicts with the synthesized claim.
- `UNRESOLVED` rule (`recon_b5a00acd3ee8`): 00_main_body, 00_main_body:chunk_text_02;00_main_body:chunk_text_03;00_main_body:chunk_text_04;00_main_body:chunk_text_05;00_main_body:chunk_text_06;00_main_body:chunk_text_07;00_main_body:chunk_text_08;00_main_body:chunk_text_09;00_main_body:chunk_text_10;00_main_body:chunk_text_11;00_main_body:chunk_text_12;00_main_body:chunk_text_13;00_main_body:embedded_02_17;00_main_body:embedded_03_18;00_main_body:embedded_05_20;00_main_body:embedded_06_21;00_main_body:embedded_07_22;00_main_body:embedded_08_23;00_main_body:embedded_09_24;00_main_body:embedded_10_25 - Deterministic evidence exists, but comparison was not reliable enough for a match.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 95.15006147540984/100
- **Statement coverage:** 100 / 129 (77.5%)
- **Rule grounding coverage:** 25 / 32 (78.1%)
- **Decision-chain coverage:** 19 / 22 branches (86.4%)
- **Decision-chain coverage gaps:** 3 branch(es) require review (`(isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0)    AND isnull(A.DPD_Renewal,0)>=   isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0)  AND  isnull(A.DPD_Renewal,0)>=   isnull(A.DPD_Overdue,0)  AND isnull(A.DPD_Renewal,0) >=isnull(A.DPD_StockStmt ,0))`, `(isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0)    AND isnull(A.DPD_Overdue,0)>=   isnull(A.DPD_IntService,0)  AND  isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0)  AND  isnull(A.DPD_Overdue,0)>=   isnull(A.DPD_Renewal,0)  AND isnull(A.DPD_Overdue ,0)>=isnull(A.DPD_StockStmt ,0))`, `dpd.DPD_Max >90`)
- **Conflicts:** 9
- **Contradictions:** 11
- **Review required items:** 29
- **Review required:** Yes

Deterministic decision-chain coverage is incomplete (86.4%).

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized rule affects different fields than the deterministic evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.

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
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: isnull(DPD_IntService,0)<0 OR isnull(DPD_NoCredit,0)<0 OR isnull(DPD_Overdrawn,0)<0 OR isnull(DPD_Overdue,0)<0 OR isnull(DPD_Renewal,0)<0 OR isnull(DPD_StockStmt,0)<0
- Synthesis response reached the output limit; recovered rules may be incomplete.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY END
- Synthesized in 6 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
