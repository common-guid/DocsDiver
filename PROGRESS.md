# Project Progress

## Phase: Bug Fixes & Improvements | 2026-01-24
Resolved compatibility issues with Python 3.14 and validated the application flow.

### Tasks Completed
- [x] Fixed `langfuse` import crash on Python 3.14 by adding a fallback mechanism in `sdaa/src/core/instrumentation.py`.
- [x] Verified the fix with regression tests in `tests/test_instrumentation.py`.
- [x] Fixed `sdaa/src/core/map_maker.py` which was hardcoding `mock-model`, preventing use of real Gemini models.
- [x] Updated `sdaa/config/config.yaml` to use `gemini-2.5-pro` as the default model, matching available models in the environment.
- [x] Validated application startup and API connectivity by running `main.py -m gemini`.
- [x] Created `scripts/validate_connections.py` to allow users to verify API connectivity (Gemini/OpenRouter).
- [x] Extended `sdaa/src/core/map_maker.py` and `ToC.json` generation to include three keyword tags per file, and updated `tests/test_map_maker.py` to cover the new format.
- [x] Updated worker agent prompts in `sdaa/src/agents/workers.py` so agents explicitly use ToC `tags` when selecting relevant documentation files.

### Next Steps & Continuity
- Verify successful generation of `ToC.json` and full audit workflow.
- Address rate limiting issues if they persist during full audit.

## Phase: Map Maker Output Directory & Skip Controls | 2026-01-25
Implemented configurable output routing for Map Maker and reporting, plus new CLI flags for controlling ToC generation.

### Tasks Completed
- [x] Added `system.output_dir` to `sdaa/config/config.yaml` and implemented `ConfigLoader.get_output_dir` to resolve and create the output directory.
- [x] Updated `generate_toc` in `sdaa/src/core/map_maker.py` to write `ToC.json` to `system.output_dir` with a skip guard when the file already exists.
- [x] Updated `generate_final_report` in `sdaa/src/tools/reporting.py` so the final `Security_Threat_Model.md` report is saved under `system.output_dir`.
- [x] Extended `main.py` CLI with `--skip-map-maker` and `--toc-only` flags and wired Phase 1 to respect existing ToC files and the new skip behavior.
- [x] Updated `tests/test_map_maker.py` so it uses the resolved output directory and cleans up any pre-existing `ToC.json` before running, keeping coverage for summary and tag structure.
- [x] Updated `README.md` configuration and data-flow documentation to describe `system.output_dir` and where outputs are written.
-### Next Steps & Continuity
- Exercise the CLI end-to-end with a non-default `system.output_dir` (for example, `./artifacts`) to confirm all outputs route correctly.

## Phase: Documentation Update (Output Dir & Skip ToC) | 2026-01-25
Updated README usage and configuration notes to document the output directory and the CLI flag for skipping Map Maker.

### Tasks Completed
- [x] Documented `--skip-map-maker` usage for reusing an existing `ToC.json` in `system.output_dir`.
- [x] Clarified README configuration guidance to include `system.output_dir`.
- [x] Added README usage notes for `--toc-only` to generate ToC and exit.

### Next Steps & Continuity
- Review README for any additional CLI flags that should be documented.

## Phase: Observability Merge Fix | 2026-01-26
Restored dual-platform tracing after merging Langfuse and LangSmith branches.

### Tasks Completed
- [x] Consolidated Langfuse and LangSmith setup into a single `setup_instrumentation` and attached both exporters to the same OpenTelemetry provider.
- [x] Removed the duplicate `setup_instrumentation` definition that was overriding Langfuse configuration.

### Next Steps & Continuity
- If needed, run `scripts/validate_langfuse_conn.py` and `scripts/test_langsmith_tracing.py` to confirm traces arrive in both platforms.

## Phase: Environment Dependency Fix (python-dotenv) | 2026-01-28
Resolved missing dependency errors when running the CLI by installing project requirements in a local virtual environment.

### Tasks Completed
- [x] Created `venv` in the project root and installed `requirements.txt` to provide `python-dotenv`.

### Next Steps & Continuity
- Re-run the CLI using `venv/bin/python main.py -m gemini` (or activate the venv) to confirm startup.

## Phase: Gemini non-text warning suppression | 2026-01-28
Addressed a noisy warning emitted by the google-genai SDK when tool calls return non-text parts during streaming.

### Tasks Completed
- [x] Added a targeted logging filter to suppress the specific "non-text parts in the response" warning during CLI runs.

### Next Steps & Continuity
- Re-run the CLI to confirm the warning no longer appears while tool calls continue to function.

## Phase: Pre-chat Sequential Audit Artifacts | 2026-01-28
Implemented a deterministic pre-chat audit that runs workers sequentially, captures their outputs in session state, and synthesizes the final report only when outputs are missing.

### Tasks Completed
- [x] Added output capture for worker agents and strengthened prompts to return the same markdown passed to reporting tools.
- [x] Added a synthesis-only coordinator to generate the final report from worker outputs in session state.
- [x] Added pre-chat output gating and a sequential pre-chat audit pipeline that reuses the same session before the first user prompt.
- [x] Added tests for pre-chat output gating and sequential agent ordering; updated CLI tests to reflect the new gating behavior.

### Next Steps & Continuity
- Run the full CLI with real models to confirm artifacts and report are generated sequentially when outputs are missing.

## Phase: Boundary reporting schema fix | 2026-01-28
Aligned the boundary reporting tool with Gemini tool schema requirements by accepting markdown-only input.

### Tasks Completed
- [x] Simplified `report_boundary_analysis` to accept only markdown strings and removed schema paths that caused invalid tool payloads.
- [x] Updated reporting tool tests to reflect the markdown-only boundary reporting behavior.

### Next Steps & Continuity
- Re-run the CLI with Gemini to confirm the boundary artifact is created without tool schema errors.

## Phase: ToC.json accessibility fix | 2026-01-30
Ensured agents can read the generated ToC.json from the configured output directory during pre-chat and interactive audits.

### Tasks Completed
- [x] Updated `sdaa/src/tools/file_ops.py` so `read_file("ToC.json")` resolves to the ToC in `system.output_dir` instead of the docs root.
- [x] Verified configuration and main CLI flow to confirm ToC generation still targets the output directory and agents continue to rely on `read_file` for access.

### Next Steps & Continuity
- Re-run the CLI with a full pre-chat audit to confirm the recommendation about missing ToC.json no longer appears and workers successfully use the table of contents.

## Phase: Config Refactor & Model Factory | 2025-05-15
Refactored configuration and model instantiation to support per-agent provider selection via CLI flag.

### Tasks Completed
- [x] Created `sdaa/src/core/model_factory.py` to instantiate `Gemini` or `OpenRouterModel` based on agent-specific config.
- [x] Updated `sdaa/config/config.yaml` to define model names per provider (openrouter/gemini) for each agent.
- [x] Refactored `sdaa/src/agents/coordinator.py` and `main.py` to use `model_factory` and accept a `provider` argument instead of a single model instance.
- [x] Created `tests/test_factory_and_integration.py` to verify the factory logic and integration with `main.py` and coordinator.

### Test Results
Created `tests/test_factory_and_integration.py` which mocks `config_loader` and verifies that `get_model_for_agent` correctly instantiates `Gemini` or `OpenRouterModel` with the configured model names. Also verifies that `main.py` and `coordinator.py` use the factory for all agents.

Output:
```
Ran 6 tests in 0.788s

OK
```

### Next Steps & Continuity
- Verify end-to-end execution with different config values.

## Phase: Artifact Generation Verification | 2025-05-15
Verified and tested the artifact generation workflow for Map Maker and Pre-chat Audit agents.

### Tasks Completed
- [x] Updated `sdaa/src/utils/mock_model.py` to support simulated function calls for reporting tools, allowing comprehensive testing of the agent workflow.
- [x] Created `tests/test_artifact_generation.py` to verify that `ToC.json`, worker artifacts, and the final report are correctly generated in the configured output directories.
- [x] Verified that `ToC.json` is written to `output/ToC.json`.
- [x] Verified that worker artifacts are written to `output/artifacts/`.
- [x] Verified that the final report is written to `output/reports/`.

### Test Results
Created `tests/test_artifact_generation.py` which runs a full integration test of the Map Maker and Pre-chat Audit agents using `MockModel`. The test verifies the existence and content of all expected output files.

Output:
```
tests/test_artifact_generation.py .                                      [100%]
1 passed, 1 warning in 3.89s
```

### Next Steps & Continuity
- Submit changes for review.
