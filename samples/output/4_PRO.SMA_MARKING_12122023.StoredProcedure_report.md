## Object Overview

- **Object Name:** `SMA_MARKING_12122023`
- **Object Type:** Procedure
- **SQL Dialect:** SQL Server T-SQL
- **Parameters:** Not specified (extraction failed / Needs Review)

## Purpose Summary

This procedure automates the identification and marking of Special Mention Accounts (SMA) in accordance with regulatory guidelines, based on the overdue status and other delinquency parameters of loan and advance accounts. It updates account and customer records with the appropriate SMA classification, reason, and effective date, and maintains historical movement records for audit and compliance tracking. The process ensures that all relevant fields are consistently updated and that negative or invalid delinquency values are corrected before classification.

## Tables Read

| Table Name | Business Context | Filter Conditions |
|---|---|---|
| `SYSDAYMATRIX` | Columns referenced: DATE | TIMEKEY=@TIMEKEY |
| `dbo.Automate_Advances` | Columns referenced: Timekey | EXT_FLG='Y' |
| `PRO.AccountCal` | Columns referenced: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_Overdrawn, DPD_Overdue | isnull(A.DPD_Overdrawn,0)>30 OR Isnull(A.DPD_Overdue,0)>0 |
| `#DPD` | Columns referenced: CustomerAcID, DPD_IntService, RefPeriodIntService, DPD_NoCredit, RefPeriodNoCredit, DPD_Overdrawn, RefPeriodOverDrawn, DPD_Overdue, RefPeriodOverdue, DPD_Renewal, RefPeriodReview, DPD_StockStmt, RefPeriodStkStatement | isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) |
| `#DPD` | Columns referenced: DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_Max | No filter / full read |
| `#DPD` | Columns referenced: DPD_Overdue, DPD_NoCredit, DPD_IntService, DPD_Overdrawn, DPD_Renewal, DPD_StockStmt | isnull(A.DPD_Overdrawn,0)>0   OR  Isnull(A.DPD_Overdue,0)>0 |
| `PRO.ACCOUNTCAL` | Columns referenced: SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA, CustomerEntityID, AccountEntityID, FACILITYTYPE, BALANCE, ASSET_NORM | No filter / full read |
| `PRO.CUSTOMERCAL` | Columns referenced: CustomerEntityID, FLGPROCESSING | No filter / full read |
| `AdvAcBasicDetail` | Columns referenced: AccountEntityId, EffectiveFromTimeKey, EffectiveToTimeKey | (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY) |
| `PRO.SMA_MOVEMENT_HISTORY` | Columns referenced: TIMEKEY | TIMEKEY=@TIMEKEY |
| `PRO.PREVSMASTATUS` | Columns referenced: CustomerAcID, SMA_CLASS | No filter / full read |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: EffectiveFromTimeKey | [EffectiveFromTimeKey]= @Timekey |
| `#SMACLASS` | Columns referenced: CustomerAcID, SMA_CLASS | No filter / full read |
| `#ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | (CASE WHEN  B.CustomerAcID IS NULL THEN 1  WHEN B.CustomerAcID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1 END )=1 |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: CustomerAcID, EFFECTIVETOTimekey, MovementTOStatus | A.CustomerAcID=B.CustomerAcID AND B.EFFECTIVETOTimekey=49999 |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: CustomerAcID, EffectiveToTimeKey | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null |
| `#ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: CustomerAcID, EffectiveToTimeKey | B.CustomerAcID is null |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: CustomerAcID, EffectiveToTimeKey, EffectiveFROMTimeKey, MOVEMENTTOSTATUS | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) |
| `#ACCOUNT_MOVEMENT_HISTORY` | Columns referenced: CustomerAcID, EffectiveToTimeKey, MOVEMENTTOSTATUS | BB.CustomerAcID=AA.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | Columns referenced: EffectiveFromTimeKey | [EffectiveFromTimeKey]= @Timekey |
| `PRO.CustomerCal` | Columns referenced: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, CustMoveDescription, TotOsCust | No filter / full read |
| `#Customer_MOVEMENT_HISTORY` | Columns referenced: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | No filter / full read |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | Columns referenced: SourceSystemCustomerID, EFFECTIVETOTimekey, MovementTOStatus | A.SourceSystemCustomerID=B.SourceSystemCustomerID AND B.EFFECTIVETOTimekey=49999 |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | Columns referenced: SourceSystemCustomerID, MOVEMENTFROMSTATUS, MOVEMENTTOSTATUS, EffectiveToTimeKey, EffectiveFROMTimeKey | AA.EffectiveToTimeKey = 49999 and B.SourceSystemCustomerID is null |
| `#Customer_MOVEMENT_HISTORY` | Columns referenced: SourceSystemCustomerID, EffectiveToTimeKey, MOVEMENTTOSTATUS | B.EffectiveToTimeKey =49999 |
| `#Customer_MOVEMENT_HISTORY` | Columns referenced: SourceSystemCustomerID, EffectiveToTimeKey, MOVEMENTTOSTATUS | EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Columns referenced: RUNNINGPROCESSNAME, COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME='SMA_MARKING' |

## Tables Written

| Table Name | Operation Type | Columns Affected | Business Trigger |
|---|---|---|---|
| `#DPD` | INSERT | AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_MAX | isnull(A.DPD_Overdrawn,0)>30 OR Isnull(A.DPD_Overdue,0)>0 |
| `#DPD` | UPDATE | DPD_IntService | isnull(DPD_IntService,0)<0 |
| `#DPD` | UPDATE | DPD_NoCredit | isnull(DPD_NoCredit,0)<0 |
| `#DPD` | UPDATE | DPD_Overdrawn | isnull(DPD_Overdrawn,0)<0 |
| `#DPD` | UPDATE | DPD_Overdue | isnull(DPD_Overdue,0)<0 |
| `#DPD` | UPDATE | DPD_Renewal | isnull(DPD_Renewal,0)<0 |
| `#DPD` | UPDATE | DPD_StockStmt | isnull(DPD_StockStmt,0)<0 |
| `#TEMPTABLE` | INSERT | CustomerAcID, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt | isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0) OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0) OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0) OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) |
| `#DPD` | UPDATE | DPD_Max | Always, on each execution |
| `PRO.ACCOUNTCAL` | UPDATE | SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | Always, on each execution |
| `PRO.ACCOUNTCAL` | UPDATE | SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 |
| `PRO.CUSTOMERCAL` | UPDATE | FLGSMA, SMA_CLASS_KEY, SMA_DT | Always, on each execution |
| `PRO.CUSTOMERCAL` | UPDATE | FLGSMA | A.CustomerEntityID =B.CustomerEntityID AND B.FLGSMA='Y' |
| `PRO.CUSTOMERCAL` | UPDATE | SMA_CLASS_KEY, SMA_DT | A.CustomerEntityID=B.CustomerEntityID AND A.FLGSMA='Y' |
| `PRO.CUSTOMERCAL` | UPDATE | FLGSMA | A.UCIF_ID =B.UCIF_ID AND B.FLGSMA='Y' |
| `PRO.CUSTOMERCAL` | UPDATE | SMA_CLASS_KEY, SMA_DT | A.UCIF_ID=B.UCIF_ID AND A.FLGSMA='Y' |
| `PRO.SMA_MOVEMENT_HISTORY` | DELETE | Not identified | TIMEKEY=@TIMEKEY |
| `PRO.SMA_MOVEMENT_HISTORY` | INSERT | TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS | Always, on each execution |
| `PRO.PREVSMASTATUS` | TRUNCATE | Not identified | Always, on each execution |
| `PRO.PREVSMASTATUS` | INSERT | @TIMEKEY, CustomerAcID, SMA_CLASS | Always, on each execution |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=1 |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=2 |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=3 |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=4 |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=5 |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SYSASSETCLASSALT_KEY=6 |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SMA_CLASS_KEY=1 |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SMA_CLASS_KEY=2 |
| `PRO.CUSTOMERCAL` | UPDATE | CustMoveDescription | SMA_CLASS_KEY=3 |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL |
| `PRO.AccountCal` | UPDATE | SMA_CLASS | FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL |
| `#ACCOUNT_MOVEMENT_HISTORY` | INSERT | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | Always, on each execution |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | INSERT | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc | Always, on each execution |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) |
| `#Customer_MOVEMENT_HISTORY` | INSERT | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | Always, on each execution |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | INSERT | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | Always, on each execution |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.SourceSystemCustomerID is null |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | UPDATE | EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) |
| `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME='SMA_MARKING' |
| `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | WHERE RUNNINGPROCESSNAME='SMA_MARKING' |

## Step-by-Step Logic Flow

1. Identify accounts with significant overdue or overdrawn days and prepare them for SMA evaluation.
2. Ensure all delinquency parameters (such as overdue days, overdrawn days, interest not serviced, etc.) are non-negative by resetting any negative values to zero.
3. For each account, determine the maximum delinquency parameter to be used for SMA classification.
4. Assign the SMA class to each account based on the maximum delinquency days, following regulatory thresholds.
5. Record the reason for SMA classification based on the type of delinquency and facility type (e.g., interest not serviced, no credit, overdue, continuous excess, stock statement, review due date).
6. Set the effective SMA date based on the maximum delinquency days.
7. Update account and customer records with the new SMA classification, reason, date, and flag indicating SMA status.
8. Aggregate SMA status at the customer level and update customer records accordingly.
9. Maintain movement history for both accounts and customers, updating or closing previous records as needed to reflect status changes.
10. Update process status and handle any errors by recording failure details and cleaning up temporary data.

# Business Conditions Report — SMA_MARKING_12122023

> **What this process does:** This procedure automates the identification and marking of Special Mention Accounts (SMA) in accordance with regulatory guidelines, based on the overdue status and other delinquency parameters of loan and advance accounts. It updates account and customer records with the appropriate SMA classification, reason, and effective date, and maintains historical movement records for audit and compliance tracking. The process ensures that all relevant fields are consistently updated and that negative or invalid delinquency values are corrected before classification.

## Glossary

| Term | Business Meaning |
|---|---|
| **COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT** | Update the process status to indicate completion and increment the process count. |
| **CustMoveDescription** | Update the customer's movement description to reflect the new classification (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS', 'SMA_0', 'SMA_1', 'SMA_2'). |
| **DPD** | Days Past Due |
| **DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt** | Set the negative delinquency parameter to zero to ensure only valid, non-negative values are used for SMA classification. |
| **DPD_Max** | Set the maximum delinquency days (DPD_Max) to the highest value among all delinquency parameters for the account. |
| **EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate** | Insert a new record into the account or customer movement history, capturing the effective dates, movement status, and outstanding amounts. |
| **EffectiveToTimeKey, MovementToDate** | Update the existing movement history record to close it by setting the effective to date and movement to date to the day before the new movement. |
| **FLGSMA** | Update the customer's SMA flag to indicate SMA status. |
| **FLGSMA, SMA_CLASS_KEY, SMA_DT** | Update the customer's SMA flag, SMA class key, and SMA date at the UCIF level. |
| **PREVSTATUS, CURRENTSTATUS** | Record the previous and current SMA status for the account in the SMA movement history for audit and compliance tracking. |
| **SMA** | Special Mention Account |
| **SMA_CLASS** | Set the account's asset classification to 'SMA_0'. |
| **SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA** | Update the account's SMA classification, reason, effective date, and flag indicating SMA status. |
| **SMA_CLASS_KEY, SMA_DT** | Update the customer's SMA class key and SMA date to reflect the highest SMA class and earliest SMA date among their accounts. |
| **SMA_REASON** | Set the SMA reason to 'DEGRADE BY INT NOT SERVICED'. |

# Business Rules

## Rule: An account has more than 30 days overdrawn or any overdue days.

**Applies to:** `Not specified`
**Business meaning:** Include the account for SMA evaluation by preparing its delinquency parameters for further processing.

### Eligibility
- An account has more than 30 days overdrawn or any overdue days.

### Decision Logic
| Condition | Outcome |
|---|---|
| An account has more than 30 days overdrawn or any overdue days. | Include the account for SMA evaluation by preparing its delinquency parameters for further processing. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #1).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Any delinquency parameter (interest not serviced, no credit, overdrawn, overdue, renewal, stock statement) is negative.

**Applies to:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt`
**Business meaning:** Set the negative delinquency parameter to zero to ensure only valid, non-negative values are used for SMA classification.

### Eligibility
- Any delinquency parameter (interest not serviced, no credit, overdrawn, overdue, renewal, stock statement) is negative.

### Decision Logic
| Condition | Outcome |
|---|---|
| Any delinquency parameter (interest not serviced, no credit, overdrawn, overdue, renewal, stock statement) is negative. | Set the negative delinquency parameter to zero to ensure only valid, non-negative values are used for SMA classification. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #2).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: Multiple delinquency parameters exist for an account.

**Applies to:** `DPD_Max`
**Business meaning:** Set the maximum delinquency days (DPD_Max) to the highest value among all delinquency parameters for the account.

### Eligibility
- Multiple delinquency parameters exist for an account.

### Decision Logic
| Condition | Outcome |
|---|---|
| Multiple delinquency parameters exist for an account. | Set the maximum delinquency days (DPD_Max) to the highest value among all delinquency parameters for the account. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #3).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The maximum delinquency days (DPD_Max) for an account is between 1 and 30.

**Applies to:** `SMA_CLASS`
**Business meaning:** Set the account's asset classification to 'SMA_0'.

### Eligibility
- The maximum delinquency days (DPD_Max) for an account is between 1 and 30.

### Decision Logic
| Condition | Outcome |
|---|---|
| The maximum delinquency days (DPD_Max) for an account is between 1 and 30. | Set the account's asset classification to 'SMA_0'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #4).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The maximum delinquency days (DPD_Max) for an account is between 31 and 60.

**Applies to:** `SMA_CLASS`
**Business meaning:** Set the account's asset classification to 'SMA_1'.

### Eligibility
- The maximum delinquency days (DPD_Max) for an account is between 31 and 60.

### Decision Logic
| Condition | Outcome |
|---|---|
| The maximum delinquency days (DPD_Max) for an account is between 31 and 60. | Set the account's asset classification to 'SMA_1'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #5).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The maximum delinquency days (DPD_Max) for an account is between 61 and 90.

**Applies to:** `SMA_CLASS`
**Business meaning:** Set the account's asset classification to 'SMA_2'.

### Eligibility
- The maximum delinquency days (DPD_Max) for an account is between 61 and 90.

### Decision Logic
| Condition | Outcome |
|---|---|
| The maximum delinquency days (DPD_Max) for an account is between 61 and 90. | Set the account's asset classification to 'SMA_2'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #6).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The maximum delinquency days (DPD_Max) for an account is greater than 90.

**Applies to:** `SMA_CLASS`
**Business meaning:** Set the account's asset classification to 'SMA_2'.

### Eligibility
- The maximum delinquency days (DPD_Max) for an account is greater than 90.

### Decision Logic
| Condition | Outcome |
|---|---|
| The maximum delinquency days (DPD_Max) for an account is greater than 90. | Set the account's asset classification to 'SMA_2'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #7).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The maximum delinquency days (DPD_Max) does not meet any SMA threshold.

**Applies to:** `SMA_CLASS`
**Business meaning:** Clear the account's SMA classification.

### Eligibility
- The maximum delinquency days (DPD_Max) does not meet any SMA threshold.

### Decision Logic
| Condition | Outcome |
|---|---|
| The maximum delinquency days (DPD_Max) does not meet any SMA threshold. | Clear the account's SMA classification. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #8).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The account is a cash credit or overdraft facility and the maximum delinquency is due to interest not serviced.

**Applies to:** `SMA_REASON`
**Business meaning:** Set the SMA reason to 'DEGRADE BY INT NOT SERVICED'.

### Eligibility
- The account is a cash credit or overdraft facility and the maximum delinquency is due to interest not serviced.

### Decision Logic
| Condition | Outcome |
|---|---|
| The account is a cash credit or overdraft facility and the maximum delinquency is due to interest not serviced. | Set the SMA reason to 'DEGRADE BY INT NOT SERVICED'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #9).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The account is a cash credit or overdraft facility and the maximum delinquency is due to no credit.

**Applies to:** `SMA_REASON`
**Business meaning:** Set the SMA reason to 'DEGRADE BY NO CREDIT'.

### Eligibility
- The account is a cash credit or overdraft facility and the maximum delinquency is due to no credit.

### Decision Logic
| Condition | Outcome |
|---|---|
| The account is a cash credit or overdraft facility and the maximum delinquency is due to no credit. | Set the SMA reason to 'DEGRADE BY NO CREDIT'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #10).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The account is a term loan, demand loan, bill purchase, bill discount, or packing credit and the maximum delinquency is due to overdue.

**Applies to:** `SMA_REASON`
**Business meaning:** Set the SMA reason to 'DEGRADE BY OVERDUE'.

### Eligibility
- The account is a term loan, demand loan, bill purchase, bill discount, or packing credit and the maximum delinquency is due to overdue.

### Decision Logic
| Condition | Outcome |
|---|---|
| The account is a term loan, demand loan, bill purchase, bill discount, or packing credit and the maximum delinquency is due to overdue. | Set the SMA reason to 'DEGRADE BY OVERDUE'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #11).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The account is a cash credit or overdraft facility and the maximum delinquency is due to continuous excess for more than 30 days.

**Applies to:** `SMA_REASON`
**Business meaning:** Set the SMA reason to 'DEGRADE BY CONTI EXCESS'.

### Eligibility
- The account is a cash credit or overdraft facility and the maximum delinquency is due to continuous excess for more than 30 days.

### Decision Logic
| Condition | Outcome |
|---|---|
| The account is a cash credit or overdraft facility and the maximum delinquency is due to continuous excess for more than 30 days. | Set the SMA reason to 'DEGRADE BY CONTI EXCESS'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #12).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The account is a cash credit or overdraft facility and the maximum delinquency is due to stock statement.

**Applies to:** `SMA_REASON`
**Business meaning:** Set the SMA reason to 'DEGRADE BY STOCK STATEMENT'.

### Eligibility
- The account is a cash credit or overdraft facility and the maximum delinquency is due to stock statement.

### Decision Logic
| Condition | Outcome |
|---|---|
| The account is a cash credit or overdraft facility and the maximum delinquency is due to stock statement. | Set the SMA reason to 'DEGRADE BY STOCK STATEMENT'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #13).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The account is a cash credit or overdraft facility and the maximum delinquency is due to review due date.

**Applies to:** `SMA_REASON`
**Business meaning:** Set the SMA reason to 'DEGRADE BY REVIEW DUE DATE'.

### Eligibility
- The account is a cash credit or overdraft facility and the maximum delinquency is due to review due date.

### Decision Logic
| Condition | Outcome |
|---|---|
| The account is a cash credit or overdraft facility and the maximum delinquency is due to review due date. | Set the SMA reason to 'DEGRADE BY REVIEW DUE DATE'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #14).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: None of the specific SMA reasons apply for the account.

**Applies to:** `SMA_REASON`
**Business meaning:** Set the SMA reason to 'OTHER'.

### Eligibility
- None of the specific SMA reasons apply for the account.

### Decision Logic
| Condition | Outcome |
|---|---|
| None of the specific SMA reasons apply for the account. | Set the SMA reason to 'OTHER'. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #15).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account is classified as SMA and meets all eligibility criteria (not under processing, valid asset class, positive balance, not always standard, and has relevant delinquency).

**Applies to:** `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA`
**Business meaning:** Update the account's SMA classification, reason, effective date, and flag indicating SMA status.

### Eligibility
- An account is classified as SMA and meets all eligibility criteria (not under processing, valid asset class, positive balance, not always standard, and has relevant delinquency).

### Decision Logic
| Condition | Outcome |
|---|---|
| An account is classified as SMA and meets all eligibility criteria (not under processing, valid asset class, positive balance, not always standard, and has relevant delinquency). | Update the account's SMA classification, reason, effective date, and flag indicating SMA status. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #16).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer has at least one account flagged as SMA.

**Applies to:** `FLGSMA`
**Business meaning:** Update the customer's SMA flag to indicate SMA status.

### Eligibility
- A customer has at least one account flagged as SMA.

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer has at least one account flagged as SMA. | Update the customer's SMA flag to indicate SMA status. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #17).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer has at least one account flagged as SMA. [Needs Review]

**Applies to:** `SMA_CLASS_KEY, SMA_DT`
**Business meaning:** Update the customer's SMA class key and SMA date to reflect the highest SMA class and earliest SMA date among their accounts.

### Eligibility
- A customer has at least one account flagged as SMA.

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer has at least one account flagged as SMA. | Update the customer's SMA class key and SMA date to reflect the highest SMA class and earliest SMA date among their accounts. |

### Tie / Priority Handling
- Needs Review

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer's UCIF_ID is associated with at least one account flagged as SMA.

**Applies to:** `FLGSMA, SMA_CLASS_KEY, SMA_DT`
**Business meaning:** Update the customer's SMA flag, SMA class key, and SMA date at the UCIF level.

### Eligibility
- A customer's UCIF_ID is associated with at least one account flagged as SMA.

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer's UCIF_ID is associated with at least one account flagged as SMA. | Update the customer's SMA flag, SMA class key, and SMA date at the UCIF level. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #19).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A customer's asset class or SMA class key changes.

**Applies to:** `CustMoveDescription`
**Business meaning:** Update the customer's movement description to reflect the new classification (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS', 'SMA_0', 'SMA_1', 'SMA_2').

### Eligibility
- A customer's asset class or SMA class key changes.

### Decision Logic
| Condition | Outcome |
|---|---|
| A customer's asset class or SMA class key changes. | Update the customer's movement description to reflect the new classification (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS', 'SMA_0', 'SMA_1', 'SMA_2'). |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #20).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An account's final asset class key is set and SMA class is not already assigned.

**Applies to:** `SMA_CLASS`
**Business meaning:** Assign the corresponding asset classification (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') to the account.

### Eligibility
- An account's final asset class key is set and SMA class is not already assigned.

### Decision Logic
| Condition | Outcome |
|---|---|
| An account's final asset class key is set and SMA class is not already assigned. | Assign the corresponding asset classification (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') to the account. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #21).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A new SMA status is determined for an account. [Needs Review]

**Applies to:** `PREVSTATUS, CURRENTSTATUS`
**Business meaning:** Record the previous and current SMA status for the account in the SMA movement history for audit and compliance tracking.

### Eligibility
- A new SMA status is determined for an account.

### Decision Logic
| Condition | Outcome |
|---|---|
| A new SMA status is determined for an account. | Record the previous and current SMA status for the account in the SMA movement history for audit and compliance tracking. |

### Tie / Priority Handling
- Needs Review

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: A new account or customer movement is detected (change in status or new entry).

**Applies to:** `EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate`
**Business meaning:** Insert a new record into the account or customer movement history, capturing the effective dates, movement status, and outstanding amounts.

### Eligibility
- A new account or customer movement is detected (change in status or new entry).

### Decision Logic
| Condition | Outcome |
|---|---|
| A new account or customer movement is detected (change in status or new entry). | Insert a new record into the account or customer movement history, capturing the effective dates, movement status, and outstanding amounts. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #23).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: An existing movement history record has an open-ended effective to date and a new movement is detected.

**Applies to:** `EffectiveToTimeKey, MovementToDate`
**Business meaning:** Update the existing movement history record to close it by setting the effective to date and movement to date to the day before the new movement.

### Eligibility
- An existing movement history record has an open-ended effective to date and a new movement is detected.

### Decision Logic
| Condition | Outcome |
|---|---|
| An existing movement history record has an open-ended effective to date and a new movement is detected. | Update the existing movement history record to close it by setting the effective to date and movement to date to the day before the new movement. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #24).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

## Rule: The SMA marking process completes successfully.

**Applies to:** `COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT`
**Business meaning:** Update the process status to indicate completion and increment the process count.

### Eligibility
- The SMA marking process completes successfully.

### Decision Logic
| Condition | Outcome |
|---|---|
| The SMA marking process completes successfully. | Update the process status to indicate completion and increment the process count. |

### Tie / Priority Handling
- Preserve the extracted order of this rule relative to the surrounding rules (rule #25).

### Default
- No source-confirmed default was extracted.

### When Not Eligible
- When the eligibility condition is not met, the stated outcome does not apply.

**Source Traceability:** see the collapsible mapping below.

# Business Rule Summary

| Rule | Output | Business Purpose |
|---|---|---|
| An account has more than 30 days overdrawn or any overdue days. | `Not specified` | Include the account for SMA evaluation by preparing its delinquency parameters for further processing. |
| Any delinquency parameter (interest not serviced, no credit, overdrawn, overdue, renewal, stock statement) is negative. | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | Set the negative delinquency parameter to zero to ensure only valid, non-negative values are used for SMA classification. |
| Multiple delinquency parameters exist for an account. | `DPD_Max` | Set the maximum delinquency days (DPD_Max) to the highest value among all delinquency parameters for the account. |
| The maximum delinquency days (DPD_Max) for an account is between 1 and 30. | `SMA_CLASS` | Set the account's asset classification to 'SMA_0'. |
| The maximum delinquency days (DPD_Max) for an account is between 31 and 60. | `SMA_CLASS` | Set the account's asset classification to 'SMA_1'. |
| The maximum delinquency days (DPD_Max) for an account is between 61 and 90. | `SMA_CLASS` | Set the account's asset classification to 'SMA_2'. |
| The maximum delinquency days (DPD_Max) for an account is greater than 90. | `SMA_CLASS` | Set the account's asset classification to 'SMA_2'. |
| The maximum delinquency days (DPD_Max) does not meet any SMA threshold. | `SMA_CLASS` | Clear the account's SMA classification. |
| The account is a cash credit or overdraft facility and the maximum delinquency is due to interest not serviced. | `SMA_REASON` | Set the SMA reason to 'DEGRADE BY INT NOT SERVICED'. |
| The account is a cash credit or overdraft facility and the maximum delinquency is due to no credit. | `SMA_REASON` | Set the SMA reason to 'DEGRADE BY NO CREDIT'. |
| The account is a term loan, demand loan, bill purchase, bill discount, or packing credit and the maximum delinquency is due to overdue. | `SMA_REASON` | Set the SMA reason to 'DEGRADE BY OVERDUE'. |
| The account is a cash credit or overdraft facility and the maximum delinquency is due to continuous excess for more than 30 days. | `SMA_REASON` | Set the SMA reason to 'DEGRADE BY CONTI EXCESS'. |
| The account is a cash credit or overdraft facility and the maximum delinquency is due to stock statement. | `SMA_REASON` | Set the SMA reason to 'DEGRADE BY STOCK STATEMENT'. |
| The account is a cash credit or overdraft facility and the maximum delinquency is due to review due date. | `SMA_REASON` | Set the SMA reason to 'DEGRADE BY REVIEW DUE DATE'. |
| None of the specific SMA reasons apply for the account. | `SMA_REASON` | Set the SMA reason to 'OTHER'. |
| An account is classified as SMA and meets all eligibility criteria (not under processing, valid asset class, positive balance, not always standard, and has relevant delinquency). | `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA` | Update the account's SMA classification, reason, effective date, and flag indicating SMA status. |
| A customer has at least one account flagged as SMA. | `FLGSMA` | Update the customer's SMA flag to indicate SMA status. |
| A customer has at least one account flagged as SMA. | `SMA_CLASS_KEY, SMA_DT` | Update the customer's SMA class key and SMA date to reflect the highest SMA class and earliest SMA date among their accounts. |
| A customer's UCIF_ID is associated with at least one account flagged as SMA. | `FLGSMA, SMA_CLASS_KEY, SMA_DT` | Update the customer's SMA flag, SMA class key, and SMA date at the UCIF level. |
| A customer's asset class or SMA class key changes. | `CustMoveDescription` | Update the customer's movement description to reflect the new classification (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS', 'SMA_0', 'SMA_1', 'SMA_2'). |
| An account's final asset class key is set and SMA class is not already assigned. | `SMA_CLASS` | Assign the corresponding asset classification (e.g., 'STD', 'SUB', 'DB1', 'DB2', 'DB3', 'LOS') to the account. |
| A new SMA status is determined for an account. | `PREVSTATUS, CURRENTSTATUS` | Record the previous and current SMA status for the account in the SMA movement history for audit and compliance tracking. |
| A new account or customer movement is detected (change in status or new entry). | `EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate` | Insert a new record into the account or customer movement history, capturing the effective dates, movement status, and outstanding amounts. |
| An existing movement history record has an open-ended effective to date and a new movement is detected. | `EffectiveToTimeKey, MovementToDate` | Update the existing movement history record to close it by setting the effective to date and movement to date to the day before the new movement. |
| The SMA marking process completes successfully. | `COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT` | Update the process status to indicate completion and increment the process count. |

# Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|
| 1 | An account has more than 30 days overdrawn or any overdue days. | isnull(A.DPD_Overdrawn,0)>30   OR  Isnull(A.DPD_Overdue,0)>0 | 04_batch3_nested_block:batch3_nested_block | conditions[1]: isnull(A.DPD_Overdrawn,0)>30   OR  Isnull(A.DPD_Overdue,0)>0 -> Row from PRO.AccountCal included in #DPD; tables_read[2]: `PRO.AccountCal` | columns: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_Overdrawn, DPD_Overdue | isnull(A.DPD_Overdrawn,0)>30 OR Isnull(A.DPD_Overdue,0)>0; tables_written[0]: `#DPD` | INSERT | columns: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_MAX | isnull(A.DPD_Overdrawn,0)>30 OR Isnull(A.DPD_Overdue,0)>0 | Verified |
| 2 | Any delinquency parameter (interest not serviced, no credit, overdrawn, overdue, renewal, stock statement) is negative. | isnull(DPD_IntService,0)<0; isnull(DPD_NoCredit,0)<0; isnull(DPD_Overdrawn,0)<0; isnull(DPD_Overdue,0)<0; isnull(DPD_Renewal,0)<0; isnull(DPD_StockStmt,0)<0 | 04_batch3_nested_block:batch3_nested_block | conditions[2]: isnull(DPD_IntService,0)<0 -> UPDATE #DPD SET DPD_IntService=0; tables_written[1]: `#DPD` | UPDATE | columns: DPD_IntService | isnull(DPD_IntService,0)<0; calculations[0]: metric not specified | explanation not specified; conditions[3]: isnull(DPD_NoCredit,0)<0 -> UPDATE #DPD SET DPD_NoCredit=0; tables_written[2]: `#DPD` | UPDATE | columns: DPD_NoCredit | isnull(DPD_NoCredit,0)<0; calculations[1]: metric not specified | explanation not specified; conditions[4]: isnull(DPD_Overdrawn,0)<0 -> UPDATE #DPD SET DPD_Overdrawn=0; tables_written[3]: `#DPD` | UPDATE | columns: DPD_Overdrawn | isnull(DPD_Overdrawn,0)<0; calculations[2]: metric not specified | explanation not specified; conditions[5]: isnull(DPD_Overdue,0)<0 -> UPDATE #DPD SET DPD_Overdue=0; tables_written[4]: `#DPD` | UPDATE | columns: DPD_Overdue | isnull(DPD_Overdue,0)<0; calculations[3]: metric not specified | explanation not specified; conditions[6]: isnull(DPD_Renewal,0)<0 -> UPDATE #DPD SET DPD_Renewal=0; tables_written[5]: `#DPD` | UPDATE | columns: DPD_Renewal | isnull(DPD_Renewal,0)<0; calculations[4]: metric not specified | explanation not specified; conditions[7]: isnull(DPD_StockStmt,0)<0 -> UPDATE #DPD SET DPD_StockStmt=0; tables_written[6]: `#DPD` | UPDATE | columns: DPD_StockStmt | isnull(DPD_StockStmt,0)<0; calculations[5]: metric not specified | explanation not specified | Verified |
| 3 | Multiple delinquency parameters exist for an account. | (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND ...); (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND ...); (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0) AND ...); (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0) AND ...) | 04_batch3_nested_block:batch3_nested_block | conditions[10]: (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_StockStmt,0)) -> A.DPD_Max = isnull(A.DPD_IntService,0); conditions[11]: (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_StockStmt,0)) -> A.DPD_Max = isnull(A.DPD_NoCredit,0); conditions[12]: (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_StockStmt,0)) -> A.DPD_Max = isnull(A.DPD_Overdrawn,0); conditions[13]: (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_StockStmt,0)) -> A.DPD_Max = isnull(A.DPD_Renewal,0) | Verified |
| 4 | The maximum delinquency days (DPD_Max) for an account is between 1 and 30. | dpd.DPD_Max  BETWEEN 1 AND 30; A.SMA_CLASS='SMA_0' | 04_batch3_nested_block_1:batch3_nested_block | conditions[15]: dpd.DPD_Max  BETWEEN 1 AND 30 -> A.SMA_CLASS='SMA_0'; calculations[8]: metric not specified | explanation not specified | Verified |
| 5 | The maximum delinquency days (DPD_Max) for an account is between 31 and 60. | dpd.DPD_Max  BETWEEN 31 AND 60; A.SMA_CLASS='SMA_1' | 04_batch3_nested_block_1:batch3_nested_block | conditions[16]: dpd.DPD_Max  BETWEEN 31 AND 60 -> A.SMA_CLASS='SMA_1'; calculations[8]: metric not specified | explanation not specified | Verified |
| 6 | The maximum delinquency days (DPD_Max) for an account is between 61 and 90. | dpd.DPD_Max  BETWEEN 61 AND 90; A.SMA_CLASS='SMA_2' | 04_batch3_nested_block_1:batch3_nested_block | conditions[17]: dpd.DPD_Max  BETWEEN 61 AND 90 -> A.SMA_CLASS='SMA_2'; calculations[8]: metric not specified | explanation not specified; conditions[18]: dpd.DPD_Max >90 -> A.SMA_CLASS='SMA_2' | Verified |
| 7 | The maximum delinquency days (DPD_Max) for an account is greater than 90. | dpd.DPD_Max >90; A.SMA_CLASS='SMA_2' | 04_batch3_nested_block_1:batch3_nested_block | conditions[18]: dpd.DPD_Max >90 -> A.SMA_CLASS='SMA_2'; calculations[8]: metric not specified | explanation not specified; conditions[17]: dpd.DPD_Max  BETWEEN 61 AND 90 -> A.SMA_CLASS='SMA_2' | Verified |
| 8 | The maximum delinquency days (DPD_Max) does not meet any SMA threshold. | A.SMA_CLASS=NULL | 04_batch3_nested_block_1:batch3_nested_block | conditions[18]: dpd.DPD_Max >90 -> A.SMA_CLASS='SMA_2' | Verified |
| 9 | The account is a cash credit or overdraft facility and the maximum delinquency is due to interest not serviced. | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON='DEGRADE BY INT NOT SERVICED' | 04_batch3_nested_block_1:batch3_nested_block | conditions[19]: A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) -> A.SMA_REASON='DEGRADE BY INT NOT SERVICED'; calculations[9]: metric not specified | explanation not specified | Verified |
| 10 | The account is a cash credit or overdraft facility and the maximum delinquency is due to no credit. | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON='DEGRADE BY NO CREDIT' | 04_batch3_nested_block_1:batch3_nested_block | conditions[20]: A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) -> A.SMA_REASON='DEGRADE BY NO CREDIT'; calculations[9]: metric not specified | explanation not specified | Verified |
| 11 | The account is a term loan, demand loan, bill purchase, bill discount, or packing credit and the maximum delinquency is due to overdue. | A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON='DEGRADE BY OVERDUE' | 04_batch3_nested_block_1:batch3_nested_block | conditions[21]: A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) -> A.SMA_REASON='DEGRADE BY OVERDUE'; calculations[9]: metric not specified | explanation not specified | Verified |
| 12 | The account is a cash credit or overdraft facility and the maximum delinquency is due to continuous excess for more than 30 days. | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30; A.SMA_REASON='DEGRADE BY CONTI EXCESS' | 04_batch3_nested_block_1:batch3_nested_block | conditions[22]: A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 -> A.SMA_REASON='DEGRADE BY CONTI EXCESS'; calculations[9]: metric not specified | explanation not specified | Verified |
| 13 | The account is a cash credit or overdraft facility and the maximum delinquency is due to stock statement. | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON='DEGRADE BY STOCK STATEMENT' | 04_batch3_nested_block_1:batch3_nested_block | conditions[23]: A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) -> A.SMA_REASON='DEGRADE BY STOCK STATEMENT'; calculations[9]: metric not specified | explanation not specified | Verified |
| 14 | The account is a cash credit or overdraft facility and the maximum delinquency is due to review due date. | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0); A.SMA_REASON='DEGRADE BY REVIEW DUE DATE' | 04_batch3_nested_block_1:batch3_nested_block | conditions[24]: A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) -> A.SMA_REASON='DEGRADE BY REVIEW DUE DATE'; calculations[9]: metric not specified | explanation not specified | Verified |
| 15 | None of the specific SMA reasons apply for the account. | ELSE 'OTHER' | 04_batch3_nested_block_1:batch3_nested_block | calculations[9]: metric not specified | explanation not specified | Verified |
| 16 | An account is classified as SMA and meets all eligibility criteria (not under processing, valid asset class, positive balance, not always standard, and has relevant delinquency). | ISNULL(B.FLGPROCESSING,'N')='N'; ISNULL(FINALASSETCLASSALT_KEY,1)=1; ISNULL(A.BALANCE,0)>0; A.ASSET_NORM<>'ALWYS_STD'; ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 ); ISNULL(DPD.DPD_MAX,0)>0 | 04_batch3_nested_block_1:batch3_nested_block | conditions[25]: ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 -> UPDATE PRO.ACCOUNTCAL; tables_written[11]: `PRO.ACCOUNTCAL` | UPDATE | columns: SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA | ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0  OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 | Verified |
| 17 | A customer has at least one account flagged as SMA. | B.FLGSMA='Y' | 04_batch3_nested_block_2:batch3_nested_block | tables_written[13]: `PRO.CUSTOMERCAL` | UPDATE | columns: FLGSMA | A.CustomerEntityID =B.CustomerEntityID AND B.FLGSMA='Y'; tables_written[15]: `PRO.CUSTOMERCAL` | UPDATE | columns: FLGSMA | A.UCIF_ID =B.UCIF_ID AND B.FLGSMA='Y' | Verified |
| 18 | A customer has at least one account flagged as SMA. | MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 ...); MIN(A.SMA_Dt) AS SMA_Dt | 04_batch3_nested_block_2:batch3_nested_block | calculations[11]: metric not specified | explanation not specified | Could not trace the stated source evidence back to a successfully parsed technical extraction record: MIN(A.SMA_Dt) AS SMA_Dt |
| 19 | A customer's UCIF_ID is associated with at least one account flagged as SMA. | A.UCIF_ID =B.UCIF_ID AND B.FLGSMA='Y' | 04_batch3_nested_block_2:batch3_nested_block | tables_written[15]: `PRO.CUSTOMERCAL` | UPDATE | columns: FLGSMA | A.UCIF_ID =B.UCIF_ID AND B.FLGSMA='Y' | Verified |
| 20 | A customer's asset class or SMA class key changes. | SYSASSETCLASSALT_KEY=1; SYSASSETCLASSALT_KEY=2; SYSASSETCLASSALT_KEY=3; SYSASSETCLASSALT_KEY=4; SYSASSETCLASSALT_KEY=5; SYSASSETCLASSALT_KEY=6; SMA_CLASS_KEY=1; SMA_CLASS_KEY=2; SMA_CLASS_KEY=3 | 04_batch3_nested_block_3:batch3_nested_block | tables_written[21]: `PRO.CUSTOMERCAL` | UPDATE | columns: CustMoveDescription | SYSASSETCLASSALT_KEY=1; tables_written[22]: `PRO.CUSTOMERCAL` | UPDATE | columns: CustMoveDescription | SYSASSETCLASSALT_KEY=2; tables_written[23]: `PRO.CUSTOMERCAL` | UPDATE | columns: CustMoveDescription | SYSASSETCLASSALT_KEY=3; tables_written[24]: `PRO.CUSTOMERCAL` | UPDATE | columns: CustMoveDescription | SYSASSETCLASSALT_KEY=4; tables_written[25]: `PRO.CUSTOMERCAL` | UPDATE | columns: CustMoveDescription | SYSASSETCLASSALT_KEY=5; tables_written[26]: `PRO.CUSTOMERCAL` | UPDATE | columns: CustMoveDescription | SYSASSETCLASSALT_KEY=6; tables_written[27]: `PRO.CUSTOMERCAL` | UPDATE | columns: CustMoveDescription | SMA_CLASS_KEY=1; tables_written[28]: `PRO.CUSTOMERCAL` | UPDATE | columns: CustMoveDescription | SMA_CLASS_KEY=2; tables_written[29]: `PRO.CUSTOMERCAL` | UPDATE | columns: CustMoveDescription | SMA_CLASS_KEY=3 | Verified |
| 21 | An account's final asset class key is set and SMA class is not already assigned. | FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL; FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL | 04_batch3_nested_block_3:batch3_nested_block | tables_written[30]: `PRO.AccountCal` | UPDATE | columns: SMA_CLASS | FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL; tables_written[31]: `PRO.AccountCal` | UPDATE | columns: SMA_CLASS | FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL; tables_written[32]: `PRO.AccountCal` | UPDATE | columns: SMA_CLASS | FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL; tables_written[33]: `PRO.AccountCal` | UPDATE | columns: SMA_CLASS | FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL; tables_written[34]: `PRO.AccountCal` | UPDATE | columns: SMA_CLASS | FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL; tables_written[35]: `PRO.AccountCal` | UPDATE | columns: SMA_CLASS | FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL | Verified |
| 22 | A new SMA status is determined for an account. | INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) | Not cited | Not cited | Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS) |
| 23 | A new account or customer movement is detected (change in status or new entry). | INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY; INSERT INTO PRO.CUSTOMER_MOVEMENT_HISTORY | 04_batch3_nested_block_3:batch3_nested_block; 04_batch3_nested_block_4:batch3_nested_block | conditions[30]: EXISTS  ( select  1  from PRO.ACCOUNT_MOVEMENT_HISTORY where  [EffectiveFromTimeKey]= @Timekey) -> print 'NO NEDD TO INSERT DATA'; conditions[34]: EXISTS  ( select  1  from PRO.CUSTOMER_MOVEMENT_HISTORY where  [EffectiveFromTimeKey]= @Timekey) -> print 'NO NEDD TO INSERT DATA' | Verified |
| 24 | An existing movement history record has an open-ended effective to date and a new movement is detected. | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null; AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) | 04_batch3_nested_block_4:batch3_nested_block | conditions[32]: AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null -> UPDATE AA SET EffectiveToTimeKey = @vEffectiveto, MovementToDate=DATEADD(DD,-1,@ProcessDate); tables_read[18]: `PRO.ACCOUNT_MOVEMENT_HISTORY` | columns: CustomerAcID, EffectiveToTimeKey | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null; tables_written[38]: `PRO.ACCOUNT_MOVEMENT_HISTORY` | UPDATE | columns: EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null; conditions[33]: AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) -> UPDATE AA SET EffectiveToTimeKey = @vEffectiveto, MovementToDate=DATEADD(DD,-1,@ProcessDate); tables_read[20]: `PRO.ACCOUNT_MOVEMENT_HISTORY` | columns: CustomerAcID, EffectiveToTimeKey, EffectiveFROMTimeKey, MOVEMENTTOSTATUS | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS); tables_written[39]: `PRO.ACCOUNT_MOVEMENT_HISTORY` | UPDATE | columns: EffectiveToTimeKey, MovementToDate | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID=BB.CustomerAcID AND BB.EffectiveToTimeKey =49999 AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS) | Verified |
| 25 | The SMA marking process completes successfully. | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 | 04_batch3_nested_block_5:batch3_nested_block | conditions[39]: RUNNINGPROCESSNAME='SMA_MARKING' -> UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1; calculations[20]: metric not specified | explanation not specified | Verified |

_Source evidence is the literal technical text carried through the pipeline; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails._
</details>

## Calculations / Formulas

- **Maximum delinquency days (DPD_Max):** For each account, DPD_Max is set to the highest value among interest not serviced days, no credit days, overdrawn days, overdue days, renewal days, and stock statement days.
- **SMA classification:** SMA_0 is assigned if DPD_Max is between 1 and 30 days, SMA_1 if between 31 and 60 days, and SMA_2 if 61 days or more.
- **SMA reason:** The reason for SMA classification is determined by which delinquency parameter matches DPD_Max and the facility type (e.g., interest not serviced for CC/OD, overdue for TL/DL/BP/BD/PC, etc.).
- **SMA effective date:** The effective date for SMA classification is calculated as the process date minus DPD_Max plus one day.
- **Customer SMA class key:** The highest SMA class among all accounts for a customer is mapped numerically (SMA_0=1, SMA_1=2, SMA_2=3) and stored as the customer's SMA class key.

## Exception Handling Behavior

If an error occurs during processing, the procedure records the failure in the process status table, including the error date and description, and increments the process count. Temporary tables are dropped to ensure no residual data remains, minimizing the risk of inconsistent or partial updates.

## Rule Provenance Summary

**Technical Implementation:** derived directly from the parsed source code and the per-chunk technical extraction (conditions, table reads/writes, calculations) - see Tables Read/Written above.

**Business Interpretation:** the Purpose Summary, Step-by-Step Logic Flow, and Business Rules sections translate that technical implementation into plain business language; the breakdown below shows how much of that interpretation is a direct restatement versus an inference or an assumption.

- **Total business rules:** 25
- **By rule type:** explicit = 25
- **By validation status:** insufficient_evidence = 1, unverified = 1, verified = 23

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Ambiguities / Needs Review

- Parameter extraction failed for a parameterized object header; the object is not known to be parameterless.
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
- There is commented-out logic related to updating movement dates using a calendar table, which is not active in the current process and may affect the accuracy of movement history dates if reactivated.
- Parameter extraction failed, so the exact business role of input parameters could not be confirmed and may require review.
- Some code comments and inactive branches suggest alternative or legacy SMA classification logic, but only the currently active logic is reflected in these business rules.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MIN(A.SMA_Dt) AS SMA_Dt
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS)
