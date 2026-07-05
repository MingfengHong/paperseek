import unittest
from types import SimpleNamespace
from unittest.mock import patch

from paperseek_core.agent import PaperSeekAgent
from paperseek_core.retrieval import RetrievalLane, document_key, fuse_candidates_rrf
from paperseek_core.sources.providers import (
    ArxivProvider,
    PaperCitation,
    PaperHubProvider,
    PaperIdentifiers,
    PaperRecord,
    PaperSource,
    ProviderSearchResult,
    SearchMetadata,
    SemanticScholarProvider,
)


class FakeLLM:
    def chat(self, messages, temperature=0.3):
        return "[]"


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


def record(uid, title, abstract="", year=2024, citations=0, doi=""):
    return PaperRecord(
        uid=uid,
        title=title,
        abstract=abstract,
        source=PaperSource(source_title="Journal", publish_year=year),
        identifiers=PaperIdentifiers(doi=doi),
        citations=[PaperCitation(db="test", count=citations)] if citations else [],
        provider="test",
    )


def config(**overrides):
    base = dict(
        data_source="openalex",
        target_min=5,
        target_max=50,
        max_iterations=5,
        retrieval_pool_max=3000,
        retrieval_pool_min=5,
        retrieval_lane_limit=1000,
        retrieval_rrf_k=60,
        retrieval_embedding_provider="local",
        retrieval_embedding_model="qwen3-embedding:8b",
        retrieval_embedding_base_url="",
        retrieval_embedding_api_key="",
        retrieval_reranker_provider="",
        retrieval_reranker_model="qwen3-reranker:8b",
        retrieval_reranker_base_url="",
        retrieval_reranker_api_key="",
        retrieval_crossref_enrichment=False,
        expand_citations=False,
        search_field="",
        discipline_fields=(),
        openalex_api_key="",
        openalex_email="",
        crossref_email="",
        semantic_scholar_api_key="",
        pubmed_api_key="",
        pubmed_email="",
        pubmed_tool="paperseek",
        wos_api_key="",
        wos_db="WOS",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class RetrievalFusionTest(unittest.TestCase):
    def test_rrf_fusion_prefers_documents_supported_by_multiple_lanes(self):
        shared = record("A", "graph retrieval for literature search", "graph neural retrieval")
        relevance_only = record("B", "unrelated platform governance")
        impact_only = record("C", "graph retrieval citation classic")
        fused = fuse_candidates_rrf(
            "graph retrieval literature",
            {
                RetrievalLane.RELEVANCE: [shared, relevance_only],
                RetrievalLane.IMPACT: [impact_only, shared],
                RetrievalLane.RECENT: [shared],
            },
            pool_max=3,
            rrf_k=60,
        )
        self.assertEqual(document_key(fused.documents[0]), document_key(shared))
        self.assertEqual(set(fused.metadata_by_key[document_key(shared)]["retrieval_lanes"]), {
            RetrievalLane.RELEVANCE,
            RetrievalLane.IMPACT,
            RetrievalLane.RECENT,
        })

    def test_rrf_fusion_dedupes_by_doi(self):
        first = record("A", "First", doi="10.1234/example")
        second = record("B", "Second", doi="https://doi.org/10.1234/example")
        fused = fuse_candidates_rrf("example", {RetrievalLane.RELEVANCE: [first], RetrievalLane.IMPACT: [second]})
        self.assertEqual(len(fused.documents), 1)


class ProviderLaneTest(unittest.TestCase):
    def test_arxiv_recent_lane_uses_submitted_date_sort(self):
        captured = {}
        atom = """<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"><opensearch:totalResults>0</opensearch:totalResults></feed>"""

        def fake_get(provider, url, params=None, headers=None, timeout=0, query="", attempts=None):
            captured.update(params or {})
            captured["url"] = url
            captured["timeout"] = timeout
            captured["attempts"] = attempts
            return FakeResponse(text=atom), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}

        with patch("paperseek_core.sources.providers.get_with_retries", fake_get):
            ArxivProvider().search("graph retrieval", lane=RetrievalLane.RECENT)

        self.assertEqual(captured["sortBy"], "submittedDate")
        self.assertEqual(captured["url"], "http://export.arxiv.org/api/query")
        self.assertEqual(captured["timeout"], 20)
        self.assertEqual(captured["attempts"], 1)

    def test_semantic_scholar_impact_lane_uses_bulk_citation_sort(self):
        captured = {}

        def fake_get(provider, url, params=None, headers=None, timeout=0, query=""):
            captured.update({"url": url, "params": dict(params or {})})
            return FakeResponse(payload={"total": 0, "data": []}), {"method": "GET", "url": url, "status": 200, "elapsed_ms": 1}

        with patch("paperseek_core.sources.providers.get_with_retries", fake_get):
            SemanticScholarProvider(api_key="key").search("graph retrieval", lane=RetrievalLane.IMPACT)

        self.assertTrue(captured["url"].endswith("/paper/search/bulk"))
        self.assertEqual(captured["params"]["sort"], "citationCount:desc")

    def test_paperhub_local_quality_orders_by_score_and_venue(self):
        papers = [
            {"id": "a", "title": "Graph Retrieval", "abstract": "graph retrieval", "conference": "AAAI", "year": 2025},
            {"id": "b", "title": "Graph Retrieval", "abstract": "graph retrieval", "conference": "NeurIPS", "year": 2024},
        ]
        with patch.object(PaperHubProvider, "_load_papers", return_value=papers):
            result = PaperHubProvider().search("graph retrieval", lane=RetrievalLane.LOCAL_QUALITY)
        self.assertEqual(result.hits[0].uid, "b")

    def test_paperhub_query_uses_required_terms_or_and_metadata_filters(self):
        papers = [
            {"id": "a", "title": "Graph Neural Retrieval", "abstract": "retrieval benchmark", "conference": "ICLR", "year": 2025},
            {"id": "b", "title": "Graph Neural Networks Survey", "abstract": "retrieval benchmark", "conference": "ICLR", "year": 2025},
            {"id": "c", "title": "Graph Neural Retrieval", "abstract": "retrieval benchmark", "conference": "NeurIPS", "year": 2025},
            {"id": "d", "title": "Vision Retrieval", "abstract": "image benchmark", "conference": "ICLR", "year": 2025},
        ]

        with patch.object(PaperHubProvider, "_load_papers", return_value=papers):
            result = PaperHubProvider().search('"graph neural" OR GNN retrieval -survey conference:ICLR year:2025', limit=10)

        self.assertEqual([hit.uid for hit in result.hits], ["a"])

    def test_paperhub_plain_terms_are_required_not_broadening_or_terms(self):
        papers = [
            {"id": "a", "title": "Graph Retrieval", "abstract": "", "conference": "ICLR", "year": 2025},
            {"id": "b", "title": "Graph Generation", "abstract": "", "conference": "ICLR", "year": 2025},
            {"id": "c", "title": "Neural Retrieval", "abstract": "", "conference": "ICLR", "year": 2025},
        ]

        with patch.object(PaperHubProvider, "_load_papers", return_value=papers):
            broad = PaperHubProvider().search("graph", limit=10)
            narrow = PaperHubProvider().search("graph retrieval", limit=10)

        self.assertEqual(broad.metadata.total, 2)
        self.assertEqual(narrow.metadata.total, 1)


class RetrievalAgentTest(unittest.TestCase):
    def test_adaptive_iteration_continues_after_configured_limit_when_pool_is_too_large(self):
        agent = PaperSeekAgent(config(retrieval_pool_max=3000), FakeLLM())
        self.assertTrue(agent._should_narrow_after_result(5000, 5, 5, 10))
        self.assertFalse(agent._should_narrow_after_result(2000, 5, 5, 10))
        self.assertFalse(agent._should_narrow_after_result(500, 1, 5, 10))

    def test_zero_results_stop_after_configured_iterations(self):
        agent = PaperSeekAgent(config(retrieval_pool_min=5), FakeLLM())
        self.assertFalse(agent._should_broaden_after_result(0, 5, 5, 10))
        self.assertTrue(agent._should_broaden_after_result(3, 5, 5, 10))

    def test_retrieve_candidates_uses_provider_capability_lanes(self):
        class Provider:
            def retrieval_capabilities(self):
                return SimpleNamespace(source="fake", lanes=(RetrievalLane.RELEVANCE, RetrievalLane.RECENT), max_lane_limit=10)

            def search(self, query, limit=50, page=1, lane=RetrievalLane.RELEVANCE):
                if lane == RetrievalLane.RECENT:
                    return ProviderSearchResult(SearchMetadata(total=1, page=1, limit=limit), [record("recent", "graph retrieval recent", year=2025)])
                return ProviderSearchResult(SearchMetadata(total=1, page=1, limit=limit), [record("rel", "graph retrieval relevant", year=2022)])

        agent = PaperSeekAgent(config(data_source="fake", retrieval_lane_limit=10, retrieval_pool_max=10), FakeLLM())
        agent.provider = Provider()
        docs = agent._retrieve_candidates("graph retrieval", "graph retrieval", [])
        self.assertEqual({doc.uid for doc in docs}, {"rel", "recent"})

    def test_llm_ranking_candidate_limit_is_separate_from_retrieval_pool(self):
        agent = PaperSeekAgent(config(retrieval_pool_max=3000, target_max=50), FakeLLM())
        self.assertEqual(agent._llm_ranking_candidate_limit(), 256)

        agent = PaperSeekAgent(config(retrieval_pool_max=30, target_max=50), FakeLLM())
        self.assertEqual(agent._llm_ranking_candidate_limit(), 30)

    def test_ranked_output_keeps_all_high_score_results_after_llm_limit(self):
        agent = PaperSeekAgent(config(), FakeLLM())
        ranked = [
            {"document": record(f"r{index}", f"paper {index}"), "score": 7 if index < 70 else 4}
            for index in range(90)
        ]

        selected = agent._select_ranked_output(ranked)

        self.assertEqual(len(selected), 70)
        self.assertTrue(all(item["score"] >= 5 for item in selected))

    def test_ranked_output_falls_back_to_top_fifty_when_high_score_results_are_few(self):
        agent = PaperSeekAgent(config(), FakeLLM())
        ranked = [
            {"document": record(f"r{index}", f"paper {index}"), "score": 7 if index < 20 else 4}
            for index in range(90)
        ]

        self.assertEqual(len(agent._select_ranked_output(ranked)), 50)

    def test_ranked_output_keeps_all_when_total_is_below_fifty(self):
        agent = PaperSeekAgent(config(), FakeLLM())
        ranked = [
            {"document": record(f"r{index}", f"paper {index}"), "score": 3}
            for index in range(12)
        ]

        self.assertEqual(len(agent._select_ranked_output(ranked)), 12)

    def test_ranking_batch_size_does_not_expand_for_large_candidate_sets(self):
        agent = PaperSeekAgent(config(ranking_batch_size=8), FakeLLM())
        self.assertEqual(agent._ranking_batch_size(100), 8)

    def test_external_embedding_uses_openai_compatible_endpoint(self):
        agent = PaperSeekAgent(
            config(
                retrieval_embedding_provider="cstcloud",
                retrieval_embedding_api_key="sk-test",
                retrieval_embedding_base_url="https://uni-api.cstcloud.cn/v1",
                retrieval_embedding_model="qwen3-embedding:8b",
            ),
            FakeLLM(),
        )
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=0):
            captured.update({"url": url, "headers": dict(headers or {}), "json": dict(json or {})})
            return FakeResponse(payload={
                "data": [
                    {"index": 0, "embedding": [1.0, 0.0]},
                    {"index": 1, "embedding": [1.0, 0.0]},
                    {"index": 2, "embedding": [0.0, 1.0]},
                ]
            })

        docs = [record("a", "graph retrieval"), record("b", "platform governance")]
        with patch("paperseek_core.agent.requests.post", fake_post):
            scores = agent._external_embedding_scores("graph retrieval", docs)

        self.assertEqual(captured["url"], "https://uni-api.cstcloud.cn/v1/embeddings")
        self.assertEqual(captured["json"]["model"], "qwen3-embedding:8b")
        self.assertEqual(captured["json"]["encoding_format"], "float")
        self.assertEqual(scores, [1.0, 0.0])

    def test_nvidia_embedding_marks_query_and_passages(self):
        agent = PaperSeekAgent(
            config(
                retrieval_embedding_provider="nvidia",
                retrieval_embedding_api_key="nv-test",
                retrieval_embedding_base_url="https://integrate.api.nvidia.com/v1",
                retrieval_embedding_model="nvidia/nv-embedqa-e5-v5",
            ),
            FakeLLM(),
        )
        calls = []

        def fake_post(url, headers=None, json=None, timeout=0):
            calls.append({"url": url, "json": dict(json or {})})
            if json["input_type"] == "query":
                data = [{"index": 0, "embedding": [1.0, 0.0]}]
            else:
                data = [{"index": 0, "embedding": [1.0, 0.0]}, {"index": 1, "embedding": [0.0, 1.0]}]
            return FakeResponse(payload={"data": data})

        docs = [record("a", "graph retrieval"), record("b", "platform governance")]
        with patch("paperseek_core.agent.requests.post", fake_post):
            scores = agent._external_embedding_scores("graph retrieval", docs)

        self.assertEqual([call["url"] for call in calls], ["https://integrate.api.nvidia.com/v1/embeddings"] * 2)
        self.assertEqual([call["json"]["input_type"] for call in calls], ["query", "passage"])
        self.assertEqual(calls[0]["json"]["input"], ["graph retrieval"])
        self.assertEqual(calls[1]["json"]["input"][0], "graph retrieval Journal 2024")
        self.assertEqual(calls[1]["json"]["input"][1], "platform governance Journal 2024")
        self.assertEqual(scores, [1.0, 0.0])

    def test_external_embedding_falls_back_to_next_model(self):
        agent = PaperSeekAgent(
            config(
                retrieval_embedding_provider="cstcloud",
                retrieval_embedding_api_key="sk-test",
                retrieval_embedding_base_url="https://uni-api.cstcloud.cn/v1",
                retrieval_embedding_model="qwen3-embedding:8b,bge-large-zh:latest",
            ),
            FakeLLM(),
        )
        models = []

        def fake_post(url, headers=None, json=None, timeout=0):
            models.append(json["model"])
            if json["model"] == "qwen3-embedding:8b":
                return FakeResponse(payload={"error": "temporary"}, status_code=503, text="temporary")
            return FakeResponse(payload={
                "data": [
                    {"index": 0, "embedding": [1.0, 0.0]},
                    {"index": 1, "embedding": [1.0, 0.0]},
                ]
            })

        with patch("paperseek_core.agent.requests.post", fake_post):
            scores = agent._external_embedding_scores("graph retrieval", [record("a", "graph retrieval")])

        self.assertEqual(models, ["qwen3-embedding:8b", "bge-large-zh:latest"])
        self.assertEqual(scores, [1.0])

    def test_external_embedding_rotates_key_pool_on_retryable_status(self):
        agent = PaperSeekAgent(
            config(
                retrieval_embedding_provider="cstcloud",
                retrieval_embedding_api_key="sk-a,sk-b",
                retrieval_embedding_base_url="https://uni-api.cstcloud.cn/v1",
                retrieval_embedding_model="qwen3-embedding:8b",
            ),
            FakeLLM(),
        )
        calls = []

        def fake_post(url, headers=None, json=None, timeout=0):
            calls.append(headers.get("Authorization"))
            if len(calls) == 1:
                return FakeResponse(payload={"error": "limited"}, status_code=429, text="limited")
            return FakeResponse(payload={"data": [{"index": 0, "embedding": [1.0, 0.0]}, {"index": 1, "embedding": [1.0, 0.0]}]})

        with patch("paperseek_core.agent.requests.post", fake_post):
            scores = agent._external_embedding_scores("graph retrieval", [record("a", "graph retrieval")])

        self.assertEqual(calls, ["Bearer sk-a", "Bearer sk-b"])
        self.assertEqual(scores, [1.0])

    def test_external_reranker_reorders_prefix_when_available(self):
        agent = PaperSeekAgent(
            config(
                retrieval_reranker_provider="cstcloud",
                retrieval_reranker_api_key="sk-test",
                retrieval_reranker_base_url="https://uni-api.cstcloud.cn/v1",
                retrieval_reranker_model="qwen3-reranker:8b",
            ),
            FakeLLM(),
        )

        def fake_post(url, headers=None, json=None, timeout=0):
            return FakeResponse(payload={"results": [{"index": 1, "relevance_score": 0.9}, {"index": 0, "relevance_score": 0.2}]})

        docs = [record("a", "less relevant"), record("b", "more relevant")]
        with patch("paperseek_core.agent.requests.post", fake_post):
            reranked = agent._apply_external_reranker("graph retrieval", docs)

        self.assertEqual([doc.uid for doc in reranked], ["b", "a"])

    def test_nvidia_reranker_uses_rankings_endpoint_and_logit_scores(self):
        agent = PaperSeekAgent(
            config(
                retrieval_reranker_provider="nvidia",
                retrieval_reranker_api_key="nv-test",
                retrieval_reranker_base_url="https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking",
                retrieval_reranker_model="nv-rerank-qa-mistral-4b:1",
            ),
            FakeLLM(),
        )
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=0):
            captured.update({"url": url, "headers": dict(headers or {}), "json": dict(json or {})})
            return FakeResponse(payload={"rankings": [{"index": 1, "logit": 4.7}, {"index": 0, "logit": -1.0}]})

        docs = [record("a", "less relevant"), record("b", "more relevant")]
        with patch("paperseek_core.agent.requests.post", fake_post):
            reranked = agent._apply_external_reranker("graph retrieval", docs)

        self.assertEqual(captured["url"], "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking")
        self.assertEqual(captured["headers"]["Accept"], "application/json")
        self.assertEqual(captured["json"]["model"], "nv-rerank-qa-mistral-4b:1")
        self.assertEqual(captured["json"]["query"], {"text": "graph retrieval"})
        self.assertEqual(captured["json"]["passages"], [{"text": "less relevant Journal 2024"}, {"text": "more relevant Journal 2024"}])
        self.assertEqual([doc.uid for doc in reranked], ["b", "a"])

    def test_nvidia_reranker_preserves_ranking_endpoint(self):
        agent = PaperSeekAgent(
            config(
                retrieval_reranker_provider="nvidia",
                retrieval_reranker_api_key="nv-test",
                retrieval_reranker_base_url="http://localhost:8000/v1/ranking",
                retrieval_reranker_model="nv-rerank-qa-mistral-4b:1",
            ),
            FakeLLM(),
        )
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=0):
            captured["url"] = url
            return FakeResponse(payload={"rankings": [{"index": 0, "logit": 1.0}]})

        with patch("paperseek_core.agent.requests.post", fake_post):
            agent._apply_external_reranker("graph retrieval", [record("a", "relevant")])

        self.assertEqual(captured["url"], "http://localhost:8000/v1/ranking")

    def test_external_reranker_falls_back_to_next_model(self):
        agent = PaperSeekAgent(
            config(
                retrieval_reranker_provider="cstcloud",
                retrieval_reranker_api_key="sk-test",
                retrieval_reranker_base_url="https://uni-api.cstcloud.cn/v1",
                retrieval_reranker_model="qwen3-reranker:8b,bge-reranker-v2-m3",
            ),
            FakeLLM(),
        )
        models = []

        def fake_post(url, headers=None, json=None, timeout=0):
            models.append(json["model"])
            if json["model"] == "qwen3-reranker:8b":
                return FakeResponse(payload={"error": "temporary"}, status_code=503, text="temporary")
            return FakeResponse(payload={"results": [{"index": 1, "relevance_score": 0.9}, {"index": 0, "relevance_score": 0.2}]})

        docs = [record("a", "less relevant"), record("b", "more relevant")]
        with patch("paperseek_core.agent.requests.post", fake_post):
            reranked = agent._apply_external_reranker("graph retrieval", docs)

        self.assertEqual(models, ["qwen3-reranker:8b", "bge-reranker-v2-m3"])
        self.assertEqual([doc.uid for doc in reranked], ["b", "a"])

    def test_external_reranker_rotates_key_pool_on_retryable_status(self):
        agent = PaperSeekAgent(
            config(
                retrieval_reranker_provider="nvidia",
                retrieval_reranker_api_key="nv-a,nv-b",
                retrieval_reranker_base_url="https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking",
                retrieval_reranker_model="nv-rerank-qa-mistral-4b:1",
            ),
            FakeLLM(),
        )
        calls = []

        def fake_post(url, headers=None, json=None, timeout=0):
            calls.append(headers.get("Authorization"))
            if len(calls) == 1:
                return FakeResponse(payload={"error": "limited"}, status_code=429, text="limited")
            return FakeResponse(payload={"rankings": [{"index": 1, "logit": 4.0}, {"index": 0, "logit": 1.0}]})

        docs = [record("a", "less relevant"), record("b", "more relevant")]
        with patch("paperseek_core.agent.requests.post", fake_post):
            reranked = agent._apply_external_reranker("graph retrieval", docs)

        self.assertEqual(calls, ["Bearer nv-a", "Bearer nv-b"])
        self.assertEqual([doc.uid for doc in reranked], ["b", "a"])

    def test_retrieval_provider_default_base_urls_include_common_embedding_vendors(self):
        agent = PaperSeekAgent(config(llm_api_key="sk-test"), FakeLLM())
        self.assertEqual(agent._retrieval_base_url("embedding", "dashscope"), "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.assertEqual(agent._retrieval_base_url("embedding", "siliconflow"), "https://api.siliconflow.cn/v1")
        self.assertEqual(agent._retrieval_base_url("embedding", "modelscope"), "https://api-inference.modelscope.cn/v1")
        self.assertEqual(agent._retrieval_base_url("embedding", "openrouter"), "https://openrouter.ai/api/v1")
        self.assertEqual(agent._retrieval_base_url("embedding", "nvidia"), "https://integrate.api.nvidia.com/v1")
        self.assertEqual(agent._retrieval_base_url("reranker", "nvidia"), "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking")
        self.assertEqual(agent._retrieval_base_url("reranker", "modelscope"), "")
        self.assertEqual(agent._retrieval_api_key("embedding", "dashscope"), "sk-test")
        self.assertEqual(agent._retrieval_api_key("reranker", "openrouter"), "sk-test")

    def test_modelscope_embedding_defaults_to_supported_qwen_models(self):
        agent = PaperSeekAgent(config(retrieval_embedding_model="qwen3-embedding:8b,bge-large-zh:latest"), FakeLLM())
        self.assertEqual(
            agent._retrieval_model_candidates("embedding", "qwen3-embedding:8b", "modelscope"),
            ["Qwen/Qwen3-Embedding-8B", "Qwen/Qwen3-Embedding-4B"],
        )

    def test_modelscope_reranker_is_skipped(self):
        agent = PaperSeekAgent(config(retrieval_reranker_provider="modelscope", llm_api_key="sk-test"), FakeLLM())
        docs = [record("a", "graph retrieval")]
        with patch("paperseek_core.agent.requests.post") as post:
            self.assertEqual(agent._apply_external_reranker("graph retrieval", docs), docs)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
