# Plan: Eval Phase P2, Path Overrides

Status: ready to implement · Created 2026-11-12 · Base: `ADK_master` · Design: `05_EVAL_DESIGN.md` §3.6 ("P2, overrides") and §4 · No Fable review (small, mock-only, no spend; `docs/plans/2026-11-12_TASKS.md`)

## 1. Goal

Add two CLI flags to `main.py`:
- `--docs-root <dir>`: the corpus to audit for this run.
- `--output-dir <dir>`: where this run writes the ToC, artifacts and report.

Both override the values in `sdaa/config/config.yaml` for one run, without editing it. The eval runner (phase H2) stages each corpus in a temporary directory and needs both flags. Every later D-phase depends on them.

**Change from the design:** the design's third P2 flag, `--set <key>=<value>`, is deferred (operator decision, 2026-11-12). No v0 phase uses it: the baseline runs the committed config. It will be built when the first comparison run is planned, once we know whether it varies the model, the prompt version or both.

## 2. Facts checked on 2026-11-12

- **F1.** `ConfigLoader` (`sdaa/src/core/config_loader.py`) is an import-time singleton. `config_loader.config` returns the loaded dict itself, so changing `config_loader.config["system"][...]` is seen by every later `get`.
- **F2.** Every path is read through `config_loader` at call time, not at import:
  - docs root: `file_ops._get_docs_root()` (`sdaa/src/tools/file_ops.py:10`);
  - output: `get_output_dir`, `get_reports_dir` and `get_artifacts_dir`.
  The callers are `main.py:132`, `map_maker.py:137`, `reporting.py:31-58`, `output_validation.py:28-29`, `coordinator.py:78` and `mock_model.py:71-147`. Setting the two keys in `main()` before any other work therefore covers every reader. No code writes outside these directories (`grep` for `open(..., "w")` in `sdaa/` and `main.py`).
- **F3.** `get_output_dir` creates the directory (`os.makedirs`). A relative path resolves against the working directory, the same as a relative YAML value.
- **F4.** Usage errors already exit 2 through `parser.error`, before any I/O (`main.py:113-121`).
- **F5.** If the output directory is inside the docs root, the worker artifacts (`.md`) sit inside the corpus. A later Map Maker run would index the audit's own findings, and an eval would grade a contaminated run. No check prevents this today.
- **F6.** The existing headless tests isolate output by monkeypatching `get_output_dir` and related methods (`tests/test_main_headless.py:49`, `_isolate_output_dirs`). The new tests must **not** use that helper, because it would bypass the code under test.
- **F7.** A mock run of the real Map Maker works offline: the mock model generates and Map Maker's prompt is inline (verified by the `--toc-only` step in `docs/plans/REMOVE_VENDOR_TEST_DOCS.md`). The worker and synthesis prompts are stubbed by the autouse `_stub_prompts` fixture in `tests/test_main_headless.py`.
- **F8a. Prototype, 2026-11-12.** §4.1 applied to a disposable copy:
  - `-m mock --toc-only --docs-root corpus --output-dir out` (relative paths) exited 0, indexed exactly the three corpus files and wrote only `out/ToC.json`;
  - a missing docs root, an output directory inside the docs root and a file as docs root each exited 2 with the §4.1 message and created nothing.
- **F8.** On the old code, any unknown flag also exits 2 ("unrecognized arguments: --docs-root ..."). So a test that checks only the exit code would pass without the change. Every test below also checks a message that only the new code prints.

## 3. Design

- **D1. Apply, then validate.** Right after the existing flag-conflict checks in `main()`, and before `RichUI(...)` and `setup_instrumentation()`:
  1. write each given flag's absolute path into `config_loader.config["system"]`;
  2. validate the effective paths, whether they came from flags or YAML.
  A failure calls `parser.error(...)`, which exits 2 before anything is created.
- **D2. Rules:**
  - `--docs-root`, when given, must be an existing directory. A docs root that comes from YAML keeps today's behaviour: Map Maker fails with exit 1.
  - The output directory must not exist as a non-directory.
  - The output directory must not be the docs root or inside it (F5). This applies to YAML values too. The default config (`docs-for-testing`, `output`) passes.
- **D3. Paths are stored absolute** (`os.path.abspath(os.path.expanduser(...))`). A later `chdir` can't move them, and the P3 manifest can record exactly where the run read and wrote.
- **D4. All modes.** The flags apply to interactive, `--toc-only`, `--headless` and every other mode. They don't interact with the refresh flags.
- **D5. Not in scope:**
  - `--set` and model overrides (deferred, §1);
  - `system.reports_dir` and `system.artifacts_dir`, which stay subdirectory names under the output directory;
  - deciding whether reused outputs are fresh. A valid ToC or artifact already in `--output-dir` is still reused. The runner (H2) must pass a new, empty output directory for each run. Record this in the H2 plan.

## 4. Changes

### 4.1 `main.py`

Add the two arguments after `--refresh-audit`:

```python
parser.add_argument("--docs-root", help="Directory of Markdown docs to audit for this run (overrides system.docs_root)")
parser.add_argument("--output-dir", help="Directory for this run's ToC, artifacts and report (overrides system.output_dir)")
```

Add `from pathlib import Path` to the imports (`main.py` doesn't import it today), and this function above `main()`:

```python
def apply_path_overrides(parser, args):
    """Write --docs-root/--output-dir into the config, then validate the effective paths (exit 2 on error)."""
    system = config_loader.config.setdefault("system", {})
    if args.docs_root is not None:
        system["docs_root"] = os.path.abspath(os.path.expanduser(args.docs_root))
    if args.output_dir is not None:
        system["output_dir"] = os.path.abspath(os.path.expanduser(args.output_dir))

    docs = Path(os.path.abspath(config_loader.get("system.docs_root", "./docs"))).resolve()
    out = Path(os.path.abspath(os.path.expanduser(config_loader.get("system.output_dir", ".") or "."))).resolve()
    if args.docs_root is not None and not docs.is_dir():
        parser.error(f"--docs-root {args.docs_root}: does not exist or is not a directory")
    if out.exists() and not out.is_dir():
        parser.error(f"output directory {out}: exists and is not a directory")
    if out == docs or out.is_relative_to(docs):
        parser.error(f"output directory {out} is inside the docs root {docs}; the audit would read its own outputs")
```

The expressions mirror the two readers: `docs` matches `file_ops._get_docs_root()` and `out` matches `get_output_dir()`.

Call `apply_path_overrides(parser, args)` immediately after the last `parser.error` conflict check (`main.py:121`).

### 4.2 Tests: `tests/test_main_headless.py`

Add one helper and five tests. The autouse `_stub_prompts` fixture already applies. Don't use `_isolate_output_dirs` or `_seed` (F6).

```python
def _pin_system_paths(monkeypatch):
    """Restore system.docs_root/output_dir after the test; main() writes them into the singleton."""
    system = config_loader.config["system"]
    for key in ("docs_root", "output_dir"):
        monkeypatch.setitem(system, key, system[key])
```

`monkeypatch.setitem` records the original value and restores it at teardown, even though `main()` overwrites it.

| # | Test | Setup | Assert |
|---|---|---|---|
| T1 | `test_path_flags_route_whole_audit` | `tmp_path/corpus/` holds copies of `docs-for-testing/auth.md` and `billing.md` plus a new `only_here.md` (a heading and two sentences). `monkeypatch.chdir(tmp_path)`. Record the SHA-256 of `sdaa/config/config.yaml`, using the path from `config_loader`'s module (not the working directory). Run `_run(monkeypatch, "--headless", "--docs-root", "corpus", "--output-dir", "out")` with **relative** paths and the real Map Maker. | `app.main()` returns without `SystemExit` (success returns `None`, as in `test_headless_mock_audit_writes_all_outputs`). The `out/ToC.json` paths are exactly `auth.md`, `billing.md`, `only_here.md`. The three files in `out/artifacts/` and `out/reports/Security_Threat_Model.md` exist and are nonempty. Every file under `tmp_path` is under `corpus/` or `out/`, so nothing went to a default `output/`. The `config.yaml` hash is unchanged. `config_loader.get("system.output_dir")` equals `str(tmp_path / "out")`, so the stored path is absolute. |
| T2 | `test_docs_root_missing_exits_2` | `--docs-root tmp_path/nope --output-dir tmp_path/out` | `SystemExit` code 2. `capsys` stderr contains `does not exist or is not a directory`. `tmp_path/out` does not exist. |
| T3 | `test_docs_root_is_file_exits_2` | `--docs-root` names an existing file | Code 2. Same message. |
| T4 | `test_output_dir_inside_docs_root_exits_2` | `--docs-root tmp_path/corpus` (exists) and `--output-dir tmp_path/corpus/out` | Code 2. stderr contains `is inside the docs root`. `tmp_path/corpus/out` does not exist. |
| T5 | `test_output_dir_is_file_exits_2` | `--output-dir` names an existing file; the docs root is valid | Code 2. stderr contains `exists and is not a directory`. |

Every test calls `_pin_system_paths(monkeypatch)` first. T2–T5 use the same `_run` helper with `--headless`.

If T1 fails because the mock Map Maker's ToC is invalid, stop and report it; don't fake `generate_toc`. The point of T1 is that the real indexer read the given corpus.

**Mutation check:** run the five new tests against the pre-change `main.py`. T1 must fail (unrecognized arguments). T2–T5 must fail on the message assertion (F8). Report the result in the PR.

### 4.3 Documentation

- `AGENTS.md:34`: replace "(no CLI path overrides)" with "(`--docs-root`/`--output-dir` override the two paths for one run; the output directory may not be inside the docs root)".
- `docs/CONFIGURATION_GUIDE.md` §4 flag table: add a row for each flag (value: a path; default: the YAML value). Note the exit-2 cases.
- `README.md`: add both flags to the CLI flag table near line 137, and one example under the usage examples near line 152: `python main.py --headless --docs-root /path/to/docs --output-dir /tmp/run1`.

Don't edit `05_EVAL_DESIGN.md`; the planner records the `--set` deferral there.

## 5. Steps

1. **Branch:** from an up-to-date `ADK_master`, create `feat/eval-p2-path-overrides`.
2. **Baseline:** run the full suite in a disposable copy, using the command in `AGENTS.md` ("Tests and syntax checks"), and record the pass count. Expected: 148.
3. **Implement** §4.1 and §4.2.
4. **Mutation check** (§4.2), in a disposable copy containing the new tests and the old `main.py`.
5. **Verify:**
   - `python -m compileall -q main.py sdaa tests scripts`;
   - the full suite in a fresh disposable copy: baseline + 5 passed, 0 failed.
6. **Docs:** §4.3, plus a phase entry in `archive/PROGRESS.md` in the format of the "Eval P1" entry.
7. **Log:**

   ```bash
   bash .agents/skills/dev-logbook/scripts/log.sh "Add --docs-root and --output-dir (eval P2)" "main.py can point one run at any corpus and output directory without editing config.yaml, which the eval runner needs; an output directory inside the docs root is refused because the audit would index its own findings."
   ```

8. **Commit and open a PR** against `ADK_master`. Title: `feat(evals): --docs-root and --output-dir overrides (eval P2)`. The body states:
   - baseline and final pass counts;
   - the mutation-check result;
   - the `--set` deferral, with a pointer to this plan's §1.

   Don't merge. No live model calls and no spending.

## 6. Acceptance criteria

- [ ] T1–T5 pass, and all five fail against the old `main.py`.
- [ ] Full suite passes in a disposable copy: baseline + 5.
- [ ] A mock headless run writes only to the given output directory. `config.yaml` is unchanged.
- [ ] An output directory inside the docs root exits 2 before anything is created.
- [ ] `AGENTS.md`, `CONFIGURATION_GUIDE.md`, `README.md` and `archive/PROGRESS.md` are updated. Logbook entry added through the script.
- [ ] PR open against `ADK_master`, not merged.
