from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingTest(unittest.TestCase):
    def test_project_metadata_is_release_ready(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('name = "paperseek"', pyproject)
        self.assertIn('version = "0.1.0"', pyproject)
        self.assertIn('Homepage = "https://www.paperseek.xyz/"', pyproject)
        self.assertIn('Online-Demo = "https://www.paperseek.xyz/"', pyproject)
        self.assertIn('Repository = "https://github.com/MingfengHong/paperseek"', pyproject)
        self.assertIn('Documentation = "https://mingfenghong.github.io/paperseek/"', pyproject)
        self.assertNotIn("modelscope.cn/studios", pyproject)
        self.assertNotRegex(pyproject, re.compile(r"^wos-search\s*=", re.MULTILINE))
        self.assertNotRegex(pyproject, re.compile(r"^wos-search-web\s*=", re.MULTILINE))

    def test_readme_uses_repository_url_and_docs_asset_screenshot(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertFalse(readme.startswith("---\n"))
        self.assertNotIn("<repo-url>", readme)
        self.assertIn("https://github.com/MingfengHong/paperseek", readme)
        self.assertIn("docs/assets/paperseek-web.png", readme)
        self.assertIn("docs/user-manual.md", readme)
        self.assertIn("docs/deployment.md", readme)
        self.assertIn("docs/online-demo.md", readme)
        self.assertIn("[English](README.en.md)", readme)
        self.assertIn("https://www.paperseek.xyz/", readme)
        self.assertNotIn("https://modelscope.cn/studios/HongMingfeng/paperseek", readme)
        self.assertNotIn("img.shields.io/badge/OpenAlex", readme)
        self.assertNotIn("img.shields.io/badge/Crossref", readme)

    def test_english_readme_exists_and_links_back_to_chinese(self):
        readme = (ROOT / "README.en.md").read_text(encoding="utf-8")
        self.assertIn("[简体中文](README.md)", readme)
        self.assertIn("https://github.com/MingfengHong/paperseek", readme)
        self.assertIn("docs/assets/paperseek-web.png", readme)
        self.assertIn("docs/online-demo.md", readme)
        self.assertIn("Docker / Vercel deployment", readme)
        self.assertIn("https://www.paperseek.xyz/", readme)
        self.assertNotIn("https://modelscope.cn/studios/HongMingfeng/paperseek", readme)
        self.assertIn("PaperSeek is licensed under the [Apache License 2.0](LICENSE).", readme)

    def test_readmes_acknowledge_reference_projects(self):
        expected_links = (
            "https://github.com/dr-dumpling/paper-search-cli/",
            "https://github.com/666ghj/MiroFish",
            "https://github.com/clarivate/wosstarter_python_client",
            "https://github.com/Lloyd-Jahn/openclaw-paper-search",
        )
        zh_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        en_readme = (ROOT / "README.en.md").read_text(encoding="utf-8")
        for link in expected_links:
            self.assertIn(link, zh_readme)
            self.assertIn(link, en_readme)

    def test_user_manual_exists_and_covers_main_user_workflows(self):
        manual = (ROOT / "docs" / "user-manual.md").read_text(encoding="utf-8")
        for heading in (
            "## Get started",
            "## Install",
            "## Configuration",
            "## Models",
            "## Data sources",
            "## CLI",
            "## Web UI",
            "## Deployment",
            "## Agent Skill",
            "## Diagnostics and troubleshooting",
        ):
            self.assertIn(heading, manual)

    def test_online_demo_guide_exists(self):
        guide = (ROOT / "docs" / "online-demo.md").read_text(encoding="utf-8")
        self.assertIn("https://www.paperseek.xyz/", guide)
        self.assertIn("ModelScope", guide)
        self.assertIn("API Inference", guide)
        self.assertIn("历史记录按登录账号隔离", guide)

    def test_vitepress_docs_site_exists(self):
        config = (ROOT / "docs" / ".vitepress" / "config.mts").read_text(encoding="utf-8")
        package = (ROOT / "package.json").read_text(encoding="utf-8")
        banner = (ROOT / "docs" / "public" / "README.md").read_text(encoding="utf-8")
        self.assertIn("defineConfig", config)
        self.assertIn("docs:build", package)
        self.assertIn("This branch is generated for GitHub Pages. Do not develop here.", banner)

    def test_deployment_files_exist(self):
        for path in (
            "Dockerfile",
            ".dockerignore",
            "docker-compose.yml",
            "app.py",
            "api/index.py",
            "vercel.json",
            "docs/deployment.md",
        ):
            self.assertTrue((ROOT / path).exists(), path)


if __name__ == "__main__":
    unittest.main()
