import os
from typing import AsyncGenerator, Optional, List, Union
from pydantic import PrivateAttr
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types
from openai import AsyncOpenAI

class OpenRouterModel(BaseLlm):
    model: str = "anthropic/claude-3-opus"
    api_key: Optional[str] = None
    _client: AsyncOpenAI = PrivateAttr()
    _base_url: str = PrivateAttr(default="https://openrouter.ai/api/v1")

    def __init__(self, model: str = "anthropic/claude-3-opus", api_key: Optional[str] = None, **data):
        super().__init__(model=model, api_key=api_key, **data)
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self._base_url
        )

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:

        messages = []

        # Handle System Instruction
        if llm_request.config and llm_request.config.system_instruction:
            sys_content = llm_request.config.system_instruction
            sys_text = ""
            if hasattr(sys_content, "parts"):
                sys_text = "".join([part.text for part in sys_content.parts if part.text])
            else:
                sys_text = str(sys_content)

            if sys_text:
                messages.append({"role": "system", "content": sys_text})

        # Handle Contents
        contents = llm_request.contents
        if isinstance(contents, list):
            for content in contents:
                role = "user"
                if hasattr(content, "role") and content.role:
                     if content.role == "model":
                         role = "assistant"
                     else:
                         role = "user"

                text_parts = []
                if hasattr(content, "parts"):
                    for part in content.parts:
                        if part.text:
                            text_parts.append(part.text)

                if text_parts:
                    messages.append({"role": role, "content": "".join(text_parts)})
        else:
             # If contents is single Content object
            if hasattr(contents, "parts"):
                 text_parts = []
                 for part in contents.parts:
                        if part.text:
                            text_parts.append(part.text)
                 if text_parts:
                    messages.append({"role": "user", "content": "".join(text_parts)})


        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=stream,
                temperature=llm_request.config.temperature if llm_request.config and llm_request.config.temperature is not None else 1.0
            )

            if stream:
                async for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield LlmResponse(
                            content=types.Content(
                                parts=[types.Part.from_text(text=content)]
                            )
                        )
            else:
                content = response.choices[0].message.content
                if content:
                    yield LlmResponse(
                        content=types.Content(
                            parts=[types.Part.from_text(text=content)]
                        )
                    )
        except Exception as e:
            # We yield nothing or re-raise. Re-raising is better.
            raise e
