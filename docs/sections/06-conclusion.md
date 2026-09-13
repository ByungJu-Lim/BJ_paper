# Conclusion
<!-- claims: C1 -->

This benchmark asked whether embedding a published physics-based fouling
correlation inside a machine-learning surrogate lowers extrapolation error
relative to a capacity-matched, purely data-driven model, for shell-and-tube
fouling resistance under a controlled synthetic design. Within that design,
the black-box surrogate's extrapolation error was measurably, consistently
worse than its interpolation error (C1, supported: ≈2.9× the preregistered
1.5× bar, in all 10 repetitions), confirming that this benchmark poses a
genuine extrapolation challenge rather than a trivial one.

Whether an additive-residual hybrid meets that challenge better is not
settled by this run. The preregistered transcription/unit/input-mapping
alarm fired: the independently verified Ebert–Panchal correlation predicted
essentially zero fouling across the training envelope and most of the
extrapolation region, so the hybrid's discrepancy term reduced to fitting
the same noisy target the black-box already fits. C0 — that the embedded
correlation and the simulator are independent enough for the residual term
to have real work to do — is therefore left `assumed`, not decided, and C2
and C3 cannot be reported as supported or refuted under the preregistered
contingency rule. The hybrid was numerically worse than the black-box on
extrapolation in every one of the 10 paired repetitions and identical to it
on interpolation; both observations are reported as data, and neither
licenses a claim about additive-residual hybrids in general, because the
correlation's near-zero predictions over this envelope confound the
comparison exactly as C0's suspension flags.

The principal next comparison this evidence suggests is not a larger or
differently tuned hybrid on the same setup, but a redesign that keeps the
embedded correlation informative (nonzero) across the training envelope —
either by choosing an operating envelope matched to a regime where the
correlation predicts appreciable fouling throughout, or by selecting a
different published correlation for which that holds — so that C0 can
actually be adjudicated rather than suspended. Testing the loss-penalty
alternative this paper deliberately excluded, given that the closest prior
work found that family to generalize better than additive residuals, is a
second natural next step.
