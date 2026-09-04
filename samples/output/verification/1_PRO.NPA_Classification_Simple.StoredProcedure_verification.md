# NPA Classification Simple — Verification & Traceability

> Companion artifact to `PRO.NPA_Classification_Simple.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_6df4a37e0d2e` |
| Raw technical object name (from source) | `NPA_Classification_Simple` |

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
| Source Hash | `457174dc853a88d1f08fbd42ccd79e17f4bd6cf6b5389078bdab330ea3f3f7dd` |
| Configuration Version | `0fd36651926da2e3` |
| Run Timestamp | `2026-09-04T02:24:09.442354+00:00` |
| Object ID | `obj_6df4a37e0d2e` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_fc92c7f5b0f7` |
| Total LLM Calls | `2` |
| Successful Calls | `2` |
| Failed Calls | `0` |
| Prompt Tokens | `13994` |
| Completion Tokens | `2441` |
| Total Tokens | `16435` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 5090 | available |
| synthesis | 1 | 1 | 0 | 11345 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify asset class by overdue days [LLM_ONLY] (`rule_01`) | `AssetClass` | Classifies the account's asset class based on the number of days past due. If the account is overdue by 90 days or less, it is classified a… |
| 🟠 2 | Flag account as NPA [LLM_ONLY] (`rule_02`) | `NpaFlag` | Flags the account as a Non-Performing Asset (NPA) if its asset class is not Standard. If the asset class is Standard, the NPA flag is set t… |
| 🔴 3 | Calculate additional provisioning [CONFLICT] (`rule_03`) | `AddlProvision` | Calculates the additional provisioning for accounts flagged as NPA based on the outstanding balance and additional provision percentage. |
| 🔴 4 | Stamp classification date [CONFLICT] (`rule_04`) | `ClassificationDate` | Stamps the classification date for accounts newly marked as NPA if the classification date is currently NULL. |
| 🔴 5 | Flag for restructuring review [CONFLICT] (`rule_05`) | `RestructureReviewFlag` | Flags accounts with 61 to 90 days past due for restructuring review. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify asset class by overdue days (rule_01) | A.DaysPastDue <= 90; A.DaysPastDue BETWEEN 91 AND 180; A.DaysPastDue BETWEEN 181 AND 365 | Not cited | Not cited | Not cited | Needs Review |
| 2 | Flag account as NPA (rule_02) | A.AssetClass = 'STANDARD' | Not cited | Not cited | Not cited | Needs Review |
| 3 | Calculate additional provisioning (rule_03) | A.NpaFlag = 'Y' AND ISNULL(A.AddlProvisionPer, 0) <> 0 | Not cited | Not cited | Not cited | Needs Review |
| 4 | Stamp classification date (rule_04) | A.NpaFlag = 'Y' AND A.ClassificationDate IS NULL | Not cited | Not cited | Not cited | Needs Review |
| 5 | Flag for restructuring review (rule_05) | A.DaysPastDue BETWEEN 61 AND 90 | Not cited | Not cited | Not cited | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 5
- **By rule type:** explicit = 5
- **By validation status:** unverified = 5

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Reconciliation Summary

- **Matched facts:** 4
- **Deterministic-only facts:** 12
- **LLM-only claims:** 2
- **Conflicts:** 4
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_eb4a6b6b61a8`): full_source
- `LLM_ONLY` rule (`recon_e90d4098fc61`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_1932fae534f2`): no direct provenance - No deterministic evidence was found for this claim.
- `CONFLICT` rule (`recon_82e30033b683`): 04_batch3_nested_block:embedded_01_11 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_4e22574f8327`): 04_batch3_nested_block:chunk_text_06;04_batch3_nested_block:embedded_01_12 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 0/100
- **Statement coverage:** 15 / 27 (55.6%)
- **Rule grounding coverage:** 3 / 5 (60.0%)
- **Conflicts:** 4
- **Contradictions:** 7
- **Review required items:** 13
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Outcome Conflict on `source`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A
        SET A.AssetClass = (
                CASE
                    WHEN A.DaysPastDue <= 90 THEN 'STANDARD'...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE PRO.RunStatus
        SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount =...
