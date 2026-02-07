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
Updated `sdaa/src/tools/file_ops.py` so `read_file("ToC.json")` reads the table of contents from the configured `system.output_dir`, allowing pre-chat and interactive audits to consume the generated ToC.
## Per-Agent Model Configuration & Factory | 2025-05-15
Refactored the configuration system to allow specifying different models for `openrouter` and `gemini` per agent, and implemented a factory pattern to instantiate the correct model based on the selected provider at runtime.
## OpenRouter Tooling Fixes | 2026-01-30
- Implemented tool support for OpenRouter in `sdaa/src/utils/openrouter_model.py`.
- Fixed `No function call event found` error in OpenRouter integration via `role="model"` enforcement.
## Gemini Role Fix for Map Maker | 2026-01-31
- Fixed `400 INVALID_ARGUMENT` error in `map_maker.py` by adding explicit `role="user"` to `LlmRequest`.
- Verified fix enables successful ToC generation with Gemini while maintaining OpenRouter compatibility.
## Path Access Error Fix | 2026-01-31
- Identified `Access denied` error caused by agents following relative links to files outside the documentation root in `workspace-settings.md`.
- Updated `sdaa/src/agents/workers.py` to strictly instruct agents in the system prompt to **only** access files explicitly listed in `ToC.json`.
- Verified the fix by running the pre-chat audit; agents successfully ignored valid-looking but out-of-bounds relative links.
## Operation Optimization | 2026-02-01
Implemented optimization to skip redundant worker execution during pre-chat audit.
-   Added `ArtifactLoaderModel` to load existing artifacts instead of re-running agents.
-   Added `--coordinator-only` CLI flag to bypass Map Maker and Workers, running only the Coordinator to synthesize the final report from existing artifacts.
-   Refactored `main.py` to support these optimization flags.

## Skip Workers Logic Fix | 2026-02-01
Resolved two crashing bugs when using the skip-workers optimization (existing artifacts).
- Fixed `ArtifactLoaderModel` to simulate a proper tool execution loop by returning a `FunctionCall` followed by a text response, preventing "malformed function call" errors.
- Fixed `KeyError: Context variable not found: id` in the Google ADK by defining a prompt sanitization layer that replaces identifier-like curly braces (e.g., `{id}` -> `(id)`) in both Langfuse-fetched prompts and injected report content, preventing the ADK's template engine from attempting invalid substitutions.

## Langfuse Linked Generation | 2026-02-01
Enabled "Linked Generation" feature for Langfuse to link managed prompts to traces.
- Extended `PromptManager` to return raw prompt objects.
- Created `InstrumentedGemini` and updated `OpenRouterModel` to inject `langfuse.prompt.name` and `version` attributes into OpenTelemetry spans.
- Updated agent factories to bind prompts to models.
## OpenRouter Reasoning Support | 2026-02-01
Added support for `x-ai/grok-4.1-fast` reasoning parameter and `reasoning_details` persistence.
- Updated `OpenRouterModel` to inject `extra_body` for reasoning-enabled models.
- Implemented serialization/deserialization of `reasoning_details` into ADK `Content` objects using `inline_data` parts.
- Added regression tests for reasoning parameter and persistence.

## Langfuse Connectivity Check Fix | 2026-02-05
Improved the Langfuse availability check in `sdaa/src/core/instrumentation.py`.
- Changed the connectivity check to target `/api/public/health` instead of the root path to ensure the service is actually responsive.
- Added `raise_for_status()` to treat HTTP errors (like 404/500) as unreachability.
- This prevents `OTLPSpanExporter` from being initialized when the host is reachable but not functioning correctly (or hanging on specific endpoints), resolving `ReadTimeout` errors during execution.

## Synthesis Prompt Langfuse Migration | 2026-02-05
Migrated the hardcoded report synthesis prompt in `coordinator.py` to Langfuse, enabling dynamic updates to the final report structure without code changes.

## Observability Fixes (LangSmith & Langfuse) | 2026-02-05
Fixed regression where LangSmith traces were missing by adding manual span generation to `OpenRouterModel`.
Fixed Langfuse Linked Generation by ensuring `InstrumentedGemini` and `OpenRouterModel` reliably attach `langfuse.prompt` attributes to generation spans.
