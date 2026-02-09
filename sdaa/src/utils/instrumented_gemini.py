import logging
import asyncio
from functools import cached_property
from typing import AsyncGenerator, Optional, Any
from google.adk.models import Gemini, BaseLlm, LlmRequest, LlmResponse
from google.genai import types
from google.api_core.exceptions import TooManyRequests
from google.genai.errors import ClientError
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

class _InnerGemini(Gemini):
    """
    Private helper class that overrides api_client to accept an explicit API key.
    """
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        # We pass kwargs to Gemini (e.g. model)
        # We store api_key for use in api_client property
        self._api_key = api_key
        super().__init__(**kwargs)

    @cached_property
    def api_client(self):
        """Override api_client to inject the API key."""
        from google.genai import Client
        # Client constructor accepts api_key. If None, it falls back to env vars.
        return Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(
                headers=self._tracking_headers(),
                retry_options=self.retry_options,
            )
        )

class InstrumentedGemini(BaseLlm):
    """
    A wrapper around Gemini that adds Langfuse prompt linking and key rotation.
    It manages an internal Gemini instance which it recreates upon key rotation.
    """
    _langfuse_prompt: Optional[Any] = None
    _current_gemini: Any = PrivateAttr() # _InnerGemini
    _rotator: Any = PrivateAttr()

    def __init__(self, model: str):
        # Initialize BaseLlm with model name
        super().__init__(model=model)
        self._rotator = get_key_rotator("gemini")
        self._initialize_gemini_client()

    def _initialize_gemini_client(self):
        """Create a new inner Gemini instance with the current key."""
        key = self._rotator.get_current_key()
        # Create _InnerGemini with current key and model
        self._current_gemini = _InnerGemini(api_key=key, model=self.model)

    def set_langfuse_prompt(self, prompt_obj: Any):
        """
        Set the Langfuse prompt object associated with the next generation.
        """
        self._langfuse_prompt = prompt_obj

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:

        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span(
            "Gemini.generate_content",
            kind=SpanKind.CLIENT,
            attributes={
                "openinference.span.kind": "LLM",
                "model_name": self.model
            }
        ) as span:

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

            # Calculate max attempts based on available keys
            key_count = self._rotator.get_key_count()
            max_attempts = max(1, key_count)
            attempt = 0

            # Start retry loop
            while attempt < max_attempts:
                try:
                    # Delegate generation to the current inner Gemini instance
                    async for response in self._current_gemini.generate_content_async(llm_request, stream=stream):
                        yield response

                    # If we reach here, generation was successful (no exception raised)
                    return

                except Exception as e:
                    # Check if error is a rate limit (429)
                    is_rate_limit = False

                    # Check specific exception types or codes
                    if isinstance(e, TooManyRequests):
                        is_rate_limit = True
                    elif isinstance(e, ClientError) and getattr(e, 'code', None) == 429:
                        is_rate_limit = True
                    # Also check for message content if needed, but code is safer

                    if not is_rate_limit:
                        # Non-retriable error
                        span.record_exception(e)
                        raise e

                    # It is a rate limit error
                    attempt += 1
                    logger.warning(f"Rate limit hit for Gemini key. Attempt {attempt}/{max_attempts}. Error: {e}")

                    if attempt >= max_attempts:
                        # Exhausted all retries/keys
                        span.record_exception(e)
                        raise e

                    # Rotate key and retry
                    try:
                        self._rotator.rotate_key()
                        logger.info("Switching to next Gemini key.")
                        self._initialize_gemini_client()
                    except ValueError as ve:
                        # Should not happen if key_count > 0, but safety check
                        logger.error(f"Failed to rotate key: {ve}")
                        raise e

                    # Loop continues to retry with new client
