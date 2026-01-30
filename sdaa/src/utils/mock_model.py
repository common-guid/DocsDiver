from typing import AsyncGenerator, Optional
import uuid
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

        # 1. Map Maker (Architectural Summary)
        if "architectural summary" in full_text and "role based access controls" not in full_text and "business logic" not in full_text and "security boundary" not in full_text:
             response_text = '{"summary": "This is a mock summary of the architectural component.", "tags": ["mock", "test", "doc"]}'
             content = types.Content(role="model", parts=[types.Part.from_text(text=response_text)])
             yield LlmResponse(content=content)
             return

        # 2. Coordinator (Principal Security Architect)
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
            # Check if tool has already been called
            if "report saved successfully" in contents_text:
                # Tool called, return final text
                content = types.Content(role="model", parts=[types.Part.from_text(text=report_content)])
                yield LlmResponse(content=content)
            else:
                # Call tool
                fc = types.FunctionCall(
                    name="generate_final_report",
                    args={"report_content": report_content},
                    id=str(uuid.uuid4())
                )
                part = types.Part(function_call=fc)
                yield LlmResponse(content=types.Content(role="model", parts=[part]))
            return

        # 3. Permissions Agent
        if "role based access controls" in full_text or "permissions analyst" in full_text:
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
            if "permissions findings recorded" in contents_text:
                 content = types.Content(role="model", parts=[types.Part.from_text(text=findings)])
                 yield LlmResponse(content=content)
            else:
                 fc = types.FunctionCall(
                     name="report_permissions_matrix",
                     args={"findings": findings},
                     id=str(uuid.uuid4())
                 )
                 part = types.Part(function_call=fc)
                 yield LlmResponse(content=types.Content(role="model", parts=[part]))
            return

        # 4. Constraints Agent
        if "business logic" in full_text or "negative constraints" in full_text:
            findings = """
# Logic Analysis
## 1. Analysis Summary
Analyzed files: billing.md
## 2. Configuration Risks
| Feature | Claim | Test Case |
|:---|:---|:---|
| Debug Mode | Must be off in prod | Enable debug in prod |
"""
            if "invariance findings recorded" in contents_text:
                 content = types.Content(role="model", parts=[types.Part.from_text(text=findings)])
                 yield LlmResponse(content=content)
            else:
                 fc = types.FunctionCall(
                     name="report_invariance_findings",
                     args={"findings": findings},
                     id=str(uuid.uuid4())
                 )
                 part = types.Part(function_call=fc)
                 yield LlmResponse(content=types.Content(role="model", parts=[part]))
            return

        # 5. Boundaries Agent
        if "security boundary" in full_text or "data flow component" in full_text:
            findings = """
# Boundaries Analysis
## 1. Architecture Overview
Overview of boundaries.

## 2. Boundaries Data
```json
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
```
"""
            if "recorded boundary analysis" in contents_text:
                 content = types.Content(role="model", parts=[types.Part.from_text(text=findings)])
                 yield LlmResponse(content=content)
            else:
                 fc = types.FunctionCall(
                     name="report_boundary_analysis",
                     args={"boundaries_markdown": findings},
                     id=str(uuid.uuid4())
                 )
                 part = types.Part(function_call=fc)
                 yield LlmResponse(content=types.Content(role="model", parts=[part]))
            return

        # Fallback
        response_text = "Mock response fallback"
        content = types.Content(role="model", parts=[types.Part.from_text(text=response_text)])
        yield LlmResponse(content=content)
