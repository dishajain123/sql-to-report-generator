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
| Prompt Version | `dde4a0b3fc523696` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `Oracle` |
| Dialect Confidence | `High` |
| Source Hash | `41d0fce2906ef64c317d5c5bee63a55364c0d1776dad77eb71446f8273d1ab79` |
| Configuration Version | `61559d31b55e1090` |
| Run Timestamp | `2026-09-03T11:08:20.737166+00:00` |
| Object ID | `obj_4cb17b45df7c` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_4e94e8b7350d` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `17686` |
| Completion Tokens | `3465` |
| Total Tokens | `21151` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 3 | 3 | 0 | 9949 | available |
| synthesis | 1 | 1 | 0 | 11202 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify account as Standard [LLM_ONLY] (`rule_972ba54010bc`) | `v_classification` | Sets the account's asset classification to Standard if overdue days are 90 or less. |
| 🟠 2 | Classify account as Standard [UNRESOLVED] (`rule_bbb97a97f05e`) | `Not specified` | Classify account as Standard. |
| 🔴 3 | Update asset_classification, last_classified_date [CONFLICT] (`rule_4724b9f92868`) | `v_classification` | The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_account_id. |
| 🟠 4 | Assign v_classification as STANDARD [LLM_ONLY] (`rule_c035ac83eff5`) | `v_classification` | Assigns v_classification the value STANDARD when the source condition is v_overdue_days <= 90. |
| 🟠 5 | Assign v_classification as SUBSTANDARD [LLM_ONLY] (`rule_bde065ae696a`) | `v_classification` | Assigns v_classification the value SUBSTANDARD when the source condition is v_overdue_days BETWEEN 91 AND 365. |
| 🟠 6 | Assign v_classification as DOUBTFUL1 [LLM_ONLY] (`rule_086c128bd92b`) | `v_classification` | Assigns v_classification the value DOUBTFUL1 when the source condition is v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365. |
| 🟠 7 | Assign v_classification as DOUBTFUL2 [LLM_ONLY] (`rule_f647e71db13b`) | `v_classification` | Assigns v_classification the value DOUBTFUL2 when the source condition is v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since <=… |
| 🟠 8 | Assign v_classification as LOSS [LLM_ONLY] (`rule_8ae1fa411eba`) | `v_classification` | Assigns v_classification the value LOSS when the source condition is ELSE AND v_doubtful_since > 1095. |
| 🟠 9 | Assign v_classification as DOUBTFUL3 [LLM_ONLY] (`rule_68870c9a21f0`) | `v_classification` | Assigns v_classification the value DOUBTFUL3 when the source condition is ELSE AND NOT (v_doubtful_since > 1095). |
| 🟠 10 | Classify account as Loss [LLM_ONLY] (`rule_a36229d75e93`) | `v_classification` | Set LOSS or DOUBTFUL3 based on doubtful_since |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify account as Standard (rule_972ba54010bc) | v_overdue_days <= 90; v_overdue_days <= 90 -> STANDARD; v_overdue_days BETWEEN 91 AND 365 -> SUBSTANDARD; v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365 -> DOUBTFUL1; v_overdue_days BETWEEN 366 AND 1095 AND ELSE -> DOUBTFUL2; ELSE AND v_doubt… | /tmp/tmp0l6p61z_.sql \| Lines 11-53 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[0]: v_overdue_days <= 90 -> v_classification := 'STANDARD'; v_provision_pct := 0.40;; decision_chains[0] | Needs Review |
| 2 | Classify account as Standard (rule_bbb97a97f05e) | calculated_date | /tmp/tmp0l6p61z_.sql \| Lines 11-53 \| Chunk 01_main_body \| Statement 01_main_body:chunk_text_20; /tmp/tmp0l6p61z_.sql \| Lines 39-40 \| Chunk 01_main_body \| Statement 01_main_body:embedded_03_24 | 01_main_body:main_body | table_operations[2]; table_operations[6]; tables_written[1]: NPA_PROVISION \| INSERT \| target: account_id, classification, provision_amount, calculated_date \| WHERE: None | Verified |
| 3 | Update asset_classification, last_classified_date (rule_4724b9f92868) | UPDATE LOAN_ACCOUNT SET asset_classification = v_classification, last_classified_date = SYSDATE WHERE account_id = p_account_id;; account_id = p_account_id; [{"column": "asset_classification", "expression": "v_classification"}, {"column": "last_classified_dat… | /tmp/tmp0l6p61z_.sql \| Lines 11-53 \| Chunk 01_main_body \| Statement 01_main_body:chunk_text_19; /tmp/tmp0l6p61z_.sql \| Lines 34-37 \| Chunk 01_main_body \| Statement 01_main_body:embedded_02_23 (+2 more span(s)) | 01_main_body:main_body | table_operations[1]; table_operations[5]; tables_read[1]: LOAN_ACCOUNT \| READ \| target: overdue_days, outstanding_amount, unsecured_amount, doubtful_since_days INTO v_overdue_days, v_outstanding_amt, v_unsecured_amt, v_doubtful_since \| WHE…; tables_read[3]: LOAN_ACCOUNT \| READ \| target: asset_classification, last_classified_date \| WHERE: account_id = p_account_id;; tables_written[0]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification, last_classified_date \| WHERE: account_id = p_account_id; tables_written[3]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification, last_classified_date \| WHERE: account_id = p_account_id;; _(+4 more instance(s) not shown)_ | Needs Review |
| 4 | Assign v_classification as STANDARD (rule_c035ac83eff5) | v_overdue_days <= 90; 'STANDARD' | /tmp/tmp0l6p61z_.sql \| Lines 11-53 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[0]: v_overdue_days <= 90 -> v_classification := 'STANDARD'; v_provision_pct := 0.40;; decision_chains[0]; conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15; | Verified |
| 5 | Assign v_classification as SUBSTANDARD (rule_bde065ae696a) | v_overdue_days BETWEEN 91 AND 365; 'SUBSTANDARD' | /tmp/tmp0l6p61z_.sql \| Lines 11-53 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15;; decision_chains[0] | Verified |
| 6 | Assign v_classification as DOUBTFUL1 (rule_086c128bd92b) | v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365; 'DOUBTFUL1' | source; /tmp/tmp0l6p61z_.sql \| Lines 11-53 \| Chunk 01_main_body | 01_main_body:main_body | decision_chains[0]; conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> IF v_doubtful_since <= 365 THEN v_classification := 'DOUBTFUL1'; v_provision_pct := 25; ELSE v_classification := 'DOUBTFUL2'; v_provision_pct :=… | Verified |
| 7 | Assign v_classification as DOUBTFUL2 (rule_f647e71db13b) | v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since <= 365); 'DOUBTFUL2' | source; /tmp/tmp0l6p61z_.sql \| Lines 11-53 \| Chunk 01_main_body | 01_main_body:main_body | decision_chains[0]; conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> IF v_doubtful_since <= 365 THEN v_classification := 'DOUBTFUL1'; v_provision_pct := 25; ELSE v_classification := 'DOUBTFUL2'; v_provision_pct :=… | Verified |
| 8 | Assign v_classification as LOSS (rule_8ae1fa411eba) | ELSE AND v_doubtful_since > 1095; 'LOSS' | source; /tmp/tmp0l6p61z_.sql \| Lines 11-53 \| Chunk 01_main_body | 01_main_body:main_body | decision_chains[0]; conditions[3]: v_doubtful_since > 1095 -> v_classification := 'LOSS'; v_provision_pct := 100; | Verified |
| 9 | Assign v_classification as DOUBTFUL3 (rule_68870c9a21f0) | ELSE AND NOT (v_doubtful_since > 1095); 'DOUBTFUL3' | source; /tmp/tmp0l6p61z_.sql \| Lines 11-53 \| Chunk 01_main_body | 01_main_body:main_body | decision_chains[0]; conditions[3]: v_doubtful_since > 1095 -> v_classification := 'LOSS'; v_provision_pct := 100; | Verified |
| 10 | Classify account as Loss (rule_a36229d75e93) | v_overdue_days > 1095 AND v_doubtful_since > 1095 | Not cited | Not cited | Not cited | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 10
- **By rule type:** explicit = 3, inferred = 7
- **By validation status:** insufficient_evidence = 2, unverified = 1, verified = 7

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 6
- **Deterministic-only facts:** 4
- **LLM-only claims:** 8
- **Conflicts:** 1
- **Unresolved items:** 1
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_e7a242d6001a`): rule_972ba54010bc, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_b52b5246c260`): rule_a36229d75e93 - No deterministic evidence was found for this claim.
- `UNRESOLVED` rule (`recon_3855705b9028`): rule_bbb97a97f05e, 01_main_body, 01_main_body:chunk_text_20;01_main_body:embedded_03_24 - Deterministic evidence exists, but comparison was not reliable enough for a match.
- `CONFLICT` rule (`recon_4ee80b49f770`): rule_4724b9f92868, 01_main_body, 01_main_body:chunk_text_02;01_main_body:chunk_text_19;01_main_body:embedded_01_22;01_main_body:embedded_02_23 - Deterministic evidence conflicts with the synthesized claim.
- `LLM_ONLY` rule (`recon_f43a1e9e3591`): rule_c035ac83eff5, 01_main_body - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 25/100
- **Statement coverage:** 12 / 41 (29.3%)
- **Rule grounding coverage:** 2 / 10 (20.0%)
- **Conflicts:** 1
- **Contradictions:** 2
- **Review required items:** 12
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `rule_4724b9f92868`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Outcome Conflict on `rule_4724b9f92868`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: v_overdue_days <= 90 -> STANDARD, v_overdue_days BETWEEN 91 AND 365 -> SUBSTANDARD, v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365 -> DOUBTFUL1, v_overdue_days BETWEEN 366 AND 1095 AND ELSE -> DOUBTFUL2, ELSE AND v_doubtful_since > 1095 -> LOSS, ELSE AND ELSE -> DOUBTFUL3
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: v_overdue_days > 1095 AND v_doubtful_since > 1095
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "asset_classification", "expression": "v_classification"}, {"column": "last_classified_date", "expression": "SYSDATE"}]
