from crewai import LLM
from src.config.model_config import (
    get_boundaries_model,
    get_negative_constraints_model,
    get_permissions_model,
    get_supervisor_model,
)

def get_supervisor_llm():
    """Returns the high-reasoning LLM for the Supervisor."""
    return LLM(model=get_supervisor_model())

def get_negative_constraints_llm():
    """Returns the LLM for the Negative Constraints agent."""
    return LLM(model=get_negative_constraints_model())


def get_permissions_llm():
    """Returns the LLM for the Permissions agent."""
    return LLM(model=get_permissions_model())


def get_boundaries_llm():
    """Returns the LLM for the Boundaries agent."""
    return LLM(model=get_boundaries_model())
