from __future__ import annotations

import json
import io
import zipfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main as main_module
from pipeline import PipelineRunResult
from src.batch.batch_runner import BatchInput, build_batch_archive_bytes, run_batch, _normalize_dialect_mode
from src.ingestion.ingestion import IngestionResult


def _make_ingestion(object_name: str, schema: str = "dbo") -> IngestionResult:
    return IngestionResult(
        object_name=object_name,
        object_type="PROCEDURE",
        parameters=[],
        raw_code="",
        chunks=[],
        schema=schema,
        canonical_object_name=object_name,
    )


def _load_manifest(batch_result) -> dict:
    manifest_path = Path(batch_result.manifest_path)
    assert manifest_path.exists()
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _make_result(object_name: str, report: str, verification: str) -> PipelineRunResult:
    return PipelineRunResult(
        report=report,
        verification_report=verification,
        ingestion=_make_ingestion(object_name),
    )


class _FakePipeline:
    def __init__(self, results_by_path: dict[str, PipelineRunResult], failures: set[str] | None = None):
        self.results_by_path = results_by_path
        self.failures = failures or set()
        self.calls: list[tuple[str, str | None]] = []
        self.model_name = "fake-model"

    def run(self, sql_file_path: str, dialect: str | None = None, progress_callback=None):
        self.calls.append((sql_file_path, dialect))
        if progress_callback:
            progress_callback(f"Stage 1/7: Starting {Path(sql_file_path).name}")
        if sql_file_path in self.failures:
            raise RuntimeError(f"boom: {Path(sql_file_path).name}")
        return self.results_by_path[sql_file_path]


def test_run_batch_processes_multiple_files_independently_and_writes_separate_outputs(tmp_path):
    input_one = tmp_path / "oracle.sql"
    input_two = tmp_path / "tsql.sql"
    input_one.write_text("select 1 from dual;", encoding="utf-8")
    input_two.write_text("select 2;", encoding="utf-8")

    result_one = _make_result("oracle_proc", "report one", "verification one")
    result_two = _make_result("tsql_proc", "report two", "verification two")
    pipeline = _FakePipeline(
        {
            str(input_one): result_one,
            str(input_two): result_two,
        }
    )

    batch_result = run_batch(
        pipeline,
        [
            BatchInput(source_path=str(input_one), display_name=input_one.name),
            BatchInput(source_path=str(input_two), display_name=input_two.name),
        ],
        output_dir=tmp_path / "outputs",
        batch_id="batch_001",
    )

    assert batch_result.batch_id == "batch_001"
    assert batch_result.success_count == 2
    assert batch_result.failure_count == 0
    assert pipeline.calls == [(str(input_one), "auto"), (str(input_two), "auto")]
    assert batch_result.output_dir == tmp_path / "outputs" / "batch_001"
    assert (batch_result.output_dir / "dbo.oracle_proc.StoredProcedure_report.md").exists()
    assert (batch_result.output_dir / "dbo.tsql_proc.StoredProcedure_report.md").exists()
    assert not (batch_result.output_dir / "dbo.oracle_proc.StoredProcedure_verification.md").exists()
    assert not (batch_result.output_dir / "dbo.tsql_proc.StoredProcedure_verification.md").exists()

    archive_bytes = build_batch_archive_bytes(batch_result)
    assert archive_bytes.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert sorted(archive.namelist()) == sorted(
            [
                "batch_manifest.json",
                "dbo.oracle_proc.StoredProcedure_report.md",
                "dbo.tsql_proc.StoredProcedure_report.md",
            ]
        )

    manifest = _load_manifest(batch_result)
    assert manifest["batch_id"] == "batch_001"
    assert manifest["total_files"] == 2
    assert manifest["successful_files"] == 2
    assert manifest["failed_files"] == 0
    assert manifest["files"][0]["filename"] == "oracle.sql"
    assert manifest["files"][0]["status"] == "success"
    assert manifest["files"][0]["selected_dialect_mode"] == "auto"
    assert manifest["files"][0]["detected_dialect"] == "ORACLE"
    assert manifest["files"][0]["effective_dialect"] == "ORACLE"
    assert manifest["files"][0]["object_identity"] == "dbo.oracle_proc.StoredProcedure"
    assert manifest["files"][0]["report_filename"] == "dbo.oracle_proc.StoredProcedure_report.md"
    assert "select 1 from dual" not in json.dumps(manifest).lower()


def test_run_batch_keeps_running_after_a_file_fails(tmp_path):
    input_one = tmp_path / "first.sql"
    input_two = tmp_path / "second.sql"
    input_three = tmp_path / "third.sql"
    for path in (input_one, input_two, input_three):
        path.write_text("select 1;", encoding="utf-8")

    result_one = _make_result("first_proc", "report one", "verification one")
    result_three = _make_result("third_proc", "report three", "verification three")
    pipeline = _FakePipeline(
        {
            str(input_one): result_one,
            str(input_three): result_three,
        },
        failures={str(input_two)},
    )

    batch_result = run_batch(
        pipeline,
        [
            BatchInput(source_path=str(input_one), display_name=input_one.name),
            BatchInput(source_path=str(input_two), display_name=input_two.name),
            BatchInput(source_path=str(input_three), display_name=input_three.name),
        ],
        output_dir=tmp_path / "outputs",
        batch_id="batch_002",
    )

    assert batch_result.success_count == 2
    assert batch_result.failure_count == 1
    assert [item.status for item in batch_result.items] == ["success", "failed", "success"]
    assert "boom: second.sql" in batch_result.items[1].error
    assert (batch_result.output_dir / "dbo.first_proc.StoredProcedure_report.md").exists()
    assert (batch_result.output_dir / "dbo.third_proc.StoredProcedure_report.md").exists()
    archive_bytes = build_batch_archive_bytes(batch_result)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert sorted(archive.namelist()) == sorted(
            [
                "batch_manifest.json",
                "dbo.first_proc.StoredProcedure_report.md",
                "dbo.third_proc.StoredProcedure_report.md",
            ]
        )

    manifest = _load_manifest(batch_result)
    assert manifest["total_files"] == 3
    assert manifest["successful_files"] == 2
    assert manifest["failed_files"] == 1
    assert [item["status"] for item in manifest["files"]] == ["success", "failed", "success"]
    assert manifest["files"][1]["error_message"].startswith("boom: second.sql")


def test_run_batch_writes_manifest_even_when_all_files_fail(tmp_path):
    input_one = tmp_path / "first.sql"
    input_two = tmp_path / "second.sql"
    input_one.write_text("select 1;", encoding="utf-8")
    input_two.write_text("select 2;", encoding="utf-8")

    pipeline = _FakePipeline({}, failures={str(input_one), str(input_two)})

    batch_result = run_batch(
        pipeline,
        [
            BatchInput(source_path=str(input_one), display_name=input_one.name),
            BatchInput(source_path=str(input_two), display_name=input_two.name),
        ],
        output_dir=tmp_path / "outputs",
        batch_id="batch_004",
    )

    assert batch_result.success_count == 0
    assert batch_result.failure_count == 2
    manifest = _load_manifest(batch_result)
    assert manifest["successful_files"] == 0
    assert manifest["failed_files"] == 2
    assert [item["status"] for item in manifest["files"]] == ["failed", "failed"]


def test_run_batch_manifest_write_failure_does_not_break_reports(tmp_path, monkeypatch):
    input_one = tmp_path / "single.sql"
    input_one.write_text("select 1;", encoding="utf-8")

    result_one = _make_result("single_proc", "report one", "verification one")
    pipeline = _FakePipeline({str(input_one): result_one})

    original_write_text = Path.write_text

    def _write_text_with_manifest_failure(self, data, encoding=None, errors=None):
        if self.name == "batch_manifest.json":
            raise OSError("manifest write failed")
        return original_write_text(self, data, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "write_text", _write_text_with_manifest_failure, raising=True)

    batch_result = run_batch(
        pipeline,
        [BatchInput(source_path=str(input_one), display_name=input_one.name)],
        output_dir=tmp_path / "outputs",
        batch_id="batch_005",
    )

    assert batch_result.success_count == 1
    assert batch_result.failure_count == 0
    assert (batch_result.output_dir / "dbo.single_proc.StoredProcedure_report.md").exists()
    assert not (batch_result.output_dir / "dbo.single_proc.StoredProcedure_verification.md").exists()
    assert batch_result.manifest_path.endswith("batch_manifest.json")
    assert not Path(batch_result.manifest_path).exists()


def test_run_batch_honors_per_file_dialect_overrides(tmp_path):
    input_one = tmp_path / "oracle.sql"
    input_two = tmp_path / "tsql.sql"
    input_one.write_text("select 1;", encoding="utf-8")
    input_two.write_text("select 2;", encoding="utf-8")

    result_one = _make_result("oracle_proc", "report one", "verification one")
    result_two = _make_result("tsql_proc", "report two", "verification two")
    pipeline = _FakePipeline(
        {
            str(input_one): result_one,
            str(input_two): result_two,
        }
    )

    batch_result = run_batch(
        pipeline,
        [
            BatchInput(source_path=str(input_one), display_name=input_one.name, dialect_mode="oracle"),
            BatchInput(source_path=str(input_two), display_name=input_two.name, dialect_mode="tsql"),
        ],
        output_dir=tmp_path / "outputs",
        batch_id="batch_override",
    )

    assert pipeline.calls == [(str(input_one), "oracle"), (str(input_two), "tsql")]
    manifest = _load_manifest(batch_result)
    assert [item["selected_dialect_mode"] for item in manifest["files"]] == ["oracle", "tsql"]


def test_run_batch_mixed_auto_and_overrides_and_invalid_mode_falls_back_to_auto(tmp_path):
    input_one = tmp_path / "auto.sql"
    input_two = tmp_path / "oracle.sql"
    input_three = tmp_path / "invalid.sql"
    for path in (input_one, input_two, input_three):
        path.write_text("select 1;", encoding="utf-8")

    result_one = _make_result("auto_proc", "report one", "verification one")
    result_two = _make_result("oracle_proc", "report two", "verification two")
    result_three = _make_result("invalid_proc", "report three", "verification three")
    pipeline = _FakePipeline(
        {
            str(input_one): result_one,
            str(input_two): result_two,
            str(input_three): result_three,
        }
    )

    batch_result = run_batch(
        pipeline,
        [
            BatchInput(source_path=str(input_one), display_name=input_one.name, dialect_mode="auto"),
            BatchInput(source_path=str(input_two), display_name=input_two.name, dialect_mode="oracle"),
            BatchInput(source_path=str(input_three), display_name=input_three.name, dialect_mode="bogus"),
        ],
        output_dir=tmp_path / "outputs",
        batch_id="batch_mixed",
    )

    assert pipeline.calls == [
        (str(input_one), "auto"),
        (str(input_two), "oracle"),
        (str(input_three), "auto"),
    ]
    manifest = _load_manifest(batch_result)
    assert [item["selected_dialect_mode"] for item in manifest["files"]] == ["auto", "oracle", "auto"]
    assert _normalize_dialect_mode("bogus") == "auto"


def test_run_batch_avoids_filename_collisions_with_duplicate_object_identity(tmp_path):
    input_one = tmp_path / "one.sql"
    input_two = tmp_path / "two.sql"
    input_one.write_text("select 1;", encoding="utf-8")
    input_two.write_text("select 2;", encoding="utf-8")

    result_one = _make_result("shared_proc", "report one", "verification one")
    result_two = _make_result("shared_proc", "report two", "verification two")
    pipeline = _FakePipeline(
        {
            str(input_one): result_one,
            str(input_two): result_two,
        }
    )

    batch_result = run_batch(
        pipeline,
        [
            BatchInput(source_path=str(input_one), display_name="same.sql"),
            BatchInput(source_path=str(input_two), display_name="same.sql"),
        ],
        output_dir=tmp_path / "outputs",
        batch_id="batch_003",
    )

    report_names = [Path(item.report_path).name for item in batch_result.successful_items]
    assert len(report_names) == 2
    assert len(set(report_names)) == 2
    assert report_names[0] == "dbo.shared_proc.StoredProcedure_report.md"
    assert report_names[1].startswith("dbo.shared_proc.StoredProcedure__2")


def test_main_single_file_workflow_still_writes_report_and_verification(tmp_path, monkeypatch):
    sql_file = tmp_path / "single.sql"
    sql_file.write_text("create procedure dbo.demo as begin select 1; end", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class _FakePipelineForMain:
        def __init__(self, *args, **kwargs):
            self.model_name = "fake-model"
            self.retrieval_agent = type("R", (), {"build_or_load": lambda self, force_rebuild=False: None})()

        def run(self, sql_file_path: str, dialect: str | None = None, progress_callback=None):
            return _make_result("demo_proc", "main report", "main verification")

    monkeypatch.setattr(main_module, "LogicRulesExtractorPipeline", _FakePipelineForMain)

    exit_code = main_module.main([str(sql_file)])
    assert exit_code == 0

    report_path = tmp_path / "samples" / "output" / "dbo.demo_proc.StoredProcedure_report.md"
    assert report_path.exists()
    assert not (tmp_path / "samples" / "output" / "dbo.demo_proc.StoredProcedure_verification.md").exists()
