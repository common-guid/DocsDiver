import os
from crewai import LLM

# Define your specific model names here
SUPERVISOR_MODEL_NAME = "openrouter/openai/gpt-4o"
WORKER_MODEL_NAME = "gemini/gemini-2.0-flash"

def get_supervisor_llm():
    """Returns the high-reasoning LLM for the Supervisor."""
    return LLM(model=SUPERVISOR_MODEL_NAME)

def get_worker_llm():
    """Returns the fast/efficient LLM for Worker agents."""
    return LLM(model=WORKER_MODEL_NAME)
