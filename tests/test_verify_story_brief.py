import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.validation_common import is_concluding_section
from scripts.verify_story_brief import (
    extract_section_claims,
    parse_brief,
    validate_all,
    validate_claims,
    validate_evidence,
    validate_narrative,
    validate_sections,
)

ALL_SLOTS = ("Context", "Gap", "Question", "Approach", "Finding", "Implication")

NARRATIVE_TABLE = (
    "| Slot | Sentence |\n"
    "|---|---|\n"
    "| Context | Electrolysers are deployed at scale. |\n"
    "| Gap | Degradation under dynamic load is unquantified. |\n"
    "| Question | How does duty cycle drive degradation? |\n"
    "| Approach | A cycled bench test with a physics-informed model. |\n"
    "| Finding | Degradation scales with ramp count, not runtime. |\n"
    "| Implication | Dispatch schedules should cap ramps. |\n"
)


def brief_text(narrative: str = NARRATIVE_TABLE, claims: str = "", falsifiers: str = "") -> str:
    return (
        "# Story Brief\n\n"
        "## Narrative\n\n" + narrative + "\n"
        "## Claims\n\n"
        "| ID | Claim | Status | Evidence |\n"
        "|---|---|---|---|\n" + claims + "\n"
        "## Falsifiers\n\n" + falsifiers
    )


def write_brief(tmp_dir: str, content: str) -> Path:
    brief_path = Path(tmp_dir) / "story-brief.md"
    brief_path.write_text(content, encoding="utf-8")
    return brief_path


def write_section(tmp_dir: str, name: str, content: str) -> Path:
    section_path = Path(tmp_dir) / name
    section_path.write_text(content, encoding="utf-8")
    return section_path


class TestParseBrief(unittest.TestCase):
    def test_parses_slots_claims_and_falsifiers(self):
        with TemporaryDirectory() as tmp:
            brief_path = write_brief(
                tmp,
                brief_text(
                    claims="| C1 | Ramps drive degradation | supported | run:2026-09-07-a |\n",
                    falsifiers="- **C1:** Degradation tracks runtime instead of ramp count.\n",
                ),
            )
            brief = parse_brief(brief_path)

            self.assertEqual([name for name, _ in brief["slots"]], list(ALL_SLOTS))
            self.assertEqual(len(brief["claims"]), 1)
            self.assertEqual(brief["claims"][0]["id"], "C1")
            self.assertEqual(brief["claims"][0]["status"], "supported")
            self.assertEqual(brief["claims"][0]["evidence"], "run:2026-09-07-a")
            self.assertIn("C1", brief["falsifiers"])

    def test_ignores_unrelated_tables(self):
        with TemporaryDirectory() as tmp:
            brief_path = write_brief(
                tmp,
                brief_text(claims="| C1 | A claim | assumed | |\n")
                + "\n## Evidence forms\n\n| Form | Meaning |\n|---|---|\n| @key | a source |\n",
            )
            brief = parse_brief(brief_path)
            self.assertEqual([claim["id"] for claim in brief["claims"]], ["C1"])


class TestValidateNarrative(unittest.TestCase):
    def test_missing_slot_is_flagged(self):
        brief = {"slots": [("Context", "x"), ("Gap", "y")], "claims": [], "falsifiers": {}}
        errors = validate_narrative(brief, [])
        self.assertTrue(any("missing slots" in error for error in errors))

    def test_out_of_order_slots_are_flagged(self):
        slots = [
            ("Gap", "y"),
            ("Context", "x"),
            ("Question", "q"),
            ("Approach", "a"),
            ("Finding", "f"),
            ("Implication", "i"),
        ]
        errors = validate_narrative({"slots": slots, "claims": [], "falsifiers": {}}, [])
        self.assertTrue(any("not in Context-Gap-Question" in error for error in errors))

    def test_unknown_slot_is_flagged(self):
        slots = [(name, "x") for name in ALL_SLOTS] + [("Motivation", "x")]
        errors = validate_narrative({"slots": slots, "claims": [], "falsifiers": {}}, [])
        self.assertTrue(any("unknown slots" in error for error in errors))

    def test_required_slot_must_not_be_a_placeholder(self):
        brief = {
            "slots": [(name, "_입력 필요_") for name in ALL_SLOTS],
            "claims": [],
            "falsifiers": {},
        }
        self.assertEqual(validate_narrative(brief, []), [])
        errors = validate_narrative(brief, ["Context"])
        self.assertTrue(any("slot 'Context' is required" in error for error in errors))

    def test_empty_required_slot_is_flagged(self):
        slots = [(name, "" if name == "Gap" else "filled") for name in ALL_SLOTS]
        errors = validate_narrative({"slots": slots, "claims": [], "falsifiers": {}}, ["Gap"])
        self.assertTrue(any("slot 'Gap' is required" in error for error in errors))


class TestValidateClaims(unittest.TestCase):
    def brief(self, claims, falsifiers):
        return {"slots": [], "claims": claims, "falsifiers": falsifiers}

    def test_supported_claim_requires_evidence(self):
        errors = validate_claims(
            self.brief(
                [{"id": "C1", "claim": "x", "status": "supported", "evidence": ""}],
                {"C1": "something measurable"},
            )
        )
        self.assertTrue(any("requires at least one evidence" in error for error in errors))

    def test_supported_claim_requires_written_falsifier(self):
        errors = validate_claims(
            self.brief(
                [{"id": "C1", "claim": "x", "status": "supported", "evidence": "@kim2021"}],
                {"C1": "_입력 필요_"},
            )
        )
        self.assertTrue(any("requires a written falsifier" in error for error in errors))

    def test_assumed_claim_may_be_unfilled_but_needs_a_falsifier_entry(self):
        self.assertEqual(
            validate_claims(
                self.brief(
                    [{"id": "C1", "claim": "_입력 필요_", "status": "assumed", "evidence": ""}],
                    {"C1": "_입력 필요_"},
                )
            ),
            [],
        )
        errors = validate_claims(
            self.brief([{"id": "C1", "claim": "x", "status": "assumed", "evidence": ""}], {})
        )
        self.assertTrue(any("no falsifier recorded" in error for error in errors))

    def test_invalid_id_status_and_duplicates_are_flagged(self):
        errors = validate_claims(
            self.brief(
                [
                    {"id": "X1", "claim": "x", "status": "assumed", "evidence": ""},
                    {"id": "C1", "claim": "x", "status": "maybe", "evidence": ""},
                    {"id": "C1", "claim": "x", "status": "assumed", "evidence": ""},
                ],
                {"C1": "f"},
            )
        )
        self.assertTrue(any("invalid claim id 'X1'" in error for error in errors))
        self.assertTrue(any("invalid status 'maybe'" in error for error in errors))
        self.assertTrue(any("duplicate claim id 'C1'" in error for error in errors))

    def test_falsifier_for_unknown_claim_is_flagged(self):
        errors = validate_claims(
            self.brief(
                [{"id": "C1", "claim": "x", "status": "assumed", "evidence": ""}],
                {"C1": "f", "C9": "f"},
            )
        )
        self.assertTrue(any("falsifiers: no such claim: C9" in error for error in errors))


class TestValidateEvidence(unittest.TestCase):
    def brief(self, evidence):
        return {
            "slots": [],
            "claims": [{"id": "C1", "claim": "x", "status": "supported", "evidence": evidence}],
            "falsifiers": {"C1": "f"},
        }

    def test_registered_source_key_passes_and_unregistered_fails(self):
        with TemporaryDirectory() as tmp:
            registry = Path(tmp) / "retrieved-sources.json"
            registry.write_text(json.dumps([{"key": "kim2021flux"}]), encoding="utf-8")

            self.assertEqual(validate_evidence(self.brief("@kim2021flux"), registry, Path(tmp)), [])
            errors = validate_evidence(self.brief("@ghost2020"), registry, Path(tmp))
            self.assertTrue(any("not in the source registry" in error for error in errors))

    def test_run_evidence_requires_a_manifest(self):
        with TemporaryDirectory() as tmp:
            processed = Path(tmp)
            errors = validate_evidence(self.brief("run:2026-09-07-a"), None, processed)
            self.assertTrue(any("has no manifest" in error for error in errors))

            (processed / "2026-09-07-a.manifest.json").write_text("{}", encoding="utf-8")
            self.assertTrue(validate_evidence(self.brief("run:2026-09-07-a"), None, processed))

    def test_figure_and_table_evidence_requires_rendered_sections(self):
        with TemporaryDirectory() as tmp:
            self.assertTrue(validate_evidence(self.brief("Fig. 2, Table 3"), None, Path(tmp)))

    def test_unrecognised_evidence_is_flagged(self):
        with TemporaryDirectory() as tmp:
            errors = validate_evidence(self.brief("trust me"), None, Path(tmp))
            self.assertTrue(any("unrecognised evidence" in error for error in errors))

    def test_missing_registry_file_fails_key_resolution(self):
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "absent.json"
            self.assertTrue(validate_evidence(self.brief("@anything"), missing, Path(tmp)))


class TestSectionDeclarations(unittest.TestCase):
    def test_extracts_claim_ids_from_comment(self):
        with TemporaryDirectory() as tmp:
            section = write_section(
                tmp, "01-introduction.md", "# Introduction\n<!-- claims: C1, C3 -->\nText.\n"
            )
            self.assertEqual(extract_section_claims(section), {"C1", "C3"})

    def test_section_without_declaration_yields_nothing(self):
        with TemporaryDirectory() as tmp:
            section = write_section(tmp, "01-introduction.md", "# Introduction\n")
            self.assertEqual(extract_section_claims(section), set())

    def test_concluding_sections_are_recognised(self):
        roles = {"04-results.md": "concluding", "06-conclusion.md": "concluding",
                 "01-introduction.md": "front-matter"}
        self.assertTrue(is_concluding_section(Path("docs/sections/04-results.md"), roles))
        self.assertTrue(is_concluding_section(Path("docs/sections/06-conclusion.md"), roles))
        self.assertFalse(is_concluding_section(Path("docs/sections/01-introduction.md"), roles))

    def test_concluding_role_comes_from_the_outline_not_the_filename(self):
        """A section named 'results' with no outline entry is not concluding by
        name alone - the outline's Sections table is what assigns the role."""
        self.assertFalse(is_concluding_section(Path("docs/sections/04-results.md"), {}))
        self.assertFalse(is_concluding_section(Path("docs/sections/04-results.md")))


class TestValidateSections(unittest.TestCase):
    def brief(self, statuses):
        return {
            "slots": [],
            "claims": [
                {"id": cid, "claim": "x", "status": status, "evidence": ""}
                for cid, status in statuses.items()
            ],
            "falsifiers": {},
        }

    def test_orphan_claim_is_flagged(self):
        with TemporaryDirectory() as tmp:
            section = write_section(tmp, "01-introduction.md", "<!-- claims: C7 -->\n")
            errors = validate_sections(self.brief({"C1": "assumed"}), [section], False)
            self.assertTrue(any("claims not in the brief: C7" in error for error in errors))

    def test_refuted_claim_in_any_section_is_flagged(self):
        with TemporaryDirectory() as tmp:
            section = write_section(tmp, "01-introduction.md", "<!-- claims: C1 -->\n")
            errors = validate_sections(self.brief({"C1": "refuted"}), [section], False)
            self.assertTrue(any("carries refuted claims: C1" in error for error in errors))

    def test_assumed_claim_is_allowed_in_introduction_but_not_in_results(self):
        with TemporaryDirectory() as tmp:
            intro = write_section(tmp, "01-introduction.md", "<!-- claims: C1 -->\n")
            results = write_section(tmp, "04-results.md", "<!-- claims: C1 -->\n")
            brief = self.brief({"C1": "assumed"})
            roles = {"01-introduction.md": "front-matter", "04-results.md": "concluding"}

            self.assertEqual(validate_sections(brief, [intro], False, roles), [])
            errors = validate_sections(brief, [results], False, roles)
            self.assertTrue(any("states assumed claims as findings" in error for error in errors))

    def test_supported_claim_is_allowed_in_results(self):
        with TemporaryDirectory() as tmp:
            results = write_section(tmp, "04-results.md", "<!-- claims: C1 -->\n")
            brief = self.brief({"C1": "supported"})
            self.assertEqual(validate_sections(brief, [results], False), [])

    def test_require_coverage_flags_claims_no_section_carries(self):
        with TemporaryDirectory() as tmp:
            intro = write_section(tmp, "01-introduction.md", "<!-- claims: C1 -->\nA hypothesis.\n")
            brief = self.brief({"C1": "assumed", "C2": "assumed", "C3": "refuted"})

            self.assertEqual(validate_sections(brief, [intro], False), [])
            errors = validate_sections(brief, [intro], True)
            self.assertEqual(len(errors), 1)
            self.assertIn("no section carries C2", errors[0])
            self.assertNotIn("C3", errors[0])


class TestValidateAll(unittest.TestCase):
    def test_shipped_template_passes_the_structural_check(self):
        errors = validate_all(
            Path("docs/notes/story-brief.md"), [], [], None, Path("data/processed"), False
        )
        self.assertEqual(errors, [])

    def test_end_to_end_failure_collects_errors_from_every_check(self):
        with TemporaryDirectory() as tmp:
            brief_path = write_brief(
                tmp,
                brief_text(
                    claims="| C1 | Ramps drive degradation | supported | trust me |\n",
                    falsifiers="- **C1:** _입력 필요_\n",
                ),
            )
            results = write_section(tmp, "04-results.md", "<!-- claims: C1, C9 -->\n")
            errors = validate_all(brief_path, [results], ["Context"], None, Path(tmp), False)

            self.assertTrue(any("written falsifier" in error for error in errors))
            self.assertTrue(any("unrecognised evidence" in error for error in errors))
            self.assertTrue(any("claims not in the brief: C9" in error for error in errors))
            self.assertFalse(any("slot 'Context' is required" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
