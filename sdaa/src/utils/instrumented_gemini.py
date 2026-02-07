from typing import Optional, Any
from google.adk.models import Gemini, LlmRequest, LlmResponse
from opentelemetry import trace, baggage, context
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
        token = None
        if self._langfuse_prompt:
            try:
                # Use Baggage to propagate prompt metadata to the child span created by auto-instrumentation
                # We create a new context with the baggage and attach it.
                ctx = context.get_current()
                ctx = baggage.set_baggage("langfuse.prompt.name", self._langfuse_prompt.name, context=ctx)
                ctx = baggage.set_baggage("langfuse.prompt.version", str(self._langfuse_prompt.version), context=ctx)
                token = context.attach(ctx)

                logger.debug(f"Attached baggage for prompt '{self._langfuse_prompt.name}' (v{self._langfuse_prompt.version})")
            except Exception as e:
                logger.warning(f"Failed to attach Langfuse prompt baggage: {e}")

        try:
            # Delegate to the parent implementation within the context
            async for chunk in super().generate_content_async(llm_request, stream=stream):
                yield chunk
        finally:
            if token is not None:
                context.detach(token)
