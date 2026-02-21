import os
import json
import logging
from typing import AsyncGenerator, Optional, List, Dict, Any
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types
from openai import AsyncOpenAI
from opentelemetry import trace
from opentelemetry.trace import SpanKind

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
    client: AsyncOpenAI
    _langfuse_prompt: Optional[Any] = None

    def __init__(self, model_name: str, base_url: str = "https://openrouter.ai/api/v1", api_key: Optional[str] = None):
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
        )
        super().__init__(model=model_name, client=client)

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

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=should_stream,
                    tools=openai_tools if openai_tools else NOT_GIVEN,
                    extra_body=extra_body
                )

                if should_stream:
                    # TODO: Properly instrument streaming output if needed
                    async for chunk in response:
                        content_text = chunk.choices[0].delta.content or ""
                        if content_text:
                            content = types.Content(parts=[types.Part.from_text(text=content_text)])
                            yield LlmResponse(content=content)
                else:
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
                            # Force ADK-compliant ID format: functions.{name}:{index}
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
                # Handle error gracefully or re-raise
                # Record exception in span
                span.record_exception(e)
                # Returning an error message as content for now
                error_msg = f"Error calling OpenRouter: {str(e)}"
                content = types.Content(parts=[types.Part.from_text(text=error_msg)])
                yield LlmResponse(content=content)
