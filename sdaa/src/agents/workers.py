from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
import re
from typing import AsyncGenerator
from sdaa.src.tools.file_ops import read_file, list_files
from sdaa.src.tools.reporting import (
    report_permissions_matrix,
    report_invariance_findings,
    report_boundary_analysis
)
from sdaa.src.utils.prompt_manager import prompt_manager
from sdaa.src.core.config_loader import config_loader


class AgyWorker:
    def __init__(self, name: str, prompt: str, tools: list):
        self.name = name
        self.prompt = prompt
        self.tools = tools

    async def run_async(self, model_name: str = None) -> AsyncGenerator[str, None]:
        if model_name == "mock" or model_name == "mock-model":
            # Simulate execution by writing a mock file
            for t in self.tools:
                if t.__name__ == "report_permissions_matrix":
                    t(f"Mock permissions findings for {self.name}")
                elif t.__name__ == "report_invariance_findings":
                    t(f"Mock invariance findings for {self.name}")
                elif t.__name__ == "report_boundary_analysis":
                    t(f"Mock boundary analysis for {self.name}")
            yield f"\n[Mock] Analysis complete for {self.name}.\n"
            return

        config = LocalAgentConfig(
            system_instructions=self.prompt,
            capabilities=CapabilitiesConfig(),
            tools=self.tools,
            model=model_name
        )
        async with Agent(config) as agent:
            response = await agent.chat("Audit the application")
            async for token in response:
                yield token


def create_permissions_agent(model_name: str = None) -> AgyWorker:
    agent_config = config_loader.get("agents.permissions_agent", {})
    prompt_config = agent_config.get("prompt", {})
    
    prompt_obj = prompt_manager.get_prompt_object(
        name=prompt_config.get("name", "permissions-agent"),
        label=prompt_config.get("label", "production")
    )
    
    prompt = ""
    if prompt_obj:
        try:
            prompt = prompt_obj.compile()
        except Exception:
            pass

    if not prompt:
        prompt = "Error: Could not fetch 'permissions-agent' prompt from Langfuse."
    
    # Sanitize identifiers in braces
    prompt = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", prompt)

    return AgyWorker(
        name="permissions_agent",
        prompt=prompt,
        tools=[read_file, list_files, report_permissions_matrix]
    )

def create_constraints_agent(model_name: str = None) -> AgyWorker:
    agent_config = config_loader.get("agents.constraints_agent", {})
    prompt_config = agent_config.get("prompt", {})

    prompt_obj = prompt_manager.get_prompt_object(
        name=prompt_config.get("name", "negative-constraints-agent"),
        label=prompt_config.get("label", "production")
    )
    
    prompt = ""
    if prompt_obj:
        try:
            prompt = prompt_obj.compile()
        except Exception:
            pass

    if not prompt:
        prompt = "Error: Could not fetch 'negative-constraints-agent' prompt from Langfuse."

    prompt = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", prompt)

    return AgyWorker(
        name="constraints_agent",
        prompt=prompt,
        tools=[read_file, list_files, report_invariance_findings]
    )

def create_boundaries_agent(model_name: str = None) -> AgyWorker:
    agent_config = config_loader.get("agents.boundaries_agent", {})
    prompt_config = agent_config.get("prompt", {})

    prompt_obj = prompt_manager.get_prompt_object(
        name=prompt_config.get("name", "security-boundaries-agent"),
        label=prompt_config.get("label", "production")
    )
    
    prompt = ""
    if prompt_obj:
        try:
            prompt = prompt_obj.compile()
        except Exception:
            pass

    if not prompt:
        prompt = "Error: Could not fetch 'security-boundaries-agent' prompt from Langfuse."

    # Escape braces
    prompt = prompt.replace("{", "{{").replace("}", "}}")

    return AgyWorker(
        name="boundaries_agent",
        prompt=prompt,
        tools=[read_file, list_files, report_boundary_analysis]
    )

