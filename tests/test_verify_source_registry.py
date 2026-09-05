import io
import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError

from scripts.verify_source_registry import validate_registry


def http_error(code: int) -> HTTPError:
    # A real file object keeps HTTPError from emitting a ResourceWarning on cleanup.
    return HTTPError("https://api.example.org/doi", code, "error", {}, io.BytesIO(b""))


def unreachable(*_args, **_kwargs):
    raise AssertionError("network fetcher should not be called in this test")


class RegistryTestCase(unittest.TestCase):
    """Every online test injects all three fetchers so the suite never hits the network."""

    def write_registry(self, directory: str, entries: list[dict]) -> Path:
        path = Path(directory) / "retrieved-sources.json"
        path.write_text(json.dumps(entries), encoding="utf-8")
        return path

    def validate(self, path: Path, **overrides) -> list[str]:
        kwargs = {
            "online": True,
            "fetch_crossref": unreachable,
            "fetch_datacite": unreachable,
            "fetch_updates": lambda doi: [],
            "today": date(2026, 9, 5),
        }
        kwargs.update(overrides)
        return validate_registry(path, **kwargs)


class TestStructuralValidation(RegistryTestCase):
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

    def test_future_retrieved_at_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "future2027",
                "title": "Dated after today",
                "url": "https://example.org/a",
                "retrieved_at": "2027-01-01",
                "source_type": "web",
            }])
            errors = validate_registry(path, today=date(2026, 9, 5))
            self.assertTrue(any("future" in error for error in errors))

    def test_preprint_requires_a_doi(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "nodoi2026",
                "title": "Preprint without an identifier",
                "url": "https://arxiv.org/abs/2601.00001",
                "retrieved_at": "2026-09-05",
                "source_type": "preprint",
            }])
            errors = validate_registry(path)
            self.assertTrue(any("requires a DOI" in error for error in errors))


class TestDoiResolution(RegistryTestCase):
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
            errors = self.validate(
                path,
                fetch_crossref=lambda doi: {"DOI": doi, "title": ["Verified research title"]},
            )
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
            errors = self.validate(
                path,
                fetch_crossref=lambda doi: {"DOI": doi, "title": ["Verified research title"]},
            )
            self.assertEqual(errors, [])

    def test_arxiv_preprint_falls_back_to_datacite(self):
        """arXiv DOIs are registered with DataCite, so Crossref answers 404."""
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "vaswani2017attention",
                "title": "Attention Is All You Need",
                "url": "https://arxiv.org/abs/1706.03762",
                "doi": "10.48550/arXiv.1706.03762",
                "retrieved_at": "2026-09-05",
                "source_type": "preprint",
            }])

            def crossref_404(doi: str) -> dict:
                raise http_error(404)

            errors = self.validate(
                path,
                fetch_crossref=crossref_404,
                fetch_datacite=lambda doi: {"DOI": doi, "title": ["Attention Is All You Need"]},
            )
            self.assertEqual(errors, [])

    def test_doi_missing_from_both_agencies_is_reported(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "ghost2026",
                "title": "A fabricated citation",
                "url": "https://example.org/ghost",
                "doi": "10.9999/does-not-exist",
                "retrieved_at": "2026-09-05",
                "source_type": "journal-article",
            }])

            def not_found(doi: str) -> dict:
                raise http_error(404)

            errors = self.validate(path, fetch_crossref=not_found, fetch_datacite=not_found)
            self.assertEqual(errors, ["entry 'ghost2026': DOI not found in Crossref or DataCite"])


class TestRetractionScreening(RegistryTestCase):
    RETRACTED = {
        "key": "example1998retracted",
        "title": "Retracted Study",
        "url": "https://doi.org/10.1234/retracted",
        "doi": "10.1234/retracted",
        "retrieved_at": "2026-09-05",
        "source_type": "journal-article",
    }

    def metadata(self, doi: str) -> dict:
        return {"DOI": doi, "title": ["Retracted Study"]}

    def notices(self, update_type: str):
        return lambda doi: [
            {"type": update_type, "notice_doi": "10.1234/notice", "source": "retraction-watch"}
        ]

    def test_retracted_source_is_blocked(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [dict(self.RETRACTED)])
            errors = self.validate(
                path,
                fetch_crossref=self.metadata,
                fetch_updates=self.notices("retraction"),
            )
            self.assertTrue(any("flagged as retraction" in error for error in errors))

    def test_expression_of_concern_is_blocked(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [dict(self.RETRACTED)])
            errors = self.validate(
                path,
                fetch_crossref=self.metadata,
                fetch_updates=self.notices("expression_of_concern"),
            )
            self.assertTrue(any("expression_of_concern" in error for error in errors))

    def test_plain_correction_does_not_block(self):
        """A corrected paper is still citable; only retraction-grade notices block."""
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [dict(self.RETRACTED)])
            errors = self.validate(
                path,
                fetch_crossref=self.metadata,
                fetch_updates=self.notices("correction"),
            )
            self.assertEqual(errors, [])

    def test_acknowledged_retraction_is_allowed(self):
        with TemporaryDirectory() as tmp:
            entry = dict(self.RETRACTED)
            entry["retraction_ack"] = "cited as an example of research misconduct"
            path = self.write_registry(tmp, [entry])
            errors = self.validate(
                path,
                fetch_crossref=self.metadata,
                fetch_updates=self.notices("retraction"),
            )
            self.assertEqual(errors, [])

    def test_blank_acknowledgement_does_not_bypass_the_block(self):
        with TemporaryDirectory() as tmp:
            entry = dict(self.RETRACTED)
            entry["retraction_ack"] = "   "
            path = self.write_registry(tmp, [entry])
            errors = self.validate(
                path,
                fetch_crossref=self.metadata,
                fetch_updates=self.notices("retraction"),
            )
            self.assertTrue(any("flagged as retraction" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
