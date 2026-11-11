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


def _record_usage(span, response) -> None:
    """Copy OpenRouter token counts and USD cost onto the span. Never raises."""
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        counts = {
            key: getattr(usage, field, None)
            for key, field in (("input", "prompt_tokens"), ("output", "completion_tokens"), ("total", "total_tokens"))
        }
        counts = {k: v for k, v in counts.items() if type(v) is int}
        if counts:
            span.set_attribute("langfuse.observation.usage_details", json.dumps(counts))
        cost = getattr(usage, "cost", None)
        if type(cost) in (int, float):
            span.set_attribute("langfuse.observation.cost_details", json.dumps({"total": cost}))
    except Exception as e:  # observability must not fail a model call
        logger.warning(f"Failed to record OpenRouter usage on span: {e}")

REASONING_MIME_TYPE = "application/x-reasoning-details"

class OpenRouterModel(BaseLlm):
    model: str
    client: Any  # AsyncOpenAI; Any so the client can be swapped on key rotation
    _langfuse_prompt: Optional[Any] = None
    _rotator: Any = PrivateAttr()
    _base_url: str = PrivateAttr()

    def __init__(self, model_name: str, base_url: str = "https://openrouter.ai/api/v1", api_key: Optional[str] = None):
        rotator = get_key_rotator("openrouter")
        # An explicit api_key overrides rotation for the first client.
        client = AsyncOpenAI(base_url=base_url, api_key=api_key or rotator.get_current_key())
        super().__init__(model=model_name, client=client)
        self._rotator = rotator
        self._base_url = base_url

    async def _create_with_rotation(self, **kwargs):
        """Call chat.completions.create; on HTTP 429 rotate to the next key and retry once per key."""
        max_attempts = max(1, self._rotator.get_key_count())
        for attempt in range(1, max_attempts + 1):
            try:
                return await self.client.chat.completions.create(**kwargs)
            except RateLimitError as e:
                if attempt >= max_attempts:
                    raise
                logger.warning(f"OpenRouter rate limit ({attempt}/{max_attempts}); rotating key. {e}")
                self.client = AsyncOpenAI(base_url=self._base_url, api_key=self._rotator.rotate_key())

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

        if t == "array" and schema.items:
            json_schema["items"] = self._convert_schema(schema.items)

        return json_schema

    def _declaration_parameters(self, func: Any) -> Dict[str, Any]:
        """JSON Schema for a function declaration's parameters.

        google-adk >= 2.x sets `parameters_json_schema` (already JSON Schema) and leaves
        `parameters` None; older declarations carry a `types.Schema` in `parameters`.
        The JSON Schema is passed through unchanged: its `title`/`default` keys are valid
        JSON Schema and OpenAI-compatible endpoints accept them (not verified live).
        """
        json_schema = getattr(func, "parameters_json_schema", None)
        if json_schema:
            return dict(json_schema)
        if getattr(func, "parameters", None) is not None:
            return self._convert_schema(func.parameters)
        return {"type": "object", "properties": {}}

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
                            "parameters": self._declaration_parameters(func)
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
                "llm.model_name": self.model
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
            # Use a more general check than isinstance(..., list)
            contents = llm_request.contents
            if contents and hasattr(contents, '__iter__'):
                for content in contents:
                    # Robust role extraction
                    role = None
                    if hasattr(content, 'role'):
                        role = content.role
                    elif isinstance(content, dict):
                        role = content.get('role')

                    if role == "model":
                        role = "assistant"
                    elif role == "tool":
                        role = "tool"
                    elif not role:
                        role = "user"

                    content_parts = []
                    tool_calls = []
                    reasoning_details = None

                    # Robust parts extraction
                    parts = []
                    if hasattr(content, 'parts'):
                        parts = content.parts
                    elif isinstance(content, dict):
                        parts = content.get('parts', [])

                    if parts:
                        for part in parts:
                            if hasattr(part, 'text') and part.text:
                                content_parts.append(part.text)
                            elif isinstance(part, dict) and part.get('text'):
                                content_parts.append(part.get('text'))
                            
                            # Reasoning details
                            inline_data = None
                            if hasattr(part, 'inline_data'):
                                inline_data = part.inline_data
                            elif isinstance(part, dict):
                                inline_data = part.get('inline_data')

                            if inline_data:
                                mime_type = getattr(inline_data, 'mime_type', None) or (inline_data.get('mime_type') if isinstance(inline_data, dict) else None)
                                if mime_type == REASONING_MIME_TYPE:
                                    data = getattr(inline_data, 'data', None) or (inline_data.get('data') if isinstance(inline_data, dict) else None)
                                    if data:
                                        try:
                                            if isinstance(data, bytes):
                                                reasoning_details = json.loads(data.decode("utf-8"))
                                            else:
                                                reasoning_details = json.loads(data)
                                        except Exception:
                                            pass

                            # Function call
                            fc = None
                            if hasattr(part, 'function_call'):
                                fc = part.function_call
                            elif isinstance(part, dict):
                                fc = part.get('function_call')

                            if fc:
                                name = getattr(fc, 'name', None) or (fc.get('name') if isinstance(fc, dict) else None)
                                args = getattr(fc, 'args', None) or (fc.get('args') if isinstance(fc, dict) else None)
                                tc_id = getattr(fc, 'id', None) or (fc.get('id') if isinstance(fc, dict) else None) or f"functions.{name}:{len(tool_calls)}"

                                tool_calls.append({
                                    "id": tc_id,
                                    "type": "function",
                                    "function": {
                                        "name": name,
                                        "arguments": json.dumps(args) if args else "{}"
                                    }
                                })

                            # Function response
                            fr = None
                            if hasattr(part, 'function_response'):
                                fr = part.function_response
                            elif isinstance(part, dict):
                                fr = part.get('function_response')

                            if fr:
                                name = getattr(fr, 'name', None) or (fr.get('name') if isinstance(fr, dict) else None)
                                response_val = getattr(fr, 'response', None) or (fr.get('response') if isinstance(fr, dict) else None)
                                tc_id = getattr(fr, 'id', None) or (fr.get('id') if isinstance(fr, dict) else None)

                                if not tc_id:
                                    # Try to find the last assistant message with a tool call for this function
                                    for msg in reversed(messages):
                                        if msg.get("role") == "assistant" and "tool_calls" in msg:
                                            for tc in msg["tool_calls"]:
                                                if tc["function"]["name"] == name:
                                                    tc_id = tc["id"]
                                                    break
                                        if tc_id: break

                                if not tc_id:
                                    tc_id = f"call_unknown_{name}"

                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc_id,
                                    "content": json.dumps(response_val) if response_val else ""
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
                        if reasoning_details:
                            msg["reasoning_details"] = reasoning_details
                        messages.append(msg)

                    elif role == "user":
                        if content_parts:
                            messages.append({"role": "user", "content": "".join(content_parts)})
            
            # Set input messages attribute for OpenInference
            try:
                # Format for OpenInference: JSON string or list of dicts
                span.set_attribute("llm.input_messages", json.dumps(messages))
            except Exception:
                pass

            if not messages:
                logger.warning("No messages to send to OpenRouter. Input contents might be improperly formatted.")

            # Process Tools
            openai_tools = None
            if llm_request.config and hasattr(llm_request.config, 'tools') and llm_request.config.tools:
                openai_tools = self._convert_tools(llm_request.config.tools)

            try:
                # Note: stream=False simplifies tool handling.
                should_stream = stream
                if openai_tools:
                    should_stream = False

                from openai import NOT_GIVEN

                extra_body = None
                if self.model == "x-ai/grok-4.1-fast":
                    extra_body = {"reasoning": {"enabled": True}}

                response = await self._create_with_rotation(
                    model=self.model,
                    messages=messages,
                    stream=should_stream,
                    tools=openai_tools if openai_tools else NOT_GIVEN,
                    extra_body=extra_body
                )

                if should_stream:
                    # ponytail: streamed calls record no usage; headless never streams. Read usage from the final chunk if chat cost matters.
                    async for chunk in response:
                        content_text = chunk.choices[0].delta.content or ""
                        if content_text:
                            content = types.Content(parts=[types.Part.from_text(text=content_text)])
                            yield LlmResponse(content=content)
                else:
                    _record_usage(span, response)
                    message = response.choices[0].message
                    parts = []

                    # Set output messages attribute for OpenInference
                    try:
                        output_msg = {"role": "assistant", "content": message.content}
                        if message.tool_calls:
                             output_msg["tool_calls"] = [
                                 {
                                     "id": tc.id,
                                     "type": "function",
                                     "function": {
                                         "name": tc.function.name,
                                         "arguments": tc.function.arguments
                                     }
                                 } for tc in message.tool_calls
                             ]
                        span.set_attribute("llm.output_messages", json.dumps([output_msg]))
                    except Exception:
                        pass

                    # Handle Tool Calls
                    if message.tool_calls:
                        for i, tool_call in enumerate(message.tool_calls):
                            func_name = tool_call.function.name
                            provider_id = getattr(tool_call, "id", None)
                            tc_id = provider_id if provider_id else f"functions.{func_name}:{i}"
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

                    # Handle Text
                    if message.content:
                        parts.append(types.Part.from_text(text=message.content))

                    # Handle Reasoning Details (if present)
                    if hasattr(message, "reasoning_details") and message.reasoning_details:
                        try:
                            data_bytes = json.dumps(message.reasoning_details).encode("utf-8")
                            blob = types.Blob(mime_type=REASONING_MIME_TYPE, data=data_bytes)
                            parts.append(types.Part(inline_data=blob))
                        except Exception:
                            pass # Ignore serialization errors

                    if not parts:
                        # Empty response?
                        parts.append(types.Part.from_text(text=""))

                    content = types.Content(parts=parts, role="model")
                    yield LlmResponse(content=content)

            except Exception as e:
                span.record_exception(e)
                raise
