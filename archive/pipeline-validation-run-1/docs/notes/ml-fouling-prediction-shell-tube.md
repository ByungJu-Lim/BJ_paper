# Lit-review note: ML fouling-resistance prediction in shell-and-tube heat exchangers

## Registered sources, black-box side (read at `abstract-only`)

- **@he2025machine** — He, Ye, Wang, Zhang, Tian, Qiu, Su (2025), *Nuclear Engineering and Design*. Trains four purely data-driven networks (BPNN, PSO-BPNN, CNN, RBFNN) on CFD-simulated shell-and-tube fouling data (steam-generator case) to build a fast surrogate. CFD is used only to *generate* training data — no physics-based correlation is embedded inside the learned model itself, so this is a non-hybrid, black-box approach in our sense. The abstract does not report an explicit interpolation-vs-extrapolation split; robustness there is checked via noise sensitivity. (Abstract-only: this describes what the abstract states, not a full-text-confirmed absence — the full paper could still report such a split.)
- **@hosseini2022novel** — Hosseini, Khandakar, Chowdhury, Ayari, Rahman, Chowdhury, Vaferi (2022), *Energy Reports*. Compares Gaussian Process Regression, Decision Trees, Bagged Trees, Support Vector Regression, and Linear Regression for estimating heat-exchanger fouling factor from operating/construction variables; GPR wins. Again a purely data-driven comparison among ML families; the abstract does not mention an embedded physics correlation or an interpolation/extrapolation split. (Abstract-only, same caveat as above.)

## Registered source, physics-informed side (read at `full-text`)

- **@jadhav2022physics** — Jadhav, Deodhar, Gupta, Runkana (2022), *PHM Society European Conference*, DOI `10.36001/phme.2022.v7i1.3343`, full PDF read. A PINN predicts internal temperature fields of a **rotary air preheater** (a different exchanger geometry from shell-and-tube) by enforcing the governing heat-transfer PDEs as **loss-function penalties** (Eqs. 20-25: MSE terms for PDE residuals, boundary/interface conditions) — not by embedding a closed-form fouling correlation as an additive structural prior. Fouling propensity is then computed from the PINN's predicted temperatures using a separate, non-learned empirical formula (Chen et al. 2020's R-number, Eq. 27) — the ML model does not predict fouling resistance directly. No purely data-driven (non-physics) baseline is compared for the temperature-field task; the comparisons that exist are PINN vs. numerical finite-difference solver, and PINN-from-scratch vs. transfer-learned PINN. The 9 boundary-condition cases in Table 2 are each given their own transfer-learned model — there is no held-out extrapolation test where a single model is evaluated on conditions it never saw. This is architecturally the mechanism the Gap needed a real example of: a genuine physics-informed approach to heat-exchanger fouling monitoring that is *not* an additive-residual hybrid and does *not* test extrapolation.

## Relation to the paper's Gap

The registered evidence now covers both sides the Gap needs to distinguish: the purely-data-driven side (@he2025machine, @hosseini2022novel — no physics, no reported extrapolation split) and one genuine physics-informed side (@jadhav2022physics — physics via loss penalty, different target and geometry, no extrapolation split). None of the three is an additive-residual hybrid predicting fouling resistance directly with an explicit interpolation-vs-extrapolation comparison on shell-and-tube exchangers. The Gap in `docs/notes/story-brief.md` cites only @gallup2023physics as the directly relevant precedent; @he2025machine and @ikram2023comparative (read but dropped for corrupt Crossref metadata) show that shell-and-tube fouling resistance *is* studied by ML surrogates, just not in a matched-capacity extrapolation comparison of the kind this paper runs.

## Open risk — not yet resolved

A search hit surfaced a closely-adjacent paper we could **not** read: *"Machine learning for heat exchanger fouling prediction: A systematic review of hybrid and non-hybrid approaches for model selection"* (ScienceDirect, PII `S2590123026034018`, apparently a 2026 review synthesizing 43 studies 2016-2026). Search-engine snippets describe it as concluding "hybrid models do not consistently outperform standalone approaches" - but this is a third-party paraphrase, not text we have actually read, and per project rule we cannot rely on it or fold it into the ledger without reading the source. `WebFetch` was blocked (HTTP 403) and no open-access copy was found. **Not registered** in `retrieved-sources.json` - doing so on a paraphrase would violate the "read before registering" rule.

This paper matters more than a typical unread hit: if its "hybrid" category matches our definition (an embedded physics correlation + learned residual) and it already reports extrapolation-specific comparisons, our Gap sentence could be wrong. If "hybrid" there means something looser (e.g., ANN+PSO, ANFIS - combining ML techniques or optimizers, not ML+physics), it doesn't touch our Gap at all. We cannot tell without the full text.

**Action needed from the user:** either (a) supply `docs/sources/<key>.pdf` for this review (DOI not yet resolved - the ScienceDirect PII didn't come with one from the searches run; would need to look it up via institutional access or Crossref search by title), or (b) accept proceeding to `novelty-check` with this flagged as an open risk to revisit before the Gap is treated as final.

## Deferred — C0's embedded correlation

`story-brief.md`'s C0 requires the hybrid's embedded correlation to be a specific published, registered fouling correlation. A strong candidate was found — **Coletti & Macchietto (2011), "A Dynamic, Distributed Model of Shell-and-Tube Heat Exchangers Undergoing Crude Oil Fouling,"** *Ind. Eng. Chem. Res.*, DOI `10.1021/ie901991g` — a highly-cited, shell-and-tube-specific, physics-based fouling model validated against a year of refinery data. Full text is paywalled (ACS, 403 on fetch); only a third-party paraphrase of the abstract was obtainable, which is not sufficient to register it or commit to it as C0's correlation. Picking the exact correlation is properly an `outline-draft`/`code-experiment`-stage decision (the Approach slot, still correctly blank) rather than a `lit-review` one — recorded here so the choice isn't made blind when that stage starts. If institutional access to this paper (or a similarly strong open-access alternative, e.g. `hatte2022generalized`, `coletti2011dynamic`'s companion OA conference version at heatexchanger-fouling.com) becomes available, read and register it before C0 is exercised in `code-experiment`.

## Also dropped

- `ikram2023comparative` (Ikram et al., *Research on Engineering Structures and Materials*, 2023) was found and read at abstract level (FNN-MLP vs NARX vs SVM-RBF for shell-and-tube fouling resistance - another purely data-driven comparison, consistent with the Gap) but its Crossref record has corrupted author metadata (institutional-affiliation strings interleaved into the author list), which fails `verify_source_registry.py`'s exact-match check and cannot be cleanly resolved. Dropped rather than force a match against bad data. Could be re-added later if the publisher's Crossref record is corrected, or by attaching a manual correction note if the project adds one.

---

# Round 2 of lit-review (2026-09-10) — C0 correlation, and the "PINN-only" search blind spot

The first cycle registered three sources and searched the hybrid structure almost
entirely under the term *PINN*. Two things came out of widening it.

## C0's correlation now has a source (`full-text`)

- **@wilson2017twenty** — Wilson, Ishiyama, Polley (2017), *Heat Transfer Engineering* 38(7-8),
  DOI `10.1080/01457632.2016.1206407`; read via the open-access Cambridge Apollo deposit of the
  accepted manuscript (`10.17863/cam.13048`). Writes the **Ebert-Panchal threshold fouling model**
  out explicitly as deposition minus suppression,
  `dRf/dt = a1 * Re^b1 * exp(-Ea/(R*Tf)) - c1 * tau_w`,
  whose operating-condition inputs are exactly the two axes of our simulator design
  (Reynolds number and film temperature). It also tabulates regressed parameter sets for
  several published variants (Panchal et al., Polley et al., Yeap et al., Nasr & Givi,
  Yang & Crittenden), and records that Ebert and Panchal designed the model to support both
  extrapolation to the zero-fouling threshold and interpolation between measured conditions.
  This satisfies the first half of C0: a published literature correlation, chosen independently
  of any simulator we build.

  **Caveat, load-bearing:** the numeric parameter values were extracted by `pdftotext` and
  show signs of mangled scientific notation. They must be re-read off the source page before
  any of them is hard-coded in `code/`. Do not copy them from this note.

  The true primary source — Ebert & Panchal, *"Analysis of Exxon crude-oil-slip stream coking
  data"*, ANL/ES/CP-92175, 1995 — sits behind a bot-check at the UNT Digital Library and was not
  retrieved. We currently cite a review's transcription of the equation rather than the original.

- **@yang2020computational** — Yang (2020), *Int. J. Heat and Mass Transfer* 159:120129, full text read.
  3D CFD of the **induction period** of crude-oil fouling, separating reaction-driven from
  precipitation-driven mechanisms. This supplies the second half of C0: a citable mechanism the
  Ebert-Panchal form omits, so the residual term has real work to do.

- **@deshannavar2021revisiting** (abstract-only) records a known criticism of the threshold form —
  some crude oils foul *less* at higher temperature, against the Arrhenius term, and the physical
  reading of "activation energy" absorbing a velocity effect is questionable. A limitations citation.

- **@coletti2011dynamic** (abstract-only) is now registered: a dynamic, distributed **shell-and-tube**
  crude-oil fouling model validated against a year of refinery data. Approach-slot support for the
  simulator being a defensible stand-in, not a C0 correlation (it is a whole model, not a closed form).
  Same for **@dazbejarano2016new** (abstract-only), a multicomponent reactive-deposit successor.

## The Gap does not survive unchanged

Searching *gray-box* / *semi-parametric* / *hybrid submodeling* / *residual physics* instead of
*PINN* found the additive-residual structure published widely, and found one direct precedent.

- **@gallup2023physics** — Gallup, Gallup, Powell (2023), *Computers & Chemical Engineering*, full text read.
  This is the finding that matters. It taxonomizes physics-guided NNs into physics-guided loss,
  physics-guided architecture, **conjunction** (explicitly including *parallel conjunction*, which it
  names "residual physics"), and physics-guided initialization. It then builds four surrogates for a
  **CSTR**, trains them on an inlet-temperature window of 400-420 C, and tests them **outside that
  window at 430-450 C**, reporting each model's percent-error increase against a black-box baseline.
  Its result runs against our C2 premise: the architecture-plus-conjunction model (series physics
  followed by a residual-estimation layer — the closest published analog to our hybrid) generalized
  only *slightly* better than the baseline, while the pure loss-penalty PINN generalized far better.
  Single trial, different domain, no repeated seeds and no paired test — but it is a real prior
  evaluation of a residual hybrid against a black-box under an explicit extrapolation split.
- **@bradley2022perspectives** (full text, Sections 1-3 read) separates **"Hybrid Submodeling"** —
  additive models of separate physical and data-driven equations — from physics-informed ML as
  distinct hybridization families. Exactly the taxonomic distinction our Gap sentence needs to make.
  It cites a Sansana et al. (2021) comparison of hybrid-model approaches that we have not yet resolved.
- **@azadi2022hybrid** (abstract-only) applies a first-principles model plus a *parallel* data-based
  model that "compensates for the deficiencies of the mechanistic model" to a blast furnace —
  the same structure, under the name "hybrid dynamic model", outside both fouling and PINN language.
- **@mcbride2020hybrid** (full text, partially traversed — intro and data-driven sections read, the
  "5 Hybrid Models" section not fully) reviews hybrid semi-parametric modeling in *separation*
  processes and states qualitatively that data-driven models extrapolate poorly. Not a quantified
  per-model extrapolation test. Treat as incompletely verified until that section is read.
- **@bonfanti2024generalization** (abstract-only) studies PINN generalization *outside* the training
  domain and which hyperparameters drive it. Loss-penalty family, so not a Gap threat — useful as
  methodology precedent for testing extrapolation at all, and as support for keeping loss-penalty
  PINNs and additive-residual hybrids as separate categories.

**Consequence:** the Gap can no longer claim that no prior work evaluates a residual-type hybrid
against a black-box under an extrapolation split. It has to narrow to *shell-and-tube fouling
resistance*, and cite @gallup2023physics as a directly relevant, partly negative precedent.
Rewriting a narrative slot is a user-approval gate, so the slot is left unchanged pending that decision.

## Still open

1. **@ichsan2026machine** — the paywalled ScienceDirect review from the last round now has a resolved
   identity: Ichsan, Hidayat, Pramata, Hantoro, *"Machine learning for heat exchanger fouling
   prediction: A systematic review of hybrid and non-hybrid approaches for model selection"*,
   *Results in Engineering* (2026), DOI `10.1016/j.rineng.2026.112383` — confirmed via Crossref to
   carry PII `S2590123026034018`. Every route to the full text returned a hard block, and on
   2026-09-10 the user chose to proceed without it, so it is **not registered** - registering a
   source we have not read would violate the read-before-registering rule, and leaving it as
   `awaiting-user-file` would hold the whole registry in a failing state. It stays here as an open
   risk: it is the single most Gap-relevant title found, and a reviewer may well ask why the Gap
   was fixed without engaging with a 2026 systematic review of exactly hybrid-vs-non-hybrid fouling
   ML. Revisit before the Gap is treated as final.
2. `ardsomang2013heat` — the candidate key said 2021, but the DOI `10.36001/phmconf.2013.v5i1.2773`
   and the landing page both say 2013 (Ardsomang, Hines, Upadhyaya, *PHM Society*). Only the citation
   page was seen, not the abstract, so it is **not registered** — there is no honest `access` value for it.
3. Unresolved leads: Sansana et al. (2021), cited by @bradley2022perspectives; and
   Rogers et al. (2022), *"Investigating 'greyness' of hybrid model for bioprocess predictive
   modelling"*, `10.1016/j.bej.2022.108761`, whose framing looks directly relevant.
4. No source yet establishes that a *shell-and-tube-specific* simulator behaves as the C0 falsifier
   assumes; @coletti2011dynamic and @dazbejarano2016new support plausibility but are abstract-only.

---

# Round 1 critic review (2026-09-11) — verdict `revise`

The review is recorded in full in `.omc/paper-state.md`. Five blockers. The user
decided on 2026-09-11 to act on the two argument-level ones (M1, M2) and to carry
the three literature-coverage ones as open risks, on the grounds that this paper is
a pipeline-validation workload rather than a submission (see `CLAUDE.md`).

## Acted on

- **M1 — the Gap was defended on the weaker ground.** It rested on "a CSTR, not
  shell-and-tube", which reads as salami-slicing. The stronger ground was already in
  this note and left out of the sentence: @gallup2023physics is a **single trial with
  no repeated seeds, no paired test, and capacity matching unconfirmed**. A comparison
  that underpowered settles the question at no system at all, so the gap is evidential
  quality, with shell-and-tube fouling as the setting rather than the justification.
- **M2 — the Gap omitted the half that threatens this paper.** In that same study the
  **loss-penalty PINN generalized far better** than the conjunction/residual model.
  The one cited precedent therefore argues against the architecture this paper chooses,
  and that has to be stated rather than omitted.

  The affirmative reason for choosing additive-residual anyway, recorded here so the
  Approach slot can pin it when methods are fixed: capacity matching is tractable **for**
  additive-residual, because the residual network's trainable parameters can be counted
  against the black-box's, so choosing it does not forfeit the matched comparison C2
  commits to. That much is true. **It is not a reason to prefer additive-residual over a
  loss penalty, and the comparative reason is still owed at `outline-draft`.**

  **Corrected twice; do not read this as settled.** Round 2 (B4) struck the first version,
  which argued that Ebert-Panchal is "an empirical algebraic threshold correlation, not a
  PDE — there is no governing equation to enforce in the loss." That is refuted by the
  equation written above: `dRf/dt = a1*Re^b1*exp(-Ea/(R*Tf)) - c1*tau_w` is an **ODE**, and
  loss penalties on ODE residuals are ordinary. Round 3 then struck the replacement's
  comparative clause, which had claimed a loss penalty "changes the objective rather than
  the capacity" and so is the harder case for capacity matching. @gallup2023physics shows
  the reverse in its own setup: because a loss penalty leaves the architecture untouched,
  its loss model and its baseline are literally the same six-layer, 20-node network —
  matched by construction. The architectural hybrid is the one model whose capacity had to
  drift. On the capacity-matching axis the loss-penalty variant is **cleaner** than
  additive-residual, not messier.

  Two rounds, two failed reasons. A genuine comparative justification cannot be manufactured
  at `lit-review` because it depends on the methods decision, so it is owed when `Approach`
  is pinned. Until then the architecture choice stands on the non-comparative statement
  above and on nothing else. A loss-penalty variant on the Ebert-Panchal ODE residual is a
  **feasible alternative deliberately not taken**, and the paper must say so: the one cited
  precedent found that family generalizing far better, so a referee will ask.

  **Corrected on 2026-09-11 (round 2 critic, B4).** The first version of this justification
  also argued that Ebert-Panchal is "an empirical algebraic threshold correlation, not a PDE
  — there is no governing equation to enforce in the loss." That is refuted by the equation
  written twenty lines above it: `dRf/dt = a1*Re^b1*exp(-Ea/(R*Tf)) - c1*tau_w` is an
  **ODE**, and physics-informed loss penalties are routinely applied to ODE residuals.
  Forming `(dRf/dt)_pred - f(Re, Tf, tau_w)` as a loss term is entirely available. The
  claimed obstacle does not exist, so the argument is withdrawn rather than defended.

  A loss-penalty variant on the Ebert-Panchal ODE residual is therefore a **feasible
  alternative deliberately not taken**, and the paper should say so. Given that
  @gallup2023physics found exactly that family generalizing far better, a referee will ask;
  naming it as a considered and declined option is a better answer than having it found.

## Carried as open risks, not acted on

- **B1 — the additive-residual structure has an unregistered canonical origin.**
  Searching "discrepancy modeling", which this round did not try, returns
  **Kennedy & O'Hagan (2001), "Bayesian Calibration of Computer Models",
  `10.1111/1467-9868.00294`** — the paper that introduced the `y = eta(x) + delta(x) + eps`
  form this hybrid *is* — and **Willard et al., `10.1145/3514228`**, whose taxonomy names
  "residual modeling" directly. Neither is registered. This is the most substantive open
  risk of the three: Kennedy & O'Hagan's result that the discrepancy term is weakly
  identifiable, and that identification degrades away from the calibration region, bears
  directly on C0 ("the residual term has real work to do") and on C2's extrapolation
  premise. Whether that caveat binds under a fully simulated, known-noise design is an
  open question and must not be assumed either way. **Revisit before C0 is exercised in
  `code-experiment`.**
- **B2** — Rogers et al. (2022), `10.1016/j.bej.2022.108761`, on hybrid-model "greyness",
  is listed above as unresolved but is open access and was not attempted.
- **B3** — @mcbride2020hybrid is registered `full-text` while its "5 Hybrid Models"
  section, the load-bearing one for the claim it is cited for, was not traversed. The
  critic judged @bradley2022perspectives' `full-text` defensible on the same test, since
  the sections actually read carry the distinction it is cited for. Finishing one section
  of an already-obtained PDF would settle B3; until then treat the registry value as
  optimistic.
- **M3, required before `code-experiment`** — C0's falsifier is testable in form but
  **biased in the direction of confirming C0**: if the Ebert-Panchal parameters were
  mangled in transcription, the residual-free correlation predicts worse, its
  extrapolation RMSE rises, and C0 is left un-refuted for the wrong reason. Record the
  parameter provenance in the run manifest with the page or table it was verified
  against, and add a sanity gate — if the residual-free correlation's RMSE exceeds the
  black-box's extrapolation RMSE, treat that as a transcription-error signal rather than
  as evidence for C0.
- **M4** — the Gap should scope its negative to the searches run and the date rather than
  asserting a universal negative while `10.1016/j.rineng.2026.112383` is unread.
- Unexamined: Sansana et al. (2021), cited inside @bradley2022perspectives; and
  `10.2139/ssrn.6837407` (2026 SSRN, heat-exchanger hybrid PIML, likely control-oriented).
- @bonfanti2024generalization's "loss-penalty family, not a Gap threat" judgment is made
  from the abstract and is **provisional**.
- The Round-1 "Relation to the paper's Gap" paragraph near the top of this note is stale:
  it says the Gap cites all three original sources, which the rewritten Gap does not.

---

# Round 3 critic review (2026-09-11) — verdict `pass`

All five Gap assertions about @gallup2023physics were re-checked line by line against the
DOE accepted manuscript and are correct: hybrid hidden layers 5 nodes (§3.2), baseline six
layers of 20 (§4), no paired test anywhere (the one statistical display, Figure 10's
boxplot, is in-range and unpaired), "only generalized slightly better than the baseline"
(§4.3, the source's own words; 4.50% vs 6.38% out of range), loss-penalty PINN far ahead of
both (2.28% out of range, "generalized better than any other model", §5.2).

Two things the review corrected in our favour, recorded so they are not undone later.

- **Do not import "in the hybrid's disfavour" into the manuscript.** The round-3 commit
  message used that phrase; the Gap does not, and the Gap is right. Smaller capacity is not
  monotonically worse for extrapolation — an under-parameterised model can extrapolate
  better by fitting in-range structure less — and the manuscript shows the hybrid is not
  capacity-starved in range (0.80% vs the baseline's 0.85%). Scaling it to six layers of 20
  could plausibly make its extrapolation *worse*. The direction is undetermined, which is
  exactly why "confounds capacity with effect" is the right claim and a directional one
  would be an overreach.
- The Gap compares the hybrid's *hidden* layers against the baseline's *six layers*, which
  includes the output layer. Both phrases are the source's own, so this is faithful, but it
  is an asymmetry a referee will re-check.

## Carried to `novelty-check`

The trailing clause "and nothing addresses shell-and-tube fouling resistance **at all**"
is true on the coherent reading — among matched-capacity comparisons of this kind, none is
on shell-and-tube — but read literally it is false and contradicted by this project's own
registry: @he2025machine trains surrogates on CFD-simulated shell-and-tube fouling data,
and `ikram2023comparative` (read, dropped only for corrupt Crossref author metadata)
compares models for shell-and-tube fouling resistance directly. "at all" is an intensifier
on a clause that needs a restrictor. The three-word fix needs no new reading:
**"and no such comparison addresses shell-and-tube fouling resistance."** Pair it with
clearing the stale round-1 paragraph near the top of this note, which still says the Gap
"cites all three" of the original sources.
