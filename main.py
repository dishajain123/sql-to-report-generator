#!/usr/bin/env python3
"""
main.py
--------
CLI entry point for the AI-Powered DB Logic & Business Rules Extractor.

Usage
-----
    python main.py samples/npa_classification.sql
    python main.py samples/provisioning_view.sql --output samples/output/report.md
    python main.py samples/npa_classification.sql --rebuild-kb

Environment
-----------
Reads LLM_PROVIDER, LLM_API_KEY, LLM_MODEL_NAME, and LLM_BASE_URL from
a `.env` file in the project root (see config/.env.example) via
python-dotenv.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

from dotenv import load_dotenv

from pipeline import LogicRulesExtractorPipeline, PipelineInputError
from src.batch.batch_runner import BatchInput, build_batch_archive_bytes, run_batch
from src.ingestion.ingestion import build_object_identity_stem


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
        "sql_files",
        type=str,
        nargs="+",
        help=(
            "Path(s) to one or more .sql files. A single input preserves the "
            "existing single-file workflow; multiple inputs are processed "
            "independently."
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
        "samples/output/<Schema>.<ObjectName>.<Type>_report.md, named from "
        "the SQL object's own parsed identity (not the input filename). "
        "Verification and traceability diagnostics are written to the run log, "
        "not to a separate Markdown artifact.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=(
            "Directory for batch outputs. Defaults to "
            "samples/output/batches/<batch_id> when multiple files are given."
        ),
    )
    parser.add_argument(
        "--dialect",
        type=str,
        choices=["auto", "oracle", "tsql"],
        default="auto",
        help=(
            "SQL dialect of the input object. 'auto' (default) detects Oracle "
            "SQL/PL-SQL vs SQL Server T-SQL from the source; pass 'oracle' or "
            "'tsql' to override detection explicitly."
        ),
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


@contextmanager
def _capture_run_logs(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    previous_level = root_logger.level
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root_logger.addHandler(handler)
    if previous_level > logging.INFO or previous_level == logging.NOTSET:
        root_logger.setLevel(logging.INFO)
    try:
        yield
    finally:
        root_logger.removeHandler(handler)
        handler.close()
        root_logger.setLevel(previous_level)


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=True)

    args = build_arg_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    sql_paths = [Path(path) for path in args.sql_files]
    for sql_path in sql_paths:
        if not sql_path.exists():
            print(f"Error: input file not found: {sql_path}", file=sys.stderr)
            return 1

    try:
        pipeline = LogicRulesExtractorPipeline(
            temperature=args.temperature,
            persist_directory=args.persist_dir,
            knowledge_base_dir=args.kb_dir,
            dialect=args.dialect,
        )
        if args.rebuild_kb:
            pipeline.retrieval_agent.build_or_load(force_rebuild=True)
    except EnvironmentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if len(sql_paths) > 1:
        if args.output:
            print(
                "Error: --output is only supported for single-file runs; use --output-dir for batch runs.",
                file=sys.stderr,
            )
            return 1
        batch_inputs = [BatchInput(source_path=str(path), display_name=path.name) for path in sql_paths]
        batch_output_dir = Path(args.output_dir) if args.output_dir else Path("samples/output/batches")
        print(
            f"Running batch pipeline on {len(batch_inputs)} files using model '{pipeline.model_name}' "
            f"(per-file dialect auto-detection)..."
        )
        try:
            batch_result = run_batch(
                pipeline,
                batch_inputs,
                output_dir=batch_output_dir,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Error: batch pipeline failed: {exc}", file=sys.stderr)
            return 1

        archive_path = batch_result.output_dir / f"{batch_result.batch_id}.zip"
        archive_path.write_bytes(build_batch_archive_bytes(batch_result))

        print(f"Batch ID: {batch_result.batch_id}")
        print(f"Batch outputs written to: {batch_result.output_dir}")
        for item in batch_result.items:
            if item.status == "success":
                print(f"[OK] {item.display_name} -> {item.report_path}")
            else:
                print(f"[FAIL] {item.display_name} -> {item.error}")
        print(f"Batch archive written to: {archive_path}")
        return 0 if batch_result.failure_count == 0 else 2

    sql_path = sql_paths[0]

    logs_dir = Path("samples/output/logs")
    log_path = logs_dir / f"{sql_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pipeline.log"

    print(
        f"Running pipeline on '{sql_path}' using model '{pipeline.model_name}' "
        f"(dialect: {args.dialect})..."
    )
    try:
        with _capture_run_logs(log_path):
            run_result = pipeline.run(str(sql_path), dialect=args.dialect)
    except PipelineInputError as exc:
        print(f"Error: input rejected by guardrails: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: pipeline failed: {exc}", file=sys.stderr)
        return 1

    report_stem = build_object_identity_stem(run_result.ingestion, fallback_stem=sql_path.stem)

    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path("samples/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{report_stem}_report.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(run_result.report, encoding="utf-8")

    print(f"Report written to: {output_path}")
    print(f"Run log written to: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
