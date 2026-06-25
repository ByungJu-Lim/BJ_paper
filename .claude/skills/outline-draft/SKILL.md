---
name: outline-draft
description: Designs the paper's outline from the novelty matrix, then expands each section into a full draft. Use after novelty-check, before results-discussion.
---

# Outline and Draft

## Procedure

1. Delegate to `writer`: using `docs/notes/novelty-matrix.md`, fill in `docs/outline.md` with a one-sentence purpose for each of the 6 sections.
2. Stop for the **outline-complete user gate** — do not draft any section before the user approves the outline, even if `critic` already approved it.
3. Once approved, delegate to `writer` to expand each `docs/sections/0N-*.md` stub into a full draft, one section at a time, referencing `docs/notes/novelty-matrix.md` wherever the section discusses prior work.
4. After each section draft, stop for the **section-draft-complete user gate**.
5. Hand off each section to `critic` for review through the `paper-supervise` loop before presenting it to the user.
