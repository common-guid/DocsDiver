# Project Progress

## Phase 5 QC & Wrap-Up | 2026-01-28
Completed implementation of DocsDiver-Crew across all phases: custom file tools, Librarian ToC generation, hierarchical CrewAI agents/tasks, CLI orchestration, and QC testing strategy. Documentation was consolidated with a comprehensive README.
IMPLEMENTATION_PLAN.md has been completed.

### Next Steps & Continuity
If new features are requested, start a new plan phase and update this log accordingly.
## Phase 6 Configurable Models | 2026-01-28
Added per-agent model configuration via `config.yaml` with environment variable overrides, and wired each agent (Librarian, Supervisor, and workers) to its own model setting.

### Next Steps & Continuity
If model parameters beyond names are needed, extend `config.yaml` and the config loader accordingly.

## Outstanding
None.

## Phase 7 LiteLLM Proxy Deps | 2026-01-28
Installed LiteLLM proxy extras in the project venv to satisfy missing logging/proxy dependencies (fastapi/apscheduler).

### Next Steps & Continuity
If you want this to be persistent across environments, add `litellm[proxy]` to project dependencies.

## Phase 8 Configurable Paths + ToC Skip | 2026-01-28
Added app-level configuration for `docs_dir`, `toc_path`, and `artifacts` with env overrides and project-root resolution. The CLI now skips the Librarian when the configured ToC exists, the ToC generator writes to the configured path, and reports are saved under the artifacts directory. README and integration tests were updated accordingly.

### Next Steps & Continuity
If desired, run the integration test to validate the new paths and update `.gitignore` to exclude artifacts.

## Phase 9 Observability: LangSmith + Langfuse | 2026-01-29
Integrated OpenTelemetry observability via OpenLit, exporting shared traces to Langfuse and LangSmith, and applied the `crewai_docsdiver` label/tag. Added dependencies, bootstrap logic, and documentation.

### Next Steps & Continuity
Integration tests passed; OTEL export 404s were addressed in Phase 10. If desired, investigate tracer provider override warnings to reduce noisy logs.

## Phase 10 Observability Fix: Langfuse + LangSmith OTLP Endpoints | 2026-01-29
Resolved OTEL exporter 404s by normalizing the Langfuse OTLP base endpoint (OpenTelemetry HTTP exporters append `/v1/traces`) and switching LangSmith export to the official `langsmith[otel]` span processor so it targets `/otel/v1/traces` and honors `LANGSMITH_PROJECT`.

### Next Steps & Continuity
Run `uv run python src/main.py` and confirm new traces appear in both Langfuse (tagged `crewai_docsdiver`) and LangSmith (under `LANGSMITH_PROJECT`). If spans are still missing, investigate the OpenLit `litellm` instrumentation warning and confirm the Langfuse server is reachable from this machine.
