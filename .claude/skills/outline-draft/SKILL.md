---
name: outline-draft
description: Designs the paper's outline from the story brief and the novelty matrix, maps each claim onto the section that carries it, then expands each section into a full draft. Use after novelty-check, before results-discussion.
---

# Outline and Draft

## Procedure

1. Delegate to `writer`: using `docs/notes/story-brief.md` and
   `docs/notes/novelty-matrix.md`, fill in `docs/outline.md` with a one-sentence
   purpose for each of the 6 sections. The six narrative slots map onto the
   sections directly — `Context`/`Gap`/`Question` are the Introduction's spine,
   `Approach` is Methods, `Finding` is Results, `Implication` is Discussion and
   Conclusion — so a section whose purpose does not trace back to a slot is
   either unnecessary or the brief is incomplete.
2. Map planned claims in `docs/outline.md`. Add a claim declaration to each
   section only when it is actually drafted, naming the claims it carries:
   ```markdown
   <!-- claims: C1, C3 -->
   ```
   Then fill the `Approach` slot in the brief and verify the mapping:
   ```bash
   python scripts/verify_story_brief.py --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json
   ```
   Results, Discussion, and Conclusion may not declare a claim that is still
   `assumed` — the check enforces this, and it is why those sections stay thin
   until `results-discussion` runs.
3. Stop for the **outline-complete user gate** — do not draft any section before the user approves the outline, even if `critic` already approved it.
4. Once approved, delegate to `writer` to draft Introduction, Related Work and Methods one at a time. Leave Results, Discussion and Conclusion as scaffold until the experiment results are available. Reference `docs/notes/novelty-matrix.md` where comparing prior work.
5. Review each drafted section with `critic` before presenting it for the **section-draft-complete user gate**. Record which section/outline approval is pending in `last-critic-issues` so a resumed task does not restart or skip it. Section approvals alone do not mark this whole stage approved.
6. Once the initial three sections are approved, hand off the stage package to `paper-supervise` for its stage review and approval. Do not invent findings to fill the later sections.
