# SMA Marking — Business Logic Report

**Procedure:** `PRO.SMA_MARKING_12122023`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Purpose | This procedure calculates and updates the overdue days and SMA (Special Mention Account) classification for accounts based on various overdue conditions and facility types. It also handles the movement history and SMA class assignment for accounts and customers. |
| Business rules | 13 |
| Tables read | 10 |
| Tables written | 7 |
| Produces audit trail | Yes — account and customer movement history |

## What This Does

This procedure calculates and updates the overdue days and SMA (Special Mention Account) classification for accounts based on various overdue conditions and facility types. It also handles the movement history and SMA class assignment for accounts and customers.

## Process Flow

1. Initializes temporary tables and drops existing ones if they exist.
2. Reads data from various tables to calculate overdue days and SMA classification.
3. Updates temporary tables with calculated overdue days and SMA classification.
4. Updates the main account and customer tables with the calculated SMA classification and reason.
5. Inserts or updates movement history records for accounts and customers.
6. Handles exceptions by logging failures and rolling back transactions.

## Business Rules

### R1 — Reset negative DPD values to zero

**Applies to:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt`
**Eligibility (all must hold):**
- Account has overdue days data
- overdue-day value is below zero
**Meaning:** Negative overdue-day values are reset to zero before the maximum overdue days is calculated.

### Decision Logic
| Condition | Outcome |
|---|---|
| Metric value is below 0 | Metric set to 0 |


### R2 — Calculate maximum overdue days

**Applies to:** `DPD_Max`
**Eligibility:** Account has overdue days data
**Meaning:** Determines the maximum overdue days across various services for an account.

### Decision Logic
| Condition | Outcome |
|---|---|
| (DPD_IntService is at least DPD_NoCredit and DPD_IntService is at least DPD_Overdrawn and DPD_IntService is at least DPD_Overdue and DPD_IntService is at least DPD_Renewal and DPD_IntService is at least DPD_StockStmt) | DPD_IntService |
| (DPD_NoCredit is at least DPD_IntService and DPD_NoCredit is at least DPD_Overdrawn and DPD_NoCredit is at least DPD_Overdue and DPD_NoCredit is at least DPD_Renewal and DPD_NoCredit is at least DPD_StockStmt) | DPD_NoCredit |
| (DPD_Overdrawn is at least DPD_NoCredit and DPD_Overdrawn is at least DPD_IntService and DPD_Overdrawn is at least DPD_Overdue and DPD_Overdrawn is at least DPD_Renewal and DPD_Overdrawn is at least DPD_StockStmt) | DPD_Overdrawn |
| (DPD_Renewal is at least DPD_NoCredit and DPD_Renewal is at least DPD_IntService and DPD_Renewal is at least DPD_Overdrawn and DPD_Renewal is at least DPD_Overdue and DPD_Renewal is at least DPD_StockStmt) | DPD_Renewal |
| (DPD_Overdue is at least DPD_NoCredit and DPD_Overdue is at least DPD_IntService and DPD_Overdue is at least DPD_Overdrawn and DPD_Overdue is at least DPD_Renewal and DPD_Overdue is at least DPD_StockStmt) | DPD_Overdue |
| ELSE | DPD_StockStmt |


### R3 — Assign account-level SMA fields in order

**Applies to:** `SMA_CLASS, SMA_REASON, SMA_DT`
**Eligibility:** Account has overdue days data
**Meaning:** The account-level SMA fields in order is assigned.

### Decision Logic
| Condition | Outcome |
|---|---|
| DPD_Max is between 1 and 30 | 'SMA_0' |
| DPD_Max is between 31 and 60 | 'SMA_1' |
| DPD_Max is between 61 and 90 | 'SMA_2' |
| DPD_Max is above 90 | 'SMA_2' |
| FACILITYTYPE IN ('CC','OD') and DPD_INTSERVICE equals DPD_MAX | 'DEGRADE BY INT NOT SERVICED' |
| FACILITYTYPE IN ('CC','OD') and DPD_NOCREDIT equals DPD_MAX | 'DEGRADE BY NO CREDIT' |
| FACILITYTYPE IN ('TL','DL','BP','BD','PC') and DPD_OVERDUE equals DPD_MAX | 'DEGRADE BY OVERDUE' |
| FACILITYTYPE IN ('CC','OD') and DPD_OVERDRAWN equals DPD_MAX and DPD_OVERDRAWN>30 | 'DEGRADE BY CONTI EXCESS' |
| FACILITYTYPE IN ('CC','OD') and DPD_STOCKSTMT equals DPD_MAX | 'DEGRADE BY STOCK STATEMENT' |
| FACILITYTYPE IN ('CC','OD') and DPD_RENEWAL equals DPD_MAX | 'DEGRADE BY REVIEW DUE DATE' |
| DPD_Max is above 0 | Calculates the SMA date based on the maximum overdue days. |


### R4 — Assign customer movement description by key

**Applies to:** `CustMoveDescription`
**Eligibility (all must hold):**
- Customer has a SMA class key
- customer has an SMA-marked account
- customer asset-class or SMA key matches
**Meaning:** Assigns a movement description to the customer based on the SMA class key. Customer-level SMA status is aggregated from linked SMA-marked accounts. Customer movement descriptions are assigned from the applicable asset-class or SMA key.

### Decision Logic
| Condition | Outcome |
|---|---|
| SMA_CLASS_KEY equals 1 | 'STD' |
| SMA_CLASS_KEY equals 2 | 'SUB' |
| SMA_CLASS_KEY equals 3 | 'DB1' |
| customer has an SMA-marked account | Customer-level SMA status is aggregated from linked SMA-marked accounts. |
| SYSASSETCLASSALT_KEY equals 1 | STD |
| SYSASSETCLASSALT_KEY equals 2 | SUB |
| SYSASSETCLASSALT_KEY equals 3 | DB1 |
| SYSASSETCLASSALT_KEY equals 4 | DB2 |
| SYSASSETCLASSALT_KEY equals 5 | DB3 |
| SYSASSETCLASSALT_KEY equals 6 | LOS |
| SMA_CLASS_KEY equals 1 | SMA_0 |
| SMA_CLASS_KEY equals 2 | SMA_1 |
| SMA_CLASS_KEY equals 3 | SMA_2 |


### R5 — Assign account SMA class

**Applies to:** `SMA_CLASS`
**Eligibility:** Account has a final asset class alternate key
**Meaning:** Assigns the SMA class to the account based on the final asset class alternate key.

### Decision Logic
| Condition | Outcome |
|---|---|
| FinalAssetClassAlt_Key equals 1 | 'STD' |
| FinalAssetClassAlt_Key equals 2 | 'SUB' |
| FinalAssetClassAlt_Key equals 3 | 'DB1' |
| FinalAssetClassAlt_Key equals 4 | 'DB2' |
| FinalAssetClassAlt_Key equals 5 | 'DB3' |


### R6 — Insert SMA movement history

**Eligibility:** Account has a changed SMA class
**Meaning:** Inserts SMA movement history records for accounts with changed SMA classes.


### R7 — Update account movement history

**Applies to:** `EffectiveToTimeKey`
**Eligibility:** Account movement history record exists
**Meaning:** Updates the effective to time key and movement to date for account movement history records.


### R8 — Propagate customer-level SMA status

**Applies to:** `FLGSMA, SMA_DT`
**Eligibility (all must hold):**
- FLGPROCESSING equals 'N' and FINALASSETCLASSALT_KEY equals 1 and BALANCE is above 0 and ASSET_NORM is not 'ALWYS_STD' and (DPD_Overdrawn is at least 0 or DPD_Overdue is at least 0) and DPD_MAX is above 0
- SMA_CLASS is NULL
**Meaning:** Propagate customer-level SMA status.

### Decision Logic
| Condition | Outcome |
|---|---|
| FLGPROCESSING equals 'N' and FINALASSETCLASSALT_KEY equals 1 and BALANCE is above 0 and ASSET_NORM is not 'ALWYS_STD' and (DPD_Overdrawn is at least 0 or DPD_Overdue is at least 0) and DPD_MAX is above 0 | Processed accounts are marked as being under SMA classification. |
| FLGPROCESSING equals 'N' and FINALASSETCLASSALT_KEY equals 1 and BALANCE is above 0 and ASSET_NORM is not 'ALWYS_STD' and (DPD_Overdrawn is at least 0 or DPD_Overdue is at least 0) and DPD_MAX is above 0 | (CASE WHEN DPD_Max BETWEEN 1 AND 30 THEN 'SMA_0' WHEN DPD_Max BETWEEN 31 AND 60 THEN 'SMA_1' WHEN DPD_Max BETWEEN 61 AND 90 THEN 'SMA_2' WHEN DPD_Max > 90 THEN 'SMA_2' ELSE NULL END) |
| FLGPROCESSING equals 'N' and FINALASSETCLASSALT_KEY equals 1 and BALANCE>0 and ASSET_NORM is not 'ALWYS_STD' and ( DPD_Overdrawn is at least 0 or DPD_Overdue is at least 0 ) and DPD_MAX>0 | assigned asset-class label |
| FinalAssetClassAlt_Key equals 1 and SMA_CLASS IS NULL | STD |
| FinalAssetClassAlt_Key equals 2 and SMA_CLASS IS NULL | SUB |
| FinalAssetClassAlt_Key equals 3 and SMA_CLASS IS NULL | DB1 |
| FinalAssetClassAlt_Key equals 4 and SMA_CLASS IS NULL | DB2 |
| FinalAssetClassAlt_Key equals 5 and SMA_CLASS IS NULL | DB3 |
| FinalAssetClassAlt_Key equals 6 and SMA_CLASS is NULL if EXISTS ( select 1 from ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey] equals @Timekey) begin print 'NO NEDD TO INSERT DATA' | assigned asset-class label |


### R9 — Clear SMA fields before reprocessing

**Applies to:** `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA`
**Eligibility:** existing SMA classification is reset before reprocessing
**Meaning:** Existing SMA classification fields are cleared before the account is reprocessed.

### Decision Logic
| Condition | Outcome |
|---|---|
| Before reprocessing | NULL |


### R10 — Update DPD_Max

**Applies to:** `DPD_Max`
**Eligibility:** DPD_Overdrawn is above 0 or DPD_Overdue is above 0
**Meaning:** The procedure sets DPD_Max to the source-defined value when COALESCE(A.DPD_Overdrawn, 0) > 0 OR COALESCE(A.DPD_Overdue, 0) > 0.


### R11 — Update SMA_CLASS

**Applies to:** `SMA_CLASS`
**Meaning:** The procedure sets SMA_CLASS to the source-defined value.


### R12 — Update EffectiveToTimeKey, MovementToDate

**Applies to:** `EffectiveToTimeKey, MovementToDate`
**Eligibility:** EffectiveToTimeKey equals 49999 and CustomerAcID IS NULL
**Meaning:** The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL.


### R13 — Update EffectiveToTimeKey, MovementToDate

**Applies to:** `EffectiveToTimeKey, MovementToDate`
**Eligibility:** EffectiveToTimeKey equals 49999 and SourceSystemCustomerID IS NULL
**Meaning:** The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL.

## Calculations

- **A.DPD_Max:** (CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_IntService,0) WHEN (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_NoCredit,0) WHEN (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_Overdrawn,0) WHEN (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_Renewal,0) WHEN (isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_Overdue,0) ELSE isnull(A.DPD_StockStmt,0) END
- **A.SMA_DT:** DATEADD(DAY, -dpd.DPD_MAX+1, @ProcessDate)
- **MovementToDate:** DATEADD(DD,-1,@ProcessDate)

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.ACCOUNTCAL` | Read + Write | Existing SMA classification fields are cleared before the account is reprocessed. |
| `PRO.CUSTOMERCAL` | Read + Write | Assigns a movement description to the customer based on the SMA class key. Customer-level SMA status is aggregated from linked SMA-marked accounts. Customer movement descriptions are assigned from th… |
| `PRO.SMA_MOVEMENT_HISTORY` | Read + Write | Updates: TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS |
| `PRO.PREVSMASTATUS` | Read + Write | Set STANDARD classification and 15 provision pct Assigns the SMA class to the account based on the final asset class alternate key. |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Read + Write | Assigns the SMA class to the account based on the final asset class alternate key. The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999… |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | Read + Write | The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL. The procedure sets EffectiveToTimeKey, MovementToDate… |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SYSDAYMATRIX` | Read | Provides: DATE |
| `dbo.Automate_Advances` | Read | Provides: Timekey-1 |
| `AdvAcBasicDetail` | Read | Provides: dpd.DPD_MAX, A.CustomerEntityID, dpd.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE |

_9 working/temporary table(s) used only for intermediate calculation steps are omitted here - see the verification report for the full technical lineage._

## Exception Handling

In case of an exception, the procedure logs the failure and rolls back the transaction.

## Findings / Needs Review

- The actual logic and tables involved in the procedure are not present in the provided code chunk.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `PRO.SMA_MARKING.StoredProcedure_verification.md`._
