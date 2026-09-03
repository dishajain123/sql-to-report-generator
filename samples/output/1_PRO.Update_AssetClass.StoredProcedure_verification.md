# Update Assetclass — Verification & Traceability

> Companion artifact to `PRO.Update_AssetClass.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_445a87a93ad4` |
| Raw technical object name (from source) | `Update_AssetClass` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `dde4a0b3fc523696` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `1e571bfed09ebc1d24f341a406ed83ab6e3d501af64c6b4dc1af0500d7ed9a07` |
| Configuration Version | `04a16e5eaa317a4d` |
| Run Timestamp | `2026-09-03T12:09:10.871763+00:00` |
| Object ID | `obj_445a87a93ad4` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_f18576d8d2ff` |
| Total LLM Calls | `5` |
| Successful Calls | `5` |
| Failed Calls | `0` |
| Prompt Tokens | `28634` |
| Completion Tokens | `6866` |
| Total Tokens | `35500` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 4 | 4 | 0 | 17496 | available |
| synthesis | 1 | 1 | 0 | 18004 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Drop temporary table if exists [LLM_ONLY] (`rule_aa32f6f89eb8`) | `Not specified` | Ensures that the temporary table #CTE_CustomerWiseBalance is dropped if it already exists. |
| 🟠 2 | Initialize variables [LLM_ONLY] (`rule_9c984c0836c7`) | `INT, BusinessRule` | Initializes variables with values from the refperiod table based on the provided time key. |
| 🟠 3 | Create temporary table [LLM_ONLY] (`rule_6cead8bc1d8a`) | `refcustomerid` | Creates a temporary table #CTE_CustomerWiseBalance with customer-wise balance data from the ##ACCOUNTCAL and ##CUSTOMERCAL tables. |
| 🔴 4 | Reset specific fields [CONFLICT] (`rule_0f524ef1021a`) | `DbtDt, LossDt, DegDate` | Resets certain fields in the ##CUSTOMERCAL table based on specific conditions. |
| 🟠 5 | Update asset class and dates [LLM_ONLY] (`rule_c39d4e89c45a`) | `SysAssetClassAlt_Key, DbtDt, DegDate` | The asset class and dates is updated. |
| 🔴 6 | Mark asset class as 'LOS' [CONFLICT] (`rule_cc45d08ee522`) | `SysAssetClassAlt_Key` | Mark asset class as 'LOS'. |
| 🔴 7 | Set DbtDt to NULL for LOS customers [CONFLICT] (`rule_a625366093f0`) | `DbtDt` | Sets the DbtDt field to NULL for customers with a specific asset class. |
| 🟠 8 | Update final asset class at account level [LLM_ONLY] (`rule_33b71b9e2e7e`) | `FinalAssetClassAlt_Key` | The final asset class at account level is updated. |
| 🔴 9 | Update DbtDt, LossDt, DegDate [CONFLICT] (`rule_195600bb7c87`) | `DbtDt, LossDt, DegDate` | The procedure sets DbtDt, LossDt, DegDate to the source-defined value when (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N'… |
| 🔴 10 | Update SysAssetClassAlt_Key, DBTDT, DegDate [CONFLICT] (`rule_0f5bed57d8ee`) | `SysAssetClassAlt_Key, DBTDT, DegDate` | The procedure sets SysAssetClassAlt_Key, DBTDT, DegDate to the source-defined value when (COALESCE(B.FlgDeg, 'N') = 'Y' AND B.FlgProcessing… |
| 🟠 11 | Update SysAssetClassAlt_Key [MATCHED] (`rule_111ebb409bf5`) | `SysAssetClassAlt_Key` | The procedure sets SysAssetClassAlt_Key to the source-defined value when (COALESCE(A.SplCatg1Alt_Key, 0) = 870 OR COALESCE(A.SplCatg2Alt_Ke… |
| 🟠 12 | Update DbtDt [MATCHED] (`rule_9cc3a649bd5a`) | `DbtDt` | The procedure sets DbtDt to the source-defined value when (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N') = 'N') AND SysA… |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Drop temporary table if exists (rule_aa32f6f89eb8) | IF OBJECT_ID('TEMPDB..#CTE_CustomerWiseBalance') IS NOT NULL DROP TABLE #CTE_CustomerWiseBalance | /tmp/tmp5qd974q6.sql \| Lines 22-129 \| Chunk 01_nested_block; /tmp/tmp5qd974q6.sql \| Lines 10-13 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_07 | 01_nested_block:nested_block | conditions[0]: OBJECT_ID('TEMPDB..#CTE_CustomerWiseBalance') IS NOT NULL -> DROP TABLE #CTE_CustomerWiseBalance; table_operations[5]; tables_read[5]: SysDayMatrix \| READ \| target: DATE \| WHERE: TimeKey=@TIMEKEY) IF OBJECT_ID('TEMPDB..#CTE_CustomerWiseBalance') IS NOT NULL DROP TABLE #CTE_CustomerWiseBalance | Verified |
| 2 | Initialize variables (rule_9c984c0836c7) | DECLARE @SUB_Days INT =(SELECT RefValue FROM PRO.refperiod WHERE BusinessRule='SUB_Days' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) | /tmp/tmp5qd974q6.sql \| Line 4 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_02 | 01_nested_block:nested_block | table_operations[0]; tables_read[0]: PRO.refperiod \| READ \| target: RefValue \| WHERE: BusinessRule='SUB_Days' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) | Verified |
| 3 | Create temporary table (rule_6cead8bc1d8a) | SELECT A.refcustomerid,SUM(ISNULL(A.BALANCE,0)) Balance INTO #CTE_CustomerWiseBalance FROM ##ACCOUNTCAL A INNER JOIN ##CUSTOMERCAL B ON A.refcustomerid=B.refcustomerid WHERE ISNULL(B.FlgProcessing,'N')='N' GROUP BY A.refcustomerid | /tmp/tmp5qd974q6.sql \| Lines 16-25 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_08 | 01_nested_block:nested_block | table_operations[6]; tables_read[6]: ##ACCOUNTCAL \| READ \| target: A.refcustomerid, SUM(ISNULL(A.BALANCE, 0)) Balance INTO #CTE_CustomerWiseBalance \| WHERE: ISNULL(B.FlgProcessing,'N')='N' | Verified |
| 4 | Reset specific fields (rule_0f524ef1021a) | UPDATE B SET B.DbtDt=NULL,B.LossDt=NULL,B.DegDate=NULL FROM #CTE_CustomerWiseBalance A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID WHERE (ISNULL(B.FlgDeg,'N')='Y' AND ISNULL(B.FlgProcessing,'N')='N') | /tmp/tmp5qd974q6.sql \| Lines 22-129 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_09; /tmp/tmp5qd974q6.sql \| Lines 27-32 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_16 | 01_nested_block:nested_block | table_operations[7]; table_operations[8]; table_operations[9]; table_operations[23]; tables_read[7]: B \| READ \| target: A.REFCUSTOMERID, B.REFCUSTOMERID, B.FlgDeg, B.FlgProcessing \| WHERE: (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N') = 'N'); tables_read[8]: #CTE_CustomerWiseBalance \| READ \| target: A.REFCUSTOMERID, B.REFCUSTOMERID, B.FlgDeg, B.FlgProcessing \| WHERE: (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N') = 'N…; _(+4 more instance(s) not shown)_ | Verified |
| 5 | Update asset class and dates (rule_c39d4e89c45a) | UPDATE B SET B.SysAssetClassAlt_Key= (--CASE WHEN B.CurntQtrRv< (A.BALANCE *@MoveToLoss) THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='LOS' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) CASE WHEN DATEADD(D… | /tmp/tmp5qd974q6.sql \| Lines 22-129 \| Chunk 01_nested_block | 01_nested_block:nested_block | calculations[1]: metric not specified \| explanation not specified | Verified |
| 6 | Mark asset class as 'LOS' (rule_cc45d08ee522) | UPDATE A SET A.SysAssetClassAlt_Key= (SELECT TOP 1 AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='LOS' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) FROM ##CUSTOMERCAL A WHERE (ISNULL(A.SplCatg1Alt_Key,0) =870 OR ISNULL… | /tmp/tmp5qd974q6.sql \| Lines 22-129 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_11; /tmp/tmp5qd974q6.sql \| Lines 54-67 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_18 | 01_nested_block:nested_block | table_operations[14]; table_operations[15]; table_operations[16]; table_operations[26]; table_operations[27]; tables_read[14]: B \| READ \| target: SysAssetClassAlt_Key, A.REFCUSTOMERID, B.REFCUSTOMERID, AssetClassAlt_Key, B.FlgDeg, B.FlgProcessing, EffectiveToTimeKey, AssetClassShortName, EffectiveFromTimeK…; _(+6 more instance(s) not shown)_ | Verified |
| 7 | Set DbtDt to NULL for LOS customers (rule_a625366093f0) | UPDATE B SET DbtDt=NULL FROM #CTE_CustomerWiseBalance A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID WHERE (ISNULL(B.FlgDeg,'N')='Y' AND ISNULL(B.FlgProcessing,'N')='N') AND SysAssetClassAlt_Key IN(SELECT AssetClassAlt_Key FROM DimAssetClass… | /tmp/tmp5qd974q6.sql \| Lines 22-129 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_12; /tmp/tmp5qd974q6.sql \| Lines 68-72 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_19 | 01_nested_block:nested_block | table_operations[17]; table_operations[18]; table_operations[19]; table_operations[20]; table_operations[28]; table_operations[29]; _(+8 more instance(s) not shown)_ | Verified |
| 8 | Update final asset class at account level (rule_33b71b9e2e7e) | UPDATE A SET A.FinalAssetClassAlt_Key=B.SysAssetClassAlt_Key FROM ##ACCOUNTCAL A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID WHERE (ISNULL(B.FlgDeg,'N')='Y' AND ISNULL(B.FlgProcessing,'N')='N') AND (ISNULL(A.Asset_Norm,'NORMAL')='NORMAL' AND… | /tmp/tmp5qd974q6.sql \| Lines 74-97 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_13 | 01_nested_block:nested_block | table_operations[21]; tables_read[21]: ##CUSTOMERCAL \| READ \| target: B.SysAssetClassAlt_Key, B.DBTDT, B.DegDate \| WHERE: (COALESCE(B.FlgDeg, 'N') = 'Y' AND B.FlgProcessing = 'N'); tables_written[4]: ##ACCOUNTCAL \| UPDATE \| target: A.FinalAssetClassAlt_Key \| WHERE: (ISNULL(B.FlgDeg,'N')='Y' AND ISNULL(B.FlgProcessing,'N')='N' ) AND (ISNULL(A.Asset_Norm,'NORMAL')='NORMAL' AND… | Verified |
| 9 | Update DbtDt, LossDt, DegDate (rule_195600bb7c87) | UPDATE B SET B.DbtDt=NULL,B.LossDt=NULL,B.DegDate=NULL FROM #CTE_CustomerWiseBalance a INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID WHERE (ISNULL(B.FlgDeg,'N')='Y' AND ISNULL(B.FlgProcessing,'N')='N' ) /*---CALCULATE SysAssetClassAlt_Key ,Dbt… | /tmp/tmp5qd974q6.sql \| Lines 22-129 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_09; /tmp/tmp5qd974q6.sql \| Lines 27-32 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_16 (+1 more span(s)) | 01_nested_block:nested_block | table_operations[7]; table_operations[8]; table_operations[9]; table_operations[23]; tables_read[7]: B \| READ \| target: A.REFCUSTOMERID, B.REFCUSTOMERID, B.FlgDeg, B.FlgProcessing \| WHERE: (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N') = 'N'); tables_read[8]: #CTE_CustomerWiseBalance \| READ \| target: A.REFCUSTOMERID, B.REFCUSTOMERID, B.FlgDeg, B.FlgProcessing \| WHERE: (COALESCE(B.FlgDeg, 'N') = 'Y' AND COALESCE(B.FlgProcessing, 'N') = 'N…; _(+13 more instance(s) not shown)_ | Needs Review |
| 10 | Update SysAssetClassAlt_Key, DBTDT, DegDate (rule_0f5bed57d8ee) | UPDATE B SET B.SysAssetClassAlt_Key= (--CASE WHEN B.CurntQtrRv< (A.BALANCE *@MoveToLoss) THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='LOS' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) CASE WHEN DATEADD(D… | /tmp/tmp5qd974q6.sql \| Lines 22-129 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_10; /tmp/tmp5qd974q6.sql \| Lines 34-53 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_17 (+1 more span(s)) | 01_nested_block:nested_block | table_operations[10]; table_operations[11]; table_operations[12]; table_operations[13]; table_operations[24]; table_operations[25]; _(+9 more instance(s) not shown)_ | Needs Review |
| 11 | Update SysAssetClassAlt_Key (rule_111ebb409bf5) | UPDATE A SET A.SysAssetClassAlt_Key= (SELECT TOP 1 AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName='LOS' AND EffectiveFromTimeKey<=@TIMEKEY AND EffectiveToTimeKey>=@TIMEKEY) FROM ##CUSTOMERCAL A WHERE ( ISNULL(A.SplCatg1Alt_Key,0) =870 OR ISNUL… | /tmp/tmp5qd974q6.sql \| Lines 22-129 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_11; /tmp/tmp5qd974q6.sql \| Lines 54-67 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_18 | 01_nested_block:nested_block | table_operations[14]; table_operations[15]; table_operations[16]; table_operations[26]; table_operations[27]; tables_read[14]: B \| READ \| target: SysAssetClassAlt_Key, A.REFCUSTOMERID, B.REFCUSTOMERID, AssetClassAlt_Key, B.FlgDeg, B.FlgProcessing, EffectiveToTimeKey, AssetClassShortName, EffectiveFromTimeK…; _(+6 more instance(s) not shown)_ | Needs Review |
| 12 | Update DbtDt (rule_9cc3a649bd5a) | UPDATE B SET DbtDt=NULL FROM #CTE_CustomerWiseBalance A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID WHERE (ISNULL(B.FlgDeg,'N')='Y' AND ISNULL(B.FlgProcessing,'N')='N' ) AND SysAssetClassAlt_Key IN(SELECT AssetClassAlt_Key FROM DimAssetClass… | /tmp/tmp5qd974q6.sql \| Lines 22-129 \| Chunk 01_nested_block \| Statement 01_nested_block:chunk_text_12; /tmp/tmp5qd974q6.sql \| Lines 68-72 \| Chunk 01_nested_block \| Statement 01_nested_block:embedded_01_19 | 01_nested_block:nested_block | table_operations[17]; table_operations[18]; table_operations[19]; table_operations[20]; table_operations[28]; table_operations[29]; _(+8 more instance(s) not shown)_ | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 12
- **By rule type:** explicit = 12
- **By validation status:** insufficient_evidence = 4, verified = 8

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 5
- **Deterministic-only facts:** 1
- **LLM-only claims:** 7
- **Conflicts:** 13
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_read (`recon_7cb44c7e80ca`): 01_nested_block
- `CONFLICT` tables_read (`recon_7cb44c7e80ca`): 01_nested_block
- `CONFLICT` tables_read (`recon_7cb44c7e80ca`): 01_nested_block
- `CONFLICT` tables_read (`recon_7cb44c7e80ca`): 01_nested_block
- `LLM_ONLY` tables_written (`recon_d2eca4ddd9bc`): 01_nested_block

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 0/100
- **Statement coverage:** 11 / 31 (35.5%)
- **Rule grounding coverage:** 7 / 12 (58.3%)
- **Conflicts:** 13
- **Contradictions:** 20
- **Review required items:** 40
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): SELECT A.refcustomerid,SUM(ISNULL(A.BALANCE,0)) Balance 
INTO #CTE_CustomerWiseBalance FROM ##ACCOUNTCAL A INNER JOIN #...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE PRO.ACLRUNNINGPROCESSSTATUS 
	SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNUL...
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "B.DbtDt", "expression": "NULL"}, {"column": "B.LossDt", "expression": "NULL"}, {"column": "B.DegDate", "expression": "NULL"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "B.SysAssetClassAlt_Key", "expression": "(CASE WHEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) > @ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'SUB' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY) WHEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) <= @ProcessDate AND DATEADD(DAY, @SUB_Days + @DB1_Days, B.SysNPA_Dt) > @ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'DB1' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY) WHEN DATEADD(DAY, @SUB_Days + @DB1_Days, B.SysNPA_Dt) <= @ProcessDate AND DATEADD(DAY, @SUB_Days + @DB1_Days + @DB2_Days, B.SysNPA_Dt) > @ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'DB2' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY) WHEN DATEADD(DAY, (@DB1_Days + @SUB_Days + @DB2_Days), B.SysNPA_Dt) <= @ProcessDate THEN (SELECT AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'DB3' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY) END)"}, {"column": "B.DBTDT", "expression": "(CASE WHEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) <= @ProcessDate AND DATEADD(DAY, @SUB_Days + @DB1_Days, B.SysNPA_Dt) > @ProcessDate THEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) WHEN DATEADD(DAY, @SUB_Days + @DB1_Days, B.SysNPA_Dt) <= @ProcessDate AND DATEADD(DAY, @SUB_Days + @DB1_Days + @DB2_Days, B.SysNPA_Dt) > @ProcessDate THEN DATEADD(DAY, @SUB_Days, B.SysNPA_Dt) WHEN DATEADD(DAY, (@DB1_Days + @SUB_Days + @DB2_Days), B.SysNPA_Dt) <= @ProcessDate THEN DATEADD(DAY, (@SUB_Days), B.SysNPA_Dt) ELSE DBTDT END)"}, {"column": "B.DegDate", "expression": "@ProcessDate"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "A.SysAssetClassAlt_Key", "expression": "(SELECT TOP 1 AssetClassAlt_Key FROM DimAssetClass WHERE AssetClassShortName = 'LOS' AND EffectiveFromTimeKey <= @TIMEKEY AND EffectiveToTimeKey >= @TIMEKEY)"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "DbtDt", "expression": "NULL"}]
