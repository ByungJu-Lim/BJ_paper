import io
import json
import os
import unittest
from contextlib import redirect_stderr
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

    def test_html_escaped_crossref_metadata_matches_plain_registry_text(self):
        """Crossref returns "Computers &amp; Chemical Engineering"; the registry spells
        the venue with a literal ampersand. Both must normalize to the same string, or
        every Elsevier journal with "&" in its name fails venue verification."""
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [{
                "key": "gallup2023physics",
                "title": "Physics-guided neural networks & hybrid process modeling",
                "url": "https://doi.org/10.1234/example",
                "doi": "https://doi.org/10.1234/example",
                "retrieved_at": "2026-09-05",
                "source_type": "journal-article",
                "access": "full-text",
                "authors": ["Ethan Gallup"],
                "year": 2023,
                "venue": "Computers & Chemical Engineering",
            }])
            errors = self.validate(
                path,
                fetch_crossref=lambda doi: {
                    "DOI": doi,
                    "title": ["Physics-guided neural networks &amp; hybrid process modeling"],
                    "author": [{"given": "Ethan", "family": "Gallup"}],
                    "published": {"date-parts": [[2023]]},
                    "container-title": ["Computers &amp; Chemical Engineering"],
                },
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


class TestLocatorMetadata(RegistryTestCase):
    """Optional volume, issue, and pages must match Crossref before they reach the bib."""

    ENTRY = TestOnlineBibliographicMetadata.ENTRY

    def entry(self, **locators) -> dict:
        entry = dict(self.ENTRY)
        entry.update(locators)
        return entry

    def crossref(self, **locators):
        def fetch(doi: str) -> dict:
            metadata = {
                "DOI": doi,
                "title": ["Boiler Efficiency"],
                "author": [
                    {"given": "Jane", "family": "Smith"},
                    {"given": "Ji-Hoon", "family": "Kim"},
                ],
                "published-print": {"date-parts": [[2024]]},
                "container-title": ["Applied Energy"],
            }
            metadata.update(locators)
            return metadata
        return fetch

    def test_non_string_or_blank_locators_are_rejected_offline(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [self.entry(volume=12, issue="  ", pages=None)])
            errors = validate_registry(path)
            self.assertTrue(any("volume must be a non-empty string" in error for error in errors))
            self.assertTrue(any("issue must be a non-empty string" in error for error in errors))
            self.assertTrue(any("pages must be a non-empty string" in error for error in errors))

    def test_locators_are_optional(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [self.entry()])
            errors = self.validate(path, fetch_crossref=self.crossref(volume="12", page="1-9"))
            self.assertEqual(errors, [])

    def test_matching_locators_pass_regardless_of_dash_style(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(
                tmp, [self.entry(volume="59", issue="9", pages="1713--1720")]
            )
            errors = self.validate(
                path, fetch_crossref=self.crossref(volume="59", issue="9", page="1713–1720")
            )
            self.assertEqual(errors, [])

    def test_pages_may_match_the_crossref_article_number(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [self.entry(volume="12", issue="4", pages="044501")])
            errors = self.validate(
                path,
                fetch_crossref=self.crossref(volume="12", issue="4", **{"article-number": "044501"}),
            )
            self.assertEqual(errors, [])

    def test_mismatched_locators_are_reported(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [self.entry(volume="60", issue="2", pages="1-10")])
            errors = self.validate(
                path,
                fetch_crossref=self.crossref(
                    volume="59", issue="9", page="1713-1720", **{"article-number": "e1"}
                ),
            )
            self.assertTrue(any("volume '60' does not match Crossref" in error for error in errors))
            self.assertTrue(any("issue '2' does not match Crossref" in error for error in errors))
            self.assertTrue(any("pages '1-10' does not match Crossref" in error for error in errors))

    def test_locator_absent_from_crossref_is_reported(self):
        with TemporaryDirectory() as tmp:
            path = self.write_registry(tmp, [self.entry(volume="12", issue="4", pages="7")])
            errors = self.validate(path, fetch_crossref=self.crossref(volume="12"))
            self.assertTrue(any("issue '4' is not in Crossref metadata" in error for error in errors))
            self.assertTrue(any("pages '7' is not in Crossref metadata" in error for error in errors))
            self.assertFalse(any("volume" in error for error in errors))

    def test_datacite_resolved_doi_skips_locator_comparison(self):
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
                "volume": "1",
                "pages": "1-15",
            }])

            def crossref_404(doi: str) -> dict:
                raise http_error(404)

            errors = self.validate(
                path,
                fetch_crossref=crossref_404,
                fetch_datacite=lambda doi: {"DOI": doi, "title": ["Attention Is All You Need"], "creators": [{"name": "Vaswani, Ashish"}], "publicationYear": 2017, "publisher": "arXiv"},
            )
            self.assertEqual(errors, [])


class TestMetadataException(RegistryTestCase):
    """A documented, auditable way past a defective agency author record - and nothing else."""

    PDF = "docs/sources/smith2024boiler.pdf"

    def entry(self, **overrides) -> dict:
        base = {
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
            "local_file": self.PDF,
            "metadata_exception": {
                "fields": ["authors"],
                "reason": "Crossref lists only the first author; the PDF lists two",
                "evidence": f"{self.PDF}#page=1",
            },
        }
        base.update(overrides)
        return base

    def exception(self, **overrides) -> dict:
        value = dict(self.entry()["metadata_exception"])
        value.update(overrides)
        return value

    def metadata(self, doi: str, **overrides) -> dict:
        record = {
            "DOI": doi,
            "title": ["Boiler Efficiency"],
            "author": [{"given": "J", "family": "SMITH"}],
            "published-print": {"date-parts": [[2024]]},
            "container-title": ["Applied Energy"],
        }
        record.update(overrides)
        return record

    def setup_repo(self, tmp: str, entries: list[dict]) -> Path:
        pdf = Path(tmp) / self.PDF
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(b"%PDF-1.4")
        return self.write_registry(tmp, entries)

    def test_author_exception_passes_with_a_visible_warning(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(tmp, [self.entry()])
            warnings: list[str] = []
            errors = self.validate(
                path, root=Path(tmp), warnings=warnings, fetch_crossref=self.metadata
            )
            self.assertEqual(errors, [])
            self.assertEqual(len(warnings), 1)
            self.assertIn("smith2024boiler", warnings[0])
            self.assertIn("SKIPPED", warnings[0])
            self.assertIn("Crossref lists only the first author", warnings[0])
            self.assertIn(f"{self.PDF}#page=1", warnings[0])

    def test_author_exception_covers_agency_record_without_authors(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(tmp, [self.entry()])
            warnings: list[str] = []
            errors = self.validate(
                path,
                root=Path(tmp),
                warnings=warnings,
                fetch_crossref=lambda doi: self.metadata(doi, author=[]),
            )
            self.assertEqual(errors, [])
            self.assertIn("lists: (none)", warnings[0])

    def test_warning_goes_to_stderr_when_no_list_is_given(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(tmp, [self.entry()])
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                errors = self.validate(path, root=Path(tmp), fetch_crossref=self.metadata)
            self.assertEqual(errors, [])
            self.assertIn("WARNING: entry 'smith2024boiler'", stderr.getvalue())

    def test_url_evidence_is_accepted_without_a_local_file(self):
        with TemporaryDirectory() as tmp:
            entry = self.entry(
                access="abstract-only",
                metadata_exception=self.exception(evidence="https://www.osti.gov/biblio/1"),
            )
            del entry["local_file"]
            path = self.write_registry(tmp, [entry])
            warnings: list[str] = []
            errors = self.validate(
                path, root=Path(tmp), warnings=warnings, fetch_crossref=self.metadata
            )
            self.assertEqual(errors, [])
            self.assertEqual(len(warnings), 1)

    def test_unneeded_exception_is_flagged_in_a_warning(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(tmp, [self.entry()])
            warnings: list[str] = []
            errors = self.validate(
                path,
                root=Path(tmp),
                warnings=warnings,
                fetch_crossref=lambda doi: self.metadata(doi, author=[
                    {"given": "Jane", "family": "Smith"},
                    {"given": "Ji-Hoon", "family": "Kim"},
                ]),
            )
            self.assertEqual(errors, [])
            self.assertIn("no longer needed", warnings[0])

    def test_exception_on_a_non_author_field_is_rejected(self):
        for field in ("title", "year", "venue", "doi"):
            with self.subTest(field=field), TemporaryDirectory() as tmp:
                path = self.setup_repo(
                    tmp, [self.entry(metadata_exception=self.exception(fields=["authors", field]))]
                )
                errors = validate_registry(path, root=Path(tmp))
                self.assertTrue(any("cannot be excepted" in error for error in errors))

    def test_rejected_exception_excuses_nothing_online(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(
                tmp, [self.entry(metadata_exception=self.exception(fields=["title"]))]
            )
            warnings: list[str] = []
            errors = self.validate(
                path, root=Path(tmp), warnings=warnings, fetch_crossref=self.metadata
            )
            self.assertTrue(any("cannot be excepted" in error for error in errors))
            self.assertTrue(any("authors do not match" in error for error in errors))
            self.assertEqual(warnings, [])

    def test_missing_or_invalid_evidence_is_rejected(self):
        not_local = "must point at this entry's local_file"
        cases = {
            "missing": ({"evidence": None}, "evidence must be a non-empty string"),
            "blank": ({"evidence": "  "}, "evidence must be a non-empty string"),
            "no page": ({"evidence": self.PDF}, "#page=<N>"),
            "page zero": ({"evidence": f"{self.PDF}#page=0"}, "#page=<N>"),
            "other file": ({"evidence": "docs/sources/other.pdf#page=1"}, not_local),
            "trailing space": ({"evidence": f"{self.PDF} #page=1"}, not_local),
            "url despite local file": ({"evidence": "https://example.org/paper.pdf"}, "#page=<N>"),
        }
        for name, (override, message) in cases.items():
            with self.subTest(case=name), TemporaryDirectory() as tmp:
                exception = self.exception(**override)
                if exception["evidence"] is None:
                    del exception["evidence"]
                path = self.setup_repo(tmp, [self.entry(metadata_exception=exception)])
                (Path(tmp) / "docs/sources/other.pdf").write_bytes(b"%PDF-1.4")
                errors = validate_registry(path, root=Path(tmp))
                self.assertTrue(
                    any(message in error and "metadata_exception" in error for error in errors),
                    errors,
                )

    def test_evidence_file_must_exist(self):
        with TemporaryDirectory() as tmp:
            # local_file and evidence agree, but neither file was created.
            path = self.write_registry(tmp, [self.entry()])
            errors = validate_registry(path, root=Path(tmp))
            self.assertTrue(
                any("evidence file" in error and "does not exist" in error for error in errors),
                errors,
            )

    def test_evidence_outside_the_repository_is_rejected(self):
        with TemporaryDirectory() as outside_dir, TemporaryDirectory() as tmp:
            outside = Path(outside_dir) / "outside.pdf"
            outside.write_bytes(b"%PDF-1.4")
            relative = Path(os.path.relpath(outside, Path(tmp).resolve())).as_posix()
            self.assertTrue(relative.startswith(".."), relative)
            for name, evidence in {
                "relative": f"{relative}#page=1",
                "absolute": f"{outside.resolve().as_posix()}#page=1",
            }.items():
                with self.subTest(case=name):
                    path = self.setup_repo(
                        tmp, [self.entry(metadata_exception=self.exception(evidence=evidence))]
                    )
                    errors = validate_registry(path, root=Path(tmp))
                    self.assertTrue(
                        any(
                            "metadata_exception.evidence must stay inside" in error
                            for error in errors
                        ),
                        errors,
                    )

    def test_evidence_must_be_the_entry_local_file_not_another_repo_file(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(tmp, [self.entry()])
            other = Path(tmp) / "docs/sources/other.pdf"
            other.write_bytes(b"%PDF-1.4")
            registry = json.loads(path.read_text(encoding="utf-8"))
            registry[0]["metadata_exception"]["evidence"] = "docs/sources/other.pdf#page=1"
            path.write_text(json.dumps(registry), encoding="utf-8")
            errors = validate_registry(path, root=Path(tmp))
            self.assertTrue(
                any("must point at this entry's local_file" in error for error in errors), errors
            )

    def test_invalid_exception_never_excuses_the_author_check_online(self):
        not_local = "must point at this entry's local_file"
        cases = {
            "missing page": ({"evidence": self.PDF}, True, "#page=<N>"),
            "nonexistent file": ({}, False, "does not exist"),
            "blank reason": ({"reason": " "}, True, "reason must say why"),
            "unknown key": ({"note": "extra"}, True, "unknown keys"),
            "other file": ({"evidence": "docs/sources/other.pdf#page=1"}, True, not_local),
            "trailing space": ({"evidence": f"{self.PDF} #page=1"}, True, not_local),
        }
        for name, (override, create_pdf, message) in cases.items():
            with self.subTest(case=name), TemporaryDirectory() as tmp:
                exception = self.exception(**override)
                entries = [self.entry(metadata_exception=exception)]
                path = (
                    self.setup_repo(tmp, entries)
                    if create_pdf
                    else self.write_registry(tmp, entries)
                )
                (Path(tmp) / "docs/sources").mkdir(parents=True, exist_ok=True)
                (Path(tmp) / "docs/sources/other.pdf").write_bytes(b"%PDF-1.4")
                warnings: list[str] = []
                errors = self.validate(
                    path, root=Path(tmp), warnings=warnings, fetch_crossref=self.metadata
                )
                self.assertTrue(any(message in error for error in errors), errors)
                self.assertTrue(any("authors do not match" in error for error in errors), errors)
                self.assertEqual(warnings, [])

    def test_invalid_exception_does_not_excuse_missing_agency_authors_online(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(
                tmp, [self.entry(metadata_exception=self.exception(evidence=self.PDF))]
            )
            warnings: list[str] = []
            errors = self.validate(
                path,
                root=Path(tmp),
                warnings=warnings,
                fetch_crossref=lambda doi: self.metadata(doi, author=[]),
            )
            self.assertTrue(any("authors missing from" in error for error in errors), errors)
            self.assertEqual(warnings, [])

    def test_agency_and_doi_resolver_urls_are_rejected_as_evidence(self):
        for url in (
            "https://api.crossref.org/works/10.1234/example",
            "https://search.crossref.org/?q=10.1234%2Fexample",
            "https://data.crossref.org/10.1234/example",
            "https://api.datacite.org/dois/10.1234/example",
            "https://doi.org/10.1234/example",
            "http://dx.doi.org/10.1234/example",
            "https://API.Crossref.org/works/10.1234/example",
        ):
            with self.subTest(url=url), TemporaryDirectory() as tmp:
                entry = self.entry(
                    access="abstract-only", metadata_exception=self.exception(evidence=url)
                )
                del entry["local_file"]
                path = self.write_registry(tmp, [entry])
                errors = validate_registry(path, root=Path(tmp))
                self.assertTrue(
                    any("agency or DOI-resolver URL" in error for error in errors), errors
                )

    def test_entry_without_local_file_needs_url_evidence(self):
        with TemporaryDirectory() as tmp:
            entry = self.entry(access="abstract-only")
            del entry["local_file"]
            path = self.setup_repo(tmp, [entry])
            errors = validate_registry(path, root=Path(tmp))
            self.assertTrue(any("http(s) URL" in error for error in errors))

    def test_exception_shape_is_checked_offline(self):
        cases = {
            "not an object": "authors",
            "unknown key": self.exception(note="extra"),
            "blank reason": self.exception(reason=" "),
            "empty fields": self.exception(fields=[]),
        }
        for name, exception in cases.items():
            with self.subTest(case=name), TemporaryDirectory() as tmp:
                path = self.setup_repo(tmp, [self.entry(metadata_exception=exception)])
                errors = validate_registry(path, root=Path(tmp))
                self.assertTrue(any("metadata_exception" in error for error in errors), errors)

    def test_exception_requires_a_doi(self):
        with TemporaryDirectory() as tmp:
            entry = self.entry(source_type="report")
            del entry["doi"]
            path = self.setup_repo(tmp, [entry])
            errors = validate_registry(path, root=Path(tmp))
            self.assertTrue(any("only applies to entries with a DOI" in error for error in errors))

    def test_title_mismatch_still_fails_with_an_exception(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(tmp, [self.entry()])
            errors = self.validate(
                path,
                root=Path(tmp),
                warnings=[],
                fetch_crossref=lambda doi: self.metadata(doi, title=["Something else entirely"]),
            )
            self.assertTrue(any("title does not match" in error for error in errors))

    def test_year_and_venue_mismatch_still_fail_with_an_exception(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(tmp, [self.entry()])
            errors = self.validate(
                path,
                root=Path(tmp),
                warnings=[],
                fetch_crossref=lambda doi: self.metadata(
                    doi,
                    **{"published-print": {"date-parts": [[2019]]},
                       "container-title": ["Invented Journal"]},
                ),
            )
            self.assertTrue(any("year does not match" in error for error in errors))
            self.assertTrue(any("venue does not match" in error for error in errors))

    def test_unresolvable_doi_still_fails_with_an_exception(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(tmp, [self.entry()])

            def not_found(doi: str) -> dict:
                raise http_error(404)

            errors = self.validate(
                path, root=Path(tmp), warnings=[],
                fetch_crossref=not_found, fetch_datacite=not_found,
            )
            self.assertTrue(any("DOI not found" in error for error in errors))

    def test_retraction_still_blocks_with_an_exception(self):
        with TemporaryDirectory() as tmp:
            path = self.setup_repo(tmp, [self.entry()])
            errors = self.validate(
                path,
                root=Path(tmp),
                warnings=[],
                fetch_crossref=self.metadata,
                fetch_updates=lambda doi: [
                    {"type": "retraction", "notice_doi": "10.1234/notice", "source": "retraction-watch"}
                ],
            )
            self.assertTrue(any("flagged as retraction" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
