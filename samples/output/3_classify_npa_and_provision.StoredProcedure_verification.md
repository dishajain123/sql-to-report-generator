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
| Run Timestamp | `2026-09-03T07:43:52.538043+00:00` |
| Object ID | `obj_228a6be8e500` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_24d401ceeef0` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `16625` |
| Completion Tokens | `2119` |
| Total Tokens | `18744` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 3 | 3 | 0 | 9120 | available |
| synthesis | 1 | 1 | 0 | 9624 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Determine v_classification from decision bands [LLM_ONLY] (`rule_a5d6ac6b4f6f`) | `v_classification` | Determines the value assigned to v_classification based on the source-defined decision bands. |
| 🔴 2 | Update asset_classification [CONFLICT] (`rule_ee855da854a4`) | `v_classification` | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |
| 🟠 3 | Assign V_PROVISION_PCT by source-defined conditions [LLM_ONLY] (`rule_4e2684c77fc0`) | `V_PROVISION_PCT` | Assigns V_PROVISION_PCT according to the ordered conditions in the source. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Determine v_classification from decision bands (rule_a5d6ac6b4f6f) | v_overdue_days <= 90; 'STANDARD'; v_overdue_days BETWEEN 91 AND 365; 'SUBSTANDARD'; v_overdue_days BETWEEN 366 AND 1095; 'DOUBTFUL1'; ELSE; 'LOSS'; v_overdue_days <= 90 -> STANDARD; v_overdue_days BETWEEN 91 AND 365 -> SUBSTANDARD; v_overdue_days BETWEEN 366… | /tmp/tmpyt56hrt4.sql \| Lines 6-34 \| Chunk 01_main_body; source \| Lines 12-24 | 01_main_body:main_body | conditions[0]: v_overdue_days <= 90 -> v_classification := 'STANDARD'; v_provision_pct := 0.40;; decision_chains[0]; conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15;; conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> v_classification := 'DOUBTFUL1'; v_provision_pct := 25;; conditions[3]: ELSE -> v_classification := 'LOSS'; v_provision_pct := 100; | Needs Review |
| 2 | Update asset_classification (rule_ee855da854a4) | UPDATE LOAN_ACCOUNT SET asset_classification = v_classification WHERE account_id = p_account_id;; account_id = p_account_id; [{"column": "asset_classification", "expression": "v_classification"}] | /tmp/tmpyt56hrt4.sql \| Lines 6-34 \| Chunk 01_main_body \| Statement 01_main_body:chunk_text_12; /tmp/tmpyt56hrt4.sql \| Lines 21-23 \| Chunk 01_main_body \| Statement 01_main_body:embedded_02_16 (+2 more span(s)) | 01_main_body:main_body | table_operations[1]; table_operations[5]; tables_read[1]: LOAN_ACCOUNT \| READ \| target: overdue_days, outstanding_amount INTO v_overdue_days, v_outstanding \| WHERE: account_id = p_account_id;; tables_read[3]: LOAN_ACCOUNT \| READ \| target: asset_classification \| WHERE: account_id = p_account_id;; tables_written[0]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification \| WHERE: account_id = p_account_id; tables_written[3]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification \| WHERE: account_id = p_account_id;; _(+4 more instance(s) not shown)_ | Needs Review |
| 3 | Assign V_PROVISION_PCT by source-defined conditions (rule_4e2684c77fc0) | v_overdue_days <= 90 -> 0.40; v_overdue_days BETWEEN 91 AND 365 -> 15; v_overdue_days BETWEEN 366 AND 1095 -> 25; ELSE -> 100 | Not cited | Not cited | Not cited | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 3
- **By rule type:** explicit = 3
- **By validation status:** insufficient_evidence = 2, unverified = 1

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 4
- **Deterministic-only facts:** 2
- **LLM-only claims:** 2
- **Conflicts:** 1
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_ce00803a9eb9`): rule_a5d6ac6b4f6f, 01_main_body - No deterministic evidence was found for this claim.
- `CONFLICT` rule (`recon_e2584055b614`): rule_ee855da854a4, 01_main_body, 01_main_body:chunk_text_02;01_main_body:chunk_text_12;01_main_body:embedded_01_15;01_main_body:embedded_02_16 - Deterministic evidence conflicts with the synthesized claim.
- `LLM_ONLY` rule (`recon_1a65cfd7ffcb`): rule_4e2684c77fc0 - No deterministic evidence was found for this claim.
- `DETERMINISTIC_ONLY` coverage (`recon_3a0e9ba28a7e`): 02_exception, 02_exception:chunk_text_02 - Deterministic evidence is present in the source but no synthesized rule referenced it.
- `DETERMINISTIC_ONLY` coverage (`recon_3a0e9ba28a7e`): 02_exception, 02_exception:embedded_01_05 - Deterministic evidence is present in the source but no synthesized rule referenced it.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 32/100
- **Statement coverage:** 10 / 27 (37.0%)
- **Rule grounding coverage:** 1 / 3 (33.3%)
- **Conflicts:** 1
- **Contradictions:** 2
- **Review required items:** 5
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `rule_ee855da854a4`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Outcome Conflict on `rule_ee855da854a4`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: v_overdue_days <= 90 -> STANDARD, v_overdue_days BETWEEN 91 AND 365 -> SUBSTANDARD, v_overdue_days BETWEEN 366 AND 1095 -> DOUBTFUL1, ELSE -> LOSS
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "asset_classification", "expression": "v_classification"}]
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: v_overdue_days <= 90 -> 0.40, v_overdue_days BETWEEN 91 AND 365 -> 15, v_overdue_days BETWEEN 366 AND 1095 -> 25, ELSE -> 100
