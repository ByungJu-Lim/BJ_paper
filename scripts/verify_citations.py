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
