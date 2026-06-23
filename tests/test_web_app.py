import unittest

from fastapi.testclient import TestClient

from paperseek.web_app import app
from paperseek.web_app import SearchRequest, _config_from_payload
from tests.helpers import CONFIG_ENV_KEYS, temporary_env


class WebAppTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_sources_endpoint_returns_ordered_source_capabilities(self):
        response = self.client.get("/api/sources")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([item["id"] for item in payload["sources"]], ["openalex", "crossref", "wos"])
        self.assertTrue(payload["sources"][0]["default"])
        self.assertEqual(payload["sources"][-1]["status"], "temporarily_unavailable")
        self.assertIn("discipline_fields", payload["sources"][0]["supported_parameters"])

    def test_disciplines_endpoint_returns_openalex_fields(self):
        response = self.client.get("/api/disciplines")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["disciplines"]), 26)
        self.assertEqual(payload["disciplines"][6]["id"], "17")
        self.assertEqual(payload["disciplines"][6]["label"], "Computer Science")

    def test_diagnostics_accepts_ollama_without_api_key(self):
        response = self.client.post(
            "/api/diagnostics",
            json={
                "data_source": "openalex",
                "llm_provider": "ollama",
                "llm_api_type": "openai_chat",
                "llm_model": "qwen3:8b",
                "llm_base_url": "http://127.0.0.1:11434/v1",
                "target_min": 5,
                "target_max": 50,
                "max_iterations": 5,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], ("pass", "warning"))
        self.assertNotEqual(payload["status"], "fail")

    def test_search_validation_reports_missing_question(self):
        response = self.client.post(
            "/api/search",
            json={
                "question": "",
                "data_source": "openalex",
                "llm_provider": "ollama",
                "llm_api_type": "openai_chat",
                "target_min": 5,
                "target_max": 50,
                "max_iterations": 5,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("Research Question is required", response.json()["detail"])

    def test_search_rejects_invalid_target_range_before_llm_setup(self):
        response = self.client.post(
            "/api/search",
            json={
                "question": "open innovation",
                "data_source": "openalex",
                "llm_provider": "ollama",
                "llm_api_type": "openai_chat",
                "target_min": 20,
                "target_max": 5,
                "max_iterations": 5,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Target minimum cannot exceed", response.json()["detail"])

    def test_config_from_payload_preserves_environment_credentials_when_form_keys_are_blank(self):
        with temporary_env({
            "DATA_SOURCE": "openalex",
            "OPENALEX_API_KEY": "oa-env-test",
            "LLM_PROVIDER": "deepseek",
            "LLM_API_TYPE": "openai_chat",
            "LLM_MODEL": "deepseek-test",
            "LLM_BASE_URL": "https://api.deepseek.com",
            "LLM_API_KEY": "sk-env-test",
        }, clear=CONFIG_ENV_KEYS):
            payload = SearchRequest(
                question="open innovation",
                data_source="openalex",
                openalex_api_key="",
                llm_api_key="",
                llm_provider="",
                llm_api_type="",
                llm_model=None,
                llm_base_url=None,
                discipline_fields=["Computer Science", "14"],
            )
            config = _config_from_payload(payload)
            self.assertEqual(config.openalex_api_key, "oa-env-test")
            self.assertEqual(config.llm_api_key, "sk-env-test")
            self.assertEqual(config.llm_provider, "deepseek")
            self.assertEqual(config.llm_model, "deepseek-test")
            self.assertEqual(config.discipline_fields, ("17", "14"))

    def test_config_defaults_reports_configured_secrets_without_exposing_values(self):
        with temporary_env({
            "DATA_SOURCE": "openalex",
            "OPENALEX_API_KEY": "oa-env-test",
            "LLM_PROVIDER": "deepseek",
            "LLM_API_TYPE": "openai_chat",
            "LLM_MODEL": "deepseek-test",
            "LLM_BASE_URL": "https://api.deepseek.com",
            "LLM_API_KEY": "sk-env-test",
        }, clear=CONFIG_ENV_KEYS):
            response = self.client.get("/api/config/defaults")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["llm_provider"], "deepseek")
            self.assertTrue(payload["has_llm_api_key"])
            self.assertTrue(payload["has_openalex_api_key"])
            self.assertNotIn("sk-env-test", response.text)
            self.assertNotIn("oa-env-test", response.text)


if __name__ == "__main__":
    unittest.main()
