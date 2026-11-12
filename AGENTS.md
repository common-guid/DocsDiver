# AGENTS.md

## Project context

DocsDiver (SDAA) is a Google ADK Python CLI that audits Markdown documentation and generates specialist findings plus a security threat model/test plan.

- Read `archive/PROGRESS.md` at session start and the active plan in `docs/plans/` before implementation. Record completed phases and next steps in the progress file; log other completed features/fixes in `LOG_BOOK.md`.
- `README.md` covers usage; `docs/` covers architecture, configuration, extension, and observability. Verify historical descriptions against source. `ROADMAP.md` describes proposals; `archive/IMPLEMENTATION_PLAN.md` is partly stale.

## Development commands

Run from the repository root; relative corpus/output paths depend on the working directory. Use a virtual environment outside containers.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
# If .env does not already exist:
cp -n .env.example .env
```

`requirements.txt` declares dependencies; `requirements.lock` pins them. Regenerate with `uv pip compile requirements.txt -o requirements.lock --python .venv/bin/python`. No build, lint, formatter, or type-check workflow is configured; `scripts/check_types*.py` only inspect SDK types.

### Run the CLI

```bash
python main.py                                  # Interactive; defaults to OpenRouter
python main.py -m gemini                        # Use Gemini for all agents
python main.py -m openrouter --headless --no-rich
python main.py -m mock --toc-only --no-rich      # Index with a local mock model
python main.py --coordinator-only --headless --no-rich
```

- Configure paths, per-agent models, and prompt bindings in `sdaa/config/config.yaml`. `--docs-root`/`--output-dir` override the two paths for one run; given either flag, a missing docs root, a non-directory output path or an output directory inside the docs root exits 2. `.env` supplies provider and Langfuse credentials; `OPENROUTER_API_KEY`/`GEMINI_API_KEY` accept comma-separated keys for HTTP 429 rotation.
- `--headless` requires a valid ToC, three nonempty worker artifacts, and a nonempty report; `SKIPPED:` placeholders are invalid. It labels outputs `reused`/`generated`. Failures exit 1; conflicting flags exit 2. Success does not establish freshness or quality.
- `--skip-map-maker` requires a valid existing ToC. `--coordinator-only` additionally requires valid worker artifacts and reruns synthesis without worker LLM calls.
- `--refresh-toc` rebuilds indexing and the audit; `--refresh-audit` reruns workers/synthesis. Replaced outputs become `<name>.prev`. Refresh-ToC conflicts with skip-map-maker/coordinator-only; refresh-audit conflicts with coordinator-only/toc-only.
- Mock mode replaces generation, **not Langfuse prompt retrieval**. Full offline audits need prompt stubs; see the headless tests.

### Tests and syntax checks

Use `python -m pytest tests ...` to preserve root imports and avoid collecting diagnostic scripts. **Run the full suite in a disposable copy:** reporting tests delete `output/`, and Map Maker tests remove the ToC. Tests assume the default YAML and `docs-for-testing/` corpus.

With `.venv` populated, run the suite without touching local outputs or copying the repository's `.env`:

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

Focused checks (no repository-output deletion):

```bash
python -m pytest tests/test_main_headless.py -q
python -m pytest tests/test_main_headless.py::test_headless_mock_audit_writes_all_outputs -q
python -m compileall -q main.py sdaa tests scripts
```

`tests/conftest.py` supplies dummy credentials/tracing settings. Headless tests stub prompts and isolate outputs with `tmp_path`.

Live diagnostics: `python scripts/validate_connections.py`, `python scripts/validate_langfuse_conn.py`, and `python scripts/test_langsmith_tracing.py`.

## Mandatory Task Logging Protocol

After completing any code modification, bug fix, refactoring, or feature implementation, you **MUST** execute the `dev-logbook` script as your final action before marking a task complete or providing your final response.

### Execution Command
Run the script using `run_command` (or your shell execution tool):
```bash
bash .agents/skills/dev-logbook/scripts/log.sh "<Title Change of>" "<Brief and changed of summary was what why>"
```

### Protocol Rules & Constraints

Always Use the Script: Never edit LOGBOOK.md directly using text editing tools (write_to_file, replace_file_content, etc.). Direct edits bypass timestamping, branch detection, and formatting standardization.
Timing: Run the logging command immediately after verifying your changes pass build/test checks, but before concluding your turn.

### Log Content Quality:

Title: A concise headline describing the work (e.g., "Fix JWT expiration edge case" or "Add user profile avatar upload").
Summary: 1–2 sentences explaining why the change was necessary and what core logic was updated.

## Vault inbox (CoS_brain)

Hermes owns this project's `tasks.md`, `project.md`, `worklog.md`, and checkboxes. You do not edit those files. You do not run `task_ops.py`. You do not check a box.

When the operator wants this session recorded in the vault, create one new file. Do not append to an old drop. Do not edit a file after you create it. A correction is a new file.

Drop path:

`/home/guid/CoS_brain/projects/Doc_Analysis_Agent/reports/inbox/YYYY-MM-DDTHHMMSSZ-<slug>.md`

Vault root on the laptop, squawk, and serval: `/home/guid/CoS_brain`.
This project's vault directory: `projects/Doc_Analysis_Agent`.

Use UTC (`date -u +%Y-%m-%dT%H%M%SZ`). Do not reuse a filename. If `reports/inbox/` is missing, stop. Do not create the directory. Say that the inbox is missing.

```yaml
---
type: agent-report
status: staged
project: doc_analysis_agent
agent: <your-name>
---
```

Body: one verb per line. No status essay.

- `ADD:` imperative title — one sentence of scope
- `DONE:` title — commit, command, or test output you checked. A DONE line with no evidence is incomplete.
- `BLOCKED:` title — the exact blocker
- `DOC:` repo or vault path — one sentence. Do not create a vault note. Put the repo path on the DOC line.
- `NOTE:` one sentence for the worklog. Not a new task.

A DONE line is a claim. Hermes checks the box after the evidence matches.

Do not write `project.md`, `tasks.md`, `worklog.md`, `tasks/`, `.checkpoints/`, `01_Executive/`, `03_Dashboards/`, or another project. Do not write `projects_wiki`. No secrets.

Ignore `README.md` in the inbox. Do not edit it.

## Architecture

Module paths below are relative to `sdaa/src/`; `main.py` is at the repository root.

`main.py` orchestrates three stages, ADK runners, shared in-memory sessions/memory, and `ui/rich_chat.py`:

1. **Index:** `core/map_maker.py` reads corpus Markdown through `tools/file_ops.py`, summarizes whole files sequentially, and writes `output/ToC.json`. Each `files` entry has a corpus-relative `path`, `summary`, and exactly three `tags`.
2. **Pre-chat audit:** An ADK `SequentialAgent` runs permissions → constraints → boundaries → synthesis. Workers in `agents/workers.py` set `permissions_report`, `constraints_report`, and `boundaries_report` state keys.
3. **Chat:** A separate coordinator in `agents/coordinator.py` delegates to worker sub-agents. Sessions do not persist across processes.

Valid outputs are reused unless refreshed; `core/output_validation.py` defines validity, not freshness. Existing worker artifacts use `utils/artifact_loader_model.py` to replay reporting-tool calls. Its final state contains an acknowledgement, so synthesis reads artifact bodies from disk. Changed documents/models/prompts do not automatically invalidate outputs.

### Configuration and outputs

`core/config_loader.py` loads `.env` and YAML as an import-time singleton. Defaults audit `docs-for-testing/`, not the developer guides in `docs/`, and write under `output/`.

`tools/reporting.py` accepts Markdown strings, not its declared Pydantic finding classes:

- Workers write `artifacts/{permissions,constraints,boundaries}_agent.md`.
- `generate_final_report(report_content)` writes `reports/Security_Threat_Model.md`.
- Directory names resolve under `system.output_dir`; tools can return error strings without raising.

`tools/file_ops.py` authorizes every path through `resolve_corpus_path`: it must resolve inside `system.docs_root` with no symlink. Listing is sorted and skips symlinks with a warning. Only the bare configured ToC filename is served from output; it is not a general artifact reader. Tools return an access-denied string (and log a warning); internal callers (Map Maker, `toc_problems`) raise.

### Models and prompts

`core/model_factory.py` selects `agents.<agent_name>.<provider>` and returns an ADK `BaseLlm` adapter or mock. Provider-level YAML `model_name`, `system.batch_size`, and `notebook_dir` are not active pipeline controls.

`utils/openrouter_model.py` translates ADK messages/tool schemas to OpenAI-compatible requests; preserve tool-call IDs, schema `items`, reasoning round-trips, and empty-string assistant content for tool calls. Provider failures must propagate. `utils/instrumented_gemini.py` wraps Gemini by composition; both adapters use cached provider key rotators.

`utils/prompt_manager.py` fetches Langfuse instructions; retrieval failure yields error-text instructions, not a usable local fallback. Bindings come from YAML except `report-synthesizer`/`production`, hardcoded in the coordinator. Preserve brace sanitization/escaping: ADK interprets braces as state substitutions.

`core/instrumentation.py` shares OpenTelemetry tracing across LangSmith/Langfuse. Tracing and prompt retrieval are separate; disabling observability does not supply prompts.

Adding a worker requires aligning its factory/state key, reporting tool, YAML bindings, both agent trees, output validation/replay mapping, and remote coordinator/synthesis prompts.

## Upstream documentation

Prefer the link indexes in `docs/llms-txt/`: `ADK-llms.txt` for ADK, `openrouter-llms.txt` for provider integration, and `langfuse-llms.txt` for prompts/tracing. Open their linked pages for detail; root `llms.txt` is older. These indexes track newer upstream releases: installed source at `requirements.lock` versions is authoritative when APIs differ.
