---
name: paper-supervise
description: Orchestrates the paper-writing pipeline via .omc/paper-state.md — figures out which stage is next, runs each stage's generate-then-review loop (max 3 rounds), and enforces the fixed user-approval gates instead of auto-passing. Use when starting work, resuming after a break, or asking "what's next".
---

# Paper Supervisor

## Stage order

1. `story-brief`
2. `lit-review`
3. `novelty-check`
4. `outline-draft`
5. `code-experiment` — produce or refresh the processed data needed by the manuscript
6. `results-discussion`, `figures-tables` (parallel after `code-experiment` is approved)
7. `citation-manage`
8. `polish-review`
9. `submission-manage` — venue selection, submission, and every editorial decision after it

Stages 1-8 produce the manuscript; stage 9 repeats for as long as the paper is in review. A rejection sends specific stages back to `in-progress`, and every downstream approval becomes stale until the reopened stage is approved again.

## On invocation

1. Read `docs/notes/story-brief.md` before anything else and restate the `Question` slot in your first message. Every stage below serves that one sentence; a stage whose output does not move a claim in the brief's ledger is off course. Validate it with:
   ```bash
   python scripts/verify_story_brief.py --state .omc/paper-state.md --brief docs/notes/story-brief.md --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json
   ```
   This is what keeps a long drafting run from drifting: it fails when a section carries a claim that is not in the ledger, when a `refuted` claim is still being argued, or when Results/Discussion/Conclusion assert a claim that is still `assumed`. At `polish-review`, add `--require-slots all --require-coverage`.
2. Run `python scripts/check_paper_state.py --state .omc/paper-state.md`. If it reports errors, stop and show them to the user before doing anything else. Repair only deterministic format/order errors; never guess research decisions or approvals.
3. Before completing `lit-review` or starting `citation-manage`, run `python scripts/verify_source_registry.py --registry docs/notes/retrieved-sources.json --online`. This resolves each DOI (Crossref, falling back to DataCite for arXiv and Zenodo), matches titles, and screens against Crossref's Retraction Watch feed. Stop and quarantine any source that fails — a retracted source is a hard stop, not a warning. A source reported as `awaiting-user-file` is a request to relay: give the user the key, title, DOI, and the exact `docs/sources/` path, and wait for the file rather than proceeding on the abstract.
4. Once `code-experiment` is `approved`, run `python scripts/rerun_manifest.py --all` before any stage that consumes its output. `--check-manifests` proves the manifest is well formed; only the re-run proves the result reproduces, and `results-discussion`, `figures-tables` and the submission preflight all rest on that. A run that no longer reproduces reopens `code-experiment` — it does not become a caveat in Discussion.
5. Once `polish-review` is `approved`, also run `python scripts/check_submissions.py --log submissions/submission-log.md` and report the open attempt's venue and status. If an attempt is `submitted` or `under-review`, the paper is with a venue and the only valid work is answering a decision — do not open a new attempt.
6. Read `.omc/paper-state.md` and find the first eligible stage whose prerequisites are approved and whose `status` is not `approved`. This means `code-experiment` is selected before `results-discussion` or `figures-tables`; `results-discussion` and `figures-tables` may proceed in either order after `code-experiment` is approved; `citation-manage` waits for both; and `polish-review` waits for `citation-manage`. If the first non-approved eligible stage is `awaiting-user` or `escalated`, surface it and stop instead of generating more work.
7. Report that stage and its current `status`/`round` to the user, then proceed per the loop below. For `awaiting-review`, review the already generated artifact without generating it again or incrementing the round. When every manuscript stage is approved, route to `submission-manage` using its own ledger; it is not an extra stage block in `paper-state.md`.

## Generate-then-review loop (per stage)

1. If the stage is `not-started`, set it to `in-progress`. If the round is already `3/3` and a new attempt is needed, set `escalated` and stop. Otherwise increment `round` exactly once before generation, including attempts triggered by user rejection. Clear the old verdict. After generation set `awaiting-review`; a resumed review uses that artifact and round.
2. Delegate generation to `writer` (with `analyst` for framing), `scientist` for literature/analysis, `executor` for code/figures, or `verifier` for citations. `outline-draft` writes only the outline and Introduction/Related Work/Methods before experiments. Results, Discussion and Conclusion remain scaffold until `results-discussion` has approved experiment outputs.
3. Delegate review to `critic` (or `verifier` for `citation-manage`) using this rubric — record the verdict and any issues back into the stage's `last-critic-verdict` / `last-critic-issues` fields:
   - novelty/significance
   - technical soundness
   - clarity
   - prior-work coverage
   - concrete revision suggestions
4. If the verdict is `pass`: set `status: awaiting-user` and stop — do not proceed automatically, even though the critic passed.
5. If the verdict is `revise` and `round` is below `3/3`: fold the issues into the next generation attempt and go back to step 1.
6. If `round` is `3/3` and the verdict is still `revise`: set `status: escalated`, stop, and report the unresolved issues to the user verbatim. Never set `status: approved` automatically and never loop past round 3.
7. When the user reviews an `awaiting-user` stage: if they approve, set `status: approved` and move to the next eligible stage. If they reject, append their feedback to `last-critic-issues`; at `3/3` set `escalated`, otherwise set `in-progress` and go back to step 1. Never infer user approval from a critic pass.

## Reopening work

Before changing an approved artifact, record the reason and previous decisions in
`docs/notes/revision-log.md` (create it on first use). Set the earliest affected
stage to `in-progress`, `round: 0/3`, blank verdict. Reset every transitive
dependent in `scripts/check_paper_state.py`'s `STAGE_DEPENDENCIES` to `not-started`,
`round: 0/3`, blank verdict; keep unaffected branches approved. Save these changes
together before validating state. Existing artifacts remain available for revision,
but prior approvals no longer authorize their downstream use. An exhausted loop
requires the user's resolution before starting a new cycle; an automatic reset
must not bypass the three-attempt limit.

## Fixed user-approval gates

Regardless of critic verdict, always stop for explicit user sign-off at:
- story brief complete (`story-brief` stage, before any literature search runs against it — approving the argument is what makes the rest of the pipeline meaningful)
- narrative revision (`story-brief`, whenever evidence refutes a claim and a narrative slot has to be rewritten — the user decides whether the paper changes shape or the claim is dropped)
- outline complete (`outline-draft` stage, before drafting any section)
- each section draft complete (`outline-draft` / `results-discussion` stages)
- citations finalized (`citation-manage` stage, before any `refs/references.bib` edit is treated as final)
- final polish (`polish-review` stage)
- submission (`submission-manage`, before the manuscript goes to a venue — the user submits, never the agent)
- venue change (`submission-manage`, after a rejection — the user picks the next venue)
