# Eval Design Brief (Strategic Feature 1, v0)

Status: brief, ready for detailed design · Created 2026-11-10 · Repo baseline `ADK_master` at `963fc6f` · Sources: `01_EVAL_BRAINSTORM.md`, `02_FOLLOWUP_QUESTIONS.md`

This brief collects every decision from the brainstorm in one place. It is the input for the detailed eval design (to be produced by a frontier model from a prompt in `04_…`), and it says what that design must decide. It is not a design or an implementation plan.

## 1. The question the eval answers

**Is a DocsDiver report good enough to hand over?**

That means finding at least 90% of the issues it should find, each one located and explained accurately, with a grade assigned by a rubric. Failures matter in this order:
1. missed issues;
2. invented issues;
3. inaccurate descriptions of real issues.

## 2. Settled decisions

### Corpus

- **C1. Public documentation only.** Client or engagement documents are never used in evals or sent to Langfuse.
- **C2. Seeded real docs.** Freeze a dated snapshot of Hex's public docs (<https://learn.hex.tech/docs>) and plant known issues in it. Use two variants of the same snapshot:
  - **clean:** unmodified;
  - **seeded:** with the planted issues.
- **C3. The v0 slice covers about 20–40 pages:**
  - roles and permissions;
  - sharing;
  - workspace, including workspace and API tokens.

  Out for v0: SSO/SCIM, data connections.
- **C4. About 12 planted issues**, spread across the tags, including some contradictions across pages.
  - Planted text matches the docs' voice and is never labelled. The current `docs-for-testing/` fixture labels its flaws inline ("Intentional flaw: …"), which leaks the answers.
  - The planted issues vary in how hard they are to spot.
- **C5. Private storage.** The snapshot, the answer key and the run outputs live outside the public repo, in the vault at `~/CoS_brain/projects/Doc_Analysis_Agent/evals/hex-v0/`. Two reasons:
  - Hex owns the copyright on the docs, so copying them into the repo would republish them.
  - A list of weaknesses in a real vendor's documentation is sensitive.

  Nothing derived from Hex goes into the repo. The public repo holds only the eval code and synthetic examples. Langfuse may hold traces of Hex runs, since the docs are public.

### Answer key

- **K1. Item granularity:** one key item is one distinct claim a tester could act on.
- **K2. Tags, not categories:** each item has one or more tags from a fixed vocabulary.
  - Starting point: the three workers' areas (permission gaps or ambiguity, broken or missing invariants, trust-boundary gaps) plus contradictions between documents.
  - Tags let metrics be sliced, and map items to the worker responsible for them.
- **K3. Where each item comes from:**
  - **planted:** the issues we seed, with a fully known key;
  - **native:** real issues already in Hex's docs, found and confirmed through the protocol in K5.
- **K4. Versioning:** every run records the key version, and results are compared only within one key version.
- **K5. Native-issue protocol:**
  1. Audit the clean variant 3 times and merge the findings into one deduplicated list.
  2. The operator rules on each finding:
     - **real:** added to the key as native;
     - **not real:** kept as examples of invented findings, also used for judge calibration;
     - **unsure:** marked disputed and left out of scoring.
  3. On seeded runs, a finding that matches a native item counts neither for nor against.
  4. A new unmatched finding goes into a review queue. The operator's ruling may add it to the key, which produces a new key version.
  5. An optional single pass with a stronger model over the clean variant can widen the native list. DocsDiver can only surface natives it is able to see.

### Grading

- **G1. Binary checks per finding:**
  - *Located:* right document and section;
  - *What:* the issue is stated accurately;
  - *Why:* the impact or risk reasoning is correct.
- **G2. Two recall numbers:**
  - **detection recall:** Located and What pass;
  - **full-credit recall:** all three pass.
- **G3. Invented finding:** matches no key item and is ruled not real. It is measured and reported, with a threshold set after the baseline. A real but unplanted issue is never counted as invented (K5).
- **G4. Where grading happens:**
  - **Primary:** the worker artifacts. Overall recall uses the union of findings across all three workers; per-worker recall uses the items carrying that worker's tags.
  - **Secondary:** the final report, for **synthesis retention**: of the key items the workers caught, the share that reached `Security_Threat_Model.md`.
- **G5. Judge calibration:** the operator hand-grades about 10–20 findings, pass/fail on each check. An LLM judge is used for bulk grading only after it agrees with those grades well enough.

### Gate and thresholds

- **T1. Gate:** detection recall on planted items ≥90%, averaged over 3 runs, with no single run below 80%.
- **T2. Weighting:** all issues weigh the same; no severity weighting in v0.
- **T3. Set after the baseline:**
  - the full-credit recall threshold;
  - the invented-findings threshold;
  - the synthesis-retention threshold.

### Model and budget

- **M1. Model under test:** DeepSeek v4.1 Flash (`deepseek/deepseek-v4.1-flash-1017`) for every agent, as committed in `sdaa/config/config.yaml`.
  - It's weak but cheap, and a stronger model is planned later. The model per agent must therefore be an easy-to-change, recorded variable of each run.
  - The first baseline may well fail the gate. That's useful: it shows how far the model is from the bar.
- **M2. Budget:** at most $1.50 per run, provisional.
  - A **run** is one full audit of one corpus variant.
  - A v0 evaluation is at least 3 clean runs plus 3 seeded runs, plus judge calls.
  - Revisit the budget once cost can be measured (P1).

### Operator time

- **O1. About 2 hours for v0:**

  | Task | Time |
  |---|---|
  | Review the drafted planted issues and key entries | ~60 min |
  | Rule on the clean-run findings | ~30 min |
  | Grade the calibration set | ~30 min |

  The AI drafts; the operator approves. Drafted key entries are not ground truth until the operator approves them.

## 3. Prerequisites

These block the first real run.

- **P1. Capture token usage and cost.**
  - **Today:** all 214 Langfuse generations since 2026-11-08 show $0 cost and 0 tokens. `OpenRouterModel.generate_content_async` (`sdaa/src/utils/openrouter_model.py:131`) records `model_name` and the input and output messages, but nothing from `response.usage`.
  - **What OpenRouter sends:** a `usage` object with every response, including `cost` in USD, with no parameters needed.
  - **What Langfuse accepts:**
    - token usage via `gen_ai.usage.*`, `llm.token_count.*` or `langfuse.observation.usage_details`;
    - cost via `gen_ai.usage.cost` or `langfuse.observation.cost_details`.
  - **Choice of cost source:** sending OpenRouter's cost avoids a custom model price definition in Langfuse. Langfuse uses a sent cost in preference to one it calculates.
  - The streaming path is not instrumented (TODO at the stream branch). Tool calls force non-streaming.
- **P2. Point a run at a different corpus and output directory without editing tracked config.** Today `docs_root`/`output_dir` come only from `sdaa/config/config.yaml`. The Roadmap puts `--docs-root`/`--output-dir` in Strategic 3; evals need them now, because the corpus and outputs live in the vault (C5).
- **P3. A run record.** Each run records:
  - code commit;
  - model per agent;
  - prompt name and **version** for each agent, not just the movable `production` label;
  - corpus snapshot ID and hash, and which variant (clean or seeded);
  - answer-key version;
  - token usage and cost;
  - outcome.
- **P4. Repeat runs.** At least 3 per configuration, with the spread reported.

Not blocking: **Tactical 2** (local prompt fallbacks). It matters for an offline CI gate, but the Langfuse prompts work today.

## 4. Existing assets

- **Headless mode:**
  - `python main.py --headless --no-rich` exits 0 only with a valid ToC and all four outputs, 1 on failure, 2 on conflicting flags.
  - `--refresh-toc`/`--refresh-audit` force regeneration, so each eval run can start fresh.
- **Outputs:**
  - worker artifacts `artifacts/{permissions,constraints,boundaries}_agent.md`;
  - final report `reports/Security_Threat_Model.md`;
  - `ToC.json`.

  All are free-form Markdown, except the ToC, which is JSON.
- **Langfuse:**
  - 5 production prompts (`permissions-agent`, `negative-constraints-agent`, `security-boundaries-agent`, `coordinator-agent`, `report-synthesizer`);
  - OpenTelemetry traces with prompt-to-generation links;
  - the CLI (`@langfuse/cli` 1.3.1) and the Langfuse agent skill are available;
  - no datasets, score configs or annotation queues exist yet.
- **File access:** `tools/file_ops.py` enforces corpus containment (Tactical 1), so an eval corpus outside the repo is safe to point at.

## 5. What the detailed design must decide

1. **Finding-to-key matching.** How a free-text Markdown finding is matched to a key item: by the judge, by rules, or a hybrid. Also how one finding covering two items is counted, and how two findings covering one item are counted. This is the core problem.
2. **Tag vocabulary.** The fixed list, its definitions, and which worker each tag belongs to.
3. **Answer-key schema.** Fields per item: ID, origin, tags, location, what, why, variant, key version, adjudication status, plus the file format.
4. **Planting method.** How planted issues are drafted, how difficulty is varied, how cross-page contradictions are built, and how the seeded variant is produced reproducibly from the clean snapshot.
5. **Judge design.** Judge prompt and model, the three binary checks, the calibration protocol (agreement measure, target, what happens on disagreement), and where judge prompts are versioned.
6. **Harness architecture.** What lives in the public repo (code) and what in the vault (data, outputs). How a run is driven (headless CLI with P2's overrides), collected, graded and recorded (P3).
7. **Langfuse mapping.** Whether and how to use datasets, experiments, scores and annotation queues: for example, the operator's rulings and calibration grades as an annotation queue, and per-run scores attached to traces.
8. **Metrics and report.** How detection recall, full-credit recall, invented count and synthesis retention are computed and presented per run and across runs, including the spread.
9. **Phased build plan.** Small, independently verifiable phases with exit criteria, starting with P1–P3, and an estimate of model and operator cost per phase.

## 6. Out of scope for v0

- the structured findings schema and citation validation (the rest of Strategic 1; v0 baselines the current Markdown output first);
- severity grading;
- online or production evaluation;
- a CI gate;
- comparisons across models beyond the DeepSeek baseline;
- SSO/SCIM and data-connection pages.

## 7. Known risks

- **A small key is brittle.** With 12 items, one miss is about 8 points of recall.
- **Planted issues may be unrealistic:** too obvious inflates recall, too subtle deflates it.
- **Bias in native discovery:** natives DocsDiver can't see stay unknown (K5 mitigates).
- **The judge may drift or disagree with the operator.** Calibrate before trusting it (G5).
- **Hex's live docs change.** Always evaluate against the frozen snapshot.
- **Cost is unknown until P1 lands.** The $1.50 budget is unverified.
