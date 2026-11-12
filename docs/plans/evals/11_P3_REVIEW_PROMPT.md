# Prompt: Independent Review of the P3 Plan (for Fable 5.2)

Status: ready to run · Created 2026-11-12 · Subject: `10_P3_RUN_MANIFEST_PLAN.md` · Expected output: `12_P3_PLAN_REVIEW.md`

## How to run it

- **Model:** Fable 5.2 (`claude-fable-5-2`), at high effort.
- **Where:** a fresh Claude Code session started in the review worktree, `/home/guid/projects/DocsDiver-review`. It is a checkout of `origin/ADK_master` that contains this prompt and both plans. Don't use the main checkout: P2 is being implemented there.
- **What to paste:** everything below the line, into the new session.

---

You are reviewing an implementation plan before anyone writes code. Nobody in this session has seen the conversation that produced the plan. Everything you need is in the repository, the installed libraries and the public docs listed below.

Your job is to decide whether the plan is sound. If changes are needed, recommend them in a written report. Be independent: the plan's author checked its facts, and you should check them again rather than trust them. The author's last plan, for P2, had two wrong facts about the test fixtures that an implementer only found by running the suite. Look hard at how the plan's tests interact with existing fixtures and mocks.

## Background

- **DocsDiver** is a Python CLI built on Google ADK. It audits Markdown documentation with several LLM agents and calls models through OpenRouter using its own adapter, `OpenRouterModel`. It exports OpenTelemetry traces to Langfuse.
- The project is building an **evaluation suite**. Its design is in `docs/plans/evals/05_EVAL_DESIGN.md`.
- **Phases done or in progress:**
  - **P1** (merged) records token usage and USD cost on each model call's span. Plan: `06_P1_USAGE_COST_PLAN.md`.
  - **P2** (being implemented now, not merged) adds `--docs-root` and `--output-dir`. Plan: `09_P2_PATHS_PLAN.md`; its §4.1 and §4.2 hold the verified code. **P3 is built on top of P2**, so read `main.py` as it will look with P2's §4.1 applied.
- **The plan under review is `docs/plans/evals/10_P3_RUN_MANIFEST_PLAN.md`.** It adds:
  - `--run-id`, with one Langfuse session per run;
  - session and tags on every span;
  - a call ledger;
  - `run_manifest.json` on every headless exit.
- **The operator has approved the eight decisions in §7.** Challenge one only if you find a concrete defect, not a preference.
- **Langfuse Cloud becomes v4-only on 2026-11-16.** P1 already sends the v4 ingestion header.

## Read first

1. `docs/plans/evals/10_P3_RUN_MANIFEST_PLAN.md`, the plan in full.
2. In `docs/plans/evals/05_EVAL_DESIGN.md`:
   - §2 rows V4, V5 and V6;
   - §3.6 from "_P3, run manifest._" to the end of "Reproducibility";
   - §3.7;
   - the §4 P3, H1 and H2 rows;
   - §6.
3. `docs/plans/evals/09_P2_PATHS_PLAN.md` §2–§4, which is the base P3 builds on.
4. `AGENTS.md`: the rules for running tests, logging work and changing the adapter.
5. Source:
   - `main.py`
   - `sdaa/src/core/instrumentation.py`
   - `sdaa/src/core/model_factory.py`
   - `sdaa/src/core/output_validation.py`
   - `sdaa/src/core/map_maker.py`
   - `sdaa/src/utils/openrouter_model.py`
   - `sdaa/src/utils/mock_model.py`
   - `sdaa/src/utils/prompt_manager.py`
   - `sdaa/src/agents/workers.py`
   - `sdaa/src/agents/coordinator.py`
6. Tests, **especially the fixtures and mocks**:
   - `tests/conftest.py`, including every autouse fixture;
   - `tests/test_main_headless.py`
   - `tests/test_factory_and_integration.py`
   - `tests/test_openrouter_usage.py`
   - `tests/test_instrumentation.py`
   - every other test that patches `main.config_loader`, `get_model_for_agent`, `setup_instrumentation`, `Runner`, `InMemorySessionService` or the model classes.
7. Installed libraries, at the `requirements.lock` versions:
   - `google/adk/sessions/in_memory_session_service.py` (`google-adk` 2.14.0): any constraint on session IDs;
   - `openinference/instrumentation/google_adk/` (1.1.2): which spans it creates, and whether any are created outside the global tracer provider;
   - the `langfuse` 5.2.0 package: `LangfuseOtelSpanAttributes`, and the span processor the `Langfuse()` client adds;
   - `opentelemetry-sdk`: `SpanProcessor.on_start` semantics.
8. Public documentation. Fetch the current pages; don't rely on memory.
   - Langfuse OpenTelemetry integration, especially "Propagating Trace Attributes to All Spans" and "Trace-Level Attributes": <https://langfuse.com/integrations/native/opentelemetry.md>
   - Langfuse v4 migration for OpenTelemetry users: <https://langfuse.com/integrations/native/opentelemetry/migration-to-v4.md>
   - Langfuse sessions: <https://langfuse.com/docs/observability/features/sessions.md>
   - OpenRouter response format, for the `provider` field: start from <https://openrouter.ai/docs>

**Environment.** This worktree has no `.venv` and no `.env`. Use the main checkout's interpreter, `/home/guid/projects/DocsDiver/.venv/bin/python`, which matches `requirements.lock`. For read-only Langfuse queries, use `langfuse --env /home/guid/projects/DocsDiver/.env ...`. Never copy, print or modify `.env`.

## What you may and may not do

**You may:**
- read any file in the repository and the installed packages;
- run the full test suite, but **only in a disposable copy** made with the `tar` command in `AGENTS.md` (run it from this worktree), using the interpreter above;
- write throwaway scripts in a temporary directory outside the repository. The strongest evidence:
  - for D2: a real `TracerProvider` with an in-memory exporter, the OpenInference instrumentor and the proposed processor, showing which spans carry `session.id`;
  - for D6: a sketch of the `main()` split, run against the existing headless tests in a disposable copy.
- run the Langfuse CLI read-only (`api <resource> list|get`);
- fetch public documentation.

**You may not:**
- edit, create or delete any file in either checkout, except the report you write in this worktree;
- commit, push or open a PR;
- call OpenRouter with a key, run DocsDiver against a real model, or spend money in any other way;
- write anything to Langfuse;
- touch `/home/guid/projects/DocsDiver` (the main checkout) except to read it and use its `.venv` interpreter;
- write anything under `~/CoS_brain/`.

## What to check

Answer each question with evidence: a file and line number, a doc URL with the passage, or a script and its output.

1. **Facts.** Is each of F1–F12 in plan §2 correct for the pinned versions and for `main.py` with P2 applied?
2. **Session and tags (D1, D2).**
   - Does stamping every span in `on_start` give Langfuse v4 one session per run, with every observation (Map Maker roots, `call_llm`, adapter spans) in it?
   - Is it equivalent to the baggage or `propagate_attributes()` approach the docs recommend?
   - Is `session.id` accepted as well as `langfuse.session.id`?
   - Does any span bypass the processor? Consider spans created before `setup_instrumentation`, and the processor `Langfuse()` adds.
   - Is the run-ID pattern safe as an ADK session ID and a directory name?
3. **Ledger (D3–D5).**
   - Is every model call recorded exactly once, including Map Maker's direct calls and the synthesizer's repeated instruction builds?
   - Can `_agent` be set on these pydantic `BaseLlm` subclasses as written?
   - Does the prompt version per call really reflect what each call used?
   - What happens with key rotation retries, provider errors and streaming?
   - Does clearing the ledger at the start of `main()` cover the tests?
4. **Manifest writing (D6, D7).**
   - Does the `main()`/`_run` split write a manifest on every headless exit listed in F9 and none on exit 2?
   - Does it change behaviour that existing tests check?
   - Is the exit code right for `SystemExit` with a `None` or string code?
   - Is recomputing problems at write time correct for `--toc-only` and for a Map Maker failure?
5. **Modification times (F11).** Is "generated if the modification time is at or after `started_at`" correct? Check:
   - filesystem timestamp resolution;
   - `set_aside` followed by regeneration;
   - outputs that are reused and never touched.
6. **Tree hash (D8).** Is the definition fully specified: encoding, path separator, sorting, empty directories, symlinks, non-Markdown files? Can H1 reproduce it exactly by importing it?
7. **Manifest content.** Is anything the eval runner (H2 validity rules in design §3.6, "Run" step 4) or the report needs missing from the schema? Is anything there that could leak eval information into what the model sees (design V6)?
8. **Tests (§4.7).**
   - Would any test still pass with a broken implementation?
   - Do any collide with existing fixtures? Check `conftest.py`'s autouse `_isolated_output_dir`, `_stub_prompts`, and mocks of `config_loader`.
   - Is the mutation-check expectation (all fail except I2) right?
   - Is a case missing?
9. **Live check (§6).** Is it correct, safe for the operator's `.env` and outputs, and under $0.05? Can the Langfuse CLI filter observations by session as described?
10. **Project rules.** Does the plan comply with `AGENTS.md`? That covers:
    - tests in a disposable copy;
    - the logbook script and `archive/PROGRESS.md`;
    - the adapter invariants;
    - provider failures propagating.
11. **Anything missing** that would make an implementer stop, guess or get it wrong.

## Report: `docs/plans/evals/12_P3_PLAN_REVIEW.md`

Write it in this worktree. Use this structure:

1. **Verdict:** one of *Approve*, *Approve with changes* or *Rework*, with at most three lines of reasons.
2. **Fact check:** a table of F1–F12 with confirmed, wrong or unverifiable, and the evidence for each.
3. **Findings.** One entry per finding:
   - an ID;
   - severity: *blocker* (the plan would fail or mislead), *major* (an implementer would likely get it wrong) or *minor*;
   - the plan section it concerns;
   - the problem;
   - the evidence;
   - the recommended change, written as concrete replacement text or code for the plan.
4. **Decisions in §7:** for each of 1–8, either "no concern" or the concrete defect.
5. **Questions in §8:** an answer to each, with evidence.
6. **What you verified and how:** commands, scripts (inline, short) and their output.
7. **Not verified:** anything you could not check, and why.

Rules for the report:
- Findings must rest on evidence. Leave out preferences and style.
- "No change needed" is a valid outcome. Don't pad the report.
- Don't edit `10` yourself. The operator and the plan's author will apply the changes you recommend.
- Write plainly: short sentences, one idea per bullet, no marketing language.

## When you finish

Reply in chat with:
- the path of the report;
- the verdict;
- the number of findings by severity;
- the three most important findings in one line each.
