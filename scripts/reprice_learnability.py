"""Forecast possible follow-up work from measured probe tokens. No service calls."""

import gzip
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.learnability import probe_messages
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import rates
from twenty_bits.worlds import ROOT, training_game


def main():
    summary = json.loads((ROOT / "results/learnability_probe/summary.json").read_text())
    config = json.loads((ROOT / "experiments/learnability_probe.json").read_text())
    rendering = Rendering(config["primary_model"], config)
    r = {k: float(v) / 1e6 for k, v in rates(config["primary_model"]).items()}
    output_proxies = {
        c["n"]: c["mean_output_tokens_per_call"] for c in summary["cells"]
    }
    prefixes = {}
    for n in (4, 8, 16, 32, 64, 128):
        lengths = [
            rendering.prompt(
                probe_messages(training_game(n, 500000 + i, seed=20261120, noise=0))
            ).length
            for i in range(40)
        ]
        prefixes[n] = {
            "mean": float(np.mean(lengths)),
            "max": max(lengths),
            "measured_games": 40,
        }

    def price(n, prefix, *, cap=False):
        output = 2048 if cap else output_proxies[8 if n <= 8 else 16]
        inputs = outputs = calls = 0
        for turn in range(2 * math.ceil(math.log2(n)) + 1):
            prompt = prefix + (output + 32) * turn
            if prompt + 2048 > 32768:
                break
            inputs += prompt
            outputs += output
            calls += 1
        sampling = inputs * r["prefill"] + outputs * r["sample"]
        training = (inputs + outputs) * r["train"]
        return {
            "sampling_usd": sampling,
            "training_usd": training,
            "combined_usd": sampling + training,
            "input_tokens": inputs,
            "output_tokens": outputs,
            "calls": calls,
            "output_tokens_per_call_proxy": output,
        }

    training_prices = [
        {
            "n": n,
            "prefix": prefixes[n],
            "probe_token_proxy": price(n, prefixes[n]["max"]),
            "full_output_cap_stress": price(n, prefixes[n]["max"], cap=True),
        }
        for n in prefixes
    ]
    warm = json.loads((ROOT / "research/format_warmstart_price.json").read_text())
    pilot = {}
    schedule = {4: 4, 8: 8, 16: 4}
    for cap, name in [
        (False, "measured_token_proxy"),
        (True, "full_output_cap_stress"),
    ]:
        train = sum(
            updates * 8 * price(n, prefixes[n]["max"], cap=cap)["combined_usd"]
            for n, updates in schedule.items()
        )
        dev_per_check = sum(
            16 * price(n, prefixes[n]["max"], cap=cap)["sampling_usd"] for n in (4, 8)
        )
        pilot_storage = 0.10
        sft = float(warm["forward_backward_usd"]) + float(warm["storage_allowance_usd"])
        total = train + 5 * dev_per_check + pilot_storage
        abort = (
            4 * 8 * price(4, prefixes[4]["max"], cap=cap)["combined_usd"]
            + 2 * dev_per_check
            + pilot_storage
            + sft
        )
        pilot[name] = {
            "training_games": 128,
            "updates": 16,
            "schedule": [{"n": n, "updates": u} for n, u in schedule.items()],
            "training_sampling_and_gradient_usd": train,
            "development_checks": [0, 4, 8, 12, 16],
            "development_games_per_check": 32,
            "development_sampling_usd": 5 * dev_per_check,
            "storage_allowance_usd": pilot_storage,
            "without_sft_with_margin_usd": total * 1.5,
            "with_sft_with_margin_usd": (total + sft) * 1.5,
            "abort_after_four_updates_with_sft_and_margin_usd": abort * 1.5,
            "sft_qualification_only_with_margin_usd": (sft + dev_per_check) * 1.5,
        }

    eval_cells = []
    for cell in frozen_manifest()["cells"]:
        # Read frozen cases only for pricing. No transcript becomes a training example.
        lengths = [
            rendering.prompt(probe_messages(record)).length
            for record in frozen_games(cell["domain"], cell["n"], cell["noise"], 28)
        ]
        eval_cells.append(
            {
                "domain": cell["domain"],
                "n": cell["n"],
                "noise": cell["noise"],
                "games": 28,
                "initial_prompt_max": max(lengths),
                "initial_prompt_mean": float(np.mean(lengths)),
                "forecast_usd": 28 * price(cell["n"], max(lengths))["sampling_usd"],
                "full_cap_stress_usd": 28
                * price(cell["n"], max(lengths), cap=True)["sampling_usd"],
            }
        )
    eval_cost = sum(c["forecast_usd"] for c in eval_cells)
    eval_stress = sum(c["full_cap_stress_usd"] for c in eval_cells)
    remaining = float(summary["cost"]["project"]["available_usd"])
    forecasts = {
        "authorized": False,
        "service_calls": 0,
        "observed_probe_complete": summary["complete"],
        "observed_probe_games": summary["games"],
        "observed_cost_per_game_usd": {
            str(c["n"]): c["cost_per_complete_game_usd"] for c in summary["cells"]
        },
        "method": "Measured generated tokens/call from each probe size. N=4 uses the N=8 output proxy; larger sizes use N=16, an untested extrapolation. Measure 40 native training prefixes/size and all 280 frozen prefixes under the proposed prompt. Charge full question budget plus guess and full per-turn training contexts, including masked prompt tokens. No cache credit. Stress scenario uses 2048 generated tokens each turn until context loss. A changed policy can have different token usage; per-call holds still enforce the cap.",
        "storage_assumptions": "Use ephemeral fixed-weight sampler copies between updates. At most five named pilot snapshots and one SFT snapshot, each bounded at 64 GB with a two-hour TTL. At $0.10/GB/month using a 30-day month, those cost at most $0.088889 and $0.017778, below the separate $0.10 allowances. Download retained artifacts before expiry. Recheck size and reserve the storage maximum before each save; no optimizer-state checkpoint is included.",
        "training_prices": training_prices,
        "pilot": pilot,
        "pilot_stop_rule": {
            "groups_per_update": 1,
            "games_per_group": 8,
            "evaluate_after_updates": 4,
            "halt_if_fraction_nonzero_total_return_variance_below": 0.25,
            "equivalent_at_four_groups": "Halt if zero of the four groups has return variance greater than 1e-12. One of four equals 25% and passes this rule.",
            "recommended_additional_check": "Require at least one training win in those 32 games. Otherwise cost-only reward variation can pass the requested test. Freeze this extra condition only if approved.",
            "sft_qualification_proposal": "Before RL, at least 90% valid turns and 8/32 development wins. If this fails, stop after warm start and development sampling.",
        },
        "full_eval_280_games_usd": eval_cost,
        "full_eval_280_games_with_margin_usd": eval_cost * 1.5,
        "full_eval_280_full_cap_stress_with_margin_usd": eval_stress * 1.5,
        "eval_cells": eval_cells,
        "matched_control_requirement": "All RL comparisons require a pre-RL control under the same prompt on the same frozen games. Without SFT that is the newly prompted raw base. With SFT it is the warm-start checkpoint. A full raw-base versus warm-start ablation is optional and separately priced. Keep Phase 2 frozen files and hashes; add an approved prompt-version hash set. Historical Phase 2 cannot isolate RL under a changed prompt.",
        "available_project_usd": remaining,
        "after_warm_pilot_margin_usd": remaining
        - pilot["measured_token_proxy"]["with_sft_with_margin_usd"],
        "planning_example_with_one_control_and_three_main_endpoints_with_margin_usd": pilot[
            "measured_token_proxy"
        ]["with_sft_with_margin_usd"]
        + 4 * eval_cost * 1.5,
        "example_is_not_a_main_run_authorization": True,
    }
    records = {
        r["id"]: r
        for r in json.loads(
            (ROOT / "experiments/learnability_probe_games.json").read_text()
        )
    }
    extra = {}
    for line in gzip.open(ROOT / "results/learnability_probe/games.jsonl.gz", "rt"):
        game = json.loads(line)
        record = records[game["game_id"]]
        difference = 0
        for index in range(len(game["turns"])):
            public = probe_messages(record, game["turns"][:index])
            original = rendering.prompt(public).length
            for j, past in enumerate(game["turns"][:index]):
                remaining_names = [
                    name
                    for name, mass in zip(
                        record["world"]["names"], past["posterior_after"]
                    )
                    if mass > 0
                ]
                public[3 + 2 * j]["content"] += "\nRemaining candidates: " + ",".join(
                    remaining_names
                )
            difference += rendering.prompt(public).length - original
        extra.setdefault(game["n"], []).append(difference)
    forecasts["remaining_list_option"] = {
        "authorized": False,
        "definition": "After every answer, reveal noiseless posterior support as a name list. This supplies state tracking and changes the task. In noisy play support includes every item, so useful Bayesian posterior feedback would be a further task change.",
        "pricing_only": "Replay the observed actions with list feedback added; no policy was sampled with this feedback. Strategy and output costs could change.",
        "extra_input_tokens_per_game": {
            str(n): float(np.mean(xs)) for n, xs in extra.items()
        },
        "extra_uncached_usd_per_game": {
            str(n): float(np.mean(xs)) * r["prefill"] for n, xs in extra.items()
        },
        "extra_uncached_usd_32_games": sum(
            16 * float(np.mean(xs)) * r["prefill"] for xs in extra.values()
        ),
    }
    (ROOT / "research/learnability_forecast.json").write_text(
        json.dumps(forecasts, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: forecasts[k]
                for k in [
                    "observed_probe_games",
                    "observed_cost_per_game_usd",
                    "pilot",
                    "full_eval_280_games_with_margin_usd",
                    "full_eval_280_full_cap_stress_with_margin_usd",
                    "available_project_usd",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
