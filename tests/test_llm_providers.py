import unittest

from paperseek.config import (
    AgentConfig,
    SUPPORTED_LLM_PROVIDERS,
    default_api_type,
    default_base_url,
    default_model,
)
from tests.helpers import read_text, temporary_env


class LLMProviderTest(unittest.TestCase):
    def test_modelscope_provider_defaults(self):
        self.assertIn("modelscope", SUPPORTED_LLM_PROVIDERS)
        self.assertEqual(default_api_type("modelscope"), "openai_chat")
        self.assertEqual(default_model("modelscope"), "Qwen/Qwen3-235B-A22B-Instruct-2507")
        self.assertEqual(default_base_url("modelscope"), "https://api-inference.modelscope.cn/v1")

    def test_cstcloud_provider_defaults(self):
        self.assertIn("cstcloud", SUPPORTED_LLM_PROVIDERS)
        self.assertEqual(default_api_type("cstcloud"), "openai_chat")
        self.assertEqual(default_model("cstcloud"), "deepseek-v4-flash")
        self.assertEqual(default_base_url("cstcloud"), "https://uni-api.cstcloud.cn/v1")

    def test_blank_model_and_base_url_fall_back_to_provider_defaults(self):
        with temporary_env(
            {
                "LLM_PROVIDER": "openai",
                "LLM_MODEL": "",
                "LLM_BASE_URL": "",
            },
            clear=("LLM_API_TYPE",),
        ):
            config = AgentConfig.from_env()

        self.assertEqual(config.llm_model, "gpt-5.4-mini")
        self.assertEqual(config.llm_base_url, "https://api.openai.com/v1")

    def test_blank_or_invalid_llm_max_tokens_falls_back_safely(self):
        import importlib
        import paperseek_core.llm as core_llm

        try:
            with temporary_env({"LLM_MAX_TOKENS": ""}):
                config = AgentConfig.from_env()
                reloaded = importlib.reload(core_llm)
                self.assertEqual(config.llm_max_tokens, 2048)
                self.assertEqual(reloaded.DEFAULT_LLM_MAX_TOKENS, 2048)

            with temporary_env({"LLM_MAX_TOKENS": "not-a-number"}):
                config = AgentConfig.from_env()
                reloaded = importlib.reload(core_llm)
                self.assertEqual(config.llm_max_tokens, 2048)
                self.assertEqual(reloaded.DEFAULT_LLM_MAX_TOKENS, 2048)

            with temporary_env({"LLM_MAX_TOKENS": "-1"}):
                config = AgentConfig.from_env()
                reloaded = importlib.reload(core_llm)
                self.assertEqual(config.llm_max_tokens, 0)
                self.assertEqual(reloaded.DEFAULT_LLM_MAX_TOKENS, 0)
        finally:
            importlib.reload(core_llm)

    def test_modelscope_provider_is_available_in_web_ui(self):
        html = read_text("paperseek/static/index.html")
        app_js = read_text("paperseek/static/app.js")
        self.assertIn('value="modelscope"', html)
        self.assertIn("Qwen/Qwen3-235B-A22B-Instruct-2507", app_js)
        self.assertIn("https://api-inference.modelscope.cn/v1", app_js)

    def test_web_ui_exposes_language_switch(self):
        html = read_text("paperseek/static/index.html")
        app_js = read_text("paperseek/static/app.js")
        self.assertIn('data-language="en"', html)
        self.assertIn('data-language="zh"', html)
        self.assertIn("paperseek.ui.language", app_js)
        self.assertIn("开始检索", app_js)
        self.assertIn("高级设置", app_js)

    def test_cstcloud_provider_is_available_in_web_ui(self):
        html = read_text("paperseek/static/index.html")
        app_js = read_text("paperseek/static/app.js")
        self.assertIn('value="cstcloud"', html)
        self.assertIn("deepseek-v4-flash", app_js)
        self.assertIn("https://uni-api.cstcloud.cn/v1", app_js)

    def test_llm_timeout_is_configurable_and_keeps_safe_minimum(self):
        import importlib
        import paperseek_core.llm as core_llm

        try:
            with temporary_env(clear=("LLM_TIMEOUT_SECONDS",)):
                reloaded = importlib.reload(core_llm)
                self.assertEqual(reloaded.DEFAULT_LLM_TIMEOUT_SECONDS, 180)

            with temporary_env({"LLM_TIMEOUT_SECONDS": "240"}):
                reloaded = importlib.reload(core_llm)
                self.assertEqual(reloaded.DEFAULT_LLM_TIMEOUT_SECONDS, 240)

            with temporary_env({"LLM_TIMEOUT_SECONDS": "10"}):
                reloaded = importlib.reload(core_llm)
                self.assertEqual(reloaded.DEFAULT_LLM_TIMEOUT_SECONDS, 30)
        finally:
            importlib.reload(core_llm)


if __name__ == "__main__":
    unittest.main()
