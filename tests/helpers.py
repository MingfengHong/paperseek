from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

CONFIG_ENV_KEYS = (
    "DATA_SOURCE",
    "WOS_API_KEY",
    "OPENALEX_API_KEY",
    "OPENALEX_EMAIL",
    "CROSSREF_EMAIL",
    "SEMANTIC_SCHOLAR_API_KEY",
    "PUBMED_API_KEY",
    "PUBMED_EMAIL",
    "PUBMED_TOOL",
    "SERPER_API_KEY",
    "SERPER_API_KEYS",
    "LLM_API_KEY",
    "LLM_PROVIDER",
    "LLM_API_TYPE",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "RANKING_CANDIDATE_LIMIT",
    "DISCIPLINE_FIELDS",
)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def read_json(relative_path: str):
    return json.loads(read_text(relative_path))


def assert_contains_all(testcase, text: str, expected: tuple[str, ...] | list[str]) -> None:
    for item in expected:
        with testcase.subTest(item=item):
            testcase.assertIn(item, text)


@contextmanager
def temporary_env(values: dict[str, str] | None = None, *, clear: tuple[str, ...] | list[str] = ()):
    keys = set(clear)
    if values:
        keys.update(values)
    previous = {key: os.environ.get(key) for key in keys}
    try:
        for key in clear:
            os.environ.pop(key, None)
        if values:
            os.environ.update(values)
        yield
    finally:
        for key, value in previous.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value


def run_cli(*args: str, env: dict[str, str] | None = None, cwd=None) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    merged_env["PYTHONIOENCODING"] = "utf-8"
    python_path = [str(ROOT)]
    if merged_env.get("PYTHONPATH"):
        python_path.append(merged_env["PYTHONPATH"])
    merged_env["PYTHONPATH"] = os.pathsep.join(python_path)
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "paperseek.cli", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=merged_env,
        cwd=cwd,
    )
