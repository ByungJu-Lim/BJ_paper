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
