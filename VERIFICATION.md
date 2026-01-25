# Verification Instructions

This document outlines how to verify that the Langfuse integration is active and working correctly, specifically addressing the Python 3.14 incompatibility issue.

## 1. Verify Application Startup and Initialization

Run the application with your preferred model (e.g., Gemini):

```bash
python main.py -m gemini
```

Check the console output for the following line:

```text
Langfuse observability initialized at <YOUR_LANGFUSE_HOST>
```

Example output:
```text
Langfuse observability initialized at http://localhost:3000
LangSmith observability initialized at https://api.smith.langchain.com
Observability instrumentation complete.
```

If you see this message, the Langfuse exporter has been successfully configured using the OpenTelemetry standard libraries, bypassing the problematic `langfuse` Python client import.

## 2. Generate Traces

Interact with the agent to generate some traces. For example:

1.  Wait for the agent to initialize (Phase 3).
2.  Type a message: `Hello, can you help me?`
3.  Wait for the response.
4.  Type `exit` to quit.

## 3. Validate in Langfuse Dashboard

1.  Open your Langfuse dashboard (e.g., `http://localhost:3000` or your cloud instance).
2.  Navigate to the **Traces** view.
3.  You should see new traces with the tag `ADK-DocsDiver`.
4.  Click on a trace to inspect it. Ensure it contains spans and metadata.

## Troubleshooting

If you do not see traces:

1.  **Check Environment Variables**: Ensure `.env` contains valid `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST`.
    ```bash
    grep LANGFUSE .env
    ```
2.  **Check Network**: Ensure your machine can reach the `LANGFUSE_HOST`.
3.  **Check Logs**: Look for any error messages starting with `Langfuse credentials not found` or OpenTelemetry errors in the console output.

## Technical Details of the Fix

The `langfuse` Python library has dependencies (like `pydantic` v1 compatibility layers) that may not yet be fully compatible with Python 3.14.

The fix involves refactoring `sdaa/src/core/instrumentation.py` to:
1.  **Remove the import dependency** on the `langfuse` library.
2.  **Directly use `opentelemetry` exporters** which are the core requirement for sending traces to Langfuse.
3.  **Hardcode necessary constants** (like trace tags) that were previously imported.

This ensures that the observability pipeline remains functional regardless of the `langfuse` client library's compatibility with your Python version.
