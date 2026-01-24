import os
import asyncio
from typing import AsyncGenerator, Optional
from pydantic import PrivateAttr
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types, Client

class GeminiModel(BaseLlm):
    model: str = "gemini-1.5-pro"
    api_key: Optional[str] = None
    _client: Client = PrivateAttr()

    def __init__(self, model: str = "gemini-1.5-pro", api_key: Optional[str] = None, **data):
        super().__init__(model=model, api_key=api_key, **data)
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = Client(api_key=self.api_key)

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:

        config = types.GenerateContentConfig()
        if llm_request.config:
            if llm_request.config.temperature is not None:
                config.temperature = llm_request.config.temperature
            if llm_request.config.system_instruction:
                config.system_instruction = llm_request.config.system_instruction

        def _call_api():
            if stream:
                return self._client.models.generate_content_stream(
                    model=self.model,
                    contents=llm_request.contents,
                    config=config
                )
            else:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=llm_request.contents,
                    config=config
                )
                return [response]

        # Offload the blocking API call to a thread
        response_iterator = await asyncio.to_thread(_call_api)

        for chunk in response_iterator:
            # Ensure we have candidates before accessing
            if chunk.candidates and len(chunk.candidates) > 0:
                yield LlmResponse(content=chunk.candidates[0].content)
