# Asset Class Upgrade Marking — Verification & Traceability

> Companion artifact to `PRO.Asset_Class_Upgrade_Marking.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_510af9b5e9e9` |
| Raw technical object name (from source) | `Asset_Class_Upgrade_Marking` |

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
| Source Hash | `560a6822ac7bb45373a4debba9ef544783e3c6ee7f6a69459dfd7cf29352386e` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T08:35:20.521530+00:00` |
| Object ID | `obj_510af9b5e9e9` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_f50d21983a74` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `18944` |
| Completion Tokens | `3678` |
| Total Tokens | `22622` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 5046 | available |
| synthesis | 3 | 3 | 0 | 17576 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🟢 1 | Mark accounts for upgrade eligibility [MATCHED] (`rule__1`) | `UpgradeEligible` | Determines if accounts are eligible for asset class upgrade based on overdue days and review period. |
| 🟢 2 | Calculate provision release amount [MATCHED] (`rule__2`) | `ProvisionReleaseAmount` | Computes the provision release amount for eligible accounts. |
| 🟢 3 | Reclassify accounts to standard [MATCHED] (`rule__3`) | `AssetClass, ProvisionPct, ProvisionAmount` | Reclassifies eligible accounts to the 'STANDARD' asset class with base provisioning. |
| 🟢 4 | Record upgrade date [MATCHED] (`rule__4`) | `UpgradeDate` | Stamps the date the upgrade took effect for eligible accounts. |
| 🟢 5 | Update process status [MATCHED] (`rule__5`) | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Marks the process as completed and increments the run count. |
| 🟠 6 | Determine UpgradeEligible [MATCHED] (`deterministic_tsql_if_0026_0045_upgradeeligible`) | `UpgradeEligible` | Not specified |
| 🔴 7 | Update run status on error [CONFLICT] (`rule__1__6`) | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, update the run status to reflect the error. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Mark accounts for upgrade eligibility (rule__1) | A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.DaysSinceLastOverdue >= @ReviewPeriodDays; ELSE | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | 03_batch3_main_body+batch3_nested_block:chunk_text_10 | Verified |
| 2 | Calculate provision release amount (rule__2) | A.ProvisionAmount - ((A.OutstandingBalance * A.StandardProvisionPct) / 100) | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_13 | 03_batch3_main_body+batch3_nested_block:chunk_text_13 | Verified |
| 3 | Reclassify accounts to standard (rule__3) | A.AssetClass = 'STANDARD', A.ProvisionPct = A.StandardProvisionPct, A.ProvisionAmount = (A.OutstandingBalance * A.StandardProvisionPct) / 100 | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_14 | 03_batch3_main_body+batch3_nested_block:chunk_text_14 | Verified |
| 4 | Record upgrade date (rule__4) | A.UpgradeDate = @ProcessDate | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_15 | 03_batch3_main_body+batch3_nested_block:chunk_text_15 | Verified |
| 5 | Update process status (rule__5) | COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 | Not cited | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | 03_batch3_main_body+batch3_nested_block:chunk_text_16 | Verified |
| 6 | Determine UpgradeEligible (deterministic_tsql_if_0026_0045_upgradeeligible) | Not cited | source \| Lines 26-45 | Not cited | Not cited | Verified |
| 7 | Update run status on error (rule__1__6) | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Asset_Class_Upgrade_Marking' | Not cited | BEGIN CATCH... END CATCH | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| tsql_if_0026_0045:branch_001 | EXISTS (SELECT 1 FROM PRO.AccountCal WHERE AssetClass <> 'STANDARD') | source \| Lines 27-34 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_12 |
| tsql_if_0026_0045:branch_002 | ELSE | source \| Lines 37-41 \| Statement 03_batch3_main_body+batch3_nested_block:chunk_text_13 |
| decision_chain_002:branch_001 | EXISTS (SELECT 1 FROM PRO.AccountCal WHERE AssetClass <> 'STANDARD') | source |
| decision_chain_002:branch_002 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 59
- **Disposition:** covered_by_rule=49, uncovered=10

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | covered_by_rule | Lines 1-2 | 03_batch3_main_body+batch3_nested_block:chunk_text_01, 03_batch3_main_body+batch3_nested_block | BEGIN SET NOCOUNT ON |
| STATEMENT | covered_by_rule | Lines 4-4 | 03_batch3_main_body+batch3_nested_block:chunk_text_02, 03_batch3_main_body+batch3_nested_block | BEGIN TRY |
| STATEMENT | covered_by_rule | Lines 6-6 | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | DECLARE @ReviewPeriodDays INT = 90 |
| SELECT | covered_by_rule | Lines 7-9 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) -- Rule 1: mark NPA accounts eligible for upgrade if cleared for the full review period |
| SELECT | covered_by_rule | Lines 10-10 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | IF EXISTS (SELECT 1 FROM PRO.AccountCal WHERE AssetClass <> 'STANDARD') |
| STATEMENT | covered_by_rule | Lines 1-1 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 12-17 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeEligible = 'Y' FROM PRO.AccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.DaysSinceLastOverdue >= @ReviewPeriodDays |
| STATEMENT | covered_by_rule | Lines 18-19 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | END -- Rule 2: otherwise, mark all accounts as not eligible this run |
| STATEMENT | covered_by_rule | Lines 20-20 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | ELSE |
| STATEMENT | covered_by_rule | Lines 1-1 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 22-24 | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeEligible = 'N' FROM PRO.AccountCal A |
| STATEMENT | covered_by_rule | Lines 25-29 | 03_batch3_main_body+batch3_nested_block:chunk_text_12, 03_batch3_main_body+batch3_nested_block | END -- Rule 3 (formula, same balance * percent / 100 shape as the real -- AddlProvision calculation in PRO.UpdateNetBalance_AccountWise): -- calculate the provision released by the upgrade, before reclassifying |
| UPDATE | covered_by_rule | Lines 30-35 | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionReleaseAmount = A.ProvisionAmount - ((A.OutstandingBalance * A.StandardProvisionPct) / 100) FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' -- Rule 4: reclassify eligible accounts back to Standard with base pr... |
| UPDATE | covered_by_rule | Lines 36-43 | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = 'STANDARD', A.ProvisionPct = A.StandardProvisionPct, A.ProvisionAmount = (A.OutstandingBalance * A.StandardProvisionPct) / 100 FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' -- Rule 5: stamp the date the... |
| UPDATE | covered_by_rule | Lines 44-47 | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeDate = @ProcessDate FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' |
| UPDATE | covered_by_rule | Lines 49-51 | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Asset_Class_Upgrade_Marking' |
| STATEMENT | covered_by_rule | Lines 53-53 | 03_batch3_main_body+batch3_nested_block:chunk_text_17, 03_batch3_main_body+batch3_nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 12-17 | 03_batch3_main_body+batch3_nested_block:embedded_01_18, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeEligible = 'Y' FROM PRO.AccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.DaysSinceLastOverdue >= @ReviewPeriodDays |
| UPDATE | covered_by_rule | Lines 22-24 | 03_batch3_main_body+batch3_nested_block:embedded_02_19, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeEligible = 'N' FROM PRO.AccountCal A |
| UPDATE | covered_by_rule | Lines 30-35 | 03_batch3_main_body+batch3_nested_block:embedded_03_20, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionReleaseAmount = A.ProvisionAmount - ((A.OutstandingBalance * A.StandardProvisionPct) / 100) FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' -- Rule 4: reclassify eligible accounts back to Standard with base pr... |
| UPDATE | covered_by_rule | Lines 36-43 | 03_batch3_main_body+batch3_nested_block:embedded_04_21, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = 'STANDARD', A.ProvisionPct = A.StandardProvisionPct, A.ProvisionAmount = (A.OutstandingBalance * A.StandardProvisionPct) / 100 FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' -- Rule 5: stamp the date the... |
| UPDATE | covered_by_rule | Lines 44-47 | 03_batch3_main_body+batch3_nested_block:embedded_05_22, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeDate = @ProcessDate FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' |
| UPDATE | covered_by_rule | Lines 49-51 | 03_batch3_main_body+batch3_nested_block:embedded_06_23, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Asset_Class_Upgrade_Marking' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Asset_Class_Upgrade_Marking' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | END |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Asset_Class_Upgrade_Marking' |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) -- Rule 1: mark NPA accounts eligible for upgrade if cleared for the full review period |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | IF EXISTS (SELECT 1 FROM PRO.AccountCal WHERE AssetClass <> 'STANDARD') |
| UPDATE | covered_by_rule | samples/04_Asset_Class_Upgrade_Marking.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeEligible = 'Y' FROM PRO.AccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.DaysSinceLastOverdue >= @ReviewPeriodDays |
| UPDATE | covered_by_rule | samples/04_Asset_Class_Upgrade_Marking.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block:chunk_text_11, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeEligible = 'N' FROM PRO.AccountCal A |
| UPDATE | covered_by_rule | samples/04_Asset_Class_Upgrade_Marking.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block:chunk_text_13, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionReleaseAmount = A.ProvisionAmount - ((A.OutstandingBalance * A.StandardProvisionPct) / 100) FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' -- Rule 4: reclassify eligible accounts back to Standard with base pr... |
| UPDATE | covered_by_rule | samples/04_Asset_Class_Upgrade_Marking.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block:chunk_text_14, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = 'STANDARD', A.ProvisionPct = A.StandardProvisionPct, A.ProvisionAmount = (A.OutstandingBalance * A.StandardProvisionPct) / 100 FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' -- Rule 5: stamp the date the... |
| UPDATE | covered_by_rule | samples/04_Asset_Class_Upgrade_Marking.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block:chunk_text_15, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeDate = @ProcessDate FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' |
| UPDATE | covered_by_rule | samples/04_Asset_Class_Upgrade_Marking.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block:chunk_text_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Asset_Class_Upgrade_Marking' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_18, 03_batch3_main_body+batch3_nested_block:embedded_01_18, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeEligible = 'Y' FROM PRO.AccountCal A WHERE A.AssetClass <> 'STANDARD' AND A.OverdueDays = 0 AND A.DaysSinceLastOverdue >= @ReviewPeriodDays |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_19, 03_batch3_main_body+batch3_nested_block:embedded_02_19, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeEligible = 'N' FROM PRO.AccountCal A |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_20, 03_batch3_main_body+batch3_nested_block:embedded_03_20, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.ProvisionReleaseAmount = A.ProvisionAmount - ((A.OutstandingBalance * A.StandardProvisionPct) / 100) FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' -- Rule 4: reclassify eligible accounts back to Standard with base pr... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_21, 03_batch3_main_body+batch3_nested_block:embedded_04_21, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.AssetClass = 'STANDARD', A.ProvisionPct = A.StandardProvisionPct, A.ProvisionAmount = (A.OutstandingBalance * A.StandardProvisionPct) / 100 FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' -- Rule 5: stamp the date the... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_22, 03_batch3_main_body+batch3_nested_block:embedded_05_22, 03_batch3_main_body+batch3_nested_block | UPDATE A SET A.UpgradeDate = @ProcessDate FROM PRO.AccountCal A WHERE A.UpgradeEligible = 'Y' |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_23, 03_batch3_main_body+batch3_nested_block:embedded_06_23, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Asset_Class_Upgrade_Marking' |
| UPDATE | covered_by_rule | samples/04_Asset_Class_Upgrade_Marking.sql / Lines 70-76 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Asset_Class_Upgrade_Marking' |
| UPDATE | covered_by_rule | unavailable | 04_batch3_exception:embedded_01_05, 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'Asset_Class_Upgrade_Marking' |
| IF_BRANCH | covered_by_rule | Lines 27-34 | 03_batch3_main_body+batch3_nested_block:chunk_text_12 | EXISTS (SELECT 1 FROM PRO.AccountCal WHERE AssetClass <> 'STANDARD') |
| ELSE | covered_by_rule | Lines 37-41 | 03_batch3_main_body+batch3_nested_block:chunk_text_13 | ELSE |
| IF_BRANCH | covered_by_rule | samples/04_Asset_Class_Upgrade_Marking.sql | full_source | EXISTS (SELECT 1 FROM PRO.AccountCal WHERE AssetClass <> 'STANDARD') |
| ELSE | covered_by_rule | samples/04_Asset_Class_Upgrade_Marking.sql | full_source | ELSE |
| IF | covered_by_rule | Lines 26-26 | unavailable | IF EXISTS (SELECT 1 FROM PRO.AccountCal WHERE AssetClass <> ) |
| ELSE | covered_by_rule | Lines 36-36 | unavailable | ELSE |
| CALCULATION | covered_by_rule | Lines 47-47 | unavailable | SET A.ProvisionReleaseAmount = A.ProvisionAmount - ((A.OutstandingBalance * A.StandardProvisionPct) / 100) |
| CALCULATION | covered_by_rule | Lines 55-55 | unavailable | A.ProvisionAmount = (A.OutstandingBalance * A.StandardProvisionPct) / 100 |
| CATCH | uncovered | Lines 70-70 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 75-75 | unavailable | END CATCH |

## Confirmed Statement Dependencies


Unresolved dependency candidates: 42. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** deterministic_decision_table = 1, explicit = 6
- **By validation status:** verified = 7

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

## Reconciliation Summary

- **Matched facts:** 14
- **Deterministic-only facts:** 2
- **LLM-only claims:** 0
- **Conflicts:** 3
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_read (`recon_9fa17067c14f`): full_source
- `CONFLICT` tables_written (`recon_8abf8b3a553f`): full_source
- `CONFLICT` rule (`recon_5162918c1cd9`): rule__1__6, BEGIN CATCH... END CATCH, 03_batch3_main_body+batch3_nested_block:chunk_text_16;03_batch3_main_body+batch3_nested_block:embedded_06_23;04_batch3_exception:chunk_text_02;04_batch3_exception:embedded_01_05 - Deterministic evidence conflicts with the synthesized claim.
- `DETERMINISTIC_ONLY` coverage (`recon_f6313117b776`): 04_batch3_exception, 04_batch3_exception:chunk_text_02 - Deterministic evidence is present in the source but no synthesized rule referenced it.
- `DETERMINISTIC_ONLY` coverage (`recon_f6313117b776`): 04_batch3_exception, 04_batch3_exception:embedded_01_05 - Deterministic evidence is present in the source but no synthesized rule referenced it.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 88.05882352941177/100
- **Statement coverage:** 18 / 33 (54.5%)
- **Rule grounding coverage:** 6 / 7 (85.7%)
- **Decision-chain coverage:** 2 / 2 branches (100.0%)
- **Conflicts:** 3
- **Contradictions:** 4
- **Review required items:** 7
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `rule__1__6`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- One or more ambiguities showed signs of repetition-degeneration or mid-sentence truncation and were dropped rather than included in the report.
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: ELSE
- Synthesized in 3 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
