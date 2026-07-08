import unittest
from unittest.mock import patch

from paperseek.config import (
    AgentConfig,
    SUPPORTED_LLM_PROVIDERS,
    default_api_type,
    default_base_url,
    default_model,
)
from paperseek_core.llm import (
    AnthropicClient,
    OpenAIChatClient,
    OpenAIResponsesClient,
    create_llm_client,
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

    def test_nvidia_provider_defaults(self):
        self.assertIn("nvidia", SUPPORTED_LLM_PROVIDERS)
        self.assertEqual(default_api_type("nvidia"), "openai_chat")
        self.assertEqual(default_model("nvidia"), "nvidia/llama-3.3-nemotron-super-49b-v1.5")
        self.assertEqual(default_base_url("nvidia"), "https://integrate.api.nvidia.com/v1")

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

    def test_default_ranking_concurrency_is_16(self):
        with temporary_env({}, clear=("RANKING_CONCURRENCY",)):
            config = AgentConfig.from_env()

        self.assertEqual(config.ranking_concurrency, 16)

    def test_kimi_coding_openai_chat_disables_thinking_and_forces_supported_temperature(self):
        class FakeResponse:
            status_code = 200
            headers = {}

            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "clean answer"}}]}

        with patch("paperseek_core.llm.requests.post", return_value=FakeResponse()) as post:
            client = OpenAIChatClient("sk-test", model="kimi-for-coding", base_url="https://api.kimi.com/coding/v1")
            self.assertEqual(client.chat([{"role": "user", "content": "ping"}], temperature=0), "clean answer")

        self.assertEqual(post.call_args.args[0], "https://api.kimi.com/coding/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["json"]["temperature"], 0.6)
        self.assertEqual(post.call_args.kwargs["json"]["thinking"], {"type": "disabled"})

    def test_openai_chat_rotates_key_pool_on_retryable_status(self):
        class FakeResponse:
            headers = {}

            def __init__(self, status_code, payload=None, text=""):
                self.status_code = status_code
                self._payload = payload or {}
                self.text = text

            def json(self):
                return self._payload

        calls = []

        def fake_post(url, **kwargs):
            calls.append(kwargs["headers"].get("Authorization"))
            if len(calls) == 1:
                return FakeResponse(429, text='{"status":429}')
            return FakeResponse(200, {"choices": [{"message": {"content": "clean answer"}}]})

        with patch("paperseek_core.llm.requests.post", side_effect=fake_post):
            client = OpenAIChatClient("sk-rotate-a,sk-rotate-b", model="gpt-test", base_url="https://example.test/v1")
            self.assertEqual(client.chat([{"role": "user", "content": "ping"}]), "clean answer")

        self.assertEqual(calls, ["Bearer sk-rotate-a", "Bearer sk-rotate-b"])

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

    def test_nvidia_provider_is_available_in_web_ui(self):
        html = read_text("paperseek/static/index.html")
        app_js = read_text("paperseek/static/app.js")
        self.assertIn('value="nvidia"', html)
        self.assertIn("nvidia/llama-3.3-nemotron-super-49b-v1.5", app_js)
        self.assertIn("nvidia/nv-embedqa-e5-v5", app_js)
        self.assertIn("nv-rerank-qa-mistral-4b:1", app_js)

    def test_openrouter_retrieval_is_available_in_web_ui(self):
        html = read_text("paperseek/static/index.html")
        app_js = read_text("paperseek/static/app.js")
        self.assertIn('value="openrouter"', html)
        self.assertIn("openai/text-embedding-3-small", app_js)
        self.assertIn("jinaai/jina-reranker-v2-base-multilingual", app_js)

    def test_ranking_llm_timeout_defaults_to_preview_safe_value(self):
        with temporary_env(clear=("RANKING_LLM_TIMEOUT_SECONDS",)):
            config = AgentConfig.from_env()
            self.assertEqual(config.ranking_llm_timeout_seconds, 60)

        with temporary_env({"RANKING_LLM_TIMEOUT_SECONDS": "15"}):
            config = AgentConfig.from_env()
            self.assertEqual(config.ranking_llm_timeout_seconds, 15)

        with temporary_env({"RANKING_LLM_TIMEOUT_SECONDS": "2"}):
            config = AgentConfig.from_env()
            self.assertEqual(config.ranking_llm_timeout_seconds, 10)

    def test_create_llm_client_factory(self):
        class MockConfig:
            def __init__(self, api_type=None, max_tokens=None, timeout=None):
                if api_type is not None:
                    self.llm_api_type = api_type
                if max_tokens is not None:
                    self.llm_max_tokens = max_tokens
                if timeout is not None:
                    self.llm_timeout_seconds = timeout
                self.llm_api_key = "test-key"
                self.llm_model = "test-model"
                self.llm_base_url = "https://test.url"

        import paperseek_core.llm as core_llm

        # Test Anthropic
        client = core_llm.create_llm_client(MockConfig(api_type="anthropic_messages"))
        self.assertIsInstance(client, core_llm.AnthropicClient)
        self.assertEqual(client.model, "test-model")

        # Test OpenAI Responses
        client = core_llm.create_llm_client(MockConfig(api_type="openai_responses"))
        self.assertIsInstance(client, core_llm.OpenAIResponsesClient)

        # Test default fallback (OpenAI Chat)
        client = core_llm.create_llm_client(MockConfig(api_type="unknown"))
        self.assertIsInstance(client, core_llm.OpenAIChatClient)

        client = core_llm.create_llm_client(MockConfig(api_type=""))
        self.assertIsInstance(client, core_llm.OpenAIChatClient)

        client = core_llm.create_llm_client(MockConfig())
        self.assertIsInstance(client, core_llm.OpenAIChatClient)

        # Test default config attribute missing
        client = core_llm.create_llm_client(MockConfig(api_type="anthropic_messages"))
        self.assertEqual(client.max_tokens, core_llm.DEFAULT_LLM_MAX_TOKENS)
        self.assertEqual(client.timeout_seconds, core_llm.DEFAULT_LLM_TIMEOUT_SECONDS)

        # Test values are passed through
        client = core_llm.create_llm_client(MockConfig(api_type="openai_responses", max_tokens=100, timeout=50))
        self.assertEqual(client.max_tokens, 100)
        self.assertEqual(client.timeout_seconds, 50)


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
