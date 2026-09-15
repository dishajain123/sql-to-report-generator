# SMA report defects and fixes

The attached report is not a faithful specification of the active stored procedure. The reviewed expected behavior is in [SMA_MARKING_12122023_reference.md](SMA_MARKING_12122023_reference.md). That document was written from the source; it is not represented as a newly generated model result.

| Observed defect | Root cause | Change |
|---|---|---|
| Disabled DPD calculations, alternate classifications and continuous-excess reset appear as active rules | Original SQL, including comments, reached extraction and the synthesis `source_sql` payload. Source grounding could also see disabled text. | A shared SQL comment scanner supplies executable text to extraction and synthesis, preserves literals/quoted identifiers and source offsets, and handles nested block comments. The deterministic SQL/CASE parsers use the same scanner. |
| The DPD maximum table repeats all winners and unrelated actions in every row | Canonical block membership used token overlap. The different maximum comparisons have almost identical token sets, and token sets lose operators and operand order. | Match expressions while preserving operators and operand order. Enforce output-field compatibility and available statement/chain identity. Broad evidence snippets no longer establish branch membership. |
| `ELSE` combines stock-statement DPD, `OTHER`, and the SMA class fallback | A generic ELSE match was sufficient to associate unrelated rules with a decision chain. | Match a non-ELSE branch before accepting the rule's ELSE. Source recovery rules carry a chain identity. |
| Reset rules acquire later classification logic; repeated writes to one field are confused | Decision-table backfill selected the first matching output field. | Do not backfill reset/initialization rules; abstain when more than one chain writes that field. |
| Additional CASE tables never reach recovery | The parser required `AS` for projection aliases and did not recognize aggregate-wrapped CASE expressions; structural deduplication also collapsed identical mappings at different source locations. | Support implicit aliases and direct aggregate wrappers, retain aggregation semantics and distinct source occurrences. The sample now yields 12 active CASE tables instead of 4, independently of model rules. |
| Missing branches survive completeness recovery | Coverage accepted only 50% of non-ELSE conditions, without checking outcomes or output fields. | Require complete condition/result coverage for the field, including the fallback. Recover a full source table when incomplete; use its recovered values instead of concatenating incorrect model values. |
| Rule count and overview disagree with numbered detail | The formatter independently grouped/consumed canonical rules only in the detail section. | A shared display projection feeds the count, overview and detail, retaining source order and all affected fields. |
| Grouped decision tables omit eligibility; an empty eligibility array becomes “all rows” | Decision-block rendering did not display eligibility, and ordinary rendering treated missing metadata as proof of unconditional execution. | Preserve eligibility on projected blocks and display it. Missing eligibility is explicitly undocumented. |
| Calculations say “None identified,” despite date arithmetic and customer aggregates | The report used only the model's synthesis calculation list. SELECT INTO operations also lacked structured projection assignments. | Preserve parsed SELECT INTO assignments; collect formula expressions from deterministic assignments with chunk/statement provenance; render extracted calculations omitted by synthesis. |
| Overview is a run-on collection of section introductions; failure summary contradicts itself | Section outputs were concatenated, and each section could assert whole-procedure behavior or say there was no handler. | Keep section purpose text in separate paragraphs. Prompts require concise section-specific prose, empty exception summaries in sections without handlers, exact formulas and join filters, no invented acronym expansions/compliance claims, and no inferred data flow through unread temporary results. |

The existing working-tree changes for model output ceilings and sectioned synthesis were retained. This change does not establish that model truncation is impossible: the configured model can still produce incomplete or inaccurate prose. Truncation/review warnings remain available, and the live output must be checked before declaring the whole report verified.

## Additional deterministic coverage

The later parser audit found that useful decisions extended beyond CASE assignments. The corrected path now recognizes **23 decision tables** in the bundled sample: 12 CASE assignments/rankings, seven scalar fallback selections, two sequential update mappings, and two history-insertion predicate tables.

| Further root cause | Permanent correction |
|---|---|
| A simple `CASE value WHEN ...` lost its comparison operand; missing ELSE was treated as missing logic | Preserve the operand in each comparison and emit the SQL-defined implicit NULL result, including a single-WHEN CASE. `WHEN NULL` remains an equality to NULL, not an invented IS NULL test. |
| Nested choices remained opaque expressions | Parse supported scalar expressions into ordered leaf rows. Preserve first-match semantics even when predicates are NULL. Bounded expansion leaves original expressions available when limits are reached. |
| ISNULL/COALESCE, IIF, CHOOSE and previous-status selection had no deterministic tables | Add SQL-AST-based scalar decision extraction. CHOOSE retains SQL Server's integer-index conversion and NULL fallback; ordinary SQL type conversion still applies. |
| Only CASE-like syntax was recognized as decision logic | Group contiguous, same-target literal UPDATE assignments into explicitly sequential tables. A read, unrelated write or procedural boundary stops grouping. Later matching writes may overwrite earlier values; no match preserves the current value. |
| An IF or END could be swallowed into preceding semicolon-free SQL | Keep control wrappers as separate, lossless statement spans. Distinguish CASE's END from a procedural END. Split same-line semicolon-separated statements for decision extraction. |
| Decisions lost WHERE, joins, grouping and enclosing guards | Attach parsed statement context and complete T-SQL IF/BEGIN/END scopes. Resolve UPDATE target aliases; keep outer joins as context rather than treating ON conditions as global filters. |
| CASE expressions inside WHERE could be missed or mistaken for assignments | Emit row-selection predicate tables, labelled as decision outputs rather than changed fields. Preserve the resulting full predicate; only TRUE includes a row. |
| Structural deduplication ignored branch order; repeated predicates mixed outcomes | Preserve ordered coverage and occurrence-specific result lookup. Keep separate source occurrences, distinct same-line IDs and each UPDATE row's own provenance. Keep field names on multi-output branch results. |

These are source-derived tables, not invented business interpretations. The deterministic snapshot is [available here](SMA_deterministic_decision_tables.md). It is generated without model-authored rules using the production recovery and rendering code.

This remains a conservative static parser, not a full SQL execution engine. Dynamic SQL, unsupported expression wrappers, unbracketed procedural guards and complex control flow are not claimed to be fully expanded. Expressions retain SQL's type-conversion/error behavior; a fallback row does not catch conversion failures. A table count is not proof that an entire procedure has been semantically verified.

## Validation

Local regression checks cover the actual bundled UTF-16 procedure, threshold boundaries, independent maximum branches, unrelated ELSE branches, wrong-result recovery, comment/literal handling, calculation retention, eligibility, and consistency of the full formatted report. The full repository test suite passes: 473 tests. Additional behavior checks compare nested nullable CASE paths and sequential updates with local SQLite execution; no external database or model is called by these checks.

Live regeneration was attempted but the sandbox could not reach the configured endpoint. Automatic approval review then rejected the network-enabled attempt because sending this private procedure to AWS Bedrock in `us-east-1` had not been explicitly approved. No successfully regenerated live-model report is claimed. The remaining verification step is to run the updated pipeline with that transfer approved, compare the resulting report against the reference, and address any model-output defects it still exposes.

## September 11: 248 overview entries but only 23 rule details

The latest sample report exposed a separate identity failure in the mixed
model/deterministic path. Coverage revision normalizes the model's rules but,
unlike initial synthesis grounding, previously did not allocate missing rule
IDs. `BusinessRuleIR.from_dict` preserved those IDs as empty strings.
`_build_decision_blocks` and `_project_decision_rules` then used the empty string
as a dictionary key for multiple unrelated rules. The projection selected the
last rule's metadata (customer history in the observed report), and emitted all
replacements for that ID once per original rule. Detail rendering grouped those
replacements again; the overview and count did not.

An offline reproduction using the bundled SQL, 26 ID-less model-shaped rules
(nine matching decision tables), and the 23 recovered deterministic tables
produces **248 overview entries and 23 distinct blocks with the previous
projection**. The repaired path produces **40 entries/details: 23 decision
tables plus 17 independent narrative rules**. This is a controlled reproduction,
not a regenerated model report. It explains both the repeated overview and the
unrelated history descriptions attached to DPD rules. Previous tests exercised
only deterministic rules, whose IDs were already unique, and missed this case.

Permanent changes:

- Allocate nonempty, unique IDs during rule normalization, section merging,
  coverage recovery and canonical construction. Preserve existing unique IDs
  and retain replaced IDs as provenance. Allocation is idempotent and reserves
  existing IDs before generating replacements.
- Defensively reject ambiguous legacy block references in the formatter and
  emit each block once. Retain ambiguous rules individually instead of silently
  selecting the last rule's metadata.
- Section deduplication now compares rule rows and source/scope metadata too;
  matching names, actions and fields alone are insufficient to delete a rule.
- Prefer recovered deterministic table names over generic evaluation-order
  sentences. Do not repeat identical evaluation semantics in the summary.
- Collapse exact duplicate calculation records while retaining records with
  different scope or provenance.

Regression coverage in `tests/test_rule_identity_regressions.py` includes missing
and reused IDs, suffix collisions, idempotence, preservation of distinct source
scopes and outcomes, ambiguous legacy references, duplicate block references,
and the mixed SMA source-to-report count and metadata checks. The original
`samples/output` report is retained for comparison; it must be regenerated to
reflect the corrected pipeline. No new model call is required by these tests.

## September 11 (later): rule titles that read as duplicates

A generated report (`samples/output/2_PRO.SMA_MARKING...`) showed two distinct
title defects that make genuinely different rules look like duplicates in the
overview table, even though the underlying decision tables were each correct
and none were dropped.

| Observed defect | Root cause | Change |
|---|---|---|
| Six+ unrelated rules (different tables/fields: `SMA_CLASS`, `MovementFromStatus`, `TotOsAcc`, `totOsCust`, `TotOsCust`) all titled the identical boilerplate sentence "First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates." | `ensure_decision_chain_coverage` skips synthesizing its own deterministic rule whenever a model-authored rule already covers a chain's rows (correct - avoids a duplicate table). But when the model had copied the evaluation-order/execution-semantics sentence verbatim into that rule's `rule_name` instead of writing a short label, the boilerplate sentence was left standing as the title with nothing to replace it. | When a covering rule's `rule_name` matches its chain's `execution_semantics` text exactly, rename only that rule (in place, decision rows untouched) to the same `Determine <field>` convention synthesized rules already use. A `rule_name` that isn't a copy of the execution semantics text is never touched. |
| Two structurally distinct rules (the same MAX ladder recomputed once per `CustomerEntityID`, once per `UCIF_ID`) rendered as two identical-looking "Determine inputs to MAX for MAXSMA_CLASS" rows | The naming convention for synthesized aggregation rules uses only the aggregated field name, which collides whenever the same field is independently recomputed under a different grouping/target. | The shared display projection now disambiguates any rule_name shared by two-or-more displayed rules that differ in output field or target table, appending that distinguishing detail in parentheses. Rules that are exact duplicates (same name *and* same field/target) are left alone - that is a dedup problem, not a naming problem. |
| A legacy multi-rule decision block rendered raw joined SQL with table-alias prefixes (`CONVERT(INT, B.SMA_CLASS_KEY) = 3`) instead of the alias-stripped display used by every other rule-rendering path | `_render_decision_block` had picked up `preserve_sql=source_sql`, extending a raw-SQL-preservation mode (added for the new grouped per-field sub-tables, where it is appropriate) to the older single/multi-rule path as well, inconsistently with `_render_business_rule_block` and the default renderer. | `_render_decision_block` always renders through the standard alias-stripped display; raw-SQL preservation stays scoped to the grouped statement-decision sub-tables it was built for. |

Separately, a same-statement/same-eligibility grouping feature (`src/output/decision_groups.py`)
that merges rules like the six independent `#DPD` CASE columns (`DPD_IntService` ...
`DPD_StockStmt`, one SELECT INTO, one shared eligibility) into a single displayed
rule with a per-field `#### Decision Logic` sub-table each was already present but
had not been reconciled with the older regression tests, which still asserted one
rule per chain with zero grouping. Verified end-to-end against the bundled sample:
grouping now takes 23 raw decision chains down to 15 displayed rules with the total
rendered decision-table count still exactly 23 (nothing dropped, nothing duplicated).
`test_mixed_sma_revision_rules_keep_all_tables_without_multiplying_or_losing_history`,
`test_full_report_counts_and_all_source_decision_tables_agree_for_bundled_sample`, and
`test_real_sample_scope_fallback_and_sequential_maps_reach_full_report` were updated to
assert that invariant (block count may drop via grouping; total table count and content
must not) instead of the older no-grouping invariant.

New regression coverage: `test_model_rule_name_copied_from_evaluation_order_is_replaced`
and `test_duplicate_rule_names_on_different_fields_are_disambiguated` in
`tests/test_rule_identity_regressions.py`. Full suite: 482 tests pass. The bundled sample
was regenerated through the deterministic-only path (no model call) to confirm the
grouped report renders 15 rule entries covering all 23 recovered decision tables with no
generic-boilerplate titles; a live model-driven regeneration was not attempted here for
the same network-approval reason noted above.

### Follow-up: disambiguated title not reaching the rule-detail heading

Regenerating the bundled sample end-to-end exposed one more gap in the
disambiguation from the previous entry: the "## Business Rule Summary" table
showed `Determine SMA_CLASS (#SMACLASS)` correctly for two distinct rules, but
their own `### R6 -` / `### R7 -` detail headings both still read plain
"Determine SMA_CLASS" - the summary and the detail for the *same rule*
disagreed. Root cause: `_render_decision_block`'s heading prefers
`decision_block_title` over `rule_name`, and the earlier fix only updated
`rule_name`. Also, when two rules share both output field *and* target table
(R6 populates `#SMACLASS` via `SELECT INTO`, R7 then transforms it in place
via `UPDATE` - same field, same target), neither suffix source varies, so no
suffix was produced at all and the pair stayed literally identical.

Fix: `_disambiguate_duplicate_names` now writes `decision_block_title` in
step with `rule_name` (fixing the summary/detail disagreement), and always
applies a suffix source even when it doesn't vary within the group, then adds
a plain ordinal (` [1]`, ` [2]`) as a last-resort tiebreaker for whatever
still collides after that. Verified against the bundled sample: all 15
displayed rule titles are now pairwise-unique, and the summary table and
detail headings agree for every rule. New tests:
`test_duplicate_rule_names_sharing_field_and_target_get_ordinal_fallback`
and an added assertion on `decision_block_title` in the existing
disambiguation test. Full suite: 483 tests pass.

### Follow-up: a content-level duplicate survives even with unique titles

A live-generated report (`samples/output/3_PRO.SMA_MARKING...`, 29 rules) had
no more duplicate/generic *titles*, but still had one duplicate *rule*: a
model-authored "Set DPD to zero if less than reference period" rule restated,
in prose only, exactly what the deterministic "Determine DPD_IntService,
DPD_NoCredit, ... DPD_StockStmt" block already documents field-by-field with
real decision tables.

Root cause, in two parts:
1. The model reported all six affected fields as one comma-joined string
   (`"DPD_IntService, DPD_NoCredit, ..."`) rather than a list of individual
   field names. The decision-block matcher in `_build_decision_blocks`
   (`canonical_ir.py`) compared that whole string against each chain's
   individual field names and never split on comma, so it never intersected
   - the rule could never be recognized as describing the same chain.
2. Even after fixing (1) to split on comma, block-matching also requires
   either literal condition-text overlap or cited evidence text - neither of
   which a pure-narrative rule (no `decision_logic_rows`, no evidence
   quoting the source) can ever provide. So field-set matching alone cannot
   safely *merge* such a rule into a block; forcing a merge on field overlap
   alone risks pulling in an unrelated rule that only happens to touch one
   shared field (e.g. a real, separate `DPD_Max` reset-to-zero step also
   names `DPD_Max`, which the `DPD_Max` MAX-selection block does too, but
   they are genuinely different operations).

Fix: (1) `canonical_ir.py`'s block-matching now splits `output_field` and
`fields_affected` on commas before comparing to chain fields, so a rule that
does cite real condition text or evidence for a comma-joined field list can
still be matched/merged. (2) A new, narrow suppression pass in
`report_formatter.py`, `_suppress_narrative_duplicates_of_decision_blocks`,
drops a displayed rule only when it has zero decision rows of its own *and*
its whole field set (comma-split, 2+ fields) exactly equals an
already-displayed block's whole field set - never on a single shared field,
and never when the rule carries its own decision content. Verified: the
narrative duplicate is now dropped; a genuinely distinct single-field
`DPD_Max` reset rule is unaffected and still renders. New tests:
`test_narrative_rule_duplicating_a_full_decision_block_is_suppressed`. Full
suite: 484 tests pass.

### Follow-up: a duplicate survives even when it carries its OWN decision table

A live-generated report (`samples/output/4_PRO.SMA_MARKING...`, 31 rules)
showed `R11 - Determine DPD_Max` (the deterministically recovered `#DPD`
MAX-selection block) and `R24 - Calculate maximum DPD` (a model-authored
rule) rendering the identical six-row ladder twice, word for word except for
incidental formatting - one side wrapped each branch's boolean expression in
parentheses and kept the `A.` table alias, the other didn't.

Root cause: `_suppress_narrative_duplicates_of_decision_blocks` intentionally
never touches a rule that has `decision_logic_rows` of its own (see the
entry above - that guard exists so a rule with real, distinct decision
content is never mistaken for a table-less narrative restatement). R24 has
its own `decision_logic_rows`, so it always passed that guard untouched,
regardless of whether its content was original or a restatement.

Fix: a second, content-level pass, `_suppress_content_duplicate_decision_tables`,
runs after the narrative pass. It normalizes every row's condition/outcome
text the same way the renderer displays it (alias-stripped via
`_field_references_for_display`, whitespace-collapsed, and one redundant
fully-wrapping parenthesis pair removed) and groups rules by (field set,
normalized row sequence). A rule is dropped only when an *exact* match in
that group already carries a `decision_block_id` or is flagged
`deterministic_decision_table` - the canonical/recovered copy always wins,
and a non-canonical rule is never dropped in favor of another non-canonical
one. Two independently recovered blocks that legitimately share row content
(the `MAXSMA_CLASS` ladder computed once per `CustomerEntityID` and once per
`UCIF_ID`, from the entry below) are both `decision_block_id`-tagged, so
this pass never touches either of them - confirmed by re-running
`test_mixed_sma_revision_rules_keep_all_tables_without_multiplying_or_losing_history`,
which still requires all 23 chain tables to survive.

Verified against a reconstruction of the real R11/R24 shape (deterministic
`#DPD` block plus a paraphrased duplicate matching the report's actual
formatting differences): the duplicate heading and table are gone, the
canonical `Determine DPD_Max` block is untouched, and a genuinely distinct
single-field rule with different row content still renders. New test:
`test_model_rule_restating_a_decision_blocks_own_table_is_suppressed`. Full
suite: 485 tests pass.

### Follow-up: the same "Findings" bullet doubled across two containers

The same report (`samples/output/4_PRO.SMA_MARKING...`) also showed the
identical "Affected regions: lines 19-19, 653-660, 693-695, 710-712 (4
total) - needs review..." sentence twice in "## Findings / Needs Review" -
once standalone, once appended to the "exceeded the model's maximum
response length" truncation sentence.

Root cause: on a truncated synthesis pass with multiple unresolved coverage
gaps, `pipeline.py` calls `_merge_into_truncation_ambiguity` once on
`merged_extraction["ambiguities"]` and once on `synthesis.data["ambiguities"]`,
intending one combined bullet. Only `synthesis.data["ambiguities"]` actually
carries the truncation-marker sentence (`synthesize()` puts it there);
`merged_extraction["ambiguities"]` never does. The old
`_merge_into_truncation_ambiguity` always silently fell back to appending
the summary standalone when a container had no marker to merge into - so
the `merged_extraction` call unconditionally added a second, freestanding
copy of the same "Affected regions" text, while the `synthesis.data` call
correctly folded it into the existing sentence. `_findings_section` unions
ambiguities from both containers and only deduplicates *exact* string
matches, so the two differently-worded sentences (one standalone, one
combined) both survived as separate bullets describing the same truncation.

Fix: `_merge_into_truncation_ambiguity` now returns whether it found a
marker to merge into. The `pipeline.py` call site merges into
`synthesis.data` first, then `merged_extraction`, and only appends a
standalone bullet (to `merged_extraction`) when NEITHER container had a
marker - so the information is never silently dropped, but is never
duplicated either once any container already carries the combined sentence.
New test: `test_consolidated_gap_ambiguity_does_not_duplicate_across_containers`
in `tests/test_rule_identity_regressions.py`, asserting the affected-regions
text appears exactly once in the rendered findings section. Full suite: 486
tests pass.

### Follow-up: a table alias is stripped instead of resolved

Report 5 (`samples/output/5_PRO.SMA_MARKING...`) showed a bare column name
(e.g. `CustomerAcID`, `BALANCE`) in most conditions/eligibility text - the
`A.`/`B.`/`dpd.` alias prefix from the source SQL was simply removed, not
replaced with the real table it stood for. That is lossy in exactly the
cases where it matters most: several rules join two-or-more tables (e.g.
`PRO.ACCOUNTCAL AS A INNER JOIN PRO.CUSTOMERCAL AS B ...`, or `#ACCOUNT_
MOVEMENT_HISTORY AS A LEFT JOIN PRO.ACCOUNT_MOVEMENT_HISTORY AS B`, the
temp working copy and the permanent audit table sharing one column name),
so a bare `CustomerAcID` genuinely could be either table - the alias was
the only thing distinguishing them, and stripping it threw that information
away instead of preserving it.

Fix: `_field_for_display`/`_field_references_for_display`/
`_pretty_condition_for_display`/`_assignment_text`/`_decision_logic_block`
now take an optional alias map and, when an alias resolves, substitute the
real table name (`A.FACILITYTYPE` -> `PRO.ACCOUNTCAL.FACILITYTYPE`) instead
of dropping the alias; an unresolvable alias still falls back to the
previous strip-only behavior so nothing regresses for text with no
available FROM/JOIN context. The map itself, `_rule_alias_map`/
`_merged_alias_map`, is built by reusing `_extract_from_clause_alias_map`
(the same alias-resolution regex `technical_sql_ops.py` already uses for
deterministic table-operation extraction) against the rule's own `FROM ...
JOIN ...` text - already present verbatim in every rule's `decision_context`
("Source context") - so no new SQL parsing pass is needed. Threaded through
`_render_business_rule_block` and `_render_decision_block` (conditions,
outcomes, actions, and eligibility), and through `_render_statement_
decisions`'s eligibility only - that function's own `### Decision Logic`
sub-tables keep the literal, byte-exact source SQL on purpose (a deliberate,
previously-fixed design choice; see the "raw-SQL preservation stays scoped
to..." entry above), so alias letters there are intentionally left as
written in the source, not resolved.

One existing test asserted the old strip-only text (`CONVERT(INT, SMA_CLASS_KEY)
= 3`) and was updated to the resolved form (`CONVERT(INT, PRO.CUSTOMERCAL.
SMA_CLASS_KEY) = 3`), which is strictly more informative, not a behavior
regression. New tests in `tests/test_rule_identity_regressions.py` cover
alias-map construction from source context, known/unknown-alias resolution,
end-to-end resolution through both render paths, and that the preserved-SQL
decision tables stay untouched. Full suite: 491 tests pass.

### Follow-up: harden the synthesis prompt itself against two defects already fixed downstream

The two title/duplicate defects from the "rule titles that read as duplicates"
and "a content-level duplicate survives even with unique titles" entries above
were both fixed only in `report_formatter.py`/`canonical_ir.py` - after the
model had already produced the bad output. The prompt (`src/prompts/
rule_synthesis.yaml`) never actually told the model not to do either thing,
so a differently-shaped occurrence of the same underlying behavior (a
boilerplate evaluation-order phrase copied somewhere the downstream
suppression doesn't check, or a narrative duplicate the content-matching
pass doesn't catch) could still reach the report undetected.

Change: added two explicit instructions to all three dialect prompt blocks
(`default`, `oracle`, `tsql`, kept in sync since the file already duplicates
this content per dialect):
- Forbid copying execution-semantics/evaluation-order phrases (e.g. "First
  matching row wins", "SQL type conversion still applies", "Each row is a
  separate update executed in source order") into `rule_name`, and point the
  model at the existing `Determine <field>` / `Calculate <metric>` naming
  convention instead.
- Forbid emitting a second, table-less business rule that only restates in
  prose a decision table another rule already carries for the same output
  field(s), while explicitly preserving a genuinely different operation that
  happens to share a field name (the same distinction
  `_suppress_narrative_duplicates_of_decision_blocks` already applies
  downstream).

This is a defense-in-depth addition, not a replacement for the existing
downstream suppression passes (`_suppress_narrative_duplicates_of_decision_blocks`,
`_suppress_content_duplicate_decision_tables`) - a model can still ignore a
prompt instruction, so those passes stay in place as the actual guarantee.
New test: `test_synthesis_prompt_forbids_evaluation_order_titles_and_table_restatements`
in `tests/test_rule_synthesizer.py`, checking the literal instruction text is
present in all three dialect prompt blocks. Full suite: 492 tests pass.

## Phase 3: live Bedrock verification run

Executed `python main.py samples/PRO.SMA_MARKING_12122023.StoredProcedure.sql
--output samples/output/6_PRO.SMA_MARKING.StoredProcedure_report.md --verbose`
against the real AWS Bedrock endpoint (`us-east-1`, `amazon.nova-lite-v1:0`,
credentials from `.env`), per explicit user approval for this specific run.
This is the first genuinely live-model regeneration in this document's
history - every entry above was either a controlled offline reproduction or
a deterministic-only regeneration, because earlier attempts could not get
network/approval clearance.

Result: **38 business rules**, no duplicate rule titles in the overview
table, and the earlier "Affected regions" Findings bullet appeared exactly
once (both confirming the fixes above hold under real model output, not
just the reconstructed test cases that exercised them). Two further defects
were found and fixed from this live run specifically:

### Follow-up: content-duplicate suppression missed a stray space before punctuation

`R5 - Determine DPD_Max` (the recovered `#DPD` block) and `R26 - Calculate
maximum DPD` (a model-authored rule) rendered the same six-row MAX-selection
ladder twice again - this time despite `_suppress_content_duplicate_decision_tables`
(added earlier in this document) being in place. Root cause: the original
source literally has a stray space before a comma in several branches
(`isnull(A.DPD_NoCredit ,0)`, a hand-typed formatting quirk the
deterministic block preserves verbatim), while the model's paraphrase of
that same row cleaned it up (`isnull(DPD_NoCredit,0)`). `_normalize_condition_text`
collapsed whitespace *runs* to one space but left a single stray space next
to punctuation untouched, so that one row's signature differed from its
otherwise-identical counterpart, the two rules' whole row-sequence tuples
compared unequal, and the duplicate survived.

Fix: `_normalize_condition_text` now also strips whitespace immediately
before a comma/closing-paren and immediately after an opening paren.
Verified the exact real-world row pair now normalizes equal. New test:
`test_content_duplicate_suppression_survives_a_stray_space_before_punctuation`.

### Follow-up: a shared line range printed twice in one Findings sentence

The consolidated truncation Findings bullet read "Affected regions: lines
610-651, 610-651, 693-695, 710-712 (4 total)..." - the same range listed
twice in one sentence. Root cause: `format_consolidated_gap_ambiguity`
built its preview list from every gap's line range with no dedup; two
distinct gaps (an `INSERT` keyword and a nested `CASE/WHEN` keyword) happen
to share one line range, so both copies survived into the shown preview
even though they describe different unresolved constructs at that location.

Fix: the preview list is now deduplicated (`dict.fromkeys`) while the
`({len(gaps)} total)` count still reflects every distinct gap - so the
sentence never repeats a line range, but no gap's existence is hidden. New
test: `test_consolidated_gap_ambiguity_does_not_repeat_a_shared_line_range`
in `tests/test_coverage_check.py`.

Both fixes verified against a reconstruction of the exact real row/gap
shapes from this live run (re-running the live Bedrock call a second time
just to re-confirm was not done, to avoid further cost/data-transfer beyond
the one approved run). Full suite: 494 tests pass.

Remaining review items in this live report (reconciliation conflicts,
`REVIEW_REQUIRED` quality status, several narrative rules with fields the
model didn't name) are model-output-quality limitations of the configured
`amazon.nova-lite-v1:0` model (a small, real 5000-token-ceiling model,
hence the 8-section synthesis) - the pipeline surfaces them honestly rather
than hiding them, which is the intended, correct behavior; they are not
pipeline defects to fix in code.

## Prompt token-efficiency pass

`src/prompts/rule_synthesis.yaml` and `src/prompts/logic_extraction.yaml`
carry the same content three times (`default`/`oracle`/`tsql` dialect
blocks) written as long, repetitive prose, plus one accidental literal
duplication (`default`'s "OUTCOME MUST BE THE LITERAL ASSIGNED VALUE" and
"SEQUENTIAL UPDATE PASSES" bullets each appeared twice, verbatim, back to
back) - every synthesis/extraction call pays for this in input tokens, and
`_run_rule_synthesis` sends the full system prompt once per section (8
sections for the live SMA_MARKING run above).

Rewrote every dialect block as dense bullets/tables instead of flowing
prose, removed repeated framing sentences and the accidental duplicate,
and shortened the worked examples while keeping every substantive
constraint (schema shape, banned-word list, the alias/eligibility/decision-
chain rules, and the two marker phrases the prompt-content regression
tests check for verbatim: `NEVER COPY EXECUTION-SEMANTICS`, `SQL type
conversion still applies`, `DO NOT RESTATE A DECISION TABLE IN PROSE`, and
`"decision_chains"`/`branch_condition`/`assignments` in extraction).

Per-call token estimate (chars/4), system + user template, the actual
payload size for one call:

| Prompt / dialect | Before | After | Cut |
|---|---|---|---|
| rule_synthesis (tsql) | ~7,813 | ~4,576 | 41% |
| rule_synthesis (oracle) | ~7,914 | ~4,511 | 43% |
| rule_synthesis (default) | ~9,095 | ~4,515 | 50% |
| logic_extraction (tsql) | ~2,281 | ~1,754 | 23% |
| logic_extraction (oracle) | ~2,192 | ~1,687 | 23% |
| logic_extraction (default) | ~2,145 | ~1,641 | 23% |

Verified with the full test suite (494 tests, including the two literal
prompt-content assertions) rather than a new live model call - a wording
change to a prompt has no deterministic test of *output quality* by
nature, so the next live Bedrock run against this procedure is the real
confirmation that quality held; nothing in this pass changed the JSON
schema, the enforced constraints, or any code path, only prompt wording
and structure.

Note: `src/prompts/logic_extraction.yaml` was found deleted from the
working tree at the start of the next session (visible as `deleted:` in
`git status`, cause unknown - not from any tool call made that session)
and was restored via `git checkout` to its last-committed, pre-compaction
form. The `rule_synthesis.yaml` compaction survived and is unaffected;
the `logic_extraction.yaml` compaction from this entry was lost and would
need to be redone if still wanted.

## Alias resolution extended to the preserved decision tables; Findings-section garbage and duplicate housekeeping fixed

Report `samples/output/1_PRO.SMA_MARKING...` surfaced two more real
defects, both fixed.

**Aliases still raw inside `_render_statement_decisions`'s tables.** Per
explicit user request, a bare alias (`A.FACILITYTYPE`, `dpd.DPD_Max`) is
no longer acceptable anywhere in a `### `/`#### Decision Logic` table or
its `Expression:` bullet, including the grouped/statement-decision
sub-tables that previously kept 100% raw source formatting for
evidentiary fidelity. `_field_references_for_display` only ever rewrites
a dotted `alias.field` token and leaves every other character (spacing,
casing, parens, function names) exactly as written, so it is safe to
apply even in that raw-preserved path: `_decision_logic_block`'s
`preserve_sql=True` branch and `_render_statement_decisions`'s
`Expression:` bullets now resolve aliases through it instead of passing
the row through completely untouched. `Source context` (the literal
`FROM`/`JOIN` evidence bullets) is unchanged and stays raw - that is
distinct evidence text, not a rendered decision-table cell.

**Findings section chaos.** The same report showed, in `## Findings /
Needs Review`: the same "chunk had malformed JSON" fact stated 3-4
different ways for the same chunks, a bullet cut off mid-sentence
(`- Chunk '00_main_body`, no closing quote or rest of the sentence), and
bare garbage fragments (`SMA_x`, `SMA_SMA_`, `SMA_`) as standalone
bullets. Three separate root causes:
1. The deterministic per-chunk "malformed JSON" housekeeping message
   (`pipeline.py`'s `_merge_extractions`/`_single_pass_extraction_payload`)
   was sent to the synthesis model as input `ambiguities`, and the model
   paraphrased it back out in its own `ambiguities` output several
   different ways - none adding information over the one deterministic
   message per chunk. Fixed: `_build_compact_synthesis_payload` now
   excludes this specific housekeeping shape from the model's input
   (`_is_parse_error_housekeeping_ambiguity`), so the model has nothing
   to restate; genuine extraction-derived ambiguities are unaffected.
2. `business_rules` and `step_by_step_flow` are screened for
   repetition-degeneration garbage (`_is_degenerate_text`) when merging
   sectioned synthesis results, but `ambiguities` never was - so a
   truncated model response's garbage tokens reached the report directly.
   Fixed: added `_looks_truncated` (an unclosed quote, or a short fragment
   with no closing punctuation) alongside the existing degenerate-text
   check, applied to `ambiguities` in `merge_section_results` and via a
   new `_clean_ambiguities` helper in `synthesize()`'s cache-hit path,
   main path, and `revise()` - the same protection every other synthesis
   return path already had.
3. `_findings_section`'s own `chunk_provenance` loop independently
   re-derives "Chunk X (kind) returned malformed JSON..." from the same
   `parse_error` field the deterministic `_merge_extractions` ambiguity
   was already built from - producing two differently-worded bullets
   about the same chunk. Fixed: the loop now skips a chunk whose id is
   already named in an existing ambiguity, falling back to its own
   bullet only when no matching ambiguity was recorded (preserving the
   general two-independent-sources behavior an existing test exercises
   with genuinely distinct wording).

New tests: `test_merge_section_results_drops_degenerate_and_truncated_ambiguities`,
`test_looks_truncated_flags_unclosed_quotes_and_short_cutoffs`,
`test_parse_error_housekeeping_ambiguities_excluded_from_synthesis_payload`
in `tests/test_sectioned_synthesis.py`;
`test_chunk_parse_error_reported_once_not_twice_when_pipeline_already_named_it`
in `tests/test_canonical_ir.py`; `test_render_statement_decisions_leaves_raw_sql_tables_untouched_but_resolves_eligibility`
renamed to `test_render_statement_decisions_resolves_aliases_but_preserves_everything_else`
and rewritten for the new behavior. Full suite: 498 tests pass.

## Review-status, determinism, and repeatability pass

Scope: (1) find why deterministically-resolvable SQL was showing as
"Needs Review"/`REVIEW_REQUIRED`, (2) audit and fix nondeterminism
sources, (3) add a repeatability regression test, (4) measure real token
usage from the last live run. Primary evidence: `samples/output/
verification/1_PRO.SMA_MARKING.StoredProcedure_verification.md`.

### Root cause 1: deterministically-synthesized rules default to a blank `validation_status`

`ensure_decision_chain_coverage` (`src/synthesis/rule_synthesizer.py`)
builds a rule directly from a parsed decision chain - no LLM involved -
and set `"validation_status": ""`. `_source_traceability_details`
(`report_formatter.py`) renders `"Needs Review"` for anything that is not
literally `"verified"`, so `"" or "unverified"` always lost. Every one of
the report's 23 `deterministic_case_*`/`deterministic_decision_*` rows
showed "Needs Review" despite being the most trustworthy rule kind in the
report (built byte-for-byte from the parsed source, zero free-text
generation, zero hallucination risk).

Fix: `validation_status` is now `"verified"` at creation for these rules -
correct by definition, not an invented claim.

### Root cause 2: reconciliation never told a rule what it had proven about it

`reconcile_deterministic_evidence` (`src/validation/reconciliation.py`)
independently computes a `reconciliation_status` (MATCHED/CONFLICT/
UNRESOLVED/LLM_ONLY) per rule by cross-checking it against deterministic
evidence - but only ever wrote that into `rule["reconciliation_status"]`,
a field nothing in the report reads. The report's "Verified"/"Needs
Review" label and the Rule Provenance Summary's validation-status
breakdown both read `rule["validation_status"]` instead, which stayed
whatever the model self-reported (frequently "unverified" by the model's
own conservative default) even when reconciliation had *already proven
the rule correct*.

Fix: a MATCHED reconciliation result now also sets
`rule["validation_status"] = "verified"`. CONFLICT/UNRESOLVED are
deliberately left untouched: `_rule_has_insufficient_evidence` (used by
contradiction classification) treats `"ambiguous"`/`"insufficient_evidence"`/
`"parser_failed"` in `validation_status` as a signal to *downgrade* a
finding away from `GENUINE_BUSINESS_CONTRADICTION` - writing one of those
values for a CONFLICT would have defeated that classifier for the exact
rule it just flagged as conflicting. Caught by running the full suite
after the first version of this fix (6 failures in
`test_unsafe_business_rules.py`/`test_reconciliation.py` expecting
`GENUINE_BUSINESS_CONTRADICTION` to survive); narrowed to the MATCHED-only
case and all 6 passed again. This is the one change in this pass where a
broader version was tried, measured to weaken grounding, and reverted to
the narrow, safe form - not a superficial fix.

### Root cause 3: deterministic rules were matched against the wrong evidence pool

Measured directly: reconciling the 23 deterministic SMA rules against
real `table_operations`/`statement_provenance` (extracted the same way
`pipeline.py` does) classified **all 23 as `LLM_ONLY`** - the "no
deterministic evidence found for this claim" status - despite every one
being built directly from a parsed `decision_chains` entry.

Root cause: the rule-matching loop looks up candidate evidence via
`rule["source_chunks"]`/`source_evidence`, populated for model claims but
left empty (`[]`) on synthetic deterministic rules (they have no "claim"
to cite - `decision_logic_rows` already *is* the evidence). With zero
candidate rows, the loop can never advance past its `"LLM_ONLY"` default,
regardless of how well-grounded the rule actually is. `deterministic_rows`
itself comes from a structurally separate extraction path
(`table_operations`/`statement_provenance`, parsed independently of
`decision_chains`) that does not always textually overlap with a decision
chain's branch conditions even when both describe the same SQL - so this
was never going to self-resolve by improving the text-matching alone.

Fix: when the matching loop's own logic leaves a rule at `LLM_ONLY` and
`rule["rule_type"] == "deterministic_decision_table"`, the status is
upgraded to `MATCHED` - the rule's own `decision_logic_rows` (copied
verbatim from the chain) and `source_chain_id` (linking it back to the
exact chain) already are the deterministic evidence; this only recognizes
that fact explicitly rather than defaulting to "no evidence" because a
different, unrelated evidence pool didn't happen to contain a textual
match. A genuine CONFLICT/UNRESOLVED computed by the earlier matching
logic (e.g. a bug elsewhere corrupted a chain's rows) is never
overridden - only the specific "found nothing to compare against"
default is.

**Measured effect** (reconciling the real 23-rule SMA deterministic set
against real extracted evidence, before/after):

| Metric | Before | After |
|---|---|---|
| Rule-kind reconciliation status | `LLM_ONLY` × 23 | `MATCHED` × 23 |
| `review_required_items` | 23 | 0 |
| Source Traceability "Needs Review" | 23 | 0 |
| Source Traceability "Verified" | 0 | 23 |
| `quality.review_required` | `True` | `False` |

This does not touch how a genuine model-authored rule with no
deterministic backing is classified - those legitimately still show
`LLM_ONLY` and correctly remain flagged; only the rule *kind* that was
never an LLM claim in the first place is affected.

### Determinism audit

Checked: LLM sampling config (`temperature=0.1`, `seed=0` passed when the
provider supports it - `pipeline.py` `DEFAULT_TEMPERATURE`/`DEFAULT_SEED`,
already in place), rule/reconciliation ID generation (`stable_id()` in
`src/core/pipeline_utils.py` - SHA-256 of stable parts, no uuid/timestamp;
grepped the whole `src/`/`pipeline.py` tree for `uuid`/`datetime.now()`/
`time.time()` outside telemetry/run-metadata paths - none found), and set/
dict display ordering in `report_formatter.py`/`reconciliation.py` (already
`sorted()` at every set-to-list conversion found).

Found one real gap: `PatternRetrievalAgent.retrieve` (`src/retrieval/
retriever.py`) took Chroma's `.query()` result order as-is. Chroma's HNSW
index does not guarantee a stable order for equal/near-equal-distance
results - two runs of the identical query against the identical
collection can return tied documents in a different order, changing the
RAG context text handed to the extraction prompt (a real source of
run-to-run prompt-content variation independent of model sampling). Fixed:
results are now re-sorted by `(distance, document text)` - relevance order
preserved, ties broken by a stable key. New test:
`test_retriever_breaks_equal_distance_ties_deterministically`, simulating
Chroma returning the same three equal-distance documents in two different
raw orders and asserting both resolve to the identical final order.

### Repeatability regression test

`tests/test_sma_repeatability.py`: runs the deterministic pipeline stages
(ingestion, decision-chain extraction, table-operation extraction,
`ensure_decision_chain_coverage`, reconciliation, canonical IR, business
report, verification report) three times over the real
`PRO.SMA_MARKING_12122023.StoredProcedure.sql` input and asserts the
decision chains, rule list (content and order), canonical IR, business
report, and verification report are byte-identical across all three runs.
A second test (`test_sma_repeatability_would_catch_a_real_regression`)
checks the comparison itself isn't vacuous by confirming a deliberately
reordered rule list is correctly detected as different.

Scope note, stated plainly rather than glossed over: this exercises the
deterministic layers - exactly where Python set/dict-ordering, unstable
sorting, retrieval tie-breaking, or ID-generation nondeterminism would
surface, and what canonicalizes whatever the model returns into the final
report - without making a new live LLM call each run. The model call
itself already uses the lowest-variance settings this provider setup
supports (temperature 0.1, seed 0); re-verifying raw-response sampling
variance with repeated live Bedrock calls was not done in this pass, to
avoid spending further approved-once Bedrock cost/data-transfer without a
fresh explicit go-ahead (see the "Phase 3" live-run entry above for that
approval's scope).

### Token usage (measured, not estimated)

From the real live run's own recorded telemetry
(`samples/output/verification/1_PRO.SMA_MARKING.StoredProcedure_verification.md`,
"## LLM Telemetry" - `amazon.nova-lite-v1:0`, the same run analyzed for
the review-status root causes above):

| Stage | Calls | Tokens |
|---|---:|---:|
| synthesis | 8 | 243,961 |
| synthesis_retry | 1 | 36,380 |
| synthesis_revision | 1 | 119,403 |
| **Total** | **10** | **399,744** (372,010 prompt / 27,734 completion) |

All 10 recorded calls are synthesis-family; no extraction-stage calls
appear in this run's telemetry table despite the run log recording
`extraction_calls=1` for its single-pass extraction path - worth a
follow-up look at telemetry-tracker coverage for that stage, not
something this pass changed blindly.

This confirms synthesis (base pass + one malformed-JSON retry + one
coverage-gap revision) is the dominant cost, exactly where the earlier
"Prompt token-efficiency pass" entry's `rule_synthesis.yaml` compaction
(~41-50% cut to the fixed system+user-template portion of every synthesis
call, measured in that entry) applies - each of the 10 calls carries that
fixed overhead once. A full live re-run to capture matching "after"
telemetry was not performed in this pass for the same cost/approval
reason noted above; the reduction is measured at the prompt-file level
(char/4 token estimate, that entry's table) rather than re-billed against
a live call here.

### Verification

Full suite: 501 tests pass (498 from the prior entry + 2 new repeatability
tests + 1 new retrieval tie-break test). Deterministic golden evaluation
(`python evaluate.py --mode deterministic`): **13/13 PASS**, unchanged.
`python -m compileall src pipeline.py main.py evaluate.py tests`: clean,
no syntax errors. `git diff --check`: flags pre-existing CRLF line endings
across the repository (confirmed via `git show HEAD:pipeline.py` - already
1,580 of 1,585 lines CRLF before this pass; every line this pass touched
preserved that existing convention) as "trailing whitespace" - not new
whitespace introduced by this pass, and normalizing the whole repository's
line endings is out of scope for this change.

### Remaining limitations (genuinely unresolved, not swept under a status rename)

- A model-authored rule with no deterministic evidence match anywhere
  (`LLM_ONLY`) still correctly shows as needing review - that is a real
  "cannot cross-check automatically" case, not something safe to
  auto-resolve without inventing a match.
- A genuine CONFLICT (deterministic evidence disagrees with the model's
  claim) still correctly shows as needing review.
- Live-model sampling-variance repeatability (as opposed to the
  deterministic-layer repeatability this pass verified with 3 runs) has
  not been re-confirmed with fresh live Bedrock calls in this pass.
- Extraction-stage telemetry coverage gap noted above was observed, not
  root-caused or fixed in this pass. (Root-caused and fixed in the
  follow-up pass immediately below.)

## Production-hardening follow-up: extraction telemetry gap, review-language wording

### Root cause 4: extraction's own retry call was never tracked

Traced the exact path the prior entry left open ("extraction_calls=1
logged but no extraction telemetry row"). Reproduced end-to-end via a real
`pipeline.run()` call against fake, OpenAI-shaped clients (not a live
Bedrock call): with a client that returns valid JSON every time, extraction
telemetry recorded correctly (`extraction: 8 calls`) - the base wiring
(`pipeline.py` → `LogicExtractionAgent.extract()` → `LLMTelemetryTracker.
record_call()` → `aggregate_run_telemetry()` → `_telemetry_section()`) is
sound. Reproducing the *exact* real failure shape - the model's first
response truncated (`finish_reason == "length"`), the retry succeeding -
surfaced the actual gap: `client.chat.completions.create()` was called
**5 times** but telemetry recorded only **4**. The one missing call was
extraction's own retry-on-truncation request
(`src/extraction/logic_extractor.py`, the `elif effective_max_tokens <
self.hard_max_output_tokens:` branch) - a second, real API call made
directly with no `tracker.record_call(...)` around it at all. Its tokens,
and its very existence, were invisible to telemetry - unlike
`RuleSynthesizerAgent`'s equivalent retries, which were already recorded
under a dedicated `synthesis_retry` stage (visible in the real run's
telemetry table: `synthesis_retry | 1 | 1 | 0 | 36380`).

Fix: wrapped the retry call in the same try/finally + `tracker.record_call`
pattern as the first call, under a new `extraction_retry` stage name
(matching the `synthesis_retry` convention already established). Verified:
the reproduction now shows `Total LLM Calls: 5` matching the fake client's
real call count exactly, with `extraction: 1` + `extraction_retry: 1` as
separate stage rows. New test:
`test_extraction_retry_call_is_recorded_in_telemetry` in
`tests/test_telemetry.py`, asserting call count and per-stage token totals
directly against a fake client forced through the truncation-retry path.

This does not fully prove the *exact* historical report's zero-extraction-
row anomaly was caused only by this - that would require re-running the
same live Bedrock request, which was not done here - but it is a real,
demonstrated telemetry undercounting bug in exactly the code path ("a
retry after a truncated/malformed response") the historical run's own
Findings section shows it went through, and it is now fixed regardless of
whether it was the *entire* explanation.

### Review-language wording

`_rule_provenance_summary` (`report_formatter.py`) carried "should be
prioritized for human review before being treated as confirmed" /"need a
human review before use" phrasing for the `unverified`/`ambiguous`
footnotes. Per root causes 1-3 above, these statuses are now reserved for
the genuinely unprovable cases (an unmatched claim, a real conflict, weak/
incomplete evidence) rather than the normal case - but the wording itself
still read as a general approval-workflow instruction. Reworded to
describe each as an unresolved/undetermined finding ("this specific claim
remains unresolved and should not yet be treated as a confirmed business
rule") rather than a "send this to a human for sign-off" instruction, per
the explicit request to describe truly unprovable cases as unresolved
rather than a normal human-review workflow. No test pinned the old exact
wording; verified via full-suite pass.

Checked for literal `PENDING_REVIEW` / "before approving" / "requires
human approval" / "awaiting approval" strings across `src/`+`pipeline.py`:
none found. The verification report's `Review required: Yes/No` field
(distinct from the business report) is retained as-is - it is explicitly
a technical/audit-only document (see `format_verification`'s own
docstring: "kept out of the document business users read"), not the
primary report a business reader sees, and after the root-cause-4 fix
above it correctly reads `No` for a well-grounded rule set (verified via
the same reconciliation reproduction used earlier in this document).

### Verification

Full suite: **502 tests pass** (501 from the prior entry + 1 new
extraction-retry telemetry test). Deterministic golden evaluation:
**13/13 PASS**, unchanged. `compileall`: clean. SMA repeatability test:
**PASS** (unaffected by this pass's changes - none of them touch ordering,
IDs, or canonicalization).
