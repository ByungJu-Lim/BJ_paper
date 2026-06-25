import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.verify_citations import (
    extract_bibtex_keys,
    extract_citation_keys_from_markdown,
    extract_registry_keys,
    find_unverified_citations,
)


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


class TestExtractCitationKeysFromMarkdown(unittest.TestCase):
    def test_single_pandoc_citation(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text("Prior work [@smith2021boiler] showed this.", encoding="utf-8")
            self.assertEqual(extract_citation_keys_from_markdown(md_path), {"smith2021boiler"})

    def test_multiple_citations_in_one_bracket(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text("See [@smith2021boiler; @lee2022process].", encoding="utf-8")
            self.assertEqual(
                extract_citation_keys_from_markdown(md_path),
                {"smith2021boiler", "lee2022process"},
            )

    def test_non_citation_brackets_are_ignored(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text("See [Figure 1] for the setup.", encoding="utf-8")
            self.assertEqual(extract_citation_keys_from_markdown(md_path), set())


class TestFindUnverifiedCitations(unittest.TestCase):
    def test_flags_keys_missing_from_registry(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "retrieved-sources.json"
            registry_path.write_text(
                json.dumps([{"key": "smith2021boiler", "title": "t", "url": "u", "retrieved_at": "2026-06-20"}]),
                encoding="utf-8",
            )
            section_path = tmp_path / "section.md"
            section_path.write_text("Uses [@smith2021boiler] and [@fabricated2099].", encoding="utf-8")

            report = find_unverified_citations([section_path], registry_path)
            self.assertEqual(report, {str(section_path): ["fabricated2099"]})

    def test_no_unverified_citations_returns_empty_report(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "retrieved-sources.json"
            registry_path.write_text(
                json.dumps([{"key": "smith2021boiler", "title": "t", "url": "u", "retrieved_at": "2026-06-20"}]),
                encoding="utf-8",
            )
            section_path = tmp_path / "section.md"
            section_path.write_text("Uses [@smith2021boiler] only.", encoding="utf-8")

            self.assertEqual(find_unverified_citations([section_path], registry_path), {})


if __name__ == "__main__":
    unittest.main()
