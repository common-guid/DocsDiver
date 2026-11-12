# Prompt: Apply the Fable Review to the P3 Plan (for an external agent)

Status: ready to run · Created 2026-11-12 · Edits: `10_P3_RUN_MANIFEST_PLAN.md` · Source: `12_P3_PLAN_REVIEW.md`

## How to run it

- **Where:** a fresh session in the review worktree, `/home/guid/projects/DocsDiver-review`. Not the main checkout: P2's branch is checked out there.
- **What to paste:** everything below the line.

---

You are editing one planning document. You write no code.

## Context

- `docs/plans/evals/10_P3_RUN_MANIFEST_PLAN.md` is an implementation plan for eval phase P3 of DocsDiver. P3 adds:
  - a `--run-id` flag, with one Langfuse session per run;
  - session and tags on every span;
  - a call ledger;
  - `run_manifest.json`.
- `docs/plans/evals/12_P3_PLAN_REVIEW.md` is an independent review of that plan. Its verdict is "approve with changes", with 15 findings: B1, B2, M1–M6 and m1–m7.
- **The operator has accepted all 15 findings.** Your job is to apply them to `10` so that an implementer can follow `10` alone, without reading `12`.

## Rules

- **Edit only `docs/plans/evals/10_P3_RUN_MANIFEST_PLAN.md`.** Don't touch `12`, any code, any test, or any other file.
- Don't commit, push or open a PR. The planner reviews your diff and commits it.
- Don't run DocsDiver, call any model or spend money. You don't need to run tests.
- **Use the review's replacement text and code verbatim** wherever it gives some. Each finding's "Change" bullet says what to replace or add.
- **Don't invent fixes** beyond the review. If a finding is ambiguous or conflicts with another, apply the reading below. If it's still unclear, leave a line starting `> **OPEN:**` at that spot and list it in your reply.
- Keep the plan's existing structure, headings and writing style: short sentences, one idea per bullet.

## Where each finding goes

| Finding | Apply to |
|---|---|
| B1 | §4.7: add the "Existing tests to update (2)" block. §9: say the two tests are edited. |
| B2 | Replace F11 with a fact saying modification times can't tell a replayed artifact from a regenerated one (`artifact_loader_model.py:41-52`, `reporting.py:52-87`). Replace the `status` bullet under "Manifest shape" with the review's text. D6 and §4.6: `_run(args, parser, run_id, regenerated)`. §4.1: `write_manifest` takes `generated: set[str]` instead of reading modification times. Add test **M8**. |
| M1 | D2: "keeps the existing `langsmith.span.tags` branch unchanged". Add to F2 that the existing root check (`parent_context is None`) matches most spans, so today only `call_llm` lacks tags (review S1). Replace I1's last sentence with the review's text. |
| M2 | §4.1: add `prompt_ref`. §4.2 and §4.3: build the entry with `prompt_ref` and call `record_call` inside one `try/except Exception` that logs a warning. |
| M3 | Replace the first paragraph of §4.7 with the review's text. M4's row expects `SystemExit(1)`. |
| M4 | D6: replace step 4 with the review's code block. Extend F9: "uncaught exception" includes `BaseException`. Add test **M9**. |
| M5 | Add F6's gap (the synthesizer keeps a stale prompt). Add a new subsection **§4.4b `sdaa/src/agents/coordinator.py`** with the one-line reset. Add a unit test, named **C1**, in `tests/test_run_manifest.py`. |
| M6 | Replace the Langfuse bullet in §6 step 4 with the review's text, including the paragraph about the health check and `code: {commit: null, dirty: null}`. |
| m1 | Replace F1's second and third sentences with the review's text. Change `main.py:195` to `main.py:219 (P2 version)`. |
| m2 | §4.7, the mutation-check paragraph: replace it with the review's expected outcome. I2 constructs `TaggingSpanProcessor()` with no argument. |
| m3 | D3: "clear in place (`LEDGER.clear()`); never rebind the name". §4.7: the conftest autouse fixture that clears the ledger before each test. |
| m4 | D8: replace the prose definition with the review's `tree_hash` code and the paragraph after it. Move the computation to the wrapper, before `_run` (§4.6). The manifest records nulls on failure. |
| m5 | Add to F8 that OpenRouter's published schema has no top-level `provider`. Add the "report how many ledger entries have a non-null `provider`" line to §6 step 4. |
| m6 | D3: the `InstrumentedGemini` note and the H2 validity note. |
| m7 | M2's row: the two spies. Add test **M10**. Fold "a run without `--headless` writes no manifest" into **M7's** row; don't create a separate test. |

Also apply these two points from the review's §6 ("Project rules"):
- In §4.2, the streaming branch records its unmetered entry **before** iterating the stream.
- Correct the `main.py` line numbers in F9 to the P2 version: `sys.exit(1)` at `188, 198, 257, 291, 305`.

## Consistency edits after the findings

- **Status line:** "Reviewed by Fable 5.2 (`12_P3_PLAN_REVIEW.md`, approve with changes); all 15 findings applied 2026-11-12. Ready to implement after P2 merges."
- **§7:**
  - Decision 4 becomes "Generated or reused from a set that `_run` fills (replaces modification times, review B2)".
  - Decision 5 gains "plus a reset in the synthesizer (review M5)".
  - Keep the "Approved" column and add "(revised after review)" to those two rows.
- **§8:** replace the three questions with one line: "Answered in `12_P3_PLAN_REVIEW.md` §5."
- **Test totals:** the new tests are M1–M10, A1–A3, I1–I2, F1 and C1, which is **17**. Set §4.7, step 5 and §9 to "baseline + 17", with the two existing tests edited (B1).
- **§9 acceptance criteria:** update them to match:
  - the test list;
  - the mutation-check expectation from m2;
  - "the manifest's `outputs` statuses match the `reused`/`generated` line `main.py` prints".
- **Facts:** every fact the review marked wrong or partly wrong (F1, F2, F11) must read correctly after your edits. Don't leave an old sentence that contradicts a new one.
- **Search for leftovers:** search the plan for "modification time", "mtime", `parent_context`, "baseline + 13" and "root spans only". Each remaining mention must agree with the revised design.

## When you finish

Reply with:
- for each of the 15 findings plus the two §6 points, the plan section(s) you changed, one line each;
- any `> **OPEN:**` lines you left, and why;
- `git diff --stat`.
