# SMA Marking — Business Logic Report

**Procedure:** `PRO.SMA_MARKING_12122023`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Purpose | This procedure calculates overdue days for various account services and assigns a Sub-Standard Asset (SMA) classification based on the maximum overdue days. It also updates SMA-related fields and handles SMA movement history. |
| Business rules | 12 |
| Tables read | 10 |
| Tables written | 7 |
| Produces audit trail | Yes — account and customer movement history |

## What This Does

This procedure calculates overdue days for various account services and assigns a Sub-Standard Asset (SMA) classification based on the maximum overdue days. It also updates SMA-related fields and handles SMA movement history.

## Process Flow

1. Drops temporary tables if they exist.
2. Reads data from the SYSDAYMATRIX table to get the process date.
3. Reads data from the Automate_Advances table to get the previous time key.
4. Initializes a temporary table #DPD with account details and sets initial overdue days to zero.
5. Calculates the maximum overdue days for each account and updates the temporary table.
6. Updates the SMA class, reason, and date for accounts based on the maximum overdue days.
7. Updates the SMA class and reason for customer-level accounts based on specific conditions.
8. Updates the SMA class and date for accounts based on the maximum overdue days.
9. Updates the SMA class and date for customer-level accounts based on specific conditions.
10. Deletes existing SMA movement history for the current time key if it exists.
11. Inserts new SMA movement history records from the temporary table.
12. Truncates the PREVSMASTATUS table.
13. Inserts new records into the PREVSMASTATUS table from the temporary table.
14. Updates the movement description for accounts based on system asset class alternate keys.
15. Updates the movement description for accounts based on final asset class alternate keys.
16. Updates the movement description for accounts based on SMA class keys.
17. Updates the movement from date and to date for account movement history records.
18. Updates the movement from date and to date for customer movement history records.
19. Updates the running process status for SMA marking.

## Business Rules

### R1 — Reset negative DPD values to zero

**Applies to:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_StockStmt`
**Eligibility (all must hold):**
- Account has overdue days data
- overdue-day value is below zero
**Meaning:** Ensures that negative overdue days for internal service, no credit, overdrawn, overdue, and stock statement are set to zero.

### Decision Logic
| Condition | Outcome |
|---|---|
| Metric value is below 0 | Metric set to 0 |


### R2 — Calculate maximum overdue days

**Applies to:** `DPD_Max`
**Eligibility:** Account has overdue days data
**Meaning:** Determines the maximum overdue days for an account based on various conditions.

### Decision Logic
| Condition | Outcome |
|---|---|
| DPD_IntService is at least RefPeriodIntService | DPD_IntService |
| DPD_NoCredit is at least RefPeriodNoCredit | DPD_NoCredit |
| DPD_Overdrawn is at least RefPeriodOverDrawn | DPD_Overdrawn |
| DPD_Overdue is at least RefPeriodOverdue | DPD_Overdue |
| DPD_Renewal is at least RefPeriodReview | DPD_Renewal |
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
| DPD_Overdrawn is at least 0 or DPD_Overdue is at least 0 | Calculates the SMA date based on the maximum overdue days. |


### R4 — Update SMA movement history

**Eligibility:** SMA class has changed
**Meaning:** Updates the SMA movement history for accounts.


### R5 — Update customer movement history

**Applies to:** `EffectiveToTimeKey`
**Eligibility:** Customer movement history record exists
**Meaning:** Updates the movement from date and to date for customer movement history records.


### R6 — Propagate customer-level SMA status

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


### R7 — Assign customer movement description by key

**Applies to:** `CustMoveDescription`
**Eligibility (all must hold):**
- customer has an SMA-marked account
- customer asset-class or SMA key matches
**Meaning:** Customer-level SMA status is aggregated from linked SMA-marked accounts. Customer movement descriptions are assigned from the applicable asset-class or SMA key.

### Decision Logic
| Condition | Outcome |
|---|---|
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


### R8 — Clear SMA fields before reprocessing

**Applies to:** `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA`
**Eligibility:** existing SMA classification is reset before reprocessing
**Meaning:** Existing SMA classification fields are cleared before the account is reprocessed.

### Decision Logic
| Condition | Outcome |
|---|---|
| Before reprocessing | NULL |


### R9 — Update DPD_Max

**Applies to:** `DPD_Max`
**Eligibility:** DPD_Overdrawn is above 0 or DPD_Overdue is above 0
**Meaning:** The procedure sets DPD_Max to the source-defined value when COALESCE(A.DPD_Overdrawn, 0) > 0 OR COALESCE(A.DPD_Overdue, 0) > 0.


### R10 — Update SMA_CLASS

**Applies to:** `SMA_CLASS`
**Meaning:** The procedure sets SMA_CLASS to the source-defined value.


### R11 — Update EffectiveToTimeKey, MovementToDate

**Applies to:** `EffectiveToTimeKey, MovementToDate`
**Eligibility:** EffectiveToTimeKey equals 49999 and CustomerAcID IS NULL
**Meaning:** The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL.


### R12 — Update EffectiveToTimeKey, MovementToDate

**Applies to:** `EffectiveToTimeKey, MovementToDate`
**Eligibility:** EffectiveToTimeKey equals 49999 and SourceSystemCustomerID IS NULL
**Meaning:** The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL.

## Calculations

- **A.DPD_Max:** CASE WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_IntService,0) WHEN (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_NoCredit,0) WHEN (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_Overdrawn,0) WHEN (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_Renewal,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_Renewal,0) WHEN (isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Overdue,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_Overdue,0) ELSE isnull(A.DPD_StockStmt,0) END
- **Metric:** N/A
- **Metric:** N/A

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.ACCOUNTCAL` | Read + Write | Assigns an SMA class to an account based on the maximum overdue days. Assigns a reason for the SMA class based on the type of overdue days. Calculates the SMA date based on the maximum overdue days.… |
| `PRO.CUSTOMERCAL` | Read + Write | Assigns an SMA class to an account based on the maximum overdue days. Assigns a reason for the SMA class based on the type of overdue days. Calculates the SMA date based on the maximum overdue days.… |
| `PRO.SMA_MOVEMENT_HISTORY` | Read + Write | Updates: TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS |
| `PRO.PREVSMASTATUS` | Read + Write | Assigns an SMA class to an account based on the maximum overdue days. Assigns a reason for the SMA class based on the type of overdue days. Calculates the SMA date based on the maximum overdue days.… |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Read + Write | Updates the movement from date and to date for customer movement history records. The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999… |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | Read + Write | Updates the movement from date and to date for customer movement history records. The procedure sets EffectiveToTimeKey, MovementToDate to the source-defined value when AA.EffectiveToTimeKey = 49999… |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SYSDAYMATRIX` | Read | Provides: DATE |
| `dbo.Automate_Advances` | Read | Provides: Timekey-1 |
| `AdvAcBasicDetail` | Read | Provides: dpd.DPD_MAX, A.CustomerEntityID, dpd.AccountEntityId, A.ASSET_NORM, A.FACILITYTYPE, DPD.DPD_INTSERVICE |

_9 working/temporary table(s) used only for intermediate calculation steps are omitted here - see the verification report for the full technical lineage._

## Exception Handling

Logs failures via INSERT into an exceptions/audit table and rolls back/logs/re-raises/silently handles exceptions.

## Findings / Needs Review

- The specific logic and tables involved in the procedure are not provided in the code chunk.
- DROP TABLE statements within the CATCH block
- DROP TABLE statements within the CATCH block.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `PRO.SMA_MARKING.StoredProcedure_verification.md`._
