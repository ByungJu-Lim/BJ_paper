"""Validate the structure and invariants of .omc/paper-state.md."""
import re
from pathlib import Path

try:
    from .validation_common import parse_outline_sections, section_artifact_id
except ImportError:  # pragma: no cover - script execution path
    from validation_common import parse_outline_sections, section_artifact_id

STAGE_HEADER_RE = re.compile(r"^## Stage: (?P<id>.+)$")
FIELD_RE = re.compile(r"^(?P<key>[\w-]+):\s*(?P<value>.*)$")
ISSUE_RE = re.compile(r'^\s*-\s*"?(?P<issue>.*?)"?\s*$')

TRACKED_SCALAR_FIELDS = ("status", "round", "last-critic-verdict", "verified-sources")
LIST_FIELDS = ("last-critic-issues", "rejected-citations", "preconditions", "artifacts")
ARTIFACT_RE = re.compile(
    r"^(?P<id>[a-z][a-z0-9-]*):\s*"
    r"(?P<status>[a-z-]+),\s*round\s+(?P<round>\d+/\d+),\s*"
    r"verdict\s+(?P<verdict>pass|revise|none)$"
)
DEFAULT_OUTLINE_PATH = Path("docs/outline.md")
# A review at one stage routinely turns up something a *later* stage must settle.
# Prose in a notes file cannot bind it: the later session has no structural reason
# to open that file. A precondition recorded here does bind it, because the stage
# cannot be approved while one is still open.
PRECONDITION_RE = re.compile(r"^(?P<state>open|resolved):\s*(?P<text>.+)$")
# The only stage carrying citation bookkeeping beyond the common fields.
CITATION_STAGE_ID = "citation-manage"
REQUIRED_STAGE_IDS = (
    "story-brief",
    "lit-review",
    "novelty-check",
    "outline-draft",
    "code-experiment",
    "results-discussion",
    "figures-tables",
    "citation-manage",
    "polish-review",
)
STAGE_DEPENDENCIES = {
    "lit-review": ("story-brief",),
    "novelty-check": ("lit-review",),
    "outline-draft": ("novelty-check",),
    "code-experiment": ("outline-draft",),
    "results-discussion": ("code-experiment",),
    "figures-tables": ("code-experiment",),
    "citation-manage": ("results-discussion", "figures-tables"),
    "polish-review": ("citation-manage",),
}


def parse_stages(state_path: Path) -> list[dict]:
    stages: list[dict] = []
    current: dict | None = None
    list_field: str | None = None

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
                "verified-sources": None,
                "last-critic-issues": [],
                "rejected-citations": [],
                "preconditions": [],
                "artifacts": [],
                "_field-errors": [],
                "_seen-scalar-fields": set(),
            }
            list_field = None
            continue

        if current is None:
            continue

        field_match = FIELD_RE.match(raw_line)
        if field_match:
            key = field_match.group("key")
            value = field_match.group("value").strip()
            list_field = key if key in LIST_FIELDS else None
            if key in TRACKED_SCALAR_FIELDS:
                if key in current["_seen-scalar-fields"]:
                    current["_field-errors"].append(
                        f"{current['id']}: duplicate scalar field '{key}'"
                    )
                current["_seen-scalar-fields"].add(key)
                current[key] = value or None
            continue

        if list_field:
            issue_match = ISSUE_RE.match(raw_line)
            if issue_match and raw_line.strip().startswith("-"):
                current[list_field].append(issue_match.group("issue"))

    if current is not None:
        stages.append(current)

    return stages


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
    errors: list[str] = list(stage.get("_field-errors", []))
    stage_id = stage["id"]

    status = stage["status"]
    if status not in ALLOWED_STATUSES:
        errors.append(f"{stage_id}: invalid status '{status}'")

    current_round = None
    max_round = None
    round_value = stage["round"]
    if not round_value:
        errors.append(f"{stage_id}: round is required")
    else:
        round_match = re.match(r"^(\d+)/(\d+)$", round_value)
        if not round_match:
            errors.append(f"{stage_id}: invalid round format '{round_value}', expected 'n/3'")
        else:
            current_round, max_round = int(round_match.group(1)), int(round_match.group(2))

    verdict = stage["last-critic-verdict"]
    if verdict is not None and verdict not in ALLOWED_VERDICTS:
        errors.append(f"{stage_id}: invalid last-critic-verdict '{verdict}'")

    if status == "not-started" and verdict is not None:
        errors.append(f"{stage_id}: status 'not-started' must not retain a critic verdict")
    if status in {"approved", "awaiting-user"} and verdict != "pass":
        errors.append(f"{stage_id}: status '{status}' requires last-critic-verdict 'pass'")
    if status == "awaiting-review" and verdict is not None:
        errors.append(f"{stage_id}: awaiting-review must not already have a critic verdict")
    if status == 'not-started' and verdict is not None:
        errors.append(f"{stage_id}: not-started must not retain a critic verdict")

    if current_round is not None and max_round is not None:
        if max_round != 3:
            errors.append(f"{stage_id}: round denominator must be 3 (got '{max_round}')")
        if not 0 <= current_round <= max_round:
            errors.append(f"{stage_id}: round must be between 0 and {max_round}")
        if status == "not-started" and current_round != 0:
            errors.append(f"{stage_id}: status 'not-started' requires round 0/3")
        if status == "awaiting-review" and current_round == 0:
            errors.append(f"{stage_id}: awaiting-review requires at least one generation round")
        if status in {"approved", "awaiting-user"} and current_round == 0:
            errors.append(f"{stage_id}: status '{status}' requires at least one review round")
        if status == 'awaiting-review' and current_round == 0:
            errors.append(f"{stage_id}: awaiting-review requires a generated attempt (round >= 1)")
        if (
            current_round >= max_round
            and verdict == "revise"
            and status != "escalated"
        ):
            errors.append(
                f"{stage_id}: round {current_round}/{max_round} reached without "
                f"status 'escalated' (got '{status}')"
            )

    errors.extend(validate_citation_bookkeeping(stage))
    return errors


def expected_outline_artifact_ids(outline_path: Path) -> list[str]:
    """`outline`, then one artifact per front-matter section in outline order.

    `outline-draft` drafts only front-matter sections (by default
    Introduction, Related Work, Methods) - concluding sections stay scaffolds
    until `results-discussion` has real data to report. Before `outline-draft`
    has written the Sections table (early in the pipeline, or right after a
    reset), there is nothing to derive section artifacts from yet, so the
    ledger is expected to carry only `outline` itself: the row `outline-draft`
    produces before any section exists. Once the table exists, its row order
    fixes the required order - a paper whose story needs a different shape
    gets a different ledger, not a fixed four-artifact one.
    """
    rows = parse_outline_sections(outline_path)
    front_matter = [row for row in rows if row["role"] == "front-matter"]
    return ["outline"] + [section_artifact_id(row["file"]) for row in front_matter]


def validate_outline_artifacts(stage: dict, outline_path: Path | None = None) -> list[str]:
    """Validate the nested review ledger used by `outline-draft`.

    The stage-level round belongs to the final package review. The outline
    itself and each front-matter section the outline lists (Introduction,
    Related Work, Methods by default - but whatever `docs/outline.md`'s
    Sections table actually says, since the story decides the shape) each
    have a separate maximum-three review loop and explicit user gate
    recorded here.
    """
    entries = stage.get("artifacts", [])
    if stage.get("id") != "outline-draft":
        return [f"{stage.get('id')}: artifacts belongs to outline-draft only"] if entries else []

    expected_ids = expected_outline_artifact_ids(outline_path or DEFAULT_OUTLINE_PATH)
    if not entries:
        return [f"outline-draft: requires artifacts ledger for {', '.join(expected_ids)}"]

    errors: list[str] = []
    parsed: list[dict] = []
    for entry in entries:
        match = ARTIFACT_RE.fullmatch(entry)
        if not match:
            errors.append(
                "outline-draft: artifact must read '<id>: <status>, round n/3, "
                f"verdict <pass|revise|none>', got '{entry}'"
            )
            continue
        item = match.groupdict()
        item["verdict"] = None if item["verdict"] == "none" else item["verdict"]
        parsed.append(item)

    ids = [item["id"] for item in parsed]
    duplicates = sorted({artifact_id for artifact_id in ids if ids.count(artifact_id) > 1})
    missing = [artifact_id for artifact_id in expected_ids if artifact_id not in ids]
    unknown = [artifact_id for artifact_id in ids if artifact_id not in expected_ids]
    if duplicates:
        errors.append(f"outline-draft: duplicate artifacts: {', '.join(duplicates)}")
    if missing:
        errors.append(f"outline-draft: missing artifacts: {', '.join(missing)}")
    if unknown:
        errors.append(f"outline-draft: unknown artifacts: {', '.join(unknown)}")
    known = [artifact_id for artifact_id in ids if artifact_id in expected_ids]
    expected_order = [artifact_id for artifact_id in expected_ids if artifact_id in ids]
    if known != expected_order:
        errors.append("outline-draft: artifacts are not in required order")

    by_id = {item["id"]: item for item in parsed if item["id"] in expected_ids}
    for artifact_id in expected_ids:
        item = by_id.get(artifact_id)
        if item is None:
            continue
        status = item["status"]
        verdict = item["verdict"]
        if status not in ALLOWED_STATUSES:
            errors.append(f"outline-draft/{artifact_id}: invalid status '{status}'")
            continue
        round_match = re.fullmatch(r"(\d+)/(\d+)", item["round"])
        if not round_match:
            errors.append(f"outline-draft/{artifact_id}: invalid round '{item['round']}'")
            continue
        current_round, max_round = map(int, round_match.groups())
        if max_round != 3 or not 0 <= current_round <= 3:
            errors.append(f"outline-draft/{artifact_id}: round must be n/3 with 0 <= n <= 3")
        if status == "not-started" and (current_round != 0 or verdict is not None):
            errors.append(f"outline-draft/{artifact_id}: not-started requires round 0/3 and verdict none")
        if status == "awaiting-review" and (current_round == 0 or verdict is not None):
            errors.append(f"outline-draft/{artifact_id}: awaiting-review requires round >= 1 and verdict none")
        if status in {"approved", "awaiting-user"} and (current_round == 0 or verdict != "pass"):
            errors.append(f"outline-draft/{artifact_id}: {status} requires round >= 1 and verdict pass")
        if current_round >= 3 and verdict == "revise" and status != "escalated":
            errors.append(f"outline-draft/{artifact_id}: round 3/3 revise requires status escalated")

    # Artifacts are sequential user gates: a later one cannot start while an
    # earlier one is anything other than approved.
    for index, artifact_id in enumerate(expected_ids[1:], start=1):
        item = by_id.get(artifact_id)
        if item and item["status"] != "not-started":
            blockers = [prior for prior in expected_ids[:index]
                        if by_id.get(prior, {}).get("status") != "approved"]
            if blockers:
                errors.append(
                    f"outline-draft/{artifact_id}: requires approved artifacts: "
                    + ", ".join(blockers)
                )

    if stage.get("status") == "not-started" and any(
        item["status"] != "not-started" for item in parsed
    ):
        errors.append("outline-draft: not-started stage requires all artifacts not-started")
    if stage.get("status") == "approved":
        incomplete = [artifact_id for artifact_id in expected_ids
                      if by_id.get(artifact_id, {}).get("status") != "approved"]
        if incomplete:
            errors.append(
                "outline-draft: cannot be approved until all artifacts are approved: "
                + ", ".join(incomplete)
            )
    return errors


def open_preconditions(stage: dict) -> list[str]:
    """The unmet preconditions on a stage, in the order they were recorded."""
    texts = []
    for entry in stage.get("preconditions", []):
        match = PRECONDITION_RE.match(entry)
        if match and match.group("state") == "open":
            texts.append(match.group("text").strip())
    return texts


def validate_preconditions(stage: dict) -> list[str]:
    """Preconditions are kept, not deleted, once met - the record of what was owed
    is worth as much as the fact that it is now paid, so a met one is marked
    'resolved:' rather than removed."""
    errors: list[str] = []
    stage_id = stage["id"]
    for entry in stage.get("preconditions", []):
        if not PRECONDITION_RE.match(entry):
            errors.append(
                f"{stage_id}: precondition must read 'open: <what is owed>' or "
                f"'resolved: <what was owed>', got '{entry}'"
            )
    unmet = open_preconditions(stage)
    if unmet and stage["status"] == "approved":
        errors.append(
            f"{stage_id}: cannot be approved with {len(unmet)} open precondition(s): "
            + "; ".join(unmet)
        )
    return errors


def validate_citation_bookkeeping(stage: dict) -> list[str]:
    """citation-manage tracks how many sources survived verification and what was rejected."""
    stage_id = stage["id"]
    verified = stage.get("verified-sources")

    if stage_id != CITATION_STAGE_ID:
        if verified is not None:
            return [f"{stage_id}: verified-sources belongs to {CITATION_STAGE_ID} only"]
        return []

    if verified is None:
        return [f"{stage_id}: verified-sources is required"]
    if not re.fullmatch(r"\d+", verified):
        return [f"{stage_id}: verified-sources must be a non-negative integer (got '{verified}')"]

    # An approved citation stage that verified nothing means the bibliography is empty,
    # which is only ever an accident this late in the pipeline.
    if stage["status"] == "approved" and int(verified) == 0:
        return [f"{stage_id}: approved with verified-sources 0"]
    return []


def validate_all(state_path: Path, outline_path: Path | None = None) -> dict[str, list[str]]:
    report: dict[str, list[str]] = {}
    stages = parse_stages(state_path)
    stage_ids = [stage["id"] for stage in stages]
    workflow_errors: list[str] = []

    duplicates = sorted({stage_id for stage_id in stage_ids if stage_ids.count(stage_id) > 1})
    missing = [stage_id for stage_id in REQUIRED_STAGE_IDS if stage_id not in stage_ids]
    unknown = [stage_id for stage_id in stage_ids if stage_id not in REQUIRED_STAGE_IDS]
    known_in_file = [stage_id for stage_id in stage_ids if stage_id in REQUIRED_STAGE_IDS]
    expected_known_order = [stage_id for stage_id in REQUIRED_STAGE_IDS if stage_id in stage_ids]

    if duplicates:
        workflow_errors.append(f"duplicate stages: {', '.join(duplicates)}")
    if missing:
        workflow_errors.append(f"missing stages: {', '.join(missing)}")
    if unknown:
        workflow_errors.append(f"unknown stages: {', '.join(unknown)}")
    if known_in_file != expected_known_order:
        workflow_errors.append("stages are not in the required workflow order")
    if workflow_errors:
        report["__workflow__"] = workflow_errors

    for stage in stages:
        errors = (validate_stage(stage) + validate_preconditions(stage)
                  + validate_outline_artifacts(stage, outline_path))
        if errors:
            report.setdefault(stage["id"], []).extend(errors)

    by_id = {stage["id"]: stage for stage in stages}
    for stage_id, dependencies in STAGE_DEPENDENCIES.items():
        stage = by_id.get(stage_id)
        if stage is None or stage["status"] == "not-started":
            continue
        missing_approvals = [
            dependency
            for dependency in dependencies
            if by_id.get(dependency, {}).get("status") != "approved"
        ]
        if missing_approvals:
            report.setdefault(stage_id, []).append(
                f"{stage_id}: status '{stage['status']}' requires approved prerequisites: "
                f"{', '.join(missing_approvals)}"
            )
    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate .omc/paper-state.md")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--outline", type=Path, default=DEFAULT_OUTLINE_PATH,
                        help="docs/outline.md, whose Sections table decides the "
                             "outline-draft artifact ledger's expected shape")
    args = parser.parse_args()

    report = validate_all(args.state, args.outline)
    if not report:
        print("paper-state.md is valid.")
        # Printed on success as well: a precondition nobody reads binds nothing.
        for stage in parse_stages(args.state):
            for text in open_preconditions(stage):
                print(f"  open precondition on {stage['id']}: {text}")
        return 0

    print("paper-state.md validation errors:")
    for stage_id, errors in report.items():
        for error in errors:
            print(f"  {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
