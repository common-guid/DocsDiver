# Prompt: Detailed Eval Design (for Fable 5.2)

Status: ready to run · Created 2026-11-10 · Input: `03_EVAL_DESIGN_BRIEF.md` · Expected output: `05_EVAL_DESIGN.md`

## How to run it

- **Model:** Fable 5.2 (`claude-fable-5-2`), at high effort.
- **Where:** Claude Code, started from the DocsDiver repo root on `ADK_master`, so the model can read the code and check claims against it.
- **Without repo access** (e.g. claude.ai): attach `03_EVAL_DESIGN_BRIEF.md`, `ROADMAP.md`, `AGENTS.md`, `main.py`, `sdaa/src/tools/reporting.py`, `sdaa/src/utils/openrouter_model.py` and `sdaa/config/config.yaml`, and change the output step to "reply with the document".
- Copy everything below the line into a new session.

---

You are designing the first quality evaluation for DocsDiver, a multi-agent CLI that audits Markdown product documentation for security issues. The design you write will be reviewed by the operator, a security engineer who owns the project, and then implemented phase by phase by a coding agent. Write it for both readers.

## Your task

Produce the detailed eval design for v0, as specified in `docs/plans/evals/03_EVAL_DESIGN_BRIEF.md`, and write it to `docs/plans/evals/05_EVAL_DESIGN.md`.

This is a design task. Do not change code, tests, config or any other file, do not commit, and do not run DocsDiver or anything else that calls a model or spends money.

## Read first

1. `docs/plans/evals/03_EVAL_DESIGN_BRIEF.md`: the settled decisions and the nine things you must decide. **This is your specification.**
2. `docs/plans/evals/01_EVAL_BRAINSTORM.md` and `02_FOLLOWUP_QUESTIONS.md`: how those decisions were reached, and the operator's own words.
3. `AGENTS.md`, then `ROADMAP.md` §3 Strategic Feature 1 and §4.
4. The code paths the eval touches: `main.py` (headless mode, refresh flags, exit codes), `sdaa/src/core/config_loader.py`, `sdaa/src/core/output_validation.py`, `sdaa/src/tools/reporting.py`, `sdaa/src/tools/file_ops.py`, `sdaa/src/agents/workers.py`, `sdaa/src/utils/openrouter_model.py`, `sdaa/src/core/instrumentation.py`, `sdaa/config/config.yaml`. (`sdaa/src/schemas/findings.py` doesn't exist yet; the Roadmap only proposes it.)
5. Langfuse documentation, current versions only: start from `docs/llms-txt/langfuse-llms.txt` and fetch the pages on datasets, experiments, scores, score configs, annotation queues, LLM-as-a-judge and OpenTelemetry usage and cost attributes. Don't design from memory; Langfuse changes often. Name the exact SDK or API version for anything you propose to use.

Verify what the brief says about the code against the source. If they disagree, the source wins; note the disagreement.

You may use the Langfuse CLI read-only (`langfuse --env .env api <resource> list|get`) to look at existing prompts, traces and observations. Don't create, update or delete anything in Langfuse.

You may browse <https://learn.hex.tech/docs> to check that the v0 slice (brief C3) is about 20–40 pages and to understand its structure. Don't copy Hex text into any file.

## Hard constraints

These are settled. Design within them.

- **Nothing derived from Hex goes into the repo.** No Hex text, page lists, planted issues or answer-key content in `05_EVAL_DESIGN.md` or anywhere else in the repo, which is public. Use synthetic placeholders in examples. If you produce a Hex page list, put it in your final chat reply, not in a file.
- **Don't write to the vault** (`~/CoS_brain/`). Data locations there are part of the design, but the operator creates them.
- **The model under test is DeepSeek v4.1 Flash for every agent** (brief M1). The model per agent must be a recorded, easily changed variable.
- **Operator time is about 2 hours in total** (brief O1). Any step that needs the operator must fit that budget. Show the arithmetic.
- **Budget:** at most $1.50 per audit run, provisional (brief M2). Estimate judge cost separately.
- **v0 grades the current free-form Markdown output.** The structured findings schema is out of scope (brief §6); don't make v0 depend on it.

## What to decide

Answer each of the nine items in brief §5. For each one:
- give your recommendation and the reason for it;
- name the alternatives you rejected, in a line each;
- say how the implementer will know it works (a test, a check, an acceptance criterion).

Where you are unsure, or the choice is the operator's, say so and list it under open questions rather than guessing.

### Hard parts not to skip

The brief leaves these implicit. Address each one explicitly:

1. **Segmentation comes before matching.** Worker artifacts are free-form Markdown. Before any finding can be matched to a key item, something must split an artifact into individual findings. Decide how, and how a segmentation error shows up in the metrics instead of silently changing recall.
2. **Many-to-many matching.** One finding can cover two key items; two findings, from one worker or several, can cover one item. Define exactly what counts as a hit for recall, and what counts for the invented-findings count.
3. **Clean and seeded interact.** A planted edit can create, hide or alter a native issue on the same page. Say how the key and the grading handle that, so a native issue never counts as a planted miss or as invented.
4. **Small numbers.** About 12 planted items and 3 runs per variant: one miss is about 8 points. Say how results are reported so the operator isn't misled: counts beside percentages, the per-run spread, and which differences are too small to mean anything.
5. **Key leakage.** DocsDiver must never see the answer key, file names or other traces of what was planted. The judge must see the key. Design the directory layout and the harness so the two can't mix.
6. **Judge independence and cost.** Whether the judge may be the same model family as the model under test, which model it should be, and its cost per graded run.
7. **Reproducibility.** Every number in a report must trace back to a run record (brief P3): the corpus hash and variant, the key version, the prompt versions and the judge version.

## Challenges to the brief

If you think a settled decision is wrong, don't quietly design around it. Put it in a "Challenges to the brief" section: the decision ID, what you'd change, why, and what it costs. Then design to the brief as written anyway.

## Output: `05_EVAL_DESIGN.md`

Use this structure:

1. **Summary:** the design in at most 10 lines.
2. **Verified facts:** what you checked in the code and the docs, including any place where the brief was wrong.
3. **Design:** one subsection per brief §5 item 1–8, plus the hard parts above where they don't fit an item.
4. **Phased build plan** (brief §5 item 9). Each phase:
   - is small and independently verifiable;
   - lists the files it touches (repo or vault);
   - has exit criteria a reviewer can check;
   - estimates model cost and operator minutes.

   Start with prerequisites P1–P3. The first phase that spends money on a live audit must come after P1, so the spend is measured.
5. **Challenges to the brief.**
6. **Open questions for the operator**, each answerable in a sentence or a choice between options.
7. **Risks** beyond brief §7, if any.

Style:
- plain, direct prose; short sentences; no marketing language;
- one idea per paragraph or bullet;
- tables where they help comparison, e.g. the answer-key schema or the cost per phase;
- example data synthetic only.

Aim for a document the operator can review in 30–40 minutes.

## When you finish

Reply in chat with:
- the path of the file you wrote;
- your three most consequential decisions;
- any challenges to the brief;
- the open questions;
- the Hex page list for the v0 slice, if you made one.
