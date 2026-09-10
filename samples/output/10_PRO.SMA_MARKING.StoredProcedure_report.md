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

This procedure updates and calculates various overdue days and provisioning amounts for accounts under the SMA Aqua Scheme, ensuring that negative values are reset to zero and certain conditions are met for account classification and processing. The SMA_MARKING procedure processes and updates various overdue and renewal-related fields in the banking system, ensuring that the maximum overdue days and renewal days are correctly calculated and stored for each account. This procedure assigns SMA (Serious Misconduct Account) classifications to accounts based on their overdue days and facility type, updating the account's SMA class, reason, date, and flag status. The SMA_MARKING procedure updates various fields related to the Special Mention Account (SMA) classification and movement history for customer accounts based on their financial status and overdue days. The procedure SMA_MARKING updates account movement history records and SMA class statuses based on specific conditions related to account asset classes and movement statuses. The SMA_MARKING procedure updates customer movement history, account details, and running process status based on specific conditions related to account status changes and overdue days.

## Process Flow

1. Initializes the process by setting the process date and effective time.
2. Drops temporary tables if they exist.
3. Selects accounts under the SMA Aqua Scheme and inserts them into a temporary table.
4. Updates the ContiExcessDt and DPD_Overdrawn fields to zero for accounts with DPD_Overdrawn less than or equal to 30.
5. Updates the ReviewDueDt and DPD_Renewal fields to zero for accounts with DPD_Overdrawn less than or equal to 30.
6. Inserts account details into another temporary table if DPD_Overdrawn is greater than 30 or DPD_Overdue is greater than 0.
7. Resets negative DPD values to zero in the temporary table.
8. Calculates the maximum DPD value.
9. Initializes the temporary table #TEMPTABLE with selected fields from the #DPD table, comparing various overdue and renewal-related fields to their respective reference period fields.
10. Updates the DPD_Max field in the #DPD table to zero for reprocessing data.
11. Calculates the maximum overdue days (DPD_Max) for each account by comparing various overdue and renewal-related fields.
12. Resets the SMA_CLASS, SMA_REASON, SMA_DT, and FLGSMA fields in the ##AccountCal table to NULL.
13. Updates the account's SMA class based on the maximum overdue days.
14. Updates the account's SMA reason based on the facility type and the reason for the maximum overdue days.
15. Sets the account's SMA date to the date calculated by subtracting the maximum overdue days from the process date.
16. Marks the account as having an SMA flag.
17. Initializes temporary tables to store SMA class and date information.
18. Updates the customer account table with SMA flags and keys based on account balance and asset class.
19. Updates the UCIF ID and SMA date information in the account table based on the UCIF ID and SMA flag.
20. Inserts SMA class and date information into temporary tables for further processing.
21. Updates the customer account table with SMA class and date information from the temporary tables.
22. Deletes existing SMA movement history for the specified time key if it exists.
23. Inserts new SMA movement history into the SMA movement history table.
24. Truncates the previous SMA status table.
25. Inserts the current SMA status into the previous SMA status table.
26. Updates the customer movement description based on the system asset class alternate key and SMA class key.
27. Check if there are any existing account movement history records for the given time key. If not, proceed to insert new records.
28. Update the SMA class for accounts with a specific asset class and no existing SMA class.
29. Insert new account movement history records if no existing records are found for the given time key.
30. Update the effective end time and movement end date for account movement history records with certain conditions.
31. Check if there are any existing customer movement history records for the given time key. If not, proceed to insert new records.
32. Insert new customer movement history records if no existing records are found for the given time key.
33. Update the effective end time and movement end date for customer movement history records with certain conditions.
34. Updates the customer movement history with the effective to time key and movement to date for specific customer status changes.
35. Updates account details such as continuous excess days, DPD overdrawn, review due date, and DPD renewal based on data from the DPD_Aqua_SMA table.
36. Updates the running process status for the SMA_MARKING process, marking it as completed or failed based on the execution outcome.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Set ContiExcessDt and DPD_Overdrawn to zero | `ContiExcessDt, DPD_Overdrawn` | For accounts with DPD_Overdrawn less than or equal to 30, the ContiExcessDt and DPD_Overdrawn fields are set to zero. |
| Set ReviewDueDt and DPD_Renewal to zero | `ReviewDueDt, DPD_Renewal` | For accounts with DPD_Overdrawn less than or equal to 30, the ReviewDueDt and DPD_Renewal fields are set to zero. |
| Reset negative DPD values to zero | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | For accounts with negative DPD values, the corresponding fields are set to zero. |
| Initialize #TEMPTABLE with selected fields | `CustomerAcID, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | Populates the temporary table #TEMPTABLE with selected fields from the #DPD table, comparing various overdue and renewal-related fields to… |
| Update DPD_Max to zero for reprocessing | `DPD_Max` | Updates the DPD_Max field in the #DPD table to zero for reprocessing data. |
| Calculate maximum overdue days | `DPD_Max` | Calculates the maximum overdue days (DPD_Max) for each account by comparing various overdue and renewal-related fields. |
| Reset SMA fields in ##AccountCal | `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA` | Resets the SMA_CLASS, SMA_REASON, SMA_DT, and FLGSMA fields in the ##AccountCal table to NULL. |
| Assign SMA class based on overdue days | `SMA_CLASS` | The account's SMA class is set based on the maximum number of overdue days. |
| Assign SMA class based on overdue days | `SMA_CLASS` | The account's SMA class is set based on the maximum number of overdue days. |
| Assign SMA class based on overdue days | `SMA_CLASS` | The account's SMA class is set based on the maximum number of overdue days. |
| Assign SMA class based on overdue days | `SMA_CLASS` | The account's SMA class is set based on the maximum number of overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | The account's SMA reason is set based on the facility type and the reason for the maximum overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | The account's SMA reason is set based on the facility type and the reason for the maximum overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | The account's SMA reason is set based on the facility type and the reason for the maximum overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | The account's SMA reason is set based on the facility type and the reason for the maximum overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | The account's SMA reason is set based on the facility type and the reason for the maximum overdue days. |
| Assign SMA reason based on facility type and overdue days | `SMA_REASON` | The account's SMA reason is set based on the facility type and the reason for the maximum overdue days. |
| Assign SMA date based on overdue days | `SMA_DT` | The account's SMA date is set to the date calculated by subtracting the maximum overdue days from the process date. |
| Reset SMA flags and keys | `SMA flags and keys, FLGSMA, SMA_CLASS_KEY, SMA_DT` | Resets the SMA flags and keys for customer accounts to null. |
| Set SMA flag to 'Y' for eligible accounts | `SMA flag, FLGSMA` | Sets the SMA flag to 'Y' for customer accounts that meet the eligibility criteria. |
| Update UCIF ID and SMA date for eligible accounts | `UCIF ID and SMA date, UCIF_ID, SMA_DT` | Updates the UCIF ID and SMA date for customer accounts that meet the eligibility criteria. |
| Insert SMA class and date into temporary tables | `SMA class and date, CustomerEntityID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt` | Inserts SMA class and date information into temporary tables for further processing. |
| Update SMA class and date from temporary tables | `SMA class and date, SMA_CLASS_KEY, SMA_DT` | Updates the SMA class and date for customer accounts from the temporary tables. |
| Delete existing SMA movement history | `SMA movement history, TIMEKEY` | Deletes existing SMA movement history for the specified time key if it exists. |
| Insert new SMA movement history | `SMA movement history, TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS` | Inserts new SMA movement history into the SMA movement history table. |
| Truncate previous SMA status table | `Previous SMA status table` | Truncates the previous SMA status table. |
| Insert current SMA status into previous SMA status table | `Previous SMA status table, @TIMEKEY, CustomerAcID, SMA_CLASS` | Inserts the current SMA status into the previous SMA status table. |
| Update customer movement description | `Customer movement description, CustMoveDescription` | Updates the customer movement description based on the system asset class alternate key and SMA class key. |
| Update customer movement history | `EffectiveToTimeKey, MovementToDate` | Updates the customer movement history with the effective to time key and movement to date for specific customer status changes. |
| Update account details for SMA Aqua Scheme | `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal` | Updates account details such as continuous excess days, DPD overdrawn, review due date, and DPD renewal based on data from the DPD_Aqua_SMA… |

## Business Rules

### R1 — Set ContiExcessDt and DPD_Overdrawn to zero

**Affected Field:** `ContiExcessDt, DPD_Overdrawn`

**Applies to:**

- Account is under the SMA Aqua Scheme
- Account's DPD_Overdrawn is less than or equal to 30

**Summary:**

- For accounts with DPD_Overdrawn less than or equal to 30, the ContiExcessDt and DPD_Overdrawn fields are set to zero.


### R2 — Set ReviewDueDt and DPD_Renewal to zero

**Affected Field:** `ReviewDueDt, DPD_Renewal`

**Applies to:**

- Account is under the SMA Aqua Scheme
- Account's DPD_Overdrawn is less than or equal to 30

**Summary:**

- For accounts with DPD_Overdrawn less than or equal to 30, the ReviewDueDt and DPD_Renewal fields are set to zero.


### R3 — Reset negative DPD values to zero

**Affected Field:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt`

**Applies to:**

- Account has negative DPD values

**Summary:**

- For accounts with negative DPD values, the corresponding fields are set to zero.


### R4 — Initialize #TEMPTABLE with selected fields

**Affected Field:** `CustomerAcID, DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Populates the temporary table #TEMPTABLE with selected fields from the #DPD table, comparing various overdue and renewal-related fields to their respective reference period fields.


### R5 — Update DPD_Max to zero for reprocessing

**Affected Field:** `DPD_Max`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Updates the DPD_Max field in the #DPD table to zero for reprocessing data.


### R6 — Calculate maximum overdue days

**Affected Field:** `DPD_Max`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Calculates the maximum overdue days (DPD_Max) for each account by comparing various overdue and renewal-related fields.


### R7 — Reset SMA fields in ##AccountCal

**Affected Field:** `SMA_CLASS, SMA_REASON, SMA_DT, FLGSMA`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the SMA_CLASS, SMA_REASON, SMA_DT, and FLGSMA fields in the ##AccountCal table to NULL.


### R8 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA class is set based on the maximum number of overdue days.


### R9 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA class is set based on the maximum number of overdue days.


### R10 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA class is set based on the maximum number of overdue days.


### R11 — Assign SMA class based on overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA class is set based on the maximum number of overdue days.


### R12 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA reason is set based on the facility type and the reason for the maximum overdue days.


### R13 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA reason is set based on the facility type and the reason for the maximum overdue days.


### R14 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA reason is set based on the facility type and the reason for the maximum overdue days.


### R15 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA reason is set based on the facility type and the reason for the maximum overdue days.


### R16 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA reason is set based on the facility type and the reason for the maximum overdue days.


### R17 — Assign SMA reason based on facility type and overdue days

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA reason is set based on the facility type and the reason for the maximum overdue days.


### R18 — Assign SMA date based on overdue days

**Affected Field:** `SMA_DT`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- The account's SMA date is set to the date calculated by subtracting the maximum overdue days from the process date.


### R19 — Reset SMA flags and keys

**Affected Field:** `SMA flags and keys, FLGSMA, SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- Customer account record exists

**Summary:**

- Resets the SMA flags and keys for customer accounts to null.


### R20 — Set SMA flag to 'Y' for eligible accounts

**Affected Field:** `SMA flag, FLGSMA`

**Applies to:**

- Customer account record exists
- Account balance is greater than zero
- Asset class key is 1

**Summary:**

- Sets the SMA flag to 'Y' for customer accounts that meet the eligibility criteria.


### R21 — Update UCIF ID and SMA date for eligible accounts

**Affected Field:** `UCIF ID and SMA date, UCIF_ID, SMA_DT`

**Applies to:**

- Customer account record exists
- UCIF ID and SMA flag are set

**Summary:**

- Updates the UCIF ID and SMA date for customer accounts that meet the eligibility criteria.


### R22 — Insert SMA class and date into temporary tables

**Affected Field:** `SMA class and date, CustomerEntityID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN 1 WHEN SMA_CLASS='SMA_1' THEN 2 WHEN SMA_CLASS='SMA_2' THEN 3 ELSE 0 END) AS MAXSMA_CLASS, MIN(A.SMA_Dt) AS SMA_Dt`

**Applies to:**

- Customer account record exists
- Account balance is greater than zero
- Asset class alternate key is 1

**Summary:**

- Inserts SMA class and date information into temporary tables for further processing.


### R23 — Update SMA class and date from temporary tables

**Affected Field:** `SMA class and date, SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- Customer account record exists
- SMA flag is set

**Summary:**

- Updates the SMA class and date for customer accounts from the temporary tables.


### R24 — Delete existing SMA movement history

**Affected Field:** `SMA movement history, TIMEKEY`

**Applies to:**

- SMA movement history record exists for the specified time key

**Summary:**

- Deletes existing SMA movement history for the specified time key if it exists.


### R25 — Insert new SMA movement history

**Affected Field:** `SMA movement history, TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS`

**Applies to:**

- SMA class has changed

**Summary:**

- Inserts new SMA movement history into the SMA movement history table.


### R26 — Truncate previous SMA status table

**Affected Field:** `Previous SMA status table`

**Applies to:**

- Previous SMA status table exists

**Summary:**

- Truncates the previous SMA status table.


### R27 — Insert current SMA status into previous SMA status table

**Affected Field:** `Previous SMA status table, @TIMEKEY, CustomerAcID, SMA_CLASS`

**Applies to:**

- Current SMA status exists

**Summary:**

- Inserts the current SMA status into the previous SMA status table.


### R28 — Update customer movement description

**Affected Field:** `Customer movement description, CustMoveDescription`

**Applies to:**

- Customer account record exists
- System asset class alternate key or SMA class key is set

**Summary:**

- Updates the customer movement description based on the system asset class alternate key and SMA class key.


### R29 — Update customer movement history

**Affected Field:** `EffectiveToTimeKey, MovementToDate`

**Applies to:**

- AA.EffectiveToTimeKey = 49999
- AA.EffectiveFROMTimeKey < @TIMEKEY
- EXISTS(SELECT 1 FROM #Customer_MOVEMENT_HISTORY AS BB WHERE AA.SourceSystemCustomerID = BB.SourceSystemCustomerID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS)

**Summary:**

- Updates the customer movement history with the effective to time key and movement to date for specific customer status changes.


### R30 — Update account details for SMA Aqua Scheme

**Affected Field:** `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal`

**Applies to:**

- A.AccountEntityID = B.AccountEntityID

**Summary:**

- Updates account details such as continuous excess days, DPD overdrawn, review due date, and DPD renewal based on data from the DPD_Aqua_SMA table.

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

The procedure includes a TRY block to handle any exceptions that may occur during execution. If an error occurs during the execution of the procedure, the running process status is updated to mark the process as failed, and temporary tables are dropped.

## Findings / Needs Review

- Lines 19-19 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 24-24 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 36-41 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 340-346 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 400-453 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 511-550 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 511-559 (ASSIGNMENT/CASE/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 751-759 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 768-772 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
