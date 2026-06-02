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
        self.assertNotIn("<repo-url>", readme)
        self.assertIn("https://github.com/MingfengHong/paperseek", readme)
        self.assertIn("docs/assets/paperseek-web.png", readme)
        self.assertIn("docs/user-manual.md", readme)
        self.assertNotIn("img.shields.io/badge/OpenAlex", readme)
        self.assertNotIn("img.shields.io/badge/Crossref", readme)

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
            "## Agent Skill",
            "## Diagnostics and troubleshooting",
        ):
            self.assertIn(heading, manual)


if __name__ == "__main__":
    unittest.main()
