## Object Overview

- **Object Name:** `UNKNOWN_OBJECT`
- **Object Type:** Procedure
- **SQL Dialect:** SQL Server T-SQL (detection confidence: high)
- **Parameters:** None

## Purpose Summary

This procedure determines and updates the Special Mention Account (SMA) classification and asset classification for loan and advance accounts and their related customers, in line with regulatory requirements such as RBI IRAC. It calculates Days Past Due (DPD) metrics, assigns SMA classes based on overdue status, records the reasons for SMA downgrades, and maintains historical movement records for both accounts and customers. The process ensures that overdue, non-performing, or otherwise irregular accounts are correctly tracked and reported for compliance and risk management purposes.

## Tables Read

| Table Name | Business Context | Filter Conditions | Confidence |
|---|---|---|---|
| `SYSDAYMATRIX` | Columns referenced: DATE | TIMEKEY=@TIMEKEY | high |
| `[dbo].Automate_Advances` | Columns referenced: Timekey | EXT_FLG='Y' | low |
| `PRO.AccountCal` | Columns referenced: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_Overdrawn, DPD_Overdue | isnull(A.DPD_Overdrawn,0)>30   OR  Isnull(A.DPD_Overdue,0)>0 | high |
| `#DPD` | Columns referenced: DPD_IntService, DPD_NoCredit, RefPeriodNoCredit, DPD_Overdrawn, RefPeriodOverDrawn, DPD_Overdue, RefPeriodOverdue, DPD_Renewal, RefPeriodReview, DPD_StockStmt, RefPeriodStkStatement, AccountEntityId | isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) | low |
| `#DPD` | Columns referenced: DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | isnull(A.DPD_Overdrawn,0)>0 OR Isnull(A.DPD_Overdue,0)>0 | low |
| `PRO.ACCOUNTCAL` | Columns referenced: CustomerEntityID, AccountEntityID, FACILITYTYPE, BALANCE, ASSET_NORM, FINALASSETCLASSALT_KEY | No filter / full read | high |
| `PRO.CUSTOMERCAL` | Columns referenced: CustomerEntityID, FLGPROCESSING | No filter / full read | high |
| `AdvAcBasicDetail` | Columns referenced: AccountEntityId, EffectiveFromTimeKey, EffectiveToTimeKey | (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY) | high |
| `#DPD` | Columns referenced: AccountEntityId, DPD_Max, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | No filter / full read | low |
| `PRO.SMA_MOVEMENT_HISTORY` | Columns referenced: TIMEKEY | TIMEKEY=@TIMEKEY | high |
| `PRO.PREVSMASTATUS` | Columns referenced: CustomerAcID, SMA_CLASS | No filter / full read | high |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: EffectiveFromTimeKey, CustomerAcID, EFFECTIVETOTimekey, MOVEMENTTOSTATUS | [EffectiveFromTimeKey]= @Timekey OR CustomerAcID=B.CustomerAcID AND B.EFFECTIVETOTimekey=49999 OR AA.EffectiveToTimeKey = 49999 OR AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY | high |
| `#ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | No filter / full read | low |
| `PRO.CustomerCal` | Columns referenced: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, CustMoveDescription, TotOsCust | No filter / full read | high |
| `#Customer_MOVEMENT_HISTORY` | Columns referenced: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | No filter / full read | low |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | Columns referenced: SourceSystemCustomerID, EFFECTIVETOTimekey, MovementTOStatus, MOVEMENTTOSTATUS, MOVEMENTFROMSTATUS | No filter / full read | high |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Columns referenced: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT, RUNNINGPROCESSNAME | RUNNINGPROCESSNAME='SMA_MARKING' | high |

## Tables Written

| Table Name | Operation Type | Columns Affected | Business Trigger | Confidence |
|---|---|---|---|---|
| `#DPD` | INSERT | AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_MAX | isnull(A.DPD_Overdrawn,0)>30   OR  Isnull(A.DPD_Overdue,0)>0 | low |
| `#DPD` | UPDATE | DPD_IntService | isnull(DPD_IntService,0)<0 | low |
| `#DPD` | UPDATE | DPD_NoCredit | isnull(DPD_NoCredit,0)<0 | low |
| `#DPD` | UPDATE | DPD_Overdrawn | isnull(DPD_Overdrawn,0)<0 | low |
| `#DPD` | UPDATE | DPD_Overdue | isnull(DPD_Overdue,0)<0 | low |
| `#DPD` | UPDATE | DPD_Renewal | isnull(DPD_Renewal,0)<0 | low |
| `#DPD` | UPDATE | DPD_StockStmt | isnull(DPD_StockStmt,0)<0 | low |
| `#TEMPTABLE` | INSERT | DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) | low |
| `#DPD` | UPDATE | DPD_Max | Always, on each execution | low |
| `#DPD` | UPDATE | DPD_Max | isnull(A.DPD_Overdrawn,0)>0 OR Isnull(A.DPD_Overdue,0)>0 | low |
| `PRO.ACCOUNTCAL` | UPDATE | SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | Always, on each execution | high |
| `PRO.ACCOUNTCAL` | UPDATE | SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 | high |
| `PRO.CUSTOMERCAL` | UPDATE | FLGSMA, SMA_CLASS_KEY, SMA_DT | Always, on each execution | high |
| `#TEMPTABLE_SMACLASS` | INSERT | CustomerEntityID, MAXSMA_CLASS, SMA_Dt | Always, on each execution | low |
| `PRO.CUSTOMERCAL` | UPDATE | SMA_CLASS_KEY, SMA_DT | A.FLGSMA='Y' | high |
| `PRO.CUSTOMERCAL` | UPDATE | FLGSMA | B.FLGSMA='Y' | high |
| `#TEMPTABLE_SMACLASSUcif` | INSERT | UCIF_ID, MAXSMA_CLASS, SMA_Dt | Always, on each execution | low |
| `PRO.SMA_MOVEMENT_HISTORY` | DELETE | Not identified | TIMEKEY=@TIMEKEY | high |
| `#SMACLASS` | INSERT | CustomerAcID, SMA_CLASS | Always, on each execution | low |
| `#SMACLASS` | UPDATE | SMA_CLASS | Always, on each execution | low |
| `PRO.SMA_MOVEMENT_HISTORY` | INSERT | TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS | B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') | high |
| `PRO.PREVSMASTATUS` | TRUNCATE | Not identified | Always, on each execution | high |
| `PRO.PREVSMASTATUS` | INSERT | TIMEKEY, CustomerAcID, SMA_CLASS | Always, on each execution | high |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=1 | high |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=2 | high |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=3 | high |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=4 | high |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=5 | high |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=6 | high |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SMA_CLASS_KEY=1 | high |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SMA_CLASS_KEY=2 | high |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SMA_CLASS_KEY=3 | high |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL | high |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL | high |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL | high |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL | high |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL | high |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL | high |
| `#ACCOUNT_MOVEMENT_HISTORY` | INSERT | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | Always, on each execution | low |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | INSERT | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | (CASE WHEN  B.CustomerAcID IS NULL THEN 1 WHEN B.CustomerAcID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 | high |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null | high |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) | high |
| `#Customer_MOVEMENT_HISTORY` | INSERT | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | Always, on each execution | low |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | INSERT | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | (CASE WHEN  B.SourceSystemCustomerID IS NULL THEN 1  WHEN B.SourceSystemCustomerID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 | high |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.SourceSystemCustomerID is null | high |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) | high |
| `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME='SMA_MARKING' | high |

## Step-by-Step Logic Flow

1. 1. Remove any existing temporary tables used for DPD and SMA calculations to ensure a clean processing environment.
2. 2. Identify accounts with significant overdue or overdrawn status and include them for DPD analysis.
3. 3. For each DPD metric (interest servicing, no credit, overdrawn, overdue, renewal, stock statement), ensure that negative values are reset to zero to maintain data integrity.
4. 4. For each account, compare current DPD metrics to reference periods and retain the value if it meets or exceeds the reference; otherwise, set it to zero.
5. 5. Calculate the maximum DPD value across all DPD metrics for each account to determine the most severe overdue indicator.
6. 6. Assign an SMA class to each account based on the maximum DPD value, following regulatory thresholds.
7. 7. Determine the reason for SMA downgrade based on the facility type and which DPD metric triggered the maximum value.
8. 8. Calculate the SMA date as the date corresponding to the start of the overdue period.
9. 9. Update account records with the calculated SMA class, reason, date, and flag indicating SMA status.
10. 10. For customers with multiple accounts, aggregate SMA status and update customer-level SMA class and date accordingly.
11. 11. Update customer records to reflect SMA status if any linked account is classified as SMA.
12. 12. Maintain movement history for both accounts and customers, recording any changes in SMA or asset classification status.
13. 13. Update descriptive fields for asset classification and SMA movement on customer records based on the latest classification keys.
14. 14. Mark the process as completed and increment the process run count if the SMA marking process finishes successfully.
15. 15. In case of errors, perform cleanup and update process status with error details.

## Business Rules / Validations

| # | Condition | Resulting Action | Fields Affected | Rule Type | Confidence | Validation Status | Source Evidence | Dependencies |
|---|---|---|---|---|---|---|---|---|
| 1 | A temporary table for DPD calculations already exists | Removes the existing DPD temporary table to avoid data conflicts | None (no data written) | explicit | high | verified | OBJECT_ID('TEMPDB..#DPD') IS NOT NULL; DROP TABLE  #DPD | None |
| 2 | An account has more than 30 days overdrawn or any overdue days | Includes the account for DPD analysis | None (no data written) | explicit | high | verified | isnull(A.DPD_Overdrawn,0)>30   OR  Isnull(A.DPD_Overdue,0)>0; Row from PRO.AccountCal included in #DPD | None |
| 3 | Any DPD metric (interest servicing, no credit, overdrawn, overdue, renewal, stock statement) is negative | Resets the negative DPD metric to zero to ensure only non-negative overdue values are used | DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | explicit | high | verified | isnull(DPD_IntService,0)<0; UPDATE #DPD SET DPD_IntService=0; isnull(DPD_NoCredit,0)<0; UPDATE #DPD SET DPD_NoCredit=0; isnull(DPD_Overdrawn,0)<0; UPDATE #DPD SET DPD_Overdrawn=0; isnull(DPD_Overdue,0)<0; UPDATE #DPD SET DPD_Overdue=0; isnull(DPD_Renewal,0)<0; UPDATE #DPD SET DPD_Renewal=0; isnull(DPD_StockStmt,0)<0; UPDATE #DPD SET DPD_StockStmt=0 | None |
| 4 | A DPD metric meets or exceeds its reference period value | Retains the DPD metric value; otherwise, sets it to zero | None (no data written) | explicit | high | verified | isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0); isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0); isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn ,0); isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue ,0); isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview ,0); isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) | None |
| 5 | At least one DPD metric meets or exceeds its reference period value | Includes the account in further SMA and asset classification analysis | None (no data written) | explicit | high | verified | isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) | None |
| 6 | Multiple DPD metrics are present for an account | Sets the maximum DPD value (DPD_Max) as the highest among all DPD metrics for the account | DPD_Max | explicit | high | unverified | DPD_Max; CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND ... ) THEN isnull(A.DPD_IntService,0) ... ELSE isnull(A.DPD_StockStmt,0) END | None |
| 7 | An account has a positive DPD_Max value | Assigns an SMA class to the account based on the DPD_Max value: 'SMA_0' for 1-30 days, 'SMA_1' for 31-60 days, 'SMA_2' for 61 days or more | SMA_CLASS | inferred | high | verified | CASE  WHEN dpd.DPD_Max  BETWEEN 1 AND 30  THEN 'SMA_0' WHEN dpd.DPD_Max  BETWEEN 31 AND 60  THEN 'SMA_1' WHEN dpd.DPD_Max  BETWEEN 61 AND 90  THEN 'SMA_2' WHEN dpd.DPD_Max >90 THEN 'SMA_2' ELSE NULL END | DPD_Max calculation |
| 8 | The facility type and DPD metric triggering the maximum value are identified | Records the reason for SMA downgrade (e.g., 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', 'DEGRADE BY OVERDUE', etc.) in the account record | SMA_REASON | inferred | high | unverified | CASE WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED' ... ELSE 'OTHER' END | DPD_Max calculation |
| 9 | An account is assigned an SMA class | Sets the SMA date to the date corresponding to the start of the overdue period | SMA_DT | inferred | high | verified | DATEADD(DAY, -dpd.DPD_MAX+1 ,@ProcessDate) | SMA_CLASS assignment |
| 10 | An account meets SMA criteria and is not always standard | Updates the account record with the calculated SMA class, reason, date, and sets the SMA flag | SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | explicit | high | unverified | UPDATE PRO.ACCOUNTCAL SET SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | SMA_CLASS assignment; SMA_REASON assignment; SMA_DT assignment |
| 11 | A customer has multiple accounts with SMA status | Aggregates the highest SMA class and earliest SMA date across all accounts and updates the customer record accordingly | SMA_CLASS_KEY, SMA_DT | inferred | high | verified | MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END); MIN(A.SMA_Dt) | SMA_CLASS assignment on accounts |
| 12 | Any linked account for a customer is classified as SMA | Sets the SMA flag on the customer record | FLGSMA | explicit | high | verified | UPDATE A SET A.FLGSMA='Y' FROM PRO.CUSTOMERCAL A INNER JOIN PRO.ACCOUNTCAL B ON A.UCIF_ID =B.UCIF_ID | SMA_CLASS assignment on accounts |
| 13 | A customer's SMA class or asset classification changes | Inserts a new record into the movement history table to track the change | None (no data written) | explicit | high | verified | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS); INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY; INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY | SMA_CLASS or asset class change |
| 14 | A customer's asset classification key or SMA class key is updated | Updates the descriptive movement field on the customer record to reflect the new classification (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS', 'SMA_0', 'SMA_1', 'SMA_2') | CustMoveDescription | explicit | high | verified | UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='STD'; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SUB'; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB1'; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB2'; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='DB3'; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='LOS'; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SMA_0'; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SMA_1'; UPDATE PRO.CUSTOMERCAL SET CustMoveDescription='SMA_2' | Asset class or SMA class key update |
| 15 | An account's final asset classification key is set and no SMA class is present | Updates the account's SMA class field to match the asset classification (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') | SMA_CLASS | explicit | high | verified | UPDATE PRO.AccountCal SET SMA_CLASS='STD'; UPDATE PRO.AccountCal SET SMA_CLASS='SUB'; UPDATE PRO.AccountCal SET SMA_CLASS='DB1'; UPDATE PRO.AccountCal SET SMA_CLASS='DB2'; UPDATE PRO.AccountCal SET SMA_CLASS='DB3'; UPDATE PRO.AccountCal SET SMA_CLASS='LOS' | FinalAssetClassAlt_Key set; SMA_CLASS is NULL |
| 16 | The SMA marking process completes successfully | Marks the process as completed, clears any error information, and increments the process run count | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | explicit | high | verified | Update PRO.ACLRUNNINGPROCESSSTATUS set COMPLETED='Y', ERRORDATE=NULL, ERRORDESCRIPTION=NULL, COUNT=ISNULL(COUNT,0)+1 | None |

## Calculations / Formulas

- **Process Date:** The process date is determined by selecting the date from the system day matrix for the given time key.
- **Effective To Date:** The effective to date is set as one day before the process date or derived from the automate advances table for extended flagged records.
- **DPD Metrics (No Credit, Overdrawn, Overdue, Renewal, Stock Statement):** Each DPD metric is set to its value if it meets or exceeds the reference period value; otherwise, it is set to zero.
- **Maximum DPD (DPD_Max):** The maximum DPD value is the highest among all DPD metrics for an account, representing the most severe overdue indicator.
- **SMA Class:** SMA class is assigned based on DPD_Max: 'SMA_0' for 1-30 days, 'SMA_1' for 31-60 days, 'SMA_2' for 61 days or more.
- **SMA Reason:** The reason for SMA downgrade is determined by the facility type and which DPD metric triggered the maximum value.
- **SMA Date:** The SMA date is calculated as the process date minus the DPD_Max value plus one, indicating the start of the overdue period.
- **Maximum SMA Class for Customer:** For each customer, the highest SMA class among all accounts is determined and recorded.
- **Earliest SMA Date for Customer:** For each customer, the earliest SMA date among all accounts is determined and recorded.
- **Movement To Date:** The movement to date is set as one day before the process date for movement history records.
- **Outstanding Balance for Account:** The outstanding balance is set to the account balance or zero if null.
- **Outstanding Balance for Customer:** The outstanding balance for the customer is set to the sum of balances or zero if null.
- **Process Run Count:** The process run count is incremented by one, defaulting to zero if previously null.

## Exception Handling Behavior

If an error occurs during processing, the procedure performs cleanup of temporary tables and updates the process status with error details, ensuring that incomplete or inconsistent data does not persist and that operational staff are alerted to the failure.

## Rule Provenance Summary

**Technical Implementation:** derived directly from the parsed source code and the per-chunk technical extraction (conditions, table reads/writes, calculations) - see Tables Read/Written above.

**Business Interpretation:** the Purpose Summary, Step-by-Step Logic Flow, and Business Rules sections translate that technical implementation into plain business language; the breakdown below shows how much of that interpretation is a direct restatement versus an inference or an assumption.

- **Total business rules:** 16
- **By rule type:** explicit = 12, inferred = 4
- **By validation status:** unverified = 3, verified = 13

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Ambiguities / Needs Review

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID,  

RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNo...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.DPD_Max=0  

   FROM #DPD A   

      

  

  

----  /*----------------FIND MAX DPD---------------------...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.FLGSMA=NULL  

             ,A.SMA_CLASS_KEY=NULL  

       ,A.SMA_DT=NULL  

     FROM PRO.CUSTOMERCAL A...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): SELECT A.CustomerEntityID,MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1   

                             WHEN SMA_CLASS='SMA_1...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): INSERT INTO #ACCOUNT_MOVEMENT_HISTORY  

   (  

     UCIF_ID,  

     RefCustomerID,  

     SourceSystemCustomerID,...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): INSERT INTO #Customer_MOVEMENT_HISTORY  

   (  

     UCIF_ID,  

     RefCustomerID,  

     SourceSystemCustomerID,...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE PRO.ACLRUNNINGPROCESSSTATUS   

SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNU...
- Table '[dbo].Automate_Advances' named in the technical extraction (tables_read) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#DPD' named in the technical extraction (tables_written) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#DPD' named in the technical extraction (tables_read) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#TEMPTABLE' named in the technical extraction (tables_written) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#TEMPTABLE_SMACLASS' named in the technical extraction (tables_written) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#TEMPTABLE_SMACLASSUcif' named in the technical extraction (tables_written) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#SMACLASS' named in the technical extraction (tables_written) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#ACCOUNT_MOVEMENT_HISTORY' named in the technical extraction (tables_read) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#ACCOUNT_MOVEMENT_HISTORY' named in the technical extraction (tables_written) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#Customer_MOVEMENT_HISTORY' named in the technical extraction (tables_read) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- Table '#Customer_MOVEMENT_HISTORY' named in the technical extraction (tables_written) could not be matched back to the source code for this chunk and may not be accurate; flagged low-confidence rather than asserted.
- The final output or reporting step is unclear due to an incomplete SELECT statement, so it is not possible to determine what summary or result is ultimately produced for users.
- Some DPD calculation logic and temporary table creation is referenced in commented-out code, making it uncertain whether all DPD metrics are calculated within this procedure or rely on external processes.
- Business rule evidence strings CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND ... ) THEN isnull(A.DPD_IntService,0) ... ELSE isnull(A.DPD_StockStmt,0) END could not be matched back to the technical extraction or source code and are flagged unverified.
- Business rule evidence strings CASE WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED' ... ELSE 'OTHER' END could not be matched back to the technical extraction or source code and are flagged unverified.
- Business rule evidence strings UPDATE PRO.ACCOUNTCAL SET SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA could not be matched back to the technical extraction or source code and are flagged unverified.
- Automated style check flagged possible leftover technical jargon in the synthesized output: select statement. Recommend a human pass to rephrase in business terms.
