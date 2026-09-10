"""Validate source provenance, resolve DOIs, and screen for retractions.

Verification layers, in order:
1. Structural  - required fields, URL scheme, date sanity, source_type vocabulary.
2. Resolution  - the DOI must resolve against Crossref, falling back to DataCite
                 for DOIs registered there (arXiv preprints, Zenodo datasets).
3. Integrity   - the resolved title must match, and the work must not be retracted
                 or under an expression of concern.
"""
import argparse
import html
import json
import re
import time
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
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
VENUE_SOURCE_TYPES = {"journal-article", "conference-paper", "preprint"}
# update-to types that make a source unsafe to cite without explicit acknowledgement.
BLOCKING_UPDATE_TYPES = {
    "retraction",
    "withdrawal",
    "removal",
    "expression_of_concern",
}

# How much of the source was actually read. Citing a paper for a method or a
# number that appears only in its full text, having read only the abstract, is
# how a citation ends up misrepresenting what the paper says.
FULL_TEXT_ACCESS = "full-text"
ABSTRACT_ONLY_ACCESS = "abstract-only"
AWAITING_USER_FILE_ACCESS = "awaiting-user-file"
ALLOWED_ACCESS_LEVELS = {FULL_TEXT_ACCESS, ABSTRACT_ONLY_ACCESS, AWAITING_USER_FILE_ACCESS}

DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
# Crossref marks a retracted article by prefixing its title. Publishers also mint
# duplicate DOIs for the same article, and those duplicates carry neither the
# prefix nor the retraction notice - so the marker has to be looked for across
# every record sharing the title, not just the DOI in hand.
RETRACTION_TITLE_RE = re.compile(
    r"^\s*(?:retracted|withdrawn|retraction)\s*[:—–-]\s*", re.IGNORECASE
)
TITLE_SIMILARITY_THRESHOLD = 0.9
USER_AGENT = "paper-agent-source-verifier/2.0"


def normalize_doi(value: str) -> str:
    return DOI_PREFIX_RE.sub("", value.strip()).lower()


def normalize_title(value: str) -> str:
    """Crossref returns HTML-escaped text ("Computers &amp; Chemical Engineering"),
    so unescape before stripping punctuation: otherwise "&amp;" survives as the word
    "amp" and never matches a registry entry spelled with a literal ampersand."""
    return " ".join(re.sub(r"[^\w]+", " ", html.unescape(value).casefold()).split())


def normalize_update_type(value: str) -> str:
    return re.sub(r"[\s_-]+", "_", value.strip().casefold())


def normalize_author_name(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


def author_names(authors: object) -> list[str]:
    """Canonicalize full names, including family-first metadata and Unicode."""
    if not isinstance(authors, list):
        return []
    names = []
    for author in authors:
        if not isinstance(author, str) or not author.strip():
            continue
        if "," in author:
            family, given = author.split(",", 1)
            author = given + " " + family
        names.append(normalize_author_name(author))
    return names


def _metadata_authors(metadata: dict) -> list[str]:
    names: list[str] = []
    for author in metadata.get("author") or []:
        if not isinstance(author, dict):
            continue
        given = str(author.get("given", "")).strip()
        family = str(author.get("family", "")).strip()
        literal = str(author.get("name", "")).strip()
        name = " ".join(part for part in (given, family) if part) or literal
        if name:
            names.append(name)
    if names:
        return names

    for creator in metadata.get("creators") or []:
        if isinstance(creator, dict):
            name = str(creator.get("name", "")).strip()
            if name:
                names.append(name)
    return names


def _metadata_year(metadata: dict) -> int | None:
    for key in (
        "published-print",
        "published-online",
        "published",
        "issued",
    ):
        date_parts = (metadata.get(key) or {}).get("date-parts")
        try:
            year = date_parts[0][0]
        except (TypeError, IndexError):
            continue
        if isinstance(year, int):
            return year
    year = metadata.get("publicationYear") or metadata.get("publication_year")
    return year if isinstance(year, int) else None


def _metadata_venue(metadata: dict) -> str:
    for key in ("container-title", "event"):
        value = metadata.get(key)
        if isinstance(value, list) and value and isinstance(value[0], str):
            return value[0]
        if isinstance(value, str):
            return value
    publisher = metadata.get("publisher")
    return publisher if isinstance(publisher, str) else ""


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
    creators = [
        {"name": creator.get("name", "")}
        for creator in attributes.get("creators", [])
        if creator.get("name")
    ]
    return {
        "DOI": attributes.get("doi", ""),
        "title": titles,
        "creators": creators,
        "publicationYear": attributes.get("publicationYear"),
        "publisher": attributes.get("publisher", ""),
    }


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
                        "type": normalize_update_type(str(update.get("type", ""))),
                        "notice_doi": item.get("DOI", ""),
                        "source": update.get("source", ""),
                    }
                )
    return notices


def fetch_title_siblings(title: str, mailto: str | None = None) -> list[dict]:
    """Crossref records sharing this title, used to spot duplicate-DOI retractions."""
    url = "https://api.crossref.org/works?" + urlencode(
        {"query.bibliographic": title, "rows": "5", "select": "DOI,title"}
    )
    return _get_json(url, mailto)["message"].get("items", [])


def find_retracted_siblings(title: str, siblings: list[dict]) -> list[str]:
    """DOIs of same-title records that Crossref has marked as retracted."""
    ours = normalize_title(title)
    hits: list[str] = []
    for item in siblings:
        titles = item.get("title") or []
        raw = titles[0] if titles else ""
        if not RETRACTION_TITLE_RE.match(raw):
            continue
        stripped = normalize_title(RETRACTION_TITLE_RE.sub("", raw))
        if SequenceMatcher(None, ours, stripped).ratio() >= TITLE_SIMILARITY_THRESHOLD:
            hits.append(str(item.get("DOI", "")))
    return hits


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


def _check_bibliographic_metadata(label: str, entry: dict, metadata: dict, agency: str) -> list[str]:
    errors: list[str] = []

    expected_authors = author_names(entry.get("authors"))
    resolved_authors = author_names(_metadata_authors(metadata))
    if expected_authors and not resolved_authors:
        errors.append(f"{label}: authors missing from {agency} metadata; verify authoritative metadata before citing")
    elif expected_authors != resolved_authors:
        errors.append(f"{label}: authors do not match {agency} metadata")

    expected_year = entry.get("year")
    resolved_year = _metadata_year(metadata)
    if resolved_year is None:
        errors.append(f"{label}: year missing from {agency} metadata; verify authoritative metadata before citing")
    elif expected_year != resolved_year:
        errors.append(f"{label}: year does not match {agency} metadata")

    expected_venue = entry.get("venue")
    resolved_venue = _metadata_venue(metadata)
    if entry.get("source_type") in VENUE_SOURCE_TYPES and not resolved_venue:
        errors.append(f"{label}: venue missing from {agency} metadata; verify authoritative metadata before citing")
    if (
        isinstance(expected_venue, str)
        and expected_venue.strip()
        and resolved_venue
        and normalize_title(expected_venue) != normalize_title(resolved_venue)
    ):
        errors.append(f"{label}: venue does not match {agency} metadata")

    return errors


def validate_access(label: str, entry: dict, root: Path) -> list[str]:
    """Check what was actually read, and surface sources still waiting on the user."""
    errors: list[str] = []
    access = entry.get("access")

    if access not in ALLOWED_ACCESS_LEVELS:
        return [
            f"{label}: access must be one of {', '.join(sorted(ALLOWED_ACCESS_LEVELS))}"
        ]

    if access == AWAITING_USER_FILE_ACCESS:
        errors.append(
            f"{label}: full text is not reachable - ask the user to download the PDF to "
            f"docs/sources/{entry.get('key', '<key>')}.pdf, then set local_file and "
            f"access '{FULL_TEXT_ACCESS}'"
        )

    local_file = entry.get("local_file")
    if local_file is not None:
        if not isinstance(local_file, str) or not local_file.strip():
            errors.append(f"{label}: local_file must be a non-empty path")
        else:
            root_path = root.resolve()
            file_path = (root_path / local_file).resolve()
            try:
                file_path.relative_to(root_path)
            except ValueError:
                errors.append(f"{label}: local_file must stay inside {root_path}")
            else:
                if not file_path.is_file():
                    errors.append(f"{label}: local_file '{local_file}' does not exist")

    return errors


def validate_bibliographic_fields(label: str, entry: dict, source_type: object) -> list[str]:
    errors: list[str] = []

    authors = entry.get("authors")
    if not isinstance(authors, list) or not authors:
        errors.append(f"{label}: authors must be a non-empty list of strings")
    elif not all(isinstance(author, str) and author.strip() for author in authors):
        errors.append(f"{label}: authors must be a non-empty list of strings")

    year = entry.get("year")
    if type(year) is not int or year < 1000 or year > 9999:
        errors.append(f"{label}: year must be a four-digit integer")

    venue = entry.get("venue")
    if source_type in VENUE_SOURCE_TYPES and (
        not isinstance(venue, str) or not venue.strip()
    ):
        errors.append(f"{label}: venue must be a non-empty string")

    return errors


def validate_registry(
    registry_path: Path,
    online: bool = False,
    fetch_crossref: Callable[[str], dict] | None = None,
    fetch_datacite: Callable[[str], dict] | None = None,
    fetch_updates: Callable[[str], list[dict]] | None = None,
    fetch_siblings: Callable[[str], list[dict]] | None = None,
    today: date | None = None,
    root: Path | None = None,
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
    siblings = fetch_siblings or fetch_title_siblings
    current_day = today or date.today()
    base_dir = root if root is not None else Path(".")

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

        errors.extend(validate_access(label, entry, base_dir))
        errors.extend(validate_bibliographic_fields(label, entry, source_type))

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
        errors.extend(_check_bibliographic_metadata(label, entry, metadata, agency))

        try:
            notices = updates(doi)
        except (HTTPError, URLError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{label}: retraction screening failed: {exc}")
            continue

        acknowledged = entry.get("retraction_ack")
        is_acknowledged = isinstance(acknowledged, str) and bool(acknowledged.strip())

        blocking = sorted({normalize_update_type(str(n.get("type", ""))) for n in notices}
                          & BLOCKING_UPDATE_TYPES)
        if blocking and not is_acknowledged:
            errors.append(
                f"{label}: flagged as {', '.join(blocking)} - do not cite as a valid "
                "result; set 'retraction_ack' with a reason to cite it deliberately"
            )
            continue

        if blocking or is_acknowledged:
            continue

        # No notice points at this DOI, but a duplicate record of the same article
        # may carry the retraction instead.
        try:
            same_title = siblings(title)
        except (HTTPError, URLError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{label}: duplicate-record screening failed: {exc}")
            continue

        retracted_twins = [d for d in find_retracted_siblings(title, same_title) if d != doi]
        if retracted_twins:
            errors.append(
                f"{label}: another record of this article is marked retracted "
                f"({', '.join(retracted_twins)}); this DOI is likely a duplicate of a "
                "retracted work - verify by hand before citing"
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
