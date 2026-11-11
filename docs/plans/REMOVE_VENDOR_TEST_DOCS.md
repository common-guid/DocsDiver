# Plan: Remove Vendor-Derived Test Docs

Status: implemented, PR #48 merged 2026-11-11 (`166764e`; 137 tests passed before and after) · Created 2026-11-11 · Base: `ADK_master` · Decision: operator, 2026-11-11 (`docs/plans/evals/05_EVAL_DESIGN.md` §6, decision 7)

## Goal

Remove `docs-for-testing/api/` from the repository. Its 12 tracked files are a third-party vendor's public API documentation with the product name replaced by "company". The repository is public, and the eval design (brief C5) says nothing derived from that vendor's docs is kept in it.

After this change, `docs-for-testing/` holds only its four small synthetic files: `api.md`, `auth.md`, `billing.md` and `roles.md`.

## Facts checked on 2026-11-11

- `git ls-files docs-for-testing` lists 16 files: the 4 synthetic ones and the 12 under `api/`.
- The files under `api/` hold only 3 distinct contents; the other 9 files are exact copies.
- They were added in commits `8600a18` (2026-01-23) and `0e0ad24` (2026-01-31).
- `docs-for-testing/api.md` (top level) is synthetic. **Keep it.**
- No code depends on `api/`:
  - `tests/`, `sdaa/`, `main.py` and `scripts/` contain no reference to `docs-for-testing/api/`, `api-overview` or `api-reference`.
  - Tests that read the real corpus use only `auth.md` and `billing.md` (`tests/test_tools.py:14`, `:26-29`; `tests/conftest.py:39`).
  - `tests/test_map_maker.py:25` asserts only that the ToC has at least one entry.
- Prose that mentions `docs-for-testing/` (`README.md`, `AGENTS.md`, `docs/CONFIGURATION_GUIDE.md`, `sdaa/config/config.yaml`) describes the directory, not `api/`. It stays correct.
- References in `docs/plans/evals/*.md` and `.checkpoints/` are historical records. **Do not edit them.**

## Scope

**In:**
- delete `docs-for-testing/api/`;
- show the suite still passes;
- log the change.

**Out:**
- **Rewriting git history** (for example with `git filter-repo`) or force-pushing. The files stay in history and in existing forks; the operator has not decided on a rewrite.
- **Other branches.** Stale remote branches still contain the files. Branch cleanup is a separate task.
- **New synthetic API docs.** No test needs them.
- **Any other file in `docs-for-testing/`.**

## Steps

1. **Branch.** From an up-to-date `ADK_master`, create `chore/remove-vendor-test-docs`.

2. **Baseline.** Before changing anything, run the full suite in a disposable copy using the command in `AGENTS.md` ("Tests and syntax checks"), and record the pass count.
   - You need a virtual environment with `requirements.lock` installed.
   - Never run the full suite in the repository root: it deletes `output/`.

3. **Delete.**

   ```bash
   git rm -r -q docs-for-testing/api
   git ls-files docs-for-testing
   ```

   Expected listing: exactly `docs-for-testing/api.md`, `auth.md`, `billing.md`, `roles.md`.

4. **Look for stray references.**

   ```bash
   git grep -n "docs-for-testing/api/\|api-overview\|api-reference" -- . ':!docs/plans/evals' ':!.checkpoints' ':!docs/llms-txt' ':!llms.txt' ':!docs/plans/REMOVE_VENDOR_TEST_DOCS.md'
   ```

   Expected: no output. If anything turns up, stop and report it; don't edit around it.

5. **Verify.**
   - **Syntax:** `python -m compileall -q main.py sdaa tests scripts`.
   - **Full suite:** run it in a fresh disposable copy, the same way as the baseline. The pass count must equal the baseline.
   - **Mock index of the smaller corpus:** run this in the disposable copy, not the repository root, because it writes `output/ToC.json`:

     ```bash
     LANGSMITH_API_KEY= LANGFUSE_PUBLIC_KEY= LANGFUSE_SECRET_KEY= \
         python main.py -m mock --toc-only --no-rich
     python -c "import json; print(sorted(f['path'] for f in json.load(open('output/ToC.json'))['files']))"
     ```

     Expected: `['api.md', 'auth.md', 'billing.md', 'roles.md']`. This makes no network or model calls: the mock model generates, and Map Maker's prompt is inline.

6. **Log.** Run the logbook script, as `AGENTS.md` requires:

   ```bash
   bash .agents/skills/dev-logbook/scripts/log.sh "Remove vendor-derived test docs" "Deleted docs-for-testing/api/ (12 files of third-party vendor API docs with the name replaced, 9 duplicates) from the public repo. The default test corpus is now the four synthetic files; history is unchanged."
   ```

7. **Commit and open a PR** against `ADK_master`.
   - **Commit message:** `chore: remove vendor-derived docs from docs-for-testing`.
   - **PR body:**
     - what was removed and why (one paragraph, without naming the vendor);
     - the baseline and post-change pass counts;
     - the mock ToC listing;
     - a line saying history was not rewritten.

   Don't merge; the operator reviews.

## Acceptance criteria

- [ ] `git ls-files docs-for-testing` lists exactly the four synthetic files.
- [ ] The stray-reference grep in step 4 prints nothing.
- [ ] The full suite passes in a disposable copy, with the same count as the baseline.
- [ ] The mock `--toc-only` run indexes exactly the four files.
- [ ] Logbook entry added through the script.
- [ ] PR open against `ADK_master`, not merged, history untouched.

## Note for the operator

Deleting a directory on a branch doesn't remove it from git history, from other branches or from forks. If you later decide to rewrite history, that needs `git filter-repo` over every branch and a force-push. It is destructive and separate from this plan.
