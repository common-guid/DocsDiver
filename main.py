import sys
import asyncio
import argparse
import os
import logging
from sdaa.src.core.instrumentation import setup_instrumentation
from sdaa.src.core.config_loader import config_loader
from sdaa.src.core.map_maker import generate_toc
from sdaa.src.agents.coordinator import create_coordinator_agent
from sdaa.src.utils.mock_model import MockModel
from sdaa.src.utils.openrouter_model import OpenRouterModel
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types
from google.adk.sessions import Session
from sdaa.src.ui.rich_chat import RichUI
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

async def main():
    parser = argparse.ArgumentParser(description="SDAA: Security Documentation Analysis Agent")
    parser.add_argument("-m", "--model", choices=["gemini", "openrouter", "mock"], default="openrouter", help="Model provider to use")
    parser.add_argument("--skip-map-maker", action="store_true", help="Skip Map Maker and use an existing ToC.json if present")
    parser.add_argument("--toc-only", action="store_true", help="Run Map Maker only and exit before starting the coordinator")
    parser.add_argument("--no-rich", action="store_true", help="Disable Rich terminal UI and use plain text output")
    args = parser.parse_args()

    ui = RichUI(no_rich=args.no_rich)
    suppress_genai_non_text_warning()

    setup_instrumentation()
    ui.print_banner("SDAA: Security Documentation Analysis Agent")
    ui.print_status(f"Using provider: {args.model}")

    # Select model
    if args.model == "gemini":
        model_name = config_loader.get("providers.gemini.model_name", "gemini-2.5-pro")
        # Assuming Gemini class takes model name as argument or keyword argument
        # Based on typical ADK usage and MockModel structure
        model = Gemini(model=model_name)
    elif args.model == "openrouter":
        model_name = config_loader.get("providers.openrouter.model_name", "anthropic/claude-3-opus")
        base_url = config_loader.get("providers.openrouter.base_url", "https://openrouter.ai/api/v1")
        model = OpenRouterModel(model_name=model_name, base_url=base_url)
    else:
        # Fallback (should not happen due to argparse choices, but good for safety)
        model = MockModel(model="mock-model")

    # 1. Map Maker
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = config_loader.get_output_dir()
    toc_path = os.path.join(output_dir, toc_filename)

    if args.skip_map_maker:
        ui.print_status(f"\n[Phase 1] Skipping Map Maker due to --skip-map-maker flag. Expecting existing ToC at {toc_path}.")
    elif os.path.exists(toc_path):
        ui.print_status(f"\n[Phase 1] Skipping Map Maker because existing ToC was found at {toc_path}.")
    else:
        ui.print_status("\n[Phase 1] Initializing Map Maker...")
        try:
            await generate_toc(model=model)
            ui.print_status(f"ToC generation complete. Wrote ToC to {toc_path}.")
        except Exception as e:
            ui.print_error(f"generating ToC: {e}")

    if args.toc_only:
        ui.print_status("[Phase 1] --toc-only specified; exiting after Map Maker.")
        return

    # 2. Initialize Agent
    ui.print_status("\n[Phase 2] Initializing Coordinator...")
    coordinator = create_coordinator_agent(model=model)

    # Initialize Runner
    runner = InMemoryRunner(agent=coordinator, app_name="sdaa")
    session_id = "session_001"
    user_id = "user_001"

    # Create Session explicitly
    try:
        session = await runner.session_service.create_session(
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

    ui.print_status("\n[Phase 2.5] Running Pre-chat Audit...")
    try:
        await ui.stream_response(
            runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(parts=[types.Part.from_text(text="Audit the application")])
            ),
            title="Coordinator (Audit)"
        )
        ui.print_status("Audit complete.")
    except Exception as e:
        ui.print_error(f"\nduring audit: {e}")

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
