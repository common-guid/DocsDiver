from google.adk.agents import LlmAgent
import re
import logging
from google.adk.agents.readonly_context import ReadonlyContext
from sdaa.src.utils.mock_model import MockModel

# Configure logging
logger = logging.getLogger(__name__)

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
    
    prompt_obj = prompt_manager.get_prompt_object(
        name=prompt_config.get("name", "coordinator-agent"),
        label=prompt_config.get("label", "production")
    )
    
    prompt = ""
    if prompt_obj:
        try:
            prompt = prompt_obj.compile()
            if hasattr(model, "set_langfuse_prompt"):
                model.set_langfuse_prompt(prompt_obj)
        except Exception:
            pass

    if not prompt:
        prompt = "Error: Could not fetch 'coordinator-agent' prompt from Langfuse."

    # Sanitize identifiers in braces in the fetched prompt
    prompt = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", prompt)

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

    def _build_synthesis_prompt(ctx: ReadonlyContext) -> str:
        permissions_report = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", (ctx.state.get("permissions_report") or "").strip())
        constraints_report = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", (ctx.state.get("constraints_report") or "").strip())
        boundaries_report = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", (ctx.state.get("boundaries_report") or "").strip())

        if not permissions_report:
            permissions_report = "MISSING: permissions_report"
        if not constraints_report:
            constraints_report = "MISSING: constraints_report"
        if not boundaries_report:
            boundaries_report = "MISSING: boundaries_report"

        prompt_obj = prompt_manager.get_prompt_object(
            name="report-synthesizer",
            label="production"
        )

        prompt = ""
        if prompt_obj:
            try:
                prompt = prompt_obj.compile(
                    permissions_report=permissions_report,
                    constraints_report=constraints_report,
                    boundaries_report=boundaries_report
                )
                if hasattr(model, "set_langfuse_prompt"):
                    model.set_langfuse_prompt(prompt_obj)
            except Exception as e:
                logger.error(f"Error compiling synthesis prompt: {e}")
                pass

        if not prompt:
            logger.error("Failed to fetch 'report-synthesizer' prompt from Langfuse.")
            return "Error: Could not fetch 'report-synthesizer' prompt from Langfuse."

        return prompt

    return LlmAgent(
        name="coordinator_psa",
        instruction=_build_synthesis_prompt,
        model=model,
        tools=[generate_final_report]
    )
