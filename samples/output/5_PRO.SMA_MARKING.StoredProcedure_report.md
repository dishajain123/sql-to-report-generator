# SMA Marking — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_MARKING` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 17 |
| Tables read | 9 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure marks accounts with a Sub-Standard Asset (SMA) classification based on the maximum overdue days (DPD) and facility type. It also records the reason for the classification and the date when the classification was applied. The SMA_MARKING procedure updates various fields in the ##CUSTOMERCAL and ##AccountCal tables to mark the status of accounts based on their overdue days and asset classification. It also manages the SMA_MOVEMENT_HISTORY and PREVSMASTATUS tables to track changes in SMA class. This procedure updates account movement history and SMA classification details for accounts with a specific asset class, ensuring that overdue days and renewal dates are correctly set based on the provided time key.

## Process Flow

1. Reads account data from the ACCOUNTCAL and CUSTOMERCAL tables.
2. Updates the SMA_CLASS, SMA_REASON, SMA_DT, and FLGSMA fields in the ##AccountCal table based on the maximum DPD and facility type.
3. Inserts data into the #DPD_Aqua_SMA temporary table if certain conditions are met.
4. Updates the DPD fields in the #DPD table if they are negative.
5. Inserts data into the #TEMPTABLE temporary table based on certain conditions.
6. Reads data from the SYSDAYMATRIX, dbo.Automate_Advances, DIMPRODUCT, and AdvAcBasicDetail tables.
7. Updates the DPD fields in the #DPD table based on reference period values.
8. Initializes the ##CUSTOMERCAL table by setting FLGSMA, SMA_CLASS_KEY, and SMA_DT to NULL.
9. Updates the ##CUSTOMERCAL table to set FLGSMA to 'Y' based on a join with the ##AccountCal table.
10. Drops the temporary table #TEMPTABLE_SMACLASS if it exists.
11. Creates the temporary table #TEMPTABLE_SMACLASS by selecting the maximum SMA class and minimum SMA date from the ##AccountCal table, grouped by CustomerEntityID.
12. Updates the ##CUSTOMERCAL table to set SMA_CLASS_KEY and SMA_DT based on the temporary table #TEMPTABLE_SMACLASS.
13. Updates the ##CUSTOMERCAL table to set FLGSMA to 'Y' based on a join with the ##AccountCal table on UCIF_ID.
14. Drops the temporary table #TEMPTABLE_SMACLASSUcif if it exists.
15. Creates the temporary table #TEMPTABLE_SMACLASSUcif by selecting the maximum SMA class and minimum SMA date from the ##AccountCal table, grouped by UCIF_ID.
16. Updates the ##CUSTOMERCAL table to set SMA_CLASS_KEY and SMA_DT based on the temporary table #TEMPTABLE_SMACLASSUcif.
17. Deletes records from the PRO.SMA_MOVEMENT_HISTORY table if they exist for the given TIMEKEY.
18. Drops the temporary table #SMACLASS if it exists.
19. Creates the temporary table #SMACLASS by selecting the SMA class from the ##AccountCal table, joined with the ##CUSTOMERCAL table.
20. Updates the SMA_CLASS in the temporary table #SMACLASS based on the SMA class value.
21. Inserts records into the PRO.SMA_MOVEMENT_HISTORY table from the temporary table #SMACLASS and the PRO.PREVSMASTATUS table.
22. Truncates the PRO.PREVSMASTATUS table.
23. Inserts records into the PRO.PREVSMASTATUS table from the temporary table #SMACLASS.
24. Updates the CustMoveDescription in the ##CUSTOMERCAL table based on the SYSASSETCLASSALT_KEY.
25. Updates the SMA_CLASS in the ##AccountCal table based on the FinalAssetClassAlt_Key.
26. Checks if there is existing data in the temporary account movement history table and drops it if present.
27. Inserts data into the temporary account movement history table from the ##AccountCal table.
28. Inserts data into the PRO.ACCOUNT_MOVEMENT_HISTORY table from the temporary account movement history table.
29. Updates the EffectiveToTimeKey and MovementToDate in the PRO.ACCOUNT_MOVEMENT_HISTORY table based on certain conditions.
30. Checks if there is existing data in the temporary customer movement history table and drops it if present.
31. Inserts data into the temporary customer movement history table from the ##CUSTOMERCAL table.
32. Inserts data into the PRO.CUSTOMER_MOVEMENT_HISTORY table from the temporary customer movement history table.
33. Updates the EffectiveToTimeKey and MovementToDate in the PRO.CUSTOMER_MOVEMENT_HISTORY table based on certain conditions.
34. Updates the SMA_CLASS, ContiExcessDt, DPD_Overdrawn, ReviewDueDt, and DPD_Renewal fields in the ##ACCOUNTCAL table from the #DPD_Aqua_SMA table.
35. Updates the COMPLETED, ERRORDATE, ERRORDESCRIPTION, and COUNT fields in the PRO.ACLRUNNINGPROCESSSTATUS table to reflect the process status.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Assign SMA class based on DPD Max | `SMA_CLASS` | Assigns the account's SMA class based on the maximum DPD value and facility type. |
| Assign SMA reason based on DPD Max | `SMA_REASON` | Assigns the reason for the SMA class based on the maximum DPD value and facility type. |
| Set SMA date based on DPD Max | `SMA_DT` | Sets the date when the SMA class was applied based on the maximum DPD value. |
| Flag SMA processing | `FLGSMA` | Flags the account for SMA processing. |
| Initialize customer SMA fields | `FLGSMA, SMA_CLASS_KEY, SMA_DT` | Sets the SMA-related fields in the ##CUSTOMERCAL table to NULL. |
| Set FLGSMA to 'Y' based on AccountCal | `FLGSMA` | Sets FLGSMA to 'Y' in the ##CUSTOMERCAL table based on a join with the ##AccountCal table. |
| Create temporary table #TEMPTABLE_SMACLASS | `Not specified` | Creates the temporary table #TEMPTABLE_SMACLASS by selecting the maximum SMA class and minimum SMA date from the ##AccountCal table, groupe… |
| Update SMA_CLASS_KEY and SMA_DT from #TEMPTABLE_SMACLASS | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the temporary table #TEMPTABLE_SMACLASS. |
| Set FLGSMA to 'Y' based on UCIF_ID | `FLGSMA` | Sets FLGSMA to 'Y' in the ##CUSTOMERCAL table based on a join with the ##AccountCal table on UCIF_ID. |
| Create temporary table #TEMPTABLE_SMACLASSUcif | `Not specified` | Creates the temporary table #TEMPTABLE_SMACLASSUcif by selecting the maximum SMA class and minimum SMA date from the ##AccountCal table, gr… |
| Update SMA_CLASS_KEY and SMA_DT from #TEMPTABLE_SMACLASSUcif | `SMA_CLASS_KEY, SMA_DT` | Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the temporary table #TEMPTABLE_SMACLASSUcif. |
| Delete SMA_MOVEMENT_HISTORY records for given TIMEKEY | `Not specified` | Deletes records from the PRO.SMA_MOVEMENT_HISTORY table if they exist for the given TIMEKEY. |
| Create temporary table #SMACLASS | `Not specified` | Creates the temporary table #SMACLASS by selecting the SMA class from the ##AccountCal table, joined with the ##CUSTOMERCAL table. |
| Update account movement history | `EffectiveToTimeKey, MovementToDate` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.ACCOUNT_MOVEMENT_HISTORY table if certain conditions are met. |
| Update customer movement history | `EffectiveToTimeKey, MovementToDate` | Updates the EffectiveToTimeKey and MovementToDate in the PRO.CUSTOMER_MOVEMENT_HISTORY table if certain conditions are met. |
| Update SMA class for specific asset class | `SMA_CLASS` | Updates the SMA_CLASS field in the ##AccountCal table to 'LOS' for accounts with a FinalAssetClassAlt_Key of 6 and a NULL SMA_CLASS. |
| Update ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal | `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal` | Updates the ContiExcessDt, DPD_Overdrawn, ReviewDueDt, and DPD_Renewal fields in the ##ACCOUNTCAL table from the #DPD_Aqua_SMA table. |

## Business Rules

### R1 — Assign SMA class based on DPD Max

**Affected Field:** `SMA_CLASS`

**Applies to:**

- The account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Assigns the account's SMA class based on the maximum DPD value and facility type.

### Decision Logic

| Condition | Result |
|---|---|
| DPD_Max BETWEEN 1 AND 30 | SMA_0 |
| DPD_Max BETWEEN 31 AND 60 | SMA_1 |
| DPD_Max BETWEEN 61 AND 90 | SMA_2 |
| DPD_Max > 90 | SMA_2 |


### R2 — Assign SMA reason based on DPD Max

**Affected Field:** `SMA_REASON`

**Applies to:**

- The account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Assigns the reason for the SMA class based on the maximum DPD value and facility type.

### Decision Logic

| Condition | Result |
|---|---|
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_INTSERVICE,0)=ISNULL(DPD_MAX,0) | DEGRADE BY INT NOT SERVICED |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_NOCREDIT,0)=ISNULL(DPD_MAX,0) | DEGRADE BY NO CREDIT |
| FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(DPD_OVERDUE,0)=ISNULL(DPD_MAX,0) | DEGRADE BY OVERDUE |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_OVERDRAWN,0)=ISNULL(DPD_MAX,0) and ISNULL(DPD_OVERDRAWN,0)>30 | DEGRADE BY CONTI EXCESS |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_STOCKSTMT,0)=ISNULL(DPD_MAX,0) | DEGRADE BY STOCK STATEMENT |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_RENEWAL,0)=ISNULL(DPD_MAX,0) | DEGRADE BY REVIEW DUE DATE |
| ELSE | OTHER |


### R3 — Set SMA date based on DPD Max

**Affected Field:** `SMA_DT`

**Applies to:**

- The account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Sets the date when the SMA class was applied based on the maximum DPD value.


### R4 — Flag SMA processing

**Affected Field:** `FLGSMA`

**Applies to:**

- The account is not currently mid-processing
- Account's current asset class is Standard
- Outstanding balance is greater than zero
- Account is not flagged as always-standard

**Summary:**

- Flags the account for SMA processing.


### R5 — Initialize customer SMA fields

**Affected Field:** `FLGSMA, SMA_CLASS_KEY, SMA_DT`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Sets the SMA-related fields in the ##CUSTOMERCAL table to NULL.


### R6 — Set FLGSMA to 'Y' based on AccountCal

**Affected Field:** `FLGSMA`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Sets FLGSMA to 'Y' in the ##CUSTOMERCAL table based on a join with the ##AccountCal table.


### R7 — Create temporary table #TEMPTABLE_SMACLASS

**Affected Field:** Not specified

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Creates the temporary table #TEMPTABLE_SMACLASS by selecting the maximum SMA class and minimum SMA date from the ##AccountCal table, grouped by CustomerEntityID.


### R8 — Update SMA_CLASS_KEY and SMA_DT from #TEMPTABLE_SMACLASS

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the temporary table #TEMPTABLE_SMACLASS.


### R9 — Set FLGSMA to 'Y' based on UCIF_ID

**Affected Field:** `FLGSMA`

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Sets FLGSMA to 'Y' in the ##CUSTOMERCAL table based on a join with the ##AccountCal table on UCIF_ID.


### R10 — Create temporary table #TEMPTABLE_SMACLASSUcif

**Affected Field:** Not specified

**Applies to:**

- B.FLGSMA='Y'

**Summary:**

- Creates the temporary table #TEMPTABLE_SMACLASSUcif by selecting the maximum SMA class and minimum SMA date from the ##AccountCal table, grouped by UCIF_ID.


### R11 — Update SMA_CLASS_KEY and SMA_DT from #TEMPTABLE_SMACLASSUcif

**Affected Field:** `SMA_CLASS_KEY, SMA_DT`

**Applies to:**

- A.FLGSMA='Y'

**Summary:**

- Updates the SMA_CLASS_KEY and SMA_DT in the ##CUSTOMERCAL table based on the temporary table #TEMPTABLE_SMACLASSUcif.


### R12 — Delete SMA_MOVEMENT_HISTORY records for given TIMEKEY

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Deletes records from the SMA_MOVEMENT_HISTORY table if they exist for the given TIMEKEY.


### R13 — Create temporary table #SMACLASS

**Affected Field:** Not specified

**Applies to:**

- B.FLGSMA='Y' AND ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1

**Summary:**

- Creates the temporary table #SMACLASS by selecting the SMA class from the ##AccountCal table, joined with the ##CUSTOMERCAL table.


### R14 — Update account movement history

**Affected Field:** `EffectiveToTimeKey, MovementToDate`

**Applies to:**

- AA.EffectiveToTimeKey = 49999 AND B.CustomerAcID IS NULL

**Summary:**

- Updates the EffectiveToTimeKey and MovementToDate in the ACCOUNT_MOVEMENT_HISTORY table if certain conditions are met.


### R15 — Update customer movement history

**Affected Field:** `EffectiveToTimeKey, MovementToDate`

**Applies to:**

- AA.EffectiveToTimeKey = 49999 AND B.SourceSystemCustomerID IS NULL

**Summary:**

- Updates the EffectiveToTimeKey and MovementToDate in the CUSTOMER_MOVEMENT_HISTORY table if certain conditions are met.


### R16 — Update SMA class for specific asset class

**Affected Field:** `SMA_CLASS`

**Applies to:**

- FinalAssetClassAlt_Key=6 AND SMA_CLASS is NULL

**Summary:**

- Updates the SMA_CLASS field in the ##AccountCal table to 'LOS' for accounts with a FinalAssetClassAlt_Key of 6 and a NULL SMA_CLASS.


### R17 — Update ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal

**Affected Field:** `ContiExcessDt, DPD_Overdrawn, ReviewDueDt, DPD_Renewal`

**Applies to:**

- A.AccountEntityID=B.AccountEntityID

**Summary:**

- Updates the ContiExcessDt, DPD_Overdrawn, ReviewDueDt, and DPD_Renewal fields in the ##ACCOUNTCAL table from the #DPD_Aqua_SMA table.

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

If any DPD field is negative, it is set to zero. If an error occurs, the process updates the PRO.ACLRUNNINGPROCESSSTATUS table to reflect the error and drops the temporary tables.

## Findings / Needs Review

- Affected regions: lines 19-19, 24-24, 36-41, 106-118, 111-118 (+9 more) (14 total) - needs review after a larger output budget or chunked synthesis.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic. Affected regions: lines 19-19, 24-24, 36-41, 106-118, 111-118 (+9 more) (14 total) - needs review after a larger output budget or chunked synthesis.
- The exact business meaning of the commented-out conditions and statements is unclear as they are not executed.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
