from __future__ import annotations

import re
import json
import inspect
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import count
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple
import requests

from paperseek_core.client import Configuration, ApiClient, DocumentsApi
from paperseek_core.client import ApiException
from paperseek_core.llm import LLMClient, LLMError, format_modelscope_quota
from paperseek_core.prompts import (
    SYSTEM_SEARCH_INTENT_ANALYSIS,
    SYSTEM_ARXIV_QUERY_GENERATION,
    SYSTEM_ARXIV_QUERY_BROADEN,
    SYSTEM_ARXIV_QUERY_NARROW,
    SYSTEM_PAPERHUB_QUERY_GENERATION,
    SYSTEM_PAPERHUB_QUERY_BROADEN,
    SYSTEM_PAPERHUB_QUERY_NARROW,
    SYSTEM_PUBMED_QUERY_GENERATION,
    SYSTEM_PUBMED_QUERY_BROADEN,
    SYSTEM_PUBMED_QUERY_NARROW,
    SYSTEM_GOOGLE_SCHOLAR_QUERY_GENERATION,
    SYSTEM_GOOGLE_SCHOLAR_QUERY_BROADEN,
    SYSTEM_GOOGLE_SCHOLAR_QUERY_NARROW,
    SYSTEM_QUERY_GENERATION,
    SYSTEM_QUERY_BROADEN,
    SYSTEM_QUERY_NARROW,
    SYSTEM_OPENALEX_QUERY_GENERATION,
    SYSTEM_OPENALEX_QUERY_BROADEN,
    SYSTEM_OPENALEX_QUERY_NARROW,
    SYSTEM_CROSSREF_QUERY_GENERATION,
    SYSTEM_CROSSREF_QUERY_BROADEN,
    SYSTEM_CROSSREF_QUERY_NARROW,
    SYSTEM_GENERIC_SOURCE_QUERY_GENERATION,
    SYSTEM_GENERIC_SOURCE_QUERY_BROADEN,
    SYSTEM_GENERIC_SOURCE_QUERY_NARROW,
    SYSTEM_RESULT_RANKING,
    SYSTEM_SEMANTIC_SCHOLAR_QUERY_GENERATION,
    SYSTEM_SEMANTIC_SCHOLAR_QUERY_BROADEN,
    SYSTEM_SEMANTIC_SCHOLAR_QUERY_NARROW,
)
from paperseek_core.abstracts import AbstractFetcher
from paperseek_core.disciplines import (
    apply_arxiv_category_filter,
    apply_wos_discipline_filter,
    discipline_prompt_context,
    discipline_source_note,
    discipline_summary,
    normalize_source_filter_values,
    openalex_field_ids,
)
from paperseek_core.retrieval import (
    ProviderRetrievalCapabilities,
    RetrievalLane,
    document_key,
    document_text,
    fuse_candidates_rrf,
)
from paperseek_core.sources.providers import (
    ArxivProvider,
    CitationSeedPlan,
    CrossrefProvider,
    GoogleScholarSerperProvider,
    OpenAlexProvider,
    PaperAuthor,
    PaperCitation,
    PaperHubProvider,
    PaperIdentifiers,
    PaperKeywords,
    PaperLinks,
    PaperNames,
    PaperRecord,
    PaperSource,
    ProviderError,
    ProviderSearchResult,
    PubMedProvider,
    SearchMetadata,
    SemanticScholarProvider,
)


_EXTERNAL_API_KEY_COUNTER_LOCK = Lock()
_EXTERNAL_API_KEY_COUNTERS = {}


def _split_external_api_keys(api_key: str) -> List[str]:
    keys = [item.strip() for item in re.split(r"[\s,;]+", api_key or "") if item.strip()]
    return list(dict.fromkeys(keys))


def _next_external_api_key(keys: List[str]) -> str:
    if not keys:
        return ""
    if len(keys) == 1:
        return keys[0]
    pool_key = "\0".join(keys)
    with _EXTERNAL_API_KEY_COUNTER_LOCK:
        counter = _EXTERNAL_API_KEY_COUNTERS.setdefault(pool_key, count())
        index = next(counter)
    return keys[index % len(keys)]


def _external_api_key_attempts(api_key: str, max_attempts: int = 3) -> List[str]:
    keys = _split_external_api_keys(api_key)
    if not keys:
        return [""]
    attempts = min(max(1, int(max_attempts or 1)), len(keys))
    return [_next_external_api_key(keys) for _ in range(attempts)]


def _retryable_external_status(status_code: int) -> bool:
    return status_code in (401, 403, 408, 409, 425, 429) or status_code >= 500


def _extract_json_object_text(text: str) -> str:
    raw = _strip_llm_fence(text)
    if not raw:
        return ""
    if raw.startswith("{") and raw.endswith("}"):
        return raw
    start = raw.find("{")
    if start < 0:
        return ""
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(raw[start:], start):
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw[start:index + 1]
    return ""


def _query_response_from_json(text: str) -> Tuple[str, str]:
    obj_text = _extract_json_object_text(text)
    if not obj_text:
        return "", ""
    try:
        parsed = json.loads(obj_text)
    except json.JSONDecodeError:
        return "", ""
    if not isinstance(parsed, dict):
        return "", ""
    query_value = ""
    for key in ("query", "search_query", "query_string", "source_query", "term", "wos_query"):
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            query_value = value
            break
        if isinstance(value, dict):
            nested = value.get("value") or value.get("query")
            if isinstance(nested, str) and nested.strip():
                query_value = nested
                break
    query = query_value.strip()
    rationale_parts = []
    for key in ("rationale", "adjustment", "adjustment_direction", "reason", "diagnostic_note"):
        value = parsed.get(key)
        if isinstance(value, list):
            value = "; ".join(str(item).strip() for item in value if str(item).strip())
        value = str(value or "").strip()
        if value:
            rationale_parts.append(value)
    return query, "\n".join(rationale_parts).strip()


def _trim_boolean_edges(query: str) -> str:
    query = re.sub(r"^\s*(?:AND|OR|NOT)\b\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\s+\b(?:AND|OR|NOT)\s*$", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\(\s*(?:AND|OR)\s+", "(", query, flags=re.IGNORECASE)
    query = re.sub(r"\s+(?:AND|OR)\s*\)", ")", query, flags=re.IGNORECASE)
    return query.strip()


def _parentheses_are_balanced(query: str) -> bool:
    depth = 0
    for char in query or "":
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _looks_truncated_or_malformed_query(query: str) -> bool:
    value = (query or "").strip()
    if not value:
        return True
    if value.count('"') % 2:
        return True
    if not _parentheses_are_balanced(value):
        return True
    if re.search(r"\b(?:AND|OR|NOT)\s*$", value, flags=re.IGNORECASE):
        return True
    if re.search(r"\(\s*$", value):
        return True
    return False


def _sanitize_openalex_query(query: str) -> str:
    """Keep OpenAlex search= queries inside the syntax accepted by default search."""
    original = (query or "").strip()
    if not original:
        return ""
    cleaned = (
        original.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )
    cleaned = re.sub(r"^\s*(?:search|q)\s*=\s*", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.strip().strip("`")
    cleaned = re.sub(r"\b(?:filter|per-page|page|sort|select|fields)\s*=[^\s]+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"([A-Za-z0-9])[*?]+\b", r"\1", cleaned)
    cleaned = cleaned.replace("*", "").replace("?", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([)])", r"\1", cleaned)
    cleaned = re.sub(r"([(])\s+", r"\1", cleaned)
    cleaned = _trim_boolean_edges(cleaned)
    return cleaned or original


def _provider_error_text(exc: ProviderError) -> str:
    parts = [str(exc)]
    if exc.status:
        parts.append(f"HTTP {exc.status}")
    if exc.body:
        parts.append(str(exc.body))
    return " ".join(parts)


def _queries_equivalent(left: str, right: str) -> bool:
    return re.sub(r"\s+", " ", (left or "").strip()).lower() == re.sub(r"\s+", " ", (right or "").strip()).lower()


def _strip_llm_fence(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


def _extract_intent_summary(text: str, max_chars: int = 1600) -> str:
    raw = _strip_llm_fence(text)
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        parts = []
        for key in ("intent", "core_concepts", "likely_synonyms", "boundaries", "adjustment_strategy"):
            value = parsed.get(key)
            if isinstance(value, list):
                value = "; ".join(str(item).strip() for item in value if str(item).strip())
            value = str(value or "").strip()
            if value:
                parts.append(f"{key}: {value}")
        raw = "\n".join(parts) if parts else raw
    raw = re.sub(r"\s+\n", "\n", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
    if len(raw) > max_chars:
        raw = raw[:max_chars].rstrip() + "..."
    return raw


def _repair_server_error_query(query: str) -> str:
    """Rewrite fragile exact phrases into proximity expressions after WoS 5xx errors."""
    normalized = (
        query.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )

    def phrase_to_near(match):
        phrase = re.sub(r"\s+", " ", match.group(1).strip())
        if re.search(r"\b(AND|OR|NOT|NEAR|SAME)\b", phrase, re.IGNORECASE):
            return match.group(0)
        terms = [t for t in phrase.split(" ") if t]
        if len(terms) < 2:
            return match.group(0)
        return "(" + " NEAR/2 ".join(terms) + ")"

    repaired = re.sub(r'"([^"]+)"', phrase_to_near, normalized)
    repaired = re.sub(r"\s+", " ", repaired).strip()
    return repaired if repaired != query else query


def _simplify_server_error_query(query: str) -> str:
    """Fallback query for WoS 5xx errors: avoid proximity and exact-phrase operators."""
    simplified = (
        query.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )

    def phrase_to_and(match):
        phrase = re.sub(r"\s+", " ", match.group(1).strip())
        if re.search(r"\b(AND|OR|NOT|NEAR|SAME)\b", phrase, re.IGNORECASE):
            return match.group(0)
        terms = [t for t in phrase.split(" ") if t]
        if len(terms) < 2:
            return match.group(0)
        return "(" + " AND ".join(terms) + ")"

    simplified = re.sub(r'"([^"]+)"', phrase_to_and, simplified)
    simplified = re.sub(r"([\w*?-]+)\s+NEAR/\d+\s+([\w*?-]+)", r"\1 AND \2", simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"([\w*?-]+)\s+NEAR\s+([\w*?-]+)", r"\1 AND \2", simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"([\w*?-]+)\s+SAME\s+([\w*?-]+)", r"\1 AND \2", simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"\s+", " ", simplified).strip()
    return simplified if simplified != query else query


def _make_starter_safe_query(query: str) -> str:
    """Normalize LLM output to the most stable WoS Starter API query subset."""
    safe_query = _simplify_server_error_query(query)
    # Run twice to catch nested forms that expose another proximity expression after
    # phrase simplification.
    safe_query = _simplify_server_error_query(safe_query)
    return safe_query


def _server_error_query_variants(query: str) -> list:
    variants = []
    for candidate in (
        _simplify_server_error_query(query),
        _repair_server_error_query(query),
        _simplify_server_error_query(_repair_server_error_query(query)),
    ):
        if candidate != query and candidate not in variants:
            variants.append(candidate)
    return variants


def _describe_document(doc, idx: int) -> str:
    """Produce a compact text description of a document for the LLM ranking prompt."""
    parts = [f"{idx}. UID: {doc.uid}"]
    provider = getattr(doc, "provider", "")
    if provider:
        parts.append(f"   Provider: {provider}")
    if doc.title:
        parts.append(f"   Title: {doc.title}")
    if doc.types:
        parts.append(f"   Document types: {'; '.join(doc.types[:5])}")
    if doc.source:
        src = doc.source
        src_parts = []
        if src.source_title:
            src_parts.append(src.source_title)
        if src.publish_year:
            src_parts.append(str(src.publish_year))
        if src.volume:
            src_parts.append(f"V{src.volume}")
        if src.issue:
            src_parts.append(f"I{src.issue}")
        if src_parts:
            parts.append(f"   Source: {', '.join(src_parts)}")
    if doc.names and doc.names.authors:
        authors = [
            a.display_name or a.wos_standard or ""
            for a in doc.names.authors[:5]
        ]
        parts.append(f"   Authors: {', '.join(a for a in authors if a)}")
    if doc.keywords and doc.keywords.author_keywords:
        parts.append(f"   Keywords: {'; '.join(doc.keywords.author_keywords[:8])}")
    abstract = getattr(doc, "abstract", "")
    if abstract:
        parts.append(f"   Abstract: {abstract[:1200]}")
    return "\n".join(parts)


def _citation_count(doc) -> int:
    total = 0
    for citation in getattr(doc, "citations", []) or []:
        total += getattr(citation, "count", 0) or 0
    return total


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _to_int(value: Any) -> Optional[int]:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = _first_text(item)
            if text:
                return text
        return ""
    if isinstance(value, dict):
        for key in ("value", "name", "displayName", "display_name", "title"):
            text = _first_text(value.get(key))
            if text:
                return text
        return ""
    return str(value or "").strip()


def _wos_author(item: Any) -> PaperAuthor:
    if isinstance(item, dict):
        return PaperAuthor(
            display_name=_first_text(item.get("displayName") or item.get("display_name") or item.get("name")),
            wos_standard=_first_text(item.get("wosStandard") or item.get("wos_standard")),
            researcher_id=_first_text(item.get("researcherId") or item.get("researcher_id")),
        )
    return PaperAuthor(display_name=_first_text(item))


def _wos_record_from_json(item: dict[str, Any]) -> PaperRecord:
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    names = item.get("names") if isinstance(item.get("names"), dict) else {}
    identifiers = item.get("identifiers") if isinstance(item.get("identifiers"), dict) else {}
    links = item.get("links") if isinstance(item.get("links"), dict) else {}
    keywords = item.get("keywords") if isinstance(item.get("keywords"), dict) else {}
    citations = []
    for citation in _as_list(item.get("citations")):
        if isinstance(citation, dict):
            citations.append(PaperCitation(db=_first_text(citation.get("db")), count=_to_int(citation.get("count")) or 0))

    return PaperRecord(
        uid=_first_text(item.get("uid") or item.get("id") or identifiers.get("wosuid") or item.get("title")),
        title=_first_text(item.get("title")),
        types=[_first_text(value) for value in _as_list(item.get("types")) if _first_text(value)],
        source_types=[_first_text(value) for value in _as_list(item.get("sourceTypes")) if _first_text(value)],
        source=PaperSource(
            source_title=_first_text(source.get("sourceTitle") or source.get("source_title")),
            publish_year=_to_int(source.get("publishYear") or source.get("publish_year")),
            publish_month=_first_text(source.get("publishMonth") or source.get("publish_month")),
            volume=_first_text(source.get("volume")),
            issue=_first_text(source.get("issue")),
        ),
        names=PaperNames(authors=[_wos_author(author) for author in _as_list(names.get("authors"))]),
        links=PaperLinks(
            record=_first_text(links.get("record")),
            citing_articles=_first_text(links.get("citingArticles") or links.get("citing_articles")),
            references=_first_text(links.get("references")),
            related=_first_text(links.get("related")),
            landing_page=_first_text(links.get("record") or links.get("landingPage") or links.get("landing_page")),
        ),
        citations=citations,
        identifiers=PaperIdentifiers(
            doi=_first_text(identifiers.get("doi")),
            issn=_first_text(identifiers.get("issn")),
            eissn=_first_text(identifiers.get("eissn")),
            isbn=_first_text(identifiers.get("isbn")),
            eisbn=_first_text(identifiers.get("eisbn")),
            pmid=_first_text(identifiers.get("pmid")),
        ),
        keywords=PaperKeywords(author_keywords=[_first_text(value) for value in _as_list(keywords.get("authorKeywords") or keywords.get("author_keywords")) if _first_text(value)]),
        provider="wos",
        raw=item,
    )


def _wos_result_from_json(payload: dict[str, Any], limit: int) -> ProviderSearchResult:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    hits = payload.get("hits") if isinstance(payload.get("hits"), list) else []
    return ProviderSearchResult(
        metadata=SearchMetadata(
            total=_to_int(metadata.get("total")) or 0,
            page=_to_int(metadata.get("page")) or 1,
            limit=_to_int(metadata.get("limit")) or limit,
        ),
        hits=[_wos_record_from_json(item) for item in hits if isinstance(item, dict)],
    )


class PaperSeekAgent:
    def __init__(self, config, llm_client: LLMClient, abstract_fetcher: Optional[AbstractFetcher] = None):
        self.config = config
        self.llm = llm_client
        self.abstract_fetcher = abstract_fetcher or AbstractFetcher()
        self.data_source = (getattr(config, "data_source", "wos") or "wos").lower()
        self.discipline_fields = normalize_source_filter_values(
            self.data_source,
            getattr(config, "discipline_fields", ()),
        )
        try:
            self.config.discipline_fields = self.discipline_fields
        except Exception:
            pass
        self.event_handler: Optional[Callable[[dict], None]] = None
        self.citation_map: dict = self._empty_citation_map(enabled=getattr(config, "expand_citations", True))
        self.search_intent: str = ""
        self.last_query_audit: str = ""
        self.retrieval_metadata_by_key: Dict[str, Dict[str, Any]] = {}
        self.ranking_steps: Dict[str, Dict[str, Any]] = {}
        self.ranking_context: Dict[str, Any] = {}

        self.documents_api = None
        self.provider = None
        if self.data_source == "openalex":
            self.provider = OpenAlexProvider(
                api_key=getattr(config, "openalex_api_key", ""),
                email=getattr(config, "openalex_email", ""),
            )
        elif self.data_source == "crossref":
            self.provider = CrossrefProvider(email=getattr(config, "crossref_email", ""))
        elif self.data_source == "arxiv":
            self.provider = ArxivProvider()
        elif self.data_source == "semanticscholar":
            self.provider = SemanticScholarProvider(api_key=getattr(config, "semantic_scholar_api_key", ""))
        elif self.data_source == "pubmed":
            self.provider = PubMedProvider(
                api_key=getattr(config, "pubmed_api_key", ""),
                email=getattr(config, "pubmed_email", ""),
                tool=getattr(config, "pubmed_tool", "paperseek"),
            )
        elif self.data_source == "googlescholar":
            self.provider = GoogleScholarSerperProvider(api_key=getattr(config, "serper_api_key", ""))
        elif self.data_source == "paperhub":
            self.provider = PaperHubProvider()
        else:
            wos_cfg = Configuration(api_key={"ClarivateApiKeyAuth": config.wos_api_key})
            self.documents_api = DocumentsApi(ApiClient(configuration=wos_cfg))

    def search(self, question: str, verbose: bool = False, event_handler: Optional[Callable[[dict], None]] = None) -> dict:
        """Main entry: natural language question -> dict with results and metadata."""
        self.event_handler = event_handler
        try:
            return self._search(question, verbose=verbose)
        finally:
            self.event_handler = None

    def _search(self, question: str, verbose: bool = False) -> dict:
        self.search_intent = self._analyze_intent(question)
        if self.search_intent:
            self._emit_stage("query", "processing", source=self.data_source, intent=self.search_intent)
        query = self._source_safe_query(self._apply_discipline_filter(self._generate_query(question)))
        history = []
        iteration = 0
        total = 0
        hits = []

        configured_iterations = max(1, int(getattr(self.config, "max_iterations", 5) or 5))
        adaptive_max_iterations = self._adaptive_max_iterations(configured_iterations)
        while iteration < adaptive_max_iterations:
            iteration += 1
            if self.data_source == "wos":
                safe_query = _make_starter_safe_query(query)
                sanitize_message = "Converted the generated query to the stable WoS Starter subset before calling the API."
            else:
                safe_query = self._source_safe_query(query)
                sanitize_message = f"Sanitized the generated {self._source_label()} query before calling the API."
            if safe_query != query:
                row = {
                    "iteration": iteration,
                    "query": query,
                    "total": None,
                    "action": "sanitize",
                    "next_query": safe_query,
                    "message": sanitize_message,
                }
                history.append(row)
                self._emit_stage("search", "processing", history=history, final_query=safe_query)
                query = safe_query

            if verbose:
                print(f"[Iteration {iteration}] Query: {query}", file=sys.stderr)

            server_error_variants = _server_error_query_variants(query)
            provider_repair_attempts = set()
            try:
                while True:
                    try:
                        self._emit_stage(
                            "search",
                            "processing",
                            iteration=iteration,
                            query=query,
                            history=history,
                            final_query=query,
                        )
                        self._emit_log(f"{self._source_label()} request started: {self._source_request_label(query)}")
                        result = self._provider_search(query)
                        self._emit_log(self._source_response_log(result))
                        break
                    except ProviderError as e:
                        repair_key = (query, e.status, str(e)[:200])
                        if repair_key not in provider_repair_attempts and len(provider_repair_attempts) < 2:
                            provider_repair_attempts.add(repair_key)
                            repaired_query = self._repair_query_after_provider_error(question, query, e)
                            if repaired_query and not _queries_equivalent(query, repaired_query):
                                row = {
                                    "iteration": iteration,
                                    "query": query,
                                    "total": None,
                                    "action": "repair",
                                    "next_query": repaired_query,
                                    "message": f"{self._source_label()} rejected the query; repaired the source syntax and retried.",
                                }
                                history.append(row)
                                self._emit_stage("search", "processing", history=history, final_query=repaired_query)
                                self._emit_log(f"{self._source_label()} query repaired after API error; retrying request.")
                                query = repaired_query
                                continue
                        raise
                    except ApiException as e:
                        if e.status == 512 and server_error_variants:
                            repaired_query = server_error_variants.pop(0)
                            if repaired_query != query:
                                action = "repair" if "NEAR/" in repaired_query.upper() else "simplify"
                                row = {
                                    "iteration": iteration,
                                    "query": query,
                                    "total": None,
                                    "action": action,
                                    "next_query": repaired_query,
                                    "message": "WoS returned HTTP 512; rewrote the query into a simpler supported form and retried.",
                                }
                                history.append(row)
                                self._emit_stage("search", "processing", history=history, final_query=repaired_query)
                                query = repaired_query
                                if verbose:
                                    print(f"[Iteration {iteration}] Rewrote query after 512: {query}", file=sys.stderr)
                                continue
                        raise
            except ApiException as e:
                if e.status == 400 and "query" in str(e.body).lower():
                    current_query = query
                    feedback = self._result_feedback(query, [], None, "syntax rejected")
                    revised_query = self._apply_discipline_filter(self._broaden_query(question, query, feedback))
                    query_audit = self._consume_query_audit()
                    if _queries_equivalent(current_query, revised_query):
                        e.query = query
                        e.iteration = iteration
                        raise
                    query = revised_query
                    row = {
                        "iteration": iteration,
                        "query": current_query,
                        "total": None,
                        "action": "broaden",
                        "next_query": query,
                        "message": "WoS rejected the query syntax; generated a broader replacement query.",
                        "rationale": query_audit,
                    }
                    history.append(row)
                    self._emit_stage("search", "processing", history=history, final_query=query)
                    continue
                e.query = query
                e.iteration = iteration
                raise

            total = result.metadata.total if result.metadata and result.metadata.total is not None else 0
            hits = result.hits or []

            if verbose:
                print(f"[Iteration {iteration}] Total results: {total}", file=sys.stderr)

            if total == 0 and self._should_broaden_after_result(total, iteration, configured_iterations, adaptive_max_iterations):
                current_query = query
                feedback = self._result_feedback(query, hits, total, "too few or zero records")
                revised_query = self._apply_discipline_filter(self._broaden_query(question, query, feedback))
                query_audit = self._consume_query_audit()
                if _queries_equivalent(current_query, revised_query):
                    self._complete_after_unchanged_revision(history, iteration, current_query, total, hits, "broader")
                    break
                query = revised_query
                row = {
                    "iteration": iteration,
                    "query": current_query,
                    "total": total,
                    "action": "broaden",
                    "next_query": query,
                    "message": "No records found; generated a broader query.",
                    "rationale": query_audit,
                }
                history.append(row)
                self._emit_stage("search", "processing", total=total, history=history, final_query=query, preview=self._preview_hits(hits))
                continue
            elif self._should_broaden_after_result(total, iteration, configured_iterations, adaptive_max_iterations):
                current_query = query
                feedback = self._result_feedback(query, hits, total, f"below target minimum {self.config.target_min}")
                revised_query = self._apply_discipline_filter(self._broaden_query(question, query, feedback))
                query_audit = self._consume_query_audit()
                if _queries_equivalent(current_query, revised_query):
                    self._complete_after_unchanged_revision(history, iteration, current_query, total, hits, "broader")
                    break
                query = revised_query
                row = {
                    "iteration": iteration,
                    "query": current_query,
                    "total": total,
                    "action": "broaden",
                    "next_query": query,
                    "message": f"Only {total} records found, below the target minimum of {self.config.target_min}; generated a broader query.",
                    "rationale": query_audit,
                }
                history.append(row)
                self._emit_stage("search", "processing", total=total, history=history, final_query=query, preview=self._preview_hits(hits))
                continue
            elif self._should_narrow_after_result(total, iteration, configured_iterations, adaptive_max_iterations):
                current_query = query
                adjustment = f"above LLM pre-ranking safety pool {self._retrieval_pool_max()}"
                message = f"{total} records found, above the LLM pre-ranking safety pool of {self._retrieval_pool_max()}; generated a narrower query."
                feedback = self._result_feedback(query, hits, total, adjustment)
                revised_query = self._apply_discipline_filter(self._narrow_query(question, query, feedback))
                query_audit = self._consume_query_audit()
                if _queries_equivalent(current_query, revised_query):
                    if total > self._retrieval_pool_max() and iteration < adaptive_max_iterations:
                        retry_feedback = (
                            f"{feedback}\n"
                            "The previous narrowing response did not change the query. "
                            "Return a different valid query that adds a missing central facet, stricter phrase, method, domain, population, or publication-type term from the interpreted intent. "
                            "Do not remove existing core intent terms."
                        )
                        revised_query = self._apply_discipline_filter(self._narrow_query(question, current_query, retry_feedback))
                        query_audit = self._consume_query_audit()
                    if _queries_equivalent(current_query, revised_query):
                        self._complete_after_unchanged_revision(history, iteration, current_query, total, hits, "narrower")
                        break
                query = revised_query
                row = {
                    "iteration": iteration,
                    "query": current_query,
                    "total": total,
                    "action": "narrow",
                    "next_query": query,
                    "message": message,
                    "rationale": query_audit,
                }
                history.append(row)
                self._emit_stage("search", "processing", total=total, history=history, final_query=query, preview=self._preview_hits(hits))
                continue
            else:
                if total == 0:
                    action = "empty"
                    message = "No records found before the iteration limit was reached."
                elif total < self.config.target_min:
                    action = "accept_low"
                    message = f"Accepted {total} records at the iteration limit, below the target minimum of {self.config.target_min}."
                elif total > self._retrieval_pool_max():
                    action = "accept_high"
                    message = f"Accepted {total} records at the iteration limit, above the LLM pre-ranking safety pool of {self._retrieval_pool_max()}; the fused candidate pool will be truncated before LLM ranking."
                elif total > self.config.target_max:
                    action = "accept_pool"
                    message = f"Accepted {total} records for downstream pre-ranking; final displayed results are selected after retrieval fusion and LLM ranking."
                else:
                    action = "accept"
                    message = f"Accepted {total} records within the target range."
                row = {
                    "iteration": iteration,
                    "query": query,
                    "total": total,
                    "action": action,
                    "next_query": None,
                    "message": message,
                }
                history.append(row)
                self._emit_stage(
                    "search",
                    "complete",
                    total=total,
                    history=history,
                    final_query=query,
                    preview=self._preview_hits(hits),
                )
                break

        if iteration > configured_iterations or (not hits and total == 0):
            if verbose:
                print(f"[Done] {total} total results after {iteration} iterations.", file=sys.stderr)

        self.ranking_steps = {}
        ranking_context = {
            "source": self.data_source,
            "total": total,
            "history": history,
            "final_query": query,
            "preview": self._preview_hits(hits),
        }
        self.ranking_context = dict(ranking_context)
        self._emit_stage("ranking", "processing", candidate_count=len(hits or []), **ranking_context)
        if total == 0 and not hits:
            retrieved = []
        else:
            retrieved = self._retrieve_candidates(question, query, hits)
        self._emit_ranking_step(
            "candidate_preparation",
            "processing",
            "Preparing LLM candidate list",
            current=0,
            total=max(1, len(retrieved or [])),
            detail=f"{len(retrieved or [])} fused candidates before citation expansion.",
        )
        candidates = self._prepare_candidates(question, retrieved)
        self._emit_ranking_step(
            "candidate_preparation",
            "complete",
            "Preparing LLM candidate list",
            current=len(candidates),
            total=max(1, len(candidates)),
            detail=f"{len(candidates)} candidates ready before LLM ranking.",
            candidate_count=len(candidates),
        )
        ranking_candidate_limit = self._llm_ranking_candidate_limit()
        if len(candidates) > ranking_candidate_limit:
            self._emit_log(
                f"LLM ranking candidate list truncated: candidates={len(candidates)}; "
                f"ranking_candidate_limit={ranking_candidate_limit}."
            )
            candidates = candidates[:ranking_candidate_limit]
        if len(candidates) != len(hits or []):
            self._emit_stage("ranking", "processing", candidate_count=len(candidates), **ranking_context)
        ranked_all = self._rank_results(question, candidates, ranking_context=ranking_context)
        ranked = self._select_ranked_output(ranked_all)
        self._finalize_citation_map(ranked)

        if self.config.fetch_abstracts:
            self._emit_log("External abstract enrichment started.")
            self._emit_ranking_step(
                "abstract_enrichment",
                "processing",
                "Abstract enrichment",
                current=0,
                total=max(1, len(ranked)),
                detail="Fetching missing abstracts when available.",
            )
            ranked = self._enrich_with_abstracts(ranked)
            self._emit_log("External abstract enrichment completed.")
            self._emit_ranking_step(
                "abstract_enrichment",
                "complete",
                "Abstract enrichment",
                current=len(ranked),
                total=max(1, len(ranked)),
                detail="Abstract enrichment completed.",
            )

        self._emit_stage(
            "ranking",
            "complete",
            ranked_count=len(ranked),
            ranking_steps=list(self.ranking_steps.values()),
            **ranking_context,
        )

        self._emit_stage("results", "complete", ranked_count=len(ranked), total=total)

        return {
            "question": question,
            "search_intent": self.search_intent,
            "final_query": query,
            "db": self.config.wos_db if self.data_source == "wos" else self.data_source.upper(),
            "source": self.data_source,
            "field": self._field_summary(),
            "total": total,
            "iterations": iteration,
            "history": history,
            "citation_map": self.citation_map,
            "ranking_steps": list(self.ranking_steps.values()),
            "ranked": ranked,
        }

    def _provider_search(self, query: str):
        return self._provider_search_lane(query, RetrievalLane.RELEVANCE, self._candidate_limit(), page=1)

    def _source_safe_query(self, query: str) -> str:
        if self.data_source == "openalex":
            return _sanitize_openalex_query(query)
        return (query or "").strip()

    def _source_query_format_issue(self, query: str) -> str:
        if not (query or "").strip():
            return "missing query field in JSON response"
        if self.data_source in {"openalex", "arxiv", "pubmed", "wos"} and _looks_truncated_or_malformed_query(query):
            return "unbalanced quotation marks, parentheses, or trailing Boolean operator"
        return ""

    def _consume_query_audit(self) -> str:
        audit = self.last_query_audit
        self.last_query_audit = ""
        return audit

    def _finalize_source_query(
        self,
        question: str,
        raw: str,
        *,
        current_query: str = "",
        feedback: str = "",
        system_prompt: str = "",
        log_name: str = "",
        output_label: str = "query string",
        operation: str = "generate",
    ) -> str:
        query, rationale = _query_response_from_json(raw)
        query = self._source_safe_query(self._apply_discipline_filter(query))
        self.last_query_audit = rationale
        issue = self._source_query_format_issue(query)
        if not issue:
            return query
        self._emit_log(f"{self._source_label()} query output looked malformed or truncated ({issue}); requesting a replacement.")
        repaired = self._retry_malformed_source_query(
            question,
            query,
            current_query=current_query,
            feedback=feedback,
            system_prompt=system_prompt,
            log_name=log_name,
            output_label=output_label,
            operation=operation,
            issue=issue,
        )
        if repaired:
            return repaired
        self.last_query_audit = ""
        if current_query:
            return current_query
        raise LLMError(f"{self._source_label()} query generation failed: LLM did not return valid JSON with a query field.")

    def _retry_malformed_source_query(
        self,
        question: str,
        malformed_query: str,
        *,
        current_query: str = "",
        feedback: str = "",
        system_prompt: str = "",
        log_name: str = "",
        output_label: str = "query string",
        operation: str = "generate",
        issue: str = "",
    ) -> str:
        if not system_prompt:
            system_prompt = self._syntax_repair_prompt()
        retry_log = f"{log_name}_format_retry" if log_name else f"{self.data_source}_query_format_retry"
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Research question: {question}\n"
                    f"{self._intent_context()}"
                    f"{self._discipline_context()}\n"
                    f"{feedback}"
                    f"Previous valid query: {current_query or '(none)'}\n"
                    f"Rejected malformed {operation} output: {malformed_query or '(empty)'}\n"
                    f"Format problem: {issue or 'malformed or truncated output'}.\n\n"
                    f"Generate a complete replacement {output_label}. "
                    "Do not return a fragment. Keep quotation marks and parentheses balanced."
                    f"{self._strict_query_output_instruction(output_label)}"
                ),
            },
        ]
        self._llm_request_log(retry_log)
        try:
            raw = self.llm.chat(messages, temperature=self._query_temperature())
            self._llm_response_log(retry_log)
        except Exception as exc:
            self._emit_log(f"{self._source_label()} query format retry skipped after LLM error: {exc}")
            return ""
        query, rationale = _query_response_from_json(raw)
        query = self._source_safe_query(self._apply_discipline_filter(query))
        self.last_query_audit = rationale
        if query and not self._source_query_format_issue(query):
            return query
        self._emit_log(f"{self._source_label()} query format retry returned another malformed query; keeping the previous valid query.")
        self.last_query_audit = ""
        return ""

    def _repair_query_after_provider_error(self, question: str, query: str, error: ProviderError) -> str:
        if self.data_source == "openalex":
            sanitized = _sanitize_openalex_query(query)
            if sanitized and not self._source_query_format_issue(sanitized) and not _queries_equivalent(query, sanitized):
                return sanitized
        if not self._is_repairable_provider_error(error):
            return ""
        return self._repair_source_query_syntax(question, query, error)

    def _is_repairable_provider_error(self, error: ProviderError) -> bool:
        text = _provider_error_text(error).lower()
        if error.status in (400, 422):
            return True
        markers = (
            "invalid query",
            "invalid query parameters",
            "syntax",
            "wildcard",
            "parse",
            "unbalanced",
            "unsupported",
            "malformed",
            "bad query",
        )
        return any(marker in text for marker in markers)

    def _repair_source_query_syntax(self, question: str, query: str, error: ProviderError) -> str:
        source_label = self._source_label()
        error_text = _provider_error_text(error)
        messages = [
            {
                "role": "system",
                "content": self._syntax_repair_prompt(),
            },
            {
                "role": "user",
                "content": (
                    f"Source: {source_label}\n"
                    f"Research question: {question}\n"
                    f"{self._intent_context()}"
                    f"{self._discipline_context()}\n"
                    f"Rejected query:\n{query}\n\n"
                    f"API error:\n{error_text[:1200]}\n\n"
                    "Return exactly one corrected query string that preserves the research intent "
                    "and follows the source API rules."
                    f"{self._strict_query_output_instruction('corrected source query string')}"
                ),
            },
        ]
        self._llm_request_log(f"{self.data_source}_query_syntax_repair")
        try:
            raw = self.llm.chat(messages, temperature=self._query_temperature())
            self._llm_response_log(f"{self.data_source}_query_syntax_repair")
        except Exception as exc:
            self._emit_log(f"{source_label} query syntax repair skipped after LLM error: {exc}")
            return ""
        repaired, rationale = _query_response_from_json(raw)
        repaired = self._source_safe_query(self._apply_discipline_filter(repaired))
        self.last_query_audit = rationale
        if not repaired or self._source_query_format_issue(repaired):
            self.last_query_audit = ""
            return ""
        return repaired

    def _syntax_repair_prompt(self) -> str:
        if self.data_source == "openalex":
            return (
                SYSTEM_OPENALEX_QUERY_GENERATION
                + "\nRepair task: correct only syntax that the OpenAlex /works search parameter rejected. "
                "Keep the output as a single search= query value. Do not use search.exact, filters, wildcards, URLs, or API parameters."
            )
        if self.data_source == "crossref":
            return (
                SYSTEM_CROSSREF_QUERY_GENERATION
                + "\nRepair task: convert the rejected text into a valid Crossref query.bibliographic value. "
                "Keep plain bibliographic terms only."
            )
        if self.data_source == "arxiv":
            return SYSTEM_ARXIV_QUERY_GENERATION + "\nRepair task: return a valid arXiv search_query value only."
        if self.data_source == "semanticscholar":
            return SYSTEM_SEMANTIC_SCHOLAR_QUERY_GENERATION + "\nRepair task: return a valid Semantic Scholar query value only."
        if self.data_source == "pubmed":
            return SYSTEM_PUBMED_QUERY_GENERATION + "\nRepair task: return a valid PubMed ESearch term value only."
        if self.data_source == "googlescholar":
            return SYSTEM_GOOGLE_SCHOLAR_QUERY_GENERATION + "\nRepair task: return a valid Google Scholar q value only."
        if self.data_source == "paperhub":
            return SYSTEM_PAPERHUB_QUERY_GENERATION + "\nRepair task: return valid plain PaperHub search text only."
        return SYSTEM_QUERY_GENERATION + "\nRepair task: return a valid Web of Science Starter API q value only."

    def _provider_search_lane(self, query: str, lane: str, limit: int, page: int = 1):
        if self.data_source == "openalex":
            return self._call_provider_search(query=query, limit=limit, page=page, field_ids=openalex_field_ids(self.discipline_fields), lane=lane)
        if self.data_source == "crossref":
            return self._call_provider_search(query=query, limit=limit, page=page, lane=lane)
        if self.provider:
            return self._call_provider_search(query=query, limit=limit, page=page, lane=lane)
        sort_field = self._wos_sort_field_for_lane(lane)
        try:
            return self.documents_api.documents_get(
                q=query,
                db=self.config.wos_db,
                limit=limit,
                sort_field=sort_field,
            )
        except ApiException as exc:
            if exc.status == 429:
                self._emit_log("WoS Starter rate limit reached; waiting briefly before one retry.")
                time.sleep(2.0)
                return self.documents_api.documents_get(
                    q=query,
                    db=self.config.wos_db,
                    limit=limit,
                    sort_field=sort_field,
                )
            raise
        except Exception as exc:
            self._emit_log(f"WoS generated client parsing failed; retrying with raw JSON parser: {exc.__class__.__name__}.")
            return self._wos_raw_search(query, limit=limit, sort_field=sort_field)

    def _call_provider_search(self, **kwargs):
        search = self.provider.search
        signature = inspect.signature(search)
        accepts_kwargs = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
        if accepts_kwargs:
            return search(**kwargs)
        supported = {name: value for name, value in kwargs.items() if name in signature.parameters}
        return search(**supported)

    @staticmethod
    def _wos_sort_field_for_lane(lane: str) -> str:
        if lane == RetrievalLane.IMPACT:
            return "TC+D"
        if lane == RetrievalLane.RECENT:
            return "PY+D"
        return "RS+D"

    def _wos_raw_search(self, query: str, limit: Optional[int] = None, sort_field: str = "RS+D") -> ProviderSearchResult:
        limit = limit or self._candidate_limit()
        response = requests.get(
            "https://api.clarivate.com/apis/wos-starter/v1/documents",
            params={"q": query, "db": self.config.wos_db, "limit": limit, "sortField": sort_field},
            headers={"Accept": "application/json", "X-ApiKey": self.config.wos_api_key},
            timeout=45,
        )
        if response.status_code == 429:
            self._emit_log("WoS Starter raw request rate limited; waiting briefly before one retry.")
            time.sleep(2.0)
            response = requests.get(
                "https://api.clarivate.com/apis/wos-starter/v1/documents",
                params={"q": query, "db": self.config.wos_db, "limit": limit, "sortField": sort_field},
                headers={"Accept": "application/json", "X-ApiKey": self.config.wos_api_key},
                timeout=45,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise ApiException(status=response.status_code, reason=response.reason, body=response.text)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiException(status=response.status_code, reason="Invalid JSON response", body=response.text) from exc
        return _wos_result_from_json(payload, limit)

    def _apply_discipline_filter(self, query: str) -> str:
        if self.data_source == "wos":
            return apply_wos_discipline_filter(query, self.discipline_fields)
        if self.data_source == "arxiv":
            return apply_arxiv_category_filter(query, self.discipline_fields)
        return query

    def _discipline_context(self) -> str:
        return discipline_prompt_context(
            self.discipline_fields,
            self.data_source,
            getattr(self.config, "search_field", ""),
        )

    def _field_summary(self) -> str:
        parts = []
        if self.data_source == "openalex":
            selected = discipline_summary(self.discipline_fields)
            if selected:
                parts.append(selected)
        elif self.discipline_fields:
            parts.append(", ".join(self.discipline_fields))
        if getattr(self.config, "search_field", ""):
            parts.append(str(self.config.search_field))
        return "; ".join(parts)

    def _retrieval_pool_max(self) -> int:
        try:
            return max(1, int(getattr(self.config, "retrieval_pool_max", 3000) or 3000))
        except (TypeError, ValueError):
            return 3000

    def _retrieval_pool_min(self) -> int:
        try:
            configured = max(0, int(getattr(self.config, "retrieval_pool_min", 5) or 5))
        except (TypeError, ValueError):
            configured = 5
        try:
            target_max = max(1, int(getattr(self.config, "target_max", 50) or 50))
        except (TypeError, ValueError):
            target_max = 50
        return min(configured, target_max)

    def _adaptive_max_iterations(self, configured_iterations: int) -> int:
        configured = max(1, int(configured_iterations or 5))
        requested = getattr(self.config, "adaptive_max_iterations", None)
        try:
            if requested is not None:
                return max(configured, int(requested))
        except (TypeError, ValueError):
            pass
        return max(configured + 8, configured * 3, 10)

    def _llm_ranking_candidate_limit(self) -> int:
        try:
            configured = max(1, int(getattr(self.config, "ranking_candidate_limit", 256) or 256))
        except (TypeError, ValueError):
            configured = 256
        try:
            target_max = max(1, int(getattr(self.config, "target_max", 50) or 50))
        except (TypeError, ValueError):
            target_max = 50
        return min(max(configured, target_max), self._retrieval_pool_max())

    def _ranked_output_floor(self) -> int:
        return 50

    def _select_ranked_output(self, ranked: list) -> list:
        if len(ranked) <= self._ranked_output_floor():
            return ranked
        high_score = [entry for entry in ranked if self._ranking_score(entry) >= 5]
        if len(high_score) > self._ranked_output_floor():
            return high_score
        return ranked[: self._ranked_output_floor()]

    def _ranking_score(self, entry: Any) -> float:
        try:
            return float((entry or {}).get("score", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _should_broaden_after_result(self, total: int, iteration: int, configured_iterations: int, adaptive_max_iterations: int) -> bool:
        if self.config.target_min <= total <= self.config.target_max:
            return False
        if iteration < configured_iterations:
            return total < self.config.target_min
        if total == 0:
            return False
        return total < self._retrieval_pool_min() and iteration < adaptive_max_iterations

    def _should_narrow_after_result(self, total: int, iteration: int, configured_iterations: int, adaptive_max_iterations: int) -> bool:
        return total > self._retrieval_pool_max() and iteration < adaptive_max_iterations

    def _complete_after_unchanged_revision(self, history: list, iteration: int, query: str, total: int, hits: list, attempted_action: str) -> None:
        if total == 0:
            action = "empty"
            message = f"No records found and the {attempted_action} query was unchanged; stopped instead of repeating the same request."
        elif total < self.config.target_min:
            action = "accept_low"
            message = f"Accepted {total} records below the target minimum because the {attempted_action} query was unchanged."
        elif total > self._retrieval_pool_max():
            action = "accept_high"
            message = f"Accepted {total} records above the LLM pre-ranking safety pool because the {attempted_action} query was unchanged; the fused candidate pool will be truncated before LLM ranking."
        elif total > self.config.target_max:
            action = "accept_pool"
            message = f"Accepted {total} records for downstream pre-ranking because the {attempted_action} query was unchanged."
        else:
            action = "accept"
            message = f"Accepted {total} records because the {attempted_action} query was unchanged."
        row = {
            "iteration": iteration,
            "query": query,
            "total": total,
            "action": action,
            "next_query": None,
            "message": message,
        }
        history.append(row)
        self._emit_stage(
            "search",
            "complete",
            total=total,
            history=history,
            final_query=query,
            preview=self._preview_hits(hits),
        )

    def _candidate_limit(self) -> int:
        output_limit = max(1, min(int(self.config.target_max or 50), 50))
        if self.data_source == "wos":
            return output_limit
        return min(max(output_limit * 2, output_limit), 100)

    def _retrieval_capabilities(self) -> ProviderRetrievalCapabilities:
        if self.provider and hasattr(self.provider, "retrieval_capabilities"):
            return self.provider.retrieval_capabilities()
        if self.data_source == "wos":
            return ProviderRetrievalCapabilities(
                source="wos",
                lanes=(RetrievalLane.RELEVANCE, RetrievalLane.IMPACT, RetrievalLane.RECENT),
                max_lane_limit=100,
            )
        return ProviderRetrievalCapabilities(source=self.data_source, lanes=(RetrievalLane.RELEVANCE,))

    def _retrieve_candidates(self, question: str, query: str, primary_hits: list) -> list:
        capabilities = self._retrieval_capabilities()
        lane_limit = self._effective_lane_limit(capabilities)
        lane_results: Dict[str, list] = {}
        lane_total = max(1, len(capabilities.lanes))
        self._emit_ranking_step(
            "multi_lane_retrieval",
            "processing",
            "Multi-lane retrieval",
            current=0,
            total=lane_total,
            detail=f"Starting {', '.join(capabilities.lanes)} lanes; lane limit {lane_limit}.",
        )
        self._emit_log(
            "Lightweight multi-lane retrieval started: "
            f"source={self.data_source}; lanes={','.join(capabilities.lanes)}; lane_limit={lane_limit}; pool_max={self._retrieval_pool_max()}."
        )
        completed_lanes = 0
        for lane in capabilities.lanes:
            try:
                lane_results[lane] = self._collect_retrieval_lane(query, lane, lane_limit)
                self._emit_log(f"Retrieval lane completed: {lane}; candidates={len(lane_results[lane])}.")
            except Exception as exc:
                self._emit_log(f"Retrieval lane skipped after error: {lane}; {exc.__class__.__name__}: {exc}")
            completed_lanes += 1
            self._emit_ranking_step(
                "multi_lane_retrieval",
                "processing",
                "Multi-lane retrieval",
                current=completed_lanes,
                total=lane_total,
                detail=f"{lane} lane finished; collected {sum(len(values) for values in lane_results.values())} lane candidates.",
                lane_counts={key: len(value) for key, value in lane_results.items()},
            )
        if not lane_results and primary_hits:
            lane_results[RetrievalLane.RELEVANCE] = list(primary_hits or [])
        if not lane_results:
            self._emit_ranking_step(
                "multi_lane_retrieval",
                "complete",
                "Multi-lane retrieval",
                current=lane_total,
                total=lane_total,
                detail="No retrieval lanes returned candidates; using the primary source response.",
            )
            return list(primary_hits or [])

        ordered_docs = []
        for lane_docs in lane_results.values():
            ordered_docs.extend(lane_docs)
        unique_docs = self._dedupe_documents(ordered_docs)
        self._emit_ranking_step(
            "embedding_similarity",
            "processing",
            "Embedding similarity",
            current=0,
            total=max(1, len(unique_docs)),
            detail=f"Computing semantic similarity for {len(unique_docs)} unique candidates.",
        )
        embedding_scores = self._external_embedding_scores(question, unique_docs)
        self._emit_ranking_step(
            "embedding_similarity",
            "complete",
            "Embedding similarity",
            current=len(unique_docs),
            total=max(1, len(unique_docs)),
            detail="External embedding completed." if embedding_scores else "Using local sparse hashing similarity.",
        )
        self._emit_ranking_step(
            "rrf_fusion",
            "processing",
            "RRF fusion",
            current=0,
            total=max(1, len(unique_docs)),
            detail=f"Fusing lane rank, BM25/term coverage, and embedding signals for {len(unique_docs)} candidates.",
        )
        fused = fuse_candidates_rrf(
            question,
            lane_results,
            pool_max=self._retrieval_pool_max(),
            rrf_k=self._retrieval_rrf_k(),
            embedding_scores_by_key=self._embedding_score_map(unique_docs, embedding_scores),
        )
        self.retrieval_metadata_by_key = fused.metadata_by_key
        self._emit_ranking_step(
            "rrf_fusion",
            "complete",
            "RRF fusion",
            current=len(fused.documents),
            total=max(1, fused.total_candidates),
            detail=f"Fused {fused.total_candidates} unique candidates into a pool of {len(fused.documents)}.",
            lane_counts=fused.lane_counts,
            candidate_count=len(fused.documents),
        )
        fused_documents = self._maybe_crossref_enrich_candidates(fused.documents)
        fused_documents = self._apply_external_reranker(question, fused_documents)
        self._emit_log(
            "Lightweight multi-lane retrieval completed: "
            f"unique_candidates={fused.total_candidates}; fused_candidates={len(fused_documents)}; "
            f"lane_counts={fused.lane_counts}."
        )
        self._emit_ranking_step(
            "multi_lane_retrieval",
            "complete",
            "Multi-lane retrieval",
            current=lane_total,
            total=lane_total,
            detail=f"Retrieval completed with {len(fused_documents)} fused candidates.",
            lane_counts=fused.lane_counts,
            candidate_count=len(fused_documents),
        )
        return fused_documents

    def _maybe_crossref_enrich_candidates(self, documents: list) -> list:
        if not getattr(self.config, "retrieval_crossref_enrichment", False):
            return documents
        enriched = 0
        headers = {"Accept": "application/json", "User-Agent": "paperseek/1.0"}
        for document in documents[:100]:
            identifiers = getattr(document, "identifiers", None)
            doi = getattr(identifiers, "doi", "") if identifiers is not None else ""
            if not doi:
                continue
            try:
                response = requests.get(f"https://api.crossref.org/works/{doi}", headers=headers, timeout=20)
                if response.status_code < 200 or response.status_code >= 300:
                    continue
                message = (response.json().get("message") or {})
                cited = int(message.get("is-referenced-by-count") or 0)
                if cited and not getattr(document, "citations", None):
                    document.citations = [PaperCitation(db="Crossref", count=cited)]
                if getattr(document, "source", None) is not None and not getattr(document.source, "publish_year", None):
                    year = self._crossref_year(message)
                    if year:
                        document.source.publish_year = year
                enriched += 1
            except Exception:
                continue
        self._emit_log(f"Optional Crossref candidate enrichment completed: enriched={enriched}.")
        return documents

    @staticmethod
    def _crossref_year(message: dict) -> Optional[int]:
        for key in ("published-print", "published-online", "published", "issued"):
            parts = ((message.get(key) or {}).get("date-parts") or [])
            if parts and parts[0]:
                try:
                    return int(parts[0][0])
                except (TypeError, ValueError):
                    continue
        return None

    def _effective_lane_limit(self, capabilities: ProviderRetrievalCapabilities) -> int:
        try:
            configured = max(1, int(getattr(self.config, "retrieval_lane_limit", 1000) or 1000))
        except (TypeError, ValueError):
            configured = 1000
        return max(1, min(configured, capabilities.max_lane_limit, self._retrieval_pool_max()))

    def _retrieval_rrf_k(self) -> int:
        try:
            return max(1, int(getattr(self.config, "retrieval_rrf_k", 60) or 60))
        except (TypeError, ValueError):
            return 60

    def _collect_retrieval_lane(self, query: str, lane: str, limit: int) -> list:
        collected = []
        page = 1
        while len(collected) < limit:
            request_limit = min(1000 if self.data_source == "semanticscholar" and lane != RetrievalLane.RELEVANCE else 100, limit - len(collected))
            if self.data_source == "wos":
                request_limit = min(request_limit, limit)
            result = self._provider_search_lane(query, lane, request_limit, page=page)
            hits = list(getattr(result, "hits", []) or [])
            if not hits:
                break
            collected.extend(hits)
            metadata = getattr(result, "metadata", None)
            page_size = max(1, int(getattr(metadata, "limit", request_limit) or request_limit))
            total = int(getattr(metadata, "total", 0) or 0)
            if self.data_source == "wos":
                break
            if len(hits) < page_size:
                break
            if total and len(collected) >= total:
                break
            if self.data_source == "semanticscholar" and lane != RetrievalLane.RELEVANCE:
                break
            page += 1
        return self._dedupe_documents(collected)[:limit]

    def _external_embedding_scores(self, question: str, documents: list) -> Optional[List[float]]:
        provider = (getattr(self.config, "retrieval_embedding_provider", "local") or "local").strip().lower()
        if provider in ("", "local", "python"):
            return None
        if not documents:
            return []
        api_key = self._retrieval_api_key("embedding", provider)
        base_url = self._retrieval_base_url("embedding", provider)
        if not api_key or not base_url:
            self._emit_log("External embedding skipped: provider configured but API key or base URL is missing; using local hashing embeddings.")
            return None
        texts = [question] + [document_text(document)[:1800] for document in documents]
        for model in self._retrieval_model_candidates("embedding", "qwen3-embedding:8b", provider):
            try:
                vectors = self._embedding_vectors(base_url, api_key, model, texts, provider=provider)
            except Exception as exc:
                self._emit_log(f"External embedding failed for model={model}; trying fallback if available: {exc}")
                continue
            if len(vectors) != len(texts):
                self._emit_log(f"External embedding returned an unexpected vector count for model={model}; trying fallback if available.")
                continue
            query_vector = vectors[0]
            self._emit_log(f"External embedding completed: provider={provider}; model={model}; documents={len(documents)}.")
            return [self._dense_cosine(query_vector, vector) for vector in vectors[1:]]
        self._emit_log("External embedding failed for all configured models; using local hashing embeddings.")
        return None

    @staticmethod
    def _embedding_score_map(documents: list, scores: Optional[List[float]]) -> Dict[str, float]:
        if not scores or len(scores) != len(documents):
            return {}
        output = {}
        for document, score in zip(documents, scores):
            key = document_key(document)
            if key:
                output[key] = score
        return output

    def _post_external_api(
        self,
        url: str,
        api_key: str,
        headers_factory: Callable[[str], Dict[str, str]],
        payload: Dict[str, Any],
        *,
        timeout: int = 60,
        label: str = "External API",
    ):
        attempts = _external_api_key_attempts(api_key)
        last_error = None
        for attempt_index, key in enumerate(attempts, 1):
            try:
                response = requests.post(url, headers=headers_factory(key), json=payload, timeout=timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt_index < len(attempts):
                    self._emit_log(f"{label} request failed; retrying with another key ({attempt_index}/{len(attempts)}): {exc}")
                    continue
                raise
            if (
                response.status_code < 200 or response.status_code >= 300
            ) and attempt_index < len(attempts) and _retryable_external_status(response.status_code):
                self._emit_log(
                    f"{label} request returned HTTP {response.status_code}; "
                    f"retrying with another key ({attempt_index}/{len(attempts)})."
                )
                last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
                continue
            return response
        if last_error:
            raise last_error
        return requests.post(url, headers=headers_factory(""), json=payload, timeout=timeout)

    def _embedding_vectors(self, base_url: str, api_key: str, model: str, texts: list, provider: str = "") -> List[List[float]]:
        if (provider or "").strip().lower() == "nvidia":
            return self._nvidia_embedding_vectors(base_url, api_key, model, texts)
        vectors: List[List[float]] = []
        url = f"{base_url.rstrip('/')}/embeddings"
        batch_size = 64
        for offset in range(0, len(texts), batch_size):
            batch = texts[offset:offset + batch_size]
            response = self._post_external_api(
                url,
                api_key,
                lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                {"model": model, "input": batch, "encoding_format": "float"},
                timeout=60,
                label="External embedding",
            )
            if response.status_code < 200 or response.status_code >= 300:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
            payload = response.json()
            data = payload.get("data") or []
            data = sorted(data, key=lambda item: int(item.get("index", 0))) if all(isinstance(item, dict) for item in data) else data
            for item in data:
                embedding = item.get("embedding") if isinstance(item, dict) else None
                if not isinstance(embedding, list):
                    raise RuntimeError("embedding response item has no embedding vector")
                vectors.append([float(value) for value in embedding])
        return vectors

    def _nvidia_embedding_vectors(self, base_url: str, api_key: str, model: str, texts: list) -> List[List[float]]:
        url = f"{base_url.rstrip('/')}/embeddings"

        def request_vectors(batch: list, input_type: str) -> List[List[float]]:
            response = self._post_external_api(
                url,
                api_key,
                lambda key: {"Authorization": f"Bearer {key}", "Accept": "application/json", "Content-Type": "application/json"},
                {"model": model, "input": batch, "input_type": input_type, "encoding_format": "float"},
                timeout=60,
                label="NVIDIA embedding",
            )
            if response.status_code < 200 or response.status_code >= 300:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
            payload = response.json()
            data = payload.get("data") or []
            data = sorted(data, key=lambda item: int(item.get("index", 0))) if all(isinstance(item, dict) for item in data) else data
            vectors = []
            for item in data:
                embedding = item.get("embedding") if isinstance(item, dict) else None
                if not isinstance(embedding, list):
                    raise RuntimeError("embedding response item has no embedding vector")
                vectors.append([float(value) for value in embedding])
            return vectors

        vectors: List[List[float]] = []
        if texts:
            vectors.extend(request_vectors(texts[:1], "query"))
        batch_size = 64
        for offset in range(1, len(texts), batch_size):
            vectors.extend(request_vectors(texts[offset:offset + batch_size], "passage"))
        return vectors

    def _apply_external_reranker(self, question: str, documents: list) -> list:
        provider = (getattr(self.config, "retrieval_reranker_provider", "") or "").strip().lower()
        if provider in ("", "none", "off") or not documents:
            return documents
        self._emit_ranking_step(
            "external_reranker",
            "processing",
            "External reranker",
            current=0,
            total=max(1, min(200, len(documents))),
            detail=f"Calling {provider} reranker for the top {min(200, len(documents))} candidates.",
        )
        if provider == "modelscope":
            self._emit_log("External reranker skipped: ModelScope API-Inference does not support rerank.")
            self._emit_ranking_step(
                "external_reranker",
                "skipped",
                "External reranker",
                current=0,
                total=max(1, min(200, len(documents))),
                detail="ModelScope API-Inference does not support rerank; keeping RRF order.",
            )
            return documents
        api_key = self._retrieval_api_key("reranker", provider)
        base_url = self._retrieval_base_url("reranker", provider)
        if not api_key or not base_url:
            self._emit_log("External reranker skipped: provider configured but API key or base URL is missing.")
            self._emit_ranking_step(
                "external_reranker",
                "skipped",
                "External reranker",
                current=0,
                total=max(1, min(200, len(documents))),
                detail="Reranker API key or base URL is missing; keeping RRF order.",
            )
            return documents
        rerank_count = min(200, len(documents))
        texts = [document_text(document)[:1800] for document in documents[:rerank_count]]
        for model in self._retrieval_model_candidates("reranker", "qwen3-reranker:8b", provider):
            try:
                if provider == "nvidia":
                    endpoint = base_url.rstrip("/")
                    if not (endpoint.endswith("/reranking") or endpoint.endswith("/ranking")):
                        endpoint = f"{endpoint}/reranking"
                    response = self._post_external_api(
                        endpoint,
                        api_key,
                        lambda key: {"Authorization": f"Bearer {key}", "Accept": "application/json", "Content-Type": "application/json"},
                        {"model": model, "query": {"text": question}, "passages": [{"text": text} for text in texts]},
                        timeout=60,
                        label="External reranker",
                    )
                else:
                    response = self._post_external_api(
                        f"{base_url.rstrip('/')}/rerank",
                        api_key,
                        lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        {"model": model, "query": question, "documents": texts, "top_n": rerank_count},
                        timeout=60,
                        label="External reranker",
                    )
                if response.status_code < 200 or response.status_code >= 300:
                    raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
                payload = response.json()
                results = (payload.get("rankings") or []) if provider == "nvidia" else (payload.get("results") or payload.get("data") or [])
                ranked = []
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    index = item.get("index")
                    score = item.get("logit", item.get("relevance_score", item.get("score", 0)))
                    if isinstance(index, int) and 0 <= index < rerank_count:
                        ranked.append((float(score or 0), index))
                if not ranked:
                    raise RuntimeError("reranker response contained no indexed scores")
                ranked.sort(reverse=True)
                used = {index for _, index in ranked}
                reranked_docs = [documents[index] for _, index in ranked]
                reranked_docs.extend(documents[index] for index in range(rerank_count) if index not in used)
                reranked_docs.extend(documents[rerank_count:])
                self._emit_log(f"External reranker completed: provider={provider}; model={model}; reranked={rerank_count}.")
                self._emit_ranking_step(
                    "external_reranker",
                    "complete",
                    "External reranker",
                    current=rerank_count,
                    total=max(1, rerank_count),
                    detail=f"{provider} reranker completed with model={model}.",
                    candidate_count=len(reranked_docs),
                )
                return reranked_docs
            except Exception as exc:
                self._emit_log(f"External reranker failed for model={model}; trying fallback if available: {exc}")
        self._emit_log("External reranker failed for all configured models; keeping RRF order.")
        self._emit_ranking_step(
            "external_reranker",
            "error",
            "External reranker",
            current=0,
            total=max(1, rerank_count),
            detail="All configured reranker models failed; keeping RRF order.",
        )
        return documents

    def _retrieval_model_candidates(self, kind: str, default_model: str, provider: str = "") -> List[str]:
        raw = getattr(self.config, f"retrieval_{kind}_model", "") or default_model
        provider = (provider or "").strip().lower()
        if kind == "embedding" and provider == "modelscope":
            modelscope_models = "Qwen/Qwen3-Embedding-8B,Qwen/Qwen3-Embedding-4B"
            if raw in ("", default_model, "qwen3-embedding:8b,bge-large-zh:latest", "BAAI/bge-large-zh-v1.5"):
                raw = modelscope_models
        if kind == "embedding" and provider == "nvidia":
            if raw in ("", default_model, "qwen3-embedding:8b", "qwen3-embedding:8b,bge-large-zh:latest"):
                raw = "nvidia/nv-embedqa-e5-v5"
            elif raw == "nv-embed-v1":
                raw = "nvidia/nv-embed-v1"
        if kind == "embedding" and provider == "openrouter":
            if raw in ("", default_model, "qwen3-embedding:8b", "qwen3-embedding:8b,bge-large-zh:latest"):
                raw = "openai/text-embedding-3-small"
        if kind == "reranker" and provider == "nvidia":
            if raw in ("", default_model, "qwen3-reranker:8b", "BAAI/bge-reranker-v2-m3"):
                raw = "nv-rerank-qa-mistral-4b:1"
        if kind == "reranker" and provider == "openrouter":
            if raw in ("", default_model, "qwen3-reranker:8b", "BAAI/bge-reranker-v2-m3"):
                raw = "jinaai/jina-reranker-v2-base-multilingual"
        candidates = []
        for part in str(raw).replace(";", ",").split(","):
            value = part.strip()
            if value and value not in candidates:
                candidates.append(value)
        return candidates or [default_model]

    def _retrieval_api_key(self, kind: str, provider: str) -> str:
        attr = f"retrieval_{kind}_api_key"
        value = getattr(self.config, attr, "") or ""
        if value:
            return value
        if provider in (
            "cstcloud",
            "openai",
            "dashscope",
            "siliconflow",
            "openrouter",
            "nvidia",
            "zhipu",
            "volcengine",
            "modelscope",
            "custom",
        ):
            return getattr(self.config, "llm_api_key", "") or ""
        return ""

    def _retrieval_base_url(self, kind: str, provider: str) -> str:
        attr = f"retrieval_{kind}_base_url"
        value = getattr(self.config, attr, "") or ""
        if value:
            return value
        if kind == "reranker" and provider == "modelscope":
            return ""
        provider_urls = {
            "cstcloud": "https://uni-api.cstcloud.cn/v1",
            "openai": "https://api.openai.com/v1",
            "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "nvidia": "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking" if kind == "reranker" else "https://integrate.api.nvidia.com/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
            "modelscope": "https://api-inference.modelscope.cn/v1",
        }
        if provider in provider_urls:
            return provider_urls[provider]
        if provider == "custom":
            return getattr(self.config, "llm_base_url", "") or ""
        return ""

    @staticmethod
    def _dense_cosine(left: list, right: list) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(float(a) * float(b) for a, b in zip(left, right))
        left_norm = math.sqrt(sum(float(a) * float(a) for a in left))
        right_norm = math.sqrt(sum(float(b) * float(b) for b in right))
        if left_norm <= 0 or right_norm <= 0:
            return 0.0
        return max(0.0, min(1.0, dot / (left_norm * right_norm)))

    @staticmethod
    def _citation_seed_key(doc) -> str:
        if not doc:
            return ""
        identifiers = getattr(doc, "identifiers", None)
        for value in (
            getattr(identifiers, "openalex", "") if identifiers else "",
            getattr(identifiers, "doi", "") if identifiers else "",
            getattr(doc, "uid", ""),
            getattr(doc, "title", ""),
        ):
            normalized = str(value or "").strip().lower()
            if normalized:
                return normalized
        return ""

    def _build_citation_seed_plans(self, seed_ranked: list, candidates: list, seed_limit: int, depth: int) -> list:
        seed_limit = max(1, int(seed_limit or 1))
        depth = max(1, min(int(depth or 1), 3))
        relevance_quota = max(1, seed_limit // 2)
        impact_quota = max(1, seed_limit // 4) if seed_limit > 1 else 0
        recent_quota = max(0, seed_limit - relevance_quota - impact_quota)
        plans: List[CitationSeedPlan] = []
        index_by_key: Dict[str, CitationSeedPlan] = {}

        def add_plan(doc, role: str, directions: Tuple[str, ...]):
            if not doc or len(plans) >= seed_limit and self._citation_seed_key(doc) not in index_by_key:
                return
            key = self._citation_seed_key(doc)
            if not key:
                return
            existing = index_by_key.get(key)
            if existing:
                merged = []
                for direction in tuple(existing.directions) + tuple(directions):
                    if direction not in merged:
                        merged.append(direction)
                existing.directions = tuple(merged)
                if role not in existing.role.split("+"):
                    existing.role = f"{existing.role}+{role}"
                existing.depth = max(existing.depth, depth)
                return
            if len(plans) >= seed_limit:
                return
            plan = CitationSeedPlan(record=doc, role=role, directions=directions, depth=depth)
            index_by_key[key] = plan
            plans.append(plan)

        relevance_docs = [
            entry.get("document")
            for entry in seed_ranked
            if entry.get("document") is not None and float(entry.get("score") or 0) >= 7
        ]
        if len(relevance_docs) < relevance_quota:
            for entry in seed_ranked:
                doc = entry.get("document")
                if doc is not None and doc not in relevance_docs:
                    relevance_docs.append(doc)
                if len(relevance_docs) >= relevance_quota:
                    break
        for doc in relevance_docs[:relevance_quota]:
            add_plan(doc, "relevance", ("backward", "forward"))

        impact_docs = sorted(
            candidates or [],
            key=lambda doc: (_citation_count(doc), getattr(getattr(doc, "source", None), "publish_year", 0) or 0),
            reverse=True,
        )
        for doc in impact_docs[:impact_quota]:
            add_plan(doc, "impact", ("backward",))

        recent_docs = sorted(
            candidates or [],
            key=lambda doc: (getattr(getattr(doc, "source", None), "publish_year", 0) or 0, _citation_count(doc)),
            reverse=True,
        )
        for doc in recent_docs[:recent_quota]:
            add_plan(doc, "recent", ("forward",))

        if len(plans) < seed_limit:
            for entry in seed_ranked:
                add_plan(entry.get("document"), "relevance", ("backward", "forward"))
                if len(plans) >= seed_limit:
                    break
        return plans

    @staticmethod
    def _citation_seed_plan_counts(seed_plans: list) -> dict:
        counts: Dict[str, int] = {"relevance": 0, "impact": 0, "recent": 0}
        for plan in seed_plans or []:
            for role in str(getattr(plan, "role", "") or "").split("+"):
                if role in counts:
                    counts[role] += 1
        return counts

    def _prepare_candidates(self, question: str, hits: list) -> list:
        candidates = list(hits or [])
        self.citation_map = self._empty_citation_map(
            enabled=getattr(self.config, "expand_citations", True),
            initial_candidates=len(candidates),
            candidate_pool=len(candidates),
        )
        if not candidates:
            return candidates
        if not getattr(self.config, "expand_citations", True):
            return candidates
        if self.data_source != "openalex" or not isinstance(self.provider, OpenAlexProvider):
            self._emit_log("Citation expansion skipped: this data source does not support OpenAlex citation traversal yet.")
            self.citation_map.update({"supported": False, "status": "unsupported"})
            return candidates

        self._emit_log("Citation expansion started: ranking seed papers before traversing references and citing works.")
        self._emit_ranking_step(
            "citation_seed_ranking",
            "processing",
            "Citation seed ranking",
            current=0,
            total=max(1, len(candidates)),
            detail="Ranking initial candidates to choose citation expansion seeds.",
        )
        seed_ranked = self._rank_results(question, candidates, step_id="citation_seed_ranking", step_title="Citation seed ranking")
        self._emit_ranking_step(
            "citation_seed_ranking",
            "complete",
            "Citation seed ranking",
            current=len(candidates),
            total=max(1, len(candidates)),
            detail="Seed ranking completed.",
        )
        seed_limit = max(1, int(getattr(self.config, "citation_seed_count", 30) or 30))
        citation_depth = max(1, min(int(getattr(self.config, "citation_depth", 2) or 2), 3))
        seed_plans = self._build_citation_seed_plans(seed_ranked, candidates, seed_limit, citation_depth)
        seeds = [plan.record for plan in seed_plans]
        if not seed_plans:
            self._emit_log("Citation expansion skipped: no seed papers available.")
            self.citation_map.update({"status": "no_seeds"})
            self._emit_ranking_step(
                "citation_expansion",
                "skipped",
                "Citation expansion",
                current=0,
                total=max(1, seed_limit),
                detail="No seed papers were available for citation traversal.",
            )
            return candidates

        self._emit_ranking_step(
            "citation_expansion",
            "processing",
            "Citation expansion",
            current=0,
            total=max(1, len(seed_plans)),
            detail=f"Traversing citation neighborhoods for {len(seed_plans)} seed papers across relevance, impact, and recency plans.",
            seed_count=len(seeds),
            citation_depth=citation_depth,
        )
        try:
            citation_data = self.provider.citation_neighbors_with_graph(
                seeds,
                per_seed=getattr(self.config, "citation_per_seed", 4),
                max_records=getattr(self.config, "citation_max_records", 160),
                field_ids=openalex_field_ids(self.discipline_fields),
                seed_plans=seed_plans,
                depth=citation_depth,
            )
        except ProviderError as exc:
            self._emit_log(f"Citation expansion skipped after OpenAlex error: {exc}")
            self.citation_map.update({"status": "error", "error": str(exc)})
            self._emit_ranking_step(
                "citation_expansion",
                "error",
                "Citation expansion",
                current=0,
                total=max(1, len(seeds)),
                detail=f"Citation traversal failed: {exc}",
                seed_count=len(seeds),
            )
            return candidates

        related = citation_data.get("records", [])
        before = len(candidates)
        candidates = self._dedupe_documents(candidates + related)
        added = len(candidates) - before
        self.citation_map.update({
            "enabled": True,
            "supported": True,
            "status": "complete",
            "initial_candidates": len(hits or []),
            "seed_count": len(seeds),
            "seed_plan_counts": self._citation_seed_plan_counts(seed_plans),
            "citation_depth": citation_depth,
            "added_candidates": added,
            "candidate_pool": len(candidates),
            "nodes": citation_data.get("nodes", []),
            "edges": citation_data.get("edges", []),
        })
        self._emit_log(f"Citation expansion completed: added {added} citation-neighbor candidates; candidate pool={len(candidates)}.")
        self._emit_ranking_step(
            "citation_expansion",
            "complete",
            "Citation expansion",
            current=len(seeds),
            total=max(1, len(seeds)),
            detail=f"Added {added} citation-neighbor candidates; candidate pool={len(candidates)}.",
            seed_count=len(seeds),
            candidate_count=len(candidates),
            added_candidates=added,
            citation_depth=citation_depth,
        )
        return candidates

    def _empty_citation_map(self, enabled: bool = True, initial_candidates: int = 0, candidate_pool: int = 0) -> dict:
        return {
            "enabled": bool(enabled),
            "supported": self.data_source == "openalex",
            "status": "waiting",
            "initial_candidates": initial_candidates,
            "seed_count": 0,
            "added_candidates": 0,
            "candidate_pool": candidate_pool,
            "nodes": [],
            "edges": [],
        }

    def _finalize_citation_map(self, ranked: list) -> None:
        if not self.citation_map:
            return
        nodes = {node.get("id"): node for node in self.citation_map.get("nodes", []) if node.get("id")}
        for index, entry in enumerate(ranked or [], 1):
            doc = entry.get("document")
            if not doc:
                continue
            node_id = getattr(doc, "uid", "") or getattr(getattr(doc, "identifiers", None), "openalex", "") or getattr(doc, "title", "")
            if not node_id:
                continue
            source = getattr(doc, "source", None)
            citations = _citation_count(doc)
            node = nodes.get(node_id)
            if not node:
                node = {
                    "id": node_id,
                    "title": getattr(doc, "title", "") or "(no title)",
                    "year": getattr(source, "publish_year", None) if source else None,
                    "source": getattr(source, "source_title", "") if source else "",
                    "citations": citations,
                    "roles": [],
                    "seed_uids": [],
                }
                nodes[node_id] = node
            if "result" not in node["roles"]:
                node["roles"].append("result")
            node["rank"] = index
            node["score"] = entry.get("score", 0)
            node["reasoning"] = entry.get("reasoning", "")
        self.citation_map["nodes"] = list(nodes.values())

    @staticmethod
    def _dedupe_documents(documents: list) -> list:
        deduped = []
        seen = set()
        for doc in documents or []:
            identifiers = getattr(doc, "identifiers", None)
            doi = (getattr(identifiers, "doi", "") if identifiers else "") or ""
            key = (doi or getattr(doc, "uid", "") or getattr(doc, "title", "")).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(doc)
        return deduped

    def _emit(self, event_type: str, **payload: Any) -> None:
        if self.event_handler:
            self.event_handler({"type": event_type, **payload})

    def _emit_log(self, message: str, **payload: Any) -> None:
        self._emit("log", message=message, **payload)

    def _emit_stage(self, stage: str, status: str, **data: Any) -> None:
        self._emit("stage", stage=stage, status=status, data=data)

    def _emit_ranking_step(
        self,
        step_id: str,
        status: str,
        title: str,
        current: int = 0,
        total: int = 0,
        detail: str = "",
        **data: Any,
    ) -> None:
        normalized_status = (status or "processing").lower()
        safe_total = max(0, int(total or 0))
        safe_current = max(0, min(int(current or 0), safe_total or int(current or 0)))
        step = {
            "id": step_id,
            "title": title,
            "status": normalized_status,
            "current": safe_current,
            "total": safe_total,
            "detail": detail,
        }
        for key in ("candidate_count", "lane_counts", "seed_count", "added_candidates", "concurrency", "batch_size"):
            if key in data and data[key] is not None:
                step[key] = data[key]
        self.ranking_steps[step_id] = step
        payload = dict(self.ranking_context)
        payload.update(data)
        payload["ranking_steps"] = list(self.ranking_steps.values())
        if "candidate_count" not in payload and "candidate_count" in step:
            payload["candidate_count"] = step["candidate_count"]
        self._emit_stage("ranking", "processing", **payload)

    def _source_label(self) -> str:
        labels = {
            "wos": "WoS Starter",
            "openalex": "OpenAlex",
            "crossref": "Crossref",
            "arxiv": "arXiv",
            "semanticscholar": "Semantic Scholar",
            "pubmed": "PubMed",
            "googlescholar": "Google Scholar",
            "paperhub": "Computer science top conferences",
        }
        return labels.get(self.data_source, self.data_source)

    def _source_request_label(self, query: str) -> str:
        discipline_note = discipline_source_note(self.discipline_fields, self.data_source)
        suffix = f" ({discipline_note})" if discipline_note else ""
        if self.data_source == "wos":
            return f"GET /documents db={self.config.wos_db} q={query}{suffix}"
        if self.data_source == "openalex":
            return f"GET /works search={query}{suffix}"
        if self.data_source == "crossref":
            return f"GET /works query.bibliographic={query}{suffix}"
        if self.data_source == "arxiv":
            return f"GET /api/query search_query={query}{suffix}"
        if self.data_source == "semanticscholar":
            return f"GET /graph/v1/paper/search query={query}{suffix}"
        if self.data_source == "pubmed":
            return f"GET /entrez/eutils/esearch.fcgi term={query}{suffix}"
        if self.data_source == "googlescholar":
            return f"POST /scholar q={query}{suffix}"
        if self.data_source == "paperhub":
            return f"GET paper-hub shards query={query}{suffix}"
        return f"{query}{suffix}"

    def _source_response_log(self, result) -> str:
        total = result.metadata.total if result.metadata else 0
        count = len(result.hits or [])
        if self.provider:
            info = getattr(self.provider, "last_response_info", {}) or {}
            method = info.get("method", "GET")
            url = str(info.get("url", "")).split("?")[0] or self._source_label()
            status = info.get("status", "unknown")
            elapsed = info.get("elapsed_ms")
            elapsed_text = f" in {elapsed}ms" if elapsed is not None else ""
            attempts = info.get("attempts")
            attempts_text = f"; attempts={attempts}" if attempts else ""
            return f"{self._source_label()} {method} {url} -> HTTP {status} OK{elapsed_text}{attempts_text}; total={total}; returned={count}."
        return f"WoS Starter GET /documents completed; total={total}; returned={count}."

    def _llm_request_log(self, purpose: str) -> None:
        base_url = getattr(self.llm, "base_url", "")
        model = self._display_llm_model(getattr(self.llm, "model", ""))
        provider = getattr(self.config, "llm_provider", "llm")
        api_type = getattr(self.config, "llm_api_type", "")
        self._emit_log(f"LLM request started: provider={provider} api_type={api_type} model={model} purpose={purpose} endpoint={base_url}.")

    def _llm_response_log(self, purpose: str) -> None:
        info = getattr(self.llm, "last_response_info", {}) or {}
        method = info.get("method", "POST")
        url = str(info.get("url", "")).split("?")[0] or "LLM endpoint"
        status = info.get("status", "completed")
        elapsed = info.get("elapsed_ms")
        elapsed_text = f" in {elapsed}ms" if elapsed is not None else ""
        status_text = f"HTTP {status} OK" if isinstance(status, int) and status < 400 else str(status)
        self._emit_log(f"LLM {method} {url} -> {status_text}{elapsed_text}; purpose={purpose}.")
        route_label = info.get("fallback_route")
        if route_label:
            self._emit_log(f"LLM route used: {route_label}.")
        quota = info.get("quota") or {}
        quota_text = format_modelscope_quota(quota)
        if quota_text:
            self._emit(
                "quota",
                provider=getattr(self.config, "llm_provider", ""),
                model=getattr(self.llm, "model", ""),
                purpose=purpose,
                quota=quota,
            )
            self._emit_log(f"ModelScope quota updated: {quota_text}.")

    @staticmethod
    def _display_llm_model(model: str) -> str:
        return {
            "kimi-for-coding": "kimi-k2.7-code",
            "z-ai/glm-5.2": "glm-5.2",
            "minimaxai/minimax-m3": "minimax-m3",
            "moonshotai/kimi-k2.6": "kimi-k2.6",
            "nvidia/nemotron-3-ultra-550b-a55b": "nemotron-3-ultra-550b-a55b",
        }.get(model, model)

    def _preview_hits(self, hits: list, limit: int = 5) -> list:
        preview = []
        for doc in (hits or [])[:limit]:
            source = getattr(doc, "source", None)
            preview.append({
                "uid": getattr(doc, "uid", ""),
                "title": getattr(doc, "title", "") or "(no title)",
                "source": getattr(source, "source_title", "") if source else "",
                "year": getattr(source, "publish_year", None) if source else None,
                "provider": getattr(doc, "provider", self.data_source),
            })
        return preview

    def _analyze_intent(self, question: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_SEARCH_INTENT_ANALYSIS},
            {"role": "user", "content": f"Research question: {question}\n\nOutput ONLY the compact JSON intent object."},
        ]
        self._emit_log("Search intent analysis started.")
        self._llm_request_log("intent_analysis")
        try:
            raw = self.llm.chat(messages, temperature=0.2)
            self._llm_response_log("intent_analysis")
        except Exception as exc:
            self._emit_log(f"Search intent analysis skipped after LLM error: {exc}")
            return f"Intent analysis unavailable after LLM error. Original question: {question}"
        intent = _extract_intent_summary(raw)
        if intent:
            self._emit_log("Search intent analysis completed.")
        else:
            self._emit_log("Search intent analysis returned no usable intent; continuing without intent context.")
            intent = f"Intent analysis returned no usable structured result. Original question: {question}"
        return intent

    def _intent_context(self) -> str:
        if not self.search_intent:
            return ""
        return (
            "\nInterpreted search intent:\n"
            f"{self.search_intent}\n"
            "Use this intent as the invariant goal when generating or revising the query. "
            "Preserve the core concepts and avoid the listed boundaries.\n"
        )

    def _result_feedback(self, query: str, hits: list, total: Optional[int], adjustment: str, limit: int = 5) -> str:
        total_text = "unknown" if total is None else str(total)
        lines = [
            "\nPrevious source feedback:",
            f"- Current query: {query}",
            f"- Returned total records: {total_text}",
            f"- Adjustment needed: {adjustment}",
        ]
        preview = self._preview_hits(hits, limit=limit)
        if preview:
            lines.append(
                "- Top returned candidate titles to compare against the intent "
                "(source relevance order when available):"
            )
            for index, item in enumerate(preview, 1):
                title = re.sub(r"\s+", " ", item.get("title") or "(no title)").strip()
                source = item.get("source") or item.get("provider") or ""
                year = item.get("year")
                meta = ", ".join(str(value) for value in (source, year) if value)
                suffix = f" ({meta})" if meta else ""
                lines.append(f"  {index}. {title[:220]}{suffix}")
        else:
            lines.append("- Top returned candidate titles: none returned.")
        lines.append(
            "Before revising the query, compare these titles with the interpreted search intent. "
            "Decide whether the returned set is on-intent, off-intent, or missing a core facet. "
            "If titles are off-intent, remove or replace the drift-causing terms rather than "
            "mechanically adding more keywords. If titles are on-intent but the count is still "
            "wrong, adjust specificity or recall while preserving the invariant intent. Put the "
            "adjustment direction, title-based diagnostic, and reason in the JSON rationale field. "
            "Put only the revised source query in the JSON query field."
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _query_temperature() -> float:
        return 0.0

    @staticmethod
    def _strict_query_output_instruction(output_label: str) -> str:
        return (
            "\nStructured output contract:\n"
            "- Return exactly one valid JSON object and no text outside JSON.\n"
            "- Use this schema: {\"query\":\"...\", \"rationale\":\"...\"}.\n"
            f"- The query field must contain exactly one complete {output_label}; it is the only value PaperSeek will send to the source API.\n"
            "- The rationale field may briefly explain the adjustment, direction, or title-intent diagnostic for audit.\n"
            "- Do not put the rationale, labels, markdown, bullets, or comments inside the query field.\n"
            "- If you compare returned titles with the intent, put the on-intent/off-intent conclusion in rationale and keep query clean.\n"
            "- If you cannot improve the query, repeat the current valid query in query and explain why in rationale.\n"
        )

    def _generate_query(self, question: str) -> str:
        if self.data_source == "openalex":
            return self._generate_openalex_query(question)
        if self.data_source == "crossref":
            return self._generate_crossref_query(question)
        if self.data_source == "arxiv":
            return self._generate_source_query(
                question,
                SYSTEM_ARXIV_QUERY_GENERATION,
                "arxiv_query_generation",
                "arXiv search_query string",
            )
        if self.data_source == "semanticscholar":
            return self._generate_source_query(
                question,
                SYSTEM_SEMANTIC_SCHOLAR_QUERY_GENERATION,
                "semanticscholar_query_generation",
                "Semantic Scholar query string",
            )
        if self.data_source == "pubmed":
            return self._generate_source_query(
                question,
                SYSTEM_PUBMED_QUERY_GENERATION,
                "pubmed_query_generation",
                "PubMed ESearch term string",
            )
        if self.data_source == "googlescholar":
            return self._generate_source_query(
                question,
                SYSTEM_GOOGLE_SCHOLAR_QUERY_GENERATION,
                "googlescholar_query_generation",
                "Google Scholar q string",
            )
        if self.data_source == "paperhub":
            return self._generate_source_query(
                question,
                SYSTEM_PAPERHUB_QUERY_GENERATION,
                "paperhub_query_generation",
                "PaperHub search query string",
            )
        if self.provider:
            return self._generate_generic_source_query(question)

        context = self._intent_context()
        field_hint = ""
        if self.config.search_field:
            field_hint = f"\nDiscipline/field constraint: {self.config.search_field}\nIncorporate this into the query via relevant SO= journals or TS= field-specific keywords."
        field_hint += self._discipline_context()

        messages = [
            {"role": "system", "content": SYSTEM_QUERY_GENERATION},
            {"role": "user", "content": f"Research question: {question}{context}{field_hint}{self._strict_query_output_instruction('WoS query string')}"},
        ]
        self._emit_stage("query", "processing", source=self.data_source)
        self._llm_request_log("wos_query_generation")
        raw = self.llm.chat(messages, temperature=self._query_temperature())
        self._llm_response_log("wos_query_generation")
        query = self._finalize_source_query(
            question,
            raw,
            system_prompt=SYSTEM_QUERY_GENERATION,
            log_name="wos_query_generation",
            output_label="WoS query string",
            operation="generated query",
        )
        query = _make_starter_safe_query(query)
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _broaden_query(self, question: str, current_query: str, feedback: str = "") -> str:
        if self.data_source == "openalex":
            messages = [
                {"role": "system", "content": SYSTEM_OPENALEX_QUERY_BROADEN},
                {"role": "user", "content": (
                    f"Question: {question}\n"
                    f"{self._intent_context()}"
                    f"{self._discipline_context()}\n"
                    f"{feedback}"
                    f"Current query returned too few results: {current_query}\n"
                    f"{self._strict_query_output_instruction('broadened OpenAlex search query string')}"
                )},
            ]
            self._llm_request_log("openalex_query_broaden")
            raw = self.llm.chat(messages, temperature=self._query_temperature())
            self._llm_response_log("openalex_query_broaden")
            query = self._finalize_source_query(
                question,
                raw,
                current_query=current_query,
                feedback=feedback,
                system_prompt=SYSTEM_OPENALEX_QUERY_BROADEN,
                log_name="openalex_query_broaden",
                output_label="broadened OpenAlex search query string",
                operation="broadened query",
            )
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query
        if self.data_source == "crossref":
            messages = [
                {"role": "system", "content": SYSTEM_CROSSREF_QUERY_BROADEN},
                {"role": "user", "content": (
                    f"Question: {question}\n"
                    f"{self._intent_context()}"
                    f"{self._discipline_context()}\n"
                    f"{feedback}"
                    f"Current query returned too few results: {current_query}\n"
                    f"{self._strict_query_output_instruction('broadened Crossref bibliographic query string')}"
                )},
            ]
            self._llm_request_log("crossref_query_broaden")
            raw = self.llm.chat(messages, temperature=self._query_temperature())
            self._llm_response_log("crossref_query_broaden")
            query = self._finalize_source_query(
                question,
                raw,
                current_query=current_query,
                feedback=feedback,
                system_prompt=SYSTEM_CROSSREF_QUERY_BROADEN,
                log_name="crossref_query_broaden",
                output_label="broadened Crossref bibliographic query string",
                operation="broadened query",
            )
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query
        if self.data_source == "arxiv":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_ARXIV_QUERY_BROADEN,
                "arxiv_query_broaden",
                "too few or zero records",
                "broadened arXiv search_query string",
                feedback,
            )
        if self.data_source == "semanticscholar":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_SEMANTIC_SCHOLAR_QUERY_BROADEN,
                "semanticscholar_query_broaden",
                "too few or zero records",
                "broadened Semantic Scholar query string",
                feedback,
            )
        if self.data_source == "pubmed":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_PUBMED_QUERY_BROADEN,
                "pubmed_query_broaden",
                "too few or zero records",
                "broadened PubMed ESearch term string",
                feedback,
            )
        if self.data_source == "googlescholar":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_GOOGLE_SCHOLAR_QUERY_BROADEN,
                "googlescholar_query_broaden",
                "too few or zero records",
                "broadened Google Scholar q string",
                feedback,
            )
        if self.data_source == "paperhub":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_PAPERHUB_QUERY_BROADEN,
                "paperhub_query_broaden",
                "too few or zero records",
                "broadened PaperHub search query string",
                feedback,
            )
        if self.provider:
            messages = [
                {"role": "system", "content": SYSTEM_GENERIC_SOURCE_QUERY_BROADEN},
                {"role": "user", "content": (
                    f"Source: {self._source_label()}\n"
                    f"Question: {question}\n"
                    f"{self._intent_context()}"
                    f"{self._discipline_context()}\n"
                    f"{feedback}"
                    f"Current query returned too few results: {current_query}\n"
                    f"{self._strict_query_output_instruction('broadened plain search query string')}"
                )},
            ]
            self._llm_request_log(f"{self.data_source}_query_broaden")
            raw = self.llm.chat(messages, temperature=self._query_temperature())
            self._llm_response_log(f"{self.data_source}_query_broaden")
            query = self._finalize_source_query(
                question,
                raw,
                current_query=current_query,
                feedback=feedback,
                system_prompt=SYSTEM_GENERIC_SOURCE_QUERY_BROADEN,
                log_name=f"{self.data_source}_query_broaden",
                output_label="broadened plain search query string",
                operation="broadened query",
            )
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query

        messages = [
            {"role": "system", "content": SYSTEM_QUERY_BROADEN},
            {"role": "user", "content": (
                f"Question: {question}\n"
                f"{self._intent_context()}"
                f"{self._discipline_context()}\n"
                f"{feedback}"
                f"Current query returned too few or zero results: {current_query}\n"
                f"{self._strict_query_output_instruction('broadened WoS query string')}"
            )},
        ]
        self._llm_request_log("wos_query_broaden")
        raw = self.llm.chat(messages, temperature=self._query_temperature())
        self._llm_response_log("wos_query_broaden")
        query = self._finalize_source_query(
            question,
            raw,
            current_query=current_query,
            feedback=feedback,
            system_prompt=SYSTEM_QUERY_BROADEN,
            log_name="wos_query_broaden",
            output_label="broadened WoS query string",
            operation="broadened query",
        )
        query = _make_starter_safe_query(query)
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _narrow_query(self, question: str, current_query: str, feedback: str = "") -> str:
        if self.data_source == "openalex":
            messages = [
                {"role": "system", "content": SYSTEM_OPENALEX_QUERY_NARROW},
                {"role": "user", "content": (
                    f"Question: {question}\n"
                    f"{self._intent_context()}"
                    f"{self._discipline_context()}\n"
                    f"{feedback}"
                    f"Current query returned too many results: {current_query}\n"
                    f"{self._strict_query_output_instruction('narrowed OpenAlex search query string')}"
                )},
            ]
            self._llm_request_log("openalex_query_narrow")
            raw = self.llm.chat(messages, temperature=self._query_temperature())
            self._llm_response_log("openalex_query_narrow")
            query = self._finalize_source_query(
                question,
                raw,
                current_query=current_query,
                feedback=feedback,
                system_prompt=SYSTEM_OPENALEX_QUERY_NARROW,
                log_name="openalex_query_narrow",
                output_label="narrowed OpenAlex search query string",
                operation="narrowed query",
            )
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query
        if self.data_source == "crossref":
            messages = [
                {"role": "system", "content": SYSTEM_CROSSREF_QUERY_NARROW},
                {"role": "user", "content": (
                    f"Question: {question}\n"
                    f"{self._intent_context()}"
                    f"{self._discipline_context()}\n"
                    f"{feedback}"
                    f"Current query returned too many results: {current_query}\n"
                    f"{self._strict_query_output_instruction('narrowed Crossref bibliographic query string')}"
                )},
            ]
            self._llm_request_log("crossref_query_narrow")
            raw = self.llm.chat(messages, temperature=self._query_temperature())
            self._llm_response_log("crossref_query_narrow")
            query = self._finalize_source_query(
                question,
                raw,
                current_query=current_query,
                feedback=feedback,
                system_prompt=SYSTEM_CROSSREF_QUERY_NARROW,
                log_name="crossref_query_narrow",
                output_label="narrowed Crossref bibliographic query string",
                operation="narrowed query",
            )
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query
        if self.data_source == "arxiv":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_ARXIV_QUERY_NARROW,
                "arxiv_query_narrow",
                "too many records",
                "narrowed arXiv search_query string",
                feedback,
            )
        if self.data_source == "semanticscholar":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_SEMANTIC_SCHOLAR_QUERY_NARROW,
                "semanticscholar_query_narrow",
                "too many records",
                "narrowed Semantic Scholar query string",
                feedback,
            )
        if self.data_source == "pubmed":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_PUBMED_QUERY_NARROW,
                "pubmed_query_narrow",
                "too many records",
                "narrowed PubMed ESearch term string",
                feedback,
            )
        if self.data_source == "googlescholar":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_GOOGLE_SCHOLAR_QUERY_NARROW,
                "googlescholar_query_narrow",
                "too many records",
                "narrowed Google Scholar q string",
                feedback,
            )
        if self.data_source == "paperhub":
            return self._revise_source_query(
                question,
                current_query,
                SYSTEM_PAPERHUB_QUERY_NARROW,
                "paperhub_query_narrow",
                "too many records",
                "narrowed PaperHub search query string",
                feedback,
            )
        if self.provider:
            messages = [
                {"role": "system", "content": SYSTEM_GENERIC_SOURCE_QUERY_NARROW},
                {"role": "user", "content": (
                    f"Source: {self._source_label()}\n"
                    f"Question: {question}\n"
                    f"{self._intent_context()}"
                    f"{self._discipline_context()}\n"
                    f"{feedback}"
                    f"Current query returned too many results: {current_query}\n"
                    f"{self._strict_query_output_instruction('narrowed plain search query string')}"
                )},
            ]
            self._llm_request_log(f"{self.data_source}_query_narrow")
            raw = self.llm.chat(messages, temperature=self._query_temperature())
            self._llm_response_log(f"{self.data_source}_query_narrow")
            query = self._finalize_source_query(
                question,
                raw,
                current_query=current_query,
                feedback=feedback,
                system_prompt=SYSTEM_GENERIC_SOURCE_QUERY_NARROW,
                log_name=f"{self.data_source}_query_narrow",
                output_label="narrowed plain search query string",
                operation="narrowed query",
            )
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query

        field_hint = ""
        if self.config.search_field:
            field_hint = f" Consider adding SO= for key journals in {self.config.search_field}."
        field_hint += self._discipline_context()

        messages = [
            {"role": "system", "content": SYSTEM_QUERY_NARROW},
            {"role": "user", "content": (
                f"Question: {question}\n"
                f"{self._intent_context()}"
                f"Current query returned too many results: {current_query}\n"
                f"{feedback}"
                f"{field_hint}\n"
                f"{self._strict_query_output_instruction('narrowed WoS query string')}"
            )},
        ]
        self._llm_request_log("wos_query_narrow")
        raw = self.llm.chat(messages, temperature=self._query_temperature())
        self._llm_response_log("wos_query_narrow")
        query = self._finalize_source_query(
            question,
            raw,
            current_query=current_query,
            feedback=feedback,
            system_prompt=SYSTEM_QUERY_NARROW,
            log_name="wos_query_narrow",
            output_label="narrowed WoS query string",
            operation="narrowed query",
        )
        query = _make_starter_safe_query(query)
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _generate_openalex_query(self, question: str) -> str:
        context = self._intent_context()
        field_hint = ""
        if self.config.search_field:
            field_hint = f"\nDiscipline/field constraint: {self.config.search_field}\nTranslate this into standard English field or topic terms if useful."
        field_hint += self._discipline_context()

        messages = [
            {"role": "system", "content": SYSTEM_OPENALEX_QUERY_GENERATION},
            {"role": "user", "content": f"Research question: {question}{context}{field_hint}{self._strict_query_output_instruction('OpenAlex search query string')}"},
        ]
        self._emit_stage("query", "processing", source=self.data_source)
        self._llm_request_log("openalex_query_generation")
        raw = self.llm.chat(messages, temperature=self._query_temperature())
        self._llm_response_log("openalex_query_generation")
        query = self._finalize_source_query(
            question,
            raw,
            system_prompt=SYSTEM_OPENALEX_QUERY_GENERATION,
            log_name="openalex_query_generation",
            output_label="OpenAlex search query string",
            operation="generated query",
        )
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _generate_generic_source_query(self, question: str) -> str:
        context = self._intent_context()
        field_hint = ""
        if self.config.search_field:
            field_hint = f"\nDiscipline/field constraint: {self.config.search_field}\nTranslate this into standard English academic terms if useful."
        field_hint += self._discipline_context()

        messages = [
            {"role": "system", "content": SYSTEM_GENERIC_SOURCE_QUERY_GENERATION},
            {"role": "user", "content": (
                f"Source: {self._source_label()}\n"
                f"Research question: {question}{context}{field_hint}\n\n"
                f"{self._strict_query_output_instruction('source search query string')}"
            )},
        ]
        self._emit_stage("query", "processing", source=self.data_source)
        self._llm_request_log(f"{self.data_source}_query_generation")
        raw = self.llm.chat(messages, temperature=self._query_temperature())
        self._llm_response_log(f"{self.data_source}_query_generation")
        query = self._finalize_source_query(
            question,
            raw,
            system_prompt=SYSTEM_GENERIC_SOURCE_QUERY_GENERATION,
            log_name=f"{self.data_source}_query_generation",
            output_label="source search query string",
            operation="generated query",
        )
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _generate_source_query(self, question: str, system_prompt: str, log_name: str, output_label: str) -> str:
        context = self._intent_context()
        field_context = self._discipline_context()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Research question: {question}{context}{field_context}{self._strict_query_output_instruction(output_label)}"},
        ]
        self._emit_stage("query", "processing", source=self.data_source)
        self._llm_request_log(log_name)
        raw = self.llm.chat(messages, temperature=self._query_temperature())
        self._llm_response_log(log_name)
        query = self._finalize_source_query(
            question,
            raw,
            system_prompt=system_prompt,
            log_name=log_name,
            output_label=output_label,
            operation="generated query",
        )
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _revise_source_query(
        self,
        question: str,
        current_query: str,
        system_prompt: str,
        log_name: str,
        result_description: str,
        output_label: str,
        feedback: str = "",
    ) -> str:
        context = self._intent_context()
        field_context = self._discipline_context()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"Source: {self._source_label()}\n"
                f"Question: {question}\n"
                f"{context}"
                f"{field_context}\n"
                f"{feedback}"
                f"Current query returned {result_description}: {current_query}\n"
                f"{self._strict_query_output_instruction(output_label)}"
            )},
        ]
        self._llm_request_log(log_name)
        raw = self.llm.chat(messages, temperature=self._query_temperature())
        self._llm_response_log(log_name)
        query = self._finalize_source_query(
            question,
            raw,
            current_query=current_query,
            feedback=feedback,
            system_prompt=system_prompt,
            log_name=log_name,
            output_label=output_label,
            operation="revised query",
        )
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _generate_crossref_query(self, question: str) -> str:
        context = self._intent_context()
        field_hint = ""
        if self.config.search_field:
            field_hint = f"\nDiscipline/field constraint: {self.config.search_field}\nTranslate this into standard English bibliographic terms if useful."
        field_hint += self._discipline_context()

        messages = [
            {"role": "system", "content": SYSTEM_CROSSREF_QUERY_GENERATION},
            {"role": "user", "content": f"Research question: {question}{context}{field_hint}{self._strict_query_output_instruction('Crossref bibliographic query string')}"},
        ]
        self._emit_stage("query", "processing", source=self.data_source)
        self._llm_request_log("crossref_query_generation")
        raw = self.llm.chat(messages, temperature=self._query_temperature())
        self._llm_response_log("crossref_query_generation")
        query = self._finalize_source_query(
            question,
            raw,
            system_prompt=SYSTEM_CROSSREF_QUERY_GENERATION,
            log_name="crossref_query_generation",
            output_label="Crossref bibliographic query string",
            operation="generated query",
        )
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _rank_results(
        self,
        question: str,
        documents: list,
        ranking_context: Optional[Dict[str, Any]] = None,
        step_id: str = "llm_reranking",
        step_title: str = "LLM reranking",
    ) -> list:
        if not documents:
            return []

        batch_size = self._ranking_batch_size(len(documents))
        batches = [documents[index:index + batch_size] for index in range(0, len(documents), batch_size)]
        ranking_context = ranking_context or {}
        if ranking_context:
            self.ranking_context = dict(ranking_context)
        if len(batches) <= 1:
            self._emit_ranking_step(
                step_id,
                "processing",
                step_title,
                current=0,
                total=1,
                detail=f"Scoring {len(documents)} candidates in one LLM batch.",
            )
            try:
                self._llm_request_log("result_ranking")
                scores = self._score_ranking_batch(question, documents, self._new_ranking_llm_client())
                self._llm_response_log("result_ranking")
            except Exception as exc:
                self._emit_log(f"Result ranking batch failed; keeping local pre-ranking order: {exc}")
                self._emit_ranking_step(
                    step_id,
                    "skipped",
                    step_title,
                    current=0,
                    total=1,
                    detail="LLM ranking failed or timed out; keeping the local pre-ranking order.",
                    candidate_count=len(documents),
                )
                return self._rank_from_scores(documents, [])
            self._emit_ranking_step(
                step_id,
                "complete",
                step_title,
                current=1,
                total=1,
                detail=f"Scored {len(documents)} candidates.",
                candidate_count=len(documents),
            )
            return self._rank_from_scores(documents, scores)

        initial_workers = self._ranking_concurrency()
        self._emit_ranking_step(
            step_id,
            "processing",
            step_title,
            current=0,
            total=len(batches),
            detail=f"Scoring {len(documents)} candidates in {len(batches)} LLM batches; concurrency={initial_workers}.",
            concurrency=initial_workers,
            batch_size=batch_size,
            candidate_count=len(documents),
        )
        self._emit_log(
            f"Result ranking started in {len(batches)} batches; "
            f"candidates={len(documents)}; batch_size={batch_size}; concurrency={initial_workers}."
        )
        scores = []
        remaining_batches = [(index, batch) for index, batch in enumerate(batches, 1)]
        completed_batches = 0
        schedule = self._ranking_concurrency_schedule(len(batches))
        for tier_index, workers in enumerate(schedule):
            if not remaining_batches:
                break
            run_workers = workers
            if tier_index > 0:
                self._emit_log(f"Retrying {len(remaining_batches)} failed result-ranking batch(es) with concurrency={run_workers}.")
            failed_batches = []
            lower_tier_available = tier_index < len(schedule) - 1
            backoff_to_lower_tier = False
            worklist = list(remaining_batches)
            for start in range(0, len(worklist), run_workers):
                chunk = worklist[start:start + run_workers]
                with ThreadPoolExecutor(max_workers=run_workers) as executor:
                    future_to_batch = {
                        executor.submit(self._score_ranking_batch, question, batch, self._new_ranking_llm_client()): (index, batch)
                        for index, batch in chunk
                    }
                    for future in as_completed(future_to_batch):
                        index, batch = future_to_batch[future]
                        try:
                            batch_scores = future.result()
                        except Exception as exc:
                            self._emit_log(
                                f"Result ranking batch {index}/{len(batches)} failed at concurrency={run_workers}; "
                                f"will retry if a lower concurrency tier is available: {exc}"
                            )
                            failed_batches.append((index, batch))
                            if lower_tier_available and self._is_rate_limit_error(exc):
                                backoff_to_lower_tier = True
                            self._emit_ranking_step(
                                step_id,
                                "processing",
                                step_title,
                                current=completed_batches,
                                total=len(batches),
                                detail=f"Batch {index}/{len(batches)} failed at concurrency={run_workers}; retrying failed batches with lower concurrency.",
                                concurrency=run_workers,
                                batch_size=batch_size,
                                candidate_count=len(documents),
                            )
                            continue
                        scores.extend(batch_scores)
                        completed_batches += 1
                        self._emit_log(f"Result ranking batch {index}/{len(batches)} completed; candidates={len(batch)}; scored={len(batch_scores)}.")
                        self._emit_ranking_step(
                            step_id,
                            "processing",
                            step_title,
                            current=completed_batches,
                            total=len(batches),
                            detail=f"Completed batch {index}/{len(batches)} at concurrency={run_workers}.",
                            concurrency=run_workers,
                            batch_size=batch_size,
                            candidate_count=len(documents),
                        )
                if backoff_to_lower_tier:
                    unsubmitted = worklist[start + len(chunk):]
                    failed_batches.extend(unsubmitted)
                    self._emit_log(
                        f"Rate limit detected at concurrency={run_workers}; "
                        f"moving {len(failed_batches)} failed or unsubmitted batch(es) to the next lower concurrency tier."
                    )
                    break
            remaining_batches = failed_batches

        if remaining_batches:
            self._emit_log(
                f"{len(remaining_batches)} result ranking batch(es) still failed at minimum concurrency=4; "
                "returning those candidates in source order with zero scores."
            )
            failed_docs = sum(len(batch) for _, batch in remaining_batches)
            self._emit_ranking_step(
                step_id,
                "skipped" if not scores else "complete",
                step_title,
                current=completed_batches,
                total=len(batches),
                detail=(
                    f"{len(remaining_batches)} batch(es), {failed_docs} candidates, failed even at concurrency=4; "
                    "keeping local pre-ranking order for those candidates."
                ),
                concurrency=4,
                batch_size=batch_size,
                candidate_count=len(documents),
            )

        if not scores:
            self._emit_log("All result ranking batches failed; returning candidates in source order with zero scores.")
            self._emit_ranking_step(
                step_id,
                "skipped",
                step_title,
                current=completed_batches,
                total=len(batches),
                detail="All LLM ranking batches failed or timed out; keeping the local pre-ranking order.",
                concurrency=4,
                batch_size=batch_size,
                candidate_count=len(documents),
            )
        elif not remaining_batches:
            self._emit_ranking_step(
                step_id,
                "complete",
                step_title,
                current=len(batches),
                total=len(batches),
                detail=f"LLM scoring completed for {completed_batches}/{len(batches)} batches.",
                concurrency=initial_workers,
                batch_size=batch_size,
                candidate_count=len(documents),
            )
        return self._rank_from_scores(documents, scores)

    def _ranking_batch_size(self, total_documents: int) -> int:
        configured = getattr(self.config, "ranking_batch_size", 8) or 8
        try:
            batch_size = max(1, int(configured))
        except (TypeError, ValueError):
            batch_size = 8
        return min(max(1, batch_size), max(1, total_documents))

    def _ranking_concurrency(self) -> int:
        configured = getattr(self.config, "ranking_concurrency", 16) or 16
        try:
            return min(32, max(4, int(configured)))
        except (TypeError, ValueError):
            return 16

    def _ranking_concurrency_schedule(self, batch_count: int) -> List[int]:
        configured = max(4, self._ranking_concurrency())
        tiers = [32, 16, 8, 4]
        schedule = []
        for tier in tiers:
            if tier <= configured and tier not in schedule:
                schedule.append(tier)
        if configured not in schedule:
            schedule.insert(0, configured)
        if 4 not in schedule:
            schedule.append(4)
        return schedule

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return "429" in text or "rate_limit" in text or "too many requests" in text

    def _ranking_llm_timeout_seconds(self) -> int:
        configured = getattr(self.config, "ranking_llm_timeout_seconds", 60) or 60
        try:
            return max(10, int(configured))
        except (TypeError, ValueError):
            return 60

    def _new_ranking_llm_client(self):
        timeout_seconds = self._ranking_llm_timeout_seconds()
        if hasattr(self.llm, "fork"):
            try:
                client = self.llm.fork()
                if hasattr(client, "timeout_seconds"):
                    client.timeout_seconds = timeout_seconds
                return client
            except Exception:
                pass
        client_class = self.llm.__class__
        api_key = getattr(self.llm, "api_key", None)
        base_url = getattr(self.llm, "base_url", "")
        if api_key is None:
            return self.llm
        try:
            if hasattr(self.llm, "models"):
                try:
                    return client_class(api_key, list(getattr(self.llm, "models") or []), base_url, timeout_seconds=timeout_seconds)
                except TypeError:
                    return client_class(api_key, list(getattr(self.llm, "models") or []), base_url)
            model = getattr(self.llm, "model", "")
            attempts = getattr(self.llm, "attempts", None)
            if attempts is not None:
                try:
                    return client_class(api_key, model=model, base_url=base_url, attempts=attempts, timeout_seconds=timeout_seconds)
                except TypeError:
                    try:
                        return client_class(api_key, model=model, base_url=base_url, attempts=attempts)
                    except TypeError:
                        pass
            try:
                return client_class(api_key, model=model, base_url=base_url, timeout_seconds=timeout_seconds)
            except TypeError:
                try:
                    return client_class(api_key, model, base_url, timeout_seconds=timeout_seconds)
                except TypeError:
                    return client_class(api_key, model, base_url)
        except Exception:
            return self.llm

    def _score_ranking_batch(self, question: str, documents: list, llm_client: LLMClient) -> list:
        descriptions = []
        for i, doc in enumerate(documents, 1):
            descriptions.append(_describe_document(doc, i))

        papers_text = "\n\n".join(descriptions)

        messages = [
            {"role": "system", "content": SYSTEM_RESULT_RANKING},
            {"role": "user", "content": (
                f"Research question: {question}\n\n"
                f"Papers to evaluate:\n\n{papers_text}\n\n"
                f"Output ONLY the JSON array."
            )},
        ]

        raw = llm_client.chat(messages, temperature=0.3)
        return self._parse_ranking_response(raw)

    def _rank_from_scores(self, documents: list, scores: list) -> list:
        uid_to_doc = {doc.uid: doc for doc in documents}

        ranked = []
        for entry in scores:
            uid = entry.get("uid", "")
            doc = uid_to_doc.get(uid)
            if doc is None:
                for d in documents:
                    if d.uid and uid and (uid in d.uid or d.uid in uid):
                        doc = d
                        break
            if doc is None and uid:
                continue

            ranked.append({
                "document": doc,
                "score": entry.get("score", 0),
                "reasoning": entry.get("reasoning", ""),
                **self._retrieval_entry_metadata(doc),
            })

        remaining = [d for d in documents if d.uid not in {e.get("uid", "") for e in scores}]
        for doc in remaining:
            ranked.append({"document": doc, "score": 0, "reasoning": "", **self._retrieval_entry_metadata(doc)})

        return sorted(ranked, key=lambda item: float(item.get("score") or 0), reverse=True)

    def _retrieval_entry_metadata(self, doc) -> Dict[str, Any]:
        key = document_key(doc)
        if not key:
            return {}
        return dict(self.retrieval_metadata_by_key.get(key, {}))

    def _parse_ranking_response(self, raw: str) -> list:
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        return []

    def _enrich_with_abstracts(self, ranked: list) -> list:
        for entry in ranked:
            doc = entry["document"]
            if not doc:
                continue
            identifiers = getattr(doc, "identifiers", None)
            if identifiers:
                doi = getattr(identifiers, "doi", None)
                if doi:
                    abstract = self.abstract_fetcher.fetch(doi)
                    if abstract:
                        entry["abstract"] = abstract
        return ranked


LiteratureSearchAgent = PaperSeekAgent
WosSearchAgent = PaperSeekAgent
