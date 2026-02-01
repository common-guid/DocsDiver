
from google.genai import types
import inspect

print("FunctionCall signature:")
try:
    print(inspect.signature(types.FunctionCall))
except ValueError:
    print("Could not get signature (might be a Pydantic model or similar)")
    print(types.FunctionCall.__annotations__)

print("\nFunctionCall init:")
print(dir(types.FunctionCall))
