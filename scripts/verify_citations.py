"""Cross-check citations, the bibliography, and the retrieved-sources registry.

Three invariants keep fabricated references out of the paper:

A. every citation key used in a section is registered      (no invented citations)
B. every BibTeX entry is registered                        (no hand-added bibliography)
C. every citation key used in a section has a BibTeX entry (no dangling citations)

A alone is not enough: without B, an agent or a human can append a plausible-looking
entry straight to refs/references.bib and nothing would notice.
"""
import argparse
import json
import re
from pathlib import Path

try:
    from .validation_common import expand_paths, visible_markdown
    from .verify_source_registry import author_names
    from .check_paper_state import parse_stages, validate_all as validate_state
except ImportError:  # pragma: no cover - script execution path
    from validation_common import expand_paths, visible_markdown
    from verify_source_registry import author_names
    from check_paper_state import parse_stages, validate_all as validate_state

DEFAULT_BIB_PATH = Path("refs/references.bib")
CITATION_KEY_RE = re.compile(r"(?<![\\\w])-?@([A-Za-z0-9][A-Za-z0-9_:+?<>/~%-]*)")
BIB_ENTRY_RE = re.compile(r"@(\w+)\s*\{")
BIB_FIELD_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|[^,\n]+)",
    re.DOTALL,
)


def extract_registry_keys(registry_path: Path) -> set[str]:
    return set(extract_registry_entries(registry_path))


def extract_registry_entries(registry_path: Path) -> dict[str, dict]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("retrieved-sources registry must be a JSON array")

    entries: dict[str, dict] = {}
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"registry entry {index} must be a JSON object")
        key = entry.get("key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"registry entry {index} has no valid key")
        if key in entries:
            raise ValueError(f"duplicate registry key: {key}")
        entries[key] = entry
    return entries


def extract_bibtex_keys(bib_path: Path) -> set[str]:
    return set(extract_bibtex_entries(bib_path))


def _strip_bib_value(value: str) -> str:
    value = value.strip().rstrip(",").strip()
    while len(value) >= 2 and (
        (value[0] == "{" and value[-1] == "}") or (value[0] == '"' and value[-1] == '"')
    ):
        value = value[1:-1].strip()
    return re.sub(r"\s+", " ", value)


def extract_bibtex_entries(bib_path: Path) -> dict[str, dict[str, str]]:
    text = re.sub(r"(?<!\\)%[^\n]*", "", bib_path.read_text(encoding="utf-8"))
    entries: dict[str, dict[str, str]] = {}
    position = 0
    while match := BIB_ENTRY_RE.search(text, position):
        start = match.end()
        depth = 1
        quoted = False
        escaped = False
        end = start
        while end < len(text) and depth:
            char = text[end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"' and depth == 1:
                quoted = not quoted
            elif not quoted:
                depth += (char == "{") - (char == "}")
            end += 1
        if depth:
            raise ValueError("unterminated BibTeX entry")
        position = end
        if match.group(1).casefold() in {"comment", "preamble", "string"}:
            continue
        contents = text[start:end - 1]
        if "," not in contents:
            raise ValueError("BibTeX entry has no key/field separator")
        key, body = contents.split(",", 1)
        key = key.strip()
        if not key or re.search(r"\s", key):
            raise ValueError("invalid BibTeX key")
        fields = {
            field_match.group(1).casefold(): _strip_bib_value(field_match.group(2))
            for field_match in BIB_FIELD_RE.finditer(body)
        }
        if key in entries:
            raise ValueError(f"duplicate bibliography key: {key}")
        entries[key] = fields
    return entries


def extract_citation_keys_from_markdown(md_path: Path) -> set[str]:
    """Extract the supported citation key subset from visible Markdown.

    Supported keys start with an ASCII letter or digit and may continue with
    letters, digits, underscore, hyphen, colon, plus, question mark, angle
    brackets, slash, tilde, or percent. Fenced code, inline code, HTML comments,
    escaped at-signs, and email addresses are ignored.
    """
    text = visible_markdown(md_path.read_text(encoding="utf-8"))
    return {match.group(1) for match in CITATION_KEY_RE.finditer(text)}


def find_unverified_citations(section_paths: list[Path], registry_path: Path) -> dict[str, list[str]]:
    """Invariant A: section citations that are absent from the registry."""
    registry_keys = extract_registry_keys(registry_path)
    report: dict[str, list[str]] = {}
    for section_path in section_paths:
        used_keys = extract_citation_keys_from_markdown(section_path)
        unverified = sorted(used_keys - registry_keys)
        if unverified:
            report[str(section_path)] = unverified
    return report


def find_unregistered_bib_entries(bib_path: Path, registry_path: Path) -> list[str]:
    """Invariant B: BibTeX entries that were never registered as retrieved sources."""
    return sorted(extract_bibtex_keys(bib_path) - extract_registry_keys(registry_path))


def _normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


def _normalize_doi(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I).lower()


def find_bibliography_metadata_mismatches(bib_path: Path, registry_path: Path) -> list[str]:
    """Reject BibTeX entries whose core fields no longer match the registry."""
    registry = extract_registry_entries(registry_path)
    bib_entries = extract_bibtex_entries(bib_path)
    errors: list[str] = []

    for key in sorted(set(bib_entries) & set(registry)):
        bib = bib_entries[key]
        entry = registry[key]

        required = ["title", "author", "year"]
        if entry.get("doi"):
            required.append("doi")
        for field in required:
            if not bib.get(field):
                errors.append(f"{key}: BibTeX missing required {field}")
        venue = bib.get("journal") or bib.get("booktitle") or bib.get("publisher") or bib.get("institution")
        if entry.get("venue") and _normalize_text(venue) != _normalize_text(entry["venue"]):
            errors.append(f"{key}: BibTeX venue differs from registry venue or is missing")

        if "title" in bib and _normalize_text(bib["title"]) != _normalize_text(entry.get("title")):
            errors.append(f"{key}: BibTeX title differs from registry title")

        registry_doi = _normalize_doi(entry.get("doi"))
        if "doi" in bib and registry_doi and _normalize_doi(bib["doi"]) != registry_doi:
            errors.append(f"{key}: BibTeX DOI differs from registry DOI")

        registry_year = entry.get("year")
        if "year" in bib and isinstance(registry_year, int):
            try:
                bib_year = int(bib["year"])
            except ValueError:
                errors.append(f"{key}: BibTeX year is not an integer")
            else:
                if bib_year != registry_year:
                    errors.append(f"{key}: BibTeX year differs from registry year")

        registry_authors = author_names(entry.get("authors"))
        bib_authors = author_names(re.split(r"\s+and\s+", bib.get("author", "")))
        if bib_authors and registry_authors and bib_authors != registry_authors:
            errors.append(f"{key}: BibTeX authors differ from registry authors")

    return errors


def find_citations_missing_from_bib(
    section_paths: list[Path], bib_path: Path
) -> dict[str, list[str]]:
    """Invariant C: section citations with no matching BibTeX entry."""
    bib_keys = extract_bibtex_keys(bib_path)
    report: dict[str, list[str]] = {}
    for section_path in section_paths:
        missing = sorted(extract_citation_keys_from_markdown(section_path) - bib_keys)
        if missing:
            report[str(section_path)] = missing
    return report


def _print_section_report(header: str, report: dict[str, list[str]]) -> None:
    print(header)
    for path, keys in report.items():
        print(f"  {path}: {', '.join(keys)}")


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify citations against the retrieved-sources registry and bibliography."
    )
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--sections", required=True, nargs="+", type=Path)
    parser.add_argument('--state', type=Path, help='Allow bibliography to be incomplete before citation review; key and existing metadata checks always run')
    parser.add_argument(
        "--bib",
        type=Path,
        default=DEFAULT_BIB_PATH,
        help="BibTeX file to audit (default: refs/references.bib; skipped if absent)",
    )
    args = parser.parse_args()
    require_bibliography = True
    if args.state:
        state_errors = validate_state(args.state)
        if state_errors:
            raise ValueError('invalid workflow state: ' + '; '.join(e for group in state_errors.values() for e in group))
        citation = next(s for s in parse_stages(args.state) if s['id'] == 'citation-manage')
        require_bibliography = citation['status'] in {'awaiting-review', 'awaiting-user', 'approved'}

    try:
        section_paths = expand_paths(args.sections)
    except ValueError as exc:
        print(f"Section path error: {exc}")
        return 1

    failed = False

    unverified = find_unverified_citations(section_paths, args.registry)
    if unverified:
        _print_section_report(
            "Unverified citations (not in retrieved-sources registry):", unverified
        )
        failed = True

    if args.bib.exists():
        unregistered = find_unregistered_bib_entries(args.bib, args.registry)
        if unregistered:
            print("Unregistered bibliography entries (not in retrieved-sources registry):")
            print(f"  {args.bib}: {', '.join(unregistered)}")
            failed = True

        dangling = find_citations_missing_from_bib(section_paths, args.bib) if require_bibliography else {}
        if dangling:
            _print_section_report(f"Citations with no entry in {args.bib}:", dangling)
            failed = True

        mismatches = find_bibliography_metadata_mismatches(args.bib, args.registry)
        if mismatches:
            print("Bibliography metadata mismatches:")
            for mismatch in mismatches:
                print(f"  {mismatch}")
            failed = True
    else:
        if require_bibliography and any(extract_citation_keys_from_markdown(path) for path in section_paths):
            print(f"Bibliography missing: {args.bib}; cited sources require BibTeX entries.")
            failed = True
        else:
            print(f"Note: {args.bib} not found; no citations require bibliography entries.")

    if failed:
        return 1

    if require_bibliography:
        print("All citations verified against registry and bibliography.")
    else:
        print('Draft citations and existing bibliography verified; bibliography completeness is deferred until citation review.')
    return 0


def main() -> int:
    try:
        return _main()
    except (OSError, ValueError) as exc:
        print(f"Citation validation error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
