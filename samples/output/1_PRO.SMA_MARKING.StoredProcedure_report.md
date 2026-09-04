# SMA Marking — Business Logic Report

**Procedure:** `PRO.SMA_MARKING`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_MARKING` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 6 |
| Tables read | 9 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

**Automated verification:** REVIEW REQUIRED (quality score 15/100) — 1 of 6 rules could not be traced back to source statements; 22.5% of SQL statements were not matched to a rule; 11 contradiction(s) were flagged between source and report. See the companion verification report before relying on this document.

## What This Does

Not explicitly determined from source SQL.

## Process Flow

_Not explicitly determined from source SQL._

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Reset negative DPD to zero | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | Ensures that any negative overdue days are reset to zero for all types of overdue days. |
| Calculate maximum overdue days | `DPD_Max` | Determines the maximum overdue days for each account by comparing different types of overdue days. |
| Assign SMA class based on maximum overdue days | `SMA_CLASS` | Classifies accounts into SMA categories based on the maximum overdue days. |
| Assign SMA reason based on facility type and maximum overdue days | `SMA_REASON` | Determines the reason for SMA classification based on the facility type and the type of overdue days that matches the maximum overdue days. |
| Update SMA class key and SMA date | `SMA_CLASS_KEY` | Updates the SMA class key and SMA date for accounts and customers based on the maximum SMA class. |
| Record account movement history | `Not specified` | Records movement history for accounts if there is a change in SMA status. |

## Business Rules

### R1 — Reset negative DPD to zero

**Affected Field:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt`

**Applies to:**

- Overdue days for any type is negative

**Summary:**

- Ensures that any negative overdue days are reset to zero for all types of overdue days.


### R2 — Calculate maximum overdue days

**Affected Field:** `DPD_Max`

**Applies to:**

- Overdue days for any type are greater than or equal to zero

**Summary:**

- Determines the maximum overdue days for each account by comparing different types of overdue days.
- isnull(A.DPD_StockStmt,0)

### Decision Logic

| Condition | Result |
|---|---|
| (isnull(DPD_IntService,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_IntService,0)>=isnull(DPD_StockStmt,0)) | isnull(DPD_IntService,0) |
| (isnull(DPD_NoCredit,0)>=isnull(DPD_IntService,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_StockStmt,0)) | isnull(DPD_NoCredit,0) |
| (isnull(DPD_Overdrawn,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_IntService,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_StockStmt,0)) | isnull(DPD_Overdrawn,0) |
| (isnull(DPD_Renewal,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_IntService,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_StockStmt,0)) | isnull(DPD_Renewal,0) |
| (isnull(DPD_Overdue,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_Overdue,0)>=isnull(DPD_IntService,0) AND isnull(DPD_Overdue,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_Overdue,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_Overdue,0)>=isnull(DPD_StockStmt,0)) | isnull(DPD_Overdue,0) |
| ELSE | isnull(DPD_StockStmt,0) |


### R3 — Assign SMA class based on maximum overdue days

**Affected Field:** `SMA_CLASS`

**Applies to:**

- Overdue days for any type are greater than or equal to zero

**Summary:**

- Classifies accounts into SMA categories based on the maximum overdue days.
- NULL

### Decision Logic

| Condition | Result |
|---|---|
| DPD_Max BETWEEN 1 AND 30 | 'SMA_0' |
| DPD_Max BETWEEN 31 AND 60 | 'SMA_1' |
| DPD_Max BETWEEN 61 AND 90 | 'SMA_2' |
| DPD_Max > 90 | 'SMA_2' |


### R4 — Assign SMA reason based on facility type and maximum overdue days

**Affected Field:** `SMA_REASON`

**Applies to:**

- Overdue days for any type are greater than or equal to zero

**Summary:**

- Determines the reason for SMA classification based on the facility type and the type of overdue days that matches the maximum overdue days.
- 'OTHER'

### Decision Logic

| Condition | Result |
|---|---|
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_INTSERVICE,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY INT NOT SERVICED' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_NOCREDIT,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY NO CREDIT' |
| FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(DPD_OVERDUE,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY OVERDUE' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_OVERDRAWN,0)=ISNULL(DPD_MAX,0) AND ISNULL(DPD_OVERDRAWN,0)>30 | 'DEGRADE BY CONTI EXCESS' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_STOCKSTMT,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY STOCK STATEMENT' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_RENEWAL,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY REVIEW DUE DATE' |


### R5 — Update SMA class key and SMA date

**Affected Field:** `SMA_CLASS_KEY`

**Applies to:**

- SMA flag is set to 'Y'

**Summary:**

- Updates the SMA class key and SMA date for accounts and customers based on the maximum SMA class.
- SMA_CLASS

### Decision Logic

| Condition | Result |
|---|---|
| SMA_CLASS='SMA_0' | 1 |
| SMA_CLASS='SMA_1' | 2 |
| SMA_CLASS='SMA_2' | 3 |


### R6 — Record account movement history

**Affected Field:** Not specified

**Applies to:**

- SMA class in temporary table is not null and differs from the current SMA class

**Summary:**

- Records movement history for accounts if there is a change in SMA status.

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

- Possible unreviewed decision logic near source line 19-19 (ASSIGNMENT): no synthesized rule's evidence appears to reference "Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1  FROM [dbo].Automate_Advances WHERE EXT_FLG='Y')". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 24-24 (IF): no synthesized rule's evidence appears to reference "IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 36-776 (ASSIGNMENT): no synthesized rule's evidence appears to reference "Update         A SET            A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM           ##ACCOUNTCAL A  INNER JOIN     #DPD_Aqua_SMA B ON             A.AccountEnt...". Needs human review to confirm whether this is business-relevant.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
