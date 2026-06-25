---
name: paper-supervise
description: Orchestrates the paper-writing pipeline via .omc/paper-state.md — figures out which stage is next, runs each stage's generate-then-review loop (max 3 rounds), and enforces the 4 fixed user-approval gates instead of auto-passing. Use when starting work, resuming after a break, or asking "what's next".
---

# Paper Supervisor

## Stage order

1. `lit-review`
2. `novelty-check`
3. `outline-draft`
4. `results-discussion`, `code-experiment`, `figures-tables` (any order, once `code/` has produced `data/processed/`)
5. `citation-manage`
6. `polish-review`

## On invocation

1. Run `python scripts/check_paper_state.py --state .omc/paper-state.md`. If it reports errors, stop and show them to the user before doing anything else — the state file is corrupted and must be fixed by hand first.
2. Read `.omc/paper-state.md` and find the first stage (in the order above) whose `status` is not `approved` (an `escalated` stage surfaces here too — the user must resolve it before the pipeline continues).
3. Report that stage and its current `status`/`round` to the user, then proceed per the loop below.

## Generate-then-review loop (per stage)

1. Delegate generation to the agent listed for that stage in `CLAUDE.md`'s workflow table (`scientist` for `lit-review`/analysis, `writer` for drafting, `executor` for code/figures, `verifier` for citations).
2. Delegate review to `critic` (or `verifier` for `citation-manage`) using this rubric — record the verdict and any issues back into the stage's `last-critic-verdict` / `last-critic-issues` fields:
   - novelty/significance
   - technical soundness
   - clarity
   - prior-work coverage
   - concrete revision suggestions
3. If the verdict is `pass`: set `status: awaiting-user` and stop — do not proceed automatically, even though the critic passed.
4. If the verdict is `revise`: increment `round`, fold the issues into the next generation attempt, go back to step 1.
5. If `round` reaches `3/3` and the verdict is still `revise`: set `status: escalated`, stop, and report the unresolved issues to the user verbatim. Never set `status: approved` automatically and never loop past round 3.
6. When the user reviews an `awaiting-user` stage: if they approve, set `status: approved` and move to the next stage. If they reject, go back to step 1 with their feedback as an additional issue.

## Fixed user-approval gates

Regardless of critic verdict, always stop for explicit user sign-off at:
- outline complete (`outline-draft` stage, before drafting any section)
- each section draft complete (`outline-draft` / `results-discussion` stages)
- citations finalized (`citation-manage` stage, before any `refs/references.bib` edit is treated as final)
- final polish (`polish-review` stage)
