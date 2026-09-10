"""Clear one paper's work so a fresh paper can start in this repository.

"Use this template" copies the whole tree, research artifacts included. Nothing
else catches that: neither check_paper_state.py nor verify_story_brief.py asks
whether a claim belongs to *this* paper, so an inherited claims ledger is
perfectly valid to them. A new paper would start out arguing a previous paper's
argument from its sources, and every validator would agree.

Refuses to touch anything without --confirm. The default is a plan you can read.
data/raw/ is never touched.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = "_입력 필요_"
NARRATIVE_SLOTS = ("Context", "Gap", "Question", "Approach", "Finding", "Implication")

# docs/notes files that belong to the template. Anything else there is a topic
# note some lit-review round wrote: the previous paper's, not the next one's.
TEMPLATE_NOTES = {
    "story-brief.md",
    "novelty-matrix.md",
    "retrieved-sources.json",
    "pipeline-findings.md",
}

SECTION_STUBS = {
    "01-introduction.md": ("Introduction", "Drafted by the outline-draft skill once docs/outline.md is approved."),
    "02-related-work.md": ("Related Work", "Drafted by outline-draft using docs/notes/novelty-matrix.md."),
    "03-methods.md": ("Methods", "Drafted by outline-draft; updated after code-experiment."),
    "04-results.md": ("Results", "Drafted by results-discussion from data/processed/."),
    "05-discussion.md": ("Discussion", "Drafted by results-discussion; compare with docs/notes/novelty-matrix.md."),
    "06-conclusion.md": ("Conclusion", "Drafted after results-discussion, before citation-manage."),
}

STAGES = (
    "story-brief", "lit-review", "novelty-check", "outline-draft", "code-experiment",
    "results-discussion", "figures-tables", "citation-manage", "polish-review",
)

# check_paper_state.py requires these on citation-manage and rejects them anywhere
# else, so they cannot simply be written onto every stage.
STAGE_EXTRA_FIELDS = {
    "citation-manage": ("verified-sources: 0", "rejected-citations:"),
}

HEADER_FIELDS = ("가제", "목표 학술지/학회", "분야", "작성 언어")

# The workflow ledger, named once so callers and tests share one spelling.
STATE_FILE = ".omc/paper-state.md"

# How the template maintainer happens to host this repository is their business,
# not the business of anyone who downloads it. A derived paper gets none of it and
# is asked where it wants to live instead.
MAINTAINER_MARKERS = (
    "원격을 Gitea",
    "core.hooksPath .githooks",
    "Gitea 원본 및/또는 GitHub 미러",
)
MAINTAINER_SECTIONS = ("## 원격 두 곳 운영",)


class Plan:
    """Collects intended changes so --dry-run and --confirm share one code path."""

    def __init__(self, root: Path, confirm: bool):
        self.root = root
        self.confirm = confirm
        self.actions: list[str] = []
        self.skipped: list[str] = []

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return str(path)

    def write(self, path: Path, text: str, what: str) -> None:
        if path.exists() and path.read_text(encoding="utf-8") == text:
            self.skipped.append(f"{self.rel(path)} (already clear)")
            return
        self.actions.append(f"rewrite  {self.rel(path)} - {what}")
        if self.confirm:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")

    def delete(self, path: Path, what: str) -> None:
        if not path.exists():
            return
        self.actions.append(f"delete   {self.rel(path)} - {what}")
        if self.confirm:
            shutil.rmtree(path) if path.is_dir() else path.unlink()


def reset_narrative_and_claims(text: str) -> str:
    """Blank the narrative slots and drop every claim row and falsifier.

    The instructional prose around them is the template and stays; only what a
    previous paper filled in is removed. The legend tables above the ledger
    explain the evidence forms rather than assert anything, so they stay too --
    which is why claim rows are matched on a C<n> id rather than on being a row.
    """
    out: list[str] = []
    in_claims = False
    in_falsifiers = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            in_claims = stripped == "## Claims"
            in_falsifiers = stripped == "## Falsifiers"
        slot = re.match(r"\|\s*(" + "|".join(NARRATIVE_SLOTS) + r")\s*\|", line)
        if slot:
            out.append(f"| {slot.group(1)} | {PLACEHOLDER} |")
            continue
        if in_claims and re.match(r"\|\s*C\d+\s*\|", stripped):
            continue
        if in_falsifiers and re.match(r"-\s+\*\*C\d+", stripped):
            continue
        out.append(line)
    return "\n".join(out)


def reset_story_brief(plan: Plan) -> None:
    path = plan.root / "docs/notes/story-brief.md"
    if not path.exists():
        return
    plan.write(
        path,
        reset_narrative_and_claims(path.read_text(encoding="utf-8")),
        "narrative slots blanked, claims and falsifiers dropped",
    )


def reset_paper_state(plan: Plan) -> None:
    blocks = ["# Paper State", ""]
    for stage in STAGES:
        blocks += [
            f"## Stage: {stage}",
            "status: not-started",
            "round: 0/3",
            "last-critic-verdict:",
            "last-critic-issues:",
            "preconditions:",
            *STAGE_EXTRA_FIELDS.get(stage, ()),
            "",
        ]
    plan.write(plan.root / STATE_FILE, "\n".join(blocks),
               "every stage back to not-started")


def reset_novelty_matrix(plan: Plan) -> None:
    path = plan.root / "docs/notes/novelty-matrix.md"
    if not path.exists():
        return
    out: list[str] = []
    past_separator = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if past_separator and stripped.startswith("|"):
            continue
        out.append(line)
        if stripped.startswith("|") and set(stripped) <= set("|-: "):
            past_separator = True
    plan.write(path, "\n".join(out), "novelty rows dropped")


def reset_sections(plan: Plan) -> None:
    for name, (title, comment) in SECTION_STUBS.items():
        plan.write(plan.root / "docs/sections" / name,
                   f"# {title}\n\n<!-- {comment} -->\n", "back to an empty stub")


def reset_bibliography(plan: Plan) -> None:
    path = plan.root / "refs/references.bib"
    if not path.exists():
        return
    header = [ln for ln in path.read_text(encoding="utf-8").split("\n") if ln.startswith("%")]
    plan.write(path, "\n".join(header) + "\n", "BibTeX entries dropped")


def reset_submission_log(plan: Plan) -> None:
    path = plan.root / "submissions/submission-log.md"
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").split("\n")
    for index, line in enumerate(lines):
        if line.startswith("## Attempt:"):
            plan.write(path, "\n".join(lines[:index]).rstrip("\n") + "\n",
                       "submission attempts dropped")
            return
    plan.skipped.append(f"{plan.rel(path)} (no attempts recorded)")


def reset_claude_md(plan: Plan) -> None:
    """Blank the per-paper header fields and drop a validation-marker blockquote.

    The marker is one contiguous blockquote introduced by a warning line; the
    first line that is neither a quote nor blank ends it.
    """
    path = plan.root / "CLAUDE.md"
    if not path.exists():
        return
    out: list[str] = []
    dropping = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("> **⚠️"):
            dropping = True
            continue
        if dropping:
            if line.startswith(">") or not line.strip():
                continue
            dropping = False
        field = re.match(r"- \*\*(" + "|".join(map(re.escape, HEADER_FIELDS)) + r"):\*\*", line)
        out.append(f"- **{field.group(1)}:** {PLACEHOLDER}" if field else line)
    plan.write(path, re.sub(r"\n{3,}", "\n\n", "\n".join(out)),
               "header fields blanked, validation marker removed")


def drop_maintainer_prose(text: str) -> str:
    """Remove the maintainer's own hosting arrangement from a Markdown file.

    Whole sections go by heading; stray sentences go by marker. A fenced block
    inside a dropped section goes with it, since the section boundary is the
    next heading and a fence cannot contain one.
    """
    out: list[str] = []
    in_dropped_section = False
    for line in text.split("\n"):
        if line.startswith("## "):
            in_dropped_section = any(line.startswith(h) for h in MAINTAINER_SECTIONS)
        if in_dropped_section:
            continue
        if any(marker in line for marker in MAINTAINER_MARKERS):
            continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def strip_maintainer_content(plan: Plan) -> None:
    for name in ("CLAUDE.md", "README.md"):
        path = plan.root / name
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        stripped = drop_maintainer_prose(original)
        if stripped != original:
            plan.write(path, stripped, "maintainer's hosting arrangement removed")
    plan.delete(plan.root / ".githooks", "maintainer's git hooks")


def clear_directory(plan: Plan, rel: str, what: str, keep_suffixes: tuple[str, ...] = ()) -> None:
    directory = plan.root / rel
    if not directory.is_dir():
        return
    for child in sorted(directory.iterdir()):
        if child.name == ".gitkeep" or child.suffix in keep_suffixes:
            continue
        plan.delete(child, what)


def delete_generated_notes(plan: Plan, template_repo: bool) -> None:
    notes = plan.root / "docs/notes"
    if not notes.is_dir():
        return
    for child in sorted(notes.iterdir()):
        if child.name not in TEMPLATE_NOTES:
            plan.delete(child, "topic note written for the previous paper")
    findings = notes / "pipeline-findings.md"
    if template_repo:
        if findings.exists():
            plan.skipped.append(f"{plan.rel(findings)} (kept: --template-repo)")
    else:
        plan.delete(findings, "template-only; belongs to the template repository")


def clear_submission_folders(plan: Plan) -> None:
    submissions = plan.root / "submissions"
    if not submissions.is_dir():
        return
    for child in sorted(submissions.iterdir()):
        if child.is_dir() and child.name != "_template":
            plan.delete(child, "submission attempt folder")


def build_plan(root: Path, confirm: bool, template_repo: bool = False) -> Plan:
    plan = Plan(root, confirm)
    reset_claude_md(plan)
    if not template_repo:
        strip_maintainer_content(plan)
    reset_paper_state(plan)
    reset_story_brief(plan)
    plan.write(root / "docs/notes/retrieved-sources.json", "[]\n", "source registry emptied")
    reset_novelty_matrix(plan)
    reset_sections(plan)
    reset_bibliography(plan)
    reset_submission_log(plan)
    delete_generated_notes(plan, template_repo)
    clear_directory(plan, "figures", "rendered figure")
    clear_directory(plan, "data/processed", "processed data or run manifest")
    clear_directory(plan, "docs/sources", "downloaded PDF (never committed)", keep_suffixes=(".md",))
    clear_submission_folders(plan)
    return plan


def verify(root: Path) -> int:
    """Prove the cleared state still validates, so a reset cannot leave a wreck."""
    checks = [
        [sys.executable, "scripts/check_paper_state.py", "--state", STATE_FILE],
        [sys.executable, "scripts/verify_story_brief.py", "--state", STATE_FILE,
         "--sections", "docs/sections/*.md", "--registry", "docs/notes/retrieved-sources.json"],
        [sys.executable, "scripts/verify_source_registry.py",
         "--registry", "docs/notes/retrieved-sources.json"],
    ]
    failures = 0
    for command in checks:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        print(f"  {'ok  ' if result.returncode == 0 else 'FAIL'} {Path(command[1]).name}")
        if result.returncode != 0:
            failures += 1
            print((result.stdout + result.stderr).rstrip())
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--confirm", action="store_true",
                        help="actually apply the reset; without it nothing is written")
    parser.add_argument("--template-repo", action="store_true",
                        help="this is the template repository itself, not a derived paper: keep "
                             "docs/notes/pipeline-findings.md and the maintainer's hosting setup")
    parser.add_argument("--skip-verify", action="store_true",
                        help="do not run the validators after applying")
    args = parser.parse_args()

    root = args.root.resolve()
    if not (root / STATE_FILE).exists():
        print(f"error: {root} does not look like a paper repository "
              "(the workflow ledger is missing)", file=sys.stderr)
        return 2

    plan = build_plan(root, args.confirm, args.template_repo)

    if not plan.actions:
        print("Nothing to reset - this repository is already clear.")
        return 0

    print(f"{'Applying' if args.confirm else 'Would apply'} {len(plan.actions)} change(s):\n")
    for action in plan.actions:
        print(f"  {action}")
    if plan.skipped:
        print("\nUnchanged:")
        for item in plan.skipped:
            print(f"  {item}")

    if not args.confirm:
        print("\nDry run - nothing was written. Re-run with --confirm to apply.")
        print("data/raw/ is never touched; move the previous paper's inputs out yourself.")
        return 0

    if args.skip_verify:
        return 0
    print("\nVerifying the cleared state:")
    if verify(root):
        print("\nThe reset applied but the cleared state does not validate. "
              "Inspect the failures above before starting a new paper.", file=sys.stderr)
        return 1
    print("\nCleared. This template carries no remote of its own: decide where this paper's\n"
          "repository should live before you push anywhere. Then fill in CLAUDE.md's header\n"
          "and start with the story-brief skill.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
