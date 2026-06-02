import json
from typing import List

from paperseek.results import ranked_items_to_results


def _safe_get(doc, attr, default=""):
    try:
        val = getattr(doc, attr, None)
        return val if val is not None else default
    except Exception:
        return default


def _format_authors(doc) -> str:
    names = _safe_get(doc, "names")
    if not names:
        return ""
    authors = getattr(names, "authors", None) or []
    return ", ".join(
        a.display_name or a.wos_standard or ""
        for a in authors[:5]
        if a
    )


def _format_source(doc) -> str:
    source = _safe_get(doc, "source")
    if not source:
        return ""
    parts = [
        getattr(source, "source_title", "") or "",
    ]
    year = getattr(source, "publish_year", None)
    vol = getattr(source, "volume", None)
    issue = getattr(source, "issue", None)
    if year:
        parts.append(f"({year})")
    if vol:
        parts.append(f" {vol}")
    if issue:
        parts.append(f"({issue})")
    pages_obj = getattr(source, "pages", None)
    if pages_obj:
        pr = getattr(pages_obj, "range", None)
        if pr:
            parts.append(f":{pr}")
    return "".join(str(p) for p in parts if p)


def _format_citations(doc) -> str:
    citations = _safe_get(doc, "citations")
    if isinstance(citations, list) and citations:
        total = 0
        for c in citations:
            total += getattr(c, "count", 0) or 0
        if total:
            return str(total)
    return ""


def _format_keywords(doc) -> str:
    kw = _safe_get(doc, "keywords")
    if not kw:
        return ""
    author_kw = getattr(kw, "author_keywords", None) or []
    if author_kw:
        return "; ".join(author_kw[:8])
    return ""


def ranked_items_to_dict(items: list) -> list:
    """Convert ranked document entries into stable JSON metadata.

    The response intentionally keeps older UI-facing fields such as ``score``
    and ``publish_year`` while adding normalized names such as
    ``relevance_score`` and ``citation_count`` for scripts and agents.
    """
    output = []
    for result in ranked_items_to_results(items):
        row = result.to_dict()
        row.update({
            "score": result.relevance_score,
            "provider": result.source,
            "uid": result.source_raw_id or result.id,
            "source": result.venue,
            "publish_year": result.year,
            "document_types": [result.publication_type] if result.publication_type else [],
            "keywords": "; ".join(result.keywords),
            "citations": str(result.citation_count) if result.citation_count else "",
            "reasoning": result.relevance_reason,
            "pdf_url": result.pdf_url,
        })
        output.append(row)
    return output


def format_text(items: list, question: str, final_query: str, db: str,
                total_count: int, iterations: int, field_name: str = "",
                verbose: bool = False) -> str:
    separator = "=" * 80
    lines = [separator]
    lines.append(f"  Search: \"{question}\"")
    if field_name:
        lines.append(f"  Field:  {field_name} | Database: {db}")
    else:
        lines.append(f"  Database: {db}")
    lines.append(f"  Query:  {final_query}")
    lines.append(f"  Found:  {total_count} total | {len(items)} ranked ({iterations} iteration{'s' if iterations > 1 else ''})")
    lines.append(separator)
    lines.append("")

    for i, ranked in enumerate(items, 1):
        doc = ranked["document"]
        scoring = ranked.get("score", "?")
        rationale = ranked.get("reasoning", "")

        title = _safe_get(doc, "title") or "(no title)"
        authors = _format_authors(doc)
        source = _format_source(doc)
        doi = ""
        identifiers = _safe_get(doc, "identifiers")
        if identifiers:
            doi = getattr(identifiers, "doi", "") or ""
        cit = _format_citations(doc)

        lines.append(f"{i}. [{scoring}/10] {title}")
        if authors:
            lines.append(f"   {authors}")
        if source:
            lines.append(f"   {source}")
        meta_parts = []
        if doi:
            meta_parts.append(f"DOI: {doi}")
        if cit:
            meta_parts.append(f"Cited: {cit}")
        if meta_parts:
            lines.append(f"   {' | '.join(meta_parts)}")

        abstract = ranked.get("abstract", "") or _safe_get(doc, "abstract")
        if abstract:
            abbr = abstract[:500] + ("..." if len(abstract) > 500 else "")
            lines.append(f"   Abstract: {abbr}")

        if rationale:
            lines.append(f"   -> {rationale}")
        lines.append("")

    return "\n".join(lines)


def format_json(items: list, question: str, final_query: str, db: str,
                total_count: int, iterations: int, field_name: str = "",
                history: list = None, source: str = "") -> str:
    output = {
        "question": question,
        "source": source or None,
        "query": final_query,
        "database": db,
        "field": field_name or None,
        "total_results": total_count,
        "iterations": iterations,
        "history": history or [],
        "ranked": ranked_items_to_dict(items)
    }
    return json.dumps(output, ensure_ascii=False, indent=2)
