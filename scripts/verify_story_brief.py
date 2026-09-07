"""Check the story brief's internal consistency and how the sections use it.

The brief (docs/notes/story-brief.md) holds the paper's argument as six narrative
slots plus a ledger of load-bearing claims. It is written before the literature
search and revised as evidence arrives, so the risk it introduces is the opposite
of a fabricated citation: a story that stops matching what was actually found.

Four invariants keep the argument honest:

A. every claim a section declares exists in the brief   (no orphan claims)
B. no section carries a refuted claim                   (evidence beats narrative)
C. concluding sections carry no assumed claim           (no hypothesis stated as result)
D. every evidence entry resolves                        (no invented backing)

Sections declare what they carry with one comment line under the heading:

    <!-- claims: C1, C3 -->
"""
import argparse
import json
import re
from pathlib import Path

DEFAULT_BRIEF_PATH = Path("docs/notes/story-brief.md")
DEFAULT_PROCESSED_DIR = Path("data/processed")

NARRATIVE_SLOTS = ("Context", "Gap", "Question", "Approach", "Finding", "Implication")
CLAIM_STATUSES = ("assumed", "supported", "refuted")
# Sections that report outcomes; an assumed claim may not be asserted in these.
CONCLUDING_SECTION_MARKERS = ("results", "discussion", "conclusion")

NARRATIVE_HEADER_RE = re.compile(r"^\|\s*Slot\s*\|\s*Sentence\s*\|$", re.IGNORECASE)
CLAIM_HEADER_RE = re.compile(
    r"^\|\s*ID\s*\|\s*Claim\s*\|\s*Status\s*\|\s*Evidence\s*\|$", re.IGNORECASE
)
TABLE_DIVIDER_RE = re.compile(r"^\|[\s:|-]+\|$")
# The colon may sit inside or outside the bold markers: `- **C1:** ...` or `- **C1**: ...`
FALSIFIER_RE = re.compile(r"^\s*-\s*\*\*(?P<id>C\d+)\s*:?\s*\*\*\s*:?\s*(?P<text>.*?)\s*$")
CLAIM_ID_RE = re.compile(r"^C\d+$")
PLACEHOLDER_RE = re.compile(r"^_.*_$")
SECTION_CLAIMS_RE = re.compile(r"<!--\s*claims\s*:\s*(?P<ids>[^>]*?)-->", re.IGNORECASE)
RUN_EVIDENCE_RE = re.compile(r"^run:(?P<run_id>[\w.\-]+)$")
FIGURE_EVIDENCE_RE = re.compile(r"^(?:Fig\.?|Figure|Table|Tab\.?)\s*\d+[a-z]?$", re.IGNORECASE)
SOURCE_EVIDENCE_RE = re.compile(r"^@(?P<key>[^\s,]+)$")


def is_placeholder(value: str) -> bool:
    """An unfilled cell: empty, or the `_입력 필요_` style marker the template ships with."""
    stripped = value.strip()
    return not stripped or bool(PLACEHOLDER_RE.match(stripped))


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _read_table(lines: list[str], start: int) -> list[list[str]]:
    """Read the body rows of a markdown table whose header sits at `start`."""
    rows: list[list[str]] = []
    index = start + 1
    if index < len(lines) and TABLE_DIVIDER_RE.match(lines[index].strip()):
        index += 1
    while index < len(lines) and lines[index].strip().startswith("|"):
        rows.append(_split_row(lines[index]))
        index += 1
    return rows


def parse_brief(brief_path: Path) -> dict:
    """Parse the brief into slots, claims, and falsifiers. Tables are found by header."""
    lines = brief_path.read_text(encoding="utf-8").splitlines()

    slots: list[tuple[str, str]] = []
    claims: list[dict] = []
    falsifiers: dict[str, str] = {}

    for index, line in enumerate(lines):
        stripped = line.strip()
        if NARRATIVE_HEADER_RE.match(stripped):
            slots = [(row[0], row[1] if len(row) > 1 else "") for row in _read_table(lines, index)]
        elif CLAIM_HEADER_RE.match(stripped):
            for row in _read_table(lines, index):
                padded = row + [""] * (4 - len(row))
                claims.append(
                    {
                        "id": padded[0],
                        "claim": padded[1],
                        "status": padded[2],
                        "evidence": padded[3],
                    }
                )
        else:
            falsifier_match = FALSIFIER_RE.match(line)
            if falsifier_match:
                falsifiers[falsifier_match.group("id")] = falsifier_match.group("text")

    return {"slots": slots, "claims": claims, "falsifiers": falsifiers}


def parse_evidence(evidence: str) -> list[str]:
    return [entry.strip() for entry in evidence.split(",") if entry.strip()]


def validate_narrative(brief: dict, required_slots: list[str]) -> list[str]:
    errors: list[str] = []
    slot_names = [name for name, _ in brief["slots"]]

    missing = [slot for slot in NARRATIVE_SLOTS if slot not in slot_names]
    if missing:
        errors.append(f"narrative: missing slots: {', '.join(missing)}")
    unknown = [name for name in slot_names if name not in NARRATIVE_SLOTS]
    if unknown:
        errors.append(f"narrative: unknown slots: {', '.join(unknown)}")

    present_in_order = [slot for slot in NARRATIVE_SLOTS if slot in slot_names]
    known_as_written = [name for name in slot_names if name in NARRATIVE_SLOTS]
    if known_as_written != present_in_order:
        errors.append(
            "narrative: slots are not in Context-Gap-Question-Approach-Finding-Implication order"
        )

    sentences = dict(brief["slots"])
    for slot in required_slots:
        if slot not in NARRATIVE_SLOTS:
            errors.append(f"narrative: '{slot}' is not a narrative slot")
            continue
        if is_placeholder(sentences.get(slot, "")):
            errors.append(f"narrative: slot '{slot}' is required at this stage but still unfilled")

    return errors


def validate_claims(brief: dict) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()

    for claim in brief["claims"]:
        claim_id = claim["id"]
        if not CLAIM_ID_RE.match(claim_id):
            errors.append(f"claims: invalid claim id '{claim_id}', expected C<number>")
            continue
        if claim_id in seen:
            errors.append(f"claims: duplicate claim id '{claim_id}'")
            continue
        seen.add(claim_id)

        status = claim["status"]
        if status not in CLAIM_STATUSES:
            errors.append(
                f"{claim_id}: invalid status '{status}', "
                f"expected one of {', '.join(CLAIM_STATUSES)}"
            )

        evidence = parse_evidence(claim["evidence"])
        if status in {"supported", "refuted"} and not evidence:
            errors.append(f"{claim_id}: status '{status}' requires at least one evidence entry")

        falsifier = brief["falsifiers"].get(claim_id)
        if falsifier is None:
            errors.append(f"{claim_id}: no falsifier recorded")
        elif status in {"supported", "refuted"} and is_placeholder(falsifier):
            errors.append(f"{claim_id}: status '{status}' requires a written falsifier")

    unknown_falsifiers = sorted(set(brief["falsifiers"]) - seen)
    if unknown_falsifiers:
        errors.append(f"falsifiers: no such claim: {', '.join(unknown_falsifiers)}")

    return errors


def _registry_keys(registry_path: Path) -> set[str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("retrieved-sources registry must be a JSON array")
    return {entry["key"] for entry in data if isinstance(entry, dict) and entry.get("key")}


def validate_evidence(brief: dict, registry_path: Path | None, processed_dir: Path) -> list[str]:
    """Invariant D: every evidence entry names something that actually exists."""
    errors: list[str] = []
    keys = _registry_keys(registry_path) if registry_path and registry_path.exists() else None

    for claim in brief["claims"]:
        for entry in parse_evidence(claim["evidence"]):
            source_match = SOURCE_EVIDENCE_RE.match(entry)
            if source_match:
                key = source_match.group("key")
                if keys is not None and key not in keys:
                    errors.append(f"{claim['id']}: evidence '@{key}' is not in the source registry")
                continue

            run_match = RUN_EVIDENCE_RE.match(entry)
            if run_match:
                manifest = processed_dir / f"{run_match.group('run_id')}.manifest.json"
                if not manifest.exists():
                    errors.append(f"{claim['id']}: evidence '{entry}' has no manifest at {manifest}")
                continue

            if FIGURE_EVIDENCE_RE.match(entry):
                continue

            errors.append(
                f"{claim['id']}: unrecognised evidence '{entry}' "
                "(expected @key, run:<run-id>, or Fig./Table N)"
            )

    return errors


def extract_section_claims(section_path: Path) -> set[str]:
    text = section_path.read_text(encoding="utf-8")
    claim_ids: set[str] = set()
    for match in SECTION_CLAIMS_RE.finditer(text):
        for token in re.split(r"[,\s]+", match.group("ids")):
            if token:
                claim_ids.add(token)
    return claim_ids


def is_concluding_section(section_path: Path) -> bool:
    stem = section_path.stem.lower()
    return any(marker in stem for marker in CONCLUDING_SECTION_MARKERS)


def validate_sections(brief: dict, section_paths: list[Path], require_coverage: bool) -> list[str]:
    errors: list[str] = []
    status_by_id = {claim["id"]: claim["status"] for claim in brief["claims"]}
    covered: set[str] = set()

    for section_path in section_paths:
        declared = extract_section_claims(section_path)
        covered |= declared

        orphans = sorted(declared - set(status_by_id))
        if orphans:
            errors.append(f"{section_path}: claims not in the brief: {', '.join(orphans)}")

        refuted = sorted(cid for cid in declared if status_by_id.get(cid) == "refuted")
        if refuted:
            errors.append(f"{section_path}: carries refuted claims: {', '.join(refuted)}")

        if is_concluding_section(section_path):
            assumed = sorted(cid for cid in declared if status_by_id.get(cid) == "assumed")
            if assumed:
                errors.append(
                    f"{section_path}: states assumed claims as findings: {', '.join(assumed)}"
                )

    if require_coverage:
        uncovered = sorted(
            claim_id
            for claim_id, status in status_by_id.items()
            if status != "refuted" and claim_id not in covered
        )
        if uncovered:
            errors.append(f"coverage: no section carries {', '.join(uncovered)}")

    return errors


def validate_all(
    brief_path: Path,
    section_paths: list[Path],
    required_slots: list[str],
    registry_path: Path | None,
    processed_dir: Path,
    require_coverage: bool,
) -> list[str]:
    brief = parse_brief(brief_path)
    errors = validate_narrative(brief, required_slots)
    errors.extend(validate_claims(brief))
    errors.extend(validate_evidence(brief, registry_path, processed_dir))
    errors.extend(validate_sections(brief, section_paths, require_coverage))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate docs/notes/story-brief.md")
    parser.add_argument("--brief", type=Path, default=DEFAULT_BRIEF_PATH)
    parser.add_argument(
        "--sections",
        nargs="*",
        type=Path,
        default=[],
        help="section markdown files whose claim declarations are cross-checked",
    )
    parser.add_argument(
        "--require-slots",
        default="",
        help="comma-separated narrative slots that must be filled at this stage "
        "(e.g. 'Context,Gap,Question' before lit-review; 'all' at polish-review)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="retrieved-sources registry used to resolve @key evidence",
    )
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument(
        "--require-coverage",
        action="store_true",
        help="every non-refuted claim must be carried by at least one section",
    )
    args = parser.parse_args()

    if args.require_slots.strip().lower() == "all":
        required_slots = list(NARRATIVE_SLOTS)
    else:
        required_slots = [slot.strip() for slot in args.require_slots.split(",") if slot.strip()]

    errors = validate_all(
        args.brief,
        args.sections,
        required_slots,
        args.registry,
        args.processed_dir,
        args.require_coverage,
    )

    if errors:
        print("story-brief.md validation errors:")
        for error in errors:
            print(f"  {error}")
        return 1

    print("story-brief.md is consistent with the sections.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
