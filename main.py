import sys
import asyncio
import argparse
import os
import logging
from typing import AsyncGenerator
from sdaa.src.core.config_loader import config_loader
from sdaa.src.core.map_maker import generate_toc
from sdaa.src.agents.coordinator import (
    create_coordinator_agent,
    create_coordinator_synthesizer
)
from sdaa.src.agents.workers import (
    create_permissions_agent,
    create_constraints_agent,
    create_boundaries_agent
)
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
from sdaa.src.ui.rich_chat import RichUI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def suppress_genai_non_text_warning() -> None:
    """
    Suppress the google-genai warning emitted when .text is accessed on responses
    that include non-text parts (e.g., function_call). This keeps the CLI output
    clean while preserving other warnings.
    """
    lg = logging.getLogger("google_genai.types")
    for existing_filter in lg.filters:
        if getattr(existing_filter, "_suppress_non_text_warning", False):
            return

    class _SuppressNonTextWarning(logging.Filter):
        _suppress_non_text_warning = True

        def filter(self, record: logging.LogRecord) -> bool:
            message = record.getMessage()
            return "non-text parts in the response" not in message

    lg.addFilter(_SuppressNonTextWarning())

def _expected_prechat_output_paths() -> list[str]:
    artifacts_dir = config_loader.get_artifacts_dir()
    reports_dir = config_loader.get_reports_dir()
    return [
        os.path.join(artifacts_dir, "permissions_agent.md"),
        os.path.join(artifacts_dir, "constraints_agent.md"),
        os.path.join(artifacts_dir, "boundaries_agent.md"),
        os.path.join(reports_dir, "Security_Threat_Model.md"),
    ]

def get_missing_prechat_outputs() -> list[str]:
    expected_paths = _expected_prechat_output_paths()
    return [path for path in expected_paths if not os.path.exists(path)]

def get_agy_model_name(agent_name: str, provider: str) -> str:
    """Resolves the model name to be used with the local Antigravity binary."""
    if provider == "mock":
        return "mock"
    
    # We resolve the model name configured under the gemini provider in config.yaml,
    # as the local AGY binary operates on Gemini models using local Google credentials.
    model_name = config_loader.get(f"agents.{agent_name}.gemini")
    if not model_name:
        model_name = "gemini-2.5-pro"
    return model_name

async def run_prechat_audit(provider: str, coordinator_only: bool = False) -> AsyncGenerator[str, None]:
    artifacts_dir = config_loader.get_artifacts_dir()
    
    def get_worker_model(agent_name: str) -> str:
        return get_agy_model_name(agent_name, provider)

    # 1. Permissions Agent
    perm_path = os.path.join(artifacts_dir, "permissions_agent.md")
    if os.path.exists(perm_path):
        yield "Permissions Agent: Artifact already exists. Skipping.\n"
    elif not coordinator_only:
        yield "Running Permissions Agent...\n"
        perm_agent = create_permissions_agent()
        async for token in perm_agent.run_async(get_worker_model("permissions_agent")):
            yield token
            
    # 2. Constraints Agent
    const_path = os.path.join(artifacts_dir, "constraints_agent.md")
    if os.path.exists(const_path):
        yield "Constraints Agent: Artifact already exists. Skipping.\n"
    elif not coordinator_only:
        yield "Running Constraints Agent...\n"
        const_agent = create_constraints_agent()
        async for token in const_agent.run_async(get_worker_model("constraints_agent")):
            yield token
            
    # 3. Boundaries Agent
    bound_path = os.path.join(artifacts_dir, "boundaries_agent.md")
    if os.path.exists(bound_path):
        yield "Boundaries Agent: Artifact already exists. Skipping.\n"
    elif not coordinator_only:
        yield "Running Boundaries Agent...\n"
        bound_agent = create_boundaries_agent()
        async for token in bound_agent.run_async(get_worker_model("boundaries_agent")):
            yield token

    # 4. Coordinator Synthesizer (always runs to build final report)
    yield "Running Coordinator Synthesizer...\n"
    synth_model = get_worker_model("coordinator")
    coord_synth = create_coordinator_synthesizer()
    async for token in coord_synth.run_async(synth_model):
        yield token

async def main():
    parser = argparse.ArgumentParser(description="SDAA: Security Documentation Analysis Agent")
    parser.add_argument("-m", "--model", choices=["gemini", "openrouter", "mock"], default="gemini", help="Model provider to use")
    parser.add_argument("--skip-map-maker", action="store_true", help="Skip Map Maker and use an existing ToC.json if present")
    parser.add_argument("--toc-only", action="store_true", help="Run Map Maker only and exit before starting the coordinator")
    parser.add_argument("--coordinator-only", action="store_true", help="Run only the coordinator using existing artifacts, bypassing workers and Map Maker")
    parser.add_argument("--no-rich", action="store_true", help="Disable Rich terminal UI and use plain text output")
    args = parser.parse_args()

    ui = RichUI(no_rich=args.no_rich)
    suppress_genai_non_text_warning()

    ui.print_banner("SDAA: Security Documentation Analysis Agent")
    ui.print_status(f"Using provider: {args.model}")

    # 1. Map Maker
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = config_loader.get_output_dir()
    toc_path = os.path.join(output_dir, toc_filename)

    if args.skip_map_maker or args.coordinator_only:
        ui.print_status(f"\n[Phase 1] Skipping Map Maker due to CLI flag. Expecting existing ToC at {toc_path}.")
    elif os.path.exists(toc_path):
        ui.print_status(f"\n[Phase 1] Skipping Map Maker because existing ToC was found at {toc_path}.")
    else:
        ui.print_status("\n[Phase 1] Initializing Map Maker...")
        try:
            map_maker_model = get_agy_model_name("map_maker", args.model)
            await generate_toc(model_name=map_maker_model)
            ui.print_status(f"ToC generation complete. Wrote ToC to {toc_path}.")
        except Exception as e:
            ui.print_error(f"generating ToC: {e}")

    if args.toc_only:
        ui.print_status("[Phase 1] --toc-only specified; exiting after Map Maker.")
        return

    # Ensure output directories exist
    config_loader.get_reports_dir()
    config_loader.get_artifacts_dir()
    
    # 2. Pre-chat Audit
    missing_outputs = get_missing_prechat_outputs()
    if missing_outputs or args.coordinator_only:
        ui.print_status("\n[Phase 2.5] Running Pre-chat Audit...")
        try:
            await ui.stream_response(
                run_prechat_audit(provider=args.model, coordinator_only=args.coordinator_only),
                title="Pre-chat Audit"
            )
            ui.print_status("Pre-chat audit complete.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            ui.print_error(f"\n{e}")
    else:
        ui.print_status("\n[Phase 2.5] Skipping Pre-chat Audit (outputs present).")

    # 3. Initialize Interactive Coordinator
    ui.print_status("\n[Phase 3] Initializing Coordinator...")
    coord_info = create_coordinator_agent(provider=args.model)
    coord_prompt = coord_info["prompt"]
    coord_tools = coord_info["tools"]
    coord_model = get_agy_model_name("coordinator", args.model)

    config = LocalAgentConfig(
        system_instructions=coord_prompt,
        capabilities=CapabilitiesConfig(),
        tools=coord_tools,
        model=coord_model
    )

    ui.print_status("\n[Phase 3] Agent Ready. (Type 'exit' to quit)")

    async with Agent(config) as agent:
        while True:
            try:
                user_input = ui.ask_user("\nUser> ")
                if user_input.lower() in ('exit', 'quit'):
                    break

                response = await agent.chat(user_input)
                await ui.stream_response(
                    response,
                    title="Coordinator"
                )

            except KeyboardInterrupt:
                break
            except Exception as e:
                ui.print_error(f"\n{e}")
                break

if __name__ == "__main__":
    asyncio.run(main())
