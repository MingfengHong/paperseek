import json
import re
import unittest

from paperseek.config import AgentConfig
from paperseek.providers import PaperRecord, PaperSource, ProviderSearchResult, SearchMetadata, OpenAlexProvider
from paperseek.search_agent import WosSearchAgent


def paper(uid, title=None, refs=None):
    return PaperRecord(
        uid=uid,
        title=title or uid,
        source=PaperSource(source_title="Test Journal", publish_year=2026),
        provider="openalex",
        raw={"referenced_works": refs or []},
    )


class FakeLLM:
    def __init__(self):
        self.model = "fake-model"
        self.base_url = "http://fake-llm"
        self.last_response_info = {"method": "POST", "url": "http://fake-llm/chat", "status": 200, "elapsed_ms": 1}
        self.calls = []

    def chat(self, messages, temperature=0.3):
        text = "\n".join(message["content"] for message in messages)
        self.calls.append(text)
        if "evaluating academic papers" in text:
            uids = []
            for line in text.splitlines():
                match = re.search(r"\bUID:\s*(.+)$", line.strip())
                if match:
                    uids.append(match.group(1).strip())
            return json.dumps([{"uid": uid, "score": 9 if uid != "N2" else 6, "reasoning": "test"} for uid in uids])
        if "reached its final iteration" in text:
            return "focused query"
        return "generated query"


class FakeProvider:
    def __init__(self):
        self.queries = []
        self.last_response_info = {"method": "GET", "url": "https://example.org/works", "status": 200, "elapsed_ms": 1}

    def search(self, query, limit=50, page=1):
        self.queries.append(query)
        total = 1
        if query == "generated query":
            total = 5000
        return ProviderSearchResult(SearchMetadata(total=total, page=1, limit=limit), [paper("P1")])


class FakePagingProvider:
    def __init__(self):
        self.pages = []
        self.last_response_info = {"method": "GET", "url": "https://example.org/works", "status": 200, "elapsed_ms": 1}

    def search(self, query, limit=50, page=1):
        self.pages.append(page)
        if page == 1:
            records = [paper("P1"), paper("P2"), paper("P3")][:limit] if limit >= 3 else [paper("P1")]
        else:
            records = [paper("P2"), paper("P3")][:limit]
        return ProviderSearchResult(SearchMetadata(total=3, page=page, limit=limit), records)


class FakeOpenAlexCitationProvider(OpenAlexProvider):
    def __init__(self):
        super().__init__()
        self.calls = []

    def citation_neighbors_with_graph(self, seeds, per_seed=4, max_records=40):
        self.calls.append([seed.uid for seed in seeds])
        if len(self.calls) == 1:
            records = [paper("N1")]
            return {
                "records": records,
                "nodes": [{"id": "N1", "title": "N1", "roles": ["forward"], "seed_uids": [seeds[0].uid]}],
                "edges": [{"source": "N1", "target": seeds[0].uid, "type": "cites", "seed": seeds[0].uid}],
            }
        records = [paper("N2")]
        return {
            "records": records,
            "nodes": [{"id": "N2", "title": "N2", "roles": ["forward"], "seed_uids": [seeds[0].uid]}],
            "edges": [{"source": "N2", "target": seeds[0].uid, "type": "cites", "seed": seeds[0].uid}],
        }


def config(**overrides):
    base = AgentConfig(
        data_source="openalex",
        llm_provider="ollama",
        llm_api_type="openai_chat",
        llm_model="fake-model",
        llm_base_url="http://fake-llm",
        target_min=5,
        target_max=50,
        max_iterations=1,
        expand_citations=False,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


class SearchAgentFlowTest(unittest.TestCase):
    def test_final_iteration_uses_fallback_query_when_source_count_is_unusable(self):
        llm = FakeLLM()
        agent = WosSearchAgent(config(search_accept_max_records=1000), llm)
        provider = FakeProvider()
        agent.provider = provider

        result = agent.search("open innovation")

        self.assertEqual(provider.queries, ["generated query", "focused query"])
        self.assertEqual(result["final_query"], "focused query")
        self.assertIn("fallback", [row["action"] for row in result["history"]])

    def test_source_candidate_paging_fetches_records_within_accept_cap(self):
        llm = FakeLLM()
        agent = WosSearchAgent(config(target_min=1, target_max=1, search_accept_max_records=3), llm)
        provider = FakePagingProvider()
        agent.provider = provider

        result = agent.search("open innovation")

        self.assertEqual(provider.pages, [1, 1])
        self.assertEqual(len(result["ranked"]), 1)

    def test_openalex_citation_expansion_traverses_until_no_high_value_neighbors(self):
        llm = FakeLLM()
        agent = WosSearchAgent(
            config(
                expand_citations=True,
                citation_seed_count=1,
                citation_per_seed=1,
                citation_max_records=10,
                citation_max_depth=3,
                citation_relevance_threshold=7,
            ),
            llm,
        )
        provider = FakeOpenAlexCitationProvider()
        agent.provider = provider

        candidates = agent._prepare_candidates("open innovation", [paper("S1")])

        self.assertEqual([doc.uid for doc in candidates], ["S1", "N1"])
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(agent.citation_map["stop_reason"], "no_high_value_neighbors")
        self.assertEqual(agent.citation_map["depth_reached"], 2)


if __name__ == "__main__":
    unittest.main()
