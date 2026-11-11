# Observability & Prompt Management Guide

## 1. Executive Summary

This guide details the **Observability & Telemetry Infrastructure** and **Externalized Prompt Management** implemented within the Security Documentation Analysis Agent (SDAA). SDAA uses unified **OpenTelemetry (OTEL)** tracing supporting both **Langfuse** and **LangSmith** concurrently, alongside dynamic prompt versioning via Langfuse.

---

## 2. OpenTelemetry Tracing Infrastructure

### Architecture Diagram

```mermaid
graph TD
    ADK[Google ADK Runner / Agents] --> OTEL[OpenInference ADK Instrumentor]
    OTEL --> Provider[Global TracerProvider]
    Provider --> Exporter1[Langfuse OTLPSpanExporter]
    Provider --> Exporter2[LangSmith Exporter]
    Exporter1 -->|/api/public/otel/v1/traces| LF[(Langfuse Dashboard)]
    Exporter2 --> LS[(LangSmith Dashboard)]
```

### 2.1 Unified Instrumentation (`sdaa/src/core/instrumentation.py`)
Both Langfuse and LangSmith telemetry exporters attach to a single `TracerProvider` during application startup via `setup_instrumentation()`:

1. **Auto-Instrumentation**: Uses `openinference-instrumentation-google-adk` to automatically trace ADK `Runner`, `LlmAgent`, tool invocations, and model calls.
2. **Langfuse OTLP Endpoint**:
   - Defaults to `${LANGFUSE_HOST}/api/public/otel/v1/traces`.
   - Supports overriding via `LANGFUSE_OTEL_TRACES_ENDPOINT`.
   - Performs Basic Auth using `${LANGFUSE_PUBLIC_KEY}:${LANGFUSE_SECRET_KEY}`.
3. **Health Check Guard**:
   - Before attaching the `OTLPSpanExporter`, `setup_instrumentation()` sends an HTTP GET request to `${LANGFUSE_HOST}/api/public/health`.
   - If the backend is unreachable or returns an HTTP error, Langfuse tracing is gracefully disabled, preventing network timeouts or noisy stack traces during normal CLI execution.
   - The exporter sends the `x-langfuse-ingestion-version: 4` header, which Langfuse Cloud requires after its v4 cutover.
4. **OpenRouter Usage and Cost**:
   - For OpenRouter calls, the `OpenRouterModel.generate_content` span carries OpenRouter's token usage (`langfuse.observation.usage_details`) and USD cost (`langfuse.observation.cost_details`), and is the only span that does.

---

## 3. Dynamic Prompt Management with Langfuse

System prompts are externalized to **Langfuse Prompt Management**, enabling real-time prompt updates and version control without redeploying code.

### 3.1 Prompt Fetching (`sdaa/src/utils/prompt_manager.py`)
The `PromptManager` singleton handles retrieval of prompt definitions:

```python
from sdaa.src.utils.prompt_manager import prompt_manager

# Fetch prompt object by slug name and release label
prompt_obj = prompt_manager.get_prompt_object(
    name="permissions-agent",
    label="production"
)

# Compile text output
prompt_text = prompt_obj.compile()
```

### 3.2 Prompts Registry Reference

| Agent | Langfuse Prompt Name | Default Label | Fallback Behavior |
| :--- | :--- | :--- | :--- |
| **Coordinator Supervisor** | `coordinator-agent` | `production` | Returns error message if fetch fails. |
| **Coordinator Synthesizer** | `report-synthesizer` | `production` | Compiles with `permissions_report`, `constraints_report`, `boundaries_report`. |
| **Permissions Agent** | `permissions-agent` | `production` | Analyzes roles and access matrices. |
| **Constraints Agent** | `negative-constraints-agent` | `production` | Analyzes negative invariants and logic rules. |
| **Boundaries Agent** | `security-boundaries-agent` | `production` | Analyzes perimeter boundaries and trust zones. |

---

### 3.3 Prompt Linking & Telemetry Metadata
To attribute LLM generations directly to specific prompt versions in Langfuse traces:
1. `PromptManager.get_prompt_object()` returns the raw Langfuse `TextPromptClient` object.
2. Models (`InstrumentedGemini` and `OpenRouterModel`) accept this object via `.set_langfuse_prompt(prompt_obj)`.
3. During content generation, metadata (prompt ID, version, name) is attached to the active OpenTelemetry span.

---

### 3.4 ADK Template Engine Sanitization

> [!IMPORTANT]
> Google ADK automatically attempts to substitute curly brace sequences `{variable}` as context template parameters. If a prompt fetched from Langfuse contains raw JSON examples, code snippets, or identifiers like `{user_id}`, ADK throws `KeyError: Context variable not found: user_id`.

To prevent crashes while allowing prompts to contain illustrative code samples, SDAA applies a regex sanitization pass to all fetched prompts before passing them to `LlmAgent`:

```python
# Translates single-line identifier braces: {user_id} -> (user_id)
prompt = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", prompt)
```

---

## 4. Logging & SDK Warning Suppression

When models execute tool calls during streaming, the `google-genai` SDK emits noisy log warnings regarding non-text response parts (`.text` accessed on function call responses).

In `main.py`, `suppress_genai_non_text_warning()` attaches a custom `logging.Filter` to `google_genai.types`:

```python
class _SuppressNonTextWarning(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "non-text parts in the response" not in record.getMessage()

logging.getLogger("google_genai.types").addFilter(_SuppressNonTextWarning())
```

---

## 5. Connectivity Validation & Troubleshooting

Diagnostic scripts in `scripts/` allow validating telemetry connections independently:

### 1. Validate Gemini & OpenRouter APIs
```bash
python scripts/validate_connections.py
```
Checks API key validity and network reachability for LLM providers.

### 2. Validate Langfuse Connectivity & OTEL Tracing
```bash
python scripts/validate_langfuse_conn.py
```
Pings the Langfuse health check endpoint (`/api/public/health`) and sends a test OTEL span to verify delivery.

### 3. Validate LangSmith Tracing
```bash
python scripts/test_langsmith_tracing.py
```
Emits a test trace to LangSmith to confirm project and API key configuration.
