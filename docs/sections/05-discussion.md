# Discussion
<!-- claims: C1 -->

## What was measured, and what it implies

This benchmark measured, not assumed, that a purely data-driven surrogate's
extrapolation error grows sharply relative to its interpolation error on this
simulated fouling task (C1, supported: ratio ≈2.9× against the preregistered
1.5× bar, consistent in all 10 repetitions). It also measured that an
additive-residual hybrid built on a specific published correlation did not
improve on that black-box's extrapolation RMSE in this run — the hybrid was
worse in all 10 of 10 paired repetitions, not merely non-significantly better.
Whether that second measurement bears on the paper's central question —
whether embedding a physics-based fouling correlation improves extrapolation
— is exactly what C0's suspension leaves unresolved, and that distinction is
the one this section must not blur.

The transcription gate that suspended C0 fired because the residual-free
Ebert–Panchal correlation, evaluated at face value over an operating envelope
matched to its own fitted velocity range, predicts zero net fouling almost
everywhere in the protected central box (0% of central-box points) and at
90% of extrapolation-region points (i.e. a positive net rate at only 10.3%
of extrapolation-region points, per `ebert_panchal_coverage` in the run's
processed output). That is not a numerical error in this
implementation — coefficients were independently visually verified twice
against the source figure, and a hand check against the source's own
benchmark point reproduces a physically sensible rate — but it does mean the
correlation, as embedded here, supplies almost no informative signal over
most of this study's chosen envelope. C0 asks whether the simulator adds a
mechanism the correlation omits, which requires the correlation to be
predicting *something* nontrivial for the residual to have work to do beyond
that. With the correlation predicting uniformly zero in the interpolation
region, the additive-residual hybrid's residual target there collapses to
the same noisy signal the black-box already fits — which is exactly why the
two arms produced numerically identical interpolation RMSE in every
repetition. That is a design artifact of this particular Reynolds/temperature
envelope paired with this particular correlation, not evidence about
additive-residual hybrids in general, and not evidence against C0 — the
preregistered precedence rule treats this pattern as a signal to suspend
judgment rather than to decide C0 either way.

## Relation to closest prior work

`gallup2023physics` (per `docs/notes/novelty-matrix.md`) found its
residual hybrid only slightly ahead of an unmatched-capacity black-box on
extrapolation, and its loss-penalty PINN substantially ahead of both. This
run, on a different domain (shell-and-tube fouling resistance rather than
CSTR temperature) and with exactly matched capacity, found the additive
hybrid strictly behind the black-box on extrapolation in every paired
repetition — the opposite direction from Gallup et al.'s hybrid result, and
consistent with their finding that the *loss-penalty* family, not the
*additive-residual* family, was the strong performer in their setting. This
paper explicitly declined to test the loss-penalty alternative (see Methods,
"Deliberate exclusion of a feasible alternative"); nothing in this run
revisits that choice, but the direction of this result is a data point
consistent with, not contradicting, Gallup et al.'s comparative finding that
loss-penalty methods generalized better than additive-residual hybrids in
their setting. Neither result licenses a general claim that additive
residuals are inferior — this run's C0 suspension means the comparison here
is confounded with the specific correlation's near-zero predictions over
this envelope, exactly the kind of confound this paper's Related Work
identified as unresolved in the literature.

## Limitations

- **C0 is unresolved by this run, not merely uncertain.** The preregistered
  transcription/unit/input-mapping alarm suspends adjudication rather than
  refuting or supporting C0; a different, non-threshold correlation, or a
  Reynolds/temperature envelope chosen to keep the correlation informative
  across the whole grid rather than only the extrapolation tail, could
  produce a different outcome. This run does not distinguish "additive
  residuals do not help here" from "this specific correlation was
  uninformative over this specific envelope."
- **@kennedy2001bayesian's (2001) identifiability caveat is set aside by
  construction, not resolved.** In a fully simulated design with a known
  noise model, the discrepancy the hybrid must learn is computable directly
  from the recorded config, side-stepping the field-data identifiability
  problem their result describes. That does not establish that an
  additive-residual hybrid's discrepancy term is well identified when
  calibrated against real, non-simulated fouling data, which is the setting
  their result was derived for.
- **Simulation, not measurement.** All data are generated by the latent
  mechanistic simulator in `code/fouling_benchmark.py`, not measured fouling
  resistance; the benchmark's realism depends entirely on the simulator's
  induction-period and deposition/removal kinetics, which were chosen only
  to satisfy the preregistered induction-coverage and positive-range gates,
  not fit to any measured dataset.
- **Ten repetitions bound what can be claimed statistically.** The paired
  exact Wilcoxon test at this repetition count has limited power to detect a
  small true effect; the wrong-direction result reported here (0/10 wins,
  p = 1.0000 for the one-sided "hybrid below black-box" alternative) is
  strong evidence against a *large* hybrid advantage in this run, not proof
  that no advantage of any size exists.
- **Split geometry.** The union-rule extrapolation set is defined by either
  axis lying in an outer 20% tail; a different extrapolation geometry (e.g.
  a single-axis holdout, or a different tail fraction) was not tested and
  could change both the C1 ratio and the hybrid-versus-black-box comparison.
- **Capacity matching here means architectural identity**, not merely a
  10%-tolerance match: both arms used one shared architecture grid at every
  trial. This removes capacity as a confound entirely, but it also means the
  result says nothing about whether a hybrid with more distinct
  hyperparameter freedom than the black-box would perform differently.
- **The untested loss-penalty alternative remains untested here.** As
  Methods states, this design does not evaluate a loss-penalty formulation
  of the Ebert–Panchal ODE residual, which is the family the closest prior
  work found to generalize best.
