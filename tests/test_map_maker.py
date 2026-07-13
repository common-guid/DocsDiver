import pytest
from sdaa.src.core.map_maker import generate_toc
from sdaa.src.core.config_loader import config_loader
import os
import json

@pytest.mark.asyncio
async def test_generate_toc():
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = config_loader.get_output_dir()
    toc_path = os.path.join(output_dir, toc_filename)

    # Ensure pre-existing ToC does not cause the skip guard to bypass generation
    if os.path.exists(toc_path):
        os.remove(toc_path)

    # Run async function
    await generate_toc(model_name="mock")

    # Check ToC.json exists at the resolved output path
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
