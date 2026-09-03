# VW Provision Summary — Verification & Traceability

> Companion artifact to `VW_PROVISION_SUMMARY.View_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_4109f3c95559` |
| Raw technical object name (from source) | `VW_PROVISION_SUMMARY` |

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
| Source Hash | `741b6edea8524feb4f1a93957203112977c622886d70f73db4d8bc8c555fd41a` |
| Configuration Version | `5da7e25e83100117` |
| Run Timestamp | `2026-09-03T04:26:51.932860+00:00` |
| Object ID | `obj_4109f3c95559` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_41cf2e914f0f` |
| Total LLM Calls | `2` |
| Successful Calls | `2` |
| Failed Calls | `0` |
| Prompt Tokens | `10414` |
| Completion Tokens | `1012` |
| Total Tokens | `11426` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 3098 | available |
| synthesis | 1 | 1 | 0 | 8328 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Filter non-null asset classification [CONFLICT] (`rule_de46642045fb`) | `v_classification` | Ensures that only accounts with a non-null asset classification are included in the summary. |
| 🔴 2 | Filter most recent provisioning date [CONFLICT] (`rule_494e6dbcbfa7`) | `account_id` | Ensures that only the most recent provisioning date for each account is included in the summary. |
| 🔴 3 | Filter non-null asset classification [CONFLICT] (`rule_d8b1a409e836`) | `account_id` | Filter non-null asset classification. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Filter non-null asset classification (rule_de46642045fb) | la.asset_classification IS NOT NULL | /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_summary_view.sql \| Lines 2-17 \| Chunk 00_declaration; /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_summary_view.sql \| Lines 2-17 \| Chunk 00_declaration \| Statement 00_declaration:chunk_text_01 (+1 more span(s)) | 00_declaration:declaration | conditions[0]: la.asset_classification IS NOT NULL -> outcome not specified; table_operations[0]; table_operations[1]; table_operations[2]; tables_read[0]: LOAN_ACCOUNT \| READ \| target: la.branch_code, la.asset_classification, COUNT(*) AS account_count, SUM(la.outstanding_amount) AS total_outstanding, SUM(np.provision_amount) AS total_…; tables_read[1]: NPA_PROVISION \| READ \| target: la.branch_code, la.asset_classification, COUNT(*) AS account_count, SUM(la.outstanding_amount) AS total_outstanding, SUM(np.provision_amount) AS total… | Verified |
| 2 | Filter most recent provisioning date (rule_494e6dbcbfa7) | np.calculated_date = (SELECT MAX(np2.calculated_date) FROM NPA_PROVISION np2 WHERE np2.account_id = la.account_id) | /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_summary_view.sql \| Lines 2-17 \| Chunk 00_declaration; /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_summary_view.sql \| Lines 2-17 \| Chunk 00_declaration \| Statement 00_declaration:chunk_text_01 (+1 more span(s)) | 00_declaration:declaration | conditions[1]: np.calculated_date = (SELECT MAX(np2.calculated_date) FROM NPA_PROVISION np2 WHERE np2.account_id = la.account_id) -> outcome not specified; table_operations[0]; table_operations[1]; table_operations[2]; tables_read[0]: LOAN_ACCOUNT \| READ \| target: la.branch_code, la.asset_classification, COUNT(*) AS account_count, SUM(la.outstanding_amount) AS total_outstanding, SUM(np.provision_amount) AS total_…; tables_read[1]: NPA_PROVISION \| READ \| target: la.branch_code, la.asset_classification, COUNT(*) AS account_count, SUM(la.outstanding_amount) AS total_outstanding, SUM(np.provision_amount) AS total… | Verified |
| 3 | Filter non-null asset classification (rule_d8b1a409e836) | NOT la.asset_classification IS NULL AND np.calculated_date = (SELECT MAX(np2.calculated_date) FROM NPA_PROVISION np2 WHERE np2.account_id = la.account_id) | /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_summary_view.sql \| Lines 2-17 \| Chunk 00_declaration; /Users/dishajain/Desktop/logic_rules_extractor/samples/provisioning_summary_view.sql \| Lines 2-17 \| Chunk 00_declaration \| Statement 00_declaration:chunk_text_01 | 00_declaration:declaration | conditions[1]: np.calculated_date = (SELECT MAX(np2.calculated_date) FROM NPA_PROVISION np2 WHERE np2.account_id = la.account_id) -> outcome not specified; table_operations[0]; table_operations[1]; tables_read[0]: LOAN_ACCOUNT \| READ \| target: la.branch_code, la.asset_classification, COUNT(*) AS account_count, SUM(la.outstanding_amount) AS total_outstanding, SUM(np.provision_amount) AS total_…; tables_read[1]: NPA_PROVISION \| READ \| target: la.branch_code, la.asset_classification, COUNT(*) AS account_count, SUM(la.outstanding_amount) AS total_outstanding, SUM(np.provision_amount) AS total… | Verified |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 3
- **By rule type:** explicit = 2, inferred = 1
- **By validation status:** verified = 3

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 0
- **Deterministic-only facts:** 0
- **LLM-only claims:** 0
- **Conflicts:** 5
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_read (`recon_c6f8e898cc1f`): 00_declaration
- `CONFLICT` tables_read (`recon_c6f8e898cc1f`): 00_declaration
- `CONFLICT` rule (`recon_b94326aa14ed`): rule_de46642045fb, 00_declaration, 00_declaration:chunk_text_01;00_declaration:embedded_01_02 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_502bcf84f897`): rule_494e6dbcbfa7, 00_declaration, 00_declaration:chunk_text_01;00_declaration:embedded_01_02 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_7a7b351fe950`): rule_d8b1a409e836, 00_declaration, 00_declaration:chunk_text_01 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 20/100
- **Statement coverage:** 2 / 2 (100.0%)
- **Rule grounding coverage:** 3 / 3 (100.0%)
- **Conflicts:** 5
- **Contradictions:** 8
- **Review required items:** 13
- **Review required:** Yes

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule_de46642045fb`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Condition Conflict on `rule_de46642045fb`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule_494e6dbcbfa7`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

None.
