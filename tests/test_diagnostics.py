import unittest

from paperseek.config import AgentConfig
from paperseek.diagnostics import run_doctor


class DiagnosticsTest(unittest.TestCase):
    def test_doctor_reports_missing_llm_key(self):
        config = AgentConfig(
            data_source="openalex",
            llm_provider="openai",
            llm_api_type="openai_responses",
            llm_model="gpt-5.4-mini",
            llm_base_url="https://api.openai.com/v1",
            llm_api_key="",
        )
        result = run_doctor(config)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "fail")
        failing_ids = {check["id"] for check in result["checks"] if check["status"] == "fail"}
        self.assertIn("llm.api_key", failing_ids)

    def test_doctor_accepts_local_ollama_without_key(self):
        config = AgentConfig(
            data_source="crossref",
            llm_provider="ollama",
            llm_api_type="openai_chat",
            llm_model="qwen3:8b",
            llm_base_url="http://127.0.0.1:11434/v1",
            llm_api_key="",
            crossref_email="you@example.org",
        )
        result = run_doctor(config)
        self.assertTrue(result["ok"])
        self.assertIn(result["status"], ("pass", "warning"))


if __name__ == "__main__":
    unittest.main()
