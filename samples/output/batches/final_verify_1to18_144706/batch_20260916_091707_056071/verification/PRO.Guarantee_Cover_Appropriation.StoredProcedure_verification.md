# Guarantee Cover Appropriation — Verification & Traceability

> Companion artifact to `PRO.Guarantee_Cover_Appropriation.StoredProcedure_report.md`. Everything here is pipeline/source provenance for review and audit; none of it appears in the business report.

| Item | Value |
|---|---|
| Object ID | `obj_490fdc2ddd1d` |
| Raw technical object name (from source) | `Guarantee_Cover_Appropriation` |

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
| Source Hash | `bb41ee60c4c2dffc6cbea25a80376a1d68029a8fc0a202d7a3ad77a065ac6b6e` |
| Configuration Version | `ddb60c677229031b` |
| Run Timestamp | `2026-09-16T09:29:14.097132+00:00` |
| Object ID | `obj_490fdc2ddd1d` |

## LLM Telemetry

| Item | Value |
|---|---|
| Run ID | `telemetry_b17413602789` |
| Total LLM Calls | `8` |
| Successful Calls | `8` |
| Failed Calls | `0` |
| Prompt Tokens | `150823` |
| Completion Tokens | `15747` |
| Total Tokens | `166570` |
| Telemetry Availability | `available` |

| Stage | Calls | Success | Failure | Tokens | Availability |
|---|---:|---:|---:|---:|---|
| extraction | 1 | 1 | 0 | 7306 | available |
| synthesis | 7 | 7 | 0 | 159264 | available |

## Business Rule Summary

| Priority | Rule | Output | Business Purpose |
|---|---|---|---|
| 🔴 1 | Insert into staging table [CONFLICT] (`rule__1__17`) | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Insert qualifying loan account entries into the staging table for cover ledger entries. |
| 🔴 2 | Merge into guarantee cover ledger [CONFLICT] (`rule__2__18`) | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover, LastAppropriationDate, FirstAppropriationDate` | Merge the staging table data into the guarantee cover ledger, updating existing entries or inserting new ones. |
| 🟢 3 | Update cover appropriated amount [MATCHED] (`rule__3__19`) | `CoverAppropriatedAmount` | Update the cover appropriated amount in the loan account calculation table based on the asset class and requested cover amount. |
| 🟢 4 | Update net provision after cover [MATCHED] (`rule__4__20`) | `NetProvisionAfterCover` | Update the net provision after cover in the loan account calculation table based on the provision amount and cover appropriated amount. |
| 🔴 5 | Update guarantee fund balance [CONFLICT] (`rule__5__21`) | `AvailableBalance, LastAppropriationDate` | Update the available balance and last appropriation date in the guarantee fund table. |
| 🔴 6 | Insert into collections queue [CONFLICT] (`rule__6__22`) | `AccountId, EscalationDate, Reason` | Insert entries into the collections queue for accounts with a guarantee cover shortfall. |
| 🟠 7 | Determine CoverAppropriatedAmount [MATCHED] (`deterministic_decision_2622_3465_0_coverappropriatedamount`) | `CoverAppropriatedAmount` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| 🟠 8 | Update CoverRequestedAmount [LLM_ONLY] (`rule__1`) | `CoverRequestedAmount` | Update the CoverRequestedAmount field in the PRO.LoanAccountCal table based on specific conditions. |
| 🟠 9 | Update CoverShortfallFlag [LLM_ONLY] (`rule__2`) | `CoverShortfallFlag` | Update the CoverShortfallFlag field in the PRO.LoanAccountCal table based on specific conditions. |
| 🟠 10 | Update CoverAppropriatedAmount [LLM_ONLY] (`rule__3`) | `CoverAppropriatedAmount` | Update the CoverAppropriatedAmount field in the PRO.LoanAccountCal table based on specific conditions. |
| 🟠 11 | Update NetProvisionAfterCover [LLM_ONLY] (`rule__4`) | `NetProvisionAfterCover` | Update the NetProvisionAfterCover field in the PRO.LoanAccountCal table based on specific conditions. |
| 🟠 12 | Insert into CoverLedgerStaging [LLM_ONLY] (`rule__5`) | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Insert data into the #CoverLedgerStaging table. |
| 🟠 13 | Insert into CollectionsQueue [LLM_ONLY] (`rule__6`) | `AccountId, EscalationDate, Reason` | Insert data into the PRO.CollectionsQueue table. |
| 🟢 14 | Reset cover requested amount to null [MATCHED] (`rule__1__7`) | `CoverRequestedAmount` | For accounts with a guarantee covered flag of 'Y' and a null provision amount, the cover requested amount is reset to null. |
| 🟢 15 | Set cover requested amount to provision amount [MATCHED] (`rule__2__8`) | `CoverRequestedAmount` | For accounts with a guarantee covered flag of 'Y', a non-null provision amount, and a positive provision amount, the cover requested amount… |
| 🔴 16 | Set cover appropriated amount to 0 and shortfall flag to 'Y' [CONFLICT] (`rule__3__9`) | `CoverAppropriatedAmount, CoverShortfallFlag` | If the fund renewal date is not null and the process date is within 7 days before the fund renewal date, for accounts with a guarantee cove… |
| 🟢 17 | Update cover appropriation amount [MATCHED] (`rule__1__10`) | `CoverAppropriatedAmount` | Calculate the cover appropriation amount for loan accounts based on their asset class and the available cover balance. |
| 🟢 18 | Calculate net provision after cover [MATCHED] (`rule__2__11`) | `NetProvisionAfterCover` | Calculate the net provision after cover for each loan account. |
| 🟢 19 | Update available balance in guarantee fund [MATCHED] (`rule__3__12`) | `AvailableBalance` | Update the available balance in the guarantee fund by subtracting the total appropriated amount from the loan accounts. |
| 🟠 20 | Merge into guarantee cover ledger [LLM_ONLY] (`rule__5__13`) | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Merge records into the guarantee cover ledger table. |
| 🔴 21 | Update available balance [CONFLICT] (`rule__3__16`) | `AvailableBalance` | Adjust the available balance of the guarantee fund by subtracting the sum of appropriated amounts from the available cover balance. |
| 🟢 22 | Calculate net provision after cover [MATCHED] (`rule__2__24`) | `NetProvisionAfterCover` | Calculate the net provision after cover for loan accounts. |
| 🟢 23 | Update available balance in guarantee fund [MATCHED] (`rule__3__25`) | `AvailableBalance` | Update the available balance in the guarantee fund after appropriation. |
| 🟠 24 | Insert into cover ledger staging [LLM_ONLY] (`rule__4__26`) | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Insert records into the cover ledger staging table. |
| 🟠 25 | Merge into guarantee cover ledger [LLM_ONLY] (`rule__5__27`) | `Target.AccountId, Source.AccountId, Target.CoverAppropriatedAmount, Source.CoverAppropriatedAmount, Target.NetProvisionAfterCover, Source.NetProvisionAfterCover, Target.LastAppropriationDate, AccountId, CoverAppropriatedAmount, NetProvisionAfterCover, FirstAppropriationDate, LastAppropriationDate` | Merge records into the guarantee cover ledger table. |
| 🔴 26 | Insert into collections queue [CONFLICT] (`rule__6__28`) | `AccountId, EscalationDate, Reason` | Insert records into the collections queue for accounts with a guarantee cover shortfall. |
| 🟠 27 | Insert into CoverLedgerStaging [LLM_ONLY] (`rule__5__33`) | `AccountId, CoverAppropriatedAmount, NetProvisionAfterCover` | Insert records into the '#CoverLedgerStaging' table with fields 'AccountId', 'CoverAppropriatedAmount', and 'NetProvisionAfterCover'. |
| 🟠 28 | Insert into CollectionsQueue [LLM_ONLY] (`rule__6__34`) | `AccountId, EscalationDate, Reason` | Insert records into the 'PRO.CollectionsQueue' table with fields 'AccountId', 'EscalationDate', and 'Reason'. |

## Source Traceability

<details>
<summary><strong>Show rule-to-source mapping</strong></summary>

| # | Rule | Source Evidence | Source Location | SQL Statements / Chunks | Technical References | Notes |
|---|---|---|---|---|---|---|
| 1 | Insert into staging table (rule__1__17) | INSERT INTO #CoverLedgerStaging (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover) SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverRequestedAmount > 0 | Not cited | 04_batch3_nested_block:chunk_text_23 | 04_batch3_nested_block:chunk_text_23 | Needs Review |
| 2 | Merge into guarantee cover ledger (rule__2__18) | MERGE PRO.GuaranteeCoverLedger AS Target USING #CoverLedgerStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.CoverAppropriatedAmount = Source.CoverAppropriatedAmount, Target.NetProvisionAfterCover = Source.NetProvisi… | Not cited | 04_batch3_nested_block | 04_batch3_nested_block | Needs Review |
| 3 | Update cover appropriated amount (rule__3__19) | UPDATE A SET A.CoverAppropriatedAmount = CASE WHEN A.AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE WHEN A.CoverRequestedAmount <= @AvailableCoverBalance THEN A.CoverRequestedAmount ELSE @AvailableCoverBalance END WHEN A.AssetClass = 'SUBSTANDARD' THEN CASE WHE… | Not cited | 04_batch3_nested_block:chunk_text_13 | 04_batch3_nested_block:chunk_text_13 | Verified |
| 4 | Update net provision after cover (rule__4__20) | UPDATE A SET A.NetProvisionAfterCover = A.ProvisionAmount - ISNULL(A.CoverAppropriatedAmount, 0) FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' | Not cited | 04_batch3_nested_block:chunk_text_19 | 04_batch3_nested_block:chunk_text_19 | Verified |
| 5 | Update guarantee fund balance (rule__5__21) | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - (SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y'), LastAppropriationDate = @ProcessDate WHERE FundId = 'GOVT_CGF' | Not cited | 04_batch3_nested_block:chunk_text_26 | 04_batch3_nested_block:chunk_text_26 | Needs Review |
| 6 | Insert into collections queue (rule__6__22) | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'GUARANTEE_COVER_SHORTFALL' FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverShortfallFlag = 'Y' | Not cited | 04_batch3_nested_block:embedded_09_37 | 04_batch3_nested_block:embedded_09_37 | Needs Review |
| 7 | Determine CoverAppropriatedAmount (deterministic_decision_2622_3465_0_coverappropriatedamount) | Not cited | source \| Lines 62-80 | Not cited | Not cited | Verified |
| 8 | Update CoverRequestedAmount (rule__1) | A.CoverRequestedAmount is updated | Not cited | Not cited | Not cited | Needs Review |
| 9 | Update CoverShortfallFlag (rule__2) | A.CoverShortfallFlag is updated | Not cited | Not cited | Not cited | Needs Review |
| 10 | Update CoverAppropriatedAmount (rule__3) | A.CoverAppropriatedAmount is updated | Not cited | Not cited | Not cited | Needs Review |
| 11 | Update NetProvisionAfterCover (rule__4) | A.NetProvisionAfterCover is updated | Not cited | Not cited | Not cited | Needs Review |
| 12 | Insert into CoverLedgerStaging (rule__5) | Data is inserted into #CoverLedgerStaging | Not cited | Not cited | Not cited | Needs Review |
| 13 | Insert into CollectionsQueue (rule__6) | Data is inserted into PRO.CollectionsQueue | Not cited | Not cited | Not cited | Needs Review |
| 14 | Reset cover requested amount to null (rule__1__7) | UPDATE A SET A.CoverRequestedAmount = NULL, A.CoverShortfallFlag = 'N' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NULL | Not cited | Not cited | Not cited | Verified |
| 15 | Set cover requested amount to provision amount (rule__2__8) | UPDATE A SET A.CoverRequestedAmount = A.ProvisionAmount FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NOT NULL AND A.ProvisionAmount > 0 | Not cited | Not cited | Not cited | Verified |
| 16 | Set cover appropriated amount to 0 and shortfall flag to 'Y' (rule__3__9) | IF @FundRenewalDate IS NOT NULL AND @ProcessDate >= DATEADD(DAY, -7, @FundRenewalDate) BEGIN UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' END | Not cited | Not cited | Not cited | Needs Review |
| 17 | Update cover appropriation amount (rule__1__10) | UPDATE A SET A.CoverAppropriatedAmount = CASE WHEN A.AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE WHEN A.CoverRequestedAmount <= @AvailableCoverBalance THEN A.CoverRequestedAmount ELSE @AvailableCoverBalance END WHEN A.AssetClass = 'SUBSTANDARD' THEN CASE WHE… | Not cited | Not cited | Not cited | Verified |
| 18 | Calculate net provision after cover (rule__2__11) | UPDATE A SET A.NetProvisionAfterCover = A.ProvisionAmount - ISNULL(A.CoverAppropriatedAmount, 0) FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' | Not cited | Not cited | Not cited | Verified |
| 19 | Update available balance in guarantee fund (rule__3__12) | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - (SELECT COALESCE(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y'), LastAppropriationDate = @ProcessDate WHERE FundId = 'GOVT_CGF' | Not cited | Not cited | Not cited | Verified |
| 20 | Merge into guarantee cover ledger (rule__5__13) | MERGE INTO PRO.GuaranteeCoverLedger AS Target USING (SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM #CoverLedgerStaging) AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.CoverAppropriatedAmount = Sou… | Not cited | Not cited | Not cited | Needs Review |
| 21 | Update available balance (rule__3__16) | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - (SELECT COALESCE(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y'), LastAppropriationDate = @ProcessDate WHERE FundId = 'GOVT_CGF' | Not cited | Not cited | Not cited | Needs Review |
| 22 | Calculate net provision after cover (rule__2__24) | UPDATE A SET A.NetProvisionAfterCover = A.ProvisionAmount - ISNULL(A.CoverAppropriatedAmount, 0) FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' | Not cited | Not cited | Not cited | Verified |
| 23 | Update available balance in guarantee fund (rule__3__25) | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - (SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y'), LastAppropriationDate = @ProcessDate WHERE FundId = 'GOVT_CGF' | Not cited | Not cited | Not cited | Verified |
| 24 | Insert into cover ledger staging (rule__4__26) | INSERT INTO #CoverLedgerStaging (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover) SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' | Not cited | Not cited | Not cited | Needs Review |
| 25 | Merge into guarantee cover ledger (rule__5__27) | MERGE INTO PRO.GuaranteeCoverLedger AS Target USING (SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM #CoverLedgerStaging) AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.CoverAppropriatedAmount = Sou… | Not cited | Not cited | Not cited | Needs Review |
| 26 | Insert into collections queue (rule__6__28) | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'GUARANTEE_COVER_SHORTFALL' FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverShortfallFlag = 'Y' | Not cited | Not cited | Not cited | Needs Review |
| 27 | Insert into CoverLedgerStaging (rule__5__33) | Insert into '#CoverLedgerStaging' table | Not cited | Not cited | Not cited | Verified |
| 28 | Insert into CollectionsQueue (rule__6__34) | Insert into 'PRO.CollectionsQueue' table | Not cited | Not cited | Not cited | Verified |

### Decision-Chain Branch Provenance

| Branch | Condition | Source Location |
|---|---|---|
| decision_2622_3465_0:branch_001 | (A.AssetClass IN ('DOUBTFUL', 'LOSS')) AND (A.CoverRequestedAmount <= @AvailableCoverBalance) | samples/16_Guarantee_Cover_Appropriation.sql \| Lines 62-80 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_13 |
| decision_2622_3465_0:branch_002 | A.AssetClass IN ('DOUBTFUL', 'LOSS') | samples/16_Guarantee_Cover_Appropriation.sql \| Lines 62-80 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_13 |
| decision_2622_3465_0:branch_003 | (A.AssetClass = 'SUBSTANDARD') AND (A.CoverRequestedAmount <= @AvailableCoverBalance * 0.5) | samples/16_Guarantee_Cover_Appropriation.sql \| Lines 62-80 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_13 |
| decision_2622_3465_0:branch_004 | A.AssetClass = 'SUBSTANDARD' | samples/16_Guarantee_Cover_Appropriation.sql \| Lines 62-80 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_13 |
| decision_2622_3465_0:branch_005 | ELSE | samples/16_Guarantee_Cover_Appropriation.sql \| Lines 62-80 \| Chunk 04_batch3_nested_block \| Statement 04_batch3_nested_block:chunk_text_13 |
| decision_chain_002:branch_001 | A.AssetClass IN ('DOUBTFUL', 'LOSS') | source |
| decision_chain_002:branch_002 | A.AssetClass = 'SUBSTANDARD' | source |
| decision_chain_002:branch_003 | ELSE | source |

_Source evidence is the literal technical text carried through the pipeline; Source Location is derived deterministically from chunk and statement provenance when available; SQL Statements / Chunks and Technical References point back to the extracted chunk ids and statement references used by the guardrails. Technical references that repeat the same table/operation/target-columns are shown once._
</details>

## Completeness Ledger

- **Executable constructs:** 108
- **Disposition:** covered_by_rule=87, technical_only=2, uncovered=19

| Construct | Status | Source location | Statement / chunk | Evidence |
|---|---|---|---|---|
| STATEMENT | uncovered | Lines 1-1 | 00_batch0_declaration:chunk_text_01, 00_batch0_declaration | USE [DEMO_MISDB] |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:chunk_text_01, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 01_batch1_declaration:embedded_01_02, 01_batch1_declaration | SET ANSI_NULLS ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:chunk_text_01, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| SET | uncovered | Lines 1-1 | 02_batch2_declaration:embedded_01_02, 02_batch2_declaration | SET QUOTED_IDENTIFIER ON |
| STATEMENT | uncovered | Lines 1-2 | 03_batch3_main_body:chunk_text_01, 03_batch3_main_body | BEGIN SET NOCOUNT ON |
| STATEMENT | covered_by_rule | Lines 1-1 | 04_batch3_nested_block:chunk_text_01, 04_batch3_nested_block | BEGIN TRY |
| SELECT | covered_by_rule | Lines 3-3 | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| SELECT | covered_by_rule | Lines 4-4 | 04_batch3_nested_block:chunk_text_03, 04_batch3_nested_block | DECLARE @AvailableCoverBalance DECIMAL(18,2) = (SELECT AvailableBalance FROM PRO.GuaranteeFund WHERE FundId = 'GOVT_CGF') |
| SELECT | covered_by_rule | Lines 5-8 | 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block | DECLARE @FundRenewalDate DATE = (SELECT RenewalDate FROM PRO.GuaranteeFund WHERE FundId = 'GOVT_CGF') -- Rule 1: NULL check - accounts flagged guarantee-covered but with -- no provisioning requirement recorded at all cannot be assessed |
| UPDATE | covered_by_rule | Lines 9-17 | 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block | UPDATE A SET A.CoverRequestedAmount = NULL, A.CoverShortfallFlag = 'N' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NULL -- Rule 2: only guaranteed accounts with a positive provisioning -- require... |
| UPDATE | covered_by_rule | Lines 18-26 | 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block | UPDATE A SET A.CoverRequestedAmount = A.ProvisionAmount FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NOT NULL AND A.ProvisionAmount > 0 -- Rule 2: sequential IF/ELSE - the fund must not be within... |
| STATEMENT | covered_by_rule | Lines 27-27 | 04_batch3_nested_block:chunk_text_07, 04_batch3_nested_block | IF @FundRenewalDate IS NOT NULL AND @ProcessDate >= DATEADD(DAY, -7, @FundRenewalDate) |
| STATEMENT | covered_by_rule | Lines 1-1 | 04_batch3_nested_block:chunk_text_08, 04_batch3_nested_block | BEGIN |
| UPDATE | covered_by_rule | Lines 29-34 | 04_batch3_nested_block:chunk_text_09, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.CoverRequestedAmount > 0 |
| STATEMENT | covered_by_rule | Lines 35-35 | 04_batch3_nested_block:chunk_text_10, 04_batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 36-36 | 04_batch3_nested_block:chunk_text_11, 04_batch3_nested_block | ELSE IF @AvailableCoverBalance IS NOT NULL AND @AvailableCoverBalance > 0 |
| STATEMENT | covered_by_rule | Lines 37-40 | 04_batch3_nested_block:chunk_text_12, 04_batch3_nested_block | BEGIN -- Rule 3: nested condition on both asset class and whether the -- fund can cover it in full - accounts in the worse asset -- classes are appropriated first when balance is insufficient |
| UPDATE | covered_by_rule | Lines 41-58 | 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = CASE WHEN A.AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE WHEN A.CoverRequestedAmount <= @AvailableCoverBalance THEN A.CoverRequestedAmount ELSE @AvailableCoverBalance END WHEN A.AssetClass = 'SUBS... |
| STATEMENT | covered_by_rule | Lines 35-35 | 04_batch3_nested_block:chunk_text_14, 04_batch3_nested_block | END |
| STATEMENT | covered_by_rule | Lines 25-25 | 04_batch3_nested_block:chunk_text_15, 04_batch3_nested_block | ELSE |
| STATEMENT | covered_by_rule | Lines 61-63 | 04_batch3_nested_block:chunk_text_16, 04_batch3_nested_block | BEGIN -- Rule 4: no fund balance available this cycle - nothing is -- appropriated, and the shortfall is flagged |
| UPDATE | covered_by_rule | Lines 29-34 | 04_batch3_nested_block:chunk_text_17, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.CoverRequestedAmount > 0 |
| STATEMENT | covered_by_rule | Lines 70-72 | 04_batch3_nested_block:chunk_text_18, 04_batch3_nested_block | END -- Rule 5: net provisioning required after appropriation |
| UPDATE | covered_by_rule | Lines 73-76 | 04_batch3_nested_block:chunk_text_19, 04_batch3_nested_block | UPDATE A SET A.NetProvisionAfterCover = A.ProvisionAmount - ISNULL(A.CoverAppropriatedAmount, 0) FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' |
| STATEMENT | covered_by_rule | Lines 78-78 | 04_batch3_nested_block:chunk_text_20, 04_batch3_nested_block | IF OBJECT_ID('tempdb..#CoverLedgerStaging') IS NOT NULL |
| STATEMENT | covered_by_rule | Lines 79-79 | 04_batch3_nested_block:chunk_text_21, 04_batch3_nested_block | DROP TABLE #CoverLedgerStaging |
| INSERT | covered_by_rule | Lines 81-89 | 04_batch3_nested_block:chunk_text_22, 04_batch3_nested_block | CREATE TABLE #CoverLedgerStaging ( AccountId VARCHAR(20), CoverAppropriatedAmount DECIMAL(18,2), NetProvisionAfterCover DECIMAL(18,2) ) -- Rule 6: conditional INSERT - only accounts actually processed -- for cover this cycle are staged |
| INSERT | covered_by_rule | Lines 90-97 | 04_batch3_nested_block:chunk_text_23, 04_batch3_nested_block | INSERT INTO #CoverLedgerStaging (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover) SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverRequestedAmo... |
| MERGE | covered_by_rule | Lines 98-110 | 04_batch3_nested_block:chunk_text_24, 04_batch3_nested_block | MERGE PRO.GuaranteeCoverLedger AS Target USING #CoverLedgerStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.CoverAppropriatedAmount = Source.CoverAppropriatedAmount, Target.NetProvisionAfterCov... |
| INSERT | covered_by_rule | Lines 111-117 | 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'GUARANTEE_COVER_SHORTFALL' FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverShortfallFlag = 'Y' -- Rule 9: record the... |
| UPDATE | covered_by_rule | Lines 118-125 | 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - ( SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' ), LastAppropriationDate = @ProcessDate WHERE FundId = 'GO... |
| UPDATE | covered_by_rule | Lines 127-129 | 04_batch3_nested_block:chunk_text_27, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Guarantee_Cover_Appropriation' |
| STATEMENT | covered_by_rule | Lines 131-131 | 04_batch3_nested_block:chunk_text_28, 04_batch3_nested_block | END TRY |
| UPDATE | covered_by_rule | Lines 9-17 | 04_batch3_nested_block:embedded_01_29, 04_batch3_nested_block | UPDATE A SET A.CoverRequestedAmount = NULL, A.CoverShortfallFlag = 'N' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NULL -- Rule 2: only guaranteed accounts with a positive provisioning -- require... |
| UPDATE | covered_by_rule | Lines 18-26 | 04_batch3_nested_block:embedded_02_30, 04_batch3_nested_block | UPDATE A SET A.CoverRequestedAmount = A.ProvisionAmount FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NOT NULL AND A.ProvisionAmount > 0 -- Rule 2: sequential IF/ELSE - the fund must not be within... |
| UPDATE | covered_by_rule | Lines 29-34 | 04_batch3_nested_block:embedded_03_31, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.CoverRequestedAmount > 0 |
| UPDATE | covered_by_rule | Lines 41-58 | 04_batch3_nested_block:embedded_04_32, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = CASE WHEN A.AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE WHEN A.CoverRequestedAmount <= @AvailableCoverBalance THEN A.CoverRequestedAmount ELSE @AvailableCoverBalance END WHEN A.AssetClass = 'SUBS... |
| UPDATE | covered_by_rule | Lines 29-34 | 04_batch3_nested_block:embedded_05_33, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.CoverRequestedAmount > 0 |
| UPDATE | covered_by_rule | Lines 73-76 | 04_batch3_nested_block:embedded_06_34, 04_batch3_nested_block | UPDATE A SET A.NetProvisionAfterCover = A.ProvisionAmount - ISNULL(A.CoverAppropriatedAmount, 0) FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' |
| INSERT | covered_by_rule | Lines 90-97 | 04_batch3_nested_block:embedded_07_35, 04_batch3_nested_block | INSERT INTO #CoverLedgerStaging (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover) SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverRequestedAmo... |
| MERGE | covered_by_rule | Lines 98-110 | 04_batch3_nested_block:embedded_08_36, 04_batch3_nested_block | MERGE PRO.GuaranteeCoverLedger AS Target USING #CoverLedgerStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.CoverAppropriatedAmount = Source.CoverAppropriatedAmount, Target.NetProvisionAfterCov... |
| INSERT | covered_by_rule | Lines 111-117 | 04_batch3_nested_block:embedded_09_37, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'GUARANTEE_COVER_SHORTFALL' FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverShortfallFlag = 'Y' -- Rule 9: record the... |
| UPDATE | covered_by_rule | Lines 118-125 | 04_batch3_nested_block:embedded_10_38, 04_batch3_nested_block | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - ( SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' ), LastAppropriationDate = @ProcessDate WHERE FundId = 'GO... |
| UPDATE | covered_by_rule | Lines 127-129 | 04_batch3_nested_block:embedded_11_39, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Guarantee_Cover_Appropriation' |
| STATEMENT | uncovered | Lines 1-2 | 05_batch3_exception:chunk_text_01, 05_batch3_exception | BEGIN CATCH -- Exception handling: record the failure for operations to investigate |
| UPDATE | uncovered | Lines 3-5 | 05_batch3_exception:chunk_text_02, 05_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Guarantee_Cover_Appropriation' |
| STATEMENT | uncovered | Lines 6-6 | 05_batch3_exception:chunk_text_03, 05_batch3_exception | END CATCH |
| SET | uncovered | Lines 7-7 | 05_batch3_exception:chunk_text_04, 05_batch3_exception | SET NOCOUNT OFF |
| STATEMENT | covered_by_rule | Lines 6-6 | 05_batch3_exception:chunk_text_05, 05_batch3_exception | END |
| UPDATE | uncovered | Lines 3-5 | 05_batch3_exception:embedded_01_06, 05_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Guarantee_Cover_Appropriation' |
| SET | uncovered | Lines 7-7 | 05_batch3_exception:embedded_02_07, 05_batch3_exception | SET NOCOUNT OFF |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block:chunk_text_02, 04_batch3_nested_block | DECLARE @ProcessDate DATE = (SELECT [Date] FROM SysDayMatrix WHERE TimeKey = @TimeKey) |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:chunk_text_03, 04_batch3_nested_block:chunk_text_03, 04_batch3_nested_block | DECLARE @AvailableCoverBalance DECIMAL(18,2) = (SELECT AvailableBalance FROM PRO.GuaranteeFund WHERE FundId = 'GOVT_CGF') |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block:chunk_text_04, 04_batch3_nested_block | DECLARE @FundRenewalDate DATE = (SELECT RenewalDate FROM PRO.GuaranteeFund WHERE FundId = 'GOVT_CGF') -- Rule 1: NULL check - accounts flagged guarantee-covered but with -- no provisioning requirement recorded at all cannot be assessed |
| UPDATE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block:chunk_text_05, 04_batch3_nested_block | UPDATE A SET A.CoverRequestedAmount = NULL, A.CoverShortfallFlag = 'N' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NULL -- Rule 2: only guaranteed accounts with a positive provisioning -- require... |
| UPDATE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block:chunk_text_06, 04_batch3_nested_block | UPDATE A SET A.CoverRequestedAmount = A.ProvisionAmount FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NOT NULL AND A.ProvisionAmount > 0 -- Rule 2: sequential IF/ELSE - the fund must not be within... |
| UPDATE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_09, 04_batch3_nested_block:chunk_text_09, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.CoverRequestedAmount > 0 |
| UPDATE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = CASE WHEN A.AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE WHEN A.CoverRequestedAmount <= @AvailableCoverBalance THEN A.CoverRequestedAmount ELSE @AvailableCoverBalance END WHEN A.AssetClass = 'SUBS... |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:chunk_text_17, 04_batch3_nested_block:chunk_text_17, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.CoverRequestedAmount > 0 |
| UPDATE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_19, 04_batch3_nested_block:chunk_text_19, 04_batch3_nested_block | UPDATE A SET A.NetProvisionAfterCover = A.ProvisionAmount - ISNULL(A.CoverAppropriatedAmount, 0) FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' |
| INSERT_TEMP | technical_only | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_23, 04_batch3_nested_block:chunk_text_23, 04_batch3_nested_block | INSERT INTO #CoverLedgerStaging (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover) SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverRequestedAmo... |
| MERGE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_24, 04_batch3_nested_block:chunk_text_24, 04_batch3_nested_block | MERGE PRO.GuaranteeCoverLedger AS Target USING #CoverLedgerStaging AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.CoverAppropriatedAmount = Source.CoverAppropriatedAmount, Target.NetProvisionAfterCov... |
| INSERT | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block:chunk_text_25, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'GUARANTEE_COVER_SHORTFALL' FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverShortfallFlag = 'Y' -- Rule 9: record the... |
| UPDATE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - ( SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' ), LastAppropriationDate = @ProcessDate WHERE FundId = 'GO... |
| READ | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block:chunk_text_26, 04_batch3_nested_block | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - ( SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' ), LastAppropriationDate = @ProcessDate WHERE FundId = 'GO... |
| UPDATE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 22-152 | 04_batch3_nested_block:chunk_text_27, 04_batch3_nested_block:chunk_text_27, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Guarantee_Cover_Appropriation' |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_01_29, 04_batch3_nested_block:embedded_01_29, 04_batch3_nested_block | UPDATE A SET A.CoverRequestedAmount = NULL, A.CoverShortfallFlag = 'N' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NULL -- Rule 2: only guaranteed accounts with a positive provisioning -- require... |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_02_30, 04_batch3_nested_block:embedded_02_30, 04_batch3_nested_block | UPDATE A SET A.CoverRequestedAmount = A.ProvisionAmount FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' AND A.ProvisionAmount IS NOT NULL AND A.ProvisionAmount > 0 -- Rule 2: sequential IF/ELSE - the fund must not be within... |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_04_32, 04_batch3_nested_block:embedded_04_32, 04_batch3_nested_block | UPDATE A SET A.CoverAppropriatedAmount = CASE WHEN A.AssetClass IN ('DOUBTFUL', 'LOSS') THEN CASE WHEN A.CoverRequestedAmount <= @AvailableCoverBalance THEN A.CoverRequestedAmount ELSE @AvailableCoverBalance END WHEN A.AssetClass = 'SUBS... |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_06_34, 04_batch3_nested_block:embedded_06_34, 04_batch3_nested_block | UPDATE A SET A.NetProvisionAfterCover = A.ProvisionAmount - ISNULL(A.CoverAppropriatedAmount, 0) FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_07_35, 04_batch3_nested_block:embedded_07_35, 04_batch3_nested_block | INSERT INTO #CoverLedgerStaging (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover) SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverRequestedAmo... |
| INSERT_TEMP | technical_only | unavailable | 04_batch3_nested_block:embedded_07_35, 04_batch3_nested_block:embedded_07_35, 04_batch3_nested_block | INSERT INTO #CoverLedgerStaging (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover) SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverRequestedAmo... |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_09_37, 04_batch3_nested_block:embedded_09_37, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'GUARANTEE_COVER_SHORTFALL' FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverShortfallFlag = 'Y' -- Rule 9: record the... |
| INSERT | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_09_37, 04_batch3_nested_block:embedded_09_37, 04_batch3_nested_block | INSERT INTO PRO.CollectionsQueue (AccountId, EscalationDate, Reason) SELECT AccountId, @ProcessDate, 'GUARANTEE_COVER_SHORTFALL' FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' AND CoverShortfallFlag = 'Y' -- Rule 9: record the... |
| READ | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_10_38, 04_batch3_nested_block:embedded_10_38, 04_batch3_nested_block | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - ( SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' ), LastAppropriationDate = @ProcessDate WHERE FundId = 'GO... |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_10_38, 04_batch3_nested_block:embedded_10_38, 04_batch3_nested_block | UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - ( SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y' ), LastAppropriationDate = @ProcessDate WHERE FundId = 'GO... |
| UPDATE | covered_by_rule | unavailable | 04_batch3_nested_block:embedded_11_39, 04_batch3_nested_block:embedded_11_39, 04_batch3_nested_block | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'Y', ERRORDATE = NULL, ERRORDESCRIPTION = NULL, COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Guarantee_Cover_Appropriation' |
| UPDATE | uncovered | samples/16_Guarantee_Cover_Appropriation.sql / Lines 153-160 | 05_batch3_exception:chunk_text_02, 05_batch3_exception:chunk_text_02, 05_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Guarantee_Cover_Appropriation' |
| UPDATE | uncovered | unavailable | 05_batch3_exception:embedded_01_06, 05_batch3_exception:embedded_01_06, 05_batch3_exception | UPDATE PRO.ACLRUNNINGPROCESSSTATUS SET COMPLETED = 'N', ERRORDATE = GETDATE(), ERRORDESCRIPTION = ERROR_MESSAGE(), COUNT = ISNULL(COUNT, 0) + 1 WHERE RUNNINGPROCESSNAME = 'Guarantee_Cover_Appropriation' |
| IF_BRANCH | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 62-80 | 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block | (A.AssetClass IN ('DOUBTFUL', 'LOSS')) AND (A.CoverRequestedAmount <= @AvailableCoverBalance) |
| IF_BRANCH | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 62-80 | 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block | A.AssetClass IN ('DOUBTFUL', 'LOSS') |
| IF_BRANCH | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 62-80 | 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block | (A.AssetClass = 'SUBSTANDARD') AND (A.CoverRequestedAmount <= @AvailableCoverBalance * 0.5) |
| IF_BRANCH | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 62-80 | 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block | A.AssetClass = 'SUBSTANDARD' |
| ELSE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql / Lines 62-80 | 04_batch3_nested_block:chunk_text_13, 04_batch3_nested_block | ELSE |
| IF_BRANCH | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql | full_source | A.AssetClass IN ('DOUBTFUL', 'LOSS') |
| IF_BRANCH | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql | full_source | A.AssetClass = 'SUBSTANDARD' |
| ELSE | covered_by_rule | samples/16_Guarantee_Cover_Appropriation.sql | full_source | ELSE |
| IF | covered_by_rule | Lines 48-48 | unavailable | IF @FundRenewalDate IS NOT NULL AND @ProcessDate >= DATEADD(DAY, -7, @FundRenewalDate) |
| ELSE | uncovered | Lines 57-57 | unavailable | ELSE IF @AvailableCoverBalance IS NOT NULL AND @AvailableCoverBalance > 0 |
| IF | uncovered | Lines 57-57 | unavailable | ELSE IF @AvailableCoverBalance IS NOT NULL AND @AvailableCoverBalance > 0 |
| CASE | covered_by_rule | Lines 64-64 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 65-65 | unavailable | WHEN A.AssetClass IN ( , ) THEN |
| CASE | covered_by_rule | Lines 66-66 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 67-67 | unavailable | WHEN A.CoverRequestedAmount <= @AvailableCoverBalance THEN A.CoverRequestedAmount |
| ELSE | covered_by_rule | Lines 68-68 | unavailable | ELSE @AvailableCoverBalance |
| CASE_BRANCH | covered_by_rule | Lines 70-70 | unavailable | WHEN A.AssetClass = THEN |
| CASE | covered_by_rule | Lines 71-71 | unavailable | CASE |
| CASE_BRANCH | covered_by_rule | Lines 72-72 | unavailable | WHEN A.CoverRequestedAmount <= @AvailableCoverBalance * 0.5 THEN A.CoverRequestedAmount |
| ELSE | covered_by_rule | Lines 73-73 | unavailable | ELSE @AvailableCoverBalance * 0.5 |
| ELSE | covered_by_rule | Lines 75-75 | unavailable | ELSE 0 |
| ELSE | covered_by_rule | Lines 81-81 | unavailable | ELSE |
| IF | uncovered | Lines 99-99 | unavailable | IF OBJECT_ID( ) IS NOT NULL |
| CASE_BRANCH | covered_by_rule | Lines 122-122 | unavailable | WHEN MATCHED THEN |
| CASE_BRANCH | covered_by_rule | Lines 127-127 | unavailable | WHEN NOT MATCHED BY TARGET THEN |
| CALCULATION | covered_by_rule | Lines 141-141 | unavailable | SELECT ISNULL(SUM(CoverAppropriatedAmount), 0) |
| CATCH | uncovered | Lines 153-153 | unavailable | BEGIN CATCH |
| CATCH | uncovered | Lines 158-158 | unavailable | END CATCH |

## Confirmed Statement Dependencies

The following dependencies are confirmed from exact table/field matches and source order:

| Relationship | From | To | Confidence |
|---|---|---|---|
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_29 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_26 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_29 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_29 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_01_29 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_05 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_26 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_05 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_05 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_05 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_06 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_26 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_06 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_06 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_06 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_09 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_26 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_09 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_09 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_09 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_13 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_26 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_13 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_13 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_13 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_19 / PRO.LoanAccountCal | 04_batch3_nested_block:chunk_text_26 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_19 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_19 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_19 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_23 / #CoverLedgerStaging | 04_batch3_nested_block:embedded_07_35 / #CoverLedgerStaging | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_25 / PRO.CollectionsQueue | 04_batch3_nested_block:embedded_09_37 / PRO.CollectionsQueue | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_02_30 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_02_30 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_02_30 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_17 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_17 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:chunk_text_17 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_04_32 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_04_32 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_04_32 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_06_34 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_07_35 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_06_34 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_09_37 / PRO.LoanAccountCal | high |
| table_write_to_later_use | 04_batch3_nested_block:embedded_06_34 / PRO.LoanAccountCal | 04_batch3_nested_block:embedded_10_38 / PRO.LoanAccountCal | high |

Unresolved dependency candidates: 24. They were not supplied as confirmed dependencies.

## Rule Provenance Summary

- **Total business rules:** 28
- **By rule type:** deterministic_decision_table = 1, explicit = 27
- **By validation status:** unverified = 16, verified = 12

_This count reflects every individually traceable rule (one per source statement/field, for full auditability). The business report may show a smaller number, because closely related rules that apply the same pattern to several fields (e.g. "reset each of these six DPD fields to zero if negative") are presented there as one combined rule for readability. Every rule counted here is still individually traceable in the Source Traceability table below - none are dropped, only grouped for display._

_Rules marked **unverified** could not be matched back to the technical extraction or source code - this specific claim remains unresolved and should not yet be treated as a confirmed business rule._

## Reconciliation Summary

- **Matched facts:** 19
- **Deterministic-only facts:** 2
- **LLM-only claims:** 12
- **Conflicts:** 13
- **Unresolved items:** 0
- **Review required:** Yes

### Review Items

- `CONFLICT` tables_written (`recon_456a863962fe`): full_source
- `CONFLICT` tables_written (`recon_456a863962fe`): full_source
- `CONFLICT` tables_written (`recon_456a863962fe`): full_source
- `CONFLICT` tables_written (`recon_456a863962fe`): full_source
- `CONFLICT` tables_written (`recon_456a863962fe`): full_source

## Quality Summary

- **Overall status:** REVIEW_REQUIRED
- **Quality score:** 72.38207547169812/100
- **Statement coverage:** 30 / 52 (57.7%)
- **Rule grounding coverage:** 16 / 28 (57.1%)
- **Decision-chain coverage:** 5 / 5 branches (100.0%)
- **Conflicts:** 13
- **Contradictions:** 18
- **Review required items:** 43
- **Review required:** Yes

Statement parse success is below the preferred threshold.; Rule grounding coverage is below the preferred threshold.

### Contradictions

- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `MEDIUM` Field Conflict on `source`: Synthesized affected fields do not match deterministic SQL/AST evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.
- `HIGH` Condition Conflict on `source`: Synthesized condition conflicts with deterministic predicate evidence.

_Quality is derived deterministically from parse success, grounding, conflicts, contradictions, and dialect support._

## Pipeline Diagnostics

- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.CoverRequestedAmount is updated
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.CoverShortfallFlag is updated
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.CoverAppropriatedAmount is updated
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: A.NetProvisionAfterCover is updated
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Data is inserted into #CoverLedgerStaging
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Data is inserted into PRO.CollectionsQueue
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: IF @FundRenewalDate IS NOT NULL AND @ProcessDate >= DATEADD(DAY, -7, @FundRenewalDate) BEGIN UPDATE A SET A.CoverAppropriatedAmount = 0, A.CoverShortfallFlag = 'Y' FROM PRO.LoanAccountCal A WHERE A.GuaranteeCoveredFlag = 'Y' END
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: UPDATE PRO.GuaranteeFund SET AvailableBalance = @AvailableCoverBalance - (SELECT COALESCE(SUM(CoverAppropriatedAmount), 0) FROM PRO.LoanAccountCal WHERE GuaranteeCoveredFlag = 'Y'), LastAppropriationDate = @ProcessDate WHERE FundId = 'GOVT_CGF'
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.GuaranteeCoverLedger AS Target USING (SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM #CoverLedgerStaging) AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.CoverAppropriatedAmount = Source.CoverAppropriatedAmount, Target.NetProvisionAfterCover = Source.NetProvisionAfterCover WHEN NOT MATCHED BY TARGET THEN INSERT (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover) VALUES (Source.AccountId, Source.CoverAppropriatedAmount, Source.NetProvisionAfterCover)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: MERGE INTO PRO.GuaranteeCoverLedger AS Target USING (SELECT AccountId, CoverAppropriatedAmount, NetProvisionAfterCover FROM #CoverLedgerStaging) AS Source ON Target.AccountId = Source.AccountId WHEN MATCHED THEN UPDATE SET Target.CoverAppropriatedAmount = Source.CoverAppropriatedAmount, Target.NetProvisionAfterCover = Source.NetProvisionAfterCover WHEN NOT MATCHED BY TARGET THEN INSERT (AccountId, CoverAppropriatedAmount, NetProvisionAfterCover, LastAppropriationDate) VALUES (Source.AccountId, Source.CoverAppropriatedAmount, Source.NetProvisionAfterCover, @ProcessDate)
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Insert into '#CoverLedgerStaging' table
- Could not trace the stated source evidence back to a successfully parsed technical extraction record: Insert into 'PRO.CollectionsQueue' table
- Synthesized in 7 section(s) aligned to extraction chunk boundaries because the object exceeded the single-call output-token ceiling; sections were merged into this report.
