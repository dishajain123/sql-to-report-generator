# Anonymous Block — Verification & Traceability

> Companion artifact to `tmprpo5nvya_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_6f5dbd97cf87` |
| Raw technical object name (from source) | `ANONYMOUS_BLOCK` |

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
| Source Hash | `678586f6e9e1c9d44b564f371c7789f4c2e2f6407c1446f6e56975ecc24720e3` |
| Configuration Version | `072834053f80c136` |
| Run Timestamp | `2026-09-03T23:24:51.279868+00:00` |
| Object ID | `obj_6f5dbd97cf87` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_d6c7f66bd296` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `32207` |
| Completion Tokens | `4902` |
| Total Tokens | `37109` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 4246 | available |
| synthesis | 1 | 1 | 0 | 9626 | available |
| synthesis_revision | 2 | 2 | 0 | 23237 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify overdue accounts [LLM_ONLY] (`rule_01`) | `asset_classification, provision_pct` | Classifies accounts based on the number of overdue days. |
| 🔴 2 | Update provisioning amount [CONFLICT] (`rule_02`) | `provision_amount` | Calculates and updates the provisioning amount for each account. |
| 🔴 3 | Insert audit log entry [CONFLICT] (`rule_03`) | `NPA_AUDIT_LOG, account_id, new_classification, change_date` | Logs the change in asset classification and provisioning percentage for each account. |
| 🔴 4 | Merge provisioning data [CONFLICT] (`rule_04`) | `provision_amount, classification_date` | Merges the provisioning amount and classification date into the NPA_PROVISION table. |
| 🟠 5 | Handle exceptions [LLM_ONLY] (`rule_05`) | `Not specified` | Logs the error and rolls back the transaction on failure. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify overdue accounts (rule_01) | rec.overdue_days BETWEEN 91 AND 365; rec.overdue_days BETWEEN 366 AND 1095; NOT (rec.overdue_days BETWEEN 91 AND 365) AND NOT (rec.overdue_days BETWEEN 366 AND 1095) | Not cited | Not cited | Not cited | Needs Review |
| 2 | Update provisioning amount (rule_02) | rec.overdue_days > 90 AND asset_classification = 'STANDARD' | Not cited | Not cited | Not cited | Needs Review |
| 3 | Insert audit log entry (rule_03) | rec.overdue_days > 90 AND asset_classification = 'STANDARD' | Not cited | Not cited | Not cited | Needs Review |
| 4 | Merge provisioning data (rule_04) | rec.overdue_days > 90 AND asset_classification = 'STANDARD' | Not cited | Not cited | Not cited | Needs Review |
| 5 | Handle exceptions (rule_05) | WHEN OTHERS | Not cited | Not cited | Not cited | Needs Review |

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
- **Deterministic-only facts:** 7
- **LLM-only claims:** 2
- **Conflicts:** 4
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_906a903ddd9c`): full_source
- `LLM_ONLY` rule (`recon_8e5fc0e6f534`): no direct provenance - No deterministic evidence was found for this claim.
- `CONFLICT` rule (`recon_abe8b0d33a60`): 00_declaration:chunk_text_01 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_fc8a0cb822b9`): 00_declaration:chunk_text_01 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_26754eb8c056`): 00_declaration:chunk_text_01 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 8/100
- **Statement coverage:** 10 / 24 (41.7%)
- **Rule grounding coverage:** 3 / 5 (60.0%)
- **Conflicts:** 4
- **Contradictions:** 5
- **Review required items:** 11
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized rule affects different fields than the deterministic evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not deterministically identify the database object type from the raw source.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: rec.overdue_days > 90 AND asset_classification = 'STANDARD'
