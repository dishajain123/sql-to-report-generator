from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional


_CACHE_SCHEMA_VERSION = "v1"


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _json_default(value: Any) -> str:
    return str(value)


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )


def build_llm_response_cache_key(request: Mapping[str, Any]) -> str:
    payload = dict(request)
    payload.setdefault("cache_schema_version", _CACHE_SCHEMA_VERSION)
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8", errors="ignore")).hexdigest()
    return digest


@dataclass(frozen=True)
class CacheLookupResult:
    status: str
    response_text: str = ""
    error: str = ""
    cache_key: str = ""

    @property
    def hit(self) -> bool:
        return self.status == "hit"

    @property
    def miss(self) -> bool:
        return self.status == "miss"

    @property
    def disabled(self) -> bool:
        return self.status == "disabled"


class PersistentLLMResponseCache:
    """Simple persistent exact-response cache for LLM calls.

    The cache stores only successful raw response text and never raises
    to the caller if persistence is unavailable.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        enabled: Optional[bool] = None,
    ) -> None:
        self.enabled = _env_flag("LLM_RESPONSE_CACHE_ENABLED", default=True) if enabled is None else bool(enabled)
        self.path = self._resolve_path(path)
        self._lock = threading.Lock()
        self._schema_ready = False

    @staticmethod
    def _resolve_path(path: str | Path | None) -> Path:
        if path is not None:
            return Path(path)
        explicit_path = os.environ.get("LLM_RESPONSE_CACHE_PATH", "").strip()
        if explicit_path:
            return Path(explicit_path)
        explicit_dir = os.environ.get("LLM_RESPONSE_CACHE_DIR", "").strip()
        if explicit_dir:
            return Path(explicit_dir) / "llm_response_cache.sqlite3"
        return Path("runtime") / "llm_cache" / "llm_response_cache.sqlite3"

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=30) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_response_cache (
                    cache_key TEXT PRIMARY KEY,
                    stage TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    dialect TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_llm_response_cache_stage ON llm_response_cache(stage)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_llm_response_cache_provider ON llm_response_cache(provider, model_name)"
            )
        self._schema_ready = True

    def lookup(self, request: Mapping[str, Any]) -> CacheLookupResult:
        if not self.enabled:
            return CacheLookupResult(status="disabled")
        cache_key = build_llm_response_cache_key(request)
        try:
            with self._lock:
                self._ensure_schema()
                with sqlite3.connect(self.path, timeout=30) as conn:
                    row = conn.execute(
                        "SELECT response_text FROM llm_response_cache WHERE cache_key = ?",
                        (cache_key,),
                    ).fetchone()
            if not row:
                return CacheLookupResult(status="miss", cache_key=cache_key)
            return CacheLookupResult(status="hit", response_text=str(row[0] or ""), cache_key=cache_key)
        except Exception as exc:  # pragma: no cover - exercised in failure-safety tests
            return CacheLookupResult(status="error", error=str(exc), cache_key=cache_key)

    def store(self, request: Mapping[str, Any], response_text: str) -> bool:
        if not self.enabled:
            return False
        response_text = str(response_text or "")
        if not response_text:
            return False
        payload = dict(request)
        cache_key = build_llm_response_cache_key(payload)
        try:
            with self._lock:
                self._ensure_schema()
                with sqlite3.connect(self.path, timeout=30) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO llm_response_cache
                        (cache_key, stage, provider, model_name, dialect, request_json, response_text)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cache_key,
                            str(payload.get("stage", "") or ""),
                            str(payload.get("provider", "") or ""),
                            str(payload.get("model_name", "") or ""),
                            str(payload.get("dialect", "") or ""),
                            _canonical_json(payload),
                            response_text,
                        ),
                    )
            return True
        except Exception:  # pragma: no cover - exercised in failure-safety tests
            return False

    def delete(self, request: Mapping[str, Any]) -> bool:
        if not self.enabled:
            return False
        cache_key = build_llm_response_cache_key(request)
        try:
            with self._lock:
                self._ensure_schema()
                with sqlite3.connect(self.path, timeout=30) as conn:
                    conn.execute("DELETE FROM llm_response_cache WHERE cache_key = ?", (cache_key,))
            return True
        except Exception:  # pragma: no cover - exercised in failure-safety tests
            return False

