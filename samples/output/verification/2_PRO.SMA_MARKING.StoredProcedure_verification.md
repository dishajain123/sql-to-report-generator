# SMA Marking — Verification & Traceability

> Companion artifact to `PRO.SMA_MARKING.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_6ed9993261c9` |
| Raw technical object name (from source) | `SMA_MARKING` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `1c8e103a89db04c2` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `fff7585a03cb147d56cb99cc3fa108a5a08556179ba637f7356954000e362a12` |
| Configuration Version | `646dbbaf5be7f3a0` |
| Run Timestamp | `2026-09-04T12:08:26.243966+00:00` |
| Object ID | `obj_6ed9993261c9` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_21a6c35c6f71` |
| Total LLM Calls | `3` |
| Successful Calls | `3` |
| Failed Calls | `0` |
| Prompt Tokens | `110405` |
| Completion Tokens | `14377` |
| Total Tokens | `124782` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 28174 | available |
| synthesis | 1 | 1 | 0 | 45530 | available |
| synthesis_revision | 1 | 1 | 0 | 51078 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Reset negative DPD to zero [LLM_ONLY] (`rule_01`) | `DPD_IntService` | Ensures that any negative overdue days are reset to zero for all accounts. |
| 🟠 2 | Reset negative DPD to zero [LLM_ONLY] (`rule_02`) | `DPD_NoCredit` | Ensures that any negative overdue days are reset to zero for all accounts. |
| 🟠 3 | Reset negative DPD to zero [LLM_ONLY] (`rule_03`) | `DPD_Overdrawn` | Ensures that any negative overdue days are reset to zero for all accounts. |
| 🟠 4 | Reset negative DPD to zero [LLM_ONLY] (`rule_04`) | `DPD_Overdue` | Ensures that any negative overdue days are reset to zero for all accounts. |
| 🟠 5 | Reset negative DPD to zero [LLM_ONLY] (`rule_05`) | `DPD_Renewal` | Ensures that any negative overdue days are reset to zero for all accounts. |
| 🟠 6 | Reset negative DPD to zero [LLM_ONLY] (`rule_06`) | `DPD_StockStmt` | Ensures that any negative overdue days are reset to zero for all accounts. |
| 🟠 7 | Calculate maximum overdue days [LLM_ONLY] (`rule_07`) | `DPD_Max` | Determines the maximum overdue days for an account by comparing various overdue day metrics. |
| 🔴 8 | Assign SMA class based on overdue days [CONFLICT] (`rule_08`) | `SMA_CLASS` | Assigns an SMA class to the account based on the maximum overdue days. |
| 🟠 9 | Assign SMA reason based on overdue days [LLM_ONLY] (`rule_09`) | `SMA_REASON` | Assigns a reason for the SMA class based on the maximum overdue days. |
| 🟠 10 | Update SMA movement history [LLM_ONLY] (`rule_10`) | `Not specified` | Updates the SMA movement history for accounts that have changed SMA status. |
| 🟠 11 | Update SMA movement history [LLM_ONLY] (`rule_11`) | `Not specified` | Updates the SMA movement history for accounts that have changed SMA status. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Reset negative DPD to zero (rule_01) | isnull(A.DPD_IntService,0)<0 | Not cited | full_source | full_source | Needs Review |
| 2 | Reset negative DPD to zero (rule_02) | isnull(A.DPD_NoCredit,0)<0 | Not cited | full_source | full_source | Needs Review |
| 3 | Reset negative DPD to zero (rule_03) | isnull(A.DPD_Overdrawn,0)<0 | Not cited | full_source | full_source | Needs Review |
| 4 | Reset negative DPD to zero (rule_04) | isnull(A.DPD_Overdue,0)<0 | Not cited | full_source | full_source | Needs Review |
| 5 | Reset negative DPD to zero (rule_05) | isnull(A.DPD_Renewal,0)<0 | Not cited | full_source | full_source | Needs Review |
| 6 | Reset negative DPD to zero (rule_06) | isnull(A.DPD_StockStmt,0)<0 | Not cited | full_source | full_source | Needs Review |
| 7 | Calculate maximum overdue days (rule_07) | isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0) OR isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0) OR isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn,0) OR isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue,0) OR isnull(A.DPD_Renewa… | Not cited | full_source | full_source | Needs Review |
| 8 | Assign SMA class based on overdue days (rule_08) | dpd.DPD_Max BETWEEN 1 AND 30; dpd.DPD_Max BETWEEN 31 AND 60; dpd.DPD_Max BETWEEN 61 AND 90; dpd.DPD_Max > 90; ELSE | Not cited | full_source | full_source | Needs Review |
| 9 | Assign SMA reason based on overdue days (rule_09) | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE, 0) = ISNULL(dpd.DPD_MAX, 0); A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT, 0) = ISNULL(dpd.DPD_MAX, 0); A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE, 0) = ISN… | Not cited | full_source | full_source | Needs Review |
| 10 | Update SMA movement history (rule_10) | B.CustomerAcID IS NULL OR (B.CustomerAcID IS NOT NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS) | Not cited | full_source | full_source | Needs Review |
| 11 | Update SMA movement history (rule_11) | AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey < @TIMEKEY AND EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB WHERE AA.CustomerAcID = BB.CustomerAcID AND BB.EffectiveToTimeKey = 49999 AND AA.MOVEMENTTOSTATUS <> BB.MOVEMENTTOSTATUS) | Not cited | full_source | full_source | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 11
- **By rule type:** explicit = 11
- **By validation status:** unverified = 11

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Reconciliation Summary

- **Matched facts:** 0
- **Deterministic-only facts:** 93
- **LLM-only claims:** 10
- **Conflicts:** 1
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_127694eea6de`): full_source - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_205cb96c7597`): full_source - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_ca09f743cb5e`): full_source - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_b929126b4c45`): full_source - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_b8b708b094d6`): full_source - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 13/100
- **Statement coverage:** 100 / 129 (77.5%)
- **Rule grounding coverage:** 1 / 11 (9.1%)
- **Conflicts:** 1
- **Contradictions:** 2
- **Review required items:** 13
- **Review required:** Yes

Rule grounding coverage is below the preferred threshold.

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): Update         A
SET            A.ReviewDueDt=NULL,A.DPD_Renewal=0
FROM           ##ACCOUNTCAL A 
INNER JOIN     #DPD...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0  
  
  
  
----/* CALCULATE MAX DPD */  
  
  IF O...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.FLGSMA='Y'  
FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.FLGSMA='Y'  
FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.UCIF_ID =B.UCIF_ID  
WHERE B.FLGSMA='Y...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS,A.SMA_DT=B.SMA_Dt  
FROM ##CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASSUc...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): SELECT @TIMEKEY,B.CustomerAcID,A.SMA_CLASS,B.SMA_CLASS   
FROM PRO.PREVSMASTATUS A  RIGHT OUTER JOIN  #SMACLASS B  
ON...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE  ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL  
    
  
  
 --IF OB...
- Technical extraction response reached the output limit; recovered facts may be incomplete.
- Commented-out logic found in source (19 block(s)) and excluded from extraction - not included in the business rules.
