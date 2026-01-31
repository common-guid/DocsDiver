import json
import asyncio
import os
import re
from typing import List, Tuple
from sdaa.src.tools.file_ops import list_files, read_file
from sdaa.src.core.config_loader import config_loader
from sdaa.src.utils.mock_model import MockModel
from google.adk.models import LlmRequest
from google.genai import types


def _derive_tags_from_path(filepath: str) -> List[str]:
    """Fallback tag generator based on file path.

    Uses directory and filename segments to produce up to three
    short, lowercase keyword tags. Ensures exactly three tags by
    truncating or padding with the last available token.
    """
    path = filepath.replace("\\", "/")
    segments = [seg for seg in path.split("/") if seg and not seg.startswith(".")]

    candidates: List[str] = []
    # Focus on the most specific parts: last two path segments
    for seg in segments[-2:]:
        base, _ext = os.path.splitext(seg)
        for token in re.split(r"[^a-zA-Z0-9]+", base):
            token = token.strip().lower()
            if token and token not in candidates:
                candidates.append(token)

    if not candidates:
        candidates = ["docs"]

    # Ensure exactly three tags
    while len(candidates) < 3:
        candidates.append(candidates[-1])

    return candidates[:3]


def _normalize_tags(raw_tags, filepath: str) -> List[str]:
    """Normalize tags from model output and ensure exactly three.

    - Accepts any iterable of strings.
    - Lowercases, strips, and de-duplicates.
    - Falls back to path-derived tags if none are usable.
    """
    tags: List[str] = []

    if isinstance(raw_tags, list):
        for t in raw_tags:
            if not isinstance(t, str):
                continue
            token = t.strip().lower()
            if token and token not in tags:
                tags.append(token)

    if not tags:
        tags = _derive_tags_from_path(filepath)
    else:
        while len(tags) < 3:
            tags.append(tags[-1])
        tags = tags[:3]

    return tags


async def _summarize_file(filepath: str, model) -> Tuple[str, List[str]]:
    """Generate a summary and tags for a single file.

    The model is prompted to return JSON of the form:
    {"summary": "...", "tags": ["tag1", "tag2", "tag3"]}.
    If the response is not valid JSON, we fall back to using the raw
    text as the summary and derive tags from the file path.
    """
    try:
        content = read_file(filepath)
    except Exception as e:
        # On read error, encode message as summary and derive tags from path
        return f"Error reading file: {e}", _derive_tags_from_path(filepath)

    prompt = (
        "You are helping build a navigation map for a documentation corpus.\n"
        "Read the following content and:\n"
        "1. Provide a one-sentence architectural summary.\n"
        "2. Provide exactly three short, lowercase keyword tags related to the file's subject.\n\n"
        "Return ONLY valid JSON of the form:\n"
        "{\n"
        "  \"summary\": \"<one sentence>\",\n"
        "  \"tags\": [\"tag1\", \"tag2\", \"tag3\"]\n"
        "}\n\n"
        f"Content:\n{content}"
    )

    # Determine model name dynamically
    model_name = getattr(model, "model", None)
    if not model_name:
         model_name = getattr(model, "model_name", "mock-model")

    # Create request
    request = LlmRequest(
        model=model_name,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    )

    response_text = ""
    async for response in model.generate_content_async(request):
        if response.content and response.content.parts:
            for part in response.content.parts:
                if part.text:
                    response_text += part.text

    summary: str
    tags: List[str]

    # The mock model returns JSON-like string for 'architectural summary'.
    # Real models are instructed to return JSON with summary and tags.
    try:
        data = json.loads(response_text)
        summary = str(data.get("summary", "")).strip() or response_text.strip()
        tags = _normalize_tags(data.get("tags"), filepath)
    except json.JSONDecodeError:
        summary = response_text.strip() or "No summary available."
        tags = _derive_tags_from_path(filepath)

    return summary, tags

async def generate_toc(model=None):
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = config_loader.get_output_dir()
    toc_path = os.path.join(output_dir, toc_filename)

    # Optional guard so direct calls behave consistently with CLI behavior.
    if os.path.exists(toc_path):
        print(f"{toc_filename} already exists at {toc_path}. Skipping ToC generation.")
        return

    print(f"Generating {toc_filename} at {toc_path}...")

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

    # Initialize model
    if model is None:
        # Using MockModel as fallback
        model = MockModel(model="mock-model")

    for file in file_list:
        summary, tags = await _summarize_file(file, model)
        toc_entries.append({"path": file, "summary": summary, "tags": tags})

    toc_data = {"files": toc_entries}

    try:
        with open(toc_path, 'w') as f:
            json.dump(toc_data, f, indent=2)
        print(f"{toc_filename} generated with {len(toc_entries)} entries at {toc_path}.")
    except Exception as e:
        print(f"Error writing ToC file: {e}")

if __name__ == "__main__":
    asyncio.run(generate_toc())
