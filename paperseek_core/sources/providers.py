from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
from typing import Any, Dict, List, Optional, Sequence, Tuple
import re
import requests
import threading
import time
import xml.etree.ElementTree as ET

from paperseek_core.retrieval import ProviderRetrievalCapabilities, RetrievalLane


@dataclass
class PaperAuthor:
    display_name: str = ""
    wos_standard: str = ""
    researcher_id: str = ""


@dataclass
class PaperNames:
    authors: List[PaperAuthor] = field(default_factory=list)


@dataclass
class PaperSource:
    source_title: str = ""
    publish_year: Optional[int] = None
    publish_month: str = ""
    volume: str = ""
    issue: str = ""
    pages: Any = None


@dataclass
class PaperLinks:
    record: str = ""
    citing_articles: str = ""
    references: str = ""
    related: str = ""
    landing_page: str = ""
    pdf: str = ""


@dataclass
class PaperCitation:
    db: str = ""
    count: int = 0


@dataclass
class PaperIdentifiers:
    doi: str = ""
    issn: str = ""
    eissn: str = ""
    isbn: str = ""
    eisbn: str = ""
    pmid: str = ""
    openalex: str = ""
    arxiv: str = ""
    semanticscholar: str = ""


@dataclass
class PaperKeywords:
    author_keywords: List[str] = field(default_factory=list)


@dataclass
class PaperRecord:
    uid: str
    title: str = ""
    types: List[str] = field(default_factory=list)
    source_types: List[str] = field(default_factory=list)
    source: Optional[PaperSource] = None
    names: Optional[PaperNames] = None
    links: Optional[PaperLinks] = None
    citations: List[PaperCitation] = field(default_factory=list)
    identifiers: Optional[PaperIdentifiers] = None
    keywords: Optional[PaperKeywords] = None
    abstract: str = ""
    provider: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CitationSeedPlan:
    record: PaperRecord
    role: str = "relevance"
    directions: Tuple[str, ...] = ("backward", "forward")
    depth: int = 1


@dataclass
class SearchMetadata:
    total: int = 0
    page: int = 1
    limit: int = 10


@dataclass
class ProviderSearchResult:
    metadata: SearchMetadata
    hits: List[PaperRecord]


class ProviderError(Exception):
    def __init__(self, source: str, message: str, status: Optional[int] = None, body: str = "", query: str = ""):
        super().__init__(message)
        self.source = source
        self.status = status
        self.body = body
        self.query = query


def _redact_request_text(value: object) -> str:
    text = str(value or "")
    if not text:
        return ""
    return re.sub(r"([?&](?:api_key|apikey|key|token|access_token)=)[^&\s)]+", r"\1<redacted>", text, flags=re.I)


def reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    if not inverted_index:
        return ""

    positions: Dict[int, str] = {}
    for word, indexes in inverted_index.items():
        if not isinstance(indexes, list):
            continue
        for idx in indexes:
            if isinstance(idx, int):
                positions[idx] = word

    if not positions:
        return ""

    return " ".join(positions[i] for i in sorted(positions))


def normalize_doi(value: str) -> str:
    value = (value or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.lower().startswith(prefix):
            return value[len(prefix):].strip()
    return value


def get_with_retries(
    source: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    query: str = "",
    attempts: int = 3,
):
    last_exc: Optional[requests.RequestException] = None
    started = time.perf_counter()
    for attempt in range(1, max(1, attempts) + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            info = {
                "method": "GET",
                "url": _redact_request_text(response.url),
                "status": response.status_code,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "attempts": attempt,
            }
            if response.status_code in {429, 500, 502, 503, 504} and attempt < attempts:
                time.sleep(_retry_delay(response, attempt, source))
                continue
            return response, info
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < attempts:
                time.sleep(0.7 * attempt)

    info = {
        "method": "GET",
        "url": url,
        "status": "request_error",
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "attempts": attempts,
    }
    detail = _redact_request_text(last_exc)
    raise ProviderError(source, f"{source.title()} request failed after {attempts} attempts: {detail}", query=query) from last_exc


def _split_api_keys(value: str) -> List[str]:
    return list(dict.fromkeys(item.strip() for item in re.split(r"[\s,;]+", value or "") if item.strip()))


def _retry_delay(response: requests.Response, attempt: int, source: str = "") -> float:
    retry_after = response.headers.get("Retry-After", "")
    try:
        return max(0.7 * attempt, min(float(retry_after), 15.0))
    except (TypeError, ValueError):
        if response.status_code == 429 and (source or "").lower() == "arxiv":
            return min(5.0 * attempt, 20.0)
        return 0.7 * attempt


class OpenAlexProvider:
    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, api_key: str = "", email: str = ""):
        self.api_key = (api_key or "").strip()
        self.email = (email or "").strip()
        self.last_response_info: Dict[str, Any] = {}

    def retrieval_capabilities(self) -> ProviderRetrievalCapabilities:
        return ProviderRetrievalCapabilities(
            source="openalex",
            lanes=(RetrievalLane.RELEVANCE, RetrievalLane.IMPACT, RetrievalLane.RECENT),
        )

    def search(
        self,
        query: str,
        limit: int = 50,
        page: int = 1,
        field_ids: Optional[Sequence[str]] = None,
        lane: str = RetrievalLane.RELEVANCE,
    ) -> ProviderSearchResult:
        query = (query or "").strip()
        if not query:
            raise ProviderError("openalex", "OpenAlex search query is empty.")

        page_size = max(1, min(int(limit or 10), 100))
        params = {
            "search": query,
            "per-page": page_size,
            "page": max(1, int(page or 1)),
            "select": ",".join([
                "id",
                "doi",
                "title",
                "display_name",
                "publication_year",
                "publication_date",
                "type",
                "type_crossref",
                "authorships",
                "primary_location",
                "cited_by_count",
                "abstract_inverted_index",
                "open_access",
                "keywords",
                "concepts",
                "ids",
                "primary_topic",
                "referenced_works",
            ]),
        }
        normalized_field_ids = self._normalize_field_ids(field_ids)
        if normalized_field_ids:
            params["filter"] = self._field_filter_clause(normalized_field_ids)
        if lane == RetrievalLane.IMPACT:
            params["sort"] = "cited_by_count:desc"
        elif lane == RetrievalLane.RECENT:
            params["sort"] = "publication_date:desc"
        elif lane == RetrievalLane.RELEVANCE:
            params["sort"] = "relevance_score:desc"
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["mailto"] = self.email

        headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent(),
        }

        try:
            response, info = get_with_retries("openalex", self.BASE_URL, params=params, headers=headers, timeout=45, query=query)
            self.last_response_info = info
        except ProviderError as exc:
            self.last_response_info = {"method": "GET", "url": self.BASE_URL, "status": "request_error", "elapsed_ms": None}
            raise exc


        if response.status_code >= 400:
            raise ProviderError(
                "openalex",
                f"OpenAlex returned HTTP {response.status_code}.",
                status=response.status_code,
                body=response.text[:1000],
                query=query,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("openalex", "OpenAlex returned a non-JSON response.", body=response.text[:1000], query=query) from exc

        meta = payload.get("meta") or {}
        works = payload.get("results") or []
        records = [self._to_record(work) for work in works if isinstance(work, dict)]

        return ProviderSearchResult(
            metadata=SearchMetadata(
                total=int(meta.get("count") or 0),
                page=int(meta.get("page") or page),
                limit=int(meta.get("per_page") or page_size),
            ),
            hits=records,
        )

    def citation_neighbors(
        self,
        seeds: List[PaperRecord],
        per_seed: int = 4,
        max_records: int = 40,
        field_ids: Optional[Sequence[str]] = None,
    ) -> List[PaperRecord]:
        return self.citation_neighbors_with_graph(seeds, per_seed=per_seed, max_records=max_records, field_ids=field_ids)["records"]

    def citation_neighbors_with_graph(
        self,
        seeds: List[PaperRecord],
        per_seed: int = 4,
        max_records: int = 40,
        field_ids: Optional[Sequence[str]] = None,
        seed_plans: Optional[Sequence[Any]] = None,
        depth: int = 1,
    ) -> Dict[str, Any]:
        """Fetch forward and backward citation neighbors for seed OpenAlex works."""
        per_seed = max(1, min(int(per_seed or 4), 10))
        max_records = max(1, min(int(max_records or 40), 500))
        depth = max(1, min(int(depth or 1), 3))
        normalized_field_ids = self._normalize_field_ids(field_ids)
        output: List[PaperRecord] = []
        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, str]] = []
        seen = set()
        expanded = set()

        def add_node(record: PaperRecord, role: str, seed_uid: str = ""):
            node_id = record.uid or (record.identifiers.openalex if record.identifiers else "") or record.title
            if not node_id:
                return
            source = record.source
            citations = sum((c.count or 0) for c in (record.citations or []))
            existing = nodes.get(node_id)
            if existing:
                if role not in existing["roles"]:
                    existing["roles"].append(role)
                if seed_uid and seed_uid not in existing["seed_uids"]:
                    existing["seed_uids"].append(seed_uid)
                return
            nodes[node_id] = {
                "id": node_id,
                "title": record.title or "(no title)",
                "year": source.publish_year if source else None,
                "source": source.source_title if source else "",
                "citations": citations,
                "roles": [role],
                "seed_uids": [seed_uid] if seed_uid else [],
            }

        def add_record(record: Optional[PaperRecord]):
            if not record:
                return
            key = (record.uid or "").lower()
            doi = ((record.identifiers.doi if record.identifiers else "") or "").lower()
            dedupe = key or doi
            if not dedupe or dedupe in seen:
                return
            seen.add(dedupe)
            output.append(record)

        def normalize_seed_plans() -> List[CitationSeedPlan]:
            plans: List[CitationSeedPlan] = []
            raw_plans = seed_plans or [
                {"record": seed, "role": "relevance", "directions": ("backward", "forward"), "depth": depth}
                for seed in (seeds or [])
            ]
            for item in raw_plans:
                if isinstance(item, CitationSeedPlan):
                    plan = item
                elif isinstance(item, dict):
                    record = item.get("record") or item.get("seed")
                    if not isinstance(record, PaperRecord):
                        continue
                    directions = tuple(
                        direction
                        for direction in (item.get("directions") or ("backward", "forward"))
                        if direction in ("backward", "forward")
                    )
                    plan = CitationSeedPlan(
                        record=record,
                        role=str(item.get("role") or "relevance"),
                        directions=directions or ("backward", "forward"),
                        depth=max(1, min(int(item.get("depth") or depth), 3)),
                    )
                elif isinstance(item, PaperRecord):
                    plan = CitationSeedPlan(record=item, depth=depth)
                else:
                    continue
                plans.append(plan)
            return plans

        def append_neighbor(
            *,
            seed_uid: str,
            parent_uid: str,
            record: Optional[PaperRecord],
            direction: str,
            layer: int,
            next_frontier: List[PaperRecord],
            frontier_seen: set,
        ):
            if not record or not self._record_matches_field_ids(record, normalized_field_ids):
                return
            record_uid = record.uid or (record.identifiers.openalex if record.identifiers else "") or record.title
            if not record_uid:
                return
            role = "backward" if direction == "backward" else "forward"
            add_node(record, role, seed_uid)
            if direction == "backward":
                edge = {
                    "source": parent_uid,
                    "target": record_uid,
                    "type": "references",
                    "seed": seed_uid,
                    "layer": str(layer),
                }
            else:
                edge = {
                    "source": record_uid,
                    "target": parent_uid,
                    "type": "cites",
                    "seed": seed_uid,
                    "layer": str(layer),
                }
            edges.append(edge)
            add_record(record)
            if layer < depth and record_uid not in frontier_seen:
                frontier_seen.add(record_uid)
                next_frontier.append(record)

        for plan in normalize_seed_plans():
            if len(output) >= max_records:
                break
            seed = plan.record
            seed_id = self._openalex_work_id(seed)
            if not seed_id:
                continue
            seed_uid = seed.uid or (seed.identifiers.openalex if seed.identifiers else "") or seed_id
            add_node(seed, "seed")
            add_node(seed, f"seed_{plan.role}", seed_uid)
            frontier = [seed]
            frontier_seen = {seed_uid}
            for layer in range(1, max(1, min(plan.depth, depth)) + 1):
                next_frontier: List[PaperRecord] = []
                for current in frontier:
                    if len(output) >= max_records:
                        break
                    current_id = self._openalex_work_id(current)
                    if not current_id:
                        continue
                    current_uid = current.uid or (current.identifiers.openalex if current.identifiers else "") or current_id
                    if "backward" in plan.directions:
                        expand_key = (current_id, "backward", layer)
                        if expand_key not in expanded:
                            expanded.add(expand_key)
                            for ref_url in (current.raw.get("referenced_works") or [])[:per_seed]:
                                if len(output) >= max_records:
                                    break
                                try:
                                    record = self._fetch_work(ref_url)
                                except ProviderError:
                                    continue
                                append_neighbor(
                                    seed_uid=seed_uid,
                                    parent_uid=current_uid,
                                    record=record,
                                    direction="backward",
                                    layer=layer,
                                    next_frontier=next_frontier,
                                    frontier_seen=frontier_seen,
                                )
                    if len(output) >= max_records:
                        break
                    if "forward" in plan.directions:
                        expand_key = (current_id, "forward", layer)
                        if expand_key in expanded:
                            continue
                        expanded.add(expand_key)
                        try:
                            records = self._fetch_forward_citations(current_id, per_seed, field_ids=normalized_field_ids)
                        except ProviderError:
                            continue
                        for record in records:
                            if len(output) >= max_records:
                                break
                            append_neighbor(
                                seed_uid=seed_uid,
                                parent_uid=current_uid,
                                record=record,
                                direction="forward",
                                layer=layer,
                                next_frontier=next_frontier,
                                frontier_seen=frontier_seen,
                            )
                frontier = next_frontier
                if not frontier or len(output) >= max_records:
                    break

        return {"records": output, "nodes": list(nodes.values()), "edges": edges}

    @classmethod
    def _normalize_field_ids(cls, field_ids: Optional[Sequence[str]]) -> List[str]:
        ids: List[str] = []
        for field_id in field_ids or []:
            normalized = cls._normalize_openalex_id(str(field_id))
            if normalized and normalized not in ids:
                ids.append(normalized)
        return ids

    @staticmethod
    def _field_filter_clause(field_ids: Sequence[str]) -> str:
        ids = [str(field_id).strip() for field_id in (field_ids or []) if str(field_id).strip()]
        return "primary_topic.field.id:" + "|".join(ids) if ids else ""

    @classmethod
    def _record_matches_field_ids(cls, record: PaperRecord, field_ids: Sequence[str]) -> bool:
        if not field_ids:
            return True
        raw = record.raw if isinstance(getattr(record, "raw", None), dict) else {}
        primary_topic = raw.get("primary_topic") or {}
        field = primary_topic.get("field") or {}
        work_field_id = cls._normalize_openalex_id(str(field.get("id") or ""))
        return bool(work_field_id and work_field_id in field_ids)

    def _base_params(self) -> Dict[str, str]:
        params: Dict[str, str] = {}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["mailto"] = self.email
        return params

    def _fetch_work(self, openalex_id: str) -> Optional[PaperRecord]:
        identifier = self._normalize_openalex_id(openalex_id)
        if not identifier:
            return None
        url = f"{self.BASE_URL}/{identifier}"
        headers = {"Accept": "application/json", "User-Agent": self._user_agent()}
        try:
            response, info = get_with_retries("openalex", url, params=self._base_params(), headers=headers, timeout=30, query=identifier)
            self.last_response_info = info
        except ProviderError as exc:
            self.last_response_info = {"method": "GET", "url": url, "status": "request_error", "elapsed_ms": None}
            raise exc

        if response.status_code >= 400:
            raise ProviderError("openalex", f"OpenAlex returned HTTP {response.status_code}.", status=response.status_code, body=response.text[:1000], query=identifier)
        try:
            work = response.json()
        except ValueError as exc:
            raise ProviderError("openalex", "OpenAlex returned a non-JSON citation response.", body=response.text[:1000], query=identifier) from exc
        return self._to_record(work) if isinstance(work, dict) else None

    def _fetch_forward_citations(self, seed_id: str, limit: int, field_ids: Optional[Sequence[str]] = None) -> List[PaperRecord]:
        params = self._base_params()
        filter_parts = [f"cites:{seed_id}"]
        field_clause = self._field_filter_clause(self._normalize_field_ids(field_ids))
        if field_clause:
            filter_parts.append(field_clause)
        params.update({
            "filter": ",".join(filter_parts),
            "sort": "cited_by_count:desc",
            "per-page": max(1, min(int(limit or 4), 10)),
            "select": ",".join([
                "id",
                "doi",
                "title",
                "display_name",
                "publication_year",
                "publication_date",
                "type",
                "type_crossref",
                "authorships",
                "primary_location",
                "cited_by_count",
                "abstract_inverted_index",
                "open_access",
                "keywords",
                "concepts",
                "ids",
                "primary_topic",
                "referenced_works",
            ]),
        })
        headers = {"Accept": "application/json", "User-Agent": self._user_agent()}
        try:
            response, info = get_with_retries("openalex", self.BASE_URL, params=params, headers=headers, timeout=30, query=seed_id)
            self.last_response_info = info
        except ProviderError as exc:
            self.last_response_info = {"method": "GET", "url": self.BASE_URL, "status": "request_error", "elapsed_ms": None}
            raise exc

        if response.status_code >= 400:
            raise ProviderError("openalex", f"OpenAlex returned HTTP {response.status_code}.", status=response.status_code, body=response.text[:1000], query=seed_id)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("openalex", "OpenAlex returned a non-JSON forward citation response.", body=response.text[:1000], query=seed_id) from exc
        return [self._to_record(work) for work in (payload.get("results") or []) if isinstance(work, dict)]

    def _user_agent(self) -> str:
        if self.email:
            return f"paperseek/1.0 (mailto:{self.email})"
        return "paperseek/1.0"

    def _to_record(self, work: Dict[str, Any]) -> PaperRecord:
        openalex_id = work.get("id") or ""
        title = work.get("title") or work.get("display_name") or ""
        primary_location = work.get("primary_location") or {}
        source_obj = primary_location.get("source") or {}
        source_title = source_obj.get("display_name") or ""
        landing_page = primary_location.get("landing_page_url") or ""
        pdf_url = (primary_location.get("pdf_url") or "")

        authors = []
        for authorship in work.get("authorships") or []:
            author_obj = authorship.get("author") or {}
            display = author_obj.get("display_name") or ""
            if display:
                authors.append(PaperAuthor(display_name=display, wos_standard=display))

        keywords = self._extract_keywords(work)
        abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
        doi = normalize_doi(work.get("doi") or "")
        ids = work.get("ids") or {}

        work_type = work.get("type") or work.get("type_crossref") or ""
        record_url = openalex_id or landing_page
        cited_by_count = int(work.get("cited_by_count") or 0)

        return PaperRecord(
            uid=openalex_id or title,
            title=title,
            types=[work_type] if work_type else [],
            source_types=[work_type] if work_type else [],
            source=PaperSource(
                source_title=source_title,
                publish_year=work.get("publication_year"),
            ),
            names=PaperNames(authors=authors),
            links=PaperLinks(record=record_url, landing_page=landing_page, pdf=pdf_url),
            citations=[PaperCitation(db="OpenAlex", count=cited_by_count)] if cited_by_count else [],
            identifiers=PaperIdentifiers(
                doi=doi,
                openalex=openalex_id,
                pmid=(ids.get("pmid") or "").replace("https://pubmed.ncbi.nlm.nih.gov/", ""),
            ),
            keywords=PaperKeywords(author_keywords=keywords),
            abstract=abstract,
            provider="openalex",
            raw=work,
        )

    @staticmethod
    def _normalize_openalex_id(value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        return value.rstrip("/").split("/")[-1]

    def _openalex_work_id(self, record: PaperRecord) -> str:
        identifiers = record.identifiers
        value = (identifiers.openalex if identifiers else "") or record.uid or ""
        return self._normalize_openalex_id(value)

    @staticmethod
    def _extract_keywords(work: Dict[str, Any]) -> List[str]:
        terms = []
        for item in work.get("keywords") or []:
            value = item.get("display_name") or item.get("keyword") or item.get("name")
            if value and value not in terms:
                terms.append(value)
        if terms:
            return terms[:10]

        for item in work.get("concepts") or []:
            value = item.get("display_name")
            if value and value not in terms:
                terms.append(value)
        return terms[:10]


class CrossrefProvider:
    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, email: str = ""):
        self.email = (email or "").strip()
        self.last_response_info: Dict[str, Any] = {}

    def retrieval_capabilities(self) -> ProviderRetrievalCapabilities:
        return ProviderRetrievalCapabilities(
            source="crossref",
            lanes=(RetrievalLane.RELEVANCE, RetrievalLane.IMPACT, RetrievalLane.RECENT),
        )

    def search(self, query: str, limit: int = 50, page: int = 1, lane: str = RetrievalLane.RELEVANCE) -> ProviderSearchResult:
        query = (query or "").strip()
        if not query:
            raise ProviderError("crossref", "Crossref search query is empty.")

        page_size = max(1, min(int(limit or 10), 100))
        params = {
            "query.bibliographic": query,
            "rows": page_size,
            "offset": max(0, (int(page or 1) - 1) * page_size),
            "order": "desc",
            "select": ",".join([
                "DOI",
                "title",
                "author",
                "published-print",
                "published-online",
                "issued",
                "container-title",
                "type",
                "is-referenced-by-count",
                "URL",
                "abstract",
                "ISSN",
                "ISBN",
            ]),
        }
        if lane == RetrievalLane.IMPACT:
            params["sort"] = "is-referenced-by-count"
        elif lane == RetrievalLane.RECENT:
            params["sort"] = "published"
        if self.email:
            params["mailto"] = self.email

        headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent(),
        }

        try:
            response, info = get_with_retries("crossref", self.BASE_URL, params=params, headers=headers, timeout=45, query=query)
            self.last_response_info = info
        except ProviderError as exc:
            self.last_response_info = {"method": "GET", "url": self.BASE_URL, "status": "request_error", "elapsed_ms": None}
            raise exc


        if response.status_code >= 400:
            raise ProviderError(
                "crossref",
                f"Crossref returned HTTP {response.status_code}.",
                status=response.status_code,
                body=response.text[:1000],
                query=query,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("crossref", "Crossref returned a non-JSON response.", body=response.text[:1000], query=query) from exc

        message = payload.get("message") or {}
        items = message.get("items") or []
        records = [self._to_record(item) for item in items if isinstance(item, dict)]

        return ProviderSearchResult(
            metadata=SearchMetadata(
                total=int(message.get("total-results") or 0),
                page=max(1, int(page or 1)),
                limit=page_size,
            ),
            hits=records,
        )

    def _user_agent(self) -> str:
        if self.email:
            return f"paperseek/1.0 (mailto:{self.email})"
        return "paperseek/1.0"

    def _to_record(self, item: Dict[str, Any]) -> PaperRecord:
        doi = normalize_doi(item.get("DOI") or "")
        title = self._first(item.get("title")) or doi
        authors = []
        for author in item.get("author") or []:
            parts = [author.get("given") or "", author.get("family") or ""]
            name = " ".join(p for p in parts if p).strip()
            if not name:
                name = author.get("name") or ""
            if name:
                authors.append(PaperAuthor(display_name=name, wos_standard=name))

        source_title = self._first(item.get("container-title"))
        year = self._extract_year(item)
        work_type = item.get("type") or ""
        abstract = self._clean_xml(item.get("abstract") or "")
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")

        issn = self._first(item.get("ISSN"))
        isbn = self._first(item.get("ISBN"))
        cited_by_count = int(item.get("is-referenced-by-count") or 0)

        return PaperRecord(
            uid=f"DOI:{doi}" if doi else url or title,
            title=title,
            types=[work_type] if work_type else [],
            source_types=[work_type] if work_type else [],
            source=PaperSource(source_title=source_title, publish_year=year),
            names=PaperNames(authors=authors),
            links=PaperLinks(record=url, landing_page=url),
            citations=[PaperCitation(db="Crossref", count=cited_by_count)] if cited_by_count else [],
            identifiers=PaperIdentifiers(doi=doi, issn=issn, isbn=isbn),
            keywords=PaperKeywords(author_keywords=[]),
            abstract=abstract,
            provider="crossref",
            raw=item,
        )

    @staticmethod
    def _first(value: Any) -> str:
        if isinstance(value, list) and value:
            return str(value[0] or "")
        if value:
            return str(value)
        return ""

    @staticmethod
    def _extract_year(item: Dict[str, Any]) -> Optional[int]:
        for key in ("published-print", "published-online", "issued"):
            date_parts = ((item.get(key) or {}).get("date-parts") or [])
            if date_parts and date_parts[0]:
                try:
                    return int(date_parts[0][0])
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _clean_xml(text: str) -> str:
        if not text:
            return ""
        import re

        text = re.sub(r"<[^>]+>", "", text)
        text = (
            text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )
        return re.sub(r"\s+", " ", text).strip()


class GoogleScholarSerperProvider:
    BASE_URL = "https://google.serper.dev/scholar"

    def __init__(self, api_key: str = ""):
        self.api_keys = _split_api_keys(api_key)
        self.last_response_info: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._index = 0

    def retrieval_capabilities(self) -> ProviderRetrievalCapabilities:
        return ProviderRetrievalCapabilities(
            source="googlescholar",
            lanes=(RetrievalLane.RELEVANCE,),
            max_lane_limit=100,
        )

    def search(self, query: str, limit: int = 50, page: int = 1, lane: str = RetrievalLane.RELEVANCE) -> ProviderSearchResult:
        query = (query or "").strip()
        if not query:
            raise ProviderError("googlescholar", "Google Scholar search query is empty.")
        if not self.api_keys:
            raise ProviderError("googlescholar", "SERPER_API_KEY or SERPER_API_KEYS is required for Google Scholar searches.", query=query)

        requested_limit = max(1, min(int(limit or 10), 100))
        page_size = 10
        page_number = max(1, int(page or 1))
        records: List[PaperRecord] = []
        total = 0
        last_info: Dict[str, Any] = {}
        while len(records) < requested_limit:
            payload = {
                "q": query,
                "page": page_number,
            }
            response, info = self._post_with_key_rotation(payload, query=query)
            last_info = info
            if response.status_code >= 400:
                raise ProviderError(
                    "googlescholar",
                    f"Google Scholar via Serper returned HTTP {response.status_code}.",
                    status=response.status_code,
                    body=response.text[:1000],
                    query=query,
                )
            try:
                data = response.json()
            except ValueError as exc:
                raise ProviderError("googlescholar", "Google Scholar via Serper returned a non-JSON response.", body=response.text[:1000], query=query) from exc

            items = [item for item in data.get("organic") or [] if isinstance(item, dict)]
            if not total:
                total = self._total(data, items, page_number, page_size)
            records.extend(self._to_record(item) for item in items)
            if len(items) < page_size:
                break
            page_number += 1
        self.last_response_info = last_info
        records = records[:requested_limit]
        if not total:
            total = len(records)
        return ProviderSearchResult(
            metadata=SearchMetadata(total=total, page=max(1, int(page or 1)), limit=requested_limit),
            hits=records,
        )

    def _post_with_key_rotation(self, payload: Dict[str, Any], query: str):
        last_response: Optional[requests.Response] = None
        last_exc: Optional[requests.RequestException] = None
        started = time.perf_counter()
        attempts = max(1, min(max(3, len(self.api_keys)), len(self.api_keys) * 3))
        for attempt in range(1, attempts + 1):
            api_key = self._next_api_key()
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "paperseek/1.0",
                "X-API-KEY": api_key,
            }
            try:
                response = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=45)
                info = {
                    "method": "POST",
                    "url": self.BASE_URL,
                    "status": response.status_code,
                    "elapsed_ms": int((time.perf_counter() - started) * 1000),
                    "attempts": attempt,
                }
                last_response = response
                if response.status_code in {401, 403, 408, 409, 425, 429, 500, 502, 503, 504} and attempt < attempts:
                    time.sleep(_retry_delay(response, attempt, "googlescholar"))
                    continue
                return response, info
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < attempts:
                    time.sleep(0.7 * attempt)
        if last_response is not None:
            return last_response, {
                "method": "POST",
                "url": self.BASE_URL,
                "status": last_response.status_code,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "attempts": attempts,
            }
        detail = _redact_request_text(last_exc)
        raise ProviderError("googlescholar", f"Google Scholar via Serper request failed after {attempts} attempts: {detail}", query=query) from last_exc

    def _next_api_key(self) -> str:
        with self._lock:
            index = self._index
            self._index += 1
        return self.api_keys[index % len(self.api_keys)]

    @staticmethod
    def _total(data: Dict[str, Any], records: List[Any], page: int, page_size: int) -> int:
        for path in (
            ("searchInformation", "totalResults"),
            ("searchInformation", "total_results"),
            ("searchParameters", "totalResults"),
        ):
            value: Any = data
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
            try:
                if value not in (None, ""):
                    return int(str(value).replace(",", ""))
            except (TypeError, ValueError):
                pass
        return max(len(records), ((page - 1) * page_size) + len(records))

    def _to_record(self, item: Dict[str, Any]) -> PaperRecord:
        scholar_id = str(item.get("id") or item.get("resultId") or "")
        title = item.get("title") or scholar_id or item.get("link") or ""
        link = item.get("link") or ""
        pdf = item.get("pdfUrl") or ""
        year = self._year(item.get("year"))
        publication_info = item.get("publicationInfo") or {}
        authors = self._authors(publication_info)
        source_title = self._source_title(publication_info)
        cited_by = item.get("citedBy") or {}
        cited_total = 0
        citing_link = ""
        if isinstance(cited_by, dict):
            try:
                cited_total = int(cited_by.get("total") or 0)
            except (TypeError, ValueError):
                cited_total = 0
            citing_link = cited_by.get("link") or ""
        elif cited_by not in (None, ""):
            try:
                cited_total = int(cited_by)
            except (TypeError, ValueError):
                cited_total = 0
        snippet = item.get("snippet") or ""
        return PaperRecord(
            uid=f"googlescholar:{scholar_id}" if scholar_id else link or title,
            title=title,
            types=["scholarly result"],
            source_types=["scholarly result"],
            source=PaperSource(source_title=source_title or "Google Scholar", publish_year=year),
            names=PaperNames(authors=authors),
            links=PaperLinks(record=link, landing_page=link, pdf=pdf, citing_articles=citing_link),
            citations=[PaperCitation(db="Google Scholar", count=cited_total)] if cited_total else [],
            identifiers=PaperIdentifiers(),
            keywords=PaperKeywords(author_keywords=[]),
            abstract=snippet,
            provider="googlescholar",
            raw=item,
        )

    @staticmethod
    def _authors(publication_info: Any) -> List[PaperAuthor]:
        if not isinstance(publication_info, dict):
            return []
        authors = []
        for author in publication_info.get("authors") or []:
            if isinstance(author, dict):
                name = author.get("name") or author.get("title") or ""
            else:
                name = str(author or "")
            if name:
                authors.append(PaperAuthor(display_name=name))
        return authors

    @staticmethod
    def _source_title(publication_info: Any) -> str:
        if isinstance(publication_info, dict):
            summary = publication_info.get("summary") or publication_info.get("journal") or publication_info.get("venue") or ""
            return re.sub(r"\s+", " ", str(summary)).strip()
        return re.sub(r"\s+", " ", str(publication_info or "")).strip()

    @staticmethod
    def _year(value: Any) -> Optional[int]:
        try:
            if value not in (None, ""):
                return int(value)
        except (TypeError, ValueError):
            pass
        match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
        return int(match.group(0)) if match else None


class ArxivProvider:
    BASE_URL = "http://export.arxiv.org/api/query"
    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    _lock = threading.Lock()
    _last_request_at = 0.0

    def __init__(self):
        self.last_response_info: Dict[str, Any] = {}

    def retrieval_capabilities(self) -> ProviderRetrievalCapabilities:
        return ProviderRetrievalCapabilities(
            source="arxiv",
            lanes=(RetrievalLane.RELEVANCE, RetrievalLane.RECENT),
            max_lane_limit=200,
        )

    def search(self, query: str, limit: int = 50, page: int = 1, lane: str = RetrievalLane.RELEVANCE) -> ProviderSearchResult:
        query = (query or "").strip()
        if not query:
            raise ProviderError("arxiv", "arXiv search query is empty.")

        page_size = max(1, min(int(limit or 10), 100))
        params = {
            "search_query": self._search_query(query),
            "start": max(0, (int(page or 1) - 1) * page_size),
            "max_results": page_size,
            "sortBy": "submittedDate" if lane == RetrievalLane.RECENT else "relevance",
            "sortOrder": "descending",
        }
        headers = {"Accept": "application/atom+xml", "User-Agent": "paperseek/1.0"}
        try:
            self._throttle()
            response, info = get_with_retries("arxiv", self.BASE_URL, params=params, headers=headers, timeout=20, query=query, attempts=1)
            self.last_response_info = info
        except ProviderError as exc:
            self.last_response_info = {"method": "GET", "url": self.BASE_URL, "status": "request_error", "elapsed_ms": None}
            raise exc

        if response.status_code >= 400:
            raise ProviderError("arxiv", f"arXiv returned HTTP {response.status_code}.", status=response.status_code, body=response.text[:1000], query=query)

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise ProviderError("arxiv", "arXiv returned invalid Atom XML.", body=response.text[:1000], query=query) from exc

        total_text = root.findtext("opensearch:totalResults", default="", namespaces={"opensearch": "http://a9.com/-/spec/opensearch/1.1/"})
        try:
            total = int((total_text or "0").strip())
        except ValueError:
            total = 0
        entries = root.findall("atom:entry", self.ATOM_NS)
        return ProviderSearchResult(
            metadata=SearchMetadata(total=total, page=max(1, int(page or 1)), limit=page_size),
            hits=[self._to_record(entry) for entry in entries],
        )

    @staticmethod
    def _search_query(query: str) -> str:
        if re.search(r"\b(?:all|ti|au|abs|cat|id|jr):", query, flags=re.I):
            return query
        cleaned = re.sub(r"\s+", " ", query).strip()
        if not cleaned:
            return "all:*"
        if re.search(r"\b(AND|OR|ANDNOT)\b", cleaned, flags=re.I):
            return cleaned
        return f'all:"{ArxivProvider._quote_phrase(cleaned)}"'

    @staticmethod
    def _quote_phrase(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    @classmethod
    def _throttle(cls) -> None:
        with cls._lock:
            elapsed = time.monotonic() - cls._last_request_at
            if elapsed < 3.1:
                time.sleep(3.1 - elapsed)
            cls._last_request_at = time.monotonic()

    def _to_record(self, entry: ET.Element) -> PaperRecord:
        arxiv_url = self._text(entry, "atom:id")
        arxiv_id = arxiv_url.rstrip("/").split("/")[-1]
        title = self._clean(self._text(entry, "atom:title"))
        abstract = self._clean(self._text(entry, "atom:summary"))
        year = self._year(self._text(entry, "atom:published") or self._text(entry, "atom:updated"))
        authors = [
            PaperAuthor(display_name=self._clean(author.findtext("atom:name", default="", namespaces=self.ATOM_NS)))
            for author in entry.findall("atom:author", self.ATOM_NS)
        ]
        authors = [author for author in authors if author.display_name]
        pdf = ""
        landing_page = arxiv_url
        for link in entry.findall("atom:link", self.ATOM_NS):
            href = link.attrib.get("href") or ""
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf = href
            elif link.attrib.get("rel") == "alternate":
                landing_page = href
        doi = normalize_doi(self._text(entry, "arxiv:doi"))
        categories = []
        primary = entry.find("arxiv:primary_category", self.ATOM_NS)
        if primary is not None and primary.attrib.get("term"):
            categories.append(primary.attrib["term"])
        for category in entry.findall("atom:category", self.ATOM_NS):
            term = category.attrib.get("term")
            if term and term not in categories:
                categories.append(term)
        return PaperRecord(
            uid=f"arxiv:{arxiv_id}" if arxiv_id else arxiv_url or title,
            title=title,
            types=["preprint"],
            source_types=["preprint"],
            source=PaperSource(source_title="arXiv", publish_year=year),
            names=PaperNames(authors=authors),
            links=PaperLinks(record=landing_page, landing_page=landing_page, pdf=pdf),
            identifiers=PaperIdentifiers(doi=doi, arxiv=arxiv_id),
            keywords=PaperKeywords(author_keywords=categories),
            abstract=abstract,
            provider="arxiv",
            raw={"id": arxiv_id, "categories": categories, "url": arxiv_url},
        )

    def _text(self, entry: ET.Element, path: str) -> str:
        return entry.findtext(path, default="", namespaces=self.ATOM_NS)

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", unescape(text or "")).strip()

    @staticmethod
    def _year(value: str) -> Optional[int]:
        match = re.match(r"^(\d{4})", value or "")
        return int(match.group(1)) if match else None


class SemanticScholarProvider:
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    BULK_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
    FULL_FIELDS = (
        "paperId",
        "corpusId",
        "title",
        "abstract",
        "year",
        "publicationDate",
        "venue",
        "publicationVenue",
        "publicationTypes",
        "authors",
        "url",
        "externalIds",
        "citationCount",
        "fieldsOfStudy",
        "openAccessPdf",
    )
    FALLBACK_FIELDS = (
        "paperId",
        "corpusId",
        "title",
        "year",
        "publicationDate",
        "venue",
        "authors",
        "url",
        "externalIds",
        "citationCount",
    )

    def __init__(self, api_key: str = ""):
        self.api_key = (api_key or "").strip()
        self.last_response_info: Dict[str, Any] = {}

    def retrieval_capabilities(self) -> ProviderRetrievalCapabilities:
        return ProviderRetrievalCapabilities(
            source="semanticscholar",
            lanes=(RetrievalLane.RELEVANCE, RetrievalLane.IMPACT, RetrievalLane.RECENT),
        )

    def search(self, query: str, limit: int = 50, page: int = 1, lane: str = RetrievalLane.RELEVANCE) -> ProviderSearchResult:
        query = (query or "").strip()
        if not query:
            raise ProviderError("semanticscholar", "Semantic Scholar search query is empty.")

        if lane in (RetrievalLane.IMPACT, RetrievalLane.RECENT):
            return self._bulk_search(query, limit=limit, lane=lane)

        page_size = max(1, min(int(limit or 10), 100))
        params = {
            "query": query,
            "limit": page_size,
            "offset": max(0, (int(page or 1) - 1) * page_size),
            "fields": ",".join(self.FULL_FIELDS),
        }
        headers = {"Accept": "application/json", "User-Agent": "paperseek/1.0"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        try:
            response, info = get_with_retries("semanticscholar", self.BASE_URL, params=params, headers=headers, timeout=45, query=query)
            self.last_response_info = info
        except ProviderError as exc:
            self.last_response_info = {"method": "GET", "url": self.BASE_URL, "status": "request_error", "elapsed_ms": None}
            raise exc
        if response.status_code >= 500:
            fallback_params = dict(params)
            fallback_params["fields"] = ",".join(self.FALLBACK_FIELDS)
            response, fallback_info = get_with_retries(
                "semanticscholar",
                self.BASE_URL,
                params=fallback_params,
                headers=headers,
                timeout=45,
                query=query,
            )
            fallback_info["fallback"] = "basic_fields"
            self.last_response_info = fallback_info

        if response.status_code >= 400:
            raise ProviderError(
                "semanticscholar",
                f"Semantic Scholar returned HTTP {response.status_code}.",
                status=response.status_code,
                body=response.text[:1000],
                query=query,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("semanticscholar", "Semantic Scholar returned a non-JSON response.", body=response.text[:1000], query=query) from exc
        papers = payload.get("data") or []
        records = [self._to_record(item) for item in papers if isinstance(item, dict)]
        return ProviderSearchResult(
            metadata=SearchMetadata(total=int(payload.get("total") or len(records)), page=max(1, int(page or 1)), limit=page_size),
            hits=records,
        )

    def _bulk_search(self, query: str, limit: int = 50, lane: str = RetrievalLane.IMPACT) -> ProviderSearchResult:
        page_size = max(1, min(int(limit or 10), 1000))
        params = {
            "query": query,
            "limit": page_size,
            "fields": ",".join(self.FULL_FIELDS),
            "sort": "publicationDate:desc" if lane == RetrievalLane.RECENT else "citationCount:desc",
        }
        headers = {"Accept": "application/json", "User-Agent": "paperseek/1.0"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        try:
            response, info = get_with_retries("semanticscholar", self.BULK_URL, params=params, headers=headers, timeout=45, query=query)
            self.last_response_info = info
        except ProviderError as exc:
            self.last_response_info = {"method": "GET", "url": self.BULK_URL, "status": "request_error", "elapsed_ms": None}
            raise exc
        if response.status_code >= 500:
            fallback_params = dict(params)
            fallback_params["fields"] = ",".join(self.FALLBACK_FIELDS)
            response, fallback_info = get_with_retries(
                "semanticscholar",
                self.BULK_URL,
                params=fallback_params,
                headers=headers,
                timeout=45,
                query=query,
            )
            fallback_info["fallback"] = "basic_fields"
            self.last_response_info = fallback_info
        if response.status_code >= 400:
            raise ProviderError(
                "semanticscholar",
                f"Semantic Scholar returned HTTP {response.status_code}.",
                status=response.status_code,
                body=response.text[:1000],
                query=query,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("semanticscholar", "Semantic Scholar returned a non-JSON response.", body=response.text[:1000], query=query) from exc
        papers = payload.get("data") or []
        records = [self._to_record(item) for item in papers if isinstance(item, dict)]
        total = int(payload.get("total") or len(records))
        return ProviderSearchResult(metadata=SearchMetadata(total=total, page=1, limit=page_size), hits=records)

    def _to_record(self, item: Dict[str, Any]) -> PaperRecord:
        external = item.get("externalIds") or {}
        paper_id = str(item.get("paperId") or "")
        corpus_id = str(item.get("corpusId") or "")
        title = item.get("title") or paper_id or corpus_id
        authors = [
            PaperAuthor(display_name=str(author.get("name") or ""))
            for author in item.get("authors") or []
            if isinstance(author, dict) and author.get("name")
        ]
        venue_obj = item.get("publicationVenue") or {}
        venue = venue_obj.get("name") if isinstance(venue_obj, dict) else ""
        source_title = venue or item.get("venue") or ""
        pdf = ""
        open_pdf = item.get("openAccessPdf") or {}
        if isinstance(open_pdf, dict):
            pdf = open_pdf.get("url") or ""
        doi = normalize_doi(external.get("DOI") or external.get("DOIUrl") or "")
        pmid = str(external.get("PubMed") or "")
        arxiv_id = str(external.get("ArXiv") or "")
        citations = int(item.get("citationCount") or 0)
        fields = [str(value) for value in (item.get("fieldsOfStudy") or []) if value]
        publication_types = [str(value) for value in (item.get("publicationTypes") or []) if value]
        return PaperRecord(
            uid=paper_id or f"CorpusId:{corpus_id}" or title,
            title=title,
            types=publication_types,
            source_types=publication_types,
            source=PaperSource(source_title=source_title, publish_year=item.get("year")),
            names=PaperNames(authors=authors),
            links=PaperLinks(record=item.get("url") or "", landing_page=item.get("url") or "", pdf=pdf),
            citations=[PaperCitation(db="Semantic Scholar", count=citations)] if citations else [],
            identifiers=PaperIdentifiers(doi=doi, pmid=pmid, arxiv=arxiv_id, semanticscholar=paper_id),
            keywords=PaperKeywords(author_keywords=fields),
            abstract=item.get("abstract") or "",
            provider="semanticscholar",
            raw=item,
        )


class PubMedProvider:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, api_key: str = "", email: str = "", tool: str = "paperseek"):
        self.api_key = (api_key or "").strip()
        self.email = (email or "").strip()
        self.tool = (tool or "paperseek").strip()
        self.last_response_info: Dict[str, Any] = {}

    def retrieval_capabilities(self) -> ProviderRetrievalCapabilities:
        return ProviderRetrievalCapabilities(
            source="pubmed",
            lanes=(RetrievalLane.RELEVANCE, RetrievalLane.RECENT),
            max_lane_limit=500,
        )

    def search(self, query: str, limit: int = 50, page: int = 1, lane: str = RetrievalLane.RELEVANCE) -> ProviderSearchResult:
        query = (query or "").strip()
        if not query:
            raise ProviderError("pubmed", "PubMed search query is empty.")

        page_size = max(1, min(int(limit or 10), 100))
        retstart = max(0, (int(page or 1) - 1) * page_size)
        search_payload = self._get_json(
            "esearch.fcgi",
            {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": page_size,
                "retstart": retstart,
                "sort": "pub+date" if lane == RetrievalLane.RECENT else "relevance",
            },
            query,
        )
        result = search_payload.get("esearchresult") or {}
        ids = [str(value) for value in result.get("idlist") or [] if value]
        total = int(result.get("count") or 0)
        if not ids:
            return ProviderSearchResult(metadata=SearchMetadata(total=total, page=max(1, int(page or 1)), limit=page_size), hits=[])

        summary_payload = self._get_json(
            "esummary.fcgi",
            {"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
            query,
        )
        summaries = (summary_payload.get("result") or {})
        abstracts = self._fetch_abstracts(ids, query)
        records = []
        for pmid in ids:
            item = summaries.get(pmid)
            if isinstance(item, dict):
                records.append(self._to_record(pmid, item, abstracts.get(pmid, "")))
        return ProviderSearchResult(metadata=SearchMetadata(total=total, page=max(1, int(page or 1)), limit=page_size), hits=records)

    def _get_json(self, endpoint: str, params: Dict[str, Any], query: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint}"
        params = {**params, **self._common_params()}
        headers = {"Accept": "application/json", "User-Agent": self._user_agent()}
        try:
            response, info = get_with_retries("pubmed", url, params=params, headers=headers, timeout=45, query=query)
            self.last_response_info = info
        except ProviderError as exc:
            self.last_response_info = {"method": "GET", "url": url, "status": "request_error", "elapsed_ms": None}
            raise exc
        if response.status_code >= 400:
            raise ProviderError("pubmed", f"PubMed returned HTTP {response.status_code}.", status=response.status_code, body=response.text[:1000], query=query)
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError("pubmed", "PubMed returned a non-JSON response.", body=response.text[:1000], query=query) from exc

    def _fetch_abstracts(self, pmids: List[str], query: str) -> Dict[str, str]:
        if not pmids:
            return {}
        url = f"{self.BASE_URL}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            **self._common_params(),
        }
        headers = {"Accept": "application/xml", "User-Agent": self._user_agent()}
        try:
            response, info = get_with_retries("pubmed", url, params=params, headers=headers, timeout=45, query=query)
            self.last_response_info = info
        except ProviderError:
            return {}
        if response.status_code >= 400:
            return {}
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            return {}
        abstracts: Dict[str, str] = {}
        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//PMID") or ""
            parts = []
            for node in article.findall(".//Abstract/AbstractText"):
                label = node.attrib.get("Label")
                text = "".join(node.itertext()).strip()
                if text:
                    parts.append(f"{label}: {text}" if label else text)
            if pmid and parts:
                abstracts[pmid] = re.sub(r"\s+", " ", " ".join(parts)).strip()
        return abstracts

    def _common_params(self) -> Dict[str, str]:
        params = {"tool": self.tool}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _user_agent(self) -> str:
        if self.email:
            return f"paperseek/1.0 (mailto:{self.email})"
        return "paperseek/1.0"

    def _to_record(self, pmid: str, item: Dict[str, Any], abstract: str) -> PaperRecord:
        article_ids = item.get("articleids") or []
        doi = ""
        for article_id in article_ids:
            if isinstance(article_id, dict) and str(article_id.get("idtype") or "").lower() == "doi":
                doi = normalize_doi(article_id.get("value") or "")
                break
        authors = []
        for author in item.get("authors") or []:
            if isinstance(author, dict) and author.get("name"):
                authors.append(PaperAuthor(display_name=str(author.get("name") or "")))
        year = self._extract_year(item.get("pubdate") or item.get("epubdate") or "")
        pub_types = [str(value) for value in (item.get("pubtype") or []) if value]
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
        return PaperRecord(
            uid=f"PMID:{pmid}",
            title=item.get("title") or pmid,
            types=pub_types,
            source_types=pub_types,
            source=PaperSource(source_title=item.get("fulljournalname") or item.get("source") or "PubMed", publish_year=year),
            names=PaperNames(authors=authors),
            links=PaperLinks(record=url, landing_page=url),
            identifiers=PaperIdentifiers(doi=doi, pmid=pmid),
            keywords=PaperKeywords(author_keywords=[]),
            abstract=abstract,
            provider="pubmed",
            raw=item,
        )

    @staticmethod
    def _extract_year(value: str) -> Optional[int]:
        match = re.search(r"\b(19|20)\d{2}\b", value or "")
        return int(match.group(0)) if match else None


class PaperHubProvider:
    MANIFEST_URL = "https://raw.githubusercontent.com/Yupu-Wang/paper-hub/main/data/manifest.json"
    RAW_BASE_URL = "https://raw.githubusercontent.com/Yupu-Wang/paper-hub/main/data"
    _lock = threading.Lock()
    _paper_cache: Optional[List[Dict[str, Any]]] = None

    def __init__(self):
        self.last_response_info: Dict[str, Any] = {}

    def retrieval_capabilities(self) -> ProviderRetrievalCapabilities:
        return ProviderRetrievalCapabilities(
            source="paperhub",
            lanes=(RetrievalLane.RELEVANCE, RetrievalLane.RECENT, RetrievalLane.LOCAL_QUALITY),
            max_lane_limit=1000,
        )

    def search(self, query: str, limit: int = 50, page: int = 1, lane: str = RetrievalLane.RELEVANCE) -> ProviderSearchResult:
        query = (query or "").strip()
        if not query:
            raise ProviderError("paperhub", "Paper Hub search query is empty.")
        papers = self._load_papers(query)
        scored = []
        terms = self._terms(query)
        for paper in papers:
            score = self._score(paper, terms)
            if score > 0:
                scored.append((score, paper))
        if lane == RetrievalLane.RECENT:
            scored.sort(key=lambda item: (int(item[1].get("year") or 0), item[0], item[1].get("conference") or ""), reverse=True)
        elif lane == RetrievalLane.LOCAL_QUALITY:
            scored.sort(key=lambda item: (item[0], self._conference_weight(item[1]), int(item[1].get("year") or 0)), reverse=True)
        else:
            scored.sort(key=lambda item: (item[0], int(item[1].get("year") or 0), item[1].get("conference") or ""), reverse=True)
        page_size = max(1, min(int(limit or 10), 100))
        offset = max(0, (int(page or 1) - 1) * page_size)
        selected = [paper for _, paper in scored[offset:offset + page_size]]
        return ProviderSearchResult(
            metadata=SearchMetadata(total=len(scored), page=max(1, int(page or 1)), limit=page_size),
            hits=[self._to_record(paper) for paper in selected],
        )

    def _load_papers(self, query: str) -> List[Dict[str, Any]]:
        if PaperHubProvider._paper_cache is not None:
            return PaperHubProvider._paper_cache
        with PaperHubProvider._lock:
            if PaperHubProvider._paper_cache is not None:
                return PaperHubProvider._paper_cache
            response, info = get_with_retries("paperhub", self.MANIFEST_URL, headers={"Accept": "application/json"}, timeout=45, query=query)
            self.last_response_info = info
            if response.status_code >= 400:
                raise ProviderError("paperhub", f"Paper Hub manifest returned HTTP {response.status_code}.", status=response.status_code, body=response.text[:1000], query=query)
            try:
                manifest = response.json()
            except ValueError as exc:
                raise ProviderError("paperhub", "Paper Hub manifest returned non-JSON content.", body=response.text[:1000], query=query) from exc
            papers: List[Dict[str, Any]] = []
            for shard in manifest.get("shards") or []:
                file_name = shard.get("file") if isinstance(shard, dict) else ""
                if not file_name:
                    continue
                url = f"{self.RAW_BASE_URL}/{file_name}"
                shard_response, shard_info = get_with_retries("paperhub", url, headers={"Accept": "application/json"}, timeout=60, query=query)
                self.last_response_info = shard_info
                if shard_response.status_code >= 400:
                    continue
                try:
                    payload = shard_response.json()
                except ValueError:
                    continue
                for paper in payload.get("papers") or []:
                    if isinstance(paper, dict):
                        papers.append(paper)
            PaperHubProvider._paper_cache = papers
            return papers

    @staticmethod
    def _terms(query: str) -> List[str]:
        terms = re.findall(r"[A-Za-z0-9][A-Za-z0-9_+-]{1,}", query.lower())
        stop = {"and", "or", "not", "the", "with", "for", "from", "paper", "papers", "study", "research"}
        return [term for term in terms if term not in stop][:20]

    def _score(self, paper: Dict[str, Any], terms: List[str]) -> int:
        if not terms:
            return 1
        title = str(paper.get("title") or "").lower()
        abstract = str(paper.get("abstract") or "").lower()
        keywords = " ".join(str(value) for value in (paper.get("keywords") or [])).lower()
        authors = " ".join(str(value) for value in (paper.get("authors") or [])).lower()
        venue = f"{paper.get('conference') or ''} {paper.get('year') or ''} {paper.get('presentation') or ''}".lower()
        score = 0
        for term in terms:
            if term in title:
                score += 8
            if term in keywords:
                score += 5
            if term in abstract:
                score += 3
            if term in authors:
                score += 2
            if term in venue:
                score += 4
        return score

    @staticmethod
    def _conference_weight(paper: Dict[str, Any]) -> int:
        conference = str(paper.get("conference") or "").upper()
        order = {"NEURIPS": 6, "ICML": 5, "ICLR": 5, "AAAI": 4, "NDSS": 4}
        return order.get(conference, 1)

    def _to_record(self, paper: Dict[str, Any]) -> PaperRecord:
        paper_id = str(paper.get("id") or paper.get("url") or paper.get("title") or "")
        conference = str(paper.get("conference") or "")
        year = paper.get("year")
        presentation = str(paper.get("presentation") or "")
        keywords = [str(value) for value in (paper.get("keywords") or []) if value]
        if conference and conference not in keywords:
            keywords.append(conference)
        if presentation and presentation not in keywords:
            keywords.append(presentation)
        authors = [PaperAuthor(display_name=str(name)) for name in (paper.get("authors") or []) if name]
        url = str(paper.get("url") or "")
        return PaperRecord(
            uid=paper_id or url,
            title=str(paper.get("title") or paper_id),
            types=["conference-paper"],
            source_types=[presentation] if presentation else ["conference-paper"],
            source=PaperSource(source_title=conference, publish_year=year),
            names=PaperNames(authors=authors),
            links=PaperLinks(record=url, landing_page=url),
            identifiers=PaperIdentifiers(),
            keywords=PaperKeywords(author_keywords=keywords),
            abstract=str(paper.get("abstract") or ""),
            provider="paperhub",
            raw=paper,
        )
