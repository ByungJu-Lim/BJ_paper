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
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote

if __package__:
    from .validation_common import (expand_paths, is_concluding_section, outline_roles_by_file,
                                    visible_markdown)
    from .check_paper_state import parse_stages, validate_all as validate_state
else:
    from validation_common import (expand_paths, is_concluding_section, outline_roles_by_file,
                                   visible_markdown)
    from check_paper_state import parse_stages, validate_all as validate_state

DEFAULT_BRIEF_PATH = Path("docs/notes/story-brief.md")
DEFAULT_PROCESSED_DIR = Path("data/processed")
DEFAULT_OUTLINE_PATH = Path("docs/outline.md")

NARRATIVE_SLOTS = ("Context", "Gap", "Question", "Approach", "Finding", "Implication")
CLAIM_STATUSES = ("assumed", "supported", "refuted")

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
        elif (status in {"supported", "refuted"} or not is_placeholder(claim["claim"])) and is_placeholder(falsifier):
            errors.append(f"{claim_id}: status '{status}' requires a written falsifier")

    unknown_falsifiers = sorted(set(brief["falsifiers"]) - seen)
    if unknown_falsifiers:
        errors.append(f"falsifiers: no such claim: {', '.join(unknown_falsifiers)}")

    return errors


def _registry_keys(registry_path: Path) -> set[str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("retrieved-sources registry must be a JSON array")
    keys: set[str] = set()
    for entry in data:
        if not isinstance(entry, dict) or not isinstance(entry.get('key'), str) or not entry['key'].strip():
            raise ValueError('source registry entries must contain nonempty keys')
        if entry['key'] in keys:
            raise ValueError(f"duplicate registry key: {entry['key']}")
        keys.add(entry['key'])
    return keys


def _project_file(value: object, root: Path) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    windows = PureWindowsPath(value)
    if path.is_absolute() or windows.is_absolute() or windows.drive or '..' in windows.parts:
        return None
    resolved = (root / path).resolve()
    return resolved if resolved.is_relative_to(root.resolve()) and resolved.is_file() else None


def validate_manifest(manifest: Path, run_id: str, root: Path, processed_dir: Path) -> list[str]:
    """Resolve reproducibility fields without executing the recorded command."""
    if not manifest.is_file():
        return [f"run:{run_id} has no manifest at {manifest}"]
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return [f"{manifest}: invalid manifest: {exc}"]
    if not isinstance(data, dict):
        return [f"{manifest}: manifest must be an object"]
    errors: list[str] = []
    if data.get('run_id') != run_id:
        errors.append(f"{manifest}: run_id must equal {run_id}")
    script = _project_file(data.get('script'), root)
    if script is None or not script.is_relative_to((root / 'code').resolve()):
        errors.append(f"{manifest}: script must name an existing file under code/")
    for field in ('command', 'python_version'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"{manifest}: {field} must be a nonempty string")
    if 'random_seed' not in data or (data['random_seed'] is not None and type(data['random_seed']) is not int):
        errors.append(f"{manifest}: random_seed must be an integer or null")
    dependencies = data.get('dependencies')
    if not isinstance(dependencies, dict) or not all(
        isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
        for k, v in dependencies.items()
    ):
        errors.append(f"{manifest}: dependencies must map package names to versions")
    for field in ('inputs', 'outputs'):
        values = data.get(field)
        if not isinstance(values, list) or not values:
            errors.append(f"{manifest}: {field} must be a nonempty list of project files")
            continue
        for value in values:
            path = _project_file(value, root)
            if path is None:
                errors.append(f"{manifest}: {field} file missing or outside project: {value}")
            elif field == 'outputs' and (not path.is_relative_to(processed_dir.resolve()) or path == manifest.resolve()):
                errors.append(f"{manifest}: output must be a result file under data/processed/: {value}")
    return errors


def _figure_id(text: str) -> str:
    match = re.match(r'^(Fig\.?|Figure|Table|Tab\.?)\s*(\d+[a-z]?)', text, re.IGNORECASE)
    assert match
    kind = 'table' if match.group(1).lower().startswith('tab') else 'figure'
    return f'{kind} {match.group(2).lower()}'


def _rendered_evidence(section_paths: list[Path], root: Path) -> tuple[set[str], list[str]]:
    """A caption must be followed by a local image or a Markdown table."""
    found: set[str] = set()
    errors: list[str] = []
    for section in section_paths:
        lines = [line.strip() for line in visible_markdown(section.read_text(encoding='utf-8')).splitlines() if line.strip()]
        for index, line in enumerate(lines):
            caption = re.match(r'^(?:Fig\.?|Figure|Table|Tab\.?)\s*\d+[a-z]?[.:]\s+\S', line, re.IGNORECASE)
            if not caption:
                continue
            label = _figure_id(line)
            following = lines[index + 1: index + 4]
            valid = False
            if label.startswith('figure') and following:
                image = re.fullmatch(r'!\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+"[^"]*")?\)', following[0])
                if image:
                    value = unquote(image.group(1) or image.group(2))
                    target = (section.parent / value).resolve()
                    valid = target.is_relative_to(root.resolve()) and target.is_file() and target.stat().st_size > 0
            elif label.startswith('table') and len(following) == 3:
                valid = following[0].startswith('|') and bool(TABLE_DIVIDER_RE.fullmatch(following[1])) and following[2].startswith('|')
            if valid:
                if label in found:
                    errors.append(f'{section}: duplicate evidence caption {label}')
                found.add(label)
    return found, errors


def validate_evidence(brief: dict, registry_path: Path | None, processed_dir: Path,
                      section_paths: list[Path] | None = None, project_root: Path | None = None) -> list[str]:
    """Invariant D: every evidence entry names something that actually exists."""
    errors: list[str] = []
    root = (project_root or Path.cwd()).resolve()
    keys: set[str] = set()
    if registry_path is not None:
        try:
            keys = _registry_keys(registry_path)
        except (OSError, ValueError) as exc:
            errors.append(f"source registry cannot be read: {exc}")
    rendered, figure_errors = _rendered_evidence(section_paths or [], root)
    errors.extend(figure_errors)

    for claim in brief["claims"]:
        for entry in parse_evidence(claim["evidence"]):
            source_match = SOURCE_EVIDENCE_RE.match(entry)
            if source_match:
                key = source_match.group("key")
                if key not in keys:
                    errors.append(f"{claim['id']}: evidence '@{key}' is not in the source registry")
                continue

            run_match = RUN_EVIDENCE_RE.match(entry)
            if run_match:
                manifest = processed_dir / f"{run_match.group('run_id')}.manifest.json"
                errors.extend(f"{claim['id']}: {error}" for error in validate_manifest(manifest, run_match.group('run_id'), root, processed_dir))
                continue

            if FIGURE_EVIDENCE_RE.match(entry):
                if _figure_id(entry) not in rendered:
                    errors.append(f"{claim['id']}: evidence '{entry}' has no rendered figure/table with a caption in the sections")
                continue

            errors.append(
                f"{claim['id']}: unrecognised evidence '{entry}' "
                "(expected @key, run:<run-id>, or Fig./Table N)"
            )

    return errors


def extract_section_claims(section_path: Path) -> set[str]:
    text = visible_markdown(section_path.read_text(encoding="utf-8"), keep_comments=True)
    claim_ids: set[str] = set()
    for match in SECTION_CLAIMS_RE.finditer(text):
        for token in re.split(r"[,\s]+", match.group("ids")):
            if token:
                claim_ids.add(token)
    return claim_ids


def validate_sections(brief: dict, section_paths: list[Path], require_coverage: bool,
                      outline_roles: dict[str, str] | None = None) -> list[str]:
    errors: list[str] = []
    status_by_id = {claim["id"]: claim["status"] for claim in brief["claims"]}
    covered: set[str] = set()

    for section_path in section_paths:
        text = section_path.read_text(encoding='utf-8')
        declarations = list(SECTION_CLAIMS_RE.finditer(visible_markdown(text, keep_comments=True)))
        content = [line.strip() for line in visible_markdown(text).splitlines()
                   if line.strip() and not line.lstrip().startswith('#')]
        scaffold = not content
        declared = extract_section_claims(section_path)
        if (not scaffold or require_coverage) and (len(declarations) != 1 or not declared):
            errors.append(f'{section_path}: written sections require exactly one nonempty claims declaration')
        if require_coverage and scaffold:
            errors.append(f'{section_path}: final sections must contain manuscript prose')
        covered |= declared

        orphans = sorted(declared - set(status_by_id))
        if orphans:
            errors.append(f"{section_path}: claims not in the brief: {', '.join(orphans)}")

        refuted = sorted(cid for cid in declared if status_by_id.get(cid) == "refuted")
        if refuted:
            errors.append(f"{section_path}: carries refuted claims: {', '.join(refuted)}")

        if is_concluding_section(section_path, outline_roles):
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
    outline_path: Path | None = None,
) -> list[str]:
    brief = parse_brief(brief_path)
    errors = validate_narrative(brief, required_slots)
    errors.extend(validate_claims(brief))
    if required_slots and (not brief['claims'] or any(is_placeholder(c['claim']) for c in brief['claims'])):
        errors.append('claims: required research stage must contain written claims, not placeholders')
    errors.extend(validate_evidence(brief, registry_path, processed_dir, section_paths))
    outline_roles = outline_roles_by_file(outline_path) if outline_path else {}
    errors.extend(validate_sections(brief, section_paths, require_coverage, outline_roles))
    if not is_placeholder(dict(brief['slots']).get('Finding', '')):
        if not any(RUN_EVIDENCE_RE.fullmatch(entry) for c in brief['claims'] for entry in parse_evidence(c['evidence'])):
            errors.append('Finding: a written result requires run:<run-id> evidence in the claims ledger')
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
    parser.add_argument("--outline", type=Path, default=DEFAULT_OUTLINE_PATH,
                        help="docs/outline.md, whose Sections table assigns each "
                             "section file its role (front-matter or concluding)")
    parser.add_argument('--state', type=Path, help='Derive artifact requirements from workflow review/approval state')
    parser.add_argument('--check-manifests', action='store_true', help='Require and validate all processed run manifests')
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

    try:
        if args.state:
            state_errors = validate_state(args.state)
            if state_errors:
                raise ValueError('invalid workflow state: ' + '; '.join(e for group in state_errors.values() for e in group))
            completed = {s['id'] for s in parse_stages(args.state) if s['status'] in {'approved', 'awaiting-user'}}
            if 'story-brief' in completed:
                required_slots = list(dict.fromkeys(required_slots + ['Context', 'Gap', 'Question']))
            if 'outline-draft' in completed:
                required_slots = list(dict.fromkeys(required_slots + ['Approach']))
            if 'results-discussion' in completed:
                required_slots = list(NARRATIVE_SLOTS)
            if 'code-experiment' in completed:
                args.check_manifests = True
            if 'polish-review' in completed:
                required_slots = list(NARRATIVE_SLOTS)
                args.require_coverage = True
        sections = expand_paths(args.sections)
        if args.require_coverage and not sections:
            raise ValueError('final coverage requires section files')
        errors = validate_all(args.brief, sections, required_slots,
                              args.registry, args.processed_dir, args.require_coverage,
                              args.outline)
        if args.check_manifests:
            manifests = sorted(args.processed_dir.glob('*.manifest.json'))
            if not manifests:
                errors.append('code-experiment: at least one run manifest is required')
            for manifest in manifests:
                errors.extend(validate_manifest(manifest, manifest.name.removesuffix('.manifest.json'), Path.cwd(), args.processed_dir))
    except (OSError, ValueError) as exc:
        errors = [str(exc)]

    if errors:
        print("story-brief.md validation errors:")
        for error in errors:
            print(f"  {error}")
        return 1

    print("story-brief.md is consistent with the sections.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
