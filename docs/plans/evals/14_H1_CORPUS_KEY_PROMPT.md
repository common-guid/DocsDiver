# Prompt: Implement Eval Phase H1, Corpus and Key Tools (for an external agent)

Status: ready to run · Created 2026-11-12 · Design: `05_EVAL_DESIGN.md` §3.2–§3.4, §3.6, §4 (H1)

## How to run it

- **Where:** a fresh session started in `/home/guid/projects/DocsDiver`. You create your own worktree (step 1); you don't edit the main checkout.
- **What to paste:** everything below the line.

---

You are implementing eval phase H1 of DocsDiver. You write offline Python tools and their tests. Nothing in H1 calls a model or spends money.

## Context

- DocsDiver audits a Markdown documentation corpus with LLM agents. The eval harness, which will live in a new `evals/` package, will grade those audits against an **answer key** of known issues, some of them **planted** into a copy of the corpus.
- H1 builds three offline commands, plus a small synthetic example corpus and key that the tests use:
  - `python -m evals corpus verify <dir>`: checks that a corpus tree is safe to audit;
  - `python -m evals key check --key <file> --clean <dir>`: validates an answer key against the clean corpus;
  - `python -m evals corpus build --key <file> --clean <dir> --seeded <dir> [--variants <file>]`: writes the seeded corpus by applying the key's approved plants, and records both tree hashes.
- Read `docs/plans/evals/05_EVAL_DESIGN.md` §3.2, §3.3, §3.4 and the "Modules" and "Key leakage" parts of §3.6 before you start. **This prompt is the spec:** where it is more specific than the design, follow this prompt.
- The real corpus (Hex's public docs) and the real key live in a private vault. **Never read, copy or mention anything from `~/CoS_brain`.** The example in this prompt is invented ("Acme Notebooks"); use it verbatim.

## Rules

- Work only in your worktree, on branch `feat/eval-h1-corpus-key`, based on `origin/ADK_master` (`c1ef121` or later, which includes the Langfuse v4 merge, PR #52).
- Create or edit only the files listed under "Files". Don't touch `sdaa/`, `main.py`, `tests/conftest.py` or any existing test.
- Add no dependencies. Use the standard library and PyYAML (already pinned at 6.0.3).
- Use the repo venv: `/home/guid/projects/DocsDiver/.venv/bin/python`. Always run tests with `python -m pytest`, never bare `pytest`.
- **Run the full suite only in a disposable copy**, as `AGENTS.md` describes. Run the copy command from your worktree root. Focused runs of the new test files are fine in the worktree, because they write only to `tmp_path`.
- Commit on your branch. **Don't push, and don't open a PR**: the planner reviews your work and opens the PR.
- **Stop and report**, without working around it, if:
  - `from sdaa.src.core.run_manifest import tree_hash` fails, or `tree_hash(root)` doesn't return `(hex_digest, file_count)`;
  - the baseline full suite (step 2) isn't `173 passed`;
  - the spec below needs a change to a file not listed under "Files".
  
  A line number in this prompt that has drifted is **not** a reason to stop. Find the code by name and continue.

## Steps

1. `git -C /home/guid/projects/DocsDiver fetch origin && git -C /home/guid/projects/DocsDiver worktree add /home/guid/projects/DocsDiver-h1 -b feat/eval-h1-corpus-key origin/ADK_master`. Then `cd /home/guid/projects/DocsDiver-h1`. Copy this prompt in: `cp /home/guid/projects/DocsDiver/docs/plans/evals/14_H1_CORPUS_KEY_PROMPT.md docs/plans/evals/`.
2. Run the baseline full suite in a disposable copy. Expect `173 passed`.
3. Write the example corpus and key ("Example data" below), exactly as given.
4. Write `evals/corpus.py`, `evals/key.py`, `evals/__init__.py` and `evals/__main__.py` ("Spec" below).
5. Write the tests ("Tests" below). Run them in the worktree: `/home/guid/projects/DocsDiver/.venv/bin/python -m pytest tests/test_evals_corpus.py tests/test_evals_key.py -q`.
6. Run the mutation checks ("Mutation checks" below). Revert each mutation before the next one.
7. Run the full suite in a disposable copy. Expect `173 + <your new test count> passed`.
8. Run `/home/guid/projects/DocsDiver/.venv/bin/python -m compileall -q evals tests`.
9. Update the docs ("Docs" below), then commit everything in one commit. End the commit message with `Co-Authored-By:` for yourself if your harness asks for it.
10. Run the logbook script from the worktree: `bash .agents/skills/dev-logbook/scripts/log.sh "Add eval H1 corpus and key tools" "<1–2 sentences>"`. Commit the `LOGBOOK.md` change on the same branch.
11. Reply in the "Report" format.

## Files

| Path | New or edit | What |
|---|---|---|
| `evals/__init__.py` | new | One-line docstring. Nothing else. |
| `evals/__main__.py` | new | The CLI. |
| `evals/corpus.py` | new | Verify, Markdown sections, build. |
| `evals/key.py` | new | Key load, hash, check, approved edits. |
| `evals/examples/acme/clean/**.md` | new | The 4 example pages. |
| `evals/examples/acme/key.yaml` | new | The example key. |
| `tests/test_evals_corpus.py` | new | Corpus tests. |
| `tests/test_evals_key.py` | new | Key and CLI tests. |
| `docs/plans/evals/14_H1_CORPUS_KEY_PROMPT.md` | new (copied) | This prompt. |
| `AGENTS.md`, `archive/PROGRESS.md`, `LOGBOOK.md` | edit | See "Docs". `LOGBOOK.md` only through the script. |

**Two deviations from the design, on purpose:**

- **Tests go in `tests/test_evals_*.py`, not `tests/evals/`.** `tests/` has no `__init__.py`, so pytest puts `tests/` on `sys.path`. A `tests/evals/` directory would then compete with the real `evals` package for the name `evals`. Don't create `tests/evals/`.
- **`evals/__main__.py` lands in H1** (the design lists it under H2), because H1's commands need it. **`key check` takes `--clean`**, because rule 2 needs the corpus text.

## Example data

Use these files verbatim. They are invented and must stay free of the words "planted", "seeded" and "intentional".

`evals/examples/acme/clean/admin/roles.md`:

~~~~markdown
# Roles

Acme Notebooks has three workspace roles. An Admin assigns roles from **Settings > Members**.

## Admin

Admins manage members, billing and workspace settings. Admins can create public links and set their expiry.

## Editor

Editors can create, edit and delete notebooks in the projects they belong to. Editors can share a notebook with other workspace members. Editors cannot create public links.

## Viewer

Viewers can open and comment on notebooks shared with them. Viewers cannot edit or delete notebooks.
~~~~

`evals/examples/acme/clean/sharing/links.md`:

~~~~markdown
# Public links

A public link lets anyone with the URL view a notebook without signing in.

## Creating links

Open a notebook and select **Share > Public link**. The link shows the latest published version of the notebook.

## Link expiry

Only Admins can create public links. Public links expire after 30 days.

An Admin can revoke a public link at any time from **Settings > Links**. Revoking a link stops new visits to the URL.
~~~~

`evals/examples/acme/clean/billing/invoices.md`:

~~~~markdown
# Invoices

Acme issues an invoice on the first day of each billing period.

## Viewing invoices

Admins can view and download every invoice from **Settings > Billing**. Other roles cannot see invoices.

## Editing invoices

An Admin can change the billing address and tax ID on an open invoice. Changes appear on the PDF within a few minutes.

## Payment

Invoices are paid automatically with the card on file. A paid invoice is marked **Paid** and a receipt is emailed to every Admin.
~~~~

`evals/examples/acme/clean/api/tokens.md` (the `# List ...` line is a shell comment inside a code fence, not a heading; a test depends on it):

~~~~markdown
# API tokens

API tokens let scripts call the Acme API as the user who created the token.

## Creating a token

Go to **Settings > API tokens** and select **New token**. Copy the token when it is shown; it is not shown again.

```bash
# List the notebooks you can see
curl -H "Authorization: Bearer $ACME_TOKEN" https://api.acme.example/v1/notebooks
```

## Token scopes

A token has the same access as its owner. A token can be limited to read-only access when it is created.

## Expiry

Tokens expire after 90 days. An Admin can revoke any token from **Settings > Members**.
~~~~

`evals/examples/acme/key.yaml`:

```yaml
key_id: acme-example
key_version: 2
snapshot_id: acme-2026-01-01
tags_version: 1
items:
  - id: PL-01
    kind: planted
    status: approved
    tags: [permission-gap, contradiction]
    variants: [seeded]
    difficulty: 3
    locations:
      - {path: admin/roles.md, section: "Editor"}
      - {path: sharing/links.md, section: "Link expiry"}
    what: >-
      roles.md says Editors cannot create public links. links.md says any
      Editor can create a public link that never expires.
    why: >-
      If links.md is the real behaviour, an Editor can publish a notebook
      outside the workspace with no admin control and no expiry.
    plant:
      - path: sharing/links.md
        find: "Only Admins can create public links. Public links expire after 30 days."
        replace: "Any Editor can create a public link. Public links do not expire."
    added_in: 2
  - id: PL-02
    kind: planted
    status: draft
    tags: [invariant-gap]
    variants: [seeded]
    difficulty: 1
    locations: [{path: api/tokens.md, section: "Expiry"}]
    what: Tokens never expire unless their owner sets a date.
    why: A leaked token stays valid indefinitely.
    plant:
      - path: api/tokens.md
        find: "Tokens expire after 90 days."
        replace: "Tokens do not expire unless their owner sets a date."
    added_in: 2
  - id: NA-02
    kind: native
    status: approved
    tags: [trust-boundary-gap]
    variants: [clean, seeded]
    locations: [{path: sharing/links.md, section: "Link expiry"}]
    what: >-
      The page does not say whether revoking a public link ends access for
      visitors who already have the notebook open.
    why: An outside visitor may keep reading a notebook after the link is revoked.
    interaction: {plant: PL-01, effect: none}
    source: {run: r-20260101-01, finding: B-F02}
    added_in: 1
  - id: NA-03
    kind: native
    status: approved
    tags: [invariant-gap]
    variants: [clean, seeded]
    locations: [{path: billing/invoices.md, section: "Editing invoices"}]
    what: The page never says whether a paid invoice can be edited.
    why: Nothing in the docs stops a change to a paid invoice, so it must be tested.
    source: {run: r-20260101-01, finding: C-F07}
    added_in: 1
  - id: NA-04
    kind: native
    status: draft
    tags: [permission-gap]
    variants: [clean, seeded]
    locations: [{path: api/tokens.md, section: "Token scopes"}]
    what: The page does not say whether a token keeps its access after its owner's role is lowered.
    why: A demoted user's scripts may keep admin access.
    added_in: 2
  - id: RJ-01
    kind: invented
    status: approved
    tags: [permission-gap]
    variants: [clean, seeded]
    locations: [{path: admin/roles.md, section: "Viewer"}]
    what: Viewers can delete notebooks.
    source: {run: r-20260101-01, finding: P-F03}
    note: roles.md says Viewers cannot delete notebooks.
    added_in: 1
```

Note how the example exercises the rules: NA-02 sits in the section PL-01 edits, so it carries `interaction`. NA-04 is on the same page as PL-02 but in a different section, so it needs none. PL-02 is a draft, so the build does not apply it.

## Spec

### Import direction (required for H2)

H2 adds `evals/run.py`, which must not import `key.py`, and a test will check that by running `python -m evals run` in a subprocess. So:

- `corpus.py` imports only the standard library and `sdaa.src.core.run_manifest`. **It never imports `key.py`.**
- `key.py` may import `corpus.py`.
- `__main__.py` imports **nothing from `evals` at module level**. Each subcommand handler imports what it needs inside the function.

### `evals/corpus.py`

```python
from sdaa.src.core.run_manifest import tree_hash   # the single tree-hash definition; do not copy it
```

- `class CorpusError(Exception)`: carries `problems: list[str]`; `str()` joins them with newlines.
- `verify(root) -> list[str]`: returns the problems, an empty list when the tree is clean. Walk with `os.walk(root)`, which doesn't follow symlinks. A problem for each of:
  - `root` missing or not a directory (return just that problem);
  - any symlink, file or directory (report it, then skip it: never read through it, so it can't also count as a duplicate);
  - any file whose name doesn't end in `.md`, including hidden files such as `.DS_Store`;
  - two or more files with identical bytes (one problem per group, naming every path);
  - no `.md` files at all.
  
  Report paths relative to `root`, with `/` separators, sorted, so the output is stable.
- `headings(text) -> list[str]` and `section_at(text, offset) -> str`. A heading is a line matching `^ {0,3}#{1,6}\s+(.*?)(?:\s+#+)?\s*$` that is **outside a code fence**. A line whose stripped form starts with ```` ``` ```` or `~~~` toggles the fence state. `section_at` returns the text of the last heading that starts before `offset`, or `""` when there is none. Mark the simplification: `# ponytail: ATX headings and simple fence toggling only; no setext headings or fence-length matching`.
- `build(clean, seeded, edits) -> dict`. `edits` is a list of `(item_id, path, find, replace)` tuples. It does everything in memory first and writes only when every check passes. Otherwise it raises `CorpusError` with **all** problems:
  1. `verify(clean)` must return no problems.
  2. `seeded` must not exist. Refuse it if it resolves to `clean`, is inside `clean`, or contains `clean`. The operator deletes an old seeded tree by hand; the tool never deletes.
  3. Read every clean file as bytes, then decode as UTF-8. Never use text mode: that would rewrite line endings.
  4. For each edit: `path` must be a clean file, and `find` must occur **exactly once** in the **original** clean text. Report zero and two-or-more separately, naming the item ID and path.
  5. Collect each edit's span `(start, start + len(find))` per file. Two spans in one file that overlap are a problem (spans that only touch are fine).
  6. Apply each file's edits from the last span to the first, against the original text.
  7. Write every file under `seeded` (`os.makedirs(..., exist_ok=True)` for parents). Edited files are encoded as UTF-8; unedited files are copied byte for byte.
  8. Check that the seeded tree has exactly the same relative file list as the clean tree.
  
  It returns `{"clean": {"tree_hash": h, "files": n}, "seeded": {"tree_hash": h, "files": n}}`, both computed with `tree_hash`.

### `evals/key.py`

Constants:

```python
TAGS_VERSION = 1
AREA_TAGS = {"permission-gap", "invariant-gap", "trust-boundary-gap"}
CROSS_TAGS = {"contradiction"}
KINDS = {"planted": "PL", "native": "NA", "incidental": "IN", "invented": "RJ", "disputed": "DS"}
STATUSES = {"draft", "approved", "retired"}
EFFECTS = {"none", "hidden", "altered"}
LABEL_WORDS = re.compile(r"\b(planted|seeded|intentional(ly)?)\b|\b(PL|NA|IN|RJ|DS)-\d+\b", re.I)
```

Functions:

- `key_hash(path) -> str`: SHA-256 hex of the file's bytes. This hash, not `key_version`, is the version comparisons use.
- `load(path) -> dict`: `yaml.safe_load`. If the result isn't a mapping, raise `ValueError`.
- `check(key: dict, clean_dir) -> list[str]`: every problem, sorted by item order, each starting with the item ID (or `header`). An empty list means valid.
- `approved_edits(key) -> list[tuple]`: `(id, path, find, replace)` for every edit of every item with `kind: planted` and `status: approved`, in key order.

What `check` enforces. "Integer" means `type(x) is int`, so `true` is rejected.

**Header**
- Keys are exactly `key_id` (non-empty string), `key_version` (integer ≥ 1), `snapshot_id` (non-empty string), `tags_version` (integer equal to `TAGS_VERSION`) and `items` (a list). Unknown keys are problems.

**Every item (schema; retired items included)**
- `id`: matches `^(PL|NA|IN|RJ|DS)-\d{2,}$`, its prefix matches `KINDS[kind]`, and it is unique.
- `kind` is in `KINDS`; `status` is in `STATUSES`.
- `tags`: a list with no duplicates and no unknown tags. It has one or two area tags. `contradiction` never appears alone.
- `variants`: a non-empty list of `clean`/`seeded` with no duplicates.
  - `planted` and `incidental` must be exactly `[seeded]`.
  - A native with `interaction.effect` of `hidden` or `altered` must be exactly `[clean]`.
- `locations`: 1 or 2 mappings, each with exactly `path` and `section` (strings). A `path` is relative, uses `/`, ends in `.md`, and has no `..` part and no leading `/` or `\`.
- `what`: a non-empty string. `why`: a non-empty string, required for `planted`, `native` and `incidental` and optional for the others. `note`: an optional string.
- `added_in`: an integer from 1 to `key_version`.
- Fields allowed **only** on `planted`:
  - `difficulty` (required; integer 1–3);
  - `plant` (required; a non-empty list of mappings with exactly `path`, `find` and `replace`; `find` non-empty, `replace` may be empty);
  - `confounded` (optional bool).
- Field allowed only on `native`: `interaction` (a mapping with exactly `plant`, which is the ID of a non-retired planted item, and `effect`, which is in `EFFECTS`).
- `source`: optional on every kind except `planted`; a mapping with exactly `run` and `finding` (strings).
- Any other field is a problem.

**Against the clean corpus (non-retired items only)**
- Every location `path` is a file in `clean_dir`, and its `section` is `""` or one of `headings()` of that file.
- Every plant edit's `path` is one of the item's location paths, and its `find` occurs exactly once in the clean file.
- At most one planted item edits any one page.
- **Lint:** no `replace` text matches `LABEL_WORDS`.
- **Rule 2:** for each plant edit, take `section_at(text, offset_of_find)`. Every native with a location equal to that `(path, section)` must have `interaction.plant` equal to that planted item's ID.

### `evals/__main__.py`

- `argparse` with the subcommands `corpus verify <dir>`, `corpus build --key --clean --seeded [--variants]` and `key check --key --clean`. Usage errors exit 2 (argparse's default).
- Problems go to stderr, one per line, and the command exits 1. Success prints one summary line to stdout and exits 0:
  - verify: `OK <n> files, tree <hash>`;
  - key check: `OK <key_id> v<key_version> sha256 <hash>, <n> items`;
  - build: `OK clean <hash> seeded <hash>, <k> plants -> <variants path>`.
- `corpus build`:
  1. Load and `check` the key; any problem exits 1.
  2. Take `approved_edits`; if there are none, exit 1 with `no approved plants`.
  3. Call `corpus.build`; a `CorpusError` exits 1.
  4. Write `variants.yaml` with `yaml.safe_dump(..., sort_keys=False)`. The default path is `<key dir>/variants.yaml`. It contains no timestamp, so the same inputs give identical bytes:

```yaml
snapshot_id: acme-2026-01-01
key_id: acme-example
key_hash: <sha256 of key.yaml>
plants: [PL-01]
variants:
  clean: {tree_hash: <hex>, files: 4}
  seeded: {tree_hash: <hex>, files: 4}
```

Out of scope for H1, and left to H2: refusing paths inside the repo, staging and running audits.

## Tests

Use plain pytest functions and `tmp_path`. Never write into the repo: **every build test passes `--variants` (or calls `corpus.build`) with a `tmp_path` target.** To mutate the key, load `key.yaml`, change the dict (`copy.deepcopy`) and call `key.check` directly. To mutate the corpus, copy `evals/examples/acme/clean` to `tmp_path` with `shutil.copytree` first. Use `EXAMPLE = Path(__file__).resolve().parents[1] / "evals" / "examples" / "acme"`.

For the CLI tests, run `subprocess.run([sys.executable, "-m", "evals", ...], cwd=<repo root>, capture_output=True, text=True)` and assert the exit code.

`tests/test_evals_corpus.py`:

1. `verify` on the example clean tree returns `[]`, and its tree hash equals `run_manifest.tree_hash(<dir>)`.
2. `verify` rejects each of: a symlinked file, a symlinked directory, a `notes.txt`, a `.DS_Store`, two files with identical bytes, an empty directory, a missing path. Parametrize; each case yields exactly the one expected problem.
3. `section_at` in `api/tokens.md`: the offset of `curl` gives `"Creating a token"`, not the shell comment. The offset of `Tokens expire` gives `"Expiry"`. Offset 0 gives `""`. `headings()` on that file doesn't contain `"List the notebooks you can see"`.
4. The build is reproducible: two builds of the example (approved edits) into two `tmp_path` directories give the same seeded tree hash and identical `variants.yaml` bytes (via the CLI).
5. After a build: the seeded file list equals the clean one; only `sharing/links.md` differs; it contains PL-01's `replace` and not its `find`; PL-02's `replace` is absent from `api/tokens.md`; the seeded hash differs from the clean hash.
6. A `find` that occurs zero times fails. A `find` that occurs twice (append the sentence again in the copied corpus) fails. In both cases the seeded directory is not created.
7. Overlapping edits fail (two edits on one file whose finds overlap). Touching edits succeed.
8. An edit whose path isn't in the corpus fails.
9. The build refuses a `seeded` path that exists, equals `clean`, or is inside `clean`.
10. CRLF survives: convert one unedited file and the edited file to `\r\n` in the copy; after the build, the unedited file is byte-identical and the edited file still uses `\r\n`.

`tests/test_evals_key.py`:

1. The example key passes: `check(...) == []`. The CLI `key check` exits 0.
2. `key_hash(p) == hashlib.sha256(p.read_bytes()).hexdigest()`. Changing one character of a YAML comment or of whitespace in a `tmp_path` copy changes `key_hash`, and `key_version` is unchanged.
3. Parametrized rejections, each a single mutation of the example dict that must produce a problem naming the item:
   - an unknown tag;
   - no area tag;
   - `contradiction` alone;
   - three area tags;
   - a duplicate ID;
   - an ID prefix that doesn't match the kind;
   - a planted item without `plant`;
   - a planted item without `difficulty`;
   - `difficulty: 4`;
   - `difficulty: true`;
   - a planted item with `variants: [clean, seeded]`;
   - `interaction` on a planted item;
   - `source` on a planted item;
   - a native without `why`;
   - an unknown field;
   - `added_in` greater than `key_version`;
   - `tags_version: 2`;
   - an unknown header key;
   - a location path with `..`;
   - a location path not ending in `.md`;
   - a location section that isn't a heading;
   - a location file missing from the corpus;
   - a plant path that isn't among the item's locations;
   - a plant `find` that isn't in the file;
   - two planted items on one page;
   - a `replace` containing `seeded`;
   - a `replace` containing `NA-03`;
   - `interaction` naming an unknown plant;
   - `effect: hidden` with `variants: [clean, seeded]`.
4. **Rule 2:** delete NA-02's `interaction`. `check` reports NA-02. Moving NA-02 to section `"Creating links"` instead clears the problem (with the `interaction` still deleted).
5. Retired items skip the corpus checks: setting PL-02 to `retired` and breaking its `find` gives no problem.
6. `approved_edits` returns exactly PL-01's one edit.
7. CLI: `corpus build` with a key that has no approved plants exits 1. With a key that fails `check`, it exits 1 and doesn't create the seeded directory.

## Mutation checks

Apply each mutation alone, run the two new test files, record how many tests fail, and revert. **Each must fail at least one test.** If one fails none, add a test that catches it, then rerun.

- M1: `find` count check accepts 2 occurrences (`!= 1` becomes `not in (1, 2)`).
- M2: delete the overlap check.
- M3: delete rule 2.
- M4: skip symlinks in `verify` without reporting them.
- M5: open clean files in text mode in `build`.
- M6: `key_hash` hashes `yaml.safe_dump(load(path))` instead of the file bytes.

## Docs

- **`AGENTS.md`:** under "Tests and syntax checks", add one short paragraph saying that `evals/` holds the offline eval harness; that `python -m evals corpus verify <dir>`, `key check --key <file> --clean <dir>` and `corpus build ...` make no model calls; that `evals/examples/acme/` is the synthetic example the tests use; and that the design is `docs/plans/evals/05_EVAL_DESIGN.md`.
- **`archive/PROGRESS.md`:** append `## Phase: Eval H1 — Corpus and Key Tools | 2026-11-12` after the P3 entry, in the same shape as the P1–P3 entries (tasks completed, test count, next steps: H2 runner).
- **`LOGBOOK.md`:** through the script only (step 10).

## Report

Reply with exactly these sections:

1. **Branch and commits:** branch name, commit hashes, `git diff --stat origin/ADK_master`.
2. **Baseline:** the full-suite result before your change.
3. **Result:** the full-suite result after, and the new test count.
4. **Mutations:** a table of M1–M6 with the number of failing tests for each.
5. **Deviations:** anything you did differently from this prompt, and why. "None" if none.
6. **Stops:** any stop condition you hit, quoted with the command and output.
