import json
import asyncio
import os
from sdaa.src.tools.file_ops import list_files, read_file
from sdaa.src.core.config_loader import config_loader
from sdaa.src.utils.mock_model import MockModel
from google.adk.models import LlmRequest
from google.genai import types

async def _summarize_file(filepath: str, model) -> str:
    try:
        content = read_file(filepath)
    except Exception as e:
        return f"Error reading file: {e}"

    prompt = f"Read the following content and provide a one-sentence architectural summary.\n\n{content}"

    # Create request
    model_name = getattr(model, "model_name", "model")
    request = LlmRequest(
        model=model_name,
        contents=[types.Content(parts=[types.Part.from_text(text=prompt)])]
    )

    response_text = ""
    async for response in model.generate_content_async(request):
        if response.content and response.content.parts:
            for part in response.content.parts:
                if part.text:
                    response_text += part.text

    # The mock model returns JSON-like string for 'architectural summary'
    # Real models might just return text.
    try:
        data = json.loads(response_text)
        if isinstance(data, dict):
            return data.get("summary", response_text)
        return response_text.strip()
    except json.JSONDecodeError:
        return response_text.strip()

async def generate_toc(model=None):
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    print(f"Generating {toc_filename}...")

    try:
        files_output = list_files()
    except Exception as e:
        print(f"Error listing files: {e}")
        return

    if not files_output or files_output.startswith("Error"):
        print(f"No files found or error: {files_output}")
        file_list = []
    else:
        file_list = files_output.splitlines()

    toc_entries = []

    # Initialize model if not provided
    if model is None:
        model = MockModel(model="mock-model")

    for file in file_list:
        summary = await _summarize_file(file, model)
        toc_entries.append({"path": file, "summary": summary})

    toc_data = {"files": toc_entries}

    try:
        with open(toc_filename, 'w') as f:
            json.dump(toc_data, f, indent=2)
        print(f"{toc_filename} generated with {len(toc_entries)} entries.")
    except Exception as e:
        print(f"Error writing ToC file: {e}")

if __name__ == "__main__":
    asyncio.run(generate_toc())
