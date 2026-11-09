# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project context and continuity

DocsDiver, also called SDAA (Security Documentation Analysis Agent), is a Python CLI built on Google ADK. It audits a Markdown documentation corpus with specialist LLM agents and produces worker findings and a synthesized security threat model/test plan.

- Read `PROGRESS.md` at session start and consult `IMPLEMENTATION_PLAN.md` before planned implementation work. After completing a plan phase, record its outcome and next steps in `PROGRESS.md`.
- Append a dated, short entry to `LOG_BOOK.md` for completed features or fixes outside the implementation plan.
- `README.md` describes usage; `docs/` contains architecture, configuration, extension, and observability guides. Some descriptions are historical: check the source before relying on them. `ROADMAP.md` distinguishes current limitations from proposed capabilities; roadmap features are not necessarily implemented.
- `llms.txt` links to Google ADK documentation.

## Development commands

Run from the repository root: corpus and output paths resolve relative to the working directory. Use a virtual environment when running Python outside a container.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
# If .env does not already exist:
cp -n .env.example .env
```

`requirements.txt` declares direct dependencies; `requirements.lock` pins the resolved environment. Its header records the regeneration command: `uv pip compile requirements.txt -o requirements.lock --python .venv/bin/python`. There is no package/build step or configured lint, formatter, or type-check command. The `scripts/check_types*.py` files inspect ADK SDK types; they are not static type checks.

### Run the CLI

```bash
python main.py                                  # Interactive; defaults to OpenRouter
python main.py -m gemini                        # Use Gemini for all agents
python main.py -m openrouter --headless --no-rich
python main.py -m mock --toc-only --no-rich      # Index with a local mock model
python main.py --skip-map-maker                 # Reuse the configured ToC
python main.py --coordinator-only --headless --no-rich
```

- Set `OPENROUTER_API_KEY` or `GEMINI_API_KEY` for the selected provider. Both accept comma-separated keys for bounded rotation on HTTP 429.
- Configure corpus, outputs, per-agent models, and prompt bindings in `sdaa/config/config.yaml`; these do not have CLI path overrides.
- `--headless` exits before chat, fails on propagated audit exceptions or missing expected worker/report files, and otherwise returns success. It is not a content-quality or freshness check.
- `--coordinator-only` skips indexing and worker LLM calls, but still runs worker artifact-loader agents before synthesis. Missing artifacts become `SKIPPED` placeholders.
- Mock mode replaces model generation, **not prompt retrieval**. A complete mock audit still needs appropriate prompts or test stubs; the standalone mock CLI is not a reliable offline end-to-end smoke test.

### Tests and syntax checks

Tests use pytest, pytest-asyncio, and unittest-style classes collected by pytest. Prefer `python -m pytest tests ...` over bare `pytest` so the root is importable and ad-hoc scripts under `scripts/` are not collected.

**Run the full suite in a disposable copy.** `tests/test_reporting_tools.py` deletes the working directory's `output/` in setup; `tests/test_map_maker.py` removes the configured ToC. Several tests depend on the default YAML settings and `docs-for-testing/` corpus.

From the repository root, with `.venv` already populated:

```bash
repo_root="$PWD"
test_root="$(mktemp -d)"
tar --exclude='./.git' --exclude='./.venv' --exclude='./.gemini' \
    --exclude='./.env' --exclude='./output' -cf - . |
    tar -xf - -C "$test_root"
(
    cd "$test_root" &&
    LANGSMITH_API_KEY= LANGFUSE_PUBLIC_KEY= LANGFUSE_SECRET_KEY= \
        "$repo_root/.venv/bin/python" -m pytest tests -q
)
```

For focused checks that do not delete repository outputs:

```bash
python -m pytest tests/test_main_headless.py -q
python -m pytest tests/test_main_headless.py::test_headless_mock_audit_writes_all_outputs -q
python -m pytest tests/test_openrouter_payload.py -q
python -m compileall -q main.py sdaa tests scripts
```

`tests/conftest.py` supplies dummy OpenRouter/OpenAI credentials and adjusts tracing settings. Headless tests additionally stub Langfuse prompts and redirect outputs with `tmp_path`; retain that isolation when extending them.

Opt-in live diagnostics (not offline tests): `python scripts/validate_connections.py` checks both providers, `python scripts/validate_langfuse_conn.py` emits a test span, and `python scripts/test_langsmith_tracing.py` exercises tracing.

## Architecture and cross-module contracts

Module paths below are relative to `sdaa/src/` unless otherwise specified.

### Execution pipeline and reuse

The root `main.py` owns orchestration, ADK runners, in-memory sessions/memory, and the Rich/plain-text interface (`ui/rich_chat.py`). Its three stages use separate pre-chat and interactive agent trees:

1. **Indexing:** `core/map_maker.py` lists Markdown through `tools/file_ops.py`, reads whole files, and calls a model sequentially for each summary/tag set. It writes `output/ToC.json` as `{"files": [{"path": "...", "summary": "...", "tags": ["...", "...", "..."]}]}`. Paths are relative to the corpus root; tags are normalized to exactly three. The indexing prompt is local to Map Maker.
2. **Pre-chat audit:** `build_prechat_audit_agent()` constructs an ADK `SequentialAgent`: permissions → constraints → boundaries → synthesizer. Worker `output_key` values populate session state as `permissions_report`, `constraints_report`, and `boundaries_report`; the synthesizer compiles these into its prompt.
3. **Interactive review:** A separate coordinator (`agents/coordinator.py`) has worker `sub_agents` for delegation and tools for reading documentation and writing the final report. It shares the session/memory services with the pre-chat runner; sessions do not persist across processes.

The CLI and Map Maker skip indexing whenever the ToC exists. Pre-chat is skipped when all three worker files and the final report exist, unless `--coordinator-only` forces synthesis. During pre-chat, existing worker files select `utils/artifact_loader_model.py` instead of a provider model: it emits a reporting-tool call and then a completion acknowledgement. That acknowledgement, not the artifact body, can become the worker's session-state output. Reuse is existence-based, with no automatic invalidation when documents, models, or prompts change; use a separate output directory for a clean experiment rather than deleting user artifacts.

### Tools, outputs, and configuration

`core/config_loader.py` is an import-time singleton and loads `.env`. Its directory helpers create the configured paths. Defaults in the checked-in YAML audit `docs-for-testing/` (fixture input, not the developer guides in `docs/`) and write under `output/`.

`tools/reporting.py` accepts Markdown strings, not the Pydantic finding classes declared alongside it. The worker contract ties together agent name, session-state key, tool argument, and artifact:

- Permissions: `permissions_report` → `report_permissions_matrix(findings)` → `artifacts/permissions_agent.md`.
- Constraints: `constraints_report` → `report_invariance_findings(findings)` → `artifacts/constraints_agent.md`.
- Boundaries: `boundaries_report` → `report_boundary_analysis(boundaries_markdown)` → `artifacts/boundaries_agent.md`.
- Synthesis: `generate_final_report(report_content)` → `reports/Security_Threat_Model.md`.

These directories are resolved under `system.output_dir` using the configured reports/artifacts directory names. Reporting tools return status/error strings; a tool failure does not necessarily raise.

`tools/file_ops.py` resolves normal reads relative to `system.docs_root`, and special-cases the configured ToC basename to read from `output_dir`. It is not a general output-artifact reader. Its current string-prefix containment check does not securely handle sibling-prefix paths or symlinks; do not assume the sandboxing described in older guides is enforced.

### Model and prompt boundaries

`core/model_factory.py` selects `agents.<agent_name>.<provider>` and returns an ADK `BaseLlm`: `InstrumentedGemini`, `OpenRouterModel`, or `MockModel`. Model fallback names are hardcoded in the factory; provider-level `model_name` YAML values are not used there. `system.batch_size` and `notebook_dir` are also not implemented pipeline controls on this branch.

`utils/openrouter_model.py` translates ADK/Google GenAI messages and tool schemas to OpenAI-compatible requests. Preserve provider tool-call IDs, array-schema `items`, model-role responses, and empty-string assistant content for tool calls. Grok reasoning is round-tripped via `inline_data` using `application/x-reasoning-details`. Provider exceptions must propagate, not become report text. `InstrumentedGemini` wraps an inner Gemini client by composition; `core/key_rotator.py` caches rotators per provider.

Workers and both coordinators obtain instructions through the lazy singleton in `utils/prompt_manager.py`. Langfuse names are `permissions-agent`, `negative-constraints-agent`, `security-boundaries-agent`, `coordinator-agent`, and `report-synthesizer`, normally at label `production`. The synthesizer name/label are hardcoded in `coordinator.py`; other bindings come from YAML. Retrieval failure currently produces error-text instructions, not usable local fallback prompts.

ADK interprets braces as state substitutions. Agent factories sanitize or escape braces in fetched instructions; synthesis sanitizes injected report bodies before Langfuse compilation. Preserve this distinction when changing prompt assembly.

`core/instrumentation.py` sets up shared OpenTelemetry tracing for LangSmith and Langfuse, with a Langfuse health check before OTLP export. Prompt objects are separately attached to model generation spans. Disabling observability does not provide missing agent prompts.

Adding a worker therefore requires coordinated updates to its factory and state key, reporting tool/file, YAML model/prompt binding, interactive coordinator delegation, pre-chat ordering/replay mapping and expected-output list, plus the remote synthesis/coordinator prompts—not just a new agent class.
