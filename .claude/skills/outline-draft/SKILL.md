---
name: outline-draft
description: Designs the paper's outline from the story brief and the novelty matrix, maps each claim onto the section that carries it, then expands each section into a full draft. Use after novelty-check, before results-discussion.
---

# Outline and Draft

## Procedure

1. On first entry, initialize the `outline-draft` block's artifact ledger and keep
   the stage-level `round` at `0/3` until all four artifacts are approved:
   ```markdown
   artifacts:
   - outline: not-started, round 0/3, verdict none
   - introduction: not-started, round 0/3, verdict none
   - related-work: not-started, round 0/3, verdict none
   - methods: not-started, round 0/3, verdict none
   ```
   Each artifact has its own generate-review loop and maximum three attempts. Use
   the same status/verdict invariants as a stage: `awaiting-user`/`approved`
   require `pass`; a third `revise` becomes `escalated`. Work sequentially and do
   not start an artifact until every artifact above it is `approved`.
2. For the `outline` artifact, delegate to `writer`: using
   `docs/notes/story-brief.md` and `docs/notes/novelty-matrix.md`, fill in
   `docs/outline.md` with a one-sentence purpose for each of the 6 sections. The
   six narrative slots map onto the sections directly —
   `Context`/`Gap`/`Question` are the Introduction's spine, `Approach` is Methods,
   `Finding` is Results, `Implication` is Discussion and Conclusion — so a section
   whose purpose does not trace back to a slot is either unnecessary or the brief
   is incomplete.
3. Map planned claims in `docs/outline.md`. Every section that will contain prose
   must map at least one claim, because `verify_story_brief.py` requires exactly
   one nonempty declaration in every written section. Introduction, Related Work,
   and Methods may carry `assumed` claims explicitly as hypotheses or design
   conditions; Results, Discussion, and Conclusion may not assert them as facts.
   Add the declaration only when the section is actually drafted:
   ```markdown
   <!-- claims: C1, C3 -->
   ```
   Fill the `Approach` slot in the brief and verify the mapping:
   ```bash
   python scripts/verify_story_brief.py --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json
   ```
4. Review the outline with `critic`; update only the `outline` artifact's round,
   status, and verdict. Stop for the **outline-complete user gate** and mark that
   artifact `approved` only after explicit approval. Do not draft any section
   before then.
5. Draft Introduction, Related Work, and Methods one at a time. For each artifact,
   delegate to `writer`, leave Results/Discussion/Conclusion as scaffolds, review
   with `critic`, then stop for that section's **section-draft-complete user gate**.
   Record every attempt in that artifact's own round instead of consuming or
   reusing the stage-level round.
6. After all four artifacts are `approved`, start the stage-level package review
   at `round: 1/3` under `paper-supervise`. Only this final package loop uses the
   stage-level status/round/verdict. Do not mark `outline-draft` approved merely
   because the outline artifact passed.
