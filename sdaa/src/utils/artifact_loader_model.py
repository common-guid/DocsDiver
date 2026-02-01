from typing import AsyncGenerator, Dict, Any, Optional
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types

class ArtifactLoaderModel(BaseLlm):
    """
    A model that simulates execution by returning a pre-defined artifact content.
    It returns the content directly as a text response, skipping tool execution
    since the artifact already exists.
    """
    model: str = "artifact-loader-model"
    client: Optional[Any] = None
    content: str
    tool_name: str
    tool_arg_name: str

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        
        # Return the content as text immediately.
        # This simulates the final step of the agent (returning the report).
        # We do NOT simulate the tool call because the artifact is already saved.
        part = types.Part.from_text(text=self.content)
        yield LlmResponse(content=types.Content(parts=[part], role="model"))
