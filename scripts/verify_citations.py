"""Cross-check citations used in section drafts against the retrieved-sources registry."""
import json
import re
from pathlib import Path


def extract_registry_keys(registry_path: Path) -> set[str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return {entry["key"] for entry in data}


def extract_bibtex_keys(bib_path: Path) -> set[str]:
    text = bib_path.read_text(encoding="utf-8")
    return set(re.findall(r"@\w+\{\s*([^,\s]+)\s*,", text))


def extract_citation_keys_from_markdown(md_path: Path) -> set[str]:
    text = md_path.read_text(encoding="utf-8")
    keys: set[str] = set()
    for bracket_contents in re.findall(r"\[([^\]]+)\]", text):
        if "@" not in bracket_contents:
            continue
        for token in bracket_contents.split(";"):
            token = token.strip()
            if token.startswith("@"):
                keys.add(token[1:].strip())
    return keys


def find_unverified_citations(section_paths: list[Path], registry_path: Path) -> dict[str, list[str]]:
    registry_keys = extract_registry_keys(registry_path)
    report: dict[str, list[str]] = {}
    for section_path in section_paths:
        used_keys = extract_citation_keys_from_markdown(section_path)
        unverified = sorted(used_keys - registry_keys)
        if unverified:
            report[str(section_path)] = unverified
    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Verify citations against the retrieved-sources registry.")
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--sections", required=True, nargs="+", type=Path)
    args = parser.parse_args()

    report = find_unverified_citations(args.sections, args.registry)
    if not report:
        print("All citations verified against registry.")
        return 0

    print("Unverified citations found (not in retrieved-sources registry):")
    for path, keys in report.items():
        print(f"  {path}: {', '.join(keys)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
