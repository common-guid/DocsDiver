from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from sdaa.src.utils.mock_model import MockModel
from sdaa.src.tools.file_ops import read_file
from sdaa.src.tools.reporting import generate_final_report
from sdaa.src.agents.workers import (
    create_permissions_agent,
    create_constraints_agent,
    create_boundaries_agent
)
from sdaa.src.core.model_factory import get_model_for_agent
from sdaa.src.utils.prompt_manager import prompt_manager
from sdaa.src.core.config_loader import config_loader


# SUPERVISOR_PROMPT is now managed via Langfuse (coordinator-agent)

def _build_synthesis_prompt(ctx: ReadonlyContext) -> str:
    permissions_report = (ctx.state.get("permissions_report") or "").strip()
    constraints_report = (ctx.state.get("constraints_report") or "").strip()
    boundaries_report = (ctx.state.get("boundaries_report") or "").strip()

    if not permissions_report:
        permissions_report = "MISSING: permissions_report"
    if not constraints_report:
        constraints_report = "MISSING: constraints_report"
    if not boundaries_report:
        boundaries_report = "MISSING: boundaries_report"

    return f"""
# Role
You are the **Principal Security Architect (PSA)**. You must synthesize a final audit report from three worker reports provided below. Do NOT call or delegate to any other agents. You MUST call `generate_final_report` with the full markdown content of your final report.

# Required Output Format: The Master Audit Report
Your final response must use this structure:

## 1. Executive Summary
*High-level assessment of the application's security posture based on the documentation coverage.*

## 2. Architecture & Trust Model
*Synthesize the findings from the Boundary Mapper into a coherent paragraph describing the stack.*

## 3. Key Findings & Risks
*   **Contradictions:** [List conflicts between different documentation sections]
*   **Missing Controls:** [List areas where documentation is silent on critical security]
*   **Critical Logic Flaws:** [Highlights from the Logic Auditor]

## 4. Master Test Plan (Consolidated)
*Merge the test tables from all three agents into one master table. Remove duplicates. Prioritize by Risk.*

| ID | Category | Test Scenario | Source Agent | Risk |
|:---|:---|:---|:---|:---|

# Source Reports
## Permissions Report
{permissions_report}

## Constraints Report
{constraints_report}

## Boundaries Report
{boundaries_report}

# Mandatory Reporting
1. Call `generate_final_report` with the full markdown you produce.
2. After calling the tool, return the **exact same markdown** content and nothing else.
"""

def create_coordinator_agent(provider: str = "openrouter", model=None):
    if model is None:
        model = get_model_for_agent("coordinator", provider)

    # Instantiate models for sub-agents based on the selected provider
    perm_model = get_model_for_agent("permissions_agent", provider)
    const_model = get_model_for_agent("constraints_agent", provider)
    bound_model = get_model_for_agent("boundaries_agent", provider)

    permissions_agent = create_permissions_agent(model=perm_model)
    constraints_agent = create_constraints_agent(model=const_model)
    boundaries_agent = create_boundaries_agent(model=bound_model)


    agent_config = config_loader.get("agents.coordinator", {})
    prompt_config = agent_config.get("prompt", {})
    
    prompt = prompt_manager.get_prompt(
        name=prompt_config.get("name", "coordinator-agent"),
        label=prompt_config.get("label", "production")
    )
    
    if not prompt:
        prompt = "Error: Could not fetch 'coordinator-agent' prompt from Langfuse."

    return LlmAgent(
        name="coordinator_psa",
        instruction=prompt,
        model=model,
        tools=[read_file, generate_final_report],
        sub_agents=[permissions_agent, constraints_agent, boundaries_agent]
    )

def create_coordinator_synthesizer(provider: str = "openrouter", model=None):
    if model is None:
        model = get_model_for_agent("coordinator", provider)

    return LlmAgent(
        name="coordinator_psa",
        instruction=_build_synthesis_prompt,
        model=model,
        tools=[generate_final_report]
    )
