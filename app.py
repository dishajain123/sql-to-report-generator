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

from src.batch.batch_runner import BatchInput, build_batch_archive_bytes, run_batch
from src.ingestion.ingestion import decode_sql_source_bytes, build_object_identity_stem
from src.core.llm_client import LLMConfig, load_llm_config
from pipeline import LogicRulesExtractorPipeline, PipelineInputError

load_dotenv(override=True)

APP_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = APP_DIR / "samples"
OUTPUT_DIR = SAMPLES_DIR / "output"
LOGS_DIR = OUTPUT_DIR / "logs"
VERIFICATION_DIR = OUTPUT_DIR / "verification"
PIPELINE_CACHE_VERSION = "2026-08-26-phase1"
DIALECT_OPTIONS = {
    "Auto-detect": "auto",
    "Oracle SQL / PL-SQL": "oracle",
    "SQL Server T-SQL": "tsql",
}
BATCH_DIALECT_OPTIONS = {
    "Auto Detect": "auto",
    "Oracle": "oracle",
    "T-SQL": "tsql",
}


def _request_kb_rebuild() -> None:
    """Keep the sidebar rebuild request until the next pipeline run."""
    st.session_state["rebuild_kb_requested"] = True


def _batch_dialect_key(index: int, filename: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", Path(filename).stem or filename).strip("_")
    return f"batch_dialect_mode_{index}_{safe_name or 'file'}"

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
    source_files = [APP_DIR / "app.py", APP_DIR / "main.py", APP_DIR / "pipeline.py"]
    source_files.extend(sorted(APP_DIR.joinpath("src").rglob("*.py")))
    source_files.extend(sorted(APP_DIR.joinpath("src").rglob("*.yaml")))
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
        st.button(
            "🔄 Rebuild knowledge base from disk",
            on_click=_request_kb_rebuild,
            help="Rebuild on the next extraction run using the selected knowledge-base directory.",
        )

    st.divider()
    st.caption(
        "This app reads the provider, API key, model, and base URL from `.env`."
    )

rebuild_kb = bool(st.session_state.get("rebuild_kb_requested", False))


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


def _run_paths(stem: str) -> tuple[int, Path, Path, Path]:
    """Build the run-numbered report, verification, and log paths.
    `stem` is
    expected to be the object's *parsed identity* stem (see
    `build_object_identity_stem`), not the raw upload filename - that is
    what keeps the numbering and naming stable across differently-named
    uploads of the same underlying SQL object.
    """
    run_number = _next_run_number(stem)
    report_path = OUTPUT_DIR / f"{run_number}_{stem}_report.md"
    verification_path = VERIFICATION_DIR / f"{run_number}_{stem}_verification.md"
    log_path = LOGS_DIR / f"{run_number}_{stem}_pipeline.log"
    return run_number, report_path, verification_path, log_path


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


def _render_batch_run_status(batch_state: dict, log_path: Path | None = None) -> str:
    current_file = batch_state.get("current_file") or "Waiting to start."
    current_message = batch_state.get("latest_message") or "Starting..."
    completed = batch_state.get("completed_files", 0)
    total = batch_state.get("total_files", 0)
    recent = batch_state.get("messages", [])[-4:]
    recent_block = "\n".join(f"- {msg}" for msg in recent) if recent else "- Waiting to start."
    log_line = f"- **Log file:** `{log_path}`\n" if log_path else ""
    return (
        "### Batch Run Status\n\n"
        f"- **Current file:** {current_file}\n"
        f"- **Current step:** {current_message}\n"
        f"- **Batch progress:** {completed}/{total}\n"
        f"{log_line}"
        "**Recent updates**\n"
        f"{recent_block}"
    )


def _count_report_findings(report: str) -> int:
    """Count visible review bullets across current and legacy headings."""
    sections = re.split(r"^##\s+", str(report or ""), flags=re.MULTILINE)
    for section in sections:
        if not re.match(r"(?:Findings\s*/\s*Needs Review|Ambiguities\s*/\s*Needs Review)\b", section, re.IGNORECASE):
            continue
        body = section.split("\n", 1)[1] if "\n" in section else ""
        if body.strip().lower().startswith("none"):
            return 0
        return sum(1 for line in body.splitlines() if line.strip().startswith("- "))
    return 0


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
uploaded_files: list = []
batch_mode = False

if source == "Upload a .sql file":
    uploaded_files = st.file_uploader(
        "Upload a .sql file",
        type=["sql", "prc", "pks", "pkb", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    batch_mode = len(uploaded_files) > 1
    if batch_mode:
        st.info(
            f"{len(uploaded_files)} files selected. Batch mode will auto-detect the dialect for each file independently."
        )
        st.caption("Choose a per-file dialect override only if you need to override auto-detection.")
        for index, uploaded in enumerate(uploaded_files, start=1):
            st.selectbox(
                f"Dialect for {uploaded.name}",
                list(BATCH_DIALECT_OPTIONS.keys()),
                index=0,
                key=_batch_dialect_key(index, uploaded.name),
                help="Applies only to this file in the batch. Auto Detect preserves the existing behavior.",
            )
    elif uploaded_files:
        uploaded = uploaded_files[0]
        # Use the same BOM/heuristic-aware decoder as the CLI path
        # (agents.ingestion.decode_sql_source_bytes) instead of a bare
        # UTF-8 decode, which silently corrupts UTF-16 SSMS/Toad exports
        # (a very common source of "truncated"/garbled SQL in the UI).
        sql_code = decode_sql_source_bytes(uploaded.getvalue())
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
        sql_code = decode_sql_source_bytes((SAMPLES_DIR / chosen).read_bytes())
        sql_filename = chosen
        with st.expander("Preview sample code", expanded=False):
            st.code(sql_code, language="sql")
    else:
        st.warning(f"No sample .sql files found in `{SAMPLES_DIR}/`.")

st.subheader("2. Run the pipeline")

run_label = "🚀 Run Batch Extraction" if batch_mode else "🚀 Run Extraction"
run_clicked = st.button(
    run_label,
    type="primary",
    disabled=not batch_mode and not sql_code,
    use_container_width=False,
)

# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------

if run_clicked and batch_mode:
    for key in (
        "last_report",
        "last_stem",
        "last_model",
        "last_saved_path",
        "last_verification_path",
        "last_verification",
        "last_log_path",
        "last_run_number",
        "last_run_messages",
    ):
        st.session_state.pop(key, None)
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
        st.session_state.pop("rebuild_kb_requested", None)

    pipeline.retrieval_k = retrieval_k
    pipeline.extraction_agent.temperature = temperature
    pipeline.synthesizer_agent.temperature = temperature

    temp_dir = tempfile.TemporaryDirectory()
    tmp_paths: list[Path] = []
    run_state = {
        "messages": [],
        "current_file": "Starting...",
        "latest_message": "Starting...",
        "completed_files": 0,
        "total_files": len(uploaded_files),
    }
    status_panel = st.container(border=True)
    status_placeholder = status_panel.empty()
    progress_bar = status_panel.progress(0)

    def _refresh_status() -> None:
        total = max(run_state["total_files"], 1)
        progress_bar.progress(min(int((run_state["completed_files"] / total) * 100), 100))
        status_placeholder.markdown(_render_batch_run_status(run_state))

    def _on_batch_progress(message: str) -> None:
        run_state["messages"].append(message)
        batch_match = re.match(r"^\[(\d+)/(\d+)\]\s+\[(.*?)\]\s+(.*)$", message)
        if batch_match:
            run_state["current_file"] = f"{batch_match.group(1)}/{batch_match.group(2)} · {batch_match.group(3)}"
            inner_message = batch_match.group(4).strip()
            if inner_message.startswith("Completed"):
                run_state["completed_files"] = min(
                    run_state["total_files"], run_state["completed_files"] + 1
                )
            elif inner_message.startswith("Failed"):
                run_state["completed_files"] = min(
                    run_state["total_files"], run_state["completed_files"] + 1
                )
            stage_match = re.match(r"^Stage\s+(\d+)/(\d+):\s*(.*)$", inner_message)
            run_state["latest_message"] = stage_match.group(3).strip() if stage_match else inner_message
        else:
            run_state["latest_message"] = message
        _refresh_status()

    try:
        for uploaded in uploaded_files:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=Path(uploaded.name).suffix or ".sql", delete=False) as tmp:
                tmp.write(uploaded.getvalue())
                tmp_paths.append(Path(tmp.name))

        batch_inputs = [
            BatchInput(
                source_path=str(tmp_path),
                display_name=uploaded.name,
                dialect_mode=BATCH_DIALECT_OPTIONS[
                    st.session_state.get(_batch_dialect_key(index, uploaded.name), "Auto Detect")
                ],
            )
            for index, (tmp_path, uploaded) in enumerate(zip(tmp_paths, uploaded_files), start=1)
        ]

        with st.status("Running the batch pipeline…", expanded=False) as status:
            batch_result = run_batch(
                pipeline,
                batch_inputs,
                output_dir=Path("samples/output/batches"),
                progress_callback=_on_batch_progress,
            )
            run_state["completed_files"] = batch_result.success_count + batch_result.failure_count
            run_state["latest_message"] = "Batch extraction complete"
            _refresh_status()
            status.update(label="Batch extraction complete ✅", state="complete")

        archive_bytes = build_batch_archive_bytes(batch_result)
        archive_path = batch_result.output_dir / f"{batch_result.batch_id}.zip"
        archive_path.write_bytes(archive_bytes)

        st.session_state["last_batch_result"] = batch_result
        st.session_state["last_batch_archive"] = archive_bytes
        st.session_state["last_batch_archive_path"] = str(archive_path)
        st.session_state["last_batch_messages"] = run_state["messages"]

    except PipelineInputError as exc:
        st.error(f"Batch input rejected by guardrails: {exc}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Batch pipeline error: {exc}")
        st.exception(exc)
    finally:
        for tmp_path in tmp_paths:
            tmp_path.unlink(missing_ok=True)
        temp_dir.cleanup()

elif run_clicked:
    for key in (
        "last_batch_result",
        "last_batch_archive",
        "last_batch_archive_path",
        "last_batch_messages",
    ):
        st.session_state.pop(key, None)
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
        st.session_state.pop("rebuild_kb_requested", None)

    # apply the sidebar's live settings to the cached pipeline instance
    pipeline.retrieval_k = retrieval_k
    pipeline.extraction_agent.temperature = temperature
    pipeline.synthesizer_agent.temperature = temperature

    tmp_path = None
    tmp_log_path = None
    try:
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
                    tmp_log_path,
                )
            )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sql", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(sql_code)
            tmp_path = tmp.name

        # The run log is captured to a temporary file while the object's
        # identity (schema/name/type) is still unknown - it can only be
        # named from the parsed SQL, not the upload - then renamed to its
        # final `<run_number>_<Schema>.<Name>.<Type>_pipeline.log` path
        # alongside the report once the pipeline has run.
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=LOGS_DIR, prefix="_run_", suffix=".log.tmp", delete=False, encoding="utf-8"
        ) as tmp_log:
            tmp_log_path = Path(tmp_log.name)

        _refresh_status()

        with st.status("Running the pipeline…", expanded=False) as status:
            with _capture_run_logs(tmp_log_path):
                logging.getLogger(__name__).info("Run started for %s", sql_filename)

                def on_progress(message: str) -> None:
                    run_state["messages"].append(message)
                    stage_match = re.match(r"^Stage\s+(\d+)/(\d+):\s*(.*)$", message)
                    if stage_match:
                        run_state["current_stage"] = int(stage_match.group(1))
                        run_state["latest_message"] = stage_match.group(3).strip()
                    else:
                        run_state["latest_message"] = message
                    _refresh_status()

                run_result = pipeline.run(tmp_path, dialect=dialect_choice, progress_callback=on_progress)
                run_state["current_stage"] = 6
                run_state["latest_message"] = "Extraction complete"
                run_state["messages"].append("Pipeline completed successfully.")
                _refresh_status()
                status.update(label="Extraction complete ✅", state="complete")

        # Filenames are derived from the object's own parsed identity
        # (schema + canonical business name + object type), never from
        # the uploaded file's name - see build_object_identity_stem.
        report_stem = build_object_identity_stem(run_result.ingestion, fallback_stem=Path(sql_filename).stem)
        run_number, report_path, verification_path, log_path = _run_paths(report_stem)

        report_path.write_text(run_result.report, encoding="utf-8")
        verification_path.parent.mkdir(parents=True, exist_ok=True)
        verification_path.write_text(run_result.verification_report, encoding="utf-8")
        tmp_log_path.replace(log_path)
        tmp_log_path = None
        logging.getLogger(__name__).info("Saved report to %s", report_path)
        logging.getLogger(__name__).info("Saved run log to %s", log_path)

        st.session_state["last_report"] = run_result.report
        st.session_state["last_stem"] = report_stem
        st.session_state["last_model"] = pipeline.model_name
        st.session_state["last_saved_path"] = str(report_path)
        st.session_state["last_verification_path"] = str(verification_path)
        st.session_state["last_verification"] = run_result.verification_report
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
        if tmp_log_path:
            Path(tmp_log_path).unlink(missing_ok=True)

# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------

if "last_batch_result" in st.session_state:
    st.divider()
    st.subheader("3. Batch results")

    batch_result = st.session_state["last_batch_result"]
    manifest = batch_result.manifest or {}
    success_count = batch_result.success_count
    failure_count = batch_result.failure_count
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        st.metric("Batch ID", batch_result.batch_id)
    with col2:
        st.metric("Succeeded", success_count)
    with col3:
        st.metric("Failed", failure_count)

    summary_cols = st.columns([2, 2, 2, 2])
    with summary_cols[0]:
        st.metric("Total files", manifest.get("total_files", len(batch_result.items)))
    with summary_cols[1]:
        st.metric("Successful files", manifest.get("successful_files", success_count))
    with summary_cols[2]:
        st.metric("Failed files", manifest.get("failed_files", failure_count))
    with summary_cols[3]:
        st.metric("Manifest", Path(batch_result.manifest_path).name if batch_result.manifest_path else "—")

    if manifest:
        st.caption(
            f"Batch window: `{manifest.get('batch_start_time', '—')}` → `{manifest.get('batch_end_time', '—')}`"
        )
        st.caption(f"Batch output directory: `{manifest.get('batch_output_dir', batch_result.output_dir)}`")

    if st.session_state.get("last_batch_archive"):
        st.download_button(
            "⬇️ Download all reports as ZIP",
            data=st.session_state["last_batch_archive"],
            file_name=f"{batch_result.batch_id}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

    if st.session_state.get("last_batch_archive_path"):
        st.caption(f"Batch archive saved to: `{st.session_state['last_batch_archive_path']}`")

    if manifest:
        with st.expander("Batch manifest", expanded=False):
            st.json(manifest)

    for idx, item in enumerate(batch_result.items, start=1):
        title = f"{idx}. {item.display_name}"
        with st.expander(title, expanded=idx == 1):
            if item.status == "success" and item.run_result:
                st.success("Completed successfully")
                st.caption(
                    f"Dialect mode: {item.selected_dialect_mode} | Effective dialect: {item.detected_dialect or '—'}"
                )
                st.caption(f"Report: `{item.report_path}`")
                st.caption(f"Verification: `{item.verification_path}`")
                if item.log_path:
                    st.caption(f"Pipeline log: `{item.log_path}`")
                st.download_button(
                    f"⬇️ Download report ({idx})",
                    data=item.run_result.report,
                    file_name=Path(item.report_path).name,
                    mime="text/markdown",
                    key=f"batch-report-{idx}",
                )
                st.download_button(
                    f"⬇️ Download verification ({idx})",
                    data=item.run_result.verification_report,
                    file_name=Path(item.verification_path).name,
                    mime="text/markdown",
                    key=f"batch-verification-{idx}",
                )
                if item.log_path:
                    log_path = Path(item.log_path)
                    if log_path.exists():
                        st.download_button(
                            f"⬇️ Download log ({idx})",
                            data=log_path.read_bytes(),
                            file_name=log_path.name,
                            mime="text/plain",
                            key=f"batch-log-{idx}",
                        )
                tab_rendered, tab_raw = st.tabs([f"📖 {item.display_name}", "🔤 Raw Markdown"])
                with tab_rendered:
                    st.markdown(item.run_result.report)
                with tab_raw:
                    st.text_area(
                        "Raw Markdown",
                        value=item.run_result.report,
                        height=700,
                        label_visibility="collapsed",
                        key=f"batch-raw-{idx}",
                    )
            else:
                st.error(item.error or "Unknown failure")

if "last_report" in st.session_state:
    st.divider()
    st.subheader("3. Business logic report")

    report_md: str = st.session_state["last_report"]
    ambiguity_count = _count_report_findings(report_md)

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
    if "last_verification_path" in st.session_state:
        st.caption(f"Verification saved to: `{st.session_state['last_verification_path']}`")
        st.download_button(
            "⬇️ Download verification",
            data=st.session_state.get("last_verification", ""),
            file_name=Path(st.session_state["last_verification_path"]).name,
            mime="text/markdown",
            use_container_width=True,
        )
    if "last_log_path" in st.session_state:
        st.caption(f"Run log (including verification diagnostics) saved to: `{st.session_state['last_log_path']}`")

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
