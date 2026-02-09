import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import os
import pytest
from openai import RateLimitError
from google.api_core.exceptions import TooManyRequests
from google.genai.errors import ClientError
from google.genai import types

from sdaa.src.core.key_rotator import KeyRotator, get_key_rotator
from sdaa.src.utils.openrouter_model import OpenRouterModel
from sdaa.src.utils.instrumented_gemini import InstrumentedGemini
from google.adk.models import LlmRequest, LlmResponse

class TestKeyRotator(unittest.TestCase):

    def test_load_keys(self):
        os.environ["TEST_KEYS"] = "key1,key2,key3"
        rotator = KeyRotator("test", "TEST_KEYS")
        self.assertEqual(rotator.get_key_count(), 3)
        self.assertEqual(rotator.get_current_key(), "key1")

    def test_rotate_keys(self):
        os.environ["TEST_KEYS"] = "key1,key2"
        rotator = KeyRotator("test", "TEST_KEYS")
        self.assertEqual(rotator.get_current_key(), "key1")

        k = rotator.rotate_key()
        self.assertEqual(k, "key2")
        self.assertEqual(rotator.get_current_key(), "key2")

        k = rotator.rotate_key()
        self.assertEqual(k, "key1") # Wrapped around
        self.assertEqual(rotator.get_current_key(), "key1")

    def test_single_key(self):
        os.environ["TEST_KEYS"] = "key1"
        rotator = KeyRotator("test", "TEST_KEYS")
        self.assertEqual(rotator.get_key_count(), 1)
        self.assertEqual(rotator.rotate_key(), "key1")

    def test_no_keys(self):
        if "TEST_KEYS_EMPTY" in os.environ:
            del os.environ["TEST_KEYS_EMPTY"]
        rotator = KeyRotator("test", "TEST_KEYS_EMPTY")
        self.assertEqual(rotator.get_key_count(), 0)
        with self.assertRaises(ValueError):
            rotator.rotate_key()


@patch("sdaa.src.utils.openrouter_model.get_key_rotator")
@patch("sdaa.src.utils.openrouter_model.AsyncOpenAI")
class TestOpenRouterRotation(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.llm_request = MagicMock(spec=LlmRequest)
        self.llm_request.contents = []
        self.llm_request.config = MagicMock()
        self.llm_request.config.tools = None
        self.llm_request.config.system_instruction = None

    async def test_rotation_on_429(self, mock_openai_cls, mock_get_rotator):
        # Setup Rotator Mock
        mock_rotator = MagicMock()
        mock_rotator.get_key_count.return_value = 2
        mock_rotator.get_current_key.side_effect = ["key1", "key2"]
        mock_rotator.rotate_key.return_value = "key2"
        mock_get_rotator.return_value = mock_rotator

        # Setup OpenAI Client Mock
        mock_client = AsyncMock()
        mock_openai_cls.return_value = mock_client

        # Mock create to fail first, then succeed
        error_429 = RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)

        async def side_effect(*args, **kwargs):
            if mock_client.chat.completions.create.call_count == 1:
                raise error_429
            # Return success mock
            resp = MagicMock()
            resp.choices = [MagicMock(message=MagicMock(content="Success", tool_calls=None))]
            return resp

        mock_client.chat.completions.create.side_effect = side_effect

        model = OpenRouterModel("test-model")

        # Execute
        responses = [r async for r in model.generate_content_async(self.llm_request)]

        # Verify
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].content.parts[0].text, "Success")

        # Check calls
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
        mock_rotator.rotate_key.assert_called_once()

        # Verify client was re-initialized with new key
        calls = mock_openai_cls.call_args_list
        self.assertEqual(len(calls), 2)

    async def test_exhaustion(self, mock_openai_cls, mock_get_rotator):
        # Setup Rotator
        mock_rotator = MagicMock()
        mock_rotator.get_key_count.return_value = 2
        mock_get_rotator.return_value = mock_rotator

        mock_client = AsyncMock()
        mock_openai_cls.return_value = mock_client

        error_429 = RateLimitError("Rate limit", response=MagicMock(), body=None)
        mock_client.chat.completions.create.side_effect = error_429

        model = OpenRouterModel("test-model")

        with self.assertRaises(RateLimitError):
            [r async for r in model.generate_content_async(self.llm_request)]

        self.assertEqual(mock_client.chat.completions.create.call_count, 2)


@patch("sdaa.src.utils.instrumented_gemini.get_key_rotator")
@patch("sdaa.src.utils.instrumented_gemini._InnerGemini")
class TestGeminiRotation(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.llm_request = MagicMock(spec=LlmRequest)

    async def test_rotation_on_429(self, mock_inner_gemini_cls, mock_get_rotator):
        mock_rotator = MagicMock()
        mock_rotator.get_key_count.return_value = 2
        mock_rotator.get_current_key.return_value = "key1"
        mock_get_rotator.return_value = mock_rotator

        # Mock Inner Gemini instances
        gemini_1 = MagicMock()
        gemini_2 = MagicMock()

        # Make generate_content_async raise 429 on first instance
        async def gen_1(*args, **kwargs):
            if False: yield # Force generator
            raise TooManyRequests("Rate limit")

        gemini_1.generate_content_async.side_effect = gen_1

        # Make second instance succeed
        async def gen_2(*args, **kwargs):
            content = types.Content(role="model", parts=[types.Part.from_text(text="Success")])
            yield LlmResponse(content=content)
        gemini_2.generate_content_async.side_effect = gen_2

        # side_effect for class constructor (mocks return values of _InnerGemini())
        mock_inner_gemini_cls.side_effect = [gemini_1, gemini_2]

        model = InstrumentedGemini("gemini-pro")

        # Execute
        responses = [r async for r in model.generate_content_async(self.llm_request)]

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].content.parts[0].text, "Success")

        # Verify rotation
        mock_rotator.rotate_key.assert_called_once()
        self.assertEqual(mock_inner_gemini_cls.call_count, 2) # Initial + Re-init

if __name__ == "__main__":
    unittest.main()
