from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests
import time


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
    semantic_scholar: str = ""


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
                "url": response.url,
                "status": response.status_code,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "attempts": attempt,
            }
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
    raise ProviderError(source, f"{source.title()} request failed after {attempts} attempts: {last_exc}", query=query) from last_exc


class OpenAlexProvider:
    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, api_key: str = "", email: str = ""):
        self.api_key = (api_key or "").strip()
        self.email = (email or "").strip()
        self.last_response_info: Dict[str, Any] = {}

    def search(self, query: str, limit: int = 50, page: int = 1) -> ProviderSearchResult:
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
                "referenced_works",
            ]),
        }
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
    ) -> List[PaperRecord]:
        return self.citation_neighbors_with_graph(seeds, per_seed=per_seed, max_records=max_records)["records"]

    def citation_neighbors_with_graph(
        self,
        seeds: List[PaperRecord],
        per_seed: int = 4,
        max_records: int = 40,
    ) -> Dict[str, Any]:
        """Fetch forward and backward citation neighbors for seed OpenAlex works."""
        per_seed = max(1, min(int(per_seed or 4), 20))
        max_records = max(1, min(int(max_records or 40), 500))
        output: List[PaperRecord] = []
        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, str]] = []
        seen = set()

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

        for seed in seeds or []:
            if len(output) >= max_records:
                break
            seed_id = self._openalex_work_id(seed)
            if not seed_id:
                continue
            seed_uid = seed.uid or (seed.identifiers.openalex if seed.identifiers else "") or seed_id
            add_node(seed, "seed")

            for ref_url in (seed.raw.get("referenced_works") or [])[:per_seed]:
                if len(output) >= max_records:
                    break
                try:
                    record = self._fetch_work(ref_url)
                    if record:
                        add_node(record, "backward", seed_uid)
                        edges.append({
                            "source": seed_uid,
                            "target": record.uid,
                            "type": "references",
                            "seed": seed_uid,
                        })
                    add_record(record)
                except ProviderError:
                    continue

            if len(output) >= max_records:
                break
            try:
                for record in self._fetch_forward_citations(seed_id, per_seed):
                    if len(output) >= max_records:
                        break
                    add_node(record, "forward", seed_uid)
                    edges.append({
                        "source": record.uid,
                        "target": seed_uid,
                        "type": "cites",
                        "seed": seed_uid,
                    })
                    add_record(record)
            except ProviderError:
                continue

        return {"records": output, "nodes": list(nodes.values()), "edges": edges}

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

    def _fetch_forward_citations(self, seed_id: str, limit: int) -> List[PaperRecord]:
        params = self._base_params()
        params.update({
            "filter": f"cites:{seed_id}",
            "sort": "cited_by_count:desc",
            "per-page": max(1, min(int(limit or 4), 20)),
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

    def search(self, query: str, limit: int = 50, page: int = 1) -> ProviderSearchResult:
        query = (query or "").strip()
        if not query:
            raise ProviderError("crossref", "Crossref search query is empty.")

        page_size = max(1, min(int(limit or 10), 100))
        params = {
            "query.bibliographic": query,
            "rows": page_size,
            "offset": max(0, (int(page or 1) - 1) * page_size),
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
