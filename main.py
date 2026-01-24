import sys
import asyncio
from sdaa.src.core.instrumentation import setup_instrumentation
from sdaa.src.core.config_loader import config_loader
from sdaa.src.core.map_maker import generate_toc
from sdaa.src.agents.coordinator import create_coordinator_agent
from sdaa.src.utils.mock_model import MockModel
from google.adk.runners import InMemoryRunner
from google.genai import types
from google.adk.sessions import Session

async def main():
    setup_instrumentation()
    print("SDAA: Security Documentation Analysis Agent")
    print("===========================================")

    # 1. Map Maker
    print("\n[Phase 1] Initializing Map Maker...")
    try:
        await generate_toc()
        print("ToC generation complete.")
    except Exception as e:
        print(f"Error generating ToC: {e}")

    # 2. Initialize Agent
    print("\n[Phase 2] Initializing Coordinator...")
    # Using MockModel for all agents as per plan
    model = MockModel(model="mock-model")
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
