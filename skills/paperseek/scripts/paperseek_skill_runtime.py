#!/usr/bin/env python3
"""Self-contained PaperSeek Skill runtime.

This runtime is intentionally dependency-free. It lets a separately published
Skill perform core literature discovery without installing the PaperSeek Python
package. When the package is installed, scripts/paperseek.py delegates to the
full implementation; otherwise this module handles search, smoke, sources,
doctor, config inspection, and history path lookup.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen


CONFIG_KEYS = (
    "CROSSREF_EMAIL",
    "DATA_SOURCE",
    "DISCIPLINE_FIELDS",
    "EXPAND_CITATIONS",
    "FETCH_ABSTRACTS",
    "LLM_API_KEY",
    "LLM_API_TYPE",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_PROVIDER",
    "MAX_ITERATIONS",
    "OPENALEX_API_KEY",
    "OPENALEX_EMAIL",
    "PAPERSEEK_HISTORY_DB",
    "PAPERSEEK_HISTORY_ENABLED",
    "SEARCH_FIELD",
    "TARGET_MAX",
    "TARGET_MIN",
    "WOS_API_KEY",
    "WOS_DB",
)

OPENALEX_FIELDS = {
    "11": "Agricultural and Biological Sciences",
    "12": "Arts and Humanities",
    "13": "Biochemistry, Genetics and Molecular Biology",
    "14": "Business, Management and Accounting",
    "15": "Chemical Engineering",
    "16": "Chemistry",
    "17": "Computer Science",
    "18": "Decision Sciences",
    "19": "Earth and Planetary Sciences",
    "20": "Economics, Econometrics and Finance",
    "21": "Energy",
    "22": "Engineering",
    "23": "Environmental Science",
    "24": "Immunology and Microbiology",
    "25": "Materials Science",
    "26": "Mathematics",
    "27": "Medicine",
    "28": "Neuroscience",
    "29": "Nursing",
    "30": "Pharmacology, Toxicology and Pharmaceutics",
    "31": "Physics and Astronomy",
    "32": "Psychology",
    "33": "Social Sciences",
    "34": "Veterinary",
    "35": "Dentistry",
    "36": "Health Professions",
}

SOURCE_METADATA = [
    {
        "id": "openalex",
        "display_name": "OpenAlex",
        "status": "default",
        "description": "Open scholarly metadata source for broad discovery, abstracts when available, citation counts, and citation graph traversal.",
        "api_key": "recommended",
        "default": True,
        "supports_abstracts": True,
        "supports_citations": True,
        "supports_citation_expansion": False,
        "supports_pdf_links": True,
        "supported_parameters": [
            "openalex_api_key",
            "openalex_email",
            "search_field",
            "discipline_fields",
            "target_min",
            "target_max",
            "max_iterations",
        ],
        "required_config": [],
        "optional_config": ["OPENALEX_API_KEY", "OPENALEX_EMAIL"],
        "notes": [
            "Standalone Skill search uses OpenAlex works search and primary_topic.field.id filters.",
            "Full citation expansion requires the PaperSeek package.",
        ],
    },
    {
        "id": "crossref",
        "display_name": "Crossref",
        "status": "supported",
        "description": "Publisher DOI and bibliographic metadata registry; useful for DOI/title verification and broad metadata lookup.",
        "api_key": "not_required",
        "default": False,
        "supports_abstracts": True,
        "supports_citations": False,
        "supports_citation_expansion": False,
        "supports_pdf_links": False,
        "supported_parameters": [
            "crossref_email",
            "search_field",
            "discipline_fields",
            "target_min",
            "target_max",
            "max_iterations",
        ],
        "required_config": [],
        "optional_config": ["CROSSREF_EMAIL"],
        "notes": [
            "Crossref abstracts are optional publisher metadata and are often missing.",
            "Use a mailto email for Crossref polite-pool requests.",
        ],
    },
    {
        "id": "wos",
        "display_name": "Web of Science Starter",
        "status": "temporarily_unavailable",
        "description": "Clarivate Web of Science Starter API adapter for users with approved API access.",
        "api_key": "required",
        "default": False,
        "supports_abstracts": False,
        "supports_citations": True,
        "supports_citation_expansion": False,
        "supports_pdf_links": False,
        "supported_parameters": [
            "wos_api_key",
            "wos_db",
            "search_field",
            "discipline_fields",
            "target_min",
            "target_max",
            "max_iterations",
        ],
        "required_config": ["WOS_API_KEY"],
        "optional_config": [],
        "notes": [
            "WoS Starter returns basic bibliographic metadata and links; do not rely on native abstract fields.",
            "Availability depends on Clarivate API entitlement and upstream service status.",
        ],
    },
]


def run(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(help_text())
        return 0

    command = argv[0]
    if command not in {"search", "doctor", "smoke", "sources", "config", "history"}:
        argv = ["search", *argv]
        command = "search"

    rest = argv[1:]
    if command == "sources":
        return run_sources(rest)
    if command == "doctor":
        return run_doctor(rest)
    if command == "smoke":
        return run_smoke(rest)
    if command == "search":
        return run_search(rest)
    if command == "config":
        return run_config(rest)
    if command == "history":
        return run_history(rest)

    print(f"Unknown standalone Skill command: {command}", file=sys.stderr)
    return 2


def help_text() -> str:
    return """PaperSeek Skill standalone runtime

Usage:
  python scripts/paperseek.py search "QUESTION" [--source openalex] [--json]
  python scripts/paperseek.py "QUESTION" [--source openalex] [--json]
  python scripts/paperseek.py smoke [--source openalex] [--query "machine learning"] [--json]
  python scripts/paperseek.py sources [--json]
  python scripts/paperseek.py doctor [--source openalex] [--json]
  python scripts/paperseek.py config <path|keys|list>
  python scripts/paperseek.py history path
  python scripts/paperseek.py --install-help

The standalone runtime is bundled inside the Skill folder and uses only the
Python standard library. It can search OpenAlex, Crossref, and WoS Starter
directly. If LLM_API_KEY is configured, it can also ask an OpenAI-compatible LLM
to refine search terms and score candidates; otherwise it uses deterministic
query and ranking heuristics.
"""


def run_sources(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="paperseek sources")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = {"sources": SOURCE_METADATA, "runtime": "standalone_skill"}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for source in SOURCE_METADATA:
            default = " (default)" if source.get("default") else ""
            print(f"{source['id']}: {source['display_name']} [{source['status']}]{default}")
            print(f"  {source['description']}")
            if source.get("required_config"):
                print(f"  Required config: {', '.join(source['required_config'])}")
            if source.get("optional_config"):
                print(f"  Optional config: {', '.join(source['optional_config'])}")
    return 0


def run_doctor(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="paperseek doctor")
    parser.add_argument("--source", default=os.environ.get("DATA_SOURCE", "openalex"))
    parser.add_argument("--discipline", "--discipline-field", dest="discipline_fields", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    config = effective_config()
    source = (args.source or config.get("DATA_SOURCE") or "openalex").lower()
    provider = (config.get("LLM_PROVIDER") or "openai").lower()
    api_type = (config.get("LLM_API_TYPE") or default_api_type(provider)).lower()
    disciplines = normalize_discipline_fields(args.discipline_fields or split_fields(config.get("DISCIPLINE_FIELDS", "")))

    checks = doctor_checks(config, source, provider, api_type, disciplines)
    status = aggregate_status(checks)
    payload = {
        "ok": status != "fail",
        "status": status,
        "runtime": "standalone_skill",
        "checks": checks,
        "sources": SOURCE_METADATA,
        "discipline_fields": disciplines,
        "summary": summarize_checks(checks),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"PaperSeek standalone Skill doctor: {status}")
        for item in checks:
            print(f"- [{item['status']}] {item['summary']}")
            for action in item.get("actions", []):
                print(f"  action: {action}")
    return 0 if status != "fail" else 1


def run_smoke(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="paperseek smoke")
    parser.add_argument("--source", default=os.environ.get("DATA_SOURCE", "openalex"))
    parser.add_argument("--query", default="machine learning")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--discipline", "--discipline-field", dest="discipline_fields", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    config = effective_config()
    source = (args.source or config.get("DATA_SOURCE") or "openalex").lower()
    disciplines = normalize_discipline_fields(args.discipline_fields or split_fields(config.get("DISCIPLINE_FIELDS", "")))
    started = time.perf_counter()
    try:
        records, total, used_query = fetch_source(source, args.query, max(1, min(args.limit, 5)), config, disciplines)
        payload = {
            "ok": True,
            "source": source,
            "status": "pass",
            "runtime": "standalone_skill",
            "query": used_query,
            "discipline_fields": disciplines,
            "total": total,
            "returned": len(records),
            "elapsed_ms": elapsed_ms(started),
            "sample_titles": [record.get("title", "") for record in records[:3]],
        }
    except Exception as exc:
        payload = {
            "ok": False,
            "source": source,
            "status": "request_error",
            "runtime": "standalone_skill",
            "query": args.query,
            "message": str(exc),
            "elapsed_ms": elapsed_ms(started),
        }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_smoke_text(payload)
    return 0 if payload["ok"] else 1


def run_search(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="paperseek search")
    parser.add_argument("question")
    parser.add_argument("--source", default=os.environ.get("DATA_SOURCE", "openalex"), choices=["openalex", "crossref", "wos"])
    parser.add_argument("--min", dest="target_min", type=int, default=int_env("TARGET_MIN", 5))
    parser.add_argument("--max", dest="target_max", type=int, default=int_env("TARGET_MAX", 20))
    parser.add_argument("--iterations", type=int, default=int_env("MAX_ITERATIONS", 1))
    parser.add_argument("--field", default=os.environ.get("SEARCH_FIELD", ""))
    parser.add_argument("--discipline", "--discipline-field", dest="discipline_fields", action="append", default=[])
    parser.add_argument("--no-expand-citations", action="store_true")
    parser.add_argument("--fetch-abstracts", action="store_true")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--llm-provider", default="")
    parser.add_argument("--llm-api-type", default="")
    parser.add_argument("--llm-model", default="")
    parser.add_argument("--llm-base-url", default="")
    parser.add_argument("--llm-key", default="")
    parser.add_argument("--openalex-key", default="")
    parser.add_argument("--openalex-email", default="")
    parser.add_argument("--crossref-email", default="")
    parser.add_argument("--wos-key", default="")
    parser.add_argument("--db", default="")
    args = parser.parse_args(argv)

    config = effective_config()
    apply_arg_config(config, args)
    disciplines = normalize_discipline_fields(args.discipline_fields or split_fields(config.get("DISCIPLINE_FIELDS", "")))
    source = args.source
    target_max = max(1, min(args.target_max, 50))
    fetch_limit = max(target_max, args.target_min, 10)
    question = args.question.strip()
    started = time.perf_counter()

    generated_query = build_search_query(question, args.field, source, config)
    records, total, used_query = fetch_source(source, generated_query, fetch_limit, config, disciplines)
    ranked = rank_records(question, records, config, limit=target_max)

    payload = {
        "question": question,
        "source": source,
        "query": used_query,
        "database": config.get("WOS_DB", "WOS") if source == "wos" else source.upper(),
        "field": args.field,
        "discipline_fields": disciplines,
        "total_results": total,
        "iterations": 1,
        "runtime": "standalone_skill",
        "elapsed_ms": elapsed_ms(started),
        "history": [
            {
                "iteration": 1,
                "query": used_query,
                "total": total,
                "reason": "Standalone Skill runtime performs one source query with optional LLM query refinement.",
            }
        ],
        "ranked": ranked,
        "citation_map": {"enabled": False, "reason": "Citation expansion requires the full PaperSeek package."},
        "warnings": standalone_warnings(config),
    }
    if args.json or args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_search_text(payload)
    return 0


def run_config(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("""paperseek config <command>

Standalone Skill commands:
  path                         Print user config path
  keys                         List supported config keys
  list [--all] [--json]         List configured values with secrets masked
""")
        return 0
    command, rest = argv[0], argv[1:]
    if command == "path":
        print(config_path())
        return 0
    if command == "keys":
        for key in CONFIG_KEYS:
            print(key)
        return 0
    if command == "list":
        parser = argparse.ArgumentParser(prog="paperseek config list")
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args(rest)
        entries = config_entries(include_missing=args.all)
        if args.json:
            print(json.dumps({"path": str(config_path()), "entries": entries}, ensure_ascii=False, indent=2))
        else:
            print(f"Config path: {config_path()}")
            if not entries:
                print("No PaperSeek config values found.")
            for entry in entries:
                print(f"{entry['key']}={entry['value']} ({entry['source']})")
        return 0
    print(f"Unsupported standalone config command: {command}", file=sys.stderr)
    return 2


def run_history(argv: List[str]) -> int:
    if argv == ["path"]:
        print(history_path())
        return 0
    print("Standalone Skill runtime supports only `paperseek history path`.", file=sys.stderr)
    return 2


def fetch_source(source: str, query: str, limit: int, config: Dict[str, str], discipline_fields: Sequence[str]) -> Tuple[List[Dict[str, object]], int, str]:
    if source == "openalex":
        return fetch_openalex(query, limit, config, discipline_fields)
    if source == "crossref":
        return fetch_crossref(query, limit, config)
    if source == "wos":
        return fetch_wos(query, limit, config, discipline_fields)
    raise ValueError(f"Unsupported data source: {source}")


def fetch_openalex(query: str, limit: int, config: Dict[str, str], discipline_fields: Sequence[str]) -> Tuple[List[Dict[str, object]], int, str]:
    params = {
        "search": query,
        "per-page": str(max(1, min(limit, 50))),
    }
    if config.get("OPENALEX_EMAIL"):
        params["mailto"] = config["OPENALEX_EMAIL"]
    if config.get("OPENALEX_API_KEY"):
        params["api_key"] = config["OPENALEX_API_KEY"]
    field_ids = [field for field in discipline_fields if field in OPENALEX_FIELDS]
    if field_ids:
        params["filter"] = "primary_topic.field.id:" + "|".join(field_ids)
    data = http_json("https://api.openalex.org/works?" + urlencode(params))
    results = data.get("results", [])
    records = [normalize_openalex(item) for item in results if isinstance(item, dict)]
    total = int((data.get("meta") or {}).get("count") or len(records))
    return records, total, query


def fetch_crossref(query: str, limit: int, config: Dict[str, str]) -> Tuple[List[Dict[str, object]], int, str]:
    params = {
        "query.bibliographic": query,
        "rows": str(max(1, min(limit, 50))),
    }
    if config.get("CROSSREF_EMAIL"):
        params["mailto"] = config["CROSSREF_EMAIL"]
    data = http_json("https://api.crossref.org/works?" + urlencode(params))
    message = data.get("message") or {}
    items = message.get("items") or []
    records = [normalize_crossref(item) for item in items if isinstance(item, dict)]
    total = int(message.get("total-results") or len(records))
    return records, total, query


def fetch_wos(query: str, limit: int, config: Dict[str, str], discipline_fields: Sequence[str]) -> Tuple[List[Dict[str, object]], int, str]:
    api_key = config.get("WOS_API_KEY", "")
    if not api_key:
        raise ValueError("WOS_API_KEY is required for WoS Starter searches.")
    wos_query = query if re.search(r"\b(TS|TI|AU|SO|WC)=", query, re.I) else f"TS=({query})"
    wc_terms = wos_categories_for_fields(discipline_fields)
    if wc_terms:
        wc_query = " OR ".join(quote_wos_category(term) for term in wc_terms[:10])
        wos_query = f"({wos_query}) AND WC=({wc_query})"
    params = {
        "db": config.get("WOS_DB", "WOS"),
        "q": wos_query,
        "limit": str(max(1, min(limit, 50))),
    }
    headers = {"X-ApiKey": api_key}
    data = http_json("https://api.clarivate.com/apis/wos-starter/v1/documents?" + urlencode(params), headers=headers)
    records_raw = data.get("hits") or data.get("records") or data.get("documents") or []
    records = [normalize_wos(item) for item in records_raw if isinstance(item, dict)]
    metadata = data.get("metadata") or data.get("meta") or {}
    total = int(metadata.get("total") or metadata.get("totalRecords") or len(records))
    return records, total, wos_query


def normalize_openalex(item: Dict[str, object]) -> Dict[str, object]:
    doi = clean_doi(str(item.get("doi") or ""))
    primary_location = item.get("primary_location") if isinstance(item.get("primary_location"), dict) else {}
    source = primary_location.get("source") if isinstance(primary_location.get("source"), dict) else {}
    authors = []
    for authorship in item.get("authorships") or []:
        if isinstance(authorship, dict):
            author = authorship.get("author") if isinstance(authorship.get("author"), dict) else {}
            name = author.get("display_name")
            if name:
                authors.append(str(name))
    abstract = truncate_text(inverted_abstract(item.get("abstract_inverted_index")), 3000)
    keywords = []
    for concept in item.get("concepts") or []:
        if isinstance(concept, dict) and concept.get("display_name"):
            keywords.append(str(concept["display_name"]))
    return {
        "id": str(item.get("id") or doi or item.get("display_name") or ""),
        "source": "openalex",
        "title": str(item.get("display_name") or ""),
        "authors": authors,
        "authors_text": ", ".join(authors),
        "year": item.get("publication_year") or "",
        "venue": source.get("display_name") or "",
        "publication_type": item.get("type") or "",
        "doi": doi,
        "url": item.get("id") or item.get("doi") or "",
        "pdf_url": best_pdf_url(primary_location),
        "abstract": abstract,
        "keywords": keywords,
        "keywords_text": ", ".join(keywords),
        "citation_count": int(item.get("cited_by_count") or 0),
        "source_raw_id": item.get("id") or "",
    }


def normalize_crossref(item: Dict[str, object]) -> Dict[str, object]:
    title = first_text(item.get("title"))
    authors = []
    for author in item.get("author") or []:
        if isinstance(author, dict):
            name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
            if name:
                authors.append(name)
    container = first_text(item.get("container-title"))
    year = year_from_crossref_date(item.get("published-print") or item.get("published-online") or item.get("issued"))
    abstract = truncate_text(strip_tags(str(item.get("abstract") or "")), 3000)
    doi = clean_doi(str(item.get("DOI") or ""))
    return {
        "id": doi or str(item.get("URL") or title),
        "source": "crossref",
        "title": title,
        "authors": authors,
        "authors_text": ", ".join(authors),
        "year": year,
        "venue": container or str(item.get("publisher") or ""),
        "publication_type": first_text(item.get("type")),
        "doi": doi,
        "url": item.get("URL") or ("https://doi.org/" + doi if doi else ""),
        "pdf_url": "",
        "abstract": abstract,
        "keywords": [],
        "keywords_text": "",
        "citation_count": int(item.get("is-referenced-by-count") or 0),
        "source_raw_id": doi,
    }


def normalize_wos(item: Dict[str, object]) -> Dict[str, object]:
    title = str(item.get("title") or item.get("articleTitle") or item.get("sourceTitle") or "")
    authors_raw = item.get("authors") or item.get("names") or []
    authors = []
    for author in authors_raw:
        if isinstance(author, dict):
            name = author.get("displayName") or author.get("wosStandard") or author.get("fullName")
            if name:
                authors.append(str(name))
        elif isinstance(author, str):
            authors.append(author)
    doi = clean_doi(str(item.get("doi") or item.get("DOI") or ""))
    links = item.get("links") if isinstance(item.get("links"), dict) else {}
    return {
        "id": str(item.get("uid") or item.get("ut") or doi or title),
        "source": "wos",
        "title": title,
        "authors": authors,
        "authors_text": ", ".join(authors),
        "year": item.get("year") or item.get("publishYear") or "",
        "venue": item.get("sourceTitle") or item.get("journal") or "",
        "publication_type": item.get("doctype") or item.get("documentType") or "",
        "doi": doi,
        "url": links.get("record") or item.get("url") or "",
        "pdf_url": "",
        "abstract": truncate_text(str(item.get("abstract") or ""), 3000),
        "keywords": item.get("keywords") if isinstance(item.get("keywords"), list) else [],
        "keywords_text": ", ".join(item.get("keywords") or []) if isinstance(item.get("keywords"), list) else "",
        "citation_count": int(item.get("timesCited") or item.get("citations") or 0),
        "source_raw_id": item.get("uid") or item.get("ut") or "",
    }


def build_search_query(question: str, field: str, source: str, config: Dict[str, str]) -> str:
    llm_key = config.get("LLM_API_KEY", "")
    if not llm_key:
        return compact_query(question, field)
    prompt = (
        "Convert the research question into one concise scholarly literature search query. "
        "Use English academic terms, synonyms joined naturally, and no Boolean syntax unless the target source is Web of Science. "
        "Return only the query string.\n\n"
        f"Source: {source}\n"
        f"Discipline hint: {field or 'none'}\n"
        f"Question: {question}\n"
    )
    try:
        text = llm_complete(prompt, config, max_tokens=160)
        return sanitize_query(text) or compact_query(question, field)
    except Exception:
        return compact_query(question, field)


def rank_records(question: str, records: List[Dict[str, object]], config: Dict[str, str], limit: int) -> List[Dict[str, object]]:
    scored = []
    llm_scores = {}
    if config.get("LLM_API_KEY") and records:
        try:
            llm_scores = llm_rank(question, records[: min(20, len(records))], config)
        except Exception:
            llm_scores = {}
    for record in records:
        score, reason = heuristic_score(question, record)
        item_id = str(record.get("id") or "")
        if item_id in llm_scores:
            llm_score, llm_reason = llm_scores[item_id]
            score = max(score, float(llm_score))
            reason = llm_reason or reason
        row = dict(record)
        row["relevance_score"] = round(score, 3)
        row["relevance_reason"] = reason
        row["score"] = row["relevance_score"]
        row["provider"] = row.get("source", "")
        row["uid"] = row.get("id", "")
        row["publish_year"] = row.get("year", "")
        row["document_types"] = [row.get("publication_type", "")] if row.get("publication_type") else []
        row["citations"] = row.get("citation_count", 0)
        row["reasoning"] = reason
        row["links"] = [value for value in [row.get("url"), row.get("pdf_url")] if value]
        scored.append(row)
    scored.sort(key=lambda item: (float(item.get("relevance_score") or 0), int(item.get("citation_count") or 0)), reverse=True)
    for index, row in enumerate(scored[:limit], start=1):
        row["rank"] = index
    return scored[:limit]


def llm_rank(question: str, records: Sequence[Dict[str, object]], config: Dict[str, str]) -> Dict[str, Tuple[float, str]]:
    candidates = []
    for record in records:
        candidates.append({
            "id": record.get("id", ""),
            "title": record.get("title", ""),
            "year": record.get("year", ""),
            "venue": record.get("venue", ""),
            "abstract": str(record.get("abstract", ""))[:700],
        })
    prompt = (
        "Score candidate papers for relevance to the research question. "
        "Return only a JSON array of objects with id, score from 1 to 5, and reason.\n\n"
        f"Question: {question}\n"
        f"Candidates: {json.dumps(candidates, ensure_ascii=False)}"
    )
    text = llm_complete(prompt, config, max_tokens=1200)
    data = parse_json_array(text)
    scores = {}
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            try:
                score = float(item.get("score", 0))
            except (TypeError, ValueError):
                score = 0.0
            scores[str(item["id"])] = (max(0.0, min(5.0, score)), str(item.get("reason") or "LLM relevance score."))
    return scores


def llm_complete(prompt: str, config: Dict[str, str], max_tokens: int = 512) -> str:
    provider = (config.get("LLM_PROVIDER") or "openai").lower()
    api_type = (config.get("LLM_API_TYPE") or default_api_type(provider)).lower()
    model = config.get("LLM_MODEL") or default_model(provider)
    base_url = (config.get("LLM_BASE_URL") or default_base_url(provider)).rstrip("/")
    api_key = config.get("LLM_API_KEY") or ""
    if not api_key:
        raise ValueError("LLM_API_KEY is not configured.")
    if api_type == "openai_responses":
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = http_json(
            base_url + "/responses",
            method="POST",
            headers=headers,
            payload={"model": model, "input": prompt, "max_output_tokens": max_tokens},
        )
        return extract_responses_text(data)
    if api_type == "anthropic_messages":
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        data = http_json(
            base_url + "/v1/messages" if not base_url.endswith("/v1") else base_url + "/messages",
            method="POST",
            headers=headers,
            payload={"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]},
        )
        content = data.get("content") or []
        return "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = http_json(
        base_url + "/chat/completions",
        method="POST",
        headers=headers,
        payload={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        },
    )
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("LLM response did not include choices.")
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    return str((message or {}).get("content") or choices[0].get("text") or "")


def http_json(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, payload: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    body = None
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "PaperSeek-Skill/standalone",
    }
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:500]}")
    except URLError as exc:
        raise RuntimeError(f"Network error from {url}: {exc.reason}")
    return json.loads(raw)


def doctor_checks(config: Dict[str, str], source: str, provider: str, api_type: str, disciplines: Sequence[str]) -> List[Dict[str, object]]:
    checks = []
    metadata = source_metadata(source)
    if metadata:
        checks.append(check("source.supported", "pass", "info", f"Data source '{source}' is available in the standalone Skill runtime."))
        if metadata["status"] == "temporarily_unavailable":
            checks.append(check(
                "source.status",
                "warning",
                "warning",
                f"{metadata['display_name']} is marked temporarily unavailable in the UI.",
                ["Use OpenAlex unless WoS Starter access has been verified."],
            ))
    else:
        checks.append(check("source.supported", "fail", "error", f"Unsupported data source: {source}.", ["Run `paperseek sources` to list supported sources."]))

    if source == "wos" and not config.get("WOS_API_KEY"):
        checks.append(check("source.wos_key", "fail", "error", "WOS_API_KEY is required for WoS Starter searches."))
    elif source == "openalex" and not config.get("OPENALEX_API_KEY"):
        checks.append(check("source.openalex_key", "warning", "warning", "OPENALEX_API_KEY is not configured.", ["OpenAlex may still work, but configure a key for stable use."]))
    elif source == "crossref" and not config.get("CROSSREF_EMAIL"):
        checks.append(check("source.crossref_email", "warning", "warning", "CROSSREF_EMAIL is not configured.", ["Set CROSSREF_EMAIL for Crossref polite-pool requests."]))
    else:
        checks.append(check("source.credentials", "pass", "info", "Source-specific credential requirement is satisfied or not required."))

    if disciplines:
        checks.append(check("source.discipline_fields", "pass", "info", "Discipline filter configured: " + ", ".join(field_label(item) for item in disciplines)))

    if provider not in ("anthropic", "deepseek", "google", "openai", "ollama", "siliconflow", "zhipu"):
        checks.append(check("llm.provider", "fail", "error", f"Unsupported LLM provider: {provider}."))
    else:
        checks.append(check("llm.provider", "pass", "info", f"LLM provider '{provider}' is recognized."))

    if api_type not in ("anthropic_messages", "openai_chat", "openai_responses"):
        checks.append(check("llm.api_type", "fail", "error", f"Unsupported LLM API type: {api_type}."))
    else:
        checks.append(check("llm.api_type", "pass", "info", f"LLM API type '{api_type}' is recognized."))

    if provider != "ollama" and not config.get("LLM_API_KEY"):
        checks.append(check("llm.api_key", "warning", "warning", "LLM_API_KEY is not configured.", ["Standalone search will use deterministic query and ranking heuristics."]))
    else:
        checks.append(check("llm.api_key", "pass", "info", "LLM configuration can be used for query refinement and ranking."))
    return checks


def check(check_id: str, status: str, severity: str, summary: str, actions: Optional[List[str]] = None) -> Dict[str, object]:
    return {
        "id": check_id,
        "status": status,
        "severity": severity,
        "summary": summary,
        "actions": actions or [],
        "details": {},
        "ok": status in ("pass", "info", "skip", "warning"),
    }


def aggregate_status(checks: Sequence[Dict[str, object]]) -> str:
    if any(item.get("status") == "fail" for item in checks):
        return "fail"
    if any(item.get("status") == "warning" for item in checks):
        return "warning"
    return "pass"


def summarize_checks(checks: Sequence[Dict[str, object]]) -> Dict[str, int]:
    summary = {"pass": 0, "warning": 0, "fail": 0, "info": 0, "skip": 0}
    for item in checks:
        status = str(item.get("status", "info"))
        summary[status] = summary.get(status, 0) + 1
    return summary


def heuristic_score(question: str, record: Dict[str, object]) -> Tuple[float, str]:
    q_terms = important_terms(question)
    haystack = " ".join(str(record.get(key, "")) for key in ("title", "abstract", "keywords_text", "venue")).lower()
    matches = [term for term in q_terms if term in haystack]
    term_score = (len(matches) / max(1, len(q_terms))) * 3.5
    citation_score = min(1.0, math.log10(int(record.get("citation_count") or 0) + 1) / 3)
    year_score = 0.0
    try:
        year = int(record.get("year") or 0)
        if year >= 2020:
            year_score = 0.4
        elif year >= 2015:
            year_score = 0.2
    except (TypeError, ValueError):
        year_score = 0.0
    score = min(5.0, 1.0 + term_score + citation_score + year_score)
    reason = "Matched query terms: " + ", ".join(matches[:8]) if matches else "Ranked by metadata overlap, citation count, and recency."
    return score, reason


def important_terms(text: str) -> List[str]:
    stopwords = {
        "about", "after", "against", "among", "and", "are", "for", "from", "how", "into", "of", "on",
        "or", "study", "the", "their", "to", "under", "what", "with", "研究", "文献", "关于",
    }
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", text.lower())
    unique = []
    for word in words:
        if word in stopwords:
            continue
        if word not in unique:
            unique.append(word)
    return unique[:24]


def compact_query(question: str, field: str = "") -> str:
    text = " ".join(important_terms(question))
    if not text:
        text = question.strip()
    if field:
        text = f"{text} {field}"
    return text[:260]


def sanitize_query(text: str) -> str:
    text = strip_code_fence(text).strip().strip('"').strip("'")
    text = re.sub(r"^(query|search query)\s*:\s*", "", text, flags=re.I)
    return " ".join(text.split())[:300]


def parse_json_array(text: str) -> List[object]:
    text = strip_code_fence(text)
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text


def extract_responses_text(data: Dict[str, object]) -> str:
    if data.get("output_text"):
        return str(data["output_text"])
    chunks = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("text"):
                chunks.append(str(content["text"]))
    return "\n".join(chunks)


def source_metadata(source: str) -> Optional[Dict[str, object]]:
    for item in SOURCE_METADATA:
        if item["id"] == source:
            return item
    return None


def default_api_type(provider: str) -> str:
    if provider == "anthropic":
        return "anthropic_messages"
    if provider == "openai":
        return "openai_responses"
    return "openai_chat"


def default_model(provider: str) -> str:
    return {
        "anthropic": "claude-sonnet-4-6",
        "deepseek": "deepseek-v4-flash",
        "google": "gemini-3.5-flash",
        "ollama": "llama3.1",
        "openai": "gpt-5.4-mini",
        "siliconflow": "deepseek-ai/DeepSeek-V4-Flash",
        "zhipu": "glm-5.1",
    }.get(provider, "gpt-5.4-mini")


def default_base_url(provider: str) -> str:
    return {
        "anthropic": "https://api.anthropic.com",
        "deepseek": "https://api.deepseek.com/v1",
        "google": "https://generativelanguage.googleapis.com/v1beta/openai",
        "ollama": "http://localhost:11434/v1",
        "openai": "https://api.openai.com/v1",
        "siliconflow": "https://api.siliconflow.cn/v1",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    }.get(provider, "https://api.openai.com/v1")


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
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if key in CONFIG_KEYS and value is not None}


def effective_config() -> Dict[str, str]:
    config = read_config()
    for key in CONFIG_KEYS:
        if os.environ.get(key):
            config[key] = os.environ[key]
    return config


def apply_arg_config(config: Dict[str, str], args) -> None:
    mapping = {
        "llm_provider": "LLM_PROVIDER",
        "llm_api_type": "LLM_API_TYPE",
        "llm_model": "LLM_MODEL",
        "llm_base_url": "LLM_BASE_URL",
        "llm_key": "LLM_API_KEY",
        "openalex_key": "OPENALEX_API_KEY",
        "openalex_email": "OPENALEX_EMAIL",
        "crossref_email": "CROSSREF_EMAIL",
        "wos_key": "WOS_API_KEY",
        "db": "WOS_DB",
    }
    for attr, key in mapping.items():
        value = getattr(args, attr, "")
        if value:
            config[key] = value
    if args.source:
        config["DATA_SOURCE"] = args.source


def config_entries(include_missing: bool = False) -> List[Dict[str, object]]:
    stored = read_config()
    entries = []
    for key in CONFIG_KEYS:
        value = os.environ.get(key) or stored.get(key, "")
        if not value and not include_missing:
            continue
        source = "environment" if os.environ.get(key) else "user_config" if stored.get(key) else "missing"
        entries.append({
            "key": key,
            "configured": bool(value),
            "source": source,
            "value": mask_value(key, value) if value else "",
        })
    return entries


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


def history_path() -> Path:
    explicit = os.environ.get("PAPERSEEK_HISTORY_DB")
    if explicit:
        return Path(explicit).expanduser()
    data_dir = Path(os.environ.get("PAPERSEEK_DATA_DIR", Path.home() / ".paperseek")).expanduser()
    return data_dir / "paperseek.db"


def normalize_discipline_fields(values: Sequence[str]) -> List[str]:
    normalized = []
    label_to_id = {label.lower(): field_id for field_id, label in OPENALEX_FIELDS.items()}
    for raw in values:
        for part in split_fields(raw):
            token = part.strip()
            if not token:
                continue
            if token.startswith("https://openalex.org/fields/"):
                token = token.rsplit("/", 1)[-1]
            if token in OPENALEX_FIELDS:
                field_id = token
            else:
                field_id = label_to_id.get(token.lower())
            if field_id and field_id not in normalized:
                normalized.append(field_id)
    return normalized


def split_fields(value: str) -> List[str]:
    if not value:
        return []
    # Semicolon is the safe separator because official field labels can contain commas.
    if ";" in value:
        return [part.strip() for part in value.split(";")]
    return [value.strip()]


def field_label(field_id: str) -> str:
    return OPENALEX_FIELDS.get(field_id, field_id)


def wos_categories_for_fields(fields: Sequence[str]) -> List[str]:
    mapping = {
        "14": ["Management", "Business", "Business, Finance"],
        "17": ["Computer Science, Artificial Intelligence", "Computer Science, Information Systems", "Computer Science, Software Engineering"],
        "20": ["Economics", "Business, Finance"],
        "22": ["Engineering, Multidisciplinary", "Engineering, Electrical & Electronic"],
        "23": ["Environmental Sciences", "Environmental Studies"],
        "27": ["Medicine, General & Internal"],
        "32": ["Psychology, Multidisciplinary"],
        "33": ["Social Sciences, Interdisciplinary", "Sociology"],
    }
    categories = []
    for field_id in fields:
        categories.extend(mapping.get(field_id, []))
    return categories


def quote_wos_category(term: str) -> str:
    escaped = str(term).replace('"', r'\"')
    return f'"{escaped}"'


def standalone_warnings(config: Dict[str, str]) -> List[str]:
    warnings = ["Standalone Skill runtime does not perform OpenAlex citation expansion; install the full package for citation maps."]
    if not config.get("LLM_API_KEY"):
        warnings.append("LLM_API_KEY is not configured; query generation and ranking used deterministic heuristics.")
    return warnings


def inverted_abstract(index) -> str:
    if not isinstance(index, dict):
        return ""
    positions = []
    for word, offsets in index.items():
        if not isinstance(offsets, list):
            continue
        for offset in offsets:
            try:
                positions.append((int(offset), str(word)))
            except (TypeError, ValueError):
                continue
    return " ".join(word for _, word in sorted(positions))


def best_pdf_url(location: Dict[str, object]) -> str:
    if not isinstance(location, dict):
        return ""
    pdf_url = location.get("pdf_url")
    if pdf_url:
        return str(pdf_url)
    landing = location.get("landing_page_url")
    return str(landing or "")


def first_text(value) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def year_from_crossref_date(value) -> object:
    if not isinstance(value, dict):
        return ""
    parts = value.get("date-parts")
    if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
        return parts[0][0]
    return ""


def clean_doi(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.I)
    return value


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value).strip()


def truncate_text(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def print_smoke_text(payload: Dict[str, object]) -> None:
    status = "PASS" if payload.get("ok") else "FAIL"
    print(f"PaperSeek standalone smoke: {status}")
    print(f"Source: {payload.get('source')}")
    print(f"Query: {payload.get('query')}")
    if payload.get("ok"):
        print(f"Returned {payload.get('returned')} of {payload.get('total')} records in {payload.get('elapsed_ms')} ms")
        for title in payload.get("sample_titles") or []:
            print(f"- {title}")
    else:
        print(payload.get("message", "Request failed."))


def print_search_text(payload: Dict[str, object]) -> None:
    print(f"PaperSeek standalone search: {payload['question']}")
    print(f"Source: {payload['source']} | Query: {payload['query']}")
    print(f"Returned {len(payload['ranked'])} ranked records from {payload['total_results']} total candidates.")
    for item in payload["ranked"]:
        print(f"{item['rank']}. {item.get('title', '')} ({item.get('year', '')})")
        details = []
        if item.get("authors_text"):
            details.append(str(item["authors_text"]))
        if item.get("venue"):
            details.append(str(item["venue"]))
        if item.get("doi"):
            details.append("doi:" + str(item["doi"]))
        if details:
            print("   " + " | ".join(details))
        print(f"   score={item.get('relevance_score')} citations={item.get('citation_count', 0)}")


def supported_config_keys() -> Iterable[str]:
    return CONFIG_KEYS


if __name__ == "__main__":
    raise SystemExit(run())
