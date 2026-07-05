from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
import time
from typing import Any, Dict, List, Optional, Tuple


def safe_get(obj: Any, attr: str, default: Any = "") -> Any:
    try:
        value = getattr(obj, attr, None)
        return value if value is not None else default
    except Exception:
        return default


def first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def citation_count(doc: Any) -> int:
    total = 0
    for citation in safe_get(doc, "citations", []) or []:
        try:
            total += int(getattr(citation, "count", 0) or 0)
        except (TypeError, ValueError):
            continue
    return total


def authors_from_doc(doc: Any) -> List[str]:
    names = safe_get(doc, "names")
    output: List[str] = []
    for author in (getattr(names, "authors", None) or []) if names else []:
        if not author:
            continue
        name = first_non_empty(getattr(author, "display_name", ""), getattr(author, "wos_standard", ""))
        if name:
            output.append(name)
    return output


def links_from_doc(doc: Any) -> Dict[str, str]:
    links = safe_get(doc, "links")
    if not links:
        return {"record": "", "landing_page": "", "pdf": "", "citing_articles": "", "references": "", "related": ""}
    return {
        "record": getattr(links, "record", "") or "",
        "landing_page": getattr(links, "landing_page", "") or "",
        "pdf": getattr(links, "pdf", "") or "",
        "citing_articles": getattr(links, "citing_articles", "") or "",
        "references": getattr(links, "references", "") or "",
        "related": getattr(links, "related", "") or "",
    }


def keywords_from_doc(doc: Any) -> List[str]:
    keywords = safe_get(doc, "keywords")
    if not keywords:
        return []
    return [str(item) for item in (getattr(keywords, "author_keywords", None) or []) if item]


def source_type_from_doc(doc: Any) -> str:
    values = safe_get(doc, "types", []) or safe_get(doc, "source_types", []) or []
    if isinstance(values, list) and values:
        return str(values[0] or "")
    return ""


def plausible_year(value: Any) -> Optional[int]:
    current_year = time.gmtime().tm_year + 2
    try:
        if value not in (None, ""):
            year = int(value)
            if 1500 <= year <= current_year:
                return year
    except (TypeError, ValueError):
        pass
    text = str(value or "")
    for match in re.finditer(r"\b(?:1[5-9]\d{2}|20\d{2})\b", text):
        year = int(match.group(0))
        if year <= current_year:
            return year
    return None


def clean_google_scholar_fragment(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()
    text = text.replace("\u0431\u043d", "...")
    text = re.sub(r"\b(?:1[5-9]\d{2}|20\d{2})\b", "", text)
    text = re.sub(r"\bAvailable at\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bSSRN\s+\d+\b", "SSRN", text, flags=re.IGNORECASE)
    text = text.replace("...", " ")
    return re.sub(r"\s+", " ", text).strip(" ,;:-")


def google_scholar_summary_parts(value: Any) -> List[str]:
    return [clean_google_scholar_fragment(part) for part in re.split(r"\s+-\s+", str(value or "")) if clean_google_scholar_fragment(part)]


def author_names_from_google_scholar_summary(value: Any) -> List[str]:
    parts = google_scholar_summary_parts(value)
    if len(parts) < 2 or plausible_year(parts[0]):
        return []
    authors = []
    for part in re.split(r"\s*,\s*|;\s*", parts[0]):
        name = clean_google_scholar_fragment(part)
        if not name or plausible_year(name):
            continue
        if re.search(r"://|www\.|\.com\b|\.org\b|\.net\b|\.edu\b", name, flags=re.IGNORECASE):
            continue
        authors.append(name)
    return authors


def venue_from_google_scholar_summary(value: Any) -> str:
    parts = google_scholar_summary_parts(value)
    for part in parts[1:]:
        if part and not plausible_year(part):
            return part
    return ""


def normalize_google_scholar_metadata(provider: str, authors: List[str], year: Optional[int], venue: str) -> Tuple[List[str], Optional[int], str]:
    if provider != "googlescholar":
        return authors, year, venue
    normalized_year = plausible_year(year) or plausible_year(venue)
    normalized_authors = authors or author_names_from_google_scholar_summary(venue)
    normalized_venue = venue_from_google_scholar_summary(venue) if " - " in str(venue or "") else clean_google_scholar_fragment(venue)
    return normalized_authors, normalized_year, normalized_venue or "Google Scholar"


@dataclass
class PaperResult:
    rank: int
    source: str
    id: str
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    venue: str = ""
    publication_type: str = ""
    doi: str = ""
    url: str = ""
    pdf_url: str = ""
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    citation_count: int = 0
    relevance_score: Optional[float] = None
    relevance_reason: str = ""
    source_rank: Optional[int] = None
    retrieval_score: Optional[float] = None
    retrieval_lanes: List[str] = field(default_factory=list)
    source_raw_id: str = ""
    links: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["keywords_text"] = "; ".join(self.keywords)
        data["authors_text"] = "; ".join(self.authors)
        return data


def ranked_entry_to_result(entry: Dict[str, Any], rank: int) -> PaperResult:
    doc = entry.get("document")
    source = safe_get(doc, "source")
    identifiers = safe_get(doc, "identifiers")
    links = links_from_doc(doc)
    provider = first_non_empty(safe_get(doc, "provider"), entry.get("provider"))
    doi = getattr(identifiers, "doi", "") if identifiers else ""
    url = first_non_empty(links.get("record"), links.get("landing_page"), f"https://doi.org/{doi}" if doi else "")
    score = entry.get("score")
    try:
        score_value: Optional[float] = float(score) if score is not None and score != "" else None
    except (TypeError, ValueError):
        score_value = None
    authors = authors_from_doc(doc)
    year = getattr(source, "publish_year", None) if source else None
    venue = getattr(source, "source_title", "") if source else ""
    authors, year, venue = normalize_google_scholar_metadata(provider, authors, year, venue)

    return PaperResult(
        rank=rank,
        source=provider,
        id=first_non_empty(safe_get(doc, "uid"), getattr(identifiers, "openalex", "") if identifiers else "", doi),
        title=first_non_empty(safe_get(doc, "title"), "(no title)"),
        authors=authors,
        year=year,
        venue=venue,
        publication_type=source_type_from_doc(doc),
        doi=doi or "",
        url=url,
        pdf_url=links.get("pdf", ""),
        abstract=entry.get("abstract", "") or safe_get(doc, "abstract", ""),
        keywords=keywords_from_doc(doc),
        citation_count=citation_count(doc),
        relevance_score=score_value,
        relevance_reason=entry.get("reasoning", "") or "",
        source_rank=entry.get("source_rank"),
        retrieval_score=entry.get("retrieval_score"),
        retrieval_lanes=[str(value) for value in (entry.get("retrieval_lanes") or []) if value],
        source_raw_id=safe_get(doc, "uid"),
        links=links,
    )


def ranked_items_to_results(items: List[Dict[str, Any]]) -> List[PaperResult]:
    return [ranked_entry_to_result(entry, index) for index, entry in enumerate(items or [], 1)]


def ranked_items_to_dict(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [result.to_dict() for result in ranked_items_to_results(items)]
