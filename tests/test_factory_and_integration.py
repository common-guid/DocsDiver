import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add repo root to path
sys.path.append(os.getcwd())

from sdaa.src.agents.workers import create_permissions_agent, create_constraints_agent, create_boundaries_agent
from sdaa.src.agents.coordinator import create_coordinator_agent, create_coordinator_synthesizer

class TestAgyAgents(unittest.TestCase):
    @patch('sdaa.src.agents.workers.prompt_manager')
    def test_create_permissions_agent(self, mock_prompt_manager):
        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = "Mock Prompt"
        mock_prompt_manager.get_prompt_object.return_value = mock_prompt

        agent = create_permissions_agent()
        self.assertEqual(agent.name, "permissions_agent")
        self.assertEqual(agent.prompt, "Mock Prompt")
        self.assertTrue(len(agent.tools) > 0)

    @patch('sdaa.src.agents.workers.prompt_manager')
    def test_create_constraints_agent(self, mock_prompt_manager):
        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = "Mock Constraints Prompt"
        mock_prompt_manager.get_prompt_object.return_value = mock_prompt

        agent = create_constraints_agent()
        self.assertEqual(agent.name, "constraints_agent")
        self.assertEqual(agent.prompt, "Mock Constraints Prompt")

    @patch('sdaa.src.agents.workers.prompt_manager')
    def test_create_boundaries_agent(self, mock_prompt_manager):
        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = "Mock Boundaries Prompt {test}"
        mock_prompt_manager.get_prompt_object.return_value = mock_prompt

        agent = create_boundaries_agent()
        self.assertEqual(agent.name, "boundaries_agent")
        # should replace braces with double braces for escaping
        self.assertEqual(agent.prompt, "Mock Boundaries Prompt {{test}}")


class TestIntegration(unittest.TestCase):
    @patch('main.generate_toc')
    @patch('main.create_coordinator_agent')
    @patch('main.run_prechat_audit')
    @patch('main.RichUI')
    @patch('main.Agent')
    @patch('main.config_loader')
    @patch('sys.argv', ['main.py', '-m', 'gemini', '--skip-map-maker', '--toc-only']) # Minimal run
    def test_main_toc_only(self, mock_config, mock_agent, mock_ui, mock_prechat, mock_create_coord, mock_gen_toc):
        from main import main
        import asyncio

        # Mock config
        mock_config.get_output_dir.return_value = "/tmp"
        mock_config.get.return_value = "ToC.json"

        # Run main
        asyncio.run(main())

        # Verify main exited early before prechat or coordinator initialization
        mock_gen_toc.assert_not_called() # skipped because skip-map-maker is passed
        mock_prechat.assert_not_called()
        mock_create_coord.assert_not_called()

    @patch('main.generate_toc')
    @patch('main.create_coordinator_agent')
    @patch('main.run_prechat_audit')
    @patch('main.RichUI')
    @patch('main.Agent')
    @patch('main.config_loader')
    @patch('sys.argv', ['main.py', '-m', 'gemini'])
    @patch('os.path.exists', return_value=True) # Mock to skip map maker and skip pre-chat
    def test_main_skips_prechat_if_artifacts_exist(self, mock_exists, mock_config, mock_agent, mock_ui, mock_prechat, mock_create_coord, mock_gen_toc):
        from main import main
        import asyncio

        mock_config.get_output_dir.return_value = "/tmp"
        mock_config.get.return_value = "ToC.json"
        
        # Mock ui instance to exit immediately
        mock_ui_instance = mock_ui.return_value
        mock_ui_instance.ask_user.return_value = "exit"

        # Mock coordinator agent creation
        mock_create_coord.return_value = {
            "prompt": "mock prompt",
            "tools": []
        }

        # Mock AGY Agent context manager
        mock_agent_instance = AsyncMock()
        mock_agent.return_value.__aenter__.return_value = mock_agent_instance

        asyncio.run(main())

        # Verify prechat was skipped
        mock_prechat.assert_not_called()
        mock_agent.assert_called_once()

if __name__ == '__main__':
    unittest.main()
