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

## Reporting review

The statistical design was reviewed in `code-experiment`, before the numbers
existed. This pass checks that the write-up reports what that design actually
produced.

| Check | Failure it catches |
|---|---|
| Every number in the prose traces to a run manifest, and the run reproduces (`python scripts/rerun_manifest.py --all`) | A figure quoted from a superseded run |
| Effect sizes are reported with the test, not a p-value alone | "Significant" with no magnitude is not a result |
| The interval reported is named (SD, SE, CI, IQR) and its repetition count stated | An unnamed ± is uninterpretable |
| Every comparison the design ran appears, including the ones that went the wrong way | Selective reporting, which is what makes the surviving p-value meaningless |
| A `refuted` claim is reported as a negative result in its own right, not quietly dropped or restated more weakly | Rewriting the hypothesis around the answer |
| No claim still `assumed` is stated in the indicative in Results, Discussion, or Conclusion | The validator catches the declaration; only a reader catches the sentence |
| Discussion separates what was measured from what it implies, and marks which is which | Implication presented as finding |
| Limitations name the design choices that bound the claim (simulation vs. measured data, split rule, seed count), not generic caveats | "More work is needed" is not a limitation |
| The Conclusion claims no more than the Results section established | Where papers most often overreach |

An item that fails is a `revise` verdict. If a number cannot be traced to a
manifest, the fix is to re-run the experiment, not to soften the sentence.
