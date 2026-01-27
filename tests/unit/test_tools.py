import unittest
from unittest.mock import patch, mock_open
from src.tools.file_tools import SearchFilesTool

class TestSearchTool(unittest.TestCase):

    def test_search_context_window(self):
        """Verify the tool returns 3 lines before and after the match."""
        tool = SearchFilesTool()

        # Mock file content with 10 lines
        file_content = "\n".join([f"Line {i}" for i in range(1, 11)])
        # Let's verify searching for "Line 5"

        with patch("builtins.open", mock_open(read_data=file_content)):
            with patch("os.walk") as mock_walk:
                # Mock directory structure
                mock_walk.return_value = [(".", [], ["test.md"])]

                result = tool._run(query="Line 5", directory=".")

                # Assertions
                self.assertIn("Line 2", result, "Context should include 3 lines before (Line 2)")
                self.assertIn(">> Line 5", result, "Match should have visual marker >>")
                self.assertIn("Line 8", result, "Context should include 3 lines after (Line 8)")
                self.assertNotIn("Line 1", result, "Context should NOT include Line 1 (too far)")

if __name__ == "__main__":
    unittest.main()
