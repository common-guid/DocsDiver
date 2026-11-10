# Tactical Feature 1: Safe, Deterministic Documentation Access — Implementation Plan
Status: final, ready to implement · Target: ROADMAP release 0.1 (implemented after 0.3, see Q5) · Effort 1/5 · Baseline: `feature/tactical-3-refresh-and-completion` at `30dbdc9` (PR #46). Start T1 from `ADK_master` once #46 merges. If #46 changes before merge, re-check the `map_maker.py`, `output_validation.py` and `main.py` line references below.
## 0. Baseline verification
- A clean venv built from `requirements.lock` (`uv venv --python 3.14` + `uv pip install -r requirements.lock`; `google-adk==2.14.0`), running the full suite in a disposable copy (AGENTS.md procedure), gives **121 passed**. That is the 52 from the pre-T3 baseline plus the T3 tests.
  
- Empirical checks ran in that copy with a scratch script, against a temporary corpus `<tmp>/corpus` and these neighbours:
  
  - a sibling `<tmp>/corpus-private/secret.md`;
    
  - an outside directory `<tmp>/secrets/creds`;
    
  - inside the corpus, a symlinked file `leak.md -> ../secrets/creds` and a symlinked directory `linkdir -> ../secrets`.
    
  
  `file_ops._get_docs_root` and `config_loader.get_output_dir` were monkeypatched. These checks are cited as **[repro N]** below.
  
## 1. Findings: verified behavior vs. roadmap claims
| # | Topic | Verified current behavior | Roadmap claim | Verdict |
|---|---|---|---|---|
| F1 | Sibling-prefix read | `file_ops.py:30-39` builds `abspath(...)` and checks `full_path.startswith(docs_root)` (`:36`). **[repro 1, 2]** `read_file("../corpus-private/secret.md")` and the absolute form both return the secret. In-repo instance: with the code default `./docs` (`file_ops.py:6`), every file under `docs-for-testing/` passes the check. | Sibling-prefix escape | Correct |
| F2 | Sibling-prefix listing | `file_ops.py:60-66`: same prefix check. **[repro 3]** `list_files("../corpus-private")` returns `../corpus-private/secret.md` to the model. | Sibling-directory listing | Correct |
| F3 | Symlinks | `abspath` does not resolve links. **[repro 4, 5]** Reads through a symlinked file and through a symlinked directory both return outside content. `os.walk` (`file_ops.py:72-77`) does not descend into symlinked directories, but it does list symlinked *files*. **[repro 7]** `leak.md` is listed. | Symlink escape | Correct |
| F4 | **Map Maker sends escaped content to the provider before any gate** | `generate_toc` reads every listed file and sends it to the model (`map_maker.py:147-166`). **[repro 13]** The `leak.md` content reached the model. T3's gate catches the entry only *afterwards*: `toc_problems` rejects it (`output_validation.py:71-73`, **[repro 15]**), and `main.py:171-174` exits 1. | Not mentioned | **Roadmap gap.** This is the realistic vector: a cloned docs repository containing `x.md -> ~/.aws/credentials` leaks on the first run, even though T3 then fails the run. |
| F5 | Denial raises | **[repro 6]** Plain `../` and outside absolute paths are denied with `ValueError`. ADK 2.14 propagates tool exceptions out of `Runner.run_async` (T3 plan, F8), so a model-requested outside path ends the audit; headless exits 1. | Not mentioned | **Changed (Q1):** the tools return an access-denied string and log a warning. Internal callers still raise. |
| F6 | ToC redirect by basename | `file_ops.py:24-28`: any path whose *basename* equals `toc_filename` reads the output ToC. **[repro 8]** `../../anywhere/ToC.json` returns it. **[repro 9]** A corpus file named `ToC.json` is unreadable. | "Explicitly authorize the configured ToC reference" | Correct. Not an escape (always the same file), but authorization by basename is wrong. |
| F7 | Listing order | `os.walk` order is defined by the filesystem (Python documents no ordering), and results are emitted directory by directory (`file_ops.py:72-79`). Map Maker writes ToC entries in that order (`map_maker.py:163-166`). On this machine the repro happened to come out sorted; that is not guaranteed elsewhere. | "Sort for reproducible indexing" | Correct |
| F8 | Error strings | `read_file`/`list_files` return `"Error: …"` strings for not-found and read errors (`file_ops.py:41-48`, `:68-69`). Map Maker matches those prefixes (`map_maker.py:78-81`, `:147-150`), with `# ponytail:` comments that defer the fix to T1. | Not mentioned | T3 left this to T1 (`archive/PROGRESS.md:297`) |
| F9 | Two containment rules | `toc_problems` already uses `resolve()` + `is_relative_to()` (`output_validation.py:49`, `:71-73`). It rejects the escaping symlink that `read_file` accepts (repro 15 vs. 4), and it accepts internal symlinks. | Not mentioned | **Gap:** consolidate so ToC validity means readability |
| F10 | Non-Markdown reads | `list_files` lists only `.md` (`file_ops.py:74`), but `read_file` reads any file inside the root. **[repro 10]** It read a corpus-internal `.env`. | Not mentioned | See Q2 |
| F11 | Tests | `tests/test_tools.py:1-16` has 3 tests. The traversal case `../requirements.txt` is denied because `requirements.txt` is not under a prefix sibling, so no test covers F1–F3 or F6. | "Existing traversal tests do not cover these" | Correct |
| F12 | Doc drift | `docs/ARCHITECTURE_AND_DATA_FLOW.md:89` claims the tools prevent traversal "outside `docs_root` / `output_dir`". `:40` shows the coordinator reading artifacts via `read_file`, which cannot happen (only the ToC is redirected). `AGENTS.md:115` describes the defect and needs updating after the fix. | — | Fix in Step 4 |

Callers that share the rule: worker tools (`workers.py:52`, `:88`, `:124`), coordinator tools (`coordinator.py:67`), Map Maker (`map_maker.py:7`), and ToC validation (`output_validation.py:13`). Tests redirect the corpus by monkeypatching `file_ops._get_docs_root` (`test_map_maker.py:49`, `test_output_validation.py:17`, `test_main_headless.py:329`), so the new code must keep looking it up through the module at call time.
## 2. Design decisions
### D1. One authorization function
Add this to `sdaa/src/tools/file_ops.py`. It is the only containment rule in the codebase:

```python
def resolve_corpus_path(path: str) -> Path:
    """Absolute path of `path` inside the docs root. ValueError if outside the root or reached via a symlink."""
    root = Path(_get_docs_root()).resolve()
    candidate = Path(os.path.normpath(root / path))  # an absolute `path` replaces root
    resolved = candidate.resolve()
    if resolved != candidate or not resolved.is_relative_to(root):
        raise ValueError(f"Access denied: {path} is outside the documentation root or uses a symlink.")
    return resolved
```

- `is_relative_to` on resolved paths is real containment, which closes F1 and F2.
  
- `resolved != candidate` holds exactly when some component below the already-resolved root is a symlink, which closes F3.
  
- `..` is collapsed lexically _before_ the check, so `linkdir/../a.md` becomes `a.md` and is allowed. That is safe only because callers open the **returned** path, never the raw input. The kernel would read `linkdir/..` as the symlink target's parent. State this in the docstring.
  
- The root itself is resolved first, so a `docs_root` that is itself a symlink still works.
  
- The function handles missing files (`resolve()` is non-strict). Callers decide what not-found means.
  
- Standard library only; no new dependency.
  
### D2. Symlinks are rejected, not followed
Per ROADMAP T1 step 2 ("initially"), all symlinks are rejected, whether the target is inside or outside the corpus (Q3). The listing skips symlinked files and directories and logs one `logging.warning` per skipped entry, so a coverage gap is visible rather than silent (Q4). `os.walk`'s default `followlinks=False` already prevents descent; the change adds the warning and filters symlinked files.
### D3. Raising helpers for internal callers; tools return error strings
- `list_markdown(directory_path=".") -> list[str]`:
  
  - authorizes the directory through D1;
    
  - raises `FileNotFoundError` if it is not a directory;
    
  - walks it and returns **sorted** corpus-relative `.md` paths, excluding symlinks (D2).
    
  
  Sorting the whole list, not each directory, makes the ToC order independent of the filesystem (F7).
  
- `list_files` (tool) = `"\n".join(list_markdown(...))`. It keeps returning `"Error: Directory not found: …"` on `FileNotFoundError`.
  
- `read_file` (tool) authorizes through D1, then reads the file. It keeps the current strings for not-found and read errors (`file_ops.py:41-48`).
  
- Denial (F5, Q1): both tools catch the D1 `ValueError` and return `"Error: Access denied: <requested path> is outside the documentation root or uses a symlink."` They also log the same text with `logger.warning`. The message echoes only the requested path, never the resolved one. Map Maker and `toc_problems` call D1 directly, so a denial there still raises.
  
- Tool signatures and the `Args:` docstrings stay identical, so the ADK and OpenRouter tool schemas do not change (`tests/test_openrouter_tool_schema.py:77-86` guards this).
  
### D4. The ToC is authorized by exact name
`read_file` serves the output ToC only when `file_path == toc_filename` (the bare configured name, which is what agents are told to read). Every other path goes through D1, including `sub/ToC.json` and `../x/ToC.json`. This closes F6.

A corpus file named exactly `ToC.json` at the corpus root stays shadowed. That is accepted and documented.
### D5. Map Maker and ToC validation use the shared rule
- `map_maker.py:147-153`: call `list_markdown()` and delete the prefix match and its `# ponytail:` comment. The empty-corpus `ValueError` stays.
  
- `map_maker.py:78-81`: read with `resolve_corpus_path(filepath).read_text(encoding="utf-8")`, and wrap `OSError`/`UnicodeDecodeError` in `RuntimeError(f"Map Maker could not read {filepath}: {e}")`. This keeps T3's file-naming error (`test_map_maker.py` `test_generate_toc_unreadable_doc_raises_naming_file`). Delete the prefix match and its `# ponytail:` comment.
  
- `output_validation.py:49`, `:71-73`: replace the local `docs_root`/`resolve` logic with `resolve_corpus_path(path)`; a `ValueError` or a non-file becomes the existing "not a file inside the docs root" problem. A ToC is then valid exactly when every entry is readable by the tools (F9).
  

With D1–D3, a symlinked document is never listed, so it is never read or sent to a model. That closes F4 _before_ the provider call rather than at the T3 gate.
### Out of scope
- Time-of-check/time-of-use races, where a symlink is swapped in after the check (would need `openat`/`O_NOFOLLOW` walking). An attacker would need write access to the corpus during the run.
  
- Hardlinks. Git cannot create them, which closes the cloned-repository vector.
  
- An `output_dir` placed inside `docs_root`.
  
- Content-level prompt-injection defenses.
  
- Freshness (Strategic 2).
  
- Prompt fallbacks (T2).
  
## 3. Work breakdown
Each step can be committed on its own and ends with the full suite green in a disposable copy (§4).

**Step 1 — Tests first (red).**

- `tests/test_tools.py`:
  
  - Add a `tmp_corpus` fixture that monkeypatches `file_ops._get_docs_root` and `config_loader.get_output_dir`, and builds:
    
    - `corpus/` containing `a.md`, `sub/b.md` and `z.md`;
      
    - a sibling `corpus-private/secret.md`;
      
    - `outside/creds`.
      
  - Add the §4 cases.
    
  - Keep the three existing tests, which run against `docs-for-testing/`. Change `test_read_file_traversal` to assert the access-denied string instead of `ValueError` (Q1).
    
- `tests/test_map_maker.py`: add the spy-model case (a symlinked `.md` is never sent to the model, and the ToC excludes it) and the deterministic-order case.
  
- `tests/test_output_validation.py`: add a case where an internal symlink entry (target inside the corpus) is now rejected.
  

**Step 2 —** `file_ops.py`**.**

- Add `resolve_corpus_path` (D1) and `list_markdown` (D2, D3).
  
- Rewrite `read_file` and `list_files` on top of them, with the D4 ToC rule.
  
- Add a module `logger`. Remove both `startswith` checks.
  
- Expected size is about 40 changed lines.
  

**Step 3 — Wire the shared rule into its callers.**

- Apply the D5 edits in `map_maker.py` (remove both `# ponytail:` comments) and in `output_validation.py`.
  

**Step 4 — Docs.**

- Make the §6 edits.
  
- Append the phase entry to `archive/PROGRESS.md` (location per T3 Q6).
  
## 4. Test plan
| Case | Expected | Location |
|---|---|---|
| Nested valid read (`sub/b.md`); absolute path inside the root | Content returned | `test_tools.py` |
| Sibling prefix, relative and absolute (`../corpus-private/secret.md`) | Access-denied string, no content, one warning (`caplog`) | `test_tools.py` |
| Plain traversal (`../outside/creds`), absolute outside path | Access-denied string | `test_tools.py` |
| Symlinked file → outside; symlinked file → inside the corpus | Access-denied string (D2) | `test_tools.py` |
| Read through a symlinked directory | Access-denied string | `test_tools.py` |
| `resolve_corpus_path` on each escape above | `ValueError` (the internal contract Map Maker relies on) | `test_tools.py` |
| Denial message | Contains the requested path, not the resolved absolute path | `test_tools.py` |
| `linkdir/../a.md` | Returns `a.md`'s content, not anything under the symlink target (pins "open the returned path") | `test_tools.py` |
| `list_files("../corpus-private")` | Access-denied string | `test_tools.py` |
| `list_files()` with a symlinked file and a symlinked directory | Sorted `["a.md", "sub/b.md", "z.md"]`; one warning per symlink (`caplog`) | `test_tools.py` |
| `read_file("ToC.json")` | Output ToC | `test_tools.py` |
| `read_file("sub/ToC.json")`; `read_file("../../x/ToC.json")` | Corpus lookup (not-found string); access-denied string | `test_tools.py` |
| Missing file / missing directory | Unchanged `"Error: … not found"` strings | `test_tools.py` |
| Map Maker over a corpus with `leak.md -> outside` | Spy model never receives the outside content; ToC has no `leak.md`; `toc_problems == []` | `test_map_maker.py` |
| Map Maker ToC order with files created out of order | Paths sorted | `test_map_maker.py` |
| Existing T3 Map Maker tests (empty corpus, missing root, unreadable doc, model failure) | Still pass unchanged | `test_map_maker.py` |
| ToC entry that is an internal symlink | Problem reported | `test_output_validation.py` |

Symlink tests need `os.symlink`. Skip them on platforms without it (`pytest.mark.skipif(not hasattr(os, "symlink"), …)`), so Windows CI does not fail; Linux is the supported platform.

Run the suite only in the AGENTS.md disposable copy, with a clean venv built from `requirements.lock`, until the repository `.venv` is repaired.
## 5. Backward compatibility and risk
Behavior changes users will notice:

1. **Corpora that use symlinks lose those files.** Symlinked documents are no longer indexed or readable, and a warning names each one. An existing ToC that lists a symlinked entry becomes invalid, so it is regenerated on the next run; under `--skip-map-maker`/`--coordinator-only` the run exits 1.
  
2. **The ToC redirect is narrower.** Only the bare `ToC.json` reaches the output ToC. A model that asks for `output/ToC.json` gets the not-found string and can retry.
  
3. **ToC order can change on regeneration** (sorted). Reused ToCs are unaffected.
  
4. **Absolute paths through a symlinked alias of** `docs_root` **are denied**, because the lexical path differs from the resolved one. Models receive relative paths from `list_files` and the ToC, so this should be rare.
  
5. **An outside path no longer ends the audit.** The model gets an access-denied string and can continue; the denial appears as a warning in the run output (Q1). The not-found and read-error strings, tool signatures and schemas are unchanged.
  

Risks:

- **Merge friction with T2:** low. T2 touches `prompt_manager.py`, `workers.py` and `coordinator.py` instructions, not the tool lists.
  
- **False denials on unusual filesystems.** `resolve()` might normalize case or Unicode differently from `normpath`, for example on case-insensitive macOS volumes, which would make D1 reject a legitimate path. Linux is unaffected. If this is reported, compare `os.path.samefile`-style identities instead.
  
## 6. Docs
- `docs/ARCHITECTURE_AND_DATA_FLOW.md`**:**
  
  - `:89`: replace the claim with "Corpus-confined read/list tools: paths must resolve inside `docs_root` without symlinks; the only output file readable is the bare ToC name."
    
  - `:40`: remove the `read_file / artifacts` edge.
    
- `AGENTS.md:115`**:** replace the defect sentence with the D1/D2/D4 contract: resolved containment, symlinks rejected and skipped with a warning, sorted listing, ToC by exact name, and tool denials returned as an access-denied string with a logged warning (internal callers raise).
  
- `README.md:175` (`system.docs_root`) and `docs/CONFIGURATION_GUIDE.md:46`**:** add one sentence: symlinks inside the corpus are skipped; copy files in instead.
  
- `ROADMAP.md`**:** mark T1 implemented in §4 (see Q5).
  

Entry for `archive/PROGRESS.md`:

```
## Phase: Tactical 1 — Safe, Deterministic Documentation Access | <date>
### Tasks Completed
- [x] file_ops: resolve_corpus_path (resolved containment, symlinks rejected) shared by read_file, list_files, Map Maker and toc_problems.
- [x] Sorted Markdown listing; symlinks skipped with a warning; ToC readable only by its exact name.
- [x] Tool denials return an access-denied string and log a warning instead of ending the run.
- [x] Map Maker uses raising helpers; error-prefix matching removed.
- [x] Tests: sibling-prefix, traversal, symlink file/dir, ToC, ordering, Map Maker spy; suite: <N> passed (clean venv, disposable copy).
### Next Steps & Continuity
- TOCTOU and hardlinks remain out of scope; revisit before running on untrusted corpora in CI (Strategic 3).
```
## 7. Exit criteria (ROADMAP release 0.1)
1. In a clean venv from `requirements.lock`, the full suite passes in a disposable copy: at least 121 tests plus the new ones.
  
2. **Every escape is rejected.** The §4 sibling-prefix, traversal, symlink-file, symlink-directory and sibling-listing tests pass. Each tool call returns the access-denied string with no file content and logs a warning, and `resolve_corpus_path` raises `ValueError`. Ordinary nested and absolute-inside reads succeed.
  
3. **No disclosure before the gate.** The Map Maker spy test shows symlinked content never reaches a model.
  
4. **One rule.** `grep -n "startswith" sdaa/src/tools/file_ops.py` and `grep -n "ponytail: matches file_ops" sdaa/src/core/map_maker.py` both return nothing, and `output_validation.py` calls `resolve_corpus_path`.
  
5. **Deterministic indexing.** The ordering test passes.
  
6. **Tests leave user outputs untouched.** The T3 sentinel check (T3 plan §7, item 2) still gives an empty `diff`.
  
7. The docs and `archive/PROGRESS.md` are updated per §6.
  
## 8. Decisions (resolved open questions)
The maintainer reviewed each question on 2026-11-10. The plan above reflects these decisions.

| # | Question | Decision | Rationale |
|---|---|---|---|
| Q1 | When a model requests a path outside the corpus, should the tool raise (ending the audit) or return an error string the model can recover from? | **Return an error string, and log a warning.** `read_file`/`list_files` catch the D1 `ValueError` and return `"Error: Access denied: <requested path> is outside the documentation root or uses a symlink."` They also call `logger.warning` with the same text. | A denial discloses nothing, so it fails closed either way. Returning the error means one hallucinated `../` no longer kills a long live run. The warning keeps escape attempts, such as prompt injection from a corpus document, visible in the run output. The message echoes only the path the model asked for, never a resolved absolute path. Map Maker and `toc_problems` call D1 directly, so a denial there still fails. |
| Q2 | Should `read_file` be limited to `.md` files, matching `list_files`? | **No.** | Docs link to specs and examples (`.yaml`, `.json`, `.txt`). Containment, not file extension, is the security boundary; a sensitive file inside `docs_root` is a configuration choice. |
| Q3 | Should symlinks whose target is _inside_ the corpus be allowed? | **No; reject all symlinks for now** (ROADMAP: "initially"). | One rule, no aliasing, and no duplicate ToC entries for the same file. Relaxing it later means dropping the `resolved != candidate` clause in D1 (keeping `is_relative_to`), filtering the listing on the resolved target, and deduping by resolved path: about 5 lines plus tests. |
| Q4 | When the listing finds a symlink, should it warn and continue, or fail the run? | **Warn and continue.** | A corpus with an unrelated symlink, such as a `latest -> v2` directory, should still be auditable, and the warning names what was skipped. |
| Q5 | ROADMAP numbers T1 as release 0.1, but T3 shipped first as 0.3. Should the releases be renumbered? | **No. Keep the labels as feature identifiers, and note the actual order in `archive/PROGRESS.md` and the ROADMAP §4 status.** | There are no published release tags to keep consistent, and renumbering churns every plan's references. If releases are tagged later, label them by the order shipped from then on. |
