import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliManagementTest(unittest.TestCase):
    def run_cli(self, *args, env=None):
        merged_env = os.environ.copy()
        merged_env["PYTHONIOENCODING"] = "utf-8"
        if env:
            merged_env.update(env)
        return subprocess.run(
            [sys.executable, "-m", "paperseek.cli", *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=merged_env,
        )

    def test_sources_json_contract(self):
        result = self.run_cli("sources", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual([item["id"] for item in payload["sources"]], ["openalex", "crossref", "wos"])

    def test_config_set_list_unset_uses_requested_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = str(Path(tmp) / "paperseek-config.json")
            env = {"PAPERSEEK_CONFIG_FILE": config_file}

            set_result = self.run_cli("config", "set", "LLM_API_KEY", "sk-test-abcdef", env=env)
            self.assertEqual(set_result.returncode, 0, set_result.stderr)

            list_result = self.run_cli("config", "list", "--json", env=env)
            self.assertEqual(list_result.returncode, 0, list_result.stderr)
            payload = json.loads(list_result.stdout)
            row = next(item for item in payload["entries"] if item["key"] == "LLM_API_KEY")
            self.assertEqual(row["value"], "sk-t...cdef")
            self.assertEqual(row["source"], "user_config")

            unset_result = self.run_cli("config", "unset", "LLM_API_KEY", env=env)
            self.assertEqual(unset_result.returncode, 0, unset_result.stderr)

            list_after_unset = self.run_cli("config", "list", "--json", env=env)
            self.assertEqual(list_after_unset.returncode, 0, list_after_unset.stderr)
            payload = json.loads(list_after_unset.stdout)
            self.assertFalse(any(item["key"] == "LLM_API_KEY" for item in payload["entries"]))


if __name__ == "__main__":
    unittest.main()
