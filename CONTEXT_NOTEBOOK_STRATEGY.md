# Context Management & Scalability Strategy

## 1. Current State Analysis

### How It Works Today
Currently, DocsDiver and the ADK agents (Permissions, Constraints, Boundaries) operate on a **"Pull-based Accumulation"** model:
1.  **Discovery:** The agent reads the `ToC.json` (or uses `list_files`) to discover available documentation.
2.  **Reading:** The agent uses the `read_file` tool to retrieve the content of specific files.
3.  **Context Accumulation:** The content of every file read is appended to the **Conversation History**.
    *   *Question:* "Is each document provided in an individual call, or grouped?"
    *   *Answer:* They are effectively grouped *in the history*. If the agent reads File A, then File B, then File C, the context window for the 4th turn contains [File A + File B + File C].

### The Problem: Context Overflow
This architecture suffers from a critical scalability limit: **The Context Window Cap.**
If the Permissions Agent is tasked with auditing a repository where the relevant documentation exceeds the model's context window (e.g., 128k or 1M tokens), the following failure modes occur:
*   **Truncation/Eviction:** The beginning of the conversation (instructions, `ToC`, or early file contents) is dropped to make room for new files. The agent "forgets" what it read 10 steps ago.
*   **Thrashing:** The agent may re-read files it forgot, entering a loop.
*   **Incomplete Analysis:** The agent cannot "hold" the entire system state in its head to make a comprehensive judgment (e.g., verifying a permission across 50 different files).

The Coordinator faces a similar issue: it receives the *full text* of the worker reports. If the workers produce massive reports, the Coordinator cannot synthesize them.

---

## 2. Proposed Strategies (Ranked by Benefit)

### Rank 1: Map-Reduce / Streaming Analysis (The "Notebook" Approach)
*Highest Impact for Thorough Audits*

**Concept:**
Instead of trying to fit everything into the context window ("InMemory"), the agent uses an **external persistent state** (a "Notebook" or "Scratchpad"). The agent processes files in batches, extracts findings to the notebook, and then **clears its short-term memory**.

**Workflow:**
1.  **Batching:** The agent (or a driver loop) selects a batch of files (e.g., 5 files).
2.  **Processing:** The agent reads the batch.
3.  **Extraction:** The agent uses a tool `add_finding(finding_data)` to write relevant info to a structured artifact on disk.
4.  **Flush:** The agent calls `clear_context()`, retaining only its core instructions and a summary of progress, but discarding the raw file text.
5.  **Repeat:** Process the next batch.
6.  **Synthesis:** Once all files are processed, the agent reads the *consolidated findings* (which are much smaller than the raw text) to generate the final report.

**Why it wins:**
*   **Infinite Scaling:** Can process 10,000 files with a fixed context window.
*   **Thoroughness:** Guarantees every file is "seen" by the LLM.
*   **Robustness:** Prevents "lost in the middle" phenomena common in long contexts.

**Implementation in DocsDiver:**
*   New Tool: `append_to_notebook(category, content)`
*   New Tool: `reset_context(keep_instructions=True)`
*   Update Agents: Instruct them to iterate through the ToC, process, record, and flush.
