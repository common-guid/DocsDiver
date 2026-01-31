
import asyncio
import os
from sdaa.src.utils.openrouter_model import OpenRouterModel
from google.adk.models import LlmRequest
from google.genai import types

async def reproduce():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Skipping reproduction: OPENROUTER_API_KEY not set")
        return

    model = OpenRouterModel(model_name="moonshotai/kimi-k2.5", api_key=api_key)

    # 1. First turn: User asks a question that requires a tool
    # We'll mock the config with a tool definition
    
    tool_code = """
    def get_weather(location: str):
        '''Get the weather for a location.'''
        return "Sunny"
    """
    
    # We can't easily construct the full adk Tool object here without the full machinery, 
    # but we can check if OpenRouterModel correctly structures the history.
    # Actually, the error comes from the Runner or underlying logic not seeing the FunctionCall in the history
    # when it processes the FunctionResponse.
    
    # Let's verify what OpenRouterModel generates for a simple history of [User, Model(ToolCall), User(ToolResult)]
    
    # Step 1: Simulate sending a history provided by ADK runner
    # ADK sends a list of Content objects.
    
    # Case: History contains a Function Call and a Function Response
    # The Runner expects the model to see this history correctly.
    
    mock_func_call = types.Part(
        function_call=types.FunctionCall(name="get_weather", args={"location": "Paris"})
    )
    # Note: treating this as if it came from the model previously. 
    # In ADK, model responses become parts of the history.
    # However, OpenRouterModel.generate_content_async takes llm_request.contents.
    
    content_turn_1_user = types.Content(role="user", parts=[types.Part.from_text(text="What is the weather in Paris?")])
    content_turn_2_model = types.Content(role="model", parts=[mock_func_call]) 
    content_turn_3_tool = types.Content(role="tool", parts=[types.Part(function_response=types.FunctionResponse(name="get_weather", response={"result": "Sunny"}))])
    
    request = LlmRequest(
        model="moonshotai/kimi-k2.5",
        contents=[content_turn_1_user, content_turn_2_model, content_turn_3_tool]
    )
    
    print("\n--- Sending Request with History ---")
    try:
        async for response in model.generate_content_async(request):
            print("Response chunk:", response)
    except Exception as e:
        print(f"Error during generation: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce())
