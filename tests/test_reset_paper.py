"""Tests for scripts/reset_paper.py.

Every fixture here is synthetic and lives in a TemporaryDirectory. Like the rest
of the suite (see tests/state_fixture.py), these tests never read the live
workflow ledger - a reset test that reached the real repository would both go
red as the manuscript advances and, on --confirm, destroy it. The ledger path
comes from scripts.reset_paper.STATE_FILE and is always joined onto a temporary
root.
"""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.reset_paper import STAGES, STATE_FILE, build_plan, reset_narrative_and_claims
from tests.state_fixture import write_state

STORY_BRIEF = """# Story Brief

## Narrative

| Slot | Sentence |
|---|---|
| Context | Fouling degrades heat transfer. |
| Gap | Nobody compared the two surrogates. |
| Question | Does the hybrid extrapolate better? |
| Approach | _입력 필요_ |
| Finding | _입력 필요_ |
| Implication | _입력 필요_ |

## Claims

| Form | Meaning | Checked against |
|---|---|---|
| `@key` | a registered source | `docs/notes/retrieved-sources.json` |

| ID | Claim | Status | Evidence |
|---|---|---|---|
| C0 | The correlation is published. | assumed | |
| C1 | Extrapolation is harder. | supported | @prev2024source |

## Falsifiers

- **C0:** Refuted if the correlation already explains the data.
- **C1:** Refuted if the gap is below 1.5x.

## Evidence format

Prose that explains the format and must survive a reset.
"""

CLAUDE_MD = """# 논문 작성 에이전트 프로젝트

- **가제:** A Previous Paper
- **목표 학술지/학회:** _입력 필요_
- **분야:** 공학
- **작성 언어:** 영어

> **⚠️ 이 저장소의 논문은 투고용이 아닙니다.**
>
> 검증용 워크로드입니다.

## 작업 흐름

This prose is the template and must survive.

- 원격을 Gitea(`origin`)와 GitHub(`github`) 둘로 운영하는 경우, 푸시는 하나로 끝냅니다.
- This rule is about the paper and must survive.
"""

README_MD = """# 논문 작성 에이전트 템플릿

- 이 저장소(Gitea 원본 및/또는 GitHub 미러)에 대한 클론 권한

## 빠른 시작

1. Clone it.
   원격을 둘 운영한다면 `git config core.hooksPath .githooks`를 실행하세요.

## 원격 두 곳 운영 (선택)

Gitea를 원본으로 두고 GitHub를 push mirror로 미러링하는 구성 설명.

```bash
git config core.hooksPath .githooks
```

## 안전성과 설계 원칙

This section must survive.
"""


def build_repo(root: Path) -> None:
    """A miniature paper repository carrying one previous paper's work."""
    (root / ".omc").mkdir()
    write_state(root / STATE_FILE, {"story-brief": "approved"})
    (root / "docs/notes").mkdir(parents=True)
    (root / "docs/sections").mkdir(parents=True)
    (root / "docs/sources").mkdir(parents=True)
    (root / "docs/notes/story-brief.md").write_text(STORY_BRIEF, encoding="utf-8")
    (root / "docs/notes/retrieved-sources.json").write_text(
        json.dumps([{"key": "prev2024source", "title": "A Previous Paper's Source"}]),
        encoding="utf-8",
    )
    (root / "docs/notes/pipeline-findings.md").write_text("# findings\n", encoding="utf-8")
    (root / "docs/notes/fouling-topic-note.md").write_text("# topic note\n", encoding="utf-8")
    (root / "docs/sections/04-results.md").write_text(
        "# Results\n\n<!-- claims: C1 -->\n\nThe hybrid won.\n", encoding="utf-8")
    (root / "docs/sources/prev2024source.pdf").write_bytes(b"%PDF-1.4")
    (root / "refs").mkdir()
    (root / "refs/references.bib").write_text(
        "% Populated exclusively by the citation-manage skill.\n"
        "@article{prev2024source,\n  title = {A Previous Paper's Source},\n}\n",
        encoding="utf-8",
    )
    (root / "figures").mkdir()
    (root / "figures/.gitkeep").write_text("", encoding="utf-8")
    (root / "figures/fig1.png").write_bytes(b"\x89PNG")
    (root / "data/processed").mkdir(parents=True)
    (root / "data/raw").mkdir(parents=True)
    (root / "data/raw/measurements.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (root / "data/processed/run-1.manifest.json").write_text("{}", encoding="utf-8")
    (root / "submissions/_template").mkdir(parents=True)
    (root / "submissions/01-applied-thermal").mkdir(parents=True)
    (root / "submissions/01-applied-thermal/venue.md").write_text("venue\n", encoding="utf-8")
    (root / "submissions/submission-log.md").write_text(
        "# Submission Log\n\n> Maintained by submission-manage.\n\n"
        "## Attempt: 01-applied-thermal\nvenue: Applied Thermal Engineering\n",
        encoding="utf-8",
    )
    (root / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")
    (root / "README.md").write_text(README_MD, encoding="utf-8")
    (root / ".githooks").mkdir()
    (root / ".githooks/pre-push").write_text("#!/bin/sh\n", encoding="utf-8")


class ResetPaperTestCase(unittest.TestCase):
    def reset(self, confirm: bool = True, template_repo: bool = False):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        build_repo(root)
        return root, build_plan(root, confirm=confirm, template_repo=template_repo)


class TestDryRunIsInert(ResetPaperTestCase):
    def test_dry_run_writes_and_deletes_nothing(self):
        """The safety property the whole design rests on: no --confirm, no changes."""
        root, plan = self.reset(confirm=False)
        self.assertTrue(plan.actions, "a populated repository should have something to reset")
        self.assertEqual(
            json.loads((root / "docs/notes/retrieved-sources.json").read_text(encoding="utf-8")),
            [{"key": "prev2024source", "title": "A Previous Paper's Source"}],
        )
        self.assertIn("Fouling degrades heat transfer.",
                      (root / "docs/notes/story-brief.md").read_text(encoding="utf-8"))
        self.assertTrue((root / "docs/notes/fouling-topic-note.md").exists())
        self.assertTrue((root / "figures/fig1.png").exists())
        self.assertTrue((root / "submissions/01-applied-thermal").exists())


class TestConfirmedReset(ResetPaperTestCase):
    def test_previous_paper_argument_is_gone(self):
        root, _ = self.reset()
        brief = (root / "docs/notes/story-brief.md").read_text(encoding="utf-8")
        self.assertNotIn("Fouling degrades heat transfer.", brief)
        self.assertNotIn("| C0 |", brief)
        self.assertNotIn("**C1:**", brief)
        self.assertEqual(brief.count("_입력 필요_"), 6)

    def test_template_scaffolding_survives(self):
        """A reset that also destroys the instructions leaves an unusable repository."""
        root, _ = self.reset()
        brief = (root / "docs/notes/story-brief.md").read_text(encoding="utf-8")
        self.assertIn("Prose that explains the format and must survive a reset.", brief)
        self.assertIn("| `@key` | a registered source |", brief)
        self.assertIn("| ID | Claim | Status | Evidence |", brief)
        self.assertIn("This prose is the template and must survive.",
                      (root / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_registry_and_bibliography_are_emptied_but_keep_their_headers(self):
        root, _ = self.reset()
        self.assertEqual(
            json.loads((root / "docs/notes/retrieved-sources.json").read_text(encoding="utf-8")), [])
        bib = (root / "refs/references.bib").read_text(encoding="utf-8")
        self.assertNotIn("prev2024source", bib)
        self.assertIn("% Populated exclusively", bib)

    def test_every_stage_returns_to_not_started(self):
        root, _ = self.reset()
        state = (root / STATE_FILE).read_text(encoding="utf-8")
        for stage in STAGES:
            self.assertIn(f"## Stage: {stage}", state)
        self.assertEqual(state.count("status: not-started"), len(STAGES))
        self.assertNotIn("approved", state)
        self.assertNotIn("3/3", state)

    def test_verified_sources_is_written_only_for_citation_manage(self):
        """check_paper_state rejects that field on any other stage, so writing it
        onto every stage would produce a file the repository's own validator fails."""
        root, _ = self.reset()
        state = (root / STATE_FILE).read_text(encoding="utf-8")
        self.assertEqual(state.count("verified-sources: 0"), 1)
        citation_block = state.split("## Stage: citation-manage")[1].split("## Stage:")[0]
        self.assertIn("verified-sources: 0", citation_block)
        self.assertIn("rejected-citations:", citation_block)

    def test_claude_md_header_and_validation_marker(self):
        root, _ = self.reset()
        claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertNotIn("A Previous Paper", claude)
        self.assertNotIn("투고용이 아닙니다", claude)
        self.assertNotIn("검증용 워크로드입니다", claude)
        self.assertIn("- **가제:** _입력 필요_", claude)
        self.assertIn("- **작성 언어:** _입력 필요_", claude)

    def test_generated_artifacts_are_removed(self):
        root, _ = self.reset()
        self.assertFalse((root / "docs/notes/fouling-topic-note.md").exists())
        self.assertFalse((root / "figures/fig1.png").exists())
        self.assertFalse((root / "data/processed/run-1.manifest.json").exists())
        self.assertFalse((root / "docs/sources/prev2024source.pdf").exists())
        self.assertFalse((root / "submissions/01-applied-thermal").exists())
        self.assertNotIn("## Attempt:",
                         (root / "submissions/submission-log.md").read_text(encoding="utf-8"))
        self.assertFalse((root / "docs/sections/04-results.md").exists())
        self.assertIn("outline-draft", (root / "docs/outline.md").read_text(encoding="utf-8"))

    def test_raw_data_and_scaffolding_are_preserved(self):
        """data/raw holds inputs the script cannot regenerate and must never delete."""
        root, _ = self.reset()
        self.assertTrue((root / "data/raw/measurements.csv").exists())
        self.assertTrue((root / "figures/.gitkeep").exists())
        self.assertTrue((root / "submissions/_template").is_dir())

    def test_template_repo_retains_the_template_only_note(self):
        root, _ = self.reset(template_repo=True)
        self.assertTrue((root / "docs/notes/pipeline-findings.md").exists())
        self.assertFalse((root / "docs/notes/fouling-topic-note.md").exists())

    def test_findings_are_dropped_by_default(self):
        root, _ = self.reset()
        self.assertFalse((root / "docs/notes/pipeline-findings.md").exists())

    def test_reset_is_idempotent(self):
        root, _ = self.reset()
        self.assertEqual(build_plan(root, confirm=True, template_repo=False).actions, [])


class TestMaintainerContent(ResetPaperTestCase):
    """Whoever downloads this template inherits a paper pipeline, not the
    maintainer's hosting arrangement."""

    def test_derived_repo_loses_the_hosting_setup(self):
        root, _ = self.reset()
        claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("Gitea", claude)
        self.assertNotIn("Gitea", readme)
        self.assertNotIn("core.hooksPath", readme)
        self.assertNotIn("원격 두 곳 운영", readme)
        self.assertFalse((root / ".githooks").exists())

    def test_paper_rules_and_other_sections_survive(self):
        root, _ = self.reset()
        self.assertIn("This rule is about the paper and must survive.",
                      (root / "CLAUDE.md").read_text(encoding="utf-8"))
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertIn("This section must survive.", readme)
        self.assertIn("## 빠른 시작", readme)

    def test_template_repo_keeps_its_own_hosting_setup(self):
        root, _ = self.reset(template_repo=True)
        self.assertIn("Gitea", (root / "README.md").read_text(encoding="utf-8"))
        self.assertTrue((root / ".githooks/pre-push").exists())


class TestNarrativeRewrite(unittest.TestCase):
    def test_claim_rows_go_but_legend_rows_stay(self):
        """Both are table rows under ## Claims; only one of them asserts anything."""
        result = reset_narrative_and_claims(STORY_BRIEF)
        self.assertNotIn("| C0 |", result)
        self.assertNotIn("| C1 |", result)
        self.assertIn("| `@key` | a registered source |", result)

    def test_a_cleared_brief_is_unchanged_by_a_second_pass(self):
        once = reset_narrative_and_claims(STORY_BRIEF)
        self.assertEqual(reset_narrative_and_claims(once), once)


if __name__ == "__main__":
    unittest.main()
