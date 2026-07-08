import os
from pathlib import Path
from typing import Iterable, List, Optional, Union, Tuple


def load_env_file(path: Optional[Union[Path, str]] = None, *, override: bool = False) -> List[str]:
    """Load simple KEY=VALUE pairs from a .env file into os.environ."""
    if os.environ.get("PAPERSEEK_DOTENV_DISABLED", "").lower() in ("1", "true", "yes", "on"):
        return []
    paths = [_normalize_path(path)] if path else _default_env_paths()
    applied: List[str] = []
    seen = set()
    for env_path in paths:
        if env_path in seen or not env_path.exists():
            continue
        seen.add(env_path)
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(raw_line)
            if parsed is None:
                continue
            key, value = parsed
            if not override and os.environ.get(key):
                continue
            os.environ[key] = value
            applied.append(key)
    return applied


def _default_env_paths() -> Iterable[Path]:
    package_root = Path(__file__).resolve().parents[1]
    yield Path.cwd() / ".env"
    yield package_root / ".env"


def _normalize_path(path: Union[Path, str]) -> Path:
    return Path(path).expanduser().resolve()


def _parse_env_line(raw_line: str) -> Optional[Tuple[str, str]]:
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    if line.startswith("export "):
        line = line[len("export "):].strip()
    key, value = line.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value
