---
name: results-discussion
description: Analyzes processed experiment data and drafts the Results and Discussion sections. Use once code-experiment has produced data/processed/ output.
---

# Results and Discussion

## Procedure

1. Delegate to `scientist`: analyze the contents of `data/processed/` (statistics, trends, anomalies relevant to the paper's claims).
2. Delegate to `writer`: draft `docs/sections/04-results.md` as an objective report of what the data shows — no interpretation here.
3. Delegate to `writer`: draft `docs/sections/05-discussion.md` interpreting the results, explicitly comparing against the "Closest Prior Work" column of `docs/notes/novelty-matrix.md`, and naming limitations.
4. Update `docs/notes/story-brief.md` from what the data actually showed:
   - Fill the `Finding` and `Implication` slots. `Finding` may only state what a
     run manifest in `data/processed/` backs; if no manifest exists, there is no
     finding yet.
   - Flip each claim's status with `run:<run-id>` evidence. A claim the data
     contradicts is `refuted` — rewrite the narrative slot that rested on it and
     take that to the user as a narrative-revision gate. The falsifier written
     before the experiment is what decides this, not a reading of the plot.
   ```bash
   python scripts/verify_story_brief.py --sections docs/sections/*.md \
     --registry docs/notes/retrieved-sources.json
   ```
5. Hand off both sections to `critic` through the `paper-supervise` loop, then stop for the section-draft-complete user gate.
