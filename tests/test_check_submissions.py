import json
import subprocess
import sys
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
    manuscript_tag: str | None = "submission/01-applied-energy/v1",
    carried_forward: str | None = None,
    reviewer_points: tuple[str, ...] = (),
    no_feedback_reason: str | None = None,
) -> str:
    lines = [
        f"## Attempt: {attempt_id}",
        f"venue: {venue}",
        f"status: {status}",
        f"submitted-on: {submitted_on or ''}",
        f"decision-on: {decision_on or ''}",
        f"manuscript-tag: {manuscript_tag or ''}",
        f"carried-forward: {carried_forward or ''}",
        f"no-feedback-reason: {no_feedback_reason or ''}",
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

    def test_minor_revision_allows_decision_date(self):
        attempt = self.parse_one(
            attempt_block(
                "01-applied-energy",
                status="minor-revision",
                decision_on="2026-03-02",
                reviewer_points=("clarify sensitivity analysis",),
            )
        )
        self.assertEqual(validate_attempt(attempt, today=TODAY), [])

    def test_carry_forward_requires_feedback_or_explicit_reason(self):
        attempt = self.parse_one(
            attempt_block(
                "01-applied-energy",
                status="rejected",
                decision_on="2026-03-02",
                carried_forward="yes",
            )
        )
        errors = validate_attempt(attempt, today=TODAY)
        self.assertTrue(any("reviewer-points or no-feedback-reason" in error for error in errors))

    def test_carry_forward_allows_explicit_no_feedback_reason(self):
        attempt = self.parse_one(
            attempt_block(
                "01-applied-energy",
                status="desk-rejected",
                decision_on="2026-03-02",
                carried_forward="yes",
                no_feedback_reason="Desk rejection returned only an out-of-scope form letter.",
            )
        )
        self.assertEqual(validate_attempt(attempt, today=TODAY), [])


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
                    manuscript_tag="submission/02-energy-conversion/v1",
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
                    manuscript_tag="submission/02-energy-conversion/v1",
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
                    manuscript_tag="submission/02-energy-conversion/v1",
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
                    manuscript_tag="submission/02-energy-conversion/v1",
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


def valid_revision_history(
    attempt_id: str,
    tag: str | None = None,
    commit: str = "1" * 40,
    date_value: str = "2026-01-10",
) -> dict:
    return {
        "attempt": attempt_id,
        "versions": [
            {
                "version": 1,
                "date": date_value,
                "tag": tag or f"submission/{attempt_id}/v1",
                "commit": commit,
            }
        ],
    }


def run_git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        raise unittest.SkipTest("git is not available")
    return result.stdout


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

    def test_figure_names_must_be_safe_basenames(self):
        errors = validate_figure_profile("01-x", valid_profile(main_figures=["../shared"]))
        self.assertTrue(any("safe figure basenames" in error for error in errors))


class TestValidateAttemptFolder(unittest.TestCase):
    def build_folder(
        self,
        tmp: str,
        attempt_id: str,
        profile: dict | None,
        figures: tuple[str, ...],
        revision_history: dict | None | bool = True,
    ):
        folder = Path(tmp) / attempt_id
        (folder / "figures").mkdir(parents=True)
        (folder / "venue.md").write_text("# Venue\n", encoding="utf-8")
        if profile is not None:
            (folder / "figure-profile.json").write_text(json.dumps(profile), encoding="utf-8")
        if revision_history is True:
            revision_history = valid_revision_history(attempt_id)
        if revision_history is not None:
            (folder / "revision-history.json").write_text(
                json.dumps(revision_history), encoding="utf-8"
            )
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

    def test_malformed_profile_is_flagged(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "01-applied-energy"
            (folder / "figures").mkdir(parents=True)
            (folder / "venue.md").write_text("# Venue\n", encoding="utf-8")
            (folder / "figure-profile.json").write_text("{", encoding="utf-8")
            (folder / "revision-history.json").write_text(
                json.dumps(valid_revision_history("01-applied-energy")), encoding="utf-8"
            )
            errors = validate_attempt_folder(self.attempt(), root)
            self.assertTrue(any("figure-profile.json cannot be read" in error for error in errors))

    def test_missing_supplementary_figure_is_flagged(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(
                tmp,
                "01-applied-energy",
                valid_profile(supplementary_figures=["supp1"]),
                ("fig1.tiff", "fig2.tiff"),
            )
            errors = validate_attempt_folder(self.attempt(), root)
            self.assertTrue(any("supp1.tiff" in error for error in errors))

    def test_unsafe_figure_name_does_not_escape_figures_dir(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(
                tmp,
                "01-applied-energy",
                valid_profile(main_figures=["../shared"]),
                ("fig1.tiff", "fig2.tiff"),
            )
            (Path(tmp) / "shared.tiff").write_bytes(b"")
            errors = validate_attempt_folder(self.attempt(), root)
            self.assertTrue(any("safe figure basenames" in error for error in errors))

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

    def test_missing_revision_history_is_flagged_after_submission(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(
                tmp,
                "01-applied-energy",
                valid_profile(),
                ("fig1.tiff", "fig2.tiff"),
                revision_history=None,
            )
            errors = validate_attempt_folder(self.attempt(), root)
            self.assertTrue(any("revision-history.json" in error for error in errors))

    def test_revision_history_requires_current_manuscript_tag(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(
                tmp,
                "01-applied-energy",
                valid_profile(),
                ("fig1.tiff", "fig2.tiff"),
                revision_history=valid_revision_history("01-applied-energy", tag="submission/wrong/v1"),
            )
            errors = validate_attempt_folder(self.attempt(), root)
            self.assertTrue(any("must equal latest revision tag" in error for error in errors))

    def test_revision_history_git_tag_must_match_commit_when_checked(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_git(root, "init")
            run_git(root, "config", "user.email", "tests@example.com")
            run_git(root, "config", "user.name", "Tests")
            (root / "paper.txt").write_text("v1\n", encoding="utf-8")
            run_git(root, "add", "paper.txt")
            run_git(root, "commit", "-m", "v1")
            commit = run_git(root, "rev-parse", "HEAD").strip()
            run_git(root, "tag", "submission/01-applied-energy/v1")
            history = valid_revision_history("01-applied-energy", commit="0" * 40)
            attempts_dir = self.build_folder(
                tmp, "01-applied-energy", valid_profile(), ("fig1.tiff", "fig2.tiff"), history
            )
            errors = validate_attempt_folder(
                self.attempt(), attempts_dir, repo_dir=root, check_git_tags=True
            )
            self.assertTrue(any(commit[:12] in error and "does not match" in error for error in errors))


class TestSubmissionRegressions(unittest.TestCase):
    build_folder = TestValidateAttemptFolder.build_folder
    attempt = TestValidateAttemptFolder.attempt

    def test_preflight_preparing_validates_package_without_receipt(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(tmp, '01-applied-energy', valid_profile(),
                                     ('fig1.tiff',), revision_history=None)
            attempt = self.attempt(status='preparing')
            errors = validate_attempt_folder(attempt, root, preflight=True)
            self.assertTrue(any('fig2.tiff' in e for e in errors))
            self.assertFalse(any('revision-history' in e for e in errors))
            (root / '01-applied-energy/figures/fig2.tiff').write_bytes(b'figure')
            self.assertEqual(validate_attempt_folder(attempt, root, preflight=True), [])

    def test_preflight_preparing_missing_folder_fails(self):
        with TemporaryDirectory() as tmp:
            self.assertTrue(validate_attempt_folder(self.attempt(status='preparing'),
                                                   Path(tmp), preflight=True))

    def test_preflight_cli_rejects_unsafe_preparing_supplementary(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(tmp, '01-applied-energy',
                valid_profile(supplementary_figures=['../outside']),
                ('fig1.tiff', 'fig2.tiff'), revision_history=None)
            log = write_log(tmp, attempt_block('01-applied-energy', status='preparing',
                submitted_on=None, manuscript_tag=None))
            script = Path(__file__).resolve().parents[1] / 'scripts/check_submissions.py'
            command = [sys.executable, str(script), '--log', str(log), '--preflight']
            result = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn('safe figure basenames', result.stdout)
            (root / '01-applied-energy/figure-profile.json').write_text(
                json.dumps(valid_profile()), encoding='utf-8')
            result = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    def test_both_figure_lists_reject_path_variants(self):
        for field in ('main_figures', 'supplementary_figures'):
            for name in ('../shared', '..\\shared', '/absolute', 'C:\\outside', 'fig.pdf'):
                with self.subTest(field=field, name=name):
                    self.assertTrue(validate_figure_profile('01-x', valid_profile(**{field: [name]})))

    def test_symlink_figure_cannot_escape(self):
        with TemporaryDirectory() as tmp:
            root = self.build_folder(tmp, '01-applied-energy', valid_profile(main_figures=['fig1']), ())
            outside = root / 'outside.tiff'
            outside.write_bytes(b'outside')
            try:
                (root / '01-applied-energy/figures/fig1.tiff').symlink_to(outside)
            except OSError:
                self.skipTest('symlink creation unavailable')
            self.assertTrue(any('escapes' in e for e in validate_attempt_folder(self.attempt(), root)))

    def test_revision_dates_and_latest_receipt(self):
        with TemporaryDirectory() as tmp:
            history = valid_revision_history('01-applied-energy')
            history['versions'].append(dict(version=2, date='2026-01-09',
                tag='submission/01-applied-energy/v2', commit='2' * 40))
            root = self.build_folder(tmp, '01-applied-energy', valid_profile(), ('fig1.tiff', 'fig2.tiff'), history)
            attempt = self.attempt()
            attempt['manuscript-tag'] = 'submission/01-applied-energy/v2'
            errors = validate_attempt_folder(attempt, root)
            self.assertTrue(any('precedes previous revision' in e for e in errors))
            self.assertTrue(any('submitted-on must equal' in e for e in errors))
            history['versions'][1]['date'] = '2026-03-01'
            (root / '01-applied-energy/revision-history.json').write_text(json.dumps(history), encoding='utf-8')
            attempt['submitted-on'] = '2026-03-01'
            self.assertEqual(validate_attempt_folder(attempt, root), [])

    def test_cli_checks_real_git_tags(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_git(root, 'init')
            run_git(root, 'config', 'user.email', 'tests@example.com')
            run_git(root, 'config', 'user.name', 'Tests')
            (root / 'paper.txt').write_text('v1', encoding='utf-8')
            run_git(root, 'add', 'paper.txt')
            run_git(root, 'commit', '-m', 'v1')
            commit = run_git(root, 'rev-parse', 'HEAD').strip()
            self.build_folder(tmp, '01-applied-energy', valid_profile(), ('fig1.tiff', 'fig2.tiff'),
                valid_revision_history('01-applied-energy', commit=commit))
            log = write_log(tmp, attempt_block('01-applied-energy'))
            script = Path(__file__).resolve().parents[1] / 'scripts/check_submissions.py'
            def check():
                return subprocess.run([sys.executable, str(script), '--log', str(log)],
                    cwd=root, capture_output=True, text=True)
            self.assertNotEqual(check().returncode, 0)
            run_git(root, 'tag', 'submission/01-applied-energy/v1', commit)
            result = check()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_active_attempt_blocks_preparing_next_venue(self):
        with TemporaryDirectory() as tmp:
            log = write_log(tmp, attempt_block('01-applied-energy'),
                attempt_block('02-next', status='preparing', submitted_on=None, manuscript_tag=None))
            self.assertTrue(any('still active' in e for e in validate_ledger(log)['__ledger__']))


if __name__ == "__main__":
    unittest.main()
