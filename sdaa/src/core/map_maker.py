import json
import asyncio
import os
import re
from typing import List, Tuple
from sdaa.src.tools.file_ops import list_files, read_file
from sdaa.src.core.config_loader import config_loader
from google.antigravity import Agent, LocalAgentConfig


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


async def _summarize_file(filepath: str, model_name: str = None) -> Tuple[str, List[str]]:
    """Generate a summary and tags for a single file.

    The model is prompted to return JSON of the form:
    {"summary": "...", "tags": ["tag1", "tag2", "tag3"]}.
    If the response is not valid JSON, we attempt to extract JSON from markdown
    code blocks before falling back to using the raw text as the summary.
    """
    try:
        content = read_file(filepath)
    except Exception as e:
        # On read error, encode message as summary and derive tags from path
        return f"Error reading file: {e}", _derive_tags_from_path(filepath)

    if model_name == "mock" or model_name == "mock-model":
        return f"Mock architectural summary for {filepath}", _derive_tags_from_path(filepath)

    prompt = (
        "You are helping build a navigation map for a documentation corpus.\n"
        "Read the following content and:\n"
        "1. Provide a one-sentence architectural summary.\n"
        "2. Provide exactly three short, lowercase keyword tags that are descriptive of the file's subject. These keyword tags must be nouns or adjectives, and must not be duplicated.\n\n"
        "Return ONLY valid JSON. Do not include any other text before or after the JSON.\n"
        "{\n"
        "  \"summary\": \"<one sentence>\",\n"
        "  \"tags\": [\"tag1\", \"tag2\", \"tag3\"]\n"
        "}\n\n"
        f"Content:\n{content}"
    )

    config = LocalAgentConfig(
        system_instructions="You are helping build a navigation map for a documentation corpus. Return ONLY valid JSON.",
        model=model_name
    )

    response_text = ""
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        async for token in response:
            response_text += token

    summary: str
    tags: List[str]

    # Attempt to parse as JSON.
    # Some models might wrap JSON in markdown blocks like ```json ... ```.
    # We prioritize content within code blocks if they exist.
    clean_text = response_text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean_text, re.DOTALL)
    if match:
        clean_text = match.group(1).strip()

    try:
        data = json.loads(clean_text)
        summary = str(data.get("summary", "")).strip() or clean_text
        tags = _normalize_tags(data.get("tags"), filepath)
    except json.JSONDecodeError:
        summary = response_text.strip() or "No summary available."
        tags = _derive_tags_from_path(filepath)

    return summary, tags

async def generate_toc(model_name: str = None):
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

    total_files = len(file_list)
    for i, file in enumerate(file_list, 1):
        print(f"[{i}/{total_files}] Processing {file}...")
        summary, tags = await _summarize_file(file, model_name)
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
