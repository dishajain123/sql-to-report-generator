# SMA Marking — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_MARKING` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 30 |
| Tables read | 9 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure updates and calculates various overdue and renewal days for accounts under the SMA Aqua Scheme, ensuring that negative values are reset to zero and certain conditions are met for account classification and processing. The SMA_MARKING procedure processes account data to determine the maximum days past due (DPD) and resets the SMA classification and related fields for accounts. This procedure assigns a Special Mention Account (SMA) classification to accounts based on their overdue days and facility type, updating the account's SMA class, reason, date, and flag. The procedure SMA_MARKING processes customer account data to update and classify accounts based on their overdue status and asset class. It involves resetting certain flags, updating classification keys, and setting movement descriptions for accounts. The procedure SMA_MARKING updates the SMA class for accounts and inserts or updates movement history records based on the account's asset class and movement status. The SMA_MARKING procedure updates customer movement history, account calendar details, and running process status based on specific conditions and time keys.

## Process Flow

1. Initializes temporary tables to store account data.
2. Updates account data based on specific conditions related to overdue and renewal days.
3. Resets negative values in calculated overdue and renewal days to zero.
4. Calculates the maximum overdue and renewal days for accounts.
5. Initializes a temporary table to store DPD values.
6. Updates the DPD_Max field in the #DPD table to zero.
7. Calculates the maximum DPD value for each account and updates the DPD_Max field in the #DPD table.
8. Resets the SMA classification, reason, date, and flag in the ##AccountCal table to null.
9. Update the account's SMA class, reason, date, and flag based on the maximum overdue days and facility type.
10. Read relevant data from the ##AccountCal, ##CUSTOMERCAL, AdvAcBasicDetail, and #DPD tables to determine the SMA classification.
11. Resets the FLGSMA, SMA_CLASS_KEY, and SMA_DT flags in the ##CUSTOMERCAL table to NULL.
12. Updates the FLGSMA flag in the ##CUSTOMERCAL table to 'Y' for accounts that meet certain conditions.
13. Drops the temporary table #TEMPTABLE_SMACLASS if it exists.
14. Creates a temporary table #TEMPTABLE_SMACLASS with customer entity ID, maximum SMA class, and minimum SMA date from the ##AccountCal and ##CUSTOMERCAL tables.
15. Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the data from the temporary table #TEMPTABLE_SMACLASS.
16. Updates the FLGSMA flag in the ##CUSTOMERCAL table to 'Y' for accounts that meet certain conditions based on UCIF_ID.
17. Drops the temporary table #TEMPTABLE_SMACLASSUcif if it exists.
18. Creates a temporary table #TEMPTABLE_SMACLASSUcif with UCIF_ID, maximum SMA class, and minimum SMA date from the ##AccountCal and ##CUSTOMERCAL tables.
19. Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the data from the temporary table #TEMPTABLE_SMACLASSUcif.
20. Deletes records from the PRO.SMA_MOVEMENT_HISTORY table if they exist for the given TIMEKEY.
21. Drops the temporary table #SMACLASS if it exists.
22. Creates a temporary table #SMACLASS with customer account ID and SMA class from the ##AccountCal and ##CUSTOMERCAL tables.
23. Updates the SMA_CLASS in the temporary table #SMACLASS based on certain conditions.
24. Inserts records into the PRO.SMA_MOVEMENT_HISTORY table from the PRO.PREVSMASTATUS and #SMACLASS tables.
25. Truncates the PRO.PREVSMASTATUS table.
26. Inserts records into the PRO.PREVSMASTATUS table from the #SMACLASS table.
27. Updates the CustMoveDescription in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY.
28. Updates the CustMoveDescription in the ##CUSTOMERCAL table based on the SMA_CLASS_KEY.
29. Updates the SMA_CLASS in the ##AccountCal table based on the FinalAssetClassAlt_Key.
30. Check if there is existing movement history for the specified time key. If not, proceed to insert new records.
31. Update the SMA class for accounts with a specific asset class if it is currently NULL.
32. Insert new movement history records for accounts if certain conditions are met.
33. Update the effective end date and movement end date for existing movement history records under specific conditions.
34. Updates customer movement history records where the effective to time key is 49999 and the movement to status has changed.
35. Updates account calendar details with values from a temporary table based on account entity ID.
36. Updates the running process status for the SMA_MARKING process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Initialize DPD values | `Not specified` | Creates a temporary table to store DPD values for further processing. |
| Reset DPD_Max to zero | `DPD_Max` | Resets the DPD_Max field in the #DPD table to zero for all accounts. |
| Calculate maximum DPD | `DPD_Max` | Calculates the maximum DPD value for each account and updates the DPD_Max field in the #DPD table. |
| Reset SMA classification | `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA` | Resets the SMA classification, reason, date, and flag in the ##AccountCal table to null. |
| Create temporary table for SMA Aqua accounts | `Not specified` | Creates a temporary table to store account data for accounts under the SMA Aqua Scheme that meet specific conditions. |
| Update ContiExcessDt and DPD_Overdrawn for SMA Aqua accounts | `ContiExcessDt, DPD_Overdrawn` | Updates the ContiExcessDt and DPD_Overdrawn fields to zero for accounts under the SMA Aqua Scheme that meet specific conditions. |
| Update ReviewDueDt and DPD_Renewal for SMA Aqua accounts | `ReviewDueDt, DPD_Renewal` | Updates the ReviewDueDt and DPD_Renewal fields to zero for accounts under the SMA Aqua Scheme that meet specific conditions. |
| Reset negative DPD_IntService | `DPD_IntService` | Resets the DPD_IntService field to zero if it is negative. |
| Reset negative DPD_NoCredit | `DPD_NoCredit` | Resets the DPD_NoCredit field to zero if it is negative. |
| Reset negative DPD_Overdrawn | `DPD_Overdrawn` | Resets the DPD_Overdrawn field to zero if it is negative. |
| Reset negative DPD_Overdue | `DPD_Overdue` | Resets the DPD_Overdue field to zero if it is negative. |
| Reset negative DPD_Renewal | `DPD_Renewal` | Resets the DPD_Renewal field to zero if it is negative. |
| Reset negative DPD_StockStmt | `DPD_StockStmt` | Resets the DPD_StockStmt field to zero if it is negative. |
| Assign SMA class based on overdue days | `SMA_CLASS` | Sets the account's SMA class based on the maximum number of overdue days and facility type. |
| Assign SMA class based on overdue days | `SMA_CLASS` | Sets the account's SMA class to 'SMA_1' if the maximum number of overdue days is between 31 and 60. |
| Assign SMA class based on overdue days | `SMA_CLASS` | Sets the account's SMA class to 'SMA_2' if the maximum number of overdue days is between 61 and 90 or greater than 90. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Sets the account's SMA reason based on the facility type and the reason for the maximum overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Sets the account's SMA reason to 'DEGRADE BY NO CREDIT' if the facility type is 'CC' or 'OD' and the maximum overdue days are due to no cre… |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Sets the account's SMA reason to 'DEGRADE BY OVERDUE' if the facility type is 'TL', 'DL', 'BP', 'BD', or 'PC' and the maximum overdue days… |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | Sets the account's SMA reason to 'DEGRADE BY CONTI EXCESS' if the facility type is 'CC' or 'OD' and the maximum overdue days are due to con… |
| Reset customer flags | `FLGSMA, SMA_CLASS_KEY, SMA_DT` | Resets the FLGSMA, SMA_CLASS_KEY, and SMA_DT flags in the ##CUSTOMERCAL table to NULL. |
| Set FLGSMA to 'Y' for certain accounts | `FLGSMA` | Updates the FLGSMA flag in the ##CUSTOMERCAL table to 'Y' for accounts that meet certain conditions. |
| Create temporary table with SMA class data | `CustomerEntityID, MAXSMA_CLASS, SMA_Dt` | Creates a temporary table #TEMPTABLE_SMACLASS with customer entity ID, maximum SMA class, and minimum SMA date from the ##AccountCal and ##… |
| Update SMA class key and date from temp table | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the data from the temporary table #TEMPTABLE_SMACLASS. |
| Set FLGSMA to 'Y' for UCIF-based accounts | `FLGSMA` | Updates the FLGSMA flag in the ##CUSTOMERCAL table to 'Y' for accounts that meet certain conditions based on UCIF_ID. |
| Create UCIF-based temporary table with SMA class data | `UCIF_ID, MAXSMA_CLASS, SMA_Dt` | Creates a temporary table #TEMPTABLE_SMACLASSUcif with UCIF_ID, maximum SMA class, and minimum SMA date from the ##AccountCal and ##CUSTOME… |
| Update UCIF-based SMA class key and date from temp table | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the data from the temporary table #TEMPTABLE_SMACLASSUcif. |
| Delete SMA movement history for given TIMEKEY | `Not specified` | Deletes records from the PRO.SMA_MOVEMENT_HISTORY table if they exist for the given TIMEKEY. |
| Update customer movement history | `EffectiveToTimeKey, MovementToDate` | Updates customer movement history records where the effective to time key is 49999 and the movement to status has changed. |
| Update account calendar details | `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal` | Updates account calendar details with values from a temporary table based on account entity ID. |

## Business Rules

### R1 — Initialize DPD values

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


### R4 — Reset SMA classification

**Affected Field:** `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the SMA classification, reason, date, and flag in the ##AccountCal table to null.


### R5 — Create temporary table for SMA Aqua accounts

**Affected Field:** Not specified

**Applies to:**

- Account is under the SMA Aqua Scheme
- Account's scheme type is ODA
- Account's facility type is CC or OD
- Account's REFPERIODOVERDRAWN is 91
- Account's FinalAssetClassAlt_Key is 1

**Summary:**

- Creates a temporary table to store account data for accounts under the SMA Aqua Scheme that meet specific conditions.


### R6 — Update ContiExcessDt and DPD_Overdrawn for SMA Aqua accounts

**Affected Field:** `ContiExcessDt, DPD_Overdrawn`

**Applies to:**

- Account's DPD_Overdrawn is less than or equal to 30

**Summary:**

- Updates the ContiExcessDt and DPD_Overdrawn fields to zero for accounts under the SMA Aqua Scheme that meet specific conditions.


### R7 — Update ReviewDueDt and DPD_Renewal for SMA Aqua accounts

**Affected Field:** `ReviewDueDt, DPD_Renewal`

**Applies to:**

- Account's DPD_Overdrawn is less than or equal to 30

**Summary:**

- Updates the ReviewDueDt and DPD_Renewal fields to zero for accounts under the SMA Aqua Scheme that meet specific conditions.


### R8 — Reset negative DPD_IntService

**Affected Field:** `DPD_IntService`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_IntService field to zero if it is negative.


### R9 — Reset negative DPD_NoCredit

**Affected Field:** `DPD_NoCredit`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_NoCredit field to zero if it is negative.


### R10 — Reset negative DPD_Overdrawn

**Affected Field:** `DPD_Overdrawn`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_Overdrawn field to zero if it is negative.


### R11 — Reset negative DPD_Overdue

**Affected Field:** `DPD_Overdue`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_Overdue field to zero if it is negative.


### R12 — Reset negative DPD_Renewal

**Affected Field:** `DPD_Renewal`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_Renewal field to zero if it is negative.


### R13 — Reset negative DPD_StockStmt

**Affected Field:** `DPD_StockStmt`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the DPD_StockStmt field to zero if it is negative.


### R14 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:**

- Customer is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- Overdue days or overdrawn days are non-negative
- Maximum overdue days is greater than zero

**Summary:**

- Sets the account's SMA class based on the maximum number of overdue days and facility type.


### R15 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:**

- Customer is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- Overdue days or overdrawn days are non-negative
- Maximum overdue days is greater than zero

**Summary:**

- Sets the account's SMA class to 'SMA_1' if the maximum number of overdue days is between 31 and 60.


### R16 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:**

- Customer is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- Overdue days or overdrawn days are non-negative
- Maximum overdue days is greater than zero

**Summary:**

- Sets the account's SMA class to 'SMA_2' if the maximum number of overdue days is between 61 and 90 or greater than 90.


### R17 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:**

- Customer is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- Overdue days or overdrawn days are non-negative
- Maximum overdue days is greater than zero

**Summary:**

- Sets the account's SMA reason based on the facility type and the reason for the maximum overdue days.


### R18 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:**

- Customer is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- Overdue days or overdrawn days are non-negative
- Maximum overdue days is greater than zero

**Summary:**

- Sets the account's SMA reason to 'DEGRADE BY NO CREDIT' if the facility type is 'CC' or 'OD' and the maximum overdue days are due to no credit.


### R19 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:**

- Customer is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- Overdue days or overdrawn days are non-negative
- Maximum overdue days is greater than zero

**Summary:**

- Sets the account's SMA reason to 'DEGRADE BY OVERDUE' if the facility type is 'TL', 'DL', 'BP', 'BD', or 'PC' and the maximum overdue days are due to overdue.


### R20 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:**

- Customer is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- Overdue days or overdrawn days are non-negative
- Maximum overdue days is greater than zero

**Summary:**

- Sets the account's SMA reason to 'DEGRADE BY CONTI EXCESS' if the facility type is 'CC' or 'OD' and the maximum overdue days are due to continuous excess and the overdrawn days are greater than 30.


### R21 — Reset customer flags

**Affected Field:** `FLGSMA, SMA_CLASS_KEY, SMA_DT`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the FLGSMA, SMA_CLASS_KEY, and SMA_DT flags in the ##CUSTOMERCAL table to NULL.


### R22 — Set FLGSMA to 'Y' for certain accounts

**Affected Field:** `FLGSMA`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Updates the FLGSMA flag in the ##CUSTOMERCAL table to 'Y' for accounts that meet certain conditions.


### R23 — Create temporary table with SMA class data

**Affected Field:** `CustomerEntityID, MAXSMA_CLASS, SMA_Dt`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Creates a temporary table #TEMPTABLE_SMACLASS with customer entity ID, maximum SMA class, and minimum SMA date from the ##AccountCal and ##CUSTOMERCAL tables.


### R24 — Update SMA class key and date from temp table

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the data from the temporary table #TEMPTABLE_SMACLASS.


### R25 — Set FLGSMA to 'Y' for UCIF-based accounts

**Affected Field:** `FLGSMA`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Updates the FLGSMA flag in the ##CUSTOMERCAL table to 'Y' for accounts that meet certain conditions based on UCIF_ID.


### R26 — Create UCIF-based temporary table with SMA class data

**Affected Field:** `UCIF_ID, MAXSMA_CLASS, SMA_Dt`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Creates a temporary table #TEMPTABLE_SMACLASSUcif with UCIF_ID, maximum SMA class, and minimum SMA date from the ##AccountCal and ##CUSTOMERCAL tables.


### R27 — Update UCIF-based SMA class key and date from temp table

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the data from the temporary table #TEMPTABLE_SMACLASSUcif.


### R28 — Delete SMA movement history for given TIMEKEY

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Deletes records from the SMA_MOVEMENT_HISTORY table if they exist for the given TIMEKEY.


### R29 — Update customer movement history

**Affected Field:** `EffectiveToTimeKey, MovementToDate`

**Applies to:**

- Customer movement history record exists
- Effective to time key is 49999
- Movement to status has changed

**Summary:**

- Updates customer movement history records where the effective to time key is 49999 and the movement to status has changed.


### R30 — Update account calendar details

**Affected Field:** `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal`

**Applies to:**

- Account entity ID matches between temporary table and account calendar

**Summary:**

- Updates account calendar details with values from a temporary table based on account entity ID.

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

In case of an error, the procedure updates the running process status to indicate failure, sets the error date and description, and increments the count.

## Findings / Needs Review

- Affected regions: lines 19-19, 24-24, 36-41, 400-453, 511-550 (+3 more) (8 total) - needs review after a larger output budget or chunked synthesis.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic. Affected regions: lines 19-19, 24-24, 36-41, 400-453, 511-550 (+3 more) (8 total) - needs review after a larger output budget or chunked synthesis.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
