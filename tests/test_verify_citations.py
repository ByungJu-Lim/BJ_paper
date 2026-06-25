import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.verify_citations import extract_bibtex_keys, extract_registry_keys


class TestExtractRegistryKeys(unittest.TestCase):
    def test_reads_keys_from_registry_json(self):
        with TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "retrieved-sources.json"
            registry_path.write_text(
                json.dumps(
                    [
                        {"key": "smith2021boiler", "title": "Boiler Efficiency", "url": "https://example.com/a", "retrieved_at": "2026-06-20"},
                        {"key": "lee2022process", "title": "Process Analysis", "url": "https://example.com/b", "retrieved_at": "2026-06-21"},
                    ]
                ),
                encoding="utf-8",
            )
            self.assertEqual(extract_registry_keys(registry_path), {"smith2021boiler", "lee2022process"})

    def test_empty_registry_returns_empty_set(self):
        with TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "retrieved-sources.json"
            registry_path.write_text("[]", encoding="utf-8")
            self.assertEqual(extract_registry_keys(registry_path), set())


class TestExtractBibtexKeys(unittest.TestCase):
    def test_reads_keys_from_multiple_entry_types(self):
        with TemporaryDirectory() as tmp:
            bib_path = Path(tmp) / "references.bib"
            bib_path.write_text(
                "@article{smith2021boiler,\n  title = {Boiler Efficiency},\n}\n"
                "@inproceedings{lee2022process,\n  title = {Process Analysis},\n}\n",
                encoding="utf-8",
            )
            self.assertEqual(extract_bibtex_keys(bib_path), {"smith2021boiler", "lee2022process"})

    def test_comment_only_file_returns_empty_set(self):
        with TemporaryDirectory() as tmp:
            bib_path = Path(tmp) / "references.bib"
            bib_path.write_text("% no entries yet\n", encoding="utf-8")
            self.assertEqual(extract_bibtex_keys(bib_path), set())


if __name__ == "__main__":
    unittest.main()
