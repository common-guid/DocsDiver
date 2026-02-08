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
                                # Map FunctionCall to OpenAI tool_calls
                                # We need a tool_call_id. ADK might not persist it in the FunctionCall object directly
                                # if it's just a data class. We might need to generate a deterministic one or see if it's there.
                                # For OpenRouter/OpenAI, the tool usage flow is Strict: Assistant (tool_call) -> Tool (result).
                                # If we don't have IDs in history, we might face issues.
                                # Let's generate a mock ID if missing, but consistency is key.

                                fc = part.function_call
                                # Attempt to use specific ID if available, otherwise generate one
                                # Note: google.genai types might not have 'id' on FunctionCall.
                                # We'll check via getattr.
                                # Fix for ID mismatch: use deterministic ID format matching ADK/generation
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
                                 # Map FunctionResponse to OpenAI tool message
                                 fr = part.function_response
                                 # We need the id of the call this response is for.
                                 # If ADK doesn't store it, we verify if OpenRouter accepts just matching names?
                                 # No, OpenAI API requires tool_call_id.
                                 # If we generated ID above based on position, we might tricky.
                                 # HOWEVER, in standard ADK flow, the generic runner usually keeps history.

                                 # Critical: We must find the ID.
                                 # If we can't find it, we'll generate one and hope for loose validation or
                                 # that we can infer it.
                                 # For now, let's use the 'id' field if it exists.
                                 tc_id = getattr(fr, 'id', None)

                                 # Fallback: if we just saw a tool call in the previous message, grab its ID?
                                 # This implementation iterates sequentially.

                                 if not tc_id:
                                     # Try to find the last assistant message with a tool call for this function
                                     # This is a heuristic.
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
                            # Ensure content is empty string if only tool calls (null is standard, but some providers require string)
                            if "content" not in msg:
                                msg["content"] = ""
                        # Note: xAI/Grok might fail if 'reasoning_details' is included in the message struct.
                        # We omit it from the request payload to ensure compatibility.
                        # if reasoning_details:
                        #     msg["reasoning_details"] = reasoning_details
                        messages.append(msg)

                    elif role == "user":
                        if content_parts:
                            messages.append({"role": "user", "content": "".join(content_parts)})
            
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
                    async for chunk in response:
                        content_text = chunk.choices[0].delta.content or ""
                        if content_text:
                            content = types.Content(parts=[types.Part.from_text(text=content_text)])
                            yield LlmResponse(content=content)
                else:
                    message = response.choices[0].message
                    parts = []

                    # Handle Tool Calls
                    if message.tool_calls:
                        for i, tool_call in enumerate(message.tool_calls):
                            # Force ADK-compliant ID format: functions.{name}:{index}
                            # This appears to be what the ADK runner expects or generates for responses.
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
