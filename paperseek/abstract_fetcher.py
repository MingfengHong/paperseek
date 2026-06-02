from typing import Optional, Dict
import requests


class AbstractFetcher:
    """Fetch abstracts by DOI from open APIs, with in-memory caching."""

    def __init__(self):
        self._cache: Dict[str, Optional[str]] = {}

    def fetch(self, doi: str) -> Optional[str]:
        if not doi:
            return None
        if doi in self._cache:
            return self._cache[doi]

        abstract = self._try_crossref(doi)
        if abstract is None:
            abstract = self._try_semantic_scholar(doi)

        self._cache[doi] = abstract
        return abstract

    def _try_crossref(self, doi: str) -> Optional[str]:
        try:
            url = f"https://api.crossref.org/works/{doi}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            msg = resp.json().get("message", {})
            abstract = msg.get("abstract", "")
            if abstract and abstract.strip() and len(abstract.strip()) > 20:
                return self._clean_xml(abstract.strip())
        except Exception:
            pass
        return None

    def _try_semantic_scholar(self, doi: str) -> Optional[str]:
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=abstract"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            abstract = resp.json().get("abstract", "")
            if abstract and abstract.strip():
                return abstract.strip()
        except Exception:
            pass
        return None

    @staticmethod
    def _clean_xml(text: str) -> str:
        import re
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = re.sub(r"\s+", " ", text).strip()
        return text
