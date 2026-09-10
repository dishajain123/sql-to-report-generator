# SMA Marking — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_MARKING` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 22 |
| Tables read | 9 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure marks accounts with a Sub-Standard Asset (SMA) classification based on the maximum overdue days (DPD) and facility type. It also records the reason for the classification and the date when the classification was applied. The procedure SMA_MARKING processes customer account data to update and classify accounts based on their financial status and overdue days. It resets certain fields, updates SMA class, and records movement history. This procedure marks accounts with a specific asset class and updates related overdue days and provisioning data for a given time period, ensuring compliance with RBI IRAC regulations.

## Process Flow

1. Reads account and customer data from various tables.
2. Updates the account's SMA classification, reason, date, and SMA flag based on the maximum overdue days and facility type.
3. Inserts or updates temporary tables with relevant account data.
4. Performs additional updates to specific overdue days parameters if they are negative.
5. Resets SMA related fields in the ##CUSTOMERCAL table.
6. Updates the FLGSMA field in the ##CUSTOMERCAL table based on conditions.
7. Drops temporary tables if they exist.
8. Creates and populates temporary tables with SMA class and date information.
9. Updates SMA related fields in the ##CUSTOMERCAL table using data from temporary tables.
10. Checks and deletes existing SMA movement history if it exists for the given time key.
11. Creates and populates a temporary table with SMA class information.
12. Updates the SMA class in the temporary table based on conditions.
13. Inserts new SMA movement history records and updates the SMA status in the ##CUSTOMERCAL and ##AccountCal tables based on conditions.
14. Updates the CustMoveDescription field in the ##CUSTOMERCAL table based on SYSASSETCLASSALT_KEY and SMA_CLASS_KEY values.
15. Checks if there is existing data in the temporary table #ACCOUNT_MOVEMENT_HISTORY and drops it if present.
16. Inserts data into the temporary table #ACCOUNT_MOVEMENT_HISTORY from the ##AccountCal table.
17. Updates the EffectiveToTimeKey and MovementToDate in the PRO.ACCOUNT_MOVEMENT_HISTORY table based on conditions.
18. Checks if there is existing data in the temporary table #Customer_MOVEMENT_HISTORY and drops it if present.
19. Inserts data into the temporary table #Customer_MOVEMENT_HISTORY from the ##CUSTOMERCAL table.
20. Updates the EffectiveToTimeKey and MovementToDate in the PRO.CUSTOMER_MOVEMENT_HISTORY table based on conditions.
21. Updates the SMA_CLASS, ContiExcessDt, DPD_Overdrawn, ReviewDueDt, and DPD_Renewal fields in the ##AccountCal table from the #DPD_Aqua_SMA table.
22. Updates the COMPLETED, ERRORDATE, ERRORDESCRIPTION, and COUNT fields in the PRO.ACLRUNNINGPROCESSSTATUS table to reflect the process status.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Update EffectiveToTimeKey and MovementToDate in PRO.ACCOUNT_MOVEMENT_HISTORY | `EffectiveToTimeKey, MovementToDate` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.ACCOUNT_MOVEMENT_HISTORY table based on specific conditions. |
| Update EffectiveToTimeKey and MovementToDate in PRO.CUSTOMER_MOVEMENT_HISTORY | `EffectiveToTimeKey, MovementToDate` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.CUSTOMER_MOVEMENT_HISTORY table based on specific conditions. |
| Update ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal in ##AccountCal | `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal` | Updates the ContiExcessDt, DPD_Overdrawn, ReviewDueDt, and DPD_Renewal fields in the ##AccountCal table from the #DPD_Aqua_SMA table. |
| Assign SMA class based on DPD Max | `SMA_CLASS` | Assigns the account's SMA class based on the maximum number of overdue days (DPD_Max). The SMA class is determined by the range of DPD_Max… |
| Set SMA reason based on DPD Max | `SMA_REASON` | Sets the reason for the SMA class based on the maximum number of overdue days (DPD_Max) and facility type. |
| Set SMA date based on DPD Max | `SMA_DT` | Sets the date when the SMA classification was applied based on the maximum number of overdue days (DPD_Max). |
| Set SMA flag to 'Y' | `FLGSMA` | Sets the SMA flag to 'Y' for accounts that meet the SMA classification criteria. |
| Reset negative DPD values | `DPD_IntService` | Resets negative values in various overdue days parameters to zero. |
| Reset negative DPD_NoCredit | `DPD_NoCredit` | Resets the DPD_NoCredit value to zero if it is negative. |
| Reset negative DPD_Overdrawn | `DPD_Overdrawn` | Resets the DPD_Overdrawn value to zero if it is negative. |
| Reset negative DPD_Overdue | `DPD_Overdue` | Resets the DPD_Overdue value to zero if it is negative. |
| Reset negative DPD_Renewal | `DPD_Renewal` | Resets the DPD_Renewal value to zero if it is negative. |
| Reset negative DPD_StockStmt | `DPD_StockStmt` | Resets the DPD_StockStmt value to zero if it is negative. |
| Reset negative DPD_Max | `DPD_Max` | Resets the DPD_Max value to zero if it is negative. |
| Reset SMA fields in CUSTOMERCAL | `FLGSMA, SMA_CLASS_KEY, SMA_DT` | Resets SMA related fields in the ##CUSTOMERCAL table to null. |
| Update FLGSMA in CUSTOMERCAL | `FLGSMA` | Updates the FLGSMA field in the ##CUSTOMERCAL table to 'Y' based on conditions. |
| Create and populate #TEMPTABLE_SMACLASS | `MAXSMA_CLASS, SMA_Dt` | Creates and populates the temporary table #TEMPTABLE_SMACLASS with SMA class and date information. |
| Update SMA fields in CUSTOMERCAL using #TEMPTABLE_SMACLASS | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table using data from the temporary table #TEMPTABLE_SMACLASS. |
| Create and populate #TEMPTABLE_SMACLASSUcif | `MAXSMA_CLASS, SMA_Dt` | Creates and populates the temporary table #TEMPTABLE_SMACLASSUcif with SMA class and date information. |
| Update SMA fields in CUSTOMERCAL using #TEMPTABLE_SMACLASSUcif | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table using data from the temporary table #TEMPTABLE_SMACLASSUcif. |
| Delete SMA movement history if exists | `TIMEKEY` | Deletes existing SMA movement history records for the given time key if they exist. |
| Create and populate #SMACLASS | `SMA_CLASS` | Creates and populates the temporary table #SMACLASS with SMA class information. |

## Business Rules

### R1 — Update EffectiveToTimeKey and MovementToDate in PRO.ACCOUNT_MOVEMENT_HISTORY

**Affected Field:** `EffectiveToTimeKey, MovementToDate`

**Applies to:**

- AA.EffectiveToTimeKey = 49999
- B.CustomerAcID IS NULL

**Summary:**

- Updates the EffectiveToTimeKey and MovementToDate in the ACCOUNT_MOVEMENT_HISTORY table based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| EffectiveToTimeKey = 49999 AND CustomerAcID IS NULL | EffectiveToTimeKey = @vEffectiveto, MovementToDate = DATEADD(DD, -1, @ProcessDate) |
| EffectiveToTimeKey = 49999 AND EffectiveFROMTimeKey < @TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE CustomerAcID = CustomerAcID AND EffectiveToTimeKey = 49999 AND MOVEMENTTOSTATUS <> MOVEMENTTOSTATUS) | EffectiveToTimeKey = @vEffectiveto, MovementToDate = DATEADD(DD, -1, @ProcessDate) |


### R2 — Update EffectiveToTimeKey and MovementToDate in PRO.CUSTOMER_MOVEMENT_HISTORY

**Affected Field:** `EffectiveToTimeKey, MovementToDate`

**Applies to:**

- AA.EffectiveToTimeKey = 49999
- B.SourceSystemCustomerID IS NULL

**Summary:**

- Updates the EffectiveToTimeKey and MovementToDate in the CUSTOMER_MOVEMENT_HISTORY table based on specific conditions.

### Decision Logic

| Condition | Result |
|---|---|
| EffectiveToTimeKey = 49999 AND SourceSystemCustomerID IS NULL | EffectiveToTimeKey = @vEffectiveto, MovementToDate = DATEADD(DD, -1, @ProcessDate) |
| EffectiveToTimeKey = 49999 AND EffectiveFROMTimeKey < @TIMEKEY AND EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB WHERE SourceSystemCustomerID = SourceSystemCustomerID AND EffectiveToTimeKey = 49999 AND MOVEMENTTOSTATUS <> MOVEMENTTOSTATUS) | EffectiveToTimeKey = @vEffectiveto, MovementToDate = DATEADD(DD, -1, @ProcessDate) |


### R3 — Update ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal in ##AccountCal

**Affected Field:** `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal`

**Applies to:**

- A.AccountEntityID = B.AccountEntityID

**Summary:**

- Updates the ContiExcessDt, DPD_Overdrawn, ReviewDueDt, and DPD_Renewal fields in the ##AccountCal table from the #DPD_Aqua_SMA table.


### R4 — Assign SMA class based on DPD Max

**Affected Field:** `SMA_CLASS`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Assigns the account's SMA class based on the maximum number of overdue days (DPD_Max). The SMA class is determined by the range of DPD_Max and the facility type.

### Decision Logic

| Condition | Result |
|---|---|
| DPD_Max BETWEEN 1 AND 30 | SMA_0 |
| DPD_Max BETWEEN 31 AND 60 | SMA_1 |
| DPD_Max BETWEEN 61 AND 90 | SMA_2 |
| DPD_Max > 90 | SMA_2 |


### R5 — Set SMA reason based on DPD Max

**Affected Field:** `SMA_REASON`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Sets the reason for the SMA class based on the maximum number of overdue days (DPD_Max) and facility type.

### Decision Logic

| Condition | Result |
|---|---|
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_INTSERVICE,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY INT NOT SERVICED' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_NOCREDIT,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY NO CREDIT' |
| FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(DPD_OVERDUE,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY OVERDUE' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_OVERDRAWN,0)=ISNULL(DPD_MAX,0) and ISNULL(DPD_OVERDRAWN,0)>30 | 'DEGRADE BY CONTI EXCESS' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_STOCKSTMT,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY STOCK STATEMENT' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_RENEWAL,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY REVIEW DUE DATE' |
| ELSE | 'OTHER' |


### R6 — Set SMA date based on DPD Max

**Affected Field:** `SMA_DT`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Sets the date when the SMA classification was applied based on the maximum number of overdue days (DPD_Max).


### R7 — Set SMA flag to 'Y'

**Affected Field:** `FLGSMA`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Sets the SMA flag to 'Y' for accounts that meet the SMA classification criteria.


### R8 — Reset negative DPD values

**Affected Field:** `DPD_IntService`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets negative values in various overdue days parameters to zero.


### R9 — Reset negative DPD_NoCredit

**Affected Field:** `DPD_NoCredit`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_NoCredit value to zero if it is negative.


### R10 — Reset negative DPD_Overdrawn

**Affected Field:** `DPD_Overdrawn`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_Overdrawn value to zero if it is negative.


### R11 — Reset negative DPD_Overdue

**Affected Field:** `DPD_Overdue`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_Overdue value to zero if it is negative.


### R12 — Reset negative DPD_Renewal

**Affected Field:** `DPD_Renewal`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_Renewal value to zero if it is negative.


### R13 — Reset negative DPD_StockStmt

**Affected Field:** `DPD_StockStmt`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_StockStmt value to zero if it is negative.


### R14 — Reset negative DPD_Max

**Affected Field:** `DPD_Max`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_Max value to zero if it is negative.


### R15 — Reset SMA fields in CUSTOMERCAL

**Affected Field:** `FLGSMA, SMA_CLASS_KEY, SMA_DT`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets SMA related fields in the ##CUSTOMERCAL table to null.


### R16 — Update FLGSMA in CUSTOMERCAL

**Affected Field:** `FLGSMA`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Updates the FLGSMA field in the ##CUSTOMERCAL table to 'Y' based on conditions.


### R17 — Create and populate #TEMPTABLE_SMACLASS

**Affected Field:** `MAXSMA_CLASS, SMA_Dt`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Creates and populates the temporary table #TEMPTABLE_SMACLASS with SMA class and date information.


### R18 — Update SMA fields in CUSTOMERCAL using #TEMPTABLE_SMACLASS

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table using data from the temporary table #TEMPTABLE_SMACLASS.


### R19 — Create and populate #TEMPTABLE_SMACLASSUcif

**Affected Field:** `MAXSMA_CLASS, SMA_Dt`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Creates and populates the temporary table #TEMPTABLE_SMACLASSUcif with SMA class and date information.


### R20 — Update SMA fields in CUSTOMERCAL using #TEMPTABLE_SMACLASSUcif

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table using data from the temporary table #TEMPTABLE_SMACLASSUcif.


### R21 — Delete SMA movement history if exists

**Affected Field:** `TIMEKEY`

**Applies to:**

- IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY)

**Summary:**

- Deletes existing SMA movement history records for the given time key if they exist.


### R22 — Create and populate #SMACLASS

**Affected Field:** `SMA_CLASS`

**Applies to:**

- B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1

**Summary:**

- Creates and populates the temporary table #SMACLASS with SMA class information.

## Calculations

_None identified._

## Data Touched

### Target (written)

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.PREVSMASTATUS` | Read + Write | Inserts data into: CustomerAcID, SMA_CLASS |

### Source (read-only)

| Table | Read/Write | Purpose |
|---|---|---|
| `SYSDAYMATRIX` | Read | Provides: DATE |
| `dbo.Automate_Advances` | Read | Provides: Timekey-1 |
| `DIMPRODUCT` | Read | Provides: CustomerAcID, AccountEntityID, DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt |
| `AdvAcBasicDetail` | Read | Provides: DPD_MAX, CustomerEntityID, AccountEntityId, ASSET_NORM, FACILITYTYPE, DPD_INTSERVICE |

### Control / Audit

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.SMA_MOVEMENT_HISTORY` | Read + Write | Inserts data into: TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS |
| `PRO.ACCOUNT_MOVEMENT_HISTORY` | Read + Write | Inserts data into: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt |
| `PRO.CUSTOMER_MOVEMENT_HISTORY` | Read + Write | Inserts data into: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#DPD_Aqua_SMA` | Read + Write | Inserts data into: CustomerAcID, AccountEntityID, DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt |
| `##ACCOUNTCAL` | Read + Write | Updates: ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal, SMA_CLASS, SMA_REASON |
| `#DPD` | Read + Write | Inserts data into: AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID |
| `#TEMPTABLE` | Write | Inserts data into: CustomerAcID, CASE WHEN COALESCE(A.DPD_IntService, 0) >= COALESCE(A.RefPeriodIntService, 0) THEN A.DPD_IntService ELSE 0 END AS DPD_IntService, CASE WHEN COALESCE(A.DPD_NoCredit, 0) >= COALESCE(A.RefPeriodNoCredit, 0) THEN A.DPD_NoCredit ELSE 0 END AS DPD_NoCredit, CASE WHEN COALESCE(A.DPD_Overdrawn, 0) >= COALESCE(A.RefPeriodOverDrawn, 0) THEN A.DPD_Overdrawn ELSE 0 END AS DPD_Overdrawn, CASE WHEN COALESCE(A.DPD_Overdue, 0) >= COALESCE(A.RefPeriodOverdue, 0) THEN A.DPD_Overdue ELSE 0 END AS DPD_Overdue, CASE WHEN COALESCE(A.DPD_Renewal, 0) >= COALESCE(A.RefPeriodReview, 0) THEN A.DPD_Renewal ELSE 0 END AS DPD_Renewal |
| `##CUSTOMERCAL` | Read + Write | Updates: FLGSMA, SMA_CLASS_KEY, SMA_DT, CustMoveDescription |
| `#TEMPTABLE_SMACLASS` | Read + Write | Inserts data into: CustomerEntityID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt |
| `#TEMPTABLE_SMACLASSUcif` | Write | Inserts data into: UCIF_ID, MAX(CASE WHEN SMA_CLASS = 'SMA_0' THEN 1 WHEN SMA_CLASS = 'SMA_1' THEN 2 WHEN SMA_CLASS = 'SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt |
| `#SMACLASS` | Read + Write | Inserts data into: CustomerAcID, COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2')) AS SMA_CLASS, SMA_CLASS |
| `#ACCOUNT_MOVEMENT_HISTORY` | Read + Write | Inserts data into: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerAcID, FinalAssetClassAlt_Key, FinalNpaDt |
| `#Customer_MOVEMENT_HISTORY` | Read + Write | Inserts data into: UCIF_ID, RefCustomerID, SourceSystemCustomerID, CustomerName, SysAssetClassAlt_Key, SysNPA_Dt |

_2 table reference(s) could not be resolved to a table name and are omitted from this list - see the verification report for the full technical lineage._

## Hardcoded Values

Literal date values found directly in the source (not parameters or config lookups):

| Value | Occurrences | Line(s) |
|---|---|---|
| `2086-11-21` | 2 | 506, 644 |

## Exception Handling

No explicit exception handling is defined in the provided extraction. If an error occurs, the temporary tables are dropped, and the PRO.ACLRUNNINGPROCESSSTATUS table is updated to reflect an error with the current date and error message.

## Findings / Needs Review

- Affected regions: lines 24-24, 36-41, 107-110, 111-118, 400-453 (+2 more) (7 total) - needs review after a larger output budget or chunked synthesis.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic. Affected regions: lines 24-24, 36-41, 107-110, 111-118, 400-453 (+2 more) (7 total) - needs review after a larger output budget or chunked synthesis.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
