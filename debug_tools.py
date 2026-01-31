
import json
import logging
from google.genai import types
from sdaa.src.utils.openrouter_model import OpenRouterModel
from sdaa.src.tools.reporting import report_permissions_matrix

# Mock the client since we don't need to make network calls
class MockClient:
    pass

def test_schema_conversion():
    # Create a dummy tool definition manually to simulate what ADK might produce
    # Or better, use the ADK's introspection if possible, but let's just use google.genai.types
    
    # Define a function schema similar to report_permissions_matrix(findings: str)
    # Note: In a real scenario, ADK/GenAI SDK inspects the function to build this.
    # Here we manually build the schema object that OpenRouterModel._convert_tools expects.
    
    # Assuming google.genai.types.Tool and FunctionDeclaration
    
    func_decl = types.FunctionDeclaration(
        name="report_permissions_matrix",
        description="Logs the permissions matrix findings.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "findings": types.Schema(
                    type=types.Type.STRING,
                    description="Markdown findings"
                )
            },
            required=["findings"]
        )
    )
    
    tool = types.Tool(function_declarations=[func_decl])
    
    # Instantiate model (mocking client)
    model = OpenRouterModel("test-model", api_key="test")
    model.client = MockClient()
    
    # Test conversion
    converted = model._convert_tools([tool])
    
    print("Converted Tools JSON:")
    print(json.dumps(converted, indent=2))
    
    # Check if "type" is correct
    props = converted[0]['function']['parameters']['properties']
    if props['findings']['type'] != 'string':
        print(f"FAILURE: Expected 'string', got '{props['findings']['type']}'")
    else:
        print("SUCCESS: Parameter type is 'string'")

if __name__ == "__main__":
    try:
        test_schema_conversion()
    except Exception as e:
        print(f"Error: {e}")
