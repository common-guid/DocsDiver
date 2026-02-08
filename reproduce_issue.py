import asyncio
import os
import json
from google.genai import types
from google.adk.models import LlmRequest, LlmResponse
from sdaa.src.utils.openrouter_model import OpenRouterModel

async def test():
    model = OpenRouterModel("x-ai/grok-4.1-fast")

    # Simulate a history with a tool call to a tool that is NOT in the current request's config
    history = [
        types.Content(role="user", parts=[types.Part.from_text(text="Do something")]),
        types.Content(role="model", parts=[
            types.Part(function_call=types.FunctionCall(name="old_tool", args={"arg": "value"}))
        ]),
        types.Content(role="tool", parts=[
            types.Part(function_response=types.FunctionResponse(name="old_tool", response={"result": "ok"}))
        ]),
        types.Content(role="user", parts=[types.Part.from_text(text="Now summarize")])
    ]

    # Current request config has NO tools (or different tools)
    request = LlmRequest(
        contents=history,
        config=types.GenerateContentConfig(tools=[])
    )

    print("Sending request...")
    try:
        async for response in model.generate_content_async(request):
            print("Response:", response.content.parts[0].text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test())
