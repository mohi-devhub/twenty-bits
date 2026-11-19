"""Show every scheduled endpoint and the fixed development checks."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from twenty_bits.worlds import ROOT


COLORS = {"Raw": "#8a9ba5", "A11": "#246c94", "A23": "#b76834", "B41": "#277d60"}


def save(fig, folder, name):
    fig.savefig(folder / f"{name}.png", dpi=180)
    path = folder / f"{name}.svg"
    fig.savefig(path)
    path.write_text(
        "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
    )
    plt.close(fig)


def main():
    folder = ROOT / "results/main_B41/charts"
    folder.mkdir(parents=True, exist_ok=True)
    data = json.loads((ROOT / "results/main_B41/all_seeds.json").read_text())
    references = json.loads(
        (ROOT / "results/phase2/matched_baselines.json").read_text()
    )
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
        }
    )
    cells = [
        ("animals", 32),
        ("animals", 128),
        ("synthetic", 32),
        ("synthetic", 128),
        ("synthetic", 256),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for col, noise in enumerate([0, 0.1]):
        for row, key, title in [
            (0, "eig_per_question", "Expected bits/question"),
            (1, "win_rate", "Win rate"),
        ]:
            ax = axes[row, col]
            for shift, (policy, color) in zip(
                [-0.27, -0.09, 0.09, 0.27], COLORS.items()
            ):
                selected = [
                    next(
                        r
                        for r in data["cells"]
                        if (r["domain"], r["n"], r["noise"], r["policy"])
                        == (domain, n, noise, policy)
                    )
                    for domain, n in cells
                ]
                y = np.array([r[key] for r in selected])
                ci = [r["ci95"][key]["ci95"] for r in selected]
                errors = np.maximum(
                    0,
                    np.array(
                        [
                            y - np.array([r[0] for r in ci]),
                            np.array([r[1] for r in ci]) - y,
                        ]
                    ),
                )
                ax.errorbar(
                    np.arange(5) + shift,
                    y,
                    yerr=errors,
                    fmt="o",
                    ms=5,
                    capsize=2,
                    color=color,
                    label=policy,
                )
            baseline = [
                next(
                    r
                    for r in references
                    if (r["domain"], r["n"], r["noise"], r["policy"])
                    == (domain, n, noise, "greedy_predicate")
                )
                for domain, n in cells
            ]
            ax.plot(
                np.arange(5),
                [r[key] for r in baseline],
                ls=":",
                color="#98742f",
                lw=1.5,
                label="Matched greedy predicate",
            )
            if key == "eig_per_question":
                ax.axhline(
                    1 if noise == 0 else 0.5310044064,
                    color="#596d77",
                    ls="--",
                    lw=1,
                    label="Answer-channel ceiling",
                )
            ax.set(
                title=f"{title} · p={noise:g}",
                xticks=range(5),
                xticklabels=[f"{d}\nN={n}" for d, n in cells],
                ylim=(-0.03, 1.05),
            )
            ax.grid(axis="y", alpha=0.2)
            if row == 0:
                ax.legend(
                    frameon=False,
                    fontsize=8,
                    loc="upper right" if noise else "lower right",
                )
    fig.suptitle(
        "Twenty Bits · all scheduled main endpoints", fontsize=16, fontweight="bold"
    )
    fig.supxlabel(
        "28 paired games per cell. Error bars resample games within each fitted endpoint; A has two training seeds, B has one.",
        fontsize=9,
    )
    save(fig, folder, "all-endpoints")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    for policy in ["A11", "A23", "B41"]:
        summary = json.loads((ROOT / f"results/main_{policy}/summary.json").read_text())
        dev = summary["development"]
        x = [int(i) for i in dev]
        for ax, key, title in zip(
            axes,
            ["eig_per_question", "win_rate", "mean_reward"],
            ["EIG/question", "Win rate", "Mean reward"],
        ):
            y = [dev[str(i)]["point"][key] for i in x]
            ax.plot(x, y, marker="o", ms=4, color=COLORS[policy], label=policy)
            ax.set(
                title=title,
                xlabel="Optimizer update",
                xticks=[0, 4, 8, 12, 16, 20, 24, 28, 30],
            )
            ax.grid(axis="y", alpha=0.2)
    axes[0].axhline(1, color="#596d77", ls="--", lw=1)
    axes[0].set_ylim(-0.02, 1.04)
    axes[1].set_ylim(-0.02, 1.04)
    axes[0].legend(frameon=False)
    fig.suptitle(
        "The same eight noiseless development games · no checkpoint selection",
        fontsize=14,
        fontweight="bold",
    )
    fig.supxlabel(
        "Four N=4 and four N=8 cases. Curves show fixed-case behavior; they do not assess large-N or noisy training performance.",
        fontsize=9,
    )
    save(fig, folder, "all-development")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), constrained_layout=True)
    for ax, key, title in zip(
        axes,
        ["ambiguous_guess_rate", "no_guess_rate"],
        ["GUESS with multiple candidates / game", "No GUESS / game"],
    ):
        for shift, (policy, color) in zip([-0.27, -0.09, 0.09, 0.27], COLORS.items()):
            selected = [
                next(
                    r
                    for r in data["cells"]
                    if (r["domain"], r["n"], r["noise"], r["policy"])
                    == (domain, n, 0, policy)
                )
                for domain, n in cells
            ]
            ax.plot(
                np.arange(5) + shift,
                [r[key] for r in selected],
                "o",
                color=color,
                label=policy,
            )
        ax.set(
            title=title,
            xticks=range(5),
            xticklabels=[f"{d}\nN={n}" for d, n in cells],
            ylim=(-0.03, 1.05),
        )
        ax.grid(axis="y", alpha=0.2)
    axes[0].legend(frameon=False, ncols=2)
    fig.suptitle(
        "Noiseless stopping behavior · every game stays in the denominator",
        fontsize=14,
        fontweight="bold",
    )
    save(fig, folder, "all-stopping")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), constrained_layout=True)
    for shift, (policy, color) in zip([-0.27, -0.09, 0.09, 0.27], COLORS.items()):
        selected = [
            next(
                r
                for r in data["cells"]
                if (r["domain"], r["n"], r["noise"], r["policy"])
                == (domain, n, 0.1, policy)
            )
            for domain, n in cells
        ]
        for ax, key, title in zip(
            axes,
            ["low_probability_reasks", "low_probability_opportunities"],
            ["Next-action semantic re-asks", "Opportunities after unlikely replies"],
        ):
            ax.plot(
                np.arange(5) + shift,
                [r[key] for r in selected],
                "o",
                color=color,
                label=policy,
            )
            ax.set(
                title=title,
                xticks=range(5),
                xticklabels=[f"{d}\nN={n}" for d, n in cells],
            )
            ax.grid(axis="y", alpha=0.2)
    baseline = [
        next(
            r
            for r in references
            if (r["domain"], r["n"], r["noise"], r["policy"])
            == (domain, n, 0.1, "greedy_predicate")
        )
        for domain, n in cells
    ]
    opportunities = [r["low_probability_opportunities"] for r in baseline]
    repeats = [
        round(n * r["reask_after_low_probability_rate"]) if n else 0
        for n, r in zip(opportunities, baseline)
    ]
    axes[0].plot(np.arange(5), repeats, "x", color="#98742f", label="Greedy Bayesian")
    axes[1].plot(
        np.arange(5), opportunities, "x", color="#98742f", label="Greedy Bayesian"
    )
    axes[0].legend(frameon=False, ncols=2)
    fig.suptitle(
        "Noisy games · report re-check numerators and denominators",
        fontsize=14,
        fontweight="bold",
    )
    fig.supxlabel(
        "An unlikely answer has predictive probability <0.20. A repeat may be uninformative; counts alone do not establish robustness.",
        fontsize=9,
    )
    save(fig, folder, "all-rechecks")


if __name__ == "__main__":
    main()
