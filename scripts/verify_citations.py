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

DEFAULT_BIB_PATH = Path("refs/references.bib")


def extract_registry_keys(registry_path: Path) -> set[str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("retrieved-sources registry must be a JSON array")

    keys: set[str] = set()
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"registry entry {index} must be a JSON object")
        key = entry.get("key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"registry entry {index} has no valid key")
        if key in keys:
            raise ValueError(f"duplicate registry key: {key}")
        keys.add(key)
    return keys


def extract_bibtex_keys(bib_path: Path) -> set[str]:
    text = bib_path.read_text(encoding="utf-8")
    return set(re.findall(r"@\w+\{\s*([^,\s]+)\s*,", text))


def extract_citation_keys_from_markdown(md_path: Path) -> set[str]:
    text = md_path.read_text(encoding="utf-8")
    keys: set[str] = set()
    for bracket_contents in re.findall(r"\[([^\]]+)\]", text):
        if "@" not in bracket_contents:
            continue
        for match in re.finditer(r"(?:^|[\s;])-?@([^\s,;\]]+)", bracket_contents):
            keys.add(match.group(1))
    return keys


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify citations against the retrieved-sources registry and bibliography."
    )
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--sections", required=True, nargs="+", type=Path)
    parser.add_argument(
        "--bib",
        type=Path,
        default=DEFAULT_BIB_PATH,
        help="BibTeX file to audit (default: refs/references.bib; skipped if absent)",
    )
    args = parser.parse_args()

    failed = False

    unverified = find_unverified_citations(args.sections, args.registry)
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

        dangling = find_citations_missing_from_bib(args.sections, args.bib)
        if dangling:
            _print_section_report(f"Citations with no entry in {args.bib}:", dangling)
            failed = True
    else:
        print(f"Note: {args.bib} not found - bibliography checks skipped.")

    if failed:
        return 1

    print("All citations verified against registry and bibliography.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
