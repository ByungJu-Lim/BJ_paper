"""Discovery backends beyond OpenAlex: query Crossref and arXiv directly.

`search_openalex.py` is the first stop, but discovery cannot rest on it alone.
Its own docstring says coverage is incomplete, and the two documented
alternatives - WebSearch and the exa MCP - are not always reachable: a search
tool that is down or unauthorized takes the whole `lit-review` stage with it.
Crossref and arXiv are public HTTP APIs with no key, so this keeps discovery
working on the standard library alone.

    python scripts/search_fallback.py --query "<topic>" --limit 10 --mailto <your email>
    python scripts/search_fallback.py --query "<topic>" --source arxiv
    python scripts/search_fallback.py --query "<topic>" --source crossref --from-year 2018

Same contract as `search_openalex.py`: this is *discovery only*. Nothing here is
verified and nothing here writes to the registry. Every candidate still has to
pass `verify_source_registry.py --online`, which resolves the DOI against
Crossref or DataCite, matches the metadata, and screens for retractions.

Crossref indexes the published record and carries its own retraction notices, so
it is the better first pass for journal articles. arXiv indexes preprints that
Crossref may not have at all - register those as `preprint` with the
server-issued `10.48550/arXiv.*` DOI, never as journal articles.
"""
import argparse
import json
import re
import time
import xml.etree.ElementTree as ElementTree
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:  # package import when run as scripts.search_fallback
    from .search_openalex import normalize_doi, title_keyword
except ImportError:  # direct invocation: python scripts/search_fallback.py
    from search_openalex import normalize_doi, title_keyword

CROSSREF_ROOT = "https://api.crossref.org/works"
ARXIV_ROOT = "http://export.arxiv.org/api/query"
USER_AGENT = "paper-agent-search-fallback/1.0"
ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

# Crossref's type vocabulary mapped onto the registry's. Anything absent maps to
# None so the agent has to make the call rather than inherit a wrong label -
# peer-review status changes how much weight a claim can carry.
CROSSREF_TYPE_MAP = {
    "journal-article": "journal-article",
    "proceedings-article": "conference-paper",
    "posted-content": "preprint",
    "report": "report",
    "report-component": "report",
    "dataset": "dataset",
    "standard": "standard",
}
RETRACTION_LABELS = {"retraction", "withdrawal", "removal",
                     "expression_of_concern", "expression of concern"}


def _fetch(url: str, mailto: str | None, accept: str) -> bytes:
    agent = f"{USER_AGENT} (mailto:{mailto})" if mailto else USER_AGENT
    request = Request(url, headers={"Accept": accept, "User-Agent": agent})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=25) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise
            if attempt == 2:
                raise
        except URLError:
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError(f"request failed: {url}")


def _surname(full_name: str) -> str:
    parts = [part for part in re.split(r"\s+", full_name.strip()) if part]
    tail = parts[-1] if parts else ""
    return re.sub(r"[^a-z]", "", tail.casefold()) or "anon"


def _build_key(authors: list[str], year: int | None, title: str) -> str:
    surname = _surname(authors[0]) if authors else "anon"
    return f"{surname}{year if isinstance(year, int) else 'nodate'}{title_keyword(title)}"


def _candidate(entry: dict, source_api: str, **hints) -> dict:
    """Split what could enter the registry from what is only a search hint."""
    return {"entry": entry, "source_api": source_api,
            "authors": entry["authors"], "venue": entry["venue"],
            "publication_year": entry["year"],
            "cited_by_count": hints.get("cited_by_count"),
            "is_oa": bool(hints.get("is_oa")),
            "pdf_url": hints.get("pdf_url"),
            "is_retracted": bool(hints.get("is_retracted"))}


# --- Crossref ---------------------------------------------------------------

def fetch_crossref(query: str, limit: int, mailto: str | None, from_year: int | None) -> dict:
    params = {"query.bibliographic": query, "rows": str(min(limit, 100))}
    if from_year:
        params["filter"] = f"from-pub-date:{from_year}-01-01"
    if mailto:
        params["mailto"] = mailto
    raw = _fetch(f"{CROSSREF_ROOT}?{urlencode(params)}", mailto, "application/json")
    return json.loads(raw.decode("utf-8"))


def _crossref_year(work: dict) -> int | None:
    for field in ("published", "published-print", "published-online", "issued"):
        parts = ((work.get(field) or {}).get("date-parts") or [[]])[0]
        if parts and isinstance(parts[0], int):
            return parts[0]
    return None


def _crossref_retracted(work: dict) -> bool:
    for update in work.get("update-to") or []:
        label = str((update or {}).get("type", "")).strip().casefold()
        if label in RETRACTION_LABELS:
            return True
    return False


def crossref_candidate(work: dict, today: date) -> dict:
    authors = []
    for author in work.get("author") or []:
        given, family = (author or {}).get("given"), (author or {}).get("family")
        name = " ".join(part for part in (given, family) if part) or (author or {}).get("name")
        if name:
            authors.append(name)

    title = next((t for t in work.get("title") or [] if t), "")
    doi = normalize_doi(work.get("DOI"))
    container = next((c for c in work.get("container-title") or [] if c), "")
    year = _crossref_year(work)

    pdf_url = next((link.get("URL") for link in work.get("link") or []
                    if str((link or {}).get("content-type", "")).endswith("pdf")), None)

    entry = {
        "key": _build_key(authors, year, title),
        "title": title,
        "url": f"https://doi.org/{doi}" if doi else work.get("URL", ""),
        "retrieved_at": today.isoformat(),
        "source_type": CROSSREF_TYPE_MAP.get(work.get("type")),
        "authors": authors,
        "year": year,
        "venue": container,
    }
    if doi:
        entry["doi"] = doi

    return _candidate(entry, "crossref",
                      cited_by_count=work.get("is-referenced-by-count"),
                      is_oa=bool(pdf_url), pdf_url=pdf_url,
                      is_retracted=_crossref_retracted(work))


# --- arXiv ------------------------------------------------------------------

def fetch_arxiv(query: str, limit: int, mailto: str | None, from_year: int | None) -> bytes:
    """`from_year` is deliberately unused here.

    The signature matches `fetch_crossref` so both are interchangeable at the
    `fetchers` injection point, but arXiv's query syntax has no equivalent of
    Crossref's from-pub-date filter that is reliable across its date fields.
    `search()` filters the parsed entries by year instead.
    """
    params = {"search_query": f"all:{query}", "start": "0",
              "max_results": str(min(limit, 100)),
              "sortBy": "relevance", "sortOrder": "descending"}
    return _fetch(f"{ARXIV_ROOT}?{urlencode(params)}", mailto, "application/atom+xml")


def _text(node, path: str) -> str:
    found = node.find(path, ATOM)
    return (found.text or "").strip() if found is not None and found.text else ""


def arxiv_candidate(node, today: date) -> dict:
    title = re.sub(r"\s+", " ", _text(node, "atom:title"))
    authors = [re.sub(r"\s+", " ", (name.text or "").strip())
               for name in node.findall("atom:author/atom:name", ATOM)
               if name.text and name.text.strip()]
    published = _text(node, "atom:published")
    year = int(published[:4]) if published[:4].isdigit() else None

    abs_url = _text(node, "atom:id")
    arxiv_id = abs_url.rsplit("/abs/", 1)[-1] if "/abs/" in abs_url else ""
    versionless = re.sub(r"v\d+$", "", arxiv_id)
    doi = f"10.48550/arXiv.{versionless}" if versionless else ""

    pdf_url = next((link.get("href") for link in node.findall("atom:link", ATOM)
                    if link.get("title") == "pdf"), None)

    entry = {
        "key": _build_key(authors, year, title),
        "title": title,
        "url": f"https://doi.org/{doi}" if doi else abs_url,
        "retrieved_at": today.isoformat(),
        "source_type": "preprint",
        "authors": authors,
        "year": year,
        "venue": "arXiv",
    }
    if doi:
        entry["doi"] = doi

    return _candidate(entry, "arxiv", is_oa=True, pdf_url=pdf_url, is_retracted=False)


# --- driver -----------------------------------------------------------------

def search(query: str, limit: int = 10, source: str = "both", mailto: str | None = None,
           from_year: int | None = None, include_retracted: bool = False,
           today: date | None = None, fetchers: dict | None = None) -> dict:
    fetchers = fetchers or {}
    current_day = today or date.today()
    candidates: list[dict] = []
    total: int | None = None
    errors: list[str] = []

    if source in ("crossref", "both"):
        try:
            payload = (fetchers.get("crossref") or fetch_crossref)(query, limit, mailto, from_year)
            message = payload.get("message") or {}
            total = message.get("total-results")
            candidates.extend(crossref_candidate(work, current_day)
                              for work in message.get("items") or [])
        except (HTTPError, URLError, ValueError, RuntimeError) as exc:
            errors.append(f"crossref: {exc}")

    if source in ("arxiv", "both"):
        try:
            raw = (fetchers.get("arxiv") or fetch_arxiv)(query, limit, mailto, from_year)
            root = ElementTree.fromstring(raw)
            hits = [arxiv_candidate(node, current_day)
                    for node in root.findall("atom:entry", ATOM)]
            if from_year:
                hits = [c for c in hits if c["publication_year"] is None
                        or c["publication_year"] >= from_year]
            candidates.extend(hits)
        except (HTTPError, URLError, ValueError, RuntimeError, ElementTree.ParseError) as exc:
            errors.append(f"arxiv: {exc}")

    retracted_count = sum(1 for c in candidates if c["is_retracted"])
    if not include_retracted:
        candidates = [c for c in candidates if not c["is_retracted"]]

    # The same work from both APIs: keep the first, which is Crossref's
    # published record rather than the preprint of it.
    #
    # Without a DOI, dedupe on the candidate key rather than the title alone.
    # Two distinct works can share a title, and dropping one of them is the
    # exact failure this script exists to prevent - a search that quietly
    # decides a paper does not exist.
    deduplicated: list[dict] = []
    seen: set[str] = set()
    for candidate in candidates:
        entry = candidate["entry"]
        # DOIs are case-insensitive by spec; arXiv issues 10.48550/arXiv.*
        # while Crossref reports the same DOI lowercased.
        marker = (entry.get("doi") or entry["key"]).casefold()
        if marker and marker in seen:
            continue
        seen.add(marker)
        deduplicated.append(candidate)

    return {"query": query, "retrieved_at": current_day.isoformat(),
            "total_matches": total, "retracted_filtered": retracted_count,
            "errors": errors, "candidates": deduplicated[:limit]}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search Crossref and arXiv for candidate sources.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--source", choices=("crossref", "arxiv", "both"), default="both")
    parser.add_argument("--mailto", help="Contact email for the Crossref polite pool")
    parser.add_argument("--from-year", type=int, help="Only works published this year or later")
    parser.add_argument("--include-retracted", action="store_true",
                        help="Keep works Crossref flags as retracted instead of filtering them out")
    parser.add_argument("--out", type=Path, help="Write JSON here instead of stdout")
    args = parser.parse_args()

    result = search(args.query, limit=args.limit, source=args.source, mailto=args.mailto,
                    from_year=args.from_year, include_retracted=args.include_retracted)

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {len(result['candidates'])} candidates to {args.out}")
    else:
        print(text)

    if result["retracted_filtered"]:
        print(f"\nFiltered {result['retracted_filtered']} retracted work(s). "
              "Re-run with --include-retracted only if you are citing one deliberately.")
    for error in result["errors"]:
        print(f"\nbackend unavailable - {error}")

    # Every backend down is a failure. One down while the other returned work is
    # the situation this script exists for, and must not read as success either
    # way round: report it, but do not throw away the results that did arrive.
    if not result["candidates"] and result["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
