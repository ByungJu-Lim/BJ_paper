"""Mechanical length and wording gate for manuscript prose.

Section 2 and 8 of docs/notes/scientific-writing-rules.md are easy to agree with and
easy to ignore: a reviewer reading for meaning lets an 80-word sentence through because
every clause in it is true. This check counts instead of judging. It fails on

- a sentence longer than MAX_SENTENCE_WORDS words,
- a file whose mean sentence length exceeds MAX_MEAN_WORDS (files with at least
  MIN_SENTENCES_FOR_MEAN sentences),
- a paragraph longer than MAX_PARAGRAPH_WORDS words,
- a sentence that chains clauses with two or more colons/semicolons,
- an inline enumeration of three or more items such as "(a) ... (b) ... (c)",
- a banned filler phrase.

A paragraph whose first line is `<!-- prose-ok: <reason> -->` is exempt from the length,
mean and chaining checks (not from banned phrases); every waiver is printed so the
reviewer sees it. Headings, tables, display equations, figure/table captions, image lines
and HTML comments are not prose and are skipped. A waiver that is not followed by a prose
paragraph is an error. Word counts assume English text: a file written mainly in Hangul is
skipped with a note until a Korean limit is agreed (CLAUDE.md).

With --state, only sections that have reached review are enforced (the outline-draft
artifact for a front-matter section, the results-discussion stage for the rest, every
file once polish-review has started), so a draft can be committed mid-revision. Without
--state every file is enforced.
"""
import argparse
import glob
import re
import sys
from pathlib import Path

try:
    from .check_paper_state import ARTIFACT_RE, parse_stages, validate_all as validate_state
    from .validation_common import outline_roles_by_file, section_artifact_id, visible_markdown
except ImportError:  # pragma: no cover - script execution path
    from check_paper_state import ARTIFACT_RE, parse_stages, validate_all as validate_state
    from validation_common import outline_roles_by_file, section_artifact_id, visible_markdown

MAX_SENTENCE_WORDS = 35
MAX_MEAN_WORDS = 22
MIN_SENTENCES_FOR_MEAN = 5
MAX_PARAGRAPH_WORDS = 180
MAX_CLAUSE_MARKS = 1

BANNED_PHRASES = (
    "it is worth mentioning",
    "it is worth noting",
    "it is important to note",
    "it should be noted",
    "needless to say",
    "in order to",
    "due to the fact that",
    "a large number of",
    "conduct an analysis of",
    "has the capability to",
    "plays a crucial role",
    "plays a vital role",
    "utilize",
    "utilise",
    "clearly",
    "obviously",
    "remarkably",
    "interestingly",
)

WAIVER_RE = re.compile(r"^\s*<!--\s*prose-ok:\s*(.+?)\s*-->\s*$")
CAPTION_RE = re.compile(r"^\s*(Fig\.|Figure|Table)\s+\S+?:")
ABBREVIATIONS = ("e.g.", "i.e.", "et al.", "Eq.", "Eqs.", "Fig.", "Figs.", "Ref.", "Refs.",
                 "vs.", "cf.", "approx.", "No.", "Sec.", "Secs.", "resp.")
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9$\x00])")
REVIEWED_STATUSES = {"awaiting-review", "awaiting-user", "approved", "escalated"}
DEFAULT_OUTLINE_PATH = Path("docs/outline.md")
ENUMERATION_RE = re.compile(r"\((?:[a-h]|i{1,3}|iv|vi{0,3})\)")
# "Panels (a), (b) and (c)" or "Fig. 3(a)-(c)" name figure panels, not an inline list.
PANEL_REFERENCE_RE = re.compile(
    r"\b(?:[Pp]anels?|Figs?\.|Figures?)\s*\d*\s*(?:\([a-h]\)\s*(?:,|and|or|–|-|to)?\s*)+")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _clean_inline(text: str) -> str:
    text = re.sub(r"\$[^$]+\$", "X", text)               # inline math counts as one word
    text = re.sub(r"\[[^\]]*@[^\]]*\]", "", text)         # [@key; @key] citations are not words
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links keep their text
    text = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", text)  # list markers
    return text


def _drop_comments_except_waivers(text: str) -> str:
    def keep_waiver(match: re.Match) -> str:
        if WAIVER_RE.match(match.group(0)):
            return match.group(0)
        return "\n" * match.group(0).count("\n")
    return COMMENT_RE.sub(keep_waiver, text)


def paragraphs(text: str) -> tuple[list[tuple[int, str, str | None]], list[int]]:
    """Return prose paragraphs as (first line, prose, waiver reason) and orphan waiver lines."""
    visible = visible_markdown(text, keep_comments=True)
    lines = _drop_comments_except_waivers(visible).splitlines()
    result: list[tuple[int, str, str | None]] = []
    orphans: list[int] = []
    pending_line = 0
    buffer: list[str] = []
    start = 0
    waiver: str | None = None
    pending_waiver: str | None = None
    in_math = False

    def flush() -> None:
        nonlocal buffer, waiver
        if buffer:
            result.append((start, " ".join(buffer), waiver))
        buffer = []
        waiver = None

    def drop_pending() -> None:
        nonlocal pending_waiver
        if pending_waiver is not None:
            orphans.append(pending_line)
        pending_waiver = None

    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("$$"):
            flush()
            drop_pending()
            if not (len(stripped) > 2 and stripped.endswith("$$")):
                in_math = not in_math
            continue
        if in_math:
            continue
        waiver_match = WAIVER_RE.match(line)
        if waiver_match:
            flush()
            drop_pending()
            pending_waiver = waiver_match.group(1)
            pending_line = number
            continue
        if not stripped:
            flush()
            continue
        if stripped.startswith(("#", "|", "![", "<!--")) or CAPTION_RE.match(line):
            flush()
            drop_pending()
            continue
        if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line):
            flush()  # each list item is its own paragraph
        if not buffer:
            start = number
            waiver = pending_waiver
            pending_waiver = None
        buffer.append(stripped)
    flush()
    drop_pending()
    return result, orphans


def sentences(paragraph: str) -> list[str]:
    protected = paragraph
    for index, abbreviation in enumerate(ABBREVIATIONS):
        protected = protected.replace(abbreviation, f"\x00{index}\x00")
    parts = SENTENCE_END_RE.split(protected)
    restored = []
    for part in parts:
        for index, abbreviation in enumerate(ABBREVIATIONS):
            part = part.replace(f"\x00{index}\x00", abbreviation)
        if part.strip():
            restored.append(part.strip())
    return restored


def word_count(sentence: str) -> int:
    return sum(1 for token in _clean_inline(sentence).split() if re.search(r"\w", token))


def clause_marks(sentence: str) -> int:
    cleaned = _clean_inline(sentence)
    cleaned = re.sub(r"\d:\d", "", cleaned)  # ratios and times
    return cleaned.count(";") + cleaned.count(":")


def mainly_hangul(text: str) -> bool:
    return len(re.findall(r"[\uac00-\ud7a3]", text)) > len(re.findall(r"[A-Za-z]", text))


def check_text(text: str, label: str) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    notes: list[str] = []
    lengths: list[int] = []
    if mainly_hangul(text):
        notes.append(f"{label}: written mainly in Korean; no agreed Korean limit yet, not checked")
        return errors, notes, {"sentences": 0, "mean": 0.0, "max": 0}
    prose, orphans = paragraphs(text)
    for line in orphans:
        errors.append(f"{label}:{line}: prose-ok waiver is not followed by a prose paragraph")
    for line, paragraph, waiver in prose:
        lowered = _clean_inline(paragraph).lower()
        for phrase in BANNED_PHRASES:
            if re.search(r"\b" + re.escape(phrase) + r"\b", lowered):
                errors.append(f"{label}:{line}: banned phrase {phrase!r}")
        paragraph_sentences = sentences(paragraph)
        counts = [word_count(sentence) for sentence in paragraph_sentences]
        if waiver is not None:
            notes.append(f"{label}:{line}: waiver prose-ok: {waiver}")
            continue
        if sum(counts) > MAX_PARAGRAPH_WORDS:
            errors.append(f"{label}:{line}: paragraph has {sum(counts)} words (max {MAX_PARAGRAPH_WORDS})")
        lengths.extend(counts)
        for sentence, count in zip(paragraph_sentences, counts):
            preview = sentence if len(sentence) <= 90 else sentence[:87] + "..."
            if count > MAX_SENTENCE_WORDS:
                errors.append(f"{label}:{line}: sentence has {count} words (max {MAX_SENTENCE_WORDS}): {preview}")
            if clause_marks(sentence) > MAX_CLAUSE_MARKS:
                errors.append(f"{label}:{line}: sentence chains clauses with colons/semicolons; split it: {preview}")
            if len(ENUMERATION_RE.findall(PANEL_REFERENCE_RE.sub(" ", sentence))) >= 3:
                errors.append(f"{label}:{line}: inline enumeration of 3+ items; use a list or table: {preview}")
    mean = sum(lengths) / len(lengths) if lengths else 0.0
    if len(lengths) >= MIN_SENTENCES_FOR_MEAN and mean > MAX_MEAN_WORDS:
        errors.append(f"{label}: mean sentence length {mean:.1f} words (max {MAX_MEAN_WORDS})")
    stats = {"sentences": len(lengths), "mean": mean, "max": max(lengths, default=0)}
    return errors, notes, stats


def expand(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        if glob.has_magic(pattern):
            paths.extend(Path(match) for match in sorted(glob.glob(pattern)))
        else:
            path = Path(pattern)
            if not path.is_file():
                raise ValueError(f"not a readable file: {path}")
            paths.append(path)
    return paths


def files_under_review(paths: list[Path], state_path: Path, outline_path: Path) -> list[Path]:
    stages = {stage["id"]: stage for stage in parse_stages(state_path)}
    if stages.get("polish-review", {}).get("status", "not-started") != "not-started":
        return paths
    artifact_status = {}
    for entry in stages.get("outline-draft", {}).get("artifacts", []):
        match = ARTIFACT_RE.match(entry.strip())
        if match:
            artifact_status[match.group("id")] = match.group("status")
    concluding_status = stages.get("results-discussion", {}).get("status", "not-started")
    roles = outline_roles_by_file(outline_path)
    enforced = []
    for path in paths:
        if roles.get(path.name) == "front-matter":
            status = artifact_status.get(section_artifact_id(path.name), "not-started")
        else:
            status = concluding_status
        if status in REVIEWED_STATUSES:
            enforced.append(path)
    return enforced


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sections", nargs="+", required=True,
                        help="Markdown files or globs (sections, abstract, cover letter)")
    parser.add_argument("--state", type=Path,
                        help="Enforce only sections that have reached review in this workflow state")
    parser.add_argument("--outline", type=Path, default=DEFAULT_OUTLINE_PATH,
                        help="docs/outline.md, whose Sections table gives each file its role")
    args = parser.parse_args(argv)
    try:
        paths = expand(args.sections)
        if args.state:
            state_errors = validate_state(args.state, args.outline)
            if state_errors:
                raise ValueError("invalid workflow state: " + "; ".join(
                    error for group in state_errors.values() for error in group))
            under_review = files_under_review(paths, args.state, args.outline)
            for path in paths:
                if path not in under_review:
                    print(f"{path}: not yet under review, skipped")
            paths = under_review
    except ValueError as error:
        print(f"ERROR: {error}")
        return 1
    if not paths:
        print("No manuscript files to check.")
        return 0
    all_errors: list[str] = []
    for path in paths:
        errors, notes, stats = check_text(path.read_text(encoding="utf-8"), str(path))
        print(f"{path}: {stats['sentences']} sentences, mean {stats['mean']:.1f}, max {stats['max']} words")
        for note in notes:
            print(f"  NOTE: {note}")
        all_errors.extend(errors)
    for error in all_errors:
        print(f"ERROR: {error}")
    if all_errors:
        print(f"{len(all_errors)} prose violation(s). Split sentences or move conditions to Methods/tables; "
              "see docs/notes/scientific-writing-rules.md section 2.")
        return 1
    print("Prose check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
