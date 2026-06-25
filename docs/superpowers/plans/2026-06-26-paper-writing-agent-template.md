# Paper-Writing Agent Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Claude Code project template (skills + scaffolding) for writing English-language engineering/energy research papers, ready to be pushed to Gitea as a Template Repository.

**Architecture:** A directory skeleton (`docs/`, `refs/`, `code/`, `data/`, `figures/`, `.omc/paper-state.md`) plus nine `.claude/skills/*/SKILL.md` files that delegate generation to the existing OMC agents (`scientist`, `writer`, `executor`, `critic`/`verifier`) and one orchestrator skill (`paper-supervise`) that runs a generate→review loop (max 3 rounds) per stage. Two small, dependency-free Python scripts enforce the two hard invariants from the spec deterministically: citations must come only from the verified-sources registry (`scripts/verify_citations.py`), and `paper-state.md` must never silently exceed 3 rounds without escalating (`scripts/check_paper_state.py`).

**Tech Stack:** Python 3.10+ stdlib only (no pip dependencies), `unittest` for tests (run via `python -m unittest`), Markdown for all content files, Gitea Template Repository feature for distribution.

## Global Constraints

- All paper content is authored in Markdown first; output-format conversion (Pandoc etc.) is out of scope for this template.
- Target field: engineering/energy (experiments, process analysis, AI design); target language: English.
- No new dedicated subagents are created — all generation/review delegates to OMC's existing `scientist`, `writer`, `executor`, `critic`, `verifier`.
- Citations must never be fabricated from model memory: only keys present in `docs/notes/retrieved-sources.json` may enter `refs/references.bib`.
- Every pipeline stage allows at most 3 generate→review rounds; on the 4th failed review the stage status becomes `escalated`, never auto-approved.
- Four fixed user-approval gates regardless of critic verdict: outline complete, each section draft complete, citations finalized, final polish.
- Scripts use Python 3.10+ stdlib only — no `requirements.txt`, no pip install step.
- Run all commands with `python` (not `python3` — confirmed `python3` alias is unavailable in this environment, `python` resolves to 3.14.3).

---

### Task 1: Project skeleton and placeholder content

**Files:**
- Create: `docs/outline.md`
- Create: `docs/sections/01-introduction.md`
- Create: `docs/sections/02-related-work.md`
- Create: `docs/sections/03-methods.md`
- Create: `docs/sections/04-results.md`
- Create: `docs/sections/05-discussion.md`
- Create: `docs/sections/06-conclusion.md`
- Create: `docs/notes/retrieved-sources.json`
- Create: `docs/notes/novelty-matrix.md`
- Create: `refs/references.bib`
- Create: `code/.gitkeep`
- Create: `data/raw/.gitkeep`
- Create: `data/processed/.gitkeep`
- Create: `figures/.gitkeep`
- Create: `.omc/paper-state.md`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: the fixture files later tasks read from — `docs/notes/retrieved-sources.json` (JSON array of `{key, title, url, retrieved_at}` objects, starts as `[]`), `.omc/paper-state.md` (stage blocks with `status`/`round`/`last-critic-verdict`/`last-critic-issues` fields, see Task 5 for the exact grammar), `docs/sections/*.md` (Markdown stubs, no citations yet).

- [ ] **Step 1: Create the docs skeleton**

`docs/outline.md`:
```markdown
# Paper Outline

> Filled in by the `outline-draft` skill after `novelty-check` produces `docs/notes/novelty-matrix.md`.

1. Introduction
2. Related Work
3. Methods
4. Results
5. Discussion
6. Conclusion
```

`docs/sections/01-introduction.md`:
```markdown
# Introduction

> Drafted by the `outline-draft` skill once `docs/outline.md` is approved.
```

`docs/sections/02-related-work.md`:
```markdown
# Related Work

> Drafted by the `outline-draft` skill using `docs/notes/novelty-matrix.md` as the source of comparisons.
```

`docs/sections/03-methods.md`:
```markdown
# Methods

> Drafted by the `outline-draft` skill; updated by `code-experiment` once experiment code exists under `code/`.
```

`docs/sections/04-results.md`:
```markdown
# Results

> Drafted by the `results-discussion` skill from `data/processed/`.
```

`docs/sections/05-discussion.md`:
```markdown
# Discussion

> Drafted by the `results-discussion` skill; must reference `docs/notes/novelty-matrix.md` when comparing to prior work.
```

`docs/sections/06-conclusion.md`:
```markdown
# Conclusion

> Drafted by the `polish-review` skill pass once all other sections are approved.
```

`docs/notes/retrieved-sources.json`:
```json
[]
```

`docs/notes/novelty-matrix.md`:
```markdown
# Novelty Matrix

> Filled in by the `novelty-check` skill. Each row maps one claimed contribution to the closest prior work and the concrete difference. Every "Closest Prior Work" entry must cite a `key` that exists in `docs/notes/retrieved-sources.json`.

| Claim | Closest Prior Work | Key Difference |
|---|---|---|
```

`refs/references.bib`:
```
% Populated exclusively by the citation-manage skill, sourced from docs/notes/retrieved-sources.json.
% Do not hand-add an entry whose key is not already registered there — see scripts/verify_citations.py.
```

- [ ] **Step 2: Create placeholder directories and Python package markers**

```bash
touch code/.gitkeep data/raw/.gitkeep data/processed/.gitkeep figures/.gitkeep
touch scripts/__init__.py tests/__init__.py
```

- [ ] **Step 3: Create the initial `.omc/paper-state.md`**

```markdown
# Paper State

## Stage: lit-review
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: novelty-check
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: outline-draft
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: results-discussion
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: code-experiment
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: figures-tables
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: citation-manage
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:
verified-sources: 0
rejected-citations:

## Stage: polish-review
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:
```

- [ ] **Step 4: Verify the skeleton**

Run: `find docs refs code data figures .omc scripts tests -type f | sort`
Expected: all 17 files from the Files list above are listed (plus the 4 `.gitkeep` files and 2 `__init__.py` files).

- [ ] **Step 5: Commit**

```bash
git add docs refs code data figures .omc scripts tests
git commit -m "Add paper-writing template skeleton and placeholder content"
```

---

### Task 2: CLAUDE.md authoring

**Files:**
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: stage list and skill names from Task 1's `.omc/paper-state.md`.
- Produces: the top-level instructions every Claude Code session in a paper project reads first.

- [ ] **Step 1: Write `CLAUDE.md`**

```markdown
# Paper Project

> Fill in the four fields below when you start a new paper from this template.

- **Working title:** _fill in_
- **Target venue:** _fill in (journal/conference)_
- **Field:** Engineering / Energy (experiments, process analysis, AI design)
- **Language:** English

## Workflow

This project is driven by `.omc/paper-state.md` and the skills under `.claude/skills/`. Do not skip stages or hand-write `refs/references.bib` directly.

Stage order:
1. `lit-review` — search and register real sources
2. `novelty-check` — compare claims against registered sources
3. `outline-draft` — outline, then section drafts
4. `results-discussion` + `code-experiment` + `figures-tables` — can run in any order once `code/` produces `data/processed/`
5. `citation-manage` — cross-check every citation against the registry before touching `refs/references.bib`
6. `polish-review` — final full-draft pass

Run `paper-supervise` to find out which stage is next, or to resume after a break — it reads `.omc/paper-state.md` and tells you what to do.

## Hard rules

- Never add a citation to `refs/references.bib` unless its key exists in `docs/notes/retrieved-sources.json`. Run `python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md` before finalizing citations.
- Each stage gets at most 3 generate→review rounds. On the 4th failed review, stop and report to the user — do not keep retrying and do not auto-approve.
- Always stop for explicit user approval at: outline complete, each section draft complete, citations finalized, final polish — even if the reviewing agent already approved.
- All agent delegation reuses the existing OMC agents (`scientist`, `writer`, `executor`, `critic`, `verifier`). Do not invent new subagents for this project.
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -c "^##" CLAUDE.md`
Expected: `2` (the `## Workflow` and `## Hard rules` headings)

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "Add CLAUDE.md workflow guide for paper projects"
```

---

### Task 3: Citation registry and BibTeX key extraction

**Files:**
- Create: `scripts/verify_citations.py`
- Test: `tests/test_verify_citations.py`

**Interfaces:**
- Produces: `extract_registry_keys(registry_path: Path) -> set[str]`, `extract_bibtex_keys(bib_path: Path) -> set[str]` — used by Task 4.

- [ ] **Step 1: Write the failing tests**

`tests/test_verify_citations.py`:
```python
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.verify_citations import extract_bibtex_keys, extract_registry_keys


class TestExtractRegistryKeys(unittest.TestCase):
    def test_reads_keys_from_registry_json(self):
        with TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "retrieved-sources.json"
            registry_path.write_text(
                json.dumps(
                    [
                        {"key": "smith2021boiler", "title": "Boiler Efficiency", "url": "https://example.com/a", "retrieved_at": "2026-06-20"},
                        {"key": "lee2022process", "title": "Process Analysis", "url": "https://example.com/b", "retrieved_at": "2026-06-21"},
                    ]
                ),
                encoding="utf-8",
            )
            self.assertEqual(extract_registry_keys(registry_path), {"smith2021boiler", "lee2022process"})

    def test_empty_registry_returns_empty_set(self):
        with TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "retrieved-sources.json"
            registry_path.write_text("[]", encoding="utf-8")
            self.assertEqual(extract_registry_keys(registry_path), set())


class TestExtractBibtexKeys(unittest.TestCase):
    def test_reads_keys_from_multiple_entry_types(self):
        with TemporaryDirectory() as tmp:
            bib_path = Path(tmp) / "references.bib"
            bib_path.write_text(
                "@article{smith2021boiler,\n  title = {Boiler Efficiency},\n}\n"
                "@inproceedings{lee2022process,\n  title = {Process Analysis},\n}\n",
                encoding="utf-8",
            )
            self.assertEqual(extract_bibtex_keys(bib_path), {"smith2021boiler", "lee2022process"})

    def test_comment_only_file_returns_empty_set(self):
        with TemporaryDirectory() as tmp:
            bib_path = Path(tmp) / "references.bib"
            bib_path.write_text("% no entries yet\n", encoding="utf-8")
            self.assertEqual(extract_bibtex_keys(bib_path), set())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_verify_citations -v`
Expected: `ModuleNotFoundError: No module named 'scripts.verify_citations'`

- [ ] **Step 3: Write the minimal implementation**

`scripts/verify_citations.py`:
```python
"""Cross-check citations used in section drafts against the retrieved-sources registry."""
import json
import re
from pathlib import Path


def extract_registry_keys(registry_path: Path) -> set[str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return {entry["key"] for entry in data}


def extract_bibtex_keys(bib_path: Path) -> set[str]:
    text = bib_path.read_text(encoding="utf-8")
    return set(re.findall(r"@\w+\{\s*([^,\s]+)\s*,", text))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_verify_citations -v`
Expected: `OK` with 4 tests run

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_citations.py tests/test_verify_citations.py
git commit -m "Add registry and BibTeX key extraction for citation verification"
```

---

### Task 4: Markdown citation extraction, unverified-citation report, and CLI

**Files:**
- Modify: `scripts/verify_citations.py`
- Modify: `tests/test_verify_citations.py`

**Interfaces:**
- Consumes: `extract_registry_keys`, `extract_bibtex_keys` from Task 3.
- Produces: `extract_citation_keys_from_markdown(md_path: Path) -> set[str]`, `find_unverified_citations(section_paths: list[Path], registry_path: Path) -> dict[str, list[str]]` — used by Task 14 (`citation-manage` skill).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_verify_citations.py` (above the `if __name__ == "__main__":` line):
```python
class TestExtractCitationKeysFromMarkdown(unittest.TestCase):
    def test_single_pandoc_citation(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text("Prior work [@smith2021boiler] showed this.", encoding="utf-8")
            self.assertEqual(extract_citation_keys_from_markdown(md_path), {"smith2021boiler"})

    def test_multiple_citations_in_one_bracket(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text("See [@smith2021boiler; @lee2022process].", encoding="utf-8")
            self.assertEqual(
                extract_citation_keys_from_markdown(md_path),
                {"smith2021boiler", "lee2022process"},
            )

    def test_non_citation_brackets_are_ignored(self):
        with TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "section.md"
            md_path.write_text("See [Figure 1] for the setup.", encoding="utf-8")
            self.assertEqual(extract_citation_keys_from_markdown(md_path), set())


class TestFindUnverifiedCitations(unittest.TestCase):
    def test_flags_keys_missing_from_registry(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "retrieved-sources.json"
            registry_path.write_text(
                json.dumps([{"key": "smith2021boiler", "title": "t", "url": "u", "retrieved_at": "2026-06-20"}]),
                encoding="utf-8",
            )
            section_path = tmp_path / "section.md"
            section_path.write_text("Uses [@smith2021boiler] and [@fabricated2099].", encoding="utf-8")

            report = find_unverified_citations([section_path], registry_path)
            self.assertEqual(report, {str(section_path): ["fabricated2099"]})

    def test_no_unverified_citations_returns_empty_report(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "retrieved-sources.json"
            registry_path.write_text(
                json.dumps([{"key": "smith2021boiler", "title": "t", "url": "u", "retrieved_at": "2026-06-20"}]),
                encoding="utf-8",
            )
            section_path = tmp_path / "section.md"
            section_path.write_text("Uses [@smith2021boiler] only.", encoding="utf-8")

            self.assertEqual(find_unverified_citations([section_path], registry_path), {})
```

Update the import line at the top of `tests/test_verify_citations.py` to:
```python
from scripts.verify_citations import (
    extract_bibtex_keys,
    extract_citation_keys_from_markdown,
    extract_registry_keys,
    find_unverified_citations,
)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_verify_citations -v`
Expected: `ImportError: cannot import name 'extract_citation_keys_from_markdown'`

- [ ] **Step 3: Write the minimal implementation**

Append to `scripts/verify_citations.py`:
```python
def extract_citation_keys_from_markdown(md_path: Path) -> set[str]:
    text = md_path.read_text(encoding="utf-8")
    keys: set[str] = set()
    for bracket_contents in re.findall(r"\[([^\]]+)\]", text):
        if "@" not in bracket_contents:
            continue
        for token in bracket_contents.split(";"):
            token = token.strip()
            if token.startswith("@"):
                keys.add(token[1:].strip())
    return keys


def find_unverified_citations(section_paths: list[Path], registry_path: Path) -> dict[str, list[str]]:
    registry_keys = extract_registry_keys(registry_path)
    report: dict[str, list[str]] = {}
    for section_path in section_paths:
        used_keys = extract_citation_keys_from_markdown(section_path)
        unverified = sorted(used_keys - registry_keys)
        if unverified:
            report[str(section_path)] = unverified
    return report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_verify_citations -v`
Expected: `OK` with 9 tests run

- [ ] **Step 5: Add the CLI entry point**

Append to `scripts/verify_citations.py`:
```python
def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Verify citations against the retrieved-sources registry.")
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--sections", required=True, nargs="+", type=Path)
    args = parser.parse_args()

    report = find_unverified_citations(args.sections, args.registry)
    if not report:
        print("All citations verified against registry.")
        return 0

    print("Unverified citations found (not in retrieved-sources registry):")
    for path, keys in report.items():
        print(f"  {path}: {', '.join(keys)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Verify the CLI against the Task 1 skeleton fixtures**

Run: `python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md`
Expected: `All citations verified against registry.` (exit code 0 — the skeleton sections contain no citations yet)

- [ ] **Step 7: Commit**

```bash
git add scripts/verify_citations.py tests/test_verify_citations.py
git commit -m "Add markdown citation extraction, unverified-citation report, and CLI"
```

---

### Task 5: paper-state.md parsing

**Files:**
- Create: `scripts/check_paper_state.py`
- Test: `tests/test_check_paper_state.py`

**Interfaces:**
- Produces: `parse_stages(state_path: Path) -> list[dict]`, where each dict has keys `id: str`, `status: str | None`, `round: str | None`, `last-critic-verdict: str | None`, `last-critic-issues: list[str]` — used by Task 6.

- [ ] **Step 1: Write the failing tests**

`tests/test_check_paper_state.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_check_paper_state -v`
Expected: `ModuleNotFoundError: No module named 'scripts.check_paper_state'`

- [ ] **Step 3: Write the minimal implementation**

`scripts/check_paper_state.py`:
```python
"""Validate the structure and invariants of .omc/paper-state.md."""
import re
from pathlib import Path

STAGE_HEADER_RE = re.compile(r"^## Stage: (?P<id>.+)$")
FIELD_RE = re.compile(r"^(?P<key>[\w-]+):\s*(?P<value>.*)$")
ISSUE_RE = re.compile(r'^\s*-\s*"?(?P<issue>.*?)"?\s*$')

TRACKED_SCALAR_FIELDS = ("status", "round", "last-critic-verdict")


def parse_stages(state_path: Path) -> list[dict]:
    stages: list[dict] = []
    current: dict | None = None
    in_issues = False

    for raw_line in state_path.read_text(encoding="utf-8").splitlines():
        header_match = STAGE_HEADER_RE.match(raw_line)
        if header_match:
            if current is not None:
                stages.append(current)
            current = {
                "id": header_match.group("id").strip(),
                "status": None,
                "round": None,
                "last-critic-verdict": None,
                "last-critic-issues": [],
            }
            in_issues = False
            continue

        if current is None:
            continue

        field_match = FIELD_RE.match(raw_line)
        if field_match:
            key = field_match.group("key")
            value = field_match.group("value").strip()
            in_issues = key == "last-critic-issues"
            if key in TRACKED_SCALAR_FIELDS:
                current[key] = value or None
            continue

        if in_issues:
            issue_match = ISSUE_RE.match(raw_line)
            if issue_match and raw_line.strip().startswith("-"):
                current["last-critic-issues"].append(issue_match.group("issue"))

    if current is not None:
        stages.append(current)

    return stages
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_check_paper_state -v`
Expected: `OK` with 4 tests run

- [ ] **Step 5: Commit**

```bash
git add scripts/check_paper_state.py tests/test_check_paper_state.py
git commit -m "Add paper-state.md parsing"
```

---

### Task 6: paper-state.md validation rules and CLI

**Files:**
- Modify: `scripts/check_paper_state.py`
- Modify: `tests/test_check_paper_state.py`

**Interfaces:**
- Consumes: `parse_stages` from Task 5.
- Produces: `validate_stage(stage: dict) -> list[str]`, `validate_all(state_path: Path) -> dict[str, list[str]]` — used by `paper-supervise` (Task 7).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_check_paper_state.py` (above the `if __name__ == "__main__":` line), and add `validate_all`/`validate_stage` to the existing import line:
```python
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
                "last-critic-issues:\n",
            )
            report = validate_all(state_path)
            self.assertEqual(list(report.keys()), ["novelty-check"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_check_paper_state -v`
Expected: `ImportError: cannot import name 'validate_stage'`

- [ ] **Step 3: Write the minimal implementation**

Append to `scripts/check_paper_state.py`:
```python
ALLOWED_STATUSES = {
    "not-started",
    "in-progress",
    "awaiting-review",
    "awaiting-user",
    "approved",
    "escalated",
}
ALLOWED_VERDICTS = {"pass", "revise"}


def validate_stage(stage: dict) -> list[str]:
    errors: list[str] = []
    stage_id = stage["id"]

    status = stage["status"]
    if status not in ALLOWED_STATUSES:
        errors.append(f"{stage_id}: invalid status '{status}'")

    current_round = None
    max_round = None
    round_value = stage["round"]
    if round_value:
        round_match = re.match(r"^(\d+)/(\d+)$", round_value)
        if not round_match:
            errors.append(f"{stage_id}: invalid round format '{round_value}', expected 'n/3'")
        else:
            current_round, max_round = int(round_match.group(1)), int(round_match.group(2))

    verdict = stage["last-critic-verdict"]
    if verdict is not None and verdict not in ALLOWED_VERDICTS:
        errors.append(f"{stage_id}: invalid last-critic-verdict '{verdict}'")

    if current_round is not None and max_round is not None:
        if current_round >= max_round and status not in {"escalated", "approved"}:
            errors.append(
                f"{stage_id}: round {current_round}/{max_round} reached without "
                f"status 'escalated' or 'approved' (got '{status}')"
            )

    return errors


def validate_all(state_path: Path) -> dict[str, list[str]]:
    report: dict[str, list[str]] = {}
    for stage in parse_stages(state_path):
        errors = validate_stage(stage)
        if errors:
            report[stage["id"]] = errors
    return report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_check_paper_state -v`
Expected: `OK` with 11 tests run

- [ ] **Step 5: Add the CLI entry point**

Append to `scripts/check_paper_state.py`:
```python
def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate .omc/paper-state.md")
    parser.add_argument("--state", required=True, type=Path)
    args = parser.parse_args()

    report = validate_all(args.state)
    if not report:
        print("paper-state.md is valid.")
        return 0

    print("paper-state.md validation errors:")
    for stage_id, errors in report.items():
        for error in errors:
            print(f"  {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Verify the CLI against the Task 1 skeleton's initial state file**

Run: `python scripts/check_paper_state.py --state .omc/paper-state.md`
Expected: `paper-state.md is valid.` (exit code 0)

- [ ] **Step 7: Commit**

```bash
git add scripts/check_paper_state.py tests/test_check_paper_state.py
git commit -m "Add paper-state.md validation rules and CLI"
```

---

### Task 7: `paper-supervise` orchestrator skill

**Files:**
- Create: `.claude/skills/paper-supervise/SKILL.md`

**Interfaces:**
- Consumes: `.omc/paper-state.md` (Task 1), `scripts/check_paper_state.py` (Task 6).
- Produces: the orchestrator entry point referenced by `CLAUDE.md` (Task 2) and by every other skill's gate logic.

- [ ] **Step 1: Write the skill**

`.claude/skills/paper-supervise/SKILL.md`:
```markdown
---
name: paper-supervise
description: Orchestrates the paper-writing pipeline via .omc/paper-state.md — figures out which stage is next, runs each stage's generate-then-review loop (max 3 rounds), and enforces the 4 fixed user-approval gates instead of auto-passing. Use when starting work, resuming after a break, or asking "what's next".
---

# Paper Supervisor

## Stage order

1. `lit-review`
2. `novelty-check`
3. `outline-draft`
4. `results-discussion`, `code-experiment`, `figures-tables` (any order, once `code/` has produced `data/processed/`)
5. `citation-manage`
6. `polish-review`

## On invocation

1. Run `python scripts/check_paper_state.py --state .omc/paper-state.md`. If it reports errors, stop and show them to the user before doing anything else — the state file is corrupted and must be fixed by hand first.
2. Read `.omc/paper-state.md` and find the first stage (in the order above) whose `status` is not `approved`.
3. Report that stage and its current `status`/`round` to the user, then proceed per the loop below.

## Generate-then-review loop (per stage)

1. Delegate generation to the agent listed for that stage in `CLAUDE.md`'s workflow table (`scientist` for `lit-review`/analysis, `writer` for drafting, `executor` for code/figures, `verifier` for citations).
2. Delegate review to `critic` (or `verifier` for `citation-manage`) using this rubric — record the verdict and any issues back into the stage's `last-critic-verdict` / `last-critic-issues` fields:
   - novelty/significance
   - technical soundness
   - clarity
   - prior-work coverage
   - concrete revision suggestions
3. If the verdict is `pass`: set `status: awaiting-user` and stop — do not proceed automatically, even though the critic passed.
4. If the verdict is `revise`: increment `round`, fold the issues into the next generation attempt, go back to step 1.
5. If `round` reaches `3/3` and the verdict is still `revise`: set `status: escalated`, stop, and report the unresolved issues to the user verbatim. Never set `status: approved` automatically and never loop past round 3.
6. When the user reviews an `awaiting-user` stage: if they approve, set `status: approved` and move to the next stage. If they reject, go back to step 1 with their feedback as an additional issue.

## Fixed user-approval gates

Regardless of critic verdict, always stop for explicit user sign-off at:
- outline complete (`outline-draft` stage, before drafting any section)
- each section draft complete (`outline-draft` / `results-discussion` stages)
- citations finalized (`citation-manage` stage, before any `refs/references.bib` edit is treated as final)
- final polish (`polish-review` stage)
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -E "^## " .claude/skills/paper-supervise/SKILL.md`
Expected: 4 lines — `## Stage order`, `## On invocation`, `## Generate-then-review loop (per stage)`, `## Fixed user-approval gates`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/paper-supervise/SKILL.md
git commit -m "Add paper-supervise orchestrator skill"
```

---

### Task 8: `lit-review` skill

**Files:**
- Create: `.claude/skills/lit-review/SKILL.md`

**Interfaces:**
- Produces: entries appended to `docs/notes/retrieved-sources.json` (Task 1 schema) and notes under `docs/notes/*.md`, consumed by Task 9 (`novelty-check`) and Task 14 (`citation-manage`).

- [ ] **Step 1: Write the skill**

`.claude/skills/lit-review/SKILL.md`:
```markdown
---
name: lit-review
description: Searches for and organizes literature on a research topic, registering every real source found into docs/notes/retrieved-sources.json. Use when starting literature review or when a later stage needs an additional source.
---

# Literature Review

## Rule

Every entry in `docs/notes/retrieved-sources.json` must come from an actual search result (WebSearch or equivalent). Never invent an entry — `citation-manage` (Task 14) trusts this file as ground truth and will reject any citation whose key is missing from it.

## Procedure

1. Delegate to the `scientist` agent: search for papers/reports relevant to the given topic or keyword using WebSearch.
2. For each real result, append one object to `docs/notes/retrieved-sources.json`:
   ```json
   {
     "key": "<firstauthorsurname><year><oneword>",
     "title": "<exact title from the source>",
     "url": "<the URL actually returned by the search>",
     "retrieved_at": "<today's date, YYYY-MM-DD>"
   }
   ```
3. Write or update a summary note at `docs/notes/<topic-slug>.md` covering what the source claims and how it relates to the current paper's topic.
4. Hand off to `paper-supervise`, which routes the result through the critic for the `lit-review` stage's review round.
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -E "^## " .claude/skills/lit-review/SKILL.md`
Expected: 2 lines — `## Rule`, `## Procedure`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/lit-review/SKILL.md
git commit -m "Add lit-review skill"
```

---

### Task 9: `novelty-check` skill

**Files:**
- Create: `.claude/skills/novelty-check/SKILL.md`

**Interfaces:**
- Consumes: `docs/notes/retrieved-sources.json` (Task 8).
- Produces: `docs/notes/novelty-matrix.md` (Task 1 template, filled in), consumed by Task 10 (`outline-draft`) and Task 11 (`results-discussion`).

- [ ] **Step 1: Write the skill**

`.claude/skills/novelty-check/SKILL.md`:
```markdown
---
name: novelty-check
description: Compares this paper's claimed contributions against registered prior work to establish novelty, and separately estimates overlap with the author's own prior publications. Use after lit-review, before outline-draft.
---

# Novelty Check

## Three-stage novelty pipeline

1. **Extract claims** — list this paper's claimed contributions (from the working draft of `docs/outline.md` or the user's description).
2. **Retrieve and rank related work** — reuse `docs/notes/retrieved-sources.json`; run an additional `lit-review` pass if a claim has no close match yet.
3. **Structured comparison** — for each claim, fill one row of `docs/notes/novelty-matrix.md`:

   | Claim | Closest Prior Work | Key Difference |
   |---|---|---|
   | <contribution> | <source key from retrieved-sources.json> | <concrete delta, not "more novel"> |

   Every "Closest Prior Work" entry must be a `key` that exists in `docs/notes/retrieved-sources.json` — this table feeds `citation-manage` later.

## Self-redundancy check (separate from novelty)

If the user has prior publications on a related topic, list them and estimate, per claim, what percentage of the contribution overlaps with the user's own earlier work. Report this as a short paragraph appended to the bottom of `docs/notes/novelty-matrix.md` under a `## Self-Redundancy` heading — this is about duplicate-publication risk, not about novelty versus the field.

## Handoff

Delegate the comparison work to the `scientist` agent and the structured write-up to `critic` for review, per the `paper-supervise` loop.
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -E "^## " .claude/skills/novelty-check/SKILL.md`
Expected: 3 lines — `## Three-stage novelty pipeline`, `## Self-redundancy check (separate from novelty)`, `## Handoff`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/novelty-check/SKILL.md
git commit -m "Add novelty-check skill"
```

---

### Task 10: `outline-draft` skill

**Files:**
- Create: `.claude/skills/outline-draft/SKILL.md`

**Interfaces:**
- Consumes: `docs/notes/novelty-matrix.md` (Task 9).
- Produces: `docs/outline.md`, `docs/sections/*.md` (filled in from the Task 1 stubs), consumed by Task 11 (`results-discussion`) and Task 14 (`citation-manage`).

- [ ] **Step 1: Write the skill**

`.claude/skills/outline-draft/SKILL.md`:
```markdown
---
name: outline-draft
description: Designs the paper's outline from the novelty matrix, then expands each section into a full draft. Use after novelty-check, before results-discussion.
---

# Outline and Draft

## Procedure

1. Delegate to `writer`: using `docs/notes/novelty-matrix.md`, fill in `docs/outline.md` with a one-sentence purpose for each of the 6 sections.
2. Stop for the **outline-complete user gate** — do not draft any section before the user approves the outline, even if `critic` already approved it.
3. Once approved, delegate to `writer` to expand each `docs/sections/0N-*.md` stub into a full draft, one section at a time, referencing `docs/notes/novelty-matrix.md` wherever the section discusses prior work.
4. After each section draft, stop for the **section-draft-complete user gate**.
5. Hand off each section to `critic` for review through the `paper-supervise` loop before presenting it to the user.
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -E "^## " .claude/skills/outline-draft/SKILL.md`
Expected: 1 line — `## Procedure`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/outline-draft/SKILL.md
git commit -m "Add outline-draft skill"
```

---

### Task 11: `results-discussion` skill

**Files:**
- Create: `.claude/skills/results-discussion/SKILL.md`

**Interfaces:**
- Consumes: `data/processed/` (Task 12), `docs/notes/novelty-matrix.md` (Task 9).
- Produces: `docs/sections/04-results.md`, `docs/sections/05-discussion.md` (filled in).

- [ ] **Step 1: Write the skill**

`.claude/skills/results-discussion/SKILL.md`:
```markdown
---
name: results-discussion
description: Analyzes processed experiment data and drafts the Results and Discussion sections. Use once code-experiment has produced data/processed/ output.
---

# Results and Discussion

## Procedure

1. Delegate to `scientist`: analyze the contents of `data/processed/` (statistics, trends, anomalies relevant to the paper's claims).
2. Delegate to `writer`: draft `docs/sections/04-results.md` as an objective report of what the data shows — no interpretation here.
3. Delegate to `writer`: draft `docs/sections/05-discussion.md` interpreting the results, explicitly comparing against the "Closest Prior Work" column of `docs/notes/novelty-matrix.md`, and naming limitations.
4. Hand off both sections to `critic` through the `paper-supervise` loop, then stop for the section-draft-complete user gate.
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -E "^## " .claude/skills/results-discussion/SKILL.md`
Expected: 1 line — `## Procedure`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/results-discussion/SKILL.md
git commit -m "Add results-discussion skill"
```

---

### Task 12: `code-experiment` skill

**Files:**
- Create: `.claude/skills/code-experiment/SKILL.md`

**Interfaces:**
- Produces: files under `code/` and `data/processed/`, consumed by Task 11 (`results-discussion`) and Task 13 (`figures-tables`).

- [ ] **Step 1: Write the skill**

`.claude/skills/code-experiment/SKILL.md`:
```markdown
---
name: code-experiment
description: Writes and runs experiment/analysis code, producing processed data under data/processed/. Use when the paper needs new experimental or analytical results.
---

# Code and Experiments

## Procedure

1. Delegate to `executor`: write the analysis/experiment code under `code/`, reading only from `data/raw/`.
2. Run the code and write its output to `data/processed/` — never modify files under `data/raw/`.
3. Record what the code does and how to re-run it in a comment header at the top of the relevant file under `code/`.
4. Hand off the code and a summary of what it produced to `critic` through the `paper-supervise` loop before `results-discussion` or `figures-tables` consume the output.
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -E "^## " .claude/skills/code-experiment/SKILL.md`
Expected: 1 line — `## Procedure`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/code-experiment/SKILL.md
git commit -m "Add code-experiment skill"
```

---

### Task 13: `figures-tables` skill

**Files:**
- Create: `.claude/skills/figures-tables/SKILL.md`

**Interfaces:**
- Consumes: `data/processed/` (Task 12).
- Produces: `figures/*.png` and Markdown tables embedded in `docs/sections/*.md`.

- [ ] **Step 1: Write the skill**

`.claude/skills/figures-tables/SKILL.md`:
```markdown
---
name: figures-tables
description: Generates figures and tables from processed experiment data. Use once code-experiment has produced data/processed/ output.
---

# Figures and Tables

## Procedure

1. Delegate to `executor`: write a plotting/table-generation script under `code/` that reads from `data/processed/` and writes images to `figures/*.png`.
2. Embed any tables directly as Markdown tables in the relevant `docs/sections/*.md` file (not as images), with a one-line caption above each table and figure reference.
3. Hand off to `critic` through the `paper-supervise` loop: review checks axis labels, units, and caption accuracy against `data/processed/`.
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -E "^## " .claude/skills/figures-tables/SKILL.md`
Expected: 1 line — `## Procedure`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/figures-tables/SKILL.md
git commit -m "Add figures-tables skill"
```

---

### Task 14: `citation-manage` skill

**Files:**
- Create: `.claude/skills/citation-manage/SKILL.md`

**Interfaces:**
- Consumes: `scripts/verify_citations.py` (`find_unverified_citations`, Task 4), `docs/notes/retrieved-sources.json` (Task 8).
- Produces: `refs/references.bib` entries, the `verified-sources`/`rejected-citations` fields of the `citation-manage` stage in `.omc/paper-state.md`.

- [ ] **Step 1: Write the skill**

`.claude/skills/citation-manage/SKILL.md`:
```markdown
---
name: citation-manage
description: Cross-checks every citation used in the draft against the retrieved-sources registry before allowing it into refs/references.bib. Use before finalizing citations, never to hand-author bibliography entries.
---

# Citation Management

## Hard rule

A citation may enter `refs/references.bib` **only if** its key already exists in `docs/notes/retrieved-sources.json`. This is a deterministic check, not a judgment call — run the script, don't eyeball it.

## Procedure

1. Run:
   ```bash
   python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md
   ```
2. For every verified key (present in both the sections and the registry), add one BibTeX entry to `refs/references.bib` using the `title`/`url` fields already stored in `docs/notes/retrieved-sources.json` — do not add fields the registry doesn't have.
3. For every key the script reports as unverified: do **not** add it to `refs/references.bib`. Instead, record it under `rejected-citations` in the `citation-manage` stage of `.omc/paper-state.md` with the reason `"not in retrieved-sources.json"`, and tell the user — either run `lit-review` to register the real source, or remove the citation from the draft.
4. Update `verified-sources` in `.omc/paper-state.md` to the count of keys now in `refs/references.bib`.
5. Stop for the **citations-finalized user gate** before treating this stage as done.
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -E "^## " .claude/skills/citation-manage/SKILL.md`
Expected: 2 lines — `## Hard rule`, `## Procedure`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/citation-manage/SKILL.md
git commit -m "Add citation-manage skill"
```

---

### Task 15: `polish-review` skill

**Files:**
- Create: `.claude/skills/polish-review/SKILL.md`

**Interfaces:**
- Consumes: all of `docs/sections/*.md` (Tasks 10–11), `refs/references.bib` (Task 14).
- Produces: a final review report, the `polish-review` stage update in `.omc/paper-state.md`.

- [ ] **Step 1: Write the skill**

`.claude/skills/polish-review/SKILL.md`:
```markdown
---
name: polish-review
description: Runs a full-draft proofreading and consistency pass using the 5-axis rubric, after every section and citations are approved. Use as the last stage before considering the paper done.
---

# Polish and Final Review

## Rubric

Delegate to `critic` to review the full draft (`docs/sections/*.md` in order) against these 5 axes, same as every other stage's review:
- novelty/significance
- technical soundness
- clarity
- prior-work coverage
- concrete revision suggestions

Additionally check, specific to a final pass: terminology consistency across sections, that every in-text citation key also appears in `refs/references.bib`, and tense/voice consistency (English, target venue).

## Procedure

1. Run `python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md` one more time — citations must still be clean after any late edits.
2. Produce a short review report listing any remaining issues per section.
3. Stop for the **final-polish user gate** — this is the last of the 4 fixed gates; do not mark the paper complete without explicit user sign-off.
```

- [ ] **Step 2: Verify required sections are present**

Run: `grep -E "^## " .claude/skills/polish-review/SKILL.md`
Expected: 2 lines — `## Rubric`, `## Procedure`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/polish-review/SKILL.md
git commit -m "Add polish-review skill"
```

---

### Task 16: Template README and Gitea distribution instructions

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: the full skill list (Tasks 7–15), `CLAUDE.md` (Task 2).
- Produces: the top-level entry point a user reads when they land on the Gitea repository page.

This task documents the manual Gitea steps; it does not create or modify any remote Gitea repository, since that requires the user's own Gitea server URL and credentials.

- [ ] **Step 1: Write the README**

`README.md`:
```markdown
# Paper-Writing Agent Template

A Claude Code project template for writing English-language engineering/energy research papers (experiments, process analysis, AI design), built to be reused across papers via Gitea's Template Repository feature.

## Quick start for a new paper

1. On your Gitea instance, open this repository → **Settings** → enable **"Template Repository"** (one-time setup on this repo, not per paper).
2. For each new paper: this repo's page → **"Use this template"** → create a new, independent repository. No submodule or symlink dependency is created — the new repo is fully standalone.
3. Clone the new repo and fill in the 4 fields at the top of `CLAUDE.md` (working title, target venue, field, language).
4. Ask Claude Code to run the `paper-supervise` skill — it reads `.omc/paper-state.md` and tells you which stage to start on.

## Skills

| Skill | Purpose |
|---|---|
| `paper-supervise` | Orchestrates the whole pipeline; run this first and after every break |
| `lit-review` | Searches and registers real sources into `docs/notes/retrieved-sources.json` |
| `novelty-check` | Compares claims to prior work; flags self-redundancy |
| `outline-draft` | Outline, then section-by-section drafting |
| `results-discussion` | Analyzes `data/processed/` and writes Results + Discussion |
| `code-experiment` | Writes/runs experiment and analysis code |
| `figures-tables` | Generates figures and tables from processed data |
| `citation-manage` | The only path that may write to `refs/references.bib` |
| `polish-review` | Final full-draft pass before calling the paper done |

## Scripts

Dependency-free Python 3.10+ (stdlib only). Run tests with:
```bash
python -m unittest discover -s tests -v
```

- `scripts/verify_citations.py` — enforces that every citation key used in `docs/sections/*.md` exists in `docs/notes/retrieved-sources.json` before it can enter `refs/references.bib`.
- `scripts/check_paper_state.py` — validates `.omc/paper-state.md` (valid statuses, round format, and that no stage silently exceeds 3 review rounds without escalating).

## Design rationale

See `docs/superpowers/specs/2026-06-25-paper-writing-agent-template-design.md` for the full design (architecture decision, citation-hallucination defenses, novelty-check pipeline, and sources).
```

- [ ] **Step 2: Verify the full test suite still passes**

Run: `python -m unittest discover -s tests -v`
Expected: `OK` with 20 tests run (4 from Task 3 + 5 from Task 4 + 4 from Task 5 + 7 from Task 6)

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Add template README with quick-start and Gitea distribution instructions"
```

---

## After this plan

Pushing this repository to Gitea and flipping the "Template Repository" setting requires the user's own Gitea server URL and login — that step is documented in `README.md` (Task 16) but must be performed manually by the user, not automated here.
