## Object Overview

- **Object Name:** `UNKNOWN_OBJECT`
- **Object Type:** Procedure
- **SQL Dialect:** SQL Server T-SQL (detection confidence: high)
- **Parameters:** None

## Purpose Summary

This procedure determines and updates the Special Mention Account (SMA) classification and reasons for loan accounts and customers based on Days Past Due (DPD) metrics, in line with regulatory requirements such as RBI IRAC. It tracks changes in asset classification status over time, maintains movement history for both accounts and customers, and ensures that overdue, overdrawn, and other DPD-related fields are correctly calculated and do not contain negative values. The process also updates operational status and error tracking for audit and compliance purposes.

## Tables Read

| Table Name | Business Context | Filter Conditions | Confidence |
|---|---|---|---|
| `SYSDAYMATRIX` | Columns referenced: DATE | TIMEKEY=@TIMEKEY | high |
| `[dbo].Automate_Advances` | Columns referenced: Timekey | EXT_FLG='Y' | low |
| `PRO.AccountCal` | Columns referenced: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_Overdrawn, DPD_Overdue | isnull(A.DPD_Overdrawn,0)>30   OR  Isnull(A.DPD_Overdue,0)>0 | high |
| `#DPD` | Columns referenced: DPD_IntService, DPD_NoCredit, RefPeriodNoCredit, DPD_Overdrawn, RefPeriodOverDrawn, DPD_Overdue, RefPeriodOverdue, DPD_Renewal, RefPeriodReview, DPD_StockStmt, RefPeriodStkStatement, AccountEntityId | isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) | low |
| `#DPD` | Columns referenced: DPD_Max, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | isnull(A.DPD_Overdrawn,0)>0 OR Isnull(A.DPD_Overdue,0)>0 | low |
| `PRO.ACCOUNTCAL` | Columns referenced: SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | No filter / full read | high |
| `PRO.ACCOUNTCAL` | Columns referenced: SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA, FACILITYTYPE, BALANCE, ASSET_NORM, CustomerEntityID, AccountEntityID | ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 | high |
| `PRO.CUSTOMERCAL` | Columns referenced: CustomerEntityID, FLGPROCESSING | No filter / full read | high |
| `AdvAcBasicDetail` | Columns referenced: AccountEntityId, EffectiveFromTimeKey, EffectiveToTimeKey | (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY) | high |
| `PRO.SMA_MOVEMENT_HISTORY` | Columns referenced: TIMEKEY | TIMEKEY=@TIMEKEY | high |
| `PRO.PREVSMASTATUS` | Columns referenced: CustomerAcID, SMA_CLASS | No filter / full read | high |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: EffectiveFromTimeKey, CustomerAcID, EFFECTIVETOTimekey, MOVEMENTTOSTATUS | [EffectiveFromTimeKey]=@Timekey OR CustomerAcID=B.CustomerAcID AND B.EFFECTIVETOTimekey=49999 OR AA.EffectiveToTimeKey = 49999 OR AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY | high |
| `#ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | No filter / full read | low |
| `#ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: CustomerAcID, EffectiveToTimeKey, MOVEMENTTOSTATUS | AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS | low |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | Columns referenced: EffectiveFromTimeKey | [EffectiveFromTimeKey]=@Timekey | high |
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

1. 1. Remove any temporary tables from previous runs to ensure clean processing.
2. 2. Identify accounts with significant overdue or overdrawn days and prepare DPD metrics for these accounts.
3. 3. Ensure that all DPD-related fields (such as DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt) are not negative; reset any negative values to zero.
4. 4. For each DPD metric, compare the current value to its reference period; if the current value meets or exceeds the reference, retain it, otherwise set it to zero.
5. 5. Determine the maximum DPD value across all DPD metrics for each account.
6. 6. Update the account's maximum DPD field accordingly.
7. 7. Assign the SMA classification to each account based on the maximum DPD value, mapping DPD ranges to SMA_0, SMA_1, or SMA_2 as per regulatory guidelines.
8. 8. Assign the reason for SMA classification based on which DPD metric triggered the maximum value and the facility type of the account.
9. 9. Set the SMA date to reflect the start of the overdue period based on the maximum DPD.
10. 10. For eligible accounts, update the SMA classification, reason, date, and SMA flag fields.
11. 11. Aggregate SMA classification at the customer level, updating customer SMA class and date where required.
12. 12. Track and record any changes in SMA classification for both accounts and customers in movement history tables, updating effective dates as needed.
13. 13. Update descriptive fields for customer movement based on asset classification keys and SMA class keys.
14. 14. Update process status and error tracking fields to reflect completion or errors in the SMA marking process.

## Business Rules / Validations

| # | Condition | Resulting Action | Fields Affected | Rule Type | Confidence | Validation Status | Source Evidence | Dependencies |
|---|---|---|---|---|---|---|---|---|
| 1 | If any DPD-related field (DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt) is less than zero | Set the respective DPD field to zero to prevent negative overdue or overdrawn values | DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | explicit | high | verified | isnull(DPD_IntService,0)<0; isnull(DPD_NoCredit,0)<0; isnull(DPD_Overdrawn,0)<0; isnull(DPD_Overdue,0)<0; isnull(DPD_Renewal,0)<0; isnull(DPD_StockStmt,0)<0 | None |
| 2 | If the current DPD metric (e.g., DPD_NoCredit) is greater than or equal to its reference period value | Retain the current DPD metric value; otherwise, set it to zero | None (no data written) | explicit | high | verified | isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0); isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn ,0); isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue ,0); isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview ,0); isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) | None |
| 3 | For each account, determine which DPD metric has the highest value among DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | Set the account's maximum DPD field to this highest value | DPD_Max | explicit | high | verified | A.DPD_Max; DPD_Max | None |
| 4 | If the account's maximum DPD is between 1 and 30 days | Set the account's asset classification to SMA_0 | SMA_CLASS | explicit | high | verified | dpd.DPD_Max BETWEEN 1 AND 30; A.SMA_CLASS = 'SMA_0' | Set the account's maximum DPD field to this highest value |
| 5 | If the account's maximum DPD is between 31 and 60 days | Set the account's asset classification to SMA_1 | SMA_CLASS | explicit | high | verified | dpd.DPD_Max BETWEEN 31 AND 60; A.SMA_CLASS = 'SMA_1' | Set the account's maximum DPD field to this highest value |
| 6 | If the account's maximum DPD is between 61 and 90 days or greater than 90 days | Set the account's asset classification to SMA_2 | SMA_CLASS | explicit | high | verified | dpd.DPD_Max BETWEEN 61 AND 90; dpd.DPD_Max > 90; A.SMA_CLASS = 'SMA_2' | Set the account's maximum DPD field to this highest value |
| 7 | If the facility type is Cash Credit or Overdraft and the DPD_IntService equals the maximum DPD | Set the SMA reason to 'DEGRADE BY INT NOT SERVICED' | SMA_REASON | explicit | high | verified | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON = 'DEGRADE BY INT NOT SERVICED' | Set the account's maximum DPD field to this highest value |
| 8 | If the facility type is Cash Credit or Overdraft and the DPD_NoCredit equals the maximum DPD | Set the SMA reason to 'DEGRADE BY NO CREDIT' | SMA_REASON | explicit | high | verified | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON = 'DEGRADE BY NO CREDIT' | Set the account's maximum DPD field to this highest value |
| 9 | If the facility type is Term Loan, Demand Loan, Bill Purchased, Bill Discounted, or Packing Credit and the DPD_Overdue equals the maximum DPD | Set the SMA reason to 'DEGRADE BY OVERDUE' | SMA_REASON | explicit | high | verified | A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON = 'DEGRADE BY OVERDUE' | Set the account's maximum DPD field to this highest value |
| 10 | If the facility type is Cash Credit or Overdraft and the DPD_Overdrawn equals the maximum DPD and is greater than 30 days | Set the SMA reason to 'DEGRADE BY CONTI EXCESS' | SMA_REASON | explicit | high | verified | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30; A.SMA_REASON = 'DEGRADE BY CONTI EXCESS' | Set the account's maximum DPD field to this highest value |
| 11 | If the facility type is Cash Credit or Overdraft and the DPD_StockStmt equals the maximum DPD | Set the SMA reason to 'DEGRADE BY STOCK STATEMENT' | SMA_REASON | explicit | high | verified | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON = 'DEGRADE BY STOCK STATEMENT' | Set the account's maximum DPD field to this highest value |
| 12 | If the facility type is Cash Credit or Overdraft and the DPD_Renewal equals the maximum DPD | Set the SMA reason to 'DEGRADE BY REVIEW DUE DATE' | SMA_REASON | explicit | high | verified | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON = 'DEGRADE BY REVIEW DUE DATE' | Set the account's maximum DPD field to this highest value |
| 13 | If none of the above SMA reason conditions are met | Set the SMA reason to 'OTHER' | SMA_REASON | explicit | high | verified | ELSE; A.SMA_REASON = 'OTHER' | Set the account's maximum DPD field to this highest value |
| 14 | If the account meets eligibility criteria (processing flag is 'N', asset class key is 1, balance is positive, asset norm is not 'ALWYS_STD', DPD_Overdrawn or DPD_Overdue is non-negative, and DPD_Max is positive) | Update the account's SMA classification, reason, SMA date, and SMA flag fields | SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | explicit | high | verified | ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 | Set the account's asset classification to SMA_0; Set the account's asset classification to SMA_1; Set the account's asset classification to SMA_2; Set the SMA reason |
| 15 | If a customer's SMA flag is 'Y' | Update the customer's SMA class key and SMA date fields based on the maximum SMA class and earliest SMA date among their accounts | SMA_CLASS_KEY, SMA_DT | explicit | high | verified | A.FLGSMA='Y'; UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM PRO.CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID | None |
| 16 | If an account's SMA flag is 'Y' | Update the corresponding customer's SMA flag to 'Y' | FLGSMA | explicit | high | verified | B.FLGSMA='Y'; UPDATE A SET A.FLGSMA='Y' FROM PRO.CUSTOMERCAL A INNER JOIN PRO.ACCOUNTCAL B ON A.UCIF_ID =B.UCIF_ID | None |
| 17 | If the asset classification key or SMA class key matches a specific value | Update the customer's movement description field to the corresponding classification label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS', 'SMA_0', 'SMA_1', 'SMA_2') | CustMoveDescription | explicit | high | verified | SYSASSETCLASSALT_KEY=1; SYSASSETCLASSALT_KEY=2; SYSASSETCLASSALT_KEY=3; SYSASSETCLASSALT_KEY=4; SYSASSETCLASSALT_KEY=5; SYSASSETCLASSALT_KEY=6; SMA_CLASS_KEY=1; SMA_CLASS_KEY=2; SMA_CLASS_KEY=3 | None |
| 18 | If the final asset class key is set and the SMA class is not already assigned | Update the account's SMA class field to the corresponding classification label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') | SMA_CLASS | explicit | high | verified | FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL | None |
| 19 | If an account's SMA classification changes compared to its previous value | Insert a record into the SMA movement history table to track the change, including the time, account, previous status, and current status | None (no data written) | explicit | high | verified | B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,''); INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) | None |
| 20 | If an account's movement history record is open (EffectiveToTimeKey = 49999) and the account is not present in the new movement set | Update the movement history record to close it by setting the EffectiveToTimeKey and MovementToDate | EffectiveToTimeKey, MovementToDate | explicit | high | verified | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null; UPDATE AA SET EffectiveToTimeKey = @vEffectiveto, MovementToDate=DATEADD(DD,-1,@ProcessDate) | None |
| 21 | If an account's movement history record is open and the movement status has changed in the new movement set | Update the movement history record to close it by setting the EffectiveToTimeKey and MovementToDate | EffectiveToTimeKey, MovementToDate | explicit | high | verified | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS); UPDATE AA SET EffectiveToTimeKey = @vEffectiveto, MovementToDate=DATEADD(DD,-1,@ProcessDate) | None |
| 22 | If a customer's movement history record is open (EffectiveToTimeKey = 49999) and the customer is not present in the new movement set | Update the customer movement history record to close it by setting the EffectiveToTimeKey and MovementToDate | EffectiveToTimeKey, MovementToDate | explicit | high | verified | AA.EffectiveToTimeKey = 49999 and B.SourceSystemCustomerID is null; Update PRO.CUSTOMER_MOVEMENT_HISTORY set EffectiveToTimeKey, MovementToDate | None |
| 23 | If a customer's movement history record is open and the movement status has changed in the new movement set | Update the customer movement history record to close it by setting the EffectiveToTimeKey and MovementToDate | EffectiveToTimeKey, MovementToDate | explicit | high | verified | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS); Update PRO.CUSTOMER_MOVEMENT_HISTORY set EffectiveToTimeKey, MovementToDate | None |
| 24 | If the SMA marking process completes or encounters an error | Update the process status fields to reflect completion, error date, error description, and increment the count | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | explicit | high | verified | RUNNINGPROCESSNAME='SMA_MARKING'; Update PRO.ACLRUNNINGPROCESSSTATUS set COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | None |

## Calculations / Formulas

- **Process Date:** The process date is set to the date corresponding to the current time key from the system day matrix.
- **Effective To Date for Movement History:** The effective to date is set to one day before the process date, calculated by subtracting one day from the process date.
- **DPD Metrics (e.g., DPD_NoCredit, DPD_Overdrawn, etc.):** Each DPD metric is set to its current value if it meets or exceeds its reference period value; otherwise, it is set to zero.
- **Maximum DPD (DPD_Max):** The maximum DPD is determined by comparing all DPD metrics and selecting the highest value.
- **SMA Classification:** The SMA classification is assigned based on the maximum DPD value: SMA_0 for 1-30 days, SMA_1 for 31-60 days, SMA_2 for 61 days or more.
- **SMA Reason:** The SMA reason is determined by which DPD metric triggered the maximum value and the facility type of the account.
- **SMA Date:** The SMA date is set to the process date minus the maximum DPD plus one, representing the start of the overdue period.
- **Maximum SMA Class at Customer Level:** The maximum SMA class for a customer is determined by the highest SMA class among all their accounts.
- **Earliest SMA Date at Customer Level:** The earliest SMA date for a customer is determined by the minimum SMA date among all their accounts.
- **Outstanding Balance for Account:** The total outstanding balance for an account is set to the account's balance, defaulting to zero if null.
- **Outstanding Balance for Customer:** The total outstanding balance for a customer is set to the sum of outstanding balances for all their accounts, defaulting to zero if null.
- **Movement To Date for History Records:** The movement to date is set to one day before the process date.
- **Process Count:** The process count is incremented by one, defaulting to zero if previously null.

## Exception Handling Behavior

If an error occurs during processing, the system performs cleanup by removing temporary tables and updates the process status with error details, including the error date and description. This ensures that incomplete or failed runs are properly logged for audit and operational follow-up.

## Rule Provenance Summary

**Technical Implementation:** derived directly from the parsed source code and the per-chunk technical extraction (conditions, table reads/writes, calculations) - see Tables Read/Written above.

**Business Interpretation:** the Purpose Summary, Step-by-Step Logic Flow, and Business Rules sections translate that technical implementation into plain business language; the breakdown below shows how much of that interpretation is a direct restatement versus an inference or an assumption.

- **Total business rules:** 24
- **By rule type:** explicit = 24
- **By validation status:** verified = 24

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
- The calculation logic for DPD fields such as DPD_IntService and DPD_NoCredit is not fully shown, so the exact business meaning of these fields and how they are derived is unclear.
- The final logic for calculating the maximum DPD value and its destination is incomplete, making it uncertain how this value is finalized for each account.
- There are references to updating movement history dates from the system day matrix, but the actual implementation is not shown, leaving the exact date assignment process ambiguous.
- Some DPD and movement history calculations are commented out or not executed in the provided extraction, so their business impact cannot be fully determined.
