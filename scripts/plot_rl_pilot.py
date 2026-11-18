"""Clean pilot learning curves and two preselected side-by-side transcripts."""

import gzip
import html
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.baselines import play
from twenty_bits.prompts import prefix
from twenty_bits.worlds import ROOT, World


def main():
    folder = ROOT / "results/pilot_A"
    summary = json.loads((folder / "summary.json").read_text())
    rows = summary["updates"]
    dev = {int(k): v for k, v in summary["development"].items()}
    x = np.array([r["update"] for r in rows])
    dx = np.array(sorted(dev))

    def numeric(value):
        return np.nan if value is None else float(value)

    manifest = json.loads((ROOT / "experiments/pilot_A_games.json").read_text())
    greedy = [play(r, "greedy_predicate") for r in manifest["development"]]
    reference = sum(sum(g["question_eigs"]) for g in greedy) / sum(
        g["questions"] for g in greedy
    )
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "svg.fonttype": "none",
        }
    )
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    plots = [
        ("eig_per_question", "Expected bits per question"),
        ("win_rate", "Win rate"),
        ("mean_reward", "Mean game reward"),
        ("questions_per_win", "Questions per win"),
        ("output_tokens_per_game", "Generated tokens per game"),
        ("cumulative_nonzero_group_fraction", "Cumulative groups with return variance"),
    ]
    for ax, (key, title) in zip(axes.flat, plots):
        y = [r.get(key) if r.get(key) is not None else np.nan for r in rows]
        ax.plot(
            x,
            y,
            color="#70a1c6",
            alpha=0.8,
            lw=1.5,
            marker="o",
            ms=4,
            label="On-policy group",
        )
        if key != "cumulative_nonzero_group_fraction":
            vals = [numeric(dev[int(i)]["point"][key]) for i in dx]
            ax.plot(
                dx,
                vals,
                color="#163c58",
                marker="o",
                lw=2,
                label="Fixed development games",
            )
            if key in ("eig_per_question", "win_rate", "questions_per_win"):
                lo = np.array(
                    [numeric(dev[int(i)]["ci95"][key + "_ci95"][0]) for i in dx]
                )
                hi = np.array(
                    [numeric(dev[int(i)]["ci95"][key + "_ci95"][1]) for i in dx]
                )
                ax.fill_between(dx, lo, hi, color="#163c58", alpha=0.10, lw=0)
        else:
            ax.axhline(
                0.25, color="#aa673b", ls="--", lw=1, label="Four-update stop threshold"
            )
        if key == "eig_per_question":
            ax.axhline(1, color="#2a826b", ls="--", lw=1, label="Noiseless ceiling")
            ax.axhline(
                reference,
                color="#ad8037",
                ls=":",
                lw=1,
                label="Matched greedy predicate",
            )
        if key in ("eig_per_question", "win_rate", "cumulative_nonzero_group_fraction"):
            ax.set_ylim(-0.03, 1.06)
        ax.axvline(4.5, color="#d3dce3", lw=1)
        ax.axvline(12.5, color="#d3dce3", lw=1)
        ax.set_title(title, loc="left", pad=10)
        ax.set_xlabel("Optimizer update")
        ax.set_xticks([0, 4, 8, 12, 16])
        ax.set_xlim(-0.4, max(16, x[-1]) + 0.4)
        ax.grid(axis="y", color="#dce4e9", lw=0.6, alpha=0.7)
    axes[0, 0].legend(frameon=False, fontsize=8, loc="lower right")
    axes[-1, -1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle(
        "Twenty Bits · Pilot A with candidate feedback", fontsize=17, fontweight="bold"
    )
    fig.supxlabel(
        "One seed; 8 games per group. N=4 at updates 1–4, N=8 at 5–12, N=16 at 13–16.\nDevelopment: the same 8 noiseless games at each check; shaded intervals resample games, not seeds.",
        fontsize=9,
    )
    charts = folder / "charts"
    charts.mkdir(exist_ok=True)
    fig.savefig(charts / "pilot-learning.png", dpi=180)
    fig.savefig(charts / "pilot-learning.svg")
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.2), constrained_layout=True)
    for ax, key, title in zip(
        axes,
        ["enumeration_rate", "invalid_question_rate", "post_budget_non_guesses"],
        [
            "Item-name enumeration / question",
            "Invalid questions / question",
            "Non-GUESS actions after budget",
        ],
    ):
        ax.plot(x, [r[key] for r in rows], marker="o", color="#163c58", ms=4)
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_xlabel("Update")
        ax.set_xticks([4, 8, 12, 16])
        ax.grid(axis="y", alpha=0.2)
        if key != "post_budget_non_guesses":
            ax.set_ylim(-0.03, 1.03)
    fig.savefig(charts / "pilot-behavior.png", dpi=180)
    fig.savefig(charts / "pilot-behavior.svg")
    plt.close(fig)
    for path in charts.glob("*.svg"):
        path.write_text(
            "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
        )
    pairs = [
        json.loads(line) for line in gzip.open(folder / "example_games.jsonl.gz", "rt")
    ]
    lines = [
        "# Paired pilot games",
        "",
        "These two development targets were selected before training. The raw-base games are from update 0; the comparison uses the last scheduled development snapshot. Neither case entered gradients. They illustrate strategy and are not representative performance samples.",
        "",
    ]
    for pair in pairs:
        record = pair["record"]
        base = pair["base"]
        final = pair["final"]
        lines.extend(
            [
                f"## {record['id']}",
                "",
                f"Hidden target: `{record['world']['names'][record['target']]}`. N={record['n']}. Final policy update: {final['policy_step']}.",
                "",
                f"Raw base: {'win' if base['won'] else 'loss'}, {base['questions']} questions, EIG/question {base['eig_per_question']:.3f}. RL: {'win' if final['won'] else 'loss'}, {final['questions']} questions, EIG/question {final['eig_per_question']:.3f}.",
                "",
                "| Turn | Raw base action → answer | RL action → answer |",
                "| ---: | --- | --- |",
            ]
        )
        for i in range(max(len(base["turns"]), len(final["turns"]))):
            cells = []
            for game in (base, final):
                if i >= len(game["turns"]):
                    cells.append("—")
                    continue
                t = game["turns"][i]
                action = (
                    html.escape(t["raw_action"])
                    .replace("|", "&#124;")
                    .replace("\n", "<br>")
                )
                remaining = sum(p > 0 for p in t["posterior_after"])
                cells.append(
                    f"<code>{action}</code> → **{t['answer']}**<br>{remaining} remaining; EIG {t['eig']:.3f}"
                )
            lines.append(f"| {i + 1} | {cells[0]} | {cells[1]} |")
        lines.extend(
            [
                "",
                "Candidate table, shared by both players:",
                "",
                "```text",
                "DOMAIN "
                + prefix(World.from_dict(record["world"])).split("\nDOMAIN ", 1)[1],
                "```",
                "",
            ]
        )
    (folder / "EXAMPLE_GAMES.md").write_text("\n".join(lines))
    (folder / "plot_metadata.json").write_text(
        json.dumps(
            {
                "matched_greedy_development_eig": reference,
                "graphs_are_development_not_frozen_evaluation": True,
                "png_and_svg": True,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
