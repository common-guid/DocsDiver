from typing import Optional, Any
from google.adk.models import Gemini, LlmRequest, LlmResponse
from opentelemetry import trace
from pydantic import PrivateAttr
import logging

logger = logging.getLogger(__name__)

try:
    from langfuse import LangfuseOtelSpanAttributes
except ImportError:
    # Fallback for when langfuse is not installed or import fails
    class LangfuseOtelSpanAttributes:
        OBSERVATION_PROMPT_NAME = "langfuse.prompt.name"
        OBSERVATION_PROMPT_VERSION = "langfuse.prompt.version"

class InstrumentedGemini(Gemini):
    """
    A subclass of Gemini that supports linking Langfuse prompts to OpenTelemetry spans.
    """
    _langfuse_prompt: Optional[Any] = PrivateAttr(default=None)

    def set_langfuse_prompt(self, prompt_obj: Any):
        """Link a Langfuse prompt object to this model instance."""
        self._langfuse_prompt = prompt_obj

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False):
        tracer = trace.get_tracer(__name__)

        # Start a manual span for Gemini generation
        # This acts as a reliable anchor for Langfuse prompt linking, regardless of internal ADK instrumentation
        with tracer.start_as_current_span("Gemini.generate_content") as span:
            if self._langfuse_prompt:
                try:
                    span.set_attribute(LangfuseOtelSpanAttributes.OBSERVATION_PROMPT_NAME, self._langfuse_prompt.name)
                    span.set_attribute(LangfuseOtelSpanAttributes.OBSERVATION_PROMPT_VERSION, self._langfuse_prompt.version)
                    logger.debug(f"Linked prompt '{self._langfuse_prompt.name}' (v{self._langfuse_prompt.version}) to trace.")
                except Exception as e:
                    logger.warning(f"Failed to link Langfuse prompt to trace: {e}")

            # Delegate to the parent implementation
            async for chunk in super().generate_content_async(llm_request, stream=stream):
                yield chunk
