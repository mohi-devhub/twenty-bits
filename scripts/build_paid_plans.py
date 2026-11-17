"""Price candidate paid schedules from measured prompt tokens, with no API calls."""

from pathlib import Path
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from twenty_bits.worlds import ROOT, sample_game
from twenty_bits.prompts import prompt_ids, get_tokenizer


def main():
    measurement = json.loads((ROOT / "research/token_measurements.json").read_text())
    catalog = json.loads((ROOT / "research/tinker-models-2026-11-17.json").read_text())

    def rates(model):
        row = next(r for r in catalog if r["tinker_id"] == model)
        return {
            k: float(row[k][1:])
            for k in ["prefill", "cached_prefill", "sample", "train"]
        }

    def tokens(prefix, n, output=64):
        turns = 2 * math.ceil(math.log2(n)) + 1
        inputs = turns * prefix + (output + 32) * turns * (turns - 1) / 2
        return inputs, turns * output

    def cost(model, prefix, n, *, training=False, output=64):
        r = rates(model)
        i, o = tokens(prefix, n, output)
        return (
            i * r["prefill"]
            + o * r["sample"]
            + ((i + o) * r["train"] if training else 0)
        ) / 1e6

    evaluation = {}
    for model in ["Qwen/Qwen3-8B", "Qwen/Qwen3.5-4B", "openai/gpt-oss-120b"]:
        evaluation[model] = sum(
            cost(model, c["initial_prompt_tokens"]["max"], c["n"])
            for c in measurement["models"][model]["cells"]
        )
    train_counts = {}
    for model in ["Qwen/Qwen3-8B", "Qwen/Qwen3.5-4B"]:
        train_counts[model] = {}
        for n in [16, 32, 64, 128]:
            measured = [
                len(
                    prompt_ids(
                        sample_game(
                            "animals", n, i, namespace="train-plan-v1", noise=0
                        ),
                        model=model,
                    )
                )
                for i in range(40)
            ]
            train_counts[model][str(n)] = {
                "mean": float(np.mean(measured)),
                "max": max(measured),
                "examples": len(measured),
            }
    model = "Qwen/Qwen3-8B"

    def train_price(updates, sizes):
        return sum(
            4
            * updates
            / len(sizes)
            * cost(model, train_counts[model][str(n)]["max"], n, training=True)
            for n in sizes
        )

    plans = []
    for cap, gpc, a_seeds, b_seeds, updates, pilot_a, pilot_b in [
        (30, 24, 2, 1, 32, 24, 8),
        (50, 28, 3, 2, 32, 32, 16),
    ]:
        parts = {}
        parts["phase2_base_primary"] = gpc * evaluation[model]
        parts["phase2_alternative_4b_5_games_per_cell"] = (
            5 * evaluation["Qwen/Qwen3.5-4B"]
        )
        reference_cells = [
            c
            for c in measurement["models"]["openai/gpt-oss-120b"]["cells"]
            if c["n"] == 32
        ]
        parts["phase2_reference_20_games"] = sum(
            5
            * cost(
                "openai/gpt-oss-120b", c["initial_prompt_tokens"]["max"], 32, output=128
            )
            for c in reference_cells
        )
        parts["phase3_pilot_training"] = train_price(pilot_a + pilot_b, [16, 32])
        # Three animals N32 checks of eight development games, for each pilot.
        parts["phase3_pilot_dev_checks"] = (
            6 * 8 * cost(model, train_counts[model]["32"]["max"], 32)
        )
        parts["phase4_main_training"] = (a_seeds + b_seeds) * train_price(
            updates, [16, 32, 64, 128]
        )
        parts["phase4_final_evaluations"] = (
            (a_seeds + b_seeds) * gpc * evaluation[model]
        )
        total = sum(parts.values())
        if total * 1.5 > cap:
            raise RuntimeError(f"Plan {cap} does not fit: {total * 1.5}; parts={parts}")
        # Sampling uncertainty widths use worst-case Bernoulli SD=0.5.
        # For EIG, use baseline per-game means as an explicit proxy, not an LLM prediction.
        eig_widths = []
        q_widths = []
        recheck_rates = []
        import gzip

        for c in measurement["models"][model]["cells"]:
            path = (
                ROOT
                / f"results/baselines/{c['domain']}_n{c['n']}_p{c['noise']:.2f}.jsonl.gz"
            )
            rows = [
                json.loads(line)
                for line in gzip.decompress(path.read_bytes()).decode().splitlines()
            ]
            rows = [r for r in rows if r["policy"] == "greedy_predicate"]
            eig_widths.append(
                2
                * 1.96
                * np.std([r["eig_per_question"] for r in rows], ddof=1)
                / math.sqrt(gpc)
            )
            q = [r["questions"] for r in rows if r["won"]]
            if len(q) > 1:
                q_widths.append(
                    2 * 1.96 * np.std(q, ddof=1) / math.sqrt(gpc * len(q) / len(rows))
                )
            if c["noise"]:
                recheck_rates.append(
                    sum(r["low_probability_opportunities"] for r in rows) / len(rows)
                )
        plans.append(
            {
                "name": f"Plan {cap}",
                "cap_usd": cap,
                "main_model": model,
                "alternative_model": "Qwen/Qwen3.5-4B",
                "games_per_cell": gpc,
                "cells": 10,
                "evaluation_games_per_checkpoint": 10 * gpc,
                "seeds": {
                    "A": list([11, 23, 37][:a_seeds]),
                    "B": list([41, 53][:b_seeds]),
                },
                "main_updates_per_seed": updates,
                "groups_per_update": 1,
                "games_per_group": 4,
                "pilot_updates": {"A": pilot_a, "B": pilot_b},
                "evaluated_main_checkpoints": a_seeds + b_seeds,
                "kept_checkpoints_per_main_seed": 1,
                "base_eval_rounds": 1,
                "reference_games": 20,
                "alternative_4b_screen_games": 50,
                "output_cap_tokens": 2048,
                "thinking": "disabled for Qwen; reference has a 512-token cap including reasoning",
                "parts_usd": parts,
                "forecast_usd": total,
                "forecast_with_margin_usd": 1.5 * total,
                "headroom_after_margin_usd": cap - 1.5 * total,
                "precision": {
                    "win_rate_full_ci_width_per_cell_worst_case": 1.96 / math.sqrt(gpc),
                    "win_rate_full_ci_width_pooled_10_cells_worst_case": 1.96
                    / math.sqrt(5 * gpc),
                    "paired_win_difference_full_ci_width_per_cell_worst_case": 3.92
                    / math.sqrt(gpc),
                    "eig_full_ci_width_per_cell_baseline_proxy_range": [
                        min(eig_widths),
                        max(eig_widths),
                    ],
                    "questions_per_win_full_ci_width_baseline_proxy_range": [
                        min(q_widths),
                        max(q_widths),
                    ],
                    "noisy_recheck_opportunities_per_game_baseline_mean": float(
                        np.mean(recheck_rates)
                    ),
                    "recheck_full_ci_width_if_opportunities_match_baseline": min(
                        1, 1.96 / math.sqrt(5 * gpc * np.mean(recheck_rates))
                    ),
                    "seed_eig_full_ci_width_sensitivity_sd_0_02": {
                        str(s): 2
                        * ({1: float("nan"), 2: 12.706, 3: 4.303}[s])
                        * 0.02
                        / math.sqrt(s)
                        if s > 1
                        else None
                        for s in [a_seeds, b_seeds]
                    },
                },
            }
        )
    # How much room the universal cap leaves for a half-candidate name list.
    enum = {}
    for model in ["Qwen/Qwen3-8B", "Qwen/Qwen3.5-4B"]:
        tokenizer = get_tokenizer(model)
        values = []
        for domain, n in [
            ("animals", 32),
            ("animals", 128),
            ("synthetic", 32),
            ("synthetic", 128),
            ("synthetic", 256),
        ]:
            r = sample_game(domain, n, 0, namespace="paid-v1", noise=0)
            text = "ASK: " + " OR ".join(
                "item == " + name for name in r["world"]["names"][: n // 2]
            )
            values.append(
                {
                    "domain": domain,
                    "n": n,
                    "half_list_action_tokens": len(
                        tokenizer.encode(text, add_special_tokens=False)
                    ),
                }
            )
        enum[model] = values
    result = {
        "status": "proposals only; ledger cap remains $30 until approval",
        "forecast_method": "no cache credit; measured maximum initial prompt in each frozen cell; full question budget plus guess; 64 output tokens per turn plus 32 chat/answer tokens in later prompts; full per-turn contexts charged for training; margin 1.5",
        "uncertainty": "Output lengths and model success have not been measured. 2048 is a universal output cap, not the 64-token forecast. If actual usage consumes the held budget, stop before submitting more work; do not silently cut an approved evaluation.",
        "zero_shot_choice": "8B is cheaper on the published rate card. Task ability remains unknown without paid calls. Phase 2 screens 4B on 50 matched games before any training; switching models requires a reviewed plan at that gate.",
        "training_prompt_measurements": train_counts,
        "name_list_token_audit": enum,
        "plans": plans,
    }
    (ROOT / "research/paid_plans.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    for p in plans:
        print(
            p["name"], p["forecast_usd"], p["forecast_with_margin_usd"], p["parts_usd"]
        )


if __name__ == "__main__":
    main()
