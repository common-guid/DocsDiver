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

        response_text = "Mock response"

        # Simple heuristic to determine response based on prompt content
        if "architectural summary" in full_text:
             response_text = '{"summary": "This is a mock summary of the architectural component."}'

        elif "principal security architect" in full_text:
             response_text = """
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
        elif "role based access controls" in full_text or "permissions analyst" in full_text:
             response_text = """
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
        elif "business logic" in full_text or "negative constraints" in full_text:
             response_text = """
# Logic Analysis
## 1. Analysis Summary
Analyzed files: billing.md
## 2. Configuration Risks
| Feature | Claim | Test Case |
|:---|:---|:---|
| Debug Mode | Must be off in prod | Enable debug in prod |
"""
        elif "security boundary" in full_text or "data flow component" in full_text:
             response_text = """
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

        # Wrap response in types.Content
        content = types.Content(parts=[types.Part.from_text(text=response_text)])
        yield LlmResponse(content=content)
