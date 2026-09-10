import unittest
from datetime import date
from urllib.error import URLError

from scripts.search_fallback import search

TODAY = date(2026, 1, 15)

ARXIV_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2309.17345v2</id>
    <published>2023-09-29T00:00:00Z</published>
    <title>Physics-Informed
      Surrogates for Fouling</title>
    <author><name>Ada Lovelace</name></author>
    <author><name>Grace Hopper</name></author>
    <link title="pdf" href="http://arxiv.org/pdf/2309.17345v2"/>
  </entry>
</feed>
"""


def crossref_payload(items, total=1):
    return {"message": {"total-results": total, "items": items}}


def article(**overrides):
    work = {
        "DOI": "https://doi.org/10.1016/J.EXAMPLE.2024.001",
        "title": ["A Machine Learning Approach to Fouling"],
        "author": [{"given": "Jane", "family": "Doe"}, {"given": "Rui", "family": "Silva"}],
        "container-title": ["Example Journal"],
        "type": "journal-article",
        "published": {"date-parts": [[2024, 5, 1]]},
        "is-referenced-by-count": 12,
    }
    work.update(overrides)
    return work


def stub(payload=None, atom=None, crossref_error=None, arxiv_error=None):
    def crossref(*_args):
        if crossref_error:
            raise crossref_error
        return payload

    def arxiv(*_args):
        if arxiv_error:
            raise arxiv_error
        return (atom or ARXIV_ATOM).encode("utf-8")

    return {"crossref": crossref, "arxiv": arxiv}


class TestCrossrefBackend(unittest.TestCase):
    def result(self, items, **kwargs):
        return search("fouling", source="crossref", today=TODAY,
                      fetchers=stub(payload=crossref_payload(items)), **kwargs)

    def test_entry_is_registry_shaped(self):
        entry = self.result([article()])["candidates"][0]["entry"]
        self.assertEqual(entry["key"], "doe2024machine")
        self.assertEqual(entry["doi"], "10.1016/j.example.2024.001")
        self.assertEqual(entry["url"], "https://doi.org/10.1016/j.example.2024.001")
        self.assertEqual(entry["authors"], ["Jane Doe", "Rui Silva"])
        self.assertEqual(entry["year"], 2024)
        self.assertEqual(entry["venue"], "Example Journal")
        self.assertEqual(entry["source_type"], "journal-article")
        self.assertEqual(entry["retrieved_at"], "2026-01-15")

    def test_unmapped_type_stays_undecided(self):
        # A label the registry has no vocabulary for must not be guessed:
        # peer-review status changes how much weight a claim can carry.
        entry = self.result([article(type="book-chapter")])["candidates"][0]["entry"]
        self.assertIsNone(entry["source_type"])

    def test_posted_content_is_a_preprint(self):
        entry = self.result([article(type="posted-content")])["candidates"][0]["entry"]
        self.assertEqual(entry["source_type"], "preprint")

    def test_retracted_work_is_filtered_and_counted(self):
        retracted = article(**{"update-to": [{"type": "retraction"}]})
        result = self.result([retracted])
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["retracted_filtered"], 1)

    def test_retracted_work_is_kept_only_when_asked(self):
        retracted = article(**{"update-to": [{"type": "retraction"}]})
        result = self.result([retracted], include_retracted=True)
        self.assertEqual(len(result["candidates"]), 1)
        self.assertTrue(result["candidates"][0]["is_retracted"])

    def test_expression_of_concern_counts_as_retraction(self):
        flagged = article(**{"update-to": [{"type": "expression_of_concern"}]})
        self.assertEqual(self.result([flagged])["retracted_filtered"], 1)

    def test_missing_date_yields_nodate_key_not_a_guess(self):
        entry = self.result([article(published=None, issued=None)])["candidates"][0]["entry"]
        self.assertIsNone(entry["year"])
        self.assertIn("nodate", entry["key"])


class TestArxivBackend(unittest.TestCase):
    def test_preprint_carries_the_server_issued_doi(self):
        result = search("fouling", source="arxiv", today=TODAY, fetchers=stub())
        entry = result["candidates"][0]["entry"]
        self.assertEqual(entry["source_type"], "preprint")
        self.assertEqual(entry["doi"], "10.48550/arXiv.2309.17345")
        self.assertEqual(entry["venue"], "arXiv")
        self.assertEqual(entry["authors"], ["Ada Lovelace", "Grace Hopper"])
        self.assertEqual(entry["year"], 2023)
        self.assertEqual(entry["title"], "Physics-Informed Surrogates for Fouling")

    def test_from_year_excludes_older_preprints(self):
        result = search("fouling", source="arxiv", from_year=2025, today=TODAY, fetchers=stub())
        self.assertEqual(result["candidates"], [])


class TestCombinedSearch(unittest.TestCase):
    def test_duplicate_doi_keeps_the_published_record(self):
        shared = article(DOI="10.48550/arXiv.2309.17345", type="journal-article")
        result = search("fouling", source="both", today=TODAY,
                        fetchers=stub(payload=crossref_payload([shared])))
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["source_api"], "crossref")

    def test_one_backend_down_still_returns_the_other(self):
        result = search("fouling", source="both", today=TODAY,
                        fetchers=stub(atom=ARXIV_ATOM, crossref_error=URLError("offline")))
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["source_api"], "arxiv")
        self.assertTrue(any("crossref" in error for error in result["errors"]))

    def test_both_backends_down_reports_both_and_returns_nothing(self):
        result = search("fouling", source="both", today=TODAY,
                        fetchers=stub(crossref_error=URLError("offline"),
                                      arxiv_error=URLError("offline")))
        self.assertEqual(result["candidates"], [])
        self.assertEqual(len(result["errors"]), 2)

    def test_limit_caps_the_combined_result(self):
        items = [article(DOI=f"10.1234/x{index}", title=[f"Study {index}"]) for index in range(5)]
        result = search("fouling", limit=2, source="both", today=TODAY,
                        fetchers=stub(payload=crossref_payload(items, total=5)))
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["total_matches"], 5)


if __name__ == "__main__":
    unittest.main()
