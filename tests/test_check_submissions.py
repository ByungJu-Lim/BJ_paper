import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_submissions import parse_attempts, validate_attempt, validate_ledger

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


if __name__ == "__main__":
    unittest.main()
