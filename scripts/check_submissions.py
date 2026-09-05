"""Validate the submission ledger at submissions/submission-log.md.

One paper is submitted to one venue at a time, and each rejection has to be
answered before the next attempt opens. Both rules are easy to break by hand
once a manuscript has been in flight for months, so they are checked here:

- concurrent submission to two venues is research misconduct, not a slip
- opening a new attempt without folding in the previous reviewers' points
  throws away the only feedback the paper has received
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

ATTEMPT_HEADER_RE = re.compile(r"^## Attempt: (?P<id>.+)$")
FIELD_RE = re.compile(r"^(?P<key>[\w-]+):\s*(?P<value>.*)$")
POINT_RE = re.compile(r'^\s*-\s*"?(?P<point>.*?)"?\s*$')
ATTEMPT_ID_RE = re.compile(r"^(?P<seq>\d{2})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$")

SCALAR_FIELDS = (
    "venue",
    "venue-url",
    "status",
    "submitted-on",
    "decision-on",
    "manuscript-tag",
    "carried-forward",
)
LIST_FIELDS = ("reviewer-points",)

# Before the manuscript has left the desk.
PREPARING_STATUSES = {"preparing"}
# In the venue's hands - only one attempt may sit here at a time.
ACTIVE_STATUSES = {"submitted", "under-review", "minor-revision", "major-revision"}
# The attempt is over without acceptance.
CLOSED_NEGATIVE_STATUSES = {"rejected", "desk-rejected", "withdrawn"}
ACCEPTED_STATUS = "accepted"
ALLOWED_STATUSES = (
    PREPARING_STATUSES | ACTIVE_STATUSES | CLOSED_NEGATIVE_STATUSES | {ACCEPTED_STATUS}
)
# Statuses meaning the manuscript actually reached the venue.
SUBMITTED_STATUSES = ALLOWED_STATUSES - PREPARING_STATUSES
DECIDED_STATUSES = CLOSED_NEGATIVE_STATUSES | {ACCEPTED_STATUS}
BOOLEAN_VALUES = {"yes", "no"}

# Figures are re-rendered per venue, so each attempt folder carries a render profile.
FIGURE_PROFILE_NAME = "figure-profile.json"
VENUE_NOTES_NAME = "venue.md"
FIGURES_DIR_NAME = "figures"
VECTOR_FIGURE_FORMATS = {"eps", "pdf", "svg"}
RASTER_FIGURE_FORMATS = {"tiff", "tif", "png", "jpg", "jpeg"}
ALLOWED_FIGURE_FORMATS = VECTOR_FIGURE_FORMATS | RASTER_FIGURE_FORMATS
MIN_RASTER_DPI = 300


def parse_attempts(log_path: Path) -> list[dict]:
    attempts: list[dict] = []
    current: dict | None = None
    list_field: str | None = None

    for raw_line in log_path.read_text(encoding="utf-8").splitlines():
        header_match = ATTEMPT_HEADER_RE.match(raw_line)
        if header_match:
            if current is not None:
                attempts.append(current)
            current = {"id": header_match.group("id").strip()}
            current.update({field: None for field in SCALAR_FIELDS})
            current.update({field: [] for field in LIST_FIELDS})
            list_field = None
            continue

        if current is None:
            continue

        field_match = FIELD_RE.match(raw_line)
        if field_match:
            key = field_match.group("key")
            value = field_match.group("value").strip()
            list_field = key if key in LIST_FIELDS else None
            if key in SCALAR_FIELDS:
                current[key] = value or None
            continue

        if list_field and raw_line.strip().startswith("-"):
            point_match = POINT_RE.match(raw_line)
            if point_match:
                current[list_field].append(point_match.group("point"))

    if current is not None:
        attempts.append(current)
    return attempts


def _parse_day(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def validate_attempt(attempt: dict, today: date | None = None) -> list[str]:
    errors: list[str] = []
    attempt_id = attempt["id"]
    current_day = today or date.today()

    if not ATTEMPT_ID_RE.match(attempt_id):
        errors.append(f"{attempt_id}: id must look like '01-venue-slug'")

    if not attempt["venue"]:
        errors.append(f"{attempt_id}: venue is required")

    status = attempt["status"]
    if status not in ALLOWED_STATUSES:
        errors.append(f"{attempt_id}: invalid status '{status}'")
        return errors

    submitted_on = attempt["submitted-on"]
    decision_on = attempt["decision-on"]

    if status in SUBMITTED_STATUSES:
        if not submitted_on:
            errors.append(f"{attempt_id}: status '{status}' requires submitted-on")
        if not attempt["manuscript-tag"]:
            errors.append(
                f"{attempt_id}: status '{status}' requires manuscript-tag "
                "recording exactly what was sent"
            )
    elif submitted_on:
        errors.append(f"{attempt_id}: status 'preparing' must not have submitted-on")

    submitted_day = _parse_day(submitted_on)
    if submitted_on and submitted_day is None:
        errors.append(f"{attempt_id}: submitted-on must use YYYY-MM-DD")
    elif submitted_day and submitted_day > current_day:
        errors.append(f"{attempt_id}: submitted-on is in the future")

    decision_day = _parse_day(decision_on)
    if decision_on and decision_day is None:
        errors.append(f"{attempt_id}: decision-on must use YYYY-MM-DD")
    elif decision_day and decision_day > current_day:
        errors.append(f"{attempt_id}: decision-on is in the future")

    if status in DECIDED_STATUSES and not decision_on:
        errors.append(f"{attempt_id}: status '{status}' requires decision-on")
    if status not in DECIDED_STATUSES and decision_on:
        errors.append(f"{attempt_id}: decision-on set while status is '{status}'")

    if submitted_day and decision_day and decision_day < submitted_day:
        errors.append(f"{attempt_id}: decision-on precedes submitted-on")

    carried = attempt["carried-forward"]
    if carried is not None and carried not in BOOLEAN_VALUES:
        errors.append(f"{attempt_id}: carried-forward must be 'yes' or 'no'")

    return errors


def validate_figure_profile(label: str, profile: dict) -> list[str]:
    """A venue's figure render settings, checked against what journals actually demand."""
    errors: list[str] = []

    fmt = profile.get("format")
    if not isinstance(fmt, str) or fmt.lower() not in ALLOWED_FIGURE_FORMATS:
        errors.append(f"{label}: format must be one of {', '.join(sorted(ALLOWED_FIGURE_FORMATS))}")
        fmt = None
    else:
        fmt = fmt.lower()

    dpi = profile.get("dpi")
    if fmt in RASTER_FIGURE_FORMATS:
        if not isinstance(dpi, int) or isinstance(dpi, bool):
            errors.append(f"{label}: dpi must be an integer for raster format '{fmt}'")
        elif dpi < MIN_RASTER_DPI:
            errors.append(
                f"{label}: dpi {dpi} is below the {MIN_RASTER_DPI} that most venues require"
            )

    widths = profile.get("column_width_mm")
    if not isinstance(widths, dict) or not widths:
        errors.append(f"{label}: column_width_mm must map column names to widths in mm")
    else:
        for name, value in widths.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                errors.append(f"{label}: column_width_mm['{name}'] must be a positive number")

    main = profile.get("main_figures")
    if not isinstance(main, list) or not all(isinstance(item, str) and item for item in main):
        errors.append(f"{label}: main_figures must be a list of figure names")
        main = []

    supplementary = profile.get("supplementary_figures", [])
    if not isinstance(supplementary, list) or not all(
        isinstance(item, str) and item for item in supplementary
    ):
        errors.append(f"{label}: supplementary_figures must be a list of figure names")
        supplementary = []

    overlap = sorted(set(main) & set(supplementary))
    if overlap:
        errors.append(f"{label}: {', '.join(overlap)} listed as both main and supplementary")

    return errors


def validate_attempt_folder(attempt: dict, attempts_dir: Path) -> list[str]:
    """Once an attempt has left 'preparing', its venue folder must hold what was sent."""
    errors: list[str] = []
    attempt_id = attempt["id"]
    if attempt["status"] not in SUBMITTED_STATUSES:
        return errors

    folder = attempts_dir / attempt_id
    if not folder.is_dir():
        return [f"{attempt_id}: no folder at {folder}"]

    if not (folder / VENUE_NOTES_NAME).is_file():
        errors.append(f"{attempt_id}: missing {VENUE_NOTES_NAME}")

    profile_path = folder / FIGURE_PROFILE_NAME
    if not profile_path.is_file():
        return errors + [f"{attempt_id}: missing {FIGURE_PROFILE_NAME}"]

    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return errors + [f"{attempt_id}: {FIGURE_PROFILE_NAME} cannot be read: {exc}"]

    if not isinstance(profile, dict):
        return errors + [f"{attempt_id}: {FIGURE_PROFILE_NAME} must be a JSON object"]

    errors.extend(validate_figure_profile(attempt_id, profile))

    fmt = profile.get("format")
    figures = profile.get("main_figures")
    if not isinstance(fmt, str) or not isinstance(figures, list):
        return errors

    figures_dir = folder / FIGURES_DIR_NAME
    missing = [
        name
        for name in figures
        if isinstance(name, str) and not (figures_dir / f"{name}.{fmt.lower()}").is_file()
    ]
    if missing:
        errors.append(
            f"{attempt_id}: rendered figures missing from {figures_dir}: "
            f"{', '.join(f'{name}.{fmt.lower()}' for name in missing)}"
        )
    return errors


def validate_ledger(
    log_path: Path, today: date | None = None, attempts_dir: Path | None = None
) -> dict[str, list[str]]:
    report: dict[str, list[str]] = {}
    attempts = parse_attempts(log_path)
    ledger_errors: list[str] = []

    ids = [attempt["id"] for attempt in attempts]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        ledger_errors.append(f"duplicate attempts: {', '.join(duplicates)}")

    sequence = [m.group("seq") for i in ids if (m := ATTEMPT_ID_RE.match(i))]
    expected = [f"{n:02d}" for n in range(1, len(sequence) + 1)]
    if sequence and sequence != expected:
        ledger_errors.append(
            f"attempt numbers must run {', '.join(expected)} in order (got {', '.join(sequence)})"
        )

    active = [a["id"] for a in attempts if a["status"] in ACTIVE_STATUSES]
    if len(active) > 1:
        ledger_errors.append(
            f"concurrent submission: {', '.join(active)} are all with a venue at once"
        )

    accepted = [a["id"] for a in attempts if a["status"] == ACCEPTED_STATUS]
    if len(accepted) > 1:
        ledger_errors.append(f"more than one accepted attempt: {', '.join(accepted)}")
    elif accepted and attempts[-1]["id"] != accepted[0]:
        ledger_errors.append(f"attempts recorded after {accepted[0]} was accepted")

    for previous, following in zip(attempts, attempts[1:]):
        if previous["status"] in PREPARING_STATUSES:
            ledger_errors.append(
                f"{following['id']} opened while {previous['id']} is still 'preparing'"
            )
        if previous["status"] in CLOSED_NEGATIVE_STATUSES and previous["carried-forward"] != "yes":
            ledger_errors.append(
                f"{previous['id']} closed as '{previous['status']}' but its reviewer points "
                f"were not carried forward before {following['id']} opened"
            )

    if ledger_errors:
        report["__ledger__"] = ledger_errors

    for attempt in attempts:
        errors = validate_attempt(attempt, today=today)
        if attempts_dir is not None:
            errors.extend(validate_attempt_folder(attempt, attempts_dir))
        if errors:
            report.setdefault(attempt["id"], []).extend(errors)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate submissions/submission-log.md")
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument(
        "--attempts-dir",
        type=Path,
        help="Directory holding the NN-<venue-slug> folders (default: the log's own directory)",
    )
    args = parser.parse_args()

    if not args.log.exists():
        print(f"Note: {args.log} not found - no submissions recorded yet.")
        return 0

    attempts_dir = args.attempts_dir or args.log.parent
    report = validate_ledger(args.log, attempts_dir=attempts_dir)
    if not report:
        print("submission-log.md is valid.")
        return 0

    print("submission-log.md validation errors:")
    for errors in report.values():
        for error in errors:
            print(f"  {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
