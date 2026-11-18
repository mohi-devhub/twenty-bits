"""Freeze the auxiliary diagnostic without changing any primary artifact."""

from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger
from twenty_bits.candidate_feedback import candidate_messages, token_hash
from twenty_bits.suffix_diagnostic import SuffixDiagnosticGame
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import rates, save_json
from twenty_bits.worlds import ROOT


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old = json.loads((ROOT / "experiments/main_A11.json").read_text())
    source = json.loads((ROOT / "results/main_A11/completion.json").read_text())
    path = ROOT / "experiments/A11_suffix_diagnostic.json"
    config = json.loads(path.read_text())
    config.update(
        source_adapter_files=source["adapter_files"],
        source_checkpoint=source["external"]["path"],
        source_primary_config_sha256=digest(ROOT / "experiments/main_A11.json"),
        sampling_checkpoint_paths={},
    )
    save_json(path, config)
    for field in (
        "primary_model",
        "primary_output_cap",
        "primary_thinking",
        "temperature",
        "top_p",
        "top_k",
        "context_window",
        "reward",
        "lora",
        "grammar_version",
        "observation_mode",
        "posterior_threshold",
        "prompt_version",
    ):
        assert config[field] == old[field], field
    assert not config["is_primary_result"] and not config["rl_training_authorized"]
    manifest = json.loads(
        gzip.decompress((ROOT / "experiments/main_A11_games.json.gz").read_bytes())
    )
    records = [r for r in manifest["evaluation"] if r["domain"] == "synthetic"]
    assert len(records) == 168
    data = json.dumps(records, indent=2).encode() + b"\n"
    data_path = ROOT / "experiments/A11_suffix_diagnostic_games.json"
    data_path.write_bytes(data)
    data_path.with_suffix(".json.gz").write_bytes(gzip.compress(data, mtime=0))
    rendering = Rendering(config["primary_model"], config)
    hashes = json.loads((ROOT / "evals/candidate_set/prompt_hashes.json").read_text())[
        "hashes"
    ]
    prompts = []
    for r in records:
        ids = rendering.prompt(candidate_messages(r)).to_ints()
        assert token_hash(ids) == hashes[r["id"]]["main_initial_tokens_sha256"]
        prompts.append({"id": r["id"], "tokens": len(ids), "sha256": token_hash(ids)})
        game = SuffixDiagnosticGame(r)
        assert len(game.aliases.extra) > 0
    summary = json.loads((ROOT / "results/main_A11/summary.json").read_text())
    cells = [
        r for r in summary["frozen_evaluation"]["cells"] if r["domain"] == "synthetic"
    ]
    observed = sum(Decimal(r["endpoint"]["actual_usage_cost_usd"]) for r in cells)
    rate = rates(config["primary_model"])
    reference = sum(
        Decimal(r["endpoint"]["prompt_tokens"])
        * (Decimal(".3") * rate["prefill"] + Decimal(".7") * rate["cached_prefill"])
        / 1_000_000
        + Decimal(r["endpoint"]["output_tokens"]) * rate["sample"] / 1_000_000
        for r in cells
    )
    ledger = Ledger(ROOT / "ledger.json")
    status = ledger.status()
    future = Decimal(
        str(
            json.loads(
                (ROOT / "research/main_A11_remaining_forecast.json").read_text()
            )["total_with_1_5_margin_usd"]
        )
    )
    assert Decimal(status["available_usd"]) >= Decimal("1.5") + future
    assert (reference + Decimal(".05")) * Decimal("1.5") < Decimal("1.5")
    files = (
        "scripts/run_suffix_diagnostic.py",
        "twenty_bits/suffix_diagnostic.py",
        "twenty_bits/endpoint_restore.py",
        "twenty_bits/model_player.py",
        "twenty_bits/game.py",
        "twenty_bits/predicates.py",
        "twenty_bits/recovery.py",
        "twenty_bits/rl_pilot.py",
        "twenty_bits/tinker_transport.py",
        "twenty_bits/tinker_rendering.py",
        "twenty_bits/candidate_feedback.py",
    )
    save_json(
        ROOT / "research/A11_suffix_diagnostic_preflight.json",
        {
            "diagnostic_only": True,
            "is_primary_result": False,
            "config_sha256": digest(path),
            "games_sha256": hashlib.sha256(data).hexdigest(),
            "source_adapter_files": source["adapter_files"],
            "implementation_sha256": {name: digest(ROOT / name) for name in files},
            "native_prompt_parity": prompts,
            "games": 168,
            "cells": 6,
            "games_per_cell": 28,
            "sampling_seed_namespace": "main-U-v1/evaluation",
            "observed_A11_primary_sampling_usd": str(observed),
            "observed_cost_plus_restore_with_margin_usd": str(
                (observed + Decimal(".05")) * Decimal("1.5")
            ),
            "same_tokens_at_70_percent_cache_plus_restore_with_margin_usd": str(
                (reference + Decimal(".05")) * Decimal("1.5")
            ),
            "cap_including_holds_usd": "1.500000",
            "remaining_U_with_margin_usd": str(future),
            "global_budget_before_sampling": {
                k: v for k, v in status.items() if k != "entries"
            },
            "mapping_rule": "Only an exact active table code plus underscore plus suffix is considered. Preserve existing names/codes; require exactly one real attribute matching a single-letter prefix plus the identical suffix. Case sensitive; item names/guesses are literal.",
            "method": "Fresh A11 endpoint rollouts. Same frozen cases, requested seeds, prompts, caps and settings. Only predicate interpretation changes; later answers and public candidate lists follow the changed trajectory. Never rescore a primary trajectory or use this parser in primary evaluation/training.",
            "cost_limits": "Cost forecast uses measured primary trajectory tokens, observed cache behavior and a separate 70% cache reference. Parser changes may alter lengths. Each call still reserves its full token maximum and the $1.50 run cap stops unaffordable work.",
            "training_or_optimizer_calls_permitted": 0,
        },
    )
    print(
        json.dumps(
            {
                "games": 168,
                "native_prompts_verified": len(prompts),
                "forecast_with_margin": str(
                    (observed + Decimal(".05")) * Decimal("1.5")
                ),
                "cache_reference_with_margin": str(
                    (reference + Decimal(".05")) * Decimal("1.5")
                ),
                "cap": "1.50",
            }
        )
    )


if __name__ == "__main__":
    main()
