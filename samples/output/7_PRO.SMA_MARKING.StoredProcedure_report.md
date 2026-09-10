# SMA Marking — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_MARKING` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 32 |
| Tables read | 9 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure updates and calculates various overdue days and provisioning amounts for accounts under the SMA Aqua Scheme, ensuring that negative values are reset to zero and certain conditions are met for account classification and processing. This procedure calculates the maximum days past due (DPD) for accounts and updates the SMA class based on the calculated DPD values. This procedure assigns a Special Mention Account (SMA) classification to accounts based on their overdue days and facility type, and updates related fields accordingly. The procedure SMA_MARKING updates various fields in the ##CUSTOMERCAL and ##AccountCal tables to mark the status of customer accounts based on their overdue days and asset classification. It also updates the movement history and previous status tables to track changes in account status over time. This procedure updates the SMA class for accounts and inserts or updates account and customer movement history records based on the provided time key. The SMA_MARKING procedure updates customer movement history and account details for SMA Aqua Scheme, ensuring accurate tracking of account statuses and movements.

## Process Flow

1. Initializes the process by setting the process date and effective time.
2. Drops temporary tables if they exist.
3. Selects accounts under the SMA Aqua Scheme and inserts them into a temporary table.
4. Updates the ContiExcessDt and DPD_Overdrawn fields to zero for accounts with DPD_Overdrawn less than or equal to 30.
5. Updates the ReviewDueDt and DPD_Renewal fields to zero for accounts with DPD_Overdrawn less than or equal to 30.
6. Inserts account details into another temporary table if DPD_Overdrawn is greater than 30 or DPD_Overdue is greater than 0.
7. Resets negative DPD values to zero in the temporary table.
8. Calculates the maximum DPD value.
9. Initializes a temporary table to store DPD values.
10. Updates the DPD_Max field in the #DPD table to zero.
11. Calculates the maximum DPD value for each account and updates the DPD_Max field in the #DPD table.
12. Resets the SMA class, reason, date, and flag in the ##AccountCal table to null.
13. Updates the SMA class, reason, date, and flag for accounts based on their overdue days and facility type.
14. Reads data from various tables to determine the SMA classification and related details.
15. Initializes the ##CUSTOMERCAL table by setting FLGSMA, SMA_CLASS_KEY, and SMA_DT to NULL.
16. Updates the ##CUSTOMERCAL table to set FLGSMA to 'Y' for accounts that meet certain conditions.
17. Creates temporary tables #TEMPTABLE_SMACLASS and #TEMPTABLE_SMACLASSUcif to store aggregated data on SMA_CLASS and SMA_Dt.
18. Updates the ##CUSTOMERCAL table to set SMA_CLASS_KEY and SMA_DT based on the data in the temporary tables.
19. Checks if a record exists in the PRO.SMA_MOVEMENT_HISTORY table for the given TIMEKEY and deletes it if it does.
20. Creates a temporary table #SMACLASS to store SMA_CLASS values for accounts that meet certain conditions.
21. Updates the #SMACLASS table to map SMA_CLASS values to numeric codes.
22. Inserts records into the PRO.SMA_MOVEMENT_HISTORY table to track changes in SMA_CLASS.
23. Truncates the PRO.PREVSMASTATUS table to remove old records.
24. Inserts records into the PRO.PREVSMASTATUS table to store the previous SMA_CLASS values.
25. Updates the ##CUSTOMERCAL table to set CustMoveDescription based on the SYSASSETCLASSALT_KEY.
26. Updates the ##AccountCal table to set SMA_CLASS based on the FinalAssetClassAlt_Key.
27. Check if there is existing data for the given time key in the account movement history table. If so, print a message and do not insert new data.
28. If no existing data is found, drop the temporary account movement history table if it exists.
29. Create a temporary account movement history table and insert data from the account calendar table.
30. Insert data from the temporary account movement history table into the account movement history table.
31. Update the effective end time and movement end date in the account movement history table based on certain conditions.
32. Check if there is existing data for the given time_ INSERTION_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_
33. SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_S
34. SMA_SMA_SMA_SMA_SMA_SMA_SMA_SMA_
35. Updates customer movement history with the effective to time key and movement to date.
36. Updates account details such as continuous excess date, DPD overdrawn, review due date, and DPD renewal for SMA Aqua Scheme.
37. Updates the running process status for SMA_MARKING to indicate completion or error.
38. Handles exceptions by rolling back changes and updating the running process status with error details.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Initialize temporary table | `Not specified` | Creates a temporary table to store DPD values for further processing. |
| Reset DPD_Max to zero | `DPD_Max` | Resets the DPD_Max field in the #DPD table to zero for all accounts. |
| Calculate maximum DPD | `DPD_Max` | Calculates the maximum DPD value for each account and updates the DPD_Max field in the #DPD table. |
| Reset SMA class | `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA` | Resets the SMA class, reason, date, and flag in the ##AccountCal table to null for all accounts. |
| Set ContiExcessDt and DPD_Overdrawn to zero | `ContiExcessDt, DPD_Overdrawn` | For accounts with DPD_Overdrawn less than or equal to 30, the ContiExcessDt and DPD_Overdrawn fields are set to zero. |
| Set ReviewDueDt and DPD_Renewal to zero | `ReviewDueDt, DPD_Renewal` | For accounts with DPD_Overdrawn less than or equal to 30, the ReviewDueDt and DPD_Renewal fields are set to zero. |
| Insert account details if DPD_Overdrawn or DPD_Overdue is greater than 0 | `AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_MAX` | Inserts account details into a temporary table if DPD_Overdrawn is greater than 30 or DPD_Overdue is greater than 0. |
| Reset negative DPD values to zero | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | Resets negative values of DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt to zero. |
| Assign SMA class based on overdue days | `SMA_CLASS` | Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2. |
| Assign SMA class based on overdue days | `SMA_CLASS` | Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2. |
| Assign SMA class based on overdue days | `SMA_CLASS` | Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2. |
| Assign SMA class based on overdue days | `SMA_CLASS` | Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days. |
| Initialize customer fields | `FLGSMA, SMA_CLASS_KEY, SMA_DT` | Sets the FLGSMA, SMA_CLASS_KEY, and SMA_DT fields in the ##CUSTOMERCAL table to NULL. |
| Set FLGSMA to 'Y' | `FLGSMA` | Sets the FLGSMA field in the ##CUSTOMERCAL table to 'Y' for accounts that meet certain conditions. |
| Create temporary table #TEMPTABLE_SMACLASS | `Not specified` | Creates a temporary table #TEMPTABLE_SMACLASS to store aggregated data on SMA_CLASS and SMA_Dt for accounts that meet certain conditions. |
| Update SMA_CLASS_KEY and SMA_DT | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the data in the temporary table #TEMPTABLE_SMACLASS. |
| Delete existing SMA_MOVEMENT_HISTORY record | `Not specified` | Deletes the existing record in the PRO.SMA_MOVEMENT_HISTORY table for the given TIMEKEY if it exists. |
| Create temporary table #SMACLASS | `Not specified` | Creates a temporary table #SMACLASS to store SMA_CLASS values for accounts that meet certain conditions. |
| Map SMA_CLASS to numeric codes | `SMA_CLASS` | Updates the #SMACLASS table to map SMA_CLASS values to numeric codes. |
| Insert into SMA_MOVEMENT_HISTORY | `Not specified` | Inserts records into the PRO.SMA_MOVEMENT_HISTORY table to track changes in SMA_CLASS. |
| Truncate PREVSMASTATUS table | `Not specified` | Truncates the PRO.PREVSMASTATUS table to remove old records. |
| Update CustMoveDescription based on SYSASSETCLASSALT_KEY | `CustMoveDescription` | Updates the CustMoveDescription field in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY. |
| Update SMA_CLASS based on FinalAssetClassAlt_Key | `SMA_CLASS` | Updates the SMA_CLASS field in the ##AccountCal table based on the FinalAssetClassAlt_Key. |
| Update customer movement history | `EffectiveToTimeKey, MovementToDate` | Updates the effective to time key and movement to date in the customer movement history table for specific conditions. |
| Update account details for SMA Aqua Scheme | `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal` | Updates account details such as continuous excess date, DPD overdrawn, review due date, and DPD renewal for SMA Aqua Scheme. |

## Business Rules

### R1 — Initialize temporary table

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Creates a temporary table to store DPD values for further processing.


### R2 — Reset DPD_Max to zero

**Affected Field:** `DPD_Max`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_Max field in the #DPD table to zero for all accounts.


### R3 — Calculate maximum DPD

**Affected Field:** `DPD_Max`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Calculates the maximum DPD value for each account and updates the DPD_Max field in the #DPD table.


### R4 — Reset SMA class

**Affected Field:** `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the SMA class, reason, date, and flag in the ##AccountCal table to null for all accounts.


### R5 — Set ContiExcessDt and DPD_Overdrawn to zero

**Affected Field:** `ContiExcessDt, DPD_Overdrawn`

**Applies to:**

- Account is under the SMA Aqua Scheme
- Account's DPD_Overdrawn is less than or equal to 30

**Summary:**

- For accounts with DPD_Overdrawn less than or equal to 30, the ContiExcessDt and DPD_Overdrawn fields are set to zero.


### R6 — Set ReviewDueDt and DPD_Renewal to zero

**Affected Field:** `ReviewDueDt, DPD_Renewal`

**Applies to:**

- Account is under the SMA Aqua Scheme
- Account's DPD_Overdrawn is less than or equal to 30

**Summary:**

- For accounts with DPD_Overdrawn less than or equal to 30, the ReviewDueDt and DPD_Renewal fields are set to zero.


### R7 — Insert account details if DPD_Overdrawn or DPD_Overdue is greater than 0

**Affected Field:** `AccountEntityID, UcifEntityID, CustomerEntityID, CustomerAcID, RefCustomerID, SourceSystemCustomerID, UCIF_ID, IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, RefPeriodIntService, RefPeriodNoCredit, RefPeriodOverDrawn, RefPeriodOverdue, RefPeriodReview, RefPeriodStkStatement, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_MAX`

**Applies to:**

- Account's DPD_Overdrawn is greater than 30 or DPD_Overdue is greater than 0

**Summary:**

- Inserts account details into a temporary table if DPD_Overdrawn is greater than 30 or DPD_Overdue is greater than 0.


### R8 — Reset negative DPD values to zero

**Affected Field:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt`

**Applies to:**

- DPD value is negative

**Summary:**

- Resets negative values of DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, and DPD_StockStmt to zero.


### R9 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2.


### R10 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2.


### R11 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2.


### R12 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns an SMA class to accounts based on the maximum overdue days, categorizing them into SMA_0, SMA_1, or SMA_2.


### R13 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days.


### R14 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days.


### R15 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days.


### R16 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days.


### R17 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days.


### R18 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days.


### R19 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns a reason for the SMA classification based on the facility type and the reason for the overdue days.


### R20 — Initialize customer fields

**Affected Field:** `FLGSMA, SMA_CLASS_KEY, SMA_DT`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Sets the FLGSMA, SMA_CLASS_KEY, and SMA_DT fields in the ##CUSTOMERCAL table to NULL.


### R21 — Set FLGSMA to 'Y'

**Affected Field:** `FLGSMA`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Sets the FLGSMA field in the ##CUSTOMERCAL table to 'Y' for accounts that meet certain conditions.


### R22 — Create temporary table #TEMPTABLE_SMACLASS

**Affected Field:** Not specified

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Creates a temporary table #TEMPTABLE_SMACLASS to store aggregated data on SMA_CLASS and SMA_Dt for accounts that meet certain conditions.


### R23 — Update SMA_CLASS_KEY and SMA_DT

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the data in the temporary table #TEMPTABLE_SMACLASS.


### R24 — Delete existing SMA_MOVEMENT_HISTORY record

**Affected Field:** Not specified

**Applies to:**

- EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY)

**Summary:**

- Deletes the existing record in the SMA_MOVEMENT_HISTORY table for the given TIMEKEY if it exists.


### R25 — Create temporary table #SMACLASS

**Affected Field:** Not specified

**Applies to:**

- B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1

**Summary:**

- Creates a temporary table #SMACLASS to store SMA_CLASS values for accounts that meet certain conditions.


### R26 — Map SMA_CLASS to numeric codes

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Updates the #SMACLASS table to map SMA_CLASS values to numeric codes.


### R27 — Insert into SMA_MOVEMENT_HISTORY

**Affected Field:** Not specified

**Applies to:**

- B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'')

**Summary:**

- Inserts records into the SMA_MOVEMENT_HISTORY table to track changes in SMA_CLASS.


### R28 — Truncate PREVSMASTATUS table

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Truncates the PREVSMASTATUS table to remove old records.


### R29 — Update CustMoveDescription based on SYSASSETCLASSALT_KEY

**Affected Field:** `CustMoveDescription`

**Applies to:**

- SYSASSETCLASSALT_KEY=1

**Summary:**

- Updates the CustMoveDescription field in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY.


### R30 — Update SMA_CLASS based on FinalAssetClassAlt_Key

**Affected Field:** `SMA_CLASS`

**Applies to:**

- FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL

**Summary:**

- Updates the SMA_CLASS field in the ##AccountCal table based on the FinalAssetClassAlt_Key.


### R31 — Update customer movement history

**Affected Field:** `EffectiveToTimeKey, MovementToDate`

**Applies to:**

- Customer movement history record exists
- Effective to time key is 49999
- Effective from time key is less than @TIMEKEY
- Movement to status differs from the previous status

**Summary:**

- Updates the effective to time key and movement to date in the customer movement history table for specific conditions.


### R32 — Update account details for SMA Aqua Scheme

**Affected Field:** `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal`

**Applies to:**

- Account entity ID matches between ##ACCOUNTCAL and #DPD_Aqua_SMA

**Summary:**

- Updates account details such as continuous excess date, DPD overdrawn, review due date, and DPD renewal for SMA Aqua Scheme.

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

In case of an exception, the procedure rolls back changes, drops temporary tables, and updates the running process status with error details.

## Findings / Needs Review

- Affected regions: lines 19-19, 24-24, 36-41, 106-110, 340-346 (+5 more) (10 total) - needs review after a larger output budget or chunked synthesis.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic. Affected regions: lines 19-19, 24-24, 36-41, 106-110, 340-346 (+5 more) (10 total) - needs review after a larger output budget or chunked synthesis.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
