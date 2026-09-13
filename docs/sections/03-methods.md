# Methods
<!-- claims: C0, C1, C2, C3 -->

## Scope and preregistration

This study is preregistered as a controlled synthetic tube-side fouling benchmark. Fluid properties and wall temperature will be fixed across operating points. The benchmark is not a validated model of a complete shell-and-tube exchanger, an industrial digital twin, or a basis for cleaning decisions. Its estimand is narrower: whether, under the protocol below, adding a learned discrepancy to a fixed published correlation improves extrapolation relative to a capacity-matched black-box network.

The approved design already fixes the grid size (45 by 45, or 2,025 operating points), the 30 d horizon, the noise rule, protected-split proportions, ten paired repetitions, decision thresholds, and inferential procedure. Numerical inputs that remain unresolved will be frozen before any code is executed in the version-controlled input `data/raw/fouling-benchmark-config.json`. Experiment code will only read this file; it will not choose or rewrite its values. The file must specify the grid bounds; $D_h$, $\rho$, $\mu$, and $T_w$; all simulator kinetic constants and references; solver, tolerances, boundary epsilon, and time conversion; the Ebert–Panchal variant and visually verified coefficients, units, and conversions; model architectures or search ranges, trial count, preprocessing, and stopping/refitting settings; and the complete seed list. The Methods will be updated from the approved run manifest after `code-experiment`, replacing unresolved descriptions with the frozen values actually used, without changing the preregistered rules.

## Operating domain and physical input mapping

The synthetic design will use an exact $45\times45$ Cartesian grid, including endpoints, over preregistered Reynolds-number and bulk-fluid-temperature bounds. Thus, the latent full grid contains exactly 2,025 points. With $T_b$ in kelvin and fixed hydraulic diameter $D_h$, density $\rho$, viscosity $\mu$, and wall temperature satisfying $T_w>T_{b,\max}$, each point will be mapped as

$$
u = \frac{\mathrm{Re}\,\mu}{\rho D_h}, \qquad
f_D=0.3164\,\mathrm{Re}^{-1/4},$$

$$
\tau_w=\frac{f_D\rho u^2}{8}, \qquad
T_f=\frac{T_b+T_w}{2}.
$$

Here $u$ is the mean tube velocity, $f_D$ is the smooth-tube turbulent Darcy friction factor, $\tau_w$ is wall shear stress, and $T_f$ is a declared synthetic film-temperature approximation. The Reynolds-number bounds must lie within both the documented applicability of this friction relation and that of the selected Ebert–Panchal parameter set. These mappings are applicable only to this fixed-property synthetic tube-side setup; they are not presented as a general exchanger calculation.

## Latent fouling simulator

The data-generating simulator will be specified independently of the Ebert–Panchal transcription. Time $t$ is measured in days. At every grid point, a dimensionless induction state $z$ and fouling resistance $R_f$ in native resistance units begin from $z(0)=0$ and $R_f(0)=0$ and are integrated to the fixed horizon $H=30\ \mathrm{d}$. The induction kinetics are

$$
k_{\mathrm{ind}}(T_f)=A_{\mathrm{ind}}
\exp\left[-\frac{E_{\mathrm{ind}}}{R_g}
\left(\frac{1}{T_f}-\frac{1}{T_{\mathrm{ref}}}\right)\right],
\qquad
\frac{dz}{dt}=k_{\mathrm{ind}}(T_f)(1-z),
$$

where $k_{\mathrm{ind}}$ and $A_{\mathrm{ind}}$ have units $\mathrm{d}^{-1}$ and $E_{\mathrm{ind}}$ has units $\mathrm{J\,mol}^{-1}$. Induction gates deposition through

$$
G(z)=
\begin{cases}
0, & z<z_c,\\
\dfrac{z-z_c}{1-z_c}, & z\ge z_c.
\end{cases}
$$

The unconstrained fouling-resistance rate is

$$
F=G(z)A_{\mathrm{dep}}
\left(\frac{\mathrm{Re}}{\mathrm{Re}_{\mathrm{ref}}}\right)^p
\exp\left[-\frac{E_{\mathrm{dep}}}{R_g}
\left(\frac{1}{T_f}-\frac{1}{T_{\mathrm{ref}}}\right)\right]
-A_{\mathrm{rem}}
\left(\frac{\tau_w}{\tau_{\mathrm{ref}}}\right)^qR_f.
$$

$A_{\mathrm{dep}}$ has resistance-per-day units, $A_{\mathrm{rem}}$ has $\mathrm{d}^{-1}$, and $E_{\mathrm{dep}}$ has $\mathrm{J\,mol}^{-1}$; $z$, $z_c$, $p$, and $q$ are dimensionless. At the nonnegative boundary,

$$
\frac{dR_f}{dt}=
\begin{cases}
\max(0,F), & R_f=0\ \text{and}\ F<0,\\
F, & \text{otherwise}.
\end{cases}
$$

Only negative numerical round-off after integration may be clamped to zero. The config will freeze $A_{\mathrm{ind}}$, $E_{\mathrm{ind}}$, $z_c$, $A_{\mathrm{dep}}$, $E_{\mathrm{dep}}$, $p$, $A_{\mathrm{rem}}$, $q$, $T_{\mathrm{ref}}$, $\mathrm{Re}_{\mathrm{ref}}$, $\tau_{\mathrm{ref}}$, $R_g$, all units, and numerical controls. Before execution it will also freeze a nontrivial required fraction of grid points for which the induction transition occurs within $H$. Simulator coefficients may be selected only to satisfy that preregistered induction-coverage rule and physical/unit constraints, independently of Ebert–Panchal errors and either model's outcomes. Before noise generation or training, the run must pass

$$
\max_i R_{f,i}(H)-\min_i R_{f,i}(H)>0.
$$

Failure of either the induction-coverage requirement or this positive-range gate stops the run rather than prompting post hoc retuning.

## Independent physics baseline and noisy targets

The fixed physics component will use one published Ebert–Panchal variant documented by @wilson2017twenty, selected and frozen before model evaluation. It will not reuse the simulator's kinetic coefficients. Using the same $\mathrm{Re}$, $T_f$, $\tau_w$, clean initial condition, gas constant, unit system, and horizon, its rate is

$$
r_{\mathrm{EP}}=a_1\mathrm{Re}^{b_1}
\exp\left(-\frac{E_a}{R_gT_f}\right)-c_1\tau_w,
\qquad
R_{f,\mathrm{EP}}(H)=H\max(0,r_{\mathrm{EP}}).
$$

Thus, a negative net rate produces zero accumulation, never negative resistance. The simulator's separately motivated induction mechanism, consistent with the type of mechanism studied by @yang2020computational, is absent from this baseline; whether that omission creates useful residual structure remains an empirical C0 question.

Noise magnitude will be computed once from the latent full-grid endpoints:

$$
\sigma=0.02\left[\max_iR_{f,i}(H)-\min_iR_{f,i}(H)\right].
$$

For each repetition and point, independent zero-mean Gaussian noise with standard deviation $\sigma$ will be added without clipping. Every adjudicative black-box, hybrid, and residual-free RMSE will be computed against the same noisy held-out targets in native fouling-resistance units. The manifest must record `target_basis: noisy`; clean-target scores, if produced, are diagnostic only.

## Models, capacity, and tuning parity

The black-box maps the preregistered inputs directly to endpoint fouling resistance. The additive-residual hybrid predicts

$$
\widehat R_{f,\mathrm{hyb}}(H)=R_{f,\mathrm{EP}}(H)+\widehat\delta(\mathrm{Re},T_b),
$$

where $\widehat\delta$ is learned. Setting $\widehat\delta=0$ exposes the residual-free physics component used for C0. Exact architectures remain unresolved and therefore will be bound by the pre-run config and recorded in the run manifest rather than asserted here.

Capacity is the total number of trainable scalar weights and biases optimized in each predictor; fixed Ebert–Panchal calculations and nontrainable preprocessing constants count as zero. If these totals are $P_H$ and $P_B$, admissibility requires $|P_H-P_B|/P_B\le0.10$. The manifest must report both counts and the resulting ratio. This is a pre-execution acceptance rule, not a claim that parity has already been measured.

Both arms will receive exactly the same number of search trials and tune the same dimensions—learning rate, hidden width, hidden depth, and regularization strength—over identical frozen ranges. The config will define the ranges, trial count, candidate-generation seeds, training budget per trial, and tie-breaking rule. A trial means one candidate configuration trained and evaluated once under the same resource limit. Neither arm may receive replacement trials or a wider range because of observed performance.

## Protected splits and paired repetitions

Normalize each grid axis by its preregistered bounds. The central 60% interval on each axis defines a central $60\%\times60\%$ geometric box. Any point for which either axis lies in an outer 20% tail belongs to the untouched extrapolation set (the union rule).

Within the central box in each repetition, a stratified 20% of points will first be reserved as the interpolation test set. Of the remaining 80%, 80% will be assigned to fitting and 20% to validation. Hyperparameters and stopping will use validation RMSE only. After selection, each selected configuration will be refit on the combined fitting-plus-validation pool. Interpolation-test targets and all union-rule extrapolation targets will never be used for selection, stopping, or refitting. Stratification variables and rounding rules will be frozen in the config.

The benchmark comprises exactly ten compute-bounded repetitions, not a powered population-level claim. Repetitions vary weight initialization, the central-box partition, and the noise draw. Within each repetition, the two models use exactly the same split and noise seeds; search randomness is paired where operationally applicable and fully recorded. All ten repetitions, including unfavorable or failed comparisons, will be reported, and the limitations of ten repetitions will be addressed after execution.

## Inference and preregistered decisions

For repetition $i$, define $d_i=\mathrm{RMSE}_{H,i}^{\mathrm{extra}}-\mathrm{RMSE}_{B,i}^{\mathrm{extra}}$. The sole inferential test has the one-sided alternative that these differences are negative. Exact zeros are discarded; tied absolute differences receive average ranks; and the one-sided $p$ value is obtained by enumerating all $2^m$ sign assignments for the $m$ nonzero differences. If all differences are zero, $p=1$. The inferential $p$-value family therefore has size one. C0, C1, and C3 thresholds and C2's 8/10 direction requirement are deterministic gates, not additional significance tests.

Decisions follow a fixed precedence. First, if the median residual-free extrapolation RMSE exceeds the black-box median extrapolation RMSE, C0 adjudication is suspended and C0 remains `assumed`; this is a transcription, conversion, or input-mapping alarm. Otherwise, C0 is refuted if the residual-free median noisy-target extrapolation RMSE is at or below $1.1\sigma$. C0 may be supported only if neither condition holds and the source, omitted-mechanism, independence, and provenance checks all pass.

C1 is supported only if the black-box median extrapolation RMSE is at least $1.5$ times its median interpolation RMSE. If C1 fails, C2 and C3 are uninterpretable. Subject to C1 and C0, C2 requires all three conditions: hybrid median extrapolation RMSE at least 10% below the black-box median, hybrid RMSE lower in at least 8 of 10 pairs, and exact one-sided $p<0.05$. C3 requires hybrid median interpolation RMSE no more than 10% above the black-box median. If C0 is refuted or suspended, C2 and C3 cannot be supported.

## Provenance and excluded alternative

The run manifest must identify `@wilson2017twenty`, DOI `10.1080/01457632.2016.1206407`, the exact source version, equation, page, table, and selected variant; list every coefficient, unit, and conversion; and document two independent visual transcription checks. Values obtained from `pdftotext` are inadmissible. `@kennedy2001bayesian` (Kennedy and O'Hagan, 2001) originates the additive discrepancy form `y = eta(x) + delta(x) + eps` this hybrid uses; its finding that the discrepancy term is weakly identifiable and degrades away from the calibration region is a caveat on C0 and C2's extrapolation premise, addressed in Discussion.

An Ebert–Panchal ODE-residual loss penalty is feasible but deliberately excluded. It would test soft ODE enforcement under a penalty-weighted objective, require selection of a penalty weight, and would not expose the same removable learned correction used by this estimand and C0 falsifier. This exclusion does not imply that additive residuals are generally superior or easier to capacity-match; indeed, the stronger loss-penalty result in the direct precedent remains a negative comparator (@gallup2023physics).