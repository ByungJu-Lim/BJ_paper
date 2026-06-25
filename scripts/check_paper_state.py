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
