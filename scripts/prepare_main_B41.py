"""Freeze B41 science unchanged, with verified native endpoint persistence."""

import asyncio
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.prepare_rl_pilot import freeze
from tinker_cookbook.completers import TokensWithLogprobs
from tinker_cookbook.rl.rollouts import do_single_rollout
from twenty_bits.baselines import Baseline
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.candidate_feedback import candidate_messages, token_hash
from twenty_bits.model_player import TableEnv
from twenty_bits.native_checkpoints import storage_estimate
from twenty_bits.rl_pilot import group_data
from twenty_bits.replacement_registry import refresh_legacy_ids
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT, load_split, seed_for, training_game


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    persistence = json.loads(
        (ROOT / "research/native_persistence_test.json").read_text()
    )
    if not persistence.get("fresh_client_sample_passed"):
        raise RuntimeError("Native persistence must support fresh-client sampling.")
    storage = {
        kind: {
            "measured_test_bytes": row["size_bytes"],
            "size_multiplier": 2,
            "coverage_days": 30,
            "estimated_usd": str(storage_estimate(row["size_bytes"] * 2)),
            "maximum_usd": str(storage_estimate(row["size_bytes"] * 2)),
        }
        for kind, row in persistence["checkpoints"].items()
    }
    config = json.loads((ROOT / "experiments/main_A23.json").read_text())
    config.update(
        run_id="main-U-B41-v1",
        display_name="Twenty Bits main B seed 41",
        policy="main_B41",
        pilot_condition="B",
        noise=0.10,
        checkpoint_prefix="main-B-seed41",
        stage_gate="Stop after B seed 41 endpoint evaluation and report all three main seeds.",
        lora={**config["lora"], "seed": 41},
        checkpoint_ttl_seconds=None,
        permanent_storage=storage,
        endpoint_evaluations=["frozen_primary"],
    )
    config_path = ROOT / "experiments/main_B41.json"
    freeze(config_path, config)
    source = json.loads(
        gzip.decompress((ROOT / "experiments/main_A11_games.json.gz").read_bytes())
    )
    training = []
    for phase in config["curriculum"]:
        for _ in range(phase["updates"]):
            u = len(training) + 1
            training.append(
                {
                    "update": u,
                    "record": training_game(
                        phase["n"], 1000000 + u, seed=41, noise=0.10
                    ),
                }
            )
    manifest = {
        "training": training,
        "development": source["development"],
        "evaluation": source["evaluation"],
        "examples": source["examples"],
        "raw_development_source_sha256": source["raw_development_source_sha256"],
        "raw_frozen_source_sha256": sha(ROOT / "results/main_A11/games.jsonl.gz"),
        "training_index_namespace": 1000000,
        "note": "Fresh raw-base B seed 41, p=0.10 training only, unchanged primary protocol. Reuse the matched raw frozen/development controls. No auxiliary parser or synthetic game enters gradients.",
    }
    games_path = ROOT / "experiments/main_B41_games.json"
    freeze(games_path, manifest)
    games_path.with_suffix(".json.gz").write_bytes(
        gzip.compress(games_path.read_bytes(), mtime=0)
    )
    pool = set(load_split()["train"])
    assert len(training) == 30
    assert all(set(r["record"]["world"]["names"]) <= pool for r in training)
    assert not {r["record"]["id"] for r in training} & {
        r["id"] for r in manifest["development"] + manifest["evaluation"]
    }
    rendering = Rendering(config["primary_model"], config)
    hashes = json.loads((ROOT / "evals/candidate_set/prompt_hashes.json").read_text())[
        "hashes"
    ]
    prompts = []
    for r in (
        [x["record"] for x in training]
        + manifest["development"]
        + manifest["evaluation"]
    ):
        ids = rendering.prompt(candidate_messages(r)).to_ints()
        assert len(ids) + config["primary_output_cap"] <= config["context_window"]
        if r["id"] in hashes:
            assert token_hash(ids) == hashes[r["id"]]["main_initial_tokens_sha256"]
        prompts.append({"id": r["id"], "tokens": len(ids), "sha256": token_hash(ids)})

    class OfflineCompleter:
        def __init__(self, env, member):
            self.env = env
            self.policy = Baseline(env.game, "random", member + 981)

        async def __call__(self, model_input, stop, *, max_tokens=None):
            ids = rendering.tokenizer.encode(
                self.policy.act(self.env.game), add_special_tokens=False
            ) + [stop[0]]
            return TokensWithLogprobs(
                tokens=ids, maybe_logprobs=[-0.1] * len(ids), stop_reason="stop"
            )

    checks = []
    for n in config["sizes"]:
        r = next(x["record"] for x in training if x["record"]["n"] == n)
        trajectories = []
        for member in range(8):
            env = TableEnv(
                r, config["primary_model"], config, message_builder=candidate_messages
            )
            t = await do_single_rollout(OfflineCompleter(env, member), env)
            assert abs(sum(x.reward for x in t.transitions) - env.game.reward) < 1e-10
            trajectories.append(t)
        data, archive, returns, advantages = group_data(trajectories)
        checks.append(
            {
                "n": n,
                "games": 8,
                "training_tokens": sum(d.model_input.length for d in data),
                "returns": returns,
                "advantages": advantages,
                "prompt_loss_tokens": 0,
            }
        )
    independent = []
    for row in training:
        seeds = [
            seed_for(f"main-U-v1/B/seed41/train/member-{i}", row["record"]["id"], 0)
            % 2**31
            for i in range(8)
        ]
        assert len(set(seeds)) == 8
        independent.append({"update": row["update"], "initial_generation_seeds": seeds})
    schedule = [
        {
            "n": n,
            "update_start": min(x["update"] for x in training if x["record"]["n"] == n),
            "update_end": max(x["update"] for x in training if x["record"]["n"] == n),
        }
        for n in config["sizes"]
    ]
    forecast = json.loads((ROOT / "research/B41_forecast_after_A23.json").read_text())
    stage = Decimal(str(forecast["total_before_margin_usd"]))
    status = Ledger(ROOT / "ledger.json").status()
    remaining_all = stage * Decimal("1.5")
    assert Decimal(status["available_usd"]) >= remaining_all
    original_runner = (ROOT / "scripts/run_main_A23.py").read_text()
    replica_runner = (ROOT / "scripts/run_main_B41.py").read_text()

    def training_loop(text):
        body = text[text.index('            for row in manifest["training"]:') :]
        return body[: body.index('            last = updates[-1]["update"]')]

    assert training_loop(original_runner) == training_loop(replica_runner)
    parent = json.loads((ROOT / "research/main_A11_preflight.json").read_text())[
        "implementation_sha256"
    ]
    files = [name for name in parent if name != "scripts/run_main_seed.py"] + [
        "scripts/run_main_B41.py",
        "twenty_bits/native_checkpoints.py",
        "twenty_bits/budget.py",
        "twenty_bits/ledger_store.py",
    ]
    save_json(
        ROOT / "research/main_B41_preflight.json",
        {
            "config_sha256": sha(config_path),
            "games_sha256": sha(games_path),
            "implementation_sha256": {name: sha(ROOT / name) for name in files},
            "native_initial_prompts": prompts,
            "independent_group_seeds": independent,
            "cookbook_data_checks": checks,
            "curriculum": schedule,
            "training_pool_only": True,
            "frozen_games_in_gradients": 0,
            "reward_is_outcome_only": True,
            "training_loop_identical_to_A23": True,
            "training_loop_sha256": hashlib.sha256(
                training_loop(original_runner).encode()
            ).hexdigest(),
            "auxiliary_parser_in_primary_or_training": False,
            "service_calls": 0,
            "stage_forecast_before_margin_usd": str(stage),
            "stage_forecast_including_margin_usd": str(stage * Decimal("1.5")),
            "remaining_U_with_margin_usd": str(remaining_all),
            "permanent_native_training_and_sampler": True,
            "storage_hold_coverage_days": 30,
            "external_upload_or_export_required": False,
            "global_budget_before_B41": {
                k: v for k, v in status.items() if k != "entries"
            },
            "matched_frozen_cells": 10,
            "frozen_games_per_policy": 280,
            "new_frozen_base_games": 0,
            "reused_raw_frozen_games": 280,
            "persistence_test_must_complete_before_paid_B41": True,
            "A11_suffix_and_hard_mode": "not run: A11 checkpoint wasn't persisted, external uploads unavailable",
            "stop_after_B41_endpoint": True,
        },
    )
    ids = set()
    for filename in (
        "research/main_A11_replacements.json",
        "research/A11_suffix_diagnostic_replacements.json",
    ):
        registry = json.loads((ROOT / filename).read_text())
        ids.update(registry["legacy_lost_entry_ids"])
        ids.update(c["original_entry_id"] for c in registry["cases"])
    registry_path = ROOT / "research/main_B41_replacements.json"
    if not registry_path.exists():
        save_json(registry_path, {"legacy_lost_entry_ids": sorted(ids), "cases": []})
    refresh_legacy_ids(registry_path)
    approval = json.loads((ROOT / "research/main_B41_approval.json").read_text())
    assert approval["authorized"] and approval["active_stage"] == "B41"
    print(
        json.dumps(
            {
                "training_groups": 30,
                "games": 240,
                "native_prompts": len(prompts),
                "scripted_groups_checked": len(checks),
                "stage_forecast_with_margin": str(stage * Decimal("1.5")),
                "service_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
