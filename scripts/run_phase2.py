"""Run or resume exactly the approved base evaluation. Never starts training."""

from pathlib import Path
import asyncio
import argparse
from contextlib import suppress
import fcntl
import hashlib
import json
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tinker_cookbook.rl.rollouts import do_single_rollout
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.model_player import GuardedCompleter, TableEnv
from twenty_bits.tinker_transport import GuardedTinker, save_json
from twenty_bits.worlds import ROOT


async def main(defer_uncertain=False, concurrent_games=None):
    config_path = ROOT / "evals/phase2.json"
    config = json.loads(config_path.read_text())
    proof = json.loads((ROOT / config["rendering_proof"]).read_text())
    if hashlib.sha256(config_path.read_bytes()).hexdigest() != proof["config_sha256"]:
        raise RuntimeError("Sampling configuration changed after the rendering proof.")
    directory = ROOT / "runs" / config["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config_copy = directory / "config.json"
        if config_copy.exists() and json.loads(config_copy.read_text()) != config:
            raise RuntimeError("This run already has different sampling settings.")
        save_json(config_copy, config)
        transport = GuardedTinker(config, directory)
        forecast = json.loads((ROOT / "research/approved_plan.json").read_text())[
            "phase2"
        ]
        jobs = []
        deferred = []
        uncertain_keys = set()
        for request in (directory / "requests").glob("*.json"):
            journal = json.loads(request.read_text())
            if not journal.get("receipt"):
                uncertain_keys.add(journal["key"].rsplit("/turn-", 1)[0])
        for model in [config["primary_model"], config["reference_model"]]:
            for cell in frozen_manifest()["cells"]:
                count = config["primary_games_per_cell"]
                if model == config["reference_model"]:
                    if cell["n"] not in config["reference_sizes"]:
                        continue
                    count = config["reference_games_per_cell"]
                for record in frozen_games(
                    cell["domain"], cell["n"], cell["noise"], count
                ):
                    key = model + "/" + record["id"]
                    path = (
                        directory
                        / "games"
                        / (hashlib.sha256(key.encode()).hexdigest() + ".json")
                    )
                    if not path.exists():
                        if defer_uncertain and key in uncertain_keys:
                            deferred.append(key)
                        else:
                            jobs.append((model, record, path))
        if not jobs:
            print(
                "All 300 approved games are already saved; no service calls made.",
                flush=True,
            )
            return
        parallelism = (
            config["concurrent_games"] if concurrent_games is None else concurrent_games
        )
        if parallelism < 1:
            raise ValueError("Concurrent game count must be positive.")
        save_json(
            directory / "execution.json",
            {
                "concurrent_games": parallelism,
                "sampling_config_sha256": hashlib.sha256(
                    config_path.read_bytes()
                ).hexdigest(),
                "note": "Execution parallelism only; frozen games, seeds, prompts and sampling parameters do not change.",
            },
        )
        transport.ledger.check_run(
            estimate_usd=str(forecast["forecast_usd"]),
            max_cost_usd=str(forecast["uncached_token_cap_envelope_usd"]),
        )
        await transport.open()
        for model in sorted({model for model, _, _ in jobs}):
            await transport.sampler(model)
        heartbeat = asyncio.create_task(transport.heartbeat())
        loop = asyncio.get_running_loop()

        def stop_after_active_requests():
            transport.failed = True

        loop.add_signal_handler(signal.SIGINT, stop_after_active_requests)
        loop.add_signal_handler(signal.SIGTERM, stop_after_active_requests)
        semaphore = asyncio.Semaphore(parallelism)
        completed = 300 - len(jobs) - len(deferred)

        async def run_one(model, record, path):
            nonlocal completed
            async with semaphore:
                if transport.failed:
                    raise RuntimeError("New games stopped after an adapter error.")
                if heartbeat.done():
                    heartbeat.result()
                env = TableEnv(record, model, config)
                trajectory = await do_single_rollout(
                    GuardedCompleter(transport, env), env
                )
                if not env.game.done:
                    raise RuntimeError("Cookbook rollout returned an incomplete game.")
                result = env.result()
                result["trajectory_transitions"] = len(trajectory.transitions)
                save_json(path, result)
                completed += 1
                status = transport.ledger.status()
                print(
                    json.dumps(
                        {
                            "completed": completed,
                            "total": 300,
                            "model": model,
                            "game": record["id"],
                            "won": result["won"],
                            "questions": result["questions"],
                            "eig": result["eig_per_question"],
                            "spent_usd": status["spent_usd"],
                            "held_usd": status["held_usd"],
                        }
                    ),
                    flush=True,
                )

        tasks = [asyncio.create_task(run_one(*job)) for job in jobs]
        try:
            await asyncio.gather(*tasks)
            if not deferred:
                await transport.finish()
            else:
                print(
                    json.dumps(
                        {"deferred_uncertain_games": deferred, "complete": False}
                    ),
                    flush=True,
                )
        finally:
            transport.failed = True
            # Drain active HTTP requests so their receipts and usage survive.
            # Queued games see failed=True before making another submission.
            await asyncio.gather(*tasks, return_exceptions=True)
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
            await transport.close()
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--defer-uncertain", action="store_true")
    parser.add_argument("--concurrent-games", type=int)
    args = parser.parse_args()
    asyncio.run(main(args.defer_uncertain, args.concurrent_games))
