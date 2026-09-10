# Paper State

## Stage: story-brief
status: approved
round: 3/3
last-critic-verdict: pass
last-critic-issues: round 3 verdict pass. Non-blocking polish deferred to later stages: (1) C2 falsifier should also trigger on <8/10 win-rate, not just the 10% median gap and p-value; (2) declare in the run manifest whether extrapolation RMSE is scored against noisy or clean targets; (3) mirror "contingent on C0" explicitly into C1's own text, not just C2/C3; (4) pin the additive-residual hybrid architecture in Approach once methods are chosen; (5) minor Gap phrasing tweak; (6) state explicitly that the Wilcoxon test pairs both models on the same 10 seeds.

## Stage: lit-review
status: awaiting-review
round: 3/3
last-critic-verdict:
last-critic-issues: round 2 verdict revise. M1's framing fix accepted (the Gap now rests on evidential quality), but two facts asserted about @gallup2023physics are wrong against its own text, which the critic settled by retrieving the DOE accepted manuscript: (B1) "no repeated seeds" is false - it trains each model twenty times and Table 1's in-range column is an average, though whether the out-of-range column is a single case or an average is unstated; (B2) "capacity matching unconfirmed" is confirmable and cuts the other way - the hybrid gets 5-node hidden layers against the baseline's six layers of twenty, so capacity is uncontrolled in the hybrid's disfavor rather than unknown; (B3) "and for the structure generally" enlarges the universal negative that M4 asked to narrow, while the 2026 systematic review stays unread; (B4) the note's affirmative justification is refuted by its own equation - dRf/dt = a1*Re^b1*exp(-Ea/(R*Tf)) - c1*tau_w is an ODE, so a loss penalty on its residual is perfectly available and "no governing equation to enforce" is not a real obstacle; the capacity-countability half of that argument survives and suffices. NON-BLOCKING: the power criticism should not lean on repetition count, since this paper commits to 10 repetitions and the precedent ran 20 - the defensible axes are the paired test and matched capacity; the Gap calls @gallup2023physics an additive-residual precedent while the model it builds is series conjunction plus a residual-estimation layer, a qualifier the note keeps and the Gap compresses away; carried risks B1 Kennedy & O'Hagan, B2 Rogers, B3 mcbride section 5, M3 C0 parameter provenance all remain open as the user directed. Critic noted approvingly that the carried risks are recorded honestly and are actionable cold.

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
