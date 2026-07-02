from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


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

    return PaperResult(
        rank=rank,
        source=provider,
        id=first_non_empty(safe_get(doc, "uid"), getattr(identifiers, "openalex", "") if identifiers else "", doi),
        title=first_non_empty(safe_get(doc, "title"), "(no title)"),
        authors=authors_from_doc(doc),
        year=getattr(source, "publish_year", None) if source else None,
        venue=getattr(source, "source_title", "") if source else "",
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
