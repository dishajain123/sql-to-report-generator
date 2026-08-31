from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
import re
import zipfile
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

from pipeline import LogicRulesExtractorPipeline, PipelineInputError
from src.ingestion.ingestion import build_object_identity_stem

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
    verification_path: str = ""
    report_filename: str = ""
    verification_filename: str = ""
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
    batch_start_time = datetime.now(timezone.utc).isoformat()
    used_stems: set[str] = set()
    results: list[BatchItemResult] = []

    for index, item in enumerate(inputs, start=1):
        display_name = str(item.display_name or Path(item.source_path).name or f"input_{index}")
        selected_dialect_mode = _normalize_dialect_mode(getattr(item, "dialect_mode", "auto"))

        def _on_progress(message: str) -> None:
            if progress_callback:
                progress_callback(f"[{index}/{len(inputs)}] [{display_name}] {message}")

        try:
            run_result = pipeline.run(
                item.source_path,
                dialect=selected_dialect_mode,
                progress_callback=_on_progress,
            )
            output_stem = _build_output_stem(run_result, display_name, used_stems)
            report_filename = f"{output_stem}_report.md"
            verification_filename = f"{output_stem}_verification.md"
            report_path = batch_dir / report_filename
            verification_path = batch_dir / verification_filename
            report_path.write_text(run_result.report, encoding="utf-8")
            verification_path.write_text(run_result.verification_report, encoding="utf-8")
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
                    verification_path=str(verification_path),
                    report_filename=report_filename,
                    verification_filename=verification_filename,
                    output_stem=output_stem,
                    run_result=run_result,
                )
            )
            if progress_callback:
                progress_callback(f"[{index}/{len(inputs)}] [{display_name}] Completed successfully")
        except (PipelineInputError, Exception) as exc:  # noqa: BLE001
            results.append(
                BatchItemResult(
                    input_file=item.source_path,
                    display_name=display_name,
                    status="failed",
                    selected_dialect_mode=selected_dialect_mode,
                    error=str(exc),
                )
            )
            if progress_callback:
                progress_callback(f"[{index}/{len(inputs)}] [{display_name}] Failed: {exc}")
            continue

    batch_end_time = datetime.now(timezone.utc).isoformat()
    manifest = _build_manifest(
        batch_id=resolved_batch_id,
        batch_start_time=batch_start_time,
        batch_end_time=batch_end_time,
        output_dir=batch_dir,
        inputs=inputs,
        items=results,
    )
    manifest_path = batch_dir / "batch_manifest.json"
    try:
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write batch manifest for %s: %s", resolved_batch_id, exc)
    else:
        manifest["manifest_filename"] = manifest_path.name

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
    }


def build_batch_archive_bytes(batch_result: BatchRunResult) -> bytes:
    """Package successful batch outputs into a ZIP archive for download."""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_path = Path(batch_result.manifest_path) if batch_result.manifest_path else None
        if manifest_path and manifest_path.exists():
            archive.write(manifest_path, arcname=manifest_path.name)
        for item in batch_result.successful_items:
            report_path = Path(item.report_path)
            verification_path = Path(item.verification_path)
            if report_path.exists():
                archive.write(report_path, arcname=report_path.name)
            if verification_path.exists():
                archive.write(verification_path, arcname=verification_path.name)
    return buffer.getvalue()
