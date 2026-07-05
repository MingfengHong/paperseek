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


SOURCE_IDS = ["openalex", "arxiv", "semanticscholar", "pubmed", "googlescholar", "paperhub", "crossref", "wos"]


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
        self.assertEqual([item["id"] for item in payload["sources"]], SOURCE_IDS)

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
        self.assertEqual([item["id"] for item in payload["sources"]], SOURCE_IDS)

    def test_standalone_fetches_new_sources_with_standard_library(self):
        runtime = self._load_runtime()

        def fake_http_json(url, method="GET", headers=None, payload=None):
            if "semanticscholar.org" in url:
                return {"total": 1, "data": [{"paperId": "S2", "title": "Graph Learning", "year": 2024, "authors": [{"name": "Ada"}]}]}
            if "esearch.fcgi" in url:
                return {"esearchresult": {"count": "1", "idlist": ["123"]}}
            if "esummary.fcgi" in url:
                return {"result": {"123": {"title": "Cancer Immunotherapy", "uid": "123", "pubdate": "2024", "authors": [{"name": "Lin"}]}}}
            if "google.serper.dev/scholar" in url:
                self.assertEqual(method, "POST")
                self.assertEqual(headers["X-API-KEY"], "serper-test")
                self.assertEqual(payload["q"], "graph retrieval")
                self.assertEqual(payload["page"], 1)
                self.assertNotIn("num", payload)
                return {"organic": [{"id": "gs1", "title": "Graph Scholar Retrieval", "year": 2025, "snippet": "Scholar result.", "link": "https://example.org/gs", "citedBy": {"total": 3}}]}
            if "manifest.json" in url:
                return {"shards": [{"file": "shards/iclr-2025.fake.json"}]}
            if "iclr-2025.fake.json" in url:
                return {"papers": [{"id": "p1", "title": "Graph Neural Retrieval", "authors": ["Ada"], "conference": "ICLR", "year": 2025, "abstract": "retrieval with graphs"}]}
            raise AssertionError(url)

        def fake_http_text(url, method="GET", headers=None, payload=None):
            if "export.arxiv.org" in url:
                return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Graph Retrieval</title>
    <summary>Graph retrieval abstract.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <link href="http://arxiv.org/abs/2401.00001v1" rel="alternate"/>
    <link href="http://arxiv.org/pdf/2401.00001v1" title="pdf" type="application/pdf"/>
    <arxiv:primary_category term="cs.IR"/>
  </entry>
</feed>"""
            if "efetch.fcgi" in url:
                return """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><Abstract><AbstractText>PubMed abstract.</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
            raise AssertionError(url)

        runtime.http_json = fake_http_json
        runtime.http_text = fake_http_text
        runtime.PAPERHUB_CACHE = None

        for source in ("arxiv", "semanticscholar", "pubmed", "googlescholar", "paperhub"):
            config = {"SERPER_API_KEY": "serper-test"} if source == "googlescholar" else {}
            records, total, used_query = runtime.fetch_source(source, "graph retrieval", 2, config, [])
            self.assertEqual(total, 1, source)
            self.assertEqual(len(records), 1, source)
            self.assertEqual(records[0]["source"], source)
            self.assertTrue(used_query)

    def test_standalone_google_scholar_rotates_serper_keys(self):
        runtime = self._load_runtime()
        seen_keys = []

        def fake_http_json(url, method="GET", headers=None, payload=None):
            self.assertIn("google.serper.dev/scholar", url)
            seen_keys.append(headers["X-API-KEY"])
            if headers["X-API-KEY"] == "bad-key":
                raise RuntimeError("HTTP 403 from Serper")
            return {"organic": [{"id": "gs1", "title": "Recovered Scholar Result", "publicationInfo": {"authors": "not-a-list"}}]}

        runtime.http_json = fake_http_json

        records, total, _ = runtime.fetch_google_scholar(
            "AI governance",
            5,
            {"SERPER_API_KEYS": "bad-key; good-key"},
        )

        self.assertEqual(seen_keys, ["bad-key", "good-key"])
        self.assertEqual(total, 1)
        self.assertEqual(records[0]["title"], "Recovered Scholar Result")
        self.assertEqual(records[0]["authors"], [])

    def test_standalone_google_scholar_cleans_summary_metadata(self):
        runtime = self._load_runtime()

        def fake_http_json(url, method="GET", headers=None, payload=None):
            self.assertIn("google.serper.dev/scholar", url)
            return {
                "organic": [
                    {
                        "id": "gs-clean",
                        "title": "Digital\u9225\u63dceal Economy Integration",
                        "snippet": "\u9225?, resource allocation and industrial innovation \u9225?",
                        "publicationInfo": {
                            "summary": "Y Feng, Y Gao, L Yang\u9225? - Resources Policy, 2024 - Elsevier",
                        },
                        "citedBy": {"cites": 41},
                    }
                ]
            }

        runtime.http_json = fake_http_json

        records, total, _ = runtime.fetch_google_scholar("digital economy", 1, {"SERPER_API_KEY": "key"})

        self.assertEqual(total, 1)
        self.assertEqual(records[0]["title"], "Digital\u2013Real Economy Integration")
        self.assertEqual(records[0]["authors"], ["Y Feng", "Y Gao", "L Yang"])
        self.assertEqual(records[0]["venue"], "Resources Policy")
        self.assertEqual(records[0]["year"], 2024)
        self.assertEqual(records[0]["abstract"], "resource allocation and industrial innovation")
        self.assertEqual(records[0]["citation_count"], 41)

    def test_standalone_arxiv_query_escapes_quotes(self):
        runtime = self._load_runtime()
        self.assertEqual(
            runtime.arxiv_query('graph "neural" retrieval'),
            'all:"graph \\"neural\\" retrieval"',
        )

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

    def test_standalone_wos_omits_unsupported_wc_terms(self):
        runtime = self._load_runtime()
        captured = {}

        def fake_http_json(url, method="GET", headers=None, payload=None):
            captured["url"] = unquote_plus(url)
            captured["headers"] = headers or {}
            return {"hits": [], "metadata": {"total": 0}}

        runtime.http_json = fake_http_json
        records, total, query = runtime.fetch_wos(
            "(TS=(open innovation)) AND WC=(Management)",
            1,
            {"WOS_API_KEY": "wos-key", "WOS_DB": "WOS"},
            ["14", "17"],
        )
        self.assertEqual(records, [])
        self.assertEqual(total, 0)
        self.assertEqual(query, "(TS=(open innovation))")
        self.assertIn("q=(TS=(open innovation))", captured["url"])
        self.assertIn("sortField=RS+D", captured["url"])
        self.assertNotIn("WC=", captured["url"])
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
