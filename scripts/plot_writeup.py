"""Consistent final figures from the accepted, archived measurements."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from twenty_bits.worlds import ROOT

POLICY_COLORS = {"Raw": "#687583", "A11": "#3D62A9", "A23": "#087A70", "B41": "#B45C2B"}
OUTCOMES = {
    "win": ("Win", "#287E72"),
    "ambiguous_wrong_guess": ("Ambiguous wrong guess", "#C76F36"),
    "no_guess": ("No guess", "#798291"),
    "other": ("Other loss", "#D3D6DD"),
}


def save(fig, name):
    folder = ROOT / "results/writeup/charts"
    folder.mkdir(parents=True, exist_ok=True)
    fig.savefig(folder / f"{name}.png", dpi=190, facecolor=fig.get_facecolor())
    path = folder / f"{name}.svg"
    fig.savefig(path, metadata={"Date": None})
    path.write_text(
        "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
    )
    plt.close(fig)


def eig_panel(ax, data, baseline):
    names = list(POLICY_COLORS)
    for index, name in enumerate(names):
        row = data["animal_noiseless"][name]
        mean, (low, high) = row["eig_per_question"], row["ci95"]
        ax.bar(index, mean, color=POLICY_COLORS[name], width=0.61)
        ax.errorbar(
            index,
            mean,
            yerr=[[mean - low], [high - mean]],
            fmt="none",
            capsize=4,
            color="#253647",
            lw=1.3,
        )
        ax.text(
            index,
            high + 0.035,
            f"{mean:.3f}",
            ha="center",
            fontweight="bold",
            fontsize=11,
        )
    ax.axhline(1, color="#66717B", ls="--", lw=1)
    ax.axhline(baseline, color="#B59A52", ls=":", lw=1.8)
    ax.text(3.7, 1.012, "1 bit ceiling", ha="right", fontsize=9, color="#59636E")
    ax.text(
        3.7,
        baseline - 0.035,
        f"Greedy predicate {baseline:.3f}",
        ha="right",
        va="top",
        fontsize=9,
        color="#816A2F",
    )
    ax.set(
        xticks=range(4),
        xticklabels=names,
        ylim=(0, 1.1),
        ylabel="Expected bits per question",
        title="Animal questions become more informative",
    )
    ax.grid(axis="y", alpha=0.16)
    ax.set_axisbelow(True)


def stack(ax, rows, labels, totals, *, legend=False):
    left = np.zeros(len(rows))
    for key, (title, color) in OUTCOMES.items():
        values = np.array([row[key] for row in rows])
        ax.barh(
            range(len(rows)), values, left=left, color=color, height=0.61, label=title
        )
        for index, value in enumerate(values):
            if value >= max(2, totals[index] * 0.045):
                ax.text(
                    left[index] + value / 2,
                    index,
                    str(value),
                    ha="center",
                    va="center",
                    color="#FFFFFF" if key != "other" else "#263445",
                    fontsize=11,
                    fontweight="bold",
                )
        left += values
    assert list(left) == totals
    ax.set(
        yticks=range(len(rows)),
        yticklabels=labels,
        xlim=(0, max(totals)),
        xlabel="Games",
    )
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.12)
    ax.set_axisbelow(True)
    if legend:
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncols=2,
            frameon=False,
            fontsize=9,
        )


def main():
    data = json.loads((ROOT / "results/writeup/numbers.json").read_text())
    references = json.loads(
        (ROOT / "results/phase2/matched_baselines.json").read_text()
    )
    baseline = np.mean(
        [
            r["eig_per_question"]
            for r in references
            if r["domain"] == "animals"
            and r["noise"] == 0
            and r["n"] in (32, 128)
            and r["policy"] == "greedy_predicate"
        ]
    )
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "figure.facecolor": "#FAF8F2",
            "axes.facecolor": "#FAF8F2",
            "text.color": "#253647",
            "axes.labelcolor": "#253647",
            "xtick.color": "#4A5765",
            "ytick.color": "#4A5765",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.edgecolor": "#B7BEC4",
            "axes.titleweight": "bold",
            "axes.titlepad": 16,
            "svg.fonttype": "none",
            "svg.hashsalt": "twenty-bits-writeup-v1",
        }
    )
    fig, ax = plt.subplots(figsize=(8.4, 4.8), layout="constrained")
    eig_panel(ax, data, baseline)
    fig.supxlabel(
        "Noiseless animals, N=32 and 128, 28 paired games per size. 95% game-bootstrap CIs.",
        fontsize=9,
    )
    save(fig, "animal-eig")

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(13, 4.8),
        layout="constrained",
        gridspec_kw={"width_ratios": [1.15, 1]},
    )
    eig_panel(axes[0], data, baseline)
    stack(
        axes[1],
        [data["animal_noiseless"][name]["outcomes"] for name in POLICY_COLORS],
        list(POLICY_COLORS),
        [56] * 4,
        legend=True,
    )
    axes[1].set_title("Similar wins hide opposite failures")
    fig.suptitle(
        "Twenty Bits: better questions, unreliable stopping",
        fontsize=18,
        fontweight="bold",
    )
    fig.supxlabel(
        "Noiseless animals, N=32 and 128. EIG error bars are 95% game-bootstrap CIs conditional on each endpoint.\nOutcome-only RL, all scheduled endpoints shown. Two truthful-training seeds and one noisy-training seed.",
        fontsize=9,
    )
    save(fig, "headline")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    stack(
        axes[0],
        [data["animal_noiseless"][name]["outcomes"] for name in POLICY_COLORS],
        list(POLICY_COLORS),
        [56] * 4,
        legend=True,
    )
    axes[0].set_title("Noiseless animals: 56 games per policy")
    stack(
        axes[1],
        [data["outcomes"]["primary"][name]["outcomes"] for name in POLICY_COLORS],
        list(POLICY_COLORS),
        [280] * 4,
        legend=True,
    )
    axes[1].set_title("Full primary bank: 280 games per policy")
    fig.suptitle("Same-ish wins, different policies", fontsize=17, fontweight="bold")
    fig.supxlabel(
        "Ambiguous means multiple displayed candidates before GUESS. Wins include lucky guesses. Context losses count as no guess.",
        fontsize=9,
    )
    save(fig, "different-failures")

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12, 5.3),
        layout="constrained",
        gridspec_kw={"width_ratios": [1.4, 1]},
    )
    labels, rows = [], []
    for name in ("Raw", "A23", "B41"):
        for stage, label in [
            ("primary", "primary"),
            ("visible_budget", "budget visible"),
        ]:
            labels.append(f"{name} / {label}")
            rows.append(data["outcomes"][stage][name]["outcomes"])
    stack(axes[0], rows, labels, [280] * 6, legend=True)
    axes[0].set_title("The counter removes final-ASK stalling")
    for index, name in enumerate(("Raw", "A23", "B41")):
        old = data["outcomes"]["primary"][name]["ambiguous_with_budget_left"]
        new = data["outcomes"]["visible_budget"][name]["ambiguous_with_budget_left"]
        axes[1].plot(
            [0, 1], [old, new], "o-", lw=2, color=POLICY_COLORS[name], label=name
        )
        axes[1].text(-0.06, old, str(old), ha="right", va="center", fontsize=10)
        axes[1].text(1.06, new, str(new), ha="left", va="center", fontsize=10)
    axes[1].set(
        xticks=[0, 1],
        xticklabels=["Primary", "Visible budget"],
        ylim=(0, 225),
        xlim=(-0.35, 1.35),
        ylabel="Ambiguous guesses with questions left / 280",
        title="Gambling persists",
    )
    axes[1].legend(frameon=False)
    axes[1].grid(axis="y", alpha=0.16)
    fig.suptitle(
        "Fixed policies, one added observation", fontsize=17, fontweight="bold"
    )
    fig.supxlabel(
        "Identical frozen games and requested generation seeds. No training. A11 unavailable. The new prompt can also change questions.",
        fontsize=9,
    )
    save(fig, "visible-budget")

    fig, ax = plt.subplots(figsize=(8.6, 4.7), layout="constrained")
    for index, (name, color) in enumerate(POLICY_COLORS.items()):
        row = data["noisy"][name]
        mean = row["win_rate"]
        lo, hi = row["ci95"]
        ax.bar(index, mean, color=color, width=0.6)
        ax.errorbar(
            index,
            mean,
            yerr=[[mean - lo], [hi - mean]],
            fmt="none",
            color="#253647",
            capsize=4,
        )
        ax.text(index, hi + 0.015, f"{row['wins']}/140", ha="center", fontweight="bold")
    ax.axhline(
        data["noisy"]["Raw"]["win_rate"], color=POLICY_COLORS["Raw"], ls="--", lw=1
    )
    ax.set(
        xticks=range(4),
        xticklabels=[
            "Raw",
            "A11\ntrained p=0",
            "A23\ntrained p=0",
            "B41\ntrained p=0.10",
        ],
        ylabel="Win rate with 10% answer noise",
        ylim=(0, 0.49),
        title="No trained seed beats raw base on primary noisy wins",
    )
    ax.grid(axis="y", alpha=0.16)
    ax.set_axisbelow(True)
    fig.supxlabel(
        "140 games per policy across five cells. Stratified 95% game-bootstrap CIs, conditional on each endpoint.",
        fontsize=9,
    )
    save(fig, "noisy-wins")

    fig, axes = plt.subplots(2, 2, figsize=(12, 7.6), layout="constrained")
    for ax, key, label in zip(
        axes.flat,
        ["eig_per_question", "win_rate", "mean_reward", "questions_per_win"],
        [
            "Expected bits per question",
            "Win rate",
            "Mean outcome reward",
            "Questions per win",
        ],
    ):
        for name in ("A11", "A23", "B41"):
            entries = data["development"][name]
            x = sorted(int(i) for i in entries)
            y = [
                entries[str(i)]["point"][key]
                if entries[str(i)]["point"][key] is not None
                else np.nan
                for i in x
            ]
            ax.plot(x, y, "o-", lw=1.7, ms=4, color=POLICY_COLORS[name], label=name)
        ax.set(
            xlabel="Training update",
            ylabel=label,
            xticks=[0, 4, 8, 12, 16, 20, 24, 28, 30],
        )
        ax.grid(alpha=0.15)
    axes[0, 0].axhline(1, ls="--", lw=1, color="#6D7885")
    axes[0, 0].set_ylim(0, 1.05)
    axes[0, 1].set_ylim(0, 1.05)
    axes[0, 0].legend(frameon=False)
    fig.suptitle(
        "Development improves while stopping failures survive",
        fontsize=17,
        fontweight="bold",
    )
    fig.supxlabel(
        "Same eight noiseless training-pool cases: four at N=4 and four at N=8. Scheduled checks only; no checkpoint selection.\nThese descriptive curves do not measure noisy play or large-N transfer. Undefined questions/win are gaps.",
        fontsize=9,
    )
    save(fig, "development")
    print("Saved six figures as PNG and SVG under results/writeup/charts.")


if __name__ == "__main__":
    main()
