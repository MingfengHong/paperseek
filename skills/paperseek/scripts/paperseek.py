#!/usr/bin/env python3
"""
PaperSeek Skill CLI launcher.

This script intentionally does not reimplement PaperSeek. It locates and runs
the full `paperseek` Python package so a standalone Skill distribution can keep
one stable script entrypoint while preserving the complete CLI/Web/source logic
in the package itself.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("--install-help", "install-help"):
        print(install_help())
        return 0

    package_main = locate_package_main()
    if package_main is None:
        print(missing_package_message(), file=sys.stderr)
        return 2

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
    return """PaperSeek package installation

The PaperSeek Skill script is a launcher for the full PaperSeek Python package.
It does not vendor a partial CLI implementation.

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


def missing_package_message() -> str:
    return (
        "The full PaperSeek Python package is not importable. "
        "This Skill script intentionally does not provide a reduced fallback CLI.\n\n"
        + install_help()
    )


if __name__ == "__main__":
    raise SystemExit(main())
