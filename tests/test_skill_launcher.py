import json
import os
from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote_plus

from tests.helpers import ROOT, read_text


class SkillLauncherTest(unittest.TestCase):
    def test_launcher_delegates_to_full_package(self):
        result = subprocess.run(
            [sys.executable, "skills/paperseek/scripts/paperseek.py", "sources", "--json"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual([item["id"] for item in payload["sources"]], ["openalex", "crossref", "wos"])

    def test_launcher_install_help_is_available(self):
        result = subprocess.run(
            [sys.executable, "skills/paperseek/scripts/paperseek.py", "--install-help"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PaperSeek Skill and package installation", result.stdout)
        self.assertIn("python -m pip install -e .", result.stdout)

    def test_standalone_skill_sources_without_installed_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "paperseek"
            shutil.copytree(ROOT / "skills" / "paperseek", skill_dir)
            result = subprocess.run(
                [sys.executable, "-S", str(skill_dir / "scripts" / "paperseek.py"), "sources", "--json"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=tmp,
                env=self._standalone_env(tmp),
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["runtime"], "standalone_skill")
        self.assertEqual([item["id"] for item in payload["sources"]], ["openalex", "crossref", "wos"])

    def test_standalone_skill_doctor_without_installed_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "paperseek"
            shutil.copytree(ROOT / "skills" / "paperseek", skill_dir)
            result = subprocess.run(
                [sys.executable, "-S", str(skill_dir / "scripts" / "paperseek.py"), "doctor", "--json"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=tmp,
                env=self._standalone_env(tmp),
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["runtime"], "standalone_skill")
        self.assertIn(payload["status"], {"pass", "warning"})
        self.assertTrue(any(check["id"] == "source.supported" for check in payload["checks"]))

    def test_standalone_skill_search_help_is_self_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "paperseek"
            shutil.copytree(ROOT / "skills" / "paperseek", skill_dir)
            result = subprocess.run(
                [sys.executable, "-S", str(skill_dir / "scripts" / "paperseek.py"), "--help"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=tmp,
                env=self._standalone_env(tmp),
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PaperSeek Skill standalone runtime", result.stdout)
        self.assertIn("search \"QUESTION\"", result.stdout)

    def test_standalone_anthropic_uses_x_api_key_header(self):
        runtime = self._load_runtime()
        captured = {}

        def fake_http_json(url, method="GET", headers=None, payload=None):
            captured["url"] = url
            captured["headers"] = headers or {}
            captured["payload"] = payload or {}
            return {"content": [{"text": "ok"}]}

        runtime.http_json = fake_http_json
        text = runtime.llm_complete(
            "hello",
            {
                "LLM_API_KEY": "anthropic-key",
                "LLM_API_TYPE": "anthropic_messages",
                "LLM_MODEL": "claude-test",
                "LLM_BASE_URL": "https://api.anthropic.com",
            },
        )
        self.assertEqual(text, "ok")
        self.assertEqual(captured["headers"]["x-api-key"], "anthropic-key")
        self.assertEqual(captured["headers"]["anthropic-version"], "2023-06-01")
        self.assertNotIn("Authorization", captured["headers"])
        self.assertTrue(captured["url"].endswith("/v1/messages"))

    def test_standalone_wos_quotes_category_terms(self):
        runtime = self._load_runtime()
        captured = {}

        def fake_http_json(url, method="GET", headers=None, payload=None):
            captured["url"] = unquote_plus(url)
            captured["headers"] = headers or {}
            return {"hits": [], "metadata": {"total": 0}}

        runtime.http_json = fake_http_json
        records, total, query = runtime.fetch_wos(
            "open innovation",
            1,
            {"WOS_API_KEY": "wos-key", "WOS_DB": "WOS"},
            ["14", "17"],
        )
        self.assertEqual(records, [])
        self.assertEqual(total, 0)
        self.assertIn('WC=("Management" OR "Business" OR "Business, Finance"', query)
        self.assertIn('"Computer Science, Artificial Intelligence"', query)
        self.assertIn('q=(TS=(open innovation)) AND WC=("Management"', captured["url"])
        self.assertEqual(captured["headers"]["X-ApiKey"], "wos-key")

    def test_skill_readme_documents_current_layout(self):
        readme = read_text("skills/README.md")
        self.assertIn("scripts/", readme)
        self.assertIn("paperseek.py", readme)
        self.assertIn("paperseek_skill_runtime.py", readme)
        self.assertIn("不安装 PaperSeek Python 包也可以运行", readme)

    def _standalone_env(self, tmp):
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PAPERSEEK_PROJECT_ROOT", None)
        env["PAPERSEEK_CONFIG_DIR"] = str(Path(tmp) / "config")
        env["PAPERSEEK_DATA_DIR"] = str(Path(tmp) / "data")
        env["LLM_PROVIDER"] = "ollama"
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def _load_runtime(self):
        runtime_path = ROOT / "skills" / "paperseek" / "scripts" / "paperseek_skill_runtime.py"
        spec = importlib.util.spec_from_file_location("paperseek_skill_runtime_test", runtime_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


if __name__ == "__main__":
    unittest.main()
