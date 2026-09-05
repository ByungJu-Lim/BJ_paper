import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_submissions import (
    parse_attempts,
    validate_attempt,
    validate_attempt_folder,
    validate_figure_profile,
    validate_ledger,
)

TODAY = date(2026, 9, 5)


def attempt_block(
    attempt_id: str,
    venue: str = "Applied Energy",
    status: str = "submitted",
    submitted_on: str | None = "2026-01-10",
    decision_on: str | None = None,
    manuscript_tag: str | None = "submission/01",
    carried_forward: str | None = None,
    reviewer_points: tuple[str, ...] = (),
) -> str:
    lines = [
        f"## Attempt: {attempt_id}",
        f"venue: {venue}",
        f"status: {status}",
        f"submitted-on: {submitted_on or ''}",
        f"decision-on: {decision_on or ''}",
        f"manuscript-tag: {manuscript_tag or ''}",
        f"carried-forward: {carried_forward or ''}",
        "reviewer-points:",
    ]
    lines.extend(f'  - "{point}"' for point in reviewer_points)
    return "\n".join(lines) + "\n"


def write_log(tmp_dir: str, *blocks: str) -> Path:
    path = Path(tmp_dir) / "submission-log.md"
    path.write_text("# Submission Log\n\n" + "\n".join(blocks), encoding="utf-8")
    return path


class TestParseAttempts(unittest.TestCase):
    def test_parses_scalars_and_reviewer_points(self):
        with TemporaryDirectory() as tmp:
            path = write_log(
                tmp,
                attempt_block(
                    "01-applied-energy",
                    status="rejected",
                    decision_on="2026-03-02",
                    carried_forward="yes",
                    reviewer_points=("scope too narrow", "needs uncertainty analysis"),
                ),
            )
            attempt = parse_attempts(path)[0]
            self.assertEqual(attempt["id"], "01-applied-energy")
            self.assertEqual(attempt["venue"], "Applied Energy")
            self.assertEqual(attempt["status"], "rejected")
            self.assertEqual(attempt["decision-on"], "2026-03-02")
            self.assertEqual(
                attempt["reviewer-points"],
                ["scope too narrow", "needs uncertainty analysis"],
            )

    def test_empty_optional_fields_become_none(self):
        with TemporaryDirectory() as tmp:
            path = write_log(tmp, attempt_block("01-applied-energy"))
            attempt = parse_attempts(path)[0]
            self.assertIsNone(attempt["decision-on"])
            self.assertEqual(attempt["reviewer-points"], [])


class TestValidateAttempt(unittest.TestCase):
    def parse_one(self, block: str) -> dict:
        with TemporaryDirectory() as tmp:
            return parse_attempts(write_log(tmp, block))[0]

    def test_valid_submitted_attempt_has_no_errors(self):
        attempt = self.parse_one(attempt_block("01-applied-energy"))
        self.assertEqual(validate_attempt(attempt, today=TODAY), [])

    def test_malformed_id_is_flagged(self):
        attempt = self.parse_one(attempt_block("Applied_Energy"))
        errors = validate_attempt(attempt, today=TODAY)
        self.assertTrue(any("01-venue-slug" in error for error in errors))

    def test_invalid_status_is_flagged(self):
        attempt = self.parse_one(attempt_block("01-applied-energy", status="maybe"))
        errors = validate_attempt(attempt, today=TODAY)
        self.assertTrue(any("invalid status" in error for error in errors))

    def test_submitted_attempt_requires_manuscript_tag(self):
        attempt = self.parse_one(attempt_block("01-applied-energy", manuscript_tag=None))
        errors = validate_attempt(attempt, today=TODAY)
        self.assertTrue(any("manuscript-tag" in error for error in errors))

    def test_preparing_attempt_must_not_have_submitted_on(self):
        attempt = self.parse_one(
            attempt_block("01-applied-energy", status="preparing", manuscript_tag=None)
        )
        errors = validate_attempt(attempt, today=TODAY)
        self.assertTrue(any("must not have submitted-on" in error for error in errors))

    def test_rejected_attempt_requires_decision_on(self):
        attempt = self.parse_one(attempt_block("01-applied-energy", status="rejected"))
        errors = validate_attempt(attempt, today=TODAY)
        self.assertTrue(any("requires decision-on" in error for error in errors))

    def test_decision_before_submission_is_flagged(self):
        attempt = self.parse_one(
            attempt_block(
                "01-applied-energy",
                status="rejected",
                submitted_on="2026-03-01",
                decision_on="2026-01-01",
            )
        )
        errors = validate_attempt(attempt, today=TODAY)
        self.assertTrue(any("precedes submitted-on" in error for error in errors))

    def test_future_submission_date_is_flagged(self):
        attempt = self.parse_one(attempt_block("01-applied-energy", submitted_on="2027-01-01"))
        errors = validate_attempt(attempt, today=TODAY)
        self.assertTrue(any("future" in error for error in errors))


class TestValidateLedger(unittest.TestCase):
    def test_rejection_then_new_attempt_is_valid(self):
        with TemporaryDirectory() as tmp:
            path = write_log(
                tmp,
                attempt_block(
                    "01-applied-energy",
                    status="rejected",
                    decision_on="2026-03-02",
                    carried_forward="yes",
                    reviewer_points=("needs uncertainty analysis",),
                ),
                attempt_block(
                    "02-energy-conversion",
                    venue="Energy Conversion and Management",
                    status="under-review",
                    submitted_on="2026-04-01",
                    manuscript_tag="submission/02",
                ),
            )
            self.assertEqual(validate_ledger(path, today=TODAY), {})

    def test_concurrent_submission_is_flagged(self):
        """Two venues holding the same manuscript at once is misconduct, not a typo."""
        with TemporaryDirectory() as tmp:
            path = write_log(
                tmp,
                attempt_block("01-applied-energy", status="under-review"),
                attempt_block(
                    "02-energy-conversion",
                    venue="Energy Conversion and Management",
                    status="submitted",
                    submitted_on="2026-02-01",
                    manuscript_tag="submission/02",
                ),
            )
            errors = validate_ledger(path, today=TODAY)["__ledger__"]
            self.assertTrue(any("concurrent submission" in error for error in errors))

    def test_new_attempt_without_carrying_feedback_forward_is_flagged(self):
        with TemporaryDirectory() as tmp:
            path = write_log(
                tmp,
                attempt_block(
                    "01-applied-energy",
                    status="rejected",
                    decision_on="2026-03-02",
                    carried_forward="no",
                    reviewer_points=("needs uncertainty analysis",),
                ),
                attempt_block(
                    "02-energy-conversion",
                    venue="Energy Conversion and Management",
                    status="submitted",
                    submitted_on="2026-04-01",
                    manuscript_tag="submission/02",
                ),
            )
            errors = validate_ledger(path, today=TODAY)["__ledger__"]
            self.assertTrue(any("carried forward" in error for error in errors))

    def test_out_of_order_numbering_is_flagged(self):
        with TemporaryDirectory() as tmp:
            path = write_log(
                tmp,
                attempt_block(
                    "02-applied-energy",
                    status="rejected",
                    decision_on="2026-03-02",
                    carried_forward="yes",
                ),
                attempt_block(
                    "01-energy-conversion",
                    venue="Energy Conversion and Management",
                    status="submitted",
                    submitted_on="2026-04-01",
                    manuscript_tag="submission/02",
                ),
            )
            errors = validate_ledger(path, today=TODAY)["__ledger__"]
            self.assertTrue(any("in order" in error for error in errors))

    def test_attempt_after_acceptance_is_flagged(self):
        with TemporaryDirectory() as tmp:
            path = write_log(
                tmp,
                attempt_block(
                    "01-applied-energy",
                    status="accepted",
                    decision_on="2026-03-02",
                ),
                attempt_block(
                    "02-energy-conversion",
                    venue="Energy Conversion and Management",
                    status="submitted",
                    submitted_on="2026-04-01",
                    manuscript_tag="submission/02",
                ),
            )
            errors = validate_ledger(path, today=TODAY)["__ledger__"]
            self.assertTrue(
                any("after 01-applied-energy was accepted" in error for error in errors)
            )

    def test_empty_ledger_is_valid(self):
        with TemporaryDirectory() as tmp:
            path = write_log(tmp)
            self.assertEqual(validate_ledger(path, today=TODAY), {})


def valid_profile(**overrides) -> dict:
    profile = {
        "format": "tiff",
        "dpi": 300,
        "column_width_mm": {"single": 90, "double": 190},
        "main_figures": ["fig1", "fig2"],
        "supplementary_figures": [],
    }
    profile.update(overrides)
    return profile


class TestValidateFigureProfile(unittest.TestCase):
    def test_valid_profile_has_no_errors(self):
        self.assertEqual(validate_figure_profile("01-x", valid_profile()), [])

    def test_vector_format_does_not_require_dpi(self):
        profile = valid_profile(format="eps")
        del profile["dpi"]
        self.assertEqual(validate_figure_profile("01-x", profile), [])

    def test_raster_below_300_dpi_is_flagged(self):
        errors = validate_figure_profile("01-x", valid_profile(dpi=150))
        self.assertTrue(any("below the 300" in error for error in errors))

    def test_unknown_format_is_flagged(self):
        errors = validate_figure_profile("01-x", valid_profile(format="bmp"))
        self.assertTrue(any("format must be one of" in error for error in errors))

    def test_negative_column_width_is_flagged(self):
        errors = validate_figure_profile("01-x", valid_profile(column_width_mm={"single": -5}))
        self.assertTrue(any("positive number" in error for error in errors))

    def test_figure_in_both_main_and_supplementary_is_flagged(self):
        errors = validate_figure_profile(
            "01-x", valid_profile(supplementary_figures=["fig2", "figS1"])
        )
        self.assertTrue(any("both main and supplementary" in error for error in errors))


class TestValidateAttemptFolder(unittest.TestCase):
    def build_folder(self, tmp: str, attempt_id: str, profile: dict | None, figures: tuple[str, ...]):
        folder = Path(tmp) / attempt_id
        (folder / "figures").mkdir(parents=True)
        (folder / "venue.md").write_text("# Venue\n", encoding="utf-8")
        if profile is not None:
            (folder / "figure-profile.json").write_text(json.dumps(profile), encoding="utf-8")
        for name in figures:
            (folder / "figures" / name).write_bytes(b"")
        return Path(tmp)

    def attempt(self, status: str = "submitted") -> dict:
        with TemporaryDirectory() as tmp:
            return parse_attempts(write_log(tmp, attempt_block("01-applied-energy", status=status)))[0]

    def test_folder_with_profile_and_rendered_figures_passes(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(
                tmp, "01-applied-energy", valid_profile(), ("fig1.tiff", "fig2.tiff")
            )
            self.assertEqual(validate_attempt_folder(self.attempt(), root), [])

    def test_missing_rendered_figure_is_flagged(self):
        """The profile promises fig2; the folder does not hold it."""
        with TemporaryDirectory() as tmp:
            root = self.build_folder(tmp, "01-applied-energy", valid_profile(), ("fig1.tiff",))
            errors = validate_attempt_folder(self.attempt(), root)
            self.assertTrue(any("fig2.tiff" in error for error in errors))

    def test_missing_profile_is_flagged(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(tmp, "01-applied-energy", None, ())
            errors = validate_attempt_folder(self.attempt(), root)
            self.assertTrue(any("figure-profile.json" in error for error in errors))

    def test_preparing_attempt_is_not_checked_yet(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(tmp, "01-applied-energy", None, ())
            self.assertEqual(validate_attempt_folder(self.attempt(status="preparing"), root), [])

    def test_venue_change_needs_its_own_render(self):
        """Attempt 02 at a vector-format venue cannot reuse attempt 01's TIFFs."""
        with TemporaryDirectory() as tmp:
            root = self.build_folder(
                tmp, "02-energy-conversion", valid_profile(format="eps"), ("fig1.tiff", "fig2.tiff")
            )
            attempt = parse_attempts(
                write_log(tmp, attempt_block("02-energy-conversion", status="submitted"))
            )[0]
            errors = validate_attempt_folder(attempt, root)
            self.assertTrue(any("fig1.eps" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
