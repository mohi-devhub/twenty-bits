"""Measure candidate-feedback prompts and freeze paired inference settings offline."""

from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.baselines import play
from twenty_bits.candidate_feedback import (
    POSTERIOR_THRESHOLD,
    PROMPT_VERSION,
    candidate_messages,
    feedback,
    token_hash,
)
from twenty_bits.learnability import probe_messages
from twenty_bits.supervised import qualification_records
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import sample_cost, save_json
from twenty_bits.worlds import ROOT, load_split


def freeze(path, value):
    if path.exists() and json.loads(path.read_text()) != value:
        raise RuntimeError(f"Prepared artifact already differs: {path.name}")
    if not path.exists():
        save_json(path, value)


def main():
    source_path = ROOT / "results/format_sft/completion.json"
    source = json.loads(source_path.read_text())
    records_path = ROOT / "experiments/format_qualification_games.json"
    records = json.loads(records_path.read_text())
    assert records == qualification_records()
    train = set(load_split()["train"])
    assert all(set(r["world"]["names"]) <= train for r in records)
    common = json.loads((ROOT / "experiments/alias_probe.json").read_text())
    common.pop("decision_rule", None)
    common.update(
        run_cap_usd="0.250000",
        training_authorized=False,
        rl_training_authorized=False,
        evaluation_kind="candidate_set_qualification",
        primary_games_per_cell=16,
        prompt_version=PROMPT_VERSION,
        sizes=[4, 8],
        remaining_candidate_feedback=True,
        posterior_threshold=POSTERIOR_THRESHOLD,
        sampling_seed_namespace="format-qualification-policy-v1",
        qualification={"valid_turn_rate_minimum": 0.9, "wins_minimum": 8, "games": 32},
        checkpoint_source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    )
    rendering = Rendering(common["primary_model"], common)
    histories = []
    checks = []
    source_games = [
        json.loads(line)
        for line in gzip.open(ROOT / "results/format_sft/games.jsonl.gz", "rt")
    ]
    by_id = {r["id"]: r for r in records}
    replay_forecast = Decimal(0)
    for g in source_games:
        r = by_id[g["game_id"]]
        for i, turn in enumerate(g["turns"]):
            public = candidate_messages(r, g["turns"][:i])
            count = rendering.prompt(public).length
            histories.append({"id": r["id"], "turn": i, "prompt_tokens": count})
            replay_forecast += Decimal(
                sample_cost(
                    common["primary_model"], count, turn["usage"]["output_tokens"]
                )
            )
    for r in records:
        ids = rendering.prompt(candidate_messages(r)).to_ints()
        checks.append({"id": r["id"], "tokens": len(ids), "sha256": token_hash(ids)})
    implementations = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in (
            "twenty_bits/candidate_feedback.py",
            "twenty_bits/learnability.py",
            "twenty_bits/game.py",
            "twenty_bits/predicates.py",
            "twenty_bits/attributes.py",
            "twenty_bits/tinker_transport.py",
            "twenty_bits/tinker_rendering.py",
            "twenty_bits/model_player.py",
            "scripts/run_learnability_probe.py",
            "scripts/run_candidate_qualification.py",
        )
    }
    maximum_call = Decimal(
        sample_cost(
            common["primary_model"],
            common["context_window"] - common["primary_output_cap"],
            common["primary_output_cap"],
        )
    )
    full_envelope = sum(
        (Decimal(2 * (r["n"] - 1).bit_length() + 1) * maximum_call for r in records),
        Decimal(0),
    )
    for policy in ("format_sft", "raw_base"):
        config = {
            **common,
            "run_id": "candidate-set-v1-" + policy,
            "policy": policy,
            "sampling_checkpoint_paths": {
                common["primary_model"]: source["checkpoints"]["native"]["path"]
            }
            if policy == "format_sft"
            else {},
            "display_name": "Twenty Bits candidate set " + policy,
        }
        path = ROOT / f"experiments/candidate_set_{policy}.json"
        freeze(path, config)
        proof = {
            "config_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "games_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
            "prompt_code_sha256": implementations["twenty_bits/learnability.py"],
            "implementation_sha256": implementations,
            "native_initial_checks": checks,
            "native_history_checks": len(histories),
            "forecast_usd": str(replay_forecast),
            "forecast_basis": "Replay the prior SFT qualification's actual actions and output counts with new candidate-set input tokens, no cache credit. Raw-base behavior remains uncertain.",
            "full_cap_hold_envelope_usd": str(full_envelope),
            "full_cap_envelope_note": "Uncached per-call context/output-cap bound times every allowed action. Admission is limited to the policy cap; per-call holds enforce it. Maximum-length trajectories need not all fit.",
            "per_policy_cap_including_holds_usd": "0.250000",
            "combined_cap_including_holds_usd": "0.500000",
            "rl_updates_authorized": 0,
            "service_calls": 0,
        }
        freeze(ROOT / f"research/candidate_set_{policy}_rendering.json", proof)
    manifest = json.loads((ROOT / "evals/frozen/manifest.json").read_text())
    hashes, cell_counts = {}, []
    trace_rows = []
    for cell in manifest["cells"]:
        path = ROOT / "evals/frozen" / cell["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == cell["sha256"]
        frozen = [json.loads(line) for line in gzip.open(path, "rt")]
        counts = []
        for r in frozen:
            ids = rendering.prompt(candidate_messages(r)).to_ints()
            hard_ids = rendering.prompt(probe_messages(r)).to_ints()
            hashes[r["id"]] = {
                "main_initial_tokens_sha256": token_hash(ids),
                "hard_initial_tokens_sha256": token_hash(hard_ids),
                "main_initial_tokens": len(ids),
                "hard_initial_tokens": len(hard_ids),
            }
            counts.append(len(ids))
        cell_counts.append(
            {
                "domain": cell["domain"],
                "n": cell["n"],
                "noise": cell["noise"],
                "games": len(frozen),
                "initial_prompt_tokens_mean": float(np.mean(counts)),
                "initial_prompt_tokens_max": max(counts),
            }
        )
        # Fixed examples of shrinking per-answer lists; not policy cost predictions.
        for r in frozen[:2]:
            for kind in ("random", "greedy_predicate"):
                g = play(r, kind, keep_trace=True)
                for i in range(len(g["turns"])):
                    public = candidate_messages(r, g["turns"][:i])
                    main_count = rendering.prompt(public).length
                    hard_count = rendering.prompt(
                        probe_messages(r, g["turns"][:i])
                    ).length
                    state = (
                        feedback(r, g["turns"][i - 1]["posterior_after"]) if i else None
                    )
                    trace_rows.append(
                        {
                            "game_id": r["id"],
                            "policy": kind,
                            "turn": i,
                            "n": r["n"],
                            "noise": r["noise"],
                            "domain": r["domain"],
                            "prompt_tokens": main_count,
                            "no_list_tokens": hard_count,
                            "feedback_candidates": len(state["candidates"])
                            if state
                            else r["n"],
                            "latest_feedback_tokens": len(
                                rendering.tokenizer.encode(
                                    public[-1]["content"].split("\n", 1)[1],
                                    add_special_tokens=False,
                                )
                            )
                            if i
                            else 0,
                        }
                    )
    freeze(
        ROOT / "evals/candidate_set/prompt_hashes.json",
        {
            "version": PROMPT_VERSION,
            "hash_encoding": "SHA-256 of compact JSON array of native generation-prefix token IDs",
            "old_phase2_hashes": "evals/frozen/prompt_hashes.json",
            "feedback_threshold": POSTERIOR_THRESHOLD,
            "hashes": hashes,
        },
    )
    freeze(
        ROOT / "evals/hard_mode.json",
        {
            "mode": "no_candidate_list",
            "message_builder": "twenty_bits.learnability.probe_messages",
            "grammar_version": "attribute-codes-v2",
            "train_on_this_mode": False,
            "models": ["raw_base", "final_rl_endpoint"],
            "indices_per_cell": [0, 1],
            "cells": 10,
            "games_per_model": 20,
            "sampling_authorized_now": False,
            "interpretation": "Descriptive pipeline comparison; raw base versus final includes SFT. Use the matched pre-RL SFT control for isolated RL comparisons in the main condition.",
        },
    )
    result = {
        "version": PROMPT_VERSION,
        "service_calls": 0,
        "native_initial_frozen_prompts_verified": len(hashes),
        "native_training_pool_histories_verified": len(histories),
        "old_sft_actions_new_context_forecast_usd_per_policy": str(replay_forecast),
        "frozen_cells": cell_counts,
        "baseline_trace_tokens": trace_rows,
        "history_note": "Each new list shrinks in noiseless play, but old lists remain in the conversation. Total prompt length grows with history. No history was dropped.",
    }
    freeze(ROOT / "research/candidate_set_tokens.json", result)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "baseline_trace_tokens"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
