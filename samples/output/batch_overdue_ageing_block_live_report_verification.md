# Anonymous Block — Verification & Traceability

> Companion artifact to `batch_overdue_ageing_block_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_47b930359cc3` |
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
| Source Hash | `f466b0b32c9da8dea7e8e5b2f13892a4fe03f999f9656f2632242e1a71878386` |
| Configuration Version | `800b96eecc6bffb2` |
| Run Timestamp | `2026-09-03T04:25:53.530228+00:00` |
| Object ID | `obj_47b930359cc3` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_3cd21ea9ca92` |
| Total LLM Calls | `6` |
| Successful Calls | `6` |
| Failed Calls | `0` |
| Prompt Tokens | `22327` |
| Completion Tokens | `2390` |
| Total Tokens | `24717` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 5 | 5 | 0 | 14661 | available |
| synthesis | 1 | 1 | 0 | 10056 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Lock active overdue accounts [CONFLICT] (`rule_3da6586f3c38`) | `status` | Ensures that active loan accounts with overdue days greater than zero are locked for processing. |
| 🟠 2 | Update ageing summary table [MATCHED] (`rule_6a44aa750ebf`) | `ageing_bucket` | The ageing summary table is updated. |
| 🟠 3 | Increment processed account count [LLM_ONLY] (`rule_d3ffc762afc8`) | `v_processed_count` | Increments the count of processed accounts. |
| 🟠 4 | Update ageing summary table [MATCHED] (`rule_7fdba897fa92`) | `status` | The ageing summary table is updated. |
| 🟠 5 | Update ageing summary table [LLM_ONLY] (`rule_c651ce0aebb6`) | `v_ageing_bucket` | The ageing summary table is updated. |
| 🟠 6 | Update ageing summary table [LLM_ONLY] (`rule_79c805e7e9c1`) | `v_ageing_bucket` | The ageing summary table is updated. |
| 🟠 7 | Update ageing summary table [LLM_ONLY] (`rule_08fb3c59efbc`) | `v_ageing_bucket` | The ageing summary table is updated. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Lock active overdue accounts (rule_3da6586f3c38) | status = 'ACTIVE' AND overdue_days > 0 | /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 3-10 \| Chunk 00_declaration; /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 3-10 \| Chunk 00_declaration \| Statement 00_declaration:chunk_text_01 (+1 more span(s)) | 00_declaration:declaration | conditions[0]: status = 'ACTIVE' AND overdue_days > 0 -> SELECT account_id, overdue_days, outstanding_amount FROM LOAN_ACCOUNT FOR UPDATE; table_operations[0]; table_operations[1]; table_operations[2]; tables_read[0]: LOAN_ACCOUNT \| READ \| target: account_id, overdue_days, outstanding_amount \| WHERE: status = 'ACTIVE' AND overdue_days > 0; tables_read[1]: LOAN_ACCOUNT \| READ \| target: account_id, overdue_days, outstanding_amount \| WHERE: status = 'ACTIVE' AND overdue_days > 0 FOR; _(+1 more instance(s) not shown)_ | Verified |
| 2 | Update ageing summary table (rule_6a44aa750ebf) | tgt.account_id = src.account_id | /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 22-34 \| Chunk 03_main_body \| Statement 03_main_body:chunk_text_02; /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 3-11 \| Chunk 03_main_body \| Statement 03_main_body:embedded_01_04 | 03_main_body:main_body | table_operations[3]; table_operations[4]; tables_read[2]: dual \| READ \| target: rec.account_id AS account_id \| WHERE: None; tables_read[3]: OVERDUE_AGEING_SUMMARY \| READ \| target: tgt.account_id, src.account_id, rec.account_id, tgt.ageing_bucket, v_ageing_bucket, tgt.last_updated, account_id, ageing_bucket, last_updated…; tables_written[1]: OVERDUE_AGEING_SUMMARY \| MERGE \| target: tgt.account_id, src.account_id, rec.account_id, tgt.ageing_bucket, v_ageing_bucket, tgt.last_updated, account_id, ageing_bucket, last_upd… | Needs Review |
| 3 | Increment processed account count (rule_d3ffc762afc8) | v_processed_count := v_processed_count + 1 | /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 22-34 \| Chunk 03_main_body | 03_main_body:main_body | conditions[5]: v_processed_count := v_processed_count + 1 -> v_processed_count is incremented by 1 | Needs Review |
| 4 | Update ageing summary table (rule_7fdba897fa92) | status = 'ACTIVE' AND overdue_days > 0; SELECT account_id, overdue_days, outstanding_amount FROM LOAN_ACCOUNT FOR UPDATE | /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 3-10 \| Chunk 00_declaration; /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 3-10 \| Chunk 00_declaration \| Statement 00_declaration:chunk_text_01 (+1 more span(s)) | 00_declaration:declaration | conditions[0]: status = 'ACTIVE' AND overdue_days > 0 -> SELECT account_id, overdue_days, outstanding_amount FROM LOAN_ACCOUNT FOR UPDATE; table_operations[0]; table_operations[1]; table_operations[2]; tables_read[0]: LOAN_ACCOUNT \| READ \| target: account_id, overdue_days, outstanding_amount \| WHERE: status = 'ACTIVE' AND overdue_days > 0; tables_read[1]: LOAN_ACCOUNT \| READ \| target: account_id, overdue_days, outstanding_amount \| WHERE: status = 'ACTIVE' AND overdue_days > 0 FOR; _(+1 more instance(s) not shown)_ | Verified |
| 5 | Update ageing summary table (rule_c651ce0aebb6) | rec.overdue_days <= 30; v_ageing_bucket := 'BUCKET_0_30'; | /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 13-22 \| Chunk 02_nested_block | 02_nested_block:nested_block | conditions[1]: rec.overdue_days <= 30 -> v_ageing_bucket := 'BUCKET_0_30';; decision_chains[0] | Needs Review |
| 6 | Update ageing summary table (rule_79c805e7e9c1) | rec.overdue_days <= 60; v_ageing_bucket := 'BUCKET_31_60'; | /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 13-22 \| Chunk 02_nested_block | 02_nested_block:nested_block | conditions[2]: rec.overdue_days <= 60 -> v_ageing_bucket := 'BUCKET_31_60';; decision_chains[0] | Needs Review |
| 7 | Update ageing summary table (rule_08fb3c59efbc) | rec.overdue_days <= 90; v_ageing_bucket := 'BUCKET_61_90'; | /Users/dishajain/Desktop/logic_rules_extractor/samples/batch_overdue_ageing_block.sql \| Lines 13-22 \| Chunk 02_nested_block | 02_nested_block:nested_block | conditions[3]: rec.overdue_days <= 90 -> v_ageing_bucket := 'BUCKET_61_90';; decision_chains[0] | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** explicit = 3, inferred = 4
- **By validation status:** insufficient_evidence = 5, verified = 2

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **insufficient_evidence** have some support, but the technical extraction was incomplete or only weakly supported and should not be treated as fully verified._

## Reconciliation Summary

- **Matched facts:** 5
- **Deterministic-only facts:** 2
- **LLM-only claims:** 5
- **Conflicts:** 2
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_53771ea71b3f`): 03_main_body
- `LLM_ONLY` tables_written (`recon_c2e5a015e4e1`): 03_main_body
- `CONFLICT` rule (`recon_bfbebb1e9dba`): rule_3da6586f3c38, 00_declaration, 00_declaration:chunk_text_01;00_declaration:embedded_01_04 - Deterministic evidence conflicts with the synthesized claim.
- `LLM_ONLY` rule (`recon_c82317d9425f`): rule_d3ffc762afc8, 03_main_body - No deterministic evidence was found for this claim.
- `LLM_ONLY` rule (`recon_9a34bf5b4940`): rule_c651ce0aebb6, 02_nested_block - No deterministic evidence was found for this claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 29/100
- **Statement coverage:** 6 / 24 (25.0%)
- **Rule grounding coverage:** 3 / 7 (42.9%)
- **Conflicts:** 2
- **Contradictions:** 2
- **Review required items:** 9
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `rule_3da6586f3c38`: Synthesized condition conflicts with deterministic predicate evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not deterministically identify the database object type from the raw source.
- The supporting technical evidence was low-confidence and should not be presented as fully verified: tgt.account_id = src.account_id
- The supporting technical evidence was low-confidence and should not be presented as fully verified: v_processed_count := v_processed_count + 1
- The supporting technical evidence was low-confidence and should not be presented as fully verified: rec.overdue_days <= 30, v_ageing_bucket := 'BUCKET_0_30';
- The supporting technical evidence was low-confidence and should not be presented as fully verified: rec.overdue_days <= 60, v_ageing_bucket := 'BUCKET_31_60';
- The supporting technical evidence was low-confidence and should not be presented as fully verified: rec.overdue_days <= 90, v_ageing_bucket := 'BUCKET_61_90';
- Automated style check flagged possible leftover technical jargon in the synthesized output: if statement, pl/sql.
