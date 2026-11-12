from sdaa.src.core.model_factory import get_model_for_agent


def test_factory_models_carry_agent():
    for provider in ("mock", "openrouter"):
        model = get_model_for_agent("permissions_agent", provider)
        assert model._agent == "permissions_agent"
