# ContExcsSinceDtDebit — Verification & Traceability

> Companion artifact to `PRO.ContExcsSinceDtDebit.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_8d12902a3a79` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `1c8e103a89db04c2` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `c343056b9e4f4c719f1e2cfd7e4b33128afb4bef67ff82a67ef76d11e4197d88` |
| Configuration Version | `646dbbaf5be7f3a0` |
| Run Timestamp | `2026-09-04T12:24:21.205265+00:00` |
| Object ID | `obj_8d12902a3a79` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_9953610a0fb1` |
| Total LLM Calls | `2` |
| Successful Calls | `2` |
| Failed Calls | `0` |
| Prompt Tokens | `11760` |
| Completion Tokens | `446` |
| Total Tokens | `12206` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 3679 | available |
| synthesis | 1 | 1 | 0 | 8527 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | No active operations [LLM_ONLY] (`rule_01`) | `Not specified` | The procedure is currently empty and does not perform any operations. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | No active operations (rule_01) | The procedure contains commented-out code that suggests it was intended to perform certain operations, but the active code is empty. | Not cited | Not cited | Not cited | Verified |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 1
- **By rule type:** explicit = 1
- **By validation status:** verified = 1

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 0
- **Deterministic-only facts:** 0
- **LLM-only claims:** 1
- **Conflicts:** 0
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` rule (`recon_7ed8f0ebf91a`): no direct provenance - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 83/100
- **Statement coverage:** 0 / 1 (0.0%)
- **Rule grounding coverage:** 0 / 1 (0.0%)
- **Conflicts:** 0
- **Contradictions:** 0
- **Review required items:** 1
- **Review required:** Yes

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Commented-out logic found in source (5 block(s)) and excluded from extraction - not included in the business rules.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: The procedure contains commented-out code that suggests it was intended to perform certain operations, but the active code is empty.
