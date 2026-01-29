import os
import sys
import json
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.bootstrap_env import init_env

init_env()

from litellm import completion
from src.config.model_config import get_librarian_model

class ToCGenerator:
    def __init__(self, root_dir: str, model_name: str | None = None, output_path: str | None = None):
        self.root_dir = root_dir
        self.model_name = model_name or get_librarian_model()
        self.output_path = output_path or "ToC.json"
        self.toc_data: List[Dict] = []

    def _get_files(self) -> List[str]:
        """Recursively find all .md files."""
        md_files = []
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith(".md"):
                    md_files.append(os.path.join(root, file))
        return md_files

    def _generate_summary(self, file_path: str, content: str) -> Dict:
        """Calls Gemini 2 Flash to summarize the content."""

        prompt = f"""
        You are a Technical Librarian. Analyze the following documentation file.

        FILE PATH: {file_path}

        CONTENT:
        {content[:4000]}  # Truncate to first 4k chars to save tokens/time if files are huge

        ---
        Your Goal:
        1. Write a 1-sentence summary of what this file covers.
        2. Assign 2-5 relevant tags (e.g., "auth", "payment", "user-input", "logging").

        Return strictly JSON in this format:
        {{
            "summary": "The summary text here.",
            "tags": ["tag1", "tag2"]
        }}
        """

        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1 # Low temp for consistent JSON
            )

            content_str = response.choices[0].message.content

            # Clean up potential markdown formatting (```json ... ```)
            content_str = content_str.replace("```json", "").replace("```", "").strip()

            data = json.loads(content_str)
            return data
        except Exception as e:
            print(f"xx Failed to process {file_path}: {e}")
            return {"summary": "Error processing file.", "tags": ["error"]}

    def generate(self):
        print(f"📚 Librarian starting scan of: {self.root_dir}")
        print(f"🤖 Using Model: {self.model_name}")

        files = self._get_files()
        print(f"found {len(files)} markdown files.")

        for file_path in files:
            print(f"   ... processing: {os.path.basename(file_path)}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                meta = self._generate_summary(file_path, content)

                # Append to Master Record
                self.toc_data.append({
                    "file": os.path.basename(file_path),
                    "path": file_path,
                    "summary": meta.get("summary", "No summary"),
                    "tags": meta.get("tags", [])
                })
            except Exception as e:
                print(f"xx Critical error reading {file_path}: {e}")

        # Save to Disk
        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.toc_data, f, indent=2)

        print(f"✅ ToC generated! Saved to {output_path}")

# Standalone execution for testing
if __name__ == "__main__":
    # Ensure GEMINI_API_KEY is set in your environment
    generator = ToCGenerator(root_dir="./docs") # Default to ./docs
    generator.generate()
