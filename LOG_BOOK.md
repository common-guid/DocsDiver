## ADK implementation | 2026/1/24
had jules use the PRD from gemini to create an implementation plan. then had a second jules instance take the implementation plan to create an MVP
## Langfuse Observability Integration | 2026-01-24
Integrated Langfuse observability using OpenTelemetry and `openinference-instrumentation-google-adk`, configuring the `ADK-DocsDiver` tag for all traces and setting up environment-based configuration.
## Langsmith observability integration | 2026-01-24
integrated the langsmith tracing along side the langfuse
## Gemini API | 2026-01-24
added gemini api support to complimient openrouter
## Configuration & env docs | 2026-01-24
Documented configuration options and environment variables in README, including which are required versus optional for core runtime and observability.
## Python 3.14 Compatibility Fix | 2026-01-24
Fixed `langfuse` import crash on Python 3.14 due to `pydantic` v1 incompatibility. Added graceful fallback to disable Langfuse observability if import fails, ensuring the application can start.
## Validation & Bug Fixes | 2026-01-24
Validated the fix by running the application with `python main.py -m gemini`. Resolved additional issues found during validation:
- Fixed `map_maker.py` hardcoding `mock-model` which caused API errors.
- Updated `config.yaml` to use `gemini-2.5-pro` as `gemini-1.5-pro` was not available in the environment.
Validated that the application starts and attempts API calls (confirmed by Quota Exceeded response).
## Connection Validation Scripts | 2026-01-24
Created `scripts/validate_connections.py` to verify connectivity to Gemini and OpenRouter APIs. Updated `tests/test_instrumentation.py` to ensure regression testing for the Langfuse import failure scenario.
## ToC Tag Generation | 2026-01-25
Updated the Map Maker (`sdaa/src/core/map_maker.py`) so each ToC entry includes a summary and three keyword tags, and adjusted `tests/test_map_maker.py` to validate the new `tags` field.
## ToC Tag-Aware Agents | 2026-01-25
Refined worker agent prompts in `sdaa/src/agents/workers.py` so the permissions, constraints, and boundaries agents treat ToC `tags` as primary metadata when deciding which documentation files to read.
## Langfuse Offline Handling | 2026-01-25
Improved `setup_instrumentation` so that Langfuse OTLP export is disabled gracefully when the configured `LANGFUSE_HOST` is unreachable, preventing noisy connection-refused stack traces during normal chat usage.
## Map Maker Output Directory & Skip Controls | 2026-01-25
Added a configurable `system.output_dir` for routing `ToC.json`, `Security_Threat_Model.md`, and future artifacts, introduced `--skip-map-maker` and `--toc-only` CLI flags, and updated Map Maker, reporting, tests, and docs to respect the new output path.
## Skip ToC Generation Tests | 2026-01-25
Added `tests/test_main_skip_map_maker.py` to verify Map Maker is called when ToC is missing, skipped when a ToC already exists or `--skip-map-maker` is set, and that the coordinator and agents still initialize correctly when reusing a precomputed ToC.
## README output_dir & skip-map-maker docs | 2026-01-25
Updated README configuration guidance to include `system.output_dir` and added usage notes for `--skip-map-maker` to reuse an existing ToC.
## README toc-only docs | 2026-01-25
Added README usage notes for `--toc-only` to generate `ToC.json` and exit without starting the interactive session.
## Langfuse OTEL Endpoint Fix | 2026-01-25
Updated `setup_instrumentation` to use the documented Langfuse OTEL HTTP traces endpoint (`/api/public/otel/v1/traces`), added an optional `LANGFUSE_OTEL_TRACES_ENDPOINT` override, and extended `scripts/validate_langfuse_conn.py` to validate end-to-end Langfuse connectivity.
## Langfuse + LangSmith unified instrumentation | 2026-01-26
Consolidated tracing setup so both LangSmith and Langfuse exporters attach to the same OpenTelemetry provider, restoring dual-platform trace delivery after the branch merge.
## python-dotenv dependency install | 2026-01-28
Created a project virtual environment and installed requirements to resolve the missing `dotenv` import when running `main.py`.
## Suppress google-genai non-text warning | 2026-01-28
Added a targeted logging filter to silence the noisy non-text response warning while preserving normal tool-call behavior.
## Pre-chat sequential audit artifacts | 2026-01-28
Implemented a sequential pre-chat audit pipeline that generates worker artifacts and the synthesized coordinator report only when outputs are missing, and added tests for gating and ordering.
## Boundary reporting schema fix | 2026-01-28
Simplified the boundary reporting tool to accept markdown-only input to avoid invalid Gemini tool schemas, and updated tests accordingly.
## ToC.json accessibility fix | 2026-01-30
Updated `sdaa/src/tools/file_ops.py` so `read_file("ToC.json")` reads the table of contents from the configured `system.output_dir`, allowing pre-chat and interactive agents to consume the generated ToC.
## Per-Agent Model Configuration & Factory | 2025-05-15
Refactored the configuration system to allow specifying different models for `openrouter` and `gemini` per agent, and implemented a factory pattern to instantiate the correct model based on the selected provider at runtime.
## OpenRouter Tooling Fixes | 2026-01-30
- Implemented tool support for OpenRouter in `sdaa/src/utils/openrouter_model.py`.
- Fixed `No function call event found` error in OpenRouter integration.
    - Diagnosed that ADK Runner requires strict adherence to `role="model"` for response content to register function calls.
    - Identified that ADK Runner likely expects/generates tool IDs in `functions.{name}:{index}` format.
    - Updated `OpenRouterModel` to set `role="model"` and generate compliant tool IDs, enabling successful tool execution and history validation.