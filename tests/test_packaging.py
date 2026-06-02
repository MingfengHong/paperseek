from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingTest(unittest.TestCase):
    def test_project_metadata_is_release_ready(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('name = "paperseek"', pyproject)
        self.assertIn('version = "0.1.0"', pyproject)
        self.assertIn('Homepage = "https://paperseek.top"', pyproject)
        self.assertIn('Repository = "https://github.com/MingfengHong/paperseek"', pyproject)
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
        self.assertIn("[English](README.en.md)", readme)
        self.assertNotIn("img.shields.io/badge/OpenAlex", readme)
        self.assertNotIn("img.shields.io/badge/Crossref", readme)

    def test_english_readme_exists_and_links_back_to_chinese(self):
        readme = (ROOT / "README.en.md").read_text(encoding="utf-8")
        self.assertIn("[简体中文](README.md)", readme)
        self.assertIn("https://github.com/MingfengHong/paperseek", readme)
        self.assertIn("docs/assets/paperseek-web.png", readme)
        self.assertIn("Docker, Vercel, and ModelScope", readme)
        self.assertIn("PaperSeek is licensed under the [Apache License 2.0](LICENSE).", readme)

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

    def test_deployment_files_exist(self):
        for path in (
            "Dockerfile",
            ".dockerignore",
            "docker-compose.yml",
            "api/index.py",
            "vercel.json",
            "docs/deployment.md",
        ):
            self.assertTrue((ROOT / path).exists(), path)


if __name__ == "__main__":
    unittest.main()
