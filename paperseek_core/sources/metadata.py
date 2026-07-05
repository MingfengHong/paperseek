from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


RETRIEVAL_PARAMETERS = [
    "retrieval_pool_max",
    "retrieval_pool_min",
    "retrieval_lane_limit",
    "retrieval_rrf_k",
    "retrieval_embedding_provider",
    "retrieval_crossref_enrichment",
]


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
            "discipline_fields",
            "target_min",
            "target_max",
            "max_iterations",
            "expand_citations",
        ] + RETRIEVAL_PARAMETERS,
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
        ] + RETRIEVAL_PARAMETERS,
        optional_config=["CROSSREF_EMAIL"],
        notes=[
            "Crossref abstracts are optional publisher metadata and are often missing.",
            "Use a mailto email for Crossref polite-pool requests.",
            "Field/context hints are used only as bibliographic search context.",
        ],
    ),
    "arxiv": SourceMetadata(
        id="arxiv",
        display_name="arXiv",
        status="supported",
        description="Open preprint repository API for physics, mathematics, computer science, quantitative biology, statistics, electrical engineering, and economics.",
        api_key="not_required",
        supports_abstracts=True,
        supports_citations=False,
        supports_citation_expansion=False,
        supports_pdf_links=True,
        supported_parameters=[
            "search_field",
            "discipline_fields",
            "target_min",
            "target_max",
            "max_iterations",
        ] + RETRIEVAL_PARAMETERS,
        notes=[
            "Uses the public arXiv API Atom feed.",
            "arXiv category filters use native cat: clauses.",
            "Best for preprints and computer science / quantitative fields covered by arXiv.",
        ],
    ),
    "semanticscholar": SourceMetadata(
        id="semanticscholar",
        display_name="Semantic Scholar",
        status="supported",
        description="Semantic Scholar Academic Graph search with title, abstract, author, venue, citation count, DOI, PubMed, and arXiv identifiers when available.",
        api_key="optional",
        supports_abstracts=True,
        supports_citations=True,
        supports_citation_expansion=False,
        supports_pdf_links=True,
        supported_parameters=[
            "semantic_scholar_api_key",
            "search_field",
            "target_min",
            "target_max",
            "max_iterations",
        ] + RETRIEVAL_PARAMETERS,
        optional_config=["SEMANTIC_SCHOLAR_API_KEY"],
        notes=[
            "Anonymous access works for light use; an API key improves rate limits.",
            "Field/context hints are used only to help the LLM choose better query terms.",
        ],
    ),
    "pubmed": SourceMetadata(
        id="pubmed",
        display_name="PubMed",
        status="supported",
        description="PubMed biomedical literature search through NCBI E-utilities with PMID, journal, author, publication type, DOI, and abstract extraction when available.",
        api_key="optional",
        supports_abstracts=True,
        supports_citations=False,
        supports_citation_expansion=False,
        supports_pdf_links=False,
        supported_parameters=[
            "pubmed_api_key",
            "pubmed_email",
            "pubmed_tool",
            "search_field",
            "target_min",
            "target_max",
            "max_iterations",
        ] + RETRIEVAL_PARAMETERS,
        optional_config=["PUBMED_API_KEY", "PUBMED_EMAIL", "PUBMED_TOOL"],
        notes=[
            "NCBI recommends identifying the tool and email for responsible E-utilities usage.",
            "An NCBI API key increases allowed request rate.",
            "Biomedical field/context hints are used only to help the LLM choose PubMed terms.",
        ],
    ),
    "googlescholar": SourceMetadata(
        id="googlescholar",
        display_name="Google Scholar (Serper)",
        status="supported",
        description="Google Scholar results accessed through Serper's /scholar API, useful for broad discovery across scholarly pages and citation metadata exposed by Google Scholar.",
        api_key="required",
        supports_abstracts=True,
        supports_citations=True,
        supports_citation_expansion=False,
        supports_pdf_links=True,
        supported_parameters=[
            "serper_api_key",
            "search_field",
            "target_min",
            "target_max",
            "max_iterations",
        ] + RETRIEVAL_PARAMETERS,
        required_config=["SERPER_API_KEY"],
        optional_config=["SERPER_API_KEYS"],
        notes=[
            "Uses Serper's Google Scholar endpoint and requires a Serper API key.",
            "SERPER_API_KEYS can contain multiple keys separated by commas, semicolons, spaces, or newlines; PaperSeek rotates them across requests.",
            "Field/context hints are used only to help the LLM choose better Google Scholar terms.",
        ],
    ),
    "paperhub": SourceMetadata(
        id="paperhub",
        display_name="Computer science top conferences",
        status="supported",
        description="Computer science top-conference paper index, currently covering selected ICLR, ICML, NeurIPS, AAAI, and NDSS proceedings.",
        api_key="not_required",
        supports_abstracts=True,
        supports_citations=False,
        supports_citation_expansion=False,
        supports_pdf_links=False,
        supported_parameters=[
            "search_field",
            "target_min",
            "target_max",
            "max_iterations",
        ] + RETRIEVAL_PARAMETERS,
        notes=[
            "Downloads and caches computer science top-conference index shards at runtime.",
            "Best for top ML/security conference discovery rather than exhaustive bibliographic coverage.",
            "Computer-science field/context hints are used only to help the LLM choose better query terms.",
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
            "discipline_fields",
            "target_min",
            "target_max",
            "max_iterations",
            "fetch_abstracts",
        ] + RETRIEVAL_PARAMETERS,
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
    return [
        SOURCE_METADATA[key].to_dict()
        for key in ("openalex", "arxiv", "semanticscholar", "pubmed", "googlescholar", "paperhub", "crossref", "wos")
    ]


def supported_source_ids() -> tuple:
    return tuple(SOURCE_METADATA.keys())
