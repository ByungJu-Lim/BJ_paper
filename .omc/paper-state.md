# Paper State

## Stage: story-brief
status: approved
round: 3/3
last-critic-verdict: pass
last-critic-issues: round 3 verdict pass. Non-blocking polish deferred to later stages: (1) C2 falsifier should also trigger on <8/10 win-rate, not just the 10% median gap and p-value; (2) declare in the run manifest whether extrapolation RMSE is scored against noisy or clean targets; (3) mirror "contingent on C0" explicitly into C1's own text, not just C2/C3; (4) pin the additive-residual hybrid architecture in Approach once methods are chosen; (5) minor Gap phrasing tweak; (6) state explicitly that the Wilcoxon test pairs both models on the same 10 seeds.

## Stage: lit-review
status: approved
round: 3/3
last-critic-verdict: pass
last-critic-issues: round 3 verdict pass. All five Gap assertions about @gallup2023physics re-verified line by line against the DOE accepted manuscript. Carried to novelty-check (not a lit-review blocker): tighten "nothing addresses shell-and-tube fouling resistance at all" to "no such comparison addresses shell-and-tube fouling resistance" - read literally the current wording is contradicted by our own registry (@he2025machine, and ikram2023comparative which was read but dropped for corrupt Crossref metadata); and clear the stale round-1 paragraph in the topic note that still says the Gap cites all three original sources. Owed at outline-draft/code-experiment: a genuine comparative reason for choosing additive-residual over a loss penalty. Two rounds produced two failed reasons - the "not a PDE" argument (refuted by the ODE it writes) and the "loss penalty changes the objective rather than the capacity" argument (reversed: a loss penalty leaves the architecture untouched, so @gallup2023physics's loss model and baseline are the same six-layer 20-node network, matched by construction, while the architectural hybrid is the one whose capacity drifted). The note now says only that capacity matching is tractable FOR additive-residual, which is true but is not a preference argument, and marks the comparative reason as still owed. Do not import the round-3 commit message's phrase "in the hybrid's disfavour" into the manuscript: smaller capacity is not monotonically worse for extrapolation and the hybrid is not capacity-starved in range (0.80% vs 0.85%), so the direction is undetermined and "confounds capacity with effect" is the defensible claim. Carried risks unchanged per user direction: Kennedy & O'Hagan, Rogers 2022, @mcbride2020hybrid section 5, M3 C0 parameter provenance, 10.1016/j.rineng.2026.112383 unread.

## Stage: novelty-check
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: outline-draft
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: code-experiment
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: results-discussion
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: figures-tables
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:

## Stage: citation-manage
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:
verified-sources: 0
rejected-citations:

## Stage: polish-review
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:
