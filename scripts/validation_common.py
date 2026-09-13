"""Small shared helpers for the dependency-free Markdown validators."""
import glob
import re
from pathlib import Path


def expand_paths(patterns: list[Path]) -> list[Path]:
    """Accept both shell-expanded files and literal globs; never silently skip one."""
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        matches = sorted(glob.glob(str(pattern))) if glob.has_magic(str(pattern)) else [str(pattern)]
        if not matches:
            raise ValueError(f"no files match: {pattern}")
        for match in matches:
            path = Path(match)
            if not path.is_file():
                raise ValueError(f"not a readable file: {path}")
            if path.resolve() not in seen:
                paths.append(path)
                seen.add(path.resolve())
    return paths


def visible_markdown(text: str, *, keep_comments: bool = False) -> str:
    """Remove code examples and, by default, HTML comments before inspecting prose."""
    lines: list[str] = []
    fence = ''
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if fence:
            if re.match(r'^ {0,3}' + re.escape(fence[0]) + '{' + str(len(fence)) + r',}\s*$', line):
                fence = ''
            lines.append('\n')
        elif marker:
            fence = marker.group(1)
            lines.append('\n')
        else:
            # Indentation alone may be a paragraph/list continuation, not code.
            # Preserve it rather than hiding citations; use fences for examples.
            lines.append(line)
    result = ''.join(lines)
    result = re.sub(r'(`+)(?!`)(.*?)\1(?!`)', ' ', result, flags=re.DOTALL)
    if not keep_comments:
        result = re.sub(r'<!--.*?-->', '', result, flags=re.DOTALL)
    return result


TABLE_DIVIDER_RE = re.compile(r"^\|[\s:|-]+\|$")


def read_table_rows(lines: list[str], header_index: int) -> list[list[str]]:
    """Read the body rows of a Markdown table whose header sits at `header_index`."""
    rows: list[list[str]] = []
    index = header_index + 1
    if index < len(lines) and TABLE_DIVIDER_RE.match(lines[index].strip()):
        index += 1
    while index < len(lines) and lines[index].strip().startswith('|'):
        rows.append([cell.strip() for cell in lines[index].strip().strip('|').split('|')])
        index += 1
    return rows


# `docs/outline.md`'s `## Sections` table is the single source of truth for how
# many sections the manuscript has, what they are called, and what role each
# plays in the argument. Both `verify_story_brief.py` (claim/role enforcement)
# and `check_paper_state.py` (outline-draft's per-section artifact ledger) read
# it, so the parser lives here rather than being duplicated or, worse, one
# validator quietly trusting a fixed section list the other no longer does.
OUTLINE_SECTIONS_HEADER_RE = re.compile(
    r"^\|\s*#\s*\|\s*File\s*\|\s*Title\s*\|\s*Role\s*\|", re.IGNORECASE
)
VALID_SECTION_ROLES = ("front-matter", "concluding")


def parse_outline_sections(outline_path: Path) -> list[dict[str, str]]:
    """Parse `docs/outline.md`'s `## Sections` table into ordered row dicts.

    Each row has at least `file` and `role`. Returns `[]` if the outline does
    not exist or has no Sections table yet (true early in the pipeline,
    before `outline-draft` has written one) - callers treat that as "the
    outline has not assigned section roles yet", not as an error on its own.
    """
    if not outline_path.is_file():
        return []
    lines = outline_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not OUTLINE_SECTIONS_HEADER_RE.match(line.strip()):
            continue
        rows: list[dict[str, str]] = []
        for raw_row in read_table_rows(lines, index):
            padded = raw_row + [""] * (7 - len(raw_row))
            file_name = padded[1].strip().strip("`")
            if not file_name:
                continue
            rows.append({
                "file": file_name,
                "title": padded[2].strip(),
                "role": padded[3].strip().strip("`").lower(),
                "slots": padded[4].strip(),
                "claims": padded[5].strip(),
                "purpose": padded[6].strip(),
            })
        return rows
    return []


def section_artifact_id(file_name: str) -> str:
    """`04-results.md` -> `results`: drop a numeric prefix and the extension.

    This is the id `outline-draft`'s per-section artifact ledger uses, kept
    as one function so the ledger and the outline table can never drift into
    two different naming schemes for the same file.
    """
    stem = Path(file_name).stem
    return re.sub(r"^\d+-", "", stem)


def outline_roles_by_file(outline_path: Path) -> dict[str, str]:
    """`{file_name: role}` from `parse_outline_sections`, for role lookups."""
    return {row["file"]: row["role"] for row in parse_outline_sections(outline_path)}


def is_concluding_section(section_path: Path, outline_roles: dict[str, str] | None = None) -> bool:
    """A section is concluding if the outline's Sections table says so.

    `outline_roles` is normally `outline_roles_by_file(docs/outline.md)`.
    Falling back to `False` when the outline has nothing to say about a file
    is deliberate: an unlisted section is an outline gap to fix, not a
    licence to assert an assumed claim as fact by omission.
    """
    if outline_roles is None:
        outline_roles = {}
    return outline_roles.get(section_path.name) == "concluding"
