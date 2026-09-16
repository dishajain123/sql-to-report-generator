from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
import re
import zipfile
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

from pipeline import LogicRulesExtractorPipeline, PipelineInputError
from src.ingestion.ingestion import build_object_identity_stem
from src.output.report_formatter import ReportFormatterAgent, normalize_call_target

logger = logging.getLogger("logic_rules_extractor.batch")


@dataclass(frozen=True)
class BatchInput:
    """One source file to process as part of a batch run."""

    source_path: str
    display_name: str
    dialect_mode: str = "auto"


@dataclass
class BatchItemResult:
    """Result for one file inside a batch run."""

    input_file: str
    display_name: str
    status: str
    selected_dialect_mode: str = "auto"
    detected_dialect: str = ""
    object_identity: str = ""
    report_path: str = ""
    report_filename: str = ""
    verification_path: str = ""
    verification_filename: str = ""
    log_path: str = ""
    log_filename: str = ""
    error: str = ""
    output_stem: str = ""
    run_result: object | None = None


@dataclass
class BatchRunResult:
    """Aggregate result for a whole batch invocation."""

    batch_id: str
    output_dir: Path
    batch_start_time: str = ""
    batch_end_time: str = ""
    manifest_path: str = ""
    manifest: dict[str, object] = field(default_factory=dict)
    items: list[BatchItemResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for item in self.items if item.status == "success")

    @property
    def failure_count(self) -> int:
        return sum(1 for item in self.items if item.status != "success")

    @property
    def successful_items(self) -> list[BatchItemResult]:
        return [item for item in self.items if item.status == "success"]


def make_batch_id(prefix: str = "batch") -> str:
    """Create a compact, human-readable batch identifier."""

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    suffix = f"{now.microsecond:06d}"[:6]
    return f"{prefix}_{timestamp}_{suffix}"


def _sanitize_stem(text: str) -> str:
    stem = re.sub(r"[\\/]+", "_", str(text or "").strip())
    stem = re.sub(r"\s+", "_", stem)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
    stem = stem.strip("._-")
    return stem or "report"


def _unique_stem(base_stem: str, used: set[str]) -> str:
    candidate = base_stem
    counter = 2
    while candidate in used:
        candidate = f"{base_stem}__{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def _display_stem(display_name: str) -> str:
    return _sanitize_stem(Path(display_name).stem or display_name)


def _normalize_dialect_mode(value: str | None) -> str:
    mode = str(value or "auto").strip().lower()
    if mode in {"auto", "oracle", "tsql"}:
        return mode
    return "auto"


def _build_output_stem(run_result, display_name: str, used: set[str]) -> str:
    fallback_stem = _display_stem(display_name)
    if run_result and getattr(run_result, "ingestion", None) is not None:
        base = build_object_identity_stem(run_result.ingestion, fallback_stem=fallback_stem)
    else:
        base = fallback_stem
    return _unique_stem(_sanitize_stem(base), used)


@contextmanager
def _capture_item_log(log_path: Path):
    """Capture one batch item's pipeline diagnostics in its own artifact."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root_logger.addHandler(handler)
    previous_level = root_logger.level
    if previous_level > logging.INFO or previous_level == logging.NOTSET:
        root_logger.setLevel(logging.INFO)
    try:
        yield
    finally:
        root_logger.removeHandler(handler)
        handler.close()
        root_logger.setLevel(previous_level)


def run_batch(
    pipeline: LogicRulesExtractorPipeline,
    inputs: Sequence[BatchInput],
    *,
    output_dir: Path,
    batch_id: str | None = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> BatchRunResult:
    """Run the existing single-file pipeline once per input file."""

    resolved_batch_id = batch_id or make_batch_id()
    output_dir = Path(output_dir)
    batch_dir = output_dir / resolved_batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = batch_dir / "logs"
    batch_start_time = datetime.now(timezone.utc).isoformat()
    used_stems: set[str] = set()
    results: list[BatchItemResult] = []

    for index, item in enumerate(inputs, start=1):
        display_name = str(item.display_name or Path(item.source_path).name or f"input_{index}")
        selected_dialect_mode = _normalize_dialect_mode(getattr(item, "dialect_mode", "auto"))
        provisional_log_path = logs_dir / f"_{index}_{_display_stem(display_name)}_pipeline.log"

        def _on_progress(message: str) -> None:
            if progress_callback:
                progress_callback(f"[{index}/{len(inputs)}] [{display_name}] {message}")

        try:
            with _capture_item_log(provisional_log_path):
                logging.getLogger(__name__).info("Batch item started: %s", display_name)
                run_result = pipeline.run(
                    item.source_path,
                    dialect=selected_dialect_mode,
                    progress_callback=_on_progress,
                )
            output_stem = _build_output_stem(run_result, display_name, used_stems)
            report_filename = f"{output_stem}_report.md"
            report_path = batch_dir / report_filename
            report_path.write_text(run_result.report, encoding="utf-8")
            verification_dir = batch_dir / "verification"
            verification_dir.mkdir(parents=True, exist_ok=True)
            verification_filename = f"{output_stem}_verification.md"
            verification_path = verification_dir / verification_filename
            verification_path.write_text(run_result.verification_report, encoding="utf-8")
            log_filename = f"{output_stem}_pipeline.log"
            log_path = logs_dir / log_filename
            provisional_log_path.replace(log_path)
            detected_dialect = str(getattr(getattr(run_result, "ingestion", None), "dialect", "") or "")
            object_identity = ""
            if getattr(run_result, "ingestion", None) is not None:
                object_identity = build_object_identity_stem(run_result.ingestion, fallback_stem=display_name)
            results.append(
                BatchItemResult(
                    input_file=item.source_path,
                    display_name=display_name,
                    status="success",
                    selected_dialect_mode=selected_dialect_mode,
                    detected_dialect=detected_dialect,
                    object_identity=object_identity,
                    report_path=str(report_path),
                    report_filename=report_filename,
                    verification_path=str(verification_path),
                    verification_filename=verification_filename,
                    log_path=str(log_path),
                    log_filename=log_filename,
                    output_stem=output_stem,
                    run_result=run_result,
                )
            )
            if progress_callback:
                progress_callback(f"[{index}/{len(inputs)}] [{display_name}] Completed successfully")
        except (PipelineInputError, Exception) as exc:  # noqa: BLE001
            if provisional_log_path.exists():
                log_path = logs_dir / f"{_display_stem(display_name)}_pipeline.log"
                provisional_log_path.replace(log_path)
            else:
                log_path = None
            results.append(
                BatchItemResult(
                    input_file=item.source_path,
                    display_name=display_name,
                    status="failed",
                    selected_dialect_mode=selected_dialect_mode,
                    log_path=str(log_path) if log_path else "",
                    log_filename=log_path.name if log_path else "",
                    error=str(exc),
                )
            )
            if progress_callback:
                progress_callback(f"[{index}/{len(inputs)}] [{display_name}] Failed: {exc}")
            continue

    # Second pass, now that every file in the batch has been processed:
    # resolve each item's called_procedures (already captured per-file by
    # ingestion - see IngestionResult.called_procedures) against the other
    # objects in this same batch. This can only happen as a post-process
    # step, not threaded through pipeline.run() itself, because which
    # other object identities exist in the batch isn't known until every
    # file in it has finished. No child business rules are invented or
    # copied here - this only cross-links to the sibling's own report.
    call_graph = _cross_reference_batch(results)

    batch_end_time = datetime.now(timezone.utc).isoformat()
    manifest = _build_manifest(
        batch_id=resolved_batch_id,
        batch_start_time=batch_start_time,
        batch_end_time=batch_end_time,
        output_dir=batch_dir,
        inputs=inputs,
        items=results,
        call_graph=call_graph,
    )
    manifest_path = batch_dir / "batch_manifest.json"
    try:
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write batch manifest for %s: %s", resolved_batch_id, exc)
    else:
        manifest["manifest_filename"] = manifest_path.name

    index_path = batch_dir / "_batch_index.md"
    try:
        index_path.write_text(_build_batch_index_markdown(results, call_graph), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write batch index for %s: %s", resolved_batch_id, exc)

    return BatchRunResult(
        batch_id=resolved_batch_id,
        output_dir=batch_dir,
        batch_start_time=batch_start_time,
        batch_end_time=batch_end_time,
        manifest_path=str(manifest_path),
        manifest=manifest,
        items=results,
    )


def _build_manifest(
    *,
    batch_id: str,
    batch_start_time: str,
    batch_end_time: str,
    output_dir: Path,
    inputs: Sequence[BatchInput],
    items: Sequence[BatchItemResult],
    call_graph: Sequence[dict[str, object]] = (),
) -> dict[str, object]:
    file_entries: list[dict[str, object]] = []
    for source_input, item in zip(inputs, items):
        file_entries.append(
            {
                "filename": item.display_name,
                "status": item.status,
                "selected_dialect_mode": item.selected_dialect_mode,
                "detected_dialect": item.detected_dialect,
                "object_identity": item.object_identity,
                "effective_dialect": item.detected_dialect,
                "report_filename": item.report_filename,
                "verification_filename": item.verification_filename,
                "log_filename": item.log_filename,
                "error_message": item.error,
            }
        )

    success_count = sum(1 for item in items if item.status == "success")
    failure_count = sum(1 for item in items if item.status != "success")
    return {
        "batch_id": batch_id,
        "batch_start_time": batch_start_time,
        "batch_end_time": batch_end_time,
        "batch_output_dir": str(output_dir),
        "total_files": len(inputs),
        "successful_files": success_count,
        "failed_files": failure_count,
        "files": file_entries,
        "call_graph": list(call_graph),
    }


def _identity_keys_for_item(item: BatchItemResult) -> tuple[str, str]:
    """Returns (bare_key, full_key) normalized lookup keys for one
    successfully-run batch item's own object identity - `full_key` is
    empty when no schema is known. Both keys resolve through
    `normalize_call_target` so bracket/case noise never causes a false
    non-match (see that function's docstring)."""
    ingestion = getattr(item.run_result, "ingestion", None)
    if ingestion is None:
        return "", ""
    name = str(getattr(ingestion, "canonical_object_name", "") or "").strip()
    if not name or name.upper() in {"UNKNOWN_OBJECT", "UNKNOWN", "ANONYMOUS_BLOCK"}:
        name = str(getattr(ingestion, "object_name", "") or "").strip()
    if not name:
        return "", ""
    schema = str(getattr(ingestion, "schema", "") or "").strip()
    bare_key = normalize_call_target(name)
    full_key = normalize_call_target(f"{schema}.{name}") if schema else ""
    return bare_key, full_key


def _cross_reference_batch(results: Sequence[BatchItemResult]) -> list[dict[str, object]]:
    """Resolve every successful item's called_procedures against the
    other objects known in this batch, rewriting each item's own
    already-written report with a "Report" cross-reference column where a
    call resolves - and return the underlying call-graph edges (purely
    derived from called_procedures + identity matching; no child business
    logic is invented or copied) for the manifest/index.

    A schema-qualified match (`full_key`) is always trusted. A bare
    unqualified name match is only trusted when it is unique across the
    whole batch - an unqualified call name that happens to match two
    different schemas' same-named object is genuinely ambiguous, and
    silently picking one would be exactly the kind of guess this
    pipeline's design otherwise refuses to make (see guardrails.py).
    """
    successful = [item for item in results if item.status == "success" and item.run_result is not None]

    full_key_map: dict[str, BatchItemResult] = {}
    bare_key_counts: dict[str, int] = {}
    bare_key_map: dict[str, BatchItemResult] = {}
    for item in successful:
        bare_key, full_key = _identity_keys_for_item(item)
        if not bare_key:
            continue
        bare_key_counts[bare_key] = bare_key_counts.get(bare_key, 0) + 1
        bare_key_map[bare_key] = item
        if full_key:
            full_key_map[full_key] = item

    def _resolve(call_name: str) -> Optional[BatchItemResult]:
        key = normalize_call_target(call_name)
        if key in full_key_map:
            return full_key_map[key]
        if key in bare_key_map and bare_key_counts.get(key) == 1:
            return bare_key_map[key]
        return None

    edges: list[dict[str, object]] = []
    for item in successful:
        ingestion = getattr(item.run_result, "ingestion", None)
        calls = getattr(ingestion, "called_procedures", None) or []
        resolved: dict[str, str] = {}
        for call in calls:
            call_name = str(call.get("name") or "").strip()
            if not call_name:
                continue
            target_item = _resolve(call_name)
            is_resolved = target_item is not None and target_item is not item
            edges.append(
                {
                    "caller": item.object_identity or item.display_name,
                    "caller_report": item.report_filename,
                    "callee": call_name,
                    "resolved": is_resolved,
                    "callee_report": target_item.report_filename if is_resolved else "",
                }
            )
            if is_resolved:
                resolved[normalize_call_target(call_name)] = target_item.report_filename
        if not resolved or not ingestion:
            continue
        old_section = ReportFormatterAgent.render_called_procedures_section(ingestion)
        if not old_section or old_section not in (item.run_result.report or ""):
            continue
        new_section = ReportFormatterAgent.render_called_procedures_section(ingestion, resolved)
        updated_report = item.run_result.report.replace(old_section, new_section, 1)
        item.run_result.report = updated_report
        try:
            Path(item.report_path).write_text(updated_report, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to rewrite cross-referenced report for %s: %s", item.display_name, exc)

    return edges


def _build_batch_index_markdown(
    results: Sequence[BatchItemResult], call_graph: Sequence[dict[str, object]]
) -> str:
    """A generated, generic starting point for reviewing a batch: objects
    that nothing else in this batch calls (in-degree 0 - typically
    orchestrators) are listed first, since a reviewer benefits most from
    starting there, then everything else. Purely derived from in-degree
    computed over `call_graph`'s resolved edges - no hardcoded ordering,
    no procedure-name-specific logic.
    """
    successful = [item for item in results if item.status == "success"]
    callee_reports = {
        str(edge.get("callee_report")) for edge in call_graph if edge.get("resolved") and edge.get("callee_report")
    }
    roots = [item for item in successful if item.report_filename not in callee_reports]
    leaves = [item for item in successful if item.report_filename in callee_reports]

    lines = ["# Batch Index", ""]
    if roots:
        lines.append("## Not called by anything else in this batch (start here)")
        lines.append("")
        for item in roots:
            lines.append(f"- [{item.display_name}]({item.report_filename})")
        lines.append("")
    if leaves:
        lines.append("## Called by at least one other object in this batch")
        lines.append("")
        for item in leaves:
            lines.append(f"- [{item.display_name}]({item.report_filename})")
        lines.append("")
    failed = [item for item in results if item.status != "success"]
    if failed:
        lines.append("## Failed")
        lines.append("")
        for item in failed:
            lines.append(f"- {item.display_name}: {item.error}")
        lines.append("")
    return "\n".join(lines)


def build_batch_archive_bytes(batch_result: BatchRunResult) -> bytes:
    """Package successful batch outputs into a ZIP archive for download."""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_path = Path(batch_result.manifest_path) if batch_result.manifest_path else None
        if manifest_path and manifest_path.exists():
            archive.write(manifest_path, arcname=manifest_path.name)
        for item in batch_result.successful_items:
            report_path = Path(item.report_path)
            if report_path.exists():
                archive.write(report_path, arcname=report_path.name)
            verification_path = Path(getattr(item, "verification_path", ""))
            if verification_path.exists():
                archive.write(verification_path, arcname=f"verification/{verification_path.name}")
            log_value = str(getattr(item, "log_path", "") or "").strip()
            log_path = Path(log_value) if log_value else None
            if log_path and log_path.exists():
                archive.write(log_path, arcname=f"logs/{log_path.name}")
    return buffer.getvalue()
