"""Replay probe results, check paid requests, and summarize complete cases offline."""

import argparse
from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.run_baselines import summarize
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.game import Game
from twenty_bits.learnability import probe_messages
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.worlds import ROOT, World, seed_for


def wilson(wins, total):
    z = 1.959963984540054
    p = wins / total
    middle = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = (
        z
        * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5)
        / (1 + z * z / total)
    )
    return [max(0, middle - half), min(1, middle + half)]


def main(
    partial=False,
    *,
    config_path=None,
    games_path=None,
    output_path=None,
    message_builder=probe_messages,
):
    config_path = config_path or ROOT / "experiments/learnability_probe.json"
    config = json.loads(config_path.read_text())
    records = json.loads(
        (games_path or ROOT / "experiments/learnability_probe_games.json").read_text()
    )
    records = {r["id"]: r for r in records}
    directory = ROOT / "runs" / config["run_id"]
    out = output_path or ROOT / "results/learnability_probe"
    out.mkdir(parents=True, exist_ok=True)
    paths = sorted((directory / "games").glob("*.json"))
    source = (
        [json.loads(p.read_text()) for p in paths]
        if paths
        else [json.loads(line) for line in gzip.open(out / "games.jsonl.gz", "rt")]
    )
    games = sorted(source, key=lambda g: g["game_id"])
    missing = sorted(set(records) - {g["game_id"] for g in games})
    if missing and not partial:
        raise RuntimeError(
            f"Probe incomplete: {len(missing)} games. Use --partial to label a partial summary."
        )
    requests = {
        r["entry_id"]: r
        for p in (directory / "requests").glob("*.json")
        if (r := json.loads(p.read_text())).get("entry_id")
    }
    if not requests:
        requests = {
            r["entry_id"]: r
            for line in gzip.open(out / "requests.jsonl.gz", "rt")
            if (r := json.loads(line))
        }
        for line in gzip.open(out / "responses.jsonl.gz", "rt"):
            row = json.loads(line)
            requests[row["entry_id"]]["response"] = row["response"]
    rendering = Rendering(config["primary_model"], config)
    used, valid_by_game = set(), {}
    for game in games:
        record = records[game["game_id"]]
        replay = Game(record, grammar_version=config.get("grammar_version", "names-v1"))
        valid = 0
        for index, turn in enumerate(game["turns"]):
            prompt = rendering.prompt(message_builder(record, replay.turns))
            usage = turn["usage"]
            request = requests[usage["entry_id"]]
            assert request.get("output_allowed") is not False and not request.get(
                "orphaned"
            )
            assert request["request_id_saved_before_dispatch"]
            assert (
                request["receipt"]["request_id"]
                == request["request_id"]
                == usage["request_id"]
            )
            assert request["prompt_tokens"] == prompt.length
            assert request["parameters"]["max_tokens"] == 2048
            for field in ("temperature", "top_p", "top_k"):
                assert request["parameters"][field] == config[field]
            assert (
                request["parameters"]["stop"] == rendering.renderer.get_stop_sequences()
            )
            assert request["parameters"]["seed"] == seed_for(
                config["sampling_seed_namespace"], record["id"], index
            ) % (2**31)
            payload = {
                "model": config["primary_model"],
                "prompt_ids": prompt.to_ints(),
                "sampling_params": request["parameters"],
            }
            assert (
                hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                == request["signature"]
            )
            decoded = rendering.decode(request["response"]["sequences"][0]["tokens"])
            assert decoded["action"] == turn["raw_action"]
            assert decoded["reasoning_tokens"] == turn["reasoning_tokens"]
            reproduced = replay.step(
                turn["raw_action"],
                reasoning_tokens=turn["reasoning_tokens"],
                action_tokens=turn["action_tokens"],
                predicate_tokens=turn["predicate_tokens"],
                truncated=turn["truncated"],
            )
            for field in ("answer", "invalid", "is_question", "enumeration"):
                assert reproduced[field] == turn[field]
            np.testing.assert_allclose(
                reproduced["posterior_after"],
                turn["posterior_after"],
                atol=1e-12,
                rtol=0,
            )
            assert abs(reproduced["eig"] - turn["eig"]) < 1e-12
            valid += int(
                (turn["is_question"] and not turn["invalid"])
                or (
                    turn["action"].startswith("GUESS: ")
                    and turn["action"][7:].strip() in replay.world.names
                    and "\n" not in turn["action"]
                )
            )
            used.add(usage["entry_id"])
        assert (
            replay.done
            and replay.won == game["won"]
            and replay.questions == game["questions"]
        )
        valid_by_game[game["game_id"]] = valid
    cells = []
    for n in sorted({r["n"] for r in records.values()}):
        gs = [g for g in games if g["n"] == n]
        if not gs:
            continue
        metrics = summarize(gs, bootstrap=10000)
        turns = [t for g in gs for t in g["turns"]]
        cost = sum((Decimal(t["usage"]["actual_usd"]) for t in turns), Decimal(0))
        valid = sum(valid_by_game[g["game_id"]] for g in gs)
        outcome_counts = Counter(
            "valid_ASK"
            if t["is_question"] and not t["invalid"]
            else "valid_GUESS"
            if t["action"].startswith("GUESS: ")
            and t["action"][7:].strip()
            in World.from_dict(records[g["game_id"]]["world"]).names
            else "INVALID"
            if t["invalid"]
            else "other"
            for g in gs
            for t in g["turns"]
        )
        errors = Counter(t.get("error", "") for t in turns if t["invalid"])
        per_game_cost = np.array(
            [sum(float(t["usage"]["actual_usd"]) for t in g["turns"]) for g in gs]
        )
        sample = np.random.default_rng(3901).integers(0, len(gs), (10000, len(gs)))
        vc = np.array([valid_by_game[g["game_id"]] for g in gs])
        tc = np.array([len(g["turns"]) for g in gs])
        cell = {
            "n": n,
            "noise": 0,
            "games": len(gs),
            "expected_games": 16,
            "wins": sum(g["won"] for g in gs),
            "win_rate": float(np.mean([g["won"] for g in gs])),
            "win_wilson_ci95": wilson(sum(g["won"] for g in gs), len(gs)),
            "valid_turns": valid,
            "turns": len(turns),
            "valid_turn_rate": valid / len(turns),
            "valid_turn_ci95_game_bootstrap": np.quantile(
                vc[sample].sum(axis=1) / tc[sample].sum(axis=1), [0.025, 0.975]
            ).tolist(),
            "outcomes": dict(outcome_counts),
            "parse_errors": dict(errors),
            "actual_usd_complete_games": str(cost),
            "cost_per_complete_game_usd": float(cost / len(gs)),
            "cost_per_game_ci95": np.quantile(
                per_game_cost[sample].mean(axis=1), [0.025, 0.975]
            ).tolist(),
            "prompt_tokens": sum(g["prompt_tokens"] for g in gs),
            "output_tokens": sum(g["output_tokens"] for g in gs),
            "prompt_cache_hit_tokens": sum(g["prompt_cache_hit_tokens"] for g in gs),
            "reasoning_tokens": sum(g["reasoning_tokens"] for g in gs),
            "mean_calls_per_game": len(turns) / len(gs),
            "mean_output_tokens_per_call": sum(g["output_tokens"] for g in gs)
            / len(turns),
            "format_error_rate": sum(g["format_error_count"] for g in gs) / len(turns),
            "truncation_rate": sum(g["truncation_count"] for g in gs) / len(turns),
            "metrics": metrics,
        }
        cells.append(cell)
    status = Ledger(ROOT / "ledger.json").status()
    run_entries = [
        e
        for e in status["entries"]
        if e["operation"].startswith(f"[{config['run_id']}] ")
    ]
    run_spent = sum(
        (Decimal(e["actual_usd"]) for e in run_entries if e["state"] == "settled"),
        Decimal(0),
    )
    run_held = sum(
        (
            Decimal(e["reserved_usd"])
            for e in run_entries
            if e["state"] in ACTIVE_STATES
        ),
        Decimal(0),
    )
    assert run_spent + run_held <= Decimal(config["run_cap_usd"])
    known_total = sum(
        (Decimal(r["actual_usd"]) for r in requests.values() if r.get("settled")),
        Decimal(0),
    )
    operations = []
    if config.get("training_kind") == "format_sft":
        operation_paths = sorted((directory / "operations").glob("*.json"))
        if operation_paths:
            operations = [json.loads(p.read_text()) for p in operation_paths]
        else:
            operations = [
                json.loads(line)
                for line in gzip.open(out / "operations.jsonl.gz", "rt")
            ]
        known_total += sum(
            (Decimal(op["actual_usd"]) for op in operations if op.get("settled")),
            Decimal(0),
        )
        for op in operations:
            assert op["completed"]
            if op["key"].startswith("forward-"):
                assert op["payload"]["loss_fn"] == "cross_entropy"
                assert op["payload"]["dataset_sha256"] == config["training_data_sha256"]
    assert known_total == run_spent
    ledger_entries = {e["id"]: e for e in run_entries}
    for request in requests.values():
        assert request["request_id_saved_before_dispatch"]
        assert request.get("saved_before_dispatch_at")
        assert (
            ledger_entries[request["entry_id"]]["request_id"] == request["request_id"]
        )
        if request.get("receipt"):
            assert request["receipt"]["request_id"] == request["request_id"]
    for entry in run_entries:
        operation = entry["operation"].split("] ", 1)[1]
        allowed_metadata = operation in {
            "construct low-level SDK client",
            "server capabilities",
            "create Phase 2 session",
            "session heartbeat",
            "finish Phase 2 session",
            "close SDK transport",
        } or operation.startswith(
            ("create sampler ", "retrieve ", "inspect saved future ")
        )
        if config.get("training_kind") == "format_sft":
            allowed_metadata |= (
                operation == "external weight download URLs"
                or operation.startswith(("SFT ", "download adapter file "))
            )
        assert allowed_metadata or operation.startswith("sample Qwen/Qwen3-8B ")
    incident_name = config.get(
        "incident_record", "research/learnability_probe_incident.json"
    )
    incident = (
        json.loads((ROOT / incident_name).read_text())
        if incident_name
        else {"approved_replacements": {}}
    )
    by_key = {r["key"]: r for r in requests.values()}
    for old_key, new_key in incident["approved_replacements"].items():
        original, replacement = by_key[old_key], by_key[new_key]
        assert original["orphaned"] and original["output_allowed"] is False
        assert original["entry_id"] not in used
        assert original["signature"] == replacement["signature"]
        assert replacement["settled"] and replacement["entry_id"] in used
    assert used <= {e["id"] for e in run_entries if e["state"] == "settled"}
    result = {
        "sampling_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "complete": not missing,
        "missing_games": missing,
        "games": len(games),
        "cells": cells,
        "cost": {
            "probe_spent_usd": str(run_spent),
            "probe_held_usd": str(run_held),
            "probe_cap_usd": config["run_cap_usd"],
            "project": {k: status[k] for k in status if k != "entries"},
        },
        "verification": {
            "replayed_turns": len(used),
            "used_entry_ids": sorted(used),
            "orphan_or_unavailable_outputs_used": 0,
            "training_operations": sum(
                op["key"].startswith("forward-") for op in operations
            ),
            "pre_dispatch_ids_verified": len(used),
            "all_attempts_with_pre_dispatch_ids_verified": len(requests),
            "native_rendering_and_request_signatures_verified": len(used),
            "exact_replacement_signatures_verified": len(
                incident["approved_replacements"]
            ),
        },
        "interpretation": "Training-pool development probe, noiseless only, no remaining-candidate feedback. Prompt and size differ from Phase 2, so this is not an isolated prompt treatment effect. Intervals resample complete games; missing games are listed and not scored as losses or wins.",
    }
    if config.get("grammar_version") == "attribute-codes-v2":
        valid = sum(c["valid_turns"] for c in cells)
        total = sum(c["turns"] for c in cells)
        n8_wins = sum(g["won"] for g in games if g["n"] == 8)
        result.update(
            grammar_version=config["grammar_version"],
            pooled_valid_turns=valid,
            pooled_turns=total,
            pooled_valid_turn_rate=valid / total,
            decision="pending"
            if missing
            else "skip_sft_propose_rl"
            if valid / total >= 0.8 and n8_wins >= 1
            else "run_approved_sft_then_qualify",
            interpretation="Parser-only development re-probe. Initial prompts, candidate subsets, targets and requested generation seeds match the earlier prompt probe. No remaining-candidate feedback and no frozen-eval service calls.",
        )
        if config.get("evaluation_kind") in {
            "format_qualification", "candidate_set_qualification"
        }:
            wins = sum(g["won"] for g in games)
            result.update(
                decision="pending"
                if missing
                else "qualified_stop_before_rl"
                if valid / total >= config["qualification"]["valid_turn_rate_minimum"]
                and wins >= config["qualification"]["wins_minimum"]
                else "qualification_failed_stop_before_rl",
                qualification_wins=wins,
                interpretation="Post-SFT qualification on separate training-pool animals cases at N=4 and N=8. Neither these games nor frozen/held-out rows entered SFT gradients. The SFT uses fresh procedural toy tables and cross_entropy only; this is not RL.",
            )
            result["verification"].update(
                sft_optimizer_operations=sum(
                    op["key"].startswith("optim-") for op in operations
                ),
                rl_training_operations=0,
            )
            if config["evaluation_kind"] == "candidate_set_qualification":
                result["interpretation"] = (
                    "Candidate-set qualification on the same 32 training-pool animal "
                    "games for raw base and the existing format-SFT checkpoint. "
                    "These cases are development data, not frozen-test evaluation. "
                    "No new training occurred. The main task measures question "
                    "selection given environment-computed candidate state."
                )
            result["cost"].update(
                scope="format SFT plus qualification"
                if config["evaluation_kind"] == "format_qualification"
                else "candidate-set qualification only",
                gradient_usd=str(
                    sum(
                        (
                            Decimal(op["actual_usd"])
                            for op in operations
                            if op["key"].startswith("forward-") and op.get("settled")
                        ),
                        Decimal(0),
                    )
                ),
                sampling_usd=str(
                    sum(
                        (
                            Decimal(r["actual_usd"])
                            for r in requests.values()
                            if r.get("settled")
                        ),
                        Decimal(0),
                    )
                ),
            )
        for cell in cells:
            causes = Counter()
            for game in games:
                if game["n"] != cell["n"]:
                    continue
                names = records[game["game_id"]]["world"]["names"]
                for turn in game["turns"]:
                    if turn["invalid"]:
                        causes[turn.get("error", "INVALID without diagnostic")] += 1
                    elif turn["action"].startswith("GUESS: "):
                        if "\n" in turn["action"]:
                            causes["GUESS contains extra lines"] += 1
                        elif turn["action"][7:].strip() not in names:
                            causes["GUESS name outside candidate table"] += 1
                    elif not turn["is_question"]:
                        causes["Non-GUESS action after question budget"] += 1
            assert sum(causes.values()) == cell["turns"] - cell["valid_turns"]
            cell["remaining_invalid_turn_causes"] = dict(causes)
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    (out / "games.jsonl.gz").write_bytes(
        gzip.compress(
            "".join(
                json.dumps(g, separators=(",", ":")) + "\n" for g in games
            ).encode(),
            mtime=0,
        )
    )
    compact = []
    responses = []
    for request in requests.values():
        row = {k: v for k, v in request.items() if k != "response"}
        if "response" in request:
            row["response_sha256"] = hashlib.sha256(
                json.dumps(request["response"], sort_keys=True).encode()
            ).hexdigest()
            assert request.get("output_allowed") is not False
            responses.append(
                {"entry_id": request["entry_id"], "response": request["response"]}
            )
        compact.append(row)
    (out / "requests.jsonl.gz").write_bytes(
        gzip.compress(
            "".join(
                json.dumps(r, separators=(",", ":")) + "\n"
                for r in sorted(compact, key=lambda r: r["key"])
            ).encode(),
            mtime=0,
        )
    )
    (out / "responses.jsonl.gz").write_bytes(
        gzip.compress(
            "".join(
                json.dumps(r, separators=(",", ":")) + "\n"
                for r in sorted(responses, key=lambda r: r["entry_id"])
            ).encode(),
            mtime=0,
        )
    )
    if operations:
        compact_operations = []
        for op in operations:
            row = {k: v for k, v in op.items() if k != "response"}
            if "response" in op:
                row["response_sha256"] = hashlib.sha256(
                    json.dumps(op["response"], sort_keys=True).encode()
                ).hexdigest()
                if not op["key"].startswith("forward-"):
                    row["response"] = op["response"]
                else:
                    row["reported_metrics"] = op["response"].get("metrics", {})
            compact_operations.append(row)
        (out / "operations.jsonl.gz").write_bytes(
            gzip.compress(
                "".join(
                    json.dumps(row, separators=(",", ":")) + "\n"
                    for row in compact_operations
                ).encode(),
                mtime=0,
            )
        )
    print(
        json.dumps(
            {
                "games": len(games),
                "missing": missing,
                "cells": [
                    {k: v for k, v in c.items() if k not in ("metrics", "parse_errors")}
                    for c in cells
                ],
                "cost": result["cost"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partial", action="store_true")
    main(parser.parse_args().partial)
