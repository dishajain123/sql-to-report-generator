## Object Overview

- **Object Name:** `SMA_MARKING_12122023`
- **Object Type:** Procedure
- **SQL Dialect:** SQL Server T-SQL
- **Parameters:**

| Parameter | Direction | Datatype |
|---|---|---|
| `@TIMEKEY` | IN | INT |

## Purpose Summary

This procedure automates the identification and marking of Special Mention Accounts (SMA) for advances, in line with regulatory and internal asset classification requirements. It calculates Days Past Due (DPD) metrics for accounts, assigns SMA categories based on overdue status, records reasons for SMA downgrades, and maintains historical movement records for both account and customer asset classifications. The process ensures accurate, timely, and auditable SMA status updates for regulatory compliance and risk monitoring.

## Tables Read

| Table Name | Business Context | Filter Conditions |
|---|---|---|
| `SYSDAYMATRIX` | DATE | TIMEKEY = @TIMEKEY |
| `dbo.Automate_Advances` | Timekey-1 | None |
| `#DPD` | AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, 0 AS DPD_IntService, 0 AS DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, 0 AS DPD_Renewal, 0 AS DPD_StockStmt, 0 AS DPD_MAX | COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0 |
| `PRO.AccountCal` | AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, 0 AS DPD_IntService, 0 AS DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, 0 AS DPD_Renewal, 0 AS DPD_StockStmt, 0 AS DPD_MAX | COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0 |
| `#TEMPTABLE` | A.CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.RefPeriodNoCredit, 0) THEN A.DPD_NoCredit ELSE 0 END AS DPD_NoCredit, CASE WHEN COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.RefPeriodOverDrawn, 0) THEN A.DPD_Overdrawn ELSE 0 END AS DPD_Overdrawn, CASE WHEN COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.RefPeriodOverdue, 0) THEN A.DPD_Overdue ELSE 0 END AS DPD_Overdue, CASE WHEN COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.RefPeriodReview, 0) THEN A.DPD_Renewal ELSE 0 END AS DPD_Renewal, CASE WHEN COALESCE(A.DPD_StockStmt, 0) >= COALESCE(A.RefPeriodStkStatement, 0) THEN A.DPD_StockStmt ELSE 0 END AS DPD_StockStmt | (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0)) |
| `#DPD` | A.CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.RefPeriodNoCredit, 0) THEN A.DPD_NoCredit ELSE 0 END AS DPD_NoCredit, CASE WHEN COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.RefPeriodOverDrawn, 0) THEN A.DPD_Overdrawn ELSE 0 END AS DPD_Overdrawn, CASE WHEN COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.RefPeriodOverdue, 0) THEN A.DPD_Overdue ELSE 0 END AS DPD_Overdue, CASE WHEN COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.RefPeriodReview, 0) THEN A.DPD_Renewal ELSE 0 END AS DPD_Renewal, CASE WHEN COALESCE(A.DPD_StockStmt, 0) >= COALESCE(A.RefPeriodStkStatement, 0) THEN A.DPD_StockStmt ELSE 0 END AS DPD_StockStmt | (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0)) |
| `PRO.AccountCal` | AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, 0 AS DPD_IntService, 0 AS DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, 0 AS DPD_Renewal, 0 AS DPD_StockStmt, 0 AS DPD_MAX  
 INTO #DPD | isnull(A.DPD_Overdrawn,0)>30 OR Isnull(A.DPD_Overdue,0)>0 |
| `#DPD` | A.CustomerAcID, CASE WHEN  isnull(A.DPD_IntService, 0)>=isnull(A.RefPeriodIntService, 0)  THEN A.DPD_IntService  ELSE 0   END DPD_IntService, CASE WHEN  isnull(A.DPD_NoCredit, 0)>=isnull(A.RefPeriodNoCredit, 0)   THEN A.DPD_NoCredit    ELSE 0   END DPD_NoCredit, CASE WHEN  isnull(A.DPD_Overdrawn, 0)>=isnull(A.RefPeriodOverDrawn, 0)     THEN A.DPD_Overdrawn   ELSE 0   END DPD_Overdrawn, CASE WHEN  isnull(A.DPD_Overdue, 0)>=isnull(A.RefPeriodOverdue, 0)      THEN A.DPD_Overdue     ELSE 0   END DPD_Overdue, CASE WHEN  isnull(A.DPD_Renewal, 0)>=isnull(A.RefPeriodReview, 0)   THEN A.DPD_Renewal     ELSE 0   END  DPD_Renewal, CASE WHEN  isnull(A.DPD_StockStmt, 0)>=isnull(A.RefPeriodStkStatement, 0)       THEN A.DPD_StockStmt   ELSE 0   END DPD_StockStmt    
    INTO #TEMPTABLE | ( isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) ) |
| `#TEMPTABLE_SMACLASS` | A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER PRO.CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y' |
| `PRO.ACCOUNTCAL` | A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER PRO.CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y' |
| `PRO.CUSTOMERCAL` | A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER PRO.CUSTOMERCAL ON A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y' |
| `#TEMPTABLE_SMACLASS` | B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | A.FLGSMA = 'Y'; INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID |
| `#TEMPTABLE_SMACLASSUcif` | A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER PRO.CUSTOMERCAL ON A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y' |
| `PRO.ACCOUNTCAL` | A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER PRO.CUSTOMERCAL ON A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y' |
| `PRO.CUSTOMERCAL` | A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | INNER PRO.CUSTOMERCAL ON A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y' |
| `PRO.SMA_MOVEMENT_HISTORY` | 1 | None |
| `#SMACLASS` | A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1; INNER PRO.CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' |
| `PRO.ACCOUNTCAL` | A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1; INNER PRO.CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' |
| `PRO.CUSTOMERCAL` | A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1; INNER PRO.CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' |
| `PRO.PREVSMASTATUS` | @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS | OUTER SMACLASS ON A.CustomerAcID = B.CustomerAcID |
| `#SMACLASS` | @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS | OUTER SMACLASS ON A.CustomerAcID = B.CustomerAcID |
| `PRO.ACCOUNTCAL` | A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1   
                             WHEN SMA_CLASS='SMA_1' THEN  2  
        WHEN SMA_CLASS='SMA_2' THEN  3 ELSE 0 END ) MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt  
                                 
INTO #TEMPTABLE_SMACLASS | None |
| `PRO.ACCOUNTCAL` | A.UCIF_ID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1   
                          WHEN SMA_CLASS='SMA_1' THEN  2  
                          WHEN SMA_CLASS='SMA_2' THEN  3 ELSE 0 END ) MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt  
                                 
INTO #TEMPTABLE_SMACLASSUcif | None |
| `PRO.ACCOUNTCAL` | A.CustomerAcID, ISNULL(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2'))  SMA_CLASS INTO #SMACLASS | B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1 |
| `PRO.PREVSMASTATUS` | @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS | None |
| `#SMACLASS` | @TIMEKEY, CustomerAcID, SMA_CLASS | None |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | 1 | None |
| `PRO.ACCOUNTCAL` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey, SMA_CLASS AS MovementFromStatus, SMA_CLASS AS MovementToStatus, COALESCE(Balance, 0) AS TotOsAcc, @ProcessDate AS MovementFromDate, '2086-11-21' AS MovementToDate | None |
| `#SMACLASS` | @TIMEKEY, CustomerAcID, SMA_CLASS | None |
| `PRO.ACCOUNTCAL` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS  EffectiveToTimeKey, SMA_CLASS AS MovementFromStatus, SMA_CLASS AS MovementToStatus, ISNULL(Balance, 0) as TotOsAcc, @ProcessDate MovementFromDate, '2086-11-21' MovementToDate | None |
| `#ACCOUNT_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsAcc, 0) AS TotOsAcc, A.MovementFromDate, A.MovementToDate | (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN NOT B.CustomerAcID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1; LEFT JOIN PRO.ACCOUNT_MOVEMENT_HISTORY ON A.CustomerAcID = B.CustomerAcID AND B.EFFECTIVETOTimekey = 49999 |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsAcc, 0) AS TotOsAcc, A.MovementFromDate, A.MovementToDate | (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN NOT B.CustomerAcID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1; LEFT JOIN PRO.ACCOUNT_MOVEMENT_HISTORY ON A.CustomerAcID = B.CustomerAcID AND B.EFFECTIVETOTimekey = 49999 |
| `#ACCOUNT_MOVEMENT_HISTORY` | AA.EffectiveToTimeKey, B.CustomerAcID, AA.CustomerAcID, B.EffectiveToTimeKey | AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL; LEFT JOIN ACCOUNT_MOVEMENT_HISTORY ON AA.CustomerAcID = B.CustomerAcID AND B.EffectiveToTimeKey = 49999 |
| `#ACCOUNT_MOVEMENT_HISTORY` | AA.EffectiveToTimeKey, AA.EffectiveFROMTimeKey, AA.MOVEMENTTOSTATUS, BB.MOVEMENTTOSTATUS, AA.CustomerAcID, BB.CustomerAcID, BB.EffectiveToTimeKey | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey < @TIMEKEY AND EXISTS(SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY AS BB WHERE AA.CustomerAcID = BB.CustomerAcID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS); EXISTS: EXISTS(SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY AS BB WHERE AA.CustomerAcID = BB.CustomerAcID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS) [tables: ACCOUNT_MOVEMENT_HISTORY] |
| `PRO.CustomerCal` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, 49999 AS EffectiveToTimeKey, CustMoveDescription AS MovementFromStatus, CustMoveDescription AS MovementToStatus, COALESCE(TotOsCust, 0) AS TotOsCust, @ProcessDate AS MovementFromDate, '2086-11-21' AS MovementToDate | None |
| `#Customer_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsCust, 0) AS TotOsCust, A.MovementFromDate, A.MovementToDate | LEFT JOIN PRO.CUSTOMER_MOVEMENT_HISTORY ON A.SourceSystemCustomerID = B.SourceSystemCustomerID |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsCust, 0) AS TotOsCust, A.MovementFromDate, A.MovementToDate | LEFT JOIN PRO.CUSTOMER_MOVEMENT_HISTORY ON A.SourceSystemCustomerID = B.SourceSystemCustomerID |
| `#ACCOUNT_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, ISNULL(A.TotOsAcc, 0) AS TotOsAcc, A.MovementFromDate, A.MovementToDate | (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN B.CustomerAcID IS NOT NULL AND A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 |
| `#ACCOUNT_MOVEMENT_HISTORY` | 1 | AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS ) |
| `PRO.CustomerCal` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, 49999 AS  EffectiveToTimeKey, CustMoveDescription AS MovementFromStatus, CustMoveDescription AS MovementToStatus, ISNULL(TotOsCust, 0) AS TotOsCust, @ProcessDate MovementFromDate, '2086-11-21' MovementToDate | None |
| `#Customer_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, ISNULL(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, ISNULL(A.TotOsCust, 0) AS TotOsCust, A.MovementFromDate, A.MovementToDate | None |
| `#Customer_MOVEMENT_HISTORY` | AA.EffectiveToTimeKey, B.SourceSystemCustomerID, AA.SourceSystemCustomerID, B.EffectiveToTimeKey | AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL; LEFT JOIN Customer_MOVEMENT_HISTORY ON AA.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EffectiveToTimeKey = 49999 |
| `#Customer_MOVEMENT_HISTORY` | AA.EffectiveToTimeKey, AA.EffectiveFROMTimeKey, AA.MOVEMENTTOSTATUS, BB.MOVEMENTTOSTATUS, AA.SourceSystemCustomerID, BB.SourceSystemCustomerID, BB.EffectiveToTimeKey | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey < @TIMEKEY AND EXISTS(SELECT 1 FROM #Customer_MOVEMENT_HISTORY AS BB WHERE AA.SourceSystemCustomerID = BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS); EXISTS: EXISTS(SELECT 1 FROM #Customer_MOVEMENT_HISTORY AS BB WHERE AA.SourceSystemCustomerID = BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS) [tables: Customer_MOVEMENT_HISTORY] |
| `#Customer_MOVEMENT_HISTORY` | 1 | AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS ) |

## Tables Written

| Table Name | Operation Type | Columns Affected | Business Trigger |
|---|---|---|---|
| `#DPD` | `UPDATE` | DPD_IntService | COALESCE(DPD_IntService, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_NoCredit | COALESCE(DPD_NoCredit, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_Overdrawn | COALESCE(DPD_Overdrawn, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_Overdue | COALESCE(DPD_Overdue, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_Renewal | COALESCE(DPD_Renewal, 0) < 0 |
| `#DPD` | `UPDATE` | DPD_StockStmt | isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE |
| `#DPD` | `UPDATE` | A.DPD_Max | None |
| `A` | `UPDATE` | A.DPD_Max | None |
| `#DPD` | `UPDATE` | DPD_IntService | isnull(DPD_IntService,0)<0 |
| `#DPD` | `UPDATE` | DPD_NoCredit | isnull(DPD_NoCredit,0)<0 |
| `#DPD` | `UPDATE` | DPD_Overdrawn | isnull(DPD_Overdrawn,0)<0 |
| `#DPD` | `UPDATE` | DPD_Overdue | isnull(DPD_Overdue,0)<0 |
| `#DPD` | `UPDATE` | DPD_Renewal | isnull(DPD_Renewal,0)<0 |
| `A` | `UPDATE` | A.DPD_Max | None |
| `PRO.ACCOUNTCAL` | `UPDATE` | A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | None |
| `A` | `UPDATE` | A.SMA_CLASS | None |
| `A` | `UPDATE` | A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA | None |
| `PRO.CUSTOMERCAL` | `UPDATE` | A.FLGSMA, A.SMA_CLASS_KEY, A.SMA_DT | None |
| `A` | `UPDATE` | A.FLGSMA | B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS |
| `PRO.CUSTOMERCAL` | `UPDATE` | A.SMA_CLASS_KEY, A.SMA_DT | A.FLGSMA = 'Y'; INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID |
| `A` | `UPDATE` | A.FLGSMA | B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif |
| `A` | `UPDATE` | A.SMA_CLASS_KEY, A.SMA_DT | A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN |
| `PRO.SMA_MOVEMENT_HISTORY` | `DELETE` | TIMEKEY | TIMEKEY = @TIMEKEY |
| `#SMACLASS` | `UPDATE` | SMA_CLASS | None |
| `PRO.SMA_MOVEMENT_HISTORY` | `INSERT` | TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS | None |
| `A` | `UPDATE` | A.FLGSMA, A.SMA_CLASS_KEY, A.SMA_DT | None |
| `A` | `UPDATE` | A.SMA_CLASS_KEY, A.SMA_DT | A.FLGSMA='Y' |
| `#SMACLASS` | `UPDATE` | SMA_CLASS | None |
| `PRO.PREVSMASTATUS` | `INSERT` | Not identified | None |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 1 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 2 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 3 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 4 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 5 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY = 6 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY = 1 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY = 2 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY = 3 |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 3 AND SMA_CLASS IS NULL |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO |
| `#ACCOUNT_MOVEMENT_HISTORY` | `INSERT` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | None |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=1 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=2 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=3 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=4 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=5 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SYSASSETCLASSALT_KEY=6 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY=1 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY=2 |
| `PRO.CUSTOMERCAL` | `UPDATE` | CustMoveDescription | SMA_CLASS_KEY=3 |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL |
| `PRO.AccountCal` | `UPDATE` | SMA_CLASS | FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL; LEFT JOIN ACCOUNT_MOVEMENT_HISTORY ON AA.CustomerAcID = B.CustomerAcID AND B.EffectiveToTimeKey = 49999 |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey < @TIMEKEY AND EXISTS(SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY AS BB WHERE AA.CustomerAcID = BB.CustomerAcID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS); EXISTS: EXISTS(SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY AS BB WHERE AA.CustomerAcID = BB.CustomerAcID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS) [tables: ACCOUNT_MOVEMENT_HISTORY] |
| `#Customer_MOVEMENT_HISTORY` | `INSERT` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, totOsCust, MovementFromDate, MovementToDate | None |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | `INSERT` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | None |
| `AA` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null |
| `AA` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS ) |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL; LEFT JOIN Customer_MOVEMENT_HISTORY ON AA.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EffectiveToTimeKey = 49999 |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey < @TIMEKEY AND EXISTS(SELECT 1 FROM #Customer_MOVEMENT_HISTORY AS BB WHERE AA.SourceSystemCustomerID = BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS); EXISTS: EXISTS(SELECT 1 FROM #Customer_MOVEMENT_HISTORY AS BB WHERE AA.SourceSystemCustomerID = BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS) [tables: Customer_MOVEMENT_HISTORY] |
| `PRO.ACLRUNNINGPROCESSSTATUS` | `UPDATE` | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME = 'SMA_MARKING' |
| `AA` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.SourceSystemCustomerID is null |
| `AA` | `UPDATE` | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS ) |
| `PRO.ACLRUNNINGPROCESSSTATUS` | `UPDATE` | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME='SMA_MARKING' |
| `PRO.ACLRUNNINGPROCESSSTATUS` | `UPDATE` | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME = 'SMA_MARKING' |
| `PRO.ACLRUNNINGPROCESSSTATUS` | `UPDATE` | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME='SMA_MARKING' |

## Step-by-Step Logic Flow

1. Retrieve the processing date corresponding to the provided time key.
2. Identify accounts with significant overdue or overdrawn amounts and calculate DPD metrics for each relevant dimension (interest servicing, credit, overdrawn, overdue, renewal, stock statement).
3. Ensure all DPD metrics are non-negative by resetting any negative values to zero.
4. For each account, determine the maximum DPD value across all DPD types.
5. For accounts meeting eligibility criteria (e.g., not already processed, standard asset class, positive balance, not always standard), assign the appropriate SMA class based on the maximum DPD value.
6. Assign a specific SMA downgrade reason based on the facility type and which DPD metric triggered the downgrade.
7. Set the SMA effective date based on the processing date and the DPD value.
8. Mark accounts and customers as flagged for SMA if any of their linked accounts are flagged.
9. Aggregate SMA class information at the customer and UCIF (unique customer identifier) levels, updating customer records with the highest SMA class and earliest SMA date.
10. Maintain movement history by recording previous and current SMA statuses for each account and customer, updating effective dates as needed.
11. Update descriptive fields for customer and account movement based on asset classification and SMA class.
12. Update process completion status and error tracking for operational monitoring.
13. On error, update process status with error details for audit and troubleshooting.

# Business Conditions Report — SMA_MARKING_12122023

> **What this process does:** This procedure automates the identification and marking of Special Mention Accounts (SMA) for advances, in line with regulatory and internal asset classification requirements. It calculates Days Past Due (DPD) metrics for accounts, assigns SMA categories based on overdue status, records reasons for SMA downgrades, and maintains historical movement records for both account and customer asset classifications. The process ensures accurate, timely, and auditable SMA status updates for regulatory compliance and risk monitoring.

## Glossary

| Term | Business Meaning |
|---|---|
| @TIMEKEY | Declared as IN INT. `TIMEKEY = @TIMEKEY`; `UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM PRO.CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID WHERE A.FLGSMA='Y' IF EXISTS(SELEC…` |
| TIMEKEY | Source field read in active SQL on SYSDAYMATRIX, A, PRO.SMA_MOVEMENT_HISTORY. Referenced in active predicate(s): `A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN`; `TIMEKEY = @TIMEKEY` |
| DATE | Source field read in active SQL from SYSDAYMATRIX. |
| 1 | Literal used in active SQL: `1`. Observed in active predicate(s): `Literal value used in active statement `Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y') --IF OBJECT_ID('TEMPDB..#Dpd…`; `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'Y' | Literal used in active SQL: `'Y'`. Observed in active predicate(s): `Flag literal used in active read on dbo.Automate_Advances for Timekey-1.`; `Flag literal used in active update on A for A.FLGSMA.` |
| 'TEMPDB..#DPD' | Literal used in active SQL: `'TEMPDB..#DPD'`. Observed in active predicate(s): `Literal value used in active statement `Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1 FROM [dbo].Automate_Advances WHERE EXT_FLG='Y') --IF OBJECT_ID('TEMPDB..#Dpd…` |
| A.DPD_OVERDRAWN | Calculated field updated in active SQL using `CASE` on #DPD, PRO.AccountCal, #TEMPTABLE, A: `(CASE WHEN A.ContiExcessDt IS NOT NULL THEN DATEDIFF(DAY,A.ContiExcessDt, '2020-12-31') + 1 ELSE 0 END) --`. Source field read in active SQL on #DPD, PRO.AccountCal, #TEMPTABLE, A. Source field read in active SQL from #DPD, PRO.AccountCal, #TEMPTABLE, A. Also referenced in active predicate(s): `COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0`; `0` Referenced in active predicate(s): `COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0`; `0` |
| A.DPD_OVERDUE | Calculated field updated in active SQL using `CASE` on #DPD, PRO.AccountCal, #TEMPTABLE, A: `(CASE WHEN A.OverDueSinceDt IS NOT NULL THEN DATEDIFF(DAY,A.OverDueSinceDt, '2020-12-31') ELSE 0 END) --`. Source field read in active SQL on #DPD, PRO.AccountCal, #TEMPTABLE, A. Source field read in active SQL from #DPD, PRO.AccountCal, #TEMPTABLE, A. Also referenced in active predicate(s): `COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0`; `0` Referenced in active predicate(s): `COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0`; `0` |
| AccountEntityID | Source field read in active SQL from #DPD, PRO.AccountCal. |
| UcifEntityID | Source field read in active SQL from #DPD, PRO.AccountCal. |
| CustomerEntityID | Source field read in active SQL on #DPD, PRO.AccountCal, A, #TEMPTABLE_SMACLASS, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, #SMACLASS. Source field read in active SQL from #DPD, PRO.AccountCal, A, #TEMPTABLE_SMACLASS, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, #SMACLASS. Also referenced in active predicate(s): `A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y'`; `A.CustomerEntityID = B.CustomerEntityID` Referenced in active predicate(s): `A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y'`; `A.CustomerEntityID = B.CustomerEntityID` |
| CustomerAcID | Source field read in active SQL on #DPD, PRO.AccountCal, #TEMPTABLE, #SMACLASS, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, PRO.SMA_MOVEMENT_HISTORY, PRO.PREVSMASTATUS, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, AA. Source field read in active SQL from #DPD, PRO.AccountCal, #TEMPTABLE, #SMACLASS, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, PRO.SMA_MOVEMENT_HISTORY, PRO.PREVSMASTATUS, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, AA. Also referenced in active predicate(s): `Inserted field populated in active INSERT into PRO.SMA_MOVEMENT_HISTORY.`; `A.CustomerAcID = B.CustomerAcID` Referenced in active predicate(s): `Inserted field populated in active INSERT into PRO.SMA_MOVEMENT_HISTORY.`; `A.CustomerAcID = B.CustomerAcID` |
| RefCustomerID | Source field read in active SQL from #DPD, PRO.AccountCal, #SMACLASS, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.` Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.` |
| SourceSystemCustomerID | Source field read in active SQL on #DPD, PRO.AccountCal, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNTCAL, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY, AA. Source field read in active SQL from #DPD, PRO.AccountCal, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNTCAL, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY, AA. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.` Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.` |
| UCIF_ID | Source field read in active SQL on #DPD, PRO.AccountCal, A, #TEMPTABLE_SMACLASSUcif, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Source field read in active SQL from #DPD, PRO.AccountCal, A, #TEMPTABLE_SMACLASSUcif, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y'`; `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.` Referenced in active predicate(s): `A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y'`; `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.` |
| IntNotServicedDt | Source field read in active SQL from #DPD, PRO.AccountCal. |
| LastCrDate | Source field read in active SQL from #DPD, PRO.AccountCal. |
| ContiExcessDt | Source field read in active SQL from #DPD, PRO.AccountCal. |
| OverDueSinceDt | Source field read in active SQL from #DPD, PRO.AccountCal. |
| ReviewDueDt | Source field read in active SQL from #DPD, PRO.AccountCal. |
| StockStDt | Source field read in active SQL from #DPD, PRO.AccountCal. |
| RefPeriodIntService | Source field read in active SQL from #DPD, PRO.AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| RefPeriodNoCredit | Source field read in active SQL from #DPD, PRO.AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| RefPeriodOverDrawn | Source field read in active SQL from #DPD, PRO.AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| RefPeriodOverdue | Source field read in active SQL from #DPD, PRO.AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| RefPeriodReview | Source field read in active SQL from #DPD, PRO.AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| RefPeriodStkStatement | Source field read in active SQL from #DPD, PRO.AccountCal, #TEMPTABLE. Referenced in active predicate(s): |
| 0 | Literal used in active SQL: `0`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0`.`; `Literal reset value used in active update on #DPD for DPD_IntService.` |
| 30 | Literal used in active SQL: `30`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0`.`; `Threshold or filter literal used in active predicate `isnull(A.DPD_Overdrawn,0)>30 OR Isnull(A.DPD_Overdue,0)>0`.` |
| DPD_INTSERVICE | Target field updated in active SQL on #DPD, #TEMPTABLE, A from `0`. Source field read in active SQL on #DPD, #TEMPTABLE, A. Referenced in active predicate(s): `0`; `isnull(DPD_IntService,0)<0` |
| DPD_NOCREDIT | Target field updated in active SQL on #DPD, #TEMPTABLE, A from `0`. Source field read in active SQL on #DPD, #TEMPTABLE, A. Referenced in active predicate(s): `0`; `isnull(DPD_NoCredit,0)<0` |
| DPD_RENEWAL | Target field updated in active SQL on #DPD, #TEMPTABLE, A from `0`. Source field read in active SQL on #DPD, #TEMPTABLE, A. Referenced in active predicate(s): `0`; `isnull(DPD_Renewal,0)<0` |
| DPD_STOCKSTMT | Target field updated in active SQL on #DPD, #TEMPTABLE, A from `0`. Source field read in active SQL on #DPD, #TEMPTABLE, A. Referenced in active predicate(s): `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE`; `0` |
| IF | Source field read in active SQL on #DPD, A, PRO.AccountCal. Referenced in active predicate(s): `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE`; `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS` |
| OBJECT_ID | Source field read in active SQL on #DPD, A. Referenced in active predicate(s): `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE`; `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS` |
| TEMPDB..#TEMPTABLE | Referenced in active predicate(s): `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE` |
| DROP | Source field read in active SQL on #DPD, A. Referenced in active predicate(s): `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE`; `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS` |
| TABLE | Source field read in active SQL on #DPD, A. Referenced in active predicate(s): `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE`; `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS` |
| isnull | Source field read in active SQL on #DPD, A, PRO.ACLRUNNINGPROCESSSTATUS. |
| TEMPDB | Source field read in active SQL on #DPD, A. |
| IS | Source field read in active SQL on #DPD, A, PRO.AccountCal, AA. |
| 'TEMPDB..#TEMPTABLE' | Literal used in active SQL: `'TEMPDB..#TEMPTABLE'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE`. Target field updated in acti…` |
| A.DPD_Max | Target field updated in active SQL on #DPD, A from `0`. Source field read in active SQL on #DPD, A. |
| A | Source field read in active SQL on A. |
| A.SMA_CLASS | Calculated field updated in active SQL using `CASE` on PRO.ACCOUNTCAL, A, #SMACLASS, PRO.PREVSMASTATUS, PRO.AccountCal: `NULL`. Source field read in active SQL from PRO.ACCOUNTCAL, A, #SMACLASS, PRO.PREVSMASTATUS, PRO.AccountCal. Also referenced in active predicate(s): `NULL`; `(CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA…` Referenced in active predicate(s): `NULL`; `(CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA…` |
| A.SMA_REASON | Calculated field updated in active SQL using `CASE` on PRO.ACCOUNTCAL, A: `NULL`. |
| A.SMA_DT | Target field updated in active SQL on PRO.ACCOUNTCAL, A, PRO.CUSTOMERCAL from `NULL`. Source field read in active SQL on PRO.ACCOUNTCAL, A, PRO.CUSTOMERCAL. |
| A.FLGSMA | Target field updated in active SQL on PRO.ACCOUNTCAL, A, PRO.CUSTOMERCAL, #TEMPTABLE_SMACLASS, #TEMPTABLE_SMACLASSUcif, #SMACLASS from `NULL`. Source field read in active SQL on PRO.ACCOUNTCAL, A, PRO.CUSTOMERCAL, #TEMPTABLE_SMACLASS, #TEMPTABLE_SMACLASSUcif, #SMACLASS. Referenced in active predicate(s): `NULL`; `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS` |
| BETWEEN | Source field read in active SQL on A. |
| SMA_0 | Source field read in active SQL on A, #SMACLASS, PRO.CUSTOMERCAL. |
| SMA_1 | Source field read in active SQL on A, #SMACLASS, PRO.CUSTOMERCAL. |
| SMA_2 | Source field read in active SQL on A, #SMACLASS, PRO.CUSTOMERCAL. |
| 'SMA_0' | Literal used in active SQL: `'SMA_0'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…`; `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…` |
| 31 | Literal used in active SQL: `31`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 60 | Literal used in active SQL: `60`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'SMA_1' | Literal used in active SQL: `'SMA_1'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…`; `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…` |
| 61 | Literal used in active SQL: `61`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 90 | Literal used in active SQL: `90`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…` |
| 'SMA_2' | Literal used in active SQL: `'SMA_2'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE A SET A.SMA_CLASS= (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD…`; `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…` |
| PRO.ACCOUNTCAL | Source field read in active SQL on A, PRO.AccountCal. |
| A.SMA_CLASS_KEY | Target field updated in active SQL on PRO.CUSTOMERCAL, A from `NULL`. Source field read in active SQL on PRO.CUSTOMERCAL, A. Referenced in active predicate(s): `NULL`; `B.MAXSMA_CLASS` |
| Y | Source field read in active SQL on A, #TEMPTABLE_SMACLASS, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, #TEMPTABLE_SMACLASSUcif, #SMACLASS, PRO.ACLRUNNINGPROCESSSTATUS. Referenced in active predicate(s): `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS`; `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif` |
| TEMPDB..#TEMPTABLE_SMACLASS | Referenced in active predicate(s): `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS` |
| PRO.CUSTOMERCAL | Source field read in active SQL on A, PRO.CUSTOMERCAL. |
| INNER | Source field read in active SQL on A. |
| JOIN | Source field read in active SQL on A, AA. |
| B | Source field read in active SQL on A, AA. |
| 'TEMPDB..#TEMPTABLE_SMACLASS' | Literal used in active SQL: `'TEMPDB..#TEMPTABLE_SMACLASS'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS`. Target field updated in…` |
| 2 | Literal used in active SQL: `2`. Observed in active predicate(s): `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…`; `Literal value used in active statement `SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLA…` |
| 3 | Literal used in active SQL: `3`. Observed in active predicate(s): `Literal value used in active statement `SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) M…`; `Literal value used in active statement `SELECT A.UCIF_ID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END ) MAXSMA_CLA…` |
| B.MAXSMA_CLASS | Source field read in active SQL on PRO.CUSTOMERCAL, A. |
| TEMPDB..#TEMPTABLE_SMACLASSUCIF | Referenced in active predicate(s): `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif` |
| 'TEMPDB..#TEMPTABLE_SMACLASSUcif' | Literal used in active SQL: `'TEMPDB..#TEMPTABLE_SMACLASSUcif'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif`. Target field up…` |
| PRO.SMA_MOVEMENT_HISTORY | Source field read in active SQL on A. Referenced in active predicate(s): `A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN` |
| BEGIN | Referenced in active predicate(s): `A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN`; `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO` |
| A.BALANCE | Referenced in active predicate(s): `B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1` |
| B.SYSASSETCLASSALT_KEY | Source field read in active SQL on #SMACLASS, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Source field read in active SQL from #SMACLASS, PRO.ACCOUNTCAL, PRO.CUSTOMERCAL, #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1`; `SYSASSETCLASSALT_KEY = 1` Referenced in active predicate(s): `B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1`; `SYSASSETCLASSALT_KEY = 1` |
| PREVSTATUS | Referenced in active predicate(s): `Inserted field populated in active INSERT into PRO.SMA_MOVEMENT_HISTORY.` |
| CURRENTSTATUS | Referenced in active predicate(s): `Inserted field populated in active INSERT into PRO.SMA_MOVEMENT_HISTORY.` |
| CustMoveDescription | Target field updated in active SQL on PRO.CUSTOMERCAL from `'STD'`. |
| 'STD' | Literal used in active SQL: `'STD'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1`.`; `Literal value used in active statement `UPDATE PRO.AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL`.` |
| 'SUB' | Literal used in active SQL: `'SUB'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2`.`; `Literal value used in active statement `UPDATE PRO.AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL`.` |
| 'DB1' | Literal used in active SQL: `'DB1'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3`.`; `Literal value used in active statement `UPDATE PRO.AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL`.` |
| 'DB2' | Literal used in active SQL: `'DB2'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4`.`; `Literal value used in active statement `UPDATE PRO.AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL`.` |
| 4 | Literal used in active SQL: `4`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `SYSASSETCLASSALT_KEY = 4`. Target field updated in active SQL on PRO.CUSTOMERCAL.`; `Threshold or filter literal used in active predicate `FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL`. Target field updated in active SQL on PRO.AccountCal.` |
| 'DB3' | Literal used in active SQL: `'DB3'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5`.`; `Literal value used in active statement `UPDATE PRO.AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL`.` |
| 5 | Literal used in active SQL: `5`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `SYSASSETCLASSALT_KEY = 5`. Target field updated in active SQL on PRO.CUSTOMERCAL.`; `Threshold or filter literal used in active predicate `FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL`. Target field updated in active SQL on PRO.AccountCal.` |
| 'LOS' | Literal used in active SQL: `'LOS'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6`.`; `Literal value used in active statement `UPDATE PRO.AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HI…` |
| 6 | Literal used in active SQL: `6`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `SYSASSETCLASSALT_KEY = 6`. Target field updated in active SQL on PRO.CUSTOMERCAL.`; `Literal value used in active statement `UPDATE PRO.AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HI…` |
| FINALASSETCLASSALT_KEY | Source field read in active SQL on PRO.AccountCal, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNTCAL, PRO.ACCOUNT_MOVEMENT_HISTORY. Source field read in active SQL from PRO.AccountCal, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNTCAL, PRO.ACCOUNT_MOVEMENT_HISTORY. Also referenced in active predicate(s): `FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL`; `FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL` Referenced in active predicate(s): `FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL`; `FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL` |
| 'NO NEDD TO INSERT DATA' | Literal used in active SQL: `'NO NEDD TO INSERT DATA'`. Observed in active predicate(s): `Literal value used in active statement `UPDATE PRO.AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HI…` |
| PRO.ACCOUNT_MOVEMENT_HISTORY | Source field read in active SQL on PRO.AccountCal, PRO.ACCOUNT_MOVEMENT_HISTORY, #ACCOUNT_MOVEMENT_HISTORY, AA. Referenced in active predicate(s): `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO` |
| EFFECTIVEFROMTIMEKEY | Source field read in active SQL on PRO.AccountCal, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNTCAL, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY, AA. Source field read in active SQL from PRO.AccountCal, #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNTCAL, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY, AA. Also referenced in active predicate(s): `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO`; `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.` Referenced in active predicate(s): `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO`; `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.` |
| PRINT | Source field read in active SQL on PRO.AccountCal. Referenced in active predicate(s): `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO` |
| NO | Source field read in active SQL on PRO.AccountCal. Referenced in active predicate(s): `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO` |
| NEDD | Source field read in active SQL on PRO.AccountCal. Referenced in active predicate(s): `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO` |
| TO | Source field read in active SQL on PRO.AccountCal. Referenced in active predicate(s): `FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO` |
| LOS | Source field read in active SQL on PRO.AccountCal, PRO.CUSTOMERCAL. |
| DATA | Source field read in active SQL on PRO.AccountCal. |
| FinalNpaDt | Source field read in active SQL from #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNTCAL, PRO.ACCOUNT_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.` |
| EffectiveToTimeKey | Target field updated in active SQL on #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY, AA from `49999`. Source field read in active SQL on #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY, AA. Source field read in active SQL from #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY, AA. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `@vEffectiveto` Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `@vEffectiveto` |
| MovementFromStatus | Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.` |
| MovementToStatus | Source field read in active SQL on #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY, AA. Source field read in active SQL from #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY, AA. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey < @TIMEKEY AND EXISTS(SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY AS BB WHERE AA.CustomerAcID = BB.CustomerAcID AND BB.Effect…` Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey < @TIMEKEY AND EXISTS(SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY AS BB WHERE AA.CustomerAcID = BB.CustomerAcID AND BB.Effect…` |
| TotOsAcc | Referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Calculated field `TotOsAcc` is defined by `ISNULL(Balance,0)`.` |
| MovementFromDate | Source field read in active SQL from #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.` |
| MovementToDate | Target field updated in active SQL on #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY, AA from `DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE`. Source field read in active SQL from #ACCOUNT_MOVEMENT_HISTORY, PRO.ACCOUNT_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, PRO.CUSTOMER_MOVEMENT_HISTORY, AA. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #ACCOUNT_MOVEMENT_HISTORY.`; `DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE` |
| SMA_CLASS AS MovementFromStatus | Source field read in active SQL from PRO.ACCOUNTCAL. |
| SMA_CLASS AS MovementToStatus | Source field read in active SQL from PRO.ACCOUNTCAL. |
| @ProcessDate AS MovementFromDate | Declared parameter. Used in active operations: read |
| 49999 | Literal used in active SQL: `49999`. Observed in active predicate(s): `Literal value used in active statement `SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS Eff…`; `Literal value used in active statement `SELECT A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey…` |
| '2086-11-21' | Literal used in active SQL: `'2086-11-21'`. Observed in active predicate(s): `Literal value used in active statement `SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, 49999 AS Eff…`; `Literal value used in active statement `SELECT UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, 49999 AS Effect…` |
| STD | Source field read in active SQL on PRO.CUSTOMERCAL, PRO.AccountCal. |
| SUB | Source field read in active SQL on PRO.CUSTOMERCAL, PRO.AccountCal. |
| DB1 | Source field read in active SQL on PRO.CUSTOMERCAL, PRO.AccountCal. |
| DB2 | Source field read in active SQL on PRO.CUSTOMERCAL, PRO.AccountCal. |
| DB3 | Source field read in active SQL on PRO.CUSTOMERCAL, PRO.AccountCal. |
| @ProcessDate MovementFromDate | Declared parameter. Used in active operations: read |
| BB | Source field read in active SQL on PRO.ACCOUNT_MOVEMENT_HISTORY, #ACCOUNT_MOVEMENT_HISTORY, AA, PRO.CUSTOMER_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY. Referenced in active predicate(s): `AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToT…`; `AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerI…` |
| TABLES | Referenced in active predicate(s): |
| CustomerName | Source field read in active SQL from #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.CUSTOMER_MOVEMENT_HISTORY.` |
| SysNPA_Dt | Source field read in active SQL from #Customer_MOVEMENT_HISTORY, PRO.CustomerCal, PRO.CUSTOMER_MOVEMENT_HISTORY. Also referenced in active predicate(s): `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.CUSTOMER_MOVEMENT_HISTORY.` |
| totOsCust | Referenced in active predicate(s): `Inserted field populated in active INSERT into #Customer_MOVEMENT_HISTORY.`; `Inserted field populated in active INSERT into PRO.CUSTOMER_MOVEMENT_HISTORY.` |
| CustMoveDescription AS MovementFromStatus | Source field read in active SQL from PRO.CustomerCal. |
| CustMoveDescription AS MovementToStatus | Source field read in active SQL from PRO.CustomerCal. |
| AA | Source field read in active SQL on AA. |
| DATEADD | Source field read in active SQL on AA. |
| DD | Source field read in active SQL on AA. |
| LEFT | Source field read in active SQL on AA. |
| CUSTOMER_MOVEMENT_HISTORY | Source field read in active SQL on PRO.CUSTOMER_MOVEMENT_HISTORY, #Customer_MOVEMENT_HISTORY, AA. Referenced in active predicate(s): |
| RUNNINGPROCESSNAME | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. Referenced in active predicate(s): `RUNNINGPROCESSNAME = 'SMA_MARKING'`; `RUNNINGPROCESSNAME='SMA_MARKING'` |
| SMA_MARKING | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. Referenced in active predicate(s): `RUNNINGPROCESSNAME='SMA_MARKING'` |
| COMPLETED | Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS from `'Y'`. |
| ERRORDATE | Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS from `NULL`. |
| ERRORDESCRIPTION | Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS from `NULL`. |
| COUNT | Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS from `ISNULL(COUNT,0)+1`. |
| 'SMA_MARKING' | Literal used in active SQL: `'SMA_MARKING'`. Observed in active predicate(s): `Threshold or filter literal used in active predicate `RUNNINGPROCESSNAME = 'SMA_MARKING'`. Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS.`; `Threshold or filter literal used in active predicate `RUNNINGPROCESSNAME='SMA_MARKING'`. Target field updated in active SQL on PRO.ACLRUNNINGPROCESSSTATUS.` |
| PRO.ACLRUNNINGPROCESSSTATUS | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. |
| 'N' | Literal used in active SQL: `'N'`. Observed in active predicate(s): `Flag literal used in active update on PRO.ACLRUNNINGPROCESSSTATUS for COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT.` |
| N | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. |
| GETDATE | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. |
| ERROR_MESSAGE | Source field read in active SQL on PRO.ACLRUNNINGPROCESSSTATUS. |

# Business Rules

## Rule: An account has a DPD_IntService value less than zero

**Applies to:** `DPD_IntService`
**Business meaning:** Set the account's DPD_IntService to zero

### Eligibility
- An account has a DPD_IntService value less than zero

### Decision Logic
| Condition | Outcome |
|---|---|
| An account has a DPD_IntService value less than zero | Set the account's DPD_IntService to zero |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #1).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account has a DPD_NoCredit value less than zero

**Applies to:** `DPD_NoCredit`
**Business meaning:** Set the account's DPD_NoCredit to zero

### Eligibility
- An account has a DPD_NoCredit value less than zero

### Decision Logic
| Condition | Outcome |
|---|---|
| An account has a DPD_NoCredit value less than zero | Set the account's DPD_NoCredit to zero |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #2).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account has a DPD_Overdrawn value less than zero

**Applies to:** `DPD_Overdrawn`
**Business meaning:** Set the account's DPD_Overdrawn to zero

### Eligibility
- An account has a DPD_Overdrawn value less than zero

### Decision Logic
| Condition | Outcome |
|---|---|
| An account has a DPD_Overdrawn value less than zero | Set the account's DPD_Overdrawn to zero |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #3).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account has a DPD_Overdue value less than zero

**Applies to:** `DPD_Overdue`
**Business meaning:** Set the account's DPD_Overdue to zero

### Eligibility
- An account has a DPD_Overdue value less than zero

### Decision Logic
| Condition | Outcome |
|---|---|
| An account has a DPD_Overdue value less than zero | Set the account's DPD_Overdue to zero |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #4).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account has a DPD_Renewal value less than zero

**Applies to:** `DPD_Renewal`
**Business meaning:** Set the account's DPD_Renewal to zero

### Eligibility
- An account has a DPD_Renewal value less than zero

### Decision Logic
| Condition | Outcome |
|---|---|
| An account has a DPD_Renewal value less than zero | Set the account's DPD_Renewal to zero |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #5).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account has a DPD_StockStmt value less than zero

**Applies to:** `DPD_StockStmt`
**Business meaning:** Set the account's DPD_StockStmt to zero

### Eligibility
- An account has a DPD_StockStmt value less than zero

### Decision Logic
| Condition | Outcome |
|---|---|
| An account has a DPD_StockStmt value less than zero | Set the account's DPD_StockStmt to zero |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #6).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: For each account, calculate the maximum value among DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt

**Applies to:** `DPD_Max`
**Business meaning:** Set the account's DPD_Max to the highest of these DPD values

### Eligibility
- For each account, calculate the maximum value among DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt

### Decision Logic
| Condition | Outcome |
|---|---|
| For each account, calculate the maximum value among DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt | Set the account's DPD_Max to the highest of these DPD values |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #7).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account is eligible for SMA marking (not already processed, standard asset class, positive balance, not always standard, and has DPD_Overdrawn or DPD_Overdue >= 0, and DPD_Max > 0)

**Applies to:** `SMA_CLASS`
**Business meaning:** Assign the account's SMA_CLASS based on DPD_Max: 'SMA_0' for 1-30 days, 'SMA_1' for 31-60 days, 'SMA_2' for 61 days or more

### Eligibility
- An account is eligible for SMA marking (not already processed, standard asset class, positive balance, not always standard, and has DPD_Overdrawn or DPD_Overdue >= 0, and DPD_Max > 0)

### Decision Logic
| Condition | Outcome |
|---|---|
| An account is eligible for SMA marking (not already processed, standard asset class, positive balance, not always standard, and has DPD_Overdrawn or DPD_Overdue >= 0, and DPD_Max > 0) | Assign the account's SMA_CLASS based on DPD_Max: 'SMA_0' for 1-30 days, 'SMA_1' for 31-60 days, 'SMA_2' for 61 days or more |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #8).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account is assigned an SMA_CLASS due to DPD criteria

**Applies to:** `SMA_REASON`
**Business meaning:** Set the account's SMA_REASON to indicate the specific reason for downgrade, such as 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', or 'DEGRADE BY REVIEW DUE DATE', depending on which DPD metric matches DPD_Max and the facility type

### Eligibility
- An account is assigned an SMA_CLASS due to DPD criteria

### Decision Logic
| Condition | Outcome |
|---|---|
| An account is assigned an SMA_CLASS due to DPD criteria | Set the account's SMA_REASON to indicate the specific reason for downgrade, such as 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', or 'DEGRADE BY REVIEW DUE DATE', depending on which DPD metric matches DPD_Max and the facility type |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #9).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account is assigned an SMA_CLASS

**Applies to:** `SMA_DT`
**Business meaning:** Set the account's SMA_DT to the date corresponding to the start of the DPD period (processing date minus DPD_Max plus one)

### Eligibility
- An account is assigned an SMA_CLASS

### Decision Logic
| Condition | Outcome |
|---|---|
| An account is assigned an SMA_CLASS | Set the account's SMA_DT to the date corresponding to the start of the DPD period (processing date minus DPD_Max plus one) |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #10).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account is assigned an SMA_CLASS

**Applies to:** `FLGSMA`
**Business meaning:** Set the account's FLGSMA to 'Y' to indicate it is flagged as an SMA account

### Eligibility
- An account is assigned an SMA_CLASS

### Decision Logic
| Condition | Outcome |
|---|---|
| An account is assigned an SMA_CLASS | Set the account's FLGSMA to 'Y' to indicate it is flagged as an SMA account |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #11).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer has at least one linked account flagged as SMA (FLGSMA='Y')

**Applies to:** `FLGSMA`
**Business meaning:** Set the customer's FLGSMA to 'Y'

### Eligibility
- A customer has at least one linked account flagged as SMA (FLGSMA='Y')

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer has at least one linked account flagged as SMA (FLGSMA='Y') | Set the customer's FLGSMA to 'Y' |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #12).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer is flagged as SMA (FLGSMA='Y')

**Applies to:** `SMA_CLASS_KEY, SMA_DT`
**Business meaning:** Update the customer's SMA_CLASS_KEY to the highest SMA class among their accounts and set SMA_DT to the earliest SMA date among those accounts

### Eligibility
- A customer is flagged as SMA (FLGSMA='Y')

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer is flagged as SMA (FLGSMA='Y') | Update the customer's SMA_CLASS_KEY to the highest SMA class among their accounts and set SMA_DT to the earliest SMA date among those accounts |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #13).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer is flagged as SMA (FLGSMA='Y') at the UCIF level

**Applies to:** `SMA_CLASS_KEY, SMA_DT`
**Business meaning:** Update the customer's SMA_CLASS_KEY and SMA_DT at the UCIF level to reflect the highest SMA class and earliest SMA date among all linked accounts

### Eligibility
- A customer is flagged as SMA (FLGSMA='Y') at the UCIF level

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer is flagged as SMA (FLGSMA='Y') at the UCIF level | Update the customer's SMA_CLASS_KEY and SMA_DT at the UCIF level to reflect the highest SMA class and earliest SMA date among all linked accounts |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #14).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer's asset class or SMA class changes

**Applies to:** `TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS`
**Business meaning:** Record the previous and current SMA status for the account in the SMA movement history table, including the time key

### Eligibility
- A customer's asset class or SMA class changes

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer's asset class or SMA class changes | Record the previous and current SMA status for the account in the SMA movement history table, including the time key |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #15).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer's asset class or SMA class changes at the customer level

**Applies to:** `EffectiveToTimeKey, MovementToDate`
**Business meaning:** Record the previous and current status in the customer movement history table, updating effective dates as needed

### Eligibility
- A customer's asset class or SMA class changes at the customer level

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer's asset class or SMA class changes at the customer level | Record the previous and current status in the customer movement history table, updating effective dates as needed |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #16).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer's asset class or SMA class changes at the account level

**Applies to:** `EffectiveToTimeKey, MovementToDate`
**Business meaning:** Record the previous and current status in the account movement history table, updating effective dates as needed

### Eligibility
- A customer's asset class or SMA class changes at the account level

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer's asset class or SMA class changes at the account level | Record the previous and current status in the account movement history table, updating effective dates as needed |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #17).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer's asset class key matches a specific value (1-6)

**Applies to:** `CustMoveDescription`
**Business meaning:** Set the customer's movement description to the corresponding asset class label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS')

### Eligibility
- A customer's asset class key matches a specific value (1-6)

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer's asset class key matches a specific value (1-6) | Set the customer's movement description to the corresponding asset class label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #18).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer's SMA_CLASS_KEY matches a specific value (1-3)

**Applies to:** `CustMoveDescription`
**Business meaning:** Set the customer's movement description to the corresponding SMA class label ('SMA_0', 'SMA_1', 'SMA_2')

### Eligibility
- A customer's SMA_CLASS_KEY matches a specific value (1-3)

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer's SMA_CLASS_KEY matches a specific value (1-3) | Set the customer's movement description to the corresponding SMA class label ('SMA_0', 'SMA_1', 'SMA_2') |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #19).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account's FinalAssetClassAlt_Key matches a specific value (1-6) and SMA_CLASS is NULL

**Applies to:** `SMA_CLASS`
**Business meaning:** Set the account's SMA_CLASS to the corresponding asset class label ('STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS')

### Eligibility
- An account's FinalAssetClassAlt_Key matches a specific value (1-6) and SMA_CLASS is NULL

### Decision Logic
| Condition | Outcome |
|---|---|
| An account's FinalAssetClassAlt_Key matches a specific value (1-6) and SMA_CLASS is NULL | Set the account's SMA_CLASS to the corresponding asset class label ('STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #20).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The process completes successfully

**Applies to:** `COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT`
**Business meaning:** Set the process status to completed, clear any error details, and increment the process count

### Eligibility
- The process completes successfully

### Decision Logic
| Condition | Outcome |
|---|---|
| The process completes successfully | Set the process status to completed, clear any error details, and increment the process count |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #21).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The process encounters an error

**Applies to:** `COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT`
**Business meaning:** Set the process status to not completed, record the error date and error description, and increment the process count

### Eligibility
- The process encounters an error

### Decision Logic
| Condition | Outcome |
|---|---|
| The process encounters an error | Set the process status to not completed, record the error date and error description, and increment the process count |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #22).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

# Business Rule Summary

| Rule | Output | Business Purpose |
|---|---|---|
| An account has a DPD_IntService value less than zero | `DPD_IntService` | Set the account's DPD_IntService to zero |
| An account has a DPD_NoCredit value less than zero | `DPD_NoCredit` | Set the account's DPD_NoCredit to zero |
| An account has a DPD_Overdrawn value less than zero | `DPD_Overdrawn` | Set the account's DPD_Overdrawn to zero |
| An account has a DPD_Overdue value less than zero | `DPD_Overdue` | Set the account's DPD_Overdue to zero |
| An account has a DPD_Renewal value less than zero | `DPD_Renewal` | Set the account's DPD_Renewal to zero |
| An account has a DPD_StockStmt value less than zero | `DPD_StockStmt` | Set the account's DPD_StockStmt to zero |
| For each account, calculate the maximum value among DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt | `DPD_Max` | Set the account's DPD_Max to the highest of these DPD values |
| An account is eligible for SMA marking (not already processed, standard asset class, positive balance, not always standard, and has DPD_Overdrawn or DPD_Overdue >= 0, and DPD_Max > 0) | `SMA_CLASS` | Assign the account's SMA_CLASS based on DPD_Max: 'SMA_0' for 1-30 days, 'SMA_1' for 31-60 days, 'SMA_2' for 61 days or more |
| An account is assigned an SMA_CLASS due to DPD criteria | `SMA_REASON` | Set the account's SMA_REASON to indicate the specific reason for downgrade, such as 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', 'DEGRADE BY CONTI EXCESS', 'DEGRADE BY STOCK STATEMENT', or 'DEGRADE BY REVIEW DUE DATE', depending on which DPD metric matches DPD_Max and the facility type |
| An account is assigned an SMA_CLASS | `SMA_DT` | Set the account's SMA_DT to the date corresponding to the start of the DPD period (processing date minus DPD_Max plus one) |
| An account is assigned an SMA_CLASS | `FLGSMA` | Set the account's FLGSMA to 'Y' to indicate it is flagged as an SMA account |
| A customer has at least one linked account flagged as SMA (FLGSMA='Y') | `FLGSMA` | Set the customer's FLGSMA to 'Y' |
| A customer is flagged as SMA (FLGSMA='Y') | `SMA_CLASS_KEY, SMA_DT` | Update the customer's SMA_CLASS_KEY to the highest SMA class among their accounts and set SMA_DT to the earliest SMA date among those accounts |
| A customer is flagged as SMA (FLGSMA='Y') at the UCIF level | `SMA_CLASS_KEY, SMA_DT` | Update the customer's SMA_CLASS_KEY and SMA_DT at the UCIF level to reflect the highest SMA class and earliest SMA date among all linked accounts |
| A customer's asset class or SMA class changes | `TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS` | Record the previous and current SMA status for the account in the SMA movement history table, including the time key |
| A customer's asset class or SMA class changes at the customer level | `EffectiveToTimeKey, MovementToDate` | Record the previous and current status in the customer movement history table, updating effective dates as needed |
| A customer's asset class or SMA class changes at the account level | `EffectiveToTimeKey, MovementToDate` | Record the previous and current status in the account movement history table, updating effective dates as needed |
| A customer's asset class key matches a specific value (1-6) | `CustMoveDescription` | Set the customer's movement description to the corresponding asset class label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') |
| A customer's SMA_CLASS_KEY matches a specific value (1-3) | `CustMoveDescription` | Set the customer's movement description to the corresponding SMA class label ('SMA_0', 'SMA_1', 'SMA_2') |
| An account's FinalAssetClassAlt_Key matches a specific value (1-6) and SMA_CLASS is NULL | `SMA_CLASS` | Set the account's SMA_CLASS to the corresponding asset class label ('STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') |
| The process completes successfully | `COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT` | Set the process status to completed, clear any error details, and increment the process count |
| The process encounters an error | `COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT` | Set the process status to not completed, record the error date and error description, and increment the process count |

# Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|
| 1 | An account has a DPD_IntService value less than zero | UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0 | 01_nested_block:nested_block | tables_written[0]: 01_nested_block:chunk_text_04 | `#DPD` | UPDATE | target: DPD_IntService | source: N/A | WHERE: COALESCE(DPD_IntService, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_04 | parse=parsed; tables_written[8]: 01_nested_block:embedded_01_14 | `#DPD` | UPDATE | target: DPD_IntService | source: isnull | WHERE: isnull(DPD_IntService,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_14 | parse=regex_fallback | Verified |
| 2 | An account has a DPD_NoCredit value less than zero | UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0 | 01_nested_block:nested_block | tables_written[1]: 01_nested_block:chunk_text_05 | `#DPD` | UPDATE | target: DPD_NoCredit | source: N/A | WHERE: COALESCE(DPD_NoCredit, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_05 | parse=parsed; tables_written[9]: 01_nested_block:embedded_01_15 | `#DPD` | UPDATE | target: DPD_NoCredit | source: isnull | WHERE: isnull(DPD_NoCredit,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_15 | parse=regex_fallback | Verified |
| 3 | An account has a DPD_Overdrawn value less than zero | UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0 | 01_nested_block:nested_block | tables_written[2]: 01_nested_block:chunk_text_06 | `#DPD` | UPDATE | target: DPD_Overdrawn | source: N/A | WHERE: COALESCE(DPD_Overdrawn, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_06 | parse=parsed; tables_written[10]: 01_nested_block:embedded_01_16 | `#DPD` | UPDATE | target: DPD_Overdrawn | source: isnull | WHERE: isnull(DPD_Overdrawn,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_16 | parse=regex_fallback | Verified |
| 4 | An account has a DPD_Overdue value less than zero | UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0 | 01_nested_block:nested_block | tables_written[3]: 01_nested_block:chunk_text_07 | `#DPD` | UPDATE | target: DPD_Overdue | source: N/A | WHERE: COALESCE(DPD_Overdue, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_07 | parse=parsed; tables_written[11]: 01_nested_block:embedded_01_17 | `#DPD` | UPDATE | target: DPD_Overdue | source: isnull | WHERE: isnull(DPD_Overdue,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_17 | parse=regex_fallback | Verified |
| 5 | An account has a DPD_Renewal value less than zero | UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0 | 01_nested_block:nested_block | tables_written[4]: 01_nested_block:chunk_text_08 | `#DPD` | UPDATE | target: DPD_Renewal | source: N/A | WHERE: COALESCE(DPD_Renewal, 0) < 0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_08 | parse=parsed; tables_written[12]: 01_nested_block:embedded_01_18 | `#DPD` | UPDATE | target: DPD_Renewal | source: isnull | WHERE: isnull(DPD_Renewal,0)<0 | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:embedded_01_18 | parse=regex_fallback | Verified |
| 6 | An account has a DPD_StockStmt value less than zero | UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0 | 01_nested_block:nested_block | tables_written[5]: 01_nested_block:chunk_text_09 | `#DPD` | UPDATE | target: DPD_StockStmt | source: isnull, IF, OBJECT_ID, TEMPDB, IS, DROP, TABLE | WHERE: isnull(DPD_StockStmt,0)<0 IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL DROP TABLE #TEMPTABLE | JOIN: None | EXISTS: None | HAVING: None | constants: 0, 'TEMPDB..#TEMPTABLE' | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_09 | parse=regex_fallback | Verified |
| 7 | For each account, calculate the maximum value among DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt | UPDATE   A SET A.DPD_Max= (CASE ... | 01_nested_block:nested_block | tables_written[7]: 01_nested_block:chunk_text_12 | `A` | UPDATE | target: A.DPD_Max | source: A, isnull, A.DPD_IntService, A.DPD_NoCredit, A.DPD_Overdrawn, A.DPD_Overdue, A.DPD_Renewal, A.DPD_StockStmt | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: 0 | provenance: 01_nested_block:nested_block | 01_nested_block:chunk_text_12 | parse=regex_fallback | Verified |
| 8 | An account is eligible for SMA marking (not already processed, standard asset class, positive balance, not always standard, and has DPD_Overdrawn or DPD_Overdue >= 0, and DPD_Max > 0) | UPDATE A SET A.SMA_CLASS=  (CASE  WHEN dpd.DPD_Max  BETWEEN 1 AND 30  THEN 'SMA_0' ... | 01_nested_block_1:nested_block | tables_written[15]: 01_nested_block_1:chunk_text_02 | `A` | UPDATE | target: A.SMA_CLASS | source: A, dpd.DPD_Max, BETWEEN, SMA_0, SMA_1, SMA_2 | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: 1, 30, 'SMA_0', 31, 60, 'SMA_1', 61, 90, 'SMA_2' | provenance: 01_nested_block_1:nested_block | 01_nested_block_1:chunk_text_02 | parse=regex_fallback | Verified |
| 9 | An account is assigned an SMA_CLASS due to DPD criteria | A.SMA_REASON= (CASE ... | 01_nested_block_1:nested_block | calculations[8]: metric not specified | explanation not specified | Verified |
| 10 | An account is assigned an SMA_CLASS | A.SMA_DT=   DATEADD(DAY, -dpd.DPD_MAX+1 ,@ProcessDate) | 01_nested_block_1:nested_block | calculations[9]: metric not specified | explanation not specified | Verified |
| 11 | An account is assigned an SMA_CLASS | A.FLGSMA='Y' | 01_nested_block_2:nested_block | conditions[13]: B.FLGSMA='Y' -> UPDATE A SET A.FLGSMA='Y' FROM PRO.CUSTOMERCAL A INNER JOIN PRO.ACCOUNTCAL B ON A.CustomerEntityID =B.CustomerEntityID; conditions[15]: A.FLGSMA='Y' -> UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM PRO.CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID; conditions[16]: B.FLGSMA='Y' -> UPDATE A SET A.FLGSMA='Y' FROM PRO.CUSTOMERCAL A INNER JOIN PRO.ACCOUNTCAL B ON A.UCIF_ID =B.UCIF_ID; conditions[18]: A.FLGSMA='Y' -> UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM PRO.CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID; tables_read[11]: 01_nested_block_2:chunk_text_04 | `#TEMPTABLE_SMACLASS` | target: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | source: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | WHERE: A.FLGSMA = 'Y' | JOIN: INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_04 | parse=parsed; tables_read[15]: 01_nested_block_2:chunk_text_07 | `PRO.SMA_MOVEMENT_HISTORY` | target: 1 | source: 1 | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 1 | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_07 | parse=regex_fallback; tables_read[16]: 01_nested_block_2:chunk_text_09 | `#SMACLASS` | target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | source: A.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS_KEY, A.FLGSMA, A.REFCUSTOMERID, B.REFCUSTOMERID, A.CUSTOMERENTITYID, B.CUSTOMERENTITYID, B.FLGSMA, B.SYSASSETCLASSALT_KEY, A.BALANCE | WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1 | JOIN: INNER PRO.CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' | EXISTS: None | HAVING: None | constants: 'SMA_0', 'SMA_1', 'SMA_2', 'Y', 1, 0 | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_09 | parse=parsed; tables_read[17]: 01_nested_block_2:chunk_text_09 | `PRO.ACCOUNTCAL` | target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | source: A.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS_KEY, A.FLGSMA, A.REFCUSTOMERID, B.REFCUSTOMERID, A.CUSTOMERENTITYID, B.CUSTOMERENTITYID, B.FLGSMA, B.SYSASSETCLASSALT_KEY, A.BALANCE | WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1 | JOIN: INNER PRO.CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' | EXISTS: None | HAVING: None | constants: 'SMA_0', 'SMA_1', 'SMA_2', 'Y', 1, 0 | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_09 | parse=parsed; tables_read[18]: 01_nested_block_2:chunk_text_09 | `PRO.CUSTOMERCAL` | target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS | source: A.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS_KEY, A.FLGSMA, A.REFCUSTOMERID, B.REFCUSTOMERID, A.CUSTOMERENTITYID, B.CUSTOMERENTITYID, B.FLGSMA, B.SYSASSETCLASSALT_KEY, A.BALANCE | WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1 | JOIN: INNER PRO.CUSTOMERCAL ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y' | EXISTS: None | HAVING: None | constants: 'SMA_0', 'SMA_1', 'SMA_2', 'Y', 1, 0 | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_09 | parse=parsed; tables_read[23]: 01_nested_block_2:embedded_01_21 | `PRO.ACCOUNTCAL` | target: A.CustomerAcID, ISNULL(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2'))  SMA_CLASS INTO #SMACLASS | source: A.CustomerAcID, ISNULL(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2'))  SMA_CLASS INTO #SMACLASS | WHERE: B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_0', 'SMA_1', 'SMA_2', 'Y', 0, 1 | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:embedded_01_21 | parse=regex_fallback; tables_written[18]: 01_nested_block_2:chunk_text_02 | `A` | UPDATE | target: A.FLGSMA | source: A, Y, PRO.CUSTOMERCAL, INNER, JOIN, PRO.ACCOUNTCAL, B, A.CustomerEntityID, B.CustomerEntityID, B.FLGSMA, IF, OBJECT_ID, TEMPDB, IS, DROP, TABLE | WHERE: B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 'TEMPDB..#TEMPTABLE_SMACLASS' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_02 | parse=regex_fallback; tables_written[19]: 01_nested_block_2:chunk_text_04 | `PRO.CUSTOMERCAL` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | WHERE: A.FLGSMA = 'Y' | JOIN: INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_04 | parse=parsed; tables_written[20]: 01_nested_block_2:chunk_text_05 | `A` | UPDATE | target: A.FLGSMA | source: A, Y, PRO.CUSTOMERCAL, INNER, JOIN, PRO.ACCOUNTCAL, B, A.UCIF_ID, B.UCIF_ID, B.FLGSMA, IF, OBJECT_ID, TEMPDB, IS, DROP, TABLE | WHERE: B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASSUcif | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 'TEMPDB..#TEMPTABLE_SMACLASSUcif' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_05 | parse=regex_fallback; tables_written[21]: 01_nested_block_2:chunk_text_07 | `A` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: A, B.MAXSMA_CLASS, B.SMA_Dt, PRO.CUSTOMERCAL, INNER, JOIN, B, A.UCIF_ID, B.UCIF_ID, A.FLGSMA, Y, IF, PRO.SMA_MOVEMENT_HISTORY, TIMEKEY | WHERE: A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 1 | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_07 | parse=regex_fallback; tables_written[26]: 01_nested_block_2:embedded_01_16 | `A` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: A, B.MAXSMA_CLASS, B.SMA_Dt, PRO.CUSTOMERCAL, INNER, JOIN, B, A.CustomerEntityID, B.CustomerEntityID, A.FLGSMA, Y | WHERE: A.FLGSMA='Y' | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:embedded_01_16 | parse=regex_fallback | Verified |
| 12 | A customer has at least one linked account flagged as SMA (FLGSMA='Y') | UPDATE A SET A.FLGSMA='Y' FROM PRO.CUSTOMERCAL A INNER JOIN PRO.ACCOUNTCAL B ON A.CustomerEntityID =B.CustomerEntityID WHERE B.FLGSMA='Y' | 01_nested_block_2:nested_block | tables_written[18]: 01_nested_block_2:chunk_text_02 | `A` | UPDATE | target: A.FLGSMA | source: A, Y, PRO.CUSTOMERCAL, INNER, JOIN, PRO.ACCOUNTCAL, B, A.CustomerEntityID, B.CustomerEntityID, B.FLGSMA, IF, OBJECT_ID, TEMPDB, IS, DROP, TABLE | WHERE: B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 'TEMPDB..#TEMPTABLE_SMACLASS' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_02 | parse=regex_fallback | Verified |
| 13 | A customer is flagged as SMA (FLGSMA='Y') | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM PRO.CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID WHERE A.FLGSMA='Y' | 01_nested_block_2:nested_block | tables_read[11]: 01_nested_block_2:chunk_text_04 | `#TEMPTABLE_SMACLASS` | target: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | source: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | WHERE: A.FLGSMA = 'Y' | JOIN: INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_04 | parse=parsed; tables_written[19]: 01_nested_block_2:chunk_text_04 | `PRO.CUSTOMERCAL` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID | WHERE: A.FLGSMA = 'Y' | JOIN: INNER TEMPTABLE_SMACLASS ON A.CustomerEntityID = B.CustomerEntityID | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_04 | parse=parsed; tables_written[26]: 01_nested_block_2:embedded_01_16 | `A` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: A, B.MAXSMA_CLASS, B.SMA_Dt, PRO.CUSTOMERCAL, INNER, JOIN, B, A.CustomerEntityID, B.CustomerEntityID, A.FLGSMA, Y | WHERE: A.FLGSMA='Y' | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y' | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:embedded_01_16 | parse=regex_fallback | Verified |
| 14 | A customer is flagged as SMA (FLGSMA='Y') at the UCIF level | UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM PRO.CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID WHERE A.FLGSMA='Y' | 01_nested_block_2:nested_block | tables_read[15]: 01_nested_block_2:chunk_text_07 | `PRO.SMA_MOVEMENT_HISTORY` | target: 1 | source: 1 | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 1 | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_07 | parse=regex_fallback; tables_written[21]: 01_nested_block_2:chunk_text_07 | `A` | UPDATE | target: A.SMA_CLASS_KEY, A.SMA_DT | source: A, B.MAXSMA_CLASS, B.SMA_Dt, PRO.CUSTOMERCAL, INNER, JOIN, B, A.UCIF_ID, B.UCIF_ID, A.FLGSMA, Y, IF, PRO.SMA_MOVEMENT_HISTORY, TIMEKEY | WHERE: A.FLGSMA='Y' IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY) BEGIN | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 1 | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_07 | parse=regex_fallback | Verified |
| 15 | A customer's asset class or SMA class changes | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) | 01_nested_block_2:nested_block | tables_written[24]: 01_nested_block_2:chunk_text_11 | `PRO.SMA_MOVEMENT_HISTORY` | INSERT | target: TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS | source: N/A | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: None | provenance: 01_nested_block_2:nested_block | 01_nested_block_2:chunk_text_11 | parse=parsed | Verified |
| 16 | A customer's asset class or SMA class changes at the customer level | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto, MovementToDate=DATEADD(DD,-1,@ProcessDate) FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA ... | 01_nested_block_5:nested_block; 01_nested_block_4:nested_block | conditions[27]: (CASE WHEN  B.SourceSystemCustomerID IS NULL THEN 1  WHEN B.SourceSystemCustomerID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 -> UPDATE AA SET EffectiveToTimeKey = @vEffectiveto, MovementToDate=DATEADD(DD,-1,@ProcessDate) FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA LEFT JOIN #Customer_MOVEMENT_HISTORY B ON  AA.SourceSystemCustomerID=B.SourceSystemCustomerID AND B.EffectiveToTimeKey =49999 WHERE AA.EffectiveToTimeKey = 49999 and B.SourceSystemCustomerID is null; conditions[28]: AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) -> UPDATE AA SET EffectiveToTimeKey = @vEffectiveto, MovementToDate=DATEADD(DD,-1,@ProcessDate) FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA; calculations[15]: metric not specified | explanation not specified; calculations[18]: metric not specified | explanation not specified | Verified |
| 17 | A customer's asset class or SMA class changes at the account level | UPDATE AA SET EffectiveToTimeKey = @vEffectiveto, MovementToDate=DATEADD(DD,-1,@ProcessDate) FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA ... | 01_nested_block_4:nested_block; 01_nested_block_5:nested_block | calculations[15]: metric not specified | explanation not specified; calculations[18]: metric not specified | explanation not specified | Verified |
| 18 | A customer's asset class key matches a specific value (1-6) | UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6 | 01_nested_block_3:nested_block | tables_written[29]: 01_nested_block_3:chunk_text_03 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'STD', 1 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_03 | parse=parsed; tables_written[45]: 01_nested_block_3:embedded_01_23 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: PRO.CUSTOMERCAL, STD, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'STD', 1 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_23 | parse=regex_fallback; tables_written[30]: 01_nested_block_3:chunk_text_04 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 2 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SUB', 2 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_04 | parse=parsed; tables_written[46]: 01_nested_block_3:embedded_01_24 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: PRO.CUSTOMERCAL, SUB, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=2 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SUB', 2 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_24 | parse=regex_fallback; tables_written[31]: 01_nested_block_3:chunk_text_05 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 3 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB1', 3 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_05 | parse=parsed; tables_written[47]: 01_nested_block_3:embedded_01_25 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: PRO.CUSTOMERCAL, DB1, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=3 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB1', 3 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_25 | parse=regex_fallback; tables_written[32]: 01_nested_block_3:chunk_text_06 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 4 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB2', 4 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_06 | parse=parsed; tables_written[48]: 01_nested_block_3:embedded_01_26 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: PRO.CUSTOMERCAL, DB2, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=4 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB2', 4 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_26 | parse=regex_fallback; tables_written[33]: 01_nested_block_3:chunk_text_07 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 5 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB3', 5 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_07 | parse=parsed; tables_written[49]: 01_nested_block_3:embedded_01_27 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: PRO.CUSTOMERCAL, DB3, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=5 | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB3', 5 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_27 | parse=regex_fallback; tables_written[34]: 01_nested_block_3:chunk_text_08 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY = 6 | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_08 | parse=parsed; tables_written[50]: 01_nested_block_3:embedded_01_28 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: PRO.CUSTOMERCAL, LOS, SYSASSETCLASSALT_KEY | WHERE: SYSASSETCLASSALT_KEY=6 | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_28 | parse=regex_fallback | Verified |
| 19 | A customer's SMA_CLASS_KEY matches a specific value (1-3) | UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3 | 01_nested_block_3:nested_block | tables_written[35]: 01_nested_block_3:chunk_text_09 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY = 1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_0', 1 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_09 | parse=parsed; tables_written[51]: 01_nested_block_3:embedded_01_29 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: PRO.CUSTOMERCAL, SMA_0, SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY=1 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_0', 1 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_29 | parse=regex_fallback; tables_written[36]: 01_nested_block_3:chunk_text_10 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY = 2 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_1', 2 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_10 | parse=parsed; tables_written[52]: 01_nested_block_3:embedded_01_30 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: PRO.CUSTOMERCAL, SMA_1, SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY=2 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_1', 2 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_30 | parse=regex_fallback; tables_written[37]: 01_nested_block_3:chunk_text_11 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY = 3 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_2', 3 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_11 | parse=parsed; tables_written[53]: 01_nested_block_3:embedded_01_31 | `PRO.CUSTOMERCAL` | UPDATE | target: CustMoveDescription | source: PRO.CUSTOMERCAL, SMA_2, SMA_CLASS_KEY | WHERE: SMA_CLASS_KEY=3 | JOIN: None | EXISTS: None | HAVING: None | constants: 'SMA_2', 3 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_31 | parse=regex_fallback | Verified |
| 20 | An account's FinalAssetClassAlt_Key matches a specific value (1-6) and SMA_CLASS is NULL | UPDATE PRO.AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL; UPDATE PRO.AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL; UPDATE PRO.AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL; UPDATE PRO.AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL; UPDATE PRO.AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL; UPDATE PRO.AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL | 01_nested_block_3:nested_block | tables_written[38]: 01_nested_block_3:chunk_text_12 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'STD', 1, NULL | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_12 | parse=parsed; tables_written[54]: 01_nested_block_3:embedded_01_32 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: PRO.AccountCal, STD, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'STD', 1 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_32 | parse=regex_fallback; tables_written[39]: 01_nested_block_3:chunk_text_13 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'SUB', 2, NULL | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_13 | parse=parsed; tables_written[55]: 01_nested_block_3:embedded_01_33 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: PRO.AccountCal, SUB, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'SUB', 2 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_33 | parse=regex_fallback; tables_written[40]: 01_nested_block_3:chunk_text_14 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 3 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB1', 3, NULL | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_14 | parse=parsed; tables_written[56]: 01_nested_block_3:embedded_01_34 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: PRO.AccountCal, DB1, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB1', 3 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_34 | parse=regex_fallback; tables_written[41]: 01_nested_block_3:chunk_text_15 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB2', 4, NULL | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_15 | parse=parsed; tables_written[57]: 01_nested_block_3:embedded_01_35 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: PRO.AccountCal, DB2, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB2', 4 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_35 | parse=regex_fallback; tables_written[42]: 01_nested_block_3:chunk_text_16 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: FinalAssetClassAlt_Key | WHERE: FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB3', 5, NULL | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_16 | parse=parsed; tables_written[58]: 01_nested_block_3:embedded_01_36 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: PRO.AccountCal, DB3, FinalAssetClassAlt_Key, is | WHERE: FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL | JOIN: None | EXISTS: None | HAVING: None | constants: 'DB3', 5 | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:embedded_01_36 | parse=regex_fallback; tables_read[26]: 01_nested_block_3:chunk_text_17 | `PRO.ACCOUNT_MOVEMENT_HISTORY` | target: 1 | source: 1 | WHERE: None | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6, 1, 'NO NEDD TO INSERT DATA' | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_17 | parse=regex_fallback; tables_written[43]: 01_nested_block_3:chunk_text_17 | `PRO.AccountCal` | UPDATE | target: SMA_CLASS | source: PRO.AccountCal, LOS, FinalAssetClassAlt_Key, is, if, PRO.ACCOUNT_MOVEMENT_HISTORY, EffectiveFromTimeKey, print, NO, NEDD, TO, DATA | WHERE: FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO | JOIN: None | EXISTS: None | HAVING: None | constants: 'LOS', 6, 1, 'NO NEDD TO INSERT DATA' | provenance: 01_nested_block_3:nested_block | 01_nested_block_3:chunk_text_17 | parse=regex_fallback | Verified |
| 21 | The process completes successfully | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' | 01_nested_block_5:nested_block | tables_written[67]: 01_nested_block_5:chunk_text_03 | `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | target: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | source: RUNNINGPROCESSNAME | WHERE: RUNNINGPROCESSNAME = 'SMA_MARKING' | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', NULL, 1, 'SMA_MARKING', 0 | provenance: 01_nested_block_5:nested_block | 01_nested_block_5:chunk_text_03 | parse=parsed; tables_written[70]: 01_nested_block_5:embedded_01_06 | `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | target: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | source: PRO.ACLRUNNINGPROCESSSTATUS, Y, ISNULL, RUNNINGPROCESSNAME, SMA_MARKING | WHERE: RUNNINGPROCESSNAME='SMA_MARKING' | JOIN: None | EXISTS: None | HAVING: None | constants: 'Y', 0, 1, 'SMA_MARKING' | provenance: 01_nested_block_5:nested_block | 01_nested_block_5:embedded_01_06 | parse=regex_fallback; calculations[19]: metric not specified | explanation not specified | Verified |
| 22 | The process encounters an error | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 WHERE RUNNINGPROCESSNAME='SMA_MARKING' | 03_exception:exception; 01_nested_block_5:nested_block | tables_written[71]: 03_exception:chunk_text_01 | `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | target: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | source: RUNNINGPROCESSNAME | WHERE: RUNNINGPROCESSNAME = 'SMA_MARKING' | JOIN: None | EXISTS: None | HAVING: None | constants: 'N', 1, 'SMA_MARKING', 0 | provenance: 03_exception:exception | 03_exception:chunk_text_01 | parse=parsed; tables_written[72]: 03_exception:embedded_01_03 | `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | target: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | source: PRO.ACLRUNNINGPROCESSSTATUS, N, GETDATE, ERROR_MESSAGE, ISNULL, RUNNINGPROCESSNAME, SMA_MARKING | WHERE: RUNNINGPROCESSNAME='SMA_MARKING' | JOIN: None | EXISTS: None | HAVING: None | constants: 'N', 0, 1, 'SMA_MARKING' | provenance: 03_exception:exception | 03_exception:embedded_01_03 | parse=regex_fallback; calculations[19]: metric not specified | explanation not specified | Verified |

_Source evidence is the literal technical text carried through the pipeline; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails._
</details>

## Calculations / Formulas

- **DPD_IntService (in #TEMPTABLE):** If the account's DPD_IntService is greater than or equal to the reference period, use DPD_IntService; otherwise, use zero
- **DPD_NoCredit (in #TEMPTABLE):** If the account's DPD_NoCredit is greater than or equal to the reference period, use DPD_NoCredit; otherwise, use zero
- **DPD_Overdrawn (in #TEMPTABLE):** If the account's DPD_Overdrawn is greater than or equal to the reference period, use DPD_Overdrawn; otherwise, use zero
- **DPD_Overdue (in #TEMPTABLE):** If the account's DPD_Overdue is greater than or equal to the reference period, use DPD_Overdue; otherwise, use zero
- **DPD_Renewal (in #TEMPTABLE):** If the account's DPD_Renewal is greater than or equal to the reference period, use DPD_Renewal; otherwise, use zero
- **DPD_StockStmt (in #TEMPTABLE):** If the account's DPD_StockStmt is greater than or equal to the reference period, use DPD_StockStmt; otherwise, use zero
- **DPD_Max (in #DPD):** Set to the highest value among DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt
- **SMA_CLASS assignment:** Assign 'SMA_0' if DPD_Max is between 1 and 30, 'SMA_1' if between 31 and 60, 'SMA_2' if 61 or more
- **SMA_REASON assignment:** Assign a reason based on which DPD metric matches DPD_Max and the facility type
- **SMA_DT assignment:** Set to the processing date minus DPD_Max plus one
- **MAXSMA_CLASS:** Set to the highest numeric value among SMA_CLASS values for a customer (SMA_0=1, SMA_1=2, SMA_2=3)
- **SMA_Dt:** Set to the earliest SMA_Dt among a customer's accounts
- **SMA_CLASS (numeric mapping):** Map 'SMA_0' to 1, 'SMA_1' to 2, 'SMA_2' to 3
- **TotOsAcc:** Set to the account's balance, or zero if null
- **MovementToDate:** Set to one day before the processing date
- **TotOsCust:** Set to the customer's total outstanding, or zero if null
- **COUNT (process status):** Increment by one, or set to one if previously null

## Exception Handling Behavior

If an error occurs during processing, the system updates the process status to indicate failure, records the error date and error message, and increments the process count for audit and troubleshooting. Temporary tables are dropped as part of cleanup to prevent data inconsistencies.

## Rule Provenance Summary

**Technical Implementation:** derived directly from the parsed source code and the per-chunk technical extraction (conditions, table reads/writes, calculations) - see Tables Read/Written above.

**Business Interpretation:** the Purpose Summary, Step-by-Step Logic Flow, and Business Rules sections translate that technical implementation into plain business language; the breakdown below shows how much of that interpretation is a direct restatement versus an inference or an assumption.

- **Total business rules:** 22
- **By rule type:** explicit = 22
- **By validation status:** verified = 22

## Ambiguities / Needs Review

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID,  
RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNo...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.SMA_CLASS=NULL  
             ,A.SMA_REASON=NULL  
       ,A.SMA_DT=NULL  
       ,A.FLGSMA=NULL  
 F...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.FLGSMA=NULL  
             ,A.SMA_CLASS_KEY=NULL  
       ,A.SMA_DT=NULL  
     FROM PRO.CUSTOMERCAL A...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): INSERT INTO PRO.PREVSMASTATUS  
SELECT @TIMEKEY,CustomerAcID,SMA_CLASS  
FROM #SMACLASS  
  
--INSERT INTO PRO.ACCOU...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): SELECT   
                   A.UCIF_ID,  
     A.RefCustomerID,  
     A.SourceSystemCustomerID,  
     A.CustomerAc...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE AA  
SET   
  EffectiveToTimeKey = @vEffectiveto  
    ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE PRO.ACLRUNNINGPROCESSSTATUS   
SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNU...
- There is commented-out logic for updating movement dates using a calendar table, but this is not executed and does not affect the business process.
- Some code fragments reference conditional logic or temporary tables that are not fully tied to active business rules, but these do not impact the main SMA marking and movement tracking logic.
- A code fragment labeled 'TRY' is present without further context or logic, and does not affect the business process.
