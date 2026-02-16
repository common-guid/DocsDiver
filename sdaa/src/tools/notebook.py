import json
import os
import datetime
from typing import Optional, Dict, List, Any
from sdaa.src.core.config_loader import config_loader

def _get_notebook_dir() -> str:
    """Returns the absolute path to the notebook directory."""
    output_dir = config_loader.get_output_dir()
    notebook_dirname = config_loader.get("system.notebook_dir", "notebook")
    notebook_dir = os.path.join(output_dir, notebook_dirname)
    os.makedirs(notebook_dir, exist_ok=True)
    return notebook_dir

def _get_notebook_path(category: str) -> str:
    """Returns the path for a specific category notebook file."""
    notebook_dir = _get_notebook_dir()
    # Sanitize category to prevent path traversal
    safe_category = "".join([c for c in category if c.isalnum() or c in ('-', '_')])
    return os.path.join(notebook_dir, f"{safe_category}.json")

def append_to_notebook(category: str, content: str) -> str:
    """
    Appends a finding to the specified category notebook.

    Args:
        category: The category of findings (e.g., 'permissions', 'constraints').
        content: The content of the finding (markdown or text).

    Returns:
        A confirmation message.
    """
    try:
        file_path = _get_notebook_path(category)

        # Load existing data or initialize
        data = {"findings": []}
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                pass # Start fresh if corrupt

        # Append new finding
        finding = {
            "timestamp": datetime.datetime.now().isoformat(),
            "content": content
        }
        data["findings"].append(finding)

        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return f"Successfully appended finding to notebook '{category}'."
    except Exception as e:
        return f"Error appending to notebook: {str(e)}"

def read_notebook(category: str = None) -> str:
    """
    Reads findings from the notebook.

    Args:
        category: If provided, reads only that category. If None, reads all notebooks.

    Returns:
        A string representation of the findings (JSON or text summary).
    """
    notebook_dir = _get_notebook_dir()

    if category:
        file_path = _get_notebook_path(category)
        if not os.path.exists(file_path):
            return f"Notebook '{category}' is empty or does not exist."
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return json.dumps(data, indent=2)
        except Exception as e:
            return f"Error reading notebook '{category}': {str(e)}"

    # Read all categories
    all_findings = {}
    try:
        for filename in os.listdir(notebook_dir):
            if filename.endswith(".json"):
                cat = filename[:-5] # remove .json
                file_path = os.path.join(notebook_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        all_findings[cat] = data.get("findings", [])
                    except json.JSONDecodeError:
                        all_findings[cat] = "Error: Corrupt file"
        return json.dumps(all_findings, indent=2)
    except Exception as e:
        return f"Error reading notebooks: {str(e)}"

def clear_notebook(category: str = None) -> str:
    """
    Clears the notebook.

    Args:
        category: If provided, clears only that category. If None, clears all notebooks.

    Returns:
        Confirmation message.
    """
    notebook_dir = _get_notebook_dir()

    try:
        if category:
            file_path = _get_notebook_path(category)
            if os.path.exists(file_path):
                os.remove(file_path)
            return f"Cleared notebook '{category}'."

        # Clear all
        if os.path.exists(notebook_dir):
            for filename in os.listdir(notebook_dir):
                if filename.endswith(".json"):
                    os.remove(os.path.join(notebook_dir, filename))
        return "Cleared all notebooks."
    except Exception as e:
        return f"Error clearing notebook: {str(e)}"
