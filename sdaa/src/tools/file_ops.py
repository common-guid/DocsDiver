import os
from sdaa.src.core.config_loader import config_loader

def _get_docs_root():
    return os.path.abspath(config_loader.get("system.docs_root", "./docs"))

def read_file(file_path: str) -> str:
    """
    Reads the content of a file.
    Args:
        file_path: Path to the file, relative to the docs root.
    Returns:
        The content of the file.
    Raises:
        ValueError: If the file path is outside the docs root.
        FileNotFoundError: If the file does not exist.
    """
    docs_root = _get_docs_root()
    # Handle absolute paths if they start with docs_root, otherwise treat as relative
    if os.path.isabs(file_path):
        full_path = os.path.abspath(file_path)
    else:
        full_path = os.path.abspath(os.path.join(docs_root, file_path))

    if not full_path.startswith(docs_root):
        raise ValueError(f"Access denied: {file_path} is outside the documentation root.")

    if not os.path.exists(full_path):
        return f"Error: File not found: {file_path}"

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(directory_path: str = ".") -> str:
    """
    Lists files in a directory.
    Args:
        directory_path: Path to the directory, relative to the docs root. Defaults to root.
    Returns:
        A list of file paths relative to the docs root.
    """
    docs_root = _get_docs_root()

    if os.path.isabs(directory_path):
        full_path = os.path.abspath(directory_path)
    else:
        full_path = os.path.abspath(os.path.join(docs_root, directory_path))

    if not full_path.startswith(docs_root):
        raise ValueError(f"Access denied: {directory_path} is outside the documentation root.")

    if not os.path.exists(full_path):
        return f"Error: Directory not found: {directory_path}"

    file_list = []
    for root, dirs, files in os.walk(full_path):
        for file in files:
            if file.endswith('.md'): # Only list markdown files as per plan implication
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, docs_root)
                file_list.append(rel_path)

    return "\n".join(file_list)
