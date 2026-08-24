#!/usr/bin/env python3
"""
main.py
--------
CLI entry point for the AI-Powered DB Logic & Business Rules Extractor.

Usage
-----
    python main.py samples/npa_classification.sql
    python main.py samples/npa_classification.sql --model llama-3.1-8b-instant
    python main.py samples/provisioning_view.sql --output samples/output/report.md
    python main.py samples/npa_classification.sql --rebuild-kb

Environment
-----------
Reads GROQ_API_KEY (and optional overrides) from a `.env` file in the
project root (see config/.env.example) via python-dotenv.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from pipeline import LogicRulesExtractorPipeline, DEFAULT_MODEL


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logic-rules-extractor",
        description=(
            "Reverse-engineer a banking stored procedure / function / view / "
            "trigger / PL-SQL block (.sql file) into structured, business-"
            "focused Markdown documentation."
        ),
    )
    parser.add_argument(
        "sql_file",
        type=str,
        help="Path to the input .sql file containing exactly one DB object.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("GROQ_MODEL", DEFAULT_MODEL),
        help=(
            "Groq model to use for extraction/synthesis "
            "(e.g. llama-3.3-70b-versatile, llama-3.1-8b-instant). "
            f"Default: {DEFAULT_MODEL} (or $GROQ_MODEL if set)."
        ),
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="LLM sampling temperature. Default: 0.1 (extraction favors determinism).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Path to write the generated Markdown report. Defaults to "
        "samples/output/<object_name>.md",
    )
    parser.add_argument(
        "--kb-dir",
        type=str,
        default="knowledge_base",
        help="Path to the pattern/domain knowledge base directory. Default: knowledge_base/",
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default="chroma_store",
        help="Path to the local ChromaDB persistence directory. Default: chroma_store/",
    )
    parser.add_argument(
        "--rebuild-kb",
        action="store_true",
        help="Force rebuild of the ChromaDB vector store from the knowledge base directory.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (INFO-level) pipeline logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    args = build_arg_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    sql_path = Path(args.sql_file)
    if not sql_path.exists():
        print(f"Error: input file not found: {sql_path}", file=sys.stderr)
        return 1

    try:
        pipeline = LogicRulesExtractorPipeline(
            model_name=args.model,
            temperature=args.temperature,
            persist_directory=args.persist_dir,
            knowledge_base_dir=args.kb_dir,
        )
        if args.rebuild_kb:
            pipeline.retrieval_agent.build_or_load(force_rebuild=True)
    except EnvironmentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Running pipeline on '{sql_path}' using Groq model '{args.model}'...")
    report_markdown = pipeline.run(str(sql_path))

    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path("samples/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{sql_path.stem}_report.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_markdown, encoding="utf-8")

    print(f"Report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
