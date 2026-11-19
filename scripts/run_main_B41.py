"""Run the authorized B seed 41 stage, then stop before any other seed."""

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

import httpx
import numpy as np
import tinker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tinker_cookbook.rl.rollouts import do_single_rollout
from twenty_bits.native_checkpoints import PersistentEndpointRL
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.guess_metrics import guess_state, guess_summary
from scripts.run_rl_pilot import game_metrics
from twenty_bits.model_player import GuardedCompleter, TableEnv
from twenty_bits.rl_pilot import (
    GuardedRL,
    SamplingScope,
    group_data,
    pack_trajectory,
    unpack_trajectory,
)
from twenty_bits.recovery import RecoveringTransport
from twenty_bits.tinker_transport import NetworkInterruption, save_json
from twenty_bits.worlds import ROOT, training_game


def metrics(games):
    return {**game_metrics(games), "guess_with_k_remaining": guess_summary(games)}


def save_reused_development_base(out, manifest):
    source = ROOT / "results/pilot_A/games.jsonl.gz"
    if (
        hashlib.sha256(source.read_bytes()).hexdigest()
        != manifest["raw_development_source_sha256"]
    ):
        raise RuntimeError("The saved raw development control changed.")
    records = {r["id"]: r for r in manifest["development"]}
    games = [json.loads(line) for line in gzip.open(source, "rt")]
    base = sorted(
        [g for g in games if g["kind"] == "dev" and g["update"] == 0],
        key=lambda g: g["game_id"],
    )
    if {g["game_id"] for g in base} != set(records):
        raise RuntimeError("Reused raw development cases differ.")
    for g in base:
        g["guess_state"] = guess_state(g, records[g["game_id"]])
    (out / "development_base_games.jsonl.gz").write_bytes(
        gzip.compress(
            "".join(json.dumps(g, separators=(",", ":")) + "\n" for g in base).encode(),
            mtime=0,
        )
    )
    save_json(
        out / "development-00.json",
        {"policy_step": 0, "reused_from_pilot": True, **metrics(base)},
    )


def save_reused_frozen_base(out, manifest):
    source = ROOT / "results/main_A11/games.jsonl.gz"
    if (
        hashlib.sha256(source.read_bytes()).hexdigest()
        != manifest["raw_frozen_source_sha256"]
    ):
        raise RuntimeError("The matched raw frozen control archive changed.")
    games = [json.loads(line) for line in gzip.open(source, "rt")]
    base = [g for g in games if g["kind"] == "eval_base"]
    if len(base) != 280 or {g["game_id"] for g in base} != {
        r["id"] for r in manifest["evaluation"]
    }:
        raise RuntimeError(
            "The reused raw control differs from the frozen primary slice."
        )
    save_json(
        out / "eval_base.json",
        {"policy_step": 0, "reused_from_A11": True, **metrics(base)},
    )


async def run_once():
    approval_path = ROOT / "research/main_B41_approval.json"
    if not approval_path.exists() or not json.loads(approval_path.read_text()).get(
        "authorized"
    ):
        print("B41 lacks authorization. No service calls.", flush=True)
        return
    persistence = ROOT / "research/native_persistence_test.json"
    if not persistence.exists() or not json.loads(persistence.read_text()).get(
        "passed"
    ):
        print(
            "B41 waits for the native persistence test. No service calls.", flush=True
        )
        return
    pause_path = ROOT / "research/main_B41_pause.json"
    if pause_path.exists() and json.loads(pause_path.read_text())["active"]:
        print(
            "B41 is paused. Explicit user resume is required. No service calls.",
            flush=True,
        )
        return
    path = ROOT / "experiments/main_B41.json"
    config = json.loads(path.read_text())
    proof = json.loads((ROOT / "research/main_B41_preflight.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != proof["config_sha256"]:
        raise RuntimeError("The approved main-run settings changed.")
    complete = ROOT / "results/main_B41/completion.json"
    if complete.exists():
        if json.loads(complete.read_text())["config_sha256"] != proof["config_sha256"]:
            raise RuntimeError("Completed main seed used different settings.")
        print("B41 stage complete; stop at its gate. No service calls.", flush=True)
        return
    for name, digest in proof["implementation_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("The frozen RL implementation changed.")
    manifest_path = ROOT / "experiments/main_B41_games.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != proof["games_sha256"]:
        raise RuntimeError("The fixed main games changed.")
    manifest = json.loads(manifest_path.read_text())
    approval = json.loads((ROOT / "research/main_B41_approval.json").read_text())
    if approval["active_stage"] != "B41" or not approval["stop_after_B41_endpoint"]:
        raise RuntimeError("Stop at the B seed 41 gate before any further paid work.")
    for row in manifest["training"]:
        r = row["record"]
        if r != training_game(r["n"], 1000000 + row["update"], seed=41, noise=0.10):
            raise RuntimeError(
                "Main training must use its fixed training-pool factory."
            )
    if (
        not config["rl_training_authorized"]
        or config["initial_policy"] != "raw_base"
        or config["sampling_checkpoint_paths"]
        or config["run_cap_usd"] != "42.490000"
        or config["lora"]["seed"] != 41
        or config["pilot_condition"] != "B"
        or config["noise"] != 0.10
        or config["updates"] != 30
        or config["observation_mode"] != "candidate_set"
    ):
        raise RuntimeError("This runner permits only main B seed 41, then its gate.")
    directory = ROOT / "runs" / config["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    out = ROOT / "results/main_B41"
    with (directory / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        transport = RecoveringTransport(
            config,
            directory,
            usage_path=out / "usage.jsonl",
            run_cap_usd=config["run_cap_usd"],
            registry_path=ROOT / "research/main_B41_replacements.json",
        )
        used = transport.run_status()
        remaining = max(
            Decimal(0),
            Decimal(proof["stage_forecast_before_margin_usd"])
            - Decimal(used["spent_usd"])
            - Decimal(used["held_usd"]),
        )
        transport.ledger.check_run(
            estimate_usd=f"{remaining:.6f}", max_cost_usd=f"{remaining:.6f}"
        )
        save_json(directory / "config.json", config)
        trainer = PersistentEndpointRL(transport)
        heartbeat = None
        heartbeat_stop = asyncio.Event()
        stop_requested = False
        tasks = []
        loop = asyncio.get_running_loop()

        def stop():
            nonlocal stop_requested
            stop_requested = True
            transport.failed = True

        loop.add_signal_handler(signal.SIGINT, stop)
        loop.add_signal_handler(signal.SIGTERM, stop)
        parallelism = int(
            os.environ.get("TWENTY_BITS_CONCURRENT_GAMES", config["concurrent_games"])
        )
        if not 1 <= parallelism <= 32:
            raise ValueError("Execution concurrency must be between 1 and 32.")
        save_json(
            directory / "execution.json",
            {
                "concurrent_games": parallelism,
                "sampling_config_sha256": proof["config_sha256"],
                "note": "Execution parallelism only; games, prompts, generation seeds, sampling settings and all experiment caps remain unchanged.",
            },
        )
        semaphore = asyncio.Semaphore(parallelism)

        async def sample_game(record, *, kind, update, member=None):
            if kind == "train":
                scope = f"train/update-{update:02d}/member-{member}/"
                namespace = f"main-U-v1/B/seed41/train/member-{member}"
            elif kind == "dev":
                scope = f"dev/checkpoint-{update:02d}/"
                namespace = "pilot-A-v1/development"
            else:
                scope = kind + "/"
                namespace = "main-U-v1/evaluation"
            key = scope + record["id"]
            dest = (
                directory
                / "games"
                / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            )
            if dest.exists():
                return json.loads(dest.read_text())
            async with semaphore:
                if transport.failed or stop_requested:
                    raise RuntimeError("New rollouts paused while pending work drains.")
                if heartbeat.done():
                    heartbeat.result()
                local = {**config, "sampling_seed_namespace": namespace}
                env = TableEnv(
                    record,
                    config["primary_model"],
                    local,
                    message_builder=candidate_messages,
                )
                trajectory = await do_single_rollout(
                    GuardedCompleter(SamplingScope(transport, scope), env), env
                )
                result = env.result()
                if not env.game.done:
                    raise RuntimeError("An RL rollout returned an unfinished game.")
                if (
                    abs(
                        sum(t.reward for t in trajectory.transitions) - result["reward"]
                    )
                    > 1e-10
                ):
                    raise RuntimeError(
                        "Cookbook return differs from exact outcome reward."
                    )
                result.update(
                    kind=kind,
                    update=update,
                    member=member,
                    policy_step=transport.active_step,
                    scope=scope,
                    sampling_seed_namespace=namespace,
                    policy="raw_base" if transport.active_step == 0 else "main_B41",
                    guess_state=guess_state(result, record),
                    trajectory=pack_trajectory(trajectory),
                )
                save_json(dest, result)
                if kind.startswith("eval_"):
                    print(
                        json.dumps(
                            {
                                "evaluation": kind,
                                "game": record["id"],
                                "won": result["won"],
                                "questions": result["questions"],
                                "eig": result["eig_per_question"],
                            }
                        ),
                        flush=True,
                    )
                return result

        async def sample_many(coroutines):
            nonlocal tasks
            tasks = [asyncio.create_task(c) for c in coroutines]
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            failures = [r for r in outcomes if isinstance(r, BaseException)]
            if failures:
                transport.failed = True
                network = next(
                    (r for r in failures if isinstance(r, NetworkInterruption)), None
                )
                raise network or failures[0]
            return outcomes

        async def develop(step):
            games = await sample_many(
                sample_game(r, kind="dev", update=step) for r in manifest["development"]
            )
            row = {"policy_step": step, **metrics(games)}
            save_json(out / f"development-{step:02d}.json", row)
            print(
                json.dumps({"development": row, "budget": transport.run_status()}),
                flush=True,
            )

        async def evaluate(kind, step):
            transport.active_step = step
            games = await sample_many(
                sample_game(r, kind=kind, update=step) for r in manifest["evaluation"]
            )
            save_json(out / f"{kind}.json", {"policy_step": step, **metrics(games)})

        failure = None
        outcomes = []
        try:
            await transport.open(recover_pending=True)
            heartbeat = asyncio.create_task(transport.heartbeat(heartbeat_stop))
            model_id = await trainer.create_model(config)
            await trainer.base_sampler(config)
            save_reused_frozen_base(out, manifest)
            save_reused_development_base(out, manifest)
            updates = []
            checkpoints = {}
            stop_reason = "completed_30_updates"
            for row in manifest["training"]:
                step, record = row["update"], row["record"]
                games = await sample_many(
                    sample_game(record, kind="train", update=step, member=i)
                    for i in range(8)
                )
                trajectories = [unpack_trajectory(g["trajectory"]) for g in games]
                data, archive, returns, advantages = group_data(trajectories)
                if not data:
                    raise RuntimeError(
                        "No sampled action tokens were available for an update."
                    )
                if not np.allclose(
                    returns, [g["reward"] for g in games], atol=1e-12, rtol=0
                ):
                    raise RuntimeError(
                        "Group advantage inputs include unexpected reward."
                    )
                data_path = out / f"training-data-{step:02d}.json.gz"
                encoded = json.dumps(
                    archive, separators=(",", ":"), allow_nan=False
                ).encode()
                data_path.parent.mkdir(parents=True, exist_ok=True)
                compressed = gzip.compress(encoded, mtime=0)
                if data_path.exists() and data_path.read_bytes() != compressed:
                    raise RuntimeError("A resumed RL batch changed its training data.")
                temporary = data_path.with_suffix(".tmp")
                with temporary.open("wb") as f:
                    f.write(compressed)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, data_path)
                training = await trainer.update(model_id, step, data, archive, config)
                snapshots = await trainer.snapshot(model_id, step, config)
                if "checkpoint" in snapshots:
                    checkpoints[str(step)] = snapshots["checkpoint"]
                variance = float(np.var(returns))
                stats = {
                    "update": step,
                    "n": record["n"],
                    "start_state": record["id"],
                    **metrics(games),
                    **training,
                    "returns": returns,
                    "advantages": advantages,
                    "reward_variance": variance,
                    "win_variance": float(np.var([g["won"] for g in games])),
                    "nonzero_group_fraction": float(variance > 1e-12),
                }
                updates.append(stats)
                stats["cumulative_nonzero_group_fraction"] = float(
                    np.mean([u["nonzero_group_fraction"] for u in updates])
                )
                save_json(out / "learning_curve.json", {"updates": updates})
                print(
                    json.dumps(
                        {"training_update": stats, "budget": transport.run_status()}
                    ),
                    flush=True,
                )
                if step in config["development_checks"]:
                    await develop(step)
            last = updates[-1]["update"]
            await evaluate("eval_endpoint", last)
            await transport.finish()
            save_json(
                complete,
                {
                    "config_sha256": proof["config_sha256"],
                    "training_model_id": model_id,
                    "initialization": "raw_base_no_sft",
                    "updates": last,
                    "stop_reason": stop_reason,
                    "training_games": last * 8,
                    "development_games": 8 * len(config["development_checks"]),
                    "reused_raw_development_games": 8,
                    "frozen_base_games": 280,
                    "reused_raw_frozen_games": 280,
                    "new_raw_frozen_games": 0,
                    "frozen_endpoint_games": 280,
                    "next_gate": "Stop after B41 and report all three main seeds. No further paid work.",
                    "endpoint_evaluations_complete": True,
                    "condition": "B",
                    "training_noise": 0.10,
                    "checkpoints": checkpoints,
                    "external_upload_or_export_required": False,
                    "snapshots": transport.state["snapshots"],
                    "run_budget": transport.run_status(),
                },
            )
        except Exception as exc:
            failure = exc
        finally:
            transport.failed = True
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            heartbeat_stop.set()
            if heartbeat:
                outcomes.extend(await asyncio.gather(heartbeat, return_exceptions=True))
            await transport.close()
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)
        if stop_requested:
            raise RuntimeError(
                "Main seed stopped after draining HTTP work. All pending holds retained."
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
                "Network interrupted. Drained active work; reconnecting and collecting all saved sample/training futures before new submissions.",
                flush=True,
            )
            await asyncio.sleep(1)
        except tinker.APIStatusError as exc:
            if exc.status_code == 429 or exc.status_code >= 500:
                print(
                    "Submission interrupted. HTTP operations drained; recovering saved IDs without resubmitting mutations.",
                    flush=True,
                )
                await asyncio.sleep(1)
                continue
            raise


if __name__ == "__main__":
    asyncio.run(main())
