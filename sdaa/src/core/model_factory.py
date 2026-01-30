from typing import Optional
from google.adk.models import BaseLlm, Gemini
from sdaa.src.core.config_loader import config_loader
from sdaa.src.utils.mock_model import MockModel
from sdaa.src.utils.openrouter_model import OpenRouterModel

def get_model_for_agent(agent_name: str, provider: str) -> BaseLlm:
    """
    Factory function to instantiate the correct LLM model for a given agent and provider.

    Args:
        agent_name: The key of the agent in config.yaml (e.g., "map_maker", "coordinator")
        provider: The provider name selected via CLI (e.g., "gemini", "openrouter", "mock")

    Returns:
        An instance of BaseLlm (Gemini, OpenRouterModel, or MockModel)
    """
    if provider == "mock":
        return MockModel(model="mock-model")

    # Get model name from config: agents.<agent_name>.<provider>
    config_path = f"agents.{agent_name}.{provider}"
    model_name = config_loader.get(config_path)

    if not model_name:
        if provider == "gemini":
            model_name = "gemini-2.5-pro" # Fallback
        elif provider == "openrouter":
            model_name = "moonshotai/kimi-k2.5" # Fallback

    if provider == "gemini":
        return Gemini(model=model_name)

    elif provider == "openrouter":
        base_url = config_loader.get("providers.openrouter.base_url", "https://openrouter.ai/api/v1")
        return OpenRouterModel(model_name=model_name, base_url=base_url)

    else:
        # Unknown provider, return Mock or error.
        return MockModel(model=f"unknown-{provider}")
