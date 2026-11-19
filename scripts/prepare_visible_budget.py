"""Freeze and price the eval-only counter amendment without SDK access."""

from collections import defaultdict
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger, money
from twenty_bits.candidate_feedback import candidate_messages, token_hash
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import rates, save_json
from twenty_bits.visible_budget import PROMPT_VERSION, visible_budget_messages
from twenty_bits.worlds import ROOT


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def primary_games():
    result = {}
    for label, folder, kind in [
        ("Raw", "main_A11", "eval_base"),
        ("A23", "main_A23", "eval_endpoint"),
        ("B41", "main_B41", "eval_endpoint"),
    ]:
        result[label] = [
            g
            for line in gzip.open(ROOT / f"results/{folder}/games.jsonl.gz", "rt")
            if (g := json.loads(line))["kind"] == kind
        ]
    return result


def main():
    config_path = ROOT / "experiments/visible_budget.json"
    if config_path.exists():
        raise RuntimeError(
            "Follow-up already frozen; do not rewrite its configuration or price."
        )
    source = json.loads((ROOT / "experiments/main_B41.json").read_text())
    config = {
        key: source[key]
        for key in [
            "primary_model",
            "primary_output_cap",
            "primary_thinking",
            "reference_model",
            "reference_output_cap",
            "reference_reasoning_effort",
            "reference_template_date",
            "temperature",
            "top_p",
            "top_k",
            "context_window",
            "cost_source",
            "rendering_proof",
            "active_models",
            "grammar_version",
            "posterior_threshold",
            "sdk_version",
            "cookbook_pin",
            "reward",
        ]
    }
    policies = [
        {"name": "Raw", "snapshot_key": 0, "training_updates": 0, "model_path": None}
    ]
    for key, label in [(23, "A23"), (41, "B41")]:
        checkpoint = json.loads(
            (ROOT / f"results/main_{label}/completion.json").read_text()
        )["checkpoints"]["30"]["sampler"]
        assert checkpoint["expires_at"] is None and checkpoint["size_bytes"] > 0
        policies.append(
            {
                "name": label,
                "snapshot_key": key,
                "training_updates": 30,
                "model_path": checkpoint["tinker_path"],
                "checkpoint_evidence": f"results/main_{label}/completion.json",
            }
        )
    config.update(
        run_id="visible-budget-v1",
        approval_date="2026-11-19",
        display_name="Twenty Bits visible-budget eval only",
        approved_cap_usd="50.000000",
        run_cap_usd="8.000000",
        ledger_phase=5,
        prompt_version=PROMPT_VERSION,
        sampling_seed_namespace="main-U-v1/evaluation",
        training_authorized=False,
        rl_training_authorized=False,
        eval_only=True,
        is_primary_result=False,
        concurrent_games=16,
        policies=policies,
        skipped_policies={
            "A11": "not run: A11 checkpoint wasn't persisted, external uploads unavailable"
        },
        primary_games_per_cell=28,
        stage_gate="Stop after visible-budget follow-up; no training or write-up phase continuation.",
    )
    records = json.loads(
        gzip.decompress((ROOT / "experiments/main_B41_games.json.gz").read_bytes())
    )["evaluation"]
    by_id = {r["id"]: r for r in records}
    assert len(by_id) == 280
    encoded = (
        json.dumps(records, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    path = ROOT / "experiments/visible_budget_games.json.gz"
    path.write_bytes(gzip.compress(encoded, mtime=0))
    rendering = Rendering(config["primary_model"], config)
    initial = []
    for record in records:
        public = visible_budget_messages(record)
        ids = rendering.prompt(public).to_ints()
        assert public[0] == candidate_messages(record)[0]
        initial.append(
            {
                "game_id": record["id"],
                "tokens": len(ids),
                "visible_budget_tokens_sha256": token_hash(ids),
                "primary_tokens_sha256": token_hash(
                    rendering.prompt(candidate_messages(record)).to_ints()
                ),
            }
        )
    save_json(
        ROOT / "evals/visible_budget/prompt_hashes.json",
        {
            "prompt_version": PROMPT_VERSION,
            "games": initial,
            "dynamic_hashes": "results/visible_budget/prompt_hashes.json.gz after collection",
            "old_hashes_untouched": True,
        },
    )
    cohorts = primary_games()
    rate = rates(config["primary_model"])
    observed_cache = min(
        sum(g["prompt_cache_hit_tokens"] for g in gs)
        / sum(g["prompt_tokens"] for g in gs)
        for gs in cohorts.values()
    )
    credit = min(Decimal("0.70"), Decimal(str(observed_cache)))
    cells = []
    for policy, gs in cohorts.items():
        groups = defaultdict(
            lambda: {
                "games": 0,
                "turns": 0,
                "primary_prompt_tokens": 0,
                "amended_prompt_tokens": 0,
                "output_tokens": 0,
            }
        )
        for index, game in enumerate(gs):
            record = by_id[game["game_id"]]
            cell = groups[(game["domain"], game["n"], game["noise"])]
            cell["games"] += 1
            for i, turn in enumerate(game["turns"]):
                before = game["turns"][:i]
                primary_ids = rendering.prompt(
                    candidate_messages(record, before)
                ).to_ints()
                assert primary_ids == game["trajectory"][i]["ob"]
                ids = rendering.prompt(
                    visible_budget_messages(record, before)
                ).to_ints()
                cell["turns"] += 1
                cell["primary_prompt_tokens"] += len(primary_ids)
                cell["amended_prompt_tokens"] += len(ids)
                cell["output_tokens"] += len(game["trajectory"][i]["tokens"])
            if (index + 1) % 70 == 0:
                print(f"Offline token replay {policy}: {index + 1}/280", flush=True)
        for (domain, n, noise), cell in sorted(groups.items()):
            p, o = cell["amended_prompt_tokens"], cell["output_tokens"]
            estimated = (
                Decimal(p)
                * ((1 - credit) * rate["prefill"] + credit * rate["cached_prefill"])
                + Decimal(o) * rate["sample"]
            ) / 1000000
            uncached = (
                Decimal(p) * rate["prefill"] + Decimal(o) * rate["sample"]
            ) / 1000000
            cells.append(
                {
                    "policy": policy,
                    "domain": domain,
                    "n": n,
                    "noise": noise,
                    **cell,
                    "estimated_usd": str(estimated),
                    "uncached_usd": str(uncached),
                }
            )
    amount = sum(Decimal(c["estimated_usd"]) for c in cells)
    forecast = money(amount * Decimal("1.15") * Decimal("1.5"))
    budget = Ledger(ROOT / "ledger.json").summary()
    result = {
        "date": "2026-11-19",
        "eval_only": True,
        "new_training_games": 0,
        "policies": policies,
        "skipped_policies": config["skipped_policies"],
        "games_per_policy": 280,
        "total_games": 840,
        "cells_per_policy": 10,
        "observed_minimum_cohort_cache_fraction": observed_cache,
        "forecast_cache_fraction": str(credit),
        "measured_trajectory_replay_usd": str(amount),
        "behaviour_allowance_multiplier": "1.15",
        "reservation_margin_multiplier": "1.5",
        "forecast_including_margin_usd": str(forecast),
        "uncached_replay_usd": str(sum(Decimal(c["uncached_usd"]) for c in cells)),
        "new_storage_holds_usd": "0.000000",
        "existing_holds_remain_usd": budget["held_usd"],
        "project_budget_before": budget,
        "followup_cap_including_holds_usd": "8.000000",
        "fits": forecast <= Decimal("8")
        and forecast <= Decimal(budget["available_usd"]),
        "method": "Replay all saved primary actions with the real native tokenizer and the added counters. Retain measured generated token lengths, credit at most 70% cached input versus the observed minimum cohort, add 15% behavior allowance, then 1.5 margin. No new checkpoint saves. Per-call full-cap reservations, the aggregate follow-up $8 guard and the project $50 guard still apply.",
        "limitations": "Action trajectories can change. Cache hits are not guaranteed; the uncached replay exceeds this follow-up cap. Stop rather than exceed either cap if measured behavior or cache misses use the allowance.",
        "cells": cells,
    }
    save_json(ROOT / "research/visible_budget_forecast.json", result)
    save_json(config_path, config)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("cells", "policies")},
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
