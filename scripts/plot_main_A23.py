"""Main A seed 23 curves, stopping behavior and paired examples."""

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
    folder = ROOT / "results/main_A23"
    summary = json.loads((folder / "summary.json").read_text())
    rows = summary["updates"]
    dev = {int(k): v for k, v in summary["development"].items()}
    x = np.array([r["update"] for r in rows])
    dx = np.array(sorted(dev))

    def numeric(value):
        return np.nan if value is None else float(value)

    manifest = json.loads(
        gzip.decompress((ROOT / "experiments/main_A23_games.json.gz").read_bytes())
    )
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
        ("ambiguous_guesses_per_game", "Guesses with multiple candidates remaining"),
    ]
    for ax, (key, title) in zip(axes.flat, plots):

        def point(row):
            return (
                row["guess_with_k_remaining"][key]
                if key == "ambiguous_guesses_per_game"
                else row.get(key)
            )

        y = [numeric(point(r)) for r in rows]
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
        vals = [numeric(point(dev[int(i)]["point"])) for i in dx]
        ax.plot(
            dx, vals, color="#163c58", marker="o", lw=2, label="Fixed development games"
        )
        if key in ("eig_per_question", "win_rate", "questions_per_win"):
            intervals = [dev[int(i)]["ci95"][key + "_ci95"] for i in dx]
            lo = np.array([numeric(ci[0]) if ci else np.nan for ci in intervals])
            hi = np.array([numeric(ci[1]) if ci else np.nan for ci in intervals])
            ax.fill_between(dx, lo, hi, color="#163c58", alpha=0.10, lw=0)
        if key == "eig_per_question":
            ax.axhline(1, color="#2a826b", ls="--", lw=1, label="Noiseless ceiling")
            ax.axhline(
                reference,
                color="#ad8037",
                ls=":",
                lw=1,
                label="Matched greedy predicate",
            )
        if key in ("eig_per_question", "win_rate", "ambiguous_guesses_per_game"):
            ax.set_ylim(-0.03, 1.06)
        if key == "output_tokens_per_game":
            ax.set_yscale("log")
            title += " (log scale)"
        for boundary in (2.5, 4.5, 15.5, 22.5, 26.5):
            ax.axvline(boundary, color="#d3dce3", lw=1)
        ax.set_title(title, loc="left", pad=10)
        ax.set_xlabel("Optimizer update")
        ax.set_xticks([0, 4, 8, 12, 16, 20, 24, 28, 30])
        ax.set_xlim(-0.4, max(16, x[-1]) + 0.4)
        ax.grid(axis="y", color="#dce4e9", lw=0.6, alpha=0.7)
    axes[0, 0].legend(frameon=False, fontsize=8, loc="lower right")
    axes[-1, -1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle(
        "Twenty Bits · Main A seed 23 with candidate feedback",
        fontsize=17,
        fontweight="bold",
    )
    fig.supxlabel(
        "One A seed; 8 games per group. Curriculum: N=4,8,16,32,64,128 at the vertical boundaries.\nDevelopment: the same 8 noiseless games at each check; shaded intervals resample games, not seeds.",
        fontsize=9,
    )
    charts = folder / "charts"
    charts.mkdir(exist_ok=True)
    fig.savefig(charts / "main-learning.png", dpi=180)
    fig.savefig(charts / "main-learning.svg")
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
        ax.set_xticks([4, 8, 12, 16, 20, 24, 28, 30])
        ax.grid(axis="y", alpha=0.2)
        if key != "post_budget_non_guesses":
            ax.set_ylim(-0.03, 1.03)
    fig.savefig(charts / "main-behavior.png", dpi=180)
    fig.savefig(charts / "main-behavior.svg")
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.4), constrained_layout=True)
    references = json.loads(
        (ROOT / "results/phase2/matched_baselines.json").read_text()
    )
    for column, noise in enumerate((0, 0.1)):
        cells = [
            r for r in summary["frozen_evaluation"]["cells"] if r["noise"] == noise
        ]
        labels = [f"{r['domain']}\nN={r['n']}" for r in cells]
        for row, key in enumerate(("eig_per_question", "win_rate")):
            ax = axes[row, column]
            for policy, label, color, shift in (
                ("base", "Raw base", "#9caeb9", -0.13),
                ("endpoint", "A seed 23, update 30", "#163c58", 0.13),
            ):
                y = np.array([numeric(r[policy][key]) for r in cells])
                ci = [r[policy][key + "_ci95"] for r in cells]
                lo = np.array([numeric(v[0]) if v else np.nan for v in ci])
                hi = np.array([numeric(v[1]) if v else np.nan for v in ci])
                ax.errorbar(
                    np.arange(len(cells)) + shift,
                    y,
                    yerr=np.maximum(0, [y - lo, hi - y]),
                    fmt="o",
                    capsize=3,
                    color=color,
                    label=label,
                )
            points = [
                next(
                    r
                    for r in references
                    if r["policy"] == "greedy_predicate"
                    and (r["domain"], r["n"], r["noise"])
                    == (c["domain"], c["n"], c["noise"])
                )
                for c in cells
            ]
            ax.plot(
                np.arange(len(cells)),
                [r[key] for r in points],
                marker="_",
                color="#ad8037",
                ls=":",
                label="Matched greedy predicate",
            )
            if key == "eig_per_question":
                ax.axhline(
                    1 if noise == 0 else 0.5310044064,
                    color="#2a826b",
                    ls="--",
                    lw=1,
                    label="Answer-channel ceiling",
                )
            ax.set_xticks(np.arange(len(cells)), labels)
            ax.set_ylim(-0.03, 1.06)
            ax.set_title(
                ("Expected bits / question" if row == 0 else "Win rate")
                + f" · p={noise:g}",
                loc="left",
            )
            ax.grid(axis="y", alpha=0.2)
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle(
        "Scheduled endpoint on the unchanged frozen slice",
        fontsize=16,
        fontweight="bold",
    )
    fig.supxlabel(
        "28 paired games per cell; 95% game-bootstrap intervals. One A seed; no between-seed uncertainty.",
        fontsize=9,
    )
    fig.savefig(charts / "frozen-endpoint.png", dpi=180)
    fig.savefig(charts / "frozen-endpoint.svg")
    plt.close(fig)
    for path in charts.glob("*.svg"):
        path.write_text(
            "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
        )
    pairs = [
        json.loads(line) for line in gzip.open(folder / "example_games.jsonl.gz", "rt")
    ]
    lines = [
        "# Paired main A seed 23 development games",
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
