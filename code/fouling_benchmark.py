"""fouling_benchmark.py — code-experiment run for C0-C3.

Generates a synthetic tube-side fouling benchmark from a latent mechanistic
simulator (induction period + deposition/removal kinetics), computes an
independent Ebert-Panchal physics baseline from visually double-verified
published coefficients (@wilson2017twenty, Fig. 2 caption), trains a
black-box surrogate and an additive-residual hybrid surrogate with matched
trainable capacity and identical hyperparameter-search budgets, and runs the
preregistered paired one-sided Wilcoxon signed-rank test plus the C0-C3
decision gates specified in docs/sections/03-methods.md.

Re-run exactly as recorded in the run manifest:
    "/c/Python313/python.exe" code/fouling_benchmark.py \
        --config data/raw/fouling-benchmark-config.json \
        --out data/processed/fouling-benchmark-2026-09-13.json

Reads only data/raw/fouling-benchmark-config.json. Writes only the single
JSON result file named by --out under data/processed/. No other file is
touched. All randomness is seeded from the config's random_seed_policy, so
two runs of this exact command produce byte-identical output.
"""
from __future__ import annotations

import argparse
import itertools
import json
import platform
import sys
from pathlib import Path

import numpy as np
from sklearn.neural_network import MLPRegressor


# --------------------------------------------------------------------------
# Physical input mapping
# --------------------------------------------------------------------------

def build_grid(cfg: dict) -> tuple[np.ndarray, np.ndarray]:
    g = cfg["grid"]
    re = np.linspace(g["re_min"], g["re_max"], g["n_re"])
    tb = np.linspace(g["tb_min"], g["tb_max"], g["n_tb"])
    Re, Tb = np.meshgrid(re, tb, indexing="ij")
    return Re.ravel(), Tb.ravel()


def physical_mapping(Re: np.ndarray, Tb: np.ndarray, cfg: dict) -> dict:
    phys = cfg["physical"]
    fr = cfg["friction"]
    D_h, rho, mu, T_w = phys["D_h"], phys["rho"], phys["mu"], phys["T_w"]
    u = Re * mu / (rho * D_h)
    f_D = fr["f_D_coeff"] * np.power(Re, fr["f_D_exp"])
    tau_w = f_D * rho * u ** 2 / 8.0
    T_f = (Tb + T_w) / 2.0
    return {"u": u, "f_D": f_D, "tau_w": tau_w, "T_f": T_f}


# --------------------------------------------------------------------------
# Latent mechanistic simulator (independent of Ebert-Panchal transcription)
# --------------------------------------------------------------------------

def simulate_latent(Re: np.ndarray, T_f: np.ndarray, tau_w: np.ndarray, cfg: dict) -> dict:
    sim = cfg["simulator"]
    R_g = sim["R_g"]
    H = sim["H_days"]
    n_steps = sim["euler_steps"]
    dt = H / n_steps

    n = Re.shape[0]
    z = np.zeros(n)
    Rf = np.zeros(n)

    k_ind = sim["A_ind"] * np.exp(
        -(sim["E_ind"] / R_g) * (1.0 / T_f - 1.0 / sim["T_ref"])
    )
    re_ratio = np.power(Re / sim["Re_ref"], sim["p"])
    dep_temp = np.exp(-(sim["E_dep"] / R_g) * (1.0 / T_f - 1.0 / sim["T_ref"]))
    tau_ratio = np.power(tau_w / sim["tau_ref"], sim["q"])

    z_c = sim["z_c"]
    transitioned_within_H = np.zeros(n, dtype=bool)

    for step in range(n_steps):
        dz = k_ind * (1.0 - z)
        z_next = z + dz * dt

        G = np.where(z < z_c, 0.0, (z - z_c) / (1.0 - z_c))
        F = G * sim["A_dep"] * re_ratio * dep_temp - sim["A_rem"] * tau_ratio * Rf

        boundary = (Rf <= 0.0) & (F < 0.0)
        dRf = np.where(boundary, np.maximum(0.0, F), F)
        Rf_next = Rf + dRf * dt
        # Only negative numerical round-off may be clamped.
        Rf_next = np.where((Rf_next < 0.0) & (Rf_next > -1e-12), 0.0, Rf_next)

        newly_transitioned = (z < z_c) & (z_next >= z_c)
        transitioned_within_H |= newly_transitioned

        z, Rf = z_next, Rf_next

    induction_fraction = float(np.mean(transitioned_within_H))
    positive_range = float(np.max(Rf) - np.min(Rf))

    return {
        "Rf": Rf,
        "induction_fraction": induction_fraction,
        "positive_range": positive_range,
    }


# --------------------------------------------------------------------------
# Independent Ebert-Panchal physics baseline
# --------------------------------------------------------------------------

def ebert_panchal_baseline(Re: np.ndarray, T_f: np.ndarray, tau_w: np.ndarray, cfg: dict) -> np.ndarray:
    ep = cfg["ebert_panchal"]["coefficients"]
    R_g = cfg["simulator"]["R_g"]
    H_hours = cfg["ebert_panchal"]["H_hours"]
    r_EP = (
        ep["a1"] * np.power(Re, ep["b1"]) * np.exp(-ep["Ea"] / (R_g * T_f))
        - ep["c1"] * tau_w
    )
    return H_hours * np.maximum(0.0, r_EP)


# --------------------------------------------------------------------------
# Splits
# --------------------------------------------------------------------------

def union_rule_mask(re_norm: np.ndarray, tb_norm: np.ndarray) -> np.ndarray:
    """True where the point belongs to the untouched extrapolation set."""
    outer = 0.2
    return (
        (re_norm < outer) | (re_norm > 1 - outer)
        | (tb_norm < outer) | (tb_norm > 1 - outer)
    )


def normalize(values: np.ndarray) -> np.ndarray:
    lo, hi = values.min(), values.max()
    return (values - lo) / (hi - lo)


def make_splits(re_norm: np.ndarray, tb_norm: np.ndarray, rng: np.random.Generator,
                 cfg: dict) -> dict:
    extra_mask = union_rule_mask(re_norm, tb_norm)
    central_idx = np.where(~extra_mask)[0]
    extra_idx = np.where(extra_mask)[0]

    shuffled = rng.permutation(central_idx)
    n_central = shuffled.shape[0]
    n_interp_test = int(round(cfg["splits"]["interp_test_fraction"] * n_central))
    interp_test_idx = shuffled[:n_interp_test]
    remainder_idx = shuffled[n_interp_test:]

    n_val = int(round(cfg["splits"]["val_fraction_of_remainder"] * remainder_idx.shape[0]))
    val_idx = remainder_idx[:n_val]
    fit_idx = remainder_idx[n_val:]

    return {
        "fit": fit_idx,
        "val": val_idx,
        "fit_plus_val": remainder_idx,
        "interp_test": interp_test_idx,
        "extrapolation": extra_idx,
    }


# --------------------------------------------------------------------------
# Models: matched-capacity black-box and additive-residual hybrid
# --------------------------------------------------------------------------

def count_mlp_params(hidden_layer_sizes: tuple[int, ...], n_inputs: int = 2, n_outputs: int = 1) -> int:
    sizes = (n_inputs,) + tuple(hidden_layer_sizes) + (n_outputs,)
    total = 0
    for a, b in zip(sizes[:-1], sizes[1:]):
        total += a * b + b
    return total


def fit_mlp(X_fit, y_fit, hidden_layer_sizes, learning_rate_init, alpha, max_iter, seed):
    model = MLPRegressor(
        hidden_layer_sizes=tuple(hidden_layer_sizes),
        learning_rate_init=learning_rate_init,
        alpha=alpha,
        max_iter=max_iter,
        random_state=seed,
        solver="adam",
        activation="relu",
        early_stopping=False,
    )
    model.fit(X_fit, y_fit)
    return model


def rmse(pred, target) -> float:
    return float(np.sqrt(np.mean((pred - target) ** 2)))


def select_and_refit(X, y_target, splits, trial_grid, max_iter, seed):
    """Select on validation RMSE only, then refit on fit+val. Returns model + params + trial count."""
    best = None
    trial_count = 0
    for trial_idx, (hidden, lr, alpha) in enumerate(trial_grid):
        trial_count += 1
        trial_seed = (seed * 100_003 + trial_idx) % (2 ** 32 - 1)
        model = fit_mlp(X[splits["fit"]], y_target[splits["fit"]], hidden, lr, alpha, max_iter, trial_seed)
        val_rmse = rmse(model.predict(X[splits["val"]]), y_target[splits["val"]])
        if best is None or val_rmse < best["val_rmse"]:
            best = {"hidden": hidden, "lr": lr, "alpha": alpha, "val_rmse": val_rmse}
    refit_seed = (seed * 100_003 + 999_999) % (2 ** 32 - 1)
    final_model = fit_mlp(
        X[splits["fit_plus_val"]], y_target[splits["fit_plus_val"]],
        best["hidden"], best["lr"], best["alpha"], max_iter, refit_seed,
    )
    return final_model, best, trial_count


# --------------------------------------------------------------------------
# Inference: exact one-sided paired Wilcoxon signed-rank test
# --------------------------------------------------------------------------

def exact_one_sided_wilcoxon_less(diffs: np.ndarray) -> float:
    """P(T <= observed) for H1: diffs tend to be negative (hybrid < black-box)."""
    nonzero = diffs[diffs != 0]
    m = nonzero.shape[0]
    if m == 0:
        return 1.0
    abs_d = np.abs(nonzero)
    order = np.argsort(abs_d)
    ranks = np.empty(m)
    sorted_abs = abs_d[order]
    i = 0
    rank_cursor = 1
    while i < m:
        j = i
        while j + 1 < m and sorted_abs[j + 1] == sorted_abs[i]:
            j += 1
        avg_rank = (rank_cursor + (rank_cursor + (j - i))) / 2.0
        ranks[order[i:j + 1]] = avg_rank
        rank_cursor += (j - i + 1)
        i = j + 1

    signs = np.sign(nonzero)
    observed_T_neg = float(np.sum(ranks[signs < 0]))

    total_le = 0
    total = 0
    for sign_bits in itertools.product([1, -1], repeat=m):
        total += 1
        t_neg = sum(r for r, s in zip(ranks, sign_bits) if s < 0)
        if t_neg >= observed_T_neg:
            total_le += 1
    return total_le / total


# --------------------------------------------------------------------------
# Main experiment
# --------------------------------------------------------------------------

def run(cfg: dict) -> dict:
    Re, Tb = build_grid(cfg)
    mapping = physical_mapping(Re, Tb, cfg)
    latent = simulate_latent(Re, mapping["T_f"], mapping["tau_w"], cfg)
    Rf_latent = latent["Rf"]

    min_frac = cfg["simulator"]["induction_coverage_min_fraction"]
    if latent["induction_fraction"] < min_frac:
        raise SystemExit(
            f"induction-coverage gate failed: {latent['induction_fraction']:.3f} < {min_frac}"
        )
    if latent["positive_range"] <= 0.0:
        raise SystemExit("positive-range gate failed: max Rf(H) - min Rf(H) <= 0")

    sigma = cfg["noise"]["sigma_fraction"] * latent["positive_range"]

    Rf_ep = ebert_panchal_baseline(Re, mapping["T_f"], mapping["tau_w"], cfg)

    re_norm = normalize(Re)
    tb_norm = normalize(Tb)
    X = np.column_stack([re_norm, tb_norm])

    extra_mask = union_rule_mask(re_norm, tb_norm)
    central_mask = ~extra_mask
    ep_coverage = {
        "central_box_positive_fraction": float(np.mean(Rf_ep[central_mask] > 0.0)),
        "extrapolation_positive_fraction": float(np.mean(Rf_ep[extra_mask] > 0.0)),
        "whole_grid_positive_fraction": float(np.mean(Rf_ep > 0.0)),
        "central_box_n": int(central_mask.sum()),
        "extrapolation_n": int(extra_mask.sum()),
    }

    trial_grid = list(itertools.product(
        cfg["models"]["hidden_layer_sizes_grid"],
        cfg["models"]["learning_rate_init_grid"],
        cfg["models"]["alpha_grid"],
    ))
    max_iter = cfg["models"]["max_iter"]

    hidden_sizes_used = {tuple(h) for h, _, _ in trial_grid}
    param_counts = {h: count_mlp_params(h) for h in hidden_sizes_used}
    p_min, p_max = min(param_counts.values()), max(param_counts.values())

    seeds = cfg["repetitions"]["seed_list"]
    master_seed = cfg["random_seed_policy"]["master_seed"]

    per_rep = []
    for rep_idx, seed in enumerate(seeds):
        rep_seed = master_seed + seed * 7919 + rep_idx
        rng = np.random.default_rng(rep_seed)

        splits = make_splits(re_norm, tb_norm, rng, cfg)
        noise = rng.normal(0.0, sigma, size=Rf_latent.shape[0])
        y_noisy = Rf_latent + noise

        bb_model, bb_params, bb_trials = select_and_refit(
            X, y_noisy, splits, trial_grid, max_iter, rep_seed
        )

        residual_target = y_noisy - Rf_ep
        hyb_model, hyb_params, hyb_trials = select_and_refit(
            X, residual_target, splits, trial_grid, max_iter, rep_seed
        )

        def hybrid_predict(idx):
            return Rf_ep[idx] + hyb_model.predict(X[idx])

        def residual_free_predict(idx):
            return Rf_ep[idx]

        bb_interp_rmse = rmse(bb_model.predict(X[splits["interp_test"]]), y_noisy[splits["interp_test"]])
        bb_extra_rmse = rmse(bb_model.predict(X[splits["extrapolation"]]), y_noisy[splits["extrapolation"]])
        hyb_interp_rmse = rmse(hybrid_predict(splits["interp_test"]), y_noisy[splits["interp_test"]])
        hyb_extra_rmse = rmse(hybrid_predict(splits["extrapolation"]), y_noisy[splits["extrapolation"]])
        ep_extra_rmse = rmse(residual_free_predict(splits["extrapolation"]), y_noisy[splits["extrapolation"]])
        ep_interp_rmse = rmse(residual_free_predict(splits["interp_test"]), y_noisy[splits["interp_test"]])

        per_rep.append({
            "seed": seed,
            "rep_seed": rep_seed,
            "bb_interp_rmse": bb_interp_rmse,
            "bb_extra_rmse": bb_extra_rmse,
            "hyb_interp_rmse": hyb_interp_rmse,
            "hyb_extra_rmse": hyb_extra_rmse,
            "ep_extra_rmse": ep_extra_rmse,
            "ep_interp_rmse": ep_interp_rmse,
            "bb_selected": bb_params,
            "hyb_selected": hyb_params,
            "bb_trials": bb_trials,
            "hyb_trials": hyb_trials,
            "sigma": sigma,
        })

    bb_extra = np.array([r["bb_extra_rmse"] for r in per_rep])
    bb_interp = np.array([r["bb_interp_rmse"] for r in per_rep])
    hyb_extra = np.array([r["hyb_extra_rmse"] for r in per_rep])
    hyb_interp = np.array([r["hyb_interp_rmse"] for r in per_rep])
    ep_extra = np.array([r["ep_extra_rmse"] for r in per_rep])

    diffs = hyb_extra - bb_extra
    p_value = exact_one_sided_wilcoxon_less(diffs)
    win_count = int(np.sum(hyb_extra < bb_extra))

    thr = cfg["decision_thresholds"]

    median_bb_extra = float(np.median(bb_extra))
    median_bb_interp = float(np.median(bb_interp))
    median_hyb_extra = float(np.median(hyb_extra))
    median_hyb_interp = float(np.median(hyb_interp))
    median_ep_extra = float(np.median(ep_extra))

    c0_suspended = median_ep_extra > median_bb_extra
    c0_refuted = (not c0_suspended) and (median_ep_extra <= thr["c0_refute_sigma_multiple"] * sigma)
    if c0_suspended:
        c0_status = "assumed (suspended: transcription/unit/input-mapping alarm)"
    elif c0_refuted:
        c0_status = "refuted"
    else:
        c0_status = "supported"

    c1_supported = median_bb_extra >= thr["c1_ratio_min"] * median_bb_interp
    c1_status = "supported" if c1_supported else "refuted"

    if not c1_supported:
        c2_status = "uninterpretable"
        c3_status = "uninterpretable"
    elif c0_status != "supported":
        c2_status = "cannot be supported (C0 not supported)"
        c3_status = "cannot be supported (C0 not supported)"
    else:
        c2_rmse_ok = median_hyb_extra <= (1 - thr["c2_rmse_improvement_min"]) * median_bb_extra
        c2_win_ok = (win_count / len(per_rep)) >= thr["c2_win_rate_min"]
        c2_p_ok = p_value < thr["c2_p_max"]
        c2_status = "supported" if (c2_rmse_ok and c2_win_ok and c2_p_ok) else "refuted"

        c3_ok = median_hyb_interp <= (1 + thr["c3_rmse_degradation_max"]) * median_bb_interp
        c3_status = "supported" if c3_ok else "refuted"

    result = {
        "config_echo": {
            "grid_points": int(Re.shape[0]),
            "induction_fraction": latent["induction_fraction"],
            "positive_range": latent["positive_range"],
            "sigma": sigma,
        },
        "ebert_panchal_coverage": ep_coverage,
        "capacity": {
            "hidden_layer_sizes_grid": cfg["models"]["hidden_layer_sizes_grid"],
            "param_counts": {str(k): v for k, v in param_counts.items()},
            "min_params": p_min,
            "max_params": p_max,
            "note": "black-box and hybrid share the same 2-input MLPRegressor architecture "
                    "at every trial (same hidden_layer_sizes/lr/alpha grid), so trainable "
                    "parameter counts are identical by construction at each trial (ratio 0%), "
                    "not merely within the 10% tolerance.",
        },
        "target_basis": "noisy",
        "per_repetition": per_rep,
        "medians": {
            "bb_extra_rmse": median_bb_extra,
            "bb_interp_rmse": median_bb_interp,
            "hyb_extra_rmse": median_hyb_extra,
            "hyb_interp_rmse": median_hyb_interp,
            "ep_extra_rmse": median_ep_extra,
        },
        "wilcoxon": {
            "diffs": diffs.tolist(),
            "p_value_one_sided": p_value,
            "hybrid_win_count": win_count,
            "n_repetitions": len(per_rep),
        },
        "claims": {
            "C0": c0_status,
            "C1": c1_status,
            "C2": c2_status,
            "C3": c3_status,
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    result = run(cfg)
    result["_run_environment"] = {
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {args.out}")
    print(json.dumps(result["claims"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
