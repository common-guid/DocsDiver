DocsDiver-Crew** is a hierarchical multi-agent system built on CrewAI that automates the security review of software documentation by identifying logic gaps, permission issues, and undefined boundaries. It utilizes a "Librarian" pre-processing script to index content, enabling a Supervisor agent to efficiently delegate analysis tasks to three specialized worker agents using custom context-aware file tools. The system ensures reliability through asynchronous execution and a robust Quality Control suite that uses "Canary Tokens" to deterministically verify the detection of security vulnerabilities.
### **1. Project Structure**

We will maintain a clean, modular directory structure to separate tooling, agents, and execution logic.

```text
doc-sec-audit/
├── src/
│   ├── agents/          # Agent configurations (Supervisor + 3 Workers)
│   ├── tools/           # Custom File I/O tools (Completed)
│   ├── utils/           # Helper scripts (ToC Generator)
│   └── main.py          # CLI Entry point & Orchestration
├── tests/               # Unit tests & "Bad Docs" integration test
├── .env                 # API Keys
└── requirements.txt     # Dependencies (crewai, pydantic, etc.)

```

---

### **2. Phase Breakdown**

#### **Phase 1: Core Tooling (Completed)**

* **Objective:** Enable agents to navigate and read the file system efficiently.
* **Status:** **Ready** (Code generated in previous step).
* **Components:**
* `ListFilesTool`: Recursively finds `.md` files.
* `ReadFileTool`: Ingests full file content.
* `SearchFilesTool`: Context-aware search (returns 3 lines before/after match) to satisfy QC requirements.



#### **Phase 2: Preprocessing ("The Librarian")**

* **Objective:** Generate a map of the documentation to prevent the Supervisor from blindly searching.
* **Input:** Raw directory of `.md` files.
* **Action:**
1. Script iterates through all files.
2. Sends content to a cheap/fast LLM (e.g., GPT-3.5/Haiku).
3. Extracts a 1-sentence summary and tags (e.g., `["auth", "payments"]`).


* **Output:** `ToC.json` (Table of Contents) stored in root.
* **Key Constraint:** This runs *outside* the Crew loop to save tokens and time.

#### **Phase 3: Crew Configuration (The Hierarchy)**

* **Objective:** Define the agents and the management structure.
* **Architecture:** Hierarchical Process (Supervisor delegates to Workers).
* **Agents:**
1. **Supervisor (Manager):** Orchestrates the audit.
2. **Negative Constraints Agent:** Looks for "what the system should NOT do" (e.g., "Users cannot delete logs").
3. **Permissions Agent:** Looks for RBAC gaps (e.g., "Admin vs. User").
4. **Boundaries Agent:** Looks for system limits (e.g., API rate limits, data retention).


* **Critical Implementation Detail (Context Injection):**
* We will **not** ask the Supervisor to "read the ToC file."
* Instead, we will read `ToC.json` in Python and **inject the string directly** into the Supervisor's task description: *"Here is the map of the documentation: [JSON DATA]. Assign tasks based on these tags..."*



#### **Phase 4: Execution & Orchestration**

* **Objective:** Tie it all together into a usable CLI.
* **File:** `src/main.py`.
* **Flow:**
1. **CLI Args:** User runs `python main.py --dir ./my_docs`.
2. **Trigger Phase 2:** Run `generate_toc()` automatically.
3. **Load Context:** Read the resulting `ToC.json`.
4. **Initialize Crew:** Pass the `file_tools` to the workers and the `ToC` context to the Supervisor.
5. **Kickoff:** Execute the Crew.


* **Output:** `FINAL_AUDIT_REPORT.md` (Strict Markdown structure).

#### **Phase 5: Quality Control (QC)**

* **Objective:** Verify the system actually catches bugs.
* **Strategy:** "Bad Docs" Integration Test.
* **Action:** Create a `./tests/fixtures/vulnerable_docs/` folder containing known bad security practices (e.g., hardcoded passwords, vague permission logic) and assert that the Crew's report flags them.
