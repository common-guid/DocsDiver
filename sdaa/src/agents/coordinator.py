from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
import re
import os
import logging
from typing import AsyncGenerator
from sdaa.src.tools.file_ops import read_file
from sdaa.src.tools.reporting import generate_final_report
from sdaa.src.utils.prompt_manager import prompt_manager
from sdaa.src.core.config_loader import config_loader

logger = logging.getLogger(__name__)


def create_coordinator_agent(provider: str = "gemini", model_name: str = None):
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
        except Exception:
            pass

    if not prompt:
        prompt = "Error: Could not fetch 'coordinator-agent' prompt from Langfuse."

    # Sanitize identifiers in braces
    prompt = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", prompt)

    return {
        "prompt": prompt,
        "tools": [read_file, generate_final_report]
    }


class AgyCoordinatorSynthesizer:
    def __init__(self, prompt_generator, tools: list):
        self.prompt_generator = prompt_generator
        self.tools = tools

    async def run_async(self, model_name: str = None) -> AsyncGenerator[str, None]:
        system_instructions = self.prompt_generator()
        
        if model_name == "mock" or model_name == "mock-model":
            for t in self.tools:
                if t.__name__ == "generate_final_report":
                    t("Mock Final Threat Model Report")
            yield "\n[Mock] Synthesis complete.\n"
            return
            
        config = LocalAgentConfig(
            system_instructions=system_instructions,
            capabilities=CapabilitiesConfig(),
            tools=self.tools,
            model=model_name
        )
        async with Agent(config) as agent:
            response = await agent.chat("Generate the final Security Threat Model report using the worker findings.")
            async for token in response:
                yield token


def create_coordinator_synthesizer(provider: str = "gemini", model_name: str = None):
    def _build_synthesis_prompt() -> str:
        artifacts_dir = config_loader.get_artifacts_dir()
        
        def read_report(filename):
            path = os.path.join(artifacts_dir, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            return "MISSING: " + filename

        permissions_report = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", read_report("permissions_agent.md").strip())
        constraints_report = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", read_report("constraints_agent.md").strip())
        boundaries_report = re.sub(r"\{([a-zA-Z_]\w*)\}", r"(\1)", read_report("boundaries_agent.md").strip())

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
            except Exception as e:
                logger.error(f"Error compiling synthesis prompt: {e}")
                pass

        if not prompt:
            logger.error("Failed to fetch 'report-synthesizer' prompt from Langfuse.")
            return "Error: Could not fetch 'report-synthesizer' prompt from Langfuse."

        return prompt

    return AgyCoordinatorSynthesizer(
        prompt_generator=_build_synthesis_prompt,
        tools=[generate_final_report]
    )
