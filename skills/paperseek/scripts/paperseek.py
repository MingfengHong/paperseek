#!/usr/bin/env python3
"""PaperSeek Skill CLI launcher with a self-contained helper fallback."""

from __future__ import annotations

import os
import sys
import importlib.util
from pathlib import Path
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("--install-help", "install-help"):
        print(install_help())
        return 0

    package_main = locate_package_main()
    if package_main is None:
        return run_standalone_helper(argv)

    package_main(argv)
    return 0


def locate_package_main():
    script_dir = Path(__file__).resolve().parent
    project_root = find_project_root(script_dir)

    # Avoid resolving this launcher as a top-level `paperseek.py` module.
    sys.path[:] = [
        item for item in sys.path
        if Path(item or ".").resolve() != script_dir
    ]

    candidate_paths = []
    if project_root:
        candidate_paths.append(project_root)
    env_root = os.environ.get("PAPERSEEK_PROJECT_ROOT")
    if env_root:
        candidate_paths.append(Path(env_root).expanduser())

    for path in candidate_paths:
        resolved = path.resolve()
        if str(resolved) not in sys.path:
            sys.path.insert(0, str(resolved))
        try:
            from paperseek.cli import main as package_main  # type: ignore
            return package_main
        except Exception:
            if str(resolved) in sys.path:
                sys.path.remove(str(resolved))

    try:
        from paperseek.cli import main as package_main  # type: ignore
        return package_main
    except Exception:
        return None


def find_project_root(start: Path) -> Optional[Path]:
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists() and (parent / "paperseek" / "cli.py").exists():
            return parent
    return None


def install_help() -> str:
    return """PaperSeek Skill and package installation

The PaperSeek Skill folder is self-contained for agent guidance, source
metadata, static doctor checks, masked config inspection, and local path lookup.

Real literature search, live smoke checks, and the Web UI still require the
full PaperSeek Python package.

If this Skill is inside the PaperSeek repository:
  python -m pip install -e .
  python skills/paperseek/scripts/paperseek.py doctor

If this Skill was published separately:
  1. Install the PaperSeek Python package from its project repository or package index.
  2. Confirm the command works:

       paperseek --help
       paperseek doctor

  3. If the package source is not on Python's import path, set:

       PAPERSEEK_PROJECT_ROOT=/path/to/paperseek

API keys must be configured through environment variables, `paperseek config`,
or the Web UI session fields. Do not write secrets into Skill files.
"""


def run_standalone_helper(argv: List[str]) -> int:
    script_dir = Path(__file__).resolve().parent
    runtime_path = script_dir / "paperseek_skill_runtime.py"
    spec = importlib.util.spec_from_file_location("paperseek_skill_runtime", runtime_path)
    if spec is None or spec.loader is None:
        print(f"Standalone Skill helper is missing: {runtime_path}", file=sys.stderr)
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.run(argv))


if __name__ == "__main__":
    raise SystemExit(main())
