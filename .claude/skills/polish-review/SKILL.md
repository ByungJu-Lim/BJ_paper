---
name: polish-review
description: Runs a full-draft proofreading and consistency pass using the 5-axis rubric, after every section and citations are approved. Use as the last stage before considering the paper done.
---

# Polish and Final Review

## Rubric

Delegate to `critic` to review the full draft (`docs/sections/*.md` in order) against these 5 axes, same as every other stage's review:
- novelty/significance
- technical soundness
- clarity
- prior-work coverage
- concrete revision suggestions

Additionally check, specific to a final pass: terminology consistency across sections, that every in-text citation key also appears in `refs/references.bib`, and tense/voice consistency (English, target venue).

## Procedure

1. Run `python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md` one more time — citations must still be clean after any late edits.
2. Produce a short review report listing any remaining issues per section.
3. Stop for the **final-polish user gate** — this is the last of the 4 fixed gates; do not mark the paper complete without explicit user sign-off.
