from typing import List, Dict, Union, Any
from pydantic import BaseModel
import os
import json
from sdaa.src.core.config_loader import config_loader

class TestCase(BaseModel):
    id: str
    category: str
    scenario: str
    source_agent: str
    risk: str

class AuthMatrixEntry(BaseModel):
    role: str
    resource: str
    permission: str

class PermissionIssue(BaseModel):
    issue: str
    severity: str

class Vulnerability(BaseModel):
    name: str
    description: str
    severity: str

# Tools

def ensure_output_dirs():
    """Ensure all output directories exist."""
    config_loader.get_output_dir()
    config_loader.get_reports_dir()
    config_loader.get_artifacts_dir()

def generate_final_report(report_content: str) -> str:
    """
    Saves the final Master Audit Report under the configured output directory
    as Security_Threat_Model.md.

    Args:
        report_content: The full markdown content of the report.
    Returns:
        Status message.
    """
    try:
        reports_dir = config_loader.get_reports_dir()
        filepath = os.path.join(reports_dir, "Security_Threat_Model.md")
        filepath = os.path.abspath(filepath)
        with open(filepath, "w", encoding='utf-8') as f:
            f.write(report_content)
        return f"Report saved successfully to {filepath}."
    except Exception as e:
        return f"Error saving report: {str(e)}"

def report_permissions_matrix(findings: str) -> str:
    """
    Logs the permissions matrix findings and saves to artifact file.
    Args:
        findings: Markdown or text description of findings.
    """
    try:
        artifacts_dir = config_loader.get_artifacts_dir()
        filepath = os.path.join(artifacts_dir, "permissions_agent.md")
        with open(filepath, "w", encoding='utf-8') as f:
            f.write(findings)
        return f"Permissions findings recorded and saved to {filepath}."
    except Exception as e:
        return f"Error saving permissions findings: {str(e)}"

def report_invariance_findings(findings: str) -> str:
    """
    Logs the invariance/logic findings and saves to artifact file.
    Args:
        findings: Markdown or text description.
    """
    try:
        artifacts_dir = config_loader.get_artifacts_dir()
        filepath = os.path.join(artifacts_dir, "constraints_agent.md")
        with open(filepath, "w", encoding='utf-8') as f:
            f.write(findings)
        return f"Invariance findings recorded and saved to {filepath}."
    except Exception as e:
        return f"Error saving invariance findings: {str(e)}"

def report_boundary_analysis(boundaries: Union[List[Dict[str, Any]], str]) -> str:
    """
    Logs the boundary analysis findings and saves to artifact file.
    Args:
        boundaries: List of boundary objects or a markdown string.
    """
    try:
        artifacts_dir = config_loader.get_artifacts_dir()
        filepath = os.path.join(artifacts_dir, "boundaries_agent.md")

        content = ""
        if isinstance(boundaries, str):
            content = boundaries
        else:
            # Convert list of dicts to a JSON block in Markdown
            json_str = json.dumps({"boundaries": boundaries}, indent=2)
            content = f"```json\n{json_str}\n```"

        with open(filepath, "w", encoding='utf-8') as f:
            f.write(content)

        count = len(boundaries) if isinstance(boundaries, list) else "N/A"
        return f"Recorded boundary analysis ({count} items) and saved to {filepath}."
    except Exception as e:
        return f"Error saving boundary analysis: {str(e)}"
