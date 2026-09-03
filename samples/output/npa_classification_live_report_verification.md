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
| Prompt Version | `5c8879cd38c3a577` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `Oracle` |
| Dialect Confidence | `High` |
| Source Hash | `41d0fce2906ef64c317d5c5bee63a55364c0d1776dad77eb71446f8273d1ab79` |
| Configuration Version | `800b96eecc6bffb2` |
| Run Timestamp | `2026-09-03T04:26:26.575796+00:00` |
| Object ID | `obj_4cb17b45df7c` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_f193f7358dbf` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `17661` |
| Completion Tokens | `2755` |
| Total Tokens | `20416` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 3 | 3 | 0 | 9949 | available |
| synthesis | 1 | 1 | 0 | 10467 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify account as Standard [LLM_ONLY] (`rule_c400c3889915`) | `v_classification` | Classifies the account as Standard if the overdue days are less than or equal to 90. |
| 🟠 2 | Classify account as Doubtful3 or Loss [LLM_ONLY] (`rule_0d5398b59bbc`) | `v_classification` | Classify account as Doubtful3 or Loss. |
| 🟠 3 | Classify account as Doubtful3 or Loss [LLM_ONLY] (`rule_bb6ab97a1bd5`) | `v_classification` | Classify account as Doubtful3 or Loss. |
| 🟠 4 | Classify account as Doubtful3 or Loss [LLM_ONLY] (`rule_2b1bad8e33f5`) | `v_classification` | Classify account as Doubtful3 or Loss. |
| 🟠 5 | Classify account as Doubtful3 or Loss [UNRESOLVED] (`rule_936888682bd8`) | `Not specified` | Classify account as Doubtful3 or Loss. |
| 🔴 6 | Update asset_classification, last_classified_date [CONFLICT] (`rule_4724b9f92868`) | `v_classification` | The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_account_id. |
| 🟠 7 | Classify account as Doubtful3 or Loss [LLM_ONLY] (`rule_3f26dd8477e0`) | `v_classification` | Set LOSS or DOUBTFUL3 based on doubtful_since |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify account as Standard (rule_c400c3889915) | v_overdue_days <= 90 | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_classification.sql \| Lines 11-53 \| Chunk 01_main_body | 01_main_body:main_body | conditions[0]: v_overdue_days <= 90 -> v_classification := 'STANDARD'; v_provision_pct := 0.40;; decision_chains[0] | Verified |
| 2 | Classify account as Doubtful3 or Loss (rule_0d5398b59bbc) | v_overdue_days <= 90; v_classification := 'STANDARD'; v_provision_pct := 0.40; | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_classification.sql \| Lines 11-53 \| Chunk 01_main_body | 01_main_body:main_body | conditions[0]: v_overdue_days <= 90 -> v_classification := 'STANDARD'; v_provision_pct := 0.40;; decision_chains[0] | Verified |
| 3 | Classify account as Doubtful3 or Loss (rule_bb6ab97a1bd5) | v_overdue_days BETWEEN 91 AND 365; v_classification := 'SUBSTANDARD'; v_provision_pct := 15; | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_classification.sql \| Lines 11-53 \| Chunk 01_main_body | 01_main_body:main_body | conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15;; decision_chains[0] | Verified |
| 4 | Classify account as Doubtful3 or Loss (rule_2b1bad8e33f5) | v_overdue_days BETWEEN 366 AND 1095; IF v_doubtful_since <= 365 THEN v_classification := 'DOUBTFUL1'; v_provision_pct := 25; ELSE v_classification := 'DOUBTFUL2'; v_provision_pct := 40; END IF; | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_classification.sql \| Lines 11-53 \| Chunk 01_main_body | 01_main_body:main_body | conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> IF v_doubtful_since <= 365 THEN v_classification := 'DOUBTFUL1'; v_provision_pct := 25; ELSE v_classification := 'DOUBTFUL2'; v_provision_pct :=…; decision_chains[0] | Verified |
| 5 | Classify account as Doubtful3 or Loss (rule_936888682bd8) | calculated_date | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_classification.sql \| Lines 11-53 \| Chunk 01_main_body \| Statement 01_main_body:chunk_text_20; /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_classification.sql \| Lines 39-40 \| Chunk 01_main_body \| Statement 01_main_body:embedded_03_24 | 01_main_body:main_body | table_operations[2]; table_operations[6]; tables_written[1]: NPA_PROVISION \| INSERT \| target: account_id, classification, provision_amount, calculated_date \| WHERE: None | Verified |
| 6 | Update asset_classification, last_classified_date (rule_4724b9f92868) | UPDATE LOAN_ACCOUNT SET asset_classification = v_classification, last_classified_date = SYSDATE WHERE account_id = p_account_id;; account_id = p_account_id; [{"column": "asset_classification", "expression": "v_classification"}, {"column": "last_classified_dat… | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_classification.sql \| Lines 11-53 \| Chunk 01_main_body \| Statement 01_main_body:chunk_text_19; /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_classification.sql \| Lines 34-37 \| Chunk 01_main_body \| Statement 01_main_body:embedded_02_23 (+2 more span(s)) | 01_main_body:main_body | table_operations[1]; table_operations[5]; tables_read[1]: LOAN_ACCOUNT \| READ \| target: overdue_days, outstanding_amount, unsecured_amount, doubtful_since_days INTO v_overdue_days, v_outstanding_amt, v_unsecured_amt, v_doubtful_since \| WHE…; tables_read[3]: LOAN_ACCOUNT \| READ \| target: asset_classification, last_classified_date \| WHERE: account_id = p_account_id;; tables_written[0]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification, last_classified_date \| WHERE: account_id = p_account_id; tables_written[3]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification, last_classified_date \| WHERE: account_id = p_account_id;; _(+4 more instance(s) not shown)_ | Needs Review |
| 7 | Classify account as Doubtful3 or Loss (rule_3f26dd8477e0) | v_overdue_days > 1095 | Not cited | Not cited | Not cited | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** explicit = 3, inferred = 4
- **By validation status:** insufficient_evidence = 1, unverified = 1, verified = 5

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 6
- **Deterministic-only facts:** 4
- **LLM-only claims:** 5
- **Conflicts:** 1
- **Unresolved items:** 1
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_49e74e820d1c`): rule_c400c3889915, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_e172fa2cf25e`): rule_0d5398b59bbc, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_30c104434df7`): rule_3f26dd8477e0 - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_53becc5ec3dd`): rule_bb6ab97a1bd5, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_f28392044e6c`): rule_2b1bad8e33f5, 01_main_body - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 25/100
- **Statement coverage:** 12 / 41 (29.3%)
- **Rule grounding coverage:** 2 / 7 (28.6%)
- **Conflicts:** 1
- **Contradictions:** 2
- **Review required items:** 9
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `rule_4724b9f92868`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Outcome Conflict on `rule_4724b9f92868`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: v_overdue_days > 1095
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "asset_classification", "expression": "v_classification"}, {"column": "last_classified_date", "expression": "SYSDATE"}]
