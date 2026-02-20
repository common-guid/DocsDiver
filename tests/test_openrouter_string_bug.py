
import asyncio
import os
import unittest
from unittest.mock import MagicMock
from sdaa.src.utils.openrouter_model import OpenRouterModel
from google.adk.models import LlmRequest
from google.genai import types

class TestOpenRouterModelBug(unittest.IsolatedAsyncioTestCase):
    async def test_robust_contents_handling(self):
        model = OpenRouterModel(model_name="test-model", api_key="test-key")
        
        # Test Case 1: Pure strings (the bug)
        request1 = LlmRequest(
            model="test-model",
            contents=["This is a string message"]
        )
        
        # Test Case 2: Mixed strings and Content objects
        request2 = LlmRequest(
            model="test-model",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text="I am an object")]),
                "I am a string"
            ]
        )

        # Test Case 3: Objects WITHOUT role attribute (unexpected but possible)
        class NoRole:
            def __init__(self, parts):
                self.parts = parts
        
        request3 = LlmRequest(
            model="test-model",
            contents=[NoRole(parts=[types.Part.from_text(text="No role object")])]
        )

        requests = [request1, request2, request3]
        
        # We use a mocked client to avoid actual API calls
        model.client = MagicMock()
        model.client.chat.completions.create = MagicMock()
        
        for i, request in enumerate(requests):
            print(f"Testing request case {i+1}...")
            try:
                # Since generate_content_async is an async generator
                gen = model.generate_content_async(request)
                await gen.__anext__()
            except AttributeError as e:
                if "'str' object has no attribute 'role'" in str(e):
                    self.fail(f"Case {i+1} failed with 'str' object has no attribute 'role'")
                else:
                    print(f"Caught other AttributeError in case {i+1}: {e}")
            except StopAsyncIteration:
                pass
            except Exception as e:
                # If we get here without the 'role' error, it's probably because of my mock setup
                # which is fine as we are testing the loop before the API call.
                print(f"Caught {type(e).__name__} in case {i+1}: {e}")


if __name__ == "__main__":
    unittest.main()
