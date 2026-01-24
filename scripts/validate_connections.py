import os
import asyncio
import sys
from google import genai
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load .env
load_dotenv()

async def test_gemini():
    print("\n--- Testing Gemini Connection ---")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("FAIL: GEMINI_API_KEY not found in environment.")
        return False

    try:
        client = genai.Client(api_key=api_key)
        # Try listing models as a connectivity test
        # Note: client.models.list() returns an iterator
        models_iter = client.models.list()
        # Consume a few to verify
        count = 0
        for _ in models_iter:
            count += 1
            if count >= 5: break

        print(f"SUCCESS: Connected to Gemini API. Model list access confirmed.")
        return True
    except Exception as e:
        print(f"FAIL: Gemini connection failed: {e}")
        return False

async def test_openrouter():
    print("\n--- Testing OpenRouter Connection ---")
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = "https://openrouter.ai/api/v1"

    if not api_key:
        print("FAIL: OPENROUTER_API_KEY not found in environment.")
        return False

    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    try:
        # Simple test: list models
        models = await client.models.list()
        print(f"SUCCESS: Connected to OpenRouter API. Found {len(models.data)} models.")
        return True
    except Exception as e:
        print(f"FAIL: OpenRouter connection failed: {e}")
        return False

async def main():
    print("Starting API Connection Validation...")

    gemini_ok = await test_gemini()
    openrouter_ok = await test_openrouter()

    if gemini_ok and openrouter_ok:
        print("\nAll API connections validated successfully.")
        sys.exit(0)
    else:
        print("\nSome API connections failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
