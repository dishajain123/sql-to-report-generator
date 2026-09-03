# Vw Active Npa Provisions — Verification & Traceability

> Companion artifact to `vw_active_npa_provisions.View_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_290a23b3bf2f` |
| Raw technical object name (from source) | `vw_active_npa_provisions` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `5c8879cd38c3a577` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `Oracle` |
| Dialect Confidence | `Medium` |
| Source Hash | `a44927dfb04652e997d51a04a13992e3becbef0f6206516d5d11fea70e3fa031` |
| Configuration Version | `5da7e25e83100117` |
| Run Timestamp | `2026-09-03T04:26:59.313837+00:00` |
| Object ID | `obj_290a23b3bf2f` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_b7e145f8be7a` |
| Total LLM Calls | `2` |
| Successful Calls | `2` |
| Failed Calls | `0` |
| Prompt Tokens | `9405` |
| Completion Tokens | `659` |
| Total Tokens | `10064` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 2704 | available |
| synthesis | 1 | 1 | 0 | 7360 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Select active NPA provisions [CONFLICT] (`rule_6bf42c965979`) | `v_classification` | Retrieves active non-performing asset provisions for accounts not classified as Standard. |
| 🔴 2 | Select active NPA provisions [CONFLICT] (`rule_dc9c84c7207b`) | `classification_date, account_id` | Select active NPA provisions. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Select active NPA provisions (rule_6bf42c965979) | la.asset_classification!= 'STANDARD'; np.classification_date = (SELECT MAX(classification_date) FROM NPA_PROVISION WHERE account_id = la.account_id) | /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_view.sql \| Lines 2-18 \| Chunk 00_declaration \| Statement 00_declaration:chunk_text_01; /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_view.sql \| Lines 1-17 \| Chunk 00_declaration \| Statement 00_declaration:embedded_01_02 | 00_declaration:declaration | table_operations[0]; table_operations[1]; table_operations[2]; tables_read[0]: LOAN_ACCOUNT \| READ \| target: la.account_id, la.customer_id, la.overdue_days, la.outstanding_amount, la.asset_classification, np.provision_amount, np.classification_date \| WHERE: la…; tables_read[1]: NPA_PROVISION \| READ \| target: la.account_id, la.customer_id, la.overdue_days, la.outstanding_amount, la.asset_classification, np.provision_amount, np.classification_date \| WHERE: l… | Verified |
| 2 | Select active NPA provisions (rule_dc9c84c7207b) | la.asset_classification <> 'STANDARD' AND np.classification_date = (SELECT MAX(classification_date) FROM NPA_PROVISION WHERE account_id = la.account_id) | /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_view.sql \| Lines 2-18 \| Chunk 00_declaration \| Statement 00_declaration:chunk_text_01; /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_view.sql \| Lines 1-17 \| Chunk 00_declaration \| Statement 00_declaration:embedded_01_02 | 00_declaration:declaration | table_operations[0]; table_operations[1]; table_operations[2]; tables_read[0]: LOAN_ACCOUNT \| READ \| target: la.account_id, la.customer_id, la.overdue_days, la.outstanding_amount, la.asset_classification, np.provision_amount, np.classification_date \| WHERE: la…; tables_read[1]: NPA_PROVISION \| READ \| target: la.account_id, la.customer_id, la.overdue_days, la.outstanding_amount, la.asset_classification, np.provision_amount, np.classification_date \| WHERE: l… | Verified |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 2
- **By rule type:** explicit = 1, inferred = 1
- **By validation status:** verified = 2

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 0
- **Deterministic-only facts:** 0
- **LLM-only claims:** 0
- **Conflicts:** 4
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_read (`recon_cd0b94da45a9`): 00_declaration
- `CONFLICT` tables_read (`recon_cd0b94da45a9`): 00_declaration
- `CONFLICT` rule (`recon_961c8326f63a`): rule_6bf42c965979, 00_declaration, 00_declaration:chunk_text_01;00_declaration:embedded_01_02 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_07552f2d06db`): rule_dc9c84c7207b, 00_declaration, 00_declaration:chunk_text_01;00_declaration:embedded_01_02 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 26/100
- **Statement coverage:** 2 / 2 (100.0%)
- **Rule grounding coverage:** 2 / 2 (100.0%)
- **Conflicts:** 4
- **Contradictions:** 6
- **Review required items:** 10
- **Review required:** Yes

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule_6bf42c965979`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Condition Conflict on `rule_6bf42c965979`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule_dc9c84c7207b`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

None.
