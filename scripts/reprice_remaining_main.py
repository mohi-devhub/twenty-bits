"""Price the two deferred seeds and hard mode from A11 observations offline."""

from collections import defaultdict
from decimal import Decimal
import gzip
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.tinker_transport import rates, save_json
from twenty_bits.worlds import ROOT


def main():
    folder = ROOT / "results/main_A11"
    summary = json.loads((folder / "summary.json").read_text())
    proposal = json.loads((ROOT / "research/main_options_after_pilot.json").read_text())
    option = proposal["options"]["U"]
    games = [json.loads(line) for line in gzip.open(folder / "games.jsonl.gz", "rt")]
    rate = {k: float(v) / 1e6 for k, v in rates("Qwen/Qwen3-8B").items()}

    def sample_price(gs, cache=0):
        return sum(
            g["prompt_tokens"]
            * ((1 - cache) * rate["prefill"] + cache * rate["cached_prefill"])
            + g["output_tokens"] * rate["sample"]
            for g in gs
        )

    by_size = defaultdict(list)
    for r in summary["updates"]:
        gs = [g for g in games if g["kind"] == "train" and g["update"] == r["update"]]
        by_size[r["n"]].append((sample_price(gs) + float(r["gradient_usd"])) / 8)
    profiles = {}
    for n, observed in by_size.items():
        reference = proposal["training_profiles"][f"{n}/p0"]
        floor = reference["sampling_usd"] + reference["gradient_usd"]
        value = max(floor, float(np.quantile(observed, 0.75)), float(np.mean(observed)))
        noisy = proposal["training_profiles"][f"{n}/p0.1"]
        ratio = (noisy["sampling_usd"] + noisy["gradient_usd"]) / floor
        profiles[str(n)] = {
            "A_uncached_sampling_plus_gradient_per_game_usd": value,
            "B_reference_multiplier": max(1, ratio),
            "observed_A_group_per_game_costs": observed,
            "reference_floor_usd": floor,
        }
    trainA = sum(
        r["games_per_seed"]
        * profiles[str(r["n"])]["A_uncached_sampling_plus_gradient_per_game_usd"]
        for r in option["curriculum"]
    )
    trainB = sum(
        r["games_per_seed"]
        * profiles[str(r["n"])]["A_uncached_sampling_plus_gradient_per_game_usd"]
        * profiles[str(r["n"])]["B_reference_multiplier"]
        for r in option["curriculum"]
    )
    cache = min(
        0.60,
        sum(g["prompt_cache_hit_tokens"] for g in games if g["kind"] == "eval_endpoint")
        / sum(g["prompt_tokens"] for g in games if g["kind"] == "eval_endpoint"),
    )
    eval_cost = eval_uncached = 0
    for cell in summary["frozen_evaluation"]["cells"]:
        cohorts = [
            [
                g
                for g in games
                if g["kind"] == kind
                and (g["domain"], g["n"], g["noise"])
                == (cell["domain"], cell["n"], cell["noise"])
            ]
            for kind in ("eval_base", "eval_endpoint")
        ]
        eval_cost += max(sample_price(gs, cache) for gs in cohorts)
        eval_uncached += max(sample_price(gs) for gs in cohorts)
    dev = max(
        sample_price([g for g in games if g["kind"] == "dev" and g["update"] == u])
        for u in option["development_checks"]
    )
    dev_total = dev * len(option["development_checks"]) * 2
    checkpoint = 0.20
    upload_buffer = 0.05
    hard = option["hard_mode_40_games_usd"]
    total = (
        trainA + trainB + dev_total + 2 * eval_cost + checkpoint + upload_buffer + hard
    )
    result = {
        "authorized_to_start_now": False,
        "gate": "User decision required after A11.",
        "remaining_seeds": {"A": [23], "B": [41]},
        "updates_per_seed": 30,
        "training_games_per_seed": 240,
        "training_A23_usd": trainA,
        "training_B41_usd": trainB,
        "development_usd": dev_total,
        "two_endpoint_evaluations_usd": 2 * eval_cost,
        "hard_mode_usd": hard,
        "checkpoint_holds_usd": checkpoint,
        "possible_adapter_reupload_hold_usd": upload_buffer,
        "total_before_margin_usd": total,
        "total_with_1_5_margin_usd": total * 1.5,
        "separate_zero_cache_reference_without_extra_margin_usd": trainA
        + trainB
        + dev_total
        + 2 * eval_uncached
        + checkpoint
        + upload_buffer
        + hard,
        "available_including_holds_usd": summary["cost"]["project"]["available_usd"],
        "fits_with_margin": Decimal(str(total * 1.5))
        <= Decimal(summary["cost"]["project"]["available_usd"]),
        "training_profiles": profiles,
        "stable_endpoint_cache_credit": cache,
        "method": "No training cache credit. Per-N measured mean/upper-quartile uncached sampling plus gradient cost, bounded below by original free-reference forecast. B scales by the original noisy/noiseless reference ratio. Endpoint uses the more expensive observed base/endpoint cell and at most 60% cache credit. No new raw frozen control is needed. Hard mode retains its full-output-cap forecast; a possible local adapter reupload has a separate hold allowance.",
        "limits": "One A seed measured; B training behavior remains unobserved. These are forecasts, not bills or guarantees. No schedule, reward or cap changes are automatic.",
    }
    save_json(ROOT / "research/main_A11_remaining_forecast.json", result)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "training_profiles"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
