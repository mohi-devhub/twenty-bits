"""Reproduce planning estimates from a saved public Tinker rate card.

These are scenarios, not measurements or permission to spend. Before a real
call, tokenize its actual prompt and reserve its token-limited maximum.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZES = (16, 32, 64, 128, 256)
CELLS_PER_SIZE = 4 * 2


def rates_for(catalog: list[dict], model_id: str) -> dict[str, Decimal]:
    model = next(row for row in catalog if row["tinker_id"] == model_id)
    return {
        key: Decimal(model[key].removeprefix("$"))
        for key in ("prefill", "cached_prefill", "sample", "train")
    }


def game_tokens(n: int, *, stress: bool) -> tuple[int, int]:
    """Include a final guess and repeated table/history input on every turn."""
    log_n = n.bit_length() - 1
    if n <= 1 or 2**log_n != n:
        raise ValueError("The planning grid uses powers of two greater than one.")
    turns = (2 if stress else 1) * log_n + 1
    prompt = 512 + 24 * n
    output_per_turn = 256 if stress else 128
    history_per_turn = output_per_turn + 32
    input_tokens = turns * prompt + history_per_turn * turns * (turns - 1) // 2
    return input_tokens, turns * output_per_turn


def sample_cost(
    tokens: tuple[int, int], rates: dict[str, Decimal], *, cached: bool
) -> Decimal:
    inputs, outputs = tokens
    input_rate = rates["cached_prefill" if cached else "prefill"]
    return (inputs * input_rate + outputs * rates["sample"]) / Decimal(1_000_000)


def grid_cost(
    games_per_cell: int, rates: dict[str, Decimal], *, stress: bool, cached: bool
) -> Decimal:
    return (
        sum(
            (
                sample_cost(game_tokens(n, stress=stress), rates, cached=cached)
                for n in SIZES
            ),
            Decimal(0),
        )
        * CELLS_PER_SIZE
        * games_per_cell
    )


def training_cost(
    n: int, rates: dict[str, Decimal], *, stress: bool, cached: bool
) -> Decimal:
    tokens = game_tokens(n, stress=stress)
    # Conservatively allow one full datum per turn. Cookbook prefix reuse can
    # reduce this, but masked prompt tokens still incur training charges.
    return sample_cost(tokens, rates, cached=cached) + sum(tokens) * rates[
        "train"
    ] / Decimal(1_000_000)


def projection(catalog: list[dict]) -> dict:
    small_id, large_id = "Qwen/Qwen3-8B", "openai/gpt-oss-120b"
    small, large = rates_for(catalog, small_id), rates_for(catalog, large_id)
    scenarios = {}
    for name, stress, cached in [
        ("expected_no_cache", False, False),
        ("optimistic_all_prefill_cached", False, True),
        ("stress_no_cache", True, False),
    ]:
        small_grid = grid_cost(200, small, stress=stress, cached=cached)
        large_grid = grid_cost(20, large, stress=stress, cached=cached)
        pilot_train = sum(
            (
                128 * training_cost(n, small, stress=stress, cached=cached)
                for n in (16, 32)
            ),
            Decimal(0),
        )
        pilot_eval = 2 * grid_cost(5, small, stress=stress, cached=cached)
        main_train = sum(
            (
                6 * 200 * training_cost(n, small, stress=stress, cached=cached)
                for n in SIZES[:-1]
            ),
            Decimal(0),
        )
        phases = {
            "0": {"research_and_budget": Decimal(0)},
            "1": {"offline_environment_and_baselines": Decimal(0)},
            "2": {
                "small_zero_shot_8000_games": small_grid,
                "large_zero_shot_800_games": large_grid,
            },
            "3": {
                "pilot_256_training_games": pilot_train,
                "pilot_400_eval_games": pilot_eval,
            },
            "4": {
                "main_4800_training_games": main_train,
                "six_final_full_evals_48000_games": 6 * small_grid,
            },
            "5": {"offline_analysis": Decimal(0)},
        }
        amounts = {
            phase: {**parts, "total_usd": sum(parts.values(), Decimal(0))}
            for phase, parts in phases.items()
        }
        total = sum((row["total_usd"] for row in amounts.values()), Decimal(0))
        scenarios[name] = {
            "phases": amounts,
            "total_usd": total,
            "total_times_1_5_usd": total * Decimal("1.5"),
        }
    diagnostic_phase2 = grid_cost(5, small, stress=False, cached=False) + grid_cost(
        5, large, stress=False, cached=False
    )
    diagnostic_phase3 = sum(
        (64 * training_cost(n, small, stress=False, cached=False) for n in (16, 32)),
        Decimal(0),
    ) + 2 * grid_cost(1, small, stress=False, cached=False)
    diagnostic_phase4 = sum(
        (
            6 * 24 * training_cost(n, small, stress=False, cached=False)
            for n in SIZES[:-1]
        ),
        Decimal(0),
    ) + 6 * grid_cost(5, small, stress=False, cached=False)
    diagnostic_total = diagnostic_phase2 + diagnostic_phase3 + diagnostic_phase4
    return {
        "models": {"small": small_id, "large_reference_only": large_id},
        "assumptions": {
            "cells": 40,
            "small_games_per_cell": 200,
            "large_games_per_cell": 20,
            "prompt_tokens": "512 + 24*N; planning assumption until the Phase 1 tables are tokenized",
            "expected_turns": "log2(N) questions + one final guess",
            "stress_turns": "2*log2(N) questions + one final guess",
            "expected_output_tokens_per_turn": 128,
            "stress_output_tokens_per_turn": 256,
            "history_overhead_tokens_per_turn": 32,
            "pilot": "32 steps * 2 groups * 4 games; half at N=16, half at N=32; two 200-game eval slices",
            "main": "six runs, each 100 steps * 2 groups * 4 games; equal allocation at N=16,32,64,128",
            "kept_main_checkpoints": "one final checkpoint per run, the minimum for six runs",
            "training_tokens": "conservative sum of per-turn input and output, including masked prompt tokens",
            "storage": "zero only if the organization has free-plan headroom; account not verified",
            "status": "unapproved planning scenarios, not frozen experimental settings or guaranteed bills",
        },
        "scenarios": scenarios,
        "unapproved_smaller_diagnostic": {
            "phase_2_usd": diagnostic_phase2,
            "phase_3_usd": diagnostic_phase3,
            "phase_4_usd": diagnostic_phase4,
            "total_usd": diagnostic_total,
            "total_times_1_5_usd": diagnostic_total * Decimal("1.5"),
            "assumptions": "no cache savings; 5 games/cell/model; pilot 32 updates x 1 group x 4 games at N=16,32; two 40-game eval slices; six main runs of 24 updates x 1 group x 4 games across N=16,32,64,128; one final checkpoint/run",
            "status": "proposal only; weak cell-level power; real token maxima can still make it unaffordable",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, default=ROOT / "research/tinker-models-2026-11-17.json"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = projection(json.loads(args.catalog.read_text()))
    rendered = (
        json.dumps(result, indent=2, default=lambda value: format(value, ".8f")) + "\n"
    )
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
