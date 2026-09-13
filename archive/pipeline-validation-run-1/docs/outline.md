# Paper Outline

> Planning document only: the claims below remain `assumed`, and Results, Discussion, and Conclusion stay prospective until `Finding` and `Implication` are populated after `code-experiment`.

**Narrative mapping**

| Story element | Destination |
|---|---|
| Context / Gap / Question | Introduction |
| Prior-work comparison / novelty matrix | Related Work |
| Approach | Methods |
| Finding | Results |
| Implication | Discussion and Conclusion |

## 1. Introduction

**Purpose:** Establish the shell-and-tube fouling context, narrow the unresolved comparison, and pose the study question without anticipating an answer.

- **Context:** Fouling in shell-and-tube heat exchangers used across power and process industries progressively degrades heat-transfer performance and raises energy consumption, so operators need fouling-resistance models accurate enough to schedule cleaning before the loss becomes costly.
- **Gap:** On the searches run through 2026-09, no matched-capacity comparison decides whether an additive-residual physics-informed hybrid beats a black-box outside the training envelope: the one precedent, @gallup2023physics, gives its hybrid 5-node hidden layers against the baseline's six layers of 20 and reports no paired test, so its result—the hybrid slightly ahead, a loss-penalty PINN far ahead of both—confounds capacity with effect, and no such comparison addresses shell-and-tube fouling resistance.
- **Question:** For shell-and-tube heat exchanger fouling resistance simulated by a mechanistic fouling model, does embedding a physics-based fouling correlation inside a machine-learning surrogate lower RMSE on operating conditions held outside the training envelope, compared to a capacity-matched purely data-driven model?
- **Planned claims:** C0–C3 are introduced only as preregistered hypotheses and contingencies; no experimental outcome is asserted.

## 2. Related Work

**Purpose:** Position the proposed comparison against fouling-domain modeling and distinct physics-informed architecture families, using the novelty matrix to delimit rather than assert novelty.

- **Fouling-domain sources:** Separate purely data-driven fouling prediction in @he2025machine and @hosseini2022novel from the Ebert–Panchal correlation documented by @wilson2017twenty and the omitted induction-period mechanism documented by @yang2020computational.
- **Physics-informed families:** Distinguish loss-penalty PINNs such as @jadhav2022physics from hybrid submodeling and additive or conjunction architectures discussed by @bradley2022perspectives and @gallup2023physics.
- **Direct, partly negative precedent:** Treat @gallup2023physics as directly relevant: its residual hybrid was only slightly better than its black-box baseline, while its loss-penalty model was far better; however, the residual hybrid used 5-node hidden layers versus the baseline's six 20-node layers, and the study reported neither a paired repeated-seed design nor a paired test.
- **Novelty boundary:** Present the contribution as a controlled shell-and-tube fouling-resistance test with matched trainable capacity, identical search effort, an explicit interpolation/extrapolation design, and paired inference—not as evidence that additive-residual models are generally superior.
- **Planned claim mapping:** C0 receives literature grounding here; its empirical status is tested in Results.

## 3. Methods

**Purpose:** Specify a reproducible, capacity-controlled experiment that directly tests C0–C3 and the additive-residual estimand.

- **Scope:** Treat this as a controlled synthetic tube-side fouling benchmark with fixed fluid properties and wall temperature—not as a validated shell-and-tube exchanger model, an industrial digital twin, or a basis for cleaning decisions.

- **Operating grid and input mapping:** Use an exact 45 × 45 Cartesian grid (2,025 points, including endpoints) over preregistered Reynolds-number and bulk-fluid-temperature bounds; with bulk temperature in kelvin and fixed preregistered tube diameter `D_h`, density `rho`, viscosity `mu`, and wall temperature `T_w > T_b,max`, compute `u = Re mu/(rho D_h)`, the smooth-tube turbulent Darcy factor `f_D = 0.3164 Re^(-1/4)`, wall shear `tau_w = f_D rho u^2/8`, and the declared synthetic film-temperature approximation `T_f = (T_b + T_w)/2`, restricting the Reynolds range to the friction relation and selected Ebert–Panchal parameter set's documented applicability ranges.
- **Latent synthetic simulator:** Without calling or copying Ebert–Panchal coefficients, integrate in days from dimensionless `z(0)=0` and `R_f(0)=0` in native resistance units to `H=30 d`, with `k_ind(T_f)=A_ind exp{-[E_ind/R_g](1/T_f-1/T_ref)}` in `d^-1`, `dz/dt=k_ind(T_f)(1-z)`, `G(z)=0` for `z<z_c` and `G(z)=(z-z_c)/(1-z_c)` otherwise, and unconstrained rate `F=G(z) A_dep (Re/Re_ref)^p exp{-[E_dep/R_g](1/T_f-1/T_ref)}-A_rem(tau_w/tau_ref)^q R_f`, where `A_dep` has resistance-per-day units, `A_rem` has `d^-1`, `E_ind` and `E_dep` have `J mol^-1`, and `z`, `z_c`, `p`, and `q` are dimensionless; apply the zero-boundary projection `dR_f/dt=max(0,F)` only when `R_f=0` and `F<0`, otherwise use `dR_f/dt=F`, clamping only negative solver round-off to zero.
- **Simulator preregistration:** Freeze `A_ind`, `E_ind`, `z_c`, `A_dep`, `E_dep`, `p`, `A_rem`, `q`, `T_ref`, `Re_ref`, `tau_ref`, every unit, solver, tolerance, boundary epsilon, and time conversion independently of model outcomes; require the induction transition to occur within `H` for a preregistered nontrivial grid fraction and require `max R_f(H)-min R_f(H)>0` before any noise or training step.
- **Independent physics baseline:** From the visually verified published parameter set in @wilson2017twenty, compute `r_EP = a1 Re^b1 exp[-E_a/(R_g T_f)] - c1 tau_w` using the same physical input mapping, clean initial condition, units, gas constant, and horizon but no simulator-specific kinetics, and define `R_f,EP(H) = H max(0, r_EP)` so a negative net rate means zero accumulation rather than negative resistance.
- **Noise and scoring target:** Compute `sigma = 0.02[max R_f(H) - min R_f(H)]` once from the latent full grid, add independent zero-mean Gaussian noise per point and repetition without clipping, and compute every adjudicative black-box, hybrid, and residual-free RMSE against the same noisy held-out targets in native fouling-resistance units; record `target_basis: noisy` in the run manifest, while any clean-target score is diagnostic only.
- **Models:** Compare a black-box network with an additive-residual hybrid whose prediction is the integrated Ebert–Panchal prediction plus a learned discrepancy, and expose the physics-only component by fixing that discrepancy to zero.
- **Fairness controls:** Match trainable-parameter counts within 10% and give both models identical hyperparameter-search budgets: the same trial count, tuned dimensions, and ranges for learning rate, hidden width/depth, and regularization strength.
- **Protected selection and test splits:** Within each repetition, first reserve a stratified 20% of central-box points as the untouched interpolation test set, split the remaining central-box points into 80% fitting and 20% validation subsets for hyperparameter selection, select both models under identical trial budgets using validation RMSE only, then refit each selected configuration on the combined fitting-plus-validation pool; never use interpolation-test or extrapolation targets for selection, stopping, or refitting, and define the untouched extrapolation set by the union rule holding out every condition where either variable lies in an outer 20% tail.
- **Repeated paired evaluation and test:** Run 10 repetitions that vary weight initialization, the central-box fitting/validation/interpolation partition, and the noise draw while pairing both models on the same seeds; test the one-sided alternative that hybrid extrapolation RMSE is lower using an exact Wilcoxon signed-rank calculation that discards zero differences, averages ranks for tied absolute differences, enumerates all `2^m` sign assignments for the `m` nonzero pairs, and sets `p=1` if all differences are zero.
- **Preregistered decisions:** Support C1 only if the black-box median extrapolation RMSE is at least `1.5×` its median interpolation RMSE; support C2 only if the hybrid median extrapolation RMSE is at least 10% lower than the black-box median, the hybrid is lower in at least 8/10 paired repetitions, and the preregistered one-sided exact Wilcoxon test gives `p < 0.05`; support C3 only if the hybrid median interpolation RMSE is no more than 10% higher than the black-box median; if C1 fails, report C2 and C3 as uninterpretable, and if C0 is refuted or suspended, do not support C2 or C3.
- **C0 precedence, falsifier, and transcription gate:** First suspend C0 adjudication and leave it `assumed` if the median residual-free Ebert–Panchal extrapolation RMSE exceeds the black-box median extrapolation RMSE, treating that result as a parameter-transcription, unit-conversion, or input-mapping alarm; only otherwise refute C0 if the residual-free median across the 10 noisy-target repetitions is at or below `1.1 sigma`, and support C0 only if neither condition holds.
- **Parameter provenance:** Before coding, record in the run manifest the selected Ebert–Panchal variant, @wilson2017twenty DOI/version, equation number, source page and table, every coefficient and unit as visually verified independently twice, and all conversions; values obtained only from `pdftotext` are inadmissible.
- **Deliberate exclusion of a feasible alternative:** Do not use an Ebert–Panchal ODE-residual loss penalty because it estimates soft ODE enforcement under a penalty-weighted objective, requires selection of a penalty weight, and lacks the same removable learned correction needed by this estimand and C0 falsifier; this scope choice does not claim that additive residuals are generally superior or easier to capacity-match, and it retains @gallup2023physics as negative precedent.
- **Planned claim mapping:** C0 maps to simulator–correlation independence, omitted-mechanism construction, and the noise-floor/transcription gates; C1 maps to the split and black-box interpolation/extrapolation protocol; C2 maps to matched capacity, identical search, paired repetitions, 8/10 direction check, and Wilcoxon inference; C3 maps to the paired interpolation comparison.

## 4. Results

**Purpose:** After `code-experiment`, report the preregistered tests and claim statuses without adding unplanned outcomes.

- **Prospective sequence:** Report data, mapping, positive-range, selection-protection, and split checks; apply the C0 transcription/unit/input-mapping alarm first, then only if it does not fire compare the median residual-free extrapolation RMSE with the `1.1 sigma` noisy-target threshold; report C1's requirement that black-box median extrapolation RMSE be at least `1.5×` its median interpolation RMSE; report C2's conjunctive requirements of at least 10% lower hybrid median extrapolation RMSE, hybrid wins in at least 8/10 paired repetitions, and `p < 0.05` from the preregistered one-sided exact signed-rank enumeration; and report C3's requirement that hybrid median interpolation RMSE be no more than 10% higher than the black-box median.
- **Contingencies:** Apply the declared gates and falsifiers, including treating C2 and C3 as uninterpretable if C1's hard-extrapolation premise fails and withholding support for C2 and C3 if C0 is refuted or remains `assumed` because adjudication is suspended.
- **Planned claim mapping:** C0, C1, C2, and C3 are all adjudicated here; no outcome is asserted at outline stage.

## 5. Discussion

**Purpose:** After the Finding is known, interpret supported, refuted, or uninterpretable claims and derive only implications warranted by the experiment.

- **Prospective interpretation:** Explain what the observed C0–C3 pattern says about this simulator, correlation, split, and estimand; compare it with @gallup2023physics, including its stronger loss-penalty result; and separate interpolation behavior from extrapolation behavior.
- **Limits:** Address the fact that this is a controlled synthetic tube-side fouling benchmark with fixed properties and wall temperature—not a validated shell-and-tube exchanger model, industrial digital twin, or cleaning-decision basis—along with correlation misspecification, residual identifiability, split geometry, ten-repetition inference, capacity matching, and the untested loss-penalty alternative.
- **Scope guardrail:** Avoid general claims that additive-residual architectures outperform physics-loss or black-box methods.
- **Planned claim mapping:** Interpret C0–C3 according to their final statuses, without changing thresholds after seeing results.

## 6. Conclusion

**Purpose:** After the Implication is established, answer the study question briefly and conditionally within the validated scope.

- **Prospective close:** Summarize only the final status of C0–C3, the resulting answer for shell-and-tube fouling resistance under the specified design, and the principal next comparison suggested by the evidence.
- **Planned claim mapping:** Carry forward only claims among C0–C3 that the completed Results support or explicitly report as negative or uninterpretable; no outcome is asserted at outline stage.
