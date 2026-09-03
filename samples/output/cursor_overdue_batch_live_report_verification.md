# Anonymous Block — Verification & Traceability

> Companion artifact to `cursor_overdue_batch_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_6f5dbd97cf87` |
| Raw technical object name (from source) | `ANONYMOUS_BLOCK` |

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
| Source Hash | `678586f6e9e1c9d44b564f371c7789f4c2e2f6407c1446f6e56975ecc24720e3` |
| Configuration Version | `800b96eecc6bffb2` |
| Run Timestamp | `2026-09-03T04:26:15.319882+00:00` |
| Object ID | `obj_6f5dbd97cf87` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_082895d7693c` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `16756` |
| Completion Tokens | `1922` |
| Total Tokens | `18678` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 3 | 3 | 0 | 9442 | available |
| synthesis | 1 | 1 | 0 | 9236 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Classify account as Substandard [LLM_ONLY] (`rule_ef7eb9746503`) | `v_classification` | Classify account as Substandard. |
| 🟢 2 | Calculate provisioning amount [MATCHED] (`rule_b2164412753a`) | `provision_amount` | Calculates the provisioning amount based on the outstanding amount and provisioning percentage. |
| 🟠 3 | Classify account as Substandard [LLM_ONLY] (`rule_432005a3954d`) | `v_classification` | Classify account as Substandard. |
| 🟠 4 | Classify account as Substandard [LLM_ONLY] (`rule_e6327db9b799`) | `v_classification` | Classify account as Substandard. |
| 🔴 5 | Classify account as Substandard [CONFLICT] (`rule_5ea3c6d3e252`) | `v_classification` | Classify account as Substandard. |
| 🔴 6 | Update asset_classification [CONFLICT] (`rule_48146a86d76b`) | `v_classification` | The procedure sets asset_classification to the source-defined value when account_id = rec.account_id. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Classify account as Substandard (rule_ef7eb9746503) | rec.overdue_days BETWEEN 91 AND 365 | /Users/dishajain/Desktop/logic_rules_extractor/samples/cursor_overdue_batch.sql \| Lines 10-39 \| Chunk 01_main_body | 01_main_body:main_body | conditions[0]: rec.overdue_days BETWEEN 91 AND 365 -> v_new_classification := 'SUBSTANDARD'; v_provision_pct := 15;; decision_chains[0] | Verified |
| 2 | Calculate provisioning amount (rule_b2164412753a) | rec.outstanding_amount * v_provision_pct / 100 | /Users/dishajain/Desktop/logic_rules_extractor/samples/cursor_overdue_batch.sql \| Lines 10-39 \| Chunk 01_main_body \| Statement 01_main_body:chunk_text_09; /Users/dishajain/Desktop/logic_rules_extractor/samples/cursor_overdue_batch.sql \| Lines 18-26 \| Chunk 01_main_body \| Statement 01_main_body:embedded_02_13 (+1 more span(s)) | 01_main_body:main_body | table_operations[3]; table_operations[6]; tables_read[3]: LOAN_ACCOUNT \| READ \| target: asset_classification \| WHERE: account_id = rec.account_id; tables_read[5]: LOAN_ACCOUNT \| READ \| target: asset_classification \| WHERE: account_id = rec.account_id;; tables_written[1]: NPA_PROVISION \| MERGE \| target: np.account_id, src.account_id, rec.account_id, provision_amount, classification_date, account_id, rec.outstanding_amount, v_provision_pct \| WHERE:…; calculations[0]: metric not specified \| explanation not specified | Verified |
| 3 | Classify account as Substandard (rule_432005a3954d) | rec.overdue_days BETWEEN 91 AND 365; v_new_classification := 'SUBSTANDARD'; v_provision_pct := 15; | /Users/dishajain/Desktop/logic_rules_extractor/samples/cursor_overdue_batch.sql \| Lines 10-39 \| Chunk 01_main_body | 01_main_body:main_body | conditions[0]: rec.overdue_days BETWEEN 91 AND 365 -> v_new_classification := 'SUBSTANDARD'; v_provision_pct := 15;; decision_chains[0] | Verified |
| 4 | Classify account as Substandard (rule_e6327db9b799) | rec.overdue_days BETWEEN 366 AND 1095; v_new_classification := 'DOUBTFUL1'; v_provision_pct := 25; | /Users/dishajain/Desktop/logic_rules_extractor/samples/cursor_overdue_batch.sql \| Lines 10-39 \| Chunk 01_main_body | 01_main_body:main_body | conditions[1]: rec.overdue_days BETWEEN 366 AND 1095 -> v_new_classification := 'DOUBTFUL1'; v_provision_pct := 25;; decision_chains[0] | Verified |
| 5 | Classify account as Substandard (rule_5ea3c6d3e252) | overdue_days > 90 AND asset_classification = 'STANDARD' | /Users/dishajain/Desktop/logic_rules_extractor/samples/cursor_overdue_batch.sql \| Lines 3-9 \| Chunk 00_declaration \| Statement 00_declaration:chunk_text_01; /Users/dishajain/Desktop/logic_rules_extractor/samples/cursor_overdue_batch.sql \| Lines 1-4 \| Chunk 00_declaration \| Statement 00_declaration:embedded_01_04 | 00_declaration:declaration | table_operations[0]; table_operations[1]; tables_read[0]: LOAN_ACCOUNT \| READ \| target: account_id, overdue_days, outstanding_amount \| WHERE: overdue_days > 90 AND asset_classification = 'STANDARD'; tables_read[1]: LOAN_ACCOUNT \| READ \| target: account_id, overdue_days, outstanding_amount \| WHERE: overdue_days > 90 AND asset_classification = 'STANDARD'; | Verified |
| 6 | Update asset_classification (rule_48146a86d76b) | UPDATE LOAN_ACCOUNT SET asset_classification = v_new_classification WHERE account_id = rec.account_id;; account_id = rec.account_id; [{"column": "asset_classification", "expression": "v_new_classification"}] | /Users/dishajain/Desktop/logic_rules_extractor/samples/cursor_overdue_batch.sql \| Lines 10-39 \| Chunk 01_main_body \| Statement 01_main_body:chunk_text_08; /Users/dishajain/Desktop/logic_rules_extractor/samples/cursor_overdue_batch.sql \| Lines 14-16 \| Chunk 01_main_body \| Statement 01_main_body:embedded_01_12 (+2 more span(s)) | 01_main_body:main_body | table_operations[2]; table_operations[5]; tables_read[2]: dual \| READ \| target: rec.account_id AS account_id \| WHERE: None; tables_read[4]: NPA_PROVISION \| READ \| target: np.account_id, src.account_id, rec.account_id, provision_amount, classification_date, account_id, rec.outstanding_amount, v_provision_pct \| WHERE: None; tables_written[0]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification \| WHERE: account_id = rec.account_id; tables_written[3]: LOAN_ACCOUNT \| UPDATE \| target: asset_classification \| WHERE: account_id = rec.account_id;; _(+5 more instance(s) not shown)_ | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 6
- **By rule type:** explicit = 3, inferred = 3
- **By validation status:** insufficient_evidence = 1, verified = 5

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 6
- **Deterministic-only facts:** 2
- **LLM-only claims:** 4
- **Conflicts:** 3
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` tables_written (`recon_e7c959a732e5`): 01_main_body
- `CONFLICT` tables_written (`recon_2727c415b827`): 01_main_body
- `LLM_ONLY` rule (`recon_18026322d830`): rule_ef7eb9746503, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_7f309a774345`): rule_432005a3954d, 01_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_7f6f71847aa0`): rule_e6327db9b799, 01_main_body - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 0/100
- **Statement coverage:** 10 / 24 (41.7%)
- **Rule grounding coverage:** 3 / 6 (50.0%)
- **Conflicts:** 3
- **Contradictions:** 5
- **Review required items:** 12
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `MEDIUM` Field Conflict on `rule_5ea3c6d3e252`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Condition Conflict on `rule_5ea3c6d3e252`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule_48146a86d76b`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Outcome Conflict on `rule_48146a86d76b`: Synthesized outcome/assignment conflicts with deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not deterministically identify the database object type from the raw source.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: [{"column": "asset_classification", "expression": "v_new_classification"}]
- Automated style check flagged possible leftover technical jargon in the synthesized output: cursor, pl/sql.
