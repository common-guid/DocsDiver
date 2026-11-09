# Configuration & Multi-Model Guide

## 1. Overview

The Security Documentation Analysis Agent (SDAA) features a flexible, multi-layered configuration system. System settings, model choices, and prompt metadata are specified in `sdaa/config/config.yaml`, environment secrets in `.env`, and operational modes via CLI flags.

---

## 2. Environment Variables (`.env`)

Secrets and observability endpoints are configured via environment variables. Create a `.env` file in the project root based on `.env.example`:

```ini
# --- Provider API Keys ---
GEMINI_API_KEY=AIzaSy...              # Required when using provider: gemini
OPENROUTER_API_KEY=sk-or-v1-...        # Required when using provider: openrouter

# --- System & Logging ---
LOG_LEVEL=INFO                         # Logging level (DEBUG | INFO | WARNING | ERROR)

# --- LangSmith Observability ---
LANGSMITH_TRACING=true                 # Enables LangSmith tracing (true | false)
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY=ls__...              # LangSmith API key
LANGSMITH_PROJECT="doc-sec-audit"      # Target LangSmith project name

# --- Langfuse Observability & Prompt Management ---
LANGFUSE_PUBLIC_KEY=pk-lf-...          # Langfuse public API key
LANGFUSE_SECRET_KEY=sk-lf-...          # Langfuse secret API key
LANGFUSE_HOST=http://localhost:3000   # Base URL for Langfuse instance
# LANGFUSE_OTEL_TRACES_ENDPOINT=http://localhost:3000/api/public/otel/v1/traces # Optional OTEL override
```

---

## 3. Configuration File (`sdaa/config/config.yaml`)

The main YAML file controls system paths, provider defaults, per-agent model selections, and prompt bindings.

### 3.1 `system` Section

Controls directory locations, file naming, and batch sizes.

| Key | Type | Default Value | Description & Valid Values |
| :--- | :--- | :--- | :--- |
| `system.docs_root` | String | `"docs-for-testing"` | Relative or absolute path to the directory containing documentation Markdown files to audit. Example: `"./docs"`. |
| `system.output_dir` | String | `"output"` | Base output directory where generated artifacts and reports are written. Example: `"./artifacts"`. |
| `system.reports_dir` | String | `"reports"` | Subdirectory inside `output_dir` for master audit reports (`output/reports/`). |
| `system.artifacts_dir` | String | `"artifacts"` | Subdirectory inside `output_dir` for individual worker report files (`output/artifacts/`). |
| `system.toc_filename` | String | `"ToC.json"` | Filename for the generated Table of Contents map. |
| `system.batch_size` | Integer | `10` | Number of documentation files processed per batch during Map Maker execution. |
| `system.notebook_dir` | String | `""` | Optional path for exported analysis notebooks. |

---

### 3.2 `providers` Section

Defines provider-level default model names and API endpoints.

```yaml
providers:
  gemini:
    model_name: "gemini-2.5-pro"
  openrouter:
    base_url: "https://openrouter.ai/api/v1"
    model_name: "google/gemini-2.5-pro"
```

| Key | Description | Example Values |
| :--- | :--- | :--- |
| `providers.gemini.model_name` | Default fallback model name for Gemini provider. | `"gemini-2.5-pro"`, `"gemini-2.0-flash"` |
| `providers.openrouter.base_url` | Base URL for OpenRouter API requests. | `"https://openrouter.ai/api/v1"` |
| `providers.openrouter.model_name` | Default fallback model for OpenRouter provider. | `"google/gemini-2.5-pro"`, `"anthropic/claude-3.5-sonnet"` |

---

### 3.3 `agents` Section (Per-Agent Model & Prompt Selection)

SDAA allows assigning different models and prompt versions to each agent independently, based on the selected provider (`gemini` or `openrouter`).

```yaml
agents:
  map_maker:
    openrouter: "google/gemma-3-27b-it"
    gemini: "gemini-2.0-flash-001"
  coordinator:
    openrouter: "x-ai/grok-4.1-fast"
    gemini: "gemini-2.5-pro"
    prompt:
      name: "coordinator-agent"
      label: "production"
  permissions_agent:
    openrouter: "x-ai/grok-4.1-fast"
    gemini: "gemini-2.5-flash"
    prompt:
      name: "permissions-agent"
      label: "production"
  constraints_agent:
    openrouter: "x-ai/grok-4.1-fast"
    gemini: "gemini-2.5-flash"
    prompt:
      name: "negative-constraints-agent"
      label: "production"
  boundaries_agent:
    openrouter: "x-ai/grok-4.1-fast"
    gemini: "gemini-2.5-flash"
    prompt:
      name: "security-boundaries-agent"
      label: "production"
```

#### Agent Configuration Reference

*   **`map_maker`**: Pre-processing agent. High speed and low cost are recommended.
    *   *Gemini Value*: `"gemini-2.0-flash-001"`
    *   *OpenRouter Value*: `"google/gemma-3-27b-it"` or `"meta-llama/llama-3.3-70b-instruct"`
*   **`coordinator`**: Supervisor synthesizer and interactive chat agent. High reasoning model recommended.
    *   *Gemini Value*: `"gemini-2.5-pro"`
    *   *OpenRouter Value*: `"x-ai/grok-4.1-fast"` or `"anthropic/claude-3.5-sonnet"`
    *   *Prompt Settings*: `name: "coordinator-agent"`, `label: "production"`
*   **`permissions_agent`**: Access control & RBAC specialist worker.
    *   *Gemini Value*: `"gemini-2.5-flash"`
    *   *OpenRouter Value*: `"x-ai/grok-4.1-fast"`
    *   *Prompt Settings*: `name: "permissions-agent"`, `label: "production"`
*   **`constraints_agent`**: Negative security constraints specialist worker.
    *   *Gemini Value*: `"gemini-2.5-flash"`
    *   *OpenRouter Value*: `"x-ai/grok-4.1-fast"`
    *   *Prompt Settings*: `name: "negative-constraints-agent"`, `label: "production"`
*   **`boundaries_agent`**: Security boundary & trust zone specialist worker.
    *   *Gemini Value*: `"gemini-2.5-flash"`
    *   *OpenRouter Value*: `"x-ai/grok-4.1-fast"`
    *   *Prompt Settings*: `name: "security-boundaries-agent"`, `label: "production"`

---

## 4. Command-Line Interface (CLI) Flags

CLI arguments override or bypass default execution phases at runtime:

```bash
python main.py [FLAGS]
```

| Flag | Long Option | Values | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `-m` | `--model` | `gemini` \| `openrouter` \| `mock` | `openrouter` | Selects which provider block in `config.yaml` to use for all agents. |
| | `--skip-map-maker` | Flag (boolean) | `False` | Skips Map Maker execution and expects `ToC.json` to already exist in `output_dir`. |
| | `--toc-only` | Flag (boolean) | `False` | Generates `ToC.json` and exits immediately before starting agents. |
| | `--coordinator-only` | Flag (boolean) | `False` | Runs only the Coordinator using pre-existing worker artifacts, bypassing worker LLM execution. |
| | `--no-rich` | Flag (boolean) | `False` | Disables Rich terminal formatting for plain text log output. |
| | `--headless` | Flag (boolean) | `False` | Runs Map Maker and the pre-chat audit non-interactively. Exit `0` only with a valid ToC and four valid outputs; `1` on failure; `2` on contradictory flags. |
| | `--refresh-toc` | Flag (boolean) | `False` | Rebuilds the ToC and then the whole audit; previous files are kept as `.prev`. Incompatible with `--skip-map-maker` and `--coordinator-only`. |
| | `--refresh-audit` | Flag (boolean) | `False` | Reruns all workers and synthesis, reusing a valid ToC; previous files are kept as `.prev`. Incompatible with `--coordinator-only` and `--toc-only`. |

---

## 5. Setup Recipes

### Recipe A: Full Gemini Provider Suite
To run all agents using Google Gemini models:
1. Ensure `GEMINI_API_KEY` is set in `.env`.
2. Execute:
   ```bash
   python main.py -m gemini
   ```

### Recipe B: High-Performance OpenRouter Setup (Grok + Gemma)
To run Map Maker on Gemma and analysis workers on Grok via OpenRouter:
1. Ensure `OPENROUTER_API_KEY` is set in `.env`.
2. Execute:
   ```bash
   python main.py -m openrouter
   ```

### Recipe C: Fast Offline / Unit Testing Mode
To execute the pipeline instantly without making real API calls:
```bash
python main.py -m mock
```
