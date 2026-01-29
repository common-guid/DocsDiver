## Comprehensive README | 2026-01-28
Created a full project README covering architecture, setup/usage, extensibility, testing, and roadmap so new contributors can get started quickly.

## Per-agent model configuration | 2026-01-28
Added `config.yaml` with environment-variable overrides and wired each agent to its own model setting via a shared config loader.

## LiteLLM proxy dependency fix | 2026-01-28
Installed LiteLLM proxy extras in the project venv to resolve missing proxy logging dependencies (fastapi/apscheduler).

## Configurable paths + ToC skip | 2026-01-28
Added app configuration for docs input, ToC output, and artifacts output (with env overrides), and made the Librarian phase skip when a ToC already exists.

## LangSmith + Langfuse observability | 2026-01-29
Added OpenTelemetry-based observability with OpenLit, exporting shared traces to Langfuse and LangSmith and tagging runs with `crewai_docsdiver`.

## Import error fix for end-to-end run | 2026-01-29
Added a bootstrap to load `.env` and set a default `LITELLM_LOG` plus ensured the project root is on `sys.path` when running scripts directly, fixing the import error during `uv run python src/main.py`.

## Fix OTEL trace export to Langfuse/LangSmith | 2026-01-29
Fixed Langfuse OTLP endpoint normalization to prevent `/v1/traces` duplication and updated LangSmith OTEL exporting to use the built-in `OtelSpanProcessor` so traces are sent to `/otel/v1/traces` under the configured project.
