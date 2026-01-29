import os
from typing import List, Type
from pydantic import BaseModel, Field
from src.bootstrap_env import init_env

init_env()

from crewai.tools import BaseTool

# --- 1. List Files Tool ---
class ListFilesToolInput(BaseModel):
    directory: str = Field(..., description="The absolute or relative path to the directory to list files from.")

class ListFilesTool(BaseTool):
    name: str = "List Markdown Files"
    description: str = (
        "Recursively lists all file paths ending in .md in a given directory. "
        "Useful for discovering the documentation structure before reading specific files."
    )
    args_schema: Type[BaseModel] = ListFilesToolInput

    def _run(self, directory: str) -> List[str]:
        md_files = []
        if not os.path.exists(directory):
            return [f"Error: Directory '{directory}' does not exist."]

        for root, dirs, files in os.walk(directory):
            for file in files:
                # CONSTRAINT CHECK: Strict .md only
                if file.endswith(".md"):
                    full_path = os.path.join(root, file)
                    md_files.append(full_path)

        return md_files if md_files else [f"No .md files found in {directory}"]

# --- 2. Read File Tool ---
class ReadFileToolInput(BaseModel):
    file_path: str = Field(..., description="The full path of the markdown file to read.")

class ReadFileTool(BaseTool):
    name: str = "Read Markdown File"
    description: str = (
        "Reads the complete content of a specified markdown file. "
        "Use this to analyze the full context of a document found via ListFiles."
    )
    args_schema: Type[BaseModel] = ReadFileToolInput

    def _run(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' not found."

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

# --- 3. Search Files Tool (Context-Aware) ---
class SearchFilesToolInput(BaseModel):
    query: str = Field(..., description="The keyword or phrase to search for.")
    directory: str = Field(..., description="The directory to search within.")

class SearchFilesTool(BaseTool):
    name: str = "Search Files with Context"
    description: str = (
        "Searches for a keyword across all .md files in a directory. "
        "Returns the file path, line number, and a snippet of text (3 lines before and after) "
        "to provide context for the match."
    )
    args_schema: Type[BaseModel] = SearchFilesToolInput

    def _run(self, query: str, directory: str) -> str:
        results = []
        if not os.path.exists(directory):
            return f"Error: Directory '{directory}' does not exist."

        # CONSTRAINT CHECK: Simple text search (no regex)
        query_lower = query.lower()

        for root, dirs, files in os.walk(directory):
            for file in files:
                # CONSTRAINT CHECK: Strict .md only
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()

                        for i, line in enumerate(lines):
                            if query_lower in line.lower():
                                # LOGIC: Capture 3 lines before and 4 lines after (slice exclusive)
                                start_index = max(0, i - 3)
                                end_index = min(len(lines), i + 4)

                                snippet_lines = []
                                for j in range(start_index, end_index):
                                    # Visual marker for the exact match line
                                    prefix = ">> " if j == i else "   "
                                    snippet_lines.append(f"{prefix}Line {j+1}: {lines[j].strip()}")

                                snippet_block = "\n".join(snippet_lines)

                                results.append(
                                    f"Found in: {file_path}\n"
                                    f"Context:\n{snippet_block}\n"
                                    f"{'-'*40}"
                                )
                    except Exception as e:
                        results.append(f"Could not read {file_path}: {str(e)}")

        if not results:
            return f"No matches found for '{query}' in {directory}."

        return "\n\n".join(results)
