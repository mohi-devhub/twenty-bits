"""Estimate random grammar-valid play on training rows, including grouped returns."""

import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.baselines import Baseline
from twenty_bits.game import Game
from twenty_bits.worlds import ROOT, seed_for, training_game


def main(states=500):
    cells = []
    for n in (4, 8, 16, 32, 64, 128):
        for noise in (0, 0.10):
            groups = []
            for index in range(states):
                record = training_game(n, 100000 + index, seed=20261119, noise=noise)
                returns, wins, questions, singleton_wins = [], [], [], []
                for member in range(8):
                    game = Game(record)
                    policy = Baseline(
                        game,
                        "random",
                        seed_for("random-learnability-v1", n, index, member),
                    )
                    while not game.done:
                        game.step(policy.act(game))
                    returns.append(game.reward)
                    wins.append(int(game.won))
                    questions.append(game.questions)
                    singleton_wins.append(
                        int(game.won and np.count_nonzero(game.posterior) == 1)
                    )
                groups.append(
                    {
                        "index": index,
                        "wins": wins,
                        "returns": returns,
                        "questions": questions,
                        "singleton_wins": singleton_wins,
                        "nonzero_return_variance": bool(np.ptp(returns) > 1e-12),
                        "mixed_wins": bool(0 < sum(wins) < 8),
                    }
                )
            group_rates = np.array([np.mean(g["wins"]) for g in groups])
            rng = np.random.default_rng(717)
            bootstrap = group_rates[rng.integers(0, states, (10000, states))].mean(
                axis=1
            )
            cell = {
                "n": n,
                "noise": noise,
                "states": states,
                "games_per_state": 8,
                "games": states * 8,
                "win_rate": float(group_rates.mean()),
                "win_ci95_clustered": np.quantile(bootstrap, [0.025, 0.975]).tolist(),
                "nonzero_return_variance_groups": float(
                    np.mean([g["nonzero_return_variance"] for g in groups])
                ),
                "mixed_win_groups": float(np.mean([g["mixed_wins"] for g in groups])),
                "singleton_wins": sum(sum(g["singleton_wins"]) for g in groups),
                "groups": groups,
            }
            cells.append(cell)
            print(
                json.dumps({k: v for k, v in cell.items() if k != "groups"}), flush=True
            )
    result = {
        "seed": 20261119,
        "namespace": "train-v1",
        "service_calls": 0,
        "policy": "Uniform single attributes with replacement; GUESS at singleton (p=0), confidence >= .95 (p=.10), or budget; stable MAP tie break. Same start and noise schedule within each group; independent policy RNGs. CIs resample start states.",
        "cells": cells,
    }
    path = ROOT / "results/diagnosis/random_valid.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    group_records = [
        {"n": cell["n"], "noise": cell["noise"], "groups": cell.pop("groups")}
        for cell in cells
    ]
    path.with_name("random_valid_groups.jsonl.gz").write_bytes(
        gzip.compress(
            "".join(
                json.dumps(row, separators=(",", ":")) + "\n" for row in group_records
            ).encode(),
            mtime=0,
        )
    )
    path.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--states", type=int, default=500)
    main(parser.parse_args().states)
