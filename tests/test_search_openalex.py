import unittest
from datetime import date

from scripts.search_openalex import (
    build_key,
    map_source_type,
    normalize_doi,
    search,
    to_candidate,
)

TODAY = date(2026, 9, 5)


def work(**overrides) -> dict:
    base = {
        "id": "https://openalex.org/W123",
        "doi": "https://doi.org/10.1234/Example",
        "display_name": "A Study of Heat Exchanger Fouling",
        "publication_year": 2021,
        "type": "article",
        "authorships": [{"author": {"display_name": "Ji-Hoon Kim"}}],
        "primary_location": {"source": {"display_name": "Applied Energy", "type": "journal"}},
        "open_access": {"is_oa": True, "oa_url": "https://example.org/paper.pdf"},
        "best_oa_location": {"pdf_url": "https://example.org/paper.pdf"},
        "cited_by_count": 12,
        "is_retracted": False,
    }
    base.update(overrides)
    return base


def payload(*works: dict, count: int = 99) -> dict:
    return {"meta": {"count": count}, "results": list(works)}


class TestFieldMapping(unittest.TestCase):
    def test_doi_url_is_normalised_and_lowercased(self):
        self.assertEqual(normalize_doi("https://doi.org/10.1234/Example"), "10.1234/example")

    def test_missing_doi_becomes_empty(self):
        self.assertEqual(normalize_doi(None), "")

    def test_key_is_surname_year_keyword(self):
        self.assertEqual(build_key(work()), "kim2021heat")

    def test_key_skips_stopwords_in_the_title(self):
        self.assertEqual(build_key(work(display_name="A Review of the Process")), "kim2021review")

    def test_key_survives_missing_author_and_year(self):
        self.assertEqual(build_key(work(authorships=[], publication_year=None)), "anonnodateheat")

    def test_journal_article_is_mapped(self):
        self.assertEqual(map_source_type(work()), "journal-article")

    def test_preprint_is_mapped(self):
        self.assertEqual(map_source_type(work(type="preprint")), "preprint")

    def test_article_outside_a_journal_is_not_called_a_journal_article(self):
        candidate = work(primary_location={"source": {"display_name": "SSRN", "type": "repository"}})
        self.assertEqual(map_source_type(candidate), "report")

    def test_unmapped_type_is_left_for_the_agent(self):
        """A wrong source_type would misstate peer-review status, so guess nothing."""
        self.assertIsNone(map_source_type(work(type="book-chapter")))


class TestCandidateShape(unittest.TestCase):
    def test_entry_holds_only_registry_fields(self):
        candidate = to_candidate(work(), TODAY)
        self.assertEqual(
            set(candidate["entry"]),
            {"key", "title", "url", "retrieved_at", "source_type", "doi"},
        )

    def test_access_is_not_guessed(self):
        """access records what was actually read; a search cannot know that."""
        self.assertNotIn("access", to_candidate(work(), TODAY)["entry"])

    def test_open_access_pdf_is_surfaced_outside_the_entry(self):
        candidate = to_candidate(work(), TODAY)
        self.assertEqual(candidate["pdf_url"], "https://example.org/paper.pdf")
        self.assertTrue(candidate["is_oa"])

    def test_url_falls_back_to_landing_page_without_a_doi(self):
        candidate = to_candidate(
            work(
                doi=None,
                primary_location={
                    "source": {"display_name": "X", "type": "journal"},
                    "landing_page_url": "https://example.org/landing",
                },
            ),
            TODAY,
        )
        self.assertEqual(candidate["entry"]["url"], "https://example.org/landing")


class TestSearch(unittest.TestCase):
    def run_search(self, *works: dict, **kwargs):
        return search("fouling", today=TODAY, fetch=lambda *a, **k: payload(*works), **kwargs)

    def test_results_are_returned_with_the_match_count(self):
        result = self.run_search(work())
        self.assertEqual(result["total_matches"], 99)
        self.assertEqual(len(result["candidates"]), 1)

    def test_retracted_works_are_filtered_and_counted(self):
        result = self.run_search(work(), work(id="W2", is_retracted=True))
        self.assertEqual(result["retracted_filtered"], 1)
        self.assertEqual(len(result["candidates"]), 1)

    def test_retracted_works_can_be_kept_deliberately(self):
        result = self.run_search(work(), work(id="W2", is_retracted=True), include_retracted=True)
        self.assertEqual(len(result["candidates"]), 2)

    def test_limit_is_applied(self):
        result = self.run_search(work(), work(id="W2"), work(id="W3"), limit=2)
        self.assertEqual(len(result["candidates"]), 2)

    def test_empty_results_are_handled(self):
        result = search("fouling", today=TODAY, fetch=lambda *a, **k: {"meta": {"count": 0}})
        self.assertEqual(result["candidates"], [])


if __name__ == "__main__":
    unittest.main()
