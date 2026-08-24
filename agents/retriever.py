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

Embeddings are produced locally via chromadb's built-in
`SentenceTransformerEmbeddingFunction` (all-MiniLM-L6-v2), so the RAG
layer works entirely offline / free of additional API cost - only the
two LLM reasoning stages (logic_extractor, rule_synthesizer) call out
to Groq.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100
_ADD_BATCH_SIZE = 100


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
        self._embedding_fn = SentenceTransformerEmbeddingFunction(model_name=embedding_model)
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = None

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def build_or_load(self, force_rebuild: bool = False) -> None:
        """Create (or fetch) the Chroma collection. Populates it from the
        knowledge base directory only if it is currently empty, or if
        `force_rebuild` is set (in which case any existing collection is
        dropped and rebuilt from scratch).
        """
        existing_names = {c.name for c in self._client.list_collections()}
        if force_rebuild and self.collection_name in existing_names:
            self._client.delete_collection(self.collection_name)

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name, embedding_function=self._embedding_fn
        )

        if self._collection.count() > 0:
            return  # already populated, nothing to do

        documents, metadatas, ids = self._load_knowledge_base()
        for i in range(0, len(documents), _ADD_BATCH_SIZE):
            self._collection.add(
                documents=documents[i : i + _ADD_BATCH_SIZE],
                metadatas=metadatas[i : i + _ADD_BATCH_SIZE],
                ids=ids[i : i + _ADD_BATCH_SIZE],
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
        if self._collection is None:
            self.build_or_load()
        results = self._collection.query(query_texts=[query], n_results=k)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return list(zip(docs, metas))

    def retrieve_context_text(self, query: str, k: int = 4) -> str:
        """Convenience helper returning retrieved docs pre-joined into a
        single context string ready to be dropped into an LLM prompt.
        """
        pairs = self.retrieve(query, k=k)
        if not pairs:
            return "No directly relevant pattern context found."
        blocks = []
        for doc_text, meta in pairs:
            source = (meta or {}).get("source", "knowledge_base")
            blocks.append(f"[Source: {source}]\n{doc_text.strip()}")
        return "\n\n".join(blocks)
