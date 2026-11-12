# Review: P3 Run Manifest Plan (`10_P3_RUN_MANIFEST_PLAN.md`)

Reviewed 2026-11-12 by Claude Fable 5.2 · Worktree at `edc2b7b`, with `main.py` and `tests/test_main_headless.py` from the P2 commit `8078cd9` · Interpreter: main checkout `.venv` (google-adk 2.14.0, openinference-instrumentation-google-adk 1.1.2, langfuse 5.2.0, opentelemetry-sdk 1.45.2, openai 1.109.1, pydantic 2.14.3)

## 1. Verdict

**Approve with changes.**

- The design holds: the processor puts session and tags on every span, the ledger records each call once, and the `main()`/`_run` split writes a manifest on every headless exit.
- Two things fail as written: two existing tests must break (B1), and the modification-time rule labels replayed artifacts `generated` (B2).
- Six more points would make an implementer guess or get it wrong, mostly in how the new tests meet existing fixtures.

Counts: 2 blockers, 6 major, 7 minor.

## 2. Fact check

Line numbers for `main.py` are for the P2 version (`8078cd9`).

| # | Result | Evidence |
|---|---|---|
| F1 | **Partly wrong** | `session_id = "session_001"` is at `main.py:219` (195 before P2). "No span carries a Langfuse session attribute" is false: the OpenInference instrumentor sets `session.id` on `invocation`, `agent_run` and `call_llm` spans (`_wrappers.py:168-173, 183-184`; §6 script S1). Langfuse already shows `sessionId=session_001` on these and on adapter observations inside ADK traces (§6, Langfuse query). Only the Map Maker roots have no session, as design V4 says. |
| F2 | **Docs confirmed; "root spans only" wrong** | Docs, "Propagating Trace Attributes to All Spans": "they need to be present on each span in the trace, not only on the root span". But the current processor is not root-only. `on_start` receives the caller's `context` argument, which is `None` whenever a span is started with the implicit current context (`opentelemetry/sdk/trace/__init__.py:1217`). So `parent_context is None` is true for almost every span. S1 shows a non-root adapter span and `agent_run` already tagged; only `call_llm` is not. See M1. |
| F3 | Confirmed | `langfuse/_client/attributes.py:32-33`. Fallback class: `instrumentation.py:18-19`. |
| F4 | Confirmed | `instrumentation.py:144-146`. The Langfuse client adds its processor to the global provider (`resource_manager.py:246-269`, `_init_tracer_provider` at 648-668). Attributes set in `on_start` are on the span object that both exporters read. S1 registers the exporter before the tagging processor and still sees the attributes. |
| F5 | Confirmed | `model_factory.py:19-41`; `main.py:183`. |
| F6 | Confirmed, with one gap | `workers.py:32-37`, `coordinator.py:104-112`, `mock_model.py:9`. Gap: the synthesizer never clears the prompt, so a failed fetch after a successful one leaves the old version on the model (M5). |
| F7 | Confirmed | `coordinator.py:64` and `124`; factory key `coordinator` at `coordinator.py:28, 73`. |
| F8 | Confirmed for the code; **`provider` unverifiable** | `openrouter_model.py:24, 353`. `getattr(ChatCompletion, "provider", None)` works (S4). OpenRouter's published response schema (`ChatResult`) has no top-level `provider`; routing data is documented under the opt-in `openrouter_metadata`. See m5. |
| F9 | Confirmed | `sys.exit(1)` at `main.py:188, 198, 257, 291, 305`. "Uncaught exception" must include `BaseException` (M4). |
| F10 | Confirmed | `tests/test_main_headless.py:95, 194`. |
| F11 | **Wrong** | `os.replace` keeps the modification time, but reused artifacts are not left untouched. Whenever the pre-chat audit runs, each valid artifact is replayed through its reporting tool, which rewrites the file (`artifact_loader_model.py:41-52`, `reporting.py:52-87`). See B2. |
| F12 | Confirmed | `.gitignore:131`. |

## 3. Findings

### B1 (blocker) — §4.6, §4.7, §9: two existing tests must fail

- **Problem.** The plan says the moved code "stays as it is" and expects "baseline + 13". Two existing tests cannot pass after P3:
  - `tests/test_instrumentation.py::test_tagging_span_processor`, Case 2, asserts `set_attribute.assert_not_called()` for a child span. D2 sets tags on every span.
  - `tests/test_main_headless.py::test_coordinator_only_with_skipped_artifact_exits_1_and_touches_nothing` asserts the output tree is unchanged after a headless exit 1. D6 writes `run_manifest.json` there.
- **Evidence.** Prototype of §4.1–§4.6 in a disposable copy: `2 failed, 151 passed` (baseline `153 passed`). §6, S2.
- **Change.** Add to §4.7:

  > **Existing tests to update (2).**
  > - `test_tagging_span_processor`, Case 2: replace `mock_span.set_attribute.assert_not_called()` with: the Langfuse tag is set, and `"langsmith.span.tags"` is not among the calls.
  > - `test_coordinator_only_with_skipped_artifact_exits_1_and_touches_nothing`: compare the tree without the manifest (`[p for p in _tree(out) if p != "run_manifest.json"] == before`) and assert the manifest exists with `exit_code == 1`.
  >
  > Expected suite result: baseline + 13, with these two edited.

### B2 (blocker) — F11, D6 schema note, §7 decision 4: replayed artifacts are reported as `generated`

- **Problem.** With `--coordinator-only`, or when only some outputs are invalid, valid artifacts are replayed and rewritten. Their modification time is after `started_at`, so the manifest says `generated`. `main.py` itself prints `(reused)` for the same files.
- **Evidence.** S3, `--coordinator-only` on a complete output directory:
  ```
  manifest: permissions_agent.md generated, constraints_agent.md generated, boundaries_agent.md generated, Security_Threat_Model.md generated
  main.py:  Audit outputs: permissions_agent.md (reused), constraints_agent.md (reused), boundaries_agent.md (reused), Security_Threat_Model.md (generated)
  ```
- **Change.** `main.py` already knows the answer (`generated = set(stale) | {report_path}`, `main.py:263-264`). Pass one set through instead of reading modification times. Replace the F11 rule and the `status` bullet with:

  > `status` is `missing` if the file is absent, `generated` if `_run` regenerated it, otherwise `reused`. The wrapper creates `regenerated = set()` and passes it to `_run(args, parser, run_id, regenerated)`. `_run` adds `toc_path` right after `generate_toc` returns, and calls `regenerated.update(generated)` right after `generated` is computed. `write_manifest` takes `generated: set[str]` and no longer needs modification times.

  Add test **M8**: after a full run, a second run with `--coordinator-only` gives the three artifacts `reused`, the report `generated`, and `ToC.json` `reused`.
- Verified in the prototype: all statuses match what `main.py` prints, and the suite result is unchanged (S3b).

### M1 (major) — D2, §4.7 I1: "only the root carries `langsmith.span.tags`" fails with a real provider

- **Problem.** The existing root check is `parent_context is None`. That is true for any span started with the implicit context, including ordinary children. I1 as written fails unless the implementer changes the check, which D2 forbids ("LangSmith behaviour doesn't change").
- **Evidence.** S5, real `TracerProvider` with the P3 processor:
  ```
  child-implicit-context   parent=yes session.id=run-x langfuse.trace.tags=('ADK-DocsDiver',) langsmith.span.tags=('ADK-DocsDiver',)
  child-explicit-context   parent=yes session.id=run-x langfuse.trace.tags=('ADK-DocsDiver',) langsmith.span.tags=None
  root                     parent=no  session.id=run-x langfuse.trace.tags=('ADK-DocsDiver',) langsmith.span.tags=('ADK-DocsDiver',)
  ```
- **Change.** Keep the LangSmith branch byte-for-byte. Reword D2 to "keeps the existing `langsmith.span.tags` branch unchanged". Replace I1's last sentence with:

  > Create the child with an explicit parent, `tracer.start_span("child", context=trace.set_span_in_context(root))`. The root carries `langsmith.span.tags`; this child does not. Don't assert on children started with the implicit context: the existing check tags those too.

### M2 (major) — §4.3, D3: reading `.name`/`.version` breaks every existing stubbed-prompt test

- **Problem.** §4.3 says "the prompt from `_langfuse_prompt`". The existing stubs have neither attribute (`tests/test_main_headless.py:25-30`; `tests/test_prechat_audit.py` uses the same kind). "Recording never raises" covers `record_call`, not the code that builds the entry.
- **Evidence.** First prototype used `lp.name`/`lp.version`: `14 failed`, 12 of them `AttributeError` at `mock_model.py`. With `getattr`, back to the two in B1.
- **Change.** Add to §4.1 and reference it from §4.2 and §4.3:

  ```python
  def prompt_ref(prompt_obj) -> dict:
      return {"name": getattr(prompt_obj, "name", None), "version": getattr(prompt_obj, "version", None)}
  ```

  > In both models, build the entry and call `record_call` inside one `try/except Exception` that logs a warning. No part of ledger recording may raise into a model call.

### M3 (major) — §4.7: the new tests collide with the autouse fixtures

- **Problem.** Three things the plan leaves to the implementer:
  1. conftest's autouse `_isolated_output_dir` still patches `get_output_dir`. With it in place, `--output-dir` is ignored and the manifest lands in `tmp_path/out`.
  2. `_stub_prompts` is defined in `tests/test_main_headless.py`, not conftest. It doesn't apply to a new file.
  3. M4 doesn't say the run exits 1. A worker with the error instruction writes no artifact under the mock model.
- **Evidence.** S3: with only the conftest patch left in place, `manifest in --output-dir: False | manifest in tmp_path/out: True`. Missing-prompt run: `exit 1`, `constraints_agent.md: missing`, that worker's prompts `[{name: None, version: None}]`, the others unaffected.
- **Change.** Replace the first paragraph of §4.7 with:

  > New file `tests/test_run_manifest.py`. Every test that calls `main()`:
  > - calls `_real_paths(monkeypatch)` first (import it and `_STUB_PROMPTS` from `tests.test_main_headless`); without it conftest's `get_output_dir` patch overrides `--output-dir`;
  > - never names a directory `out`, and never uses `_isolate_output_dirs` or `_seed`;
  > - uses its own autouse fixture that patches `prompt_manager.get_prompt_object` to return an object with `name=<requested name>`, `version=7` and `compile(**kwargs)` returning `_STUB_PROMPTS[name]`, and `None` for other names.
  >
  > M4 expects `SystemExit(1)`; read the manifest afterwards.

### M4 (major) — D6 step 4: exit code for `BaseException`, `None` and string codes

- **Problem.** "0 on return, `e.code` for `SystemExit`, 1 for any other exception". Coded with `except Exception`, a `KeyboardInterrupt` or `asyncio.CancelledError` records `exit_code: 0`. `SystemExit().code` is `None` and `SystemExit("msg").code` is a string; neither is a valid manifest integer.
- **Evidence.** S3, `KeyboardInterrupt` raised inside `_run`, first prototype: `manifest exit_code = 0 problems 4`. S4 prints the `SystemExit` codes.
- **Change.** Put this code in D6:

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

  Add test **M9**: an exception that is not `SystemExit`, raised inside `_run` (patch `app.create_coordinator_agent` to raise `RuntimeError`), propagates and leaves a manifest with `exit_code == 1`.

### M5 (major) — D5, F6: the synthesizer can record a prompt version it did not use

- **Problem.** `_build_synthesis_prompt` runs before every synthesis call. It sets the prompt on success and does nothing on failure. If call 1 fetches version 7 and call 2's fetch fails, call 2 runs on the error sentence but the ledger records version 7. The agent then shows one clean prompt pair and passes the H2 rule.
- **Evidence.** S4:
  ```
  build 1: instruction='You are the Principal Security Architect.' | model._langfuse_prompt version=7
  build 2: instruction="Error: Could not fetch 'report-synthesizer' p" | model._langfuse_prompt version=7
  ```
- **Change.** Add §4.4b, `sdaa/src/agents/coordinator.py`:

  > At the top of `_build_synthesis_prompt`, before the fetch: `if hasattr(model, "set_langfuse_prompt"): model.set_langfuse_prompt(None)`. The existing call after a successful `compile` sets it again.

  Add a unit test: two builds, the second fetch returns `None`, and `model._langfuse_prompt is None` after the second.

### M6 (major) — §6 step 4: the session check cannot fail

- **Problem.** "List observations filtered by `sessionId`... every observation has the session ID" is true by construction. An observation outside the session is not in the list. Langfuse also already shows the session on adapter observations inside ADK traces, so the only observations P3 can newly bring in are the Map Maker roots.
- **Evidence.** The CLI does support the filter: `langfuse api observations list --session-id <id>`, and `--fields trace_context` returns tags (`--help` output). Langfuse today: the latest 50 adapter observations split `{'session_001': 33, '': 17}` (§6).
- **Change.** Replace the Langfuse bullet in §6 step 4 with:

  > Two minutes after the run, with `--from-start-time <start>` and no session filter:
  > `langfuse --env .env api observations list --from-start-time <start> --fields core,basic,usage,trace_context --all --json`
  > - every observation returned has `sessionId == p3-live-<UTC>` and `ADK-DocsDiver` in `tags`; list any that don't;
  > - `OpenRouterModel.generate_content` observations, counted by distinct `id`, equal `usage.calls`;
  > - those with no parent observation (Map Maker) equal `agents.map_maker.calls`;
  > - the sum of `totalCost` over distinct adapter observations equals the manifest's `usage.cost_usd` within $0.000001.
  >
  > Nothing else may write to the project during the window. The run's log must contain `Langfuse observability initialized`; if the 1-second health check fails, the tagging processor is not installed (`instrumentation.py:113-122, 144-146`). In the disposable copy `code` is `{commit: null, dirty: null}` because the copy has no `.git`; that is expected.

### m1 (minor) — F1 wording

- **Change.** Replace the second and third sentences of F1 with: "The OpenInference instrumentor copies it to `session.id` on ADK spans, so every run lands in the Langfuse session `session_001`. Map Maker calls the model outside ADK, so each Map Maker call is its own trace with no session (design V4)."

### m2 (minor) — §4.7 mutation check

- **Problem.** The outcome depends on details the plan doesn't fix. A module-level `from sdaa.src.core.run_manifest import ...` in `tests/test_openrouter_usage.py` makes the ten existing P1 tests uncollectable on the old code. `TaggingSpanProcessor(session_id=None)` raises `TypeError` on the old class, so I2 would fail too.
- **Change.** Add: "Import `run_manifest` inside the new test functions, not at module level. I2 constructs `TaggingSpanProcessor()` with no argument. Expected on the old code: `test_run_manifest.py` fails or errors as a whole; A1–A3, I1 and F1 fail; I2 and every existing test pass."

### m3 (minor) — D3: ledger state in tests that don't call `main()`

- **Problem.** A1–A3 and many existing tests call the adapter or the mock model directly. The module-level ledger carries entries between them.
- **Change.** Add to §4.7: "Add an autouse fixture to `tests/conftest.py` that calls `run_manifest.LEDGER.clear()` before each test." Add to D3: "Clear in place (`LEDGER.clear()`); never rebind the name."

### m4 (minor) — D8: `tree_hash` is not fully specified

- **Problem.** Not stated: symlinked directories, sort key, non-UTF-8 names, hidden files, a missing root, and when it runs. The design says "computed over `docs_root` at start"; the plan computes it at exit. A missing root returns the hash of nothing with count 0 (S6), which looks like a valid empty corpus.
- **Evidence.** Hashing every regular file is right: `read_file` serves any corpus file, not only Markdown (`file_ops.py:66-99`). Importing `tree_hash` loads only `sdaa.src.core.run_manifest` (S6), so H1 can import it without loading the config singleton.
- **Change.** Put the code in §4.1 as the definition:

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

  > Every regular file counts, hidden and non-Markdown files included. Empty directories don't. The wrapper computes it once, before `_run`, inside `try/except`; if `root` is not a directory or the walk fails, the manifest records `corpus: {"tree_hash": null, "file_count": null}`.

### m5 (minor) — F8, §7 decision 6: `provider` may always be null

- **Problem.** The per-call ledger is kept to record provider routing. OpenRouter's published `ChatResult` schema lists `choices, created, id, model, object, openrouter_metadata, service_tier, system_fingerprint, usage` and no `provider`. Routing data is documented under `openrouter_metadata`, enabled by the `X-OpenRouter-Metadata` request header. I could not call OpenRouter to see what it returns today.
- **Change.** Add to §6 step 4: "Report how many ledger entries have a non-null `provider`. Zero is not a failure; record it, so a follow-up can read `openrouter_metadata` instead." No code change in P3.

### m6 (minor) — D3: Gemini runs record no calls

- **Problem.** Only `OpenRouterModel` and `MockModel` record. `-m gemini --headless` writes `usage.calls: 0, unmetered_calls: 0` beside generated outputs, which reads as fully metered.
- **Change.** Add to D3: "`InstrumentedGemini` is not recorded in P3. Note for H2: a valid run needs `provider == "openrouter"` and the four audit agents plus `map_maker` present in `agents`."

### m7 (minor) — §4.7: cases with no test

- **Problem.** These would pass with a broken implementation:
  - D1: nothing checks that the run ID reaches the ADK session or `setup_instrumentation`. Leaving `session_001` passes every listed test.
  - D7: no test for `--headless --toc-only`.
  - Decision 3: no test that an interactive run writes no manifest.
- **Change.** Add to M2: "Wrap `app.setup_instrumentation` and `InMemorySessionService.create_session` with spies; both receive `session_id == "t-m2"`." Add **M10**: "`--headless --toc-only` on a new output directory: exit 0, `ToC.json` `generated`, the four audit outputs `missing`, `problems == []`." Add to M7 or a new test: "a run without `--headless` (`--toc-only`) writes no `run_manifest.json`."

  With M8–M10 and the M5 unit test, the expected count becomes baseline + 17.

## 4. Decisions in §7

| # | Result |
|---|---|
| 1 | No concern. Needs the test edits in B1 and M1. |
| 2 | No concern. The generated form matches the D1 pattern. |
| 3 | No concern. |
| 4 | **Defect: B2.** Modification times cannot tell a replayed artifact from a regenerated one. One set passed to `_run` fixes it. |
| 5 | **Narrow defect: M5.** Correct for workers. The synthesizer needs the one-line reset. |
| 6 | No concern. See m5: confirm in the live check that `provider` is populated. |
| 7 | No concern. Needs the exact definition (m4). |
| 8 | No concern on cost: P1 measured $0.0404 for the same run. The Langfuse check needs the rewrite in M6. |

## 5. Questions in §8

1. **Is the processor equivalent to baggage, and does anything bypass it?**
   - Equivalent for this process. Every span from the global provider gets both attributes: Map Maker roots, `invocation`, `agent_run`, `call_llm` and adapter spans (S1). `session.id` is accepted as well as `langfuse.session.id` (docs, Trace-Level Attributes table).
   - The instrumentor also sets `session.id` to the ADK session ID on its spans. D1 makes the two equal, so they agree.
   - The run-ID pattern is safe: ADK only strips whitespace (`in_memory_session_service.py:129`); Langfuse accepts US-ASCII under 200 characters (sessions page); the pattern allows no `/` and no leading `.`.
   - No span is created before `setup_instrumentation`: tracers are fetched at call time (`openrouter_model.py:149`), and the instrumentor is installed after the provider.
   - One bypass: if no exporter is configured, or the Langfuse health check fails, the processor is not added (`instrumentation.py:144-146`), while the Langfuse client still attaches its own exporter to the same provider when `PromptManager` starts. See M6 and §7.
2. **Does the split change behaviour?** Yes, in one existing test (B1, the `touches_nothing` test). A headless exit 1 now also creates `artifacts/` and `reports/` if they are absent, because `audit_output_paths()` creates them. Nothing else changed: with `getattr` in the mock model, 151 of 153 existing tests pass on the prototype, the other two being B1. The two tests that mock `main.config_loader` are not headless and never reach the manifest code.
3. **Are modification times safe?** On this machine (ext4, Linux 7.1) a file written right after `time.time()` never had an earlier timestamp (0 of 3000, S7). Not checked: kernels before multigrain timestamps, and filesystems with 1–2 second resolution. The question goes away with B2's change, which reads no timestamps. If modification times are kept anyway, compare `st_mtime_ns` with an unrounded `time.time_ns()`, never with the second-precision `started_at` string.

## 6. What I verified and how

All scripts ran from the session scratchpad, outside both checkouts. The disposable copy was made from this worktree with the `AGENTS.md` `tar` command; `main.py` and `tests/test_main_headless.py` were then replaced with the P2 versions (`git show 8078cd9:<file>`).

- **Baseline.** `LANGSMITH_API_KEY= LANGFUSE_PUBLIC_KEY= LANGFUSE_SECRET_KEY= python -m pytest tests -q` → `153 passed`.
- **S2, prototype.** §4.1–§4.6 applied to the copy as written: `main()`/`_run` split, `TaggingSpanProcessor(session_id)`, `_agent` in the factory, ledger in the mock model, `run_manifest.py`.
  - With `lp.name`/`lp.version` in the mock model: `14 failed, 139 passed`.
  - With `getattr`: `2 failed, 151 passed` (the two in B1).
- **S1, spans.** Real `TracerProvider`, `InMemorySpanExporter`, `GoogleADKInstrumentor`, the real adapter with a mocked OpenAI client; one direct call (Map Maker style) and one `Runner` call.

  ```
  === CURRENT CODE, ADK session_001 ===
  span                              scope                                      root  session.id   tags
  OpenRouterModel.generate_content  sdaa.src.utils.openrouter_model            True  None         lf=('ADK-DocsDiver',) ls=('ADK-DocsDiver',)
  OpenRouterModel.generate_content  sdaa.src.utils.openrouter_model            False None         lf=('ADK-DocsDiver',) ls=('ADK-DocsDiver',)
  call_llm                          openinference.instrumentation.google_adk   False session_001  lf=None ls=None
  agent_run [permissions_agent]     openinference.instrumentation.google_adk   False session_001  lf=('ADK-DocsDiver',) ls=('ADK-DocsDiver',)
  invocation [sdaa]                 openinference.instrumentation.google_adk   True  session_001  lf=('ADK-DocsDiver',) ls=('ADK-DocsDiver',)
  === P3 PROTOTYPE, run id run-x ===
  OpenRouterModel.generate_content  sdaa.src.utils.openrouter_model            True  run-x        lf=('ADK-DocsDiver',) ls=('ADK-DocsDiver',)
  OpenRouterModel.generate_content  sdaa.src.utils.openrouter_model            False run-x        lf=('ADK-DocsDiver',) ls=('ADK-DocsDiver',)
  call_llm                          openinference.instrumentation.google_adk   False run-x        lf=('ADK-DocsDiver',) ls=None
  agent_run [permissions_agent]     openinference.instrumentation.google_adk   False run-x        lf=('ADK-DocsDiver',) ls=('ADK-DocsDiver',)
  invocation [sdaa]                 openinference.instrumentation.google_adk   True  run-x        lf=('ADK-DocsDiver',) ls=('ADK-DocsDiver',)
  ```
- **S3, manifest probes.** A temporary test file in the copy, mock provider, stub prompts with `name` and `version=7`, `_real_paths`, a two-file corpus.

  ```
  fresh:              exit 0, all five outputs generated; map_maker 2 calls [null prompt]; each worker 1 call [version 7]; coordinator 1 call [report-synthesizer, 7]
  second run:         exit 0, all five reused; agents {}
  coordinator-only:   see B2
  missing prompt:     exit 1; constraints_agent.md missing; constraints_agent prompts [{name: None, version: None}]
  conftest patch kept: manifest in --output-dir: False | manifest in tmp_path/out: True
  docs root (YAML) missing: exit 1 | manifest exists: True
  KeyboardInterrupt in _run: manifest exit_code = 0   (M4 code: 1)
  ```
- **S3b.** With B2's set and M4's code in the prototype: coordinator-only gives three `reused` and the report `generated`; suite still `2 failed, 151 passed`.
- **S4, small probes.**

  ```
  OpenRouterModel      _agent declared=False: set ok   (pydantic 2.14.3 allows undeclared underscore attributes; not in model_dump)
  MockModel, ArtifactLoaderModel, InstrumentedGemini: set ok
  SystemExit().code = None; SystemExit('message').code = 'message'
  provider present: DeepInfra | absent: None
  ```
  Plus the synthesizer output quoted in M5.
- **S5.** The I1 probe quoted in M1.
- **S6.** `tree_hash('/nonexistent')` → `('e3b0c442…', 0)`; importing it loads `['sdaa', 'sdaa.src', 'sdaa.src.core', 'sdaa.src.core.run_manifest']` only.
- **S7.** 3000 files written right after `time.time()`, on `/tmp` and under `$HOME` (both ext4): none had an earlier modification time.
- **Langfuse, read-only.** `langfuse --env <main>/.env api observations list --session-id session_001 --limit 100 --fields core,basic,trace_context --json`: 100 observations, including `OpenRouterModel.generate_content`, `call_llm`, `agent_run [...]`, `invocation [sdaa]` and tool spans. `... --name OpenRouterModel.generate_content --limit 50`: `{'session_001': 33, '': 17}`.
- **Docs fetched 2026-11-12.**
  - `langfuse.com/integrations/native/opentelemetry.md`: the passage in F2; `sessionId` from `langfuse.session.id` or `session.id`; `tags` from `langfuse.trace.tags`; baggage recommended, `propagate_attributes()` the SDK alternative.
  - `.../opentelemetry/migration-to-v4.md`: "Copy these attributes to every span where they must be queryable".
  - `langfuse.com/docs/observability/features/sessions.md`: "any US-ASCII character string less than 200 characters".
  - `openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request.md`: the `ChatResult` schema and `openrouter_metadata`.
- **Project rules.** The plan complies with `AGENTS.md`: the suite runs in a disposable copy (steps 2, 5), the logbook script and `archive/PROGRESS.md` are in steps 6–7, the adapter's message and tool translation is untouched, and recording happens after the response, so provider failures still propagate (`test_provider_error_still_propagates` passes on the prototype). Key-rotation retries produce one response and one entry. The streaming branch should record its unmetered entry before iterating the stream, so an abandoned stream is still counted.
- **Leakage (V6).** Nothing new reaches the model. The manifest is not readable through `read_file` (only the bare ToC name is served from the output directory), and the run ID is used only as the ADK session key and a span attribute.

## 7. Not verified

- **What OpenRouter returns for `provider`.** Needs a paid call (m5).
- **Langfuse v4 behaviour after the 2026-11-16 cutover.** The docs say how to prepare; the live check is the test.
- **The no-exporter path.** I read the code (`instrumentation.py:144-146`, `resource_manager.py:269`) but did not run a process with Langfuse credentials and a failing health check, so I did not see which spans the Langfuse client's own exporter sends without session and tags. M6 guards the live check against it.
- **Modification times on other kernels and filesystems** (question 3).
- **The §6 live check itself**, and the OpenRouter key-usage read.
- **The mutation check.** I did not write the 13 tests; m2 is from reading the old code.
- **LangSmith.** No LangSmith export was run. The claim that its behaviour is unchanged rests on the branch being left as it is (M1).
