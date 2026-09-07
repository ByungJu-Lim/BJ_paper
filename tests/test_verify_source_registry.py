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
            "fetch_siblings": lambda title: [],
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
                "access": "full-text",
                "authors": ["NIST"],
                "year": 2024,
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
                "access": "full-text",
                "authors": ["Example Org"],
                "year": 2026,
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
                "access": "full-text",
                "authors": ["Example Org"],
                "year": 2027,
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
                "access": "full-text",
                "authors": ["No Doi"],
                "year": 2026,
                "venue": "arXiv",
            }])
            errors = validate_registry(path)
            self.assertTrue(any("requires a DOI" in error for error in errors))

    def test_doi_sources_require_canonical_bibliographic_fields(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "thin2026",
                "title": "Missing Metadata",
                "url": "https://doi.org/10.1234/thin",
                "doi": "10.1234/thin",
                "retrieved_at": "2026-09-05",
                "source_type": "journal-article",
                "access": "full-text",
            }])
            errors = validate_registry(path)
            self.assertTrue(any("authors must be" in error for error in errors))
            self.assertTrue(any("year must be" in error for error in errors))
            self.assertTrue(any("venue must be" in error for error in errors))

    def test_web_sources_do_not_require_venue(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "web2026",
                "title": "A Web Source",
                "url": "https://example.org/source",
                "retrieved_at": "2026-09-05",
                "source_type": "web",
                "access": "full-text",
                "authors": ["Example Org"],
                "year": 2026,
            }])
            self.assertEqual(validate_registry(path, today=date(2026, 9, 5)), [])


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
                "access": "full-text",
                "authors": ["Jane Smith"],
                "year": 2024,
                "venue": "Journal of Examples",
            }])
            errors = self.validate(
                path,
                fetch_crossref=lambda doi: {"DOI": doi, "title": ["Verified research title"], "author": [{"given": "Jane", "family": "Smith"}], "published": {"date-parts": [[2024]]}, "container-title": ["Journal of Examples"]},
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
                "access": "full-text",
                "authors": ["Jane Smith"],
                "year": 2024,
                "venue": "Journal of Examples",
            }])
            errors = self.validate(
                path,
                fetch_crossref=lambda doi: {"DOI": doi, "title": ["Verified research title"], "author": [{"given": "Jane", "family": "Smith"}], "published": {"date-parts": [[2024]]}, "container-title": ["Journal of Examples"]},
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
                "access": "full-text",
                "authors": ["Ashish Vaswani"],
                "year": 2017,
                "venue": "arXiv",
            }])

            def crossref_404(doi: str) -> dict:
                raise http_error(404)

            errors = self.validate(
                path,
                fetch_crossref=crossref_404,
                fetch_datacite=lambda doi: {"DOI": doi, "title": ["Attention Is All You Need"], "creators": [{"name": "Vaswani, Ashish"}], "publicationYear": 2017, "publisher": "arXiv"},
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
                "access": "full-text",
                "authors": ["Ghost Writer"],
                "year": 2026,
                "venue": "Journal of Examples",
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
        "access": "full-text",
        "authors": ["Jane Smith"],
        "year": 1998,
        "venue": "Journal of Examples",
    }

    def metadata(self, doi: str) -> dict:
        return {"DOI": doi, "title": ["Retracted Study"], "author": [{"given": "Jane", "family": "Smith"}], "published": {"date-parts": [[1998]]}, "container-title": ["Journal of Examples"]}

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
                fetch_updates=self.notices("expression-of-concern"),
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

    def test_duplicate_record_of_a_retracted_article_is_caught(self):
        """Publishers mint second DOIs that carry neither the marker nor the notice."""
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [dict(self.RETRACTED)])
            errors = self.validate(
                path,
                fetch_crossref=self.metadata,
                fetch_updates=lambda doi: [],
                fetch_siblings=lambda title: [
                    {"DOI": "10.1234/original", "title": ["RETRACTED: Retracted Study"]}
                ],
            )
            self.assertTrue(any("marked retracted" in error for error in errors))

    def test_unrelated_same_field_title_is_not_flagged(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [dict(self.RETRACTED)])
            errors = self.validate(
                path,
                fetch_crossref=self.metadata,
                fetch_updates=lambda doi: [],
                fetch_siblings=lambda title: [
                    {"DOI": "10.1234/other", "title": ["RETRACTED: A Completely Different Paper"]}
                ],
            )
            self.assertEqual(errors, [])

    def test_acknowledged_retraction_skips_duplicate_screening(self):
        with TemporaryDirectory() as tmp:
            entry = dict(self.RETRACTED)
            entry["retraction_ack"] = "discussed as a case of research misconduct"
            path = self.write_registry(tmp, [entry])
            errors = self.validate(
                path,
                fetch_crossref=self.metadata,
                fetch_updates=lambda doi: [],
                fetch_siblings=unreachable,
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


class TestFullTextAccess(RegistryTestCase):
    def entry(self, **overrides) -> dict:
        base = {
            "key": "smith2024boiler",
            "title": "Boiler Efficiency",
            "url": "https://example.org/a",
            "retrieved_at": "2026-09-05",
            "source_type": "report",
            "access": "full-text",
            "authors": ["Jane Smith"],
            "year": 2024,
        }
        base.update(overrides)
        return base

    def test_missing_access_is_reported(self):
        with TemporaryDirectory() as tmp:
            entry = self.entry()
            del entry["access"]
            path = self.write_registry(tmp, [entry])
            errors = validate_registry(path)
            self.assertTrue(any("access must be one of" in error for error in errors))

    def test_unknown_access_level_is_reported(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [self.entry(access="skimmed-it")])
            errors = validate_registry(path)
            self.assertTrue(any("access must be one of" in error for error in errors))

    def test_abstract_only_is_allowed(self):
        """Some claims genuinely rest on the abstract; the point is to record which."""
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [self.entry(access="abstract-only")])
            self.assertEqual(validate_registry(path), [])

    def test_awaiting_user_file_blocks_and_names_the_path(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [self.entry(access="awaiting-user-file")])
            errors = validate_registry(path)
            self.assertEqual(len(errors), 1)
            self.assertIn("ask the user to download", errors[0])
            self.assertIn("docs/sources/smith2024boiler.pdf", errors[0])

    def test_declared_local_file_must_exist(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(
                tmp, [self.entry(local_file="docs/sources/smith2024boiler.pdf")]
            )
            errors = validate_registry(path, root=Path(tmp))
            self.assertTrue(any("does not exist" in error for error in errors))

    def test_present_local_file_passes(self):
        with TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "docs" / "sources" / "smith2024boiler.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF-1.4")
            path = self.write_registry(
                tmp, [self.entry(local_file="docs/sources/smith2024boiler.pdf")]
            )
            self.assertEqual(validate_registry(path, root=Path(tmp)), [])

    def test_local_file_must_remain_inside_root(self):
        with TemporaryDirectory() as tmp:
            outside = Path(tmp).parent / "outside-paper-source.pdf"
            outside.write_bytes(b"%PDF-1.4")
            try:
                path = self.write_registry(tmp, [self.entry(local_file="../outside-paper-source.pdf")])
                errors = validate_registry(path, root=Path(tmp))
                self.assertTrue(any("must stay inside" in error for error in errors))
            finally:
                outside.unlink(missing_ok=True)


class TestOnlineBibliographicMetadata(RegistryTestCase):
    ENTRY = {
        "key": "smith2024boiler",
        "title": "Boiler Efficiency",
        "url": "https://doi.org/10.1234/example",
        "doi": "10.1234/example",
        "retrieved_at": "2026-09-05",
        "source_type": "journal-article",
        "access": "full-text",
        "authors": ["Jane Smith", "Ji-Hoon Kim"],
        "year": 2024,
        "venue": "Applied Energy",
    }

    def test_online_metadata_confirms_author_year_and_venue(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [dict(self.ENTRY)])
            errors = self.validate(
                path,
                fetch_crossref=lambda doi: {
                    "DOI": doi,
                    "title": ["Boiler Efficiency"],
                    "author": [
                        {"given": "Jane", "family": "Smith"},
                        {"given": "Ji-Hoon", "family": "Kim"},
                    ],
                    "published-print": {"date-parts": [[2024]]},
                    "container-title": ["Applied Energy"],
                },
            )
            self.assertEqual(errors, [])

    def test_online_missing_metadata_fails_closed(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [dict(self.ENTRY)])
            errors = self.validate(path, fetch_crossref=lambda doi: {
                "DOI": doi, "title": ["Boiler Efficiency"]})
            self.assertTrue(any("authors missing" in error for error in errors))
            self.assertTrue(any("year missing" in error for error in errors))
            self.assertTrue(any("venue missing" in error for error in errors))

    def test_online_metadata_mismatch_is_reported(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [dict(self.ENTRY)])
            errors = self.validate(
                path,
                fetch_crossref=lambda doi: {
                    "DOI": doi,
                    "title": ["Boiler Efficiency"],
                    "author": [{"given": "John", "family": "Doe"}],
                    "published-print": {"date-parts": [[2025]]},
                    "container-title": ["Invented Journal"],
                },
            )
            self.assertTrue(any("authors do not match" in error for error in errors))
            self.assertTrue(any("year does not match" in error for error in errors))
            self.assertTrue(any("venue does not match" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
