from typing import AsyncGenerator, Optional
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types

class MockModel(BaseLlm):
    model: str = "mock-model"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:

        contents_text = str(llm_request.contents).lower()
        system_text = str(llm_request.config.system_instruction).lower() if llm_request.config and llm_request.config.system_instruction else ""
        full_text = contents_text + system_text
        
        # Debug: Print tool structure to understand what LlmAgent passes
        if llm_request.config and hasattr(llm_request.config, 'tools'):
            print(f"DEBUG: Tools in config: {llm_request.config.tools}")


        # Check if the last part of the last content is a FunctionResponse
        # If so, we have already called the tool, so now we should return the final text (step 6).
        last_was_function_response = False
        if llm_request.contents:
            last_content = llm_request.contents[-1]
            if hasattr(last_content, 'parts'):
                for part in last_content.parts:
                    if hasattr(part, 'function_response') and part.function_response:
                        last_was_function_response = True
                        break

        response_text = "Mock response"
        tool_call_part = None

        # Simple heuristic to determine response based on prompt content
        
        # Check for specific agent roles FIRST to avoid false positives
        if "principal security architect" in full_text:
             report_content = """
# Master Audit Report

## 1. Executive Summary
The application has good documentation but some gaps in RBAC.

## 2. Architecture & Trust Model
Standard 3-tier web app with public login and internal database.

## 3. Key Findings & Risks
*   **Contradictions:** None found.
*   **Missing Controls:** API rate limiting not mentioned.
*   **Critical Logic Flaws:** Debug mode checks.

## 4. Master Test Plan (Consolidated)

| ID | Category | Test Scenario | Source Agent | Risk |
|:---|:---|:---|:---|:---|
| TEST-01 | AuthZ | Edit other user profile | RBAC | High |
| LOGIC-01 | Logic | Enable debug in prod | Logic | Medium |
| BND-01 | Network | Attack Login API | Boundary | High |
"""
             if not last_was_function_response:
                 # Call generate_final_report manually since we are mocking
                 # and ignoring the complex tool-id dance.
                 from sdaa.src.core.config_loader import config_loader
                 import os
                 reports_dir = config_loader.get_reports_dir()
                 filepath = os.path.join(reports_dir, "Security_Threat_Model.md")
                 with open(filepath, "w", encoding='utf-8') as f:
                     f.write(report_content)
                 response_text = f"Report saved successfully to {filepath}."
             else:
                 response_text = report_content

        elif ("role based access controls" in full_text or "permissions analyst" in full_text):
             # Permissions Agent
             findings = """
# RBAC Analysis
## 1. Analysis Summary
Analyzed files: auth.md
## 2. Threat Hierarchy
- IDOR
- Privilege Escalation
## 3. Findings
- Missing explicit admin checks in user update.
## 4. Test Cases
| ID | Category | Scenario | Risk |
|:---|:---|:---|:---|
| TEST-01 | AuthZ | Edit other user profile | High |
"""
             if not last_was_function_response:
                 from sdaa.src.core.config_loader import config_loader
                 import os
                 artifacts_dir = config_loader.get_artifacts_dir()
                 filepath = os.path.join(artifacts_dir, "permissions_agent.md")
                 with open(filepath, "w", encoding='utf-8') as f:
                     f.write(findings)
                 response_text = f"Permissions findings recorded and saved to {filepath}."
             else:
                 response_text = findings

        elif ("business logic" in full_text or "negative constraints" in full_text):
             # Constraints Agent
             findings = """
# Logic Analysis
## 1. Analysis Summary
Analyzed files: billing.md
## 2. Configuration Risks
| Feature | Claim | Test Case |
|:---|:---|:---|
| Debug Mode | Must be off in prod | Enable debug in prod |
"""
             if not last_was_function_response:
                 from sdaa.src.core.config_loader import config_loader
                 import os
                 artifacts_dir = config_loader.get_artifacts_dir()
                 filepath = os.path.join(artifacts_dir, "constraints_agent.md")
                 with open(filepath, "w", encoding='utf-8') as f:
                     f.write(findings)
                 response_text = f"Invariance findings recorded and saved to {filepath}."
             else:
                 response_text = findings

        elif ("security boundary" in full_text or "data flow component" in full_text):
             # Boundaries Agent
             boundaries_markdown = """
{
  "boundaries": [
    {
      "name": "Login API",
      "type": "Ingress",
      "trust_zone_source": "Public",
      "trust_zone_destination": "Internal",
      "description": "User login endpoint",
      "risk_level": "High"
    }
  ]
}
"""
             if not last_was_function_response:
                 from sdaa.src.core.config_loader import config_loader
                 import os
                 artifacts_dir = config_loader.get_artifacts_dir()
                 filepath = os.path.join(artifacts_dir, "boundaries_agent.md")
                 with open(filepath, "w", encoding='utf-8') as f:
                     f.write(boundaries_markdown)
                 response_text = f"Recorded boundary analysis and saved to {filepath}."
             else:
                 response_text = boundaries_markdown

        elif "architectural summary" in full_text and not last_was_function_response:
             # Map Maker - checking this LAST because other prompts might contain this phrase
             # It acts as a fallback or specific check if no other role matched
             response_text = '{"summary": "This is a mock summary of the architectural component."}'

        # Wrap response in types.Content
        if tool_call_part:
            content = types.Content(parts=[tool_call_part])
        else:
            content = types.Content(parts=[types.Part.from_text(text=response_text)])
        
        yield LlmResponse(content=content)
