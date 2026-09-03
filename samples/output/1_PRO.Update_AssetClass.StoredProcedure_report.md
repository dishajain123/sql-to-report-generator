# Update Assetclass — Business Logic Report

**Procedure:** `PRO.Update_AssetClass`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Purpose | This procedure updates the asset classification and related fields for customer accounts based on the current time period and predefined rules. It affects both customer-level and account-level data. |
| Business rules | 12 |
| Tables read | 4 |
| Tables written | 1 |
| Produces audit trail | No |

## Review Required

The reconciliation stage detected source/report inconsistencies. Business Rules, Calculations, and Data Touched are provisional and must not be treated as confirmed until the discrepancies are resolved.

## What This Does

This procedure updates the asset classification and related fields for customer accounts based on the current time period and predefined rules. It affects both customer-level and account-level data.

## Process Flow

1. Drop the temporary table #CTE_CustomerWiseBalance if it exists.
2. Initialize variables with values from the refperiod table based on the provided time key.
3. Create a temporary table #CTE_CustomerWiseBalance with customer-wise balance data from the ##ACCOUNTCAL and ##CUSTOMERCAL tables.
4. Reset certain fields in the ##CUSTOMERCAL table based on specific conditions.
5. Update the SysAssetClassAlt_Key, DbtDt, and DegDate fields in the ##CUSTOMERCAL table based on the number of days overdue and predefined rules.
6. Mark the SysAssetClassAlt_Key for certain customers as 'LOS' based on specific conditions.
7. Set the DbtDt field to NULL for customers with a specific asset class.
8. Update the FinalAssetClassAlt_Key field in the ##ACCOUNTCAL table based on the SysAssetClassAlt_Key from the ##CUSTOMERCAL table.
9. Drop the temporary table #CTE_CustomerWiseBalance.
10. Execute the Final_AssetClass_Npadate stored procedure with the provided time key and flag.
11. Update the ACLRUNNINGPROCESSSTATUS table to mark the 'Update_AssetClass' process as completed.
12. In case of an error, update the ACLRUNNINGPROCESSSTATUS table with error details and mark the process as not completed.

## Business Rules

### R1 — Drop temporary table if exists

**Eligibility:** OBJECT_ID('TEMPDB..#CTE_CustomerWiseBalance') IS NOT NULL
**Meaning:** Ensures that the temporary table #CTE_CustomerWiseBalance is dropped if it already exists.


### R2 — Initialize variables

**Applies to:** `INT, BusinessRule`
**Meaning:** Initializes variables with values from the refperiod table based on the provided time key.


### R3 — Create temporary table

**Applies to:** `refcustomerid`
**Meaning:** Creates a temporary table #CTE_CustomerWiseBalance with customer-wise balance data from the ##ACCOUNTCAL and ##CUSTOMERCAL tables.


### R4 — Reset specific fields

**Applies to:** `DbtDt, LossDt, DegDate`
**Eligibility:** (FlgDeg equals 'Y' and FlgProcessing equals 'N')
**Meaning:** Resets certain fields in the ##CUSTOMERCAL table based on specific conditions.


### R5 — Update asset class and dates

**Applies to:** `SysAssetClassAlt_Key, DbtDt, DegDate`
**Eligibility:** (FlgDeg equals 'Y' and FlgProcessing equals 'N')
**Meaning:** The asset class and dates is updated.


### R6 — Mark asset class as 'LOS'

**Applies to:** `SysAssetClassAlt_Key`
**Eligibility:** (SplCatg1Alt_Key equals 870 or SplCatg2Alt_Key equals 870 or SplCatg3Alt_Key equals 870 or SplCatg4Alt_Key equals 870) and FlgDeg equals 'Y'
**Meaning:** Mark asset class as 'LOS'.


### R7 — Set DbtDt to NULL for LOS customers

**Applies to:** `DbtDt`
**Eligibility:** (FlgDeg equals 'Y' and FlgProcessing equals 'N') and SysAssetClassAlt_Key IN(SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName equals 'LOS' and EffectiveFromTimeKey is at most @TIMEKEY and EffectiveToTimeKey is at least @TIMEKEY)
**Meaning:** Sets the DbtDt field to NULL for customers with a specific asset class.


### R8 — Update final asset class at account level

**Applies to:** `FinalAssetClassAlt_Key`
**Eligibility:** (FlgDeg equals 'Y' and FlgProcessing equals 'N') and (Asset_Norm equals 'NORMAL' and FlgDeg equals 'Y')
**Meaning:** The final asset class at account level is updated.


### R9 — Update DbtDt, LossDt, DegDate

**Applies to:** `DbtDt, LossDt, DegDate`
**Eligibility:** (FlgDeg equals 'Y' and FlgProcessing equals 'N')
**Meaning:** The procedure sets DbtDt, LossDt, DegDate to the source-defined value when (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N') = 'N').


### R10 — Update SysAssetClassAlt_Key, DBTDT, DegDate

**Applies to:** `SysAssetClassAlt_Key, DBTDT, DegDate`
**Eligibility:** (FlgDeg equals 'Y' and FlgProcessing equals 'N')
**Meaning:** The procedure sets SysAssetClassAlt_Key, DBTDT, DegDate to the source-defined value when (COALESCE(B.FlgDeg, 'N') = 'Y' AND B.FlgProcessing = 'N').


### R11 — Update SysAssetClassAlt_Key

**Applies to:** `SysAssetClassAlt_Key`
**Eligibility:** (SplCatg1Alt_Key equals 870 or SplCatg2Alt_Key equals 870 or SplCatg3Alt_Key equals 870 or SplCatg4Alt_Key equals 870) and FlgDeg equals 'Y'
**Meaning:** The procedure sets SysAssetClassAlt_Key to the source-defined value when (COALESCE(A.SplCatg1Alt_Key, 0) = 870 OR COALESCE(A.SplCatg2Alt_Key, 0) = 870 OR COALESCE(A.SplCatg3Alt_Key, 0) = 870 OR COALESCE(A.SplCatg4Alt_Key, 0) = 870) AND COALESCE(A.FlgDeg, 'N') = 'Y'.


### R12 — Update DbtDt

**Applies to:** `DbtDt`
**Eligibility:** (FlgDeg equals 'Y' and FlgProcessing equals 'N') and SysAssetClassAlt_Key IN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName equals 'LOS' and EffectiveFromTimeKey is at most @TIMEKEY and EffectiveToTimeKey is at least @TIMEKEY)
**Meaning:** The procedure sets DbtDt to the source-defined value when (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N') = 'N') AND SysAssetClassAlt_Key IN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'LOS' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY).

## Calculations

- **SysAssetClassAlt_Key:** CASE WHEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt)>@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='SUB' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) WHEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)>@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='DB1' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) WHEN DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days+@DB2_Days,B.SysNPA_Dt)>@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='DB2' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) WHEN DATEADD(DAY,(@DB1_Days+@SUB_Days+@DB2_Days),B.SysNPA_Dt)<=@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='DB3' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) END
- **DBTDT:** CASE WHEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)>@ProcessDate THEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt) WHEN DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days+@DB2_Days,B.SysNPA_Dt)>@ProcessDate THEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt) WHEN DATEADD(DAY,(@DB1_Days+@SUB_Days+@DB2_Days),B.SysNPA_Dt)<=@ProcessDate THEN DATEADD(DAY,(@SUB_Days),B.SysNPA_Dt) ELSE DBTDT END

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `PRO.refperiod` | Read | Provides: RefValue, cast(RefValue/100.00 as decimal(5, 2)) |
| `SysDayMatrix` | Read | Provides: DATE |
| `DimAssetClass` | Read | Provides: DBTDT, A.REFCUSTOMERID, B.FlgProcessing, B.SysNPA_Dt, B.FlgDeg, AssetClassAlt_Key |

_5 working/temporary table(s) used only for intermediate calculation steps are omitted here - see the verification report for the full technical lineage._

## Exception Handling

In case of an error, the procedure updates the ACLRUNNINGPROCESSSTATUS table with error details and marks the 'Update_AssetClass' process as not completed.

## Findings / Needs Review

- The actual logic and operations within the procedure are not specified in the provided code chunk.
- Unresolved dynamic SQL or missing context for exception handling behavior
- Reconciliation review required: tables_read evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: tables_written evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: tables_written evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: rule evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: rule evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: coverage evidence is deterministic_only and must not be treated as a confirmed business rule.
- Reconciliation detected a source/report discrepancy: Synthesized condition conflicts with deterministic predicate evidence.
- Reconciliation detected a source/report discrepancy: Synthesized affected fields do not match deterministic SQL/AST evidence.
- Reconciliation detected a source/report discrepancy: Synthesized rule affects different fields than the deterministic evidence.
- Reconciliation detected a source/report discrepancy: Synthesized outcome/assignment conflicts with deterministic evidence.
- Unresolved dynamic SQL or missing context for exception handling behavior.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `PRO.Update_AssetClass.StoredProcedure_verification.md`._
