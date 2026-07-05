import unittest
from types import SimpleNamespace

from paperseek_core.agent import PaperSeekAgent, _query_response_from_json, _sanitize_openalex_query
from paperseek_core.sources.providers import PaperRecord, ProviderError, ProviderSearchResult, SearchMetadata


class CapturingLlm:
    def __init__(self):
        self.calls = []
        self.last_response_info = {}

    def chat(self, messages, temperature=0.3):
        self.calls.append({"messages": messages, "temperature": temperature})
        return '{"query":"graph neural networks","rationale":"test response"}'


class SequencedLlm:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.last_response_info = {}

    def chat(self, messages, temperature=0.3):
        self.calls.append({"messages": messages, "temperature": temperature})
        if self.responses:
            return self.responses.pop(0)
        return '{"query":"graph neural networks","rationale":"fallback response"}'


class FeedbackProvider:
    def __init__(self):
        self.calls = 0

    def search(self, query, limit=50):
        self.calls += 1
        if self.calls == 1:
            return ProviderSearchResult(
                metadata=SearchMetadata(total=5, page=1, limit=limit),
                hits=[
                    PaperRecord(uid="p1", title="Digital Platform Governance and Algorithmic Control", provider="paperhub"),
                    PaperRecord(uid="p2", title="AI Governance in Online Platforms", provider="paperhub"),
                ],
            )
        return ProviderSearchResult(
            metadata=SearchMetadata(total=2, page=1, limit=limit),
            hits=[PaperRecord(uid="p3", title="Algorithmic Governance of Digital Platforms", provider="paperhub")],
        )


class EmptyProvider:
    def __init__(self):
        self.calls = 0

    def search(self, query, limit=50):
        self.calls += 1
        return ProviderSearchResult(metadata=SearchMetadata(total=0, page=1, limit=limit), hits=[])


class OpenAlexSyntaxProvider:
    def __init__(self):
        self.queries = []

    def search(self, query, limit=50, page=1, field_ids=None, lane="relevance"):
        self.queries.append(query)
        if "*" in query or query.count("(") != query.count(")"):
            raise ProviderError(
                "openalex",
                "OpenAlex returned HTTP 400.",
                status=400,
                body='{"message":"Wildcards require exact search."}',
                query=query,
            )
        return ProviderSearchResult(
            metadata=SearchMetadata(total=1, page=1, limit=limit),
            hits=[PaperRecord(uid="oa1", title="AI Governance Frameworks", provider="openalex")],
        )


class RejectOnceProvider:
    def __init__(self):
        self.queries = []

    def search(self, query, limit=50, page=1, field_ids=None, lane="relevance"):
        self.queries.append(query)
        if len(self.queries) == 1:
            raise ProviderError(
                "openalex",
                "OpenAlex returned HTTP 400.",
                status=400,
                body='{"message":"Invalid query parameters error."}',
                query=query,
            )
        return ProviderSearchResult(
            metadata=SearchMetadata(total=1, page=1, limit=limit),
            hits=[PaperRecord(uid="oa2", title="AI Policy and Governance", provider="openalex")],
        )


class QueryTotalProvider:
    def __init__(self, totals):
        self.totals = dict(totals)
        self.queries = []

    def search(self, query, limit=50, page=1, field_ids=None, lane="relevance"):
        self.queries.append(query)
        total = self.totals.get(query, 1)
        return ProviderSearchResult(
            metadata=SearchMetadata(total=total, page=1, limit=limit),
            hits=[PaperRecord(uid=f"p{len(self.queries)}", title=f"Result for {query}", provider="openalex")],
        )


class SourcePromptRoutingTest(unittest.TestCase):
    def _agent(self, source: str):
        llm = CapturingLlm()
        config = SimpleNamespace(
            data_source=source,
            discipline_fields=("17",),
            search_field="Computer Science",
            expand_citations=False,
            semantic_scholar_api_key="",
            pubmed_api_key="",
            pubmed_email="",
            pubmed_tool="paperseek",
            serper_api_key="serper-test",
        )
        return PaperSeekAgent(config, llm), llm

    def test_new_sources_use_dedicated_generation_prompts(self):
        expected_markers = {
            "arxiv": "arXiv API search_query construction",
            "semanticscholar": "Semantic Scholar Academic Graph keyword search",
            "pubmed": "PubMed ESearch term construction",
            "googlescholar": "Google Scholar searches through Serper",
            "paperhub": "computer science top-conference paper search",
        }

        for source, marker in expected_markers.items():
            with self.subTest(source=source):
                agent, llm = self._agent(source)
                agent._generate_query("graph neural networks")

                system_prompt = llm.calls[-1]["messages"][0]["content"]
                user_prompt = llm.calls[-1]["messages"][1]["content"]
                self.assertIn(marker, system_prompt)
                self.assertNotIn("academic literature search", system_prompt)
                self.assertNotIn("not JSON", system_prompt)
                self.assertNotIn("Discipline/field constraint", user_prompt)
                self.assertIn("Structured output contract", user_prompt)
                self.assertIn('"query"', user_prompt)
                self.assertIn('"rationale"', user_prompt)
                self.assertEqual(llm.calls[-1]["temperature"], 0.0)
                if source in {"semanticscholar", "pubmed", "googlescholar", "paperhub"}:
                    self.assertIn("Research field/context hint: Computer Science", user_prompt)
                else:
                    self.assertNotIn("Research field/context hint", user_prompt)

    def test_new_sources_use_dedicated_revision_prompts(self):
        expected_markers = {
            "arxiv": "arXiv API search_query construction",
            "semanticscholar": "Semantic Scholar Academic Graph keyword search",
            "pubmed": "PubMed ESearch term construction",
            "googlescholar": "Google Scholar searches through Serper",
            "paperhub": "computer science top-conference paper search",
        }

        for source, marker in expected_markers.items():
            with self.subTest(source=source, operation="broaden"):
                agent, llm = self._agent(source)
                agent._broaden_query("graph neural networks", "graph neural networks")

                system_prompt = llm.calls[-1]["messages"][0]["content"]
                user_prompt = llm.calls[-1]["messages"][1]["content"]
                self.assertIn(marker, system_prompt)
                self.assertNotIn("academic literature search", system_prompt)
                self.assertNotIn("not JSON", system_prompt)
                self.assertNotIn("Discipline/field constraint", user_prompt)
                self.assertIn("Structured output contract", user_prompt)
                self.assertIn('"query"', user_prompt)
                self.assertIn('"rationale"', user_prompt)
                self.assertEqual(llm.calls[-1]["temperature"], 0.0)
                if source in {"semanticscholar", "pubmed", "googlescholar", "paperhub"}:
                    self.assertIn("Research field/context hint: Computer Science", user_prompt)
                else:
                    self.assertNotIn("Research field/context hint", user_prompt)

            with self.subTest(source=source, operation="narrow"):
                agent, llm = self._agent(source)
                agent._narrow_query("graph neural networks", "graph neural networks")

                system_prompt = llm.calls[-1]["messages"][0]["content"]
                user_prompt = llm.calls[-1]["messages"][1]["content"]
                self.assertIn(marker, system_prompt)
                self.assertNotIn("academic literature search", system_prompt)
                self.assertNotIn("not JSON", system_prompt)
                self.assertNotIn("Discipline/field constraint", user_prompt)
                self.assertIn("Structured output contract", user_prompt)
                self.assertIn('"query"', user_prompt)
                self.assertIn('"rationale"', user_prompt)
                self.assertEqual(llm.calls[-1]["temperature"], 0.0)
                if source in {"semanticscholar", "pubmed", "googlescholar", "paperhub"}:
                    self.assertIn("Research field/context hint: Computer Science", user_prompt)
                else:
                    self.assertNotIn("Research field/context hint", user_prompt)

    def test_search_runs_intent_analysis_before_first_query_and_feeds_titles_to_revision(self):
        llm = SequencedLlm([
            '{"intent":"Find literature on AI governance in digital platforms","core_concepts":["AI governance","digital platforms"],"likely_synonyms":["algorithmic governance"],"boundaries":["generic corporate governance"],"adjustment_strategy":"Preserve both governance and platform context."}',
            '{"query":"AI governance digital platforms","rationale":"Initial query keeps both concepts."}',
            '{"query":"algorithmic governance digital platforms","rationale":"Narrowed toward algorithmic governance after title review."}',
        ])
        config = SimpleNamespace(
            data_source="paperhub",
            discipline_fields=(),
            search_field="",
            expand_citations=False,
            target_min=1,
            target_max=2,
            max_iterations=2,
            fetch_abstracts=False,
            retrieval_pool_max=3,
        )
        agent = PaperSeekAgent(config, llm)
        agent.provider = FeedbackProvider()
        agent._rank_results = lambda question, documents, **_: []

        result = agent.search("AI governance in digital platforms")

        self.assertEqual(result["final_query"], "algorithmic governance digital platforms")
        self.assertIn("literature-search analyst", llm.calls[0]["messages"][0]["content"])
        first_query_prompt = llm.calls[1]["messages"][1]["content"]
        revision_prompt = llm.calls[2]["messages"][1]["content"]
        self.assertIn("Interpreted search intent", first_query_prompt)
        self.assertIn("AI governance", first_query_prompt)
        self.assertIn("Previous source feedback", revision_prompt)
        self.assertIn("Top returned candidate titles", revision_prompt)
        self.assertIn("Digital Platform Governance and Algorithmic Control", revision_prompt)
        self.assertIn("above LLM pre-ranking safety pool", revision_prompt)
        self.assertIn("on-intent", revision_prompt)
        self.assertIn("off-intent", revision_prompt)
        self.assertIn("JSON rationale field", revision_prompt)
        self.assertIn("Structured output contract", revision_prompt)
        self.assertEqual(result["history"][0]["rationale"], "Narrowed toward algorithmic governance after title review.")

    def test_intent_is_emitted_and_returned_for_ui_audit(self):
        llm = SequencedLlm([
            '{"intent":"Find AI governance literature","core_concepts":["AI governance"],"likely_synonyms":["AI regulation"],"boundaries":[],"adjustment_strategy":"Keep governance central."}',
            '{"query":"AI governance","rationale":"Initial query keeps the central concept."}',
        ])
        config = SimpleNamespace(
            data_source="paperhub",
            discipline_fields=(),
            search_field="",
            expand_citations=False,
            target_min=1,
            target_max=5,
            max_iterations=1,
            fetch_abstracts=False,
        )
        agent = PaperSeekAgent(config, llm)
        agent.provider = FeedbackProvider()
        agent._rank_results = lambda question, documents, **_: []
        events = []

        result = agent.search("AI governance", event_handler=events.append)

        query_events = [event for event in events if event.get("type") == "stage" and event.get("stage") == "query"]
        self.assertTrue(any((event.get("data") or {}).get("intent") for event in query_events))
        self.assertIn("Find AI governance literature", result["search_intent"])

    def test_query_response_from_json_separates_query_and_rationale(self):
        raw = (
            '{"query":"(\\"AI governance\\" OR \\"AI regulation\\") AND framework",'
            '"rationale":"Narrowed toward governance frameworks after title review."}'
        )

        query, rationale = _query_response_from_json(raw)

        self.assertEqual(query, '("AI governance" OR "AI regulation") AND framework')
        self.assertEqual(rationale, "Narrowed toward governance frameworks after title review.")

    def test_query_response_from_json_extracts_json_object_only(self):
        raw = (
            'The model should not add text, but the parser only trusts JSON. '
            '{"query":"AI governance accountability","rationale":"Added accountability facet."}'
        )

        query, rationale = _query_response_from_json(raw)

        self.assertEqual(query, "AI governance accountability")
        self.assertEqual(rationale, "Added accountability facet.")

    def test_query_response_from_json_accepts_structured_query_aliases(self):
        raw = '{"search_query":"AI governance policy","rationale":"Used provider naming but still structured."}'

        query, rationale = _query_response_from_json(raw)

        self.assertEqual(query, "AI governance policy")
        self.assertEqual(rationale, "Used provider naming but still structured.")

    def test_non_json_query_output_is_not_accepted_as_query(self):
        raw = 'Thus, proposed query: ("AI governance" OR "AI policy") AND "responsible AI"'

        query, rationale = _query_response_from_json(raw)

        self.assertEqual(query, "")
        self.assertEqual(rationale, "")

    def test_openalex_query_sanitizer_removes_default_search_wildcards_without_balancing_fragments(self):
        self.assertEqual(
            _sanitize_openalex_query('("AI governance" AND (framework* OR guideline*)'),
            '("AI governance" AND (framework OR guideline)',
        )

    def test_openalex_provider_error_runs_limited_syntax_repair_retry(self):
        llm = SequencedLlm([
            '{"intent":"Find AI governance policy literature","core_concepts":["AI governance","policy"],"likely_synonyms":["regulation"],"boundaries":[],"adjustment_strategy":"Keep AI governance central."}',
            '{"query":"AI governance policy","rationale":"Initial query keeps governance and policy."}',
            '{"query":"AI governance regulation policy","rationale":"Repaired after provider syntax rejection."}',
        ])
        config = SimpleNamespace(
            data_source="openalex",
            discipline_fields=(),
            search_field="",
            expand_citations=False,
            target_min=1,
            target_max=5,
            max_iterations=1,
            fetch_abstracts=False,
            openalex_api_key="",
            openalex_email="",
        )
        agent = PaperSeekAgent(config, llm)
        provider = RejectOnceProvider()
        agent.provider = provider
        agent._retrieve_candidates = lambda question, query, hits: hits
        agent._rank_results = lambda question, documents, **_: []

        result = agent.search("AI governance policy")

        self.assertEqual(provider.queries, ["AI governance policy", "AI governance regulation policy"])
        self.assertEqual(result["total"], 1)

    def test_openalex_sanitizer_runs_before_provider_request(self):
        llm = SequencedLlm([
            '{"intent":"Find AI governance frameworks","core_concepts":["AI governance","frameworks"],"likely_synonyms":["guidelines"],"boundaries":[],"adjustment_strategy":"Keep governance and framework terms."}',
            '{"query":"(\\"AI governance\\" AND (framework* OR guideline*))","rationale":"Initial query uses framework synonyms."}',
        ])
        config = SimpleNamespace(
            data_source="openalex",
            discipline_fields=(),
            search_field="",
            expand_citations=False,
            target_min=1,
            target_max=5,
            max_iterations=1,
            fetch_abstracts=False,
            openalex_api_key="",
            openalex_email="",
        )
        agent = PaperSeekAgent(config, llm)
        provider = OpenAlexSyntaxProvider()
        agent.provider = provider
        agent._retrieve_candidates = lambda question, query, hits: hits
        agent._rank_results = lambda question, documents, **_: []

        result = agent.search("AI governance frameworks")

        self.assertEqual(provider.queries, ['("AI governance" AND (framework OR guideline))'])
        self.assertEqual(result["total"], 1)

    def test_malformed_openalex_revision_is_retried_without_requesting_fragment(self):
        llm = SequencedLlm([
            '{"intent":"Find AI governance frameworks","core_concepts":["AI governance","frameworks"],"likely_synonyms":["guidelines"],"boundaries":[],"adjustment_strategy":"Keep governance and framework terms."}',
            '{"query":"\\"AI governance\\" framework","rationale":"Initial query keeps topic and framework."}',
            '{"query":"(\\"AI governance\\" OR \\"artificial intelligence governance","rationale":"Attempted to broaden governance phrase."}',
            '{"query":"(\\"AI governance\\" OR \\"artificial intelligence governance\\") AND accountability","rationale":"Replaced malformed query with a balanced accountability query."}',
        ])
        config = SimpleNamespace(
            data_source="openalex",
            discipline_fields=(),
            search_field="",
            expand_citations=False,
            target_min=1,
            target_max=50,
            max_iterations=1,
            fetch_abstracts=False,
            openalex_api_key="",
            openalex_email="",
            retrieval_pool_max=3000,
        )
        agent = PaperSeekAgent(config, llm)
        provider = QueryTotalProvider({
            '"AI governance" framework': 1000000,
            '("AI governance" OR "artificial intelligence governance") AND accountability': 20,
        })
        agent.provider = provider
        agent._retrieve_candidates = lambda question, query, hits: hits
        agent._rank_results = lambda question, documents, **_: []

        result = agent.search("AI governance frameworks")

        self.assertEqual(provider.queries, [
            '"AI governance" framework',
            '("AI governance" OR "artificial intelligence governance") AND accountability',
        ])
        self.assertEqual(result["total"], 20)

    def test_unchanged_huge_narrowing_gets_second_distinct_attempt(self):
        llm = SequencedLlm([
            '{"intent":"Find AI governance accountability literature","core_concepts":["AI governance","accountability"],"likely_synonyms":["responsible AI"],"boundaries":[],"adjustment_strategy":"Narrow with accountability facets."}',
            '{"query":"AI governance","rationale":"Initial broad query."}',
            '{"query":"AI governance","rationale":"Could not improve on first narrow attempt."}',
            '{"query":"AI governance accountability compliance","rationale":"Added accountability and compliance facets after unchanged attempt."}',
        ])
        config = SimpleNamespace(
            data_source="openalex",
            discipline_fields=(),
            search_field="",
            expand_citations=False,
            target_min=1,
            target_max=50,
            max_iterations=1,
            fetch_abstracts=False,
            openalex_api_key="",
            openalex_email="",
            retrieval_pool_max=3000,
        )
        agent = PaperSeekAgent(config, llm)
        provider = QueryTotalProvider({
            "AI governance": 955068,
            "AI governance accountability compliance": 42,
        })
        agent.provider = provider
        agent._retrieve_candidates = lambda question, query, hits: hits
        agent._rank_results = lambda question, documents, **_: []

        result = agent.search("AI governance")

        self.assertEqual(provider.queries, ["AI governance", "AI governance accountability compliance"])
        self.assertEqual(result["history"][0]["action"], "narrow")
        self.assertEqual(result["total"], 42)

    def test_reasoning_revision_is_retried_instead_of_requested(self):
        llm = SequencedLlm([
            '{"intent":"Find AI governance frameworks","core_concepts":["AI governance","frameworks"],"likely_synonyms":["guidelines"],"boundaries":[],"adjustment_strategy":"Keep governance and framework terms."}',
            '{"query":"\\"AI governance\\" framework","rationale":"Initial query keeps governance and framework."}',
            'Maybe I can require that "AI" appears with a governance term in a phrase like "AI governance". But that might be too restrictive.',
            '{"query":"\\"AI governance\\" accountability framework","rationale":"Added accountability facet while keeping framework."}',
        ])
        config = SimpleNamespace(
            data_source="openalex",
            discipline_fields=(),
            search_field="",
            expand_citations=False,
            target_min=1,
            target_max=50,
            max_iterations=1,
            fetch_abstracts=False,
            openalex_api_key="",
            openalex_email="",
            retrieval_pool_max=3000,
        )
        agent = PaperSeekAgent(config, llm)
        provider = QueryTotalProvider({
            '"AI governance" framework': 1000000,
            '"AI governance" accountability framework': 20,
        })
        agent.provider = provider
        agent._retrieve_candidates = lambda question, query, hits: hits
        agent._rank_results = lambda question, documents, **_: []

        result = agent.search("AI governance frameworks")

        self.assertEqual(provider.queries, ['"AI governance" framework', '"AI governance" accountability framework'])
        self.assertEqual(result["total"], 20)

    def test_but_note_revision_is_retried_instead_of_requested(self):
        llm = SequencedLlm([
            '{"intent":"Find AI governance policy frameworks","core_concepts":["AI governance","policy frameworks"],"likely_synonyms":["responsible AI"],"boundaries":[],"adjustment_strategy":"Keep policy and framework facets."}',
            '{"query":"\\"AI governance\\" policy framework","rationale":"Initial query keeps governance and policy framework."}',
            'But note: the word "governance" might appear in many papers that are not about AI governance. So it should be fine.',
            '{"query":"\\"AI governance\\" \\"policy framework\\" accountability","rationale":"Added accountability while keeping policy framework."}',
        ])
        config = SimpleNamespace(
            data_source="openalex",
            discipline_fields=(),
            search_field="",
            expand_citations=False,
            target_min=1,
            target_max=50,
            max_iterations=1,
            fetch_abstracts=False,
            openalex_api_key="",
            openalex_email="",
            retrieval_pool_max=3000,
        )
        agent = PaperSeekAgent(config, llm)
        provider = QueryTotalProvider({
            '"AI governance" policy framework': 1000000,
            '"AI governance" "policy framework" accountability': 20,
        })
        agent.provider = provider
        agent._retrieve_candidates = lambda question, query, hits: hits
        agent._rank_results = lambda question, documents, **_: []

        result = agent.search("AI governance policy frameworks")

        self.assertEqual(provider.queries, ['"AI governance" policy framework', '"AI governance" "policy framework" accountability'])
        self.assertEqual(result["total"], 20)

    def test_unchanged_revision_stops_without_repeating_same_request(self):
        llm = SequencedLlm([
            '{"intent":"Find graph neural network papers","core_concepts":["graph neural networks"],"likely_synonyms":["GNN"],"boundaries":[],"adjustment_strategy":"Broaden with common synonyms."}',
            '{"query":"graph neural networks","rationale":"Initial query keeps central concept."}',
            '{"query":"graph neural networks","rationale":"No broader query available without drifting."}',
        ])
        config = SimpleNamespace(
            data_source="paperhub",
            discipline_fields=(),
            search_field="",
            expand_citations=False,
            target_min=1,
            target_max=5,
            max_iterations=3,
            fetch_abstracts=False,
        )
        agent = PaperSeekAgent(config, llm)
        provider = EmptyProvider()
        agent.provider = provider
        agent._rank_results = lambda question, documents, **_: []

        result = agent.search("graph neural networks")

        self.assertEqual(provider.calls, 1)
        self.assertEqual(result["history"][-1]["action"], "empty")
        self.assertIn("unchanged", result["history"][-1]["message"])


if __name__ == "__main__":
    unittest.main()
