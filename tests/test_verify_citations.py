import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.verify_citations import (
    extract_bibtex_keys,
    extract_citation_keys_from_markdown,
    extract_registry_keys,
    find_bibliography_metadata_mismatches,
    find_citations_missing_from_bib,
    find_unregistered_bib_entries,
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

    def test_duplicate_keys_are_rejected(self):
        with TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "retrieved-sources.json"
            registry_path.write_text(
                json.dumps([
                    {"key": "same", "title": "A", "url": "https://example.com/a", "retrieved_at": "2026-06-20"},
                    {"key": "same", "title": "B", "url": "https://example.com/b", "retrieved_at": "2026-06-21"},
                ]),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate registry key"):
                extract_registry_keys(registry_path)

    def test_invalid_registry_shape_is_rejected(self):
        with TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "retrieved-sources.json"
            registry_path.write_text('{"key": "not-a-list"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON array"):
                extract_registry_keys(registry_path)


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

    def test_same_line_entries_are_all_checked(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "refs.bib"
            path.write_text("@article{one, title={One}} @article{two, title={Two}}", encoding="utf-8")
            self.assertEqual(extract_bibtex_keys(path), {"one", "two"})

    def test_duplicate_bibtex_key_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "refs.bib"
            path.write_text("@article{one, title={One}} @article{one, title={Other}}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate bibliography key"):
                extract_bibtex_keys(path)

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

    def test_locator_and_suppress_author_citations(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text(
                "Evidence [see @smith2021boiler, pp. 3-4; -@lee2022process].",
                encoding="utf-8",
            )
            self.assertEqual(
                extract_citation_keys_from_markdown(md_path),
                {"smith2021boiler", "lee2022process"},
            )

    def test_narrative_citations_are_detected(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text(
                "@smith2021boiler argues this, while -@lee2022process suppresses the author.",
                encoding="utf-8",
            )
            self.assertEqual(
                extract_citation_keys_from_markdown(md_path),
                {"smith2021boiler", "lee2022process"},
            )

    def test_non_visible_and_non_citation_at_signs_are_ignored(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text(
                "\\@escaped and name@example.org are not citations.\n"
                "`@inline2024` is code.\n"
                "```markdown\n@fenced2025\n```\n"
                "<!-- @commented2026 -->\n"
                "Actual [@real2024].\n",
                encoding="utf-8",
            )
            self.assertEqual(extract_citation_keys_from_markdown(md_path), {"real2024"})

    def test_malformed_citation_key_subset_is_ignored(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text("Do not treat @ as a key, but keep @valid-2024_ok.", encoding="utf-8")
            self.assertEqual(extract_citation_keys_from_markdown(md_path), {"valid-2024_ok"})


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


class TestBibliographyInvariants(unittest.TestCase):
    """Invariant B (bib subset of registry) and C (citations have bib entries)."""

    def build(self, tmp: str, registry: list[dict], bib: str, section: str) -> tuple[Path, Path, Path]:
        registry_path = Path(tmp) / "retrieved-sources.json"
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        bib_path = Path(tmp) / "references.bib"
        bib_path.write_text(bib, encoding="utf-8")
        section_path = Path(tmp) / "01-introduction.md"
        section_path.write_text(section, encoding="utf-8")
        return registry_path, bib_path, section_path

    def registry_entry(self) -> dict:
        return {
            "key": "real2024",
            "title": "Real",
            "url": "https://example.org/a",
            "retrieved_at": "2026-09-05",
        }

    def test_bib_entry_absent_from_registry_is_reported(self):
        """The core hole this closes: a fabricated entry appended straight to the .bib."""
        with TemporaryDirectory() as tmp:
            registry_path, bib_path, _ = self.build(
                tmp,
                [self.registry_entry()],
                "@article{real2024, title={Real}}\n@article{fabricated2023, title={Invented}}\n",
                "Body text [@real2024].\n",
            )
            self.assertEqual(
                find_unregistered_bib_entries(bib_path, registry_path), ["fabricated2023"]
            )

    def test_fully_registered_bib_passes(self):
        with TemporaryDirectory() as tmp:
            registry_path, bib_path, _ = self.build(
                tmp,
                [self.registry_entry()],
                "@article{real2024, title={Real}}\n",
                "Body text [@real2024].\n",
            )
            self.assertEqual(find_unregistered_bib_entries(bib_path, registry_path), [])

    def test_citation_without_bib_entry_is_reported(self):
        with TemporaryDirectory() as tmp:
            _, bib_path, section_path = self.build(
                tmp,
                [self.registry_entry()],
                "@article{real2024, title={Real}}\n",
                "Claim one [@real2024] and claim two [@registered_but_not_in_bib].\n",
            )
            report = find_citations_missing_from_bib([section_path], bib_path)
            self.assertEqual(report[str(section_path)], ["registered_but_not_in_bib"])

    def test_section_with_all_citations_in_bib_passes(self):
        with TemporaryDirectory() as tmp:
            _, bib_path, section_path = self.build(
                tmp,
                [self.registry_entry()],
                "@article{real2024, title={Real}}\n@inproceedings{other2025, title={Other}}\n",
                "Claims [@real2024; @other2025] hold.\n",
            )
            self.assertEqual(find_citations_missing_from_bib([section_path], bib_path), {})


class TestBibliographyMetadata(unittest.TestCase):
    def write_registry_and_bib(self, tmp: str, entry: dict, bib: str) -> tuple[Path, Path]:
        registry_path = Path(tmp) / "retrieved-sources.json"
        registry_path.write_text(json.dumps([entry]), encoding="utf-8")
        bib_path = Path(tmp) / "references.bib"
        bib_path.write_text(bib, encoding="utf-8")
        return registry_path, bib_path

    def entry(self) -> dict:
        return {
            "key": "smith2024boiler",
            "title": "Boiler Efficiency",
            "url": "https://doi.org/10.1234/example",
            "doi": "10.1234/example",
            "retrieved_at": "2026-09-05",
            "source_type": "journal-article",
            "authors": ["Jane Smith", "Ji-Hoon Kim"],
            "year": 2024,
            "venue": "Applied Energy",
        }

    def test_matching_bibtex_metadata_passes(self):
        with TemporaryDirectory() as tmp:
            registry_path, bib_path = self.write_registry_and_bib(
                tmp,
                self.entry(),
                "@article{smith2024boiler,\n"
                "  title={Boiler Efficiency},\n"
                "  doi={10.1234/example},\n"
                "  year={2024},\n"
                "  author={Smith, Jane and Kim, Ji-Hoon},\n"
                "  journal={Applied Energy}\n"
                "}\n",
            )
            self.assertEqual(find_bibliography_metadata_mismatches(bib_path, registry_path), [])

    def test_missing_bibliographic_fields_are_rejected(self):
        with TemporaryDirectory() as tmp:
            registry, bib = self.write_registry_and_bib(tmp, self.entry(),
                "@article{smith2024boiler, title={Boiler Efficiency}}")
            errors = find_bibliography_metadata_mismatches(bib, registry)
            self.assertTrue(any("required author" in error for error in errors))
            self.assertTrue(any("required year" in error for error in errors))
            self.assertTrue(any("required doi" in error for error in errors))
            self.assertTrue(any("venue" in error for error in errors))

    def test_same_surname_different_given_name_is_rejected(self):
        with TemporaryDirectory() as tmp:
            registry, bib = self.write_registry_and_bib(tmp, self.entry(),
                "@article{smith2024boiler, title={Boiler Efficiency}, "
                "author={John Smith and Ji-Hoon Kim}, year={2024}, "
                "doi={10.1234/example}, journal={Applied Energy}}")
            self.assertTrue(any("authors differ" in error for error in
                find_bibliography_metadata_mismatches(bib, registry)))

    def test_fabricated_bibtex_fields_are_reported(self):
        with TemporaryDirectory() as tmp:
            registry_path, bib_path = self.write_registry_and_bib(
                tmp,
                self.entry(),
                "@article{smith2024boiler,\n"
                "  title={Invented Title},\n"
                "  doi={10.9999/fake},\n"
                "  year={2099},\n"
                "  author={Doe, John}\n"
                "}\n",
            )
            errors = find_bibliography_metadata_mismatches(bib_path, registry_path)
            self.assertTrue(any("title differs" in error for error in errors))
            self.assertTrue(any("DOI differs" in error for error in errors))
            self.assertTrue(any("year differs" in error for error in errors))
            self.assertTrue(any("authors differ" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
