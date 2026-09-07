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

Additionally check, specific to a final pass: that the paper still tells the
story in `docs/notes/story-brief.md` — read the six slots in order, then read
the section openings in order, and confirm they are the same argument;
terminology consistency across sections, that every in-text citation key also appears in `refs/references.bib`, and tense/voice consistency (English, target venue).

## Procedure

1. Confirm all six sections, including Conclusion, were drafted and approved before citation finalization. If substantive content or citations are missing, reopen the responsible stage and invalidate its dependent approvals using `paper-supervise`; do not silently add a new section after citation approval. Minor wording edits still require the checks below.
2. Run the full citation audit one more time — late edits are exactly how dangling citations appear:
   ```bash
   python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections "docs/sections/*.md" --bib refs/references.bib
   ```
   This covers the manual "every in-text key is also in `refs/references.bib`" check above; do not eyeball it.
3. Run the strict story check. Every slot must be filled and every live claim
   must be carried by some section — a claim no section carries was either
   abandoned mid-draft or belongs to a different paper:
   ```bash
   python scripts/verify_story_brief.py --require-slots all --require-coverage --check-manifests --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json
   ```
4. Produce a short review report listing any remaining issues per section.
5. Stop for the **final-polish user gate** — do not mark the paper complete without explicit user sign-off.
6. Once approved, hand off to `submission-manage`. "Done drafting" is not "published": the paper still has to reach a venue, and a rejection routes specific sections back through the stages above.
