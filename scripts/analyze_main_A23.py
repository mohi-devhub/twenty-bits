"""Replay the A23 primary run; reuse its matched raw control from A11 archives."""

from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.analyze_main_seed import write_gzip, transfer_identifier_audit, paired_change, audit, stopping_confidence
from scripts.audit_qualification import audit as consistency_audit
from scripts.run_baselines import summarize
from scripts.run_main_A23 import metrics as game_metrics
from scripts.analyze_main_evaluation import frozen_comparison
from twenty_bits.guess_metrics import guess_state
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.game import Game
from twenty_bits.rl_pilot import group_data, unpack_trajectory
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import rates, sample_cost, save_json
from twenty_bits.worlds import ROOT, seed_for
from twenty_bits.name_reference_audit import audit_name_references

def main():
    out = ROOT / "results/main_A23"
    config = json.loads((ROOT / "experiments/main_A23.json").read_text())
    manifest_path = ROOT / "experiments/main_A23_games.json"
    manifest_bytes = (
        manifest_path.read_bytes()
        if manifest_path.exists()
        else gzip.decompress((ROOT / "experiments/main_A23_games.json.gz").read_bytes())
    )
    assert (
        hashlib.sha256(manifest_bytes).hexdigest()
        == json.loads((ROOT / "research/main_A23_preflight.json").read_text())[
            "games_sha256"
        ]
    )
    manifest = json.loads(manifest_bytes)
    completion = json.loads((out / "primary_completion.json").read_text())
    directory = ROOT / "runs" / config["run_id"]
    session_archive = out / "sessions.json"
    if not session_archive.exists():
        session = json.loads((directory / "sessions.json").read_text())
        assert session["finished"]
        save_json(session_archive, session)
    paths = sorted((directory / "games").glob("*.json"))
    games = (
        [json.loads(p.read_text()) for p in paths]
        if paths
        else [json.loads(line) for line in gzip.open(out / "games.jsonl.gz", "rt")]
    )
    games.sort(
        key=lambda g: (g["kind"], g["update"], g["game_id"], g.get("member") or 0)
    )
    req_paths = sorted((directory / "requests").glob("*.json"))
    requests = (
        [json.loads(p.read_text()) for p in req_paths]
        if req_paths
        else [json.loads(line) for line in gzip.open(out / "requests.jsonl.gz", "rt")]
    )
    excluded = [
        r for r in requests if r.get("orphaned") or r.get("output_allowed") is False
    ]
    requests = [r for r in requests if r not in excluded]
    if not req_paths and (out / "excluded_originals.jsonl.gz").exists():
        excluded = [
            json.loads(line)
            for line in gzip.open(out / "excluded_originals.jsonl.gz", "rt")
        ]
    registry = json.loads((ROOT / "research/main_A23_replacements.json").read_text())
    aliases = {c["logical_key"]: c["replacement_key"] for c in registry["cases"]}
    if not req_paths:
        responses = {
            r["entry_id"]: r["response"]
            for line in gzip.open(out / "responses.jsonl.gz", "rt")
            if (r := json.loads(line))
        }
        for r in requests:
            r["response"] = responses[r["entry_id"]]
    by_entry = {r["entry_id"]: r for r in requests}
    records = {r["record"]["id"]: r["record"] for r in manifest["training"]}
    records.update(
        {r["id"]: r for r in manifest["development"] + manifest["evaluation"]}
    )
    rendering = Rendering(config["primary_model"], config)
    used = set()
    for g in games:
        record = records[g["game_id"]]
        assert g["guess_state"] == guess_state(g, record)
        replay = Game(record, grammar_version=config["grammar_version"])
        overflow = (
            rendering.prompt(candidate_messages(record)).length + 2048
            > config["context_window"]
        )
        if overflow:
            replay.done = True
        expected_step = g["update"] - 1 if g["kind"] == "train" else g["update"]
        assert g["policy_step"] == expected_step
        assert len(g["turns"]) == len(g["trajectory"])
        for index, (turn, tape) in enumerate(zip(g["turns"], g["trajectory"])):
            ids = rendering.prompt(candidate_messages(record, replay.turns)).to_ints()
            assert tape["ob"] == ids
            usage = turn["usage"]
            request = by_entry[usage["entry_id"]]
            assert request["settled"] and request["request_id_saved_before_dispatch"]
            assert (
                request["request_id"]
                == request["receipt"]["request_id"]
                == usage["request_id"]
            )
            assert (
                request["request_id"].rsplit(":", 1)[0]
                == completion["snapshots"][str(expected_step)]["id"]
            )
            logical_key = (
                g["scope"]
                + config["primary_model"]
                + "/"
                + g["game_id"]
                + f"/turn-{index}"
            )
            assert request["key"] == aliases.get(logical_key, logical_key)
            params = request["parameters"]
            assert params["seed"] == seed_for(
                g["sampling_seed_namespace"], g["game_id"], index
            ) % (2**31)
            assert (
                params["max_tokens"] == 2048
                and params["temperature"] == 0.7
                and params["top_p"] == 1
                and params["top_k"] == -1
            )
            payload = {
                "model": config["primary_model"],
                "prompt_ids": ids,
                "sampling_params": params,
            }
            assert (
                hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                == request["signature"]
            )
            sequence = request["response"]["sequences"][0]
            assert (
                sequence["tokens"] == tape["tokens"]
                and sequence["logprobs"] == tape["logprobs"]
            )
            assert rendering.decode(sequence["tokens"])["action"] == turn["raw_action"]
            before = replay.reward
            reproduced = replay.step(
                turn["raw_action"],
                reasoning_tokens=turn["reasoning_tokens"],
                action_tokens=turn["action_tokens"],
                predicate_tokens=turn["predicate_tokens"],
                truncated=turn["truncated"],
            )
            for field in ("answer", "invalid", "enumeration", "is_question", "reask"):
                assert reproduced[field] == turn[field]
            assert abs(reproduced["eig"] - turn["eig"]) < 1e-12
            np.testing.assert_allclose(
                reproduced["posterior_after"],
                turn["posterior_after"],
                atol=1e-12,
                rtol=0,
            )
            assert abs(replay.reward - before - tape["reward"]) < 1e-12
            assert usage["actual_usd"] == sample_cost(
                config["primary_model"],
                len(ids),
                len(sequence["tokens"]),
                request["prompt_cache_hit_tokens"],
            )
            used.add(usage["entry_id"])
            if (
                not replay.done
                and rendering.prompt(candidate_messages(record, replay.turns)).length
                + 2048
                > config["context_window"]
            ):
                replay.done = True
                overflow = True
        assert overflow == g["context_overflow"]
        assert (
            replay.done
            and replay.won == g["won"]
            and abs(replay.reward - g["reward"]) < 1e-10
        )
    assert used == set(by_entry)
    assert not used & {r["entry_id"] for r in excluded}
    for case in registry["cases"]:
        original = next(
            r for r in excluded if r["entry_id"] == case["original_entry_id"]
        )
        replacement = by_entry[case["replacement_entry_id"]]
        assert original["signature"] == replacement["signature"] == case["signature"]
        assert (
            original["parameters"] == replacement["parameters"]
            and original["output_allowed"] is False
        )
    op_paths = sorted((directory / "operations").glob("*.json"))
    operations = (
        [json.loads(p.read_text()) for p in op_paths]
        if op_paths
        else [json.loads(line) for line in gzip.open(out / "operations.jsonl.gz", "rt")]
    )
    ops = {o["key"]: o for o in operations}
    curve = json.loads((out / "learning_curve.json").read_text())["updates"]
    for step in range(1, completion["updates"] + 1):
        gs = sorted(
            [g for g in games if g["kind"] == "train" and g["update"] == step],
            key=lambda g: g["member"],
        )
        assert len(gs) == 8 and len({g["game_id"] for g in gs}) == 1
        data, archive, returns, advantages = group_data(
            [unpack_trajectory(g["trajectory"]) for g in gs]
        )
        assert archive == json.loads(
            gzip.decompress((out / f"training-data-{step:02d}.json.gz").read_bytes())
        )
        op = ops[f"forward-{step:02d}"]
        assert op["payload"]["loss_fn"] == "importance_sampling"
        assert (
            op["payload"]["data_sha256"]
            == hashlib.sha256(json.dumps(archive, sort_keys=True).encode()).hexdigest()
        )
        tokens = sum(d.model_input.length for d in data)
        assert tokens == op["payload"]["tokens"] == curve[step - 1]["training_tokens"]
        np.testing.assert_allclose(
            returns, curve[step - 1]["returns"], atol=1e-12, rtol=0
        )
        np.testing.assert_allclose(
            advantages, curve[step - 1]["advantages"], atol=1e-12, rtol=0
        )
        assert curve[step - 1]["gradient_usd"] == op["actual_usd"]
        sampled = [
            np.asarray(row["loss_fn_inputs"]["logprobs"]["data"])[
                np.asarray(row["training_mask"], dtype=bool)
            ]
            for row in archive
        ]
        trained = (
            [
                np.asarray(output["logprobs"]["data"])[
                    np.asarray(row["training_mask"], dtype=bool)
                ]
                for output, row in zip(op["response"]["loss_fn_outputs"], archive)
            ]
            if "response" in op
            else [np.asarray(values) for values in op["action_logprobs"]]
        )
        assert len(trained) == len(sampled)
        differences = np.concatenate([t - p for t, p in zip(trained, sampled)])
        assert (
            abs(
                np.mean(differences)
                - curve[step - 1]["mean_train_minus_sample_logprob"]
            )
            < 1e-10
        )
        assert (
            abs(
                np.max(np.abs(differences))
                - curve[step - 1]["max_abs_train_minus_sample_logprob"]
            )
            < 1e-10
        )
        expected = (
            Decimal(tokens) * rates(config["primary_model"])["train"] / 1_000_000
        ).quantize(Decimal(".000001"), rounding="ROUND_CEILING")
        assert Decimal(op["actual_usd"]) == expected
    training = [g for g in games if g["kind"] == "train"]
    dev = {
        step: sorted(
            [g for g in games if g["kind"] == "dev" and g["update"] == step],
            key=lambda g: g["game_id"],
        )
        for step in config["development_checks"]
        if step <= completion["updates"]
    }
    dev[0] = [
        json.loads(line)
        for line in gzip.open(out / "development_base_games.jsonl.gz", "rt")
    ]
    dev = dict(sorted(dev.items()))
    assert len(training) == completion["training_games"]
    assert sum(len(gs) for k, gs in dev.items() if k) == completion["development_games"]
    raw_source = ROOT / "results/main_A11/games.jsonl.gz"
    assert hashlib.sha256(raw_source.read_bytes()).hexdigest() == manifest["raw_frozen_source_sha256"]
    raw_control = [json.loads(line) for line in gzip.open(raw_source, "rt") if json.loads(line)["kind"] == "eval_base"]
    assert len(raw_control) == 280
    evaluation = frozen_comparison(games + raw_control, manifest["evaluation"])
    status = Ledger(ROOT / "ledger.json").status()
    entries = [
        e for e in status["entries"] if e["operation"].startswith("[main-U-A23-v1] ")
    ]
    spent = sum(
        (Decimal(e["actual_usd"]) for e in entries if e["state"] == "settled"),
        Decimal(0),
    )
    held = sum(
        (Decimal(e["reserved_usd"]) for e in entries if e["state"] in ACTIVE_STATES),
        Decimal(0),
    )
    assert spent + held <= Decimal("42.49")
    assert Decimal(status["spent_usd"]) + Decimal(status["held_usd"]) <= Decimal("50")
    result = {
        "complete": True,
        "initial_policy": "raw_base_no_sft",
        "updates": curve,
        "development": {
            str(k): {"point": game_metrics(gs), "ci95": summarize(gs, bootstrap=10000)}
            for k, gs in dev.items()
        },
        "paired_development_final_minus_base": paired_change(dev[0], dev[max(dev)]),
        "frozen_evaluation": evaluation,
        "transfer_identifier_audit": transfer_identifier_audit(
            games + raw_control, records, evaluation
        ),
        "sampling_recovery": {
            "excluded_originals": len(excluded),
            "exact_replacements": len(registry["cases"]),
            "cases": [
                {
                    **c,
                    "original_hold_usd": str(
                        next(e for e in entries if e["id"] == c["original_entry_id"])[
                            "reserved_usd"
                        ]
                    ),
                }
                for c in registry["cases"]
            ],
            "original_outputs_used": 0,
        },
        "training_audit": audit(training),
        "raw_candidate_name_reference_audit": {
            "training": audit_name_references(training, records),
            "raw_frozen_control": audit_name_references(raw_control, records),
            "frozen_endpoint": audit_name_references([g for g in games if g["kind"]=="eval_endpoint"], records),
        },
        "development_audit": audit([g for gs in dev.values() for g in gs]),
        "base_development_audit": audit(dev[0]),
        "final_development_audit": audit(dev[max(dev)]),
        "guess_consistency_audit": {
            "training": consistency_audit(training, records),
            "base_dev": consistency_audit(dev[0], records),
            "final_dev": consistency_audit(dev[max(dev)], records),
        },
        "stopping_confidence_audit": {
            "training": stopping_confidence(training, records),
            "base_dev": stopping_confidence(dev[0], records),
            "final_dev": stopping_confidence(dev[max(dev)], records),
        },
        "group_signal_audit": {
            "nonconstant_return_groups": sum(
                r["reward_variance"] > 1e-12 for r in curve
            ),
            "groups": len(curve),
            "groups_with_win_variance": sum(r["win_variance"] > 1e-12 for r in curve),
            "zero_win_groups": [r["update"] for r in curve if r["wins"] == 0],
            "zero_win_groups_with_cost_only_variance": [
                r["update"]
                for r in curve
                if r["wins"] == 0 and r["reward_variance"] > 1e-12
            ],
        },
        "per_update_interpretation": "Training outcomes are on the policy before each update. Eight games share one hidden target and table. Curriculum changes at updates 3,5,16,23,27; fixed development cases, not raw training slopes alone, assess learning.",
        "uncertainty": "This summary covers A23 only. A11 versus A23 comparisons and the separate suffix/hard-mode data are in replication_summary.json. Development uses eight fixed cases; frozen cells use 28 paired games. B41 has not run.",
        "sample_train_logprob_diagnostic": {
            "mean_difference_range_nats": [
                min(r["mean_train_minus_sample_logprob"] for r in curve),
                max(r["mean_train_minus_sample_logprob"] for r in curve),
            ],
            "maximum_absolute_token_difference_nats": max(
                r["max_abs_train_minus_sample_logprob"] for r in curve
            ),
            "interpretation": "Native token sequences match exactly; training and sampling log probabilities are not bit-identical. The backend cause is not established. The standard importance-sampling loss uses the recorded rollout log probabilities; no correction or experiment setting changed.",
        },
        "cost": {
            "main_A23_spent_usd": str(spent),
            "main_A23_held_usd": str(held),
            "lost_original_holds_usd": str(
                sum(
                    (
                        Decimal(e["reserved_usd"])
                        for e in entries
                        if e["state"] in ACTIVE_STATES
                        and e["id"] in {r["entry_id"] for r in excluded}
                    ),
                    Decimal(0),
                )
            ),
            "checkpoint_holds_usd": str(
                sum(
                    (
                        Decimal(e["reserved_usd"])
                        for e in entries
                        if e["state"] in ACTIVE_STATES
                        and e["id"] not in {r["entry_id"] for r in excluded}
                    ),
                    Decimal(0),
                )
            ),
            "sampling_by_kind_usd": {
                kind: str(
                    sum(
                        (
                            Decimal(t["usage"]["actual_usd"])
                            for g in games
                            if g["kind"] == kind
                            for t in g["turns"]
                        ),
                        Decimal(0),
                    )
                )
                for kind in ("train", "dev", "eval_base", "eval_endpoint")
            },
            "gradient_usd": str(
                sum((Decimal(r["gradient_usd"]) for r in curve), Decimal(0))
            ),
            "token_usage_by_kind": {
                kind: {
                    key: sum(g[key] for g in games if g["kind"] == kind)
                    for key in (
                        "sampling_calls",
                        "prompt_tokens",
                        "output_tokens",
                        "prompt_cache_hit_tokens",
                    )
                }
                for kind in ("train", "dev", "eval_base", "eval_endpoint")
            },
            "cap_including_holds_usd": "42.490000",
            "project": {k: status[k] for k in status if k != "entries"},
        },
        "verification": {
            "sampled_games": len(games),
            "reused_raw_development_games": 8,
            "reused_raw_frozen_games": 280,
            "sampling_request_signatures_and_predispatch_ids": len(used),
            "gradient_batches_verified": completion["updates"],
            "outcome_rewards_only": True,
            "prompt_loss_tokens": 0,
            "frozen_games_in_gradients": 0,
        },
    }
    save_json(out / "summary.json", result)
    write_gzip(out / "games.jsonl.gz", games)
    write_gzip(
        out / "excluded_originals.jsonl.gz", sorted(excluded, key=lambda r: r["key"])
    )
    write_gzip(
        out / "requests.jsonl.gz",
        [
            {k: v for k, v in r.items() if k != "response"}
            for r in sorted(requests, key=lambda x: x["key"])
        ],
    )
    write_gzip(
        out / "responses.jsonl.gz",
        [
            {"entry_id": r["entry_id"], "response": r["response"]}
            for r in sorted(requests, key=lambda x: x["entry_id"])
        ],
    )
    compact = []
    for op in operations:
        row = {k: v for k, v in op.items() if k != "response"}
        if op["key"].startswith("forward-"):
            if "response" in op:
                step = int(op["key"].split("-")[1])
                archive = json.loads(
                    gzip.decompress(
                        (out / f"training-data-{step:02d}.json.gz").read_bytes()
                    )
                )
                row["response_sha256"] = hashlib.sha256(
                    json.dumps(op["response"], sort_keys=True).encode()
                ).hexdigest()
                row["reported_metrics"] = op["response"].get("metrics", {})
                row["action_logprobs"] = [
                    np.asarray(o["logprobs"]["data"])[
                        np.asarray(d["training_mask"], dtype=bool)
                    ].tolist()
                    for o, d in zip(op["response"]["loss_fn_outputs"], archive)
                ]
        else:
            row["response"] = op["response"]
        compact.append(row)
    write_gzip(out / "operations.jsonl.gz", sorted(compact, key=lambda o: o["key"]))
    pairs = []
    for identity in manifest["examples"]:
        pairs.append(
            {
                "game_id": identity,
                "record": records[identity],
                "base": next(g for g in dev[0] if g["game_id"] == identity),
                "final": next(g for g in dev[max(dev)] if g["game_id"] == identity),
                "selection": "Preselected before training; final scheduled development snapshot.",
            }
        )
    write_gzip(out / "example_games.jsonl.gz", pairs)
    print(
        json.dumps(
            {
                "cost": result["cost"],
                "development": {
                    k: v["point"] for k, v in result["development"].items()
                },
                "paired_change": result["paired_development_final_minus_base"],
                "verification": result["verification"],
            },
            indent=2,
        )
    )

if __name__ == "__main__":
    main()
