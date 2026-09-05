# UpdationTotalProvision — Business Logic Report

**Procedure:** `PRO.UpdationTotalProvision`  ·  **Dialect:** T-SQL  ·  **Input:** `@TimeKey` (INT, the processing day), `@ProcessType` (VARCHAR(6))

## At a Glance

| | |
|---|---|
| Procedure | `PRO.UpdationTotalProvision` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT), `@ProcessType` (VARCHAR(6)) |
| Business rules | 10 |
| Tables read | 8 |
| Tables written | 3 |
| Produces audit trail | Not detected |

## What This Does

The UpdationTotalProvision procedure updates various provisioning fields in the account and customer tables, ensuring that the provisioning amounts are accurate and comply with regulatory requirements.

## Process Flow

1. Initializes provisioning fields to zero in the ##ACCOUNTCAL and ##CUSTOMERCAL tables.
2. Updates provisioning fields based on various conditions, such as negative values, overdue days, and net balance comparisons.
3. Applies restructuring provisions and updates related fields based on restructuring stages and types.
4. Calculates and updates additional provisions based on asset class, restructuring type, and other conditions.
5. Updates release provisions based on restructuring categories and conditions.
6. Calculates final provision percentages and updates related fields.
7. Updates secured and unsecured provisions based on final provision percentages.
8. Updates total provisions by adding secured, unsecured, and restructuring provisions.
9. Deletes records from ##CUSTOMERCAL and ##ACCOUNTCAL tables where the customer status is 'Charge Off'.
10. Updates the process status in the PRO.ACLRUNNINGPROCESSSTATUS table based on the success or failure of the procedure.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Reset negative TOTALPROVISION | `TOTALPROVISION` | If the TOTALPROVISION is negative, it is reset to zero. |
| Reset negative BANKTOTALPROVISION | `BANKTOTALPROVISION` | If the BANKTOTALPROVISION is negative, it is reset to zero. |
| Reset negative RBITOTALPROVISION | `RBITOTALPROVISION` | If the RBITOTALPROVISION is negative, it is reset to zero. |
| Set TOTALPROVISION to NetBalance if overdue | `TOTALPROVISION` | If the TOTALPROVISION is greater than the NetBalance and the NetBalance is positive, the TOTALPROVISION is set to the NetBalance. |
| Set BANKTOTALPROVISION to NetBalance if overdue | `BANKTOTALPROVISION` | If the BANKTOTALPROVISION is greater than the NetBalance and the NetBalance is positive, the BANKTOTALPROVISION is set to the NetBalance. |
| Set RBITOTALPROVISION to NetBalance if overdue | `RBITOTALPROVISION` | If the RBITOTALPROVISION is greater than the NetBalance and the NetBalance is positive, the RBITOTALPROVISION is set to the NetBalance. |
| Update RBITOTALPROVISION based on RBI and BANKTOTALPROVISION | `RBITOTALPROVISION, PROVSECURED, PROVUNSECURED, ADDLPROVISION, PROVCOVERGOVGUR, PROVDFV` | If RBITOTALPROVISION is greater than BANKTOTALPROVISION, update RBITOTALPROVISION to RBITOTALPROVISION and other related fields to RBI valu… |
| Update asset class and restructuring fields | `FinalAssetClassAlt_Key, InitialAssetClassAlt_Key, AppliedNormalProvPer, FinalNpaDt, RestructureStage, UpgradeDate, SurvPeriodEndDate` | Updates the asset class, restructuring stage, and other related fields based on the effective time key and restructuring details. |
| Update restructuring stage to STD-STD-NPA-STD | `RestructureStage` | If the restructuring stage is 'STD-STD-NPA-STD-NPA-STD', it is updated to 'STD-STD-NPA-STD'. |
| Update restructuring stage to NPA-STD-NPA-STD | `RestructureStage` | If the restructuring stage is 'NPA-STD-NPA-STD-NPA-STD', it is updated to 'NPA-STD-NPA-STD'. |

## Business Rules

### R1 — Reset negative TOTALPROVISION

**Affected Field:** `TOTALPROVISION`

**Applies to:**

- The account record is being processed

**Summary:**

- If the TOTALPROVISION is negative, it is reset to zero.


### R2 — Reset negative BANKTOTALPROVISION

**Affected Field:** `BANKTOTALPROVISION`

**Applies to:**

- The account record is being processed

**Summary:**

- If the BANKTOTALPROVISION is negative, it is reset to zero.


### R3 — Reset negative RBITOTALPROVISION

**Affected Field:** `RBITOTALPROVISION`

**Applies to:**

- The account record is being processed

**Summary:**

- If the RBITOTALPROVISION is negative, it is reset to zero.


### R4 — Set TOTALPROVISION to NetBalance if overdue

**Affected Field:** `TOTALPROVISION`

**Applies to:**

- The account record is being processed

**Summary:**

- If the TOTALPROVISION is greater than the NetBalance and the NetBalance is positive, the TOTALPROVISION is set to the NetBalance.


### R5 — Set BANKTOTALPROVISION to NetBalance if overdue

**Affected Field:** `BANKTOTALPROVISION`

**Applies to:**

- The account record is being processed

**Summary:**

- If the BANKTOTALPROVISION is greater than the NetBalance and the NetBalance is positive, the BANKTOTALPROVISION is set to the NetBalance.


### R6 — Set RBITOTALPROVISION to NetBalance if overdue

**Affected Field:** `RBITOTALPROVISION`

**Applies to:**

- The account record is being processed

**Summary:**

- If the RBITOTALPROVISION is greater than the NetBalance and the NetBalance is positive, the RBITOTALPROVISION is set to the NetBalance.


### R7 — Update RBITOTALPROVISION based on RBI and BANKTOTALPROVISION

**Affected Field:** `RBITOTALPROVISION, PROVSECURED, PROVUNSECURED, ADDLPROVISION, PROVCOVERGOVGUR, PROVDFV`

**Applies to:**

- The account record is being processed

**Summary:**

- If RBITOTALPROVISION is greater than BANKTOTALPROVISION, update RBITOTALPROVISION to RBITOTALPROVISION and other related fields to RBI values.


### R8 — Update asset class and restructuring fields

**Affected Field:** `FinalAssetClassAlt_Key, InitialAssetClassAlt_Key, AppliedNormalProvPer, FinalNpaDt, RestructureStage, UpgradeDate, SurvPeriodEndDate`

**Applies to:**

- The account record is being processed

**Summary:**

- Updates the asset class, restructuring stage, and other related fields based on the effective time key and restructuring details.


### R9 — Update restructuring stage to STD-STD-NPA-STD

**Affected Field:** `RestructureStage`

**Applies to:**

- The account record is being processed

**Summary:**

- If the restructuring stage is 'STD-STD-NPA-STD-NPA-STD', it is updated to 'STD-STD-NPA-STD'.


### R10 — Update restructuring stage to NPA-STD-NPA-STD

**Affected Field:** `RestructureStage`

**Applies to:**

- The account record is being processed

**Summary:**

- If the restructuring stage is 'NPA-STD-NPA-STD-NPA-STD', it is updated to 'NPA-STD-NPA-STD'.

## Calculations

_None identified._

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AdvAcRestructureCal` | Read + Write | Updates: FinalAssetClassAlt_Key, InitialAssetClassAlt_Key, AppliedNormalProvPer, FinalNpaDt, RestructureStage, UpgradeDate |
| `PRO.PUI_CAL` | Read + Write | Updates: FinalAssetClassAlt_Key, PUI_ProvPer, SecuredProvision, UnSecuredProvision |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `dbo.Automate_Advances` | Read | Provides: TimeKey, Timekey-1, Date |
| `DimProvision_SegStd` | Read | Provides: FinalAssetClassAlt_Key, InitialAssetClassAlt_Key, FinalNpaDt, ProvisionSecured, UpgDate, EffectiveFromTimeKey |
| `DimProvision_Seg` | Read | Provides: FinalAssetClassAlt_Key, InitialAssetClassAlt_Key, FinalNpaDt, ProvisionSecured, UpgDate, EffectiveFromTimeKey |
| `DimParameter` | Read | Provides: FinalAssetClassAlt_Key, PreRestructureNPA_Prov, ParameterShortNameEnum, PreRestructureAssetClassAlt_Key, DimParameterName, ParameterAlt_Key |
| `ADVACRESTRUCTUREDETAIL` | Read | Provides: SurvPeriodEndDate, FinalAssetClassAlt_Key, AccountEntityId, ParameterShortNameEnum, EffectiveFromTimeKey, EffectiveToTimeKey |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `##ACCOUNTCAL` | Read + Write | Updates: TOTALPROVISION, BANKTOTALPROVISION, RBITOTALPROVISION, PROVSECURED, PROVUNSECURED, ADDLPROVISION |
| `##CUSTOMERCAL` | Read + Write | Updates: TOTPROVISION, BANKTOTPROVISION, RBITOTPROVISION, CustomerEntityID |
| `#TOTALPROVCUST` | Write | Inserts data into: CUSTOMERENTITYID, SUM(COALESCE(TOTALPROVISION, 0)) AS TOTALPROVISION, SUM(COALESCE(BANKTOTALPROVISION, 0)) AS BANKTOTPROVISION, SUM(COALESCE(RBITOTALPROVISION, 0)) AS RBITOTPROVISION |
| `#tempACCOUNTCAL_2` | Write | Inserts data into: CustomerEntityID, COUNT(a.CustomerAcID) AS CNT |
| `#tempACCOUNTCAL_1` | Read | Provides: CustomerEntityID, COUNT(a.CustomerAcID) AS CNT |

_1 table reference(s) could not be resolved to a table name and are omitted from this list - see the verification report for the full technical lineage._

## Exception Handling

No explicit failure-path behavior identified.

## Findings / Needs Review

- Possible unreviewed decision logic near source line 29-30 (ASSIGNMENT): no synthesized rule's evidence appears to reference "DECLARE @vEffectivefrom  Int SET @vEffectiveFrom=(SELECT TimeKey FROM [dbo].Automate_Advances WHERE EXT_FLG='Y')            Declare @vEffectiveto INT Set @vEffe...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 114-124 (ASSIGNMENT/CASE/WHEN): no synthesized rule's evidence appears to reference "UPDATE A SET 				AddlProvPer=(CASE WHEN isnull(PreRestructureAssetClassAlt_Key,0)>1  									THEN isnull(PreRestructureNPA_Prov,0)  								ELSE 10  							END...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 128-155 (ASSIGNMENT/CASE/WHEN): no synthesized rule's evidence appears to reference "UPDATE A SET 				ProvReleasePer= CASE WHEN E.ParameterShortNameEnum='Personal' 										THEN  											CASE WHEN Res_POS_to_CurrentPOS_Per<=30  												T...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 128-155 (ASSIGNMENT/WHEN): no synthesized rule's evidence appears to reference "UPDATE A SET 				ProvReleasePer= CASE WHEN E.ParameterShortNameEnum='Personal' 										THEN  											CASE WHEN Res_POS_to_CurrentPOS_Per<=30  												T...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 128-155 (CASE/WHEN): no synthesized rule's evidence appears to reference "UPDATE A SET 				ProvReleasePer= CASE WHEN E.ParameterShortNameEnum='Personal' 										THEN  											CASE WHEN Res_POS_to_CurrentPOS_Per<=30  												T...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 203-211 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE A SET 				ProvReleasePer=AddlProvPer 		FROM PRO.AdvAcRestructureCal A 		INNER JOIN DimParameter D ON D.EffectiveFromTimeKey <=@timekey AND D.EffectiveToT...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 223-230 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE A SET 				ProvReleasePer=AddlProvPer 		FROM PRO.AdvAcRestructureCal A 		INNER JOIN DimParameter D ON D.EffectiveFromTimeKey <=@timekey AND D.EffectiveToT...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 233-241 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE A SET 				AddlProvPer=15 		FROM PRO.AdvAcRestructureCal A 		INNER JOIN DimParameter D ON D.EffectiveFromTimeKey <=@timekey AND D.EffectiveToTimeKey>=@tim...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 285-286 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE A SET FinalProvPer=100 		FROM pro.AdvAcRestructureCal A WHERE FinalProvPer>=100". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 288-289 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE A SET FinalProvPer=0 		FROM pro.AdvAcRestructureCal A WHERE FinalProvPer<=0". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 339-346 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE A	 		SET A.FlgDeg ='N' 		from PRO.AdvAcRestructureCal A 			INNER JOIN DimParameter D ON D.EffectiveFromTimeKey <=@tIMEKEY AND D.EffectiveToTimeKey>=@tIME...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 370-376 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE A  			 SET A.SecuredProvision=isnull(B.SecuredAmt,0)*isnull((PUI_ProvPer),0)/100  				,A.UnSecuredProvision=isnull(B.UnSecuredAmt,0)*isnull((PUI_ProvPer)...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 378-383 (ASSIGNMENT): no synthesized rule's evidence appears to reference "UPDATE A 		SET A.TotalProvision=ISNULL(TotalProvision,0)+(ISNULL(b.SecuredProvision,0)+ISNULL(b.UnSecuredProvision,0)) 	FROM ##ACCOUNTCAL  A 		INNER JOIN PRO.PU...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 449-456 (ASSIGNMENT/UPDATE): no synthesized rule's evidence appears to reference "UPDATE PRO.ACLRUNNINGPROCESSSTATUS  	SET COMPLETED='Y',ERRORDATE=NULL,ERRORDESCRIPTION=NULL,COUNT=ISNULL(COUNT,0)+1 	WHERE RUNNINGPROCESSNAME='UpdationTotalProv...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 459-462 (ASSIGNMENT/UPDATE): no synthesized rule's evidence appears to reference "UPDATE PRO.ACLRUNNINGPROCESSSTATUS  	SET COMPLETED='N',ERRORDATE=GETDATE(),ERRORDESCRIPTION=ERROR_MESSAGE(),COUNT=ISNULL(COUNT,0)+1 	WHERE RUNNINGPROCESSNAME='U...". Needs human review to confirm whether this is business-relevant.
- The automated analysis of this procedure exceeded the model's maximum response length and was cut short. Sections of this report may be incomplete or missing entirely. Re-run with a larger model before treating this document as a complete record of the procedure's logic.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
