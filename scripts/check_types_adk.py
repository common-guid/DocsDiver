
try:
    from google.genai import types
    from google.adk.models import LlmRequest
    print("Imports successful")
    print(f"types.Content fields: {types.Content.__annotations__ if hasattr(types.Content, '__annotations__') else 'unknown'}")
    
    # Try to instantiate with role
    try:
        c = types.Content(role="user", parts=[types.Part.from_text(text="hello")])
        print(f"Successfully created Content with role='user': {c}")
    except Exception as e:
        print(f"Failed to create Content with role='user': {e}")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
