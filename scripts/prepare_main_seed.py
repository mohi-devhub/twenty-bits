"""Freeze main A seed 11, the requested gate and its offline preflight."""

import asyncio
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.prepare_rl_pilot import freeze
from tinker_cookbook.completers import TokensWithLogprobs
from tinker_cookbook.rl.rollouts import do_single_rollout
from twenty_bits.baselines import Baseline
from twenty_bits.budget import Ledger
from twenty_bits.candidate_feedback import candidate_messages, token_hash
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.guess_metrics import guess_state
from twenty_bits.model_player import TableEnv
from twenty_bits.rl_pilot import group_data
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.worlds import ROOT, load_split, seed_for, training_game


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    proposal = json.loads((ROOT / "research/main_options_after_pilot.json").read_text())
    option = proposal["options"]["U"]
    config = json.loads((ROOT / "experiments/pilot_A.json").read_text())
    config.update(
        run_id="main-U-A11-v1",
        display_name="Twenty Bits main A seed 11",
        ledger_phase=4,
        run_cap_usd="42.490000",
        policy="main_A11",
        updates=30,
        curriculum=option["curriculum"],
        sizes=[4, 8, 16, 32, 64, 128],
        primary_games_per_cell=28,
        kept_checkpoints=[30],
        development_checks=option["development_checks"],
        checkpoint_prefix="main-A-seed11",
        sampling_seed_namespace="main-U-v1",
        guess_metric_version="guess-with-k-v1",
        variance_stop=None,
        stage_gate="Stop after A seed 11 endpoint, before A seed 23 or B seed 41.",
    )
    for key in ("games_per_size",):
        config.pop(key, None)
    config_path = ROOT / "experiments/main_A11.json"
    freeze(config_path, config)
    training = []
    for phase in option["curriculum"]:
        for _ in range(phase["updates"]):
            u = len(training) + 1
            training.append(
                {
                    "update": u,
                    "record": training_game(phase["n"], 1000000 + u, seed=11, noise=0),
                }
            )
    assert len(training) == 30
    development = json.loads((ROOT / "experiments/pilot_A_games.json").read_text())[
        "development"
    ]
    evaluation = [
        r
        for cell in frozen_manifest()["cells"]
        for r in frozen_games(cell["domain"], cell["n"], cell["noise"], 28)
    ]
    assert len(evaluation) == 280
    manifest = {
        "training": training,
        "development": development,
        "evaluation": evaluation,
        "raw_development_source_sha256": sha(ROOT / "results/pilot_A/games.jsonl.gz"),
        "examples": [development[0]["id"], development[4]["id"]],
        "training_index_namespace": 1000000,
        "note": "Only animals training-pool groups enter gradients. Development and all frozen cases never enter gradients. Reuse the matched raw development control, and purchase a new full frozen raw control.",
    }
    games_path = ROOT / "experiments/main_A11_games.json"
    freeze(games_path, manifest)
    schedule = [
        {
            "n": n,
            "update_start": min(r["update"] for r in training if r["record"]["n"] == n),
            "update_end": max(r["update"] for r in training if r["record"]["n"] == n),
        }
        for n in config["sizes"]
    ]
    assert any(r["n"] == 32 for r in schedule) and any(r["n"] == 128 for r in schedule)
    approved = {**option, "authorized": True}
    freeze(
        ROOT / "research/main_U_approval.json",
        {
            "date": "2026-11-18",
            "approved_option": approved,
            "active_stage": "A11",
            "stop_after_A11_endpoint": True,
            "A23_or_B41_may_start_before_gate": False,
            "global_cap_including_holds_usd": "50.000000",
            "initialization": "fresh_raw_base_no_sft_no_pilot_adapter",
            "reward_and_caps_unchanged": True,
            "hard_mode": "Deferred until the end, as approved.",
            "new_metric": "guess-with-k-v1: exact support when noiseless; displayed posterior-threshold list plus MAP when noisy; also retain full positive support. Counts and wins at k=1,2,3,4+, with all-game and guess denominators.",
            "main_horizon": "30 scheduled updates per seed; the four-update variance halt was the completed pilot qualification. Main variance remains logged.",
            "curriculum": schedule,
            "no_further_seed_before_user_gate_decision": True,
        },
    )
    train_pool = set(load_split()["train"])
    held = set(load_split()["held_out"])
    train_ids = {r["record"]["id"] for r in training}
    assert not train_ids & {r["id"] for r in development + evaluation}
    assert all(set(r["record"]["world"]["names"]) <= train_pool for r in training)
    assert not any(set(r["record"]["world"]["names"]) & held for r in training)
    rendering = Rendering(config["primary_model"], config)
    hashes = json.loads((ROOT / "evals/candidate_set/prompt_hashes.json").read_text())[
        "hashes"
    ]
    prompts = []
    for record in [r["record"] for r in training] + development + evaluation:
        ids = rendering.prompt(candidate_messages(record)).to_ints()
        digest = token_hash(ids)
        assert len(ids) + 2048 <= 32768
        if record["id"] in hashes:
            assert hashes[record["id"]]["main_initial_tokens_sha256"] == digest
        prompts.append({"id": record["id"], "tokens": len(ids), "sha256": digest})
    distinct = []
    for row in training:
        seeds = [
            seed_for(f"main-U-v1/A/seed11/train/member-{i}", row["record"]["id"], 0)
            % (2**31)
            for i in range(8)
        ]
        assert len(set(seeds)) == 8
        distinct.append({"update": row["update"], "initial_generation_seeds": seeds})

    class OfflineCompleter:
        def __init__(self, env, index):
            self.env = env
            self.policy = Baseline(env.game, "random", index + 981)

        async def __call__(self, model_input, stop, *, max_tokens=None):
            ids = rendering.tokenizer.encode(
                self.policy.act(self.env.game), add_special_tokens=False
            ) + [stop[0]]
            return TokensWithLogprobs(
                tokens=ids, maybe_logprobs=[-0.1] * len(ids), stop_reason="stop"
            )

    checks = []
    for n in config["sizes"]:
        record = next(r["record"] for r in training if r["record"]["n"] == n)
        trajectories = []
        for i in range(8):
            env = TableEnv(
                record,
                config["primary_model"],
                config,
                message_builder=candidate_messages,
            )
            t = await do_single_rollout(OfflineCompleter(env, i), env)
            assert abs(sum(x.reward for x in t.transitions) - env.game.reward) < 1e-10
            state = guess_state(env.result(), record)
            assert state is not None and state["won"] == env.game.won
            trajectories.append(t)
        data, archive, returns, advantages = group_data(trajectories)
        checks.append(
            {
                "n": n,
                "scripted_games": 8,
                "training_tokens": sum(d.model_input.length for d in data),
                "sampled_tokens_trained_once": sum(
                    sum(r["training_mask"]) for r in archive
                ),
                "prompt_loss_tokens": 0,
                "returns": returns,
                "advantages": advantages,
            }
        )
    dev = Decimal(str(option["development_usd"])) / 3
    stage = (
        Decimal(str(option["training_usd_per_A_seed"]))
        + dev
        + 2 * Decimal(str(proposal["fixed_model_evaluation_280_games_usd"]))
        + Decimal(".10")
    )
    ledger = Ledger(ROOT / "ledger.json")
    ledger.check_run(
        estimate_usd=str(option["total_before_margin_usd"]),
        max_cost_usd=str(option["total_before_margin_usd"]),
    )
    implementations = {
        name: sha(ROOT / name)
        for name in (
            "twenty_bits/rl_pilot.py",
            "twenty_bits/model_player.py",
            "twenty_bits/tinker_transport.py",
            "twenty_bits/tinker_rendering.py",
            "twenty_bits/candidate_feedback.py",
            "twenty_bits/guess_metrics.py",
            "twenty_bits/game.py",
            "twenty_bits/predicates.py",
            "twenty_bits/attributes.py",
            "twenty_bits/learnability.py",
            "twenty_bits/worlds.py",
            "scripts/run_main_seed.py",
            "scripts/run_rl_pilot.py",
            "scripts/run_format_sft.py",
        )
    }
    freeze(
        ROOT / "research/main_A11_preflight.json",
        {
            "config_sha256": sha(config_path),
            "games_sha256": sha(games_path),
            "implementation_sha256": implementations,
            "native_initial_prompts": prompts,
            "independent_group_seeds": distinct,
            "cookbook_data_checks": checks,
            "training_pool_only": True,
            "frozen_games_in_gradients": 0,
            "reward_is_outcome_only": True,
            "service_calls": 0,
            "stage_forecast_before_margin_usd": str(stage),
            "stage_forecast_including_margin_usd": str(stage * Decimal("1.5")),
            "approved_option_total_with_margin_usd": str(
                option["total_with_1_5_margin_usd"]
            ),
            "global_budget_before_calls": {
                k: v for k, v in ledger.status().items() if k != "entries"
            },
            "curriculum": schedule,
            "matched_frozen_cells": 10,
            "frozen_games_per_policy": 280,
        },
    )
    print(
        json.dumps(
            {
                "native_prompts": len(prompts),
                "scripted_checks": len(checks),
                "stage_forecast_with_margin": str(stage * Decimal("1.5")),
                "curriculum": schedule,
                "service_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
