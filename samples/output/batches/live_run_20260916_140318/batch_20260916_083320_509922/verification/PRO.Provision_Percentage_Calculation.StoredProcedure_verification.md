# Provision Percentage Calculation — Verification & Traceability

> Companion artifact to `PRO.Provision_Percentage_Calculation.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_890a2d3ea714` |
| Raw technical object name (from source) | `Provision_Percentage_Calculation` |

## Run Metadata

| Item | Value |
|---|---|
| Pipeline Version | `2026-08-26-phase1` |
| Prompt Version | `3fde9e2078dcda12` |
| Knowledge Base Version | `2e6fc62902751973` |
| Model | `amazon.nova-lite-v1:0` |
| Provider | `bedrock` |
| Dialect | `T-SQL` |
| Dialect Confidence | `High` |
| Source Hash | `a644e9ad7329553f5a95dbe1d6047027e8ac2e37955a3ae74b2c78e3c4029117` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T08:34:41.778836+00:00` |
| Object ID | `obj_890a2d3ea714` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_f01c5f76a740` |
| Total LLM Calls | `6` |
| Successful Calls | `6` |
| Failed Calls | `0` |
| Prompt Tokens | `45091` |
| Completion Tokens | `7489` |
| Total Tokens | `52580` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 4928 | available |
| synthesis | 3 | 3 | 0 | 16931 | available |
| synthesis_revision | 2 | 2 | 0 | 30721 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟠 1 | Determine ProvisionPct [MATCHED] (`deterministic_case_0025_0031_748_provisionpct`) | `ProvisionPct` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ 2 | Calculate provisioning percentage [LLM_ONLY] (`rule__1__2`) | `ProvisionPct` | Determine the provisioning percentage for accounts based on the asset class. |
| ⚠️ 3 | Increase provision percentage [MATCHED] (`rule__2`) | `ProvisionPct` | Increase the provision percentage by 10% for unsecured accounts with non-standard asset classes. |
| ⚠️ 4 | Calculate provision amount [CONFLICT] (`rule__3`) | `ProvisionAmount` | Calculate the provision amount based on the outstanding balance and provision percentage. |
| ⚠️ 5 | Limit provision amount [CONFLICT] (`rule__4`) | `ProvisionAmount` | Ensure the provision amount does not exceed the outstanding balance. |
| ⚠️ 6 | Flag for senior review [CONFLICT] (`rule__5`) | `SeniorReviewFlag` | Flag accounts for senior review if the provision amount exceeds 1,000,000. |
| ⚠️ 7 | Update run status [MATCHED] (`rule__6`) | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | Update the process run status to mark the process as completed and increment the run count. |
| ⚠️ 8 | Update run status on error [CONFLICT] (`rule__1__8`) | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an error occurs during the provision percentage calculation, update the run status to reflect the error. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Determine ProvisionPct (deterministic_case_0025_0031_748_provisionpct) | Not cited | source \| Lines 25-31 | Not cited | Not cited | Verified |
| 2 | Calculate provisioning percentage (rule__1__2) | UPDATE A SET A.ProvisionPct = (CASE A.AssetClass... END) FROM PRO.AccountCal A | Not cited | Not cited | Not cited | Verified |
| 3 | Increase provision percentage (rule__2) | UPDATE A SET A.ProvisionPct = A.ProvisionPct + 10.00 FROM PRO.AccountCal A WHERE A.SecuredFlag = 'N' AND A.AssetClass <> 'STANDARD' | Not cited | Not cited | Not cited | Verified |
| 4 | Calculate provision amount (rule__3) | UPDATE A SET A.ProvisionAmount = (A.OutstandingBalance * A.ProvisionPct) / 100 FROM PRO.AccountCal A WHERE A.OutstandingBalance > 0 | Not cited | Not cited | Not cited | Verified |
| 5 | Limit provision amount (rule__4) | UPDATE A SET A.ProvisionAmount = A.OutstandingBalance FROM PRO.AccountCal A WHERE A.ProvisionAmount > A.OutstandingBalance | Not cited | Not cited | Not cited | Verified |
| 6 | Flag for senior review (rule__5) | UPDATE A SET A.SeniorReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.ProvisionAmount > 1000000 | Not cited | Not cited | Not cited | Verified |
| 7 | Update run status (rule__6) | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Provision_Percentage_Calculation' | Not cited | Not cited | Not cited | Verified |
| 8 | Update run status on error (rule__1__8) | ProcessName = 'Provision_Percentage_Calculation' | Not cited | Not cited | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| case_0025_0031_748:branch_001 | A.AssetClass = 'STANDARD' | source \| Lines 26-27 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_04 |
| case_0025_0031_748:branch_002 | A.AssetClass = 'SUBSTANDARD' | source \| Lines 27-28 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_04 |
| case_0025_0031_748:branch_003 | A.AssetClass = 'DOUBTFUL' | source \| Lines 28-29 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_04 |
| case_0025_0031_748:branch_004 | A.AssetClass = 'LOSS' | source \| Lines 29-30 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_04 |
| case_0025_0031_748:branch_005 | ELSE | source \| Lines 30-31 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_05 |
| decision_chain_002:branch_001 | A.AssetClass = 'STANDARD' | source |
| decision_chain_002:branch_002 | A.AssetClass = 'SUBSTANDARD' | source |
| decision_chain_002:branch_003 | A.AssetClass = 'DOUBTFUL' | source |
| decision_chain_002:branch_004 | A.AssetClass = 'LOSS' | source |
| decision_chain_002:branch_005 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 58
- **Disposition:** covered_by_rule=42, uncovered=16

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | uncovered | Lines 1-2 | 03_batch3_main_body+batch3_nested_block:chunk_text_01, 03_batch3_main_body+batch3_nested_block | BEGIN SET NOCOUNT ON |
| STATEMENT | uncovered | Lines 4-6 | 03_batch3_main_body+batch3_nested_block:chunk_text_02, 03_batch3_main_body+batch3_nested_block | BEGIN TRY -- Rule 1: base provisioning percentage by asset classification |
| UPDATE | uncovered | Lines 7-19 | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionPct = ( CASE A.AssetClass WHEN 'STANDARD' THEN 0.40 WHEN 'SUBSTANDARD' THEN 15.00 WHEN 'DOUBTFUL' THEN 25.00 WHEN 'LOSS' THEN 100.00 ELSE 0.00 END ) FROM PRO.AccountCal A -- Rule 2: unsecured accounts carry an add... |
| UPDATE | covered_by_rule | Lines 20-28 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionPct = A.ProvisionPct + 10.00 FROM PRO.AccountCal A WHERE A.SecuredFlag = 'N' AND A.AssetClass <> 'STANDARD' -- Rule 3 (formula, same shape as the real AddlProvision calculation in -- PRO.UpdateNetBalance_AccountWi... |
| UPDATE | covered_by_rule | Lines 29-34 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionAmount = (A.OutstandingBalance * A.ProvisionPct) / 100 FROM PRO.AccountCal A WHERE A.OutstandingBalance > 0 -- Rule 4: the provision amount can never exceed the outstanding balance |
| UPDATE | covered_by_rule | Lines 35-40 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionAmount = A.OutstandingBalance FROM PRO.AccountCal A WHERE A.ProvisionAmount > A.OutstandingBalance -- Rule 5: flag large provisions (over 1,000,000) for senior review |
| UPDATE | covered_by_rule | Lines 41-44 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SeniorReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.ProvisionAmount > 1000000 |
| UPDATE | covered_by_rule | Lines 46-48 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Provision_Percentage_Calculation' |
| STATEMENT | uncovered | Lines 50-50 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | END TRY |
| UPDATE | uncovered | Lines 7-19 | 03_batch3_main_body+batch3_nested_block:embedded_01_10, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionPct = ( CASE A.AssetClass WHEN 'STANDARD' THEN 0.40 WHEN 'SUBSTANDARD' THEN 15.00 WHEN 'DOUBTFUL' THEN 25.00 WHEN 'LOSS' THEN 100.00 ELSE 0.00 END ) FROM PRO.AccountCal A -- Rule 2: unsecured accounts carry an add... |
| UPDATE | covered_by_rule | Lines 20-28 | 03_batch3_main_body+batch3_nested_block:embedded_02_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionPct = A.ProvisionPct + 10.00 FROM PRO.AccountCal A WHERE A.SecuredFlag = 'N' AND A.AssetClass <> 'STANDARD' -- Rule 3 (formula, same shape as the real AddlProvision calculation in -- PRO.UpdateNetBalance_AccountWi... |
| UPDATE | covered_by_rule | Lines 29-34 | 03_batch3_main_body+batch3_nested_block:embedded_03_12, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionAmount = (A.OutstandingBalance * A.ProvisionPct) / 100 FROM PRO.AccountCal A WHERE A.OutstandingBalance > 0 -- Rule 4: the provision amount can never exceed the outstanding balance |
| UPDATE | covered_by_rule | Lines 35-40 | 03_batch3_main_body+batch3_nested_block:embedded_04_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionAmount = A.OutstandingBalance FROM PRO.AccountCal A WHERE A.ProvisionAmount > A.OutstandingBalance -- Rule 5: flag large provisions (over 1,000,000) for senior review |
| UPDATE | covered_by_rule | Lines 41-44 | 03_batch3_main_body+batch3_nested_block:embedded_05_14, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SeniorReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.ProvisionAmount > 1000000 |
| UPDATE | covered_by_rule | Lines 46-48 | 03_batch3_main_body+batch3_nested_block:embedded_06_15, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Provision_Percentage_Calculation' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Provision_Percentage_Calculation' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| STATEMENT | covered_by_rule | Lines 6-6 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | END |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Provision_Percentage_Calculation' |
| UPDATE | uncovered | samples/03_Provision_Percentage_Calculation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionPct = ( CASE A.AssetClass WHEN 'STANDARD' THEN 0.40 WHEN 'SUBSTANDARD' THEN 15.00 WHEN 'DOUBTFUL' THEN 25.00 WHEN 'LOSS' THEN 100.00 ELSE 0.00 END ) FROM PRO.AccountCal A -- Rule 2: unsecured accounts carry an add... |
| UPDATE | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionPct = A.ProvisionPct + 10.00 FROM PRO.AccountCal A WHERE A.SecuredFlag = 'N' AND A.AssetClass <> 'STANDARD' -- Rule 3 (formula, same shape as the real AddlProvision calculation in -- PRO.UpdateNetBalance_AccountWi... |
| UPDATE | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionAmount = (A.OutstandingBalance * A.ProvisionPct) / 100 FROM PRO.AccountCal A WHERE A.OutstandingBalance > 0 -- Rule 4: the provision amount can never exceed the outstanding balance |
| UPDATE | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionAmount = A.OutstandingBalance FROM PRO.AccountCal A WHERE A.ProvisionAmount > A.OutstandingBalance -- Rule 5: flag large provisions (over 1,000,000) for senior review |
| UPDATE | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SeniorReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.ProvisionAmount > 1000000 |
| UPDATE | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Provision_Percentage_Calculation' |
| UPDATE | uncovered | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_10, 03_batch3_main_body+batch3_nested_block:embedded_01_10, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionPct = ( CASE A.AssetClass WHEN 'STANDARD' THEN 0.40 WHEN 'SUBSTANDARD' THEN 15.00 WHEN 'DOUBTFUL' THEN 25.00 WHEN 'LOSS' THEN 100.00 ELSE 0.00 END ) FROM PRO.AccountCal A -- Rule 2: unsecured accounts carry an add... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_11, 03_batch3_main_body+batch3_nested_block:embedded_02_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionPct = A.ProvisionPct + 10.00 FROM PRO.AccountCal A WHERE A.SecuredFlag = 'N' AND A.AssetClass <> 'STANDARD' -- Rule 3 (formula, same shape as the real AddlProvision calculation in -- PRO.UpdateNetBalance_AccountWi... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_12, 03_batch3_main_body+batch3_nested_block:embedded_03_12, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionAmount = (A.OutstandingBalance * A.ProvisionPct) / 100 FROM PRO.AccountCal A WHERE A.OutstandingBalance > 0 -- Rule 4: the provision amount can never exceed the outstanding balance |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_13, 03_batch3_main_body+batch3_nested_block:embedded_04_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionAmount = A.OutstandingBalance FROM PRO.AccountCal A WHERE A.ProvisionAmount > A.OutstandingBalance -- Rule 5: flag large provisions (over 1,000,000) for senior review |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_14, 03_batch3_main_body+batch3_nested_block:embedded_05_14, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.SeniorReviewFlag = 'Y' FROM PRO.AccountCal A WHERE A.ProvisionAmount > 1000000 |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_15, 03_batch3_main_body+batch3_nested_block:embedded_06_15, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Provision_Percentage_Calculation' |
| UPDATE | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql / Lines 67-73 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Provision_Percentage_Calculation' |
| UPDATE | covered_by_rule | unavailable | 04_batch3_exception:embedded_01_05, 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Provision_Percentage_Calculation' |
| CASE | covered_by_rule | Lines 26-27 | 03_batch3_main_body+batch3_nested_block:chunk_text_04 | A.AssetClass = 'STANDARD' |
| CASE | covered_by_rule | Lines 27-28 | 03_batch3_main_body+batch3_nested_block:chunk_text_04 | A.AssetClass = 'SUBSTANDARD' |
| CASE | covered_by_rule | Lines 28-29 | 03_batch3_main_body+batch3_nested_block:chunk_text_04 | A.AssetClass = 'DOUBTFUL' |
| CASE | covered_by_rule | Lines 29-30 | 03_batch3_main_body+batch3_nested_block:chunk_text_04 | A.AssetClass = 'LOSS' |
| ELSE | covered_by_rule | Lines 30-31 | 03_batch3_main_body+batch3_nested_block:chunk_text_05 | ELSE |
| IF_BRANCH | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | full_source | A.AssetClass = 'STANDARD' |
| IF_BRANCH | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | full_source | A.AssetClass = 'SUBSTANDARD' |
| IF_BRANCH | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | full_source | A.AssetClass = 'DOUBTFUL' |
| IF_BRANCH | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | full_source | A.AssetClass = 'LOSS' |
| ELSE | covered_by_rule | samples/03_Provision_Percentage_Calculation.sql | full_source | ELSE |
| CASE | covered_by_rule | Lines 25-25 | unavailable | CASE A.AssetClass |
| CASE_BRANCH | covered_by_rule | Lines 26-26 | unavailable | WHEN THEN 0.40 |
| CASE_BRANCH | covered_by_rule | Lines 27-27 | unavailable | WHEN THEN 15.00 |
| CASE_BRANCH | covered_by_rule | Lines 28-28 | unavailable | WHEN THEN 25.00 |
| CASE_BRANCH | covered_by_rule | Lines 29-29 | unavailable | WHEN THEN 100.00 |
| ELSE | covered_by_rule | Lines 30-30 | unavailable | ELSE 0.00 |
| CALCULATION | covered_by_rule | Lines 46-46 | unavailable | SET A.ProvisionAmount = (A.OutstandingBalance * A.ProvisionPct) / 100 |
| CATCH | uncovered | Lines 67-67 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 72-72 | unavailable | END CATCH |

## Confirmed Statement Dependencies


Unresolved dependency candidates: 43. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 8
- **By rule type:** deterministic_decision_table = 1, explicit = 7
- **By validation status:** verified = 8

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 10
- **Deterministic-only facts:** 14
- **LLM-only claims:** 1
- **Conflicts:** 5
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_88a527b0b3ac`): full_source
- `LLM_ONLY` rule (`recon_eacc1f179bcf`): rule__1__2 - No deterministic evidence was found for this claim.
- `CONFLICT` rule (`recon_e9906111e4b1`): rule__3, 03_batch3_main_body+batch3_nested_block:chunk_text_05;03_batch3_main_body+batch3_nested_block:embedded_03_12 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_7929834c021b`): rule__4, 03_batch3_main_body+batch3_nested_block:chunk_text_06;03_batch3_main_body+batch3_nested_block:embedded_04_13 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_7ed81d44cf7a`): rule__5, 03_batch3_main_body+batch3_nested_block:chunk_text_07;03_batch3_main_body+batch3_nested_block:embedded_05_14 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 86.125/100
- **Statement coverage:** 18 / 25 (72.0%)
- **Rule grounding coverage:** 6 / 8 (75.0%)
- **Decision-chain coverage:** 5 / 5 branches (100.0%)
- **Conflicts:** 5
- **Contradictions:** 5
- **Review required items:** 11
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `rule__3`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `rule__4`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `rule__5`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule__1__8`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: @TimeKey is provided
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE A SET A.ProvisionPct = (CASE A.AssetClass... END) FROM PRO.AccountCal A
- Synthesized in 3 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
