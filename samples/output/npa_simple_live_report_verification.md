# Classify Npa And Provision — Verification & Traceability

> Companion artifact to `classify_npa_and_provision.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_228a6be8e500` |
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
| Source Hash | `6f18ccc6f88d9cbbdb44a1c2547772b48b88de1cb9d1e2482715b235da70ea24` |
| Configuration Version | `800b96eecc6bffb2` |
| Run Timestamp | `2026-09-03T04:26:40.606574+00:00` |
| Object ID | `obj_228a6be8e500` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_67f238f14cfd` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `16590` |
| Completion Tokens | `2028` |
| Total Tokens | `18618` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 3 | 3 | 0 | 9120 | available |
| synthesis | 1 | 1 | 0 | 9498 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify account as Doubtful1 [LLM_ONLY] (`rule_7f9d7912234f`) | `v_classification` | Classifies the account as Doubtful1 if the overdue days are between 366 and 1095. |
| 🟠 2 | Classify account as Loss [LLM_ONLY] (`rule_39b5cb486033`) | `v_classification` | Classify account as Loss. |
| 🟠 3 | Classify account as Loss [LLM_ONLY] (`rule_29be6fa98314`) | `v_classification` | Classifies the account as Loss if the overdue days are more than 1095. |
| 🟠 4 | Classify account as Loss [LLM_ONLY] (`rule_7b1385e9b78c`) | `v_classification` | Classify account as Loss. |
| 🔴 5 | Update asset_classification [CONFLICT] (`rule_ee855da854a4`) | `v_classification` | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify account as Doubtful1 (rule_7f9d7912234f) | v_overdue_days BETWEEN 366 AND 1095 | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_simple.sql \| Lines 6-34 \| Chunk 01_main_body | 01_main_body:main_body | conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> v_classification := 'DOUBTFUL1'; v_provision_pct := 25;; decision_chains[0] | Verified |
| 2 | Classify account as Loss (rule_39b5cb486033) | v_overdue_days <= 90; v_classification := 'STANDARD'; v_provision_pct := 0.40; | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_simple.sql \| Lines 6-34 \| Chunk 01_main_body | 01_main_body:main_body | conditions[0]: v_overdue_days <= 90 -> v_classification := 'STANDARD'; v_provision_pct := 0.40;; decision_chains[0] | Verified |
| 3 | Classify account as Loss (rule_29be6fa98314) | ELSE | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_simple.sql \| Lines 6-34 \| Chunk 01_main_body | 01_main_body:main_body | conditions[3]: ELSE -> v_classification := 'LOSS'; v_provision_pct := 100;; decision_chains[0] | Verified |
| 4 | Classify account as Loss (rule_7b1385e9b78c) | v_overdue_days BETWEEN 91 AND 365; v_classification := 'SUBSTANDARD'; v_provision_pct := 15; | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_simple.sql \| Lines 6-34 \| Chunk 01_main_body | 01_main_body:main_body | conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15;; decision_chains[0] | Verified |
| 5 | Update asset_classification (rule_ee855da854a4) | UPDATE LOAN_ACCOUNT SET asset_classification = v_classification WHERE account_id = p_account_id;; account_id = p_account_id; [{"column": "asset_classification", "expression": "v_classification"}] | /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_simple.sql \| Lines 6-34 \| Chunk 01_main_body \| Statement 01_main_body:chunk_text_12; /Users/dishajain/Desktop/logic_rules_extractor/samples/npa_simple.sql \| Lines 21-23 \| Chunk 01_main_body \| Statement 01_main_body:embedded_02_16 (+2 more span(s)) | 01_main_body:main_body | table_operations[1]; table_operations[5]; tables_read[1]: LOAN_ACCOUNT \| READ \| target: overdue_days, outstanding_amount INTO v_overdue_days, v_outstanding \| WHERE: account_id = p_account_id;; tables_read[3]: LOAN_ACCOUNT \| READ \| target: asset_classification \| WHERE: account_id = p_account_id;; tables_written[0]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification \| WHERE: account_id = p_account_id; tables_written[3]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification \| WHERE: account_id = p_account_id;; _(+4 more instance(s) not shown)_ | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 5
- **By rule type:** explicit = 3, inferred = 2
- **By validation status:** insufficient_evidence = 1, verified = 4

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 4
- **Deterministic-only facts:** 2
- **LLM-only claims:** 4
- **Conflicts:** 1
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_4954dfa68d4d`): rule_7f9d7912234f, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_aedb652a55fd`): rule_39b5cb486033, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_aeb994b7a212`): rule_29be6fa98314, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_9791225a0709`): rule_7b1385e9b78c, 01_main_body - No deterministic evidence was found for this claim.
- `CONFLICT` rule (`recon_e2584055b614`): rule_ee855da854a4, 01_main_body, 01_main_body:chunk_text_02;01_main_body:chunk_text_12;01_main_body:embedded_01_15;01_main_body:embedded_02_16 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 31/100
- **Statement coverage:** 10 / 27 (37.0%)
- **Rule grounding coverage:** 1 / 5 (20.0%)
- **Conflicts:** 1
- **Contradictions:** 2
- **Review required items:** 7
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `rule_ee855da854a4`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Outcome Conflict on `rule_ee855da854a4`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "asset_classification", "expression": "v_classification"}]
