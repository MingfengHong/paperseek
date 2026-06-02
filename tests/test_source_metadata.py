import unittest

from paperseek.source_metadata import get_source_metadata, list_source_metadata, supported_source_ids


class SourceMetadataTest(unittest.TestCase):
    def test_registered_sources_are_ordered_and_descriptive(self):
        sources = list_source_metadata()
        self.assertEqual([item["id"] for item in sources], ["openalex", "crossref", "wos"])
        self.assertIn("openalex", supported_source_ids())
        self.assertTrue(get_source_metadata("openalex").supports_citation_expansion)
        self.assertFalse(get_source_metadata("crossref").supports_citation_expansion)
        self.assertEqual(get_source_metadata("wos").api_key, "required")


if __name__ == "__main__":
    unittest.main()
