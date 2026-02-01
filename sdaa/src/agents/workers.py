from google.adk.agents import LlmAgent
from sdaa.src.utils.mock_model import MockModel
from sdaa.src.tools.file_ops import read_file, list_files
from sdaa.src.tools.reporting import (
    report_permissions_matrix,
    report_invariance_findings,
    report_boundary_analysis
)
from sdaa.src.utils.prompt_manager import prompt_manager
from sdaa.src.core.config_loader import config_loader

# --- PROMPTS ---


# --- PROMPTS ---
# Prompts are now managed via Langfuse and fetched dynamically.

def create_permissions_agent(model=None):
    if model is None:
        model = MockModel(model="mock-model")


    agent_config = config_loader.get("agents.permissions_agent", {})
    prompt_config = agent_config.get("prompt", {})
    
    prompt = prompt_manager.get_prompt(
        name=prompt_config.get("name", "permissions-agent"),
        label=prompt_config.get("label", "production")
    )
    
    if not prompt:
        # Fallback if fetch fails or no key
        prompt = "Error: Could not fetch 'permissions-agent' prompt from Langfuse."

    return LlmAgent(
        name="permissions_agent",
        instruction=prompt,
        model=model,
        tools=[read_file, list_files, report_permissions_matrix],
        output_key="permissions_report"
    )

def create_constraints_agent(model=None):
    if model is None:
        model = MockModel(model="mock-model")


    agent_config = config_loader.get("agents.constraints_agent", {})
    prompt_config = agent_config.get("prompt", {})

    prompt = prompt_manager.get_prompt(
        name=prompt_config.get("name", "negative-constraints-agent"),
        label=prompt_config.get("label", "production")
    )
    
    if not prompt:
        prompt = "Error: Could not fetch 'negative-constraints-agent' prompt from Langfuse."

    return LlmAgent(
        name="constraints_agent",
        instruction=prompt,
        model=model,
        tools=[read_file, list_files, report_invariance_findings],
        output_key="constraints_report"
    )

def create_boundaries_agent(model=None):
    if model is None:
        model = MockModel(model="mock-model")


    agent_config = config_loader.get("agents.boundaries_agent", {})
    prompt_config = agent_config.get("prompt", {})

    prompt = prompt_manager.get_prompt(
        name=prompt_config.get("name", "security-boundaries-agent"),
        label=prompt_config.get("label", "production")
    )
    
    if not prompt:
        prompt = "Error: Could not fetch 'security-boundaries-agent' prompt from Langfuse."

    return LlmAgent(
        name="boundaries_agent",
        instruction=prompt,
        model=model,
        tools=[read_file, list_files, report_boundary_analysis],
        output_key="boundaries_report"
    )
