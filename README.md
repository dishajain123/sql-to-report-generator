# AI-Powered DB Logic & Business Rules Extractor

An **Agentic RAG** pipeline that reads banking database objects — stored
procedures, functions, views, triggers, or standalone PL/SQL blocks — and
reverse-engineers them into structured, **business-focused** Markdown
documentation. The primary target use case is core-banking / lending
logic such as NPA (Non-Performing Asset) classification and provisioning
calculation procedures governed by RBI IRAC norms.

Orchestration is **pure Python** — there is no agent framework. Each
agent is a plain class; `pipeline.py` calls their methods in order and
passes data between them as ordinary Python objects/dicts. The two
LLM-calling agents talk to Groq directly via the official `groq` SDK, and
the RAG layer talks to `chromadb` directly.

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

Each agent lives in its own module under `agents/` and is orchestrated by
`pipeline.py` — plain Python method calls, no agent framework. Agents 1
and 5 are pure/deterministic (no LLM call); agents 3 and 4 call the
configured Groq model directly via the `groq` SDK; agent 2 is a local,
file-based `chromadb` collection queried directly (embeddings via
chromadb's built-in sentence-transformers embedding function).

---

## Project Structure

```
logic-rules-extractor/
├── agents/
│   ├── __init__.py
│   ├── ingestion.py          # Code Ingestion Agent
│   ├── retriever.py          # Pattern Retrieval Agent (RAG / ChromaDB)
│   ├── logic_extractor.py    # Logic Extraction Agent
│   ├── rule_synthesizer.py   # Rule Synthesizer Agent (business-language)
│   └── report_formatter.py   # Report Formatter Agent
├── knowledge_base/           # Seed docs used to build the vector store
│   ├── rbi_irac_norms.md
│   └── plsql_construct_patterns.md
├── samples/                  # Sample banking .sql inputs
│   ├── npa_classification.sql
│   ├── provisioning_summary_view.sql
│   └── batch_overdue_ageing_block.sql
├── config/
│   └── .env.example
├── tests/
│   ├── test_ingestion.py
│   └── test_rule_synthesizer.py
├── .streamlit/
│   └── config.toml            # Streamlit theme
├── app.py                     # Streamlit frontend
├── pipeline.py                # Orchestrator
├── main.py                    # CLI entry point
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

```bash
pip install -r requirements.txt
```

### 3. Add your Groq API key

Get a free-tier key from [console.groq.com](https://console.groq.com/),
then:

```bash
cp config/.env.example .env
# edit .env and set GROQ_API_KEY=your_key_here
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

### Switch the Groq model at call time

```bash
python main.py samples/npa_classification.sql --model llama-3.1-8b-instant
python main.py samples/npa_classification.sql --model llama-3.3-70b-versatile
```

### Other useful flags

```bash
# custom output path
python main.py samples/provisioning_summary_view.sql -o out/report.md

# force-rebuild the ChromaDB knowledge base (e.g. after editing knowledge_base/*.md)
python main.py samples/npa_classification.sql --rebuild-kb

# verbose pipeline logging (shows per-stage progress)
python main.py samples/npa_classification.sql -v
```

Full flag reference: `python main.py --help`

---

## Streamlit Frontend

A browser UI is included as an alternative to the CLI:

```bash
streamlit run app.py
```

This opens a local page where you can:

- **Enter your Groq API key** in the sidebar (falls back to `GROQ_API_KEY`
  from `.env` if already set — the key is only held in the browser
  session, never written to disk).
- **Switch the Groq model** from a dropdown (`llama-3.3-70b-versatile`,
  `llama-3.1-8b-instant`, or a custom model name) — the vector store and
  Groq client are cached and reused, so switching models between runs is
  instant, no rebuild required.
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
pip install pytest
pytest tests/ -v
```

`test_ingestion.py` exercises the deterministic parsing/chunking logic
directly. `test_rule_synthesizer.py` mocks the LLM call so JSON-parsing,
fallback, and jargon-detection behavior can be verified without a live
Groq API key.

---

## Known Limitations

- **Dynamic SQL** (`EXECUTE IMMEDIATE` with a runtime-built string) cannot
  be statically resolved to a fixed table/condition; it is always flagged
  under "Ambiguities / Needs Review" rather than guessed.
- **sqlglot** validates embedded SQL statements (SELECT/INSERT/UPDATE/
  DELETE/MERGE) structurally, but does not parse PL/SQL procedural
  control flow (IF/LOOP/CURSOR/EXCEPTION) — those regions are chunked via
  structural heuristics instead.
- Multi-object `.sql` files (more than one procedure/view/etc. in a
  single file) are not supported — provide one DB object per file.
- Extraction quality depends on the curated `knowledge_base/` content;
  extending it with more domain-specific patterns (e.g. additional RBI
  circular thresholds specific to your institution) will materially
  improve output quality on more complex procedures.

## Possible Future Improvements

- Add Excel/JSON output formats alongside Markdown (`openpyxl` /
  pydantic models are already listed as suggested stack components).
- Add a confidence score per extracted business rule.
- Support T-SQL / other dialects beyond Oracle PL/SQL.
- Add a lightweight LangGraph-based agent graph for retry/self-critique
  loops on low-confidence chunks before final synthesis.
