# Update Assetclass — Business Logic Report

**Procedure:** `PRO.Update_AssetClass`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Purpose | The procedure Update_AssetClass updates asset classes and related fields for customer accounts based on predefined business rules and conditions. |
| Business rules | 8 |
| Tables read | 4 |
| Tables written | 1 |
| Produces audit trail | No |

## Review Required

The reconciliation stage detected source/report inconsistencies. Business Rules, Calculations, and Data Touched are provisional and must not be treated as confirmed until the discrepancies are resolved.

## What This Does

The procedure Update_AssetClass updates asset classes and related fields for customer accounts based on predefined business rules and conditions.

## Process Flow

1. Drops the temporary table #CTE_CustomerWiseBalance if it exists.
2. Initializes variables with values from the PRO.refperiod table based on the @TIMEKEY parameter.
3. Creates a temporary table #CTE_CustomerWiseBalance with customer balances from the ##ACCOUNTCAL and ##CUSTOMERCAL tables.
4. Updates the DbtDt, LossDt, and DegDate fields in the ##CUSTOMERCAL table based on conditions related to the SysNPA_Dt and @ProcessDate.
5. Updates the SysAssetClassAlt_Key field in the ##CUSTOMERCAL table based on the days overdue and predefined conditions.
6. Updates the DbtDt field in the ##CUSTOMERCAL table to NULL for certain customers.
7. Updates the FinalAssetClassAlt_Key field in the ##ACCOUNTCAL table based on conditions from the ##CUSTOMERCAL table.
8. Executes the Pro.Final_AssetClass_Npadate stored procedure with the @TIMEKEY parameter and FlgPreErosion set to 'Y'.
9. Updates the PRO.ACLRUNNINGPROCESSSTATUS table to mark the 'Update_AssetClass' process as completed or logs an error if an exception occurs.

## Business Rules

### R1 — Drop temporary table if exists

**Validation:** Incomplete LLM-authored rule; missing or empty field(s): output_field/fields_affected

**Eligibility:** The temporary table #CTE_CustomerWiseBalance exists
**Action:** Drops the temporary table #CTE_CustomerWiseBalance
**Meaning:** Removes the temporary table #CTE_CustomerWiseBalance if it already exists to avoid conflicts.


### R2 — Initialize variables from refperiod

**Validation:** Incomplete LLM-authored rule; missing or empty field(s): condition, output_field/fields_affected

**Action:** Initializes variables @SUB_Days, @DB1_Days, @DB2_Days, @MoveToDB1, and @MoveToLoss with values from the PRO.refperiod table.
**Meaning:** Initializes variables with values from the PRO.refperiod table based on the @TIMEKEY parameter.


### R3 — Create temporary table with customer balances

**Validation:** Incomplete LLM-authored rule; missing or empty field(s): condition, output_field/fields_affected

**Action:** Creates a temporary table #CTE_CustomerWiseBalance with customer balances from the ##ACCOUNTCAL and ##CUSTOMERCAL tables.
**Meaning:** Creates a temporary table #CTE_CustomerWiseBalance with customer balances from the ##ACCOUNTCAL and ##CUSTOMERCAL tables.


### R4 — Update DbtDt, LossDt, and DegDate fields

**Applies to:** `DbtDt, LossDt, DegDate`
**Eligibility:** Customer degree flag is 'Y' and processing flag is 'N'
**Action:** Sets DbtDt, LossDt, and DegDate fields to NULL.
**Meaning:** Updates the DbtDt, LossDt, and DegDate fields in the ##CUSTOMERCAL table based on conditions related to the SysNPA_Dt and @ProcessDate.


### R5 — Update SysAssetClassAlt_Key based on days overdue

**Applies to:** `SysAssetClassAlt_Key`
**Eligibility:** Customer degree flag is 'Y' and processing flag is 'N'
**Action:** Sets SysAssetClassAlt_Key based on the number of days overdue.
**Meaning:** Updates the SysAssetClassAlt_Key field in the ##CUSTOMERCAL table based on the days overdue and predefined conditions.


### R6 — Update DbtDt field to NULL for LOS customers

**Applies to:** `DbtDt`
**Eligibility:** Customer degree flag is 'Y', processing flag is 'N', and asset class is 'LOS'
**Action:** Sets DbtDt field to NULL.
**Meaning:** Updates the DbtDt field in the ##CUSTOMERCAL table to NULL for certain customers.


### R7 — Update FinalAssetClassAlt_Key in account level

**Applies to:** `FinalAssetClassAlt_Key`
**Eligibility:** Customer degree flag is 'Y', processing flag is 'N', asset norm is 'NORMAL', and degree flag is 'Y'
**Action:** Sets FinalAssetClassAlt_Key in the ##ACCOUNTCAL table based on SysAssetClassAlt_Key from the ##CUSTOMERCAL table.
**Meaning:** Updates the FinalAssetClassAlt_Key field in the ##ACCOUNTCAL table based on conditions from the ##CUSTOMERCAL table.


### R8 — Execute Final_AssetClass_Npadate stored procedure

**Validation:** Incomplete LLM-authored rule; missing or empty field(s): condition, output_field/fields_affected

**Action:** Executes the Pro.Final_AssetClass_Npadate stored procedure.
**Meaning:** Executes the Pro.Final_AssetClass_Npadate stored procedure with the @TIMEKEY parameter and FlgPreErosion set to 'Y'.

## Calculations

- **SysAssetClassAlt_Key:** CASE WHEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt)>@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='SUB' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) WHEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)>@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='DB1' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) WHEN DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days+@DB2_Days,B.SysNPA_Dt)>@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='DB2' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) WHEN DATEADD(DAY,@SUB_Days+@DB1_Days+@DB2_Days,B.SysNPA_Dt)<=@ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='DB3' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) END
- **DBTDT:** CASE WHEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)>@ProcessDate THEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt) WHEN DATEADD(DAY,@SUB_Days+@DB1_Days,B.SysNPA_Dt)<=@ProcessDate AND DATEADD(DAY,@SUB_Days+@DB1_Days+@DB2_Days,B.SysNPA_Dt)>@ProcessDate THEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt) WHEN DATEADD(DAY,@SUB_Days+@DB1_Days+@DB2_Days,B.SysNPA_Dt)<=@ProcessDate THEN DATEADD(DAY,@SUB_Days,B.SysNPA_Dt) ELSE DBTDT END

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `PRO.refperiod` | Read | Provides: RefValue, cast(RefValue/100.00 as decimal(5, 2)) |
| `SysDayMatrix` | Read | Provides: DATE |
| `DimAssetClass` | Read | Provides: DBTDT, A.REFCUSTOMERID, B.FlgProcessing, B.SysNPA_Dt, B.FlgDeg, AssetClassAlt_Key |

_5 working/temporary table(s) used only for intermediate calculation steps are omitted here - see the pipeline run log for the full technical lineage._

## Exception Handling

If an exception occurs during the execution of the procedure, the PRO.ACLRUNNINGPROCESSSTATUS table is updated to log the error with COMPLETED set to 'N', ERRORDATE set to the current date and time, ERRORDESCRIPTION set to the error message, and COUNT incremented.

## Findings / Needs Review

- The actual logic and operations within the procedure are not specified in the provided code chunk.
- Possible unreviewed decision logic near source line 122-123 (ASSIGNMENT/UPDATE): no synthesized rule's evidence appears to reference "UPDATE PRO.ACLRUNNINGPROCESSSTATUS  	SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 132-133 (ASSIGNMENT/UPDATE): no synthesized rule's evidence appears to reference "UPDATE PRO.ACLRUNNINGPROCESSSTATUS  	SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1". Needs human review to confirm whether this is business-relevant.
- Reconciliation review required: tables_read evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: tables_written evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: tables_written evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: rule evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: coverage evidence is deterministic_only and must not be treated as a confirmed business rule.
- Reconciliation detected a source/report discrepancy: Synthesized condition conflicts with deterministic predicate evidence.
- Reconciliation detected a source/report discrepancy: Synthesized affected fields do not match deterministic SQL/AST evidence.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
