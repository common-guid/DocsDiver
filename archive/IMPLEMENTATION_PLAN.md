# Implementation Plan: Security Documentation Analysis Agent (SDAA)

## 1. Project Overview
This document outlines the implementation steps for the **Security Documentation Analysis Agent (SDAA)**. The system uses the **ADK Hierarchical Coordinator Pattern** to perform deep security reviews of technical documentation.

### Key Constraints & Requirements
*   **Architecture:** ADK `LlmAgent` with a Coordinator-Worker topology.
*   **Initialization:** A "Map Maker" phase runs **within the main application** before the agent runtime starts to generate a `ToC.json`.
*   **Configuration:** Support for multiple model providers (Gemini, OpenRouter) via `config.yaml`.
*   **Dependencies:** Managed via `requirements.txt`.

---

## 2. Project Structure
The development team shall use the following directory structure:

```text
sdaa/
├── config/
│   └── config.yaml          # Model & System configuration
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config_loader.py # Logic to load config.yaml
│   │   └── map_maker.py     # Pre-processing logic (Phase 1)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── file_ops.py      # read_file, list_files
│   │   └── reporting.py     # Pydantic models & reporting tools
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── workers.py       # Permissions, Constraints, Boundaries agents
│   │   └── coordinator.py   # PSA Coordinator agent
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_tools.py
│   └── test_map_maker.py
├── .env.example             # Template for API keys
├── main.py                  # Application Entry Point
├── requirements.txt         # Project Dependencies
└── README.md
```

---

## 3. Phase 1: Environment & Configuration Setup

### 3.1 Dependencies (`requirements.txt`)
Create a `requirements.txt` file with the following core libraries:
*   `google-adk` (Core framework)
*   `pydantic` (Data validation for tools)
*   `pyyaml` (Config parsing)
*   `python-dotenv` (Environment variable management)
*   `openai` (If using OpenRouter via OpenAI-compatible client, or relevant ADK integration)

### 3.2 Configuration System (`config/config.yaml`)
Define the model selection and system parameters. This allows easy switching between Gemini and OpenRouter.

```yaml
system:
  toc_filename: "ToC.json"
  docs_root: "./docs"  # Target directory to scan

# Model Provider Configurations
providers:
  gemini:
    model_name: "gemini-2.5-pro"
  openrouter:
    base_url: "https://openrouter.ai/api/v1"
    model_name: "anthropic/claude-3-opus" # Example

# Agent-Specific Model Selection
agents:
  map_maker:
    provider: "gemini"
    model: "gemini-2-flash" # Lightweight model for summaries
  coordinator:
    provider: "gemini"
    model: "gemini-2.5-pro"
  permissions_agent:
    provider: "gemini" # or "openrouter"
    model: "gemini-2.5-pro"
  constraints_agent:
    provider: "gemini"
    model: "gemini-2.5-pro"
  boundaries_agent:
    provider: "gemini"
    model: "gemini-2.5-pro"
```

### 3.3 Config Loader (`src/core/config_loader.py`)
Implement a singleton or utility function to load `config.yaml` and resolve environment variables (e.g., `${GEMINI_API_KEY}`, `${OPENROUTER_API_KEY}`).

---

## 4. Phase 2: Core Logic Implementation

### 4.1 The "Map Maker" (`src/core/map_maker.py`)
This module implements the synchronous pre-processing routine.

**Functionality:**
1.  **Scan:** Recursively walk `config.system.docs_root` to find `.md` files.
2.  **Summarize:** For each file, instantiate a lightweight ADK agent (or direct API client) configured via `agents.map_maker` in `config.yaml`.
    *   *Prompt:* "Read the following content and provide a one-sentence architectural summary."
3.  **Output:** Generate a JSON object:
    ```json
    {
      "files": [
        { "path": "docs/auth/login.md", "summary": "Handles user authentication flows." },
        ...
      ]
    }
    ```
4.  **Save:** Write this object to `ToC.json` in the project root.

### 4.2 Tooling Layer

**`src/tools/file_ops.py`**
*   `read_file(file_path)`: Implement safe reading. Ensure `file_path` is within `docs_root` to prevent path traversal.
*   `list_files(directory_path)`: Return list of files.

**`src/tools/reporting.py`**
*   Define Pydantic models: `AuthMatrixEntry`, `PermissionIssue`, `Vulnerability`, `TestCase`.
*   Implement reporting functions:
    *   `report_permissions_matrix(...)`
    *   `report_invariance_findings(...)`
    *   `report_boundary_analysis(...)`
    *   `generate_final_report(...)`: Used by the Coordinator to save the final `Security_Threat_Model.md`.

---

## 5. Phase 3: Agent Implementation

### 5.1 Workers (`src/agents/workers.py`)
Implement the three worker agents (`permissions_agent`, `constraints_agent`, `boundaries_agent`) using `LlmAgent`.

*   **Initialization:** Use `config_loader` to fetch the specific model and provider for each agent.
*   **Tools:** Bind the specific reporting tool and `read_file` to each agent.
*   **Prompts:** Paste the System Prompts defined in the PRD (Section 3).

### 5.2 Coordinator (`src/agents/coordinator.py`)
Implement `coordinator_psa`.

*   **Sub-agents:** Import workers from `src/agents/workers.py` and register them in the `sub_agents` list.
*   **Tools:** Bind `read_file` (to read ToC) and `generate_final_report`.
*   **Prompt:** Use the "Principal Security Architect" instructions.

---

## 6. Phase 4: Main Application & Orchestration (`main.py`)

The entry point must strictly follow this sequence:

1.  **Load Configuration:** Initialize config and environment.
2.  **Run Map Maker:**
    ```python
    print("Initializing Map Maker Phase...")
    from src.core.map_maker import generate_toc
    generate_toc() # This blocks until ToC.json is written
    print("Map generated.")
    ```
3.  **Initialize Agents:**
    ```python
    from src.agents.coordinator import coordinator_psa
    ```
4.  **Start Runtime:**
    *   Initialize the ADK runtime with `coordinator_psa`.
    *   Start the interactive session (CLI or loop).

---

## 7. Phase 5: Testing & Verification

### 7.1 Unit Tests (`tests/`)
*   **`test_tools.py`**: Verify `read_file` prevents path traversal. Verify Pydantic models correctly validate valid/invalid JSON.
*   **`test_map_maker.py`**: Mock the LLM call and verify `generate_toc` correctly scans a dummy directory and produces valid JSON.

### 7.2 Functional Verification
1.  **Environment:** Create a `docs/` folder with dummy markdown files.
2.  **Execution:** Run `python main.py`.
3.  **Check 1:** Verify `ToC.json` is created *before* the agent prompt appears.
4.  **Check 2:** Engage the agent: "Perform a full security audit."
5.  **Check 3:** Verify all agents activate in the logs.
6.  **Check 4:** Verify `Security_Threat_Model.md` is generated with structured sections.

---

## 8. Handover Checklist for Dev Team
- [ ] Environment variables set for `GEMINI_API_KEY` and/or `OPENROUTER_API_KEY`.
- [ ] `config.yaml` updated with preferred models.
- [ ] `docs/` directory populated with target documentation.
- [ ] Verify `ToC.json` is not stale (it should regenerate on every run).
