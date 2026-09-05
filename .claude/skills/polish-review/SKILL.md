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

1. Delegate to `writer`: if `docs/sections/06-conclusion.md` has not yet been drafted, write it now, summarizing the approved Results/Discussion sections and restating the paper's contribution from `docs/notes/novelty-matrix.md`.
2. Run the full citation audit one more time — late edits are exactly how dangling citations appear:
   ```bash
   python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json \n     --sections docs/sections/*.md --bib refs/references.bib
   ```
   This covers the manual "every in-text key is also in `refs/references.bib`" check above; do not eyeball it.
3. Produce a short review report listing any remaining issues per section.
4. Stop for the **final-polish user gate** — do not mark the paper complete without explicit user sign-off.
5. Once approved, hand off to `submission-manage`. "Done drafting" is not "published": the paper still has to reach a venue, and a rejection routes specific sections back through the stages above.
