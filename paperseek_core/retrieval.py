from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import blake2b
import math
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


class RetrievalLane:
    RELEVANCE = "relevance"
    IMPACT = "impact"
    RECENT = "recent"
    LOCAL_QUALITY = "local_quality"


@dataclass(frozen=True)
class ProviderRetrievalCapabilities:
    source: str
    lanes: Tuple[str, ...] = (RetrievalLane.RELEVANCE,)
    max_lane_limit: int = 1000

    def supports(self, lane: str) -> bool:
        return lane in self.lanes


@dataclass
class FusedRetrievalResult:
    documents: List[Any]
    metadata_by_key: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    lane_counts: Dict[str, int] = field(default_factory=dict)
    total_candidates: int = 0


LANE_WEIGHTS = {
    RetrievalLane.RELEVANCE: 1.0,
    RetrievalLane.IMPACT: 0.9,
    RetrievalLane.RECENT: 0.8,
    RetrievalLane.LOCAL_QUALITY: 0.9,
}

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+\-.]{1,}", re.I)
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "paper",
    "papers",
    "research",
    "study",
    "studies",
    "the",
    "to",
    "with",
}


def document_key(document: Any) -> str:
    identifiers = getattr(document, "identifiers", None)
    for attr in ("doi", "openalex", "arxiv", "semanticscholar", "pmid"):
        value = getattr(identifiers, attr, "") if identifiers is not None else ""
        normalized = _normalize_key(value)
        if normalized:
            return f"{attr}:{normalized}"
    uid = _normalize_key(getattr(document, "uid", ""))
    if uid:
        return f"uid:{uid}"
    title = _normalize_title(getattr(document, "title", ""))
    return f"title:{title}" if title else ""


def document_text(document: Any) -> str:
    parts: List[str] = []
    for value in (
        getattr(document, "title", ""),
        getattr(document, "abstract", ""),
    ):
        if value:
            parts.append(str(value))
    source = getattr(document, "source", None)
    if source is not None:
        for value in (getattr(source, "source_title", ""), getattr(source, "publish_year", "")):
            if value:
                parts.append(str(value))
    keywords = getattr(document, "keywords", None)
    if keywords is not None:
        parts.extend(str(value) for value in getattr(keywords, "author_keywords", []) or [] if value)
    names = getattr(document, "names", None)
    if names is not None:
        for author in getattr(names, "authors", []) or []:
            name = getattr(author, "display_name", "") or getattr(author, "wos_standard", "")
            if name:
                parts.append(str(name))
    parts.extend(str(value) for value in getattr(document, "types", []) or [] if value)
    return " ".join(parts)


def fuse_candidates_rrf(
    query: str,
    lane_results: Mapping[str, Sequence[Any]],
    *,
    pool_max: int = 3000,
    rrf_k: int = 60,
    embedding_scores_by_key: Optional[Mapping[str, float]] = None,
) -> FusedRetrievalResult:
    pool_max = max(1, int(pool_max or 3000))
    rrf_k = max(1, int(rrf_k or 60))
    key_to_doc: Dict[str, Any] = {}
    lane_ranks: Dict[str, Dict[str, int]] = {}

    for lane, documents in lane_results.items():
        seen_in_lane = set()
        ranks: Dict[str, int] = {}
        for document in documents or []:
            key = document_key(document)
            if not key or key in seen_in_lane:
                continue
            seen_in_lane.add(key)
            key_to_doc.setdefault(key, document)
            ranks[key] = len(ranks) + 1
        lane_ranks[lane] = ranks

    if not key_to_doc:
        return FusedRetrievalResult(documents=[], lane_counts={lane: 0 for lane in lane_results})

    keys = list(key_to_doc)
    documents = [key_to_doc[key] for key in keys]
    texts = [document_text(document) for document in documents]
    bm25 = _bm25_scores(query, texts)
    query_vector = _hashed_vector(query)
    if embedding_scores_by_key:
        cosine = [max(0.0, min(1.0, float(embedding_scores_by_key.get(key, 0.0) or 0.0))) for key in keys]
    else:
        cosine = [_cosine(query_vector, _hashed_vector(text)) for text in texts]
    coverage = [_term_coverage(query, text) for text in texts]
    bm25_norm = _normalize_scores(bm25)

    scored = []
    metadata_by_key: Dict[str, Dict[str, Any]] = {}
    for index, key in enumerate(keys):
        rrf_score = 0.0
        lanes = []
        source_rank = None
        for lane, ranks in lane_ranks.items():
            rank = ranks.get(key)
            if rank is None:
                continue
            lanes.append(lane)
            source_rank = rank if source_rank is None else min(source_rank, rank)
            rrf_score += LANE_WEIGHTS.get(lane, 0.8) / (rrf_k + rank)
        final_score = rrf_score + (0.35 * cosine[index]) + (0.35 * bm25_norm[index]) + (0.20 * coverage[index])
        metadata = {
            "source_rank": source_rank or index + 1,
            "retrieval_score": round(final_score, 6),
            "retrieval_lanes": lanes,
            "retrieval_rrf_score": round(rrf_score, 6),
            "retrieval_embedding_score": round(cosine[index], 6),
            "retrieval_bm25_score": round(bm25_norm[index], 6),
            "retrieval_term_coverage": round(coverage[index], 6),
        }
        metadata_by_key[key] = metadata
        scored.append((final_score, -(source_rank or index + 1), key))

    scored.sort(reverse=True)
    selected_keys = [key for _, _, key in scored[:pool_max]]
    return FusedRetrievalResult(
        documents=[key_to_doc[key] for key in selected_keys],
        metadata_by_key={key: metadata_by_key[key] for key in selected_keys},
        lane_counts={lane: len(ranks) for lane, ranks in lane_ranks.items()},
        total_candidates=len(key_to_doc),
    )


def _normalize_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return re.sub(r"\s+", "", text)


def _normalize_title(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _tokens(text: str) -> List[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text or "") if token.lower() not in _STOPWORDS]


def _hashed_vector(text: str, dimensions: int = 512) -> Dict[int, float]:
    tokens = _tokens(text)
    features: Iterable[str] = tokens
    char_features = []
    compact = re.sub(r"\s+", " ", (text or "").lower())
    if len(compact) >= 3:
        char_features = [compact[index:index + 3] for index in range(0, min(len(compact) - 2, 600))]
    vector: Dict[int, float] = {}
    for feature in list(features) + char_features:
        digest = blake2b(feature.encode("utf-8", errors="ignore"), digest_size=8).digest()
        slot = int.from_bytes(digest[:4], "little") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[slot] = vector.get(slot, 0.0) + sign
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm <= 0:
        return {}
    return {key: value / norm for key, value in vector.items()}


def _cosine(left: Dict[int, float], right: Dict[int, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    score = sum(value * right.get(key, 0.0) for key, value in left.items())
    return max(0.0, min(1.0, score))


def _bm25_scores(query: str, documents: Sequence[str]) -> List[float]:
    query_terms = _tokens(query)
    if not query_terms or not documents:
        return [0.0 for _ in documents]
    doc_tokens = [_tokens(document) for document in documents]
    doc_count = len(doc_tokens)
    avg_len = sum(len(tokens) for tokens in doc_tokens) / max(1, doc_count)
    doc_freq: Dict[str, int] = {}
    for tokens in doc_tokens:
        for token in set(tokens):
            doc_freq[token] = doc_freq.get(token, 0) + 1

    scores = []
    k1 = 1.5
    b = 0.75
    for tokens in doc_tokens:
        term_freq: Dict[str, int] = {}
        for token in tokens:
            term_freq[token] = term_freq.get(token, 0) + 1
        doc_len = len(tokens)
        score = 0.0
        for term in query_terms:
            tf = term_freq.get(term, 0)
            if tf <= 0:
                continue
            df = doc_freq.get(term, 0)
            idf = math.log(1 + ((doc_count - df + 0.5) / (df + 0.5)))
            denom = tf + k1 * (1 - b + b * doc_len / max(avg_len, 1.0))
            score += idf * ((tf * (k1 + 1)) / max(denom, 1e-9))
        scores.append(score)
    return scores


def _term_coverage(query: str, document: str) -> float:
    query_terms = set(_tokens(query))
    if not query_terms:
        return 0.0
    document_terms = set(_tokens(document))
    return len(query_terms & document_terms) / max(1, len(query_terms))


def _normalize_scores(scores: Sequence[float]) -> List[float]:
    if not scores:
        return []
    high = max(scores)
    low = min(scores)
    if high <= low:
        return [1.0 if high > 0 else 0.0 for _ in scores]
    return [(score - low) / (high - low) for score in scores]
