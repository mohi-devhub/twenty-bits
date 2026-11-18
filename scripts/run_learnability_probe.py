"""Run only the authorized prompt probe, with a $1.50 limit including holds."""

import asyncio
import argparse
from decimal import Decimal
import fcntl
import hashlib
import json
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tinker_cookbook.rl.rollouts import do_single_rollout
from twenty_bits.learnability import probe_messages, probe_records
from twenty_bits.model_player import GuardedCompleter, TableEnv
from twenty_bits.tinker_transport import GuardedTinker, NetworkInterruption, save_json
from twenty_bits.worlds import ROOT


async def run_once(
    defer_unrecoverable=False,
    *,
    config_path=None,
    proof_path=None,
    games_path=None,
    results_path=None,
    approved_run_cap="1.500000",
):
    config_path = config_path or ROOT / "experiments/learnability_probe.json"
    games_path = games_path or ROOT / "experiments/learnability_probe_games.json"
    results_path = results_path or ROOT / "results/learnability_probe"
    config = json.loads(config_path.read_text())
    proof = json.loads(
        (proof_path or ROOT / "research/learnability_probe_rendering.json").read_text()
    )
    for path, field in [
        (config_path, "config_sha256"),
        (games_path, "games_sha256"),
        (ROOT / "twenty_bits/learnability.py", "prompt_code_sha256"),
    ]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != proof[field]:
            raise RuntimeError("The prepared probe changed. No service call was made.")
    for name, digest in proof.get("implementation_sha256", {}).items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("The declared grammar implementation changed.")
    if config["training_authorized"] or config["run_cap_usd"] != approved_run_cap:
        raise RuntimeError("This runner authorizes only the approved inference cap.")
    records = json.loads(games_path.read_text())
    if records != probe_records():
        raise RuntimeError("The probe no longer matches its training-pool factory.")
    saved_summary = results_path / "summary.json"
    if saved_summary.exists():
        summary = json.loads(saved_summary.read_text())
        if summary.get("complete") and summary.get("games") == 32:
            if summary["sampling_config_sha256"] != proof["config_sha256"]:
                raise RuntimeError("Completed probe settings differ from this request.")
            print(
                "The approved 32-game probe is complete. No service calls made.",
                flush=True,
            )
            return
    directory = ROOT / "runs" / config["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config_copy = directory / "config.json"
        if config_copy.exists() and json.loads(config_copy.read_text()) != config:
            raise RuntimeError("An existing probe used different settings.")
        save_json(config_copy, config)
        jobs = []
        deferred = []
        unavailable = set()
        if defer_unrecoverable:
            for request in (directory / "requests").glob("*.json"):
                journal = json.loads(request.read_text())
                if journal.get("recovery_pending"):
                    unavailable.add(journal["key"].rsplit("/turn-", 1)[0])
        for record in records:
            key = config["primary_model"] + "/" + record["id"]
            path = (
                directory
                / "games"
                / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            )
            if not path.exists():
                if key in unavailable:
                    deferred.append(record["id"])
                else:
                    jobs.append((record, path))
        if not jobs:
            print(
                json.dumps(
                    {
                        "saved_games": 32 - len(deferred),
                        "deferred_games": deferred,
                        "service_calls": 0,
                    }
                ),
                flush=True,
            )
            return
        incident_name = config.get(
            "incident_record", "research/learnability_probe_incident.json"
        )
        incident_path = ROOT / incident_name if incident_name else None
        incident = (
            json.loads(incident_path.read_text())
            if incident_path and incident_path.exists()
            else {}
        )
        approved = incident.get("approved_replacements", {})
        if approved and incident.get("replacement_approval") != "approved":
            raise RuntimeError("Replacement requests lack approval.")
        transport = GuardedTinker(
            config,
            directory,
            usage_path=results_path / "usage.jsonl",
            run_cap_usd=config["run_cap_usd"],
            approved_replacements=approved,
        )
        # Admission uses a forecast. The per-call guard enforces the run cap.
        transport.ledger.check_run(
            estimate_usd=proof.get("forecast_usd", "0"),
            max_cost_usd=str(
                min(
                    Decimal(proof["full_cap_hold_envelope_usd"]),
                    Decimal(approved_run_cap),
                )
            ),
        )
        try:
            # This runs before even checking capabilities or making a new sampler.
            await transport.open(recover_pending=True)
            await transport.sampler(config["primary_model"])
        except BaseException:
            await transport.close()
            raise
        stop_heartbeat = asyncio.Event()
        heartbeat = asyncio.create_task(transport.heartbeat(stop_heartbeat))
        loop = asyncio.get_running_loop()
        stop_requested = False

        def stop_after_active_requests():
            nonlocal stop_requested
            stop_requested = True
            transport.failed = True

        loop.add_signal_handler(signal.SIGINT, stop_after_active_requests)
        loop.add_signal_handler(signal.SIGTERM, stop_after_active_requests)
        semaphore = asyncio.Semaphore(config["concurrent_games"])
        completed = 32 - len(jobs) - len(deferred)

        async def run_one(record, path):
            nonlocal completed
            async with semaphore:
                if transport.failed:
                    raise RuntimeError(
                        "New games stopped; active requests are draining."
                    )
                if heartbeat.done():
                    heartbeat.result()
                env = TableEnv(
                    record,
                    config["primary_model"],
                    config,
                    message_builder=probe_messages,
                )
                trajectory = await do_single_rollout(
                    GuardedCompleter(transport, env), env
                )
                if not env.game.done:
                    raise RuntimeError("Cookbook rollout returned an incomplete game.")
                result = env.result()
                result.update(
                    policy=config.get("policy", "prompt_probe"),
                    prompt_version=config["prompt_version"],
                    trajectory_transitions=len(trajectory.transitions),
                )
                if "grammar_version" in config:
                    result["grammar_version"] = config["grammar_version"]
                save_json(path, result)
                completed += 1
                print(
                    json.dumps(
                        {
                            "completed": completed,
                            "total": 32,
                            "n": record["n"],
                            "game": record["id"],
                            "won": result["won"],
                            "questions": result["questions"],
                            "invalid": result["invalid_count"],
                            "eig": result["eig_per_question"],
                            "probe_budget": transport.run_status(),
                        }
                    ),
                    flush=True,
                )

        tasks = [asyncio.create_task(run_one(*job)) for job in jobs]
        failure = None
        outcomes = []
        try:
            await asyncio.gather(*tasks)
            if not deferred:
                await transport.finish()
            else:
                print(
                    json.dumps({"deferred_games": deferred, "complete": False}),
                    flush=True,
                )
        except Exception as exc:
            failure = exc
        finally:
            transport.failed = True
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            stop_heartbeat.set()
            try:
                outcomes.extend(await asyncio.gather(heartbeat, return_exceptions=True))
            finally:
                await transport.close()
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)
        if stop_requested:
            raise RuntimeError(
                "Stopped after draining HTTP operations; saved requests retain their holds."
            )
        network = next(
            (r for r in outcomes if isinstance(r, NetworkInterruption)), None
        )
        if network is not None:
            raise network
        if failure is not None:
            raise failure


async def main(defer_unrecoverable=False, **run_options):
    while True:
        try:
            return await run_once(defer_unrecoverable, **run_options)
        except NetworkInterruption:
            print(
                "Network interrupted. HTTP tasks drained; reconnecting to collect all pending futures before new submissions.",
                flush=True,
            )
            await asyncio.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--defer-unrecoverable", action="store_true")
    asyncio.run(main(parser.parse_args().defer_unrecoverable))
