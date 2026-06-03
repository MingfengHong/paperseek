import unittest
from pathlib import Path

from paperseek.config import (
    SUPPORTED_LLM_PROVIDERS,
    default_api_type,
    default_base_url,
    default_model,
)


ROOT = Path(__file__).resolve().parents[1]


class LLMProviderTest(unittest.TestCase):
    def test_modelscope_provider_defaults(self):
        self.assertIn("modelscope", SUPPORTED_LLM_PROVIDERS)
        self.assertEqual(default_api_type("modelscope"), "openai_chat")
        self.assertEqual(default_model("modelscope"), "Qwen/Qwen3-235B-A22B-Instruct-2507")
        self.assertEqual(default_base_url("modelscope"), "https://api-inference.modelscope.cn/v1")

    def test_cstcloud_provider_defaults(self):
        self.assertIn("cstcloud", SUPPORTED_LLM_PROVIDERS)
        self.assertEqual(default_api_type("cstcloud"), "openai_chat")
        self.assertEqual(default_model("cstcloud"), "DeepSeek-V4-Flash")
        self.assertEqual(default_base_url("cstcloud"), "https://uni-api.cstcloud.cn/v1")

    def test_modelscope_provider_is_available_in_web_ui(self):
        html = (ROOT / "paperseek" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "paperseek" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('value="modelscope"', html)
        self.assertIn("Qwen/Qwen3-235B-A22B-Instruct-2507", app_js)
        self.assertIn("https://api-inference.modelscope.cn/v1", app_js)

    def test_cstcloud_provider_is_available_in_web_ui(self):
        html = (ROOT / "paperseek" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "paperseek" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('value="cstcloud"', html)
        self.assertIn("DeepSeek-V4-Flash", app_js)
        self.assertIn("https://uni-api.cstcloud.cn/v1", app_js)


if __name__ == "__main__":
    unittest.main()
