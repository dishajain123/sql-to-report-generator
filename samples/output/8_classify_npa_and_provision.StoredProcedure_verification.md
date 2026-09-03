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
| Run Timestamp | `2026-09-03T11:46:22.035251+00:00` |
| Object ID | `obj_228a6be8e500` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_51a93d372f13` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `16579` |
| Completion Tokens | `2187` |
| Total Tokens | `18766` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 3 | 3 | 0 | 9122 | available |
| synthesis | 1 | 1 | 0 | 9644 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Assign v_classification as STANDARD [LLM_ONLY] (`rule_c035ac83eff5`) | `v_classification` | Assigns v_classification the value STANDARD when the source condition is v_overdue_days <= 90. |
| 🟠 2 | Assign v_classification as SUBSTANDARD [LLM_ONLY] (`rule_bde065ae696a`) | `v_classification` | Assigns v_classification the value SUBSTANDARD when the source condition is v_overdue_days BETWEEN 91 AND 365. |
| 🟠 3 | Assign v_classification as DOUBTFUL1 [LLM_ONLY] (`rule_272eea4fb2f6`) | `v_classification` | Assigns v_classification the value DOUBTFUL1 when the source condition is v_overdue_days BETWEEN 366 AND 1095. |
| 🟠 4 | Assign v_classification as LOSS [LLM_ONLY] (`rule_8cbfd7c45cd1`) | `v_classification` | Assigns v_classification the value LOSS when the source condition is NOT (v_overdue_days <= 90) AND NOT (v_overdue_days BETWEEN 91 AND 365)… |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Assign v_classification as STANDARD (rule_c035ac83eff5) | v_overdue_days <= 90; 'STANDARD' | /tmp/tmpssohpfvt.sql \| Lines 6-34 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[0]: v_overdue_days <= 90 -> v_classification := 'STANDARD'; v_provision_pct := 0.40;; decision_chains[0]; conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15; | Verified |
| 2 | Assign v_classification as SUBSTANDARD (rule_bde065ae696a) | v_overdue_days BETWEEN 91 AND 365; 'SUBSTANDARD' | /tmp/tmpssohpfvt.sql \| Lines 6-34 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15;; decision_chains[0] | Verified |
| 3 | Assign v_classification as DOUBTFUL1 (rule_272eea4fb2f6) | v_overdue_days BETWEEN 366 AND 1095; 'DOUBTFUL1' | /tmp/tmpssohpfvt.sql \| Lines 6-34 \| Chunk 01_main_body; source | 01_main_body:main_body | conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> v_classification := 'DOUBTFUL1'; v_provision_pct := 25;; decision_chains[0] | Verified |
| 4 | Assign v_classification as LOSS (rule_8cbfd7c45cd1) | NOT (v_overdue_days <= 90) AND NOT (v_overdue_days BETWEEN 91 AND 365) AND NOT (v_overdue_days BETWEEN 366 AND 1095); 'LOSS' | source; /tmp/tmpssohpfvt.sql \| Lines 6-34 \| Chunk 01_main_body | 01_main_body:main_body | decision_chains[0]; conditions[3]: ELSE -> v_classification := 'LOSS'; v_provision_pct := 100; | Verified |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 4
- **By rule type:** explicit = 4
- **By validation status:** verified = 4

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 4
- **Deterministic-only facts:** 2
- **LLM-only claims:** 4
- **Conflicts:** 0
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_db3ceb9d9abe`): rule_c035ac83eff5, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_af1e2e080b0e`): rule_bde065ae696a, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_ced412ad9590`): rule_272eea4fb2f6, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_322c9638d667`): rule_8cbfd7c45cd1, 01_main_body - No deterministic evidence was found for this claim.
- `DETERMINISTIC_ONLY` coverage (`recon_3a0e9ba28a7e`): 02_exception, 02_exception:chunk_text_02 - Deterministic evidence is present in the source but no synthesized rule referenced it.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 71/100
- **Statement coverage:** 10 / 27 (37.0%)
- **Rule grounding coverage:** 0 / 4 (0.0%)
- **Conflicts:** 0
- **Contradictions:** 0
- **Review required items:** 4
- **Review required:** Yes

Statement parse success is below the preferred threshold.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

None.
