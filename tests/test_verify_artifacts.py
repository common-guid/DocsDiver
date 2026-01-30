import os
import shutil
import pytest
import json
from sdaa.src.tools.reporting import (
    generate_final_report,
    report_permissions_matrix,
    report_invariance_findings,
    report_boundary_analysis,
    ensure_output_dirs
)
from sdaa.src.core.map_maker import generate_toc
from sdaa.src.core.config_loader import config_loader

# Define output directories for testing
TEST_OUTPUT_DIR = "test_output_artifacts"
TEST_REPORTS_DIR = os.path.join(TEST_OUTPUT_DIR, "reports")
TEST_ARTIFACTS_DIR = os.path.join(TEST_OUTPUT_DIR, "artifacts")
TOC_FILENAME = "ToC.json"

@pytest.fixture
def setup_teardown():
    # Setup: override config to use test output dir
    original_output_dir = config_loader._config.get("system", {}).get("output_dir")

    # Inject test configuration
    if "system" not in config_loader._config:
        config_loader._config["system"] = {}
    config_loader._config["system"]["output_dir"] = TEST_OUTPUT_DIR

    # Clean up before test
    if os.path.exists(TEST_OUTPUT_DIR):
        shutil.rmtree(TEST_OUTPUT_DIR)

    yield

    # Teardown: Restore config and clean up
    if original_output_dir:
        config_loader._config["system"]["output_dir"] = original_output_dir
    else:
        del config_loader._config["system"]["output_dir"]

    if os.path.exists(TEST_OUTPUT_DIR):
        shutil.rmtree(TEST_OUTPUT_DIR)

@pytest.mark.asyncio
async def test_verify_librarian_toc_generation(setup_teardown):
    """Verify Librarian writes ToC.json to $output_dir/$toc_filename"""
    await generate_toc()

    toc_path = os.path.join(TEST_OUTPUT_DIR, TOC_FILENAME)
    assert os.path.exists(toc_path), f"Librarian failed to write {TOC_FILENAME} to {TEST_OUTPUT_DIR}"

    with open(toc_path, 'r') as f:
        data = json.load(f)
        assert "files" in data

def test_verify_workers_artifacts_generation(setup_teardown):
    """Verify Workers write artifacts to $output_dir/$artifacts_dir"""
    ensure_output_dirs()

    # Permissions Agent
    report_permissions_matrix("# Permissions")
    perm_path = os.path.join(TEST_ARTIFACTS_DIR, "permissions_agent.md")
    assert os.path.exists(perm_path), "Permissions agent failed to write artifact"

    # Constraints Agent
    report_invariance_findings("# Constraints")
    const_path = os.path.join(TEST_ARTIFACTS_DIR, "constraints_agent.md")
    assert os.path.exists(const_path), "Constraints agent failed to write artifact"

    # Boundaries Agent
    report_boundary_analysis("# Boundaries\n```json\n[]\n```")
    bound_path = os.path.join(TEST_ARTIFACTS_DIR, "boundaries_agent.md")
    assert os.path.exists(bound_path), "Boundaries agent failed to write artifact"

def test_verify_supervisor_report_generation(setup_teardown):
    """Verify Supervisor writes final report to $output_dir/$reports_dir"""
    ensure_output_dirs()

    generate_final_report("# Final Report")
    report_path = os.path.join(TEST_REPORTS_DIR, "Security_Threat_Model.md")
    assert os.path.exists(report_path), "Supervisor failed to write final report"
