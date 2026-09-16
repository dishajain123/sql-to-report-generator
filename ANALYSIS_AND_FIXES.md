# Analysis and Fixes — SQL → Business Rules Report Generator

**Date:** 2026-09-16  
**Repo:** `/Users/dishajain/Desktop/logic_rules_extractor`  
**Live model used for sample validation:** `bedrock` / `amazon.nova-lite-v1:0`  
**Not run (no credentials configured):** `openai/gpt-oss-120b`

---

## A. Codebase Architecture Analysis

### Real execution flow (`LogicRulesExtractorPipeline.run`)

Entry points: `main.py` (CLI), `app.py` (Streamlit), `src/batch/batch_runner.py`.

| Stage | What it does | Primary files / functions | Data in → out | Report impact |
|---|---|---|---|---|
| 1. Input guardrails | Truncate oversized input; flag injection; strip BOM/control chars | `src/ingestion/guardrails.py` (`run_input_guardrails`) | raw `.sql` → `clean_code` + warnings | Truncation banner when wired |
| 2. Dialect detection | Score Oracle vs T-SQL; reject Postgres | `src/dialect/detector.py` (`detect_dialect`) | clean code → `concrete_dialect` | At-a-glance dialect; unsupported → empty analysis |
| 3. Ingest / chunk | Object metadata, procedural chunks, called procs, hardcoded dates | `src/ingestion/ingestion.py` (`CodeIngestionAgent.ingest_text`) | clean code → `IngestionResult` | Title, inputs, called procs, hardcoded values |
| 4. RAG + extraction | KB retrieve; LLM technical JSON (single-pass or chunked) | `src/retrieval/retriever.py`, `src/extraction/logic_extractor.py`, `src/prompts/logic_extraction.yaml` | chunks → `ChunkExtraction[]` | Feeds synthesis; tables/calcs |
| 5a. Merge + deterministic enrich | Overlay CASE/IF chains, table ops, calcs, dependencies, provenance | `pipeline.py`, `src/validation/semantic_validation.py`, `src/parsing/decision_tables.py`, `src/parsing/technical_sql_ops.py`, `src/validation/dependencies.py` | extractions → `merged_extraction` | Decision Logic floors; Data Touched |
| 5b. Synthesis | LLM business JSON; sectioned merge for large objects | `src/synthesis/rule_synthesizer.py`, `src/prompts/rule_synthesis.yaml` | extraction → `SynthesisResult` | Purpose, flow, business rules |
| 5c. Coverage / post-filters | Coverage revise; `ensure_decision_chain_coverage`; `ensure_statement_coverage`; operational/tautology/cleanup filters; consolidate; blank-outcome backfill | `pipeline.py`, `rule_synthesizer.py`, `src/validation/coverage_check.py` | rules → cleaned rules | Completeness without inventing business meaning |
| 6. Reconciliation + IR | Match claims to deterministic evidence; build `CanonicalBusinessIR` | `src/validation/reconciliation.py`, `src/ir/canonical_ir.py` | synthesis + extraction → IR | Verification quality; display projection |
| 7. Format | Business Markdown + verification companion | `src/output/report_formatter.py` | IR + synthesis → two Markdown docs | Final user-facing report |

### Strengths

- Strong deterministic decision-chain extraction (CASE, nested, T-SQL IF/ELSE IF, sequential updates).
- Defense-in-depth: coverage floors, content-duplicate suppression, operational-status filtering.
- Clear split between business report and verification report (no review/confidence language in the business doc by design).
- Malformed LLM JSON retries and degraded-run telemetry (telemetry tracked; business banner intentionally not shown per prior client direction).

### Weaknesses (pre-fix / residual)

1. Many post-synthesis transforms make reasoning hard (ensure → filter → IR → formatter suppress).
2. `ground_business_rules_against_extraction` computed provenance then discarded copies (IDs later from `unique_rule_ids`).
3. IR rebuild path previously omitted `extract_tsql_if_elseif_chains` when no structural chains were present.
4. Presentational `[UNREACHABLE …]` annotations broke IR condition matching → blank Result cells.
5. Evaluation-order boilerplate leaked into Business Purpose / rule titles.
6. Model could emit CREATE #temp / read-only SELECT as “business rules.”
7. Two complete model paraphrases of one CASE could both survive when both carried `decision_block_id`.

---

## B. Sample Analysis (01–18)

Findings below are from source inspection plus a live Bedrock batch (`samples/output/validation_01_18/batch_20260916_184052_266320/`, all **18/18 OK**). Only actual issues are listed.

| Sample | Business logic | Current issue | Root cause phase | Fix | Verification |
| ------ | -------------- | ------------- | ---------------- | --- | ------------ |
| 01 NPA Classification | DPD asset-class ladder, NPA flag, provision, restructure watch | Minor model prose variance; core ladders present | Synthesis (LLM) | Deterministic CASE coverage already floors ladders | Live OK; deterministic tests pass |
| 02 SMA Stage Marking | SMA_0/1/2 by overdue; facility reasons; cure clear | ELSE NULL vs cure can look contradictory if eligibility lost | Formatter eligibility display (prior) | Existing “eligibility not documented” wording | Live OK |
| 03 Provision % | Base % by class; +10 unsecured; cap; senior review | None material in live run | — | — | Live OK |
| 04 Asset Class Upgrade | 90-day cure IF EXISTS; provision release; reclass | IF EXISTS control-flow can be narrated as per-row | Synthesis (LLM) | T-SQL IF extractor + annotations | Live OK |
| 05 NPA Movement Audit | Change detect; customer MIN(AssetClass); snapshot refresh | Alphabetical MIN severity limitation is SQL-faithful | — | Report must not invent severity order | Live OK |
| 06 GovtGuar Appropriation | Processing flag; BP/BD pro-rata; ##temps | Production noise; window NULL edge | Extraction/synthesis | Deterministic ops + grounding | Live OK |
| 07 DPD Bucket | Full age → penal → grace IF → stage → MERGE → queue → audit | **Fixed:** blank `NOT_APPLICABLE` result; boilerplate purpose; CREATE #temp / read-as-rule; duplicate Classify/Penal from assignment-empty LLM `decision_chain_NNN` shells | IR match; merge; ensure; formatter | See §C | Live batch `validation_07_18/batch_20260916_192607_525235`: **1 Classify, 1 Penal**; blank cells / CREATE #temp gone |
| 08 Restructuring Eligibility | Scheme gate; nested eligibility; tenure; MERGE | Scheme nearly always closed (sample design) | — | Faithful reporting of dead/edge branch | Live OK |
| 09 Provision Coverage Merge | Ratio ladder; quarter-end suffix; 50% flag | ELSE no-op branch | Synthesis | Deterministic CASE coverage | Live OK |
| 10 Late Fee | Grace; fee ladder; escalate | None material | — | — | Live OK |
| 11 Collateral Valuation | Freshness; shortfall; month-based priority | Two priority ladders | Decision chains | Deterministic coverage | Live OK |
| 12 Customer Risk Score | Weighted score; tiers; always-true review IF | Dead ELSE branch | Synthesis | Faithful IF/ELSE extraction | Live OK |
| 13 Account Closure | Close vs reject tree; dispute grace | Sequential overwrite order | — | Ordered rules / decision tables | Live OK |
| 14 Interest Accrual | Day count; promo EXISTS; capitalize | Global EXISTS may read as per-row | Synthesis | IF EXISTS annotations | Live OK |
| 15 NPA Upgrade Watchlist | Class wait days; day-1 gate; DELETE/MERGE | None material | — | — | Live OK |
| 16 Guarantee Cover | Renewal blackout; priority caps; fund drawdown | Per-account cap vs fund (SQL shape) | — | Do not invent FIFO | Live OK |
| 17 Dishonour Penalty | Penalty ladder; 6-month suspend; CATCH upsert | Richer CATCH | Exception filter | Keep business vs ops separate | Live OK |
| 18 Batch Reconciliation | Outcome tree; retry once; chronic CRITICAL | Ops domain (not credit risk) | — | Still a valid business report | Live OK |

---

## C. Root Cause & Fix Report

### Fixes implemented in this pass

| Issue | Root cause | Files / functions | Why the fix is correct |
|---|---|---|---|
| Blank Result for unreachable CASE arms (e.g. `DpdDays IS NULL → NOT_APPLICABLE`) | IR `_condition_matches` compared annotated row text to raw chain conditions and failed; projection left empty results | `src/ir/canonical_ir.py` (`_condition_matches`; chain-assignment fallback) | Strip display-only annotations before match; fall back to chain assignment values — source truth, not invented meaning |
| IR rebuild dropped T-SQL IF ladders | Fallback re-extract omitted `extract_tsql_if_elseif_chains` | `src/ir/canonical_ir.py` (`CanonicalBusinessIR.from_pipeline`) | Align IR rebuild with `pipeline._extract_deterministic_decision_chains` |
| Boilerplate “First matching row wins…” as Business Purpose / title | Model copied `execution_semantics` into `rule_name` / `business_meaning`; sanitize only renamed titles | `src/synthesis/rule_synthesizer.py` (`_sanitize_covering_rule_name`); `src/output/report_formatter.py` (`_business_rule_business_meaning`) | Clear meaning when it equals evaluation-order text; formatter rejects those markers |
| Blank-outcome near-cover caused duplicate tables | Incomplete model ladder ≠ covered → synthetic + broken model both kept | `rule_synthesizer.ensure_decision_chain_coverage` (`_repair_blank_outcome_cover`, `_drop_incomplete_siblings`) | Fill blanks from chain; keep one complete cover |
| Quote / annotation mismatches blocked dedup | `'NOT_APPLICABLE'` vs `NOT_APPLICABLE`; `[UNREACHABLE…]` suffixes | `src/parsing/decision_identity.py` (`normalized_condition_key`); formatter `_normalize_condition_text` / `_decision_table_signature` | Identity compares business content, not quote style or display annotations |
| CREATE #temp / DROP temp framed as business rules | Model synthesis + no post-coverage cleanup re-filter | `rule_synthesizer._remove_non_business_cleanup_rules`; `pipeline.py` re-apply after floors | Technical DDL stays out of business rules |
| Read-only SELECT framed as business rule | `_remove_operation_only_rules` too narrow | `rule_synthesizer._remove_operation_only_rules` | Drop SELECT-only “read/retrieve” rules with no decision rows |
| Projection emptied tables when block branches had no results | Block `results` empty → blank `decision_logic_rows` | `report_formatter._project_decision_rules` | Fall back to authoritative rule rows |
| Hallucinated calculation function wrappers | Grounding checked identifiers only | `guardrails._ground_calculation_expressions` (prior working-tree) | Drop calcs whose `NAME(` tokens are absent from source |
| Single-branch WHERE writes missing | `ensure_decision_chain_coverage` only multi-branch | `ensure_statement_coverage` (prior working-tree + pipeline wiring) | Deterministic one-row floor from `table_operations` |
| Duplicate Classify/Penal (and similar) decision tables | LLM extraction re-emitted deterministic CASE/IF ladders as `decision_chain_NNN` with the same conditions but **empty assignments**; full structural signature treated empty≠filled as distinct, so merge kept both; IR matched the same rule to both chains; formatter projected both (both had `decision_block_id`, so content-dedup refused to collapse) | `semantic_validation.merge_decision_chains` (drop assignment-empty shells); `report_formatter._project_decision_rules` (one projection per primary `rule_id`) | Empty shells cannot feed coverage/IR results; first (deterministic) block wins |
| Competing non-canonical paraphrases of a single-write field (e.g. RiskScore ×2) | Sectioned synthesis emitted two one-row tables with different WHERE prose; neither was canonical, so identity suppress (canonical-vs-narrative only) never fired | `report_formatter._suppress_single_write_field_duplicates_by_identity` | Globally single-write field ⇒ at most one decision table |
| “Read …” rule with a pasted WHERE filter as a one-row table | `_remove_operation_only_rules` skipped any rule that already had `decision_logic_rows` | `rule_synthesizer._remove_operation_only_rules` | Drop read-titled rules with ≤1 decision row |
| Contentless INSERT shell blocks floor, then CONFLICT drops the write (audit/queue) | Shell listed columns in `fields_affected` with empty rows → counted as covered → no deterministic floor → reconciliation CONFLICT → formatter excluded | `ensure_statement_coverage` (substantive-only coverage; enrich shells from ops; statement-level INSERT floor; CASE-INSERT skip); `_rule_is_conflicting` keeps `decision_rows_grounded` | Conditional INSERT … WHERE survives as one business rule |
| IF/ELSEIF/ELSE ladder + contentless “Reset …” / branch fragment | Ladder already documents the field; model also emits empty Reset or one-branch WHERE restatement | **Permanent:** `src/synthesis/rule_shape.py` (`shape_structural_business_rules`) wired in `pipeline.py` after floors/alias rewrite; formatter re-applies as safety net via same module | One ladder rule per IF chain in IR and reports |
| MERGE MATCHED exploded per SET column + separate insert | Sectioned synthesis one rule per updated column | **Permanent:** `rule_shape.finalize_business_rule_shape` (MERGE collapse) in pipeline before IR; formatter safety net | One upsert rule per MERGE |
| Grounded INSERT/audit marked CONFLICT then dropped | Reconciliation CONFLICT on pre-enrichment shell; formatter only kept grounded at display | **Permanent:** `clear_grounded_reconciliation_conflicts` + `drop_ungrounded_conflict_rules` after reconciliation in pipeline | Audit/queue grounded rules stay in IR |
| SQL aliases (A/S/H/Target/Source) in report text | Display-time rewrite only | **Permanent:** `src/parsing/alias_resolution.py` rewrites `merged_extraction` + `business_rules` in pipeline; formatter display net | Real table names in IR and reports |

### Rule counts (samples 07–18)

**No hardcoding** of “emit N rules because the sample comment says Rule N.” Counts come from SQL structure: one rule per real decision (CASE/IF ladder, conditional write, INSERT…WHERE, MERGE upsert, etc.). Sample comments are a soft reference only (e.g. sample 07 usually → ~10 rules). Model noise can still add/omit a rule on harder procs; floors/suppressors keep the shape general for similar SQL.

### Model-specific limitations

- **`amazon.nova-lite-v1:0`:** Low output ceiling → frequent sectioned synthesis; purpose/flow can understate multi-step procedures; may emit duplicate paraphrases and technical staging rules. Pipeline floors and filters mitigate; they do not rewrite business meaning.
- **`openai/gpt-oss-120b`:** Not executed here (no API config in `.env`). Expect better prose coherence; still rely on deterministic floors for ladders and blank-outcome repair.
- Complex samples (07, 08, 16, SMA_MARKING) remain challenging for small models; simplify SQL only if business meaning is preserved—do not hardcode expected rules.

### Remaining risks

1. **Multi-write fields** (e.g. `RestructureEligible`, `EligibleForUpgrade`, `ReviewReason`) can still show several rules when the SQL truly has several statements; occasional model paraphrases of one of those statements may coexist when condition text differs enough to miss content-dedup.
2. **Process flow** may still narrate mutually exclusive IF/ELSEIF/ELSE as sequential steps (LLM prose). Decision tables remain authoritative.
3. **Staging INSERT into #temp** may still appear as a rule (business-relevant eligibility, not pure DDL).
4. **Findings / degraded banners** exist but are intentionally not rendered in the business report (client direction); verification report holds diagnostics.

---

## D. Final Validation

### Files changed (this work)

- `pipeline.py` — statement coverage wiring; re-apply cleanup/operation filters after floors; **permanent** alias rewrite + `finalize_business_rule_shape` (pre- and post-reconciliation)
- `src/synthesis/rule_shape.py` — MERGE collapse, IF-ladder fragment suppress, grounded CONFLICT clear / ungrounded CONFLICT drop (IR path)
- `src/parsing/alias_resolution.py` — permanent table-name rewrite for extraction + business rules
- `src/ir/canonical_ir.py` — UNREACHABLE-aware matching; T-SQL IF rebuild; chain-value fallback
- `src/synthesis/rule_synthesizer.py` — blank-outcome repair; sibling collapse; meaning sanitize; CREATE/read filters; `ensure_statement_coverage` (prior)
- `src/output/report_formatter.py` — boilerplate purpose filter; quote-aware signatures; projection fallback; non-canonical duplicate collapse; one projection per rule_id; single-write non-canonical collapse; delegates MERGE/ladder shaping to `rule_shape` (safety net)
- `src/validation/semantic_validation.py` — drop assignment-empty LLM decision-chain shells; qualifier-aware chain signatures
- `src/parsing/decision_identity.py` — quote + annotation normalization for identity
- `src/ingestion/guardrails.py` — calculation expression grounding (prior working-tree)
- Tests: `tests/test_rule_identity_regressions.py`, `tests/test_rule_synthesizer.py`, `tests/test_rule_deduplication.py`, `tests/test_statement_coverage.py`, `tests/test_semantic_validation.py`, `tests/test_rule_shape.py`, `tests/test_alias_resolution.py`

### Tests executed (actual results)

| Suite | Result |
|---|---|
| `pytest tests/` | **697 passed**, 2 warnings (Chroma deprecation) |
| `python evaluate.py --mode deterministic` | **13/13 PASS** (prior pass; re-run if needed) |
| Live batch samples 01–18 (`amazon.nova-lite-v1:0`) | **18/18 OK** → `samples/output/validation_01_18/batch_20260916_184052_266320/` |
| Live batch samples 07–18 (post duplicate-shell fix) | **12/12 OK** → `samples/output/validation_07_18/batch_20260916_192607_525235/` |
| `openai/gpt-oss-120b` | **Not run** — no credentials |

### Are final reports user-facing and logically correct?

**Yes** for samples 07–18 under Nova Lite after this pass: decision ladders are present once per real chain; Classify/Penal no longer double-project; read-titled SELECT framing and competing RiskScore paraphrases are filtered; blank results and evaluation-order purposes remain fixed from the prior pass.

**Still needs attention:** multi-statement fields can still list several related rules (usually SQL-faithful); IF/ELSEIF prose in Process Flow; model-quality variance across providers.

### How to reproduce live validation

```bash
# Nova Lite (current .env)
python main.py samples/07_DPD_Bucket_Classification.sql --output samples/output/validation_07_18/out.md --cache

# Batch 07–18
python main.py samples/0{7,8,9}_*.sql samples/1{0..8}_*.sql \
  --output-dir samples/output/validation_07_18 --cache
```
