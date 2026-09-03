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
| Prompt Version | `dde4a0b3fc523696` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `Oracle` |
| Dialect Confidence | `High` |
| Source Hash | `6f18ccc6f88d9cbbdb44a1c2547772b48b88de1cb9d1e2482715b235da70ea24` |
| Configuration Version | `61559d31b55e1090` |
| Run Timestamp | `2026-09-03T11:36:05.988683+00:00` |
| Object ID | `obj_228a6be8e500` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_3dd708f9f0eb` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `16595` |
| Completion Tokens | `2148` |
| Total Tokens | `18743` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 3 | 3 | 0 | 9120 | available |
| synthesis | 1 | 1 | 0 | 9623 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify account as Doubtful1 [LLM_ONLY] (`rule_c7d90c319c1b`) | `v_classification` | Classifies the account as Doubtful1 if the overdue days are between 366 and 1095. |
| 🟠 2 | Classify account as Loss [LLM_ONLY] (`rule_42562c0670f3`) | `v_classification` | Classifies the account as Loss if the overdue days are more than 1095. |
| 🔴 3 | Update asset_classification [CONFLICT] (`rule_ee855da854a4`) | `v_classification` | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |
| 🟠 4 | Assign v_classification as STANDARD [LLM_ONLY] (`rule_c035ac83eff5`) | `v_classification` | Assigns v_classification the value STANDARD when the source condition is v_overdue_days <= 90. |
| 🟠 5 | Assign v_classification as SUBSTANDARD [LLM_ONLY] (`rule_bde065ae696a`) | `v_classification` | Assigns v_classification the value SUBSTANDARD when the source condition is v_overdue_days BETWEEN 91 AND 365. |
| 🟠 6 | Assign v_classification as DOUBTFUL1 [LLM_ONLY] (`rule_272eea4fb2f6`) | `v_classification` | Assigns v_classification the value DOUBTFUL1 when the source condition is v_overdue_days BETWEEN 366 AND 1095. |
| 🟠 7 | Assign v_classification as LOSS [LLM_ONLY] (`rule_8cbfd7c45cd1`) | `v_classification` | Assigns v_classification the value LOSS when the source condition is NOT (v_overdue_days <= 90) AND NOT (v_overdue_days BETWEEN 91 AND 365)… |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify account as Doubtful1 (rule_c7d90c319c1b) | v_overdue_days BETWEEN 366 AND 1095; v_overdue_days <= 90 -> STANDARD; v_overdue_days BETWEEN 91 AND 365 -> SUBSTANDARD; v_overdue_days BETWEEN 366 AND 1095 -> DOUBTFUL1; ELSE -> LOSS | /tmp/tmpjxn3e975.sql \| Lines 6-34 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> v_classification := 'DOUBTFUL1'; v_provision_pct := 25;; decision_chains[0] | Needs Review |
| 2 | Classify account as Loss (rule_42562c0670f3) | ELSE | /tmp/tmpjxn3e975.sql \| Lines 6-34 \| Chunk 01_main_body | 01_main_body:main_body | conditions[3]: ELSE -> v_classification := 'LOSS'; v_provision_pct := 100; | Verified |
| 3 | Update asset_classification (rule_ee855da854a4) | UPDATE LOAN_ACCOUNT SET asset_classification = v_classification WHERE account_id = p_account_id;; account_id = p_account_id; [{"column": "asset_classification", "expression": "v_classification"}] | /tmp/tmpjxn3e975.sql \| Lines 6-34 \| Chunk 01_main_body \| Statement 01_main_body:chunk_text_12; /tmp/tmpjxn3e975.sql \| Lines 21-23 \| Chunk 01_main_body \| Statement 01_main_body:embedded_02_16 (+2 more span(s)) | 01_main_body:main_body | table_operations[1]; table_operations[5]; tables_read[1]: LOAN_ACCOUNT \| READ \| target: overdue_days, outstanding_amount INTO v_overdue_days, v_outstanding \| WHERE: account_id = p_account_id;; tables_read[3]: LOAN_ACCOUNT \| READ \| target: asset_classification \| WHERE: account_id = p_account_id;; tables_written[0]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification \| WHERE: account_id = p_account_id; tables_written[3]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification \| WHERE: account_id = p_account_id;; _(+4 more instance(s) not shown)_ | Needs Review |
| 4 | Assign v_classification as STANDARD (rule_c035ac83eff5) | v_overdue_days <= 90; 'STANDARD' | /tmp/tmpjxn3e975.sql \| Lines 6-34 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[0]: v_overdue_days <= 90 -> v_classification := 'STANDARD'; v_provision_pct := 0.40;; decision_chains[0]; conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15; | Verified |
| 5 | Assign v_classification as SUBSTANDARD (rule_bde065ae696a) | v_overdue_days BETWEEN 91 AND 365; 'SUBSTANDARD' | /tmp/tmpjxn3e975.sql \| Lines 6-34 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15;; decision_chains[0] | Verified |
| 6 | Assign v_classification as DOUBTFUL1 (rule_272eea4fb2f6) | v_overdue_days BETWEEN 366 AND 1095; 'DOUBTFUL1' | /tmp/tmpjxn3e975.sql \| Lines 6-34 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> v_classification := 'DOUBTFUL1'; v_provision_pct := 25;; decision_chains[0] | Verified |
| 7 | Assign v_classification as LOSS (rule_8cbfd7c45cd1) | NOT (v_overdue_days <= 90) AND NOT (v_overdue_days BETWEEN 91 AND 365) AND NOT (v_overdue_days BETWEEN 366 AND 1095); 'LOSS' | source; /tmp/tmpjxn3e975.sql \| Lines 6-34 \| Chunk 01_main_body | 01_main_body:main_body | decision_chains[0]; conditions[3]: ELSE -> v_classification := 'LOSS'; v_provision_pct := 100; | Verified |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** explicit = 3, inferred = 4
- **By validation status:** insufficient_evidence = 2, verified = 5

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 4
- **Deterministic-only facts:** 2
- **LLM-only claims:** 6
- **Conflicts:** 1
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_e211385dcd6a`): rule_c7d90c319c1b, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_a365772427c0`): rule_42562c0670f3, 01_main_body - No deterministic evidence was found for this claim.
- `CONFLICT` rule (`recon_e2584055b614`): rule_ee855da854a4, 01_main_body, 01_main_body:chunk_text_02;01_main_body:chunk_text_12;01_main_body:embedded_01_15;01_main_body:embedded_02_16 - Deterministic evidence conflicts with the synthesized claim.
- `LLM_ONLY` rule (`recon_db3ceb9d9abe`): rule_c035ac83eff5, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_af1e2e080b0e`): rule_bde065ae696a, 01_main_body - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 31/100
- **Statement coverage:** 10 / 27 (37.0%)
- **Rule grounding coverage:** 1 / 7 (14.3%)
- **Conflicts:** 1
- **Contradictions:** 2
- **Review required items:** 9
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `rule_ee855da854a4`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Outcome Conflict on `rule_ee855da854a4`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: v_overdue_days <= 90 -> STANDARD, v_overdue_days BETWEEN 91 AND 365 -> SUBSTANDARD, v_overdue_days BETWEEN 366 AND 1095 -> DOUBTFUL1, ELSE -> LOSS
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "asset_classification", "expression": "v_classification"}]
