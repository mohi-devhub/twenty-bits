"""Build the submission figures, matched metrics, and examples from saved games."""

from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from threadpoolctl import threadpool_limits

from scripts.build_writeup_data import POLICIES, endings
from twenty_bits.baselines import play
from twenty_bits.budget_followup_metrics import flags
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.worlds import ROOT

OUT = ROOT / "results/submission"
REFERENCES = ("random", "greedy_single", "greedy_predicate")
LABELS = {
    "Raw": "Raw Qwen3-8B",
    "A11": "A11",
    "A23": "A23",
    "B41": "B41",
    "random": "Random attribute",
    "greedy_single": "Greedy attribute",
    "greedy_predicate": "Greedy predicate",
}
COLORS = {
    "Raw": "#657584",
    "A11": "#3D62A9",
    "A23": "#087A70",
    "B41": "#AD501F",
    "random": "#7B7293",
    "greedy_single": "#7C671F",
    "greedy_predicate": "#5F4B19",
}


def rows(path):
    with gzip.open(ROOT / path, "rt") as file:
        return [json.loads(line) for line in file]


def primary_games():
    games = {}
    for policy in POLICIES[1:]:
        archive = rows(f"results/main_{policy}/games.jsonl.gz")
        games[policy] = [g for g in archive if g["kind"] == "eval_endpoint"]
        if policy == "A11":
            games["Raw"] = [g for g in archive if g["kind"] == "eval_base"]
    return games


def case_key(game):
    return (game["domain"], game["n"], game["noise"])


def numeric_index(game_id):
    return int(game_id.split("/")[-2])


def joined(games, records):
    by_id = {g["game_id"]: g for g in games}
    assert len(games) == len(by_id) == len(records)
    assert set(by_id) == {r["id"] for r in records}
    return [by_id[r["id"]] for r in records]


def totals(games):
    turns = [t for g in games for t in g["turns"] if t["is_question"]]
    wins = [g for g in games if g["won"]]
    assert len(turns) == sum(g["questions"] for g in games)
    return {
        "games": len(games),
        "wins": len(wins),
        "questions": len(turns),
        "winning_questions": sum(g["questions"] for g in wins),
        "questions_per_win": sum(g["questions"] for g in wins) / len(wins)
        if wins
        else None,
        "eig_per_question": sum(sum(g["question_eigs"]) for g in games) / len(turns)
        if turns
        else None,
        "invalid_questions": sum(t["invalid"] for t in turns),
        "repeated_splits": sum(t["reask"] for t in turns),
        "truncated_turns": sum(g["truncation_count"] for g in games),
        "no_guess_games": sum(
            not any(t["action"].startswith("GUESS: ") for t in g["turns"])
            for g in games
        ),
        "context_losses": sum(g.get("context_overflow", False) for g in games),
        "valid_yes_no_answers": sum(t["answer"] in ("YES", "NO") for t in turns),
        "flipped_answers": sum(t.get("flipped", False) for t in turns),
        "mean_reward": sum(g["reward"] for g in games) / len(games),
    }


def paired_difference(before, after, draws):
    def samples(cohort):
        win = np.array([g["won"] for g in cohort])
        q = np.array([g["questions"] for g in cohort])
        eig = np.array([sum(g["question_eigs"]) for g in cohort])
        qs = q[draws].sum(axis=1)
        mean_eig = np.divide(
            eig[draws].sum(axis=1), qs, out=np.full(len(draws), np.nan), where=qs > 0
        )
        return win[draws].mean(axis=1), mean_eig

    before_win, before_eig = samples(before)
    after_win, after_eig = samples(after)
    intervals = {}
    for name, change in (
        ("win_rate", after_win - before_win),
        ("eig_per_question", after_eig - before_eig),
    ):
        valid = change[np.isfinite(change)]
        intervals[name + "_ci95"] = (
            np.quantile(valid, [0.025, 0.975]).tolist() if len(valid) else None
        )

    pairs = list(zip(before, after, strict=True))
    won_before = sum(b["won"] and not a["won"] for b, a in pairs)
    won_after = sum(a["won"] and not b["won"] for b, a in pairs)
    both_win = [(b, a) for b, a in pairs if b["won"] and a["won"]]
    return {
        "delta_wins": won_after - won_before,
        "won_only_before": won_before,
        "won_only_after": won_after,
        "joint_wins": len(both_win),
        "delta_questions_on_joint_wins": sum(
            a["questions"] - b["questions"] for b, a in both_win
        ),
        **intervals,
    }


def replay_references(path, records):
    saved = defaultdict(list)
    ids = {r["id"] for r in records}
    for game in rows(path):
        if game["game_id"] in ids:
            saved[game["policy"]].append(game)
    for policy in REFERENCES:
        matches = joined(saved[policy], records)
        for record, original in zip(records, matches, strict=True):
            replay = play(record, policy, keep_trace=True)
            for key in ("won", "questions", "reward", "question_eigs", "invalid_count"):
                assert replay[key] == original[key], (record["id"], policy, key)
            original["turns"] = replay["turns"]
    return saved


def append_example(lines, record, game):
    policy = game["policy_label"]
    source = "main_A11" if policy == "Raw" else f"main_{policy}"
    result = "Win" if game["won"] else "Loss"
    lines += [
        f"## {LABELS[policy]} game",
        "",
        f"{result}. {game['questions']} counted questions. Return {game['reward']}.",
        f"[Source archive](../results/{source}/games.jsonl.gz).",
        "",
    ]
    if policy != "Raw":
        lines += ["[Opening prompt and table](#opening-prompt).", ""]
    turns = game["turns"]
    public = candidate_messages(record, turns)
    for i, turn in enumerate(turns):
        raw = turn["raw_action"]
        fence = "~~~"
        while fence in raw:
            fence += "~"
        answer = public[3 + 2 * i]["content"] if turn["is_question"] else turn["answer"]
        lines += [
            f"### Action {i + 1}",
            "",
            f"{fence}text",
            raw,
            fence,
            "",
            "Environment reply",
            "",
            "~~~text",
            answer,
            "~~~",
            "",
        ]
        if turn.get("flipped"):
            lines += [
                "The recorded answer was flipped. This annotation was private.",
                "",
            ]
    if game["context_overflow"]:
        lines += ["The game ended at the context limit.", ""]


def export_examples(primary, records):
    folder = ROOT / "examples"
    folder.mkdir(exist_ok=True)
    index = [
        "# Full game transcripts",
        "",
        "Four N=32 animal cases, each with the raw policy and all three trained policies. "
        "Within each noise level, take the lowest numeric case index where raw wins and all trained policies lose, "
        "then the lowest where raw loses and all trained policies win. The selection illustrates wins and losses for every policy.",
        "",
        "Each case includes the common opening prompt and every untrimmed decoded action and reply. "
        "The target, score, and flip annotations belong to the reader. The archives retain the original model text and token data.",
        "",
        "| Case | Noise | Raw | A11 | A23 | B41 |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    by_id = {p: {g["game_id"]: g for g in primary[p]} for p in POLICIES}
    for noise in (0, 0.1):
        for raw_won in (True, False):
            record = next(
                r
                for r in records
                if case_key(r) == ("animals", 32, noise)
                and by_id["Raw"][r["id"]]["won"] == raw_won
                and all(by_id[p][r["id"]]["won"] != raw_won for p in POLICIES[1:])
            )
            gid = record["id"]
            number = numeric_index(gid)
            name = f"animals-n32-case-{number}-{'noisy' if noise else 'truthful'}.md"
            frozen = f"animals_n32_p{noise:.2f}.jsonl.gz"
            lines = [
                f"# {gid}",
                "",
                f"Target `{record['world']['names'][record['target']]}`. "
                f"Answer flip probability {noise}. [Frozen cases](../evals/frozen/{frozen}).",
                "",
                "## Opening prompt",
                "",
            ]
            for msg in candidate_messages(record):
                lines += [
                    msg["role"].capitalize(),
                    "",
                    "~~~text",
                    msg["content"],
                    "~~~",
                    "",
                ]
            outcomes = []
            for p in POLICIES:
                game = by_id[p][gid]
                outcomes.append("Win" if game["won"] else "Loss")
                append_example(lines, record, {**game, "policy_label": p})
            (folder / name).write_text("\n".join(lines).rstrip("\n") + "\n")
            index.append(
                f"| [{gid}]({name}) | {noise} | " + " | ".join(outcomes) + " |"
            )
    (folder / "README.md").write_text("\n".join(index) + "\n")


def save_figure(fig, name):
    folder = ROOT / "figures"
    folder.mkdir(exist_ok=True)
    fig.savefig(folder / f"{name}.png", dpi=170)
    vector = folder / f"{name}.svg"
    fig.savefig(vector, metadata={"Date": None})
    vector.write_text(
        "\n".join(line.rstrip() for line in vector.read_text().splitlines()) + "\n"
    )
    plt.close(fig)


def plot(summary, animal32):
    plt.rcParams.update(
        {"svg.hashsalt": "twenty-bits-submission", "font.family": "DejaVu Sans"}
    )
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 5.1), layout="constrained")
    fig.suptitle(
        "Twenty Bits frozen evaluation",
        x=0.02,
        ha="left",
        fontsize=19,
        fontweight="bold",
    )
    panels = [
        (summary, "wins", 280, "Full primary bank", "Wins out of 280"),
        (animal32, "wins", 28, "Noiseless animals, N=32", "Wins out of 28"),
        (
            animal32,
            "eig_per_question",
            1,
            "Question quality, N=32",
            "Expected bits per counted question",
        ),
    ]
    for ax, (data, metric, right, title, label) in zip(axes, panels, strict=True):
        policies = [p for p in LABELS if p in data]
        values = [data[p][metric] for p in policies]
        ax.barh(
            range(len(policies)),
            values,
            color=[COLORS[p] for p in policies],
            height=0.65,
        )
        ax.set(
            yticks=range(len(policies)),
            yticklabels=[LABELS[p] for p in policies],
            xlim=(0, right),
            xlabel=label,
        )
        ax.invert_yaxis()
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", alpha=0.2)
        ax.set_axisbelow(True)
        if metric == "wins":
            for index, value in enumerate(values):
                inside = value > right * 0.87
                ax.text(
                    value + right * (-0.025 if inside else 0.02),
                    index,
                    str(value),
                    va="center",
                    ha="right" if inside else "left",
                    color="white" if inside else "#22303B",
                )
    save_figure(fig, "submission-baselines")


def plot_guess_timing(summary):
    seeds = POLICIES[1:]
    modes = [
        ("ambiguous_wrong_guess", "Ambiguous wrong guess", "#3D62A9", "A11"),
        ("no_guess", "No final guess", "#087A70", "A23"),
        (
            "ambiguous_guesses_with_budget",
            "Ambiguous guess with budget left",
            "#AD501F",
            "B41",
        ),
    ]
    fig, ax = plt.subplots(figsize=(7.4, 3.8), layout="constrained")
    fig.suptitle("When the trained policies guessed", fontsize=15, fontweight="bold")
    fig.supxlabel(
        "280 primary games per seed. The measures can count the same game.",
        fontsize=9,
    )
    y = np.arange(len(seeds))
    for i, (field, label, color, highlighted_seed) in enumerate(modes):
        values = [summary[seed][field] for seed in seeds]
        locations = y + (i - 1) * 0.22
        bars = ax.barh(locations, values, height=0.19, color=color, label=label)
        for seed, bar, location, value in zip(
            seeds, bars, locations, values, strict=True
        ):
            bar.set_alpha(1 if seed == highlighted_seed else 0.47)
            ax.text(
                value + 4,
                location,
                str(value),
                va="center",
                fontsize=9,
                fontweight="bold" if seed == highlighted_seed else "normal",
            )
    ax.set(yticks=y, yticklabels=seeds, xlim=(0, 280), xlabel="Games")
    ax.invert_yaxis()
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        ncols=3,
        frameon=False,
        fontsize=8,
    )
    save_figure(fig, "guess-timing")


def main():
    primary = primary_games()
    half_path = "results/submission/halving/games.jsonl.gz"
    halving = rows(half_path) if (ROOT / half_path).exists() else []
    sources = [f"results/main_{p}/games.jsonl.gz" for p in POLICIES[1:]]
    sources += ["results/writeup/numbers.json", "evals/frozen/manifest.json"]
    rng = np.random.default_rng(20261122)
    cells, all_records = [], []
    cohorts = defaultdict(list)
    with threadpool_limits(limits=1):
        for cell in frozen_manifest()["cells"]:
            key = case_key(cell)
            records = sorted(
                frozen_games(*key, count=28), key=lambda r: numeric_index(r["id"])
            )
            all_records.extend(records)
            groups = {
                p: joined([g for g in primary[p] if case_key(g) == key], records)
                for p in POLICIES
            }
            path = f"results/baselines/frozen/{cell['file']}"
            sources += [path, f"evals/frozen/{cell['file']}"]
            groups.update(replay_references(path, records))
            for p in REFERENCES:
                groups[p] = joined(groups[p], records)
            if key == ("animals", 32, 0) and halving:
                groups["Halving"] = joined(halving, records)
                sources.append(half_path)
            draws = rng.integers(0, len(records), (10000, len(records)))
            metrics = {p: totals(games) for p, games in groups.items()}
            for p, games in groups.items():
                cohorts[p].extend(games)
                gap = paired_difference(games, groups["greedy_predicate"], draws)
                gap["delta_eig_per_question"] = (
                    metrics["greedy_predicate"]["eig_per_question"]
                    - metrics[p]["eig_per_question"]
                )
                metrics[p]["greedy_predicate_minus_policy"] = gap
            if "Halving" in groups:
                gap = paired_difference(groups["Raw"], groups["Halving"], draws)
                gap["delta_eig_per_question"] = (
                    metrics["Halving"]["eig_per_question"]
                    - metrics["Raw"]["eig_per_question"]
                )
                metrics["Halving"]["halving_minus_raw"] = gap
            cells.append(
                {
                    "domain": key[0],
                    "n": key[1],
                    "noise": key[2],
                    "game_ids": [r["id"] for r in records],
                    "policies": metrics,
                }
            )
    all_records.sort(key=lambda r: (case_key(r), numeric_index(r["id"])))
    export_examples(primary, all_records)
    primary_summary = {p: totals(primary[p]) | endings(primary[p]) for p in POLICIES}
    for p in POLICIES:
        primary_summary[p]["ambiguous_guesses_with_budget"] = sum(
            flags(g)["ambiguous_with_budget_left"] for g in primary[p]
        )
    assert [primary_summary[p]["wins"] for p in POLICIES] == [141, 104, 138, 127]
    animal32 = next(
        c["policies"]
        for c in cells
        if (c["domain"], c["n"], c["noise"]) == ("animals", 32, 0)
    )
    noise = {
        str(p): {
            name: totals([g for g in games if g["noise"] == p])
            for name, games in cohorts.items()
            if name != "Halving"
        }
        for p in (0, 0.1)
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "comparison.json").write_text(
        json.dumps(
            {
                "title": "Matched primary evaluation and submission controls",
                "definitions": {
                    "bootstrap": "10,000 paired complete-game draws per cell, seed 20261122. Intervals condition on the fitted policies.",
                    "questions_per_win": "Counted questions on winning games divided by wins. A win at an ambiguous state may be lucky.",
                    "joint_wins": "The compared policies win these same cases. The saved question gap sums the per-case differences.",
                    "repeated_splits": "A legal question with the same truth mask as a previous question, or its complement.",
                    "flipped_answers": "Observed flips among valid sampled yes/no turns. Which turns are observed depends on the policy.",
                    "reward": "Mean of the saved game returns in that group. Noise comparisons are descriptive.",
                    "halving": "Format failure on noiseless animals N=32. The tested wording produced 262 invalid questions out of 280 and no final guesses. A working prompted-halving baseline remains untested.",
                },
                "primary_outcomes": primary_summary,
                "by_noise": noise,
                "cells": cells,
                "source_sha256": {
                    path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                    for path in sources
                },
            },
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    plot(primary_summary, animal32)
    plot_guess_timing(primary_summary)


if __name__ == "__main__":
    main()
