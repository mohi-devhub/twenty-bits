"""Price an unapproved A pilot using measured candidate-list token sequences."""

from decimal import Decimal, ROUND_CEILING
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.game import Game
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import rates, save_json
from twenty_bits.worlds import ROOT, training_game


def price_policy(policy):
    config = json.loads((ROOT / f"experiments/candidate_set_{policy}.json").read_text())
    summary = json.loads(
        (ROOT / f"results/candidate_set/{policy}/summary.json").read_text()
    )
    if summary["decision"] != "qualified_stop_before_rl":
        raise RuntimeError("Qualification failed; no RL pilot proposal is eligible.")
    rendering = Rendering(config["primary_model"], config)
    rate = {k: float(v) / 1e6 for k, v in rates(config["primary_model"]).items()}
    measured_outputs = {
        c["n"]: c["mean_output_tokens_per_call"] for c in summary["cells"]
    }
    prices = {}
    for n in (4, 8, 16):
        examples = []
        for i in range(40):
            record = training_game(n, 700000 + i, seed=20261122, noise=0)
            g = Game(record)
            # A legal constant question retains every name. This deliberately
            # measures full-budget list/history overhead without bisection.
            action = "ASK: a OR NOT a"
            history_output = (
                len(rendering.tokenizer.encode(action, add_special_tokens=False)) + 1
            )
            lengths = []
            for turn in range(g.limit + 1):
                lengths.append(
                    rendering.prompt(candidate_messages(record, g.turns)).length
                )
                if turn < g.limit:
                    g.step(action)
            scenarios = {}
            for scenario in ("measured_output_full_budget", "output_cap_stress"):
                out = (
                    2048
                    if scenario == "output_cap_stress"
                    else math.ceil(measured_outputs[min(n, 8)])
                )
                inputs = outputs = calls = 0
                for t, length in enumerate(lengths):
                    # Never reduce the measured native context. Inflate prior
                    # assistant spans when the sampled-output proxy is longer.
                    context = length + t * max(0, out - history_output)
                    if (
                        context + config["primary_output_cap"]
                        > config["context_window"]
                    ):
                        break
                    inputs += context
                    outputs += out
                    calls += 1
                sampling = inputs * rate["prefill"] + outputs * rate["sample"]
                gradient = (inputs + outputs) * rate["train"]
                scenarios[scenario] = {
                    "sampling_usd": sampling,
                    "gradient_usd": gradient,
                    "combined_usd": sampling + gradient,
                    "input_tokens": inputs,
                    "output_tokens": outputs,
                    "calls": calls,
                    "output_tokens_per_call_proxy": out,
                }
            examples.append(
                {
                    "id": record["id"],
                    "initial_tokens": lengths[0],
                    "scenarios": scenarios,
                }
            )
        prices[n] = {
            "measured_training_pool_prefixes": 40,
            "initial_tokens_mean": float(
                np.mean([e["initial_tokens"] for e in examples])
            ),
            "initial_tokens_max": max(e["initial_tokens"] for e in examples),
            "scenarios": {
                scenario: max(
                    (e["scenarios"][scenario] for e in examples),
                    key=lambda x: x["combined_usd"],
                )
                for scenario in ("measured_output_full_budget", "output_cap_stress")
            },
        }
    schedule = {4: 4, 8: 8, 16: 4}
    scenarios = {}
    for name in ("measured_output_full_budget", "output_cap_stress"):
        sampling = sum(
            u * 8 * prices[n]["scenarios"][name]["sampling_usd"]
            for n, u in schedule.items()
        )
        gradient = sum(
            u * 8 * prices[n]["scenarios"][name]["gradient_usd"]
            for n, u in schedule.items()
        )
        # Five checks, each with four N=4 and four N=8 development games.
        dev = 5 * sum(4 * prices[n]["scenarios"][name]["sampling_usd"] for n in (4, 8))
        # Six operations with at most $0.05 held each, including restoring the
        # locally saved adapter if the original hosted checkpoint has expired.
        storage_holds = 0.30
        total = sampling + gradient + dev + storage_holds
        abort = (
            4 * 8 * prices[4]["scenarios"][name]["combined_usd"]
            + 2 * sum(4 * prices[n]["scenarios"][name]["sampling_usd"] for n in (4, 8))
            + storage_holds
        )
        scenarios[name] = {
            "training_sampling_usd": sampling,
            "training_gradient_usd": gradient,
            "development_sampling_usd": dev,
            "checkpoint_holds_usd": storage_holds,
            "total_including_checkpoint_holds_usd": total,
            "total_with_1_5_margin_usd": total * 1.5,
            "four_update_abort_with_margin_usd": abort * 1.5,
        }
    expected = Decimal(
        str(scenarios["measured_output_full_budget"]["total_with_1_5_margin_usd"])
    )
    # A concrete spending ceiling above the measured-token forecast plus margin.
    proposed_cap = max(
        Decimal("1.50"),
        (expected / Decimal(".50")).to_integral_value(rounding=ROUND_CEILING)
        * Decimal(".50"),
    )
    ledger = Ledger(ROOT / "ledger.json").status()
    assert proposed_cap < Decimal(ledger["available_usd"])
    result = {
        "authorized": False,
        "rl_updates_started": 0,
        "initial_policy": policy,
        "observation_mode": "candidate_set",
        "condition": "A",
        "seed": 11,
        "updates": 16,
        "groups_per_update": 1,
        "games_per_group": 8,
        "training_games": 128,
        "curriculum": [
            {"n": n, "updates": u, "games": u * 8} for n, u in schedule.items()
        ],
        "group_definition": "Eight independent generation seeds from one common training_game start state per update.",
        "advantage": "Subtract the group mean total return and divide by the population standard deviation plus 1e-8. A constant-return group has zero advantages.",
        "reward": {
            "win": 1,
            "per_question": -0.03,
            "per_invalid": -0.1,
            "information_shaping": False,
        },
        "thinking": False,
        "output_cap": 2048,
        "grammar_version": "attribute-codes-v2",
        "development_checks": [0, 4, 8, 12, 16],
        "development_games_per_check": 8,
        "development_slice": {
            "factory": "training_game",
            "seed": 20261122,
            "sizes": [4, 8],
            "indices": [700100, 700101, 700102, 700103],
        },
        "required_stop_rule": {
            "after_updates": 4,
            "halt_if_fraction_of_nonzero_return_variance_groups_below": 0.25,
            "nonzero_variance_tolerance": 1e-12,
        },
        "stop_rule_note": "With four total groups, zero nonconstant groups halts; one equals 25% and passes. Cost-only return variance can pass, so also report win variation without adding another stop rule.",
        "method": "Measure native candidate-list contexts on 40 fresh training-pool starts at each N. Retain all candidates via a tautology and charge the full question budget plus final-guess slot. Use the maximum measured context trajectory at each N. Generated-token proxies come from this policy's completed candidate-set qualification; N=16 uses its N=8 proxy and is unmeasured model behavior. Charge full per-turn context plus output for gradients and give sampling caches no credit. No new training is performed by this script.",
        "gradient_billing_assumption": "Conservatively sum each turn's full input plus sampled output, even with prompt loss masked. The actual cookbook datum packing will be verified before any approved RL call.",
        "storage_note": "Up to four native kept checkpoints and a final external export, plus one restore upload if using an expired hosted SFT checkpoint, with two-hour TTLs and at most $0.05 held per operation. $0.30 is a conservative common hold allowance, not a storage bill. Preserve and download the final adapter locally.",
        "profiles": prices,
        "scenarios": scenarios,
        "proposed_run_ceiling_including_holds_usd": str(proposed_cap),
        "ceiling_note": "The output-cap stress scenario is not the forecast. If individual reservations would exceed the approved pilot ceiling, halt with pending work retained; do not change caps or rewards mid-run.",
        "available_project_usd": ledger["available_usd"],
        "after_proposed_pilot_ceiling_usd": str(
            Decimal(ledger["available_usd"]) - proposed_cap
        ),
        "after_measured_forecast_with_margin_usd": str(
            Decimal(ledger["available_usd"]) - expected
        ),
        "gate_after_pilot": "Report learning curves and the behavior audit; offer S (A:3,B:2 seeds) versus U (A:2,B:1) priced using observed learning speed. Do not start main runs.",
    }
    save_json(ROOT / f"research/candidate_set_pilot_{policy}.json", result)
    return result


def main():
    proposals = {policy: price_policy(policy) for policy in ("format_sft", "raw_base")}
    result = {
        "authorized": False,
        "recommended_initial_policy": "raw_base",
        "recommendation": "Raw base passed the same qualification and won 23/32 versus 14/32 for SFT, with higher validity and EIG. Propose raw base to avoid the SFT attribute-action prior; this is a development-slice recommendation, not a general SFT claim. Initialization remains the user's choice.",
        "alternatives": proposals,
    }
    save_json(ROOT / "research/candidate_set_pilot_proposal.json", result)
    print(
        json.dumps(
            {
                "authorized": False,
                "recommended_initial_policy": "raw_base",
                "alternatives": {
                    p: {
                        "scenarios": v["scenarios"],
                        "proposed_run_ceiling_including_holds_usd": v[
                            "proposed_run_ceiling_including_holds_usd"
                        ],
                    }
                    for p, v in proposals.items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
