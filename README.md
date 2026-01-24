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
