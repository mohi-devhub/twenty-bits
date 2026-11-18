"""Freeze the approved raw-base pilot and verify its real cookbook data offline."""

import asyncio
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tinker_cookbook.completers import TokensWithLogprobs
from tinker_cookbook.rl.rollouts import do_single_rollout
from twenty_bits.baselines import Baseline
from twenty_bits.candidate_feedback import candidate_messages, token_hash
from twenty_bits.model_player import TableEnv
from twenty_bits.rl_pilot import group_data, pack_trajectory, unpack_trajectory
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT, load_split, seed_for, training_game


def freeze(path, value):
    if path.exists() and json.loads(path.read_text()) != value:
        raise RuntimeError(f"Prepared pilot artifact changed: {path.name}")
    if not path.exists():
        save_json(path, value)


async def main():
    proposed = json.loads(
        (ROOT / "research/candidate_set_pilot_raw_base.json").read_text()
    )
    config = json.loads((ROOT / "experiments/candidate_set_raw_base.json").read_text())
    for key in ("qualification", "evaluation_kind", "checkpoint_source_sha256"):
        config.pop(key, None)
    config.update(
        run_id="pilot-A-v1",
        display_name="Twenty Bits raw-base A pilot",
        ledger_phase=3,
        run_cap_usd="2.000000",
        training_authorized=True,
        rl_training_authorized=True,
        initial_policy="raw_base",
        observation_mode="candidate_set",
        training_kind="outcome_only_rl",
        sampling_checkpoint_paths={},
        policy="pilot_A",
        sampling_seed_namespace="pilot-A-v1",
        updates=16,
        groups_per_training_update=1,
        games_per_training_group=8,
        curriculum=proposed["curriculum"],
        sizes=[4, 8, 16],
        noise=0,
        development_checks=[0, 4, 8, 12, 16],
        kept_checkpoints=[4, 8, 12, 16],
        checkpoint_ttl_seconds=7200,
        lora={
            "rank": 32,
            "seed": 11,
            "train_mlp": True,
            "train_attn": True,
            "train_unembed": True,
        },
        adam={
            "learning_rate": 4e-5,
            "beta1": 0.9,
            "beta2": 0.95,
            "eps": 1e-8,
            "weight_decay": 0,
            "grad_clip_norm": 0,
        },
        loss_fn="importance_sampling",
        loss_fn_config=None,
        kl_penalty_coef=0,
        reward={
            "win": 1,
            "per_question": -0.03,
            "per_invalid": -0.1,
            "information_shaping": False,
        },
        variance_stop=proposed["required_stop_rule"],
        cookbook_pin="6c081121b90dbc290b4550eb9fd9f646f8e4960a",
        sdk_version="0.39.1",
    )
    config_path = ROOT / "experiments/pilot_A.json"
    freeze(config_path, config)
    training = []
    update = 0
    for phase in proposed["curriculum"]:
        for _ in range(phase["updates"]):
            update += 1
            training.append(
                {
                    "update": update,
                    "record": training_game(
                        phase["n"], 800000 + update, seed=11, noise=0
                    ),
                }
            )
    development = [
        training_game(n, i, seed=20261122, noise=0)
        for n in (4, 8)
        for i in (700100, 700101, 700102, 700103)
    ]
    manifest = {
        "training": training,
        "development": development,
        "examples": [development[0]["id"], development[4]["id"]],
        "examples_note": "Preselected development targets; compare raw base at update 0 with the last completed development snapshot. No extra paid examples or gradients on development games.",
    }
    manifest_path = ROOT / "experiments/pilot_A_games.json"
    freeze(manifest_path, manifest)
    train = set(load_split()["train"])
    held = set(load_split()["held_out"])
    rendering = Rendering(config["primary_model"], config)
    prompts = []
    for record in [r["record"] for r in training] + development:
        assert set(record["world"]["names"]) <= train
        assert not set(record["world"]["names"]) & held
        ids = rendering.prompt(candidate_messages(record)).to_ints()
        assert len(ids) + 2048 <= 32768
        prompts.append(
            {"id": record["id"], "tokens": len(ids), "sha256": token_hash(ids)}
        )
    distinct = []
    for row in training:
        seeds = [
            seed_for(f"pilot-A-v1/train/member-{i}", row["record"]["id"], 0) % (2**31)
            for i in range(8)
        ]
        assert len(set(seeds)) == 8
        distinct.append({"update": row["update"], "initial_generation_seeds": seeds})

    class OfflineCompleter:
        def __init__(self, env, index):
            self.env = env
            self.policy = Baseline(env.game, "random", index + 981)

        async def __call__(self, model_input, stop, *, max_tokens=None):
            action = self.policy.act(self.env.game)
            ids = rendering.tokenizer.encode(action, add_special_tokens=False) + [
                stop[0]
            ]
            return TokensWithLogprobs(
                tokens=ids, maybe_logprobs=[-0.1] * len(ids), stop_reason="stop"
            )

    # These scripted tests never enter the paid runner or a gradient request.
    data_checks = []
    for n in (4, 8, 16):
        record = next(r["record"] for r in training if r["record"]["n"] == n)
        trajectories = []
        raw_tokens = 0
        for i in range(8):
            env = TableEnv(
                record,
                config["primary_model"],
                config,
                message_builder=candidate_messages,
            )
            trajectory = await do_single_rollout(OfflineCompleter(env, i), env)
            assert (
                abs(sum(t.reward for t in trajectory.transitions) - env.game.reward)
                < 1e-10
            )
            trajectories.append(unpack_trajectory(pack_trajectory(trajectory)))
            raw_tokens += sum(
                t.ob.length + len(t.ac.tokens) - 1 for t in trajectory.transitions
            )
        data, archive, returns, advantages = group_data(trajectories)
        data_checks.append(
            {
                "n": n,
                "scripted_games": 8,
                "datums": len(data),
                "packed_training_tokens": sum(d.model_input.length for d in data),
                "sum_of_per_turn_training_tokens": raw_tokens,
                "sampled_tokens_trained_once": sum(
                    sum(r["training_mask"]) for r in archive
                ),
                "prompt_and_environment_loss_tokens": 0,
                "returns": returns,
                "advantages": advantages,
            }
        )
    implementations = {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        for p in (
            "twenty_bits/rl_pilot.py",
            "twenty_bits/model_player.py",
            "twenty_bits/tinker_transport.py",
            "twenty_bits/tinker_rendering.py",
            "twenty_bits/candidate_feedback.py",
            "twenty_bits/game.py",
            "twenty_bits/predicates.py",
            "twenty_bits/attributes.py",
            "twenty_bits/learnability.py",
            "twenty_bits/worlds.py",
            "scripts/run_rl_pilot.py",
            "scripts/run_format_sft.py",
        )
    }
    proof = {
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "games_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "implementation_sha256": implementations,
        "native_initial_prompts": prompts,
        "independent_group_seeds": distinct,
        "cookbook_data_checks": data_checks,
        "training_pool_only": True,
        "frozen_games_in_gradients": 0,
        "reward_is_outcome_only": True,
        "service_calls": 0,
        "forecast_before_margin_usd": str(
            proposed["scenarios"]["measured_output_full_budget"][
                "total_including_checkpoint_holds_usd"
            ]
        ),
        "forecast_including_margin_usd": str(
            proposed["scenarios"]["measured_output_full_budget"][
                "total_with_1_5_margin_usd"
            ]
        ),
        "run_cap_including_holds_usd": "2.000000",
        "optimizer_source": "Pinned cookbook recipes/rl_loop.py default learning rate 4e-5 and Adam beta1=.9 beta2=.95 eps=1e-8, one substep; rank 32. No KL or information shaping.",
    }
    freeze(ROOT / "research/pilot_A_preflight.json", proof)
    freeze(
        ROOT / "research/pilot_A_approval.json",
        {
            "date": "2026-11-18",
            "status": "approved",
            "global_cap_including_holds_usd": "50.000000",
            "pilot_cap_including_holds_usd": "2.000000",
            "initial_policy": "raw_base_no_sft",
            "updates": 16,
            "training_games": 128,
            "development_games": 40,
            "group_size": 8,
            "variance_stop": proposed["required_stop_rule"],
            "main_runs_authorized": False,
            "main_plan_sft_checkpoint": None,
            "sft_removal_reason": "Random-question SFT lowered EIG on the paired candidate-set qualification: pooled SFT minus raw base = -0.1444299248 bits/question, paired 95% CI [-0.2580291075,-0.0268366927]. SFT remains historical diagnostic data, never loaded into the main policy.",
        },
    )
    print(
        json.dumps(
            {
                "native_prompts": len(prompts),
                "scripted_data_checks": data_checks,
                "forecast_with_margin_usd": proof["forecast_including_margin_usd"],
                "cap_usd": "2.00",
                "service_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
