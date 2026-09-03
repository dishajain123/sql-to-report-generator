"""
agents/retriever.py
--------------------
Pattern Retrieval Agent (the RAG layer).

Pure Python + `chromadb` only - no orchestration framework involved.
Loads a curated knowledge base (Markdown/text files under
`knowledge_base/`) describing:
    - Common SQL/PL-SQL construct semantics (cursors, MERGE, exception
      handlers, dynamic SQL, bulk collect, etc.)
    - Banking domain rules (e.g. RBI IRAC NPA classification thresholds
      and provisioning percentages)

into a local, file-based ChromaDB collection, and exposes a
`retrieve()` method that the Logic Extraction Agent calls per code
chunk to fetch grounding context before interpretation.

Embeddings are produced locally via a deterministic hash-based embedding
function, so the RAG layer works entirely offline / free of additional
API cost - only the two LLM reasoning stages (logic_extractor,
rule_synthesizer) call out to the configured chat completion provider.
"""

from __future__ import annotations

import re
import hashlib
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import posthog

    def _noop_capture(*args, **kwargs):  # pragma: no cover - trivial shim
        return None

    posthog.disabled = True
    posthog.capture = _noop_capture
except Exception:
    pass

import chromadb
from chromadb.api.shared_system_client import SharedSystemClient

DEFAULT_EMBEDDING_MODEL = "local-hash-384"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100
_ADD_BATCH_SIZE = 100
_EMBEDDING_DIMENSION = 384


class _LocalHashEmbeddingFunction:
    """Deterministic, fully local embedding function.

    Chroma only needs a callable that turns text into vectors. Using a
    local hash-based embedding avoids Hugging Face downloads and keeps
    the app usable offline while still providing stable semantic-ish
    retrieval over the curated knowledge base.

    Implements the small bit of chromadb's ``EmbeddingFunction`` protocol
    (``name`` / ``build_from_config`` / ``get_config``) that newer chromadb
    versions (1.x) require even for a hand-rolled function - without it,
    ``get_or_create_collection`` on an existing persisted collection raises
    ``AttributeError: '_LocalHashEmbeddingFunction' object has no
    attribute 'name'`` from chromadb's own conflict-validation code before
    a single query ever runs, silently breaking retrieval/RAG in offline
    mode. Reporting itself as chromadb's reserved "default" name keeps
    that conflict check a no-op (see chromadb.api.collection_configuration
    .validate_embedding_function_conflict_on_get) without depending on
    chromadb's actual default (network-downloaded) embedding function.
    """

    def __init__(self, dimension: int = _EMBEDDING_DIMENSION):
        self.dimension = dimension

    def __call__(self, input):  # Chroma expects a callable embedding function
        return [self._embed_text(text) for text in input]

    def embed_query(self, input):
        """Return query embeddings for Chroma versions with split APIs."""
        return [self._embed_text(text) for text in input]

    @staticmethod
    def name() -> str:
        return "default"

    @staticmethod
    def build_from_config(config):
        return _LocalHashEmbeddingFunction(dimension=(config or {}).get("dimension", _EMBEDDING_DIMENSION))

    def get_config(self):
        return {"dimension": self.dimension}

    def is_legacy(self) -> bool:
        return False

    def _embed_text(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[A-Za-z0-9_]+", (text or "").lower())
        if not tokens:
            return vector

        for idx, token in enumerate(tokens):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            weight = 1.0 + (len(token) / 10.0)
            vector[bucket] += weight
            if idx + 1 < len(tokens):
                bigram = f"{token}:{tokens[idx + 1]}"
                digest2 = hashlib.blake2b(bigram.encode("utf-8"), digest_size=16).digest()
                bucket2 = int.from_bytes(digest2[:4], "big") % self.dimension
                vector[bucket2] += 0.5

        norm = sum(v * v for v in vector) ** 0.5
        if norm:
            vector = [v / norm for v in vector]
        return vector


def _split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """Minimal, dependency-free text splitter.

    Groups paragraphs (blank-line separated) into chunks up to
    `chunk_size` characters, hard-wrapping any single paragraph that is
    still too long on its own, and stitches a small overlap between
    consecutive chunks so context isn't lost right at a chunk boundary.
    This replaces the need for a text-splitting library.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]

    raw_chunks: List[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 2 <= chunk_size:
            buf = f"{buf}\n\n{para}" if buf else para
            continue

        if buf:
            raw_chunks.append(buf)
            buf = ""

        if len(para) <= chunk_size:
            buf = para
        else:
            start = 0
            while start < len(para):
                end = start + chunk_size
                raw_chunks.append(para[start:end])
                start = end - chunk_overlap if end - chunk_overlap > start else end
    if buf:
        raw_chunks.append(buf)

    if not chunk_overlap or len(raw_chunks) <= 1:
        return raw_chunks

    overlapped = [raw_chunks[0]]
    for i in range(1, len(raw_chunks)):
        prev_tail = raw_chunks[i - 1][-chunk_overlap:]
        overlapped.append(f"{prev_tail}\n{raw_chunks[i]}")
    return overlapped


class PatternRetrievalAgent:
    """Wraps a local Chroma collection of SQL/PLSQL + banking-domain
    pattern documents and provides similarity-search based retrieval.
    """

    def __init__(
        self,
        persist_directory: str = "chroma_store",
        knowledge_base_dir: str = "knowledge_base",
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        collection_name: str = "logic_rules_patterns",
    ):
        self.persist_directory = persist_directory
        self.knowledge_base_dir = knowledge_base_dir
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self._embedding_fn = _LocalHashEmbeddingFunction()
        self._client = self._create_client()
        self._collection = None
        self._loaded = False
        self._lock = threading.RLock()
        self._query_cache: Dict[Tuple[str, int], List[Tuple[str, Dict[str, str]]]] = {}

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def build_or_load(self, force_rebuild: bool = False) -> None:
        """Create (or fetch) the Chroma collection. Populates it from the
        knowledge base directory only if it is currently empty, or if
        `force_rebuild` is set (in which case any existing collection is
        dropped and rebuilt from scratch).
        """
        with self._lock:
            if self._loaded and not force_rebuild:
                return

            if force_rebuild:
                self._query_cache.clear()
                existing_names = self._safe_list_collection_names()
                if self.collection_name in existing_names:
                    self._client.delete_collection(self.collection_name)

            if not hasattr(self._client, "get_or_create_collection"):
                self._client = self._create_client()

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name, embedding_function=self._embedding_fn
            )

            if self._collection.count() > 0:
                self._loaded = True
                return  # already populated, nothing to do

            documents, metadatas, ids = self._load_knowledge_base()
            for i in range(0, len(documents), _ADD_BATCH_SIZE):
                self._collection.add(
                    documents=documents[i : i + _ADD_BATCH_SIZE],
                    metadatas=metadatas[i : i + _ADD_BATCH_SIZE],
                    ids=ids[i : i + _ADD_BATCH_SIZE],
                )
            self._loaded = True

    def _create_client(self):
        return chromadb.PersistentClient(path=self.persist_directory)

    def _safe_list_collection_names(self) -> set[str]:
        try:
            return {c.name for c in self._client.list_collections()}
        except Exception as exc:
            if self._is_legacy_collection_configuration_error(exc):
                self._rebuild_persisted_store()
                return set()
            raise

    def _rebuild_persisted_store(self) -> None:
        """Drop an incompatible persisted Chroma store and recreate it.

        Older Chroma stores can contain collection configuration JSON
        that lacks the newer ``_type`` field, which causes the current
        client to fail when listing collections. Since this project
        derives the vector store entirely from the checked-in knowledge
        base, it is safe to rebuild the store automatically.
        """
        SharedSystemClient.clear_system_cache()
        store_path = Path(self.persist_directory)
        if store_path.exists():
            shutil.rmtree(store_path)
        self._client = self._create_client()
        self._collection = None
        self._loaded = False

    @staticmethod
    def _is_legacy_collection_configuration_error(exc: Exception) -> bool:
        message = str(exc)
        return (
            (isinstance(exc, KeyError) and exc.args and exc.args[0] == "_type")
            or ("_type" in message and "CollectionConfiguration" in message)
        )

    def _load_knowledge_base(self) -> Tuple[List[str], List[Dict[str, str]], List[str]]:
        kb_path = Path(self.knowledge_base_dir)
        if not kb_path.exists():
            raise FileNotFoundError(
                f"Knowledge base directory not found: {self.knowledge_base_dir}"
            )

        documents: List[str] = []
        metadatas: List[Dict[str, str]] = []
        ids: List[str] = []
        counter = 0

        for file_path in sorted(kb_path.glob("**/*")):
            if file_path.suffix.lower() not in (".md", ".txt"):
                continue
            text = file_path.read_text(encoding="utf-8", errors="replace")
            for chunk in _split_text(text):
                documents.append(chunk)
                metadatas.append({"source": file_path.name})
                ids.append(f"{file_path.stem}_{counter}")
                counter += 1

        if not documents:
            raise ValueError(
                f"No .md/.txt knowledge base documents found in {self.knowledge_base_dir}"
            )
        return documents, metadatas, ids

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(self, query: str, k: int = 4) -> List[Tuple[str, Dict[str, str]]]:
        cache_key = (query, k)
        with self._lock:
            cached = self._query_cache.get(cache_key)
            if cached is not None:
                return [(doc, dict(meta or {})) for doc, meta in cached]

            if self._collection is None:
                self.build_or_load()

            results = self._collection.query(query_texts=[query], n_results=k)
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            pairs = list(zip(docs, metas))
            self._query_cache[cache_key] = [(doc, dict(meta or {})) for doc, meta in pairs]
            return pairs

    def retrieve_context_text(self, query: str, k: int = 4) -> str:
        """Convenience helper returning retrieved docs pre-joined into a
        single context string ready to be dropped into an LLM prompt.
        """
        pairs = self.retrieve(query, k=k)
        if not pairs:
            return "No directly relevant pattern context found."
        pairs = self._deduplicate_context_pairs(pairs)
        blocks = []
        for doc_text, meta in pairs:
            source = (meta or {}).get("source", "knowledge_base")
            blocks.append(f"[Source: {source}]\n{doc_text.strip()}")
        return "\n\n".join(blocks)

    @staticmethod
    def _deduplicate_context_pairs(
        pairs: List[Tuple[str, Dict[str, str]]],
    ) -> List[Tuple[str, Dict[str, str]]]:
        """Remove only exact duplicate LLM context blocks.

        Retrieval results remain unchanged. This affects only the string sent
        to extraction. The source label is part of the identity so identical
        text from separately labelled sources is retained rather than losing
        provenance. First occurrence wins, preserving retrieval order.
        """
        unique: List[Tuple[str, Dict[str, str]]] = []
        seen = set()
        for doc_text, meta in pairs or []:
            metadata = dict(meta or {})
            source = metadata.get("source", "knowledge_base")
            key = (str(source), str(doc_text).strip())
            if key in seen:
                continue
            seen.add(key)
            unique.append((doc_text, metadata))
        return unique
