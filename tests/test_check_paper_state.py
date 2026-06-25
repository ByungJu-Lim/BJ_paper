import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_paper_state import parse_stages


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


if __name__ == "__main__":
    unittest.main()
