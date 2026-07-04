import unittest
from unittest.mock import patch

from paperseek.config import AgentConfig
from paperseek.diagnostics import run_doctor, smoke_source


class FakeResponse:
    status_code = 200
    reason = "OK"
    text = "{}"

    def json(self):
        return {
            "metadata": {"total": "1", "page": "1", "limit": "1"},
            "hits": [{
                "uid": "WOS:1",
                "title": "AI Governance",
                "source": {"sourceTitle": "Research Policy", "publishYear": "2025"},
            }],
        }


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

    def test_wos_smoke_uses_raw_fallback_when_client_parse_fails(self):
        config = AgentConfig(
            data_source="wos",
            llm_provider="ollama",
            llm_api_type="openai_chat",
            llm_model="qwen3:8b",
            llm_base_url="http://127.0.0.1:11434/v1",
            llm_api_key="",
            wos_api_key="secret",
            wos_db="WOS",
        )

        with patch("paperseek.diagnostics.DocumentsApi.documents_get", side_effect=ValueError("strict parse")):
            with patch("paperseek.diagnostics.requests.get", return_value=FakeResponse()) as raw_get:
                result = smoke_source(config, query="AI governance", limit=1)

        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "wos")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["sample_titles"], ["AI Governance"])
        self.assertEqual(raw_get.call_args.kwargs["params"]["q"], "TS=(AI governance)")


if __name__ == "__main__":
    unittest.main()
