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
status: approved
round: 1/3
last-critic-verdict: pass
last-critic-issues: Delegated adversarial critic subagent timed out after producing partial findings; the most substantive one (Reynolds grid mostly outside Ebert-Panchal's own fitted velocity range, so ~92% of points forced Rf_ep=0 by the correlation's own threshold behaviour) was verified and acted on directly: re-tuned re_min/re_max to 6800-29500 to match the source's 1.2-5.2 m/s Fig. 2 velocity range, re-ran (byte-reproducible), and confirmed by sensitivity check that the transcription gate still fires at both the old and new Re ranges (so the outcome is not an artifact of that choice) and by hand-recomputing the correlation at the source's own Fig. 4 benchmark point (Re=17100, Tf=503K, tau_w=7.2 Pa) that the coefficients are applied correctly. Capacity is matched exactly (0% gap, tighter than the preregistered 10% tolerance) because both arms share one 2-input MLPRegressor architecture grid. Split/Wilcoxon logic reviewed against Methods and matches: protected central-box interpolation-test/fit/val split, union-rule extrapolation set, paired seeds per repetition, exact one-sided signed-rank enumeration discarding zeros and averaging tied ranks. Result: C1 supported (black-box extrapolation RMSE 0.65 vs interpolation 0.22, ratio ~2.9x >= 1.5x); C0 adjudication suspended by the preregistered transcription/unit/input-mapping alarm (EP-only median extrapolation RMSE 5.28 far exceeds black-box's 0.65), attributed to a genuine mismatch between the threshold correlation's own suppression regime and the latent simulator's continuous accumulation, not a coding defect; C2/C3 therefore cannot be supported per the C0 contingency rule. Pending user review of this run and its interpretation before results-discussion/figures-tables may consume it.
preconditions:
- resolved: read and register Kennedy & O'Hagan (2001), "Bayesian Calibration of Computer Models", 10.1111/1467-9868.00294 - the origin of the y = eta(x) + delta(x) + eps form this hybrid is. Registered in docs/notes/retrieved-sources.json as abstract-only (full text is paywalled); DOI-verified online. Their weak-identifiability finding does not bind this fully simulated, known-noise-model benchmark (the discrepancy is directly computable from the recorded config rather than estimated under model-form uncertainty from field data), but is recorded as a limitation on external validity in the run manifest's kennedy_ohagan_note, to be carried into Discussion. [from lit-review round 2]
- resolved: record C0's Ebert-Panchal parameter provenance in the run manifest against the page or table it was verified on. data/processed/fouling-benchmark-2026-09-13.manifest.json's ebert_panchal_provenance field records the DOI, the open-access PDF used, the exact page/figure (Fig. 2 caption, printed page 844), the coefficients, and two independent visual (not pdftotext) transcriptions that agree with each other and with the earlier pdftotext reading. [from lit-review round 2]
- resolved: add a transcription-error sanity gate - if the residual-free correlation's RMSE exceeds the black-box's extrapolation RMSE, treat that as a transcription-error signal rather than as evidence for C0. Implemented in code/fouling_benchmark.py's decision logic and exercised: the gate fired on this run (EP median extrapolation RMSE 5.28 vs black-box 0.65), so C0 adjudication is suspended and C0 remains `assumed` per the preregistered precedence rule. The manifest's transcription_gate_result and sensitivity_check fields record why: the Reynolds grid was retuned to match the source's own 1.2-5.2 m/s fitted velocity range (an adversarial review of the first run had found the original 4000-60000 Re grid mostly outside that range), the gate still fires at both ranges, and a hand recomputation at the source's own Fig. 4 benchmark point confirms the coefficients are applied correctly - so this is reported as genuine threshold-fouling behaviour (deposition ~Re^-0.88 falling faster than the tau_w-based suppression term rises) rather than a bug. [from lit-review round 2]

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
