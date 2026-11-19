"""Compare the common frozen cells without choosing a seed or repairing actions."""

import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from scripts.analyze_main_evaluation import paired_cell, wilson
from twenty_bits.name_reference_audit import audit_name_references
from twenty_bits.worlds import ROOT


def read_games(folder):
    return [
        json.loads(line)
        for line in gzip.open(ROOT / f"results/{folder}/games.jsonl.gz", "rt")
    ]


def vectors(games):
    return {
        "wins": np.array([g["won"] for g in games], dtype=float),
        "questions": np.array([g["questions"] for g in games], dtype=float),
        "eig": np.array([sum(g["question_eigs"]) for g in games]),
        "ambiguous_guess_rate": np.array(
            [
                bool(g["guess_state"] and g["guess_state"]["k_remaining"] > 1)
                for g in games
            ],
            dtype=float,
        ),
        "no_guess_rate": np.array(
            [g["guess_state"] is None for g in games], dtype=float
        ),
        "early_guess_win_rate": np.array(
            [g["early_guess"] and g["won"] for g in games], dtype=float
        ),
        "reasks": np.array(
            [g["reasks_after_low_probability"] for g in games], dtype=float
        ),
        "opportunities": np.array(
            [g["low_probability_opportunities"] for g in games], dtype=float
        ),
    }


def statistics(games, indices):
    v = vectors(games)

    def ratio(numerator, denominator):
        a = numerator[indices].sum(axis=-1)
        b = denominator[indices].sum(axis=-1)
        return np.divide(a, b, out=np.full(np.shape(b), np.nan), where=b > 0)

    return {
        "win_rate": v["wins"][indices].mean(axis=-1),
        "eig_per_question": ratio(v["eig"], v["questions"]),
        "questions_per_win": ratio(v["questions"] * v["wins"], v["wins"]),
        "recheck_rate": ratio(v["reasks"], v["opportunities"]),
        **{
            k: v[k][indices].mean(axis=-1)
            for k in ["ambiguous_guess_rate", "no_guess_rate", "early_guess_win_rate"]
        },
    }


def finite_interval(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    return {
        "ci95": np.quantile(values, [0.025, 0.975]).tolist() if len(values) else None,
        "defined_draws": len(values),
    }


def b_vs_a(policies, cells, draws=10000):
    rng = np.random.default_rng(20261120)
    seed_draw = rng.integers(2, size=(2, draws))
    indices = {}
    delta_draws = []
    delta_points = []
    for cell in cells:
        pairs = {
            name: sorted(
                [g for g in games if (g["domain"], g["n"], g["noise"]) == cell],
                key=lambda g: g["game_id"],
            )
            for name, games in policies.items()
            if name != "Raw"
        }
        assert all(len(gs) == 28 for gs in pairs.values())
        assert all(
            [g["game_id"] for g in gs] == [g["game_id"] for g in pairs["B41"]]
            for gs in pairs.values()
        )
        ix = indices.setdefault(cell[:2], rng.integers(28, size=(draws, 28)))
        boot = {name: statistics(gs, ix) for name, gs in pairs.items()}
        point = {name: statistics(gs, np.arange(28)) for name, gs in pairs.items()}
        ds = {}
        ps = {}
        for key in boot["B41"]:
            a = np.stack([boot["A11"][key], boot["A23"][key]])
            ds[key] = boot["B41"][key] - a[seed_draw, np.arange(draws)].mean(axis=0)
            ps[key] = point["B41"][key] - (point["A11"][key] + point["A23"][key]) / 2
        delta_draws.append(ds)
        delta_points.append(ps)
    selected = {
        "all_cells": list(range(len(cells))),
        "noisy_all_domains": [i for i, c in enumerate(cells) if c[2] == 0.1],
        "noisy_animals": [
            i for i, c in enumerate(cells) if c[2] == 0.1 and c[0] == "animals"
        ],
        "noisy_synthetic": [
            i for i, c in enumerate(cells) if c[2] == 0.1 and c[0] == "synthetic"
        ],
        "noiseless_animals": [
            i for i, c in enumerate(cells) if c[2] == 0 and c[0] == "animals"
        ],
        "noiseless_synthetic": [
            i for i, c in enumerate(cells) if c[2] == 0 and c[0] == "synthetic"
        ],
    }
    result = {}
    for label, indices in selected.items():
        result[label] = {}
        for key in delta_draws[0]:
            point = float(np.mean([delta_points[i][key] for i in indices]))
            result[label][key] = {
                "B41_minus_mean_A": point if np.isfinite(point) else None,
                **finite_interval(
                    np.mean([delta_draws[i][key] for i in indices], axis=0)
                ),
            }
    return {
        "subsets": result,
        "draws": draws,
        "A_seeds": [11, 23],
        "B_seeds": [41],
        "method": "Resample the two A seeds then paired complete games within each cell; share case draws between noise variants. The single B endpoint is fixed, with no estimate of B training-seed variability. Equal weight per cell and A seed. Undefined recheck ratios remain undefined, not zero.",
    }


def main():
    from scripts.analyze_A23_replication import identifier_forms
    from scripts.run_main_B41 import metrics

    records = json.loads(
        gzip.decompress((ROOT / "experiments/main_B41_games.json.gz").read_bytes())
    )
    by_id = {r["id"]: r for r in records["evaluation"]}
    noise_pairs = {}
    for record in records["evaluation"]:
        noise_pairs.setdefault(record["id"].rsplit("/", 1)[0], []).append(record)
    assert len(noise_pairs) == 140
    assert all(
        len(pair) == 2
        and pair[0]["world"] == pair[1]["world"]
        and pair[0]["target"] == pair[1]["target"]
        for pair in noise_pairs.values()
    )
    raw_archive = read_games("main_A11")
    policies = {"Raw": [g for g in raw_archive if g["kind"] == "eval_base"]}
    all_games = {
        "A11": raw_archive,
        "A23": read_games("main_A23"),
        "B41": read_games("main_B41"),
    }
    policies.update(
        {
            name: [g for g in games if g["kind"] == "eval_endpoint"]
            for name, games in all_games.items()
        }
    )
    assert all(
        {g["game_id"] for g in games} == set(by_id) for games in policies.values()
    )
    cells = sorted({(r["domain"], r["n"], r["noise"]) for r in records["evaluation"]})
    rows = []
    for cell in cells:
        pair = {
            name: sorted(
                [g for g in games if (g["domain"], g["n"], g["noise"]) == cell],
                key=lambda g: g["game_id"],
            )
            for name, games in policies.items()
        }
        for name, games in pair.items():
            point = metrics(games)
            g = point["guess_with_k_remaining"]
            ix = np.random.default_rng(20261121).integers(28, size=(10000, 28))
            ci = {
                key: finite_interval(values)
                for key, values in statistics(games, ix).items()
            }
            rows.append(
                {
                    "domain": cell[0],
                    "n": cell[1],
                    "noise": cell[2],
                    "policy": name,
                    "games": len(games),
                    "wins": point["wins"],
                    "win_rate": point["win_rate"],
                    "eig_per_question": point["eig_per_question"],
                    "questions_per_win": point["questions_per_win"],
                    "ambiguous_guesses": g["ambiguous_guesses"],
                    "ambiguous_guess_rate": g["ambiguous_guesses"] / len(games),
                    "ambiguous_guess_wins": g["ambiguous_guess_wins"],
                    "no_guess_games": g["no_guess_games"],
                    "no_guess_rate": g["no_guess_games"] / len(games),
                    "early_guesses": sum(x["early_guess"] for x in games),
                    "early_guess_wins": sum(
                        x["early_guess"] and x["won"] for x in games
                    ),
                    "low_probability_reasks": sum(
                        x["reasks_after_low_probability"] for x in games
                    ),
                    "low_probability_opportunities": sum(
                        x["low_probability_opportunities"] for x in games
                    ),
                    "guess_with_k_remaining": g,
                    "ci95": ci,
                    "win_wilson_ci95": wilson(point["wins"], len(games)),
                    "B41_minus_this_policy": paired_cell(games, pair["B41"])[0]
                    if name != "B41"
                    else None,
                }
            )
    endings = {}
    for name, games in policies.items():
        endings[name] = {
            "games": len(games),
            "wins": sum(g["won"] for g in games),
            "wrong_guesses": sum(
                g["guess_state"] is not None and not g["won"] for g in games
            ),
            "no_guess_games": sum(g["guess_state"] is None for g in games),
            "ambiguous_wrong_guesses": sum(
                bool(
                    g["guess_state"]
                    and g["guess_state"]["k_remaining"] > 1
                    and not g["won"]
                )
                for g in games
            ),
            "early_guesses": sum(g["early_guess"] for g in games),
            "early_guess_wins": sum(g["early_guess"] and g["won"] for g in games),
        }
    training_records = {
        row["record"]["id"]: row["record"] for row in records["training"]
    }
    training = [g for g in all_games["B41"] if g["kind"] == "train"]
    result = {
        "cells": rows,
        "B41_vs_mean_A": b_vs_a(policies, cells),
        "endings": endings,
        "B41_synthetic_identifier_forms": identifier_forms(policies["B41"], by_id),
        "B41_invalid_name_reference_audit": {
            "training": audit_name_references(training, training_records),
            "endpoint": audit_name_references(policies["B41"], by_id),
        },
        "definitions": {
            "ambiguous_guess_rate": "Games with a GUESS at displayed k>1, divided by all 28 games; exact positive support at p=0, threshold-plus-MAP display at p=.1.",
            "no_guess_rate": "Games without GUESS divided by all 28 games.",
            "early_guess_wins": "Correct guesses using fewer than ceil(log2(N)) questions; counts, with early-guess attempts also reported.",
            "EIG": "Sum of exact question EIG divided by counted questions, including losses and INVALID.",
            "uncertainty": "Whole-game paired intervals condition on endpoints. The A mean comparison resamples two A seeds; no B training-seed variance is estimable.",
        },
    }
    out = ROOT / "results/main_B41/all_seeds.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "endings": endings,
                "cells": len(rows),
                "B41_vs_mean_A": result["B41_vs_mean_A"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
