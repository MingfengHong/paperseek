import importlib.util
import unittest

from tests.helpers import ROOT, read_json, read_text


class DeploymentTest(unittest.TestCase):
    def test_vercel_config_uses_fastapi_auto_detection(self):
        config = read_json("vercel.json")
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
        dockerfile = read_text("Dockerfile")
        self.assertIn("EXPOSE 7860", dockerfile)
        self.assertIn("PORT=7860", dockerfile)
        self.assertIn("--shell /bin/sh paperseek", dockerfile)
        self.assertIn("--host 0.0.0.0", dockerfile)
        self.assertIn("${PORT:-7860}", dockerfile)
        self.assertIn("HEALTHCHECK", dockerfile)

    def test_dockerfile_copies_runtime_packages(self):
        dockerfile = read_text("Dockerfile")
        self.assertIn("COPY paperseek ./paperseek", dockerfile)
        self.assertIn("COPY paperseek_core ./paperseek_core", dockerfile)

    def test_compose_exposes_configurable_host_port(self):
        compose = read_text("docker-compose.yml")
        self.assertIn("${PAPERSEEK_PORT:-8765}:${PAPERSEEK_CONTAINER_PORT:-7860}", compose)
        self.assertIn("PORT: ${PAPERSEEK_CONTAINER_PORT:-7860}", compose)
        self.assertIn("env_file:", compose)
        self.assertIn("path: .env", compose)
        self.assertIn("required: false", compose)
        self.assertIn("LLM_PROVIDER: ${LLM_PROVIDER}", compose)
        self.assertIn("LLM_API_KEY: ${LLM_API_KEY}", compose)
        self.assertIn("OPENALEX_API_KEY: ${OPENALEX_API_KEY}", compose)
        self.assertIn("DISCIPLINE_FIELDS: ${DISCIPLINE_FIELDS}", compose)

    def test_modelscope_deploy_config_uses_docker_port(self):
        config = read_json("ms_deploy.json")
        self.assertEqual(config["sdk_type"], "docker")
        self.assertEqual(config["port"], 7860)
        self.assertEqual(config["resource_configuration"], "platform/2v-cpu-16g-mem")

    def test_github_community_standard_files_exist(self):
        required_files = [
            "CODE_OF_CONDUCT.md",
            ".github/pull_request_template.md",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/feature_request.yml",
            ".github/ISSUE_TEMPLATE/config.yml",
        ]
        for relative_path in required_files:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())


if __name__ == "__main__":
    unittest.main()
