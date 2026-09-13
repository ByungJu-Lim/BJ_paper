# Paper Outline

> Filled in by the `outline-draft` skill from `docs/notes/story-brief.md` and
> `docs/notes/novelty-matrix.md`, after `novelty-check` produces the matrix.
> The number, order, title, and role of sections are decided by the paper's
> own story — not fixed by this template. A different argument can need a
> different shape (a split Related Work, an added Case Study section, a
> combined Discussion-and-Conclusion), as long as every section maps back to
> a narrative slot and every load-bearing claim lands somewhere.

## Sections

> One row per file under `docs/sections/`, in the order they appear in the
> manuscript. `Role` is `front-matter` (may state `assumed` claims as
> hypotheses or design conditions) or `concluding` (may never assert an
> `assumed` claim as settled fact — `scripts/verify_story_brief.py` reads
> this table, not the filename, to enforce that). `Claims` lists what the
> section will carry once drafted; leave it blank until the section's
> `<!-- claims: ... -->` declaration is actually written. Empty until
> `outline-draft` designs the paper's actual shape from the approved story
> brief and novelty matrix — a typical shape has an Introduction, Related
> Work, and Methods (`front-matter`) followed by Results, Discussion, and
> Conclusion (`concluding`), but the count, names, and split are the
> story's call, not a fixed requirement.

| # | File | Title | Role | Narrative slot(s) | Claims | Purpose |
|---|---|---|---|---|---|---|

Keep these invariants whatever shape the table ends up as:

- Every row's file exists under `docs/sections/` with that exact basename.
- `Context`/`Gap`/`Question` are covered by `front-matter` section(s);
  `Approach` likewise; `Finding` and `Implication` are covered by
  `concluding` section(s). A slot with no section role covering it means
  the outline is incomplete.
- File basenames stay sortable by number prefix (`01-`, `02-`, ...) so the
  manuscript's read order matches directory order.
