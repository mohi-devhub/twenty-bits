"""Run the approved format SFT and qualification, then stop before RL."""

import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import signal
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tinker_cookbook.rl.rollouts import do_single_rollout
from tinker import types
from twenty_bits.learnability import probe_messages
from twenty_bits.model_player import GuardedCompleter, TableEnv
from twenty_bits.supervised import (
    GuardedSupervised,
    qualification_records,
    supervised_data,
)
from twenty_bits.tinker_transport import GuardedTinker, NetworkInterruption, save_json
from twenty_bits.worlds import ROOT


async def download_export(transport, external):
    folder = transport.directory / "adapter"
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    parsed = types.ParsedCheckpointTinkerPath.from_tinker_path(external["path"])
    if parsed.checkpoint_type != "external":
        raise ValueError("The export is not an external-format checkpoint.")
    urls = await transport.free(
        "external weight download URLs",
        lambda: transport.client.weights.get_external_weights_urls(
            model_id=parsed.training_run_id, checkpoint_id=parsed.checkpoint_id
        ),
    )
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for name, url in urls["urls"].items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("External checkpoint file has an unsafe path.")
            path = folder / relative
            if name in manifest and path.exists():
                if (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    != manifest[name]["sha256"]
                ):
                    raise ValueError("Saved adapter file changed.")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)

            async def fetch():
                temporary = path.with_name(path.name + ".partial")
                digest = hashlib.sha256()
                count = 0
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with temporary.open("wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                            digest.update(chunk)
                            count += len(chunk)
                        f.flush()
                        os.fsync(f.fileno())
                os.replace(temporary, path)
                return {"bytes": count, "sha256": digest.hexdigest()}

            manifest[name] = await transport.free(
                "download adapter file " + name, fetch
            )
            save_json(manifest_path, manifest)
    return manifest


async def run_once():
    config_path = ROOT / "experiments/format_sft.json"
    config = json.loads(config_path.read_text())
    proof = json.loads((ROOT / "research/format_sft_rendering.json").read_text())
    if hashlib.sha256(config_path.read_bytes()).hexdigest() != proof["config_sha256"]:
        raise RuntimeError("The approved SFT configuration changed.")
    for name, digest in proof["implementation_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("The frozen SFT implementation changed.")
    decision_path = ROOT / "results/alias_probe/summary.json"
    decision = json.loads(decision_path.read_text())
    if (
        hashlib.sha256(
            (ROOT / "results/alias_probe/games.jsonl.gz").read_bytes()
        ).hexdigest()
        != config["decision_source_sha256"]
        or not decision["complete"]
        or decision["decision"] != "run_approved_sft_then_qualify"
    ):
        raise RuntimeError("Conditional SFT approval does not apply to this probe.")
    if (
        not config["training_authorized"]
        or config["rl_training_authorized"]
        or config["training_kind"] != "format_sft"
        or config["run_cap_usd"] != "2.510000"
    ):
        raise RuntimeError("Only the approved bounded format SFT may run.")
    records_path = ROOT / "experiments/format_qualification_games.json"
    records = json.loads(records_path.read_text())
    if (
        hashlib.sha256(records_path.read_bytes()).hexdigest()
        != proof["qualification_games_sha256"]
        or records != qualification_records()
    ):
        raise RuntimeError("The fixed qualification games changed.")
    out = ROOT / "results/format_sft"
    complete_path = out / "completion.json"
    if complete_path.exists():
        done = json.loads(complete_path.read_text())
        if done["config_sha256"] != proof["config_sha256"]:
            raise RuntimeError("Completed SFT used different settings.")
        print(
            "Format SFT and qualification are already complete. No service calls.",
            flush=True,
        )
        return
    data = supervised_data(config)
    directory = ROOT / "runs" / config["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        copy = directory / "config.json"
        if copy.exists() and json.loads(copy.read_text()) != config:
            raise RuntimeError("Existing SFT run has different settings.")
        save_json(copy, config)
        transport = GuardedTinker(
            config,
            directory,
            usage_path=out / "usage.jsonl",
            run_cap_usd=config["run_cap_usd"],
        )
        transport.ledger.check_run(
            estimate_usd=proof["forecast_usd"], max_cost_usd=config["run_cap_usd"]
        )
        stop_heartbeat = asyncio.Event()
        heartbeat = None
        tasks = []
        stopped = False
        failure = None
        outcomes = []
        loop = asyncio.get_running_loop()

        def stop():
            nonlocal stopped
            stopped = True
            transport.failed = True

        loop.add_signal_handler(signal.SIGINT, stop)
        loop.add_signal_handler(signal.SIGTERM, stop)
        try:
            await transport.open(recover_pending=True)
            heartbeat = asyncio.create_task(transport.heartbeat(stop_heartbeat))
            trainer = GuardedSupervised(transport)
            model_id = await trainer.create_model(config)
            curves = []
            for epoch in range(config["epochs"]):
                order = list(range(len(data)))
                random.Random(config["shuffle_seed"] + epoch).shuffle(order)
                for start in range(0, len(order), config["batch_size"]):
                    if stopped or transport.failed:
                        raise RuntimeError("SFT stopped before another update.")
                    if heartbeat.done():
                        heartbeat.result()
                    indices = order[start : start + config["batch_size"]]
                    row = await trainer.batch(
                        model_id, len(curves), indices, data, config
                    )
                    row["epoch"] = epoch + 1
                    curves.append(row)
                    save_json(out / "learning_curve.json", {"updates": curves})
                    print(
                        json.dumps(
                            {
                                "sft_update": row["update"],
                                "of": config["updates"],
                                "action_nll": row["action_nll"],
                                "budget": transport.run_status(),
                            }
                        ),
                        flush=True,
                    )
            sampler_id = await trainer.sampler(model_id, config)
            checkpoints = await trainer.save_checkpoints(model_id, config)
            adapter_manifest = await download_export(transport, checkpoints["external"])
            semaphore = asyncio.Semaphore(config["concurrent_games"])

            async def evaluate(record):
                path = (
                    directory
                    / "games"
                    / (
                        hashlib.sha256(
                            (config["primary_model"] + "/" + record["id"]).encode()
                        ).hexdigest()
                        + ".json"
                    )
                )
                if path.exists():
                    return
                async with semaphore:
                    if stopped or transport.failed:
                        raise RuntimeError(
                            "Qualification paused until pending futures are collected."
                        )
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
                        raise RuntimeError("Qualification rollout was incomplete.")
                    result = env.result()
                    result.update(
                        policy="format_sft",
                        grammar_version=config["grammar_version"],
                        training_model_id=model_id,
                        sampler_id=sampler_id,
                        trajectory_transitions=len(trajectory.transitions),
                    )
                    save_json(path, result)
                    print(
                        json.dumps(
                            {
                                "qualification_game": record["id"],
                                "won": result["won"],
                                "invalid": result["invalid_count"],
                                "budget": transport.run_status(),
                            }
                        ),
                        flush=True,
                    )

            tasks = [asyncio.create_task(evaluate(record)) for record in records]
            await asyncio.gather(*tasks)
            await transport.finish()
            save_json(
                complete_path,
                {
                    "config_sha256": proof["config_sha256"],
                    "training_model_id": model_id,
                    "sampler_id": sampler_id,
                    "checkpoints": checkpoints,
                    "adapter_files": adapter_manifest,
                    "updates": len(curves),
                    "qualification_games": len(records),
                    "rl_updates": 0,
                    "run_budget": transport.run_status(),
                },
            )
        except Exception as exc:
            failure = exc
        finally:
            transport.failed = True
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            stop_heartbeat.set()
            try:
                if heartbeat:
                    outcomes.extend(
                        await asyncio.gather(heartbeat, return_exceptions=True)
                    )
            finally:
                await transport.close()
                loop.remove_signal_handler(signal.SIGINT)
                loop.remove_signal_handler(signal.SIGTERM)
        if stopped:
            raise RuntimeError(
                "Stopped after draining active HTTP work. Retain all pending holds."
            )
        network = next(
            (r for r in outcomes if isinstance(r, NetworkInterruption)), None
        )
        if network:
            raise network
        if failure:
            raise failure


async def main():
    while True:
        try:
            return await run_once()
        except (NetworkInterruption, httpx.TransportError):
            print(
                "Network interrupted. Active HTTP work drained; reconnecting to recover saved operations before new work.",
                flush=True,
            )
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
