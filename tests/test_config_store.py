import os
import tempfile
import unittest
from pathlib import Path

from paperseek import config_store


class ConfigStoreTest(unittest.TestCase):
    def test_set_list_and_mask_config_value(self):
        previous = os.environ.get("PAPERSEEK_CONFIG_FILE")
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["PAPERSEEK_CONFIG_FILE"] = str(Path(tmp) / "config.json")
            try:
                config_store.set_config_value("LLM_API_KEY", "sk-test-123456")
                entries = config_store.list_config_entries()
                row = next(item for item in entries if item["key"] == "LLM_API_KEY")
                self.assertTrue(row["configured"])
                self.assertEqual(row["source"], "user_config")
                self.assertEqual(row["value"], "sk-t...3456")
                config_store.unset_config_value("LLM_API_KEY")
                self.assertNotIn("LLM_API_KEY", config_store.read_config())
            finally:
                if previous is None:
                    os.environ.pop("PAPERSEEK_CONFIG_FILE", None)
                else:
                    os.environ["PAPERSEEK_CONFIG_FILE"] = previous


if __name__ == "__main__":
    unittest.main()
