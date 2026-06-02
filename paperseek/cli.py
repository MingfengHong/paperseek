"""
PaperSeek command line interface.

Backward-compatible search still works:
    paperseek "your research question"

Agent-friendly commands are also available:
    paperseek search "your research question" --output json
    paperseek doctor --json
    paperseek smoke --source openalex --json
"""

from __future__ import annotations

import argparse
import json
import sys

from paperseek.config import (
    SUPPORTED_LLM_API_TYPES,
    SUPPORTED_LLM_PROVIDERS,
    AgentConfig,
    default_api_type,
    default_base_url,
    default_model,
)
from paperseek.config_store import (
    config_path,
    import_env_file,
    list_config_entries,
    load_user_config_into_env,
    read_config,
    set_config_value,
    supported_config_keys,
    unset_config_value,
)
from paperseek.diagnostics import dumps, render_doctor_text, render_smoke_text, run_doctor, smoke_source
from paperseek.formatter import format_json, format_text
from paperseek.llm_client import LLMError, create_llm_client
from paperseek.search_agent import WosSearchAgent
from paperseek.source_metadata import list_source_metadata, supported_source_ids

COMMANDS = {"search", "doctor", "smoke", "sources", "config", "help"}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    load_user_config_into_env()

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(_top_help())
        return

    command = argv[0]
    if command in COMMANDS:
        rest = argv[1:]
        if command == "search":
            return _run_search(rest, prog="paperseek search")
        if command == "doctor":
            return _run_doctor(rest)
        if command == "smoke":
            return _run_smoke(rest)
        if command == "sources":
            return _run_sources(rest)
        if command == "config":
            return _run_config(rest)

    # Legacy mode: `paperseek "question" ...`
    return _run_search(argv, prog="paperseek")


def _top_help() -> str:
    return """PaperSeek - LLM based Literature Search Agent

Usage:
  paperseek search <question> [options]
  paperseek <question> [options]
  paperseek doctor [--source openalex] [--json]
  paperseek smoke [--source openalex] [--query "machine learning"] [--json]
  paperseek sources [--json]
  paperseek config <path|list|keys|set|unset|import-env>

Examples:
  paperseek "open innovation and digital platforms"
  paperseek search "responsible AI policy" --source openalex --output json
  paperseek doctor --source openalex
  paperseek smoke --source crossref --query "open innovation"
  paperseek config set LLM_API_KEY sk-...

Run `paperseek search --help` for search options.
"""


def _search_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Search literature sources using natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables:
  DATA_SOURCE        "openalex" (default), "crossref", or "wos"
  WOS_API_KEY        Clarivate WoS Starter API key (X-ApiKey)
  OPENALEX_API_KEY   OpenAlex API key, recommended for stable use
  OPENALEX_EMAIL     Optional email for OpenAlex contact/polite usage
  CROSSREF_EMAIL     Optional email for Crossref polite pool
  LLM_API_KEY        LLM API key; optional for Ollama
  LLM_PROVIDER       Service provider, e.g. openai, anthropic, deepseek, ollama, custom
  LLM_API_TYPE       Protocol: openai_chat, openai_responses, anthropic_messages
  LLM_MODEL          Model name
  LLM_BASE_URL       Custom API endpoint URL
  SEARCH_FIELD       Default discipline/field constraint
  EXPAND_CITATIONS   Set to "false" to skip OpenAlex citation expansion
  FETCH_ABSTRACTS    Set to "true" to enable DOI-based abstract fetching
        """,
    )
    parser.add_argument("question", help="Research question in natural language")
    parser.add_argument("--source", default=None, choices=list(supported_source_ids()), help="Literature data source (default: openalex)")
    parser.add_argument("--field", "-f", default=None, help="Discipline or subject area constraint")
    parser.add_argument("--db", "-d", default=None, help="WoS database (WOS, MEDLINE, BIOABS, etc.)")
    parser.add_argument("--fetch-abstracts", action="store_true", default=None, help="Fetch abstracts via DOI from Crossref/Semantic Scholar")
    parser.add_argument("--no-expand-citations", action="store_true", default=False, help="Disable OpenAlex citation-neighbor expansion")
    parser.add_argument("--llm-provider", default=None, choices=list(SUPPORTED_LLM_PROVIDERS), help="LLM service provider")
    parser.add_argument("--llm-api-type", default=None, choices=list(SUPPORTED_LLM_API_TYPES), help="LLM API protocol")
    parser.add_argument("--llm-key", default=None, help="LLM API key")
    parser.add_argument("--wos-key", default=None, help="WoS API key")
    parser.add_argument("--openalex-key", default=None, help="OpenAlex API key")
    parser.add_argument("--openalex-email", default=None, help="Email for OpenAlex polite/contact usage")
    parser.add_argument("--crossref-email", default=None, help="Email for Crossref polite pool")
    parser.add_argument("--llm-model", default=None, help="LLM model name")
    parser.add_argument("--llm-base-url", default=None, help="Custom LLM API endpoint")
    parser.add_argument("--min", type=int, default=None, help="Target minimum results (default: 5)")
    parser.add_argument("--max", type=int, default=None, help="Target maximum results (default: 50)")
    parser.add_argument("--iterations", type=int, default=None, help="Max broaden/narrow cycles (default: 5)")
    parser.add_argument("--output", "-o", default="text", choices=["text", "json"], help="Output format (default: text)")
    parser.add_argument("--json", action="store_true", help="Shortcut for --output json")
    parser.add_argument("--verbose", "-v", action="store_true", default=False, help="Print intermediate queries")
    return parser


def _apply_search_args(config: AgentConfig, args) -> AgentConfig:
    if args.source:
        config.data_source = args.source
    if args.wos_key:
        config.wos_api_key = args.wos_key
    if args.openalex_key:
        config.openalex_api_key = args.openalex_key
    if args.openalex_email:
        config.openalex_email = args.openalex_email
    if args.crossref_email:
        config.crossref_email = args.crossref_email
    if args.llm_key:
        config.llm_api_key = args.llm_key
    if args.llm_provider:
        config.llm_provider = args.llm_provider
        if not args.llm_api_type:
            config.llm_api_type = default_api_type(args.llm_provider)
        if not args.llm_model:
            config.llm_model = default_model(args.llm_provider)
        if not args.llm_base_url:
            config.llm_base_url = default_base_url(args.llm_provider, config.llm_api_type)
    if args.llm_api_type:
        config.llm_api_type = args.llm_api_type
    if args.llm_model:
        config.llm_model = args.llm_model
    if args.llm_base_url:
        config.llm_base_url = args.llm_base_url
    if args.db:
        config.wos_db = args.db
    if args.field:
        config.search_field = args.field
    if args.fetch_abstracts is not None and args.fetch_abstracts:
        config.fetch_abstracts = True
    if args.no_expand_citations:
        config.expand_citations = False
    if args.min is not None:
        config.target_min = args.min
    if args.max is not None:
        config.target_max = args.max
    if args.iterations is not None:
        config.max_iterations = args.iterations
    return config


def _run_search(argv, prog: str):
    parser = _search_parser(prog)
    args = parser.parse_args(argv)
    if args.json:
        args.output = "json"

    config = _apply_search_args(AgentConfig.from_env(), args)

    try:
        config.validate()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        print("Run `paperseek doctor` for diagnostics.", file=sys.stderr)
        sys.exit(1)

    try:
        llm = create_llm_client(config)
    except Exception as exc:
        print(f"Failed to initialize LLM client: {exc}", file=sys.stderr)
        sys.exit(1)

    agent = WosSearchAgent(config, llm)

    try:
        result = agent.search(args.question, verbose=args.verbose)
    except LLMError as exc:
        print(f"LLM error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Search error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.output == "json":
        print(format_json(
            items=result["ranked"],
            question=result["question"],
            final_query=result["final_query"],
            db=result["db"],
            total_count=result["total"],
            iterations=result["iterations"],
            field_name=result["field"],
            history=result.get("history", []),
            source=result.get("source", ""),
        ))
    else:
        print(format_text(
            items=result["ranked"],
            question=result["question"],
            final_query=result["final_query"],
            db=result["db"],
            total_count=result["total"],
            iterations=result["iterations"],
            field_name=result["field"],
            verbose=args.verbose,
        ))


def _doctor_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paperseek doctor", description="Check PaperSeek configuration without making live source requests")
    parser.add_argument("--source", choices=list(supported_source_ids()), default=None, help="Override DATA_SOURCE for diagnostics")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    return parser


def _run_doctor(argv):
    args = _doctor_parser().parse_args(argv)
    config = AgentConfig.from_env()
    if args.source:
        config.data_source = args.source
    result = run_doctor(config)
    print(dumps(result) if args.json else render_doctor_text(result))
    if not result.get("ok"):
        sys.exit(1)


def _smoke_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paperseek smoke", description="Run a minimal live request against one literature source")
    parser.add_argument("--source", choices=list(supported_source_ids()), default=None, help="Source to check")
    parser.add_argument("--query", default="machine learning", help="Small smoke-test query")
    parser.add_argument("--limit", type=int, default=1, help="Number of records to request, max 5")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    return parser


def _run_smoke(argv):
    args = _smoke_parser().parse_args(argv)
    config = AgentConfig.from_env()
    if args.source:
        config.data_source = args.source
    result = smoke_source(config, query=args.query, limit=args.limit)
    print(dumps(result) if args.json else render_smoke_text(result))
    if not result.get("ok"):
        sys.exit(1)


def _run_sources(argv):
    parser = argparse.ArgumentParser(prog="paperseek sources", description="List PaperSeek data source capabilities")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args(argv)
    data = {"sources": list_source_metadata()}
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    for source in data["sources"]:
        print(f"{source['id']}: {source['display_name']} [{source['status']}]")
        print(f"  API key: {source['api_key']}")
        print(f"  Abstracts: {source['supports_abstracts']} | Citations: {source['supports_citations']} | Citation expansion: {source['supports_citation_expansion']}")
        print(f"  Parameters: {', '.join(source['supported_parameters'])}")
        if source.get("notes"):
            for note in source["notes"]:
                print(f"  - {note}")
        print()


def _run_config(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print("""paperseek config <command>

Commands:
  path                         Print user config path
  keys                         List supported config keys
  list [--all] [--json]         List configured values with secrets masked
  set <KEY> <VALUE>             Store a user-level CLI config value
  unset <KEY>                   Remove a user-level CLI config value
  import-env <PATH>             Import supported keys from a .env file

Environment variables still override user-level config. Web UI values are not saved.
""")
        return

    command = argv[0]
    rest = argv[1:]
    if command == "path":
        print(config_path())
        return
    if command == "keys":
        for key in supported_config_keys():
            print(key)
        return
    if command == "list":
        parser = argparse.ArgumentParser(prog="paperseek config list")
        parser.add_argument("--all", action="store_true", help="Include missing keys")
        parser.add_argument("--json", action="store_true", help="Print JSON")
        args = parser.parse_args(rest)
        entries = list_config_entries(include_missing=args.all)
        if args.json:
            print(json.dumps({"path": str(config_path()), "entries": entries}, ensure_ascii=False, indent=2))
        else:
            print(f"Config path: {config_path()}")
            for entry in entries:
                print(f"{entry['key']}: {entry['value'] or '(missing)'} [{entry['source']}]")
        return
    if command == "set":
        parser = argparse.ArgumentParser(prog="paperseek config set")
        parser.add_argument("key")
        parser.add_argument("value")
        args = parser.parse_args(rest)
        set_config_value(args.key, args.value)
        print(f"Saved {args.key} to {config_path()}")
        return
    if command == "unset":
        parser = argparse.ArgumentParser(prog="paperseek config unset")
        parser.add_argument("key")
        args = parser.parse_args(rest)
        unset_config_value(args.key)
        print(f"Removed {args.key} from {config_path()}")
        return
    if command == "import-env":
        parser = argparse.ArgumentParser(prog="paperseek config import-env")
        parser.add_argument("path")
        args = parser.parse_args(rest)
        imported = import_env_file(args.path)
        print(f"Imported {len(imported)} keys into {config_path()}: {', '.join(imported)}")
        return

    print(f"Unknown config command: {command}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
