import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.verify_source_registry import validate_registry


class TestValidateRegistry(unittest.TestCase):
    def write_registry(self, directory: str, entries: list[dict]) -> Path:
        path = Path(directory) / "retrieved-sources.json"
        path.write_text(json.dumps(entries), encoding="utf-8")
        return path

    def test_valid_non_doi_source_passes_structural_validation(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "nist2024genai",
                "title": "Artificial Intelligence Risk Management Framework",
                "url": "https://www.nist.gov/itl/ai-risk-management-framework",
                "retrieved_at": "2026-09-05",
                "source_type": "standard",
            }])
            self.assertEqual(validate_registry(path), [])

    def test_invalid_url_and_date_are_reported(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "bad",
                "title": "Bad source",
                "url": "not-a-url",
                "retrieved_at": "yesterday",
                "source_type": "web",
            }])
            errors = validate_registry(path)
            self.assertTrue(any("URL" in error for error in errors))
            self.assertTrue(any("retrieved_at" in error for error in errors))

    def test_crossref_title_mismatch_is_reported(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "smith2024",
                "title": "Completely different title",
                "url": "https://doi.org/10.1234/example",
                "doi": "10.1234/example",
                "retrieved_at": "2026-09-05",
                "source_type": "journal-article",
            }])

            def fake_fetch(doi: str) -> dict:
                self.assertEqual(doi, "10.1234/example")
                return {"DOI": doi, "title": ["Verified research title"]}

            errors = validate_registry(path, online=True, fetch_crossref=fake_fetch)
            self.assertTrue(any("title does not match Crossref" in error for error in errors))

    def test_crossref_verified_doi_passes(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "smith2024",
                "title": "Verified Research Title",
                "url": "https://doi.org/10.1234/example",
                "doi": "https://doi.org/10.1234/example",
                "retrieved_at": "2026-09-05",
                "source_type": "journal-article",
            }])

            errors = validate_registry(
                path,
                online=True,
                fetch_crossref=lambda doi: {"DOI": doi, "title": ["Verified research title"]},
            )
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
