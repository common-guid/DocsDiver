import sys
import asyncio
import argparse
import os
import logging
from sdaa.src.core.instrumentation import setup_instrumentation
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
from sdaa.src.utils.mock_model import MockModel
from sdaa.src.utils.openrouter_model import OpenRouterModel
from sdaa.src.core.model_factory import get_model_for_agent
from google.adk.agents import SequentialAgent
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from sdaa.src.ui.rich_chat import RichUI
from sdaa.src.utils.artifact_loader_model import ArtifactLoaderModel

def suppress_genai_non_text_warning() -> None:
    """
    Suppress the google-genai warning emitted when .text is accessed on responses
    that include non-text parts (e.g., function_call). This keeps the CLI output
    clean while preserving other warnings.
    """
    logger = logging.getLogger("google_genai.types")
    for existing_filter in logger.filters:
        if getattr(existing_filter, "_suppress_non_text_warning", False):
            return

    class _SuppressNonTextWarning(logging.Filter):
        _suppress_non_text_warning = True

        def filter(self, record: logging.LogRecord) -> bool:
            message = record.getMessage()
            return "non-text parts in the response" not in message

    logger.addFilter(_SuppressNonTextWarning())

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

def build_prechat_audit_agent(provider: str, coordinator_only: bool = False) -> SequentialAgent:
    artifacts_dir = config_loader.get_artifacts_dir()
    
    # helper to decide model for a worker
    def get_worker_model(agent_name: str, artifact_name: str, tool_name: str, tool_arg: str):
        artifact_path = os.path.join(artifacts_dir, artifact_name)
        
        # If artifact exists, use it (Optimization Goal 1)
        if os.path.exists(artifact_path):
            print(f"DEBUG: Found existing artifact for {agent_name}, skipping execution.")
            with open(artifact_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ArtifactLoaderModel(content=content, tool_name=tool_name, tool_arg_name=tool_arg)
            
        # If coordinator only and artifact missing, skip with dummy (Goal 2)
        if coordinator_only:
            print(f"DEBUG: Coordinator-only mode: Skipping {agent_name} (artifact missing).")
            return ArtifactLoaderModel(
                content=f"SKIPPED: {agent_name} was skipped because --coordinator-only was specified and no artifact was found.",
                tool_name=tool_name, 
                tool_arg_name=tool_arg
            )
            
        # Otherwise use real model
        return get_model_for_agent(agent_name, provider)

    perm_model = get_worker_model(
        "permissions_agent", "permissions_agent.md", "report_permissions_matrix", "findings"
    )
    const_model = get_worker_model(
        "constraints_agent", "constraints_agent.md", "report_invariance_findings", "findings"
    )
    bound_model = get_worker_model(
        "boundaries_agent", "boundaries_agent.md", "report_boundary_analysis", "boundaries_markdown"
    )

    permissions_agent = create_permissions_agent(model=perm_model)
    constraints_agent = create_constraints_agent(model=const_model)
    boundaries_agent = create_boundaries_agent(model=bound_model)

    # create_coordinator_synthesizer now accepts provider
    coordinator_synth = create_coordinator_synthesizer(provider=provider)

    return SequentialAgent(
        name="prechat_audit",
        sub_agents=[
            permissions_agent,
            constraints_agent,
            boundaries_agent,
            coordinator_synth
        ]
    )

async def main():
    parser = argparse.ArgumentParser(description="SDAA: Security Documentation Analysis Agent")
    parser.add_argument("-m", "--model", choices=["gemini", "openrouter", "mock"], default="openrouter", help="Model provider to use")
    parser.add_argument("--skip-map-maker", action="store_true", help="Skip Map Maker and use an existing ToC.json if present")
    parser.add_argument("--toc-only", action="store_true", help="Run Map Maker only and exit before starting the coordinator")
    parser.add_argument("--coordinator-only", action="store_true", help="Run only the coordinator using existing artifacts, bypassing workers and Map Maker")
    parser.add_argument("--no-rich", action="store_true", help="Disable Rich terminal UI and use plain text output")
    args = parser.parse_args()

    ui = RichUI(no_rich=args.no_rich)
    suppress_genai_non_text_warning()

    setup_instrumentation()
    ui.print_banner("SDAA: Security Documentation Analysis Agent")
    ui.print_status(f"Using provider: {args.model}")

    # 1. Map Maker
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = config_loader.get_output_dir()
    toc_path = os.path.join(output_dir, toc_filename)

    if args.skip_map_maker or args.coordinator_only:
        ui.print_status(f"\n[Phase 1] Skipping Map Maker due to --skip-map-maker flag. Expecting existing ToC at {toc_path}.")
    elif os.path.exists(toc_path):
        ui.print_status(f"\n[Phase 1] Skipping Map Maker because existing ToC was found at {toc_path}.")
    else:
        ui.print_status("\n[Phase 1] Initializing Map Maker...")
        try:
            # Instantiate model specifically for map_maker
            map_maker_model = get_model_for_agent("map_maker", args.model)
            await generate_toc(model=map_maker_model)
            ui.print_status(f"ToC generation complete. Wrote ToC to {toc_path}.")
        except Exception as e:
            ui.print_error(f"generating ToC: {e}")

    if args.toc_only:
        ui.print_status("[Phase 1] --toc-only specified; exiting after Map Maker.")
        return

    # 2. Initialize Agent
    ui.print_status("\n[Phase 2] Initializing Coordinator...")
    # Pass provider to create_coordinator_agent
    coordinator = create_coordinator_agent(provider=args.model)

    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()

    # Initialize Runner
    runner = Runner(
        agent=coordinator,
        app_name="sdaa",
        session_service=session_service,
        memory_service=memory_service
    )
    session_id = "session_001"
    user_id = "user_001"

    # Create Session explicitly
    try:
        session = await session_service.get_session(
            app_name="sdaa",
            user_id=user_id,
            session_id=session_id
        )
        if not session:
            session = await session_service.create_session(
                app_name="sdaa",
                user_id=user_id,
                session_id=session_id
            )
        # print(f"Session created: {session.id}")

    except Exception as e:
        ui.print_error(f"creating session: {e}")

    # Ensure output directories exist
    config_loader.get_reports_dir()
    config_loader.get_artifacts_dir()
    missing_outputs = get_missing_prechat_outputs()
    if missing_outputs or args.coordinator_only:
        ui.print_status(
            "\n[Phase 2.5] Running Pre-chat Audit..."
        )
        prechat_agent = build_prechat_audit_agent(provider=args.model, coordinator_only=args.coordinator_only)
        prechat_runner = Runner(
            agent=prechat_agent,
            app_name="sdaa",
            session_service=session_service,
            memory_service=memory_service
        )
        try:
            await ui.stream_response(
                prechat_runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=types.Content(parts=[types.Part.from_text(text="Audit the application")])
                ),
                title="Pre-chat Audit"
            )
            ui.print_status("Pre-chat audit complete.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            ui.print_error(f"\n{e}")
    else:
        ui.print_status("\n[Phase 2.5] Skipping Pre-chat Audit (outputs present).")

    ui.print_status("\n[Phase 3] Agent Ready. (Type 'exit' to quit)")

    while True:
        try:
            user_input = ui.ask_user("\nUser> ")
            if user_input.lower() in ('exit', 'quit'):
                break

            await ui.stream_response(
                runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=types.Content(parts=[types.Part.from_text(text=user_input)])
                ),
                title="Coordinator"
            )

        except KeyboardInterrupt:
            break
        except Exception as e:
            ui.print_error(f"\n{e}")
            break

if __name__ == "__main__":
    asyncio.run(main())
