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
| Run Timestamp | `2026-09-03T09:05:03.464398+00:00` |
| Object ID | `obj_228a6be8e500` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_ddb744890358` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `16623` |
| Completion Tokens | `2124` |
| Total Tokens | `18747` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 3 | 3 | 0 | 9122 | available |
| synthesis | 1 | 1 | 0 | 9625 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify account as Doubtful1 [LLM_ONLY] (`rule_1730b7c9812c`) | `v_classification` | Classifies the account as Doubtful1 if overdue days are between 366 and 1095. |
| 🟠 2 | Classify account as Loss [LLM_ONLY] (`rule_20e784271a9f`) | `v_classification` | Classifies the account as Loss if overdue days are more than 1095. |
| 🟠 3 | Classify account as STANDARD [LLM_ONLY] (`rule_a14e84c372ff`) | `v_classification` | Classifies the account as STANDARD when v_overdue_days <= 90. |
| 🟠 4 | Classify account as DOUBTFUL1 [LLM_ONLY] (`rule_5da6cfd5bdd3`) | `v_classification` | Classifies the account as DOUBTFUL1 when v_overdue_days BETWEEN 366 AND 1095. |
| 🟠 5 | Assign V_PROVISION_PCT by source-defined conditions [LLM_ONLY] (`rule_4e2684c77fc0`) | `V_PROVISION_PCT` | Assigns V_PROVISION_PCT according to the ordered conditions in the source. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify account as Doubtful1 (rule_1730b7c9812c) | v_overdue_days BETWEEN 366 AND 1095; v_overdue_days <= 90 -> STANDARD; v_overdue_days BETWEEN 91 AND 365 -> SUBSTANDARD; v_overdue_days BETWEEN 366 AND 1095 -> DOUBTFUL1; ELSE -> LOSS | /tmp/tmpz2xbjt_9.sql \| Lines 6-34 \| Chunk 01_main_body; source \| Lines 12-24 | 01_main_body:main_body | conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> v_classification := 'DOUBTFUL1'; v_provision_pct := 25;; decision_chains[0] | Needs Review |
| 2 | Classify account as Loss (rule_20e784271a9f) | ELSE | /tmp/tmpz2xbjt_9.sql \| Lines 6-34 \| Chunk 01_main_body; source \| Lines 12-24 | 01_main_body:main_body | conditions[3]: ELSE -> v_classification := 'LOSS'; v_provision_pct := 100;; decision_chains[0] | Verified |
| 3 | Classify account as STANDARD (rule_a14e84c372ff) | v_overdue_days <= 90; 'STANDARD' | /tmp/tmpz2xbjt_9.sql \| Lines 6-34 \| Chunk 01_main_body; source \| Lines 12-24 | 01_main_body:main_body | conditions[0]: v_overdue_days <= 90 -> v_classification := 'STANDARD'; v_provision_pct := 0.40;; decision_chains[0]; conditions[1]: v_overdue_days BETWEEN 91 AND 365 -> v_classification := 'SUBSTANDARD'; v_provision_pct := 15; | Verified |
| 4 | Classify account as DOUBTFUL1 (rule_5da6cfd5bdd3) | v_overdue_days BETWEEN 366 AND 1095; 'DOUBTFUL1' | /tmp/tmpz2xbjt_9.sql \| Lines 6-34 \| Chunk 01_main_body; source \| Lines 12-24 | 01_main_body:main_body | conditions[2]: v_overdue_days BETWEEN 366 AND 1095 -> v_classification := 'DOUBTFUL1'; v_provision_pct := 25;; decision_chains[0] | Verified |
| 5 | Assign V_PROVISION_PCT by source-defined conditions (rule_4e2684c77fc0) | v_overdue_days <= 90 -> 0.40; v_overdue_days BETWEEN 91 AND 365 -> 15; v_overdue_days BETWEEN 366 AND 1095 -> 25; ELSE -> 100 | Not cited | Not cited | Not cited | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 5
- **By rule type:** explicit = 3, inferred = 2
- **By validation status:** insufficient_evidence = 1, unverified = 1, verified = 3

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code and should be prioritized for human review before being treated as confirmed._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 4
- **Deterministic-only facts:** 2
- **LLM-only claims:** 5
- **Conflicts:** 0
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_97bb1d67cb35`): rule_1730b7c9812c, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_511bf21e5879`): rule_20e784271a9f, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_29bf54a778f0`): rule_a14e84c372ff, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_a600f485b00d`): rule_5da6cfd5bdd3, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_1a65cfd7ffcb`): rule_4e2684c77fc0 - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 71/100
- **Statement coverage:** 10 / 27 (37.0%)
- **Rule grounding coverage:** 0 / 5 (0.0%)
- **Conflicts:** 0
- **Contradictions:** 0
- **Review required items:** 5
- **Review required:** Yes

Statement parse success is below the preferred threshold.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: v_overdue_days <= 90 -> STANDARD, v_overdue_days BETWEEN 91 AND 365 -> SUBSTANDARD, v_overdue_days BETWEEN 366 AND 1095 -> DOUBTFUL1, ELSE -> LOSS
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: v_overdue_days <= 90 -> 0.40, v_overdue_days BETWEEN 91 AND 365 -> 15, v_overdue_days BETWEEN 366 AND 1095 -> 25, ELSE -> 100
