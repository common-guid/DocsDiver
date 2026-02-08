from typing import AsyncGenerator, Dict, Any, Optional
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types

class ArtifactLoaderModel(BaseLlm):
    """
    A model that simulates execution by returning a pre-defined artifact content via a tool call.
    It inspects the request history:
    1. If no tool has been called yet, it returns a FunctionCall to the specified tool
       with the artifact content as the argument.
    2. If the tool has been executed (FunctionResponse present), it returns a text
       confirmation to successfully complete the turn.
    """
    model: str = "artifact-loader-model"
    client: Optional[Any] = None
    content: str
    tool_name: str
    tool_arg_name: str

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        
        # Check if we have already called the tool (look for FunctionResponse in history)
        last_was_function_response = False
        if llm_request.contents:
            last_content = llm_request.contents[-1]
            if hasattr(last_content, 'parts'):
                for part in last_content.parts:
                    # Check for function_response attribute (standard in google-genai types)
                    if hasattr(part, 'function_response') and part.function_response:
                        last_was_function_response = True
                        break

        if last_was_function_response:
            # Step 2: Tool has successfully run (artifact saved/loaded). Return completion text.
            response_text = f"Artifact loaded and processed via {self.tool_name}."
            part = types.Part.from_text(text=response_text)
            yield LlmResponse(content=types.Content(parts=[part], role="model"))
        else:
            # Step 1: Instruct the agent to call the tool with our existing content.
            # This ensures the tool executes (saving the file again) and the agent history is consistent.
            # We must assign an ID to the tool call so that subsequent processing (e.g. OpenRouterModel)
            # can correctly link the tool call to its response.
            # We use a deterministic ID based on the tool name.
            fc = types.FunctionCall(
                name=self.tool_name,
                args={self.tool_arg_name: self.content},
                id=f"call_{self.tool_name}_artifact"
            )
            part = types.Part(function_call=fc)
            yield LlmResponse(content=types.Content(parts=[part], role="model"))
