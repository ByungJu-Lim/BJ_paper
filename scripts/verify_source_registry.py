"""Validate source provenance and optionally verify DOI metadata with Crossref."""
import argparse
import json
import re
import time
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

ALLOWED_SOURCE_TYPES = {
    "journal-article",
    "conference-paper",
    "report",
    "dataset",
    "standard",
    "web",
}
DOI_SOURCE_TYPES = {"journal-article", "conference-paper"}
DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)


def normalize_doi(value: str) -> str:
    return DOI_PREFIX_RE.sub("", value.strip()).lower()


def normalize_title(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


def fetch_crossref_metadata(doi: str, mailto: str | None = None) -> dict:
    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    user_agent = "AITOP-source-verifier/1.0"
    if mailto:
        user_agent += f" (mailto:{mailto})"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": user_agent})

    for attempt in range(3):
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.load(response)
            return payload["message"]
        except HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise
            if attempt == 2:
                raise
        except URLError:
            if attempt == 2:
                raise
        time.sleep(2**attempt)
    raise RuntimeError("Crossref request failed")


def validate_registry(
    registry_path: Path,
    online: bool = False,
    fetch_crossref: Callable[[str], dict] | None = None,
) -> list[str]:
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"registry cannot be read: {exc}"]

    if not isinstance(data, list):
        return ["registry root must be a JSON array"]

    errors: list[str] = []
    seen_keys: set[str] = set()
    fetcher = fetch_crossref or fetch_crossref_metadata

    for index, entry in enumerate(data):
        label = f"entry {index}"
        if not isinstance(entry, dict):
            errors.append(f"{label}: must be a JSON object")
            continue

        key = entry.get("key")
        if not isinstance(key, str) or not key.strip():
            errors.append(f"{label}: key must be a non-empty string")
        elif key in seen_keys:
            errors.append(f"{label}: duplicate key '{key}'")
        else:
            seen_keys.add(key)
            label = f"entry '{key}'"

        title = entry.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{label}: title must be a non-empty string")

        url = entry.get("url")
        parsed_url = urlparse(url) if isinstance(url, str) else None
        if parsed_url is None or parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            errors.append(f"{label}: URL must use http or https")

        retrieved_at = entry.get("retrieved_at")
        try:
            date.fromisoformat(retrieved_at)
        except (TypeError, ValueError):
            errors.append(f"{label}: retrieved_at must use YYYY-MM-DD")

        source_type = entry.get("source_type")
        if source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{label}: invalid source_type '{source_type}'")

        raw_doi = entry.get("doi")
        doi = normalize_doi(raw_doi) if isinstance(raw_doi, str) else ""
        if source_type in DOI_SOURCE_TYPES and not doi:
            errors.append(f"{label}: {source_type} requires a DOI")
            continue

        if online and doi and isinstance(title, str) and title.strip():
            try:
                metadata = fetcher(doi)
                crossref_doi = normalize_doi(str(metadata.get("DOI", "")))
                crossref_titles = metadata.get("title") or []
                crossref_title = crossref_titles[0] if crossref_titles else ""
                similarity = SequenceMatcher(
                    None,
                    normalize_title(title),
                    normalize_title(crossref_title),
                ).ratio()
                if crossref_doi != doi:
                    errors.append(f"{label}: DOI does not match Crossref metadata")
                if not crossref_title or similarity < 0.9:
                    errors.append(f"{label}: title does not match Crossref metadata")
            except (HTTPError, URLError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"{label}: Crossref verification failed: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the retrieved-sources registry.")
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--online", action="store_true", help="Verify DOI metadata with Crossref")
    parser.add_argument("--mailto", help="Contact email for the Crossref polite pool")
    args = parser.parse_args()

    fetcher = None
    if args.online:
        fetcher = lambda doi: fetch_crossref_metadata(doi, args.mailto)
    errors = validate_registry(args.registry, online=args.online, fetch_crossref=fetcher)
    if not errors:
        mode = "including Crossref metadata" if args.online else "structurally"
        print(f"Source registry verified {mode}.")
        return 0

    print("Source registry validation errors:")
    for error in errors:
        print(f"  {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
