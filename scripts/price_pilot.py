"""Price an A-only pilot from observed base output lengths, without training."""

from pathlib import Path
from decimal import Decimal
import gzip
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from twenty_bits.budget import Ledger
from twenty_bits.tinker_transport import rates, save_json
from twenty_bits.worlds import ROOT


def main():
    config = json.loads((ROOT / "evals/phase2.json").read_text())
    summary = json.loads((ROOT / "results/phase2/summary.json").read_text())
    if summary["status"] != "complete":
        raise ValueError("Finish Phase 2 before issuing its pilot forecast.")
    records = [
        json.loads(line)
        for line in gzip.decompress(
            (ROOT / "results/phase2/games.jsonl.gz").read_bytes()
        ).splitlines()
    ]
    animals32 = [
        r
        for r in records
        if r["model"] == config["primary_model"]
        and r["domain"] == "animals"
        and r["n"] == 32
        and r["noise"] == 0
    ]
    output_mean = sum(g["output_tokens"] for g in animals32) / sum(
        g["sampling_calls"] for g in animals32
    )
    output_p95 = float(
        np.quantile(
            [t["usage"]["output_tokens"] for g in animals32 for t in g["turns"]], 0.95
        )
    )
    old = json.loads((ROOT / "research/paid_plans.json").read_text())
    prefixes = old["training_prompt_measurements"][config["primary_model"]]
    r = rates(config["primary_model"])

    def game_cost(n, output, training):
        prefix = prefixes[str(n)]["max"]
        inputs = generated = 0.0
        used = 0
        for turn in range(2 * (n - 1).bit_length() + 1):
            prompt = prefix + turn * (output + 32)
            if prompt + config["primary_output_cap"] > config["context_window"]:
                break
            inputs += prompt
            generated += output
            used += 1
        cost = (
            Decimal(str(inputs)) * r["prefill"] + Decimal(str(generated)) * r["sample"]
        )
        if training:
            cost += Decimal(str(inputs + generated)) * r["train"]
        return float(cost / Decimal(1_000_000)), used

    status = Ledger(ROOT / "ledger.json").status()
    available = float(status["available_usd"])
    proposals = []
    for updates in (8, 16, 32):
        estimates = {}
        for label, length in [
            ("short_64_token_sensitivity", 64),
            ("observed_base_output_proxy", output_mean),
            ("output_cap_stress", config["primary_output_cap"]),
        ]:
            training = sum(
                updates / 2 * 8 * game_cost(n, length, True)[0] for n in (16, 32)
            )
            # Eight fixed development games at updates 0, quarter, half, endpoint.
            development = 32 * game_cost(32, length, False)[0]
            storage = 0.10
            estimates[label] = {
                "output_tokens_per_turn": length,
                "training_usd": training,
                "development_usd": development,
                "checkpoint_storage_allowance_usd": storage,
                "total_usd": training + development + storage,
                "with_margin_usd": 1.5 * (training + development + storage),
                "fits_remaining_usd": 1.5 * (training + development + storage)
                <= available,
            }
        proposals.append(
            {
                "updates": updates,
                "condition": "A",
                "games_per_group": 8,
                "training_games": updates * 8,
                "curriculum": "N=16 then N=32, equal update counts",
                "development_games": 32,
                "estimates": estimates,
            }
        )
    result = {
        "status": "proposals only; no training authorized",
        "source_model": config["primary_model"],
        "source_games": len(animals32),
        "observed_output_tokens_per_call": output_mean,
        "observed_output_tokens_per_call_p95": output_p95,
        "source_invalid_rate": next(
            c["invalid_rate"]
            for c in summary["cells"]
            if c["model"] == config["primary_model"]
            and c["domain"] == "animals"
            and c["n"] == 32
            and c["noise"] == 0
        ),
        "available_after_spend_and_holds_usd": status["available_usd"],
        "assumptions": "Full question budget plus guess; measured maximum training-pool table prefix; per-turn full contexts charged for sampling and training; no cache credit. N=16 output length is an unmeasured proxy from N=32. Learning may shorten outputs. Storage allowance assumes at most four sampler snapshots, each no larger than 64 GB with a two-hour TTL. At $0.10/GB/month that bound costs $0.071112; reserve $0.10 even if the organization has free storage. No optimizer-state checkpoint or storage-plan change is included. Verify this bound and reserve storage before creating snapshots.",
        "storage_pricing_source": "https://tinker-docs.thinkingmachines.ai/administration/checkpoint-storage-pricing/",
        "pilot_options": proposals,
        "main_options_at_pilot_gate": {
            "S": {"A_seeds": [11, 23, 37], "B_seeds": [41, 53]},
            "U": {"A_seeds": [11, 23], "B_seeds": [41]},
            "decision": "Price updates and recommend only after measuring the pilot learning speed and cost. Visible curves take priority over seed count.",
        },
    }
    save_json(ROOT / "research/pilot_after_phase2.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
