---
name: story-brief
description: Fixes the paper's argument as six narrative slots plus a ledger of claims, each with its status, evidence, and falsifier, in docs/notes/story-brief.md. Use first, before lit-review, and again at the start of every later stage to re-check the argument against what the evidence now says.
---

# Story Brief

## Why this comes first

A paper fails at the argument, not the sentences. If "this is the problem →
prior work cannot do X → so we did Y → the result is Z → therefore W" does not
hold together, no amount of drafting saves it, and writing section by section
hides the break until the Discussion.

The brief is the argument on one page. Every later stage reads it before doing
anything, and writes back to it afterwards.

## What it is not

It is not a plan to be defended. It is a **hypothesis document**: when the
literature or the data contradicts a line, the line changes. Writing the story
first is only safe under that rule — otherwise `lit-review` degrades into
searching for confirmation and `results-discussion` into bending numbers to fit.

Three mechanisms enforce it:

- Every claim carries a `status`. An `assumed` claim may not be stated as fact
  in Results, Discussion, or Conclusion.
- Every claim carries a **falsifier**, written before the experiment: what result
  would force it to be rewritten.
- Every claim carries **evidence** that must resolve — a registered source key, a
  run manifest, or a figure in this paper.

## Procedure

1. Inventory what already exists before writing anything: `code/`, `data/raw/`,
   `data/processed/`, and `docs/sources/`. Most papers start from evidence the
   author already has — prior runs, an existing dataset, code already written
   — not from a blank slate. That is a normal starting point this brief must
   represent honestly, not a shortcut to hide. Existing evidence changes what
   the brief can say immediately (see "Basis" below); it does not exempt any
   claim from a falsifier or from evidence that resolves.
2. Delegate to `writer` (with `analyst` where the framing is unclear): fill the
   `Context`, `Gap`, and `Question` slots of `docs/notes/story-brief.md`. One
   sentence each. `Approach`, `Finding`, and `Implication` may be filled now if
   step 1 found existing code, data, or results that already answer them —
   otherwise leave them as placeholders; guessing them is what causes the
   story to drive the evidence.
3. List the load-bearing claims the paper will need, as `C1`, `C2`, … Each
   starts at `status: assumed` with an empty `Evidence` cell, and each gets a
   falsifier line and a `basis`:
   - `prospective` if the falsifier is written before the run/search that
     resolves the claim.
   - `retrospective` if the claim starts from evidence already in hand
     (step 1). Write the falsifier now, against that existing evidence — a
     condition it could still fail, not one it is already known to satisfy.
   A claim with no falsifier is not a claim, it is an opinion, regardless of
   basis.
4. Run the check:
   ```bash
   python scripts/verify_story_brief.py --require-slots Context,Gap,Question --registry docs/notes/retrieved-sources.json --sections "docs/sections/*.md"
   ```
5. Fill in `CLAUDE.md`'s **가제** from the `Question` slot. Leave **목표 학술지**
   until `Finding` exists — the size of the finding picks the venue, not the
   other way round.
6. Hand off to `paper-supervise` for the critic round, then the user-approval
   gate. The brief is a fixed gate: the user approves the argument before any
   literature search runs against it. For a claim marked `retrospective`, the
   critic checks the falsifier is a real condition the existing evidence
   could have failed, not a restatement of what it already shows.

## Revisiting the brief at each later stage

| Stage | What it writes back |
|---|---|
| `lit-review` | Sharpen `Gap` against what actually exists. Move claims to `supported` with `@key` evidence, or to `refuted`. |
| `novelty-check` | If the novelty matrix shows the `Gap` is already filled, the `Gap` sentence is wrong — rewrite it before drafting. |
| `outline-draft` | Map planned claims in the outline, then add declarations to the drafted Introduction/Related Work/Methods. Keep result sections as scaffold. Fill `Approach`. |
| `code-experiment` | Nothing yet — but check the planned runs can actually decide the falsifiers. If none can, the experiment is not answering the paper's question. |
| `results-discussion` | Fill `Finding` and `Implication` from `data/processed/`. Flip claim statuses with `run:<run-id>` evidence. A `refuted` claim means rewriting the narrative slot that rested on it. |
| `polish-review` | Run with `--require-slots all --require-coverage`. Every slot filled, every live claim carried by some section. |

## Rules

- Never change a claim's status without evidence that resolves. `supported` with
  a hand-waved justification is the same failure mode as a fabricated citation.
- `retrospective` basis changes when the falsifier was written, not what it
  takes to satisfy it — the same falsifier, evidence, and status rules apply
  as for a `prospective` claim. It exists to keep the ledger honest about
  order, not to grant a weaker claim.
- Never delete a `refuted` claim. It stays as a record of what the evidence did,
  and the verifier keeps it out of the sections.
- Never let the brief's `Finding` outrun `data/processed/`. If a run manifest
  does not exist, the finding is not a finding.
- Two sentences in one slot means the argument is not sharp enough yet. Split
  the paper or narrow the question — do not widen the slot.
