---
name: results-discussion
description: Analyzes processed experiment data and drafts the Results and Discussion sections. Use once code-experiment has produced data/processed/ output.
---

# Results and Discussion

## Procedure

1. Delegate to `scientist`: analyze the contents of `data/processed/` (statistics, trends, anomalies relevant to the paper's claims).
2. Delegate to `writer`: draft `docs/sections/04-results.md` as an objective report of what the data shows — no interpretation here.
3. Delegate to `writer`: draft `docs/sections/05-discussion.md` interpreting the results, explicitly comparing against the "Closest Prior Work" column of `docs/notes/novelty-matrix.md`, and naming limitations.
4. Hand off both sections to `critic` through the `paper-supervise` loop, then stop for the section-draft-complete user gate.
