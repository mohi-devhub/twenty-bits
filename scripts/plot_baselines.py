"""Publication-independent baseline figures from the completed offline sweep."""

from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from twenty_bits.worlds import ROOT


def main():
    rows = json.loads((ROOT / "results/baselines/summary.json").read_text())
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.titleweight": "bold",
            "svg.fonttype": "none",
            "svg.hashsalt": "twenty-bits",
        }
    )
    colors = {
        "random": "#88958b",
        "greedy_single": "#318478",
        "greedy_predicate": "#b65b32",
    }
    labels = {
        "random": "Random attribute",
        "greedy_single": "Greedy attribute",
        "greedy_predicate": "Greedy predicate",
    }
    for metric, caption, filename in [
        ("eig_per_question", "Expected bits per question", "baseline-eig"),
        ("win_rate", "Win rate", "baseline-wins"),
        ("questions_per_win", "Questions per win", "baseline-questions"),
    ]:
        fig, axes = plt.subplots(2, 4, figsize=(14, 6.5), sharex=True)
        for r, p in enumerate([0, 0.1]):
            for c, domain in enumerate(["animals", "tools", "foods", "synthetic"]):
                ax = axes[r, c]
                for policy in colors:
                    data = sorted(
                        [
                            row
                            for row in rows
                            if row["domain"] == domain
                            and row["noise"] == p
                            and row["policy"] == policy
                        ],
                        key=lambda z: z["n"],
                    )
                    x = np.array([d["n"] for d in data])
                    y = np.array([d[metric] for d in data])
                    ci = np.array([d[metric + "_ci95"] for d in data])
                    ax.plot(
                        x,
                        y,
                        marker="o",
                        markersize=3,
                        color=colors[policy],
                        label=labels[policy],
                    )
                    ax.fill_between(
                        x,
                        ci[:, 0],
                        ci[:, 1],
                        alpha=0.12,
                        color=colors[policy],
                        linewidth=0,
                    )
                if metric == "eig_per_question":
                    ax.axhline(
                        1 if not p else 0.5310044064,
                        color="#253c32",
                        linestyle="--",
                        linewidth=0.9,
                        label="Answer-channel ceiling",
                    )
                    ax.set_ylim(0, 1.07)
                elif metric == "win_rate":
                    ax.set_ylim(0, 1.05)
                else:
                    ax.plot(
                        x,
                        np.log2(x),
                        color="#253c32",
                        linestyle="--",
                        linewidth=0.9,
                        label="log₂ N reference",
                    )
                ax.set_xscale("log", base=2)
                ax.set_xticks([16, 32, 64, 128, 256], ["16", "32", "64", "128", "256"])
                ax.grid(axis="y", alpha=0.18)
                ax.set_title(f"{domain.title()} · p = {p:.2f}", fontsize=10)
                if c == 0:
                    ax.set_ylabel(caption)
                if r == 1:
                    ax.set_xlabel("Candidate count")
        handles, legend = axes[0, 0].get_legend_handles_labels()
        fig.legend(
            handles,
            legend,
            loc="lower center",
            ncol=4,
            frameon=False,
            bbox_to_anchor=(0.5, -0.005),
        )
        fig.suptitle(
            f"Offline baselines · {caption.lower()}",
            fontsize=16,
            x=0.07,
            ha="left",
            y=0.995,
        )
        fig.text(
            0.07,
            0.935,
            "200 paired games per cell · bands show 95% bootstrap intervals over complete games",
            fontsize=9,
            color="#53655b",
        )
        fig.tight_layout(rect=[0, 0.05, 1, 0.93])
        for suffix in ["png", "svg"]:
            fig.savefig(
                ROOT / f"results/baselines/{filename}.{suffix}",
                dpi=180,
                bbox_inches="tight",
            )
        for svg in (ROOT / "results/baselines").glob(filename + ".svg"):
            svg.write_text(
                "\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n"
            )
        plt.close(fig)


if __name__ == "__main__":
    main()
