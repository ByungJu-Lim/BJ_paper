"""Validate source provenance, resolve DOIs, and screen for retractions.

Verification layers, in order:
1. Structural  - required fields, URL scheme, date sanity, source_type vocabulary.
2. Resolution  - the DOI must resolve against Crossref, falling back to DataCite
                 for DOIs registered there (arXiv preprints, Zenodo datasets).
3. Integrity   - the resolved title must match, and the work must not be retracted
                 or under an expression of concern.
"""
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
    "preprint",
    "report",
    "dataset",
    "standard",
    "web",
}
# Source types that are not trustworthy as citations without a resolvable DOI.
DOI_SOURCE_TYPES = {"journal-article", "conference-paper", "preprint"}
# update-to types that make a source unsafe to cite without explicit acknowledgement.
BLOCKING_UPDATE_TYPES = {
    "retraction",
    "withdrawal",
    "removal",
    "expression_of_concern",
}
DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
TITLE_SIMILARITY_THRESHOLD = 0.9
USER_AGENT = "paper-agent-source-verifier/2.0"


def normalize_doi(value: str) -> str:
    return DOI_PREFIX_RE.sub("", value.strip()).lower()


def normalize_title(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


def _user_agent(mailto: str | None) -> str:
    return f"{USER_AGENT} (mailto:{mailto})" if mailto else USER_AGENT


def _get_json(url: str, mailto: str | None = None) -> dict:
    """GET with retry on 429/5xx, which both Crossref and DataCite use for throttling."""
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": _user_agent(mailto)},
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise
            if attempt == 2:
                raise
        except URLError:
            if attempt == 2:
                raise
        time.sleep(2**attempt)
    raise RuntimeError("metadata request failed")


def fetch_crossref_metadata(doi: str, mailto: str | None = None) -> dict:
    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    return _get_json(url, mailto)["message"]


def fetch_datacite_metadata(doi: str, mailto: str | None = None) -> dict:
    """Resolve a DataCite-registered DOI (arXiv, Zenodo) into Crossref-shaped metadata."""
    url = f"https://api.datacite.org/dois/{quote(doi, safe='')}"
    attributes = _get_json(url, mailto)["data"]["attributes"]
    titles = [t.get("title", "") for t in attributes.get("titles", []) if t.get("title")]
    return {"DOI": attributes.get("doi", ""), "title": titles}


def fetch_update_notices(doi: str, mailto: str | None = None) -> list[dict]:
    """Return Crossref update notices (retraction, correction, ...) targeting this DOI.

    Crossref records an update on the *notice* record, not on the work being
    retracted, so this is a filter query rather than a direct fetch. Retraction
    Watch data is merged into this feed and appears with source 'retraction-watch'.
    """
    url = (
        "https://api.crossref.org/works"
        f"?filter=updates:{quote(doi, safe='')}&select=DOI,update-to&rows=20"
    )
    items = _get_json(url, mailto)["message"].get("items", [])
    notices: list[dict] = []
    for item in items:
        for update in item.get("update-to") or []:
            if normalize_doi(str(update.get("DOI", ""))) == doi:
                notices.append(
                    {
                        "type": str(update.get("type", "")).strip().lower(),
                        "notice_doi": item.get("DOI", ""),
                        "source": update.get("source", ""),
                    }
                )
    return notices


def _resolve_doi(
    doi: str,
    fetch_crossref: Callable[[str], dict],
    fetch_datacite: Callable[[str], dict],
) -> tuple[dict, str]:
    """Resolve a DOI via Crossref, falling back to DataCite when it is registered there."""
    try:
        return fetch_crossref(doi), "Crossref"
    except HTTPError as exc:
        if exc.code != 404:
            raise
    return fetch_datacite(doi), "DataCite"


def _check_metadata(label: str, title: str, doi: str, metadata: dict, agency: str) -> list[str]:
    errors: list[str] = []
    resolved_doi = normalize_doi(str(metadata.get("DOI", "")))
    titles = metadata.get("title") or []
    resolved_title = titles[0] if titles else ""

    if resolved_doi != doi:
        errors.append(f"{label}: DOI does not match {agency} metadata")

    similarity = SequenceMatcher(
        None, normalize_title(title), normalize_title(resolved_title)
    ).ratio()
    if not resolved_title or similarity < TITLE_SIMILARITY_THRESHOLD:
        errors.append(f"{label}: title does not match {agency} metadata")
    return errors


def validate_registry(
    registry_path: Path,
    online: bool = False,
    fetch_crossref: Callable[[str], dict] | None = None,
    fetch_datacite: Callable[[str], dict] | None = None,
    fetch_updates: Callable[[str], list[dict]] | None = None,
    today: date | None = None,
) -> list[str]:
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"registry cannot be read: {exc}"]

    if not isinstance(data, list):
        return ["registry root must be a JSON array"]

    errors: list[str] = []
    seen_keys: set[str] = set()
    crossref = fetch_crossref or fetch_crossref_metadata
    datacite = fetch_datacite or fetch_datacite_metadata
    updates = fetch_updates or fetch_update_notices
    current_day = today or date.today()

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
            if date.fromisoformat(retrieved_at) > current_day:
                errors.append(f"{label}: retrieved_at is in the future")
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

        if not (online and doi and isinstance(title, str) and title.strip()):
            continue

        try:
            metadata, agency = _resolve_doi(doi, crossref, datacite)
        except HTTPError as exc:
            if exc.code == 404:
                errors.append(f"{label}: DOI not found in Crossref or DataCite")
            else:
                errors.append(f"{label}: DOI resolution failed: {exc}")
            continue
        except (URLError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{label}: DOI resolution failed: {exc}")
            continue

        errors.extend(_check_metadata(label, title, doi, metadata, agency))

        try:
            notices = updates(doi)
        except (HTTPError, URLError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{label}: retraction screening failed: {exc}")
            continue

        blocking = sorted({n["type"] for n in notices if n["type"] in BLOCKING_UPDATE_TYPES})
        acknowledged = entry.get("retraction_ack")
        if blocking and not (isinstance(acknowledged, str) and acknowledged.strip()):
            errors.append(
                f"{label}: flagged as {', '.join(blocking)} - do not cite as a valid "
                "result; set 'retraction_ack' with a reason to cite it deliberately"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the retrieved-sources registry.")
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument(
        "--online",
        action="store_true",
        help="Resolve DOIs (Crossref, DataCite) and screen for retractions",
    )
    parser.add_argument("--mailto", help="Contact email for the Crossref polite pool")
    args = parser.parse_args()

    kwargs: dict = {}
    if args.online:
        kwargs = {
            "fetch_crossref": lambda doi: fetch_crossref_metadata(doi, args.mailto),
            "fetch_datacite": lambda doi: fetch_datacite_metadata(doi, args.mailto),
            "fetch_updates": lambda doi: fetch_update_notices(doi, args.mailto),
        }
    errors = validate_registry(args.registry, online=args.online, **kwargs)
    if not errors:
        mode = "including DOI resolution and retraction screening" if args.online else "structurally"
        print(f"Source registry verified {mode}.")
        return 0

    print("Source registry validation errors:")
    for error in errors:
        print(f"  {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
