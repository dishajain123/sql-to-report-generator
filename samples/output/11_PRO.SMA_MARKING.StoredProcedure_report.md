# SMA Marking — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_MARKING` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 15 |
| Tables read | 9 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure marks accounts with a Sub-Standard Asset (SMA) classification based on the maximum overdue days (DPD) and facility type. It also records the reason for the classification and the date when the classification was applied. The procedure SMA_MARKING updates various fields in the ##CUSTOMERCAL and ##AccountCal tables to mark the status of customer accounts based on their asset classification and overdue days. It also manages the SMA_MOVEMENT_HISTORY and PREVSMASTATUS tables to track changes in asset classification over time. This procedure updates account movement history and SMA classification details for accounts with a specific asset class, ensuring that the movement history is accurately recorded and the SMA classification is appropriately assigned based on the overdue days and other conditions.

## Process Flow

1. Reads account and customer data from various tables.
2. Updates the SMA classification, reason, date, and flag for SMA in the ##AccountCal table based on the maximum overdue days and facility type.
3. Inserts or updates data in temporary tables for further processing.
4. Initializes the ##CUSTOMERCAL table by setting FLGSMA, SMA_CLASS_KEY, and SMA_DT to NULL.
5. Updates the ##CUSTOMERCAL table to set FLGSMA to 'Y' for accounts that meet certain conditions.
6. Creates temporary tables #TEMPTABLE_SMACLASS and #TEMPTABLE_SMACLASSUcif to store aggregated SMA class information.
7. Updates the ##CUSTOMERCAL table to set SMA_CLASS_KEY and SMA_DT based on the information in the temporary tables.
8. Checks if there is an existing SMA_MOVEMENT_HISTORY record for the given TIMEKEY and deletes it if present.
9. Creates a temporary table #SMACLASS to store SMA class information for accounts that meet certain conditions.
10. Updates the SMA_CLASS in the #SMACLASS table based on the SMA_CLASS value.
11. Inserts a new record into the PRO.SMA_MOVEMENT_HISTORY table with the current SMA_CLASS and previous SMA_CLASS for accounts that have changed.
12. Truncates the PRO.PREVSMASTATUS table.
13. Inserts a new record into the PRO.PREVSMASTATUS table with the current SMA_CLASS for accounts that have changed.
14. Updates the CustMoveDescription in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY and SMA_CLASS_KEY.
15. Updates the SMA_CLASS in the ##AccountCal table based on the FinalAssetClassAlt_Key for accounts where SMA_CLASS is NULL.
16. Checks if there is existing data in the temporary account movement history table and drops it if present.
17. Inserts data into the temporary account movement history table from the ##AccountCal table.
18. Inserts data into the PRO.ACCOUNT_MOVEMENT_HISTORY table from the temporary account movement history table.
19. Updates the EffectiveToTimeKey and MovementToDate in the PRO.ACCOUNT_MOVEMENT_HISTORY table based on certain conditions.
20. Checks if there is existing data in the temporary customer movement history table and drops it if present.
21. Inserts data into the temporary customer movement history table from the ##CUSTOMERCAL table.
22. Inserts data into the PRO.CUSTOMER_MOVEMENT_HISTORY table from the temporary customer movement history table.
23. Updates the EffectiveToTimeKey and MovementToDate in the PRO.CUSTOMER_MOVEMENT_HISTORY table based on certain conditions.
24. Updates the SMA_CLASS, ContiExcessDt, DPD_Overdrawn, ReviewDueDt, and DPD_Renewal fields in the ##ACCOUNTCAL table from the #DPD_Aqua_SMA table.
25. Updates the COMPLETED, ERRORDATE, ERRORDESCRIPTION, and COUNT fields in the PRO.ACLRUNNINGPROCESSSTATUS table to reflect the process status.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Update account movement history | `Not specified` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.ACCOUNT_MOVEMENT_HISTORY table based on certain conditions. |
| Update customer movement history | `Not specified` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.CUSTOMER_MOVEMENT_HISTORY table based on certain conditions. |
| Assign SMA class based on DPD Max | `SMA_CLASS` | Assigns the SMA class to an account based on the maximum overdue days (DPD) and facility type. The SMA class is determined by the range of… |
| Set SMA reason based on DPD Max | `SMA_REASON` | Sets the reason for the SMA class based on the maximum overdue days (DPD) and facility type. The reason is determined by which DPD componen… |
| Set SMA date based on DPD Max | `SMA_DT` | Sets the date when the SMA classification was applied based on the maximum overdue days (DPD). |
| Set SMA flag to 'Y' | `FLGSMA` | Sets the SMA flag to 'Y' for accounts that meet the SMA classification criteria. |
| Initialize customer flags | `FLGSMA, SMA_CLASS_KEY, SMA_DT` | Sets the FLGSMA, SMA_CLASS_KEY, and SMA_DT fields to NULL in the ##CUSTOMERCAL table. |
| Set FLGSMA to 'Y' | `FLGSMA` | Sets the FLGSMA field to 'Y' in the ##CUSTOMERCAL table for accounts that meet certain conditions. |
| Update SMA_CLASS_KEY and SMA_DT from temporary tables | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the information in the temporary tables. |
| Delete existing SMA_MOVEMENT_HISTORY record | `Not specified` | Deletes the existing SMA_MOVEMENT_HISTORY record for the given TIMEKEY if it exists. |
| Insert new SMA_MOVEMENT_HISTORY record | `TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS` | Inserts a new record into the PRO.SMA_MOVEMENT_HISTORY table with the current SMA_CLASS and previous SMA_CLASS for accounts that have chang… |
| Truncate PREVSMASTATUS table | `Not specified` | Truncates the PRO.PREVSMASTATUS table. |
| Update CustMoveDescription based on SYSASSETCLASSALT_KEY | `CustMoveDescription` | Updates the CustMoveDescription in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY. |
| Update SMA_CLASS based on FinalAssetClassAlt_Key | `SMA_CLASS` | Updates the SMA_CLASS in the ##AccountCal table based on the FinalAssetClassAlt_Key for accounts where SMA_CLASS is NULL. |
| Update process status | `Not specified` | Updates the COMPLETED, ERRORDATE, ERRORDESCRIPTION, and COUNT fields in the PRO.ACLRUNNINGPROCESSSTATUS table to reflect the process status. |

## Business Rules

### R1 — Update account movement history

**Affected Field:** Not specified

**Applies to:**

- The EffectiveToTimeKey is 49999 and the CustomerAcID is NULL.

**Summary:**

- Updates the EffectiveToTimeKey and MovementToDate in the ACCOUNT_MOVEMENT_HISTORY table based on certain conditions.


### R2 — Update customer movement history

**Affected Field:** Not specified

**Applies to:**

- The EffectiveToTimeKey is 49999 and the SourceSystemCustomerID is NULL.

**Summary:**

- Updates the EffectiveToTimeKey and MovementToDate in the CUSTOMER_MOVEMENT_HISTORY table based on certain conditions.


### R3 — Assign SMA class based on DPD Max

**Affected Field:** `SMA_CLASS`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- DPD Max is greater than or equal to 0

**Summary:**

- Assigns the SMA class to an account based on the maximum overdue days (DPD) and facility type. The SMA class is determined by the range of DPD Max.

### Decision Logic

| Condition | Result |
|---|---|
| DPD_Max BETWEEN 1 AND 30 | SMA_0 |
| DPD_Max BETWEEN 31 AND 60 | SMA_1 |
| DPD_Max BETWEEN 61 AND 90 | SMA_2 |
| DPD_Max > 90 | SMA_2 |


### R4 — Set SMA reason based on DPD Max

**Affected Field:** `SMA_REASON`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- DPD Max is greater than or equal to 0

**Summary:**

- Sets the reason for the SMA class based on the maximum overdue days (DPD) and facility type. The reason is determined by which DPD component equals DPD Max.

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


### R5 — Set SMA date based on DPD Max

**Affected Field:** `SMA_DT`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- DPD Max is greater than or equal to 0

**Summary:**

- Sets the date when the SMA classification was applied based on the maximum overdue days (DPD).

### Decision Logic

| Condition | Result |
|---|---|
| DPD_Max BETWEEN 1 AND 30 | DATEADD(DAY, -DPD_MAX+1, @ProcessDate) |
| DPD_Max BETWEEN 31 AND 60 | DATEADD(DAY, -DPD_MAX+1, @ProcessDate) |
| DPD_Max BETWEEN 61 AND 90 | DATEADD(DAY, -DPD_MAX+1, @ProcessDate) |
| DPD_Max > 90 | DATEADD(DAY, -DPD_MAX+1, @ProcessDate) |


### R6 — Set SMA flag to 'Y'

**Affected Field:** `FLGSMA`

**Applies to:**

- Account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard
- DPD Max is greater than or equal to 0

**Summary:**

- Sets the SMA flag to 'Y' for accounts that meet the SMA classification criteria.


### R7 — Initialize customer flags

**Affected Field:** `FLGSMA, SMA_CLASS_KEY, SMA_DT`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Sets the FLGSMA, SMA_CLASS_KEY, and SMA_DT fields to NULL in the ##CUSTOMERCAL table.


### R8 — Set FLGSMA to 'Y'

**Affected Field:** `FLGSMA`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Sets the FLGSMA field to 'Y' in the ##CUSTOMERCAL table for accounts that meet certain conditions.


### R9 — Update SMA_CLASS_KEY and SMA_DT from temporary tables

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT fields in the ##CUSTOMERCAL table based on the information in the temporary tables.


### R10 — Delete existing SMA_MOVEMENT_HISTORY record

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Deletes the existing SMA_MOVEMENT_HISTORY record for the given TIMEKEY if it exists.


### R11 — Insert new SMA_MOVEMENT_HISTORY record

**Affected Field:** `TIMEKEY, CustomerAcID, PREVSTATUS, CURRENTSTATUS`

**Applies to:**

- B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'')

**Summary:**

- Inserts a new record into the SMA_MOVEMENT_HISTORY table with the current SMA_CLASS and previous SMA_CLASS for accounts that have changed.


### R12 — Truncate PREVSMASTATUS table

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Truncates the PREVSMASTATUS table.


### R13 — Update CustMoveDescription based on SYSASSETCLASSALT_KEY

**Affected Field:** `CustMoveDescription`

**Applies to:**

- SYSASSETCLASSALT_KEY=1

**Summary:**

- Updates the CustMoveDescription in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY.


### R14 — Update SMA_CLASS based on FinalAssetClassAlt_Key

**Affected Field:** `SMA_CLASS`

**Applies to:**

- FinalAssetClassAlt_Key=1 AND SMA_CLASS is NULL

**Summary:**

- Updates the SMA_CLASS in the ##AccountCal table based on the FinalAssetClassAlt_Key for accounts where SMA_CLASS is NULL.


### R15 — Update process status

**Affected Field:** Not specified

**Applies to:**

- The RUNNINGPROCESSNAME is 'SMA_MARKING'.

**Summary:**

- Updates the COMPLETED, ERRORDATE, ERRORDESCRIPTION, and COUNT fields in the ACLRUNNINGPROCESSSTATUS table to reflect the process status.

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

No explicit exception handling is defined in the provided extraction. If an error occurs, the temporary tables are dropped, and the PRO.ACLRUNNINGPROCESSSTATUS table is updated to reflect the error.

## Findings / Needs Review

- Lines 19-19 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 24-24 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 36-41 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 106-118 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 111-118 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 401-453 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 511-550 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 511-550 (CASE/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 562-585 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 650-691 (INSERT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 650-691 (CASE/WHEN) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 703-728 (ASSIGNMENT) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 751-759 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 768-772 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
