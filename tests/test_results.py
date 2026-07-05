import unittest

from paperseek.formatter import ranked_items_to_dict
from paperseek.providers import (
    PaperAuthor,
    PaperCitation,
    PaperIdentifiers,
    PaperKeywords,
    PaperLinks,
    PaperNames,
    PaperRecord,
    PaperSource,
)


class ResultsTest(unittest.TestCase):
    def test_ranked_items_keep_legacy_and_stable_fields(self):
        record = PaperRecord(
            uid="W123",
            title="Open Innovation on Digital Platforms",
            types=["article"],
            source=PaperSource(source_title="Research Policy", publish_year=2025),
            names=PaperNames(authors=[PaperAuthor(display_name="Ada Lovelace")]),
            links=PaperLinks(record="https://example.org/record", pdf="https://example.org/paper.pdf"),
            citations=[PaperCitation(db="OpenAlex", count=42)],
            identifiers=PaperIdentifiers(doi="10.1234/example", openalex="https://openalex.org/W123"),
            keywords=PaperKeywords(author_keywords=["open innovation", "platforms"]),
            abstract="A short abstract.",
            provider="openalex",
        )
        rows = ranked_items_to_dict([{"document": record, "score": 8.5, "reasoning": "Relevant."}])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["rank"], 1)
        self.assertEqual(row["score"], 8.5)
        self.assertEqual(row["relevance_score"], 8.5)
        self.assertEqual(row["provider"], "openalex")
        self.assertEqual(row["source"], "Research Policy")
        self.assertEqual(row["venue"], "Research Policy")
        self.assertEqual(row["publish_year"], 2025)
        self.assertEqual(row["year"], 2025)
        self.assertEqual(row["citations"], "42")
        self.assertEqual(row["citation_count"], 42)
        self.assertIn("open innovation", row["keywords"])
        self.assertIn("open innovation", row["keywords_text"])

    def test_google_scholar_summary_metadata_is_split_for_display(self):
        record = PaperRecord(
            uid="googlescholar:gs-1",
            title="Main issues on foreign investment in China's regional development",
            source=PaperSource(
                source_title="M Taube, M Ogutcu\u0431\u043d - Foreign Direct Investment in China, 2002 - books.google.com",
                publish_year=3505,
            ),
            names=PaperNames(authors=[]),
            links=PaperLinks(record="https://books.google.com/example"),
            citations=[PaperCitation(db="Google Scholar", count=66)],
            identifiers=PaperIdentifiers(),
            keywords=PaperKeywords(author_keywords=[]),
            abstract="Abstract.",
            provider="googlescholar",
        )
        rows = ranked_items_to_dict([{"document": record, "score": 9, "reasoning": "Relevant."}])
        row = rows[0]
        self.assertEqual(row["authors"], ["M Taube", "M Ogutcu"])
        self.assertEqual(row["authors_text"], "M Taube; M Ogutcu")
        self.assertEqual(row["venue"], "Foreign Direct Investment in China")
        self.assertEqual(row["source"], "Foreign Direct Investment in China")
        self.assertEqual(row["year"], 2002)
        self.assertEqual(row["publish_year"], 2002)


if __name__ == "__main__":
    unittest.main()
