import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeploymentTest(unittest.TestCase):
    def test_vercel_config_uses_fastapi_auto_detection(self):
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["$schema"], "https://openapi.vercel.sh/vercel.json")
        self.assertNotIn("functions", config)
        self.assertNotIn("rewrites", config)

    def test_vercel_root_app_exposes_fastapi_app(self):
        spec = importlib.util.spec_from_file_location("paperseek_vercel_root_app", ROOT / "app.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.app.title, "PaperSeek")

    def test_vercel_entrypoint_exposes_fastapi_app(self):
        spec = importlib.util.spec_from_file_location("paperseek_vercel_entrypoint", ROOT / "api" / "index.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.app.title, "PaperSeek")

    def test_dockerfile_runs_web_app_on_container_port(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("EXPOSE 7860", dockerfile)
        self.assertIn("PORT=7860", dockerfile)
        self.assertIn("--shell /bin/sh paperseek", dockerfile)
        self.assertIn("--host 0.0.0.0", dockerfile)
        self.assertIn("${PORT:-7860}", dockerfile)
        self.assertIn("HEALTHCHECK", dockerfile)

    def test_dockerfile_copies_runtime_packages(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY paperseek ./paperseek", dockerfile)
        self.assertIn("COPY paperseek_core ./paperseek_core", dockerfile)

    def test_compose_exposes_configurable_host_port(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("${PAPERSEEK_PORT:-8765}:${PAPERSEEK_CONTAINER_PORT:-7860}", compose)
        self.assertIn("PORT: ${PAPERSEEK_CONTAINER_PORT:-7860}", compose)
        self.assertIn("LLM_PROVIDER", compose)
        self.assertIn("OPENALEX_API_KEY", compose)

    def test_modelscope_deploy_config_uses_docker_port(self):
        config = json.loads((ROOT / "ms_deploy.json").read_text(encoding="utf-8"))
        self.assertEqual(config["sdk_type"], "docker")
        self.assertEqual(config["port"], 7860)
        self.assertEqual(config["resource_configuration"], "platform/2v-cpu-16g-mem")

    def test_github_community_standard_files_exist(self):
        self.assertTrue((ROOT / "CODE_OF_CONDUCT.md").exists())
        self.assertTrue((ROOT / ".github" / "pull_request_template.md").exists())
        self.assertTrue((ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").exists())
        self.assertTrue((ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml").exists())

        code_of_conduct = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")
        pr_template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        bug_template = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").read_text(encoding="utf-8")
        self.assertIn("Reporting", code_of_conduct)
        self.assertIn("## Tests", pr_template)
        self.assertIn("Bug report", bug_template)


if __name__ == "__main__":
    unittest.main()
