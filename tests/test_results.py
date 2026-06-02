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


if __name__ == "__main__":
    unittest.main()
