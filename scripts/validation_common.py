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
