# SMA Stage Marking Simple — Verification & Traceability

> Companion artifact to `PRO.SMA_Stage_Marking_Simple.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_f88fd9f08d12` |
| Raw technical object name (from source) | `SMA_Stage_Marking_Simple` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `5d47055edb36cf02` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `3673da81736b9d16643f497b5db0f9bedb14d4d26e65256490c25d2d77d0c0c2` |
| Configuration Version | `0fd36651926da2e3` |
| Run Timestamp | `2026-09-04T05:28:34.960685+00:00` |
| Object ID | `obj_f88fd9f08d12` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_a0ff888ca3fd` |
| Total LLM Calls | `2` |
| Successful Calls | `2` |
| Failed Calls | `0` |
| Prompt Tokens | `14042` |
| Completion Tokens | `2521` |
| Total Tokens | `16563` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 5409 | available |
| synthesis | 1 | 1 | 0 | 11154 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify SMA stage by overdue days [LLM_ONLY] (`rule_01`) | `SmaStage` | Assigns the SMA stage classification based on the number of days an account is overdue. |
| 🟠 2 | Flag SMA status [LLM_ONLY] (`rule_02`) | `FlagSma` | Flags the account as currently in SMA status if the SMA stage is not null. |
| 🟠 3 | Attribute overdue reason by facility type [LLM_ONLY] (`rule_03`) | `SmaReason` | Attributes the overdue reason by facility type for SMA accounts. |
| 🔴 4 | Calculate SMA stage start date [CONFLICT] (`rule_04`) | `SmaStageDate` | Calculates the date the current SMA stage began by subtracting the overdue days from the process date. |
| 🔴 5 | Clear SMA status for non-overdue accounts [CONFLICT] (`rule_05`) | `SmaStage, FlagSma, SmaReason` | Clears the SMA stage, SMA status flag, and SMA reason for accounts that are no longer overdue. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify SMA stage by overdue days (rule_01) | A.OverdueDays BETWEEN 1 AND 30 | Not cited | Not cited | Not cited | Needs Review |
| 2 | Flag SMA status (rule_02) | A.SmaStage IS NOT NULL | Not cited | Not cited | Not cited | Needs Review |
| 3 | Attribute overdue reason by facility type (rule_03) | A.FacilityType IN ('CC', 'OD') | Not cited | Not cited | Not cited | Needs Review |
| 4 | Calculate SMA stage start date (rule_04) | A.FlagSma = 'Y' | Not cited | Not cited | Not cited | Needs Review |
| 5 | Clear SMA status for non-overdue accounts (rule_05) | A.OverdueDays = 0 | Not cited | Not cited | Not cited | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 5
- **By rule type:** explicit = 5
- **By validation status:** unverified = 5

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Reconciliation Summary

- **Matched facts:** 6
- **Deterministic-only facts:** 12
- **LLM-only claims:** 4
- **Conflicts:** 3
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_9c011e847efb`): full_source
- `LLM_ONLY` tables_written (`recon_d0115b0878e9`): full_source
- `LLM_ONLY` rule (`recon_bfc78396d2aa`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_4d3e75e8c8a0`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_8429c76e1f5f`): no direct provenance - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 1/100
- **Statement coverage:** 15 / 27 (55.6%)
- **Rule grounding coverage:** 2 / 5 (40.0%)
- **Conflicts:** 3
- **Contradictions:** 4
- **Review required items:** 11
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A
        SET A.SmaStage = (
                CASE
                    WHEN A.OverdueDays BETWEEN 1 AND 30 THEN 'S...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE PRO.RunStatus
        SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount =...
