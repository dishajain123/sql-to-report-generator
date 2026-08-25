# SMA_MARKING — Business Logic Report

> This procedure automates the identification and marking of Special Mention Accounts (SMA) for advances, in line with regulatory and internal policy requirements.

## 1. At a Glance

| Item | Details |
|---|---|
| Object | `SMA_MARKING` |
| Type | Procedure |
| SQL Dialect | SQL Server T-SQL |
| Parameters | `@TIMEKEY` (IN, INT) |
| Primary Business Entity | Account → Customer |
| Tables Updated | `##ACCOUNTCAL`, `#DPD`, `##CUSTOMERCAL`, `PRO.SMA_MOVEMENT_HISTORY`, `#SMACLASS`, `PRO.PREVSMASTATUS` |
| Business Rules Identified | 14 |

## 2. What This Procedure Does

### In Simple Terms

This procedure automates the identification and marking of Special Mention Accounts (SMA) for advances, in line with regulatory and internal policy requirements. It calculates overdue and non-serviced periods for various account attributes, assigns the appropriate SMA classification and reason, and updates both account-level and customer-level movement history for audit and compliance tracking. The process ensures that asset classification is consistent, accurate, and traceable for regulatory reporting and internal monitoring.

### Business Outcome

After this procedure completes, the following fields have been evaluated and, where applicable, updated:

- `ContiExcessDt`
- `ReviewDueDt`
- `DPD_Max`
- `SMA_CLASS`
- `SMA_REASON`
- `SMA_DT`
- `FLGSMA`
- `SMA_CLASS_KEY`

## 3. End-to-End Business Flow

1. Determine the processing date and effective period for the SMA marking run.
2. Identify accounts under the Aqua Scheme with specific product and facility types, and prepare temporary data for DPD (Days Past Due) calculations.
3. For accounts with overdrawn DPD less than or equal to 30 days, reset the continuous excess date and set the overdrawn DPD to zero.
4. For accounts with negative DPD values in any DPD attribute, reset those DPD values to zero to ensure no negative overdue calculations.
5. Calculate the maximum DPD across all relevant DPD attributes for each account.
6. Clear previous SMA classification fields before recalculating.
7. Assign the SMA classification, reason, and date to eligible accounts based on the maximum DPD and facility type.
8. Update customer-level SMA status and movement history based on the most severe account-level SMA classification.
9. Update movement history tables for both accounts and customers to reflect any changes in SMA status, ensuring effective dating and closure of previous records.
10. Update process status and handle any errors by marking the process as incomplete and logging error details.

## 4. Eligibility — Who / What Gets Evaluated

The extracted business rules reference the following eligibility conditions (gathered from each rule's own eligibility criteria; see the Business Rules section below for which condition applies to which rule):

- DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, or DPD_StockStmt is less than zero
- Account is in Aqua Scheme
- DPD_Overdrawn <= 30
- DPD_Overdrawn > 0 or DPD_Overdue > 0
- All accounts before SMA marking
- Account is not under processing
- FinalAssetClassAlt_Key = 1
- Balance > 0
- ASSET_NORM <> 'ALWYS_STD'
- DPD_Overdrawn >= 0 or DPD_Overdue >= 0
- DPD_Max > 0
- Customer has at least one account with FLGSMA = 'Y'
- SMA_CLASS is null
- FinalAssetClassAlt_Key = 2
- FinalAssetClassAlt_Key in (3,4,5)

## 5. Business Rules

## Rule: Reset negative DPD values to zero

**Applies to:** `Not specified`
**Business meaning:** Any negative Days Past Due (DPD) values for interest servicing, no credit, overdrawn, overdue, renewal, or stock statement are reset to zero to prevent invalid overdue calculations.

### Eligibility
- DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, or DPD_StockStmt is less than zero

### Decision Logic
| Condition | Outcome |
|---|---|
| DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, or DPD_StockStmt is less than zero | Any negative Days Past Due (DPD) values for interest servicing, no credit, overdrawn, overdue, renewal, or stock statement are reset to zero to prevent invalid overdue calculations. |


## Rule: Reset Aqua Scheme DPD fields if overdrawn DPD is low

**Applies to:** `ContiExcessDt`
**Business meaning:** For Aqua Scheme accounts with overdrawn DPD less than or equal to 30 days, the continuous excess date is cleared and the overdrawn DPD is set to zero.

### Eligibility
- Account is in Aqua Scheme
- DPD_Overdrawn <= 30

### Decision Logic
| Condition | Outcome |
|---|---|
| Account is in Aqua Scheme and DPD_Overdrawn is less than or equal to 30 | For Aqua Scheme accounts with overdrawn DPD less than or equal to 30 days, the continuous excess date is cleared and the overdrawn DPD is set to zero. |


## Rule: Reset Aqua Scheme renewal fields

**Applies to:** `ReviewDueDt`
**Business meaning:** For Aqua Scheme accounts, the review due date and renewal DPD are reset to null and zero respectively as part of the DPD update process.

### Eligibility
- Account is in Aqua Scheme

### Decision Logic
| Condition | Outcome |
|---|---|
| Account is in Aqua Scheme | For Aqua Scheme accounts, the review due date and renewal DPD are reset to null and zero respectively as part of the DPD update process. |


## Rule: Calculate maximum DPD for account [Needs Review]

**Applies to:** `DPD_Max`
**Business meaning:** The maximum DPD value among all DPD attributes is determined for each account to identify the most severe overdue situation.

### Eligibility
- DPD_Overdrawn > 0 or DPD_Overdue > 0

### Decision Logic
| Condition | Outcome |
|---|---|
| Account has any DPD_Overdrawn or DPD_Overdue greater than zero | The maximum DPD value among all DPD attributes is determined for each account to identify the most severe overdue situation. |


## Rule: Clear previous SMA classification fields

**Applies to:** `SMA_CLASS`
**Business meaning:** Before recalculating SMA status, all previous SMA classification, reason, date, and flag fields are cleared for each account.

### Eligibility
- All accounts before SMA marking

### Decision Logic
| Condition | Outcome |
|---|---|
| All accounts before SMA marking | Before recalculating SMA status, all previous SMA classification, reason, date, and flag fields are cleared for each account. |


## Rule: Assign SMA class based on DPD ladder [Needs Review]

**Applies to:** `SMA_CLASS`
**Business meaning:** Accounts are assigned an SMA classification based on the maximum DPD value, following regulatory thresholds.

### Eligibility
- Account is not under processing
- FinalAssetClassAlt_Key = 1
- Balance > 0
- ASSET_NORM <> 'ALWYS_STD'
- DPD_Overdrawn >= 0 or DPD_Overdue >= 0
- DPD_Max > 0

### Decision Logic
| Condition | Outcome |
|---|---|
| DPD_Max between 1 and 30 | SMA_0 |
| DPD_Max between 31 and 60 | SMA_1 |
| DPD_Max between 61 and 90 | SMA_2 |
| DPD_Max > 90 | SMA_2 |


## Rule: Assign SMA reason based on facility and DPD type

**Applies to:** `SMA_REASON`
**Business meaning:** The reason for SMA downgrade is set based on which DPD attribute matches the maximum DPD and the facility type, indicating the specific regulatory or operational cause.

### Eligibility
- Account is not under processing
- FinalAssetClassAlt_Key = 1
- Balance > 0
- ASSET_NORM <> 'ALWYS_STD'
- DPD_Overdrawn >= 0 or DPD_Overdue >= 0
- DPD_Max > 0

### Decision Logic
| Condition | Outcome |
|---|---|
| FacilityType in ('CC','OD') and DPD_INTSERVICE = DPD_MAX | DEGRADE BY INT NOT SERVICED |
| FacilityType in ('CC','OD') and DPD_NOCREDIT = DPD_MAX | DEGRADE BY NO CREDIT |
| FacilityType in ('TL','DL','BP','BD','PC') and DPD_OVERDUE = DPD_MAX | DEGRADE BY OVERDUE |
| FacilityType in ('CC','OD') and DPD_OVERDRAWN = DPD_MAX and DPD_OVERDRAWN > 30 | DEGRADE BY CONTI EXCESS |
| FacilityType in ('CC','OD') and DPD_STOCKSTMT = DPD_MAX | DEGRADE BY STOCK STATEMENT |
| FacilityType in ('CC','OD') and DPD_RENEWAL = DPD_MAX | DEGRADE BY REVIEW DUE DATE |
| Otherwise | OTHER |


## Rule: Set SMA date based on DPD_Max

**Applies to:** `SMA_DT`
**Business meaning:** The SMA date is set to the processing date minus the maximum DPD plus one, reflecting the start of the overdue period.

### Eligibility
- Account is not under processing
- FinalAssetClassAlt_Key = 1
- Balance > 0
- ASSET_NORM <> 'ALWYS_STD'
- DPD_Overdrawn >= 0 or DPD_Overdue >= 0
- DPD_Max > 0

### Decision Logic
| Condition | Outcome |
|---|---|
| Account is eligible for SMA marking and DPD_Max > 0 | The SMA date is set to the processing date minus the maximum DPD plus one, reflecting the start of the overdue period. |


## Rule: Flag account as SMA marked

**Applies to:** `FLGSMA`
**Business meaning:** Accounts that have been assigned an SMA classification are flagged as SMA marked for reporting and further processing.

### Eligibility
- Account is not under processing
- FinalAssetClassAlt_Key = 1
- Balance > 0
- ASSET_NORM <> 'ALWYS_STD'
- DPD_Overdrawn >= 0 or DPD_Overdue >= 0
- DPD_Max > 0

### Decision Logic
| Condition | Outcome |
|---|---|
| Account is eligible for SMA marking and DPD_Max > 0 | Accounts that have been assigned an SMA classification are flagged as SMA marked for reporting and further processing. |


## Rule: Update customer-level SMA class and date [Needs Review]

**Applies to:** `SMA_CLASS_KEY`
**Business meaning:** The most severe SMA classification and earliest SMA date among all accounts for a customer are assigned at the customer level for consolidated reporting.

### Eligibility
- Customer has at least one account with FLGSMA = 'Y'

### Decision Logic
| Condition | Outcome |
|---|---|
| Customer has at least one account flagged as SMA marked | The most severe SMA classification and earliest SMA date among all accounts for a customer are assigned at the customer level for consolidated reporting. |


## Rule: Assign standard asset class if missing

**Applies to:** `SMA_CLASS`
**Business meaning:** If an account's SMA classification is missing but its final asset class key indicates a standard asset, the SMA class is set to 'STD'.

### Eligibility
- FinalAssetClassAlt_Key = 1
- SMA_CLASS is null

### Decision Logic
| Condition | Outcome |
|---|---|
| FinalAssetClassAlt_Key = 1 and SMA_CLASS is null | If an account's SMA classification is missing but its final asset class key indicates a standard asset, the SMA class is set to 'STD'. |


## Rule: Assign sub-standard asset class if missing

**Applies to:** `SMA_CLASS`
**Business meaning:** If an account's SMA classification is missing but its final asset class key indicates a sub-standard asset, the SMA class is set to 'SUB'.

### Eligibility
- FinalAssetClassAlt_Key = 2
- SMA_CLASS is null

### Decision Logic
| Condition | Outcome |
|---|---|
| FinalAssetClassAlt_Key = 2 and SMA_CLASS is null | If an account's SMA classification is missing but its final asset class key indicates a sub-standard asset, the SMA class is set to 'SUB'. |


## Rule: Assign doubtful asset class if missing

**Applies to:** `SMA_CLASS`
**Business meaning:** If an account's SMA classification is missing but its final asset class key indicates a doubtful asset, the SMA class is set to the appropriate doubtful band (DB1, DB2, DB3) based on the asset class key.

### Eligibility
- FinalAssetClassAlt_Key in (3,4,5)
- SMA_CLASS is null

### Decision Logic
| Condition | Outcome |
|---|---|
| FinalAssetClassAlt_Key in (3,4,5) and SMA_CLASS is null | If an account's SMA classification is missing but its final asset class key indicates a doubtful asset, the SMA class is set to the appropriate doubtful band (DB1, DB2, DB3) based on the asset class key. |


## Rule: Assign loss asset class if missing

**Applies to:** `SMA_CLASS`
**Business meaning:** If an account's SMA classification is missing but its final asset class key indicates a loss asset, the SMA class is set to 'LOS'.

### Eligibility
- FinalAssetClassAlt_Key = 6
- SMA_CLASS is null

### Decision Logic
| Condition | Outcome |
|---|---|
| FinalAssetClassAlt_Key = 6 and SMA_CLASS is null | If an account's SMA classification is missing but its final asset class key indicates a loss asset, the SMA class is set to 'LOS'. |

## 6. Decision Logic & Rule Priority

```text
Determine the processing date and effective period for the SMA marking run.
    ↓
Identify accounts under the Aqua Scheme with specific product and facility types, and prepare temporary data for DPD (Days Past Due) calculations.
    ↓
For accounts with overdrawn DPD less than or equal to 30 days, reset the continuous excess date and set the overdrawn DPD to zero.
    ↓
For accounts with negative DPD values in any DPD attribute, reset those DPD values to zero to ensure no negative overdue calculations.
    ↓
Calculate the maximum DPD across all relevant DPD attributes for each account.
    ↓
Clear previous SMA classification fields before recalculating.
    ↓
Assign the SMA classification, reason, and date to eligible accounts based on the maximum DPD and facility type.
    ↓
Update customer-level SMA status and movement history based on the most severe account-level SMA classification.
    ↓
Update movement history tables for both accounts and customers to reflect any changes in SMA status, ensuring effective dating and closure of previous records.
    ↓
Update process status and handle any errors by marking the process as incomplete and logging error details.
```

### Rule Priority / Tie-Breaking

**Priority:** Not explicitly determined from source SQL. Rule order in this report reflects extraction order only and must not be read as a business priority.

## 7. Fallback / When Conditions Are Not Met

_Not explicitly determined from source SQL._

## 8. Roll-Up / Entity Hierarchy

```text
Account
    ↓
Customer
```

The extracted rules reference more than one level of this hierarchy. Rules mentioning each level (by name, in order first encountered):

- **Account:** Reset Aqua Scheme DPD fields if overdrawn DPD is low; Reset Aqua Scheme renewal fields; Calculate maximum DPD for account; Clear previous SMA classification fields; Assign SMA class based on DPD ladder; Flag account as SMA marked
- **Customer:** Update customer-level SMA class and date

## 9. History / Movement Tracking

```text
Previous Status
      ↓
Current Status
      ↓
Status Change?
   ↙       ↘
 Yes        No
 ↓           ↓
Record       No movement
history
```

**History / movement tables identified:** `PRO.SMA_MOVEMENT_HISTORY`, `#ACCOUNT_MOVEMENT_HISTORY`, `PRO.ACCOUNT_MOVEMENT_HISTORY`, `#Customer_MOVEMENT_HISTORY`, `PRO.CUSTOMER_MOVEMENT_HISTORY`

_Not explicitly determined from source SQL._ (no business rule was linked back to these tables)

## 10. Important Business Updates

| Table | Fields Updated | Operation(s) |
|---|---|---|
| `##ACCOUNTCAL` | A.ContiExcessDt, A.DPD_Overdrawn, A.ReviewDueDt, A.DPD_Renewal, A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA, SMA_CLASS | `UPDATE` |
| `#DPD` | DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, A.DPD_Max | `UPDATE` |
| `##CUSTOMERCAL` | A.FLGSMA, A.SMA_CLASS_KEY, A.SMA_DT, CustMoveDescription | `UPDATE` |
| `PRO.SMA_MOVEMENT_HISTORY` | TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS | `DELETE, INSERT` |
| `#SMACLASS` | SMA_CLASS | `UPDATE` |
| `PRO.PREVSMASTATUS` | Not identified | `TRUNCATE, INSERT` |
| `#ACCOUNT_MOVEMENT_HISTORY` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus | `INSERT` |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus | `INSERT, UPDATE` |
| `#Customer_MOVEMENT_HISTORY` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus | `INSERT` |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus | `INSERT, UPDATE` |
| `PRO.ACLRUNNINGPROCESSSTATUS` | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | `UPDATE` |

## 11. Technical Data Lineage

## Tables Read

| Table Name | Business Context | Filter Conditions |
|---|---|---|
| `SYSDAYMATRIX` | DATE | TIMEKEY = @TIMEKEY |
| `dbo.Automate_Advances` | Timekey-1 | EXT_FLG='Y') IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL DROP TABLE #DPD_Aqua_SMA |
| `#DPD_Aqua_SMA` | A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt, B.AccountEntityID, B.ContiExcessDt, B.DPD_Overdrawn, B.ReviewDueDt, B.DPD_Renewal | C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(C.SchemeType, '') = 'ODA' AND COALESCE(c.FacilityType, '') IN ('CC', 'OD')… _(consolidated from 3 raw references)_ |
| `##ACCOUNTCAL` | A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt, AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate | C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(C.SchemeType, '') = 'ODA' AND COALESCE(c.FacilityType, '') IN ('CC', 'OD')… _(consolidated from 12 raw references)_ |
| `DIMPRODUCT` | A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt | C.EffectiveFromTimeKey <= @TIMEKEY AND C.EffectiveToTimeKey >= @TIMEKEY AND (COALESCE(C.Aqua_Scheme, 'N') = 'Y' AND COALESCE(C.SchemeType, '') = 'ODA' AND COALESCE(c.FacilityType, '') IN ('CC', 'OD')… |
| `#DPD` | AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit | COALESCE(A.DPD_Overdrawn, 0) > 30 OR COALESCE(A.DPD_Overdue, 0) > 0; (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR… _(consolidated from 4 raw references)_ |
| `#TEMPTABLE` | A.CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.RefPeriodNoCredit, 0) THEN A.DPD_NoCredit ELSE 0 END AS DPD_NoCredit, CASE WHEN COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.RefPeriodOverDrawn, 0) THEN A.DPD_Overdrawn ELSE 0 END AS DPD_Overdrawn, CASE WHEN COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.RefPeriodOverdue, 0) THEN A.DPD_Overdue ELSE 0 END AS DPD_Overdue, CASE WHEN COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.RefPeriodReview, 0) THEN A.DPD_Renewal ELSE 0 END AS DPD_Renewal, CASE WHEN COALESCE(A.DPD_StockStmt, 0) >= COALESCE(A.RefPeriodStkStatement, 0) THEN A.DPD_StockStmt ELSE 0 END AS DPD_StockStmt | (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COA… |
| `##CUSTOMERCAL` | dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN | COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dp… _(consolidated from 6 raw references)_ |
| `AdvAcBasicDetail` | dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE, DPD.DPD_NOCREDIT, dpd.DPD_OVERDUE, dpd.DPD_OVERDRAWN | COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dp… |
| `#TEMPTABLE_SMACLASS` | A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt, B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, B.CustomerEntityID | A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y'; A.FLGSMA = 'Y'; A.CustomerEntityID = B.CustomerEntityID _(consolidated from 2 raw references)_ |
| `#TEMPTABLE_SMACLASSUcif` | A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt | A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y' |
| `PRO.SMA_MOVEMENT_HISTORY` | 1 | TIMEKEY=@TIMEKEY) BEGIN |
| `#SMACLASS` | A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS, @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS, CustomerAcID, SMA_CLASS | B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1; A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y'; NOT B.SMA_… _(consolidated from 4 raw references)_ |
| `PRO.PREVSMASTATUS` | @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS | NOT B.SMA_CLASS IS NULL AND COALESCE(A.SMA_CLASS, '') <> COALESCE(B.SMA_CLASS, ''); A.CustomerAcID = B.CustomerAcID; B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') _(consolidated from 2 raw references)_ |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | 1, A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsAcc, 0) AS TotOsAcc, A.MovementFromDate, A.MovementToDate | [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO; (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN NOT B.CustomerAcID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1; A.C… _(consolidated from 2 raw references)_ |
| `#ACCOUNT_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsAcc, 0) AS TotOsAcc, A.MovementFromDate, A.MovementToDate, AA.EffectiveToTimeKey, B.CustomerAcID | (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN NOT B.CustomerAcID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1; A.CustomerAcID = B.CustomerAcID AND B.EFFECTIVETOTimekey = 499… _(consolidated from 4 raw references)_ |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | 1, A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsCust, 0) AS TotOsCust, A.MovementFromDate, A.MovementToDate | [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO; (CASE WHEN B.SourceSystemCustomerID IS NULL THEN 1 WHEN NOT B.SourceSystemCustomerID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS… _(consolidated from 2 raw references)_ |
| `#Customer_MOVEMENT_HISTORY` | A.UCIF_ID, A.RefCustomerID, A.SourceSystemCustomerID, A.CustomerName, A.SysAssetClassAlt_Key, A.SysNPA_Dt, A.EffectiveFromTimeKey, A.EffectiveToTimeKey, COALESCE(B.MovementTOStatus, A.MovementFromStatus), A.MovementToStatus, COALESCE(A.TotOsCust, 0) AS TotOsCust, A.MovementFromDate, A.MovementToDate, AA.EffectiveToTimeKey, B.SourceSystemCustomerID | (CASE WHEN B.SourceSystemCustomerID IS NULL THEN 1 WHEN NOT B.SourceSystemCustomerID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1; A.SourceSystemCustomerID = B.SourceSystemC… _(consolidated from 4 raw references)_ |

## Tables Written

| Table Name | Operation Type | Columns Affected | Business Trigger |
|---|---|---|---|
| `##ACCOUNTCAL` | `UPDATE` | A.ContiExcessDt, A.DPD_Overdrawn, A.ReviewDueDt, A.DPD_Renewal, A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA, SMA_CLASS | COALESCE(A.DPD_Overdrawn, 0) <= 30; A.AccountEntityID = B.AccountEntityID; ISNULL(A.DPD_Overdrawn,0)<= 30 _(consolidated from 20 raw references)_ |
| `#DPD` | `UPDATE` | DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, A.DPD_Max | COALESCE(DPD_IntService, 0) < 0; COALESCE(DPD_NoCredit, 0) < 0; COALESCE(DPD_Overdrawn, 0) < 0 _(consolidated from 15 raw references)_ |
| `##CUSTOMERCAL` | `UPDATE` | A.FLGSMA, A.SMA_CLASS_KEY, A.SMA_DT, CustMoveDescription | B.FLGSMA='Y' IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL DROP TABLE #TEMPTABLE_SMACLASS; A.FLGSMA = 'Y'; A.CustomerEntityID = B.CustomerEntityID _(consolidated from 25 raw references)_ |
| `PRO.SMA_MOVEMENT_HISTORY` | `DELETE, INSERT` | TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS | TIMEKEY=@TIMEKEY _(consolidated from 2 raw references)_ |
| `#SMACLASS` | `UPDATE` | SMA_CLASS | None _(consolidated from 2 raw references)_ |
| `PRO.PREVSMASTATUS` | `TRUNCATE, INSERT` | Not identified | None _(consolidated from 2 raw references)_ |
| `#ACCOUNT_MOVEMENT_HISTORY` | `INSERT` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | None |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | `INSERT, UPDATE` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsAcc, MovementFromDate, MovementToDate | AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL; AA.CustomerAcID = B.CustomerAcID AND B.EffectiveToTimeKey = 49999; AA.EffectiveToTimeKey = 49999 and B.CustomerAcID is null _(consolidated from 4 raw references)_ |
| `#Customer_MOVEMENT_HISTORY` | `INSERT` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, totOsCust, MovementFromDate, MovementToDate | None |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | `INSERT, UPDATE` | UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt, EffectiveFromTimeKey, EffectiveToTimeKey, MovementFromStatus, MovementToStatus, TotOsCust, MovementFromDate, MovementToDate | AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL; AA.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EffectiveToTimeKey = 49999; AA.EffectiveToTimeKey = 49999 and B.SourceSy… _(consolidated from 4 raw references)_ |
| `PRO.ACLRUNNINGPROCESSSTATUS` | `UPDATE` | COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME='SMA_MARKING' _(consolidated from 2 raw references)_ |

## 12. Important Fields

| Field | Business Meaning |
|---|---|
| `@TIMEKEY` | Declared parameter (IN, INT). |
| `ContiExcessDt` | For Aqua Scheme accounts with overdrawn DPD less than or equal to 30 days, the continuous excess date is cleared and the overdrawn DPD is s… (Rule: Reset Aqua Scheme DPD fields if overdrawn DPD is low) |
| `DPD_Overdrawn` | For Aqua Scheme accounts with overdrawn DPD less than or equal to 30 days, the continuous excess date is cleared and the overdrawn DPD is s… (Rule: Reset Aqua Scheme DPD fields if overdrawn DPD is low) |
| `ReviewDueDt` | For Aqua Scheme accounts, the review due date and renewal DPD are reset to null and zero respectively as part of the DPD update process. (Rule: Reset Aqua Scheme renewal fields) |
| `DPD_Renewal` | For Aqua Scheme accounts, the review due date and renewal DPD are reset to null and zero respectively as part of the DPD update process. (Rule: Reset Aqua Scheme renewal fields) |
| `DPD_Max` | The maximum DPD value among all DPD attributes is determined for each account to identify the most severe overdue situation. (Rule: Calculate maximum DPD for account) |
| `SMA_CLASS` | Before recalculating SMA status, all previous SMA classification, reason, date, and flag fields are cleared for each account. (Rule: Clear previous SMA classification fields) |
| `SMA_REASON` | Before recalculating SMA status, all previous SMA classification, reason, date, and flag fields are cleared for each account. (Rule: Clear previous SMA classification fields) |
| `SMA_DT` | Before recalculating SMA status, all previous SMA classification, reason, date, and flag fields are cleared for each account. (Rule: Clear previous SMA classification fields) |
| `FLGSMA` | Before recalculating SMA status, all previous SMA classification, reason, date, and flag fields are cleared for each account. (Rule: Clear previous SMA classification fields) |
| `SMA_CLASS_KEY` | The most severe SMA classification and earliest SMA date among all accounts for a customer are assigned at the customer level for consolida… (Rule: Update customer-level SMA class and date) |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟢 1 | Reset negative DPD values to zero | `Not specified` | Any negative Days Past Due (DPD) values for interest servicing, no credit, overdrawn, overdue, renewal, or stock statement are reset to zer… |
| 🟢 2 | Reset Aqua Scheme DPD fields if overdrawn DPD is low | `ContiExcessDt` | For Aqua Scheme accounts with overdrawn DPD less than or equal to 30 days, the continuous excess date is cleared and the overdrawn DPD is s… |
| 🟢 3 | Reset Aqua Scheme renewal fields | `ReviewDueDt` | For Aqua Scheme accounts, the review due date and renewal DPD are reset to null and zero respectively as part of the DPD update process. |
| 🟠 4 | Calculate maximum DPD for account | `DPD_Max` | The maximum DPD value among all DPD attributes is determined for each account to identify the most severe overdue situation. |
| 🟢 5 | Clear previous SMA classification fields | `SMA_CLASS` | Before recalculating SMA status, all previous SMA classification, reason, date, and flag fields are cleared for each account. |
| 🟠 6 | Assign SMA class based on DPD ladder | `SMA_CLASS` | Accounts are assigned an SMA classification based on the maximum DPD value, following regulatory thresholds. |
| 🟢 7 | Assign SMA reason based on facility and DPD type | `SMA_REASON` | The reason for SMA downgrade is set based on which DPD attribute matches the maximum DPD and the facility type, indicating the specific reg… |
| 🟢 8 | Set SMA date based on DPD_Max | `SMA_DT` | The SMA date is set to the processing date minus the maximum DPD plus one, reflecting the start of the overdue period. |
| 🟢 9 | Flag account as SMA marked | `FLGSMA` | Accounts that have been assigned an SMA classification are flagged as SMA marked for reporting and further processing. |
| 🟠 10 | Update customer-level SMA class and date | `SMA_CLASS_KEY` | The most severe SMA classification and earliest SMA date among all accounts for a customer are assigned at the customer level for consolida… |
| 🟢 11 | Assign standard asset class if missing | `SMA_CLASS` | If an account's SMA classification is missing but its final asset class key indicates a standard asset, the SMA class is set to 'STD'. |
| 🟢 12 | Assign sub-standard asset class if missing | `SMA_CLASS` | If an account's SMA classification is missing but its final asset class key indicates a sub-standard asset, the SMA class is set to 'SUB'. |
| 🟢 13 | Assign doubtful asset class if missing | `SMA_CLASS` | If an account's SMA classification is missing but its final asset class key indicates a doubtful asset, the SMA class is set to the appropr… |
| 🟢 14 | Assign loss asset class if missing | `SMA_CLASS` | If an account's SMA classification is missing but its final asset class key indicates a loss asset, the SMA class is set to 'LOS'. |

## 14. Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|
| 1 | Reset negative DPD values to zero | isnull(DPD_IntService,0)<0; isnull(DPD_NoCredit,0)<0; isnull(DPD_Overdrawn,0)<0; isnull(DPD_Overdue,0)<0; isnull(DPD_Renewal,0)<0; isnull(DPD_StockStmt,0)<0 | 01_nested_block:nested_block | conditions[4]: isnull(DPD_IntService,0)<0 -> UPDATE #DPD SET DPD_IntService=0; tables_written[2]: #DPD \| UPDATE \| target: DPD_IntService \| WHERE: COALESCE(DPD_IntService, 0) < 0; tables_written[9]: #DPD \| UPDATE \| target: DPD_IntService \| WHERE: isnull(DPD_IntService,0)<0; conditions[5]: isnull(DPD_NoCredit,0)<0 -> UPDATE #DPD SET DPD_NoCredit=0; tables_written[3]: #DPD \| UPDATE \| target: DPD_NoCredit \| WHERE: COALESCE(DPD_NoCredit, 0) < 0; tables_written[10]: #DPD \| UPDATE \| target: DPD_NoCredit \| WHERE: isnull(DPD_NoCredit,0)<0; _(+12 more instance(s) not shown)_ | Verified |
| 2 | Reset Aqua Scheme DPD fields if overdrawn DPD is low | ISNULL(A.DPD_Overdrawn,0)<= 30 | 01_nested_block:nested_block | conditions[3]: ISNULL(A.DPD_Overdrawn,0)<= 30 -> Update A.ContiExcessDt=NULL, A.DPD_Overdrawn=0; tables_read[5]: #DPD_Aqua_SMA \| READ \| target: A.AccountEntityID, B.AccountEntityID \| WHERE: COALESCE(A.DPD_Overdrawn, 0) <= 30; tables_read[6]: #DPD \| READ \| target: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, Ove…; tables_read[7]: ##AccountCal \| READ \| target: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExces…; tables_written[0]: ##ACCOUNTCAL \| UPDATE \| target: A.ContiExcessDt, A.DPD_Overdrawn \| WHERE: COALESCE(A.DPD_Overdrawn, 0) <= 30; tables_written[8]: ##ACCOUNTCAL \| UPDATE \| target: A.ContiExcessDt, A.DPD_Overdrawn \| WHERE: ISNULL(A.DPD_Overdrawn,0)<= 30 | Verified |
| 3 | Reset Aqua Scheme renewal fields | Update A SET A.ReviewDueDt=NULL,A.DPD_Renewal=0 | 01_nested_block:nested_block | tables_written[1]: ##ACCOUNTCAL \| UPDATE \| target: A.ReviewDueDt, A.DPD_Renewal \| WHERE: None | Verified |
| 4 | Calculate maximum DPD for account | UPDATE A SET A.DPD_Max= (CASE ... END) | Not cited | Not cited | Needs Review |
| 5 | Clear previous SMA classification fields | UPDATE A SET A.SMA_CLASS=NULL ,A.SMA_REASON=NULL ,A.SMA_DT=NULL ,A.FLGSMA=NULL | 01_nested_block_3:nested_block; 01_nested_block_1:nested_block | conditions[41]: ISNULL(DPD_Max,0)>0 AND DPD_Overdrawn=DPD_Max AND DPD_Max<=30 and FlgSMA='Y' -> UPDATE A SET A.SMA_Class=NULL, A.SMA_Reason=NULL, A.SMA_Dt=NULL, A.FlgSMA=NULL; tables_written[16]: ##AccountCal \| UPDATE \| target: A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA \| WHERE: None | Verified |
| 6 | Assign SMA class based on DPD ladder | CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' ... WHEN dpd.DPD_Max >90 THEN 'SMA_2' | Not cited | Not cited | Needs Review |
| 7 | Assign SMA reason based on facility and DPD type | CASE WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED' ... | 01_nested_block_2:nested_block | tables_read[13]: ##CUSTOMERCAL \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Account…; tables_read[14]: AdvAcBasicDetail \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Acco…; tables_read[15]: #DPD \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId,…; tables_written[20]: ##AccountCal \| UPDATE \| target: A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA \| WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALE…; tables_written[21]: ##AccountCal \| UPDATE \| target: A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA \| WHERE: ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANC…; calculations[10]: metric not specified \| explanation not specified | Verified |
| 8 | Set SMA date based on DPD_Max | A.SMA_DT= DATEADD(DAY, -dpd.DPD_MAX+1 ,@ProcessDate) | 01_nested_block_2:nested_block; 01_nested_block_3:nested_block | tables_read[13]: ##CUSTOMERCAL \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Account…; tables_read[14]: AdvAcBasicDetail \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Acco…; tables_read[15]: #DPD \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId,…; tables_written[20]: ##AccountCal \| UPDATE \| target: A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA \| WHERE: COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALE…; tables_written[21]: ##AccountCal \| UPDATE \| target: A.SMA_CLASS, A.SMA_REASON, A.SMA_DT, A.FLGSMA \| WHERE: ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANC…; calculations[11]: metric not specified \| explanation not specified | Verified |
| 9 | Flag account as SMA marked | A.FLGSMA='Y' | 01_nested_block_2:nested_block; 01_nested_block_4:nested_block | tables_read[13]: ##CUSTOMERCAL \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Account…; tables_read[14]: AdvAcBasicDetail \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.Acco…; tables_read[15]: #DPD \| READ \| target: dpd.DPD_MAX, A.CustomerEntityID, B.CustomerEntityID, dpd.AccountEntityId, a.AccountEntityId, DPD.DPD_MAX, dpd.DPD_Max, A.AccountEntityID, ABD.AccountEntityId,…; tables_read[19]: #TEMPTABLE_SMACLASS \| READ \| target: B.MAXSMA_CLASS, B.SMA_Dt, A.FLGSMA, A.CustomerEntityID, B.CustomerEntityID \| WHERE: A.FLGSMA = 'Y'; tables_read[23]: PRO.SMA_MOVEMENT_HISTORY \| READ \| target: 1 \| WHERE: TIMEKEY=@TIMEKEY) BEGIN; tables_read[24]: #SMACLASS \| READ \| target: A.CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS \| WHERE: B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0)…; _(+10 more instance(s) not shown)_ | Verified |
| 10 | Update customer-level SMA class and date | MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 ... END ) MAXSMA_CLASS; MIN(A.SMA_Dt) AS SMA_Dt | 01_nested_block_4:nested_block | tables_read[16]: #TEMPTABLE_SMACLASS \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAX…; tables_read[17]: ##AccountCal \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLA…; tables_read[18]: ##CUSTOMERCAL \| READ \| target: A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CL…; tables_read[20]: #TEMPTABLE_SMACLASSUcif \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_C…; tables_read[21]: ##AccountCal \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A…; tables_read[22]: ##CUSTOMERCAL \| READ \| target: A.UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(…; _(+2 more instance(s) not shown)_ | Could not trace the stated source evidence back to a successfully parsed technical extraction record: MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1 ... END ) MAXSMA_CLASS |
| 11 | Assign standard asset class if missing | UPDATE ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL | 01_nested_block_4:nested_block | tables_written[41]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL; tables_written[58]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL | Verified |
| 12 | Assign sub-standard asset class if missing | UPDATE ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL | 01_nested_block_4:nested_block | tables_written[42]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL; tables_written[59]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=2 AND SMA_CLASS is NULL | Verified |
| 13 | Assign doubtful asset class if missing | UPDATE ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL; UPDATE ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL; UPDATE ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5… | 01_nested_block_4:nested_block | tables_written[43]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key = 3 AND SMA_CLASS IS NULL; tables_written[60]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=3 AND SMA_CLASS is NULL; tables_written[44]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL; tables_written[61]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=4 AND SMA_CLASS is NULL; tables_written[45]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL; tables_written[62]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=5 AND SMA_CLASS is NULL | Verified |
| 14 | Assign loss asset class if missing | UPDATE ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL | 01_nested_block_5:nested_block | tables_read[35]: PRO.ACCOUNT_MOVEMENT_HISTORY \| READ \| target: 1 \| WHERE: [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO; tables_written[63]: ##AccountCal \| UPDATE \| target: SMA_CLASS \| WHERE: FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTime… | Verified |

_Source evidence is the literal technical text carried through the pipeline; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Calculations / Formulas

- **Processing date:** The processing date is determined by selecting the DATE from SYSDAYMATRIX where TIMEKEY matches the input parameter.
- **Effective to date for movement history:** The effective to date is set as one day before the Timekey from Automate_Advances where EXT_FLG is 'Y'.
- **DPD attributes for SMA eligibility:** Each DPD attribute is set to its value if it is greater than or equal to the reference period value, otherwise zero.
- **Maximum DPD (DPD_Max):** DPD_Max is the highest value among DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt for each account.
- **SMA date (SMA_DT):** SMA_DT is calculated as the processing date minus DPD_Max plus one.
- **Customer-level maximum SMA class:** The most severe SMA class for a customer is determined by the maximum of the numeric mapping of SMA_CLASS among all accounts.

## Exception Handling Behavior

If an error occurs during processing, all temporary tables are dropped and the process status is updated to indicate failure, including the error date and description for audit and troubleshooting purposes.

## Rule Provenance Summary

- **Total business rules:** 14
- **By rule type:** explicit = 14
- **By validation status:** insufficient_evidence = 1, unverified = 2, verified = 11

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

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
- Some code is commented out and may not be active; actual execution context may differ.
- References to columns like FINALASSETCLASSALT_KEY and DPD_Max are present but their source tables are not always explicit in the code fragment.
- The code chunk only contains the keyword 'TRY' with no further logic, so no procedural content is present to extract.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE   A SET A.DPD_Max= (CASE ... END)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: CASE WHEN dpd.DPD_Max  BETWEEN 1 AND 30  THEN 'SMA_0' ... WHEN dpd.DPD_Max >90 THEN 'SMA_2'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1 ... END ) MAXSMA_CLASS
