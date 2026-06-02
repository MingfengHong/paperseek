from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class SourceMetadata:
    id: str
    display_name: str
    status: str
    description: str
    api_key: str
    default: bool = False
    supports_abstracts: bool = False
    supports_citations: bool = False
    supports_citation_expansion: bool = False
    supports_pdf_links: bool = False
    supported_parameters: List[str] = field(default_factory=list)
    required_config: List[str] = field(default_factory=list)
    optional_config: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


SOURCE_METADATA: Dict[str, SourceMetadata] = {
    "openalex": SourceMetadata(
        id="openalex",
        display_name="OpenAlex",
        status="default",
        description="Open scholarly metadata source for broad discovery, citation counts, abstracts when available, and citation graph traversal.",
        api_key="recommended",
        default=True,
        supports_abstracts=True,
        supports_citations=True,
        supports_citation_expansion=True,
        supports_pdf_links=True,
        supported_parameters=[
            "openalex_api_key",
            "openalex_email",
            "search_field",
            "target_min",
            "target_max",
            "max_iterations",
            "expand_citations",
        ],
        optional_config=["OPENALEX_API_KEY", "OPENALEX_EMAIL"],
        notes=[
            "Use an OpenAlex API key for normal or high-frequency work.",
            "Citation expansion uses extra OpenAlex requests and should be rate-aware.",
        ],
    ),
    "crossref": SourceMetadata(
        id="crossref",
        display_name="Crossref",
        status="supported",
        description="Publisher DOI and bibliographic metadata registry; useful for DOI/title verification and broad metadata lookup.",
        api_key="not_required",
        supports_abstracts=True,
        supports_citations=True,
        supports_citation_expansion=False,
        supports_pdf_links=False,
        supported_parameters=[
            "crossref_email",
            "search_field",
            "target_min",
            "target_max",
            "max_iterations",
        ],
        optional_config=["CROSSREF_EMAIL"],
        notes=[
            "Crossref abstracts are optional publisher metadata and are often missing.",
            "Use a mailto email for Crossref polite-pool requests.",
        ],
    ),
    "wos": SourceMetadata(
        id="wos",
        display_name="Web of Science Starter",
        status="temporarily_unavailable",
        description="Clarivate Web of Science Starter API adapter for users with approved API access.",
        api_key="required",
        supports_abstracts=False,
        supports_citations=True,
        supports_citation_expansion=False,
        supports_pdf_links=False,
        supported_parameters=[
            "wos_api_key",
            "wos_db",
            "search_field",
            "target_min",
            "target_max",
            "max_iterations",
            "fetch_abstracts",
        ],
        required_config=["WOS_API_KEY"],
        notes=[
            "WoS Starter returns basic bibliographic metadata and links; do not rely on native abstract fields.",
            "Availability depends on Clarivate API entitlement and upstream service status.",
        ],
    ),
}


def get_source_metadata(source: str) -> Optional[SourceMetadata]:
    return SOURCE_METADATA.get((source or "").strip().lower())


def require_source_metadata(source: str) -> SourceMetadata:
    metadata = get_source_metadata(source)
    if not metadata:
        supported = ", ".join(SOURCE_METADATA)
        raise ValueError(f"Unsupported data source '{source}'. Supported sources: {supported}.")
    return metadata


def list_source_metadata() -> List[Dict[str, object]]:
    return [SOURCE_METADATA[key].to_dict() for key in ("openalex", "crossref", "wos")]


def supported_source_ids() -> tuple:
    return tuple(SOURCE_METADATA.keys())
