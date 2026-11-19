"""Replay fixed-policy counter rollouts and compare paired primary games."""

from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import tinker

from scripts.prepare_visible_budget import primary_games
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.budget_followup_metrics import flags, summarize
from twenty_bits.candidate_feedback import candidate_messages, token_hash
from twenty_bits.game import Game
from twenty_bits.guess_metrics import guess_state
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import sample_cost, save_json
from twenty_bits.visible_budget import visible_budget_messages
from twenty_bits.worlds import ROOT, seed_for


def read_gzip(path):
    return [json.loads(line) for line in gzip.open(path, "rt")]


def write_gzip(path, rows):
    path.write_bytes(
        gzip.compress(
            "".join(
                json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
                for row in rows
            ).encode(),
            mtime=0,
        )
    )


def bootstrap_values(games, indices):
    win = np.array([g["won"] for g in games], dtype=float)
    q = np.array([g["questions"] for g in games], dtype=float)
    eig = np.array([sum(g["question_eigs"]) for g in games])
    denominator = q[indices].sum(axis=-1)
    values = {
        "win_rate": win[indices].mean(axis=-1),
        "eig_per_question": np.divide(
            eig[indices].sum(axis=-1),
            denominator,
            out=np.full(np.shape(denominator), np.nan),
            where=denominator > 0,
        ),
    }
    for key in flags(games[0]):
        data = np.array([flags(g)[key] for g in games], dtype=float)
        values[key + "_rate"] = data[indices].mean(axis=-1)
    return values


def summarize_cohort(games):
    result = summarize(games)
    result["context_overflow_games"] = sum(g["context_overflow"] for g in games)
    result["format_error_turns"] = sum(g["format_error_count"] for g in games)
    return result


def paired_interval(primary, visible, indices):
    assert [g["game_id"] for g in primary] == [g["game_id"] for g in visible]
    a, b = bootstrap_values(primary, indices), bootstrap_values(visible, indices)
    point_a = bootstrap_values(primary, np.arange(len(primary)))
    point_b = bootstrap_values(visible, np.arange(len(visible)))
    return {
        key: {
            "visible_minus_primary": float(point_b[key] - point_a[key]),
            "ci95": np.nanquantile(b[key] - a[key], [0.025, 0.975]).tolist(),
        }
        for key in a
    }


def main():
    out = ROOT / "results/visible_budget"
    config = json.loads((ROOT / "experiments/visible_budget.json").read_text())
    proof = json.loads((ROOT / "research/visible_budget_preflight.json").read_text())
    for path, digest in proof["immutable_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    records = json.loads(
        gzip.decompress(
            (ROOT / "experiments/visible_budget_games.json.gz").read_bytes()
        )
    )
    records = {r["id"]: r for r in records}
    directory = ROOT / "runs" / config["run_id"]
    paths = sorted((directory / "games").glob("*.json"))
    games = (
        [json.loads(p.read_text()) for p in paths]
        if paths
        else read_gzip(out / "games.jsonl.gz")
    )
    games.sort(key=lambda g: (g["policy"], g["game_id"]))
    assert len(games) == 840
    req_paths = sorted((directory / "requests").glob("*.json"))
    requests = (
        [json.loads(p.read_text()) for p in req_paths]
        if req_paths
        else read_gzip(out / "requests.jsonl.gz")
    )
    excluded = [
        r for r in requests if r.get("orphaned") or r.get("output_allowed") is False
    ]
    requests = [r for r in requests if r not in excluded]
    if not req_paths:
        excluded = read_gzip(out / "excluded_originals.jsonl.gz")
        responses = {
            row["entry_id"]: row["response"]
            for row in read_gzip(out / "responses.jsonl.gz")
        }
        for request in requests:
            request["response"] = responses[request["entry_id"]]
    by_entry = {r["entry_id"]: r for r in requests}
    rendering = Rendering(config["primary_model"], config)
    used = set()
    hashes = []
    policies = {p["name"]: p for p in config["policies"]}
    session_path = (
        directory / "sessions.json"
        if (directory / "sessions.json").exists()
        else out / "sessions.json"
    )
    session = json.loads(session_path.read_text())
    assert session["finished"]
    for number, game in enumerate(games):
        record = records[game["game_id"]]
        assert game["eval_only"] and not game["is_primary_result"]
        assert game["guess_state"] == guess_state(game, record)
        assert len(game["turns"]) == len(game["trajectory"])
        replay = Game(record, grammar_version=config["grammar_version"])
        next_ids = rendering.prompt(visible_budget_messages(record)).to_ints()
        overflow = (
            len(next_ids) + config["primary_output_cap"] > config["context_window"]
        )
        if overflow:
            replay.done = True
        policy = policies[game["policy"]]
        snapshot = session["snapshots"][str(policy["snapshot_key"])]
        assert snapshot["native_checkpoint_path"] == policy["model_path"]
        for index, (turn, tape) in enumerate(zip(game["turns"], game["trajectory"])):
            public = visible_budget_messages(record, replay.turns)
            assert public[0] == candidate_messages(record, replay.turns)[0]
            ids = next_ids
            assert ids == tape["ob"]
            assert len(ids) + config["primary_output_cap"] <= config["context_window"]
            hashes.append(
                {
                    "policy": game["policy"],
                    "game_id": game["game_id"],
                    "turn": index,
                    "tokens": len(ids),
                    "sha256": token_hash(ids),
                }
            )
            request = by_entry[turn["usage"]["entry_id"]]
            assert request["settled"] and request["request_id_saved_before_dispatch"]
            assert request["saved_before_dispatch_at"]
            assert request["request_id"].startswith(snapshot["id"] + ":")
            assert (
                request["request_id"]
                == request["receipt"]["request_id"]
                == turn["usage"]["request_id"]
            )
            parameters = tinker.SamplingParams(
                max_tokens=config["primary_output_cap"],
                seed=seed_for(config["sampling_seed_namespace"], record["id"], index)
                % (2**31),
                stop=rendering.renderer.get_stop_sequences(),
                temperature=config["temperature"],
                top_p=config["top_p"],
                top_k=config["top_k"],
            ).model_dump(mode="json")
            assert request["parameters"] == parameters
            payload = {
                "model": config["primary_model"],
                "prompt_ids": ids,
                "sampling_params": parameters,
            }
            assert (
                request["signature"]
                == hashlib.sha256(
                    json.dumps(payload, sort_keys=True).encode()
                ).hexdigest()
            )
            sequence = request["response"]["sequences"][0]
            assert tape["tokens"] == sequence["tokens"]
            assert tape["logprobs"] == sequence["logprobs"]
            decoded = rendering.decode(sequence["tokens"])
            assert decoded["action"] == turn["raw_action"]
            assert request["actual_usd"] == sample_cost(
                config["primary_model"],
                len(ids),
                len(sequence["tokens"]),
                request["prompt_cache_hit_tokens"],
            )
            assert turn["usage"]["actual_usd"] == request["actual_usd"]
            reward_before = replay.reward
            observed = replay.step(
                decoded["action"],
                reasoning_tokens=decoded["reasoning_tokens"],
                action_tokens=decoded["action_tokens"],
                predicate_tokens=turn["predicate_tokens"],
                truncated=sequence["stop_reason"] == "length",
            )
            assert abs(replay.reward - reward_before - tape["reward"]) < 1e-12
            for key, value in observed.items():
                if isinstance(value, (float, list)):
                    np.testing.assert_allclose(value, turn[key], rtol=0, atol=1e-12)
                else:
                    assert value == turn[key], (game["game_id"], index, key)
            used.add(request["entry_id"])
            if not replay.done:
                next_ids = rendering.prompt(
                    visible_budget_messages(record, replay.turns)
                ).to_ints()
                if (
                    len(next_ids) + config["primary_output_cap"]
                    > config["context_window"]
                ):
                    overflow = True
                    replay.done = True
            assert tape["episode_done"] == replay.done
        result = replay.result()
        for key in [
            "won",
            "questions",
            "reward",
            "invalid_count",
            "format_error_count",
            "question_eigs",
            "early_guess",
            "enumeration_count",
        ]:
            if isinstance(result[key], (float, list)):
                np.testing.assert_allclose(result[key], game[key], rtol=0, atol=1e-12)
            else:
                assert result[key] == game[key]
        assert replay.done and overflow == game["context_overflow"]
        if (number + 1) % 140 == 0:
            print(f"Verified {number + 1}/840 follow-up games", flush=True)
    assert used == set(by_entry)
    primary = primary_games()
    assert all(
        game["sampling_seed_namespace"] == config["sampling_seed_namespace"]
        for cohort in primary.values()
        for game in cohort
    )
    cells = sorted({(r["domain"], r["n"], r["noise"]) for r in records.values()})
    rng = np.random.default_rng(20261119)
    draws = {(domain, n): rng.integers(28, size=(10000, 28)) for domain, n, _ in cells}
    rows = []
    for name in policies:
        for domain, n, noise in cells:
            pair = []
            for cohort in [primary[name], [g for g in games if g["policy"] == name]]:
                selected = sorted(
                    [
                        g
                        for g in cohort
                        if (g["domain"], g["n"], g["noise"]) == (domain, n, noise)
                    ],
                    key=lambda g: g["game_id"],
                )
                assert len(selected) == 28
                pair.append(selected)
            rows.append(
                {
                    "policy": name,
                    "domain": domain,
                    "n": n,
                    "noise": noise,
                    "primary": summarize_cohort(pair[0]),
                    "visible_budget": summarize_cohort(pair[1]),
                    "paired_changes": paired_interval(*pair, draws[(domain, n)]),
                }
            )
    pooled = {}
    for name in policies:
        pooled[name] = {}
        for label, noise in [("all", None), ("noiseless", 0), ("noisy", 0.1)]:
            a = [g for g in primary[name] if noise is None or g["noise"] == noise]
            b = [
                g
                for g in games
                if g["policy"] == name and (noise is None or g["noise"] == noise)
            ]
            pooled[name][label] = {
                "primary": summarize_cohort(a),
                "visible_budget": summarize_cohort(b),
            }
    ledger = Ledger.snapshot_status(ROOT / "ledger.json")
    entries = {e["id"]: e for e in ledger["entries"]}
    run_entries = [
        e
        for e in entries.values()
        if e["operation"].startswith(f"[{config['run_id']}] ")
    ]
    forbidden = [
        e
        for e in run_entries
        if any(
            x in e["operation"].lower()
            for x in ["forward backward", "optimizer", "save weights", "save state"]
        )
    ]
    assert not forbidden
    for request in requests:
        assert entries[request["entry_id"]]["state"] == "settled"
        assert entries[request["entry_id"]]["actual_usd"] == request["actual_usd"]
    spent = sum(Decimal(e.get("actual_usd") or "0") for e in run_entries)
    held = sum(
        Decimal(e["reserved_usd"]) for e in run_entries if e["state"] in ACTIVE_STATES
    )
    assert spent + held <= Decimal(config["run_cap_usd"])
    result = {
        "eval_only": True,
        "is_primary_result": False,
        "games": 840,
        "training_games": 0,
        "policies": config["policies"],
        "skipped_A11": config["skipped_policies"]["A11"],
        "cells": rows,
        "pooled": pooled,
        "followup_budget": {
            "spent_usd": str(spent),
            "held_usd": str(held),
            "cap_usd": config["run_cap_usd"],
        },
        "project_budget": {
            k: ledger[k] for k in ["cap_usd", "spent_usd", "held_usd", "available_usd"]
        },
        "tokens": {
            name: {
                key: sum(g[key] for g in games if g["policy"] == name)
                for key in [
                    "prompt_tokens",
                    "output_tokens",
                    "prompt_cache_hit_tokens",
                    "reasoning_tokens",
                ]
            }
            for name in policies
        },
        "sampling_usage_usd_by_policy": {
            name: str(
                sum(
                    Decimal(turn["usage"]["actual_usd"])
                    for game in games
                    if game["policy"] == name
                    for turn in game["turns"]
                )
            )
            for name in policies
        },
        "verification": {
            "accepted_sample_requests": len(requests),
            "excluded_originals": len(excluded),
            "native_prompt_sequences": len(hashes),
            "all_request_ids_saved_before_dispatch": True,
            "unchanged_scoring_replayed": True,
            "primary_artifacts_unchanged": True,
            "training_calls": 0,
        },
        "bootstrap": {
            "draws": 10000,
            "seed": 20261119,
            "unit": "paired complete game",
            "noise_variants_share_case_draws": True,
            "training_seed_uncertainty_estimated": False,
            "multiplicity_adjusted": False,
        },
    }
    save_json(out / "summary.json", result)
    save_json(out / "sessions.json", session)
    write_gzip(out / "games.jsonl.gz", games)
    (out / "prompt_hashes.json.gz").write_bytes(
        gzip.compress(json.dumps(hashes, separators=(",", ":")).encode(), mtime=0)
    )
    write_gzip(out / "excluded_originals.jsonl.gz", excluded)
    write_gzip(
        out / "requests.jsonl.gz",
        [{k: v for k, v in r.items() if k != "response"} for r in requests],
    )
    write_gzip(
        out / "responses.jsonl.gz",
        [{"entry_id": r["entry_id"], "response": r["response"]} for r in requests],
    )
    print(
        json.dumps(
            {
                "games": len(games),
                "requests": len(requests),
                "followup_budget": result["followup_budget"],
                "pooled": pooled,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
