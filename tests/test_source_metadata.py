import unittest

from paperseek.source_metadata import get_source_metadata, list_source_metadata, supported_source_ids


class SourceMetadataTest(unittest.TestCase):
    def test_registered_sources_are_ordered_and_descriptive(self):
        sources = list_source_metadata()
        self.assertEqual([item["id"] for item in sources], ["openalex", "arxiv", "semanticscholar", "pubmed", "paperhub", "crossref", "wos"])
        self.assertIn("openalex", supported_source_ids())
        self.assertTrue(get_source_metadata("openalex").supports_citation_expansion)
        self.assertTrue(get_source_metadata("arxiv").supports_pdf_links)
        self.assertEqual(get_source_metadata("semanticscholar").api_key, "optional")
        self.assertIn("PUBMED_EMAIL", get_source_metadata("pubmed").optional_config)
        self.assertEqual(get_source_metadata("paperhub").api_key, "not_required")
        self.assertFalse(get_source_metadata("crossref").supports_citation_expansion)
        self.assertEqual(get_source_metadata("wos").api_key, "required")


if __name__ == "__main__":
    unittest.main()
