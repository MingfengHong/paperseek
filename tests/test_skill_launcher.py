import json
import subprocess
import sys
import unittest


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
        self.assertIn("PaperSeek package installation", result.stdout)
        self.assertIn("python -m pip install -e .", result.stdout)


if __name__ == "__main__":
    unittest.main()
