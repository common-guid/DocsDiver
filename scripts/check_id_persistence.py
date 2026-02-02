
from google.genai import types

def check_id_persistence():
    fc = types.FunctionCall(name="test_func", args={}, id="test_id:0")
    print(f"FC ID: {fc.id}")
    
    part = types.Part(function_call=fc)
    print(f"Part FC ID: {part.function_call.id}")
    
    content = types.Content(parts=[part])
    print(f"Content Part FC ID: {content.parts[0].function_call.id}")

if __name__ == "__main__":
    check_id_persistence()
