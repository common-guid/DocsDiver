# Plan: Eval Phase P3, Run Manifest, Run ID and Call Ledger

Status: Reviewed by Fable 5.2 (`12_P3_PLAN_REVIEW.md`, approve with changes); all 15 findings applied 2026-11-12. Ready to implement after P2 merges.
Created 2026-11-12 · Base: `ADK_master` **after P2 merges** (`09_P2_PATHS_PLAN.md`) · Design: `05_EVAL_DESIGN.md` §3.6 ("P3, run manifest"), §3.7 (sessions) and §4 · Also closes the vault task "Set Langfuse trace tags on every span"

## 1. Goal

After P3, every headless run writes `run_manifest.json` to its output directory. The manifest records:
- which code, corpus, models and prompt versions the run used;
- what each model call cost;
- which outputs the run generated;
- how it ended.

Every trace of a run lands in one Langfuse session named by the run ID.

The eval runner (H2) judges a run valid from the manifest alone. The report (H3) builds its provenance table from the manifest.

## 2. Facts checked on 2026-11-12

- **F1. Session today.** The ADK session ID is hardcoded `"session_001"` (`main.py:219 (P2 version)`) and is shared by every run. The OpenInference instrumentor copies it to `session.id` on ADK spans, so every run lands in the Langfuse session `session_001`. Map Maker calls the model outside ADK, so each Map Maker call is its own trace with no session (design V4).
- **F2. Langfuse v4 needs session and tags on every span.** The Langfuse OpenTelemetry docs ("Propagating Trace Attributes to All Spans", fetched 2026-11-12) say `sessionId` (`langfuse.session.id` or `session.id`) and `tags` (`langfuse.trace.tags`) must be on **all** spans for filtering in v4. Today `TaggingSpanProcessor` uses `parent_context is None` as its root check (`sdaa/src/core/instrumentation.py:25-41`). This matches most spans started with the implicit context, including children; only `call_llm` lacks tags in review S1. The docs recommend OpenTelemetry baggage or the SDK's `propagate_attributes()`. Here one process is one run, so a span processor that stamps every span in `on_start` has the same effect and needs no context plumbing.
- **F3. Attribute names.** `langfuse` 5.2.0: `LangfuseOtelSpanAttributes.TRACE_SESSION_ID == "session.id"` and `TRACE_TAGS == "langfuse.trace.tags"`. The fallback class in `instrumentation.py:17-19` defines only `TRACE_TAGS`.
- **F4. Processor wiring.** `TaggingSpanProcessor()` is added only when an exporter is configured (`instrumentation.py:146`). Its `on_start` runs before any span is exported, so attributes set there reach both the repo exporter and the Langfuse SDK processor added by `prompt_manager.py:33` (P1 plan F12).
- **F5. The model doesn't know its agent.** `get_model_for_agent(agent_name, provider)` (`sdaa/src/core/model_factory.py`) builds a new model instance per agent, but it doesn't tell the model which agent it serves. In mock mode it returns early with `MockModel(model="mock-model")`. Map Maker gets its model from the factory as `map_maker` (`main.py:162`).
- **F6. Prompt version per call.** Workers and the synthesizer call `model.set_langfuse_prompt(prompt_obj)` only when the fetch succeeds:
  - workers: `workers.py:31-38` and the two siblings;
  - synthesizer: `coordinator.py:~110`, on every instruction build.
  
  A failed fetch leaves `_langfuse_prompt` as `None` for a fresh model (design V5). The synthesizer never clears the prompt, so a failed fetch after a successful one leaves the old version on the model. Map Maker's prompt is inline, so it never has one. `MockModel` also has `set_langfuse_prompt` (`mock_model.py:9`).
- **F7. One agent name, two agents.** Both the chat coordinator and the synthesizer are `LlmAgent(name="coordinator_psa")`. The synthesizer's model comes from the factory key `coordinator`. The ledger uses the factory key, so synthesis calls are recorded as `coordinator`.
- **F8. Usage today.** `_record_usage(span, response)` (`openrouter_model.py:24`) puts tokens and cost on the span and returns nothing. The streaming branch records nothing (`# ponytail:` at line 353); headless never streams. The `openai` 1.109.1 `ChatCompletion` allows extra fields, so OpenRouter's `provider` field, when the response has one, is readable with `getattr(response, "provider", None)`. OpenRouter's published `ChatResult` schema has no top-level `provider`; routing data is documented under the opt-in `openrouter_metadata`.
- **F9. Exits.** A headless run ends in one of three ways:
  - a `return` on success;
  - `sys.exit(1)` from one of five places (Map Maker failure, unusable ToC, coordinator-only without artifacts, pre-chat exception, the final gate), at `main.py:188, 198, 257, 291, 305` (P2 version);
  - an uncaught exception, including `BaseException`.
  
  Usage errors exit 2 through `parser.error` before any work.
- **F10. The tests call `asyncio.run(app.main())` directly** (`tests/test_main_headless.py:95`, `_run`), not the `__main__` block. Manifest writing must therefore live inside `main()`.
- **F11. Output reuse.** Modification times cannot tell a replayed artifact from a regenerated one. Whenever the pre-chat audit runs, each valid artifact is replayed through its reporting tool, which rewrites the file (`artifact_loader_model.py:41-52`, `reporting.py:52-87`). `_run` must track which outputs it regenerated.
- **F12. `output/` is gitignored** (`.gitignore:131`), so a default run doesn't make the tree dirty.

## 3. Design

- **D1. `--run-id <id>`.** It must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`, because the eval runner uses it as a directory name; otherwise `parser.error(f"--run-id {value!r}: use 1-64 letters, digits, '.', '_' or '-', starting with a letter or digit")`, exit 2. If it's absent, generate `YYYYMMDDTHHMMSSZ-<6 hex>` (UTC), so every run, interactive ones included, gets its own session. The run ID becomes:
  - the ADK session ID (replacing `session_001`);
  - the Langfuse session ID, set on every span (D2).
- **D2. Session and tags on every span.** `TaggingSpanProcessor(session_id)`:
  - sets `langfuse.trace.tags = ["ADK-DocsDiver"]` and `session.id = <run id>` in `on_start` for **every** span;
  - keeps the existing `langsmith.span.tags` branch unchanged.
  
  This closes the vault task "Set Langfuse trace tags on every span".
- **D3. Call ledger.**
  - A module-level list in the new `sdaa/src/core/run_manifest.py`. `main()` clears it at the start of each run, because tests run many `main()`s in one process. Clear in place (`LEDGER.clear()`); never rebind the name.
  - `OpenRouterModel` appends one entry per completed call. `MockModel` appends a zero-cost entry so mock runs exercise the manifest.
  - Recording never raises into a model call.
  - `InstrumentedGemini` is not recorded in P3. Note for H2: a valid run needs `provider == "openrouter"` and the four audit agents plus `map_maker` present in `agents`.
- **D4. Agent name.** `get_model_for_agent` sets `model._agent = agent_name` on every model it returns, mock included. The ledger records `_agent`, or `null` when it's unset (a model built outside the factory).
- **D5. Prompt version from the call, not the fetch.** Each ledger entry copies `name` and `version` from the model's `_langfuse_prompt`, or `null` when there is none. That is "what each call actually used" (design §3.6). A failed fetch shows up as a `null` version on that agent's calls. Map Maker's inline prompt also shows `null`; the eval runner exempts `map_maker` from the prompt-version rule (note for H2).
- **D6. Manifest written only in headless mode,** on every exit except usage errors: success, `sys.exit(1)` and uncaught exceptions. `main()` becomes a thin wrapper:
  1. parse and validate (exit 2 stays manifest-free);
  2. record the start time and clear the ledger;
  3. compute the corpus hash once in the wrapper before `_run`, as specified in §4.1;
  4. run the existing body as `_run(args, parser, run_id, regenerated)`, with the changes in §4.6:

     ```python
     code = 1                      # anything but a normal return is a failure
     regenerated = set()
     try:
         await _run(args, parser, run_id, regenerated)
         code = 0
     except SystemExit as e:
         code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
         raise
     finally:
         if args.headless:
             try:
                 ...write_manifest(..., exit_code=code, ...)
             except Exception as e:
                 print(f"run manifest not written: {e!r}", file=sys.stderr)
     ```
  
  Interactive runs write no manifest.
- **D7. Outcome problems are recomputed at write time** from the existing checks: `toc_problems(toc_path)` plus `audit_output_problems()`, the latter skipped for `--toc-only`. The manifest doesn't capture exception text; the runner keeps the log (design §3.6, `run.log`).
- **D8. Corpus tree hash.** Use the `tree_hash` code and failure handling in §4.1 as the single definition. Phase H1's `corpus build` must import it from `run_manifest`, not reimplement it, because the eval looks up the manifest's hash in `variants.yaml`.
- **D9. Code state.** `git rev-parse HEAD` and `git status --porcelain` run with `cwd` set to the repository root (the directory of `main.py`), not the working directory. On any failure: `commit: null, dirty: null`.

### Manifest shape (`schema: 1`)

```json
{
  "schema": 1,
  "run_id": "20261112T150102Z-a1b2c3",
  "started_at": "2026-11-12T15:01:02Z",
  "ended_at": "2026-11-12T15:04:40Z",
  "argv": ["main.py", "-m", "openrouter", "--headless", "..."],
  "provider": "openrouter",
  "paths": {"docs_root": "/abs/docs", "output_dir": "/abs/out"},
  "code": {"commit": "<sha>", "dirty": false},
  "corpus": {"tree_hash": "<sha256>", "file_count": 28},
  "agents": {
    "permissions_agent": {
      "models": ["deepseek/deepseek-v4.1-flash-1017"],
      "providers": ["DeepInfra"],
      "prompts": [{"name": "permissions-agent", "version": 2}],
      "calls": 5, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "unmetered_calls": 0
    }
  },
  "usage": {"calls": 17, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0404, "unmetered_calls": 0},
  "outputs": {
    "ToC.json": {"status": "generated", "sha256": "<hex>"},
    "permissions_agent.md": {"status": "generated", "sha256": "<hex>"},
    "constraints_agent.md": {"status": "reused", "sha256": "<hex>"},
    "boundaries_agent.md": {"status": "generated", "sha256": "<hex>"},
    "Security_Threat_Model.md": {"status": "missing", "sha256": null}
  },
  "outcome": {"exit_code": 0, "problems": []},
  "calls": [
    {"agent": "map_maker", "model": "deepseek/...", "response_model": "deepseek/...", "provider": "DeepInfra",
     "prompt": {"name": null, "version": null}, "input_tokens": 812, "output_tokens": 95, "total_tokens": 907,
     "cost_usd": 0.0000531, "metered": true}
  ]
}
```

- `agents.<name>.models`, `providers` and `prompts` list the distinct values seen in that agent's calls, sorted. A clean run has exactly one prompt pair per agent.
- `status` is `missing` if the file is absent, `generated` if `_run` regenerated it, otherwise `reused`. The wrapper creates `regenerated = set()` and passes it to `_run(args, parser, run_id, regenerated)`. `_run` adds `toc_path` right after `generate_toc` returns, and calls `regenerated.update(generated)` right after `generated` is computed. `write_manifest` takes `generated: set[str]` and no longer needs modification times.
- `metered` is false when the response had no usage or the call streamed. Such calls count in `unmetered_calls`, and their tokens and cost count as 0.
- `calls` is the full ledger, about 20 entries per audit. It is kept because OpenRouter can route one model slug to different upstream providers (design §7).

## 4. Changes

### 4.1 `sdaa/src/core/run_manifest.py` (new, standard library only)

```python
LEDGER: list[dict] = []

def record_call(entry: dict) -> None: ...          # append; never raises
def prompt_ref(prompt_obj) -> dict:
    return {"name": getattr(prompt_obj, "name", None), "version": getattr(prompt_obj, "version", None)}
def git_state(repo_root: str) -> dict: ...         # D9
def write_manifest(path: str, *, run_id, started_at, argv, provider, paths,
                   repo_root, corpus, output_files: dict[str, str], generated: set[str],
                   exit_code: int, problems: list[str]) -> None: ...
```

```python
def tree_hash(root: str) -> tuple[str, int]:
    lines = []
    for dirpath, dirnames, filenames in os.walk(root):          # does not follow symlinks
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            lines.append((rel, _sha256_file(path)))
    lines.sort()                                                # by relative path, code-point order
    data = "".join(f"{digest}  {rel}\n" for rel, digest in lines)
    return hashlib.sha256(data.encode("utf-8", "surrogateescape")).hexdigest(), len(lines)
```

`_sha256_file(path)` returns the hex SHA-256 of the file's bytes, read in 64 KiB chunks. The module imports `hashlib` and `os`.

Every regular file counts, hidden and non-Markdown files included. Empty directories don't. The wrapper computes it once, before `_run`, inside `try/except`; if `root` is not a directory or the walk fails, the manifest records `corpus: {"tree_hash": null, "file_count": null}`.

- `output_files` maps each display name (`ToC.json` and the four outputs) to its absolute path.
- `corpus` is the wrapper's start-of-run hash and file count, or the nulls above. `generated` is the `regenerated` set filled by `_run`; no modification times are read.
- `write_manifest` builds `agents` and `usage` from `LEDGER`, then writes the file with `indent=2`. It writes to a temporary file in the same directory and finishes with `os.replace`, so the runner never reads half a manifest.
- It doesn't import `config_loader`; `main()` passes everything in.

### 4.2 `sdaa/src/utils/openrouter_model.py`

- `_record_usage` returns `(counts, cost)`, where `counts` is the dict it already builds and `cost` is a float or `None`. It still never raises; on an exception it returns `({}, None)`.
- Add `_agent: Optional[str] = None` next to `_langfuse_prompt`.
- After `_record_usage(span, response)` in the non-streaming branch, call `record_call(...)` with:
  - `agent` = `self._agent`, `model` = `self.model`;
  - `response_model` = `getattr(response, "model", None)`, `provider` = `getattr(response, "provider", None)`;
  - `prompt` = `prompt_ref(self._langfuse_prompt)`;
  - the token counts, `cost_usd` and `metered` = `bool(counts) and cost is not None`.
- In the streaming branch, record an entry with `metered: false` before iterating the stream, so an abandoned stream is still counted.
- In both models, build the entry and call `record_call` inside one `try/except Exception` that logs a warning. No part of ledger recording may raise into a model call.

### 4.3 `sdaa/src/utils/mock_model.py`

Add `_agent: Optional[str] = None`. At the start of `generate_content_async`, record one entry: `model: "mock-model"`, `provider: "mock"`, `prompt: prompt_ref(self._langfuse_prompt)`, zero tokens, `cost_usd: 0.0`, `metered: true`. The `try/except` rule in §4.2 applies here too.

### 4.4 `sdaa/src/core/model_factory.py`

Assign the model to a variable on every path, set `model._agent = agent_name`, and return it. This includes the mock early return and the unknown-provider fallback.

### 4.4b `sdaa/src/agents/coordinator.py`

At the top of `_build_synthesis_prompt`, before the fetch: `if hasattr(model, "set_langfuse_prompt"): model.set_langfuse_prompt(None)`. The existing call after a successful `compile` sets it again.

### 4.5 `sdaa/src/core/instrumentation.py`

- The fallback class gains `TRACE_SESSION_ID = "session.id"`.
- `TaggingSpanProcessor.__init__(self, session_id=None)`. In `on_start`, set `TRACE_TAGS` on every span and `TRACE_SESSION_ID` when `session_id` is set. Keep the existing `langsmith.span.tags` branch byte-for-byte.
- `setup_instrumentation(session_id=None)` passes it to `TaggingSpanProcessor(session_id)`.

### 4.6 `main.py`

- Add `--run-id` with D1 validation, placed next to `apply_path_overrides`.
- Split `main()` as described in D6, with `_run(args, parser, run_id, regenerated)`. The code moved into `_run` stays as it is, except:
  - `session_id = run_id`;
  - `setup_instrumentation(session_id=run_id)`.
  - Add `toc_path` to `regenerated` right after `generate_toc` returns.
  - Call `regenerated.update(generated)` right after `generated` is computed.
- Compute the corpus hash once in the wrapper before `_run`, with the directory check and failure handling in §4.1.
- In the `finally` of D6, call `write_manifest` with:
  - `repo_root` = the directory of `main.py`;
  - `corpus` = the wrapper's start-of-run hash and file count, or nulls on failure;
  - `generated` = `regenerated`;
  - the ToC path and `audit_output_paths()`, keyed by basename.
  
  If writing the manifest itself raises, print the error and keep the original exit code.

### 4.7 Tests

New file `tests/test_run_manifest.py`. Every test that calls `main()`:
- calls `_real_paths(monkeypatch)` first (import it and `_STUB_PROMPTS` from `tests.test_main_headless`); without it conftest's `get_output_dir` patch overrides `--output-dir`;
- never names a directory `out`, and never uses `_isolate_output_dirs` or `_seed`;
- uses its own autouse fixture that patches `prompt_manager.get_prompt_object` to return an object with `name=<requested name>`, `version=7` and `compile(**kwargs)` returning `_STUB_PROMPTS[name]`, and `None` for other names.

M4 expects `SystemExit(1)`; read the manifest afterwards.

Add an autouse fixture to `tests/conftest.py` that calls `run_manifest.LEDGER.clear()` before each test.

| # | Test | Assert |
|---|---|---|
| M1 | `tree_hash` | Deterministic. Independent of creation order. Changes when one byte changes. A symlinked file is skipped. The count is correct. |
| M2 | Full mock headless run with `--run-id t-m2` | Every top-level key is present. `run_id == "t-m2"`. `outcome.exit_code == 0` and `problems == []`. All five outputs are `generated` with a `sha256`. `agents` has `map_maker`, the three workers and `coordinator`, each with `calls >= 1`. Each worker's `prompts == [{"name": <stub name>, "version": 7}]`. `map_maker` prompts are `[{"name": None, "version": None}]`. `usage.cost_usd == 0.0` and `unmetered_calls == 0`. `corpus.file_count` equals the files in the temporary corpus. `corpus.tree_hash == tree_hash(corpus)`. Wrap `app.setup_instrumentation` and `InMemorySessionService.create_session` with spies; both receive `session_id == "t-m2"`. |
| M3 | Pre-chat fails (as in `test_headless_exits_nonzero_when_outputs_missing`) | `SystemExit(1)`. The manifest exists with `exit_code == 1` and `problems` nonempty. |
| M4 | One worker's prompt fetch returns `None` | `SystemExit(1)`. That worker's `prompts == [{"name": None, "version": None}]`. The others are unaffected. |
| M5 | `--run-id ../x` | Exit 2. stderr contains `use 1-64 letters` (the old code also exits 2, with "unrecognized arguments", so the message is what proves the change). No manifest is written. |
| M6 | Second run in the same output directory, all outputs valid | All four audit outputs and the ToC are `reused`. `usage.calls == 0`, which also proves the ledger was cleared between runs. |
| M7 | No `--run-id` | `run_id` matches `^\d{8}T\d{6}Z-[0-9a-f]{6}$`. A run without `--headless` (`--toc-only`) writes no `run_manifest.json`. |
| M8 | After a full run, a second run with `--coordinator-only` | The three artifacts are `reused`, the report `generated`, and `ToC.json` `reused`. |
| M9 | An exception that is not `SystemExit`, raised inside `_run` | Patch `app.create_coordinator_agent` to raise `RuntimeError`. It propagates and leaves a manifest with `exit_code == 1`. |
| M10 | `--headless --toc-only` on a new output directory | Exit 0, `ToC.json` `generated`, the four audit outputs `missing`, `problems == []`. |

Unit test in `tests/test_run_manifest.py`:
- **C1:** two synthesis prompt builds, the second fetch returns `None`, and `model._langfuse_prompt is None` after the second.

Additions to `tests/test_openrouter_usage.py`, reusing its mocked-response helpers:
- **A1:** one call appends one ledger entry with agent, model, response model, provider, prompt name and version, tokens and cost.
- **A2:** a response without `usage` gives `metered: false`, and the call still succeeds.
- **A3:** if `record_call` is monkeypatched to raise, the call still yields its response.

Additions to `tests/test_instrumentation.py`:
- **I1:** with `TaggingSpanProcessor("run-x")` on an in-memory provider, a root span and a child span both carry the tags and `session.id == "run-x"`. Create the child with an explicit parent, `tracer.start_span("child", context=trace.set_span_in_context(root))`. The root carries `langsmith.span.tags`; this child does not. Don't assert on children started with the implicit context: the existing check tags those too.
- **I2:** constructs `TaggingSpanProcessor()` with no argument; no span has `session.id`.

Addition to `tests/test_model_factory.py` (create the file if it doesn't exist):
- **F1:** mock and openrouter models from the factory carry `_agent`.

**Existing tests to update (2).**
- `test_tagging_span_processor`, Case 2: replace `mock_span.set_attribute.assert_not_called()` with: the Langfuse tag is set, and `"langsmith.span.tags"` is not among the calls.
- `test_coordinator_only_with_skipped_artifact_exits_1_and_touches_nothing`: compare the tree without the manifest (`[p for p in _tree(out) if p != "run_manifest.json"] == before`) and assert the manifest exists with `exit_code == 1`.

Expected suite result: baseline + 17, with these two edited.

**Mutation check:** run the new tests against `ADK_master` from before P3. Import `run_manifest` inside the new test functions, not at module level. I2 constructs `TaggingSpanProcessor()` with no argument. Expected on the old code: `test_run_manifest.py` fails or errors as a whole; A1–A3, I1 and F1 fail; I2 and every existing test pass.

### 4.8 Documentation

- `AGENTS.md`, CLI section: add `--run-id` and one sentence on `run_manifest.json`, which is written on every headless exit except usage errors.
- `AGENTS.md`, Architecture: replace the root-only tagging description, if present, with "session and tags on every span".
- `docs/CONFIGURATION_GUIDE.md` §4: add a `--run-id` row.
- `docs/OBSERVABILITY_AND_PROMPTS.md`: one session per run; session and tags on every span; the manifest's `usage` is the cross-check for Langfuse cost.
- `README.md`: add `--run-id` to the flag table.
- `archive/PROGRESS.md`: a phase entry.

## 5. Steps

1. Branch `feat/eval-p3-run-manifest` from an up-to-date `ADK_master` that contains P2.
2. Run the baseline suite in a disposable copy and record the count.
3. Implement §4.1–§4.6, then the tests in §4.7.
4. Run the mutation check.
5. Verify:
   - `python -m compileall -q main.py sdaa tests scripts`;
   - the full suite in a fresh disposable copy: baseline + 17, with the two existing tests in §4.7 edited.
6. Update the docs (§4.8).
7. Run the logbook script.
8. Open a PR against `ADK_master`. The body includes pass counts, the mutation result and the manifest from M2. Don't merge.
9. **Live check, only after the operator approves (about $0.04).** See §6.

## 6. Live check

1. Read OpenRouter key usage, using the P1 plan's §6 method (`GET /api/v1/key`, `data.usage`).
2. In a disposable copy, run:

   ```bash
   LANGSMITH_API_KEY= python main.py -m openrouter --headless --no-rich \
       --docs-root docs-for-testing --output-dir <tmp>/out --run-id p3-live-<UTC>
   ```

   Run from the copy's root, with the repo's `.env` reachable as in P1.
3. Read key usage again, using P1's polling rule.
4. **Checks:**
   - `outcome.exit_code == 0`.
   - The manifest's `usage.cost_usd` is within $0.000001 of the OpenRouter difference.
   - Every audit agent has exactly one prompt pair with a non-null version.
   - Report how many ledger entries have a non-null `provider`. Zero is not a failure; record it, so a follow-up can read `openrouter_metadata` instead.
   - Two minutes after the run, with `--from-start-time <start>` and no session filter:
     `langfuse --env .env api observations list --from-start-time <start> --fields core,basic,usage,trace_context --all --json`
     - every observation returned has `sessionId == p3-live-<UTC>` and `ADK-DocsDiver` in `tags`; list any that don't;
     - `OpenRouterModel.generate_content` observations, counted by distinct `id`, equal `usage.calls`;
     - adapter observations with no parent observation (Map Maker's direct calls) equal `agents.map_maker.calls`. Don't count other parentless observations: ADK's `invocation` spans are roots too;
     - the sum of `totalCost` over distinct adapter observations equals the manifest's `usage.cost_usd` within $0.000001.

   Nothing else may write to the project during the window. The run's log must contain `Langfuse observability initialized`; if the 1-second health check fails, the tagging processor is not installed (`instrumentation.py:113-122, 144-146`). In the disposable copy `code` is `{commit: null, dirty: null}` because the copy has no `.git`; that is expected.
5. Delete the copy.

Report each number in the PR.

## 7. Decisions (all eight approved by the operator, 2026-11-12)

| # | Decision | Approved |
|---|---|---|
| 1 | Fold "Set Langfuse trace tags on every span" into P3 | Yes. Same processor, same test file, and v4 needs the session on every span anyway (F2) |
| 2 | Generate a run ID when `--run-id` is absent | Yes. Every run, interactive ones included, gets its own session instead of `session_001` |
| 3 | Manifest in headless mode only | Yes. Chat sessions aren't eval runs |
| 4 | Generated or reused from a set that `_run` fills (replaces modification times, review B2) | Yes (revised after review). Matches the `reused`/`generated` line `main.py` prints |
| 5 | Prompt version from each call, not from the fetch, plus a reset in the synthesizer (review M5) | Yes (revised after review). It records what was used; a failed fetch shows as `null` |
| 6 | Keep the full ledger in the manifest | Yes. About 20 rows; records provider routing per call |
| 7 | `tree_hash` lives in DocsDiver; H1 imports it | Yes. One definition, so hashes can't drift |
| 8 | Live check, a full audit, about $0.04 | Yes, after the PR passes review |

## 8. Questions for the reviewer

Answered in `12_P3_PLAN_REVIEW.md` §5.

## 9. Acceptance criteria

- [ ] M1–M10, A1–A3, I1–I2, F1 and C1 pass (17 new tests).
- [ ] Mutation check on the old code: `test_run_manifest.py` fails or errors as a whole; A1–A3, I1 and F1 fail; I2 and every existing test pass.
- [ ] Full suite passes in a disposable copy: baseline + 17, with the two existing tests in §4.7 edited.
- [ ] The manifest's `outputs` statuses match the `reused`/`generated` line `main.py` prints.
- [ ] A mock headless run writes a complete manifest. A failed run writes one with exit code 1 and its problems. A failed prompt fetch shows as a null version.
- [ ] Usage errors write no manifest.
- [ ] Docs, `archive/PROGRESS.md` and the logbook are updated.
- [ ] PR open, not merged. The live check is reported after the operator approves it.
