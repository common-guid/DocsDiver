import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os

# Add repo root to path
sys.path.append(os.getcwd())

from sdaa.src.core.model_factory import get_model_for_agent
from google.adk.models import Gemini
from sdaa.src.utils.openrouter_model import OpenRouterModel
from sdaa.src.utils.mock_model import MockModel

class TestModelFactory(unittest.TestCase):
    @patch('sdaa.src.core.model_factory.config_loader')
    def test_get_model_gemini(self, mock_config_loader):
        # Setup config mock
        def config_side_effect(key, default=None):
            if key == "agents.map_maker.gemini":
                return "gemini-test-model"
            return default

        mock_config_loader.get.side_effect = config_side_effect

        model = get_model_for_agent("map_maker", "gemini")

        self.assertIsInstance(model, Gemini)
        self.assertEqual(model.model, "gemini-test-model")

    @patch('sdaa.src.core.model_factory.config_loader')
    def test_get_model_openrouter(self, mock_config_loader):
        def config_side_effect(key, default=None):
            if key == "agents.coordinator.openrouter":
                return "openrouter-test-model"
            if key == "providers.openrouter.base_url":
                return "https://test.url"
            return default

        mock_config_loader.get.side_effect = config_side_effect

        model = get_model_for_agent("coordinator", "openrouter")

        self.assertIsInstance(model, OpenRouterModel)
        self.assertEqual(model.model, "openrouter-test-model")

    def test_get_model_mock(self):
        model = get_model_for_agent("any_agent", "mock")
        self.assertIsInstance(model, MockModel)

class TestIntegration(unittest.TestCase):
    @patch('main.generate_toc')
    @patch('main.create_coordinator_agent')
    @patch('main.get_model_for_agent')
    @patch('main.RichUI')
    @patch('main.Runner')
    @patch('main.InMemorySessionService')
    @patch('main.InMemoryMemoryService')
    @patch('main.config_loader')
    @patch('sys.argv', ['main.py', '-m', 'gemini', '--skip-map-maker', '--toc-only']) # Minimal run
    def test_main_calls_factory_correctly(self, mock_config, mock_memory, mock_session, mock_runner, mock_ui, mock_get_model, mock_create_coord, mock_gen_toc):
        from main import main
        import asyncio

        # Setup mocks
        mock_get_model.return_value = MockModel(model="test-mock")

        # Run main
        asyncio.run(main())

        # Verify get_model_for_agent was NOT called for map maker because of skip-map-maker?
        # Wait, if skip-map-maker is present, we skip map maker logic.

    @patch('main.generate_toc')
    @patch('main.create_coordinator_agent')
    @patch('main.get_model_for_agent')
    @patch('main.RichUI')
    @patch('main.Runner')
    @patch('main.InMemorySessionService')
    @patch('main.InMemoryMemoryService')
    @patch('main.config_loader')
    @patch('sys.argv', ['main.py', '-m', 'gemini'])
    def test_main_calls_factory_for_all(self, mock_config, mock_memory, mock_session, mock_runner, mock_ui, mock_get_model, mock_create_coord, mock_gen_toc):
        from main import main
        import asyncio

        # Setup mocks
        mock_get_model.return_value = MockModel(model="test-mock")

        # Mock exists for toc
        mock_config.get_output_dir.return_value = "/tmp"
        mock_config.get.return_value = "ToC.json"
        with patch('os.path.exists', return_value=False): # Force map maker run
            # Also mock user input to exit immediately
            mock_ui_instance = mock_ui.return_value
            mock_ui_instance.ask_user.return_value = "exit"

            asyncio.run(main())

            # Check map maker model fetch
            mock_get_model.assert_any_call("map_maker", "gemini")

            # Check coordinator creation
            mock_create_coord.assert_called_with(provider="gemini")

    @patch('sdaa.src.agents.coordinator.create_permissions_agent')
    @patch('sdaa.src.agents.coordinator.create_constraints_agent')
    @patch('sdaa.src.agents.coordinator.create_boundaries_agent')
    @patch('sdaa.src.agents.coordinator.get_model_for_agent')
    @patch('sdaa.src.agents.coordinator.LlmAgent')
    def test_create_coordinator_agent_uses_factory(self, mock_LlmAgent, mock_get_model, mock_bound, mock_const, mock_perm):
        from sdaa.src.agents.coordinator import create_coordinator_agent

        mock_get_model.return_value = MockModel(model="factory-mock")

        create_coordinator_agent(provider="gemini")

        # Should verify get_model_for_agent called for each sub-agent
        mock_get_model.assert_any_call("permissions_agent", "gemini")
        mock_get_model.assert_any_call("constraints_agent", "gemini")
        mock_get_model.assert_any_call("boundaries_agent", "gemini")
        mock_get_model.assert_any_call("coordinator", "gemini")

if __name__ == '__main__':
    unittest.main()
