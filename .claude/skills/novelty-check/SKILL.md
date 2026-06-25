---
name: novelty-check
description: Compares this paper's claimed contributions against registered prior work to establish novelty, and separately estimates overlap with the author's own prior publications. Use after lit-review, before outline-draft.
---

# Novelty Check

## Three-stage novelty pipeline

1. **Extract claims** — list this paper's claimed contributions (from the working draft of `docs/outline.md` or the user's description).
2. **Retrieve and rank related work** — reuse `docs/notes/retrieved-sources.json`; run an additional `lit-review` pass if a claim has no close match yet.
3. **Structured comparison** — for each claim, fill one row of `docs/notes/novelty-matrix.md`:

   | Claim | Closest Prior Work | Key Difference |
   |---|---|---|
   | <contribution> | <source key from retrieved-sources.json> | <concrete delta, not "more novel"> |

   Every "Closest Prior Work" entry must be a `key` that exists in `docs/notes/retrieved-sources.json` — this table feeds `citation-manage` later.

## Self-redundancy check (separate from novelty)

If the user has prior publications on a related topic, list them and estimate, per claim, what percentage of the contribution overlaps with the user's own earlier work. Report this as a short paragraph appended to the bottom of `docs/notes/novelty-matrix.md` under a `## Self-Redundancy` heading — this is about duplicate-publication risk, not about novelty versus the field.

## Handoff

Delegate the comparison work to the `scientist` agent and the structured write-up to `critic` for review, per the `paper-supervise` loop.
