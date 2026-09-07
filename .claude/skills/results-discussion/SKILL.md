---
name: results-discussion
description: Analyzes processed experiment data and drafts the Results and Discussion sections. Use once code-experiment has produced data/processed/ output.
---

# Results and Discussion

## Procedure

1. Delegate to `scientist`: analyze the contents of `data/processed/` (statistics, trends, anomalies relevant to the paper's claims).
2. Delegate to `writer`: draft `docs/sections/04-results.md` as an objective report of what the data shows — no interpretation here.
3. Delegate to `writer`: draft `docs/sections/05-discussion.md` interpreting the results, explicitly comparing against the "Closest Prior Work" column of `docs/notes/novelty-matrix.md`, and naming limitations.
   Draft `docs/sections/06-conclusion.md` from those results in this stage as well,
   so all manuscript citations exist before `citation-manage`. Each written
   section needs one nonempty claim declaration. Do not declare the old refuted
   proposition as a result: retain it in the ledger and add a supported claim
   describing the negative result, with its run evidence.
4. Update `docs/notes/story-brief.md` from what the data actually showed:
   - Fill the `Finding` and `Implication` slots. `Finding` may only state what a
     run manifest in `data/processed/` backs; if no manifest exists, there is no
     finding yet.
   - Flip each claim's status with `run:<run-id>` evidence. A claim the data
     contradicts is `refuted` — rewrite the narrative slot that rested on it and
     take that to the user as a narrative-revision gate. The falsifier written
     before the experiment is what decides this, not a reading of the plot.
   ```bash
   python scripts/verify_story_brief.py --check-manifests --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json
   ```
5. Hand off Results, Discussion and Conclusion to `critic` through the `paper-supervise` loop, then stop for each section's user gate. Verify the prose matches its declared claims; structural validation alone cannot establish that correspondence.
