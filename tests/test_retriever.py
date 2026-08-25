"""
Unit tests for the retrieval/bootstrap layer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.retriever import PatternRetrievalAgent, _LocalHashEmbeddingFunction


def test_local_embedding_supports_chroma_query_api():
    embedding_function = _LocalHashEmbeddingFunction()

    embeddings = embedding_function.embed_query(["overdue days provisioning"])

    assert len(embeddings) == 1
    assert len(embeddings[0]) == 384


def test_retriever_builds_offline_with_local_embeddings(tmp_path):
    agent = PatternRetrievalAgent(
        persist_directory=str(tmp_path / "chroma"),
        knowledge_base_dir="knowledge_base",
    )

    agent.build_or_load(force_rebuild=True)

    context = agent.retrieve_context_text("overdue days provisioning classification", k=2)
    assert context.strip()
    assert "knowledge base" in context.lower() or "rbi" in context.lower()


def test_retriever_recovers_from_legacy_collection_config(tmp_path):
    agent = PatternRetrievalAgent(
        persist_directory=str(tmp_path / "chroma"),
        knowledge_base_dir="knowledge_base",
    )

    class _LegacyClient:
        def list_collections(self):
            raise KeyError("_type")

    agent._client = _LegacyClient()
    agent.build_or_load()

    context = agent.retrieve_context_text("overdue days provisioning classification", k=1)
    assert context.strip()


def test_retriever_caches_repeat_queries(tmp_path):
    agent = PatternRetrievalAgent(
        persist_directory=str(tmp_path / "chroma"),
        knowledge_base_dir="knowledge_base",
    )

    class _FakeCollection:
        def __init__(self):
            self.calls = 0

        def query(self, query_texts, n_results):
            self.calls += 1
            return {
                "documents": [["cached document"]],
                "metadatas": [[{"source": "kb.md"}]],
            }

    agent._collection = _FakeCollection()
    agent._loaded = True

    first = agent.retrieve_context_text("same query", k=2)
    second = agent.retrieve_context_text("same query", k=2)

    assert first == second
    assert agent._collection.calls == 1
