from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable, List


CONFIG_KEYS = {
    "DATA_SOURCE",
    "WOS_API_KEY",
    "OPENALEX_API_KEY",
    "OPENALEX_EMAIL",
    "CROSSREF_EMAIL",
    "SEMANTIC_SCHOLAR_API_KEY",
    "PUBMED_API_KEY",
    "PUBMED_EMAIL",
    "PUBMED_TOOL",
    "LLM_API_KEY",
    "LLM_PROVIDER",
    "LLM_API_TYPE",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "WOS_DB",
    "SEARCH_FIELD",
    "DISCIPLINE_FIELDS",
    "EXPAND_CITATIONS",
    "FETCH_ABSTRACTS",
    "TARGET_MIN",
    "TARGET_MAX",
    "MAX_ITERATIONS",
    "CITATION_SEED_COUNT",
    "CITATION_PER_SEED",
    "CITATION_MAX_RECORDS",
    "RETRIEVAL_POOL_MAX",
    "RETRIEVAL_POOL_MIN",
    "RETRIEVAL_LANE_LIMIT",
    "RETRIEVAL_RRF_K",
    "RETRIEVAL_EMBEDDING_PROVIDER",
    "RETRIEVAL_EMBEDDING_MODEL",
    "RETRIEVAL_EMBEDDING_BASE_URL",
    "RETRIEVAL_EMBEDDING_API_KEY",
    "RETRIEVAL_RERANKER_PROVIDER",
    "RETRIEVAL_RERANKER_MODEL",
    "RETRIEVAL_RERANKER_BASE_URL",
    "RETRIEVAL_RERANKER_API_KEY",
    "RETRIEVAL_CROSSREF_ENRICHMENT",
}

APPLIED_FROM_USER_CONFIG = set()


def config_path() -> Path:
    explicit = os.environ.get("PAPERSEEK_CONFIG_FILE")
    if explicit:
        return Path(explicit).expanduser()
    directory = Path(os.environ.get("PAPERSEEK_CONFIG_DIR", Path.home() / ".config" / "paperseek")).expanduser()
    return directory / "config.json"


def read_config() -> Dict[str, str]:
    path = config_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid PaperSeek config file: {path}")
    return {str(key): str(value) for key, value in data.items() if key in CONFIG_KEYS and value is not None}


def write_config(config: Dict[str, str]) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = {key: str(value) for key, value in sorted(config.items()) if key in CONFIG_KEYS and value is not None}
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load_user_config_into_env() -> List[str]:
    applied: List[str] = []
    for key, value in read_config().items():
        if os.environ.get(key):
            continue
        os.environ[key] = value
        APPLIED_FROM_USER_CONFIG.add(key)
        applied.append(key)
    return applied


def set_config_value(key: str, value: str) -> Dict[str, str]:
    assert_config_key(key)
    config = read_config()
    config[key] = value
    write_config(config)
    return config


def unset_config_value(key: str) -> Dict[str, str]:
    assert_config_key(key)
    config = read_config()
    config.pop(key, None)
    write_config(config)
    return config


def list_config_entries(include_missing: bool = False) -> List[Dict[str, object]]:
    stored = read_config()
    entries = []
    for key in sorted(CONFIG_KEYS):
        value = os.environ.get(key) or stored.get(key, "")
        if not value and not include_missing:
            continue
        if os.environ.get(key):
            source = "environment" if key not in APPLIED_FROM_USER_CONFIG else "user_config"
        elif stored.get(key):
            source = "user_config"
        else:
            source = "missing"
        entries.append({
            "key": key,
            "configured": bool(value),
            "source": source,
            "value": mask_value(key, value) if value else "",
        })
    return entries


def import_env_file(path: str) -> List[str]:
    env_path = Path(path).expanduser()
    if not env_path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")
    config = read_config()
    imported: List[str] = []
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in CONFIG_KEYS:
            config[key] = value
            imported.append(key)
    write_config(config)
    return imported


def mask_value(key: str, value: str) -> str:
    if not value:
        return ""
    if "EMAIL" in key or "@" in value:
        name, _, domain = value.partition("@")
        return f"{name[:2]}***@{domain}" if domain else "***"
    if "KEY" in key or "TOKEN" in key or "SECRET" in key:
        return "***" if len(value) <= 8 else f"{value[:4]}...{value[-4:]}"
    if len(value) > 80:
        return value[:40] + "..." + value[-12:]
    return value


def assert_config_key(key: str) -> None:
    if key not in CONFIG_KEYS:
        supported = ", ".join(sorted(CONFIG_KEYS))
        raise ValueError(f"Unsupported config key: {key}. Supported keys: {supported}.")


def supported_config_keys() -> Iterable[str]:
    return sorted(CONFIG_KEYS)
