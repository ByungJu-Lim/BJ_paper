import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_paper_state import parse_stages, validate_all, validate_stage


def write_state(tmp_dir: str, content: str) -> Path:
    state_path = Path(tmp_dir) / "paper-state.md"
    state_path.write_text(content, encoding="utf-8")
    return state_path


class TestParseStages(unittest.TestCase):
    def test_parses_single_stage_scalar_fields(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                "# Paper State\n\n"
                "## Stage: outline-draft\n"
                "status: approved\n"
                "round: 2/3\n"
                "last-critic-verdict: pass\n"
                "last-critic-issues:\n",
            )
            stages = parse_stages(state_path)
            self.assertEqual(len(stages), 1)
            self.assertEqual(stages[0]["id"], "outline-draft")
            self.assertEqual(stages[0]["status"], "approved")
            self.assertEqual(stages[0]["round"], "2/3")
            self.assertEqual(stages[0]["last-critic-verdict"], "pass")
            self.assertEqual(stages[0]["last-critic-issues"], [])

    def test_parses_multiple_stages(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                "## Stage: lit-review\n"
                "status: not-started\n"
                "round: 0/3\n"
                "last-critic-verdict:\n"
                "last-critic-issues:\n\n"
                "## Stage: novelty-check\n"
                "status: in-progress\n"
                "round: 1/3\n"
                "last-critic-verdict:\n"
                "last-critic-issues:\n",
            )
            stages = parse_stages(state_path)
            self.assertEqual([stage["id"] for stage in stages], ["lit-review", "novelty-check"])
            self.assertIsNone(stages[0]["last-critic-verdict"])

    def test_parses_critic_issues_list(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                "## Stage: draft-introduction\n"
                "status: awaiting-review\n"
                "round: 1/3\n"
                "last-critic-verdict: revise\n"
                'last-critic-issues:\n  - "Research gap is unclear"\n  - "Cite novelty-matrix"\n',
            )
            stages = parse_stages(state_path)
            self.assertEqual(
                stages[0]["last-critic-issues"],
                ["Research gap is unclear", "Cite novelty-matrix"],
            )

    def test_unrelated_fields_after_issues_do_not_crash(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                "## Stage: citation-manage\n"
                "status: not-started\n"
                "round: 0/3\n"
                "last-critic-verdict:\n"
                "last-critic-issues:\n"
                "verified-sources: 0\n"
                "rejected-citations:\n",
            )
            stages = parse_stages(state_path)
            self.assertEqual(stages[0]["status"], "not-started")
            self.assertEqual(stages[0]["last-critic-issues"], [])


class TestValidateStage(unittest.TestCase):
    def test_valid_stage_has_no_errors(self):
        stage = {
            "id": "outline-draft",
            "status": "approved",
            "round": "2/3",
            "last-critic-verdict": "pass",
            "last-critic-issues": [],
        }
        self.assertEqual(validate_stage(stage), [])

    def test_invalid_status_is_flagged(self):
        stage = {
            "id": "outline-draft",
            "status": "done",
            "round": "0/3",
            "last-critic-verdict": None,
            "last-critic-issues": [],
        }
        errors = validate_stage(stage)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid status", errors[0])

    def test_invalid_round_format_is_flagged(self):
        stage = {
            "id": "outline-draft",
            "status": "in-progress",
            "round": "two of three",
            "last-critic-verdict": None,
            "last-critic-issues": [],
        }
        errors = validate_stage(stage)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid round format", errors[0])

    def test_round_exceeded_without_escalation_is_flagged(self):
        stage = {
            "id": "outline-draft",
            "status": "in-progress",
            "round": "3/3",
            "last-critic-verdict": "revise",
            "last-critic-issues": ["still unclear"],
        }
        errors = validate_stage(stage)
        self.assertEqual(len(errors), 1)
        self.assertIn("reached without status 'escalated' or 'approved'", errors[0])

    def test_round_exceeded_with_escalated_status_passes(self):
        stage = {
            "id": "outline-draft",
            "status": "escalated",
            "round": "3/3",
            "last-critic-verdict": "revise",
            "last-critic-issues": ["still unclear"],
        }
        self.assertEqual(validate_stage(stage), [])

    def test_invalid_verdict_is_flagged(self):
        stage = {
            "id": "outline-draft",
            "status": "in-progress",
            "round": "1/3",
            "last-critic-verdict": "looks great",
            "last-critic-issues": [],
        }
        errors = validate_stage(stage)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid last-critic-verdict", errors[0])

    def test_round_denominator_must_be_three(self):
        stage = {
            "id": "outline-draft",
            "status": "in-progress",
            "round": "1/4",
            "last-critic-verdict": None,
            "last-critic-issues": [],
        }
        self.assertTrue(any("denominator" in error for error in validate_stage(stage)))

    def test_not_started_stage_must_be_round_zero(self):
        stage = {
            "id": "outline-draft",
            "status": "not-started",
            "round": "1/3",
            "last-critic-verdict": None,
            "last-critic-issues": [],
        }
        self.assertTrue(any("not-started" in error for error in validate_stage(stage)))


class TestValidateAll(unittest.TestCase):
    def test_returns_only_stages_with_errors(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                "## Stage: lit-review\n"
                "status: approved\n"
                "round: 1/3\n"
                "last-critic-verdict: pass\n"
                "last-critic-issues:\n\n"
                "## Stage: novelty-check\n"
                "status: bogus\n"
                "round: 0/3\n"
                "last-critic-verdict:\n"
                "last-critic-issues:\n\n"
                "## Stage: outline-draft\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: results-discussion\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: code-experiment\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: figures-tables\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: citation-manage\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: polish-review\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n",
            )
            report = validate_all(state_path)
            self.assertEqual(list(report.keys()), ["novelty-check"])

    def test_missing_duplicate_and_out_of_order_stages_are_flagged(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                "## Stage: novelty-check\nstatus: not-started\nround: 0/3\n"
                "last-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: lit-review\nstatus: not-started\nround: 0/3\n"
                "last-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: lit-review\nstatus: not-started\nround: 0/3\n"
                "last-critic-verdict:\nlast-critic-issues:\n",
            )
            errors = validate_all(state_path)["__workflow__"]
            self.assertTrue(any("duplicate" in error for error in errors))
            self.assertTrue(any("missing" in error for error in errors))
            self.assertTrue(any("order" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
