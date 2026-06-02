import unittest

from fastapi.testclient import TestClient

from paperseek.web_app import app


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


if __name__ == "__main__":
    unittest.main()
