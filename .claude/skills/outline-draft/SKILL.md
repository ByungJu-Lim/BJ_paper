---
name: outline-draft
description: Designs the paper's own section shape from the story brief and the novelty matrix, maps each claim onto the section that carries it, then expands each front-matter section into a full draft. Use after novelty-check, before results-discussion.
---

# Outline and Draft

## Procedure

1. On first entry, initialize the `outline-draft` block's artifact ledger with
   just the `outline` artifact and keep the stage-level `round` at `0/3` until
   every artifact in the ledger is approved:
   ```markdown
   artifacts:
   - outline: not-started, round 0/3, verdict none
   ```
   The ledger grows in step 4 once the outline artifact is approved and
   `docs/outline.md`'s Sections table says how many front-matter sections
   exist and what they're called — it is never fixed at four. Each artifact
   has its own generate-review loop and maximum three attempts. Use the same
   status/verdict invariants as a stage: `awaiting-user`/`approved` require
   `pass`; a third `revise` becomes `escalated`. Work sequentially and do not
   start an artifact until every artifact above it is `approved`.
2. For the `outline` artifact, delegate to `writer`: using
   `docs/notes/story-brief.md` and `docs/notes/novelty-matrix.md`, design
   `docs/outline.md`'s `## Sections` table from scratch — the paper's own
   argument decides the section count, names, and split, not a fixed
   template. A typical shape has Introduction, Related Work, and Methods
   (`front-matter`) followed by Results, Discussion, and Conclusion
   (`concluding`), but the story can call for something else: a Related Work
   split into two strands, a combined Discussion-and-Conclusion, an added
   Case Study or Threats-to-Validity section. For every row:
   - `Role` is `front-matter` (may state `assumed` claims as hypotheses or
     design conditions) or `concluding` (may never assert an `assumed` claim
     as settled fact — `scripts/verify_story_brief.py` reads this column,
     not the filename, to enforce that).
   - The six narrative slots must each land in at least one section:
     `Context`/`Gap`/`Question` normally anchor the opening front-matter
     section(s), `Approach` anchors a methods-type section, `Finding` and
     `Implication` anchor the concluding section(s). A slot with no section
     covering it means the outline is incomplete; a section whose purpose
     traces back to no slot is either unnecessary or the brief is
     incomplete.
   - Keep file basenames sortable by number prefix (`01-`, `02-`, ...) so
     directory order matches manuscript read order.
3. Map planned claims onto the Sections table's `Claims` column. Every section
   that will contain prose must map at least one claim, because
   `verify_story_brief.py` requires exactly one nonempty declaration in every
   written section. Add the declaration only when the section is actually
   drafted:
   ```markdown
   <!-- claims: C1, C3 -->
   ```
   Fill the `Approach` slot in the brief and verify the mapping:
   ```bash
   python scripts/verify_story_brief.py --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json --outline docs/outline.md
   ```
4. Review the outline with `critic`; update only the `outline` artifact's
   round, status, and verdict. Stop for the **outline-complete user gate**
   and mark that artifact `approved` only after explicit approval. Do not
   draft any section before then. Once approved, expand the ledger to add
   one artifact per `front-matter` row the Sections table now lists (using
   `scripts/validation_common.section_artifact_id` naming — `04-results.md`
   → `results`), each `not-started, round 0/3, verdict none`. A story with
   two Related Work strands gets two artifacts here, not one.
5. Draft each `front-matter` section one at a time, in the table's order.
   For each artifact, delegate to `writer`, create the file at the exact
   basename the Sections table names, leave every `concluding` section as a
   scaffold, review with `critic`, then stop for that section's
   **section-draft-complete user gate**. Record every attempt in that
   artifact's own round instead of consuming or reusing the stage-level
   round.
6. After every artifact in the ledger is `approved`, start the stage-level
   package review at `round: 1/3` under `paper-supervise`. Only this final
   package loop uses the stage-level status/round/verdict. Do not mark
   `outline-draft` approved merely because the outline artifact passed.
