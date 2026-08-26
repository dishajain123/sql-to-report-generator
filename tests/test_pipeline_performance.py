"""
Focused regression tests for pipeline performance behavior.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.ingestion import CodeChunk, IngestionResult, Parameter
from pipeline import LogicRulesExtractorPipeline


@dataclass
class _FakeChunkExtraction:
    chunk_id: str
    chunk_kind: str
    chunk_context: list[str]
    embedded_sql: list[str]
    data: dict
    raw_response: str = ""
    parse_error: str = ""
    guardrail_warnings: list[str] = None

    def __post_init__(self):
        if self.guardrail_warnings is None:
            self.guardrail_warnings = []


class _FakeRetrievalAgent:
    def __init__(self):
        self.calls = 0
        self.build_calls = 0
        self._loaded = True
        self._query_cache = {}

    def retrieve_context_text(self, query: str, k: int = 4) -> str:
        self.calls += 1
        return f"context for {query}"

    def build_or_load(self, force_rebuild: bool = False):
        self.build_calls += 1


class _FakeExtractionAgent:
    def __init__(self):
        self.calls = []

    def extract(self, **kwargs):
        chunk_id = kwargs["chunk_id"]
        self.calls.append(chunk_id)
        return _FakeChunkExtraction(
            chunk_id=chunk_id,
            chunk_kind=kwargs["chunk_kind"],
            chunk_context=kwargs.get("chunk_context", []),
            embedded_sql=kwargs.get("embedded_sql", []),
            data={
                "conditions": [],
                "loops": [],
                "tables_read": [],
                "tables_written": [],
                "calculations": [],
                "exception_handling": [],
                "ambiguities": [],
            },
        )


def _make_pipeline(chunk_workers: int = 2) -> LogicRulesExtractorPipeline:
    pipeline = LogicRulesExtractorPipeline.__new__(LogicRulesExtractorPipeline)
    pipeline.retrieval_k = 4
    pipeline.chunk_workers = chunk_workers
    pipeline.retrieval_agent = _FakeRetrievalAgent()
    pipeline.extraction_agent = _FakeExtractionAgent()
    pipeline.model_name = "test-model"
    return pipeline


def test_parallel_chunk_extraction_preserves_order():
    pipeline = _make_pipeline(chunk_workers=2)
    ingestion = IngestionResult(
        object_name="demo",
        object_type="PROCEDURE",
        parameters=[Parameter(name="p_id", direction="IN", datatype="NUMBER")],
        raw_code="BEGIN NULL; END;",
        chunks=[
            CodeChunk(chunk_id="02", kind="main_body", text="two", context_path=["main_body"]),
            CodeChunk(chunk_id="01", kind="main_body", text="one", context_path=["main_body"]),
            CodeChunk(chunk_id="03", kind="main_body", text="three", context_path=["main_body"]),
        ],
    )

    results = pipeline._extract_all_chunks(ingestion)

    assert [item.chunk_id for item in results] == ["02", "01", "03"]
    assert pipeline.retrieval_agent.calls == 3
    assert pipeline.extraction_agent.calls == ["02", "01", "03"]


def test_retriever_build_or_load_is_reused_when_already_loaded(tmp_path, monkeypatch):
    from src.retrieval import retriever as retriever_module

    agent = retriever_module.PatternRetrievalAgent(
        persist_directory=str(tmp_path / "chroma"),
        knowledge_base_dir="knowledge_base",
    )
    agent._loaded = True

    called = {"safe_list": 0}

    def fail_if_called():
        called["safe_list"] += 1
        raise AssertionError("should not be called when the store is already loaded")

    monkeypatch.setattr(agent, "_safe_list_collection_names", fail_if_called)

    agent.build_or_load()
    assert called["safe_list"] == 0


def test_retrieval_context_is_cached_for_duplicate_queries():
    pipeline = _make_pipeline(chunk_workers=1)
    ingestion = IngestionResult(
        object_name="demo",
        object_type="PROCEDURE",
        parameters=[Parameter(name="p_id", direction="IN", datatype="NUMBER")],
        raw_code="BEGIN NULL; END;",
        chunks=[
            CodeChunk(chunk_id="01", kind="main_body", text="same", context_path=["main_body"]),
            CodeChunk(chunk_id="02", kind="main_body", text="same", context_path=["main_body"]),
        ],
    )

    results = pipeline._extract_all_chunks(ingestion)

    assert [item.chunk_id for item in results] == ["01", "02"]
    assert pipeline.retrieval_agent.calls == 2
    assert pipeline.extraction_agent.calls == ["01"]


def test_pipeline_init_does_not_eagerly_build_kb(monkeypatch):
    import pipeline as pipeline_module

    class _DummyConfig:
        provider = "openai"
        api_key = "x"
        model_name = "test-model"
        base_url = None

    build_calls = {"count": 0}

    class _FakeRetrievalAgent:
        def __init__(self, *args, **kwargs):
            self._loaded = False

        def build_or_load(self, force_rebuild: bool = False):
            build_calls["count"] += 1

    monkeypatch.setattr(pipeline_module, "load_llm_config", lambda: _DummyConfig())
    monkeypatch.setattr(pipeline_module, "create_llm_client", lambda config: object())
    monkeypatch.setattr(pipeline_module, "PatternRetrievalAgent", _FakeRetrievalAgent)

    pipeline_module.LogicRulesExtractorPipeline(
        llm_config=_DummyConfig(),
        persist_directory="chroma_store",
        knowledge_base_dir="knowledge_base",
        dialect="auto",
    )

    assert build_calls["count"] == 0
