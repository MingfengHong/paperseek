import re
import json
import sys
from typing import Any, Callable, List, Optional

from paperseek.client import Configuration, ApiClient, DocumentsApi
from paperseek.client import ApiException
from paperseek.llm_client import LLMClient, LLMError
from paperseek.prompts import (
    SYSTEM_QUERY_GENERATION,
    SYSTEM_QUERY_BROADEN,
    SYSTEM_QUERY_NARROW,
    SYSTEM_OPENALEX_QUERY_GENERATION,
    SYSTEM_OPENALEX_QUERY_BROADEN,
    SYSTEM_OPENALEX_QUERY_NARROW,
    SYSTEM_CROSSREF_QUERY_GENERATION,
    SYSTEM_CROSSREF_QUERY_BROADEN,
    SYSTEM_CROSSREF_QUERY_NARROW,
    SYSTEM_RESULT_RANKING,
)
from paperseek.abstract_fetcher import AbstractFetcher
from paperseek.providers import CrossrefProvider, OpenAlexProvider, ProviderError


def _extract_query(text: str) -> str:
    """Extract a WoS query string from LLM output, stripping markdown and chatty text."""
    text = text.strip()
    for pfx in ("```", "```text", "```plain"):
        if text.lower().startswith(pfx):
            text = text[len(pfx):]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if re.search(r"[A-Z]{2,3}\s*=", line):
            return line
        if "TS=" in line or "TI=" in line or "AU=" in line or "PY=" in line:
            return line
        if re.match(r"^\([^)]+\)", line):
            return line
    return text.split("\n")[0].strip()


def _extract_openalex_query(text: str) -> str:
    query = _extract_query(text)
    query = re.sub(r"^\s*search\s*=\s*", "", query, flags=re.IGNORECASE).strip()
    query = re.sub(r"^\s*q\s*=\s*", "", query, flags=re.IGNORECASE).strip()
    return query.strip().strip("`")


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


class WosSearchAgent:
    def __init__(self, config, llm_client: LLMClient, abstract_fetcher: Optional[AbstractFetcher] = None):
        self.config = config
        self.llm = llm_client
        self.abstract_fetcher = abstract_fetcher or AbstractFetcher()
        self.data_source = (getattr(config, "data_source", "wos") or "wos").lower()
        self.event_handler: Optional[Callable[[dict], None]] = None
        self.citation_map: dict = self._empty_citation_map(enabled=getattr(config, "expand_citations", True))

        self.documents_api = None
        self.provider = None
        if self.data_source == "openalex":
            self.provider = OpenAlexProvider(
                api_key=getattr(config, "openalex_api_key", ""),
                email=getattr(config, "openalex_email", ""),
            )
        elif self.data_source == "crossref":
            self.provider = CrossrefProvider(email=getattr(config, "crossref_email", ""))
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
        query = self._generate_query(question)
        history = []
        iteration = 0
        total = 0
        hits = []

        for iteration in range(1, self.config.max_iterations + 1):
            safe_query = _make_starter_safe_query(query) if self.data_source == "wos" else query
            if self.data_source == "wos" and safe_query != query:
                row = {
                    "iteration": iteration,
                    "query": query,
                    "total": None,
                    "action": "sanitize",
                    "next_query": safe_query,
                    "message": "Converted the generated query to the stable WoS Starter subset before calling the API.",
                }
                history.append(row)
                self._emit_stage("search", "processing", history=history, final_query=safe_query)
                query = safe_query

            if verbose:
                print(f"[Iteration {iteration}] Query: {query}", file=sys.stderr)

            server_error_variants = _server_error_query_variants(query)
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
                    query = self._broaden_query(question, query)
                    row = {
                        "iteration": iteration,
                        "query": current_query,
                        "total": None,
                        "action": "broaden",
                        "next_query": query,
                        "message": "WoS rejected the query syntax; generated a broader replacement query.",
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

            if total == 0 and iteration < self.config.max_iterations:
                current_query = query
                query = self._broaden_query(question, query)
                row = {
                    "iteration": iteration,
                    "query": current_query,
                    "total": total,
                    "action": "broaden",
                    "next_query": query,
                    "message": "No records found; generated a broader query.",
                }
                history.append(row)
                self._emit_stage("search", "processing", total=total, history=history, final_query=query, preview=self._preview_hits(hits))
                continue
            elif total < self.config.target_min and iteration < self.config.max_iterations:
                current_query = query
                query = self._broaden_query(question, query)
                row = {
                    "iteration": iteration,
                    "query": current_query,
                    "total": total,
                    "action": "broaden",
                    "next_query": query,
                    "message": f"Only {total} records found, below the target minimum of {self.config.target_min}; generated a broader query.",
                }
                history.append(row)
                self._emit_stage("search", "processing", total=total, history=history, final_query=query, preview=self._preview_hits(hits))
                continue
            elif total > self.config.target_max and iteration < self.config.max_iterations:
                current_query = query
                query = self._narrow_query(question, query)
                row = {
                    "iteration": iteration,
                    "query": current_query,
                    "total": total,
                    "action": "narrow",
                    "next_query": query,
                    "message": f"{total} records found, above the target maximum of {self.config.target_max}; generated a narrower query.",
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
                elif total > self.config.target_max:
                    action = "accept_high"
                    message = f"Accepted {total} records at the iteration limit, above the target maximum of {self.config.target_max}."
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

        if iteration > self.config.max_iterations or (not hits and total == 0):
            if verbose:
                print(f"[Done] {total} total results after {self.config.max_iterations} iterations.", file=sys.stderr)

        candidates = self._prepare_candidates(question, hits)
        self._emit_stage("ranking", "processing", candidate_count=len(candidates))
        ranked = self._rank_results(question, candidates)[: self.config.target_max]
        self._finalize_citation_map(ranked)
        self._emit_stage("ranking", "complete", ranked_count=len(ranked))

        if self.config.fetch_abstracts:
            self._emit_log("External abstract enrichment started.")
            ranked = self._enrich_with_abstracts(ranked)
            self._emit_log("External abstract enrichment completed.")

        self._emit_stage("results", "complete", ranked_count=len(ranked), total=total)

        return {
            "question": question,
            "final_query": query,
            "db": self.config.wos_db if self.data_source == "wos" else self.data_source.upper(),
            "source": self.data_source,
            "field": self.config.search_field,
            "total": total,
            "iterations": iteration,
            "history": history,
            "citation_map": self.citation_map,
            "ranked": ranked,
        }

    def _provider_search(self, query: str):
        if self.data_source in ("openalex", "crossref"):
            return self.provider.search(query=query, limit=self._candidate_limit())
        return self.documents_api.documents_get(
            q=query,
            db=self.config.wos_db,
            limit=self._candidate_limit(),
        )

    def _candidate_limit(self) -> int:
        output_limit = max(1, min(int(self.config.target_max or 50), 50))
        if self.data_source == "wos":
            return output_limit
        return min(max(output_limit * 2, output_limit), 100)

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
        seed_ranked = self._rank_results(question, candidates)
        seed_limit = max(1, int(getattr(self.config, "citation_seed_count", 3) or 3))
        seeds = [
            entry["document"]
            for entry in seed_ranked
            if entry.get("document") is not None and float(entry.get("score") or 0) >= 7
        ][:seed_limit]
        if len(seeds) < seed_limit:
            for entry in seed_ranked:
                doc = entry.get("document")
                if doc is not None and doc not in seeds:
                    seeds.append(doc)
                if len(seeds) >= seed_limit:
                    break
        if not seeds:
            self._emit_log("Citation expansion skipped: no seed papers available.")
            self.citation_map.update({"status": "no_seeds"})
            return candidates

        try:
            citation_data = self.provider.citation_neighbors_with_graph(
                seeds,
                per_seed=getattr(self.config, "citation_per_seed", 4),
                max_records=getattr(self.config, "citation_max_records", 40),
            )
        except ProviderError as exc:
            self._emit_log(f"Citation expansion skipped after OpenAlex error: {exc}")
            self.citation_map.update({"status": "error", "error": str(exc)})
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
            "added_candidates": added,
            "candidate_pool": len(candidates),
            "nodes": citation_data.get("nodes", []),
            "edges": citation_data.get("edges", []),
        })
        self._emit_log(f"Citation expansion completed: added {added} citation-neighbor candidates; candidate pool={len(candidates)}.")
        self._emit_stage("ranking", "processing", candidate_count=len(candidates))
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

    def _source_label(self) -> str:
        labels = {
            "wos": "WoS Starter",
            "openalex": "OpenAlex",
            "crossref": "Crossref",
        }
        return labels.get(self.data_source, self.data_source)

    def _source_request_label(self, query: str) -> str:
        if self.data_source == "wos":
            return f"GET /documents db={self.config.wos_db} q={query}"
        if self.data_source == "openalex":
            return f"GET /works search={query}"
        if self.data_source == "crossref":
            return f"GET /works query.bibliographic={query}"
        return query

    def _source_response_log(self, result) -> str:
        total = result.metadata.total if result.metadata else 0
        count = len(result.hits or [])
        if self.data_source in ("openalex", "crossref") and self.provider:
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
        model = getattr(self.llm, "model", "")
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

    def _generate_query(self, question: str) -> str:
        if self.data_source == "openalex":
            return self._generate_openalex_query(question)
        if self.data_source == "crossref":
            return self._generate_crossref_query(question)

        field_hint = ""
        if self.config.search_field:
            field_hint = f"\nDiscipline/field constraint: {self.config.search_field}\nIncorporate this into the query via relevant SO= journals or TS= field-specific keywords."

        messages = [
            {"role": "system", "content": SYSTEM_QUERY_GENERATION},
            {"role": "user", "content": f"Research question: {question}{field_hint}\n\nOutput ONLY the WoS query string."},
        ]
        self._emit_stage("query", "processing", source=self.data_source)
        self._llm_request_log("wos_query_generation")
        raw = self.llm.chat(messages, temperature=0.3)
        self._llm_response_log("wos_query_generation")
        query = _make_starter_safe_query(_extract_query(raw))
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _broaden_query(self, question: str, current_query: str) -> str:
        if self.data_source == "openalex":
            messages = [
                {"role": "system", "content": SYSTEM_OPENALEX_QUERY_BROADEN},
                {"role": "user", "content": (
                    f"Question: {question}\n"
                    f"Current query returned too few results: {current_query}\n"
                    f"Output ONLY the broadened OpenAlex search query string."
                )},
            ]
            self._llm_request_log("openalex_query_broaden")
            raw = self.llm.chat(messages, temperature=0.5)
            self._llm_response_log("openalex_query_broaden")
            query = _extract_openalex_query(raw)
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query
        if self.data_source == "crossref":
            messages = [
                {"role": "system", "content": SYSTEM_CROSSREF_QUERY_BROADEN},
                {"role": "user", "content": (
                    f"Question: {question}\n"
                    f"Current query returned too few results: {current_query}\n"
                    f"Output ONLY the broadened Crossref bibliographic query string."
                )},
            ]
            self._llm_request_log("crossref_query_broaden")
            raw = self.llm.chat(messages, temperature=0.5)
            self._llm_response_log("crossref_query_broaden")
            query = _extract_openalex_query(raw)
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query

        messages = [
            {"role": "system", "content": SYSTEM_QUERY_BROADEN},
            {"role": "user", "content": (
                f"Question: {question}\n"
                f"Current query returned 0 results: {current_query}\n"
                f"Output ONLY the broadened WoS query string."
            )},
        ]
        self._llm_request_log("wos_query_broaden")
        raw = self.llm.chat(messages, temperature=0.5)
        self._llm_response_log("wos_query_broaden")
        query = _make_starter_safe_query(_extract_query(raw))
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _narrow_query(self, question: str, current_query: str) -> str:
        if self.data_source == "openalex":
            messages = [
                {"role": "system", "content": SYSTEM_OPENALEX_QUERY_NARROW},
                {"role": "user", "content": (
                    f"Question: {question}\n"
                    f"Current query returned too many results: {current_query}\n"
                    f"Output ONLY the narrowed OpenAlex search query string."
                )},
            ]
            self._llm_request_log("openalex_query_narrow")
            raw = self.llm.chat(messages, temperature=0.5)
            self._llm_response_log("openalex_query_narrow")
            query = _extract_openalex_query(raw)
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query
        if self.data_source == "crossref":
            messages = [
                {"role": "system", "content": SYSTEM_CROSSREF_QUERY_NARROW},
                {"role": "user", "content": (
                    f"Question: {question}\n"
                    f"Current query returned too many results: {current_query}\n"
                    f"Output ONLY the narrowed Crossref bibliographic query string."
                )},
            ]
            self._llm_request_log("crossref_query_narrow")
            raw = self.llm.chat(messages, temperature=0.5)
            self._llm_response_log("crossref_query_narrow")
            query = _extract_openalex_query(raw)
            self._emit_stage("query", "complete", source=self.data_source, query=query)
            return query

        field_hint = ""
        if self.config.search_field:
            field_hint = f" Consider adding SO= for key journals in {self.config.search_field}."

        messages = [
            {"role": "system", "content": SYSTEM_QUERY_NARROW},
            {"role": "user", "content": (
                f"Question: {question}\n"
                f"Current query returned too many results: {current_query}\n"
                f"{field_hint}\n"
                f"Output ONLY the narrowed WoS query string."
            )},
        ]
        self._llm_request_log("wos_query_narrow")
        raw = self.llm.chat(messages, temperature=0.5)
        self._llm_response_log("wos_query_narrow")
        query = _make_starter_safe_query(_extract_query(raw))
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _generate_openalex_query(self, question: str) -> str:
        field_hint = ""
        if self.config.search_field:
            field_hint = f"\nDiscipline/field constraint: {self.config.search_field}\nTranslate this into standard English field or venue/topic terms if useful."

        messages = [
            {"role": "system", "content": SYSTEM_OPENALEX_QUERY_GENERATION},
            {"role": "user", "content": f"Research question: {question}{field_hint}\n\nOutput ONLY the OpenAlex search query string."},
        ]
        self._emit_stage("query", "processing", source=self.data_source)
        self._llm_request_log("openalex_query_generation")
        raw = self.llm.chat(messages, temperature=0.3)
        self._llm_response_log("openalex_query_generation")
        query = _extract_openalex_query(raw)
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _generate_crossref_query(self, question: str) -> str:
        field_hint = ""
        if self.config.search_field:
            field_hint = f"\nDiscipline/field constraint: {self.config.search_field}\nTranslate this into standard English bibliographic terms if useful."

        messages = [
            {"role": "system", "content": SYSTEM_CROSSREF_QUERY_GENERATION},
            {"role": "user", "content": f"Research question: {question}{field_hint}\n\nOutput ONLY the Crossref bibliographic query string."},
        ]
        self._emit_stage("query", "processing", source=self.data_source)
        self._llm_request_log("crossref_query_generation")
        raw = self.llm.chat(messages, temperature=0.3)
        self._llm_response_log("crossref_query_generation")
        query = _extract_openalex_query(raw)
        self._emit_stage("query", "complete", source=self.data_source, query=query)
        return query

    def _rank_results(self, question: str, documents: list) -> list:
        if not documents:
            return []

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

        self._llm_request_log("result_ranking")
        raw = self.llm.chat(messages, temperature=0.3)
        self._llm_response_log("result_ranking")
        scores = self._parse_ranking_response(raw)

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
            })

        remaining = [d for d in documents if d.uid not in {e.get("uid", "") for e in scores}]
        for doc in remaining:
            ranked.append({"document": doc, "score": 0, "reasoning": ""})

        return sorted(ranked, key=lambda item: float(item.get("score") or 0), reverse=True)

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
