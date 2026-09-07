---
name: novelty-check
description: Compares this paper's claimed contributions against registered prior work to establish novelty, and separately estimates overlap with the author's own prior publications. Use after lit-review, before outline-draft.
---

# Novelty Check

## Three-stage novelty pipeline

1. **Extract claims** — take them from the Claims ledger in `docs/notes/story-brief.md`. That ledger is the paper's argument; the novelty matrix is the same claims measured against prior work, so the two must use the same `C<n>` identifiers.
2. **Retrieve and rank related work** — reuse `docs/notes/retrieved-sources.json`; run an additional `lit-review` pass if a claim has no close match yet.
3. **Structured comparison** — for each claim, fill one row of `docs/notes/novelty-matrix.md`:

   | Claim | Closest Prior Work | Key Difference |
   |---|---|---|
   | <C<n> from the story brief> | <source key from retrieved-sources.json> | <concrete delta, not "more novel"> |

   Every "Closest Prior Work" entry must be a `key` that exists in `docs/notes/retrieved-sources.json` — this table feeds `citation-manage` later.

## Self-redundancy check (separate from novelty)

If the user has prior publications on a related topic, list them and estimate, per claim, what percentage of the contribution overlaps with the user's own earlier work. Report this as a short paragraph appended to the bottom of `docs/notes/novelty-matrix.md` under a `## Self-Redundancy` heading — this is about duplicate-publication risk, not about novelty versus the field.

## When the gap is already filled

If the matrix shows a claim's "Key Difference" is empty or cosmetic, the `Gap`
slot in `docs/notes/story-brief.md` is wrong. Mark that claim `refuted`, rewrite
the `Gap`, and take it to the user as a narrative-revision gate. Do not proceed
to `outline-draft` on a gap the literature has already closed — that is the one
failure a later stage cannot repair.

## Handoff

Delegate the comparison work to the `scientist` agent and the structured write-up to `critic` for review, per the `paper-supervise` loop.
