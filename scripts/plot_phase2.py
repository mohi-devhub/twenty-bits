"""Plot base policy versus matched offline baselines. No service calls."""

from pathlib import Path
import gzip
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scripts.run_baselines import summarize
from twenty_bits.information import binary_entropy
from twenty_bits.worlds import ROOT


def main():
    directory = ROOT / "results/phase2"
    data = json.loads((directory / "summary.json").read_text())
    if data["status"] != "complete":
        raise ValueError("Complete all approved games before plotting the gate report.")
    config = json.loads((ROOT / "evals/phase2.json").read_text())
    model = config["primary_model"]
    cases = [
        ("animals", 32),
        ("animals", 128),
        ("synthetic", 32),
        ("synthetic", 128),
        ("synthetic", 256),
    ]
    outputs = [
        json.loads(line)
        for line in gzip.decompress(
            (directory / "games.jsonl.gz").read_bytes()
        ).splitlines()
    ]
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "twenty-bits-phase2",
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
    fig.subplots_adjust(
        left=0.075, right=0.985, bottom=0.12, top=0.78, wspace=0.20, hspace=0.10
    )
    baseline_rows = []
    for column, noise in enumerate([0, 0.1]):
        for policy, label, color, offset in [
            ("random", "Random", "#a3aaa6", -0.21),
            ("greedy_single", "Greedy attribute", "#8899bf", -0.07),
            ("greedy_predicate", "Greedy predicate", "#328768", 0.07),
            ("base", "Qwen3-8B base", "#d67543", 0.21),
        ]:
            points = []
            for domain, n in cases:
                cell = next(
                    c
                    for c in data["cells"]
                    if (c["model"], c["domain"], c["n"], c["noise"])
                    == (model, domain, n, noise)
                )
                if policy == "base":
                    points.append(cell)
                else:
                    eligible = {
                        g["game_id"]
                        for g in outputs
                        if (g["model"], g["domain"], g["n"], g["noise"])
                        == (model, domain, n, noise)
                    }
                    raw = gzip.decompress(
                        (
                            ROOT
                            / f"results/baselines/frozen/{domain}_n{n}_p{noise:.2f}.jsonl.gz"
                        ).read_bytes()
                    )
                    games = [json.loads(line) for line in raw.splitlines()]
                    games = [
                        g
                        for g in games
                        if g["policy"] == policy and g["game_id"] in eligible
                    ]
                    point = {
                        "domain": domain,
                        "n": n,
                        "noise": noise,
                        "policy": policy,
                        **summarize(games, bootstrap=10000),
                    }
                    baseline_rows.append(point)
                    points.append(point)
            for row, metric in enumerate(["eig_per_question", "win_rate"]):
                values = np.array(
                    [p[metric] if p[metric] is not None else np.nan for p in points]
                )
                intervals = [p[metric + "_ci95"] for p in points]
                lower = np.array([ci[0] if ci else np.nan for ci in intervals])
                upper = np.array([ci[1] if ci else np.nan for ci in intervals])
                axes[row, column].errorbar(
                    np.arange(5) + offset,
                    values,
                    yerr=[np.maximum(0, values - lower), np.maximum(0, upper - values)],
                    fmt="o",
                    markersize=5,
                    capsize=3,
                    color=color,
                    label=label,
                )
        ceiling = 1 - binary_entropy(noise)
        axes[0, column].axhline(
            ceiling,
            color="#555b57",
            linestyle="--",
            linewidth=1,
            label="Channel ceiling",
        )
        axes[0, column].set_title(
            ("Truthful answers" if noise == 0 else "10% answer flips")
            + f" · maximum {ceiling:.3f}"
        )
        axes[0, column].set_ylim(-0.025, 1.055)
        axes[1, column].set_ylim(-0.025, 1.055)
        axes[0, column].grid(axis="y", alpha=0.18)
        axes[1, column].grid(axis="y", alpha=0.18)
        axes[1, column].set_xticks(range(5), [f"{d.title()}\nN={n}" for d, n in cases])
    axes[0, 0].set_ylabel("Expected bits per question")
    axes[1, 0].set_ylabel("Win rate")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.89),
        ncol=5,
        frameon=False,
        fontsize=10,
    )
    fig.text(
        0.075,
        0.015,
        "Win bootstrap intervals collapse at observed 0 or 1; supplementary Wilson bounds are in the data.",
        fontsize=9,
        color="#555b57",
    )
    fig.suptitle(
        "Twenty Bits · base policy and matched baselines\n28 frozen games per cell; 95% game-bootstrap intervals; no RL training",
        fontsize=15,
    )
    destination = directory / "charts"
    destination.mkdir(exist_ok=True)
    fig.savefig(destination / "base-v-baselines.png", dpi=170)
    path = destination / "base-v-baselines.svg"
    fig.savefig(path, metadata={"Date": None})
    path.write_text(
        "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
    )
    plt.close(fig)
    (directory / "matched_baselines.json").write_text(
        json.dumps(baseline_rows, indent=2, allow_nan=False) + "\n"
    )
    print(destination)


if __name__ == "__main__":
    main()
