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

1. Delegate to `writer` (with `analyst` where the framing is unclear): fill the
   `Context`, `Gap`, and `Question` slots of `docs/notes/story-brief.md`. One
   sentence each. Leave `Approach`, `Finding`, and `Implication` as placeholders
   — they are not knowable yet, and guessing them is what causes the story to
   drive the evidence.
2. List the load-bearing claims the paper will need, as `C1`, `C2`, … Each
   starts at `status: assumed` with an empty `Evidence` cell, and each gets a
   falsifier line. A claim with no falsifier is not a claim, it is an opinion.
3. Run the check:
   ```bash
   python scripts/verify_story_brief.py --require-slots Context,Gap,Question \
     --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md
   ```
4. Fill in `CLAUDE.md`'s **가제** from the `Question` slot. Leave **목표 학술지**
   until `Finding` exists — the size of the finding picks the venue, not the
   other way round.
5. Hand off to `paper-supervise` for the critic round, then the user-approval
   gate. The brief is a fixed gate: the user approves the argument before any
   literature search runs against it.

## Revisiting the brief at each later stage

| Stage | What it writes back |
|---|---|
| `lit-review` | Sharpen `Gap` against what actually exists. Move claims to `supported` with `@key` evidence, or to `refuted`. |
| `novelty-check` | If the novelty matrix shows the `Gap` is already filled, the `Gap` sentence is wrong — rewrite it before drafting. |
| `outline-draft` | Add a `<!-- claims: C1, C3 -->` line under each section heading, mapping the argument onto the structure. Fill `Approach`. |
| `code-experiment` | Nothing yet — but check the planned runs can actually decide the falsifiers. If none can, the experiment is not answering the paper's question. |
| `results-discussion` | Fill `Finding` and `Implication` from `data/processed/`. Flip claim statuses with `run:<run-id>` evidence. A `refuted` claim means rewriting the narrative slot that rested on it. |
| `polish-review` | Run with `--require-slots all --require-coverage`. Every slot filled, every live claim carried by some section. |

## Rules

- Never change a claim's status without evidence that resolves. `supported` with
  a hand-waved justification is the same failure mode as a fabricated citation.
- Never delete a `refuted` claim. It stays as a record of what the evidence did,
  and the verifier keeps it out of the sections.
- Never let the brief's `Finding` outrun `data/processed/`. If a run manifest
  does not exist, the finding is not a finding.
- Two sentences in one slot means the argument is not sharp enough yet. Split
  the paper or narrow the question — do not widen the slot.
