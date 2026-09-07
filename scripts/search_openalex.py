"""Search OpenAlex and emit registry-shaped candidate sources.

Discovery only. Nothing here writes to the registry and nothing here is trusted:
candidates still have to pass verify_source_registry.py, which resolves the DOI
against Crossref or DataCite and screens for retractions. OpenAlex is used
because it returns structured metadata rather than prose a model has to parse -
a title and DOI come from the index, so they cannot be invented - and because it
reports open-access PDF locations, which is often the difference between reading
a paper and having to ask the user to download it.

    python scripts/search_openalex.py --query "heat exchanger fouling" --limit 10

Coverage is not complete: some arXiv DOIs are absent, so a source missing here is
not evidence that it does not exist.
"""
import argparse
import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://api.openalex.org/works"
USER_AGENT = "paper-agent-openalex-search/1.0"
DOI_URL_PREFIX_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)

# OpenAlex work types mapped onto the registry's source_type vocabulary.
# Anything absent maps to None so the agent has to make the call rather than
# inheriting a wrong label - peer-review status changes a claim's weight.
TYPE_MAP = {
    "preprint": "preprint",
    "conference-paper": "conference-paper",
    "dataset": "dataset",
    "report": "report",
    "standard": "standard",
}
STOPWORDS = {
    "a", "an", "and", "for", "from", "in", "of", "on", "the", "to", "with",
    "using", "based", "via", "towards", "toward", "study", "analysis",
}


def _user_agent(mailto: str | None) -> str:
    return f"{USER_AGENT} (mailto:{mailto})" if mailto else USER_AGENT


def fetch_works(
    query: str, limit: int, mailto: str | None = None, from_year: int | None = None
) -> dict:
    """One search request, retrying on the throttling and transient codes."""
    params = {"search": query, "per-page": str(min(limit, 50))}
    if from_year:
        params["filter"] = f"from_publication_date:{from_year}-01-01"
    if mailto:
        params["mailto"] = mailto
    url = f"{API_ROOT}?{urlencode(params)}"
    request = Request(
        url, headers={"Accept": "application/json", "User-Agent": _user_agent(mailto)}
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
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
    raise RuntimeError("OpenAlex request failed")


def normalize_doi(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return DOI_URL_PREFIX_RE.sub("", value.strip()).lower()


def first_author_surname(work: dict) -> str:
    for authorship in work.get("authorships") or []:
        name = ((authorship or {}).get("author") or {}).get("display_name")
        if isinstance(name, str) and name.strip():
            return re.sub(r"[^a-z]", "", name.split()[-1].casefold()) or "anon"
    return "anon"


def title_keyword(title: str) -> str:
    for word in re.findall(r"[A-Za-z]+", title or ""):
        lowered = word.casefold()
        if lowered not in STOPWORDS and len(lowered) > 2:
            return lowered
    return "work"


def build_key(work: dict) -> str:
    year = work.get("publication_year")
    year_part = str(year) if isinstance(year, int) else "nodate"
    return f"{first_author_surname(work)}{year_part}{title_keyword(work.get('display_name') or '')}"


def map_source_type(work: dict) -> str | None:
    work_type = work.get("type")
    if work_type in TYPE_MAP:
        return TYPE_MAP[work_type]
    if work_type == "article":
        source = (work.get("primary_location") or {}).get("source") or {}
        return "journal-article" if source.get("type") == "journal" else "report"
    return None


def landing_url(work: dict, doi: str) -> str:
    if doi:
        return f"https://doi.org/{doi}"
    location = work.get("primary_location") or {}
    for candidate in (location.get("landing_page_url"), work.get("id")):
        if isinstance(candidate, str) and candidate.startswith("http"):
            return candidate
    return ""


def to_candidate(work: dict, today: date) -> dict:
    """Split what could enter the registry from what is only a search hint."""
    doi = normalize_doi(work.get("doi"))
    open_access = work.get("open_access") or {}
    best_location = work.get("best_oa_location") or {}
    source = (work.get("primary_location") or {}).get("source") or {}

    entry = {
        "key": build_key(work),
        "title": work.get("display_name") or "",
        "url": landing_url(work, doi),
        "retrieved_at": today.isoformat(),
        "source_type": map_source_type(work),
    }
    if doi:
        entry["doi"] = doi

    return {
        "entry": entry,
        "openalex_id": work.get("id"),
        "authors": [
            ((a or {}).get("author") or {}).get("display_name")
            for a in (work.get("authorships") or [])[:5]
        ],
        "venue": source.get("display_name"),
        "publication_year": work.get("publication_year"),
        "cited_by_count": work.get("cited_by_count"),
        "is_oa": bool(open_access.get("is_oa")),
        "pdf_url": best_location.get("pdf_url") or open_access.get("oa_url"),
        "is_retracted": bool(work.get("is_retracted")),
    }


def search(
    query: str,
    limit: int = 10,
    mailto: str | None = None,
    from_year: int | None = None,
    include_retracted: bool = False,
    today: date | None = None,
    fetch: Callable[..., dict] | None = None,
) -> dict:
    fetcher = fetch or fetch_works
    payload = fetcher(query, limit, mailto, from_year)
    works = payload.get("results") or []
    current_day = today or date.today()

    candidates = [to_candidate(work, current_day) for work in works]
    retracted_count = sum(1 for c in candidates if c["is_retracted"])
    if not include_retracted:
        candidates = [c for c in candidates if not c["is_retracted"]]

    return {
        "query": query,
        "retrieved_at": current_day.isoformat(),
        "total_matches": (payload.get("meta") or {}).get("count"),
        "retracted_filtered": retracted_count,
        "candidates": candidates[:limit],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Search OpenAlex for candidate sources.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--mailto", help="Contact email for the OpenAlex polite pool")
    parser.add_argument("--from-year", type=int, help="Only works published this year or later")
    parser.add_argument(
        "--include-retracted",
        action="store_true",
        help="Keep retracted works in the results instead of filtering them out",
    )
    parser.add_argument("--out", type=Path, help="Write JSON here instead of stdout")
    args = parser.parse_args()

    try:
        result = search(
            args.query,
            limit=args.limit,
            mailto=args.mailto,
            from_year=args.from_year,
            include_retracted=args.include_retracted,
        )
    except (HTTPError, URLError, ValueError, RuntimeError) as exc:
        print(f"OpenAlex search failed: {exc}")
        return 1

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {len(result['candidates'])} candidates to {args.out}")
    else:
        print(text)

    if result["retracted_filtered"]:
        print(
            f"\nFiltered {result['retracted_filtered']} retracted work(s). "
            "Re-run with --include-retracted only if you are citing one deliberately."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
