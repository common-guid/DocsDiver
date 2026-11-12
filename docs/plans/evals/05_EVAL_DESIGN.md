# Eval Design (Strategic Feature 1, v0)
Status: final. Operator decisions of 2026-11-11 are in §6; every challenge in §5 is settled · Created 2026-11-10 · Finalized 2026-11-11 · Repo baseline `ADK_master` at `c30ee03` · Input: `03_EVAL_DESIGN_BRIEF.md` · Produced from `04_DESIGN_PROMPT.md`

All example data in this document is synthetic ("Acme Notes"). Nothing here is derived from the Hex snapshot.
## 1. Summary
1. **Recall is graded key-first.** For each key item, a judge model searches each worker artifact (with numbered lines) for a finding that reports the item, cites the lines, and answers three yes/no checks. Recall never depends on splitting an artifact into findings.
  
2. **The invented count is graded finding-first.** The judge, without the key, groups lines into findings. A finding is invented only if it covers nothing real and has an explicit not-real ruling. Findings with no ruling are reported as unruled.
  
3. **Two controls measure the grading itself:** planted items offered as decoys on clean runs (expected hits: 0), and a count of matches that fall outside every extracted finding.
  
4. **The answer key is one YAML file in the vault** with five kinds of item. The seeded corpus is built from the clean snapshot by exact find-and-replace edits stored in the key.
  
5. **The judge is Grok 4.7 (`x-ai/grok-4.7`) through OpenRouter**, the operator's choice, a different model family from the model under test. Its prompts live in the repo. It is trusted only after it agrees with the operator on 16 hand-graded cases.
  
6. **DocsDiver never sees the vault.** The harness copies a corpus variant to a neutral temporary directory, runs the headless CLI there and collects the outputs. `run` and `grade` are separate commands, and only `grade` reads the key.
  
7. **Every number traces to two records:** a run manifest written by DocsDiver (commit, models, prompt versions, corpus hash, tokens, cost) and a grade record (key hash, judge version).
  
8. **Langfuse in v0:** traces, usage and cost, one session per run, optional run-level scores. No datasets, experiments or annotation queues yet.
  
9. **Estimated cost:** under $0.10 per audit and $0.35–0.50 per graded run for the judge, about $7 for all of v0. Operator time is 120 minutes with no slack.
  
10. **Main challenges to the brief:** 12 items cannot show 90% recall; the operator cannot rule on every clean-run finding in 30 minutes; the repo already holds vendor-derived documentation. The operator's decisions are in §6.
  
## 2. Verified facts
Checked against the source at `c30ee03`, the Langfuse project (read-only CLI), and the current Langfuse and OpenRouter documentation on 2026-11-10.
### Where the brief is right
| Brief claim | Evidence |
| --- | --- |
| Headless exits 0, 1 or 2 | `main.py:113-121` (`parser.error`, exit 2); `main.py:164,174,233,267,281` (exit 1) |
| Output names and locations | `output_validation.py:17-23`; `reporting.py:46,59,71,83` |
| No usage or cost recorded (P1) | `openrouter_model.py:131-138` sets only `openinference.span.kind` and `model_name`; nothing reads `response.usage`; streaming TODO at `:333` |
| Corpus and output paths come only from YAML (P2) | `config_loader.py:17-29` |
| OpenRouter returns `usage` with `cost` on every Chat Completions response, no parameter needed | OpenRouter "Usage Accounting" page |
| No datasets, score configs or annotation queues exist | Langfuse CLI lists, all empty. No LLM connections either |
| `sdaa/src/schemas/findings.py` does not exist | Confirmed |
### Where the brief is wrong or incomplete
| # | Finding | Evidence | Effect on the design |
|---|---|---|---|
| V1 | "214 generations" counts each model call twice. Inside an audit trace every call appears as `call_llm` (ADK instrumentor) and as `OpenRouterModel.generate_content` (manual span). A full audit is 15–19 model calls, not 30–38. | Langfuse: traces with 38/36/36/30 generations hold 19/18/18/15 of each name | P1 must record usage on one span only, or cost doubles |
| V2 | The manual span's `model_name` attribute is not one Langfuse maps to a model. All 136 `OpenRouterModel.generate_content` generations have an empty model. | Langfuse OpenTelemetry mapping table; observation query | P1 also sets a mapped model attribute |
| V3 | Zero tokens is now permanent unless usage is sent. Langfuse stopped estimating token counts on 2026-11-06. | Langfuse "Token & Cost Tracking" | Confirms P1 |
| V4 | Every run shares the Langfuse session `session_001`, and Map Maker calls have no session. Each Map Maker call is its own trace. | `main.py:195`; observation query | Runs cannot be told apart in Langfuse today. P3 fixes this |
| V5 | A failed prompt fetch does not fail the run. The agent gets an error sentence as its instruction, and headless success checks only that outputs are non-empty. | `workers.py:41-43`; `main.py:276-283` | A run with a missing prompt version is invalid for the eval |
| V6 | The model sees the absolute output path. Reporting tools return it. | `reporting.py:50,62,74,88` | Output paths must not reveal the eval. See §3.6 |
| V7 | `production` is not the newest prompt version. All four audit prompts resolve to version 2; versions 3 and 4 exist. | Langfuse prompt list | Recording the version, not the label, matters now |
| V8 | The test corpus is not "about 220 words". `docs-for-testing/` holds 16 tracked files, about 640 KB. Twelve of them, under `api/`, look like a third-party vendor's API documentation with the product name replaced. They hold only three distinct contents; nine are exact copies. | `git ls-files docs-for-testing`; file hashes | See challenge 5 |
| V9 | Worker artifacts are large. On the test corpus they were 17,000–35,000 characters each, and the final report 44,000. The same issue appears in an analysis bullet and again in a test-plan row. | Trace of 2026-11-10 | Drives §3.1 and challenge 3 |
| V10 | Eval runs would also be exported to LangSmith: `.env` enables it and holds a key. C5 names only Langfuse. | `.env` (key names only); `instrumentation.py:63-74` | Open question 3 |
| V11 | Langfuse Cloud becomes v4-only on 2026-11-16. The OTLP exporter sends no `x-langfuse-ingestion-version: 4` header, so data can appear up to 15 minutes late. | Langfuse "Versions & Compatibility"; `instrumentation.py:134-137` | P1 adds the header |
| V12 | `docs_root` is read on every call, so a runtime override works. `~` is expanded for `output_dir` only. | `file_ops.py:10-11`; `config_loader.py:56` | The harness passes absolute paths |
### Other facts used
- **Headless never streams.** Tools force non-streaming (`openrouter_model.py:314-316`) and Map Maker calls without `stream` (`map_maker.py:108`).
  
- **Prompt versions are available at run time.** The prompt object carries `.version` (`openrouter_model.py:147-150`). The synthesizer prompt name and label are hardcoded (`coordinator.py:98-101`); the Map Maker prompt is inline (`map_maker.py:83-94`), so the commit covers it.
  
- **Worker prompts ask for footnote citations** that map to a file path and section. The Located check can use them.
  
- **Versions:** Langfuse Python SDK 5.2.0 (`requirements.lock:96`), which uses the v4 public API; `@langfuse/cli` 1.3.1 (API snapshot 4.71.0); `openai` 1.109.1.
  
- **Langfuse data model:** an experiment item is exactly one trace. Annotation queues hold traces, observations or sessions and need a score config. A score can target a session. A score `id` works as an idempotency key. An ingested cost takes priority over a calculated one.
  
- **Prices (OpenRouter list, 2026-11-10):** `deepseek/deepseek-v4.1-flash-1017` $0.006 per million input tokens, $0.50 per million output; `anthropic/claude-sonnet-5.5` $2 and $10; `anthropic/claude-opus-5.5` $4 and $20. Checked 2026-11-11: `x-ai/grok-4.7` $2 and $6, 500,000-token context, accepts `temperature` and structured outputs.
  
- **Slice size (C3):** the three areas come to about 28 pages and 48,000 words (about 65,000 tokens). That includes one reference page of about 16,000 words, because no page is left out for length (decision 6). That is inside the 20–40 page target.
  
## 3. Design
Terms used below:

- **Artifact:** one worker's Markdown file, or the final report.
  
- **Key item:** one entry in the answer key.
  
- **Match:** the judge's statement that certain lines of one artifact report a given key item, with the three check results.
  
- **Finding:** a group of lines in one artifact that states one issue a tester could act on.
  
- **Run:** one full audit of one corpus variant. **Graded run:** a run plus its grade record.
  

Where the hard parts from the design prompt are answered:

| Hard part | Section |
| --- | --- |
| 1. Segmentation before matching | §3.1 |
| 2. Many-to-many matching | §3.1 |
| 3. Clean and seeded interact | §3.3, §3.4 |
| 4. Small numbers | §3.8 |
| 5. Key leakage | §3.6 |
| 6. Judge independence and cost | §3.5 |
| 7. Reproducibility | §3.6 |
### 3.1 Finding-to-key matching (brief item 1)
**Recommendation: two passes over line-numbered artifacts, both done by the judge.**

**Step 0, numbering (code, no model).** Every non-blank line of an artifact gets a number. A table row is one line. Lines are the only unit the judge may cite. This step cannot fail in a way that changes a metric: it is a pure function of the file.

**Pass A, recall (key-first).** One judge call per artifact. The judge receives the numbered artifact and the key items valid for that run. For each item it answers: do any lines report this issue? If yes, it cites the line numbers and answers the three checks.

```json
{"item": "PL-01", "match": true, "lines": [41, 97],
 "located": true, "what": true, "why": false,
 "note": "States both passages and the conflict. Gives no impact."}
```

**Pass B, findings (finding-first).** One judge call per worker artifact, without the key. The judge groups lines into findings and gives each a one-sentence claim and the cited document. Lines that only describe documented behaviour, list sources or restate a documented rule as a test case are not findings.

**Joining the passes (code).** A finding is _covered_ by a key item when its lines overlap the lines of a match for that item. Each finding then lands in exactly one bucket, the first that applies:

| Bucket | Condition | Counts as |
| --- | --- | --- |
| planted | covers a planted item | recall evidence |
| real, unscored | covers a native or incidental item | nothing (K5 step 3) |
| disputed | covers a disputed item | nothing |
| invented | covers an item ruled not real | invented |
| unruled | covers nothing | review queue; reported as unruled |

**Why this shape.** The brief's order of priorities is missed, then invented, then inaccurate. Recall is the gate, so its path should have the fewest steps that can fail. Key-first matching has no segmentation step at all: the judge reads the whole artifact for each item. Segmentation by a model is needed only for the invented count, and there an error is visible (see below).

**Segmentation errors show up as numbers (hard part 1).** Three counters are in every grade record:

- `invalid_citations`: cited line numbers that don't exist. Must be 0; the call is retried once, then the grade fails.
  
- `match_outside_finding`: matches that pass Located and What but overlap no finding from pass B. Pass B missed a finding that pass A proved is there.
  
- `findings_per_artifact` and `lines_in_findings`: a shift between runs or judge versions shows that pass B's granularity moved.
  

Recall is unaffected by all three. The invented count is flagged as unreliable for a run when `match_outside_finding` is above 2. That threshold is provisional until the baseline shows what is normal.

**Counting rules (hard part 2).**

| Situation | Recall | Invented count |
| --- | --- | --- |
| One finding covers two key items | Each item is graded on its own against those lines. Both can be hits. | The finding counts once, in its highest bucket |
| Two findings in one artifact cover one item | One hit. The judge cites all the lines and grades them together. | Neither is invented |
| Two workers cover one item | One hit overall. Each worker gets its own per-worker credit. | Neither is invented |
| Worker A passes Located only, worker B passes What only | Not detected. Checks are never combined across artifacts. | Neither is invented |
| A finding reports the item but fails Located or What | Not detected. Reported as "reported inaccurately", not as "not reported". | Not invented |

Definitions:

- An item is **detected by a worker** when that worker's match passes Located and What.
  
- An item is **detected** when at least one worker detects it.
  
- An item has **full credit** when one worker's match passes all three checks.
  
- Recall is counted over items, so duplicates never raise it.
  

**Rejected:**

- _Rules or keyword matching:_ brittle on free prose; the brainstorm already ruled it out.
  
- _Finding-first only (extract, then match):_ an extraction miss would silently lower recall.
  
- _Key-first only:_ gives no list of findings, so no invented count.
  
- _Embedding similarity:_ a new dependency and a threshold to tune, for a few hundred comparisons.
  
- _Verbatim quotes instead of line numbers:_ models alter quotes; a line number is checkable exactly.
  
- _A Markdown block parser:_ more code and edge cases than numbering lines, with no gain.
  

**How the implementer knows it works.** Unit tests on synthetic artifacts with a canned judge cover every row of both tables above. A test feeds a judge reply with a bad line number and expects a retry, then a failed grade. A test checks that bucket counts sum to the number of findings.
### 3.2 Tag vocabulary (brief item 2)
**Recommendation: three area tags, each owned by one worker, plus one cross-cutting tag.**

| Tag | Definition | Owner |
|---|---|---|
| `permission-gap` | The docs leave undefined, ambiguous or too broad what a role, token or sharing level may do | `permissions_agent` |
| `invariant-gap` | A rule about what must not happen, a state or workflow limit, or a configuration dependency is missing, weakened or broken | `constraints_agent` |
| `trust-boundary-gap` | Data or control crosses between trust zones without a stated check | `boundaries_agent` |
| `contradiction` | Two passages, on one page or two, make incompatible statements | none |

Rules:

- Every item has one or two area tags.
  
- `contradiction` is always added to an area tag, never used alone. Every worker is responsible for contradictions in its own area.
  
- Per-worker recall uses the items that carry the worker's area tag. Contradiction recall is reported as its own slice.
  

**Rejected:**

- _A fourth owner for contradictions:_ no worker has that job, and the synthesizer is graded for retention only.
  
- _Extra tags for evidence status (silent, ambiguous, contradictory):_ useful later; with 12 items every extra slice holds two or three.
  
- _Free-form tags:_ slices would not be comparable across key versions.
  

**Check.** Key validation rejects unknown tags, an item with no area tag and `contradiction` alone. The vocabulary carries its own `tags_version`.
### 3.3 Answer-key schema (brief item 3)
**Recommendation: one YAML file,** `key/key.yaml`**, read with the PyYAML already installed.**

File header: `key_id`, `key_version` (integer, for people), `snapshot_id`, `tags_version`. The harness also computes a content hash of the file. **The hash is the version that comparisons use**; the integer is a label. An edit that forgets to bump the integer still produces a new hash.

| Field | Type | Applies to | Meaning |
|---|---|---|---|
| `id` | string | all | `PL-01` planted, `NA-01` native, `IN-01` incidental, `RJ-01` not real, `DS-01` disputed |
| `kind` | enum | all | `planted`, `native`, `incidental`, `invented`, `disputed` |
| `status` | enum | all | `draft` (proposed by the AI or the judge), `approved` (operator has ruled), `retired` |
| `tags` | list | all | From §3.2 |
| `variants` | list | all | Where the issue exists: `clean`, `seeded` or both |
| `locations` | list of `{path, section}` | all | One entry, or two for a cross-page item |
| `what` | text | all | The issue as a tester would state it |
| `why` | text | real kinds | The impact or risk reasoning |
| `difficulty` | 1–3 | planted | See §3.4 |
| `plant` | list of `{path, find, replace}` | planted | The edits that create it |
| `interaction` | `{plant, effect}` | native | Set when the item sits in a section a plant edits. `effect` is `none`, `hidden` or `altered` |
| `confounded` | bool | planted | True when a plant cannot be told apart from a native. Excluded from the gate |
| `source` | `{run, finding}` | discovered | Where the item was first reported |
| `added_in` | integer | all | Key version that introduced it |
| `note` | text | all | Operator's remark |

How the brief's terms map: _origin_ is `kind` for the three real kinds. _Adjudication status_ is real (`planted`, `native`, `incidental`), not real (`invented`) or unsure (`disputed`), with `status` saying whether the operator has ruled.

`incidental` is a real issue that exists only because a plant created it by accident. It is scored like a native. It keeps the native list clean: natives are real weaknesses in the vendor's docs, incidentals are not.

Example:

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
        find: "Only Admins can create public links."
        replace: "Any Editor can create a public link. Public links do not expire."
    added_in: 2
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
```

**Clean and seeded interact (hard part 3).** Four rules, enforced by key validation where possible:

1. **Items are offered to the judge only for the variants they list.** A planted item is never scored on a clean run (there it is a decoy, §3.5).
  
2. **A native in a section that a plant edits must carry** `interaction`**.** Validation fails otherwise. `none`: the native is unchanged. `hidden`: the edit removed it, so its `variants` becomes `[clean]`. `altered`: it is now a different claim; the old item becomes clean-only and the new claim is a new item.
  
3. **Within one variant, no two items may be the same claim.** If a plant and a native cannot be told apart in the seeded text, the planted item is marked `confounded` and leaves the gate's numerator and denominator. So a native can never count as a planted miss.
  
4. **Nothing becomes invented without a not-real ruling.** A finding that covers no item is unruled. So a native that is not yet in the key can never count as invented.
  

**Rejected:**

- _JSON:_ hard for the operator to review multi-line text.
  
- _A Markdown table:_ not safe to parse.
  
- _A Langfuse dataset:_ the key must stay in the vault (C5), and dataset versions are timestamps, not content hashes.
  
- _Separate files for plants and key:_ two versions to keep in step.
  

**Check.** `python -m evals key check` validates the schema, IDs, tags, variants and rule 2. A test changes one character of the example key and expects a different hash.
### 3.4 Planting method (brief item 4)
**Recommendation: each plant is one or more exact find-and-replace edits, stored in the key and applied by code.**

**Build.** `python -m evals corpus build` copies the clean tree and applies every approved plant. Each `find` string must occur exactly once in its file. Edits must not overlap. The build then checks that the seeded tree has the same file list as the clean tree and writes both tree hashes to `key/variants.yaml`. Same inputs give the same hash. The tree hash is the SHA-256 of the sorted list of relative paths and file hashes.

**Drafting.** The AI drafts 14 candidates so that two can be rejected. Each draft is shown to the operator as a before/after pair with its location, `what`, `why`, tags and difficulty.

| Mechanism | What the edit does |
| --- | --- |
| Alter | Changes a stated capability, default or limit |
| Delete | Removes a sentence that stated a restriction |
| Insert | Adds an exception or an unguarded path |
| Cross-page contradiction | Alters page A so it disagrees with an untouched statement on page B |

**Difficulty.**

| Level | Meaning | Target of 12 |
| --- | --- | --- |
| 1   | Visible in one sentence, on a page that is plainly about security | 4   |
| 2   | Needs two statements on one page, or sits on a page that is not plainly about security | 5   |
| 3   | Needs two pages | 3   |

**Spread by tag:** 4 `permission-gap`, 4 `invariant-gap`, 4 `trust-boundary-gap`. At least 3 of the 12 also carry `contradiction`.

**Rules for a plant:**

- It reads like the page around it: same terms, same sentence length, no labels.
  
- It yields exactly one key item (K1). An edit that creates two claims is split or redrafted.
  
- At most one plant per page. This limits interactions and stops plant density from becoming a signal.
  
- It does not touch a section that hosts a known native. Natives are found first (§4, phase D2) so this can be checked.
  
- For a contradiction, only one side is edited. The other side is the vendor's own text.
  

**Rejected:**

- _Unified diffs:_ need `patch` or git, and fuzzy context matching has no use on a frozen snapshot.
  
- _A hand-edited seeded copy:_ not reproducible and not reviewable.
  
- _Plants generated at run time:_ the corpus would differ between runs.
  
- _More than one plant per page:_ raises the chance of a plant altering a native or another plant.
  

**Check.** Tests on the synthetic corpus: the build is reproducible; a `find` that occurs zero or two times fails the build; overlapping edits fail. A lint scans the added text for label words (`planted`, `seeded`, `intentional`, key IDs). `python -m evals corpus verify` rejects symlinks, non-Markdown files, and files with identical content (V8).
### 3.5 Judge design (brief item 5)
**Model.** `x-ai/grok-4.7` through OpenRouter, temperature 0 (operator decision 1). It is a reasoning model: set the reasoning effort explicitly, and include it in the request parameters that make up the judge version. The harness uses the `openai` client already pinned, with the same API key and base URL as DocsDiver. Every response returns its cost, so judge spend is measured the same way as audit spend.

**Independence (hard part 6).** The judge must not be from the model under test's family. A model tends to favour text that reads like its own, and it shares its family's blind spots. DeepSeek is under test, so any DeepSeek model is excluded. The judge must also be clearly stronger than the model under test, because it decides whether a security claim is stated correctly. The model is a configuration value recorded in every grade record. Calibration, not the choice of vendor, decides whether the judge is trusted.

**The three tasks.** Each has one prompt file in `evals/prompts/`.

| Task | Sees the key | Input | Output |
| --- | --- | --- | --- |
| `recall` | Yes | Numbered artifact, key items | Per item: match, lines, three checks, note |
| `extract` | No  | Numbered artifact | Findings: lines, one-sentence claim, cited document |
| `draft` | No  | Unruled findings that cite one document, that document's text | Distinct candidate entries with a proposed ruling, a supporting quote from the document, and the findings each covers |

`draft` also removes duplicates: the same claim from three runs or two workers becomes one candidate entry.

**The checks.** A match requires the same subject and the same defect. A finding about the same page but a different defect is not a match.

| Check | Passes when | Fails when |
| --- | --- | --- |
| Located | The finding names the right document for every location of the item, after its own footnotes are resolved, and points to the right place: the section name, or a quote or paraphrase that identifies the passage. | Wrong document. Right document with nothing to identify the passage. One side only of a cross-page item. |
| What | The finding states the defect as the key does, in any words. | It reverses the claim, names the wrong role or object, or is too general for a tester to know what to check. |
| Why | The finding gives a specific impact that follows from the defect: the key's, or another valid one. | No impact given, or only a generic one ("this is a security risk"). |

**Output handling.** The judge replies in JSON. The harness validates it with Pydantic, retries once on a schema error, and then fails the grade. It never repairs a reply by guessing.

**Versioning.** Prompts are versioned in the repo with the code. The **judge version** is a hash of the three prompt files, the model slug and the request parameters. Each grade record stores it with the harness commit and the model name the provider returned.

**Decoys.** On clean runs the planted items are included in the `recall` call. They do not exist in the clean text. Any match that passes Located and What is a false positive of the judge, or a plant that duplicates a native. Expected: 0 of 36. This measures leniency on every clean run at no extra cost.

**Calibration (G5).**

1. Build 16 cases. Each is one key item plus the cited lines of one artifact. Take about 10 from real graded runs, including every case where the judge failed a check. Add about 6 near-misses: a real match rewritten by the AI to break exactly one check.
  
2. The operator grades the three checks on each case without seeing the judge's answers.
  
3. Compare.
  

| Measure | Target |
| --- | --- |
| Agreement on detection (Located and What together) | at least 15 of 16 |
| Agreement on each single check | at least 14 of 16 |
| Cases where the judge passes detection and the operator fails it | at most 1 |
| Decoy hits on clean runs | 0 of 36 |
| Stability: grade one seeded run twice | at most 1 planted verdict changes |

Cohen's kappa is reported but not gated; on 16 cases it is too noisy.

**On disagreement.** The operator's grade stands for that case. The prompt is revised, which makes a new judge version, and the 16 cases are rerun. At most two revisions, because the cases are also the test set. If the targets are still missed, switch to `anthropic/claude-opus-5.5`, a stronger model from a third family, and rerun. If that fails too, the judge proposes and the operator confirms every planted-item verdict on the seeded runs. That is 36 verdicts and is outside the time budget, so it is the operator's decision.

The 16 cases and the operator's grades are stored in the vault. Any later judge version is rerun against them with no operator time.

**Cost per graded run.** Token counts are estimates from V9.

| Task | Calls | Input tokens | Output tokens | Cost at $2 and $6 per million |
| --- | --- | --- | --- | --- |
| `recall` (3 artifacts and the report) | 4   | 68,000 | 12,000 | $0.21 |
| `extract` | 3   | 36,000 | 9,000 | $0.13 |
| `draft` (first grading of a variant) | about 10 | 40,000 | 8,000 | $0.13 |
| **Total** |     |     |     | **$0.34, or $0.47 with drafting** |

Reasoning tokens are billed as output and are not in these estimates; the grade record measures them. Opus 5.5, the fallback, would cost about 2.5 times this.

**Rejected:**

- _A DeepSeek judge:_ same family as the model under test.
  
- _Claude Sonnet 5.5:_ this design's first default. Same input price, higher output price ($10 against $6 per million); the operator chose Grok 4.7.
  
- _Opus 5.5 as the default:_ about 2.5 times the cost with no evidence yet that Grok 4.7 falls short. It is the first fallback.
  
- _A small, cheap judge:_ the Why check needs security reasoning, and the whole of v0 costs about $7, so there is little to save.
  
- _Langfuse-managed LLM-as-a-judge:_ needs the key and an LLM connection inside Langfuse, and it grades observations, not key items.
  
- _Judge prompts in Langfuse prompt management:_ a movable label again, and grading would need the network to fetch its own prompt.
  

**Check.** Tests run all three tasks against a canned judge. One live smoke run on the synthetic corpus must find its planted item and report zero decoy hits.
### 3.6 Harness architecture (brief item 6)
**What lives where.**

| Location | Contents |
|---|---|
| Repo, `evals/` | Harness code, judge prompts, the synthetic corpus and key used by tests |
| Repo, `sdaa/` and `main.py` | P1–P3 changes only |
| Vault, `evals/hex-v0/corpus/<snapshot-id>/clean/` and `seeded/` | The frozen snapshot and the built variant |
| Vault, `evals/hex-v0/key/` | `key.yaml`, `variants.yaml`, review sheets, calibration cases |
| Vault, `evals/hex-v0/runs/<run-id>/` | Outputs of one audit, `run_manifest.json`, `run.log` |
| Vault, `evals/hex-v0/grades/<run-id>/<key-hash>-<judge-version>/` | `grade.json` and the raw judge replies |
| Vault, `evals/hex-v0/reports/` | Generated reports |

**Modules.** Five files and a CLI entry point: `corpus.py` (hash, verify, build), `key.py` (load, validate), `run.py` (stage, run, collect), `grade.py` (numbering, judge calls, metrics), `report.py`. The implementer may merge files, except that `run.py` must stay separate from `key.py` and `grade.py`.

**Commands.**

| Command | Reads the key | Calls a model |
| --- | --- | --- |
| `python -m evals corpus verify <dir>` | No  | No  |
| `python -m evals corpus build` | Yes | No  |
| `python -m evals key check` | Yes | No  |
| `python -m evals run --corpus <dir> --runs-dir <dir> -n 3 [--set k=v]` | **No** | DocsDiver |
| `python -m evals grade --run <dir> --key <file>` | Yes | Judge |
| `python -m evals sheet` / `apply` | Yes | No  |
| `python -m evals report --grades <dir>` | No  | No  |

**How a run is driven.**

1. **Stage.** Copy the corpus variant to a new temporary directory outside the repo and the vault, as `<tmp>/docs`. Create `<tmp>/out`.
  
2. **Run.** Start `python main.py -m openrouter --headless --no-rich --docs-root <tmp>/docs --output-dir <tmp>/out --run-id <id>` as a subprocess, with a timeout. The output directory is empty, so everything is generated and no refresh flag is needed.
  
3. **Collect.** Move `<tmp>/out` to `runs/<run-id>/` with the captured log. Delete the staged copy.
  
4. **Validate.** A run is valid when the exit code is 0, the manifest exists, every agent has a prompt version (V5), no call went unmetered, and the tree was committed (or `--allow-dirty` was given and recorded).
  
5. **Repeat (P4).** Up to 5 attempts per variant to reach 3 valid runs. Every attempt is kept and reported. Nothing is retried silently.
  

**The prerequisites, concretely.**

_P1, usage and cost._ In the non-streaming branch of `OpenRouterModel.generate_content_async`, after the response:

- set `langfuse.observation.usage_details` to the token counts and `langfuse.observation.cost_details` to `{"total": <usage.cost>}`, both as JSON strings;
  
- set `llm.model_name` (V2);
  
- append the call to an in-process ledger: agent, model, prompt name and version, tokens, cost. *Moved to P3 (2026-11-11, `06_P1_USAGE_COST_PLAN.md` §7 decision 1): nothing reads the ledger before the run manifest exists.*
  

Usage goes on this span only, and `LlmResponse.usage_metadata` stays unset, so the ADK instrumentor's `call_llm` span carries no usage and nothing is counted twice (V1). The exporter gains the `x-langfuse-ingestion-version: 4` header (V11). A call that takes the streaming branch is counted as unmetered.

_P2, overrides._ Three flags on `main.py`: `--docs-root`, `--output-dir`, and a repeatable `--set <dotted.key>=<value>` that may change only keys that already exist in the loaded config. `--set agents.permissions_agent.openrouter=<slug>` changes one agent's model, which makes the model per agent an easily changed variable (M1). An unknown key exits 2. Rejected: environment variables (not visible in the command line or the log); a full `--config` file (duplicates the tracked YAML and drifts; the Roadmap can add it in Strategic 3); editing the YAML from the harness (touches a tracked file).

_P3, run manifest._ On every headless exit, DocsDiver writes `run_manifest.json` to the output directory:

| Field | Source |
|---|---|
| `run_id`, start and end time, `argv`, overrides | CLI |
| `code.commit`, `code.dirty` | `git rev-parse HEAD`, `git status --porcelain` |
| `corpus.tree_hash`, file count | Computed over `docs_root` at start |
| `agents.<name>.model`, `.prompt.name`, `.prompt.version` | The ledger: what each call actually used |
| `usage`: calls, tokens, cost, per agent, unmetered calls | The ledger |
| `outputs`: generated or reused, file hashes | Existing output checks |
| `outcome`: exit code, problems | Existing headless gate |

`--run-id` is also used as the ADK session ID and set as `langfuse.session.id` on every span, so one Langfuse session holds one run (V4).

**The run record is split on purpose.** The brief's P3 lists the variant and the key version as part of the run record. DocsDiver must not know either. The manifest holds what DocsDiver knows. The grade record adds the rest: the variant (found by looking up the manifest's tree hash in `variants.yaml`), the key hash, and the judge version.

**Key leakage (hard part 5).**

| Path by which the key could reach DocsDiver | Guard |
|---|---|
| File tools reading outside the corpus | `resolve_corpus_path` (Tactical 1). The staged corpus has no key beside it. |
| Directory or file names (`seeded`, `hex-v0`, `evals`) in paths the model sees (V6) | Staging: the model sees only `<tmp>/docs` and `<tmp>/out` |
| Leftover files in the seeded tree | The build copies and edits in memory; the file list must equal the clean tree's |
| Labels in planted text | The lint in §3.4 and the operator's review |
| Old outputs from another run | Every run starts with an empty output directory and a new process |
| The harness passing key data to the audit | `run.py` takes no key argument and does not import `key.py` or `grade.py` |
| The judge's context reaching DocsDiver | Grading happens after the audit process has exited |

Tests: one starts `run.py` in a subprocess and asserts the key modules were not imported. One runs a stub audit command and asserts that its arguments, its working directory and the value of every environment variable the harness adds contain none of: the vault path, `eval`, `seed`, `clean`, `key`, `plant`. One places a canary file next to a staged corpus and asserts a spy model never receives its content.

The harness also refuses to run when a corpus, key or output path resolves inside the repo.

**Reproducibility (hard part 7).** A grade is a pure function of the run outputs, the key file and the judge version. Grading can be repeated at any time without rerunning an audit. `report` reads only manifests and grade records; no number is typed by hand. It refuses to combine grades that differ in key hash, judge version or corpus tree hash, which enforces K4. Every report ends with a provenance table: run IDs, commit, model and prompt version per agent, corpus hashes, key version and hash, judge version.

**Operator review sheets.** `sheet` writes a Markdown file to the vault. Each entry is a heading with the context below it and one line to fill in: `Ruling:` for findings, `Decision:` for plants, or `Located:`, `What:`, `Why:` for calibration cases. `apply` reads the answers back, rejects unknown values, and writes the result into the key as a new version. This matches how the brainstorm questions were answered.

**Rejected:**

- _Running the audit in-process:_ the config singleton and in-memory sessions would carry state between runs.
  
- _Pointing DocsDiver at the vault directly:_ puts `evals/hex-v0/.../seeded` in a path the model sees.
  
- _One command that runs and grades:_ the audit and the key would share a process.
  
- _DocsDiver recording the variant:_ that is the leak the split record avoids.
  

**Check.** A mock headless run with the three flags writes only under the given directories and leaves the tracked YAML untouched. A mock run produces a manifest with every field; a failing run produces one with the failure recorded. After one live call, the Langfuse cost for the session equals the manifest's cost.
### 3.7 Langfuse mapping (brief item 7)
**Recommendation: files in the vault are the source of truth. Langfuse holds traces, cost and optional run-level scores.**

| Langfuse feature | v0  | How, or why not |
| --- | --- | --- |
| Tracing | Yes | As today, over OTLP at `/api/public/otel/v1/traces`, plus the v4 ingestion header |
| Usage and cost | Yes | P1  |
| Sessions | Yes | One session per run (P3) |
| Scores | Optional, last phase | `grade --push-scores` calls `create_score(session_id=...)` from Python SDK 5.2.0 for four numeric scores: `detection_recall`, `full_credit_recall`, `invented_confirmed`, `synthesis_retention`. The score `id` is built from the run ID, key hash, judge version and name, so a regrade updates in place. The comment holds the counts and versions. |
| Score configs | No  | Scores work without them. Add them when someone annotates in the UI. |
| Datasets and experiments | No  | An experiment item is one trace. v0 has two items (the variants) and metrics computed over a whole audit, so the comparison view would show less than a table. The expected output would be the key. |
| Annotation queues | No  | They hold traces, observations or sessions. Rulings and calibration grades are about findings and key items, which are neither. Using a queue would mean sending the key to Langfuse. |
| Managed LLM-as-a-judge | No  | §3.5 |
| Judge traces | No  | They contain the key |
| Prompt management | Unchanged | Agent prompts stay in Langfuse; resolved versions go in the manifest |

**When to revisit.** Experiments become useful when prompt versions are compared. At that point each run can be an experiment item through the OpenTelemetry experiment attributes, with no change to the grade records.

**Rejected:**

- _Langfuse as the system of record:_ the key and the native list would leave the vault, and reports could not be rebuilt offline.
  
- _No Langfuse at all:_ tracing exists already, and cost in the UI is a free cross-check of the manifest.
  

**Check.** After a run, Langfuse shows one session with every trace of that run and a total cost equal to the manifest's. A second `--push-scores` leaves four scores, not eight.
### 3.8 Metrics and report (brief item 8)
**Per run.** The scored set P is the planted items that are approved, not confounded and valid for the variant. Nominally 12.

| Metric | Definition |
| --- | --- |
| Detection recall | Items of P detected, over the size of P |
| Full-credit recall | Items of P with full credit, over the size of P |
| Reported inaccurately | Items of P matched somewhere but not detected |
| Not reported | Items of P with no match |
| Per-worker recall | For each worker: items carrying its area tag that it detected itself, over the items carrying its tag |
| Invented, confirmed | Distinct approved `invented` items covered by a finding |
| Unruled | Findings that cover nothing, split by the judge's draft: real, not real, unsure |
| Synthesis retention | Items of P detected by workers and also detected in the final report, over items of P detected by workers |
| Delivered recall | Items of P detected in the final report, over the size of P |
| Synthesis-only | Items detected in the report and by no worker. Expected 0 |
| Grading health | Decoy hits (clean runs), `match_outside_finding`, `invalid_citations`, findings per artifact |
| Cost | Audit cost and tokens from the manifest; judge cost from the grade record |

Failed attempts are listed with their exit code. Quality metrics are computed over valid runs only, and the completion rate is reported beside them.

**Across runs.** For one variant, one configuration, one key hash and one judge version:

- each run's count, the mean, the minimum and the maximum. No standard deviation: three values don't support one;
  
- the pooled count with a 95% Wilson interval;
  
- a table of item by run, hit or miss. An item missed 3 of 3 times is a different problem from one missed once.
  

**Reporting small numbers honestly (hard part 4).**

- **Counts come first, percentages second:** "10/12 (83%)", never "83%" alone.
  
- **The gate is stated in counts.** With 12 items, T1 means every run at least 10/12 and at least 33/36 in total. That allows at most 3 misses overall and at most 2 in one run. The report computes these thresholds from the actual size of P.
  
- **The interval is shown beside the gate.** 33/36 has a 95% interval of 78% to 97%. Only 36/36 has a lower bound of 90%. The three runs repeat the same 12 items, so even these intervals are optimistic.
  
- **A noise rule for comparisons.** A difference of fewer than 6 item-runs out of 36 (about 17 points) between two configurations is reported as "no evidence of a difference". That is two standard errors at a recall near 85%.
  
- **Slices are counts only.** A per-tag slice has four items. The report shows "3/4" and no percentage.
  
- **Provisional numbers are labelled.** Anything that rests on a `draft` item or an unruled finding is shown separately from confirmed numbers.
  

**Thresholds set after the baseline (T3).** The baseline report proposes values for full-credit recall, invented findings and synthesis retention from the observed counts and spread. The operator sets them.

**Rejected:**

- _Percentages only:_ one miss reads as "8 points".
  
- _Standard deviation over three runs:_ looks precise and isn't.
  
- _Severity weighting:_ out of scope (T2).
  
- _Counting a failed audit as zero recall:_ mixes an operational failure into a quality number. It is reported separately. See open question 8.
  

**Check.** Metric functions are tested against hand-computed fixtures, including a confounded item and a run with a synthesis-only item. A test asserts that `report` refuses two grades with different key hashes.
## 4. Phased build plan (brief item 9)
Model cost is an estimate until P1 lands. Operator minutes total 120.

| Phase | What | Files | Exit criteria | Model cost | Operator min |
|---|---|---|---|---|---|
| **P1** | Usage, cost, model name, ingestion header | `sdaa/src/utils/openrouter_model.py`, `sdaa/src/core/instrumentation.py`, `tests/test_openrouter_usage.py` | Mocked-response tests assert the span attributes. Live check: one full headless audit on `docs-for-testing/`; Langfuse cost equals the OpenRouter key-usage difference, with a model name on every adapter span. Detail: `06_P1_USAGE_COST_PLAN.md`. | under $0.05 | 0 |
| **P2** | `--docs-root`, `--output-dir`, `--set` | `main.py`, `sdaa/src/core/config_loader.py`, `tests/test_main_headless.py` | Mock headless run writes only to the given directories. Unknown `--set` key exits 2. Tracked YAML unchanged. | 0 | 0 |
| **P3** | Run manifest, `--run-id`, session per run, the call ledger (moved from P1) | `main.py`, new `sdaa/src/core/run_manifest.py`, `sdaa/src/utils/openrouter_model.py`, `sdaa/src/core/model_factory.py`, `sdaa/src/core/instrumentation.py`, tests | Mock run writes a complete manifest. A failed run writes one with the failure. A missing prompt version is recorded as null. | 0 | 0 |
| **H1** | Corpus and key tools, synthetic example | `evals/corpus.py`, `evals/key.py`, `evals/examples/acme/`, `tests/evals/` | Tests in §3.3 and §3.4 pass. No model calls. | 0 | 0 |
| **H2** | Runner | `evals/run.py`, `evals/__main__.py`, tests | Stub-audit run produces a run directory. The three leak tests pass. Paths inside the repo are refused. The audit process gets an empty `LANGSMITH_API_KEY` (decision 3). | 0 | 0 |
| **H3** | Judge, grading, report, sheets | `evals/grade.py`, `evals/report.py`, `evals/prompts/`, tests | Tests in §3.1, §3.5 and §3.8 pass with a canned judge. One live smoke on the synthetic corpus finds its planted item with zero decoy hits. | $0.10 | 0 |
| **D1** | Snapshot | Vault: `corpus/<snapshot-id>/clean/`, `key/variants.yaml` | `corpus verify` passes. Page count is 20–40. The operator has created the directories and confirmed the page list. | 0 | 5 |
| **D2** | Clean baseline and natives | Vault: `runs/`, `grades/`, review sheet, `key.yaml` v1 | 3 valid clean runs with measured cost. `extract` and `draft` done. The operator has ruled on at most 30 candidates; the rest stay `draft`. | $0.30 audits, $0.80 judge | 30 |
| **D3** | Plants | Vault: `key.yaml` v2, `corpus/<snapshot-id>/seeded/` | 12 plants approved. `key check` and `corpus build` pass. The seeded hash is recorded. | 0 | 48 |
| **D4** | Seeded runs, first grading | Vault: `runs/`, `grades/` | 3 valid seeded runs. All 6 runs graded with key v2. Decoy hits reported. | $0.30 audits, $2.40 judge | 0 |
| **D5** | Calibration | Vault: `key/calibration/` | The targets in §3.5 are met, or the fallback is chosen. If the judge changed, all 6 runs are regraded. | $0.80, plus $2.40 if regraded | 28 |
| **D6** | Baseline report | Vault: `reports/`; optional Langfuse scores | Report generated from grade records with the provenance table. Proposed T3 thresholds listed. Optional: the operator rules on the 9 highest-priority unruled findings from seeded runs. | 0 | 9 |
| | **Total** | | | **about $7** | **120** |

Notes on the plan:

- **Order.** P1 comes first. Its live check is the first spend and is itself the test that spend is measured. The first live audit is in D2, after P1–P3 and H1–H3.
  
- **Natives before plants.** D2 runs before D3 so plants can avoid sections that host a native (§3.4).
  
- **Grades are provisional until D5.** D4 grades with an uncalibrated judge. D5 either confirms those grades or replaces them.
  
- **Each code phase** ends with the full test suite in a disposable copy, as `AGENTS.md` requires, and a logbook entry.
  

**Operator time, by task (O1).**

| Task | Arithmetic | Minutes |
| --- | --- | --- |
| Create vault directories, confirm the page list | fixed | 5   |
| Review plants and key entries | 12 approvals at 4 minutes. 14 drafts are offered; if all 14 must be read, that is about 3.4 minutes each. | 48  |
| Rule on clean-run candidates | at most 30 at 1 minute, in this order: the judge's "not real", then "unsure", then a random sample of "real" | 30  |
| Grade calibration cases | 16 at 1.75 minutes | 28  |
| Rule on seeded-run unruled findings | at most 9 at 1 minute | 9   |
| **Total** |     | **120** |

**Audit cost, by estimate (M2).** A corpus of 65,000 tokens gives about 28 Map Maker calls (70,000 input tokens), three workers that reread their history on each turn (650,000–1,300,000 input tokens, 54,000 output because each artifact is written twice), and synthesis (75,000 input, 24,000 output). At $0.006 and $0.50 per million that is about $0.05, or under $0.10 if reasoning tokens double the output. That is under 7% of the $1.50 budget. The judge costs five to ten times the audit.
## 5. Challenges to the brief
The design above follows the brief as written in every case.

| #   | Decision | What I would change | Why | Cost of the change |
| --- | --- | --- | --- | --- |
| 1   | C4 with T1 | Read the gate as a coarse screen, or raise the key to about 24 planted items. | 12 items cannot show 90%. A pass at 33/36 is consistent with a true recall of 78%. Only 36/36 supports 90%. | 24 items: about 48 more operator minutes, and more than one plant on some pages. |
| 2   | O1  | Add 30 minutes, or accept provisional invented counts on seeded runs. | The three tasks in O1 use the whole budget. O1 has no time for K5 step 4 (new findings on seeded runs), a second calibration round or a rejected plant. The plan fits only by capping each task. | 30 minutes. |
| 3   | K5 step 2 | The judge drafts a ruling with a quote from the source page for every candidate. The operator rules on at most 30, in priority order. The rest are scored as provisional. | Artifacts on the test corpus held dozens of claims each (V9). Three clean runs will produce more distinct candidates than 30 minutes can cover. | Some natives rest on the judge alone until reviewed. They are labelled. |
| 4   | G4 with §1 | Report delivered recall (planted items detected in the final report) beside the gate. No change to the gate. | The question is whether the report is good enough to hand over. The gate measures the workers' union. If synthesis drops items, the gate can pass while the report that is handed over falls short. | None. The report is already graded for retention. |
| 5   | C5  | Decide whether `docs-for-testing/api/` stays in the public repo. | C5 says nothing derived from the vendor goes into the repo. Those 12 tracked files appear to be exactly that, with the name replaced, and have been public since January (V8). | Removing them changes the default test corpus. The suite needs a check, and history would need rewriting to remove them fully. |
| 6   | M2  | Budget per graded run, not per audit. | The audit is estimated at under $0.10. The judge is $0.35–0.50. The $1.50 cap as written constrains the cheap part. | None. |

**Status (2026-11-11):**

- **1:** resolved. Stay at 12 planted items and read the gate as a screen; revisit the size in v2 (decision 10).
- **2:** resolved. Accept provisional invented counts on seeded runs; O1 stays 120 minutes (decision 9).
- **3:** accepted. The judge drafts rulings and the operator rules on at most 30, the judge's "not real" drafts first (phase D2). The gate is unaffected: it counts planted items only. The confirmed invented count uses approved items only (§3.8), so unreviewed drafts can't inflate it.
- **4:** accepted. §3.8 reports delivered recall beside the gate. The gate stays on the workers' union (G4, F5).
- **5:** resolved. Remove the files (decision 7).
- **6:** accepted. The $1.50 cap (M2) applies per graded run: audit plus judge, from the run manifest and the grade record. The estimate is about $0.57. The cap stays provisional until P1 measures real cost.

## 6. Operator decisions (2026-11-11)

The operator answered the open questions in review. The design above has been updated to match.

| # | Question | Decision | Effect on this design |
| --- | --- | --- | --- |
| 1 | Judge model | Grok 4.7 (`x-ai/grok-4.7`) instead of the proposed Sonnet 5.5 | §1, §2 prices, §3.5 model, cost and rejected list, §4 costs, §7. Still a different family from the model under test. Fallback stays Opus 5.5. |
| 2 | Key items sent to OpenRouter and the judge's provider | Yes, with no-retention routing if OpenRouter offers it for the judge model | The implementer checks the provider-routing parameter in phase H3. |
| 3 | LangSmith for eval runs | Disabled | The harness passes `LANGSMITH_API_KEY=` (empty) to the audit process. That is what disables it: `instrumentation.py` enables LangSmith whenever the key is set, and `load_dotenv()` does not override a variable that is already set. `LANGSMITH_TRACING=false` alone would not work. Tested in H2. |
| 4 | Located check without a section name | Pass, when the finding names the right document and quotes or paraphrases the passage | As already written in §3.5. |
| 5 | "The docs don't say X" findings | Real only when the finding names a specific control on a feature the docs describe | Ruling guide for the `draft` prompt and the review sheets. |
| 6 | Snapshot capture | A new small fetch-and-convert script outside the repo. **No page is left out for length.** | The slice includes the reference page of about 16,000 words (§2). The audit estimate in §4 grows and stays under $0.10. |
| 7 | Vendor-derived test files (`docs-for-testing/api/`) | Remove from the repo | A separate repo task, not an eval phase. |
| 8 | Failed audits | Up to 5 attempts per variant, completion rate reported | As already written in §3.6 and §3.8. |
| 9 | Operator time | Accept provisional invented counts on seeded runs | O1 stays 120 minutes. Challenge 2 resolved. |
| 10 | Size of the key | Stay at 12 planted items; consider about 24 in v2 | The gate is read as a screen (§3.8). Challenge 1 resolved. |
| 11 | `--set` in P2 (2026-11-12) | Deferred. P2 ships `--docs-root` and `--output-dir` only | No v0 phase uses an override; build it when the first comparison run is planned. `evals run` drops `[--set k=v]` until then. Plan: `09_P2_PATHS_PLAN.md`. |

## 7. Risks beyond brief §7
- **A judge that holds the key is lenient by default.** It looks for the answer and tends to find it. Decoys, near-miss calibration cases and the stability check measure this; they do not remove it.
  
- **The invented count depends on how the judge splits findings.** It is comparable only within one judge version. `findings_per_artifact` shows when the granularity moves.
  
- **The model may know the public docs from training.** A plant contradicts what it remembers. That could make plants easier to spot or cause the model to "correct" them silently. The direction is unknown.
  
- **Three runs measure run-to-run noise only.** They say nothing about a different set of items or a different corpus. Results do not generalise beyond this slice.
  
- **The ToC is regenerated on every run.** Its summaries and tags steer which pages a worker reads, so Map Maker variance is part of the measured spread. A plant can also change its page's summary.
  
- **The plant drafter is a Claude model and the judge is an xAI model.** That is harmless while DeepSeek is under test. When a Claude model is put under test, plants written by its own family may be easier for it: review the plants then. When an xAI model is put under test, the judge is no longer independent: change the judge.
  
- **The judge's model can be retired.** OpenRouter already retired `x-ai/grok-4.1-fast` (seen 2026-11-09). A replacement judge is a new judge version: rerun the 16 calibration cases (no operator time) and regrade before comparing results.
  
- **OpenRouter can route one model slug to different upstream providers.** Behaviour can differ between runs for reasons outside the repo. The ledger records the provider when the response names one.
  
- **A worker can call its reporting tool twice.** The last call overwrites the file, and its final chat message can differ from the file. Grading uses the file, which is what synthesis reads.
  
- **Langfuse Cloud changes on 2026-11-16** (V11). Check that traces still arrive after the cutover before D2.
  
- **Prompt labels move** (V7). Two runs a week apart can use different prompt versions under the same label. The report treats them as different configurations.
