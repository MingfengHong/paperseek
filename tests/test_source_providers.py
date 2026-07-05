import unittest
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from paperseek_core.sources.providers import (
    ArxivProvider,
    GoogleScholarSerperProvider,
    PaperHubProvider,
    PubMedProvider,
    SemanticScholarProvider,
)


class FakeResponse:
    def __init__(self, payload=None, text="", status_code=200, url="https://example.test"):
        self._payload = payload
        self.text = text
        self.status_code = status_code
        self.url = url

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class SourceProviderTest(unittest.TestCase):
    def test_arxiv_provider_parses_atom_records(self):
        atom = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Graph Retrieval</title>
    <summary>Graph retrieval abstract.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <link href="http://arxiv.org/abs/2401.00001v1" rel="alternate"/>
    <link href="http://arxiv.org/pdf/2401.00001v1" title="pdf" type="application/pdf"/>
    <arxiv:doi>10.1234/example</arxiv:doi>
    <arxiv:primary_category term="cs.IR"/>
  </entry>
</feed>"""
        captured = {}

        def fake_get(provider, url, params=None, headers=None, timeout=0, query="", attempts=None):
            captured.update({
                "provider": provider,
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
                "query": query,
                "attempts": attempts,
            })
            return FakeResponse(text=atom), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}

        with patch("paperseek_core.sources.providers.get_with_retries", fake_get):
            result = ArxivProvider().search("graph retrieval", limit=1)

        self.assertEqual(result.metadata.total, 1)
        self.assertEqual(result.hits[0].provider, "arxiv")
        self.assertEqual(result.hits[0].identifiers.arxiv, "2401.00001v1")
        self.assertEqual(result.hits[0].identifiers.doi, "10.1234/example")
        self.assertEqual(captured["url"], "http://export.arxiv.org/api/query")
        self.assertEqual(captured["timeout"], 20)
        self.assertEqual(captured["attempts"], 1)
        self.assertEqual(captured["params"]["search_query"], 'all:"graph retrieval"')

    def test_arxiv_provider_escapes_quotes_in_plain_query(self):
        self.assertEqual(
            ArxivProvider._search_query('graph "neural" retrieval'),
            'all:"graph \\"neural\\" retrieval"',
        )

    def test_semantic_scholar_provider_uses_api_key_and_maps_fields(self):
        payload = {
            "total": 1,
            "data": [
                {
                    "paperId": "S2",
                    "title": "Graph Learning",
                    "abstract": "Abstract.",
                    "year": 2024,
                    "authors": [{"name": "Ada"}],
                    "externalIds": {"DOI": "10.1234/s2", "PubMed": "123", "ArXiv": "2401.00001"},
                    "citationCount": 7,
                    "fieldsOfStudy": ["Computer Science"],
                    "openAccessPdf": {"url": "https://example.test/paper.pdf"},
                }
            ],
        }
        captured = {}

        def fake_get(provider, url, params=None, headers=None, timeout=0, query=""):
            captured.update({"provider": provider, "headers": headers, "params": params})
            return FakeResponse(payload=payload), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}

        with patch("paperseek_core.sources.providers.get_with_retries", fake_get):
            result = SemanticScholarProvider(api_key="s2-key").search("graph learning", limit=1)

        record = result.hits[0]
        self.assertEqual(captured["headers"]["x-api-key"], "s2-key")
        self.assertEqual(record.provider, "semanticscholar")
        self.assertEqual(record.identifiers.doi, "10.1234/s2")
        self.assertEqual(record.identifiers.pmid, "123")
        self.assertEqual(record.identifiers.arxiv, "2401.00001")
        self.assertEqual(record.citations[0].count, 7)

    def test_semantic_scholar_provider_falls_back_to_basic_fields_after_5xx(self):
        calls = []

        def fake_get(provider, url, params=None, headers=None, timeout=0, query=""):
            calls.append(dict(params or {}))
            if len(calls) == 1:
                return FakeResponse(payload={"message": "Internal Server Error"}, text='{"message":"Internal Server Error"}', status_code=500), {
                    "method": "GET",
                    "url": url,
                    "status": 500,
                    "elapsed_ms": 1,
                }
            return FakeResponse(payload={
                "total": 1,
                "data": [{
                    "paperId": "S2",
                    "title": "Graph Learning",
                    "year": 2024,
                    "authors": [{"name": "Ada"}],
                    "citationCount": 7,
                }],
            }), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 2}

        with patch("paperseek_core.sources.providers.get_with_retries", fake_get):
            provider = SemanticScholarProvider(api_key="s2-key")
            result = provider.search("graph learning", limit=1)

        self.assertEqual(len(calls), 2)
        self.assertIn("abstract", calls[0]["fields"])
        self.assertNotIn("abstract", calls[1]["fields"])
        self.assertEqual(provider.last_response_info["fallback"], "basic_fields")
        self.assertEqual(result.metadata.total, 1)
        self.assertEqual(result.hits[0].title, "Graph Learning")

    def test_pubmed_provider_uses_eutilities_and_parses_abstracts(self):
        calls = []

        def fake_get(provider, url, params=None, headers=None, timeout=0, query=""):
            calls.append((url, dict(params or {})))
            if url.endswith("esearch.fcgi"):
                return FakeResponse(payload={"esearchresult": {"count": "1", "idlist": ["123"]}}), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}
            if url.endswith("esummary.fcgi"):
                return FakeResponse(payload={"result": {"123": {"title": "Cancer Immunotherapy", "uid": "123", "pubdate": "2024", "authors": [{"name": "Lin"}], "articleids": [{"idtype": "doi", "value": "10.1234/pubmed"}]}}}), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}
            if url.endswith("efetch.fcgi"):
                xml = "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><Abstract><AbstractText>PubMed abstract.</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"
                return FakeResponse(text=xml), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}
            raise AssertionError(url)

        with patch("paperseek_core.sources.providers.get_with_retries", fake_get):
            result = PubMedProvider(api_key="ncbi-key", email="you@example.org", tool="paperseek-test").search("cancer", limit=1)

        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0][1]["api_key"], "ncbi-key")
        self.assertEqual(calls[0][1]["email"], "you@example.org")
        self.assertEqual(calls[0][1]["tool"], "paperseek-test")
        record = result.hits[0]
        self.assertEqual(record.provider, "pubmed")
        self.assertEqual(record.identifiers.pmid, "123")
        self.assertEqual(record.identifiers.doi, "10.1234/pubmed")
        self.assertEqual(record.abstract, "PubMed abstract.")

    def test_google_scholar_serper_provider_posts_query_and_maps_results(self):
        payload = {
            "organic": [
                {
                    "id": "gs-1",
                    "title": "AI Governance and Accountability",
                    "link": "https://example.org/paper",
                    "pdfUrl": "https://example.org/paper.pdf",
                    "snippet": "A Google Scholar result snippet.",
                    "year": 2024,
                    "publicationInfo": {
                        "summary": "A Ada - Journal of AI Policy, 2024",
                        "authors": [{"name": "A Ada"}],
                    },
                    "citedBy": {"total": 12, "link": "https://scholar.google.com/scholar?cites=1"},
                }
            ]
        }
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=0):
            captured.update({"url": url, "json": json, "headers": headers, "timeout": timeout})
            return FakeResponse(payload=payload, status_code=200, url=url)

        with patch("paperseek_core.sources.providers.requests.post", fake_post):
            result = GoogleScholarSerperProvider(api_key="serper-a,serper-b").search("AI governance", limit=5, page=2)

        self.assertEqual(captured["url"], "https://google.serper.dev/scholar")
        self.assertEqual(captured["json"]["q"], "AI governance")
        self.assertEqual(captured["json"]["page"], 2)
        self.assertNotIn("num", captured["json"])
        self.assertIn(captured["headers"]["X-API-KEY"], {"serper-a", "serper-b"})
        self.assertEqual(result.metadata.total, 11)
        record = result.hits[0]
        self.assertEqual(record.provider, "googlescholar")
        self.assertEqual(record.uid, "googlescholar:gs-1")
        self.assertEqual(record.links.pdf, "https://example.org/paper.pdf")
        self.assertEqual(record.citations[0].count, 12)
        self.assertEqual(record.abstract, "A Google Scholar result snippet.")

    def test_google_scholar_serper_provider_skips_transient_empty_pages(self):
        payloads = [
            {"organic": []},
            {
                "organic": [
                    {"id": "gs-2", "title": "AI Governance", "link": "https://example.org/2"},
                    {"id": "gs-3", "title": "AI Accountability", "link": "https://example.org/3"},
                ]
            },
        ]
        pages = []

        def fake_post(url, json=None, headers=None, timeout=0):
            pages.append(json["page"])
            payload = payloads.pop(0) if payloads else {"organic": []}
            return FakeResponse(payload=payload, status_code=200, url=url)

        with patch("paperseek_core.sources.providers.requests.post", fake_post):
            result = GoogleScholarSerperProvider(api_key="serper-a").search("AI governance", limit=5)

        self.assertEqual(pages[:2], [1, 2])
        self.assertEqual(len(result.hits), 2)
        self.assertEqual(result.metadata.total, 12)

    def test_paperhub_provider_loads_manifest_and_scores_shards(self):
        PaperHubProvider._paper_cache = None

        def fake_get(provider, url, params=None, headers=None, timeout=0, query=""):
            if url.endswith("manifest.json"):
                return FakeResponse(payload={"shards": [{"file": "shards/iclr-2025.fake.json"}]}), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}
            if url.endswith("iclr-2025.fake.json"):
                return FakeResponse(payload={"papers": [{"id": "p1", "title": "Graph Neural Retrieval", "authors": ["Ada"], "conference": "ICLR", "year": 2025, "abstract": "retrieval with graphs"}]}), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}
            raise AssertionError(url)

        with patch("paperseek_core.sources.providers.get_with_retries", fake_get):
            result = PaperHubProvider().search("graph retrieval", limit=1)

        self.assertEqual(result.metadata.total, 1)
        record = result.hits[0]
        self.assertEqual(record.provider, "paperhub")
        self.assertEqual(record.source.source_title, "ICLR")
        self.assertEqual(record.source.publish_year, 2025)

    def test_paperhub_provider_initializes_cache_once_under_concurrency(self):
        PaperHubProvider._paper_cache = None
        calls = []

        def fake_get(provider, url, params=None, headers=None, timeout=0, query=""):
            calls.append(url)
            time.sleep(0.01)
            if url.endswith("manifest.json"):
                return FakeResponse(payload={"shards": [{"file": "shards/iclr-2025.fake.json"}]}), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}
            if url.endswith("iclr-2025.fake.json"):
                return FakeResponse(payload={"papers": [{"id": "p1", "title": "Graph Neural Retrieval", "authors": ["Ada"], "conference": "ICLR", "year": 2025, "abstract": "retrieval with graphs"}]}), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}
            raise AssertionError(url)

        with patch("paperseek_core.sources.providers.get_with_retries", fake_get):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: PaperHubProvider().search("graph retrieval", limit=1), range(2)))

        self.assertEqual([result.metadata.total for result in results], [1, 1])
        self.assertEqual(sum(1 for url in calls if url.endswith("manifest.json")), 1)
        self.assertEqual(sum(1 for url in calls if url.endswith("iclr-2025.fake.json")), 1)


if __name__ == "__main__":
    unittest.main()
