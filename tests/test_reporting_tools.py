import os
import shutil
import pytest
from sdaa.src.tools.reporting import (
    generate_final_report,
    report_permissions_matrix,
    report_invariance_findings,
    report_boundary_analysis,
    ensure_output_dirs
)
from sdaa.src.core.config_loader import config_loader

# Ensure clean state
OUTPUT_DIR = "output"
REPORTS_DIR = "output/reports"
ARTIFACTS_DIR = "output/artifacts"

def setup_module(module):
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    # Re-create ToC.json if needed by other things, but here we focus on reports

def teardown_module(module):
    # Optional: cleanup
    pass

def test_ensure_output_dirs():
    ensure_output_dirs()
    assert os.path.exists(OUTPUT_DIR)
    assert os.path.exists(REPORTS_DIR)
    assert os.path.exists(ARTIFACTS_DIR)

def test_generate_final_report():
    ensure_output_dirs()
    content = "# Master Report"
    result = generate_final_report(content)
    assert "saved successfully" in result

    filepath = os.path.join(REPORTS_DIR, "Security_Threat_Model.md")
    assert os.path.exists(filepath)
    with open(filepath, "r") as f:
        assert f.read() == content

def test_report_permissions_matrix():
    ensure_output_dirs()
    content = "# Permissions Matrix"
    result = report_permissions_matrix(content)
    assert "saved" in result

    filepath = os.path.join(ARTIFACTS_DIR, "permissions_agent.md")
    assert os.path.exists(filepath)
    with open(filepath, "r") as f:
        assert f.read() == content

def test_report_invariance_findings():
    ensure_output_dirs()
    content = "# Invariance Findings"
    result = report_invariance_findings(content)
    assert "saved" in result

    filepath = os.path.join(ARTIFACTS_DIR, "constraints_agent.md")
    assert os.path.exists(filepath)
    with open(filepath, "r") as f:
        assert f.read() == content


def test_report_boundary_analysis_str():
    ensure_output_dirs()
    markdown_content = "# Boundaries\n```json\n[]\n```"
    result = report_boundary_analysis(markdown_content)
    assert "saved" in result

    filepath = os.path.join(ARTIFACTS_DIR, "boundaries_agent.md")
    assert os.path.exists(filepath)
    with open(filepath, "r") as f:
        assert f.read() == markdown_content

if __name__ == "__main__":
    # Manual run if pytest not installed
    try:
        setup_module(None)
        test_ensure_output_dirs()
        test_generate_final_report()
        test_report_permissions_matrix()
        test_report_invariance_findings()
        test_report_boundary_analysis_str()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
