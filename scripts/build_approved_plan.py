"""Reprice the authorized phase and eight-game training groups, offline."""

from pathlib import Path
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT
from twenty_bits.tinker_transport import sample_cost


def main():
    old = json.loads((ROOT / "research/paid_plans.json").read_text())
    plan = next(p for p in old["plans"] if p["cap_usd"] == 50)
    config = json.loads((ROOT / "evals/phase2.json").read_text())
    measurement = json.loads((ROOT / "research/token_measurements.json").read_text())
    maximum = 0
    for model in [config["primary_model"], config["reference_model"]]:
        for cell in measurement["models"][model]["cells"]:
            reference = model == config["reference_model"]
            if reference and cell["n"] not in config["reference_sizes"]:
                continue
            games = (
                config["reference_games_per_cell"]
                if reference
                else config["primary_games_per_cell"]
            )
            cap = (
                config["reference_output_cap"]
                if reference
                else config["primary_output_cap"]
            )
            turns = 2 * math.ceil(math.log2(cell["n"])) + 1
            inputs = (
                turns * cell["initial_prompt_tokens"]["max"]
                + (cap + 32) * turns * (turns - 1) // 2
            )
            maximum += games * float(sample_cost(model, inputs, cap * turns))
    phase2 = (
        plan["parts_usd"]["phase2_base_primary"]
        + plan["parts_usd"]["phase2_reference_20_games"]
    )
    pilot = plan["parts_usd"]["phase3_pilot_training"] * (32 / 48) * 2
    main = plan["parts_usd"]["phase4_main_training"] * 2
    dev = plan["parts_usd"]["phase3_pilot_dev_checks"] / 2
    legacy = phase2 + pilot + dev + main + plan["parts_usd"]["phase4_final_evaluations"]
    result = {
        "approval_date": config["approval_date"],
        "approved_total_cap_usd": 50,
        "phase2": {
            "primary_model": config["primary_model"],
            "primary_games": 280,
            "reference_model": config["reference_model"],
            "reference_games": 20,
            "alternative_screen_games": 0,
            "forecast_usd": phase2,
            "forecast_with_margin_usd": phase2 * 1.5,
            "uncached_token_cap_envelope_usd": maximum,
            "forecast_basis": "Phase 1 measured maximum prefixes, full question budgets; Qwen 64 and reference 128 generated tokens/turn. No cache credit.",
        },
        "training": {
            "authorized": False,
            "games_per_group": 8,
            "groups_per_update": 1,
            "pilot_condition": "A",
            "pilot_A_32_updates_games": 256,
            "pilot_A_32_updates_forecast_usd": pilot,
            "pilot_A_24_development_games_forecast_usd": dev,
            "main_32_updates_games_per_seed": 256,
            "main_32_updates_forecast_per_seed_usd": main / 5,
            "old_five_seed_schedule_with_A_only_pilot_usd": legacy,
            "old_five_seed_schedule_with_margin_usd": legacy * 1.5,
            "status": "Over cap at 32 main updates. Choose S or U after the A pilot using actual usage and learning speed; no main schedule is active.",
        },
    }
    (ROOT / "research/approved_plan.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
