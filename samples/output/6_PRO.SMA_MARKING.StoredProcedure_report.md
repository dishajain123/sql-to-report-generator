# SMA Marking — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_MARKING` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 20 |
| Tables read | 9 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure updates and calculates various overdue days and provisioning amounts for accounts under the SMA Aqua Scheme, ensuring that negative values are reset to zero and certain conditions are met for account classification and processing. This procedure calculates the maximum days past due (DPD) for accounts and updates the SMA class based on the calculated DPD values. The procedure SMA_MARKING updates various fields in the ##CUSTOMERCAL and ##AccountCal tables to mark the status of customer accounts based on their asset classification and overdue days. It also updates the movement history and previous status tables to track changes in account status over time. The procedure SMA_MARKING updates the SMA class for accounts and inserts or updates account and customer movement history records based on the provided time key. It ensures that the SMA class is set for accounts with a specific asset class and updates movement history records for accounts and customers. The SMA_MARKING procedure updates customer movement history, account details, and running process status based on specific conditions and time keys.

## Process Flow

1. Initializes temporary tables and drops them if they already exist.
2. Selects accounts under the SMA Aqua Scheme with specific conditions and inserts them into a temporary table.
3. Updates the ContiExcessDt and DPD_Overdrawn fields to zero for accounts with DPD_Overdrawn less than or equal to 30.
4. Updates the ReviewDueDt and DPD_Renewal fields to zero for accounts with DPD_Overdrawn less than or equal to 30.
5. Selects accounts with DPD_Overdrawn greater than 30 or DPD_Overdue greater than 0 and inserts them into another temporary table.
6. Resets negative values in various DPD fields to zero in the temporary table.
7. Calculates the maximum DPD value for each account.
8. Initializes the DPD values for reprocessing.
9. Updates the maximum DPD value for each account.
10. Resets the SMA class, reason, date, and flag for all accounts.
11. Initializes the ##CUSTOMERCAL table by setting FLGSMA, SMA_CLASS_KEY, and SMA_DT to NULL.
12. Updates the ##CUSTOMERCAL table to set FLGSMA to 'Y' for accounts that meet certain conditions.
13. Creates temporary tables #TEMPTABLE_SMACLASS and #TEMPTABLE_SMACLASSUcif to store aggregated SMA class information.
14. Updates the ##CUSTOMERCAL table to set SMA_CLASS_KEY and SMA_DT based on the information in the temporary tables.
15. Checks if there is an existing SMA movement history record for the given time key and deletes it if present.
16. Creates a temporary table #SMACLASS to store the SMA class information for accounts that meet certain conditions.
17. Updates the SMA class in the #SMACLASS table based on the current SMA class.
18. Inserts a new record into the SMA movement history table with the previous and current SMA class for accounts that have changed status.
19. Truncates the PREVSMASTATUS table to remove old records.
20. Inserts the current SMA class into the PREVSMASTATUS table for accounts that have changed status.
21. Updates the CustMoveDescription in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY.
22. Updates the SMA_CLASS in the ##AccountCal table based on the FinalAssetClassAlt_Key for accounts where SMA_CLASS is NULL.
23. Check if there is existing data for the given time key in PRO.ACCOUNT_MOVEMENT_HISTORY and PRO.CUSTOMER_MOVEMENT_HISTORY. If data exists, print a message indicating no need to insert data.
24. If no data exists for the given time key, drop the temporary tables #ACCOUNT_MOVEMENT_HISTORY and #Customer_MOVEMENT_HISTORY if they exist.
25. Create the temporary tables #ACCOUNT_MOVEMENT_HISTORY and #Customer_MOVEMENT_HISTORY with specified columns.
26. Updates the customer movement history with the effective to time key and movement to date.
27. Updates account details such as continuous excess date, DPD overdrawn, review due date, and DPD renewal.
28. Updates the running process status to mark the SMA_MARKING process as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Select accounts for SMA Aqua Scheme | `Not specified` | Selects accounts under the SMA Aqua Scheme with specific conditions and inserts them into a temporary table. |
| Reset ContiExcessDt and DPD_Overdrawn to zero | `ContiExcessDt, DPD_Overdrawn` | Updates the ContiExcessDt and DPD_Overdrawn fields to zero for accounts with DPD_Overdrawn less than or equal to 30. |
| Reset ReviewDueDt and DPD_Renewal to zero | `ReviewDueDt, DPD_Renewal` | Updates the ReviewDueDt and DPD_Renewal fields to zero for accounts with DPD_Overdrawn less than or equal to 30. |
| Select accounts for DPD calculation | `Not specified` | Selects accounts with DPD_Overdrawn greater than 30 or DPD_Overdue greater than 0 and inserts them into a temporary table. |
| Reset negative DPD values to zero | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | Resets negative values in various DPD fields to zero in the temporary table. |
| Initialize DPD values | `DPD_Max` | Sets the maximum DPD value to zero for reprocessing. |
| Calculate maximum DPD | `DPD_Max` | Determines the maximum DPD value for each account based on various DPD types. |
| Reset SMA class | `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA` | Clears the SMA class, reason, date, and flag for all accounts. |
| Initialize customer flags | `FLGSMA, SMA_CLASS_KEY, SMA_DT` | Sets FLGSMA, SMA_CLASS_KEY, and SMA_DT to NULL in the ##CUSTOMERCAL table. |
| Set customer flag to Y | `FLGSMA` | Sets FLGSMA to 'Y' in the ##CUSTOMERCAL table for accounts that meet certain conditions. |
| Create temporary SMA class table | `Not specified` | Creates a temporary table #TEMPTABLE_SMACLASS to store aggregated SMA class information. |
| Update SMA class key and date | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the information in the temporary table #TEMPTABLE_SMACLASS. |
| Delete existing SMA movement history | `Not specified` | Deletes the existing SMA movement history record for the given time key if it exists. |
| Create temporary SMA class table for UCIF | `Not specified` | Creates a temporary table #TEMPTABLE_SMACLASSUcif to store aggregated SMA class information for UCIF. |
| Update UCIF SMA class key and date | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the information in the temporary table #TEMPTABLE_SMACLASSUcif. |
| Create temporary SMA class table for movement history | `Not specified` | Creates a temporary table #SMACLASS to store SMA class information for accounts that meet certain conditions. |
| Insert SMA movement history | `Not specified` | Inserts a new record into the SMA movement history table with the previous and current SMA class for accounts that have changed status. |
| Truncate previous SMA status table | `Not specified` | Truncates the PREVSMASTATUS table to remove old records. |
| Update customer movement history | `EffectiveToTimeKey, MovementToDate` | Updates the customer movement history with the effective to time key and movement to date for specific conditions. |
| Update account details | `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal` | Updates account details such as continuous excess date, DPD overdrawn, review due date, and DPD renewal. |

## Business Rules

### R1 — Select accounts for SMA Aqua Scheme

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Selects accounts under the SMA Aqua Scheme with specific conditions and inserts them into a temporary table.


### R2 — Reset ContiExcessDt and DPD_Overdrawn to zero

**Affected Field:** `ContiExcessDt, DPD_Overdrawn`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Updates the ContiExcessDt and DPD_Overdrawn fields to zero for accounts with DPD_Overdrawn less than or equal to 30.


### R3 — Reset ReviewDueDt and DPD_Renewal to zero

**Affected Field:** `ReviewDueDt, DPD_Renewal`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Updates the ReviewDueDt and DPD_Renewal fields to zero for accounts with DPD_Overdrawn less than or equal to 30.


### R4 — Select accounts for DPD calculation

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Selects accounts with DPD_Overdrawn greater than 30 or DPD_Overdue greater than 0 and inserts them into a temporary table.


### R5 — Reset negative DPD values to zero

**Affected Field:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets negative values in various DPD fields to zero in the temporary table.


### R6 — Initialize DPD values

**Affected Field:** `DPD_Max`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Sets the maximum DPD value to zero for reprocessing.


### R7 — Calculate maximum DPD

**Affected Field:** `DPD_Max`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Determines the maximum DPD value for each account based on various DPD types.


### R8 — Reset SMA class

**Affected Field:** `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Clears the SMA class, reason, date, and flag for all accounts.


### R9 — Initialize customer flags

**Affected Field:** `FLGSMA, SMA_CLASS_KEY, SMA_DT`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Sets FLGSMA, SMA_CLASS_KEY, and SMA_DT to NULL in the ##CUSTOMERCAL table.


### R10 — Set customer flag to Y

**Affected Field:** `FLGSMA`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Sets FLGSMA to 'Y' in the ##CUSTOMERCAL table for accounts that meet certain conditions.


### R11 — Create temporary SMA class table

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Creates a temporary table #TEMPTABLE_SMACLASS to store aggregated SMA class information.


### R12 — Update SMA class key and date

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the information in the temporary table #TEMPTABLE_SMACLASS.


### R13 — Delete existing SMA movement history

**Affected Field:** Not specified

**Applies to:**

- EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY)

**Summary:**

- Deletes the existing SMA movement history record for the given time key if it exists.


### R14 — Create temporary SMA class table for UCIF

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Creates a temporary table #TEMPTABLE_SMACLASSUcif to store aggregated SMA class information for UCIF.


### R15 — Update UCIF SMA class key and date

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the information in the temporary table #TEMPTABLE_SMACLASSUcif.


### R16 — Create temporary SMA class table for movement history

**Affected Field:** Not specified

**Applies to:**

- B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1

**Summary:**

- Creates a temporary table #SMACLASS to store SMA class information for accounts that meet certain conditions.


### R17 — Insert SMA movement history

**Affected Field:** Not specified

**Applies to:**

- B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'')

**Summary:**

- Inserts a new record into the SMA movement history table with the previous and current SMA class for accounts that have changed status.


### R18 — Truncate previous SMA status table

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Truncates the PREVSMASTATUS table to remove old records.


### R19 — Update customer movement history

**Affected Field:** `EffectiveToTimeKey, MovementToDate`

**Applies to:**

- AA.EffectiveToTimeKey = 49999
- AA.EffectiveFROMTimeKey < @TIMEKEY
- EXISTS(SELECT 1 FROM #Customer_MOVEMENT_HISTORY AS BB WHERE AA.SourceSystemCustomerID = BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS)

**Summary:**

- Updates the customer movement history with the effective to time key and movement to date for specific conditions.


### R20 — Update account details

**Affected Field:** `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal`

**Applies to:**

- A.AccountEntityID = B.AccountEntityID

**Summary:**

- Updates account details such as continuous excess date, DPD overdrawn, review due date, and DPD renewal.

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

If an error occurs, the running process status is updated to mark the SMA_MARKING process as failed, and temporary tables are dropped.

## Findings / Needs Review

- Affected regions: lines 19-19, 24-24, 36-41, 106-118, 111-118 (+5 more) (10 total) - needs review after a larger output budget or chunked synthesis.
- Business rule synthesis returned malformed JSON and could not be parsed; the full object needs manual review.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic. Affected regions: lines 19-19, 24-24, 36-41, 106-118, 111-118 (+5 more) (10 total) - needs review after a larger output budget or chunked synthesis.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
