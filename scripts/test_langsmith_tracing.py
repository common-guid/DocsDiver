import os
import asyncio

from dotenv import load_dotenv
from opentelemetry import trace

from sdaa.src.core.instrumentation import setup_instrumentation
from sdaa.src.utils.mock_model import MockModel

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types


APP_NAME = "observability_test_app"
USER_ID = "test_user"
SESSION_ID = "test_session"


# Load .env so LANGSMITH_* and other variables are available
load_dotenv()


async def main() -> None:
    print("\n--- Testing LangSmith / Google ADK tracing ---")

    ls_api_key_present = bool(os.getenv("LANGSMITH_API_KEY"))
    ls_project = os.getenv("LANGSMITH_PROJECT")
    ls_endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    print(f"LANGSMITH_API_KEY present: {ls_api_key_present}")
    print(f"LANGSMITH_PROJECT: {ls_project or '<not set>'}")
    print(f"LANGSMITH_ENDPOINT: {ls_endpoint}")

    # Initialize our observability stack (Langfuse + LangSmith + ADK instrumentation)
    setup_instrumentation()

    # Emit a simple root span so you can easily find it in LangSmith
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("adk_docsdiver_test_root_span") as span:
        span.set_attribute("langsmith.metadata.test_case", "adk_docsdiver_manual_check")

        # Minimal ADK agent + runner using the MockModel, so no external LLM calls are made
        model = MockModel(model="mock-model")
        agent = LlmAgent(
            name="observability_test_agent",
            model=model,
            instruction="You are a trivial test agent used only to exercise tracing.",
        )

        runner = InMemoryRunner(agent=agent, app_name=APP_NAME)

        # Ensure the session exists before running, to avoid "Session not found" errors
        await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

        # Run a single short message through the agent to trigger Google ADK spans
        async for _ in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=types.Content(parts=[types.Part.from_text(text="ping")]),
        ):
            # We only need the first event to ensure the pipeline is exercised
            break

    print("\nCompleted test span and ADK run.")
    print(
        "If LangSmith is configured correctly, you should see a trace named "
        "'adk_docsdiver_test_root_span' in the 'ADK-DocsDiver' project within a few seconds."
    )


if __name__ == "__main__":
    asyncio.run(main())
