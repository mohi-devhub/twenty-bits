"""Price S/U main-run proposals from the completed pilot; no service calls."""

from collections import defaultdict
import gzip
import json
import math
from pathlib import Path
import sys

import numpy as np
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.baselines import play
from twenty_bits.budget import Ledger
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import rates, save_json
from twenty_bits.worlds import ROOT, training_game


def price_trace(record, kind, output_proxy, rendering, rate, cache_fraction):
    game = play(record, kind, keep_trace=True, tokenizer=rendering.tokenizer)
    inputs = outputs = 0
    extra_history = 0
    for i, turn in enumerate(game["turns"]):
        actual_out = (
            len(
                rendering.tokenizer.encode(turn["raw_action"], add_special_tokens=False)
            )
            + 1
        )
        generated = max(actual_out, output_proxy)
        length = (
            rendering.prompt(candidate_messages(record, game["turns"][:i])).length
            + extra_history
        )
        if length + 2048 > 32768:
            break
        inputs += length
        outputs += generated
        extra_history += max(0, generated - actual_out)
    return {
        "sampling_usd": inputs
        * (
            (1 - cache_fraction) * rate["prefill"]
            + cache_fraction * rate["cached_prefill"]
        )
        + outputs * rate["sample"],
        "sampling_uncached_usd": inputs * rate["prefill"] + outputs * rate["sample"],
        "gradient_usd": (inputs + outputs) * rate["train"],
        "input_tokens": inputs,
        "output_tokens": outputs,
        "calls": len(game["turns"]),
    }


def schedule(updates):
    # Small warm-up, two updates at each larger size, then emphasize N=16/32
    # where the pilot still needs learning before its untested larger sizes.
    counts = {n: 2 for n in (4, 8, 16, 32, 64, 128)}
    rotation = (16, 16, 32, 16, 32, 64, 128)
    for i in range(updates - 12):
        counts[rotation[i % len(rotation)]] += 1
    return counts


def main():
    out = ROOT / "results/pilot_A"
    summary = json.loads((out / "summary.json").read_text())
    config = json.loads((ROOT / "experiments/pilot_A.json").read_text())
    games = [json.loads(line) for line in gzip.open(out / "games.jsonl.gz", "rt")]
    rendering = Rendering(config["primary_model"], config)
    rate = {k: float(v) / 1e6 for k, v in rates(config["primary_model"]).items()}
    output_counts = defaultdict(list)
    for g in games:
        if g["kind"] == "train":
            output_counts[g["n"]].extend(
                t["usage"]["output_tokens"] for t in g["turns"]
            )
    proxies = {
        n: math.ceil(max(np.mean(xs), np.quantile(xs, 0.90)))
        for n, xs in output_counts.items()
    }
    largest = max(proxies)
    measured_dev_cache = [
        sum(
            g["prompt_cache_hit_tokens"]
            for g in games
            if g["kind"] == "dev" and g["update"] == step
        )
        / sum(
            g["prompt_tokens"]
            for g in games
            if g["kind"] == "dev" and g["update"] == step
        )
        for step in (4, 8, 12, 16)
    ]
    eval_cache = min(0.60, min(measured_dev_cache))
    training_profiles = {}
    with threadpool_limits(limits=1):
        for noise in (0, 0.10):
            for n in (4, 8, 16, 32, 64, 128):
                rows = []
                proxy = proxies[min(n, largest)]
                for i in range(8):
                    record = training_game(n, 900000 + i, seed=20261123, noise=noise)
                    for kind in ("random", "greedy_predicate"):
                        rows.append(
                            price_trace(record, kind, proxy, rendering, rate, 0)
                        )
                # Upper-quartile total of two free policy references, per size/noise.
                chosen = sorted(
                    rows, key=lambda r: r["sampling_usd"] + r["gradient_usd"]
                )[math.ceil(0.75 * (len(rows) - 1))]
                training_profiles[f"{n}/p{noise:g}"] = {
                    **chosen,
                    "measured_reference_games": len(rows),
                    "output_proxy": proxy,
                }
    observed = []
    for r in summary["updates"]:
        gs = [g for g in games if g["kind"] == "train" and g["update"] == r["update"]]
        uncached = (
            sum(
                (
                    t["usage"]["prompt_tokens"] * rate["prefill"]
                    + t["usage"]["output_tokens"] * rate["sample"]
                )
                for g in gs
                for t in g["turns"]
            )
            / 8
        )
        observed.append(
            {
                "n": r["n"],
                "sampling_usd": uncached,
                "gradient_usd": float(r["gradient_usd"]) / 8,
            }
        )
    ratios = []
    for n in proxies:
        actual = np.mean(
            [r["sampling_usd"] + r["gradient_usd"] for r in observed if r["n"] == n]
        )
        predicted = (
            training_profiles[f"{n}/p0"]["sampling_usd"]
            + training_profiles[f"{n}/p0"]["gradient_usd"]
        )
        ratios.append(float(actual / predicted))
    correction = max(1, max(ratios))
    eval_cells = []
    manifest = json.loads((ROOT / "evals/frozen/manifest.json").read_text())
    with threadpool_limits(limits=1):
        for cell in manifest["cells"]:
            records = [
                json.loads(line)
                for line in gzip.open(ROOT / "evals/frozen" / cell["file"], "rt")
            ][:28]
            rows = []
            for record in records:
                pair = [
                    price_trace(
                        record, kind, proxies[largest], rendering, rate, eval_cache
                    )
                    for kind in ("random", "greedy_predicate")
                ]
                rows.append(max(pair, key=lambda r: r["sampling_usd"]))
            cost = sum(r["sampling_usd"] for r in rows) * correction
            eval_cells.append(
                {
                    "domain": cell["domain"],
                    "n": cell["n"],
                    "noise": cell["noise"],
                    "games": 28,
                    "forecast_usd": cost,
                    "uncached_forecast_usd": sum(
                        r["sampling_uncached_usd"] for r in rows
                    )
                    * correction,
                }
            )
    endpoint_cost = sum(c["forecast_usd"] for c in eval_cells)
    endpoint_uncached = sum(c["uncached_forecast_usd"] for c in eval_cells)
    dev_cost = (
        sum(training_profiles[f"{n}/p0"]["sampling_usd"] * 4 for n in (4, 8))
        * correction
    )
    # Hard mode may still produce long invalid outputs. Price all 40 games at
    # the full 2048-token output cap until their context-limit stop, not with
    # the short candidate-list output proxy.
    from twenty_bits.learnability import probe_messages

    hard_cost = hard_uncached = 0
    for cell in manifest["cells"]:
        for line in list(gzip.open(ROOT / "evals/frozen" / cell["file"], "rt"))[:2]:
            record = json.loads(line)
            initial = rendering.prompt(probe_messages(record)).length
            inputs = outputs = 0
            for turn in range(2 * math.ceil(math.log2(record["n"])) + 1):
                length = initial + turn * (2048 + 64)
                if length + 2048 > 32768:
                    break
                inputs += length
                outputs += 2048
            hard_cost += 2 * (
                inputs
                * (
                    (1 - eval_cache) * rate["prefill"]
                    + eval_cache * rate["cached_prefill"]
                )
                + outputs * rate["sample"]
            )
            hard_uncached += 2 * (inputs * rate["prefill"] + outputs * rate["sample"])
    available = float(Ledger(ROOT / "ledger.json").status()["available_usd"])

    def option(name, a, b):
        seeds = a + b
        candidates = []
        for updates in range(12, 129):
            curriculum = schedule(updates)
            train = 0
            per_seed = {}
            for noise, count in ((0, len(a)), (0.10, len(b))):
                per_seed[noise] = sum(
                    u
                    * 8
                    * (
                        training_profiles[f"{n}/p{noise:g}"]["sampling_usd"]
                        + training_profiles[f"{n}/p{noise:g}"]["gradient_usd"]
                    )
                    * correction
                    for n, u in curriculum.items()
                )
                train += count * per_seed[noise]
            # Cheap fixed development checks every four updates make the curve
            # visible without retaining more endpoint checkpoints.
            checks = math.ceil(updates / 4)
            development = len(seeds) * checks * dev_cost
            endpoints = (1 + len(seeds)) * endpoint_cost
            storage = len(seeds) * 0.10
            total = train + development + endpoints + hard_cost + storage
            margin = total * 1.5
            zero_cache = (
                train
                + development
                + (1 + len(seeds)) * endpoint_uncached
                + hard_uncached
                + storage
            )
            if margin <= available - 0.10 and zero_cache <= available - 0.10:
                candidates.append(
                    {
                        "option": name,
                        "seeds_A": a,
                        "seeds_B": b,
                        "updates_per_seed": updates,
                        "curriculum": [
                            {"n": n, "updates": u, "games_per_seed": u * 8}
                            for n, u in curriculum.items()
                        ],
                        "training_games_per_seed": updates * 8,
                        "total_training_games": updates * 8 * len(seeds),
                        "training_usd": train,
                        "training_usd_per_A_seed": per_seed[0],
                        "training_usd_per_B_seed": per_seed[0.10],
                        "development_usd": development,
                        "development_checks": sorted(
                            set(range(4, updates + 1, 4)) | {updates}
                        ),
                        "development_games_per_check": 8,
                        "development_games_per_seed": checks * 8,
                        "full_evaluation_usd": endpoints,
                        "hard_mode_40_games_usd": hard_cost,
                        "checkpoint_holds_usd": storage,
                        "total_before_margin_usd": total,
                        "total_with_1_5_margin_usd": margin,
                        "zero_cache_total_without_extra_margin_usd": zero_cache,
                        "remaining_after_margin_usd": available - margin,
                        "endpoint_checkpoints_per_seed": 1,
                        "frozen_games_per_cell": 28,
                        "frozen_cells": 10,
                        "authorized": False,
                    }
                )
        return (
            candidates[-1]
            if candidates
            else {
                "option": name,
                "seeds_A": a,
                "seeds_B": b,
                "fits_minimum_12_updates": False,
                "authorized": False,
            }
        )

    options = {
        "S": option("S", [11, 23, 37], [41, 53]),
        "U": option("U", [11, 23], [41]),
    }
    result = {
        "authorized": False,
        "initialization": "raw_base_no_sft",
        "observation_mode": "candidate_set",
        "available_including_existing_holds_usd": available,
        "options": options,
        "recommendation": "U",
        "recommendation_reason": "The fixed small-game development EIG improved by update 8 then stayed around 0.62–0.65, still below one bit, with substantial ambiguous stopping. U buys more updates and more training start states, especially at N=16/32, while keeping two A seeds. It leaves only one B seed, so noisy-training effects have no between-seed uncertainty estimate. This is an exploratory recommendation; more updates are not guaranteed to improve the policy.",
        "training_profiles": training_profiles,
        "observed_pilot_uncached_cost_per_game": observed,
        "conservative_pilot_correction_factor": correction,
        "measured_output_tokens_per_call_proxy": proxies,
        "fixed_model_evaluation_280_games_usd": endpoint_cost,
        "eval_cells": eval_cells,
        "stable_weight_eval_cache_fraction": eval_cache,
        "cache_assumption": "Training sampling receives no cache credit. Stable-weight evaluation receives at most 60% cache-hit credit, below the minimum observed trained-snapshot development hit fraction (about 75%). Both the forecast times 1.5 and the separate zero-cache reference total must fit remaining funds with $0.10 additional headroom. Hard mode uses full-cap outputs rather than the short provided-state proxy. Large-N model behavior remains uncertain.",
        "observed_trained_snapshot_dev_cache_fractions": measured_dev_cache,
        "pricing_source": "https://tinker-docs.thinkingmachines.ai/tinker/models.json",
        "pricing_rechecked_date": "2026-11-18",
        "method": "Native candidate-feedback contexts on random and greedy-predicate reference trajectories. Upper-quartile reference cost for training; more expensive reference per frozen case for evaluation. Per-N output proxy is max(mean,p90) observed pilot output length. N>=16 and noisy behavior extrapolate from the largest measured pilot size. Scale upward if reference costs underpredict observed pilot uncached sampling plus gradients; never scale down.",
        "limits": "No noisy or large-N model pilot was run. Name-list enumeration could lengthen outputs substantially. These are forecasts, not bills or guarantees that all runs finish. Ledger holds enforce $50 regardless. All future settings and schedules must be frozen before paid work; no automatic extension if calls are cheaper.",
        "main_seed_initialization": "Fresh raw-base LoRA per seed, never resume the pilot. Training game indices and generation namespaces are disjoint from pilot/development/frozen cases.",
        "endpoint_policy": "Keep and evaluate the scheduled endpoint only for each seed, on all 280 frozen games. Main raw-base control is newly sampled once under candidate-set-v1. Intermediate development samplers are ephemeral, not retained checkpoints.",
        "development_policy": "The same eight N=4/8 development cases, every four updates plus the scheduled endpoint; reuse the saved raw development control. This descriptive curve does not measure large-N, noisy or transfer performance. Those comparisons use the frozen endpoints.",
        "hard_mode": "Raw base and the predetermined final A seed 11 endpoint, 20 games each, at the end. No hard-mode training.",
        "uncertainty": "S has three A and two B seeds; U has two A and one B seed, so U cannot estimate between-seed noise-training variation. Both require game and seed CIs with this limitation disclosed.",
    }
    save_json(ROOT / "research/main_options_after_pilot.json", result)
    print(
        json.dumps(
            {
                "options": options,
                "endpoint_usd": endpoint_cost,
                "pilot_correction": correction,
                "available_usd": available,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
