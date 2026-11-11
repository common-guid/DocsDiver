# Plan: Eval Phase P1, Usage and Cost Capture

Status: approved and reviewed. Fable 5.2 review `08_P1_PLAN_REVIEW.md` (approve with changes); all nine findings applied 2026-11-11. Ready to implement · Created 2026-11-11 · Base: `ADK_master` · Design: `05_EVAL_DESIGN.md` §3.6 ("P1, usage and cost") and §4 · Decisions: §7 (all recommendations approved by the operator, 2026-11-11)

## 1. Goal

Every OpenRouter model call shows up in Langfuse with its tokens, its USD cost and its model name, counted **once**. Spans also reach Langfuse Cloud in real time after its v4 cutover on 2026-11-16.

Today all generations show $0 and 0 tokens. That makes the eval budget (M2) unmeasurable, and a P1 live check is the first step in the build plan that spends money.

## 2. Facts checked on 2026-11-11

| # | Fact | Evidence |
|---|---|---|
| F1 | The adapter opens its own span, `OpenRouterModel.generate_content`, with attributes `openinference.span.kind: LLM` and `model_name`. Langfuse doesn't read `model_name`. It reads `langfuse.observation.model.name`, `gen_ai.request.model`, `gen_ai.response.model`, `llm.model_name` or `model`. | `sdaa/src/utils/openrouter_model.py:131-138`; Langfuse OpenTelemetry attribute mapping table |
| F2 | The non-streaming branch never reads `response.usage`. | `openrouter_model.py:339-396` |
| F3 | OpenRouter returns `usage` on every Chat Completions response, with no parameter. It includes `prompt_tokens`, `completion_tokens`, `total_tokens`, `prompt_tokens_details.cached_tokens`, `completion_tokens_details.reasoning_tokens`, `cost` (USD) and `cost_details`. The old `usage: {include: true}` parameter is deprecated and has no effect. | OpenRouter "Usage Accounting" page |
| F4 | The pinned `openai` 1.109.1 keeps the extra `cost` field: `response.usage.cost` is readable on `CompletionUsage`. | Checked with `ChatCompletion.model_validate` in the lock venv |
| F5 | The ADK `call_llm` span is opened by the OpenInference instrumentor (`openinference-instrumentation-google-adk` 1.1.2). It sets `llm.model_name` from the request, and sets `llm.token_count.*` **only** from `LlmResponse.usage_metadata`. The adapter never sets `usage_metadata`, so `call_llm` carries no usage. The adapter's span is a child of `call_llm`. | `.../google_adk/__init__.py:106-138`; `.../google_adk/_wrappers.py:497-500, 649-708` |
| F6 | Map Maker calls the adapter directly, so its span has no `call_llm` parent and starts its own trace. | `sdaa/src/core/map_maker.py:108` |
| F7 | **Usage attributes Langfuse reads:** `langfuse.observation.usage_details` (JSON string), `gen_ai.usage.*` or `llm.token_count.*`. | Langfuse OpenTelemetry mapping; Langfuse "Token & Cost Tracking" |
| F8 | **Cost attributes Langfuse reads:** `langfuse.observation.cost_details` (JSON string) or `gen_ai.usage.cost`. An ingested cost takes priority over one Langfuse infers. Langfuse no longer estimates tokens from text. | Same pages |
| F9 | Langfuse Cloud becomes v4-only on 2026-11-16. OpenTelemetry ingestion keeps working. Without the header `x-langfuse-ingestion-version: 4`, data can appear 10–15 minutes late. Our exporter sends only `Authorization`. | Langfuse "Versions & Compatibility" and OpenTelemetry pages; `sdaa/src/core/instrumentation.py:134-137` |
| F10 | The streaming branch is not instrumented. Tool calls force non-streaming, and headless runs never stream. | `openrouter_model.py:314-316, 332-338` |
| F11 | Existing tests constrain the change. `tests/test_langfuse_linking_verification.py:84-111` mocks the response with `MagicMock`, so the new code must tolerate a `usage` that isn't real data. `tests/test_instrumentation.py:28-32` checks the exporter headers. | Source |
| F12 | A second exporter exists. The Langfuse SDK client created for prompt fetching (`Langfuse()` at `sdaa/src/utils/prompt_manager.py:33`) adds its own `LangfuseSpanProcessor` to the same `TracerProvider`. It already sends the v4 header. Its default filter exports `call_llm`, which comes from known LLM instrumentation, but not the adapter span or Map Maker spans. Those go only through `instrumentation.py:134-137`. So `call_llm` reaches Langfuse twice, with the same span ID. | `langfuse/_client/resource_manager.py:245-262`, `span_filter.py:104-108`; review `08` §5.5 |

## 3. Design

**D1. Usage and cost go on the adapter's span only.** `LlmResponse.usage_metadata` stays unset, so `call_llm` stays usage-free (F5).
- *Why:* if both spans carried tokens, Langfuse would count them twice. If Langfuse has a price for the model, it would also infer a second cost on `call_llm`.
- *Rejected:* filling `usage_metadata` and dropping the adapter's span. It's cleaner in the long run, because it also removes the duplicate generation. But it means moving prompt linking and the OpenAI-format messages onto `call_llm`, which is more change than P1 needs (§7, decision 5).

**D2. Attributes**, set once the response is back:
- `langfuse.observation.usage_details` = `{"input": prompt_tokens, "output": completion_tokens, "total": total_tokens}`, as a JSON string.
- `langfuse.observation.cost_details` = `{"total": usage.cost}`, as a JSON string. Set only when `cost` is a number.
- Cached and reasoning token counts are left out:
  - `completion_tokens` already includes reasoning tokens;
  - the cost comes from OpenRouter, so Langfuse needs no per-type breakdown to price anything;
  - extra usage keys risk being summed twice into Langfuse's totals.

**D3. Model name:** set `llm.model_name` to the requested model slug (`self.model`) when the span opens, replacing `model_name`. This is the same convention the `call_llm` span uses (F5).

**D4. Recording usage never breaks a model call.**
- One helper reads only numeric values, skips anything else, and logs a warning on an unexpected error.
- Provider errors still propagate, as `AGENTS.md` requires. Only the bookkeeping is guarded.

**D5. Header:** add `"x-langfuse-ingestion-version": "4"` to the Langfuse exporter headers (F9). The adapter span and Map Maker spans reach Langfuse only through this exporter (F12), so the header is required here.

**D6. Not in P1:**
- **The run ledger.** It is in `05`'s P1 row; this plan moves it to P3 (§7, decision 1).
- **Usage on the streaming path** (F10).
- **Removing the duplicate generation** (§7, decision 5).
- **Langfuse sessions per run** (P3).
- **The Langfuse 403/400 export errors.** That is a separate task; P1 only records whether they occur.
- **Tags on every span.** `langfuse.trace.tags` is set on root spans only (`instrumentation.py:36-41`). Langfuse v4 needs it on each span to filter observations by tag. The header alone does not make the span format v4-ready. A separate task; session propagation is already in P3.

## 4. Changes

### 4.1 `sdaa/src/utils/openrouter_model.py`

1. In the span attributes at `:134-137`, replace `"model_name": self.model` with `"llm.model_name": self.model`.
2. Add a module-level helper:

   ```python
   def _record_usage(span, response) -> None:
       """Copy OpenRouter token counts and USD cost onto the span. Never raises."""
       try:
           usage = getattr(response, "usage", None)
           if usage is None:
               return
           counts = {
               key: getattr(usage, field, None)
               for key, field in (("input", "prompt_tokens"), ("output", "completion_tokens"), ("total", "total_tokens"))
           }
           counts = {k: v for k, v in counts.items() if type(v) is int}
           if counts:
               span.set_attribute("langfuse.observation.usage_details", json.dumps(counts))
           cost = getattr(usage, "cost", None)
           if type(cost) in (int, float):
               span.set_attribute("langfuse.observation.cost_details", json.dumps({"total": cost}))
       except Exception as e:  # observability must not fail a model call
           logger.warning(f"Failed to record OpenRouter usage on span: {e}")
   ```

   `type(v) is int` deliberately rejects `bool` and `MagicMock`.
3. In the non-streaming branch, call `_record_usage(span, response)` as the first statement of the `else:` block (`:340`), before `message = response.choices[0].message`. Usage is then recorded even when parsing the response fails afterwards (an empty `choices`, or tool-call arguments that aren't JSON).
4. At the streaming `TODO` (`:333`), add: `# ponytail: streamed calls record no usage; headless never streams. Read usage from the final chunk if chat cost matters.`

The diff should come to roughly 25 lines. Change nothing else in the adapter. Message translation, tool-call IDs, reasoning round-trips and key rotation stay exactly as they are.

### 4.2 `sdaa/src/core/instrumentation.py`

At `:134-137`:

```python
headers={"Authorization": auth_header, "x-langfuse-ingestion-version": "4"}
```

### 4.3 Tests

**New file `tests/test_openrouter_usage.py`.** Follow the mocking pattern in `test_langfuse_linking_verification.py:78-111`: patch `trace`, capture `span.set_attribute` calls, and mock `client.chat.completions.create`. Build responses with `ChatCompletion.model_validate({...})` so `usage` is a real `CompletionUsage`, as F4 was checked.

| Test | Response | Expected |
|---|---|---|
| `test_usage_and_cost_recorded` | usage 100/20/120, `cost: 0.000016` | Both values are `str`. `json.loads` gives `{"input": 100, "output": 20, "total": 120}` and `{"total": 1.6e-05}`. No attribute key starts with `gen_ai.usage` or `llm.token_count`. |
| `test_usage_without_cost` | usage with no `cost` field | `usage_details` set; `cost_details` not set |
| `test_no_usage` | `usage: null` | Neither attribute set; the response is yielded normally |
| `test_non_numeric_usage_is_ignored` | `MagicMock` response, as in the linking test | Neither attribute set; no exception |
| `test_model_name_attribute` | any | Span opened with `llm.model_name` set to the slug; `model_name` absent |
| `test_usage_metadata_stays_unset` | usage 100/20/120 | The yielded `LlmResponse.usage_metadata is None` (guards D1) |
| `test_provider_error_still_propagates` | `create` raises `RuntimeError` | `RuntimeError` reaches the caller (D4 guards bookkeeping only) |
| `test_usage_recording_failure_does_not_break_call` | usage 100/20/120; `span.set_attribute` raises for keys starting `langfuse.observation.usage` | The response is still yielded; the warning is logged |
| `test_zero_cost_is_recorded` | usage with `cost: 0` | `cost_details` parses to `{"total": 0}` |
| `test_usage_recorded_before_response_parsing_fails` | usage, plus a tool call whose `arguments` is not JSON | `JSONDecodeError` propagates; `usage_details` was set |
| `test_usage_recorded_when_choices_is_empty` | usage, `choices: []` | `IndexError` propagates; `usage_details` was set |

The review (`08` §5.3) confirmed these four extra tests catch the broken variants the first seven miss: no `try/except`, `if cost:` instead of the type check, an extra `gen_ai.usage.*` attribute, a later call site, and a dict instead of a JSON string.

**`tests/test_instrumentation.py`:** in `test_setup_instrumentation_langfuse_only`, also assert `call_args.kwargs['headers']['x-langfuse-ingestion-version'] == "4"`.

### 4.4 Documentation

- **`docs/OBSERVABILITY_AND_PROMPTS.md`**, two sentences:
  - for OpenRouter calls, the adapter span carries OpenRouter's token usage and USD cost, and is the only span that does;
  - the exporter sends the v4 ingestion header.
- **`docs/plans/evals/05_EVAL_DESIGN.md`:** already updated during planning (review R8): the ledger note in §3.6, the P1 live check and the P3 files in §4. No implementer change.
- **`AGENTS.md`:** no change. Its adapter paragraph stays true.

## 5. Steps

1. **Branch.** From an up-to-date `ADK_master`, create `feat/eval-p1-usage-cost`.
2. **Baseline.** Run the full suite in a disposable copy (`AGENTS.md` "Tests and syntax checks") and record the pass count.
3. **Write the tests in §4.3 first.** Before the change, `test_usage_and_cost_recorded`, `test_usage_without_cost`, `test_model_name_attribute` and the four tests added from the review must fail. The other four are guards and pass already.
4. **Make the changes in §4.1–4.2.** The new tests pass, and nothing else changes.
5. **Checks.**
   - Run `python -m compileall -q main.py sdaa tests scripts`.
   - Run the full suite in a fresh disposable copy. The count is the baseline plus the new tests.
6. **Live check** (§6). This spends under $0.05: get the operator's go-ahead first.
7. **Documentation** (§4.4).
8. **Record the work.**
   - Add an `archive/PROGRESS.md` entry for eval phase P1.
   - Run the logbook script:

     ```bash
     bash .agents/skills/dev-logbook/scripts/log.sh "Record OpenRouter usage and cost in traces" "Eval phase P1: the OpenRouter adapter span now carries token usage, USD cost and a Langfuse-mapped model name, recorded once per call; the Langfuse exporter sends the v4 ingestion header."
     ```
9. **Commit and open a PR** against `ADK_master`. The body includes:
   - the test counts;
   - the live-check table;
   - whether 403/400 export errors appeared.

   The plan documents (`06`–`08`) are already on `ADK_master`; don't add them to the PR. Don't merge.

## 6. Live check

**Purpose:** prove that cost reaches Langfuse once per call, and that it matches what OpenRouter actually billed.

**Where:** a disposable copy of the repo, made with the `tar` command in `AGENTS.md`, with `.env` copied in afterwards (`cp "$repo_root/.env" "$test_root/"`). Run every command below from inside the copy. The copy stays local; never commit or share `.env`. The run disables LangSmith with `LANGSMITH_API_KEY=` (decision 3 in `05` §6).

**Steps:**
1. **Note the start time in UTC**, and read the OpenRouter key's total usage in USD (`data.usage` of `GET /api/v1/key`). This command reads the key from `.env`, adds up comma-separated keys, and prints only the number; the review could not run it, so check its output looks sane:

   ```bash
   "$repo_root/.venv/bin/python" - <<'EOF'
   import json, urllib.request
   from dotenv import dotenv_values
   total = 0.0
   for key in dotenv_values(".env")["OPENROUTER_API_KEY"].split(","):
       req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                    headers={"Authorization": f"Bearer {key.strip()}"})
       total += json.load(urllib.request.urlopen(req))["data"]["usage"]
   print(f"{total:.10f}")
   EOF
   ```

   Make sure nothing else uses these keys during the check.
2. **Run a full audit:** `LANGSMITH_API_KEY= "$repo_root/.venv/bin/python" main.py -m openrouter --headless --no-rich`. Expect exit 0 and four outputs labelled `generated`.
3. **Read the key's usage again.** OpenRouter documents neither how fast this figure updates nor its precision. Repeat every 30 seconds until two readings agree, for at most 5 minutes. The difference from step 1 is what the run cost.
4. **List the generations** about 2 minutes after the run. With the header they should already be visible.

   ```bash
   langfuse --env .env api observations list --type GENERATION --fields core,basic,usage,model --from-start-time <start> --limit 200
   ```

   Run `langfuse api observations list --help` first for the exact field names in API v2.
5. **Delete the disposable copy.** It holds `.env`.

**Pass when:**

| Check | Expected |
|---|---|
| `OpenRouterModel.generate_content` observations | Each has model `deepseek/deepseek-v4.1-flash-1017`, input tokens above 0 and cost above 0 |
| `call_llm` observations | `usageDetails` is `{}` and `totalCost` is `null` on each |
| Sum of Langfuse cost for the run | Equal to the OpenRouter usage difference within $0.000001 per call. If not, record both figures. The row still passes when the difference is smaller than the cheapest single call in the run, because a missed or doubled call would move the sum by at least that much. Otherwise it fails. |
| Number of `OpenRouterModel.generate_content` observations | Every `call_llm` has exactly one `OpenRouterModel.generate_content` child. The remaining adapter observations equal the number of entries in the new `ToC.json` (4). No observation ID appears twice. |
| Run log | Record any `403` or `400` export lines verbatim, with the logger name, so the failing exporter can be told apart (F12) |

**If export fails** (403, or nothing arrives): stop the live check and report it as blocked, with the log lines. The unit tests still prove the attributes are set. The export failure belongs to the Langfuse export-errors task.

**Side effect:** a run that exits 0 on the committed config also completes the open "re-verify committed config" task. Report it.

## 7. Decisions

The operator approved every recommendation below on 2026-11-11. Where a decision departs from `05_EVAL_DESIGN.md`, this plan wins for P1.


1. **The ledger moves from P1 to P3.** `05` puts an in-process ledger in P1. Nothing reads it until the P3 run manifest exists, and the live check uses OpenRouter's own usage figure as ground truth instead. **Decision:** defer it to P3.
2. **Full audit instead of `--toc-only` for the live check.** `05` specifies `--toc-only`, but Map Maker calls have no `call_llm` parent (F6). That run would never test the duplicate-span case that D1 exists for. A full audit on the 4-file corpus costs under $0.05. It also closes the config re-verify task. **Decision:** run the full audit.
3. **Replace `model_name` with `llm.model_name`.** Nothing in the repo reads `model_name`. A LangSmith dashboard might, but LangSmith is off for eval runs. **Decision:** replace it.
4. **Langfuse-specific attributes or `gen_ai.usage.*`.**
   - `gen_ai.usage.*` would also give LangSmith the usage.
   - Setting both kinds on one span risks double reading.
   - **Decision:** Langfuse-specific attributes only, since Langfuse is the source of truth for cost.
5. **Keep the duplicate generation for now.** Every agent call still appears twice in Langfuse, as `call_llm` (no cost) and `OpenRouterModel.generate_content` (with cost). Cost is right, but generation counts stay doubled. Removing the duplicate means moving prompt linking and the OpenAI-format messages onto `call_llm`. **Decision:** a separate follow-up task, not P1.
6. **Streaming stays unmetered.** Headless never streams; interactive chat can. **Decision:** accept, with the `ponytail:` comment.
7. **Order with the vendor-docs removal.** The removal merged as `8e7eff1` (PR #48). The live check runs on 4 files. **Decision:** no ordering constraint remains.

## 8. Acceptance criteria

- [ ] The new tests in §4.3 pass; the full suite passes in a disposable copy at the baseline count plus the new tests.
- [ ] The adapter span sets `llm.model_name`, `langfuse.observation.usage_details` and `langfuse.observation.cost_details`, and nothing sets `LlmResponse.usage_metadata`.
- [ ] The exporter sends `x-langfuse-ingestion-version: 4`.
- [ ] The live check passes every row in §6 (the cost row by its stated rule), or is reported as blocked with export-error evidence.
- [ ] Documentation updated (§4.4); `archive/PROGRESS.md` entry and logbook entry added.
- [ ] PR open against `ADK_master`, not merged.
