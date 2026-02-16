# Notebook Context Management Implementation Plan
## Problem Statement
The current "Pull-based Accumulation" architecture suffers from context overflow when auditing large documentation sets. Files read via `read_file` accumulate in conversation history, leading to truncation, thrashing, or incomplete analysis when content exceeds model context limits (~128k-1M tokens).
## Current State
* **Agent Architecture**: Workers (`permissions`, `constraints`, `boundaries`) use `read_file` to access docs, with content accumulating in `InMemorySessionService` conversation history
* **Reporting Flow**: Agents call reporting tools (`report_permissions_matrix`, etc.) to write findings to `output/artifacts/`
* **Session Management**: Uses ADK's `InMemorySessionService` with `ctx.state` for inter-agent data sharing
* **Execution**: `SequentialAgent` orchestrates workers → coordinator synthesis in `build_prechat_audit_agent()`
* **Key Files**: `sdaa/src/tools/file_ops.py`, `sdaa/src/tools/reporting.py`, `sdaa/src/agents/workers.py`, `sdaa/src/agents/coordinator.py`, `main.py`
## Proposed Changes
### Phase 1: Notebook Tools (`sdaa/src/tools/notebook.py`)
Create persistent notebook tools for incremental finding storage:
**New Functions:**
* `append_to_notebook(category: str, content: str)` - Appends a finding to category-specific JSON file in `output/notebook/`
* `read_notebook(category: str = None)` - Reads all or category-specific findings
* `clear_notebook(category: str = None)` - Clears notebook (for fresh runs)
Notebook files stored as `output/notebook/{category}.json` with entries like:
```json
{"findings": [{"timestamp": "...", "content": "..."}]}
```
### Phase 2: Context Reset Mechanism
Implement context flushing capability:
**Option A - New Session per Batch (Simpler)**
Create a new session for each batch, preserving only:
* Core instructions (from prompt)
* Notebook reference (persist findings externally)
* Progress state (current batch index)
**Option B - ADK Callback (More Complex)**
Use ADK's `before_agent_callback` to clear `llm_request.contents` while preserving system instructions.
**Recommendation**: Start with Option A for reliability; iterate to Option B if needed.
### Phase 3: Batch Processing Driver
Update `build_prechat_audit_agent()` in `main.py` to implement batch processing:
1. Load `ToC.json` and partition into batches (configurable size, e.g., 5 files)
2. For each batch:
    * Inject batch file list into agent prompt
    * Run agent to process batch → calls `append_to_notebook`
    * Create fresh session (context reset)
3. After all batches: Run synthesis agent
**Config Addition** (`config.yaml`):
```yaml
system:
  batch_size: 5  # Files per batch
  notebook_dir: "notebook"
```
### Phase 4: Agent Prompt Updates
Update Langfuse prompts (or fallback prompts in `workers.py`) to instruct agents:
1. Read assigned batch files from ToC
2. Analyze and extract findings
3. Call `append_to_notebook("permissions", findings_markdown)` for each significant finding
4. Signal completion (no need to hold all content)
**Key Prompt Changes:**
* Replace "read all relevant files" with "process assigned batch"
* Add explicit `append_to_notebook` usage instructions
* Remove expectation of full-context analysis
### Phase 5: Synthesis Agent Update
Modify `create_coordinator_synthesizer()` to:
1. Read consolidated findings from notebook instead of session state
2. Use `read_notebook()` to get all findings
3. Generate final report from notebook content
**Changes to `coordinator.py`:**
* Add `read_notebook` tool to synthesizer
* Update `_build_synthesis_prompt` to inject notebook content instead of `ctx.state`
### Phase 6: CLI & Config Updates
**New CLI Flags:**
* `--batch-size N` - Override default batch size
* `--clear-notebook` - Clear notebook before run
**Config Additions:**
* `system.batch_size: 5`
* `system.notebook_dir: "notebook"`
### Phase 7: Testing
**Unit Tests:**
* `tests/test_notebook.py` - Test notebook CRUD operations
* `tests/test_batch_processing.py` - Test batch partitioning logic
**Integration Test:**
* Run against large doc set (>50 files) to verify context doesn't overflow
* Compare findings quality vs. current implementation
## Implementation Order
1. Phase 1 (Notebook Tools) - Foundation
2. Phase 3 (Batch Processing Driver) - Core mechanism
3. Phase 2 (Context Reset) - Integrate with batching
4. Phase 4 (Prompt Updates) - Enable agent usage
5. Phase 5 (Synthesis Update) - Complete pipeline
6. Phase 6 (CLI/Config) - User controls
7. Phase 7 (Testing) - Validation
## Risk Considerations
* **Finding Quality**: Batch isolation may miss cross-file correlations → Mitigate with detailed notebook entries
* **ADK Compatibility**: Context reset may conflict with ADK internals → Use new-session approach first
* **Prompt Complexity**: Agents need clear batch instructions → Test prompts incrementally
