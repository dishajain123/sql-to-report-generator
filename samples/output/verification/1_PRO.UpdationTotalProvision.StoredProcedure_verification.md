# UpdationTotalProvision — Verification & Traceability

> Companion artifact to `PRO.UpdationTotalProvision.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_be4d0d7c6278` |

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
| Source Hash | `f1607db425260204915f4c601cdf33dc40a9651555505006688f0b0b4bc51ccd` |
| Configuration Version | `646dbbaf5be7f3a0` |
| Run Timestamp | `2026-09-04T12:27:09.951866+00:00` |
| Object ID | `obj_be4d0d7c6278` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_6f26ee71a558` |
| Total LLM Calls | `3` |
| Successful Calls | `3` |
| Failed Calls | `0` |
| Prompt Tokens | `79040` |
| Completion Tokens | `15000` |
| Total Tokens | `94040` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 19107 | available |
| synthesis | 1 | 1 | 0 | 35472 | available |
| synthesis_revision | 1 | 1 | 0 | 39461 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Reset negative TOTALPROVISION [CONFLICT] (`rule_01`) | `TOTALPROVISION` | If the TOTALPROVISION is negative, it is reset to zero. |
| 🔴 2 | Reset negative BANKTOTALPROVISION [CONFLICT] (`rule_02`) | `BANKTOTALPROVISION` | If the BANKTOTALPROVISION is negative, it is reset to zero. |
| 🔴 3 | Reset negative RBITOTALPROVISION [CONFLICT] (`rule_03`) | `RBITOTALPROVISION` | If the RBITOTALPROVISION is negative, it is reset to zero. |
| 🔴 4 | Set TOTALPROVISION to NetBalance if overdue [CONFLICT] (`rule_04`) | `TOTALPROVISION` | If the TOTALPROVISION is greater than the NetBalance and the NetBalance is positive, the TOTALPROVISION is set to the NetBalance. |
| 🔴 5 | Set BANKTOTALPROVISION to NetBalance if overdue [CONFLICT] (`rule_05`) | `BANKTOTALPROVISION` | If the BANKTOTALPROVISION is greater than the NetBalance and the NetBalance is positive, the BANKTOTALPROVISION is set to the NetBalance. |
| 🔴 6 | Set RBITOTALPROVISION to NetBalance if overdue [CONFLICT] (`rule_06`) | `RBITOTALPROVISION` | If the RBITOTALPROVISION is greater than the NetBalance and the NetBalance is positive, the RBITOTALPROVISION is set to the NetBalance. |
| 🔴 7 | Update RBITOTALPROVISION based on RBI and BANKTOTALPROVISION [CONFLICT] (`rule_07`) | `RBITOTALPROVISION, PROVSECURED, PROVUNSECURED, ADDLPROVISION, PROVCOVERGOVGUR, PROVDFV` | If RBITOTALPROVISION is greater than BANKTOTALPROVISION, update RBITOTALPROVISION to RBITOTALPROVISION and other related fields to RBI valu… |
| 🔴 8 | Update asset class and restructuring fields [CONFLICT] (`rule_08`) | `FinalAssetClassAlt_Key, InitialAssetClassAlt_Key, AppliedNormalProvPer, FinalNpaDt, RestructureStage, UpgradeDate, SurvPeriodEndDate` | Updates the asset class, restructuring stage, and other related fields based on the effective time key and restructuring details. |
| 🔴 9 | Update restructuring stage to STD-STD-NPA-STD [CONFLICT] (`rule_09`) | `RestructureStage` | If the restructuring stage is 'STD-STD-NPA-STD-NPA-STD', it is updated to 'STD-STD-NPA-STD'. |
| 🔴 10 | Update restructuring stage to NPA-STD-NPA-STD [CONFLICT] (`rule_10`) | `RestructureStage` | If the restructuring stage is 'NPA-STD-NPA-STD-NPA-STD', it is updated to 'NPA-STD-NPA-STD'. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Reset negative TOTALPROVISION (rule_01) | ISNULL(TOTALPROVISION,0)<0 | Not cited | Not cited | Not cited | Needs Review |
| 2 | Reset negative BANKTOTALPROVISION (rule_02) | ISNULL(BANKTOTALPROVISION,0)<0 | Not cited | Not cited | Not cited | Needs Review |
| 3 | Reset negative RBITOTALPROVISION (rule_03) | ISNULL(RBITOTALPROVISION,0)<0 | Not cited | Not cited | Not cited | Needs Review |
| 4 | Set TOTALPROVISION to NetBalance if overdue (rule_04) | ISNULL(TOTALPROVISION,0)>NetBalance AND ISNULL(NetBalance,0)>0 | Not cited | Not cited | Not cited | Needs Review |
| 5 | Set BANKTOTALPROVISION to NetBalance if overdue (rule_05) | ISNULL(BANKTOTALPROVISION,0)>NetBalance AND ISNULL(NetBalance,0)>0 | Not cited | Not cited | Not cited | Needs Review |
| 6 | Set RBITOTALPROVISION to NetBalance if overdue (rule_06) | ISNULL(RBITOTALPROVISION,0)>NetBalance AND ISNULL(NetBalance,0)>0 | Not cited | Not cited | Not cited | Needs Review |
| 7 | Update RBITOTALPROVISION based on RBI and BANKTOTALPROVISION (rule_07) | ISNULL(A.RBITOTALPROVISION,0)>ISNULL(A.BANKTOTALPROVISION,0) | Not cited | Not cited | Not cited | Needs Review |
| 8 | Update asset class and restructuring fields (rule_08) | A.EffectiveFromTimeKey<=@TimeKey And A.EffectiveToTimeKey>=@TimeKey | Not cited | Not cited | Not cited | Needs Review |
| 9 | Update restructuring stage to STD-STD-NPA-STD (rule_09) | RestructureStage='STD-STD-NPA-STD-NPA-STD' | Not cited | Not cited | Not cited | Needs Review |
| 10 | Update restructuring stage to NPA-STD-NPA-STD (rule_10) | RestructureStage='NPA-STD-NPA-STD-NPA-STD' | Not cited | Not cited | Not cited | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 10
- **By rule type:** explicit = 10
- **By validation status:** unverified = 10

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Reconciliation Summary

- **Matched facts:** 0
- **Deterministic-only facts:** 80
- **LLM-only claims:** 0
- **Conflicts:** 10
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` rule (`recon_9beec5fc6d57`): 01_nested_block:embedded_04_22 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_bb9570d45d58`): 01_nested_block:embedded_05_23 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_aa20263517ff`): 01_nested_block:embedded_06_24 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_959188a8b940`): 01_nested_block:embedded_07_25;01_nested_block_2:chunk_text_16;01_nested_block_2:embedded_10_27 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_8551beaa6fbd`): 01_nested_block:embedded_08_26 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 17/100
- **Statement coverage:** 83 / 101 (82.2%)
- **Rule grounding coverage:** 10 / 10 (100.0%)
- **Conflicts:** 10
- **Contradictions:** 21
- **Review required items:** 31
- **Review required:** Yes

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE ##ACCOUNTCAL SET TOTALPROVISION=NetBalance WHERE ISNULL(TOTALPROVISION,0)>NetBalance AND ISNULL(NetBalance,0)>0...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET A.TOTPROVISION=B.TOTALPROVISION,A.BANKTOTPROVISION=B.BANKTOTPROVISION,A.RBITOTPROVISION=B.RBITOTPROVISION...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): select Distinct a.CustomerEntityID
into          #tempACCOUNTCAL_1
from          ##ACCOUNTCAL a
inner join    Excepti...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): Delete        A
from          ##ACCOUNTCAL a
inner join    ExceptionFinalStatusType b
on            a.CustomerAcID=b....
- Technical extraction response reached the output limit; recovered facts may be incomplete.
- Commented-out logic found in source (7 block(s)) and excluded from extraction - not included in the business rules.
- Informational uncertainty: Calculation uncertainty: `AddlProvPer` uses a fractional numeric value in an expression that divides by a constant; the intended unit or scale cannot be established from SQL text alone.
- Synthesis response reached the output limit; recovered rules may be incomplete.
