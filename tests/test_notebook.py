import unittest
import os
import json
import shutil
from sdaa.src.tools.notebook import append_to_notebook, read_notebook, clear_notebook
from sdaa.src.core.config_loader import config_loader

class TestNotebookTools(unittest.TestCase):
    def setUp(self):
        self.original_output_dir = config_loader.get_output_dir()
        self.test_output_dir = "test_output_notebook"
        os.makedirs(self.test_output_dir, exist_ok=True)

        # Override output dir in config_loader if possible, but config_loader is a singleton.
        # Since I can't easily override config_loader internal state without mocking,
        # I will rely on the fact that `_get_notebook_dir` calls `config_loader.get_output_dir`.
        # I can mock `config_loader.get_output_dir`.
        self.original_get_output_dir = config_loader.get_output_dir
        config_loader.get_output_dir = lambda: self.test_output_dir

        self.notebook_dir = os.path.join(self.test_output_dir, "notebook")
        os.makedirs(self.notebook_dir, exist_ok=True)

    def tearDown(self):
        config_loader.get_output_dir = self.original_get_output_dir
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def test_append_and_read(self):
        cat = "test_cat"
        content = "Finding 1"

        # Append
        result = append_to_notebook(cat, content)
        self.assertIn("Successfully appended", result)

        # Read specific
        read_res = read_notebook(cat)
        data = json.loads(read_res)
        self.assertEqual(len(data["findings"]), 1)
        self.assertEqual(data["findings"][0]["content"], content)

        # Read all
        read_all = read_notebook()
        all_data = json.loads(read_all)
        self.assertIn(cat, all_data)
        self.assertEqual(len(all_data[cat]), 1)

    def test_clear(self):
        cat = "clear_cat"
        append_to_notebook(cat, "foo")

        # Clear specific
        clear_notebook(cat)
        res = read_notebook(cat)
        self.assertIn("empty or does not exist", res)

        # Clear all
        append_to_notebook("c1", "v1")
        append_to_notebook("c2", "v2")
        clear_notebook()
        res = read_notebook()
        all_data = json.loads(res)
        self.assertEqual(len(all_data), 0)

if __name__ == '__main__':
    unittest.main()
