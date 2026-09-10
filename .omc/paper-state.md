# Paper State

## Stage: story-brief
status: approved
round: 3/3
last-critic-verdict: pass
last-critic-issues: round 3 verdict pass. Non-blocking polish deferred to later stages: (1) C2 falsifier should also trigger on <8/10 win-rate, not just the 10% median gap and p-value; (2) declare in the run manifest whether extrapolation RMSE is scored against noisy or clean targets; (3) mirror "contingent on C0" explicitly into C1's own text, not just C2/C3; (4) pin the additive-residual hybrid architecture in Approach once methods are chosen; (5) minor Gap phrasing tweak; (6) state explicitly that the Wilcoxon test pairs both models on the same 10 seeds.

## Stage: lit-review
status: in-progress
round: 1/3
last-critic-verdict: revise
last-critic-issues: round 1 verdict revise. BLOCKERS: (B1) the additive-residual structure has an unregistered canonical origin - Kennedy & O'Hagan 2001 "Bayesian Calibration of Computer Models" 10.1111/1467-9868.00294 introduced the y = eta(x) + delta(x) + eps form this hybrid is, and its delta-identifiability caveat bears on C0 and C2; also Willard et al. 10.1145/3514228 names "residual modeling" directly; (B2) Rogers et al. 2022 10.1016/j.bej.2022.108761 is listed unresolved but is open access; (B3) @mcbride2020hybrid is registered full-text while its "5 Hybrid Models" section - the load-bearing one for the claim it is cited for - was not traversed; (M1) the Gap is defended on system-specificity (CSTR vs shell-and-tube), which reads as salami-slicing; the stronger ground already in the note is evidential quality - @gallup2023physics is n=1, unpaired, capacity-matching unconfirmed; (M2) the Gap omits that the loss-penalty PINN generalized far better in that same study, i.e. the one cited precedent contradicts this paper's architecture choice, which needs an affirmative justification. NON-BLOCKING: (M3, required before code-experiment) record C0 parameter provenance as a precondition plus a transcription-error sanity gate, since mangled Ebert-Panchal parameters bias toward leaving C0 un-refuted; (M4) scope the Gap negative to the searches and date rather than asserting a universal negative while 10.1016/j.rineng.2026.112383 is unread; resolve Sansana et al. 2021; check 10.2139/ssrn.6837407; mark the @bonfanti2024generalization scope judgment provisional; refresh the stale Round-1 Gap paragraph. Critic noted approvingly: not registering ardsomang2013heat and dropping ikram2023comparative over corrupt metadata were both correct.

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
