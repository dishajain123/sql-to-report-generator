# Evaluation Framework

Run the golden-dataset evaluator from the repository root:

```bash
python evaluate.py
```

Options:
- `--mode auto` uses live pipeline execution when LLM settings are available, otherwise falls back to deterministic mode.
- `--mode live` requires a configured LLM backend.
- `--mode deterministic` runs only the deterministic front half of the pipeline.

The evaluator writes its latest baseline to `evaluation/baseline.json`.

