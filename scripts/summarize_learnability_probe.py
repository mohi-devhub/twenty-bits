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


def main(partial=False):
    config = json.loads((ROOT / "experiments/learnability_probe.json").read_text())
    records = json.loads(
        (ROOT / "experiments/learnability_probe_games.json").read_text()
    )
    records = {r["id"]: r for r in records}
    directory = ROOT / "runs" / config["run_id"]
    out = ROOT / "results/learnability_probe"
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
        replay = Game(record)
        valid = 0
        for index, turn in enumerate(game["turns"]):
            prompt = rendering.prompt(probe_messages(record, replay.turns))
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
    for n in (8, 16):
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
    assert run_spent + run_held <= Decimal("1.500000")
    known_total = sum(
        (Decimal(r["actual_usd"]) for r in requests.values() if r.get("settled")),
        Decimal(0),
    )
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
        assert allowed_metadata or operation.startswith("sample Qwen/Qwen3-8B ")
    incident = json.loads(
        (ROOT / "research/learnability_probe_incident.json").read_text()
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
        "sampling_config_sha256": hashlib.sha256(
            (ROOT / "experiments/learnability_probe.json").read_bytes()
        ).hexdigest(),
        "complete": not missing,
        "missing_games": missing,
        "games": len(games),
        "cells": cells,
        "cost": {
            "probe_spent_usd": str(run_spent),
            "probe_held_usd": str(run_held),
            "probe_cap_usd": "1.500000",
            "project": {k: status[k] for k in status if k != "entries"},
        },
        "verification": {
            "replayed_turns": len(used),
            "used_entry_ids": sorted(used),
            "orphan_or_unavailable_outputs_used": 0,
            "training_operations": 0,
            "pre_dispatch_ids_verified": len(used),
            "all_attempts_with_pre_dispatch_ids_verified": len(requests),
            "native_rendering_and_request_signatures_verified": len(used),
            "exact_replacement_signatures_verified": len(
                incident["approved_replacements"]
            ),
        },
        "interpretation": "Training-pool development probe, noiseless only, no remaining-candidate feedback. Prompt and size differ from Phase 2, so this is not an isolated prompt treatment effect. Intervals resample complete games; missing games are listed and not scored as losses or wins.",
    }
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
