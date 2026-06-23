import tempfile
import unittest
from pathlib import Path

from paperseek import config_store
from tests.helpers import CONFIG_ENV_KEYS, temporary_env


class ConfigStoreTest(unittest.TestCase):
    def test_set_list_and_mask_config_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            with temporary_env(
                {"PAPERSEEK_CONFIG_FILE": str(Path(tmp) / "config.json")},
                clear=CONFIG_ENV_KEYS,
            ):
                config_store.set_config_value("LLM_API_KEY", "sk-test-123456")
                entries = config_store.list_config_entries()
                row = next(item for item in entries if item["key"] == "LLM_API_KEY")
                self.assertTrue(row["configured"])
                self.assertEqual(row["source"], "user_config")
                self.assertEqual(row["value"], "sk-t...3456")
                config_store.unset_config_value("LLM_API_KEY")
                self.assertNotIn("LLM_API_KEY", config_store.read_config())


if __name__ == "__main__":
    unittest.main()
