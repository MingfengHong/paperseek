"""
PaperSeek MCP (Model Context Protocol) server.

Exposes PaperSeek's literature search, diagnostics, and history
capabilities as MCP tools callable by AI agents.

Install::

    pip install paperseek[mcp]

Run::

    paperseek-mcp

Or::

    python -m paperseek.mcp_server

Requires Python 3.10+ and the optional ``mcp`` package.
Configuration is read from environment variables or ``.env``,
identical to the CLI and Web UI.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, List, Optional

from paperseek.config import AgentConfig
from paperseek.config_store import load_user_config_into_env
from paperseek.diagnostics import run_doctor, smoke_source
from paperseek.disciplines import normalize_discipline_ids
from paperseek.env_loader import load_env_file
from paperseek.history import (
    HistoryStore,
    result_payload_from_search_result,
    safe_search_params_from_config,
)
from paperseek.llm_client import LLMError, create_llm_client
from paperseek.search_agent import PaperSeekAgent
from paperseek.source_metadata import list_source_metadata

# Load .env and user-level config on import, same as CLI.
load_env_file()
load_user_config_into_env()


# ---------------------------------------------------------------------------
# Pure logic functions — testable without the ``mcp`` package.
# ---------------------------------------------------------------------------


# Patterns covering common credential-shaped substrings echoed back in HTTP
# error bodies (Bearer tokens, API keys, x-api-key headers, etc.). Applied
# before any error message leaves this module so that keys held by the server
# process are never returned to the MCP client or persisted to history.
_KEY_VALUE_PATTERN = re.compile(
    r"(?i)(x-api[_-]?key|api[_-]?key|authorization)\s*[:=]\s*([^\n\r,;}]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)bearer\s+([A-Za-z0-9._\-+/=]{8,})")


def _redact_secrets(text: str, max_chars: int = 700) -> str:
    """Return ``text`` with credential-shaped substrings replaced by ``[redacted]``.

    Long messages are truncated to ``max_chars`` to keep MCP responses compact.
    """
    if not text:
        return ""
    redacted = _KEY_VALUE_PATTERN.sub(lambda m: f"{m.group(1)}: [redacted]", text)
    redacted = _BEARER_PATTERN.sub("[redacted]", redacted)
    if len(redacted) > max_chars:
        redacted = redacted[:max_chars].rstrip() + "..."
    return redacted


def _redact_response(value: Any) -> Any:
    """Recursively redact credential-shaped strings before returning MCP data."""
    if isinstance(value, str):
        return _redact_secrets(value)
    if isinstance(value, dict):
        return {key: _redact_response(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_response(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_response(item) for item in value]
    return value


def _build_search_config(
    source: str = "",
    field: str = "",
    discipline_fields: Optional[List[str]] = None,
    target_min: int = 0,
    target_max: int = 0,
    max_iterations: int = 0,
    expand_citations: Optional[bool] = None,
    fetch_abstracts: Optional[bool] = None,
) -> AgentConfig:
    """Build an :class:`AgentConfig` from the environment with optional overrides.

    Boolean flags default to ``None`` so that ``AgentConfig.from_env()`` values
    (driven by ``EXPAND_CITATIONS`` / ``FETCH_ABSTRACTS``) are preserved when the
    caller does not explicitly override them. Passing ``True`` or ``False``
    forces the corresponding config field.
    """
    config = AgentConfig.from_env()
    if source:
        config.data_source = source
    if field:
        config.search_field = field
    if discipline_fields:
        config.discipline_fields = normalize_discipline_ids(discipline_fields)
    if target_min > 0:
        config.target_min = target_min
    if target_max > 0:
        config.target_max = target_max
    if max_iterations > 0:
        config.max_iterations = max_iterations
    if expand_citations is not None:
        config.expand_citations = expand_citations
    if fetch_abstracts is not None:
        config.fetch_abstracts = fetch_abstracts
    return config


def search_papers_logic(
    question: str,
    source: str = "",
    field: str = "",
    discipline_fields: Optional[List[str]] = None,
    target_min: int = 0,
    target_max: int = 0,
    max_iterations: int = 0,
    expand_citations: Optional[bool] = None,
    fetch_abstracts: Optional[bool] = None,
) -> Dict[str, Any]:
    """Execute a literature search and return a structured result dict.

    On success the dict mirrors :func:`result_payload_from_search_result`.
    On failure the dict contains an ``"error"`` key. Error messages from
    upstream services are redacted to avoid leaking credentials that the
    server process holds.
    """
    question = (question or "").strip()
    if not question:
        return {"error": "question is required"}

    config = _build_search_config(
        source=source,
        field=field,
        discipline_fields=discipline_fields,
        target_min=target_min,
        target_max=target_max,
        max_iterations=max_iterations,
        expand_citations=expand_citations,
        fetch_abstracts=fetch_abstracts,
    )

    try:
        config.validate()
    except ValueError as exc:
        return {"error": f"Configuration error: {exc}"}

    store = HistoryStore()
    run_id = store.create_run(question, safe_search_params_from_config(config))

    try:
        llm = create_llm_client(config)
        agent = PaperSeekAgent(config, llm)
        result = agent.search(question)
        payload = result_payload_from_search_result(result, config.data_source)
        if run_id:
            payload["run_id"] = run_id
        store.complete_run(run_id, payload)
        return payload
    except LLMError as exc:
        message = _redact_secrets(str(exc))
        store.fail_run(run_id, message)
        return {"error": f"LLM error: {message}"}
    except Exception as exc:
        message = _redact_secrets(str(exc))
        store.fail_run(run_id, message)
        return {"error": f"Search error: {message}"}


def check_config_logic(source: str = "") -> Dict[str, Any]:
    """Run configuration diagnostics without live source requests."""
    config = AgentConfig.from_env()
    if source:
        config.data_source = source
    return run_doctor(config)


def smoke_test_logic(source: str = "", query: str = "machine learning") -> Dict[str, Any]:
    """Run a minimal live source connectivity test."""
    config = AgentConfig.from_env()
    if source:
        config.data_source = source
    return _redact_response(smoke_source(config, query=query or "machine learning", limit=1))


def list_sources_logic() -> Dict[str, Any]:
    """Return all supported data sources and their capabilities."""
    return {"sources": list_source_metadata()}


def list_history_logic(limit: int = 50) -> Dict[str, Any]:
    """List recent search runs from local history."""
    store = HistoryStore()
    return {
        **store.status(),
        "history": store.list_runs(limit=limit),
    }


def get_history_run_logic(run_id: str) -> Dict[str, Any]:
    """Get details of a specific search run by ID."""
    store = HistoryStore()
    run = store.get_run(run_id)
    if run is None:
        return {"error": f"History run not found: {run_id}"}
    return run


# ---------------------------------------------------------------------------
# MCP server — requires the optional ``mcp`` package and Python 3.10+.
# ---------------------------------------------------------------------------


def create_server():
    """Create and return the ``FastMCP`` server instance.

    Requires the ``mcp`` package::

        pip install paperseek[mcp]
    """
    if sys.version_info < (3, 10):
        raise RuntimeError(
            "PaperSeek MCP server requires Python 3.10 or later. "
            f"Current: {sys.version}"
        )

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise ImportError(
            "The 'mcp' package is required for the MCP server. "
            "Install it with: pip install paperseek[mcp]"
        )

    mcp = FastMCP("paperseek")

    @mcp.tool()
    def search_papers(
        question: str,
        source: str = "",
        field: str = "",
        discipline_fields: list[str] | None = None,
        target_min: int = 0,
        target_max: int = 0,
        max_iterations: int = 0,
        expand_citations: bool | None = None,
        fetch_abstracts: bool | None = None,
    ) -> str:
        """Search academic literature for a research question.

        Generates a search query from the question using an LLM, searches
        OpenAlex, Crossref, or Web of Science Starter, iteratively refines
        the query, ranks results by relevance, and optionally expands the
        citation network.

        Args:
            question: Research question in natural language (required).
            source: Data source: "openalex" (default), "crossref", or "wos".
            field: Optional discipline or field hint for query generation.
            discipline_fields: OpenAlex Field IDs or labels, e.g. ["Computer Science", "17"].
            target_min: Minimum target results (default from env: 5).
            target_max: Maximum target results (default from env: 50).
            max_iterations: Max query refinement cycles (default from env: 5).
            expand_citations: Expand citation network via OpenAlex (default: from
                ``EXPAND_CITATIONS`` env var, ``true`` if unset).
            fetch_abstracts: Fetch abstracts via DOI from Crossref (default: from
                ``FETCH_ABSTRACTS`` env var, ``false`` if unset). Pass ``True`` or
                ``False`` to override the env value; omit to keep it.

        Returns:
            JSON string with ranked papers, query history, and citation map.
        """
        result = search_papers_logic(
            question=question,
            source=source,
            field=field,
            discipline_fields=discipline_fields,
            target_min=target_min,
            target_max=target_max,
            max_iterations=max_iterations,
            expand_citations=expand_citations,
            fetch_abstracts=fetch_abstracts,
        )
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    @mcp.tool()
    def check_config(source: str = "") -> str:
        """Check PaperSeek configuration and report issues.

        Validates data source, LLM provider, API keys, and target ranges
        without making live source requests. Run this before searching
        if the environment is uncertain.

        Args:
            source: Optional data source to check (openalex, crossref, wos).

        Returns:
            JSON string with diagnostic checks and overall status.
        """
        result = check_config_logic(source=source)
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    @mcp.tool()
    def smoke_test(source: str = "", query: str = "machine learning") -> str:
        """Test connectivity to a literature data source with a small real query.

        Args:
            source: Data source to test (openalex, crossref, wos).
            query: Small test query (default: "machine learning").

        Returns:
            JSON string with test results including total hits and sample titles.
        """
        result = smoke_test_logic(source=source, query=query)
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    @mcp.tool()
    def list_sources() -> str:
        """List all supported literature data sources and their capabilities.

        Returns:
            JSON string with source metadata including API key requirements,
            abstract/citation support, and supported parameters.
        """
        result = list_sources_logic()
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    @mcp.tool()
    def list_history(limit: int = 50) -> str:
        """List recent PaperSeek search runs from local history.

        Args:
            limit: Maximum number of runs to return (default: 50, max: 200).

        Returns:
            JSON string with history status and run summaries.
        """
        result = list_history_logic(limit=limit)
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    @mcp.tool()
    def get_history_run(run_id: str) -> str:
        """Get details of a specific PaperSeek search run.

        Includes the question, generated query, ranked papers, events,
        and citation map metadata.

        Args:
            run_id: The run ID, e.g. "run_abc123def456".

        Returns:
            JSON string with full run details.
        """
        result = get_history_run_logic(run_id=run_id)
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    return mcp


def main():
    """Entry point for the ``paperseek-mcp`` console script."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
