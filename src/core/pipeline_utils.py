from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Optional


PIPELINE_VERSION = "2026-08-26-phase1"


@dataclass(frozen=True)
class RunMetadata:
    pipeline_version: str
    prompt_version: str
    knowledge_base_version: str
    model_name: str
    provider: str
    dialect: str
    dialect_confidence: str
    source_hash: str
    configuration_version: str
    run_timestamp: str
    object_id: str = ""


def stable_hash_text(text: str, length: int = 16) -> str:
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    return digest[:length]


def stable_id(prefix: str, *parts: Any, length: int = 12) -> str:
    payload = "|".join(str(part) for part in parts if part not in (None, ""))
    digest = hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()[:length]
    return f"{prefix}_{digest}"


def source_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def _hash_file(path: Path) -> str:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return "missing"
    return hashlib.sha256(data).hexdigest()


def prompt_version(project_root: Path) -> str:
    prompt_dir = project_root / "prompts"
    files = [prompt_dir / "logic_extraction.yaml", prompt_dir / "rule_synthesis.yaml"]
    payload = "|".join(f"{file.name}:{_hash_file(file)}" for file in files)
    return stable_hash_text(payload)


def knowledge_base_version(project_root: Path) -> str:
    kb_dir = project_root / "knowledge_base"
    if not kb_dir.exists():
        return "missing"
    parts = []
    for path in sorted(p for p in kb_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(project_root).as_posix()
        parts.append(f"{rel}:{_hash_file(path)}")
    return stable_hash_text("|".join(parts)) if parts else "empty"


def configuration_version(*parts: Any) -> str:
    payload = "|".join(str(part) for part in parts if part not in (None, ""))
    return stable_hash_text(payload)


def build_run_metadata(
    *,
    project_root: Path,
    model_name: str,
    provider: str,
    dialect: str,
    dialect_confidence: str,
    raw_source: str,
    object_id: str = "",
) -> RunMetadata:
    prompt_ver = prompt_version(project_root)
    kb_ver = knowledge_base_version(project_root)
    src_hash = source_hash(raw_source)
    config_ver = configuration_version(
        PIPELINE_VERSION,
        prompt_ver,
        kb_ver,
        model_name,
        provider,
        dialect,
        dialect_confidence,
    )
    return RunMetadata(
        pipeline_version=PIPELINE_VERSION,
        prompt_version=prompt_ver,
        knowledge_base_version=kb_ver,
        model_name=model_name,
        provider=provider,
        dialect=dialect,
        dialect_confidence=dialect_confidence,
        source_hash=src_hash,
        configuration_version=config_ver,
        run_timestamp=datetime.now(timezone.utc).isoformat(),
        object_id=object_id,
    )


def run_metadata_to_dict(metadata: RunMetadata | None) -> dict[str, Any]:
    return asdict(metadata) if metadata else {}

