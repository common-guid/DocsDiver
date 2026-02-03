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

---

### Rank 2: Hybrid RAG (Vector-Augmented File System)
*Highest Efficiency for Targeted Queries*

**Concept:**
Maintain the "Agent using File System" paradigm but give the agent a "Search Engine" for the codebase. Instead of guessing which files to read based on filenames, the agent queries a semantic index.

**Workflow:**
1.  **Indexing:** During the "Map Maker" phase, chunk and embed all documentation into a local vector store (e.g., ChromaDB, FAISS).
2.  **Tooling:** Provide a `semantic_search(query)` tool alongside `list_files` and `read_file`.
3.  **Execution:**
    *   Agent: "I need to find where 'UserAdmin' permissions are defined."
    *   Tool `semantic_search("UserAdmin permissions definition")` -> Returns snippets from `auth/roles.md` and `config/policies.yaml`.
    *   Agent reads only those specific files.

**Why it fits:**
*   **Speed:** Drastically reduces the number of `read_file` calls needed to find relevant info.
*   **Context Savings:** The agent doesn't need to load irrelevant sections of files.
*   **Hybrid:** The agent can still browse directory structures (`ls`) to understand the layout, using Search only when digging for specifics.

---

### Rank 3: Hierarchical / Sharded ToC
*Improved Navigation*

**Concept:**
Instead of loading one massive `ToC.json` (which itself might consume 20k tokens), split the map into a directory tree.

**Workflow:**
*   `ToC.json` only contains top-level folders and root files.
*   Agent sees `["/api/", "/guides/", "/reference/"]`.
*   Agent calls `list_files("/api/")` -> receives `ToC_api.json`.
*   Agent drills down recursively.

**Why it fits:**
*   **Mimics Humans:** Natural way to explore large file systems.
*   **Initial Load:** Keeps the system prompt lightweight.

---

### Rank 4: Summary Compression / Progressive Disclosure
*Optimization*

**Concept:**
The Map Maker produces two layers of data:
1.  **Meta-Map:** Just file paths and 3 keywords. (Very small).
2.  **Detailed Summaries:** Stored in a separate look-up file or database.

The agent only sees the Meta-Map initially. It calls `get_file_summary(path)` to see the one-paragraph summary before deciding to pay the cost of `read_file(path)`.

**Why it fits:**
*   Reduces "browsing" costs.

---

## 3. Scenario: The Permissions Agent vs. Massive Docs

**The Situation:**
The Permissions Agent is provided a `ToC` with 500 files. 200 of them contain relevant permission definitions.

**Current Behavior (Failure Mode):**
1.  Agent sees 500 files.
2.  Agent loops: `read_file(1)`, `read_file(2)`... `read_file(20)`.
3.  By file 20, the context is full.
4.  Agent crashes or forgets File 1.
5.  **Result:** Report covers only 10% of the system.

**Recommended Solution (Notebook Strategy):**
1.  **Phase 1 (Scan):** The Agent is instructed to *not* memorize.
2.  Agent Loop:
    *   Read 5 files.
    *   Extract permissions to `permissions_db.json` (via tool).
    *   **CLEAR CONTEXT.**
    *   Read next 5 files.
3.  **Phase 2 (Synthesize):**
    *   Agent reads `permissions_db.json` (which is clean and structured).
    *   Agent generates the final Matrix.

This approach transforms the problem from **O(N) memory** (impossible) to **O(1) memory + O(N) time** (feasible).
