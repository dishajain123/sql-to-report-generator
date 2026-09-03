# Update Assetclass — Business Logic Report

**Procedure:** `PRO.Update_AssetClass`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Purpose | This procedure updates the asset classification for customer accounts based on the overdue days and other conditions, ensuring compliance with regulatory requirements. |
| Business rules | 18 |
| Tables read | 4 |
| Tables written | 1 |
| Produces audit trail | No |

## Review Required

The reconciliation stage detected source/report inconsistencies. Business Rules, Calculations, and Data Touched are provisional and must not be treated as confirmed until the discrepancies are resolved.

## What This Does

This procedure updates the asset classification for customer accounts based on the overdue days and other conditions, ensuring compliance with regulatory requirements.

## Process Flow

1. Drop the temporary table #CTE_CustomerWiseBalance if it exists.
2. Create a temporary table #CTE_CustomerWiseBalance to store customer balances.
3. Initialize overdue days and process date variables from the refperiod table.
4. Reset the DbtDt, LossDt, and DegDate fields for eligible customer accounts.
5. Calculate and update the SysAssetClassAlt_Key and DbtDt fields for eligible customer accounts based on the number of overdue days.
6. Mark the SysAssetClassAlt_Key for specific customer accounts as 'LOS' if they meet certain conditions.
7. Nullify the DbtDt for customer accounts that are classified as 'LOS'.
8. Update the FinalAssetClassAlt_Key in the account table based on the customer's SysAssetClassAlt_Key.
9. Drop the temporary table #CTE_CustomerWiseBalance.
10. Execute the Final_AssetClass_Npadate stored procedure with the specified parameters.
11. Update the ACLRUNNINGPROCESSSTATUS table to mark the 'Update_AssetClass' process as completed.
12. In case of an error, update the ACLRUNNINGPROCESSSTATUS table to mark the process as failed and log the error details.

## Business Rules

### R1 — Drop temporary table if exists

**Meaning:** Ensures that the temporary table #CTE_CustomerWiseBalance is dropped if it already exists to avoid conflicts.

### Decision Logic
| Condition | Outcome |
|---|---|
| asset_classification IS NOT NULL | Include only classified accounts |


### R2 — Create temporary table for customer balances

**Applies to:** `refcustomerid`
**Meaning:** Creates a temporary table #CTE_CustomerWiseBalance to store customer balances for processing.


### R3 — Reset DbtDt, LossDt, and DegDate fields

**Applies to:** `DbtDt, LossDt, DegDate`
**Meaning:** Resets the DbtDt, LossDt, and DegDate fields for eligible customer accounts.

### Decision Logic
| Condition | Outcome |
|---|---|
| asset_classification IS NOT NULL | Include only classified accounts |


### R4 — Mark SysAssetClassAlt_Key as 'LOS' for specific customers

**Applies to:** `SysAssetClassAlt_Key`
**Meaning:** Marks the SysAssetClassAlt_Key for specific customer accounts as 'LOS' if they meet certain conditions.

### Decision Logic
| Condition | Outcome |
|---|---|
| asset_classification IS NOT NULL | Include only classified accounts |


### R5 — Nullify DbtDt for 'LOS' customer accounts

**Applies to:** `DbtDt`
**Meaning:** Nullifies the DbtDt for customer accounts that are classified as 'LOS'.

### Decision Logic
| Condition | Outcome |
|---|---|
| asset_classification IS NOT NULL | Include only classified accounts |


### R6 — Update FinalAssetClassAlt_Key in account table

**Applies to:** `FinalAssetClassAlt_Key`
**Meaning:** Updates the FinalAssetClassAlt_Key in the account table based on the customer's SysAssetClassAlt_Key.

### Decision Logic
| Condition | Outcome |
|---|---|
| asset_classification IS NOT NULL | Include only classified accounts |


### R7 — Update DbtDt, LossDt, DegDate

**Applies to:** `DbtDt, LossDt, DegDate`
**Meaning:** The procedure sets DbtDt, LossDt, DegDate to the source-defined value when (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N') = 'N').

### Decision Logic
| Condition | Outcome |
|---|---|
| (FlgDeg equals 'Y' and FlgProcessing equals 'N') | DbtDt = NULL; LossDt = NULL; DegDate = NULL |


### R8 — Update SysAssetClassAlt_Key, DBTDT, DegDate

**Applies to:** `SysAssetClassAlt_Key, DBTDT, DegDate`
**Meaning:** The procedure sets SysAssetClassAlt_Key, DBTDT, DegDate to the source-defined value when (COALESCE(B.FlgDeg, 'N') = 'Y' AND B.FlgProcessing = 'N').

### Decision Logic
| Condition | Outcome |
|---|---|
| (FlgDeg equals 'Y' and FlgProcessing equals 'N') | SysAssetClassAlt_Key = (CASE WHEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) > @ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'SUB' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY) WHEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) <= @ProcessDate AND DATEADD(DAY, @SUB_Days + @DB1_Days, B.SysNPA_Dt) > @ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'DB1' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY) WHEN DATEADD(DAY, @SUB_Days + @DB1_Days, B.SysNPA_Dt) <= @ProcessDate AND DATEADD(DAY, @SUB_Days + @DB1_Days + @DB2_Days, B.SysNPA_Dt) > @ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'DB2' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY) WHEN DATEADD(DAY, (@DB1_Days + @SUB_Days + @DB2_Days), B.SysNPA_Dt) <= @ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'DB3' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY) END); DBTDT = (CASE WHEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) <= @ProcessDate AND DATEADD(DAY, @SUB_Days + @DB1_Days, B.SysNPA_Dt) > @ProcessDate THEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) WHEN DATEADD(DAY, @SUB_Days + @DB1_Days, B.SysNPA_Dt) <= @ProcessDate AND DATEADD(DAY, @SUB_Days + @DB1_Days + @DB2_Days, B.SysNPA_Dt) > @ProcessDate THEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) WHEN DATEADD(DAY, (@DB1_Days + @SUB_Days + @DB2_Days), B.SysNPA_Dt) <= @ProcessDate THEN DATEADD(DAY, (@SUB_Days), B.SysNPA_Dt) ELSE DBTDT END); DegDate = @ProcessDate |


### R9 — Update SysAssetClassAlt_Key

**Applies to:** `SysAssetClassAlt_Key`
**Meaning:** The procedure sets SysAssetClassAlt_Key to the source-defined value when (COALESCE(A.SplCatg1Alt_Key, 0) = 870 OR COALESCE(A.SplCatg2Alt_Key, 0) = 870 OR COALESCE(A.SplCatg3Alt_Key, 0) = 870 OR COALESCE(A.SplCatg4Alt_Key, 0) = 870) AND COALESCE(A.FlgDeg, 'N') = 'Y'.

### Decision Logic
| Condition | Outcome |
|---|---|
| (SplCatg1Alt_Key equals 870 or SplCatg2Alt_Key equals 870 or SplCatg3Alt_Key equals 870 or SplCatg4Alt_Key equals 870) and FlgDeg equals 'Y' | SysAssetClassAlt_Key = (SELECT TOP 1 AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'LOS' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY) |


### R10 — Update DbtDt

**Applies to:** `DbtDt`
**Meaning:** The procedure sets DbtDt to the source-defined value when (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N') = 'N') AND SysAssetClassAlt_Key IN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'LOS' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY).

### Decision Logic
| Condition | Outcome |
|---|---|
| (FlgDeg equals 'Y' and FlgProcessing equals 'N') and SysAssetClassAlt_Key IN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName equals 'LOS' and EffectiveFromTimeKey is at most @TIMEKEY and EffectiveToTimeKey is at least @TIMEKEY) | DbtDt = NULL |


### R11 — Update FinalAssetClassAlt_Key

**Applies to:** `FinalAssetClassAlt_Key`
**Meaning:** The procedure sets FinalAssetClassAlt_Key to the source-defined value when (ISNULL(B.FlgDeg,'N')='Y' AND ISNULL(B.FlgProcessing,'N')='N' ) AND (ISNULL(A.Asset_Norm,'NORMAL')='NORMAL' AND ISNULL(A.FlgDeg,'N')='Y') DROP TABLE #CTE_CustomerWiseBalance Exec Pro.Final_AssetClass_Npadate @timekey=@TIMEKEY,@FlgPreErosion='Y'.

### Decision Logic
| Condition | Outcome |
|---|---|
| (FlgDeg equals 'Y' and FlgProcessing equals 'N' ) and (Asset_Norm equals 'NORMAL' and FlgDeg equals 'Y') DROP TABLE #CTE_CustomerWiseBalance Exec Final_AssetClass_Npadate @timekey equals @TIMEKEY,@FlgPreErosion equals 'Y' | FinalAssetClassAlt_Key = B.SysAssetClassAlt_Key |


### R12 — Update COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT

**Applies to:** `COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT`
**Meaning:** The procedure sets COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT to the source-defined value when RUNNINGPROCESSNAME='Update_AssetClass'.

### Decision Logic
| Condition | Outcome |
|---|---|
| RUNNINGPROCESSNAME equals 'Update_AssetClass' | Update account status and audit the change |


### R13 — Update DbtDt, LossDt, DegDate

**Applies to:** `DbtDt, LossDt, DegDate`
**Meaning:** The procedure sets DbtDt, LossDt, DegDate to the source-defined value when (ISNULL(B.FlgDeg,'N')='Y' AND ISNULL(B.FlgProcessing,'N')='N' ).

### Decision Logic
| Condition | Outcome |
|---|---|
| (FlgDeg equals 'Y' and FlgProcessing equals 'N' ) | DbtDt = NULL; LossDt = NULL; DegDate = NULL |


### R14 — Update SysAssetClassAlt_Key, DBTDT, DegDate

**Applies to:** `SysAssetClassAlt_Key, DBTDT, DegDate`
**Meaning:** The procedure sets SysAssetClassAlt_Key, DBTDT, DegDate to the source-defined value when (ISNULL(B.FlgDeg,'N')='Y' AND B.FlgProcessing='N' ).

### Decision Logic
| Condition | Outcome |
|---|---|
| (FlgDeg equals 'Y' and FlgProcessing equals 'N' ) | SysAssetClassAlt_Key = ( CASE WHEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt)>@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='SUB' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) WHEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)>@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='DB1' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) WHEN DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days+@DB2_Days,B.SysNPA_Dt)>@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='DB2' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) WHEN DATEADD(DAY,(@DB1_Days+@SUB_Days+@DB2_Days),B.SysNPA_Dt)<=@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='DB3' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) END); DBTDT = (CASE WHEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)>@ProcessDate THEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt) WHEN DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days+@DB2_Days,B.SysNPA_Dt)>@ProcessDate THEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt) WHEN DATEADD(DAY,(@DB1_Days+@SUB_Days+@DB2_Days),B.SysNPA_Dt)<=@ProcessDate THEN DATEADD(DAY,(@SUB_Days),B.SysNPA_Dt) ELSE DBTDT END); DegDate = @ProcessDate |


### R15 — Update SysAssetClassAlt_Key

**Applies to:** `SysAssetClassAlt_Key`
**Meaning:** The procedure sets SysAssetClassAlt_Key to the source-defined value when ( ISNULL(A.SplCatg1Alt_Key,0) =870 OR ISNULL(A.SplCatg2Alt_Key,0) =870 OR ISNULL(A.SplCatg3Alt_Key,0)=870 OR ISNULL(A.SplCatg4Alt_Key,0)=870 ) AND ISNULL(A.FlgDeg,'N')='Y'.

### Decision Logic
| Condition | Outcome |
|---|---|
| ( SplCatg1Alt_Key equals 870 or SplCatg2Alt_Key equals 870 or SplCatg3Alt_Key equals 870 or SplCatg4Alt_Key equals 870 ) and FlgDeg equals 'Y' | SysAssetClassAlt_Key = (SELECT TOP 1 AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='LOS' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) |


### R16 — Update DbtDt

**Applies to:** `DbtDt`
**Meaning:** The procedure sets DbtDt to the source-defined value when (ISNULL(B.FlgDeg,'N')='Y' AND ISNULL(B.FlgProcessing,'N')='N' ) AND SysAssetClassAlt_Key IN(SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='LOS' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY).

### Decision Logic
| Condition | Outcome |
|---|---|
| (FlgDeg equals 'Y' and FlgProcessing equals 'N' ) and SysAssetClassAlt_Key IN(SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName equals 'LOS' and EffectiveFromTimeKey is at most @TIMEKEY and EffectiveToTimeKey is at least @TIMEKEY) | DbtDt = NULL |


### R17 — Update COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT

**Applies to:** `COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT`
**Meaning:** The procedure sets COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT to the source-defined value when RUNNINGPROCESSNAME='Update_AssetClass'.

### Decision Logic
| Condition | Outcome |
|---|---|
| CATCH block | COMPLETED = 'N'; ERRORDATE = GETDATE(); ERRORDESCRIPTION = ERROR_MESSAGE(); COUNT = ISNULL(COUNT,0)+1 |


### R18 — Calculate SysAssetClassAlt_Key and DbtDt

**Applies to:** `SysAssetClassAlt_Key, DbtDt`
**Meaning:** Calculates and updates the SysAssetClassAlt_Key and DbtDt fields for eligible customer accounts based on the number of overdue days.

### Decision Logic
| Condition | Outcome |
|---|---|
| asset_classification IS NOT NULL | Include only classified accounts |

## Calculations

- **SUB_Days:** (SELECT RefValue FROM PRO.refperiod WHERE BusinessRule='SUB_Days' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY)
- **DB1_Days:** (SELECT RefValue FROM PRO.refperiod WHERE BusinessRule='DB1_Days' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY)
- **DB2_Days:** (SELECT RefValue FROM PRO.refperiod WHERE BusinessRule='DB2_Days' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY)
- **MoveToLoss:** (SELECT cast(RefValue/100.00 as decimal(5,2)) FROM PRO.refperiod where BusinessRule='MoveToLoss' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY)
- **ProcessDate:** (SELECT DATE FROM SysDayMatrix WHERE TimeKey=@TIMEKEY)

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `PRO.refperiod` | Read | Provides: RefValue, cast(RefValue/100.00 as decimal(5, 2)) |
| `SysDayMatrix` | Read | Provides: DATE |
| `DimAssetClass` | Read | Provides: DBTDT, A.REFCUSTOMERID, B.FlgProcessing, B.SysNPA_Dt, B.FlgDeg, AssetClassAlt_Key |

_5 working/temporary table(s) used only for intermediate calculation steps are omitted here - see the verification report for the full technical lineage._

## Exception Handling

In case of an error, the ACLRUNNINGPROCESSSTATUS table is updated to mark the 'Update_AssetClass' process as failed, and the error details are logged.

## Findings / Needs Review

- The actual logic and tables involved in the procedure are not specified in the provided code chunk.
- The specific operations on tables and the conditions under which they occur are not specified in the provided code chunk.
- Reconciliation review required: tables_read evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: tables_written evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: tables_written evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: rule evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: rule evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation detected a source/report discrepancy: Synthesized condition conflicts with deterministic predicate evidence.
- Reconciliation detected a source/report discrepancy: Synthesized affected fields do not match deterministic SQL/AST evidence.
- Reconciliation detected a source/report discrepancy: Synthesized rule affects different fields than the deterministic evidence.
- Reconciliation detected a source/report discrepancy: Synthesized outcome/assignment conflicts with deterministic evidence.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `PRO.Update_AssetClass.StoredProcedure_verification.md`._
