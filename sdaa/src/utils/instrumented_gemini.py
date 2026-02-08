import logging
from typing import AsyncGenerator, Optional, Any
from google.adk.models import Gemini, LlmRequest, LlmResponse
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

class InstrumentedGemini(Gemini):
    """
    A subclass of Gemini that adds Langfuse prompt linking to traces.
    """
    _langfuse_prompt: Optional[Any] = None

    def set_langfuse_prompt(self, prompt_obj: Any):
        """
        Set the Langfuse prompt object associated with the next generation.

        Args:
            prompt_obj: The Langfuse prompt object (from client.get_prompt()).
        """
        self._langfuse_prompt = prompt_obj

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:

        tracer = trace.get_tracer(__name__)

        # Start a manual span to ensure we capture the generation and can tag it
        with tracer.start_as_current_span(
            "Gemini.generate_content",
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

            try:
                async for response in super().generate_content_async(llm_request, stream=stream):
                    yield response
            except Exception as e:
                span.record_exception(e)
                raise
