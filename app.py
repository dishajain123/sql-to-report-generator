"""
app.py
-------
Streamlit frontend for the AI-Powered DB Logic & Business Rules Extractor.

Lets a user upload (or paste) a banking .sql object, run the five-agent
pipeline with a live per-stage progress view, and download the resulting
Markdown report. All LLM settings are read from `.env`.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import json
import logging
import tempfile
from contextlib import contextmanager
from pathlib import Path
import re

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from llm_client import LLMConfig, load_llm_config
from pipeline import LogicRulesExtractorPipeline, PipelineInputError

load_dotenv(override=True)

APP_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = APP_DIR / "samples"
OUTPUT_DIR = SAMPLES_DIR / "output"
LOGS_DIR = OUTPUT_DIR / "logs"
PIPELINE_CACHE_VERSION = "2026-08-24-report-format-v3"
DIALECT_OPTIONS = {
    "Auto-detect": "auto",
    "Oracle SQL / PL-SQL": "oracle",
    "SQL Server T-SQL": "tsql",
}

st.set_page_config(
    page_title="DB Logic & Business Rules Extractor",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Light custom styling
# --------------------------------------------------------------------------

st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; max-width: 1100px; }
        .lre-eyebrow {
            font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase;
            color: #64748B; font-weight: 600; margin-bottom: 0.15rem;
        }
        .lre-badge {
            display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px;
            background: #EEF2F7; color: #155E75; font-size: 0.75rem; font-weight: 600;
            margin-right: 0.4rem;
        }
        div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _render_copy_button(text: str) -> None:
    """Render a lightweight clipboard button for markdown output."""
    payload = json.dumps(text)
    components.html(
        f"""
        <div style="display:flex; justify-content:flex-end; margin: 0.15rem 0 0.5rem 0;">
            <button
                id="copy-raw-md"
                style="
                    background:#0F766E;
                    color:white;
                    border:none;
                    border-radius:0.5rem;
                    padding:0.55rem 0.9rem;
                    font-size:0.9rem;
                    font-weight:600;
                    cursor:pointer;
                "
            >
                Copy raw markdown
            </button>
        </div>
        <script>
            const button = document.getElementById("copy-raw-md");
            const rawMarkdown = {payload};

            button.addEventListener("click", async () => {{
                try {{
                    await navigator.clipboard.writeText(rawMarkdown);
                }} catch (err) {{
                    const textarea = document.createElement("textarea");
                    textarea.value = rawMarkdown;
                    textarea.style.position = "fixed";
                    textarea.style.opacity = "0";
                    document.body.appendChild(textarea);
                    textarea.focus();
                    textarea.select();
                    document.execCommand("copy");
                    document.body.removeChild(textarea);
                }}

                const previous = button.textContent;
                button.textContent = "Copied";
                setTimeout(() => {{
                    button.textContent = previous;
                }}, 1200);
            }});
        </script>
        """,
        height=58,
    )


def _pipeline_cache_signature() -> tuple[int, ...] | tuple[str, ...]:
    """Bust the Streamlit resource cache whenever the generation code changes.

    A cached pipeline object can otherwise survive code edits inside a long-
    running Streamlit session and continue rendering an older report layout.
    Using source file mtimes keeps the cache tied to the actual report
    generation code rather than the app session lifetime.
    """
    source_files = [
        APP_DIR / "pipeline.py",
        APP_DIR / "agents" / "ingestion.py",
        APP_DIR / "agents" / "logic_extractor.py",
        APP_DIR / "agents" / "report_formatter.py",
        APP_DIR / "agents" / "rule_synthesizer.py",
    ]
    signature: list[int | str] = [PIPELINE_CACHE_VERSION]
    for path in source_files:
        try:
            signature.append(path.stat().st_mtime_ns)
        except FileNotFoundError:
            signature.append(0)
    return tuple(signature)

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------

st.markdown('<div class="lre-eyebrow">Agentic RAG &middot; Core Banking</div>', unsafe_allow_html=True)
st.title("🏦 DB Logic & Business Rules Extractor")
st.write(
    "Turn a banking stored procedure, function, view, trigger, or PL/SQL block "
    "into a structured, **business-focused** Markdown report — what it does and "
    "why, not a restatement of the SQL."
)
st.markdown(
    '<span class="lre-badge">5-agent pipeline</span>'
    '<span class="lre-badge">Env-configured LLM</span>'
    '<span class="lre-badge">ChromaDB RAG</span>',
    unsafe_allow_html=True,
)
st.divider()

# --------------------------------------------------------------------------
# Sidebar — configuration
# --------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Configuration")

    try:
        llm_config = load_llm_config()
    except EnvironmentError as exc:
        st.error(str(exc))
        st.stop()

    st.caption(f"Provider: `{llm_config.provider}`")
    st.caption(f"Model: `{llm_config.model_name}`")
    if llm_config.base_url:
        st.caption(f"Base URL: `{llm_config.base_url}`")
    st.caption("API key is read from `.env` and never shown in the UI.")

    st.subheader("SQL Dialect")
    dialect_choice_label = st.selectbox(
        "SQL dialect",
        list(DIALECT_OPTIONS.keys()),
        index=0,
        help="Auto-detect works from structural signals in the source "
        "(GO batches, @variables, EXCEPTION vs TRY/CATCH, etc.). Override "
        "explicitly if detection seems wrong for a given file.",
    )
    dialect_choice = DIALECT_OPTIONS[dialect_choice_label]

    with st.expander("Advanced settings"):
        temperature = st.slider(
            "Temperature", min_value=0.0, max_value=1.0, value=0.1, step=0.05,
            help="Low values keep extraction deterministic and literal.",
        )
        retrieval_k = st.slider(
            "Retrieved pattern docs per chunk (k)", min_value=1, max_value=8, value=4,
        )
        persist_directory = st.text_input("Chroma persist directory", value="chroma_store")
        knowledge_base_dir = st.text_input("Knowledge base directory", value="knowledge_base")
        rebuild_kb = st.button("🔄 Rebuild knowledge base from disk")

    st.divider()
    st.caption(
        "This app reads the provider, API key, model, and base URL from `.env`."
    )


# --------------------------------------------------------------------------
# Pipeline construction (cached — persists the Chroma store / embedding
# model / LLM client across reruns)
# --------------------------------------------------------------------------


@st.cache_resource(show_spinner="Loading knowledge base and embedding model…")
def get_pipeline(
    llm_config: LLMConfig, persist_dir: str, kb_dir: str, cache_signature
) -> LogicRulesExtractorPipeline:
    return LogicRulesExtractorPipeline(
        llm_config=llm_config,
        persist_directory=persist_dir,
        knowledge_base_dir=kb_dir,
        dialect="auto",
    )


def _next_output_path(stem: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing_numbers = []
    for path in OUTPUT_DIR.glob(f"*_{stem}_report.md"):
        match = re.match(r"^(\d+)_", path.name)
        if match:
            existing_numbers.append(int(match.group(1)))
    next_number = (max(existing_numbers) + 1) if existing_numbers else 1
    return OUTPUT_DIR / f"{next_number}_{stem}_report.md"


def _next_run_number(stem: str) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing_numbers = []
    for path in OUTPUT_DIR.glob(f"*_{stem}_report.md"):
        match = re.match(r"^(\d+)_", path.name)
        if match:
            existing_numbers.append(int(match.group(1)))
    return (max(existing_numbers) + 1) if existing_numbers else 1


def _run_paths(stem: str) -> tuple[int, Path, Path]:
    run_number = _next_run_number(stem)
    report_path = OUTPUT_DIR / f"{run_number}_{stem}_report.md"
    log_path = LOGS_DIR / f"{run_number}_{stem}_pipeline.log"
    return run_number, report_path, log_path


@contextmanager
def _capture_run_logs(log_path: Path):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    previous_level = root_logger.level
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root_logger.addHandler(handler)
    if previous_level > logging.INFO or previous_level == logging.NOTSET:
        root_logger.setLevel(logging.INFO)
    try:
        yield
    finally:
        root_logger.removeHandler(handler)
        handler.close()
        root_logger.setLevel(previous_level)


def _render_run_status(stage_index: int, last_message: str, messages: list[str], log_path: Path) -> str:
    stage_names = [
        "Input guardrails",
        "Dialect detection",
        "Preprocessing and chunking",
        "Embedded SQL / technical extraction",
        "Business reasoning",
        "Output guardrails / formatting",
    ]
    cards = []
    for idx, name in enumerate(stage_names, start=1):
        if stage_index > idx:
            mark = "✅"
            state = "Done"
        elif stage_index == idx:
            mark = "⏳"
            state = "Working"
        else:
            mark = "⬜"
            state = "Pending"
        cards.append(f"- {mark} **Stage {idx}**: {name} - {state}")

    recent = messages[-4:]
    recent_block = "\n".join(f"- {msg}" for msg in recent) if recent else "- Waiting to start."
    return (
        "### Live Run Status\n\n"
        f"- **Current step:** {last_message or 'Starting...'}\n"
        f"- **Stage progress:** {stage_index}/6\n"
        f"- **Log file:** `{log_path}`\n\n"
        "**Pipeline stages**\n"
        + "\n".join(cards)
        + "\n\n**Recent updates**\n"
        + recent_block
    )


# --------------------------------------------------------------------------
# Main — input
# --------------------------------------------------------------------------

st.subheader("1. Provide a DB object")

source = st.radio(
    "Input source",
    ["Upload a .sql file", "Paste code", "Use a bundled sample"],
    horizontal=True,
    label_visibility="collapsed",
)

sql_code: str | None = None
sql_filename = "input.sql"

if source == "Upload a .sql file":
    uploaded = st.file_uploader(
        "Upload a .sql file",
        type=["sql", "prc", "pks", "pkb", "txt"],
        label_visibility="collapsed",
    )
    if uploaded is not None:
        sql_code = uploaded.getvalue().decode("utf-8", errors="replace")
        sql_filename = uploaded.name

elif source == "Paste code":
    sql_code = st.text_area(
        "Paste PL/SQL code",
        height=280,
        placeholder="CREATE OR REPLACE PROCEDURE classify_npa_and_provision (...) IS\n...",
        label_visibility="collapsed",
    )
    sql_code = sql_code or None

else:
    if SAMPLES_DIR.exists():
        sample_files = sorted(p.name for p in SAMPLES_DIR.glob("*.sql"))
    else:
        sample_files = []

    if sample_files:
        chosen = st.selectbox("Choose a bundled sample", sample_files)
        sql_code = (SAMPLES_DIR / chosen).read_text(encoding="utf-8", errors="replace")
        sql_filename = chosen
        with st.expander("Preview sample code", expanded=False):
            st.code(sql_code, language="sql")
    else:
        st.warning(f"No sample .sql files found in `{SAMPLES_DIR}/`.")

st.subheader("2. Run the pipeline")

run_clicked = st.button(
    "🚀 Run Extraction", type="primary", disabled=not sql_code, use_container_width=False
)

# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------

if run_clicked:
    try:
        pipeline = get_pipeline(
            llm_config,
            persist_directory,
            knowledge_base_dir,
            _pipeline_cache_signature(),
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to initialize the pipeline: {exc}")
        st.stop()

    if rebuild_kb:
        with st.spinner("Rebuilding knowledge base…"):
            pipeline.retrieval_agent.build_or_load(force_rebuild=True)

    # apply the sidebar's live settings to the cached pipeline instance
    pipeline.retrieval_k = retrieval_k
    pipeline.extraction_agent.temperature = temperature
    pipeline.synthesizer_agent.temperature = temperature

    tmp_path = None
    try:
        run_number, report_path, log_path = _run_paths(Path(sql_filename).stem)
        run_state = {
            "messages": [],
            "current_stage": 0,
            "latest_message": "Starting...",
        }
        status_panel = st.container(border=True)
        status_placeholder = status_panel.empty()
        progress_bar = status_panel.progress(0)

        def _refresh_status() -> None:
            progress_bar.progress(min(int((run_state["current_stage"] / 6) * 100), 100))
            status_placeholder.markdown(
                _render_run_status(
                    run_state["current_stage"],
                    run_state["latest_message"],
                    run_state["messages"],
                    log_path,
                )
            )

        _refresh_status()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sql", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(sql_code)
            tmp_path = tmp.name

        with st.status("Running the pipeline…", expanded=False) as status:
            with _capture_run_logs(log_path):
                logging.getLogger(__name__).info("Run %s started for %s", run_number, sql_filename)

                def on_progress(message: str) -> None:
                    run_state["messages"].append(message)
                    stage_match = re.match(r"^Stage\s+(\d+)/(\d+):\s*(.*)$", message)
                    if stage_match:
                        run_state["current_stage"] = int(stage_match.group(1))
                        run_state["latest_message"] = stage_match.group(3).strip()
                    else:
                        run_state["latest_message"] = message
                    _refresh_status()

                report = pipeline.run(tmp_path, dialect=dialect_choice, progress_callback=on_progress)
                run_state["current_stage"] = 6
                run_state["latest_message"] = "Extraction complete"
                run_state["messages"].append("Pipeline completed successfully.")
                _refresh_status()
                status.update(label="Extraction complete ✅", state="complete")

        report_path.write_text(report, encoding="utf-8")
        logging.getLogger(__name__).info("Saved report to %s", report_path)
        logging.getLogger(__name__).info("Saved run log to %s", log_path)

        st.session_state["last_report"] = report
        st.session_state["last_stem"] = Path(sql_filename).stem
        st.session_state["last_model"] = pipeline.model_name
        st.session_state["last_saved_path"] = str(report_path)
        st.session_state["last_log_path"] = str(log_path)
        st.session_state["last_run_number"] = run_number
        st.session_state["last_run_messages"] = run_state["messages"]

    except PipelineInputError as exc:
        st.error(f"Input rejected by guardrails: {exc}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Pipeline error: {exc}")
        st.exception(exc)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------

if "last_report" in st.session_state:
    st.divider()
    st.subheader("3. Business logic report")

    report_md: str = st.session_state["last_report"]
    ambiguity_count = 0
    ambiguities_section = report_md.split("## Ambiguities / Needs Review", 1)
    if len(ambiguities_section) == 2:
        tail = ambiguities_section[1].strip()
        if not tail.lower().startswith("none"):
            ambiguity_count = sum(1 for line in tail.splitlines() if line.strip().startswith("- "))

    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        st.metric("Model used", st.session_state.get("last_model", "—"))
    with col2:
        st.metric("Flagged for review", ambiguity_count)
    with col3:
        st.download_button(
            "⬇️ Download Markdown report",
            data=report_md,
            file_name=f"{st.session_state.get('last_stem', 'report')}_report.md",
            mime="text/markdown",
            type="primary",
            use_container_width=True,
        )

    st.caption(
        f"Saved to: `{st.session_state.get('last_saved_path', OUTPUT_DIR / (st.session_state.get('last_stem', 'report') + '_report.md'))}`"
    )
    if "last_log_path" in st.session_state:
        st.caption(f"Run log saved to: `{st.session_state['last_log_path']}`")

    if ambiguity_count:
        st.warning(
            f"{ambiguity_count} item(s) flagged for human review — see the "
            "**Ambiguities / Needs Review** section below."
        )

    if "last_run_messages" in st.session_state:
        with st.expander("Run status summary", expanded=False):
            st.markdown(
                _render_run_status(
                    6,
                    "Extraction complete",
                    st.session_state.get("last_run_messages", []),
                    Path(st.session_state.get("last_log_path", LOGS_DIR / "run.log")),
                )
            )

    tab_rendered, tab_raw = st.tabs(["📖 Rendered", "🔤 Raw Markdown"])
    with tab_rendered:
        st.markdown(report_md)
    with tab_raw:
        toolbar_left, toolbar_right = st.columns([1, 4])
        with toolbar_left:
            st.download_button(
                "⬇️ Download raw markdown",
                data=report_md,
                file_name=f"{st.session_state.get('last_stem', 'report')}_report.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with toolbar_right:
            _render_copy_button(report_md)
        st.text_area(
            "Raw Markdown",
            value=report_md,
            height=700,
            label_visibility="collapsed",
        )
