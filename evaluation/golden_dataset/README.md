# Golden Dataset

This directory stores the small regression set used to evaluate the SQL extraction pipeline.

Structure:
- `manifest.json` maps each case to its SQL source and expected-result file.
- `expected/` contains the manually reviewed expectations.
- `oracle/`, `tsql/`, and `edge_cases/` contain the SQL examples or references used by the cases.

The evaluator can run in:
- `live` mode when LLM settings are configured, using the full production pipeline.
- `deterministic` mode when LLM settings are unavailable, using ingestion plus deterministic SQL/AST extraction.

The initial baseline in this checkout is generated in deterministic mode because the LLM environment is not configured in the sandbox.

