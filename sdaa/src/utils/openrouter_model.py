import os
import json
import logging
from typing import AsyncGenerator, Optional, List, Dict, Any
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types
from openai import AsyncOpenAI, RateLimitError
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from pydantic import PrivateAttr
from sdaa.src.core.key_rotator import get_key_rotator

try:
    from langfuse import LangfuseOtelSpanAttributes
except ImportError:
    # Fallback if langfuse is not installed or import fails
    class LangfuseOtelSpanAttributes:
        OBSERVATION_PROMPT_NAME = "langfuse.observation.prompt.name"
        OBSERVATION_PROMPT_VERSION = "langfuse.observation.prompt.version"

logger = logging.getLogger(__name__)

REASONING_MIME_TYPE = "application/x-reasoning-details"

class OpenRouterModel(BaseLlm):
    model: str
    client: Any # AsyncOpenAI
    _langfuse_prompt: Optional[Any] = None
    _rotator: Any = PrivateAttr()
    _base_url: str = PrivateAttr()

    def __init__(self, model_name: str, base_url: str = "https://openrouter.ai/api/v1", api_key: Optional[str] = None):
        rotator = get_key_rotator("openrouter")

        # If explicit api_key is provided, use it (override rotation), otherwise use rotator
        if api_key:
            client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        else:
            client = AsyncOpenAI(base_url=base_url, api_key=rotator.get_current_key())

        super().__init__(model=model_name, client=client)
        self._rotator = rotator
        self._base_url = base_url

    def set_langfuse_prompt(self, prompt_obj: Any):
        """
        Set the Langfuse prompt object associated with the next generation.

        Args:
            prompt_obj: The Langfuse prompt object (from client.get_prompt()).
        """
        self._langfuse_prompt = prompt_obj

    def _convert_schema(self, schema: Any) -> Dict[str, Any]:
        """Convert Google GenAI Schema to JSON Schema."""
        # Convert enum type to string (e.g. <Type.STRING: 'STRING'> -> 'string')
        schema_type = str(schema.type).upper()
        if "STRING" in schema_type: t = "string"
        elif "INTEGER" in schema_type: t = "integer"
        elif "NUMBER" in schema_type: t = "number"
        elif "BOOLEAN" in schema_type: t = "boolean"
        elif "ARRAY" in schema_type: t = "array"
        elif "OBJECT" in schema_type: t = "object"
        else:
            if schema.properties:
                t = "object"
            else:
                t = "string"

        json_schema = {"type": t}
        if schema.description:
            json_schema["description"] = schema.description

        if t == "object" and schema.properties:
            props = {}
            for k, v in schema.properties.items():
                props[k] = self._convert_schema(v)
            json_schema["properties"] = props
            if schema.required:
                json_schema["required"] = schema.required

        # TODO: Handle array items if strictly needed, but internal tools seem flat or simple.
        
        return json_schema

    def _convert_tools(self, tools: List[Any]) -> List[Dict[str, Any]]:
        """Convert Google GenAI Tools to OpenAI Tools format."""
        openai_tools = []
        for tool in tools:
            if hasattr(tool, 'function_declarations'):
                for func in tool.function_declarations:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": func.name,
                            "description": func.description,
                            "parameters": self._convert_schema(func.parameters)
                        }
                    })
        return openai_tools

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span(
            "OpenRouterModel.generate_content",
            kind=SpanKind.CLIENT,
            attributes={
                "openinference.span.kind": "LLM",
                "model_name": self.model
            }
        ) as span:

            # Link prompt if available
            if self._langfuse_prompt:
                try:
                    span.set_attribute(
                        LangfuseOtelSpanAttributes.OBSERVATION_PROMPT_NAME,
                        self._langfuse_prompt.name
                    )
                    span.set_attribute(
                        LangfuseOtelSpanAttributes.OBSERVATION_PROMPT_VERSION,
                        self._langfuse_prompt.version
                    )
                except Exception as e:
                    logger.warning(f"Failed to link Langfuse prompt to trace: {e}")

            # IMPROVED HISTORY HANDLING
            # Clear the messages list and rebuild it correctly from llm_request.contents
            messages = []

            # Add system instruction if present
            if llm_request.config and llm_request.config.system_instruction:
                 sys_text = ""
                 if hasattr(llm_request.config.system_instruction, 'parts'):
                     for part in llm_request.config.system_instruction.parts:
                         if part.text:
                             sys_text += part.text
                 else:
                     sys_text = str(llm_request.config.system_instruction)

                 if sys_text:
                    messages.append({"role": "system", "content": sys_text})

            # Iterate through contents to build conversation history
            if isinstance(llm_request.contents, list):
                for content in llm_request.contents:
                    role = content.role
                    if role == "model":
                        role = "assistant"
                    elif role == "tool":
                        role = "tool"
                    else:
                        role = "user"

                    content_parts = []
                    tool_calls = []
                    reasoning_details = None

                    if hasattr(content, 'parts'):
                        for part in content.parts:
                            if part.text:
                                content_parts.append(part.text)
                            
                            if part.inline_data and part.inline_data.mime_type == REASONING_MIME_TYPE:
                                try:
                                    reasoning_details = json.loads(part.inline_data.data.decode("utf-8"))
                                except Exception:
                                    pass

                            if hasattr(part, 'function_call') and part.function_call:
                                fc = part.function_call
                                tc_id = getattr(fc, 'id', None) or f"functions.{fc.name}:{len(tool_calls)}"

                                tool_calls.append({
                                    "id": tc_id,
                                    "type": "function",
                                    "function": {
                                        "name": fc.name,
                                        "arguments": json.dumps(fc.args) if fc.args else "{}"
                                    }
                                })

                            if hasattr(part, 'function_response') and part.function_response:
                                 fr = part.function_response
                                 tc_id = getattr(fr, 'id', None)

                                 if not tc_id:
                                     for msg in reversed(messages):
                                         if msg.get("role") == "assistant" and "tool_calls" in msg:
                                             for tc in msg["tool_calls"]:
                                                 if tc["function"]["name"] == fr.name:
                                                     tc_id = tc["id"]
                                                     break
                                         if tc_id: break

                                 if not tc_id:
                                     tc_id = f"call_unknown_{fr.name}"

                                 messages.append({
                                     "role": "tool",
                                     "tool_call_id": tc_id,
                                     "content": json.dumps(fr.response) if fr.response else ""
                                 })

                    # Construct message
                    if role == "assistant":
                        msg = {"role": "assistant"}
                        if content_parts:
                            msg["content"] = "".join(content_parts)
                        if tool_calls:
                            msg["tool_calls"] = tool_calls
                            if "content" not in msg:
                                msg["content"] = ""
                        messages.append(msg)

                    elif role == "user":
                        if content_parts:
                            messages.append({"role": "user", "content": "".join(content_parts)})
            
            # Process Tools
            openai_tools = None
            if llm_request.config and hasattr(llm_request.config, 'tools') and llm_request.config.tools:
                openai_tools = self._convert_tools(llm_request.config.tools)

            from openai import NOT_GIVEN

            extra_body = None
            if self.model == "x-ai/grok-4.1-fast":
                extra_body = {"reasoning": {"enabled": True}}

            # RETRY LOGIC FOR KEY ROTATION
            # We will try at most N times where N is number of keys (or 1 if no keys configured)
            max_attempts = max(1, self._rotator.get_key_count())
            attempt = 0

            while attempt < max_attempts:
                try:
                    should_stream = stream
                    if openai_tools:
                        should_stream = False

                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        stream=should_stream,
                        tools=openai_tools if openai_tools else NOT_GIVEN,
                        extra_body=extra_body
                    )

                    if should_stream:
                        async for chunk in response:
                            content_text = chunk.choices[0].delta.content or ""
                            if content_text:
                                content = types.Content(parts=[types.Part.from_text(text=content_text)])
                                yield LlmResponse(content=content)
                    else:
                        message = response.choices[0].message
                        parts = []

                        if message.tool_calls:
                            for i, tool_call in enumerate(message.tool_calls):
                                func_name = tool_call.function.name
                                tc_id = f"functions.{func_name}:{i}"
                                func_args = json.loads(tool_call.function.arguments)
                                parts.append(
                                    types.Part(
                                        function_call=types.FunctionCall(
                                            name=func_name,
                                            args=func_args,
                                            id=tc_id
                                        )
                                    )
                                )

                        if message.content:
                            parts.append(types.Part.from_text(text=message.content))

                        if hasattr(message, "reasoning_details") and message.reasoning_details:
                            try:
                                data_bytes = json.dumps(message.reasoning_details).encode("utf-8")
                                blob = types.Blob(mime_type=REASONING_MIME_TYPE, data=data_bytes)
                                parts.append(types.Part(inline_data=blob))
                            except Exception:
                                pass

                        if not parts:
                            parts.append(types.Part.from_text(text=""))

                        content = types.Content(parts=parts, role="model")
                        yield LlmResponse(content=content)

                    # If success, break loop
                    break

                except RateLimitError as e:
                    attempt += 1
                    logger.warning(f"Rate limit hit for OpenRouter key. Attempt {attempt}/{max_attempts}. Error: {e}")

                    if attempt >= max_attempts:
                        span.record_exception(e)
                        # Returning error message content as per original design?
                        # Or raising? User requested "fail immediately" after all keys fail.
                        # Original code returned error content. The user said "fail execution".
                        # But returning error content might be handled by agent.
                        # If I just raise, it bubbles up.
                        # However, previous code did `yield LlmResponse` with error message.
                        # If I want to "end execution", I should probably raise.
                        # But if I follow the pattern, I should yield error.
                        # Let's try to rotate first.
                        raise e # Raise so we can see the failure or let upper layer handle.

                    # Rotate key
                    new_key = self._rotator.rotate_key()
                    logger.info("Switching to next OpenRouter key.")
                    self.client = AsyncOpenAI(base_url=self._base_url, api_key=new_key)
                    # Loop continues

                except Exception as e:
                    # Non-retriable error (or at least not for key rotation)
                    span.record_exception(e)
                    error_msg = f"Error calling OpenRouter: {str(e)}"
                    content = types.Content(parts=[types.Part.from_text(text=error_msg)])
                    yield LlmResponse(content=content)
                    break
