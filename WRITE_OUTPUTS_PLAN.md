# Remediation Plan: Fix Artifact Generation in Pre-Chat Audit

## Problem Analysis
The artifacts (`ToC.json`, reports, and agent findings) are not being written to the `/output` directory when using the `openrouter` provider. This failure occurs because the `OpenRouterModel` wrapper incorrectly reconstructs the conversation history for the OpenAI-compatible API, specifically regarding **Tool Call IDs**.

### Root Cause: Tool Call ID Mismatch
The OpenRouter/OpenAI API requires strict matching between the `tool_call_id` in a `tool` (result) message and the `id` of the corresponding `tool_calls` entry in the preceding `assistant` message.

1.  **Generation Phase:** When the model generates a tool call, `OpenRouterModel.generate_content_async` intercepts the response and assigns a custom, ADK-compliant ID format: `functions.{function_name}:{index}`.
2.  **History Reconstruction Phase:** When the ADK Runner sends the conversation history back to the model for the next turn (e.g., after tool execution), `OpenRouterModel` attempts to reconstruct the messages.
    *   It checks the `FunctionCall` object for an `id`.
    *   If the ADK runner or types (specifically `google.genai`) does not persist the `id` field in the history object, `OpenRouterModel` falls back to generating a default ID: `call_{message_index}_{tool_index}`.
3.  **The Mismatch:** The reconstructed `assistant` message gets the ID `call_...`, but the `tool` message (containing the result) often retains the ID `functions...` (if preserved by the runner) or forces a lookup. This mismatch causes the OpenRouter/OpenAI API to reject the request with a 400 Bad Request error.
4.  **Consequence:** The agents fail to complete their tool execution cycles (or fail to report results), leading to no files being written. The system might swallow the error or the agent might fail silently, resulting in an "empty" success state.

## Proposed Changes

### 1. Fix Tool Call ID Generation in `OpenRouterModel`
Modify `sdaa/src/utils/openrouter_model.py` to ensure consistent ID generation during history reconstruction.

*   **Location:** `generate_content_async` method, inside the `llm_request.contents` loop.
*   **Logic:** When processing `FunctionCall` parts in the history:
    *   Maintain a `tool_call_index` counter for each message.
    *   If `fc.id` is missing (None/Empty), generate the ID using the **same format** used during generation: `f"functions.{fc.name}:{tool_call_index}"`.
    *   This ensures that the ID sent in the `assistant` message matches the format expected by the system and likely matches the `FunctionResponse` ID.

### 2. Clean Up Duplicate System Instruction Logic
The `generate_content_async` method currently contains a redundant code block that processes system instructions and then clears the `messages` list immediately after. This should be removed to clean up the code, although it is not the primary cause of the bug.

### 3. Verify `_convert_schema` Robustness
Ensure `_convert_schema` can handle edge cases where `schema.type` might not map cleanly to a string representation containing standard type names, ensuring it defaults correctly to "string" or "object" as appropriate.

## Verification Plan
1.  **Run the fix:** Execute `python main.py -m openrouter`.
2.  **Check Output:** Verify that the `/output` directory is populated with:
    *   `ToC.json` (from Map Maker)
    *   `artifacts/permissions_agent.md`
    *   `artifacts/constraints_agent.md`
    *   `artifacts/boundaries_agent.md`
    *   `reports/Security_Threat_Model.md`
3.  **Logs:** Ensure no "Error calling OpenRouter" messages appear in the CLI output.

## Code Changes Spec
(Do not implement yet, but here is the logic for the plan)

```python
# In sdaa/src/utils/openrouter_model.py

# Inside the history loop:
if hasattr(content, 'parts'):
    tool_call_index = 0 # Reset per message
    for part in content.parts:
        if hasattr(part, 'function_call') and part.function_call:
            fc = part.function_call
            # Use existing ID or generate deterministic ADK-style ID
            tc_id = getattr(fc, 'id', None)
            if not tc_id:
                tc_id = f"functions.{fc.name}:{tool_call_index}"
            
            tool_calls.append({
                "id": tc_id,
                # ...
            })
            tool_call_index += 1
```
