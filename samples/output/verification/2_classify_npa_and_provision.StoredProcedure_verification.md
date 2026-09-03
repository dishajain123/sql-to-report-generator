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
| Run Timestamp | `2026-09-03T22:51:48.029776+00:00` |
| Object ID | `obj_4cb17b45df7c` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_2dde66f784e8` |
| Total LLM Calls | `3` |
| Successful Calls | `3` |
| Failed Calls | `0` |
| Prompt Tokens | `24638` |
| Completion Tokens | `6053` |
| Total Tokens | `30691` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 4796 | available |
| synthesis | 1 | 1 | 0 | 11173 | available |
| synthesis_revision | 1 | 1 | 0 | 14722 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify account as STANDARD [LLM_ONLY] (`rule_01`) | `asset_classification, provisioning_percentage` | Classifies the account as STANDARD if overdue days are 90 or less. |
| 🟠 2 | Classify account as SUBSTANDARD [LLM_ONLY] (`rule_02`) | `asset_classification, provisioning_percentage` | Classifies the account as SUBSTANDARD if overdue days are between 91 and 365. |
| 🟠 3 | Classify account as DOUBTFUL1 or DOUBTFUL2 [LLM_ONLY] (`rule_03`) | `asset_classification, provisioning_percentage` | Classifies the account as DOUBTFUL1 or DOUBTFUL2 based on overdue days and doubtful since days. |
| 🟠 4 | Classify account as LOSS or DOUBTFUL3 [LLM_ONLY] (`rule_04`) | `asset_classification, provisioning_percentage` | Classifies the account as LOSS or DOUBTFUL3 based on overdue days and doubtful since days. |
| 🟠 5 | Calculate provisioning amount [LLM_ONLY] (`rule_05`) | `provisioning_amount` | Calculates the provisioning amount based on the outstanding amount, unsecured amount, and provisioning percentage. |
| 🟠 6 | Handle NO_DATA_FOUND exception [LLM_ONLY] (`rule_06`) | `Not specified` | Handles the NO_DATA_FOUND exception by inserting an audit log entry and raising the exception. |
| 🟠 7 | Handle OTHERS exception [LLM_ONLY] (`rule_07`) | `Not specified` | Handles the OTHERS exception by inserting an audit log entry and raising the exception. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify account as STANDARD (rule_01) | v_overdue_days <= 90 | Not cited | Not cited | Not cited | Needs Review |
| 2 | Classify account as SUBSTANDARD (rule_02) | v_overdue_days BETWEEN 91 AND 365 | Not cited | Not cited | Not cited | Needs Review |
| 3 | Classify account as DOUBTFUL1 or DOUBTFUL2 (rule_03) | v_overdue_days BETWEEN 366 AND 1095 | Not cited | Not cited | Not cited | Needs Review |
| 4 | Classify account as LOSS or DOUBTFUL3 (rule_04) | v_overdue_days > 1095 | Not cited | Not cited | Not cited | Needs Review |
| 5 | Calculate provisioning amount (rule_05) | (v_outstanding_amt - v_unsecured_amt) * (v_provision_pct / 100) + (v_unsecured_amt * ((v_provision_pct + 10) / 100)) | Not cited | Not cited | Not cited | Needs Review |
| 6 | Handle NO_DATA_FOUND exception (rule_06) | WHEN NO_DATA_FOUND THEN INSERT INTO NPA_AUDIT_LOG (account_id, old_classification, new_classification, changed_on) VALUES (p_account_id, NULL, 'ACCOUNT_NOT_FOUND', SYSDATE); RAISE; | Not cited | Not cited | Not cited | Needs Review |
| 7 | Handle OTHERS exception (rule_07) | WHEN OTHERS THEN INSERT INTO NPA_AUDIT_LOG (account_id, old_classification, new_classification, changed_on) VALUES (p_account_id, NULL, 'ERROR: ' \|\| SQLERRM, SYSDATE); RAISE; | Not cited | Not cited | Not cited | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** explicit = 7
- **By validation status:** unverified = 7

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

## Reconciliation Summary

- **Matched facts:** 4
- **Deterministic-only facts:** 10
- **LLM-only claims:** 7
- **Conflicts:** 0
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_83c5a0515a13`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_b20a7fd9c1b4`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_d982bab80a93`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_a9822cfb8432`): no direct provenance - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_8990664ad137`): no direct provenance - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 65/100
- **Statement coverage:** 12 / 41 (29.3%)
- **Rule grounding coverage:** 0 / 7 (0.0%)
- **Conflicts:** 0
- **Contradictions:** 0
- **Review required items:** 7
- **Review required:** Yes

Statement parse success is below the preferred threshold.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Informational uncertainty: Calculation uncertainty: `v_provision_pct` uses a fractional numeric value in an expression that divides by a constant; the intended unit or scale cannot be established from SQL text alone.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: v_overdue_days > 1095
