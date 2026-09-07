"""Validate the structure and invariants of .omc/paper-state.md."""
import re
from pathlib import Path

STAGE_HEADER_RE = re.compile(r"^## Stage: (?P<id>.+)$")
FIELD_RE = re.compile(r"^(?P<key>[\w-]+):\s*(?P<value>.*)$")
ISSUE_RE = re.compile(r'^\s*-\s*"?(?P<issue>.*?)"?\s*$')

TRACKED_SCALAR_FIELDS = ("status", "round", "last-critic-verdict", "verified-sources")
LIST_FIELDS = ("last-critic-issues", "rejected-citations")
# The only stage carrying citation bookkeeping beyond the common fields.
CITATION_STAGE_ID = "citation-manage"
REQUIRED_STAGE_IDS = (
    "story-brief",
    "lit-review",
    "novelty-check",
    "outline-draft",
    "results-discussion",
    "code-experiment",
    "figures-tables",
    "citation-manage",
    "polish-review",
)


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
        if max_round != 3:
            errors.append(f"{stage_id}: round denominator must be 3 (got '{max_round}')")
        if not 0 <= current_round <= max_round:
            errors.append(f"{stage_id}: round must be between 0 and {max_round}")
        if status == "not-started" and current_round != 0:
            errors.append(f"{stage_id}: status 'not-started' requires round 0/3")
        if (
            current_round >= max_round
            and verdict == "revise"
            and status not in {"escalated", "approved"}
        ):
            errors.append(
                f"{stage_id}: round {current_round}/{max_round} reached without "
                f"status 'escalated' or 'approved' (got '{status}')"
            )

    errors.extend(validate_citation_bookkeeping(stage))
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


def validate_all(state_path: Path) -> dict[str, list[str]]:
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
        errors = validate_stage(stage)
        if errors:
            report.setdefault(stage["id"], []).extend(errors)
    return report


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
