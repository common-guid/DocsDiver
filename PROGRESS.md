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

### Next Steps & Continuity
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

## Phase: OpenRouter Tool Support Implementation | 2026-01-30
Resolved the issue where agents running on OpenRouter were unable to call tools, preventing artifact generation.

### Tasks Completed
- [x] Diagnosed that `OpenRouterModel` lacked tool conversion and handling logic.
- [x] Implemented `_convert_tools` and `_convert_schema` in `sdaa/src/utils/openrouter_model.py` to map Google GenAI tools to OpenAI format.
- [x] Updated `generate_content_async` in `sdaa/src/utils/openrouter_model.py` to pass tools to the API and parse tool calls from the response.
- [x] Updated `sdaa/src/utils/mock_model.py` to support debugging tool structures.
- [x] Verified the fix using mock simulation and debugging logs.

### Next Steps & Continuity
- Run a full audit with `python main.py -m openrouter` to confirm all artifacts (permissions, constraints, boundaries, and final report) are correctly generated in the `output` directory. [x] (Verified via logs showing successful multi-turn tool execution)

## Phase: Gemini Role Error Fix | 2026-01-31
Resolved `400 INVALID_ARGUMENT` error when running map maker with Gemini by adding explicit role assignment.

### Tasks Completed
- [x] Updating `sdaa/src/core/map_maker.py` to add `role="user"` to the `LlmRequest` content construction.
- [x] Verified fix by generating ToC with Gemini without errors.
- [x] Verified no regression for OpenRouter execution.

### Next Steps & Continuity
- Proceed with full audit test using Gemini to ensure other agents function correctly.

## Phase: Path Access Error Fix | 2026-01-31
Resolved `Access denied` errors where agents attempted to follow broken relative links in documentation.

### Tasks Completed
- [x] Identified that `workspace-settings.md` contained links to files outside the documentation root (e.g., `../administration/workspace_settings/overview.md`).
- [x] Updated `sdaa/src/agents/workers.py` to strictly instruct `permissions`, `constraints`, and `boundaries` agents via system prompts to **only** access files explicitly listed in `ToC.json` and ignore other paths.
- [x] Verified fix by running pre-chat audit; agents successfully ignored valid-looking but out-of-bounds links.

### Next Steps & Continuity
- Monitor for any other hallucinated paths or valid relative links that *should* be followed but aren't (though ToC-only approach is safer).

## Phase: End-to-End Gemini Validation | 2026-01-31
Completed full end-to-end validation of the audit pipeline using the Gemini provider.

### Tasks Completed
- [x] Successfully ran end-to-end tests (excluding interactive chat) with `python main.py -m gemini`.
- [x] Verified that all agent artifacts and the final `Security_Threat_Model.md` report are generated correctly and stored in the `output/reports` directory (run5 in ../test-runs directory).

### Next Steps & Continuity
- **Prompt Improvement**: Refine agent system instructions to increase the depth of analysis and improve report formatting.

## Phase: Operation Optimization | 2026-02-01
Optimized pre-chat audit to skip redundant work and reuse existing artifacts.

### Tasks Completed
- [x] Implemented `ArtifactLoaderModel` to simulate agent execution using existing artifact content.
- [x] Added `--coordinator-only` CLI flag to `main.py` to bypass Map Maker and Worker execution.
- [x] Updated `build_prechat_audit_agent` to check for existing artifacts and skip worker execution if found.
- [x] Patched `MockModel` to include IDs in function calls, resolving verification errors.
- [x] Verified optimization flow using `mock` provider.

### Next Steps & Continuity
- Ensure developers use `--coordinator-only` when iterating on the synthesizer prompt without re-running workers.

