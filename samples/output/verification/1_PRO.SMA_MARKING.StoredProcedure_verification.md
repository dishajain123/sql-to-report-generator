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
| Run Timestamp | `2026-09-04T09:44:13.715376+00:00` |
| Object ID | `obj_6ed9993261c9` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_36bd1113e76b` |
| Total LLM Calls | `3` |
| Successful Calls | `3` |
| Failed Calls | `0` |
| Prompt Tokens | `109140` |
| Completion Tokens | `15000` |
| Total Tokens | `124140` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 28174 | available |
| synthesis | 1 | 1 | 0 | 45471 | available |
| synthesis_revision | 1 | 1 | 0 | 50495 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Reset negative DPD to zero [CONFLICT] (`rule_01`) | `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt` | Ensures that any negative overdue days are reset to zero for all types of overdue days. |
| 🔴 2 | Calculate maximum overdue days [CONFLICT] (`rule_02`) | `DPD_Max` | Determines the maximum overdue days for each account by comparing different types of overdue days. |
| 🔴 3 | Assign SMA class based on maximum overdue days [CONFLICT] (`rule_03`) | `SMA_CLASS` | Classifies accounts into SMA categories based on the maximum overdue days. |
| 🔴 4 | Assign SMA reason based on facility type and maximum overdue days [CONFLICT] (`rule_04`) | `SMA_REASON` | Determines the reason for SMA classification based on the facility type and the type of overdue days that matches the maximum overdue days. |
| 🔴 5 | Update SMA class key and SMA date [CONFLICT] (`rule_05`) | `SMA_CLASS_KEY` | Updates the SMA class key and SMA date for accounts and customers based on the maximum SMA class. |
| 🟠 6 | Record account movement history [LLM_ONLY] (`rule_06`) | `Not specified` | Records movement history for accounts if there is a change in SMA status. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Reset negative DPD to zero (rule_01) | isnull(DPD_IntService,0)<0; isnull(DPD_NoCredit,0)<0; isnull(DPD_Overdrawn,0)<0; isnull(DPD_Overdue,0)<0; isnull(DPD_Renewal,0)<0; isnull(DPD_StockStmt,0)<0 | Not cited | full_source | full_source | Needs Review |
| 2 | Calculate maximum overdue days (rule_02) | (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_IntService,0)>=isn… | Not cited | full_source | full_source | Needs Review |
| 3 | Assign SMA class based on maximum overdue days (rule_03) | dpd.DPD_Max BETWEEN 1 AND 30; dpd.DPD_Max BETWEEN 31 AND 60; dpd.DPD_Max BETWEEN 61 AND 90; dpd.DPD_Max > 90 | Not cited | full_source | full_source | Needs Review |
| 4 | Assign SMA reason based on facility type and maximum overdue days (rule_04) | A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0); A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0); A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD… | Not cited | full_source | full_source | Needs Review |
| 5 | Update SMA class key and SMA date (rule_05) | SMA_CLASS='SMA_0'; SMA_CLASS='SMA_1'; SMA_CLASS='SMA_2' | Not cited | full_source | full_source | Needs Review |
| 6 | Record account movement history (rule_06) | B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'') | Not cited | full_source | full_source | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 6
- **By rule type:** explicit = 6
- **By validation status:** unverified = 6

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Reconciliation Summary

- **Matched facts:** 0
- **Deterministic-only facts:** 93
- **LLM-only claims:** 1
- **Conflicts:** 5
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` rule (`recon_8a908954edd3`): full_source, 01_nested_block:chunk_text_13;01_nested_block:embedded_05_18;01_nested_block:embedded_06_19;01_nested_block:embedded_07_20;01_nested_block:embedded_08_21;01_nested_block:embedded_09_22 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_58a76e0a7692`): full_source - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_40015d420743`): full_source - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_9bb4db6e373b`): full_source - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_26fc32b2ea67`): full_source - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 15/100
- **Statement coverage:** 100 / 129 (77.5%)
- **Rule grounding coverage:** 5 / 6 (83.3%)
- **Conflicts:** 5
- **Contradictions:** 11
- **Review required items:** 17
- **Review required:** Yes

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.

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
- Synthesis response reached the output limit; recovered rules may be incomplete.
