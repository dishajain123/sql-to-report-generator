## Object Overview

- **Object Name:** `UNKNOWN_OBJECT`
- **Object Type:** Procedure
- **SQL Dialect:** SQL Server T-SQL (detection confidence: high)
- **Parameters:** None

## Purpose Summary

This procedure determines and updates the Special Mention Account (SMA) classification and asset quality status for loan and advance accounts, as well as for customers, based on overdue and credit behavior. It ensures compliance with regulatory norms by tracking overdue days, classifying accounts and customers into SMA and asset classes, and recording movement histories for audit and regulatory reporting. The process also updates operational status and error tracking for process monitoring.

## Tables Read

| Table Name | Business Context | Filter Conditions | Confidence |
|---|---|---|---|
| `SYSDAYMATRIX` | Columns referenced: DATE | TIMEKEY=@TIMEKEY | high |
| `[dbo].Automate_Advances` | Columns referenced: Timekey | EXT_FLG='Y' | low |
| `PRO.AccountCal` | Columns referenced: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_Overdrawn, DPD_Overdue | isnull(A.DPD_Overdrawn,0)>30   OR  Isnull(A.DPD_Overdue,0)>0 | high |
| `#DPD` | Columns referenced: DPD_IntService, DPD_NoCredit, RefPeriodNoCredit, DPD_Overdrawn, RefPeriodOverDrawn, DPD_Overdue, RefPeriodOverdue, DPD_Renewal, RefPeriodReview, DPD_StockStmt, RefPeriodStkStatement, AccountEntityId | isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) | low |
| `#DPD` | Columns referenced: DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | No filter / full read | low |
| `PRO.ACCOUNTCAL` | Columns referenced: SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA, CustomerEntityID, AccountEntityID, FACILITYTYPE, BALANCE, ASSET_NORM, FINALASSETCLASSALT_KEY | No filter / full read | high |
| `PRO.CUSTOMERCAL` | Columns referenced: CustomerEntityID, FLGPROCESSING | No filter / full read | high |
| `AdvAcBasicDetail` | Columns referenced: AccountEntityId, EffectiveFromTimeKey, EffectiveToTimeKey | (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY) | high |
| `PRO.SMA_MOVEMENT_HISTORY` | Columns referenced: TIMEKEY | TIMEKEY=@TIMEKEY | high |
| `PRO.PREVSMASTATUS` | Columns referenced: CustomerAcID, SMA_CLASS | No filter / full read | high |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: EffectiveFromTimeKey, CustomerAcID, EFFECTIVETOTimekey, MOVEMENTTOSTATUS | [EffectiveFromTimeKey]=@Timekey OR CustomerAcID=B.CustomerAcID AND B.EFFECTIVETOTimekey=49999 OR AA.EffectiveToTimeKey=49999 OR AA.EffectiveToTimeKey=49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY | high |
| `#ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | No filter / full read | low |
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
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | INSERT | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | (CASE WHEN  B.SourceSystemCustomerID IS NULL THEN 1 WHEN B.SourceSystemCustomerID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 | high |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.SourceSystemCustomerID is null | high |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) | high |
| `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME='SMA_MARKING' | high |

## Step-by-Step Logic Flow

1. 1. Remove any temporary data from previous runs to ensure a clean processing environment.
2. 2. Identify accounts with significant overdue or overdrawn status and prepare them for further SMA and asset classification analysis.
3. 3. Normalize negative overdue and related counters to zero to prevent invalid data from affecting classification.
4. 4. For each account, compare current overdue and related counters to reference periods to determine if regulatory thresholds are breached.
5. 5. Calculate the maximum overdue days across all relevant overdue and credit counters for each account.
6. 6. Assign an SMA class to each account based on the maximum overdue days, following regulatory definitions (e.g., SMA_0, SMA_1, SMA_2).
7. 7. Determine the primary reason for SMA classification based on the type of facility and which overdue or credit counter triggered the maximum.
8. 8. Update the SMA classification, reason, and effective date for each account in the core account table.
9. 9. Propagate SMA flags and classes to the customer level, updating customer records where any linked account is classified as SMA.
10. 10. Track and record changes in SMA class for accounts and customers in movement history tables for audit and compliance.
11. 11. Update descriptive fields for asset class and SMA class on customer records for reporting and downstream processing.
12. 12. Maintain and update process status and error tracking for operational monitoring.
13. 13. On process completion or error, update process status and clean up temporary data.

## Business Rules / Validations

| # | Condition | Resulting Action | Fields Affected | Rule Type | Confidence | Validation Status | Source Evidence | Dependencies |
|---|---|---|---|---|---|---|---|---|
| 1 | If an account's days past due for overdrawn balance exceeds 30 days or days past due for overdue amount is greater than 0 | Include the account for SMA and asset classification processing | None (no data written) | explicit | high | verified | isnull(A.DPD_Overdrawn,0)>30   OR  Isnull(A.DPD_Overdue,0)>0 | None |
| 2 | If any of the overdue or credit counters (DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt) are negative | Set the respective counter to zero to ensure only valid overdue values are used in classification | DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | explicit | high | verified | isnull(DPD_IntService,0)<0; isnull(DPD_NoCredit,0)<0; isnull(DPD_Overdrawn,0)<0; isnull(DPD_Overdue,0)<0; isnull(DPD_Renewal,0)<0; isnull(DPD_StockStmt,0)<0 | None |
| 3 | If any overdue or credit counter meets or exceeds its reference period threshold | Mark the account for further SMA classification processing | None (no data written) | explicit | high | verified | isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) | None |
| 4 | For each account, determine the maximum value among all overdue and credit counters | Set the DPD_Max field to the highest overdue or credit counter value for the account | DPD_Max | explicit | high | unverified | DPD_Max calculation formula | None |
| 5 | If DPD_Max is between 1 and 30 days | Set the account's SMA class to 'SMA_0' | SMA_CLASS | explicit | high | verified | dpd.DPD_Max BETWEEN 1 AND 30 | Set the DPD_Max field to the highest overdue or credit counter value for the account |
| 6 | If DPD_Max is between 31 and 60 days | Set the account's SMA class to 'SMA_1' | SMA_CLASS | explicit | high | verified | dpd.DPD_Max BETWEEN 31 AND 60 | Set the DPD_Max field to the highest overdue or credit counter value for the account |
| 7 | If DPD_Max is between 61 and 90 days or greater than 90 days | Set the account's SMA class to 'SMA_2' | SMA_CLASS | explicit | high | verified | dpd.DPD_Max BETWEEN 61 AND 90; dpd.DPD_Max >90 | Set the DPD_Max field to the highest overdue or credit counter value for the account |
| 8 | If the account's facility type and overdue/credit counter match specific criteria (e.g., for CC/OD, DPD_IntService equals DPD_Max) | Set the SMA reason field to the corresponding degradation reason (e.g., 'DEGRADE BY INT NOT SERVICED', 'DEGRADE BY NO CREDIT', etc.) | SMA_REASON | explicit | high | verified | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0); A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0); A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0); A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30; A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0); A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) | Set the DPD_Max field to the highest overdue or credit counter value for the account |
| 9 | For each account with a positive balance, not always standard, and with overdue or overdrawn counters non-negative and DPD_Max positive | Update the account's SMA class, SMA reason, SMA effective date, and SMA flag in the account master table | SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | explicit | high | verified | ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 | Set the account's SMA class to 'SMA_0'; Set the account's SMA class to 'SMA_1'; Set the account's SMA class to 'SMA_2' |
| 10 | If any account linked to a customer is flagged as SMA | Update the customer's SMA flag, SMA class key, and SMA effective date in the customer master table | FLGSMA, SMA_CLASS_KEY, SMA_DT | explicit | high | verified | A.FLGSMA='Y'; UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt FROM PRO.CUSTOMERCAL A INNER JOIN #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID | Update the account's SMA class, SMA reason, SMA effective date, and SMA flag in the account master table |
| 11 | If a customer's SMA flag is set based on any linked account | Update the customer's SMA flag to 'Y' | FLGSMA | explicit | high | verified | B.FLGSMA='Y'; UPDATE A SET A.FLGSMA='Y' FROM PRO.CUSTOMERCAL A INNER JOIN PRO.ACCOUNTCAL B ON A.UCIF_ID =B.UCIF_ID | Update the account's SMA class, SMA reason, SMA effective date, and SMA flag in the account master table |
| 12 | If the SMA class for an account changes compared to the previous status | Insert a new record in the SMA movement history table to track the change | TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS | explicit | high | verified | B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') | Update the account's SMA class, SMA reason, SMA effective date, and SMA flag in the account master table |
| 13 | If the asset class key for a customer matches a specific value | Update the customer's movement description field to the corresponding asset class label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') | CustMoveDescription | explicit | high | verified | SYSASSETCLASSALT_KEY=1; SYSASSETCLASSALT_KEY=2; SYSASSETCLASSALT_KEY=3; SYSASSETCLASSALT_KEY=4; SYSASSETCLASSALT_KEY=5; SYSASSETCLASSALT_KEY=6 | None |
| 14 | If the SMA class key for a customer matches a specific value | Update the customer's movement description field to the corresponding SMA class label (e.g., 'SMA_0', 'SMA_1', 'SMA_2') | CustMoveDescription | explicit | high | verified | SMA_CLASS_KEY=1; SMA_CLASS_KEY=2; SMA_CLASS_KEY=3 | None |
| 15 | If the final asset class key for an account matches a specific value and the SMA class is not already set | Set the account's SMA class to the corresponding asset class label (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') | SMA_CLASS | explicit | high | verified | FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL | None |
| 16 | If an account or customer movement status changes or is new for the current processing date | Insert a new record in the account or customer movement history table to track the status change, including effective dates and outstanding amounts | EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate, UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, TotOsCust | explicit | high | verified | (CASE WHEN  B.CustomerAcID IS NULL THEN 1 WHEN B.CustomerAcID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1; (CASE WHEN  B.SourceSystemCustomerID IS NULL THEN 1 WHEN B.SourceSystemCustomerID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 | None |
| 17 | If an account or customer movement record is open-ended (EffectiveToTimeKey = 49999) and a new movement is detected | Update the existing movement record to close it by setting the EffectiveToTimeKey and MovementToDate to the appropriate values | EffectiveToTimeKey, MovementToDate | explicit | high | verified | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null; AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS); AA.EffectiveToTimeKey = 49999 and B.SourceSystemCustomerID is null; AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) | Insert a new record in the account or customer movement history table to track the status change, including effective dates and outstanding amounts |
| 18 | If the process being executed is 'SMA_MARKING' | Update the process status table to mark completion, record any errors, and increment the process count | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | explicit | high | verified | RUNNINGPROCESSNAME='SMA_MARKING' | None |

## Calculations / Formulas

- **Process Date:** The process date is determined by looking up the date corresponding to the current time key in the system day matrix.
- **Effective To Date for Movement Records:** The effective to date for closing movement records is set to one day before the process date.
- **Overdue and Credit Counters (DPD_* fields):** Each overdue or credit counter is set to its current value if it meets or exceeds its reference period threshold; otherwise, it is set to zero.
- **Maximum Days Past Due (DPD_Max):** The maximum overdue days for an account is determined by taking the highest value among all overdue and credit counters.
- **SMA Class:** The SMA class is assigned based on the maximum overdue days: 1-30 days is 'SMA_0', 31-60 days is 'SMA_1', 61-90 days or more is 'SMA_2'.
- **SMA Reason:** The SMA reason is set based on which overdue or credit counter triggered the maximum and the facility type of the account.
- **SMA Effective Date:** The SMA effective date is calculated as the process date minus the maximum overdue days plus one.
- **Maximum SMA Class for Customer:** The maximum SMA class for a customer is determined by the highest SMA class among all linked accounts.
- **Outstanding Amounts:** Outstanding amounts for accounts and customers are defaulted to zero if not available.
- **Process Count:** The process count is incremented by one, defaulting to zero if previously null.

## Exception Handling Behavior

If an error occurs during processing, the system cleans up temporary data and updates the process status table with error details, including the error date and description. This ensures that operational staff are alerted to failures and that incomplete or inconsistent data does not persist.

## Rule Provenance Summary

**Technical Implementation:** derived directly from the parsed source code and the per-chunk technical extraction (conditions, table reads/writes, calculations) - see Tables Read/Written above.

**Business Interpretation:** the Purpose Summary, Step-by-Step Logic Flow, and Business Rules sections translate that technical implementation into plain business language; the breakdown below shows how much of that interpretation is a direct restatement versus an inference or an assumption.

- **Total business rules:** 18
- **By rule type:** explicit = 18
- **By validation status:** unverified = 1, verified = 17

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
- The calculation logic for the individual overdue and credit counters (DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt) is not fully visible in the extraction, so the exact business meaning of these counters may require further review.
- The final logic for calculating the maximum days past due (DPD_Max) is incomplete in the extraction, so there may be additional conditions or adjustments not captured here.
- Business rule evidence strings DPD_Max calculation formula could not be matched back to the technical extraction or source code and are flagged unverified.
