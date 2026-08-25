## Object Overview

- **Object Name:** `SMA_MARKING`
- **Object Type:** Procedure
- **SQL Dialect:** SQL Server T-SQL
- **Parameters:**

| Parameter | Direction | Datatype |
|---|---|---|
| `@TIMEKEY` | IN | INT |

## Purpose Summary

This procedure determines and updates the Special Mention Account (SMA) classification for loan and advance accounts, based on overdue and non-servicing criteria, in line with regulatory and internal policy requirements. It ensures that accounts are correctly marked for SMA status, records the reasons for degradation, and maintains historical movement for both account and customer levels. The process also updates related status and description fields to support downstream reporting and compliance monitoring.

## Tables Read

| Table Name | Business Context | Filter Conditions |
|---|---|---|
| `SYSDAYMATRIX` | DATE | TIMEKEY = @TIMEKEY |
| `dbo.Automate_Advances` | Timekey-1 | EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA |
| `#DPD_Aqua_SMA` | A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt | C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(C.SchemeType, '') = 'ODA' AND COALESCE(c.FacilityType, '') IN ('CC', 'OD')) AND COALESCE(A.REFPERIODOVERDRAWN, 91) = 91 AND COALESCE(A.FinalAssetClassAlt_Key, 1) = 1; INNER DIMPRODUCT ON A.ProductAlt_Key = C.ProductAlt_Key |
| `##ACCOUNTCAL` | A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt | C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(C.SchemeType, '') = 'ODA' AND COALESCE(c.FacilityType, '') IN ('CC', 'OD')) AND COALESCE(A.REFPERIODOVERDRAWN, 91) = 91 AND COALESCE(A.FinalAssetClassAlt_Key, 1) = 1; INNER DIMPRODUCT ON A.ProductAlt_Key = C.ProductAlt_Key |
| `DIMPRODUCT` | A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt | C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(C.SchemeType, '') = 'ODA' AND COALESCE(c.FacilityType, '') IN ('CC', 'OD')) AND COALESCE(A.REFPERIODOVERDRAWN, 91) = 91 AND COALESCE(A.FinalAssetClassAlt_Key, 1) = 1; INNER DIMPRODUCT ON A.ProductAlt_Key = C.ProductAlt_Key |
| `#DPD_Aqua_SMA` | A.AccountEntityID, B.AccountEntityID | COALESCE(A.DPD_Overdrawn, 0) <= 30; INNER DPD_Aqua_SMA ON A.AccountEntityID = B.AccountEntityID |
| `#DPD` | AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, 0 AS DPD_IntService, 0 AS DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, 0 AS DPD_Renewal, 0 AS DPD_StockStmt, 0 AS DPD_MAX | COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0 |
| `##AccountCal` | AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, 0 AS DPD_IntService, 0 AS DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, 0 AS DPD_Renewal, 0 AS DPD_StockStmt, 0 AS DPD_MAX | COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0 |
| `##ACCOUNTCAL` | A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt 
into           #DPD_Aqua_SMA | C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD')) AND ISNULL(A.REFPERIODOVERDRAWN,91)=91 AND ISNULL(A.FinalAssetClassAlt_Key,1)=1 |
| `##AccountCal` | AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, 0 AS DPD_IntService, 0 AS DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, 0 AS DPD_Renewal, 0 AS DPD_StockStmt, 0 AS DPD_MAX  
 INTO #DPD | isnull(A.DPD_Overdrawn,0)>30 OR Isnull(A.DPD_Overdue,0)>0 |
| `#TEMPTABLE` | A.CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.RefPeriodNoCredit, 0) THEN A.DPD_NoCredit ELSE 0 END AS DPD_NoCredit, CASE WHEN COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.RefPeriodOverDrawn, 0) THEN A.DPD_Overdrawn ELSE 0 END AS DPD_Overdrawn, CASE WHEN COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.RefPeriodOverdue, 0) THEN A.DPD_Overdue ELSE 0 END AS DPD_Overdue, CASE WHEN COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.RefPeriodReview, 0) THEN A.DPD_Renewal ELSE 0 END AS DPD_Renewal, CASE WHEN COALESCE(A.DPD_StockStmt, 0) >= COALESCE(A.RefPeriodStkStatement, 0) THEN A.DPD_StockStmt ELSE 0 END AS DPD_StockStmt | (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0)) |
| `#DPD` | A.CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.RefPeriodNoCredit, 0) THEN A.DPD_NoCredit ELSE 0 END AS DPD_NoCredit, CASE WHEN COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.RefPeriodOverDrawn, 0) THEN A.DPD_Overdrawn ELSE 0 END AS DPD_Overdrawn, CASE WHEN COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.RefPeriodOverdue, 0) THEN A.DPD_Overdue ELSE 0 END AS DPD_Overdue, CASE WHEN COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.RefPeriodReview, 0) THEN A.DPD_Renewal ELSE 0 END AS DPD_Renewal, CASE WHEN COALESCE(A.DPD_StockStmt, 0) >= COALESCE(A.RefPeriodStkStatement, 0) THEN A.DPD_StockStmt ELSE 0 END AS DPD_StockStmt | (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0)) |
| `#DPD` | A.CustomerAcID, CASE WHEN  isnull(A.DPD_IntService, 0)>=isnull(A.RefPeriodIntService, 0)  THEN A.DPD_IntService  ELSE 0   END DPD_IntService, CASE WHEN  isnull(A.DPD_NoCredit, 0)>=isnull(A.RefPeriodNoCredit, 0)   THEN A.DPD_NoCredit    ELSE 0   END DPD_NoCredit, CASE WHEN  isnull(A.DPD_Overdrawn, 0)>=isnull(A.RefPeriodOverDrawn, 0)     THEN A.DPD_Overdrawn   ELSE 0   END DPD_Overdrawn, CASE WHEN  isnull(A.DPD_Overdue, 0)>=isnull(A.RefPeriodOverdue, 0)      THEN A.DPD_Overdue     ELSE 0   END DPD_Overdue, CASE WHEN  isnull(A.DPD_Renewal, 0)>=isnull(A.RefPeriodReview, 0)   THEN A.DPD_Renewal     ELSE 0   END  DPD_Renewal, CASE WHEN  isnull(A.DPD_StockStmt, 0)>=isnull(A.RefPeriodStkStatement, 0)       THEN A.DPD_StockStmt   ELSE 0   END DPD_StockStmt    
    INTO #TEMPTABLE | ( isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) ) |
| `##CUSTOMERCAL` | dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0; INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId |
| `AdvAcBasicDetail` | dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0; INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId |
| `#DPD` | dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0; INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId |
| `#TEMPTABLE_SMACLASS` | A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y' |
| `##AccountCal` | A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y' |
| `##CUSTOMERCAL` | A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y' |
| `#TEMPTABLE_SMACLASS` | B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | A.FLGSMA = 'Y'; INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID |
| `#TEMPTABLE_SMACLASSUcif` | A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER CUSTOMERCAL ON A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y' |
| `##AccountCal` | A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER CUSTOMERCAL ON A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y' |
| `##CUSTOMERCAL` | A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER CUSTOMERCAL ON A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y' |
| `PRO.SMA_MOVEMENT_HISTORY` | 1 | TIMEKEY=@TIMEKEY) BEGIN |
| `#SMACLASS` | A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1; INNER CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' |
| `##AccountCal` | A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1; INNER CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' |
| `##CUSTOMERCAL` | A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1; INNER CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' |
| `PRO.PREVSMASTATUS` | @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS | NOT B.SMA_CLASS IS NULL AND COALESCE(A.SMA_CLASS, '') <> COALESCE(B.SMA_CLASS, ''); OUTER SMACLASS ON A.CustomerAcID = B.CustomerAcID |
| `#SMACLASS` | @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS | NOT B.SMA_CLASS IS NULL AND COALESCE(A.SMA_CLASS, '') <> COALESCE(B.SMA_CLASS, ''); OUTER SMACLASS ON A.CustomerAcID = B.CustomerAcID |
| `#SMACLASS` | @TIMEKEY, CustomerAcID, SMA_CLASS | None |
| `##AccountCal` | A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1   
                             WHEN SMA_CLASS='SMA_1' THEN  2  
        WHEN SMA_CLASS='SMA_2' THEN  3 ELSE 0 END ) MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt  
                                 
INTO #TEMPTABLE_SMACLASS | None |
| `##AccountCal` | A.UCIF_ID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1   
                          WHEN SMA_CLASS='SMA_1' THEN  2  
                          WHEN SMA_CLASS='SMA_2' THEN  3 ELSE 0 END ) MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt  
                                 
INTO #TEMPTABLE_SMACLASSUcif | None |
| `##AccountCal` | A.CustomerAcID, ISNULL(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2'))  SMA_CLASS INTO #SMACLASS | B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1 |
| `PRO.PREVSMASTATUS` | @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS | B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') |
| `#SMACLASS` | @TIMEKEY, CustomerAcID, SMA_CLASS | None |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | 1 | [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO |
| `##AccountCal` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey, SMA_CLASS AS MovementFromStatus, SMA_CLASS AS MovementToStatus, COALESCE(Balance, 0) AS TotOsAcc, @ProcessDate AS MovementFromDate, '2086-11-21' AS MovementToDate | None |
| `#ACCOUNT_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsAcc, 0) AS TotOsAcc, A.MovementFromDate, A.MovementToDate | (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN NOT B.CustomerAcID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1; LEFT JOIN PRO.ACCOUNT_MOVEMENT_HISTORY ON A.CustomerAcID = B.CustomerAcID AND B.EFFECTIVETOTimekey = 49999 |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsAcc, 0) AS TotOsAcc, A.MovementFromDate, A.MovementToDate | (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN NOT B.CustomerAcID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1; LEFT JOIN PRO.ACCOUNT_MOVEMENT_HISTORY ON A.CustomerAcID = B.CustomerAcID AND B.EFFECTIVETOTimekey = 49999 |
| `#ACCOUNT_MOVEMENT_HISTORY` | AA.EffectiveToTimeKey, B.CustomerAcID, AA.CustomerAcID, B.EffectiveToTimeKey | AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL; LEFT JOIN ACCOUNT_MOVEMENT_HISTORY ON AA.CustomerAcID = B.CustomerAcID AND B.EffectiveToTimeKey = 49999 |
| `##AccountCal` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS  EffectiveToTimeKey, SMA_CLASS AS MovementFromStatus, SMA_CLASS AS MovementToStatus, ISNULL(Balance, 0) as TotOsAcc, @ProcessDate MovementFromDate, '2086-11-21' MovementToDate | None |
| `#ACCOUNT_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, ISNULL(A.TotOsAcc, 0) AS TotOsAcc, A.MovementFromDate, A.MovementToDate | (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN B.CustomerAcID IS NOT NULL AND A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 |
| `#ACCOUNT_MOVEMENT_HISTORY` | 1 | AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS ) |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | 1 | [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO |
| `##CUSTOMERCAL` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey, CustMoveDescription AS MovementFromStatus, CustMoveDescription AS MovementToStatus, COALESCE(TotOsCust, 0) AS TotOsCust, @ProcessDate AS MovementFromDate, '2086-11-21' AS MovementToDate | None |
| `#Customer_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsCust, 0) AS TotOsCust, A.MovementFromDate, A.MovementToDate | (CASE WHEN B.SourceSystemCustomerID IS NULL THEN 1 WHEN NOT B.SourceSystemCustomerID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1; LEFT JOIN PRO.CUSTOMER_MOVEMENT_HISTORY ON A.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EFFECTIVETOTimekey = 49999 |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsCust, 0) AS TotOsCust, A.MovementFromDate, A.MovementToDate | (CASE WHEN B.SourceSystemCustomerID IS NULL THEN 1 WHEN NOT B.SourceSystemCustomerID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1; LEFT JOIN PRO.CUSTOMER_MOVEMENT_HISTORY ON A.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EFFECTIVETOTimekey = 49999 |
| `#Customer_MOVEMENT_HISTORY` | AA.EffectiveToTimeKey, B.SourceSystemCustomerID, AA.SourceSystemCustomerID, B.EffectiveToTimeKey | AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL; LEFT JOIN Customer_MOVEMENT_HISTORY ON AA.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EffectiveToTimeKey = 49999 |
| `##CUSTOMERCAL` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, 49999 AS  EffectiveToTimeKey, CustMoveDescription AS MovementFromStatus, CustMoveDescription AS MovementToStatus, ISNULL(TotOsCust, 0) AS TotOsCust, @ProcessDate MovementFromDate, '2086-11-21' MovementToDate | None |
| `#Customer_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, ISNULL(A.TotOsCust, 0) AS TotOsCust, A.MovementFromDate, A.MovementToDate | (CASE WHEN B.SourceSystemCustomerID IS NULL THEN 1 WHEN B.SourceSystemCustomerID IS NOT NULL AND A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 |
| `#Customer_MOVEMENT_HISTORY` | 1 | AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS ) |
| `#DPD_Aqua_SMA` | B.ContiExcessDt, B.DPD_Overdrawn, B.ReviewDueDt, B.DPD_Renewal, A.AccountEntityID, B.AccountEntityID | INNER DPD_Aqua_SMA ON A.AccountEntityID = B.AccountEntityID |

## Tables Written

| Table Name | Operation Type | Columns Affected | Business Trigger |
|---|---|---|---|
| `##ACCOUNTCAL` | `UPDATE` | A.ContiExcessDt, A.DPD_Overdrawn | COALESCE(A.DPD_Overdrawn, 0) <= 30; INNER DPD_Aqua_SMA ON A.AccountEntityID = B.AccountEntityID |
| `##ACCOUNTCAL` | `UPDATE` | A.ReviewDueDt, A.DPD_Renewal | None |
| `#DPD` | `UPDATE` | DPD_IntService | COALESCE(DPD_IntService, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_NoCredit | COALESCE(DPD_NoCredit, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_Overdrawn | COALESCE(DPD_Overdrawn, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_Overdue | COALESCE(DPD_Overdue, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_Renewal | COALESCE(DPD_Renewal, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_StockStmt | isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE |
| `##ACCOUNTCAL` | `UPDATE` | A.ContiExcessDt, A.DPD_Overdrawn | ISNULL(A.DPD_Overdrawn,0)<= 30 |
| `#DPD` | `UPDATE` | DPD_IntService | isnull(DPD_IntService,0)<0 |
| `#DPD` | `UPDATE` | DPD_NoCredit | isnull(DPD_NoCredit,0)<0 |
| `#DPD` | `UPDATE` | DPD_Overdrawn | isnull(DPD_Overdrawn,0)<0 |
| `#DPD` | `UPDATE` | DPD_Overdue | isnull(DPD_Overdue,0)<0 |
| `#DPD` | `UPDATE` | DPD_Renewal | isnull(DPD_Renewal,0)<0 |
| `#DPD` | `UPDATE` | A.DPD_Max | None |
| `#DPD` | `UPDATE` | A.DPD_Max | COALESCE(A.DPD_Overdrawn, 0) > 0 OR COALESCE(A.DPD_Overdue, 0) > 0 |
| `##AccountCal` | `UPDATE` | A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | None |
| `#DPD` | `UPDATE` | A.DPD_Max | None |
| `#DPD` | `UPDATE` | A.DPD_Max | isnull(A.DPD_Overdrawn,0)>0 OR Isnull(A.DPD_Overdue,0)>0 |
| `##AccountCal` | `UPDATE` | A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | None |
| `##AccountCal` | `UPDATE` | A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0; INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId |
| `##AccountCal` | `UPDATE` | A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0 OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 |
| `##CUSTOMERCAL` | `UPDATE` | A.FLGSMA, A.SMA_CLASS_KEY, A.SMA_DT | None |
| `##CUSTOMERCAL` | `UPDATE` | A.FLGSMA | B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS |
| `##CUSTOMERCAL` | `UPDATE` | A.SMA_CLASS_KEY, A.SMA_DT | A.FLGSMA = 'Y'; INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID |
| `##CUSTOMERCAL` | `UPDATE` | A.FLGSMA | B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif |
| `##CUSTOMERCAL` | `UPDATE` | A.SMA_CLASS_KEY, A.SMA_DT | A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN |
| `PRO.SMA_MOVEMENT_HISTORY` | `DELETE` | Not identified | TIMEKEY=@TIMEKEY |
| `#SMACLASS` | `UPDATE` | SMA_CLASS | None |
| `PRO.SMA_MOVEMENT_HISTORY` | `INSERT` | TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS | None |
| `PRO.PREVSMASTATUS` | `TRUNCATE` | Not identified | None |
| `PRO.PREVSMASTATUS` | `INSERT` | Not identified | None |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 1 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 2 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 3 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 4 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 5 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 6 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY = 1 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY = 2 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY = 3 |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 3 AND SMA_CLASS IS NULL |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL |
| `##CUSTOMERCAL` | `UPDATE` | A.FLGSMA, A.SMA_CLASS_KEY, A.SMA_DT | None |
| `##CUSTOMERCAL` | `UPDATE` | A.SMA_CLASS_KEY, A.SMA_DT | A.FLGSMA='Y' |
| `#SMACLASS` | `UPDATE` | SMA_CLASS | None |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=1 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=2 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=3 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=4 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=5 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=6 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY=1 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY=2 |
| `##CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY=3 |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL |
| `##AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA' |
| `#ACCOUNT_MOVEMENT_HISTORY` | `INSERT` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | None |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | `INSERT` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | None |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL; LEFT JOIN ACCOUNT_MOVEMENT_HISTORY ON AA.CustomerAcID = B.CustomerAcID AND B.EffectiveToTimeKey = 49999 |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS ) |
| `#Customer_MOVEMENT_HISTORY` | `INSERT` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, totOsCust, MovementFromDate, MovementToDate | None |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | `INSERT` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | None |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL; LEFT JOIN Customer_MOVEMENT_HISTORY ON AA.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EffectiveToTimeKey = 49999 |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.SourceSystemCustomerID is null |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS ) |
| `##ACCOUNTCAL` | `UPDATE` | A.ContiExcessDt, A.DPD_Overdrawn, A.ReviewDueDt, A.DPD_Renewal | INNER DPD_Aqua_SMA ON A.AccountEntityID = B.AccountEntityID |
| `PRO.ACLRUNNINGPROCESSSTATUS` | `UPDATE` | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME='SMA_MARKING' |
| `##ACCOUNTCAL` | `UPDATE` | A.ContiExcessDt, A.DPD_Overdrawn, A.ReviewDueDt, A.DPD_Renewal | None |
| `PRO.ACLRUNNINGPROCESSSTATUS` | `UPDATE` | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME='SMA_MARKING' |

## Step-by-Step Logic Flow

1. Retrieve the process date and effective date parameters for the current run.
2. Identify accounts under specific schemes (such as Aqua Scheme with ODA type and CC/OD facility) that meet eligibility criteria for SMA evaluation.
3. For eligible accounts, reset continuous excess and overdue days to zero if the overdrawn days are within the allowed threshold.
4. For accounts exceeding overdue or overdrawn thresholds, calculate Days Past Due (DPD) metrics for various criteria (interest not serviced, no credit, overdrawn, overdue, renewal, stock statement).
5. Ensure that all DPD metrics are non-negative by resetting any negative values to zero.
6. Determine the maximum DPD value across all DPD metrics for each account.
7. Assign the SMA classification (SMA_0, SMA_1, SMA_2) to each account based on the maximum DPD value.
8. Record the specific reason for SMA degradation (e.g., interest not serviced, no credit, overdue, continuous excess, stock statement, review due date, or other) based on which DPD metric triggered the maximum.
9. Set the SMA effective date based on the process date and DPD value.
10. Mark accounts as having an active SMA flag where applicable.
11. Aggregate SMA status at the customer and UCIF (unique customer identifier) levels, updating summary fields and movement descriptions.
12. Update or insert records in movement history tables for both accounts and customers, tracking changes in SMA status over time.
13. Update status and error tracking tables to reflect process completion or errors.

# Business Conditions Report — SMA_MARKING

> **What this process does:** This procedure determines and updates the Special Mention Account (SMA) classification for loan and advance accounts, based on overdue and non-servicing criteria, in line with regulatory and internal policy requirements. It ensures that accounts are correctly marked for SMA status, records the reasons for degradation, and maintains historical movement for both account and customer levels. The process also updates related status and description fields to support downstream reporting and compliance monitoring.

## Glossary

| Term | Business Meaning |
|---|---|
| @TIMEKEY | Declared as IN INT. `TIMEKEY = @TIMEKEY`; `C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(C.SchemeType, '') = 'ODA' AND COALESCE(c.FacilityType,…` |
| TIMEKEY | Source field read in active SQL on SYSDAYMATRIX, PRO.SMA_MOVEMENT_HISTORY, ##CUSTOMERCAL. Referenced in active predicate(s): `TIMEKEY=@TIMEKEY) BEGIN`; `A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN` |
| DATE | Source field read in active SQL on SYSDAYMATRIX, ##AccountCal. Source field read in active SQL from SYSDAYMATRIX, ##AccountCal. |
| EXT_FLG | Referenced in active predicate(s): `EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA` |
| Y | Source field read in active SQL on dbo.Automate_Advances, #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal, ##CUSTOMERCAL, #TEMPTABLE_SMACLASS, #TEMPTABLE_SMACLASSUcif, #SMACLASS, PRO.ACLRUNNINGPROCESSSTATUS. Referenced in active predicate(s): `EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA`; `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…` |
| IF | Source field read in active SQL on dbo.Automate_Advances, ##ACCOUNTCAL, #DPD, ##CUSTOMERCAL, ##AccountCal. Referenced in active predicate(s): `EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA`; `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE` |
| OBJECT_ID | Source field read in active SQL on dbo.Automate_Advances, ##ACCOUNTCAL, #DPD, ##CUSTOMERCAL. Referenced in active predicate(s): `EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA`; `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE` |
| TEMPDB..#DPD_AQUA_SMA | Referenced in active predicate(s): `EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA` |
| DROP | Source field read in active SQL on dbo.Automate_Advances, ##ACCOUNTCAL, #DPD, ##CUSTOMERCAL. Referenced in active predicate(s): `EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA`; `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE` |
| TABLE | Source field read in active SQL on dbo.Automate_Advances, ##ACCOUNTCAL, #DPD, ##CUSTOMERCAL. Referenced in active predicate(s): `EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA`; `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE` |
| 1 | Literal used in active SQL: `1`. Observed in active predicate(s): `Literal value used in active statement `Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y') --------------START---------…`; `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(…` |
| 'Y' | Literal used in active SQL: `'Y'`. Observed in active predicate(s): `Flag literal used in active read on dbo.Automate_Advances for Timekey-1.`; `Flag literal used in active read on #DPD_Aqua_SMA for A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt.` |
| 'TEMPDB..#DPD_Aqua_SMA' | Literal used in active SQL: `'TEMPDB..#DPD_Aqua_SMA'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA`.` |
| C.EFFECTIVEFROMTIMEKEY | Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD, PRO.ACCOUNT_MOVEMENT_HISTORY, #ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY. Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD, PRO.ACCOUNT_MOVEMENT_HISTORY, #ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY. Also referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…`; `A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY)` Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…`; `A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY)` |
| C.EFFECTIVETOTIMEKEY | Target field updated in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY from `49999`. Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…`; `A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY)` Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…`; `A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY)` |
| C.AQUA_SCHEME | Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…` |
| N | Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD, PRO.ACLRUNNINGPROCESSSTATUS. Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…`; `ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0 OR isnull(dpd.D…` |
| C.SCHEMETYPE | Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…` |
| ODA | Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…` |
| C.FACILITYTYPE | Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal. Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…` |
| CC | Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal. Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…` |
| OD | Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal. Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…` |
| A.REFPERIODOVERDRAWN | Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal, #TEMPTABLE. Also referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…` Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…` |
| A.FINALASSETCLASSALT_KEY | Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY. Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY. Also referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…`; `COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0)…` Referenced in active predicate(s): `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD…`; `COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0)…` |
| A.PRODUCTALT_KEY | Referenced in active predicate(s): |
| A.CustomerAcID | Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal, #TEMPTABLE, #SMACLASS, ##CUSTOMERCAL, PRO.SMA_MOVEMENT_HISTORY, PRO.PREVSMASTATUS, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY. Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal, #TEMPTABLE, #SMACLASS, ##CUSTOMERCAL, PRO.SMA_MOVEMENT_HISTORY, PRO.PREVSMASTATUS, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into PRO.SMA_MOVEMENT_HISTORY.`; `A.CustomerAcID = B.CustomerAcID` Referenced in active predicate(s): `Inserted field populated in active INSERT into PRO.SMA_MOVEMENT_HISTORY.`; `A.CustomerAcID = B.CustomerAcID` |
| A.AccountEntityID | Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail. Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail. Also referenced in active predicate(s): `A.AccountEntityID = B.AccountEntityID`; `dpd.AccountEntityId = a.AccountEntityId` Referenced in active predicate(s): `A.AccountEntityID = B.AccountEntityID`; `dpd.AccountEntityId = a.AccountEntityId` |
| A.DPD_Overdrawn | Target field updated in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal, #TEMPTABLE, ##CUSTOMERCAL, AdvAcBasicDetail from `0`. Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal, #TEMPTABLE, ##CUSTOMERCAL, AdvAcBasicDetail. Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal, #TEMPTABLE, ##CUSTOMERCAL, AdvAcBasicDetail. Also referenced in active predicate(s): `COALESCE(A.DPD_Overdrawn, 0) <= 30`; `0` Referenced in active predicate(s): `COALESCE(A.DPD_Overdrawn, 0) <= 30`; `0` |
| ContiExcessDt | Target field updated in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal from `NULL`. Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal. Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal. Also referenced in active predicate(s): `NULL`; `B.ContiExcessDt` |
| DPD_Renewal | Target field updated in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, #TEMPTABLE, ##AccountCal from `0`. Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, #TEMPTABLE, ##AccountCal. Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, #TEMPTABLE, ##AccountCal. Also referenced in active predicate(s): `0`; `isnull(DPD_Renewal,0)<0` Referenced in active predicate(s): `0`; `isnull(DPD_Renewal,0)<0` |
| ReviewDueDt | Target field updated in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal from `NULL`. Source field read in active SQL on #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal. Source field read in active SQL from #DPD_Aqua_SMA, ##ACCOUNTCAL, DIMPRODUCT, #DPD, ##AccountCal. Also referenced in active predicate(s): `NULL`; `B.ReviewDueDt` |
| 91 | Literal used in active SQL: `91`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(…`; `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeTyp…` |
| 'CC' | Literal used in active SQL: `'CC'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(…`; `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeTyp…` |
| 'OD' | Literal used in active SQL: `'OD'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(…`; `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeTyp…` |
| 'ODA' | Literal used in active SQL: `'ODA'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(…`; `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeTyp…` |
| '' | Literal used in active SQL: `''`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(…`; `Threshold or filter literal used in active predicate `C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY AND (ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeTyp…` |
| 'N' | Literal used in active SQL: `'N'`. Observed in active predicate(s): `Flag literal used in active read on #DPD_Aqua_SMA for A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt.`; `Flag literal used in active read on ##ACCOUNTCAL for A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt.` |
| 0 | Literal used in active SQL: `0`. Observed in active predicate(s): `Literal reset value used in active update on ##ACCOUNTCAL for A.ContiExcessDt, A.DPD_Overdrawn.`; `Threshold or filter literal used in active predicate `COALESCE(A.DPD_Overdrawn, 0) <= 30`.` |
| 30 | Literal used in active SQL: `30`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `COALESCE(A.DPD_Overdrawn, 0) <= 30`. Target field updated in active SQL on ##ACCOUNTCAL.`; `Threshold or filter literal used in active predicate `COALESCE(A.DPD_Overdrawn, 0) <= 30`.` |
| A | Source field read in active SQL on ##ACCOUNTCAL, #DPD, ##AccountCal, ##CUSTOMERCAL. |
| INNER | Source field read in active SQL on ##ACCOUNTCAL, ##AccountCal, ##CUSTOMERCAL. |
| JOIN | Source field read in active SQL on ##ACCOUNTCAL, ##AccountCal, ##CUSTOMERCAL, PRO.ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. |
| B | Source field read in active SQL on ##ACCOUNTCAL, ##AccountCal, ##CUSTOMERCAL, PRO.ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. |
| TEMPDB | Source field read in active SQL on ##ACCOUNTCAL, #DPD, ##CUSTOMERCAL. |
| IS | Source field read in active SQL on ##ACCOUNTCAL, #DPD, ##CUSTOMERCAL, ##AccountCal, PRO.ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. |
| 'TEMPDB..#DPD' | Literal used in active SQL: `'TEMPDB..#DPD'`. Observed in active predicate(s): `Literal value used in active statement `Update A SET A.ReviewDueDt=NULL,A.DPD_Renewal=0 FROM ##ACCOUNTCAL A INNER JOIN #DPD_Aqua_SMA B ON A.AccountEntityID=B.AccountEntityID --INN…` |
| A.DPD_OVERDUE | Calculated field updated in active SQL using `CASE` on #DPD, ##AccountCal, #TEMPTABLE, ##CUSTOMERCAL, AdvAcBasicDetail: `(CASE WHEN A.OverDueSinceDt IS NOT NULL THEN DATEDIFF(DAY,A.OverDueSinceDt, '2020-12-31') ELSE 0 END) --`. Source field read in active SQL on #DPD, ##AccountCal, #TEMPTABLE, ##CUSTOMERCAL, AdvAcBasicDetail. Source field read in active SQL from #DPD, ##AccountCal, #TEMPTABLE, ##CUSTOMERCAL, AdvAcBasicDetail. Also referenced in active predicate(s): `COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0`; `0` Referenced in active predicate(s): `COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0`; `0` |
| UcifEntityID | Source field read in active SQL from #DPD, ##AccountCal. |
| CustomerEntityID | Source field read in active SQL on #DPD, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #TEMPTABLE_SMACLASS, #SMACLASS. Source field read in active SQL from #DPD, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #TEMPTABLE_SMACLASS, #SMACLASS. Also referenced in active predicate(s): `A.CustomerEntityID = B.CustomerEntityID`; `A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y'` Referenced in active predicate(s): `A.CustomerEntityID = B.CustomerEntityID`; `A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y'` |
| RefCustomerID | Source field read in active SQL from #DPD, ##AccountCal, #SMACLASS, ##CUSTOMERCAL, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` |
| SourceSystemCustomerID | Source field read in active SQL on #DPD, ##AccountCal, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, ##CUSTOMERCAL, PRO.CUSTOMER_MOVEMENT_HISTORY. Source field read in active SQL from #DPD, ##AccountCal, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, ##CUSTOMERCAL, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` |
| UCIF_ID | Source field read in active SQL on #DPD, ##AccountCal, ##CUSTOMERCAL, #TEMPTABLE_SMACLASSUcif, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Source field read in active SQL from #DPD, ##AccountCal, ##CUSTOMERCAL, #TEMPTABLE_SMACLASSUcif, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y'`; `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.` Referenced in active predicate(s): `A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y'`; `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.` |
| IntNotServicedDt | Source field read in active SQL from #DPD, ##AccountCal. |
| LastCrDate | Source field read in active SQL from #DPD, ##AccountCal. |
| OverDueSinceDt | Source field read in active SQL from #DPD, ##AccountCal. |
| StockStDt | Source field read in active SQL from #DPD, ##AccountCal. |
| RefPeriodIntService | Source field read in active SQL from #DPD, ##AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| RefPeriodNoCredit | Source field read in active SQL from #DPD, ##AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| RefPeriodOverdue | Source field read in active SQL from #DPD, ##AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| RefPeriodReview | Source field read in active SQL from #DPD, ##AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| RefPeriodStkStatement | Source field read in active SQL from #DPD, ##AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| DPD_INTSERVICE | Target field updated in active SQL on #DPD, #TEMPTABLE, ##AccountCal from `0`. Source field read in active SQL on #DPD, #TEMPTABLE, ##AccountCal. Referenced in active predicate(s): `0`; `isnull(DPD_IntService,0)<0` |
| DPD_NOCREDIT | Target field updated in active SQL on #DPD, #TEMPTABLE, ##AccountCal from `0`. Source field read in active SQL on #DPD, #TEMPTABLE, ##AccountCal. Referenced in active predicate(s): `0`; `isnull(DPD_NoCredit,0)<0` |
| DPD_STOCKSTMT | Target field updated in active SQL on #DPD, #TEMPTABLE, ##AccountCal from `0`. Source field read in active SQL on #DPD, #TEMPTABLE, ##AccountCal. Referenced in active predicate(s): `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE`; `0` |
| TEMPDB..#TEMPTABLE | Referenced in active predicate(s): `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE` |
| isnull | Source field read in active SQL on #DPD, ##ACCOUNTCAL, ##AccountCal, PRO.ACLRUNNINGPROCESSSTATUS. |
| 'TEMPDB..#TEMPTABLE' | Literal used in active SQL: `'TEMPDB..#TEMPTABLE'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE`. Target field updated in acti…` |
| A.DPD_Max | Target field updated in active SQL on #DPD, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail from `0`. Source field read in active SQL on #DPD, ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail. Referenced in active predicate(s): `0`; `(CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0)…` |
| A.SMA_CLASS | Calculated field updated in active SQL using `CASE` on ##AccountCal, #SMACLASS, PRO.PREVSMASTATUS: `NULL`. Source field read in active SQL from ##AccountCal, #SMACLASS, PRO.PREVSMASTATUS. Also referenced in active predicate(s): `NULL`; `(CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA…` Referenced in active predicate(s): `NULL`; `(CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA…` |
| A.SMA_REASON | Calculated field updated in active SQL using `CASE` on ##AccountCal: `NULL`. |
| A.SMA_DT | Target field updated in active SQL on ##AccountCal, ##CUSTOMERCAL from `NULL`. Source field read in active SQL on ##AccountCal, ##CUSTOMERCAL. |
| A.FLGSMA | Target field updated in active SQL on ##AccountCal, ##CUSTOMERCAL, #TEMPTABLE_SMACLASS, #TEMPTABLE_SMACLASSUcif, #SMACLASS from `NULL`. Source field read in active SQL on ##AccountCal, ##CUSTOMERCAL, #TEMPTABLE_SMACLASS, #TEMPTABLE_SMACLASSUcif, #SMACLASS. Referenced in active predicate(s): `NULL`; `'Y'` |
| B.FLGPROCESSING | Source field read in active SQL on ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD. Referenced in active predicate(s): `COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0)…`; `ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0 OR isnull(dpd.D…` |
| A.BALANCE | Source field read in active SQL on ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD, #SMACLASS. Referenced in active predicate(s): `COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0)…`; `ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0 OR isnull(dpd.D…` |
| A.ASSET_NORM | Source field read in active SQL on ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD. Referenced in active predicate(s): `COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0)…`; `ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0 OR isnull(dpd.D…` |
| ALWYS_STD | Source field read in active SQL on ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, #DPD. Referenced in active predicate(s): `ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0 OR isnull(dpd.D…` |
| 'OTHER' | Literal used in active SQL: `'OTHER'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'SMA_0' | Literal used in active SQL: `'SMA_0'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…`; `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…` |
| 'SMA_1' | Literal used in active SQL: `'SMA_1'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…`; `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…` |
| 'SMA_2' | Literal used in active SQL: `'SMA_2'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…`; `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…` |
| 'DEGRADE BY INT NOT SERVICED' | Literal used in active SQL: `'DEGRADE BY INT NOT SERVICED'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'DEGRADE BY NO CREDIT' | Literal used in active SQL: `'DEGRADE BY NO CREDIT'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'DEGRADE BY OVERDUE' | Literal used in active SQL: `'DEGRADE BY OVERDUE'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'DEGRADE BY CONTI EXCESS' | Literal used in active SQL: `'DEGRADE BY CONTI EXCESS'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'DEGRADE BY STOCK STATEMENT' | Literal used in active SQL: `'DEGRADE BY STOCK STATEMENT'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'DEGRADE BY REVIEW DUE DATE' | Literal used in active SQL: `'DEGRADE BY REVIEW DUE DATE'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 31 | Literal used in active SQL: `31`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 60 | Literal used in active SQL: `60`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 61 | Literal used in active SQL: `61`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 90 | Literal used in active SQL: `90`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'ALWYS_STD' | Literal used in active SQL: `'ALWYS_STD'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_N…`; `Threshold or filter literal used in active predicate `COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_N…` |
| 'TL' | Literal used in active SQL: `'TL'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'DL' | Literal used in active SQL: `'DL'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'BP' | Literal used in active SQL: `'BP'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'BD' | Literal used in active SQL: `'BD'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'PC' | Literal used in active SQL: `'PC'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| BETWEEN | Source field read in active SQL on ##AccountCal. |
| SMA_0 | Source field read in active SQL on ##AccountCal, #SMACLASS, ##CUSTOMERCAL. |
| SMA_1 | Source field read in active SQL on ##AccountCal, #SMACLASS, ##CUSTOMERCAL. |
| SMA_2 | Source field read in active SQL on ##AccountCal, #SMACLASS, ##CUSTOMERCAL. |
| IN | Source field read in active SQL on ##AccountCal. |
| DEGRADE | Source field read in active SQL on ##AccountCal. |
| BY | Source field read in active SQL on ##AccountCal. |
| INT | Source field read in active SQL on ##AccountCal. |
| SERVICED | Source field read in active SQL on ##AccountCal. |
| NO | Source field read in active SQL on ##AccountCal, PRO.ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Referenced in active predicate(s): `[EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO`; `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA'` |
| CREDIT | Source field read in active SQL on ##AccountCal. |
| TL | Source field read in active SQL on ##AccountCal. |
| DL | Source field read in active SQL on ##AccountCal. |
| BP | Source field read in active SQL on ##AccountCal. |
| BD | Source field read in active SQL on ##AccountCal. |
| PC | Source field read in active SQL on ##AccountCal. |
| OVERDUE | Source field read in active SQL on ##AccountCal. |
| CONTI | Source field read in active SQL on ##AccountCal. |
| EXCESS | Source field read in active SQL on ##AccountCal. |
| STOCK | Source field read in active SQL on ##AccountCal. |
| STATEMENT | Source field read in active SQL on ##AccountCal. |
| REVIEW | Source field read in active SQL on ##AccountCal. |
| DUE | Source field read in active SQL on ##AccountCal. |
| OTHER | Source field read in active SQL on ##AccountCal. |
| DATEADD | Source field read in active SQL on ##AccountCal, PRO.ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. |
| DAY | Source field read in active SQL on ##AccountCal. |
| AdvAcBasicDetail | Source field read in active SQL on ##AccountCal. |
| ABD | Source field read in active SQL on ##AccountCal. |
| dpd | Source field read in active SQL on ##AccountCal. |
| A.SMA_CLASS_KEY | Target field updated in active SQL on ##CUSTOMERCAL from `NULL`. Source field read in active SQL on ##CUSTOMERCAL. Referenced in active predicate(s): `NULL`; `B.MAXSMA_CLASS` |
| TEMPDB..#TEMPTABLE_SMACLASS | Referenced in active predicate(s): `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS` |
| 'TEMPDB..#TEMPTABLE_SMACLASS' | Literal used in active SQL: `'TEMPDB..#TEMPTABLE_SMACLASS'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS`. Target field updated in…` |
| 2 | Literal used in active SQL: `2`. Observed in active predicate(s): `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…`; `Literal value used in active statement `SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLA…` |
| 3 | Literal used in active SQL: `3`. Observed in active predicate(s): `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…`; `Literal value used in active statement `SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLA…` |
| B.MAXSMA_CLASS | Source field read in active SQL on ##CUSTOMERCAL. |
| TEMPDB..#TEMPTABLE_SMACLASSUCIF | Referenced in active predicate(s): `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif` |
| 'TEMPDB..#TEMPTABLE_SMACLASSUcif' | Literal used in active SQL: `'TEMPDB..#TEMPTABLE_SMACLASSUcif'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif`. Target field up…` |
| BEGIN | Referenced in active predicate(s): `TIMEKEY=@TIMEKEY) BEGIN`; `A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN` |
| PRO.SMA_MOVEMENT_HISTORY | Source field read in active SQL on ##CUSTOMERCAL, PRO.SMA_MOVEMENT_HISTORY. Referenced in active predicate(s): `A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN` |
| B.SYSASSETCLASSALT_KEY | Source field read in active SQL on #SMACLASS, ##AccountCal, ##CUSTOMERCAL, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Source field read in active SQL from #SMACLASS, ##AccountCal, ##CUSTOMERCAL, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `SYSASSETCLASSALT_KEY = 1`; `SYSASSETCLASSALT_KEY = 2` Referenced in active predicate(s): `SYSASSETCLASSALT_KEY = 1`; `SYSASSETCLASSALT_KEY = 2` |
| PREVSTATUS | Referenced in active predicate(s): `Inserted field populated in active INSERT into PRO.SMA_MOVEMENT_HISTORY.` |
| CURRENTSTATUS | Referenced in active predicate(s): `Inserted field populated in active INSERT into PRO.SMA_MOVEMENT_HISTORY.` |
| CustMoveDescription | Target field updated in active SQL on ##CUSTOMERCAL from `'STD'`. |
| 'STD' | Literal used in active SQL: `'STD'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1`.`; `Literal value used in active statement `UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL`.` |
| 'SUB' | Literal used in active SQL: `'SUB'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2`.`; `Literal value used in active statement `UPDATE ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL`.` |
| 'DB1' | Literal used in active SQL: `'DB1'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3`.`; `Literal value used in active statement `UPDATE ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL`.` |
| 'DB2' | Literal used in active SQL: `'DB2'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4`.`; `Literal value used in active statement `UPDATE ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL`.` |
| 4 | Literal used in active SQL: `4`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `SYSASSETCLASSALT_KEY = 4`. Target field updated in active SQL on ##CUSTOMERCAL.`; `Threshold or filter literal used in active predicate `FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL`. Target field updated in active SQL on ##AccountCal.` |
| 'DB3' | Literal used in active SQL: `'DB3'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5`.`; `Literal value used in active statement `UPDATE ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL`.` |
| 5 | Literal used in active SQL: `5`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `SYSASSETCLASSALT_KEY = 5`. Target field updated in active SQL on ##CUSTOMERCAL.`; `Threshold or filter literal used in active predicate `FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL`. Target field updated in active SQL on ##AccountCal.` |
| 'LOS' | Literal used in active SQL: `'LOS'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6`.`; `Literal value used in active statement `UPDATE ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HIST…` |
| 6 | Literal used in active SQL: `6`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `SYSASSETCLASSALT_KEY = 6`. Target field updated in active SQL on ##CUSTOMERCAL.`; `Threshold or filter literal used in active predicate `SYSASSETCLASSALT_KEY=6`. Target field updated in active SQL on ##CUSTOMERCAL.` |
| STD | Source field read in active SQL on ##CUSTOMERCAL, ##AccountCal. |
| SUB | Source field read in active SQL on ##CUSTOMERCAL, ##AccountCal. |
| DB1 | Source field read in active SQL on ##CUSTOMERCAL, ##AccountCal. |
| DB2 | Source field read in active SQL on ##CUSTOMERCAL, ##AccountCal. |
| DB3 | Source field read in active SQL on ##CUSTOMERCAL, ##AccountCal. |
| LOS | Source field read in active SQL on ##CUSTOMERCAL, ##AccountCal. |
| PRINT | Source field read in active SQL on PRO.ACCOUNT_MOVEMENT_HISTORY, ##AccountCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Referenced in active predicate(s): `[EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO`; `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA'` |
| NEDD | Source field read in active SQL on PRO.ACCOUNT_MOVEMENT_HISTORY, ##AccountCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Referenced in active predicate(s): `[EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO`; `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA'` |
| TO | Source field read in active SQL on PRO.ACCOUNT_MOVEMENT_HISTORY, ##AccountCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Referenced in active predicate(s): `[EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO`; `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA'` |
| 'NO NEDD TO INSERT DATA' | Literal used in active SQL: `'NO NEDD TO INSERT DATA'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HIST…`; `Threshold or filter literal used in active predicate `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTim…` |
| PRO.ACCOUNT_MOVEMENT_HISTORY | Source field read in active SQL on ##AccountCal, PRO.ACCOUNT_MOVEMENT_HISTORY. Referenced in active predicate(s): `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA'` |
| DATA | Source field read in active SQL on ##AccountCal. Referenced in active predicate(s): `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA'` |
| FinalNpaDt | Source field read in active SQL from #ACCOUNT_MOVEMENT_HISTORY, ##AccountCal, PRO.ACCOUNT_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` |
| MovementFromStatus | Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` |
| MovementToStatus | Source field read in active SQL on #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Source field read in active SQL from #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` |
| TotOsAcc | Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` |
| MovementFromDate | Source field read in active SQL from #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` |
| MovementToDate | Target field updated in active SQL on #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY from `DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE`. Source field read in active SQL from #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.ACCOUNT_MOVEMENT_HISTORY.` |
| SMA_CLASS AS MovementFromStatus | Source field read in active SQL from ##AccountCal. |
| SMA_CLASS AS MovementToStatus | Source field read in active SQL from ##AccountCal. |
| @ProcessDate AS MovementFromDate | Declared parameter. Used in active operations: read |
| 49999 | Literal used in active SQL: `49999`. Observed in active predicate(s): `Literal value used in active statement `SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS Eff…`; `Literal value used in active statement `SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey…` |
| '2086-11-21' | Literal used in active SQL: `'2086-11-21'`. Observed in active predicate(s): `Literal value used in active statement `SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS Eff…`; `Literal value used in active statement `SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, 49999 AS Effect…` |
| @ProcessDate MovementFromDate | Declared parameter. Used in active operations: read |
| AA | Source field read in active SQL on PRO.ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. |
| DD | Source field read in active SQL on PRO.ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. |
| LEFT | Source field read in active SQL on PRO.ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. |
| BB | Source field read in active SQL on PRO.ACCOUNT_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Referenced in active predicate(s): `AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToT…`; `AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerI…` |
| CustomerName | Source field read in active SQL from #Customer_MOVEMENT_HISTORY, ##CUSTOMERCAL, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.CUSTOMER_MOVEMENT_HISTORY.` |
| SysNPA_Dt | Source field read in active SQL from #Customer_MOVEMENT_HISTORY, ##CUSTOMERCAL, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.CUSTOMER_MOVEMENT_HISTORY.` |
| totOsCust | Referenced in active predicate(s): `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.CUSTOMER_MOVEMENT_HISTORY.` |
| CustMoveDescription AS MovementFromStatus | Source field read in active SQL from ##CUSTOMERCAL. |
| CustMoveDescription AS MovementToStatus | Source field read in active SQL from ##CUSTOMERCAL. |
| PRO.CUSTOMER_MOVEMENT_HISTORY | Source field read in active SQL on PRO.CUSTOMER_MOVEMENT_HISTORY. |
| RUNNINGPROCESSNAME | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. Referenced in active predicate(s): `RUNNINGPROCESSNAME='SMA_MARKING'` |
| SMA_MARKING | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. Referenced in active predicate(s): `RUNNINGPROCESSNAME='SMA_MARKING'` |
| COMPLETED | Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS from `'Y'`. |
| ERRORDATE | Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS from `NULL`. |
| ERRORDESCRIPTION | Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS from `NULL`. |
| COUNT | Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS from `ISNULL(COUNT,0)+1`. |
| PRO.ACLRUNNINGPROCESSSTATUS | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. |
| 'SMA_MARKING' | Literal used in active SQL: `'SMA_MARKING'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `RUNNINGPROCESSNAME='SMA_MARKING'`. Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS.` |
| GETDATE | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. |
| ERROR_MESSAGE | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. |
| CATCH | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. |
| @ProcessDate | Declared parameter. `Calculated field `@ProcessDate` is defined by `(SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY=@TIMEKEY)`.` |
| @vEffectiveto | Declared parameter. `Calculated field `@vEffectiveto` is defined by `(select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y')`.` |

# Business Rules

## Rule: Reset negative DPD values to zero

**Applies to:** `Not specified`
**Business meaning:** Sets the corresponding DPD metric to zero

### Eligibility
- Any DPD metric (interest not serviced, no credit, overdrawn, overdue, renewal, stock statement) is less than zero

### Decision Logic
| Condition | Outcome |
|---|---|
| Any DPD metric (interest not serviced, no credit, overdrawn, overdue, renewal, stock statement) is less than zero | Sets the corresponding DPD metric to zero |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #1).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Calculate maximum DPD for account [Needs Review]

**Applies to:** `DPD_Max`
**Business meaning:** Sets the maximum DPD value (DPD_Max) to the highest among all DPD metrics for the account

### Eligibility
- Account has any positive DPD metric (overdrawn or overdue)

### Decision Logic
| Condition | Outcome |
|---|---|
| Account has any positive DPD metric (overdrawn or overdue) | Sets the maximum DPD value (DPD_Max) to the highest among all DPD metrics for the account |

### Tie / Priority Handling
- Needs Review

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Assign SMA class from DPD ladder [Needs Review]

**Applies to:** `SMA_CLASS`
**Business meaning:** Assigns the account's SMA classification based on the maximum DPD value

### Eligibility
- Account is eligible for SMA marking and has a positive DPD_Max value

### Decision Logic
| Condition | Outcome |
|---|---|
| DPD_Max between 1 and 30 | SMA_0 |
| DPD_Max between 31 and 60 | SMA_1 |
| DPD_Max between 61 and 90 | SMA_2 |
| DPD_Max greater than 90 | SMA_2 |

### Tie / Priority Handling
- Needs Review

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Set SMA reason for degradation [Needs Review]

**Applies to:** `SMA_REASON`
**Business meaning:** Sets the SMA reason field to indicate the cause of degradation (e.g., interest not serviced, no credit, overdue, continuous excess, stock statement, review due date, or other)

### Eligibility
- Account's SMA classification is being set and a specific DPD metric equals the maximum DPD value

### Decision Logic
| Condition | Outcome |
|---|---|
| Account's SMA classification is being set and a specific DPD metric equals the maximum DPD value | Sets the SMA reason field to indicate the cause of degradation (e.g., interest not serviced, no credit, overdue, continuous excess, stock statement, review due date, or other) |

### Tie / Priority Handling
- Needs Review

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Set SMA effective date

**Applies to:** `SMA_DT`
**Business meaning:** Sets the SMA effective date to the process date minus the maximum DPD value plus one

### Eligibility
- Account's SMA classification is being set

### Decision Logic
| Condition | Outcome |
|---|---|
| Account's SMA classification is being set | Sets the SMA effective date to the process date minus the maximum DPD value plus one |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #5).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Mark account as SMA active

**Applies to:** `FLGSMA`
**Business meaning:** Sets the SMA flag to 'Y' to indicate the account is currently under SMA monitoring

### Eligibility
- Account's SMA classification is being set

### Decision Logic
| Condition | Outcome |
|---|---|
| Account's SMA classification is being set | Sets the SMA flag to 'Y' to indicate the account is currently under SMA monitoring |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #6).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Reset SMA fields when DPD is within threshold

**Applies to:** `ContiExcessDt, DPD_Overdrawn`
**Business meaning:** Resets continuous excess date and DPD_Overdrawn to zero

### Eligibility
- Account is under Aqua Scheme, ODA type, CC/OD facility, and DPD_Overdrawn is less than or equal to 30

### Decision Logic
| Condition | Outcome |
|---|---|
| Account is under Aqua Scheme, ODA type, CC/OD facility, and DPD_Overdrawn is less than or equal to 30 | Resets continuous excess date and DPD_Overdrawn to zero |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #7).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Reset renewal fields for Aqua Scheme

**Applies to:** `ReviewDueDt, DPD_Renewal`
**Business meaning:** Resets review due date and DPD_Renewal to zero

### Eligibility
- Account is under Aqua Scheme, ODA type, CC/OD facility

### Decision Logic
| Condition | Outcome |
|---|---|
| Account is under Aqua Scheme, ODA type, CC/OD facility | Resets review due date and DPD_Renewal to zero |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #8).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Aggregate SMA class at customer level

**Applies to:** `SMA_CLASS_KEY`
**Business meaning:** Sets the customer's SMA class key to the highest SMA class among their accounts and the SMA date to the earliest SMA date among those accounts

### Eligibility
- Customer has one or more accounts with SMA flag set to 'Y'

### Decision Logic
| Condition | Outcome |
|---|---|
| Customer has one or more accounts with SMA flag set to 'Y' | Sets the customer's SMA class key to the highest SMA class among their accounts and the SMA date to the earliest SMA date among those accounts |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #9).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Aggregate SMA class at UCIF level

**Applies to:** `SMA_CLASS_KEY`
**Business meaning:** Sets the UCIF's SMA class key to the highest SMA class among their accounts and the SMA date to the earliest SMA date among those accounts

### Eligibility
- UCIF (unique customer identifier) has one or more accounts with SMA flag set to 'Y'

### Decision Logic
| Condition | Outcome |
|---|---|
| UCIF (unique customer identifier) has one or more accounts with SMA flag set to 'Y' | Sets the UCIF's SMA class key to the highest SMA class among their accounts and the SMA date to the earliest SMA date among those accounts |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #10).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Update movement history for account

**Applies to:** `Not specified`
**Business meaning:** Inserts a new record into the account movement history table with the updated SMA status and relevant dates

### Eligibility
- Account's SMA status has changed compared to previous movement history or is new

### Decision Logic
| Condition | Outcome |
|---|---|
| Account's SMA status has changed compared to previous movement history or is new | Inserts a new record into the account movement history table with the updated SMA status and relevant dates |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #11).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Update movement history for customer

**Applies to:** `Not specified`
**Business meaning:** Inserts a new record into the customer movement history table with the updated movement status and relevant dates

### Eligibility
- Customer's movement status has changed compared to previous movement history or is new

### Decision Logic
| Condition | Outcome |
|---|---|
| Customer's movement status has changed compared to previous movement history or is new | Inserts a new record into the customer movement history table with the updated movement status and relevant dates |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #12).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Set movement description for asset class

**Applies to:** `CustMoveDescription`
**Business meaning:** Sets the movement description field to a corresponding label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS')

### Eligibility
- Customer's system asset class key matches a predefined value

### Decision Logic
| Condition | Outcome |
|---|---|
| Customer's system asset class key matches a predefined value | Sets the movement description field to a corresponding label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #13).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Set movement description for SMA class key

**Applies to:** `CustMoveDescription`
**Business meaning:** Sets the movement description field to the corresponding SMA label ('SMA_0', 'SMA_1', 'SMA_2')

### Eligibility
- Customer's SMA class key matches a predefined value

### Decision Logic
| Condition | Outcome |
|---|---|
| Customer's SMA class key matches a predefined value | Sets the movement description field to the corresponding SMA label ('SMA_0', 'SMA_1', 'SMA_2') |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #14).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Default SMA class for missing values

**Applies to:** `SMA_CLASS`
**Business meaning:** Sets the SMA class to the corresponding default label ('STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS')

### Eligibility
- Account's SMA class is null and the final asset class key matches a predefined value

### Decision Logic
| Condition | Outcome |
|---|---|
| Account's SMA class is null and the final asset class key matches a predefined value | Sets the SMA class to the corresponding default label ('STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #15).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

# Business Rule Summary

| Rule | Output | Business Purpose |
|---|---|---|
| Reset negative DPD values to zero | `Not specified` | Sets the corresponding DPD metric to zero |
| Calculate maximum DPD for account | `DPD_Max` | Sets the maximum DPD value (DPD_Max) to the highest among all DPD metrics for the account |
| Assign SMA class from DPD ladder | `SMA_CLASS` | Assigns the account's SMA classification based on the maximum DPD value |
| Set SMA reason for degradation | `SMA_REASON` | Sets the SMA reason field to indicate the cause of degradation (e.g., interest not serviced, no credit, overdue, continuous excess, stock statement, review due date, or other) |
| Set SMA effective date | `SMA_DT` | Sets the SMA effective date to the process date minus the maximum DPD value plus one |
| Mark account as SMA active | `FLGSMA` | Sets the SMA flag to 'Y' to indicate the account is currently under SMA monitoring |
| Reset SMA fields when DPD is within threshold | `ContiExcessDt, DPD_Overdrawn` | Resets continuous excess date and DPD_Overdrawn to zero |
| Reset renewal fields for Aqua Scheme | `ReviewDueDt, DPD_Renewal` | Resets review due date and DPD_Renewal to zero |
| Aggregate SMA class at customer level | `SMA_CLASS_KEY` | Sets the customer's SMA class key to the highest SMA class among their accounts and the SMA date to the earliest SMA date among those accounts |
| Aggregate SMA class at UCIF level | `SMA_CLASS_KEY` | Sets the UCIF's SMA class key to the highest SMA class among their accounts and the SMA date to the earliest SMA date among those accounts |
| Update movement history for account | `Not specified` | Inserts a new record into the account movement history table with the updated SMA status and relevant dates |
| Update movement history for customer | `Not specified` | Inserts a new record into the customer movement history table with the updated movement status and relevant dates |
| Set movement description for asset class | `CustMoveDescription` | Sets the movement description field to a corresponding label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') |
| Set movement description for SMA class key | `CustMoveDescription` | Sets the movement description field to the corresponding SMA label ('SMA_0', 'SMA_1', 'SMA_2') |
| Default SMA class for missing values | `SMA_CLASS` | Sets the SMA class to the corresponding default label ('STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') |

# Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|
| 1 | Reset negative DPD values to zero | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0; UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0; UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0; UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0; UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0; UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0 | 01_nested_block:nested_block | tables_written[2]: 01_nested_block:chunk_text_08 | `#DPD` | UPDATE | target: DPD_IntService | source: N/A | WHERE: COALESCE(DPD_IntService, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_08 | parse=parsed; tables_written[9]: 01_nested_block:embedded_01_18 | `#DPD` | UPDATE | target: DPD_IntService | source: isnull | WHERE: isnull(DPD_IntService,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_18 | parse=regex_fallback; tables_written[3]: 01_nested_block:chunk_text_09 | `#DPD` | UPDATE | target: DPD_NoCredit | source: N/A | WHERE: COALESCE(DPD_NoCredit, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_09 | parse=parsed; tables_written[10]: 01_nested_block:embedded_01_19 | `#DPD` | UPDATE | target: DPD_NoCredit | source: isnull | WHERE: isnull(DPD_NoCredit,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_19 | parse=regex_fallback; tables_written[4]: 01_nested_block:chunk_text_10 | `#DPD` | UPDATE | target: DPD_Overdrawn | source: N/A | WHERE: COALESCE(DPD_Overdrawn, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_10 | parse=parsed; tables_written[11]: 01_nested_block:embedded_01_20 | `#DPD` | UPDATE | target: DPD_Overdrawn | source: isnull | WHERE: isnull(DPD_Overdrawn,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_20 | parse=regex_fallback; tables_written[5]: 01_nested_block:chunk_text_11 | `#DPD` | UPDATE | target: DPD_Overdue | source: N/A | WHERE: COALESCE(DPD_Overdue, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_11 | parse=parsed; tables_written[12]: 01_nested_block:embedded_01_21 | `#DPD` | UPDATE | target: DPD_Overdue | source: isnull | WHERE: isnull(DPD_Overdue,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_21 | parse=regex_fallback; tables_written[6]: 01_nested_block:chunk_text_12 | `#DPD` | UPDATE | target: DPD_Renewal | source: N/A | WHERE: COALESCE(DPD_Renewal, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_12 | parse=parsed; tables_written[13]: 01_nested_block:embedded_01_22 | `#DPD` | UPDATE | target: DPD_Renewal | source: isnull | WHERE: isnull(DPD_Renewal,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_22 | parse=regex_fallback; tables_written[7]: 01_nested_block:chunk_text_13 | `#DPD` | UPDATE | target: DPD_StockStmt | source: isnull, IF, OBJECT_ID, TEMPDB, IS, DROP, TABLE | WHERE: isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE | JOIN: None | EXISTS: None | HAVING: None | constants: 0, 'TEMPDB..#TEMPTABLE' | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_13 | parse=regex_fallback | Verified |
| 2 | Calculate maximum DPD for account | UPDATE   A SET A.DPD_Max= (CASE ... END) FROM  #DPD a WHERE  isnull(A.DPD_Overdrawn,0)>0   OR  Isnull(A.DPD_Overdue,0)>0 | Not cited | Not cited | Needs Review |
| 3 | Assign SMA class from DPD ladder | UPDATE A SET A.SMA_CLASS=  (CASE  WHEN dpd.DPD_Max  BETWEEN 1 AND 30  THEN 'SMA_0' ... END) | Not cited | Not cited | Needs Review |
| 4 | Set SMA reason for degradation | A.SMA_REASON= (CASE ... END) | Not cited | Not cited | Needs Review |
| 5 | Set SMA effective date | A.SMA_DT=   DATEADD(DAY, -dpd.DPD_MAX+1 ,@ProcessDate) | 01_nested_block_2:nested_block; 01_nested_block_3:nested_block | tables_read[13]: 01_nested_block_2:chunk_text_01 | `##CUSTOMERCAL` | target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | source: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | JOIN: INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId | EXISTS: None | HAVING: None | constants: 'Y', NULL, 'OTHER', 1, 0, 'SMA_0', 'SMA_1', 'SMA_2', 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 30, 31, 60, 61, 90, 'ALWYS_STD', 'CC', 'OD', 'TL', 'DL', 'BP', 'BD', 'PC', 'N' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_01 | parse=parsed; tables_read[14]: 01_nested_block_2:chunk_text_01 | `AdvAcBasicDetail` | target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | source: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | JOIN: INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId | EXISTS: None | HAVING: None | constants: 'Y', NULL, 'OTHER', 1, 0, 'SMA_0', 'SMA_1', 'SMA_2', 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 30, 31, 60, 61, 90, 'ALWYS_STD', 'CC', 'OD', 'TL', 'DL', 'BP', 'BD', 'PC', 'N' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_01 | parse=parsed; tables_read[15]: 01_nested_block_2:chunk_text_01 | `#DPD` | target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | source: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | JOIN: INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId | EXISTS: None | HAVING: None | constants: 'Y', NULL, 'OTHER', 1, 0, 'SMA_0', 'SMA_1', 'SMA_2', 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 30, 31, 60, 61, 90, 'ALWYS_STD', 'CC', 'OD', 'TL', 'DL', 'BP', 'BD', 'PC', 'N' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_01 | parse=parsed; tables_written[20]: 01_nested_block_2:chunk_text_01 | `##AccountCal` | UPDATE | target: A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | source: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | JOIN: INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId | EXISTS: None | HAVING: None | constants: 'Y', NULL, 'OTHER', 1, 0, 'SMA_0', 'SMA_1', 'SMA_2', 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 30, 31, 60, 61, 90, 'ALWYS_STD', 'CC', 'OD', 'TL', 'DL', 'BP', 'BD', 'PC', 'N' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_01 | parse=parsed; tables_written[21]: 01_nested_block_2:embedded_01_02 | `##AccountCal` | UPDATE | target: A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | source: A, dpd.DPD_Max, BETWEEN, SMA_0, SMA_1, SMA_2, A.FACILITYTYPE, IN, CC, OD, ISNULL, DPD.DPD_INTSERVICE, dpd.DPD_MAX, DEGRADE, BY, INT, SERVICED, DPD.DPD_NOCREDIT, NO, CREDIT, TL, DL, BP, BD, PC, dpd.DPD_OVERDUE, OVERDUE, dpd.DPD_OVERDRAWN, CONTI, EXCESS, DPD.DPD_STOCKSTMT, STOCK, STATEMENT, DPD.DPD_RENEWAL, REVIEW, DUE, DATE, OTHER, DATEADD, DAY, Y, INNER, JOIN, B, A.CustomerEntityID, B.CustomerEntityID, AdvAcBasicDetail, ABD, A.AccountEntityID, ABD.AccountEntityId, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, dpd, dpd.AccountEntityId, a.AccountEntityId, B.FLGPROCESSING, N, FINALASSETCLASSALT_KEY, A.BALANCE, A.ASSET_NORM, ALWYS_STD, isnull, dpd.DPD_Overdrawn, dpd.DPD_Overdue, DPD.DPD_MAX | WHERE: ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0 OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 | JOIN: None | EXISTS: None | HAVING: None | constants: 1, 30, 'SMA_0', 31, 60, 'SMA_1', 61, 90, 'SMA_2', 'CC', 'OD', 0, 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'TL', 'DL', 'BP', 'BD', 'PC', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 'OTHER', 'Y', 'N', 'ALWYS_STD' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:embedded_01_02 | parse=regex_fallback; calculations[11]: metric not specified | explanation not specified; calculations[12]: metric not specified | explanation not specified | Verified |
| 6 | Mark account as SMA active | A.FLGSMA='Y' | 01_nested_block_2:nested_block; 01_nested_block_4:nested_block | tables_read[13]: 01_nested_block_2:chunk_text_01 | `##CUSTOMERCAL` | target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | source: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | JOIN: INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId | EXISTS: None | HAVING: None | constants: 'Y', NULL, 'OTHER', 1, 0, 'SMA_0', 'SMA_1', 'SMA_2', 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 30, 31, 60, 61, 90, 'ALWYS_STD', 'CC', 'OD', 'TL', 'DL', 'BP', 'BD', 'PC', 'N' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_01 | parse=parsed; tables_read[14]: 01_nested_block_2:chunk_text_01 | `AdvAcBasicDetail` | target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | source: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | JOIN: INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId | EXISTS: None | HAVING: None | constants: 'Y', NULL, 'OTHER', 1, 0, 'SMA_0', 'SMA_1', 'SMA_2', 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 30, 31, 60, 61, 90, 'ALWYS_STD', 'CC', 'OD', 'TL', 'DL', 'BP', 'BD', 'PC', 'N' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_01 | parse=parsed; tables_read[15]: 01_nested_block_2:chunk_text_01 | `#DPD` | target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | source: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | JOIN: INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId | EXISTS: None | HAVING: None | constants: 'Y', NULL, 'OTHER', 1, 0, 'SMA_0', 'SMA_1', 'SMA_2', 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 30, 31, 60, 61, 90, 'ALWYS_STD', 'CC', 'OD', 'TL', 'DL', 'BP', 'BD', 'PC', 'N' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_01 | parse=parsed; tables_read[19]: 01_nested_block_4:chunk_text_04 | `#TEMPTABLE_SMACLASS` | target: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | source: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | WHERE: A.FLGSMA = 'Y' | JOIN: INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_04 | parse=parsed; tables_read[23]: 01_nested_block_4:chunk_text_07 | `PRO.SMA_MOVEMENT_HISTORY` | target: 1 | source: 1 | WHERE: TIMEKEY=@TIMEKEY) BEGIN | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_07 | parse=regex_fallback; tables_read[24]: 01_nested_block_4:chunk_text_10 | `#SMACLASS` | target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | source: A.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS_KEY, A.FLGSMA, A.REFCUSTOMERID, B.REFCUSTOMERID, A.CUSTOMERENTITYID, B.CUSTOMERENTITYID, B.FLGSMA, B.SYSASSETCLASSALT_KEY, A.BALANCE | WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1 | JOIN: INNER CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' | EXISTS: None | HAVING: None | constants: 'SMA_0', 'SMA_1', 'SMA_2', 'Y', 1, 0 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_10 | parse=parsed; tables_read[25]: 01_nested_block_4:chunk_text_10 | `##AccountCal` | target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | source: A.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS_KEY, A.FLGSMA, A.REFCUSTOMERID, B.REFCUSTOMERID, A.CUSTOMERENTITYID, B.CUSTOMERENTITYID, B.FLGSMA, B.SYSASSETCLASSALT_KEY, A.BALANCE | WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1 | JOIN: INNER CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' | EXISTS: None | HAVING: None | constants: 'SMA_0', 'SMA_1', 'SMA_2', 'Y', 1, 0 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_10 | parse=parsed; tables_read[26]: 01_nested_block_4:chunk_text_10 | `##CUSTOMERCAL` | target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | source: A.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS_KEY, A.FLGSMA, A.REFCUSTOMERID, B.REFCUSTOMERID, A.CUSTOMERENTITYID, B.CUSTOMERENTITYID, B.FLGSMA, B.SYSASSETCLASSALT_KEY, A.BALANCE | WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1 | JOIN: INNER CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' | EXISTS: None | HAVING: None | constants: 'SMA_0', 'SMA_1', 'SMA_2', 'Y', 1, 0 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_10 | parse=parsed; tables_read[32]: 01_nested_block_4:embedded_01_40 | `##AccountCal` | target: A.CustomerAcID, ISNULL(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2'))  SMA_CLASS INTO #SMACLASS | source: A.CustomerAcID, ISNULL(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2'))  SMA_CLASS INTO #SMACLASS | WHERE: B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_0', 'SMA_1', 'SMA_2', 'Y', 0, 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_40 | parse=regex_fallback; tables_written[20]: 01_nested_block_2:chunk_text_01 | `##AccountCal` | UPDATE | target: A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | source: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN, DPD.DPD_STOCKSTMT, DPD.DPD_RENEWAL, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, A.BALANCE, dpd.DPD_Overdrawn, dpd.DPD_Overdue, B.FLGPROCESSING, FINALASSETCLASSALT_KEY | WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | JOIN: INNER CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID; INNER AdvAcBasicDetail ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY); INNER DPD ON dpd.AccountEntityId = a.AccountEntityId | EXISTS: None | HAVING: None | constants: 'Y', NULL, 'OTHER', 1, 0, 'SMA_0', 'SMA_1', 'SMA_2', 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 30, 31, 60, 61, 90, 'ALWYS_STD', 'CC', 'OD', 'TL', 'DL', 'BP', 'BD', 'PC', 'N' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_01 | parse=parsed; tables_written[21]: 01_nested_block_2:embedded_01_02 | `##AccountCal` | UPDATE | target: A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | source: A, dpd.DPD_Max, BETWEEN, SMA_0, SMA_1, SMA_2, A.FACILITYTYPE, IN, CC, OD, ISNULL, DPD.DPD_INTSERVICE, dpd.DPD_MAX, DEGRADE, BY, INT, SERVICED, DPD.DPD_NOCREDIT, NO, CREDIT, TL, DL, BP, BD, PC, dpd.DPD_OVERDUE, OVERDUE, dpd.DPD_OVERDRAWN, CONTI, EXCESS, DPD.DPD_STOCKSTMT, STOCK, STATEMENT, DPD.DPD_RENEWAL, REVIEW, DUE, DATE, OTHER, DATEADD, DAY, Y, INNER, JOIN, B, A.CustomerEntityID, B.CustomerEntityID, AdvAcBasicDetail, ABD, A.AccountEntityID, ABD.AccountEntityId, ABD.EffectiveFromTimeKey, ABD.EffectiveToTimeKey, dpd, dpd.AccountEntityId, a.AccountEntityId, B.FLGPROCESSING, N, FINALASSETCLASSALT_KEY, A.BALANCE, A.ASSET_NORM, ALWYS_STD, isnull, dpd.DPD_Overdrawn, dpd.DPD_Overdue, DPD.DPD_MAX | WHERE: ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0 OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 | JOIN: None | EXISTS: None | HAVING: None | constants: 1, 30, 'SMA_0', 31, 60, 'SMA_1', 61, 90, 'SMA_2', 'CC', 'OD', 0, 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'TL', 'DL', 'BP', 'BD', 'PC', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', 'DEGRADE BY REVIEW DUE DATE', 'OTHER', 'Y', 'N', 'ALWYS_STD' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:embedded_01_02 | parse=regex_fallback; tables_written[23]: 01_nested_block_4:chunk_text_02 | `##CUSTOMERCAL` | UPDATE | target: A.FLGSMA | source: A, Y, INNER, JOIN, B, A.CustomerEntityID, B.CustomerEntityID, B.FLGSMA, IF, OBJECT_ID, TEMPDB, IS, DROP, TABLE | WHERE: B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 'TEMPDB..#TEMPTABLE_SMACLASS' | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_02 | parse=regex_fallback; tables_written[24]: 01_nested_block_4:chunk_text_04 | `##CUSTOMERCAL` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | WHERE: A.FLGSMA = 'Y' | JOIN: INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_04 | parse=parsed; tables_written[25]: 01_nested_block_4:chunk_text_05 | `##CUSTOMERCAL` | UPDATE | target: A.FLGSMA | source: A, Y, INNER, JOIN, B, A.UCIF_ID, B.UCIF_ID, B.FLGSMA, IF, OBJECT_ID, TEMPDB, IS, DROP, TABLE | WHERE: B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 'TEMPDB..#TEMPTABLE_SMACLASSUcif' | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_05 | parse=regex_fallback; tables_written[26]: 01_nested_block_4:chunk_text_07 | `##CUSTOMERCAL` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: A, B.MAXSMA_CLASS, B.SMA_Dt, INNER, JOIN, B, A.UCIF_ID, B.UCIF_ID, A.FLGSMA, Y, IF, PRO.SMA_MOVEMENT_HISTORY, TIMEKEY | WHERE: A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_07 | parse=regex_fallback; tables_written[47]: 01_nested_block_4:embedded_01_34 | `##CUSTOMERCAL` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: A, B.MAXSMA_CLASS, B.SMA_Dt, INNER, JOIN, B, A.CustomerEntityID, B.CustomerEntityID, A.FLGSMA, Y | WHERE: A.FLGSMA='Y' | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_34 | parse=regex_fallback | Verified |
| 7 | Reset SMA fields when DPD is within threshold | Update         A SET            A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM           ##ACCOUNTCAL A INNER JOIN     #DPD_Aqua_SMA B ON             A.AccountEntityID=B.AccountEntityID WHERE          ISNULL(A.DPD_Overdrawn,0)<= 30 | 01_nested_block:nested_block | tables_read[5]: 01_nested_block:chunk_text_05 | `#DPD_Aqua_SMA` | target: A.AccountEntityID, B.AccountEntityID | source: A.AccountEntityID, B.AccountEntityID | WHERE: COALESCE(A.DPD_Overdrawn, 0) <= 30 | JOIN: INNER DPD_Aqua_SMA ON A.AccountEntityID = B.AccountEntityID | EXISTS: None | HAVING: None | constants: NULL, 0, 30 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_05 | parse=parsed; tables_written[0]: 01_nested_block:chunk_text_05 | `##ACCOUNTCAL` | UPDATE | target: A.ContiExcessDt, A.DPD_Overdrawn | source: A.AccountEntityID, B.AccountEntityID | WHERE: COALESCE(A.DPD_Overdrawn, 0) <= 30 | JOIN: INNER DPD_Aqua_SMA ON A.AccountEntityID = B.AccountEntityID | EXISTS: None | HAVING: None | constants: NULL, 0, 30 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_05 | parse=parsed; tables_written[8]: 01_nested_block:embedded_01_15 | `##ACCOUNTCAL` | UPDATE | target: A.ContiExcessDt, A.DPD_Overdrawn | source: A, INNER, JOIN, B, A.AccountEntityID, B.AccountEntityID, ISNULL | WHERE: ISNULL(A.DPD_Overdrawn,0)<= 30 | JOIN: None | EXISTS: None | HAVING: None | constants: 0, 30 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_15 | parse=regex_fallback | Verified |
| 8 | Reset renewal fields for Aqua Scheme | Update         A SET            A.ReviewDueDt=NULL,A.DPD_Renewal=0 FROM           ##ACCOUNTCAL A INNER JOIN     #DPD_Aqua_SMA B ON             A.AccountEntityID=B.AccountEntityID | 01_nested_block:nested_block | tables_written[1]: 01_nested_block:chunk_text_06 | `##ACCOUNTCAL` | UPDATE | target: A.ReviewDueDt, A.DPD_Renewal | source: A, INNER, JOIN, B, A.AccountEntityID, B.AccountEntityID, IF, OBJECT_ID, TEMPDB, IS, DROP, TABLE | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: 0, 'TEMPDB..#DPD' | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_06 | parse=regex_fallback | Verified |
| 9 | Aggregate SMA class at customer level | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' | 01_nested_block_4:nested_block | tables_read[19]: 01_nested_block_4:chunk_text_04 | `#TEMPTABLE_SMACLASS` | target: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | source: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | WHERE: A.FLGSMA = 'Y' | JOIN: INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_04 | parse=parsed; tables_written[24]: 01_nested_block_4:chunk_text_04 | `##CUSTOMERCAL` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | WHERE: A.FLGSMA = 'Y' | JOIN: INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_04 | parse=parsed; tables_written[47]: 01_nested_block_4:embedded_01_34 | `##CUSTOMERCAL` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: A, B.MAXSMA_CLASS, B.SMA_Dt, INNER, JOIN, B, A.CustomerEntityID, B.CustomerEntityID, A.FLGSMA, Y | WHERE: A.FLGSMA='Y' | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_34 | parse=regex_fallback | Verified |
| 10 | Aggregate SMA class at UCIF level | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM ##CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID WHERE A.FLGSMA='Y' | 01_nested_block_4:nested_block | tables_read[23]: 01_nested_block_4:chunk_text_07 | `PRO.SMA_MOVEMENT_HISTORY` | target: 1 | source: 1 | WHERE: TIMEKEY=@TIMEKEY) BEGIN | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_07 | parse=regex_fallback; tables_written[26]: 01_nested_block_4:chunk_text_07 | `##CUSTOMERCAL` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: A, B.MAXSMA_CLASS, B.SMA_Dt, INNER, JOIN, B, A.UCIF_ID, B.UCIF_ID, A.FLGSMA, Y, IF, PRO.SMA_MOVEMENT_HISTORY, TIMEKEY | WHERE: A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_07 | parse=regex_fallback | Verified |
| 11 | Update movement history for account | Insert into PRO.ACCOUNT_MOVEMENT_HISTORY | 01_nested_block_5:nested_block; 01_nested_block_4:nested_block | conditions[50]: (CASE WHEN  B.CustomerAcID IS NULL THEN 1  WHEN B.CustomerAcID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 -> Insert into PRO.ACCOUNT_MOVEMENT_HISTORY; tables_read[29]: 01_nested_block_4:chunk_text_16 | `#SMACLASS` | target: @TIMEKEY, CustomerAcID, SMA_CLASS | source: CustomerAcID, SMA_CLASS | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: None | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_16 | parse=parsed; tables_read[34]: 01_nested_block_4:embedded_01_46 | `#SMACLASS` | target: @TIMEKEY, CustomerAcID, SMA_CLASS | source: @TIMEKEY, CustomerAcID, SMA_CLASS | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: None | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_46 | parse=regex_fallback; tables_read[35]: 01_nested_block_5:chunk_text_01 | `PRO.ACCOUNT_MOVEMENT_HISTORY` | target: 1 | source: 1 | WHERE: [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6, 1, 'NO NEDD TO INSERT DATA' | provenance: 01_nested_block_5:nested_block | 01_nested_block_5:chunk_text_01 | parse=regex_fallback; tables_written[63]: 01_nested_block_5:chunk_text_01 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: LOS, FinalAssetClassAlt_Key, is, if, PRO.ACCOUNT_MOVEMENT_HISTORY, EffectiveFromTimeKey, print, NO, NEDD, TO, DATA | WHERE: FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA' | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6, 1, 'NO NEDD TO INSERT DATA' | provenance: 01_nested_block_5:nested_block | 01_nested_block_5:chunk_text_01 | parse=regex_fallback; tables_written[65]: 01_nested_block_5:chunk_text_05 | `PRO.ACCOUNT_MOVEMENT_HISTORY` | INSERT | target: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | source: N/A | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: None | provenance: 01_nested_block_5:nested_block | 01_nested_block_5:chunk_text_05 | parse=parsed | Verified |
| 12 | Update movement history for customer | INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY | 01_nested_block_6:nested_block | conditions[53]: (CASE WHEN  B.SourceSystemCustomerID IS NULL THEN 1  WHEN B.SourceSystemCustomerID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 -> INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY ... SELECT ...; tables_written[70]: 01_nested_block_6:chunk_text_06 | `PRO.CUSTOMER_MOVEMENT_HISTORY` | INSERT | target: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | source: N/A | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: None | provenance: 01_nested_block_6:nested_block | 01_nested_block_6:chunk_text_06 | parse=parsed | Verified |
| 13 | Set movement description for asset class | UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1; UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2; UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3; UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4; UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5; UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6 | 01_nested_block_4:nested_block | tables_written[32]: 01_nested_block_4:chunk_text_17 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'STD', 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_17 | parse=parsed; tables_written[49]: 01_nested_block_4:embedded_01_47 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: STD, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'STD', 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_47 | parse=regex_fallback; tables_written[33]: 01_nested_block_4:chunk_text_18 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 2 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SUB', 2 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_18 | parse=parsed; tables_written[50]: 01_nested_block_4:embedded_01_48 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SUB, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=2 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SUB', 2 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_48 | parse=regex_fallback; tables_written[34]: 01_nested_block_4:chunk_text_19 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 3 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB1', 3 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_19 | parse=parsed; tables_written[51]: 01_nested_block_4:embedded_01_49 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: DB1, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=3 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB1', 3 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_49 | parse=regex_fallback; tables_written[35]: 01_nested_block_4:chunk_text_20 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 4 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB2', 4 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_20 | parse=parsed; tables_written[52]: 01_nested_block_4:embedded_01_50 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: DB2, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=4 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB2', 4 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_50 | parse=regex_fallback; tables_written[36]: 01_nested_block_4:chunk_text_21 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 5 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB3', 5 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_21 | parse=parsed; tables_written[53]: 01_nested_block_4:embedded_01_51 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: DB3, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=5 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB3', 5 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_51 | parse=regex_fallback; tables_written[37]: 01_nested_block_4:chunk_text_22 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 6 | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_22 | parse=parsed; tables_written[54]: 01_nested_block_4:embedded_01_52 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: LOS, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=6 | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_52 | parse=regex_fallback | Verified |
| 14 | Set movement description for SMA class key | UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1; UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2; UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3 | 01_nested_block_4:nested_block | tables_written[38]: 01_nested_block_4:chunk_text_23 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY = 1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_0', 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_23 | parse=parsed; tables_written[55]: 01_nested_block_4:embedded_01_53 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SMA_0, SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY=1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_0', 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_53 | parse=regex_fallback; tables_written[39]: 01_nested_block_4:chunk_text_24 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY = 2 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_1', 2 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_24 | parse=parsed; tables_written[56]: 01_nested_block_4:embedded_01_54 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SMA_1, SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY=2 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_1', 2 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_54 | parse=regex_fallback; tables_written[40]: 01_nested_block_4:chunk_text_25 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY = 3 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_2', 3 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_25 | parse=parsed; tables_written[57]: 01_nested_block_4:embedded_01_55 | `##CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SMA_2, SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY=3 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_2', 3 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_55 | parse=regex_fallback | Verified |
| 15 | Default SMA class for missing values | UPDATE  ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL; UPDATE  ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL; UPDATE  ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL; UPDATE  ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL; UPDATE  ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL; UPDATE  ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL | 01_nested_block_4:nested_block; 01_nested_block_5:nested_block | tables_written[41]: 01_nested_block_4:chunk_text_26 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'STD', 1, NULL | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_26 | parse=parsed; tables_written[58]: 01_nested_block_4:embedded_01_56 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: STD, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'STD', 1 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_56 | parse=regex_fallback; tables_written[42]: 01_nested_block_4:chunk_text_27 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'SUB', 2, NULL | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_27 | parse=parsed; tables_written[59]: 01_nested_block_4:embedded_01_57 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: SUB, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'SUB', 2 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_57 | parse=regex_fallback; tables_written[43]: 01_nested_block_4:chunk_text_28 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 3 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB1', 3, NULL | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_28 | parse=parsed; tables_written[60]: 01_nested_block_4:embedded_01_58 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: DB1, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB1', 3 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_58 | parse=regex_fallback; tables_written[44]: 01_nested_block_4:chunk_text_29 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB2', 4, NULL | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_29 | parse=parsed; tables_written[61]: 01_nested_block_4:embedded_01_59 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: DB2, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB2', 4 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_59 | parse=regex_fallback; tables_written[45]: 01_nested_block_4:chunk_text_30 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB3', 5, NULL | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:chunk_text_30 | parse=parsed; tables_written[62]: 01_nested_block_4:embedded_01_60 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: DB3, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB3', 5 | provenance: 01_nested_block_4:nested_block | 01_nested_block_4:embedded_01_60 | parse=regex_fallback; tables_read[35]: 01_nested_block_5:chunk_text_01 | `PRO.ACCOUNT_MOVEMENT_HISTORY` | target: 1 | source: 1 | WHERE: [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6, 1, 'NO NEDD TO INSERT DATA' | provenance: 01_nested_block_5:nested_block | 01_nested_block_5:chunk_text_01 | parse=regex_fallback; tables_written[63]: 01_nested_block_5:chunk_text_01 | `##AccountCal` | UPDATE | target: SMA_CLASS | source: LOS, FinalAssetClassAlt_Key, is, if, PRO.ACCOUNT_MOVEMENT_HISTORY, EffectiveFromTimeKey, print, NO, NEDD, TO, DATA | WHERE: FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA' | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6, 1, 'NO NEDD TO INSERT DATA' | provenance: 01_nested_block_5:nested_block | 01_nested_block_5:chunk_text_01 | parse=regex_fallback | Verified |

_Source evidence is the literal technical text carried through the pipeline; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails._
</details>

## Calculations / Formulas

- **Process date for SMA marking:** The process date is set to the date from the system day matrix corresponding to the input time key.
- **Effective to date for movement history:** The effective to date is set to one day before the time key from the automate advances table where the extension flag is 'Y'.
- **Conditional DPD metrics:** Each DPD metric is set to its value if it is greater than or equal to the reference period value, otherwise it is set to zero.
- **Maximum DPD value (DPD_Max):** DPD_Max is set to the highest value among all DPD metrics for the account.
- **SMA effective date:** The SMA effective date is calculated as the process date minus the maximum DPD value plus one.
- **Customer-level maximum SMA class:** The maximum SMA class key for a customer is determined by mapping SMA_0 to 1, SMA_1 to 2, SMA_2 to 3, and taking the highest value among the customer's accounts.

## Exception Handling Behavior

If an error occurs during processing, all temporary tables are dropped and the process status table is updated to indicate failure, including the error date and description. The process count is incremented to track the number of attempts.

## Rule Provenance Summary

**Technical Implementation:** derived directly from the parsed source code and the per-chunk technical extraction (conditions, table reads/writes, calculations) - see Tables Read/Written above.

**Business Interpretation:** the Purpose Summary, Step-by-Step Logic Flow, and Business Rules sections translate that technical implementation into plain business language; the breakdown below shows how much of that interpretation is a direct restatement versus an inference or an assumption.

- **Total business rules:** 15
- **By rule type:** explicit = 15
- **By validation status:** unverified = 3, verified = 12

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Ambiguities / Needs Review

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): SELECT         A.CustomerAcID,A.AccountEntityID,A.DPD_Overdrawn,ContiExcessDt,DPD_Renewal,ReviewDueDt 
into           #...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): SELECT A.CustomerAcID  
   ,CASE WHEN  isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0)  THEN A.DPD_IntServi...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.FLGSMA=NULL  
             ,A.SMA_CLASS_KEY=NULL  
       ,A.SMA_DT=NULL  
     FROM ##CUSTOMERCAL A...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE  ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL  
    
  
  
 --IF OB...
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
- Some code is commented out, so actual execution may differ from what is shown in the extraction.
- References to columns such as FINALASSETCLASSALT_KEY and DPD_Max are used without explicit table alias in some places; the business meaning is inferred from context.
- The code chunk only contains the keyword 'TRY' with no further logic, so no procedural content is present to extract.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE   A SET A.DPD_Max= (CASE ... END) FROM  #DPD a WHERE  isnull(A.DPD_Overdrawn,0)>0   OR  Isnull(A.DPD_Overdue,0)>0
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.SMA_CLASS=  (CASE  WHEN dpd.DPD_Max  BETWEEN 1 AND 30  THEN 'SMA_0' ... END)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.SMA_REASON= (CASE ... END)
