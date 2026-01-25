import sys
import asyncio
import argparse
import os
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

async def main():
    parser = argparse.ArgumentParser(description="SDAA: Security Documentation Analysis Agent")
    parser.add_argument("-m", "--model", choices=["gemini", "openrouter"], default="openrouter", help="Model provider to use")
    parser.add_argument("--skip-map-maker", action="store_true", help="Skip Map Maker and use an existing ToC.json if present")
    parser.add_argument("--toc-only", action="store_true", help="Run Map Maker only and exit before starting the coordinator")
    args = parser.parse_args()

    setup_instrumentation()
    print("SDAA: Security Documentation Analysis Agent")
    print("===========================================")
    print(f"Using provider: {args.model}")

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
        print(f"\n[Phase 1] Skipping Map Maker due to --skip-map-maker flag. Expecting existing ToC at {toc_path}.")
    elif os.path.exists(toc_path):
        print(f"\n[Phase 1] Skipping Map Maker because existing ToC was found at {toc_path}.")
    else:
        print("\n[Phase 1] Initializing Map Maker...")
        try:
            await generate_toc(model=model)
            print(f"ToC generation complete. Wrote ToC to {toc_path}.")
        except Exception as e:
            print(f"Error generating ToC: {e}")

    if args.toc_only:
        print("[Phase 1] --toc-only specified; exiting after Map Maker.")
        return

    # 2. Initialize Agent
    print("\n[Phase 2] Initializing Coordinator...")
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
        print(f"Error creating session: {e}")

    print("\n[Phase 3] Agent Ready. (Type 'exit' to quit)")

    while True:
        try:
            user_input = input("\nUser> ")
            if user_input.lower() in ('exit', 'quit'):
                break

            print("Coordinator> ", end="", flush=True)

            # run_async yields events.
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(parts=[types.Part.from_text(text=user_input)])
            ):
                if event.content:
                    if hasattr(event.content, 'parts'):
                         for part in event.content.parts:
                             if part.text:
                                 print(part.text, end="", flush=True)
                    else:
                        print(event.content, end="", flush=True)
            print() # Newline after response

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nError: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main())
