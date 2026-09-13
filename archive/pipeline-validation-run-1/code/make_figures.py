"""make_figures.py — venue-neutral figure/table renders from processed results.

Reads only data/processed/<run-id>.json (the fouling-benchmark result) and
writes PNG figures under figures/ plus a Markdown table fragment used to
build docs/sections/04-results.md's table. All venue-specific rendering
(format, DPI, width, colour mode) happens later in submission-manage via
figure-profile.json; this script only produces the venue-neutral working
images used while drafting, and every such setting here is a CLI parameter,
not a hard-coded value.

Re-run exactly as recorded in its own manifest:
    "/c/Python313/python.exe" code/make_figures.py \
        --result data/processed/fouling-benchmark-2026-09-13.json \
        --outdir figures \
        --dpi 150 --width-in 6.0 --format png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load(result_path: Path) -> dict:
    return json.loads(result_path.read_text(encoding="utf-8"))


def fig1_extrapolation_vs_interpolation(data: dict, outdir: Path, dpi: int, width_in: float, fmt: str) -> Path:
    """Paired per-repetition RMSE: black-box and hybrid, interpolation vs extrapolation."""
    reps = data["per_repetition"]
    seeds = [r["seed"] for r in reps]
    bb_interp = [r["bb_interp_rmse"] for r in reps]
    bb_extra = [r["bb_extra_rmse"] for r in reps]
    hyb_interp = [r["hyb_interp_rmse"] for r in reps]
    hyb_extra = [r["hyb_extra_rmse"] for r in reps]

    fig, axes = plt.subplots(1, 2, figsize=(width_in * 2, width_in * 0.85), sharey=True)

    x = np.arange(len(seeds))
    width = 0.35

    ax = axes[0]
    ax.bar(x - width / 2, bb_interp, width, label="black-box", color="#4C72B0")
    ax.bar(x + width / 2, hyb_interp, width, label="hybrid", color="#DD8452")
    ax.set_title("Interpolation RMSE (central-box held-out)")
    ax.set_xlabel("repetition (seed)")
    ax.set_ylabel("RMSE (native fouling-resistance units)")
    ax.set_xticks(x)
    ax.set_xticklabels(seeds)
    ax.legend()

    ax = axes[1]
    ax.bar(x - width / 2, bb_extra, width, label="black-box", color="#4C72B0")
    ax.bar(x + width / 2, hyb_extra, width, label="hybrid", color="#DD8452")
    ax.set_title("Extrapolation RMSE (union-rule outer tail)")
    ax.set_xlabel("repetition (seed)")
    ax.set_xticks(x)
    ax.set_xticklabels(seeds)
    ax.tick_params(axis="y", labelleft=True)
    ax.legend()

    fig.suptitle("Per-repetition RMSE, black-box vs additive-residual hybrid (n=10 paired repetitions)")
    fig.tight_layout()
    out_path = outdir / f"fig1.{fmt}"
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path


def fig2_ep_baseline_coverage(data: dict, outdir: Path, dpi: int, width_in: float, fmt: str) -> Path:
    """Bar chart: fraction of central-box vs extrapolation points where EP predicts a positive rate."""
    coverage = data["ebert_panchal_coverage"]
    central_frac = coverage["central_box_positive_fraction"]
    extra_frac = coverage["extrapolation_positive_fraction"]

    fig, ax = plt.subplots(figsize=(width_in, width_in * 0.85))
    bars = ax.bar(["training envelope\n(central box)", "extrapolation\nregion (outer tail)"],
                   [central_frac * 100, extra_frac * 100], color=["#4C72B0", "#C44E52"])
    ax.set_ylabel("% of grid points with positive Ebert-Panchal net rate")
    ax.set_title("Ebert-Panchal baseline positive-rate coverage by region")
    ax.set_ylim(0, 100)
    for bar, frac in zip(bars, [central_frac, extra_frac]):
        ax.annotate(f"{frac * 100:.1f}%", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom")
    fig.tight_layout()
    out_path = outdir / f"fig2.{fmt}"
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path


def table1_medians(data: dict) -> str:
    m = data["medians"]
    w = data["wilcoxon"]
    lines = [
        "| Metric | Black-box | Hybrid | Ebert-Panchal only |",
        "|---|---|---|---|",
        f"| Median interpolation RMSE | {m['bb_interp_rmse']:.4f} | {m['hyb_interp_rmse']:.4f} | \u2014 |",
        f"| Median extrapolation RMSE | {m['bb_extra_rmse']:.4f} | {m['hyb_extra_rmse']:.4f} | {m['ep_extra_rmse']:.4f} |",
        f"| Extrapolation/interpolation ratio | {m['bb_extra_rmse'] / m['bb_interp_rmse']:.2f}x | {m['hyb_extra_rmse'] / m['hyb_interp_rmse']:.2f}x | \u2014 |",
        f"| Hybrid extrapolation wins (of {w['n_repetitions']}) | \u2014 | {w['hybrid_win_count']} | \u2014 |",
        f"| One-sided exact Wilcoxon p (hybrid < black-box) | \u2014 | {w['p_value_one_sided']:.4f} | \u2014 |",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--width-in", type=float, default=6.0)
    parser.add_argument("--format", type=str, default="png")
    args = parser.parse_args()

    data = load(args.result)
    args.outdir.mkdir(parents=True, exist_ok=True)

    fig1_path = fig1_extrapolation_vs_interpolation(data, args.outdir, args.dpi, args.width_in, args.format)
    fig2_path = fig2_ep_baseline_coverage(data, args.outdir, args.dpi, args.width_in, args.format)
    table_path = args.outdir / "table1.md"
    table_path.write_text(table1_medians(data), encoding="utf-8")

    print(f"wrote {fig1_path}")
    print(f"wrote {fig2_path}")
    print(f"wrote {table_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
