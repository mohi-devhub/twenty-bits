"""Derive the final figures and disclosed examples from accepted saved games."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np

from twenty_bits.budget import Ledger
from twenty_bits.budget_followup_metrics import flags
from twenty_bits.worlds import ROOT

POLICIES = ("Raw", "A11", "A23", "B41")
OUTCOMES = ("win", "ambiguous_wrong_guess", "no_guess", "other")


def read_json(name):
    return json.loads((ROOT / name).read_text())


def saved_games(name, kinds):
    result = []
    for line in gzip.open(ROOT / name, "rt"):
        game = json.loads(line)
        if game["kind"] in kinds:
            game.pop("trajectory", None)
            result.append(game)
    return result


def outcome(game):
    if game["won"]:
        return "win"
    if game["guess_state"] is None:
        return "no_guess"
    if game["guess_state"]["k_remaining"] > 1:
        return "ambiguous_wrong_guess"
    return "other"


def endings(games):
    counts = Counter(outcome(game) for game in games)
    return {key: counts[key] for key in OUTCOMES}


def case_order(game):
    return (game["domain"], game["n"], int(game["game_id"].split("/")[-2]))


def public_trace(game):
    return {key: value for key, value in game.items() if key not in ("trajectory",)}


def select_examples(primary, visible, records):
    by_id = {name: {g["game_id"]: g for g in games} for name, games in primary.items()}
    budget = {g["game_id"]: g for g in visible if g["policy"] == "A23"}
    candidates = sorted(
        [g for g in primary["A11"] if g["domain"] == "animals" and g["noise"] == 0],
        key=case_order,
    )
    eligible = [
        g
        for g in candidates
        if outcome(g) == "ambiguous_wrong_guess"
        and flags(g)["ambiguous_with_budget_left"]
        and by_id["A23"][g["game_id"]]["guess_state"] is None
    ]
    if not eligible:
        raise ValueError(
            "No saved noiseless animal case meets the declared contrast rule."
        )
    chosen = eligible[0]["game_id"]
    comparisons = [
        {
            "id": "gamble-stall",
            "label": "Same target, different failures",
            "record": records[chosen],
            "players": [
                {
                    "label": name,
                    "trace": public_trace(by_id[name][chosen]),
                    "budget_visible_to_model": False,
                }
                for name in ("Raw", "A11", "A23")
            ],
            "selection": "Animals, p=0. Sort N ascending, then frozen index numerically ascending. Take the earliest case where A11 makes an ambiguous wrong guess with questions left and A23 never guesses. The raw control uses that same case, without an outcome filter.",
            "eligible_cases": len(eligible),
        }
    ]
    candidates = sorted(
        [g for g in primary["A23"] if g["domain"] == "animals" and g["noise"] == 0.1],
        key=case_order,
    )
    eligible = [
        g
        for g in candidates
        if g["guess_state"] is None and budget[g["game_id"]]["won"]
    ]
    if not eligible:
        raise ValueError(
            "No saved noisy animal case meets the declared budget contrast rule."
        )
    chosen = eligible[0]["game_id"]
    comparisons.append(
        {
            "id": "budget-fix",
            "label": "Same weights, visible budget",
            "record": records[chosen],
            "players": [
                {
                    "label": "A23 primary",
                    "trace": public_trace(by_id["A23"][chosen]),
                    "budget_visible_to_model": False,
                },
                {
                    "label": "A23 visible budget",
                    "trace": public_trace(budget[chosen]),
                    "budget_visible_to_model": True,
                },
            ],
            "selection": "Animals, p=0.10. Sort N ascending, then frozen index numerically ascending. Take the earliest case where A23 primary never guesses and its visible-budget rollout wins. Do not filter question text, target, EIG or game length.",
            "eligible_cases": len(eligible),
        }
    )
    return comparisons


def main():
    sources = [
        "ledger.json",
        "results/main_B41/all_seeds.json",
        "results/main_A23/replication_summary.json",
        "results/A23_suffix/session_variation.json",
        "results/visible_budget/summary.json",
        "experiments/main_B41_games.json.gz",
        "results/phase2/matched_baselines.json",
        "PROTOCOL.md",
        "NUMBERS.md",
    ]
    primary, development, summaries = {}, {}, {}
    for name in ("A11", "A23", "B41"):
        path = f"results/main_{name}/games.jsonl.gz"
        sources.extend(
            [path, f"results/main_{name}/summary.json", f"experiments/main_{name}.json"]
        )
        games = saved_games(path, {"eval_endpoint", "eval_base", "dev"})
        primary[name] = [g for g in games if g["kind"] == "eval_endpoint"]
        development[name] = [g for g in games if g["kind"] == "dev"]
        summaries[name] = read_json(f"results/main_{name}/summary.json")
        if name == "A11":
            primary["Raw"] = [g for g in games if g["kind"] == "eval_base"]
    sources.append("results/visible_budget/games.jsonl.gz")
    visible = saved_games("results/visible_budget/games.jsonl.gz", {"visible_budget"})
    all_seeds = read_json("results/main_B41/all_seeds.json")
    rng = np.random.default_rng(20261119)
    animal_draws = {n: rng.integers(28, size=(10000, 28)) for n in (32, 128)}
    animal = {}
    boot = {}
    for name in POLICIES:
        cells, draws = [], []
        for n in (32, 128):
            games = sorted(
                [
                    g
                    for g in primary[name]
                    if g["domain"] == "animals" and g["n"] == n and g["noise"] == 0
                ],
                key=lambda g: g["game_id"],
            )
            q = np.array([g["questions"] for g in games])
            eig = np.array([sum(g["question_eigs"]) for g in games])
            ix = animal_draws[n]
            cells.append(float(eig.sum() / q.sum()))
            draws.append(eig[ix].sum(axis=1) / q[ix].sum(axis=1))
        boot[name] = np.mean(draws, axis=0)
        selected = [
            g for g in primary[name] if g["domain"] == "animals" and g["noise"] == 0
        ]
        animal[name] = {
            "eig_per_question": float(np.mean(cells)),
            "ci95": np.quantile(boot[name], [0.025, 0.975]).tolist(),
            "games": len(selected),
            "wins": sum(g["won"] for g in selected),
            "outcomes": endings(selected),
        }
        if name != "Raw":
            declared = summaries[name]["frozen_evaluation"]["declared_subsets"][
                "noiseless_animals"
            ]["eig_per_question"]
            assert abs(animal[name]["eig_per_question"] - declared["endpoint"]) < 1e-12
            animal[name]["paired_change_from_raw"] = declared
    cohorts = {
        "primary": primary,
        "visible_budget": {
            name: [g for g in visible if g["policy"] == name]
            for name in ("Raw", "A23", "B41")
        },
    }
    outcomes = {}
    for stage, policies in cohorts.items():
        outcomes[stage] = {}
        for name, games in policies.items():
            outcomes[stage][name] = {
                "games": len(games),
                "outcomes": endings(games),
                "ambiguous_with_budget_left": sum(
                    flags(g)["ambiguous_with_budget_left"] for g in games
                ),
                "extra_ask_final": sum(flags(g)["extra_ask_final"] for g in games),
                "context_losses": sum(g["context_overflow"] for g in games),
                "enumeration_questions": sum(g["enumeration_count"] for g in games),
            }
    noisy = {}
    for name in POLICIES:
        selected = sorted(
            [g for g in primary[name] if g["noise"] == 0.1], key=lambda g: g["game_id"]
        )
        # Stratify by the five domain/size cells. Complete games stay paired.
        cell_groups = [
            [g for g in selected if (g["domain"], g["n"]) == (d, n)]
            for d, n in sorted({(g["domain"], g["n"]) for g in selected})
        ]
        draws = [
            np.array([g["won"] for g in gs], dtype=float)[
                animal_draws[n]
                if d == "animals"
                else np.random.default_rng(20261119 + n).integers(28, size=(10000, 28))
            ].mean(axis=1)
            for (d, n), gs in zip(
                sorted({(g["domain"], g["n"]) for g in selected}), cell_groups
            )
        ]
        noisy[name] = {
            "games": len(selected),
            "wins": sum(g["won"] for g in selected),
            "win_rate": sum(g["won"] for g in selected) / len(selected),
            "ci95": np.quantile(np.mean(draws, axis=0), [0.025, 0.975]).tolist(),
            "reasks": sum(g["reasks_after_low_probability"] for g in selected),
            "reask_opportunities": sum(
                g["low_probability_opportunities"] for g in selected
            ),
        }
    records = json.loads(
        gzip.decompress((ROOT / "experiments/main_B41_games.json.gz").read_bytes())
    )["evaluation"]
    records = {r["id"]: r for r in records}
    examples = select_examples(primary, visible, records)
    frozen = read_json("results/visible_budget/summary.json")
    replication = read_json("results/main_A23/replication_summary.json")
    variation = read_json("results/A23_suffix/session_variation.json")
    result = {
        "analysis_only": True,
        "service_calls": 0,
        "bootstrap": {
            "draws": 10000,
            "seed": 20261119,
            "unit": "complete paired game, stratified by cell",
            "animal_headline": "Equal weight on N=32 and N=128 noiseless cell EIG ratios. Intervals condition on each scheduled endpoint; no B seed uncertainty can be estimated.",
        },
        "animal_noiseless": animal,
        "primary_cells": all_seeds["cells"],
        "outcomes": outcomes,
        "noisy": noisy,
        "hierarchical_A_seed_comparison": read_json(
            "results/main_A23/replication_summary.json"
        )["hierarchical_seed_and_game_bootstrap"],
        "B41_vs_mean_A": all_seeds["B41_vs_mean_A"],
        "visible_budget": frozen["pooled"],
        "visible_budget_cells": frozen["cells"],
        "development": {name: s["development"] for name, s in summaries.items()},
        "training_updates": {name: s["updates"] for name, s in summaries.items()},
        "side_findings": {
            "sampler_trainer_logprob": {
                name: s["sample_train_logprob_diagnostic"]
                for name, s in summaries.items()
            },
            "A23_invalid_name_attempts": replication[
                "post_hoc_raw_candidate_name_audits"
            ]["23"]["train"]["counts"],
            "A23_update23": next(
                r for r in summaries["A23"]["updates"] if r["update"] == 23
            ),
            "same_seed_session_variation": {
                "games": variation["paired_synthetic_games"],
                "identical_complete_action_pairs": variation[
                    "identical_complete_action_pairs"
                ],
                "divergent_before_mapping": len(
                    variation["initial_action_divergence_before_mapping"]
                ),
                "supplied_parameter_mismatches": variation[
                    "supplied_parameter_mismatches"
                ],
            },
            "A11_checkpoint": replication["A11_suffix_status"],
        },
        "examples": [
            {
                "id": e["id"],
                "game_id": e["record"]["id"],
                "target": e["record"]["world"]["names"][e["record"]["target"]],
                "selection": e["selection"],
                "eligible_cases": e["eligible_cases"],
                "policies": [
                    {
                        "label": p["label"],
                        "outcome": outcome(p["trace"]),
                        "questions": p["trace"]["questions"],
                        "guess_state": p["trace"]["guess_state"],
                    }
                    for p in e["players"]
                ],
            }
            for e in examples
        ],
        "ledger": {
            k: v
            for k, v in Ledger.snapshot_status(ROOT / "ledger.json").items()
            if k in ("spent_usd", "held_usd", "available_usd", "cap_usd")
        },
        "source_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in sorted(sources)
        },
    }
    folder = ROOT / "results/writeup"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "numbers.json").write_text(json.dumps(result, indent=2) + "\n")
    replay_folder = ROOT / "replays/study"
    replay_folder.mkdir(parents=True, exist_ok=True)
    (replay_folder / "games.json").write_text(json.dumps(examples, indent=2) + "\n")
    (replay_folder / "games.js").write_text(
        "window.REPLAYS = " + json.dumps(examples, separators=(",", ":")) + ";\n"
    )
    print(
        json.dumps(
            {
                "animal": animal,
                "examples": result["examples"],
                "ledger": result["ledger"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
