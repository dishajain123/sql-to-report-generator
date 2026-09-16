# Design Notes — AI-Powered DB Logic & Business Rules Extractor

## Key Design Decisions

**Merge small structural sections before calling the LLM.** Early on,
each declaration/cursor/nested-block/exception region became its own
chunk, which meant one LLM call per tiny fragment - unnecessarily many
calls for a modestly-sized procedure. `chunk_code` now greedily merges
adjacent sections back together up to `max_chunk_chars` before the
extraction stage runs, and the ceiling itself was raised (3,000 → 6,000
chars) since modern chat models comfortably support far larger prompts.
A typical small-to-medium object now produces a small handful of chunks
- and therefore a small handful of extraction calls - instead of one per
structural region, while still guaranteeing no single chunk risks
overflowing the model's context window (oversized merged sections still
fall back to statement-boundary splitting). `MAX_CHUNK_CHARS` lives in
exactly one place (`src/ingestion/ingestion.py`); `pipeline.py` imports
it rather than hardcoding its own default, so a `CodeIngestionAgent`
built directly (tests, scripts) and the real pipeline can never silently
disagree on chunk size.

For genuinely large real-world objects (100KB+, 20-40+ chunks - not
uncommon for orchestrator-heavy batch stored procedures), a flat "small
handful of chunks" no longer holds, and cross-chunk coherence for rule
synthesis becomes the real risk (a single whole-object synthesis call is
virtually guaranteed to exceed the output-token ceiling and truncate).
`RuleSynthesizerAgent.requires_sectioned_synthesis` /
`plan_synthesis_sections` detect this and switch rule synthesis to a
hierarchical pass - one synthesis call per logical section, reusing the
same chunk boundaries extraction already produced, merged back into one
result by `merge_section_results` - rather than one oversized call or an
arbitrarily raised chunk-size ceiling. Extraction itself stays per-chunk
either way; deterministic decision-chain extraction runs over the whole
raw source in a single pass regardless of chunk count, so it is inherently
unaffected by chunk boundaries.

**Plain Python orchestration, no agent framework.** Each agent is an
independent class with a small, explicit method signature (e.g.
`extract(...) -> ChunkExtraction`). `pipeline.py` calls them directly and
passes plain Python objects/dicts between stages. LLM calls go through
an OpenAI-compatible chat completions client
(`client.chat.completions.create(...)`), configured for OpenAI, Groq,
Ollama, or AWS Bedrock via `src/core/llm_client.py`, and the RAG layer
talks to `chromadb` directly. This keeps the dependency surface
small, makes every prompt and every parsing step fully visible/greppable
in one file each, and makes each agent trivial to unit test by mocking a
plain object instead of a framework-specific chain/runnable.

**Two-stage extraction (technical → business), not one LLM call.**
A single prompt asked to go straight from raw PL/SQL to "business rules"
tends to either leak SQL syntax into the output or hallucinate plausible-
sounding business meaning it can't actually support. Splitting this into
a Logic Extraction Agent (technical, precise, still allowed to use SQL
terms) and a separate Rule Synthesizer Agent (business language only, with
an explicit banned-word list and a post-hoc jargon scanner) made each
prompt smaller, more testable, and much more reliable at holding the
"business intent, not syntax" line that the project's evaluation criteria
weight most heavily.

**Deterministic ingestion and formatting; LLM only where judgment is
needed.** The Code Ingestion Agent (object detection, parameter parsing,
chunking) and the Report Formatter Agent are pure Python with no LLM
calls. This keeps object-type detection and the final Markdown structure
100% reproducible, and confines LLM variance to the two stages that
actually require interpretation.

**sqlglot used narrowly, not as a full procedural parser.** sqlglot parses
embedded SQL statements (SELECT/INSERT/UPDATE/DELETE/MERGE) well in both
the Oracle and T-SQL dialects, but it does not model procedural control
flow (Oracle IF/LOOP/EXCEPTION, T-SQL IF/BEGIN/WHILE/TRY-CATCH). Rather
than forcing a mismatched tool, the ingestion agent uses sqlglot only to
structurally validate embedded SQL, and uses `src/parsing/
statement_boundaries.py` - a single, shared, dependency-free
statement-boundary detector - for the procedural chunking. This was a
deliberate scope decision after early experiments where trying to make
sqlglot "understand" IF/LOOP constructs produced brittle, hard-to-debug
code. That boundary detector is deliberately the *only* implementation of
this logic in the codebase: it is imported by both the ingestion
statement-validation path and the deterministic table-operation
extraction path, specifically so a boundary-detection fix (e.g.
recognizing `IF`/`EXEC`/`DROP`/`CREATE`/`PRINT` as statement starts, not
just DML keywords) lands once and benefits every caller, rather than
risking two independent splitters silently drifting apart.

**Local, file-based RAG (Chroma + deterministic local embeddings).** Domain
context (RBI IRAC thresholds, PLSQL construct meanings) is retrieved
per-chunk before extraction so the model correctly interprets constructs
like cursors, MERGE, and overdue-day branching in banking terms rather
than generic terms. A deterministic hash-based embedding function runs
locally (no model download or extra API cost/latency), keeping only the
two reasoning stages dependent on the Groq API. Chroma is pinned to a
release with platform wheels so setup does not compile native dependencies.

**Never silently guess.** Every stage that can fail to confidently
interpret something (malformed JSON from the model, unresolved dynamic
SQL, a jargon-scanner hit) writes to an `ambiguities` list rather than
being dropped or backfilled with a plausible guess. The Report Formatter
merges all of these into one explicit "Ambiguities / Needs Review"
section — this was treated as a hard requirement (FR8), not a nice-to-have.

**Bounded retry for transient LLM failures; visible degradation, not
silent gaps, for permanent ones.** The `openai`-SDK-backed providers
(OpenAI, Groq, Ollama) already retry transient errors (timeouts,
connection errors, 429/5xx) by default at the SDK level. The AWS Bedrock
client - both its boto3 path and its raw-HTTP fallback for environments
without boto3 - previously had no retry at all; `src/core/llm_client.py`
now classifies failures into `LLMTransientError` (rate limit, timeout,
network error, 5xx - retried with bounded exponential backoff + jitter
via `call_with_retry`) versus a permanent `RuntimeError` (bad request,
auth, malformed response - never retried, since retrying can't fix them).
Separately, a chunk extraction or rule-synthesis call that still fails
after retry is exhausted degrades *that one chunk/section* to empty
evidence (mirroring the pattern already used for full-source-extraction
failure) rather than aborting the whole run - but the run's telemetry
records `degraded`/`failed_chunk_count`/`failed_section_count`, and the
business report renders a loud "DEGRADED RUN" banner when set, so a
report missing evidence from a transient failure is never visually
indistinguishable from a fully clean one.

**Batch mode treats the batch as a graph, not N independent files.**
`IngestionResult.called_procedures` already captures every statically-
resolvable `EXEC`/procedure-call target per object. `src/batch/
batch_runner.py` resolves those calls against the *other* objects in the
same batch run (schema-qualified matches always trusted; an unqualified
name is only trusted when it's unique across the batch, to avoid
guessing between two same-named objects in different schemas) and
rewrites the caller's own report with a link to the callee's report,
plus writes a batch-level call graph and a generated index that surfaces
objects nothing else in the batch calls (typically orchestrators) first.
This deliberately reuses the single existing rendering function
(`ReportFormatterAgent.render_called_procedures_section`) for both the
single-file and batch-augmented cases, and never invents or copies a
callee's business logic into the caller's report - only a link.

**LLM telemetry is observability only.** The pipeline now records
provider-neutral token usage and latency for extraction/synthesis calls
through a small `src/telemetry/` module, then stores the aggregated
result inside the existing run/verification metadata. This data is kept
out of the business-facing Markdown report and never influences
extraction, synthesis, confidence, reconciliation, or caching.

## Known Limitations

- Dynamic SQL (Oracle `EXECUTE IMMEDIATE`, T-SQL `EXEC(@sql)`/
  `sp_executesql`) content is never resolved — always flagged.
- One DB object per input file; multi-object files are out of scope.
  Batch mode (multiple files in one run) cross-references calls between
  files, but still does not merge multiple objects declared inside one
  file.
- Chunk/section count scales with object size — a very large object
  still means proportionally more LLM calls, even with boundary-aware
  chunking and sectioned synthesis (see above).
- A permanently-failing LLM call degrades its own chunk/section rather
  than the whole run, but the report is then only as complete as what did
  succeed — the "DEGRADED RUN" banner is the signal to review or re-run,
  not an automatic recovery.
- Extraction quality is bounded by the curated knowledge base — it is a
  starting seed (RBI IRAC thresholds + common construct patterns), not an
  exhaustive regulatory reference.

## Possible Future Improvements

- Confidence scoring per extracted rule, surfaced in the report.
- Excel/JSON output in addition to Markdown.
- Self-critique / retry loop (e.g. via LangGraph) for chunks whose
  extraction comes back with ambiguities, before final synthesis.
- Additional dialect support beyond Oracle PL/SQL and T-SQL (e.g.
  PostgreSQL/MySQL procedural SQL).
- Merging multiple objects declared in a single `.sql` file.
