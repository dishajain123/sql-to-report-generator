"""
Unit tests for the retrieval/bootstrap layer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.retrieval.retriever import PatternRetrievalAgent, _LocalHashEmbeddingFunction


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


def test_retriever_breaks_equal_distance_ties_deterministically(tmp_path):
    """Chroma's HNSW index does not guarantee a stable order for results
    tied on distance - two runs of the exact same query against the exact
    same collection can come back with equal-distance documents in a
    different order, which changes the RAG context text handed to the LLM
    prompt and is a real source of run-to-run output variation. `retrieve`
    must re-sort by (distance, document text) so ties always resolve the
    same way regardless of what order the fake/real backend returned them.
    """
    agent = PatternRetrievalAgent(
        persist_directory=str(tmp_path / "chroma2"),
        knowledge_base_dir="knowledge_base",
    )

    class _TiedCollection:
        def __init__(self, order):
            self._order = order

        def query(self, query_texts, n_results, include=None):
            # Simulate Chroma returning three equal-distance documents in
            # whatever order this call happens to receive them in.
            docs = [f"doc-{name}" for name in self._order]
            metas = [{"source": f"{name}.md"} for name in self._order]
            distances = [0.5, 0.5, 0.5]
            return {"documents": [docs], "metadatas": [metas], "distances": [distances]}

    agent._collection = _TiedCollection(["c", "a", "b"])
    agent._loaded = True
    first = agent.retrieve("tie query", k=3)

    agent2 = PatternRetrievalAgent(
        persist_directory=str(tmp_path / "chroma3"),
        knowledge_base_dir="knowledge_base",
    )
    agent2._collection = _TiedCollection(["b", "c", "a"])
    agent2._loaded = True
    second = agent2.retrieve("tie query", k=3)

    assert [doc for doc, _ in first] == [doc for doc, _ in second]
    assert [doc for doc, _ in first] == ["doc-a", "doc-b", "doc-c"]


def test_retriever_caches_repeat_queries(tmp_path):
    agent = PatternRetrievalAgent(
        persist_directory=str(tmp_path / "chroma"),
        knowledge_base_dir="knowledge_base",
    )

    class _FakeCollection:
        def __init__(self):
            self.calls = 0

        def query(self, query_texts, n_results, include=None):
            self.calls += 1
            return {
                "documents": [["cached document"]],
                "metadatas": [[{"source": "kb.md"}]],
                "distances": [[0.1]],
            }

    agent._collection = _FakeCollection()
    agent._loaded = True

    first = agent.retrieve_context_text("same query", k=2)
    second = agent.retrieve_context_text("same query", k=2)

    assert first == second
    assert agent._collection.calls == 1


def test_retriever_removes_only_exact_duplicate_context_blocks():
    pairs = [
        ("same guidance", {"source": "oracle.md"}),
        ("same guidance", {"source": "oracle.md"}),
        ("different guidance", {"source": "tsql.md"}),
    ]

    result = PatternRetrievalAgent._deduplicate_context_pairs(pairs)

    assert result == [pairs[0], pairs[2]]


def test_retriever_keeps_identical_text_with_different_source_labels():
    pairs = [
        ("shared guidance", {"source": "oracle.md"}),
        ("shared guidance", {"source": "tsql.md"}),
    ]

    result = PatternRetrievalAgent._deduplicate_context_pairs(pairs)

    assert result == pairs


def test_retriever_preserves_context_order_after_deduplication():
    pairs = [
        ("first", {"source": "one.md"}),
        ("second", {"source": "two.md"}),
        ("first", {"source": "one.md"}),
        ("third", {"source": "three.md"}),
    ]

    result = PatternRetrievalAgent._deduplicate_context_pairs(pairs)

    assert [doc for doc, _ in result] == ["first", "second", "third"]
