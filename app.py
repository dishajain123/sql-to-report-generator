"""
app.py
-------
Streamlit frontend for the AI-Powered DB Logic & Business Rules Extractor.

Lets a user upload (or paste) a banking .sql object, pick/switch the
Groq model from a sidebar control, run the five-agent pipeline with a
live per-stage progress view, and download the resulting Markdown
report.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from pipeline import LogicRulesExtractorPipeline, DEFAULT_MODEL

load_dotenv()

SAMPLES_DIR = Path("samples")
MODEL_OPTIONS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "Other (enter model name)",
]

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
    '<span class="lre-badge">Groq LLM</span>'
    '<span class="lre-badge">ChromaDB RAG</span>',
    unsafe_allow_html=True,
)
st.divider()

# --------------------------------------------------------------------------
# Sidebar — configuration
# --------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Configuration")

    env_api_key = os.environ.get("GROQ_API_KEY", "")
    override_key = st.text_input(
        "Groq API Key (optional override)",
        value="",
        type="password",
        placeholder="Leave blank to use GROQ_API_KEY from .env",
        help="By default this app uses GROQ_API_KEY from your .env file. "
        "Enter a key here only if you want to override it for this session.",
    )
    api_key = override_key.strip() or env_api_key

    if override_key.strip():
        st.caption("🔑 Using the API key entered above (overrides `.env`).")
    elif env_api_key:
        st.caption("🔑 Using `GROQ_API_KEY` from `.env`.")
    else:
        st.caption("⚠️ No API key found. Set `GROQ_API_KEY` in `.env`, or enter one above.")

    st.subheader("Model")
    model_choice = st.selectbox(
        "Groq model",
        MODEL_OPTIONS,
        index=0,
        help="Switch models per run — no need to rebuild anything else.",
    )
    if model_choice == "Other (enter model name)":
        model_name = st.text_input("Custom Groq model name", value="")
    else:
        model_name = model_choice

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
        "Free-tier Groq key: [console.groq.com](https://console.groq.com/) · "
        "This app never sends your key anywhere except the Groq API."
    )


# --------------------------------------------------------------------------
# Pipeline construction (cached — persists the Chroma store / embedding
# model / Groq client across reruns and across model switches)
# --------------------------------------------------------------------------


@st.cache_resource(show_spinner="Loading knowledge base and embedding model…")
def get_pipeline(
    _api_key: str, persist_dir: str, kb_dir: str
) -> LogicRulesExtractorPipeline:
    return LogicRulesExtractorPipeline(
        model_name=DEFAULT_MODEL,
        groq_api_key=_api_key,
        persist_directory=persist_dir,
        knowledge_base_dir=kb_dir,
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
    if not api_key:
        st.error("Enter your Groq API key in the sidebar first.")
        st.stop()
    if not model_name:
        st.error("Choose or enter a Groq model in the sidebar first.")
        st.stop()

    try:
        pipeline = get_pipeline(api_key, persist_directory, knowledge_base_dir)
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sql", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(sql_code)
            tmp_path = tmp.name

        with st.status("Running the 5-agent pipeline…", expanded=True) as status:

            def on_progress(message: str) -> None:
                status.write(message)

            report = pipeline.run(
                tmp_path, model_name=model_name, progress_callback=on_progress
            )
            status.update(label="Extraction complete ✅", state="complete")

        st.session_state["last_report"] = report
        st.session_state["last_stem"] = Path(sql_filename).stem
        st.session_state["last_model"] = model_name

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

    if ambiguity_count:
        st.warning(
            f"{ambiguity_count} item(s) flagged for human review — see the "
            "**Ambiguities / Needs Review** section below."
        )

    tab_rendered, tab_raw = st.tabs(["📖 Rendered", "🔤 Raw Markdown"])
    with tab_rendered:
        st.markdown(report_md)
    with tab_raw:
        st.code(report_md, language="markdown")
