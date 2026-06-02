from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from paperseek.client import ApiClient, ApiException, Configuration, DocumentsApi
from paperseek.config import SUPPORTED_LLM_API_TYPES, SUPPORTED_LLM_PROVIDERS, AgentConfig, default_api_type
from paperseek.providers import CrossrefProvider, OpenAlexProvider, ProviderError
from paperseek.source_metadata import get_source_metadata, list_source_metadata, require_source_metadata


@dataclass
class DiagnosticCheck:
    id: str
    status: str
    severity: str
    summary: str
    actions: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in ("pass", "info", "skip")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["ok"] = self.ok
        return data


def run_doctor(config: AgentConfig) -> Dict[str, Any]:
    source = (config.data_source or "openalex").lower()
    provider = (config.llm_provider or "openai").lower()
    api_type = (config.llm_api_type or default_api_type(provider)).lower()
    checks: List[DiagnosticCheck] = []

    metadata = get_source_metadata(source)
    if metadata:
        checks.append(DiagnosticCheck(
            id="source.supported",
            status="pass",
            severity="info",
            summary=f"Data source '{source}' is registered as {metadata.display_name}.",
            details={"source": metadata.to_dict()},
        ))
        if metadata.status == "temporarily_unavailable":
            checks.append(DiagnosticCheck(
                id="source.status",
                status="warning",
                severity="warning",
                summary=f"{metadata.display_name} is marked temporarily unavailable in this UI.",
                actions=["Use OpenAlex while Clarivate API availability or entitlement is being verified."],
            ))
    else:
        checks.append(DiagnosticCheck(
            id="source.supported",
            status="fail",
            severity="error",
            summary=f"Unsupported data source: {source}.",
            actions=["Run `paperseek sources` to list supported data sources."],
        ))

    if source == "wos" and not config.wos_api_key:
        checks.append(DiagnosticCheck(
            id="source.wos_key",
            status="fail",
            severity="error",
            summary="WOS_API_KEY is required for Web of Science Starter searches.",
            actions=["Set WOS_API_KEY, pass --wos-key, or choose OpenAlex/Crossref."],
        ))
    elif source == "openalex" and not config.openalex_api_key:
        checks.append(DiagnosticCheck(
            id="source.openalex_key",
            status="warning",
            severity="warning",
            summary="OPENALEX_API_KEY is not configured.",
            actions=["Configure OPENALEX_API_KEY for stable OpenAlex usage and higher practical limits."],
        ))
    elif source == "crossref" and not config.crossref_email:
        checks.append(DiagnosticCheck(
            id="source.crossref_email",
            status="warning",
            severity="warning",
            summary="CROSSREF_EMAIL is not configured.",
            actions=["Set CROSSREF_EMAIL so Crossref requests enter the polite pool."],
        ))
    else:
        checks.append(DiagnosticCheck(
            id="source.credentials",
            status="pass",
            severity="info",
            summary="Source-specific required configuration is present or not required.",
        ))

    if provider not in SUPPORTED_LLM_PROVIDERS:
        checks.append(DiagnosticCheck(
            id="llm.provider",
            status="fail",
            severity="error",
            summary=f"Unsupported LLM provider: {provider}.",
            actions=[f"Use one of: {', '.join(SUPPORTED_LLM_PROVIDERS)}."],
        ))
    else:
        checks.append(DiagnosticCheck(
            id="llm.provider",
            status="pass",
            severity="info",
            summary=f"LLM provider '{provider}' is supported.",
        ))

    if api_type not in SUPPORTED_LLM_API_TYPES:
        checks.append(DiagnosticCheck(
            id="llm.api_type",
            status="fail",
            severity="error",
            summary=f"Unsupported LLM API type: {api_type}.",
            actions=[f"Use one of: {', '.join(SUPPORTED_LLM_API_TYPES)}."],
        ))
    else:
        checks.append(DiagnosticCheck(
            id="llm.api_type",
            status="pass",
            severity="info",
            summary=f"LLM API type '{api_type}' is supported.",
        ))

    if provider != "ollama" and not config.llm_api_key:
        checks.append(DiagnosticCheck(
            id="llm.api_key",
            status="fail",
            severity="error",
            summary="LLM_API_KEY is required unless provider is Ollama.",
            actions=["Set LLM_API_KEY, pass --llm-key, or choose provider=ollama for local OpenAI-compatible Ollama."],
        ))
    else:
        checks.append(DiagnosticCheck(
            id="llm.api_key",
            status="pass",
            severity="info",
            summary="LLM credential requirement is satisfied.",
        ))

    checks.append(_check_base_url(config.llm_base_url, provider))

    if config.target_min > config.target_max:
        checks.append(DiagnosticCheck(
            id="runtime.target_range",
            status="fail",
            severity="error",
            summary="TARGET_MIN cannot exceed TARGET_MAX.",
            actions=["Lower TARGET_MIN or raise TARGET_MAX."],
        ))
    elif config.target_max > 50:
        checks.append(DiagnosticCheck(
            id="runtime.target_range",
            status="warning",
            severity="warning",
            summary="TARGET_MAX above 50 is not supported by the current ranking/export UI.",
            actions=["Use a maximum of 50 until pagination is implemented."],
        ))
    else:
        checks.append(DiagnosticCheck(
            id="runtime.target_range",
            status="pass",
            severity="info",
            summary=f"Target result range is {config.target_min}-{config.target_max}.",
        ))

    status = "pass"
    if any(check.status == "fail" for check in checks):
        status = "fail"
    elif any(check.status == "warning" for check in checks):
        status = "warning"

    return {
        "ok": status != "fail",
        "status": status,
        "checks": [check.to_dict() for check in checks],
        "sources": list_source_metadata(),
        "summary": summarize_checks(checks),
    }


def smoke_source(config: AgentConfig, query: str = "machine learning", limit: int = 1) -> Dict[str, Any]:
    source = (config.data_source or "openalex").lower()
    require_source_metadata(source)
    query = (query or "machine learning").strip()
    limit = max(1, min(int(limit or 1), 5))
    started = time.perf_counter()
    try:
        if source == "openalex":
            result = OpenAlexProvider(config.openalex_api_key, config.openalex_email).search(query, limit=limit)
        elif source == "crossref":
            result = CrossrefProvider(config.crossref_email).search(query, limit=limit)
        else:
            if not config.wos_api_key:
                return {
                    "ok": False,
                    "source": source,
                    "status": "missing_config",
                    "message": "WOS_API_KEY is required for WoS smoke checks.",
                    "elapsed_ms": int((time.perf_counter() - started) * 1000),
                }
            wos_query = query if any(tag in query.upper() for tag in ("TS=", "TI=", "AU=")) else f"TS=({query})"
            api = DocumentsApi(ApiClient(configuration=Configuration(api_key={"ClarivateApiKeyAuth": config.wos_api_key})))
            result = api.documents_get(q=wos_query, db=config.wos_db, limit=limit)
        hits = getattr(result, "hits", []) or []
        metadata = getattr(result, "metadata", None)
        return {
            "ok": True,
            "source": source,
            "status": "pass",
            "query": query,
            "total": getattr(metadata, "total", 0) if metadata else 0,
            "returned": len(hits),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "sample_titles": [getattr(item, "title", "") for item in hits[:3]],
        }
    except ProviderError as exc:
        return {
            "ok": False,
            "source": source,
            "status": exc.status or "request_error",
            "query": exc.query or query,
            "message": str(exc),
            "body": _compact(exc.body),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
    except ApiException as exc:
        return {
            "ok": False,
            "source": source,
            "status": exc.status or "request_error",
            "query": query,
            "message": str(exc.reason or exc),
            "body": _compact(exc.body or exc.data),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
    except Exception as exc:
        return {
            "ok": False,
            "source": source,
            "status": "error",
            "query": query,
            "message": str(exc),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }


def summarize_checks(checks: List[DiagnosticCheck]) -> Dict[str, int]:
    counts = {"pass": 0, "warning": 0, "fail": 0, "info": 0, "skip": 0}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    return counts


def render_doctor_text(result: Dict[str, Any]) -> str:
    lines = ["PaperSeek doctor", f"Status: {result.get('status')}"]
    lines.append("")
    for check in result.get("checks", []):
        marker = {"pass": "PASS", "warning": "WARN", "fail": "FAIL", "info": "INFO", "skip": "SKIP"}.get(check["status"], check["status"].upper())
        lines.append(f"[{marker}] {check['summary']}")
        for action in check.get("actions", []) or []:
            lines.append(f"       - {action}")
    return "\n".join(lines)


def render_smoke_text(result: Dict[str, Any]) -> str:
    lines = ["PaperSeek smoke", f"Source: {result.get('source')}", f"Status: {'PASS' if result.get('ok') else 'FAIL'}"]
    if result.get("query"):
        lines.append(f"Query: {result.get('query')}")
    if result.get("total") is not None:
        lines.append(f"Total: {result.get('total')} | Returned: {result.get('returned')}")
    if result.get("elapsed_ms") is not None:
        lines.append(f"Elapsed: {result.get('elapsed_ms')}ms")
    if result.get("sample_titles"):
        lines.append("Sample:")
        for title in result.get("sample_titles", []):
            lines.append(f"  - {title}")
    if result.get("message"):
        lines.append(f"Message: {result.get('message')}")
    if result.get("body"):
        lines.append(f"Body: {result.get('body')}")
    return "\n".join(lines)


def dumps(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _check_base_url(url: str, provider: str) -> DiagnosticCheck:
    if not url:
        return DiagnosticCheck(
            id="llm.base_url",
            status="warning",
            severity="warning",
            summary="LLM_BASE_URL is empty; provider defaults will be used when available.",
        )
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return DiagnosticCheck(
            id="llm.base_url",
            status="fail",
            severity="error",
            summary=f"LLM_BASE_URL must start with http:// or https://, got {url}.",
            actions=["Fix LLM_BASE_URL."],
        )
    host = (parsed.hostname or "").lower()
    local = host in ("127.0.0.1", "localhost", "::1")
    if parsed.scheme != "https" and not local:
        return DiagnosticCheck(
            id="llm.base_url",
            status="warning",
            severity="warning",
            summary="Remote LLM_BASE_URL is not HTTPS.",
            actions=["Use HTTPS for remote model providers."],
        )
    return DiagnosticCheck(
        id="llm.base_url",
        status="pass",
        severity="info",
        summary=f"LLM Base URL looks valid for provider '{provider}'.",
        details={"base_url": _redact_url(url)},
    )


def _redact_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def _compact(value: Any, limit: int = 700) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text
