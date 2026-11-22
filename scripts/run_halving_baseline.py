"""Price, collect, and replay the approved N=32 noiseless halving-prompt baseline."""

import argparse
import asyncio
from decimal import Decimal
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tinker
from tinker_cookbook.rl.rollouts import do_single_rollout

from scripts.build_writeup_data import read_json
from twenty_bits.budget import ACTIVE_STATES, MULTIPLIER, BudgetError, Ledger, money
from twenty_bits.candidate_feedback import candidate_messages, token_hash
from twenty_bits.evaluation import frozen_games
from twenty_bits.game import Game
from twenty_bits.guess_metrics import guess_state
from twenty_bits.model_player import GuardedCompleter, TableEnv
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import (
    GuardedTinker,
    NetworkInterruption,
    rates,
    sample_cost,
    save_json,
)
from twenty_bits.worlds import ROOT, seed_for

OUT = ROOT / "results/submission/halving"
RUN_ID = "submission-halving-v1"
RUN = ROOT / "runs" / RUN_ID
CAP = Decimal("0.400000")
PROMPT_VERSION = "candidate-set-halving-v1"
INSTRUCTIONS = (
    "\nQUESTION SELECTION STRATEGY\n"
    "Before each ASK, use the remaining candidates and the table to choose a legal "
    "Boolean expression that divides those candidates as evenly as possible. "
    "Compare how many remaining rows would answer YES and how many would answer NO. "
    "Prefer a question with roughly half on each side, so either answer removes "
    "roughly half the possibilities. For example, among eight remaining candidates "
    "a four-YES, four-NO split is better than a one-YES, seven-NO split. "
    "Use attributes and legal Boolean combinations to find an even split. "
    "When attributes give poor splits, a legal OR of item equalities can define a half. "
    "After a reply, repeat this strategy on the updated remaining set. "
    "Keep following the existing output and final-guess rules.\n"
)


def halving_messages(record, turns=None):
    messages = candidate_messages(record, turns)
    messages[0]["content"] += INSTRUCTIONS
    return messages


def setup():
    config = {
        key: value
        for key, value in read_json("experiments/main_A11.json").items()
        if key
        in (
            "primary_model",
            "primary_thinking",
            "primary_output_cap",
            "context_window",
            "temperature",
            "top_p",
            "top_k",
            "grammar_version",
            "reference_model",
            "reference_template_date",
            "sdk_version",
            "cookbook_pin",
            "reward",
            "posterior_threshold",
        )
    }
    config.update(
        active_models=[config["primary_model"]],
        run_id=RUN_ID,
        run_cap_usd=str(CAP),
        sampling_seed_namespace="main-U-v1/evaluation",
        display_name="Twenty Bits submission halving baseline",
        prompt_version=PROMPT_VERSION,
        training_authorized=False,
        eval_only=True,
        concurrent_games=8,
        ledger_phase=5,
        system_prompt_addition=INSTRUCTIONS,
        approval="User approved one halving-prompt evaluation only, with a $0.40 cap.",
    )
    records = frozen_games("animals", 32, 0, count=28)
    with gzip.open(ROOT / "results/main_A11/games.jsonl.gz", "rt") as archive:
        raw = {
            g["game_id"]: g
            for g in map(json.loads, archive)
            if g["kind"] == "eval_base"
            and (g["domain"], g["n"], g["noise"]) == ("animals", 32, 0)
        }
    assert set(raw) == {r["id"] for r in records} and len(raw) == 28
    assert all(
        game["sampling_seed_namespace"] == config["sampling_seed_namespace"]
        for game in raw.values()
    )
    return config, records, raw


def preflight(config, records, raw):
    rendering = Rendering(config["primary_model"], config)
    original_tokens = amended_tokens = output_tokens = 0
    initial, largest_addition, maximum_prompt_tokens = {}, 0, 0
    for record in records:
        gid = record["id"]
        turns = raw[gid]["turns"]
        assert len(turns) == raw[gid]["sampling_calls"]
        for i, turn in enumerate(turns):
            before = turns[:i]
            primary = candidate_messages(record, before)
            amended = halving_messages(record, before)
            assert amended[0]["content"] == primary[0]["content"] + INSTRUCTIONS
            assert amended[1:] == primary[1:]
            original = rendering.prompt(primary)
            prompt = rendering.prompt(amended)
            assert original.to_ints() == raw[gid]["trajectory"][i]["ob"]
            assert original.length == turn["usage"]["prompt_tokens"]
            assert (
                prompt.length + config["primary_output_cap"] <= config["context_window"]
            )
            original_tokens += original.length
            amended_tokens += prompt.length
            output_tokens += turn["usage"]["output_tokens"]
            maximum_prompt_tokens = max(maximum_prompt_tokens, prompt.length)
            largest_addition = max(largest_addition, prompt.length - original.length)
            if i == 0:
                initial[gid] = {
                    "primary_sha256": token_hash(original.to_ints()),
                    "halving_sha256": token_hash(prompt.to_ints()),
                    "halving_tokens": prompt.length,
                }
    assert largest_addition <= 256 and (original_tokens, output_tokens) == (
        767369,
        33303,
    )
    rate = rates(config["primary_model"])
    token_price = Decimal(1_000_000)
    replay = (
        amended_tokens * rate["prefill"] + output_tokens * rate["sample"]
    ) / token_price
    planned = (
        (original_tokens + 308 * 256) * rate["prefill"] + output_tokens * rate["sample"]
    ) / token_price
    allowance = Decimal("1.15")
    forecast = planned * allowance * MULTIPLIER
    assert forecast <= CAP
    return {
        "config": config,
        "game_ids": list(initial),
        "initial_prompt_hashes": initial,
        "primary_input_tokens": original_tokens,
        "halving_replay_input_tokens": amended_tokens,
        "observed_primary_output_tokens": output_tokens,
        "max_measured_added_tokens_per_call": largest_addition,
        "max_measured_prompt_tokens": maximum_prompt_tokens,
        "uncached_replay_cost_usd": str(replay),
        "padded_replay_estimate_usd": str(planned),
        "trajectory_allowance": str(allowance),
        "reservation_multiplier": str(MULTIPLIER),
        "forecast_including_margin_usd": str(forecast),
        "run_cap_usd": str(CAP),
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "experiments/main_A11.json",
                "evals/frozen/animals_n32_p0.00.jsonl.gz",
                "results/main_A11/games.jsonl.gz",
                "twenty_bits/candidate_feedback.py",
                "twenty_bits/model_player.py",
            )
        },
    }


def game_path(record):
    return RUN / "games" / (hashlib.sha256(record["id"].encode()).hexdigest() + ".json")


async def collect(config, records, ledger):
    transport = GuardedTinker(
        config, RUN, ledger=ledger, usage_path=OUT / "usage.jsonl", run_cap_usd=str(CAP)
    )
    transport.replacements.clear()
    if transport.state["finished"]:
        return transport.state
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    def halt():
        transport.failed = True
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, halt)

    tasks = []
    heartbeat = None
    try:
        await transport.open(recover_pending=True)
        await transport.sampler(config["primary_model"])
        heartbeat = asyncio.create_task(transport.heartbeat(stop))
        slots = asyncio.Semaphore(config["concurrent_games"])

        async def one(record):
            path = game_path(record)
            if path.exists():
                return
            async with slots:
                try:
                    if transport.failed:
                        return
                    if heartbeat.done():
                        heartbeat.result()
                    env = TableEnv(
                        record,
                        config["primary_model"],
                        config,
                        message_builder=halving_messages,
                    )
                    trajectory = await do_single_rollout(
                        GuardedCompleter(transport, env), env
                    )
                    game = env.result()
                    assert (
                        env.game.done
                        and abs(
                            sum(t.reward for t in trajectory.transitions)
                            - game["reward"]
                        )
                        < 1e-10
                    )
                    game.update(
                        policy="Halving",
                        kind="eval_halving",
                        is_primary_result=False,
                        prompt_version=PROMPT_VERSION,
                        sampling_seed_namespace=config["sampling_seed_namespace"],
                        guess_state=guess_state(game, record),
                    )
                    save_json(path, game)
                    print(f"Saved {record['id']} (win={game['won']}).", flush=True)
                except BaseException:
                    transport.failed = True
                    raise

        tasks = [asyncio.create_task(one(r)) for r in records]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, BaseException)]
        if errors:
            raise next(
                (e for e in errors if isinstance(e, NetworkInterruption)), errors[0]
            )
        if stop.is_set() or not all(game_path(r).exists() for r in records):
            raise BudgetError("Halving evaluation stopped after draining active work.")
        await transport.finish()
        return transport.state
    finally:
        halt()
        await asyncio.gather(*tasks, return_exceptions=True)
        if heartbeat:
            await asyncio.gather(heartbeat, return_exceptions=True)
        try:
            await transport.close()
        finally:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)


def write_archive(name, rows):
    path = OUT / name
    temporary = path.with_suffix(".tmp")
    with (
        temporary.open("wb") as f,
        gzip.GzipFile(filename="", fileobj=f, mode="wb", mtime=0) as g,
    ):
        for row in rows:
            g.write(
                (
                    json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
                ).encode()
            )
    temporary.replace(path)


def read_archive(name):
    with gzip.open(OUT / name, "rt") as f:
        return [json.loads(line) for line in f]


def archive(config, records, ledger, state):
    assert state["finished"] and all(game_path(r).exists() for r in records)
    entries = ledger.entries(operation_prefix=f"[{RUN_ID}] ")
    status = ledger.summary(operation_prefix=f"[{RUN_ID}] ")
    assert not any(entry["state"] in ACTIVE_STATES for entry in entries)
    assert Decimal(status["spent_usd"]) + Decimal(status["held_usd"]) <= CAP
    games = [json.loads(game_path(r).read_text()) for r in records]
    requests = [
        json.loads(p.read_text()) for p in sorted((RUN / "requests").glob("*.json"))
    ]
    assert len(requests) == sum(g["sampling_calls"] for g in games)
    assert all(r["settled"] for r in requests)
    write_archive("games.jsonl.gz", games)
    write_archive(
        "requests.jsonl.gz",
        ({k: v for k, v in r.items() if k != "response"} for r in requests),
    )
    write_archive(
        "responses.jsonl.gz",
        ({"key": r["key"], "response": r["response"]} for r in requests),
    )
    write_archive("ledger_entries.jsonl.gz", entries)
    summary = verify(config, records)
    save_json(
        OUT / "completion.json",
        {
            **summary,
            "training_updates": 0,
            "finished_session": True,
            "all_HTTP_work_drained": True,
            "run_budget": {k: status[k] for k in ("spent_usd", "held_usd")},
            "project_budget": ledger.summary(),
        },
    )


def verify(config, records):
    rendering = Rendering(config["primary_model"], config)
    games = read_archive("games.jsonl.gz")
    requests = {row["key"]: row for row in read_archive("requests.jsonl.gz")}
    responses = {
        row["key"]: row["response"] for row in read_archive("responses.jsonl.gz")
    }
    entries = {row["id"]: row for row in read_archive("ledger_entries.jsonl.gz")}
    hashes = []
    spent = Decimal(0)
    for game, record in zip(games, records, strict=True):
        assert game["game_id"] == record["id"] and game["policy"] == "Halving"
        replay = Game(record, grammar_version=config["grammar_version"])
        for i, turn in enumerate(game["turns"]):
            key = f"{config['primary_model']}/{record['id']}/turn-{i}"
            request = requests.pop(key)
            response = responses.pop(key)
            prompt = rendering.prompt(halving_messages(record, replay.turns))
            parameters = request["parameters"]
            assert (
                parameters["seed"]
                == seed_for(config["sampling_seed_namespace"], record["id"], i) % 2**31
            )
            for name in ("temperature", "top_p", "top_k"):
                assert parameters[name] == config[name]
            assert parameters["max_tokens"] == config["primary_output_cap"]
            payload = {
                "model": config["primary_model"],
                "prompt_ids": prompt.to_ints(),
                "sampling_params": parameters,
            }
            assert (
                hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                == request["signature"]
            )
            assert (
                prompt.length
                == request["prompt_tokens"]
                == turn["usage"]["prompt_tokens"]
            )
            hashes.append({"key": key, "prompt_sha256": token_hash(prompt.to_ints())})
            assert (
                request["request_id"]
                == request["receipt"]["request_id"]
                == entries[request["entry_id"]]["request_id"]
            )
            assert request["actual_usd"] == entries[request["entry_id"]]["actual_usd"]
            spent += Decimal(request["actual_usd"])
            tokens = response["sequences"][0]["tokens"]
            assert (
                len(tokens)
                == request["output_tokens"]
                == turn["usage"]["output_tokens"]
            )
            assert (
                response["prompt_cache_hit_tokens"]
                == request["prompt_cache_hit_tokens"]
            )
            assert request["actual_usd"] == sample_cost(
                config["primary_model"],
                prompt.length,
                len(tokens),
                request["prompt_cache_hit_tokens"],
            )
            decoded = rendering.decode(tokens)
            assert decoded["raw_model_text"] == turn["raw_model_text"]
            assert decoded["action"] == turn["raw_action"]
            scored = replay.step(decoded["action"])
            for name in ("answer", "invalid", "is_question", "reask", "eig"):
                assert scored[name] == turn[name], (key, name)
        if game["context_overflow"]:
            assert (
                rendering.prompt(halving_messages(record, replay.turns)).length
                + config["primary_output_cap"]
                > config["context_window"]
            )
        else:
            assert replay.done
        assert replay.won == game["won"] and replay.reward == game["reward"]
    assert not requests and not responses
    assert all(row["state"] == "settled" for row in entries.values())
    assert spent == sum(Decimal(row["actual_usd"]) for row in entries.values())
    summary = {
        "games": len(games),
        "wins": sum(g["won"] for g in games),
        "verified_requests": len(hashes),
        "observed_sampling_usage_usd": str(spent),
        "eval_only": True,
        "is_primary_result": False,
    }
    if (OUT / "completion.json").exists():
        completed = read_json("results/submission/halving/completion.json")
        assert all(completed[key] == value for key, value in summary.items())
        assert read_archive("prompt_hashes.jsonl.gz") == hashes
    else:
        write_archive("prompt_hashes.jsonl.gz", hashes)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "run", "verify"))
    args = parser.parse_args()
    if args.mode == "run" and (OUT / "completion.json").exists():
        print("Halving baseline complete. No service calls.")
        return
    config, records, raw = setup()
    proof_path = OUT / "preflight.json"
    if args.mode == "verify":
        if not (OUT / "completion.json").exists():
            parser.error("completed halving archive is required")
        print(json.dumps(verify(config, records)))
        return
    proof = preflight(config, records, raw)
    if args.mode == "preflight":
        save_json(proof_path, proof)
        print(
            json.dumps(
                {
                    k: v
                    for k, v in proof.items()
                    if k
                    not in (
                        "game_ids",
                        "config",
                        "initial_prompt_hashes",
                        "source_sha256",
                    )
                },
                indent=2,
            )
        )
        return
    if not proof_path.exists() or json.loads(proof_path.read_text()) != proof:
        parser.error("matching saved preflight required before sampling")
    if tinker.__version__ != config["sdk_version"]:
        parser.error("pinned Tinker SDK required before sampling")
    os.environ.pop("TINKER_LOG", None)
    RUN.mkdir(parents=True, exist_ok=True)
    with (RUN / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger = Ledger(ROOT / "ledger.json")
        if not ledger.entries(operation_prefix=f"[{RUN_ID}] "):
            ledger.check_run(
                estimate_usd=str(
                    money(
                        Decimal(proof["padded_replay_estimate_usd"])
                        * Decimal(proof["trajectory_allowance"])
                    )
                ),
                max_cost_usd=str(CAP),
            )
        for attempt in range(3):
            try:
                state = asyncio.run(collect(config, records, ledger))
                archive(config, records, ledger, state)
                break
            except NetworkInterruption:
                if attempt == 2:
                    raise
                print(
                    "Connection interrupted. Reconnecting to collect original requests before submitting more.",
                    flush=True,
                )


if __name__ == "__main__":
    try:
        main()
    except (tinker.APIError, NetworkInterruption) as exc:
        status = getattr(exc, "status_code", None)
        print(
            f"Halving runner stopped ({type(exc).__name__}, HTTP {status}). Consult the local request journal.",
            file=sys.stderr,
        )
        sys.exit(1)
