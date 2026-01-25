import os
from typing import AsyncGenerator, Optional, List
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types
from openai import AsyncOpenAI

class OpenRouterModel(BaseLlm):
    model: str
    client: AsyncOpenAI

    def __init__(self, model_name: str, base_url: str = "https://openrouter.ai/api/v1", api_key: Optional[str] = None):
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
        )
        super().__init__(model=model_name, client=client)

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:

        messages = []

        # System instruction
        if llm_request.config and llm_request.config.system_instruction:
             # system_instruction is usually a Content object
             sys_text = ""
             if hasattr(llm_request.config.system_instruction, 'parts'):
                 for part in llm_request.config.system_instruction.parts:
                     if part.text:
                         sys_text += part.text
             else:
                 sys_text = str(llm_request.config.system_instruction)

             if sys_text:
                messages.append({"role": "system", "content": sys_text})

        # User contents
        # llm_request.contents is expected to be a list of Content objects
        # We need to serialize this to OpenAI format.
        # ADK might send multiple Content objects for chat history?
        # Or just one for the current prompt?
        # Assuming simple concatenation for now or mapping based on ADK patterns.

        user_content_str = ""
        if isinstance(llm_request.contents, list):
            for content in llm_request.contents:
                if hasattr(content, 'parts'):
                    for part in content.parts:
                        if part.text:
                            user_content_str += part.text
                else:
                    user_content_str += str(content)
        elif hasattr(llm_request.contents, 'parts'):
             for part in llm_request.contents.parts:
                if part.text:
                    user_content_str += part.text
        else:
             user_content_str = str(llm_request.contents)

        if user_content_str:
             messages.append({"role": "user", "content": user_content_str})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=stream
            )

            if stream:
                async for chunk in response:
                    content_text = chunk.choices[0].delta.content or ""
                    if content_text:
                        content = types.Content(parts=[types.Part.from_text(text=content_text)])
                        yield LlmResponse(content=content)
            else:
                content_text = response.choices[0].message.content or ""
                content = types.Content(parts=[types.Part.from_text(text=content_text)])
                yield LlmResponse(content=content)

        except Exception as e:
            # Handle error gracefully or re-raise
            # Returning an error message as content for now
            error_msg = f"Error calling OpenRouter: {str(e)}"
            content = types.Content(parts=[types.Part.from_text(text=error_msg)])
            yield LlmResponse(content=content)
