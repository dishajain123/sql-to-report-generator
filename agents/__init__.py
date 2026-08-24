"""
agents package
----------------
Contains the five isolated agents that make up the Agentic RAG pipeline:

    ingestion.py        -> CodeIngestionAgent
    retriever.py         -> PatternRetrievalAgent
    logic_extractor.py   -> LogicExtractionAgent
    rule_synthesizer.py  -> RuleSynthesizerAgent
    report_formatter.py  -> ReportFormatterAgent

Each agent is intentionally kept independent (no agent imports another
agent) so they can be unit tested, swapped, or re-ordered by the
`pipeline.py` orchestrator without side effects.
"""
