# Design Notes — AI-Powered DB Logic & Business Rules Extractor

## Key Design Decisions

**Merge small structural sections before calling the LLM.** Early on,
each declaration/cursor/nested-block/exception region became its own
chunk, which meant one Groq call per tiny fragment - unnecessarily many
calls for a modestly-sized procedure. `chunk_code` now greedily merges
adjacent sections back together up to `max_chunk_chars` before the
extraction stage runs, and the ceiling itself was raised (3,000 → 6,000
chars) since Groq's Llama 3.3 models comfortably support far larger
prompts. A typical object now produces a small handful of chunks - and
therefore a small handful of extraction calls - instead of one per
structural region, while still guaranteeing no single chunk risks
overflowing the model's context window (oversized merged sections still
fall back to statement-boundary splitting).

**Plain Python orchestration, no agent framework.** Each agent is an
independent class with a small, explicit method signature (e.g.
`extract(...) -> ChunkExtraction`). `pipeline.py` calls them directly and
passes plain Python objects/dicts between stages. LLM calls go straight
to the `groq` SDK (`client.chat.completions.create(...)`) and the RAG
layer talks to `chromadb` directly. This keeps the dependency surface
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

**sqlglot used narrowly, not as a full PL/SQL parser.** sqlglot parses
embedded SQL statements (SELECT/INSERT/UPDATE/DELETE/MERGE) well, but it
does not model PL/SQL procedural control flow (IF/LOOP/CURSOR/EXCEPTION
blocks). Rather than forcing a mismatched tool, the ingestion agent uses
sqlglot only to structurally validate embedded SQL, and uses regex/
structural heuristics for the procedural chunking. This was a deliberate
scope decision after early experiments where trying to make sqlglot
"understand" IF/LOOP constructs produced brittle, hard-to-debug code.

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

**LLM telemetry is observability only.** The pipeline now records
provider-neutral token usage and latency for extraction/synthesis calls
through a small `src/telemetry/` module, then stores the aggregated
result inside the existing run/verification metadata. This data is kept
out of the business-facing Markdown report and never influences
extraction, synthesis, confidence, reconciliation, or caching.

## Known Limitations

- Dynamic SQL (`EXECUTE IMMEDIATE`) content is never resolved — always
  flagged.
- One DB object per input file; multi-object files are out of scope.
- Chunking heuristics are tuned for Oracle-style PL/SQL; T-SQL support
  would need a second detection/chunking path.
- Extraction quality is bounded by the curated knowledge base — it is a
  starting seed (RBI IRAC thresholds + common construct patterns), not an
  exhaustive regulatory reference.

## Possible Future Improvements

- Confidence scoring per extracted rule, surfaced in the report.
- Excel/JSON output in addition to Markdown.
- Self-critique / retry loop (e.g. via LangGraph) for chunks whose
  extraction comes back with ambiguities, before final synthesis.
- T-SQL and additional dialect support.
