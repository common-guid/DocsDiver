from google.adk.agents import LlmAgent
import re
from sdaa.src.utils.mock_model import MockModel
from sdaa.src.tools.file_ops import read_file, list_files
from sdaa.src.tools.reporting import (
    report_permissions_matrix,
    report_invariance_findings,
    report_boundary_analysis
)
from sdaa.src.tools.context_ops import reset_context, append_to_notebook, read_notebook
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
    
    # Sanitize identifiers in braces to prevent ADK from treating them as variables
    prompt = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", prompt)

    notebook_instructions = (
        "\n\n# Context Management Strategy\n"
        "To handle large documentation sets, you must use the 'Notebook Strategy':\n"
        "1. Process files in batches (e.g., 5-10 files at a time).\n"
        "2. For each batch, read the files and analyze them.\n"
        "3. Record your findings immediately using `append_to_notebook(notebook_name='permissions_agent', content='...')`.\n"
        "4. After recording findings, call `reset_context(summary='...')` to clear your memory and prevent context overflow. Pass a summary of what you have done and what is left to do.\n"
        "5. Repeat until all relevant files are processed.\n"
        "6. Finally, use `read_notebook(notebook_name='permissions_agent')` to review all your findings and generate the final report using your reporting tool."
    )
    prompt += notebook_instructions

    return LlmAgent(
        name="permissions_agent",
        instruction=prompt,
        model=model,
        tools=[read_file, list_files, report_permissions_matrix, reset_context, append_to_notebook, read_notebook],
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

    # Sanitize identifiers in braces to prevent ADK from treating them as variables
    prompt = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", prompt)

    notebook_instructions = (
        "\n\n# Context Management Strategy\n"
        "To handle large documentation sets, you must use the 'Notebook Strategy':\n"
        "1. Process files in batches (e.g., 5-10 files at a time).\n"
        "2. For each batch, read the files and analyze them.\n"
        "3. Record your findings immediately using `append_to_notebook(notebook_name='constraints_agent', content='...')`.\n"
        "4. After recording findings, call `reset_context(summary='...')` to clear your memory and prevent context overflow. Pass a summary of what you have done and what is left to do.\n"
        "5. Repeat until all relevant files are processed.\n"
        "6. Finally, use `read_notebook(notebook_name='constraints_agent')` to review all your findings and generate the final report using your reporting tool."
    )
    prompt += notebook_instructions

    return LlmAgent(
        name="constraints_agent",
        instruction=prompt,
        model=model,
        tools=[read_file, list_files, report_invariance_findings, reset_context, append_to_notebook, read_notebook],
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

    # Escape braces to prevent ADK from treating them as variables
    prompt = prompt.replace("{", "{{").replace("}", "}}")

    notebook_instructions = (
        "\n\n# Context Management Strategy\n"
        "To handle large documentation sets, you must use the 'Notebook Strategy':\n"
        "1. Process files in batches (e.g., 5-10 files at a time).\n"
        "2. For each batch, read the files and analyze them.\n"
        "3. Record your findings immediately using `append_to_notebook(notebook_name='boundaries_agent', content='...')`.\n"
        "4. After recording findings, call `reset_context(summary='...')` to clear your memory and prevent context overflow. Pass a summary of what you have done and what is left to do.\n"
        "5. Repeat until all relevant files are processed.\n"
        "6. Finally, use `read_notebook(notebook_name='boundaries_agent')` to review all your findings and generate the final report using your reporting tool."
    )
    prompt += notebook_instructions

    return LlmAgent(
        name="boundaries_agent",
        instruction=prompt,
        model=model,
        tools=[read_file, list_files, report_boundary_analysis, reset_context, append_to_notebook, read_notebook],
        output_key="boundaries_report"
    )
