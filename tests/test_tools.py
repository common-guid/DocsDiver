import pytest
from sdaa.src.tools.file_ops import read_file, list_files

def test_read_file_safe():
    # Setup docs-for-testing/auth.md exists
    content = read_file("auth.md")
    assert "Authentication" in content

def test_read_file_traversal():
    with pytest.raises(ValueError):
        read_file("../requirements.txt")

def test_list_files():
    files = list_files()
    assert "auth.md" in files
    assert "billing.md" in files
