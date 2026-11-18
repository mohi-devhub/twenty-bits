"""Freeze the conditionally approved format SFT and its separate qualification set."""

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.supervised import qualification_records, supervised_data
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT, load_split


def main():
    decision_path = ROOT / "results/alias_probe/summary.json"
    decision = json.loads(decision_path.read_text())
    if (
        not decision["complete"]
        or decision["decision"] != "run_approved_sft_then_qualify"
    ):
        raise RuntimeError("The user's conditional SFT trigger is not satisfied.")
    config = json.loads((ROOT / "experiments/alias_probe.json").read_text())
    price = json.loads((ROOT / "research/format_warmstart_price.json").read_text())
    config.update(
        run_id="format-warmstart-v1",
        run_cap_usd="2.510000",
        training_authorized=True,
        rl_training_authorized=False,
        training_kind="format_sft",
        evaluation_kind="format_qualification",
        policy="format_sft",
        display_name="Twenty Bits conditional format warm start",
        training_data="experiments/format_warmstart_proposal.jsonl.gz",
        training_data_sha256=price["data_sha256"],
        examples=price["examples"],
        tokens_per_epoch=price["full_context_tokens_per_epoch"],
        epochs=2,
        batch_size=32,
        updates=36,
        lora={
            "rank": 32,
            "seed": 11,
            "train_mlp": True,
            "train_attn": True,
            "train_unembed": True,
        },
        adam={
            "learning_rate": 1e-4,
            "beta1": 0.9,
            "beta2": 0.95,
            "eps": 1e-12,
            "weight_decay": 0.0,
            "grad_clip_norm": 0.0,
        },
        shuffle_seed=11,
        checkpoint_ttl_seconds=7200,
        qualification={
            "valid_turn_rate_minimum": 0.90,
            "wins_minimum": 8,
            "games": 32,
            "sizes": [4, 8],
            "stop_before_rl": True,
        },
        sampling_seed_namespace="format-qualification-policy-v1",
        decision_source_sha256=hashlib.sha256(
            (ROOT / "results/alias_probe/games.jsonl.gz").read_bytes()
        ).hexdigest(),
    )
    config.pop("decision_rule", None)
    config_path = ROOT / "experiments/format_sft.json"
    if config_path.exists() and json.loads(config_path.read_text()) != config:
        raise RuntimeError("The warm-start config is already frozen.")
    save_json(config_path, config)
    data = supervised_data(config)
    records = qualification_records()
    train = set(load_split()["train"])
    rendering = Rendering(config["primary_model"], config)
    checks = []
    for record in records:
        assert set(record["world"]["names"]) <= train
        assert not set(record["world"]["names"]) & set(load_split()["held_out"])
        from twenty_bits.learnability import probe_messages

        checks.append(
            {
                "id": record["id"],
                "initial_prompt_tokens": rendering.prompt(
                    probe_messages(record)
                ).length,
            }
        )
    records_path = ROOT / "experiments/format_qualification_games.json"
    save_json(records_path, records)
    proof = {
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "data_sha256": price["data_sha256"],
        "qualification_games_sha256": hashlib.sha256(
            records_path.read_bytes()
        ).hexdigest(),
        "native_supervision_prefixes_verified": len(data),
        "trainable_prompt_tokens": 0,
        "cross_entropy_only": True,
        "service_calls": 0,
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "twenty_bits/supervised.py",
                "twenty_bits/predicates.py",
                "twenty_bits/attributes.py",
                "twenty_bits/game.py",
                "twenty_bits/learnability.py",
            )
        },
        "forecast_usd": "0.500000",
        "run_cap_usd": "2.510000",
        "qualification_checks": checks,
    }
    save_json(ROOT / "research/format_sft_rendering.json", proof)
    print(
        json.dumps(
            {k: v for k, v in proof.items() if k != "qualification_checks"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
