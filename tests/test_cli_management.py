import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import CONFIG_ENV_KEYS, run_cli


SOURCE_IDS = ["openalex", "arxiv", "semanticscholar", "pubmed", "googlescholar", "paperhub", "crossref", "wos"]


class CliManagementTest(unittest.TestCase):
    def test_sources_json_contract(self):
        result = run_cli("sources", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual([item["id"] for item in payload["sources"]], SOURCE_IDS)

    def test_config_set_list_unset_uses_requested_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = str(Path(tmp) / "paperseek-config.json")
            env = {key: "" for key in CONFIG_ENV_KEYS}
            env.update({"PAPERSEEK_CONFIG_FILE": config_file, "PAPERSEEK_DOTENV_DISABLED": "1"})

            set_result = run_cli("config", "set", "LLM_API_KEY", "sk-test-abcdef", env=env)
            self.assertEqual(set_result.returncode, 0, set_result.stderr)

            list_result = run_cli("config", "list", "--json", env=env)
            self.assertEqual(list_result.returncode, 0, list_result.stderr)
            payload = json.loads(list_result.stdout)
            row = next(item for item in payload["entries"] if item["key"] == "LLM_API_KEY")
            self.assertEqual(row["value"], "sk-t...cdef")
            self.assertEqual(row["source"], "user_config")

            unset_result = run_cli("config", "unset", "LLM_API_KEY", env=env)
            self.assertEqual(unset_result.returncode, 0, unset_result.stderr)

            list_after_unset = run_cli("config", "list", "--json", env=env)
            self.assertEqual(list_after_unset.returncode, 0, list_after_unset.stderr)
            payload = json.loads(list_after_unset.stdout)
            self.assertFalse(any(item["key"] == "LLM_API_KEY" for item in payload["entries"]))

    def test_cli_loads_dotenv_from_working_directory_before_user_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join([
                    "DATA_SOURCE=openalex",
                    "OPENALEX_API_KEY=oa-env-test",
                    "LLM_PROVIDER=deepseek",
                    "LLM_API_TYPE=openai_chat",
                    "LLM_MODEL=deepseek-test",
                    "LLM_BASE_URL=https://api.deepseek.com",
                    "LLM_API_KEY=sk-env-test",
                ]),
                encoding="utf-8",
            )
            config_path = str(Path(tmp) / "paperseek-config.json")
            clean_env = {key: "" for key in CONFIG_ENV_KEYS}
            clean_env["PAPERSEEK_CONFIG_FILE"] = config_path

            result = run_cli("doctor", "--source", "openalex", "--json", env=clean_env, cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            summaries = [check["summary"] for check in payload["checks"]]
            self.assertIn("LLM provider 'deepseek' is supported.", summaries)
            self.assertIn("Source-specific required configuration is present or not required.", summaries)


if __name__ == "__main__":
    unittest.main()
