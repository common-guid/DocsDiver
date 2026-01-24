# SDAA: Security Documentation Analysis Agent

**DocsDiver** (SDAA) is an automated security architect that "dives" into your application documentation to uncover security risks, logical contradictions, and missing controls. 

Built with the **Google Agent Development Kit (ADK)**, it orchestrates a team of specialized AI agents to generate a comprehensive **Security Architecture Review** and a **Master Test Plan** directly from your markdown documentation.

---

## 🚀 Features

*   **Automated Knowledge Mapping:** Scans documentation directories to build a semantic Table of Contents (`ToC.json`).
*   **Multi-Agent Architecture:**
    *   **Coordinator (PSA):** Acts as the Principal Security Architect, synthesizing results.
    *   **Permissions Agent:** Maps "Who can do what" (RBAC, ACLs).
    *   **Constraints Agent:** Identifies "What cannot happen" (Invariants, Business Logic).
    *   **Boundaries Agent:** Maps "Where data flows" (Trust Zones, APIs, Ingress/Egress).
*   **Cross-Context Analysis:** Detects contradictions between different documentation sections (e.g., a constraint says "X is immutable," but an API doc shows a `PUT /X` endpoint).
*   **Master Test Plan Generation:** Auto-generates prioritized security test cases (AuthZ, Logic, Network) based on findings.

---

## 🏗 Architecture

### Repository Structure

*   `main.py`: The entry point for the CLI application. Initializes the MapMaker and the Agent Coordinator.
*   `sdaa/src/agents/`: Contains the logic for the AI agents.
    *   `coordinator.py`: Defines the Principal Security Architect (PSA) agent.
    *   `workers.py`: Defines the specialized sub-agents (Permissions, Constraints, Boundaries).
*   `sdaa/src/core/`: Core system logic.
    *   `map_maker.py`: Scans documentation to generate the semantic Table of Contents (`ToC.json`).
*   `sdaa/src/tools/`: Tool definitions used by the agents.
    *   `file_ops.py`: File system operations (`read_file`, `list_files`) for accessing documentation.
    *   `reporting.py`: Functions to log findings and generate the final report (`generate_final_report`).
*   `docs-for-testing/`: Default directory containing the markdown documentation to be analyzed.

### Agent System & Tools

The system operates on a **Coordinator-Worker** model:

1.  **Coordinator (PSA):**
    *   **Role:** Orchestrates the audit, delegates tasks, and synthesizes the final report.
    *   **Tools:** `read_file`, `generate_final_report`.
    *   **Function:** Decides whether to perform a full audit or answer specific user queries.

2.  **Worker Agents:**
    *   **Permissions Agent:** Analyzes RBAC and ACLs.
        *   *Tools:* `read_file`, `list_files`, `report_permissions_matrix`.
    *   **Constraints Agent:** Identifies business logic and negative constraints.
        *   *Tools:* `read_file`, `list_files`, `report_invariance_findings`.
    *   **Boundaries Agent:** Maps data flow and trust boundaries.
        *   *Tools:* `read_file`, `list_files`, `report_boundary_analysis`.

### Data Flow

1.  **Ingestion:** On startup, `MapMaker` scans `system.docs_root` and generates `ToC.json`, creating a "mental map" of the available documentation.
2.  **Interaction:** The user provides a command via the CLI (e.g., "Audit the application").
3.  **Delegation:** The Coordinator consults the `ToC.json` and instructs the relevant Worker Agents to analyze specific files using `read_file`.
4.  **Analysis:** Workers parse the content, extract security insights, and report back to the Coordinator.
5.  **Synthesis:** The Coordinator aggregates these findings, cross-references them for contradictions, and generates the **Master Audit Report**.
6.  **Output:** The final report is saved to `Security_Threat_Model.md` via `generate_final_report`.

---

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/DocsDiver.git
    cd DocsDiver
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration:**
    *   Review `sdaa/config/config.yaml` to configure your documentation root path and model providers.
    *   Ensure your markdown documentation is placed in the directory specified by `system.docs_root` (default: `./docs-for-testing`).

---

## 🛠 Usage

### Basic Execution

To start the interactive CLI agent:

```bash
python main.py
```

### The Workflow

1.  **Initialization:** The system first runs the **Map Maker** to index your documentation and generate `ToC.json`.
2.  **Interactive Session:** You enter the CLI chat loop.
    *   **Full Audit:** Type "Audit the application" or "Analyze the docs" to trigger the full multi-agent sweep.
    *   **Specific Queries:** Ask questions like "How does the billing logic work?" or "List all public API endpoints."
3.  **Output:** The agent streams its thought process and final reports to the console.

### Configuration (`sdaa/config/config.yaml`)

```yaml
system:
  docs_root: "./docs-for-testing" # Directory containing your markdown docs

providers:
  gemini:
    model_name: "gemini-2.5-pro"  # Default model for complex reasoning
```

---

## 🔌 Extending Functionality and Capabilities

SDAA is designed to be modular. Here is how you can extend it:

### 1. Adding New Specialized Agents
To add a new domain expert (e.g., a "Cryptography Agent" or "Compliance Agent"):
1.  Define the agent prompt in `sdaa/src/agents/workers.py`.
2.  Create a factory function (e.g., `create_crypto_agent`).
3.  Register the new agent in the `create_coordinator_agent` function in `sdaa/src/agents/coordinator.py`.
4.  Update the `SUPERVISOR_PROMPT` in `coordinator.py` so the Principal Architect knows when to deploy this new expert.

### 2. Custom Tools
Tools are defined in `sdaa/src/tools/`. You can add tools for:
*   **Jira Integration:** `create_jira_ticket(summary, severity)` to auto-file bugs.
*   **Static Analysis:** Integration with `semgrep` or `sonar` to correlate docs with code.
*   **Live Probing:** `curl` or `requests` tools to verify if an endpoint actually exists (use with caution).

### 3. Support for New Document Formats
Currently, `sdaa/src/core/map_maker.py` and `file_ops.py` support text/markdown.
*   **PDF/Docx:** Integrate libraries like `pypdf` or `unstructured` to parse binary formats into text before feeding them to the agents.
*   **Confluence/Wiki:** Add an API scraper to fetch live docs instead of reading local files.

---

## 🗺 Roadmap

The following improvements are planned to evolve SDAA from a prototype to a production-grade tool:

### 🔴 Immediate Priority (Alpha)
- [ ] **Real Model Integration:** Replace `MockModel` with actual Google Gemini API calls via `google-adk`.
- [ ] **Streaming Responses:** Improve the CLI UX to show agent thoughts in real-time.
- [ ] **Output Persistence:** Save the "Master Audit Report" to a timestamped Markdown file (e.g., `reports/audit_2024-01-23.md`).

### 🟡 Medium Term (Beta)
- [ ] **Vector Database Memory:** Instead of linear file reading, implement RAG (Retrieval-Augmented Generation) using a vector store (Chroma/Pinecone) for handling massive documentation sets.
- [ ] **Graph Visualization:** Generate a visual graph (Mermaid.js or Graphviz) showing the Trust Boundaries and Data Flows discovered by the `boundaries_agent`.
- [ ] **CI/CD Integration:** A GitHub Action that runs SDAA on every PR to `docs/` and comments on potential security contradictions.

### 🟢 Long Term (v1.0)
- [ ] **Compliance Mapping:** New agents specifically for SOC2, HIPAA, and ISO 27001 compliance mapping.
- [ ] **Code-to-Doc Correlation:** Ability to read the actual source code and flag where implementation diverges from documentation ("Drift Detection").
- [ ] **Jira/Linear Sync:** Automatically export the "Master Test Plan" rows as tickets in your project management tool.

---

## 📄 License
[MIT License](LICENSE)
