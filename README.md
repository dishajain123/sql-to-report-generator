# AI-Powered DB Logic & Business Rules Extractor

An **Agentic RAG** pipeline that reads banking database objects — stored
procedures, functions, views, triggers, or standalone SQL blocks — and
reverse-engineers them into structured, **business-focused** Markdown
documentation. The primary target use case is core-banking / lending
logic such as NPA (Non-Performing Asset) classification and provisioning
calculation procedures governed by RBI IRAC norms.

Both **Oracle PL/SQL and T-SQL (SQL Server) are fully supported**, with
automatic dialect detection (`--dialect auto`, the default) or an
explicit `--dialect oracle`/`--dialect tsql` override. T-SQL support is
not a second code path bolted on — dialect detection, statement-boundary
parsing, and structural SQL validation are dialect-aware throughout the
same pipeline.

Orchestration is **pure Python** — there is no agent framework. Each
agent is a plain class; `pipeline.py` calls their methods in order and
passes data between them as ordinary Python objects/dicts. The two
LLM-calling agents talk to an OpenAI-compatible chat completion API
configured entirely through environment variables (OpenAI, Groq, Ollama,
or AWS Bedrock — see Setup below), and the RAG layer talks to `chromadb`
directly.

The critical design goal: the output explains **what business rule is
being enforced and why**, not a line-by-line restatement of SQL syntax.

> Bad output: *"This is a SELECT statement that reads from LOAN_ACCOUNT."*
> Good output: *"The system checks how many days a loan has been overdue
> to decide whether it should be classified as a Non-Performing Asset and
> how much provisioning to set aside."*

---

## Architecture — Agent Flow

```
                     ┌─────────────────────┐
   .sql file  ─────► │ 1. Code Ingestion    │  detects object type, extracts
                      │    Agent             │  parameters, chunks the code
                      └──────────┬───────────┘  (sqlglot-assisted)
                                 │  code chunks
                                 ▼
                      ┌──────────────────────┐
                      │ 2. Pattern Retrieval  │  ChromaDB similarity search
                      │    Agent (RAG layer)  │  over knowledge_base/
                      └──────────┬───────────┘  (PLSQL patterns + RBI IRAC)
                                 │  chunk + retrieved context
                                 ▼
                      ┌──────────────────────┐
                      │ 3. Logic Extraction   │  per-chunk technical JSON:
                      │    Agent              │  conditions, tables, loops,
                      └──────────┬───────────┘  calcs, exceptions, ambiguities
                                 │  merged technical extraction
                                 ▼
                      ┌──────────────────────┐
                      │ 4. Rule Synthesizer   │  translates extraction into
                      │    Agent (critical)   │  numbered BUSINESS rules —
                      └──────────┬───────────┘  no SQL jargon allowed
                                 │  synthesized business rules
                                 ▼
                      ┌──────────────────────┐
                      │ 5. Report Formatter   │  assembles final Markdown,
                      │    Agent              │  flags ambiguities for review
                      └──────────┬───────────┘
                                 ▼
                        structured .md report
```

Each agent lives in its own module under `src/` and is orchestrated by
`pipeline.py` — plain Python method calls, no agent framework. Ingestion
and report formatting are pure/deterministic (no LLM call); extraction
and rule synthesis call the configured chat model through the OpenAI SDK
(or the Bedrock-compatible client for AWS); retrieval is a local,
file-based `chromadb` collection queried directly with a deterministic
local embedding function.

---

## Project Structure

```
logic-rules-extractor/
├── src/
│   ├── ingestion/          # Code Ingestion: dialect detection, decoding,
│   │                       # parameter/statement parsing, chunking,
│   │                       # deterministic decision-chain + table-op
│   │                       # extraction, called-procedure detection
│   ├── parsing/            # Shared statement-boundary detector used by
│   │                       # both ingestion and the deterministic
│   │                       # extraction path (single implementation)
│   ├── dialect/            # Oracle / T-SQL dialect auto-detection
│   ├── extraction/         # Logic Extraction Agent (LLM, per-chunk)
│   ├── synthesis/          # Rule Synthesizer Agent (LLM, business-
│   │                       # language rules; sectioned/hierarchical
│   │                       # synthesis for large objects)
│   ├── validation/         # Semantic validation, decision-chain merge,
│   │                       # reconciliation/grounding against source,
│   │                       # coverage checking
│   ├── retrieval/          # Pattern Retrieval Agent (RAG / ChromaDB)
│   ├── output/             # Report Formatter Agent
│   ├── batch/              # Batch runner: multi-file runs, call-graph
│   │                       # cross-referencing, batch manifest/index
│   ├── ir/                 # Canonical business-rule intermediate repr.
│   ├── telemetry/          # LLM call telemetry tracking
│   ├── core/               # LLM client (OpenAI/Groq/Ollama/Bedrock),
│   │                       # response cache, shared pipeline utilities
│   └── benchmark/          # Offline evaluation harness
├── knowledge_base/           # Seed docs used to build the vector store
│   ├── rbi_irac_norms.md
│   └── plsql_construct_patterns.md
├── samples/                  # Sample banking .sql inputs
├── config/
│   └── .env.example
├── tests/                     # pytest suite (500+ tests, all deterministic
│                               # paths + fake-LLM-client integration tests)
├── .streamlit/
│   └── config.toml            # Streamlit theme
├── app.py                     # Streamlit frontend
├── pipeline.py                # Orchestrator
├── main.py                    # CLI entry point (single file or batch)
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone / unzip the project and create a virtual environment

```bash
cd logic-rules-extractor
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

Python 3.13 or newer is supported. The pinned Chroma release includes
binary wheels for Windows and Linux, so a C++ compiler and Rust toolchain
are not required.

```bash
pip install -r requirements.txt
```

### 3. Add your LLM settings

Set the provider, API key, model, and base URL in `.env`. Supported providers
are `openai`, `groq`, `ollama`, and `bedrock`:

```bash
cp config/.env.example .env
# OpenAI: set LLM_PROVIDER=openai, LLM_API_KEY, LLM_MODEL_NAME, LLM_BASE_URL
# Groq: set LLM_PROVIDER=groq, GROQ_API_KEY, GROQ_MODEL_NAME
# Ollama: install Ollama, run `ollama pull llama3.1:8b`, then set
# LLM_PROVIDER=ollama and OLLAMA_MODEL_NAME=llama3.1:8b (no API key needed)
# Bedrock: set LLM_PROVIDER=bedrock, AWS credentials/region, and LLM_MODEL_NAME
```

`main.py` loads `.env` automatically via `python-dotenv`. **Never commit
your real `.env` file.**

---

## Usage

Run the pipeline against any of the bundled sample banking objects:

```bash
python main.py samples/npa_classification.sql
```

This prints progress and writes the Markdown report to
`samples/output/npa_classification_report.md`.

### Other useful flags

```bash
# custom output path
python main.py samples/provisioning_summary_view.sql -o out/report.md

# explicit dialect instead of auto-detection
python main.py samples/some_tsql_proc.sql --dialect tsql

# force-rebuild the ChromaDB knowledge base (e.g. after editing knowledge_base/*.md)
python main.py samples/npa_classification.sql --rebuild-kb

# verbose pipeline logging (shows per-stage progress)
python main.py samples/npa_classification.sql -v
```

Full flag reference: `python main.py --help`

### Batch mode (multiple files)

Passing more than one file processes them as a batch — each object still
gets its own independent report, but the batch runner additionally:

- resolves each object's statically-detected `EXEC`/procedure calls
  against the *other* objects in the same batch and adds a "Report"
  column linking straight to the callee's own report (a call to a name
  outside the batch is left as plain text, not guessed at);
- writes a `batch_manifest.json` with per-file status plus a `call_graph`
  (caller/callee/resolved edges, purely derived from the calls actually
  found — no child business logic is invented or copied between reports);
- writes a generated `_batch_index.md` listing objects nothing else in
  the batch calls first (typically the orchestrators — the most useful
  starting point for a reviewer), then everything else.

```bash
python main.py samples/*.sql --output-dir samples/output/batches
```

Single-object-per-file is still the unit of analysis — a batch does not
merge multiple objects declared in one `.sql` file (see Known Limitations).

---

## Streamlit Frontend

A browser UI is included as an alternative to the CLI:

```bash
streamlit run app.py
```

This opens a local page where you can:

- **Use the LLM settings from `.env`** in the sidebar. The provider,
  API key, model, and base URL are read from environment variables and
  not entered manually in the UI.
- **Provide input** by uploading a `.sql` file, pasting code directly, or
  picking one of the three bundled samples under `samples/`.
- **Watch live per-stage progress** (ingestion → retrieval/extraction →
  synthesis → formatting) as the pipeline runs.
- **Review the report** either rendered as Markdown or as raw text, see
  how many items were flagged under "Ambiguities / Needs Review", and
  **download the report as a `.md` file** with one click.
- **Rebuild the knowledge base** on demand from the sidebar (useful after
  editing files in `knowledge_base/`).

---

## Output

The generated Markdown report always follows this exact section
structure:

1. **Object Overview** — name, type, parameters and their business role
2. **Purpose Summary** — 2-4 sentence plain-language business impact
3. **Tables Read** — table, business context, filter conditions
4. **Tables Written** — table, operation type, business trigger
5. **Step-by-Step Logic Flow** — numbered business-language milestones
6. **Business Rules / Validations** — condition → resulting action table
7. **Calculations / Formulas** — plain-language breakdown of any math
8. **Exception Handling Behavior** — operational risk summary
9. **Ambiguities / Needs Review** — anything not confidently inferred
   (unresolved dynamic SQL, malformed model output, leftover jargon, or
   "None" if nothing was flagged) — the pipeline never silently guesses.

---

## Running Tests

```bash
pip install -r requirements.txt   # includes chromadb, boto3, openai, pytest
pytest tests/ -v
```

The suite (500+ tests) covers the deterministic ingestion/parsing/
chunking/decision-chain paths directly against real SQL, plus the
LLM-calling agents against fake, OpenAI-shaped clients (no live API key
needed to run the suite) — including scripted failure/retry scenarios for
the LLM reliability behavior described below.

---

## Known Limitations

- **Dynamic SQL** (Oracle `EXECUTE IMMEDIATE`, T-SQL `EXEC(@sql)` /
  `sp_executesql`) cannot be statically resolved to a fixed table/
  condition; it is always flagged under "Ambiguities / Needs Review"
  rather than guessed.
- Embedded DML (SELECT/INSERT/UPDATE/DELETE/MERGE) is structurally
  validated with `sqlglot`; procedural control flow around it
  (IF/BEGIN/WHILE/CURSOR/EXCEPTION handling) is not itself SQL and is
  handled by the shared statement-boundary detector
  (`src/parsing/statement_boundaries.py`) rather than passed to sqlglot.
- Multi-object `.sql` files (more than one procedure/view/etc. in a
  single file) are not supported — provide one DB object per file. Batch
  mode (see above) cross-references calls *between* files in a batch, but
  does not merge multiple objects declared inside one file.
- Very large objects (100KB+, tens of chunks) are handled by boundary-
  aware chunking plus hierarchical/sectioned rule synthesis rather than
  one oversized call, but chunk/section count still scales with object
  size — expect proportionally more LLM calls for very large procedures.
- A single LLM call failing after bounded retry degrades just that
  chunk/section to empty evidence rather than aborting the whole run, and
  the report is marked with a visible "DEGRADED RUN" banner when this
  happens — the affected portion should be reviewed or the run retried,
  since the report is not necessarily complete.
- Retry/backoff for transient LLM failures (rate limits, timeouts, 5xx)
  is applied automatically: the `openai`-SDK-backed providers (OpenAI,
  Groq, Ollama) retry via the SDK's own defaults; the AWS Bedrock client
  has its own bounded exponential-backoff retry layer (`src/core/
  llm_client.py`), on top of botocore's standard retry mode when the
  `boto3` client path is available.
- Extraction quality depends on the curated `knowledge_base/` content;
  extending it with more domain-specific patterns (e.g. additional RBI
  circular thresholds specific to your institution) will materially
  improve output quality on more complex procedures.

## Possible Future Improvements

- Add Excel/JSON output formats alongside Markdown (`openpyxl` /
  pydantic models are already listed as suggested stack components).
- Add a confidence score per extracted business rule.
- Merge multiple objects declared in a single `.sql` file.
- Add a lightweight LangGraph-based agent graph for retry/self-critique
  loops on low-confidence chunks before final synthesis.
