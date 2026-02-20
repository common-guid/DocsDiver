import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import json
import os
import shutil

from sdaa.src.core.batch_processor import run_batch_audit
from sdaa.src.tools.notebook import append_to_notebook, read_notebook, clear_notebook
from sdaa.src.core.config_loader import config_loader

class TestBatchProcessing(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.output_dir = "test_output_batch"
        os.makedirs(self.output_dir, exist_ok=True)
        self.toc_path = os.path.join(self.output_dir, "ToC.json")

        # Mock ToC
        toc_data = {
            "files": [
                {"path": "file1.md", "summary": "s1", "tags": ["t1"]},
                {"path": "file2.md", "summary": "s2", "tags": ["t2"]},
                {"path": "file3.md", "summary": "s3", "tags": ["t3"]},
                {"path": "file4.md", "summary": "s4", "tags": ["t4"]},
                {"path": "file5.md", "summary": "s5", "tags": ["t5"]},
                {"path": "file6.md", "summary": "s6", "tags": ["t6"]},
            ]
        }
        with open(self.toc_path, 'w') as f:
            json.dump(toc_data, f)

        # Mock config_loader
        self.original_get_output_dir = config_loader.get_output_dir
        config_loader.get_output_dir = lambda: self.output_dir

        # Setup notebook dir
        self.notebook_dir = os.path.join(self.output_dir, "notebook")
        os.makedirs(self.notebook_dir, exist_ok=True)

    async def asyncTearDown(self):
        config_loader.get_output_dir = self.original_get_output_dir
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    @patch('sdaa.src.core.batch_processor.Runner')
    @patch('sdaa.src.core.batch_processor.get_model_for_agent')
    @patch('sdaa.src.core.batch_processor.create_permissions_agent')
    @patch('sdaa.src.core.batch_processor.create_constraints_agent')
    @patch('sdaa.src.core.batch_processor.create_boundaries_agent')
    @patch('sdaa.src.core.batch_processor.create_coordinator_synthesizer')
    async def test_batch_execution(self,
                                   mock_synth_factory,
                                   mock_boundaries_factory,
                                   mock_constraints_factory,
                                   mock_permissions_factory,
                                   mock_get_model,
                                   mock_runner_class):

        # Mock factories to return agents with tools list
        mock_agent = MagicMock()
        mock_agent.tools = []
        mock_permissions_factory.return_value = mock_agent
        mock_constraints_factory.return_value = mock_agent
        mock_boundaries_factory.return_value = mock_agent
        mock_synth_factory.return_value = mock_agent

        # Mock Runner
        mock_runner_instance = MagicMock()
        mock_runner_class.return_value = mock_runner_instance

        # Mock run_async to be an AsyncMock that can also act as an async generator
        async def mock_run_async_gen(*args, **kwargs):
            yield MagicMock(content="Mock response")

        mock_runner_instance.run_async = AsyncMock(side_effect=mock_run_async_gen)

        # Mock UI
        mock_ui = MagicMock()
        mock_ui.stream_response = AsyncMock()

        # Run Batch Audit
        await run_batch_audit("mock-provider", ui=mock_ui)

        # Verify calls
        # 3 workers * 2 batches = 6 calls to worker factories
        self.assertEqual(mock_permissions_factory.call_count, 2)
        
        # Verify that run_async was called with types.Content
        from google.genai import types
        call_args = mock_runner_instance.run_async.call_args_list[0]
        new_message = call_args.kwargs.get('new_message')
        self.assertIsInstance(new_message, types.Content)
        self.assertTrue(len(new_message.parts) > 0)
        self.assertTrue(hasattr(new_message.parts[0], 'text'))
        self.assertEqual(mock_constraints_factory.call_count, 2)
        self.assertEqual(mock_boundaries_factory.call_count, 2)

        # Coordinator called once
        self.assertEqual(mock_synth_factory.call_count, 1)

        # Check if append_to_notebook was added to tools
        self.assertIn(append_to_notebook, mock_agent.tools)

        # Check if read_notebook was added to coordinator tools (mock_agent is reused)
        self.assertIn(read_notebook, mock_agent.tools)

        # Check UI interaction
        self.assertEqual(mock_ui.stream_response.call_count, 7)
        self.assertEqual(mock_ui.print_status.call_count, 12) # approx

if __name__ == '__main__':
    unittest.main()
