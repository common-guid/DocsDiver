# Prompt: Independent Review of the P1 Plan (for Fable 5.2)

Status: ready to run · Created 2026-11-11 · Subject: `06_P1_USAGE_COST_PLAN.md` · Expected output: `08_P1_PLAN_REVIEW.md`

## How to run it

- **Model:** Fable 5.2 (`claude-fable-5-2`), at high effort.
- **Where:** a fresh Claude Code session started from the DocsDiver repo root, so the model can read the code, the installed libraries and the plan. `06` may be uncommitted; it is in the working tree.
- **What to paste:** everything below the line, into the new session.

---

You are reviewing an implementation plan before anyone writes code. Nobody in this session has seen the conversation that produced the plan. Everything you need is in the repository, the installed libraries and the public docs listed below.

Your job is to decide whether the plan is sound. If changes are needed, recommend them in a written report. Be independent: the plan's facts were checked by its author, and you should check them again rather than trust them.

## Background

- **DocsDiver** is a Python CLI built on Google ADK. It audits Markdown documentation with several LLM agents, and calls models through OpenRouter using its own adapter, `OpenRouterModel`. It exports OpenTelemetry traces to Langfuse.
- The project is building an **evaluation suite**. Its design is in `docs/plans/evals/05_EVAL_DESIGN.md`. The first build phase, **P1**, makes every model call's token usage and USD cost visible in Langfuse. Today every generation shows $0 and 0 tokens.
- **The plan under review is `docs/plans/evals/06_P1_USAGE_COST_PLAN.md`.** The operator has approved the decisions in its §7. Challenge one only if you find a concrete defect, not a preference.
- **Langfuse Cloud becomes v4-only on 2026-11-16.** Part of P1 is getting ready for that.

## Read first

1. `docs/plans/evals/06_P1_USAGE_COST_PLAN.md`, the plan in full.
2. In `docs/plans/evals/05_EVAL_DESIGN.md`:
   - §2 rows V1, V2, V3, V11;
   - §3.6 "The prerequisites, concretely", the part on P1;
   - §4, the P1 row and its notes;
   - §6, decision 3 (LangSmith).
3. `AGENTS.md`: the rules for running tests, logging work and changing the adapter.
4. Source:
   - `sdaa/src/utils/openrouter_model.py`
   - `sdaa/src/core/instrumentation.py`
   - `sdaa/src/core/map_maker.py` (lines 70–135)
   - `tests/test_langfuse_linking_verification.py`
   - `tests/test_instrumentation.py`
   - `tests/conftest.py`
5. Installed libraries, at the versions in `requirements.lock`:
   - `openinference/instrumentation/google_adk/__init__.py` and `_wrappers.py` (`openinference-instrumentation-google-adk` 1.1.2);
   - `google/adk/flows/llm_flows/core/_model_call.py` and `google/adk/telemetry/` (`google-adk` 2.14.0);
   - `openai/types/completion_usage.py` (`openai` 1.109.1).
6. Public documentation. Fetch the current pages; don't rely on memory.
   - Langfuse OpenTelemetry attribute mapping: <https://langfuse.com/integrations/native/opentelemetry.md>
   - Langfuse token and cost tracking: <https://langfuse.com/docs/observability/features/token-and-cost-tracking.md>
   - Langfuse versions and compatibility: <https://langfuse.com/docs/compatibility.md>
   - OpenRouter usage accounting: <https://openrouter.ai/docs/cookbook/administration/usage-accounting.md>
   - The OpenRouter API reference for `GET /api/v1/key`, found from <https://openrouter.ai/docs>

**Environment.** Use `.venv` if it has the `requirements.lock` dependencies installed. If not, create a throwaway virtual environment **outside the repository** (for example under `mktemp -d`) and install `requirements.lock` into it. Don't modify `.venv`.

## What you may and may not do

**You may:**
- read any file in the repository and in the installed packages;
- run the full test suite, but **only in a disposable copy**, exactly as `AGENTS.md` describes;
- write small throwaway scripts in a temporary directory outside the repository to test how a library behaves. A script that wires a real `TracerProvider` with an in-memory span exporter, the OpenInference instrumentor and a stubbed OpenAI client is the strongest evidence for D1. Use one if you can.
- run the Langfuse CLI read-only (`langfuse --env .env api <resource> list|get`) to look at existing observations;
- fetch public documentation.

**You may not:**
- edit, create or delete any file in the repository, except the report you write;
- commit, push or open a PR;
- call the OpenRouter API with a key, run DocsDiver against a real model, or spend money in any other way;
- write anything to Langfuse;
- touch `docs-for-testing/`, because another agent is changing it on a separate branch;
- write anything under `~/CoS_brain/`.

## What to check

Answer each question with evidence: a file and line number, a doc URL with the passage, or a script and its output.

1. **Facts.** Is each of F1–F11 in plan §2 correct for the pinned versions?
2. **Counting once (D1).** Does usage end up on exactly one span per model call? Check for anything else that could emit usage or let Langfuse infer a cost:
   - ADK's own telemetry, including its schema-v2 agent span and whatever the OpenInference instrumentor disables;
   - the `call_llm` span;
   - the LangSmith exporter.

   Also check that Langfuse classifies `OpenRouterModel.generate_content` as a generation, and that it attaches no inferred cost to `call_llm` when that span has a model name but no usage.
3. **Attribute format (D2).**
   - Are JSON-string values for `langfuse.observation.usage_details` and `langfuse.observation.cost_details` accepted?
   - Are the keys `input`, `output`, `total` and a cost with only `total` right?
   - Does sending `total` cause double counting?
   - Is OpenRouter's `cost` in USD?
   - Is leaving out cached and reasoning tokens safe?
4. **Model name (D3).** Is `llm.model_name` read by Langfuse, and does it conflict with any other attribute on that span?
5. **The helper (D4).**
   - Edge cases: a cost of 0, a missing `usage`, an unusual `choices`.
   - Is the call placed so it can't be skipped on the success path, and can't break the response?
   - Does provider-error propagation stay unchanged?
6. **Header (D5).** Is the header name and value right? Does it work with the pinned OTLP exporter, and leave the LangSmith exporter unaffected?
7. **Tests (§4.3).** Would any test still pass with a broken implementation? Is a case missing? Is the mocking approach sound?
8. **Live check (§6).**
   - Is `data.usage` from `GET /api/v1/key` the right ground truth? Is it updated immediately, and what about several rotated keys?
   - Is the tolerance realistic?
   - Are the expected observation counts right?
   - Is the procedure safe for the operator's `.env` and local outputs?
9. **Scope and decisions (§3 D6, §7).** Does any decision create rework for P3 (run manifest and ledger) or for the later removal of the duplicate span?
10. **Project rules.** Does the plan comply with `AGENTS.md`? That covers:
    - running tests in a disposable copy;
    - the logbook script and `archive/PROGRESS.md`;
    - the adapter invariants: tool-call IDs, reasoning round-trips, empty-string assistant content;
    - provider failures propagating.
11. **Anything missing** that would make an implementer stop, guess or get it wrong.

## Report: `docs/plans/evals/08_P1_PLAN_REVIEW.md`

Use this structure:

1. **Verdict:** one of *Approve*, *Approve with changes* or *Rework*, with at most three lines of reasons.
2. **Fact check:** a table of F1–F11 with confirmed, wrong or unverifiable, and the evidence for each.
3. **Findings.** One entry per finding:
   - an ID;
   - severity: *blocker* (the plan would fail or mislead), *major* (an implementer would likely get it wrong) or *minor*;
   - the plan section it concerns;
   - the problem;
   - the evidence;
   - the recommended change, written as concrete replacement text or steps for the plan.
4. **Decisions in §7:** for each of 1–7, either "no concern" or the concrete defect.
5. **What you verified and how:** commands, scripts (inline, short) and their output.
6. **Not verified:** anything you could not check, and why.

Rules for the report:
- Findings must rest on evidence. Leave out preferences and style.
- "No change needed" is a valid outcome. Don't pad the report.
- Don't edit `06` yourself. The operator and the plan's author will apply the changes you recommend.
- Write plainly: short sentences, one idea per bullet, no marketing language.

## When you finish

Reply in chat with:
- the path of the report;
- the verdict;
- the number of findings by severity;
- the three most important findings in one line each.
