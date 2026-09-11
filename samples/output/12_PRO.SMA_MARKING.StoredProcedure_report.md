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

This procedure marks accounts with a Sub-Standard Asset (SMA) classification based on the maximum overdue days (DPD) and facility type. It also records the reason for the classification and the date when the classification was applied. The SMA_MARKING procedure updates various fields in the ##CUSTOMERCAL and ##AccountCal tables to mark the status of accounts based on their overdue days and asset classification. It also manages the SMA_MOVEMENT_HISTORY and PREVSMASTATUS tables to track changes in SMA class. This procedure updates account movement history and SMA classification for accounts with a specific asset class, ensuring that the movement history is accurately recorded and the SMA classification is appropriately assigned based on the overdue days and other conditions.

## Process Flow

1. Reads account and customer data from various tables.
2. Updates the account's SMA classification, reason, date, and SMA flag based on the maximum overdue days and facility type.
3. Inserts or updates temporary tables with relevant account data for further processing.
4. Initializes the SMA_CLASS_KEY, SMA_DT, and FLGSMA fields in the ##CUSTOMERCAL table to NULL.
5. Sets the FLGSMA field in the ##CUSTOMERCAL table to 'Y' if the corresponding account in the ##AccountCal table has FLGSMA set to 'Y'.
6. Creates a temporary table #TEMPTABLE_SMACLASS to store the maximum SMA class and minimum SMA date for each customer entity.
7. Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the data in the #TEMPTABLE_SMACLASS temporary table.
8. Sets the FLGSMA field in the ##CUSTOMERCAL table to 'Y' if the corresponding UCIF_ID in the ##AccountCal table has FLGSMA set to 'Y'.
9. Creates a temporary table #TEMPTABLE_SMACLASSUcif to store the maximum SMA class and minimum SMA date for each UCIF_ID.
10. Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the data in the #TEMPTABLE_SMACLASSUcif temporary table.
11. Deletes existing records in the PRO.SMA_MOVEMENT_HISTORY table for the specified TIMEKEY if they exist.
12. Creates a temporary table #SMACLASS to store the SMA class for each customer account.
13. Updates the SMA_CLASS field in the #SMACLASS temporary table based on the SMA_CLASS_KEY.
14. Inserts records into the PRO.SMA_MOVEMENT_HISTORY table to track changes in SMA class.
15. Truncates the PRO.PREVSMASTATUS table.
16. Inserts records into the PRO.PREVSMASTATUS table to store the previous SMA class for each customer account.
17. Updates the CustMoveDescription field in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY and SMA_CLASS_KEY.
18. Updates the SMA_CLASS field in the ##AccountCal table based on the FinalAssetClassAlt_Key.
19. Checks if there is existing data in the temporary tables and drops them if present.
20. Inserts data into the temporary tables #ACCOUNT_MOVEMENT_HISTORY and #Customer_MOVEMENT_HISTORY from the AccountCal and CUSTOMERCAL tables respectively.
21. Updates the EffectiveToTimeKey and MovementToDate in the PRO.ACCOUNT_MOVEMENT_HISTORY and PRO.CUSTOMER_MOVEMENT_HISTORY tables based on conditions from the temporary tables.
22. Updates the SMA_CLASS in the ##AccountCal table for accounts with a specific asset class.
23. Updates various DPD related fields in the ##ACCOUNTCAL table from the #DPD_Aqua_SMA temporary table.
24. Updates the process status in the PRO.ACLRUNNINGPROCESSSTATUS table to mark the process as completed or with an error if any occurs.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Insert into #ACCOUNT_MOVEMENT_HISTORY | `Not specified` | Inserts data into the temporary table #ACCOUNT_MOVEMENT_HISTORY from the ##AccountCal table for accounts with a specific asset class. |
| Insert into PRO.ACCOUNT_MOVEMENT_HISTORY | `Not specified` | Inserts data into the PRO.ACCOUNT_MOVEMENT_HISTORY table from the temporary table #ACCOUNT_MOVEMENT_HISTORY. |
| Update EffectiveToTimeKey and MovementToDate in PRO.ACCOUNT_MOVEMENT_HISTORY | `Not specified` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.ACCOUNT_MOVEMENT_HISTORY table based on conditions from the temporary table #A… |
| Update EffectiveToTimeKey and MovementToDate in PRO.CUSTOMER_MOVEMENT_HISTORY | `Not specified` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.CUSTOMER_MOVEMENT_HISTORY table based on conditions from the temporary table #… |
| Update SMA_CLASS in ##AccountCal | `SMA_CLASS` | Updates the SMA_CLASS in the ##AccountCal table to 'LOS' for accounts with a specific asset class. |
| Update ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal in ##ACCOUNTCAL | `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal` | Updates the ContiExcessDt, DPD_Overdrawn, ReviewDueDt, and DPD_Renewal fields in the ##ACCOUNTCAL table from the #DPD_Aqua_SMA temporary ta… |
| Assign SMA class based on DPD max | `SMA_CLASS` | Assigns the account's SMA classification based on the maximum number of overdue days (DPD) and facility type. |
| Set SMA reason based on DPD max | `SMA_REASON` | Sets the reason for the account's SMA classification based on the maximum number of overdue days (DPD) and facility type. |
| Set SMA date based on DPD max | `SMA_DT` | Sets the date when the account's SMA classification was applied based on the maximum number of overdue days (DPD). |
| Set SMA flag to 'Y' | `FLGSMA` | Sets the SMA flag to 'Y' for accounts that meet the SMA classification criteria. |
| Reset SMA marking flags | `SMA_CLASS_KEY, SMA_DT, FLGSMA` | Resets the SMA_CLASS_KEY, SMA_DT, and FLGSMA fields in the ##CUSTOMERCAL table to NULL. |
| Set FLGSMA to 'Y' based on AccountCal | `FLGSMA` | Sets the FLGSMA field in the ##CUSTOMERCAL table to 'Y' if the corresponding account in the ##AccountCal table has FLGSMA set to 'Y'. |
| Create #TEMPTABLE_SMACLASS | `Not specified` | Creates a temporary table #TEMPTABLE_SMACLASS to store the maximum SMA class and minimum SMA date for each customer entity. |
| Update SMA_CLASS_KEY and SMA_DT from #TEMPTABLE_SMACLASS | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the data in the #TEMPTABLE_SMACLASS temporary table. |
| Set FLGSMA to 'Y' based on UCIF_ID | `FLGSMA` | Sets the FLGSMA field in the ##CUSTOMERCAL table to 'Y' if the corresponding UCIF_ID in the ##AccountCal table has FLGSMA set to 'Y'. |
| Create #TEMPTABLE_SMACLASSUcif | `Not specified` | Creates a temporary table #TEMPTABLE_SMACLASSUcif to store the maximum SMA class and minimum SMA date for each UCIF_ID. |
| Update SMA_CLASS_KEY and SMA_DT from #TEMPTABLE_SMACLASSUcif | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the data in the #TEMPTABLE_SMACLASSUcif temporary table. |
| Delete existing SMA movement history | `Not specified` | Deletes existing records in the PRO.SMA_MOVEMENT_HISTORY table for the specified TIMEKEY if they exist. |
| Create #SMACLASS temporary table | `Not specified` | Creates a temporary table #SMACLASS to store the SMA class for each customer account. |
| Insert SMA movement history | `Not specified` | Inserts records into the PRO.SMA_MOVEMENT_HISTORY table to track changes in SMA class. |

## Business Rules

### R1 — Insert into #ACCOUNT_MOVEMENT_HISTORY

**Affected Field:** Not specified

**Applies to:**

- Accounts with FinalAssetClassAlt_Key=6 and SMA_CLASS is NULL

**Summary:**

- Inserts data into the temporary table #ACCOUNT_MOVEMENT_HISTORY from the ##AccountCal table for accounts with a specific asset class.


### R2 — Insert into PRO.ACCOUNT_MOVEMENT_HISTORY

**Affected Field:** Not specified

**Applies to:**

- Data exists in the temporary table #ACCOUNT_MOVEMENT_HISTORY

**Summary:**

- Inserts data into the ACCOUNT_MOVEMENT_HISTORY table from the temporary table #ACCOUNT_MOVEMENT_HISTORY.


### R3 — Update EffectiveToTimeKey and MovementToDate in PRO.ACCOUNT_MOVEMENT_HISTORY

**Affected Field:** Not specified

**Applies to:**

- AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL

**Summary:**

- Updates the EffectiveToTimeKey and MovementToDate in the ACCOUNT_MOVEMENT_HISTORY table based on conditions from the temporary table #ACCOUNT_MOVEMENT_HISTORY.


### R4 — Update EffectiveToTimeKey and MovementToDate in PRO.CUSTOMER_MOVEMENT_HISTORY

**Affected Field:** Not specified

**Applies to:**

- AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL

**Summary:**

- Updates the EffectiveToTimeKey and MovementToDate in the CUSTOMER_MOVEMENT_HISTORY table based on conditions from the temporary table #Customer_MOVEMENT_HISTORY.


### R5 — Update SMA_CLASS in ##AccountCal

**Affected Field:** `SMA_CLASS`

**Applies to:**

- Accounts with FinalAssetClassAlt_Key=6 and SMA_CLASS is NULL

**Summary:**

- Updates the SMA_CLASS in the ##AccountCal table to 'LOS' for accounts with a specific asset class.


### R6 — Update ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal in ##ACCOUNTCAL

**Affected Field:** `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal`

**Applies to:**

- Matching AccountEntityID in ##ACCOUNTCAL and #DPD_Aqua_SMA

**Summary:**

- Updates the ContiExcessDt, DPD_Overdrawn, ReviewDueDt, and DPD_Renewal fields in the ##ACCOUNTCAL table from the #DPD_Aqua_SMA temporary table.


### R7 — Assign SMA class based on DPD max

**Affected Field:** `SMA_CLASS`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Assigns the account's SMA classification based on the maximum number of overdue days (DPD) and facility type.

### Decision Logic

| Condition | Result |
|---|---|
| DPD_Max BETWEEN 1 AND 30 | SMA_0 |
| DPD_Max BETWEEN 31 AND 60 | SMA_1 |
| DPD_Max BETWEEN 61 AND 90 | SMA_2 |
| DPD_Max > 90 | SMA_2 |


### R8 — Set SMA reason based on DPD max

**Affected Field:** `SMA_REASON`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Sets the reason for the account's SMA classification based on the maximum number of overdue days (DPD) and facility type.

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


### R9 — Set SMA date based on DPD max

**Affected Field:** `SMA_DT`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Sets the date when the account's SMA classification was applied based on the maximum number of overdue days (DPD).


### R10 — Set SMA flag to 'Y'

**Affected Field:** `FLGSMA`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Sets the SMA flag to 'Y' for accounts that meet the SMA classification criteria.


### R11 — Reset SMA marking flags

**Affected Field:** `SMA_CLASS_KEY, SMA_DT, FLGSMA`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Resets the SMA_CLASS_KEY, SMA_DT, and FLGSMA fields in the ##CUSTOMERCAL table to NULL.


### R12 — Set FLGSMA to 'Y' based on AccountCal

**Affected Field:** `FLGSMA`

**Applies to:**

- The corresponding account in the ##AccountCal table has FLGSMA set to 'Y'

**Summary:**

- Sets the FLGSMA field in the ##CUSTOMERCAL table to 'Y' if the corresponding account in the ##AccountCal table has FLGSMA set to 'Y'.


### R13 — Create #TEMPTABLE_SMACLASS

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Creates a temporary table #TEMPTABLE_SMACLASS to store the maximum SMA class and minimum SMA date for each customer entity.


### R14 — Update SMA_CLASS_KEY and SMA_DT from #TEMPTABLE_SMACLASS

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- The ##CUSTOMERCAL table has FLGSMA set to 'Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the data in the #TEMPTABLE_SMACLASS temporary table.


### R15 — Set FLGSMA to 'Y' based on UCIF_ID

**Affected Field:** `FLGSMA`

**Applies to:**

- The corresponding UCIF_ID in the ##AccountCal table has FLGSMA set to 'Y'

**Summary:**

- Sets the FLGSMA field in the ##CUSTOMERCAL table to 'Y' if the corresponding UCIF_ID in the ##AccountCal table has FLGSMA set to 'Y'.


### R16 — Create #TEMPTABLE_SMACLASSUcif

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Creates a temporary table #TEMPTABLE_SMACLASSUcif to store the maximum SMA class and minimum SMA date for each UCIF_ID.


### R17 — Update SMA_CLASS_KEY and SMA_DT from #TEMPTABLE_SMACLASSUcif

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- The ##CUSTOMERCAL table has FLGSMA set to 'Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the data in the #TEMPTABLE_SMACLASSUcif temporary table.


### R18 — Delete existing SMA movement history

**Affected Field:** Not specified

**Applies to:**

- There are existing records in the PRO.SMA_MOVEMENT_HISTORY table for the specified TIMEKEY

**Summary:**

- Deletes existing records in the SMA_MOVEMENT_HISTORY table for the specified TIMEKEY if they exist.


### R19 — Create #SMACLASS temporary table

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Creates a temporary table #SMACLASS to store the SMA class for each customer account.


### R20 — Insert SMA movement history

**Affected Field:** Not specified

**Applies to:**

- There are changes in SMA class to track

**Summary:**

- Inserts records into the SMA_MOVEMENT_HISTORY table to track changes in SMA class.

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

No explicit exception handling is defined in the provided extraction. If an error occurs, the process status in the PRO.ACLRUNNINGPROCESSSTATUS table is updated to mark the SMA_MARKING process as failed, and the temporary tables are dropped.

## Findings / Needs Review

- Affected regions: lines 19-19, 24-24, 36-41, 106-118, 111-118 (+4 more) (9 total) - needs review after a larger output budget or chunked synthesis.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic. Affected regions: lines 19-19, 24-24, 36-41, 106-118, 111-118 (+4 more) (9 total) - needs review after a larger output budget or chunked synthesis.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
