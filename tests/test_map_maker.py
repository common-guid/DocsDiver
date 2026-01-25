import pytest
from sdaa.src.core.map_maker import generate_toc
import os
import json

@pytest.mark.asyncio
async def test_generate_toc():
    # Run async function
    await generate_toc()

    # Check ToC.json exists
    toc_path = "ToC.json" # Based on config default
    assert os.path.exists(toc_path)

    with open(toc_path) as f:
        data = json.load(f)
        assert "files" in data
        assert len(data["files"]) > 0

        # Verify summary and tags format (MockModel logic)
        first = data["files"][0]
        assert "path" in first
        assert "summary" in first
        assert "tags" in first
        assert isinstance(first["tags"], list)
        assert len(first["tags"]) == 3
        assert all(isinstance(t, str) for t in first["tags"])
        # MockModel returns mock summary or logic based on content
