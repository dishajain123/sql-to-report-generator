# SMA Marking — Business Logic Report

**Procedure:** `PRO.SMA_MARKING_12122023`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Purpose | This procedure calculates overdue days for various account activities and assigns a Sub-Standard Asset (SMA) classification based on the maximum overdue days. It also updates movement history and process status records. |
| Business rules | 10 |
| Tables read | 17 |
| Tables written | 14 |
| Produces audit trail | Yes — account and customer movement history |

## What This Does

This procedure calculates overdue days for various account activities and assigns a Sub-Standard Asset (SMA) classification based on the maximum overdue days. It also updates movement history and process status records.

## Process Flow

1. Initializes temporary tables to store account data and overdue days.
2. Calculates overdue days for different account activities and stores them in temporary tables.
3. Determines the maximum overdue days for each account and assigns an SMA classification based on the maximum days.
4. Updates the SMA class and related fields in the account records.
5. Updates movement history records for accounts and customers.
6. Updates the running process status record for the SMA marking process.

## Business Rules

### R1 — Reset negative DPD values to zero

**Applies to:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_StockStmt`
**Eligibility (all must hold):**
- Account has overdue days data
- overdue-day value is below zero
**Meaning:** Negative overdue-day values are reset to zero before the maximum overdue days is calculated.

### Decision Logic
| Condition | Outcome |
|---|---|
| isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) | A.DPD_IntService |
| ELSE | 0 |
| isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) | A.DPD_NoCredit |
| isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn,0) | A.DPD_Overdrawn |
| isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue,0) | A.DPD_Overdue |
| isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0) | A.DPD_StockStmt |
| COALESCE(DPD_IntService, 0) < 0 | 0 |
| COALESCE(DPD_NoCredit, 0) < 0 | 0 |
| COALESCE(DPD_Overdrawn, 0) < 0 | 0 |
| COALESCE(DPD_Overdue, 0) < 0 | 0 |
| COALESCE(DPD_Renewal, 0) < 0 | 0 |
| isnull(DPD_StockStmt,0)<0 | 0 |
| isnull(DPD_IntService,0)<0 | 0 |
| isnull(DPD_NoCredit,0)<0 | 0 |
| isnull(DPD_Overdrawn,0)<0 | 0 |
| isnull(DPD_Overdue,0)<0 | 0 |
| isnull(DPD_Renewal,0)<0 | 0 |


### R2 — Calculate DPD_Renewal

**Applies to:** `DPD_Renewal`
**Eligibility:** Account has overdue days data
**Meaning:** The DPD_Renewal is calculated.

### Decision Logic
| Condition | Outcome |
|---|---|
| isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview,0) | A.DPD_Renewal |
| ELSE | 0 |


### R3 — Assign account-level SMA fields in order

**Applies to:** `SMA_CLASS`
**Eligibility (all must hold):**
- Account has overdue days data
- existing SMA classification is reset before reprocessing
**Meaning:** The account-level SMA fields in order is assigned.

### Decision Logic
| Condition | Outcome |
|---|---|
| dpd.DPD_Max BETWEEN 1 AND 30 | 'SMA_0' |
| dpd.DPD_Max BETWEEN 31 AND 60 | 'SMA_1' |
| dpd.DPD_Max BETWEEN 61 AND 90 | 'SMA_2' |
| dpd.DPD_Max > 90 | 'SMA_2' |
| dpd.DPD_MAX BETWEEN 276 AND 305 | 'SMA_0' |
| dpd.DPD_MAX BETWEEN 306 AND 335 | 'SMA_1' |
| dpd.DPD_MAX BETWEEN 336 AND 365 | 'SMA_2' |
| dpd.DPD_MAX >= 366 | 'SMA_2' |
| A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) | 'DEGRADE BY INT NOT SERVICED' |
| A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) | 'DEGRADE BY NO CREDIT' |
| A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) | 'DEGRADE BY OVERDUE' |
| A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 | 'DEGRADE BY CONTI EXCESS' |
| A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) | 'DEGRADE BY STOCK STATEMENT' |
| A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) | 'DEGRADE BY REVIEW DUE DATE' |
| ELSE | 'OTHER' |
| Before reprocessing | NULL |


### R4 — Update SMA movement history

**Applies to:** `TIMEKEY`
**Eligibility:** SMA movement history exists for the specified time key
**Meaning:** Updates the SMA movement history record for the specified time key.


### R5 — Insert SMA movement history

**Eligibility:** Current SMA class differs from the previous SMA class
**Meaning:** Inserts a new SMA movement history record if the current status differs from the previous status.


### R6 — Update EffectiveToTimeKey, MovementToDate

**Applies to:** `EffectiveToTimeKey`
**Eligibility (all must hold):**
- Account movement history record has EffectiveToTimeKey = 49999 and CustomerAcID is NULL
- AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL
**Meaning:** The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL.


### R7 — Propagate customer-level SMA status

**Applies to:** `FLGSMA, SMA_DT`
**Eligibility (all must hold):**
- COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0
- SMA_CLASS is NULL
**Meaning:** Propagate customer-level SMA status.

### Decision Logic
| Condition | Outcome |
|---|---|
| COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | Processed accounts are marked as being under SMA classification. |
| COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0 | (CASE WHEN dpd.DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN dpd.DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN dpd.DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN dpd.DPD_Max > 90 THEN 'SMA_2' ELSE NULL END) |
| ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1 AND ISNULL(A.BALANCE,0)>0 and A.ASSET_NORM<>'ALWYS_STD' AND ( isnull(dpd.DPD_Overdrawn,0)>=0 OR isnull(dpd.DPD_Overdue,0)>=0 ) AND ISNULL(DPD.DPD_MAX,0)>0 | assigned asset-class label |
| FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL | STD |
| FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL | SUB |
| FinalAssetClassAlt_Key = 3 AND SMA_CLASS IS NULL | DB1 |
| FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL | DB2 |
| FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL | DB3 |
| FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL if EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) begin print 'NO NEDD TO INSERT DATA' | assigned asset-class label |


### R8 — Assign customer movement description by key

**Applies to:** `CustMoveDescription`
**Eligibility (all must hold):**
- customer has an SMA-marked account
- customer asset-class or SMA key matches
**Meaning:** Customer-level SMA status is aggregated from linked SMA-marked accounts. Customer movement descriptions are assigned from the applicable asset-class or SMA key.

### Decision Logic
| Condition | Outcome |
|---|---|
| customer has an SMA-marked account | Customer-level SMA status is aggregated from linked SMA-marked accounts. |
| SYSASSETCLASSALT_KEY = 1 | STD |
| SYSASSETCLASSALT_KEY = 2 | SUB |
| SYSASSETCLASSALT_KEY = 3 | DB1 |
| SYSASSETCLASSALT_KEY = 4 | DB2 |
| SYSASSETCLASSALT_KEY = 5 | DB3 |
| SYSASSETCLASSALT_KEY = 6 | LOS |
| SMA_CLASS_KEY = 1 | SMA_0 |
| SMA_CLASS_KEY = 2 | SMA_1 |
| SMA_CLASS_KEY = 3 | SMA_2 |


### R9 — Update DPD_Max

**Applies to:** `DPD_Max`
**Eligibility:** COALESCE(A.DPD_Overdrawn, 0) > 0 OR COALESCE(A.DPD_Overdue, 0) > 0
**Meaning:** The procedure sets DPD_Max to the source-defined value when COALESCE(A.DPD_Overdrawn, 0) > 0 OR COALESCE(A.DPD_Overdue, 0) > 0.


### R10 — Update EffectiveToTimeKey, MovementToDate

**Applies to:** `EffectiveToTimeKey, MovementToDate`
**Eligibility:** AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL
**Meaning:** The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL.

## Calculations

- **DPD_IntService:** Calculates the overdue days for interest not serviced.
- **DPD_NoCredit:** Calculates the overdue days for no credit.
- **DPD_Overdrawn:** Calculates the overdue days for continuous excess.
- **DPD_Overdue:** Calculates the overdue days for overdue.
- **DPD_StockStmt:** Calculates the overdue days for stock statement.
- **A.DPD_Max:** Determines the maximum overdue days for an account.
- **A.SMA_DT:** Calculates the SMA date based on the maximum overdue days.
- **SMA_CLASS:** Determines the SMA class based on the maximum overdue days.
- **MovementToDate:** Calculates the movement to date as one day before the process date.

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.ACCOUNTCAL` | Read + Write | Assigns an SMA class based on the maximum overdue days. Assigns an SMA class based on the maximum overdue days (alternate logic). Assigns an SMA class based on the facility type and specific overdue… |
| `PRO.CUSTOMERCAL` | Read + Write | Assigns an SMA class based on the maximum overdue days. Assigns an SMA class based on the maximum overdue days (alternate logic). Assigns an SMA class based on the facility type and specific overdue… |
| `PRO.SMA_MOVEMENT_HISTORY` | Read + Write | Updates the SMA movement history record for the specified time key. |
| `PRO.PREVSMASTATUS` | Read + Write | Assigns an SMA class based on the maximum overdue days. Assigns an SMA class based on the maximum overdue days (alternate logic). Assigns an SMA class based on the facility type and specific overdue… |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Read + Write | The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL. The procedure sets EffectiveToTimeKey, MovementToDate… |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | Read + Write | The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL. The procedure sets EffectiveToTimeKey, MovementToDate… |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SYSDAYMATRIX` | Read | Provides: DATE |
| `dbo.Automate_Advances` | Read | Provides: Timekey-1 |
| `AdvAcBasicDetail` | Read | Provides: dpd.DPD_MAX, A.CustomerEntityID, dpd.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE |

_9 working/temporary table(s) used only for intermediate calculation steps are omitted here - see the verification report for the full technical lineage._

## Exception Handling

If an exception occurs, the procedure logs the error details and updates the running process status record to indicate failure.

## Findings / Needs Review

- Commented out code blocks and conditions
- --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY) SELECT A.CustomerAcID,A.FinalAssetClassAlt_Key,A.FinalNpaDt,@TIMEKEY,49999 FROM PRO.AccountCal A  LEFT OUTER JOIN  Pro.ACCOUNT_MOVEMENT_HISTORY B ON A.CustomerAcID=B.CustomerAcID WHERE  ISNULL(A.FinalAssetClassAlt_Key,'')<>ISNULL(B.FinalAssetClassAlt_Key,'') AND B.EffectiveToTimeKeY=49999
- DROP TABLE #TEMPTABLE_SMACLASS
- DROP TABLE #SMACLASS
- DROP TABLE #ACCOUNT_MOVEMENT_HISTORY
- DROP TABLE #Customer_MOVEMENT_HISTORY
- Commented out code blocks and conditions may indicate deprecated or alternative logic.
- The purpose and logic of some dropped temporary tables are unclear.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `PRO.SMA_MARKING.StoredProcedure_verification.md`._
