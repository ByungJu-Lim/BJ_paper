import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_paper_state import (open_preconditions, parse_stages, validate_all,
                                       validate_outline_artifacts, validate_preconditions,
                                       validate_stage)
from tests.state_fixture import build_state


def write_state(tmp_dir: str, content: str) -> Path:
    state_path = Path(tmp_dir) / "paper-state.md"
    state_path.write_text(content, encoding="utf-8")
    return state_path


def stage_block(
    stage_id: str,
    status: str = "not-started",
    round_value: str = "0/3",
    verdict: str = "",
    extra: str = "",
) -> str:
    artifact_ledger = ""
    if stage_id == "outline-draft" and "artifacts:" not in extra:
        if status == "not-started":
            artifact_statuses = ("not-started",) * 4
        elif status == "in-progress":
            artifact_statuses = ("in-progress", "not-started", "not-started", "not-started")
        else:
            artifact_statuses = ("approved",) * 4
        artifact_ledger = "artifacts:\n" + "".join(
            f"- {artifact_id}: {artifact_status}, "
            f"round {'0/3' if artifact_status == 'not-started' else '1/3'}, "
            f"verdict {'none' if artifact_status in {'not-started', 'in-progress'} else 'pass'}\n"
            for artifact_id, artifact_status in zip(
                ("outline", "introduction", "related-work", "methods"), artifact_statuses
            )
        )
    return (
        f"## Stage: {stage_id}\n"
        f"status: {status}\n"
        f"round: {round_value}\n"
        f"last-critic-verdict: {verdict}\n"
        "last-critic-issues:\n"
        f"{extra}"
        f"{artifact_ledger}"
    )


def valid_state(**overrides: dict) -> str:
    stages = [
        "story-brief",
        "lit-review",
        "novelty-check",
        "outline-draft",
        "code-experiment",
        "results-discussion",
        "figures-tables",
        "citation-manage",
        "polish-review",
    ]
    blocks = []
    for stage_id in stages:
        fields = {
            "status": "not-started",
            "round_value": "0/3",
            "verdict": "",
            "extra": "",
        }
        fields.update(overrides.get(stage_id, {}))
        if stage_id == "citation-manage":
            fields["extra"] += "verified-sources: 0\nrejected-citations:\n"
        blocks.append(stage_block(stage_id, **fields))
    return "# Paper State\n\n" + "\n".join(blocks)


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
    def test_pending_states_cannot_claim_impossible_review_history(self):
        for status, verdict in [('not-started', 'pass'), ('awaiting-review', None)]:
            with self.subTest(status=status):
                self.assertTrue(validate_stage({'id': 'story-brief', 'status': status,
                    'round': '0/3', 'last-critic-verdict': verdict, 'last-critic-issues': []}))

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
        self.assertIn("reached without status 'escalated'", errors[0])

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

    def test_not_started_stage_must_not_retain_verdict(self):
        stage = {
            "id": "outline-draft",
            "status": "not-started",
            "round": "0/3",
            "last-critic-verdict": "pass",
            "last-critic-issues": [],
        }
        self.assertTrue(any("must not retain a critic verdict" in error for error in validate_stage(stage)))

    def test_awaiting_review_requires_review_round(self):
        stage = {
            "id": "outline-draft",
            "status": "awaiting-review",
            "round": "0/3",
            "last-critic-verdict": None,
            "last-critic-issues": [],
        }
        self.assertTrue(any("requires at least one generation round" in error for error in validate_stage(stage)))


class TestValidateAll(unittest.TestCase):
    def test_returns_only_stages_with_errors(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                "## Stage: story-brief\n"
                "status: approved\n"
                "round: 1/3\n"
                "last-critic-verdict: pass\n"
                "last-critic-issues:\n\n"
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
                "## Stage: outline-draft\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n"
                "artifacts:\n- outline: not-started, round 0/3, verdict none\n"
                "- introduction: not-started, round 0/3, verdict none\n"
                "- related-work: not-started, round 0/3, verdict none\n"
                "- methods: not-started, round 0/3, verdict none\n\n"
                "## Stage: code-experiment\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: results-discussion\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: figures-tables\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\nlast-critic-issues:\n\n"
                "## Stage: citation-manage\nstatus: not-started\nround: 0/3\nlast-critic-verdict:\n"
                "last-critic-issues:\nverified-sources: 0\nrejected-citations:\n\n"
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

    def test_approved_without_round_or_verdict_is_flagged(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                valid_state(
                    **{
                        "story-brief": {
                            "status": "approved",
                            "round_value": "",
                            "verdict": "",
                        }
                    }
                ),
            )
            errors = validate_all(state_path)["story-brief"]
            self.assertTrue(any("round is required" in error for error in errors))
            self.assertTrue(any("requires last-critic-verdict 'pass'" in error for error in errors))

    def test_approved_after_revise_at_max_round_is_flagged(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                valid_state(
                    **{
                        "story-brief": {
                            "status": "approved",
                            "round_value": "3/3",
                            "verdict": "revise",
                        }
                    }
                ),
            )
            errors = validate_all(state_path)["story-brief"]
            self.assertTrue(any("requires last-critic-verdict 'pass'" in error for error in errors))
            self.assertTrue(any("reached without status 'escalated'" in error for error in errors))

    def test_downstream_stage_requires_approved_prerequisites(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                valid_state(
                    **{
                        "story-brief": {
                            "status": "in-progress",
                            "round_value": "2/3",
                            "verdict": "revise",
                        },
                        "lit-review": {
                            "status": "approved",
                            "round_value": "1/3",
                            "verdict": "pass",
                        },
                    }
                ),
            )
            errors = validate_all(state_path)["lit-review"]
            self.assertTrue(any("requires approved prerequisites: story-brief" in error for error in errors))

    def test_results_and_figures_depend_on_code_experiment(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                valid_state(
                    **{
                        "story-brief": {
                            "status": "approved",
                            "round_value": "1/3",
                            "verdict": "pass",
                        },
                        "lit-review": {
                            "status": "approved",
                            "round_value": "1/3",
                            "verdict": "pass",
                        },
                        "novelty-check": {
                            "status": "approved",
                            "round_value": "1/3",
                            "verdict": "pass",
                        },
                        "outline-draft": {
                            "status": "approved",
                            "round_value": "1/3",
                            "verdict": "pass",
                        },
                        "results-discussion": {
                            "status": "awaiting-user",
                            "round_value": "1/3",
                            "verdict": "pass",
                        },
                        "figures-tables": {
                            "status": "awaiting-review",
                            "round_value": "1/3",
                            "verdict": "",
                        },
                    }
                ),
            )
            report = validate_all(state_path)
            self.assertTrue(
                any("requires approved prerequisites: code-experiment" in error for error in report["results-discussion"])
            )
            self.assertTrue(
                any("requires approved prerequisites: code-experiment" in error for error in report["figures-tables"])
            )

    def test_duplicate_scalar_fields_are_flagged(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                "## Stage: story-brief\n"
                "status: not-started\n"
                "status: approved\n"
                "round: 0/3\n"
                "last-critic-verdict: pass\n"
                "last-critic-issues:\n",
            )
            self.assertTrue(
                any("duplicate scalar field 'status'" in error for error in validate_all(state_path)["story-brief"])
            )


class TestOutlineArtifacts(unittest.TestCase):
    def stage(self, status="in-progress", artifacts=None) -> dict:
        return {
            "id": "outline-draft",
            "status": status,
            "artifacts": artifacts or [],
        }

    def test_parses_artifact_ledger(self):
        with TemporaryDirectory() as tmp:
            path = write_state(
                tmp,
                "## Stage: outline-draft\n"
                "status: in-progress\nround: 0/3\nlast-critic-verdict:\n"
                "last-critic-issues:\nartifacts:\n"
                "- outline: approved, round 3/3, verdict pass\n"
                "- introduction: awaiting-user, round 2/3, verdict pass\n"
                "- related-work: not-started, round 0/3, verdict none\n"
                "- methods: not-started, round 0/3, verdict none\n",
            )
            stage = parse_stages(path)[0]
            self.assertEqual(len(stage["artifacts"]), 4)
            self.assertTrue(stage["artifacts"][1].startswith("introduction:"))

    def test_requires_complete_artifact_ledger(self):
        errors = validate_outline_artifacts(self.stage(artifacts=[]))
        self.assertTrue(any("requires artifacts" in error for error in errors), errors)

    def test_approved_stage_requires_every_artifact_approved(self):
        artifacts = [
            "outline: approved, round 1/3, verdict pass",
            "introduction: approved, round 1/3, verdict pass",
            "related-work: awaiting-user, round 1/3, verdict pass",
            "methods: approved, round 1/3, verdict pass",
        ]
        errors = validate_outline_artifacts(self.stage(status="approved", artifacts=artifacts))
        self.assertTrue(any("cannot be approved" in error for error in errors), errors)

    def test_artifact_at_third_revise_must_escalate(self):
        artifacts = [
            "outline: approved, round 1/3, verdict pass",
            "introduction: approved, round 1/3, verdict pass",
            "related-work: in-progress, round 3/3, verdict revise",
            "methods: not-started, round 0/3, verdict none",
        ]
        errors = validate_outline_artifacts(self.stage(artifacts=artifacts))
        self.assertTrue(any("related-work" in error and "escalated" in error for error in errors), errors)

    def test_valid_artifact_ledger_passes(self):
        artifacts = [
            "outline: approved, round 3/3, verdict pass",
            "introduction: approved, round 2/3, verdict pass",
            "related-work: awaiting-review, round 1/3, verdict none",
            "methods: not-started, round 0/3, verdict none",
        ]
        self.assertEqual(validate_outline_artifacts(self.stage(artifacts=artifacts)), [])


class TestCitationBookkeeping(unittest.TestCase):
    def stage(self, **overrides) -> dict:
        base = {
            "id": "citation-manage",
            "status": "in-progress",
            "round": "1/3",
            "last-critic-verdict": None,
            "verified-sources": "4",
            "last-critic-issues": [],
            "rejected-citations": [],
        }
        base.update(overrides)
        return base

    def test_valid_citation_stage_has_no_errors(self):
        self.assertEqual(validate_stage(self.stage()), [])

    def test_missing_verified_sources_is_flagged(self):
        errors = validate_stage(self.stage(**{"verified-sources": None}))
        self.assertTrue(any("verified-sources is required" in error for error in errors))

    def test_non_numeric_verified_sources_is_flagged(self):
        errors = validate_stage(self.stage(**{"verified-sources": "many"}))
        self.assertTrue(any("non-negative integer" in error for error in errors))

    def test_approved_with_zero_verified_sources_is_flagged(self):
        errors = validate_stage(self.stage(status="approved", **{"verified-sources": "0"}))
        self.assertTrue(any("approved with verified-sources 0" in error for error in errors))

    def test_other_stage_must_not_carry_verified_sources(self):
        errors = validate_stage(self.stage(id="lit-review", **{"verified-sources": "3"}))
        self.assertTrue(any("belongs to citation-manage only" in error for error in errors))

    def test_rejected_citations_are_parsed_as_a_list(self):
        with TemporaryDirectory() as tmp:
            state_path = write_state(
                tmp,
                "## Stage: citation-manage\n"
                "status: in-progress\n"
                "round: 1/3\n"
                "last-critic-verdict: revise\n"
                "last-critic-issues:\n"
                '  - "one issue"\n'
                "verified-sources: 2\n"
                "rejected-citations:\n"
                '  - "ghost2021: not in retrieved-sources.json"\n'
                '  - "smith2019: retracted"\n',
            )
            stage = parse_stages(state_path)[0]
            self.assertEqual(stage["last-critic-issues"], ["one issue"])
            self.assertEqual(
                stage["rejected-citations"],
                ["ghost2021: not in retrieved-sources.json", "smith2019: retracted"],
            )


class TestPreconditions(unittest.TestCase):
    """A review at one stage routinely turns up something a later stage must settle.

    Prose in a notes file cannot bind that stage - the later session has no
    structural reason to open the file. These tests pin the mechanism that does.
    """

    def validate(self, tmp_dir: str, **kwargs) -> dict:
        path = write_state(tmp_dir, build_state(**kwargs))
        return validate_all(path)

    def test_an_open_precondition_blocks_approval(self):
        with TemporaryDirectory() as tmp:
            report = self.validate(
                tmp,
                statuses={"story-brief": "approved", "lit-review": "approved",
                          "novelty-check": "approved"},
                preconditions={"novelty-check": ["open: settle the Gap's trailing clause"]},
            )
            errors = report.get("novelty-check", [])
            self.assertTrue(any("cannot be approved with 1 open precondition" in e for e in errors),
                            errors)
            self.assertTrue(any("settle the Gap's trailing clause" in e for e in errors),
                            "the error must name what is owed, or it cannot be acted on")

    def test_resolving_it_unblocks_approval(self):
        with TemporaryDirectory() as tmp:
            report = self.validate(
                tmp,
                statuses={"story-brief": "approved", "lit-review": "approved",
                          "novelty-check": "approved"},
                preconditions={"novelty-check": ["resolved: settled the Gap's trailing clause"]},
            )
            self.assertEqual(report, {})

    def test_a_resolved_precondition_is_kept_not_deleted(self):
        """The record of what was owed is worth as much as the fact it was paid."""
        with TemporaryDirectory() as tmp:
            path = write_state(tmp, build_state(
                preconditions={"code-experiment": ["resolved: registered Kennedy and O'Hagan"]}))
            stage = {s["id"]: s for s in parse_stages(path)}["code-experiment"]
            self.assertEqual(stage["preconditions"], ["resolved: registered Kennedy and O'Hagan"])
            self.assertEqual(open_preconditions(stage), [])

    def test_open_preconditions_do_not_block_earlier_statuses(self):
        """They gate approval, not work: the stage still has to be worked on."""
        with TemporaryDirectory() as tmp:
            report = self.validate(
                tmp,
                statuses={"story-brief": "approved", "lit-review": "approved",
                          "novelty-check": "in-progress"},
                preconditions={"novelty-check": ["open: settle the Gap's trailing clause"]},
            )
            self.assertEqual(report, {})

    def test_a_malformed_precondition_is_rejected(self):
        with TemporaryDirectory() as tmp:
            report = self.validate(
                tmp, preconditions={"code-experiment": ["settle this eventually"]})
            errors = report.get("code-experiment", [])
            self.assertTrue(any("must read 'open:" in e for e in errors), errors)

    def test_several_open_preconditions_are_all_named(self):
        stage = {"id": "code-experiment", "status": "approved",
                 "preconditions": ["open: first", "resolved: second", "open: third"]}
        errors = validate_preconditions(stage)
        self.assertEqual(len(errors), 1)
        self.assertIn("2 open precondition", errors[0])
        self.assertIn("first", errors[0])
        self.assertIn("third", errors[0])
        self.assertNotIn("second", errors[0])


if __name__ == "__main__":
    unittest.main()
