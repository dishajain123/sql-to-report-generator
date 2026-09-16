# NPA Movement Audit Log — Verification & Traceability

> Companion artifact to `PRO.NPA_Movement_Audit_Log.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_6f3adb81cb4c` |
| Raw technical object name (from source) | `NPA_Movement_Audit_Log` |

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
| Source Hash | `3e6753521451cb8ac2c64ef5653d89c2aa89df0aa774496d76e68f3663a815a2` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:19:18.673225+00:00` |
| Object ID | `obj_6f3adb81cb4c` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_17720291528f` |
| Total LLM Calls | `4` |
| Successful Calls | `4` |
| Failed Calls | `0` |
| Prompt Tokens | `21454` |
| Completion Tokens | `4238` |
| Total Tokens | `25692` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 5198 | available |
| synthesis | 3 | 3 | 0 | 20494 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Insert asset movements [CONFLICT] (`rule__1`) | `AssetClassMovementHistory, TimeKey, AccountId, PreviousClass, CurrentClass, MovementDate` | Records asset class movements for accounts that have changed classes. |
| 🔴 2 | Insert customer movements [CONFLICT] (`rule__2`) | `CustomerClassMovementHistory, TimeKey, CustomerId, WorstClass, MovementDate` | Records customer class movements for customers with non-standard asset classes. |
| 🟠 3 | Truncate previous asset class [LLM_ONLY] (`rule__3`) | `Not specified` | Clears the previous asset class records to prepare for new data insertion. |
| 🟢 4 | Update movement count [MATCHED] (`rule__5`) | `MovementCount` | Increments the movement count in the RunStatistics table based on the number of asset class movements recorded. |
| 🟢 5 | Flag multi-account movements [MATCHED] (`rule__6`) | `MultiAccountMovementFlag` | Sets the MultiAccountMovementFlag to 'Y' for customers with more than one account movement in the current run. |
| 🔴 6 | Update run status [CONFLICT] (`rule__7`) | `RunStatus, COMPLETED, ErrorDate, ErrorDescription, RunCount` | Marks the NPA_Movement_Audit_Log process as completed and resets error information. |
| 🔴 7 | Update run status on error [CONFLICT] (`rule__1__7`) | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an exception occurs during the NPA_Movement_Audit_Log process, the run status is updated to indicate the process did not complete succes… |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Insert asset movements (rule__1) | INSERT INTO PRO.AssetClassMovementHistory (TimeKey, AccountId, PreviousClass, CurrentClass, MovementDate) SELECT @TimeKey, B.AccountId, A.AssetClass, B.AssetClass, GETDATE() FROM PRO.PreviousAssetClass A RIGHT OUTER JOIN PRO.AccountCal B ON A.AccountId = B.Ac… | Not cited | Not cited | Not cited | Needs Review |
| 2 | Insert customer movements (rule__2) | INSERT INTO PRO.CustomerClassMovementHistory (TimeKey, CustomerId, WorstClass, MovementDate) SELECT @TimeKey, B.CustomerId, MIN(B.AssetClass), GETDATE() FROM PRO.AccountCal B WHERE B.AssetClass <> 'STANDARD' GROUP BY B.CustomerId | Not cited | Not cited | Not cited | Needs Review |
| 3 | Truncate previous asset class (rule__3) | TRUNCATE TABLE PRO.PreviousAssetClass | Not cited | Not cited | Not cited | Needs Review |
| 4 | Update movement count (rule__5) | UPDATE PRO.RunStatistics SET MovementCount = MovementCount + (SELECT COUNT(*) FROM PRO.AssetClassMovementHistory WHERE TimeKey = @TimeKey) WHERE StatisticName = 'DAILY_ASSET_MOVEMENTS' | Not cited | Not cited | Not cited | Verified |
| 5 | Flag multi-account movements (rule__6) | UPDATE C SET C.MultiAccountMovementFlag = 'Y' FROM PRO.CustomerCal C WHERE C.CustomerId IN (SELECT CustomerId FROM PRO.CustomerClassMovementHistory WHERE TimeKey = @TimeKey GROUP BY CustomerId HAVING COUNT(*) > 1) | Not cited | Not cited | Not cited | Verified |
| 6 | Update run status (rule__7) | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' | Not cited | Not cited | Not cited | Needs Review |
| 7 | Update run status on error (rule__1__7) | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' | Not cited | BEGIN CATCH... END CATCH | dependency_0001; dependency_0002 | Needs Review |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 52
- **Disposition:** covered_by_rule=35, uncovered=17

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | uncovered | Lines 1-2 | 03_batch3_main_body+batch3_nested_block:chunk_text_01, 03_batch3_main_body+batch3_nested_block | BEGIN SET NOCOUNT ON |
| STATEMENT | uncovered | Lines 4-8 | 03_batch3_main_body+batch3_nested_block:chunk_text_02, 03_batch3_main_body+batch3_nested_block | BEGIN TRY -- Rule 1 (condition modeled on PRO.SMA_MARKING's real change-detection -- logic: `WHERE B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'')`): -- log an account-level movement row only when classificatio... |
| INSERT | covered_by_rule | Lines 9-15 | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AssetClassMovementHistory (TimeKey, AccountId, PreviousClass, CurrentClass, MovementDate) SELECT @TimeKey, B.AccountId, A.AssetClass, B.AssetClass, GETDATE() FROM PRO.PreviousAssetClass A RIGHT OUTER JOIN PRO.AccountCal B... |
| INSERT | covered_by_rule | Lines 16-22 | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CustomerClassMovementHistory (TimeKey, CustomerId, WorstClass, MovementDate) SELECT @TimeKey, B.CustomerId, MIN(B.AssetClass), GETDATE() FROM PRO.AccountCal B WHERE B.AssetClass <> 'STANDARD' GROUP BY B.CustomerId -- Rule... |
| TRUNCATETABLE | covered_by_rule | Lines 23-23 | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | TRUNCATE TABLE PRO.PreviousAssetClass |
| INSERT | uncovered | Lines 25-29 | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.PreviousAssetClass (AccountId, AssetClass) SELECT AccountId, AssetClass FROM PRO.AccountCal -- Rule 4 (formula): increment the movement counter used for the daily operations dashboard |
| UPDATE | covered_by_rule | Lines 30-34 | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatistics SET MovementCount = MovementCount + (SELECT COUNT(*) FROM PRO.AssetClassMovementHistory WHERE TimeKey = @TimeKey) WHERE StatisticName = 'DAILY_ASSET_MOVEMENTS' -- Rule 5: flag customers with more than one account... |
| UPDATE | covered_by_rule | Lines 35-44 | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.MultiAccountMovementFlag = 'Y' FROM PRO.CustomerCal C WHERE C.CustomerId IN ( SELECT CustomerId FROM PRO.CustomerClassMovementHistory WHERE TimeKey = @TimeKey GROUP BY CustomerId HAVING COUNT(*) > 1 ) |
| UPDATE | covered_by_rule | Lines 46-48 | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' |
| STATEMENT | uncovered | Lines 50-50 | 03_batch3_main_body+batch3_nested_block:chunk_text_10, 03_batch3_main_body+batch3_nested_block | END TRY |
| INSERT | covered_by_rule | Lines 9-15 | 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AssetClassMovementHistory (TimeKey, AccountId, PreviousClass, CurrentClass, MovementDate) SELECT @TimeKey, B.AccountId, A.AssetClass, B.AssetClass, GETDATE() FROM PRO.PreviousAssetClass A RIGHT OUTER JOIN PRO.AccountCal B... |
| INSERT | covered_by_rule | Lines 16-22 | 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CustomerClassMovementHistory (TimeKey, CustomerId, WorstClass, MovementDate) SELECT @TimeKey, B.CustomerId, MIN(B.AssetClass), GETDATE() FROM PRO.AccountCal B WHERE B.AssetClass <> 'STANDARD' GROUP BY B.CustomerId -- Rule... |
| INSERT | uncovered | Lines 25-29 | 03_batch3_main_body+batch3_nested_block:embedded_03_13, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.PreviousAssetClass (AccountId, AssetClass) SELECT AccountId, AssetClass FROM PRO.AccountCal -- Rule 4 (formula): increment the movement counter used for the daily operations dashboard |
| UPDATE | covered_by_rule | Lines 30-34 | 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatistics SET MovementCount = MovementCount + (SELECT COUNT(*) FROM PRO.AssetClassMovementHistory WHERE TimeKey = @TimeKey) WHERE StatisticName = 'DAILY_ASSET_MOVEMENTS' -- Rule 5: flag customers with more than one account... |
| UPDATE | covered_by_rule | Lines 35-44 | 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.MultiAccountMovementFlag = 'Y' FROM PRO.CustomerCal C WHERE C.CustomerId IN ( SELECT CustomerId FROM PRO.CustomerClassMovementHistory WHERE TimeKey = @TimeKey GROUP BY CustomerId HAVING COUNT(*) > 1 ) |
| UPDATE | covered_by_rule | Lines 46-48 | 03_batch3_main_body+batch3_nested_block:embedded_06_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' |
| STATEMENT | uncovered | Lines 1-2 | 04_batch3_exception:chunk_text_01, 04_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_03, 04_batch3_exception | END CATCH |
| STATEMENT | uncovered | Lines 6-6 | 04_batch3_exception:chunk_text_04, 04_batch3_exception | END |
| UPDATE | covered_by_rule | Lines 3-5 | 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' |
| INSERT | covered_by_rule | samples/05_NPA_Movement_Audit_Log.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block:chunk_text_03, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AssetClassMovementHistory (TimeKey, AccountId, PreviousClass, CurrentClass, MovementDate) SELECT @TimeKey, B.AccountId, A.AssetClass, B.AssetClass, GETDATE() FROM PRO.PreviousAssetClass A RIGHT OUTER JOIN PRO.AccountCal B... |
| INSERT | covered_by_rule | samples/05_NPA_Movement_Audit_Log.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block:chunk_text_04, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CustomerClassMovementHistory (TimeKey, CustomerId, WorstClass, MovementDate) SELECT @TimeKey, B.CustomerId, MIN(B.AssetClass), GETDATE() FROM PRO.AccountCal B WHERE B.AssetClass <> 'STANDARD' GROUP BY B.CustomerId -- Rule... |
| TRUNCATE | covered_by_rule | samples/05_NPA_Movement_Audit_Log.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block:chunk_text_05, 03_batch3_main_body+batch3_nested_block | TRUNCATE TABLE PRO.PreviousAssetClass |
| INSERT | uncovered | samples/05_NPA_Movement_Audit_Log.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block:chunk_text_06, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.PreviousAssetClass (AccountId, AssetClass) SELECT AccountId, AssetClass FROM PRO.AccountCal -- Rule 4 (formula): increment the movement counter used for the daily operations dashboard |
| UPDATE | covered_by_rule | samples/05_NPA_Movement_Audit_Log.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatistics SET MovementCount = MovementCount + (SELECT COUNT(*) FROM PRO.AssetClassMovementHistory WHERE TimeKey = @TimeKey) WHERE StatisticName = 'DAILY_ASSET_MOVEMENTS' -- Rule 5: flag customers with more than one account... |
| READ | covered_by_rule | samples/05_NPA_Movement_Audit_Log.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block:chunk_text_07, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatistics SET MovementCount = MovementCount + (SELECT COUNT(*) FROM PRO.AssetClassMovementHistory WHERE TimeKey = @TimeKey) WHERE StatisticName = 'DAILY_ASSET_MOVEMENTS' -- Rule 5: flag customers with more than one account... |
| UPDATE | covered_by_rule | samples/05_NPA_Movement_Audit_Log.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.MultiAccountMovementFlag = 'Y' FROM PRO.CustomerCal C WHERE C.CustomerId IN ( SELECT CustomerId FROM PRO.CustomerClassMovementHistory WHERE TimeKey = @TimeKey GROUP BY CustomerId HAVING COUNT(*) > 1 ) |
| READ | covered_by_rule | samples/05_NPA_Movement_Audit_Log.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block:chunk_text_08, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.MultiAccountMovementFlag = 'Y' FROM PRO.CustomerCal C WHERE C.CustomerId IN ( SELECT CustomerId FROM PRO.CustomerClassMovementHistory WHERE TimeKey = @TimeKey GROUP BY CustomerId HAVING COUNT(*) > 1 ) |
| UPDATE | covered_by_rule | samples/05_NPA_Movement_Audit_Log.sql | 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block:chunk_text_09, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AssetClassMovementHistory (TimeKey, AccountId, PreviousClass, CurrentClass, MovementDate) SELECT @TimeKey, B.AccountId, A.AssetClass, B.AssetClass, GETDATE() FROM PRO.PreviousAssetClass A RIGHT OUTER JOIN PRO.AccountCal B... |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block:embedded_01_11, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.AssetClassMovementHistory (TimeKey, AccountId, PreviousClass, CurrentClass, MovementDate) SELECT @TimeKey, B.AccountId, A.AssetClass, B.AssetClass, GETDATE() FROM PRO.PreviousAssetClass A RIGHT OUTER JOIN PRO.AccountCal B... |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CustomerClassMovementHistory (TimeKey, CustomerId, WorstClass, MovementDate) SELECT @TimeKey, B.CustomerId, MIN(B.AssetClass), GETDATE() FROM PRO.AccountCal B WHERE B.AssetClass <> 'STANDARD' GROUP BY B.CustomerId -- Rule... |
| INSERT | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block:embedded_02_12, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.CustomerClassMovementHistory (TimeKey, CustomerId, WorstClass, MovementDate) SELECT @TimeKey, B.CustomerId, MIN(B.AssetClass), GETDATE() FROM PRO.AccountCal B WHERE B.AssetClass <> 'STANDARD' GROUP BY B.CustomerId -- Rule... |
| READ | uncovered | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_03_13, 03_batch3_main_body+batch3_nested_block:embedded_03_13, 03_batch3_main_body+batch3_nested_block | INSERT INTO PRO.PreviousAssetClass (AccountId, AssetClass) SELECT AccountId, AssetClass FROM PRO.AccountCal -- Rule 4 (formula): increment the movement counter used for the daily operations dashboard |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatistics SET MovementCount = MovementCount + (SELECT COUNT(*) FROM PRO.AssetClassMovementHistory WHERE TimeKey = @TimeKey) WHERE StatisticName = 'DAILY_ASSET_MOVEMENTS' -- Rule 5: flag customers with more than one account... |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block:embedded_04_14, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatistics SET MovementCount = MovementCount + (SELECT COUNT(*) FROM PRO.AssetClassMovementHistory WHERE TimeKey = @TimeKey) WHERE StatisticName = 'DAILY_ASSET_MOVEMENTS' -- Rule 5: flag customers with more than one account... |
| READ | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.MultiAccountMovementFlag = 'Y' FROM PRO.CustomerCal C WHERE C.CustomerId IN ( SELECT CustomerId FROM PRO.CustomerClassMovementHistory WHERE TimeKey = @TimeKey GROUP BY CustomerId HAVING COUNT(*) > 1 ) |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block:embedded_05_15, 03_batch3_main_body+batch3_nested_block | UPDATE C SET C.MultiAccountMovementFlag = 'Y' FROM PRO.CustomerCal C WHERE C.CustomerId IN ( SELECT CustomerId FROM PRO.CustomerClassMovementHistory WHERE TimeKey = @TimeKey GROUP BY CustomerId HAVING COUNT(*) > 1 ) |
| UPDATE | covered_by_rule | unavailable | 03_batch3_main_body+batch3_nested_block:embedded_06_16, 03_batch3_main_body+batch3_nested_block:embedded_06_16, 03_batch3_main_body+batch3_nested_block | UPDATE PRO.RunStatus SET COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' |
| UPDATE | covered_by_rule | samples/05_NPA_Movement_Audit_Log.sql / Lines 68-74 | 04_batch3_exception:chunk_text_02, 04_batch3_exception:chunk_text_02, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' |
| UPDATE | covered_by_rule | unavailable | 04_batch3_exception:embedded_01_05, 04_batch3_exception:embedded_01_05, 04_batch3_exception | UPDATE PRO.RunStatus SET COMPLETED = 'N', ErrorDate = GETDATE(), ErrorDescription = ERROR_MESSAGE(), RunCount = ISNULL(RunCount, 0) + 1 WHERE ProcessName = 'NPA_Movement_Audit_Log' |
| CALCULATION | covered_by_rule | Lines 34-34 | unavailable | SELECT @TimeKey, B.CustomerId, MIN(B.AssetClass), GETDATE() |
| CALCULATION | covered_by_rule | Lines 48-48 | unavailable | SET MovementCount = MovementCount + (SELECT COUNT(*) FROM PRO.AssetClassMovementHistory WHERE TimeKey = @TimeKey) |
| CALCULATION | covered_by_rule | Lines 60-60 | unavailable | HAVING COUNT(*) > 1 |
| CATCH | uncovered | Lines 68-68 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 73-73 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_01_11 / PRO.AssetClassMovementHistory | 03_batch3_main_body+batch3_nested_block:embedded_04_14 / PRO.AssetClassMovementHistory | high |
| table_write_to_later_use | 03_batch3_main_body+batch3_nested_block:embedded_02_12 / PRO.CustomerClassMovementHistory | 03_batch3_main_body+batch3_nested_block:embedded_05_15 / PRO.CustomerClassMovementHistory | high |

Unresolved dependency candidates: 14. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 7
- **By rule type:** explicit = 7
- **By validation status:** unverified = 5, verified = 2

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 13
- **Deterministic-only facts:** 13
- **LLM-only claims:** 2
- **Conflicts:** 4
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `LLM_ONLY` tables_written (`recon_eec8d6b6746d`): full_source
- `CONFLICT` rule (`recon_bb62a9afb754`): rule__1, 03_batch3_main_body+batch3_nested_block:embedded_01_11 - Deterministic evidence conflicts with the synthesized claim.
- `CONFLICT` rule (`recon_81d997caa0b8`): rule__2, 03_batch3_main_body+batch3_nested_block:embedded_02_12 - Deterministic evidence conflicts with the synthesized claim.
- `LLM_ONLY` rule (`recon_af8608ee81d0`): rule__3 - No deterministic evidence was found for this claim.
- `CONFLICT` rule (`recon_b9edf52f8b98`): rule__7, 03_batch3_main_body+batch3_nested_block:chunk_text_09;03_batch3_main_body+batch3_nested_block:embedded_06_16;04_batch3_exception:chunk_text_02;04_batch3_exception:embedded_01_05 - Deterministic evidence conflicts with the synthesized claim.

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 86.03448275862068/100
- **Statement coverage:** 19 / 26 (73.1%)
- **Rule grounding coverage:** 6 / 7 (85.7%)
- **Decision-chain coverage:** Not applicable (no deterministic decision chains detected)
- **Conflicts:** 4
- **Contradictions:** 5
- **Review required items:** 11
- **Review required:** Yes

Statement parse success is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `rule__1`: Synthesized rule affects different fields than the deterministic evidence.
- `MEDIUM` Field Conflict on `rule__2`: Synthesized rule affects different fields than the deterministic evidence.
- `MEDIUM` Field Conflict on `rule__7`: Synthesized rule affects different fields than the deterministic evidence.
- `HIGH` Outcome Conflict on `rule__7`: Synthesized outcome/assignment conflicts with deterministic evidence.
- `MEDIUM` Field Conflict on `rule__1__7`: Synthesized rule affects different fields than the deterministic evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Synthesized in 3 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
