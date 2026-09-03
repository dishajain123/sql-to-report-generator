# Classify Npa And Provision — Verification & Traceability

> Companion artifact to `classify_npa_and_provision.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_4cb17b45df7c` |
| Raw technical object name (from source) | `classify_npa_and_provision` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `5a4d0a2976fd37b3` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `Oracle` |
| Dialect Confidence | `High` |
| Source Hash | `41d0fce2906ef64c317d5c5bee63a55364c0d1776dad77eb71446f8273d1ab79` |
| Configuration Version | `072834053f80c136` |
| Run Timestamp | `2026-09-03T23:08:54.371862+00:00` |
| Object ID | `obj_4cb17b45df7c` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_357a21698b8b` |
| Total LLM Calls | `3` |
| Successful Calls | `3` |
| Failed Calls | `0` |
| Prompt Tokens | `24949` |
| Completion Tokens | `6920` |
| Total Tokens | `31869` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 4744 | available |
| synthesis | 1 | 1 | 0 | 11463 | available |
| synthesis_revision | 1 | 1 | 0 | 15662 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify account as Standard [LLM_ONLY] (`rule_01`) | `asset_classification, provisioning_percentage` | Classifies the account as Standard if the overdue days are 90 or less. |
| 🟠 2 | Classify account as Substandard [LLM_ONLY] (`rule_02`) | `asset_classification, provisioning_percentage` | Classifies the account as Substandard if the overdue days are between 91 and 365. |
| 🟠 3 | Classify account as Doubtful1 [LLM_ONLY] (`rule_03`) | `asset_classification, provisioning_percentage` | Classifies the account as Doubtful1 if the overdue days are between 366 and 1095 and the account has been doubtful for 365 days or less. |
| 🟠 4 | Classify account as Doubtful2 [LLM_ONLY] (`rule_04`) | `asset_classification, provisioning_percentage` | Classifies the account as Doubtful2 if the overdue days are between 366 and 1095 and the account has been doubtful for more than 365 days. |
| 🟠 5 | Classify account as Loss [LLM_ONLY] (`rule_05`) | `asset_classification, provisioning_percentage` | Classifies the account as Loss if the account has been doubtful for more than 1095 days. |
| 🟠 6 | Classify account as Doubtful3 [LLM_ONLY] (`rule_06`) | `asset_classification, provisioning_percentage` | Classifies the account as Doubtful3 if the account has been doubtful for 1095 days or less. |
| 🟠 7 | Calculate provisioning amount [LLM_ONLY] (`rule_07`) | `provisioning_amount` | Calculates the provisioning amount based on the outstanding amount, unsecured amount, and provisioning percentage. |
| 🟠 8 | Handle NO_DATA_FOUND exception [LLM_ONLY] (`rule_08`) | `Not specified` | Handles the NO_DATA_FOUND exception by logging the error in the NPA_AUDIT_LOG table. |
| 🟠 9 | Handle OTHERS exception [LLM_ONLY] (`rule_09`) | `Not specified` | Handles the OTHERS exception by logging the error in the NPA_AUDIT_LOG table and raising the exception. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify account as Standard (rule_01) | v_overdue_days <= 90 | Not cited | Not cited | Not cited | Needs Review |
| 2 | Classify account as Substandard (rule_02) | v_overdue_days BETWEEN 91 AND 365 | Not cited | Not cited | Not cited | Needs Review |
| 3 | Classify account as Doubtful1 (rule_03) | v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365 | Not cited | Not cited | Not cited | Needs Review |
| 4 | Classify account as Doubtful2 (rule_04) | v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since <= 365) | Not cited | Not cited | Not cited | Needs Review |
| 5 | Classify account as Loss (rule_05) | v_doubtful_since > 1095 | Not cited | Not cited | Not cited | Needs Review |
| 6 | Classify account as Doubtful3 (rule_06) | NOT (v_doubtful_since > 1095) | Not cited | Not cited | Not cited | Needs Review |
| 7 | Calculate provisioning amount (rule_07) | (v_outstanding_amt - v_unsecured_amt) * (v_provision_pct / 100) + (v_unsecured_amt * ((v_provision_pct + 10) / 100)) | Not cited | Not cited | Not cited | Needs Review |
| 8 | Handle NO_DATA_FOUND exception (rule_08) | WHEN NO_DATA_FOUND THEN INSERT INTO NPA_AUDIT_LOG (account_id, old_classification, new_classification, changed_on) VALUES (p_account_id, NULL, 'ACCOUNT_NOT_FOUND', SYSDATE); | Not cited | Not cited | Not cited | Needs Review |
| 9 | Handle OTHERS exception (rule_09) | WHEN OTHERS THEN INSERT INTO NPA_AUDIT_LOG (account_id, old_classification, new_classification, changed_on) VALUES (p_account_id, NULL, 'ERROR: ' \|\| SQLERRM, SYSDATE); RAISE; | Not cited | Not cited | Not cited | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 9
- **By rule type:** explicit = 9
- **By validation status:** unverified = 9

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Reconciliation Summary

- **Matched facts:** 4
- **Deterministic-only facts:** 10
- **LLM-only claims:** 9
- **Conflicts:** 0
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_2ccf178789a1`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_6b55301318f3`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_7b01dce7d0e9`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_184510e9f27a`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_dbe0ea36b873`): no direct provenance - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 65/100
- **Statement coverage:** 12 / 41 (29.3%)
- **Rule grounding coverage:** 0 / 9 (0.0%)
- **Conflicts:** 0
- **Contradictions:** 0
- **Review required items:** 9
- **Review required:** Yes

Statement parse success is below the preferred threshold.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Informational uncertainty: Calculation uncertainty: `v_provision_pct` uses a fractional numeric value in an expression that divides by a constant; the intended unit or scale cannot be established from SQL text alone.
