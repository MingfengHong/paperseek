import unittest
from unittest.mock import patch

from tests.helpers import CONFIG_ENV_KEYS, temporary_env


def _mcp_available() -> bool:
    try:
        import mcp  # noqa: F401
        import sys
        return sys.version_info >= (3, 10)
    except ImportError:
        return False


class McpServerLogicTest(unittest.TestCase):
    """Test the pure logic functions in mcp_server (no mcp package required)."""

    def test_module_imports_without_mcp_package(self):
        """The module must be importable even when ``mcp`` is not installed."""
        import paperseek.mcp_server as mod
        self.assertTrue(hasattr(mod, "search_papers_logic"))
        self.assertTrue(hasattr(mod, "create_server"))

    # ------------------------------------------------------------------
    # list_sources_logic
    # ------------------------------------------------------------------

    def test_list_sources_returns_expected_ids(self):
        from paperseek.mcp_server import list_sources_logic

        result = list_sources_logic()
        ids = [item["id"] for item in result["sources"]]
        self.assertEqual(ids, ["openalex", "crossref", "wos"])
        self.assertTrue(result["sources"][0]["default"])

    # ------------------------------------------------------------------
    # check_config_logic
    # ------------------------------------------------------------------

    def test_check_config_reports_missing_llm_key(self):
        from paperseek.mcp_server import check_config_logic

        with temporary_env(
            {
                "DATA_SOURCE": "openalex",
                "LLM_PROVIDER": "openai",
                "LLM_API_TYPE": "openai_responses",
                "LLM_MODEL": "gpt-5.4-mini",
                "LLM_BASE_URL": "https://api.openai.com/v1",
                "LLM_API_KEY": "",
            },
            clear=CONFIG_ENV_KEYS,
        ):
            result = check_config_logic()
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "fail")

    def test_check_config_accepts_ollama_without_key(self):
        from paperseek.mcp_server import check_config_logic

        with temporary_env(
            {
                "DATA_SOURCE": "crossref",
                "LLM_PROVIDER": "ollama",
                "LLM_API_TYPE": "openai_chat",
                "LLM_MODEL": "qwen3:8b",
                "LLM_BASE_URL": "http://127.0.0.1:11434/v1",
                "LLM_API_KEY": "",
                "CROSSREF_EMAIL": "you@example.org",
            },
            clear=CONFIG_ENV_KEYS,
        ):
            result = check_config_logic()
        self.assertTrue(result["ok"])
        self.assertIn(result["status"], ("pass", "warning"))

    def test_check_config_respects_source_override(self):
        from paperseek.mcp_server import check_config_logic

        with temporary_env(
            {
                "DATA_SOURCE": "openalex",
                "LLM_PROVIDER": "ollama",
                "LLM_API_TYPE": "openai_chat",
                "LLM_MODEL": "qwen3:8b",
                "LLM_BASE_URL": "http://127.0.0.1:11434/v1",
            },
            clear=CONFIG_ENV_KEYS,
        ):
            result = check_config_logic(source="crossref")
        checks = {c["id"]: c for c in result["checks"]}
        source_check = checks.get("source.supported")
        self.assertIsNotNone(source_check)
        self.assertIn("Crossref", source_check["summary"])

    # ------------------------------------------------------------------
    # search_papers_logic
    # ------------------------------------------------------------------

    def test_search_rejects_empty_question(self):
        from paperseek.mcp_server import search_papers_logic

        result = search_papers_logic(question="")
        self.assertIn("error", result)
        self.assertIn("required", result["error"])

    def test_search_returns_config_error_without_llm_key(self):
        from paperseek.mcp_server import search_papers_logic

        with temporary_env(
            {
                "DATA_SOURCE": "openalex",
                "LLM_PROVIDER": "deepseek",
                "LLM_API_TYPE": "openai_chat",
                "LLM_MODEL": "deepseek-v4-flash",
                "LLM_BASE_URL": "https://api.deepseek.com",
                "LLM_API_KEY": "",
            },
            clear=CONFIG_ENV_KEYS,
        ):
            result = search_papers_logic(question="open innovation")
        self.assertIn("error", result)
        self.assertIn("Configuration error", result["error"])

    # ------------------------------------------------------------------
    # smoke_test_logic
    # ------------------------------------------------------------------

    def test_smoke_test_redacts_provider_error_credentials(self):
        from paperseek.mcp_server import smoke_test_logic
        from paperseek.providers import ProviderError

        secret = "sk-secret-abcdef123456"

        def fail_with_secret(*args, **kwargs):
            raise ProviderError(
                "openalex",
                f"failed Authorization: Bearer {secret}",
                status=401,
                query="machine learning",
                body=f"x-api-key: {secret}",
            )

        with temporary_env({"DATA_SOURCE": "openalex"}, clear=CONFIG_ENV_KEYS):
            with patch("paperseek.diagnostics.OpenAlexProvider.search", fail_with_secret):
                result = smoke_test_logic(source="openalex")

        payload = str(result)
        self.assertNotIn(secret, payload)
        self.assertIn("[redacted]", payload)

    # ------------------------------------------------------------------
    # list_history_logic
    # ------------------------------------------------------------------

    def test_list_history_returns_status(self):
        from paperseek.mcp_server import list_history_logic

        result = list_history_logic(limit=5)
        self.assertIn("enabled", result)
        self.assertIn("path", result)
        self.assertIn("history", result)

    def test_list_history_respects_disabled_flag(self):
        from paperseek.mcp_server import list_history_logic

        with temporary_env(
            {"PAPERSEEK_HISTORY_ENABLED": "false"},
            clear=("PAPERSEEK_HISTORY_ENABLED",),
        ):
            result = list_history_logic()
        self.assertFalse(result["enabled"])
        self.assertEqual(result["history"], [])

    # ------------------------------------------------------------------
    # get_history_run_logic
    # ------------------------------------------------------------------

    def test_get_history_run_returns_error_for_missing_id(self):
        from paperseek.mcp_server import get_history_run_logic

        result = get_history_run_logic("run_does_not_exist")
        self.assertIn("error", result)
        self.assertIn("not found", result["error"])

    # ------------------------------------------------------------------
    # _build_search_config
    # ------------------------------------------------------------------

    def test_build_search_config_applies_overrides(self):
        from paperseek.mcp_server import _build_search_config

        with temporary_env(
            {
                "DATA_SOURCE": "openalex",
                "LLM_PROVIDER": "deepseek",
                "LLM_API_TYPE": "openai_chat",
                "LLM_MODEL": "deepseek-v4-flash",
                "LLM_BASE_URL": "https://api.deepseek.com",
                "LLM_API_KEY": "sk-test",
            },
            clear=CONFIG_ENV_KEYS,
        ):
            config = _build_search_config(
                source="crossref",
                field="management",
                discipline_fields=["Computer Science", "17"],
                target_min=10,
                target_max=30,
                max_iterations=3,
                expand_citations=False,
                fetch_abstracts=True,
            )
        self.assertEqual(config.data_source, "crossref")
        self.assertEqual(config.search_field, "management")
        self.assertEqual(config.discipline_fields, ("17",))
        self.assertEqual(config.target_min, 10)
        self.assertEqual(config.target_max, 30)
        self.assertEqual(config.max_iterations, 3)
        self.assertFalse(config.expand_citations)
        self.assertTrue(config.fetch_abstracts)

    def test_build_search_config_preserves_env_when_no_overrides(self):
        from paperseek.mcp_server import _build_search_config

        with temporary_env(
            {
                "DATA_SOURCE": "crossref",
                "LLM_PROVIDER": "deepseek",
                "LLM_API_TYPE": "openai_chat",
                "LLM_MODEL": "deepseek-v4-flash",
                "LLM_BASE_URL": "https://api.deepseek.com",
                "LLM_API_KEY": "sk-test",
                "TARGET_MIN": "8",
                "TARGET_MAX": "40",
            },
            clear=CONFIG_ENV_KEYS,
        ):
            config = _build_search_config()
        self.assertEqual(config.data_source, "crossref")
        self.assertEqual(config.target_min, 8)
        self.assertEqual(config.target_max, 40)

    def test_build_search_config_preserves_env_boolean_defaults(self):
        """Boolean flags default to ``None`` so env values win by default."""
        from paperseek.mcp_server import _build_search_config

        with temporary_env(
            {
                "DATA_SOURCE": "openalex",
                "LLM_PROVIDER": "ollama",
                "LLM_API_TYPE": "openai_chat",
                "LLM_MODEL": "qwen3:8b",
                "LLM_BASE_URL": "http://127.0.0.1:11434/v1",
                "LLM_API_KEY": "",
                "EXPAND_CITATIONS": "false",
                "FETCH_ABSTRACTS": "true",
            },
            clear=CONFIG_ENV_KEYS,
        ):
            config = _build_search_config()
        self.assertFalse(config.expand_citations)
        self.assertTrue(config.fetch_abstracts)

    def test_build_search_config_explicit_overrides_env(self):
        """Passing True/False still overrides env values."""
        from paperseek.mcp_server import _build_search_config

        with temporary_env(
            {
                "DATA_SOURCE": "openalex",
                "LLM_PROVIDER": "ollama",
                "LLM_API_TYPE": "openai_chat",
                "LLM_MODEL": "qwen3:8b",
                "LLM_BASE_URL": "http://127.0.0.1:11434/v1",
                "LLM_API_KEY": "",
                "EXPAND_CITATIONS": "false",
                "FETCH_ABSTRACTS": "true",
            },
            clear=CONFIG_ENV_KEYS,
        ):
            config = _build_search_config(
                expand_citations=True,
                fetch_abstracts=False,
            )
        self.assertTrue(config.expand_citations)
        self.assertFalse(config.fetch_abstracts)

    # ------------------------------------------------------------------
    # _redact_secrets
    # ------------------------------------------------------------------

    def test_redact_secrets_removes_authorization_header(self):
        from paperseek.mcp_server import _redact_secrets

        text = 'HTTP 401: {"error": "Authorization: Bearer sk-abcdef0123456789"}'
        redacted = _redact_secrets(text)
        self.assertNotIn("sk-abcdef0123456789", redacted)
        self.assertIn("[redacted]", redacted)

    def test_redact_secrets_removes_api_key_header(self):
        from paperseek.mcp_server import _redact_secrets

        text = "x-api-key: sk-test-1234567890, status=401"
        redacted = _redact_secrets(text)
        self.assertNotIn("sk-test-1234567890", redacted)
        self.assertIn("x-api-key: [redacted]", redacted)

    def test_redact_secrets_truncates_long_text(self):
        from paperseek.mcp_server import _redact_secrets

        text = "a" * 1000
        redacted = _redact_secrets(text, max_chars=100)
        self.assertTrue(redacted.endswith("..."))
        self.assertLessEqual(len(redacted), 104)

    def test_redact_secrets_handles_empty(self):
        from paperseek.mcp_server import _redact_secrets

        self.assertEqual(_redact_secrets(""), "")
        self.assertEqual(_redact_secrets(None), "")  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # create_server
    # ------------------------------------------------------------------

    @unittest.skipUnless(
        _mcp_available(),
        "mcp package not installed",
    )
    def test_create_server_returns_server_instance(self):
        from paperseek.mcp_server import create_server

        server = create_server()
        self.assertIsNotNone(server)


if __name__ == "__main__":
    unittest.main()
