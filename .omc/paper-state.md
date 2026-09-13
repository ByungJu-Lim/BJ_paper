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
status: approved
round: 3/3
last-critic-verdict: pass
last-critic-issues: round 3 verdict pass. The matrix now distinguishes component sources from structural hybrid precedent for C0, explains the closest-work choice for C1, preserves @gallup2023physics's partly negative loss-penalty result for C2, and reports self-redundancy as not yet assessable without author-specific evidence.
preconditions:
- resolved: tighten the Gap's trailing clause - "nothing addresses shell-and-tube fouling resistance at all" is true only on the anaphoric reading; read literally our own registry contradicts it (@he2025machine trains surrogates on CFD-simulated shell-and-tube fouling data, and ikram2023comparative compares models for shell-and-tube fouling resistance directly). Replaced with "and no such comparison addresses shell-and-tube fouling resistance." [from lit-review round 3]
- resolved: clear the stale round-1 paragraph in docs/notes/ml-fouling-prediction-shell-tube.md that still says the Gap cites all three original sources; the rewritten Gap cites only @gallup2023physics. [from lit-review round 3]

## Stage: outline-draft
status: approved
round: 1/3
last-critic-verdict: pass
last-critic-issues: Stage-level package review round 1 verdict pass. All four artifacts cohere: Introduction/Related Work/Methods claim declarations match story-brief's section-coverage mapping, numeric thresholds and Gallup figures are stated identically across sections, Results/Discussion/Conclusion remain scaffolds, and code-experiment's three open preconditions (Kennedy & O'Hagan registration, parameter provenance, transcription gate) are correctly left open rather than resolved prematurely. Pending final user approval of the outline-draft stage before code-experiment begins.
preconditions:
- resolved: supply a comparative reason for choosing additive-residual over a loss penalty, and pin it in the Approach slot. Additive-residual is selected on scope, estimand, and falsifiability grounds—not because it is generally superior or easier to capacity-match—because it decomposes prediction into an explicit mechanistic term and a removable learned discrepancy for C0's falsifier. The two rejected arguments remain rejected. [from lit-review round 3]
- resolved: state in the manuscript that a loss-penalty variant on the Ebert-Panchal ODE residual is a feasible alternative deliberately not taken. The Approach acknowledges it as feasible but outside this estimand and retains @gallup2023physics's substantially better loss-penalty extrapolation result as negative precedent. [from lit-review round 3]
artifacts:
- outline: approved, round 3/3, verdict pass
- introduction: approved, round 2/3, verdict pass
- related-work: approved, round 1/3, verdict pass
- methods: approved, round 1/3, verdict pass

## Stage: code-experiment
status: not-started
round: 0/3
last-critic-verdict:
last-critic-issues:
preconditions:
- open: read and register Kennedy & O'Hagan (2001), "Bayesian Calibration of Computer Models", 10.1111/1467-9868.00294 - the origin of the y = eta(x) + delta(x) + eps form this hybrid is. Their result that the discrepancy term is weakly identifiable and that identification degrades away from the calibration region bears directly on C0 ("the residual term has real work to do") and on C2's extrapolation premise. Whether it binds under a fully simulated, known-noise design is open and must not be assumed either way. [from lit-review round 2]
- open: record C0's Ebert-Panchal parameter provenance in the run manifest against the page or table it was verified on. The values in the topic note came from pdftotext and show mangled scientific notation. [from lit-review round 2]
- open: add a transcription-error sanity gate: C0's falsifier is biased toward confirming C0, because mangled parameters make the residual-free correlation predict worse, which raises its extrapolation RMSE, which is the direction that leaves C0 un-refuted. If the residual-free correlation's RMSE exceeds the black-box's extrapolation RMSE, treat that as a transcription error rather than as evidence for C0. [from lit-review round 2]

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
