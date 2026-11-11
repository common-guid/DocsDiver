# Review: Eval Phase P1 Plan (`06_P1_USAGE_COST_PLAN.md`)

Reviewed 2026-11-11 · Repo at `8e7eff1` (`ADK_master`) · Libraries at `requirements.lock` versions (repo `.venv` matches the lock) · Reviewer had no access to the conversation that produced the plan.

## 1. Verdict

**Approve with changes.**

- The design is sound. I applied the plan's diff to a scratch copy and ran it against the pinned libraries: usage and cost land on exactly one span per model call, and `call_llm` stays usage-free.
- All eleven facts hold. One is incomplete: a second exporter to Langfuse exists (R1).
- No blockers and no majors. Nine minor changes: tests that pass with broken code, a live check with an undecidable row, and stale text.

## 2. Fact check

| # | Status | Evidence |
|---|---|---|
| F1 | Confirmed | `openrouter_model.py:131-138` sets only `openinference.span.kind` and `model_name`. Langfuse mapping table, row `model`: "`langfuse.observation.model.name` · `gen_ai.request.model` · `gen_ai.response.model` · `llm.model_name` · `model`" (<https://langfuse.com/integrations/native/opentelemetry.md>). Existing data: 128 of 128 `OpenRouterModel.generate_content` generations have an empty model (§5.6). |
| F2 | Confirmed | `openrouter_model.py:339-396`. No read of `response.usage` anywhere in the file. |
| F3 | Confirmed, one nuance | OpenRouter Usage Accounting: "Full usage details are always included automatically in every response on both APIs", and `usage: { include: true }` is "deprecated and [has] no effect". The Chat Completions example shows every field the plan lists. Nuance: that page says "Cost in credits", not USD. USD comes from the FAQ ("a credit system where the base currency is US dollars") and the key endpoint schema ("credit usage (in USD)"). |
| F4 | Confirmed | §5.4, check 1: `CompletionUsage` keeps `cost` as a float; extras are `['cost', 'cost_details']`. |
| F5 | Confirmed | Source: `google_adk/__init__.py:106-138`; model name at `_wrappers.py:499-500`; usage only under `if obj.usage_metadata:` at `_wrappers.py:649-650`. Probe (§5.2): `call_llm` has `llm.model_name` and no usage attribute; the adapter span's parent is `call_llm`. |
| F6 | Confirmed | `map_maker.py:108`. Probe: a direct call gives a span with no parent in its own trace. Existing data: Map Maker generations sit in single-generation traces. |
| F7 | Confirmed | Mapping table, row `usage`: "`langfuse.observation.usage_details`: `JSON string` · `gen_ai.usage.*` · `llm.token_count.*`". |
| F8 | Confirmed | Mapping table, row `cost`: "`langfuse.observation.cost_details`: `JSON string` · `gen_ai.usage.cost` (set as `total` key)". Token & Cost Tracking: "ingested costs take priority over inferred ones" and "Langfuse no longer estimates token counts from inputs and outputs. If neither usage nor cost is submitted, no cost is calculated." |
| F9 | Confirmed, incomplete | Compatibility page: Cloud is "v4-only" from 2026-11-16; OpenTelemetry is "Full" on v3 and v4; without the header "data can be delayed by up to 15 minutes" (the OpenTelemetry page says "up to 10 minutes"). `instrumentation.py:134-137` sends only `Authorization`. **Incomplete:** that is not the only exporter. See R1. |
| F10 | Confirmed | `openrouter_model.py:314-316, 332-338`. No `RunConfig` or `streaming_mode` anywhere in `sdaa/` or `main.py`, so ADK passes `stream=False`. Map Maker calls without `stream`. |
| F11 | Confirmed | `test_langfuse_linking_verification.py:93-99` builds a `MagicMock` response. `test_instrumentation.py:28-32` checks the headers. Both pass with the plan's diff (§5.3). |

## 3. Findings

### R1. A second exporter already sends `call_llm` to Langfuse, with the v4 header

- **Severity:** minor
- **Section:** §2 F9, §3 D5, §6 "Run log" row
- **Problem:** The plan reasons about one exporter. There are two. `PromptManager` creates a Langfuse SDK client with tracing on (`prompt_manager.py:33`, `Langfuse()`). The SDK finds the global `TracerProvider` that `setup_instrumentation()` installed and adds its own `LangfuseSpanProcessor` to it (`langfuse/_client/resource_manager.py:245-262, 648-660`). From the first prompt fetch on:
  - `call_llm` is exported twice with the same span ID: once by the repo's exporter (no header today), once by the SDK (header `4`).
  - `OpenRouterModel.generate_content` is exported only by the repo's exporter. The SDK's default filter drops it (`langfuse/_client/span_filter.py:104-108`).
- **Effect on P1:** D1 and D5 stay correct. The span that carries usage travels only through the repo's exporter, so D5 is needed and usage is sent once. But a `403` or `400` log line can now come from either exporter, and the follow-up that removes the duplicate span needs this fact.
- **Evidence:** §5.5. Processors after `Langfuse()`: `['BatchSpanProcessor', 'LangfuseSpanProcessor']`. Two POSTs reached a local server: `(None, ['call_llm', 'OpenRouterModel.generate_content'])` and `('4', ['call_llm'])`.
- **Recommended change:**
  1. Add a fact row: "F12. The Langfuse SDK client created for prompts (`prompt_manager.py:33`) adds a second span processor to the same `TracerProvider`. It exports `call_llm` (already with the v4 header) but not the adapter span or Map Maker spans. Those go only through `instrumentation.py:134-137`."
  2. In D5, add: "The adapter span and Map Maker spans reach Langfuse only through this exporter (F12), so the header is required here."
  3. In the §6 "Run log" row, replace the text with: "Record any `403` or `400` export lines verbatim, with the logger name, so the failing exporter can be told apart (F12)."

### R2. Four broken implementations pass the planned tests

- **Severity:** minor
- **Section:** §4.3
- **Problem:** The seven tests do not pin D4, the JSON-string format, a cost of 0, or decision 4.
- **Evidence:** §5.3. Each variant below passed all seven tests plus the linking test.

  | Variant | What breaks in production |
  |---|---|
  | Helper without `try/except` | A span error fails a model call (D4) |
  | `if cost:` instead of the type check | A cost of 0 is dropped; Langfuse may then infer a non-zero cost |
  | Helper also sets `gen_ai.usage.input_tokens` | The double read that decision 4 rules out |
  | Call moved to just before the `yield` | Usage is lost when tool-call arguments fail to parse |

  A fifth variant, a dict instead of a JSON string, fails only if the test parses the value. The plan's table (`usage_details == {...}`) does not say it must. The pinned OpenTelemetry SDK stores a dict attribute without complaint (§5.4, check 3), while Langfuse documents a JSON string.
- **Recommended change:** Add these rows to the §4.3 table. All were run against the plan's diff and each kills its variant (§5.3).

  | Test | Response | Expected |
  |---|---|---|
  | `test_usage_recording_failure_does_not_break_call` | usage 100/20/120; `span.set_attribute` raises for keys starting `langfuse.observation.usage` | The response is still yielded; the warning is logged |
  | `test_zero_cost_is_recorded` | usage with `cost: 0` | `cost_details` == `{"total": 0}` |
  | `test_usage_recorded_before_response_parsing_fails` | usage plus a tool call whose `arguments` is not JSON | `JSONDecodeError` propagates; `usage_details` was set |

  And change the first row's Expected to: "Both values are `str`. `json.loads` gives `{"input": 100, "output": 20, "total": 120}` and `{"total": 1.6e-05}`. No attribute key starts with `gen_ai.usage` or `llm.token_count`."

### R3. Step 3 says the new tests fail first; four of seven pass

- **Severity:** minor
- **Section:** §5 step 3
- **Problem:** "Confirm the new ones fail" is wrong for `test_no_usage`, `test_non_numeric_usage_is_ignored`, `test_usage_metadata_stays_unset` and `test_provider_error_still_propagates`. They guard existing behaviour.
- **Evidence:** §5.3: on the unchanged code, "3 failed, 4 passed". The tests recommended in R2 and R4 all fail on the unchanged code ("5 failed").
- **Recommended change:** Replace step 3 with: "Write the tests in §4.3 first. Before the change, `test_usage_and_cost_recorded`, `test_usage_without_cost`, `test_model_name_attribute` and the tests added from review R2 must fail. The other four are guards and pass already."

### R4. The call site skips usage when `choices` is empty

- **Severity:** minor
- **Section:** §4.1 item 3
- **Problem:** The plan calls `_record_usage` after `message = response.choices[0].message`. A response with `usage` but an empty `choices` raises `IndexError` first. The call was billed and nothing is recorded. The error still propagates either way.
- **Evidence:** §5.4, check 4. With the helper moved one line up, the full suite still passes (149 with the extra tests) and a `choices: []` test records usage.
- **Recommended change:** Replace item 3 with: "In the non-streaming branch, call `_record_usage(span, response)` as the first statement of the `else:` block (`:340`), before `message = response.choices[0].message`." Optionally add `test_usage_recorded_when_choices_is_empty`: `choices: []` with usage → `IndexError` propagates and `usage_details` was set.

### R5. The cost-match row can't be decided if OpenRouter's figure lags or rounds

- **Severity:** minor
- **Section:** §6 steps 1 and 3, the "Sum of Langfuse cost" row, §8
- **Problem:**
  - `data.usage` is the right field: "Total OpenRouter credit usage (in USD) for the API key". But OpenRouter documents neither how fast it updates nor its precision. The tolerance of $0.000001 per call assumes both.
  - §8 allows only "pass" or "blocked with export-error evidence". A small mismatch fits neither.
  - The `curl` line uses `$OPENROUTER_API_KEY`, which lives in `.env` and is not exported to the shell. It also prints the whole response.
- **Evidence:** OpenRouter API reference, `GET /key` schema (<https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key.md>); limits page, "`usage: number; // Number of credits used (all time)`". No passage on freshness or precision in either page or the FAQ. `.env` holds one key, so no summing is needed today.
- **Recommended change:**
  1. Replace the `curl` line in step 1 with a command that reads the key from `.env` and prints only the number (not run by me; the review may not call OpenRouter):

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
  2. Replace step 3 with: "Read the key's usage again. Repeat every 30 seconds until two readings agree, for at most 5 minutes. The difference from step 1 is what the run cost."
  3. Replace the row's Expected with: "Equal to the OpenRouter usage difference within $0.000001 per call. If not, record both figures. The row still passes when the difference is smaller than the cheapest single call in the run, because a missed or doubled call would move the sum by at least that much. Otherwise it fails."

### R6. The expected observation count is a guess; an exact check is available

- **Severity:** minor
- **Section:** §6, rows "Number of … observations" and "`call_llm` observations"
- **Problem:** "15–19 audit calls" was measured on the old 16-file corpus. The corpus is now 4 files and 1,489 bytes, so the number of tool turns may differ. The implementer has no way to know the true call count from that row.
- **Evidence:** `05` V1 (19, 18, 18, 15 on 2026-11-10); `git ls-files docs-for-testing` gives 4 files. Existing data pairs every `call_llm` with exactly one adapter child (19/19, 15/15, 18/18) and shows one single-generation trace per Map Maker file (§5.6). For a span with no usage the API returns `usageDetails: {}` and `totalCost: null`, not 0.
- **Recommended change:**
  - Replace the count row's Expected with: "Every `call_llm` has exactly one `OpenRouterModel.generate_content` child. The remaining adapter observations equal the number of entries in the new `ToC.json` (4). No observation ID appears twice."
  - Replace the `call_llm` row's Expected with: "`usageDetails` is `{}` and `totalCost` is `null` on each."

### R7. The header is not all of v4 readiness

- **Severity:** minor
- **Section:** §1 goal, §3 D6
- **Problem:** The header meets the stated goal (real-time arrival). Langfuse says it is not enough to be v4-ready, and names a case this repo has: trace attributes set on the root span only. `TaggingSpanProcessor` sets `langfuse.trace.tags` on root spans only (`instrumentation.py:36-41`). After the cutover, child observations can't be filtered by the `ADK-DocsDiver` tag. P1's live check does not filter by tag, so P1 is unaffected.
- **Evidence:** <https://langfuse.com/integrations/native/opentelemetry/migration-to-v4.md>: "the header alone does not make a legacy or incomplete span format v4-ready" and "Attributes that exist only on the root span are therefore unavailable when filtering or aggregating its child observations."
- **Recommended change:** Add to D6: "**Tags on every span.** `langfuse.trace.tags` is set on root spans only (`instrumentation.py:36-41`). Langfuse v4 needs it on each span to filter observations by tag. A separate task; session propagation is already in P3."

### R8. `05` still places the ledger in P1

- **Severity:** minor
- **Section:** §4.4, §7 decision 1
- **Problem:** Decision 1 moves the ledger to P3, and "this plan wins for P1". But the P3 implementer reads `05`. Its P3 row lists no adapter file, and its manifest table takes model, prompt and usage from "the ledger" as if it exists.
- **Evidence:** `05_EVAL_DESIGN.md` §3.6 (P1 bullet "append the call to an in-process ledger"; P3 table "The ledger: what each call actually used") and the §4 P3 row (files: `main.py`, `run_manifest.py`, `model_factory.py`, `instrumentation.py`).
- **Recommended change:** Add to §4.4: "**`docs/plans/evals/05_EVAL_DESIGN.md`:** in §3.6 and the §4 table, note that the ledger moved from P1 to P3, add `sdaa/src/utils/openrouter_model.py` to the P3 files, and change the P1 live check to a full audit checked against OpenRouter's key usage."

### R9. Stale and loose text

- **Severity:** minor
- **Section:** §4.4, §5 steps 6 and 9, §6, §7 decision 7
- **Problem and evidence:**
  - Decision 7 and the §6 count row treat the vendor-docs removal as pending. It merged as `8e7eff1` (PR #48). The corpus has 4 files.
  - The cost is "about one cent" in §5 step 6 and §7 decision 2, and "under $0.05" in §7 decision 7. The operator's go-ahead should name one bound.
  - §4.4 says the adapter span "is the only span that does" carry usage. That is true for OpenRouter only. `InstrumentedGemini` yields Gemini's own responses (`instrumented_gemini.py:110-111`), which carry `usage_metadata`, so `call_llm` gets `llm.token_count.*` under `-m gemini` (`_wrappers.py:649-650`). Read from source, not run.
  - §6 copies `.env` into the disposable copy and never says to delete the copy. Step 2 runs `python`, but the copy has no `.venv`.
  - Step 9 does not say whether the untracked `06`, `07` and `08` go into the PR.
- **Recommended change:**
  - Decision 7: "The removal merged as `8e7eff1`. The live check runs on 4 files."
  - §5 step 6: "This spends under $0.05".
  - §4.4, first bullet: "for OpenRouter calls, the adapter span carries OpenRouter's token usage and USD cost, and is the only span that does;".
  - §6 step 2: use `"$repo_root/.venv/bin/python" main.py …`. Add a last step: "Delete the disposable copy; it holds `.env`."
  - Step 9: state whether `docs/plans/evals/06`–`08` are committed with the PR.

## 4. Decisions in §7

| # | Decision | Result |
|---|---|---|
| 1 | Ledger moves to P3 | No concern for P1. `_record_usage` is a small module-level helper; P3 can extend the call site in a few lines. `05` needs the note in R8. |
| 2 | Full audit for the live check | No concern. It is the only run that exercises the `call_llm` parent (F6 confirmed). Use the exact count check in R6. |
| 3 | Replace `model_name` with `llm.model_name` | No concern. Nothing reads `model_name`: the only other use is the Gemini wrapper setting it (`instrumented_gemini.py:84`). `llm.model_name` does not clash with any attribute on the adapter span (§5.2). |
| 4 | Langfuse-specific attributes only | No concern. Langfuse: `langfuse.*` attributes "always take precedence". Flat `usage_details` is "stored unchanged". |
| 5 | Keep the duplicate generation | No concern. The follow-up should start from R1: `call_llm` already has two export paths. |
| 6 | Streaming stays unmetered | No concern. Nothing in the repo turns streaming on (F10). |
| 7 | Order with the vendor-docs removal | No defect. The text is stale (R9). |

## 5. What I verified and how

All scripts ran from a temporary directory outside the repo, against disposable copies made with the `tar` command in `AGENTS.md`. Nothing called OpenRouter. Nothing was written to Langfuse. The repo's `git status` is unchanged apart from this file.

### 5.1 Environment and baseline

```text
.venv: google-adk 2.14.0, openai 1.109.1, openinference-instrumentation-google-adk 1.1.2,
       langfuse 5.2.0, opentelemetry-sdk 1.45.2   (all equal to requirements.lock)
Full suite, disposable copy, unchanged code:  137 passed
```

### 5.2 Span probe (D1, D3, F5, F6)

A real `TracerProvider` with `InMemorySpanExporter`, `GoogleADKInstrumentor().instrument()`, an `LlmAgent` with one tool, and the repo's `OpenRouterModel` whose client returns `ChatCompletion.model_validate(...)` with usage 100/20/120, 40 cached, 5 reasoning, `cost: 0.000016`. Two agent calls (tool call, then text) and one direct call as Map Maker makes it. Condensed:

```python
exporter = InMemorySpanExporter(); provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter)); trace.set_tracer_provider(provider)
GoogleADKInstrumentor().instrument()
model = OpenRouterModel(model_name="test/requested-slug", api_key="dummy")
model.client.chat.completions.create = AsyncMock(side_effect=[tool_call_completion, text_completion])
agent = LlmAgent(name="probe_agent", model=model, instruction="Use the tool.", tools=[lookup])
# Runner(...).run_async(...), then model.generate_content_async(LlmRequest(...)) directly
# print name, parent, and every attribute whose key contains usage/token/cost/model/langfuse
```

Output with the plan's diff applied (one agent call and the direct call shown; the second agent call is identical):

```text
[call_llm] parent=agent_run [probe_agent] scope=openinference.instrumentation.google_adk
    gen_ai.operation.name = generate_content
    gen_ai.provider.name = test
    gen_ai.request.model = test/requested-slug
    llm.model_name = test/requested-slug
    openinference.span.kind = LLM
[OpenRouterModel.generate_content] parent=call_llm scope=sdaa.src.utils.openrouter_model
    langfuse.observation.cost_details = {"total": 1.6e-05}
    langfuse.observation.usage_details = {"input": 100, "output": 20, "total": 120}
    llm.model_name = test/requested-slug
    openinference.span.kind = LLM
[OpenRouterModel.generate_content] parent=None (own trace)
    langfuse.observation.cost_details = {"total": 1.6e-05}
    langfuse.observation.usage_details = {"input": 100, "output": 20, "total": 120}
    llm.model_name = test/requested-slug
    openinference.span.kind = LLM
```

- Eight spans in total: `invocation`, `agent_run`, two `call_llm`, three adapter spans, one `execute_tool`. No span from ADK's own tracer. `invocation`, `agent_run` and `execute_tool` carry no usage, token or cost attribute.
- ADK logs "Skipping missing token usage metadata for agent …" once per call. That is existing behaviour.

### 5.3 The plan's tests, and mutations

I wrote the seven tests of §4.3 as described (mock tracer, mock span, `ChatCompletion.model_validate`).

```text
Unchanged code:   3 failed, 4 passed   (failed: usage_and_cost_recorded, usage_without_cost, model_name_attribute)
Plan's diff:      7 passed
Full suite with the diff and the seven tests:  144 passed;  compileall OK
```

Mutations of the plan's diff, run against the seven tests plus `test_langfuse_linking_verification.py`:

```text
helper without try/except                 10 passed
call moved to just before the yield       10 passed
`if cost:` instead of the type check      10 passed
also sets gen_ai.usage.input_tokens       10 passed
```

With the R2 tests added and the R4 call site: 12 passed, full suite 149 passed. On the unchanged code the five added tests all fail. Re-run with the added tests, every mutation fails: the first, third and fourth fail one test each, and the "call moved" and dict-instead-of-string mutations fail two each.

### 5.4 Edge cases (D2, D4, D5, F4)

```text
1. CompletionUsage cost = 1.6e-05 | extras = ['cost', 'cost_details']
2. helper on a real SDK span
   cost 0 (int)     -> usage_details '{"input": 5, "output": 0, "total": 5}', cost_details '{"total": 0}'
   cost 0.0         -> cost_details '{"total": 0.0}'
   no cost          -> usage_details only
   cost as string   -> usage_details only
   usage null       -> nothing set
   cached+reasoning -> usage_details '{"input": 100, "output": 20, "total": 120}', cost_details '{"total": 0.5}'
3. a dict as attribute value on a real span: stored as {'input': 1}; no error, no warning
4. choices=[]: response.choices[0] raises IndexError before _record_usage runs;
   usage on the response was 9 tokens, cost 0.001
5. OTLPSpanExporter(headers={"Authorization": ..., "x-langfuse-ingestion-version": "4"}) -> local HTTP server saw
   {'authorization': 'Basic eDp5', 'x-langfuse-ingestion-version': '4', 'content-type': 'application/x-protobuf'}
6. LANGSMITH_API_KEY='' then load_dotenv(file with LANGSMITH_API_KEY=from-dotenv) -> ''
```

- **D2, from the docs.** Token & Cost Tracking: "`total` is the sum of the buckets, not a bucket itself", so sending it does not double count. Flat `langfuse.observation.usage_details` is "Stored unchanged; values must already be exclusive". The plan sends no cached or reasoning key, so `input` and `output` do not overlap with anything. Leaving those keys out is safe.
- **D5.** LangSmith builds its own exporter with its own headers (`langsmith/integrations/otel/processor.py:124-133`), so it is unaffected.
- **Provider errors.** The `except Exception … raise` block at `openrouter_model.py:398-400` is untouched, and `test_provider_error_still_propagates` passes.
- **Adapter invariants.** Tool-call IDs, reasoning round-trips and empty-string assistant content are untouched by the diff (23 changed lines across both files); the full suite passes.

### 5.5 Second exporter (R1)

Fake keys and a local HTTP server as `base_url`. Condensed:

```python
provider = TracerProvider(); trace.set_tracer_provider(provider)          # as setup_instrumentation()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=f"{base}/api/public/otel/v1/traces", headers={"Authorization": "Basic eDp5"})))
client = Langfuse(public_key="pk-lf-fake", secret_key="sk-lf-fake", base_url=base)  # as PromptManager
# emit call_llm (OpenInference scope) with a child OpenRouterModel.generate_content, then flush
```

```text
processors after setup_instrumentation(): ['BatchSpanProcessor']
processors after Langfuse():              ['BatchSpanProcessor', 'LangfuseSpanProcessor']
SDK reuses the global provider: True
each POST: (x-langfuse-ingestion-version, span names in body)
   (None, ['call_llm', 'OpenRouterModel.generate_content'])
   ('4', ['call_llm'])
```

### 5.6 Existing Langfuse data (read-only)

```bash
langfuse --env .env api observations list --type GENERATION --fields core,basic,usage,model --limit 200 --json
```

```text
200 rows, 200 unique IDs, start times 2026-11-10T01:54–02:27Z
OpenRouterModel.generate_content: 128 × GENERATION, model '', usageDetails {}, totalCost null
call_llm: 72 × GENERATION, usageDetails {}, totalCost null;
          model deepseek/deepseek-v4.1-flash-1017 × 28, x-ai/grok-4.1-fast × 2, '' × 42
Audit traces: 19/19, 15/15, 18/18, 18/18 (adapter spans / call_llm); every adapter span's parent is call_llm
Other traces: one adapter generation each, in runs of 16
```

- Langfuse classifies the adapter span as a generation today, from `openinference.span.kind: LLM` alone.
- `call_llm` with a model name and no usage has no cost. This matches the docs: "If neither usage nor cost is submitted, no cost is calculated."
- `langfuse api observations list --help` confirms the flags and field groups in §6 step 4 (`usage` returns `usageDetails`, `costDetails`, `totalCost`).

### 5.7 Documentation fetched 2026-11-11

- <https://langfuse.com/integrations/native/opentelemetry.md>
- <https://langfuse.com/integrations/native/opentelemetry/migration-to-v4.md>
- <https://langfuse.com/docs/observability/features/token-and-cost-tracking.md>
- <https://langfuse.com/docs/compatibility.md>
- <https://openrouter.ai/docs/cookbook/administration/usage-accounting.md>
- <https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key.md>
- <https://openrouter.ai/docs/api_reference/limits.md>
- <https://openrouter.ai/docs/faq.md>

### 5.8 Project rules

- The plan runs the suite in a disposable copy (steps 2 and 5), adds an `archive/PROGRESS.md` entry and runs the logbook script (step 8). This matches `AGENTS.md`.
- I did not run the logbook script or edit `archive/PROGRESS.md`. The review brief allows no repo change other than this file.

## 6. Not verified

- **How Langfuse ingests the new attributes.** I may not write to Langfuse. That it accepts the two JSON strings, derives `totalCost` from `cost_details.total` and keeps the ingested cost rests on its documentation. The live check is the first real test.
- **OpenRouter's `data.usage`:** how soon it updates and to what precision (R5). I may not call OpenRouter with a key.
- **A live response's `usage`.** That `deepseek/deepseek-v4.1-flash-1017` returns `cost` on a Chat Completions response through `us.openrouter.ai` rests on OpenRouter's documentation.
- **BYOK.** If the account routes this model through its own provider key, `usage.cost` is "the total amount charged to your account" by OpenRouter and would understate the spend. I did not check the account.
- **Duplicate delivery of `call_llm`.** Existing data shows unique IDs and one `call_llm` per adapter child. I can't tell whether both exporters delivered in those runs, so I can't confirm from data that Langfuse merges the two copies in every view.
- **The header before the cutover.** The compatibility page marks OpenTelemetry "Full" on v3 and v4. I did not test what the project's current UI shows once the header is sent.
- **The cost of the live check.** No token counts exist yet to estimate from.
- **The Gemini path** in R9 was read from source, not run.
- **The `.env` reading command in R5** was not run.
