# SMA Marking — Business Logic Report

**Procedure:** `PRO.SMA_MARKING`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Procedure | `PRO.SMA_MARKING` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 7 |
| Tables read | 9 |
| Tables written | 5 |
| Produces audit trail | Yes — records audit events |

## What This Does

The procedure SMA_MARKING processes account data to determine the SMA (Serious Management Action) classification and reason for accounts based on their overdue days and facility type. It also updates movement history records and resets certain fields for reprocessing.

## Process Flow

1. Drops temporary tables if they exist.
2. Updates and resets specific fields in temporary tables to ensure non-negative values.
3. Calculates the maximum overdue days (DPD) for each account and assigns SMA class and reason based on the DPD value.
4. Updates the SMA class key and date for customer records.
5. Deletes existing SMA movement history for the given time key if it exists.
6. Inserts new SMA movement history records based on the updated SMA class.
7. Truncates the previous SMA status table.
8. Inserts new records into the previous SMA status table.
9. Checks if account movement history exists for the given time key and decides whether to insert new records or not.
10. Checks if customer movement history exists for the given time key and decides whether to insert new records or not.
11. Updates the running process status for SMA_MARKING.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Calculate maximum DPD | `DPD_Max` | Determines the maximum overdue days (DPD) for each account based on various DPD fields. |
| Assign SMA class based on DPD_Max | `SMA_CLASS` | Assigns the SMA class based on the maximum overdue days (DPD_Max). |
| Assign SMA reason based on facility type and DPD_Max | `SMA_REASON` | Assigns the SMA reason based on the facility type and the maximum overdue days (DPD_Max). |
| Assign SMA class key based on SMA_CLASS | `SMA_CLASS_KEY` | Converts the SMA_CLASS string to a numeric key. |
| Update SMA_CLASS in #SMACLASS | `SMA_CLASS` | Updates the SMA_CLASS field in the #SMACLASS temporary table to a numeric key. |
| Delete SMA movement history for the given time key | `Not specified` | If SMA movement history exists for the given time key, it is deleted to ensure the history is up-to-date. |
| Update SMA_CLASS in ##AccountCal | `SMA_CLASS` | Updates the SMA_CLASS field in the ##AccountCal table based on the SMA_CLASS_KEY. |

## Business Rules

### R1 — Calculate maximum DPD

**Affected Field:** `DPD_Max`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Determines the maximum overdue days (DPD) for each account based on various DPD fields.

### Decision Logic

| Condition | Result |
|---|---|
| (isnull(DPD_IntService,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_IntService,0)>=isnull(DPD_StockStmt,0) | isnull(DPD_IntService,0) |
| (isnull(DPD_NoCredit,0)>=isnull(DPD_IntService,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_StockStmt,0) | isnull(DPD_NoCredit,0) |
| (isnull(DPD_Overdrawn,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_IntService,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_StockStmt,0) | isnull(DPD_Overdrawn,0) |
| (isnull(DPD_Renewal,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_IntService,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_Overdrawn,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_Overdue,0) AND isnull(DPD_Renewal,0)>=isnull(DPD_StockStmt,0) | isnull(DPD_Renewal,0) |
| ELSE | isnull(DPD_StockStmt,0) |


### R2 — Assign SMA class based on DPD_Max

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns the SMA class based on the maximum overdue days (DPD_Max).

### Decision Logic

| Condition | Result |
|---|---|
| DPD_Max BETWEEN 1 AND 30 | 'SMA_0' |
| DPD_Max BETWEEN 31 AND 60 | 'SMA_1' |
| DPD_Max BETWEEN 61 AND 90 | 'SMA_2' |
| DPD_Max > 90 | 'SMA_2' |
| ELSE | NULL |


### R3 — Assign SMA reason based on facility type and DPD_Max

**Affected Field:** `SMA_REASON`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Assigns the SMA reason based on the facility type and the maximum overdue days (DPD_Max).

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


### R4 — Assign SMA class key based on SMA_CLASS

**Affected Field:** `SMA_CLASS_KEY`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Converts the SMA_CLASS string to a numeric key.

### Decision Logic

| Condition | Result |
|---|---|
| SMA_CLASS='SMA_0' | 1 |
| SMA_CLASS='SMA_1' | 2 |
| SMA_CLASS='SMA_2' | 3 |
| ELSE | SMA_CLASS |


### R5 — Update SMA_CLASS in #SMACLASS

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Updates the SMA_CLASS field in the #SMACLASS temporary table to a numeric key.

### Decision Logic

| Condition | Result |
|---|---|
| SMA_CLASS='SMA_0' | 1 |
| SMA_CLASS='SMA_1' | 2 |
| SMA_CLASS='SMA_2' | 3 |
| ELSE | SMA_CLASS |


### R6 — Delete SMA movement history for the given time key

**Affected Field:** Not specified

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- If SMA movement history exists for the given time key, it is deleted to ensure the history is up-to-date.


### R7 — Update SMA_CLASS in ##AccountCal

**Affected Field:** `SMA_CLASS`

**Applies to:** all rows (no additional conditions found in the source)

**Summary:**

- Updates the SMA_CLASS field in the ##AccountCal table based on the SMA_CLASS_KEY.

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
- Possible unreviewed decision logic near source line 36-41 (ASSIGNMENT): no synthesized rule's evidence appears to reference "Update         A SET            A.ContiExcessDt=NULL,A.DPD_Overdrawn=0 FROM           ##ACCOUNTCAL A  INNER JOIN     #DPD_Aqua_SMA B ON             A.AccountEnt...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 106-118 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0    UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0    UPDATE #DPD SET DPD_Overdr...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 111-118 (IF): no synthesized rule's evidence appears to reference "UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0            ----/* CALCULATE MAX DPD */        IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 316-322 (IF): no synthesized rule's evidence appears to reference "UPDATE A SET A.FLGSMA='Y'   FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID   WHERE B.FLGSMA='Y'         IF OBJECT_ID('...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 334-336 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt   FROM ##CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 340-346 (IF): no synthesized rule's evidence appears to reference "UPDATE A SET A.FLGSMA='Y'   FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.UCIF_ID =B.UCIF_ID   WHERE B.FLGSMA='Y'         IF OBJECT_ID('TEMPDB..#TEMPTABLE...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 400-408 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1      UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_K...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 511-550 (INSERT): no synthesized rule's evidence appears to reference "INSERT  INTO  PRO.ACCOUNT_MOVEMENT_HISTORY        (        UCIF_ID,        RefCustomerID,        SourceSystemCustomerID,        CustomerAcID,        FinalAssetC...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 511-559 (ASSIGNMENT/CASE/WHEN): no synthesized rule's evidence appears to reference "INSERT  INTO  PRO.ACCOUNT_MOVEMENT_HISTORY        (        UCIF_ID,        RefCustomerID,        SourceSystemCustomerID,        CustomerAcID,        FinalAssetC...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 562-585 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE AA    SET       EffectiveToTimeKey = @vEffectiveto       ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 650-691 (INSERT): no synthesized rule's evidence appears to reference "INSERT  INTO  PRO.CUSTOMER_MOVEMENT_HISTORY        (        UCIF_ID,        RefCustomerID,        SourceSystemCustomerID,        CustomerName,        SysAssetCl...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 650-700 (ASSIGNMENT/CASE/WHEN): no synthesized rule's evidence appears to reference "INSERT  INTO  PRO.CUSTOMER_MOVEMENT_HISTORY        (        UCIF_ID,        RefCustomerID,        SourceSystemCustomerID,        CustomerName,        SysAssetCl...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 703-728 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE AA   SET     EffectiveToTimeKey = @vEffectiveto   ,MovementToDate=DATEADD(DD,-1,@ProcessDate) -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 751-759 (ASSIGNMENT/UPDATE): no synthesized rule's evidence appears to reference "UPDATE PRO.ACLRUNNINGPROCESSSTATUS    SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1   WHERE RUNNINGPROCESSNAME='SMA_MARKING'...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 768-772 (ASSIGNMENT/UPDATE): no synthesized rule's evidence appears to reference "UPDATE PRO.ACLRUNNINGPROCESSSTATUS    SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1   WHERE RUNNINGPROCESSNAME=...". Needs human review to confirm whether this is business-relevant.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
