# SMA Marking — Business Logic Report

**Procedure:** `PRO.SMA_MARKING`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_MARKING` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 5 |
| Tables read | 9 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

The procedure SMA_MARKING processes account data to determine the Special Mention Account (SMA) classification and reason for a given time key. It updates various account attributes, calculates the maximum days past due (DPD), assigns SMA classes and reasons, and manages movement history records.

## Process Flow

1. Drops temporary tables if they exist.
2. Updates account data for SMA Aqua Scheme.
3. Calculates and sets the maximum DPD for each account.
4. Assigns SMA class and reason based on DPD and facility type.
5. Updates customer and account movement history records.
6. Updates SMA class and SMA reason in the account record.
7. Updates SMA class key and SMA date in the customer record.
8. Updates SMA class key and SMA date in the UCIF record.
9. Inserts or updates SMA movement history records.
10. Inserts or updates account movement history records.
11. Inserts or updates customer movement history records.
12. Updates the running process status for SMA_MARKING.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Reset negative DPD values to zero | `Not specified` | If any DPD value is negative, it is reset to zero. |
| Calculate maximum DPD | `DPD_Max` | Determines the maximum DPD for each account based on various DPD values. |
| Assign SMA class based on DPD | `SMA_CLASS` | Assigns the SMA class based on the maximum DPD value. |
| Assign SMA reason based on DPD and facility type | `SMA_REASON` | Assigns the SMA reason based on the DPD value and facility type. |
| Assign SMA class key from temporary table | `SMA_CLASS_KEY` | Assigns the SMA class key from the temporary table #TEMPTABLE_SMACLASS. |

## Business Rules

### R1 — Reset negative DPD values to zero

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- If any DPD value is negative, it is reset to zero.

### Decision Logic

| Condition | Result |
|---|---|
| isnull(DPD_IntService, 0) < 0 | 0 |
| isnull(DPD_NoCredit, 0) < 0 | 0 |
| isnull(DPD_Overdrawn, 0) < 0 | 0 |
| isnull(DPD_Overdue, 0) < 0 | 0 |
| isnull(DPD_Renewal, 0) < 0 | 0 |
| isnull(DPD_StockStmt, 0) < 0 | 0 |


### R2 — Calculate maximum DPD

**Affected Field:** `DPD_Max`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Determines the maximum DPD for each account based on various DPD values.

### Decision Logic

| Condition | Result |
|---|---|
| (isnull(DPD_IntService,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_IntService,0)>=isnull(DPD_StockStmt,0) | isnull(DPD_IntService,0) |
| (isnull(DPD_NoCredit,0)>=isnull(DPD_IntService,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_StockStmt,0) | isnull(DPD_NoCredit,0) |
| (isnull(DPD_Overdrawn,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_IntService,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_StockStmt,0) | isnull(DPD_Overdrawn,0) |
| (isnull(DPD_Renewal,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_IntService,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_StockStmt,0) | isnull(DPD_Renewal,0) |
| ELSE | isnull(DPD_StockStmt,0) |


### R3 — Assign SMA class based on DPD

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns the SMA class based on the maximum DPD value.

### Decision Logic

| Condition | Result |
|---|---|
| DPD_Max BETWEEN 1 AND 30 | 'SMA_0' |
| DPD_Max BETWEEN 31 AND 60 | 'SMA_1' |
| DPD_Max BETWEEN 61 AND 90 | 'SMA_2' |
| DPD_Max > 90 | 'SMA_2' |
| ELSE | NULL |


### R4 — Assign SMA reason based on DPD and facility type

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns the SMA reason based on the DPD value and facility type.

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


### R5 — Assign SMA class key from temporary table

**Affected Field:** `SMA_CLASS_KEY`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns the SMA class key from the temporary table #TEMPTABLE_SMACLASS.

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

No explicit failure-path behavior identified.

## Findings / Needs Review

- Affected regions: lines 19-19, 24-24, 36-41, 111-118, 340-346 (+12 more) (17 total) - needs review after a larger output budget or chunked synthesis.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic. Affected regions: lines 19-19, 24-24, 36-41, 111-118, 340-346 (+12 more) (17 total) - needs review after a larger output budget or chunked synthesis.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
