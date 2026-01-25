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
