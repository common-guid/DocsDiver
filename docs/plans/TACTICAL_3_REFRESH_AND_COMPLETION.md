# Tactical Feature 3: Explicit Refresh and Trustworthy Completion — Implementation Plan
Status: implemented (see the PR for this branch) · Target: ROADMAP release 0.3 · Effort 2/5 Baseline: `ADK_master` at `37113a0`. The roadmap cites `accbe0a`; the only commit since is documentation (`git diff --stat accbe0a HEAD -- '*.py'` is empty), so every code reference below is valid for both.
## 0. Baseline verification
- The repository `.venv` cannot collect tests: `google.adk` and other runtime dependencies are missing, giving 12 collection errors. This matches ROADMAP §1.
  
- I built a clean venv from `requirements.lock` with `uv venv --python 3.14` and `uv pip install -r requirements.lock`. The lock pins `google-adk==2.14.0` and `google-genai==2.34.0`.
  
- Running the full suite in a disposable copy (AGENTS.md procedure) gave **52 passed**. The baseline is reproduced.
  
- Empirical checks were run in that copy with scratch scripts and are cited as **[repro]** below. They:
  
  - drove `build_prechat_audit_agent("mock")` through an ADK `Runner` and inspected session state;
    
  - made an ADK tool raise an exception.
    
## 1. Findings: verified behavior vs. roadmap claims
| # | Topic | Verified current behavior | Roadmap claim | Verdict |
|---|---|---|---|---|
| F1 | ToC reuse | `main.py:139-142`: Map Maker is skipped if `--skip-map-maker`/`--coordinator-only` is set, or if the ToC file exists. `generate_toc` has its own existence guard (`map_maker.py:141-143`). Nothing parses the ToC. | Existence-based reuse | Correct |
| F2 | Worker reuse | `main.py:72`: if the artifact file exists, the worker's model becomes `ArtifactLoaderModel`. No content check. | Existence-based | Correct |
| F3 | Pre-chat skip | `main.py:199-200`: pre-chat runs if any of the 4 outputs is missing, or if `--coordinator-only` is set. Otherwise it is skipped (`main.py:227-228`). | Existence-based | Correct |
| F4 | Headless success | `main.py:230-237` checks only that the 4 pre-chat files **exist**. The ToC is never checked. `--skip-map-maker --headless` with no ToC and existing outputs exits 0. | "Does not consistently validate the ToC, nonempty content, or placeholders" | Correct. README:135 ("exit 1 if the ToC could not be generated") is **stale**: it holds only when `generate_toc` raises, and it rarely does (F7). |
| F5 | Replay state | **[repro]** On replay, `permissions_report`, `constraints_report` and `boundaries_report` each hold `"Artifact loaded and processed via <tool>."`. ADK writes `output_key` from the final text turn (`google/adk/agents/llm_agent.py:1119-1145`), and the loader's second turn is that acknowledgement (`artifact_loader_model.py:35-39`). | Replay reaches synthesis as an acknowledgement | Correct but **incomplete**: see F6 |
| F6 | Fresh-run state | **[repro]** On a fresh mock run, state holds `"Permissions findings recorded and saved to …"`, again not the findings. `MockModel` writes the file directly and returns an acknowledgement (`mock_model.py:95-102`). With live providers, state holds whatever the model says after its tool call, so the content depends on the model. The synthesizer reads only state (`coordinator.py:74-76`). | Not mentioned | **Roadmap gap**: fixing only `ArtifactLoaderModel` would leave fresh runs feeding acknowledgements to synthesis |
| F7 | Map Maker swallowing | (a) `map_maker.py:77-81`: a `ValueError` on read becomes the summary `"Error reading file: …"`. (b) `read_file` *returns* `"Error: File not found: …"` / `"Error reading file: …"` strings (`file_ops.py:41-48`); these are sent to the model as document content. (c) `map_maker.py:147-151`: a `list_files` exception is printed and the function returns with no ToC. `main.py:149` still prints "ToC generation complete". (d) `map_maker.py:153-157`: a `list_files` error string or an empty corpus writes `{"files": []}`. (e) `map_maker.py:174-179`: a write failure is printed and the function returns normally. | "Map Maker failures can be swallowed" | Correct; (b) and (d) were not called out |
| F8 | Reporting swallowing | `reporting.py:45-53`, `61-68`, `76-83`, `91-100`: each tool catches `Exception` and returns an `"Error …"` string to the model. | Correct | Correct. **[repro]** If the tool raises instead, ADK 2.14 propagates the exception out of `Runner.run_async`. It is then caught at `main.py:221-226`, and headless exits 1. Propagation needs no ADK work. |
| F9 | SKIPPED placeholders | `main.py:79-85`: `--coordinator-only` with a missing artifact replays `"SKIPPED: <agent> was skipped because --coordinator-only was specified and no artifact was found."`. **[repro]** The loader *calls the reporting tool*, so the placeholder is **written to disk** as the artifact. Later runs reuse it as a real artifact (F2), and headless exits 0. | "Placeholders can resemble success" | **Worse than stated**: the placeholder persists and poisons later runs |
| F10 | Destructive tests | `tests/test_reporting_tools.py:18-20`: `setup_module` runs `shutil.rmtree("output")` relative to the working directory (ToC, artifacts, reports), then writes 4 files under the configured dirs. `tests/test_map_maker.py:14-15`: `os.remove`s the configured `output/ToC.json`, then writes a mock-model ToC there. All other output-touching tests already use `tmp_path`. | "Move destructive output tests to `tmp_path`" | Correct; exactly these two |
| F11 | Map Maker `force` | Not needed: if `main` moves the old ToC aside before calling `generate_toc`, the existing guard never fires (see D1). | "Add a force option in `map_maker.py`" | Rejected as unnecessary |
| F12 | README / plan drift | README:54 says Phase 1 always generates the ToC; it is actually skipped when the file exists (F1). README:135 is stale (F4). `docs/INTERNALS_AND_DESIGN_PATTERNS.md:47` says the loader writes "the artifact content directly into session state", which is false (F5). `archive/IMPLEMENTATION_PLAN.md:117,195` say the ToC is written to the project root and "regenerates on every run"; both are false. | "Reconcile README" | Also covers the two `docs/` guides |
| F13 | Process docs moved | `PROGRESS.md` and `IMPLEMENTATION_PLAN.md` were moved to `archive/` in `37113a0`, but AGENTS.md still says to read `PROGRESS.md` at the root. | ROADMAP §4 says to update both | See open question Q6 |
| F14 | **OpenRouter + tools is broken on the locked ADK** (outside this feature) | `openrouter_model.py:105` calls `_convert_schema(func.parameters)`. ADK 2.14 emits `parameters_json_schema` and leaves `parameters=None`, so every OpenRouter request that carries tools raises `AttributeError: 'NoneType' object has no attribute 'type'`. `tests/test_main_skip_map_maker.py::test_skip_map_maker_with_existing_toc_still_initializes_agents` hits this and still passes only because interactive mode swallows pre-chat exceptions (`main.py:221-226`). It also patches `app.OpenRouterModel`, which has no effect because the factory imports its own reference (`model_factory.py:5`). | Not mentioned | **Live headless OpenRouter audits with missing artifacts currently exit 1.** Fix separately; see Q7 |

Interaction with the recent merges:

- PR #44 makes provider exceptions raise, and PR #39 retries 429 errors inside `_create_with_rotation`. Both already propagate to `main.py:150` (Map Maker) and `main.py:221` (pre-chat).
  
- This plan adds **no** `try/except` around model calls. It removes swallowing only in local I/O.
  
- It leaves `ArtifactLoaderModel` untouched, including its deterministic tool-call ID (`artifact_loader_model.py:46-50`), which OpenRouter message linking relies on.
  
## 2. Design decisions
### D1. Regenerated outputs are moved aside first; success is decided by validating what is on disk at the end
Rule: any output this run is going to regenerate is first renamed to `<name>.prev` with `os.replace`, which overwrites any older `.prev`. Then:

- an output that fails to regenerate is _missing_, not stale;
  
- a final validation pass decides success.
  

This gives correct freshness for the files that were regenerated without timestamps, hashes or a manifest. It is also the reason Map Maker needs no `force` flag (F11). `.prev` rather than deletion means a refresh that fails mid-run never destroys the user's previous results (see Q1).
### D2. Flag semantics
| Flag | Moves aside (D1) | Effect |
|---|---|---|
| `--refresh-toc` | ToC **and** the 3 worker artifacts and the report | Rebuild the index, then the whole audit. Moving the downstream files aside makes the invalidation durable even with `--toc-only`, so the next run cannot reuse findings built from the old index. |
| `--refresh-audit` | the 3 worker artifacts and the report | Rerun all workers and synthesis. The ToC is reused if valid, and generated if missing or invalid. |

Rejected combinations, each reported through `parser.error(...)`, which exits with **code 2** before any I/O:

- `--refresh-toc` with `--skip-map-maker` or `--coordinator-only`, because both skip Map Maker;
  
- `--refresh-audit` with `--coordinator-only`, because coordinator-only means "reuse the worker artifacts";
  
- `--refresh-audit` with `--toc-only`, because `--toc-only` exits before the audit.
  

Example message: `--refresh-toc cannot be combined with --skip-map-maker`.

Allowed combinations:

- `--refresh-toc --toc-only`;
  
- `--refresh-audit --skip-map-maker`;
  
- both refresh flags together (redundant, because `--refresh-toc` implies an audit refresh).
  

The existing no-op `--skip-map-maker --toc-only` becomes useful: it validates the ToC (see D4).
### D3. What "valid" means
The checks live in new `sdaa/src/core/output_validation.py`. Each check returns a list of human-readable problems; an empty list means valid.

**ToC** — `toc_problems(toc_path) -> list[str]`. A ToC is valid iff:

1. the file exists and is UTF-8 JSON;
  
2. the top level is an object whose `files` value is a **non-empty** list (an empty corpus is an error);
  
3. every entry is an object with:
  

- `path`: a non-empty `str`;
  
- `summary`: a non-empty `str` after `strip()`, not starting with `"Error reading file:"` (this catches ToCs left by the old F7a behavior);
  
- `tags`: a list of exactly 3 non-empty `str`;
  

4. `Path(docs_root, path).resolve()` is an existing regular file and `is_relative_to(Path(docs_root).resolve())`;
  
5. paths are unique.
  

`docs_root` comes from `file_ops._get_docs_root()` (`file_ops.py:5-6`), so tests and Tactical 1 have a single place to redirect it.

Not checked: whether the ToC covers every file currently in the corpus. That is freshness detection and out of scope (see Q3).

**Worker artifact / final report** — `text_output_problems(path) -> list[str]`. Valid iff:

- the path is a regular file;
  
- it decodes as UTF-8;
  
- `content.strip()` is non-empty;
  
- `content.lstrip()` does not start with `SKIPPED_PREFIX = "SKIPPED:"`.
  

The prefix check keeps rejecting placeholders already on users' disks, even though D5 stops producing them.

**Whole audit** — `audit_output_problems() -> list[str]`: the concatenated problems of the 3 artifacts and the report. The module also owns the single list of expected outputs:

- `WORKER_ARTIFACTS = {"permissions_report": "permissions_agent.md", "constraints_report": "constraints_agent.md", "boundaries_report": "boundaries_agent.md"}`;
  
- `REPORT_FILENAME`;
  
- `audit_output_paths() -> list[str]`, which replaces `main._expected_prechat_output_paths` (`main.py:50-58`).
  

`reporting.py` keeps its filename literals; the seam is noted rather than refactored.
### D4. Orchestration flow in `main.py`
```
parse args; reject contradictions (exit 2)
if --refresh-toc: set_aside([toc] + audit_output_paths())
if not (skip_map_maker or coordinator_only) and toc_problems(toc):
    set_aside([toc]); await generate_toc(...)   # any exception → exit 1, all modes
if toc_problems(toc): print problems; exit 1    # all modes, incl. --skip-map-maker/--coordinator-only/--toc-only
if --toc-only: return
... coordinator / session setup (unchanged) ...
if --refresh-audit: set_aside(audit_output_paths())
if --coordinator-only and any worker artifact invalid: print problems; exit 1   # no SKIPPED manufacturing
stale = [p for p in audit_output_paths() if text_output_problems(p)]
if stale or coordinator_only:
    set_aside(stale + [report]); run pre-chat (workers reuse only valid artifacts)
problems = audit_output_problems()
headless: problems → exit 1; else print per-output "reused"/"generated" and exit 0
interactive: problems → print a warning listing them, then enter chat
```

Decisions embedded in this flow:

- **Map Maker failure or an invalid ToC is fatal in every mode.** Today interactive mode continues without a ToC (`main.py:150-154`). Workers would then audit an unindexed corpus, which one code path removes.
  
- **Headless success means** a valid ToC plus 4 valid audit outputs at the end of the run. Reused outputs are still allowed, which keeps today's cost-saving reuse, but they are no longer reused _silently_: the final status line names each output as `reused` or `generated`, and `--refresh-audit` is the documented way to force regeneration.
  
- **When the ToC is regenerated without a refresh flag** (it was missing or invalid), existing valid audit outputs are kept, as they are today, and a warning is printed: `audit outputs predate the new ToC; use --refresh-audit`. See Q2.
  
- **Exit codes:** 0 = valid; 1 = runtime or validation failure (existing meaning); 2 = usage error (argparse convention).
  
### D5. Synthesis reads artifact bodies from disk, not from session state
F5 and F6 show that `output_key` state never reliably holds findings: it gets loader acknowledgements on replay, mock acknowledgements on fresh mock runs, and model-dependent text on live runs. The files written by the reporting tools _are_ the findings. So in `create_coordinator_synthesizer._build_synthesis_prompt` (`coordinator.py:73-83`):

- take each body from `WORKER_ARTIFACTS` via `text_output_problems`, then read the file;
  
- keep the existing `re.sub` brace sanitization (`coordinator.py:74-76`) and the `MISSING: …` fallback (`coordinator.py:78-83`).
  

This is one change at the only consumer, and it fixes fresh, replay and mock runs together. The roadmap item "make the artifact loader preserve the full body" becomes unnecessary: `ArtifactLoaderModel` stays as is. `output_key` stays too, because it is harmless and removing it touches 3 factories. The pre-chat branch also drops its `coordinator_only` parameter and the SKIPPED placeholder (`main.py:78-85`), because D4 has already rejected missing artifacts.
### D6. Failures propagate
- `reporting.py`: delete the 4 `try/except Exception` blocks so `OSError` propagates. ADK carries it out of the runner (F8).
  
- `map_maker.py`:
  
  - delete the `try/except` blocks at `77-81`, `147-151` and `174-179`;
    
  - if `read_file` returns a string starting with `"Error: File not found:"` or `"Error reading file:"` (the exact prefixes at `file_ops.py:42,48`), raise `RuntimeError(f"Map Maker could not read {filepath}: …")`;
    
  - if `list_files` returns an `"Error"` string or no files, raise (`FileNotFoundError` / `ValueError("no Markdown files under <docs_root>")`).
    
- Leave the JSON-decode fallback (`map_maker.py:129-131`) alone: it degrades output quality, it does not signal failure.
  

Matching `read_file`'s error strings is a known ceiling. If Tactical 1 introduces a raising internal reader, Map Maker should call that instead. Mark the check with `# ponytail: matches file_ops error strings; use a raising reader once Tactical 1 lands`.
## 3. Work breakdown
Each step is independently committable. Each ends with the full suite green, run in a disposable copy (see §4).

**Step 1 — Isolate test outputs (no behavior change).**

- `tests/conftest.py`: add an autouse fixture that monkeypatches `config_loader.get_output_dir` to return `tmp_path / "out"`. `get_reports_dir` and `get_artifacts_dir` derive from it through `self.get_output_dir()` (`config_loader.py:68,79`). Tests that patch it again still win.
  
- `tests/test_reporting_tools.py`: delete `setup_module`/`teardown_module` and the `OUTPUT_DIR`-style literals. Assert against `config_loader.get_reports_dir()` / `get_artifacts_dir()` instead.
  
- `tests/test_map_maker.py`: delete the `os.remove`.
  
- Add a ToC fixture helper `write_valid_toc(path)` to `conftest.py`. It writes entries for `auth.md` and `billing.md`, which both exist in `docs-for-testing/`.
  
- Verify: the suite count is unchanged (52), and the sentinel check in §7 passes.
  

**Step 2 —** `output_validation.py` **(pure, not wired).**

- New `sdaa/src/core/output_validation.py`: `SKIPPED_PREFIX`, `WORKER_ARTIFACTS`, `REPORT_FILENAME`, `audit_output_paths()`, `toc_problems()`, `text_output_problems()`, `audit_output_problems()`, and `set_aside(paths)` (`os.replace(p, p + ".prev")` for each existing `p`).
  
- New `tests/test_output_validation.py`, written first, one case per D3 rule. ToC cases: valid; missing; non-JSON; `{}`; `{"files": []}`; entry missing a key; 2 tags; legacy `"Error reading file:"` summary; path not in the corpus; `../` path; symlink escaping the corpus; duplicate path. Text cases: missing; empty; whitespace-only; `SKIPPED:` legacy placeholder; non-UTF-8; valid. `set_aside`: moves existing files, ignores missing ones, overwrites an older `.prev`.
  

**Step 3 — Reporting tools raise.**

- `sdaa/src/tools/reporting.py`: remove the 4 `try/except` blocks. Docstrings keep `Returns: status message` for the tool schema.
  
- Test (`tests/test_reporting_tools.py`): with `get_artifacts_dir` patched to a non-existent nested path, each tool raises `OSError`.
  
- Test (`tests/test_prechat_audit.py`): an `LlmAgent` on `ArtifactLoaderModel` whose tool raises → `Runner.run_async` raises (pins F8 against ADK upgrades).
  

**Step 4 — Map Maker failures propagate.**

- `sdaa/src/core/map_maker.py`: the D6 edits.
  
- Tests (`tests/test_map_maker.py`, tmp corpus via monkeypatched `file_ops._get_docs_root`):
  
  - empty corpus raises and writes no ToC;
    
  - a missing docs root raises;
    
  - an unreadable `.md` (invalid UTF-8) raises and names the file;
    
  - a model that raises (simulating OpenRouter raise-on-error) propagates, with no ToC written;
    
  - an unwritable output dir raises;
    
  - the happy path writes a ToC that passes `toc_problems`.
    

**Step 5 — Synthesis reads artifact files.**

- `sdaa/src/agents/coordinator.py`: implement D5 inside `_build_synthesis_prompt` and touch nothing else there. Tactical 2 will rework the prompt-compile half of the same function.
  
- Tests (`tests/test_prechat_audit.py`): the stub prompt records `compile(**kwargs)`.
  
  - Replay: pre-write 3 artifacts containing distinctive tokens and run the pre-chat agent with `mock`. Assert each `*_report` kwarg contains its token and not `"Artifact loaded"`.
    
  - Fresh mock run: assert the kwargs contain the MockModel findings headings (`# RBAC Analysis`, etc.), not `"recorded and saved"`.
    
  - A body containing `{user_id}` arrives sanitized as `(user_id)`.
    

**Step 6 — ToC gate in** `main.py`**.**

- `main.py`: the Phase 1 part of D4, with Map Maker failure fatal in all modes and the misleading "Skipping … due to --skip-map-maker" text fixed for `--coordinator-only`. Import the validators by name into `main` so tests can patch `main.toc_problems`.
  
- Existing tests to update:
  
  - `{}` ToC fixtures → `write_valid_toc`: `test_main_skip_map_maker.py:42,71,165`, `test_main_headless.py:81,112-113,139-140`. The last one matters most: with an invalid ToC it would still exit 1, but for the wrong reason, and it would stop guarding the pre-chat-raise path.
    
  - `test_main_honors_skip_flag_even_without_toc` → now expects `SystemExit(1)` (a missing ToC under `--skip-map-maker` is invalid). Rename it to say so.
    
  - `test_factory_and_integration.py::test_main_calls_factory_for_all` patches `main.config_loader` wholesale and patches `os.path.exists` to always return False (`:90-92`). Also patch `main.toc_problems` and `main.audit_output_problems` to return `[]`.
    
- New tests (`tests/test_main_skip_map_maker.py`):
  
  - an invalid ToC present without flags → Map Maker regenerates it, and the old ToC becomes `ToC.json.prev`;
    
  - an invalid ToC with `--skip-map-maker --headless` → exit 1, and `generate_toc` is not called;
    
  - `generate_toc` raising in interactive mode → exit 1, and the chat is never entered.
    

**Step 7 — Validated reuse, coordinator-only and the headless gate.**

- `main.py`: the Phase 2.5 and final-gate parts of D4.
  
  - `build_prechat_audit_agent(provider)` loses `coordinator_only` and the SKIPPED branch. Reuse becomes `not text_output_problems(path)` instead of `os.path.exists` (`main.py:72`).
    
  - Replace `get_missing_prechat_outputs` with `output_validation.audit_output_problems`, and update `test_prechat_audit.py::test_get_missing_prechat_outputs` to test the replacement.
    
  - Print the reused/generated summary.
    
- New tests (`tests/test_main_headless.py`):
  
  - an empty `permissions_agent.md` → that worker reruns live (mock), the others replay, and the exit is 0 with a non-empty artifact;
    
  - a legacy `SKIPPED:` artifact + `--headless` → regenerated;
    
  - the same with `--coordinator-only` → exit 1, no model calls, and no files written;
    
  - `--coordinator-only` with an artifact missing → exit 1, and no `SKIPPED` file appears;
    
  - `--coordinator-only` where synthesis does not write a report: start from a valid report, stub the synthesizer to skip its tool call, and assert exit 1 and `Security_Threat_Model.md.prev` holds the old text;
    
  - the existing `…prechat_raises_and_outputs_exist` test → exit 1; the old report is preserved in `.prev` (update its assertion at `test_main_headless.py:166`);
    
  - all valid and nothing to do → exit 0, with every output reported as `reused`.
    

**Step 8 — Refresh flags.**

- `main.py`: add the 2 `argparse` flags, the 4 `parser.error` checks, and the 2 `set_aside` calls (D2/D4).
  
- Tests:
  
  - **stale ToC**: a valid ToC plus valid outputs, then `--refresh-toc --headless` → `generate_toc` is called and every output is `generated`, with `.prev` copies;
    
  - **edited corpus**: a tmp corpus is indexed, a file is edited and another added, then `--refresh-toc --toc-only` → the new ToC lists the added file, and the downstream outputs are moved to `.prev`, so the next headless run regenerates them;
    
  - **audit refresh**: `--refresh-audit --headless` → `generate_toc` is not called, and all 4 outputs are regenerated;
    
  - **contradictions**: parametrised over the 4 rejected pairs → `SystemExit(2)`, with no file created or moved in the tmp output dir;
    
  - **allowed combos** parse without error.
    

**Step 9 — Docs** (§6).
## 4. Test plan
Each scenario from the brief, mapped to the step that covers it:

| Scenario | Step | Test location |
|---|---|---|
| Stale ToC + `--refresh-toc` | 8 | `test_main_skip_map_maker.py` |
| Edited corpus + refresh (tmp corpus) | 8 | `test_main_skip_map_maker.py` |
| Invalid / missing / empty ToC (unit) | 2 | `test_output_validation.py` |
| Invalid ToC at CLI level (regenerate vs. `--skip-map-maker` exit 1) | 6 | `test_main_skip_map_maker.py` |
| Empty corpus / unreadable doc / model raise in Map Maker | 4 | `test_map_maker.py` |
| Empty worker output → rerun | 7 | `test_main_headless.py` |
| SKIPPED placeholder (legacy file; coordinator-only never writes one) | 2, 7 | both |
| Failed write (reporting tool raises; ADK propagates) | 3 | `test_reporting_tools.py`, `test_prechat_audit.py` |
| Synthesis gets no report (stale report not counted as success) | 7 | `test_main_headless.py` |
| Replayed artifact body reaches synthesis (also fresh mock) | 5 | `test_prechat_audit.py` |
| Contradictory flags → exit 2, no side effects | 8 | `test_main_skip_map_maker.py` |

Isolation rules:

- Every new CLI test calls `_isolate_output_dirs` (`test_main_headless.py:49-67`) or relies on the Step 1 autouse fixture. Corpus edits go into a `tmp_path` corpus selected through `file_ops._get_docs_root`; never into `docs-for-testing/`.
  
- Keep the prompt stubs (`test_main_headless.py:17-46`) until Tactical 2 lands.
  

Running safely: never run the suite in the repo root. Use the AGENTS.md disposable-copy procedure exactly. Until the repo `.venv` is repaired (`python -m pip install -r requirements.lock`), point `repo_root/.venv/bin/python` at any clean venv built from the lock. After Step 1, a root-level run should be harmless, but the copy procedure stays the documented rule.
## 5. Backward compatibility and risk
Behavior changes users will notice:

1. **Headless runs that "passed" now fail (exit 1)** when:
  

- the ToC is `{}`, empty, malformed or references missing files;
  
- any artifact or report is empty or a `SKIPPED:` placeholder;
  
- `--coordinator-only` is missing an artifact;
  
- `--skip-map-maker` is given without a valid ToC.
  

Migration: rerun with `--refresh-audit`, or `--refresh-toc` for a bad index. To check an index cheaply, use `--skip-map-maker --toc-only`, which exits 0 or 1.

2. **Interactive mode now exits 1** when Map Maker fails or the ToC is invalid; it used to continue.
  
3. **Map Maker aborts** on any unreadable document or an empty corpus, naming the file. It used to index the error text.
  
4. `.prev` **files** appear next to regenerated outputs.
  
5. **Synthesis prompts grow**: they now carry the full findings instead of one-line acknowledgements (F5/F6). This is the intended fix, but on large corpora it raises token cost and context risk for the synthesizer. Budgeting is Strategic Feature 2. The remote `report-synthesizer` prompt may also need review, since replayed runs have never shown it real findings.
  
6. **A disk-level write failure during interactive chat** now ends the session. A raised tool error reaches `main.py:258-260`, which breaks the loop. It used to come back to the model as an error string.
  

What could regress, and how it is guarded:

- **OpenRouter raise-on-error and key rotation:** no new `except` around model calls. Step 4 adds a "model raises → propagates" test; the existing `test_key_rotation.py` and `test_openrouter_*.py` stay unchanged.
  
- **Loader tool-call IDs:** `ArtifactLoaderModel` is untouched.
  
- **Brace handling:** Step 5 tests sanitization of artifact bodies.
  
- **Tests patching** `main` **internals:** `test_factory_and_integration.py` needs the extra patches from Step 6.
  
- **Merge friction:** Tactical 1 (`file_ops`) and Tactical 2 (`prompt_manager`, and the same `_build_synthesis_prompt`) touch neighbouring code. Keep the Step 5 diff limited to report gathering.
  

Seams left for strategic work, but not built:

- `output_validation` is the single place a run manifest or hash check would hook in (Strategic 2).
  
- `audit_output_paths()` is the one expected-output list a manifest would replace.
  
- `set_aside` is where run-specific output directories would replace `.prev`.
  
- Synthesis reading files is where validated JSON findings would be read instead (Strategic 1).
  
## 6. Docs
- **README.md:**
  
  - Phase 1 (`:54`): the ToC is reused when valid and regenerated when missing or invalid.
    
  - Flags table (`:129-135`): add `--refresh-toc` and `--refresh-audit`; list the rejected combinations and exit code 2; replace the `--headless` description with the D4 definition (exit 0/1/2; valid outputs; reused vs. generated); state that `--coordinator-only` requires 3 valid artifacts.
    
  - Workflow (`:140`): reuse requires valid outputs.
    
  - Add a short "Rerunning after documentation changes" note: reuse does not detect edits; use `--refresh-toc`; `.prev` holds the previous outputs.
    
- **docs/INTERNALS_AND_DESIGN_PATTERNS.md:38-47** and **docs/ARCHITECTURE_AND_DATA_FLOW.md:66**: replace the "content into session state" claim with: the loader replays the tool call; synthesis reads the artifact files.
  
- **docs/CONFIGURATION_GUIDE.md:147:** add the new flags.
  
- **AGENTS.md:** update the "Execution pipeline and reuse" paragraph (validation-based reuse, `.prev`, synthesis reads files, no SKIPPED placeholders) and the `--coordinator-only` / `--headless` bullets.
  
- **archive/IMPLEMENTATION_PLAN.md:** leave it unedited, since it is archived. This plan supersedes its stale `:117` and `:195` claims.
  

Entry for `PROGRESS.md` (location per Q6):

```
## Phase: Tactical 3 — Explicit Refresh and Trustworthy Completion | <date>
### Tasks Completed
- [x] output_validation.py: ToC/artifact/report validity; legacy SKIPPED detection.
- [x] --refresh-toc / --refresh-audit with contradiction checks (exit 2); regenerated outputs kept as .prev.
- [x] Map Maker and reporting failures propagate; headless success = valid ToC + 4 valid outputs.
- [x] Synthesis reads artifact files (fixes acknowledgement-in-state on replay and fresh runs).
- [x] Destructive tests moved to tmp_path; suite: <N> passed (clean venv, disposable copy).
### Next Steps & Continuity
- Freshness detection / manifests remain Strategic 2; validation module is the hook.
- Synthesizer prompt now receives full findings — review the remote prompt and watch token use.
```

Entry for `LOG_BOOK.md`, written only for work outside the plan, such as the F14 fix if it lands separately:

```
## OpenRouter tool schema on ADK 2.14 | <date>
_convert_tools now reads parameters_json_schema when parameters is None; fixes AttributeError on every tool-bearing OpenRouter call.
```
## 7. Exit criteria (release 0.3)
1. In a clean venv from `requirements.lock`, the full suite passes in a disposable copy, with at least 52 tests plus the new ones.
  
2. **Tests leave user outputs untouched.** In the disposable copy, run:
  

```bash
mkdir -p output/artifacts output/reports && echo sentinel | tee output/ToC.json output/artifacts/permissions_agent.md output/reports/Security_Threat_Model.md >/dev/null
find output -type f -exec sha256sum {} + | sort > /tmp/before
"$repo_root/.venv/bin/python" -m pytest tests -q
find output -type f -exec sha256sum {} + | sort | diff /tmp/before -
```

The `diff` must be empty.

3. **No silent success.** Named tests show `--headless` exits non-zero for each of:
  

- a missing, empty, malformed or dangling ToC;
  
- an empty or `SKIPPED:` artifact under `--coordinator-only`;
  
- a missing artifact under `--coordinator-only`;
  
- a reporting write failure;
  
- Map Maker read, list or model failure;
  
- synthesis that writes no new report.
  

4. **No manufactured inputs.** `grep -n "SKIPPED" main.py` returns nothing, and no code path writes a placeholder artifact.
  
5. **No swallowed failures.** `grep -n "except" sdaa/src/tools/reporting.py` returns nothing, and `map_maker.py` contains only the JSON-decode fallback `except`.
  
6. **Synthesis sees findings.** The Step 5 tests show artifact bodies, not acknowledgements, in the synthesizer's compile arguments for both replay and fresh runs.
  
7. **Refresh works.** The flags behave per D2: Step 8 tests pass, and contradictions exit 2 with no file-system side effects.
  
8. The README, the two `docs/` guides, AGENTS.md and `PROGRESS.md` are updated per §6.
  
## 8. Open questions for the maintainer
Each question has a recommendation the plan already assumes, so implementation is not blocked. The plan proceeds with the recommendation unless the maintainer overrides it. The last column says what changes if they choose otherwise.

|
| Q1 | When refreshing or regenerating, should the previous outputs be moved aside as `.prev` or deleted? | **Move aside to `<name>.prev`, keeping one generation and overwriting any older `.prev`.** | Same code size as `unlink` (`os.replace` vs `os.remove`), and a refresh that fails mid-run (provider outage, 429 exhaustion, Ctrl-C) loses nothing. To delete instead: swap the call in `set_aside` and drop the `.prev` assertions in Steps 6–8. Never "overwrite in place": a worker that fails to write would leave the old file looking fresh (D1). |
| Q2 | Should an *implicit* ToC regeneration (ToC missing or invalid, no flag) also invalidate the existing audit outputs? | **No. Keep the audit outputs and print `audit outputs predate the new ToC; use --refresh-audit`.** | This matches today's behavior, and a user who deleted only `ToC.json` may still be iterating on the findings. Explicit refresh stays the only thing that discards work. To invalidate instead: call `set_aside(audit_output_paths())` next to the ToC regeneration in D4, and add one Step 6 test. That is safe, but it costs a full live audit every time the ToC is missing. |
| Q3 | Should a ToC whose file set differs from the current corpus (files added or removed) count as invalid? | **No, not in T3. Document it as a known limitation in the README note from §6.** | Comparing against `list_files()` is cheap, but it is freshness detection, which is out of scope (Strategic 2). It would also misclassify ToCs as stale when Tactical 1 changes listing rules (sorting, symlink exclusion). Revisit when the Strategic 2 manifest lands; `toc_problems` is the hook. If the maintainer wants it now, make it a **warning**, not a failure. |
| Q4 | Should interactive `--coordinator-only` allow a degraded session when some worker artifacts are missing? | **No. Exit 1 in all modes, listing the missing or invalid artifacts and suggesting a run without `--coordinator-only`.** | A degraded synthesis is exactly what produced F9's persistent `SKIPPED` files. If the maintainer wants a degraded interactive mode, it must never write anything for the missing workers: no placeholder files, synthesis sees `MISSING: …`, and the report is not counted as complete. That adds a branch and two tests. Defer it until a user asks. |
| Q5 | Should headless `--coordinator-only` require a valid ToC, even though synthesis does not read it? | **Yes. Apply the same ToC gate in every mode.** | One rule is simpler than mode-specific exceptions. A "completed audit" includes the index its findings came from, and the interactive coordinator reads `ToC.json` through `read_file`. The cost: a user who deleted only the ToC must regenerate it (`--toc-only`) before re-synthesizing. To exempt coordinator-only: skip the D4 ToC gate when `coordinator_only` is set, and document the exception. |
| Q6 | `PROGRESS.md` and `IMPLEMENTATION_PLAN.md` now live in `archive/`, but AGENTS.md says to read them at the root. Where should phase records go? | **Append the phase entry to `archive/PROGRESS.md` and keep active plans in `docs/plans/`. In the Step 9 docs commit, update AGENTS.md: read `archive/PROGRESS.md` for history and `docs/plans/` for active work.** | This keeps one continuous history without un-archiving anything. Alternatives: restore `PROGRESS.md` to the root (undoes `37113a0`'s intent), or start a fresh progress log in `docs/plans/` (splits the history). Either is fine if the maintainer prefers it; the AGENTS.md pointer must match whichever is chosen. |
| Q7 | ~~F14 (OpenRouter + tools broken on ADK 2.14): fix before T3?~~ | **Resolved.** PR #45 (`bab009a`, merged as `0471e25`) shipped the fix. | The converter now prefers `parameters_json_schema`, then falls back to legacy `Schema`, then to an empty object schema. Regression tests in `tests/test_openrouter_tool_schema.py` build declarations from real ADK agents, and `test_skip_map_maker_with_existing_toc_still_initializes_agents` now patches `model_factory` and is hermetic. Remaining action for T3: line references in Step 6 for `tests/test_main_skip_map_maker.py` may have shifted after #45, so re-check them when implementing. Drop the F14 `LOG_BOOK.md` draft in §6, since #45 already logged it. |
